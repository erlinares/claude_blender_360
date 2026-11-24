# Paso a paso

Todos los comandos se corren desde la carpeta del repo. En macOS, Blender queda en `/Applications/Blender.app/Contents/MacOS/Blender`. Para no escribirlo cada vez:

```bash
export BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

## 0. Instalar herramientas
```bash
xcode-select --install          # git y herramientas básicas
brew install --cask blender     # o descarga desde https://www.blender.org/download/
$BLENDER --version              # debe decir Blender 4.2 o más nueva (probado: 5.3.0)
python3 --version               # 3.9 o superior
```

## 1. Entorno de Python
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 2. Descargar los assets CC0 (una sola vez, ~900 MB)
```bash
.venv/bin/python tools/blender/fetch_assets.py
```
Debes ver una línea por cada asset: `model tree_small_02 2k`, `texture coast_sand_01`, `hdri belfast_sunset_puresky 4k`… Quedan en `assets/polyhaven/`. Si se corta, vuelve a correrlo: se salta lo que ya bajó.

## 3. Texturas propias
```bash
.venv/bin/python tools/blender/make_textures.py
```
Crea `assets/blender/court.jpg` (cancha de 28 × 15 m con sus líneas) y `assets/blender/frond.png` (hoja de palma con transparencia).

## 4. El plano de lotes
```bash
.venv/bin/python tools/make_sample_lots.py
# 432 lotes en 24 manzanas, hueco de 97.0 m -> data/lotes.json
```
El parque se acomoda solo en el hueco más ancho entre manzanas. Para usar tu propio plano, ve a [PERSONALIZAR.md](PERSONALIZAR.md).

## 5. Prueba rápida (1 minuto)
Antes del render final, revisa que todo cargue:
```bash
$BLENDER -b -P tools/blender/build_park.py -- --light tarde --mode pano --res 1536 --samples 16 --stops 0,4,8
```
Salida esperada:
```
[parque] 82.4 x 90.0 m  (parque 69.5 m + estacionamiento)
render pano 0 llegada
... Saved: '.../renders/pano/tarde_0_llegada.jpg'
render pano 4 yoga
render pano 8 dron
listo
```
Abre `renders/pano/tarde_0_llegada.jpg`. Es una imagen 2:1 deformada en los bordes: así se ve un panorama equirectangular antes de ponerlo en el visor.

## 6. Render final (~11 min en M4)
```bash
./tools/blender/render_all.sh
# Más calidad:   RES=4096 SAMPLES=96 ./tools/blender/render_all.sh
```
Opciones de `build_park.py` (van después de `--`):

| Opción | Valores | Qué hace |
|---|---|---|
| `--light` | `tarde`, `dia` | Cielo HDRI, sol y luminarias encendidas al atardecer |
| `--mode` | `pano`, `still` | Panorama 360° (cámara equirectangular) o foto con lente normal |
| `--res` | 1024–8192 | Ancho en px (el panorama es ancho × ancho/2) |
| `--samples` | 16–256 | Muestras de Cycles: más = menos ruido y más tiempo |
| `--stops` | `all` o `0,2,5` | Qué puntos de cámara renderizar |
| `--vertical` | `1` | Fotos en 9:16 (para reels) |
| `--save` | `renders/parque.blend` | Guarda la escena para abrirla en Blender |
| `--out` | carpeta | Dónde guardar los renders (por defecto `renders/`) |

## 7. Visor web
```bash
.venv/bin/python tools/build_tour.py
.venv/bin/python -m http.server -d web/dist/tour 8000
```
Abre http://localhost:8000. Tiene que abrirse por http y no con doble clic, porque el navegador bloquea cargar imágenes como textura desde `file://`.

Para publicarlo, sube la carpeta `web/dist/tour/` a cualquier hosting estático (GitHub Pages, Netlify, Vercel o S3).

## 8. (Opcional) Abrir la escena en Blender
```bash
$BLENDER -b -P tools/blender/build_park.py -- --save renders/parque.blend
open renders/parque.blend
```
La colección `ASSETS` está excluida porque solo guarda los originales que se instancian. Lo visible está en `PARQUE`.
