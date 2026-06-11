"""API package — lazy import so the CLI does not require FastAPI.

The submodule ``server`` and the FastAPI ``app`` are loaded on first
attribute access. Importing :mod:`pdf2md.interface.api` itself is
safe and does not pull in FastAPI; if the dependency is missing,
attribute access returns ``None`` and ``hasattr`` reports ``False``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pdf2md.interface.api import server
    from pdf2md.interface.api.server import app

__all__ = ["app", "server"]


def __getattr__(name: str) -> Any:  # PEP 562
    if name in ("app", "server"):
        try:
            import importlib

            mod = importlib.import_module("pdf2md.interface.api.server")
        except ImportError:
            return None
        return mod.app if name == "app" else mod
    raise AttributeError(name)
