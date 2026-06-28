"""Domain ports (interfaces) for XLSX2MD."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from xlsx2md.domain.entities.entities import MarkdownDocument, SheetBlock, XlsxDocument


class ISpreadsheetParser(ABC):
    """Parses an Excel workbook into domain entities."""

    @abstractmethod
    def parse(self, path: Path, *, book_dir: Path) -> XlsxDocument:
        """Parse the workbook and return an :class:`XlsxDocument`."""


class IMarkdownRenderer(ABC):
    """Converts a worksheet to Markdown."""

    @abstractmethod
    def render(self, document: XlsxDocument, sheet: SheetBlock) -> MarkdownDocument:
        """Produce a :class:`MarkdownDocument` for a single sheet."""


class IIndexRenderer(ABC):
    """Builds the workbook index Markdown document."""

    @abstractmethod
    def render(
        self,
        document: XlsxDocument,
        sheet_files: dict[str, Path],
    ) -> MarkdownDocument:
        """Produce the ``_index.md`` document for a workbook."""


class IAssetExporter(ABC):
    """Exports binary assets (images) to disk."""

    @abstractmethod
    def export(self, name: str, data: bytes) -> str:
        """Save the asset and return the relative path for Markdown references."""


class IStorage(ABC):
    """Persists a Markdown document and its assets."""

    @abstractmethod
    def save(self, document: MarkdownDocument, source_path: Path) -> Path:
        """Save the document and return the path of the generated ``.md`` file."""


class IBatchRunner(ABC):
    """Concurrency primitive used by :class:`BatchConvertUseCase`."""

    @abstractmethod
    def run(
        self,
        items: list[object],
        worker: Callable[[object], object],
        *,
        workers: int,
    ) -> list[object]:
        """Apply ``worker(item)`` to every element with the given parallelism."""


__all__ = [
    "IAssetExporter",
    "IBatchRunner",
    "IIndexRenderer",
    "IMarkdownRenderer",
    "ISpreadsheetParser",
    "IStorage",
]
