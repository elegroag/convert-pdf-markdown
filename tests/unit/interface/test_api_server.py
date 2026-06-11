"""Smoke tests for the FastAPI interface.

The API server is built lazily so the tests can run without the
optional fastapi/uvicorn dependencies installed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture
def api_module():
    """Import the API module, skipping if FastAPI is not installed."""
    try:
        return importlib.import_module("pdf2md.interface.api.server")
    except ImportError:
        pytest.skip("fastapi is not installed")


class TestApiServer:
    """The API module exposes a Typer-like ``app`` object."""

    def test_module_imports(self, api_module) -> None:
        assert hasattr(api_module, "app") or hasattr(api_module, "router")
