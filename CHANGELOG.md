# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **MCP tool `convert_xlsx_to_markdown`** — Excel (.xlsx) conversion exposed
  alongside `convert_pdf_to_markdown` and `convert_docx_to_markdown` in the
  `pdf2md-mcp` server.
- **`xlsx2md` package** — Excel (.xlsx) to Markdown converter with Hexagonal
  Architecture parallel to `pdf2md` and `docx2md`.
- **CLI `xlsx2md`** with `convert`, `batch`, and `version` subcommands.
- **MCP tool `convert_docx_to_markdown`** — Word (.docx) conversion exposed
  alongside `convert_pdf_to_markdown` in the `pdf2md-mcp` server.
- **`docx2md` package** — Word (.docx) to Markdown converter with Hexagonal
  Architecture parallel to `pdf2md`.
- **CLI `docx2md`** with `convert`, `batch`, and `version` subcommands.
- **`python-docx` dependency** for parsing Word documents.
- **Infrastructure**: `DocxParser`, `MarkdownRenderer`, `FileStorage`,
  `FileAssetExporter` (PNG conversion via Pillow).
- **Tests**: 38 unit + integration tests under `tests/unit/docx2md/`.

## [0.2.0] — 2026-06-08

### Added
- **HeadingInferer multi-signal** (`domain/services/heading_inferer.py`):
  replaces the font-size-only heuristic with a 5-signal scorer
  (font size, bold, length, punctuation, all-caps) plus a
  natural-language bonus that de-prioritises code-like and shell-like
  text. Now detects headings in PDFs where every heading shares the
  body font size and weight (e.g. Packt books).
- **ParagraphJoiner** (`domain/services/paragraph_joiner.py`): re-unites
  fragmented paragraph lines emitted by PyMuPDF. Runs between
  extraction and rendering. Joins on font profile + punctuation rules,
  strips hyphenation, handles word-wrap continuation.
- **Caption inference** (`domain/services/caption_inference.py`):
  locates `Figure N.M` / `Figura N.M` / `Table N.M` / `Listing N.M`
  / `Image N.M` captions near an image's bounding box and assigns
  them to the matching `ImageAsset`.
- **YAML frontmatter hardening** (`domain/services/frontmatter_builder.py`):
  values containing YAML-unsafe characters (`:`, `#`, `&`, `*`, `?`,
  `|`, `>`, `!`, `%`, `@`, leading `-`/digit, embedded `'`) are
  emitted as literal block scalars instead of double-quoted strings.
  PDF creation dates in `D:YYYYMMDDHHMMSS±HH'MM'` format are
  normalised to ISO 8601. Garbage dates are preserved verbatim.
- **Code language detection** (`infrastructure/renderers/markdown_renderer.py`):
  added `vue`, `sql`, `json` to the language list. Improved `html`
  and `bash` patterns. Priority order: `vue > html > css > python >
  php > bash > sql > json > ts`.
- **`emit_link_list` opt-in flag** (`domain/value_objects/value_objects.py`):
  link dumps at page bottom are now opt-in (default `False`).
  When on, links are emitted as `- [anchor text](url)` and internal
  links (`#page-N`) are filtered out.
- **Span joiner** (`infrastructure/extractors/pymupdf_extractor.py`):
  inserts a single space between adjacent PyMuPDF spans when the
  previous span does not end in whitespace AND the next span does
  not start with punctuation. Fixes `Hola"él` → `Hola" él`.
- **Verification script** (`scripts/verify_output.py`): regenerates
  the output, prints Markdown metrics, and round-trips the YAML
  frontmatter through `yaml.safe_load`.
- **`.hermes/` scaffolding**: `feature_list.json` and
  `progress/current.md` track the v0.2.0 work.

### Changed
- **`HeadingInferer.infer_levels` contract**: keys are now block text
  (not font size). Same block text on multiple pages counts once.
  Default `max_level` raised from 3 to 4.
- **`_render_page` signature**: `font_levels` is `dict[str, int]`.
- **`MarkdownRenderer` integration**: pages are now run through
  `ParagraphJoiner.join` and `infer_captions` before rendering.
- **`test_emits_all_fields` / `test_uses_creation_date_key` /
  `test_heading_inference` / `test_vue_sfc_uses_html_fence` /
  `test_js_code_uses_ts_fence` / `test_html_tag_table_renders_as_fenced_block` /
  `test_links_listed` / `test_renders_links_as_paragraphs` / legacy
  `test_heading_inference`**: updated to match the v0.2.0 contracts.

### Dependencies
- Added `pyyaml>=6.0` to `[project.dependencies]` for the YAML
  frontmatter round-trip test.

## [0.1.0] — 2026-06-05

### Added
- Initial scaffold: Hexagonal Architecture skeleton (domain, application,
  infrastructure, interface).
- `ConvertPdfUseCase` and `BatchConvertUseCase` with explicit error handling.
- `PyMuPdfExtractor` (text, blocks, images, links) with `EncryptedPdfError`
  and `CorruptedPdfError` mapping.
- `PdfplumberTableExtractor` with GFM sanitization and fallback marker.
- `CamelotTableExtractor` (optional) with lattice/stream flavors.
- `MarkdownRenderer` with relative-font-size heading inference and
  YAML frontmatter generation.
- `HtmlRenderer` for alternate output.
- `FileStorage` and `InMemoryStorage` adapters.
- `ThreadPoolBatchRunner` for concurrent batch processing.
- `ConversionService` façade plus `ConversionRequest` / `ConversionResult`
  DTOs.
- Typer CLI with `convert`, `batch`, `inspect`, and `version` commands.
- Optional FastAPI server in `interface/api`.
- TOML configuration loader (`pdf2md.toml` + env overrides).
- Pytest unit tests for the domain layer (entities, value objects, ports,
  use cases, services, renderers, storage).
- `pdf2md.toml` example and `README.md`.
