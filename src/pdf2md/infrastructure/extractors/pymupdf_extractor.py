"""PyMuPDF-based extractor.

This is the default :class:`IExtractor` implementation. It uses the
``pymupdf`` library (imported as ``fitz``) to read the PDF and populate
a :class:`PdfDocument` with pages, text, blocks, images, and metadata.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

from pdf2md.domain.entities.entities import (
    ImageAsset,
    PdfDocument,
    PdfMetadata,
    PdfPage,
    TableNode,
)
from pdf2md.domain.exceptions import (
    CorruptedPdfError,
    EncryptedPdfError,
    ExtractionError,
    ImageExtractionError,
    TableExtractionError,
)
from pdf2md.domain.ports.ports import (
    IExtractor,
    IImageExtractor,
    ILinkExtractor,
    ITableExtractor,
)
from pdf2md.domain.value_objects.enums import (
    BlockType,
    ExtractorEngine,
    TableEngine,
)
from pdf2md.domain.value_objects.value_objects import (
    ContentBlock,
    ConversionConfig,
    Link,
)

try:
    import fitz  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - environment dependency
    raise ImportError(
        "pymupdf is required for the default extractor. "
        "Install with: pip install pymupdf"
    ) from exc


# Monospaced font hints used to detect code blocks.
_MONO_FONT_HINTS: tuple[str, ...] = (
    "courier",
    "consolas",
    "menlo",
    "monaco",
    "source code",
    "fira",
    "inconsolata",
    "jetbrains",
    "dejavu sans mono",
    "liberation mono",
    "ubuntu mono",
    "droid sans mono",
    "noto mono",
    "sf mono",
    "monospace",
    "andale mono",
    "anonymous pro",
)

# Regex used to detect list items in raw text.
_LIST_RE = re.compile(r"^\s*(?:[-*+•●]|\d+[.)]|[a-zA-Z][.)])\s+")
_HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.*)$", re.MULTILINE)

# Characters that, when they appear at the START of the next span,
# should NOT have a space inserted before them.
_NO_SPACE_BEFORE = set(".,;:!?)]}»\"'“’”")


def _join_spans(spans: list[dict]) -> str:
    """Join a list of PyMuPDF span dicts into a single line of text.

    Inserts a single space between adjacent spans when the previous
    span does not end in whitespace AND the next span does not start
    with punctuation. This is the v0.2.0 fix for missing spaces in
    multi-span lines (e.g. ``"Hola"él`` → ``"Hola" él``).
    """
    if not spans:
        return ""
    parts: list[str] = []
    for i, span in enumerate(spans):
        text = str(span.get("text", "") or "")
        if i == 0:
            parts.append(text)
            continue
        prev = parts[-1]
        prev_ends_space = prev.endswith(" ") or prev.endswith("\t")
        next_starts_punct = text and text[0] in _NO_SPACE_BEFORE
        next_starts_space = text.startswith(" ") or text.startswith("\t")
        if prev_ends_space or next_starts_punct or next_starts_space:
            parts.append(text)
        else:
            parts.append(" " + text)
    return "".join(parts).strip()


class PyMuPdfExtractor(IExtractor):
    """Extract PDF content using PyMuPDF.

    The extractor also implements :class:`IImageExtractor` and
    :class:`ILinkExtractor` for convenience. Table extraction is
    delegated to a separate :class:`ITableExtractor` because the
    best table engine depends on the PDF.
    """

    def __init__(
        self,
        config: ConversionConfig | None = None,
        image_min_size: int | None = None,
        table_extractor: ITableExtractor | None = None,
    ) -> None:
        self._config = config or ConversionConfig()
        self._min_size = (
            image_min_size
            if image_min_size is not None
            else self._config.image_min_size
        )
        self._table_extractor = table_extractor

    @property
    def engine(self) -> ExtractorEngine:
        """Return the engine identifier of this extractor."""
        return ExtractorEngine.PYMUPDF

    def extract(self, pdf_path: Path) -> PdfDocument:
        """Parse the PDF at ``pdf_path`` into a :class:`PdfDocument`."""
        path = Path(pdf_path)
        if not path.is_file():
            raise CorruptedPdfError(f"PDF not found: {path}")

        try:
            with fitz.open(path) as doc:
                if doc.is_encrypted:
                    if not doc.authenticate(""):
                        raise EncryptedPdfError(
                            f"PDF is password-protected: {path}"
                        )
                metadata = self._extract_metadata(doc)
                pages: list[PdfPage] = []
                for index in range(doc.page_count):
                    raw_page = doc.load_page(index)
                    page = PdfPage(page_number=index + 1)
                    page.raw_text = raw_page.get_text("text") or ""
                    page.blocks = list(self._extract_blocks(raw_page, page.raw_text))
                    if self._config.extract_images:
                        page.images = self._safe_extract_images(raw_page)
                    if self._config.extract_tables and self._table_extractor:
                        try:
                            page.tables = self._table_extractor.extract_tables(
                                path, index + 1
                            )
                        except TableExtractionError as exc:
                            logger.warning(
                                "table extraction failed on page {}: {}",
                                index + 1,
                                exc,
                            )
                    if page.tables:
                        page.blocks = self._filter_table_blocks(
                            page.blocks, page.tables
                        )
                    if self._config.extract_links:
                        page.links = self._safe_extract_links(raw_page, index + 1)
                    pages.append(page)
                if self._config.extract_images:
                    self._deduplicate_images(pages)
                return PdfDocument(
                    file_path=path,
                    page_count=doc.page_count,
                    metadata=metadata,
                    pages=pages,
                )
        except (EncryptedPdfError, CorruptedPdfError):
            raise
        except fitz.FileDataError as exc:  # type: ignore[attr-defined]
            raise CorruptedPdfError(f"corrupted PDF {path}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(
                f"failed to extract {path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public adapter surface
    # ------------------------------------------------------------------

    def extract_images(self, page: PdfPage) -> list[ImageAsset]:  # type: ignore[override]
        """Re-extract images from a page object.

        Useful when the extractor is used as an :class:`IImageExtractor`.
        """
        path = page  # type: ignore[assignment]
        if not hasattr(path, "raw_text"):
            return []
        return self._safe_extract_images(path)  # type: ignore[arg-type]

    def extract_links(self, pdf_path: Path) -> list[Link]:  # type: ignore[override]
        """Extract every link from a PDF file."""
        out: list[Link] = []
        try:
            with fitz.open(pdf_path) as doc:
                if doc.is_encrypted and not doc.authenticate(""):
                    raise EncryptedPdfError(f"encrypted PDF: {pdf_path}")
                for index in range(doc.page_count):
                    page = doc.load_page(index)
                    out.extend(self._safe_extract_links(page, index + 1))
        except (EncryptedPdfError, CorruptedPdfError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(f"failed to read links from {pdf_path}") from exc
        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metadata(doc: Any) -> PdfMetadata:
        meta = doc.metadata or {}
        return PdfMetadata(
            title=str(meta.get("title") or ""),
            author=str(meta.get("author") or ""),
            subject=str(meta.get("subject") or ""),
            creator=str(meta.get("creator") or ""),
            producer=str(meta.get("producer") or ""),
            creation_date=str(meta.get("creationDate") or ""),
        )

    def _extract_blocks(
        self, raw_page: Any, text: str
    ) -> Iterable:
        """Yield :class:`ContentBlock` instances for a page.

        The strategy is to walk the underlying ``dict`` representation
        of the page, classify each block, and emit value objects.
        """
        try:
            page_dict = raw_page.get_text("dict")
        except Exception:  # noqa: BLE001
            return self._blocks_from_text(text)

        blocks: list = []
        body = page_dict.get("blocks", []) if isinstance(page_dict, dict) else []
        for block in body:
            if block.get("type") != 0:  # text-only; skip image blocks
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                line_text = _join_spans(spans)
                if not line_text:
                    continue
                first = spans[0]
                font_size = float(first.get("size", 0.0))
                font_name = str(first.get("font", "")).lower()
                is_bold = "bold" in font_name or bool(first.get("flags", 0) & 16)
                is_mono = any(hint in font_name for hint in _MONO_FONT_HINTS)
                is_script_tag = bool(
                    re.match(r"</?script[^>]*>\s*$", line_text, re.IGNORECASE)
                )
                bbox = tuple(block.get("bbox", (0, 0, 0, 0)))  # type: ignore[assignment]
                if is_mono or is_script_tag:
                    blocks.append(
                        {
                            "block_type": BlockType.CODE.value,
                            "text": line_text,
                            "level": 0,
                            "font_size": font_size,
                            "is_bold": is_bold,
                            "bbox": bbox,
                        }
                    )
                elif _LIST_RE.match(line_text):
                    blocks.append(
                        {
                            "block_type": BlockType.LIST_ITEM.value,
                            "text": line_text,
                            "level": 0,
                            "font_size": font_size,
                            "is_bold": is_bold,
                            "bbox": bbox,
                        }
                    )
                else:
                    blocks.append(
                        {
                            "block_type": BlockType.PARAGRAPH.value,
                            "text": line_text,
                            "level": 0,
                            "font_size": font_size,
                            "is_bold": is_bold,
                            "bbox": bbox,
                        }
                    )

        return [
            ContentBlock(
                block_type=b["block_type"],
                text=b["text"],
                level=b["level"],
                font_size=b["font_size"],
                is_bold=b["is_bold"],
                bbox=b["bbox"],
            )
            for b in blocks
        ]

    @staticmethod
    def _blocks_from_text(text: str) -> Iterable:
        """Fallback when PyMuPDF's dict API fails: parse the raw text."""
        out: list[ContentBlock] = []
        for line in text.splitlines():
            stripped = line.rstrip()
            if not stripped:
                continue
            if _LIST_RE.match(stripped):
                out.append(
                    ContentBlock(
                        block_type=BlockType.LIST_ITEM.value,
                        text=stripped,
                    )
                )
            elif re.match(r"</?script[^>]*>\s*$", stripped, re.IGNORECASE):
                out.append(
                    ContentBlock(
                        block_type=BlockType.CODE.value,
                        text=stripped,
                    )
                )
            else:
                out.append(
                    ContentBlock(
                        block_type=BlockType.PARAGRAPH.value,
                        text=stripped,
                    )
                )
        return out

    @staticmethod
    def _deduplicate_images(pages: list[PdfPage]) -> None:
        """Remove duplicate images across all pages (content-hash based)."""
        seen: set[int] = set()
        for page in pages:
            keep: list[ImageAsset] = []
            for img in page.images:
                h = hash(img.raw_bytes)
                if h in seen:
                    continue
                seen.add(h)
                keep.append(img)
            page.images = keep

    @staticmethod
    def _filter_table_blocks(
        blocks: list[ContentBlock], tables: list[TableNode]
    ) -> list[ContentBlock]:
        """Remove blocks whose bbox overlaps with any table bbox."""
        if not tables:
            return blocks
        result: list[ContentBlock] = []
        for block in blocks:
            bx0, by0, bx1, by1 = block.bbox or (0, 0, 0, 0)
            if bx0 == 0 and by0 == 0 and bx1 == 0 and by1 == 0:
                result.append(block)
                continue
            inside_table = False
            for tbl in tables:
                tx0, ty0, tx1, ty1 = tbl.bbox
                if bx0 < tx1 and bx1 > tx0 and by0 < ty1 and by1 > ty0:
                    inside_table = True
                    break
            if not inside_table:
                result.append(block)
        return result

    def _safe_extract_images(self, raw_page: Any) -> list[ImageAsset]:
        try:
            return list(self._extract_images(raw_page))
        except ImageExtractionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ImageExtractionError(
                f"image extraction failed: {exc}"
            ) from exc

    def _extract_images(self, raw_page: Any) -> Iterable[ImageAsset]:
        seen_xrefs: set[int] = set()
        for img_index, image in enumerate(raw_page.get_images(full=True), start=1):
            xref = image[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                pix = fitz.Pixmap(raw_page.parent, xref)
            except Exception:  # noqa: BLE001
                continue
            try:
                if pix.width < self._min_size or pix.height < self._min_size:
                    pix = None
                    continue
                ext = "png"
                if pix.colorspace and pix.colorspace.name not in ("DeviceRGB", "DeviceGray"):
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                raw_bytes = pix.tobytes(ext)
                yield ImageAsset(
                    image_id=f"p{raw_page.number + 1}_img{img_index}",
                    page_number=raw_page.number + 1,
                    bbox=(0.0, 0.0, float(pix.width), float(pix.height)),
                    format=ext.upper(),
                    raw_bytes=raw_bytes,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("image {} failed: {}", img_index, exc)
                continue
            finally:
                pix = None

    def _safe_extract_links(self, raw_page: Any, page_number: int) -> list[Link]:
        out: list[Link] = []
        try:
            for link in raw_page.get_links() or []:
                kind = link.get("kind")
                if kind == fitz.LINK_URI:  # type: ignore[attr-defined]
                    url = str(link.get("uri") or "")
                    if not url:
                        continue
                    text = self._link_text(raw_page, link)
                    out.append(
                        Link(url=url, text=text, page_number=page_number)
                    )
                elif kind == fitz.LINK_GOTO:  # type: ignore[attr-defined]
                    page = link.get("page", -1)
                    if page < 0:
                        continue
                    text = self._link_text(raw_page, link)
                    out.append(
                        Link(
                            url=f"#page-{page + 1}",
                            text=text,
                            page_number=page_number,
                            is_internal=True,
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("link extraction failed on page {}: {}", page_number, exc)
        return out

    @staticmethod
    def _link_text(raw_page: Any, link: dict) -> str:
        """Return the text covered by a link's bounding box, if any."""
        try:
            rect = link.get("from")
            if rect is None:
                return ""
            words = raw_page.get_text("words", clip=rect) or []
            return " ".join(w[4] for w in words).strip()
        except Exception:  # noqa: BLE001
            return ""


__all__ = ["PyMuPdfExtractor"]


# Backward-compatible alias for the previous camel case used in the spec.
PymupdfExtractor = PyMuPdfExtractor


def build_default_table_extractor(
    engine: TableEngine,
    *,
    table_settings: dict | None = None,
) -> ITableExtractor:
    """Construct the default :class:`ITableExtractor` for ``engine``."""
    from pdf2md.infrastructure.extractors.pdfplumber_extractor import (
        PdfplumberTableExtractor,
    )

    return PdfplumberTableExtractor(table_settings=table_settings or {})
