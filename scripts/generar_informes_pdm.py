"""Parsea pdm.md y genera un informe Markdown por cada item de la tabla.

El archivo pdm.md exportado por xlsx2md mezcla dos formatos:

A) Items 1-6: una sola línea por item con 14 columnas separadas por `|`. Si
   una celda tiene saltos de línea, xlsx2md la "rompe" en varias filas con las
   demás columnas vacías. La primera fila del item contiene el item number y
   los datos de la primera línea de cada celda.

B) Items 7-N: el item inicia con `N | texto_recomendacion`, luego párrafos
   sueltos (algunos con `|`), y al final una línea con varias columnas
   (acción | actividad | % | fecha_ini | fecha_fin | soporte | resultado | resp).

Estrategia del parser:
1. Detectar items por el patrón `N |` (con o sin `|` inicial).
2. Para el formato A: la primera fila del item ES la fila principal con datos.
   Las filas siguientes con mayoría de celdas vacías son continuación de texto.
3. Para el formato B: se busca la fila "tabular" (con fecha y %) que marca el
   inicio de los datos de acción/actividad.
"""
from __future__ import annotations

import re
from pathlib import Path

INPUT = Path("output/pdm_seguridad_de_la_informacion_tics_2026/pdm.md")
OUT_DIR = Path("output/pdm_seguridad_de_la_informacion_tics_2026/informes")

ITEM_HEADER_RE = re.compile(r"^\s*\|?\s*(\d+)\s*\|(.*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PCT_RE = re.compile(r"^0?\.\d+$|^\d+%$|^\d+\.\d+%?$")


def split_cols(line: str) -> list[str]:
    line = line.rstrip("\n")
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def safe(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()


def join_paragraphs(parts: list[str]) -> str:
    out = [p.strip() for p in parts if p and p.strip()]
    return " ".join(out)


def parse_items(text: str) -> list[dict]:
    lines = text.splitlines()
    headers: list[tuple[int, int]] = []
    for i, ln in enumerate(lines):
        m = ITEM_HEADER_RE.match(ln)
        if m:
            num = int(m.group(1))
            if 1 <= num <= 50:
                headers.append((i, num))

    items: list[dict] = []
    for idx, (start_line, num) in enumerate(headers):
        end_line = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        block_lines = lines[start_line:end_line]
        items.append(parse_item_block(num, block_lines))
    return items


def is_action_row(cols: list[str]) -> bool:
    """Detecta fila con fecha Y porcentaje (formato B fila principal)."""
    has_date = any(DATE_RE.match(c) for c in cols)
    has_pct = any(PCT_RE.match(c) for c in cols)
    return has_date and has_pct and len(cols) >= 5


def is_activity_row(cols: list[str]) -> bool:
    """Fila de actividad desglosada (formato B): [Actividad | % | fecha_ini | fecha_fin]."""
    has_date = any(DATE_RE.match(c) for c in cols)
    has_pct = any(PCT_RE.match(c) for c in cols)
    return has_date and has_pct and 3 <= len(cols) <= 6


def parse_item_block(numero: int, block_lines: list[str]) -> dict:
    first = block_lines[0]
    m = ITEM_HEADER_RE.match(first)
    first_content = m.group(2).strip() if m else first
    rest_lines = block_lines[1:]

    first_cols = split_cols(first)
    # Si la primera fila tiene 14 columnas (formato A) o >= 8 con fecha (también A)
    is_format_a = (
        len(first_cols) == 14
        or (len(first_cols) >= 10 and any(DATE_RE.match(c) for c in first_cols))
    )

    if is_format_a:
        return parse_format_a(numero, first_cols, rest_lines, first_content)
    return parse_format_b(numero, first_content, rest_lines)


def parse_format_a(numero: int, first_cols: list[str], rest_lines: list[str], first_content: str) -> dict:
    """Formato A: la primera fila tiene 14 columnas: [Item, Rec, Acción, Act, %, fi, ff, soporte, pca, pac, resultado, resp, %cum, fecha].

    Estrategia: solo se concatena el texto de las columnas de "texto largo"
    (Recomendación, Acción, Actividad, Soporte, Resultado). Los campos
    estructurales (responsable, fechas, %) se toman únicamente de la primera
    fila para evitar contaminación por desalineamiento entre filas.
    """
    cols = first_cols[1:] if re.fullmatch(r"\d+", first_cols[0]) else first_cols
    if len(cols) > 13:
        cols = cols[:13]
    while len(cols) < 13:
        cols.append("")

    # Columnas "extendibles" (texto largo que puede tener saltos de línea)
    EXTENSIBLE = {0, 1, 2, 6, 9}  # Recomendación, Acción, Actividad, Soporte, Resultado
    celdas: list[list[str]] = [[c] if c else [] for c in cols]

    for ln in rest_lines:
        if not ln.strip():
            continue
        rc = split_cols(ln)
        if rc and re.fullmatch(r"\d+", rc[0]):
            rc = rc[1:]
        if len(rc) > 13:
            rc = rc[:13]
        if len(rc) < 13:
            rc = rc + [""] * (13 - len(rc))

        # Solo agregar a columnas "extendibles"
        for j in EXTENSIBLE:
            if j < len(rc) and rc[j]:
                celdas[j].append(rc[j])

    # Reconstruir los valores
    rec_parts = celdas[0]
    accion = " ".join(celdas[1]).strip()
    actividad_inicial = " ".join(celdas[2]).strip()
    pct_inicial = cols[3].strip()
    fi_inicial = cols[4].strip()
    ff_inicial = cols[5].strip()
    soporte_inicial = " ".join(celdas[6]).strip()
    pca_inicial = cols[7].strip()
    pct_accion = cols[8].strip()
    resultado = " ".join(celdas[9]).strip()
    responsable = cols[10].strip()
    pct_cumplimiento = cols[11].strip()
    fecha_soporte = cols[12].strip()

    # Construir la lista de actividades (una sola por item en formato A)
    actividades: list[dict] = []
    if actividad_inicial or pct_inicial:
        actividades.append({
            "pct": pct_inicial,
            "fi": fi_inicial,
            "ff": ff_inicial,
            "act_parts": [actividad_inicial] if actividad_inicial else [],
            "sop_parts": [soporte_inicial] if soporte_inicial else [],
            "pca": pca_inicial,
        })

    return {
        "numero": numero,
        "recomendacion": join_paragraphs(rec_parts),
        "accion": accion,
        "actividades": actividades,
        "resultado": resultado,
        "responsable": responsable,
        "pct_cumplimiento": pct_cumplimiento,
        "fecha_soporte": fecha_soporte,
        "pct_accion": pct_accion,
    }


def parse_format_b(numero: int, first_content: str, rest_lines: list[str]) -> dict:
    """Formato B: `N | recomendación`, párrafos sueltos, luego fila tabular."""
    # Buscar la fila principal de acción
    main_action_idx = None
    for i, ln in enumerate(rest_lines):
        cols = split_cols(ln)
        if is_action_row(cols):
            main_action_idx = i
            break

    if main_action_idx is None:
        return {
            "numero": numero,
            "recomendacion": join_paragraphs([first_content] + rest_lines),
            "accion": "",
            "actividades": [],
            "resultado": "",
            "responsable": "",
            "pct_cumplimiento": "",
            "fecha_soporte": "",
            "pct_accion": "",
        }

    rec_parts = [first_content] + rest_lines[:main_action_idx]
    main_cols = split_cols(rest_lines[main_action_idx])
    if main_cols and re.fullmatch(r"\d+", main_cols[0]):
        main_cols = main_cols[1:]

    accion = main_cols[0] if len(main_cols) >= 1 else ""
    actividad_inicial = main_cols[1] if len(main_cols) >= 2 else ""
    pct_inicial = main_cols[2] if len(main_cols) >= 3 else ""
    fi_inicial = main_cols[3] if len(main_cols) >= 4 else ""
    ff_inicial = main_cols[4] if len(main_cols) >= 5 else ""
    soporte_inicial = main_cols[5] if len(main_cols) >= 6 else ""

    resultado = ""
    responsable = ""
    pct_cumplimiento = ""
    fecha_soporte = ""

    extra = main_cols[6:] if len(main_cols) > 6 else []
    text_extras = [c for c in extra if c and not (DATE_RE.match(c) or PCT_RE.match(c))]
    if len(text_extras) >= 1:
        resultado = text_extras[0]
    if len(text_extras) >= 2:
        responsable = text_extras[1]
    pct_extras = [c for c in extra if PCT_RE.match(c)]
    if pct_extras:
        pct_cumplimiento = pct_extras[-1]
    date_extras = [c for c in extra if DATE_RE.match(c)]
    if date_extras:
        fecha_soporte = date_extras[-1]

    actividades: list[dict] = []
    if actividad_inicial or pct_inicial:
        actividades.append({
            "pct": pct_inicial,
            "fi": fi_inicial,
            "ff": ff_inicial,
            "act_parts": [actividad_inicial] if actividad_inicial else [],
            "sop_parts": [soporte_inicial] if soporte_inicial else [],
            "pca": "",
        })

    current_act = actividades[-1] if actividades else None
    for ln in rest_lines[main_action_idx + 1:]:
        if not ln.strip():
            continue
        cols = split_cols(ln)
        if len(cols) < 2:
            if current_act is not None:
                current_act["act_parts"].append(ln.strip())
            continue

        if is_activity_row(cols):
            if re.fullmatch(r"\d+", cols[0]):
                cols = cols[1:]
            act_txt = cols[0] if cols else ""
            pct_txt = cols[1] if len(cols) >= 2 else ""
            fi_txt = cols[2] if len(cols) >= 3 else ""
            ff_txt = cols[3] if len(cols) >= 4 else ""
            current_act = {
                "pct": pct_txt,
                "fi": fi_txt,
                "ff": ff_txt,
                "act_parts": [act_txt] if act_txt else [],
                "sop_parts": [],
                "pca": "",
            }
            actividades.append(current_act)
        elif len(cols) == 2 and cols[0] and cols[1] and not DATE_RE.match(cols[0]) and not DATE_RE.match(cols[1]):
            if not resultado:
                resultado = cols[0]
            if not responsable:
                responsable = cols[1]
        elif len(cols) == 3 and cols[0] and cols[2]:
            if current_act is not None and cols[0]:
                current_act["sop_parts"].append(cols[0])
            if not resultado:
                resultado = cols[1]
            if not responsable:
                responsable = cols[2]
        else:
            if current_act is not None:
                current_act["act_parts"].append(" | ".join(c for c in cols if c))

    return {
        "numero": numero,
        "recomendacion": join_paragraphs(rec_parts),
        "accion": accion,
        "actividades": actividades,
        "resultado": resultado,
        "responsable": responsable,
        "pct_cumplimiento": pct_cumplimiento,
        "fecha_soporte": fecha_soporte,
        "pct_accion": "",
    }


def build_report(item: dict) -> str:
    numero = item["numero"]
    lines: list[str] = []
    lines.append(f"# Informe — Item {numero}")
    lines.append("")
    lines.append("> Informe generado automáticamente a partir de la tabla del PDM de Seguridad de la Información TICS 2026.")
    lines.append("")
    lines.append("---")
    lines.append("")

    resumen_pairs = [
        ("Recomendación / Oportunidad de Mejora", item["recomendacion"]),
        ("Acción de Mejora", item["accion"]),
        ("Resultado Final esperado", item["resultado"]),
        ("Responsable", item["responsable"] or "Sin asignar"),
        ("% Cumplimiento global", item["pct_cumplimiento"] or "Sin registrar"),
        ("Fecha entrega de soporte", item["fecha_soporte"] or "Sin registrar"),
    ]
    lines.append("## 1. Resumen ejecutivo")
    lines.append("")
    for label, value in resumen_pairs:
        lines.append(f"- **{label}:** {value or '_(sin dato)_'}")
    lines.append("")

    lines.append("## 2. Recomendación y/u oportunidad de mejoramiento")
    lines.append("")
    lines.append(item["recomendacion"] or "_(sin recomendación registrada)_")
    lines.append("")

    lines.append("## 3. Acción de mejora")
    lines.append("")
    lines.append(item["accion"] or "_(sin acción registrada)_")
    lines.append("")

    lines.append("## 4. Actividades planificadas")
    lines.append("")
    if not item["actividades"]:
        lines.append("_(sin actividades registradas)_")
    else:
        lines.append("| # | % de la Acción | Fecha inicio | Fecha fin | Actividad | Soporte / Avance | % Cump. actividad |")
        lines.append("|---|----------------|--------------|-----------|-----------|------------------|--------------------|")
        for i, a in enumerate(item["actividades"], start=1):
            act_txt = safe(" ".join(a["act_parts"]))
            sop_txt = safe(" ".join(a["sop_parts"]))
            lines.append(
                f"| {i} | {safe(a['pct'])} | {safe(a['fi'])} | {safe(a['ff'])} | {act_txt} | {sop_txt} | {safe(a['pca'])} |"
            )
        lines.append("")

    lines.append("## 5. Cumplimiento")
    lines.append("")
    pct_accion = item.get("pct_accion", "") or "_(sin dato)_"
    pct_global = item["pct_cumplimiento"] or "_(sin dato)_"
    fecha_soporte = item["fecha_soporte"] or "_(sin dato)_"
    lines.append(f"- **% Cumplimiento acumulado por Acción de Mejora:** {pct_accion}")
    lines.append(f"- **% Cumplimiento global reportado:** {pct_global}")
    lines.append(f"- **Fecha de entrega de soporte:** {fecha_soporte}")
    lines.append("")

    lines.append("## 6. Resultado final esperado")
    lines.append("")
    lines.append(item["resultado"] or "_(sin resultado registrado)_")
    lines.append("")

    lines.append("## 7. Observaciones")
    lines.append("")
    obs = []
    if not item["pct_cumplimiento"]:
        obs.append("- ⚠️ No se ha registrado un porcentaje de cumplimiento global.")
    else:
        obs.append(f"- El cumplimiento reportado para esta acción es **{item['pct_cumplimiento']}**.")

    if item.get("pct_accion"):
        obs.append(f"- El porcentaje de cumplimiento acumulado por Acción de Mejora es **{item['pct_accion']}**.")

    if item["actividades"]:
        fechas_ini = [a["fi"] for a in item["actividades"] if a["fi"]]
        fechas_fin = [a["ff"] for a in item["actividades"] if a["ff"]]
        if fechas_ini or fechas_fin:
            fi = fechas_ini[0] if fechas_ini else "?"
            ff = fechas_fin[-1] if fechas_fin else "?"
            obs.append(f"- La acción tiene como ventana de ejecución **{fi} → {ff}**.")
    else:
        obs.append("- ⚠️ No hay actividades con fechas registradas para esta acción.")

    if not item["fecha_soporte"]:
        obs.append("- ⚠️ No se registra fecha de entrega de soporte. Se recomienda solicitar evidencia formal.")

    if item["responsable"]:
        obs.append(f"- **Responsable asignado:** {item['responsable']}.")

    n = len(item["actividades"])
    if n > 1:
        obs.append(f"- La Acción de Mejora se desglosa en **{n} actividades** con porcentajes parciales.")
    elif n == 1:
        obs.append("- La Acción de Mejora se compone de **1 actividad** principal.")
    else:
        obs.append("- ⚠️ No se identificaron actividades desglosadas en la tabla para esta acción.")

    lines.extend(obs)
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"_Generado a partir de `pdm.md` — Item {numero}._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    text = INPUT.read_text(encoding="utf-8")
    items = parse_items(text)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index_lines: list[str] = ["# Índice de informes — PDM Seguridad de la Información TICS 2026", ""]
    index_lines.append(f"_Total de items procesados: **{len(items)}**_")
    index_lines.append("")
    index_lines.append("| Item | Recomendación (resumen) | Acción de mejora (resumen) | Responsable | Informe |")
    index_lines.append("|------|--------------------------|------------------------------|-------------|---------|")

    for item in items:
        numero = item["numero"]
        rec = item["recomendacion"]
        acc = item["accion"]
        resp = item["responsable"]

        report = build_report(item)
        out_file = OUT_DIR / f"item_{int(numero):02d}.md"
        out_file.write_text(report, encoding="utf-8")

        rec_short = rec.split(".")[0][:140] + ("..." if len(rec) > 140 else "")
        acc_short = acc[:140] + ("..." if len(acc) > 140 else "")
        index_lines.append(
            f"| {numero} | {safe(rec_short)} | {safe(acc_short)} | {safe(resp) or '_(s/r)_'} | [informe](item_{int(numero):02d}.md) |"
        )

    index_path = OUT_DIR / "README.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"Generados {len(items)} informes en {OUT_DIR}")


if __name__ == "__main__":
    main()