"""Domain exceptions for DOCX2MD."""

from __future__ import annotations


class Docx2MdException(Exception):  # noqa: N818 - mirrors Pdf2MdException naming
    """Base exception for all docx2md errors."""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause


class ExtractionError(Docx2MdException):
    """Base class for extraction failures from a Word document."""


class CorruptedDocxError(ExtractionError):
    """Raised when the DOCX file is malformed or unreadable."""


class RenderingError(Docx2MdException):
    """Raised when Markdown rendering fails."""


class StorageError(Docx2MdException):
    """Raised when persisting Markdown or assets fails."""


class ConfigurationError(Docx2MdException):
    """Raised when configuration loading or validation fails."""
