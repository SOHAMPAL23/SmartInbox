"""
Vercel serverless entrypoint for FastAPI.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run import app

__all__ = ["app"]
