"""Site inputs of the evaluation tooling: where each comes from and where it stops."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import eval.site_config as site_config
from eval.lib import run_executor
from eval.lib.backends import ray as ray_backend
from eval.lib.plan_adapter import eval_site_profile
from eval.lib.run_planner import materialize_run_bundles
from exaserve.plan.io import load_site_profile
from exaserve.site import default_site_profile

_PROJECT = "/lus/flare/projects/example-project"


@pytest.fixture(autouse=True)
def fresh_site_caches():
    site_config.clear_site_config_cache()
    default_site_profile.cache_clear()
    yield
    site_config.clear_site_config_cache()
    default_site_profile.cache_clear()


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "tracked.txt").write_text("committed\n", encoding="utf-8")
    for argv in (
        ["git", "init"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "config", "user.name", "Test User"],
        ["git", "add", "tracked.txt"],
        ["git", "commit", "-m", "initial"],
    ):
        subprocess.run(argv, cwd=path, check=True, capture_output=True)
    return path


def _single_run_spec(path: Path, prompt_path: Path) -> Path:
    prompt_path.write_text(
        json.dumps([{"conversations": [{"from": "human", "value": "hi"}, {"from": "gpt"}]}]),
        encoding="utf-8",
    )
    path.write_text(
        f"""
name: site_inputs
matrix:
  name_template: "{{num_nodes}}_nodes"
  axes:
    - name: num_nodes
      values: [1]
      targets: [deployment.num_nodes, client.num_nodes, scheduler.nodes]
trace:
  kind: weak_scaling
  input_prompt_path: {prompt_path}
  tokenizer_builder: "eval.testing:whitespace_tokenizer_map"
workload:
  duration: 1.0
  input_len: 8
  output_len: 4
  rate_per_node: 2.0
deployment:
  models:
    - model_id: test/model
      tensor_parallel_size: 1
      pipeline_parallel_size: 1
      max_model_len: 64
      size: 1
client:
  num_runs: 1
  dest: direct
  num_go_procs: 1
  num_go_workers: 1
  go_concurrency: 4
backend:
  default: mock
  args:
    mock: {{}}
    ray:
      proxy:
        type: none
scheduler:
  type: pbs
""".lstrip(),
        encoding="utf-8",
    )
    return path


def test_materialize_takes_the_model_path_from_the_local_overrides(tmp_path, monkeypatch):
    """project_root in the local overrides is enough for `run materialize`, as the
    site configuration's error message and example file say."""
    overrides = tmp_path / "site_config_local.py"
    overrides.write_text(f"SITE_OVERRIDES = {{'project_root': {_PROJECT!r}}}\n", encoding="utf-8")
    monkeypatch.delenv("EXASERVE_PROJECT_ROOT")
    monkeypatch.delenv("EXASERVE_MODEL_STORAGE_PATH", raising=False)
    monkeypatch.setenv("EXASERVE_SITE_CONFIG_LOCAL", str(overrides))
    monkeypatch.setenv("EXASERVE_SNAPSHOT_DIR", str(tmp_path / "snapshots"))
    monkeypatch.setattr(site_config, "local_account_name", lambda: "alice")
    # Serving has no such file and still fails closed in this setup.
    with pytest.raises(RuntimeError, match="cannot derive the model storage path"):
        default_site_profile()

    plans = materialize_run_bundles(
        str(_single_run_spec(tmp_path / "spec.yaml", tmp_path / "prompts.json")),
        backend_name="mock",
        experiments_root=str(tmp_path / "runs"),
        trace_root=str(tmp_path / "traces"),
        repo_root=str(_git_repo(tmp_path / "repo")),
    )

    assert len(plans) == 1
    expected = f"{_PROJECT}/alice/models"
    assert load_site_profile(plans[0].site_profile_path).model_storage_path == expected
    assert plans[0].semantic_plan.deployment.model_storage_path == expected


@pytest.mark.parametrize(
    "exported",
    [
        {"EXASERVE_PROJECT_ROOT": _PROJECT},
        {
            "EXASERVE_MODEL_STORAGE_PATH": f"{_PROJECT}/shared/models",
            "EXASERVE_USER_DATA_ROOT": f"{_PROJECT}/shared/data",
        },
    ],
)
def test_eval_site_profile_is_the_serving_profile_when_a_variable_is_set(monkeypatch, exported):
    monkeypatch.delenv("EXASERVE_PROJECT_ROOT")
    for name, value in exported.items():
        monkeypatch.setenv(name, value)
    # A different overrides path must not leak into the profile either.
    monkeypatch.setattr(
        site_config,
        "get_site_config",
        lambda: SimpleNamespace(model_storage_path=f"{_PROJECT}/overrides/models"),
    )

    assert eval_site_profile() == default_site_profile()


def test_eval_launch_and_replay_drop_every_head_side_path_setting(monkeypatch):
    names = site_config.site_config_environment_names()
    head_paths = {f"EXASERVE_{field.upper()}" for field in site_config._PATH_FIELDS}
    assert head_paths | {"EXASERVE_SITE_CONFIG_LOCAL", "EXASERVE_PAPER_SUITE_ROOT"} <= names

    monkeypatch.setenv("EXASERVE_PAPER_SUITE_ROOT", f"{_PROJECT}/suite")
    launch = ray_backend._sanitize_launch_env(dict(os.environ))
    replay = run_executor._replay_base_environment({"EXASERVE_LOCAL_RUNTIME_ROOT": "/tmp/rt"})
    assert "EXASERVE_PAPER_SUITE_ROOT" not in launch
    assert "EXASERVE_PAPER_SUITE_ROOT" not in replay


def test_a_walltime_refusal_offers_the_allocation_campaign(tmp_path):
    from exaserve.state.status import RunState, StatusStore

    state_path = tmp_path / "run_status.json"
    StatusStore.run(state_path).initialize("g/r", RunState.PLANNED)
    run_plan = SimpleNamespace(
        bundle=SimpleNamespace(state_path=str(state_path)),
        scheduler=SimpleNamespace(type="pbs", queue="debug-scaling", walltime="02:00:00"),
        run_semantic_hash="a" * 64,
        spec_name="s",
        run_group_id="g",
        run_id="r",
    )
    scheduler = SimpleNamespace(submit=lambda _path: pytest.fail("the scheduler was contacted"))

    kind, detail = run_executor._submit_run_once(run_plan, scheduler, submit_attempt=1)
    assert kind == "invalid"
    assert "choose a longer queue or a shorter walltime" in detail
    assert detail.endswith(", or run this cell as an allocation-campaign child")


def test_ray_environment_script_is_expanded_and_must_be_absolute(tmp_path, monkeypatch):
    adapter = ray_backend.RayBackendAdapter()

    def plan(env_script):
        return SimpleNamespace(backend_args={"launch": {"env_script": env_script}})

    monkeypatch.setenv("HOME", str(tmp_path))
    assert adapter.runtime_env(plan("~/site/env.sh")).env_script == str(tmp_path / "site/env.sh")
    with pytest.raises(
        ValueError,
        match=r"^backend\.args\.ray\.launch\.env_script must be an absolute path, got 'env\.sh'$",
    ):
        adapter.runtime_env(plan("env.sh"))

    # Without a spec value the site configuration's script is used, and named.
    assert adapter.runtime_env(plan("")).env_script == os.environ["EXASERVE_ENV_SCRIPT_AURORA"]
    monkeypatch.setattr(
        ray_backend, "get_site_config", lambda: SimpleNamespace(env_script_aurora="site/env.sh")
    )
    with pytest.raises(ValueError, match=r"^EXASERVE_ENV_SCRIPT_AURORA .*must be an absolute"):
        adapter.runtime_env(plan(""))


def test_window_analysis_needs_no_site_configuration_for_help_or_an_explicit_root(
    tmp_path, monkeypatch
):
    from eval.scripts import direct_stream_window_analysis as analysis

    monkeypatch.delenv("EXASERVE_PROJECT_ROOT")
    monkeypatch.delenv("EXASERVE_PAPER_SUITE_ROOT", raising=False)
    monkeypatch.setenv("EXASERVE_SITE_CONFIG_LOCAL", str(tmp_path / "no-overrides.py"))
    with pytest.raises(ValueError, match="project_root is not set"):
        site_config.get_paper_suite_root()

    with pytest.raises(SystemExit) as excinfo:
        analysis.main(["--help"])
    assert excinfo.value.code == 0
    # An explicit root is analyzed; here it holds no results.
    with pytest.raises(RuntimeError, match="cannot analyze result evidence"):
        analysis.main(["--suite-root", str(tmp_path)])
