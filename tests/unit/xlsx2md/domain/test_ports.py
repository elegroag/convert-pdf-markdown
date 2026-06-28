"""Tests for xlsx2md domain ports."""

from __future__ import annotations

from xlsx2md.domain.ports.ports import (
    IAssetExporter,
    IBatchRunner,
    IIndexRenderer,
    IMarkdownRenderer,
    ISpreadsheetParser,
    IStorage,
)


class TestPorts:
    def test_ports_are_abstract(self) -> None:
        for port in (
            ISpreadsheetParser,
            IMarkdownRenderer,
            IIndexRenderer,
            IAssetExporter,
            IStorage,
            IBatchRunner,
        ):
            assert getattr(port, "__abstractmethods__", None)
