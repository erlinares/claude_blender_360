#!/usr/bin/env python3
"""Arma web/dist/tour/ (visor 360 + panoramas + fotos) a partir de renders/ de Blender."""
import json, pathlib, shutil
from PIL import Image

root = pathlib.Path(__file__).resolve().parent.parent
rend, out = root / "renders", root / "web/dist/tour"
(out / "pano").mkdir(parents=True, exist_ok=True); (out / "fotos").mkdir(parents=True, exist_ok=True)
meta = json.loads((rend / "pano/panos.json").read_text())
panos = []
for i, p in enumerate(meta["panos"]):
    src = rend / "pano" / f"tarde_{i}_{p['id']}.jpg"
    if not src.exists():
        continue
    dst = out / "pano" / src.name
    Image.open(src).convert("RGB").save(dst, quality=86, optimize=True, progressive=True)
    panos.append({**p, "file": f"pano/{src.name}"})
meta["panos"] = panos
NAMES = {"still_llegada": "Llegada por la avenida principal", "still_cancha": "Cancha de básquetbol hundida",
         "still_ceiba": "Ceiba con espacios de lectura", "still_yoga": "Yoga bajo el árbol central",
         "still_aerea": "Vista aérea del parque central", "still_mirador": "Mirador de madera"}
fotos = []
for light in ("tarde", "dia"):
    for key, name in NAMES.items():
        src = rend / "fotos" / f"{light}_{key}.jpg"
        if src.exists():
            dst = out / "fotos" / src.name
            Image.open(src).convert("RGB").save(dst, quality=86, optimize=True, progressive=True)
            fotos.append({"light": light, "name": name, "file": f"fotos/{src.name}"})
tpl = (root / "web/src/tour360.template.html").read_text(encoding="utf-8")
html = tpl.replace("{{META}}", json.dumps(meta, ensure_ascii=False)).replace("{{FOTOS}}", json.dumps(fotos, ensure_ascii=False))
(out / "index.html").write_text(html, encoding="utf-8")
size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
print(f"{len(panos)} panoramas, {len(fotos)} fotos, {size/1e6:.1f} MB -> {out}")
