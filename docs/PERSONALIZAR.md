# Personalizar

## Tu propio plano de lotes
`build_park.py` solo lee esto de `data/lotes.json`:
```json
{"lotes": [
  {"mz": 1, "p": "25.0,35.0 43.0,35.0 43.0,45.0 25.0,45.0"},
  {"mz": 1, "p": "44.5,35.0 62.5,35.0 62.5,45.0 44.5,45.0"}
]}
```
- `p`: vértices del polígono del lote, `x,y` en **metros**, separados por espacios.
- `mz`: número de manzana.
- El parque se pone en el **hueco más ancho** entre manzanas consecutivas sobre el eje X. Ese hueco debe medir unos 80–110 m, porque las amenidades están diseñadas para un parque de ~80 × 70 m.

### Desde AutoCAD (DWG/DXF)
1. Convierte el DWG a DXF (`brew install libredwg` y luego `dwg2dxf plano.dwg`).
2. Lee las polilíneas cerradas de la capa de lotes con [`ezdxf`](https://ezdxf.mozman.at/) y asigna la manzana por el texto que cae dentro de cada polígono.
3. Rota el plano para que las manzanas queden alineadas con X y escribe el JSON de arriba.

Prueba también con el generador: `python3 tools/make_sample_lots.py --manzanas 6 --hueco 90 --frente 12`.

## Mover o agregar puntos 360°
En `build_park.py`, lista `PANOS`:
```python
("mirador", (W2 - 11, 10, 8.22 + EYE), "Desde el mirador"),
#  id         x       z   altura         nombre en el visor
```
`x` es el eje a lo ancho del parque (0 = centro) y `z` va del fondo (0) a la avenida (`PARK_D`). Si agregas un punto, el visor y el minimapa lo toman solos.

## Fotos fijas
Lista `STILLS`: `(id, posición de cámara, punto al que mira, lente en mm)`. Para agregar el nombre de una foto en la galería, edita `NAMES` en `tools/build_tour.py`.

## Luz y hora del día
- Cambia el HDRI por otro de https://polyhaven.com/hdris: agrégalo a `HDRIS` en `fetch_assets.py` y cambia su nombre en `build_park.py`.
- Si el sol no coincide con el cielo, ajusta la rotación del mapping del mundo (`200` / `120` grados) y `sun_rot`.
- Para más o menos luz usa `scene.view_settings.exposure`.

## Calidad contra tiempo

| Uso | `--res` | `--samples` | Tiempo por panorama (M4) |
|---|---|---|---|
| Prueba | 1536 | 16 | ~10 s |
| Web / redes (la del video) | 3072 | 48 | ~40–60 s |
| Visor VR / impresión | 6144 | 128 | varios minutos; haz primero una prueba con `--stops 0` |

## Si tu equipo tiene poca memoria
- Baja la densidad de `scatter(...)` (el tercer argumento) para el pasto y la selva.
- Usa `--res 2048`.
- En `fetch_assets.py` cambia las texturas de `"2k"` a `"1k"`.

## Otra GPU
En `build_park.py` cambia `prefs.compute_device_type = "METAL"` por `"OPTIX"` o `"CUDA"` (NVIDIA), o por `"HIP"` (AMD).
