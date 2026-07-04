"""Tests for LibreOffice post-processor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from md2docx.domain.exceptions import LibreOfficeNotFoundError
from md2docx.infrastructure.engines.libreoffice_postprocessor import LibreOfficePostProcessor


class TestLibreOfficePostProcessor:
    def test_raises_when_libreoffice_missing(self, tmp_path: Path) -> None:
        processor = LibreOfficePostProcessor()
        with patch(
            "md2docx.infrastructure.engines.libreoffice_postprocessor.require_libreoffice",
            side_effect=LibreOfficeNotFoundError("missing"),
        ), pytest.raises(LibreOfficeNotFoundError):
            processor.refine(tmp_path / "in.docx", tmp_path / "out")

    def test_runs_subprocess(self, tmp_path: Path) -> None:
        docx = tmp_path / "in.docx"
        out_dir = tmp_path / "out"
        docx.write_bytes(b"PK")
        out_dir.mkdir()
        (out_dir / "in.docx").write_bytes(b"PK-refined")

        processor = LibreOfficePostProcessor()
        with patch(
            "md2docx.infrastructure.engines.libreoffice_postprocessor.require_libreoffice",
            return_value="/usr/bin/libreoffice",
        ), patch(
            "md2docx.infrastructure.engines.libreoffice_postprocessor.subprocess.run"
        ) as run:
            run.return_value = MagicMock(returncode=0)
            result = processor.refine(docx, out_dir)
        assert result.name.endswith(".docx")
        run.assert_called_once()
