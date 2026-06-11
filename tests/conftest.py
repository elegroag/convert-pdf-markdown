"""Shared test fixtures and helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `src/` importable when running pytest from the repo root without
# an editable install.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    """Return a non-existent PDF path inside a temporary directory."""
    return tmp_path / "sample.pdf"


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Return a fresh output directory inside a temporary location."""
    out = tmp_path / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out
