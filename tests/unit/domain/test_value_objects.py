"""Tests for ConversionConfig and BatchConfig value objects."""

from __future__ import annotations

import pytest

from pdf2md.domain.value_objects.enums import HeadingStyle, TableEngine
from pdf2md.domain.value_objects.value_objects import (
    BatchConfig,
    ConversionConfig,
)


class TestConversionConfig:
    """Tests for :class:`ConversionConfig`."""

    def test_default_values(self) -> None:
        """Defaults match the spec §6.1."""
        cfg = ConversionConfig()
        assert cfg.image_min_size == 200
        assert cfg.extract_tables is True
        assert cfg.table_extractor == TableEngine.PDFPLUMBER
        assert cfg.extract_links is True
        assert cfg.frontmatter is True
        assert cfg.extract_images is True
        assert cfg.heading_style == HeadingStyle.ATX
        assert cfg.code_fence == "```"
        assert cfg.assets_subdir == "assets"

    def test_to_dict_round_trip(self) -> None:
        """A config can be serialized to dict and rebuilt losslessly."""
        cfg = ConversionConfig(
            image_min_size=80,
            extract_tables=False,
            table_extractor=TableEngine.CAMELOT,
            frontmatter=False,
            heading_style=HeadingStyle.SETEXT,
        )
        rebuilt = ConversionConfig.from_dict(cfg.to_dict())
        assert rebuilt == cfg

    def test_from_dict_ignores_unknown_keys(self) -> None:
        """Unknown keys in the input dict are silently dropped."""
        cfg = ConversionConfig.from_dict(
            {"image_min_size": 99, "mystery": "value"}
        )
        assert cfg.image_min_size == 99

    def test_is_immutable(self) -> None:
        """Frozen dataclass: attribute assignment raises FrozenInstanceError."""
        cfg = ConversionConfig()
        with pytest.raises(Exception):
            cfg.image_min_size = 999  # type: ignore[misc]

    def test_from_dict_coerces_invalid_table_engine(self) -> None:
        """Invalid table engine raises ValueError via the enum."""
        with pytest.raises(ValueError):
            ConversionConfig.from_dict({"table_extractor": "unknown"})


class TestBatchConfig:
    """Tests for :class:`BatchConfig`."""

    def test_default_workers(self) -> None:
        """Default worker count is 2 (spec §6.1)."""
        assert BatchConfig().workers == 2

    def test_workers_must_be_positive(self) -> None:
        """Workers count must be >= 1."""
        with pytest.raises(ValueError):
            BatchConfig(workers=0)
        with pytest.raises(ValueError):
            BatchConfig(workers=-1)
