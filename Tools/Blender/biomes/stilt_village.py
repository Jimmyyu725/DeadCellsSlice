"""Stilt Village of the Drowned Chime: wooden pagodas on bird-legged stilts
over a sea of boiling lavender wine.  Wet dark timber, rope lashings,
bronze chimes, glowing paper lanterns, purple wine stains."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

import biome_kit as bk
import env_helpers as eh
from biome_kit import TF, TB, G, X, Y, Z, rad, lin, hex_mix, tint, material
from env_helpers import (Builder, block, bm_blob, bm_box, bm_cut, bm_ico, bm_lathe, bm_prism_xz, bm_tube,
                         delete_faces, rotate, scale, transform, translate)

ID = "StiltVillage"
WARM = "#FFB25A"
TAU = math.tau


def materials(kit):
    M = kit.M
    wood = dict(rough=0.72, rough_var=0.12, noise_scale=6.0, noise_amt=0.6, bevel_radius=0.012, bump_strength=0.45,
                bump_scale=10.0)
    wood_fx = dict(tint_amt=0.22, top_hex="#5E4434", top_amt=0.08, bottom_amt=0.35, edge_hex="#8A6A50",
                   edge_amt=0.75, edge_radius=0.02, cavity_amt=0.75, cavity_dist=0.07, cavity_hex="#0E0807",
                   blotch=("#2A1A14", 4.0, 0.2), grime_hex="#5A2E66", grime_amt=0.4)
    for axis, sc in (("X", (0.1, 2.6, 2.6)), ("Y", (2.6, 0.1, 2.6)), ("Z", (2.6, 2.6, 0.1))):
        m = dc_mat("M_SV_Wood" + axis, "#4E3222", "#24140C", "#76503A", wood)
        eh.stretch_coords(m, sc)
        M["Wood" + axis] = eh.enhance(m, **wood_fx)
    back = dc_mat("M_SV_WoodBack", "#3A261A", "#1E120A", "#563A28", dict(wood, rough=0.82, noise_scale=7.0,
                                                                            noise_amt=0.5))
    eh.stretch_coords(back, (1.0, 1.0, 0.08))
    eh.enhance(back, **dict(wood_fx, edge_hex="#5E4A3E", edge_amt=0.6, top_amt=0.15, grime_amt=0.4))
    eh.make_periodic(back, 4.0, 4.0)
    M["WoodBack"] = back
    M["Core"] = material("M_SV_Core", "#120C0A", "#070403", "#1E1512", rough=0.9, noise_scale=6.0,
                         fx=dict(cavity_amt=0.4, cavity_dist=0.1))
    cb = material("M_SV_CoreBack", "#0F0A08", "#060403", "#1A120F", rough=0.9, noise_scale=3.0)
    eh.make_periodic(cb, 4.0, 4.0)
    M["CoreBack"] = cb
    M["Rope"] = material("M_SV_Rope", "#8A7050", "#4E3C28", "#AA9070", rough=0.95, noise_scale=30.0,
                         stripes=("z", 40, 0.25, "#5A4630"), fx=dict(cavity_amt=0.6, cavity_dist=0.03))
    M["Bronze"] = material("M_SV_Bronze", "#8C6A3A", "#4A3418", "#C49A5A", rough=0.35, metal=0.85, noise_scale=7.0,
                           bevel_radius=0.008,
                           fx=dict(blotch=("#4E8A78", 4.5, 0.3), edge_hex="#E0B878", edge_amt=0.9, edge_radius=0.01,
                                   cavity_amt=0.7, cavity_dist=0.04, cavity_hex="#2A1C0C", top_hex="#C49A5A",
                                   top_amt=0.2))
    M["Iron"] = material("M_SV_Iron", "#2E2A2C", "#151214", "#4E484A", rough=0.5, metal=0.6, noise_scale=7.0,
                         fx=dict(edge_hex="#6A6266", edge_amt=0.7, edge_radius=0.01, blotch=("#6A3A2A", 5.0, 0.25)))
    M["Paper"] = material("M_SV_Paper", "#E6C896", "#C49A60", "#F6E2B8", rough=0.8, noise_scale=12.0,
                          emission=WARM, emission_strength=4.0)
    M["PaperRed"] = material("M_SV_PaperRed", "#B8442C", "#7A2416", "#D86A48", rough=0.8, noise_scale=12.0,
                             emission="#FF7A3A", emission_strength=3.0)
    M["Shingle"] = material("M_SV_Shingle", "#3A2E44", "#1E1626", "#584868", rough=0.6, noise_scale=5.0,
                            stripes=("z", 9.0, 0.12, "#181020"),
                            fx=dict(edge_hex="#76648A", edge_amt=0.7, edge_radius=0.012, cavity_amt=0.7,
                                    cavity_dist=0.05, cavity_hex="#0C0810", top_hex="#584868", top_amt=0.15,
                                    blotch=("#4E7A6A", 6.0, 0.15)))
    M["Stain"] = material("M_SV_Stain", "#5A2E6A", "#341A40", "#8E58A8", rough=0.25, noise_scale=12.0, noise_amt=0.8,
                          bevel_radius=0.02, bump_strength=0.4, bump_scale=40.0,
                          fx=dict(blotch=("#B07ACC", 18.0, 0.15), cavity_amt=0.5, cavity_dist=0.05,
                                  cavity_hex="#1E0E26", top_hex="#9A6AB4", top_amt=0.15, bottom_amt=0.3))
    M["Stone"] = material("M_SV_Stone", "#4A4250", "#26202C", "#6A6074", rough=0.85, noise_scale=3.0,
                          bevel_radius=0.03,
                          fx=dict(edge_hex="#8A8094", edge_amt=0.8, edge_radius=0.04, cavity_amt=0.8, cavity_dist=0.1,
                                  grime_hex="#5A2E66", grime_amt=0.8, tint_amt=0.2))
    M["Lacquer"] = material("M_SV_Lacquer", "#7A2620", "#3E120E", "#A4402E", rough=0.35, noise_scale=5.0,
                            fx=dict(edge_hex="#C8704A", edge_amt=0.8, edge_radius=0.012, cavity_amt=0.6,
                                    cavity_dist=0.05, blotch=("#3A1610", 4.0, 0.2)))
    M["Dark"] = material("M_SV_Dark", "#140D0E", "#070405", "#22171A", rough=0.95, noise_scale=2.5,
                         fx=dict(cavity_amt=0.6, cavity_dist=0.25, tint_amt=0.15))
    M["BGWood"] = material("M_SV_BGWood", "#2A2030", "#150F1A", "#3E3048", rough=0.8, noise_scale=1.0,
                           bevel_radius=0.05, bump_strength=0.3, bump_scale=4.0,
                           fx=dict(top_hex="#4E3E5A", top_amt=0.35, bottom_amt=0.3, edge_hex="#5A4866",
                                   edge_amt=0.7, edge_radius=0.12, cavity_amt=0.6, cavity_dist=1.0,
                                   cavity_hex="#0A060C", tint_amt=0.2))
    M["BGRoof"] = material("M_SV_BGRoof", "#221A2C", "#120C18", "#3A2E48", rough=0.7, noise_scale=1.2,
                           stripes=("z", 3.0, 0.14, "#100A16"),
                           fx=dict(top_hex="#4A3C5A", top_amt=0.35, edge_hex="#5A4866", edge_amt=0.7,
                                   edge_radius=0.15, cavity_amt=0.5, cavity_dist=1.0))
    M["BGWindow"] = material("M_SV_BGWindow", "#5A3A20", "#3A2412", "#7A5030", noise_scale=2.0, emission=WARM,
                             emission_strength=2.0)
    M["BGRope"] = material("M_SV_BGRope", "#4A3A2C", "#2A2018", "#6A5440", rough=0.9)


def dc_mat(name, base, dark, light, kw):
    import dc_common as dc
    return dc.make_material(name, base, dark=dark, light=light, **kw)


# ---------------------------------------------------------------------------
# Shared bits
# ---------------------------------------------------------------------------

def square_roof(center, r0, r1, h, upturn, rings=4, power=1.7, thickness=0.06, aspect=(1.0, 1.0)):
    """Hip roof with a concave sag and upturned corners (pagoda eave).
    r0 = half-width at the eave, r1 at the ridge cap."""
    cx, cy, z0 = center
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    ringsv = []
    for i in range(rings + 1):
        t = i / rings
        r = r0 + (r1 - r0) * t
        z = z0 + h * t ** power
        ring = []
        for k in range(8):
            a = TAU * k / 8
            rr = r * (math.sqrt(2.0) if k % 2 else 1.0)
            zz = z + (upturn * (1 - t) ** 2 if k % 2 else 0.0)
            ring.append(bm.verts.new((cx + math.cos(a) * rr * aspect[0], cy + math.sin(a) * rr * aspect[1], zz)))
        ringsv.append(ring)
    for i in range(rings):
        for k in range(8):
            j = (k + 1) % 8
            f = bm.faces.new((ringsv[i][k], ringsv[i][j], ringsv[i + 1][j], ringsv[i + 1][k]))
            for lp, uv in zip(f.loops, ((k, i), (k + 1, i), (k + 1, i + 1), (k, i + 1))):
                lp[uvl].uv = (uv[0] * 0.25 * r0, uv[1] * 0.25 * h)
    bm.faces.new(ringsv[-1])
    under = [bm.verts.new(v.co - Vector((0, 0, thickness))) for v in ringsv[0]]
    for k in range(8):
        j = (k + 1) % 8
        bm.faces.new((under[k], under[j], ringsv[0][j], ringsv[0][k]))
    bm.faces.new(list(reversed(under)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def rope_wrap(B, M, center, axis, r, turns=3, pitch=0.035, wire=0.012):
    c, ax = Vector(center), Vector(axis).normalized()
    side = ax.cross(Z if abs(ax.dot(Z)) < 0.9 else X).normalized()
    up = ax.cross(side)
    pts = [c + ax * (pitch * t / TAU - pitch * turns / 2) + side * math.cos(t) * r + up * math.sin(t) * r
           for t in lin(0, TAU * turns, turns * 8 + 1)]
    B.add(bm_tube(pts, wire, segs=4), M["Rope"], smooth=True)


def paper_lantern(B, M, center, r=0.16, h=0.34, mat=None, ribs=5, tassel=True):
    c = Vector(center)
    body = bm_lathe([(r * 0.35, -h / 2), (r * 0.85, -h * 0.38), (r, -h * 0.1), (r, h * 0.1), (r * 0.85, h * 0.38),
                     (r * 0.35, h / 2)], segs=12)
    translate(body, c)
    B.add(body, mat or M["Paper"], smooth=True, uvw=1.2)
    for z in lin(-h * 0.38, h * 0.38, ribs):
        rr = r * (1.0 - 0.6 * (abs(z) / (h / 2)) ** 2) + 0.004
        ring = bm_lathe([(rr, z - 0.006), (rr + 0.006, z), (rr, z + 0.006), (rr, z - 0.006)], segs=12, cap_top=False,
                        cap_bottom=False)
        translate(ring, c)
        B.add(ring, M["WoodX"])
    for zc, s in ((h / 2, 1), (-h / 2, -1)):
        cap = bm_lathe([(r * 0.4, 0.0), (r * 0.42, s * 0.03), (r * 0.25, s * 0.045)], segs=10)
        translate(cap, c + Vector((0, 0, zc)))
        B.add(cap, M["WoodX"])
    if tassel:
        B.add(bm_tube([c + Vector((0, 0, -h / 2 - 0.04)), c + Vector((0, 0, -h / 2 - 0.2))], [0.012, 0.025], segs=5),
              M["PaperRed"], smooth=True)
    return c


def chime(B, M, top, n=5, r=0.16, rng=None):
    """Bronze wind chime: wooden disc, tubes of different lengths, clapper."""
    top = Vector(top)
    disc = bm_lathe([(r * 1.1, -0.02), (r * 1.1, 0.02)], segs=12)
    translate(disc, top)
    B.add(disc, M["WoodX"])
    for k in range(n):
        a = TAU * k / n
        L = 0.3 + 0.1 * ((k * 3) % n)
        p = top + Vector((math.cos(a) * r * 0.75, math.sin(a) * r * 0.75, -0.08))
        tube = bm_lathe([(0.018, -L), (0.018, 0.0)], segs=8)
        translate(tube, p)
        B.add(tube, M["Bronze"], smooth=True, tint=tint(rng) if rng else None, uvw=1.2)
        B.add(bm_tube([top + Vector((math.cos(a) * r * 0.75, math.sin(a) * r * 0.75, -0.02)), p], 0.004, segs=3),
              M["Rope"], smooth=True)
    B.add(bm_tube([top + Vector((0, 0, -0.02)), top + Vector((0, 0, -0.42))], 0.005, segs=3), M["Rope"], smooth=True)
    cl = bm_lathe([(0.0005, -0.03), (0.05, -0.01), (0.05, 0.01), (0.0005, 0.03)], segs=10)
    translate(cl, top + Vector((0, 0, -0.32)))
    B.add(cl, M["Bronze"], smooth=True)
    sail = bm_box((-0.05, -0.003, -0.62), (0.05, 0.003, -0.44))
    translate(sail, top)
    B.add(sail, M["PaperRed"])


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------

def timber_block_fn(M, mat_key="WoodX", wet_top=False, rivets=True):
    def fn(B, rng, lo, hi, ctx):
        yf = lo[1] + rng.uniform(-0.02, 0.02)
        pcs = block((lo[0], yf, lo[2]), hi, rng, chips=rng.randint(0, 2), chip_size=(0.02, 0.06), bevel=0.022,
                    segs=2, jitter=0.006, fixed_top=1.0 if ctx["top"] else None, splits_y=(-0.45,),
                    cuts=ctx["cuts"], back_delete=1.0, bevel_back=1.0)
        t = (rng.uniform(0.25, 0.75), 0.45 if (ctx["top"] and wet_top) else rng.uniform(0.0, 0.12),
             rng.uniform(0.0, 0.3), 1.0)
        B.add(pcs, M[mat_key], tint=t, uvw_fn=bk.tile_uvw)
        for x in (lo[0] + 0.06, hi[0] - 0.06):
            if rivets and hi[0] - lo[0] > 0.3:
                B.add(bk.dome_rivet((x, yf - 0.001, (lo[2] + hi[2]) / 2), r=0.016), M["Iron"], smooth=True)
    return fn


def deck_top(B, M, rng, edge=None):
    """Deck boards running front-to-back on a fascia beam (walkable top z=1)."""
    n = 5
    for k in range(n):
        x0 = k / n + 0.008
        x1 = (k + 1) / n - 0.008
        lo = (x0, TF + rng.uniform(-0.015, 0.015), 0.86)
        pcs = block(lo, (x1, TB, 1.0), rng, chips=1, chip_size=(0.015, 0.04),
                    corners=[(-1, -1, 1), (1, -1, 1)], bevel=0.018, segs=1, fixed_top=1.0, splits_y=(-0.45,),
                    back_delete=1.0, bevel_back=1.0,
                    cuts=bk.edge_cuts(0.06) if (edge == "L" and k == 0) else [])
        B.add(pcs, M["WoodY"], tint=(rng.uniform(0.3, 0.8), 0.6, rng.uniform(0, 0.3), 1.0), uvw_fn=bk.tile_uvw)


TILES = {
    "Fill_A": (701, [(0.0, 0.3, []), (0.3, 0.62, [0.55]), (0.62, 1.0, [])]),
    "Fill_B": (702, None),
    "Fill_C": (703, None),
    "Top_A": (711, [(0.0, 0.34, []), (0.34, 0.86, [0.45])]),
    "Top_B": (712, [(0.0, 0.48, [0.6]), (0.48, 0.86, [])]),
    "Edge_L": (721, [(0.0, 0.42, []), (0.42, 0.86, [0.5])]),
}


def crate_wall(B, M, rng):
    core = bm_box((0.04, -0.86, 0.04), (0.96, TB, 0.96))
    delete_faces(core, lambda c, n: n.y > 0.9)
    B.add(core, M["Core"], uvw=0.3)
    for (z0, z1) in ((0.0, 0.5), (0.5, 1.0)):
        zc0, zc1 = z0 + 0.012, z1 - (0.0 if z1 >= 0.999 else 0.012)
        B.add(block((0.015, TF + 0.03, zc0), (0.985, TB, zc1), rng, chips=0, bevel=0.012, segs=1, back_delete=1.0,
                    bevel_back=1.0, splits_y=(-0.45,), fixed_top=1.0 if z1 >= 0.999 else None), M["WoodX"],
              tint=tint(rng), uvw_fn=bk.tile_uvw)
        bt = 0.07
        for lo, hi, mk in (((0.015, TF - 0.01, zc0), (0.015 + bt, TF + 0.04, zc1), "WoodZ"),
                           ((0.985 - bt, TF - 0.01, zc0), (0.985, TF + 0.04, zc1), "WoodZ"),
                           ((0.015 + bt, TF - 0.01, zc0), (0.985 - bt, TF + 0.04, zc0 + bt), "WoodX"),
                           ((0.015 + bt, TF - 0.01, zc1 - bt), (0.985 - bt, TF + 0.04, zc1), "WoodX")):
            B.add(block(lo, hi, rng, bevel=0.008, segs=1), M[mk], tint=tint(rng))
        L = math.hypot(0.97 - 2 * bt, (zc1 - zc0) - 2 * bt)
        ang = math.atan2((zc1 - zc0) - 2 * bt, 0.97 - 2 * bt)
        br = bm_box((-L / 2 - 0.1, -0.015, -0.035), (L / 2 + 0.1, 0.015, 0.035))
        rotate(br, -ang if z0 < 0.4 else ang, "Y")
        bm_cut(br, (0.485 - bt, 0, 0), (1, 0, 0))
        bm_cut(br, (-0.485 + bt, 0, 0), (-1, 0, 0))
        h2 = (zc1 - zc0) / 2 - bt
        bm_cut(br, (0, 0, h2), (0, 0, 1))
        bm_cut(br, (0, 0, -h2), (0, 0, -1))
        eh.bm_bevel(br, 0.006, 1)
        translate(br, (0.5, TF - 0.0, (zc0 + zc1) / 2))
        B.add(br, M["WoodX"], tint=tint(rng))
        for x in (0.05, 0.95):
            for z in (zc0 + 0.035, zc1 - 0.035):
                B.add(bk.dome_rivet((x, TF - 0.01, z), r=0.013), M["Iron"], smooth=True)


def plank_wall(B, M, rng):
    core = bm_box((0.04, -0.86, 0.04), (0.96, TB, 0.96))
    delete_faces(core, lambda c, n: n.y > 0.9)
    B.add(core, M["Core"], uvw=0.3)
    n = 5
    for k in range(n):
        x0, x1 = k / n + 0.01, (k + 1) / n - 0.01
        split = rng.uniform(0.35, 0.65) if k in (1, 3) else None
        spans = [(0.012, split - 0.01), (split + 0.01, 1.0)] if split else [(0.012, 1.0)]
        for (z0, z1) in spans:
            B.add(block((x0, TF + rng.uniform(-0.015, 0.01), z0), (x1, TB, z1), rng, chips=1, chip_size=(0.015, 0.05),
                        bevel=0.014, segs=2, fixed_top=1.0 if z1 >= 0.999 else None, back_delete=1.0, bevel_back=1.0,
                        splits_y=(-0.45,)), M["WoodZ"], tint=tint(rng), uvw_fn=bk.tile_uvw)
    for zc in (0.28, 0.72):
        B.add(block((0.004, TF - 0.05, zc - 0.06), (0.996, TF + 0.02, zc + 0.06), rng, chips=0, bevel=0.012, segs=1),
              M["WoodX"], tint=tint(rng))
        for x in (0.1, 0.5, 0.9):
            B.add(bk.dome_rivet((x, TF - 0.05, zc), r=0.014), M["Iron"], smooth=True)


def make_tile(kit, role):
    M = kit.M
    seed, rows = TILES[role]

    def fn():
        rng = random.Random(seed)
        B = Builder(kit.name(role))
        edge = "L" if role == "Edge_L" else None
        wet = role.startswith(("Top", "Edge"))
        if role == "Fill_B":
            crate_wall(B, M, rng)
        elif role == "Fill_C":
            plank_wall(B, M, rng)
        else:
            bk.tile_body(B, rng, rows, timber_block_fn(M, rivets=not wet), M["Core"], edge=edge, edge_r=0.06)
            if role in ("Fill_A",):
                for x in (0.3, 0.74):
                    pts = [Vector((x + 0.01 * math.sin(t * 9), TF - 0.03 - 0.012 * math.cos(t * TAU * 6),
                                   0.04 + 0.9 * t)) for t in lin(0, 1, 26)]
                    B.add(bm_tube(pts, 0.016, segs=4), M["Rope"], smooth=True)
        if wet:
            deck_top(B, M, rng, edge)
            B.add(block((0.0, TF - 0.035, 0.74), (1.0, TF + 0.06, 0.86), rng, chips=0, bevel=0.012, segs=1,
                        cuts=bk.edge_cuts(0.06) if edge else []), M["WoodX"], tint=(0.3, 0.6, 0.2, 1.0))
            D = bk.lip_cover(B, rng, seed, M["Stain"], edge=edge, edge_r=0.06, base=0.12, amp=0.06, dmin=0.06,
                             dmax=0.24, top_depth=0.25, offset=0.012, lump_amp=0.008, lump_freq=8.0,
                             strands=(4, (0.06, 0.2), (0.022, 0.032), M["Stain"]), front=-0.94)
            if role == "Top_B":
                for k in range(7):
                    x = (k + 0.5) / 7
                    sh = bm_box((-0.075, -0.008, -0.15), (0.075, 0.008, 0.0))
                    rotate(sh, rad(14) + rng.uniform(-0.05, 0.05), "X")
                    rotate(sh, rng.uniform(-0.06, 0.06), "Y")
                    translate(sh, (x, -0.958, 0.995 - (0.02 if k % 2 else 0.0)))
                    eh.bm_bevel(sh, 0.004, 1)
                    B.add(sh, M["Shingle"], tint=tint(rng))
            if edge == "L":
                B.add(block((0.01, TF - 0.06, 0.0), (0.17, TF + 0.12, 1.0), rng, chips=1, bevel=0.02, segs=1,
                            fixed_top=1.0, cuts=bk.edge_cuts(0.06)), M["WoodZ"], tint=tint(rng))
                rope_wrap(B, M, (0.09, TF + 0.03, 0.62), Z, 0.105, turns=2)
        bk.clamp_tile(B)
        return B

    return fn


# ---------------------------------------------------------------------------
# Platform / back wall
# ---------------------------------------------------------------------------

def make_platform(kit):
    M = kit.M

    def fn():
        rng = random.Random(731)
        B = Builder(kit.name("Platform"))
        for i, (y0, y1) in enumerate([(-0.6, -0.12), (-0.09, 0.42), (0.45, 1.0)]):
            x0 = 0.004 + rng.uniform(0.0, 0.01)
            x1 = 0.996 - rng.uniform(0.0, 0.01)
            B.add(block((x0, y0, 0.84), (x1, y1, 1.0), rng, chips=2, chip_size=(0.02, 0.05), bevel=0.016, segs=2,
                        fixed_top=1.0, corners=[(-1, -1, 1), (1, -1, 1), (-1, -1, -1), (1, -1, -1)]), M["WoodX"],
                  tint=(rng.uniform(0.3, 0.7), 0.4 if i == 0 else 0.1, rng.uniform(0, 0.3), 1.0),
                  uvw=1.0 if i == 0 else 0.45)
        for cx in (0.2, 0.8):
            B.add(bk.beam((cx, -0.62, 0.79), (cx, 1.0, 0.79), 0.09, 0.09, rng, bevel=0.012), M["WoodY"], tint=tint(rng))
            loop = [(cx + 0.06 * math.cos(a), -0.3, 0.92 + 0.12 * math.sin(a) - 0.0) for a in lin(0, TAU, 13)[:-1]]
            loop = [(x, y, min(z, 0.996)) for x, y, z in loop]
            B.add(bm_tube(loop, 0.014, segs=4, closed=True, up=Y), M["Rope"], smooth=True)
            tail = [Vector((cx + 0.05, -0.36, 0.84)), Vector((cx + 0.06, -0.38, 0.65)), Vector((cx + 0.04, -0.37, 0.48))]
            B.add(bm_tube(tail, [0.013, 0.012, 0.008], segs=4), M["Rope"], smooth=True)
        B.add(bk.beam((0.5, 0.95, 0.25), (0.5, -0.4, 0.76), 0.08, 0.08, rng, bevel=0.012), M["WoodZ"], tint=tint(rng))
        B.add(block((0.44, 0.88, 0.2), (0.56, 1.0, 0.8), rng, bevel=0.012, segs=1), M["WoodZ"], tint=tint(rng))
        rope_wrap(B, M, (0.5, 0.94, 0.3), Z, 0.08, turns=3)
        return B

    return fn


def make_backwall(kit):
    """Vertical board wall with nailed battens; boards ~0.5-0.8 m so they read at 2x2."""
    M = kit.M

    def fn():
        rng = random.Random(741)
        B = Builder(kit.name("BackWall"))
        P = 4.0
        widths = []
        while sum(widths) < P - 0.8:
            widths.append(rng.uniform(0.5, 0.8))
        rest = P - sum(widths)
        if rest < 0.4:
            widths[-1] += rest
        else:
            widths.append(rest)
        x = 0.0
        for w in widths:
            x0, x1 = x + 0.022, x + w - 0.022
            x += w
            cuts = sorted(rng.uniform(0.8, 3.2) for _ in range(rng.randint(0, 1)))
            zs = [0.0] + cuts + [P]
            d = rng.uniform(-0.03, 0.02)
            for z0, z1 in zip(zs, zs[1:]):
                lo = (x0, d, z0 + (0.015 if z0 > 0 else 0.0))
                hi = (x1, 0.18, z1 - (0.015 if z1 < P else 0.0))
                bm = bm_box(lo, hi)

                def edge_ok(e):
                    return not (all(abs(v.co.z) < 1e-4 for v in e.verts) or all(abs(v.co.z - P) < 1e-4 for v in e.verts))

                eh.bm_bevel(bm, 0.022, 2, edge_filter=edge_ok)
                delete_faces(bm, lambda c, n: n.y > 0.9 or (abs(n.z) > 0.9 and (c.z < 1e-3 or c.z > P - 1e-3)))
                B.add(bm, M["WoodBack"], tint=tint(rng, b=(0.0, 0.4)), uvw_fn=lambda c, n: 0.4 if n.y > 0.5 else 1.0)
        for zc in (1.15, 2.95):
            bm = bm_box((0.0, -0.05, zc - 0.11), (P, 0.04, zc + 0.11))

            def edge_ok2(e):
                return not (all(abs(v.co.x) < 1e-4 for v in e.verts) or all(abs(v.co.x - P) < 1e-4 for v in e.verts))

            eh.bm_bevel(bm, 0.02, 2, edge_filter=edge_ok2)
            delete_faces(bm, lambda c, n: n.y > 0.9 or (abs(n.x) > 0.9))
            B.add(bm, M["WoodBack"], tint=tint(rng))
            xx = 0.0
            for w in widths:
                B.add(bk.dome_rivet((xx + w / 2, -0.05, zc), r=0.022, segs=5), M["Iron"], smooth=True)
                xx += w
        bk.backing_plane(B, M["CoreBack"], P, 0.15)
        return B

    return fn


# ---------------------------------------------------------------------------
# Pillar / Arch / Door
# ---------------------------------------------------------------------------

def make_pillar(kit):
    """Lacquered pagoda column with a bracket set, talismans and rope bands (5 m)."""
    M = kit.M

    def fn():
        rng = random.Random(751)
        B = Builder(kit.name("Pillar"))
        cy = 0.45
        base = bm_lathe([(0.42, 0.0), (0.42, 0.18), (0.36, 0.3), (0.3, 0.34)], segs=10)
        translate(base, (0, cy, 0))
        B.add(base, M["Stone"], tint=tint(rng), hard=40)
        col = bm_lathe([(0.26, 0.3), (0.25, 2.5), (0.23, 4.1)], segs=10)
        translate(col, (0, cy, 0))
        B.add(col, M["Lacquer"], smooth=True, tint=tint(rng))
        for z in (1.1, 2.6):
            rope_wrap(B, M, (0, cy, z), Z, 0.265, turns=4, pitch=0.04, wire=0.016)
        for z, w in ((4.1, 0.3), (4.3, 0.39), (4.52, 0.48)):
            B.add(block((-w, cy - w * 0.7, z), (w, cy + w * 0.7, z + 0.22), rng, chips=0, bevel=0.02, segs=1,
                        cuts=[((0, cy - w * 0.7 + 0.06, z), (0, -1, -1)), ((-w + 0.06, 0, z), (-1, 0, -1)),
                              ((w - 0.06, 0, z), (1, 0, -1))]), M["WoodX"], tint=tint(rng))
        B.add(block((-0.495, cy - 0.42, 4.74), (0.495, cy + 0.42, 4.98), rng, chips=1, bevel=0.025, segs=2), M["WoodX"],
              tint=tint(rng))
        for sx in (-1, 1):
            B.add(block((min(sx * 0.36, sx * 0.49), cy - 0.08, 4.62), (max(sx * 0.36, sx * 0.49), cy + 0.08, 4.74), rng,
                        bevel=0.012, segs=1, cuts=[((sx * 0.49, 0, 4.62 + 0.06), (sx, 0, -1))]), M["WoodX"])
        for k, (a, z) in enumerate(((-1.75, 3.4), (-1.35, 3.1), (-1.6, 1.8))):
            p = Vector((0.27 * math.cos(a), cy + 0.27 * math.sin(a), z))
            tal = bm_box((-0.05, -0.002, -0.16), (0.05, 0.002, 0.0))
            rotate(tal, a + math.pi / 2, "Z")
            translate(tal, p)
            B.add(tal, M["Paper"] if k != 1 else M["PaperRed"], uvw=1.2)
        paper_lantern(B, M, (0.0, cy - 0.5, 4.2), r=0.12, h=0.26)
        B.add(bm_tube([Vector((0, cy - 0.45, 4.74)), Vector((0, cy - 0.5, 4.36))], 0.006, segs=3), M["Rope"])
        return B

    return fn


def make_arch(kit):
    """Torii-like gate: posts, tie beam, upswept lintel, hanging chimes."""
    M = kit.M

    def fn():
        rng = random.Random(761)
        B = Builder(kit.name("Arch"))
        cy = 0.4
        for s in (-1, 1):
            base = bm_lathe([(0.34, 0.0), (0.34, 0.3), (0.28, 0.38)], segs=10)
            translate(base, (s * 2.55, cy, 0))
            B.add(base, M["Stone"], tint=tint(rng), hard=40)
            post = bm_lathe([(0.24, 0.35), (0.22, 3.8), (0.2, 4.9)], segs=10)
            translate(post, (s * 2.55, cy, 0))
            B.add(post, M["Lacquer"], smooth=True, tint=tint(rng))
            rope_wrap(B, M, (s * 2.55, cy, 1.2), Z, 0.245, turns=4, wire=0.016)
            for z in (3.0, 4.4):
                ring = bm_lathe([(0.235, z - 0.05), (0.25, z - 0.03), (0.25, z + 0.03), (0.235, z + 0.05),
                                 (0.235, z - 0.05)], segs=10, cap_top=False, cap_bottom=False)
                translate(ring, (s * 2.55, cy, 0))
                B.add(ring, M["Bronze"], hard=40)
        B.add(block((-3.05, cy - 0.14, 4.0), (3.05, cy + 0.14, 4.32), rng, chips=2, bevel=0.025, segs=2), M["WoodX"],
              tint=tint(rng))
        pts, top = [], []
        for x in lin(-3.25, 3.25, 15):
            u = abs(x) / 3.25
            z = 4.95 + 0.35 * u ** 3
            top.append((x, z))
        poly_lo = [(x, z) for x, z in top]
        bm = bmesh.new()
        front = []
        for (x, z) in poly_lo:
            front.append([bm.verts.new((x, y, zz)) for y, zz in ((cy - 0.22, z), (cy - 0.22, z + 0.26), (cy + 0.22, z + 0.26),
                                                               (cy + 0.22, z))])
        for i in range(len(front) - 1):
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((front[i][k], front[i][j], front[i + 1][j], front[i + 1][k]))
        bm.faces.new(front[0])
        bm.faces.new(list(reversed(front[-1])))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        B.add(bm, M["Lacquer"], tint=tint(rng), hard=30)
        lint = []
        for x in lin(-3.45, 3.45, 15):
            u = abs(x) / 3.45
            lint.append((x, 5.21 + 0.42 * u ** 3))
        bm = bmesh.new()
        rings = [[bm.verts.new((x, y, zz)) for y, zz in ((cy - 0.3, z), (cy - 0.3, z + 0.14), (cy + 0.3, z + 0.14),
                                                       (cy + 0.3, z))] for x, z in lint]
        for i in range(len(rings) - 1):
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        B.add(bm, M["Shingle"], tint=tint(rng), hard=30)
        B.add(block((-0.14, cy - 0.17, 4.32), (0.14, cy + 0.17, 4.96), rng, bevel=0.012, segs=1), M["WoodX"])
        B.add(block((-0.4, cy - 0.2, 4.45), (0.4, cy - 0.16, 4.85), rng, bevel=0.01, segs=1), M["Lacquer"])
        B.add(block((-0.32, cy - 0.215, 4.5), (0.32, cy - 0.2, 4.8), rng, bevel=0.004, segs=1), M["Bronze"])
        for x in (-1.6, -0.6, 0.9, 1.9):
            top_p = Vector((x, cy, 4.0))
            L = rng.uniform(0.25, 0.8)
            B.add(bm_tube([top_p, top_p - Vector((0, 0, L))], 0.006, segs=3), M["Rope"])
            if x in (-0.6, 1.9):
                paper_lantern(B, M, top_p - Vector((0, 0, L + 0.18)), r=0.14, h=0.3)
            else:
                chime(B, M, top_p - Vector((0, 0, L)), n=5, r=0.12, rng=rng)
        return B

    return fn


def make_door(kit):
    """Pagoda doorway: timber frame, glowing shoji panels (one slid open), shingle canopy."""
    M = kit.M

    def fn():
        rng = random.Random(771)
        B = Builder(kit.name("Door"))
        for s in (-1, 1):
            B.add(block((min(s * 0.82, s * 1.06), -0.06, 0.0), (max(s * 0.82, s * 1.06), 0.36, 2.75), rng, chips=2,
                        bevel=0.02, segs=2), M["WoodZ"], tint=tint(rng))
            B.add(block((min(s * 1.06, s * 1.2), 0.0, 0.0), (max(s * 1.06, s * 1.2), 0.36, 2.75), rng, chips=1,
                        bevel=0.015, segs=1), M["WoodZ"], tint=tint(rng))
        B.add(block((-1.25, -0.08, 2.65), (1.25, 0.38, 2.88), rng, chips=2, bevel=0.02, segs=2), M["WoodX"],
              tint=tint(rng))
        B.add(block((-0.84, -0.06, 0.0), (0.84, 0.4, 0.09), rng, chips=1, bevel=0.015, segs=1), M["WoodX"],
              tint=tint(rng))
        roof = square_roof((0.0, 0.05, 2.9), 0.62, 0.12, 0.28, 0.12, rings=3, aspect=(2.1, 0.75))
        bm_cut(roof, (0, 0.62, 0), (0, 1, 0))
        B.add(roof, M["Shingle"], tint=tint(rng), hard=30)
        for (x0, x1, y, open_) in ((-0.8, 0.0, 0.2, False), (0.0, 0.8, 0.26, True)):
            if open_:
                x0, x1 = 0.55, 1.05
            B.add(block((x0 + 0.01, y - 0.012, 0.1), (x1 - 0.01, y + 0.012, 2.64), rng, bevel=0.003, segs=1),
                  M["Paper"], uvw=1.0)
            for xx in lin(x0 + 0.02, x1 - 0.02, 4):
                B.add(bm_box((xx - 0.015, y - 0.03, 0.1), (xx + 0.015, y - 0.012, 2.64)), M["WoodZ"])
            for zz in lin(0.12, 2.62, 7):
                B.add(bm_box((x0 + 0.01, y - 0.03, zz - 0.015), (x1 - 0.01, y - 0.012, zz + 0.015)), M["WoodX"])
        DK = M["Dark"]
        B.add(delete_faces(bm_box((-0.9, 0.72, 0.0), (0.9, 0.78, 2.8)), lambda c, n: n.y > 0.5), DK)
        for s in (-1, 1):
            B.add(delete_faces(bm_box((min(s * 0.8, s * 0.86), 0.36, 0.0), (max(s * 0.8, s * 0.86), 0.74, 2.8)),
                               lambda c, n, s=s: n.x * s > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.36, 2.64), (0.82, 0.74, 2.7)), lambda c, n: n.z > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.36, -0.05), (0.82, 0.74, 0.005)), lambda c, n: n.z < -0.5), DK, uvw=0.6)
        paper_lantern(B, M, (-0.98, -0.25, 2.25), r=0.13, h=0.28, mat=M["PaperRed"])
        B.add(bm_tube([Vector((-0.98, -0.08, 2.65)), Vector((-0.98, -0.25, 2.55)), Vector((-0.98, -0.25, 2.4))], 0.008,
                      segs=3), M["Rope"])
        chime(B, M, (0.95, -0.22, 2.62), n=4, r=0.09, rng=rng)
        return B

    return fn


# ---------------------------------------------------------------------------
# Light / Hang / Props / Stilt
# ---------------------------------------------------------------------------

def make_light(kit):
    M = kit.M

    def fn():
        rng = random.Random(781)
        B = Builder(kit.name("Light"))
        B.add(block((-0.08, -0.06, 0.0), (0.08, 0.0, 0.42), rng, bevel=0.01, segs=1), M["WoodZ"], tint=tint(rng))
        B.add(bk.beam((0.0, -0.03, 0.34), (0.0, -0.46, 0.4), 0.06, 0.06, rng, bevel=0.008), M["WoodY"], tint=tint(rng))
        B.add(bk.beam((0.0, -0.03, 0.1), (0.0, -0.3, 0.37), 0.045, 0.045, rng, bevel=0.006), M["WoodY"])
        rope_wrap(B, M, (0.0, -0.16, 0.36), Y, 0.04, turns=2)
        B.add(bm_tube([Vector((0, -0.42, 0.37)), Vector((0, -0.42, 0.22))], 0.006, segs=3), M["Rope"])
        c = paper_lantern(B, M, (0.0, -0.42, 0.06), r=0.15, h=0.3)
        for x in (-0.05, 0.05):
            B.add(bk.dome_rivet((x, -0.06, 0.06), r=0.012), M["Iron"], smooth=True)
        B.sockets["LightSocket"] = tuple(c)
        s = 1.35
        translate(B.bm, (0, 0, 0.25))
        scale(B.bm, s)
        B.sockets["LightSocket"] = tuple((c + Vector((0, 0, 0.25))) * s)
        return B

    return fn


def make_hang(kit):
    """Rope with two wind chimes and a bronze bell (~2.5 m)."""
    M = kit.M

    def fn():
        rng = random.Random(791)
        B = Builder(kit.name("Hang"))
        B.add(bm_lathe([(0.05, 0.0), (0.05, -0.04), (0.015, -0.06)], segs=8), M["Iron"])
        pts = [Vector((0.02 * math.sin(t * 5), 0, -2.0 * t)) for t in lin(0, 1, 10)]
        B.add(bm_tube(pts, 0.012, segs=5), M["Rope"], smooth=True)
        chime(B, M, (0.0, 0.0, -0.55), n=6, r=0.15, rng=rng)
        chime(B, M, (0.02, 0.0, -1.35), n=5, r=0.12, rng=rng)
        bell = bm_lathe([(0.02, 0.0), (0.06, -0.02), (0.09, -0.12), (0.13, -0.24), (0.15, -0.27), (0.135, -0.27),
                         (0.11, -0.22), (0.07, -0.1), (0.03, -0.03)], segs=14)
        translate(bell, (0.0, 0.0, -2.0))
        B.add(bell, M["Bronze"], smooth=True, uvw=1.3)
        B.add(bm_blob((0, 0, -2.24), 0.04, segs=6, rings=4), M["Bronze"], smooth=True)
        tag = bm_box((-0.06, -0.003, -2.58), (0.06, 0.003, -2.32))
        B.add(tag, M["PaperRed"])
        return B

    return fn


def make_prop_a(kit):
    """Wine barrel with purple overflow."""
    M = kit.M

    def fn():
        rng = random.Random(801)
        B = Builder(kit.name("Prop_A"))
        H, Rm, Re = 0.95, 0.4, 0.34

        def r_at(z):
            u = (z - H / 2) / (H / 2)
            return Rm - (Rm - Re) * u * u

        prof = [(r_at(z), z) for z in lin(0, H, 9)]
        body = bm_lathe(prof, segs=16)
        translate(body, (0, Rm, 0))
        B.add(body, M["WoodZ"], tint=tint(rng), hard=30)
        for k in range(16):
            a = TAU * k / 16
            line = [Vector((r_at(z) * math.cos(a) * 1.004, Rm + r_at(z) * math.sin(a) * 1.004, z)) for z in lin(0.02, H - 0.02, 7)]
            B.add(bm_tube(line, 0.005, segs=3), M["Core"])
        for zc in (0.12, 0.38, 0.62, 0.86):
            r = r_at(zc) + 0.006
            ring = bm_lathe([(r, zc - 0.03), (r + 0.012, zc - 0.028), (r + 0.012, zc + 0.028), (r, zc + 0.03),
                             (r, zc - 0.03)], segs=16, cap_top=False, cap_bottom=False)
            translate(ring, (0, Rm, 0))
            B.add(ring, M["Iron"], hard=40)
        lid = bm_lathe([(Re - 0.03, H - 0.05), (0.001, H - 0.05)], segs=16)
        translate(lid, (0, Rm, 0))
        B.add(lid, M["Stain"], smooth=True)
        for k in range(5):
            a = rng.uniform(math.pi * 1.2, math.pi * 1.8)
            p0 = Vector((Re * math.cos(a), Rm + Re * math.sin(a), H - 0.02))
            L = rng.uniform(0.2, 0.6)
            pts = [p0 + Vector((math.cos(a) * 0.02 * t, math.sin(a) * 0.02 * t, -L * t)) for t in lin(0, 1, 5)]
            B.add(bm_tube(pts, [0.022, 0.02, 0.018, 0.016, 0.02], segs=5, flatten=0.6), M["Stain"], smooth=True)
        sp = bm_lathe([(0.03, 0.0), (0.03, 0.12), (0.02, 0.14)], segs=8)
        transform(sp, eh.look_matrix(Vector((0.0, Rm - r_at(0.25) + 0.02, 0.25)), Vector((0.0, -1.0, 0.25))))
        B.add(sp, M["Bronze"], smooth=True)
        pool = bm_lathe([(0.0005, 0.0), (0.18, 0.004), (0.24, 0.0)], segs=12, scale_xy=(1.4, 1.0))
        translate(pool, (0.05, -0.05, 0.0))
        B.add(pool, M["Stain"], smooth=True)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


def make_prop_b(kit):
    """Rope coil and a bronze bell on a short stand."""
    M = kit.M

    def fn():
        rng = random.Random(811)
        B = Builder(kit.name("Prop_B"))
        pts = []
        for t in lin(0, TAU * 5.5, 120):
            r = 0.12 + 0.035 * (t / TAU)
            z = 0.03 + 0.035 * ((t / TAU) % 1 > 0.92)
            pts.append(Vector((-0.35 + r * math.cos(t), 0.35 + r * math.sin(t), 0.03 + 0.02 * (t / TAU / 5.5) * 3)))
        B.add(bm_tube(pts, 0.03, segs=6), M["Rope"], smooth=True)
        for sx in (-1, 1):
            B.add(bk.beam((0.25 + sx * 0.25, 0.4, 0.0), (0.25 + sx * 0.18, 0.4, 0.95), 0.06, 0.06, rng, bevel=0.008),
                  M["WoodZ"], tint=tint(rng))
        B.add(bk.beam((-0.02, 0.4, 0.92), (0.52, 0.4, 0.92), 0.07, 0.07, rng, bevel=0.01), M["WoodX"], tint=tint(rng))
        bell = bm_lathe([(0.02, 0.0), (0.05, -0.02), (0.08, -0.1), (0.12, -0.22), (0.14, -0.26), (0.125, -0.26),
                         (0.1, -0.2), (0.06, -0.09), (0.02, -0.03)], segs=14)
        translate(bell, (0.25, 0.4, 0.87))
        B.add(bell, M["Bronze"], smooth=True, uvw=1.3)
        B.add(bm_tube([Vector((0.25, 0.4, 0.92)), Vector((0.25, 0.4, 0.86))], 0.012, segs=4), M["Rope"])
        mallet = bk.beam((0.45, 0.1, 0.02), (0.75, 0.25, 0.04), 0.03, 0.03, rng, bevel=0.004)
        B.add(mallet, M["WoodX"])
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


def make_prop_c(kit):
    """Stacked fish baskets and a crate with a glowing lantern."""
    M = kit.M

    def fn():
        rng = random.Random(821)
        B = Builder(kit.name("Prop_C"))
        B.add(block((-0.5, 0.0, 0.0), (0.1, 0.6, 0.5), rng, chips=2, bevel=0.015, segs=2), M["WoodX"], tint=tint(rng))
        for lo, hi in (((-0.5, -0.01, 0.0), (-0.44, 0.04, 0.5)), ((0.04, -0.01, 0.0), (0.1, 0.04, 0.5)),
                       ((-0.44, -0.01, 0.0), (0.04, 0.04, 0.06)), ((-0.44, -0.01, 0.44), (0.04, 0.04, 0.5))):
            B.add(block(lo, hi, rng, bevel=0.006, segs=1), M["WoodZ"], tint=tint(rng))
        for k, (cx, z, r) in enumerate(((0.38, 0.0, 0.24), (0.36, 0.3, 0.2))):
            bk_ = bm_lathe([(r * 0.85, 0.0), (r, 0.08), (r * 1.05, 0.2), (r * 1.08, 0.28)], segs=12)
            translate(bk_, (cx, 0.3, z))
            B.add(bk_, M["Rope"], smooth=True, tint=tint(rng), hard=40)
            rim = bm_lathe([(r * 1.08, 0.27), (r * 1.13, 0.29), (r * 1.08, 0.31), (r * 1.08, 0.27)], segs=12,
                           cap_top=False, cap_bottom=False)
            translate(rim, (cx, 0.3, z))
            B.add(rim, M["WoodX"])
        c = paper_lantern(B, M, (-0.2, 0.3, 0.68), r=0.15, h=0.3)
        B.add(bm_tube([c + Vector((0, 0, 0.17)), c + Vector((0, 0, 0.24))], 0.005, segs=3), M["Rope"])
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


def make_stilt(kit):
    """Bird-like stilt leg, 6 m, pivot at the top, extends down to z=-6."""
    M = kit.M

    def fn():
        rng = random.Random(831)
        B = Builder(kit.name("Stilt"))
        B.add(block((-0.28, -0.28, -0.25), (0.28, 0.28, 0.0), rng, chips=1, bevel=0.02, segs=2), M["WoodX"],
              tint=tint(rng))
        hip, knee, ankle = Vector((0, 0.0, -0.2)), Vector((0, 0.55, -2.5)), Vector((0, -0.15, -5.3))
        thigh = bm_lathe([(0.2, 0.0), (0.18, 0.5), (0.15, 1.6), (0.17, 2.2)], segs=10)
        transform(thigh, eh.look_matrix(hip, knee))
        B.add(thigh, M["WoodZ"], smooth=True, tint=tint(rng))
        shin = bm_lathe([(0.15, 0.0), (0.12, 1.2), (0.1, 2.6), (0.12, 2.8)], segs=10)
        transform(shin, eh.look_matrix(knee, ankle))
        B.add(shin, M["WoodZ"], smooth=True, tint=tint(rng))
        B.add(bm_blob(knee, 0.24, (1.0, 1.1, 1.15), segs=10, rings=7, rng=rng, jitter=0.05), M["WoodX"], smooth=True)
        for p, ax in ((hip.lerp(knee, 0.25), knee - hip), (knee, Vector((0, 1, 0.3))), (knee.lerp(ankle, 0.5), ankle - knee)):
            rope_wrap(B, M, p, ax, 0.2 if p == knee else 0.17, turns=3, wire=0.018)
        for t in (0.75,):
            p = hip.lerp(knee, t)
            ring = bm_lathe([(0.175, -0.04), (0.19, -0.02), (0.19, 0.02), (0.175, 0.04), (0.175, -0.04)], segs=10,
                            cap_top=False, cap_bottom=False)
            transform(ring, eh.look_matrix(p, p + (knee - hip)))
            B.add(ring, M["Iron"], hard=40)
        B.add(bm_blob(ankle, 0.16, (1.0, 1.1, 0.9), segs=8, rings=6), M["WoodX"], smooth=True)
        rock = eh.bm_hull([Vector((rng.uniform(-0.55, 0.55), rng.uniform(-0.6, 0.4), rng.uniform(-6.05, -5.65)))
                           for _ in range(12)] + [Vector((0, -0.1, -6.05))])
        B.add(rock, M["Stone"], tint=tint(rng))
        for k, (dx, dy) in enumerate(((-0.42, -0.4), (0.0, -0.55), (0.42, -0.4), (0.0, 0.42))):
            mid = ankle + Vector((dx * 0.45, dy * 0.45, -0.32))
            tip = ankle + Vector((dx, dy, -0.62))
            pts = [ankle + Vector((0, 0, -0.05)), mid, tip]
            B.add(bm_tube(pts, [0.08, 0.06, 0.04], segs=6), M["WoodZ"], smooth=True)
            claw = bm_lathe([(0.045, 0.0), (0.03, 0.1), (0.002, 0.2)], segs=6)
            transform(claw, eh.look_matrix(tip, tip + Vector((dx * 0.3, dy * 0.3, -0.6))))
            B.add(claw, M["Iron"], smooth=True)
        for k in range(3):
            p = knee.lerp(ankle, 0.2 + 0.25 * k) + Vector((0, -0.12, 0))
            pts = [p, p + Vector((0.02, -0.02, -0.2)), p + Vector((0.0, -0.03, -0.4 - 0.15 * k))]
            B.add(bm_tube(pts, [0.03, 0.025, 0.02], segs=5, flatten=0.6), M["Stain"], smooth=True)
        return B

    return fn


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

def stilt_legs(B, mat, x, y, top, rng, s=1.0):
    knee = Vector((x + 0.2 * s, y + 0.5 * s, top * 0.55))
    B.add(bm_tube([Vector((x, y, top)), knee, Vector((x - 0.1 * s, y - 0.2 * s, 0.0))], [0.16 * s, 0.13 * s, 0.1 * s],
                  segs=6), mat, smooth=True)
    for d in (-1, 0, 1):
        B.add(bm_tube([Vector((x - 0.1 * s, y - 0.2 * s, 0.05)), Vector((x - 0.1 * s + d * 0.5 * s, y - 0.6 * s, -0.0))],
                      [0.07 * s, 0.03 * s], segs=4), mat, smooth=True)


def hut(B, cut, M, rng, cx, y0, z0, w, h, roof_h, depth=2.6):
    bk.bg_box(B, rng, (cx - w / 2, y0, z0), (cx + w / 2, y0 + depth, z0 + h), M["BGWood"], 0.04)
    roof = square_roof((cx, y0 + depth / 2, z0 + h), w * 0.62, 0.12, roof_h, 0.45, rings=3, aspect=(1.0, depth / w))
    cut.post.add(roof, M["BGRoof"], tint=tint(rng))
    cut.window(bk.win_poly(cx, z0 + h * 0.25, z0 + h * 0.65, w * 0.28, "round"), y0, 0.3)


def make_bg_near(kit):
    """Row of stilt huts on a long deck with lanterns and rope bridges (~20 x 10 m)."""
    M = kit.M

    def fn():
        rng = random.Random(901)
        B = Builder(kit.name("BG_Near"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGWood"])
        W = M["BGWood"]
        for (x0, x1, z) in ((-10.0, -3.6, 4.6), (-2.6, 4.2, 5.2), (5.2, 10.0, 4.4)):
            bk.bg_box(B, rng, (x0, 0.0, z - 0.35), (x1, 3.0, z), W, 0.04)
            for x in lin(x0 + 0.5, x1 - 0.5, 4):
                stilt_legs(cut.post, W, x, 0.4, z - 0.3, rng, s=1.2)
        hut(B, cut, M, rng, -7.0, 0.2, 4.6, 3.4, 2.4, 1.8)
        hut(B, cut, M, rng, -4.6, 0.6, 4.6, 1.6, 1.8, 1.0)
        hut(B, cut, M, rng, 0.8, 0.2, 5.2, 4.2, 2.6, 2.2)
        hut(B, cut, M, rng, 7.6, 0.3, 4.4, 3.0, 2.2, 1.6)
        for (p0, p1, dz) in (((-3.6, 0.4, 4.7), (-2.6, 0.4, 5.3), 0.3), ((4.2, 0.4, 5.3), (5.2, 0.4, 4.5), 0.35)):
            cut.post.add(bm_tube(bk.sag(p0, p1, dz, 7), 0.05, segs=4), M["BGRope"], smooth=True)
            cut.post.add(bm_tube(bk.sag(Vector(p0) + Vector((0, 0, 0.8)), Vector(p1) + Vector((0, 0, 0.8)), dz, 7), 0.03,
                                 segs=4), M["BGRope"], smooth=True)
        for x, z in ((-8.8, 6.8), (-1.6, 7.6), (3.4, 7.6), (9.1, 6.5)):
            ln = bm_lathe([(0.12, -0.25), (0.3, -0.12), (0.3, 0.12), (0.12, 0.25)], segs=8)
            translate(ln, (x, -0.2, z))
            cut.post.add(ln, M["BGWindow"])
            cut.post.add(bm_tube([Vector((x, -0.2, z + 0.25)), Vector((x, -0.2, z + 0.9))], 0.02, segs=3), M["BGRope"])
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_a(kit):
    """Lantern watchtower on tall stilts (~22 m)."""
    M = kit.M

    def fn():
        rng = random.Random(911)
        B = Builder(kit.name("BG_Far_A"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGWood"])
        W = M["BGWood"]
        for sx in (-1, 1):
            for sy in (0, 1):
                x, y = sx * 1.6, 0.6 + sy * 2.4
                B.add(bm_tube([Vector((x * 1.4, y, 0.0)), Vector((x, y, 12.5))], [0.22, 0.18], segs=6), W, smooth=True)
        for z in (4.0, 8.0):
            for sy in (0.6, 3.0):
                cut.post.add(bm_tube([Vector((-2.1, sy, z)), Vector((2.1, sy, z + 1.2))], 0.08, segs=4), W)
                cut.post.add(bm_tube([Vector((2.1, sy, z)), Vector((-2.1, sy, z + 1.2))], 0.08, segs=4), W)
        bk.bg_box(B, rng, (-2.6, 0.0, 12.4), (2.6, 3.6, 12.9), W, 0.04)
        bk.bg_box(B, rng, (-2.0, 0.3, 12.9), (2.0, 3.3, 15.8), W, 0.04)
        roof = square_roof((0.0, 1.8, 15.8), 2.9, 0.15, 2.6, 0.7, rings=4, aspect=(1.0, 0.85))
        cut.post.add(roof, M["BGRoof"])
        bk.bg_box(cut.post, rng, (-0.7, 1.2, 18.3), (0.7, 2.4, 19.4), W, 0.03)
        roof2 = square_roof((0.0, 1.8, 19.4), 1.1, 0.05, 1.8, 0.35, rings=3)
        cut.post.add(roof2, M["BGRoof"])
        cut.post.add(bm_lathe([(0.05, 21.0), (0.05, 22.0)], segs=5), W)
        for x in (-1.0, 1.0):
            cut.window(bk.win_poly(x, 13.4, 14.9, 0.7, "flat"), 0.3, 0.35)
        cut.window(bk.win_poly(0.0, 18.5, 19.1, 0.6, "flat"), 1.2, 0.3)
        for x in (-2.4, 2.4):
            ln = bm_lathe([(0.1, -0.2), (0.24, -0.1), (0.24, 0.1), (0.1, 0.2)], segs=8)
            translate(ln, (x, 0.1, 15.2))
            cut.post.add(ln, M["BGWindow"])
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_b(kit):
    """Cluster of stacked houses on stilts (~16 m)."""
    M = kit.M

    def fn():
        rng = random.Random(921)
        B = Builder(kit.name("BG_Far_B"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGWood"])
        W = M["BGWood"]
        bk.bg_box(B, rng, (-6.0, 0.0, 5.0), (6.0, 3.4, 5.4), W, 0.04)
        for x in lin(-5.4, 5.4, 6):
            stilt_legs(cut.post, W, x, 0.5, 5.1, rng, s=1.5)
        hut(B, cut, M, rng, -3.4, 0.2, 5.4, 3.6, 2.8, 2.0, depth=3.0)
        hut(B, cut, M, rng, 2.6, 0.3, 5.4, 4.2, 3.2, 2.2, depth=3.0)
        hut(B, cut, M, rng, -0.6, 0.8, 8.2, 3.4, 3.0, 2.4, depth=2.4)
        hut(B, cut, M, rng, 0.0, 1.2, 11.2, 2.2, 2.2, 2.4, depth=1.8)
        cut.post.add(bm_lathe([(0.04, 15.5), (0.04, 16.3)], segs=5), W)
        return bk.finish_bg(B, cut)

    return fn


def make_pagoda(kit):
    """Far pagoda: three upswept roof tiers on a stilted platform (~21 m)."""
    M = kit.M

    def fn():
        rng = random.Random(931)
        B = Builder(kit.name("Pagoda"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGWood"])
        W = M["BGWood"]
        bk.bg_box(B, rng, (-4.5, 0.0, 3.6), (4.5, 6.0, 4.1), W, 0.05)
        for x in lin(-4.0, 4.0, 5):
            stilt_legs(cut.post, W, x, 0.6, 3.7, rng, s=1.4)
        z = 4.1
        for k, (w, h, rh) in enumerate(((5.6, 3.0, 2.0), (4.4, 2.6, 1.8), (3.2, 2.3, 1.6))):
            bk.bg_box(B, rng, (-w / 2, 3.0 - w / 2, z), (w / 2, 3.0 + w / 2, z + h), W, 0.05)
            roof = square_roof((0.0, 3.0, z + h), w * 0.72, w * 0.3, rh, 0.55, rings=3)
            cut.post.add(roof, M["BGRoof"], tint=tint(rng))
            for x in ((-w * 0.25, w * 0.25) if k < 2 else (0.0,)):
                cut.window(bk.win_poly(x, z + h * 0.25, z + h * 0.65, 0.6, "round"), 3.0 - w / 2, 0.3)
            z += h + rh * 0.55
        spire = bm_lathe([(0.35, z - 0.3), (0.2, z + 0.6), (0.1, z + 2.6), (0.02, z + 3.4)], segs=6)
        translate(spire, (0, 3.0, 0))
        cut.post.add(spire, M["BGRoof"])
        for k in range(4):
            ln = bm_lathe([(0.08, -0.16), (0.2, -0.08), (0.2, 0.08), (0.08, 0.16)], segs=8)
            translate(ln, (-2.6 + k * 1.75, 0.0, 6.3))
            cut.post.add(ln, M["BGWindow"])
        return bk.finish_bg(B, cut)

    return fn


# ---------------------------------------------------------------------------

def chunk_extras(put):
    for x in (6.7, 10.3):
        put("Stilt", (x, 0.2, 3.3), s=0.55)


def make_kit():
    kit = bk.Kit(ID)
    kit.make_materials = materials
    kit.chunk_extras = chunk_extras
    kit.chunk_bg = "#1C1024"
    kit.light = dict(key=2.6, rim=3.0)
    kit.emission = {"paper lanterns / shoji": WARM, "red paper": "#FF7A3A", "BG windows/lanterns": WARM}
    usage = {"Fill_A": "stacked rope-lashed timbers", "Fill_B": "crate wall (two crates)",
             "Fill_C": "vertical plank wall with battens", "Top_A": "wet deck, purple wine-stain lip",
             "Top_B": "wet deck with shingle eave lip", "Edge_L": "deck end with corner post"}
    for role in ("Fill_A", "Fill_B", "Fill_C", "Top_A", "Top_B", "Edge_L"):
        kit.add(role, make_tile(kit, role), 1.6, 1500, "1x1 tile, pivot bottom-left, top y=1; " + usage[role],
                tile=True)
    kit.add("Edge_R", bk.mirror_tile(make_tile(kit, "Edge_L"), kit.name("Edge_R")), 1.6, 1500,
            "right platform end (mirror of Edge_L)", tile=True)
    kit.add("Platform", make_platform(kit), 1.5, 1500, "one-way plank platform, rope-lashed, deck top y=1")
    kit.add("BackWall", make_backwall(kit), 0.75, 3600, "4x4 vertical board wall with battens, seamless")
    kit.add("Pillar", make_pillar(kit), 0.9, 6000, "lacquered pagoda column with bracket set and talismans")
    kit.add("Arch", make_arch(kit), 0.85, 6000, "torii-like gate 6.9 m wide with chimes and lanterns")
    kit.add("Light", make_light(kit), 2.0, 4000, "paper lantern on a bracket; LightSocket = lantern centre (warm)")
    kit.add("Hang", make_hang(kit), 1.4, 4000, "rope with two wind chimes and a bronze bell, pivot top, ~2.6 m")
    kit.add("Door", make_door(kit), 1.1, 6000, "pagoda doorway with glowing shoji (one open), recess 0.78 m")
    kit.add("Prop_A", make_prop_a(kit), 1.3, 4000, "wine barrel with purple overflow")
    kit.add("Prop_B", make_prop_b(kit), 1.3, 4000, "rope coil and bronze bell stand")
    kit.add("Prop_C", make_prop_c(kit), 1.3, 4000, "crate, fish baskets and paper lantern")
    kit.add("Stilt", make_stilt(kit), 0.9, 4000, "bird-like stilt leg, pivot at top, extends to y=-6")
    kit.add("BG_Near", make_bg_near(kit), 1.0, 10000, "stilt huts on decks 20x10 m (Unity z=5)", atlas="BG")
    kit.add("BG_Far_A", make_bg_far_a(kit), 1.0, 10000, "lantern watchtower on stilts ~22 m (z=10)", atlas="BG")
    kit.add("BG_Far_B", make_bg_far_b(kit), 1.0, 10000, "stacked stilt houses ~16 m (z=16)", atlas="BG")
    kit.add("Pagoda", make_pagoda(kit), 1.0, 10000, "far three-tier pagoda roof tower ~21 m", atlas="BG")
    return kit
