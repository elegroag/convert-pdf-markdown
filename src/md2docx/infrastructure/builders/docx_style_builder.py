"""Build pandoc reference DOCX with Calibri styles."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt

from md2docx.domain.ports.ports import IReferenceDocxBuilder
from md2docx.domain.value_objects.value_objects import ConversionConfig


class DocxStyleBuilder(IReferenceDocxBuilder):
    """Create or reuse a reference DOCX for pandoc."""

    def build(self, output_dir: Path, config: ConversionConfig) -> Path:
        """Return a cached reference DOCX under ``output_dir/_template``."""
        if config.reference_docx is not None and config.reference_docx.is_file():
            return config.reference_docx

        template_dir = output_dir / "_template"
        template_dir.mkdir(parents=True, exist_ok=True)
        reference_path = template_dir / "reference.docx"
        if reference_path.is_file():
            return reference_path

        doc = Document()
        normal = doc.styles["Normal"]
        normal.font.name = config.base_font
        normal.font.size = Pt(config.base_font_size_pt)

        for level, size in ((1, 16), (2, 13), (3, 11)):
            heading = doc.styles[f"Heading {level}"]
            heading.font.name = config.base_font
            heading.font.size = Pt(size)

        doc.add_paragraph("Reference template for pandoc.")
        doc.save(str(reference_path))
        return reference_path


__all__ = ["DocxStyleBuilder"]
