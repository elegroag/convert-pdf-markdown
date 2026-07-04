"""pdfplumber-based table extractor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger

from pdf2md.domain.entities.entities import TableNode
from pdf2md.domain.exceptions import TableExtractionError
from pdf2md.domain.ports.ports import ITableExtractor

try:
    import pdfplumber  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pdfplumber is required for the default table extractor. "
        "Install with: pip install pdfplumber"
    ) from exc


_PIPE_RE = re.compile(r"[|]")
_NEWLINE_RE = re.compile(r"[\r\n]+")

LATTICE_TABLE_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 5,
}

STREAM_TABLE_SETTINGS: dict[str, Any] = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 3,
    "join_tolerance": 3,
}


def _sanitize_cell(text: str) -> str:
    """Sanitize a cell for GFM tables."""
    if text is None:
        return ""
    text = _NEWLINE_RE.sub(" ", str(text))
    text = _PIPE_RE.sub("\\|", text)
    return text.strip()


def _looks_like_table(rows: list[list[str]]) -> bool:
    """Reject stream false-positives that split prose into single-column rows."""
    if len(rows) < 2:
        return False
    max_cols = max(len(row) for row in rows)
    if max_cols < 2:
        return False
    cells = [cell for row in rows for cell in row]
    if not cells:
        return False
    non_empty = sum(1 for cell in cells if cell)
    return non_empty / len(cells) >= 0.4


class PdfplumberTableExtractor(ITableExtractor):
    """Extract tables from a PDF using pdfplumber."""

    def __init__(self, table_settings: dict | None = None) -> None:
        self._settings: dict[str, Any] = table_settings or dict(LATTICE_TABLE_SETTINGS)
        self._pdf: Any | None = None
        self._pdf_path: Path | None = None

    def begin_document(self, pdf_path: Path) -> None:
        """Open ``pdf_path`` once for the current extraction run."""
        path = Path(pdf_path)
        if self._pdf_path == path and self._pdf is not None:
            return
        self.end_document()
        self._pdf_path = path
        self._pdf = pdfplumber.open(path)

    def end_document(self) -> None:
        """Close the cached pdfplumber handle."""
        if self._pdf is not None:
            self._pdf.close()
        self._pdf = None
        self._pdf_path = None

    def extract_tables(
        self, pdf_path: Path, page_number: int
    ) -> list[TableNode]:
        """Extract all tables from a specific PDF page."""
        try:
            if self._pdf is None or self._pdf_path != Path(pdf_path):
                self.begin_document(pdf_path)
            pdf = self._pdf
            assert pdf is not None
            if page_number < 1 or page_number > len(pdf.pages):
                return []
            page = pdf.pages[page_number - 1]
            raw_tables = page.find_tables(table_settings=self._settings)
        except Exception as exc:  # noqa: BLE001
            raise TableExtractionError(
                f"pdfplumber failed on page {page_number}: {exc}"
            ) from exc

        results: list[TableNode] = []
        for raw in raw_tables:
            try:
                rows = raw.extract() or []
                if not rows:
                    continue
                rows = [[_sanitize_cell(c) for c in row] for row in rows]
                if self._settings.get("vertical_strategy") == "text":
                    if not _looks_like_table(rows):
                        continue
                first = rows[0]
                has_header = all(cell for cell in first)
                if has_header:
                    headers, body = first, rows[1:]
                else:
                    width = max(len(r) for r in rows)
                    headers = [f"col{i + 1}" for i in range(width)]
                    body = rows
                results.append(
                    TableNode(
                        page_number=page_number,
                        bbox=tuple(raw.bbox),  # type: ignore[arg-type]
                        headers=headers,
                        rows=body,
                        extraction_method="pdfplumber",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "table on page {} failed to parse: {}", page_number, exc
                )
                continue
        return results


__all__ = [
    "LATTICE_TABLE_SETTINGS",
    "PdfplumberTableExtractor",
    "STREAM_TABLE_SETTINGS",
]
