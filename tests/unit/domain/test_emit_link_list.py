"""Tests for the v0.2.0 ``emit_link_list`` opt-in feature."""

from __future__ import annotations

from pdf2md.domain.value_objects.value_objects import (
    ConversionConfig,
    Link,
)


class TestEmitLinkListConfig:
    def test_default_is_false(self) -> None:
        cfg = ConversionConfig()
        assert cfg.emit_link_list is False

    def test_serialised_in_to_dict(self) -> None:
        cfg = ConversionConfig(emit_link_list=True)
        d = cfg.to_dict()
        assert d["emit_link_list"] is True

    def test_round_trip_through_from_dict(self) -> None:
        cfg = ConversionConfig(emit_link_list=True)
        d = cfg.to_dict()
        restored = ConversionConfig.from_dict(d)
        assert restored.emit_link_list is True

    def test_from_dict_defaults_to_false_when_missing(self) -> None:
        d = ConversionConfig().to_dict()
        d.pop("emit_link_list")
        restored = ConversionConfig.from_dict(d)
        assert restored.emit_link_list is False
