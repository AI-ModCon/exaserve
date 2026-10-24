"""Exercise the synthetic server's actual HTTP framing parser."""

from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.fixture(scope="module")
def header_parser(tmp_path_factory):
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("C++ compiler is unavailable")
    source = Path(__file__).resolve().parents[1] / "targets" / "cpp_server"
    build = tmp_path_factory.mktemp("http-header-parser")
    harness = build / "main.cpp"
    harness.write_text(
        '#include "handler.hpp"\n'
        "#include <iostream>\n"
        "#include <iterator>\n"
        "int main() {\n"
        "  std::string input(std::istreambuf_iterator<char>(std::cin), {});\n"
        "  ParsedRequest request;\n"
        "  size_t offset = 0;\n"
        "  bool complete = parse_headers(input.data(), input.size(), request, offset);\n"
        "  std::cout << complete << ' ' << request.malformed << ' '\n"
        "            << request.content_length << ' ' << request.keep_alive;\n"
        "}\n",
        encoding="utf-8",
    )
    binary = build / "parse-headers"
    subprocess.run(
        [
            compiler,
            "-std=c++20",
            "-I",
            str(source),
            str(harness),
            str(source / "handler.cpp"),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return binary


def _parse(binary, headers):
    result = subprocess.run(
        [str(binary)],
        input="POST /v1/completions HTTP/1.1\r\n" + headers + "\r\n\r\n",
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return tuple(int(value) for value in result.stdout.split())


@pytest.mark.parametrize(
    ("headers", "length", "keep_alive"),
    [
        ("Content-Length: 12", 12, 1),
        ("content-length:\t12 \t\r\nConnection: close", 12, 0),
        ("Content-Length: 0", 0, 1),
        ("X-Content-Length: 99\r\nContent-Length: 12", 12, 1),
        ("X-Transfer-Encoding: chunked\r\nContent-Length: 12", 12, 1),
    ],
)
def test_valid_body_boundaries(header_parser, headers, length, keep_alive):
    assert _parse(header_parser, headers) == (1, 0, length, keep_alive)


@pytest.mark.parametrize(
    "headers",
    [
        "Content-Length:",
        "Content-Length: -1",
        "Content-Length: 99999999999999999999999999999999999",
        "Content-Length: 12garbage",
        "Content-Length: 12 3",
        "Content-Length: 12, 13",
        "Content-Length: 12\r\nContent-Length: 13",
        "Transfer-Encoding: chunked",
        "Transfer-Encoding: chunked\r\nContent-Length: 12",
    ],
)
def test_unusable_body_boundaries_are_rejected(header_parser, headers):
    complete, malformed, _length, _keep_alive = _parse(header_parser, headers)
    assert (complete, malformed) == (1, 1)
