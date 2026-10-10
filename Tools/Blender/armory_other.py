"""Twenty 'other' weapons (atlas "ArmoryGear"): six shields (Shield mount:
face toward Blender +Z, handle centred at the origin) and fourteen skills.
Throwables are centred on the origin; deployables (totem, sentry, trap,
lantern) stand on z = 0 so the same model can be placed on the floor.

Run headless:  Blender -b --factory-startup -P Tools/Blender/armory_other.py
Live preview:  import armory_other; armory_other.preview()
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
from armory_kit import (TAU, Asset, aim, blob, catmull, cbox, chain, collar, cone, disc, gem, lathe, lerp,  # noqa: E402
                        loft, prism_xz, ring_of, rot, spikes, thick_sheet, torus, tube)

UP = (0, 0, 1)


def handle(P, mat="leather"):
    """Shield strap handle on the back (z < 0)."""
    P.add(mat, tube(catmull([(-0.07, 0, -0.005), (-0.05, 0, -0.04), (0.05, 0, -0.04), (0.07, 0, -0.005)], n=3), 0.01, segs=5))


# ------------------------------------------------------------------ shields


def bell_shield():
    A = Asset("BellShield", weight=1.2, usage="Shield made from a bronze bell mouth; face +Z, clapper boss.")
    P = A.piece("BellShield")
    P.add("bronze", lathe([(0.0, 0.11), (0.06, 0.105), (0.14, 0.08), (0.22, 0.04), (0.28, 0.0), (0.3, -0.01), (0.29, -0.02),
                           (0.25, -0.005), (0.16, 0.03), (0.0, 0.06)], segs=32))
    P.add("dark_iron", torus((0, 0, 0.0), 0.29, 0.012, seg=36, rseg=5))
    P.add("glow_gold", blob((0, 0, 0.115), 0.035, segs=10, rings=7))
    for d in ring_of(8, "z"):
        P.add("brass", blob((d[0] * 0.2, d[1] * 0.2, 0.05), 0.012, segs=6, rings=4))
    handle(P)
    return A


def mirror_moon():
    A = Asset("MirrorMoon", weight=1.2, usage="Round silver shield with a moonstone mirror face and a crescent emblem.")
    P = A.piece("MirrorMoon")
    disc(P, (0, 0, 0.0), 0.28, 0.02, "steel", axis=UP, segs=32)
    disc(P, (0, 0, 0.02), 0.24, 0.006, "moonstone", axis=UP, segs=32)
    P.add("glow_moon", torus((0, 0, 0.022), 0.25, 0.006, seg=36, rseg=4))
    arc = [Vector((0.11 * math.cos(a), 0.11 * math.sin(a), 0.03)) for a in [math.radians(70 + 220 * i / 18) for i in range(19)]]
    P.add("glow_moon", tube(arc, [0.004 + 0.022 * math.sin(math.pi * i / 18) for i in range(19)], segs=6, flatten=0.3,
                            up=(0, 0, 1)))
    handle(P)
    return A


def spiked_shell():
    A = Asset("SpikedShell", weight=1.2, usage="Turtle-shell shield of chitin plates with iron spikes.")
    P = A.piece("SpikedShell")
    P.add("chitin", lathe([(0.0, 0.14), (0.1, 0.12), (0.2, 0.07), (0.27, 0.0), (0.28, -0.02), (0.0, -0.01)], segs=28,
                          scale_xy=(1.0, 1.15)))
    for d in ring_of(6, "z", phase=0.3):
        P.add("shark", blob((d[0] * 0.16, d[1] * 0.18, 0.1), 0.06, scale=(1, 1, 0.35), segs=8, rings=5))
        P.add("iron", cone((d[0] * 0.16, d[1] * 0.18, 0.11), (d[0] * 0.3, d[1] * 0.3, 1), 0.07, 0.016, segs=5))
    P.add("shark", blob((0, 0, 0.14), 0.06, scale=(1, 1, 0.4), segs=8, rings=5))
    P.add("iron", cone((0, 0, 0.15), UP, 0.09, 0.02, segs=6))
    for d in ring_of(12, "z"):
        P.add("iron", cone((d[0] * 0.27, d[1] * 0.31, 0.0), (d[0], d[1], 0.2), 0.05, 0.01, segs=4))
    handle(P)
    return A


def clockface_buckler():
    A = Asset("ClockfaceBuckler", weight=1.2, usage="Buckler made from a clock face: brass rim, numerals, hands, glass.")
    P = A.piece("ClockfaceBuckler")
    disc(P, (0, 0, 0.0), 0.24, 0.018, "brass", axis=UP, segs=32)
    disc(P, (0, 0, 0.018), 0.21, 0.004, "paper", axis=UP, segs=32)
    for k in range(12):
        a = TAU * k / 12
        P.add("dark_iron", cbox((0.18 * math.sin(a), 0.18 * math.cos(a), 0.024), (0.012, 0.028 if k % 3 == 0 else 0.016, 0.004)))
    P.add("blued", cbox((0.0, 0.06, 0.028), (0.012, 0.13, 0.004)))
    P.add("blued", rot(cbox((0.0, 0.045, 0.031), (0.01, 0.1, 0.004)), -1.1, UP))
    P.add("glow_ice", torus((0, 0, 0.026), 0.2, 0.004, seg=36, rseg=3))
    P.add("brass", torus((0, 0, 0.02), 0.215, 0.01, seg=36, rseg=4))
    gem(P, (0, 0, 0.036), 0.012, "brass", axis=UP)
    handle(P)
    return A


def ember_targe():
    A = Asset("EmberTarge", weight=1.2, usage="Obsidian targe with glowing cracks, iron rim and boss.")
    P = A.piece("EmberTarge")
    P.add("obsidian", lathe([(0.0, 0.05), (0.15, 0.035), (0.26, 0.01), (0.27, -0.01), (0.0, -0.01)], segs=30))
    P.add("dark_iron", torus((0, 0, 0.0), 0.265, 0.014, seg=36, rseg=5))
    P.add("dark_iron", lathe([(0.0, 0.1), (0.04, 0.09), (0.06, 0.05), (0.065, 0.04)], segs=16))
    for d in ring_of(10, "z"):
        P.add("iron", blob((d[0] * 0.24, d[1] * 0.24, 0.015), 0.01, segs=6, rings=4))
    handle(P)
    return A


def whalescale_tower():
    A = Asset("WhalescaleTower", weight=1.2, usage="Tall tower shield clad in overlapping whale scales, bone rim.")
    P = A.piece("WhalescaleTower")
    P.add("drift_wood", cbox((0, 0, 0.0), (0.42, 0.86, 0.03), bev=0.02, segs=2))
    for row in range(8):
        for col in range(4 if row % 2 == 0 else 3):
            x = -0.15 + col * 0.1 + (0.05 if row % 2 else 0)
            y = 0.36 - row * 0.1
            P.add("shark", blob((x, y, 0.025), 0.058, scale=(1, 1.05, 0.22), segs=10, rings=6))
    for sgn in (-1, 1):
        P.add("bone", tube([(sgn * 0.215, -0.43, 0.02), (sgn * 0.215, 0.43, 0.02)], 0.014, segs=6))
    for y in (-0.43, 0.43):
        P.add("bone", tube([(-0.215, y, 0.02), (0.215, y, 0.02)], 0.014, segs=6))
    gem(P, (0, 0, 0.06), 0.03, "glow_ice", axis=UP)
    handle(P)
    return A


# ------------------------------------------------------------------ skills


def starfall():
    A = Asset("Starfall", weight=1.1, usage="Brass astrolabe disc set with star gems (calls down falling stars).")
    P = A.piece("Starfall")
    disc(P, (0, 0, 0.0), 0.12, 0.008, "brass", axis=(0, 1, 0))
    P.add("brass", torus((0, 0, 0.0), 0.12, 0.008, normal=(0, 1, 0), seg=30, rseg=4))
    P.add("brass", torus((0, 0, 0.0), 0.08, 0.004, normal=(0.3, 1, 0.2), seg=26, rseg=3))
    for d in ring_of(7, "y", phase=0.4):
        gem(P, (d[0] * 0.095, -0.012, d[2] * 0.095), 0.012, "glow_gold")
    gem(P, (0, -0.014, 0), 0.025, "glow_gold")
    P.add("brass", torus((0, 0, 0.135), 0.015, 0.004, normal=(1, 0, 0), seg=10, rseg=3))
    return A


def thunder_totem():
    A = Asset("ThunderTotem", weight=1.2, usage="Deployable carved totem with copper lightning rods and glowing eyes; stands on z=0.")
    P = A.piece("ThunderTotem")
    for k, (h, w) in enumerate(((0.16, 0.14), (0.15, 0.12), (0.14, 0.13))):
        z = sum(x[0] for x in ((0.16, 0), (0.15, 0), (0.14, 0))[:k])
        P.add("dark_wood", cbox((0, 0, z + h / 2), (w, w * 0.9, h), bev=0.015, segs=2))
        for sgn in (-1, 1):
            P.add("glow_bolt", blob((sgn * 0.03, -w * 0.45, z + h * 0.62), 0.012, scale=(1, 0.5, 1), segs=6, rings=4))
        P.add("bone", cbox((0, -w * 0.45, z + h * 0.3), (0.06, 0.012, 0.015), bev=0.004))
    for sgn in (-1, 0, 1):
        P.add("copper", tube([(sgn * 0.04, 0, 0.45), (sgn * 0.05, 0, 0.62 - abs(sgn) * 0.05)], 0.007, segs=5))
        P.add("glow_bolt", blob((sgn * 0.05, 0, 0.625 - abs(sgn) * 0.05), 0.012, segs=6, rings=4))
    P.add("copper", torus((0, 0, 0.47), 0.05, 0.006, seg=14, rseg=4))
    return A


def gear_sentry():
    A = Asset("GearSentry", weight=1.2, usage="Deployable tripod sentry: brass gear body, small crossbow head; stands on z=0.")
    P = A.piece("GearSentry")
    for d in ring_of(3, "z", phase=0.5):
        P.add("dark_iron", tube([(0, 0, 0.26), (d[0] * 0.18, d[1] * 0.18, 0.0)], 0.01, segs=5))
        P.add("dark_iron", blob((d[0] * 0.18, d[1] * 0.18, 0.005), 0.015, segs=6, rings=4))
    disc(P, (0, 0, 0.3), 0.08, 0.03, "brass", axis=(0, 1, 0))
    for d in ring_of(12, "y"):
        P.add("brass", cbox((d[0] * 0.088, 0, 0.3 + d[2] * 0.088), (0.018, 0.04, 0.018), bev=0.003))
    gem(P, (0, -0.035, 0.3), 0.02, "glow_gold")
    P.add("dark_wood", cbox((0.0, -0.04, 0.39), (0.04, 0.22, 0.04), bev=0.008))
    for s in (1, -1):
        P.add("dark_wood", tube(catmull([(0, -0.15, 0.39), (s * 0.08, -0.13, 0.4), (s * 0.12, -0.09, 0.4)], n=3), 0.007, segs=5))
    P.add("string", tube([(0.12, -0.09, 0.4), (0, -0.04, 0.4), (-0.12, -0.09, 0.4)], 0.002, segs=4))
    P.add("iron", cone((0, -0.15, 0.4), (0, -1, 0), 0.03, 0.008, segs=5))
    return A


def bear_trap():
    A = Asset("BearTrap", weight=1.2, usage="Deployable jaw trap lying open on the floor (z=0).")
    P = A.piece("BearTrap")
    disc(P, (0, 0, 0.012), 0.08, 0.012, "rust", axis=UP)
    P.add("rust", cbox((0, 0, 0.01), (0.36, 0.05, 0.016), bev=0.004))
    for s in (1, -1):
        tilt = 0.9  # jaws sprung open, leaning outward
        ring = [Vector((s * 0.16 * math.sin(a) * math.cos(tilt) + s * 0.01, 0.16 * math.cos(a),
                        0.016 + 0.16 * math.sin(a) * math.sin(tilt))) for a in [i / 14 * math.pi for i in range(15)]]
        P.add("rust", tube(ring, 0.009, segs=5))
        for i in range(1, 14, 2):
            a = i / 14 * math.pi
            base = Vector((s * 0.16 * math.sin(a) * math.cos(tilt) + s * 0.01, 0.16 * math.cos(a), 0.016 + 0.16 * math.sin(a) * math.sin(tilt)))
            P.add("iron", cone(tuple(base), (-s * 0.6, 0, 0.8), 0.04, 0.009, segs=4))
    P.add("glow_red", blob((0, 0, 0.03), 0.014, segs=6, rings=4))
    chain(P, (0.18, 0, 0.01), (0.34, 0.05, 0.01), 7, mat="rust")
    return A


def miasma_jar():
    A = Asset("MiasmaJar", weight=1.1, usage="Glass jar of glowing poison miasma with a clamped lid.")
    P = A.piece("MiasmaJar")
    P.add("green_glass", lathe([(0.0, -0.08), (0.06, -0.075), (0.07, -0.04), (0.07, 0.05), (0.055, 0.07), (0.045, 0.08), (0.0, 0.08)], segs=16))
    P.add("brass", lathe([(0.0, 0.08), (0.05, 0.08), (0.052, 0.1), (0.0, 0.105)], segs=14))
    for sgn in (-1, 1):
        P.add("brass", tube([(sgn * 0.05, 0, 0.095), (sgn * 0.072, 0, 0.06), (sgn * 0.074, 0, 0.0)], 0.005, segs=4))
    P.add("glow_poison", blob((0, 0, -0.005), 0.05, scale=(1, 1, 1.2), segs=10, rings=7))
    P.add("rope", torus((0, 0, 0.05), 0.064, 0.006, seg=16, rseg=4))
    return A


def cluster_bell_bomb():
    A = Asset("ClusterBellBomb", weight=1.1, usage="Four small bronze bells bundled with rope around a lit fuse.")
    P = A.piece("ClusterBellBomb")
    for d in ring_of(4, "y", phase=0.785):
        c = (d[0] * 0.05, d[1] * 0.05, d[2] * 0.05)
        bell = lathe([(0.0, 0.0), (0.02, 0.003), (0.03, 0.03), (0.042, 0.06), (0.04, 0.065), (0.0, 0.05)], segs=14)
        P.add("bronze", aim(bell, tuple(-Vector(d)), tuple(Vector(c) + Vector(d) * 0.06)))
        P.add("glow_gold", blob(tuple(Vector(c) + Vector(d) * 0.0), 0.01, segs=6, rings=4))
    P.add("rope", torus((0, 0, 0), 0.05, 0.008, normal=(0, 1, 0), seg=16, rseg=4))
    P.add("rope", tube(catmull([(0, 0, 0.05), (0.02, 0, 0.1), (0.0, 0, 0.14)], n=3), 0.004, segs=4))
    P.add("glow_fire", blob((0.0, 0, 0.145), 0.012, segs=6, rings=4))
    return A


def lodestone_mine():
    A = Asset("LodestoneMine", weight=1.1, usage="Horseshoe magnet clamped around a dark lodestone with red and blue poles.")
    P = A.piece("LodestoneMine")
    arc = [Vector((0.08 * math.cos(a), 0.0, 0.08 * math.sin(a))) for a in [math.radians(-180 + 180 * i / 14) for i in range(15)]]
    arc = [Vector((p.x, 0, -p.z)) for p in arc]
    P.add("dark_iron", tube(arc, 0.026, segs=8, flatten=0.8, up=(0, 1, 0)))
    P.add("red_cloth", blob((0.08, 0, -0.01), 0.03, scale=(1, 0.9, 0.8), segs=8, rings=5))
    P.add("glow_bolt", blob((-0.08, 0, -0.01), 0.03, scale=(1, 0.9, 0.8), segs=8, rings=5))
    P.add("obsidian", blob((0, 0, 0.02), 0.045, segs=10, rings=7, rng=random.Random(5), jitter=0.15))
    return A


def frost_nova():
    A = Asset("FrostNova", weight=1.1, usage="Cluster of ice crystals growing from a brass base.")
    P = A.piece("FrostNova")
    disc(P, (0, 0, -0.04), 0.05, 0.012, "brass", axis=UP)
    rng = random.Random(7)
    for k in range(7):
        d = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.4, 0.4), 1.0)).normalized() if k else Vector(UP)
        L = rng.uniform(0.1, 0.18) if k else 0.22
        r = rng.uniform(0.018, 0.028)
        P.add("ice", aim(lathe([(0.0, 0.0), (r, 0.02), (r, L * 0.75), (0.0, L)], segs=6), tuple(d), (0, 0, -0.035)))
    P.add("glow_ice", blob((0, 0, 0.0), 0.03, segs=8, rings=5))
    return A


def ember_dash():
    A = Asset("EmberDash", weight=1.1, usage="A burning obsidian feather (dash skill).")
    P = A.piece("EmberDash")
    spine = catmull([(0, 0, -0.12), (0.01, 0, 0.0), (0.03, 0, 0.12), (0.06, 0, 0.2)], n=4)
    P.add("dark_iron", tube(spine, 0.005, segs=5))
    n = len(spine)
    for i in range(2, n - 1):
        p = spine[i]
        t = i / (n - 1)
        L = 0.07 * math.sin(math.pi * t) + 0.02
        for s in (1, -1):
            grid = [[tuple(p), tuple(p + Vector((s * L, 0, -0.02)))], [tuple(p + Vector((0, 0, 0.03))), tuple(p + Vector((s * L, 0, 0.0)))]]
            P.add("obsidian", thick_sheet(grid, 0.004, normal_hint=(0, -1, 0)))
    P.add("glow_fire", blob((0.06, 0, 0.21), 0.018, scale=(1, 0.6, 1.5), segs=8, rings=5))
    return A


def stopwatch():
    A = Asset("Stopwatch", weight=1.1, usage="Brass pocket watch with a chain (stops time).")
    P = A.piece("Stopwatch")
    disc(P, (0, 0, 0), 0.07, 0.018, "brass", axis=(0, 1, 0))
    disc(P, (0, -0.016, 0), 0.06, 0.004, "paper", axis=(0, 1, 0))
    P.add("glow_ice", aim(lathe([(0.0, 0.0), (0.06, 0.0), (0.0, 0.012)], segs=24), (0, -1, 0), (0, -0.02, 0)))
    for k in range(12):
        a = TAU * k / 12
        P.add("dark_iron", cbox((0.05 * math.sin(a), -0.021, 0.05 * math.cos(a)), (0.004, 0.003, 0.01)))
    P.add("blued", cbox((0, -0.024, 0.02), (0.005, 0.003, 0.04)))
    P.add("brass", lathe([(0.008, 0.07), (0.012, 0.075), (0.012, 0.09), (0.0, 0.095)], segs=10))
    P.add("brass", torus((0, 0, 0.105), 0.015, 0.004, normal=(1, 0, 0), seg=10, rseg=3))
    chain(P, (0, 0, 0.12), (0.08, 0.0, 0.2), 6, R=0.008, r=0.0025, mat="brass")
    return A


def rage_vial():
    A = Asset("RageVial", weight=1.1, usage="Vial of glowing red blood with a skull stopper (rage buff).")
    P = A.piece("RageVial")
    P.add("glow_red", lathe([(0.0, -0.09), (0.03, -0.085), (0.035, -0.06), (0.035, 0.03), (0.0, 0.035)], segs=14))
    P.add("lavender_glass", lathe([(0.033, 0.03), (0.035, 0.04), (0.018, 0.06), (0.016, 0.08)], segs=14, cap0=False, cap1=False))
    for z in (-0.05, 0.0):
        P.add("brass", torus((0, 0, z), 0.036, 0.004, seg=14, rseg=3))
    P.add("bone", blob((0, 0, 0.1), 0.028, segs=10, rings=7))
    for sgn in (-1, 1):
        P.add("dark_iron", blob((sgn * 0.01, -0.024, 0.104), 0.006, segs=5, rings=3))
    P.add("leather", torus((0, 0, 0.06), 0.02, 0.004, seg=12, rseg=3))
    return A


def mending_lantern():
    A = Asset("MendingLantern", weight=1.2, usage="Deployable lantern with a green healing flame; stands on z=0.")
    P = A.piece("MendingLantern")
    disc(P, (0, 0, 0.01), 0.07, 0.01, "brass", axis=UP)
    disc(P, (0, 0, 0.23), 0.06, 0.008, "brass", axis=UP)
    for d in ring_of(4, "z", phase=0.785):
        P.add("brass", tube([(d[0] * 0.055, d[1] * 0.055, 0.02), (d[0] * 0.05, d[1] * 0.05, 0.225)], 0.005, segs=4))
    P.add("green_glass", lathe([(0.0, 0.02), (0.045, 0.03), (0.05, 0.12), (0.04, 0.21), (0.0, 0.22)], segs=12))
    P.add("glow_poison", lathe([(0.0, 0.05), (0.02, 0.08), (0.014, 0.13), (0.0, 0.17)], segs=8))
    P.add("brass", lathe([(0.04, 0.24), (0.02, 0.27), (0.0, 0.28)], segs=10))
    P.add("brass", torus((0, 0, 0.3), 0.025, 0.005, normal=(1, 0, 0), seg=12, rseg=3))
    return A


def bouncing_sawdisc():
    A = Asset("BouncingSawdisc", weight=1.1, usage="Circular saw blade with hooked teeth (bouncing throw).")
    P = A.piece("BouncingSawdisc")
    disc(P, (0, 0, 0), 0.11, 0.006, "steel", axis=(0, 1, 0), segs=28)
    disc(P, (0, 0, 0), 0.03, 0.012, "brass", axis=(0, 1, 0))
    for k in range(16):
        a = TAU * k / 16
        tooth = [(0.0, 0.0), (0.03, 0.0), (0.0, 0.03)]
        base = Vector((0.108 * math.cos(a), 0, 0.108 * math.sin(a)))
        tang = Vector((-math.sin(a), 0, math.cos(a)))
        out = Vector((math.cos(a), 0, math.sin(a)))
        pts = [base + tang * 0.012, base + out * 0.03 + tang * 0.01, base - tang * 0.012]
        P.add("steel", prism_xz([(p.x, p.z) for p in pts], -0.005, 0.005))
    gem(P, (0, -0.012, 0), 0.012, "glow_red")
    return A


def abyss_inkwell():
    A = Asset("AbyssInkwell", weight=1.1, usage="Ornate inkwell with a swirling violet vortex (black hole).")
    P = A.piece("AbyssInkwell")
    P.add("ink", lathe([(0.0, -0.06), (0.07, -0.058), (0.075, -0.04), (0.06, 0.02), (0.03, 0.04), (0.032, 0.06), (0.0, 0.06)], segs=16))
    P.add("brass", torus((0, 0, -0.045), 0.074, 0.007, seg=18, rseg=4))
    P.add("brass", torus((0, 0, 0.058), 0.032, 0.006, seg=14, rseg=4))
    spiral = [Vector((0.05 * t * math.cos(a), 0.05 * t * math.sin(a), 0.07 + 0.08 * t)) for t, a in
              [(i / 20, i / 20 * TAU * 2) for i in range(21)]]
    P.add("glow_violet", tube(spiral, 0.006, segs=5))
    P.add("glow_violet", blob((0, 0, 0.065), 0.022, segs=8, rings=5))
    P.add("paper", tube(catmull([(0.03, 0, 0.06), (0.06, 0, 0.14), (0.09, 0, 0.2)], n=3), 0.004, segs=4))
    P.add("purple_cloth", cone((0.09, 0, 0.2), (0.4, 0, 1), 0.08, 0.015, segs=4))
    return A


def other_assets():
    return [bell_shield(), mirror_moon(), spiked_shell(), clockface_buckler(), ember_targe(), whalescale_tower(), starfall(),
            thunder_totem(), gear_sentry(), bear_trap(), miasma_jar(), cluster_bell_bomb(), lodestone_mine(), frost_nova(),
            ember_dash(), stopwatch(), rage_vial(), mending_lantern(), bouncing_sawdisc(), abyss_inkwell()]


def preview(only=None):
    return K.live_preview(other_assets, "Armory - Other", row=0, cols=5, spacing=1.0, only=only, x0=18.0, row_height=1.4)


if __name__ == "__main__":
    K.run_headless(other_assets, "ArmoryGear")
