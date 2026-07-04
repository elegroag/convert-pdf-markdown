"""Binary availability checks for external tools."""

from __future__ import annotations

import shutil

from md2docx.domain.exceptions import LibreOfficeNotFoundError, PandocNotFoundError


def require_pandoc() -> str:
    """Return the pandoc executable path or raise :class:`PandocNotFoundError`."""
    path = shutil.which("pandoc")
    if path is None:
        raise PandocNotFoundError(
            "pandoc not found on PATH; install pandoc to convert Markdown to DOCX"
        )
    return path


def require_libreoffice() -> str:
    """Return the LibreOffice executable path or raise :class:`LibreOfficeNotFoundError`."""
    path = shutil.which("libreoffice") or shutil.which("soffice")
    if path is None:
        raise LibreOfficeNotFoundError(
            "LibreOffice not found on PATH; install libreoffice for DOCX refinement"
        )
    return path


__all__ = ["require_libreoffice", "require_pandoc"]
