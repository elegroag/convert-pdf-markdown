"""Domain exceptions for MD2DOCX."""

from __future__ import annotations


class Md2DocxException(Exception):  # noqa: N818 - mirrors Docx2MdException naming
    """Base exception for all md2docx errors."""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause


class ConversionError(Md2DocxException):
    """Raised when Markdown to DOCX conversion fails."""


class PandocNotFoundError(ConversionError):
    """Raised when the pandoc binary is not available on PATH."""


class LibreOfficeNotFoundError(ConversionError):
    """Raised when the LibreOffice binary is not available on PATH."""


class RenderingError(Md2DocxException):
    """Raised when document preparation or rendering fails."""


class StorageError(Md2DocxException):
    """Raised when persisting Markdown or DOCX fails."""


class ConfigurationError(Md2DocxException):
    """Raised when configuration loading or validation fails."""
