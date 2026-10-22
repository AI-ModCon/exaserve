"""The plan decides what the pipeline-parallel patches do on a layer-name miss.

A lookup with no exact or canonical match used to substitute a representative
layer or mapping entry, or skip a KV-cache binding, and said so only in verbose
logs (KNOWN_ISSUES D5). Production plans now fail on the first fallback;
validation plans record each one and warn once.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from exaserve import _sitecustomize
from exaserve.compat.profile import PP_LAYER_FALLBACK_POLICY
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
