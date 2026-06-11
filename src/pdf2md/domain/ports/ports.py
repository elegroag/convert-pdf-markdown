"""Domain ports (interfaces) for PDF2MD.

Ports are abstract contracts that the domain defines and the
infrastructure implements. The domain depends on these abstractions
(inversion of dependencies), not on concrete libraries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    PdfDocument,
    PdfPage,
    TableNode,
)
from pdf2md.domain.ports.config_loader_port import IConfigLoader  # re-export
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class IExtractor(ABC):
    """Primary extractor: turns a PDF file into a :class:`PdfDocument`."""

    @abstractmethod
    def extract(self, pdf_path: Path) -> PdfDocument:
        """Extract all content from a PDF file.

        Args:
            pdf_path: Absolute or relative path to the PDF.

        Returns:
            A populated :class:`PdfDocument`.

        Raises:
            ExtractionError: If the file cannot be read.
            EncryptedPdfError: If the PDF is password-protected.
            CorruptedPdfError: If the file is not a valid PDF.
        """


class IImageExtractor(ABC):
    """Extracts images from a single PDF page."""

    @abstractmethod
    def extract_images(self, page: PdfPage) -> list[ImageAsset]:
        """Return all images on the given page."""


class ITableExtractor(ABC):
    """Extracts tables from a specific PDF page."""

    @abstractmethod
    def extract_tables(
        self, pdf_path: Path, page_number: int
    ) -> list[TableNode]:
        """Return all tables detected on the given page."""


class ILinkExtractor(ABC):
    """Extracts hyperlinks from a PDF file."""

    @abstractmethod
    def extract_links(self, pdf_path: Path) -> list:
        """Return a list of :class:`Link` objects present in the PDF."""


class IRenderer(ABC):
    """Turns a :class:`PdfDocument` into a :class:`MarkdownDocument`."""

    @abstractmethod
    def render(self, document: PdfDocument) -> MarkdownDocument:
        """Render the PDF document into Markdown."""


class IStorage(ABC):
    """Persists a :class:`MarkdownDocument` and its assets to disk.

    Implementations receive the rendered Markdown **and** the original
    :class:`PdfDocument` so that binary assets (images) can be written
    alongside the Markdown even though the renderer doesn't carry them.
    """

    @abstractmethod
    def save(
        self,
        document: MarkdownDocument,
        source: PdfDocument | None = None,
    ) -> Path:
        """Save the document and return the path of the generated ``.md`` file.

        Args:
            document: The rendered Markdown document.
            source: The original PDF document (used for image bytes).
        """


class IBatchRunner(ABC):
    """Optional concurrency primitive used by :class:`BatchConvertUseCase`.

    Implementations may use threads, processes, or a single worker.
    """

    @abstractmethod
    def run(self, items: list, worker, *, workers: int) -> list:
        """Apply ``worker(item)`` to every element with the given parallelism."""


__all__ = [
    "IBatchRunner",
    "IConfigLoader",
    "IExtractor",
    "IImageExtractor",
    "ILinkExtractor",
    "IRenderer",
    "IStorage",
    "ITableExtractor",
]
