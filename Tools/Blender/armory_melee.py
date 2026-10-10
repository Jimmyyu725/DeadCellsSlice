"""Twenty melee weapons (atlas "ArmoryMelee").  Grip centre at the origin, blade
along +Z, edge / reach toward +X, flats facing +-Y (the camera).

Run headless:  Blender -b --factory-startup -P Tools/Blender/armory_melee.py
Live preview (in an open Blender):  import armory_melee; armory_melee.preview()
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
from armory_kit import (TAU, Asset, aim, blob, blade, cap, catmull, cbox, chain, collar, cone, disc, edge_blade,  # noqa: E402
                        gem, grip, lathe, lerp, prism_xz, ribbon, ring_of, rot, shaft, spikes, torus, tube, xform)


def ember_fang():
    A = Asset("EmberFang", weight=1.2, usage="The time god's broken tooth as a dagger: obsidian fang with glowing cracks.")
    P = A.piece("EmberFang")
    path = catmull([(0.0, 0, 0.07), (0.015, 0, 0.25), (0.045, 0, 0.43), (0.095, 0, 0.6), (0.16, 0, 0.72)], n=4)
    edge_blade(P, "obsidian", path, lambda t: 0.085 * (1 - t) ** 0.8 + 0.006, lambda t: 0.026 * (1 - t) + 0.003, (-1, 0, 0))
    for sgn in (-1, 1):
        P.add("obsidian", cone((sgn * 0.02, 0, 0.075), (sgn * 0.4, 0, -1), 0.07, 0.014, segs=6))
    P.add("brass", torus((0.004, 0, 0.07), 0.034, 0.008, seg=14, rseg=5))
    grip(P, -0.1, 0.055, 0.017, "bone")
    P.add("brass", lathe([(0.0, -0.15), (0.014, -0.145), (0.02, -0.125), (0.017, -0.105)], segs=10))
    K.gem(P, (0, 0, -0.152), 0.014, "glow_fire", axis=(0, 0, 1))
    return A


def moonsickle():
    A = Asset("Moonsickle", weight=1.1, usage="One of the Moonsickle Twins (dual wield): moon-shard crescent curling forward.")
    P = A.piece("Moonsickle")
    shaft(P, -0.11, 0.09, 0.016, 0.017, "dark_wood")
    grip(P, -0.09, 0.05, 0.018, "silk")
    collar(P, 0.085, 0.02, mat="steel")
    path = catmull([(0.0, 0, 0.09), (0.04, 0, 0.28), (0.16, 0, 0.42), (0.32, 0, 0.43), (0.44, 0, 0.32), (0.47, 0, 0.18)], n=4)
    edge_blade(P, "moonstone", path, lambda t: 0.014 + 0.09 * math.sin(math.pi * min(1.0, t * 1.1)) * (1 - t * 0.6),
               lambda t: 0.009 * (1 - t) + 0.002, (1, 0, -1))
    P.add("steel", lathe([(0.0, -0.135), (0.016, -0.13), (0.02, -0.115), (0.016, -0.105)], segs=10))
    gem(P, (0.0, 0, 0.115), 0.012, "glow_moon")
    return A


def leviathan_rib():
    A = Asset("LeviathanRib", weight=1.4, usage="Greatsword cut from a petrified leviathan rib, barnacled, two-handed grip.")
    P = A.piece("LeviathanRib")
    grip(P, -0.32, 0.12, 0.024, "rope")
    cap(P, -0.33, 0.03, mat="bone")
    path = catmull([(0.0, 0, 0.16), (0.03, 0, 0.55), (0.08, 0, 0.95), (0.16, 0, 1.3), (0.24, 0, 1.52)], n=5)
    edge_blade(P, "bone", path, lambda t: 0.13 * (1 - t) ** 0.6 + 0.02, lambda t: 0.03 * (1 - t) + 0.006, (1, 0, 0), 0.06)
    # Vertebra crossguard with spurs.
    P.add("bone", blob((0.0, 0, 0.135), 0.06, scale=(1.6, 0.8, 0.7), segs=12, rings=8))
    for sgn in (-1, 1):
        P.add("bone", cone((sgn * 0.08, 0, 0.14), (sgn, 0, 0.6), 0.09, 0.022, segs=6))
    rng = random.Random(3)
    for _ in range(9):
        t = rng.uniform(0.15, 0.85)
        p = path[int(t * (len(path) - 1))]
        P.add("coral", blob((p.x + rng.uniform(0.0, 0.05), rng.choice((-1, 1)) * 0.024, p.z), rng.uniform(0.012, 0.022),
                            scale=(1, 0.6, 1), segs=8, rings=5))
    return A


def pendulum_axe():
    A = Asset("PendulumAxe", weight=1.3, usage="War axe whose head is a clock pendulum disc with a gear hub; spike toward -X.")
    P = A.piece("PendulumAxe")
    shaft(P, -0.4, 0.95, 0.021, 0.019, "dark_wood")
    grip(P, -0.16, 0.14, 0.023)
    cap(P, -0.41, 0.026)
    P.add("brass", cbox((0, 0, 0.86), (0.05, 0.05, 0.18), bev=0.008))
    disc(P, (0.17, 0, 0.88), 0.2, 0.008, "steel")
    disc(P, (0.17, 0, 0.88), 0.07, 0.016, "brass")
    for d in ring_of(10, "y"):
        P.add("brass", cbox((0.17 + d[0] * 0.075, 0, 0.88 + d[2] * 0.075), (0.02, 0.03, 0.02), bev=0.003))
    P.add("glow_gold", torus((0.17, 0, 0.88), 0.15, 0.006, normal=(0, 1, 0), seg=28, rseg=4))
    gem(P, (0.17, 0, 0.88), 0.022, "glow_gold")
    P.add("iron", cone((-0.02, 0, 0.88), (-1, 0, 0.15), 0.18, 0.03, segs=6))
    P.add("brass", lathe([(0.019, 0.95), (0.026, 0.97), (0.012, 1.02), (0.0, 1.05)], segs=10))
    return A


def lavender_bottle():
    A = Asset("LavenderBottle", weight=1.2, usage="Club with a bottle of boiling lavender wine lashed to the head.")
    P = A.piece("LavenderBottle")
    shaft(P, -0.17, 0.38, 0.02, 0.026, "dark_wood")
    grip(P, -0.15, 0.08, 0.022, "leather")
    cap(P, -0.18, 0.025)
    P.add("lavender_glass", lathe([(0.0, 0.36), (0.07, 0.37), (0.088, 0.42), (0.09, 0.58), (0.075, 0.64), (0.032, 0.68),
                                   (0.026, 0.76), (0.03, 0.78), (0.0, 0.785)], segs=16))
    P.add("dark_wood", lathe([(0.0, 0.78), (0.026, 0.78), (0.024, 0.82), (0.0, 0.825)], segs=10))
    for z in (0.43, 0.5, 0.57):
        P.add("rope", torus((0, 0, z), 0.091, 0.006, seg=18, rseg=4))
    rng = random.Random(5)
    ribbon(P, "purple_cloth", (0.03, 0.05, 0.7), 0.22, 0.05, rng)
    for k in range(5):
        a = TAU * k / 5
        P.add("glow_violet", blob((0.05 * math.cos(a), 0.05 * math.sin(a), 0.6 + 0.03 * k), 0.012, segs=6, rings=4))
    return A


def drowned_anchor():
    A = Asset("DrownedAnchor", weight=1.3, usage="Rusted ship anchor held by the shank; flukes at the top, chain and kelp.")
    P = A.piece("DrownedAnchor")
    shaft(P, -0.18, 0.95, 0.03, 0.026, "rust", segs=8)
    grip(P, -0.12, 0.12, 0.033, "rope")
    P.add("rust", torus((0, 0, -0.24), 0.06, 0.014, normal=(0, 1, 0), seg=18, rseg=6))
    P.add("rust", tube([(-0.24, 0, 0.82), (0.24, 0, 0.82)], 0.016, segs=6))
    for sgn in (-1, 1):
        P.add("rust", blob((sgn * 0.25, 0, 0.82), 0.024, segs=8, rings=6))
    arm = catmull([(0.0, 0, 1.0), (0.12, 0, 0.98), (0.22, 0, 1.06), (0.28, 0, 1.18)], n=4)
    for sgn in (-1, 1):
        pts = [Vector((sgn * p.x, 0, p.z)) for p in arm]
        P.add("rust", tube(pts, [0.03, 0.028, 0.024, 0.02] + [0.02] * (len(pts) - 4), segs=7))
        tip = pts[-1]
        fluke = [(0.0, 0.0), (sgn * 0.08, -0.03), (sgn * 0.02, 0.12), (sgn * -0.05, 0.02)]
        P.add("rust", prism_xz([(tip.x + x, tip.z + z) for x, z in fluke], -0.012, 0.012))
    P.add("rust", blob((0, 0, 1.0), 0.04, segs=10, rings=7))
    chain(P, (0.0, 0.04, -0.24), (0.1, 0.04, 0.55), 12, sag=-0.08, mat="iron")
    rng = random.Random(9)
    for x in (-0.15, 0.1):
        ribbon(P, "kelp", (x, 0.02, 0.86), 0.3, 0.04, rng)
    return A


def moonsilk_whip():
    A = Asset("MoonsilkWhip", weight=1.2, usage="Chitin handle and a long stiffened moon-silk lash ending in a moonstone weight.")
    P = A.piece("MoonsilkWhip")
    shaft(P, -0.13, 0.17, 0.018, 0.02, "chitin")
    grip(P, -0.1, 0.1, 0.02, "silk")
    for sgn in (-1, 1):
        P.add("chitin", cone((sgn * 0.012, 0, -0.13), (sgn * 0.5, 0, -1), 0.07, 0.012, segs=5))
    lash = catmull([(0, 0, 0.17), (0.05, 0, 0.45), (0.2, 0, 0.75), (0.45, 0, 0.92), (0.75, 0, 0.9), (0.95, 0, 0.75)], n=6)
    n = len(lash)
    P.add("silk", tube(lash, [lerp(0.012, 0.004, i / (n - 1)) for i in range(n)], segs=6))
    P.add("glow_moon", tube([p + Vector((0, 0.0, 0.0)) for p in lash[::2]], 0.0025, segs=4))
    P.add("moonstone", blob(tuple(lash[-1]), 0.03, scale=(1, 0.8, 1.2), segs=10, rings=7))
    return A


def gearsaw():
    A = Asset("Gearsaw", weight=1.3, usage="Clockwork saw: steel bar with gear teeth, brass motor housing with a glowing window.")
    P = A.piece("Gearsaw")
    grip(P, -0.14, 0.06, 0.02, "leather")
    cap(P, -0.15, 0.022)
    P.add("brass", cbox((0.01, 0, 0.14), (0.13, 0.07, 0.15), bev=0.02, segs=2))
    disc(P, (0.03, 0.0, 0.14), 0.045, 0.04, "brass")
    for d in ring_of(12, "y"):
        P.add("brass", cbox((0.03 + d[0] * 0.05, 0, 0.14 + d[2] * 0.05), (0.014, 0.08, 0.014), bev=0.002))
    gem(P, (0.03, 0, 0.14), 0.02, "glow_gold")
    P.add("brass", tube([(-0.05, 0, 0.18), (-0.09, 0, 0.24), (-0.09, 0, 0.3)], 0.012, segs=6))
    bar = [(-0.035, 0.21), (0.065, 0.21), (0.065, 0.78), (0.05, 0.83), (0.015, 0.85), (-0.02, 0.83), (-0.035, 0.78)]
    P.add("steel", prism_xz(bar, -0.006, 0.006))
    for k in range(18):
        z = 0.24 + k * 0.031
        for x, s in ((0.065, 1), (-0.035, -1)):
            P.add("dark_iron", cone((x, 0, z), (s, 0, 0.5), 0.022, 0.008, segs=4))
    for z in (0.35, 0.55, 0.72):
        P.add("brass", blob((0.015, 0.006, z), 0.007, scale=(1, 0.5, 1), segs=6, rings=4))
    return A


def candelabra_trident():
    A = Asset("CandelabraTrident", weight=1.3, usage="Brass trident whose three prongs end in lit candles.")
    P = A.piece("CandelabraTrident")
    shaft(P, -0.55, 1.15, 0.019, 0.017, "brass")
    grip(P, -0.14, 0.14, 0.021, "red_cloth")
    cap(P, -0.56, 0.024, mat="brass")
    P.add("brass", lathe([(0.017, 1.1), (0.04, 1.14), (0.03, 1.17), (0.017, 1.18)], segs=12))
    prongs = [[(0, 0, 1.15), (0, 0, 1.45)],
              [(0.01, 0, 1.16), (0.12, 0, 1.2), (0.17, 0, 1.3), (0.17, 0, 1.38)],
              [(-0.01, 0, 1.16), (-0.12, 0, 1.2), (-0.17, 0, 1.3), (-0.17, 0, 1.38)]]
    for pr in prongs:
        pts = catmull(pr, n=3) if len(pr) > 2 else [Vector(p) for p in pr]
        P.add("brass", tube(pts, 0.011, segs=6))
        top = Vector(pr[-1])
        P.add("brass", lathe([(0.0, 0.0), (0.03, 0.005), (0.032, 0.015), (0.02, 0.018)], segs=12, center=tuple(top)))
        P.add("wax", lathe([(0.0, 0.015), (0.016, 0.015), (0.016, 0.09), (0.012, 0.1), (0.0, 0.1)], segs=10, center=tuple(top)))
        P.add("glow_fire", lathe([(0.0, 0.1), (0.012, 0.115), (0.009, 0.14), (0.0, 0.165)], segs=8, center=tuple(top)))
    return A


def clockhand_lance():
    A = Asset("ClockhandLance", weight=1.3, usage="A giant clock hand: blued steel spade tip with an open ring, gold trims.")
    P = A.piece("ClockhandLance")
    shaft(P, -0.5, 0.95, 0.02, 0.016, "blued")
    grip(P, -0.14, 0.14, 0.022, "leather")
    disc(P, (0, 0, -0.52), 0.05, 0.012, "brass")
    for d in ring_of(8, "y"):
        P.add("brass", cbox((d[0] * 0.055, 0, -0.52 + d[2] * 0.055), (0.016, 0.022, 0.016), bev=0.002))
    P.add("blued", torus((0, 0, 1.05), 0.09, 0.014, normal=(0, 1, 0), seg=24, rseg=5))
    P.add("brass", torus((0, 0, 1.05), 0.07, 0.005, normal=(0, 1, 0), seg=24, rseg=4))
    gem(P, (0, 0, 1.05), 0.03, "glow_bolt")
    spade = [(0.0, 1.13), (0.07, 1.2), (0.05, 1.32), (0.0, 1.55), (-0.05, 1.32), (-0.07, 1.2)]
    P.add("blued", prism_xz(spade, -0.009, 0.009))
    P.add("brass", prism_xz([(0.0, 1.17), (0.035, 1.22), (0.0, 1.38), (-0.035, 1.22)], -0.011, 0.011))
    for z in (0.3, 0.6, 0.9):
        collar(P, z, 0.02, 0.016, "brass")
    return A


def eelwhip():
    A = Asset("Eelwhip", weight=1.2, usage="A dried electric eel as a whip, glowing bolt spots along its body.")
    P = A.piece("Eelwhip")
    grip(P, -0.12, 0.1, 0.02, "rope")
    cap(P, -0.13, 0.022, mat="copper")
    collar(P, 0.11, 0.024, 0.02, "copper")
    body = catmull([(0, 0, 0.12), (0.06, 0, 0.4), (0.22, 0, 0.66), (0.48, 0, 0.8), (0.74, 0, 0.74), (0.9, 0, 0.58)], n=6)
    n = len(body)
    rad = [0.026 * (1 - 0.6 * (i / (n - 1))) + 0.006 * math.sin(i * 0.9) for i in range(n)]
    P.add("eel", tube(body, rad, segs=8, flatten=0.7, up=(0, 1, 0)))
    for i in range(2, n - 2, 3):
        P.add("glow_bolt", blob(tuple(body[i] + Vector((0, 0.016, 0))), 0.008, scale=(1, 0.5, 1), segs=6, rings=4))
        P.add("glow_bolt", blob(tuple(body[i] + Vector((0, -0.016, 0))), 0.008, scale=(1, 0.5, 1), segs=6, rings=4))
    head = body[-1]
    P.add("eel", blob(tuple(head), 0.03, scale=(1.4, 0.8, 1), segs=10, rings=7))
    d = (body[-1] - body[-2]).normalized()
    for sgn in (-1, 1):
        P.add("bone", cone(tuple(head + d * 0.02 + Vector((0, 0, sgn * 0.01))), tuple(d + Vector((0, 0, sgn * 0.5))), 0.04, 0.008, segs=4))
    return A


def ossuary_scepter():
    A = Asset("OssuaryScepter", weight=1.25, usage="Mace: stacked vertebra shaft, a skull head with red eyes and an iron crown.")
    P = A.piece("OssuaryScepter")
    grip(P, -0.15, 0.08, 0.021, "leather")
    cap(P, -0.16, 0.024, mat="bone")
    for k in range(9):
        z = 0.1 + k * 0.05
        P.add("bone", lathe([(0.016, z), (0.024, z + 0.012), (0.026, z + 0.025), (0.022, z + 0.04), (0.016, z + 0.05)], segs=10))
    P.add("bone", blob((0, 0, 0.66), 0.085, scale=(0.95, 0.9, 1.0), segs=14, rings=10))
    P.add("bone", cbox((0.02, 0, 0.58), (0.09, 0.07, 0.05), bev=0.015, segs=2))
    for sgn in (-1, 1):
        P.add("glow_red", blob((sgn * 0.032, -0.07, 0.67), 0.018, scale=(1, 0.5, 1), segs=8, rings=5))
        P.add("glow_red", blob((sgn * 0.032, 0.07, 0.67), 0.018, scale=(1, 0.5, 1), segs=8, rings=5))
    P.add("iron", torus((0, 0, 0.73), 0.07, 0.01, seg=18, rseg=4))
    for d in ring_of(6, "z"):
        P.add("iron", cone((d[0] * 0.07, d[1] * 0.07, 0.73), (d[0] * 0.3, d[1] * 0.3, 1), 0.07, 0.012, segs=4))
    return A


def furnace_tongs():
    A = Asset("FurnaceTongs", weight=1.2, usage="Smith's tongs gripping a glowing coal; leather-wrapped handles.")
    P = A.piece("FurnaceTongs")
    for sgn in (-1, 1):
        arm = catmull([(sgn * 0.02, 0, -0.18), (sgn * 0.012, 0, 0.1), (-sgn * 0.02, 0, 0.45), (-sgn * 0.035, 0, 0.62),
                       (-sgn * 0.045, 0, 0.7)], n=4)
        P.add("dark_iron", tube(arm, 0.016, segs=6, flatten=0.6, up=(0, 1, 0)))
        jaw = [(-sgn * 0.045, 0.70), (-sgn * 0.075, 0.74), (-sgn * 0.07, 0.82), (-sgn * 0.035, 0.8)]
        P.add("dark_iron", prism_xz(jaw, -0.01, 0.01))
        P.add("leather", lathe(K.ridged(-0.17, 0.04, 0.013, 0.015, 8, end_r=0.013), segs=8, center=(sgn * 0.02, 0, 0)))
    P.add("iron", blob((0, 0, 0.3), 0.016, scale=(1, 1.4, 1), segs=8, rings=5))
    P.add("obsidian", blob((0, 0, 0.8), 0.075, scale=(1.1, 0.9, 1), segs=10, rings=7, rng=random.Random(2), jitter=0.12))
    return A


def moonherd_crook():
    A = Asset("MoonherdCrook", weight=1.2, usage="Shepherd's crook with a hanging moonstone lantern.")
    P = A.piece("MoonherdCrook")
    shaft(P, -0.6, 1.05, 0.019, 0.017, "drift_wood", bend=0.02)
    grip(P, -0.12, 0.12, 0.021, "silk")
    cap(P, -0.61, 0.022, mat="steel")
    hook = catmull([(0, 0, 1.05), (0.0, 0, 1.2), (0.06, 0, 1.3), (0.16, 0, 1.31), (0.22, 0, 1.24), (0.21, 0, 1.14)], n=4)
    P.add("drift_wood", tube(hook, 0.017, segs=8))
    for z in (0.5, 0.98):
        collar(P, z, 0.02, 0.018, "steel")
    P.add("steel", tube([(0.21, 0, 1.14), (0.21, 0, 1.08)], 0.003, segs=4))
    P.add("steel", lathe([(0.0, 1.08), (0.03, 1.075), (0.032, 1.06)], segs=8, cap1=False))
    P.add("moonstone", lathe([(0.0, 1.06), (0.03, 1.05), (0.034, 1.0), (0.03, 0.96), (0.0, 0.955)], segs=8, center=(0.21, 0, 0)))
    P.add("glow_moon", blob((0.21, 0, 1.005), 0.02, segs=8, rings=5))
    return A


def starsand_katana():
    A = Asset("StarsandKatana", weight=1.2, usage="Curved blued blade dusted with glowing star specks; round gold tsuba.")
    P = A.piece("StarsandKatana")
    grip(P, -0.25, 0.05, 0.019, "purple_cloth")
    P.add("brass", lathe([(0.0, -0.275), (0.017, -0.27), (0.021, -0.255), (0.02, -0.245)], segs=10))
    disc(P, (0, 0, 0.065), 0.05, 0.006, "brass", axis=(0, 0, 1))
    path = catmull([(0, 0, 0.07), (0.005, 0, 0.35), (0.025, 0, 0.62), (0.06, 0, 0.86), (0.1, 0, 0.98)], n=5)
    edge_blade(P, "blued", path, lambda t: 0.036 - 0.01 * t, lambda t: 0.007 - 0.003 * t, (1, 0, 0), 0.045)
    rng = random.Random(14)
    for _ in range(14):
        i = rng.randrange(2, len(path) - 2)
        p = path[i]
        for sgn in (-1, 1):
            P.add("glow_moon", blob((p.x + rng.uniform(0.005, 0.025), sgn * 0.0062, p.z + rng.uniform(-0.02, 0.02)),
                                    rng.uniform(0.003, 0.0055), scale=(1, 0.4, 1), segs=5, rings=3))
    return A


def sawshark_blade():
    A = Asset("SawsharkBlade", weight=1.2, usage="A sawfish rostrum: flat grey blade with teeth on both edges.")
    P = A.piece("SawsharkBlade")
    grip(P, -0.15, 0.06, 0.021, "rope")
    P.add("coral", blob((0, 0, -0.17), 0.028, segs=8, rings=6, rng=random.Random(4), jitter=0.15))
    P.add("shark", cbox((0, 0, 0.08), (0.09, 0.05, 0.05), bev=0.015, segs=2))
    blade(P, "shark", 0.1, 1.05, lambda t: -0.042 * (1 - 0.45 * t), lambda t: 0.042 * (1 - 0.45 * t),
          lambda t: 0.012 * (1 - 0.5 * t), rows=16, tip=(0, 0, 1.08))
    for k in range(13):
        z = 0.16 + k * 0.067
        w = 0.042 * (1 - 0.45 * (z - 0.1) / 0.95)
        for sgn in (-1, 1):
            P.add("bone", cone((sgn * w, 0, z), (sgn, 0, 0.15), 0.035, 0.008, segs=4))
    return A


def wardens_key():
    A = Asset("WardensKey", weight=1.2, usage="Giant dungeon key: filigree bow at the bottom, toothed bit at the top.")
    P = A.piece("WardensKey")
    P.add("rust", torus((0, 0, -0.17), 0.09, 0.016, normal=(0, 1, 0), seg=22, rseg=6))
    P.add("brass", torus((0, 0, -0.17), 0.055, 0.008, normal=(0, 1, 0), seg=18, rseg=4))
    gem(P, (0, 0, -0.17), 0.026, "glow_gold")
    grip(P, -0.07, 0.1, 0.022, "leather")
    shaft(P, -0.08, 0.95, 0.019, 0.019, "rust")
    for z in (0.15, 0.6):
        collar(P, z, 0.022, 0.02, "brass")
    bit = [(0.0, 0.7), (0.15, 0.7), (0.15, 0.76), (0.1, 0.76), (0.1, 0.8), (0.15, 0.8), (0.15, 0.88), (0.06, 0.88),
           (0.06, 0.92), (0.15, 0.92), (0.15, 0.97), (0.0, 0.97)]
    P.add("rust", prism_xz(bit, -0.012, 0.012))
    cap(P, 0.96, 0.022, mat="brass", down=False)
    return A


def ferrymans_oar():
    A = Asset("FerrymansOar", weight=1.25, usage="Long oar with a painted soul-eye on the wide blade.")
    P = A.piece("FerrymansOar")
    shaft(P, -0.55, 0.9, 0.019, 0.02, "drift_wood")
    grip(P, -0.12, 0.12, 0.021, "rope")
    P.add("drift_wood", tube([(-0.06, 0, -0.57), (0.06, 0, -0.57)], 0.014, segs=6))
    oar = [(0.0, 0.85), (0.07, 0.92), (0.1, 1.05), (0.1, 1.4), (0.07, 1.5), (0.0, 1.53), (-0.07, 1.5), (-0.1, 1.4),
           (-0.1, 1.05), (-0.07, 0.92)]
    P.add("drift_wood", prism_xz(oar, -0.012, 0.012))
    for sgn in (-1, 1):
        y = sgn * 0.0125
        P.add("purple_cloth", aim(lathe([(0.0, 0.0), (0.06, 0.0), (0.06, 0.002), (0.0, 0.002)], segs=20), (0, sgn, 0), (0, y, 1.25)))
        P.add("glow_violet", aim(lathe([(0.0, 0.0), (0.025, 0.0), (0.02, 0.004), (0.0, 0.005)], segs=14), (0, sgn, 0), (0, y, 1.25)))
    collar(P, 0.86, 0.022, 0.03, "iron")
    return A


def maestros_baton():
    A = Asset("MaestrosBaton", weight=1.0, usage="A conductor's baton: ivory taper, cork grip, glowing gold tip.")
    P = A.piece("MaestrosBaton")
    P.add("paper", lathe([(0.0, -0.11), (0.016, -0.105), (0.02, -0.07), (0.018, 0.02), (0.012, 0.05)], segs=10))
    collar(P, 0.05, 0.011, 0.01, "brass")
    P.add("bone", lathe([(0.012, 0.05), (0.009, 0.3), (0.005, 0.55), (0.0, 0.59)], segs=8))
    P.add("glow_gold", blob((0, 0, 0.59), 0.018, segs=8, rings=5))
    for k, (x, z) in enumerate(((0.06, 0.3), (0.1, 0.42), (0.07, 0.53))):
        P.add("glow_gold", blob((x, 0, z), 0.016, scale=(1.3, 0.5, 1), segs=8, rings=5))
        P.add("glow_gold", tube([(x + 0.014, 0, z), (x + 0.014, 0, z + 0.08)], 0.004, segs=4))
        if k == 1:
            P.add("glow_gold", tube([(x + 0.014, 0, z + 0.08), (x + 0.05, 0, z + 0.06)], 0.004, segs=4))
    return A


def ember_knuckles():
    A = Asset("EmberKnuckles", weight=1.2, usage="Iron gauntlet (dual wield) with cracked obsidian knuckle plates; fist centred on the grip.")
    P = A.piece("EmberKnuckles")
    P.add("dark_iron", cbox((0, 0, 0.0), (0.085, 0.075, 0.11), bev=0.02, segs=2))
    P.add("dark_iron", lathe([(0.04, -0.2), (0.048, -0.16), (0.05, -0.08), (0.045, -0.05)], segs=10))
    for k in range(4):
        x = -0.03 + 0.02 * k
        P.add("obsidian", cbox((x, 0.0, 0.065), (0.018, 0.07, 0.03), bev=0.006))
        P.add("iron", cone((x, 0, 0.08), (0, 0, 1), 0.035, 0.008, segs=4))
    P.add("dark_iron", cbox((0.05, 0.0, 0.02), (0.03, 0.06, 0.05), bev=0.01))
    P.add("leather", torus((0, 0, -0.12), 0.048, 0.008, seg=14, rseg=4))
    P.add("glow_fire", blob((0, -0.04, 0.0), 0.012, scale=(1, 0.4, 1), segs=6, rings=4))
    P.add("glow_fire", blob((0, 0.04, 0.0), 0.012, scale=(1, 0.4, 1), segs=6, rings=4))
    K.scale_piece(P, 1.35)
    return A


def melee_assets():
    return [ember_fang(), moonsickle(), leviathan_rib(), pendulum_axe(), lavender_bottle(), drowned_anchor(),
            moonsilk_whip(), gearsaw(), candelabra_trident(), clockhand_lance(), eelwhip(), ossuary_scepter(),
            furnace_tongs(), moonherd_crook(), starsand_katana(), sawshark_blade(), wardens_key(), ferrymans_oar(),
            maestros_baton(), ember_knuckles()]


def preview(only=None):
    return K.live_preview(melee_assets, "Armory - Melee", row=0, cols=5, spacing=1.6, only=only)


if __name__ == "__main__":
    K.run_headless(melee_assets, "ArmoryMelee")
