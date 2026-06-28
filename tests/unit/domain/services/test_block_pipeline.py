"""Tests for block sanitization, noise filtering, and section joining."""

from __future__ import annotations

from pdf2md.domain.services.block_sanitizer import BlockSanitizer
from pdf2md.domain.services.page_noise_filter import PageNoiseFilter
from pdf2md.domain.services.paragraph_joiner import ParagraphJoiner
from pdf2md.domain.services.section_number_joiner import SectionNumberJoiner
from pdf2md.domain.value_objects.value_objects import ContentBlock


def _heading(text: str, *, level: int = 1) -> ContentBlock:
    return ContentBlock(block_type="heading", text=text, level=level, font_size=12.0)


def _para(text: str) -> ContentBlock:
    return ContentBlock(block_type="paragraph", text=text, font_size=12.0)


class TestPageNoiseFilter:
    def test_removes_institutional_footer(self) -> None:
        blocks = [
            _para("Cuerpo del informe."),
            _para(
                "Carrera 69 No. 44-35 Piso 1 • PBX 647 7000 "
                "cgr@contraloria.gov.co • Bogotá, D. C., Colombia"
            ),
        ]
        out = PageNoiseFilter.filter(blocks)
        assert len(out) == 1
        assert "Cuerpo" in out[0].text

    def test_removes_bare_page_number(self) -> None:
        blocks = [_para("Texto"), _para("13")]
        assert len(PageNoiseFilter.filter(blocks)) == 1


class TestBlockSanitizer:
    def test_demotes_lowercase_heading(self) -> None:
        blocks = [_heading("demás soportes relacionados con la administración")]
        out = BlockSanitizer.demote_false_headings(blocks)
        assert out[0].block_type == "paragraph"
        assert out[0].level == 0

    def test_keeps_real_heading(self) -> None:
        blocks = [_heading("LIMITACIONES DEL PROCESO")]
        out = BlockSanitizer.demote_false_headings(blocks)
        assert out[0].block_type == "heading"


class TestSectionNumberJoiner:
    def test_merges_number_and_caps_title(self) -> None:
        blocks = [
            _heading("1.4.", level=1),
            _heading("LIMITACIONES DEL PROCESO", level=1),
        ]
        out = SectionNumberJoiner.join(blocks)
        assert len(out) == 1
        assert out[0].block_type == "heading"
        assert out[0].text == "1.4. LIMITACIONES DEL PROCESO"
        assert out[0].level == 2

    def test_joins_paragraph_after_demoted_false_headings(self) -> None:
        blocks = [
            _para("La CGR no tuvo acceso a la totalidad de la información de las cuentas bancarias y"),
            _heading("demás soportes relacionados con la administración de los recursos clasificados por"),
            _para("la entidad como recursos propios, teniendo en cuenta que de acuerdo con la"),
            _heading("normatividad vigente la caja de compensación debe separar la contabilidad de los"),
            _para("relacionadas, sin embargo, en relación con los recursos del contrato N. 202 de 2024"),
        ]
        cleaned = BlockSanitizer.demote_false_headings(blocks)
        joined = ParagraphJoiner.join(cleaned)
        assert len(joined) == 1
        assert "demás soportes" in joined[0].text
        assert "normatividad vigente" in joined[0].text
        assert "contrato N. 202" in joined[0].text
