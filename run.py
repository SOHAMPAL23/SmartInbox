"""
run.py
------
Uvicorn entry-point for the SmartInbox backend.

Run from the SmartInbox/ project ROOT directory:
    uvicorn run:app --reload --host 0.0.0.0 --port 8000

What this file does:
    1. Ensures the project root is on sys.path.
    2. Registers the `Backend` package as `app` in sys.modules so that
       all `from app.xxx import yyy` statements in the backend code resolve
       to Backend/xxx via Python's standard import machinery.
    3. Pre-registers every Backend sub-package (including nested ones like
       core.config, core.logging, auth.jwt_handler) to avoid lazy-import
       failures at request time.
    4. Imports the FastAPI app from Backend.main.
"""
import importlib
import pkgutil
import sys
from pathlib import Path

# ── 1. Ensure the project root is on sys.path ────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── 2. Register Backend as the 'app' package alias ───────────────────────────
import Backend  # noqa: E402  (must come after sys.path is set)

sys.modules["app"] = Backend


def _register_subpackages(backend_pkg_name: str, app_alias: str) -> None:
    """
    Walk every importable sub-module under `backend_pkg_name` and register
    each one under `app_alias.*` in sys.modules.

    This is required because Python resolves dotted imports lazily;
    without pre-registration a `from app.core.config import …` triggered
    inside middleware/services at import time will fail with ModuleNotFoundError.
    """
    try:
        pkg = importlib.import_module(backend_pkg_name)
    except ImportError:
        return

    sys.modules[app_alias] = pkg

    pkg_path = getattr(pkg, "__path__", None)
    if pkg_path is None:
        return  # not a package

    for finder, subname, ispkg in pkgutil.walk_packages(
        path=pkg_path,
        prefix=f"{backend_pkg_name}.",
        onerror=lambda name: None,
    ):
        try:
            submod = importlib.import_module(subname)
            alias = subname.replace(backend_pkg_name, app_alias, 1)
            sys.modules[alias] = submod
        except ImportError:
            pass  # gracefully skip modules that can't be loaded yet


_register_subpackages("Backend", "app")

# ── 3. Import the FastAPI application ─────────────────────────────────────────
from Backend import main as _main  # noqa: E402

# `app` is what uvicorn reads: `uvicorn run:app`
app = _main.app
