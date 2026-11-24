# Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `No encuentro Blender en ...` | Blender no está en `/Applications` | `export BLENDER=/ruta/a/Blender` |
| `GPU no disponible: ...` y el render va muy lento | No hay GPU compatible, o el tipo de dispositivo no es el correcto para tu GPU | En Mac Intel es normal (CPU). En PC, cambia `METAL` por `OPTIX`, `CUDA` o `HIP` |
| `FileNotFoundError: data/lotes.json` | Falta el plano | `python3 tools/make_sample_lots.py` |
| Error al cargar `.../assets/polyhaven/...` | La descarga quedó incompleta | Vuelve a correr `fetch_assets.py`. Si un archivo pesa 0 bytes, bórralo antes |
| `HTTP Error 429` / timeouts en la descarga | Límite de Poly Haven | Espera unos minutos y reintenta |
| El parque sale cortado o enorme | El hueco entre manzanas no mide 80–110 m o el plano no está en metros | Revisa las unidades y la rotación de tu `lotes.json` |
| Panorama negro o muy oscuro | El HDRI no cargó | Revisa `assets/polyhaven/hdri/*.hdr` |
| Mucho ruido o "puntitos" | Pocas muestras | Sube `--samples` (64–128) |
| Blender se cierra o la Mac se congela | Falta de memoria | Ver PERSONALIZAR.md, "Si tu equipo tiene poca memoria" |
| El visor se queda en "Cargando panorama…" | Abriste el archivo con doble clic (`file://`) | Sírvelo con `python3 -m http.server -d web/dist/tour` |
| El visor sale en blanco y la consola dice `THREE is not defined` | Sin internet para el CDN de three.js | Descarga `three.min.js` r128 y cambia el `<script src>` a la copia local |
| Costuras visibles en el panorama | Resolución impar o no 2:1 | Usa un `--res` par. El script ya fuerza la proporción 2:1 |
