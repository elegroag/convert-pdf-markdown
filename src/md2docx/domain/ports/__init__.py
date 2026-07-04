"""Domain ports."""

from md2docx.domain.ports.ports import (
    IBatchRunner,
    IDocxPostProcessor,
    IManualConsolidator,
    IMarkdownReader,
    IMarkdownToDocxEngine,
    IReferenceDocxBuilder,
    IStorage,
    ITableCleaner,
    ITocInserter,
)

__all__ = [
    "IBatchRunner",
    "IDocxPostProcessor",
    "IManualConsolidator",
    "IMarkdownReader",
    "IMarkdownToDocxEngine",
    "IReferenceDocxBuilder",
    "IStorage",
    "ITableCleaner",
    "ITocInserter",
]
