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


def _sanitize_cell(text: str) -> str:
    """Sanitize a cell for GFM tables.

    - Escapes pipes.
    - Replaces newlines with spaces.
    - Strips control characters.
    """
    if text is None:
        return ""
    text = _NEWLINE_RE.sub(" ", str(text))
    text = _PIPE_RE.sub("\\|", text)
    return text.strip()


class PdfplumberTableExtractor(ITableExtractor):
    """Extract tables from a PDF using pdfplumber's line-based strategy."""

    def __init__(self, table_settings: dict | None = None) -> None:
        self._settings: dict[str, Any] = table_settings or {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
        }

    def extract_tables(
        self, pdf_path: Path, page_number: int
    ) -> list[TableNode]:
        """Extract all tables from a specific PDF page."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
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
                if not rows:
                    continue
                # Decide whether the first row is a header: typical PDFs
                # mark headers via background colour or bold text. With
                # pdfplumber we have neither easily, so we treat the first
                # row as headers when all its cells are non-empty.
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


__all__ = ["PdfplumberTableExtractor"]
