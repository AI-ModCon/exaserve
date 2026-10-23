"""The plan decides what the pipeline-parallel patches do on a layer-name miss.

A lookup with no exact or canonical match used to substitute a representative
layer or mapping entry, or skip a KV-cache binding, and said so only in verbose
logs (KNOWN_ISSUES D5). Production plans now fail on the first fallback;
validation plans record each one and warn once.
"""

from __future__ import annotations

from collections import defaultdict
import sys
from types import ModuleType, SimpleNamespace

import pytest

from exaserve import _sitecustomize
from exaserve.compat.profile import PP_LAYER_FALLBACK_POLICY, PP_PATCH_GATE
from exaserve.plan.runtime_environment import runtime_environment


def _plan(*, validation_mode):
    return SimpleNamespace(
        validation_mode=validation_mode,
        compatibility_profile_hash="a" * 64,
        manifest_hash="b" * 64,
        vendor="xpu",
        engine="vllm",
        models=(SimpleNamespace(pipeline_parallel_size=2, tensor_parallel_size=8),),
        collect_stats=False,
        runtime=SimpleNamespace(
            null_compute=False,
            null_compute_latency_s=0.0,
            pp_shard_aware=True,
            clean_stage=False,
            instrumentation=False,
        ),
        readiness=SimpleNamespace(
            serve_proxy_health_check_timeout_s=10.0,
            serve_proxy_ready_check_timeout_s=11.0,
            serve_start_proxy_timeout_s=12.0,
        ),
    )


@pytest.fixture(autouse=True)
def _fresh_fallback_record(monkeypatch):
    monkeypatch.setattr(_sitecustomize, "PP_LAYER_FALLBACKS", {})


def test_the_patch_module_and_the_profile_name_the_same_variable():
    assert _sitecustomize.PP_LAYER_FALLBACK_POLICY == PP_LAYER_FALLBACK_POLICY


@pytest.mark.parametrize("validation_mode, policy", [(False, "fail"), (True, "record")])
def test_the_plan_selects_the_policy(validation_mode, policy):
    plan = _plan(validation_mode=validation_mode)
    assert runtime_environment(plan)[PP_LAYER_FALLBACK_POLICY] == policy


def test_a_canonical_match_is_not_a_fallback(monkeypatch):
    monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, "fail")
    layer = object()
    mapping = {"model.layers.0.self_attn.attn": layer}
    found = _sitecustomize._find_backend_fallback_layer(mapping, "model.layers.40.self_attn.attn")
    assert found is layer
    assert _sitecustomize.PP_LAYER_FALLBACKS == {}


@pytest.mark.parametrize("policy", ["fail", None])
def test_production_and_unset_policies_fail_closed(monkeypatch, policy):
    if policy is None:
        monkeypatch.delenv(PP_LAYER_FALLBACK_POLICY, raising=False)
    else:
        monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, policy)
    mapping = {"model.layers.0.self_attn.attn": object()}
    with pytest.raises(RuntimeError, match="does not allow layer fallbacks"):
        _sitecustomize._find_backend_fallback_layer(mapping, "model.layers.40.mlp.attn")
    with pytest.raises(RuntimeError, match="attention metadata"):
        _sitecustomize._resolve_mapping_value({"x": 1}, "unrelated.layer", None)


def test_validation_records_each_fallback_and_warns_once(monkeypatch, capsys):
    monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, "record")
    layer = object()
    mapping = {"model.layers.0.self_attn.attn": layer}
    for _ in range(2):
        found = _sitecustomize._find_backend_fallback_layer(mapping, "model.layers.40.mlp.attn")
        assert found is layer
    assert _sitecustomize._resolve_mapping_value({"x": 1}, "unrelated.layer", None) == ("x", 1)
    assert _sitecustomize.PP_LAYER_FALLBACKS == {
        ("backend lookup", "model.layers.40.mlp.attn"): repr("model.layers.0.self_attn.attn"),
        ("attention metadata", "unrelated.layer"): repr("x"),
    }
    assert capsys.readouterr().err.count("WARNING") == 2


class _Attention:
    """Stands in for vLLM's attention layer type."""


def _runner(source, layers):
    """A model runner whose attention layers sit in the static forward context, or
    only among the model's modules (the two lookups of _find_model_fallback_layer)."""
    in_context = source == "static forward context"
    return SimpleNamespace(
        vllm_config=SimpleNamespace(
            compilation_config=SimpleNamespace(
                static_forward_context=dict(layers)
                if in_context
                else {"model.embed_tokens": object()}
            )
        ),
        model=None if in_context else SimpleNamespace(named_modules=lambda: iter(layers.items())),
    )


SOURCES = ["static forward context", "model modules"]


@pytest.mark.parametrize("source", SOURCES)
def test_a_model_layer_name_match_is_not_a_fallback(monkeypatch, source):
    monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, "fail")
    layer = _Attention()
    runner = _runner(
        source, {"model.layers.0.mlp": object(), "model.layers.3.self_attn.attn": layer}
    )
    found = _sitecustomize._find_model_fallback_layer(
        runner, _Attention, "model.layers.3.self_attn.attn"
    )
    assert found == ("model.layers.3.self_attn.attn", layer)
    assert _sitecustomize.PP_LAYER_FALLBACKS == {}


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize("policy", ["fail", None])
def test_production_and_unset_policies_refuse_a_model_layer_fallback(monkeypatch, source, policy):
    if policy is None:
        monkeypatch.delenv(PP_LAYER_FALLBACK_POLICY, raising=False)
    else:
        monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, policy)
    runner = _runner(source, {"model.layers.0.self_attn.attn": _Attention()})
    with pytest.raises(RuntimeError, match="model layer lookup: no layer matches 'model.layers.40"):
        _sitecustomize._find_model_fallback_layer(
            runner, _Attention, "model.layers.40.self_attn.attn"
        )
    assert _sitecustomize.PP_LAYER_FALLBACKS == {}


@pytest.mark.parametrize("source", SOURCES)
def test_validation_records_a_model_layer_fallback(monkeypatch, capsys, source):
    monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, "record")
    first = _Attention()
    runner = _runner(
        source,
        {
            "model.layers.0.mlp": object(),
            "model.layers.0.self_attn.attn": first,
            "model.layers.1.self_attn.attn": _Attention(),
        },
    )
    found = _sitecustomize._find_model_fallback_layer(
        runner, _Attention, "model.layers.40.self_attn.attn"
    )
    # The first layer of the type, not a name match, is what a fallback binds.
    assert found == ("model.layers.0.self_attn.attn", first)
    assert _sitecustomize.PP_LAYER_FALLBACKS == {
        ("model layer lookup", "model.layers.40.self_attn.attn"): repr(
            "model.layers.0.self_attn.attn"
        ),
    }
    assert capsys.readouterr().err.count("WARNING") == 1


def _patched_bind_kv_cache(monkeypatch):
    """Apply the KV-cache binding patch (SC-02) over a stub vllm.v1.worker.utils."""
    names = ("vllm", "vllm.v1", "vllm.v1.worker", "vllm.v1.worker.utils")
    modules = [ModuleType(name) for name in names]
    for parent, child, name in zip(modules, modules[1:], names[1:]):
        setattr(parent, name.rsplit(".", 1)[1], child)
    for name, module in zip(names, modules):
        monkeypatch.setitem(sys.modules, name, module)
    worker_utils = modules[-1]
    worker_utils.defaultdict = defaultdict
    # Layer names here read model.layers.<index>.<...>.
    worker_utils.extract_layer_index = lambda layer_name, num_attn_module: int(
        layer_name.split(".")[2]
    )
    worker_utils.bind_kv_cache = lambda *arguments: None
    monkeypatch.setenv(PP_PATCH_GATE, "1")
    _sitecustomize._patch_vllm_bind_kv_cache()
    assert worker_utils.bind_kv_cache._exaserve_pp_kv_bind_patch
    return worker_utils.bind_kv_cache


def test_a_stage_relative_kv_cache_binding_is_not_a_fallback(monkeypatch):
    monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, "fail")
    bind_kv_cache = _patched_bind_kv_cache(monkeypatch)
    layer = SimpleNamespace()
    kv_cache = SimpleNamespace(shape=(2, 16))
    forward_context = {"model.layers.0.self_attn.attn": layer}
    bind_kv_cache({"model.layers.40.self_attn.attn": kv_cache}, forward_context, [], 1)
    assert layer.kv_cache == [kv_cache]
    assert forward_context["model.layers.40.self_attn.attn"] is layer
    assert _sitecustomize.PP_LAYER_FALLBACKS == {}


@pytest.mark.parametrize("policy", ["fail", None])
def test_production_and_unset_policies_refuse_to_skip_a_kv_cache_binding(monkeypatch, policy):
    if policy is None:
        monkeypatch.delenv(PP_LAYER_FALLBACK_POLICY, raising=False)
    else:
        monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, policy)
    bind_kv_cache = _patched_bind_kv_cache(monkeypatch)
    forward_context = {"model.layers.0.self_attn.attn": SimpleNamespace()}
    kv_caches = {"model.layers.40.mlp.attn": SimpleNamespace(shape=(2, 16))}
    with pytest.raises(RuntimeError, match="KV-cache binding: no layer matches 'model.layers.40"):
        bind_kv_cache(kv_caches, forward_context, [], 1)
    assert _sitecustomize.PP_LAYER_FALLBACKS == {}


def test_validation_records_a_skipped_kv_cache_binding(monkeypatch, capsys):
    monkeypatch.setenv(PP_LAYER_FALLBACK_POLICY, "record")
    bind_kv_cache = _patched_bind_kv_cache(monkeypatch)
    layer = SimpleNamespace()
    kv_caches = {
        "model.layers.0.self_attn.attn": SimpleNamespace(shape=(2, 16)),
        "model.layers.40.mlp.attn": SimpleNamespace(shape=(2, 16)),
    }
    forward_context = {"model.layers.0.self_attn.attn": layer}
    runner_kv_caches = []
    bind_kv_cache(kv_caches, forward_context, runner_kv_caches, 1)
    # The unmatched layer keeps no cache: the silent skip D5 described, now recorded.
    assert layer.kv_cache == [kv_caches["model.layers.0.self_attn.attn"]]
    assert "model.layers.40.mlp.attn" not in forward_context
    assert runner_kv_caches == list(kv_caches.values())
    assert _sitecustomize.PP_LAYER_FALLBACKS == {
        ("KV-cache binding", "model.layers.40.mlp.attn"): repr(None),
    }
    assert capsys.readouterr().err.count("WARNING") == 1
