"""Interface layer (CLI + API).

The CLI is the primary interface and is always available. The FastAPI
server is loaded lazily on first access so the CLI does not require
FastAPI as a runtime dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pdf2md.interface import api, cli

__all__ = ["api", "cli"]


def __getattr__(name: str) -> Any:  # PEP 562 lazy module attribute
    """Lazily import submodules to avoid pulling FastAPI in CLI use."""
    import importlib

    if name in {"cli", "api"}:
        return importlib.import_module(f"pdf2md.interface.{name}")
    raise AttributeError(name)
