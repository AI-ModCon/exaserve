"""The BurstGPT fetch uses only the release file it names."""

from __future__ import annotations

import pytest

from eval.tools import fetch_paper_datasets as fetch


def test_burstgpt_download_failure_stops_without_another_source(tmp_path, monkeypatch):
    calls = []

    def failing_download(url, dest):
        calls.append(url)
        raise OSError("network down")

    monkeypatch.setattr(fetch, "_download", failing_download)
    with pytest.raises(OSError, match="network down"):
        fetch.fetch_burstgpt(tmp_path)
    assert calls == [fetch.BURSTGPT_URL]
    assert not (tmp_path / "input_traces" / "BurstGPT_without_fails_1.csv").exists()
