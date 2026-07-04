"""Filesystem Markdown reader."""

from __future__ import annotations

from pathlib import Path

from md2docx.domain.exceptions import RenderingError
from md2docx.domain.ports.ports import IMarkdownReader


class FileMarkdownReader(IMarkdownReader):
    """Read Markdown files from disk."""

    def read(self, path: Path) -> str:
        """Return UTF-8 Markdown content."""
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RenderingError(f"cannot read {path}: {exc}") from exc


__all__ = ["FileMarkdownReader"]
