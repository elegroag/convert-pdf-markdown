"""Tests for the configuration loader and service factory."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pdf2md.config.config_loader import (
    build_batch_config,
    build_config,
    find_config_file,
    load_batch_config,
    load_config,
    load_toml,
)
from pdf2md.config.service_factory import (
    build_batch_use_case,
    build_default_service,
)
from pdf2md.domain.exceptions import ConfigurationError
from pdf2md.domain.value_objects.enums import HeadingStyle, TableEngine
from pdf2md.domain.value_objects.value_objects import BatchConfig


class TestLoadToml:
    """``load_toml`` reads and parses a TOML file."""

    def test_loads_minimal_file(self, tmp_path: Path) -> None:
        """A simple TOML file is returned as a dict."""
        p = tmp_path / "pdf2md.toml"
        p.write_text("[extractor]\nengine = 'pymupdf'\n")
        data = load_toml(p)
        assert data["extractor"]["engine"] == "pymupdf"

    def test_missing_file_raises_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """A non-existent file raises ``ConfigurationError``."""
        with pytest.raises(ConfigurationError):
            load_toml(tmp_path / "nope.toml")

    def test_invalid_toml_raises_configuration_error(
        self, tmp_path: Path
    ) -> None:
        """Malformed TOML raises ``ConfigurationError``."""
        p = tmp_path / "bad.toml"
        p.write_text("not = valid = toml = syntax")
        with pytest.raises(ConfigurationError):
            load_toml(p)


class TestBuildConfig:
    """``build_config`` maps a TOML dict to a :class:`ConversionConfig`."""

    def test_defaults(self) -> None:
        """Empty input returns the default config."""
        cfg = build_config({})
        assert cfg.image_min_size == 200
        assert cfg.table_extractor == TableEngine.PDFPLUMBER
        assert cfg.heading_style == HeadingStyle.ATX

    def test_overrides(self) -> None:
        """Each section is mapped to the corresponding config attribute."""
        cfg = build_config(
            {
                "images": {"min_size_px": 100, "enabled": False, "assets_subdir": "img"},
                "output": {
                    "heading_style": "setext",
                    "code_fence": "~~~",
                    "frontmatter": False,
                },
                "extractor": {"table_engine": "camelot"},
            }
        )
        assert cfg.image_min_size == 100
        assert cfg.extract_images is False
        assert cfg.assets_subdir == "img"
        assert cfg.heading_style == HeadingStyle.SETEXT
        assert cfg.code_fence == "~~~"
        assert cfg.frontmatter is False
        assert cfg.table_extractor == TableEngine.CAMELOT

    def test_invalid_heading_style_raises(self) -> None:
        """An unknown heading_style raises :class:`ConfigurationError`."""
        with pytest.raises(ConfigurationError):
            build_config({"output": {"heading_style": "bogus"}})

    def test_invalid_table_engine_raises(self) -> None:
        """An unknown table_engine raises :class:`ConfigurationError`."""
        with pytest.raises(ConfigurationError):
            build_config({"extractor": {"table_engine": "bogus"}})


class TestBuildBatchConfig:
    """``build_batch_config`` adds the batch section."""

    def test_defaults(self) -> None:
        """Empty input yields default batch config."""
        bc = build_batch_config({})
        assert bc.workers == 2
        assert bc.skip_on_error is True
        assert bc.report_file == "batch_report.json"

    def test_workers_override(self) -> None:
        """``batch.workers`` is honored."""
        bc = build_batch_config({"batch": {"workers": 8}})
        assert bc.workers == 8

    def test_invalid_extractor_engine_raises(self) -> None:
        """An unknown ``extractor.engine`` raises :class:`ConfigurationError`."""
        with pytest.raises(ConfigurationError):
            build_batch_config({"extractor": {"engine": "bogus"}})


class TestFindConfigFile:
    """``find_config_file`` walks up looking for ``pdf2md.toml``."""

    def test_finds_in_current_directory(self, tmp_path: Path) -> None:
        """A file in the current directory is found."""
        (tmp_path / "pdf2md.toml").write_text("")
        assert find_config_file(tmp_path) == tmp_path / "pdf2md.toml"

    def test_finds_in_parent(self, tmp_path: Path) -> None:
        """A file in a parent directory is found when the child has none."""
        (tmp_path / "pdf2md.toml").write_text("")
        child = tmp_path / "sub"
        child.mkdir()
        assert find_config_file(child) == tmp_path / "pdf2md.toml"

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Returns ``None`` when no ``pdf2md.toml`` exists."""
        assert find_config_file(tmp_path) is None

    def test_env_variable_takes_precedence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``PDF2MD_CONFIG`` overrides the search."""
        cfg = tmp_path / "custom.toml"
        cfg.write_text("")
        monkeypatch.setenv("PDF2MD_CONFIG", str(cfg))
        assert find_config_file(tmp_path) == cfg


class TestLoadConfig:
    """``load_config`` combines search + parse + default."""

    def test_returns_default_when_no_file(self, tmp_path: Path) -> None:
        """Returns the library default when no TOML is found."""
        from pdf2md.domain.value_objects.value_objects import ConversionConfig

        cfg = load_config(search_from=tmp_path)
        assert isinstance(cfg, ConversionConfig)

    def test_loads_file(self, tmp_path: Path) -> None:
        """Reads and parses a TOML file from disk."""
        cfg_file = tmp_path / "pdf2md.toml"
        cfg_file.write_text(
            dedent(
                """
                [images]
                min_size_px = 75

                [output]
                code_fence = '~~~'
                """
            ).strip()
        )
        cfg = load_config(search_from=tmp_path)
        assert cfg.image_min_size == 75
        assert cfg.code_fence == "~~~"

    def test_load_batch_config_returns_default_when_no_file(
        self, tmp_path: Path
    ) -> None:
        """Returns the library default when no TOML is found."""
        bc = load_batch_config(search_from=tmp_path)
        assert isinstance(bc, BatchConfig)


class TestServiceFactory:
    """``build_default_service`` and ``build_batch_use_case`` wire everything."""

    def test_build_default_service_returns_service(self, tmp_path: Path) -> None:
        """The factory returns a usable ConversionService."""
        from pdf2md import ConversionService

        service = build_default_service(output_dir=tmp_path)
        assert isinstance(service, ConversionService)

    def test_build_batch_use_case_returns_uc(self, tmp_path: Path) -> None:
        """The factory returns a BatchConvertUseCase."""
        from pdf2md.domain.use_cases.use_cases import BatchConvertUseCase

        use_case = build_batch_use_case(output_dir=tmp_path)
        assert isinstance(use_case, BatchConvertUseCase)
