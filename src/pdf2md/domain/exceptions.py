"""Domain exceptions for PDF2MD.

Defines the exception hierarchy used across all layers. Domain exceptions
are framework-agnostic and never depend on infrastructure libraries.
"""

from __future__ import annotations


class Pdf2MdException(Exception):
    """Base exception for all pdf2md errors."""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause


class ExtractionError(Pdf2MdException):
    """Base class for extraction failures from a PDF document."""


class EncryptedPdfError(ExtractionError):
    """Raised when the PDF is password-protected and no password is given."""


class CorruptedPdfError(ExtractionError):
    """Raised when the PDF file is malformed or unreadable."""


class TableExtractionError(Pdf2MdException):
    """Raised when a specific table cannot be extracted (NON-FATAL)."""


class ImageExtractionError(Pdf2MdException):
    """Raised when a specific image cannot be extracted (NON-FATAL)."""


class RenderingError(Pdf2MdException):
    """Raised when Markdown rendering fails."""


class StorageError(Pdf2MdException):
    """Raised when persisting Markdown or assets fails."""


class ConfigurationError(Pdf2MdException):
    """Raised when configuration loading or validation fails."""
