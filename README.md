# PDF2MD Converter

Convierte libros y documentos PDF a Markdown estructurado, preservando
jerarquía de encabezados, imágenes, tablas, enlaces y bloques de código.

Construido con **Arquitectura Hexagonal (Ports & Adapters)**: el dominio
no depende de ninguna librería externa; los adaptadores de infraestructura
(PyMuPDF, pdfplumber, Camelot, FileStorage) se enchufan en interfaces
claras que facilitan el testing y el reemplazo.

## Instalación

```bash
# Dependencias mínimas
pip install pymupdf pdfplumber pydantic typer loguru rich

# Soporte de Camelot (opcional, para tablas lattice/stream avanzadas)
pip install "camelot-py[cv]"

# Servidor HTTP (opcional)
pip install fastapi uvicorn

# Instalación editable en desarrollo
pip install -e ".[dev]"
```

## Uso rápido (CLI)

```bash
# Conversión simple
pdf2md convert libro.pdf -o ./output

# Opciones avanzadas
pdf2md convert libro.pdf \
  --output ./output \
  --extractor pymupdf \
  --table-extractor pdfplumber \
  --image-min-size 80 \
  --pages 1-50 \
  --no-links

# Batch processing
pdf2md batch ./libros/ -o ./markdowns/ --workers 4

# Inspección estructural (sin escribir archivos)
pdf2md inspect libro.pdf --json
```

## Uso como librería

```python
from pathlib import Path
from pdf2md import ConversionService
from pdf2md.application.dto import ConversionRequest
from pdf2md.infrastructure.extractors import PyMuPdfExtractor
from pdf2md.infrastructure.renderers import MarkdownRenderer
from pdf2md.infrastructure.storage import FileStorage
from pdf2md.domain.value_objects import ConversionConfig

config = ConversionConfig(
    image_min_size=50,
    extract_tables=True,
    extract_links=True,
    frontmatter=True,
)

service = ConversionService(
    extractor=PyMuPdfExtractor(config=config),
    renderer=MarkdownRenderer(config),
    storage=FileStorage(output_dir=Path("./output"), config=config),
    default_config=config,
)

result = service.convert(ConversionRequest(
    pdf_path=Path("libro.pdf"),
    output_dir=Path("./output"),
    config=config,
))
print(result.output_path, result.image_count, result.table_count)
```

O, equivalentemente, usando la factory pre-cableada:

```python
from pdf2md.config import build_default_service

service = build_default_service(output_dir=Path("./output"))
result = service.convert(ConversionRequest(
    pdf_path=Path("libro.pdf"),
    output_dir=Path("./output"),
))
```

## Configuración

`pdf2md.toml` (opcional) — buscar en el cwd o el valor de `PDF2MD_CONFIG`:

```toml
[extractor]
engine = "pymupdf"          # pymupdf | pdfplumber
table_engine = "pdfplumber" # pdfplumber | camelot

[images]
enabled = true
min_size_px = 50
output_format = "png"
assets_subdir = "assets"

[output]
heading_style = "atx"        # atx (#) | setext (===)
code_fence = "```"
frontmatter = true

[batch]
workers = 2
skip_on_error = true
report_file = "batch_report.json"
```

Variables de entorno: `PDF2MD_LOG_LEVEL`, `PDF2MD_WORKERS`, `PDF2MD_CONFIG`.

## Manejo de errores

La jerarquía de excepciones sigue la spec §7:

```
Pdf2MdException
├── ExtractionError
│   ├── EncryptedPdfError    (PDF con contraseña)
│   └── CorruptedPdfError    (archivo dañado)
├── TableExtractionError     (no fatal — marcador en el .md)
├── ImageExtractionError     (no fatal — log y skip)
├── RenderingError
├── StorageError
└── ConfigurationError
```

Los errores de tabla/imagen son **no fatales**: el `MarkdownRenderer`
inserta el marcador `<!-- TABLE_EXTRACTION_FAILED ... -->` y continúa.
En modo batch, `skip_on_error = true` permite seguir procesando aunque
un PDF individual falle; el reporte se consolida en `batch_report.json`.

## Testing

```bash
pytest                    # suite completa (212 tests)
pytest --cov=pdf2md       # con cobertura
```

Estructura de tests (espejo de `src/`):

```
tests/
├── unit/                  # Dominio, aplicación, infraestructura
│   ├── domain/
│   ├── use_cases/
│   ├── services/
│   ├── infrastructure/
│   ├── interface/
│   └── test_config.py
└── integration/           # Round-trip con PDFs reales
```

Métricas de cobertura actuales (≥ 90% en dominio, ≥ 70% en infra):

| Capa | Cobertura |
|------|-----------|
| `domain/entities` | 99 % |
| `domain/value_objects` | 100 % |
| `domain/use_cases` | 100 % |
| `domain/exceptions` | 100 % |
| `domain/ports` | 100 % |
| `domain/services` | 100 % |
| `application/dto` | 100 % |
| `application/services` | 100 % |
| `infrastructure/storage` | 96-100 % |
| `infrastructure/extractors/pdfplumber` | 98 % |
| **TOTAL** | **86 %** |

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│ Capa Externa (CLI / API / Tests)                         │
│   interface/cli (Typer)   interface/api (FastAPI)        │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│ Capa de Aplicación                                       │
│   application/services  application/dto                  │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│ Dominio (cero dependencias externas)                     │
│   domain/entities    domain/value_objects                │
│   domain/ports       domain/use_cases                    │
│   domain/services    domain/exceptions                   │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│ Infraestructura (adaptadores)                            │
│   infrastructure/extractors  (PyMuPDF, pdfplumber, Camelot)
│   infrastructure/renderers   (Markdown, HTML)            │
│   infrastructure/storage     (File, InMemory, ThreadPool)│
│   config                     (TomlConfigLoader, factory) │
└──────────────────────────────────────────────────────────┘
```

## Principios SOLID

- **SRP** — `PyMuPdfExtractor` solo extrae; `MarkdownRenderer` solo renderiza.
- **OCP** — Nuevos formatos (HTML, AsciiDoc) implementan `IRenderer` sin
  tocar el dominio.
- **LSP** — Cualquier `IExtractor` puede sustituirse en `ConversionService`.
- **ISP** — `IImageExtractor`, `ITableExtractor`, `IConfigLoader` son
  puertos estrechos y específicos.
- **DIP** — `ConvertPdfUseCase` depende de `IExtractor`, `IRenderer`,
  `IStorage` — nunca de las implementaciones.

## Licencia

MIT
