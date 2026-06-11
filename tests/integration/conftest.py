"""Shared fixtures for integration tests against real PDF fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.extractors.pdfplumber_extractor import (
    PdfplumberTableExtractor,
)
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor
from pdf2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer

_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "pdfs"


@pytest.fixture
def pdf_path() -> callable:
    """Return a function that resolves a PDF fixture by filename.

    Skips the test if the fixture file does not exist.
    """
    def _resolve(name: str) -> Path:
        path = FIXTURES_DIR / name
        if not path.is_file():
            pytest.skip(f"fixture not found: {path}")
        return path
    return _resolve


@pytest.fixture
def full_extractor() -> PyMuPdfExtractor:
    """Return a PyMuPdfExtractor with all features enabled.

    Uses a low ``image_min_size`` (50) so that the small fixture
    images (120×120) are extracted during integration tests.
    """
    return PyMuPdfExtractor(
        config=ConversionConfig(
            extract_images=True,
            extract_tables=True,
            extract_links=True,
            frontmatter=True,
            image_min_size=50,
        ),
        table_extractor=PdfplumberTableExtractor(),
    )


@pytest.fixture
def default_extractor() -> PyMuPdfExtractor:
    """Return a PyMuPdfExtractor with default production config.

    Uses the production default ``image_min_size=200`` to test
    real-world filtering behaviour.
    """
    return PyMuPdfExtractor(
        config=ConversionConfig(
            extract_images=True,
            extract_tables=True,
            extract_links=True,
            frontmatter=True,
        ),
        table_extractor=PdfplumberTableExtractor(),
    )


@pytest.fixture
def text_only_extractor() -> PyMuPdfExtractor:
    """Return a PyMuPdfExtractor with optional features disabled."""
    return PyMuPdfExtractor(
        config=ConversionConfig(
            extract_images=False,
            extract_tables=False,
            extract_links=False,
            frontmatter=False,
        )
    )


@pytest.fixture
def renderer() -> MarkdownRenderer:
    """Return a default MarkdownRenderer."""
    return MarkdownRenderer()
