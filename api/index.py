import importlib
import pkgutil
import sys
from pathlib import Path

# 1. Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2. Register Backend as 'app' alias for compatibility
import Backend  # noqa: E402

sys.modules["app"] = Backend


def _register_subpackages(backend_pkg_name: str, app_alias: str) -> None:
    try:
        pkg = importlib.import_module(backend_pkg_name)
    except ImportError:
        return

    sys.modules[app_alias] = pkg

    pkg_path = getattr(pkg, "__path__", None)
    if pkg_path is None:
        return

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
            pass


_register_subpackages("Backend", "app")

# 3. Import FastAPI app instance
from Backend.main import app  # noqa: E402
