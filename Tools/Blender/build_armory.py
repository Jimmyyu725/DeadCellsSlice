"""Armory kit: BellMaul, PendulumRapier, TideScythe, ChainFlail, GraveShovel and
Crossbow, sharing one 2048 atlas "Armory".  Each has its own silhouette so the
weapons read apart at gameplay distance.

Same conventions as build_arsenal.py: grip centre at the origin, primary axis
Blender +Z (blade / shaft direction), cutting edge / reach toward +X, flats
face +-Y.  The Crossbow follows the Bow convention instead: limbs along +-Z,
stock along Y, the bolt flies toward -Y.  Blender (x, y, z) == Unity (x, z, y).
Uses the shared kit pipeline from build_arsenal.py.

Run (headless only, never in the live Blender):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P Tools/Blender/build_armory.py
Options after "--": --fast, --build-only, --only=A,B, --res=N, --verify (see build_arsenal.py)
"""

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from mathutils import Vector  # noqa: E402

import build_arsenal as ba  # noqa: E402
import dc_common as dc  # noqa: E402
import env_helpers as eh  # noqa: E402
from build_arsenal import (TAU, Asset, MatEdit, aim, blob, catmull, cbox, cone, lathe, lerp, loft,  # noqa: E402
                           make_mat, prism_xz, ridged, rot, sweep, thick_sheet, torus, tube, xform)

OUT_DIR = dc.ART_ROOT / "Weapons" / "Armory"
TEX_DIR = OUT_DIR / "Textures"
MANIFEST = OUT_DIR / "armory_manifest.json"
PREV = dc.OUT_ROOT / "armory"


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def steel_mat(name, base="#9AA4AC", rust=0.0, edge_r=0.002):
    m = make_mat(name, base, dark="#56606A", light="#DCE4EA", metal=0.7, rough=0.3, rough_var=0.1, noise_scale=8.0,
                 noise_amt=0.4, bump_scale=40, bump_strength=0.08, bevel_radius=edge_r)
    if rust:
        ba.rust_layer(m, rust, scale=7.0)
    eh.enhance(m, edge_hex="#F4F8FA", edge_amt=1.0, edge_radius=edge_r, top_hex="#C8D0D6", top_amt=0.15,
               cavity_amt=0.5, cavity_dist=edge_r * 8)
    return m


def armory_materials():
    M = {}
    M["iron"] = ba.iron_mat("R_Iron", rust=0.4, edge_r=0.004)
    M["dark_iron"] = ba.iron_mat("R_DarkIron", rust=0.2, edge_r=0.004, base="#3A3F46")
    M["brass"] = ba.brass_mat("R_Brass", edge_r=0.003, patina=0.15)
    M["bronze"] = ba.brass_mat("R_Bronze", edge_r=0.004, patina=0.4)
    M["steel"] = steel_mat("R_Steel")
    M["scythe_blade"] = steel_mat("R_ScytheBlade", base="#7E8890", rust=0.55, edge_r=0.003)
    M["spade"] = ba.iron_mat("R_Spade", rust=0.85, edge_r=0.004, base="#4A4E52")
    M["ash"] = ba.wood_mat("R_Ash", "#A48A68", "#5E4A34", "#CDB896", grain=0.06, edge_r=0.004)
    M["dark_wood"] = ba.wood_mat("R_DarkWood", "#5A2A1E", "#22100A", "#8A4A32", grain=0.05, edge_r=0.004,
                                 rough=0.55)
    M["drift_wood"] = ba.wood_mat("R_DriftWood", "#6A5440", "#2A1C10", "#9A7E5E", grain=0.05, edge_r=0.005,
                                  stripes=("z", 14.0, 0.05, "#20140A"))
    M["grip"] = ba.leather_mat("R_Grip", "#3B2618", "#160C06", "#6E4C30", stripes=("z", 85.0, 0.2, "#140A05"))
    M["rope"] = ba.cloth_mat("R_Rope", "#8A7350", "#3E3020", "#BBA27A", stripes=("z", 140.0, 0.25, "#3A2C1C"),
                             edge_r=0.002, weave=260)
    M["string"] = ba.cloth_mat("R_String", "#D8CDB0", "#8A7E62", "#F4ECD6", edge_r=0.001, weave=300)
    M["red_cloth"] = ba.cloth_mat("R_RedCloth", "#9A1826", "#4A0610", "#D23A44", edge_r=0.002)
    M["kelp"] = ba.cloth_mat("R_Kelp", "#3E5A3A", "#18261A", "#7A9A62", stripes=("z", 40.0, 0.1, "#1E2E1C"),
                             edge_r=0.002)
    M["bone"] = ba.bone_mat("R_Bone", edge_r=0.003)
    # Glow: a flat warm material whose whole surface is the emission mask.
    m = make_mat("R_Glow", "#FFD27A", dark="#FF9A2A", light="#FFF6D8", rough=0.2, noise_scale=12.0, noise_amt=0.6,
                 bevel_radius=0.0015)
    MatEdit(m).emit(1.0)
    M["glow"] = m
    return M


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------

def blade_sweep(path, width, thick, side_hint, tip=None, overhang=0.004):
    """Wedge blade along `path`: spine at a=0, cutting edge at a=width(t);
    the cross-section thins from the spine to the edge."""
    n = len(path)

    def prof(k, f):
        t = k / max(1, n - 1)
        w, th = width(t), thick(t)
        return [(0.0, th), (w * 0.5, th * 0.62), (w, 0.0), (w * 0.5, -th * 0.62), (0.0, -th), (-overhang, 0.0)]

    return sweep(path, prof, side_hint=side_hint, tip1=tip)


def bezier(p0, p1, p2, n):
    out = []
    for i in range(n):
        t = i / (n - 1)
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        out.append(Vector(p0) * a + Vector(p1) * b + Vector(p2) * c)
    return out


def ribbon(top, length, width, rng, sway=0.025, rows=7, cols=3, side=(1, 0, 0)):
    """Hanging cloth strip from `top`, falling along -Z."""
    side = Vector(side)
    grid = []
    for r in range(rows):
        v = r / (rows - 1)
        wob = sway * math.sin(v * 3.1 + rng.uniform(0, 2)) * v
        row = []
        for c in range(cols):
            u = c / (cols - 1) - 0.5
            w = width * (1.0 - 0.45 * v)
            p = Vector(top) + side * (u * w + wob) + Vector((0, 0.006 * math.sin(u * 3 + v * 4), -length * v))
            row.append(tuple(p))
        grid.append(row)
    return thick_sheet(grid, 0.003)


def chain_links(points, R=0.017, r=0.0048, plane_normal=(0, 1, 0)):
    """Interlocked round links centred on `points`, alternating orientation."""
    out = []
    pn = Vector(plane_normal)
    for i, p in enumerate(points):
        t = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
        normal = pn if i % 2 == 0 else t.cross(pn).normalized()
        out.append(torus(tuple(p), R, r, normal=tuple(normal), seg=10, rseg=4))
    return out


def resample(points, step):
    """Points every `step` metres along a polyline."""
    pts = [Vector(p) for p in points]
    out = [pts[0].copy()]
    carry = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        d = step - carry
        while d <= seg:
            out.append(a + (b - a) * (d / seg))
            d += step
        carry = seg - (d - step)
    return out


# ---------------------------------------------------------------------------
# Weapons
# ---------------------------------------------------------------------------

def build_maul():
    A = Asset("BellMaul", weight=1.3, tint="#FFB347",
              usage="Bell-Breaker maul: ash haft (grip centre at origin), a cracked bronze bell as the head with the "
                    "mouth toward +X and an iron spike toward -X at y=1.06. Emission = the ember clapper in the mouth.")
    P = A.piece("BellMaul")
    zs = [lerp(-0.34, 1.0, i / 20) for i in range(21)]
    P.add("ash", tube([(0, 0, z) for z in zs], [0.0215 + 0.0035 * (1.0 - (z + 0.34) / 1.34) for z in zs], segs=8))
    P.add("grip", lathe(ridged(-0.14, 0.14, 0.0238, 0.0266, 13, end_r=0.0236), segs=8))
    P.add("iron", lathe([(0.0, -0.405), (0.014, -0.4), (0.029, -0.38), (0.031, -0.355), (0.025, -0.338),
                         (0.0235, -0.326)], segs=10))
    for sgn in (-1, 1):
        P.add("iron", cbox((0, sgn * 0.0235, 0.84), (0.024, 0.006, 0.17), bev=0.002))
        for z in (0.78, 0.88):
            P.add("iron", blob((0, sgn * 0.027, z), 0.0055, scale=(1, 0.6, 1), segs=6, rings=4))
    for z in (0.725, 0.745):
        P.add("rope", torus((0, 0, z), 0.0235, 0.0048, seg=10, rseg=4))
    # Bronze bell lying on its side: crown toward -X, hollow mouth toward +X.
    hc = (0, 0, 1.06)

    def head(bm):
        return eh.scale(bm, 1.3, hc)

    bell = lathe([(0.0, 0.0), (0.036, 0.002), (0.06, 0.012), (0.072, 0.03), (0.078, 0.06), (0.084, 0.1),
                  (0.095, 0.14), (0.112, 0.175), (0.13, 0.2), (0.139, 0.212), (0.135, 0.222), (0.121, 0.224),
                  (0.106, 0.2), (0.09, 0.16), (0.0, 0.14)], segs=22)
    P.add("bronze", head(aim(bell, (1, 0, 0), (-0.08, 0, 1.06))))
    P.add("iron", head(torus((-0.005, 0, 1.06), 0.082, 0.008, normal=(1, 0, 0), seg=22, rseg=5)))
    P.add("iron", head(torus((0.118, 0, 1.06), 0.127, 0.006, normal=(1, 0, 0), seg=22, rseg=4)))
    # Back spike with a collar.
    P.add("iron", head(lathe([(0.03, 0.0), (0.034, 0.012), (0.028, 0.026)], segs=10, axis=(-1, 0, 0),
                             center=(-0.078, 0, 1.06))))
    P.add("dark_iron", head(cone((-0.1, 0, 1.06), (-1, 0, 0), 0.16, 0.026, segs=8)))
    # Ember clapper glowing in the mouth, finial on top of the haft.
    P.add("glow", head(blob((0.115, 0, 1.06), 0.042, segs=10, rings=7)))
    P.add("iron", lathe([(0.022, 1.15), (0.027, 1.185), (0.016, 1.245), (0.0, 1.295)], segs=8))
    return A


def build_rapier():
    A = Asset("PendulumRapier", weight=1.2, tint="#FFD27A",
              usage="Clockmaker's rapier: needle blade +Y to y=1.12, brass cup guard with a gear disc facing the "
                    "camera, S quillons, knuckle bow on +X, pendulum charm under the pommel. Emission = gear gem + "
                    "pendulum glass.")
    P = A.piece("PendulumRapier")
    rings = []
    rows = 20
    for i in range(rows + 1):
        t = i / rows
        w = lerp(0.0165, 0.006, t ** 0.8)
        th = lerp(0.0062, 0.0028, t)
        z = lerp(0.1, 1.08, t)
        rings.append([Vector(p) for p in ((w, 0, z), (w * 0.4, th, z), (0, th * 1.1, z), (-w * 0.4, th, z), (-w, 0, z),
                                          (-w * 0.4, -th, z), (0, -th * 1.1, z), (w * 0.4, -th, z))])
    P.add("steel", loft(rings, tip1=Vector((0, 0, 1.125))))
    P.add("steel", cbox((0, 0, 0.11), (0.026, 0.011, 0.05), bev=0.003))
    # Cup guard (opens toward the blade) and the gear disc across it.
    P.add("brass", lathe([(0.0, 0.052), (0.034, 0.055), (0.057, 0.065), (0.069, 0.082), (0.066, 0.088),
                          (0.052, 0.077), (0.03, 0.069), (0.0, 0.066)], segs=20))
    gear = lathe([(0.0, -0.0045), (0.046, -0.0045), (0.046, 0.0045), (0.0, 0.0045)], segs=24)
    P.add("brass", aim(gear, (0, 1, 0), (0, 0, 0.075)))
    for k in range(12):
        tooth = cbox((0, 0, 0.0505), (0.012, 0.008, 0.011), bev=0.001)
        tooth = rot(tooth, TAU * k / 12, (0, 1, 0))
        P.add("brass", eh.translate(tooth, Vector((0, 0, 0.075))))
    P.add("glow", blob((0, 0, 0.075), 0.014, scale=(1, 0.75, 1), segs=10, rings=6))
    # S-curved quillons with ball ends.
    q = catmull([(-0.11, 0, 0.115), (-0.075, 0, 0.088), (-0.03, 0, 0.078), (0.03, 0, 0.078), (0.075, 0, 0.068),
                 (0.11, 0, 0.045)], n=3)
    P.add("brass", tube(q, 0.0068, segs=6))
    P.add("brass", blob((-0.113, 0, 0.118), 0.012, segs=8, rings=5))
    P.add("brass", blob((0.113, 0, 0.042), 0.012, segs=8, rings=5))
    # Knuckle bow sweeping from the guard to the pommel on the +X side.
    k = catmull([(0.05, 0, 0.07), (0.074, 0, 0.03), (0.07, 0, -0.06), (0.042, 0, -0.118), (0.018, 0, -0.132)], n=4)
    P.add("brass", tube(k, 0.0058, segs=6))
    P.add("grip", lathe(ridged(-0.112, 0.048, 0.0135, 0.0156, 15, end_r=0.0138), segs=8))
    P.add("brass", lathe([(0.016, 0.044), (0.019, 0.05), (0.017, 0.056)], segs=10, cap0=False, cap1=False))
    P.add("brass", lathe([(0.0, -0.168), (0.012, -0.165), (0.02, -0.152), (0.022, -0.136), (0.018, -0.123),
                          (0.013, -0.116), (0.0, -0.112)], segs=12))
    # Pendulum charm.
    P.add("brass", torus((0, 0, -0.182), 0.009, 0.0026, normal=(1, 0, 0), seg=8, rseg=4))
    P.add("brass", torus((0, 0, -0.197), 0.009, 0.0026, normal=(0, 1, 0), seg=8, rseg=4))
    P.add("brass", tube([(0, 0, -0.205), (0, 0, -0.24)], 0.0028, segs=5))
    bob = lathe([(0.0, -0.006), (0.026, -0.006), (0.03, -0.002), (0.03, 0.002), (0.026, 0.006), (0.0, 0.006)],
                segs=18)
    P.add("brass", aim(bob, (0, 1, 0), (0, 0, -0.265)))
    P.add("glow", blob((0, 0, -0.265), 0.017, scale=(1, 0.5, 1), segs=10, rings=6))
    return A


def build_scythe():
    A = Asset("TideScythe", weight=1.3, tint="#7FE8FF",
              usage="Tide scythe: driftwood snath (grip at origin, y=-0.6..1.1), crescent blade from the top toward "
                    "+X curving down to (0.78, 0.76), edge on the inner side; kelp strips, side nib on -X. Emission = "
                    "sea-glass line along the blade spine.")
    P = A.piece("TideScythe")

    def c(z):
        return Vector((0.022 * math.sin(z * 2.2 + 0.3) - 0.022 * math.sin(0.3), 0.0, z))

    zs = [lerp(-0.6, 1.1, i / 26) for i in range(27)]
    P.add("drift_wood", tube([c(z) for z in zs], [0.0215 - 0.0035 * (z + 0.6) / 1.7 for z in zs], segs=8))
    P.add("grip", eh.translate(lathe(ridged(-0.13, 0.13, 0.0228, 0.0252, 13, end_r=0.0226), segs=8), c(0.0)))
    nib = [c(0.52), c(0.52) + Vector((-0.06, 0, 0.03)), c(0.52) + Vector((-0.12, 0, 0.035))]
    P.add("dark_wood", tube(nib, [0.0125, 0.012, 0.0105], segs=6))
    P.add("iron", torus(tuple(c(0.52)), 0.0215, 0.005, seg=10, rseg=4))
    P.add("iron", cone(tuple(c(-0.6)), (0, 0, -1), 0.09, 0.02, segs=8))
    top = c(1.1)
    P.add("iron", cbox((top.x + 0.015, 0, 1.085), (0.075, 0.034, 0.075), bev=0.008, segs=2))
    for x, z in ((-0.004, 1.065), (0.03, 1.11)):
        for sgn in (-1, 1):
            P.add("iron", blob((top.x + x, sgn * 0.018, z), 0.006, scale=(1, 0.55, 1), segs=6, rings=4))
    spine = catmull([(top.x + 0.02, 0, 1.1), (0.2, 0, 1.165), (0.4, 0, 1.15), (0.57, 0, 1.06), (0.7, 0, 0.92),
                     (0.775, 0, 0.77)], n=5)

    def width(t):
        return 0.012 + 0.088 * math.sin(math.pi * min(1.0, t * 1.05) ** 0.75) ** 0.9 * (1.0 - t) ** 0.35

    tip = spine[-1] + (spine[-1] - spine[-2]).normalized() * 0.035
    P.add("scythe_blade", blade_sweep(spine, width, lambda t: lerp(0.0075, 0.003, t), side_hint=(0, 0, -1), tip=tip))
    glass_n = int(len(spine) * 0.72)

    def glass(k, f):
        th = lerp(0.0075, 0.003, k / max(1, len(spine) - 1)) + 0.0016
        return [(0.012, th), (0.021, th), (0.021, -th), (0.012, -th)]

    P.add("glow", sweep(spine[1:glass_n], glass, side_hint=(0, 0, -1)))
    rng = random.Random(11)
    for i, x in enumerate((-0.02, 0.012, 0.04)):
        P.add("kelp", ribbon((top.x + x, 0.019 * (1 if i % 2 else -1), 1.05), 0.2 + 0.06 * i, 0.03, rng))
    return A


def build_flail():
    A = Asset("ChainFlail", weight=1.25, tint="#FF7A3A",
              usage="Chain flail: dark-wood handle (grip at origin, y=-0.19..0.24), interlocked chain arcing to a "
                    "spiked iron ball centred at (0.19, 0.62). Emission = molten windows on both ball faces.")
    P = A.piece("ChainFlail")
    zs = [lerp(-0.17, 0.21, i / 8) for i in range(9)]
    P.add("dark_wood", tube([(0, 0, z) for z in zs], 0.0195, segs=8))
    P.add("grip", lathe(ridged(-0.12, 0.09, 0.021, 0.0236, 11, end_r=0.0212), segs=8))
    P.add("iron", lathe([(0.0, -0.205), (0.016, -0.2), (0.026, -0.185), (0.026, -0.168), (0.021, -0.16)], segs=10))
    P.add("iron", lathe([(0.021, 0.19), (0.026, 0.198), (0.026, 0.226), (0.018, 0.238), (0.0, 0.242)], segs=10))
    P.add("iron", torus((0, 0, 0.258), 0.014, 0.0045, normal=(1, 0, 0), seg=10, rseg=4))
    path = bezier((0, 0, 0.275), (0.0, 0, 0.46), (0.17, 0, 0.555), 24)
    P.add("iron", chain_links(resample(path, 0.0245)))
    ball = Vector((0.19, 0, 0.625))
    P.add("dark_iron", blob(tuple(ball), 0.074, segs=16, rings=12))
    P.add("iron", torus(tuple(ball), 0.075, 0.007, normal=(0.55, 0, -0.84), seg=20, rseg=4))
    P.add("iron", torus(tuple(ball - Vector((0.03, 0, 0.047))), 0.014, 0.0045, normal=(0, 1, 0), seg=10, rseg=4))
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(16):
        yv = 1.0 - 2.0 * (i + 0.5) / 16
        r = math.sqrt(max(0.0, 1.0 - yv * yv))
        d = Vector((math.cos(golden * i) * r, yv, math.sin(golden * i) * r))
        if d.dot(Vector((-0.55, 0, -0.84))) > 0.8:
            continue  # leave room for the chain eye
        if abs(d.y) > 0.85:
            continue  # the camera-facing poles hold the molten windows
        P.add("iron", cone(tuple(ball + d * 0.066), tuple(d), 0.06, 0.016, segs=6))
    for sgn in (-1, 1):
        P.add("iron", torus(tuple(ball + Vector((0, sgn * 0.068, 0))), 0.024, 0.0055, normal=(0, 1, 0), seg=14,
                            rseg=4))
        P.add("glow", blob(tuple(ball + Vector((0, sgn * 0.066, 0))), 0.022, scale=(1, 0.45, 1), segs=10, rings=6))
    return A


def build_shovel():
    A = Asset("GraveShovel", weight=1.2, tint="#B8B0A0",
              usage="Gravedigger's shovel: ash shaft (grip at origin, y=-0.6..0.86), D-handle at the bottom, pointed "
                    "spade y=0.84..1.2 facing the camera (+-Z). Emission = three embedded star chips.")
    P = A.piece("GraveShovel")
    zs = [lerp(-0.45, 0.8, i / 18) for i in range(19)]
    P.add("ash", tube([(0, 0, z) for z in zs], 0.0195, segs=8))
    P.add("grip", lathe(ridged(-0.12, 0.12, 0.021, 0.0236, 12, end_r=0.0212), segs=8))
    # D-handle.
    P.add("iron", lathe([(0.0205, -0.47), (0.024, -0.46), (0.024, -0.43), (0.02, -0.42)], segs=10))
    for sgn in (-1, 1):
        P.add("iron", tube([(sgn * 0.012, 0, -0.455), (sgn * 0.05, 0, -0.52), (sgn * 0.062, 0, -0.585)], 0.007,
                           segs=6, flatten=0.6, up=(0, 1, 0)))
    P.add("dark_wood", tube([(-0.075, 0, -0.592), (0.075, 0, -0.592)], 0.0145, segs=8))
    # Socket and spade.
    P.add("iron", lathe([(0.0205, 0.69), (0.025, 0.7), (0.028, 0.79), (0.034, 0.85), (0.03, 0.865)], segs=10))
    for z in (0.73, 0.79):
        P.add("iron", blob((0, 0.027, z), 0.006, scale=(1, 0.6, 1), segs=6, rings=4))
    poly = [(-0.112, 0.85), (-0.118, 0.96), (-0.112, 1.05), (-0.085, 1.13), (-0.04, 1.18), (0.0, 1.2), (0.04, 1.18),
            (0.085, 1.13), (0.112, 1.05), (0.118, 0.96), (0.112, 0.85), (0.05, 0.835), (-0.05, 0.835)]
    spade = prism_xz(poly, -0.0045, 0.0045)
    spade = xform(spade, lambda v: Vector((v.x, v.y + 0.022 * (v.x / 0.118) ** 2 - 0.01 * ((v.z - 0.85) / 0.35),
                                           v.z)))
    P.add("spade", spade)
    for sgn in (-1, 1):
        P.add("iron", cbox((sgn * 0.075, 0.004, 0.855), (0.07, 0.022, 0.012), bev=0.003))
    for x, z in ((-0.03, 0.99), (0.042, 1.065), (0.004, 0.925)):
        for sgn in (-1, 1):
            y = sgn * 0.0046 + 0.022 * (x / 0.118) ** 2 - 0.01 * ((z - 0.85) / 0.35)
            P.add("glow", blob((x, y, z), 0.0105, scale=(1, 0.4, 1), segs=8, rings=5))
    return A


def build_crossbow():
    A = Asset("Crossbow", weight=1.2, tint="#E6D2A0",
              usage="Fishbone crossbow (Bow mount convention): pistol grip at origin, stock along Y with the butt at "
                    "+Y, bone prod with limbs along +-Z at y=-0.34, a bolt loaded toward -Y. Emission = glass sight.")
    P = A.piece("Crossbow")
    P.add("dark_wood", tube([(0, 0.03, -0.075), (0, 0.012, 0.0), (0, -0.004, 0.075)], [0.0175, 0.0175, 0.016],
                            segs=8))
    P.add("grip", eh.translate(rot(lathe(ridged(-0.06, 0.05, 0.0186, 0.0204, 9, end_r=0.0184), segs=8), 0.22,
                                   (1, 0, 0)), Vector((0, 0.012, 0))))
    P.add("dark_wood", cbox((0, -0.07, 0.094), (0.044, 0.6, 0.046), bev=0.009, segs=2))
    butt = cbox((0, 0.24, 0.07), (0.04, 0.18, 0.1), bev=0.012, segs=2)
    P.add("dark_wood", rot(butt, -0.32, (1, 0, 0), (0, 0.17, 0.094)))
    P.add("brass", cbox((0, -0.17, 0.119), (0.012, 0.36, 0.006), bev=0.002))
    up = [(0, -0.345, 0.094), (0, -0.351, 0.16), (0, -0.345, 0.25), (0, -0.326, 0.33), (0, -0.298, 0.38),
          (0, -0.276, 0.397)]
    for sign in (1, -1):
        pts = [(x, y, 0.094 + sign * (z - 0.094)) for x, y, z in up]
        P.add("bone", tube(catmull(pts, n=3), [lerp(0.019, 0.008, i / 15) for i in range(16)], segs=6, flatten=0.7,
                           up=(1, 0, 0)))
        tip = pts[-1]
        P.add("iron", blob(tip, 0.009, segs=6, rings=4))
    P.add("iron", cbox((0, -0.345, 0.094), (0.05, 0.04, 0.05), bev=0.006))
    P.add("string", tube([up[-1], (0, -0.1, 0.122), (0, -0.276, 0.094 - (0.397 - 0.094))], 0.0024, segs=4))
    P.add("iron", cbox((0, -0.1, 0.123), (0.03, 0.024, 0.016), bev=0.004))
    P.add("iron", torus((0, -0.405, 0.094), 0.042, 0.0065, normal=(1, 0, 0), seg=16, rseg=4))
    # Loaded bolt.
    P.add("ash", tube([(0, -0.405, 0.131), (0, -0.105, 0.131)], 0.0058, segs=6))
    P.add("iron", cone((0, -0.405, 0.131), (0, -1, 0), 0.05, 0.011, segs=6))
    for sgn in (-1, 1):
        fin = [[(0, -0.16, 0.131 + sgn * 0.004), (0, -0.115, 0.131 + sgn * 0.004)],
               [(0, -0.15, 0.131 + sgn * 0.022), (0, -0.112, 0.131 + sgn * 0.02)]]
        P.add("red_cloth", thick_sheet(fin, 0.002, normal_hint=(1, 0, 0)))
    # Trigger and glass sight.
    P.add("iron", tube(catmull([(0, -0.03, 0.072), (0, -0.048, 0.04), (0, -0.04, 0.018)], n=3), 0.0045, segs=5))
    P.add("brass", torus((0, 0.02, 0.134), 0.013, 0.004, normal=(0, 1, 0), seg=12, rseg=4))
    P.add("glow", blob((0, 0.02, 0.134), 0.01, segs=8, rings=5))
    return A


def armory_assets():
    return [build_maul(), build_rapier(), build_scythe(), build_flail(), build_shovel(), build_crossbow()]


ARMORY_HP = {"string": (0.0, 1), "rope": (0.0, 1), "red_cloth": (0.0, 1), "kelp": (0.0, 1), "glow": (0.0, 1),
             "steel": (0.001, 1), "scythe_blade": (0.0015, 1), "spade": (0.002, 1)}
ARMORY_MAT_WEIGHT = {"bronze": 1.3, "scythe_blade": 1.3, "spade": 1.2, "steel": 1.2, "glow": 0.6, "string": 0.5}


def main():
    if "--verify" in ba.cli_args():
        ok = ba.verify_kit(MANIFEST)
        print("[armory] verify", "PASSED" if ok else "FAILED")
        return
    ba.run_kit(assets_fn=armory_assets, materials_fn=armory_materials, atlas="Armory", tex_dir=TEX_DIR,
               fbx_dir=OUT_DIR, manifest_path=MANIFEST, prev_dir=PREV, generator="Tools/Blender/build_armory.py",
               size=2048, hp_cfg=ARMORY_HP, flat=(), mat_weight=ARMORY_MAT_WEIGHT, budget=lambda a: 6000,
               emission_colors={"BellMaul clapper": "#FFB347", "PendulumRapier gem + pendulum": "#FFD27A",
                                "TideScythe sea-glass": "#FFD27A", "ChainFlail windows": "#FF8A3A",
                                "GraveShovel star chips": "#FFE9A0", "Crossbow sight": "#FFD27A"},
               views=("three_quarter", "front"), cols=3)


if __name__ == "__main__":
    main()
