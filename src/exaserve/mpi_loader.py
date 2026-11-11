"""The one place a process first imports ``mpi4py.MPI``.

MPICH on Aurora links libcurl, and its DT_RPATH lists /usr/lib64, which the
loader searches before LD_LIBRARY_PATH, so loading libmpi also loads the OS
libssl. Since the 26.181.0 image that is SUSE's OpenSSL 3.5, which needs
SUSE-only symbols (OPENSSL_3.0.1) from libcrypto. An interpreter that ships
its own OpenSSL and has already loaded its libcrypto (hashlib does) then fails
the import with "version `OPENSSL_3.0.1' not found". Importing ``ssl`` first
loads the interpreter's libssl too; libcurl reuses it, so the process keeps
one OpenSSL. Staging ranks run with an explicit environment, so a preload set
in the site environment cannot reach them.
"""

from __future__ import annotations


def import_mpi():
    """Return ``mpi4py.MPI``, loading this interpreter's libssl first."""

    import ssl  # noqa: F401 - see the module docstring

    from mpi4py import MPI

    return MPI
