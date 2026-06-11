# Verificación — PDF2MD

## Comandos de verificación rápida

```bash
# Suite completa
pytest

# Suite con cobertura
pytest --cov=pdf2md --cov-report=term-missing

# Solo unit
pytest tests/unit/ -v

# Solo integration (requiere pymupdf instalado)
pytest tests/integration/ -v

# Test específico
pytest tests/unit/use_cases/test_convert_pdf_use_case.py::TestConvertPdfUseCaseSuccess
```

## Linters

```bash
# Ruff (linting + import sort)
ruff check src tests
ruff format src tests

# Mypy strict
mypy src
```

## Smoke test end-to-end

```bash
# Generar un PDF de prueba
python -c "
import fitz
doc = fitz.open()
p = doc.new_page()
p.insert_text((50, 80), 'Hola', fontsize=22)
doc.save('/tmp/test.pdf')
"

# Convertirlo
pdf2md convert /tmp/test.pdf -o /tmp/out

# Verificar el output
cat /tmp/out/test.md
```

Salida esperada:

```markdown
---
title: ""
author: ""
pages: 1
---

# Hola
```

## Comprobaciones manuales de calidad

| Criterio | Cómo verificarlo |
|----------|-------------------|
| El frontmatter se genera | `head -5 output.md` muestra `---` y `title:` |
| Los headings se infieren | PDFs con tamaños de fuente variables producen `# H1`, `## H2` |
| Las tablas se escapan | PDFs con tablas con `|` interno producen `\\|` en el `.md` |
| Los assets se escriben | `ls output/assets/` muestra los PNG/JPG extraídos |
| El batch no aborta en errores | `cat batch_report.json` muestra `success` y `failed` separados |
| El CLI se autocompleta | `pdf2md --help` lista todos los subcomandos |

## Cobertura mínima esperada

- `pdf2md.domain`: ≥ 90 %
- `pdf2md.application`: ≥ 90 %
- `pdf2md.infrastructure`: ≥ 70 % (los extractors reales requieren
  fixtures PDF que viven en `tests/integration/`)
- `pdf2md.interface`: ≥ 80 % (CLI/API)

## Pre-commit checklist

Antes de hacer commit:

- [ ] `pytest` pasa localmente
- [ ] `ruff check src tests` no reporta errores
- [ ] `mypy src` no reporta errores
- [ ] La cobertura no ha bajado
- [ ] El commit message sigue el formato `tipo(scope): descripción`
