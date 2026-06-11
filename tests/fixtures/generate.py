"""Generate the PDF fixtures used by the integration tests.

Run from the repo root:

    python -m tests.fixtures.generate

This produces the seven PDFs declared in ``especificaciones.md`` §8.2.
The output is deterministic: every run produces byte-identical files
so that the integration tests can rely on stable content.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
PDFS_DIR = FIXTURES_DIR / "pdfs"
IMAGES_DIR = FIXTURES_DIR / "images"


# ----------------------------------------------------------------------
# Image fixtures
# ----------------------------------------------------------------------


def _make_png(path: Path, *, color: str, size: tuple[int, int]) -> None:
    img = PILImage.new("RGB", size, color=color)
    img.save(path, format="PNG")


def _make_jpeg(path: Path, *, color: str, size: tuple[int, int]) -> None:
    img = PILImage.new("RGB", size, color=color)
    img.save(path, format="JPEG", quality=85)


def _ensure_image_fixtures() -> tuple[Path, Path]:
    """Create the PNG and JPEG used by images.pdf (idempotent)."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    red = IMAGES_DIR / "red_square.png"
    blue = IMAGES_DIR / "blue_square.jpg"
    _make_png(red, color="#cc3333", size=(120, 120))
    _make_jpeg(blue, color="#3366cc", size=(120, 120))
    return red, blue


# ----------------------------------------------------------------------
# 1. simple.pdf
# ----------------------------------------------------------------------


def build_simple_pdf(path: Path) -> None:
    """Three pages with 3 heading levels, paragraphs, and a list."""
    doc = BaseDocTemplate(
        str(path),
        pagesize=letter,
        title="Simple PDF",
        author="pdf2md",
    )
    frame = Frame(
        2 * cm,
        2 * cm,
        letter[0] - 4 * cm,
        letter[1] - 4 * cm,
        id="content",
    )
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=20, leading=24)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=16, leading=20)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=13, leading=16)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=11, leading=14)

    story: list = []
    story.append(Paragraph("Chapter One: Introduction", h1))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "This is the body of the first chapter. It explains the basics.", body
        )
    )
    story.append(Spacer(1, 12))
    story.append(Paragraph("1.1 Background", h2))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Some background context goes here.", body))
    story.append(Spacer(1, 12))
    story.append(Paragraph("1.1.1 Historical note", h3))
    story.append(Paragraph("A small historical footnote about the topic.", body))
    story.append(Spacer(1, 12))
    story.append(Paragraph("- first item", body))
    story.append(Paragraph("- second item", body))
    story.append(Paragraph("- third item", body))

    story.append(PageBreak() if False else Spacer(1, 0))
    from reportlab.platypus import PageBreak

    story.append(PageBreak())
    story.append(Paragraph("Chapter Two: Methods", h1))
    story.append(
        Paragraph("The second chapter describes the methods used in the study.", body)
    )
    story.append(Spacer(1, 12))
    story.append(Paragraph("2.1 Data collection", h2))
    story.append(Paragraph("Data was collected from a representative sample.", body))
    story.append(Spacer(1, 12))
    story.append(Paragraph("2.2 Analysis", h2))
    story.append(Paragraph("We applied a simple linear model.", body))

    story.append(PageBreak())
    story.append(Paragraph("Chapter Three: Results", h1))
    story.append(Paragraph("Results show a clear positive trend.", body))

    doc.build(story)


# ----------------------------------------------------------------------
# 2. tables.pdf
# ----------------------------------------------------------------------


def build_tables_pdf(path: Path) -> None:
    """Two pages: page 1 has a lattice table (with grid lines), page 2 has a stream table (whitespace-separated)."""
    doc = BaseDocTemplate(str(path), pagesize=A4, title="Tables PDF")
    frame = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="content")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    body_style = ParagraphStyle("Body", fontName="Helvetica", fontSize=11, leading=14)

    story: list = []
    story.append(Paragraph("Lattice table (with borders)", body_style))
    story.append(Spacer(1, 12))

    lattice_data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "Madrid"],
        ["Bob", "25", "Berlin"],
        ["Carla", "35", "Paris"],
    ]
    lattice = Table(lattice_data, colWidths=[5 * cm, 2 * cm, 5 * cm])
    lattice.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
            ]
        )
    )
    story.append(lattice)

    from reportlab.platypus import PageBreak

    story.append(PageBreak())
    story.append(Paragraph("Stream table (whitespace separated)", body_style))
    story.append(Spacer(1, 12))

    stream_text = (
        "Product   Q1     Q2     Q3     Q4\n"
        "Apples    100    120    140    160\n"
        "Oranges   80     90     100    110\n"
        "Pears     60     65     70     75"
    )
    for line in stream_text.split("\n"):
        story.append(Paragraph(line.replace(" ", "&nbsp;"), body_style))

    doc.build(story)


# ----------------------------------------------------------------------
# 3. images.pdf
# ----------------------------------------------------------------------


def build_images_pdf(path: Path, png: Path, jpg: Path) -> None:
    """Two pages, one with a PNG and one with a JPEG."""
    doc = BaseDocTemplate(str(path), pagesize=A4, title="Images PDF")
    frame = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="content")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    body = styles["BodyText"]

    story: list = []
    story.append(Paragraph("A red square (PNG)", h1))
    story.append(Spacer(1, 12))
    story.append(Image(str(png), width=4 * cm, height=4 * cm))
    story.append(Spacer(1, 12))
    story.append(Paragraph("The image above is a 120x120 PNG.", body))

    from reportlab.platypus import PageBreak

    story.append(PageBreak())
    story.append(Paragraph("A blue square (JPEG)", h1))
    story.append(Spacer(1, 12))
    story.append(Image(str(jpg), width=4 * cm, height=4 * cm))
    story.append(Spacer(1, 12))
    story.append(Paragraph("The image above is a 120x120 JPEG.", body))

    doc.build(story)


# ----------------------------------------------------------------------
# 4. links.pdf
# ----------------------------------------------------------------------


def build_links_pdf(path: Path) -> None:
    """One page with an external link and an internal (page-anchor) link."""
    doc = BaseDocTemplate(str(path), pagesize=letter, title="Links PDF")
    frame = Frame(2 * cm, 2 * cm, letter[0] - 4 * cm, letter[1] - 4 * cm, id="content")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story: list = []
    story.append(Paragraph("Links", h1))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            'Visit <link href="https://example.com" color="blue">our website</link> for more.',
            body,
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            'Or jump directly to the <link href="#methods" color="blue">methods section</link>.',
            body,
        )
    )

    from reportlab.platypus import PageBreak

    story.append(PageBreak())
    story.append(
        Paragraph('<a name="methods"/>Methods', h2)
    )
    story.append(Paragraph("This is the methods section referenced above.", body))

    doc.build(story)


# ----------------------------------------------------------------------
# 5. multicolumn.pdf
# ----------------------------------------------------------------------


def build_multicolumn_pdf(path: Path) -> None:
    """Two-column layout: a single page with text flowing across two columns."""
    page_w, page_h = A4
    margin = 2 * cm
    gutter = 1 * cm
    col_w = (page_w - 2 * margin - gutter) / 2
    col_h = page_h - 2 * margin
    left_frame = Frame(margin, margin, col_w, col_h, id="left")
    right_frame = Frame(margin + col_w + gutter, margin, col_w, col_h, id="right")
    doc = BaseDocTemplate(
        str(path), pagesize=A4, title="Two-column PDF"
    )
    doc.addPageTemplates(
        [PageTemplate(id="two-col", frames=[left_frame, right_frame])]
    )

    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=13)
    text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
        "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
        "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
        "culpa qui officia deserunt mollit anim id est laborum."
    )
    story: list = []
    for _ in range(6):
        story.append(Paragraph(text, body))
        story.append(Spacer(1, 6))

    doc.build(story)


# ----------------------------------------------------------------------
# 6. encrypted.pdf
# ----------------------------------------------------------------------


def build_encrypted_pdf(path: Path) -> None:
    """PDF protected with the user password 'secret'."""
    canvas = Canvas(str(path), pagesize=letter)
    canvas.setTitle("Encrypted PDF")
    canvas.setAuthor("pdf2md")
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(2 * cm, 26 * cm, "Secret Document")
    canvas.setFont("Helvetica", 12)
    canvas.drawString(
        2 * cm, 24 * cm, "This document is password-protected."
    )
    canvas.showPage()
    canvas.save()
    canvas.setEncrypt("secret") if hasattr(canvas, "setEncrypt") else None
    _encrypt_existing_pdf(path, "secret")


def _encrypt_existing_pdf(path: Path, password: str) -> None:
    """Encrypt an existing PDF in-place using pypdf."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(path))
    writer = PdfWriter(clone_from=reader)
    for page in writer.pages:
        pass
    writer.encrypt(password)
    with path.open("wb") as f:
        writer.write(f)


# ----------------------------------------------------------------------
# 7. corrupted.pdf
# ----------------------------------------------------------------------


def build_corrupted_pdf(path: Path) -> None:
    """A file with a valid PDF magic but a truncated body — every parser will fail."""
    path.write_bytes(b"%PDF-1.4\nthis is not a valid cross-reference table\n")


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------


def main() -> None:
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    png, jpg = _ensure_image_fixtures()

    build_simple_pdf(PDFS_DIR / "simple.pdf")
    build_tables_pdf(PDFS_DIR / "tables.pdf")
    build_images_pdf(PDFS_DIR / "images.pdf", png, jpg)
    build_links_pdf(PDFS_DIR / "links.pdf")
    build_multicolumn_pdf(PDFS_DIR / "multicolumn.pdf")
    build_encrypted_pdf(PDFS_DIR / "encrypted.pdf")
    build_corrupted_pdf(PDFS_DIR / "corrupted.pdf")

    for pdf in sorted(PDFS_DIR.iterdir()):
        print(f"  {pdf.name:<20} {pdf.stat().st_size:>8} bytes")


if __name__ == "__main__":
    main()
