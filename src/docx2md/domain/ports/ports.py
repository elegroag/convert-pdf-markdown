"""Domain ports (interfaces) for DOCX2MD."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from docx2md.domain.entities.entities import DocumentBlock, MarkdownDocument


class IDocumentParser(ABC):
    """Parses a Word document into logical blocks."""

    @abstractmethod
    def parse(self, path: Path) -> Iterator[DocumentBlock]:
        """Iterate over the logical blocks of the document."""


class IMarkdownRenderer(ABC):
    """Converts document blocks to Markdown."""

    @abstractmethod
    def render(self, blocks: Sequence[DocumentBlock]) -> MarkdownDocument:
        """Produce a :class:`MarkdownDocument` from blocks."""


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
    "IDocumentParser",
    "IMarkdownRenderer",
    "IStorage",
]
