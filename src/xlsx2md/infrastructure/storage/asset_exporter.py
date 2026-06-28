"""Filesystem asset exporter for XLSX images."""

from __future__ import annotations

import io
import re
from pathlib import Path

from xlsx2md.domain.exceptions import StorageError
from xlsx2md.domain.ports.ports import IAssetExporter
from xlsx2md.domain.value_objects.value_objects import ConversionConfig

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class FileAssetExporter(IAssetExporter):
    """Export images from XLSX to an assets directory."""

    def __init__(self, assets_dir: Path, config: ConversionConfig | None = None) -> None:
        self._dir = assets_dir
        self._config = config or ConversionConfig()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self._assets_subdir_name = self._dir.name

    def export(self, name: str, data: bytes) -> str:
        """Save the asset and return a path relative to the Markdown file."""
        self._counter += 1
        safe = re.sub(r"[^\w.\-]", "_", name) or f"image_{self._counter}"
        out_path = self._dir / safe

        try:
            if PIL_AVAILABLE:
                img = Image.open(io.BytesIO(data))
                png_name = Path(safe).stem + ".png"
                out_path = self._dir / png_name
                img.save(out_path, format="PNG")
                return str(Path(self._assets_subdir_name) / png_name)
        except Exception:
            pass

        try:
            out_path.write_bytes(data)
        except OSError as exc:
            raise StorageError(f"failed to write asset {out_path}: {exc}") from exc
        return str(Path(self._assets_subdir_name) / safe)


__all__ = ["FileAssetExporter"]
