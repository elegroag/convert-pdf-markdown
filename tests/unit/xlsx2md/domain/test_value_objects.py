"""Tests for xlsx2md domain value objects."""

from __future__ import annotations

import pytest

from xlsx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig


class TestConversionConfig:
    def test_defaults(self) -> None:
        cfg = ConversionConfig()
        assert cfg.assets_subdir == "assets"
        assert cfg.include_index is True
        assert cfg.table_format == "github"

    def test_roundtrip_dict(self) -> None:
        cfg = ConversionConfig(max_rows=100, max_cols=10, include_index=False)
        restored = ConversionConfig.from_dict(cfg.to_dict())
        assert restored.max_rows == 100
        assert restored.max_cols == 10
        assert restored.include_index is False


class TestBatchConfig:
    def test_rejects_invalid_workers(self) -> None:
        with pytest.raises(ValueError, match="workers"):
            BatchConfig(workers=0)
