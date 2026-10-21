"""Repository-wide pytest bootstrap.

Single source-layout contract (WP0 / AC-TST-01): every test subtree must be
independently collectible, so the ``src/`` package root (``exaserve``) and the
repository root (``eval``, ``clientlab``) are placed on ``sys.path`` here and
nowhere else. Do not add per-directory conftest path hacks; child processes
that need the same contract must receive it explicitly (see
``eval/lib/run_planner.py`` subprocess environment).
"""

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

_TEST_PATHS = [REPO_ROOT]
if os.environ.get("EXASERVE_TEST_INSTALLED_WHEEL") != "1":
    _TEST_PATHS.append(os.path.join(REPO_ROOT, "src"))

for _path in _TEST_PATHS:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Hermeticity guard (WP0/WP11): unit tests must never reach live Hugging Face
# services, including from forkserver/spawn children (env is inherited). An
# integration job may pre-set these to "0" before invoking pytest.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# The package and the eval site configuration have no built-in allocation; tests
# that derive storage paths or render jobs use this neutral placeholder project.
os.environ.setdefault("EXASERVE_PROJECT_ROOT", "/lus/flare/projects/example-project")
os.environ.setdefault("EXASERVE_PROJECT_ACCOUNT", "example-project")


@pytest.fixture
def serve_module():
    """Load the optional Serve API only in environments that provide it.

    Portable CI deliberately excludes Ray/FastAPI. Tests of the real Serve
    graph run in the server environment; pure plan tests remain portable.
    """
    pytest.importorskip("ray", exc_type=ImportError)
    pytest.importorskip("fastapi", exc_type=ImportError)
    from exaserve import server

    return server
