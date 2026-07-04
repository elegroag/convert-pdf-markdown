"""Factory helpers for table extractors."""

from __future__ import annotations

from pdf2md.domain.ports.ports import ITableExtractor
from pdf2md.domain.value_objects.enums import TableEngine
from pdf2md.infrastructure.extractors.camelot_extractor import CamelotTableExtractor
from pdf2md.infrastructure.extractors.composite_table_extractor import (
    CompositeTableExtractor,
    DocumentScopedTableExtractor,
)
from pdf2md.infrastructure.extractors.pdfplumber_extractor import (
    LATTICE_TABLE_SETTINGS,
    PdfplumberTableExtractor,
    STREAM_TABLE_SETTINGS,
)


def build_default_table_extractor(
    engine: TableEngine,
    *,
    table_settings: dict | None = None,
) -> ITableExtractor:
    """Construct the default :class:`ITableExtractor` for ``engine``."""
    if engine == TableEngine.CAMELOT:
        inner = CompositeTableExtractor(
            CamelotTableExtractor(flavor="lattice"),
            CamelotTableExtractor(flavor="stream"),
        )
        return DocumentScopedTableExtractor(inner)

    lattice = PdfplumberTableExtractor(
        table_settings=table_settings or LATTICE_TABLE_SETTINGS
    )
    inner = CompositeTableExtractor(
        lattice,
        CamelotTableExtractor(flavor="stream"),
    )
    return DocumentScopedTableExtractor(inner)


__all__ = ["build_default_table_extractor"]
