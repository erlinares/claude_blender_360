# Requisitos y rendimiento

## Equipo de referencia (donde se hizo el video)
- **Mac mini M4** (identificador Mac16,10), CPU de 10 núcleos (4 de rendimiento y 6 de eficiencia), GPU de 10 núcleos con Metal 4.
- **16 GB** de memoria unificada.
- macOS **26.6**, Blender **5.3.0**, Python 3.9.6 (el de macOS), Pillow 11, Homebrew 7.

## Tiempos medidos en el M4

| Tarea | Ajustes | Tiempo |
|---|---|---|
| Descarga de assets (una vez) | 16 modelos, 13 texturas 2K, 2 HDRI 4K (~900 MB) | 3–10 min, según tu internet |
| Construir la escena (sin render) | `--save renders/parque.blend` | ~20 s |
| Prueba rápida | 3 panoramas, 1536 px, 16 muestras | **41 s** |
| Render completo | 9 panoramas 3072 px, 48 muestras + 12 fotos 1920 px, 64 muestras | **~11 min** |

## Memoria
- Pico medido: **~6 GB** de RAM (proceso de Blender, escena completa con pasto disperso y selva).
- **8 GB**: funciona, pero cierra otras apps. Si se queda sin memoria, baja `--res` y la densidad de pasto (ver PERSONALIZAR.md).
- **16 GB o más**: recomendado.
- En Mac, la GPU comparte esa memoria (memoria unificada), así que no hay un requisito aparte de VRAM.

## Mínimos y otros equipos

| Equipo | ¿Funciona? | Notas |
|---|---|---|
| Mac con Apple Silicon (M1–M4) | Sí | Cycles usa la GPU con Metal en automático. M1 de 8 GB: ~2–3× más lento que el M4 |
| Mac Intel | Sí, lento | Sin GPU Metal compatible, Cycles corre en CPU: espera 5–10× más tiempo |
| Windows / Linux con NVIDIA | Sí, con un cambio | En `build_park.py` cambia `"METAL"` por `"OPTIX"` (RTX) o `"CUDA"`. Ajusta la ruta de Blender con `BLENDER=...` |
| Windows / Linux con AMD | Sí, con un cambio | Usa `"HIP"` |
| Sin GPU | Sí | El script cae solo a CPU si no hay GPU; funciona, pero lento |

`render_all.sh` y `run_all.sh` usan zsh (vienen en macOS). En Linux instala zsh o córrelos con bash; en Windows usa WSL o ejecuta los comandos de PASO_A_PASO.md a mano.

## Software
| Herramienta | Versión | Para qué |
|---|---|---|
| Blender | 5.3.0 probado (4.2 LTS o más nueva debería servir) | Construir la escena y renderizar con Cycles |
| Python | 3.9 o superior | Scripts fuera de Blender (descarga, texturas, plano y visor) |
| Pillow | 10 o superior | Texturas y optimización de JPG |
| Homebrew | opcional | `brew install --cask blender` |
| Navegador moderno | Chrome, Safari, Firefox | Ver el visor (WebGL) |

Blender trae su propio Python. `build_park.py` corre **dentro** de Blender (`blender -b -P ...`) y no necesita nada instalado aparte.

## Disco
- `assets/polyhaven/`: ~900 MB.
- `renders/`: ~20 MB (JPG).
- `.blend` guardado (opcional): ~600 MB.
- Visor final `web/dist/tour/`: ~10 MB.
