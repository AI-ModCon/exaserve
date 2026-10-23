"""The documentation link check reads headings as GitHub renders them and reports
every fragment that names no heading or HTML anchor."""

import importlib.util
from pathlib import Path
import subprocess

import pytest

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


@pytest.mark.parametrize(
    "text, anchors",
    [
        pytest.param("Title\n=====\n\nSub title\n---\n", {"title", "sub-title"}, id="setext"),
        # A soft line break renders as a newline, which the slug drops.
        pytest.param(
            "First line\nsecond line\n===\n", {"first-linesecond-line"}, id="setext-lines"
        ),
        pytest.param(
            "---\nname: Bug report\nlabels: bug\n---\n\n## Steps\n", {"steps"}, id="front-matter"
        ),
        pytest.param(
            "## _Emphasis_, *star*, **strong** and __bold__\n",
            {"emphasis-star-strong-and-bold"},
            id="emphasis",
        ),
        pytest.param(
            "## __init__.py and snake_case_name\n",
            {"initpy-and-snake_case_name"},
            id="intraword-underscores",
        ),
        pytest.param(
            "## The `_kept_` and `__init__` names\n",
            {"the-_kept_-and-__init__-names"},
            id="code-spans",
        ),
        pytest.param("## Image ![alt text](x.png) here\n", {"image--here"}, id="image"),
        pytest.param("## ![logo](logo.png) Project\n", {"-project"}, id="leading-image"),
        pytest.param(
            "## [Inline](a.md), [reference][ref] and [shortcut]\n\n[ref]: b.md\n[shortcut]: c.md\n",
            {"inline-reference-and-shortcut"},
            id="links",
        ),
        pytest.param("## [Text][nowhere]\n", {"textnowhere"}, id="undefined-reference"),
        pytest.param("## Fish &amp; chips&#95;\n", {"fish--chips_"}, id="entities"),
        pytest.param(
            "> ## Quoted\n>\n> Quoted setext\n> ---\n", {"quoted", "quoted-setext"}, id="blockquote"
        ),
        # An underline cannot continue a paragraph lazily, and --- after a list
        # item is a thematic break.
        pytest.param("> Lazy\ncontinuation\n---\n", set(), id="lazy-blockquote"),
        pytest.param("- item\n---\n", set(), id="list-item"),
        pytest.param("````\n```\n# inside\n```\n````\n## After\n", {"after"}, id="longer-fence"),
        pytest.param(
            "```\n# a\n```python\n# b\n~~~\n# c\n```\n## After\n", {"after"}, id="fence-closing"
        ),
        pytest.param(
            '<!-- one line -->\n## First\n<!--\n## Hidden\n<a id="hidden"></a>\n-->\n## Second\n',
            {"first", "second"},
            id="html-comments",
        ),
        pytest.param(
            "## Notes\n## Notes 1\n## Notes\n", {"notes", "notes-1", "notes-2"}, id="duplicates"
        ),
    ],
)
def test_heading_anchors_follow_github_rendering(tmp_path, monkeypatch, text, anchors) -> None:
    checker = _checker()
    (tmp_path / "doc.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    assert checker._anchors("doc.md") == anchors


def test_a_footnote_definition_is_not_a_link() -> None:
    checker = _checker()
    assert checker.REFERENCE_LINK.match("[^1]: See the appendix") is None
    assert checker.REFERENCE_LINK.match("[guide]: docs/guide.md")["target"] == "docs/guide.md"


def _repository(tmp_path, monkeypatch, documents):
    """Track the documents in a new git repository and point the checker at it."""
    for variable in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(variable, raising=False)
    for name, text in documents.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    for command in (["init", "-q"], ["add", *documents]):
        subprocess.run(["git", *command], cwd=tmp_path, check=True, capture_output=True)
    checker = _checker()
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    return checker


def test_main_reports_each_missing_fragment(tmp_path, monkeypatch, capsys) -> None:
    checker = _repository(
        tmp_path,
        monkeypatch,
        {
            "README.md": "# Guide\n\n## Setup\n\n"
            "[setup](#setup) and [missing](#missing)\n\n"
            "[usage](docs/usage.md#running) and [nope](docs/usage.md#nope)\n",
            "docs/usage.md": "# Usage\n\n## Running\n",
        },
    )
    assert checker.main() == 1
    assert capsys.readouterr().out.splitlines() == [
        "README.md:5: no such heading: #missing",
        "README.md:7: no such heading: docs/usage.md#nope",
        "Documentation links: 4 local targets in 2 files; 2 problems",
    ]


def test_main_passes_valid_fragments(tmp_path, monkeypatch, capsys) -> None:
    checker = _repository(
        tmp_path,
        monkeypatch,
        {
            "README.md": "## Setup\n\n[setup](#setup) and [usage](docs/usage.md#running)\n",
            "docs/usage.md": "Running\n=======\n",
        },
    )
    assert checker.main() == 0
    assert capsys.readouterr().out.splitlines() == [
        "Documentation links: 2 local targets in 2 files; 0 problems"
    ]


def test_main_skips_links_that_github_does_not_render(tmp_path, monkeypatch, capsys) -> None:
    checker = _repository(
        tmp_path,
        monkeypatch,
        {
            "README.md": "<!--\n[hidden](#nowhere)\n-->\n\n"
            "````\n```\n[code](#nowhere)\n```\n````\n\n"
            "Text.[^1]\n\n[^1]: See the appendix\n",
        },
    )
    assert checker.main() == 0
    assert capsys.readouterr().out.splitlines() == [
        "Documentation links: 0 local targets in 1 files; 0 problems"
    ]
