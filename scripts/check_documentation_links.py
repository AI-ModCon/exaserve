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
import html
from html.entities import html5
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?(?P<target>[^>\s)]+)>?(?:\s+['\"].*?['\"])?\s*\)")
# A footnote definition such as "[^1]: See the appendix" is not a link.
REFERENCE_LINK = re.compile(r"^\s{0,3}\[(?!\^)(?P<label>[^\]]+)\]:\s*<?(?P<target>[^>\s]+)>?")
CODE_SPAN = re.compile(r"(`+).*?\1")
HTML_ANCHOR = re.compile(r"<a\s+(?:[^>]*?\s)?(?:id|name)=\"([^\"]+)\"")

# Block structure as GitHub's renderer, cmark-gfm, reads it. A fence may be indented
# by any amount, so that fences inside list items are found.
QUOTE_MARKER = re.compile(r" {0,3}> ?")
FENCE = re.compile(r"\s*(`{3,}|~{3,})(.*)")
FENCE_CLOSE = re.compile(r"\s*(`{3,}|~{3,})[ \t]*$")
ATX_HEADING = re.compile(r" {0,3}#{1,6}(?:[ \t]+|$)(.*)")
SETEXT_UNDERLINE = re.compile(r" {0,3}(?:=+|-+)[ \t]*$")
THEMATIC_BREAK = re.compile(r" {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
LIST_ITEM = re.compile(r" {0,3}(?:[-+*]|(\d{1,9})[.)])(?:[ \t]+|$)")
TABLE_DELIMITER = re.compile(r" {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")

# Inline structure as GitHub's cmark-gfm parses it, reduced to what reaches an anchor.
ASCII_PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
BACKTICKS = re.compile(r"`+")
ENTITY = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
AUTOLINK = re.compile(
    r"<([A-Za-z][A-Za-z0-9+.\-]{1,31}:[^\s<>]*"
    r"|[A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)*)>"
)
RAW_HTML = re.compile(
    r"<(?:[A-Za-z][A-Za-z0-9\-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:\-]*"
    r"(?:\s*=\s*(?:[^\s\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*\s*/?>"
    r"|/[A-Za-z][A-Za-z0-9\-]*\s*>|!--(?!-?>)(?:-?[^-])*-->|\?.*?\?>"
    r"|![A-Z]+\s[^>]*>|!\[CDATA\[.*?\]\]>)",
    re.S,
)
LINK_SPACE = re.compile(r"[ \t\n\v\f\r]*")
LINK_DESTINATION = re.compile(r"<(?:\\[\s\S]|[^\n<>\\])*>")
LINK_TITLE = re.compile(r"\"(?:\\[\s\S]|[^\"])*\"|'(?:\\[\s\S]|[^'])*'|\((?:\\[\s\S]|[^()])*\)")
LINK_LABEL = re.compile(r"\[((?:[^\[\]\\]|\\.){0,999})\]", re.S)


def _unquote(line: str, limit: int | None = None) -> tuple[int, str]:
    """Strip up to ``limit`` block quote markers; return their number and the rest."""
    depth = 0
    while limit is None or depth < limit:
        marker = QUOTE_MARKER.match(line)
        if marker is None:
            break
        line = line[marker.end() :]
        depth += 1
    return depth, line


def _closes(fence: str, line: str) -> bool:
    """Whether a line ends an open code fence, or an HTML comment when fence is empty."""
    if not fence:
        return "-->" in line
    closing = FENCE_CLOSE.match(line)
    return bool(closing) and closing[1][0] == fence[0] and len(closing[1]) >= len(fence)


def _markdown(text: str) -> tuple[list[tuple[int, str]], list[str], set[str]]:
    """Read a document's blocks as GitHub renders them.

    Returns the numbered lines shown as Markdown, without block quote markers
    (YAML front matter, fenced code and HTML comment blocks are left out), the
    inline source of each ATX or setext heading in document order, and the
    labels of the link reference definitions.
    """
    lines = text.splitlines()
    start = 0
    if lines and lines[0].rstrip() == "---":
        # Front matter renders as a table, so its closing --- underlines nothing.
        start = next(
            (number for number, line in enumerate(lines[1:], 2) if line.rstrip() in ("---", "...")),
            0,
        )
    shown: list[tuple[int, str]] = []
    headings: list[str] = []
    labels: set[str] = set()
    block: tuple[int, str] | None = None  # quote depth and fence of open code or a comment
    paragraph: list[str] | None = None
    paragraph_depth = 0
    kind = "text"  # the open paragraph's kind: "text", a list "item" or a "table"
    for number, line in enumerate(lines[start:], start + 1):
        if block is not None:
            depth, content = _unquote(line, block[0])
            if depth == block[0]:
                if _closes(block[1], content):
                    block = None
                continue
            block = None  # the block quote holding it has ended
        depth, content = _unquote(line)
        # A line with fewer quote markers continues a paragraph lazily, not a table.
        lazy = paragraph is not None and depth < paragraph_depth
        if paragraph is not None and (depth > paragraph_depth or (lazy and kind == "table")):
            paragraph, lazy = None, False
        if not content.strip():
            paragraph = None
            continue
        fence = FENCE.match(content)
        if fence and not (fence[1][0] == "`" and "`" in fence[2]):
            block, paragraph = (depth, fence[1]), None
            continue
        if content.lstrip().startswith("<!--"):
            if "-->" not in content:
                block = (depth, "")
            paragraph = None
            continue
        shown.append((number, content))
        heading = ATX_HEADING.match(content)
        if heading:
            headings.append(re.sub(r"(?:^|[ \t]+)#+[ \t]*$", "", heading[1]).strip(" \t"))
            paragraph = None
            continue
        if paragraph and kind == "text" and not lazy and SETEXT_UNDERLINE.match(content):
            # Link reference definitions at its start are not part of the heading.
            while paragraph and REFERENCE_LINK.match(paragraph[0]):
                del paragraph[0]
            if paragraph:
                headings.append("\n".join(paragraph).strip())
                paragraph = None
                continue
        if THEMATIC_BREAK.match(content):
            paragraph = None
            continue
        item = LIST_ITEM.match(content)
        # Only a nonempty item, numbered 1 if ordered, may interrupt a paragraph.
        if item and (
            paragraph is None
            or lazy
            or kind != "text"
            or (int(item[1] or 1) == 1 and content[item.end() :].strip())
        ):
            # An unindented --- after a list item is a thematic break, and this
            # model does not track the item's indentation, so no underline here.
            # An empty item holds no paragraph for the next line to continue.
            paragraph = [] if content[item.end() :].strip() else None
            paragraph_depth, kind = depth, "item"
            continue
        if paragraph is not None:
            if kind == "text" and not lazy and "|" in content and TABLE_DELIMITER.match(content):
                kind = "table"  # its rows run to the next blank line
            paragraph.append(content.lstrip())
        elif len(content.expandtabs(4)) - len(content.expandtabs(4).lstrip()) >= 4:
            continue  # indented code
        else:
            paragraph, paragraph_depth, kind = [content.lstrip()], depth, "text"
        # Link reference definitions start a paragraph; one inside it is text.
        if kind == "text" and all(map(REFERENCE_LINK.match, paragraph)):
            labels.add(_label(REFERENCE_LINK.match(paragraph[-1])["label"]))
    return shown, headings, labels


def _space(char: str) -> bool:
    return char in "\t\n\f\r" or unicodedata.category(char) == "Zs"


def _punctuation(char: str) -> bool:
    return char in ASCII_PUNCTUATION or unicodedata.category(char).startswith("P")


def _label(text: str) -> str:
    return " ".join(text.split()).casefold()


def _decode(entity: str) -> str:
    """The text of an HTML entity; a named one counts only when complete."""
    return html.unescape(entity) if entity[1] == "#" or entity[1:] in html5 else entity


def _link_tail(text: str, start: int) -> int | None:
    """Where an inline link's (destination "title") that starts at text[start] ends.

    As in cmark-gfm, a bare destination runs to whitespace or an unmatched ")" and
    may leave a "(" open, but it may not run to the end of the text.
    """
    if not text.startswith("(", start):
        return None
    index = LINK_SPACE.match(text, start + 1).end()
    if text.startswith("<", index):
        destination = LINK_DESTINATION.match(text, index)
        if destination is None:
            return None
        index = destination.end()
    else:
        depth = 0
        while index < len(text) and text[index] not in " \t\n\v\f\r":
            char = text[index]
            if char == "\\" and text[index + 1 : index + 2] in ASCII_PUNCTUATION:
                index += 1
            elif char == "(":
                depth += 1
                if depth > 32:
                    return None
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            index += 1
    if index >= len(text):
        return None
    end = LINK_SPACE.match(text, index).end()
    title = LINK_TITLE.match(text, end) if end > index else None
    if title:
        end = LINK_SPACE.match(text, title.end()).end()
    return end + 1 if text.startswith(")", end) else None


def _pairs(opener: list, closer: list) -> bool:
    """Whether a delimiter run can open the emphasis that ``closer`` ends."""
    # Rule of 3: when either run can both open and close, the lengths of the two
    # runs must not sum to a multiple of 3 unless both are multiples of 3.
    return (
        opener[0] == closer[0]
        and opener[2]
        and not (
            (opener[3] or closer[2])
            and (opener[4] + closer[4]) % 3 == 0
            and (opener[4] % 3 or closer[4] % 3)
        )
    )


def _emphasis(pieces: list, bottom: int) -> None:
    """Pair the delimiter runs in pieces[bottom:] as cmark-gfm's "process emphasis"
    does and replace each run with the delimiter characters it has left."""
    stack = [index for index in range(bottom, len(pieces)) if isinstance(pieces[index], list)]
    # cmark-gfm's openers_bottom: once a closer finds no opener, later closers of
    # the same character and length mod 3 search no further back than it.
    floors: dict[tuple[str, int], int] = {}
    current = 0
    while current < len(stack):
        closer = pieces[stack[current]]
        floor = floors.get((closer[0], closer[4] % 3), bottom)
        openers = range(current - 1, -1, -1) if closer[3] else range(0)
        found = next(
            (
                back
                for back in openers
                if stack[back] >= floor and _pairs(pieces[stack[back]], closer)
            ),
            None,
        )
        if found is None:
            if closer[3]:
                floors[(closer[0], closer[4] % 3)] = stack[current]
            if closer[3] and not closer[2]:
                del stack[current]
            else:
                current += 1
            continue
        opener = pieces[stack[found]]
        if closer[0] == "~":
            opener[1] = closer[1] = 0  # strikethrough; tildes never reach a slug
        else:
            used = 2 if opener[1] >= 2 and closer[1] >= 2 else 1
            opener[1] -= used
            closer[1] -= used
        del stack[found + 1 : current]
        current = found + 1
        if opener[1] == 0:
            del stack[found]
            current -= 1
        if closer[1] == 0:
            del stack[current]
    for index in range(bottom, len(pieces)):
        if isinstance(pieces[index], list):
            pieces[index] = pieces[index][0] * pieces[index][1]


def _render(text: str, labels: set[str]) -> str:
    """The text GitHub renders for a heading's inline Markdown.

    This is cmark-gfm's inline algorithm reduced to what reaches an anchor: code
    spans keep their contents, emphasis delimiters that pair up are dropped (an
    intraword "_" stays), links keep their text, images and raw HTML render no
    text, and backslash escapes and HTML entities are decoded.
    """
    pieces: list = []  # text, or a delimiter run [character, count, opens, closes, length]
    brackets: list = []  # "[" or "![": [piece, text start, image, active, bracket after]
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and text[index + 1 : index + 2] in ASCII_PUNCTUATION:
            pieces.append(text[index + 1])
            index += 2
        elif char == "`":
            run = BACKTICKS.match(text, index)[0]
            closing = re.compile(rf"(?<!`){run}(?!`)").search(text, index + len(run))
            if closing is None:
                pieces.append(run)
                index += len(run)
                continue
            code = text[index + len(run) : closing.start()].replace("\n", " ")
            if code[:1] == code[-1:] == " " and code.strip(" "):
                code = code[1:-1]
            pieces.append(code)
            index = closing.end()
        elif char == "&" and (entity := ENTITY.match(text, index)):
            pieces.append(_decode(entity[0]))
            index = entity.end()
        elif char == "<" and (link := AUTOLINK.match(text, index)):
            # An autolink shows its address.
            pieces.append(ENTITY.sub(lambda match: _decode(match[0]), link[1]))
            index = link.end()
        elif char == "<" and (tag := RAW_HTML.match(text, index)):
            index = tag.end()  # raw HTML shows no text
        elif char in "*_~":
            end = index
            while end < len(text) and text[end] == char:
                end += 1
            back, ahead = index - 1, end
            if char != "~":
                # cmark-gfm looks past strikethrough tildes beside a "*" or "_" run.
                while back > 0 and text[back] == "~":
                    back -= 1
                while ahead < len(text) and text[ahead] == "~":
                    ahead += 1
            before = text[back] if back >= 0 and text[back] != "~" else "\n"
            after = text[ahead] if ahead < len(text) and text[ahead] != "~" else "\n"
            opens = not _space(after) and (
                not _punctuation(after) or _space(before) or _punctuation(before)
            )
            closes = not _space(before) and (
                not _punctuation(before) or _space(after) or _punctuation(after)
            )
            if char == "_":
                opens, closes = (
                    opens and (not closes or _punctuation(before)),
                    closes and (not opens or _punctuation(after)),
                )
            if char == "~" and end - index > 2:
                pieces.append(text[index:end])
            else:
                pieces.append([char, end - index, opens, closes, end - index])
            index = end
        elif char == "[" or (char == "!" and text.startswith("[", index + 1)):
            if brackets:
                brackets[-1][4] = True
            index += 1 if char == "[" else 2
            brackets.append([len(pieces), index, char == "!", True, False])
            pieces.append("[" if char == "[" else "![")
        elif char == "]" and brackets:
            opener = brackets.pop()
            tail = _link_tail(text, index + 1)
            label = LINK_LABEL.match(text, index + 1)
            end = None
            if opener[3] and tail is not None:
                end = tail
            elif opener[3] and label and label[1].strip():
                end = label.end() if _label(label[1]) in labels else None
            elif opener[3] and not opener[4] and _label(text[opener[1] : index]) in labels:
                end = label.end() if label else index + 1
            if end is None:
                pieces.append("]")
                index += 1
                continue
            _emphasis(pieces, opener[0] + 1)
            inner = pieces[opener[0] + 1 :]
            del pieces[opener[0] :]
            if not opener[2]:
                pieces.extend(inner)
                for bracket in brackets:
                    bracket[3] = bracket[3] and bracket[2]  # no links inside a link
            index = end
        elif char == "\n":
            # Spaces just before a line break are dropped; each is one text piece.
            del pieces[len(pieces) - (index - len(text[:index].rstrip(" \t"))) :]
            pieces.append("\n")
            index += 1
        else:
            pieces.append(char)
            index += 1
    _emphasis(pieces, 0)
    return "".join(pieces)


def _slug(text: str) -> str:
    """GitHub's anchor for rendered heading text, as github-slugger computes it.

    Lowercase; keep letters, marks, digits, connector punctuation such as "_",
    hyphens and spaces; drop everything else; and turn each space into a hyphen.
    """
    return "".join(
        "-" if char == " " else char
        for char in text.lower()
        if char in " -\u200c\u200d"
        or unicodedata.category(char).startswith(("L", "M", "Nd", "Nl", "Pc"))
    )


@lru_cache(maxsize=None)
def _anchors(name: str) -> frozenset[str]:
    shown, headings, labels = _markdown((ROOT / name).read_text(encoding="utf-8"))
    anchors = {
        anchor for _, line in shown for anchor in HTML_ANCHOR.findall(CODE_SPAN.sub("", line))
    }
    slugs: dict[str, int] = {}
    for heading in headings:
        slug = base = _slug(_render(heading, labels))
        # Like github-slugger, count on from the base until the slug is unused.
        while slug in slugs:
            slugs[base] += 1
            slug = f"{base}-{slugs[base]}"
        slugs[slug] = 0
    return frozenset(anchors.union(slugs))


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
        for number, line in _markdown((ROOT / name).read_text(encoding="utf-8"))[0]:
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
                target = match["target"]
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
