"""Tests for IConfigLoader port and TomlConfigLoader adapter.

The port defines the contract: ``load(path) -> ConversionConfig``.
The adapter reads TOML and overlays environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pdf2md.config.toml_config_loader import TomlConfigLoader
from pdf2md.domain.exceptions import ConfigurationError
from pdf2md.domain.ports.ports import IConfigLoader
from pdf2md.domain.value_objects.enums import HeadingStyle, TableEngine
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class _FakeLoader(IConfigLoader):
    """Minimal in-memory loader used to verify the port contract."""

    def __init__(self, config: ConversionConfig) -> None:
        self._config = config
        self.calls: list[Path | None] = []

    def load(self, path: Path | None = None) -> ConversionConfig:
        self.calls.append(path)
        return self._config


class TestIConfigLoaderPort:
    """The IConfigLoader ABC cannot be instantiated directly."""

    def test_abstract_instantiation_raises(self) -> None:
        with pytest.raises(TypeError):
            IConfigLoader()  # type: ignore[abstract]

    def test_concrete_loader_is_usable(self, tmp_path: Path) -> None:
        cfg = ConversionConfig(image_min_size=77)
        loader = _FakeLoader(cfg)
        assert loader.load() is cfg
        assert loader.load(tmp_path / "x.toml") is cfg
        assert len(loader.calls) == 2


@pytest.fixture
def write_toml(tmp_path: Path):
    """Helper that writes a TOML file with the given data and returns the path."""

    def _write(data: dict[str, Any], name: str = "pdf2md.toml") -> Path:
        target = tmp_path / name
        lines: list[str] = []
        for section, contents in data.items():
            if isinstance(contents, dict):
                lines.append(f"[{section}]")
                for key, value in contents.items():
                    if isinstance(value, bool):
                        lines.append(f"{key} = {'true' if value else 'false'}")
                    elif isinstance(value, str):
                        lines.append(f'{key} = "{value}"')
                    else:
                        lines.append(f"{key} = {value}")
            else:
                lines.append(f"{section} = {contents}")
        target.write_text("\n".join(lines), encoding="utf-8")
        return target

    return _write


class TestTomlConfigLoader:
    """TomlConfigLoader reads ``pdf2md.toml`` and overlays env vars."""

    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        loader = TomlConfigLoader()
        cfg = loader.load(tmp_path / "missing.toml")
        assert isinstance(cfg, ConversionConfig)
        assert cfg.image_min_size == 200

    def test_loads_extractor_table_engine(self, write_toml, tmp_path: Path) -> None:
        path = write_toml(
            {
                "extractor": {"engine": "pymupdf", "table_engine": "camelot"},
            }
        )
        cfg = TomlConfigLoader().load(path)
        assert cfg.table_extractor == TableEngine.CAMELOT

    def test_loads_images_min_size(self, write_toml) -> None:
        path = write_toml({"images": {"min_size_px": 80, "enabled": True}})
        cfg = TomlConfigLoader().load(path)
        assert cfg.image_min_size == 80
        assert cfg.extract_images is True

    def test_loads_output_heading_style(self, write_toml) -> None:
        path = write_toml({"output": {"heading_style": "setext", "frontmatter": False}})
        cfg = TomlConfigLoader().load(path)
        assert cfg.heading_style == HeadingStyle.SETEXT
        assert cfg.frontmatter is False

    def test_invalid_table_engine_raises(self, write_toml) -> None:
        path = write_toml({"extractor": {"table_engine": "weird"}})
        with pytest.raises(ConfigurationError):
            TomlConfigLoader().load(path)

    def test_invalid_heading_style_raises(self, write_toml) -> None:
        path = write_toml({"output": {"heading_style": "weird"}})
        with pytest.raises(ConfigurationError):
            TomlConfigLoader().load(path)

    def test_malformed_toml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.toml"
        path.write_text("this is not valid TOML = [", encoding="utf-8")
        with pytest.raises(ConfigurationError):
            TomlConfigLoader().load(path)

    def test_unknown_keys_are_ignored(self, write_toml) -> None:
        path = write_toml(
            {
                "extractor": {"engine": "pymupdf"},
                "mystery_section": {"foo": "bar"},
            }
        )
        cfg = TomlConfigLoader().load(path)
        assert cfg.image_min_size == 200

    def test_pdf2md_config_env_var(self, write_toml, monkeypatch) -> None:
        path = write_toml({"output": {"frontmatter": False}})
        monkeypatch.setenv("PDF2MD_CONFIG", str(path))
        cfg = TomlConfigLoader().load()
        assert cfg.frontmatter is False

    def test_explicit_nonexistent_path_returns_defaults(self, tmp_path: Path) -> None:
        """An explicit path that does not exist returns defaults, not an error."""
        cfg = TomlConfigLoader().load(tmp_path / "does_not_exist.toml")
        assert cfg.image_min_size == 200
        assert cfg.frontmatter is True

    def test_env_prefix_can_be_customised(self, write_toml, monkeypatch) -> None:
        path = write_toml({"images": {"min_size_px": 77}})
        monkeypatch.setenv("MYAPP_CONFIG", str(path))
        cfg = TomlConfigLoader(env_prefix="MYAPP_").load()
        assert cfg.image_min_size == 77
