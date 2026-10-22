"""mpi4py.MPI is first imported with the interpreter's own libssl already loaded."""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "src" / "exaserve" / "mpi_loader.py"


def test_mpi_is_imported_after_the_interpreters_ssl(tmp_path):
    # A stand-in mpi4py records which modules were loaded when MPI imported.
    fake = tmp_path / "mpi4py"
    fake.mkdir()
    (fake / "__init__.py").write_text("")
    (fake / "MPI.py").write_text("import sys\nSSL_LOADED = '_ssl' in sys.modules\n")
    program = textwrap.dedent(
        f"""
        import hashlib, importlib.util, sys
        sys.path.insert(0, {str(tmp_path)!r})
        spec = importlib.util.spec_from_file_location("mpi_loader", {str(LOADER)!r})
        loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loader)
        before = "_ssl" in sys.modules
        MPI = loader.import_mpi()
        print(before, MPI.SSL_LOADED, MPI.__file__.startswith({str(tmp_path)!r}))
        """
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", program], capture_output=True, text=True, check=True
    )
    assert result.stdout.split() == ["False", "True", "True"]


def test_only_the_loader_imports_mpi4py():
    offenders = []
    for tree_root in (ROOT / "src", ROOT / "eval", ROOT / "clientlab", ROOT / "scripts"):
        for path in tree_root.rglob("*.py"):
            if "tests" in path.parts or path == LOADER:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                if any(name == "mpi4py" or name.startswith("mpi4py.") for name in names):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []
