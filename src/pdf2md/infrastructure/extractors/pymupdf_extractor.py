"""PyMuPDF-based extractor.

This is the default :class:`IExtractor` implementation. It uses the
``pymupdf`` library (imported as ``fitz``) to read the PDF and populate
a :class:`PdfDocument` with pages, text, blocks, images, and metadata.
"""

from __future__ import annotations

import re
from collections import Counter
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
_TOC_DOTS_RE = re.compile(r"\.{4,}")
_LETTER_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]")
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
                raw_by_page: list[list[dict[str, Any]]] = []
                page_widths: list[float] = []
                for index in range(doc.page_count):
                    raw_page = doc.load_page(index)
                    page = PdfPage(page_number=index + 1)
                    page.raw_text = raw_page.get_text("text") or ""
                    raw_blocks, page_width = self._parse_raw_blocks(
                        raw_page, page.raw_text
                    )
                    raw_by_page.append(raw_blocks)
                    page_widths.append(page_width)
                    pages.append(page)

                document_body_size = self._body_size_from_raw(
                    [block for page_blocks in raw_by_page for block in page_blocks]
                )

                for index, page in enumerate(pages):
                    page.blocks = self._classify_blocks(
                        raw_by_page[index],
                        body_size=document_body_size,
                        page_width=page_widths[index],
                    )
                    raw_page = doc.load_page(index)
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
        """Yield :class:`ContentBlock` instances for a page (legacy entry point)."""
        raw_blocks, page_width = self._parse_raw_blocks(raw_page, text)
        body_size = self._body_size_from_raw(raw_blocks)
        return self._classify_blocks(
            raw_blocks, body_size=body_size, page_width=page_width
        )

    def _parse_raw_blocks(
        self, raw_page: Any, text: str
    ) -> tuple[list[dict[str, Any]], float]:
        """Parse a page into raw block dicts without heading classification."""
        try:
            page_dict = raw_page.get_text("dict")
        except Exception:  # noqa: BLE001
            blocks = [
                {
                    "block_type": b.block_type,
                    "text": b.text,
                    "level": b.level,
                    "font_size": b.font_size,
                    "is_bold": b.is_bold,
                    "bbox": b.bbox,
                }
                for b in self._blocks_from_text(text)
            ]
            return blocks, 0.0

        blocks: list[dict[str, Any]] = []
        body = page_dict.get("blocks", []) if isinstance(page_dict, dict) else []
        page_width = float(getattr(raw_page.rect, "width", 0.0) or 0.0)
        for block in body:
            if block.get("type") != 0:
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
                line_bbox = tuple(line.get("bbox", block.get("bbox", (0, 0, 0, 0))))  # type: ignore[assignment]
                if is_mono or is_script_tag:
                    block_type = BlockType.CODE.value
                elif _LIST_RE.match(line_text):
                    block_type = BlockType.LIST_ITEM.value
                else:
                    block_type = BlockType.PARAGRAPH.value
                blocks.append(
                    {
                        "block_type": block_type,
                        "text": line_text,
                        "level": 0,
                        "font_size": font_size,
                        "is_bold": is_bold,
                        "bbox": line_bbox,
                    }
                )
        return blocks, page_width

    def _classify_blocks(
        self,
        raw_blocks: list[dict[str, Any]],
        *,
        body_size: float,
        page_width: float,
    ) -> list[ContentBlock]:
        """Apply heading promotion and return classified content blocks."""
        classified = [
            self._maybe_promote_heading(raw, body_size=body_size, page_width=page_width)
            for raw in raw_blocks
        ]
        return [
            ContentBlock(
                block_type=b["block_type"],
                text=b["text"],
                level=b["level"],
                font_size=b["font_size"],
                is_bold=b["is_bold"],
                bbox=b["bbox"],
            )
            for b in classified
        ]

    @staticmethod
    def _body_size_from_raw(blocks: list[dict[str, Any]]) -> float:
        """Return the weighted modal body font size for a page's raw block dicts."""
        weights: Counter[float] = Counter()
        for b in blocks:
            if b.get("block_type") in (
                BlockType.CODE.value,
                BlockType.LIST_ITEM.value,
            ):
                continue
            if b.get("font_size", 0.0) <= 0:
                continue
            size = round(b["font_size"], 2)
            weight = 1.0
            if b.get("is_bold"):
                weight *= 0.3
            if b.get("block_type") == BlockType.HEADING.value:
                weight *= 0.2
            weights[size] += weight
        if not weights:
            return 11.0
        return weights.most_common(1)[0][0]

    @staticmethod
    def _heading_level_from_delta(delta: float) -> int:
        """Map a font-size delta above body text to a heading level."""
        if delta > 2.5:
            return 1
        if delta >= 1.5:
            return 2
        if delta >= 0.5:
            return 3
        return 0

    @staticmethod
    def _is_centered_short_title(
        bbox: tuple[float, float, float, float],
        page_width: float,
        text: str,
        font_size: float,
        body_size: float,
    ) -> bool:
        """Return True when a short line is horizontally centred on the page."""
        if page_width <= 0:
            return False
        stripped = text.strip()
        if not stripped or len(stripped.split()) > 12 or len(stripped) > 80:
            return False
        if _TOC_DOTS_RE.search(stripped):
            return False
        if font_size < body_size:
            return False
        x0, _y0, x1, _y1 = bbox
        if x0 == 0.0 and x1 == 0.0:
            return False
        line_center = (x0 + x1) / 2.0
        page_center = page_width / 2.0
        if abs(line_center - page_center) > page_width * 0.15:
            return False
        if (x1 - x0) > page_width * 0.7:
            return False
        letters = _LETTER_RE.findall(stripped)
        if letters:
            upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if upper_ratio < 0.6:
                return False
        return True

    def _maybe_promote_heading(
        self,
        raw: dict[str, Any],
        *,
        body_size: float,
        page_width: float,
    ) -> dict[str, Any]:
        """Promote a paragraph block to HEADING when structural signals match."""
        if raw["block_type"] != BlockType.PARAGRAPH.value:
            return raw
        font_size = float(raw["font_size"])
        delta = font_size - body_size
        text = str(raw["text"]).strip()
        if not text:
            return raw
        if text[0].islower():
            return raw
        if _TOC_DOTS_RE.search(text):
            return raw
        word_count = len(text.split())
        if word_count > 12:
            return raw
        level = 0
        if raw["is_bold"] and delta >= 0.5:
            level = self._heading_level_from_delta(delta)
        elif delta >= 1.5:
            level = self._heading_level_from_delta(delta)
        elif self._is_centered_short_title(
            raw["bbox"], page_width, text, font_size, body_size
        ):
            level = self._heading_level_from_delta(max(delta, 0.5))
        if level > 0:
            return {**raw, "block_type": BlockType.HEADING.value, "level": level}
        return raw

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
