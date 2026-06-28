#!/usr/bin/env bash
# Convierte todos los XLSX de ./xlsx/ a ./output/<slug>/
# Cada libro queda en su propia carpeta con un .md por hoja.
set -u

cd "$(dirname "$0")/.."

mkdir -p output xlsx
LOG="output/_batch_xlsx.log"
echo "inicio: $(date '+%Y-%m-%d %H:%M:%S')" > "$LOG"

slugify() {
  python3 -c "
import sys, unicodedata, re
s = unicodedata.normalize('NFKD', sys.argv[1])
s = s.encode('ascii', 'ignore').decode('ascii').lower().strip()
s = re.sub(r'[^a-z0-9._-]+', '-', s)
s = re.sub(r'-+', '-', s).strip('-')
print(s or 'document')
" "$1"
}

total=0
ok=0
fail=0
skipped=0

echo "--- conversión de XLSX ---" | tee -a "$LOG"
for xlsx in xlsx/*.xlsx; do
  [ -f "$xlsx" ] || continue
  total=$((total + 1))

  stem=$(basename "$xlsx" .xlsx)
  slug=$(slugify "$stem")
  index_file="output/${slug}/_index.md"

  if [ -f "$index_file" ]; then
    echo "[skip] ya existe: $index_file" | tee -a "$LOG"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[run ] $stem -> $slug" | tee -a "$LOG"
  if xlsx2md convert "$xlsx" -o ./output >> "$LOG" 2>&1; then
    ok=$((ok + 1))
    echo "[ok  ] $slug" | tee -a "$LOG"
  else
    fail=$((fail + 1))
    echo "[fail] $slug" | tee -a "$LOG"
  fi
done

echo "" | tee -a "$LOG"
echo "total=$total ok=$ok fail=$fail skipped=$skipped" | tee -a "$LOG"
echo "fin: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
