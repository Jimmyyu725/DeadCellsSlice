"""Twenty ranged weapons (atlas "ArmoryRanged"), Bow-mount convention: grip at
the origin, the weapon seen side-on in the Blender Y-Z plane, firing toward -Y
(bows: limbs along +-Z, string on the +Y side; guns: stock toward +Y, barrel
toward -Y at about z = +0.08).

Run headless:  Blender -b --factory-startup -P Tools/Blender/armory_ranged.py
Live preview:  import armory_ranged; armory_ranged.preview()
"""

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from mathutils import Vector  # noqa: E402

import armory_kit as K  # noqa: E402
from armory_kit import (TAU, Asset, aim, blob, cap, catmull, cbox, chain, collar, cone, disc, gem, lathe,  # noqa: E402
                        lerp, loft, ring_of, rot, spikes, thick_sheet, torus, tube)

Y = (0, 1, 0)
FWD = (0, -1, 0)


def grip_v(P, mat="grip", r=0.018, z0=-0.075, z1=0.06, rake=0.15):
    """Vertical pistol grip around the origin (slightly raked)."""
    g = lathe(K.ridged(z0, z1, r * 0.92, r, 9, end_r=r * 0.95), segs=8)
    P.add(mat, rot(g, rake, (1, 0, 0)))


def barrel(P, y0, y1, r0, r1, z, mat, segs=12):
    P.add(mat, lathe([(r0 * 0.7, 0.0), (r0, 0.0), (r1, y1 - y0), (r1 * 0.7, y1 - y0)], segs=segs, axis=(0, 1, 0),
                     center=(0, y0, z)))


def limb(P, mat, span, bend, base_r, tip_r, center=(0, 0, 0), y_sign=1, segs=6, flatten=0.7):
    c = Vector(center)
    for s in (1, -1):
        pts = [c + Vector((0, y_sign * bend * (t ** 2), s * span * t)) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
        pts = catmull(pts, n=3)
        n = len(pts)
        P.add(mat, tube(pts, [lerp(base_r, tip_r, i / (n - 1)) for i in range(n)], segs=segs, flatten=flatten, up=(1, 0, 0)))
    return c + Vector((0, y_sign * bend, span)), c + Vector((0, y_sign * bend, -span))


def stock(P, mat="dark_wood", y0=-0.36, y1=0.22, z=0.094, h=0.046, w=0.044, butt=True):
    P.add(mat, cbox((0, (y0 + y1) / 2, z), (w, y1 - y0, h), bev=0.009, segs=2))
    if butt:
        b = cbox((0, y1 + 0.06, z - 0.03), (w * 0.9, 0.16, 0.1), bev=0.012, segs=2)
        P.add(mat, rot(b, -0.3, (1, 0, 0), (0, y1, z)))


def string(P, pts, r=0.0024):
    P.add("string", tube([Vector(p) for p in pts], r, segs=4))


# ---------------------------------------------------------------------------


def crescent_longbow():
    A = Asset("CrescentLongbow", weight=1.2, usage="Tall bow of two moonstone crescents; string on +Y.")
    P = A.piece("CrescentLongbow")
    top, bot = limb(P, "moonstone", 0.72, 0.16, 0.026, 0.008, center=(0, 0, 0))
    P.add("grip", lathe(K.ridged(-0.08, 0.08, 0.026, 0.029, 9), segs=8))
    for z in (0.09, -0.09):
        K.collar(P, z, 0.028, 0.016, "steel")
    string(P, [top, (0, 0.2, 0.0), bot])
    gem(P, (0, -0.03, 0.0), 0.02, "glow_moon", axis=FWD)
    for t in (top, bot):
        P.add("glow_moon", blob(tuple(t), 0.016, segs=8, rings=5))
    return A


def triple_repeater():
    A = Asset("TripleRepeater", weight=1.2, usage="Repeating crossbow with a three-bolt magazine on the stock.")
    P = A.piece("TripleRepeater")
    grip_v(P)
    stock(P)
    top, bot = limb(P, "dark_wood", 0.3, -0.05, 0.02, 0.009, center=(0, -0.34, 0.094), y_sign=-1)
    string(P, [top, (0, -0.12, 0.12), bot])
    P.add("ash", cbox((0, -0.13, 0.165), (0.05, 0.3, 0.09), bev=0.008, segs=2))
    for k in range(3):
        y = -0.12 + (k - 1) * 0.0
        z = 0.15 + k * 0.022
        P.add("ash", tube([(0, -0.3, z), (0, 0.0, z)], 0.005, segs=5))
        P.add("iron", cone((0, -0.3, z), FWD, 0.04, 0.009, segs=5))
    P.add("iron", tube(catmull([(0, 0.02, 0.2), (0, 0.08, 0.26), (0, 0.14, 0.24)], n=3), 0.008, segs=5))
    P.add("brass", torus((0, -0.38, 0.094), 0.04, 0.006, normal=(1, 0, 0), seg=14, rseg=4))
    return A


def blunderbuss():
    A = Asset("Blunderbuss", weight=1.2, usage="Flintlock blunderbuss: flared brass bell at -Y, wooden stock.")
    P = A.piece("Blunderbuss")
    grip_v(P, "dark_wood", r=0.02)
    stock(P, "dark_wood", -0.06, 0.18, 0.07, 0.06, 0.05)
    P.add("brass", lathe([(0.022, 0.0), (0.024, 0.2), (0.032, 0.32), (0.06, 0.4), (0.075, 0.42), (0.05, 0.42)], segs=16,
                         axis=FWD, center=(0, 0.02, 0.1)))
    for y in (-0.05, -0.17):
        P.add("iron", torus((0, y, 0.1), 0.027, 0.006, normal=Y, seg=14, rseg=4))
    P.add("dark_iron", cbox((0, 0.06, 0.13), (0.02, 0.05, 0.04), bev=0.005))
    P.add("dark_iron", tube(catmull([(0, 0.08, 0.14), (0, 0.1, 0.18), (0, 0.075, 0.2)], n=3), 0.006, segs=5))
    P.add("dark_iron", tube(catmull([(0, -0.02, 0.05), (0, -0.035, 0.02), (0, -0.025, 0.0)], n=3), 0.004, segs=5))
    P.add("glow_fire", lathe([(0.0, 0.0), (0.045, 0.002), (0.0, 0.006)], segs=12, axis=FWD, center=(0, -0.395, 0.1)))
    return A


def tick_blowpipe():
    A = Asset("TickBlowpipe", weight=1.1, usage="Long chitin blowpipe with a tick-mandible muzzle and feather tufts.")
    P = A.piece("TickBlowpipe")
    P.add("chitin", lathe([(0.014, 0.0), (0.016, 0.3), (0.013, 0.82)], segs=10, axis=FWD, center=(0, 0.3, 0.05)))
    for y in (0.22, 0.0, -0.22, -0.42):
        P.add("brass", torus((0, y, 0.05), 0.017, 0.004, normal=Y, seg=12, rseg=4))
    P.add("grip", lathe(K.ridged(0.0, 0.12, 0.016, 0.018, 8), segs=8, axis=Y, center=(0, -0.06, 0.05)))
    P.add("bone", lathe([(0.012, 0.0), (0.02, 0.02), (0.016, 0.04)], segs=10, axis=Y, center=(0, 0.3, 0.05)))
    for sgn in (-1, 1):
        P.add("chitin", cone((0, -0.52, 0.05 + sgn * 0.01), (0, -1, sgn * 0.5), 0.06, 0.008, segs=4))
    rng = random.Random(4)
    for k in range(3):
        K.ribbon(P, "red_cloth", (0, 0.1 - k * 0.03, 0.04), 0.1, 0.02, rng)
    P.add("glow_poison", blob((0, -0.53, 0.05), 0.009, segs=6, rings=4))
    P.add("dark_wood", cbox((0, 0.02, -0.01), (0.03, 0.04, 0.09), bev=0.008))
    return A


def frostsling():
    A = Asset("Frostsling", weight=1.1, usage="Sling: leather cords hanging from the hand, pouch holding an ice orb.")
    P = A.piece("Frostsling")
    P.add("leather", torus((0, 0, 0.02), 0.022, 0.006, normal=(0, 0, 1), seg=12, rseg=4))
    for sgn in (-1, 1):
        cord = catmull([(0, sgn * 0.01, 0.0), (0, sgn * 0.05, -0.15), (0, sgn * 0.06, -0.3), (0, sgn * 0.04, -0.42)], n=4)
        P.add("rope", tube(cord, 0.004, segs=4))
    grid = [[(x, -0.045 + 0.09 * u, -0.43 - 0.04 * math.sin(math.pi * u)) for u in (0, 0.25, 0.5, 0.75, 1.0)]
            for x in (-0.035, 0.0, 0.035)]
    P.add("leather", thick_sheet(grid, 0.004, normal_hint=(0, 0, 1)))
    gem(P, (0, 0, -0.41), 0.04, "ice", segs=8, h=1.1, axis=(0, 0, 1))
    P.add("glow_ice", blob((0, 0, -0.41), 0.018, segs=8, rings=5))
    P.add("rope", tube([(0, 0.01, 0.0), (0, 0.0, 0.08), (0, -0.02, 0.12)], 0.004, segs=4))
    return A


def moon_chakram():
    A = Asset("MoonChakram", weight=1.2, usage="Returning ring blade (in the Y-Z plane), wrapped grip on the inner edge.")
    P = A.piece("MoonChakram")
    c = Vector((0, -0.17, 0.0))
    P.add("moonstone", torus(tuple(c), 0.17, 0.018, normal=(1, 0, 0), seg=40, rseg=6, flatten=0.35))
    for d in ring_of(12, "x"):
        P.add("steel", cone(tuple(c + Vector(d) * 0.18), d, 0.045, 0.012, segs=4))
    P.add("grip", lathe(K.ridged(-0.06, 0.06, 0.016, 0.018, 7), segs=8))
    P.add("steel", tube([(0, -0.003, 0.065), (0, -0.04, 0.08)], 0.006, segs=5))
    P.add("steel", tube([(0, -0.003, -0.065), (0, -0.04, -0.08)], 0.006, segs=5))
    gem(P, tuple(c + Vector((0, -0.17, 0))), 0.02, "glow_moon", axis=(1, 0, 0))
    return A


def knife_fan():
    A = Asset("KnifeFan", weight=1.1, usage="Five throwing knives held fanned out like cards.")
    P = A.piece("KnifeFan")
    for k in range(5):
        a = math.radians(-40 + 20 * k)
        d = Vector((0, -math.sin(a), math.cos(a)))
        side = Vector((0, math.cos(a), math.sin(a)))
        base = d * 0.03
        P.add("leather", tube([base, base + d * 0.08], 0.008, segs=5))
        rings = []
        for i in range(9):
            t = i / 8
            w = 0.018 * (1 - t) ** 0.7 + 0.002
            p = base + d * (0.08 + 0.17 * t)
            rings.append([p + side * w, p + Vector((0.004, 0, 0)), p - side * w, p - Vector((0.004, 0, 0))])
        P.add("steel", loft(rings, tip1=base + d * 0.27))
        P.add("iron", torus(tuple(base - d * 0.01), 0.008, 0.0025, normal=tuple(side), seg=8, rseg=3))
    P.add("glow_red", blob((0, 0, 0.0), 0.012, segs=6, rings=4))
    return A


def thunderstring_harp():
    A = Asset("ThunderstringHarp", weight=1.2, usage="Copper lyre-bow with five glowing lightning strings.")
    P = A.piece("ThunderstringHarp")
    for s in (1, -1):
        arm = catmull([(0, 0.0, s * 0.05), (0, -0.05, s * 0.2), (0, 0.02, s * 0.34), (0, 0.1, s * 0.4)], n=4)
        P.add("copper", tube(arm, [lerp(0.02, 0.009, i / (len(arm) - 1)) for i in range(len(arm))], segs=6))
        P.add("glow_bolt", blob((0, 0.1, s * 0.4), 0.016, segs=8, rings=5))
    P.add("grip", lathe(K.ridged(-0.06, 0.06, 0.02, 0.022, 7), segs=8))
    P.add("copper", tube([(0, 0.1, -0.4), (0, 0.13, 0.0), (0, 0.1, 0.4)], 0.008, segs=5))
    for k in range(5):
        z = -0.28 + 0.14 * k
        P.add("glow_bolt", tube([(0, 0.02 + 0.03 * abs(z), z), (0, 0.125, z * 0.95)], 0.0022, segs=4))
    return A


def bell_horn():
    A = Asset("BellHorn", weight=1.2, usage="Brass horn with a bell mouth toward -Y and one coil.")
    P = A.piece("BellHorn")
    grip_v(P, "leather")
    P.add("brass", lathe([(0.012, 0.0), (0.016, 0.12), (0.03, 0.22), (0.07, 0.3), (0.12, 0.34), (0.1, 0.345), (0.0, 0.33)],
                         segs=24, axis=FWD, center=(0, -0.08, 0.1)))
    coil = [Vector((0.03 * math.sin(a), 0.05 + 0.07 * math.cos(a), 0.1 + 0.07 * math.sin(a))) for a in
            [i / 16 * TAU for i in range(17)]]
    P.add("brass", tube(coil, 0.01, segs=6))
    P.add("brass", tube([(0, -0.09, 0.1), (0, -0.015, 0.1)], 0.011, segs=6))
    P.add("brass", tube([(0, 0.12, 0.1), (0, 0.2, 0.12), (0, 0.24, 0.14)], 0.008, segs=6))
    P.add("brass", lathe([(0.008, 0.0), (0.016, 0.02), (0.012, 0.03)], segs=10, axis=Y, center=(0, 0.24, 0.14)))
    P.add("glow_gold", lathe([(0.0, 0.0), (0.09, 0.0), (0.0, 0.004)], segs=20, axis=FWD, center=(0, -0.415, 0.1)))
    P.add("red_cloth", thick_sheet([[(0, -0.12, 0.092), (0, -0.22, 0.096)], [(0, -0.12, -0.03), (0, -0.22, -0.05)]], 0.003,
                                   normal_hint=(1, 0, 0)))
    return A


def ink_squirter():
    A = Asset("InkSquirter", weight=1.2, usage="Squid-shaped pump gun: glassy ink mantle, tentacles trailing back, nozzle forward.")
    P = A.piece("InkSquirter")
    grip_v(P, "dark_wood")
    P.add("ink", lathe([(0.0, -0.02), (0.05, 0.02), (0.065, 0.12), (0.055, 0.22), (0.02, 0.27), (0.0, 0.28)], segs=14,
                       axis=FWD, center=(0, 0.06, 0.11)))
    for d in ring_of(6, "x"):
        start = Vector((0, 0.07, 0.11)) + Vector(d) * 0.04
        pts = catmull([start, start + Vector((0, 0.1, 0)) + Vector(d) * 0.03, start + Vector((0, 0.2, -0.04)) + Vector(d) * 0.02], n=3)
        P.add("ink", tube(pts, [0.012, 0.01, 0.008, 0.006, 0.005, 0.004, 0.003], segs=5))
    P.add("brass", lathe([(0.016, 0.0), (0.012, 0.08), (0.008, 0.1)], segs=10, axis=FWD, center=(0, -0.21, 0.11)))
    for sgn in (-1, 1):
        P.add("glow_violet", blob((sgn * 0.05, -0.08, 0.14), 0.012, scale=(0.5, 1, 1), segs=6, rings=4))
    P.add("brass", tube([(0, 0.0, 0.06), (0, -0.05, 0.02)], 0.006, segs=5))
    return A


def bone_flute():
    A = Asset("BoneFlute", weight=1.1, usage="Long bone flute with finger holes and a small skull at the far end.")
    P = A.piece("BoneFlute")
    P.add("bone", lathe([(0.016, 0.0), (0.02, 0.04), (0.017, 0.2), (0.019, 0.55), (0.024, 0.6)], segs=10, axis=FWD,
                        center=(0, 0.2, 0.04)))
    for k in range(6):
        P.add("dark_iron", blob((0.016, 0.1 - k * 0.06, 0.05), 0.006, scale=(0.4, 1, 1), segs=6, rings=4))
    P.add("bone", blob((0, -0.43, 0.04), 0.045, segs=10, rings=7))
    for sgn in (-1, 1):
        P.add("glow_violet", blob((sgn * 0.02, -0.46, 0.05), 0.01, segs=6, rings=4))
    P.add("purple_cloth", lathe(K.ridged(0.0, 0.1, 0.02, 0.022, 6), segs=8, axis=Y, center=(0, -0.05, 0.04)))
    rng = random.Random(8)
    K.ribbon(P, "purple_cloth", (0, 0.18, 0.03), 0.18, 0.03, rng)
    return A


def stardust_wand():
    A = Asset("StardustWand", weight=1.1, usage="Wand pointing -Y with a five-point star gem at the tip.")
    P = A.piece("StardustWand")
    P.add("dark_wood", lathe([(0.016, 0.0), (0.014, 0.1), (0.008, 0.4)], segs=8, axis=FWD, center=(0, 0.08, 0.02)))
    P.add("grip", lathe(K.ridged(0.0, 0.12, 0.016, 0.018, 7), segs=8, axis=FWD, center=(0, 0.08, 0.02)))
    star = []
    for k in range(10):
        a = TAU * k / 10 + math.pi / 2
        r = 0.07 if k % 2 == 0 else 0.03
        star.append((r * math.cos(a), r * math.sin(a)))
    pts = [Vector((0, -0.38 + x, 0.04 + y)) for x, y in star]
    front = [Vector((0.012, p.y, p.z)) for p in pts]
    back = [Vector((-0.012, p.y, p.z)) for p in pts]
    P.add("glow_gold", loft([front, back], cap0=True, cap1=True))
    P.add("brass", torus((0, -0.31, 0.02), 0.013, 0.004, normal=Y, seg=12, rseg=4))
    for k in range(4):
        a = TAU * k / 4
        P.add("glow_gold", blob((0, -0.3 + 0.08 * math.cos(a), 0.04 + 0.08 * math.sin(a)), 0.006, segs=5, rings=3))
    return A


def harpoon_gun():
    A = Asset("HarpoonGun", weight=1.2, usage="Launcher tube with a loaded barbed harpoon and a rope drum underneath.")
    P = A.piece("HarpoonGun")
    grip_v(P)
    barrel(P, -0.3, 0.2, 0.034, 0.03, 0.1, "dark_iron")
    for y in (-0.25, -0.05, 0.15):
        P.add("brass", torus((0, y, 0.1), 0.037, 0.006, normal=Y, seg=16, rseg=4))
    P.add("ash", tube([(0, -0.3, 0.1), (0, -0.5, 0.1)], 0.01, segs=6))
    P.add("steel", cone((0, -0.5, 0.1), FWD, 0.09, 0.022, segs=6))
    for sgn in (-1, 1):
        P.add("steel", cone((0, -0.53, 0.1 + sgn * 0.015), (0, 0.6, sgn * 1), 0.05, 0.006, segs=4))
    P.add("dark_wood", aim(lathe([(0.0, -0.03), (0.05, -0.03), (0.05, 0.03), (0.0, 0.03)], segs=16), (1, 0, 0), (0, -0.14, 0.01)))
    P.add("rope", torus((0, -0.14, 0.01), 0.045, 0.012, normal=(1, 0, 0), seg=18, rseg=5))
    P.add("rope", tube([(0, -0.14, 0.055), (0, -0.3, 0.09)], 0.004, segs=4))
    stock(P, "dark_wood", 0.1, 0.25, 0.08, 0.05, 0.05)
    return A


def steam_nailer():
    A = Asset("SteamNailer", weight=1.2, usage="Steam nail gun: brass tank on top, nail magazine, pressure gauge.")
    P = A.piece("SteamNailer")
    grip_v(P, "dark_wood")
    P.add("dark_iron", cbox((0, -0.08, 0.08), (0.05, 0.3, 0.06), bev=0.012, segs=2))
    barrel(P, -0.32, -0.2, 0.014, 0.014, 0.085, "steel")
    P.add("brass", lathe([(0.0, 0.0), (0.035, 0.005), (0.04, 0.03), (0.04, 0.2), (0.035, 0.225), (0.0, 0.23)], segs=14,
                         axis=Y, center=(0, -0.15, 0.15)))
    disc(P, (0.035, 0.0, 0.15), 0.025, 0.006, "brass", axis=(1, 0, 0))
    P.add("glow_gold", aim(lathe([(0.0, 0.0), (0.02, 0.0), (0.0, 0.003)], segs=14), (1, 0, 0), (0.042, 0.0, 0.15)))
    P.add("steel", cbox((0, -0.12, 0.02), (0.03, 0.04, 0.09), bev=0.006))
    for k in range(5):
        P.add("iron", tube([(0, -0.13 + 0.005 * k, 0.0 - k * 0.012), (0, -0.11 + 0.005 * k, 0.0 - k * 0.012)], 0.003, segs=4))
    P.add("brass", tube(catmull([(0, 0.0, 0.18), (0, 0.06, 0.22), (0, 0.1, 0.16)], n=3), 0.006, segs=5))
    return A


def ember_mortar():
    A = Asset("EmberMortar", weight=1.2, usage="Short fat bronze hand cannon, embers glowing in the muzzle.")
    P = A.piece("EmberMortar")
    grip_v(P, "dark_wood", r=0.021)
    P.add("bronze", lathe([(0.04, 0.0), (0.055, 0.02), (0.05, 0.1), (0.06, 0.22), (0.075, 0.26), (0.065, 0.27)], segs=18,
                          axis=FWD, center=(0, 0.05, 0.12)))
    P.add("bronze", blob((0, 0.07, 0.12), 0.05, segs=12, rings=8))
    for y in (-0.05, -0.15):
        P.add("iron", torus((0, y, 0.12), 0.058, 0.008, normal=Y, seg=18, rseg=4))
    P.add("obsidian", lathe([(0.0, 0.0), (0.06, 0.0), (0.0, 0.01)], segs=16, axis=FWD, center=(0, -0.21, 0.12)))
    P.add("dark_wood", cbox((0, 0.06, 0.06), (0.06, 0.16, 0.05), bev=0.01))
    P.add("rope", tube(catmull([(0, 0.1, 0.17), (0, 0.14, 0.22), (0, 0.12, 0.27)], n=3), 0.004, segs=4))
    P.add("glow_fire", blob((0, 0.12, 0.275), 0.01, segs=6, rings=4))
    return A


def bubble_gun():
    A = Asset("BubbleGun", weight=1.2, usage="Glass bubble tank, a hoop wand at the front, brass trigger body.")
    P = A.piece("BubbleGun")
    grip_v(P, "brass", r=0.017)
    P.add("brass", cbox((0, -0.04, 0.07), (0.04, 0.18, 0.045), bev=0.012, segs=2))
    P.add("ice", blob((0, 0.02, 0.15), 0.06, segs=14, rings=10))
    P.add("brass", torus((0, 0.02, 0.1), 0.04, 0.007, seg=16, rseg=4))
    rng = random.Random(6)
    for _ in range(5):
        P.add("glow_ice", blob((rng.uniform(-0.02, 0.02), 0.02 + rng.uniform(-0.03, 0.03), 0.15 + rng.uniform(-0.03, 0.03)),
                               rng.uniform(0.006, 0.012), segs=6, rings=4))
    P.add("brass", tube([(0, -0.13, 0.07), (0, -0.2, 0.07)], 0.008, segs=6))
    P.add("brass", torus((0, -0.26, 0.07), 0.06, 0.007, normal=Y, seg=20, rseg=4))
    P.add("glow_ice", torus((0, -0.26, 0.07), 0.052, 0.003, normal=Y, seg=20, rseg=3))
    return A


def chrono_crossbow():
    A = Asset("ChronoCrossbow", weight=1.2, usage="Crossbow with spring-coil prod and a clock dial on the stock.")
    P = A.piece("ChronoCrossbow")
    grip_v(P)
    stock(P, "blued")
    for s in (1, -1):
        coil = [Vector((0.02 * math.cos(a), -0.34 - 0.01 * math.sin(a * 0.5), 0.094 + s * (0.03 + 0.26 * a / (TAU * 3))))
                for a in [i / 30 * TAU * 3 for i in range(31)]]
        P.add("steel", tube(coil, 0.006, segs=5))
    tip_t, tip_b = (0, -0.33, 0.39), (0, -0.33, -0.2)
    string(P, [tip_t, (0, -0.1, 0.12), tip_b])
    disc(P, (0.026, -0.02, 0.094), 0.045, 0.004, "brass", axis=(1, 0, 0))
    P.add("paper", aim(lathe([(0.0, 0.0), (0.038, 0.0), (0.0, 0.001)], segs=20), (1, 0, 0), (0.031, -0.02, 0.094)))
    P.add("blued", cbox((0.034, -0.02, 0.11), (0.003, 0.004, 0.03)))
    P.add("glow_ice", blob((0, -0.34, 0.094), 0.014, segs=6, rings=4))
    P.add("ash", tube([(0, -0.4, 0.125), (0, -0.1, 0.125)], 0.005, segs=5))
    P.add("glow_ice", cone((0, -0.4, 0.125), FWD, 0.04, 0.01, segs=5))
    return A


def gravel_slingshot():
    A = Asset("GravelSlingshot", weight=1.1, usage="Forked wooden slingshot with rubber band and a stone in the pouch.")
    P = A.piece("GravelSlingshot")
    P.add("drift_wood", lathe([(0.016, -0.1), (0.018, 0.05), (0.02, 0.08)], segs=8))
    P.add("grip", lathe(K.ridged(-0.09, 0.04, 0.018, 0.02, 7), segs=8))
    tips = []
    for s in (1, -1):
        arm = catmull([(0, 0, 0.08), (0, s * 0.05, 0.14), (0, s * 0.07, 0.22)], n=3)
        P.add("drift_wood", tube(arm, [0.016, 0.014, 0.013, 0.012, 0.011, 0.011, 0.01], segs=6))
        tips.append(arm[-1])
    for t in tips:
        P.add("leather", torus(tuple(t), 0.012, 0.004, seg=10, rseg=3))
    P.add("eel", tube([tips[0], (0, 0.09, 0.18), tips[1]], 0.004, segs=4))
    P.add("leather", blob((0, 0.09, 0.18), 0.018, scale=(1, 0.6, 1), segs=8, rings=5))
    P.add("iron", blob((0, 0.085, 0.18), 0.014, segs=8, rings=5, rng=random.Random(3), jitter=0.2))
    return A


def lantern_beam():
    A = Asset("LanternBeam", weight=1.2, usage="Lantern on a short pole with a focusing lens toward -Y.")
    P = A.piece("LanternBeam")
    P.add("dark_wood", lathe([(0.016, -0.08), (0.016, 0.12)], segs=8))
    P.add("grip", lathe(K.ridged(-0.07, 0.06, 0.017, 0.019, 7), segs=8))
    P.add("brass", cbox((0, 0, 0.16), (0.1, 0.1, 0.012), bev=0.003))
    P.add("brass", cbox((0, 0, 0.32), (0.1, 0.1, 0.012), bev=0.003))
    for x in (-0.045, 0.045):
        for y in (-0.045, 0.045):
            P.add("brass", tube([(x, y, 0.16), (x, y, 0.32)], 0.006, segs=5))
    P.add("lavender_glass", cbox((0, 0, 0.24), (0.08, 0.08, 0.15), bev=0.01))
    P.add("glow_gold", blob((0, 0, 0.24), 0.03, scale=(1, 1, 1.4), segs=8, rings=6))
    P.add("brass", lathe([(0.03, 0.0), (0.045, 0.03), (0.05, 0.06)], segs=16, axis=FWD, center=(0, -0.05, 0.24), cap0=False, cap1=False))
    P.add("glow_gold", lathe([(0.0, 0.0), (0.045, 0.0), (0.0, 0.008)], segs=16, axis=FWD, center=(0, -0.11, 0.24)))
    P.add("brass", torus((0, 0, 0.36), 0.03, 0.006, normal=(1, 0, 0), seg=12, rseg=4))
    return A


def sextant_sniper():
    A = Asset("SextantSniper", weight=1.2, usage="Long rifle with a brass sextant arc mounted on top.")
    P = A.piece("SextantSniper")
    grip_v(P, "dark_wood")
    stock(P, "dark_wood", -0.2, 0.16, 0.075, 0.05, 0.045)
    barrel(P, -0.75, -0.18, 0.012, 0.014, 0.09, "blued")
    for y in (-0.7, -0.45, -0.25):
        P.add("brass", torus((0, y, 0.09), 0.016, 0.004, normal=Y, seg=12, rseg=3))
    arc = [Vector((0, -0.05 + 0.13 * math.cos(a), 0.12 + 0.13 * math.sin(a))) for a in
           [math.radians(30 + 120 * i / 12) for i in range(13)]]
    P.add("brass", tube(arc, 0.006, segs=5))
    P.add("brass", tube([(0, -0.05, 0.12), arc[0]], 0.004, segs=4))
    P.add("brass", tube([(0, -0.05, 0.12), arc[-1]], 0.004, segs=4))
    P.add("brass", tube([(0, -0.05, 0.12), arc[6]], 0.005, segs=4))
    P.add("glow_ice", cbox((0, -0.05, 0.25), (0.02, 0.012, 0.03)))
    barrel(P, -0.1, 0.06, 0.018, 0.018, 0.16, "brass")
    P.add("glow_ice", lathe([(0.0, 0.0), (0.016, 0.0), (0.0, 0.003)], segs=12, axis=FWD, center=(0, -0.102, 0.16)))
    P.add("dark_iron", tube(catmull([(0, 0.0, 0.05), (0, -0.02, 0.02), (0, -0.01, 0.0)], n=3), 0.004, segs=4))
    return A


def ranged_assets():
    return [crescent_longbow(), triple_repeater(), blunderbuss(), tick_blowpipe(), frostsling(), moon_chakram(), knife_fan(),
            thunderstring_harp(), bell_horn(), ink_squirter(), bone_flute(), stardust_wand(), harpoon_gun(), steam_nailer(),
            ember_mortar(), bubble_gun(), chrono_crossbow(), gravel_slingshot(), lantern_beam(), sextant_sniper()]


def preview(only=None):
    names = K.live_preview(ranged_assets, "Armory - Ranged", row=0, cols=5, spacing=1.6, only=only, rot_z=math.pi / 2,
                           x0=9.0)
    return names


if __name__ == "__main__":
    K.run_headless(ranged_assets, "ArmoryRanged")
