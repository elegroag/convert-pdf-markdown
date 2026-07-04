# PDF2MD

Intelligent PDF, Word, and Excel to Markdown converter with Hexagonal Architecture.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## CLI rápido

```bash
# PDF → Markdown
pdf2md convert libro.pdf -o ./output

# Word → Markdown
docx2md convert documento.docx -o ./output
docx2md batch ./documentos/ -o ./output --workers 2

# Excel → Markdown
xlsx2md convert libro.xlsx -o ./output
xlsx2md batch ./hojas/ -o ./output --workers 2

# Markdown → Word (.docx)
md2docx convert manual.md -o ./output
md2docx convert manual.md -o ./output --source-dir ./secciones
md2docx batch ./manuales/ -o ./output --workers 2

# MCP (PDF + Word + Excel + MD→DOCX)
uvx --from "/ruta/al/convert-pdf-markdown[mcp]" convert2md-mcp
```

## Repository layout

```
src/pdf2md/
├── domain/           # Entities, value objects, ports, use cases (no I/O deps)
├── application/      # DTOs and ConversionService façade
├── infrastructure/   # PyMuPDF, pdfplumber, Camelot, renderers, storage
├── config/           # TOML loader and service factory
└── interface/
    ├── cli/          # Typer CLI
    ├── api/          # FastAPI server
    └── mcp/          # convert2md-mcp (PDF, DOCX, XLSX tools)

src/docx2md/
├── domain/           # Entities, value objects, ports, use cases (no I/O deps)
├── application/      # DTOs and ConversionService façade
├── infrastructure/   # python-docx parser, renderers, storage
├── config/           # Service factory
└── interface/
    └── cli/          # Typer CLI (convert, batch, version)

src/xlsx2md/
├── domain/           # Entities, value objects, ports, use cases (no I/O deps)
├── application/      # DTOs and ConversionService façade
├── infrastructure/   # openpyxl parser, renderers, storage
├── config/           # Service factory
└── interface/
    └── cli/          # Typer CLI (convert, batch, version)

src/md2docx/
├── domain/           # Entities, value objects, ports, use cases (no I/O deps)
├── application/      # DTOs and ConversionService façade
├── infrastructure/   # pandoc, LibreOffice, python-docx reference builder
├── config/           # Service factory
└── interface/
    └── cli/          # Typer CLI (convert, batch, version)

tests/
├── unit/             # Domain + use cases
├── integration/      # Real PDF/DOCX/XLSX round-trips
└── fixtures/         # Sample generators
```

## Code conventions

- Public API in English (docstrings, identifiers, comments).
- Communication, commit messages, docs in Spanish.
- Type hints everywhere; mypy strict mode is the target.
- Tests live next to the code they cover (mirror of `src/`).
- One responsibility per class; ports are narrow (ISP).
