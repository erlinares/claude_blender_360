# Cómo funciona por dentro

## Flujo
```
data/lotes.json ─┐
assets CC0 ──────┼─> build_park.py (Blender -b) ─> renders/pano/*.jpg + panos.json ─┐
texturas propias ┘                                renders/fotos/*.jpg ─────────────┼─> build_tour.py ─> web/dist/tour/
                                                                                    web/src/tour360.template.html ┘
```

## 1. Del plano al terreno (`build_park.py`, sección "datos")
- Lee cada lote (polígono en metros y su manzana) y calcula el rectángulo de cada manzana.
- Ordena las manzanas de izquierda a derecha y busca **el hueco más ancho**: ahí va el parque. Al hueco le resta dos calles de 7.3 m y lo que queda es el ancho del parque.
- Dibuja los lotes vecinos como terreno desmontado con estacas blancas en las esquinas, para que el panorama tenga contexto urbano real.

## 2. Escena 100 % por código
- `bpy.ops.wm.read_factory_settings(use_empty=True)`: escena vacía, sin depender de nada abierto antes.
- **Materiales PBR** (`pbr()`): color, rugosidad y desplazamiento de Poly Haven con proyección en caja (`BOX`), para no tener que desenvolver UVs.
- **Modelos glTF** (`import_asset()`): árboles, faroles, bancas y rocas se importan una vez en la colección oculta `ASSETS` y se **instancian**, lo que gasta poca memoria.
- **Palmas**: tronco + frondas hechas con la textura `frond.png` (alfa y translucidez).
- **Dispersión** (`scatter()`): Geometry Nodes reparten selva, sotobosque y pasto sobre mallas con semilla fija, así que cada corrida da el mismo resultado.
- **Amenidades**: cancha hundida, mirador de madera, palapas con techo de palma, juegos, yoga, ceiba de lectura, asadores y estacionamiento. Todo son primitivas (`box`, `cyl`, `cone`, `bar`) con materiales PBR.

## 3. Luz
- **Atardecer**: HDRI `belfast_sunset_puresky` girado 200°, sol cálido bajo, faroles y guirnaldas encendidos (luces puntuales y focos emisivos) y exposición −0.35.
- **Día**: HDRI `kloofendal_48d_partly_cloudy_puresky` y sol alto.
- Gestión de color **AgX** con contraste "Medium High" para que no se quemen los cielos.

## 4. Cámara 360°
```python
cam_data.type = "PANO"
cam_data.panorama_type = "EQUIRECTANGULAR"
scene.render.resolution_x, scene.render.resolution_y = RES, RES // 2   # siempre 2:1
cam.rotation_euler = (radians(90), 0, 0)                                # horizonte al centro
```
Cada punto (`PANOS`) está a 1.65 m, la altura de los ojos, salvo el mirador (sobre la plataforma), la cancha (3 m abajo) y el dron (55 m). Las coordenadas se guardan en `renders/pano/panos.json` para que el visor dibuje el minimapa y los saltos.

## 5. Render
- Cycles en GPU Metal, con todas las GPUs detectadas activadas.
- 48 muestras + **OpenImageDenoise**: limpio y rápido.
- `use_persistent_data`: entre un panorama y el siguiente no se vuelve a cargar la escena.
- Rebotes: 6 de luz y 16 de transparencia, que necesitan las frondas con alfa.

## 6. Visor (`tour360.template.html`)
- three.js r128 desde cdnjs. Una esfera invertida con el panorama como textura y la cámara al centro.
- Arrastrar o deslizar para mirar, rueda o pellizco para el zoom (campo de visión).
- **Puntos de salto**: para cada otro panorama se calcula el ángulo y la distancia con las coordenadas de `panos.json`, y se proyecta un círculo en esa dirección.
- Minimapa SVG con tu posición y un cono hacia donde miras, y galería de fotos de día y atardecer.
- `build_tour.py` inyecta los metadatos en la plantilla y comprime los JPG en modo progresivo.
