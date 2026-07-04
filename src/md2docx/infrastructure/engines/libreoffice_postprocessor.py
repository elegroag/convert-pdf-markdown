"""LibreOffice headless post-processor."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger

from md2docx.domain.exceptions import ConversionError
from md2docx.domain.ports.ports import IDocxPostProcessor
from md2docx.infrastructure.engines._binary_check import require_libreoffice


class LibreOfficePostProcessor(IDocxPostProcessor):
    """Refine a DOCX file using LibreOffice headless conversion."""

    def refine(self, docx_path: Path, out_dir: Path) -> Path:
        """Re-export DOCX via LibreOffice and return the refined file path."""
        libreoffice = require_libreoffice()
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            libreoffice,
            "--headless",
            "--convert-to",
            "docx",
            str(docx_path),
            "--outdir",
            str(out_dir),
        ]
        try:
            logger.debug("running libreoffice: {}", " ".join(cmd))
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or exc.stdout or str(exc)
            raise ConversionError(f"LibreOffice failed: {stderr}") from exc

        refined = out_dir / docx_path.name
        if not refined.is_file():
            raise ConversionError(f"LibreOffice did not produce {refined}")

        if refined.resolve() != docx_path.resolve():
            target = out_dir / f"{docx_path.stem}_refined.docx"
            shutil.move(str(refined), str(target))
            return target
        return refined


__all__ = ["LibreOfficePostProcessor"]
