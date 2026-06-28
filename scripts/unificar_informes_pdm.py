"""Unifica todos los informes individuales de items en un único documento consolidado."""
from __future__ import annotations

import re
from pathlib import Path

INFORMES_DIR = Path("output/pdm_seguridad_de_la_informacion_tics_2026/informes")
OUTPUT_FILE = INFORMES_DIR / "informe_consolidado.md"


def parse_item_report(text: str) -> dict | None:
    """Extrae los datos de un informe individual parseando sus secciones.

    Retorna None si el texto no parece un informe válido.
    """
    m = re.match(r"# Informe — Item (\d+)", text)
    if not m:
        return None
    numero = int(m.group(1))

    def extract_section(label: str) -> str:
        """Extrae el contenido de una sección delimitada por headers `## N. label`."""
        pattern = rf"## \d+\. {re.escape(label)}\s*\n(.*?)(?=\n## |\Z)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    def extract_bullet_value(text: str, label: str) -> str:
        """Extrae el valor de un bullet `**label:** valor`."""
        m = re.search(rf"^- \*\*{re.escape(label)}:\*\*\s*(.+?)(?=\n-|\n##|\Z)", text, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ""

    resumen = extract_section("Resumen ejecutivo")
    rec = extract_section("Recomendación y/u oportunidad de mejoramiento")
    accion = extract_section("Acción de mejora")
    actividades = extract_section("Actividades planificadas")
    cumplimiento = extract_section("Cumplimiento")
    resultado = extract_section("Resultado final esperado")
    observaciones = extract_section("Observaciones")

    return {
        "numero": numero,
        "recomendacion_resumen": extract_bullet_value(resumen, "Recomendación / Oportunidad de Mejora"),
        "accion_resumen": extract_bullet_value(resumen, "Acción de Mejora"),
        "resultado_resumen": extract_bullet_value(resumen, "Resultado Final esperado"),
        "responsable": extract_bullet_value(resumen, "Responsable"),
        "pct_cumplimiento": extract_bullet_value(resumen, "% Cumplimiento global"),
        "fecha_soporte": extract_bullet_value(resumen, "Fecha entrega de soporte"),
        "recomendacion": rec,
        "accion": accion,
        "actividades": actividades,
        "cumplimiento": cumplimiento,
        "resultado": resultado,
        "observaciones": observaciones,
    }


def build_consolidated(items: list[dict]) -> str:
    """Construye el documento consolidado."""
    items_sorted = sorted(items, key=lambda x: x["numero"])
    n = len(items_sorted)

    lines: list[str] = []

    # Encabezado
    lines.append("# Informe Consolidado — Plan de Mejoramiento (PDM) Seguridad de la Información TICS 2026")
    lines.append("")
    lines.append("> Documento unificado que reúne los **18 ítems** del Plan de Mejoramiento derivados del trabajo de auditoría interna al proceso de Gestión TICS, basado en la evaluación de conformidad con ISO/IEC 27001:2022 e ISO/IEC 27005:2022.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Información general del PDM
    lines.append("## 1. Información general del Plan de Mejoramiento")
    lines.append("")
    lines.append("| Campo | Valor |")
    lines.append("|-------|-------|")
    lines.append("| Objetivo | Realizar una evaluación del grado de conformidad de la organización con los requisitos y controles establecidos en la norma ISO/IEC 27001:2022, en concordancia con la ISO/IEC 27005:2022, identificando brechas y oportunidades de mejora que contribuyan al fortalecimiento continuo del SGSI. |")
    lines.append("| Jefe del departamento | RICARDO LIEVANO CARDONA |")
    lines.append("| Trabajo de auditoría a | GESTIÓN TICS |")
    lines.append("| Fecha de suscripción | 2025-10-14 |")
    lines.append("| Total de ítems del PDM | **18** |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Resumen ejecutivo del consolidado
    lines.append("## 2. Resumen ejecutivo consolidado")
    lines.append("")
    lines.append(f"El presente Plan de Mejoramiento está compuesto por **{n} ítems** derivados del trabajo de auditoría. La siguiente tabla ofrece una visión rápida del estado de cada acción:")
    lines.append("")
    lines.append("| # | Recomendación (resumen) | Acción de mejora | Responsable | % Cumplimiento |")
    lines.append("|---|--------------------------|------------------|-------------|------------------|")
    for it in items_sorted:
        rec_short = it["recomendacion_resumen"]
        if len(rec_short) > 120:
            rec_short = rec_short[:117] + "..."
        rec_short = rec_short.replace("|", "\\|").replace("\n", " ")
        acc_short = it["accion_resumen"]
        if len(acc_short) > 100:
            acc_short = acc_short[:97] + "..."
        acc_short = acc_short.replace("|", "\\|").replace("\n", " ")
        resp = it["responsable"] or "_(s/r)_"
        pct = it["pct_cumplimiento"] or "_(s/d)_"
        lines.append(f"| {it['numero']} | {rec_short} | {acc_short} | {resp} | {pct} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Detalle por item
    lines.append("## 3. Detalle por ítem")
    lines.append("")

    for it in items_sorted:
        num = it["numero"]
        lines.append(f"### 3.{num} Ítem {num}")
        lines.append("")

        # Resumen
        lines.append("**Resumen ejecutivo**")
        lines.append("")
        lines.append(f"- **Recomendación / Oportunidad de Mejora:** {it['recomendacion_resumen'] or '_(sin dato)_'}")
        lines.append(f"- **Acción de Mejora:** {it['accion_resumen'] or '_(sin dato)_'}")
        lines.append(f"- **Resultado Final esperado:** {it['resultado_resumen'] or '_(sin dato)_'}")
        lines.append(f"- **Responsable:** {it['responsable'] or 'Sin asignar'}")
        lines.append(f"- **% Cumplimiento global:** {it['pct_cumplimiento'] or 'Sin registrar'}")
        lines.append(f"- **Fecha entrega de soporte:** {it['fecha_soporte'] or 'Sin registrar'}")
        lines.append("")

        # Recomendación completa
        lines.append("**Recomendación y/u oportunidad de mejoramiento**")
        lines.append("")
        lines.append(it["recomendacion"] or "_(sin recomendación registrada)_")
        lines.append("")

        # Acción
        lines.append("**Acción de mejora**")
        lines.append("")
        lines.append(it["accion"] or "_(sin acción registrada)_")
        lines.append("")

        # Actividades
        lines.append("**Actividades planificadas**")
        lines.append("")
        if it["actividades"] and "_(sin actividades registradas)_" not in it["actividades"]:
            lines.append(it["actividades"])
            lines.append("")
        else:
            lines.append("_(sin actividades registradas)_")
            lines.append("")

        # Cumplimiento
        lines.append("**Cumplimiento**")
        lines.append("")
        if it["cumplimiento"]:
            lines.append(it["cumplimiento"])
            lines.append("")

        # Resultado final
        lines.append("**Resultado final esperado**")
        lines.append("")
        lines.append(it["resultado"] or "_(sin resultado registrado)_")
        lines.append("")

        # Observaciones
        lines.append("**Observaciones**")
        lines.append("")
        if it["observaciones"]:
            # Eliminar línea "_Generado a partir de..." y separadores finales
            obs = it["observaciones"]
            obs = re.sub(r"\n*---\s*\n*_Generado a partir de.*$", "", obs, flags=re.DOTALL).strip()
            obs = re.sub(r"\n*---\s*$", "", obs).strip()
            lines.append(obs)
            lines.append("")

        lines.append("---")
        lines.append("")

    # 4. Observaciones globales
    lines.append("## 4. Observaciones globales")
    lines.append("")
    sin_cumplimiento = sum(1 for it in items_sorted if not it["pct_cumplimiento"] or it["pct_cumplimiento"] in ("Sin registrar", "_(sin dato)_"))
    sin_fecha = sum(1 for it in items_sorted if not it["fecha_soporte"] or it["fecha_soporte"] in ("Sin registrar", "_(sin dato)_"))
    sin_responsable = sum(1 for it in items_sorted if not it["responsable"] or it["responsable"] in ("Sin asignar", "_(s/r)_"))

    lines.append(f"- **Total de ítems:** {n}")
    lines.append(f"- **Ítems sin % de cumplimiento global registrado:** {sin_cumplimiento} de {n}")
    lines.append(f"- **Ítems sin fecha de entrega de soporte:** {sin_fecha} de {n}")
    lines.append(f"- **Ítems sin responsable claramente asignado:** {sin_responsable} de {n}")
    lines.append("")
    lines.append("> **Nota importante:** Este documento fue generado automáticamente a partir de los informes individuales por ítem. Algunas celdas de los ítems 1-6 presentan truncamiento de texto debido a una limitación del parser `xlsx2md` con celdas multilínea. Para revisión detallada de cada ítem, consultar los archivos individuales `informes/item_NN.md`.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Documento generado automáticamente por `scripts/unificar_informes_pdm.py` a partir de los 18 informes individuales._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    # Leer todos los item_NN.md en orden
    items: list[dict] = []
    for path in sorted(INFORMES_DIR.glob("item_*.md")):
        m = re.search(r"item_(\d+)\.md", path.name)
        if not m:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            item = parse_item_report(text)
            if item:
                items.append(item)
        except Exception as e:
            print(f"Error procesando {path}: {e}")

    consolidado = build_consolidated(items)
    OUTPUT_FILE.write_text(consolidado, encoding="utf-8")
    print(f"Consolidado {len(items)} ítems en {OUTPUT_FILE}")
    print(f"Tamaño: {len(consolidado)} caracteres")


if __name__ == "__main__":
    main()