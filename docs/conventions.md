# Convenciones de código — PDF2MD

## Idioma

- **Identificadores, comentarios en código, docstrings, mensajes de commit:** inglés.
- **Documentación, comunicación, issues, PR descriptions:** español.

## Estilo

- **Type hints obligatorios** en todo código nuevo. El proyecto apunta
  a `mypy --strict` (configurado en `pyproject.toml`).
- **Docstrings** en todas las funciones, clases y módulos públicos:
  Google-style para Python.
- **Line length**: 100 caracteres (configurado en ruff).
- **Imports** ordenados por `ruff` (`I` rule).
- **Sin** `print` en producción — usar `loguru.logger`.

## Estructura de clases

```python
# Cada clase pública:
# 1. Dataclass si modela estado.
# 2. Protocol / ABC si es un contrato.
# 3. Servicios como clases con métodos estáticos o de instancia claros.
# 4. Una sola responsabilidad (SRP).
```

## Naming

| Concepto | Convención | Ejemplo |
|----------|-----------|---------|
| Clase | PascalCase | `PdfDocument` |
| Función / método | snake_case | `extract_tables` |
| Variable | snake_case | `output_dir` |
| Constante | UPPER_SNAKE | `MAX_HEADING_LEVEL` |
| Módulo | snake_case | `markdown_renderer` |
| Test | `test_<unit>.py` | `test_convert_pdf_use_case.py` |
| Test class | `Test<Behaviour>` | `TestConvertPdfUseCaseSuccess` |

## Principios SOLID (recordatorio)

- **SRP** — Una clase / función = una responsabilidad.
- **OCP** — Extender sin modificar (puertos y adaptadores).
- **LSP** — Cualquier `IExtractor` debe poder sustituir a otro.
- **ISP** — Interfaces estrechas y específicas (`IImageExtractor`,
  no `IDocumentProcessor` con 20 métodos).
- **DIP** — Depender de abstracciones; el dominio no conoce PyMuPDF.

## Manejo de errores

- Excepciones de dominio (`Pdf2MdException` y subclases) en
  `domain/exceptions.py`.
- **Nunca** capturar `Exception` genérica en código de producción
  sin relanzar. Si lo haces, loguea el trace y re-empaqueta en una
  excepción de dominio.
- Tabla / imagen: errores **no fatales**. Marcar con un placeholder
  en el Markdown y continuar.

## Testing

- **Cobertura objetivo**: ≥ 90 % en unit, ≥ 70 % en integration.
- **Un assert por comportamiento** (varios asserts OK si prueban el
  mismo comportamiento).
- **No** usar `print` en tests — usar `pytest.fail`, `pytest.raises`,
  `caplog` o `capsys`.
- **Mocks** vía `pytest-mock` o `unittest.mock.MagicMock` con
  `spec=` apuntando al puerto que se está sustituyendo.
- **Fixtures** en `conftest.py` solo si se usan en ≥ 2 archivos.

## Git

- Mensajes de commit en español, formato:

  ```
  tipo(scope): descripción breve

  Cuerpo opcional.
  ```

  Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- **No commit** sin que los tests pasen localmente.
- **PR** debe incluir el resultado de `pytest --cov=pdf2md`.

## Performance

- Procesamiento por página — nunca cargar el PDF completo en memoria
  más de lo necesario.
- Batch usa `ThreadPoolExecutor` (I/O-bound, no CPU-bound).
- Si en el futuro el cuello de botella es CPU, cambiar a
  `ProcessPoolExecutor` o `multiprocessing`.
