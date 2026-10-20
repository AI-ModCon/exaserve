"""Check local documentation links against the files available in a clean clone.

External URLs and fragment-only links are outside this offline check. Historical
capture paths belong in code spans, with their provenance explained in the text,
rather than links to ignored files on one developer's machine.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
ROOT_GUIDES = {"README.md", "AGENTS.md", "CONTRIBUTING.md", "scripts/hardening/README.md"}
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^>\s)]+)>?(?:\s+['\"].*?['\"])?\s*\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?([^>\s]+)>?")
CODE_SPAN = re.compile(r"(`+).*?\1")


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
    documents = sorted(
        name
        for name in tracked
        if name.endswith(".md") and (name.startswith("docs/") or name in ROOT_GUIDES)
    )
    problems = []
    checked = 0
    for name in documents:
        fence = ""
        for number, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith(("```", "~~~")):
                marker = stripped[0]
                fence = "" if fence == marker else (marker if not fence else fence)
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
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                pathname = unquote(parsed.path)
                checked += 1
                candidate = os.path.normpath((Path(name).parent / pathname).as_posix())
                if pathname.startswith("/") or candidate not in tracked | directories | {"."}:
                    problems.append(f"{name}:{number}: unavailable in a clean clone: {target}")
    for problem in problems:
        print(problem)
    print(
        f"Documentation links: {checked} local targets in {len(documents)} files; {len(problems)} problems"
    )
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
