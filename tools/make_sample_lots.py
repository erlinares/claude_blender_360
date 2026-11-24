#!/usr/bin/env python3
"""Genera data/lotes.json de ejemplo: dos hileras de manzanas con un hueco central donde vive el parque.

build_park.py solo necesita, por lote, su polígono ("p": "x,y x,y ...", en metros) y su manzana ("mz").
Para usar tu propio plano, sustituye data/lotes.json por uno con ese formato (ver docs/PERSONALIZAR.md).

Uso: python3 tools/make_sample_lots.py [--manzanas 12] [--hueco 97] [--salida data/lotes.json]
"""
import argparse, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--manzanas", type=int, default=12, help="manzanas a cada lado del parque")
ap.add_argument("--hueco", type=float, default=97.0, help="ancho del hueco entre manzanas (parque + 2 calles de 7.3 m)")
ap.add_argument("--fondo", type=float, default=18.0, help="fondo de cada lote (m)")
ap.add_argument("--frente", type=float, default=10.0, help="frente de cada lote (m)")
ap.add_argument("--lotes", type=int, default=9, help="lotes por columna de cada manzana")
ap.add_argument("--salida", default="data/lotes.json")
a = ap.parse_args()

CALLE, PASO = 7.3, 45.0            # ancho de calle entre manzanas y separación de manzana a manzana
ANCHO_MZ = 2 * a.fondo + 1.5       # dos columnas de lotes espalda con espalda
Y0 = 35.0
lotes, mz = [], 0

def manzana(x0):
    global mz
    mz += 1
    for col in range(2):
        xa = x0 + col * (a.fondo + 1.5); xb = xa + a.fondo
        for i in range(a.lotes):
            ya = Y0 + i * a.frente; yb = ya + a.frente
            p = f"{xa:.1f},{ya:.1f} {xb:.1f},{ya:.1f} {xb:.1f},{yb:.1f} {xa:.1f},{yb:.1f}"
            lotes.append({"id": f"MZ{mz:02d}-L{len([l for l in lotes if l['mz'] == mz]) + 1:02d}", "mz": mz,
                          "m2": round(a.fondo * a.frente, 2), "p": p})

x = 25.0
for _ in range(a.manzanas):
    manzana(x); x += PASO
x = x - PASO + ANCHO_MZ + a.hueco  # salto del parque
for _ in range(a.manzanas):
    manzana(x); x += PASO

out = ROOT / a.salida
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"proyecto": "ejemplo", "unidades": "m", "lotes": lotes}, ensure_ascii=False))
print(f"{len(lotes)} lotes en {mz} manzanas, hueco de {a.hueco} m -> {out.relative_to(ROOT)}")
