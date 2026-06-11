"""End-to-end integration test: full ConvertPdfUseCase pipeline with real fixture.

Exercises the complete wiring: extract → render → save, using the
real adapters against a reproducible PDF fixture. This validates that
the domain use case, infrastructure adapters, and application service
work correctly together.
"""

from __future__ import annotations

from pathlib import Path

from pdf2md.application.dto.dtos import ConversionRequest
from pdf2md.config.service_factory import build_default_service
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class TestEndToEndPipeline:
    """Convert a real fixture PDF through the full pipeline."""

    def test_simple_pdf_full_conversion(self, pdf_path, tmp_path) -> None:
        pdf = pdf_path("simple.pdf")
        out_dir = tmp_path / "output"
        service = build_default_service(output_dir=out_dir)

        result = service.convert(
            ConversionRequest(pdf_path=pdf, output_dir=out_dir)
        )

        assert result.status == "success"
        assert result.output_path is not None
        assert result.output_path.is_file()
        assert result.page_count == 3

        body = result.output_path.read_text(encoding="utf-8")
        assert "---" in body
        assert "Simple PDF" in body
        assert "Chapter One: Introduction" in body
        assert "Chapter Two: Methods" in body
        assert "Chapter Three: Results" in body

    def test_images_pdf_creates_assets(self, pdf_path, tmp_path) -> None:
        pdf = pdf_path("images.pdf")
        out_dir = tmp_path / "output"
        # Use a low threshold so fixture images (120×120) are extracted
        service = build_default_service(
            output_dir=out_dir,
            config=ConversionConfig(image_min_size=50),
        )

        result = service.convert(
            ConversionRequest(pdf_path=pdf, output_dir=out_dir)
        )

        assert result.status == "success"
        assert result.image_count == 2
        assets_dir = out_dir / "assets"
        assert assets_dir.is_dir()
        asset_files = list(assets_dir.iterdir())
        assert len(asset_files) == 2

    def test_tables_pdf_conversion(self, pdf_path, tmp_path) -> None:
        pdf = pdf_path("tables.pdf")
        out_dir = tmp_path / "output"
        service = build_default_service(output_dir=out_dir)

        result = service.convert(
            ConversionRequest(pdf_path=pdf, output_dir=out_dir)
        )

        assert result.status == "success"
        assert result.table_count >= 1
        body = result.output_path.read_text(encoding="utf-8")
        assert "|" in body

    def test_inspect_returns_metadata(self, pdf_path, tmp_path) -> None:
        pdf = pdf_path("simple.pdf")
        service = build_default_service(output_dir=tmp_path / "out")

        info = service.inspect(pdf)

        assert info.page_count == 3
        assert info.metadata["title"] == "Simple PDF"
        assert info.metadata["author"] == "pdf2md"
