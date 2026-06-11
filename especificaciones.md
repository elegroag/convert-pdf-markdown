# PDF2MD Converter
## Especificaciones Técnicas del Proyecto
> Migración Inteligente de Libros PDF a Markdown  
> Versión 1.0 | Junio 2026

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Modelo del Dominio](#4-modelo-del-dominio)
5. [Funcionalidades Clave](#5-funcionalidades-clave)
6. [Configuración del Sistema](#6-configuración-del-sistema)
7. [Manejo de Errores](#7-manejo-de-errores)
8. [Estrategia de Testing](#8-estrategia-de-testing)
9. [Cronograma de Desarrollo](#9-cronograma-de-desarrollo)
10. [Métricas de Calidad](#10-métricas-de-calidad)
11. [Dependencias](#11-dependencias-pyprojecttoml)

---

## 1. Visión General

### 1.1 Descripción

**PDF2MD Converter** es una herramienta CLI y librería Python de alto rendimiento, diseñada con **Arquitectura Hexagonal (Clean Architecture)**, cuyo propósito es transformar libros y documentos PDF a Markdown estructurado, preservando fielmente el contenido semántico: imágenes, tablas, enlaces, encabezados jerárquicos y bloques de código.

### 1.2 Problema que Resuelve

- Los libros PDF son opacos: su contenido no es reutilizable ni versionable en sistemas como Git.
- Las soluciones existentes (`pdf2md`, `pypdf`) pierden tablas, imágenes y la estructura jerárquica de capítulos.
- No existe una herramienta orientada específicamente a libros técnico-académicos con soporte de batch processing.

### 1.3 Objetivos

1. Extraer texto con preservación de jerarquía: H1/H2/H3, párrafos, listas.
2. Exportar imágenes embebidas a archivos PNG/JPG con referencias relativas en el Markdown.
3. Reconstruir tablas en formato Markdown GFM (GitHub Flavored Markdown).
4. Detectar y preservar hipervínculos internos y externos.
5. Soportar procesamiento en lote (batch) de directorios completos.
6. Proveer una API Python limpia para integración en proyectos externos.

---

## 2. Arquitectura del Sistema

### 2.1 Patrón Arquitectónico

El proyecto sigue **Arquitectura Hexagonal (Ports & Adapters)** con separación estricta de capas. El dominio central no depende de ningún framework ni librería externa.

```
Capa Externa (CLI / API / Tests)
        │
        ▼
Capa de Aplicación (Services, DTOs, Use Cases)
        │
        ▼
Dominio (Entities, Value Objects, Ports — sin dependencias externas)
        │
        ▼
Infraestructura (Adapters: PyMuPDF, pdfplumber, FileStorage, S3)
```

### 2.2 Estructura de Directorios

```
pdf2md/
├── src/
│   ├── domain/                        # Núcleo de negocio — cero dependencias externas
│   │   ├── entities/                  # PdfDocument, MarkdownPage, ImageAsset, TableNode
│   │   ├── value_objects/             # PageContent, HeadingLevel, TableCell
│   │   ├── ports/                     # Interfaces (ABC): IExtractor, IRenderer, IStorage
│   │   └── use_cases/                 # ConvertPdfUseCase, BatchConvertUseCase
│   │
│   ├── application/                   # Orquestación de use cases
│   │   ├── services/                  # ConversionService, BatchService
│   │   └── dto/                       # ConversionRequest, ConversionResult
│   │
│   ├── infrastructure/                # Implementaciones concretas de los ports
│   │   ├── extractors/
│   │   │   ├── pymupdf_extractor.py   # Adapter: PyMuPDF → IExtractor
│   │   │   └── pdfplumber_extractor.py
│   │   ├── renderers/
│   │   │   ├── markdown_renderer.py   # Convierte domain entities → .md
│   │   │   └── html_renderer.py       # (opcional) salida HTML
│   │   └── storage/
│   │       ├── file_storage.py        # Escritura en disco
│   │       └── s3_storage.py          # (opcional) salida a S3
│   │
│   └── interface/
│       ├── cli/                       # Entrypoint Typer
│       └── api/                       # (opcional) FastAPI REST
│
├── tests/
│   ├── unit/                          # Tests de dominio y use_cases
│   ├── integration/                   # Tests con PDFs reales
│   └── fixtures/                      # PDFs de referencia para tests
│
├── pyproject.toml
├── pdf2md.toml                        # Configuración por proyecto
└── README.md
```

### 2.3 Flujo de Conversión

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│  CLI / API  │───▶│ ConversionService │───▶│ IExtractor  │
└─────────────┘    └──────────────────┘    └──────┬──────┘
                                                  │ PdfDocument
                                           ┌──────▼──────┐
                                           │  IRenderer  │
                                           └──────┬──────┘
                                                  │ MarkdownDocument
                                           ┌──────▼──────┐
                                           │  IStorage   │
                                           └──────┬──────┘
                                                  │
                                        libro.md + assets/
```

### 2.4 Principios SOLID Aplicados

| Principio | Aplicación en el Proyecto |
|-----------|--------------------------|
| **SRP** | Cada clase tiene una sola responsabilidad: `PymupdfExtractor` solo extrae, `MarkdownRenderer` solo renderiza. |
| **OCP** | Nuevos formatos de salida (HTML, AsciiDoc) se agregan implementando `IRenderer` sin modificar el dominio. |
| **LSP** | Cualquier `IExtractor` puede reemplazarse sin romper `ConversionService` (`pdfplumber` ↔ `PyMuPDF`). |
| **ISP** | `IExtractor`, `IImageExtractor` e `ITableExtractor` son interfaces separadas; los adaptadores implementan solo lo que soportan. |
| **DIP** | `ConversionService` depende de abstracciones (`IExtractor`, `IRenderer`), inyectadas vía constructor. |

---

## 3. Stack Tecnológico

### 3.1 Lenguaje y Runtime

| Tecnología | Versión | Rol |
|-----------|---------|-----|
| Python | 3.12+ | Lenguaje principal |
| Poetry | 1.8+ | Gestión de dependencias y packaging |
| Typer | 0.12+ | CLI con autocompletado y help autogenerado |

### 3.2 Librerías de Extracción PDF

| Librería | Uso Principal | Fortaleza |
|---------|--------------|-----------|
| **PyMuPDF** (`fitz`) | Extracción principal de texto, imágenes y metadatos | Rendimiento, acceso a bytes de imagen sin conversión |
| **pdfplumber** | Extracción de tablas con líneas visibles | Detección de bordes y celdas con alta precisión |
| **Camelot-py** | Tablas en PDFs escaneados / lattice | Manejo de tablas sin delimitadores textuales |
| **Pillow** (PIL) | Procesamiento y optimización de imágenes | Conversión de formatos, redimensión, compresión |

### 3.3 Librerías de Renderizado y Utilidades

| Librería | Uso |
|---------|-----|
| **tabulate** | Renderizado de tablas en formato GFM |
| **pydantic v2** | Validación y serialización de DTOs y configuración |
| **rich** | Output enriquecido en consola (progress bars, logs coloreados) |
| **loguru** | Logging estructurado con rotación de archivos |

### 3.4 Testing

| Herramienta | Uso |
|------------|-----|
| **pytest** | Framework principal de tests |
| **pytest-cov** | Cobertura de código |
| **pytest-mock** | Mocking de puertos (`IExtractor`, `IStorage`) |
| **factory-boy** | Generación de fixtures de entidades del dominio |

---

## 4. Modelo del Dominio

### 4.1 Entidades y Value Objects

#### `PdfDocument` (Entity)
```python
@dataclass
class PdfDocument:
    file_path: Path
    page_count: int
    metadata: PdfMetadata       # título, autor, subject, creation_date
    pages: list[PdfPage]
```

#### `PdfPage` (Entity)
```python
@dataclass
class PdfPage:
    page_number: int
    raw_text: str
    blocks: list[ContentBlock]
    images: list[ImageAsset]
    tables: list[TableNode]
```

#### `ContentBlock` (Value Object)
```python
@dataclass(frozen=True)
class ContentBlock:
    block_type: BlockType       # HEADING | PARAGRAPH | CODE | LIST_ITEM
    text: str
    level: int                  # 1-6 para headings, 0 para el resto
    font_size: float
    is_bold: bool
```

#### `ImageAsset` (Entity)
```python
@dataclass
class ImageAsset:
    image_id: str
    page_number: int
    bbox: tuple[float, float, float, float]
    format: str                 # PNG | JPEG | JBIG2
    raw_bytes: bytes
    caption: str | None         # inferido del texto contiguo
    output_path: Path | None    # asignado por IStorage
```

#### `TableNode` (Entity)
```python
@dataclass
class TableNode:
    page_number: int
    bbox: tuple[float, float, float, float]
    headers: list[str]
    rows: list[list[str]]
    extraction_method: str      # pdfplumber | camelot
```

#### `MarkdownDocument` (Output Entity)
```python
@dataclass
class MarkdownDocument:
    source_pdf: Path
    pages: list[MarkdownPage]
    assets_dir: Path
    output_path: Path

    def to_string(self) -> str:
        """Retorna el Markdown completo del documento."""
        ...
```

### 4.2 Ports (Interfaces)

```python
# domain/ports/i_extractor.py
class IExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_path: Path) -> PdfDocument: ...

# domain/ports/i_image_extractor.py
class IImageExtractor(ABC):
    @abstractmethod
    def extract_images(self, page: PdfPage) -> list[ImageAsset]: ...

# domain/ports/i_table_extractor.py
class ITableExtractor(ABC):
    @abstractmethod
    def extract_tables(self, pdf_path: Path, page_number: int) -> list[TableNode]: ...

# domain/ports/i_renderer.py
class IRenderer(ABC):
    @abstractmethod
    def render(self, document: PdfDocument) -> MarkdownDocument: ...

# domain/ports/i_storage.py
class IStorage(ABC):
    @abstractmethod
    def save(self, document: MarkdownDocument) -> Path: ...
```

### 4.3 Use Cases

```python
# domain/use_cases/convert_pdf_use_case.py
class ConvertPdfUseCase:
    def __init__(
        self,
        extractor: IExtractor,
        renderer: IRenderer,
        storage: IStorage,
    ) -> None: ...

    def execute(self, request: ConversionRequest) -> ConversionResult: ...

# domain/use_cases/batch_convert_use_case.py
class BatchConvertUseCase:
    def execute(self, directory: Path, config: BatchConfig) -> BatchReport: ...
```

---

## 5. Funcionalidades Clave

### 5.1 Extracción de Texto y Estructura

- **Detección de encabezados**: inferencia automática de H1/H2/H3 por tamaño de fuente relativo dentro del documento (sin hardcodear valores absolutos de pt).
- **Listas**: detección por patrones de texto (`1.`, `-`, `*`, `a)`) y por indentación del bloque.
- **Bloques de código**: detección por fuente monoespaciada (`Courier`, `Consolas`, `Menlo`) con salida en fenced code blocks.
- **Columnas múltiples**: clustering de bloques por coordenada X para libros con layout de dos columnas.
- **YAML Frontmatter** (configurable): metadata del PDF como frontmatter al inicio del `.md`.

```markdown
---
title: "Clean Code"
author: "Robert C. Martin"
pages: 431
created: 2008-08-01
---
```

### 5.2 Extracción de Imágenes

- Extracción de todas las imágenes embebidas preservando el formato original (PNG, JPEG, JBIG2).
- Las imágenes se guardan en `{output_dir}/assets/`.
- **Nomenclatura**: `{slug-titulo}_page{N}_img{M}.png`
- **Referencia en Markdown**: `![caption o 'Figure N'](assets/nombre_imagen.png)`
- Umbral de tamaño mínimo configurable para descartar iconos/decoraciones (default: `50x50 px`).
- Flag `--no-images` para omitir la extracción.

### 5.3 Extracción de Tablas

- **Estrategia dual**: `pdfplumber` para tablas con líneas visibles; `Camelot` para tablas lattice/stream.
- Salida en formato **GFM** con alineación de columnas.
- Detección de encabezado: primera fila en negrita o con fondo diferente.
- Sanitización de celdas: se escapan caracteres `|` y saltos de línea internos.
- **Fallback no fatal**: si la extracción falla, se inserta un marcador para revisión manual:

```markdown
<!-- TABLE_EXTRACTION_FAILED page=12 bbox=(72,300,540,450) -->
```

### 5.4 Procesamiento de Hipervínculos

- Extracción de anotaciones tipo `URI` del PDF vía PyMuPDF.
- Asociación de cada link con el texto visible más cercano mediante bounding box overlap.
- Links externos: `[texto del link](https://url.com)`
- Links internos al PDF: convertidos en anclas Markdown `[ver sección](#seccion)`.
- Flag `--no-links` para omitir la extracción.

### 5.5 CLI Interface

```bash
# Conversión simple
pdf2md convert libro.pdf -o ./output

# Conversión con opciones avanzadas
pdf2md convert libro.pdf \
  --output ./output \
  --extractor pymupdf \
  --table-extractor pdfplumber \
  --image-min-size 80 \
  --pages 1-50 \
  --no-links

# Batch processing
pdf2md batch ./libros/ -o ./markdowns/ --workers 4

# Inspección de estructura sin conversión
pdf2md inspect libro.pdf --json

# Ver ayuda
pdf2md --help
pdf2md convert --help
```

### 5.6 Python API

```python
from pathlib import Path
from pdf2md import ConversionService
from pdf2md.application.dto import ConversionRequest
from pdf2md.domain.value_objects import ConversionConfig
from pdf2md.infrastructure.extractors import PyMuPdfExtractor
from pdf2md.infrastructure.renderers import MarkdownRenderer
from pdf2md.infrastructure.storage import FileStorage

config = ConversionConfig(
    image_min_size=50,
    extract_tables=True,
    table_extractor="pdfplumber",
    extract_links=True,
    frontmatter=True,
)

service = ConversionService(
    extractor=PyMuPdfExtractor(),
    renderer=MarkdownRenderer(config),
    storage=FileStorage(output_dir=Path("./output")),
)

result = service.convert(ConversionRequest(pdf_path=Path("libro.pdf")))
print(result.output_path)   # ./output/libro.md
print(result.image_count)   # 42
print(result.table_count)   # 17
```

---

## 6. Configuración del Sistema

### 6.1 Archivo `pdf2md.toml`

```toml
[extractor]
engine = "pymupdf"          # pymupdf | pdfplumber
table_engine = "pdfplumber" # pdfplumber | camelot

[images]
enabled = true
min_size_px = 50
output_format = "png"       # png | original
assets_subdir = "assets"

[output]
heading_style = "atx"       # atx (#) | setext (===)
code_fence = "```"          # ``` | ~~~
line_width = 0              # 0 = sin wrap
frontmatter = true

[batch]
workers = 2
skip_on_error = true
report_file = "batch_report.json"
```

### 6.2 Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PDF2MD_LOG_LEVEL` | `INFO` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PDF2MD_WORKERS` | `2` | Workers para batch processing |
| `PDF2MD_CONFIG` | `pdf2md.toml` | Ruta al archivo de configuración |

---

## 7. Manejo de Errores

### 7.1 Jerarquía de Excepciones

```
Pdf2MdException (base)
├── ExtractionError           # Fallo al leer el PDF
│   ├── EncryptedPdfError     # PDF con contraseña
│   └── CorruptedPdfError     # Archivo dañado
├── TableExtractionError      # Fallo en tabla específica (NO FATAL)
├── ImageExtractionError      # Fallo en imagen específica (NO FATAL)
├── RenderingError            # Fallo al generar Markdown
└── StorageError              # Fallo al escribir en disco/S3
```

### 7.2 Política de Resiliencia

- Los errores de extracción de tabla/imagen son **no fatales**: se loggean con `loguru` y se inserta un marcador placeholder en el Markdown.
- En `batch` mode, `skip_on_error = true` permite continuar el lote; los errores se consolidan en `batch_report.json`.
- PDFs encriptados: se solicita password vía CLI (`--password`) o se skipea con advertencia en batch.

### 7.3 Formato de `batch_report.json`

```json
{
  "total": 25,
  "success": 23,
  "failed": 2,
  "results": [
    {
      "file": "libro_danado.pdf",
      "status": "error",
      "error": "CorruptedPdfError",
      "message": "EOF marker not found"
    }
  ]
}
```

---

## 8. Estrategia de Testing

### 8.1 Pirámide de Tests

| Nivel | Cobertura Objetivo | Herramienta | Descripción |
|-------|--------------------|-------------|-------------|
| **Unit** | ≥ 90% | pytest + pytest-mock | Dominio y use_cases con puertos mockeados |
| **Integration** | ≥ 70% | pytest + PDFs reales | Extractors e2e contra archivos PDF de fixture |
| **E2E** | Casos críticos | pytest + Click test client | CLI completo sobre PDFs de referencia |

### 8.2 Fixtures de Testing

| Fixture | Propósito |
|---------|-----------|
| `simple.pdf` | PDF de texto plano con 3 niveles de headings |
| `tables.pdf` | PDF con tablas lattice y stream |
| `images.pdf` | PDF con imágenes PNG y JPEG embebidas |
| `links.pdf` | PDF con hipervínculos externos e internos |
| `multicolumn.pdf` | PDF con layout de dos columnas |
| `encrypted.pdf` | PDF protegido — test de `EncryptedPdfError` |
| `corrupted.pdf` | PDF dañado — test de `CorruptedPdfError` |

### 8.3 Ejemplo de Test Unitario

```python
# tests/unit/use_cases/test_convert_pdf_use_case.py
def test_convert_pdf_calls_extractor_and_renderer(
    mock_extractor: MagicMock,
    mock_renderer: MagicMock,
    mock_storage: MagicMock,
    sample_pdf_document: PdfDocument,
    sample_markdown_document: MarkdownDocument,
) -> None:
    mock_extractor.extract.return_value = sample_pdf_document
    mock_renderer.render.return_value = sample_markdown_document

    use_case = ConvertPdfUseCase(mock_extractor, mock_renderer, mock_storage)
    result = use_case.execute(ConversionRequest(pdf_path=Path("libro.pdf")))

    mock_extractor.extract.assert_called_once_with(Path("libro.pdf"))
    mock_renderer.render.assert_called_once_with(sample_pdf_document)
    mock_storage.save.assert_called_once_with(sample_markdown_document)
    assert result.status == "success"
```

---

## 9. Cronograma de Desarrollo

| Sprint | Duración | Entregables |
|--------|----------|-------------|
| **Sprint 1** — Core Domain | 1 semana | Entidades, Value Objects, Ports (ABC). Tests unitarios del dominio al 100%. |
| **Sprint 2** — Extraction Layer | 1 semana | `PyMuPdfExtractor`, extracción de imágenes, `FileStorage`. Tests de integración básicos. |
| **Sprint 3** — Tables & Links | 1 semana | `PdfplumberTableExtractor`, `CamelotAdapter`, `LinkExtractor`. Tests con `tables.pdf` y `links.pdf`. |
| **Sprint 4** — Renderer & CLI | 1 semana | `MarkdownRenderer` completo, CLI Typer con todos los comandos. Tests E2E. |
| **Sprint 5** — Batch & Config | 3 días | `BatchConvertUseCase`, `pdf2md.toml`, `batch_report.json`, workers concurrentes. |
| **Sprint 6** — Polish & Docs | 3 días | README, documentación de API Python, ejemplos, publicación en PyPI. |

**Duración total estimada: ~5.5 semanas**

---

## 10. Métricas de Calidad

| Métrica | Objetivo |
|---------|----------|
| Cobertura de tests (unit) | ≥ 90% |
| Cobertura de tests (integración) | ≥ 70% |
| Tiempo de conversión — PDF 300 páginas | < 60 segundos |
| Tiempo de conversión — PDF 50 páginas | < 10 segundos |
| Pérdida de imágenes en PDFs de referencia | 0% |
| Tablas correctamente extraídas (PDFs de referencia) | ≥ 95% |
| Complejidad ciclomática máxima por función | ≤ 10 |
| Score Pylint | ≥ 8.5 / 10 |
| Score Mypy (strict mode) | 0 errores |

---

## 11. Dependencias (`pyproject.toml`)

```toml
[tool.poetry.dependencies]
python = "^3.12"
pymupdf = "^1.24"
pdfplumber = "^0.11"
camelot-py = { version = "^0.11", extras = ["cv"] }
Pillow = "^10.3"
tabulate = "^0.9"
pydantic = "^2.7"
typer = { version = "^0.12", extras = ["all"] }
loguru = "^0.7"
rich = "^13.7"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2"
pytest-cov = "^5.0"
pytest-mock = "^3.14"
factory-boy = "^3.3"
ruff = "^0.4"
mypy = "^1.10"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "UP", "ANN"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing"
testpaths = ["tests"]
```

---

*— Fin del Documento —*
