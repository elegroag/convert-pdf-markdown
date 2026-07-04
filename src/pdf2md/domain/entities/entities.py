"""Domain entities for PDF2MD.

Entities are objects with identity that mutates over time. They contain
the rich business data of the system (a parsed PDF, a generated Markdown
document, an extracted image asset, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pdf2md.domain.value_objects.value_objects import ContentBlock, Link


@dataclass
class PdfMetadata:
    """Metadata extracted from the PDF's information dictionary.

    Attributes:
        title: Document title.
        author: Document author.
        subject: Document subject.
        creator: Creating application.
        producer: PDF producer.
        creation_date: ISO-8601 string, or empty when not available.
    """

    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    producer: str = ""
    creation_date: str = ""

    def is_empty(self) -> bool:
        """Return True if no meaningful metadata is present."""
        return not any(
            getattr(self, f.name) for f in self.__dataclass_fields__.values()  # type: ignore[arg-type]
        )


@dataclass
class ImageAsset:
    """An image embedded in a PDF, ready to be persisted.

    Attributes:
        image_id: Stable identifier (e.g., ``p3_img2``).
        page_number: PDF page the image was extracted from.
        bbox: Bounding box (x0, y0, x1, y1) in PDF units.
        format: Image format (``PNG``, ``JPEG``, ``JBIG2``).
        raw_bytes: The raw image bytes.
        caption: Optional caption inferred from nearby text.
        output_path: Path assigned by the storage adapter.
    """

    image_id: str
    page_number: int
    bbox: tuple[float, float, float, float]
    format: str
    raw_bytes: bytes
    caption: str | None = None
    output_path: Path | None = None


@dataclass
class TableNode:
    """A table extracted from a PDF page.

    Attributes:
        page_number: PDF page the table was extracted from.
        bbox: Bounding box (x0, y0, x1, y1) in PDF units.
        headers: Column headers in display order.
        rows: Body rows, each a list of cell strings.
        extraction_method: Engine used (``pdfplumber`` or ``camelot``).
    """

    page_number: int
    bbox: tuple[float, float, float, float]
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    extraction_method: str = "pdfplumber"


@dataclass
class PdfPage:
    """A single page of a PDF, holding text, blocks, images, and tables.

    Attributes:
        page_number: 1-indexed page number within the document.
        raw_text: The full text of the page as extracted.
        blocks: Semantically tagged content blocks (heading, paragraph, etc.).
        images: Images embedded in this page.
        tables: Tables found on this page.
        links: Hyperlinks present on this page.
    """

    page_number: int
    raw_text: str = ""
    blocks: list[ContentBlock] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)
    tables: list[TableNode] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    page_width: float = 0.0
    table_extraction_failed: bool = False


@dataclass
class PdfDocument:
    """The parsed contents of a PDF file.

    Attributes:
        file_path: Path of the source PDF.
        page_count: Total number of pages in the document.
        metadata: PDF metadata (title, author, ...).
        pages: The pages of the document, in order.
    """

    file_path: Path
    page_count: int
    metadata: PdfMetadata = field(default_factory=PdfMetadata)
    pages: list[PdfPage] = field(default_factory=list)

    def iter_pages(self, range_filter: str | None = None) -> list[PdfPage]:
        """Return pages matching a filter expression like ``1-50`` or ``1,3,5``.

        Returns the full list when ``range_filter`` is None or empty.
        """
        if not range_filter:
            return list(self.pages)

        wanted: set[int] = set()
        for chunk in range_filter.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "-" in chunk:
                start_s, end_s = chunk.split("-", 1)
                start = int(start_s)
                end = int(end_s) if end_s else self.page_count
                wanted.update(range(start, end + 1))
            else:
                wanted.add(int(chunk))
        return [p for p in self.pages if p.page_number in wanted]


@dataclass
class MarkdownPage:
    """A single page in the rendered Markdown document.

    Attributes:
        page_number: 1-indexed page number.
        content: The Markdown content for this page.
    """

    page_number: int
    content: str = ""


@dataclass
class MarkdownDocument:
    """The final Markdown document produced by a renderer.

    Attributes:
        source_pdf: The PDF this document was generated from.
        pages: The Markdown pages of the document, in order.
        assets_dir: Directory where image assets were written.
        output_path: Path of the ``.md`` file on disk.
    """

    source_pdf: Path
    pages: list[MarkdownPage] = field(default_factory=list)
    assets_dir: Path | None = None
    output_path: Path | None = None
    frontmatter: str = ""

    def to_string(self) -> str:
        """Return the complete Markdown content of the document."""
        chunks: list[str] = []
        if self.frontmatter:
            chunks.append(self.frontmatter)
        for page in self.pages:
            if page.content:
                chunks.append(page.content)
        return "\n\n".join(chunks)
