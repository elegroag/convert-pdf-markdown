El servidor arranca correctamente con `uvx`. Te explico las tres formas de probarlo.

## 1. MCP Inspector (la herramienta oficial)

El [MCP Inspector](https://github.com/modelcontextprotocol/inspector) abre una UI web que arranca tu servidor como subproceso, lista las tools y te permite invocarlas. No requiere instalar nada globalmente.

### Instalación + arranque

```bash
# Desde la raíz del proyecto
npx @modelcontextprotocol/inspector -- \
  uvx --from "./[mcp]" pdf2md-mcp
```

Equivalente con `uv run`:

```bash
uv sync --extra mcp
npx @modelcontextprotocol/inspector -- \
  uv run --extra mcp pdf2md-mcp
```

Al ejecutar el comando, el inspector imprime dos URLs locales:

- **MCP Inspector UI** (http://localhost:5173) — para conectar y probar.
- **Proxy server** (http://localhost:3000) — endpoint HTTP para clientes remotos.

En la UI:

1. Pulsa **Connect** (no hay autenticación).
2. Ve a la pestaña **Tools** → `convert_pdf_to_markdown`, `convert_docx_to_markdown`
   o `convert_xlsx_to_markdown`.
3. Rellena los argumentos:
   ```json
   {
     "pdf_path": "/home/elegro/proyectos/python/convert-pdf-markdown/pdfs/VUE-JS-3-001.pdf",
     "output_path": "/tmp/pdf2md-inspector-test"
   }
   ```
   Para Excel, usa `xlsx_path` y un directorio de salida:
   ```json
   {
     "xlsx_path": "/ruta/a/libro.xlsx",
     "output_path": "/tmp/xlsx2md-inspector-test"
   }
   ```
4. Pulsa **Run Tool**. Verás el JSON de respuesta y, en la pestaña **Notifications**, los logs del servidor.

### Si prefieres una UI ya montada

```bash
git clone https://github.com/modelcontextprotocol/inspector.git
cd inspector
npm install
npm start
```

## 2. Cliente MCP mínimo en Python (sin Inspector)

Si solo quieres validar que el servidor responde, puedes hablar JSON-RPC directamente por stdio.

Crea `scripts/probe_mcp.py`:

```python
import json, subprocess, sys

proc = subprocess.Popen(
    ["uvx", "--from", "./[mcp]", "pdf2md-mcp"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)

def call(method: str, params: dict, _id=[0]):
    _id[0] += 1
    proc.stdin.write(json.dumps({
        "jsonrpc": "2.0", "id": _id[0], "method": method, "params": params
    }) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())

print("initialize:", call("initialize", {"protocolVersion": "2024-11-05"}))
print("tools/list:", call("tools/list", {}))
print("tools/call:", call("tools/call", {
    "name": "convert_pdf_to_markdown",
    "arguments": {
        "pdf_path": "/home/elegro/proyectos/python/convert-pdf-markdown/pdfs/VUE-JS-3-001.pdf",
        "output_path": "/tmp/pdf2md-probe",
    },
}))
proc.terminate()
```

```bash
uv run python scripts/probe_mcp.py
```

## 3. Integración real con Cursor / Claude Desktop

La forma definitiva de probarlo: configurar `mcp.json` (ya documentado en el README) y pedirle al modelo que ejecute la tool. Ejemplo de prompt:

> "Convierte el PDF `/ruta/a/libro.pdf` con `convert_pdf_to_markdown`, el Word
> `/ruta/a/informe.docx` con `convert_docx_to_markdown`, o el Excel
> `/ruta/a/reporte.xlsx` con `convert_xlsx_to_markdown` y muéstrame el JSON de salida."

---

### Tip de diagnóstico

Si el Inspector no conecta, lo más probable es el path. Usa rutas absolutas siempre:

```bash
# ✅ Funciona
npx @modelcontextprotocol/inspector -- \
  uvx --from "/home/elegro/proyectos/python/convert-pdf-markdown[mcp]" pdf2md-mcp

# ⚠️ Falla si abres otra terminal en cwd distinto
npx @modelcontextprotocol/inspector -- \
  uvx --from "./[mcp]" pdf2md-mcp
```

La opción `--from` con ruta absoluta es la recomendada para `mcp.json` y para el Inspector.

El servidor arranca bien por stdio. La clave es: el primer arranque tarda ~3-5 segundos (compilando el proyecto, instalando deps en el env aislado de uvx). Si Cursor intenta el handshake antes, falla con `-32000`. Las soluciones:

## 1. Usa path absoluto en `mcp.json` (esto es lo crítico)

`uvx --from "./[mcp]"` falla cuando Cursor no está en el directorio del proyecto. **Siempre** usa ruta absoluta. Ejemplo correcto para tu caso:

```json
{
  "mcpServers": {
    "pdf2md": {
      "command": "uvx",
      "args": [
        "--from",
        "/home/elegro/proyectos/python/convert-pdf-markdown[mcp]",
        "pdf2md-mcp"
      ]
    }
  }
}
```

## 2. Pre-resuelve el entorno (warm-up)

La primera vez, `uvx` construye el sdist e instala dependencias. Eso tarda. Ejecuta **una vez** este comando para que el entorno quede cacheado:

```bash
# Fuerza la construcción y caché del entorno uvx
uvx --from "/home/elegro/proyectos/python/convert-pdf-markdown[mcp]" \
  pdf2md-mcp </dev/null >/dev/null 2>&1
```

Tras esto, los arranques siguientes son ~0.5s.

## 3. Verifica que tu `mcp.json` está bien colocado

Cursor lee `mcp.json` desde:

- **Global**: `~/.cursor/mcp.json`
- **Proyecto**: `<proyecto>/.cursor/mcp.json` (recomendado)

Crea el de proyecto:

```bash
mkdir -p /home/elegro/proyectos/python/convert-pdf-markdown/.cursor
```

Y dentro pon lo del punto 1.

## 4. Diagnóstico directo desde la terminal

Si todavía falla, prueba a invocar el comando **exactamente** como lo haría Cursor (sin comillas que él no podría escapar):

```bash
# Simula el arranque que hace Cursor
uvx --from /home/elegro/proyectos/python/convert-pdf-markdown[mcp] pdf2md-mcp
```

Si esto imprime el banner y se queda esperando en stdin, **funciona**. El problema en Cursor es otra cosa.

## 5. Si `-32000` persiste: preconstruye el wheel

Algunos entornos no dejan a `uvx` construir sdist. Publica el proyecto como wheel instalable:

```bash
# Construye el paquete una vez
cd /home/elegro/proyectos/python/convert-pdf-markdown
uv build

# Luego, en mcp.json, usa el wheel directamente
```

`mcp.json` con wheel local:

```json
{
  "mcpServers": {
    "pdf2md": {
      "command": "uvx",
      "args": [
        "--from",
        "/home/elegro/proyectos/python/convert-pdf-markdown/dist/pdf2md-0.1.0-py3-none-any.whl[fastmcp]",
        "pdf2md-mcp"
      ]
    }
  }
}
```

---

### Resumen del fix más probable

1. Asegúrate de que `mcp.json` tiene **ruta absoluta** (no `./`).
2. Ejecuta **una vez** `uvx --from ".../convert-pdf-markdown[mcp]" pdf2md-mcp` para cachear el entorno.
3. Reinicia Cursor (la sesión MCP no se reconecta en caliente).
4. Verifica en la bandeja de MCP que el servidor sale como `Connected` (no `Disconnected`).

Si después de eso sigue el `-32000`, pega el contenido completo del log (Cursor → `Help` → `Toggle Developer Tools` → pestaña `MCP`) y miro el stacktrace exacto.
