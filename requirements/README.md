# Dependency profiles

`ci.lock` is the exact portable Python dependency set for hermetic tests,
wheel tests, lint, coverage, and the selected typed-core check. Existing pins
are retained; dependency updates must deliberately update this file and the
root `pyproject.toml` development/test groups, then regenerate `uv.lock`.
CI checks that a locked uv environment matches every applicable `ci.lock`
pin. The independent installed-wheel gate continues to install `ci.lock`
with pip before installing the audited ExaServe wheel with `--no-deps`.

The root `uv.lock` is generated with **uv 0.13.4**. Default `uv sync` selects
only the portable `dev` and `test` dependency groups, not the optional
`server`, `proxy`, `scheduler`, `eval`, or `paper` extras. The lock resolves
optional dependency metadata too, so it can list GPU packages that are not
installed in the default environment. It is not an Aurora installation
recipe or a claim that those packages are qualified on another platform.

The uv resolution envelope is Linux with Python 3.11 to 3.13. The upper bound
comes from the existing exact vLLM dependency, which uv must resolve even though
portable sync does not install it. The lower bound comes from Pillow 13.0.0, the
first release without its known advisories, which requires Python 3.11; the
published package metadata still accepts Python 3.10, but the lock does not
cover it. Portable CI targets **Python 3.12**, matching Aurora's
current Python 3.12.12 runtime; other interpreters are outside the current CI
scope and are not qualified by the lock's wider resolution envelope.

Use `make install-dev` for a locked portable environment and `make lock-check`
to check freshness without changing it. To intentionally refresh metadata,
use `make lock` (`uv lock --no-build --no-python-downloads`), then review the
lock and pin changes. No third-party source builds or GPU installation are
needed for this metadata workflow. Do not use `uv sync --all-extras` for
portable development. Evaluate markers in exported requirements for the
selected Python 3.12 interpreter rather than comparing inactive backports.

`aurora-frameworks-2025.3.1.lock` records the exact heavy stack supplied by
ALCF. It is verified at runtime by `CompatibilityProfile`; it is not a PyPI
recipe because the XPU wheels are site-built. Python itself is pinned by that
profile to 3.12.12, and the replay/staging MPI API is bound to the listed
mpi4py distribution. A new site stack requires a new lock, compatibility
profile, source hashes, semantic probes, and qualification evidence.

Pytest plugin autoload is disabled in CI. Fixed-order coverage tests explicitly
load `pytest_cov`; the randomized job explicitly loads `pytest-randomly` and
prints its replayable seed. The independent installed-wheel suite does not
enable coverage or randomized ordering. Coverage is for the portable
`exaserve`, `eval`, and `clientlab` Python surfaces, not live GPU, MPI, or scale
qualification. Each fixed-order Python job uploads its XML report as a GitHub
Actions artifact; no Codecov account or secret is required.

The root Makefile preserves the audited `build_release_artifacts.py` path;
`make build` does not replace it with a generic wheel build. Its output
directory must be new or empty (`BUILD_OUTPUT=...` selects another directory).
There is no destructive cleanup target.

On Aurora, full `make test`, `make test-cov`, and `make build` runs belong in a
validated compute session, not on a login node. Follow the safety rules in
[`AGENTS.md`](../AGENTS.md) and the
[Aurora setup guide](../docs/getting_started.md#aurora-development-and-serving)
for a scheduler-created interactive PBS allocation, toolchain setup, and
separation of the portable environment from the site-provided serving runtime.
These targets check allocation membership and interactive/legacy lease markers
on Aurora; the check neither obtains resources nor replaces the required
session and environment preflight. Generic developer machines and hosted CI
do not require an Aurora allocation.
