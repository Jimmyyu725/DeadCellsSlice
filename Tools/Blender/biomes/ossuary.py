"""Ossuary of the Forgotten Echoes: a labyrinth carved from petrified
leviathan ribs.  Dark umber stone, bleached-bone architecture, marble
stairs, skull walls and candle shrines dripping green tallow."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

import biome_kit as bk
import env_helpers as eh
from biome_kit import TF, TB, G, X, Y, Z, rad, lin, hex_mix, tint, material
from env_helpers import (Builder, block, bm_blob, bm_box, bm_cut, bm_ico, bm_lathe, bm_prism_xz, bm_tube,
                         delete_faces, rotate, scale, transform, translate)

ID = "Ossuary"
UMBER = "#4A3A2C"
FLAME = "#7DFF8A"
TAU = math.tau


def materials(kit):
    M = kit.M
    M["Stone"] = material("M_OS_Stone", UMBER, "#2A1E15", "#62503D", rough=0.88, noise_scale=3.2, noise_amt=0.42,
                          bevel_radius=0.035, bump_strength=0.4, bump_scale=12.0,
                          fx=dict(tint_amt=0.28, grime_hex="#8A7D5C", grime_amt=0.45, blotch=("#352719", 4.5, 0.12),
                                  top_hex="#5A4836", top_amt=0.06, bottom_amt=0.3, edge_hex="#9A8466", edge_amt=0.85,
                                  edge_radius=0.05, edge_top_bias=0.5, cavity_amt=0.85, cavity_dist=0.16,
                                  cavity_hex="#140D08"))
    back = material("M_OS_StoneBack", "#33271D", "#1E160F", "#45372A", rough=0.9, noise_scale=2.2, noise_amt=0.4,
                    bevel_radius=0.04, bump_strength=0.35, bump_scale=8.0,
                    fx=dict(tint_amt=0.24, blotch=("#271D14", 4.0, 0.08), top_hex="#45372A", top_amt=0.2,
                            bottom_amt=0.25, edge_hex="#5E4C3A", edge_amt=0.7, edge_radius=0.05, cavity_amt=0.8,
                            cavity_dist=0.2, cavity_hex="#0E0905"))
    eh.make_periodic(back, 4.0, 4.0)
    M["StoneBack"] = back
    M["Mortar"] = material("M_OS_Mortar", "#160F0A", "#0A0604", "#241911", rough=0.95, noise_scale=6.0,
                           fx=dict(cavity_amt=0.4, cavity_dist=0.1))
    mb = material("M_OS_MortarBack", "#140D08", "#080503", "#22170F", rough=0.95, noise_scale=3.0)
    eh.make_periodic(mb, 4.0, 4.0)
    M["MortarBack"] = mb
    bone = dict(rough=0.7, noise_scale=8.0, noise_amt=0.5, bevel_radius=0.012, bump_strength=0.35, bump_scale=30.0)
    bone_fx = dict(cavity_amt=0.95, cavity_dist=0.06, cavity_hex="#3A2E20", edge_hex="#F2ECD8", edge_amt=0.45,
                   edge_radius=0.012, bottom_amt=0.4, tint_amt=0.18, blotch=("#8E7F5E", 5.0, 0.22))
    M["Bone"] = material("M_OS_Bone", "#CFC4A4", "#8A7D5C", "#EAE2C8", fx=bone_fx, **bone)
    bb = material("M_OS_BoneBack", "#A49878", "#6A5E44", "#C4B898", fx=dict(bone_fx, cavity_amt=1.0), **bone)
    eh.make_periodic(bb, 4.0, 4.0)
    M["BoneBack"] = bb
    M["Powder"] = material("M_OS_Powder", "#C4B898", "#968A6C", "#E2DAC2", rough=0.95, noise_scale=14.0,
                           noise_amt=0.7, bevel_radius=0.02, bump_strength=0.5, bump_scale=45.0,
                           fx=dict(blotch=("#8A7D5C", 9.0, 0.2), cavity_amt=0.6, cavity_dist=0.06,
                                   cavity_hex="#5A4E38", bottom_amt=0.4, top_hex="#D8D0B6", top_amt=0.1))
    M["Marble"] = material("M_OS_Marble", "#9E988C", "#625E56", "#C8C2B6", rough=0.45, noise_scale=2.5,
                           noise_amt=0.5, bevel_radius=0.025, bump_strength=0.2, bump_scale=10.0,
                           fx=dict(blotch=("#4E4A42", 3.5, 0.1), edge_hex="#E2DED4", edge_amt=0.8, edge_radius=0.04,
                                   cavity_amt=0.8, cavity_dist=0.12, cavity_hex="#2A2620", top_hex="#B6B0A4",
                                   top_amt=0.1, bottom_amt=0.3, tint_amt=0.2))
    M["Tallow"] = material("M_OS_Tallow", "#8DB87A", "#5A8A4C", "#C4ECA8", rough=0.35, noise_scale=10.0,
                           emission="#2E7A3A", emission_strength=1.0,
                           fx=dict(cavity_amt=0.5, cavity_dist=0.03, cavity_hex="#2A4A22", top_hex="#D6F6C0",
                                   top_amt=0.3))
    M["Flame"] = material("M_OS_Flame", "#C8FFC8", "#7DFF8A", "#F0FFF0", rough=0.5, emission=FLAME,
                          emission_strength=5.0)
    M["Iron"] = material("M_OS_Iron", "#3A332C", "#1C1814", "#5E544A", rough=0.55, metal=0.6, noise_scale=7.0,
                         bevel_radius=0.008,
                         fx=dict(edge_hex="#7A6E60", edge_amt=0.8, edge_radius=0.012, cavity_amt=0.6,
                                 cavity_dist=0.05, cavity_hex="#0C0A08", blotch=("#5A3A22", 5.0, 0.25)))
    M["Rope"] = material("M_OS_Rope", "#6E5A40", "#3E3020", "#8E7656", rough=0.95, noise_scale=30.0,
                         stripes=("z", 40, 0.25, "#4A3A28"), fx=dict(cavity_amt=0.6, cavity_dist=0.03))
    M["Dark"] = material("M_OS_Dark", "#140E0A", "#080504", "#22180F", rough=0.95, noise_scale=2.5,
                         fx=dict(brick=(0.55, 0.28, "#050302"), cavity_amt=0.6, cavity_dist=0.25, tint_amt=0.15))
    M["Urn"] = material("M_OS_Urn", "#5A4030", "#33231A", "#7A5A44", rough=0.6, noise_scale=6.0,
                        stripes=("z", 6.0, 0.08, "#2A1C14"),
                        fx=dict(edge_hex="#A08060", edge_amt=0.6, edge_radius=0.015, cavity_amt=0.7,
                                cavity_dist=0.06))
    M["BGStone"] = material("M_OS_BGStone", "#2E241C", "#18120D", "#45362A", rough=0.9, noise_scale=0.7,
                            bevel_radius=0.06, bump_strength=0.3, bump_scale=4.0,
                            fx=dict(brick=(1.2, 0.55, "#110C08"), top_hex="#5A4A3A", top_amt=0.35, bottom_amt=0.3,
                                    edge_hex="#6A5644", edge_amt=0.7, edge_radius=0.18, cavity_amt=0.6,
                                    cavity_dist=1.2, cavity_hex="#0A0705", tint_amt=0.2))
    M["BGBone"] = material("M_OS_BGBone", "#6A604C", "#3A3328", "#8E846C", rough=0.8, noise_scale=1.0,
                           bevel_radius=0.08, bump_strength=0.3, bump_scale=3.0,
                           fx=dict(top_hex="#A49A80", top_amt=0.4, bottom_amt=0.35, edge_hex="#B8AE94", edge_amt=0.7,
                                   edge_radius=0.2, cavity_amt=0.7, cavity_dist=1.0, cavity_hex="#1E1A12",
                                   tint_amt=0.2))
    M["BGWindow"] = material("M_OS_BGWindow", "#2A4A2C", "#183018", "#3A6A3C", noise_scale=2.0, emission=FLAME,
                             emission_strength=2.0)


# ---------------------------------------------------------------------------
# Shared bits
# ---------------------------------------------------------------------------

def femur_end(pos, r=0.085, depth=0.35, segs=7, facing=Vector((0, -1, 0)), lod=0):
    """Femur seen end-on: shaft running into the wall, knobbly head at `pos`."""
    prof = [(r * 0.45, -depth), (r * 0.55, -0.12), (r * 0.9, -0.05), (r, -0.02), (r * 0.85, 0.0), (r * 0.45, 0.012)]
    if lod:
        prof = [(r * 0.5, -depth), (r, -0.03 * r / 0.085), (r * 0.5, 0.012)]
    bm = bm_lathe(prof, segs=segs, scale_xy=(1.0, 0.82))
    m = eh.look_matrix(Vector(pos), Vector(pos) + Vector(facing))
    return transform(bm, m)


def candle(B, M, base, h=0.25, r=0.035, rng=None, flame=True, drips=3):
    base = Vector(base)
    body = bm_lathe([(r, 0.0), (r * 1.02, h * 0.85), (r * 0.9, h), (r * 0.35, h * 0.97)], segs=8)
    translate(body, base)
    B.add(body, M["Tallow"], smooth=True, uvw=1.3)
    rng = rng or random.Random(1)
    for k in range(drips):
        a = rng.uniform(0, TAU)
        p0 = base + Vector((math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, h * 0.97))
        L = rng.uniform(0.3, 0.8) * h
        pts = [p0 + Vector((math.cos(a) * 0.006 * t, math.sin(a) * 0.006 * t, -L * t)) for t in lin(0, 1, 4)]
        B.add(bm_tube(pts, [0.011, 0.01, 0.009, 0.012], segs=4), M["Tallow"], smooth=True)
    if flame:
        fl = bm_lathe([(0.0005, 0.0), (0.02, 0.018), (0.024, 0.045), (0.014, 0.08), (0.0005, 0.115)], segs=6)
        translate(fl, base + Vector((0, 0, h + 0.004)))
        B.add(fl, M["Flame"], smooth=True, uvw=1.0)
    return base + Vector((0, 0, h + 0.05))


def vertebra(B, M, center, s=1.0, rng=None, mat=None, processes=True):
    c = Vector(center)
    body = bm_lathe([(0.2 * s, -0.16 * s), (0.25 * s, -0.13 * s), (0.22 * s, -0.04 * s), (0.21 * s, 0.04 * s),
                     (0.25 * s, 0.13 * s), (0.2 * s, 0.16 * s)], segs=10)
    translate(body, c)
    B.add(body, mat or M["Bone"], smooth=True, tint=tint(rng) if rng else None)
    if processes:
        for sx in (-1, 1):
            B.add(bm_bone(c + Vector((sx * 0.15 * s, 0.05 * s, 0.02 * s)), c + Vector((sx * 0.36 * s, 0.12 * s, 0.08 * s)),
                          r=0.04 * s, knob=0.06 * s, segs=5), mat or M["Bone"], smooth=True)
        B.add(bm_bone(c + Vector((0, 0.15 * s, 0.0)), c + Vector((0, 0.42 * s, -0.12 * s)), r=0.04 * s, knob=0.055 * s,
                      segs=5), mat or M["Bone"], smooth=True)


bm_bone = bk.bm_bone


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------

TILES = {
    "Fill_A": (401, [(0.0, 0.5, [0.45]), (0.5, 1.0, [0.62])], (0, 0)),
    "Fill_B": (402, [(0.0, 0.3, [0.5]), (0.68, 1.0, [0.4])], None),
    "Fill_C": (403, [(0.0, 0.55, [0.38]), (0.55, 1.0, [0.6])], None),
    "Top_A": (411, [(0.0, 0.45, [0.6]), (0.45, 1.0, [0.35])], (0, 0)),
    "Top_B": (412, [(0.0, 0.52, [0.4]), (0.52, 1.0, [0.68])], None),
    "Edge_L": (421, [(0.0, 0.5, [0.5]), (0.5, 1.0, [0.55])], None),
}


def make_tile(kit, role):
    M = kit.M
    seed, rows, crack = TILES[role]

    def fn():
        rng = random.Random(seed)
        B = Builder(kit.name(role))
        edge = "L" if role == "Edge_L" else None
        mossy = role.startswith(("Top", "Edge"))
        bfn = bk.stone_block_fn(M["Stone"], top_grime=0.5 if mossy else 0.0, bevel=0.034, chips=(1, 3),
                                chip_size=(0.04, 0.13), jitter=0.016)
        bk.tile_body(B, rng, rows, bfn, M["Mortar"], edge=edge, crack=crack)
        if role == "Fill_B":
            for ri, zc in enumerate((0.395, 0.585)):
                n = 5
                for k in range(n if ri == 0 else n - 1):
                    x = (k + 0.5 + (0.5 if ri else 0.0)) / n
                    B.add(femur_end((x, TF - rng.uniform(0.0, 0.03), zc), r=0.092), M["Bone"], smooth=True,
                          tint=tint(rng), uvw=1.2)
        if role == "Fill_C":
            sk, jaw = bk.bm_skull((0.7, TF + 0.02, 0.27), rng, size=1.55, pitch=rad(-6), yaw=rad(8))
            B.add(sk, M["Bone"], smooth=True, uvw=1.3)
            B.add(jaw, M["Bone"], uvw=1.3)
        if mossy:
            D = bk.lip_cover(B, rng, seed, M["Powder"], edge=edge, base=0.07, amp=0.05, dmin=0.035, dmax=0.18,
                             top_depth=0.32, offset=0.024, lump_amp=0.018, lump_freq=6.0,
                             clumps=(3, (0.045, 0.06), (1.9, 1.1, 0.6)))
            if role == "Top_A":
                for k in range(4):
                    x = 0.15 + 0.7 * (k + rng.uniform(0.2, 0.8)) / 4
                    z0 = 1.0 - D(x) + 0.03
                    L = rng.uniform(0.1, 0.32)
                    pts = [Vector((x + 0.01 * math.sin(t * 3), -0.957, z0 - L * t)) for t in lin(0, 1, 5)]
                    B.add(bm_tube(pts, [0.02, 0.017, 0.015, 0.014, 0.018], segs=5, flatten=0.6), M["Tallow"],
                          smooth=True)
            else:
                for k in range(3):
                    x = rng.uniform(0.15, 0.85)
                    p0 = Vector((x, -0.86, 1.012))
                    d = Vector((rng.uniform(-1, 1), rng.uniform(-0.3, 0.3), 0)).normalized() * rng.uniform(0.1, 0.18)
                    B.add(bm_bone(p0 - d / 2, p0 + d / 2, r=0.011, knob=0.018, segs=5), M["Bone"], smooth=True)
        bk.clamp_tile(B)
        return B

    return fn


# ---------------------------------------------------------------------------
# Platform / walls
# ---------------------------------------------------------------------------

def make_platform(kit):
    """Two petrified long bones lashed side by side, flat-topped, vertebra bracket."""
    M = kit.M

    def fn():
        rng = random.Random(431)
        B = Builder(kit.name("Platform"))
        for (yc, r) in ((-0.36, 0.13), (0.42, 0.13)):
            prof = [(r * 0.95, 0.0), (r * 1.25, 0.06), (r * 1.15, 0.14), (r, 0.24), (r * 0.92, 0.5), (r, 0.76),
                    (r * 1.15, 0.86), (r * 1.25, 0.94), (r * 0.95, 1.0)]
            bone = bm_lathe(prof, segs=12, scale_xy=(1.0, 1.9 if yc < 0 else 2.3))
            rotate(bone, math.pi / 2, "Y")
            translate(bone, (0.0, yc, 0.9))
            bm_cut(bone, (0, 0, 1.0), (0, 0, 1))
            bm_cut(bone, (0, 0, 0.8), (0, 0, -1))
            bm_cut(bone, (0.0005, 0, 0), (-1, 0, 0))
            bm_cut(bone, (0.9995, 0, 0), (1, 0, 0))
            B.add(bone, M["Bone"], smooth=False, hard=35, tint=tint(rng),
                  uvw_fn=lambda c, n: 1.0 if c.y < -0.2 else 0.45)
        vertebra(B, M, (0.5, 0.55, 0.6), s=0.75, rng=rng)
        B.add(bm_bone((0.5, 0.75, 0.3), (0.5, 0.95, 0.55), r=0.04, knob=0.06), M["Bone"], smooth=True)
        for cx in (0.16, 0.84):
            for yc in (-0.36, 0.42):
                ring = [(cx + 0.02 * math.sin(a * 2), yc + 0.27 * math.cos(a) * (1.5 if yc < 0 else 1.8) * 0.5,
                         0.9 + 0.11 * math.sin(a)) for a in lin(0, TAU, 13)[:-1]]
                ring = [(x, y, min(z, 0.995)) for x, y, z in ring]
                B.add(bm_tube(ring, 0.014, segs=5, closed=True, up=X), M["Rope"], smooth=True)
        return B

    return fn


def make_backwall(kit):
    M = kit.M

    def hook(B, rng, lo, hi, ri, bi):
        if rng.random() < 0.16 and hi[0] - lo[0] > 1.1:
            z = (lo[2] + hi[2]) / 2 + rng.uniform(-0.1, 0.1)
            x0 = lo[0] + 0.12
            x1 = min(hi[0] - 0.12, x0 + rng.uniform(0.8, 1.2))
            B.add(bm_bone((x0, lo[1] - 0.03, z), (x1, lo[1] - 0.03, z + rng.uniform(-0.1, 0.1)), r=0.06,
                          knob=0.1, segs=6), M["BoneBack"], smooth=True)

    def fn():
        rng = random.Random(441)
        B = Builder(kit.name("BackWall"))
        bk.masonry_wall(B, rng, M["StoneBack"], M["MortarBack"], rows=[0.8, 0.95, 0.7, 0.85, 0.75], width=(1.0, 1.7),
                        gap=0.08, bevel=0.05, segs=2, chips=(1, 3), block_hook=hook)
        return B

    return fn


def make_skull_wall(kit):
    """Classic ossuary wall: skull rows between rows of femur heads (4x4, seamless)."""
    M = kit.M

    def fn():
        rng = random.Random(451)
        B = Builder(kit.name("SkullWall"))
        P = 4.0
        rows = [("f", 0.3), ("s", 0.62), ("f", 0.3), ("s", 0.62), ("f", 0.3), ("s", 0.62), ("f", 0.3), ("s", 0.62),
                ("f", 0.32)]
        sc = P / sum(h for _, h in rows)
        z = 0.0
        for ri, (kind, h) in enumerate(rows):
            h *= sc
            if kind == "s":
                for k in range(8):
                    x = (k + 0.5) * P / 8 + rng.uniform(-0.03, 0.03)
                    sk, jaw = bk.bm_skull((0.0, 0.0, 0.0), rng, size=2.3, yaw=rng.uniform(-0.25, 0.25),
                                          pitch=rng.uniform(-0.15, 0.1), roll=rng.uniform(-0.12, 0.12), segs=(6, 5))
                    for b_ in (sk, jaw):
                        scale(b_, (1.0, 0.62, 1.0))
                        translate(b_, (x, 0.165, z + h * 0.52))
                    t = tint(rng, b=(0.0, 0.35))
                    B.add(sk, M["BoneBack"], smooth=True, tint=t)
                    if rng.random() < 0.3:
                        B.add(jaw, M["BoneBack"], tint=t)
                    else:
                        jaw.free()
            else:
                n = 12
                off = 0.5 if (ri // 2) % 2 else 0.0
                for k in range(n):
                    x = (k + 0.5 + off) * P / n
                    if x >= P - 0.12:
                        continue
                    B.add(femur_end((x, 0.012 + rng.uniform(0.0, 0.03), z + h / 2), r=h * 0.44, depth=0.16, segs=5, lod=1),
                          M["BoneBack"], smooth=True, tint=tint(rng))
            z += h
        bk.backing_plane(B, M["MortarBack"], P, 0.3)
        return B

    return fn


# ---------------------------------------------------------------------------
# Pillar / Arch / RibArch / Door
# ---------------------------------------------------------------------------

def make_pillar(kit):
    """Vertebral column on a marble plinth, skull crown."""
    M = kit.M

    def fn():
        rng = random.Random(461)
        B = Builder(kit.name("Pillar"))
        cy = 0.5
        B.add(block((-0.5, 0.0, 0.0), (0.5, 1.0, 0.3), rng, chips=2, bevel=0.04, segs=2, back_delete=0.95), M["Marble"],
              tint=tint(rng))
        B.add(block((-0.4, 0.1, 0.3), (0.4, 0.9, 0.5), rng, chips=1, bevel=0.04, segs=2, back_delete=0.9,
                    cuts=[((0, 0.16, 0.5), (0, -1, 1)), ((-0.34, 0, 0.5), (-1, 0, 1)), ((0.34, 0, 0.5), (1, 0, 1))]),
              M["Marble"], tint=tint(rng))
        z = 0.5
        k = 0
        while z < 4.3:
            s = 1.0 - 0.04 * k
            vertebra(B, M, (0.0, cy, z + 0.17 * s), s=s * 1.2, rng=rng)
            disc = bm_lathe([(0.2 * s, 0.0), (0.24 * s, 0.03), (0.2 * s, 0.06)], segs=10)
            translate(disc, (0, cy, z + 0.34 * s * 1.2))
            B.add(disc, M["Tallow"] if k == 3 else M["Stone"], smooth=True)
            z += 0.41 * s * 1.2
            k += 1
        B.add(block((-0.46, 0.04, z), (0.46, 0.96, z + 0.22), rng, chips=2, bevel=0.035, segs=2, back_delete=0.95,
                    cuts=[((0, 0.04 + 0.08, z), (0, -1, -1))]), M["Marble"], tint=tint(rng))
        z += 0.22
        sk, jaw = bk.bm_skull((0.0, 0.45, z + 0.13 * 1.6), rng, size=1.7, pitch=rad(-10))
        B.add(sk, M["Bone"], smooth=True, uvw=1.3)
        B.add(jaw, M["Bone"], uvw=1.3)
        for sx in (-0.33, 0.33):
            candle(B, M, (sx, 0.25, z), h=0.16, r=0.04, rng=rng)
        bk.ledge_cover(B, rng, M["Powder"], -0.4, 0.4, 0.1, 0.4, 0.5, depth=(0.03, 0.09), seed=4.0, env_z0=0.3,
                       lump_amp=0.02)
        return B

    return fn


def rib_curve(base, top, bulge, n=10):
    base, top = Vector(base), Vector(top)
    pts = []
    for t in lin(0, 1, n):
        p = base.lerp(top, t)
        p += Vector(bulge) * math.sin(math.pi * t) * (1 - 0.3 * t)
        pts.append(p)
    return pts


def rib_bone(B, mat, pts, r0, r1, flatten=0.55, segs=8, rng=None):
    n = len(pts)
    radii = [r0 + (r1 - r0) * (k / (n - 1)) ** 0.8 for k in range(n)]
    radii[0] *= 1.25
    B.add(bm_tube(pts, radii, segs=segs, flatten=flatten, up=Y), mat, smooth=True, tint=tint(rng) if rng else None)


def make_arch(kit):
    """Marble arch crowned by a fan of rib bones; tallow-dripping impost candles."""
    M = kit.M

    def fn():
        rng = random.Random(471)
        B = Builder(kit.name("Arch"))
        cz, r_in, r_out = 2.75, 2.1, 2.55
        for s in (-1, 1):
            lx, hx = sorted((s * 2.05, s * 3.0))
            B.add(block((lx, -0.07, 0.0), (hx, 0.8, 0.3), rng, chips=2, bevel=0.035, segs=2, back_delete=0.75),
                  M["Marble"], tint=tint(rng))
            lx, hx = sorted((s * 2.1, s * 2.95))
            z = bk.pier(B, rng, lx, hx, [0.6, 0.55, 0.65, 0.5], M["Marble"], z=0.3, segs=1, bevel=0.035, grime=0.0)
            lx, hx = sorted((s * 2.02, s * 3.03))
            B.add(block((lx, -0.07, z + 0.01), (hx, 0.8, cz), rng, chips=2, bevel=0.03, segs=1, back_delete=0.75,
                        cuts=[((0, -0.07 + 0.06, z + 0.01), (0, -1, -1))]), M["Marble"], tint=tint(rng))
            core = bm_box((min(s * 2.18, s * 2.88), 0.08, 0.3), (max(s * 2.18, s * 2.88), 0.72, cz))
            delete_faces(core, lambda c, n: n.y > 0.9)
            B.add(core, M["Mortar"], uvw=0.3)
            for dx in (-0.25, 0.2):
                candle(B, M, (s * 2.5 + dx, -0.02, cz), h=rng.uniform(0.14, 0.24), r=0.035, rng=rng)
        bk.voussoirs(B, rng, (0.0, cz), r_in, r_out, 0.0, 0.8, 11, 0.045, M["Marble"], key_extra=0.15, segs=1,
                     bevel=0.03)
        for i in range(12):
            a0, a1 = math.pi * i / 12, math.pi * (i + 1) / 12
            poly = [(2.16 * math.cos(a0), cz + 2.16 * math.sin(a0)), (2.48 * math.cos(a0), cz + 2.48 * math.sin(a0)),
                    (2.48 * math.cos(a1), cz + 2.48 * math.sin(a1)), (2.16 * math.cos(a1), cz + 2.16 * math.sin(a1))]
            bm = bm_prism_xz(poly, 0.07, 0.72)
            delete_faces(bm, lambda c, n: n.y > 0.9)
            B.add(bm, M["Mortar"], uvw=0.3)
        for k, th in enumerate(lin(rad(22), rad(158), 9)):
            base = Vector((2.5 * math.cos(th), 0.3, cz + 2.5 * math.sin(th)))
            out = Vector((math.cos(th), 0, math.sin(th)))
            L = 0.42 + 0.14 * math.sin(th) ** 2
            pts = [base + out * L * t + Vector((0, -0.12 * math.sin(math.pi * t), 0)) +
                   Vector((-out.z, 0, out.x)) * 0.12 * t * t for t in lin(0, 1, 6)]
            rib_bone(B, M["Bone"], pts, 0.045, 0.015, flatten=0.6, segs=6, rng=rng)
        sk, jaw = bk.bm_skull((0.0, -0.08, cz + r_out + 0.12), rng, size=1.6)
        B.add(sk, M["Bone"], smooth=True)
        B.add(jaw, M["Bone"])
        return B

    return fn


def make_rib_arch(kit):
    """Two giant leviathan ribs (8 m span) meeting at a vertebra keystone."""
    M = kit.M

    def fn():
        rng = random.Random(481)
        B = Builder(kit.name("RibArch"))
        for s in (-1, 1):
            B.add(block((min(s * 3.55, s * 4.55), -0.2, 0.0), (max(s * 3.55, s * 4.55), 0.9, 0.45), rng, chips=3,
                        chip_size=(0.06, 0.18), bevel=0.04, segs=2, back_delete=0.85), M["Stone"], tint=tint(rng))
            pts = rib_curve((s * 4.05, 0.35, 0.3), (s * 0.35, 0.35, 7.0), (s * 1.4, -0.25, 0.6), n=14)
            rib_bone(B, M["Bone"], pts, 0.34, 0.2, flatten=0.62, segs=10, rng=rng)
            knob = bm_blob(pts[0] + Vector((0, 0, 0.15)), 0.42, (1.0, 0.8, 0.75), segs=10, rings=7, rng=rng,
                           jitter=0.06)
            B.add(knob, M["Bone"], smooth=True)
            for t in (0.28, 0.5, 0.7):
                i = int(t * (len(pts) - 1))
                p = pts[i]
                d = (pts[i + 1] - pts[i - 1]).normalized()
                ring = [p + (Vector((-d.z, 0, d.x)) * math.cos(a) * 0.36 + Y * math.sin(a) * 0.24) for a in
                        lin(0, TAU, 13)[:-1]]
                B.add(bm_tube(ring, 0.022, segs=5, closed=True, up=d), M["Rope"], smooth=True)
            for k in range(3):
                i = 4 + k * 3
                base = pts[i] + Vector((0, -0.1, -0.15))
                pts2 = [base + Vector((0.03 * math.sin(t * 5), -0.02 * t, -t * (0.6 + 0.4 * k))) for t in lin(0, 1, 6)]
                B.add(bm_tube(pts2, [0.02, 0.018, 0.016, 0.014, 0.012, 0.015], segs=5), M["Tallow"], smooth=True)
        vertebra(B, M, (0.0, 0.35, 7.05), s=1.6, rng=rng)
        for s in (-1, 1):
            candle(B, M, (s * 3.75, -0.08, 0.45), h=0.3, r=0.05, rng=rng)
            candle(B, M, (s * 4.3, 0.0, 0.45), h=0.18, r=0.04, rng=rng)
        for k in range(6):
            p0 = Vector((rng.uniform(-1.6, 1.6), 0.2, 6.1 + rng.uniform(-0.3, 0.3)))
            bk.silk_thread(B, M["Rope"], [p0, p0 + Vector((0.03, 0, -0.5)), p0 + Vector((0.0, 0, -0.9))], r=0.01)
            vertebra(B, M, p0 + Vector((0, 0, -0.98)), s=0.28, rng=rng, processes=False)
        return B

    return fn


def mandible(B, M, center, w, h, thick, rng):
    """Giant jawbone as a lintel arch, teeth along the inner edge."""
    c = Vector(center)
    pts = [c + Vector((w * math.cos(a), 0, h * math.sin(a))) for a in lin(rad(-12), rad(192), 15)]
    rib_bone(B, M["Bone"], pts, thick * 1.15, thick, flatten=0.7, segs=8, rng=rng)
    for k, a in enumerate(lin(rad(20), rad(160), 10)):
        p = c + Vector(((w - thick * 0.6) * math.cos(a), -0.05, (h - thick * 0.6) * math.sin(a)))
        d = -Vector((math.cos(a), 0, math.sin(a) * h / w)).normalized()
        L = 0.16 if k % 3 else 0.24
        tooth = bm_lathe([(0.045, 0.0), (0.04, L * 0.5), (0.0005, L)], segs=5)
        transform(tooth, eh.look_matrix(p, p + d))
        B.add(tooth, M["Bone"], smooth=True)


def make_door(kit):
    M = kit.M

    def fn():
        rng = random.Random(491)
        B = Builder(kit.name("Door"))
        S = M["Stone"]
        D1 = 0.45
        for s in (-1, 1):
            z = 0.0
            for k, h in enumerate([0.5, 0.42, 0.55, 0.45, 0.48]):
                outer = 1.2 if k % 2 == 0 else 1.1
                lo = (min(s * 0.8, s * outer) + (G / 2 if s > 0 else 0), rng.uniform(-0.025, 0.02), z + G / 2)
                hi = (max(s * 0.8, s * outer) - (G / 2 if s < 0 else 0), D1, z + h - G / 2)
                if k == 2:
                    for j in range(2):
                        B.add(femur_end((s * (0.89 + 0.2 * j), -0.02, z + h / 2), r=0.09), M["Bone"], smooth=True)
                    core = bm_box(lo, (hi[0], D1, hi[2]))
                    core.verts.ensure_lookup_table()
                    translate(core, (0, 0.06, 0))
                    delete_faces(core, lambda c, n: n.y > 0.9)
                    B.add(core, M["Mortar"], uvw=0.3)
                else:
                    B.add(block(lo, hi, rng, chips=rng.randint(1, 2), bevel=0.03, segs=2, jitter=0.014,
                                back_delete=D1 - 0.05), S, tint=tint(rng))
                z += h
            sk, jaw = bk.bm_skull((s * 1.0, 0.0, 2.55), rng, size=1.6, yaw=-s * 0.25)
            B.add(sk, M["Bone"], smooth=True, uvw=1.2)
            B.add(jaw, M["Bone"], uvw=1.2)
        mandible(B, M, (0.0, 0.15, 2.4), 1.05, 0.62, 0.13, rng)
        B.add(block((-0.84, -0.06, 0.0), (0.84, 0.75, 0.1), rng, chips=2, bevel=0.02, segs=2, back_delete=0.7),
              M["Marble"], tint=tint(rng))
        DK = M["Dark"]
        B.add(delete_faces(bm_box((-0.9, 0.72, 0.0), (0.9, 0.78, 3.1)), lambda c, n: n.y > 0.5), DK)
        for s in (-1, 1):
            B.add(delete_faces(bm_box((min(s * 0.8, s * 0.86), 0.4, 0.0), (max(s * 0.8, s * 0.86), 0.74, 3.0)),
                               lambda c, n, s=s: n.x * s > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.4, 2.62), (0.82, 0.74, 2.68)), lambda c, n: n.z > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.4, -0.05), (0.82, 0.74, 0.005)), lambda c, n: n.z < -0.5), DK, uvw=0.6)
        bk.ledge_cover(B, rng, M["Powder"], -0.82, 0.82, -0.06, 0.3, 0.1, depth=(0.02, 0.06), seed=2.0, env_z0=0.0,
                       lump_amp=0.02)
        for (x, h) in ((-0.55, 0.22), (-0.4, 0.14), (0.5, 0.3)):
            candle(B, M, (x, 0.05, 0.1), h=h, r=0.04, rng=rng)
        return B

    return fn


# ---------------------------------------------------------------------------
# Light / Hang / Props
# ---------------------------------------------------------------------------

def make_light(kit):
    """Candle shrine: marble niche shelf with a skull and three dripping candles."""
    M = kit.M

    def fn():
        rng = random.Random(501)
        B = Builder(kit.name("Light"))
        back = bm_prism_xz([(-0.26, 0.0), (0.26, 0.0), (0.26, 0.42)] +
                           [(0.26 * math.cos(a), 0.42 + 0.26 * math.sin(a)) for a in lin(0, math.pi, 9)[1:-1]] +
                           [(-0.26, 0.42)], -0.06, 0.0)
        eh.bm_bevel(back, 0.012, 1)
        delete_faces(back, lambda c, n: n.y > 0.9)
        B.add(back, M["Marble"], tint=tint(rng))
        B.add(block((-0.3, -0.3, -0.06), (0.3, -0.04, 0.02), rng, chips=2, bevel=0.015, segs=2,
                    cuts=[((0, -0.3, -0.06 + 0.04), (0, -1, -1))]), M["Marble"], tint=tint(rng))
        B.add(bm_bone((0, -0.06, -0.06), (0, -0.2, -0.24), r=0.025, knob=0.04), M["Bone"], smooth=True)
        sk, jaw = bk.bm_skull((0.0, -0.15, 0.02 + 0.1 * 1.3), rng, size=1.3, pitch=rad(-5))
        B.add(sk, M["Bone"], smooth=True, uvw=1.3)
        B.add(jaw, M["Bone"], uvw=1.3)
        tops = []
        for (x, y, h) in ((-0.2, -0.17, 0.2), (0.19, -0.2, 0.28), (0.1, -0.08, 0.13)):
            tops.append(candle(B, M, (x, y, 0.02), h=h, r=0.033, rng=rng, drips=4))
        for k in range(3):
            x = rng.uniform(-0.25, 0.25)
            pts = [Vector((x, -0.302, 0.02)), Vector((x + 0.01, -0.305, -0.04)), Vector((x, -0.304, -0.1 - 0.05 * k))]
            B.add(bm_tube(pts, [0.014, 0.012, 0.015], segs=5, flatten=0.6), M["Tallow"], smooth=True)
        B.sockets["LightSocket"] = tuple(tops[1])
        s = 1.25
        translate(B.bm, (0, 0, 0.06))
        scale(B.bm, s)
        B.sockets["LightSocket"] = tuple(c * s for c in (tops[1] + Vector((0, 0, 0.06))))
        return B

    return fn


def make_hang(kit):
    """Rope of vertebra beads ending in a skull and finger bones (~2.6 m)."""
    M = kit.M

    def fn():
        rng = random.Random(511)
        B = Builder(kit.name("Hang"))
        B.add(bm_lathe([(0.06, 0.0), (0.06, -0.04), (0.02, -0.07)], segs=8), M["Iron"])
        pts = [Vector((0.03 * math.sin(t * 6), 0, -2.3 * t)) for t in lin(0, 1, 12)]
        B.add(bm_tube(pts, 0.015, segs=5), M["Rope"], smooth=True)
        for k in range(9):
            t = 0.08 + 0.09 * k
            p = Vector((0.03 * math.sin(t * 6), 0, -2.3 * t))
            vertebra(B, M, p, s=0.42 - 0.012 * k, rng=rng, processes=(k % 2 == 0))
        sk, jaw = bk.bm_skull((0.0, 0.0, -2.42), rng, size=1.5, pitch=rad(15), roll=rad(-8))
        B.add(sk, M["Bone"], smooth=True, uvw=1.2)
        B.add(jaw, M["Bone"], uvw=1.2)
        for k in range(4):
            a = TAU * k / 4 + 0.3
            p0 = Vector((0.05 * math.cos(a), 0.05 * math.sin(a), -2.3))
            B.add(bm_bone(p0, p0 + Vector((0.12 * math.cos(a), 0.08 * math.sin(a), -0.25)), r=0.009, knob=0.016,
                          segs=5), M["Bone"], smooth=True)
        return B

    return fn


def make_prop_a(kit):
    """Skull pile with candles."""
    M = kit.M

    def fn():
        rng = random.Random(521)
        B = Builder(kit.name("Prop_A"))
        spots = [(-0.3, 0.3, 0.0), (0.05, 0.25, 0.0), (0.38, 0.35, 0.0), (-0.12, 0.42, 0.21), (0.22, 0.45, 0.21),
                 (0.05, 0.5, 0.41)]
        for (x, y, z) in spots:
            sk, jaw = bk.bm_skull((x, y, z + 0.13 * 1.25), rng, size=1.25, yaw=rng.uniform(-0.5, 0.5),
                                  pitch=rng.uniform(-0.2, 0.15), roll=rng.uniform(-0.3, 0.3))
            t = tint(rng)
            B.add(sk, M["Bone"], smooth=True, tint=t)
            B.add(jaw, M["Bone"], tint=t)
        for (x, y, h) in ((-0.48, 0.2, 0.3), (0.5, 0.15, 0.22), (0.3, 0.62, 0.42)):
            candle(B, M, (x, y, 0.0), h=h, r=0.04, rng=rng, drips=4)
        for k in range(5):
            a = rng.uniform(0, TAU)
            p0 = Vector((rng.uniform(-0.5, 0.5), rng.uniform(0.0, 0.6), 0.02))
            d = Vector((math.cos(a), math.sin(a) * 0.6, 0.0)) * rng.uniform(0.15, 0.3)
            B.add(bm_bone(p0 - d, p0 + d, r=0.016, knob=0.028, segs=5), M["Bone"], smooth=True)
        pool = bm_lathe([(0.0005, 0.0), (0.12, 0.004), (0.16, 0.0)], segs=10, scale_xy=(1.3, 1.0))
        translate(pool, (0.5, 0.15, 0.0))
        B.add(pool, M["Tallow"], smooth=True)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), -min(v.co.z for v in B.bm.verts)))
        return B

    return fn


def make_prop_b(kit):
    """Broken flight of marble stairs."""
    M = kit.M

    def fn():
        rng = random.Random(531)
        B = Builder(kit.name("Prop_B"))
        for k in range(4):
            z0, z1 = k * 0.24, (k + 1) * 0.24
            y0 = k * 0.26
            x0, x1 = -0.6 + rng.uniform(0, 0.05), 0.6 - rng.uniform(0, 0.05) - (0.25 if k == 3 else 0.0)
            cuts = []
            if k >= 2:
                cuts.append(((0.35, y0, z1), (0.7, -0.2, 0.7)))
            B.add(block((x0, y0, z0), (x1, 1.1, z1), rng, chips=2, chip_size=(0.03, 0.1), bevel=0.02, segs=2,
                        cuts=cuts), M["Marble"], tint=tint(rng),
                  uvw_fn=lambda c, n: 0.4 if n.y > 0.5 else 1.0)
        for k in range(3):
            p = Vector((rng.uniform(0.35, 0.75), rng.uniform(-0.25, 0.1), 0.05))
            B.add(eh.bm_hull([p + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), rng.uniform(-0.05, 0.08)))
                              for _ in range(8)]), M["Marble"], tint=tint(rng))
        bk.ledge_cover(B, rng, M["Powder"], -0.6, 0.35, 0.0, 0.25, 0.24, depth=(0.02, 0.07), seed=8.0, env_z0=0.0,
                       lump_amp=0.02)
        candle(B, M, (-0.42, 0.62, 0.72), h=0.22, r=0.04, rng=rng)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), -min(v.co.z for v in B.bm.verts)))
        return B

    return fn


def make_prop_c(kit):
    """Reliquary urn with a skull finial."""
    M = kit.M

    def fn():
        rng = random.Random(541)
        B = Builder(kit.name("Prop_C"))
        urn = bm_lathe([(0.16, 0.0), (0.2, 0.03), (0.15, 0.08), (0.22, 0.2), (0.3, 0.38), (0.3, 0.5), (0.22, 0.64),
                        (0.15, 0.7), (0.2, 0.74), (0.2, 0.78), (0.12, 0.79)], segs=14)
        translate(urn, (0, 0.32, 0))
        B.add(urn, M["Urn"], smooth=True, tint=tint(rng), hard=50)
        for sx in (-1, 1):
            hd = [(sx * 0.27, 0.32, 0.55), (sx * 0.38, 0.32, 0.58), (sx * 0.4, 0.32, 0.46), (sx * 0.3, 0.32, 0.42)]
            B.add(bm_tube(hd, 0.022, segs=6), M["Iron"], smooth=True)
        band = bm_lathe([(0.305, 0.4), (0.315, 0.42), (0.315, 0.47), (0.305, 0.49), (0.305, 0.4)], segs=14,
                        cap_top=False, cap_bottom=False)
        translate(band, (0, 0.32, 0))
        B.add(band, M["Iron"], hard=40)
        sk, jaw = bk.bm_skull((0.0, 0.32, 0.79 + 0.11), rng, size=1.0)
        B.add(sk, M["Bone"], smooth=True, uvw=1.3)
        B.add(jaw, M["Bone"], uvw=1.3)
        for k in range(3):
            a = -math.pi / 2 + (k - 1) * 0.6
            p0 = Vector((0.3 * math.cos(a), 0.32 + 0.3 * math.sin(a), 0.48))
            pts = [p0 + Vector((0.01 * math.cos(a) * t, 0.01 * math.sin(a) * t, -0.18 * t)) for t in lin(0, 1, 4)]
            B.add(bm_tube(pts, [0.012, 0.011, 0.01, 0.013], segs=4), M["Tallow"], smooth=True)
        candle(B, M, (0.35, 0.1, 0.0), h=0.3, r=0.04, rng=rng)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

def make_bg_near(kit):
    """Catacomb wall: skull niches, rib arches, stairs (~20 x 10 m)."""
    M = kit.M

    def fn():
        rng = random.Random(601)
        B = Builder(kit.name("BG_Near"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGStone"])
        S = M["BGStone"]
        top = [(10, 8.2), (8.5, 8.8), (7.0, 8.4), (5.5, 9.6), (3.5, 9.3), (2.0, 10.0), (0.0, 9.6), (-2.5, 9.9),
               (-4.0, 9.2), (-6.0, 9.5), (-8.0, 8.6), (-10, 9.0)]
        pts = list(reversed(top))
        for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
            B.add(bm_prism_xz([(x0, 0.0), (x1, 0.0), (x1, z1), (x0, z0)], 0.0, 2.4), S, tint=tint(rng))
        for cx in (-5.5, 4.5):
            pts_ = [(cx - 1.8, -1.0), (cx + 1.8, -1.0)] + [(cx + 1.8 * math.cos(a), 4.2 + 1.8 * 1.3 * math.sin(a))
                                                          for a in lin(0, math.pi, 11)]
            cut.hole(bm_prism_xz(pts_, -1.0, 4.0))
            for s in (-1, 1):
                p = rib_curve((cx + s * 2.15, 0.0, 0.0), (cx + s * 0.25, 0.0, 7.0), (s * 0.9, -0.6, 0.4), n=10)
                rib_bone(cut.post, M["BGBone"], p, 0.28, 0.16, flatten=0.6, segs=8)
        for row in range(3):
            for k in range(9):
                x = -8.6 + k * 2.15 + (1.07 if row % 2 else 0.0)
                if any(abs(x - c) < 2.4 for c in (-5.5, 4.5)) or x > 9.0:
                    continue
                z = 1.0 + row * 2.3
                poly = [(x + 0.45 * math.cos(a), z + 0.45 * math.sin(a) * 0.9) for a in lin(0, TAU, 11)[:-1]]
                if (k + row) % 4 == 0:
                    cut.window(poly, 0.0, 0.35)
                else:
                    cut.hole(bm_prism_xz(poly, -1.0, 0.35))
                    sk, jaw = bk.bm_skull((x, 0.12, z - 0.06), rng, size=3.6, segs=(8, 6))
                    cut.post.add(sk, M["BGBone"])
                    jaw.free()
        for k in range(5):
            bk.bg_box(cut.post, rng, (-1.2 + 0.0, -0.6 - k * 0.5, k * 0.0), (1.4, -0.1 - k * 0.5 + 0.5, 0.35 * (5 - k)),
                      M["BGBone"], 0.04)
        cut.breakage((7.5, 0.6, 8.8), (1.4, 1.2, 1.0), rng, n=2)
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_a(kit):
    """Petrified leviathan rib cage: rib pairs receding in depth like the
    arches of a cathedral nave, spine along the top (~22 m)."""
    M = kit.M

    def fn():
        rng = random.Random(611)
        B = Builder(kit.name("BG_Far_A"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGStone"])
        ys = lin(0.5, 11.0, 6)
        spine = [Vector((0.0, y, 20.5 - 0.95 * y)) for y in lin(-0.5, 11.5, 10)]
        B.add(bm_tube(spine, [0.5] * 10, segs=8, flatten=0.85), M["BGBone"], tint=tint(rng))
        for i, y in enumerate(ys):
            ztop = 20.5 - 0.95 * y
            vb = bm_lathe([(0.6, -0.4), (0.85, -0.25), (0.85, 0.25), (0.6, 0.4)], segs=8)
            rotate(vb, math.pi / 2, "X")
            translate(vb, (0.0, y, ztop))
            B.add(vb, M["BGBone"], tint=tint(rng))
            spread = 7.2 - 0.95 * i
            for s in (-1, 1):
                pts = []
                for t in lin(0, 1, 12):
                    ang = math.pi * 0.5 * (1 - t)
                    x = s * (0.4 + spread * math.sin(math.pi * 0.5 * t) ** 0.8 - 1.6 * t ** 3)
                    z = ztop * (1 - t) ** 0.9 + 0.0 * t
                    pts.append(Vector((x, y, max(z, 0.0))))
                rib_bone(B, M["BGBone"], pts, 0.42, 0.26, flatten=0.55, segs=8, rng=rng)
        bk.bg_box(B, rng, (-2.6, -0.8, 0.0), (2.6, 3.0, 4.6), M["BGStone"], 0.08)
        roof = bm_lathe([(3.2, 4.6), (0.05, 8.2)], segs=4, phase=math.pi / 4)
        translate(roof, (0, 1.1, 0))
        B.add(roof, M["BGStone"], tint=tint(rng))
        for x in (-1.4, 0.0, 1.4):
            cut.window(bk.win_poly(x, 1.2, 2.7, 0.55, "pointed"), -0.8, 0.35)
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_b(kit):
    """Leviathan skull with a temple carved into it (~18 m)."""
    M = kit.M

    def fn():
        rng = random.Random(621)
        B = Builder(kit.name("BG_Far_B"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGBone"])
        sk = bm_ico((0.0, 3.0, 8.0), 1.0, (8.0, 4.0, 5.6), subdiv=3, rng=rng, jitter=0.03)
        for v in sk.verts:
            if v.co.z < 7.0 and v.co.y < 3.0:
                v.co.y += (7.0 - v.co.z) * 0.25
        bm_cut(sk, (0, 0, 3.4), (0, 0, -1))
        B.add(sk, M["BGBone"], tint=tint(rng))
        jaw = bm_ico((1.0, 2.5, 2.6), 1.0, (7.5, 3.2, 2.0), subdiv=2, rng=rng, jitter=0.04)
        bm_cut(jaw, (0, 0, 0.0), (0, 0, -1))
        B.add(jaw, M["BGBone"], tint=tint(rng))
        for k, x in enumerate(lin(-5.5, 6.5, 10)):
            L = 1.2 if k % 2 else 1.8
            th = bm_lathe([(0.32, 0.0), (0.28, L * 0.5), (0.02, L)], segs=6)
            rotate(th, math.pi, "X")
            translate(th, (x, -0.2 + abs(x) * 0.05, 3.9))
            cut.post.add(th, M["BGBone"])
        for sx in (-3.2, 3.2):
            poly = [(sx + 1.3 * math.cos(a), 9.6 + 1.0 * math.sin(a)) for a in lin(0, TAU, 13)[:-1]]
            cut.window(poly, -1.0, 0.6)
        cut.window(bk.win_poly(0.0, 4.0, 6.4, 1.6, "pointed"), -0.6, 0.5)
        for x in (-6.0, 5.6):
            bk.bg_box(cut.post, rng, (x - 0.7, 1.0, 12.0), (x + 0.7, 2.4, 15.5), M["BGStone"], 0.05)
            roof = bm_lathe([(1.1, 15.5), (0.05, 17.8)], segs=4, phase=math.pi / 4)
            translate(roof, (x, 1.7, 0))
            cut.post.add(roof, M["BGStone"])
        return bk.finish_bg(B, cut, keep_back=True)

    return fn


# ---------------------------------------------------------------------------

def chunk_extras(put):
    put("RibArch", (5.5, 1.75, 2.0), s=0.9)
    for z in (4, 6):
        put("SkullWall", (-2.0, 1.96, z), s=0.5)


def make_kit():
    kit = bk.Kit(ID)
    kit.make_materials = materials
    kit.chunk_extras = chunk_extras
    kit.chunk_bg = "#0F0C0A"
    kit.light = dict(key=2.6, rim=2.6)
    kit.emission = {"candle flames": FLAME, "tallow (faint)": "#2E7A3A", "BG windows/niches": FLAME}
    for role in ("Fill_A", "Fill_B", "Fill_C", "Top_A", "Top_B", "Edge_L"):
        kit.add(role, make_tile(kit, role), 1.6, 1500, "1x1 tile, pivot bottom-left, top y=1, front z=-0.9"
                + (" ; bone-powder lip" if role[0] in "TE" else ""), tile=True)
    kit.add("Edge_R", bk.mirror_tile(make_tile(kit, "Edge_L"), kit.name("Edge_R")), 1.6, 1500,
            "right platform end (mirror of Edge_L)", tile=True)
    kit.add("Platform", make_platform(kit), 1.5, 1500, "one-way bone beam: two flat-topped long bones lashed, deck y=1")
    kit.add("BackWall", make_backwall(kit), 0.75, 3600, "4x4 umber catacomb wall with inlaid bones, seamless")
    kit.add("SkullWall", make_skull_wall(kit), 0.7, 3600, "4x4 back-wall variant: skull + femur rows, seamless")
    kit.add("Pillar", make_pillar(kit), 0.9, 6000, "vertebral column on marble plinth, skull crown, candles")
    kit.add("Arch", make_arch(kit), 0.85, 6000, "marble arch 6 m with rib-bone fan and impost candles")
    kit.add("RibArch", make_rib_arch(kit), 0.6, 6000, "leviathan rib arch, 8 m span, ~7.3 m tall, pivot bottom-centre")
    kit.add("Light", make_light(kit), 2.0, 4000, "candle shrine; LightSocket = tallest flame (green)")
    kit.add("Hang", make_hang(kit), 1.4, 4000, "rope of vertebrae ending in a skull, pivot at top, ~2.6 m")
    kit.add("Door", make_door(kit), 1.1, 6000, "doorway: femur jambs, jawbone lintel, skulls, recess 0.78 m")
    kit.add("Prop_A", make_prop_a(kit), 1.3, 4000, "skull pile with candles")
    kit.add("Prop_B", make_prop_b(kit), 1.3, 4000, "broken marble stairs")
    kit.add("Prop_C", make_prop_c(kit), 1.3, 4000, "reliquary urn with skull finial")
    kit.add("BG_Near", make_bg_near(kit), 1.0, 10000, "catacomb wall 20x10 m with skull niches (Unity z=5)",
            atlas="BG")
    kit.add("BG_Far_A", make_bg_far_a(kit), 1.0, 10000, "leviathan rib cage ~22 m (Unity z=10)", atlas="BG")
    kit.add("BG_Far_B", make_bg_far_b(kit), 1.0, 10000, "leviathan skull temple ~18 m (Unity z=16)", atlas="BG")
    return kit
