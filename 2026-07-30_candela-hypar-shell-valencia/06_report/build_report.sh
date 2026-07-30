#!/usr/bin/env bash
# Render the A4 report to PDF with headless Chrome (5 pages).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$HERE/environmental_report.pdf" --virtual-time-budget=20000 \
  "file://$HERE/environmental_report.html" 2>/dev/null
python3 - "$HERE/environmental_report.pdf" <<'PY'
import re, sys
d = open(sys.argv[1], "rb").read()
print("pages: %d  |  %.2f MB" % (len(re.findall(rb"/Type\s*/Page[^s]", d)), len(d)/1e6))
PY
