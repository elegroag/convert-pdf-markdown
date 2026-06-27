"""Integration tests for DOCX to Markdown conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

from docx2md.application.dto.dtos import ConversionRequest
from docx2md.config.service_factory import build_default_service
from tests.fixtures.docx_generator import build_simple_docx

pytestmark = pytest.mark.integration


class TestRealDocxConversion:
    def test_converts_simple_docx(self, tmp_path: Path) -> None:
        docx_path = build_simple_docx(tmp_path / "input" / "simple.docx")
        out_dir = tmp_path / "output"
        service = build_default_service(output_dir=out_dir)
        result = service.convert(
            ConversionRequest(docx_path=Path(docx_path), output_dir=out_dir)
        )

        assert result.status == "success"
        assert result.output_path is not None
        assert result.output_path.exists()
        content = result.output_path.read_text(encoding="utf-8")
        assert "Test Title" in content or "#" in content
        assert result.headings >= 1
        assert result.tables >= 1
