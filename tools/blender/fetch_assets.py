#!/usr/bin/env python3
"""Descarga assets CC0 de Poly Haven (modelos glTF, texturas PBR, cielos HDRI) a assets/polyhaven/."""
import json, os, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/polyhaven"
UA = {"User-Agent": "blender-tour-360-fetch/1.0"}

MODELS = ["tree_small_02", "jacaranda_tree", "island_tree_01", "island_tree_02", "island_tree_03", "fern_02",
          "grass_medium_01", "grass_medium_02", "street_lamp_01", "wooden_picnic_table", "painted_wooden_bench",
          "shrub_02", "shrub_04", "flower_gazania", "flower_heliophila", "coast_rocks_01"]
TEXTURES = ["thatch_roof_angled", "coral_stone_wall", "wood_floor_deck", "weathered_planks", "palm_tree_bark",
            "coast_sand_01", "cobblestone_floor_04", "asphalt_02", "leafy_grass", "forest_leaves_02", "concrete_floor_02",
            "bark_brown_02", "brushed_concrete"]
HDRIS = ["belfast_sunset_puresky", "kloofendal_48d_partly_cloudy_puresky"]
MAPS = {"Diffuse": "diff", "nor_gl": "nor", "Rough": "rough", "AO": "ao", "Displacement": "disp", "arm": "arm"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def save(url, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.write_bytes(get(url))


def files(aid):
    return json.loads(get(f"https://api.polyhaven.com/files/{aid}"))


def main():
    for aid in MODELS:
        f = files(aid)["gltf"]; res = "2k" if "2k" in f else sorted(f)[0]
        g = f[res]["gltf"]; d = OUT / "models" / aid
        save(g["url"], d / pathlib.Path(g["url"]).name)
        for rel, inc in g.get("include", {}).items():
            save(inc["url"], d / rel)
        print("model", aid, res, flush=True)
    for aid in TEXTURES:
        f = files(aid)
        for key, short in MAPS.items():
            if key in f and "2k" in f[key]:
                fmt = "jpg" if "jpg" in f[key]["2k"] else ("png" if "png" in f[key]["2k"] else None)
                if fmt:
                    save(f[key]["2k"][fmt]["url"], OUT / "textures" / aid / f"{short}.{fmt}")
        print("texture", aid, flush=True)
    for aid in HDRIS:
        f = files(aid)["hdri"]; res = "4k" if "4k" in f else "2k"
        save(f[res]["hdr"]["url"], OUT / "hdri" / f"{aid}.hdr")
        print("hdri", aid, res, flush=True)
    (OUT / "LICENSE.txt").write_text("Assets de Poly Haven (https://polyhaven.com), licencia CC0.\n")


if __name__ == "__main__":
    main()
