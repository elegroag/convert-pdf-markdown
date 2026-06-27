"""Tests for docx2md value objects."""

from __future__ import annotations

import pytest

from docx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig


class TestConversionConfig:
    def test_defaults(self) -> None:
        cfg = ConversionConfig()
        assert cfg.assets_subdir == "assets"
        assert cfg.frontmatter is True
        assert cfg.extract_images is True

    def test_round_trip_dict(self) -> None:
        cfg = ConversionConfig(assets_subdir="media", frontmatter=False)
        restored = ConversionConfig.from_dict(cfg.to_dict())
        assert restored.assets_subdir == "media"
        assert restored.frontmatter is False


class TestBatchConfig:
    def test_workers_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="workers must be >= 1"):
            BatchConfig(workers=0)
