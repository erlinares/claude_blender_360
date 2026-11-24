#!/bin/zsh
# Todo de punta a punta: entorno Python, assets CC0, texturas, plano de ejemplo, render y visor web.
set -e
cd "$(dirname "$0")"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python tools/blender/fetch_assets.py          # ~900 MB, una sola vez
.venv/bin/python tools/blender/make_textures.py
[[ -f data/lotes.json ]] || .venv/bin/python tools/make_sample_lots.py
./tools/blender/render_all.sh
.venv/bin/python tools/build_tour.py
echo "Abre el visor:  .venv/bin/python -m http.server -d web/dist/tour 8000  ->  http://localhost:8000"
