"""Tests for docx2md domain ports."""

from __future__ import annotations

import pytest

from docx2md.domain.ports.ports import (
    IAssetExporter,
    IBatchRunner,
    IDocumentParser,
    IMarkdownRenderer,
    IStorage,
)


@pytest.mark.parametrize(
    "port_cls",
    [IDocumentParser, IMarkdownRenderer, IAssetExporter, IStorage, IBatchRunner],
)
def test_ports_are_abstract(port_cls: type) -> None:
    with pytest.raises(TypeError):
        port_cls()  # type: ignore[abstract]
