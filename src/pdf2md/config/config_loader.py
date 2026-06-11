"""Configuration loading for PDF2MD.

Reads a ``pdf2md.toml`` file and overlays environment variables. The
resulting :class:`ConversionConfig` is a pure domain object.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover - Python 3.12+ is the supported runtime
    import tomli as tomllib  # type: ignore[no-redef]

from pdf2md.domain.exceptions import ConfigurationError
from pdf2md.domain.value_objects.enums import (
    ExtractorEngine,
    HeadingStyle,
    TableEngine,
)
from pdf2md.domain.value_objects.value_objects import (
    BatchConfig,
    ConversionConfig,
)


_DEFAULT_CONFIG_PATH = "pdf2md.toml"


def find_config_file(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` looking for the first ``pdf2md.toml``.

    Returns ``None`` if no config file is found.
    """
    env = os.environ.get("PDF2MD_CONFIG")
    if env:
        candidate = Path(env)
        if candidate.is_file():
            return candidate
    current = (start or Path.cwd()).resolve()
    for parent in (current, *current.parents):
        candidate = parent / _DEFAULT_CONFIG_PATH
        if candidate.is_file():
            return candidate
    return None


def load_toml(path: Path) -> dict[str, Any]:
    """Load and return the raw dict of a TOML file.

    Raises:
        ConfigurationError: If the file cannot be read or parsed.
    """
    try:
        with Path(path).open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"config file not found: {path}") from exc
    except OSError as exc:
        raise ConfigurationError(f"cannot read config file: {path}") from exc
    except tomllib.TOMLDecodeError as exc:  # type: ignore[attr-defined]
        raise ConfigurationError(f"invalid TOML in {path}: {exc}") from exc


def build_config(toml_data: dict[str, Any]) -> ConversionConfig:
    """Translate the raw TOML dict into a :class:`ConversionConfig`.

    Unknown keys are silently ignored. The ``[output]``, ``[extractor]``
    and ``[images]`` sections are mapped; see ``especificaciones.md``
    for the full schema.
    """
    images = toml_data.get("images", {}) or {}
    output = toml_data.get("output", {}) or {}
    extractor = toml_data.get("extractor", {}) or {}

    raw_table = str(extractor.get("table_engine", "pdfplumber"))
    try:
        table_engine = TableEngine(raw_table)
    except ValueError as exc:
        raise ConfigurationError(
            f"invalid table_engine {raw_table!r}; expected pdfplumber|camelot"
        ) from exc

    raw_heading = str(output.get("heading_style", "atx"))
    try:
        heading_style = HeadingStyle(raw_heading)
    except ValueError as exc:
        raise ConfigurationError(
            f"invalid heading_style {raw_heading!r}; expected atx|setext"
        ) from exc

    return ConversionConfig(
        image_min_size=int(images.get("min_size_px", 200)),
        extract_tables=bool(extractor.get("engine", "pymupdf")) != "pdfplumber"
        or "table_engine" in extractor,
        table_extractor=table_engine,
        extract_links=bool(output.get("extract_links", True)),
        frontmatter=bool(output.get("frontmatter", True)),
        extract_images=bool(images.get("enabled", True)),
        heading_style=heading_style,
        code_fence=str(output.get("code_fence", "```")),
        assets_subdir=str(images.get("assets_subdir", "assets")),
    )


def build_batch_config(toml_data: dict[str, Any]) -> BatchConfig:
    """Build a :class:`BatchConfig` from the raw TOML dict."""
    batch = toml_data.get("batch", {}) or {}
    extractor_raw = str((toml_data.get("extractor") or {}).get("engine", "pymupdf"))
    try:
        extractor = ExtractorEngine(extractor_raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"invalid extractor.engine {extractor_raw!r}"
        ) from exc

    workers_env = os.environ.get("PDF2MD_WORKERS")
    workers = int(workers_env) if workers_env else int(batch.get("workers", 2))
    if workers < 1:
        workers = 1

    return BatchConfig(
        workers=workers,
        skip_on_error=bool(batch.get("skip_on_error", True)),
        report_file=str(batch.get("report_file", "batch_report.json")),
        extractor=extractor,
        config=build_config(toml_data),
    )


def load_config(
    path: Path | None = None,
    *,
    search_from: Path | None = None,
) -> ConversionConfig:
    """Load a :class:`ConversionConfig` from TOML and environment.

    Args:
        path: Explicit config file path. Overrides environment variable.
        search_from: Directory to start the search from. Defaults to CWD.

    Returns:
        A populated :class:`ConversionConfig`. Returns the default config
        when no TOML file is found.
    """
    if path is None:
        path = find_config_file(search_from)
    if path is None:
        return ConversionConfig()
    return build_config(load_toml(path))


def load_batch_config(
    path: Path | None = None,
    *,
    search_from: Path | None = None,
) -> BatchConfig:
    """Load a :class:`BatchConfig` from TOML and environment.

    Falls back to defaults when no file is found.
    """
    if path is None:
        path = find_config_file(search_from)
    if path is None:
        return BatchConfig()
    return build_batch_config(load_toml(path))


__all__ = [
    "build_batch_config",
    "build_config",
    "find_config_file",
    "load_batch_config",
    "load_config",
    "load_toml",
]
