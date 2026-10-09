"""Shared gameplay props + vendor NPCs, sharing one 2048 atlas "Props".

Teleporter (Chronometer Gate), Chest (Chest_Base + Chest_Lid), Pedestal, Coin,
GoldPile, Fountain (+ Fountain_Liquid), LoreTablet, ExitDoor (frame +
Door_Left / Door_Right + ExitDoor_Light), MerchantStall, Merchant and
Collector ("the Horologist").

Conventions (Tools/PIPELINE.md): pivot at the bottom centre on the floor
(z = 0), the face the player sees points to Blender -Y, Blender (x, y, z) ==
Unity (x, z, y).  Socket EMPTYs are exported in the same FBX.  Uses the shared
kit pipeline from build_arsenal.py (UV atlas -> pairwise high-poly bake ->
baked material -> export -> manifest -> previews).

Run (headless only, never in the live Blender):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P Tools/Blender/build_props.py
Options after "--": --fast, --build-only, --only=A,B, --res=N, --verify (see build_arsenal.py)
"""

import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_arsenal as ba  # noqa: E402
import dc_common as dc  # noqa: E402
import env_helpers as eh  # noqa: E402
from build_arsenal import (TAU, X, Y, Z, Asset, MatEdit, aim, arc_pts, blob, box, catmull, cbox, cone,  # noqa: E402
                           frames, glyph_image, jitter_bm, lathe, lerp, loft, prism_xz, ridged, rot, rune_strokes,
                           smooth01, sweep, thick_sheet, torus, translate, tube)

OUT_DIR = dc.ART_ROOT / "Props"
TEX_DIR = OUT_DIR / "Textures"
MANIFEST = OUT_DIR / "props_manifest.json"
PREV = dc.OUT_ROOT / "props"
GLYPHS = PREV / "glyphs"

ALL_CORNERS = [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
TABLET_RECT = (-0.3, 0.34, 0.6, 0.78)
SIGN_RECT = (-0.84, 1.93, 0.48, 0.24)


# ---------------------------------------------------------------------------
# Extra shape helpers
# ---------------------------------------------------------------------------

def stone(lo, hi, rng, chips=2, bev=0.03, corners=None, chip=(0.03, 0.08), crack=None):
    return eh.block(lo, hi, rng, chips=chips, chip_size=chip, corners=corners or ALL_CORNERS, bevel=bev, segs=1,
                    crack=crack)


def revolve_loop(prof, segs, axis=(0, -1, 0), center=(0, 0, 0), phase=0.0, scale_xy=(1.0, 1.0)):
    """Revolve a closed (r, f) cross-section loop around local Z (aimed at axis)."""
    bm = bmesh.new()
    rings = [[bm.verts.new((math.cos(phase + TAU * i / segs) * r * scale_xy[0],
                            math.sin(phase + TAU * i / segs) * r * scale_xy[1], f)) for i in range(segs)]
             for r, f in prof]
    n = len(rings)
    for k in range(n):
        k2 = (k + 1) % n
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((rings[k][i], rings[k][j], rings[k2][j], rings[k2][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return aim(bm, axis, center)


def gear(center, teeth, r_root, r_tip, r_in, y0, y1, phase=0.0, spokes=4, hub=0.06):
    """Toothed annulus in the X-Z plane, thickness along Y, plus spokes."""
    cx, cz = center[0], center[2]
    pts = []
    for k in range(teeth):
        a = phase + TAU * k / teeth
        da = TAU / teeth
        for frac, r in ((0.0, r_root), (0.17, r_tip), (0.5, r_tip), (0.67, r_root)):
            pts.append((a + frac * da, r))
    bm = bmesh.new()

    def V(a, r, y):
        return bm.verts.new((cx + math.cos(a) * r, y, cz + math.sin(a) * r))

    of = [V(a, r, y0) for a, r in pts]
    ob = [V(a, r, y1) for a, r in pts]
    inf = [V(a, r_in, y0) for a, _ in pts]
    inb = [V(a, r_in, y1) for a, _ in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((of[i], of[j], inf[j], inf[i]))
        bm.faces.new((ob[i], inb[i], inb[j], ob[j]))
        bm.faces.new((of[i], ob[i], ob[j], of[j]))
        bm.faces.new((inf[i], inf[j], inb[j], inb[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    parts = [bm]
    ym = (y0 + y1) * 0.5
    th = abs(y1 - y0) * 0.7
    for k in range(spokes):
        a = phase + TAU * (k + 0.5) / spokes
        sp = cbox((0, 0, (r_in + hub) * 0.5), (r_in * 0.16, th, r_in - hub + 0.02))
        rot(sp, math.pi / 2 - a, "Y")
        parts.append(translate(sp, (cx, ym, cz)))
    parts.append(lathe([(hub, -th * 0.7), (hub, th * 0.7)], segs=10, axis=(0, -1, 0), center=(cx, ym, cz)))
    return parts


def thick_tube(rings, th):
    """Closed ring loops (open at both ends) -> cloth shell with thickness."""
    bm = bmesh.new()
    outs, ins = [], []
    for ring in rings:
        c = sum((Vector(p) for p in ring), Vector()) / len(ring)
        o, i = [], []
        for p in ring:
            p = Vector(p)
            n = (p - c).normalized()
            o.append(bm.verts.new(p + n * th * 0.5))
            i.append(bm.verts.new(p - n * th * 0.5))
        outs.append(o)
        ins.append(i)
    m = len(rings[0])
    for k in range(len(rings) - 1):
        for a in range(m):
            b = (a + 1) % m
            bm.faces.new((outs[k][a], outs[k][b], outs[k + 1][b], outs[k + 1][a]))
            bm.faces.new((ins[k][a], ins[k + 1][a], ins[k + 1][b], ins[k][b]))
    for k in (0, len(rings) - 1):
        for a in range(m):
            b = (a + 1) % m
            bm.faces.new((outs[k][a], ins[k][a], ins[k][b], outs[k][b]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def ring_pts(center, rx, ry, n=12, phase=0.0, fn=None):
    c = Vector(center)
    out = []
    for i in range(n):
        a = phase + TAU * i / n
        p = c + Vector((math.cos(a) * rx, math.sin(a) * ry, 0.0))
        out.append(fn(p, a) if fn else p)
    return out


def oriented_ring(center, normal, rx, ry, n=10, side_hint=X):
    nrm = Vector(normal).normalized()
    s = (Vector(side_hint) - nrm * Vector(side_hint).dot(nrm)).normalized()
    u = nrm.cross(s)
    c = Vector(center)
    return [c + s * math.cos(TAU * i / n) * rx + u * math.sin(TAU * i / n) * ry for i in range(n)]


def place(bm, loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0):
    if rx:
        rot(bm, rx, "X")
    if ry:
        rot(bm, ry, "Y")
    if rz:
        rot(bm, rz, "Z")
    return translate(bm, loc)


# ---------------------------------------------------------------------------
# Glyph masks
# ---------------------------------------------------------------------------

def tablet_glyphs():
    rng = random.Random(77)
    x0, z0, w, h = TABLET_RECT
    s = []
    c = (w * 0.5, h - 0.075)
    s.append(dict(pts=arc_pts(c[0], c[1], 0.058, 0, TAU, 40), w=0.013))
    s.append(dict(pts=arc_pts(c[0], c[1] - 0.06, 0.075, 0.75, math.pi - 0.75, 16), w=0.012))
    s.append(dict(pts=arc_pts(c[0], c[1] + 0.06, 0.075, math.pi + 0.75, TAU - 0.75, 16), w=0.012))
    s.append(dict(pts=arc_pts(c[0], c[1], 0.018, 0, TAU, 16), w=0.013))
    s.append(dict(pts=[(0.03, h - 0.17), (w - 0.03, h - 0.17)], w=0.01))
    y = h - 0.27
    row = 0
    while y > 0.02:
        x = 0.035 + (0.025 if row % 2 else 0.0)
        while x < w - 0.08:
            cw = rng.uniform(0.04, 0.056)
            if rng.random() < 0.12:
                x += cw * 0.6
                continue
            s += rune_strokes(rng, x, y, cw, 0.072, 0.0115, wobble=0.04)
            x += cw + 0.018
        y -= 0.108
        row += 1
    return glyph_image("Tablet_Glyphs", w, h, s, GLYPHS, max_px=1024)


def sign_glyph():
    x0, z0, w, h = SIGN_RECT
    s = []
    cx, cy = 0.13, h * 0.5
    s.append(dict(pts=arc_pts(cx, cy - 0.02, 0.055, math.radians(115), math.radians(425), 30), w=0.014))
    s.append(dict(pts=[(cx - 0.022, cy + 0.03), (cx - 0.022, cy + 0.075), (cx + 0.022, cy + 0.075),
                       (cx + 0.022, cy + 0.03)], w=0.012))
    s.append(dict(pts=[(cx - 0.03, cy + 0.085), (cx + 0.03, cy + 0.085)], w=0.012))
    s.append(dict(pts=[(cx - 0.04, cy - 0.03), (cx + 0.04, cy - 0.03)], w=0.009))
    for k, x in enumerate((0.27, 0.36)):
        s.append(dict(pts=arc_pts(x, cy, 0.035, 0, TAU, 24), w=0.012))
        s.append(dict(pts=[(x, cy - 0.02), (x, cy + 0.02)], w=0.01))
    s.append(dict(pts=[(0.02, 0.025), (w - 0.02, 0.025), (w - 0.02, h - 0.025), (0.02, h - 0.025), (0.02, 0.025)],
                  w=0.008))
    return glyph_image("Stall_Sign", w, h, s, GLYPHS, max_px=512)


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def stone_mat(name, base="#4C5C68", dark="#252F39", light="#768894", moss=0.0, scale=1.0):
    m = ba.make_mat(name, base, dark=dark, light=light, rough=0.86, noise_scale=2.4 / scale, noise_amt=0.6,
                         edge_wear="#B9C6CE", edge_wear_amt=0.8, cavity_dirt=0.8, bump_scale=9.0 / scale,
                         bump_strength=0.35, bevel_radius=0.01 * scale)
    eh.enhance(m, blotch=("#4C6A2E", 2.0 / scale, moss) if moss else None, edge_hex="#A4B4BE", edge_amt=0.75,
               edge_radius=0.025 * scale, top_hex="#8E9EA8", top_amt=0.25, bottom_amt=0.35, cavity_amt=0.75,
               cavity_dist=0.12 * scale)
    return m


def cloth(name, base, dark, light, **kw):
    kw.setdefault("edge_r", 0.012)
    kw.setdefault("weave", 90.0)
    return ba.cloth_mat(name, base, dark, light, **kw)


def props_materials():
    M = {}
    M["stone"] = stone_mat("P_Stone")
    M["stone_moss"] = stone_mat("P_StoneMoss", base="#58676E", moss=0.22)
    M["brass"] = ba.brass_mat("P_Brass", edge_r=0.012, patina=0.22, scale=3.0)
    M["iron"] = ba.iron_mat("P_Iron", rust=0.4, edge_r=0.006, scale=3.0, base="#3A4149", edge=("#8C969E", 0.55))
    M["wood_v"] = ba.wood_mat("P_WoodV", "#6E4628", "#2E1A0D", "#A0703F", grain=0.1, edge_r=0.012, scale=2.5)
    M["wood_h"] = ba.wood_mat("P_WoodH", "#73492A", "#2E1A0D", "#A8763F", grain=0.1, edge_r=0.012, axis="x",
                              scale=2.5)
    M["wood_dark"] = ba.wood_mat("P_WoodDark", "#4A2E1C", "#1A0E07", "#7A5234", grain=0.1, edge_r=0.012, scale=2.5)

    m = ba.make_mat("P_Glow", "#CFF6FF", dark="#9AE6F6", light="#FFFFFF", rough=0.3, noise_scale=8,
                         noise_amt=0.6, bevel_radius=0.003)
    E = MatEdit(m)
    E.emit(E.rng(E.noise(6.0, 3.0, 0.6), 0.3, 0.7, 0.8, 1.0))
    M["glow"] = m

    m = ba.make_mat("P_DoorLight", "#FFE6B0", dark="#FFC870", light="#FFFFFF", rough=0.5, noise_scale=3,
                         noise_amt=0.5, bevel_radius=0.003)
    E = MatEdit(m)
    core = E.rng(E.m("ABSOLUTE", E.x), 0.9, 0.0, 0.65, 1.0, smooth=True)
    E.emit(E.m("MULTIPLY", core, E.rng(E.noise(4.0, 2.0, 0.5), 0.3, 0.7, 0.85, 1.0)))
    M["door_light"] = m

    m = ba.make_mat("P_LockGlow", "#E6D6FF", dark="#B8A0F0", light="#FFFFFF", rough=0.3, noise_scale=40,
                         noise_amt=0.4, bevel_radius=0.002)
    MatEdit(m).emit(1.0)
    M["lock_glow"] = m

    m = ba.make_mat("P_Lantern", "#FFD98A", dark="#FFB040", light="#FFF6D8", rough=0.25, noise_scale=30,
                         noise_amt=0.5, bevel_radius=0.002)
    E = MatEdit(m)
    E.emit(E.rng(E.noise(14.0, 2.0, 0.5), 0.3, 0.7, 0.85, 1.0))
    M["lantern"] = m

    m = ba.make_mat("P_Blood", "#B8142A", dark="#5E0612", light="#FF4A5A", rough=0.08, rough_var=0.03,
                         noise_scale=5, noise_amt=0.7, bump_scale=14, bump_strength=0.15, bevel_radius=0.004)
    E = MatEdit(m)
    rip = E.m("SINE", E.m("MULTIPLY", E.vlen(E.vec(E.x, E.m("ADD", E.y, 0.11), 0.0)), 70.0))
    rip = E.m("MULTIPLY", E.rng(rip, 0.6, 1.0), E.rng(E.noise(3.0), 0.35, 0.6))
    E.albedo("#FF7A84", E.m("MULTIPLY", rip, 0.5))
    E.bump(rip, 0.25)
    E.emit(E.m("ADD", E.m("MULTIPLY", rip, 0.3), E.rng(E.noise(5.0, 3.0, 0.6), 0.3, 0.7, 0.65, 0.85)))
    M["blood"] = m

    m = ba.make_mat("P_Gold", "#E2A21C", dark="#9A5C08", light="#FFD552", metal=0.65, rough=0.32, noise_scale=6,
                         noise_amt=0.45, edge_wear="#FFF0A8", edge_wear_amt=0.8, cavity_dirt=0.9, bump_scale=40,
                         bump_strength=0.08, bevel_radius=0.002)
    eh.enhance(m, edge_hex="#FFEFA0", edge_amt=0.6, edge_radius=0.002, top_hex="#FFE070", top_amt=0.2,
               cavity_amt=0.8, cavity_dist=0.012, cavity_hex="#5A3404")
    M["gold"] = m
    m = ba.make_mat("P_GoldHeap", "#D89A1E", dark="#7A4608", light="#FFD552", metal=0.6, rough=0.36,
                         noise_scale=8, noise_amt=0.6, edge_wear="#FFF6C8", edge_wear_amt=1.0, cavity_dirt=0.9,
                         bump_scale=60, bump_strength=0.15, bevel_radius=0.004)
    E = MatEdit(m)
    coins = E.voronoi(26.0)
    E.bump(E.rng(coins, 0.32, 0.18), 0.5)
    E.albedo("#5A3606", E.m("MULTIPLY", E.rng(coins, 0.42, 0.5), 0.6))
    eh.enhance(m, edge_hex="#FFF6C8", edge_amt=0.8, edge_radius=0.006, top_hex="#FFF0A0", top_amt=0.3,
               cavity_amt=0.8, cavity_dist=0.03, cavity_hex="#4A2A04")
    M["gold_heap"] = m
    m = ba.make_mat("P_Gem", "#C0142C", dark="#5A0410", light="#FF6070", rough=0.1, noise_scale=12,
                         noise_amt=0.8, bevel_radius=0.002)
    eh.enhance(m, edge_hex="#FFD0D8", edge_amt=1.0, edge_radius=0.004)
    M["gem"] = m

    M["velvet"] = cloth("P_Velvet", "#7A1030", "#36040F", "#C03656", edge_r=0.012)
    M["gold_thread"] = cloth("P_GoldThread", "#D8A23A", "#7A520E", "#FFE08A", edge_r=0.004, weave=300.0)
    M["canopy"] = cloth("P_Canopy", "#8E1E22", "#4A0A0E", "#C2383A", stripes=("x", 2.6, 0.24, "#E4D2A4"))
    M["drape"] = cloth("P_Drape", "#24505A", "#0E2228", "#3E7E88", stripes=("z", 2.0, 0.06, "#D8A23A"))
    M["burlap"] = cloth("P_Burlap", "#9A8058", "#4E3E26", "#C8AE80", weave=160.0)
    M["rope"] = cloth("P_Rope", "#8A7350", "#3E3020", "#BBA27A", stripes=("z", 60.0, 0.25, "#3A2C1C"), edge_r=0.004)
    M["potion"] = potion_mat()

    m = ba.wood_mat("P_Sign", "#7A5232", "#3A2412", "#A87A4E", grain=0.1, edge_r=0.008, axis="x", scale=2.0)
    E = MatEdit(m)
    g = E.decal(sign_glyph(), SIGN_RECT, "X", "Z", face="Y", face_lo=0.5, face_hi=0.7)
    E.albedo("#E8B850", E.m("MULTIPLY", g, 0.95))
    E.metal(0.6, g)
    E.rough(0.4, g)
    M["sign"] = m

    m = stone_mat("P_TabletStone", base="#66727A", dark="#363F48", light="#9CA8B0", moss=0.14)
    E = MatEdit(m)
    g = E.decal(tablet_glyphs(), TABLET_RECT, "X", "Z", face="Y", face_lo=0.55, face_hi=0.75)
    E.albedo("#1E2A34", E.m("MULTIPLY", g, 0.7))
    E.albedo("#BFF4FF", E.m("MULTIPLY", E.rng(g, 0.5, 0.95), 0.45))
    E.bump(g, -1.2)
    E.emit(E.rng(g, 0.3, 0.9))
    M["tablet"] = m

    # NPCs
    M["skin_m"] = skin_mat("P_SkinMerchant", "#D28E6C", "#8A4632", "#F4BC9C")
    M["skin_h"] = skin_mat("P_SkinHorologist", "#B4B49A", "#5E6252", "#DCDCC4")
    M["hair"] = cloth("P_Hair", "#5A3A26", "#22140A", "#8A6040", stripes=("z", 90.0, 0.25, "#2A180C"), edge_r=0.004,
                      weave=200.0)
    M["eye"] = ba.make_mat("P_Eye", "#14121A", dark="#000000", light="#3A3644", rough=0.12, noise_scale=20,
                                bevel_radius=0.002)
    M["shirt"] = cloth("P_Shirt", "#5A707E", "#26343E", "#8EA6B4", edge_r=0.008)
    M["trousers"] = cloth("P_Trousers", "#4C3C2E", "#1E160E", "#7A6650", edge_r=0.008)
    m = cloth("P_Apron", "#CDBE9C", "#7E6E52", "#EEE2C6", edge_r=0.008)
    E = MatEdit(m)
    st = E.rng(E.noise(7.0, 4.0, 0.65), 0.6, 0.66)
    E.albedo("#6E2A1A", E.m("MULTIPLY", st, 0.55))
    E.albedo("#3A2A1C", E.m("MULTIPLY", E.rng(E.z, 0.62, 0.42), 0.35))
    M["apron"] = m
    M["leather"] = ba.leather_mat("P_Leather", "#4E301C", "#1C0F08", "#7E563A", edge_r=0.008)
    M["bone"] = ba.bone_mat("P_Bone", edge_r=0.006, scale=2.0)
    M["string"] = cloth("P_String", "#D8CDB0", "#8A7E62", "#F4ECD6", edge_r=0.002, weave=300.0)
    M["pewter"] = ba.iron_mat("P_Pewter", rust=0.0, edge_r=0.006, base="#7E868C", scale=1.5)
    M["foam"] = cloth("P_Foam", "#F2E8C8", "#C8B88E", "#FFFFFF", edge_r=0.006)
    m = cloth("P_Robe", "#2A3552", "#0F1420", "#4C5C84", edge_r=0.012)
    E = MatEdit(m)
    hem = E.m("SUBTRACT", E.rng(E.z, 0.16, 0.12), E.rng(E.z, 0.07, 0.05), clamp=True)
    E.albedo("#C89A3A", hem)
    E.metal(0.5, hem)
    M["robe"] = m
    m = cloth("P_Mantle", "#6E2A26", "#2E0E0C", "#A84A40")
    E = MatEdit(m)
    trim = E.m("SUBTRACT", E.rng(E.z, 1.36, 1.32), E.rng(E.z, 1.27, 1.25), clamp=True)
    E.albedo("#D8A23A", trim)
    E.metal(0.5, trim)
    M["mantle"] = m
    m = ba.make_mat("P_Vials", "#6CD8FF", dark="#2A70A8", light="#D8FBFF", rough=0.08, noise_scale=20,
                         noise_amt=0.7, bevel_radius=0.003)
    E = MatEdit(m)
    cells = E.rng(E.voronoi(34.0), 0.3, 0.12)
    E.albedo("#F2FFFF", E.m("MULTIPLY", cells, 0.8))
    E.emit(E.m("ADD", E.m("MULTIPLY", cells, 0.45), 0.55))
    M["vials"] = m
    m = ba.make_mat("P_Lens", "#C8FFF0", dark="#7AE8D0", light="#FFFFFF", rough=0.05, noise_scale=40,
                         bevel_radius=0.002)
    E = MatEdit(m)
    E.emit(E.rng(E.noise(60.0), 0.3, 0.7, 0.85, 1.0))
    M["lens"] = m
    m = ba.make_mat("P_SyringeGlass", "#9CC8D0", dark="#4E7A86", light="#E6FAFF", rough=0.06, noise_scale=30,
                         bevel_radius=0.002)
    eh.enhance(m, edge_hex="#FFFFFF", edge_amt=1.0, edge_radius=0.004, top_hex="#FFFFFF", top_amt=0.3)
    M["syringe"] = m
    M["needle"] = ba.iron_mat("P_Needle", rust=0.0, edge_r=0.002, base="#A6B0B8")
    return M


def skin_mat(name, base, dark, light):
    m = ba.make_mat(name, base, dark=dark, light=light, rough=0.62, noise_scale=7.0, noise_amt=0.45,
                         edge_wear=light, edge_wear_amt=0.5, cavity_dirt=0.6, bump_scale=60, bump_strength=0.06,
                         bevel_radius=0.005)
    eh.enhance(m, edge_hex=light, edge_amt=0.6, edge_radius=0.012, top_hex=light, top_amt=0.25, bottom_amt=0.25,
               cavity_amt=0.6, cavity_dist=0.06, cavity_hex="#3A1410")
    return m


def potion_mat():
    m = ba.make_mat("P_Potion", "#3A8A3A", dark="#1A3A1A", light="#8AE08A", rough=0.08, noise_scale=8,
                         noise_amt=0.5, bevel_radius=0.003)
    E = MatEdit(m)
    hue = E.noise(0.9, 1.0, 0.5, coord=E.vec(E.m("FLOOR", E.m("MULTIPLY", E.x, 6.0)),
                                              E.m("FLOOR", E.m("MULTIPLY", E.z, 2.5)), 0.0))
    r = dc.ramp(E.nt, [(0.0, dc.hex_rgba("#B0182E")), (0.3, dc.hex_rgba("#2E9C3E")), (0.45, dc.hex_rgba("#7A2EB8")),
                       (0.6, dc.hex_rgba("#E0A020")), (0.75, dc.hex_rgba("#2A70D0"))], loc=E._loc())
    r.color_ramp.interpolation = "CONSTANT"
    E.nt.links.new(hue, dc._sock(r.inputs, "Fac"))
    E.albedo(dc._sock(r.outputs, "Color"), 0.85, blend="MIX")
    E.albedo("#06080C", E.rng(E.naxis("Z"), -0.2, -0.9, 0.0, 0.5))
    dot = dc.new_node(E.nt, "ShaderNodeVectorMath", E._loc())
    dot.operation = "DOT_PRODUCT"
    E.nt.links.new(E.normal, dot.inputs[0])
    dot.inputs[1].default_value = Vector((-0.5, -0.6, 0.6)).normalized()
    E.albedo("#FFFFFF", E.m("MULTIPLY", E.rng(dot.outputs["Value"], 0.85, 0.95), 0.8))
    return m


# ---------------------------------------------------------------------------
# Props
# ---------------------------------------------------------------------------

ROMAN = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def numeral_bars(text, h=0.082):
    cw = {"I": 0.022, "V": 0.044, "X": 0.044}
    gap = 0.007
    total = sum(cw[c] for c in text) + gap * (len(text) - 1)
    x = -total / 2
    bars = []
    for c in text:
        cx = x + cw[c] / 2
        if c == "I":
            bars.append((cx, 0.0, h))
        elif c == "V":
            bars += [(cx - 0.0108, -0.27, h * 1.03), (cx + 0.0108, 0.27, h * 1.03)]
        else:
            bars += [(cx, -0.5, h * 1.12), (cx, 0.5, h * 1.12)]
        x += cw[c] + gap
    return bars, total


def build_teleporter():
    A = Asset("Teleporter", weight=1.0, tint="#7FE8FF",
              usage="Chronometer Gate teleport statue. Pivot bottom centre; clock ring faces -Z (camera). Emission = "
                    "inner ring channel. PortalSocket = ring centre.")
    P = A.piece("Teleporter")
    rng = random.Random(31)
    RC = 1.74
    P.add("stone", stone((-0.7, -0.45, 0.0), (0.7, 0.45, 0.22), rng, chips=3, bev=0.035))
    P.add("stone", stone((-0.6, -0.38, 0.22), (0.6, 0.38, 0.53), rng, chips=2, bev=0.03))
    P.add("stone", stone((-0.67, -0.43, 0.53), (0.67, 0.43, 0.65), rng, chips=3, bev=0.03))
    P.add("stone", stone((-0.34, -0.2, 0.65), (0.34, 0.2, 0.82), rng, chips=1, bev=0.035))
    # Brass front plaque with a gear emblem.
    P.add("brass", cbox((0, -0.39, 0.375), (0.5, 0.03, 0.2), bev=0.014))
    P.add("brass", gear((0, 0, 0.375), 10, 0.055, 0.072, 0.03, -0.425, -0.405, spokes=0, hub=0.018))
    # Ring body: rims, numeral band and the recessed channel.
    prof = [(0.70, -0.08), (0.70, 0.07), (0.725, 0.10), (0.752, 0.10), (0.756, 0.062), (0.804, 0.062),
            (0.808, 0.10), (0.92, 0.10), (0.928, 0.128), (0.972, 0.128), (1.0, 0.098), (1.0, -0.076),
            (0.976, -0.102), (0.73, -0.102)]
    P.add("brass", revolve_loop(prof, 44, center=(0, 0, RC)))
    P.add("glow", revolve_loop([(0.757, 0.06), (0.803, 0.06), (0.803, 0.069), (0.757, 0.069)], 44, center=(0, 0, RC)))
    # Roman numeral studs.
    for hr in range(12):
        th = math.pi / 2 - hr * TAU / 12
        phi = math.pi / 2 - th
        bars, total = numeral_bars(ROMAN[hr])
        r = 0.866
        pos = Vector((math.cos(th) * r, 0.0, RC + math.sin(th) * r))
        plate = cbox((0, 0, 0), (max(0.07, total + 0.036), 0.022, 0.108), bev=0.01)
        rot(plate, phi, "Y")
        P.add("iron", translate(plate, pos + Vector((0, -0.111, 0))))
        for cx, psi, L in bars:
            b = cbox((0, 0, 0), (0.0135, 0.014, L))
            rot(b, psi, "Y")
            translate(b, (cx, 0, 0))
            rot(b, phi, "Y")
            P.add("brass", translate(b, pos + Vector((0, -0.127, 0))))
    # Clock hands on a hub, held by two curved arms from the lower bore.
    def hand(outline, theta, y0, y1):
        pts = [(a * math.cos(theta) - b * math.sin(theta), RC + a * math.sin(theta) + b * math.cos(theta))
               for a, b in outline]
        return prism_xz(pts, y0, y1)
    minute = [(-0.2, 0.0), (-0.17, -0.045), (-0.1, -0.03), (0.0, -0.042), (0.42, -0.02), (0.47, -0.06),
              (0.6, 0.0), (0.47, 0.06), (0.42, 0.02), (0.0, 0.042), (-0.1, 0.03), (-0.17, 0.045)]
    hour = [(-0.16, 0.0), (-0.13, -0.05), (-0.08, -0.036), (0.0, -0.05), (0.24, -0.024), (0.26, -0.075),
            (0.33, -0.07), (0.41, 0.0), (0.33, 0.07), (0.26, 0.075), (0.24, 0.024), (0.0, 0.05), (-0.08, 0.036),
            (-0.13, 0.05)]
    P.add("brass", eh.bm_bevel(hand(minute, math.radians(30), -0.172, -0.152), 0.004, 1))
    P.add("brass", eh.bm_bevel(hand(hour, math.radians(150), -0.152, -0.132), 0.004, 1))
    P.add("brass", lathe([(0.072, 0.0), (0.078, 0.022), (0.056, 0.05), (0.03, 0.062), (0.012, 0.075), (0.0, 0.078)],
                         segs=16, axis=(0, -1, 0), center=(0, -0.11, RC)))
    P.add("brass", gear((0, 0, RC), 12, 0.1, 0.125, 0.06, -0.13, -0.1, spokes=3, hub=0.02))
    # Brass struts from the plinth to the ring, ball feet.
    for sgn in (-1, 1):
        a = math.radians(-90 + sgn * 46)
        top = Vector((math.cos(a) * 0.97, 0.0, RC + math.sin(a) * 0.97))
        base = Vector((sgn * 0.5, 0.0, 0.66))
        P.add("brass", tube([base, base.lerp(top, 0.5) + Vector((sgn * 0.04, 0, 0)), top], [0.055, 0.045, 0.04], segs=8))
        P.add("brass", blob(base + Vector((0, 0, 0.02)), 0.075, scale=(1, 1, 0.75), segs=10, rings=6))
        P.add("brass", lathe([(0.065, -0.03), (0.07, 0.0), (0.065, 0.03)], segs=8, axis=(top - base),
                             center=base.lerp(top, 0.82)))
    # Gears behind the ring and a finial on top.
    P.add("brass", gear((0.66, 0, RC + 0.6), 12, 0.27, 0.33, 0.2, 0.11, 0.2, phase=0.1, spokes=4, hub=0.05))
    P.add("iron", gear((-0.78, 0, RC - 0.42), 9, 0.17, 0.215, 0.11, 0.1, 0.17, phase=0.3, spokes=3, hub=0.04))
    P.add("brass", lathe([(0.0, RC + 0.95), (0.1, RC + 0.96), (0.115, RC + 0.99), (0.07, RC + 1.03),
                          (0.055, RC + 1.07), (0.08, RC + 1.1), (0.05, RC + 1.13), (0.0, RC + 1.15)], segs=12))
    A.socket("PortalSocket", (0.0, 0.0, RC))
    return A


def build_chest():
    A = Asset("Chest", weight=1.25, tint="#C79BFF",
              usage="Iron-banded treasure chest 1.0 x 0.7 x 0.65 (Unity x,y,z). Chest_Lid pivot = hinge line "
                    "(back top edge of the base); rotate about Unity +X (negative angle opens toward the back). "
                    "Emission = glowing lock.")
    B = A.piece("Chest_Base")
    L = A.piece("Chest_Lid", pivot=(0.0, 0.3, 0.42))
    rng = random.Random(12)
    W, D = 0.48, 0.3
    for z0, z1 in ((0.035, 0.162), (0.168, 0.29), (0.296, 0.42)):
        B.add("wood_h", box((-W, -D, z0), (W, D, z1), bev=0.014))
    for sx in (-1, 1):
        for sy in (-0.17, 0.17):
            B.add("iron", cbox((sx * 0.488, sy, 0.228), (0.014, 0.06, 0.39), bev=0.004))
        B.add("iron", cbox((sx * 0.49, 0, 0.27), (0.016, 0.1, 0.06), bev=0.004))
        B.add("iron", torus((sx * 0.515, 0, 0.215), 0.05, 0.009, normal=(1, 0, 0), seg=12, rseg=5))
    for bx in (-0.32, 0.32):
        B.add("iron", cbox((bx, -D - 0.006, 0.228), (0.075, 0.014, 0.4), bev=0.005))
        B.add("iron", cbox((bx, D + 0.006, 0.228), (0.075, 0.014, 0.4), bev=0.005))
        for z in (0.09, 0.36):
            B.add("iron", blob((bx, -D - 0.014, z), 0.0125, scale=(1, 0.6, 1), segs=6, rings=4))
    for sx in (-1, 1):
        for sy in (-1, 1):
            B.add("iron", cbox((sx * (W - 0.018), sy * (D - 0.018), 0.228), (0.05, 0.05, 0.41), bev=0.006))
            B.add("iron", cbox((sx * (W - 0.03), sy * (D - 0.03), 0.02), (0.085, 0.085, 0.04), bev=0.008))
    # Lock plate + glowing keyhole and rune ring.
    B.add("iron", cbox((0, -D - 0.012, 0.335), (0.17, 0.026, 0.15), bev=0.01))
    key = [(0.0, 0.0285), (0.0115, 0.022), (0.0145, 0.011), (0.0085, 0.0), (0.016, -0.034), (-0.016, -0.034),
           (-0.0085, 0.0), (-0.0145, 0.011), (-0.0115, 0.022)]
    B.add("lock_glow", prism_xz([(x, z + 0.34) for x, z in key], -D - 0.03, -D - 0.022))
    B.add("lock_glow", torus((0, -D - 0.026, 0.335), 0.056, 0.0045, normal=(0, 1, 0), seg=20, rseg=4))
    B.add("iron", torus((0, -D - 0.027, 0.335), 0.067, 0.006, normal=(0, 1, 0), seg=20, rseg=4))
    # Base hinge leaves on the back.
    for hx in (-0.3, 0.3):
        B.add("iron", cbox((hx, D + 0.008, 0.37), (0.1, 0.012, 0.09), bev=0.003))
        B.add("iron", lathe([(0.016, -0.05), (0.016, 0.05)], segs=8, axis=(1, 0, 0), center=(hx, D + 0.012, 0.42)))
    # Lid: five barrel planks, end boards, skirt, bands, hasp.
    zc, R = 0.36, 0.34
    a0, a1 = math.radians(151.9), math.radians(28.1)
    nplank = 5
    for k in range(nplank):
        aa = lerp(a0, a1, k / nplank) - 0.006
        bb = lerp(a0, a1, (k + 1) / nplank) + 0.006
        arc = [(math.cos(lerp(aa, bb, i / 2)) * R, zc + math.sin(lerp(aa, bb, i / 2)) * R) for i in range(3)]
        inner = [(y * 0.85, zc + (z - zc) * 0.85) for y, z in reversed(arc)]
        poly = arc + inner
        rings = [[Vector((x, y, z)) for y, z in poly] for x in (-W + 0.035, W - 0.035)]
        L.add("wood_h", eh.bm_bevel(loft(rings), 0.01, 1))
    lid_prof = [(-D, 0.42)] + [(math.cos(lerp(a0, a1, i / 8)) * R, zc + math.sin(lerp(a0, a1, i / 8)) * R)
                                for i in range(9)] + [(D, 0.42)]
    for sx in (-1, 1):
        rings = [[Vector((x, y, z)) for y, z in lid_prof] for x in (sx * W, sx * (W - 0.04))]
        L.add("wood_v", eh.bm_bevel(loft(rings), 0.01, 1))
    L.add("wood_h", box((-W, -D, 0.425), (W, -D + 0.04, 0.52), bev=0.012))
    L.add("wood_h", box((-W, D - 0.04, 0.425), (W, D, 0.52), bev=0.012))
    for bx in (-0.32, 0.32):
        pts = [Vector((bx, math.cos(lerp(a0, a1, i / 10)) * (R + 0.012), zc + math.sin(lerp(a0, a1, i / 10)) * (R + 0.012)))
               for i in range(11)]
        pts = [Vector((bx, -D - 0.008, 0.43))] + pts + [Vector((bx, D + 0.008, 0.43))]
        L.add("iron", tube(pts, [0.0065] * len(pts), segs=4, flatten=5.5, up=X))
        for i in (2, 5, 8):
            p = pts[i + 1]
            n = (p - Vector((bx, 0, zc))).normalized()
            L.add("iron", blob(p + n * 0.008, 0.012, scale=(1, 1, 1), segs=6, rings=4))
    L.add("iron", box((-W - 0.008, -D - 0.008, 0.425), (W + 0.008, -D + 0.012, 0.455), bev=0.005))
    L.add("iron", box((-W - 0.008, D - 0.012, 0.425), (W + 0.008, D + 0.008, 0.455), bev=0.005))
    L.add("iron", cbox((0, -D - 0.018, 0.452), (0.07, 0.016, 0.09), bev=0.006))
    L.add("iron", torus((0, -D - 0.03, 0.418), 0.022, 0.006, normal=(1, 0, 0), seg=10, rseg=4))
    for hx in (-0.3, 0.3):
        L.add("iron", cbox((hx, D + 0.004, 0.47), (0.07, 0.012, 0.09), bev=0.003))
    return A


def build_pedestal():
    A = Asset("Pedestal", weight=1.2, tint="#FFD27A",
              usage="Shop item stand (carved stone column + velvet cushion). Pivot bottom centre. ItemSocket 0.45 m "
                    "above the cushion top. No emission.")
    P = A.piece("Pedestal")
    rng = random.Random(5)
    P.add("stone", stone((-0.24, -0.24, 0.0), (0.24, 0.24, 0.1), rng, chips=2, bev=0.02, chip=(0.02, 0.05)))
    P.add("stone", box((-0.2, -0.2, 0.1), (0.2, 0.2, 0.15), bev=0.015))
    rings = []
    for z, r in ((0.15, 0.15), (0.17, 0.135), (0.5, 0.125), (0.52, 0.14)):
        rings.append([Vector((math.cos(TAU * i / 16 + math.pi / 16) * r * (1.0 if i % 2 == 0 else 0.8),
                              math.sin(TAU * i / 16 + math.pi / 16) * r * (1.0 if i % 2 == 0 else 0.8), z))
                      for i in range(16)])
    P.add("stone", loft(rings))
    P.add("stone", torus((0, 0, 0.335), 0.132, 0.02, seg=16, rseg=5))
    P.add("brass", torus((0, 0, 0.16), 0.15, 0.012, seg=16, rseg=4))
    P.add("stone", box((-0.2, -0.2, 0.52), (0.2, 0.2, 0.58), bev=0.012))
    P.add("stone", stone((-0.235, -0.235, 0.58), (0.235, 0.235, 0.64), rng, chips=2, bev=0.015, chip=(0.015, 0.04)))
    P.add("brass", cbox((0, -0.135, 0.42), (0.11, 0.012, 0.06), bev=0.004))
    # Velvet cushion (squared pillow) with gold tassels.
    bm = lathe([(0.0, -1.0)] + [(math.sin(math.pi * k / 8), -math.cos(math.pi * k / 8)) for k in range(1, 8)] +
               [(0.0, 1.0)], segs=16)

    def pillow(v):
        dx, dy, dz = v.x, v.y, v.z
        sx = math.copysign(abs(dx) ** 0.55, dx) * 0.205
        sy = math.copysign(abs(dy) ** 0.55, dy) * 0.205
        corner = (abs(dx) * abs(dy)) * 2.0
        sz = dz * 0.055 * (1.0 - 0.45 * corner)
        return Vector((sx, sy, 0.695 + sz))
    P.add("velvet", ba.xform(bm, pillow))
    cord = [Vector((0.205 * max(-1, min(1, 1.42 * math.cos(TAU * i / 24))),
                    0.205 * max(-1, min(1, 1.42 * math.sin(TAU * i / 24))), 0.693)) for i in range(24)]
    P.add("gold_thread", tube(cord, [0.007] * 24, segs=5, closed=True, up=Z))
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = Vector((sx * 0.2, sy * 0.2, 0.69))
            P.add("gold_thread", blob(c, 0.015, segs=6, rings=4))
            P.add("gold_thread", lathe([(0.004, -0.005), (0.016, -0.03), (0.019, -0.07), (0.0, -0.075)], segs=6,
                                       center=c + Vector((sx * 0.008, sy * 0.008, 0))))
    A.socket("ItemSocket", (0.0, 0.0, 0.75 + 0.45))
    return A


def coin_bm(r=0.07, th=0.018, segs=32, emblem=True, center=(0, 0, 0)):
    """Gold coin facing -Y (front) with a raised clock emblem on both faces."""
    h = th * 0.5
    prof = [(0.0, h - 0.0045), (0.05, h - 0.0045), (0.054, h - 0.001), (0.066 * r / 0.07, h), (r, h - 0.003),
            (r, -h + 0.003), (0.066 * r / 0.07, -h), (0.054, -h + 0.001), (0.05, -h + 0.0045), (0.0, -h + 0.0045)]
    parts = [lathe(prof, segs=segs, axis=(0, -1, 0))]
    if emblem:
        for side in (-1, 1):
            face_y = side * (h - 0.0045)
            parts.append(torus((0, face_y, 0), 0.036, 0.0028, normal=(0, 1, 0), seg=24, rseg=4, flatten=0.8))
            for k in range(12):
                a = TAU * k / 12
                L = 0.009 if k % 3 == 0 else 0.0055
                t = cbox((0, 0, 0), (0.0036, 0.006, L))
                rot(t, math.pi / 2 - a, "Y")
                parts.append(translate(t, (math.cos(a) * 0.044, face_y, math.sin(a) * 0.044)))
            for ang, ln, w in ((math.radians(60), 0.026, 0.0042), (math.radians(150), 0.019, 0.0052)):
                t = cbox((0, 0, ln * 0.5), (w, 0.0055, ln))
                rot(t, math.pi / 2 - ang, "Y")
                parts.append(translate(t, (0, face_y, 0)))
            parts.append(blob((0, face_y, 0), 0.0065, scale=(1, 0.6, 1), segs=8, rings=5))
    out = []
    for b in parts:
        out.append(translate(b, center))
    return out


def build_coin():
    A = Asset("Coin", weight=2.4, tint="#FFFFFF",
              usage="Gold coin pickup, 0.14 m, origin at its centre, faces -Z (camera). Spin about Unity +Y.")
    P = A.piece("Coin", pivot=(0, 0, 0))
    P.add("gold", coin_bm())
    return A


def build_goldpile():
    A = Asset("GoldPile", weight=1.1, tint="#FFFFFF",
              usage="Heap of coins ~0.6 m wide, pivot bottom centre. No emission.")
    P = A.piece("GoldPile")
    rng = random.Random(19)
    prof = [(0.0, 0.205), (0.06, 0.198), (0.13, 0.168), (0.2, 0.116), (0.26, 0.058), (0.3, 0.018), (0.31, 0.0)]
    mound = lathe(prof, segs=20, scale_xy=(1.0, 0.78), cap1=True)
    for v in mound.verts:
        if v.co.z > 0.01:
            v.co += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 1))) * 0.008
    P.add("gold_heap", mound)

    def height(x, y):
        r = math.hypot(x, y / 0.78)
        for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
            if r0 <= r <= r1:
                return lerp(z0, z1, (r - r0) / (r1 - r0))
        return 0.0

    def coin_at(p, nrm, r=0.034):
        c = lathe([(r, -0.003), (r, 0.003)], segs=10, phase=rng.uniform(0, 1))
        rot(c, rng.uniform(0, TAU), "Z")
        return aim(c, nrm, p)

    placed = 0
    tries = 0
    while placed < 44 and tries < 400:
        tries += 1
        a = rng.uniform(0, TAU)
        rr = math.sqrt(rng.uniform(0.0, 1.0)) * 0.29
        x, y = math.cos(a) * rr, math.sin(a) * rr * 0.78
        z = height(x, y)
        eps = 0.01
        gx = (height(x + eps, y) - height(x - eps, y)) / (2 * eps)
        gy = (height(x, y + eps) - height(x, y - eps)) / (2 * eps)
        nrm = Vector((-gx, -gy, 1.0)).normalized()
        nrm = (nrm + Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45), 0.0))).normalized()
        if y > 0.12 and rng.random() < 0.6:
            continue
        P.add("gold", coin_at(Vector((x, y, z + 0.004)), nrm, rng.uniform(0.03, 0.037)))
        placed += 1
    for k in range(9):
        a = rng.uniform(0, TAU)
        rr = rng.uniform(0.31, 0.4)
        n = Vector((rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 1.0)).normalized()
        cr = rng.uniform(0.03, 0.036)
        p = Vector((math.cos(a) * rr, math.sin(a) * rr * 0.8, 0.0032 + cr * math.sqrt(1.0 - n.z * n.z)))
        P.add("gold", coin_at(p, n, cr))
    for p, n in (((0.12, -0.2, 0.06), (0.25, -0.9, 0.3)), ((-0.17, -0.17, 0.05), (-0.3, -0.85, 0.2))):
        P.add("gold", coin_at(Vector(p), Vector(n), 0.036))
    P.add("gem", jitter_bm(ba.blob((0.06, -0.12, 0.155), 0.03, scale=(1, 1, 0.8), segs=6, rings=4), 0.004, rng))
    P.add("gem", jitter_bm(ba.blob((-0.12, -0.08, 0.13), 0.024, scale=(1, 1, 0.8), segs=6, rings=4), 0.004, rng))
    gob = lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.008), (0.012, 0.02), (0.01, 0.07), (0.03, 0.085), (0.05, 0.13),
                 (0.054, 0.15), (0.048, 0.152), (0.044, 0.135), (0.0, 0.1)], segs=12)
    rot(gob, math.radians(-12), "Y")
    P.add("gold", translate(gob, (0.25, -0.04, 0.0)))
    return A


def build_fountain():
    A = Asset("Fountain", weight=1.0, tint="#FF2A3A",
              usage="Health fountain. Fountain (stone basin + gargoyle stele) pivot bottom centre; Fountain_Liquid "
                    "(surface + spout stream) pivot at the liquid surface centre so Unity can lower/hide it. "
                    "Emission = red liquid.")
    P = A.piece("Fountain")
    Lq = A.piece("Fountain_Liquid", pivot=(0.0, 0.0, 0.56))
    rng = random.Random(44)
    SY = 0.56
    P.add("stone_moss", lathe([(0.0, 0.0), (0.5, 0.0), (0.52, 0.06), (0.44, 0.1), (0.4, 0.2), (0.0, 0.2)], segs=16,
                              scale_xy=(1.0, SY)))
    basin = [(0.0, 0.17), (0.6, 0.17), (0.73, 0.28), (0.8, 0.48), (0.81, 0.6), (0.73, 0.635), (0.69, 0.585),
             (0.63, 0.43), (0.0, 0.41)]
    bm = lathe(basin, segs=28, scale_xy=(1.0, SY))
    for v in bm.verts:
        if v.co.z > 0.58:
            v.co.z += rng.uniform(-0.008, 0.008)
    P.add("stone_moss", bm)
    for k in range(7):
        a = math.pi + math.pi * (k + 0.5) / 7
        rib = [Vector((math.cos(a) * r, math.sin(a) * r * SY, z)) for r, z in ((0.62, 0.19), (0.75, 0.3), (0.815, 0.5),
                                                                             (0.825, 0.59))]
        P.add("stone_moss", tube(rib, [0.03, 0.036, 0.034, 0.03], segs=6))
    # Arched back stele with side pilasters and a cap.
    arch = [(-0.52, 0.0), (0.52, 0.0), (0.52, 1.62)] + \
           [(math.cos(math.radians(a)) * 0.52, 1.62 + math.sin(math.radians(a)) * 0.34) for a in range(15, 180, 15)] + \
           [(-0.52, 1.62)]
    P.add("stone_moss", eh.bm_bevel(prism_xz(arch, 0.36, 0.55), 0.025, 1))
    for sx in (-1, 1):
        P.add("stone_moss", stone((sx * 0.58 - 0.08, 0.32, 0.0), (sx * 0.58 + 0.08, 0.58, 1.5), rng, chips=2,
                                  bev=0.02))
        P.add("stone_moss", stone((sx * 0.58 - 0.1, 0.3, 1.5), (sx * 0.58 + 0.1, 0.6, 1.6), rng, chips=1, bev=0.02))
    # Gargoyle head (horned, open jaw) on a bracket.
    H = Vector((0.0, 0.2, 1.28))
    P.add("stone", blob(H + Vector((0, 0.12, -0.16)), 0.13, scale=(0.9, 1.0, 0.9), segs=10, rings=7))
    P.add("stone", blob(H, 0.165, scale=(1.0, 0.95, 0.88), segs=12, rings=8, rng=rng, jitter=0.03))
    P.add("stone", blob(H + Vector((0, -0.14, -0.06)), 0.105, scale=(0.85, 1.25, 0.66), segs=10, rings=7))
    P.add("stone", blob(H + Vector((0, -0.12, 0.05)), 0.1, scale=(1.45, 0.55, 0.42), segs=10, rings=6))
    P.add("stone", blob(H + Vector((0, -0.12, -0.2)), 0.09, scale=(0.82, 1.15, 0.42), segs=10, rings=6))
    P.add("stone", blob(H + Vector((0, -0.245, -0.035)), 0.038, scale=(1.2, 0.8, 0.8), segs=8, rings=5))
    for sx in (-1, 1):
        P.add("eye", blob(H + Vector((sx * 0.062, -0.135, 0.0)), 0.024, segs=8, rings=5))
        P.add("stone", cone(H + Vector((sx * 0.04, -0.215, -0.1)), (0, -0.1, -1), 0.05, 0.013, segs=5))
        P.add("stone", cone(H + Vector((sx * 0.035, -0.19, -0.2)), (0, -0.2, 1), 0.04, 0.011, segs=5))
        horn = [H + Vector((sx * 0.1, -0.02, 0.1)), H + Vector((sx * 0.19, 0.04, 0.2)),
                H + Vector((sx * 0.23, 0.14, 0.3)), H + Vector((sx * 0.2, 0.24, 0.36))]
        P.add("stone", tube(catmull(horn, 2), [0.045, 0.04, 0.034, 0.027, 0.02, 0.012, 0.004], segs=7))
        P.add("stone", cone(H + Vector((sx * 0.14, 0.04, 0.02)), (sx * 1.0, 0.5, 0.35), 0.11, 0.04, segs=5))
    # Liquid surface, ripples and the stream from the jaws.
    Lq.add("blood", lathe([(0.0, 0.54), (0.692, 0.54), (0.692, 0.562), (0.0, 0.562)], segs=28, scale_xy=(1.0, SY)))
    mouth = H + Vector((0, -0.2, -0.13))
    stream = [mouth, mouth + Vector((0, -0.05, -0.1)), mouth + Vector((0, -0.08, -0.3)),
              mouth + Vector((0, -0.09, -0.52)), Vector((mouth.x, mouth.y - 0.09, 0.565))]
    Lq.add("blood", tube(catmull(stream, 2), [0.032, 0.03, 0.028, 0.03, 0.032, 0.034, 0.036, 0.04, 0.045], segs=8))
    sp = Vector((mouth.x, mouth.y - 0.09, 0.565))
    for R, r in ((0.075, 0.012), (0.15, 0.008)):
        Lq.add("blood", torus(sp, R, r, seg=16, rseg=4, flatten=0.6))
    for k in range(5):
        a = TAU * k / 5 + 0.4
        Lq.add("blood", blob(sp + Vector((math.cos(a) * 0.07, math.sin(a) * 0.07, 0.05 + 0.03 * (k % 2))), 0.012,
                             segs=6, rings=4))
    return A


def build_loretablet():
    A = Asset("LoreTablet", weight=1.1, tint="#7FE8FF",
              usage="Cracked lore stone on a base, pivot bottom centre, glyph face toward -Z. Emission = engraved "
                    "glyph lines.")
    P = A.piece("LoreTablet")
    rng = random.Random(61)
    P.add("stone_moss", stone((-0.5, -0.22, 0.0), (0.5, 0.22, 0.17), rng, chips=3, bev=0.03))
    out = [(-0.4, 0.15), (0.4, 0.15), (0.4, 1.04)] + \
          [(math.cos(math.radians(a)) * 0.4, 1.04 + math.sin(math.radians(a)) * 0.24) for a in range(15, 180, 15)] + \
          [(-0.4, 1.04)]
    # Jagged crack from the top-right of the arch down to the right edge.
    crack = [(0.16, 1.24), (0.2, 1.12), (0.14, 1.02), (0.26, 0.9), (0.22, 0.8), (0.4, 0.66)]
    a_pt, b_pt = crack[0], crack[-1]
    arch = out[3:-1]
    split = next(i for i, p in enumerate(arch) if p[0] < a_pt[0])
    main = [out[0], out[1], b_pt] + list(reversed(crack[1:-1])) + [a_pt] + arch[split:] + [out[-1]]
    chunk = [b_pt, out[2]] + arch[:split] + [a_pt] + crack[1:-1]
    for poly, off in ((main, Vector((-0.004, 0, -0.004))), (chunk, Vector((0.022, 0.006, -0.03)))):
        bm = prism_xz(poly, -0.085, 0.085)
        bm = eh.bm_bevel(bm, 0.018, 1)
        if off.z < -0.01:
            rot(bm, math.radians(3.5), "Y", origin=(0.4, 0, 0.66))
        translate(bm, off)
        P.add("tablet", bm)
    P.add("stone_moss", cbox((0.42, -0.1, 0.19), (0.08, 0.07, 0.05), bev=0.012))
    P.add("stone_moss", jitter_bm(blob((0.47, -0.25, 0.04), 0.05, segs=6, rings=4), 0.008, rng))
    P.add("stone_moss", jitter_bm(blob((-0.43, -0.27, 0.035), 0.04, segs=6, rings=4), 0.008, rng))
    P.add("stone_moss", jitter_bm(blob((0.35, -0.3, 0.025), 0.03, segs=6, rings=4), 0.006, rng))
    return A


def build_exitdoor():
    A = Asset("ExitDoor", weight=0.62, tint="#FFC870",
              usage="Biome exit: double door in a stone frame, 3.2 x 4.2 m, pivot bottom centre. Door_Left/Door_Right "
                    "pivots = outer hinge edges (rotate about Unity +Y). ExitDoor_Light is the glowing slab behind the "
                    "leaves (shows through the cracks; hide/fade it independently). Emission = crack light.")
    F = A.piece("ExitDoor_Frame")
    DL = A.piece("Door_Left", pivot=(-1.085, 0.0, 0.12))
    DR = A.piece("Door_Right", pivot=(1.085, 0.0, 0.12))
    LG = A.piece("ExitDoor_Light")
    rng = random.Random(71)
    ZS, RI = 2.3, 1.1
    F.add("stone", stone((-1.32, -0.55, 0.0), (1.32, 0.32, 0.12), rng, chips=3, bev=0.025))
    for sx in (-1, 1):
        z = 0.0
        for k, hgt in enumerate((0.62, 0.55, 0.6, 0.53)):
            outer = 1.6 + (0.04 if k % 2 == 0 else -0.02)
            lo = (min(sx * 1.1, sx * outer), -0.38, z)
            hi = (max(sx * 1.1, sx * outer), 0.38, z + hgt - 0.012)
            F.add("stone", stone(lo, hi, rng, chips=2, bev=0.03))
            z += hgt
    nv = 9
    for k in range(nv):
        a0 = math.pi * k / nv + 0.008
        a1 = math.pi * (k + 1) / nv - 0.008
        ro = 1.92 if k == nv // 2 else (1.58 + (0.05 if k % 2 else 0.0))
        poly = [(math.cos(lerp(a0, a1, i / 2)) * RI, ZS + math.sin(lerp(a0, a1, i / 2)) * RI) for i in range(3)]
        poly += [(math.cos(lerp(a1, a0, i / 2)) * ro, ZS + math.sin(lerp(a1, a0, i / 2)) * ro) for i in range(3)]
        bm = prism_xz(poly, -0.4 if k == nv // 2 else -0.38, 0.38)
        bm = eh.bm_bevel(bm, 0.028, 1)
        if k != nv // 2:
            eh.chip_vertex(bm, rng, 0.05, pick=lambda co: co.y < -0.3)
        F.add("stone", bm)
    for sx in (-1, 1):
        F.add("stone", stone((min(sx * 1.6, sx * 1.36), -0.36, ZS - 0.01), (max(sx * 1.6, sx * 1.36), 0.36, ZS + 0.62),
                             rng, chips=1, bev=0.03))
    F.add("brass", lathe([(0.0, 0.0), (0.11, 0.0), (0.12, 0.03), (0.08, 0.05), (0.0, 0.06)], segs=12,
                         axis=(0, -1, 0), center=(0, -0.4, ZS + 1.66)))
    for sx in (-1, 1):
        for z in (0.6, 1.5, 2.4):
            F.add("iron", lathe([(0.03, -0.09), (0.03, 0.09)], segs=8, center=(sx * 1.1, 0.0, z)))
    # Light slab behind the leaves (shows through every gap).
    opening = [(-1.1, 0.12), (1.1, 0.12)] + [(math.cos(math.radians(a)) * RI, ZS + math.sin(math.radians(a)) * RI)
                                             for a in range(0, 181, 15)]
    LG.add("door_light", prism_xz(opening, 0.1, 0.12))

    def ztop(x):
        return ZS + math.sqrt(max(RI * RI - x * x, 0.0)) - 0.012

    for D, sgn in ((DL, -1), (DR, 1)):
        x_in, x_out = sgn * 0.016, sgn * 1.085
        edges = [lerp(x_in, x_out, k / 4) for k in range(5)]
        for k in range(4):
            xa, xb = sorted((edges[k], edges[k + 1]))
            xa, xb = xa + 0.0035, xb - 0.0035
            xs = [lerp(xa, xb, i / 3) for i in range(4)]
            poly = [(xa, 0.13), (xb, 0.13)] + [(x, ztop(x)) for x in reversed(xs)]
            D.add("wood_dark", eh.bm_bevel(prism_xz(poly, -0.065, 0.065), 0.014, 1))
        for z in (0.55, 1.45, 2.38):
            xa, xb = sorted((x_in + sgn * 0.03, x_out - sgn * 0.005))
            D.add("iron", box((xa, -0.088, z - 0.05), (xb, -0.062, z + 0.05), bev=0.008))
            D.add("iron", lathe([(0.04, z - 0.07), (0.044, z - 0.05), (0.044, z + 0.05), (0.04, z + 0.07)], segs=8,
                                center=(x_out, 0.0, 0.0)))
            for i in range(3):
                x = lerp(x_out, x_in, 0.2 + 0.3 * i)
                D.add("iron", blob((x, -0.09, z), 0.017, scale=(1, 0.6, 1), segs=6, rings=4))
        kx = sgn * 0.28
        D.add("iron", blob((kx, -0.075, 1.25), 0.07, scale=(1, 0.45, 1.1), segs=8, rings=6))
        D.add("brass", torus((kx, -0.105, 1.12), 0.1, 0.018, normal=(0, 1, 0), seg=16, rseg=5))
    return A


def bottle(kind, base, rng, h=None):
    """Assorted potion bottle shapes (lathe profiles), standing at base."""
    s = rng.uniform(0.9, 1.1)
    if kind == 0:
        prof = [(0.0, 0.0), (0.04, 0.0), (0.058, 0.03), (0.06, 0.06), (0.042, 0.095), (0.016, 0.11), (0.016, 0.14),
                (0.02, 0.145)]
    elif kind == 1:
        prof = [(0.0, 0.0), (0.035, 0.0), (0.036, 0.15), (0.026, 0.17), (0.013, 0.18), (0.013, 0.215), (0.017, 0.22)]
    else:
        prof = [(0.0, 0.0), (0.05, 0.0), (0.054, 0.012), (0.054, 0.085), (0.04, 0.1), (0.03, 0.105), (0.032, 0.115)]
    prof = [(r * s, z * s) for r, z in prof]
    top = prof[-1]
    glass = lathe(prof, segs=6, center=base, cap1=True)
    cork = lathe([(top[0] * 0.8, top[1] - 0.012), (top[0] * 0.95, top[1] + 0.018), (0.0, top[1] + 0.022)], segs=6,
                 center=base)
    return glass, cork


def build_merchantstall():
    A = Asset("MerchantStall", weight=0.8, tint="#FFB040",
              usage="Merchant counter ~3 m wide with canopy, potion shelves, crates, barrel and a hanging lantern. "
                    "Pivot bottom centre; the merchant stands behind the counter (Unity z ~ +0.45). "
                    "Emission = lantern. LightSocket = lantern centre.")
    P = A.piece("MerchantStall")
    rng = random.Random(8)
    for sx in (-1, 1):
        P.add("wood_v", cbox((sx * 1.42, -0.42, 1.21), (0.11, 0.11, 2.42), bev=0.014))
        P.add("wood_v", cbox((sx * 1.42, 0.92, 1.34), (0.11, 0.11, 2.68), bev=0.014))
    P.add("wood_h", cbox((0, -0.42, 2.38), (3.0, 0.1, 0.1), bev=0.014))
    P.add("wood_h", cbox((0, 0.92, 2.64), (3.0, 0.1, 0.1), bev=0.014))
    # Counter: plank front, top, sides.
    for k in range(7):
        x0 = -1.35 + k * (2.7 / 7) + 0.006
        P.add("wood_v", box((x0, -0.42, 0.06), (x0 + 2.7 / 7 - 0.012, -0.37, 0.95), bev=0.01))
    P.add("wood_h", box((-1.38, -0.44, 0.0), (1.38, -0.34, 0.07), bev=0.012))
    P.add("wood_h", box((-1.46, -0.52, 0.95), (1.46, 0.08, 1.03), bev=0.014))
    for sx in (-1, 1):
        P.add("wood_v", box((sx * 1.36 - 0.03, -0.4, 0.0), (sx * 1.36 + 0.03, 0.06, 0.95), bev=0.01))
    # Cloth drape over the counter front with a scalloped hem.
    grid = []
    for r in range(6):
        v = r / 5
        row = []
        for c in range(13):
            u = c / 12
            x = lerp(-1.22, 1.22, u)
            sc = 0.06 * abs(math.sin(u * math.pi * 6)) if r == 5 else 0.0
            z = lerp(1.0, 0.58, v) + sc
            y = -0.52 - 0.012 * v - 0.018 * math.sin(u * TAU * 6) * v
            row.append((x, y, z))
        grid.append(row)
    P.add("drape", thick_sheet(grid, 0.012))
    # Back shelves with potions.
    for z in (1.12, 1.52, 1.92):
        P.add("wood_h", box((-1.38, 0.74, z - 0.035), (1.38, 1.0, z), bev=0.01))
        for sx in (-0.7, 0.7):
            P.add("iron", cbox((sx, 0.98, z - 0.07), (0.03, 0.03, 0.09), bev=0.005))
    kinds = [0, 1, 2, 1, 0, 2, 1, 0, 2, 0, 1, 2, 0]
    slots = [(-1.15, 1.12), (-0.85, 1.12), (-0.25, 1.12), (0.3, 1.12), (0.95, 1.12),
             (-1.05, 1.52), (-0.6, 1.52), (0.05, 1.52), (0.62, 1.52), (1.12, 1.52),
             (-0.9, 1.92), (-0.2, 1.92), (0.75, 1.92)]
    for (x, z), kd in zip(slots, kinds):
        g, c = bottle(kd, (x, 0.86, z), rng)
        P.add("potion", g)
        P.add("wood_h", c)
    for (x, kd) in ((-0.95, 0), (-0.75, 1), (0.55, 2)):
        g, c = bottle(kd, (x, -0.2, 1.03), rng)
        P.add("potion", g)
        P.add("wood_h", c)
    P.add("leather", cbox((0.95, -0.22, 1.055), (0.26, 0.2, 0.05), bev=0.008))
    P.add("burlap", cbox((0.95, -0.22, 1.06), (0.24, 0.185, 0.04), bev=0.004))
    # Striped canopy with a scalloped valance.
    grid = []
    ys = [0.98, 0.6, 0.2, -0.2, -0.5, -0.56]
    for r, y in enumerate(ys + [-0.57, -0.57]):
        row = []
        for c in range(13):
            u = c / 12
            x = lerp(-1.6, 1.6, u)
            if r < len(ys):
                t = r / (len(ys) - 1)
                z = lerp(2.74, 2.47, t) - 0.07 * math.sin(math.pi * t) * (0.6 + 0.4 * abs(math.sin(u * math.pi * 2)))
                yy = y
            else:
                drop = 0.1 if r == len(ys) else 0.2 + 0.07 * abs(math.cos(u * math.pi * 6))
                z = 2.47 - drop
                yy = -0.57 - 0.01 * (r - len(ys))
            row.append((x, yy, z))
        grid.append(row)
    P.add("canopy", thick_sheet(grid, 0.018, normal_hint=(0, -0.5, 1)))
    # Hanging lantern on a chain.
    LX, LZ = 0.95, 2.0
    for k in range(3):
        P.add("iron", torus((LX, -0.42, 2.31 - k * 0.055), 0.02, 0.005, normal=(1, 0, 0) if k % 2 else (0, 1, 0),
                            seg=8, rseg=4))
    P.add("iron", lathe([(0.0, LZ + 0.17), (0.02, LZ + 0.165), (0.05, LZ + 0.14), (0.085, LZ + 0.1),
                         (0.08, LZ + 0.09)], segs=8, center=(LX, -0.42, 0)))
    P.add("iron", torus((LX, -0.42, LZ + 0.18), 0.018, 0.005, normal=(0, 1, 0), seg=8, rseg=4))
    P.add("lantern", lathe([(0.055, LZ - 0.07), (0.068, LZ - 0.02), (0.068, LZ + 0.05), (0.055, LZ + 0.09)], segs=8,
                           center=(LX, -0.42, 0)))
    for k in range(4):
        a = TAU * k / 4 + math.pi / 4
        P.add("iron", cbox((LX + math.cos(a) * 0.072, -0.42 + math.sin(a) * 0.072, LZ + 0.01), (0.012, 0.012, 0.17)))
    P.add("iron", lathe([(0.0, LZ - 0.11), (0.05, LZ - 0.105), (0.078, LZ - 0.08), (0.075, LZ - 0.07), (0.0, LZ - 0.07)],
                        segs=8, center=(LX, -0.42, 0)))
    # Hanging sign with a painted potion + coins (albedo only).
    sx0, sz0, sw, sh = SIGN_RECT
    P.add("sign", box((sx0, -0.47, sz0), (sx0 + sw, -0.43, sz0 + sh), bev=0.012))
    for x in (sx0 + 0.06, sx0 + sw - 0.06):
        P.add("rope", tube([(x, -0.45, sz0 + sh), (x, -0.43, 2.34)], [0.007, 0.007], segs=4))
    # Crates (left), barrel and sack (right).
    def crate(c, s, rz):
        parts = [cbox((0, 0, 0), (s * 0.94, s * 0.94, s * 0.94), bev=0.01)]
        e = s * 0.5 - 0.022
        for ax in range(3):
            for i in (-1, 1):
                for j in (-1, 1):
                    pos = [0.0, 0.0, 0.0]
                    size = [0.05, 0.05, 0.05]
                    pos[(ax + 1) % 3] = i * e
                    pos[(ax + 2) % 3] = j * e
                    size[ax] = s
                    parts.append(cbox(pos, size, bev=0.008))
        br = cbox((0, -s * 0.48, 0), (0.05, 0.03, s * 1.3), bev=0.006)
        rot(br, math.radians(45), "Y")
        parts.append(br)
        out = []
        for b in parts:
            rot(b, rz, "Z")
            out.append(translate(b, c))
        return out
    P.add("wood_h", crate(Vector((-1.72, -0.2, 0.26)), 0.52, 0.08))
    P.add("wood_h", crate(Vector((-1.68, -0.18, 0.7)), 0.36, -0.2))
    P.add("wood_dark", lathe([(0.2, 0.0), (0.24, 0.12), (0.26, 0.3), (0.24, 0.48), (0.2, 0.6), (0.0, 0.6)], segs=12,
                             center=(1.74, -0.12, 0.0)))
    for z, r in ((0.08, 0.225), (0.52, 0.225), (0.22, 0.256), (0.38, 0.256)):
        P.add("iron", torus((1.74, -0.12, z), r, 0.01, seg=12, rseg=4, flatten=1.6))
    sack = blob((1.72, 0.42, 0.24), 0.24, scale=(0.9, 0.8, 1.05), segs=10, rings=7, rng=rng, jitter=0.05)
    for v in sack.verts:
        if v.co.z < 0.02:
            v.co.z = 0.0
    P.add("burlap", sack)
    P.add("rope", torus((1.72, 0.42, 0.44), 0.07, 0.014, seg=8, rseg=4))
    A.socket("LightSocket", (LX, -0.42, LZ))
    return A


# ---------------------------------------------------------------------------
# NPCs
# ---------------------------------------------------------------------------

def ribcage(base, direction, side_hint, n_pairs=3, length=0.2, rib=0.13, rng=None, chimes=4):
    """A sprouting bone ribcage: short spine, rib pairs, bone wind-chimes hanging off the rib tips."""
    rng = rng or random.Random(0)
    d = Vector(direction).normalized()
    s = (Vector(side_hint) - d * Vector(side_hint).dot(d)).normalized()
    u = d.cross(s).normalized()
    if u.z < 0:
        u = -u
    bones, strings = [], []
    spine = [Vector(base) + d * length * k / 4 + u * 0.02 * math.sin(k) for k in range(5)]
    for k, p in enumerate(spine):
        bones.append(blob(p, (0.026 - 0.003 * k) * (0.6 + rib * 3.0), scale=(1, 1, 0.8), segs=6, rings=4))
    tips = []
    for k in range(n_pairs):
        a = Vector(base) + d * length * (0.25 + 0.6 * k / max(1, n_pairs - 1))
        L = rib * (1.0 - 0.18 * k)
        for sg in (-1, 1):
            pts = [a, a + s * sg * L * 0.45 + u * L * 0.25, a + s * sg * L * 0.85 + u * L * 0.1 + d * L * 0.2,
                   a + s * sg * L * 0.9 - u * L * 0.25 + d * L * 0.5]
            bones.append(tube(catmull(pts, 2), [0.015, 0.014, 0.013, 0.012, 0.011, 0.009, 0.007], segs=5))
            tips.append(pts[-1])
    rng.shuffle(tips)
    for t in tips[:chimes]:
        ln = rng.uniform(0.03, 0.09)
        strings.append(tube([t, t - Vector((0, 0, ln))], [0.003, 0.003], segs=4))
        top = t - Vector((0, 0, ln))
        cl = rng.uniform(0.07, 0.13)
        bones.append(lathe([(0.0125, 0.0), (0.0145, -0.009), (0.012, -cl * 0.5), (0.0145, -cl), (0.0, -cl - 0.005)],
                           segs=6, center=top))
    return bones, strings


def build_merchant():
    A = Asset("Merchant", weight=1.5, tint="#FFFFFF",
              usage="Tavern-keeper merchant NPC, ~1.9 m, static mesh, pivot at the feet, faces -Z. Extra ribcages "
                    "sprout through the apron as bone wind-chimes. No emission.")
    P = A.piece("Merchant")
    rng = random.Random(3)
    # Legs + boots
    for sx in (-1, 1):
        P.add("trousers", tube([(sx * 0.15, 0.0, 0.9), (sx * 0.17, -0.02, 0.55), (sx * 0.17, 0.0, 0.3)],
                               [0.135, 0.118, 0.1], segs=10))
        P.add("leather", tube([(sx * 0.17, 0.0, 0.36), (sx * 0.17, 0.0, 0.12)], [0.112, 0.105], segs=10))
        P.add("leather", torus((sx * 0.17, 0.0, 0.36), 0.112, 0.018, seg=10, rseg=4))
        P.add("leather", blob((sx * 0.17, -0.07, 0.07), 0.11, scale=(0.85, 1.45, 0.62), segs=10, rings=6))
    # Barrel torso: belly forward.
    prof = [(0.0, 0.8), (0.24, 0.81), (0.32, 0.88), (0.37, 1.0), (0.37, 1.12), (0.335, 1.26), (0.31, 1.37),
            (0.27, 1.46), (0.15, 1.53), (0.0, 1.55)]
    body = lathe(prof, segs=16, scale_xy=(1.05, 0.86))
    for v in body.verts:
        if v.co.y < 0:
            v.co.y *= 1.12
        else:
            v.co.y *= 0.86
    P.add("shirt", body)
    P.add("shirt", blob((0.0, 0.02, 1.44), 0.2, scale=(2.1, 1.12, 0.72), segs=12, rings=7))
    # Head
    HC = Vector((0.0, -0.05, 1.72))
    P.add("skin_m", tube([(0, 0.0, 1.48), (0, -0.03, 1.62)], [0.11, 0.1], segs=10))
    P.add("skin_m", blob(HC, 0.155, scale=(1.0, 0.95, 1.06), segs=14, rings=10))
    for sx in (-1, 1):
        P.add("skin_m", blob(HC + Vector((sx * 0.085, -0.075, -0.07)), 0.075, segs=8, rings=6))
        P.add("skin_m", blob(HC + Vector((sx * 0.152, 0.01, 0.0)), 0.04, scale=(0.5, 1.0, 1.25), segs=8, rings=5))
        P.add("eye", blob(HC + Vector((sx * 0.055, -0.138, 0.035)), 0.017, segs=6, rings=4))
        P.add("hair", tube([HC + Vector((sx * 0.02, -0.15, 0.075)), HC + Vector((sx * 0.065, -0.15, 0.085)),
                            HC + Vector((sx * 0.1, -0.12, 0.07))], [0.017, 0.016, 0.01], segs=5))
        P.add("hair", blob(HC + Vector((sx * 0.135, 0.04, 0.03)), 0.06, scale=(0.6, 1.0, 1.0), segs=8, rings=5,
                           rng=rng, jitter=0.1))
        must = [HC + Vector((sx * 0.012, -0.175, -0.045)), HC + Vector((sx * 0.065, -0.165, -0.055)),
                HC + Vector((sx * 0.12, -0.125, -0.085)), HC + Vector((sx * 0.155, -0.09, -0.14))]
        P.add("hair", tube(catmull(must, 2), [0.025, 0.028, 0.027, 0.022, 0.016, 0.01, 0.004], segs=7))
    P.add("skin_m", blob(HC + Vector((0, -0.175, -0.005)), 0.048, scale=(0.95, 1.05, 1.1), segs=8, rings=6))
    P.add("skin_m", blob(HC + Vector((0, -0.11, -0.115)), 0.065, scale=(1.1, 0.8, 0.7), segs=8, rings=5))
    # Arms: right holds a tankard, left hangs with a rag.
    for sx, (el, wr, hand) in ((1, ((0.47, -0.04, 1.14), (0.36, -0.3, 1.03), (0.33, -0.36, 1.01))),
                               (-1, ((-0.48, 0.02, 1.12), (-0.44, -0.1, 0.88), (-0.43, -0.13, 0.84)))):
        sh = Vector((sx * 0.38, 0.0, 1.43))
        el, wr, hand = Vector(el), Vector(wr), Vector(hand)
        P.add("shirt", tube([sh, sh.lerp(el, 0.5), el], [0.115, 0.105, 0.095], segs=10))
        P.add("shirt", torus(el, 0.1, 0.028, normal=(el - sh), seg=10, rseg=4))
        P.add("skin_m", tube([el, el.lerp(wr, 0.5), wr], [0.092, 0.085, 0.065], segs=9))
        P.add("skin_m", blob(hand, 0.068, scale=(0.95, 1.0, 1.15), segs=8, rings=6))
        P.add("skin_m", tube([hand + Vector((-sx * 0.04, -0.03, 0.02)), hand + Vector((-sx * 0.06, -0.07, 0.03))],
                             [0.025, 0.02], segs=6))
    # Tankard in the right hand (with foam).
    T = Vector((0.31, -0.45, 0.94))
    P.add("pewter", lathe([(0.0, 0.0), (0.062, 0.0), (0.066, 0.01), (0.06, 0.15), (0.066, 0.165), (0.054, 0.165),
                           (0.05, 0.14), (0.0, 0.14)], segs=12, center=T))
    for z in (0.03, 0.12):
        P.add("pewter", torus(T + Vector((0, 0, z)), 0.064, 0.006, seg=12, rseg=4))
    P.add("pewter", tube([T + Vector((0.055, 0.0, 0.13)), T + Vector((0.1, 0.0, 0.12)), T + Vector((0.1, 0.0, 0.04)),
                          T + Vector((0.055, 0.0, 0.03))], [0.01] * 4, segs=5))
    P.add("foam", blob(T + Vector((0, 0, 0.162)), 0.06, scale=(1.0, 1.0, 0.45), segs=10, rings=5, rng=rng, jitter=0.08))
    # Rag in the left hand.
    hand_l = Vector((-0.43, -0.13, 0.84))
    grid = [[hand_l + Vector((dx, -0.04, -0.02 - v * 0.24 + 0.02 * math.sin(dx * 40))) for dx in (-0.05, 0.0, 0.05)]
            for v in (0.0, 0.33, 0.66, 1.0)]
    P.add("apron", thick_sheet([[tuple(p) for p in row] for row in grid], 0.008))
    # Apron following the belly, straps and waist tie.
    def r_at(z):
        for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
            if z0 <= z <= z1:
                return lerp(r0, r1, (z - z0) / (z1 - z0))
        return prof[1][0]

    grid = []
    zs = [lerp(1.44, 0.44, k / 11) for k in range(12)]
    ymax = -0.37 * 0.86 * 1.12
    for z in zs:
        row = []
        hw = lerp(0.2, 0.33, smooth01((1.44 - z) / 0.42))
        for c in range(9):
            u = c / 8
            x = lerp(-hw, hw, u)
            if z > 0.86:
                r = r_at(z) * 1.05
                q = max(0.0, 1.0 - (x / max(r, 1e-3)) ** 2)
                y = -math.sqrt(q) * r_at(z) * 0.86 * 1.12 - 0.028
                if z < 1.0:
                    y = min(y, ymax - 0.028)
            else:
                y = ymax - 0.028 - 0.06 * (0.86 - z) + 0.03 * (u - 0.5) ** 2 * 4 * (0.86 - z)
            row.append((x, y, z))
        grid.append(row)
    P.add("apron", thick_sheet(grid, 0.014))
    P.add("apron", thick_sheet([[(x, -0.37 * 0.86 * 1.12 - 0.075 - 0.06 * (0.86 - z), z) for x in (-0.13, 0.0, 0.13)]
                                for z in (0.78, 0.62)], 0.012))
    for sx in (-1, 1):
        P.add("apron", tube([(sx * 0.19, -0.27, 1.44), (sx * 0.17, -0.18, 1.53), (sx * 0.1, -0.06, 1.58),
                             (0.0, 0.02, 1.6)], [0.014] * 4, segs=5, flatten=0.5))
    P.add("apron", tube(ring_pts((0, 0.0, 0.98), 0.39, 0.37, n=16), [0.018] * 16, segs=5, closed=True, up=Z,
                        flatten=1.6))
    # Leather belt and pouch
    P.add("leather", tube(ring_pts((0, 0.01, 0.86), 0.36, 0.33, n=16), [0.012] * 16, segs=5, closed=True, up=Z,
                          flatten=2.2))
    P.add("leather", cbox((0.3, -0.16, 0.8), (0.1, 0.07, 0.12), bev=0.015))
    # Extra ribcages bursting through: belly (chimes), left shoulder, back.
    for base, dirv, side, n, L, rb, ch in (((0.05, -0.42, 1.06), (0.1, -1.0, 0.32), X, 4, 0.27, 0.2, 7),
                                           ((-0.3, -0.12, 1.52), (-0.55, -0.35, 0.8), Y, 3, 0.27, 0.17, 4),
                                           ((0.3, -0.3, 0.74), (0.8, -0.65, -0.05), Z, 3, 0.2, 0.14, 4),
                                           ((0.08, 0.28, 1.3), (0.15, 1.0, 0.55), X, 4, 0.27, 0.19, 5)):
        bones, strings = ribcage(base, dirv, side, n, L, rb, rng=rng, chimes=ch)
        P.add("bone", bones)
        P.add("string", strings)
    # Torn apron flaps around the belly cage.
    for a in (0.3, 1.9, 3.3, 4.6):
        c = Vector((0.06, -0.425, 1.06)) + Vector((math.cos(a), 0, math.sin(a))) * 0.075
        o = Vector((math.cos(a), -0.6, math.sin(a))).normalized()
        g = [[c + Vector((-math.sin(a), 0, math.cos(a))) * w * 0.035 + o * v * 0.06 for w in (-1, 1)] for v in (0, 1)]
        P.add("apron", thick_sheet([[tuple(p) for p in row] for row in g], 0.01))
    return A


def build_collector():
    A = Asset("Collector", weight=1.5, tint="#5FD4FF",
              usage="'The Horologist' meta-progression vendor, ~2.2 m, hunched robed figure, static, pivot at the "
                    "feet, faces -Z. Emission = clockwork monocle lens + glowing cell vials in the backpack.")
    P = A.piece("Collector")
    rng = random.Random(17)
    # Robe: strongly hunched loft from a tattered hem to the shoulders.
    levels = [(0.02, -0.0, 0.06, 0.44, 0.39), (0.32, 0.0, 0.05, 0.37, 0.32), (0.62, 0.0, 0.03, 0.3, 0.26),
              (0.92, 0.0, 0.0, 0.26, 0.22), (1.15, 0.0, -0.05, 0.27, 0.22), (1.38, 0.0, -0.13, 0.29, 0.23),
              (1.56, 0.0, -0.24, 0.26, 0.2), (1.65, 0.0, -0.31, 0.13, 0.11)]
    rings = []
    n = 20
    for k, (z, cx, cy, rx, ry) in enumerate(levels):
        ring = []
        for i in range(n):
            a = TAU * i / n
            p = Vector((cx + math.cos(a) * rx, cy + math.sin(a) * ry, z))
            if 1.1 < z < 1.6 and math.sin(a) > 0:
                p.y += 0.1 * math.sin(a) ** 2
                p.z += 0.04 * math.sin(a) ** 2
            if k == 0:
                p.z += (0.06 if i % 2 else 0.0) + rng.uniform(-0.015, 0.015)
            ring.append(p)
        rings.append(ring)
    P.add("robe", loft(rings, cap0=True, cap1=True))
    # Mantle / capelet with a gold trim.
    mrings = []
    for z, cy, rx, ry in ((1.65, -0.31, 0.17, 0.15), (1.56, -0.24, 0.31, 0.26), (1.43, -0.15, 0.36, 0.31),
                          (1.3, -0.08, 0.38, 0.33)):
        mr = []
        for i in range(n):
            a = TAU * i / n
            p = Vector((math.cos(a) * rx, cy + math.sin(a) * ry, z))
            if 1.1 < z < 1.6 and math.sin(a) > 0:
                p.y += 0.1 * math.sin(a) ** 2
                p.z += 0.04 * math.sin(a) ** 2
            if z < 1.32:
                p.z += 0.05 * (i % 2) - 0.02 * math.sin(a * 3)
            mr.append(p)
        mrings.append(mr)
    P.add("mantle", thick_tube(mrings, 0.022))
    # Head inside a deep pointed hood, thrust forward and down.
    HC = Vector((0.0, -0.45, 1.69))
    fwd = Vector((0.0, -0.84, -0.42)).normalized()
    up = Vector((0.0, -0.42, 0.9)).normalized()
    side = fwd.cross(up).normalized()
    P.add("skin_h", tube([Vector((0, -0.28, 1.6)), HC + Vector((0, 0.05, -0.05))], [0.07, 0.06], segs=8))
    P.add("skin_h", blob(HC, 0.105, scale=(0.9, 1.0, 1.1), segs=12, rings=8))
    P.add("skin_h", cone(HC + fwd * 0.09, fwd * 0.8 - up * 0.6, 0.17, 0.026, segs=7))
    P.add("skin_h", blob(HC + fwd * 0.055 - up * 0.085, 0.048, scale=(1.0, 1.0, 0.8), segs=8, rings=5))
    for k in range(5):
        a = (k - 2) * 0.35
        b0 = HC + fwd * 0.05 - up * 0.1 + side * a * 0.06
        P.add("hair", cone(b0, -up * 0.9 + fwd * 0.3 + side * a * 0.4, 0.09 + 0.03 * (k % 2), 0.014, segs=5))
    eye_l = HC + fwd * 0.088 + up * 0.03 + side * 0.042
    eye_r = HC + fwd * 0.088 + up * 0.03 - side * 0.042
    P.add("eye", blob(eye_l, 0.016, segs=6, rings=4))
    # Clockwork monocle: geared rim, telescoping tube, glowing lenses.
    mc = eye_r + fwd * 0.012
    P.add("brass", torus(mc, 0.045, 0.009, normal=fwd, seg=14, rseg=5))
    for k in range(12):
        a = TAU * k / 12
        d = side * math.cos(a) + fwd.cross(side) * math.sin(a)
        P.add("brass", translate(cbox((0, 0, 0), (0.014, 0.014, 0.014)), mc + d * 0.058))
    P.add("brass", lathe([(0.036, 0.0), (0.036, 0.035), (0.03, 0.038), (0.03, 0.07), (0.035, 0.074)], segs=10,
                         axis=fwd, center=mc, cap0=False, cap1=False))
    P.add("lens", lathe([(0.0, 0.0), (0.037, 0.0), (0.036, 0.006), (0.0, 0.012)], segs=10, axis=fwd, center=mc))
    P.add("lens", lathe([(0.0, 0.0), (0.03, 0.0), (0.029, 0.005), (0.0, 0.009)], segs=10, axis=fwd,
                        center=mc + fwd * 0.07))
    P.add("brass", tube([eye_r - side * 0.035, HC - side * 0.11 + up * 0.04, HC - side * 0.12 - fwd * 0.05],
                        [0.004] * 3, segs=4))
    # Hood shell (open at the face and underneath) ending in a drooping point.
    grid = []
    for vi in range(9):
        v = vi / 8
        th = lerp(0.6, 2.85, v)
        row = []
        for ui in range(11):
            u = ui / 10
            ph = lerp(-2.2, 2.2, u)
            rr = 0.2 + 0.035 * v
            pinch = 1.0 - 0.7 * max(0.0, (v - 0.55) / 0.45) ** 1.3
            dirv = fwd * math.cos(th) + (up * math.cos(ph) * pinch + side * math.sin(ph) * pinch) * math.sin(th)
            p = HC + dirv * rr
            if v > 0.5:
                k = (v - 0.5) / 0.5
                p += up * 0.16 * k * k - fwd * 0.12 * k
            if vi == 0:
                p += fwd * 0.025
            row.append(tuple(p))
        grid.append(row)
    P.add("robe", thick_sheet(grid, 0.024, normal_hint=tuple(-fwd)))
    # Long bell sleeves and syringe-fingered hands (one beckoning, one lowered).
    for sx, wr, fdir in ((1, Vector((0.3, -0.66, 1.4)), Vector((0.12, -0.55, 0.8))),
                         (-1, Vector((-0.33, -0.6, 1.12)), Vector((-0.18, -0.6, -0.65)))):
        sh = Vector((sx * 0.25, -0.25, 1.54))
        el = Vector((sx * 0.4, -0.34, 1.28))
        pts = catmull([sh, el, wr], 3)
        fr = frames(pts, X)
        srings = []
        for k, (p, t, s_, nn) in enumerate(fr):
            r = lerp(0.075, 0.14, (k / (len(fr) - 1)) ** 1.6)
            srings.append([p + s_ * math.cos(TAU * i / 12) * r + nn * math.sin(TAU * i / 12) * r for i in range(12)])
        P.add("robe", thick_tube(srings, 0.016))
        P.add("mantle", torus(pts[-1], 0.14, 0.017, normal=fr[-1][1], seg=12, rseg=4))
        palm = wr + fr[-1][1] * 0.035
        P.add("skin_h", blob(palm, 0.055, scale=(1.0, 1.0, 0.7), segs=8, rings=5))
        f = fdir.normalized()
        fs = f.cross(Z).normalized()
        for i in range(5):
            spread = (i - 2) * 0.34
            d = (f + fs * spread * 0.9 + Vector((0, 0, 0.12 * abs(i - 2)))).normalized()
            base = palm + fs * (i - 2) * 0.022 + d * 0.035
            ln = 0.14 if i in (1, 2, 3) else 0.1
            P.add("skin_h", blob(base, 0.016, segs=6, rings=4))
            P.add("syringe", lathe([(0.0125, 0.0), (0.0135, 0.012), (0.0135, ln), (0.009, ln + 0.01)], segs=6,
                                   axis=d, center=base + d * 0.01))
            P.add("brass", torus(base + d * (0.012 + ln * 0.5), 0.015, 0.0035, normal=d, seg=8, rseg=3))
            P.add("brass", torus(base + d * (0.014 + ln), 0.011, 0.003, normal=d, seg=8, rseg=3))
            P.add("needle", cone(base + d * (0.018 + ln), d, 0.1, 0.004, segs=4))
    # Belt, pouches, pocket watch, shoe tips.
    P.add("leather", tube(ring_pts((0, -0.02, 1.0), 0.265, 0.225, n=16), [0.014] * 16, segs=5, closed=True, up=Z,
                          flatten=2.0))
    for x, y in ((0.2, -0.15), (-0.19, -0.16)):
        P.add("leather", cbox((x, y - 0.03, 0.93), (0.1, 0.06, 0.11), bev=0.015))
    P.add("brass", lathe([(0.0, 0.0), (0.05, 0.0), (0.055, 0.012), (0.05, 0.022), (0.0, 0.024)], segs=14,
                         axis=(0, -1, 0), center=(0.04, -0.29, 0.8)))
    P.add("lens", lathe([(0.0, 0.0), (0.04, 0.0), (0.0, 0.004)], segs=14, axis=(0, -1, 0), center=(0.04, -0.313, 0.8)))
    P.add("brass", tube([(0.04, -0.29, 0.86), (0.07, -0.26, 0.93), (0.11, -0.23, 0.99)], [0.004] * 3, segs=4))
    for sx in (-1, 1):
        P.add("leather", blob((sx * 0.13, -0.38, 0.03), 0.06, scale=(0.8, 1.7, 0.5), segs=8, rings=5))
    # Backpack: wooden rack of glowing cell vials, a big dome jar, brass pipes and a gear, straps.
    bx0, bx1, by0, by1 = -0.38, 0.38, 0.2, 0.58
    for x in (bx0, bx1):
        for y in (by0, by1):
            P.add("wood_dark", cbox((x, y, 1.4), (0.055, 0.055, 1.12), bev=0.01))
    for z in (0.86, 1.22, 1.58, 1.94):
        P.add("wood_dark", box((bx0, by0 - 0.03, z - 0.03), (bx1, by1 + 0.03, z + 0.01), bev=0.008))
    for z in (1.22, 1.58):
        P.add("brass", cbox((0, by0 - 0.012, z + 0.09), (0.76, 0.014, 0.024)))
    for z in (0.87, 1.23, 1.59):
        for i, x in enumerate((-0.27, -0.09, 0.09, 0.27)):
            hgt = rng.uniform(0.24, 0.31)
            r = rng.uniform(0.052, 0.066)
            c = (x + rng.uniform(-0.01, 0.01), (by0 + by1) * 0.5 + rng.uniform(-0.03, 0.03), z + 0.01)
            P.add("vials", lathe([(0.0, 0.0), (r, 0.0), (r * 1.06, hgt * 0.5), (r, hgt * 0.88), (r * 0.6, hgt)],
                                 segs=8, center=c, cap1=False))
            P.add("brass", lathe([(r * 0.62, hgt - 0.012), (r * 0.7, hgt + 0.02), (0.0, hgt + 0.028)], segs=8,
                                 center=c))
    JC = Vector((0.0, (by0 + by1) * 0.5, 1.95))
    P.add("vials", lathe([(0.0, 0.0), (0.17, 0.0), (0.19, 0.06), (0.175, 0.13), (0.12, 0.18), (0.075, 0.2)], segs=12,
                         center=JC, cap1=False))
    P.add("brass", lathe([(0.08, 0.18), (0.095, 0.2), (0.09, 0.22), (0.03, 0.235), (0.0, 0.24)], segs=12, center=JC))
    P.add("brass", torus(JC + Vector((0, 0, 0.255)), 0.035, 0.007, normal=(1, 0, 0), seg=10, rseg=4))
    P.add("brass", tube(catmull([JC + Vector((0.18, 0, 0.1)), JC + Vector((0.32, 0.02, 0.05)),
                                 Vector((0.44, 0.4, 1.6)), Vector((0.43, 0.4, 1.1))], 3), [0.017] * 10, segs=6))
    P.add("brass", tube(catmull([JC + Vector((-0.18, 0, 0.08)), JC + Vector((-0.32, -0.02, 0.0)),
                                 Vector((-0.44, 0.38, 1.5))], 3), [0.015] * 7, segs=6))
    P.add("brass", gear((0.0, 0.0, 1.4), 10, 0.11, 0.14, 0.065, by1 + 0.03, by1 + 0.07, spokes=3, hub=0.025))
    for sx in (-1, 1):
        P.add("leather", tube(catmull([Vector((sx * 0.2, by0, 1.86)), Vector((sx * 0.17, -0.2, 1.64)),
                                       Vector((sx * 0.22, -0.34, 1.4)), Vector((sx * 0.24, -0.18, 1.08)),
                                       Vector((sx * 0.24, by0, 0.94))], 2), [0.013] * 9, segs=4, flatten=3.0, up=Y))
    return A


def props_assets():
    assets = [build_teleporter(), build_chest(), build_pedestal(), build_coin(), build_goldpile(), build_fountain(),
              build_loretablet(), build_exitdoor(), build_merchantstall(), build_merchant(), build_collector()]
    for a in assets:
        a.floor = a.name != "Coin"   # floor-pivoted props: nothing below z = 0
    return assets


PROPS_HP = {
    "stone": (0.012, 1), "stone_moss": (0.012, 1), "tablet": (0.012, 1), "wood_v": (0.006, 1), "wood_h": (0.006, 1),
    "wood_dark": (0.006, 1), "iron": (0.004, 1), "brass": (0.004, 1), "gold": (0.0015, 1), "gold_heap": (0.0, 1),
    "glow": (0.0, 1), "door_light": (0.0, 0), "lock_glow": (0.0, 1), "blood": (0.0, 1), "velvet": (0.0, 1),
    "canopy": (0.0, 1), "drape": (0.0, 1), "burlap": (0.0, 1), "gem": (0.0008, 0), "potion": (0.0, 1),
    "lantern": (0.0, 1), "sign": (0.006, 1),
}
PROPS_MAT_WEIGHT = {"tablet": 2.8, "sign": 1.4, "lens": 2.0, "eye": 1.5, "skin_m": 1.3, "skin_h": 1.3,
                    "door_light": 0.25, "gold": 1.2, "stone": 0.95, "glow": 0.8}
NPC = ("Merchant", "Collector")


def main():
    args = ba.cli_args()
    if "--verify" in args:
        ok = ba.verify_kit(MANIFEST)
        print("[props] verify", "PASSED" if ok else "FAILED")
        return
    ba.run_kit(assets_fn=props_assets, materials_fn=props_materials, atlas="Props", tex_dir=TEX_DIR, fbx_dir=OUT_DIR,
               manifest_path=MANIFEST, prev_dir=PREV, generator="Tools/Blender/build_props.py", size=2048,
               hp_cfg=PROPS_HP, flat=("gem",), mat_weight=PROPS_MAT_WEIGHT,
               budget=lambda a: 9000 if a.name in NPC else 6000,
               emission_colors={"Teleporter ring channel": "#7FE8FF", "Chest lock": "#C79BFF",
                                "Fountain_Liquid": "#FF2A3A", "LoreTablet glyphs": "#7FE8FF",
                                "ExitDoor crack light": "#FFC870", "MerchantStall lantern": "#FFB040",
                                "Collector monocle + cell vials": "#5FD4FF"},
               views=("three_quarter", "front"), cols=4, default_hp=(0.004, 1))


if __name__ == "__main__":
    main()
