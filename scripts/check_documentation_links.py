"""Check local documentation links against the files available in a clean clone.

Every tracked Markdown file is checked. A link to a local file must name a tracked
file or directory, and a ``#fragment`` on a link to a Markdown file (or a
fragment-only link) must name a heading or an HTML anchor in that file, using
GitHub's anchor rules. External URLs are outside this offline check. Historical
capture paths belong in code spans, with their provenance explained in the text,
rather than links to ignored files on one developer's machine.
"""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^>\s)]+)>?(?:\s+['\"].*?['\"])?\s*\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?([^>\s]+)>?")
CODE_SPAN = re.compile(r"(`+).*?\1")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
HTML_ANCHOR = re.compile(r"<a\s+(?:[^>]*?\s)?(?:id|name)=\"([^\"]+)\"")


def _fence(stripped: str, fence: str) -> str | None:
    """Return the new fence state if this line opens or closes a code fence."""
    if not stripped.startswith(("```", "~~~")):
        return None
    marker = stripped[0]
    return "" if fence == marker else (marker if not fence else fence)


def _slug(text: str) -> str:
    """GitHub's heading anchor: rendered text, lowercased, punctuation dropped."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


@lru_cache(maxsize=None)
def _anchors(name: str) -> frozenset[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    fence = ""
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        state = _fence(line.lstrip(), fence)
        if state is not None:
            fence = state
            continue
        if fence:
            continue
        anchors.update(HTML_ANCHOR.findall(line))
        heading = HEADING.match(line)
        if heading:
            base = _slug(heading.group(2))
            count = seen.get(base, 0)
            anchors.add(base if count == 0 else f"{base}-{count}")
            seen[base] = count + 1
    return frozenset(anchors)


def main() -> int:
    tracked = {
        name
        for name in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT, text=True).split(
            "\0"
        )
        if name
    }
    directories = {
        parent.as_posix()
        for name in tracked
        for parent in Path(name).parents
        if parent != Path(".")
    }
    documents = sorted(name for name in tracked if name.endswith(".md"))
    problems = []
    checked = 0
    for name in documents:
        fence = ""
        for number, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), 1):
            state = _fence(line.lstrip(), fence)
            if state is not None:
                fence = state
                continue
            if fence:
                continue
            # Preserve the link's target when its label contains a code span.
            # Match links first, then exclude a whole link written as code.
            spans = [match.span() for match in CODE_SPAN.finditer(line)]
            matches = list(INLINE_LINK.finditer(line))
            reference = REFERENCE_LINK.match(line)
            if reference:
                matches.append(reference)
            for match in matches:
                if any(start <= match.start() and match.end() <= end for start, end in spans):
                    continue
                target = match.group(1)
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc:
                    continue
                fragment = unquote(parsed.fragment)
                if not parsed.path:
                    if fragment:
                        checked += 1
                        if fragment not in _anchors(name):
                            problems.append(f"{name}:{number}: no such heading: {target}")
                    continue
                pathname = unquote(parsed.path)
                checked += 1
                candidate = os.path.normpath((Path(name).parent / pathname).as_posix())
                if pathname.startswith("/") or candidate not in tracked | directories | {"."}:
                    problems.append(f"{name}:{number}: unavailable in a clean clone: {target}")
                elif fragment and candidate.endswith(".md") and candidate in tracked:
                    if fragment not in _anchors(candidate):
                        problems.append(f"{name}:{number}: no such heading: {target}")
    for problem in problems:
        print(problem)
    print(
        f"Documentation links: {checked} local targets in {len(documents)} files; {len(problems)} problems"
    )
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
