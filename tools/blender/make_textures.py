#!/usr/bin/env python3
"""Texturas propias para Blender: duela de básquetbol (28 x 15 m) y fronda de palma con alfa."""
import math, random, pathlib
from PIL import Image, ImageDraw, ImageFilter
OUT = pathlib.Path(__file__).resolve().parents[2] / "assets/blender"; OUT.mkdir(parents=True, exist_ok=True)
random.seed(4)
# --- cancha: 100 px por metro
S = 100; W, H = 28 * S, 15 * S
im = Image.new("RGB", (W, H), (61, 111, 120)); d = ImageDraw.Draw(im)
for _ in range(60000):
    x, y = random.randrange(W), random.randrange(H); c = random.randint(-10, 10); d.point((x, y), (61 + c, 111 + c, 120 + c))
key_w, key_l = int(4.9 * S), int(5.8 * S)
d.rectangle([0, H // 2 - key_w // 2, key_l, H // 2 + key_w // 2], fill=(47, 92, 100)); d.rectangle([W - key_l, H // 2 - key_w // 2, W, H // 2 + key_w // 2], fill=(47, 92, 100))
lw = int(0.05 * S); white = (240, 240, 234)
d.rectangle([lw // 2, lw // 2, W - lw // 2, H - lw // 2], outline=white, width=lw)
d.line([W // 2, 0, W // 2, H], fill=white, width=lw)
r = int(1.8 * S); d.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r], outline=white, width=lw)
for x0 in (0, W - key_l):
    d.rectangle([x0, H // 2 - key_w // 2, x0 + key_l, H // 2 + key_w // 2], outline=white, width=lw)
for cx in (key_l, W - key_l): d.ellipse([cx - r, H // 2 - r, cx + r, H // 2 + r], outline=white, width=lw)
R3, bx = 6.75 * S, 1.575 * S; a = math.asin(6.6 / 6.75)
for side in (0, 1):
    cx = bx if side == 0 else W - bx
    pts = [(cx + (R3 * math.cos(t) if side == 0 else -R3 * math.cos(t)), H / 2 + R3 * math.sin(t)) for t in [-a + i * 2 * a / 120 for i in range(121)]]
    d.line(pts, fill=white, width=lw)
    xe = pts[0][0]
    d.line([(0 if side == 0 else W, H / 2 - 6.6 * S), (xe, H / 2 - 6.6 * S)], fill=white, width=lw)
    d.line([(0 if side == 0 else W, H / 2 + 6.6 * S), (xe, H / 2 + 6.6 * S)], fill=white, width=lw)
im.save(OUT / "court.jpg", quality=90)
# --- fronda de palma (RGBA 2048 x 512): raquis + foliolos
FW, FH = 2048, 512
fr = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); d = ImageDraw.Draw(fr); cy = FH // 2
greens = [(62, 112, 40), (78, 130, 48), (92, 145, 56), (54, 100, 36), (104, 150, 60)]
for x in range(30, FW - 20, 9):
    t = x / FW; length = (1 - t * 0.8) * cy * 0.97 * min(1, t / 0.06)
    for s in (-1, 1):
        g = random.choice(greens); droop = random.uniform(0.8, 1.15)
        tip = (x + 70 * (1 - t) + 20, cy + s * length * droop)
        mid = (x + 25, cy + s * length * 0.5)
        d.line([(x, cy), mid, tip], fill=g + (255,), width=random.randint(7, 10))
        d.line([(x, cy), mid], fill=(min(g[0] + 30, 255), min(g[1] + 30, 255), g[2], 255), width=2)
d.line([(0, cy), (FW, cy)], fill=(190, 172, 104, 255), width=12)
fr.save(OUT / "frond.png")
print("ok", OUT)
