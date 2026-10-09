"""Shared framework for the biome environment kits (see Tools/BIOMES.md).

A biome file (Tools/Blender/biomes/<id>.py) creates a `Kit`, fills
`kit.M` with procedural materials and registers module specs; this module
builds them, packs the two shared atlases (<Id>_Kit 2048 / <Id>_BG 1024),
bakes, exports `<Id>_<Role>.fbx`, writes `biome_manifest.json` and renders
the verification previews.  Geometry helpers here are biome-agnostic and
parameterised by materials / callbacks.
"""

import json
import math
import random
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

import dc_common as dc
import env_helpers as eh
from env_helpers import (Builder, block, bm_blob, bm_box, bm_cut, bm_ico, bm_lathe, bm_prism_xz, bm_tube,
                         delete_faces, rotate, scale, transform, translate)

TAU = math.tau
G = 0.045             # mortar gap between foreground blocks
TF, TB = -0.9, 1.6    # tile front / back planes
X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))

BAKE_GPU = False   # set by build_biome.py --gpu

REQUIRED_ROLES = ["Fill_A", "Fill_B", "Fill_C", "Top_A", "Top_B", "Edge_L", "Edge_R", "Platform", "BackWall",
                  "Pillar", "Arch", "Light", "Hang", "Door", "Prop_A", "Prop_B", "Prop_C", "BG_Near", "BG_Far_A",
                  "BG_Far_B"]


def rad(d):
    return math.radians(d)


def lin(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def hex_mix(a, b, t):
    ca = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def tint(rng, r=(0.25, 0.75), g=(0.0, 0.0), b=(0.0, 0.25)):
    return (rng.uniform(*r), rng.uniform(*g), rng.uniform(*b), 1.0)


def material(name, base, dark=None, light=None, fx=None, **kw):
    """dc.make_material + optional eh.enhance layers."""
    m = dc.make_material(name, base, dark=dark or base, light=light or base, **kw)
    if fx:
        eh.enhance(m, **fx)
    return m


# ---------------------------------------------------------------------------
# Kit / specs
# ---------------------------------------------------------------------------

class Spec:
    def __init__(self, role, fn, weight=1.0, budget=4000, usage="", atlas="Kit", tile=False):
        self.role, self.fn, self.weight, self.budget = role, fn, weight, budget
        self.usage, self.atlas, self.tile = usage, atlas, tile


class Kit:
    def __init__(self, biome_id):
        self.id = biome_id
        self.root = dc.ART_ROOT / "Biomes" / biome_id
        self.mesh_dir = self.root / "Meshes"
        self.tex_dir = self.root / "Textures"
        self.manifest = self.root / "biome_manifest.json"
        self.out = dc.OUT_ROOT / "biomes" / biome_id
        self.M = {}
        self.specs = []
        self.make_materials = None
        self.chunk_extras = None
        self.chunk_bg = "#101A24"
        self.emission = {}
        self.light = dict(key=3.0, rim=3.5)

    def name(self, role):
        return f"{self.id}_{role}"

    def add(self, role, fn, weight=1.0, budget=4000, usage="", atlas="Kit", tile=False):
        self.specs.append(Spec(role, fn, weight, budget, usage, atlas, tile))


# ---------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------

def dome_rivet(pos, r=0.016, facing=Vector((0, -1, 0)), segs=6):
    bm = bm_lathe([(r, 0.0), (r * 0.8, r * 0.45), (r * 0.4, r * 0.75)], segs=segs, cap_bottom=True)
    return transform(bm, eh.look_matrix(Vector(pos), Vector(pos) + Vector(facing)))


def beam(p0, p1, w, h, rng, bevel=0.015, chips=0, segs=1, roll=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    pcs = block((-w / 2, -h / 2, 0.0), (w / 2, h / 2, L), rng, chips=chips, bevel=bevel, segs=segs,
                corners=[(-1, -1, 1), (1, -1, 1), (-1, -1, -1), (1, -1, -1)])
    m = eh.look_matrix(p0, p1, roll)
    return [transform(p, m) for p in pcs]


def inset_front(bm, thickness, depth):
    """Rusticated ashlar: raised (depth>0) or sunken centre panel on the -Y face."""
    bm.normal_update()
    fr = [f for f in bm.faces if f.normal.y < -0.9]
    if fr:
        f = min(fr, key=lambda f: f.calc_center_median().y)
        bmesh.ops.inset_region(bm, faces=[f], thickness=thickness, depth=depth, use_even_offset=True)
    return bm


def voussoirs(B, rng, center, r_in, r_out, y0, y1, n, gap, mat, *, key_extra=0.2, jitter_r=0.06, start=0.0,
              end=math.pi, bevel=0.025, segs=1, env=None, tint_g=0.0, chips=1, skip=None, inset=None):
    cx, cz = center
    rm = (r_in + r_out) / 2
    ga = gap / rm
    span = ((end - start) - (n - 1) * ga) / n
    for i in range(n):
        if skip and skip(i):
            continue
        a0 = start + i * (span + ga)
        a1 = a0 + span
        am = (a0 + a1) / 2
        ro = r_out + rng.uniform(-jitter_r, jitter_r)
        if i == n // 2:
            ro = r_out + key_extra
        poly = [(cx + r_in * math.cos(a0), cz + r_in * math.sin(a0)),
                (cx + ro * math.cos(a0), cz + ro * math.sin(a0)),
                (cx + ro * math.cos(am), cz + ro * math.sin(am)),
                (cx + ro * math.cos(a1), cz + ro * math.sin(a1)),
                (cx + r_in * math.cos(a1), cz + r_in * math.sin(a1))]
        yf = y0 + rng.uniform(-0.02, 0.02)
        bm = bm_prism_xz(poly, yf, y1)
        if inset:
            inset_front(bm, *inset)
        for _ in range(chips):
            eh.chip_vertex(bm, rng, rng.uniform(0.04, 0.1), pick=lambda co, yf=yf: co.y < yf + 1e-4)
        eh.bm_bevel(bm, bevel, segs)
        delete_faces(bm, lambda c, nn: nn.y > 0.9 and c.y > y1 - 0.05)
        if env is not None:
            eh.bm_append(env, bm)
        B.add(bm, mat, tint=(rng.uniform(0.3, 0.7), tint_g, rng.uniform(0, 0.2), 1.0))


def pier(B, rng, x0, x1, courses, mat, y0=0.0, y1=0.8, z=0.0, segs=1, bevel=0.03, grime_h=1.6, inset=None,
         grime=0.8):
    for k, h in enumerate(courses):
        two = (k % 2 == 1)
        splits = [x0, x0 + (x1 - x0) * rng.uniform(0.4, 0.6), x1] if two else [x0, x1]
        for j in range(len(splits) - 1):
            lo = (splits[j] + G / 2, y0 + rng.uniform(-0.025, 0.02), z + G / 2)
            hi = (splits[j + 1] - G / 2, y1, z + h - G / 2)
            pcs = block(lo, hi, rng, chips=rng.randint(1, 2), chip_size=(0.04, 0.12), bevel=bevel, segs=segs,
                        jitter=0.015, back_delete=y1 - 0.05, pre=(lambda bm: inset_front(bm, *inset)) if inset else None)
            t = rng.uniform(0.25, 0.75)
            B.add(pcs, mat, tint_fn=lambda co, n, t=t: (t, max(0.0, 1.0 - co.z / grime_h) * grime, 0.08, 1.0))
        z += h
    return z


L_IN, W_IN, WIRE = 0.146, 0.066, 0.017


def chain_link(segs=6, path_pts=12, s=1.0):
    a = (W_IN / 2 + WIRE) * s
    hl = (L_IN / 2 + WIRE) * s
    st = hl - a
    half = path_pts // 2
    pts = []
    for i in range(half):
        t = math.pi * i / (half - 1)
        pts.append((a * math.cos(t), 0.0, st + a * math.sin(t)))
    for i in range(half):
        t = math.pi + math.pi * i / (half - 1)
        pts.append((a * math.cos(t), 0.0, -st + a * math.sin(t)))
    return bm_tube(pts, WIRE * s, segs=segs, up=Y, closed=True)


def chain(B, rng, top, length, mat, s=1.0, segs=6, path_pts=12, uvw=1.3):
    """Hanging chain whose first link's top inner contact is at `top`."""
    top = Vector(top)
    c = top.z - L_IN * s / 2
    k = 0
    while (top.z - c) + L_IN * s / 2 + WIRE * s < length:
        bm = chain_link(segs, path_pts, s)
        if k % 2:
            rotate(bm, math.pi / 2, "Z")
        rotate(bm, rng.uniform(-0.05, 0.05), "Z")
        translate(bm, (top.x, top.y, c))
        B.add(bm, mat, smooth=True, uvw=uvw, tint=tint(rng))
        c -= L_IN * s
        k += 1
    return c + L_IN * s - L_IN * s / 2   # bottom inner contact of last link


def bm_bone(p0, p1, r=0.016, knob=0.03, segs=6):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    k = min(knob, L / 6)
    prof = [(k * 0.55, 0.0), (k, k * 0.6), (k * 0.85, k * 1.6), (r, k * 2.7), (r * 0.9, L / 2), (r, L - k * 2.7),
            (k * 0.85, L - k * 1.6), (k, L - k * 0.6), (k * 0.55, L)]
    bm = bm_lathe(prof, segs=segs, scale_xy=(1.15, 0.85))
    return transform(bm, eh.look_matrix(p0, p1))


def bm_skull(center, rng, size=1.0, yaw=0.0, pitch=0.0, roll=0.0, segs=(10, 7)):
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0, calc_uvs=True)
    eyes = [Vector((0.042, -0.1, 0.0)) * size, Vector((-0.042, -0.1, 0.0)) * size]
    nose = Vector((0.0, -0.11, -0.04)) * size
    for v in bm.verts:
        c = Vector((v.co.x * 0.092, v.co.y * 0.112, v.co.z * 0.1)) * size
        if c.z < -0.03 * size and c.y < 0:
            c.y *= 0.82
            c.x *= 0.85
        for e in eyes:
            d = (c - e).length
            if d < 0.05 * size:
                c += (Vector((0, 0.04, 0)) * size) * (1 - d / (0.05 * size))
        if (c - nose).length < 0.035 * size:
            c.y += 0.018 * size
        v.co = c
    jaw = bm_box((-0.045 * size, -0.1 * size, -0.03 * size), (0.045 * size, -0.02 * size, 0.0))
    eh.bm_bevel(jaw, 0.008 * size, 1)
    translate(jaw, (0, 0.0, -0.075 * size))
    rotate(jaw, rad(18), "X", (0, -0.02 * size, -0.075 * size))
    m = Matrix.Translation(Vector(center)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "X") @ \
        Matrix.Rotation(roll, 4, "Y")
    transform(bm, m)
    transform(jaw, m)
    return bm, jaw


def rib(center, ax, ay, r=0.011, tilt=0.15, a0=15, a1=165, segs=4, n=8):
    c = Vector(center)
    pts = [c + Vector((ax * math.cos(a), -ay * math.sin(a), -tilt * math.sin(a) * ay)) for a in lin(rad(a0), rad(a1), n)]
    return bm_tube(pts, r, segs=segs, cap=True)


def bm_gear(r_tip, r_root, teeth, thickness, *, r_rim_in=None, hub_r=None, spokes=6, spoke_w=None,
            tooth_frac=0.45, y0=0.0):
    """Spur gear lying in the x-z plane (axis = Y), front face at y0.  Built
    from convex pieces (tooth sectors, spokes, hub) so it needs no booleans."""
    r_rim_in = r_rim_in if r_rim_in is not None else r_root * 0.8
    pieces = []
    y1 = y0 + thickness
    for i in range(teeth):
        a0 = TAU * i / teeth
        a1 = TAU * (i + 1) / teeth
        am = (a0 + a1) / 2
        hw = (a1 - a0) * tooth_frac / 2
        tip_hw = hw * 0.62
        poly = [(r_rim_in * math.cos(a0), r_rim_in * math.sin(a0)), (r_root * math.cos(a0), r_root * math.sin(a0)),
                (r_root * math.cos(am - hw), r_root * math.sin(am - hw)),
                (r_tip * math.cos(am - tip_hw), r_tip * math.sin(am - tip_hw)),
                (r_tip * math.cos(am + tip_hw), r_tip * math.sin(am + tip_hw)),
                (r_root * math.cos(am + hw), r_root * math.sin(am + hw)),
                (r_root * math.cos(a1), r_root * math.sin(a1)), (r_rim_in * math.cos(a1), r_rim_in * math.sin(a1))]
        pieces.append(bm_prism_xz(poly, y0, y1))
    hub_r = hub_r or r_root * 0.22
    spoke_w = spoke_w or r_root * 0.16
    for k in range(spokes):
        a = TAU * k / spokes + TAU / (spokes * 2)
        sp = bm_box((hub_r * 0.6, y0 + thickness * 0.15, -spoke_w / 2), (r_rim_in + 0.02, y1 - thickness * 0.15, spoke_w / 2))
        rotate(sp, -a, "Y")
        pieces.append(sp)
    hub = bm_lathe([(hub_r, -thickness * 0.15), (hub_r, thickness * 1.15)], segs=16)
    rotate(hub, -math.pi / 2, "X")
    translate(hub, (0, y0, 0))
    pieces.append(hub)
    return pieces


def pipe(B, pts, r, mat, *, segs=10, flanges=(), flange_mat=None, rng=None):
    B.add(bm_tube(pts, r, segs=segs), mat, smooth=True, tint=tint(rng) if rng else None)
    for (p, d) in flanges:
        fl = bm_lathe([(r * 1.35, -0.035), (r * 1.35, 0.035)], segs=segs)
        transform(fl, eh.look_matrix(Vector(p), Vector(p) + Vector(d)))
        B.add(fl, flange_mat or mat, hard=40)


def silk_thread(B, mat, pts, r=0.006, segs=4):
    B.add(bm_tube(pts, [r] * (len(pts) - 1) + [r * 0.5], segs=segs), mat, smooth=True, uvw=0.6)


def sag(p0, p1, droop, n=7):
    p0, p1 = Vector(p0), Vector(p1)
    return [p0.lerp(p1, t) + Vector((0, 0, -droop * 4 * t * (1 - t))) for t in lin(0, 1, n)]


# ---------------------------------------------------------------------------
# 1x1 tiles (Fill / Top / Edge)
# ---------------------------------------------------------------------------

def tile_uvw(c, n):
    if n.z < -0.9 or n.y > 0.5:
        return 0.3
    return 1.0 if c.y < -0.45 else 0.28


def stone_block_fn(mat, *, chips=(1, 3), chip_size=(0.035, 0.12), bevel=0.026, segs=2, jitter=0.012, inset=None,
                   top_grime=0.0, crack_gap=0.032, front_jitter=0.03, extra=None):
    """Block maker for tile_body: chipped bevelled full-depth stone block."""

    def fn(B, rng, lo, hi, ctx):
        yf = lo[1] + rng.uniform(-front_jitter, front_jitter)
        corners = [(-1, -1, -1), (1, -1, -1), (-1, -1, 1), (1, -1, 1)]
        nchips = rng.randint(*chips)
        size = chip_size
        if ctx["outer"]:
            corners = [(-1, -1, -1), (1, -1, 1)] if ctx["top"] else [(-1, -1, -1), (-1, -1, 1), (1, -1, 1)]
            nchips = max(nchips, 2)
            size = (chip_size[0] * 1.4, chip_size[1] * 1.3)
        ck = None
        if ctx["crack"]:
            ck = (((lo[0] + hi[0]) / 2 + rng.uniform(-0.06, 0.06), 0.0, (lo[2] + hi[2]) / 2),
                  (1.0, 0.0, rng.uniform(-0.6, 0.6)))
        pre = (lambda bm: inset_front(bm, *inset)) if inset else None
        pieces = block((lo[0], yf, lo[2]), hi, rng, chips=nchips, chip_size=size, corners=corners, bevel=bevel,
                       segs=segs, jitter=jitter, fixed_top=1.0 if ctx["top"] else None, splits_y=(-0.45,),
                       cuts=ctx["cuts"], crack=ck, crack_gap=crack_gap, back_delete=1.0, bevel_back=1.0, pre=pre)
        t = (rng.uniform(0.2, 0.8), top_grime if ctx["top"] else rng.uniform(0.0, 0.2), rng.uniform(0.0, 0.25), 1.0)
        B.add(pieces, mat, tint=t, uvw_fn=tile_uvw)
        if extra:
            extra(B, rng, (lo[0], yf, lo[2]), hi, ctx)

    return fn


def edge_cuts(edge_r):
    c = Vector((0.02 + edge_r, 0.0, 1.0 - edge_r))
    cuts = []
    for phi in (20, 45, 70):
        n = Vector((-math.sin(rad(phi)), 0.0, math.cos(rad(phi))))
        cuts.append((c + n * edge_r, n))
    return cuts


def tile_body(B, rng, rows, block_fn, core_mat, *, edge=None, edge_r=0.22, crack=None, gap=G, core=True):
    if core:
        cb = bm_box((0.07, -0.86, 0.07), (0.93, TB, 0.955))
        delete_faces(cb, lambda c, n: n.y > 0.9)
        B.add(cb, core_mat, uvw=0.3)
    for ri, (z0, z1, splits) in enumerate(rows):
        top = z1 >= 0.999
        xs = [0.0] + list(splits) + [1.0]
        for bi in range(len(xs) - 1):
            x0, x1 = xs[bi] + gap / 2, xs[bi + 1] - gap / 2
            zz0 = z0 + gap / 2
            zz1 = 1.0 if top else z1 - gap / 2
            outer = edge == "L" and bi == 0
            ctx = dict(top=top, row=ri, col=bi, ncols=len(xs) - 1, edge=edge, outer=outer,
                       cuts=edge_cuts(edge_r) if (outer and top and edge_r > 0) else [],
                       crack=(crack == (ri, bi)))
            block_fn(B, rng, (x0, TF, zz0), (x1, TB, zz1), ctx)


def lip_cover(B, rng, seed, mat, *, edge=None, edge_r=0.22, base=0.08, amp=0.05, dmin=0.035, dmax=0.2,
              top_depth=0.42, offset=0.022, lump_amp=0.016, lump_freq=7.0, strands=None, clumps=None,
              zmax=1.055, front=-0.935):
    """Biome covering concentrated on the walkable tile's front lip (top strip
    `top_depth` deep, draping down the front face; wraps the side for Edge_L).
    Back edge is feathered into the top surface.  Returns the drape fn."""
    r2 = 0.04
    if edge == "L":
        R = max(edge_r, 0.06)
        cx, cz = 0.02 + R, 1.0 - R
        prof = [(cx + (R - r2) * math.cos(a), cz + (R - r2) * math.sin(a)) for a in lin(rad(90), rad(180), 7)]
        prof += [(0.02 + r2, -0.5), (2.0, -0.5), (2.0, 1.0 - r2)]
    else:
        prof = [(-1.0, 1.0 - r2), (-1.0, -0.5), (2.0, -0.5), (2.0, 1.0 - r2)]
    env = eh.bm_rounded_prism(prof, front + r2, 2.6, r2)
    bvh = eh.envelope_bvh(env)
    env.free()
    coef = [rng.uniform(-amp * 0.7, amp) / math.sqrt(k) for k in range(1, 7)]

    def D(x):
        x = min(max(x, 0.0), 1.0)
        v = base + sum(coef[k - 1] * math.sin(math.pi * k * x) for k in range(1, 7))
        return min(max(v, dmin), dmax)

    def Ds(y):
        return D(0.0) + (dmax - D(0.0)) * 0.55 * math.sin(min(1.0, (y + 1.3) / 1.0) * math.pi / 2) * \
            (0.65 + 0.35 * math.sin(3.7 * y + seed))

    def lump(p):
        x = p.x
        w = 1.0 if (edge == "L" and x < 0.5) else max(0.0, math.sin(math.pi * min(max(x, 0.0), 1.0))) ** 0.7
        return lump_amp * w * max(0.0, eh.periodic_noise(x, p.y, p.z, freq=lump_freq, seed=seed * 1.7) + 0.25)

    yb = TF + top_depth
    top_ys = [yb, TF + top_depth * 0.62, TF + top_depth * 0.3, -0.8]
    front_ts = [0.0, 0.42, 0.78, 1.0]
    if edge == "L":
        xs = [-0.3, 0.02, 0.08, 0.15, 0.24, 0.34] + [0.34 + 0.66 * i / 7 for i in range(1, 8)]
        sheet = eh.moss_net(bvh, xs, top_ys, front_ts, D, side_ys=list(reversed(top_ys)), side_drape=Ds,
                            side_x_out=-0.3, offset=offset, lump=lump, zmax=zmax, tuck_back=True)
    else:
        xs = [i / 14 for i in range(15)]
        sheet = eh.moss_net(bvh, xs, top_ys, front_ts, D, offset=offset, lump=lump, zmax=zmax, tuck_back=True)
    B.add(sheet, mat, smooth=True, uvw_fn=lambda c, n: 1.0 if c.y < -0.4 else 0.4)
    yfront = front - offset - 0.001
    if strands:
        n, lr, wr, smat = strands
        n = n - 1 if edge else n
        for k in range(n):
            x = 0.1 + 0.8 * (k + rng.uniform(0.15, 0.85)) / n
            topp = (x, yfront, 1.0 - D(x) + 0.035)
            B.add(eh.moss_strand(topp, rng.uniform(*lr), rng, width=rng.uniform(*wr)), smat or mat, smooth=True)
        if edge == "L":
            for _ in range(2):
                y = rng.uniform(-0.8, -0.5)
                B.add(eh.moss_strand((-0.012, y, 1.0 - Ds(y) + 0.03), rng.uniform(lr[0], lr[1] * 0.8), rng,
                                     width=wr[1] * 0.8, face_dir=Vector((-1, 0, 0))), smat or mat, smooth=True)
    if clumps:
        n, rr, sc = clumps
        pts = [((rng.uniform(0.15, 0.85), -0.9, 0.995), rng.uniform(*rr)) for _ in range(n)]
        if edge == "L":
            pts.append(((0.06, -0.88, 0.97), rr[1] * 1.2))
        for c, r in pts:
            bm = bm_blob(c, r, sc, segs=7, rings=5, rng=rng, jitter=0.15)
            for v in bm.verts:
                v.co.z = min(v.co.z, zmax)
                v.co.y = max(v.co.y, TF - 0.077)
            B.add(bm, mat, smooth=True)
    return D


def clamp_tile(B):
    for v in B.bm.verts:
        v.co.y = max(v.co.y, TF - 0.079)
        if 0.0 <= v.co.x <= 1.0 and TF <= v.co.y <= TB:
            v.co.z = min(v.co.z, 1.058)


def mirror_tile(builder_fn, name):
    def fn():
        B = builder_fn()
        B.name = name
        B.mirror_x(0.5)
        return B
    return fn


def ledge_cover(B, rng, mat, x0, x1, y_front, y_back, z_top, *, depth=(0.05, 0.22), strands=0, strand_mat=None,
                seed=0.0, env_z0=None, offset=0.025, lump_amp=0.03, strand_len=(0.15, 0.4), strand_w=0.035):
    """Covering blanket over the top + front edge of a rectangular ledge."""
    r2 = 0.03
    z0 = env_z0 if env_z0 is not None else z_top - 1.0
    prof = [(x0 + r2, z_top - r2), (x0 + r2, z0), (x1 - r2, z0), (x1 - r2, z_top - r2)]
    env = eh.bm_rounded_prism(prof, y_front + r2, y_back, r2)
    bvh = eh.envelope_bvh(env)
    env.free()
    amp = [rng.uniform(-0.04, 0.06) for _ in range(5)]
    w = x1 - x0

    def D(x):
        u = min(max((x - x0) / w, 0.0), 1.0)
        v = depth[0] + (depth[1] - depth[0]) * (0.5 + sum(amp[k] * math.sin(math.pi * (k + 1) * u * 1.7 + k) for k in range(5)) * 2)
        return min(max(v, depth[0]), depth[1]) * (math.sin(math.pi * u) ** 0.35)

    xs = lin(x0 + 0.02, x1 - 0.02, max(6, int(w / 0.09)))
    ys = lin(y_back, y_front + 0.05, 4)
    sheet = eh.moss_net(bvh, xs, ys, [0.0, 0.5, 1.0], D, y_out=y_front - 0.4, z_out=z_top + 0.4, z_ref=z_top,
                        offset=offset,
                        lump=lambda p: lump_amp * max(0.0, eh.periodic_noise(p.x * 0.7, p.y, p.z, 6.0, seed) + 0.3))
    B.add(sheet, mat, smooth=True)
    for _ in range(strands):
        x = rng.uniform(x0 + 0.1 * w, x1 - 0.1 * w)
        B.add(eh.moss_strand((x, y_front - 0.035, z_top - D(x) + 0.03), rng.uniform(*strand_len), rng,
                             width=strand_w), strand_mat or mat, smooth=True)
    return D


# ---------------------------------------------------------------------------
# Seamless 4 x 4 m back walls
# ---------------------------------------------------------------------------

def _wrap_spans(a, b, P):
    if b > P and a < P:
        return [(a, P, True, False), (0.0, b - P, False, True)]
    if a >= P:
        return [(a - P, b - P, True, True)]
    return [(a, b, True, True)]


def masonry_wall(B, rng, mat, mortar_mat, *, rows, width=(0.9, 1.6), gap=0.06, depth=0.4, bevel=0.045, segs=2,
                 front_jitter=0.03, chips=(0, 2), inset=None, P=4.0, block_hook=None, mortar_y=0.14):
    """Seamless masonry: rows sum to P, bricks crossing x=P are split into two
    flush halves (no bevel / faces on the cut) so panels tile in x and z."""
    s = sum(rows)
    rows = [r * P / s for r in rows]
    z = 0.0

    def on_boundary(e):
        return all(abs(v.co.x) < 1e-4 for v in e.verts) or all(abs(v.co.x - P) < 1e-4 for v in e.verts)

    for ri, h in enumerate(rows):
        widths = []
        while sum(widths) < P - width[0] * 0.6:
            widths.append(rng.uniform(*width))
        widths.append(P - sum(widths))
        if widths[-1] < width[0] * 0.55:
            widths[-2] += widths[-1]
            widths.pop()
        x = rng.uniform(0.0, P)
        for bi, w in enumerate(widths):
            a, b = x, x + w
            x = b
            d = rng.uniform(-front_jitter, front_jitter)
            t = (rng.uniform(0.2, 0.8), 0.0, rng.uniform(0.0, 0.3), 1.0)
            nchips = rng.randint(*chips)
            seed = rng.random()
            for (x0, x1, gl, gr) in _wrap_spans(a % P if a >= P else a, (a % P if a >= P else a) + w, P):
                lo = (x0 + (gap / 2 if gl else 0.0), d, z + gap / 2)
                hi = (x1 - (gap / 2 if gr else 0.0), depth, z + h - gap / 2)
                if hi[0] - lo[0] < 0.08:
                    continue
                corners = ([(-1, -1, -1), (-1, -1, 1)] if gl else []) + ([(1, -1, -1), (1, -1, 1)] if gr else [])
                bm = bm_box(lo, hi)
                if inset and gl and gr:
                    inset_front(bm, *inset)
                cr = random.Random(seed)
                for c in cr.sample(corners, min(nchips, len(corners))):
                    p = Vector((hi[0] if c[0] > 0 else lo[0], lo[1], hi[2] if c[2] > 0 else lo[2]))
                    eh.chip_corner(bm, p, c, cr, (0.05, 0.14), (hi[0] - lo[0], depth, h))
                eh.bm_bevel(bm, bevel, segs, edge_filter=lambda e: not on_boundary(e))
                delete_faces(bm, lambda c_, n: (n.y > 0.9) or (abs(n.x) > 0.9 and (abs(c_.x) < 1e-3 or abs(c_.x - P) < 1e-3)))
                B.add(bm, mat, tint=t, uvw_fn=lambda c_, n: 0.4 if n.y > 0.5 else 1.0)
                if block_hook and gl and gr:
                    block_hook(B, rng, lo, hi, ri, bi)
        z += h
    backing_plane(B, mortar_mat, P, mortar_y)


def backing_plane(B, mat, P=4.0, y=0.14):
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in ((0, y, 0), (P, y, 0), (P, y, P), (0, y, P))]
    f0 = bm.faces.new(vs)
    bm.normal_update()
    if f0.normal.y > 0:
        f0.normal_flip()
    B.add(bm, mat, uvw=0.35)


# ---------------------------------------------------------------------------
# Background silhouettes
# ---------------------------------------------------------------------------

def win_poly(x, z0, z1, w, kind="round"):
    pts = [(x - w / 2, z0), (x + w / 2, z0), (x + w / 2, z1)]
    if kind == "round":
        pts += [(x + w / 2 * math.cos(a), z1 + w / 2 * math.sin(a)) for a in lin(0, math.pi, 7)[1:-1]]
    elif kind == "pointed":
        pts += [(x + w * 0.32, z1 + w * 0.42), (x, z1 + w * 0.8), (x - w * 0.32, z1 + w * 0.42)]
    pts += [(x - w / 2, z1)]
    return pts


class Cutters:
    def __init__(self, name, win_mat, stone_mat):
        self.win = Builder(name + "_cutwin")
        self.post = Builder(name + "_post")
        self.brk = []
        self.axes = []
        self.name = name
        self.win_mat, self.stone_mat = win_mat, stone_mat

    def window(self, poly, y_front, depth, rot_z=0.0, pivot=(0, 0, 0)):
        bm = bm_prism_xz(poly, y_front - 1.5, y_front + depth)
        if rot_z:
            rotate(bm, rot_z, "Z", pivot)
        self.axes.append(Matrix.Rotation(rot_z, 3, "Z") @ Y)
        self.win.add(bm, self.win_mat)

    def hole(self, bm):
        b = Builder(f"{self.name}_hole{len(self.brk)}")
        b.add(bm, self.stone_mat)
        self.brk.append(b)

    def breakage(self, center, size, rng, n=3):
        for k in range(n):
            c = Vector(center) + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.35 * Vector(size)
            pts = [c + Vector((rng.uniform(-1, 1) * size[0], rng.uniform(-1, 1) * size[1], rng.uniform(-1, 1) * size[2]))
                   for _ in range(9)]
            self.hole(eh.bm_hull(pts))


def finish_bg(B, cut, keep_back=False):
    obj = B.build()
    cutters = []
    if cut.win.bm.faces:
        cutters.append(cut.win.build())
    else:
        cut.win.bm.free()
    for b in cut.brk:
        cutters.append(b.build())
    for c in cutters:
        mod = obj.modifiers.new("bool_" + c.name, "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = c
        mod.material_mode = "TRANSFER"
        mod.use_self = True
        mod.use_hole_tolerant = True
        c.hide_render = True
        c.hide_set(True)
    dc.apply_all_modifiers(obj)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)
    if cut.post.bm.faces:
        post = cut.post.build()
        obj = dc.join([obj, post], B.name)
    else:
        cut.post.bm.free()
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    mats = list(me.materials)
    win_i = next((i for i, m in enumerate(mats) if m and m == cut.win_mat), None)
    stone_i = next((i for i, m in enumerate(mats) if m and m == cut.stone_mat), 0)
    if win_i is not None:
        for f in bm.faces:
            if f.material_index == win_i and not any(abs(f.normal.dot(a)) > 0.75 for a in cut.axes):
                f.material_index = stone_i
    dead = [f for f in bm.faces if (f.normal.y > 0.55 and not keep_back) or
            (f.normal.z < -0.9 and f.calc_center_median().z < 0.05)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    lim = rad(32)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim) and len(e.link_faces) == 2
    for f in bm.faces:
        f.smooth = True
    uvw = bm.faces.layers.float.get("dc_uvw")
    if uvw:
        for f in bm.faces:
            if f[uvw] <= 0.0:
                f[uvw] = 1.0
    bm.to_mesh(me)
    bm.free()
    return obj


def bg_box(B, rng, lo, hi, mat, bevel=0.06, cuts=(), t=None):
    bm = bm_box(lo, hi)
    for co, no in cuts:
        bm_cut(bm, co, no)
    eh.bm_bevel(bm, bevel, 1)
    B.add(bm, mat, tint=t or tint(rng))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build_specs(kit, specs):
    objs = []
    for sp in specs:
        t0 = time.time()
        res = sp.fn()
        obj = res if isinstance(res, bpy.types.Object) else res.build()
        eh.triangulate_ngons(obj)
        nm = kit.name(sp.role)
        obj.name = nm
        obj.data.name = nm
        if sp.role.startswith("Prop_"):
            zmax = max(v.co.z for v in obj.data.vertices)
            if zmax > 1.2:
                k = 1.18 / zmax
                for v in obj.data.vertices:
                    v.co *= k
                print(f"[biome] {nm}: scaled by {k:.3f} to respect the 1.2 m prop height")
        tris = eh.tri_count(obj)
        flag = "" if tris <= sp.budget else f"  !!! over budget {sp.budget}"
        print(f"[biome] built {nm:28s} tris={tris:6d} ({time.time() - t0:.1f}s){flag}")
        objs.append(obj)
    return objs


def check_tiles(kit, objs):
    report = {}
    for o, sp in objs:
        if not sp.tile:
            continue
        vs = [v.co for v in o.data.vertices]
        walk = [v for v in vs if 0.0 <= v.x <= 1.0 and TF <= v.y <= TB]
        report[o.name] = dict(max_z=round(max(v.z for v in walk), 4), min_y=round(min(v.y for v in vs), 4),
                              min_x=round(min(v.x for v in vs), 4), max_x=round(max(v.x for v in vs), 4),
                              min_z=round(min(v.z for v in vs), 4))
        print(f"[biome] tile check {o.name}: {report[o.name]}")
    return report


def contract_checks(kit, pairs):
    """Sizes / pivots from Tools/BIOMES.md, measured in Blender units (x, y=depth, z=up)."""
    out = {}
    for o, sp in pairs:
        lo, hi = bounds(o)
        w, d, h = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
        r = sp.role
        checks = {}
        if sp.tile:
            checks["top_z<=1.06"] = hi.z <= 1.06 + 1e-4
            checks["front_overhang<=0.08"] = lo.y >= TF - 0.08 - 1e-4
        if r == "Platform":
            checks["deck_top=1"] = abs(hi.z - 1.0) < 0.03
            deck = [v.co for v in o.data.vertices if v.co.z > 0.79]
            checks["deck_thickness<=0.2"] = min(v.z for v in deck) >= 0.79
        if r in ("BackWall", "SkullWall"):
            checks["4x4"] = abs(lo.x) < 0.02 and abs(hi.x - 4) < 0.02 and abs(lo.z) < 0.02 and abs(hi.z - 4) < 0.02
            checks["depth<=0.4"] = hi.y <= 0.41
            checks["front_y~0"] = lo.y >= -0.07
            checks["tris<=3600"] = eh.tri_count(o) <= 3600
        if r == "Pillar":
            checks["width<=1"] = w <= 1.0 + 1e-3
            checks["height~5"] = 4.8 <= h <= 5.2
        if r == "Arch":
            checks["width~6"] = 5.5 <= w <= 7.0
            checks["height~5.5"] = 5.0 <= h <= 6.0
        if r == "Door":
            checks["width~2.4"] = 2.2 <= w <= 2.7
            checks["height~3.2"] = 3.0 <= h <= 3.4
            checks["recess<=0.8"] = hi.y <= 0.8 + 1e-3
        if r == "Hang":
            checks["top_at_pivot"] = abs(hi.z) < 0.05
            checks["length_2_3m"] = 2.0 <= -lo.z <= 3.05
        if r.startswith("Prop_"):
            checks["height<=1.2"] = hi.z <= 1.2 + 1e-3
        if r == "BG_Near":
            checks["~20x10"] = 17 <= w <= 23 and 8 <= h <= 12
        if r.startswith("BG_Far"):
            checks["height_16_25"] = 16 <= h <= 25.5
        if r in ("Light", "Furnace"):
            checks["LightSocket"] = any(c.name.startswith("LightSocket") for c in o.children)
        out[o.name] = dict(size_blender=[round(w, 3), round(d, 3), round(h, 3)], **checks)
        bad = [k for k, v in checks.items() if v is False]
        print(f"[biome] contract {o.name:28s} size(w,d,h)={out[o.name]['size_blender']} "
              f"{'OK' if not bad else 'FAIL ' + str(bad)}")
    return out


def spread(objs, y=0.0, gap=3.0):
    x = 0.0
    for o in objs:
        xs = [v.co.x for v in o.data.vertices]
        lo, hi = min(xs), max(xs)
        o.location = (x - lo, y, 0.0)
        x += (hi - lo) + gap


def bake(objs, others, tex_dir, prefix, size, ao_dist):
    for o in others:
        o.hide_render = True
    for o in objs:
        o.hide_render = False
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("BakeWorld")
    scene.world = world
    world.light_settings.distance = ao_dist
    t0 = time.time()
    # Bake on the CPU by default: on a busy machine (live Blender + Unity) Metal
    # can run out of memory mid-bake and silently drop chunks (black texels).
    import functools
    orig = dc.setup_cycles
    if not BAKE_GPU:
        dc.setup_cycles = functools.partial(orig, use_gpu=False)
        bpy.context.scene.render.engine = "CYCLES"
        bpy.context.scene.cycles.device = "CPU"
    try:
        paths = dc.bake_texture_set(objs, tex_dir, prefix, size=size, highpoly=None)
    finally:
        dc.setup_cycles = orig
    print(f"[biome] baked {prefix} {size}px in {time.time() - t0:.1f}s")
    for o in others:
        o.hide_render = False
    return paths


def assign(objs, mat):
    for o in objs:
        me = o.data
        me.materials.clear()
        me.materials.append(mat)
        for p in me.polygons:
            p.material_index = 0
        for a in ("dc_tint", "dc_uvw", "dc_hasuv"):
            if a in me.attributes:
                me.attributes.remove(me.attributes[a])


def bounds(obj):
    vs = [v.co for v in obj.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return lo, hi


def to_unity(v):
    return [round(v[0], 4), round(v[2], 4), round(v[1], 4)]


def render_sheet(objs, out_png, cell=384, cols=6, engine="BLENDER_EEVEE"):
    paths = []
    for o in bpy.context.scene.objects:
        o.hide_render = True
    tmp = out_png.parent / "_mod"
    tmp.mkdir(parents=True, exist_ok=True)
    for o in objs:
        o.hide_render = False
        paths.extend(dc.preview_render(str(tmp / o.name), [o], views=("three_quarter",), res=cell, engine=engine))
        o.hide_render = True
    for o in bpy.context.scene.objects:
        o.hide_render = False
    eh.compose_sheet(paths, out_png, cols=min(cols, len(paths)), cell=cell)
    print(f"[biome] sheet {out_png} order: {[o.name for o in objs]}")


def chunk_scene(kit, by):
    made = []
    nm = kit.name

    def put(role, loc, rz=0.0, s=1.0, rx=0.0):
        src = by[nm(role)] if nm(role) in by else by[role]
        o = src.copy()
        o.name = src.name + "_chunk"
        dc.link(o)
        o.hide_render = False
        o.location = loc
        o.rotation_euler = (rx, 0, rz)
        o.scale = (s, s, s)
        made.append(o)
        return o

    fills = ["Fill_A", "Fill_B", "Fill_C"]
    tops = ["Top_A", "Top_B"]
    for i in range(12):
        put(fills[(i * 2 + i // 3) % 3], (i, 0, 0))
        put("Edge_L" if i == 0 else "Edge_R" if i == 11 else tops[(i * 7 // 3) % 2], (i, 0, 1))
    for i in range(3):
        put("Platform", (7 + i, 0, 3.5))
    for x in range(-2, 14, 2):
        for z in (0, 2, 4, 6):
            put("BackWall", (x, 2.0, z), s=0.5)
    put("Door", (3.6, 1.15, 2.0))   # recess (<=0.8 m) stays in front of the wall plane
    put("Arch", (8.5, 1.0, 2.0))
    put("Pillar", (0.9, 0.55, 2.0))
    put("Light", (2.05, 2.0, 3.6))
    put("Light", (5.15, 2.0, 3.6))
    put("Hang", (9.7, 1.2, 8.0))
    put("Prop_A", (5.7, 0.25, 2.0))
    put("Prop_B", (6.7, 0.3, 2.0))
    put("Prop_C", (10.6, 0.15, 2.0))
    if kit.chunk_extras:
        kit.chunk_extras(put)
    return made


def render_previews(kit, kit_objs, bg_objs, engine="BLENDER_EEVEE"):
    out = kit.out
    by = {o.name: o for o in kit_objs + bg_objs}
    render_sheet(kit_objs, out / f"{kit.id}_sheet_Kit_three_quarter.png", engine=engine)
    render_sheet(bg_objs, out / f"{kit.id}_sheet_BG_three_quarter.png", cols=len(bg_objs), engine=engine)
    for o in bpy.context.scene.objects:
        o.hide_render = True
    made = chunk_scene(kit, by)
    center, width = Vector((5.75, 0.0, 4.1)), 15.5
    lt = kit.light
    if engine == "BLENDER_EEVEE":
        dc.preview_render(str(out / f"{kit.id}_chunk"), made, views=("front",), res=1024, bg=kit.chunk_bg)
    eh.render_framed(out / f"{kit.id}_chunk_front.png", center, width, (0, -1, 0.05), res=(1600, 900),
                     engine=engine, bg=kit.chunk_bg, key_energy=lt["key"], rim_energy=lt["rim"])
    eh.render_framed(out / f"{kit.id}_chunk_game_hi.png", center, width, (0.25, -1, 0.12), res=(1280, 720),
                     engine=engine, bg=kit.chunk_bg, key_energy=lt["key"], rim_energy=lt["rim"])
    eh.pixelate(out / f"{kit.id}_chunk_game_hi.png", out / f"{kit.id}_chunk_game_pixel.png", 2)
    for o in made:
        bpy.data.objects.remove(o, do_unlink=True)
    xs, x = [], 0.0
    copies = []
    for o in bg_objs:
        lo, hi = bounds(o)
        c = o.copy()
        dc.link(c)
        c.hide_render = False
        c.location = (x - lo.x, 0, 0)
        x += hi.x - lo.x + 3.0
        copies.append(c)
    top = max(bounds(o)[1].z for o in bg_objs)
    w = max(x, top * 16 / 9)
    eh.render_framed(out / f"{kit.id}_bg_lineup.png", Vector((x / 2, 0, top / 2)), w * 1.04, (0, -1, 0.05),
                     res=(1600, 900), engine=engine, bg=kit.chunk_bg, key_energy=lt["key"], rim_energy=lt["rim"])
    for c in copies:
        bpy.data.objects.remove(c, do_unlink=True)
    for o in bpy.context.scene.objects:
        o.hide_render = False


def export(kit, pairs, atlas_names, manifest):
    for o, sp in pairs:
        o.location = (0.0, 0.0, 0.0)
        kids = list(o.children)
        path = kit.mesh_dir / f"{o.name}.fbx"
        dc.export_fbx(path, [o] + kids, static=True)
        lo, hi = bounds(o)
        manifest["modules"].append(dict(
            name=o.name, role=sp.role, fbx=str(path.relative_to(dc.PROJECT_ROOT)), atlas=atlas_names[sp.atlas],
            unity_bounds_min=to_unity(lo), unity_bounds_max=to_unity(hi),
            sockets={c.name.split(".")[0]: to_unity(c.location) for c in kids}, tris=eh.tri_count(o),
            usage=sp.usage))


def run(kit, fast=False, build_only=False):
    t_start = time.time()
    dc.ensure_dir(kit.out)
    dc.reset_scene()
    kit.make_materials(kit)
    for m in kit.M.values():
        if m is not None and m.get("dc_base_hex"):
            m.diffuse_color = dc.hex_rgba(m["dc_base_hex"])
    roles = {s.role for s in kit.specs}
    missing = [r for r in REQUIRED_ROLES if r not in roles]
    if missing:
        raise RuntimeError(f"{kit.id}: missing required roles {missing}")
    kit_specs = [s for s in kit.specs if s.atlas == "Kit"]
    bg_specs = [s for s in kit.specs if s.atlas == "BG"]
    kit_objs = build_specs(kit, kit_specs)
    bg_objs = build_specs(kit, bg_specs)
    pairs = list(zip(kit_objs, kit_specs)) + list(zip(bg_objs, bg_specs))
    tile_report = check_tiles(kit, pairs)
    contract = contract_checks(kit, pairs)
    if build_only:
        scene = bpy.context.scene
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_cavity = True
        render_previews(kit, kit_objs, bg_objs, engine="BLENDER_WORKBENCH")
        return
    size_kit, size_bg = (1024, 512) if fast else (2048, 1024)
    t0 = time.time()
    dens = eh.atlas_uv(kit_objs, {o.name: s.weight for o, s in zip(kit_objs, kit_specs)}, margin=0.002)
    eh.atlas_uv(bg_objs, {o.name: s.weight for o, s in zip(bg_objs, bg_specs)}, margin=0.0025)
    print(f"[biome] UV atlases packed in {time.time() - t0:.1f}s")
    for k, v in dens.items():
        print(f"[biome]   front texel density {k:28s} {v * size_kit:7.1f} px/m")
    spread(kit_objs, y=0.0, gap=3.0)
    spread(bg_objs, y=120.0, gap=12.0)
    p_kit = bake(kit_objs, bg_objs, kit.tex_dir, f"{kit.id}_Kit", size_kit, 0.35)
    p_bg = bake(bg_objs, kit_objs, kit.tex_dir, f"{kit.id}_BG", size_bg, 2.0)
    m_kit = dc.baked_material(f"M_{kit.id}_Kit", p_kit, emission_strength=5.0)
    m_bg = dc.baked_material(f"M_{kit.id}_BG", p_bg, emission_strength=3.0)
    assign(kit_objs, m_kit)
    assign(bg_objs, m_bg)
    rel = lambda p: str(Path(p).relative_to(dc.PROJECT_ROOT))  # noqa: E731
    manifest = {"biome": kit.id, "generator": f"Tools/Blender/build_biome.py --biome {kit.id}",
                "unity_axes": "Unity (x,y,z) = Blender (x,z,y)",
                "atlases": {f"{kit.id}_Kit": {k: rel(v) for k, v in p_kit.items()},
                            f"{kit.id}_BG": {k: rel(v) for k, v in p_bg.items()}},
                "materials": {f"{kit.id}_Kit": f"M_{kit.id}_Kit", f"{kit.id}_BG": f"M_{kit.id}_BG"},
                "emission_colors": kit.emission, "tile_checks_blender": tile_report,
                "contract_checks_blender": contract, "modules": []}
    render_previews(kit, kit_objs, bg_objs)
    order = [p_kit[k] for k in ("albedo", "normal", "orm", "emission")] + \
            [p_bg[k] for k in ("albedo", "normal", "orm", "emission")]
    eh.compose_sheet([str(p) for p in order], kit.out / f"{kit.id}_atlas_sheet.png", cols=4, cell=768)
    export(kit, pairs, {"Kit": f"{kit.id}_Kit", "BG": f"{kit.id}_BG"}, manifest)
    kit.manifest.parent.mkdir(parents=True, exist_ok=True)
    kit.manifest.write_text(json.dumps(manifest, indent=2))
    print(f"[biome] manifest {kit.manifest}")
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(kit.out / f"{kit.id}_kit.blend"), compress=True)
    except RuntimeError as exc:
        print("[biome] blend save failed", exc)
    print(f"[biome] {kit.id} DONE in {time.time() - t_start:.1f}s")


def verify(kit):
    dc.reset_scene()
    man = json.loads(kit.manifest.read_text())
    bad = 0
    lines = []
    for m in man["modules"]:
        path = dc.PROJECT_ROOT / m["fbx"]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(path), axis_forward="Z", axis_up="Y")
        new = [o for o in bpy.data.objects if o not in before]
        mesh = next(o for o in new if o.type == "MESH")
        bpy.context.view_layer.update()
        ws = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
        lo = [min(w[i] for w in ws) for i in range(3)]
        hi = [max(w[i] for w in ws) for i in range(3)]
        ulo, uhi = to_unity(lo), to_unity(hi)
        err = max(abs(a - b) for a, b in zip(ulo + uhi, m["unity_bounds_min"] + m["unity_bounds_max"]))
        loc = tuple(round(c, 4) for c in mesh.matrix_world.translation)
        mats = [s.material.name for s in mesh.material_slots if s.material]
        sock = {o.name.split(".")[0]: to_unity(o.matrix_world.translation) for o in new if o.type == "EMPTY"}
        sock_ok = all(k in sock and max(abs(a - b) for a, b in zip(sock[k], v)) < 2e-3 for k, v in m["sockets"].items())
        ok = err < 2e-3 and max(abs(c) for c in loc) < 1e-4 and len(mats) == 1 and sock_ok
        bad += not ok
        line = (f"[verify] {m['name']:28s} ok={ok} origin={loc} bounds_err={err:.5f} mats={len(mats)} "
                f"unity_min={ulo} unity_max={uhi} sockets={sock}")
        print(line)
        lines.append(line)
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    summary = f"[verify] {kit.id}: {len(man['modules']) - bad}/{len(man['modules'])} modules OK"
    print(summary)
    dc.ensure_dir(kit.out)
    (kit.out / f"{kit.id}_verify.txt").write_text("\n".join(lines + [summary]) + "\n")
    return bad == 0
