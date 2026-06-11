"""Integration test: tables.pdf — lattice and stream table extraction."""

from __future__ import annotations


class TestTablesPdfLattice:
    """Page 1 contains a lattice table with visible grid lines."""

    def test_lattice_table_detected(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("tables.pdf"))
        page1 = doc.pages[0]
        assert len(page1.tables) >= 1

    def test_lattice_table_headers(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("tables.pdf"))
        table = doc.pages[0].tables[0]
        expected = {"Name", "Age", "City"}
        assert set(table.headers) == expected

    def test_lattice_table_rows(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("tables.pdf"))
        table = doc.pages[0].tables[0]
        cell_values = {cell for row in table.rows for cell in row}
        assert "Alice" in cell_values
        assert "Bob" in cell_values
        assert "Carla" in cell_values
        assert "Madrid" in cell_values
        assert "Berlin" in cell_values
        assert "Paris" in cell_values


class TestTablesPdfStream:
    """Page 2 contains a whitespace-separated (stream) table.

    pdfplumber uses ``vertical_strategy: lines`` by default, so
    whitespace-separated text without ruling lines is NOT expected
    to be detected as a table.
    """

    def test_stream_table_not_detected(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("tables.pdf"))
        page2 = doc.pages[1]
        assert len(page2.tables) == 0

    def test_stream_text_present(self, pdf_path, text_only_extractor) -> None:
        doc = text_only_extractor.extract(pdf_path("tables.pdf"))
        raw = doc.pages[1].raw_text
        assert "Product" in raw
        assert "Apples" in raw
        assert "Oranges" in raw
