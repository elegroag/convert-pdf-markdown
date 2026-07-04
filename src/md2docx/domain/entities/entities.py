"""Domain entities for MD2DOCX."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MarkdownSection:
    """A single section sourced from one Markdown file."""

    source: Path
    title: str
    content: str


@dataclass
class ConsolidatedManual:
    """Consolidated Markdown ready for DOCX conversion."""

    sections: list[MarkdownSection] = field(default_factory=list)
    combined: str = ""
    source_path: Path | None = None


@dataclass
class DocxBuild:
    """Result of building a DOCX from consolidated Markdown."""

    manual_path: Path
    docx_path: Path
    stylesheet_used: str = ""
    refined: bool = False
