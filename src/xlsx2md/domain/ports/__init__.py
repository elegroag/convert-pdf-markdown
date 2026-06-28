"""Domain ports."""

from xlsx2md.domain.ports.ports import (
    IAssetExporter,
    IBatchRunner,
    IIndexRenderer,
    IMarkdownRenderer,
    ISpreadsheetParser,
    IStorage,
)

__all__ = [
    "IAssetExporter",
    "IBatchRunner",
    "IIndexRenderer",
    "IMarkdownRenderer",
    "ISpreadsheetParser",
    "IStorage",
]
