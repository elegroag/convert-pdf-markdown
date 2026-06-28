"""Domain exceptions for XLSX2MD."""

from __future__ import annotations


class Xlsx2MdException(Exception):  # noqa: N818 - mirrors Docx2MdException naming
    """Base exception for all xlsx2md errors."""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause


class ExtractionError(Xlsx2MdException):
    """Base class for extraction failures from an Excel workbook."""


class CorruptedXlsxError(ExtractionError):
    """Raised when the XLSX file is malformed or unreadable."""


class RenderingError(Xlsx2MdException):
    """Raised when Markdown rendering fails."""


class StorageError(Xlsx2MdException):
    """Raised when persisting Markdown or assets fails."""


class ConfigurationError(Xlsx2MdException):
    """Raised when configuration loading or validation fails."""
