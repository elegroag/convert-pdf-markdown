"""Camelot-based table extractor (lattice & stream)."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from pdf2md.domain.entities.entities import TableNode
from pdf2md.domain.exceptions import TableExtractionError
from pdf2md.domain.ports.ports import ITableExtractor

try:
    import camelot  # type: ignore[import-not-found]
except ImportError:
    camelot = None  # type: ignore[assignment]


class CamelotTableExtractor(ITableExtractor):
    """Extract tables using Camelot.

    Supports both ``lattice`` (line-based) and ``stream`` (whitespace
    separation) strategies. Camelot is an optional dependency; the
    extractor falls back to an empty list if it isn't installed.
    """

    def __init__(self, flavor: str = "lattice", **kwargs: object) -> None:
        if flavor not in ("lattice", "stream"):
            raise ValueError("flavor must be 'lattice' or 'stream'")
        self._flavor = flavor
        self._kwargs = dict(kwargs)

    def extract_tables(
        self, pdf_path: Path, page_number: int
    ) -> list[TableNode]:
        """Extract all tables on a given page using Camelot."""
        if camelot is None:
            logger.warning(
                "camelot not installed; skipping CamelotTableExtractor"
            )
            return []
        try:
            tables = camelot.read_pdf(  # type: ignore[call-arg]
                str(pdf_path),
                pages=str(page_number),
                flavor=self._flavor,
                **self._kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            raise TableExtractionError(
                f"camelot failed on page {page_number}: {exc}"
            ) from exc

        out: list[TableNode] = []
        for table in tables:
            df = table.df
            if df is None or df.empty:
                continue
            headers = [str(c) for c in df.iloc[0].tolist()]
            body = [
                ["" if v is None else str(v) for v in row]
                for row in df.iloc[1:].values.tolist()
            ]
            out.append(
                TableNode(
                    page_number=page_number,
                    bbox=tuple(table._bbox),  # type: ignore[attr-defined]
                    headers=headers,
                    rows=body,
                    extraction_method=f"camelot-{self._flavor}",
                )
            )
        return out


__all__ = ["CamelotTableExtractor"]
