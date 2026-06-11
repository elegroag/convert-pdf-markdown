"""In-memory storage adapter — useful for tests and ephemeral pipelines."""

from __future__ import annotations

import io
from pathlib import Path
from typing import IO

from pdf2md.domain.entities.entities import MarkdownDocument, PdfDocument
from pdf2md.domain.ports.ports import IStorage


class InMemoryStorage(IStorage):
    """Storage that keeps Markdown and image bytes in memory.

    The returned "path" is a virtual :class:`Path` of the form
    ``memory:<slug>.md``. It is **not** a real filesystem path — the
    test suite uses it as an opaque handle, with a single colon to
    avoid the ``//`` quirk of :class:`pathlib.PurePath`.
    """

    def __init__(self) -> None:
        self.markdown: str = ""
        self.images: dict[str, bytes] = {}
        self.last_output: Path | None = None

    def save(
        self,
        document: MarkdownDocument,
        source: PdfDocument | None = None,
    ) -> Path:
        """Persist the document in memory and return a virtual path."""
        self.markdown = document.to_string()
        if source is not None:
            for page in source.pages:
                for image in page.images:
                    if image.raw_bytes:
                        self.images[image.image_id] = image.raw_bytes
        slug = document.source_pdf.stem if document.source_pdf else "document"
        path = Path(f"memory:{slug}.md")
        self.last_output = path
        document.output_path = path
        return path

    def open_markdown(self) -> IO[str]:
        """Open the saved Markdown as a text stream."""
        return io.StringIO(self.markdown)


__all__ = ["InMemoryStorage"]
