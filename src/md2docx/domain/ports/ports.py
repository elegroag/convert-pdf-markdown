"""Domain ports (interfaces) for MD2DOCX."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.value_objects.value_objects import ConversionConfig


class IMarkdownReader(ABC):
    """Reads Markdown content from disk."""

    @abstractmethod
    def read(self, path: Path) -> str:
        """Return the UTF-8 Markdown content of ``path``."""


class IManualConsolidator(ABC):
    """Consolidates one or more Markdown sources."""

    @abstractmethod
    def consolidate(
        self,
        paths: list[Path],
        *,
        config: ConversionConfig,
        titles: list[str] | None = None,
    ) -> ConsolidatedManual:
        """Merge Markdown files into a :class:`ConsolidatedManual`."""


class ITocInserter(ABC):
    """Inserts a table of contents into consolidated Markdown."""

    @abstractmethod
    def insert(
        self,
        manual: ConsolidatedManual,
        *,
        config: ConversionConfig,
    ) -> ConsolidatedManual:
        """Return a manual with TOC inserted."""


class ITableCleaner(ABC):
    """Normalizes Markdown tables."""

    @abstractmethod
    def clean(
        self,
        manual: ConsolidatedManual,
        *,
        config: ConversionConfig,
    ) -> ConsolidatedManual:
        """Return a cleaned copy of the manual."""


class IReferenceDocxBuilder(ABC):
    """Builds or resolves a pandoc reference DOCX template."""

    @abstractmethod
    def build(self, output_dir: Path, config: ConversionConfig) -> Path:
        """Return the path to a reference DOCX file."""


class IMarkdownToDocxEngine(ABC):
    """Converts Markdown to DOCX via pandoc."""

    @abstractmethod
    def convert(
        self,
        md_path: Path,
        reference_docx: Path,
        out_docx: Path,
    ) -> Path:
        """Run pandoc and return the generated DOCX path."""


class IDocxPostProcessor(ABC):
    """Refines a DOCX file with LibreOffice headless."""

    @abstractmethod
    def refine(self, docx_path: Path, out_dir: Path) -> Path:
        """Return the refined DOCX path."""


class IStorage(ABC):
    """Persists consolidated Markdown and final DOCX."""

    @abstractmethod
    def save_manual(
        self,
        manual: ConsolidatedManual,
        output_dir: Path,
        config: ConversionConfig,
    ) -> Path:
        """Write consolidated Markdown and return its path."""

    @abstractmethod
    def save_docx(self, source_docx: Path, output_dir: Path, config: ConversionConfig) -> Path:
        """Copy or move the DOCX to the final output location."""


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
