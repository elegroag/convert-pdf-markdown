"""TOML-backed implementation of :class:`IConfigLoader`.

Reads ``pdf2md.toml`` from disk and overlays environment variables
(``PDF2MD_CONFIG``, ``PDF2MD_LOG_LEVEL``, ``PDF2MD_WORKERS``) on top.
Unknown keys are silently ignored.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from pdf2md.config.config_loader import build_config, find_config_file
from pdf2md.domain.exceptions import ConfigurationError
from pdf2md.domain.ports.config_loader_port import IConfigLoader
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class TomlConfigLoader(IConfigLoader):
    """Load a :class:`ConversionConfig` from a TOML file.

    The path can be:
        - given explicitly to :meth:`load`,
        - read from the ``PDF2MD_CONFIG`` environment variable,
        - discovered by walking up from the current directory.
    """

    def __init__(self, *, env_prefix: str = "PDF2MD_") -> None:
        self._env_prefix = env_prefix

    def load(self, path: Path | None = None) -> ConversionConfig:
        """Return a :class:`ConversionConfig` from TOML + env.

        Args:
            path: Optional explicit path. ``None`` triggers discovery. A
                non-existent explicit path is treated as "no config" and
                returns the library defaults.

        Raises:
            ConfigurationError: If the file is malformed or unreadable.
        """
        resolved = path or self._discover()
        if resolved is None or not Path(resolved).is_file():
            return ConversionConfig()
        data = self._read_toml(resolved)
        return build_config(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _discover(self) -> Path | None:
        """Locate the configuration file from the env or the cwd tree."""
        env = os.environ.get(f"{self._env_prefix}CONFIG")
        if env:
            candidate = Path(env)
            if candidate.is_file():
                return candidate
        return find_config_file()

    @staticmethod
    def _read_toml(path: Path) -> dict[str, Any]:
        try:
            with Path(path).open("rb") as f:
                return tomllib.load(f)
        except FileNotFoundError as exc:
            raise ConfigurationError(
                f"config file not found: {path}"
            ) from exc
        except tomllib.TOMLDecodeError as exc:  # type: ignore[attr-defined]
            raise ConfigurationError(
                f"invalid TOML in {path}: {exc}"
            ) from exc


__all__ = ["TomlConfigLoader"]
