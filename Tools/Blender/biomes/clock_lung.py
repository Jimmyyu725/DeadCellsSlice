"""The Clockmaker's Lung: a cathedral-sized mechanical organ.  Riveted iron
plates, brass and copper machinery, steam pipes, giant gears, furnaces
glowing with crushed starlight (white-gold and teal)."""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import biome_kit as bk
import env_helpers as eh
from biome_kit import TF, TB, G, X, Y, Z, rad, lin, hex_mix, tint, material
from env_helpers import (Builder, block, bm_blob, bm_box, bm_cut, bm_ico, bm_lathe, bm_prism_xz, bm_tube,
                         delete_faces, rotate, scale, transform, translate)

ID = "ClockLung"
GOLD = "#FFE6A0"
TEAL = "#5FFFE0"
TAU = math.tau


def materials(kit):
    M = kit.M
    plate = dict(rough=0.5, rough_var=0.15, metal=0.75, noise_scale=3.5, noise_amt=0.45, bevel_radius=0.01,
                 bump_strength=0.3, bump_scale=30.0)
    plate_fx = dict(tint_amt=0.25, blotch=("#1A1A1E", 3.5, 0.18), grime_hex="#3E7A6A", grime_amt=0.5,
                    top_hex="#565C64", top_amt=0.06, bottom_amt=0.3, edge_hex="#8A9098", edge_amt=0.9,
                    edge_radius=0.015, edge_top_bias=0.4, cavity_amt=0.8, cavity_dist=0.08, cavity_hex="#0A0B0D")
    M["Plate"] = material("M_CL_Plate", "#3E4248", "#1F2226", "#5E646C", fx=plate_fx, **plate)
    back = material("M_CL_PlateBack", "#2C2F34", "#16181B", "#40444A", **dict(plate, noise_scale=2.0))
    eh.enhance(back, **dict(plate_fx, edge_hex="#5A6068", edge_amt=0.7, grime_amt=0.4, top_amt=0.2))
    eh.make_periodic(back, 4.0, 4.0)
    M["PlateBack"] = back
    M["Core"] = material("M_CL_Core", "#0E0F12", "#060708", "#18191D", rough=0.8, noise_scale=6.0,
                         fx=dict(cavity_amt=0.4, cavity_dist=0.1))
    cb = material("M_CL_CoreBack", "#0C0D10", "#050607", "#16171A", rough=0.8, noise_scale=3.0)
    eh.make_periodic(cb, 4.0, 4.0)
    M["CoreBack"] = cb
    metal_fx = dict(edge_amt=1.0, edge_radius=0.012, cavity_amt=0.7, cavity_dist=0.05, top_amt=0.2, tint_amt=0.15)
    M["Brass"] = material("M_CL_Brass", "#A8823A", "#5C4318", "#D9B866", rough=0.35, rough_var=0.12, metal=0.9,
                          noise_scale=7.0, bevel_radius=0.01, bump_strength=0.25, bump_scale=40.0,
                          fx=dict(metal_fx, blotch=("#4FA08A", 5.0, 0.14), edge_hex="#F0D890", cavity_hex="#2A1E0A",
                                  top_hex="#D9B866"))
    bb = material("M_CL_BrassBack", "#7A5E2A", "#3E2E12", "#A88A4A", rough=0.4, metal=0.85, noise_scale=3.0)
    eh.enhance(bb, **dict(metal_fx, edge_hex="#C8A860", cavity_hex="#1E1608", top_hex="#A88A4A"))
    eh.make_periodic(bb, 4.0, 4.0)
    M["BrassBack"] = bb
    M["Copper"] = material("M_CL_Copper", "#9A5A36", "#4E2A18", "#C98552", rough=0.38, metal=0.9, noise_scale=6.0,
                           bevel_radius=0.01, bump_strength=0.25, bump_scale=40.0,
                           fx=dict(metal_fx, blotch=("#4FA08A", 4.0, 0.22), edge_hex="#F0A878", cavity_hex="#22100A",
                                   top_hex="#C98552"))
    cpb = material("M_CL_CopperBack", "#6E4028", "#3A1E10", "#9A6040", rough=0.4, metal=0.85, noise_scale=3.0)
    eh.enhance(cpb, **dict(metal_fx, blotch=("#3E7A6A", 3.0, 0.2), edge_hex="#C88A60", cavity_hex="#160A06",
                           top_hex="#9A6040"))
    eh.make_periodic(cpb, 4.0, 4.0)
    M["CopperBack"] = cpb
    M["Verdigris"] = material("M_CL_Verdigris", "#4FA08A", "#2A6A5A", "#8AD8C0", rough=0.85, noise_scale=14.0,
                              noise_amt=0.75, bevel_radius=0.02, bump_strength=0.55, bump_scale=45.0,
                              fx=dict(blotch=("#A8F0D8", 18.0, 0.14), cavity_amt=0.6, cavity_dist=0.05,
                                      cavity_hex="#163A30", bottom_amt=0.35, top_hex="#7AC8B0", top_amt=0.12))
    M["Glow"] = material("M_CL_Glow", "#FFE8B0", "#F0C060", "#FFF6DC", rough=0.3, noise_scale=8.0, emission=GOLD,
                         emission_strength=5.0)
    M["Teal"] = material("M_CL_Teal", "#A8FFF0", "#5FD8C0", "#E0FFFA", rough=0.2, noise_scale=8.0, emission=TEAL,
                         emission_strength=4.0)
    M["Gauge"] = material("M_CL_Gauge", "#D8E8E0", "#9AB0A8", "#F0FAF6", rough=0.3, noise_scale=10.0,
                          emission="#3FA090", emission_strength=1.5)
    M["Dark"] = material("M_CL_Dark", "#0C0D10", "#050607", "#18191D", rough=0.8, noise_scale=2.5,
                         fx=dict(cavity_amt=0.6, cavity_dist=0.25, tint_amt=0.15))
    M["BGMetal"] = material("M_CL_BGMetal", "#2A2622", "#16130F", "#423A30", rough=0.6, metal=0.6, noise_scale=0.8,
                            bevel_radius=0.06, bump_strength=0.3, bump_scale=4.0,
                            fx=dict(top_hex="#5A4E3E", top_amt=0.35, bottom_amt=0.3, edge_hex="#6E604A", edge_amt=0.75,
                                    edge_radius=0.15, cavity_amt=0.6, cavity_dist=1.0, cavity_hex="#0A0806",
                                    tint_amt=0.2, brick=(1.4, 1.0, "#100D0A")))
    M["BGBrass"] = material("M_CL_BGBrass", "#5E4820", "#30240E", "#8A6C34", rough=0.4, metal=0.85, noise_scale=1.5,
                            fx=dict(edge_hex="#B8944E", edge_amt=0.8, edge_radius=0.1, top_hex="#8A6C34", top_amt=0.35,
                                    cavity_amt=0.6, cavity_dist=0.8))
    M["BGWindow"] = material("M_CL_BGWindow", "#6A5A30", "#3A3018", "#9A8448", noise_scale=2.0, emission=GOLD,
                             emission_strength=2.0)
    M["BGTeal"] = material("M_CL_BGTeal", "#3A8A80", "#1E4A44", "#6AC8B8", noise_scale=2.0, emission=TEAL,
                           emission_strength=2.0)


# ---------------------------------------------------------------------------
# Shared bits
# ---------------------------------------------------------------------------

def rivet_row(B, M, p0, p1, n, r=0.016, facing=Vector((0, -1, 0)), mat=None, segs=5):
    p0, p1 = Vector(p0), Vector(p1)
    for k in range(n):
        p = p0.lerp(p1, (k + 0.5) / n)
        B.add(bk.dome_rivet(p, r=r, facing=facing, segs=segs), mat or M["Brass"], smooth=True)


def gauge(B, M, center, r=0.09, facing=Vector((0, -1, 0)), needle_a=0.6):
    c = Vector(center)
    m = eh.look_matrix(c, c + Vector(facing))
    rim = bm_lathe([(r, -0.03), (r * 1.08, 0.0), (r * 1.02, 0.02), (r * 0.9, 0.02)], segs=12)
    B.add(transform(rim, m), M["Brass"], smooth=True, uvw=1.2)
    face = bm_lathe([(0.0005, 0.0), (r * 0.9, 0.0), (r * 0.9, 0.012), (0.0005, 0.012)], segs=12)
    B.add(transform(face, m), M["Gauge"], uvw=1.2)
    nd = bm_box((-0.006, -0.004, 0.0), (0.006, 0.004, r * 0.75))
    rotate(nd, needle_a, "Y")
    rotate(nd, -math.pi / 2, "X")
    translate(nd, (0, 0, 0.018))
    B.add(transform(nd, m), M["Plate"])


def valve_wheel(B, M, center, r=0.12, facing=Vector((0, -1, 0)), mat=None):
    c = Vector(center)
    m = eh.look_matrix(c, c + Vector(facing))
    ring = [Vector((r * math.cos(a), r * math.sin(a), 0.0)) for a in lin(0, TAU, 13)[:-1]]
    rb = bm_tube(ring, r * 0.12, segs=5, closed=True, up=Z)
    B.add(transform(rb, m), mat or M["Copper"], smooth=True)
    for k in range(4):
        a = TAU * k / 4 + 0.4
        sp = bm_tube([Vector((0, 0, 0)), Vector((r * math.cos(a), r * math.sin(a), 0))], r * 0.07, segs=4)
        B.add(transform(sp, m), mat or M["Copper"], smooth=True)
    hub = bm_lathe([(r * 0.2, -0.03), (r * 0.2, 0.03)], segs=8)
    B.add(transform(hub, m), M["Brass"])


def plate_block_fn(M, rivets=True, trim=False):
    def fn(B, rng, lo, hi, ctx):
        yf = lo[1] + rng.uniform(-0.012, 0.012)
        pcs = block((lo[0], yf, lo[2]), hi, rng, chips=1 if rng.random() < 0.3 else 0, chip_size=(0.02, 0.05),
                    bevel=0.016, segs=2, jitter=0.0, fixed_top=1.0 if ctx["top"] else None, splits_y=(-0.45,),
                    cuts=ctx["cuts"], back_delete=1.0, bevel_back=1.0)
        t = (rng.uniform(0.3, 0.7), 0.18 if ctx["top"] else rng.uniform(0.0, 0.08), rng.uniform(0.0, 0.3), 1.0)
        B.add(pcs, M["Plate"], tint=t, uvw_fn=bk.tile_uvw)
        if rivets:
            w = hi[0] - lo[0]
            n = max(2, int(w / 0.2))
            for z in (lo[2] + 0.05, hi[2] - 0.05):
                if ctx["top"] and z > 0.9 and trim:
                    continue
                rivet_row(B, M, (lo[0] + 0.03, yf - 0.002, z), (hi[0] - 0.03, yf - 0.002, z), n, r=0.017)
    return fn


TILES = {
    "Fill_A": (1001, [(0.0, 0.5, []), (0.5, 1.0, [])]),
    "Fill_B": (1002, [(0.0, 0.38, []), (0.66, 1.0, [])]),
    "Fill_C": (1003, [(0.0, 0.55, [0.5]), (0.55, 1.0, [])]),
    "Top_A": (1011, [(0.0, 0.46, []), (0.46, 1.0, [])]),
    "Top_B": (1012, [(0.0, 0.6, [0.42]), (0.6, 1.0, [])]),
    "Edge_L": (1021, [(0.0, 0.5, []), (0.5, 1.0, [])]),
}


def make_tile(kit, role):
    M = kit.M
    seed, rows = TILES[role]

    def fn():
        rng = random.Random(seed)
        B = Builder(kit.name(role))
        edge = "L" if role == "Edge_L" else None
        top = role.startswith(("Top", "Edge"))
        bk.tile_body(B, rng, rows, plate_block_fn(M, trim=top), M["Core"], edge=edge, edge_r=0.1, gap=0.03)
        if role == "Fill_B":
            zc = 0.52
            B.add(bm_tube([Vector((0.0, -0.86, zc)), Vector((1.0, -0.86, zc))], 0.095, segs=12, cap=False),
                  M["Copper"], smooth=True, uvw=1.2)
            for x in (0.022, 0.978):
                fl = bm_lathe([(0.097, -0.022), (0.118, -0.016), (0.118, 0.016), (0.097, 0.022)], segs=12)
                rotate(fl, math.pi / 2, "Y")
                translate(fl, (x, -0.86, zc))
                B.add(fl, M["Brass"], hard=40)
            clamp = [Vector((0.5, -0.86 - 0.11 * math.sin(a), zc + 0.11 * math.cos(a))) for a in lin(0, math.pi, 8)]
            B.add(bm_tube(clamp, 0.018, segs=4, flatten=1.0), M["Plate"], smooth=True)
            rivet_row(B, M, (0.48, -0.905, 0.33), (0.52, -0.905, 0.33), 1, r=0.02)
            rivet_row(B, M, (0.48, -0.905, 0.71), (0.52, -0.905, 0.71), 1, r=0.02)
        if role == "Fill_C":
            B.add(delete_faces(bm_box((0.58, TF - 0.0, 0.62), (0.92, TF + 0.06, 0.94)), lambda c, n: n.y > 0.5),
                  M["Dark"], uvw=0.6)
            for k in range(5):
                x = 0.6 + 0.3 * (k + 0.5) / 5
                B.add(bm_box((x - 0.012, TF - 0.03, 0.6), (x + 0.012, TF + 0.0, 0.96)), M["Brass"])
            gauge(B, M, (0.24, TF - 0.035, 0.78), r=0.1, needle_a=rng.uniform(-1, 1))
            pcs = bk.bm_gear(0.2, 0.17, 12, 0.05, spokes=4, y0=TF - 0.03)
            for p in pcs:
                rotate(p, 0.3, "Y")
                translate(p, (0.72, 0.0, 0.28))
            B.add(pcs, M["Brass"], tint=tint(rng), hard=40)
        if top:
            trim = bm_prism_xz([(0.0, 0.93), (1.0, 0.93), (1.0, 1.0), (0.0, 1.0)], TF - 0.03, TF + 0.07)
            if edge:
                for co, no in bk.edge_cuts(0.1):
                    bm_cut(trim, co, no)
            eh.bm_bevel(trim, 0.008, 1)
            B.add(trim, M["Brass"], tint=tint(rng))
            rivet_row(B, M, (0.0, TF - 0.03, 0.965), (1.0, TF - 0.03, 0.965), 5, r=0.013)
            D = bk.lip_cover(B, rng, seed, M["Verdigris"], edge=edge, edge_r=0.1, base=0.08, amp=0.06, dmin=0.04,
                             dmax=0.2, top_depth=0.26, offset=0.016, lump_amp=0.012, lump_freq=8.0,
                             strands=(4, (0.08, 0.28), (0.018, 0.028), M["Verdigris"]), front=-0.94)
            if role == "Top_B":
                st = bm_lathe([(0.06, 0.0), (0.06, 0.12), (0.08, 0.13), (0.08, 0.16), (0.05, 0.165)], segs=10)
                rotate(st, math.pi / 2, "X")
                translate(st, (0.7, -0.88, 0.3))
                B.add(st, M["Copper"], smooth=True, hard=40)
                valve_wheel(B, M, (0.3, -0.93, 0.32), r=0.09)
        bk.clamp_tile(B)
        return B

    return fn


# ---------------------------------------------------------------------------
# Platform / back wall
# ---------------------------------------------------------------------------

def make_platform(kit):
    """Iron grating catwalk with an I-beam and brace."""
    M = kit.M

    def fn():
        rng = random.Random(1031)
        B = Builder(kit.name("Platform"))
        B.add(block((0.0, -0.62, 0.82), (1.0, -0.58, 1.0), rng, bevel=0.006, segs=1, fixed_top=1.0), M["Plate"],
              tint=tint(rng))
        B.add(block((0.0, 0.94, 0.82), (1.0, 0.98, 1.0), rng, bevel=0.006, segs=1, fixed_top=1.0), M["Plate"],
              tint=tint(rng))
        rivet_row(B, M, (0.0, -0.622, 0.91), (1.0, -0.622, 0.91), 5, r=0.014)
        for k in range(10):
            x = (k + 0.5) / 10
            B.add(bm_box((x - 0.012, -0.58, 0.88), (x + 0.012, 0.94, 1.0)), M["Plate"], tint=tint(rng),
                  uvw_fn=lambda c, n: 0.6)
        for y in (-0.2, 0.3, 0.7):
            B.add(bm_box((0.0, y - 0.01, 0.84), (1.0, y + 0.01, 0.88)), M["Plate"], uvw=0.4)
        for (lo, hi) in (((0.46, -0.6, 0.79), (0.54, 0.98, 0.82)), ((0.485, -0.6, 0.66), (0.515, 0.98, 0.79)),
                         ((0.46, -0.6, 0.63), (0.54, 0.98, 0.66))):
            B.add(block(lo, hi, rng, bevel=0.004, segs=1), M["Plate"], tint=tint(rng))
        B.add(bk.beam((0.5, 0.95, 0.2), (0.5, -0.3, 0.64), 0.05, 0.05, rng, bevel=0.006), M["Plate"])
        B.add(block((0.42, 0.9, 0.12), (0.58, 0.98, 0.35), rng, bevel=0.006, segs=1), M["Brass"], tint=tint(rng))
        for z in (0.17, 0.3):
            rivet_row(B, M, (0.44, 0.898, z), (0.56, 0.898, z), 2, r=0.012)
        return B

    return fn


def make_backwall(kit):
    """Large riveted plate panels with raised centres (seamless; pipes would grid at 2x2 tiling)."""
    M = kit.M

    def hook(B, rng, lo, hi, ri, bi):
        w = hi[0] - lo[0]
        n = max(2, int(w / 0.38))
        rivet_row(B, M, (lo[0] + 0.06, lo[1] - 0.004, hi[2] - 0.07), (hi[0] - 0.06, lo[1] - 0.004, hi[2] - 0.07), n,
                  r=0.028, mat=M["BrassBack"], segs=4)

    def fn():
        rng = random.Random(1041)
        B = Builder(kit.name("BackWall"))
        bk.masonry_wall(B, rng, M["PlateBack"], M["CoreBack"], rows=[1.1, 0.9, 1.2, 0.8], width=(1.1, 2.0), gap=0.035,
                        depth=0.3, bevel=0.02, segs=2, chips=(0, 1), front_jitter=0.025, block_hook=hook,
                        inset=(0.08, 0.012), mortar_y=0.12)
        return B

    return fn


# ---------------------------------------------------------------------------
# Pillar / Arch / Door
# ---------------------------------------------------------------------------

def make_pillar(kit):
    """Pipe-bundle column: iron core, three copper pipes, flanges, gauge, valve."""
    M = kit.M

    def fn():
        rng = random.Random(1051)
        B = Builder(kit.name("Pillar"))
        cy = 0.45
        B.add(block((-0.48, 0.0, 0.0), (0.48, 0.9, 0.35), rng, chips=0, bevel=0.02, segs=2, back_delete=0.85),
              M["Plate"], tint=tint(rng))
        rivet_row(B, M, (-0.44, -0.003, 0.28), (0.44, -0.003, 0.28), 6, r=0.018)
        core = bm_lathe([(0.2, 0.35), (0.2, 4.55)], segs=10)
        translate(core, (0, cy, 0))
        B.add(core, M["Plate"], smooth=True, tint=tint(rng))
        for k, a in enumerate((rad(-90), rad(-90 + 120), rad(-90 - 120))):
            px, py = 0.3 * math.cos(a), cy + 0.3 * math.sin(a)
            pp = bm_lathe([(0.11, 0.35), (0.11, 4.55)], segs=10)
            translate(pp, (px, py, 0))
            B.add(pp, M["Copper"] if k == 0 else M["Brass"], smooth=True, tint=tint(rng))
            for z in (1.2, 2.5, 3.8):
                fl = bm_lathe([(0.112, z - 0.035), (0.15, z - 0.025), (0.15, z + 0.025), (0.112, z + 0.035)], segs=10)
                translate(fl, (px, py, 0))
                B.add(fl, M["Brass"], hard=40)
        for z in (0.8, 3.1):
            band = bm_lathe([(0.44, z - 0.06), (0.46, z - 0.04), (0.46, z + 0.04), (0.44, z + 0.06), (0.44, z - 0.06)],
                            segs=12, cap_top=False, cap_bottom=False)
            translate(band, (0, cy, 0))
            B.add(band, M["Plate"], hard=40)
        gauge(B, M, (0.0, cy - 0.47, 2.0), r=0.12, needle_a=0.8)
        valve_wheel(B, M, (0.0, cy - 0.47, 1.55), r=0.14)
        cap = bm_lathe([(0.44, 4.55), (0.48, 4.65), (0.48, 4.8), (0.42, 4.85), (0.2, 4.95), (0.06, 5.0)], segs=12)
        translate(cap, (0, cy, 0))
        B.add(cap, M["Brass"], smooth=True, tint=tint(rng), hard=40)
        B.add(bm_blob((0, cy, 5.0), 0.07, segs=8, rings=5), M["Teal"], smooth=True)
        return B

    return fn


def truss_arc(B, M, cz, r0, r1, y0, y1, n=14, mat=None):
    mat = mat or M["Plate"]
    for r in (r0, r1):
        pts = [Vector((r * math.cos(a), 0, cz + r * math.sin(a))) for a in lin(0, math.pi, 20)]
        for y in (y0, y1):
            B.add(bm_tube([p + Vector((0, y, 0)) for p in pts], 0.07, segs=4, twist=math.pi / 4), mat, hard=30)
    for k in range(n):
        a0 = math.pi * k / n
        a1 = math.pi * (k + 1) / n
        p0 = Vector((r0 * math.cos(a0), (y0 + y1) / 2, cz + r0 * math.sin(a0)))
        p1 = Vector((r1 * math.cos(a1 if k % 2 else a0), (y0 + y1) / 2, cz + r1 * math.sin(a1 if k % 2 else a0)))
        B.add(bm_tube([p0, p1], 0.035, segs=4), mat, hard=30)


def make_arch(kit):
    """Riveted girder portal with a curved truss and a gear in the crown."""
    M = kit.M

    def fn():
        rng = random.Random(1061)
        B = Builder(kit.name("Arch"))
        cz = 2.7
        for s in (-1, 1):
            x0, x1 = sorted((s * 2.15, s * 2.95))
            B.add(block((x0 - 0.05, -0.1, 0.0), (x1 + 0.05, 0.8, 0.35), rng, bevel=0.02, segs=2, back_delete=0.75),
                  M["Plate"], tint=tint(rng))
            for (lo, hi) in (((x0, -0.05, 0.35), (x1, 0.05, cz)), ((x0, 0.55, 0.35), (x1, 0.65, cz)),
                             ((x0 + 0.33, 0.05, 0.35), (x1 - 0.33, 0.55, cz))):
                B.add(block(lo, hi, rng, bevel=0.008, segs=1), M["Plate"], tint=tint(rng))
            for z in lin(0.6, cz - 0.2, 6):
                rivet_row(B, M, (x0 + 0.04, -0.054, z), (x1 - 0.04, -0.054, z), 3, r=0.017)
            B.add(block((x0 - 0.08, -0.12, cz - 0.05), (x1 + 0.08, 0.7, cz + 0.12), rng, bevel=0.012, segs=1),
                  M["Brass"], tint=tint(rng))
            pp = bm_lathe([(0.07, 0.35), (0.07, cz - 0.05)], segs=8)
            translate(pp, (s * 2.05, 0.3, 0))
            B.add(pp, M["Copper"], smooth=True)
        truss_arc(B, M, cz, 2.1, 2.62, 0.05, 0.55, n=16)
        pcs = bk.bm_gear(0.75, 0.66, 18, 0.12, spokes=6, y0=-0.05)
        for p in pcs:
            rotate(p, 0.2, "Y")
            translate(p, (0.0, 0.0, cz + 2.45))
        B.add(pcs, M["Brass"], tint=tint(rng), hard=40)
        B.add(bm_blob((0, -0.08, cz + 2.45), 0.12, (1, 0.6, 1), segs=8, rings=5), M["Teal"], smooth=True)
        B.add(bm_tube([Vector((0, 0.3, cz + 2.1)), Vector((0, 0.3, cz + 1.0))], 0.012, segs=4), M["Plate"])
        lamp = bm_lathe([(0.05, 0.0), (0.12, -0.05), (0.14, -0.12), (0.08, -0.16)], segs=10)
        translate(lamp, (0, 0.3, cz + 1.0))
        B.add(lamp, M["Brass"], smooth=True)
        B.add(bm_blob((0, 0.3, cz + 0.82), 0.075, segs=8, rings=5), M["Glow"], smooth=True)
        return B

    return fn


def make_door(kit):
    """Riveted bulkhead with a hatch swung open, wheel lock, teal warning lamps."""
    M = kit.M

    def fn():
        rng = random.Random(1071)
        B = Builder(kit.name("Door"))
        r_c = 0.35

        def rounded_rect(w, h, r, z0, n=5):
            pts = []
            for (cx, cz, a0) in ((w - r, z0 + r, -90), (w - r, z0 + h - r, 0), (-w + r, z0 + h - r, 90), (-w + r, z0 + r, 180)):
                for a in lin(rad(a0), rad(a0 + 90), n):
                    pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
            return pts

        outer = rounded_rect(1.2, 3.2, 0.5, 0.0)
        inner = rounded_rect(0.8, 2.7, r_c, 0.12)
        for i in range(len(outer)):
            j = (i + 1) % len(outer)
            seg = bm_prism_xz([outer[i], outer[j], inner[j], inner[i]], -0.05, 0.4)
            B.add(seg, M["Plate"], tint=(0.5, 0.0, 0.1, 1.0), hard=25)
        for k in range(0, len(outer), 2):
            p = Vector(outer[k]).lerp(Vector(inner[k]), 0.5)
            B.add(bk.dome_rivet((p.x, -0.052, p.y), r=0.022), M["Brass"], smooth=True)
        trim_o = rounded_rect(0.86, 2.8, r_c + 0.06, 0.06)
        trim_i = rounded_rect(0.8, 2.7, r_c, 0.12)
        for i in range(len(trim_o)):
            j = (i + 1) % len(trim_o)
            B.add(bm_prism_xz([trim_o[i], trim_o[j], trim_i[j], trim_i[i]], -0.08, -0.04), M["Brass"], hard=25)
        DK = M["Dark"]
        B.add(delete_faces(bm_box((-0.9, 0.72, 0.0), (0.9, 0.78, 2.9)), lambda c, n: n.y > 0.5), DK)
        for s in (-1, 1):
            B.add(delete_faces(bm_box((min(s * 0.8, s * 0.86), 0.38, 0.0), (max(s * 0.8, s * 0.86), 0.74, 2.9)),
                               lambda c, n, s=s: n.x * s > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.38, 2.78), (0.82, 0.74, 2.84)), lambda c, n: n.z > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.38, -0.05), (0.82, 0.74, 0.125)), lambda c, n: n.z < -0.5), DK, uvw=0.6)
        hatch = Builder("tmp")
        hp = rounded_rect(0.78, 2.56, r_c - 0.02, 0.14)
        hb = bm_prism_xz(hp, 0.0, 0.08)
        eh.bm_bevel(hb, 0.012, 1)
        hatch.add(hb, M["Plate"], tint=tint(rng))
        for z in (0.6, 1.4, 2.2):
            hatch.add(bm_box((-0.7, -0.03, z - 0.05), (0.7, 0.0, z + 0.05)), M["Brass"])
            rivet_row(hatch, M, (-0.7, -0.032, z), (0.7, -0.032, z), 6, r=0.013)
        valve_wheel(hatch, M, (0.3, -0.06, 1.42), r=0.16)
        rotate(hatch.bm, rad(-72), "Z", (-0.8, 0.0, 0.0))
        translate(hatch.bm, (0.0, 0.1, 0.0))
        me = bpy.data.meshes.new("tmp_hatch")
        hatch.bm.to_mesh(me)
        hatch.bm.free()
        tmp = bmesh.new()
        tmp.from_mesh(me)
        _merge(B, tmp, hatch.mats)
        bpy.data.meshes.remove(me)
        for z in (0.5, 2.3):
            hg = bm_lathe([(0.05, -0.12), (0.05, 0.12)], segs=8)
            translate(hg, (-0.84, 0.05, z))
            B.add(hg, M["Brass"], smooth=True)
        for s in (-1, 1):
            lm = bm_lathe([(0.07, -0.08), (0.09, -0.04), (0.09, 0.04), (0.07, 0.08)], segs=10)
            rotate(lm, math.pi / 2, "X")
            translate(lm, (s * 1.0, -0.12, 2.95))
            B.add(lm, M["Brass"], smooth=True)
            B.add(bm_blob((s * 1.0, -0.16, 2.95), 0.065, (1, 0.8, 1), segs=8, rings=5), M["Teal"], smooth=True)
        return B

    return fn


def _merge(B, src, mats):
    src.normal_update()
    t_src = src.loops.layers.float_color.get("dc_tint")
    u_src = src.faces.layers.float.get("dc_uvw")
    uv_src = src.loops.layers.uv.get("UVMap")
    h_src = src.faces.layers.int.get("dc_hasuv")
    vmap = {v: B.bm.verts.new(v.co) for v in src.verts}
    for f in src.faces:
        try:
            nf = B.bm.faces.new([vmap[v] for v in f.verts])
        except ValueError:
            continue
        nf.material_index = B._mi(mats[f.material_index])
        nf.smooth = f.smooth
        nf[B.uvw] = f[u_src] if u_src else 1.0
        nf[B.hasuv] = f[h_src] if h_src else 0
        for ln, lo_ in zip(nf.loops, f.loops):
            ln[B.tint] = lo_[t_src] if t_src else eh.NEUTRAL
            if uv_src:
                ln[B.uv].uv = lo_[uv_src].uv
    for e in src.edges:
        if not e.smooth:
            ne = B.bm.edges.get((vmap[e.verts[0]], vmap[e.verts[1]]))
            if ne:
                ne.smooth = False
    src.free()


# ---------------------------------------------------------------------------
# Light / Hang / Props
# ---------------------------------------------------------------------------

def make_light(kit):
    """Starlight lamp: brass wall mount, caged bulb (white-gold), teal ring."""
    M = kit.M

    def fn():
        rng = random.Random(1081)
        B = Builder(kit.name("Light"))
        plate = bm_lathe([(0.11, -0.03), (0.11, 0.0)], segs=8, phase=math.pi / 8)
        rotate(plate, -math.pi / 2, "X")
        translate(plate, (0, 0.0, 0.14))
        B.add(plate, M["Brass"], tint=tint(rng))
        arm = [Vector((0, -0.03, 0.14)), Vector((0, -0.16, 0.16)), Vector((0, -0.26, 0.24)), Vector((0, -0.3, 0.3))]
        B.add(bm_tube(arm, 0.025, segs=8), M["Copper"], smooth=True)
        c = Vector((0, -0.3, 0.42))
        socket = bm_lathe([(0.05, -0.12), (0.06, -0.08), (0.06, -0.05)], segs=10)
        translate(socket, c)
        B.add(socket, M["Brass"], smooth=True)
        B.add(bm_blob(c, 0.075, (1, 1, 1.25), segs=10, rings=7), M["Glow"], smooth=True, uvw=1.2)
        for k in range(5):
            a = TAU * k / 5
            pts = [c + Vector((0.09 * math.cos(a) * math.sin(t), 0.09 * math.sin(a) * math.sin(t), -0.1 * math.cos(t)))
                   for t in lin(0.15, math.pi * 0.95, 6)]
            B.add(bm_tube(pts, 0.006, segs=4), M["Brass"], smooth=True)
        ring = bm_lathe([(0.085, -0.005), (0.1, 0.0), (0.085, 0.005), (0.085, -0.005)], segs=12, cap_top=False,
                        cap_bottom=False)
        translate(ring, c + Vector((0, 0, -0.02)))
        B.add(ring, M["Teal"])
        gauge(B, M, (0.0, -0.032, 0.14), r=0.05, needle_a=-0.5)
        B.sockets["LightSocket"] = tuple(c)
        s = 1.5
        scale(B.bm, s)
        B.sockets["LightSocket"] = tuple(c * s)
        return B

    return fn


def make_hang(kit):
    """Hanging steam line: flanged pipe dropping from the ceiling, valve, cables, drip vent."""
    M = kit.M

    def fn():
        rng = random.Random(1091)
        B = Builder(kit.name("Hang"))
        B.add(bm_lathe([(0.16, -0.04), (0.16, 0.0)], segs=10), M["Plate"])
        pts = [Vector((0, 0, -0.04)), Vector((0, 0, -1.5)), Vector((0.05, 0, -1.75)), Vector((0.25, 0, -1.9)),
               Vector((0.45, 0, -1.95))]
        B.add(bm_tube(pts, 0.07, segs=10), M["Copper"], smooth=True)
        for z in (-0.5, -1.2):
            fl = bm_lathe([(0.072, z - 0.03), (0.1, z - 0.02), (0.1, z + 0.02), (0.072, z + 0.03)], segs=10)
            B.add(fl, M["Brass"], hard=40)
        valve_wheel(B, M, (0.0, -0.12, -0.9), r=0.12)
        B.add(bm_box((-0.05, -0.12, -0.95), (0.05, -0.06, -0.85)), M["Brass"])
        vent = bm_lathe([(0.075, 0.0), (0.11, 0.06), (0.11, 0.1)], segs=10)
        rotate(vent, math.pi / 2, "Y")
        translate(vent, (0.45, 0, -1.95))
        B.add(vent, M["Brass"], smooth=True)
        B.add(bm_blob((0.57, 0, -1.95), 0.06, (0.4, 1, 1), segs=8, rings=5), M["Teal"], smooth=True)
        for k, (dx, L) in enumerate(((-0.18, 2.6), (0.15, 2.3), (-0.08, 2.0))):
            cab = [Vector((dx, 0.08, -0.03)), Vector((dx * 1.3, 0.1, -L * 0.5)), Vector((dx * 0.8 + 0.1, 0.06, -L))]
            B.add(bm_tube(cab, 0.022, segs=5), M["Plate"], smooth=True)
            plug = bm_lathe([(0.032, -0.06), (0.04, 0.0), (0.03, 0.05)], segs=6)
            translate(plug, cab[-1])
            B.add(plug, M["Brass"], smooth=True)
        chainp = bk.chain(B, rng, (0.32, 0.0, -0.04), 1.6, M["Plate"], s=0.7, segs=5, path_pts=10)
        hook = [Vector((0.32, 0, chainp)), Vector((0.32, 0, chainp - 0.1)), Vector((0.36, 0, chainp - 0.2)),
                Vector((0.42, 0, chainp - 0.16)), Vector((0.43, 0, chainp - 0.1))]
        B.add(bm_tube(hook, [0.014, 0.014, 0.013, 0.01, 0.005], segs=5), M["Brass"], smooth=True)
        return B

    return fn


def make_prop_a(kit):
    """Pressure tank on legs with gauges."""
    M = kit.M

    def fn():
        rng = random.Random(1101)
        B = Builder(kit.name("Prop_A"))
        cy = 0.36
        tank = bm_lathe([(0.04, 0.12), (0.2, 0.15), (0.3, 0.25), (0.33, 0.4), (0.33, 0.8), (0.3, 0.95), (0.2, 1.05),
                         (0.05, 1.08)], segs=14)
        translate(tank, (0, cy, 0))
        B.add(tank, M["Copper"], smooth=True, tint=tint(rng), hard=40)
        for z in (0.42, 0.78):
            band = bm_lathe([(0.332, z - 0.03), (0.345, z - 0.02), (0.345, z + 0.02), (0.332, z + 0.03),
                             (0.332, z - 0.03)], segs=14, cap_top=False, cap_bottom=False)
            translate(band, (0, cy, 0))
            B.add(band, M["Brass"], hard=40)
            for a in (rad(-120), rad(-90), rad(-60)):
                B.add(bk.dome_rivet((0.345 * math.cos(a), cy + 0.345 * math.sin(a), z), r=0.012,
                                    facing=Vector((math.cos(a), math.sin(a), 0))), M["Brass"], smooth=True)
        for k in range(3):
            a = TAU * k / 3 + 0.4
            B.add(bm_tube([Vector((0.25 * math.cos(a), cy + 0.25 * math.sin(a), 0.2)),
                           Vector((0.36 * math.cos(a), cy + 0.36 * math.sin(a), 0.0))], 0.03, segs=5), M["Plate"],
                  smooth=True)
        gauge(B, M, (0.0, cy - 0.34, 0.62), r=0.1, needle_a=1.0)
        gauge(B, M, (0.22, cy - 0.26, 0.92), r=0.06, facing=Vector((0.5, -1, 0.3)), needle_a=-0.6)
        pp = [Vector((0, cy, 1.07)), Vector((0, cy, 1.18)), Vector((0.1, cy, 1.22)), Vector((0.3, cy, 1.18))]
        B.add(bm_tube(pp, 0.035, segs=8), M["Brass"], smooth=True)
        valve_wheel(B, M, (0.12, cy, 1.25), r=0.07, facing=Z)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


def make_prop_b(kit):
    """Crate spilling brass gears."""
    M = kit.M

    def fn():
        rng = random.Random(1111)
        B = Builder(kit.name("Prop_B"))
        B.add(block((-0.45, 0.15, 0.0), (0.25, 0.75, 0.45), rng, bevel=0.01, segs=1), M["Plate"], tint=tint(rng))
        for (lo, hi) in (((-0.47, 0.13, 0.4), (0.27, 0.77, 0.46)), ((-0.47, 0.13, 0.0), (0.27, 0.77, 0.06))):
            B.add(block(lo, hi, rng, bevel=0.006, segs=1), M["Brass"], tint=tint(rng))
        rivet_row(B, M, (-0.43, 0.128, 0.43), (0.23, 0.128, 0.43), 5, r=0.012)
        rivet_row(B, M, (-0.43, 0.128, 0.03), (0.23, 0.128, 0.03), 5, r=0.012)
        for (c, r, teeth, rx, rz) in (((-0.15, 0.45, 0.5), 0.2, 12, rad(70), 0.0), ((0.12, 0.5, 0.52), 0.15, 10, rad(55), 0.6),
                                      ((0.45, 0.25, 0.04), 0.24, 14, rad(88), 0.3), ((0.3, -0.05, 0.03), 0.12, 9, rad(90), 0.0),
                                      ((0.48, 0.55, 0.2), 0.2, 12, rad(15), 1.2)):
            pcs = bk.bm_gear(r, r * 0.86, teeth, 0.04, spokes=4, y0=-0.02)
            for p in pcs:
                rotate(p, rx, "X")
                rotate(p, rz, "Z")
                translate(p, c)
            B.add(pcs, M["Brass"], tint=tint(rng), hard=40)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), -min(v.co.z for v in B.bm.verts)))
        return B

    return fn


def make_prop_c(kit):
    """Organ-pipe stubs on a riveted plinth, one mouth glowing teal, one pipe toppled."""
    M = kit.M

    def fn():
        rng = random.Random(1121)
        B = Builder(kit.name("Prop_C"))
        B.add(block((-0.5, 0.1, 0.0), (0.5, 0.7, 0.25), rng, bevel=0.012, segs=2), M["Plate"], tint=tint(rng))
        B.add(block((-0.52, 0.08, 0.2), (0.52, 0.72, 0.26), rng, bevel=0.006, segs=1), M["Brass"], tint=tint(rng))
        rivet_row(B, M, (-0.46, 0.098, 0.1), (0.46, 0.098, 0.1), 6, r=0.014)
        for k, (x, h, r) in enumerate(((-0.28, 0.92, 0.1), (0.02, 1.15, 0.125), (0.3, 0.72, 0.09))):
            body = bm_lathe([(0.03, 0.26), (r, 0.4), (r, h), (r * 1.12, h + 0.03), (r * 1.12, h + 0.07), (r * 0.85, h + 0.08)],
                            segs=12)
            translate(body, (x, 0.4, 0))
            B.add(body, M["Brass"] if k != 1 else M["Copper"], smooth=True, tint=tint(rng), hard=40)
            mouth = bm_prism_xz([(x - r * 0.55, 0.5), (x + r * 0.55, 0.5), (x + r * 0.45, 0.64), (x - r * 0.45, 0.64)],
                                0.4 - r - 0.012, 0.4 - r + 0.04)
            B.add(mouth, M["Teal"] if k == 1 else M["Dark"])
        lying = bm_lathe([(0.09, 0.0), (0.09, 0.62), (0.1, 0.65), (0.1, 0.69), (0.075, 0.7)], segs=12)
        rotate(lying, math.pi / 2, "Y")
        rotate(lying, rad(-14), "Z")
        translate(lying, (-0.45, 0.0, 0.09))
        B.add(lying, M["Brass"], smooth=True, hard=40)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


# ---------------------------------------------------------------------------
# Signature: gear and furnace
# ---------------------------------------------------------------------------

def make_gear(kit):
    """Giant brass gear, diameter 3.2 m, pivot at the axle centre (rotate about Unity Z)."""
    M = kit.M

    def fn():
        rng = random.Random(1131)
        B = Builder(kit.name("Gear"))
        pcs = bk.bm_gear(1.6, 1.4, 28, 0.28, r_rim_in=1.12, hub_r=0.32, spokes=6, spoke_w=0.2, y0=-0.14)
        for p in pcs:
            eh.bm_bevel(p, 0.012, 1, min_angle=30)
        B.add(pcs, M["Brass"], tint=tint(rng), hard=35, uvw=0.8)
        for k in range(6):
            a = TAU * k / 6
            B.add(bk.dome_rivet((0.24 * math.cos(a), -0.17, 0.24 * math.sin(a)), r=0.035), M["Plate"], smooth=True)
        axle = bm_lathe([(0.14, -0.3), (0.14, 0.3)], segs=10)
        rotate(axle, -math.pi / 2, "X")
        B.add(axle, M["Plate"], smooth=True)
        cap = bm_lathe([(0.17, 0.0), (0.17, 0.05), (0.1, 0.09)], segs=10)
        rotate(cap, math.pi / 2, "X")
        translate(cap, (0, -0.3, 0))
        B.add(cap, M["Copper"], smooth=True)
        for k in range(12):
            a = TAU * k / 12 + 0.13
            B.add(bk.dome_rivet((1.26 * math.cos(a), -0.142, 1.26 * math.sin(a)), r=0.03), M["Copper"], smooth=True)
        return B

    return fn


def make_furnace(kit):
    """Starlight furnace (~3.6 m with stack); LightSocket at the glowing mouth."""
    M = kit.M

    def fn():
        rng = random.Random(1141)
        B = Builder(kit.name("Furnace"))
        cy = 0.9
        body = bm_lathe([(0.85, 0.0), (0.9, 0.12), (0.9, 1.4), (0.8, 1.75), (0.55, 2.0), (0.3, 2.1)], segs=16)
        translate(body, (0, cy, 0))
        B.add(body, M["Plate"], smooth=True, tint=tint(rng), hard=35, uvw=0.9)
        for z in (0.3, 0.95, 1.5):
            band = bm_lathe([(0.902, z - 0.05), (0.93, z - 0.035), (0.93, z + 0.035), (0.902, z + 0.05),
                             (0.902, z - 0.05)], segs=16, cap_top=False, cap_bottom=False)
            translate(band, (0, cy, 0))
            B.add(band, M["Brass"], hard=40)
            for a in lin(rad(-150), rad(-30), 6):
                B.add(bk.dome_rivet((0.93 * math.cos(a), cy + 0.93 * math.sin(a), z), r=0.02,
                                    facing=Vector((math.cos(a), math.sin(a), 0))), M["Brass"], smooth=True)
        mouth = [(0.42 * math.cos(a), 0.62 + 0.42 * math.sin(a)) for a in lin(0, math.pi, 9)] + [(-0.42, 0.3),
                                                                                              (0.42, 0.3)]
        mouth = [(0.42, 0.3)] + [(0.42 * math.cos(a), 0.62 + 0.42 * math.sin(a)) for a in lin(0, math.pi, 9)] + [(-0.42, 0.3)]
        B.add(delete_faces(bm_prism_xz(mouth, cy - 0.78, cy - 0.5), lambda c, n: n.y < -0.5), M["Glow"], uvw=1.0)
        inner = bm_prism_xz([(0.28 * math.cos(a), 0.6 + 0.24 * math.sin(a)) for a in lin(0, TAU, 13)[:-1]], cy - 0.56,
                            cy - 0.5)
        B.add(inner, M["Teal"], uvw=1.0)
        fr = [(0.5, 0.24), (0.5, 0.62)] + [(0.5 * math.cos(a), 0.62 + 0.5 * math.sin(a)) for a in lin(0, math.pi, 9)[1:-1]] + \
             [(-0.5, 0.62), (-0.5, 0.24)]
        for i in range(len(fr) - 1):
            p0, p1 = Vector((fr[i][0], 0, fr[i][1])), Vector((fr[i + 1][0], 0, fr[i + 1][1]))
            B.add(bk.beam(p0 + Vector((0, cy - 0.86, 0)), p1 + Vector((0, cy - 0.86, 0)), 0.1, 0.12, rng, bevel=0.008),
                  M["Brass"])
        for x in lin(-0.3, 0.3, 5):
            zt = 0.62 + math.sqrt(max(0.42 ** 2 - x * x, 0.0)) - 0.02
            B.add(bm_tube([Vector((x, cy - 0.82, 0.3)), Vector((x, cy - 0.82, zt))], 0.022, segs=6), M["Plate"],
                  smooth=True)
        stack = bm_lathe([(0.28, 2.05), (0.24, 2.4), (0.24, 3.3), (0.32, 3.36), (0.32, 3.5), (0.26, 3.55)], segs=12)
        translate(stack, (0.15, cy + 0.1, 0))
        B.add(stack, M["Copper"], smooth=True, tint=tint(rng), hard=40)
        for s in (-1, 1):
            gauge(B, M, (s * 0.62, cy - 0.66, 1.25), r=0.1, facing=Vector((s * 0.6, -1, 0)), needle_a=s * 0.7)
        valve_wheel(B, M, (0.0, cy - 0.93, 1.25), r=0.16)
        pp = [Vector((-0.85, cy, 1.1)), Vector((-1.15, cy, 1.1)), Vector((-1.25, cy, 0.95)), Vector((-1.25, cy, 0.0))]
        B.add(bm_tube(pp, 0.09, segs=10), M["Copper"], smooth=True)
        B.add(block((-0.95, cy - 0.95, 0.0), (0.95, cy - 0.75, 0.18), rng, bevel=0.012, segs=1), M["Plate"],
              tint=tint(rng))
        off = -min(v.co.y for v in B.bm.verts)
        translate(B.bm, (0, off, 0))
        B.sockets["LightSocket"] = (0.0, cy - 0.6 + off, 0.62)
        return B

    return fn


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

def make_bg_near(kit):
    """Machine wall: girders, giant pipes and gears, furnace windows (~20 x 10 m)."""
    M = kit.M

    def fn():
        rng = random.Random(1201)
        B = Builder(kit.name("BG_Near"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGMetal"])
        S = M["BGMetal"]
        bk.bg_box(B, rng, (-10, 0.4, 0.0), (10, 3.0, 7.6), S, 0.06)
        for x in (-8.5, -3.0, 2.5, 8.0):
            bk.bg_box(B, rng, (x - 0.45, -0.2, 0.0), (x + 0.45, 0.6, 9.4), S, 0.05)
            bk.bg_box(cut.post, rng, (x - 0.7, -0.35, 9.2), (x + 0.7, 0.6, 9.6), M["BGBrass"], 0.03)
        bk.bg_box(B, rng, (-10, -0.3, 7.4), (10, 0.6, 8.1), S, 0.05)
        for (x, z, r) in ((-5.8, 4.6, 2.2), (5.2, 3.6, 2.8)):
            pcs = bk.bm_gear(r, r * 0.88, int(r * 9), 0.4, spokes=6, y0=-0.4)
            for p in pcs:
                rotate(p, rng.uniform(0, 1), "Y")
                translate(p, (x, 0.0, z))
            cut.post.add(pcs, M["BGBrass"])
        for (x0, x1, z, r) in ((-10, 10, 1.4, 0.45), (-10, 10, 6.6, 0.35)):
            cut.post.add(bm_tube([Vector((x0, -0.3, z)), Vector((x1, -0.3, z))], r, segs=8, cap=False), M["BGBrass"],
                         smooth=True)
        for x in (-1.0, 0.4):
            cut.post.add(bm_tube([Vector((x, -0.25, 0.0)), Vector((x, -0.25, 9.8)), Vector((x + 0.8, -0.25, 10.0))],
                                 0.3, segs=8), M["BGBrass"], smooth=True)
        for x in (-7.2, -4.4, 3.8, 6.6):
            cut.window(bk.win_poly(x, 2.6, 3.6, 0.9, "round"), 0.4, 0.35)
        for x in (-1.9, 1.4):
            cut.window([(x - 0.35, 1.0), (x + 0.35, 1.0), (x + 0.35, 1.5), (x - 0.35, 1.5)], 0.4, 0.3)
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_a(kit):
    """Smokestack tower ringed with gears (~24 m)."""
    M = kit.M

    def fn():
        rng = random.Random(1211)
        B = Builder(kit.name("BG_Far_A"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGMetal"])
        S = M["BGMetal"]
        bk.bg_box(B, rng, (-3.5, 0.0, 0.0), (3.5, 6.0, 6.0), S, 0.08, cuts=[((0, 0.8, 6.0), (0, -1, 1))])
        st = bm_lathe([(2.2, 5.5), (1.8, 12.0), (1.5, 20.5), (1.9, 21.0), (1.9, 22.2), (1.6, 22.4)], segs=12)
        translate(st, (0, 3.0, 0))
        B.add(st, S, tint=tint(rng))
        for z in (9.0, 14.0, 18.5):
            ring = bm_lathe([(2.0 - z * 0.022, z - 0.25), (2.0 - z * 0.022, z + 0.25)], segs=12)
            translate(ring, (0, 3.0, 0))
            cut.post.add(ring, M["BGBrass"])
        for (x, z, r) in ((-2.6, 11.5, 1.6), (2.4, 15.5, 1.2), (-1.9, 17.6, 0.9)):
            pcs = bk.bm_gear(r, r * 0.86, int(r * 10), 0.3, spokes=5, y0=0.4)
            for p in pcs:
                translate(p, (x, 0.0, z))
            cut.post.add(pcs, M["BGBrass"])
        for z in (7.5, 12.5, 16.5):
            cut.window(bk.win_poly(0.0, z, z + 1.4, 0.6, "round"), 1.3, 0.4)
        cut.window(bk.win_poly(0.0, 1.2, 3.6, 1.6, "round"), 0.0, 0.45)
        cut.post.add(bm_blob((0.0, 3.0, 23.4), 1.0, (1.6, 1.6, 1.1), segs=8, rings=5, rng=rng, jitter=0.15),
                     M["BGMetal"])
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_b(kit):
    """The Lung: giant accordion bellows between riveted plates (~18 m)."""
    M = kit.M

    def fn():
        rng = random.Random(1221)
        B = Builder(kit.name("BG_Far_B"))
        cut = bk.Cutters(B.name, M["BGTeal"], M["BGMetal"])
        S = M["BGMetal"]
        bk.bg_box(B, rng, (-6.0, 0.0, 0.0), (6.0, 5.0, 3.0), S, 0.08)
        prof = []
        for k in range(13):
            z = 3.0 + k * 1.0
            w = 4.4 if k % 2 == 0 else 3.6
            w *= 1.0 - 0.02 * k
            prof.append((w, z))
        bel = bm_lathe(prof, segs=4, phase=math.pi / 4, scale_xy=(1.0, 0.55))
        translate(bel, (0, 2.5, 0))
        B.add(bel, M["BGMetal"], tint=tint(rng))
        bk.bg_box(B, rng, (-4.8, 0.2, 15.0), (4.8, 4.8, 15.8), M["BGBrass"], 0.05)
        for x in (-3.0, 0.0, 3.0):
            pp = bm_lathe([(0.35, 15.8), (0.35, 17.6), (0.5, 17.8)], segs=8)
            translate(pp, (x, 2.5, 0))
            cut.post.add(pp, M["BGBrass"])
        for x in (-4.6, 4.6):
            cut.post.add(bm_tube([Vector((x, 1.0, 3.0)), Vector((x * 1.15, 1.0, 9.0)), Vector((x, 1.0, 15.0))], 0.3,
                                 segs=6), M["BGBrass"], smooth=True)
        for k in range(1, 12, 2):
            z = 3.0 + k * 1.0
            cut.window([(-2.4, z - 0.15), (2.4, z - 0.15), (2.4, z + 0.15), (-2.4, z + 0.15)], 2.5 - 2.0, 0.6)
        return bk.finish_bg(B, cut, keep_back=False)

    return fn


def make_organ_pipes(kit):
    """Far organ pipe rank in a gothic casing (~20 m)."""
    M = kit.M

    def fn():
        rng = random.Random(1231)
        B = Builder(kit.name("OrganPipes"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGMetal"])
        bk.bg_box(B, rng, (-6.5, 0.0, 0.0), (6.5, 3.0, 3.2), M["BGMetal"], 0.06)
        for s in (-1, 1):
            bk.bg_box(B, rng, (min(s * 6.5, s * 5.6), 0.0, 3.2), (max(s * 6.5, s * 5.6), 3.0, 16.0), M["BGMetal"], 0.05)
            roof = bm_lathe([(0.8, 16.0), (0.05, 19.0)], segs=4, phase=math.pi / 4)
            translate(roof, (s * 6.05, 1.5, 0))
            cut.post.add(roof, M["BGMetal"])
        n = 11
        for k in range(n):
            u = (k - (n - 1) / 2) / ((n - 1) / 2)
            x = u * 4.9
            h = 9.0 + 9.5 * (1 - u * u) ** 0.8
            r = 0.38 + 0.12 * (1 - abs(u))
            y = 0.8 + (0.0 if k % 2 else 0.6)
            foot = bm_lathe([(0.08, 3.2), (r, 4.4)], segs=10)
            translate(foot, (x, y, 0))
            cut.post.add(foot, M["BGBrass"])
            body = bm_lathe([(r, 4.4), (r, h), (r * 1.08, h + 0.1), (r * 1.08, h + 0.25), (r * 0.9, h + 0.28)], segs=10)
            translate(body, (x, y, 0))
            cut.post.add(body, M["BGBrass"], tint=tint(rng))
            mouth = bm_prism_xz([(x - r * 0.55, 4.9), (x + r * 0.55, 4.9), (x + r * 0.5, 5.5), (x - r * 0.5, 5.5)],
                                y - r - 0.05, y - r + 0.08)
            cut.post.add(mouth, M["BGTeal"] if k % 3 == 0 else M["BGMetal"])
        bk.bg_box(cut.post, rng, (-5.6, 0.3, 8.5), (5.6, 0.6, 8.8), M["BGMetal"], 0.03)
        for x in (-2.8, 2.8):
            cut.window(bk.win_poly(x, 1.0, 2.4, 0.9, "pointed"), 0.0, 0.4)
        return bk.finish_bg(B, cut)

    return fn


# ---------------------------------------------------------------------------

def chunk_extras(put):
    put("Gear", (11.6, 1.85, 6.4), s=0.8)
    put("Furnace", (12.3, 0.25, 2.0), s=0.55)


def make_kit():
    kit = bk.Kit(ID)
    kit.make_materials = materials
    kit.chunk_extras = chunk_extras
    kit.chunk_bg = "#120E0A"
    kit.light = dict(key=2.8, rim=2.8)
    kit.emission = {"starlight white-gold": GOLD, "starlight teal": TEAL, "gauges (faint)": "#3FA090"}
    usage = {"Fill_A": "riveted iron plates", "Fill_B": "plates with a copper pipe run (flanges meet across tiles)",
             "Fill_C": "plates with vent grille, gauge and gear", "Top_A": "brass trim, verdigris lip",
             "Top_B": "verdigris lip, pipe stub and valve", "Edge_L": "rounded plate corner"}
    for role in ("Fill_A", "Fill_B", "Fill_C", "Top_A", "Top_B", "Edge_L"):
        kit.add(role, make_tile(kit, role), 1.6, 1500, "1x1 tile, pivot bottom-left, top y=1; " + usage[role],
                tile=True)
    kit.add("Edge_R", bk.mirror_tile(make_tile(kit, "Edge_L"), kit.name("Edge_R")), 1.6, 1500,
            "right platform end (mirror of Edge_L)", tile=True)
    kit.add("Platform", make_platform(kit), 1.5, 1500, "one-way iron grating catwalk, deck top y=1")
    kit.add("BackWall", make_backwall(kit), 0.75, 3600, "4x4 riveted plate wall, seamless")
    kit.add("Pillar", make_pillar(kit), 0.9, 6000, "pipe-bundle column with gauge and valve")
    kit.add("Arch", make_arch(kit), 0.85, 6000, "girder portal with truss arch, crown gear, lamp")
    kit.add("Light", make_light(kit), 2.0, 4000, "starlight lamp; LightSocket = bulb centre (white-gold)")
    kit.add("Hang", make_hang(kit), 1.4, 4000, "hanging steam line, cables and chain hook, pivot top, ~2.6 m")
    kit.add("Door", make_door(kit), 1.1, 6000, "bulkhead with hatch swung open, recess 0.78 m")
    kit.add("Prop_A", make_prop_a(kit), 1.3, 4000, "pressure tank with gauges")
    kit.add("Prop_B", make_prop_b(kit), 1.3, 4000, "crate spilling brass gears")
    kit.add("Prop_C", make_prop_c(kit), 1.3, 4000, "organ-pipe stubs on a plinth, teal mouth")
    kit.add("Gear", make_gear(kit), 0.7, 4000, "giant gear d=3.2 m, pivot = axle centre, rotate about Unity Z")
    kit.add("Furnace", make_furnace(kit), 0.9, 6000, "starlight furnace ~3.6 m; LightSocket at the mouth")
    kit.add("BG_Near", make_bg_near(kit), 1.0, 10000, "machine wall 20x10 m (Unity z=5)", atlas="BG")
    kit.add("BG_Far_A", make_bg_far_a(kit), 1.0, 10000, "smokestack tower with gears ~24 m (z=10)", atlas="BG")
    kit.add("BG_Far_B", make_bg_far_b(kit), 1.0, 10000, "giant bellows lung ~18 m (z=16)", atlas="BG")
    kit.add("OrganPipes", make_organ_pipes(kit), 1.0, 10000, "far organ pipes ~19 m", atlas="BG")
    return kit
