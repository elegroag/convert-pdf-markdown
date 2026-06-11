#!/usr/bin/env python3
"""Verification script: regenerate the output and report metrics.

Usage: python scripts/verify_output.py [pdf_path] [output_dir]

If no arguments are given, defaults to ``pdfs/VUE-JS-3-001.pdf`` and
``output-01/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src/ layout is importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger

from pdf2md.application.dto import ConversionRequest
from pdf2md.config.service_factory import build_default_service
from pdf2md.domain.value_objects import ConversionConfig

logger.remove()
logger.add(sys.stderr, level="INFO")


def _measure(text: str) -> dict[str, int]:
    lines = text.splitlines()
    return {
        "total_lines": len(lines),
        "blank_lines": sum(1 for ln in lines if not ln.strip()),
        "h1": sum(1 for ln in lines if ln.startswith("# ")),
        "h2": sum(1 for ln in lines if ln.startswith("## ")),
        "h3": sum(1 for ln in lines if ln.startswith("### ")),
        "h4": sum(1 for ln in lines if ln.startswith("#### ")),
        "h5": sum(1 for ln in lines if ln.startswith("##### ")),
        "code_blocks": sum(1 for ln in lines if ln.startswith("```") and not ln.startswith("````")),
        "images": sum(1 for ln in lines if ln.startswith("![") and "](" in ln),
        "max_line_len": max((len(ln) for ln in lines), default=0),
        "lines_under_80": sum(1 for ln in lines if 0 < len(ln) < 80),
    }


def main(pdf: str, outdir: str) -> int:
    pdf_path = Path(pdf)
    out_dir = Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = ConversionConfig()
    service = build_default_service(output_dir=out_dir, config=cfg)
    request = ConversionRequest(
        pdf_path=pdf_path, output_dir=out_dir, config=cfg
    )
    result = service.convert(request)
    if result.status != "success":
        print(f"ERROR: {result.error_message}")
        return 1

    md_path = result.output_path
    if md_path is None:
        print("ERROR: no output path")
        return 1
    text = md_path.read_text(encoding="utf-8")
    metrics = _measure(text)

    # YAML frontmatter validation.
    import yaml  # type: ignore[import-untyped]

    yaml_ok = False
    yaml_err = ""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            body = text[4:end]
            try:
                parsed = yaml.safe_load(body)
                yaml_ok = isinstance(parsed, dict)
            except yaml.YAMLError as exc:
                yaml_err = str(exc)

    print(f"PDF:              {pdf_path.name}")
    print(f"Output:           {md_path}")
    print(f"Pages:            {result.page_count}")
    print(f"Images extracted: {result.image_count}")
    print(f"Tables extracted: {result.table_count}")
    print()
    print("Markdown metrics:")
    for key, value in metrics.items():
        print(f"  {key:<16} {value}")
    print()
    if yaml_ok:
        print("YAML frontmatter: VALID (round-trips through yaml.safe_load)")
    else:
        print(f"YAML frontmatter: INVALID — {yaml_err}")
    return 0 if yaml_ok else 1


if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "pdfs/VUE-JS-3-001.pdf"
    out = sys.argv[2] if len(sys.argv) > 2 else "output-01"
    sys.exit(main(pdf, out))
