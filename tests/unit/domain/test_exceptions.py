"""Tests for domain exceptions."""

from __future__ import annotations

import pytest

from pdf2md.domain.exceptions import (
    ConfigurationError,
    CorruptedPdfError,
    EncryptedPdfError,
    ExtractionError,
    ImageExtractionError,
    Pdf2MdException,
    RenderingError,
    StorageError,
    TableExtractionError,
)


class TestExceptionHierarchy:
    """All pdf2md exceptions inherit from :class:`Pdf2MdException`."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            Pdf2MdException,
            ExtractionError,
            EncryptedPdfError,
            CorruptedPdfError,
            TableExtractionError,
            ImageExtractionError,
            RenderingError,
            StorageError,
            ConfigurationError,
        ],
    )
    def test_inherits_from_base(self, exc_cls) -> None:
        """Every exception class is a subclass of Pdf2MdException."""
        assert issubclass(exc_cls, Pdf2MdException)

    def test_encrypted_is_extraction_error(self) -> None:
        """EncryptedPdfError is a specific extraction failure."""
        assert issubclass(EncryptedPdfError, ExtractionError)

    def test_corrupted_is_extraction_error(self) -> None:
        """CorruptedPdfError is a specific extraction failure."""
        assert issubclass(CorruptedPdfError, ExtractionError)

    def test_message_preserved(self) -> None:
        """The exception's message is stored on the instance."""
        exc = CorruptedPdfError("oops")
        assert exc.message == "oops"
        assert str(exc) == "oops"

    def test_can_wrap_cause(self) -> None:
        """Exceptions can wrap an underlying cause."""
        cause = ValueError("root")
        try:
            raise StorageError("wrapper") from cause
        except StorageError as exc:
            assert exc.__cause__ is cause
            assert exc.message == "wrapper"
