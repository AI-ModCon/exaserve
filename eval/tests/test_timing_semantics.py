"""Result and analysis timing semantics fail closed."""

from eval.plot.goodput import SLO_PRESETS, _request_meets_slo


def _request(semantics: str) -> dict:
    return {
        "success": True,
        "timing_semantics": semantics,
        "latency": 0.8,
        "ttft_s": 0.2,
        "tbt_p99_s": 0.05,
        "actual_completion_tokens": 8,
    }


def test_incremental_sse_can_satisfy_token_delivery_slo() -> None:
    assert _request_meets_slo(_request("incremental_sse"), SLO_PRESETS["paper"])


def test_buffered_and_legacy_timing_cannot_satisfy_token_delivery_slo() -> None:
    assert not _request_meets_slo(_request("buffered_response"), SLO_PRESETS["paper"])
    legacy = _request("incremental_sse")
    legacy.pop("timing_semantics")
    assert not _request_meets_slo(legacy, SLO_PRESETS["paper"])


def test_e2e_only_slo_remains_available_for_buffered_response() -> None:
    assert _request_meets_slo(_request("buffered_response"), SLO_PRESETS["e2e_2s"])


def test_paper_preset_scores_ttft_against_two_seconds() -> None:
    # The paper SLO is TTFT <= 2 s and per-request P99 TBT <= 250 ms.
    within, beyond = _request("incremental_sse"), _request("incremental_sse")
    within["ttft_s"], beyond["ttft_s"] = 1.5, 2.5
    assert SLO_PRESETS["paper"].ttft_s == 2.0
    assert _request_meets_slo(within, SLO_PRESETS["paper"])
    assert not _request_meets_slo(beyond, SLO_PRESETS["paper"])
