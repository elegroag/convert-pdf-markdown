# PDF2MD

Intelligent PDF to Markdown converter with Hexagonal Architecture.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
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
    └── api/          # FastAPI server
tests/
├── unit/             # Domain + use cases
├── integration/      # Real PDF round-trips
└── fixtures/         # Sample PDFs
```

## Code conventions

- Public API in English (docstrings, identifiers, comments).
- Communication, commit messages, docs in Spanish.
- Type hints everywhere; mypy strict mode is the target.
- Tests live next to the code they cover (mirror of `src/`).
- One responsibility per class; ports are narrow (ISP).
