"""0.6 world props in two kits sharing the armory material library.

"Sanctum" (2048): the Mutator, Blacksmith (+ anvil) and Tailor (+ dress form)
NPCs, the TimedDoor vault (TimedDoor_Left / TimedDoor_Right leaves swing,
TimedDoor_Hand turns) and the CurseShroud (chains + skull padlock dropped over a
normal chest; it shatters when the chest is opened).

"Relics" (2048): four amulets, three rune tablets (Vine / Ram / Spider), the
CrackedBlock (breakable wall), RamSlab (rune floor), VineBulb + VineStalk
(tileable 1 m) + VineLeaf (platform).

Conventions (Tools/PIPELINE.md): floor props / NPCs have their pivot at the
bottom centre (z = 0) and face Blender -Y; amulets and runes are centred on the
origin.  Blender (x, y, z) == Unity (x, z, y).

Run headless:  Blender -b --factory-startup -P Tools/Blender/sanctum_props.py -- --kit=Sanctum|Relics
Live preview:  import sanctum_props; sanctum_props.preview("Sanctum")
"""

import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import armory_kit as K  # noqa: E402
import build_arsenal as ba  # noqa: E402
import dc_common as dc  # noqa: E402
import env_helpers as eh  # noqa: E402
from armory_kit import (TAU, Asset, blob, catmull, cbox, chain, cone, disc, gem, lathe, lerp, loft,  # noqa: E402
                        prism_xz, ring_of, rot, thick_sheet, torus, tube)
from build_arsenal import box, translate  # noqa: E402
from build_props import cloth, skin_mat, stone_mat  # noqa: E402

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


# ---------------------------------------------------------------------------
# Materials (the armory library + NPC / environment extras)
# ---------------------------------------------------------------------------

def extra_materials():
    M = {}
    M["coat"] = cloth("S_Coat", "#B4B6A0", "#62645A", "#E2E4D0", edge_r=0.006)
    M["trousers"] = cloth("S_Trousers", "#3A3A46", "#16161C", "#646474", edge_r=0.006)
    M["stripes"] = cloth("S_Stripes", "#3A3046", "#140E1A", "#6E6280", edge_r=0.006, stripes=("x", 40.0, 0.35, "#B8A8C8"))
    M["shirt"] = cloth("S_Shirt", "#6A2A22", "#2A0E0A", "#A04A3A", edge_r=0.006)
    M["tailcoat"] = cloth("S_Tailcoat", "#3E2A66", "#160C2A", "#7A5AB0", edge_r=0.006)
    M["velvet"] = cloth("S_Velvet", "#6A1236", "#26040E", "#B04A6A", edge_r=0.006)
    M["tape"] = cloth("S_Tape", "#E8C860", "#A08030", "#FFF0A0", edge_r=0.002, stripes=("z", 60.0, 0.12, "#3A2A10"))
    M["skin_pale"] = skin_mat("S_SkinPale", "#C8B8A8", "#7A6458", "#EDE0D4")
    M["skin_ruddy"] = skin_mat("S_SkinRuddy", "#B87458", "#5A2E20", "#E0A080")
    M["skin_grey"] = skin_mat("S_SkinGrey", "#A8A0B4", "#544E62", "#D8D0E4")
    M["hair"] = ba.make_mat("S_Hair", "#3E3832", dark="#141210", light="#7E746C", rough=0.7, noise_scale=30,
                            noise_amt=0.8, bevel_radius=0.002)
    M["eye"] = ba.make_mat("S_Eye", "#14100E", dark="#000000", light="#5A5450", rough=0.15, noise_scale=10,
                           noise_amt=0.2, bevel_radius=0.001)
    M["stone"] = stone_mat("S_Stone", scale=0.5)
    M["stone_dark"] = stone_mat("S_StoneDark", base="#3A4048", dark="#181C22", light="#5E6670", scale=0.5)
    M["crack"] = K.cracked_mat("S_Crack", "#4A4E56", "#16181C", "#7A808A", "#FF8A3A", scale=4.0, width=0.025)
    M["leaf"] = ba.make_mat("S_Leaf", "#3E7A32", dark="#163A12", light="#9AD870", rough=0.5, noise_scale=14,
                            noise_amt=0.6, bevel_radius=0.003)
    M["vine"] = ba.wood_mat("S_Vine", "#4A5A2A", "#1A2410", "#82924E", grain=0.05, edge_r=0.004)
    M["bulb"] = K.gem_mat("S_Bulb", "#6AA040", "#24401A", "#C8F08A", "#8CFF4A", 0.35)
    M["sand"] = K.glow_mat("S_Sand", "#FFCF6A")
    return M


def sanctum_materials():
    M = K.kit_materials()
    M.update(extra_materials())
    return M


def materials_cached():
    """Reuse the armory library already in the live file; build only the extras once."""
    scene = bpy.context.scene
    stored = json.loads(scene.get("dc_sanctum_mats", "{}"))
    if stored and all(n in bpy.data.materials for n in stored.values()):
        return {k: bpy.data.materials[n] for k, n in stored.items()}
    M = dict(K.kit_materials_cached())
    M.update(extra_materials())
    scene["dc_sanctum_mats"] = json.dumps({k: m.name for k, m in M.items()})
    return M


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def ring_pts(z, cx, cy, rx, ry, n=16, fn=None):
    out = []
    for i in range(n):
        a = TAU * i / n
        p = Vector((cx + math.cos(a) * rx, cy + math.sin(a) * ry, z))
        if fn:
            p = fn(p, a, i)
        out.append(p)
    return out


def legs(P, hip_z, width, foot_y=-0.06, r=(0.1, 0.08), mat="trousers", boot="leather", boot_h=0.3):
    for sx in (-1, 1):
        x = sx * width
        P.add(mat, tube([(x, 0, hip_z), (x * 1.05, -0.02, hip_z * 0.55), (x * 1.08, 0, boot_h)], [r[0], r[1] * 1.05, r[1]],
                        segs=10))
        P.add(boot, tube([(x * 1.08, 0, boot_h + 0.02), (x * 1.08, 0, 0.1)], [r[1] * 1.12, r[1] * 1.05], segs=10))
        P.add(boot, torus((x * 1.08, 0, boot_h + 0.02), r[1] * 1.12, 0.014, seg=10, rseg=4))
        P.add(boot, blob((x * 1.08, foot_y, 0.065), 0.1, scale=(0.85, 1.5, 0.66), segs=10, rings=6))


def arm(P, pts, radii, mat, hand_mat, hand_r=0.055, hand_scale=(1, 0.8, 1.2)):
    P.add(mat, tube(catmull(pts, 2), radii, segs=9))
    P.add(hand_mat, blob(Vector(pts[-1]) + (Vector(pts[-1]) - Vector(pts[-2])).normalized() * hand_r * 0.9, hand_r,
                         scale=hand_scale, segs=8, rings=6))


def head(P, c, r, skin, eyes_y=None, eye_gap=0.045, eye_z=0.02, scale=(0.95, 0.95, 1.1)):
    c = Vector(c)
    P.add(skin, blob(c, r, scale=scale, segs=14, rings=10))
    ey = eyes_y if eyes_y is not None else -r * scale[1] * 0.92
    for sx in (-1, 1):
        P.add("eye", blob(c + Vector((sx * eye_gap, ey, eye_z)), r * 0.13, segs=6, rings=4))
    return c


# ---------------------------------------------------------------------------
# Sanctum: NPCs
# ---------------------------------------------------------------------------

def build_mutator():
    A = Asset("Mutator", weight=1.5, tint="#8CFF4A",
              usage="Mutation NPC ~2.0 m, static, pivot at the feet, faces -Z. Stained surgeon's coat, goggles, a "
                    "glowing green vat on the back feeding a syringe. Emission = vat fluid, goggles, syringe.")
    P = A.piece("Mutator")
    rng = random.Random(41)
    legs(P, 0.86, 0.12)

    def coat_fn(p, a, i):
        if p.z < 0.5:
            p.z += (0.035 if i % 3 == 0 else 0.0) + rng.uniform(-0.01, 0.01)
        return p

    levels = [(0.26, 0.0, 0.0, 0.34, 0.27), (0.6, 0.0, 0.0, 0.3, 0.23), (0.92, 0.0, 0.0, 0.25, 0.19),
              (1.15, 0.0, 0.0, 0.25, 0.18), (1.36, 0.0, 0.02, 0.29, 0.19), (1.48, 0.0, 0.03, 0.24, 0.16),
              (1.55, 0.0, 0.02, 0.1, 0.09)]
    P.add("coat", loft([ring_pts(z, cx, cy, rx, ry, 20, coat_fn) for z, cx, cy, rx, ry in levels]))
    # Coat lapels + front seam.
    for sx in (-1, 1):
        P.add("coat", tube([(sx * 0.05, -0.2, 1.45), (sx * 0.12, -0.215, 1.25), (sx * 0.04, -0.2, 1.0)], [0.02, 0.025, 0.012],
                           segs=5, flatten=3.0, up=Y))
    P.add("dark_iron", tube([(0, -0.195, 0.95), (0, -0.25, 0.6), (0, -0.28, 0.3)], [0.006, 0.006, 0.006], segs=4))
    # Stains (green blotches) and belt of vials.
    for _ in range(5):
        a = rng.uniform(-1.2, 1.2)
        z = rng.uniform(0.4, 1.0)
        rr = lerp(0.3, 0.25, (z - 0.4) / 0.6)
        P.add("green_glass", blob((math.sin(a) * rr, -math.cos(a) * rr * 0.82, z), 0.03, scale=(1.2, 0.3, 1.6), segs=6,
                                  rings=4))
    P.add("leather", torus((0, 0.0, 0.92), 0.25, 0.022, seg=20, rseg=4, flatten=0.4))
    P.add("brass", cbox((0, -0.205, 0.92), (0.07, 0.02, 0.06), bev=0.008))
    for k, a in enumerate((-0.9, -0.55, 0.55, 0.9)):
        c = Vector((math.sin(a) * 0.26, -math.cos(a) * 0.21, 0.86))
        P.add("green_glass" if k % 2 else "lavender_glass", lathe([(0.0, -0.06), (0.022, -0.055), (0.024, -0.01),
                                                                    (0.012, 0.0), (0.012, 0.025)], segs=8, center=c))
        P.add("wax", lathe([(0.013, 0.02), (0.015, 0.035), (0.0, 0.04)], segs=6, center=c))
    # Arms: left hangs, right raises a syringe.
    arm(P, [(-0.29, 0.0, 1.42), (-0.36, -0.03, 1.15), (-0.34, -0.08, 0.92)], [0.075, 0.07, 0.065, 0.06, 0.058], "coat",
        "grip")
    arm(P, [(0.29, 0.0, 1.42), (0.4, -0.12, 1.2), (0.3, -0.3, 1.25)], [0.075, 0.07, 0.065, 0.06, 0.058], "coat", "grip")
    hand = Vector((0.27, -0.36, 1.27))
    sy_axis = Vector((-0.3, -0.25, 1.0)).normalized()
    P.add("green_glass", lathe([(0.026, -0.08), (0.026, 0.08)], segs=10, axis=sy_axis, center=hand))
    P.add("glow_poison", lathe([(0.02, -0.075), (0.02, 0.04)], segs=8, axis=sy_axis, center=hand))
    P.add("steel", cone(tuple(hand + sy_axis * 0.08), tuple(sy_axis), 0.12, 0.006, segs=5))
    P.add("brass", torus(tuple(hand - sy_axis * 0.08), 0.03, 0.007, normal=tuple(sy_axis), seg=10, rseg=4))
    P.add("steel", lathe([(0.008, 0.0), (0.008, 0.08), (0.03, 0.085), (0.03, 0.095)], segs=8, axis=-sy_axis,
                         center=hand - sy_axis * 0.08))
    # Head: bald, goggles, surgical mask.
    P.add("skin_pale", tube([(0, 0.0, 1.5), (0, -0.02, 1.62)], [0.07, 0.06], segs=8))
    hc = head(P, (0, -0.03, 1.71), 0.12, "skin_pale", eye_z=0.025)
    P.add("coat", blob(hc + Vector((0, -0.07, -0.05)), 0.09, scale=(1.15, 0.6, 0.7), segs=10, rings=6))
    P.add("leather", torus(hc + Vector((0, 0, 0.03)), 0.118, 0.012, normal=(0, 0, 1), seg=18, rseg=4))
    for sx in (-1, 1):
        g = hc + Vector((sx * 0.048, -0.112, 0.03))
        P.add("brass", torus(tuple(g), 0.034, 0.01, normal=(0, 1, 0), seg=12, rseg=4))
        P.add("brass", lathe([(0.034, 0.0), (0.03, 0.03)], segs=12, axis=(0, -1, 0), center=g, cap0=False, cap1=False))
        P.add("glow_poison", disc_bm(g + Vector((0, -0.028, 0)), 0.028, 0.004, (0, 1, 0)))
    # Back vat with glowing fluid and a hose to the syringe hand.
    vc = Vector((0.0, 0.3, 1.18))
    P.add("green_glass", lathe([(0.17, -0.27), (0.18, -0.2), (0.18, 0.2), (0.17, 0.27)], segs=18, center=vc))
    P.add("glow_poison", lathe([(0.0, -0.25), (0.155, -0.25), (0.155, 0.12), (0.0, 0.14)], segs=16, center=vc))
    P.add("bone", blob(vc + Vector((0.02, -0.02, 0.0)), 0.06, scale=(1.0, 0.9, 1.3), segs=8, rings=6))
    for z in (-0.3, 0.3):
        P.add("brass", lathe([(0.0, z * 0.95), (0.2, z * 0.95), (0.2, z * 1.12), (0.0, z * 1.15)], segs=18, center=vc))
    for a in ring_of(4, "z", 0.4):
        P.add("brass", tube([vc + Vector((a[0] * 0.19, a[1] * 0.19, -0.3)), vc + Vector((a[0] * 0.19, a[1] * 0.19, 0.3))],
                            [0.01, 0.01], segs=5))
    for sx in (-1, 1):
        P.add("leather", tube(catmull([(sx * 0.15, -0.15, 1.45), (sx * 0.2, 0.0, 1.52), (sx * 0.17, 0.15, 1.4),
                                       (sx * 0.15, 0.13, 1.0)], 2), [0.014] * 7, segs=4, flatten=3.0, up=X))
    hose = catmull([vc + Vector((0.08, 0.0, 0.33)), (0.2, 0.2, 1.6), (0.42, 0.0, 1.5), (0.44, -0.18, 1.3),
                    hand - sy_axis * 0.1], 3)
    P.add("leather", tube(hose, [0.016] * len(hose), segs=6))
    return A


def disc_bm(center, r, th, axis):
    prof = [(0.0, -th), (r * 0.94, -th), (r, 0.0), (r * 0.94, th), (0.0, th)]
    return ba.aim(lathe(prof, segs=14), axis, center)


def build_blacksmith():
    A = Asset("Blacksmith", weight=1.6, tint="#FF7A22",
              usage="Blacksmith NPC ~2.0 m with a hammer on the shoulder; anvil on a stump at +0.95 m. Static, pivot "
                    "at the smith's feet, faces -Z. Emission = hot ingot on the anvil + forge coals.")
    P = A.piece("Blacksmith")
    rng = random.Random(7)
    legs(P, 0.85, 0.15, r=(0.12, 0.1))
    # Barrel torso + shirt.
    prof = [(0.0, 0.8), (0.27, 0.82), (0.35, 0.95), (0.38, 1.1), (0.4, 1.28), (0.38, 1.42), (0.3, 1.52), (0.14, 1.58),
            (0.0, 1.6)]
    body = lathe(prof, segs=18, scale_xy=(1.1, 0.8))
    P.add("shirt", body)
    # Leather apron: a slightly curved sheet from chest to knee with a bib.
    grid = []
    for r_ in range(7):
        v = r_ / 6
        z = lerp(1.42, 0.45, v)
        w = lerp(0.26, 0.36, v)
        row = []
        for c in range(5):
            u = c / 4 - 0.5
            yb = -0.33 if z > 0.82 else -0.27 - 0.05 * (0.82 - z)
            if z > 0.82:
                yb = -0.3 - 0.05 * math.sin(math.pi * (z - 0.82) / 0.6)
            row.append((u * 2 * w, yb + 0.05 * (u * 2) ** 2, z + (0.02 * math.sin(u * 7) if r_ == 6 else 0.0)))
        grid.append(row)
    P.add("leather", thick_sheet(grid, 0.012))
    for sx in (-1, 1):
        P.add("leather", tube([(sx * 0.2, -0.32, 1.42), (sx * 0.22, -0.15, 1.6), (sx * 0.2, 0.15, 1.5)], [0.016] * 3,
                              segs=4, flatten=3.0, up=X))
    P.add("leather", torus((0, 0, 1.0), 0.39, 0.02, seg=24, rseg=4, flatten=0.5))
    # Bare, heavy arms; left on the hip, right holds the hammer on the shoulder.
    for sx, pts in ((-1, [(-0.4, 0.0, 1.45), (-0.52, 0.0, 1.18), (-0.42, -0.1, 1.02)]),
                    (1, [(0.4, 0.0, 1.45), (0.55, -0.1, 1.25), (0.42, -0.24, 1.42)])):
        P.add("skin_ruddy", tube(catmull(pts, 2), [0.105, 0.1, 0.092, 0.082, 0.076], segs=10))
        P.add("shirt", blob(pts[0], 0.14, scale=(1.0, 0.9, 0.9), segs=10, rings=6))
        wrist = Vector(pts[-1])
        P.add("leather", lathe([(0.08, -0.07), (0.085, 0.0), (0.08, 0.07)], segs=10,
                               axis=tuple((wrist - Vector(pts[1])).normalized()), center=wrist - (wrist - Vector(pts[1])).normalized() * 0.08))
        P.add("skin_ruddy", blob(wrist + (wrist - Vector(pts[1])).normalized() * 0.06, 0.07, segs=8, rings=6))
    # Head: bald, heavy brow, braided beard.
    P.add("skin_ruddy", tube([(0, 0.0, 1.55), (0, -0.04, 1.66)], [0.1, 0.09], segs=10))
    hc = head(P, (0, -0.06, 1.77), 0.13, "skin_ruddy", eye_z=0.03)
    P.add("skin_ruddy", blob(hc + Vector((0, -0.11, 0.06)), 0.07, scale=(1.6, 0.6, 0.45), segs=8, rings=5))
    P.add("skin_ruddy", cone(tuple(hc + Vector((0, -0.12, 0.0))), (0, -1, -0.4), 0.05, 0.028, segs=6))
    beard = [hc + Vector((0, -0.08, -0.06)), hc + Vector((0, -0.16, -0.16)), hc + Vector((0, -0.2, -0.3)),
             hc + Vector((0, -0.2, -0.42))]
    P.add("hair", tube(catmull(beard, 2), [0.1, 0.09, 0.075, 0.06, 0.045, 0.03, 0.012], segs=9))
    for sx in (-1, 1):
        P.add("hair", tube([hc + Vector((sx * 0.1, -0.06, -0.02)), hc + Vector((sx * 0.08, -0.13, -0.12))], [0.045, 0.04],
                           segs=6))
        P.add("hair", blob(hc + Vector((sx * 0.045, -0.13, 0.065)), 0.025, scale=(1.4, 0.6, 0.5), segs=6, rings=4))
    for z in (-0.3, -0.38):
        P.add("brass", torus(tuple(hc + Vector((0, -0.2, z))), 0.04, 0.008, seg=10, rseg=4))
    # Hammer over the right shoulder.
    hand = Vector((0.45, -0.28, 1.48))
    hd = Vector((0.12, 0.6, 0.55)).normalized()
    P.add("ash", tube([hand - hd * 0.15, hand + hd * 0.6], [0.026, 0.024], segs=8))
    hh = hand + hd * 0.62
    P.add("dark_iron", ba.aim(lathe([(0.0, -0.13), (0.07, -0.13), (0.085, -0.1), (0.085, 0.1), (0.07, 0.13), (0.0, 0.13)],
                                    segs=8), X, hh))
    P.add("brass", torus(tuple(hh), 0.088, 0.01, normal=(1, 0, 0), seg=10, rseg=4))
    # Anvil on a stump, hot ingot and tongs.
    ax = 0.95
    P.add("dark_wood", lathe([(0.0, 0.0), (0.27, 0.0), (0.25, 0.04), (0.24, 0.4), (0.25, 0.44), (0.0, 0.45)], segs=14,
                             center=(ax, 0.05, 0.0), rng=rng, jitter=0.04))
    P.add("dark_iron", box((ax - 0.16, -0.1, 0.45), (ax + 0.16, 0.2, 0.52), bev=0.012))
    P.add("dark_iron", box((ax - 0.08, -0.05, 0.52), (ax + 0.08, 0.15, 0.68), bev=0.01))
    top = [(-0.28, 0.0), (0.22, 0.0), (0.24, 0.1), (-0.2, 0.1)]
    P.add("iron", prism_xz([(ax + x, 0.68 + z) for x, z in top], -0.08, 0.18))
    horn = [(ax - 0.28, 0.05, 0.73), (ax - 0.4, 0.05, 0.74), (ax - 0.5, 0.05, 0.765)]
    P.add("iron", tube(horn, [0.05, 0.03, 0.004], segs=8, flatten=1.3, up=Y))
    P.add("glow_fire", cbox((ax + 0.02, 0.03, 0.81), (0.22, 0.07, 0.04), bev=0.01))
    P.add("dark_iron", tube([(ax + 0.12, 0.03, 0.81), (ax + 0.3, -0.02, 0.83), (ax + 0.45, -0.05, 0.86)], [0.01] * 3, segs=4))
    P.add("dark_iron", tube([(ax + 0.12, 0.05, 0.8), (ax + 0.3, 0.06, 0.82), (ax + 0.45, 0.05, 0.8)], [0.01] * 3, segs=4))
    # Coal brazier behind the anvil.
    bx = Vector((ax + 0.45, 0.35, 0.0))
    for a in ring_of(3, "z", 0.3):
        P.add("dark_iron", tube([bx + Vector((a[0] * 0.18, a[1] * 0.18, 0.0)), bx + Vector((a[0] * 0.12, a[1] * 0.12, 0.45))],
                                [0.014, 0.012], segs=5))
    P.add("dark_iron", lathe([(0.1, 0.42), (0.2, 0.46), (0.22, 0.56), (0.2, 0.57), (0.1, 0.5)], segs=14, center=bx))
    for k in range(9):
        a = TAU * k / 9
        P.add("obsidian", blob(bx + Vector((math.cos(a) * 0.1 * (k % 3) / 2, math.sin(a) * 0.1 * (k % 3) / 2, 0.57)),
                               0.05, segs=6, rings=4, rng=rng, jitter=0.2))
    return A


def build_tailor():
    A = Asset("Tailor", weight=1.5, tint="#B57CFF",
              usage="Tailor NPC ~2.1 m (thread-spool top hat, tailcoat, giant scissors), with a dress form at -0.85 m. "
                    "Static, pivot at the feet, faces -Z. Emission = violet thread on the spool.")
    P = A.piece("Tailor")
    rng = random.Random(5)
    legs(P, 0.95, 0.09, r=(0.075, 0.06), mat="stripes", boot="dark_iron", boot_h=0.2)
    # Long tailcoat: narrow waist, tails behind.
    def tails(p, a, i):
        if p.z < 0.7 and math.sin(a) > 0.2:
            p.z -= 0.25 * (0.7 - p.z) / 0.4
            p.y += 0.06
        return p
    levels = [(0.35, 0.0, 0.02, 0.2, 0.15), (0.7, 0.0, 0.02, 0.2, 0.15), (1.0, 0.0, 0.0, 0.17, 0.13),
              (1.22, 0.0, 0.0, 0.21, 0.14), (1.45, 0.0, 0.0, 0.25, 0.15), (1.58, 0.0, 0.0, 0.2, 0.12),
              (1.63, 0.0, 0.0, 0.08, 0.07)]
    P.add("tailcoat", loft([ring_pts(z, cx, cy, rx, ry, 20, tails) for z, cx, cy, rx, ry in levels]))
    P.add("silk", prism_xz([(-0.07, 1.58), (0.07, 1.58), (0.03, 1.2), (-0.03, 1.2)], -0.15, -0.13))
    for z in (1.25, 1.33, 1.41):
        P.add("brass", blob((0.0, -0.155, z), 0.012, segs=6, rings=4))
    # Measuring tape draped round the neck.
    for sx in (-1, 1):
        pts = catmull([(0, 0.1, 1.62), (sx * 0.12, -0.03, 1.6), (sx * 0.1, -0.15, 1.45), (sx * 0.08, -0.17, 1.1 + 0.08 * sx)], 3)
        P.add("tape", tube(pts, [0.012] * len(pts), segs=4, flatten=4.0, up=Y))
    # Arms: right holds giant scissors, left raised with a pincushion.
    arm(P, [(0.22, 0.0, 1.5), (0.3, -0.05, 1.22), (0.28, -0.2, 1.08)], [0.055, 0.05, 0.046, 0.043, 0.04], "tailcoat",
        "skin_grey", hand_r=0.045)
    arm(P, [(-0.22, 0.0, 1.5), (-0.34, -0.06, 1.25), (-0.3, -0.2, 1.38)], [0.055, 0.05, 0.046, 0.043, 0.04], "tailcoat",
        "skin_grey", hand_r=0.045)
    P.add("velvet", blob((-0.3, -0.27, 1.45), 0.05, scale=(1, 1, 0.8), segs=8, rings=6))
    for k in range(6):
        d = Vector((math.cos(k), math.sin(k) * 0.6 - 0.5, 0.8)).normalized()
        P.add("steel", tube([Vector((-0.3, -0.27, 1.45)) + d * 0.03, Vector((-0.3, -0.27, 1.45)) + d * 0.08], [0.003, 0.003],
                            segs=4))
        P.add("glow_violet" if k % 2 else "red_cloth", blob(Vector((-0.3, -0.27, 1.45)) + d * 0.085, 0.009, segs=5, rings=3))
    sc = Vector((0.3, -0.26, 1.02))
    for s in (-1, 1):
        blade_pts = [sc + Vector((0.0, -0.01 * s, 0.0)), sc + Vector((0.08 * s, -0.01 * s, -0.25)),
                     sc + Vector((0.02 * s, -0.01 * s, -0.52))]
        P.add("steel", tube(catmull(blade_pts, 3), [0.025, 0.03, 0.03, 0.028, 0.022, 0.015, 0.002], segs=4, flatten=4.0,
                            up=Y))
        P.add("brass", torus(tuple(sc + Vector((-0.07 * s, -0.01 * s, 0.07))), 0.045, 0.01, normal=(0, 1, 0), seg=12, rseg=4))
    P.add("brass", blob(tuple(sc + Vector((0, -0.03, 0))), 0.015, segs=6, rings=4))
    # Head: long, grey, pince-nez, spool top hat.
    P.add("skin_grey", tube([(0, 0.0, 1.6), (0, -0.01, 1.7)], [0.05, 0.045], segs=8))
    hc = head(P, (0, -0.02, 1.81), 0.11, "skin_grey", eye_gap=0.04, eye_z=0.02, scale=(0.82, 0.9, 1.28))
    P.add("skin_grey", cone(tuple(hc + Vector((0, -0.09, 0.0))), (0, -1, -0.8), 0.07, 0.022, segs=6))
    for sx in (-1, 1):
        P.add("brass", torus(tuple(hc + Vector((sx * 0.04, -0.1, 0.02))), 0.026, 0.004, normal=(0, 1, 0), seg=12, rseg=3))
        P.add("hair", tube(catmull([hc + Vector((sx * 0.02, -0.11, -0.06)), hc + Vector((sx * 0.08, -0.1, -0.05)),
                                    hc + Vector((sx * 0.14, -0.08, -0.0))], 2), [0.012, 0.012, 0.009, 0.006, 0.002], segs=5))
    P.add("dark_wood", lathe([(0.0, 0.0), (0.14, 0.0), (0.14, 0.025), (0.1, 0.03), (0.1, 0.2), (0.14, 0.205),
                              (0.14, 0.23), (0.0, 0.23)], segs=18, center=hc + Vector((0, 0.0, 0.11))))
    P.add("glow_violet", lathe(K.ridged(0.035, 0.195, 0.108, 0.114, 10), segs=18, center=hc + Vector((0, 0.0, 0.11)),
                               cap0=False, cap1=False))
    P.add("dark_iron", tube([hc + Vector((0.0, 0.0, 0.34)), hc + Vector((0.0, -0.02, 0.44))], [0.004, 0.004], segs=4))
    # Dress form at -0.85.
    fx = Vector((-0.85, 0.1, 0.0))
    for a in ring_of(3, "z", 0.5):
        P.add("dark_wood", tube([fx + Vector((a[0] * 0.25, a[1] * 0.25, 0.0)), fx + Vector((0, 0, 0.35))], [0.02, 0.025],
                                segs=6))
    P.add("dark_wood", tube([fx + Vector((0, 0, 0.3)), fx + Vector((0, 0, 0.85))], [0.025, 0.022], segs=6))
    form = [(0.0, 0.82), (0.2, 0.84), (0.24, 0.95), (0.17, 1.13), (0.2, 1.3), (0.23, 1.4), (0.16, 1.48), (0.06, 1.52),
            (0.0, 1.53)]
    P.add("velvet", lathe(form, segs=16, center=fx, scale_xy=(1.0, 0.7)))
    P.add("brass", lathe([(0.0, 1.52), (0.04, 1.53), (0.03, 1.6), (0.0, 1.62)], segs=8, center=fx))
    P.add("tape", torus(tuple(fx + Vector((0, 0, 1.13))), 0.175, 0.01, seg=20, rseg=4, flatten=0.3))
    for k in range(5):
        a = rng.uniform(-1.2, 1.2)
        z = rng.uniform(1.0, 1.4)
        p = fx + Vector((math.sin(a) * 0.2, -math.cos(a) * 0.14, z))
        P.add("steel", tube([p, p + Vector((math.sin(a) * 0.04, -0.05, 0.01))], [0.002, 0.002], segs=3))
        P.add("glow_violet" if k % 2 else "red_cloth", blob(tuple(p + Vector((math.sin(a) * 0.045, -0.055, 0.01))), 0.009,
                                                           segs=5, rings=3))
    # Draped cloth panel over the form's shoulder.
    grid = []
    for r_ in range(6):
        v = r_ / 5
        row = []
        for c in range(4):
            u = c / 3
            row.append((fx.x + lerp(-0.2, 0.05, u) + 0.02 * math.sin(v * 5), fx.y - 0.16 - 0.02 * math.sin(u * 3),
                        1.47 - v * 0.6 - 0.05 * u))
        grid.append(row)
    P.add("purple_cloth", thick_sheet(grid, 0.006))
    return A


# ---------------------------------------------------------------------------
# Sanctum: TimedDoor, CurseShroud
# ---------------------------------------------------------------------------

def build_timed_door():
    A = Asset("TimedDoor", weight=1.4, tint="#FFCF6A",
              usage="Timed vault door 2.2 x 3.3 m facing -Z: stone arch, clock face on top. TimedDoor_Left/Right pivot "
                    "on their outer hinges (rotate about Unity Y to open), TimedDoor_Hand pivots on the clock centre "
                    "(rotate about Unity Z). Emission = clock numerals, hand, hourglass sand.")
    F = A.piece("TimedDoor")
    L = A.piece("TimedDoor_Left", pivot=(-0.72, -0.12, 0.0))
    R = A.piece("TimedDoor_Right", pivot=(0.72, -0.12, 0.0))
    H = A.piece("TimedDoor_Hand", pivot=(0.0, -0.3, 2.82))
    rng = random.Random(9)
    # Stone jambs (stacked blocks) and arch voussoirs.
    for sx in (-1, 1):
        z = 0.0
        k = 0
        while z < 2.0:
            h = 0.32 + 0.06 * (k % 2)
            w = 0.36 if k % 2 else 0.3
            F.add("stone", box((sx * 0.78 if sx > 0 else -0.78 - w, -0.25, z), (sx * 0.78 + w if sx > 0 else -0.78, 0.25, z + h - 0.01),
                               bev=0.02))
            z += h
            k += 1
    n = 9
    for i in range(n):
        a0 = math.pi * i / n
        a1 = math.pi * (i + 1) / n
        poly = []
        for a in (a0, a1):
            poly.append((math.cos(a) * 0.78, 2.05 + math.sin(a) * 0.78))
        for a in (a1, a0):
            poly.append((math.cos(a) * 1.12, 2.05 + math.sin(a) * 1.12))
        rings = [[Vector((x, y, z)) for x, z in poly] for y in (-0.26, 0.26)]
        F.add("stone" if i != n // 2 else "stone_dark", eh.bm_bevel(loft(rings), 0.015, 1))
    # Clock face above the keystone (protrudes toward the viewer).
    cc = Vector((0.0, -0.28, 2.82))
    disc(F, tuple(cc), 0.36, 0.035, "brass", axis=(0, -1, 0), segs=32)
    disc(F, tuple(cc + Vector((0, -0.03, 0))), 0.31, 0.01, "dark_iron", axis=(0, -1, 0), segs=32)
    for k in range(12):
        a = TAU * k / 12
        p = cc + Vector((math.cos(a) * 0.26, -0.045, math.sin(a) * 0.26))
        F.add("glow_gold", cbox(tuple(p), (0.03 if k % 3 else 0.05, 0.01, 0.03 if k % 3 else 0.05), bev=0.004))
    F.add("brass", torus(tuple(cc + Vector((0, -0.04, 0))), 0.35, 0.014, normal=(0, 1, 0), seg=32, rseg=4))
    H.add("glow_gold", translate(prism_xz([(-0.022, 0.0), (0.0, 0.25), (0.022, 0.0), (0.0, -0.06)], -0.355, -0.34),
                                 (0, 0, 2.82)))
    H.add("brass", disc_bm(cc + Vector((0, -0.08, 0)), 0.032, 0.01, (0, 1, 0)))
    # Hourglasses on both jambs.
    for sx in (-1, 1):
        hc = Vector((sx * 0.95, -0.3, 1.25))
        F.add("brass", disc_bm(hc + Vector((0, 0, 0.2)), 0.1, 0.015, (0, 0, 1)))
        F.add("brass", disc_bm(hc - Vector((0, 0, 0.2)), 0.1, 0.015, (0, 0, 1)))
        F.add("ice", lathe([(0.0, -0.19), (0.08, -0.17), (0.07, -0.05), (0.012, 0.0),
                                                        (0.07, 0.05), (0.08, 0.17), (0.0, 0.19)], segs=12, center=hc))
        F.add("sand", lathe([(0.0, -0.185), (0.07, -0.165), (0.04, -0.1), (0.0, -0.08)], segs=10, center=hc))
        F.add("sand", lathe([(0.0, 0.03), (0.03, 0.08), (0.0, 0.1)], segs=8, center=hc))
        for a in ring_of(3, "z", 0.6):
            F.add("brass", tube([hc + Vector((a[0] * 0.09, a[1] * 0.09, -0.2)), hc + Vector((a[0] * 0.09, a[1] * 0.09, 0.2))],
                                [0.008, 0.008], segs=4))
    # Threshold step.
    F.add("stone_dark", box((-1.15, -0.4, 0.0), (1.15, 0.28, 0.08), bev=0.02))
    # Door leaves: riveted iron with gear emblems.
    for P_, sx in ((L, -1), (R, 1)):
        inner = 0.0
        outer = sx * 0.72
        x0, x1 = min(inner, outer), max(inner, outer)
        shape = []
        for i in range(9):
            t = i / 8
            x = lerp(x0, x1, t)
            zt = 2.05 + math.sqrt(max(0.0, 0.72 ** 2 - x ** 2)) * 0.97
            shape.append((x, zt))
        poly = [(x0, 0.08), (x1, 0.08)] + list(reversed(shape))
        if sx < 0:
            poly = [(x0, 0.08), (x1, 0.08)] + list(reversed(shape))
        P_.add("dark_iron", prism_xz(poly, -0.16, -0.08))
        for z in (0.45, 1.2, 1.95):
            P_.add("iron", box((x0 + 0.02, -0.19, z - 0.05), (x1 - 0.02, -0.15, z + 0.05), bev=0.01))
            for k in range(4):
                P_.add("brass", blob((lerp(x0 + 0.08, x1 - 0.08, k / 3), -0.195, z), 0.016, scale=(1, 0.6, 1), segs=6, rings=4))
        gc = Vector((sx * 0.36, -0.17, 1.55))
        P_.add("brass", torus(tuple(gc), 0.14, 0.022, normal=(0, 1, 0), seg=16, rseg=4))
        for k in range(10):
            a = TAU * k / 10
            P_.add("brass", cbox(tuple(gc + Vector((math.cos(a) * 0.17, 0, math.sin(a) * 0.17))), (0.04, 0.03, 0.04)))
        P_.add("glow_gold", disc_bm(gc + Vector((0, -0.01, 0)), 0.05, 0.012, (0, 1, 0)))
        P_.add("iron", torus((sx * 0.1, -0.22, 1.05), 0.06, 0.012, normal=(1, 0, 0), seg=12, rseg=4))
    return A


def build_curse_shroud():
    A = Asset("CurseShroud", weight=1.1, tint="#B57CFF",
              usage="Cursed-chest overlay: chains wrapped over a 1.0 x 0.6 x 0.55 chest, a skull padlock in front and "
                    "a violet floor sigil. Centre = chest pivot. Emission = skull eyes, floor sigil, chain glints.")
    P = A.piece("CurseShroud")
    rng = random.Random(13)
    W, D, H = 0.52, 0.33, 0.6
    # Two chains crossing over the lid, one around the middle.
    for x0, x1 in ((-0.36, 0.3), (0.34, -0.28)):
        pts = [Vector((x0, -D - 0.02, 0.05)), Vector((lerp(x0, x1, 0.3), -D - 0.03, 0.4)), Vector((lerp(x0, x1, 0.5), 0.0, H + 0.08)),
               Vector((lerp(x0, x1, 0.7), D + 0.03, 0.4)), Vector((x1, D + 0.02, 0.05))]
        path = catmull(pts, 4)
        for i, p in enumerate(path):
            if i % 1 == 0 and 0 < i < len(path):
                t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
                normal = t.cross(X).normalized() if i % 2 else X
                P.add("dark_iron", torus(tuple(p), 0.04, 0.011, normal=tuple(normal), seg=10, rseg=4, flatten=1.0))
    ring = [Vector((math.cos(a) * (W + 0.03), math.sin(a) * (D + 0.03), 0.3)) for a in [TAU * i / 40 for i in range(40)]]
    for i, p in enumerate(ring):
        t = (ring[(i + 1) % 40] - ring[i - 1]).normalized()
        P.add("dark_iron", torus(tuple(p), 0.04, 0.011, normal=tuple(Z if i % 2 else t.cross(Z)), seg=10, rseg=4))
    # Skull padlock.
    sc = Vector((0.0, -D - 0.09, 0.3))
    P.add("dark_iron", torus(tuple(sc + Vector((0, 0, 0.1))), 0.05, 0.012, normal=(1, 0, 0), seg=12, rseg=4))
    P.add("bone", blob(tuple(sc), 0.085, scale=(1.0, 0.85, 1.0), segs=12, rings=8))
    P.add("bone", blob(tuple(sc + Vector((0, -0.02, -0.07))), 0.05, scale=(1.0, 0.8, 0.7), segs=8, rings=5))
    for sx in (-1, 1):
        P.add("glow_violet", blob(tuple(sc + Vector((sx * 0.032, -0.07, 0.01))), 0.022, segs=6, rings=4))
    for k in range(4):
        P.add("bone", cbox(tuple(sc + Vector((-0.024 + k * 0.016, -0.06, -0.09))), (0.011, 0.01, 0.02), bev=0.003))
    # Floor sigil: violet ring with runic ticks.
    P.add("glow_violet", torus((0, 0, 0.012), 0.82, 0.014, seg=48, rseg=4, flatten=0.3))
    P.add("glow_violet", torus((0, 0, 0.012), 0.7, 0.008, seg=48, rseg=4, flatten=0.3))
    for k in range(12):
        a = TAU * k / 12
        P.add("glow_violet", cbox((math.cos(a) * 0.76, math.sin(a) * 0.76, 0.012), (0.05, 0.015, 0.008)))
    # Shards of bone stuck in the floor.
    for k in range(5):
        a = rng.uniform(0, TAU)
        p = Vector((math.cos(a) * 0.68, math.sin(a) * 0.5, 0.0))
        P.add("bone", cone(tuple(p), (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 1.0), rng.uniform(0.1, 0.2), 0.025, segs=5))
    return A


# ---------------------------------------------------------------------------
# Relics: amulets
# ---------------------------------------------------------------------------

def bail(P, top, mat):
    P.add(mat, torus(tuple(Vector(top) + Vector((0, 0, 0.035))), 0.03, 0.007, normal=(1, 0, 0), seg=14, rseg=5))
    chain(P, Vector(top) + Vector((-0.09, 0, 0.19)), Vector(top) + Vector((0, 0, 0.07)), 5, R=0.014, r=0.004, mat=mat)
    chain(P, Vector(top) + Vector((0.09, 0, 0.19)), Vector(top) + Vector((0, 0, 0.07)), 5, R=0.014, r=0.004, mat=mat)


def amulet_ember():
    A = Asset("AmuletEmber", weight=1.0, usage="Amulet: brass sun disc with an obsidian ember core and flame prongs; "
                                               "centred, faces -Y.")
    P = A.piece("AmuletEmber")
    disc(P, (0, 0, 0), 0.1, 0.012, "brass", axis=(0, -1, 0), segs=28)
    disc(P, (0, -0.012, 0), 0.06, 0.012, "obsidian", axis=(0, -1, 0), segs=20)
    P.add("brass", torus((0, -0.014, 0), 0.066, 0.008, normal=(0, 1, 0), seg=24, rseg=4))
    for k in range(8):
        a = TAU * k / 8 + TAU / 16
        d = Vector((math.cos(a), 0, math.sin(a)))
        path = [d * 0.095, d * 0.13 + Vector((math.cos(a + 0.6), 0, math.sin(a + 0.6))) * 0.02, d * 0.16]
        P.add("glow_fire" if k % 2 else "brass", tube(catmull(path, 2), [0.014, 0.011, 0.008, 0.005, 0.001], segs=5,
                                                      flatten=2.0, up=Y))
    P.add("glow_fire", gem_bm((0, -0.03, 0), 0.025))
    bail(P, (0, 0, 0.1), "brass")
    return A


def gem_bm(c, r, axis=(0, -1, 0), segs=6):
    return ba.aim(lathe([(0.0, -r * 0.7), (r, 0.0), (r * 0.6, r * 0.5), (0.0, r * 0.6)], segs=segs), axis, c)


def amulet_tide():
    A = Asset("AmuletTide", weight=1.0, usage="Amulet: silver scallop shell with a blue tide gem and a wave curl.")
    P = A.piece("AmuletTide")
    ribs = 9
    for k in range(ribs):
        a = math.radians(lerp(20, 160, k / (ribs - 1)))
        tip = Vector((math.cos(a) * 0.12, 0.0, -0.02 + math.sin(a) * 0.13))
        P.add("steel", tube([Vector((0, 0, -0.08)), tip * 0.55 + Vector((0, -0.012, -0.03)), tip],
                            [0.008, 0.02, 0.017], segs=5, flatten=2.0, up=Y))
    P.add("steel", blob((0, 0.004, 0.0), 0.09, scale=(1.25, 0.25, 1.05), segs=14, rings=8))
    P.add("ice", gem_bm((0, -0.03, 0.02), 0.035, segs=8))
    curl = [Vector((math.cos(t) * (0.05 - t * 0.006), -0.02, -0.1 + math.sin(t) * (0.04 - t * 0.004)))
            for t in [i * 0.5 for i in range(10)]]
    P.add("glow_ice", tube(curl, [0.008 * (1 - i / 12) for i in range(10)], segs=5))
    bail(P, (0, 0, 0.11), "steel")
    return A


def amulet_bone():
    A = Asset("AmuletBone", weight=1.0, usage="Amulet: bone ring with a small skull charm and red gem eyes.")
    P = A.piece("AmuletBone")
    P.add("bone", torus((0, 0, 0), 0.085, 0.018, normal=(0, 1, 0), seg=24, rseg=6))
    for k in range(12):
        a = TAU * k / 12
        P.add("bone", blob((math.cos(a) * 0.085, -0.012, math.sin(a) * 0.085), 0.014, segs=5, rings=4))
    P.add("bone", blob((0, -0.01, 0.0), 0.052, scale=(1.0, 0.8, 1.05), segs=12, rings=8))
    P.add("bone", blob((0, -0.03, -0.045), 0.03, scale=(1.0, 0.7, 0.7), segs=8, rings=5))
    for sx in (-1, 1):
        P.add("glow_red", blob((sx * 0.02, -0.05, 0.005), 0.012, segs=6, rings=4))
    P.add("red_cloth", tube([(0.06, -0.01, -0.06), (0.09, -0.02, -0.12), (0.07, -0.01, -0.18)], [0.012, 0.01, 0.004], segs=4,
                            flatten=3.0, up=Y))
    bail(P, (0, 0, 0.1), "dark_iron")
    return A


def amulet_star():
    A = Asset("AmuletStar", weight=1.0, usage="Amulet: gold eight-point star with a moonstone heart and violet rays.")
    P = A.piece("AmuletStar")
    poly = []
    for k in range(16):
        a = TAU * k / 16 + math.pi / 2
        r = 0.13 if k % 2 == 0 else 0.055
        poly.append((math.cos(a) * r, math.sin(a) * r))
    P.add("brass", prism_xz(poly, -0.008, 0.008))
    P.add("brass", prism_xz([(x * 0.7, z * 0.7) for x, z in poly], -0.016, -0.008))
    for k in range(0, 16, 2):
        a = TAU * k / 16 + math.pi / 2
        P.add("glow_violet", tube([(math.cos(a) * 0.04, -0.018, math.sin(a) * 0.04), (math.cos(a) * 0.11, -0.012, math.sin(a) * 0.11)],
                                  [0.006, 0.002], segs=4))
    disc(P, (0, -0.016, 0), 0.035, 0.012, "moonstone", axis=(0, -1, 0), segs=16)
    bail(P, (0, 0, 0.13), "brass")
    return A


# ---------------------------------------------------------------------------
# Relics: runes
# ---------------------------------------------------------------------------

def rune_tablet(name, glow, strokes, moss=False, usage=""):
    A = Asset(name, weight=1.1, usage=usage + " Rune tablet 0.34 x 0.46 m, centred, faces -Y. Emission = glyph.")
    P = A.piece(name)
    rng = random.Random(len(name))
    poly = [(-0.17, -0.23), (0.17, -0.23), (0.17, 0.1)] + [(math.cos(a) * 0.17, 0.1 + math.sin(a) * 0.13)
                                                           for a in [math.pi * i / 10 for i in range(1, 10)]] + [(-0.17, 0.1)]
    P.add("stone_dark", eh.bm_bevel(prism_xz(poly, -0.035, 0.035), 0.012, 1))
    inner = [(x * 0.84, z * 0.86 - 0.005) for x, z in poly]
    P.add("stone", prism_xz(inner, -0.045, -0.035))
    for path, w in strokes:
        pts = catmull([Vector((x, -0.05, z)) for x, z in path], 3)
        P.add(glow, tube(pts, [w] * len(pts), segs=5, flatten=1.6, up=Y))
    for k in range(6):
        a = rng.uniform(0, TAU)
        p = Vector((math.cos(a) * 0.17, rng.uniform(-0.03, 0.03), 0.0 + math.sin(a) * 0.2))
        P.add("stone_dark", blob(tuple(p), rng.uniform(0.015, 0.03), segs=5, rings=4, rng=rng, jitter=0.3))
    if moss:
        for k in range(5):
            P.add("leaf", blob((rng.uniform(-0.15, 0.15), -0.03, rng.uniform(-0.23, -0.15)), 0.03, scale=(1.4, 0.6, 0.8),
                               segs=6, rings=4, rng=rng, jitter=0.2))
    return A


def rune_vine():
    s = [([(0.0, -0.17), (0.0, -0.05), (0.03, 0.05), (-0.02, 0.13), (0.0, 0.2)], 0.012),
         ([(0.0, -0.06), (0.06, -0.03), (0.09, 0.03)], 0.009), ([(0.02, 0.06), (-0.06, 0.08), (-0.08, 0.14)], 0.009),
         ([(-0.0, -0.12), (-0.07, -0.1), (-0.09, -0.04)], 0.008)]
    return rune_tablet("RuneVine", "glow_poison", s, moss=True, usage="Vine rune (grows vines from bulbs).")


def rune_ram():
    def spiral(sx):
        return [(sx * (0.02 + 0.07 * math.sin(t * 0.9)) + sx * 0.02 * t, 0.1 - 0.04 * t + 0.06 * math.cos(t * 1.4))
                for t in [i * 0.45 for i in range(9)]]
    s = [(spiral(1), 0.012), (spiral(-1), 0.012), ([(-0.05, -0.04), (0.0, -0.16), (0.05, -0.04)], 0.011),
         ([(-0.06, -0.06), (0.06, -0.06)], 0.008)]
    return rune_tablet("RuneRam", "glow_fire", s, usage="Ram rune (ground pound breaks rune floors).")


def rune_spider():
    s = [([(0.0, -0.08), (0.0, 0.08)], 0.02)]
    for sx in (-1, 1):
        for k, (a, b) in enumerate(((0.06, 0.16), (0.02, 0.12), (-0.03, 0.02), (-0.06, -0.12))):
            s.append(([(sx * 0.015, a * 0.4), (sx * 0.08, a + 0.02), (sx * 0.12, b)], 0.007))
    s.append(([(0.0, 0.08), (0.0, 0.14)], 0.011))
    return rune_tablet("RuneSpider", "glow_violet", s, usage="Spider rune (wall-jump).")


# ---------------------------------------------------------------------------
# Relics: blocks and vines
# ---------------------------------------------------------------------------

def cracked_block():
    A = Asset("CrackedBlock", weight=1.2, usage="Breakable wall block, exactly 1 x 1 x 1 m (x -0.5..0.5, z 0..1, y -0.5..0.5). "
                                                "Four cracked bricks; emission = embers glowing in the cracks.")
    P = A.piece("CrackedBlock")
    rng = random.Random(21)
    for (x0, x1), (z0, z1) in (((-0.5, 0.05), (0.0, 0.48)), ((0.07, 0.5), (0.0, 0.48)), ((-0.5, -0.12), (0.5, 1.0)),
                               ((-0.1, 0.5), (0.5, 1.0))):
        bm = box((x0 + 0.01, -0.48, z0 + 0.01), (x1 - 0.01, 0.48, z1 - 0.01), bev=0.03)
        ba.jitter_bm(bm, 0.008, rng)
        P.add("crack", bm)
    P.add("stone_dark", box((-0.49, -0.44, 0.02), (0.49, 0.44, 0.98)))
    for path in ([(-0.3, 0.9), (-0.18, 0.66), (-0.26, 0.42), (-0.1, 0.2)], [(0.25, 0.95), (0.3, 0.7), (0.15, 0.55)],
                 [(0.32, 0.3), (0.2, 0.18), (0.36, 0.04)]):
        pts = catmull([Vector((x, -0.495, z)) for x, z in path], 3)
        P.add("glow_fire", tube(pts, [0.012] * len(pts), segs=4, flatten=2.0, up=Y))
    for k in range(6):
        P.add("stone_dark", blob((rng.uniform(-0.45, 0.45), -0.5, rng.uniform(0.0, 0.06)), 0.04, segs=5, rings=4, rng=rng,
                                 jitter=0.3))
    return A


def ram_slab():
    A = Asset("RamSlab", weight=1.2, usage="Ram-rune floor block, exactly 1 x 1 x 1 m (x -0.5..0.5, z 0..1). Iron-bound stone "
                                           "with a glowing ram sigil on the top and the front.")
    P = A.piece("RamSlab")
    P.add("stone_dark", box((-0.49, -0.49, 0.0), (0.49, 0.49, 0.99), bev=0.03))
    for z in (0.12, 0.88):
        P.add("iron", box((-0.5, -0.5, z - 0.05), (0.5, 0.5, z + 0.05), bev=0.01))
    for sx in (-1, 1):
        P.add("iron", box((sx * 0.5 - 0.05, -0.5, 0.0), (sx * 0.5 + 0.05, 0.5, 1.0), bev=0.01))
        for z in (0.12, 0.88):
            P.add("brass", blob((sx * 0.4, -0.51, z), 0.022, scale=(1, 0.6, 1), segs=6, rings=4))

    def horns(face_pt, axis_u, axis_v, normal):
        for sx in (-1, 1):
            pts = [face_pt + axis_u * (sx * (0.04 + 0.12 * math.sin(t * 0.9) + 0.03 * t)) +
                   axis_v * (0.15 - 0.06 * t + 0.08 * math.cos(t * 1.4)) for t in [i * 0.45 for i in range(9)]]
            P.add("glow_fire", tube(catmull(pts, 2), [0.018] * 17, segs=4, flatten=2.0, up=normal))
        tri = [face_pt + axis_u * -0.07 + axis_v * -0.05, face_pt + axis_v * -0.24, face_pt + axis_u * 0.07 + axis_v * -0.05]
        P.add("glow_fire", tube(tri, [0.016] * 3, segs=4, flatten=2.0, up=normal))
    horns(Vector((0, -0.5, 0.55)), X, Z, Y)
    horns(Vector((0, 0.0, 1.0)), X, -Y, Z)
    return A


def vine_bulb():
    A = Asset("VineBulb", weight=1.1, usage="Vine-rune seed bulb ~0.7 m, floor pivot, faces -Y. Emission = rune ring + bulb veins.")
    P = A.piece("VineBulb")
    rng = random.Random(3)
    P.add("bulb", lathe([(0.0, 0.05), (0.18, 0.1), (0.24, 0.25), (0.2, 0.42), (0.1, 0.55), (0.03, 0.62), (0.0, 0.64)],
                        segs=16, rng=rng, jitter=0.03))
    for k in range(7):
        a = TAU * k / 7
        base = Vector((math.cos(a) * 0.15, math.sin(a) * 0.15, 0.05))
        tip = Vector((math.cos(a) * 0.42, math.sin(a) * 0.42, 0.02))
        mid = (base + tip) / 2 + Vector((0, 0, 0.12))
        P.add("leaf", tube(catmull([base, mid, tip], 3), [0.03, 0.05, 0.06, 0.05, 0.04, 0.03, 0.002], segs=5, flatten=3.5,
                           up=Z))
    for k in range(5):
        a = TAU * k / 5 + 0.3
        pts = [Vector((math.cos(a) * r_, math.sin(a) * r_, z)) for r_, z in ((0.19, 0.12), (0.235, 0.27), (0.18, 0.44),
                                                                              (0.08, 0.57))]
        P.add("glow_poison", tube(catmull(pts, 2), [0.008] * 7, segs=4))
    P.add("glow_poison", torus((0, 0, 0.012), 0.48, 0.012, seg=40, rseg=4, flatten=0.3))
    for k in range(8):
        a = TAU * k / 8
        P.add("glow_poison", cbox((math.cos(a) * 0.48, math.sin(a) * 0.48, 0.012), (0.05, 0.015, 0.006)))
    return A


def vine_stalk():
    A = Asset("VineStalk", weight=0.9, usage="Climbing vine segment, tileable: 1 m tall (z 0..1), three stems twisting one "
                                             "full turn so stacked copies line up. Leaves on the front.")
    P = A.piece("VineStalk")
    for s in range(3):
        ph = TAU * s / 3
        pts = [Vector((math.cos(ph + TAU * t) * 0.07, math.sin(ph + TAU * t) * 0.07, t)) for t in [i / 12 for i in range(13)]]
        P.add("vine", tube(pts, [0.03] * 13, segs=6, cap=False))
    for k, z in enumerate((0.2, 0.55, 0.85)):
        sx = 1 if k % 2 else -1
        base = Vector((sx * 0.06, -0.05, z))
        tip = base + Vector((sx * 0.22, -0.05, 0.08))
        P.add("leaf", tube(catmull([base, (base + tip) / 2 + Vector((0, -0.02, 0.04)), tip], 3),
                           [0.01, 0.04, 0.055, 0.05, 0.04, 0.025, 0.002], segs=5, flatten=4.0, up=Y))
    return A


def vine_leaf():
    A = Asset("VineLeaf", weight=1.0, usage="Leaf pad platform 1.5 x 0.7 m, top surface at z = 0.1 (stand on it). Pivot = "
                                            "centre of the pad's underside; stem stub at x = 0.")
    P = A.piece("VineLeaf")
    rows, cols = 7, 13
    grid = []
    for r_ in range(rows):
        v = r_ / (rows - 1) - 0.5
        row = []
        for c in range(cols):
            u = c / (cols - 1) - 0.5
            w = math.cos(u * math.pi) ** 0.6
            row.append((u * 1.5, v * 0.7 * w, 0.06 + 0.04 * (1 - (2 * v) ** 2) - 0.05 * (2 * u) ** 4))
        grid.append(row)
    P.add("leaf", thick_sheet(grid, 0.03, normal_hint=(0, 0, 1)))
    P.add("vine", tube([(0.0, 0.0, 0.06), (0.0, 0.0, 0.11)], [0.02, 0.02], segs=5))
    for k in range(-3, 4):
        P.add("vine", tube([(0.0, 0.0, 0.1), (k * 0.2, (0.2 if k % 2 else -0.2), 0.095 - 0.002 * abs(k))], [0.008, 0.003], segs=4))
    P.add("vine", tube([(-0.7, 0.0, 0.08), (0.7, 0.0, 0.08)], [0.012, 0.012], segs=5))
    P.add("vine", tube([(0.0, 0.0, 0.05), (0.0, 0.0, -0.3)], [0.03, 0.025], segs=6))
    return A


# ---------------------------------------------------------------------------
# Kits and entry points
# ---------------------------------------------------------------------------

def sanctum_assets():
    assets = [build_mutator(), build_blacksmith(), build_tailor(), build_timed_door(), build_curse_shroud()]
    for a in assets:
        a.floor = True
    return assets


def relic_assets():
    assets = [amulet_ember(), amulet_tide(), amulet_bone(), amulet_star(), rune_vine(), rune_ram(), rune_spider(),
              cracked_block(), ram_slab(), vine_bulb(), vine_stalk(), vine_leaf()]
    for a in assets:
        a.floor = a.name in ("CrackedBlock", "RamSlab", "VineBulb")
    return assets


KITS = {"Sanctum": sanctum_assets, "Relics": relic_assets}
HP = dict(K.KIT_HP)
HP.update({"coat": (0.0, 1), "trousers": (0.0, 1), "stripes": (0.0, 1), "shirt": (0.0, 1), "tailcoat": (0.0, 1),
           "velvet": (0.0, 1), "tape": (0.0, 1), "leaf": (0.0, 1), "sand": (0.0, 1), "stone": (0.01, 1),
           "stone_dark": (0.01, 1), "crack": (0.01, 1)})
WEIGHT = dict(K.KIT_WEIGHT)
WEIGHT.update({"skin_pale": 1.3, "skin_ruddy": 1.3, "skin_grey": 1.3, "eye": 1.5})


def run_headless(kit):
    out = dc.ART_ROOT / "Props" / kit
    ba.run_kit(assets_fn=KITS[kit], materials_fn=sanctum_materials, atlas=kit, tex_dir=out / "Textures", fbx_dir=out,
               manifest_path=out / f"{kit.lower()}_manifest.json", prev_dir=dc.OUT_ROOT / kit.lower(),
               generator="Tools/Blender/sanctum_props.py", size=2048, hp_cfg=HP, flat=(), mat_weight=WEIGHT,
               budget=lambda a: 9000 if a.name in ("Mutator", "Blacksmith", "Tailor", "TimedDoor") else 5000,
               emission_colors=dict(K.GLOWS), views=("three_quarter", "front"), cols=4, default_hp=(0.003, 1))


def preview(kit="Sanctum", only=None, x0=0.0, z0=-8.0):
    """Build a kit into the open scene (its own collection), never resetting the file."""
    name = f"0.6 - {kit}"
    old = bpy.data.collections.get(name)
    if old is not None:
        for o in list(old.objects):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data is not None and data.users == 0 and isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    M = materials_cached()
    assets = KITS[kit]()
    if only:
        assets = [a for a in assets if a.name in only]
    ba.realize(assets, M)
    x = x0
    for a in assets:
        root = bpy.data.objects.new("S_" + a.name, None)
        root.empty_display_size = 0.2
        col.objects.link(root)
        lo, hi = ba.bounds_of(a.objs)
        for o in a.objs:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
            o.parent = root
        x += -lo.x + 0.3
        root.location = (x, 0.0, z0)
        x += hi.x + 0.3
    return [a.name for a in assets]


if __name__ == "__main__":
    kit = next((a.split("=", 1)[1] for a in ba.cli_args() if a.startswith("--kit=")), "Sanctum")
    run_headless(kit)
