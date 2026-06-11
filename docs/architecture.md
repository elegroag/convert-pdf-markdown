# Architecture — PDF2MD Converter

## Visión general

PDF2MD sigue **Arquitectura Hexagonal (Ports & Adapters)** estricta.
El dominio no conoce PyMuPDF, pdfplumber, TOML ni el sistema de
archivos; sólo interactúa con abstracciones (`IExtractor`, `IRenderer`,
`IStorage`, `IConfigLoader`, `IBatchRunner`).

## Capas

```
┌─────────────────────────────────────────────────────────────┐
│  1. Interface (entrada)                                      │
│     - CLI: Typer en interface/cli/app.py                     │
│     - API: FastAPI en interface/api/server.py (opcional)     │
│     - Tests E2E (CLI runner + clientes HTTP)                  │
└─────────────────────────────────────────────────────────────┘
                          │ llama a
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Application (orquestación pública)                       │
│     - ConversionService (façade Python)                       │
│     - DTOs: ConversionRequest, ConversionResult,              │
│             InspectionResult                                  │
└─────────────────────────────────────────────────────────────┘
                          │ delega a
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Domain (núcleo, sin I/O ni librerías externas)           │
│     - Entities: PdfDocument, PdfPage, ImageAsset, TableNode,  │
│                 MarkdownDocument, MarkdownPage               │
│     - Value Objects: ContentBlock, PageContent, Link,         │
│                       ConversionConfig, BatchConfig           │
│     - Ports: IExtractor, IRenderer, IStorage, ITableExtractor│
│              IImageExtractor, ILinkExtractor, IBatchRunner,  │
│              IConfigLoader                                    │
│     - Services: AnchorSlug, HeadingInferer, FrontmatterBuilder│
│     - Use Cases: ConvertPdfUseCase, BatchConvertUseCase      │
│     - Exceptions: Pdf2MdException + jerarquía                 │
└─────────────────────────────────────────────────────────────┘
                          │ implementado por
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Infrastructure (adaptadores hacia el exterior)           │
│     - Extractors: PyMuPdfExtractor, PdfplumberTableExtractor,│
│                   CamelotTableExtractor (opcional)            │
│     - Renderers: MarkdownRenderer, HtmlRenderer               │
│     - Storage: FileStorage, InMemoryStorage,                  │
│                ThreadPoolBatchRunner                          │
│     - Config: TomlConfigLoader, helpers funcionales, factory  │
└─────────────────────────────────────────────────────────────┘
```

## Reglas de dependencia

- **Dominio** no importa de `application`, `infrastructure` ni `interface`.
- **Application** solo importa del dominio.
- **Infrastructure** puede importar de todos los anteriores (implementa
  los puertos del dominio y consume los servicios del dominio).
- **Interface** puede importar de application, infrastructure y config
  para construir el Composition Root.

## Flujo de una conversión

1. **CLI/API** recibe la llamada y construye un `ConversionRequest`.
2. **`ConversionService.convert`** lo traduce a un `ConvertPdfRequest`
   del dominio.
3. **`ConvertPdfUseCase.execute`**:
   1. Llama `IExtractor.extract(pdf_path)` → `PdfDocument`.
   2. Llama `IRenderer.render(document)` → `MarkdownDocument`.
   3. Llama `IStorage.save(markdown, source=document)` → `Path` del `.md`.
4. Los bytes de las imágenes se persisten desde el `PdfDocument`
   original (no viajan por el `MarkdownDocument`).
5. **`ConvertPdfUseCase`** empaqueta un `ConvertPdfResult`.
6. **`ConversionService`** lo traduce a un `ConversionResult` (DTO) y
   lo devuelve al caller.

## Servicios de dominio

- **`AnchorSlug`** — Genera slugs GitHub-style. Usado por
  `FileStorage` (nombres de archivo) y por el renderer (anclas).
- **`HeadingInferer`** — Recorre todas las páginas de un `PdfDocument`
  y devuelve un mapa `font_size → nivel (1-3)` basado en la frecuencia
  de tamaños de fuente.
- **`FrontmatterBuilder`** — Convierte un `PdfMetadata` + page_count
  en un bloque YAML.

Estos servicios son **puros** (sin I/O, sin librerías externas) y se
prueban de forma aislada en `tests/unit/domain/services/`.

## Configuración

`IConfigLoader` es un puerto; `TomlConfigLoader` es el adaptador por
defecto. La función `build_default_service(output_dir, config)` en
`config/service_factory.py` es el **Composition Root** — el único
lugar donde se cablean los adaptadores concretos. Cualquier consumidor
puede construir su propio `ConversionService` con adaptadores
diferentes (e.g. S3Storage, un extractor propio) sin tocar el dominio.

## Testing

| Tipo | Qué prueba | Velocidad |
|------|-----------|-----------|
| Unit (dominio) | Lógica pura sin librerías externas | < 50 ms |
| Unit (servicios) | Servicios de aplicación con mocks de puertos | < 50 ms |
| Unit (infraestructura) | Adaptadores con mocks de librerías | < 100 ms |
| Unit (interface) | CLI con `CliRunner`, mocks del servicio | < 100 ms |
| Integration | PDFs reales generados con PyMuPDF | < 1 s |

Pirámide objetivo: ≥ 90 % unit, ≥ 70 % integración. La cobertura
actual es 86 % total con 100 % en la capa de dominio.
