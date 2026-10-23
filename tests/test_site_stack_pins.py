"""The server and paper extras pin the Aurora frameworks stack exactly.

An automated dependency update that bumps vLLM, Ray or Transformers in
pyproject.toml must fail here until the site stack is requalified and its lock
changes with it.
"""

from pathlib import Path
import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10; the test group pins tomli
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SITE_LOCK = ROOT / "requirements" / "aurora-frameworks-2025.3.1.lock"
EXACT_PIN = re.compile(r"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?==([^\s;]+)")


def _site_versions() -> dict[str, str]:
    versions = {}
    for line in SITE_LOCK.read_text(encoding="utf-8").splitlines():
        match = EXACT_PIN.fullmatch(line.split("#", 1)[0].strip())
        if match:
            # The site builds carry a local tag such as +xpu; the public pin does not.
            versions[match.group(1).lower()] = match.group(2).split("+", 1)[0]
    return versions


def test_exact_extra_pins_match_the_site_stack_lock() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    site = _site_versions()
    checked = []
    for extra in ("server", "paper"):
        for requirement in project["optional-dependencies"][extra]:
            match = EXACT_PIN.fullmatch(requirement)
            if not match or match.group(1).lower() not in site:
                continue
            name, version = match.group(1).lower(), match.group(2)
            assert version == site[name], (
                f"the {extra} extra pins {requirement}, but {SITE_LOCK.name} has {site[name]}; "
                "change both only when the site stack is requalified"
            )
            checked.append(name)
    assert {"ray", "vllm", "transformers"} <= set(checked)
