#!/usr/bin/env bash
# Renders cv/index.html to a PDF with headless Chrome, then stamps clean PDF metadata.
#
#   ./cv/build.sh            -> Ceyhun_Akar_CV.pdf in the repo root (public: no phone, no private sections)
#   ./cv/build.sh --private  -> ../private-cv/Ceyhun_Akar_CV_private.pdf, outside the repo.
#                               Fills the <!-- private:NAME --> markers from ../private-cv/NAME.html.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
python="${PYTHON:-$(command -v python3.13 || command -v python3)}"

src="$here/index.html"
out="$repo/Ceyhun_Akar_CV.pdf"

if [[ "${1:-}" == "--private" ]]; then
  private="$(cd "$repo/../private-cv" && pwd)"
  out="$private/Ceyhun_Akar_CV_private.pdf"
  # The filled-in copy lives next to the private parts, never in the repo tree.
  # A <base> tag keeps the relative font URLs pointing at cv/fonts.
  tmp="$private/.render.html"
  trap 'rm -f "$tmp"' EXIT
  "$python" - "$src" "$private" "$here" "$tmp" <<'PY'
import sys, pathlib, re
src, private, here, tmp = sys.argv[1:5]
html = pathlib.Path(src).read_text()
def fill(m):
    part = pathlib.Path(private, m.group(1) + ".html")
    return part.read_text() if part.exists() else ""
html = re.sub(r"<!-- private:([a-z]+) -->", fill, html)
html = html.replace(" (UTC+3)", "")  # keeps the longer contact line on one row
html = html.replace("</style>", "  /* the private copy carries an extra section */\n  body { line-height: 1.24; font-size: 8.7pt; } li { margin-bottom: 1px; } h2 { margin-top: 6px; }\n</style>", 1)
html = html.replace("<head>", f'<head>\n<base href="file://{here}/">', 1)
pathlib.Path(tmp).write_text(html)
PY
  src="$tmp"
fi

rm -f "$out"   # never re-stamp a stale PDF if Chrome fails
"$chrome" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf-no-header \
  --virtual-time-budget=15000 --run-all-compositor-stages-before-draw \
  --print-to-pdf="$out" "file://$src" 2>/dev/null

"$python" - "$out" <<'PY'
import sys
from pypdf import PdfReader, PdfWriter
path = sys.argv[1]
reader = PdfReader(path)
writer = PdfWriter(clone_from=reader)
writer.add_metadata({
    "/Title": "Ceyhun Akar - Data Engineer - CV",
    "/Author": "Ceyhun Akar",
    "/Subject": "Data Engineer: streaming pipelines and multi-tenant analytics platforms",
    "/Keywords": "Data Engineer, Apache Kafka, Apache Flink, PyFlink, Apache Spark, Apache Airflow, dbt, ClickHouse, PostgreSQL, Kubernetes, Docker, AWS, FastAPI, Python, SQL",
})
with open(path, "wb") as f:
    writer.write(f)
print(f"{path}: {len(reader.pages)} page(s)")
if len(reader.pages) != 1:
    sys.exit(f"{path}: expected 1 page, got {len(reader.pages)}")
PY
