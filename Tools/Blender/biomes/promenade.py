"""Promenade of the Suspended Moons: rampart causeways under an indigo night,
pale grey-violet ashlar with moon-dust lips, glowing silver tick-silk,
brass clockwork remnants, floating moon shards."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

import biome_kit as bk
import env_helpers as eh
from biome_kit import TF, TB, G, X, Y, Z, rad, lin, hex_mix, tint, material
from env_helpers import (Builder, block, bm_blob, bm_box, bm_cut, bm_ico, bm_lathe, bm_prism_xz, bm_tube,
                         delete_faces, rotate, scale, transform, translate)

ID = "Promenade"
STONE = "#5F5B74"
GLOW = "#A8D8FF"


def materials(kit):
    M = kit.M
    M["Stone"] = material("M_PR_Stone", STONE, hex_mix(STONE, "#2E2B40", 0.5), hex_mix(STONE, "#8E8AA8", 0.45),
                          rough=0.85, noise_scale=3.0, noise_amt=0.4, bevel_radius=0.03, bump_strength=0.35,
                          bump_scale=14.0,
                          fx=dict(tint_amt=0.26, grime_hex="#8D88B0", grime_amt=0.55, blotch=("#4A4660", 5.0, 0.1),
                                  top_hex="#6E6A86", top_amt=0.08, bottom_amt=0.3, edge_hex="#B6B1CC", edge_amt=0.9,
                                  edge_radius=0.05, edge_top_bias=0.5, cavity_amt=0.8, cavity_dist=0.16,
                                  cavity_hex="#15132A"))
    back = material("M_PR_StoneBack", "#3F3B55", "#26233A", "#544F6E", rough=0.88, noise_scale=2.2, noise_amt=0.4,
                    bevel_radius=0.04, bump_strength=0.35, bump_scale=8.0,
                    fx=dict(tint_amt=0.24, blotch=("#2E2A44", 4.0, 0.08), top_hex="#544F6E", top_amt=0.25,
                            bottom_amt=0.25, edge_hex="#77729A", edge_amt=0.8, edge_radius=0.05, cavity_amt=0.8,
                            cavity_dist=0.2, cavity_hex="#120F22"))
    eh.make_periodic(back, 4.0, 4.0)
    M["StoneBack"] = back
    M["Mortar"] = material("M_PR_Mortar", "#15132A", "#0A0918", "#221F3A", rough=0.95, noise_scale=6.0,
                           fx=dict(cavity_amt=0.4, cavity_dist=0.1))
    mb = material("M_PR_MortarBack", "#15132A", "#0A0918", "#221F3A", rough=0.95, noise_scale=3.0)
    eh.make_periodic(mb, 4.0, 4.0)
    M["MortarBack"] = mb
    M["Dust"] = material("M_PR_Dust", "#B4B0D0", "#8A85AD", "#DCDAF0", rough=0.95, noise_scale=14.0, noise_amt=0.7,
                         bevel_radius=0.02, bump_strength=0.5, bump_scale=45.0,
                         fx=dict(blotch=("#ECEBFA", 22.0, 0.14), cavity_amt=0.5, cavity_dist=0.06,
                                 cavity_hex="#6E6A90", bottom_amt=0.4, top_hex="#D0CDE8", top_amt=0.12))
    M["Silk"] = material("M_PR_Silk", "#C9D6EC", "#9FB2D0", "#F2F7FF", rough=0.4, noise_scale=20.0,
                         emission=GLOW, emission_strength=2.0)
    M["Brass"] = material("M_PR_Brass", "#9C7A3C", "#5A4220", "#D2B068", rough=0.38, rough_var=0.12, metal=0.85,
                          noise_scale=8.0, bevel_radius=0.01, bump_strength=0.3, bump_scale=40.0,
                          fx=dict(blotch=("#4C6E62", 6.0, 0.16), edge_hex="#E6CC88", edge_amt=1.0, edge_radius=0.012,
                                  cavity_amt=0.7, cavity_dist=0.05, cavity_hex="#2A1E0C", top_hex="#D2B068",
                                  top_amt=0.2))
    M["Iron"] = material("M_PR_Iron", "#34323F", "#1B1A24", "#5A5870", rough=0.5, metal=0.7, noise_scale=7.0,
                         bevel_radius=0.008, bump_strength=0.3, bump_scale=40.0,
                         fx=dict(edge_hex="#7A7890", edge_amt=0.9, edge_radius=0.012, cavity_amt=0.6,
                                 cavity_dist=0.05, cavity_hex="#0C0B12", top_hex="#5A5870", top_amt=0.2))
    M["Crystal"] = material("M_PR_Crystal", "#A9C4F0", "#6F8CC8", "#E2EEFF", rough=0.2, noise_scale=6.0,
                            emission="#CFE8FF", emission_strength=3.0)
    M["Orb"] = material("M_PR_Orb", "#BFE0FF", "#8FB8E8", "#F0F8FF", rough=0.15, emission=GLOW,
                        emission_strength=4.0)
    M["MoonRock"] = material("M_PR_MoonRock", "#A9A6BE", "#6E6A86", "#D4D2E6", rough=0.9, noise_scale=1.4,
                             noise_amt=0.6, bevel_radius=0.06, bump_strength=0.6, bump_scale=6.0,
                             fx=dict(cavity_amt=0.9, cavity_dist=0.45, cavity_hex="#3E3A58", edge_hex="#ECEAF6",
                                     edge_amt=0.6, edge_radius=0.08, top_hex="#D4D2E6", top_amt=0.2,
                                     blotch=("#8E8AA8", 2.5, 0.25)))
    M["Dark"] = material("M_PR_Dark", "#14121F", "#09080F", "#211E33", rough=0.95, noise_scale=2.5,
                         fx=dict(brick=(0.55, 0.28, "#06050B"), cavity_amt=0.6, cavity_dist=0.25, tint_amt=0.15))
    M["BGStone"] = material("M_PR_BGStone", "#2A2645", "#17142B", "#3F3A62", rough=0.9, noise_scale=0.7,
                            bevel_radius=0.06, bump_strength=0.3, bump_scale=4.0,
                            fx=dict(brick=(1.2, 0.55, "#120F22"), top_hex="#4A4572", top_amt=0.4, bottom_amt=0.3,
                                    edge_hex="#5A5486", edge_amt=0.8, edge_radius=0.18, cavity_amt=0.6,
                                    cavity_dist=1.2, cavity_hex="#0B0918", tint_amt=0.2))
    M["BGRoof"] = material("M_PR_BGRoof", "#221E3A", "#141128", "#38335C", rough=0.85, noise_scale=1.2,
                           stripes=("z", 2.2, 0.14, "#120F24"),
                           fx=dict(top_hex="#4A4572", top_amt=0.3, edge_hex="#5A5486", edge_amt=0.6,
                                   edge_radius=0.15, cavity_amt=0.5, cavity_dist=1.0))
    M["BGWindow"] = material("M_PR_BGWindow", "#2B3A5A", "#1A2238", "#3A4C70", noise_scale=2.0, emission=GLOW,
                             emission_strength=2.0)
    M["BGSilk"] = material("M_PR_BGSilk", "#C9D6EC", "#9FB2D0", "#F2F7FF", emission=GLOW, emission_strength=2.0)
    M["BGBrass"] = material("M_PR_BGBrass", "#7A6232", "#4A3A1C", "#B89A58", rough=0.4, metal=0.8,
                            fx=dict(edge_hex="#D8BC78", edge_amt=0.8, edge_radius=0.04))
    M["BGDial"] = material("M_PR_BGDial", "#C8D2E8", "#9AA6C4", "#E8EEFA", emission="#D8E8FF", emission_strength=2.0)


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------

TILES = {
    "Fill_A": (101, [(0.0, 0.5, [0.58]), (0.5, 1.0, [0.32])], None),
    "Fill_B": (102, [(0.0, 0.42, [0.45]), (0.42, 1.0, [0.7])], (1, 0)),
    "Fill_C": (103, [(0.0, 0.56, []), (0.56, 1.0, [0.4])], None),
    "Top_A": (111, [(0.0, 0.48, [0.38]), (0.48, 1.0, [0.62])], (0, 1)),
    "Top_B": (112, [(0.0, 0.4, [0.66]), (0.4, 1.0, [0.45])], None),
    "Edge_L": (121, [(0.0, 0.52, [0.55]), (0.52, 1.0, [0.5])], None),
}


def clock_fragment(B, M, rng, center, r, y_front, tilt=0.0, teeth=14):
    pcs = bk.bm_gear(r, r * 0.86, teeth, 0.045, spokes=4, y0=0.0)
    for p in pcs:
        rotate(p, tilt, "Y")
        translate(p, (center[0], y_front, center[1]))
    B.add(pcs, M["Brass"], tint=tint(rng), uvw=1.2, hard=40)


def make_tile(kit, role):
    M = kit.M
    seed, rows, crack = TILES[role]

    def fn():
        rng = random.Random(seed)
        B = Builder(kit.name(role))
        edge = "L" if role == "Edge_L" else None
        mossy = role.startswith(("Top", "Edge"))

        def extra(B_, rng_, lo, hi, ctx):
            if role == "Fill_C" and ctx["row"] == 0:
                clock_fragment(B_, M, rng_, (0.68, 0.24), 0.16, lo[1] - 0.025, tilt=rng_.uniform(0, 1))
                for p in ((0.18, 0.12), (0.2, 0.42)):
                    B_.add(bk.dome_rivet((p[0], lo[1] - 0.002, p[1]), r=0.022), M["Brass"], smooth=True)

        bfn = bk.stone_block_fn(M["Stone"], inset=None, top_grime=0.45 if mossy else 0.0, bevel=0.03,
                                chips=(1, 2), extra=extra)
        bk.tile_body(B, rng, rows, bfn, M["Mortar"], edge=edge, crack=crack)
        if mossy:
            D = bk.lip_cover(B, rng, seed, M["Dust"], edge=edge, base=0.1, amp=0.06, dmin=0.05, dmax=0.22,
                             top_depth=0.34, offset=0.03, lump_amp=0.02, lump_freq=4.0,
                             clumps=(4, (0.05, 0.066), (2.0, 1.15, 0.7)))
            # moon-crystal icicles growing down from the dusty lip
            for k in range(2 if role != "Top_B" else 1):
                x = rng.uniform(0.2, 0.8)
                z0 = 1.0 - D(x) + 0.02
                L = rng.uniform(0.12, 0.22)
                pts = [Vector((x + rng.uniform(-0.03, 0.03), -0.93 + rng.uniform(-0.01, 0.01), z0 + rng.uniform(-0.02, 0.02)))
                       for _ in range(5)]
                pts.append(Vector((x + rng.uniform(-0.02, 0.02), -0.95, z0 - L)))
                B.add(eh.bm_hull(pts), M["Crystal"], uvw=1.2)
            if role == "Top_A":
                x = rng.uniform(0.3, 0.7)
                bk.silk_thread(B, M["Silk"], [(x, -0.955, 1.0 - D(x)), (x + 0.02, -0.957, 1.0 - D(x) - 0.15),
                                              (x - 0.01, -0.957, 1.0 - D(x) - 0.32)])
        bk.clamp_tile(B)
        return B

    return fn


# ---------------------------------------------------------------------------
# Platform / back wall
# ---------------------------------------------------------------------------

def make_platform(kit):
    M = kit.M

    def fn():
        rng = random.Random(131)
        B = Builder(kit.name("Platform"))
        B.add(block((0.004, -0.62, 0.8), (0.996, 1.0, 1.0), rng, chips=2, chip_size=(0.03, 0.08), bevel=0.028, segs=2,
                    fixed_top=1.0, corners=[(-1, -1, 1), (1, -1, 1), (-1, -1, -1), (1, -1, -1)],
                    pre=lambda bm: bk.inset_front(bm, 0.035, -0.01)), M["Stone"], tint=tint(rng),
              uvw_fn=lambda c, n: 1.0 if c.y < -0.3 else 0.4)
        for (lo, hi, ch) in (((0.36, 0.25, 0.6), (0.64, 1.0, 0.8), 0.12), ((0.4, 0.5, 0.4), (0.6, 1.0, 0.6), 0.1),
                             ((0.43, 0.72, 0.22), (0.57, 1.0, 0.4), 0.08)):
            B.add(block(lo, hi, rng, chips=1, bevel=0.02, segs=2, back_delete=0.95,
                        cuts=[((0.5, lo[1] + ch, lo[2]), (0, -1, -1))]), M["Stone"], tint=tint(rng))
        for cx in (0.07, 0.93):
            B.add(block((cx - 0.03, -0.635, 0.81), (cx + 0.03, -0.615, 0.99), rng, bevel=0.004, segs=1), M["Brass"],
                  tint=tint(rng))
            for z in (0.85, 0.95):
                B.add(bk.dome_rivet((cx, -0.635, z), r=0.013), M["Brass"], smooth=True)
        return B

    return fn


def make_backwall(kit):
    M = kit.M

    def fn():
        rng = random.Random(141)
        B = Builder(kit.name("BackWall"))
        bk.masonry_wall(B, rng, M["StoneBack"], M["MortarBack"], rows=[0.85, 0.75, 0.9, 0.7, 0.8], width=(1.1, 1.8),
                        gap=0.075, bevel=0.05, segs=2, inset=(0.07, 0.02), chips=(0, 2))
        return B

    return fn


# ---------------------------------------------------------------------------
# Pillar / Arch / Door
# ---------------------------------------------------------------------------

def make_pillar(kit):
    M = kit.M

    def fn():
        rng = random.Random(151)
        B = Builder(kit.name("Pillar"))
        cy = 0.5
        B.add(block((-0.5, 0.0, 0.0), (0.5, 1.0, 0.3), rng, chips=2, bevel=0.04, segs=2, back_delete=0.95,
                    pre=lambda bm: bk.inset_front(bm, 0.05, 0.012)), M["Stone"], tint=tint(rng))
        B.add(block((-0.42, 0.08, 0.3), (0.42, 0.92, 0.5), rng, chips=1, bevel=0.04, segs=2, back_delete=0.9,
                    cuts=[((0, 0.08 + 0.06, 0.5), (0, -1, 1)), ((-0.36, 0, 0.5), (-1, 0, 1)), ((0.36, 0, 0.5), (1, 0, 1))]),
              M["Stone"], tint=tint(rng))
        z = 0.5
        for k, h in enumerate([0.95, 0.9, 1.0, 0.95]):
            r0 = 0.355 - 0.008 * k
            drum = bm_lathe([(r0 - 0.03, z + 0.015), (r0, z + 0.045), (r0 - 0.004, z + h - 0.045), (r0 - 0.034, z + h - 0.015)],
                            segs=8, phase=math.pi / 8)
            translate(drum, (0, cy, 0))
            B.add(drum, M["Stone"], tint=tint(rng), hard=30)
            z += h
        core = bm_lathe([(0.3, 0.5), (0.3, z)], segs=8, phase=math.pi / 8, cap_top=False, cap_bottom=False)
        translate(core, (0, cy, 0))
        B.add(core, M["Mortar"], uvw=0.3)
        for zb in (1.45, 3.35):
            ring = bm_lathe([(0.355, zb - 0.06), (0.375, zb - 0.045), (0.375, zb + 0.045), (0.355, zb + 0.06),
                             (0.355, zb - 0.06)], segs=16, cap_top=False, cap_bottom=False)
            translate(ring, (0, cy, 0))
            B.add(ring, M["Brass"], tint=tint(rng), hard=40)
            for a in (rad(-90 - 30), rad(-90), rad(-90 + 30)):
                p = Vector((0.378 * math.cos(a), cy + 0.378 * math.sin(a), zb))
                B.add(bk.dome_rivet(p, r=0.016, facing=Vector((math.cos(a), math.sin(a), 0))), M["Brass"], smooth=True)
        cap = bm_lathe([(0.31, z), (0.36, z + 0.08), (0.44, z + 0.2), (0.47, z + 0.27)], segs=8, phase=math.pi / 8,
                       cap_bottom=False)
        translate(cap, (0, cy, 0))
        B.add(cap, M["Stone"], tint=tint(rng), hard=30)
        zt = z + 0.27
        B.add(block((-0.5, 0.0, zt), (0.5, 1.0, zt + 0.2), rng, chips=2, bevel=0.035, segs=2, back_delete=0.95,
                    pre=lambda bm: bk.inset_front(bm, 0.04, 0.01)), M["Stone"], tint=tint(rng))
        zt += 0.2
        cres = [(0.0 + 0.13 * math.cos(a), cy, zt + 0.15 + 0.13 * math.sin(a)) for a in lin(rad(-60), rad(240), 11)]
        B.add(bm_tube(cres, [0.006] + [0.03] * 9 + [0.006], segs=6, up=Y, flatten=0.5), M["Brass"], smooth=True)
        B.add(bm_lathe([(0.05, zt), (0.035, zt + 0.03), (0.02, zt + 0.06)], segs=8), M["Brass"])
        bk.ledge_cover(B, rng, M["Dust"], -0.5, 0.5, 0.0, 0.5, zt - 0.2 + 0.2, depth=(0.03, 0.12), seed=3.0,
                       env_z0=zt - 0.2, lump_amp=0.02)
        bk.ledge_cover(B, rng, M["Dust"], -0.42, 0.42, 0.08, 0.2, 0.5, depth=(0.03, 0.1), seed=5.0, env_z0=0.3,
                       lump_amp=0.02)
        for sx in (-1, 1):
            p0 = Vector((sx * 0.46, -0.02, zt - 0.22))
            p1 = Vector((sx * 0.38, 0.07, 0.62 + rng.uniform(0, 0.4)))
            bk.silk_thread(B, M["Silk"], bk.sag(p0, p1, -0.12 * sx * 0, n=6))
        return B

    return fn


def spider_web(B, mat, hub, anchors, rings=(0.22, 0.38, 0.54, 0.7, 0.86), r=0.008):
    hub = Vector(hub)
    for a in anchors:
        bk.silk_thread(B, mat, bk.sag(hub, a, 0.04, n=4), r=r)
    for f in rings:
        pts = [hub.lerp(Vector(a), f) for a in anchors]
        for p0, p1 in zip(pts, pts[1:]):
            bk.silk_thread(B, mat, bk.sag(p0, p1, 0.03 * f, n=3), r=r * 0.8)


def make_arch(kit):
    M = kit.M

    def fn():
        rng = random.Random(161)
        B = Builder(kit.name("Arch"))
        cz, r_in, r_out = 2.85, 2.1, 2.55
        for s in (-1, 1):
            lx, hx = sorted((s * 2.05, s * 3.0))
            B.add(block((lx, -0.07, 0.0), (hx, 0.8, 0.3), rng, chips=2, bevel=0.035, segs=2, back_delete=0.75),
                  M["Stone"], tint=tint(rng))
            lx, hx = sorted((s * 2.1, s * 2.95))
            z = bk.pier(B, rng, lx, hx, [0.62, 0.55, 0.6, 0.55], M["Stone"], z=0.3, segs=1, bevel=0.035,
                        inset=(0.05, 0.008), grime=0.0)
            lx, hx = sorted((s * 2.02, s * 3.03))
            B.add(block((lx, -0.07, z + 0.01), (hx, 0.8, cz), rng, chips=2, bevel=0.03, segs=2, back_delete=0.75,
                        cuts=[((0, -0.07 + 0.06, z + 0.01), (0, -1, -1))]), M["Stone"], tint=tint(rng))
            core = bm_box((min(s * 2.18, s * 2.88), 0.08, 0.3), (max(s * 2.18, s * 2.88), 0.72, cz))
            delete_faces(core, lambda c, n: n.y > 0.9)
            B.add(core, M["Mortar"], uvw=0.3)
        env = bmesh.new()
        bk.voussoirs(B, rng, (0.0, cz), r_in, r_out, 0.0, 0.8, 13, 0.045, M["Stone"], key_extra=0.12, env=env,
                     segs=1, bevel=0.03, inset=(0.045, 0.008))
        for i in range(12):
            a0, a1 = math.pi * i / 12, math.pi * (i + 1) / 12
            poly = [(2.16 * math.cos(a0), cz + 2.16 * math.sin(a0)), (2.48 * math.cos(a0), cz + 2.48 * math.sin(a0)),
                    (2.48 * math.cos(a1), cz + 2.48 * math.sin(a1)), (2.16 * math.cos(a1), cz + 2.16 * math.sin(a1))]
            bm = bm_prism_xz(poly, 0.07, 0.72)
            delete_faces(bm, lambda c, n: n.y > 0.9)
            B.add(bm, M["Mortar"], uvw=0.3)
        # moon dust drifted on the extrados
        bvh = eh.envelope_bvh(env)
        thetas = lin(rad(35), rad(145), 22)

        def D(th):
            u = (th - rad(35)) / rad(110)
            return (0.05 + 0.06 * abs(math.sin(u * 7.0 + 1.3))) * max(0.0, math.sin(math.pi * u)) ** 0.4

        def P(th, rho, y):
            return (rho * math.cos(th), y, cz + rho * math.sin(th))

        top = [[P(th, 3.4, y) for th in thetas] for y in (0.8, 0.5, 0.2)] + [[P(th, 3.4, -0.5) for th in thetas]]
        front = [top[-1]] + [[P(th, r_out - t * (D(th) + 0.02), -0.5) for th in thetas] for t in (0.05, 0.5, 1.0)]
        sheet, keyed = eh.sheet_from_grids([top, front])
        eh.project_sheet(sheet, bvh, offset=0.022, tuck_verts=[keyed[eh.key_of(p)] for p in front[-1]],
                         lump=lambda p: 0.03 * max(0.0, eh.periodic_noise(p.x * 0.4, p.y * 2, p.z, 7.0, 2.0) + 0.2))
        B.add(sheet, M["Dust"], smooth=True)
        env.free()
        # tick-silk web strung across the opening
        hub = Vector((0.55, 0.45, 3.35))
        anchors = [Vector(((r_in - 0.03) * math.cos(t), 0.45, cz + (r_in - 0.03) * math.sin(t))) for t in
                   (rad(160), rad(132), rad(105), rad(78), rad(52), rad(25))]
        anchors += [Vector((2.07, 0.45, 1.6)), Vector((-2.07, 0.45, 1.9))]
        spider_web(B, M["Silk"], hub, anchors)
        for t in (rad(140), rad(60)):
            p = Vector(((r_in - 0.03) * math.cos(t), 0.3, cz + (r_in - 0.03) * math.sin(t)))
            bk.silk_thread(B, M["Silk"], [p, p + Vector((0.05, 0, -0.6)), p + Vector((-0.03, 0, -1.3))])
        clock_fragment(B, M, rng, (0.0, cz + r_out + 0.0), 0.22, -0.06, teeth=16)
        return B

    return fn


def make_door(kit):
    M = kit.M

    def fn():
        rng = random.Random(171)
        B = Builder(kit.name("Door"))
        S = M["Stone"]
        D1 = 0.45
        for s in (-1, 1):
            z = 0.0
            for k, h in enumerate([0.62, 0.55, 0.65, 0.58]):
                outer = 1.2 if k % 2 == 0 else 1.1
                lo = (min(s * 0.8, s * outer) + (G / 2 if s > 0 else 0), rng.uniform(-0.025, 0.02), z + G / 2)
                hi = (max(s * 0.8, s * outer) - (G / 2 if s < 0 else 0), D1, z + h - G / 2)
                B.add(block(lo, hi, rng, chips=rng.randint(1, 2), bevel=0.025, segs=2, jitter=0.012,
                            back_delete=D1 - 0.05, pre=lambda bm: bk.inset_front(bm, 0.035, 0.012)), S, tint=tint(rng))
                z += h
            # springer cut along the first voussoir joint
            a = math.atan2(0.6, 0.8)
            n = Vector((-math.sin(a) * s, 0, math.cos(a)))
            p = Vector((0.8 * s, 0, 2.4)) + n * (G / 2)
            lo = (min(s * 0.8, s * 1.18) + (G / 2 if s > 0 else 0), 0.0, 2.4 + G / 2)
            hi = (max(s * 0.8, s * 1.18) - (G / 2 if s < 0 else 0), D1, 2.95)
            B.add(block(lo, hi, rng, chips=1, bevel=0.025, segs=2, back_delete=D1 - 0.05, cuts=[(p, n)]), S,
                  tint=tint(rng))
        a0 = math.atan2(0.6, 0.8)
        bk.voussoirs(B, rng, (0.0, 1.8), 1.0, 1.4, 0.0, D1, 7, 0.04, S, key_extra=0.0, jitter_r=0.03, start=a0,
                     end=math.pi - a0, segs=2, bevel=0.022, inset=(0.03, 0.01))
        B.add(block((-0.84, -0.06, 0.0), (0.84, 0.75, 0.1), rng, chips=2, bevel=0.02, segs=2, back_delete=0.7), S,
              tint=tint(rng))
        for s in (-1, 1):
            core = bm_box((min(s * 0.86, s * 1.08), 0.05, 0.0), (max(s * 0.86, s * 1.08), 0.4, 2.9))
            delete_faces(core, lambda c, n: n.y > 0.9)
            B.add(core, M["Mortar"], uvw=0.25)
        DK = M["Dark"]
        B.add(delete_faces(bm_box((-0.9, 0.72, 0.0), (0.9, 0.78, 2.9)), lambda c, n: n.y > 0.5), DK)
        for s in (-1, 1):
            B.add(delete_faces(bm_box((min(s * 0.8, s * 0.86), 0.4, 0.0), (max(s * 0.8, s * 0.86), 0.74, 2.9)),
                               lambda c, n, s=s: n.x * s > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.4, 2.78), (0.82, 0.74, 2.84)), lambda c, n: n.z > 0.5), DK, uvw=0.6)
        B.add(delete_faces(bm_box((-0.82, 0.4, -0.05), (0.82, 0.74, 0.005)), lambda c, n: n.z < -0.5), DK, uvw=0.6)
        # half-raised portcullis
        I = M["Iron"]
        yp, zb = 0.24, 1.25
        for x in lin(-0.7, 0.7, 6):
            B.add(block((x - 0.022, yp - 0.022, zb), (x + 0.022, yp + 0.022, 2.85), rng, bevel=0.005, segs=1), I,
                  tint=tint(rng))
            spike = bm_lathe([(0.026, 0.0), (0.0005, -0.09)], segs=4, phase=math.pi / 4)
            translate(spike, (x, yp, zb))
            B.add(spike, I)
        for z in (zb + 0.12, zb + 0.62, zb + 1.12):
            B.add(block((-0.76, yp - 0.04, z - 0.025), (0.76, yp - 0.018, z + 0.025), rng, bevel=0.004, segs=1), I,
                  tint=tint(rng))
            for x in lin(-0.7, 0.7, 6):
                B.add(bk.dome_rivet((x, yp - 0.04, z), r=0.012), M["Brass"], smooth=True)
        clock_fragment(B, M, rng, (0.0, 2.98), 0.17, -0.05, teeth=12)
        return B

    return fn


# ---------------------------------------------------------------------------
# Light / Hang / Props
# ---------------------------------------------------------------------------

def make_light(kit):
    M = kit.M

    def fn():
        rng = random.Random(181)
        B = Builder(kit.name("Light"))
        plate = bm_prism_xz([(-0.1, 0.0), (0.1, 0.0), (0.1, 0.3), (0.0, 0.4), (-0.1, 0.3)], -0.03, 0.0)
        eh.bm_bevel(plate, 0.008, 1)
        delete_faces(plate, lambda c, n: n.y > 0.9)
        B.add(plate, M["Iron"], tint=tint(rng))
        for p in ((-0.06, 0.06), (0.06, 0.06), (0.0, 0.31)):
            B.add(bk.dome_rivet((p[0], -0.03, p[1]), r=0.016), M["Brass"], smooth=True)
        arm = [(0, -0.03, 0.2), (0, -0.12, 0.27), (0, -0.24, 0.34), (0, -0.34, 0.37), (0, -0.39, 0.34),
               (0, -0.39, 0.3)]
        B.add(bm_tube(arm, 0.017, segs=8), M["Brass"], smooth=True, tint=tint(rng))
        curl = [(0, -0.03, 0.08)] + [(0, -0.03 - 0.16 * t, 0.08 + 0.17 * t * t) for t in lin(0.1, 1, 7)]
        B.add(bm_tube(curl, 0.01, segs=6), M["Brass"], smooth=True)
        cy = -0.39
        top = bm_lathe([(0.015, 0.3), (0.05, 0.285), (0.11, 0.25), (0.12, 0.235), (0.1, 0.235)], segs=12)
        translate(top, (0, cy, 0))
        B.add(top, M["Brass"], smooth=True, tint=tint(rng))
        bot = bm_lathe([(0.1, 0.0), (0.12, 0.0), (0.09, -0.03), (0.03, -0.055), (0.01, -0.07)], segs=12)
        translate(bot, (0, cy, 0))
        B.add(bot, M["Brass"], smooth=True, tint=tint(rng))
        for k in range(6):
            a = TAU_ * k / 6
            p0 = Vector((0.105 * math.cos(a), cy + 0.105 * math.sin(a), 0.0))
            p1 = Vector((0.105 * math.cos(a), cy + 0.105 * math.sin(a), 0.235))
            mid = (p0 + p1) / 2 + Vector((0.025 * math.cos(a), 0.025 * math.sin(a), 0))
            B.add(bm_tube([p0, mid, p1], 0.008, segs=5), M["Iron"], smooth=True)
        B.add(bm_blob((0, cy, 0.12), 0.085, (1, 1, 1.08), segs=10, rings=7), M["Orb"], smooth=True, uvw=1.2)
        B.sockets["LightSocket"] = (0.0, cy, 0.12)
        s = 1.4
        scale(B.bm, s)
        B.sockets["LightSocket"] = tuple(c * s for c in B.sockets["LightSocket"])
        return B

    return fn


TAU_ = math.tau


def make_hang(kit):
    M = kit.M

    def fn():
        rng = random.Random(191)
        B = Builder(kit.name("Hang"))
        B.add(bm_blob((0, 0, -0.05), 0.08, (1.4, 1.0, 0.8), segs=8, rings=5, rng=rng, jitter=0.2), M["Silk"],
              smooth=True)
        ends = []
        for k in range(7):
            ang = TAU_ * k / 7 + rng.uniform(-0.2, 0.2)
            L = rng.uniform(1.4, 2.8)
            pts = []
            for t in lin(0, 1, 8):
                pts.append(Vector((math.cos(ang) * 0.06 * (1 + 2 * t) + 0.05 * math.sin(t * 4 + k) * t,
                                   math.sin(ang) * 0.04 * (1 + t), -0.05 - L * t)))
            bk.silk_thread(B, M["Silk"], pts, r=rng.uniform(0.007, 0.011))
            ends.append(pts)
        # wrapped cocoon on one strand
        c = Vector((0.08, 0.0, -1.95))
        cocoon = bm_lathe([(0.02, 0.36), (0.1, 0.3), (0.17, 0.12), (0.18, -0.05), (0.14, -0.25), (0.07, -0.38),
                           (0.02, -0.42)], segs=10)
        rotate(cocoon, 0.18, "Y")
        translate(cocoon, c)
        B.add(cocoon, M["Dust"], smooth=True, tint=tint(rng), uvw=1.2)
        helix = [c + Matrix.Rotation(0.18, 3, "Y") @ Vector((0.19 * math.cos(t) * (1 - abs(z) / 0.5),
                                                            0.19 * math.sin(t) * (1 - abs(z) / 0.5), z))
                 for t, z in zip(lin(0, TAU_ * 4, 40), lin(0.32, -0.36, 40))]
        bk.silk_thread(B, M["Silk"], helix, r=0.008)
        bk.silk_thread(B, M["Silk"], [Vector((0, 0, -0.08)), c + Vector((0.04, 0, 0.5)), c + Vector((0.03, 0, 0.36))])
        for pts in ends[:3]:
            for t in (0.45, 0.8):
                p = pts[int(t * (len(pts) - 1))]
                B.add(bm_blob(p, 0.022, (1, 1, 1.3), segs=6, rings=4), M["Crystal"], smooth=True)
        return B

    return fn


def make_prop_a(kit):
    """Brass clockwork debris."""
    M = kit.M

    def fn():
        rng = random.Random(201)
        B = Builder(kit.name("Prop_A"))
        for (c, r, teeth, rot) in (((-0.1, 0.45, 0.04), 0.36, 18, rad(85)), ((0.32, 0.3, 0.03), 0.22, 12, rad(80))):
            pcs = bk.bm_gear(r, r * 0.86, teeth, 0.06, spokes=5, y0=-0.03)
            for p in pcs:
                rotate(p, rot, "X")
                translate(p, c)
            B.add(pcs, M["Brass"], tint=tint(rng), hard=40)
        pcs = bk.bm_gear(0.3, 0.26, 14, 0.05, spokes=4, y0=-0.025)
        for p in pcs:
            rotate(p, rad(-18), "X")
            rotate(p, rad(25), "Z")
            translate(p, (0.05, 0.62, 0.32))
        B.add(pcs, M["Brass"], tint=tint(rng), hard=40)
        helix = [Vector((-0.42 + 0.06 * math.cos(t), 0.25 + 0.06 * math.sin(t), 0.06 + 0.028 * t / TAU_ * 2))
                 for t in lin(0, TAU_ * 4, 48)]
        rotate_pts = Matrix.Rotation(rad(70), 3, "Y")
        helix = [rotate_pts @ (p - Vector((-0.42, 0.25, 0.06))) + Vector((-0.42, 0.25, 0.06)) for p in helix]
        B.add(bm_tube(helix, 0.012, segs=5), M["Iron"], smooth=True)
        B.add(bk.beam((-0.55, 0.5, 0.03), (0.5, 0.75, 0.05), 0.04, 0.04, rng, bevel=0.005), M["Brass"])
        B.add(block((-0.25, 0.55, 0.0), (0.15, 0.95, 0.22), rng, chips=2, bevel=0.025, segs=2), M["Stone"],
              tint=tint(rng))
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))
        return B

    return fn


def make_prop_b(kit):
    """Toppled merlon rubble with a dust drift and a crystal sprout."""
    M = kit.M

    def fn():
        rng = random.Random(211)
        B = Builder(kit.name("Prop_B"))
        specs = [((-0.45, 0.0, 0.0), (0.25, 0.55, 0.45), 0.0), ((0.2, 0.1, 0.0), (0.62, 0.6, 0.3), rad(12)),
                 ((-0.3, 0.12, 0.45), (0.15, 0.5, 0.72), rad(-8))]
        for lo, hi, rz in specs:
            pcs = block(lo, hi, rng, chips=3, chip_size=(0.05, 0.14), bevel=0.03, segs=2,
                        pre=lambda bm: bk.inset_front(bm, 0.04, 0.012))
            for p in pcs:
                rotate(p, rz, "Z", ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0))
            B.add(pcs, M["Stone"], tint=tint(rng))
        bk.ledge_cover(B, rng, M["Dust"], -0.45, 0.25, 0.0, 0.55, 0.45, depth=(0.03, 0.1), seed=7.0, env_z0=0.0)
        for k in range(3):
            base = Vector((0.4 + 0.05 * k, 0.35, 0.3))
            tip = base + Vector((rng.uniform(-0.1, 0.1), rng.uniform(-0.05, 0.05), rng.uniform(0.18, 0.35)))
            pr = bm_lathe([(0.04, 0.0), (0.045, 0.6), (0.0005, 1.0)], segs=6)
            transform(pr, eh.look_matrix(base - (tip - base) * 0.2, tip))
            B.add(pr, M["Crystal"], uvw=1.2)
        return B

    return fn


def make_prop_c(kit):
    """Moon-crystal cluster on a lump of moon rock."""
    M = kit.M

    def fn():
        rng = random.Random(221)
        B = Builder(kit.name("Prop_C"))
        rock = [Vector((rng.uniform(-0.45, 0.45), rng.uniform(0.0, 0.7), rng.uniform(0.0, 0.3))) for _ in range(14)]
        rock += [Vector((0, 0.35, 0.0))]
        B.add(eh.bm_hull(rock), M["MoonRock"], tint=tint(rng))
        for k in range(7):
            base = Vector((rng.uniform(-0.25, 0.25), rng.uniform(0.2, 0.5), 0.15))
            d = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.4, 0.2), 1.0)).normalized()
            L = rng.uniform(0.35, 0.95) if k else 1.05
            w = L * 0.13
            pr = bm_lathe([(w, -0.05), (w * 1.05, L * 0.72), (0.0005, L)], segs=6, phase=rng.uniform(0, 1))
            transform(pr, eh.look_matrix(base, base + d))
            B.add(pr, M["Crystal"], uvw=1.3)
        translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), -min(v.co.z for v in B.bm.verts)))
        return B

    return fn


# ---------------------------------------------------------------------------
# Signature: floating moon chunk
# ---------------------------------------------------------------------------

def make_moon_chunk(kit):
    M = kit.M

    def fn():
        rng = random.Random(231)
        B = Builder(kit.name("MoonChunk"))
        bm = bm_ico((0, 0, 0), 1.0, subdiv=5)
        craters = [(Vector((rng.uniform(-1, 1), rng.uniform(-1, -0.2), rng.uniform(-0.3, 1))).normalized(),
                    rng.uniform(0.22, 0.5), rng.uniform(0.07, 0.14)) for _ in range(9)]
        for v in bm.verts:
            d = v.co.normalized()
            r = 1.0 + 0.07 * eh.mnoise.noise(d * 2.3 + Vector((1.7, 0.2, 3.1))) + 0.03 * eh.mnoise.noise(d * 6.1)
            for cdir, crad, cdep in craters:
                ang = d.angle(cdir)
                u = ang / crad
                if u < 1.0:
                    r -= cdep * (1 - u * u)
                elif u < 1.35:
                    r += cdep * 0.45 * math.sin((u - 1.0) / 0.35 * math.pi)
            v.co = d * r * Vector((2.05, 1.6, 1.7))
        bm_cut(bm, (0, 0, -0.85), (0.25, -0.15, -1.0))
        bm_cut(bm, (1.55, 0, 0), (1.0, 0.1, -0.35))
        B.add(bm, M["MoonRock"], smooth=False, hard=38, tint=tint(rng), uvw=0.8)
        for k in range(6):
            base = Vector((rng.uniform(-1.0, 1.0), rng.uniform(-0.8, 0.6), -0.95 + rng.uniform(-0.05, 0.05)))
            d = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.2), -1.0)).normalized()
            L = rng.uniform(0.3, 0.75)
            pr = bm_lathe([(L * 0.14, -0.1), (L * 0.15, L * 0.7), (0.0005, L)], segs=6, phase=rng.uniform(0, 1))
            transform(pr, eh.look_matrix(base, base + d))
            B.add(pr, M["Crystal"], uvw=1.0)
        for (p, d, L) in (((-1.2, -0.3, -0.6), (-0.4, 0.0, -1.0), 2.4), ((0.9, -0.4, -0.7), (0.3, 0.1, -1.0), 2.0),
                          ((0.2, 0.6, -0.8), (0.0, 0.3, -1.0), 2.6)):
            p, d = Vector(p), Vector(d).normalized()
            pts = [p + d * L * t + Vector((0.05 * math.sin(t * 5), 0, 0)) for t in lin(0, 1, 7)]
            bk.silk_thread(B, M["Silk"], pts, r=0.014)
        return B

    return fn


# ---------------------------------------------------------------------------
# Background silhouettes
# ---------------------------------------------------------------------------

def make_bg_near(kit):
    M = kit.M

    def fn():
        rng = random.Random(301)
        B = Builder(kit.name("BG_Near"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGStone"])
        S = M["BGStone"]
        bk.bg_box(B, rng, (-10, 0.3, 0.0), (10, 2.7, 6.0), S, 0.06)
        bk.bg_box(B, rng, (-10, 0.0, 5.9), (10, 3.0, 6.7), S, 0.06)
        bk.bg_box(B, rng, (-10, 0.0, 6.7), (10, 0.55, 7.6), S, 0.05)
        x = -9.6
        i = 0
        while x < 9.4:
            if not (0.6 < x < 3.2):
                bk.bg_box(B, rng, (x, 0.0, 7.55), (x + 0.75, 0.55, 8.35), S, 0.04)
            x += 1.35
            i += 1
        for cx in (-5.0, 0.0, 5.0):
            pts = [(cx - 1.9, -1.0), (cx + 1.9, -1.0)] + [(cx + 1.9 * math.cos(a), 3.6 + 1.9 * math.sin(a))
                                                          for a in lin(0, math.pi, 11)]
            cut.hole(bm_prism_xz(pts, -1.0, 4.0))
            bk.voussoirs(cut.post, rng, (cx, 3.6), 1.9, 2.35, -0.2, 0.32, 9, 0.06, S, key_extra=0.2, jitter_r=0.05,
                         bevel=0.05, segs=1, chips=0)
        for (tx, w, h) in ((-7.6, 2.6, 9.0), (6.4, 2.2, 8.4)):
            bk.bg_box(B, rng, (tx - w / 2, -0.4, 0.0), (tx + w / 2, 2.6, h), S, 0.06)
            roof = bm_lathe([(w * 0.62, h), (0.06, h + 1.6)], segs=8, phase=math.pi / 8)
            translate(roof, (tx, 1.1, 0))
            B.add(roof, M["BGRoof"], tint=tint(rng))
            for k in range(2):
                cut.window(bk.win_poly(tx, h - 3.0 - 2.2 * k, h - 2.0 - 2.2 * k, 0.36, "round"), -0.4, 0.35)
        for x0, x1, dz in ((-7.6, -3.0, 1.0), (-3.0, 0.4, 0.6), (3.6, 6.4, 0.8)):
            cut.post.add(bm_tube(bk.sag((x0, 0.2, 8.6 if x0 < -7 else 8.3), (x1, 0.2, 8.3 if x1 < 6 else 8.2), dz, 9),
                                 0.035, segs=4), M["BGSilk"], smooth=True)
        for x in (-4.2, -1.8, 4.5):
            cut.post.add(bm_tube([(x, 0.1, 7.6), (x + 0.1, 0.1, 6.2), (x - 0.05, 0.1, 4.9)], [0.03, 0.03, 0.01], segs=4),
                         M["BGSilk"], smooth=True)
        cut.breakage((1.9, 0.3, 7.9), (1.0, 0.8, 0.7), rng, n=2)
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_a(kit):
    """Observatory tower with a dome, telescope and crescent finial (~20 m)."""
    M = kit.M

    def fn():
        rng = random.Random(311)
        B = Builder(kit.name("BG_Far_A"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGStone"])
        S = M["BGStone"]
        yc = 2.6
        bk.bg_box(B, rng, (-3.0, 0.0, 0.0), (3.0, 5.2, 4.0), S, 0.1,
                  cuts=[((0, 0.7, 4.0), (0, -1, 1)), ((-2.3, 0, 4.0), (-1, 0, 1)), ((2.3, 0, 4.0), (1, 0, 1))])
        body = bm_lathe([(2.3, 3.4), (2.15, 9.0), (2.05, 14.6)], segs=12, phase=TAU_ / 24)
        translate(body, (0, yc, 0))
        B.add(body, S, tint=tint(rng))
        ring = bm_lathe([(2.4, 14.5), (2.4, 15.4)], segs=12, phase=TAU_ / 24)
        translate(ring, (0, yc, 0))
        B.add(ring, S, tint=tint(rng))
        dome = bm_lathe([(2.2, 15.3), (2.05, 16.4), (1.6, 17.4), (0.9, 18.0), (0.06, 18.25)], segs=12, phase=TAU_ / 24)
        translate(dome, (0, yc, 0))
        B.add(dome, M["BGRoof"], tint=tint(rng))
        tel = bm_lathe([(0.32, 0.0), (0.36, 2.6), (0.42, 2.7)], segs=8)
        transform(tel, eh.look_matrix(Vector((0.4, yc - 1.0, 16.6)), Vector((2.6, yc - 2.0, 18.4))))
        B.add(tel, M["BGBrass"], tint=tint(rng))
        cres = [(0.75 * math.cos(a), yc, 19.1 + 0.75 * math.sin(a)) for a in lin(rad(-50), rad(230), 12)]
        B.add(bm_tube(cres, [0.02] + [0.14] * 10 + [0.02], segs=5, up=Y, flatten=0.5), M["BGBrass"], smooth=True)
        B.add(bm_lathe([(0.06, 18.2), (0.06, 18.45)], segs=6), M["BGBrass"])
        for a_deg in (-20, 15):
            cut.window(bk.win_poly(0.0, 10.5, 12.0, 0.55, "round"), yc - 2.1, 0.4, rot_z=rad(a_deg), pivot=(0, yc, 0))
        cut.window(bk.win_poly(0.0, 6.0, 7.4, 0.4, "round"), yc - 2.2, 0.4)
        cut.window(bk.win_poly(0.0, 1.6, 3.0, 0.9, "round"), 0.0, 0.4)
        return bk.finish_bg(B, cut)

    return fn


def make_bg_far_b(kit):
    """Twin spires joined by a bridge, a moon shard tethered between them (~16 m)."""
    M = kit.M

    def fn():
        rng = random.Random(321)
        B = Builder(kit.name("BG_Far_B"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGStone"])
        S = M["BGStone"]
        for (cx, h, w) in ((-3.6, 12.0, 2.2), (3.4, 13.4, 2.0)):
            bk.bg_box(B, rng, (cx - w / 2 - 0.3, 0.0, 0.0), (cx + w / 2 + 0.3, w + 0.6, 1.4), S, 0.06)
            bk.bg_box(B, rng, (cx - w / 2, 0.3, 1.3), (cx + w / 2, w + 0.3, h), S, 0.06)
            roof = bm_lathe([(w * 0.78, h), (0.05, h + 2.6)], segs=4, phase=math.pi / 4)
            translate(roof, (cx, 0.3 + w / 2, 0))
            B.add(roof, M["BGRoof"], tint=tint(rng))
            for k in range(3):
                cut.window(bk.win_poly(cx, 3.0 + 3.0 * k, 4.0 + 3.0 * k, 0.32, "pointed"), 0.3, 0.3)
        bk.bg_box(B, rng, (-2.6, 0.5, 8.4), (2.5, 1.9, 9.3), S, 0.05)
        cut.hole(bm_prism_xz([(-2.0, 7.0), (1.9, 7.0)] + [(1.95 * math.cos(a) - 0.05, 7.6 + 1.95 * math.sin(a) * 0.4)
                                                         for a in lin(0, math.pi, 9)], -1.0, 3.0))
        rock = bm_ico((0.1, 1.2, 13.4), 1.0, (1.5, 1.0, 1.05), subdiv=2, rng=rng, jitter=0.12)
        bm_cut(rock, (0.1, 1.2, 12.9), (0.2, 0.0, -1.0))
        cut.post.add(rock, M["BGStone"], tint=(0.85, 0.0, 0.0, 1.0))
        for p0, p1, dz in (((0.1, 1.0, 12.6), (-3.6, 1.0, 11.5), 0.5), ((0.4, 1.0, 12.7), (3.4, 1.0, 12.4), 0.4),
                           ((0.0, 1.0, 12.4), (0.0, 1.0, 9.3), 0.0)):
            cut.post.add(bm_tube(bk.sag(p0, p1, dz, 8), 0.04, segs=4), M["BGSilk"], smooth=True)
        return bk.finish_bg(B, cut)

    return fn


def make_clock_tower(kit):
    M = kit.M

    def fn():
        rng = random.Random(331)
        B = Builder(kit.name("ClockTower"))
        cut = bk.Cutters(B.name, M["BGWindow"], M["BGStone"])
        S = M["BGStone"]
        bk.bg_box(B, rng, (-3.2, 0.0, 0.0), (3.2, 6.0, 3.0), S, 0.1, cuts=[((0, 0.6, 3.0), (0, -1, 1))])
        bk.bg_box(B, rng, (-2.6, 0.4, 2.8), (2.6, 5.6, 17.8), S, 0.08)
        for s in (-1, 1):
            x0, x1 = sorted((s * 3.0, s * 2.3))
            bk.bg_box(B, rng, (x0, 0.0, 2.8), (x1, 1.2, 11.0), S, 0.06, cuts=[((0, 0.5, 11.0), (0, -1, 1.2))])
        bk.bg_box(B, rng, (-2.95, 0.15, 17.7), (2.95, 5.85, 21.6), S, 0.08)
        bk.bg_box(B, rng, (-3.1, 0.0, 21.5), (3.1, 6.0, 21.9), S, 0.05)
        bk.bg_box(B, rng, (-2.5, 0.5, 21.9), (2.5, 5.5, 23.2), S, 0.05)
        roof = bm_lathe([(3.4, 23.1), (0.06, 25.0)], segs=4, phase=math.pi / 4)
        translate(roof, (0, 3.0, 0))
        B.add(roof, M["BGRoof"], tint=tint(rng))
        dial_c = Vector((0.0, 0.12, 19.65))
        dial = bm_prism_xz([(1.55 * math.cos(a), dial_c.z + 1.55 * math.sin(a)) for a in lin(0, TAU_, 25)[:-1]],
                           0.08, 0.16)
        cut.post.add(dial, M["BGDial"])
        rim = bm_lathe([(1.55, 0.0), (1.8, 0.0), (1.8, -0.12), (1.55, -0.12), (1.55, 0.0)], segs=24, cap_top=False,
                       cap_bottom=False)
        rotate(rim, math.pi / 2, "X")
        translate(rim, dial_c)
        cut.post.add(rim, M["BGBrass"])
        for k in range(12):
            a = TAU_ * k / 12
            mk = bm_box((-0.05, -0.04, 1.2), (0.05, 0.0, 1.45))
            rotate(mk, a, "Y")
            translate(mk, dial_c + Vector((0, -0.02, 0)))
            cut.post.add(mk, M["BGBrass"])
        for (L, w, a) in ((1.0, 0.09, rad(40)), (1.35, 0.06, rad(-115))):
            hd = bm_box((-w / 2, -0.06, -0.1), (w / 2, -0.02, L))
            rotate(hd, a, "Y")
            translate(hd, dial_c)
            cut.post.add(hd, M["BGBrass"])
        for x in (-1.2, 1.2):
            cut.window(bk.win_poly(x, 22.1, 22.7, 0.7, "round"), 0.5, 0.5)
        for z in (6.0, 10.0, 14.0):
            cut.window(bk.win_poly(0.0, z, z + 1.6, 0.45, "pointed"), 0.4, 0.35)
        cut.breakage((2.6, 0.6, 24.0), (0.8, 1.0, 0.9), rng, n=2)
        return bk.finish_bg(B, cut)

    return fn


# ---------------------------------------------------------------------------

def chunk_extras(put):
    put("MoonChunk", (12.4, 2.6, 6.9))


def make_kit():
    kit = bk.Kit(ID)
    kit.make_materials = materials
    kit.chunk_extras = chunk_extras
    kit.chunk_bg = "#14112A"
    kit.light = dict(key=2.6, rim=3.2)
    kit.emission = {"silk / orb": GLOW, "moon crystals": "#CFE8FF", "BG windows": GLOW, "clock dial": "#D8E8FF"}
    for role in ("Fill_A", "Fill_B", "Fill_C", "Top_A", "Top_B", "Edge_L"):
        kit.add(role, make_tile(kit, role), 1.6, 1500, "1x1 tile, pivot bottom-left, top y=1, front z=-0.9"
                + (" ; moon-dust lip" if role[0] in "TE" else ""), tile=True)
    kit.add("Edge_R", bk.mirror_tile(make_tile(kit, "Edge_L"), kit.name("Edge_R")), 1.6, 1500,
            "right platform end (mirror of Edge_L)", tile=True)
    kit.add("Platform", make_platform(kit), 1.5, 1500, "one-way stone beam 1 m, deck top y=1, corbel below")
    kit.add("BackWall", make_backwall(kit), 0.75, 3600, "4x4 ashlar back wall, seamless (game tiles it at 2x2)")
    kit.add("Pillar", make_pillar(kit), 0.9, 6000, "octagonal rampart column 5 m, brass bands, crescent finial")
    kit.add("Arch", make_arch(kit), 0.85, 6000, "rampart arch 6 m with glowing tick-silk web")
    kit.add("Light", make_light(kit), 2.0, 4000, "moon lantern; LightSocket = orb centre (pale blue)")
    kit.add("Hang", make_hang(kit), 1.4, 4000, "glowing silk strands + cocoon, pivot at top, ~2.8 m")
    kit.add("Door", make_door(kit), 1.1, 6000, "arched gate with half-raised portcullis, recess 0.78 m")
    kit.add("Prop_A", make_prop_a(kit), 1.3, 4000, "brass clockwork debris")
    kit.add("Prop_B", make_prop_b(kit), 1.3, 4000, "toppled merlon rubble with moon dust")
    kit.add("Prop_C", make_prop_c(kit), 1.3, 4000, "moon-crystal cluster (emissive)")
    kit.add("MoonChunk", make_moon_chunk(kit), 0.6, 6000, "floating moon shard ~4 m, pivot centre, silk tethers")
    kit.add("BG_Near", make_bg_near(kit), 1.0, 10000, "rampart causeway 20x10 m (Unity z=5)", atlas="BG")
    kit.add("BG_Far_A", make_bg_far_a(kit), 1.0, 10000, "observatory tower ~19 m (Unity z=10)", atlas="BG")
    kit.add("BG_Far_B", make_bg_far_b(kit), 1.0, 10000, "twin spires + tethered moon shard ~16 m (z=16)", atlas="BG")
    kit.add("ClockTower", make_clock_tower(kit), 1.0, 10000, "far clock tower 25 m, glowing dial", atlas="BG")
    return kit
