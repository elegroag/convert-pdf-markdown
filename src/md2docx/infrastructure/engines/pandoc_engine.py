"""Pandoc engine adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger

from md2docx.domain.exceptions import ConversionError
from md2docx.domain.ports.ports import IMarkdownToDocxEngine
from md2docx.infrastructure.engines._binary_check import require_pandoc


class PandocEngine(IMarkdownToDocxEngine):
    """Convert Markdown to DOCX using pandoc."""

    def convert(
        self,
        md_path: Path,
        reference_docx: Path,
        out_docx: Path,
    ) -> Path:
        """Run pandoc with a reference DOCX template."""
        pandoc = require_pandoc()
        out_docx.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            pandoc,
            str(md_path),
            "-o",
            str(out_docx),
            f"--reference-doc={reference_docx}",
        ]
        try:
            logger.debug("running pandoc: {}", " ".join(cmd))
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or exc.stdout or str(exc)
            raise ConversionError(f"pandoc failed: {stderr}") from exc
        if not out_docx.is_file():
            raise ConversionError(f"pandoc did not produce {out_docx}")
        return out_docx


__all__ = ["PandocEngine"]
