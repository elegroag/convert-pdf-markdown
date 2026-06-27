"""Tests for docx2md domain exceptions."""

from __future__ import annotations

from docx2md.domain.exceptions import (
    ConfigurationError,
    CorruptedDocxError,
    Docx2MdException,
    ExtractionError,
    RenderingError,
    StorageError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(ExtractionError, Docx2MdException)
    assert issubclass(CorruptedDocxError, ExtractionError)
    assert issubclass(RenderingError, Docx2MdException)
    assert issubclass(StorageError, Docx2MdException)
    assert issubclass(ConfigurationError, Docx2MdException)
