"""Paper figure extraction: the 2 s TTFT rule, extract_run and the per-user cache."""

from __future__ import annotations

import ast
import json
import os
import stat
from pathlib import Path

import numpy as np
import pytest

STEM, NODE = "proxycmp_haproxy", 4


def _write_result(path: Path, ttfts, *, semantics="incremental_sse", tbt=0.1) -> Path:
    """A tiny result0.json: warm-up run 0 (dropped by the scripts) and data run 1
    with one successful request per TTFT value, every P99 TBT within 250 ms."""
    request = {"success": True, "timing_semantics": semantics, "tbt_p99_s": tbt}
    doc = {
        "per_run": [
            {"run_index": 0, "requests_completed": 1, "duration_s": 1.0},
            {"run_index": 1, "requests_completed": len(ttfts), "duration_s": 10.0},
        ],
        "requests": [{**request, "run_index": 0, "ttft_s": 9.0, "latency": 10.0}]
        + [{**request, "run_index": 1, "ttft_s": t, "latency": t + 1.0} for t in ttfts],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


@pytest.fixture
def preview(tmp_path, monkeypatch):
    from eval.plot import arxiv_submission_preview as preview

    monkeypatch.setattr(preview, "RUNS_ROOT", tmp_path / "suite")
    monkeypatch.setattr(preview, "CACHE_DIR", tmp_path / "cache" / "preview")
    monkeypatch.setattr(preview, "_WARNED", set())
    return preview


def _cell(preview, ttfts, **kwargs) -> Path:
    result = preview.RUNS_ROOT / STEM / "run0" / f"n{NODE}" / "results" / "result0.json"
    return _write_result(result, ttfts, **kwargs)


def _extract(preview, keep_arrays=True):
    return preview.extract_cell(STEM, NODE, keep_arrays=keep_arrays, refresh=False)


def test_preview_scores_the_paper_slo_at_two_seconds(preview) -> None:
    assert preview.TTFT_SLO_MULTI[preview._TTFT_SLO_INDEX] == preview.TTFT_SLO_S == 2.0
    _cell(preview, [0.5, 1.5, 2.5, 3.5])
    st = _extract(preview)
    assert st.n_req == 4
    # TTFT 1.5 s meets the paper SLO and 2.5 s misses it; every TBT meets 250 ms.
    assert st.attainment == pytest.approx(0.5)
    assert st.ttft_attainment == st.ttft_attain_2s == pytest.approx(0.5)
    assert (st.ttft_attain_1s, st.ttft_attain_3s) == pytest.approx((0.25, 0.75))


def test_cell_cache_is_private_and_follows_its_source(preview) -> None:
    src = _cell(preview, [0.5, 1.5])
    assert _extract(preview).attainment == 1.0
    assert stat.S_IMODE(preview.CACHE_DIR.stat().st_mode) == 0o700
    sjson, snpz = sorted(preview.CACHE_DIR.iterdir())
    assert (sjson.suffix, snpz.suffix) == (".json", ".npz")
    assert {stat.S_IMODE(p.stat().st_mode) for p in (sjson, snpz)} == {0o600}
    ttft, tbt = preview.load_arrays(STEM, NODE)
    assert ttft.tolist() == [0.5, 1.5] and tbt.size == 2

    # A trusted entry is read back as stored ...
    marked = json.loads(sjson.read_text())
    marked["attainment"] = 0.125
    sjson.write_text(json.dumps(marked))
    assert _extract(preview).attainment == 0.125

    # ... until the result file changes: new data, new key, fresh extraction.
    _cell(preview, [2.5, 3.5, 4.5])
    later = src.stat().st_mtime_ns + 10**9
    os.utime(src, ns=(later, later))
    st = _extract(preview)
    assert (st.n_req, st.attainment) == (3, 0.0)


def test_cell_cache_does_not_cross_suite_folders(preview, tmp_path, monkeypatch) -> None:
    _cell(preview, [0.5])
    assert _extract(preview, keep_arrays=False).attainment == 1.0
    monkeypatch.setattr(preview, "RUNS_ROOT", tmp_path / "other-suite")
    _cell(preview, [5.0])
    st = _extract(preview, keep_arrays=False)
    assert st.attainment == 0.0
    assert Path(st.src).is_relative_to(tmp_path / "other-suite")


def test_cell_cache_ignores_entries_others_could_have_written(preview) -> None:
    _cell(preview, [0.5, 1.5])
    _extract(preview)
    sjson, snpz = sorted(preview.CACHE_DIR.iterdir())
    poisoned = json.loads(sjson.read_text())
    poisoned["attainment"] = 0.125
    sjson.write_text(json.dumps(poisoned))
    planted = np.array([7.0], dtype=np.float32)
    np.savez_compressed(snpz, ttft=planted, tbt=planted)
    assert preview.load_arrays(STEM, NODE)[0].tolist() == [7.0]  # still trusted (0600)

    sjson.chmod(0o664)
    snpz.chmod(0o646)
    assert _extract(preview).attainment == 1.0
    sjson, snpz = sorted(preview.CACHE_DIR.iterdir())  # replaced, private again
    assert {stat.S_IMODE(p.stat().st_mode) for p in (sjson, snpz)} == {0o600}
    np.savez_compressed(snpz, ttft=planted, tbt=planted)
    snpz.chmod(0o666)
    assert preview.load_arrays(STEM, NODE)[0].tolist() == [0.5, 1.5]


def test_cell_cache_ignores_entries_of_another_user(preview, monkeypatch) -> None:
    _cell(preview, [0.5, 1.5])
    _extract(preview, keep_arrays=False)
    sjson = next(preview.CACHE_DIR.glob("*.json"))
    poisoned = json.loads(sjson.read_text())
    poisoned["attainment"] = 0.125
    sjson.write_text(json.dumps(poisoned))
    assert preview.read_cache_file(sjson) is not None

    other_uid = os.getuid() + 1
    monkeypatch.setattr(os, "getuid", lambda: other_uid)
    assert preview.read_cache_file(sjson) is None
    assert preview.ensure_cache_dir() is None
    assert _extract(preview, keep_arrays=False).attainment == 1.0


def test_cache_folder_others_can_write_is_not_used(preview) -> None:
    preview.CACHE_DIR.mkdir(parents=True)
    preview.CACHE_DIR.chmod(0o777)  # as if another user had created it first
    _cell(preview, [0.5])
    assert _extract(preview).attainment == 1.0
    assert preview.load_arrays(STEM, NODE)[0].tolist() == [0.5]
    assert list(preview.CACHE_DIR.iterdir()) == []


def test_failed_cache_write_keeps_the_computed_cell(preview) -> None:
    preview.CACHE_DIR.mkdir(parents=True)
    preview.CACHE_DIR.chmod(0o500)  # owned and private, but no write permission
    try:
        _cell(preview, [0.5, 2.5])
        assert _extract(preview).attainment == 0.5
        assert preview.load_arrays(STEM, NODE)[0].tolist() == [0.5, 2.5]
    finally:
        preview.CACHE_DIR.chmod(0o700)


def test_without_a_home_directory_nothing_is_cached(preview, monkeypatch) -> None:
    def no_home(cls):
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(no_home))
    assert preview.figure_cache_dir("x") is None
    monkeypatch.setattr(preview, "CACHE_DIR", None)
    _cell(preview, [0.5, 2.5])
    assert _extract(preview).attainment == 0.5
    assert preview.load_arrays(STEM, NODE)[0].tolist() == [0.5, 2.5]


def test_figure_caches_live_in_the_users_cache_folder(tmp_path, monkeypatch) -> None:
    from eval.plot import arxiv_submission_full_figures as figures
    from eval.plot import arxiv_submission_preview as preview

    tail = ("exaserve", "figures", "x")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert preview.figure_cache_dir("x") == tmp_path.joinpath("xdg", *tail)
    monkeypatch.setenv("XDG_CACHE_HOME", "relative")  # not absolute: ignored (XDG spec)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert preview.figure_cache_dir("x") == tmp_path.joinpath("home", ".cache", *tail)
    assert preview.CACHE_DIR.parts[-3:] == ("exaserve", "figures", "arxiv_submission_preview")
    assert figures.P.CACHE_DIR.parts[-3:] == (
        "exaserve",
        "figures",
        "arxiv_submission_full_figures",
    )


def test_extract_run_reports_every_ttft_threshold(tmp_path, monkeypatch) -> None:
    from eval.plot import arxiv_submission_full_figures as figures

    monkeypatch.setattr(figures.P, "RUNS_ROOT", tmp_path)
    result = tmp_path / "proxycmp_envoy_scale" / "run0" / "n256" / "results" / "result0.json"
    _write_result(result, [0.5, 1.5, 2.5, 3.5])
    st = figures.extract_run("proxycmp_envoy_scale", 256, {1})
    assert (st.ttft_attain_1s, st.ttft_attain_2s, st.ttft_attain_3s) == pytest.approx(
        (0.25, 0.5, 0.75)
    )
    assert st.ttft_attainment == st.attainment == pytest.approx(0.5)
    # build() substitutes this cell for Envoy at 256 nodes; fig1's TTFT panel plots it.
    assert figures._pt(st, "ttft2") == pytest.approx((0.5, 0.0))
    assert figures._collect({("envoy", 256): st}, "envoy", "ttft2")[0] == [256]

    # Without incremental SSE there is no TTFT attainment: NaN (no point), never 0.
    _write_result(result, [0.5, 1.5], semantics="buffered_response")
    st = figures.extract_run("proxycmp_envoy_scale", 256, {1})
    for value in (st.ttft_attain_1s, st.ttft_attain_2s, st.ttft_attain_3s, st.ttft_attainment):
        assert np.isnan(value)
    assert figures._collect({("envoy", 256): st}, "envoy", "ttft2")[0] == []


def test_reuse_cache_is_json_bound_to_suite_and_slo(tmp_path, monkeypatch) -> None:
    from eval.plot import arxiv_submission_full_figures as figures

    P = figures.P
    monkeypatch.setattr(P, "RUNS_ROOT", tmp_path / "suite")
    monkeypatch.setattr(P, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(P, "_WARNED", set())
    result = tmp_path / "suite" / "proxycmp_envoy_scale" / "run0" / "n256" / "results"
    _write_result(result / "result0.json", [0.5, 2.5])
    st = figures.extract_run("proxycmp_envoy_scale", 256, {1})
    built = ({("envoy", 256): st, ("direct", 1): None}, {}, {("oat_120b", 64): st}, {})
    figures._save_built(built)
    saved = P.CACHE_DIR / figures.BUILT_CACHE_NAME
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    assert json.loads(saved.read_text())["runs_root"] == str(tmp_path / "suite")
    assert figures._load_built() == built

    monkeypatch.setattr(P, "RUNS_ROOT", tmp_path / "other-suite")
    assert figures._load_built() is None
    monkeypatch.setattr(P, "RUNS_ROOT", tmp_path / "suite")
    monkeypatch.setattr(P, "TTFT_SLO_S", 1.0)
    assert figures._load_built() is None
    monkeypatch.setattr(P, "TTFT_SLO_S", 2.0)
    assert figures._load_built() == built
    saved.chmod(0o666)
    assert figures._load_built() is None


def test_figure_scripts_never_unpickle() -> None:
    plot = Path(__file__).parents[1] / "plot"
    for name in ("arxiv_submission_full_figures.py", "arxiv_submission_preview.py"):
        tree = ast.parse((plot / name).read_text(encoding="utf-8"))
        modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        modules |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not {"pickle", "dill", "joblib", "shelve"} & modules, name
