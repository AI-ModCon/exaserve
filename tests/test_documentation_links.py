"""Heading anchors used by the documentation link check follow GitHub's rules."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_documentation_links.py"


def _checker():
    spec = importlib.util.spec_from_file_location("check_documentation_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_heading_anchors_follow_github_rules(tmp_path, monkeypatch) -> None:
    checker = _checker()
    (tmp_path / "doc.md").write_text(
        "# A3. Ray `serve.run` limits\n\n"
        "## Notes\n\n"
        "## Notes\n\n"
        "```\n# not a heading\n```\n\n"
        '<a id="custom"></a>\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    checker._anchors.cache_clear()
    assert checker._anchors("doc.md") == {"a3-ray-serverun-limits", "notes", "notes-1", "custom"}
