"""Prisoners' Quarters environment kit (Dead Cells-style vertical slice).

Procedurally models every environment module, packs the foreground/midground
modules into one shared 2048 atlas (ENV_Kit) and the background silhouettes
into one 1024 atlas (BG_Kit), bakes albedo / normal / ORM / emission with
Cycles, swaps in one baked material per kit, exports one FBX per module,
writes env_manifest.json and renders verification previews.

Run (headless only):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      -P Tools/Blender/build_environment.py
Options after "--":
  --fast     1024/512 atlases (iteration only; do not ship)
  --verify   re-import the exported FBX files in a fresh scene and check pivots/bounds
"""

import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import dc_common as dc  # noqa: E402
import env_helpers as eh  # noqa: E402
from env_helpers import (Builder, block, bm_box, bm_blob, bm_cut, bm_ico, bm_lathe, bm_prism_xz,  # noqa: E402
                         bm_tube, delete_faces, rotate, scale, translate, transform)

ENV_ART = dc.ART_ROOT / "Environment"
MESH_DIR = ENV_ART / "Meshes"
TEX_DIR = ENV_ART / "Textures"
OUT = dc.OUT_ROOT / "env"
MANIFEST = ENV_ART / "env_manifest.json"

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FAST = "--fast" in ARGS
ENV_SIZE = 1024 if FAST else 2048
BG_SIZE = 512 if FAST else 1024

M = {}
G = 0.045            # mortar gap between foreground bricks
TF, TB = -0.9, 1.6   # tile front / back planes
X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))
TAU = math.tau


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


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def make_materials():
    stone = dict(dark=hex_mix("#2E4A5C", "#142430", 0.45), light=hex_mix("#2E4A5C", "#4F7D8C", 0.45), rough=0.82,
                 rough_var=0.1, noise_scale=3.2, noise_amt=0.4,
                 bevel_radius=0.03, bump_strength=0.35, bump_scale=14.0)
    stone_fx = dict(tint_amt=0.28, grime_hex="#2F5E2A", grime_amt=0.85, blotch=("#142430", 6.0, 0.06),
                    top_hex="#4F7D8C", top_amt=0.4, bottom_amt=0.25, edge_hex="#7FA6B0", edge_amt=1.0,
                    edge_radius=0.06, edge_top_bias=0.55, cavity_amt=0.8, cavity_dist=0.16, cavity_hex="#0B141C")
    M["Stone"] = eh.enhance(dc.make_material("M_Stone", "#2E4A5C", **stone), **stone_fx)

    back = dc.make_material("M_StoneBack", "#20374A", dark="#172A38", light="#2B495B", rough=0.85, noise_scale=2.4,
                            noise_amt=0.4, bevel_radius=0.04, bump_strength=0.35, bump_scale=8.0)
    eh.enhance(back, tint_amt=0.24, blotch=("#132532", 4.0, 0.06), top_hex="#335468", top_amt=0.3, bottom_amt=0.25,
               edge_hex="#557B88", edge_amt=0.75, edge_radius=0.05, cavity_amt=0.8, cavity_dist=0.2,
               cavity_hex="#0B141C")
    eh.make_periodic(back, 4.0, 4.0)
    M["StoneBack"] = back

    M["Mortar"] = eh.enhance(dc.make_material("M_Mortar", "#0B141C", dark="#05090D", light="#17242E", rough=0.95,
                                              noise_scale=6.0, noise_amt=0.6, bump_strength=0.3),
                             cavity_amt=0.4, cavity_dist=0.1)
    mortar_back = dc.make_material("M_MortarBack", "#0B141C", dark="#05090D", light="#17242E", rough=0.95,
                                   noise_scale=3.0, noise_amt=0.6, bump_strength=0.3)
    eh.make_periodic(mortar_back, 4.0, 4.0)
    M["MortarBack"] = mortar_back

    M["Moss"] = eh.enhance(dc.make_material("M_Moss", "#4E8F3A", dark="#2F5E2A", light="#8FCB4C", rough=0.9,
                                            noise_scale=11.0, noise_amt=0.9, bevel_radius=0.02, bump_strength=0.6,
                                            bump_scale=35.0),
                           blotch=("#8FCB4C", 18.0, 0.2), top_hex="#6FAE44", top_amt=0.3, bottom_amt=0.55,
                           cavity_amt=0.7, cavity_dist=0.08, cavity_hex="#173018", tint_amt=0.15)

    M["Iron"] = eh.enhance(dc.make_material("M_Iron", "#3A3F47", dark="#1E2228", light="#6B737D", rough=0.5,
                                            rough_var=0.15, metal=0.7, noise_scale=7.0, noise_amt=0.55,
                                            bevel_radius=0.008, bump_strength=0.3, bump_scale=40.0),
                           blotch=("#7A4A2A", 5.0, 0.26), top_hex="#6B737D", top_amt=0.3, bottom_amt=0.3,
                           edge_hex="#6B737D", edge_amt=1.0, edge_radius=0.012, edge_top_bias=0.3,
                           cavity_amt=0.65, cavity_dist=0.05, cavity_hex="#0E1013", tint_amt=0.12)

    wood = dict(dark="#3A2414", light="#7A5634", rough=0.85, noise_scale=3.0, noise_amt=0.75, bevel_radius=0.012,
                bump_strength=0.45, bump_scale=10.0)
    wood_fx = dict(tint_amt=0.18, top_hex="#7A5634", top_amt=0.35, bottom_amt=0.35, edge_hex="#8E6A44",
                   edge_amt=0.7, edge_radius=0.02, cavity_amt=0.7, cavity_dist=0.07, cavity_hex="#160C06",
                   blotch=("#2E1C0F", 4.0, 0.25))
    for axis, sc in (("X", (0.1, 2.6, 2.6)), ("Y", (2.6, 0.1, 2.6)), ("Z", (2.6, 2.6, 0.1))):
        m = dc.make_material("M_Wood" + axis, "#5A3A22", **wood)
        eh.stretch_coords(m, sc)
        M["Wood" + axis] = eh.enhance(m, **wood_fx)

    def banner_extra(nt, col, coord, geo):
        tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
        sep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-1900, 1500))
        nt.links.new(dc._sock(tc.outputs, "Object"), dc._sock(sep.inputs, "Vector"))
        x, z = dc._sock(sep.outputs, "X"), dc._sock(sep.outputs, "Z")
        ax = dc.math_node(nt, "ABSOLUTE", x, 0.0, loc=(-1800, 1500), clamp=False)
        # ring
        dz = dc.math_node(nt, "ADD", z, 0.95, loc=(-1800, 1450), clamp=False)
        vec = dc.new_node(nt, "ShaderNodeCombineXYZ", (-1700, 1450))
        nt.links.new(x, dc._sock(vec.inputs, "X"))
        nt.links.new(dz, dc._sock(vec.inputs, "Y"))
        ln = dc.new_node(nt, "ShaderNodeVectorMath", (-1600, 1450))
        ln.operation = "LENGTH"
        nt.links.new(dc._sock(vec.outputs, "Vector"), ln.inputs[0])
        ring = dc.math_node(nt, "SUBTRACT", ln.outputs["Value"], 0.25, loc=(-1500, 1450), clamp=False)
        ring = dc.math_node(nt, "ABSOLUTE", ring, 0.0, loc=(-1400, 1450), clamp=False)
        ring = dc.math_node(nt, "LESS_THAN", ring, 0.04, loc=(-1300, 1450), clamp=False)
        # blade + cross guard
        blade = dc.math_node(nt, "MULTIPLY", dc.math_node(nt, "LESS_THAN", ax, 0.04, loc=(-1700, 1350), clamp=False),
                             dc.math_node(nt, "MULTIPLY",
                                          dc.math_node(nt, "LESS_THAN", z, -0.5, loc=(-1700, 1300), clamp=False),
                                          dc.math_node(nt, "GREATER_THAN", z, -1.62, loc=(-1700, 1250), clamp=False),
                                          loc=(-1600, 1300)), loc=(-1500, 1350))
        guard = dc.math_node(nt, "MULTIPLY", dc.math_node(nt, "LESS_THAN", ax, 0.19, loc=(-1700, 1200), clamp=False),
                             dc.math_node(nt, "LESS_THAN",
                                          dc.math_node(nt, "ABSOLUTE", dc.math_node(nt, "ADD", z, 0.78, loc=(-1800, 1150), clamp=False), 0.0, loc=(-1750, 1150), clamp=False),
                                          0.035, loc=(-1700, 1150), clamp=False), loc=(-1500, 1200))
        # trim bands near the rod and above the tear
        band = dc.math_node(nt, "LESS_THAN",
                            dc.math_node(nt, "ABSOLUTE", dc.math_node(nt, "ADD", z, 0.2, loc=(-1800, 1050), clamp=False), 0.0, loc=(-1750, 1050), clamp=False),
                            0.03, loc=(-1700, 1050), clamp=False)
        mask = dc.math_node(nt, "MAXIMUM", ring, blade, loc=(-1200, 1350))
        mask = dc.math_node(nt, "MAXIMUM", mask, guard, loc=(-1100, 1350))
        mask = dc.math_node(nt, "MAXIMUM", mask, band, loc=(-1000, 1350))
        mask = dc.math_node(nt, "MULTIPLY", mask, 0.8, loc=(-900, 1350))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba("#B9AE8C"), mask, loc=(-150, 600))
        low = dc.map_range(nt, z, -1.6, -2.5, 0.0, 0.65, loc=(-900, 1200))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba("#3D000B"), low, loc=(-100, 600))
        return col

    cloth = dc.make_material("M_Cloth", "#780016", dark="#3D000B", light="#8E1630", rough=0.92, noise_scale=5.0,
                             noise_amt=0.6, bevel_radius=0.01, bump_strength=0.25, bump_scale=60.0)
    M["Cloth"] = eh.enhance(cloth, cavity_amt=0.7, cavity_dist=0.12, cavity_hex="#22000A", top_hex="#8E1630",
                            top_amt=0.2, bottom_amt=0.3, extra=banner_extra)

    M["Bone"] = eh.enhance(dc.make_material("M_Bone", "#CFC6A8", dark="#8E856A", light="#E8E1C8", rough=0.7,
                                            noise_scale=9.0, noise_amt=0.5, bevel_radius=0.008, bump_strength=0.3,
                                            bump_scale=40.0),
                           cavity_amt=0.9, cavity_dist=0.05, cavity_hex="#3A3326", edge_hex="#F2ECD8",
                           edge_amt=0.45, edge_radius=0.01, bottom_amt=0.35, tint_amt=0.15,
                           blotch=("#7C7258", 6.0, 0.22))
    M["Coal"] = eh.enhance(dc.make_material("M_Coal", "#2A1A12", dark="#120A06", light="#4A2A18", rough=0.9,
                                            noise_scale=16.0, noise_amt=0.8, emission="#FF7A1A", emission_strength=4.0,
                                            emission_mask="noise"),
                           cavity_amt=0.6, cavity_dist=0.03)
    M["Dirt"] = eh.enhance(dc.make_material("M_Dirt", "#26302F", dark="#121819", light="#3A4642", rough=0.95,
                                            noise_scale=7.0, noise_amt=0.7, bump_strength=0.5, bump_scale=25.0),
                           blotch=("#2F5E2A", 3.0, 0.25), cavity_amt=0.7, cavity_dist=0.08, top_hex="#3A4642",
                           top_amt=0.3)
    M["Dark"] = eh.enhance(dc.make_material("M_Dark", "#0F1A22", dark="#070C10", light="#1A2A36", rough=0.95,
                                            noise_scale=2.5, noise_amt=0.6),
                           brick=(0.55, 0.28, "#04070A"), cavity_amt=0.6, cavity_dist=0.25, tint_amt=0.15)

    # Background kit
    M["BGStone"] = eh.enhance(dc.make_material("M_BGStone", "#1D3442", dark="#0E1A24", light="#2C4C5A", rough=0.9,
                                               noise_scale=0.7, noise_amt=0.6, bevel_radius=0.06, bump_strength=0.3,
                                               bump_scale=4.0),
                              brick=(1.1, 0.48, "#0B141C"), top_hex="#2C4C5A", top_amt=0.45, bottom_amt=0.3,
                              edge_hex="#3D6676", edge_amt=0.8, edge_radius=0.18, cavity_amt=0.6, cavity_dist=1.2,
                              cavity_hex="#070D12", tint_amt=0.2)
    M["BGRoof"] = eh.enhance(dc.make_material("M_BGRoof", "#182C38", dark="#0E1A24", light="#2C4C5A", rough=0.85,
                                              noise_scale=1.2, noise_amt=0.6, stripes=("z", 2.2, 0.14, "#0B151D"),
                                              bump_strength=0.3, bump_scale=4.0),
                             top_hex="#2C4C5A", top_amt=0.3, edge_hex="#3D6676", edge_amt=0.6, edge_radius=0.15,
                             cavity_amt=0.5, cavity_dist=1.0)
    M["BGWindow"] = dc.make_material("M_BGWindow", "#173A40", dark="#0E1A24", light="#1F4A50", rough=0.8,
                                     noise_scale=2.0, emission="#3FE0D0", emission_strength=2.0)
    M["_"] = None
    M["BGIron"] = eh.enhance(dc.make_material("M_BGIron", "#161C22", dark="#0A0E12", light="#2A323A", rough=0.6,
                                              metal=0.5, noise_scale=4.0),
                             edge_hex="#2C3440", edge_amt=0.6, edge_radius=0.03)
    M.pop("_")
    for m in M.values():
        if m.get("dc_base_hex"):
            m.diffuse_color = dc.hex_rgba(m["dc_base_hex"])


# ---------------------------------------------------------------------------
# Foreground tiles
# ---------------------------------------------------------------------------

def tile_uvw(c, n):
    if n.z < -0.9 or n.y > 0.5:
        return 0.3
    return 1.0 if c.y < -0.45 else 0.28


def tile_bricks(B, rng, rows, *, edge=None, crack=None, top_grime=0.0):
    core = bm_box((0.07, -0.86, 0.07), (0.93, TB, 0.955))
    delete_faces(core, lambda c, n: n.y > 0.9)
    B.add(core, M["Mortar"], uvw=0.3)
    for ri, (z0, z1, splits) in enumerate(rows):
        top = z1 >= 0.999
        xs = [0.0] + list(splits) + [1.0]
        for bi in range(len(xs) - 1):
            x0, x1 = xs[bi] + G / 2, xs[bi + 1] - G / 2
            zz0 = z0 + G / 2
            zz1 = 1.0 if top else z1 - G / 2
            yf = TF + rng.uniform(-0.03, 0.03)
            cuts = []
            corners = [(-1, -1, -1), (1, -1, -1), (-1, -1, 1), (1, -1, 1)]
            nchips = rng.randint(1, 3)
            size = (0.035, 0.12)
            if edge == "L" and bi == 0:
                if top:
                    c = Vector((0.02 + 0.22, 0.0, 1.0 - 0.22))
                    for phi in (20, 45, 70):
                        n = Vector((-math.sin(rad(phi)), 0.0, math.cos(rad(phi))))
                        cuts.append((c + n * 0.22, n))
                    corners = [(-1, -1, -1), (1, -1, 1)]
                else:
                    corners = [(-1, -1, -1), (-1, -1, 1), (1, -1, 1)]
                    size = (0.05, 0.16)
                nchips = 2
            ck = None
            if crack == (ri, bi):
                ck = (((x0 + x1) / 2 + rng.uniform(-0.06, 0.06), 0.0, (zz0 + zz1) / 2),
                      (1.0, 0.0, rng.uniform(-0.6, 0.6)))
            pieces = block((x0, yf, zz0), (x1, TB, zz1), rng, chips=nchips, chip_size=size, corners=corners,
                           bevel=0.026, segs=2, jitter=0.012, fixed_top=1.0 if top else None, splits_y=(-0.45,),
                           cuts=cuts, crack=ck, crack_gap=0.032, back_delete=1.0, bevel_back=1.0)
            t = (rng.uniform(0.2, 0.8), top_grime if top else rng.uniform(0.0, 0.2), rng.uniform(0.0, 0.25), 1.0)
            B.add(pieces, M["Stone"], tint=t, uvw_fn=tile_uvw)


def tile_moss(B, rng, seed, edge=None):
    r2 = 0.04
    if edge == "L":
        R = 0.22
        cx, cz = 0.02 + R, 1.0 - R
        prof = [(cx + (R - r2) * math.cos(a), cz + (R - r2) * math.sin(a)) for a in lin(rad(90), rad(180), 7)]
        prof += [(0.02 + r2, -0.5), (2.0, -0.5), (2.0, 1.0 - r2)]
    else:
        prof = [(-1.0, 1.0 - r2), (-1.0, -0.5), (2.0, -0.5), (2.0, 1.0 - r2)]
    env = eh.bm_rounded_prism(prof, -0.935 + r2, 2.6, r2)
    bvh = eh.envelope_bvh(env)
    env.free()

    amp = [rng.uniform(-0.04, 0.075) / math.sqrt(k) for k in range(1, 7)]

    def D(x):
        x = min(max(x, 0.0), 1.0)
        v = 0.09 + sum(amp[k - 1] * math.sin(math.pi * k * x) for k in range(1, 7))
        return min(max(v, 0.05), 0.24)

    def Ds(y):
        return D(0.0) + 0.11 * math.sin(min(1.0, (y + 1.3) / 1.0) * math.pi / 2) * (0.65 + 0.35 * math.sin(3.7 * y + seed))

    def lump(p):
        x = p.x
        if edge == "L" and x < 0.5:
            w = 1.0
        else:
            w = max(0.0, math.sin(math.pi * min(max(x, 0.0), 1.0))) ** 0.7
        return 0.016 * w * max(0.0, eh.periodic_noise(x, p.y, p.z, freq=7.0, seed=seed * 1.7) + 0.25)

    top_ys = [1.6, 0.6, -0.2, -0.6, -0.8]
    front_ts = [0.0, 0.42, 0.78, 1.0]
    if edge == "L":
        xs = [-0.3, 0.02, 0.08, 0.15, 0.24, 0.34] + [0.34 + 0.66 * i / 7 for i in range(1, 8)]
        sheet = eh.moss_net(bvh, xs, top_ys, front_ts, D, side_ys=list(reversed(top_ys)), side_drape=Ds,
                            side_x_out=-0.3, offset=0.022, lump=lump, zmax=1.055)
    else:
        xs = [i / 14 for i in range(15)]
        sheet = eh.moss_net(bvh, xs, top_ys, front_ts, D, offset=0.022, lump=lump, zmax=1.055)
    B.add(sheet, M["Moss"], smooth=True, uvw_fn=lambda c, n: 1.0 if c.y < -0.4 else 0.3)

    n_str = 5 if edge else 7
    for k in range(n_str):
        x = 0.1 + 0.8 * (k + rng.uniform(0.15, 0.85)) / n_str
        top = (x, -0.958, 1.0 - D(x) + 0.035)
        B.add(eh.moss_strand(top, rng.uniform(0.1, 0.35), rng, width=rng.uniform(0.03, 0.045)), M["Moss"],
              smooth=True)
    for k in range(2 if edge else 3):
        x = rng.uniform(0.12, 0.88)
        bm = bm_blob((x, -0.95, 1.0 - D(x) + 0.005), rng.uniform(0.035, 0.05), (1.4, 0.5, 1.0), segs=6, rings=4,
                     rng=rng, jitter=0.15)
        for v in bm.verts:
            v.co.y = max(v.co.y, -0.977)
        B.add(bm, M["Moss"], smooth=True)
    clumps = []
    for _ in range(rng.randint(2, 3)):
        clumps.append(((rng.uniform(0.15, 0.85), -0.9, 0.995), rng.uniform(0.058, 0.07), (1.7, 1.0, 0.85)))
    if edge == "L":
        clumps.append(((0.06, -0.88, 0.97), 0.085, (1.2, 1.0, 0.9)))
        for _ in range(2):
            y = rng.uniform(-0.8, -0.25)
            top = (-0.012, y, 1.0 - Ds(y) + 0.03)
            B.add(eh.moss_strand(top, rng.uniform(0.1, 0.3), rng, width=0.03, face_dir=Vector((-1, 0, 0))),
                  M["Moss"], smooth=True)
    for c, r, s in clumps:
        bm = bm_blob(c, r, s, segs=7, rings=5, rng=rng, jitter=0.12)
        for v in bm.verts:
            v.co.z = min(v.co.z, 1.055)
            v.co.y = max(v.co.y, -0.977)
        B.add(bm, M["Moss"], smooth=True)


TILE_LAYOUTS = {
    "ENV_Stone_A": dict(seed=11, rows=[(0.0, 0.46, [0.40]), (0.46, 1.0, [0.70])], crack=None),
    "ENV_Stone_B": dict(seed=12, rows=[(0.0, 0.58, [0.62]), (0.58, 1.0, [])], crack=(1, 0)),
    "ENV_Stone_C": dict(seed=13, rows=[(0.0, 0.36, [0.55]), (0.36, 1.0, [0.30])], crack=(1, 1)),
    "ENV_StoneTop_A": dict(seed=21, rows=[(0.0, 0.5, [0.35]), (0.5, 1.0, [0.6])], crack=(0, 1)),
    "ENV_StoneTop_B": dict(seed=22, rows=[(0.0, 0.42, [0.7]), (0.42, 1.0, [0.45])], crack=None),
    "ENV_StoneEdge_L": dict(seed=31, rows=[(0.0, 0.52, [0.55]), (0.52, 1.0, [0.5])], crack=None),
}


def build_tile(name):
    spec = TILE_LAYOUTS[name]
    rng = random.Random(spec["seed"])
    B = Builder(name)
    mossy = "Top" in name or "Edge" in name
    edge = "L" if "Edge" in name else None
    tile_bricks(B, rng, spec["rows"], edge=edge, crack=spec["crack"], top_grime=0.55 if mossy else 0.0)
    if mossy:
        tile_moss(B, rng, spec["seed"], edge=edge)
    # hard contract: decorative overhang <= 0.08 m in front of the y=-0.9 face
    for v in B.bm.verts:
        v.co.y = max(v.co.y, TF - 0.079)
    return B


def build_edge_r():
    B = build_tile("ENV_StoneEdge_L")
    B.name = "ENV_StoneEdge_R"
    B.mirror_x(0.5)
    return B


# ---------------------------------------------------------------------------
# Wooden one-way platform
# ---------------------------------------------------------------------------

def dome_rivet(pos, r=0.016, facing=Vector((0, -1, 0)), segs=6):
    bm = bm_lathe([(r, 0.0), (r * 0.8, r * 0.45), (r * 0.4, r * 0.75)], segs=segs, cap_bottom=True)
    m = eh.look_matrix(Vector(pos), Vector(pos) + facing)
    return transform(bm, m)


def beam(p0, p1, w, h, rng, bevel=0.015, chips=0, segs=1, roll=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    pcs = block((-w / 2, -h / 2, 0.0), (w / 2, h / 2, L), rng, chips=chips, bevel=bevel, segs=segs,
                corners=[(-1, -1, 1), (1, -1, 1), (-1, -1, -1), (1, -1, -1)])
    m = eh.look_matrix(p0, p1, roll)
    return [transform(p, m) for p in pcs]


def build_wood_platform():
    rng = random.Random(41)
    B = Builder("ENV_WoodPlatform")
    for i, (y0, y1) in enumerate([(-0.6, -0.1), (-0.07, 0.46), (0.49, 1.0)]):
        x0 = 0.004 + rng.uniform(0.0, 0.012)
        x1 = 0.996 - rng.uniform(0.0, 0.012)
        pcs = block((x0, y0, 0.82), (x1, y1, 1.0), rng, chips=2, chip_size=(0.02, 0.06),
                    corners=[(-1, -1, 1), (1, -1, 1), (-1, -1, -1), (1, -1, -1)], bevel=0.018, segs=2,
                    fixed_top=1.0)
        B.add(pcs, M["WoodX"], tint=tint(rng), uvw=1.0 if i == 0 else 0.45)
    B.add(block((0.43, -0.55, 0.70), (0.57, 1.0, 0.825), rng, chips=1, bevel=0.015, segs=1), M["WoodY"],
          tint=tint(rng))
    B.add(block((0.43, 0.86, 0.2), (0.57, 1.0, 0.825), rng, chips=1, bevel=0.015, segs=1,
                corners=[(-1, -1, -1), (1, -1, -1)]), M["WoodZ"], tint=(0.85, 0.0, 0.0, 1.0))
    B.add(beam((0.56, 0.93, 0.27), (0.44, -0.42, 0.78), 0.1, 0.1, rng, bevel=0.014), M["WoodZ"],
          tint=(0.9, 0.0, 0.0, 1.0))
    for cx in (0.17, 0.83):
        B.add(block((cx - 0.035, -0.616, 0.80), (cx + 0.035, -0.596, 0.99), rng, bevel=0.004, segs=1), M["Iron"])
        B.add(block((cx - 0.035, -0.616, 0.80), (cx + 0.035, -0.22, 0.822), rng, bevel=0.004, segs=1), M["Iron"])
        for z in (0.86, 0.945):
            B.add(dome_rivet((cx, -0.616, z)), M["Iron"], smooth=True)
    # iron collar where the strut meets the post
    B.add(block((0.44, 0.78, 0.24), (0.56, 0.87, 0.4), rng, bevel=0.004, segs=1), M["Iron"])
    for z in (0.28, 0.36):
        B.add(dome_rivet((0.5, 0.775, z), r=0.013), M["Iron"], smooth=True)
    return B


# ---------------------------------------------------------------------------
# Pillar
# ---------------------------------------------------------------------------

def moss_cap(B, rng, x0, x1, y_front, y_back, z_top, depth_rng=(0.06, 0.25), strands=3, seed=0, env_z0=None):
    """Moss blanket over the top + front edge of a rectangular ledge."""
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
        v = depth_rng[0] + (depth_rng[1] - depth_rng[0]) * (0.5 + sum(amp[k] * math.sin(math.pi * (k + 1) * u * 1.7 + k) for k in range(5)) * 2)
        return min(max(v, depth_rng[0]), depth_rng[1]) * (math.sin(math.pi * u) ** 0.35)

    xs = lin(x0 + 0.02, x1 - 0.02, max(6, int(w / 0.09)))
    ys = lin(y_back, y_front + 0.05, 4)
    sheet = eh.moss_net(bvh, xs, ys, [0.0, 0.5, 1.0], D, y_out=y_front - 0.4, z_out=z_top + 0.4, z_ref=z_top,
                        offset=0.025,
                        lump=lambda p: 0.03 * max(0.0, eh.periodic_noise(p.x * 0.7, p.y, p.z, 6.0, seed) + 0.3))
    B.add(sheet, M["Moss"], smooth=True)
    for _ in range(strands):
        x = rng.uniform(x0 + 0.1 * w, x1 - 0.1 * w)
        B.add(eh.moss_strand((x, y_front - 0.035, z_top - D(x) + 0.03), rng.uniform(0.15, 0.4), rng, width=0.035),
              M["Moss"], smooth=True)
    return D


def build_pillar():
    rng = random.Random(51)
    B = Builder("ENV_Pillar")
    S = M["Stone"]

    def grime(co, n):
        g = max(0.0, 1.0 - co.z / 1.8) * 0.85
        return (0.5, g, 0.1, 1.0)

    B.add(block((-0.65, 0.0, 0.0), (0.65, 1.2, 0.3), rng, chips=2, chip_size=(0.05, 0.14), bevel=0.04, segs=2,
                back_delete=1.0), S, tint_fn=grime)
    B.add(block((-0.56, 0.09, 0.3), (0.56, 1.11, 0.5), rng, chips=2, chip_size=(0.04, 0.1), bevel=0.05, segs=2,
                back_delete=1.0, cuts=[((0, 0.09 + 0.07, 0.5), (0, -1, 1)), ((-0.56 + 0.07, 0, 0.5), (-1, 0, 1)),
                                        ((0.56 - 0.07, 0, 0.5), (1, 0, 1))]), S, tint_fn=grime)
    z = 0.5
    for i, h in enumerate([0.78, 0.66, 0.84, 0.72, 0.85]):
        w = 0.45 + rng.uniform(-0.02, 0.02)
        dx = rng.uniform(-0.02, 0.02)
        lo = (-w + dx, 0.15 + rng.uniform(-0.02, 0.02), z + G / 2)
        hi = (w + dx, 1.05, z + h - G / 2)
        ck = None
        if i == 2:
            ck = ((rng.uniform(-0.1, 0.1), 0, z + h / 2), (1.0, 0.0, 0.55))
        pcs = block(lo, hi, rng, chips=rng.randint(2, 3), chip_size=(0.05, 0.17), bevel=0.03, segs=2, jitter=0.015,
                    crack=ck, crack_gap=0.035, back_delete=0.95)
        ang = rad(rng.uniform(-1.8, 1.8))
        for p in pcs:
            rotate(p, ang, "Z", (0, 0.6, z))
        t = rng.uniform(0.25, 0.75)
        B.add(pcs, S, tint_fn=lambda co, n, t=t: (t, max(0.0, 1.0 - co.z / 1.8) * 0.85, 0.08, 1.0),
              uvw_fn=lambda c, n: 0.5 if n.y > 0.5 else 1.0)
        z += h
    core = bm_box((-0.4, 0.2, 0.45), (0.4, 1.0, 4.4))
    delete_faces(core, lambda c, n: n.y > 0.9 or abs(n.z) > 0.9)
    B.add(core, M["Mortar"], uvw=0.3)
    # capital: flared echinus + abacus
    B.add(block((-0.54, 0.06, z), (0.54, 1.14, z + 0.27), rng, chips=1, bevel=0.03, segs=2, back_delete=1.0,
                cuts=[((0, 0.06 + 0.13, z), (0, -1, -1)), ((-0.54 + 0.13, 0, z), (-1, 0, -1)),
                      ((0.54 - 0.13, 0, z), (1, 0, -1))]), S, tint=tint(rng))
    zt = z + 0.27
    B.add(block((-0.62, 0.0, zt), (0.62, 1.2, 4.98), rng, chips=3, chip_size=(0.05, 0.15), bevel=0.035, segs=2,
                back_delete=1.0), S, tint=(0.6, 0.35, 0.05, 1.0))
    moss_cap(B, rng, -0.62, 0.62, 0.0, 1.2, 4.98, depth_rng=(0.06, 0.28), strands=3, seed=5.0, env_z0=zt)
    # moss at the base: blanket over the plinth step + clumps hugging the shaft
    moss_cap(B, rng, -0.56, 0.56, 0.09, 0.4, 0.5, depth_rng=(0.04, 0.16), strands=2, seed=9.0, env_z0=0.3)
    for k in range(6):
        x = -0.48 + 0.96 * (k + rng.uniform(0.2, 0.8)) / 6
        B.add(bm_blob((x, 0.13 + rng.uniform(-0.03, 0.02), 0.49 + rng.uniform(0.0, 0.03)), rng.uniform(0.1, 0.14),
                      (1.25, 0.9, 0.8), segs=8, rings=6, rng=rng, jitter=0.3), M["Moss"], smooth=True)
    for k in range(3):
        x = rng.uniform(-0.38, 0.38)
        B.add(eh.moss_strand((x, 0.12, 0.62), rng.uniform(0.2, 0.45), rng, width=0.04, sway=0.02), M["Moss"],
              smooth=True) if False else None
    for k in range(4):
        x = rng.choice([-0.62, 0.62]) * rng.uniform(0.5, 0.95)
        B.add(bm_blob((x, 0.0, 0.27), rng.uniform(0.09, 0.12), (1.3, 0.85, 0.75), segs=8, rings=6, rng=rng,
                      jitter=0.3), M["Moss"], smooth=True)
        B.add(eh.moss_strand((x, -0.035, 0.26), rng.uniform(0.1, 0.2), rng, width=0.04), M["Moss"], smooth=True)
    return B


# ---------------------------------------------------------------------------
# Arch
# ---------------------------------------------------------------------------

def voussoirs(B, rng, center, r_in, r_out, y0, y1, n, gap, *, key_extra=0.2, jitter_r=0.06, start=0.0,
              end=math.pi, bevel=0.025, segs=1, env=None, mat=None, tint_g=0.0, chips=1, skip=None):
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
        for _ in range(chips):
            eh.chip_vertex(bm, rng, rng.uniform(0.04, 0.1), pick=lambda co, yf=yf: co.y < yf + 1e-4)
        eh.bm_bevel(bm, bevel, segs)
        delete_faces(bm, lambda c, nn: nn.y > 0.9 and c.y > y1 - 0.05)
        if env is not None:
            eh.bm_append(env, bm)
        B.add(bm, mat or M["Stone"], tint=(rng.uniform(0.3, 0.7), tint_g, rng.uniform(0, 0.2), 1.0))


def pier(B, rng, x0, x1, courses, y0=0.0, y1=0.8, z=0.0, segs=1, bevel=0.03, grime_h=1.6, mat=None):
    for k, h in enumerate(courses):
        two = (k % 2 == 1)
        splits = [x0, x0 + (x1 - x0) * rng.uniform(0.4, 0.6), x1] if two else [x0, x1]
        for j in range(len(splits) - 1):
            lo = (splits[j] + G / 2, y0 + rng.uniform(-0.025, 0.02), z + G / 2)
            hi = (splits[j + 1] - G / 2, y1, z + h - G / 2)
            pcs = block(lo, hi, rng, chips=rng.randint(1, 2), chip_size=(0.04, 0.12), bevel=bevel, segs=segs,
                        jitter=0.015, back_delete=y1 - 0.05)
            t = rng.uniform(0.25, 0.75)
            B.add(pcs, mat or M["Stone"],
                  tint_fn=lambda co, n, t=t: (t, max(0.0, 1.0 - co.z / grime_h) * 0.8, 0.08, 1.0))
        z += h
    return z


def vine(B, rng, top, length, leaves=True):
    top = Vector(top)
    n = 8
    pts, radii = [], []
    ph = rng.uniform(0, TAU)
    for k in range(n):
        t = k / (n - 1)
        pts.append(top + Vector((math.sin(ph + t * 4.0) * 0.08 * t, -0.03 * t, -length * t)))
        radii.append(0.024 * (1 - 0.65 * t))
    B.add(bm_tube(pts, radii, segs=5), M["Moss"], smooth=True)
    if leaves:
        for k in range(1, n):
            for side in (-1, 1):
                if rng.random() < 0.38:
                    continue
                ang = side * rng.uniform(0.5, 1.1)
                rot = Matrix.Rotation(ang, 3, "Y") @ Matrix.Rotation(rng.uniform(-0.4, 0.4), 3, "X")
                L = rng.uniform(0.05, 0.075)
                p = pts[k] + rot @ Vector((side * 0.0, 0, 0)) + Matrix.Rotation(ang, 3, "Y") @ Vector((side * L, -0.01, 0))
                B.add(bm_blob(p, L, (1.0, 0.22, 0.42), segs=5, rings=3, rot=rot), M["Moss"], smooth=True)


def build_arch():
    rng = random.Random(61)
    B = Builder("ENV_Arch")
    cz = 2.45
    for s in (-1, 1):
        def X_(a, b):
            return (min(s * a, s * b), max(s * a, s * b))
        lo_x, hi_x = X_(1.94, 2.96)
        B.add(block((lo_x, -0.07, 0.0), (hi_x, 0.8, 0.32), rng, chips=2, chip_size=(0.05, 0.12), bevel=0.035,
                    segs=2, back_delete=0.75), M["Stone"], tint_fn=lambda co, n: (0.45, 0.9, 0.1, 1.0))
        lo_x, hi_x = X_(2.0, 2.9)
        z = pier(B, rng, lo_x, hi_x, [0.62, 0.55, 0.7], z=0.32, segs=2, bevel=0.03)
        lo_x, hi_x = X_(1.92, 2.98)
        B.add(block((lo_x, -0.07, z + 0.01), (hi_x, 0.8, cz), rng, chips=2, bevel=0.03, segs=2, back_delete=0.75,
                    cuts=[((0, -0.07 + 0.06, z + 0.01), (0, -1, -1))]), M["Stone"], tint=tint(rng))
        core = bm_box((min(s * 2.08, s * 2.82), 0.08, 0.3), (max(s * 2.08, s * 2.82), 0.72, cz))
        delete_faces(core, lambda c, n: n.y > 0.9)
        B.add(core, M["Mortar"], uvw=0.3)
    env = bmesh.new()
    voussoirs(B, rng, (0.0, cz), 2.0, 2.72, 0.0, 0.8, 11, 0.04, key_extra=0.26, env=env, segs=2, bevel=0.025,
              tint_g=0.45)
    # mortar ring behind the voussoir joints
    for i in range(12):
        a0, a1 = math.pi * i / 12, math.pi * (i + 1) / 12
        poly = [(2.06 * math.cos(a0), cz + 2.06 * math.sin(a0)), (2.64 * math.cos(a0), cz + 2.64 * math.sin(a0)),
                (2.64 * math.cos(a1), cz + 2.64 * math.sin(a1)), (2.06 * math.cos(a1), cz + 2.06 * math.sin(a1))]
        bm = bm_prism_xz(poly, 0.07, 0.72)
        delete_faces(bm, lambda c, n: n.y > 0.9)
        B.add(bm, M["Mortar"], uvw=0.3)
    # moss over the extrados
    bvh = eh.envelope_bvh(env)
    thetas = lin(rad(32), rad(148), 24)
    amp = [rng.uniform(-0.05, 0.08) for _ in range(5)]

    def D(th):
        u = (th - rad(32)) / rad(116)
        v = 0.16 + sum(amp[k] * math.sin(math.pi * (k + 1) * u + k) for k in range(5))
        return min(max(v, 0.06), 0.4) * math.sin(math.pi * u) ** 0.4

    def P(th, rho, y):
        return (rho * math.cos(th), y, cz + rho * math.sin(th))

    top = [[P(th, 3.6, y) for th in thetas] for y in (0.8, 0.55, 0.3, 0.1)] + [[P(th, 3.6, -0.5) for th in thetas]]
    front = [top[-1]] + [[P(th, 2.72 - t * (D(th) + 0.02), -0.5) for th in thetas] for t in (0.05, 0.5, 1.0)]
    sheet, keyed = eh.sheet_from_grids([top, front])
    tv = [keyed[eh.key_of(p)] for p in front[-1]]
    eh.project_sheet(sheet, bvh, offset=0.022, tuck_verts=tv,
                     lump=lambda p: 0.05 * max(0.0, eh.periodic_noise(p.x * 0.45, p.y * 2.0, p.z, 9.0, 3.0) + 0.15))
    B.add(sheet, M["Moss"], smooth=True)
    env.free()
    for th in lin(rad(38), rad(142), 9):
        r = 2.76
        B.add(bm_blob((r * math.cos(th), rng.uniform(-0.02, 0.5), cz + r * math.sin(th)), rng.uniform(0.09, 0.15),
                      (1.6, 1.1, 0.55), segs=7, rings=5, rng=rng, jitter=0.3), M["Moss"], smooth=True)
    for th in (rad(42), rad(64), rad(97), rad(118), rad(141)):
        top_p = (2.0 * math.cos(th) * 0.98, rng.uniform(0.12, 0.35), cz + 2.0 * math.sin(th) * 0.98)
        vine(B, rng, top_p, rng.uniform(0.6, 1.7))
    for th in lin(rad(45), rad(135), 7):
        th += rng.uniform(-0.05, 0.05)
        x, z_ = 2.72 * math.cos(th), cz + 2.72 * math.sin(th) - D(th)
        B.add(eh.moss_strand((x, -0.04, z_ + 0.04), rng.uniform(0.15, 0.45), rng, width=0.05), M["Moss"],
              smooth=True)
    for s in (-1, 1):
        B.add(bm_blob((s * 2.3, -0.02, cz + 0.02), 0.12, (1.5, 0.9, 0.7), segs=7, rings=5, rng=rng, jitter=0.15),
              M["Moss"], smooth=True)
    return B


# ---------------------------------------------------------------------------
# Cell door
# ---------------------------------------------------------------------------

def build_cell_door():
    rng = random.Random(71)
    B = Builder("ENV_CellDoor")
    S = M["Stone"]
    D0, D1 = 0.0, 0.45
    for s in (-1, 1):
        z = 0.0
        for k, h in enumerate([0.55, 0.5, 0.6, 0.5, 0.55]):
            outer = 1.2 if k % 2 == 0 else 1.1
            a, b = 0.8, outer
            lo = (min(s * a, s * b) + (G / 2 if s > 0 else 0), D0 + rng.uniform(-0.025, 0.02), z + G / 2)
            hi = (max(s * a, s * b) - (G / 2 if s < 0 else 0), D1, z + h - G / 2)
            pcs = block(lo, hi, rng, chips=rng.randint(1, 2), chip_size=(0.04, 0.1), bevel=0.025, segs=2,
                        jitter=0.012, back_delete=D1 - 0.05)
            t = rng.uniform(0.25, 0.75)
            B.add(pcs, S, tint_fn=lambda co, n, t=t: (t, max(0.0, 1.0 - co.z / 1.2) * 0.7, 0.08, 1.0))
            z += h
    # flat jack-arch lintel
    zl, zt = 2.7, 3.2
    parts = [[(-1.2, zl), (-0.36, zl), (-0.3, zt - 0.08), (-1.2, zt - 0.08)],
             [(-0.34 + G / 2, zl), (0.34 - G / 2, zl), (0.27 - G / 2 + 0.06, zt), (-0.27 + G / 2 - 0.06, zt)],
             [(0.36, zl), (1.2, zl), (1.2, zt - 0.08), (0.3, zt - 0.08)]]
    for i, poly in enumerate(parts):
        if i == 0:
            poly = [(poly[0][0], poly[0][1] + G / 2), (poly[1][0] - G / 2, poly[1][1] + G / 2),
                    (poly[2][0] - G / 2, poly[2][1]), (poly[3][0], poly[3][1])]
        elif i == 2:
            poly = [(poly[0][0] + G / 2, poly[0][1] + G / 2), (poly[1][0], poly[1][1] + G / 2),
                    (poly[2][0], poly[2][1]), (poly[3][0] + G / 2, poly[3][1])]
        else:
            poly = [(p[0], p[1] + (G / 2 if p[1] < zl + 0.01 else 0)) for p in poly]
        bm = bm_prism_xz(poly, D0 + rng.uniform(-0.03, 0.0), D1)
        for _ in range(2):
            eh.chip_vertex(bm, rng, rng.uniform(0.04, 0.09), pick=lambda co: co.y < 0.01)
        eh.bm_bevel(bm, 0.025, 2)
        delete_faces(bm, lambda c, n: n.y > 0.9 and c.y > D1 - 0.05)
        B.add(bm, S, tint=(rng.uniform(0.3, 0.7), 0.3, 0.1, 1.0))
    # threshold step
    B.add(block((-0.82, -0.06, 0.0), (0.82, 0.8, 0.1), rng, chips=2, bevel=0.02, segs=2, back_delete=0.75), S,
          tint=(0.4, 0.6, 0.15, 1.0))
    # mortar backing behind the frame joints
    for s in (-1, 1):
        core = bm_box((min(s * 0.86, s * 1.08), 0.05, 0.0), (max(s * 0.86, s * 1.08), 0.4, 2.75))
        delete_faces(core, lambda c, n: n.y > 0.9)
        B.add(core, M["Mortar"], uvw=0.25)
    lint_core = bm_box((-1.1, 0.05, 2.65), (1.1, 0.4, 3.1))
    delete_faces(lint_core, lambda c, n: n.y > 0.9)
    B.add(lint_core, M["Mortar"], uvw=0.25)
    # dark cell interior (recess)
    DK = M["Dark"]
    B.add(delete_faces(bm_box((-0.9, 0.8, 0.0), (0.9, 0.86, 2.8)), lambda c, n: n.y > 0.5), DK)
    for s in (-1, 1):
        B.add(delete_faces(bm_box((min(s * 0.8, s * 0.86), 0.4, 0.0), (max(s * 0.8, s * 0.86), 0.82, 2.8)),
                           lambda c, n, s=s: n.x * s < -0.5 and False or n.x * s > 0.5), DK, uvw=0.6)
    B.add(delete_faces(bm_box((-0.82, 0.4, 2.7), (0.82, 0.82, 2.76)), lambda c, n: n.z > 0.5), DK, uvw=0.6)
    B.add(delete_faces(bm_box((-0.82, 0.4, -0.05), (0.82, 0.82, 0.005)), lambda c, n: n.z < -0.5), DK, uvw=0.6)
    # shackles on the back wall
    for sx in (-0.35, 0.4):
        B.add(dome_rivet((sx, 0.8, 1.75), r=0.035), M["Iron"], smooth=True)
        ring = [(sx + 0.05 * math.sin(a), 0.78, 1.70 - 0.05 + 0.05 * math.cos(a)) for a in lin(0, TAU, 9)[:-1]]
        B.add(bm_tube(ring, 0.009, segs=5, closed=True, up=Y), M["Iron"], smooth=True)
    # --- iron door (built closed, then swung 6 deg on its hinge) ---
    door = Builder("tmp_door")
    I = M["Iron"]
    yd = 0.24
    xl, xr, zb, zt2 = -0.78, 0.78, 0.12, 2.66
    for lo, hi in (((xl, yd - 0.02, zb), (xl + 0.075, yd + 0.02, zt2)),
                   ((xr - 0.075, yd - 0.02, zb), (xr, yd + 0.02, zt2)),
                   ((xl + 0.07, yd - 0.02, zb), (xr - 0.07, yd + 0.02, zb + 0.075)),
                   ((xl + 0.07, yd - 0.02, zt2 - 0.075), (xr - 0.07, yd + 0.02, zt2))):
        door.add(block(lo, hi, rng, bevel=0.006, segs=1), I, tint=tint(rng))
    nb = 7
    bar_x = [xl + (xr - xl) * (i + 1) / (nb + 1) for i in range(nb)]
    for bx in bar_x:
        door.add(bm_tube([(bx, yd, zb + 0.05), (bx, yd, zt2 - 0.05)], 0.019, segs=8), I, smooth=True,
                 tint=tint(rng))
    for zs in (0.95, 1.95):
        door.add(block((xl + 0.05, yd - 0.045, zs - 0.045), (xr - 0.05, yd - 0.018, zs + 0.045), rng, bevel=0.006,
                       segs=1), I, tint=tint(rng))
        for bx in bar_x + [xl + 0.04, xr - 0.04]:
            door.add(dome_rivet((bx, yd - 0.045, zs), r=0.014), I, smooth=True)
    for zc in (zb + 0.04, zt2 - 0.04):
        for bx in (xl + 0.04, xr - 0.04):
            door.add(dome_rivet((bx, yd - 0.02, zc), r=0.014), I, smooth=True)
    door.add(block((0.5, yd - 0.075, 1.25), (0.72, yd - 0.025, 1.52), rng, bevel=0.008, segs=1), I, tint=tint(rng))
    door.add(block((0.6, yd - 0.082, 1.33), (0.625, yd - 0.07, 1.41), rng, bevel=0.0), M["Dark"])
    for zc in (0.45, 2.25):
        door.add(block((xl - 0.02, yd - 0.04, zc - 0.04), (xl + 0.34, yd - 0.018, zc + 0.04), rng, bevel=0.005,
                       segs=1), I, tint=tint(rng))
        door.add(bm_tube([(xl - 0.035, yd, zc - 0.1), (xl - 0.035, yd, zc + 0.1)], 0.028, segs=8), I, smooth=True)
        door.add(dome_rivet((xl + 0.28, yd - 0.04, zc), r=0.014), I, smooth=True)
    rotate(door.bm, rad(-6.0), "Z", (xl - 0.035, yd, 0))
    # merge door into the module, keeping its materials / sharp edges
    for f in door.bm.faces:
        pass
    me = bpy.data.meshes.new("tmp")
    door.bm.to_mesh(me)
    door.bm.free()
    tmp = bmesh.new()
    tmp.from_mesh(me)
    _merge_with_materials(B, tmp, door.mats)
    bpy.data.meshes.remove(me)
    # pinned pintle blocks on the jamb
    for zc in (0.45, 2.25):
        B.add(block((-0.9, 0.1, zc - 0.13), (-0.8, 0.3, zc + 0.13), rng, bevel=0.006, segs=1), I, tint=tint(rng))
    return B


def _merge_with_materials(B, src, mats):
    """Append a bmesh that has its own material indices / tint / uvw layers."""
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
        for l_new, l_old in zip(nf.loops, f.loops):
            l_new[B.tint] = l_old[t_src] if t_src else eh.NEUTRAL
            if uv_src:
                l_new[B.uv].uv = l_old[uv_src].uv
    for e in src.edges:
        if not e.smooth:
            ne = B.bm.edges.get((vmap[e.verts[0]], vmap[e.verts[1]]))
            if ne:
                ne.smooth = False
    src.free()


# ---------------------------------------------------------------------------
# Back wall (4 m x 4 m, tiles seamlessly)
# ---------------------------------------------------------------------------

def build_back_wall():
    rng = random.Random(81)
    B = Builder("ENV_BackWall")
    P = 4.0
    g = 0.05
    rows = [0.62, 0.55, 0.7, 0.5, 0.58, 0.48, 0.57]
    s = sum(rows)
    rows = [r * P / s for r in rows]
    z = 0.0
    missing = None

    def on_boundary(e):
        return all(abs(v.co.x) < 1e-4 for v in e.verts) or all(abs(v.co.x - P) < 1e-4 for v in e.verts)

    for ri, h in enumerate(rows):
        widths = []
        while sum(widths) < P - 0.4:
            widths.append(rng.uniform(0.7, 1.3))
        widths.append(P - sum(widths))
        if widths[-1] < 0.45:
            widths[-2] += widths[-1]
            widths.pop()
        off = rng.uniform(0.0, P)
        x = off
        for bi, w in enumerate(widths):
            a, b = x, x + w
            x = b
            if (ri, bi) == missing:
                continue
            d = rng.uniform(-0.03, 0.03) + (-0.04 if rng.random() < 0.12 else 0.0)
            t = (rng.uniform(0.2, 0.8), 0.0, rng.uniform(0.0, 0.3), 1.0)
            spans = []
            a_m, b_m = a % P, (b % P) if (b % P) > 1e-6 else P
            if a_m < b_m - 1e-6 and b - a < P:
                if b > P and a < P:
                    pass
                spans = [(a_m, b_m, True, True)] if b <= P or a >= P else []
            if b > P and a < P:
                spans = [(a, P, True, False), (0.0, b - P, False, True)]
            elif a >= P:
                spans = [(a - P, b - P, True, True)]
            elif not spans:
                spans = [(a, b, True, True)]
            nchips = rng.randint(0, 2)
            for (x0, x1, gap_l, gap_r) in spans:
                lo = (x0 + (g / 2 if gap_l else 0.0), d, z + g / 2)
                hi = (x1 - (g / 2 if gap_r else 0.0), 0.4, z + h - g / 2)
                if hi[0] - lo[0] < 0.08:
                    continue
                corners = []
                if gap_l:
                    corners += [(-1, -1, -1), (-1, -1, 1)]
                if gap_r:
                    corners += [(1, -1, -1), (1, -1, 1)]
                bm = bm_box(lo, hi)
                cr = random.Random(rng.random())
                for c in cr.sample(corners, min(nchips, len(corners))):
                    p = Vector((hi[0] if c[0] > 0 else lo[0], lo[1], hi[2] if c[2] > 0 else lo[2]))
                    eh.chip_corner(bm, p, c, cr, (0.04, 0.12), (hi[0] - lo[0], 0.4, h))
                eh.bm_bevel(bm, 0.04, 2, edge_filter=lambda e: not on_boundary(e))
                delete_faces(bm, lambda c_, n: (n.y > 0.9) or (abs(n.x) > 0.9 and (abs(c_.x) < 1e-3 or abs(c_.x - P) < 1e-3)))
                B.add(bm, M["StoneBack"], tint=t, uvw_fn=lambda c_, n: 0.4 if n.y > 0.5 else 1.0)
        z += h
    # mortar backing plane (front-facing quad only)
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in ((0, 0.13, 0), (P, 0.13, 0), (P, 0.13, P), (0, 0.13, P))]
    f0 = bm.faces.new(vs)
    bm.normal_update()
    if f0.normal.y > 0:
        f0.normal_flip()
    B.add(bm, M["MortarBack"], uvw=0.35)
    return B


# ---------------------------------------------------------------------------
# Torch sconce
# ---------------------------------------------------------------------------

def build_torch():
    rng = random.Random(91)
    B = Builder("ENV_Torch")
    I = M["Iron"]
    plate = bm_prism_xz([(-0.11, 0.0), (0.11, 0.0), (0.11, 0.33), (0.0, 0.44), (-0.11, 0.33)], -0.035, 0.0)
    eh.bm_bevel(plate, 0.008, 1)
    delete_faces(plate, lambda c, n: n.y > 0.9)
    B.add(plate, I, tint=tint(rng))
    for p in ((-0.07, 0.05), (0.07, 0.05), (-0.07, 0.3), (0.07, 0.3)):
        B.add(dome_rivet((p[0], -0.035, p[1]), r=0.017), I, smooth=True)
    cy = -0.33
    arm = [(0, -0.03, 0.18), (0, -0.12, 0.165), (0, -0.21, 0.19), (0, -0.28, 0.25), (0, cy, 0.3), (0, cy, 0.345)]
    B.add(bm_tube(arm, [0.024, 0.023, 0.022, 0.021, 0.021, 0.024], segs=8), I, smooth=True, tint=tint(rng))
    curl = [(0, -0.03, 0.06)]
    for k in range(1, 9):
        t = k / 8
        curl.append((0, -0.03 - 0.17 * t, 0.06 + 0.1 * math.sin(t * math.pi * 0.5)))
    for k in range(1, 7):
        a = math.pi * 0.5 + k / 6 * math.pi * 1.4
        curl.append((0, -0.2 - 0.05 * math.cos(a) * (1 - k / 14), 0.16 - 0.05 + 0.05 * math.sin(a)))
    B.add(bm_tube(curl, [0.012] * len(curl), segs=6), I, smooth=True)
    bowl = bm_lathe([(0.03, 0.335), (0.07, 0.345), (0.11, 0.37), (0.145, 0.415), (0.165, 0.465), (0.17, 0.48),
                     (0.155, 0.487), (0.14, 0.455), (0.11, 0.425), (0.05, 0.41), (0.02, 0.408)], segs=14,
                    cap_top=True, cap_bottom=True)
    translate(bowl, (0, cy, 0))
    B.add(bowl, I, smooth=True, tint=tint(rng), uvw=1.2)
    for k in range(6):
        a = TAU * k / 6 + 0.3
        base = Vector((math.cos(a) * 0.158, cy + math.sin(a) * 0.158, 0.47))
        tip = base + Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.075))
        B.add(bm_tube([base, tip], [0.016, 0.003], segs=4), I, smooth=True)
    ring = bm_lathe([(0.168, 0.405), (0.178, 0.41), (0.178, 0.43), (0.165, 0.435)], segs=14)
    translate(ring, (0, cy, 0))
    B.add(ring, I, smooth=True)
    for k in range(9):
        a = rng.uniform(0, TAU)
        rr = rng.uniform(0.0, 0.09)
        c = (math.cos(a) * rr, cy + math.sin(a) * rr, 0.445 + rng.uniform(0.0, 0.03))
        bm = bm_ico(c, rng.uniform(0.035, 0.055), (1.0, 1.0, 0.7), subdiv=1, rng=rng, jitter=0.25)
        B.add(bm, M["Coal"], hard=40, uvw=1.3)
    B.sockets["FlameSocket"] = (0.0, cy, 0.53)
    s = 1.5
    scale(B.bm, s)
    B.sockets["FlameSocket"] = tuple(c * s for c in B.sockets["FlameSocket"])
    return B


# ---------------------------------------------------------------------------
# Window grate
# ---------------------------------------------------------------------------

def build_grate():
    rng = random.Random(101)
    B = Builder("ENV_Grate")
    S = M["Stone"]
    hw, zr, cz = 0.6, 1.1, 1.1      # opening half width, rect top (=arch centre)
    y1 = 0.35
    B.add(block((-0.95, -0.08, 0.16), (0.95, 0.4, 0.3), rng, chips=2, bevel=0.025, segs=2, back_delete=0.35), S,
          tint=(0.5, 0.7, 0.1, 1.0))
    for s in (-1, 1):
        B.add(block((min(s * 0.45, s * 0.75), -0.04, 0.0), (max(s * 0.45, s * 0.75), 0.35, 0.16 + 0.004), rng,
                    chips=1, bevel=0.02, segs=1, back_delete=0.3,
                    cuts=[((s * 0.45, -0.04, 0.0), (-s * 0.0, -1, -1.2))]), S, tint=tint(rng))
        z = 0.3
        for k, h in enumerate([0.4, 0.4]):
            outer = 0.98 if k == 0 else 0.9
            lo = (min(s * hw, s * outer) + (G / 2 if s > 0 else 0), rng.uniform(-0.02, 0.01), z + G / 2)
            hi = (max(s * hw, s * outer) - (G / 2 if s < 0 else 0), y1, z + h - G / 2)
            B.add(block(lo, hi, rng, chips=rng.randint(1, 2), bevel=0.025, segs=2, jitter=0.01, back_delete=0.3), S,
                  tint=tint(rng))
            z += h
    voussoirs(B, rng, (0.0, cz), hw, 0.86, 0.0, y1, 7, 0.04, key_extra=0.06, jitter_r=0.035, segs=2, bevel=0.022)
    for s in (-1, 1):
        core = bm_box((min(s * 0.64, s * 0.86), 0.06, 0.28), (max(s * 0.64, s * 0.86), 0.3, cz + 0.02))
        delete_faces(core, lambda c, n: n.y > 0.9)
        B.add(core, M["Mortar"], uvw=0.25)
    for i in range(10):
        a0, a1 = math.pi * i / 10, math.pi * (i + 1) / 10
        poly = [(0.64 * math.cos(a0), cz + 0.64 * math.sin(a0)), (0.8 * math.cos(a0), cz + 0.8 * math.sin(a0)),
                (0.8 * math.cos(a1), cz + 0.8 * math.sin(a1)), (0.64 * math.cos(a1), cz + 0.64 * math.sin(a1))]
        bm = bm_prism_xz(poly, 0.06, 0.3)
        delete_faces(bm, lambda c, n: n.y > 0.9)
        B.add(bm, M["Mortar"], uvw=0.25)
    # recess tunnel behind the opening (inward facing) + back panel
    outline = [(-hw, 0.3), (hw, 0.3)] + [(hw * math.cos(a), cz + hw * math.sin(a)) for a in lin(0, math.pi, 9)]
    outline = [(-hw, 0.3), (hw, 0.3)] + [(hw * math.cos(a), cz + hw * math.sin(a)) for a in lin(0, math.pi, 9)][0:]
    tun = bm_prism_xz([(hw, 0.3)] + [(hw * math.cos(a), cz + hw * math.sin(a)) for a in lin(0, math.pi, 9)] +
                      [(-hw, 0.3)], 0.335, 0.55)
    bmesh.ops.reverse_faces(tun, faces=list(tun.faces))
    delete_faces(tun, lambda c, n: c.y < 0.34)
    B.add(tun, M["Dark"], uvw=0.6)
    I = M["Iron"]
    yb = 0.17
    for bx in (-0.45, -0.225, 0.0, 0.225, 0.45):
        ztop = cz + math.sqrt(max(hw * hw - bx * bx, 0.0)) + 0.03
        B.add(bm_tube([(bx, yb, 0.27), (bx, yb, ztop)], 0.024, segs=8), I, smooth=True, tint=tint(rng))
    for zs in (0.62, 0.98, 1.34):
        half = hw if zs <= cz else math.sqrt(hw * hw - (zs - cz) ** 2)
        B.add(block((-half - 0.02, yb - 0.05, zs - 0.035), (half + 0.02, yb - 0.022, zs + 0.035), rng, bevel=0.006,
                    segs=1), I, tint=tint(rng))
        for bx in (-0.45, -0.225, 0.0, 0.225, 0.45):
            if abs(bx) < half:
                B.add(dome_rivet((bx, yb - 0.05, zs), r=0.016), I, smooth=True)
    for k in range(5):
        B.add(bm_blob((rng.uniform(-0.8, 0.8), -0.04, 0.31), rng.uniform(0.06, 0.1), (1.5, 0.9, 0.7), segs=7, rings=5,
                      rng=rng, jitter=0.15), M["Moss"], smooth=True)
    for k in range(3):
        x = rng.uniform(-0.8, 0.8)
        B.add(eh.moss_strand((x, -0.1, 0.25), rng.uniform(0.12, 0.25), rng, width=0.03), M["Moss"], smooth=True)
    return B


# ---------------------------------------------------------------------------
# Chains
# ---------------------------------------------------------------------------

L_IN, W_IN, WIRE = 0.146, 0.066, 0.017


def chain_link(segs=6, path_pts=12):
    a = W_IN / 2 + WIRE
    hl = L_IN / 2 + WIRE
    s = hl - a
    half = path_pts // 2
    pts = []
    for i in range(half):
        t = math.pi * i / (half - 1)
        pts.append((a * math.cos(t), 0.0, s + a * math.sin(t)))
    for i in range(half):
        t = math.pi + math.pi * i / (half - 1)
        pts.append((a * math.cos(t), 0.0, -s + a * math.sin(t)))
    return bm_tube(pts, WIRE, segs=segs, up=Y, closed=True)


def build_chain_link():
    B = Builder("ENV_ChainLink")
    bm = chain_link()
    translate(bm, (0, 0, -L_IN / 2))
    B.add(bm, M["Iron"], smooth=True, uvw=1.5)
    return B


def build_chain():
    rng = random.Random(111)
    B = Builder("ENV_Chain")
    I = M["Iron"]
    B.add(block((-0.09, -0.09, -0.035), (0.09, 0.09, 0.0), rng, bevel=0.008, segs=1), I, tint=tint(rng))
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        B.add(dome_rivet((sx * 0.06, sy * 0.06, -0.035), r=0.014, facing=Vector((0, 0, -1))), I, smooth=True)
    eye_r, eye_w = 0.05, 0.015
    eye_c = -0.035 - eye_r + 0.012
    ring = [(0.0, eye_r * math.cos(a), eye_c + eye_r * math.sin(a)) for a in lin(0, TAU, 13)[:-1]]
    B.add(bm_tube(ring, eye_w, segs=6, closed=True, up=X), I, smooth=True)
    c = eye_c - eye_r + eye_w + WIRE - (L_IN / 2 + WIRE)
    k = 0
    while c - L_IN / 2 - 2 * WIRE > -2.83:
        bm = chain_link()
        if k % 2 == 1:
            rotate(bm, math.pi / 2, "Z")
        rotate(bm, rng.uniform(-0.04, 0.04), "Z")
        translate(bm, (0, 0, c))
        B.add(bm, I, smooth=True, tint=tint(rng), uvw=1.4)
        c -= L_IN
        k += 1
    # hook on the end, hanging from the last link's bottom
    top = c + L_IN - L_IN / 2 + WIRE * 0.0
    hook_eye_c = c + L_IN / 2 - 0.04 + WIRE
    rr = 0.035
    plane_rot = math.pi / 2 if k % 2 == 1 else 0.0
    eye = [(rr * math.cos(a), 0.0, hook_eye_c + rr * math.sin(a)) for a in lin(0, TAU, 11)[:-1]]
    hook = [(0.0, 0.0, hook_eye_c - rr), (0.0, 0.0, hook_eye_c - rr - 0.06)]
    hb = hook_eye_c - rr - 0.06
    R = 0.06
    for a in lin(math.pi, math.pi * 2.15, 8)[1:]:
        hook.append((R + R * math.cos(a), 0.0, hb + R * math.sin(a)))
    e_bm = bm_tube(eye, 0.016, segs=6, closed=True, up=Y)
    h_bm = bm_tube(hook, [0.02] * (len(hook) - 2) + [0.014, 0.006], segs=6)
    for bm in (e_bm, h_bm):
        rotate(bm, plane_rot, "Z")
        B.add(bm, I, smooth=True, tint=tint(rng))
    return B


# ---------------------------------------------------------------------------
# Gibbet cage with skeleton
# ---------------------------------------------------------------------------

def bm_bone(p0, p1, r=0.016, knob=0.03, segs=6):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    k = min(knob, L / 6)
    prof = [(k * 0.55, 0.0), (k, k * 0.6), (k * 0.85, k * 1.6), (r, k * 2.7), (r * 0.9, L / 2), (r, L - k * 2.7),
            (k * 0.85, L - k * 1.6), (k, L - k * 0.6), (k * 0.55, L)]
    bm = bm_lathe(prof, segs=segs, scale_xy=(1.15, 0.85))
    return transform(bm, eh.look_matrix(p0, p1))


def bm_skull(center, rng, size=1.0, yaw=0.0, pitch=0.0, roll=0.0):
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1.0, calc_uvs=True)
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


def rib(center, ax, ay, r=0.011, tilt=0.15):
    c = Vector(center)
    pts = []
    for a in lin(rad(-80), rad(260), 9):
        if 95 < math.degrees(a) % 360 < 110:
            continue
    for a in lin(rad(15), rad(165), 8):
        pts.append(c + Vector((ax * math.cos(a), -ay * math.sin(a), -tilt * math.sin(a) * ay)))
    return bm_tube(pts, r, segs=4, cap=True)


def build_cage():
    rng = random.Random(121)
    B = Builder("ENV_Cage")
    I = M["Iron"]
    ring_r, ring_w = 0.07, 0.018
    rc = -ring_r - ring_w
    ring = [(ring_r * math.cos(a), 0.0, rc + ring_r * math.sin(a)) for a in lin(0, TAU, 15)[:-1]]
    B.add(bm_tube(ring, ring_w, segs=6, closed=True, up=Y), I, smooth=True, tint=tint(rng))
    B.add(bm_lathe([(0.03, -0.27), (0.03, -0.15), (0.045, -0.14), (0.045, -0.165)], segs=8), I, smooth=True)
    B.add(bm_lathe([(0.02, -0.25), (0.06, -0.255), (0.12, -0.28), (0.17, -0.315), (0.175, -0.335), (0.12, -0.34),
                    (0.04, -0.34)], segs=12), I, smooth=True, tint=tint(rng))
    prof = [(0.15, -0.31), (0.32, -0.38), (0.46, -0.5), (0.56, -0.68), (0.6, -0.9), (0.6, -1.2), (0.6, -1.55),
            (0.59, -1.85), (0.55, -2.02), (0.48, -2.09)]
    n_bars = 10
    for k in range(n_bars):
        phi = TAU * k / n_bars + TAU / 20
        pts = []
        broken = (k == 8)
        bent = (k == 3)
        for (r, z) in prof:
            if broken and -1.75 < z < -1.0:
                continue
            rr = r + (0.09 * math.sin(math.pi * min(max((-z - 0.8) / 1.0, 0), 1)) if bent else 0.0)
            pts.append((rr * math.cos(phi), rr * math.sin(phi), z))
        if broken:
            upper = [p for p in pts if p[2] > -1.0] + [(0.6 * math.cos(phi) * 1.04, 0.6 * math.sin(phi) * 1.04, -1.0 - 0.05)]
            lower = [(0.6 * math.cos(phi) * 1.06, 0.6 * math.sin(phi) * 1.06, -1.78)] + [p for p in pts if p[2] < -1.75]
            B.add(bm_tube(upper, [0.017] * (len(upper) - 1) + [0.012], segs=6), I, smooth=True, tint=tint(rng))
            B.add(bm_tube(lower, [0.012] + [0.017] * (len(lower) - 1), segs=6), I, smooth=True, tint=tint(rng))
        else:
            B.add(bm_tube(pts, 0.017, segs=6), I, smooth=True, tint=tint(rng))
    for zc, r in ((-0.68, 0.575), (-1.25, 0.617), (-1.88, 0.605)):
        B.add(bm_lathe([(r, zc - 0.03), (r + 0.018, zc - 0.03), (r + 0.018, zc + 0.03), (r, zc + 0.03),
                        (r, zc - 0.03)], segs=24, cap_top=False, cap_bottom=False), I, smooth=False,
              tint=tint(rng), hard=50)
    B.add(bm_lathe([(0.04, -2.12), (0.5, -2.12), (0.53, -2.1), (0.5, -2.075), (0.06, -2.075)], segs=20), I,
          tint=tint(rng), hard=50)
    B.add(bm_lathe([(0.13, -2.125), (0.06, -2.2), (0.015, -2.3)], segs=8), I, smooth=True)
    # skeleton slumped against the rear bars, facing the camera (-Y)
    BN = M["Bone"]
    fz = -2.075
    B.add(bm_blob((0.0, 0.26, fz + 0.09), 0.11, (1.3, 0.75, 0.6), segs=8, rings=5), BN, smooth=True)
    spine = [(0.0, 0.3, fz + 0.14), (0.0, 0.36, fz + 0.35), (0.01, 0.38, fz + 0.55), (0.02, 0.32, fz + 0.72),
             (0.03, 0.22, fz + 0.8)]
    B.add(bm_tube(spine, [0.028, 0.026, 0.025, 0.022, 0.02], segs=6), BN, smooth=True)
    for k, (zc, ax) in enumerate(((0.42, 0.11), (0.5, 0.135), (0.58, 0.145), (0.65, 0.135), (0.71, 0.11))):
        B.add(rib((0.0, 0.35, fz + zc), ax, 0.15 - k * 0.006), BN, smooth=True)
    sk, jaw = bm_skull((0.04, 0.15, fz + 0.88), rng, 1.0, yaw=rad(-12), pitch=rad(-28), roll=rad(14))
    B.add(sk, BN, smooth=True, uvw=1.4)
    B.add(jaw, BN, uvw=1.4)
    sh_l, sh_r = Vector((-0.15, 0.3, fz + 0.72)), Vector((0.15, 0.3, fz + 0.72))
    B.add(bm_bone(sh_l, (-0.22, 0.12, fz + 0.45)), BN, smooth=True)
    B.add(bm_bone((-0.22, 0.12, fz + 0.45), (-0.12, -0.08, fz + 0.3), r=0.013, knob=0.024), BN, smooth=True)
    B.add(bm_bone(sh_r, (0.38, 0.0, fz + 0.52)), BN, smooth=True)
    hand = (0.6 * math.cos(TAU * 8 / 10 + TAU / 20) * 1.15, 0.6 * math.sin(TAU * 8 / 10 + TAU / 20) * 1.15, fz + 0.3)
    B.add(bm_bone((0.38, 0.0, fz + 0.52), hand, r=0.013, knob=0.024), BN, smooth=True)
    for sx in (-1, 1):
        hip = (sx * 0.09, 0.22, fz + 0.08)
        knee = (sx * 0.16, -0.14, fz + 0.36)
        ankle = (sx * 0.18, -0.34, fz + 0.04)
        B.add(bm_bone(hip, knee, r=0.019, knob=0.034), BN, smooth=True)
        B.add(bm_bone(knee, ankle, r=0.016, knob=0.028), BN, smooth=True)
        B.add(bm_blob((sx * 0.19, -0.4, fz + 0.025), 0.05, (0.7, 1.4, 0.4), segs=6, rings=4), BN, smooth=True)
    return B


# ---------------------------------------------------------------------------
# Props: barrel, crate, bone pile, banner
# ---------------------------------------------------------------------------

def build_barrel():
    rng = random.Random(131)
    B = Builder("ENV_Barrel")
    H, Rm, Re = 1.0, 0.42, 0.355
    n = 14
    gap = rad(0.9)
    zs = lin(0.0, H, 7)

    def r_at(z):
        u = (z - H / 2) / (H / 2)
        return Rm - (Rm - Re) * u * u

    for i in range(n):
        a0 = TAU * i / n + gap / 2
        a1 = TAU * (i + 1) / n - gap / 2
        bm = bmesh.new()
        outer, inner = [], []
        dr = rng.uniform(-0.006, 0.006)
        for z in zs:
            r = r_at(z) + dr
            outer.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in (a0, a1)])
            inner.append([bm.verts.new(((r - 0.035) * math.cos(a), (r - 0.035) * math.sin(a), z)) for a in (a0, a1)])
        for k in range(len(zs) - 1):
            bm.faces.new((outer[k][0], outer[k][1], outer[k + 1][1], outer[k + 1][0]))
            bm.faces.new((inner[k][1], inner[k][0], inner[k + 1][0], inner[k + 1][1]))
            bm.faces.new((inner[k][0], outer[k][0], outer[k + 1][0], inner[k + 1][0]))
            bm.faces.new((outer[k][1], inner[k][1], inner[k + 1][1], outer[k + 1][1]))
        bm.faces.new((inner[0][0], inner[0][1], outer[0][1], outer[0][0]))
        top = len(zs) - 1
        bm.faces.new((outer[top][0], outer[top][1], inner[top][1], inner[top][0]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        eh.bm_bevel(bm, 0.006, 1, min_angle=40)
        B.add(bm, M["WoodZ"], tint=tint(rng), uvw_fn=lambda c, nn: 0.4 if (c.x * nn.x + c.y * nn.y) < 0 else 1.0)
    for zc in (0.1, 0.36, 0.64, 0.9):
        r = r_at(zc) + 0.004
        B.add(bm_lathe([(r, zc - 0.035), (r + 0.014, zc - 0.033), (r + 0.014, zc + 0.033), (r, zc + 0.035),
                        (r, zc - 0.035)], segs=28, cap_top=False, cap_bottom=False), M["Iron"], tint=tint(rng),
              hard=50)
    lid_r = Re - 0.03
    for k, (x0, x1) in enumerate(((-lid_r, -0.11), (-0.105, 0.105), (0.11, lid_r))):
        pts = []
        for x in lin(x0, x1, 5):
            y = math.sqrt(max(lid_r * lid_r - x * x, 0.0))
            pts.append((x, y))
        poly = [(x, -y) for x, y in pts] + [(x, y) for x, y in reversed(pts)]
        bm = bmesh.new()
        lo = [bm.verts.new((x, y, H - 0.06)) for x, y in poly]
        hi = [bm.verts.new((x, y, H - 0.035)) for x, y in poly]
        bm.faces.new(hi)
        bm.faces.new(list(reversed(lo)))
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        B.add(bm, M["WoodX"], tint=tint(rng), uvw=0.6)
    B.add(bm_lathe([(Re - 0.035, 0.03), (0.05, 0.03)], segs=14, cap_top=True, cap_bottom=False), M["WoodX"],
          uvw=0.2)
    translate(B.bm, (0, Rm, 0))
    return B


def build_crate():
    rng = random.Random(141)
    B = Builder("ENV_Crate")
    S = 0.9
    h = S / 2
    bt = 0.085
    yc = h  # centre y (front plane at y=0)
    core = bm_box((-h + 0.04, 0.04, 0.04), (h - 0.04, S - 0.04, S - 0.04))
    B.add(core, M["WoodX"], tint=(0.3, 0.0, 0.7, 1.0), uvw=0.3)
    # 12 edge battens
    for ax in range(3):
        for sa in (-1, 1):
            for sb in (-1, 1):
                lo, hi = [0, 0, 0], [0, 0, 0]
                c = [0.0, yc, h]
                o = [i for i in range(3) if i != ax]
                for i, s_ in zip(o, (sa, sb)):
                    lo[i] = c[i] + s_ * h - (bt if s_ > 0 else 0)
                    hi[i] = c[i] + s_ * h + (0 if s_ > 0 else bt)
                lo[ax], hi[ax] = c[ax] - h + (bt if ax != 2 else 0) * 0, c[ax] + h
                lo[ax] = c[ax] - h
                if ax != 2:
                    lo[ax] += bt
                    hi[ax] -= bt
                mat = M["Wood" + "XYZ"[ax]]
                B.add(block(lo, hi, rng, chips=1, chip_size=(0.01, 0.03), bevel=0.012, segs=1,
                            corners=[(-1, -1, 1), (1, -1, 1)]), mat, tint=tint(rng),
                      uvw_fn=lambda c_, n: 0.3 if (n.y > 0.5 or n.z < -0.5) else 1.0)
    # plank panels on front (y=0), left/right sides, top
    def panels(face):
        for k, (a, b) in enumerate(((bt, 0.33), (0.335, 0.565), (0.57, S - bt))):
            if face == "front":
                lo, hi, mat = (-h + bt, 0.02, a), (h - bt, 0.06, b), M["WoodX"]
            elif face == "top":
                lo, hi, mat = (-h + bt, a, S - 0.06), (h - bt, b, S - 0.02), M["WoodX"]
            else:
                sx = -1 if face == "left" else 1
                xa, xb = sx * (h - 0.02), sx * (h - 0.06)
                lo, hi, mat = (min(xa, xb), a, bt), (max(xa, xb), b, S - bt), M["WoodZ"]
            B.add(block(lo, hi, rng, bevel=0.008, segs=1), mat, tint=tint(rng),
                  uvw_fn=lambda c_, n: 0.3 if n.y > 0.5 else 1.0)
    for f in ("front", "top", "left", "right"):
        panels(f)
    # diagonal braces
    L = math.hypot(S - 2 * bt, S - 2 * bt)
    for face in ("front", "left", "right"):
        bm = bm_box((-L / 2 - 0.08, -0.02, -0.055), (L / 2 + 0.08, 0.02, 0.055))
        eh.bm_bevel(bm, 0.01, 1)
        rotate(bm, rad(45) if face != "right" else rad(-45), "Y")
        bm_cut(bm, (0, 0, S / 2 - bt), (0, 0, 1))
        bm_cut(bm, (0, 0, -S / 2 + bt), (0, 0, -1))
        bm_cut(bm, (S / 2 - bt, 0, 0), (1, 0, 0))
        bm_cut(bm, (-S / 2 + bt, 0, 0), (-1, 0, 0))
        if face == "front":
            translate(bm, (0, 0.012, h))
        else:
            sx = -1 if face == "left" else 1
            rotate(bm, rad(90) * sx, "Z")
            translate(bm, (sx * (h - 0.012), yc, h))
        B.add(bm, M["WoodX"], tint=tint(rng))
    # iron corner brackets
    for sx in (-1, 1):
        for zc in (0.0, S):
            sz = 1 if zc > 0 else -1
            x_out = sx * (h + 0.006)
            B.add(block((min(sx * (h - 0.15), x_out), -0.008, min(zc, zc - sz * 0.15)),
                        (max(sx * (h - 0.15), x_out), 0.004, max(zc, zc - sz * 0.15)), rng, bevel=0.004, segs=1,
                        cuts=[((sx * (h - 0.15), 0, zc - sz * 0.15 + sz * 0.0), (-sx, 0, -sz))]),
                  M["Iron"], tint=tint(rng))
            B.add(block((min(x_out, sx * (h - 0.004)), -0.008, min(zc, zc - sz * 0.15)),
                        (max(x_out, sx * (h - 0.004)) + 0.0, 0.15, max(zc, zc - sz * 0.15)), rng, bevel=0.004, segs=1),
                  M["Iron"], tint=tint(rng))
            B.add(dome_rivet((sx * (h - 0.05), -0.008, zc - sz * 0.05), r=0.012), M["Iron"], smooth=True)
    return B


def build_bone_pile():
    rng = random.Random(151)
    B = Builder("ENV_BonePile")
    RX, RY, RZ, CY = 0.85, 0.55, 0.3, 0.6

    def surf(x, y):
        u = 1 - (x / RX) ** 2 - ((y - CY) / RY) ** 2
        return RZ * math.sqrt(max(u, 0.0))

    mound = bm_blob((0, CY, 0), 1.0, (RX, RY, RZ), segs=14, rings=7, rng=rng, jitter=0.03)
    bm_cut(mound, (0, 0, 0.0), (0, 0, -1))
    delete_faces(mound, lambda c, n: n.z < -0.9)
    B.add(mound, M["Dirt"], smooth=True, uvw=0.5)
    for k in range(24):
        a = rng.uniform(0, TAU)
        rr = rng.uniform(0.0, 0.85)
        x, y = math.cos(a) * RX * rr, CY + math.sin(a) * RY * rr
        z = surf(x, y)
        ang = rng.uniform(0, TAU)
        L = rng.uniform(0.25, 0.45)
        tilt = rng.uniform(-0.25, 0.45)
        d = Vector((math.cos(ang), math.sin(ang) * 0.7, tilt)).normalized() * L
        p0 = Vector((x, y, z + 0.015)) - d * 0.5
        p1 = Vector((x, y, z + 0.015)) + d * 0.5
        p0.z = max(p0.z, surf(p0.x, p0.y) - 0.01)
        p1.z = max(p1.z, surf(p1.x, p1.y) - 0.01)
        B.add(bm_bone(p0, p1, r=rng.uniform(0.014, 0.02), knob=rng.uniform(0.026, 0.034), segs=5), M["Bone"],
              smooth=True, tint=tint(rng))
    spots = [(-0.35, 0.3), (0.05, 0.25), (0.42, 0.4), (-0.12, 0.65), (0.3, 0.75), (-0.6, 0.55)]
    for (x, y) in spots:
        z = surf(x, y)
        sk, jaw = bm_skull((x, y, z + 0.08), rng, size=rng.uniform(0.95, 1.1), yaw=rng.uniform(-0.6, 0.6),
                           pitch=rng.uniform(-0.3, 0.2), roll=rng.uniform(-0.4, 0.4))
        t = tint(rng)
        B.add(sk, M["Bone"], smooth=True, tint=t, uvw=1.3)
        B.add(jaw, M["Bone"], tint=t, uvw=1.3)
    for k in range(3):
        x, y = rng.uniform(-0.5, 0.5), rng.uniform(0.4, 0.8)
        B.add(rib((x, y, surf(x, y) + 0.02), 0.12, 0.1, tilt=-0.4), M["Bone"], smooth=True)
    translate(B.bm, (0, -min(v.co.y for v in B.bm.verts), 0))   # front plane at y=0
    return B


def build_banner():
    rng = random.Random(161)
    B = Builder("ENV_Banner")
    rz = -0.035
    rod = bm_lathe([(0.035, -0.62), (0.035, 0.62)], segs=8)
    rotate(rod, math.pi / 2, "Y")
    translate(rod, (0, 0, rz))
    B.add(rod, M["WoodX"], smooth=True, tint=tint(rng))
    for s in (-1, 1):
        fin = bm_lathe([(0.03, 0.0), (0.05, 0.03), (0.055, 0.06), (0.03, 0.09), (0.035, 0.11), (0.012, 0.15)],
                       segs=8)
        rotate(fin, s * math.pi / 2, "Y")
        translate(fin, (s * 0.6, 0, rz))
        B.add(fin, M["Iron"], smooth=True, tint=tint(rng))
    cols, rows = 15, 26
    W = 1.0
    ph = rng.uniform(0, TAU)

    def tear(u):
        v = 0.55 * (1 - abs(2 * u - 1)) ** 1.6
        return v

    jag = [rng.uniform(-0.08, 0.06) for _ in range(cols)]
    jag[0] = jag[-1] = 0.0
    wrap = [(0.046 * math.cos(a), rz + 0.046 * math.sin(a)) for a in (rad(40), rad(90), rad(140), rad(215))]
    grid = []
    for r in range(len(wrap) + rows):
        row = []
        for c in range(cols):
            u = c / (cols - 1)
            x = (u - 0.5) * W
            if r < len(wrap):
                y, z = wrap[r]
                row.append(Vector((x, y, z)))
                continue
            t = (r - len(wrap) + 1) / rows
            zb = -2.5 + tear(u) + jag[c]
            z = -0.075 + (zb + 0.075) * t
            fold = 0.04 * math.sin(TAU * (u * 2.3) + ph) * min(1.0, t * 4) + 0.015 * math.sin(TAU * u * 5 + 1) * t
            x += 0.03 * math.sin(t * 3 + ph) * t * (1 - abs(2 * u - 1))
            row.append(Vector((x * (1 - 0.06 * t), -0.046 - fold, z)))
        grid.append(row)
    bm = bmesh.new()
    vg = [[bm.verts.new(p) for p in row] for row in grid]
    holes = {(rows - 8, 4), (rows - 13, 10), (rows - 12, 10)}
    for r in range(len(grid) - 1):
        for c in range(cols - 1):
            if (r - len(wrap), c) in holes:
                continue
            bm.faces.new((vg[r][c], vg[r + 1][c], vg[r + 1][c + 1], vg[r][c + 1]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    for (hr, hc) in holes:
        r = hr + len(wrap)
        for v in (vg[r][hc], vg[r + 1][hc + 1]):
            v.co += Vector((rng.uniform(-0.03, 0.03), 0, rng.uniform(-0.03, 0.03)))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.012)
    B.add(bm, M["Cloth"], smooth=True, uvw=1.0)
    for s in (-1, 1):
        loop = [(s * 0.42 + 0.03 * math.cos(a), 0.06 * math.sin(a) - 0.0, rz + 0.06 * math.cos(a) * 0.0 + 0.055 * math.cos(a))
                for a in lin(0, TAU, 9)[:-1]]
        loop = [(s * 0.42, 0.058 * math.sin(a), rz + 0.058 * math.cos(a)) for a in lin(0, TAU, 9)[:-1]]
        B.add(bm_tube(loop, 0.012, segs=5, closed=True, up=X), M["WoodY"], smooth=True)
    return B


# ---------------------------------------------------------------------------
# Background silhouettes (booleans for window recesses and broken parts)
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
    def __init__(self, name):
        self.win = Builder(name + "_cutwin")
        self.post = Builder(name + "_post")
        self.brk = []
        self.axes = []
        self.name = name

    def window(self, poly, y_front, depth, rot_z=0.0, pivot=(0, 0, 0)):
        bm = bm_prism_xz(poly, y_front - 1.5, y_front + depth)
        if rot_z:
            rotate(bm, rot_z, "Z", pivot)
        self.axes.append(Matrix.Rotation(rot_z, 3, "Z") @ Y)
        self.win.add(bm, M["BGWindow"])

    def breakage(self, center, size, rng, n=3):
        for k in range(n):
            c = Vector(center) + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.35 * Vector(size)
            pts = [c + Vector((rng.uniform(-1, 1) * size[0], rng.uniform(-1, 1) * size[1], rng.uniform(-1, 1) * size[2]))
                   for _ in range(9)]
            b = Builder(f"{self.name}_brk{k}_{len(self.brk)}")
            b.add(eh.bm_hull(pts), M["BGStone"])
            self.brk.append(b)


def finish_bg(B, cut, rng):
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
        name = obj.name
        obj = dc.join([obj, post], name)
    else:
        cut.post.bm.free()
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    mats = list(me.materials)
    win_i = next((i for i, m in enumerate(mats) if m and m.name == "M_BGWindow"), None)
    stone_i = next((i for i, m in enumerate(mats) if m and m.name == "M_BGStone"), 0)
    if win_i is not None:
        for f in bm.faces:
            if f.material_index == win_i:
                if not any(abs(f.normal.dot(a)) > 0.75 for a in cut.axes):
                    f.material_index = stone_i
    dead = [f for f in bm.faces if f.normal.y > 0.55 or (f.normal.z < -0.9 and f.calc_center_median().z < 0.05)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    lim = rad(32)
    smooth_mats = {i for i, m in enumerate(mats) if m and m.name in ("M_BGRoof",)}
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


def bg_box(B, rng, lo, hi, bevel=0.06, mat=None, cuts=(), t=None):
    bm = bm_box(lo, hi)
    for co, no in cuts:
        bm_cut(bm, co, no)
    eh.bm_bevel(bm, bevel, 1)
    B.add(bm, mat or M["BGStone"], tint=t or tint(rng))


def build_tower_a():
    rng = random.Random(301)
    B = Builder("BG_Tower_A")
    cut = Cutters("BG_Tower_A")
    bg_box(B, rng, (-3.5, 0.0, 0.0), (3.5, 5.0, 2.0), 0.1, cuts=[((0, 0.5, 2.0), (0, -1, 1))])
    bg_box(B, rng, (-3.0, 0.5, 1.8), (3.0, 5.0, 19.3), 0.08)
    for s in (-1, 1):
        x0, x1 = sorted((s * 3.55, s * 2.45))
        bg_box(B, rng, (x0, -0.55, 1.8), (x1, 1.6, 8.2), 0.08, cuts=[((0, -0.55 + 0.9, 8.2), (0, -1, 1.1))])
        x0, x1 = sorted((s * 3.45, s * 2.55))
        bg_box(B, rng, (x0, -0.2, 7.0), (x1, 1.6, 13.6), 0.08, cuts=[((0, -0.2 + 0.7, 13.6), (0, -1, 1.1))])
        x0, x1 = sorted((s * 3.35, s * 2.65))
        bg_box(B, rng, (x0, 0.15, 12.5), (x1, 1.6, 17.2), 0.08, cuts=[((0, 0.15 + 0.6, 17.2), (0, -1, 1.1))])
    for zc in (8.3, 14.0):
        bg_box(B, rng, (-3.12, 0.3, zc), (3.12, 1.0, zc + 0.32), 0.05)
    for i in range(9):
        x = -2.8 + i * 0.7
        bg_box(B, rng, (x - 0.16, 0.2, 18.55), (x + 0.16, 1.0, 19.3), 0.03, cuts=[((x, 0.2 + 0.25, 18.55), (0, -1, -1))])
    bg_box(B, rng, (-3.4, 0.12, 19.3), (3.4, 5.2, 20.55), 0.07)
    for i in range(5):
        if i == 3:
            continue
        x0 = -3.4 + i * 1.44
        cuts = [((x0 + 0.95, 0, 21.5), (0.6, 0, 1))] if i == 1 else []
        bg_box(B, rng, (x0, 0.12, 20.5), (x0 + 0.95, 0.8, 21.75), 0.05, cuts=cuts)
    for s in (-1, 1):
        for y0 in (1.3, 2.9):
            x0, x1 = sorted((s * 3.4, s * 2.8))
            bg_box(B, rng, (x0, y0, 20.5), (x1, y0 + 0.9, 21.75), 0.05)
    for x in (-1.35, 1.35):
        cut.window(win_poly(x, 10.0, 12.6, 0.9, "round"), 0.5, 0.45)
    cut.window(win_poly(0.0, 15.0, 17.2, 1.2, "round"), 0.5, 0.45)
    cut.window(win_poly(0.0, 4.4, 6.2, 0.26, "flat"), 0.5, 0.45)
    cut.window(win_poly(-1.6, 3.2, 4.6, 0.26, "flat"), 0.5, 0.45)
    cut.breakage((3.3, 2.5, 21.2), (1.2, 3.5, 1.3), rng, n=3)
    cut.breakage((-3.6, -0.3, 8.6), (0.5, 1.0, 0.5), rng, n=2)
    return finish_bg(B, cut, rng)


def build_tower_b():
    rng = random.Random(302)
    B = Builder("BG_Tower_B")
    cut = Cutters("BG_Tower_B")
    yc = 3.0
    bg_box(B, rng, (-3.0, 0.0, 0.0), (3.0, 6.0, 7.0), 0.1,
           cuts=[((0, 0.9, 7.0), (0, -1, 1)), ((-3.0 + 0.9, 0, 7.0), (-1, 0, 1)), ((3.0 - 0.9, 0, 7.0), (1, 0, 1))])
    bg_box(B, rng, (-3.25, -0.25, 0.0), (3.25, 6.0, 1.2), 0.08)
    body = bm_lathe([(2.78, 5.6), (2.62, 9.0), (2.55, 17.7)], segs=16, phase=TAU / 32)
    translate(body, (0, yc, 0))
    B.add(body, M["BGStone"], tint=tint(rng))
    for k in range(16):
        a = TAU * k / 16 + TAU / 32
        c = Vector((math.cos(a) * 2.75, yc + math.sin(a) * 2.75, 17.65))
        bm = bm_box((-0.17, -0.25, -0.5), (0.17, 0.25, 0.0))
        bm_cut(bm, (0, 0.25 - 0.3, -0.5), (0, 1, -1))
        rotate(bm, a - math.pi / 2 + math.pi, "Z")
        translate(bm, c)
        B.add(bm, M["BGStone"], tint=tint(rng))
    ring = bm_lathe([(2.98, 17.6), (2.98, 19.1)], segs=16, phase=TAU / 32)
    translate(ring, (0, yc, 0))
    B.add(ring, M["BGStone"], tint=tint(rng))
    for k in range(12):
        if k in (2, 9):
            continue
        a = TAU * k / 12
        bm = bm_box((-0.38, -0.2, 0.0), (0.38, 0.2, 1.0))
        rotate(bm, a + math.pi / 2, "Z")
        translate(bm, (math.cos(a) * 2.8, yc + math.sin(a) * 2.8, 19.05))
        B.add(bm, M["BGStone"], tint=tint(rng))
    roof = bm_lathe([(2.72, 19.3), (1.4, 21.6), (0.1, 24.6)], segs=16, phase=TAU / 32)
    translate(roof, (0, yc, 0))
    B.add(roof, M["BGRoof"], tint=tint(rng))
    B.add(translate(bm_lathe([(0.06, 24.4), (0.06, 25.4), (0.0001, 25.45)], segs=6), (0, yc, 0)), M["BGIron"])
    B.add(translate(bm_box((-0.35, -0.04, 25.0), (0.35, 0.04, 25.08)), (0, yc, 0)), M["BGIron"])
    bx, by = -2.85, yc - 1.4
    for prof, mat in (([(0.1, 11.7), (0.88, 13.2)], M["BGStone"]), ([(0.86, 13.15), (0.86, 15.7)], M["BGStone"]),
                      ([(0.98, 15.6), (0.04, 18.4)], M["BGRoof"])):
        bm = bm_lathe(prof, segs=10)
        translate(bm, (bx, by, 0))
        B.add(bm, mat, tint=tint(rng))
    for k, (rx1, ry1) in enumerate(((1.4, 1.2), (2.0, 0.6))):
        bm = bm_box((-0.06, -0.06, 0), (0.06, 0.06, 2.0))
        rotate(bm, rad(60 - 25 * k), "Y")
        translate(bm, (rx1, yc - 1.2, 21.2 + 0.3 * k))
        B.add(bm, M["BGIron"])
    for a_deg in (-24, 0, 24):
        cut.window(win_poly(0.0, 10.2, 12.2, 0.7, "round"), yc - 2.62, 0.45, rot_z=rad(a_deg), pivot=(0, yc, 0))
    cut.window(win_poly(0.0, 14.2, 15.9, 0.8, "pointed"), yc - 2.55, 0.45)
    cut.window(win_poly(0.0, 2.4, 4.4, 0.3, "flat"), 0.0, 0.45)
    cut.window(win_poly(bx, 13.9, 14.9, 0.22, "flat"), by - 0.86, 0.3)
    cut.breakage((1.5, yc - 1.3, 22.0), (0.9, 1.0, 1.1), rng, n=2)
    cut.breakage((2.9, 0.2, 6.6), (0.6, 0.6, 0.8), rng, n=2)
    return finish_bg(B, cut, rng)


def build_ruins():
    rng = random.Random(303)
    B = Builder("BG_Ruins")
    cut = Cutters("BG_Ruins")
    top = [(10, 6.6), (9.2, 7.4), (8.6, 7.0), (7.8, 8.1), (6.9, 7.6), (6.2, 5.6), (5.4, 5.2), (4.6, 6.3), (3.8, 6.0),
           (3.1, 8.6), (2.2, 9.0), (1.0, 9.4), (-1.5, 9.6), (-3.0, 9.5), (-4.2, 9.95), (-5.6, 9.6), (-6.8, 10.0),
           (-8.2, 9.5), (-9.2, 9.8), (-10, 9.4)]
    # convex vertical strips (unioned by the boolean's self-intersection pass)
    # instead of one concave n-gon, which the exact solver can turn into
    # non-simple faces that triangulate outside the outline
    pts = list(reversed(top))
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        strip = bm_prism_xz([(x0, 0.0), (x1, 0.0), (x1, z1), (x0, z0)], 0.0, 2.2)
        B.add(strip, M["BGStone"], tint=tint(rng))

    def top_at(x):
        for (x1, z1), (x0, z0) in zip(top, top[1:]):
            if x0 <= x <= x1:
                return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
        return 9.0

    for cx in (-6.0, 0.0, 6.0):
        pts = [(cx - 2.0, -1.0), (cx + 2.0, -1.0)] + [(cx + 2.0 * math.cos(a), 4.0 + 2.0 * math.sin(a))
                                                     for a in lin(0, math.pi, 11)]
        bm = bm_prism_xz(pts, -2.0, 4.0)
        b = Builder(f"BG_Ruins_arch{cx}")
        b.add(bm, M["BGStone"])
        cut.brk.append(b)
        voussoirs(cut.post, rng, (cx, 4.0), 2.0, 2.55, -0.22, 0.25, 9, 0.06, key_extra=0.25, jitter_r=0.08, bevel=0.05,
                  segs=1, mat=M["BGStone"], chips=0,
                  skip=lambda i, cx=cx: top_at(cx + 2.3 * math.cos(math.pi * (i + 0.5) / 9)) <
                  4.0 + 2.6 * math.sin(math.pi * (i + 0.5) / 9) + 0.1)
    for cx in (-9.2, -3.0, 3.0, 9.2):
        bg_box(B, rng, (cx - 0.55, -0.75, 0.0), (cx + 0.55, 0.3, 3.7), 0.06, cuts=[((cx, -0.75 + 0.6, 3.7), (0, -1, 1))])
    for (x0, x1) in ((-10.0, 3.6), (7.4, 9.4)):
        bg_box(B, rng, (x0, -0.28, 6.9), (x1, 0.3, 7.25), 0.04)
    for k, (cx, cz) in enumerate(((-6.0, 5.95), (0.0, 5.95))):
        z = cz
        n = 10 if k == 0 else 7
        for i in range(n):
            ln = chain_link(segs=4, path_pts=8)
            scale(ln, 1.8)
            if i % 2:
                rotate(ln, math.pi / 2, "Z")
            translate(ln, (cx, 1.0, z - L_IN * 0.9))
            cut.post.add(ln, M["BGIron"], smooth=True)
            z -= L_IN * 1.8
        if k == 1:
            cz2 = z - 0.1
            for j in range(6):
                a = TAU * j / 6
                pts = [(cx + r * math.cos(a), 1.0 + r * math.sin(a), cz2 + dz) for r, dz in
                       ((0.1, 0.0), (0.35, -0.2), (0.45, -0.5), (0.45, -1.1), (0.38, -1.3))]
                cut.post.add(bm_tube(pts, 0.035, segs=4), M["BGIron"], smooth=True)
            for dz, r in ((-0.5, 0.46), (-1.1, 0.46)):
                cut.post.add(translate(bm_lathe([(r, dz - 0.04), (r + 0.03, dz - 0.04), (r + 0.03, dz + 0.04),
                                                 (r, dz + 0.04), (r, dz - 0.04)], segs=12, cap_top=False,
                                                cap_bottom=False), (cx, 1.0, cz2)), M["BGIron"])
            cut.post.add(translate(bm_lathe([(0.4, -1.32), (0.4, -1.26)], segs=12), (cx, 1.0, cz2)), M["BGIron"])
    for k in range(7):
        c = Vector((rng.uniform(3.8, 7.6), rng.uniform(-1.2, 0.2), rng.uniform(0.0, 0.5)))
        s = rng.uniform(0.4, 0.8)
        pts = [c + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 1))) * s for _ in range(10)]
        B.add(eh.bm_hull(pts), M["BGStone"], tint=tint(rng))
    for x, z0 in ((-3.0, 7.6), (3.0, 7.0), (-8.3, 7.4)):
        cut.window(win_poly(x, z0, z0 + 1.1, 0.32, "pointed"), 0.0, 0.4)
    return finish_bg(B, cut, rng)


def build_spires():
    rng = random.Random(304)
    B = Builder("BG_Spires")
    cut = Cutters("BG_Spires")
    bg_box(B, rng, (-6.0, 0.0, 0.0), (6.0, 4.0, 3.6), 0.06)
    B.add(eh.bm_hull([(-6, 0, 3.5), (6, 0, 3.5), (-6, 4, 3.5), (6, 4, 3.5), (-6, 2, 5.6), (6, 2, 5.6)]), M["BGRoof"],
          tint=tint(rng))
    for (cx, h, w) in ((-4.6, 10.0, 1.35), (-2.3, 12.5, 1.6), (0.0, 16.0, 2.2), (2.6, 13.0, 1.6), (4.8, 9.2, 1.3)):
        cy = 0.7 + w / 2
        zs = h * 0.55
        bg_box(B, rng, (cx - w / 2, cy - w / 2, 0.0), (cx + w / 2, cy + w / 2, zs), 0.05)
        for sx in (-1, 1):
            bg_box(B, rng, (cx + sx * w / 2 - 0.18, cy - w / 2 - 0.35, 0.0),
                   (cx + sx * w / 2 + 0.18, cy - w / 2 + 0.3, zs * 0.7), 0.04,
                   cuts=[((cx, cy - w / 2 - 0.35 + 0.35, zs * 0.7), (0, -1, 1.4))])
            for sy in (-1, 1):
                px, py = cx + sx * (w / 2 - 0.12), cy + sy * (w / 2 - 0.12)
                B.add(eh.bm_hull([(px - 0.14, py - 0.14, zs), (px + 0.14, py - 0.14, zs), (px - 0.14, py + 0.14, zs),
                                  (px + 0.14, py + 0.14, zs), (px, py, zs + 1.3)]), M["BGStone"], tint=tint(rng))
        drum = bm_lathe([(w * 0.44, zs - 0.05), (w * 0.44, h * 0.68)], segs=8, phase=TAU / 16)
        translate(drum, (cx, cy, 0))
        B.add(drum, M["BGStone"], tint=tint(rng))
        cone = bm_lathe([(w * 0.5, h * 0.68), (0.05, h)], segs=8, phase=TAU / 16)
        translate(cone, (cx, cy, 0))
        B.add(cone, M["BGRoof"], tint=tint(rng))
        for k in range(4):
            a = TAU * k / 4 - math.pi / 2
            gx, gy = cx + math.cos(a) * w * 0.42, cy + math.sin(a) * w * 0.42
            g = eh.bm_hull([(-0.25, -0.12, 0), (0.25, -0.12, 0), (-0.25, 0.3, 0), (0.25, 0.3, 0), (0, -0.12, 0.7),
                            (0, 0.3, 0.7)])
            rotate(g, a + math.pi / 2, "Z")
            translate(g, (gx, gy, h * 0.68))
            B.add(g, M["BGRoof"], tint=tint(rng))
        B.add(translate(bm_lathe([(0.035, h - 0.05), (0.035, h + 0.7)], segs=5), (cx, cy, 0)), M["BGIron"])
        B.add(bm_box((cx - 0.18, cy - 0.03, h + 0.42), (cx + 0.18, cy + 0.03, h + 0.48)), M["BGIron"])
        nwin = 1 if (w > 2 or w < 1.5) else 2
        for i in range(nwin):
            z0 = zs * (0.35 + 0.33 * i)
            cut.window(win_poly(cx, z0, z0 + 1.1 + 0.3 * (w > 2), 0.3 if w < 2 else 0.42, "pointed"),
                       cy - w / 2, 0.35)
    rose = [(0.55 * math.cos(a), 6.6 + 0.55 * math.sin(a)) for a in lin(0, TAU, 13)[:-1]]
    cut.window(rose, 0.7, 0.35)
    for x in (-5.2, -3.4, -1.1, 1.2, 3.6, 5.4):
        cut.window(win_poly(x, 1.0, 2.2, 0.32, "pointed"), 0.0, 0.3)
    cut.breakage((4.8, 1.4, 9.2), (0.6, 0.8, 0.8), rng, n=2)
    return finish_bg(B, cut, rng)


# ---------------------------------------------------------------------------
# Module registry
# ---------------------------------------------------------------------------

ENV_MODULES = [
    ("ENV_Stone_A", lambda: build_tile("ENV_Stone_A"), 1.6, 1500,
     "Foreground 1x1 fill block (collidable). Pivot bottom-left on gameplay plane; top flat at y=1."),
    ("ENV_Stone_B", lambda: build_tile("ENV_Stone_B"), 1.6, 1500, "Foreground 1x1 fill block variant B."),
    ("ENV_Stone_C", lambda: build_tile("ENV_Stone_C"), 1.6, 1500, "Foreground 1x1 fill block variant C."),
    ("ENV_StoneTop_A", lambda: build_tile("ENV_StoneTop_A"), 1.6, 1500,
     "Walkable surface tile with mossy lip (moss <= +0.055 above y=1, overhang <= 0.08)."),
    ("ENV_StoneTop_B", lambda: build_tile("ENV_StoneTop_B"), 1.6, 1500, "Walkable surface tile variant B."),
    ("ENV_StoneEdge_L", lambda: build_tile("ENV_StoneEdge_L"), 1.6, 1500,
     "Left end of a platform: rounded outer corner, moss wraps over the -X side."),
    ("ENV_StoneEdge_R", build_edge_r, 1.6, 1500, "Right end of a platform (mirror of Edge_L)."),
    ("ENV_WoodPlatform", build_wood_platform, 1.5, 1500,
     "One-way platform, 1 m segment, deck top at y=1 (deck y 0.82-1.0), strut below."),
    ("ENV_Pillar", build_pillar, 0.9, 6000, "Midground stone column 5 m, pivot bottom-center, front at z=0."),
    ("ENV_Arch", build_arch, 0.85, 6000, "Midground archway, 4 m inner span, 5.5 m tall, vines."),
    ("ENV_CellDoor", build_cell_door, 1.1, 6000,
     "Prison cell door in stone frame (2.4x3.2 m), door ajar 6 deg, dark recess to z=+0.86."),
    ("ENV_BackWall", build_back_wall, 0.75, 6000,
     "Background wall panel 4x4 m, tiles seamlessly on a 4 m grid. Pivot bottom-left, front at z=0."),
    ("ENV_Torch", build_torch, 2.0, 4000,
     "Wall sconce; pivot = wall attachment (bottom of plate), back at z=0, sticks out to -z. Coals emissive."),
    ("ENV_Grate", build_grate, 1.1, 4000, "High wall window grate 2x2 m with recess, pivot bottom-center."),
    ("ENV_Chain", build_chain, 1.6, 4000, "3 m hanging chain + ceiling plate + hook; pivot at top attachment."),
    ("ENV_ChainLink", build_chain_link, 1.6, 400,
     "Single chain link, pivot at its top inner contact. Link pitch 0.146 m (next pivot at y=-0.146), "
     "alternate 90 deg about Y."),
    ("ENV_Cage", build_cage, 1.3, 4000, "Hanging gibbet cage with slumped skeleton; pivot at top ring."),
    ("ENV_Barrel", build_barrel, 1.3, 4000, "Barrel prop, pivot bottom-center, front at z=0."),
    ("ENV_Crate", build_crate, 1.3, 4000, "Crate prop 0.9 m, pivot bottom-center, front at z=0."),
    ("ENV_BonePile", build_bone_pile, 1.3, 4000, "Heap of skulls and bones, pivot bottom-center, front at z=0."),
    ("ENV_Banner", build_banner, 1.2, 4000, "Tattered banner 1x2.5 m on a rod; pivot at rod top-center."),
]

BG_MODULES = [
    ("BG_Tower_A", build_tower_a, 1.0, 10000, "Background castle tower (7x21.8 m), teal-glow window mask."),
    ("BG_Tower_B", build_tower_b, 1.0, 10000, "Background round tower with broken roof and bartizan (25 m)."),
    ("BG_Ruins", build_ruins, 1.0, 10000, "Background ruined arcade 20x10 m with hanging chains and cage."),
    ("BG_Spires", build_spires, 1.0, 10000, "Far silhouette cluster of gothic spires 12x16 m (layer z=10)."),
]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build_all(specs):
    objs = []
    for name, fn, _w, budget, _u in specs:
        t0 = time.time()
        res = fn()
        obj = res if isinstance(res, bpy.types.Object) else res.build()
        eh.triangulate_ngons(obj)
        obj.name = name
        obj.data.name = name
        tris = eh.tri_count(obj)
        flag = "" if tris <= budget else f"  !!! over budget {budget}"
        print(f"[env] built {name:18s} tris={tris:6d} mats={len(obj.data.materials)} ({time.time() - t0:.1f}s){flag}")
        objs.append(obj)
    return objs


def check_tiles(objs):
    report = {}
    for o in objs:
        if not (o.name.startswith("ENV_Stone")):
            continue
        vs = [v.co for v in o.data.vertices]
        walk = [v for v in vs if 0.0 <= v.x <= 1.0 and -0.9 <= v.y <= 1.6]
        report[o.name] = dict(max_z=round(max(v.z for v in walk), 4), min_y=round(min(v.y for v in vs), 4),
                              min_x=round(min(v.x for v in vs), 4), max_x=round(max(v.x for v in vs), 4),
                              min_z=round(min(v.z for v in vs), 4))
        print(f"[env] tile check {o.name}: {report[o.name]}")
    return report


def spread(objs, y=0.0, gap=3.0):
    x = 0.0
    for o in objs:
        xs = [v.co.x for v in o.data.vertices]
        lo, hi = min(xs), max(xs)
        o.location = (x - lo, y, 0.0)
        x += (hi - lo) + gap


def set_ao_distance(d):
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("BakeWorld")
    scene.world = world
    world.light_settings.distance = d


def bake_kit(objs, others, prefix, size, ao_dist):
    for o in others:
        o.hide_render = True
    for o in objs:
        o.hide_render = False
    set_ao_distance(ao_dist)
    t0 = time.time()
    paths = eh.bake_atlas(objs, TEX_DIR, prefix, size)
    print(f"[env] baked {prefix} {size}px in {time.time() - t0:.1f}s")
    for o in others:
        o.hide_render = False
    return paths


def assign_kit(objs, mat):
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


def export_all(objs, specs, atlas, manifest):
    usage = {s[0]: s[4] for s in specs}
    for o in objs:
        o.location = (0.0, 0.0, 0.0)
        kids = [c for c in o.children]
        path = MESH_DIR / f"{o.name}.fbx"
        dc.export_fbx(path, [o] + kids, static=True)
        lo, hi = bounds(o)
        entry = dict(name=o.name, fbx=str(path.relative_to(dc.PROJECT_ROOT)), atlas=atlas,
                     unity_bounds_min=to_unity(lo), unity_bounds_max=to_unity(hi),
                     sockets={c.name: to_unity(c.location) for c in kids}, tris=eh.tri_count(o),
                     usage=usage.get(o.name, ""))
        manifest["modules"].append(entry)


def preview_modules(objs, tag, engine="BLENDER_EEVEE"):
    paths = []
    for o in bpy.context.scene.objects:
        o.hide_render = True
    for o in objs:
        o.hide_render = False
        p = dc.preview_render(str(OUT / f"mod_{o.name}"), [o], views=("three_quarter",), res=384, engine=engine)
        paths.extend(p)
        o.hide_render = True
    for o in bpy.context.scene.objects:
        o.hide_render = False
    sheet = eh.compose_sheet(paths, OUT / f"sheet_{tag}_three_quarter.png", cols=6 if len(paths) > 8 else 4,
                             cell=384)
    print(f"[env] contact sheet {sheet}  order: {[o.name for o in objs]}")
    return sheet


def chunk_scene(by):
    """Place linked copies into a small level chunk; returns created objects."""
    made = []

    def put(name, loc, rz=0.0):
        src = by[name]
        o = src.copy()
        o.name = name + "_chunk"
        dc.link(o)
        o.location = loc
        o.rotation_euler = (0, 0, rz)
        made.append(o)
        return o

    base = ["ENV_Stone_A", "ENV_Stone_B", "ENV_Stone_C"]
    tops = ["ENV_StoneTop_A", "ENV_StoneTop_B"]
    for i in range(12):
        put(base[(i * 2 + i // 3) % 3], (i, 0, 0))
        if i == 0:
            put("ENV_StoneEdge_L", (i, 0, 1))
        elif i == 11:
            put("ENV_StoneEdge_R", (i, 0, 1))
        else:
            put(tops[(i * 7 // 3) % 2], (i, 0, 1))
    for i in range(3):
        put("ENV_WoodPlatform", (7 + i, 0, 3.5))
    for x in (-2, 2, 6, 10):
        for z in (0, 4):
            deep = (x == 2)
            put("ENV_BackWall", (x, 2.65 if deep else 2.0, z))
    put("ENV_CellDoor", (3.6, 1.8, 2.0))
    put("ENV_Arch", (8.5, 1.0, 2.0))
    put("ENV_Pillar", (0.9, 0.55, 2.0))
    put("ENV_Torch", (5.15, 2.0, 3.6))
    put("ENV_Torch", (2.05, 2.0, 3.6))
    put("ENV_Chain", (9.7, 1.2, 8.0))
    put("ENV_Banner", (12.6, 1.95, 7.0))
    put("ENV_Barrel", (5.6, 0.25, 2.0))
    put("ENV_Crate", (6.45, 0.3, 2.0))
    put("ENV_BonePile", (10.6, 0.15, 2.0))
    return made


def render_previews(env_objs, bg_objs, engine="BLENDER_EEVEE"):
    by = {o.name: o for o in env_objs + bg_objs}
    preview_modules(env_objs, "ENV", engine)
    preview_modules(bg_objs, "BG", engine)
    for o in bpy.context.scene.objects:
        o.hide_render = True
    made = chunk_scene(by)
    for o in made:
        o.hide_render = False
    if engine == "BLENDER_EEVEE":
        dc.preview_render(str(OUT / "chunk"), made, views=("front",), res=1024)
    center, width = Vector((5.75, 0.0, 4.1)), 15.5
    eh.render_framed(OUT / "chunk_front_wide.png", center, width, (0, -1, 0.05), res=(1600, 900), engine=engine)
    eh.render_framed(OUT / "chunk_game_hi.png", center, width, (0.25, -1, 0.12), res=(1280, 720), engine=engine)
    eh.pixelate(OUT / "chunk_game_hi.png", OUT / "chunk_game_pixel.png", 2)
    for o in made:
        bpy.data.objects.remove(o, do_unlink=True)
    # background lineup
    bgs = []
    for k, (n, x) in enumerate((("BG_Spires", -16.0), ("BG_Tower_A", -4.0), ("BG_Ruins", 10.0), ("BG_Tower_B", 25.0))):
        o = by[n].copy()
        dc.link(o)
        o.hide_render = False
        o.location = (x, 0, 0)
        bgs.append(o)
    eh.render_framed(OUT / "bg_lineup.png", Vector((5.0, 0, 12.5)), 50.0, (0, -1, 0.05), res=(1600, 900),
                     engine=engine)
    for o in bgs:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in bpy.context.scene.objects:
        o.hide_render = False


def atlas_sheet(paths_env, paths_bg):
    order = [paths_env[k] for k in ("albedo", "normal", "orm", "emission")] + \
            [paths_bg[k] for k in ("albedo", "normal", "orm", "emission")]
    eh.compose_sheet([str(p) for p in order], OUT / "atlas_sheet.png", cols=4, cell=768)


def main():
    t_start = time.time()
    dc.ensure_dir(OUT)
    dc.reset_scene()
    make_materials()
    only = [a.split("=", 1)[1].split(",") for a in ARGS if a.startswith("--only=")]
    env_specs = [s for s in ENV_MODULES if not only or s[0] in only[0]]
    bg_specs = [s for s in BG_MODULES if not only or s[0] in only[0]]
    env_objs = build_all(env_specs)
    bg_objs = build_all(bg_specs)
    tile_report = check_tiles(env_objs)
    if "--build-only" in ARGS:
        scene = bpy.context.scene
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_cavity = True
        scene.display.shading.cavity_type = "BOTH"
        if "--chunk" in ARGS:
            render_previews(env_objs, bg_objs, engine="BLENDER_WORKBENCH")
        else:
            preview_modules(env_objs, "ENV_wb", "BLENDER_WORKBENCH")
            if bg_objs:
                preview_modules(bg_objs, "BG_wb", "BLENDER_WORKBENCH")
        return

    t0 = time.time()
    dens_env = eh.atlas_uv(env_objs, {s[0]: s[2] for s in ENV_MODULES}, margin=0.002)
    dens_bg = eh.atlas_uv(bg_objs, {s[0]: s[2] for s in BG_MODULES}, margin=0.0025)
    print(f"[env] UV atlases packed in {time.time() - t0:.1f}s")
    for k, v in dens_env.items():
        print(f"[env]   texel density (front faces) {k:18s} {v * ENV_SIZE:7.1f} px/m")
    for k, v in dens_bg.items():
        print(f"[env]   texel density {k:18s} {v * BG_SIZE:7.1f} px/m")

    spread(env_objs, y=0.0, gap=3.0)
    spread(bg_objs, y=80.0, gap=10.0)
    paths_env = bake_kit(env_objs, bg_objs, "ENV_Kit", ENV_SIZE, 0.35)
    paths_bg = bake_kit(bg_objs, env_objs, "BG_Kit", BG_SIZE, 2.0)

    kit_env = dc.baked_material("M_ENV_Kit", paths_env, emission_strength=5.0)
    kit_bg = dc.baked_material("M_BG_Kit", paths_bg, emission_strength=3.0)
    assign_kit(env_objs, kit_env)
    assign_kit(bg_objs, kit_bg)

    manifest = {"generator": "Tools/Blender/build_environment.py", "unity_axes": "Unity (x,y,z) = Blender (x,z,y)",
                "atlases": {"ENV_Kit": {k: str(Path(v).relative_to(dc.PROJECT_ROOT)) for k, v in paths_env.items()},
                            "BG_Kit": {k: str(Path(v).relative_to(dc.PROJECT_ROOT)) for k, v in paths_bg.items()}},
                "materials": {"ENV_Kit": "M_ENV_Kit", "BG_Kit": "M_BG_Kit"},
                "emission_colors": {"ENV_Torch coals": "#FF7A1A", "BG windows": "#3FE0D0"},
                "tile_checks_blender": tile_report, "modules": []}
    render_previews(env_objs, bg_objs)
    atlas_sheet(paths_env, paths_bg)
    export_all(env_objs, ENV_MODULES, "ENV_Kit", manifest)
    export_all(bg_objs, BG_MODULES, "BG_Kit", manifest)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"[env] manifest {MANIFEST}")
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "env_kit.blend"), compress=True)
    except RuntimeError as exc:
        print("[env] blend save failed", exc)
    print(f"[env] DONE in {time.time() - t_start:.1f}s")


def verify():
    """Fresh scene: re-import every FBX and compare to the manifest."""
    dc.reset_scene()
    man = json.loads(MANIFEST.read_text())
    bad = 0
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
        ok = err < 2e-3 and max(abs(c) for c in loc) < 1e-4 and len(mats) == 1
        bad += not ok
        print(f"[verify] {m['name']:18s} ok={ok} origin={loc} bounds_err={err:.5f} mats={mats} "
              f"unity_min={ulo} unity_max={uhi} sockets={sock}")
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    print(f"[verify] {len(man['modules']) - bad}/{len(man['modules'])} modules OK")


if __name__ == "__main__":
    if "--verify" in ARGS:
        verify()
    else:
        main()
