#!/usr/bin/env bash
# Convierte todos los PDFs de ./pdfs/ a ./output/<slug>/<slug>.md
# Cada PDF queda en su propia carpeta para evitar colisiones de assets.
#
# El slug replica exactamente la lógica de AnchorSlug.slugify():
#   - minúsculas
#   - elimina tildes (NFKD + descarte de no-ASCII)
#   - colapsa runs de [^a-z0-9._-] a un solo '-'
#   - recorta '-' inicial/final
set -u

cd "$(dirname "$0")/.."

mkdir -p output
LOG="output/_batch.log"
echo "inicio: $(date '+%Y-%m-%d %H:%M:%S')" > "$LOG"

slugify() {
  # $1 = texto a slugificar
  python3 -c "
import sys, unicodedata
s = unicodedata.normalize('NFKD', sys.argv[1])
s = s.encode('ascii', 'ignore').decode('ascii').lower().strip()
import re
s = re.sub(r'[^a-z0-9._-]+', '-', s)
s = re.sub(r'-+', '-', s).strip('-')
print(s or 'document')
" "$1"
}

total=0
ok=0
fail=0
skipped=0
renamed=0

# Primera pasada: renombra carpetas cuyo nombre no coincide con el slug del .md
# (solo afecta las corridas previas donde se usó un slug bash distinto).
echo "--- pasada 0: renombrado de carpetas a slug canónico ---" | tee -a "$LOG"
for d in output/*/; do
  [ -d "$d" ] || continue
  dir_name=$(basename "$d")
  md_in=$(find "$d" -maxdepth 1 -name "*.md" | head -1)
  [ -z "$md_in" ] && continue
  md_stem=$(basename "$md_in" .md)
  if [ "$dir_name" != "$md_stem" ]; then
    target="output/${md_stem}"
    if [ ! -e "$target" ]; then
      mv "$d" "$target"
      echo "[mv  ] $dir_name/ -> $md_stem/" | tee -a "$LOG"
      renamed=$((renamed + 1))
    else
      echo "[!   ] colisión al renombrar $dir_name; ya existe $md_stem/" | tee -a "$LOG"
    fi
  fi
done
echo "" | tee -a "$LOG"

# Segunda pasada: convertir PDFs pendientes.
echo "--- pasada 1: conversión de PDFs ---" | tee -a "$LOG"
for pdf in pdfs/*.pdf; do
  [ -f "$pdf" ] || continue
  total=$((total + 1))

  stem=$(basename "$pdf" .pdf)
  slug=$(slugify "$stem")
  out_dir="output/${slug}"
  md_file="${out_dir}/${slug}.md"

  if [ -f "$md_file" ]; then
    echo "[skip] ya existe: $md_file" | tee -a "$LOG"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[run ] $stem -> $slug" | tee -a "$LOG"
  mkdir -p "$out_dir"
  if pdf2md convert "$pdf" -o "$out_dir" >> "$LOG" 2>&1; then
    ok=$((ok + 1))
    echo "[ok  ] $slug" | tee -a "$LOG"
  else
    fail=$((fail + 1))
    echo "[FAIL] $slug (ver $LOG)" | tee -a "$LOG"
  fi
done

echo "" | tee -a "$LOG"
echo "fin: $(date '+%Y-%m-%d %H:%M:%S')  total=$total ok=$ok fail=$fail skipped=$skipped renamed=$renamed" | tee -a "$LOG"
