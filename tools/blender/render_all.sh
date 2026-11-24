#!/bin/zsh
# Render final: 9 panoramas 360° (atardecer) + 12 fotos fijas (6 tomas × atardecer y día).
# Calidad usada en el video: ~11 min en Mac mini M4 (10 núcleos GPU, 16 GB).
# Variables opcionales: BLENDER=/ruta/a/Blender  RES=3072  SAMPLES=48
cd "$(dirname "$0")/../.."
B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
RES=${RES:-3072}; SAMPLES=${SAMPLES:-48}
[[ -x "$B" ]] || { echo "No encuentro Blender en $B (define BLENDER=...)"; exit 1; }
F="render|listo|parque|Error|Traceback"
$B -b -P tools/blender/build_park.py -- --light tarde --mode pano  --res $RES --samples $SAMPLES --stops all 2>&1 | grep -E "$F"
$B -b -P tools/blender/build_park.py -- --light tarde --mode still --res 1920 --samples 64 --stops all 2>&1 | grep -E "$F"
$B -b -P tools/blender/build_park.py -- --light dia   --mode still --res 1920 --samples 64 --stops all 2>&1 | grep -E "$F"
echo TERMINADO
