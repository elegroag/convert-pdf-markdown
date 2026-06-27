"""Integration tests for DOCX batch conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

from docx2md.config.service_factory import build_batch_use_case
from docx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig
from tests.fixtures.docx_generator import build_simple_docx

pytestmark = pytest.mark.integration


class TestBatchDocxConversion:
    def test_batch_converts_multiple_files(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        for name in ("a", "b"):
            build_simple_docx(input_dir / f"{name}.docx")

        out_dir = tmp_path / "output"
        use_case = build_batch_use_case(output_dir=out_dir)
        report = use_case.execute(
            input_dir,
            BatchConfig(workers=1, config=ConversionConfig()),
        )

        assert report.total == 2
        assert report.success == 2
        assert report.failed == 0
