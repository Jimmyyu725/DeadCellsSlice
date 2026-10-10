"""Shared pieces for the 60-weapon expansion kits (armory_melee.py,
armory_ranged.py, armory_other.py): one material library with coloured glow
materials (the emission map is baked in colour; Unity multiplies it by a
neutral HDR white), common part builders, a headless bake entry point and a
live-preview entry point that never resets the user's scene.

Conventions (same as build_arsenal.py): grip centre at the origin, primary
axis Blender +Z, edge / reach toward +X, flats face +-Y.  Ranged weapons and
shields follow the Bow / Shield mounts: ranged fire toward -Y with the stock
along Y; shields face -Y (Unity +Z out of the arm)... see each builder.
Blender (x, y, z) == Unity (x, z, y).
"""

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_arsenal as ba  # noqa: E402
import dc_common as dc  # noqa: E402
import env_helpers as eh  # noqa: E402
from build_arsenal import (TAU, Asset, MatEdit, aim, blob, catmull, cbox, cone, lathe, lerp, loft,  # noqa: E402,F401
                           make_mat, prism_xz, ridged, rot, sweep, thick_sheet, torus, tube, xform)

OUT_ROOT = dc.ART_ROOT / "Weapons" / "Armory2"

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

GLOWS = {
    "glow_fire": "#FF7A22", "glow_ice": "#7FE8FF", "glow_bolt": "#8FB4FF", "glow_poison": "#8CFF4A",
    "glow_moon": "#E6EEFF", "glow_violet": "#B57CFF", "glow_gold": "#FFCF6A", "glow_red": "#FF3048",
}


def colour_emit(mat, hex_, fac=1.0):
    """Coloured emission: DC_EMIT = colour * mask (baked in colour)."""
    E = MatEdit(mat)
    E.emit(fac)
    src = E._src("DC_EMIT")
    _, out = dc.mix_rgb(E.nt, src, dc.hex_rgba(hex_), 1.0, blend="MULTIPLY", loc=E._loc())
    E._set("DC_EMIT", out)
    return mat


def glow_mat(name, hex_):
    c = Vector(dc.hex_rgba(hex_)[:3])
    light = "#{:02X}{:02X}{:02X}".format(*[int(min(1.0, v * 0.35 + 0.65) * 255) for v in c])
    m = make_mat(name, hex_, dark=hex_, light=light, rough=0.25, noise_scale=10.0, noise_amt=0.5, bevel_radius=0.0015)
    return colour_emit(m, hex_)


def gem_mat(name, hex_, dark, light, glow_hex=None, glow=0.0):
    m = make_mat(name, hex_, dark=dark, light=light, rough=0.18, rough_var=0.08, noise_scale=16, noise_amt=0.8,
                 bump_scale=30, bump_strength=0.08, bevel_radius=0.0015)
    eh.enhance(m, edge_hex=light, edge_amt=1.0, edge_radius=0.002)
    if glow_hex and glow > 0:
        E = MatEdit(m)
        facet = E.rng(E.noise(18.0, 3.0, 0.6), 0.45, 0.75)
        E.emit(E.m("MULTIPLY", facet, glow))
        src = E._src("DC_EMIT")
        _, out = dc.mix_rgb(E.nt, src, dc.hex_rgba(glow_hex), 1.0, blend="MULTIPLY", loc=E._loc())
        E._set("DC_EMIT", out)
    return m


def cracked_mat(name, base, dark, light, glow_hex, scale=18.0, width=0.05):
    """Dark rock / char with glowing cracks (voronoi edges)."""
    m = make_mat(name, base, dark=dark, light=light, rough=0.8, noise_scale=8, noise_amt=0.7, bump_scale=40,
                 bump_strength=0.25, bevel_radius=0.003)
    E = MatEdit(m)
    edge = E.voronoi(scale, feature="DISTANCE_TO_EDGE", out="Distance")
    crack = E.rng(edge, width, 0.0)
    E.albedo(glow_hex, crack)
    E.bump(crack, -0.6)
    E.emit(crack)
    src = E._src("DC_EMIT")
    _, out = dc.mix_rgb(E.nt, src, dc.hex_rgba(glow_hex), 1.0, blend="MULTIPLY", loc=E._loc())
    E._set("DC_EMIT", out)
    eh.enhance(m, edge_hex=light, edge_amt=0.6, edge_radius=0.003)
    return m


def kit_materials():
    M = {}
    M["iron"] = ba.iron_mat("K_Iron", rust=0.4, edge_r=0.004)
    M["dark_iron"] = ba.iron_mat("K_DarkIron", rust=0.15, edge_r=0.004, base="#363B42")
    M["rust"] = ba.iron_mat("K_Rust", rust=0.95, edge_r=0.004, base="#4A4E52")
    M["steel"] = ba.iron_mat("K_Steel", rust=0.0, edge_r=0.003, base="#9AA4AC", metal=0.7, edge=("#F4F8FA", 1.0))
    M["blued"] = ba.iron_mat("K_Blued", rust=0.0, edge_r=0.003, base="#2E3C5A", metal=0.7, edge=("#A8C4F0", 1.0))
    M["brass"] = ba.brass_mat("K_Brass", edge_r=0.003, patina=0.15)
    M["bronze"] = ba.brass_mat("K_Bronze", edge_r=0.004, patina=0.45)
    M["copper"] = ba.iron_mat("K_Copper", rust=0.0, edge_r=0.003, base="#A0532E", metal=0.75, edge=("#F0B080", 1.0))
    M["ash"] = ba.wood_mat("K_Ash", "#A48A68", "#5E4A34", "#CDB896", grain=0.06, edge_r=0.004)
    M["dark_wood"] = ba.wood_mat("K_DarkWood", "#5A2A1E", "#22100A", "#8A4A32", grain=0.05, edge_r=0.004, rough=0.55)
    M["drift_wood"] = ba.wood_mat("K_DriftWood", "#6A5440", "#2A1C10", "#9A7E5E", grain=0.05, edge_r=0.005,
                                  stripes=("z", 14.0, 0.05, "#20140A"))
    M["lacquer"] = ba.wood_mat("K_Lacquer", "#7A1420", "#300408", "#C03A40", grain=0.03, edge_r=0.003, rough=0.3)
    M["grip"] = ba.leather_mat("K_Grip", "#3B2618", "#160C06", "#6E4C30", stripes=("z", 85.0, 0.2, "#140A05"))
    M["leather"] = ba.leather_mat("K_Leather", "#5E3B22", "#26150A", "#8E6440")
    M["rope"] = ba.cloth_mat("K_Rope", "#8A7350", "#3E3020", "#BBA27A", stripes=("z", 140.0, 0.25, "#3A2C1C"),
                             edge_r=0.002, weave=260)
    M["string"] = ba.cloth_mat("K_String", "#D8CDB0", "#8A7E62", "#F4ECD6", edge_r=0.001, weave=300)
    M["red_cloth"] = ba.cloth_mat("K_RedCloth", "#9A1826", "#4A0610", "#D23A44", edge_r=0.002)
    M["purple_cloth"] = ba.cloth_mat("K_PurpleCloth", "#4A2A7A", "#1E0E36", "#8A5ACA", edge_r=0.002)
    M["kelp"] = ba.cloth_mat("K_Kelp", "#3E5A3A", "#18261A", "#7A9A62", stripes=("z", 40.0, 0.1, "#1E2E1C"), edge_r=0.002)
    M["silk"] = ba.cloth_mat("K_Silk", "#DDE6F2", "#9AA6B8", "#FFFFFF", edge_r=0.0015, weave=380)
    M["bone"] = ba.bone_mat("K_Bone", edge_r=0.003)
    M["wax"] = make_mat("K_Wax", "#E8DCC0", dark="#B8A880", light="#FFF6E0", rough=0.45, noise_scale=12, noise_amt=0.5,
                        bevel_radius=0.002)
    M["moonstone"] = gem_mat("K_Moonstone", "#C8D4EA", "#7A88A8", "#F4F8FF", "#E6EEFF", 0.55)
    M["chitin"] = gem_mat("K_Chitin", "#3A2240", "#140818", "#7A5A8A")
    M["eel"] = gem_mat("K_EelSkin", "#2A5A62", "#0C2228", "#6AA6A8", "#8FB4FF", 0.25)
    M["coral"] = gem_mat("K_Coral", "#D8705A", "#7A2A22", "#FFB098")
    M["obsidian"] = cracked_mat("K_Obsidian", "#1E1820", "#08060A", "#4A4250", "#FF7A22")
    M["ice"] = gem_mat("K_Ice", "#A8E4FF", "#3A7AB0", "#F0FCFF", "#7FE8FF", 0.6)
    M["lavender_glass"] = gem_mat("K_LavenderGlass", "#A07AD8", "#4A2A7A", "#E8D8FF", "#B57CFF", 0.7)
    M["green_glass"] = gem_mat("K_GreenGlass", "#5AB86A", "#1E5A2A", "#C8FFC8", "#8CFF4A", 0.7)
    M["ink"] = gem_mat("K_Ink", "#1A1630", "#05040C", "#4A4278", "#B57CFF", 0.3)
    M["shark"] = ba.iron_mat("K_SharkSkin", rust=0.0, edge_r=0.003, base="#6E7A86", metal=0.1, edge=("#C8D2DA", 0.8))
    M["paper"] = make_mat("K_Paper", "#DCC79A", dark="#A0804E", light="#F2E4BE", rough=0.85, noise_scale=6,
                          noise_amt=0.8, bevel_radius=0.002)
    for k, v in GLOWS.items():
        M[k] = glow_mat("K_" + k.title().replace("_", ""), v)
    return M


KIT_HP = {"string": (0.0, 1), "rope": (0.0, 1), "red_cloth": (0.0, 1), "purple_cloth": (0.0, 1), "kelp": (0.0, 1),
          "silk": (0.0, 1), "paper": (0.0, 1), "steel": (0.0015, 1), "blued": (0.0015, 1)}
for _g in GLOWS:
    KIT_HP[_g] = (0.0, 1)
KIT_WEIGHT = {"string": 0.5, "rope": 0.7, "steel": 1.2, "blued": 1.2, "moonstone": 1.2, "obsidian": 1.2}
for _g in GLOWS:
    KIT_WEIGHT[_g] = 0.6

# ---------------------------------------------------------------------------
# Part helpers (all add to a Piece P)
# ---------------------------------------------------------------------------


def shaft(P, z0, z1, r0, r1=None, mat="ash", segs=8, bend=0.0, axis="z"):
    r1 = r0 if r1 is None else r1
    n = max(4, int(abs(z1 - z0) / 0.06))
    pts, rad = [], []
    for i in range(n + 1):
        t = i / n
        z = lerp(z0, z1, t)
        off = bend * math.sin(math.pi * t)
        p = Vector((off, 0, z)) if axis == "z" else Vector((0, z, off))
        pts.append(p)
        rad.append(lerp(r0, r1, t))
    P.add(mat, tube(pts, rad, segs=segs))


def grip(P, z0, z1, r, mat="grip", n=None):
    P.add(mat, lathe(ridged(z0, z1, r * 0.92, r, n or max(5, int((z1 - z0) / 0.018)), end_r=r * 0.95), segs=8))


def cap(P, z, r, h=0.03, mat="iron", down=True):
    s = -1 if down else 1
    P.add(mat, lathe([(0.0, z + s * h), (r * 0.6, z + s * h * 0.95), (r, z + s * h * 0.5), (r * 0.95, z), (r * 0.8, z - s * 0.004)],
                     segs=10))


def collar(P, z, r, h=0.02, mat="brass"):
    P.add(mat, lathe([(r * 0.9, z - h / 2), (r, z - h / 2 + 0.004), (r, z + h / 2 - 0.004), (r * 0.9, z + h / 2)], segs=12,
                     cap0=False, cap1=False))


def blade(P, mat, z0, z1, left, right, thick, rows=18, tip=None, ridge=0.5, xoff=None):
    """Lens-section blade lofted along Z.  left/right/thick: callables of t in [0,1]
    giving x of each edge and half-thickness; ridge = where the spine sits (0 left, 1 right)."""
    rings = []
    for i in range(rows + 1):
        t = i / rows
        z = lerp(z0, z1, t)
        xl, xr, th = left(t), right(t), thick(t)
        xm = lerp(xl, xr, ridge)
        o = xoff(t) if xoff else 0.0
        ring = [(xr, 0.0), (lerp(xm, xr, 0.55), th * 0.7), (xm, th), (lerp(xm, xl, 0.55), th * 0.7), (xl, 0.0),
                (lerp(xm, xl, 0.55), -th * 0.7), (xm, -th), (lerp(xm, xr, 0.55), -th * 0.7)]
        rings.append([Vector((x + o, y, z)) for x, y in ring])
    P.add(mat, loft(rings, tip1=Vector(tip) if tip else None))


def edge_blade(P, mat, path, width, thick, side_hint, tip_ext=0.03):
    path = [Vector(p) for p in path]
    tip = path[-1] + (path[-1] - path[-2]).normalized() * tip_ext
    n = len(path)

    def prof(k, f):
        t = k / max(1, n - 1)
        w, th = width(t), thick(t)
        return [(0.0, th), (w * 0.5, th * 0.62), (w, 0.0), (w * 0.5, -th * 0.62), (0.0, -th), (-0.004, 0.0)]

    P.add(mat, sweep(path, prof, side_hint=side_hint, tip1=tip))


def gem(P, center, r, mat, segs=6, h=1.3, axis=(0, 1, 0)):
    g = lathe([(0.0, -r * h), (r, 0.0), (0.0, r * h)], segs=segs)
    P.add(mat, aim(g, axis, center))


def spikes(P, center, r, dirs, length, base_r, mat="iron", segs=6):
    c = Vector(center)
    for d in dirs:
        d = Vector(d).normalized()
        P.add(mat, cone(tuple(c + d * r * 0.9), tuple(d), length, base_r, segs=segs))


def ring_of(n, axis="y", phase=0.0):
    out = []
    for i in range(n):
        a = phase + TAU * i / n
        if axis == "y":
            out.append((math.cos(a), 0.0, math.sin(a)))
        elif axis == "z":
            out.append((math.cos(a), math.sin(a), 0.0))
        else:
            out.append((0.0, math.cos(a), math.sin(a)))
    return out


def disc(P, center, r, th, mat, axis=(0, 1, 0), segs=24, bevel=0.3):
    prof = [(0.0, -th), (r * (1 - bevel * 0.2), -th), (r, -th * 0.4), (r, th * 0.4), (r * (1 - bevel * 0.2), th), (0.0, th)]
    P.add(mat, aim(lathe(prof, segs=segs), axis, center))


def ribbon(P, mat, top, length, width, rng, sway=0.025, rows=7, side=(1, 0, 0)):
    side = Vector(side)
    grid = []
    for r in range(rows):
        v = r / (rows - 1)
        wob = sway * math.sin(v * 3.1 + rng.uniform(0, 2)) * v
        row = []
        for c in range(3):
            u = c / 2 - 0.5
            w = width * (1.0 - 0.45 * v)
            p = Vector(top) + side * (u * w + wob) + Vector((0, 0.006 * math.sin(u * 3 + v * 4), -length * v))
            row.append(tuple(p))
        grid.append(row)
    P.add(mat, thick_sheet(grid, 0.003))


def chain(P, a, b, n, R=0.014, r=0.004, mat="iron", sag=0.0):
    a, b = Vector(a), Vector(b)
    pts = []
    for i in range(n):
        t = i / max(1, n - 1)
        p = a.lerp(b, t) + Vector((0, 0, -sag * math.sin(math.pi * t)))
        pts.append(p)
    for i, p in enumerate(pts):
        tdir = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        normal = Vector((0, 1, 0)) if i % 2 == 0 else tdir.cross(Vector((0, 1, 0))).normalized()
        P.add(mat, torus(tuple(p), R, r, normal=tuple(normal), seg=10, rseg=4))


def scale_piece(P, s, origin=(0, 0, 0)):
    """Uniformly scale everything already added to a piece."""
    for bm in P.parts.values():
        eh.scale(bm, s, origin)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def run_headless(assets_fn, atlas, size=2048):
    out = OUT_ROOT / atlas
    ba.run_kit(assets_fn=assets_fn, materials_fn=kit_materials, atlas=atlas, tex_dir=out / "Textures", fbx_dir=out,
               manifest_path=out / f"{atlas.lower()}_manifest.json", prev_dir=dc.OUT_ROOT / atlas.lower(),
               generator=f"Tools/Blender/{Path(sys.argv[0]).name}", size=size, hp_cfg=KIT_HP, flat=(),
               mat_weight=KIT_WEIGHT, budget=lambda a: 6000, emission_colors=dict(GLOWS),
               views=("three_quarter", "front"), cols=5)


def live_preview(assets_fn, collection, row=0, cols=10, spacing=0.75, row_height=2.2, only=None, rot_z=0.0, x0=0.0):
    """Build the assets into the open scene (own collection, procedural materials)
    without touching anything else.  Re-running replaces that collection only."""
    old = bpy.data.collections.get(collection)
    if old is not None:
        for o in list(old.objects):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data is not None and data.users == 0 and isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(collection)
    bpy.context.scene.collection.children.link(col)
    M = kit_materials_cached()
    assets = assets_fn()
    if only:
        assets = [a for a in assets if a.name in only]
    ba.realize(assets, M)
    for i, a in enumerate(assets):
        root = bpy.data.objects.new("W_" + a.name, None)
        root.empty_display_size = 0.1
        col.objects.link(root)
        for o in a.objs:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
            o.parent = root
        r, c = divmod(i, cols)
        root.location = (x0 + c * spacing, 0.0, -(row + r) * row_height)
        root.rotation_euler = (0.0, 0.0, rot_z)
    return [a.name for a in assets]


def kit_materials_cached():
    """Material library reused across live runs: built once per Blender file,
    found again by name afterwards (the key -> name map lives on the scene)."""
    import json
    scene = bpy.context.scene
    stored = json.loads(scene.get("dc_kit_mats", "{}"))
    if stored and all(n in bpy.data.materials for n in stored.values()):
        return {k: bpy.data.materials[n] for k, n in stored.items()}
    M = kit_materials()
    scene["dc_kit_mats"] = json.dumps({k: m.name for k, m in M.items()})
    return M
