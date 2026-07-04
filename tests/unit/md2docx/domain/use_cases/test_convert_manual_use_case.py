"""Tests for ConvertManualUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.exceptions import PandocNotFoundError
from md2docx.domain.use_cases.use_cases import ConvertManualRequest, ConvertManualUseCase
from md2docx.domain.value_objects.value_objects import ConversionConfig


class TestConvertManualUseCase:
    def test_success_pipeline(self, tmp_path: Path) -> None:
        md = tmp_path / "manual.md"
        md.write_text("# Manual\n\nBody", encoding="utf-8")
        out_dir = tmp_path / "out"

        consolidator = MagicMock()
        consolidator.consolidate.return_value = ConsolidatedManual(
            combined="# Manual\n\nBody",
            sections=[],
        )
        table_cleaner = MagicMock()
        table_cleaner.clean.side_effect = lambda manual, **_: manual
        toc_inserter = MagicMock()
        toc_inserter.insert.side_effect = lambda manual, **_: manual
        reference_builder = MagicMock()
        reference_builder.build.return_value = tmp_path / "ref.docx"
        pandoc_engine = MagicMock()
        intermediate = out_dir / "manual_intermediate.docx"
        pandoc_engine.convert.return_value = intermediate
        post_processor = MagicMock()
        post_processor.refine.return_value = intermediate
        storage = MagicMock()
        storage.save_manual.return_value = out_dir / "MANUAL_COMPLETO.md"
        storage.save_docx.return_value = out_dir / "MANUAL_SISTEMA.docx"

        use_case = ConvertManualUseCase(
            consolidator=consolidator,
            table_cleaner=table_cleaner,
            toc_inserter=toc_inserter,
            reference_builder=reference_builder,
            pandoc_engine=pandoc_engine,
            post_processor=post_processor,
            storage=storage,
        )
        result = use_case.execute(
            ConvertManualRequest(
                md_path=md,
                output_dir=out_dir,
                config=ConversionConfig(consolidate=False),
            )
        )

        assert result.status == "success"
        assert result.docx_path == out_dir / "MANUAL_SISTEMA.docx"
        consolidator.consolidate.assert_called_once()
        pandoc_engine.convert.assert_called_once()
        post_processor.refine.assert_called_once()
        storage.save_docx.assert_called_once()

    def test_pandoc_error_returns_failure(self, tmp_path: Path) -> None:
        md = tmp_path / "manual.md"
        md.write_text("# Manual", encoding="utf-8")

        consolidator = MagicMock()
        consolidator.consolidate.return_value = ConsolidatedManual(combined="# Manual")
        table_cleaner = MagicMock()
        table_cleaner.clean.side_effect = lambda manual, **_: manual
        toc_inserter = MagicMock()
        toc_inserter.insert.side_effect = lambda manual, **_: manual
        reference_builder = MagicMock()
        reference_builder.build.return_value = tmp_path / "ref.docx"
        pandoc_engine = MagicMock()
        pandoc_engine.convert.side_effect = PandocNotFoundError("missing")
        storage = MagicMock()
        storage.save_manual.return_value = tmp_path / "MANUAL_COMPLETO.md"

        use_case = ConvertManualUseCase(
            consolidator=consolidator,
            table_cleaner=table_cleaner,
            toc_inserter=toc_inserter,
            reference_builder=reference_builder,
            pandoc_engine=pandoc_engine,
            post_processor=MagicMock(),
            storage=storage,
        )
        result = use_case.execute(
            ConvertManualRequest(md_path=md, output_dir=tmp_path / "out")
        )
        assert result.status == "error"
        assert result.error == "PandocNotFoundError"
