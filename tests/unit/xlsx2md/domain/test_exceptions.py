"""Tests for xlsx2md domain exceptions."""

from __future__ import annotations

from xlsx2md.domain.exceptions import (
    CorruptedXlsxError,
    ExtractionError,
    RenderingError,
    StorageError,
    Xlsx2MdException,
)


class TestExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(CorruptedXlsxError, ExtractionError)
        assert issubclass(ExtractionError, Xlsx2MdException)
        assert issubclass(RenderingError, Xlsx2MdException)
        assert issubclass(StorageError, Xlsx2MdException)

    def test_message_attribute(self) -> None:
        exc = CorruptedXlsxError("bad file")
        assert exc.message == "bad file"
