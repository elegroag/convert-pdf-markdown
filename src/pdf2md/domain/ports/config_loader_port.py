"""Configuration loading port.

Defines the contract that the application uses to obtain a
:class:`ConversionConfig`. Implementations live in the infrastructure /
config layer (e.g., :class:`pdf2md.config.toml_config_loader.TomlConfigLoader`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pdf2md.domain.value_objects.value_objects import ConversionConfig


class IConfigLoader(ABC):
    """Strategy for loading a :class:`ConversionConfig`."""

    @abstractmethod
    def load(self, path: Path | None = None) -> ConversionConfig:
        """Return a :class:`ConversionConfig`.

        Args:
            path: Explicit config file path. ``None`` means "search the
                default location" (current dir + ``PDF2MD_CONFIG`` env).
        """


__all__ = ["IConfigLoader"]
