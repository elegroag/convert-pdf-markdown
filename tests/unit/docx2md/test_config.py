"""Tests for docx2md service factory."""

from __future__ import annotations

from pathlib import Path

from docx2md.application.services.conversion_service import ConversionService
from docx2md.config.service_factory import build_batch_use_case, build_default_service
from docx2md.domain.use_cases.use_cases import BatchConvertUseCase


class TestServiceFactory:
    def test_build_default_service(self, tmp_path: Path) -> None:
        service = build_default_service(output_dir=tmp_path)
        assert isinstance(service, ConversionService)

    def test_build_batch_use_case(self, tmp_path: Path) -> None:
        use_case = build_batch_use_case(output_dir=tmp_path)
        assert isinstance(use_case, BatchConvertUseCase)
