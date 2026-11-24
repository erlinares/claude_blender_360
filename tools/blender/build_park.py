"""
Construye el parque central de un desarrollo de lotes en Blender (Cycles) y renderiza
panoramas 360° y fotos fijas.

Uso:
  Blender -b -P tools/blender/build_park.py -- --light tarde --mode pano --res 4096 --samples 96 --stops all
  Blender -b -P tools/blender/build_park.py -- --light dia --mode still --res 1920 --samples 128 --stops 0,2,8
  Blender -b -P tools/blender/build_park.py -- --save renders/parque.blend   (solo construir y guardar)

Coordenadas: X = x local (hacia MZ 11), Y = -z local (z crece hacia la avenida), Z = altura.
El marco del parque se calcula de data/lotes.json: el hueco más ancho entre dos manzanas consecutivas.
"""
import bpy, bmesh, json, math, os, random, sys, pathlib
from mathutils import Vector, Euler, Matrix

ROOT = pathlib.Path(__file__).resolve().parents[2]
PH = ROOT / "assets/polyhaven"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
LIGHT = arg("--light", "tarde"); MODE = arg("--mode", "pano"); RES = int(arg("--res", "2048")); SAMPLES = int(arg("--samples", "64"))
STOPS = arg("--stops", "all"); SAVE = arg("--save"); OUTDIR = ROOT / arg("--out", "renders")
random.seed(11)
rr = random.uniform

# ------------------------------------------------------------------ escena limpia
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
ASSETS = bpy.data.collections.new("ASSETS"); scene.collection.children.link(ASSETS)
WORLDC = bpy.data.collections.new("PARQUE"); scene.collection.children.link(WORLDC)
bpy.context.view_layer.layer_collection.children["ASSETS"].exclude = True

# ------------------------------------------------------------------ datos del DWG
D = json.loads((ROOT / "data/lotes.json").read_text())
lots = [[tuple(map(float, p.split(","))) for p in l["p"].split()] + [l["mz"]] for l in D["lotes"]]
ext = {}
for l in D["lotes"]:
    pts = [tuple(map(float, p.split(","))) for p in l["p"].split()]
    e = ext.setdefault(l["mz"], [1e9, -1e9, 1e9, -1e9])
    for x, y in pts: e[0] = min(e[0], x); e[1] = max(e[1], x); e[2] = min(e[2], y); e[3] = max(e[3], y)
order = sorted(ext.values(), key=lambda e: e[0])
gap, gA, gB = -1, None, None
for a, b in zip(order, order[1:]):
    if b[0] - a[1] > gap: gap, gA, gB = b[0] - a[1], a, b
STREET = 7.3
PW = gap - 2 * STREET; W2 = PW / 2
PXp = (gA[1] + gB[0]) / 2; PZ0p = min(gA[2], gB[2]); PZ1p = max(gA[3], gB[3])
PD = PZ1p - PZ0p; PARK_D = PD - 20.5
ZMIN = min(e[2] for e in ext.values()) - PZ0p; ZMAX = max(e[3] for e in ext.values()) - PZ0p
PIT = dict(x=0.0, z=34.0, w=40.0, d=26.0, depth=3.0)
print(f"[parque] {PW:.1f} x {PD:.1f} m  (parque {PARK_D:.1f} m + estacionamiento)")
def V(x, z, y=0.0): return Vector((x, -z, y))

# ------------------------------------------------------------------ Cycles
scene.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = "GPU"
except Exception as e:
    print("GPU no disponible:", e)
scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True
try: scene.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception: pass
scene.render.use_persistent_data = True; scene.cycles.max_bounces = 6; scene.cycles.transparent_max_bounces = 16
scene.view_settings.view_transform = "AgX"
try: scene.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass
scene.render.image_settings.file_format = "JPEG"; scene.render.image_settings.quality = 90

# ------------------------------------------------------------------ materiales
def tex_dir(name): return PH / "textures" / name
def set_in(node, names, val):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs: node.inputs[n].default_value = val; return
def link_in(nt, out, node, names):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs: nt.links.new(out, node.inputs[n]); return

def pbr(name, tex, tile=2.0, rough=0.85, bump=0.25, tint=None, uv=False, metal=0.0, coord="Object"):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes
    b = N["Principled BSDF"]; set_in(b, "Roughness", rough); set_in(b, "Metallic", metal)
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
    nt.links.new(tc.outputs["UV" if uv else coord], mp.inputs["Vector"])
    d = tex_dir(tex)
    def img(file, noncolor=False):
        p = d / file
        if not p.exists(): return None
        n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(str(p), check_existing=True)
        if noncolor: n.image.colorspace_settings.name = "Non-Color"
        if not uv: n.projection = "BOX"; n.projection_blend = 0.25
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    diff = img("diff.jpg") or img("diff.png")
    if diff:
        if tint:
            mix = N.new("ShaderNodeMixRGB"); mix.blend_type = "MULTIPLY"; mix.inputs["Fac"].default_value = 1.0; mix.inputs[2].default_value = (*tint, 1)
            nt.links.new(diff.outputs["Color"], mix.inputs[1]); link_in(nt, mix.outputs[0], b, "Base Color")
        else: link_in(nt, diff.outputs["Color"], b, "Base Color")
    r = img("rough.jpg", True) or img("rough.png", True)
    if r: link_in(nt, r.outputs["Color"], b, "Roughness")
    dp = img("disp.png", True) or img("disp.jpg", True)
    if dp and bump > 0:
        bn = N.new("ShaderNodeBump"); bn.inputs["Strength"].default_value = bump; bn.inputs["Distance"].default_value = 0.05
        nt.links.new(dp.outputs["Color"], bn.inputs["Height"]); link_in(nt, bn.outputs["Normal"], b, "Normal")
    return m

def flat(name, rgb, rough=0.6, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    set_in(b, "Base Color", (*rgb, 1)); set_in(b, "Roughness", rough); set_in(b, "Metallic", metal)
    if emit: set_in(b, ["Emission Color", "Emission"], (*emit, 1)); set_in(b, "Emission Strength", strength)
    return m

def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

M = {
    "grass": pbr("pasto", "leafy_grass", 2.5, 0.95, 0.4, tint=(0.85, 1.35, 0.5)),
    "lot": pbr("lote", "leafy_grass", 3, 0.95, 0.3, tint=(0.8, 0.95, 0.55)),
    "forest": pbr("suelo_selva", "forest_leaves_02", 3, 1.0, 0.5),
    "pavers": pbr("adoquin", "cobblestone_floor_04", 2.0, 0.8, 0.5, tint=srgb("#f3e6cc")),
    "asphalt": pbr("asfalto", "asphalt_02", 4, 0.9, 0.3),
    "sand": pbr("arena", "coast_sand_01", 2, 1.0, 0.5),
    "deck": pbr("deck", "wood_floor_deck", 2.5, 0.7, 0.3),
    "wood": pbr("madera", "weathered_planks", 1.5, 0.75, 0.3),
    "thatch": pbr("palma_techo", "thatch_roof_angled", 2.2, 1.0, 0.8, tint=(1.9, 1.45, 0.85)),
    "stone": pbr("piedra_coral", "coral_stone_wall", 2.5, 0.95, 0.8),
    "concrete": pbr("concreto", "concrete_floor_02", 3, 0.85, 0.2),
    "palmbark": pbr("tronco_palma", "palm_tree_bark", 1.2, 0.95, 0.6),
    "bark": pbr("corteza", "bark_brown_02", 1.5, 1.0, 0.6),
    "rubber": flat("hule", srgb("#3b4950"), 0.9),
    "metal": flat("metal", srgb("#9aa3a8"), 0.35, 0.9), "darkmetal": flat("metal_negro", srgb("#2a2c2e"), 0.45, 0.8),
    "white": flat("blanco", srgb("#f1f1ec"), 0.5), "red": flat("rojo", srgb("#d8573a"), 0.45), "green": flat("verde", srgb("#3c9a4c"), 0.4),
    "yogaA": flat("tapete_a", srgb("#3f8f99"), 0.8), "yogaB": flat("tapete_b", srgb("#a6c7a8"), 0.8), "line": flat("pintura", srgb("#eeeeea"), 0.7),
    "bulb": flat("foco", srgb("#fff2d0"), 0.3, emit=srgb("#ffc670"), strength=0.0),
    "holds": [flat(f"presa{i}", srgb(c), 0.6) for i, c in enumerate(["#e8643c", "#3c9be8", "#f2c53d", "#8f49c9"])],
}
# duela con UV
court = bpy.data.materials.new("duela"); court.use_nodes = True; nt = court.node_tree
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(str(ROOT / "assets/blender/court.jpg"))
nt.links.new(ti.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"]); set_in(nt.nodes["Principled BSDF"], "Roughness", 0.55)
# fronda con alfa y translucidez
frond = bpy.data.materials.new("fronda"); frond.use_nodes = True; nt = frond.node_tree; b = nt.nodes["Principled BSDF"]
fi = nt.nodes.new("ShaderNodeTexImage"); fi.image = bpy.data.images.load(str(ROOT / "assets/blender/frond.png"))
nt.links.new(fi.outputs["Color"], b.inputs["Base Color"]); nt.links.new(fi.outputs["Alpha"], b.inputs["Alpha"])
set_in(b, "Roughness", 0.55); set_in(b, ["Subsurface Weight"], 0.0)
try: frond.blend_method = "HASHED"
except Exception: pass
if "Transmission Weight" in b.inputs: b.inputs["Transmission Weight"].default_value = 0.0
try:
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent"); tr.inputs["Color"].default_value = (0.25, 0.45, 0.08, 1)
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs["Fac"].default_value = 0.25
    out = nt.nodes["Material Output"]
    nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    # el alfa también en el translúcido: mezclar con transparente
    tp = nt.nodes.new("ShaderNodeBsdfTransparent"); mix2 = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fi.outputs["Alpha"], mix2.inputs["Fac"]); nt.links.new(tp.outputs[0], mix2.inputs[1]); nt.links.new(mix.outputs[0], mix2.inputs[2])
    nt.links.new(mix2.outputs[0], out.inputs["Surface"])
except Exception as e: print("translucidez:", e)

# ------------------------------------------------------------------ geometría
def put(obj, coll=WORLDC):
    coll.objects.link(obj); return obj
def mesh_obj(name, verts, faces, mat, coll=WORLDC):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat); return put(o, coll)
_box_cache = {}
def box(w, h, d, mat, x, z, y, ry=0.0, coll=WORLDC):
    """caja de ancho w (X), alto h, fondo d (z local); (x,z) centro, y = base"""
    me = bpy.data.meshes.new("caja"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("caja", me); o.scale = (w, d, h); o.location = V(x, z, y + h / 2); o.rotation_euler = (0, 0, -ry)
    o.data.materials.append(mat); put(o, coll); return o
def cyl(r, h, mat, x, z, y, seg=16, r2=None, coll=WORLDC, rot=None):
    me = bpy.data.meshes.new("cil"); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("cil", me); o.location = V(x, z, y + h / 2); o.data.materials.append(mat)
    if rot: o.rotation_euler = rot
    put(o, coll); return o
def bar(p0, p1, r, mat, coll=WORLDC):
    a, b2 = Vector(p0), Vector(p1); dvec = b2 - a; o = cyl(r, dvec.length, mat, 0, 0, 0, 10, coll=coll)
    o.location = (a + b2) / 2; o.rotation_euler = dvec.to_track_quat("Z", "Y").to_euler(); return o
def cone(r, h, mat, x, z, y, seg=16, rotz=0.0, coll=WORLDC, open_end=True):
    me = bpy.data.meshes.new("cono"); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=not open_end, segments=seg, radius1=r, radius2=0.0, depth=h); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("cono", me); o.location = V(x, z, y); o.rotation_euler = (0, 0, rotz); o.data.materials.append(mat); put(o, coll); return o
def plane(x0, z0, x1, z1, y, mat, name="plano", coll=WORLDC):
    return mesh_obj(name, [V(x0, z0, y), V(x1, z0, y), V(x1, z1, y), V(x0, z1, y)], [(0, 3, 2, 1)], mat, coll)
def disc(x, z, r, y, mat, seg=48, coll=WORLDC):
    vs = [V(x, z, y)] + [V(x + r * math.cos(t), z + r * math.sin(t), y) for t in [i / seg * 2 * math.pi for i in range(seg)]]
    return mesh_obj("disco", vs, [(0, i + 1, (i + 1) % seg + 1) for i in range(seg)][::-1] and [(0, (i + 1) % seg + 1, i + 1) for i in range(seg)], mat, coll)
def grid(name, x0, z0, x1, z1, cell, keep, y, mat, coll=WORLDC):
    """malla en cuadrícula; keep(xc, zc) decide qué celdas existen"""
    nx, nz = int(round((x1 - x0) / cell)), int(round((z1 - z0) / cell)); vs, fs, idx = [], [], {}
    def vi(i, j):
        k = (i, j)
        if k not in idx: idx[k] = len(vs); vs.append(V(x0 + i * cell, z0 + j * cell, y))
        return idx[k]
    for i in range(nx):
        for j in range(nz):
            if keep(x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell): fs.append((vi(i, j), vi(i, j + 1), vi(i + 1, j + 1), vi(i + 1, j)))
    return mesh_obj(name, vs, fs, mat, coll)
def inside(r, x, z): return r[0] <= x <= r[2] and r[1] <= z <= r[3]

# ------------------------------------------------------------------ assets de Poly Haven
def import_asset(aid, target_h=None):
    d = PH / "models" / aid; g = next(d.glob("*.gltf"), None)
    if not g: print("falta", aid); return None
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(g))
    new = [o for o in bpy.data.objects if o not in before]
    c = bpy.data.collections.new(aid); ASSETS.children.link(c)
    for o in new:
        for uc in o.users_collection: uc.objects.unlink(o)
        c.objects.link(o)
    if target_h:
        bpy.context.view_layer.update()
        zs = [(o.matrix_world @ Vector(cn)).z for o in new if o.type == "MESH" for cn in o.bound_box]
        h = max(zs) - min(zs) if zs else 1
        s = target_h / h
        for o in new:
            if o.parent is None: o.scale = (o.scale[0] * s, o.scale[1] * s, o.scale[2] * s); o.location = o.location * s
    return c
def inst(coll, x, z, y=0.0, s=1.0, rot=None, parent=WORLDC):
    if coll is None: return None
    e = bpy.data.objects.new(coll.name + "_i", None); e.instance_type = "COLLECTION"; e.instance_collection = coll
    e.location = V(x, z, y); e.scale = (s, s, s); e.rotation_euler = (0, 0, rot if rot is not None else rr(0, 6.283)); put(e, parent); return e

A = {}
for aid, h in [("tree_small_02", 6), ("jacaranda_tree", 12), ("island_tree_01", 8), ("island_tree_02", 8), ("island_tree_03", 7), ("fern_02", 1.2),
               ("grass_medium_01", 0.5), ("grass_medium_02", 0.45), ("street_lamp_01", 3.8), ("wooden_picnic_table", None), ("painted_wooden_bench", None),
               ("shrub_02", 1.4), ("shrub_04", 1.2), ("flower_gazania", None), ("flower_heliophila", None), ("coast_rocks_01", None)]:
    A[aid] = import_asset(aid, h)

# ------------------------------------------------------------------ palmas procedurales
def make_frond_mesh():
    L, Wd, n = 4.6, 1.25, 18; vs, fs, uvs = [], [], []
    for i in range(n + 1):
        t = i / n; x = t * L; drop = -0.32 * x * x * 0.25
        for j, s in enumerate((-1, 0, 1)):
            vs.append((x, s * Wd / 2, drop + abs(s) * 0.12 * (1 - t)))
    for i in range(n):
        for j in range(2):
            a = i * 3 + j; fs.append((a, a + 3, a + 4, a + 1))
    me = bpy.data.meshes.new("fronda"); me.from_pydata(vs, [], fs); me.update()
    uv = me.uv_layers.new(); k = 0
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index; i, j = divmod(vi, 3); uv.data[li].uv = (i / n, j / 2)
    me.materials.append(frond); return me
FROND = make_frond_mesh()
PALMS = []
for variant in range(3):
    c = bpy.data.collections.new(f"palma_{variant}"); ASSETS.children.link(c)
    h = [8.5, 10.5, 7.0][variant]; lean = [0.8, 1.6, 0.4][variant]
    cu = bpy.data.curves.new("tronco", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 1.0; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(3)
    for k, t in enumerate([0, 0.35, 0.7, 1.0]):
        bp = sp.bezier_points[k]; bp.co = (lean * t * t, 0, h * t); bp.handle_left_type = bp.handle_right_type = "AUTO"; bp.radius = 0.24 - 0.08 * t
    tob = bpy.data.objects.new("tronco", cu); cu.materials.append(M["palmbark"]); c.objects.link(tob)
    crown = Vector((lean, 0, h))
    for k in range(13):
        f = bpy.data.objects.new("fronda", FROND); f.location = crown
        f.rotation_euler = Euler((0, -rr(-0.35, 0.45) - (0.5 if k > 10 else 0), k / 13 * 6.283 + rr(-0.15, 0.15)), "YZX"); s = rr(0.85, 1.1); f.scale = (s, s, s); c.objects.link(f)
    for k in range(5):
        co = bpy.data.objects.new("coco", None); co.empty_display_type = "SPHERE"
    for k in range(5):
        cyl(0.11, 0.2, M["darkmetal"] if False else M["bark"], 0, 0, 0, 8, coll=c).location = crown + Vector((rr(-0.25, 0.25), rr(-0.25, 0.25), -0.35))
    PALMS.append(c)
def palm(x, z, s=None): return inst(random.choice(PALMS), x, z, 0, s or rr(0.85, 1.15))

# ------------------------------------------------------------------ geometry nodes: dispersión
def scatter(obj, coll, density, smin, smax, seed=0, zrot=True):
    ng = bpy.data.node_groups.new("disp_" + coll.name, "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes; gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    dist = N.new("GeometryNodeDistributePointsOnFaces"); dist.inputs["Density"].default_value = density; dist.inputs["Seed"].default_value = seed
    ci = N.new("GeometryNodeCollectionInfo"); ci.inputs["Collection"].default_value = coll; ci.inputs["Separate Children"].default_value = True; ci.inputs["Reset Children"].default_value = True; ci.transform_space = "ORIGINAL"
    iop = N.new("GeometryNodeInstanceOnPoints"); iop.inputs["Pick Instance"].default_value = True
    rv = N.new("FunctionNodeRandomValue"); rv.data_type = "FLOAT_VECTOR"
    en = lambda socks: [s for s in socks if s.enabled]
    vin = [s for s in rv.inputs if s.enabled and s.type == "VECTOR"]; vin[0].default_value = (0, 0, 0); vin[1].default_value = (0, 0, 6.283 if zrot else 0)
    rs = N.new("FunctionNodeRandomValue"); rs.data_type = "FLOAT"
    fin = [s for s in rs.inputs if s.enabled and s.type == "VALUE"]; fin[0].default_value = smin; fin[1].default_value = smax
    ri = N.new("FunctionNodeRandomValue"); ri.data_type = "INT"
    iin = [s for s in ri.inputs if s.enabled and s.type == "INT"]; iin[0].default_value = 0; iin[1].default_value = 64
    L = ng.links.new
    L(gi.outputs[0], dist.inputs["Mesh"]); L(dist.outputs["Points"], iop.inputs["Points"]); L(ci.outputs[0], iop.inputs["Instance"])
    L([s for s in rv.outputs if s.enabled][0], iop.inputs["Rotation"]); L([s for s in rs.outputs if s.enabled][0], iop.inputs["Scale"])
    L([s for s in ri.outputs if s.enabled][0], iop.inputs["Instance Index"])
    L(iop.outputs[0], go.inputs[0])
    mod = obj.modifiers.new("disp", "NODES"); mod.node_group = ng; return obj

# ================================================================== SUELOS
pitR = (PIT["x"] - PIT["w"] / 2, PIT["z"] - PIT["d"] / 2, PIT["x"] + PIT["w"] / 2, PIT["z"] + PIT["d"] / 2)
# selva: suelo grande + dispersión de árboles fuera de la franja urbanizada
strip = (-230, ZMIN - 10, 230, ZMAX + 12)   # franja con calles y lotes visibles
parkR = (-W2, 0, W2, PD)
grid("suelo_selva", -700, -600, 700, 700, 5, lambda x, z: not inside((strip[0] + 3, strip[1] + 3, strip[2] - 3, strip[3] - 3), x, z), -0.02, M["forest"])
grid("calles", strip[0] - 6, strip[1] - 6, strip[2] + 6, strip[3] + 6, 1.0, lambda x, z: not inside(parkR, x, z), 0.0, M["asphalt"])
def jungle_keep(x, z): return not inside((strip[0] - 2, strip[1] - 4, strip[2] + 2, strip[3] + 4), x, z)
jg = grid("selva_disp", -420, -260, 420, 380, 10, jungle_keep, 0, M["forest"]); jg.hide_render = False
trees_c = bpy.data.collections.new("selva_mix"); ASSETS.children.link(trees_c)
for k in ["island_tree_01", "island_tree_02", "island_tree_03", "jacaranda_tree", "tree_small_02"]:
    if A.get(k): trees_c.children.link(A[k])
trees_c.children.link(PALMS[2])
scatter(jg, trees_c, 0.035, 0.9, 1.6, seed=3)
fern_c = bpy.data.collections.new("sotobosque"); ASSETS.children.link(fern_c)
for k in ["fern_02", "shrub_02", "shrub_04"]:
    if A.get(k): fern_c.children.link(A[k])
jg2 = grid("sotobosque_disp", -300, -160, 300, 280, 8, lambda x, z: jungle_keep(x, z) and (abs(z - PD / 2) < 140), 0, M["forest"])
scatter(jg2, fern_c, 0.25, 0.8, 1.6, seed=5)
# lotes vecinos (terreno desmontado) con estacas en las esquinas
for l in D["lotes"]:
    pts = [tuple(map(float, p.split(","))) for p in l["p"].split()]
    xs = [x - PXp for x, _ in pts]
    if min(abs(x) for x in xs) > 225: continue
    vs = [V(x - PXp, y - PZ0p, 0.04) for x, y in pts]
    mesh_obj("lote", vs, [tuple(range(len(vs)))[::-1]], M["lot"])
    for x, y in pts[:4]: box(0.06, 0.5, 0.06, M["white"], x - PXp, y - PZ0p, 0)
# banqueta de la avenida
plane(-230, ZMAX + 2, 230, ZMAX + 4.5, 0.12, M["pavers"], "banqueta")

# ================================================================== PARQUE
# pasto (celdas de 1 m sin la cancha) + pasto 3D disperso
grid("pasto", -W2, 0, W2, PARK_D, 1.0, lambda x, z: not inside(pitR, x, z), 0.12, M["grass"])
avoid, pathz = [], []
def ring_dist(x, z): return min(W2 - abs(x), z, PARK_D - z)
# sendero perimetral (anillo de 2.6 m) como malla de celdas de 0.5 m
grid("sendero", -W2, 0, W2, PARK_D, 0.5, lambda x, z: 2.0 < ring_dist(x, z) < 4.6, 0.17, M["pavers"])
for (x, z, w, d) in [(0, (PIT["z"] + PIT["d"] / 2 + PARK_D) / 2, 3, PARK_D - PIT["z"] - PIT["d"] / 2 - 4.6), (0, 19.5, 3, 4),
                     (-W2 / 2 - 5, PIT["z"], W2 - 30, 2.6), (W2 / 2 + 5, PIT["z"], W2 - 30, 2.6), (0, PARK_D - 8, PW - 12, 2.6)]:
    plane(x - w / 2, z - d / 2, x + w / 2, z + d / 2, 0.16, M["pavers"], "eje"); pathz.append((x - w / 2, z - d / 2, x + w / 2, z + d / 2))
# cerca de madera
for (x0, z0, x1, z1) in [(-W2, 0.5, W2, 0.5), (-W2 + 0.3, 0, -W2 + 0.3, PARK_D), (W2 - 0.3, 0, W2 - 0.3, PARK_D)]:
    L = math.hypot(x1 - x0, z1 - z0); n = int(L / 2.4)
    for k in range(n + 1):
        t = k / n; box(0.12, 1.8, 0.12, M["wood"], x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, 0)
    for hh in (0.85, 1.4):
        if z0 == z1: box(L, 0.12, 0.06, M["wood"], (x0 + x1) / 2, z0, hh)
        else: box(0.06, 0.12, L, M["wood"], x0, (z0 + z1) / 2, hh)
lamp_pts, string_pts = [], []

# ---- 1 yoga + árbol central (copa plana como el logo)
inst(A["tree_small_02"], 0, 11, 0, 2.3, rot=0.4)
for sx in (-1, 1):
    px, pz = sx * 10.5, 12.5
    box(9, 0.3, 7, M["deck"], px, pz, 0)
    for ox, oz in [(-4, -3), (4, -3), (-4, 3), (4, 3)]: cyl(0.13, 3.3, M["wood"], px + ox, pz + oz, 0.3, 10)
    r = cone(6.0, 2.4, M["thatch"], px, pz, 4.75, 4, rotz=math.pi / 4); r.scale = (1, 0.82, 1)
    for i in range(6): box(0.68, 0.02, 1.8, M["yogaA"] if i % 2 else M["yogaB"], px - 3 + (i % 3) * 3, pz - 1.6 + (i // 3) * 3.2, 0.3)
    avoid.append((px - 5, pz - 4, px + 5, pz + 4)); lamp_pts.append((px, pz, 3.4))
# ---- 2 calistenia
cx, cz = -W2 + 14, 12
box(14, 0.06, 9, M["rubber"], cx, cz, 0.12); avoid.append((cx - 7, cz - 4.5, cx + 7, cz + 4.5))
for i in range(4): h = 2.2 + (i % 2) * 0.6; cyl(0.05, h, M["metal"], cx - 5 + i * 3.2, cz - 2.5, 0, 12)
for i in range(3): bar(V(cx - 5 + i * 3.2, cz - 2.5, 2.2), V(cx - 1.8 + i * 3.2, cz - 2.5, 2.2), 0.035, M["metal"])
for dz in (1.5, 2.5):
    for dx in (-1.5, 1.5): cyl(0.045, 1.2, M["metal"], cx + dx, cz + dz, 0, 12)
    bar(V(cx - 1.5, cz + dz, 1.2), V(cx + 1.5, cz + dz, 1.2), 0.035, M["metal"])
for dz in (-0.6, 0.6):
    bar(V(cx + 1, cz + 2 + dz, 2.3), V(cx + 7, cz + 2 + dz, 2.3), 0.045, M["metal"])
    for dx in (1, 7): cyl(0.045, 2.3, M["metal"], cx + dx, cz + 2 + dz, 0, 12)
for i in range(10): bar(V(cx + 1.3 + i * 0.6, cz + 1.4, 2.3), V(cx + 1.3 + i * 0.6, cz + 2.6, 2.3), 0.03, M["metal"])
# ---- 3 mirador
mx, mz, s = W2 - 11, 10, 4.2
for ox, oz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]: cyl(0.18, 13, M["wood"], mx + ox * s / 2, mz + oz * s / 2, 0, 10)
for lv in (4, 8, 12):
    box(s + 0.6, 0.22, s + 0.6, M["deck"], mx, mz, lv)
    for hh in (0.55, 1.05):
        box(s + 0.6, 0.07, 0.07, M["wood"], mx, mz - (s + 0.6) / 2, lv + hh); box(s + 0.6, 0.07, 0.07, M["wood"], mx, mz + (s + 0.6) / 2, lv + hh)
        box(0.07, 0.07, s + 0.6, M["wood"], mx - (s + 0.6) / 2, mz, lv + hh); box(0.07, 0.07, s + 0.6, M["wood"], mx + (s + 0.6) / 2, mz, lv + hh)
for i in range(3):
    sx = (-1 if i % 2 else 1) * (s / 2 + 0.7)
    for k in range(12): box(1, 0.06, 0.32, M["deck"], mx + sx, mz + (1 if i % 2 else -1) * (2.2 - k * 0.4), i * 4 + 0.33 * k + 0.2)
cone(4.4, 2.6, M["thatch"], mx, mz, 13.6, 4, rotz=math.pi / 4)
avoid.append((mx - 4, mz - 4, mx + 4, mz + 4)); lamp_pts.append((mx, mz, 12.6))
# ---- 4 cancha hundida + rocódromo
x, z, w, d, dep = PIT["x"], PIT["z"], PIT["w"], PIT["d"], PIT["depth"]
plane(x - w / 2, z - d / 2, x + w / 2, z + d / 2, -dep, M["concrete"], "fondo_cancha")
bpy.ops.mesh.primitive_plane_add(size=1); cp = bpy.context.active_object; cp.scale = (28, 15, 1); cp.location = V(x, z + 1.5, -dep + 0.01)
for c in cp.users_collection: c.objects.unlink(cp)
WORLDC.objects.link(cp); cp.data.materials.append(court)
for i in range(3):
    h = dep - i
    box(w, h, 1.6, M["stone"], x, z + d / 2 - 0.8 - i * 1.6, -dep)
    box(1.6, h, d - 2, M["stone"], x - w / 2 + 0.8 + i * 1.6, z + 1, -dep); box(1.6, h, d - 2, M["stone"], x + w / 2 - 0.8 - i * 1.6, z + 1, -dep)
box(w, dep, 0.6, M["stone"], x, z - d / 2 + 0.3, -dep)
for i in range(240):
    o = cyl(0.12, 0.08, random.choice(M["holds"]), x - w / 2 + 6 + rr(0, w - 12), z - d / 2 + 0.64, -dep + 0.3 + rr(0, dep - 0.5), 6)
    o.rotation_euler = (math.pi / 2, rr(0, 3), 0)
for sx in (-1, 1):
    for i in range(6): box(2.4, 0.5, 0.55, M["concrete"], x + sx * (w / 2 - 4.4), z - d / 2 + 1.0 + i * 0.55, -dep + i * 0.5)
for sx in (-1, 1):
    bx, bz = x + sx * 12.4, z + 1.5
    cyl(0.11, 3.6, M["darkmetal"], bx + sx * 1.2, bz, -dep, 12); box(1.2, 0.1, 0.1, M["darkmetal"], bx + sx * 0.6, bz, -dep + 3.35)
    box(0.05, 1.05, 1.8, M["white"], bx, bz, -dep + 3.1)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.23, minor_radius=0.02); t = bpy.context.active_object; t.location = V(bx - sx * 0.3, bz, -dep + 3.05); t.data.materials.append(M["red"])
for k in range(int(w / 2) + 1): cyl(0.03, 1.05, M["darkmetal"], x - w / 2 + k * 2, z - d / 2, 0, 8)
bar(V(x - w / 2, z - d / 2, 1.05), V(x + w / 2, z - d / 2, 1.05), 0.03, M["darkmetal"])
avoid.append((x - w / 2 - 1, z - d / 2 - 1, x + w / 2 + 1, z + d / 2 + 1))
lamp_pts += [(x - 10, z + 2, -1), (x + 10, z + 2, -1)]
# ---- 5 juegos infantiles
gx, gz = -W2 + 15, PIT["z"]
disc(gx, gz, 9, 0.14, M["sand"]); avoid.append((gx - 9, gz - 9, gx + 9, gz + 9))
for tx, tz, th in [(gx - 3, gz - 2, 2.0), (gx + 1.5, gz - 3, 1.6)]:
    for ox, oz in [(-0.8, -0.8), (0.8, -0.8), (-0.8, 0.8), (0.8, 0.8)]: cyl(0.08, th + 1.8, M["wood"], tx + ox, tz + oz, 0, 10)
    box(1.9, 0.12, 1.9, M["deck"], tx, tz, th); cone(1.55, 1.3, M["thatch"], tx, tz, th + 2.4, 4, rotz=math.pi / 4)
    box(1.9, 0.6, 0.05, M["wood"], tx, tz - 0.95, th + 0.1)
sl = box(0.9, 0.08, 3.6, M["green"], gx - 3, gz + 0.9, 0.9); sl.rotation_euler = (0.55, 0, 0)
sx0, sz0 = gx + 3, gz + 3.5
for dx in (-2.2, 2.2):
    bar(V(sx0 + dx, sz0 - 0.9, 0), V(sx0 + dx, sz0, 2.75), 0.07, M["wood"]); bar(V(sx0 + dx, sz0 + 0.9, 0), V(sx0 + dx, sz0, 2.75), 0.07, M["wood"])
bar(V(sx0 - 2.3, sz0, 2.75), V(sx0 + 2.3, sz0, 2.75), 0.07, M["wood"])
for dx in (-1, 1):
    box(0.55, 0.05, 0.25, M["red"], sx0 + dx, sz0, 0.5)
    for ox in (-0.25, 0.25): bar(V(sx0 + dx + ox, sz0, 0.55), V(sx0 + dx + ox, sz0, 2.75), 0.008, M["metal"])
lamp_pts.append((gx, gz, 3.5))
# ---- 6 pet park
ax, az, aw, ad = W2 - 15, PIT["z"], 18, 17
plane(ax - aw / 2, az - ad / 2, ax + aw / 2, az + ad / 2, 0.14, M["sand"], "arenero"); avoid.append((ax - aw / 2, az - ad / 2, ax + aw / 2, az + ad / 2))
for hh in (0.5, 1.05):
    box(aw, 0.07, 0.06, M["wood"], ax, az - ad / 2, hh); box(aw, 0.07, 0.06, M["wood"], ax, az + ad / 2, hh)
    box(0.06, 0.07, ad, M["wood"], ax - aw / 2, az, hh); box(0.06, 0.07, ad, M["wood"], ax + aw / 2, az, hh)
for k in range(10):
    for zz in (az - ad / 2, az + ad / 2): box(0.1, 1.2, 0.1, M["wood"], ax - aw / 2 + k * aw / 9, zz, 0)
r1 = box(1.1, 0.06, 2.4, M["deck"], ax - 4, az - 3, 0.35); r1.rotation_euler = (0.55, 0, 0)
r2 = box(1.1, 0.06, 2.4, M["deck"], ax - 4, az - 1, 0.35); r2.rotation_euler = (-0.55, 0, 0)
for dx in (0, 2.5):
    for s_ in (-0.6, 0.6): cyl(0.035, 0.8, M["white"], ax + 1 + dx, az + 2 + s_, 0, 10)
    bar(V(ax + 1 + dx, az + 1.4, 0.6), V(ax + 1 + dx, az + 2.6, 0.6), 0.025, M["red"])
box(1.6, 1, 1.4, M["wood"], ax + 6, az + 5.5, 0); cone(1.2, 0.7, M["thatch"], ax + 6, az + 5.5, 1.35, 4, rotz=math.pi / 4)
# ---- 7 palapas, asadores y cocinetas
bx, bz = -W2 + 15, PARK_D - 22
for ox, oz, r in [(-5, -4, 4.4), (5, -2, 4.0), (0, 6, 4.8)]:
    px, pz = bx + ox, bz + oz
    cyl(r, 0.25, M["deck"], px, pz, 0.12, 32)
    for i in range(6): cyl(0.13, 3.1, M["wood"], px + math.cos(i / 6 * 6.283) * (r - 0.6), pz + math.sin(i / 6 * 6.283) * (r - 0.6), 0.37, 10)
    cone(r + 1.0, r * 0.75, M["thatch"], px, pz, 3.3 + r * 0.37, 18)
    inst(A["wooden_picnic_table"], px, pz, 0.37, 1.0, rot=rr(0, 3))
    avoid.append((px - r, pz - r, px + r, pz + r)); lamp_pts.append((px, pz, 3.2))
box(5, 0.95, 0.8, M["stone"], bx + 1, bz - 10, 0); box(5.1, 0.06, 0.9, M["concrete"], bx + 1, bz - 10, 0.95)
for dx in (-1.5, 1.5): box(0.9, 0.5, 0.6, M["darkmetal"], bx + 1 + dx, bz - 10, 1.0); cyl(0.06, 1.2, M["darkmetal"], bx + 1 + dx, bz - 10, 1.5, 10)
avoid.append((bx - 2, bz - 11, bx + 4, bz - 9))
# ---- 8 ceiba de lectura
cx, cz = 0, PARK_D - 20
inst(A["jacaranda_tree"], cx, cz, 0, 1.15, rot=1.2)
for i in range(4):
    a = i / 4 * 6.283 + 0.4; inst(A["painted_wooden_bench"], cx + math.cos(a) * 6.5, cz + math.sin(a) * 6.5, 0.12, 1.0, rot=-a - math.pi / 2)
for i in range(7): a = i / 7 * 6.283; cyl(0.3, 0.48, M["bark"], cx + math.cos(a) * 3.6, cz + math.sin(a) * 3.6, 0.12, 16)
for k in range(10):
    a = k / 10 * 6.283; x1, z1 = cx + math.cos(a) * 9.5, cz + math.sin(a) * 9.5
    cyl(0.05, 3.2, M["darkmetal"], x1, z1, 0, 8)
    for t in [i / 16 for i in range(17)]:
        string_pts.append((cx + (x1 - cx) * (0.15 + t * 0.85), cz + (z1 - cz) * (0.15 + t * 0.85), 7.5 - t * 4.3 - math.sin(t * math.pi) * 0.8))
avoid.append((cx - 4, cz - 4, cx + 4, cz + 4)); lamp_pts.append((cx, cz, 5))
# ---- 9 kiosco
kx, kz = W2 - 14, PARK_D - 20
box(8, 0.4, 8, M["deck"], kx, kz, 0.12)
for ox, oz in [(-3.5, -3.5), (3.5, -3.5), (-3.5, 3.5), (3.5, 3.5)]: cyl(0.16, 3.2, M["wood"], kx + ox, kz + oz, 0.5, 10)
for hh in (0.95, 1.4):
    box(7, 0.07, 0.07, M["wood"], kx, kz - 3.5, hh); box(0.07, 0.07, 7, M["wood"], kx - 3.5, kz, hh); box(0.07, 0.07, 7, M["wood"], kx + 3.5, kz, hh)
cone(6.2, 3.0, M["thatch"], kx, kz, 5.2, 4, rotz=math.pi / 4)
box(6, 0.55, 1.2, M["stone"], kx - 1, kz - 8, 0); box(1.2, 0.55, 5, M["stone"], kx - 6, kz - 6, 0)
avoid.append((kx - 4.5, kz - 4.5, kx + 4.5, kz + 4.5)); lamp_pts.append((kx, kz, 3.6))

# ---- vegetación del parque
for i in range(16):
    t = i / 15; palm(-W2 + 1.4, 6 + t * (PARK_D - 12)); palm(W2 - 1.4, 6 + t * (PARK_D - 12))
for i in range(9): palm(-W2 + 7 + i * (PW - 14) / 8, 1.4)
for (x_, z_) in [(-W2 + 8, PIT["z"] - 8), (-W2 + 22, PIT["z"] + 8), (W2 - 4, PIT["z"] - 10), (W2 - 26, PIT["z"] + 10), (-W2 + 4, PARK_D - 12), (-W2 + 26, PARK_D - 10), (W2 - 6, PARK_D - 10), (W2 - 22, PARK_D - 8), (-14, PARK_D - 10), (14, PARK_D - 10)]:
    palm(x_, z_)
for i in range(22):
    side = random.choice((-1, 1)); inst(A[random.choice(["island_tree_01", "island_tree_02", "island_tree_03"])], side * (W2 - 7 - rr(0, 2.5)), 22 + rr(0, PARK_D - 50), 0, rr(0.8, 1.1))
for (x_, z_) in [(-W2 + 24, 6), (W2 - 24, 6), (-20, 22), (20, 22)]: inst(A["island_tree_02"], x_, z_, 0, rr(0.9, 1.2))
# arriates
beds = [(-W2 + 14, 19, 8), (-12, PARK_D - 14, 6), (12, PARK_D - 14, 6), (-W2 + 23, PARK_D - 30, 5), (W2 - 9, PARK_D - 29, 5), (-W2 + 22, PIT["z"] - 7, 4), (W2 - 5, PIT["z"] + 12, 5)]
flower_c = bpy.data.collections.new("arriate"); ASSETS.children.link(flower_c)
for k in ["shrub_02", "shrub_04", "fern_02", "flower_gazania", "flower_heliophila"]:
    if A.get(k): flower_c.children.link(A[k])
for (x_, z_, s_) in beds:
    o = disc(x_, z_, s_ / 2, 0.13, M["forest"], 24); scatter(o, flower_c, 6, 0.8, 1.3, seed=int(x_ * 7 + z_))
o = plane(-W2 + 6, PARK_D - 3.8, W2 - 6, PARK_D - 2.4, 0.13, M["forest"], "seto"); scatter(o, flower_c, 5, 0.9, 1.3, seed=9)
# pasto 3D disperso (celdas de 0.5 m fuera de caminos y amenidades)
def grass_keep(x, z):
    if inside(pitR, x, z): return False
    for r in avoid + pathz:
        if inside(r, x, z): return False
    dd = ring_dist(x, z); return dd > 0.6 and not (2.0 < dd < 4.6)
g = grid("pasto_disp", -W2, 0, W2, PARK_D, 0.5, grass_keep, 0.12, M["grass"]); g.hide_render = False
grass_c = bpy.data.collections.new("pasto_mix"); ASSETS.children.link(grass_c)
for k in ["grass_medium_01", "grass_medium_02"]:
    if A.get(k): grass_c.children.link(A[k])
scatter(g, grass_c, 3, 0.35, 0.55, seed=1)
# ---- estacionamiento 80 x 18 m + banqueta
z0 = PARK_D; wP = min(80, PW)
plane(-wP / 2, z0, wP / 2, z0 + 18, 0.1, M["asphalt"], "estacionamiento")
plane(-wP / 2, z0 + 18, wP / 2, z0 + 20.5, 0.18, M["pavers"], "banqueta_parque")
box(wP, 0.2, 0.35, M["concrete"], 0, z0 + 0.18, 0.08); box(wP, 0.2, 0.25, M["concrete"], 0, z0 + 18, 0.08)
k = 0
while True:
    xx = -wP / 2 + 1 + k * 2.6
    if xx > wP / 2 - 1: break
    for zz in (z0 + 2.6, z0 + 15.4): box(0.1, 0.01, 5, M["line"], xx, zz, 0.1)
    k += 1
for i in range(9): palm(-wP / 2 + 4 + i * (wP - 8) / 8, z0 + 19.2, rr(1.0, 1.15))
# ---- luminarias del sendero (modelo de farol) siguiendo el anillo
ring = []
per = 2 * (PW - 10.4) + 2 * (PARK_D - 10.4)
for k in range(34):
    s_ = k / 34 * per; xm, zm = W2 - 5.2, PARK_D - 5.2
    if s_ < PW - 10.4: p = (-xm + s_, 5.2)
    elif s_ < PW - 10.4 + PARK_D - 10.4: p = (xm, 5.2 + s_ - (PW - 10.4))
    elif s_ < 2 * (PW - 10.4) + PARK_D - 10.4: p = (xm - (s_ - (PW - 10.4) - (PARK_D - 10.4)), zm)
    else: p = (-xm, zm - (s_ - 2 * (PW - 10.4) - (PARK_D - 10.4)))
    ring.append(p); inst(A["street_lamp_01"], p[0], p[1], 0.17, 1.0, rot=0)

# ================================================================== LUZ
world = bpy.data.worlds.new("cielo"); scene.world = world; world.use_nodes = True; wn = world.node_tree
env = wn.nodes.new("ShaderNodeTexEnvironment"); hdr = "belfast_sunset_puresky" if LIGHT == "tarde" else "kloofendal_48d_partly_cloudy_puresky"
env.image = bpy.data.images.load(str(PH / "hdri" / f"{hdr}.hdr"))
mp = wn.nodes.new("ShaderNodeMapping"); tc = wn.nodes.new("ShaderNodeTexCoord"); wn.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); wn.links.new(mp.outputs["Vector"], env.inputs["Vector"])
mp.inputs["Rotation"].default_value = (0, 0, math.radians(200 if LIGHT == "tarde" else 120))
bg = wn.nodes["Background"]; wn.links.new(env.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.1 if LIGHT == "tarde" else 1.0
sunL = bpy.data.lights.new("sol", "SUN"); sunL.angle = math.radians(1.5)
if LIGHT == "tarde":
    sunL.energy = 2.8; sunL.color = (1.0, 0.66, 0.4); sun_rot = (math.radians(78), 0, math.radians(-115))
else:
    sunL.energy = 4.0; sunL.color = (1.0, 0.95, 0.88); sun_rot = (math.radians(40), 0, math.radians(-150))
so = bpy.data.objects.new("sol", sunL); so.rotation_euler = sun_rot; put(so)
if LIGHT == "tarde":
    M["bulb"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 25.0
    for (x_, z_, y_) in lamp_pts:
        L_ = bpy.data.lights.new("lamp", "POINT"); L_.energy = 260; L_.color = (1.0, 0.72, 0.42); L_.shadow_soft_size = 0.3
        put(bpy.data.objects.new("lamp", L_)).location = V(x_, z_, y_)
    for (x_, z_) in ring:
        L_ = bpy.data.lights.new("farol", "POINT"); L_.energy = 110; L_.color = (1.0, 0.75, 0.45); L_.shadow_soft_size = 0.15
        put(bpy.data.objects.new("farol", L_)).location = V(x_, z_, 3.3)
    for (x_, z_, y_) in string_pts:
        o = cyl(0.05, 0.08, M["bulb"], x_, z_, y_, 8)
    for i, (x_, z_, y_) in enumerate(string_pts[::6]):
        L_ = bpy.data.lights.new("guirnalda", "POINT"); L_.energy = 12; L_.color = (1.0, 0.78, 0.5); L_.shadow_soft_size = 0.05
        put(bpy.data.objects.new("guirnalda", L_)).location = V(x_, z_, y_ - 0.1)
    scene.view_settings.exposure = -0.35
else:
    for (x_, z_, y_) in string_pts: cyl(0.05, 0.08, M["white"], x_, z_, y_, 8)
    scene.view_settings.exposure = -0.35

# ================================================================== CÁMARAS
EYE = 1.65
PANOS = [
    ("llegada", (3.2, PARK_D + 19.8, EYE), "Llegada por la avenida"),
    ("ceiba", (6.5, PARK_D - 11, EYE), "Ceiba de lectura"),
    ("cancha", (0, PIT["z"] + PIT["d"] / 2 + 1.2, EYE), "Cancha hundida"),
    ("dentro_cancha", (4, PIT["z"] + 3, -PIT["depth"] + EYE), "Dentro de la cancha"),
    ("yoga", (0, 19.5, EYE), "Yoga y árbol central"),
    ("mirador", (W2 - 11, 10, 8.22 + EYE), "Desde el mirador"),
    ("juegos", (-24, PIT["z"], EYE), "Juegos y pet park"),
    ("palapas", (-W2 + 24, PARK_D - 13, EYE), "Palapas y asadores"),
    ("dron", (0, PD / 2 + 4, 55), "Vista de dron"),
]
STILLS = [
    ("still_llegada", (-14, PARK_D + 26, 6.5), (0, PARK_D - 22, 3), 24),
    ("still_cancha", (-9, PIT["z"] + 21, 6.0), (0, PIT["z"], -2.5), 24),
    ("still_ceiba", (12, PARK_D - 4, 2.2), (0, PARK_D - 20, 4.0), 22),
    ("still_yoga", (-15, 27, 2.6), (0, 11, 4), 24),
    ("still_aerea", (62, PD + 58, 62), (0, PD / 2 - 5, 0), 30),
    ("still_mirador", (W2 - 27, 31, 4.5), (W2 - 11, 10, 7.5), 28),
]
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data); put(cam); scene.camera = cam
def look_at(obj, target):
    d = Vector(target) - obj.location; obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
scene.render.resolution_percentage = 100
(OUTDIR / "pano").mkdir(parents=True, exist_ok=True); (OUTDIR / "fotos").mkdir(parents=True, exist_ok=True)
# metadatos para el visor
meta = {"light": LIGHT, "park": {"w": PW, "d": PD, "park_d": PARK_D}, "panos": [{"id": n, "name": t, "x": p[0], "z": p[1], "y": p[2]} for n, p, t in PANOS]}
if MODE == "pano":  # solo los panoramas reescriben los metadatos del visor
    (OUTDIR / "pano" / "panos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))

if SAVE:
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / SAVE)); print("guardado", SAVE)
    if "--mode" not in argv:  # --save sin --mode: solo construir y guardar, sin renderizar
        print("listo"); sys.exit(0)

sel = None if STOPS == "all" else [int(s) for s in STOPS.split(",")]
if MODE == "pano":
    cam_data.type = "PANO"
    try: cam_data.panorama_type = "EQUIRECTANGULAR"
    except Exception: cam_data.cycles.panorama_type = "EQUIRECTANGULAR"
    scene.render.resolution_x, scene.render.resolution_y = RES, RES // 2
    for i, (name, p, _) in enumerate(PANOS):
        if sel and i not in sel: continue
        cam.location = V(p[0], p[1], p[2]); cam.rotation_euler = (math.radians(90), 0, 0)  # centro de la imagen mira hacia +Y (fondo del parque)
        scene.render.filepath = str(OUTDIR / "pano" / f"{LIGHT}_{i}_{name}.jpg")
        print("render pano", i, name, flush=True); bpy.ops.render.render(write_still=True)
elif MODE == "still":
    cam_data.type = "PERSP"; cam_data.sensor_width = 36
    vertical = arg("--vertical") == "1"
    scene.render.resolution_x, scene.render.resolution_y = (RES * 9 // 16, RES) if vertical else (RES, RES * 9 // 16)
    for i, (name, p, t, lens) in enumerate(STILLS):
        if sel and i not in sel: continue
        cam_data.lens = lens * (0.75 if vertical else 1); cam.location = V(*p); look_at(cam, V(*t))
        scene.render.filepath = str(OUTDIR / "fotos" / f"{LIGHT}_{name}{'_v' if vertical else ''}.jpg")
        print("render foto", i, name, flush=True); bpy.ops.render.render(write_still=True)
print("listo")
