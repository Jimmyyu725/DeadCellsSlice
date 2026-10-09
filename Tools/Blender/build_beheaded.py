"""The Beheaded (The Prisoner) -- model, rig, bake, animate, export.

Run headless:
    Blender -b --factory-startup -P Tools/Blender/build_beheaded.py
Or step by step inside a live Blender session (MCP):
    import build_beheaded as bb; bb.step_model(); bb.step_rig(); ...
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dc_common as dc  # noqa: E402
import dc_rig as rig  # noqa: E402

NAME = "Beheaded"
OUT_DIR = dc.ART_ROOT / "Characters" / NAME
TEX_DIR = OUT_DIR / "Textures"
BLEND_PATH = dc.PROJECT_ROOT / "Tools" / "Blend" / f"{NAME}.blend"

FLAME_HEX = "#9B5DE5"  # occult purple (toxic green #38B000 is the alt preset)

# ---------------------------------------------------------------------------
# Skeleton (left side + centre; right side mirrored)
# ---------------------------------------------------------------------------

JOINTS_L = {
    "root": ((0, 0, 0), (0, 0, 0.25)),
    "hips": ((0, 0, 0.95), (0, 0, 1.06)),
    "spine": ((0, 0, 1.06), (0, 0.0, 1.22)),
    "chest": ((0, 0, 1.22), (0, 0, 1.44)),
    "neck": ((0, 0, 1.44), (0, -0.01, 1.53)),
    "head": ((0, -0.01, 1.53), (0, -0.02, 1.76)),
    "head_socket": ((0, -0.02, 1.60), (0, -0.02, 1.70)),
    "shoulder.L": ((0.04, 0.0, 1.40), (0.19, 0.01, 1.41)),
    "upper_arm.L": ((0.21, 0.01, 1.40), (0.27, 0.02, 1.13)),
    "forearm.L": ((0.27, 0.02, 1.13), (0.29, -0.02, 0.885)),
    "hand.L": ((0.29, -0.02, 0.885), (0.295, -0.03, 0.79)),
    "thigh.L": ((0.10, 0, 0.94), (0.11, -0.03, 0.52)),
    "shin.L": ((0.11, -0.03, 0.52), (0.11, 0.02, 0.11)),
    "foot.L": ((0.11, 0.02, 0.11), (0.11, -0.14, 0.03)),
    "coat_L_01": ((0.10, 0.13, 0.95), (0.12, 0.16, 0.84)),
    "coat_L_02": ((0.12, 0.16, 0.84), (0.13, 0.19, 0.72)),
    "coat_L_03": ((0.13, 0.19, 0.72), (0.14, 0.21, 0.58)),
    "scarf_01": ((0.04, 0.10, 1.45), (0.06, 0.19, 1.38)),
    "scarf_02": ((0.06, 0.19, 1.38), (0.08, 0.28, 1.18)),
    "scarf_03": ((0.08, 0.28, 1.18), (0.095, 0.31, 0.96)),
    "scarf_04": ((0.095, 0.31, 0.96), (0.105, 0.37, 0.76)),
}
EXTRA_JOINTS = {
    # Shield face normal points backward at rest -> forward when the forearm is raised.
    "shield_socket": ((0.29, 0.05, 1.0), (0.29, 0.15, 1.0)),
    # Blade points forward at rest.
    "weapon_socket": ((-0.295, -0.03, 0.83), (-0.295, -0.13, 0.83)),
}
PARENTS = {
    "root": None, "hips": "root", "spine": "hips", "chest": "spine", "neck": "chest",
    "head": "neck", "head_socket": "head",
    "scarf_01": "neck", "scarf_02": "scarf_01", "scarf_03": "scarf_02", "scarf_04": "scarf_03",
    "shield_socket": "forearm.L", "weapon_socket": "hand.R",
}
for s in ("L", "R"):
    PARENTS.update({
        f"shoulder.{s}": "chest", f"upper_arm.{s}": f"shoulder.{s}", f"forearm.{s}": f"upper_arm.{s}",
        f"hand.{s}": f"forearm.{s}", f"thigh.{s}": "hips", f"shin.{s}": f"thigh.{s}", f"foot.{s}": f"shin.{s}",
        f"coat_{s}_01": "hips", f"coat_{s}_02": f"coat_{s}_01", f"coat_{s}_03": f"coat_{s}_02",
    })
NON_DEFORM = ("root", "shield_socket", "weapon_socket")


def joints():
    j = rig.mirror_joints(JOINTS_L)
    j.update(EXTRA_JOINTS)
    return j


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def make_materials():
    M = {}
    M["cloth"] = dc.make_material(
        "M_Cloth", "#1B263B", dark="#0B111C", light="#2E4466", noise_scale=7, noise_amt=0.7,
        rough=0.85, edge_wear="#47648C", edge_wear_amt=0.45, cavity_dirt=0.55, bump_scale=120,
        bump_strength=0.18, bevel_radius=0.008)
    M["leather"] = dc.make_material(
        "M_Leather", "#4A3122", dark="#22140C", light="#73513A", noise_scale=10, noise_amt=0.8,
        rough=0.62, edge_wear="#B08A62", edge_wear_amt=0.8, cavity_dirt=0.7, bump_scale=60,
        bump_strength=0.3, bevel_radius=0.01)
    M["leather_dark"] = dc.make_material(
        "M_LeatherDark", "#2E2019", dark="#140D09", light="#4E382A", noise_scale=12, noise_amt=0.7,
        rough=0.55, edge_wear="#7C6048", edge_wear_amt=0.9, cavity_dirt=0.6, bump_scale=70,
        bump_strength=0.25, bevel_radius=0.012)
    M["iron"] = dc.make_material(
        "M_Iron", "#58626E", dark="#272D35", light="#8F9AA6", metal=1.0, rough=0.38, rough_var=0.15,
        noise_scale=14, noise_amt=0.75, edge_wear="#DDE5EC", edge_wear_amt=1.0, cavity_dirt=0.8,
        bump_scale=30, bump_strength=0.2, bevel_radius=0.012)
    M["scarf"] = dc.make_material(
        "M_Scarf", "#780016", dark="#33000A", light="#B0162F", noise_scale=6, noise_amt=0.85,
        rough=0.8, edge_wear="#D23A4E", edge_wear_amt=0.6, cavity_dirt=0.6, bump_scale=90,
        bump_strength=0.22, bevel_radius=0.01)
    M["bandage"] = dc.make_material(
        "M_Bandage", "#C2AE8E", dark="#7E6B52", light="#E4D7BE", noise_scale=9, noise_amt=0.8,
        rough=0.9, stripes=("z", 38.0, 0.16, "#6E5B44"), cavity_dirt=0.5, bump_scale=140,
        bump_strength=0.25, bevel_radius=0.006)
    M["sole"] = dc.make_material(
        "M_Sole", "#17100C", dark="#0A0705", light="#2C211A", noise_scale=20, rough=0.7,
        cavity_dirt=0.3, bevel_radius=0.008)
    M["neck_glow"] = dc.make_material(
        "M_NeckGlow", "#2A1030", dark="#12061A", light="#3D1A45", rough=0.6,
        emission="#FFFFFF", emission_strength=3.0)
    M["flame"] = dc.make_flat_material("M_Flame", FLAME_HEX, emission=FLAME_HEX, strength=6.0)
    M["eye"] = dc.make_flat_material("M_FlameEye", "#FFF4D6", emission="#FFF4D6", strength=12.0)
    M["smoke"] = dc.make_flat_material("M_Smoke", "#3A2A4A")
    return M


# ---------------------------------------------------------------------------
# Modelling helpers
# ---------------------------------------------------------------------------

def tag(obj, mat, bones=None, rigid=None, power=6.0):
    dc.assign_material(obj, mat)
    if rigid:
        obj["dc_rigid"] = rigid
    else:
        obj["dc_bones"] = ",".join(bones)
    obj["dc_power"] = power
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def lerp(a, b, t):
    return a + (b - a) * t


def limb(name, p0, p1, radii, segments=12, flatten=1.0, up=Vector((0, 1, 0))):
    """Tube between two joints with len(radii) rings."""
    p0, p1 = Vector(p0), Vector(p1)
    n = len(radii)
    pts = [p0.lerp(p1, i / (n - 1)) for i in range(n)]
    return dc.tube_along(name, pts, radii, segments=segments, up=up, flatten=flatten)


def torus(name, center, major, minor, maj_seg=24, min_seg=8, scale=(1, 1, 1), rot=(0, 0, 0)):
    bm = bmesh.new()
    verts = []
    for i in range(maj_seg):
        a = math.tau * i / maj_seg
        ring = []
        for j in range(min_seg):
            b = math.tau * j / min_seg
            r = major + minor * math.cos(b)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), minor * math.sin(b))))
        verts.append(ring)
    for i in range(maj_seg):
        i2 = (i + 1) % maj_seg
        for j in range(min_seg):
            j2 = (j + 1) % min_seg
            bm.faces.new((verts[i][j], verts[i2][j], verts[i2][j2], verts[i][j2]))
    rot_m = (Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X"))
    scale_m = Matrix.Diagonal((*scale, 1.0))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ rot_m @ scale_m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dc.mesh_object(name, bm)


def solidify(obj, thickness, offset=-1.0):
    dc.add_modifier(obj, "SOLIDIFY", thickness=thickness, offset=offset, use_even_offset=True)
    dc.apply_all_modifiers(obj)


def delete_faces(obj, predicate):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    kill = [f for f in bm.faces if predicate(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()


def transform(obj, matrix):
    obj.data.transform(matrix)
    obj.data.update()


# ---------------------------------------------------------------------------
# Step 1: model
# ---------------------------------------------------------------------------

def build_body(M):
    parts = []
    rnd = random.Random(7)

    # --- Torso (navy under-shirt) ------------------------------------------
    torso = dc.lathe("Torso", [
        (0.150, 0.90), (0.165, 0.96), (0.150, 1.04), (0.150, 1.10), (0.180, 1.20), (0.205, 1.29),
        (0.210, 1.36), (0.175, 1.425), (0.110, 1.475), (0.075, 1.52)], segments=16, scale_xy=(1.0, 0.70))

    def torso_shape(v):
        if 1.16 < v.z < 1.42 and v.y < 0:
            v.y *= 1.0 + 0.16 * math.sin(math.pi * (v.z - 1.16) / 0.26)
        if v.z > 1.33:
            v.x *= 1.0 + 0.10 * min(1.0, (v.z - 1.33) / 0.08) * (1.0 if v.z < 1.45 else 0.3)
        if v.y > 0:
            v.y *= 0.92
        return v
    dc.deform(torso, torso_shape)
    dc.subdivide(torso, 1)
    parts.append(tag(torso, M["cloth"], ["hips", "spine", "chest", "neck"]))

    # --- Leather tunic: vest + skirt ----------------------------------------
    vest = dc.lathe("TunicVest", [
        (0.168, 0.985), (0.172, 1.04), (0.163, 1.10), (0.190, 1.19), (0.218, 1.28), (0.223, 1.35),
        (0.190, 1.415), (0.150, 1.445)], segments=20, scale_xy=(1.03, 0.77), cap_top=False, cap_bottom=False)

    def vest_shape(v):
        if 1.16 < v.z < 1.42 and v.y < 0:
            v.y *= 1.0 + 0.16 * math.sin(math.pi * (v.z - 1.16) / 0.26)
        if v.y > 0:
            v.y *= 0.93
        # V neckline: drop the front of the top rings.
        if v.z > 1.33 and v.y < -0.02:
            v.z -= 0.12 * max(0.0, 1.0 - abs(v.x) / 0.16) * min(1.0, (v.z - 1.33) / 0.1)
        return v
    dc.deform(vest, vest_shape)
    solidify(vest, 0.014, offset=1.0)
    dc.subdivide(vest, 1)
    parts.append(tag(vest, M["leather"], ["hips", "spine", "chest"]))

    skirt = dc.lathe("TunicSkirt", [
        (0.176, 1.01), (0.188, 0.94), (0.202, 0.86), (0.218, 0.78), (0.232, 0.71)],
        segments=24, scale_xy=(1.02, 0.80), cap_top=False, cap_bottom=False)

    def skirt_shape(v):
        if v.y > 0.03 and v.z < 0.95:
            depth = (0.95 - v.z) / 0.24
            v.z -= 0.20 * depth * depth * min(1.0, v.y / 0.12)
            v.y += 0.05 * depth
        return v
    dc.deform(skirt, skirt_shape)
    delete_faces(skirt, lambda c: (c.y < -0.06 and abs(c.x) < 0.07 and c.z < 0.97)
                 or (c.y > 0.06 and abs(c.x) < 0.035 and c.z < 0.88))
    # Ragged hem.
    for v in skirt.data.vertices:
        if v.co.z < 0.73:
            v.co.z += rnd.uniform(-0.035, 0.03)
    solidify(skirt, 0.012, offset=1.0)
    parts.append(tag(skirt, M["leather"], ["hips", "thigh.L", "thigh.R", "coat_L_01", "coat_L_02",
                                           "coat_L_03", "coat_R_01", "coat_R_02", "coat_R_03"], power=5))

    # --- Belt, buckle, pouches ---------------------------------------------
    belt = torus("Belt", Vector((0, 0.0, 0.995)), 0.178, 0.026, 28, 6, scale=(1.0, 0.78, 1.0))
    dc.deform(belt, lambda v: Vector((v.x, v.y, 0.995 + (v.z - 0.995) * 1.6)))
    parts.append(tag(belt, M["leather_dark"], rigid="hips"))
    buckle = dc.box("Buckle", (0.075, 0.03, 0.07), (0.0, -0.145, 0.995), bevel=0.008)
    parts.append(tag(buckle, M["iron"], rigid="hips"))
    for i, (x, y) in enumerate(((0.135, -0.085), (-0.16, -0.03), (0.15, 0.07))):
        pouch = dc.box(f"Pouch{i}", (0.075, 0.05, 0.085), (x, y, 0.945), bevel=0.012)
        ang = math.atan2(y, x) + math.pi / 2
        transform(pouch, Matrix.Translation((x, y, 0.945)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Translation((-x, -y, -0.945)))
        parts.append(tag(pouch, M["leather"], rigid="hips"))

    # --- Bandolier strap over the left shoulder ------------------------------
    front = [(0.135, -0.04, 1.44), (0.10, -0.135, 1.36), (0.03, -0.172, 1.27), (-0.05, -0.165, 1.17),
             (-0.12, -0.14, 1.08), (-0.172, -0.085, 1.0)]
    back = [(0.135, 0.04, 1.44), (0.09, 0.115, 1.34), (0.0, 0.135, 1.24), (-0.08, 0.13, 1.14),
            (-0.15, 0.10, 1.05), (-0.185, 0.03, 0.99)]
    strap_f = dc.tube_along("StrapF", front, [0.026] * len(front), segments=8, up=Vector((0, -1, 0)), flatten=0.28)
    strap_b = dc.tube_along("StrapB", back, [0.026] * len(back), segments=8, up=Vector((0, 1, 0)), flatten=0.28)
    strap_top = dc.tube_along("StrapTop", [(0.135, -0.05, 1.435), (0.15, 0.0, 1.455), (0.135, 0.05, 1.435)],
                              [0.026] * 3, segments=8, up=Vector((0, 0, 1)), flatten=0.28)
    for s_ in (strap_f, strap_b, strap_top):
        parts.append(tag(s_, M["leather_dark"], ["spine", "chest"]))
    ring = torus("StrapRing", Vector((0.065, -0.16, 1.315)), 0.024, 0.006, 12, 6, rot=(math.pi / 2, 0, 0))
    parts.append(tag(ring, M["iron"], rigid="chest"))

    # --- Pauldrons -----------------------------------------------------------
    for side, sx, scale in (("L", 1.0, 1.15), ("R", -1.0, 0.95)):
        c = Vector((0.225 * sx, 0.005, 1.445))
        dome = dc.lathe(f"Pauldron{side}", [
            (0.0, 0.075), (0.045, 0.072), (0.090, 0.055), (0.120, 0.025), (0.135, -0.010), (0.140, -0.040)],
            segments=16, scale_xy=(1.0, 0.92), cap_bottom=False)
        solidify(dome, 0.013, offset=1.0)
        lame = dc.lathe(f"PauldronLame{side}", [(0.146, -0.035), (0.150, -0.075), (0.145, -0.095)],
                        segments=16, scale_xy=(1.0, 0.92), cap_top=False, cap_bottom=False)
        delete_faces(lame, lambda cc: cc.x < -0.03)
        solidify(lame, 0.011, offset=1.0)
        lame2 = dc.lathe(f"PauldronLameB{side}", [(0.140, -0.085), (0.143, -0.125), (0.137, -0.14)],
                         segments=16, scale_xy=(1.0, 0.9), cap_top=False, cap_bottom=False)
        delete_faces(lame2, lambda cc: cc.x < 0.0)
        solidify(lame2, 0.011, offset=1.0)
        rivets = []
        for k in range(6):
            a = math.radians(-70 + k * 28)
            rv = dc.ico(f"Rivet{side}{k}", 0.009, (0.128 * math.cos(a), 0.128 * 0.92 * math.sin(a), 0.0), subdiv=1)
            rivets.append(rv)
        piece = dc.join([dome, lame, lame2] + rivets, f"Pauldron{side}")
        m = Matrix.Translation(c) @ Matrix.Rotation(math.radians(28 * sx), 4, "Y") @ Matrix.Diagonal((scale * sx * 1.08, scale, scale * 0.78, 1))
        transform(piece, m)
        if sx < 0:
            # Mirroring flipped the winding.
            piece.data.flip_normals()
        parts.append(tag(piece, M["iron"], [f"shoulder.{side}", f"upper_arm.{side}"], power=10))

        # Strap holding the pauldron.
        strap = torus(f"PauldronStrap{side}", Vector((0.255 * sx, 0.012, 1.29)), 0.066, 0.011, 16, 5,
                      scale=(1.0, 1.0, 0.55), rot=(0, math.radians(18 * sx), 0))
        parts.append(tag(strap, M["leather_dark"], [f"upper_arm.{side}"], power=6))

    # --- Arms ----------------------------------------------------------------
    for side, sx in (("L", 1.0), ("R", -1.0)):
        def P(x, y, z):
            return Vector((x * sx, y, z))
        sleeve = limb(f"Sleeve{side}", P(0.205, 0.01, 1.43), P(0.272, 0.02, 1.10),
                      [0.074, 0.078, 0.072, 0.064, 0.058, 0.056], segments=12)
        parts.append(tag(sleeve, M["cloth"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        wrap = limb(f"ForearmWrap{side}", P(0.27, 0.02, 1.15), P(0.289, -0.018, 0.905),
                    [0.058, 0.060, 0.056, 0.052, 0.048, 0.046, 0.046], segments=12)
        dc.jitter(wrap, 0.002, seed=11 if sx > 0 else 12)
        parts.append(tag(wrap, M["bandage"], [f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"]))
        cuff = limb(f"Cuff{side}", P(0.287, -0.014, 0.935), P(0.29, -0.02, 0.885), [0.054, 0.056, 0.053], segments=12)
        parts.append(tag(cuff, M["leather_dark"], [f"forearm.{side}", f"hand.{side}"], power=8))
        # Gloved fist: knuckle row runs along Y (grip axis points forward).
        fist = dc.box(f"Fist{side}", (0.07, 0.098, 0.088), (0.0, 0.0, 0.0), bevel=0.022, segments=2)
        dc.deform(fist, lambda v: Vector((v.x * (1.0 - 0.25 * max(0.0, -v.z) / 0.044), v.y, v.z)))
        thumb = dc.box(f"Thumb{side}", (0.03, 0.05, 0.03), (0.032, -0.03, 0.02), bevel=0.01)
        knuck = dc.box(f"Knuckle{side}", (0.062, 0.09, 0.022), (-0.004, 0.0, -0.035), bevel=0.008)
        hand = dc.join([fist, thumb, knuck], f"Hand{side}")
        transform(hand, Matrix.Translation(P(0.295, -0.03, 0.835)) @ Matrix.Diagonal((sx, 1, 1, 1)))
        if sx < 0:
            hand.data.flip_normals()
        parts.append(tag(hand, M["leather_dark"], rigid=f"hand.{side}"))

    # --- Legs ----------------------------------------------------------------
    for side, sx in (("L", 1.0), ("R", -1.0)):
        def P(x, y, z):
            return Vector((x * sx, y, z))
        thigh = limb(f"Thigh{side}", P(0.098, 0.0, 0.99), P(0.11, -0.03, 0.49),
                     [0.098, 0.096, 0.088, 0.078, 0.068, 0.062], segments=12)
        parts.append(tag(thigh, M["cloth"], ["hips", f"thigh.{side}", f"shin.{side}"]))
        shin = limb(f"Shin{side}", P(0.11, -0.03, 0.54), P(0.11, 0.0, 0.31), [0.064, 0.060, 0.056, 0.054], segments=12)
        parts.append(tag(shin, M["cloth"], [f"thigh.{side}", f"shin.{side}"]))
        calf = limb(f"CalfWrap{side}", P(0.11, -0.002, 0.355), P(0.11, 0.018, 0.17),
                    [0.058, 0.060, 0.056, 0.051, 0.048], segments=12)
        dc.jitter(calf, 0.002, seed=21 if sx > 0 else 22)
        parts.append(tag(calf, M["bandage"], [f"shin.{side}", f"foot.{side}"]))
        knee = dc.lathe(f"Knee{side}", [(0.0, 0.03), (0.035, 0.026), (0.055, 0.008), (0.06, -0.012)],
                        segments=12, scale_xy=(1.0, 0.8), cap_bottom=False)
        solidify(knee, 0.008, offset=1.0)
        transform(knee, Matrix.Translation(P(0.11, -0.085, 0.52)) @ Matrix.Rotation(math.radians(-80), 4, "X"))
        parts.append(tag(knee, M["iron"], [f"thigh.{side}", f"shin.{side}"], power=8))
        # Boot: shaft + foot + sole.
        shaft = dc.lathe(f"BootShaft{side}", [(0.060, 0.04), (0.064, 0.10), (0.067, 0.17), (0.080, 0.215),
                                              (0.083, 0.24), (0.074, 0.25)], segments=14, scale_xy=(1.0, 1.1),
                         cap_top=False)
        transform(shaft, Matrix.Translation(P(0.11, 0.025, 0.0)))
        foot = dc.box(f"BootFoot{side}", (0.105, 0.25, 0.09), (0.0, 0.0, 0.0), bevel=0.03, segments=3)

        def foot_shape(v):
            t = max(0.0, (-v.y - 0.03) / 0.095)  # 0 at mid, 1 at toe
            v.x *= 1.0 - 0.18 * t
            if v.z > 0:
                v.z *= 1.0 - 0.45 * t
            return v
        dc.deform(foot, foot_shape)
        transform(foot, Matrix.Translation(P(0.11, -0.055, 0.052)))
        sole = dc.box(f"Sole{side}", (0.112, 0.262, 0.026), P(0.11, -0.058, 0.013), bevel=0.008)
        boot = dc.join([shaft, foot], f"Boot{side}")
        parts.append(tag(boot, M["leather_dark"], [f"shin.{side}", f"foot.{side}"], power=8))
        parts.append(tag(sole, M["sole"], rigid=f"foot.{side}"))

    # --- Scarf -----------------------------------------------------------------
    wrap = torus("ScarfWrap", Vector((0, 0.005, 1.468)), 0.098, 0.046, 24, 8, scale=(1.05, 0.92, 1.0),
                 rot=(math.radians(-8), 0, 0))
    for v in wrap.data.vertices:
        ang = math.atan2(v.co.y, v.co.x)
        v.co.z += 0.012 * math.sin(ang * 3.0) + rnd.uniform(-0.004, 0.004)
        v.co.x *= 1.0 + 0.04 * math.sin(ang * 5.0)
    wrap.data.update()
    parts.append(tag(wrap, M["scarf"], ["neck", "chest"]))
    knot = dc.ico("ScarfKnot", 0.048, (0.045, 0.098, 1.45), subdiv=2)
    dc.deform(knot, lambda v: Vector((0.045 + (v.x - 0.045) * 1.1, 0.098 + (v.y - 0.098) * 0.8, 1.45 + (v.z - 1.45) * 0.9)))
    parts.append(tag(knot, M["scarf"], ["neck", "scarf_01"]))

    def ribbon(name, pts, w0, w1, up, seed):
        pts = [Vector(p) for p in pts]
        dense = []
        for i in range(len(pts) - 1):
            for k in range(3):
                dense.append(pts[i].lerp(pts[i + 1], k / 3))
        dense.append(pts[-1])
        radii = [lerp(w0, w1, i / (len(dense) - 1)) for i in range(len(dense))]
        obj = dc.tube_along(name, dense, radii, segments=10, up=up, flatten=0.16)
        r2 = random.Random(seed)
        for v in obj.data.vertices:
            v.co += Vector((r2.uniform(-1, 1) * 0.003, 0, r2.uniform(-1, 1) * 0.004))
        obj.data.update()
        return obj

    tail = ribbon("ScarfTail", [(0.04, 0.10, 1.45), (0.06, 0.19, 1.38), (0.075, 0.25, 1.25),
                                (0.085, 0.30, 1.11), (0.095, 0.31, 0.96), (0.10, 0.34, 0.84), (0.105, 0.37, 0.76)],
                  0.075, 0.062, Vector((1, 0, 0)), 3)
    # Notched, torn tip.
    for v in tail.data.vertices:
        if v.co.z < 0.80:
            v.co.z += 0.03 * math.sin(v.co.y * 160.0)
    parts.append(tag(tail, M["scarf"], ["neck", "scarf_01", "scarf_02", "scarf_03", "scarf_04"], power=5))
    tail2 = ribbon("ScarfTail2", [(0.06, 0.10, 1.44), (0.08, 0.17, 1.38), (0.095, 0.23, 1.28),
                                  (0.105, 0.25, 1.16), (0.11, 0.27, 1.06)], 0.05, 0.04, Vector((1, 0, 0)), 4)
    transform(tail2, Matrix.Translation((0.012, 0.0, 0.0)))
    parts.append(tag(tail2, M["scarf"], ["neck", "scarf_01", "scarf_02", "scarf_03"], power=5))
    drape = ribbon("ScarfDrape", [(0.055, -0.085, 1.475), (0.08, -0.145, 1.40), (0.092, -0.168, 1.31),
                                  (0.097, -0.17, 1.22)], 0.055, 0.045, Vector((0, -1, 0)), 5)
    parts.append(tag(drape, M["scarf"], ["neck", "chest"]))

    # --- Neck stump glow (tinted by the flame colour in Unity) -----------------
    glow = dc.lathe("NeckGlow", [(0.0, 1.515), (0.05, 1.512), (0.072, 1.50)], segments=12, scale_xy=(1.0, 0.85),
                    cap_bottom=False)
    parts.append(tag(glow, M["neck_glow"], rigid="neck"))
    return parts


def build_flame_head(M):
    rnd = random.Random(42)
    base_z = 1.515
    objs, funcs = [], []

    core = dc.ico("FlameCore", 0.095, (0, 0, 0), subdiv=3)

    def core_shape(v):
        zt = max(0.0, v.z) / 0.095
        s = 1.0 - 0.5 * zt
        return Vector((v.x * s, v.y * s * 0.9 + 0.02 * zt, v.z * 1.55)) + Vector((0, 0.0, base_z + 0.1))
    dc.deform(core, core_shape)
    objs.append(core)
    funcs.append((lambda p: 1.0, lambda p: max(0.0, (p.z - base_z) / 0.3) * 0.35, 0.0))

    count = 16
    for i in range(count):
        a = math.tau * i / count + rnd.uniform(-0.2, 0.2)
        back = 0.5 + 0.5 * math.sin(a)
        h = rnd.uniform(0.20, 0.30) + 0.20 * back
        twist = rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.3)
        r0 = rnd.uniform(0.048, 0.064) * (0.85 + 0.3 * back)
        pts, radii = [], []
        steps = 8
        for k in range(steps):
            t = k / (steps - 1)
            ang = a + twist * t
            rad = 0.085 * (1.0 - 0.85 * t) + 0.075 * math.sin(math.pi * t) * (0.7 + 0.6 * back)
            p = Vector((math.cos(ang) * rad, math.sin(ang) * rad * 0.85, base_z + 0.01 + h * t))
            p.y += 0.16 * t * t * (0.6 + back)
            p.x += 0.035 * math.sin(t * 5 + i * 1.7) * t
            pts.append(p)
            radii.append(r0 * (1.0 - t) ** 0.85 + 0.002)
        radii[-1] = 0.0
        objs.append(dc.tube_along(f"Tendril{i}", pts, radii, segments=7, up=Vector((0, 0, 1)), flatten=0.62))
        funcs.append((lambda p, h=h: 1.0 - min(1.0, (p.z - base_z) / (h + 0.05)),
                      lambda p, h=h: min(1.0, (p.z - base_z) / (h + 0.02)), i / count))

    for i in range(5):
        c = Vector((rnd.uniform(-0.07, 0.08), rnd.uniform(0.04, 0.2), base_z + rnd.uniform(0.42, 0.58)))
        flick = dc.ico(f"Flick{i}", rnd.uniform(0.014, 0.024), (0, 0, 0), subdiv=1)
        dc.deform(flick, lambda v, c=c: Vector((v.x, v.y, v.z * 2.2)) + c)
        objs.append(flick)
        funcs.append((lambda p: 0.15, lambda p: 1.0, rnd.random()))

    # Write vertex colours per piece before joining (R heat, G wobble, B phase).
    for obj, (h_fn, w_fn, ph) in zip(objs, funcs):
        attr = obj.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
        for v in obj.data.vertices:
            attr.data[v.index].color = (max(0.0, min(1.0, h_fn(v.co))), max(0.0, min(1.0, w_fn(v.co))), ph, 1.0)
    flame = dc.join(objs, "Beheaded_Flame")
    tag(flame, M["flame"], rigid="head")

    eye = dc.ico("Beheaded_Eye", 0.017, (0, 0, 0), subdiv=2)
    dc.deform(eye, lambda v: Vector((v.x * 1.25, v.y * 0.6, v.z * 0.8)) + Vector((-0.03, -0.088, 1.635)))
    tag(eye, M["eye"], rigid="head")

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for i, (cx, cy, cz, s) in enumerate(((0.0, 0.10, 1.98, 0.34), (0.03, 0.17, 2.10, 0.30), (-0.02, 0.23, 2.21, 0.26))):
        vs = [bm.verts.new((cx - s / 2, cy, cz - s / 2)), bm.verts.new((cx + s / 2, cy, cz - s / 2)),
              bm.verts.new((cx + s / 2, cy, cz + s / 2)), bm.verts.new((cx - s / 2, cy, cz + s / 2))]
        f = bm.faces.new(vs)
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv_layer].uv = uv
    smoke = dc.mesh_object("Beheaded_Smoke", bm)
    attr = smoke.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for v in smoke.data.vertices:
        attr.data[v.index].color = (0.0, 1.0, (v.index // 4) / 3.0, 1.0)
    tag(smoke, M["smoke"], rigid="head_socket")
    return flame, eye, smoke


def step_model(live=True):
    if live:
        dc.clear_scene_live()
    else:
        dc.reset_scene()
    M = make_materials()
    parts = build_body(M)
    flame, eye, smoke = build_flame_head(M)
    coll = dc.collection("Beheaded")
    for o in parts + [flame, eye, smoke]:
        dc.move_to(o, coll)
    _viewport_lights()
    print(f"[beheaded] model: {len(parts)} body parts, tris={sum(_tris(o) for o in parts)}")
    return parts


def _tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def _viewport_lights():
    if "KeyLight" in bpy.data.objects:
        return
    coll = dc.collection("Lights")
    key = bpy.data.objects.new("KeyLight", bpy.data.lights.new("KeyLight", "AREA"))
    key.data.energy = 120
    key.data.size = 2.0
    key.data.color = (1.0, 0.82, 0.62)
    key.location = (-2.0, -2.5, 3.0)
    key.rotation_euler = (math.radians(55), 0, math.radians(-38))
    rim = bpy.data.objects.new("RimLight", bpy.data.lights.new("RimLight", "AREA"))
    rim.data.energy = 160
    rim.data.size = 1.5
    rim.data.color = (0.45, 0.85, 1.0)
    rim.location = (1.6, 2.4, 2.6)
    rim.rotation_euler = (math.radians(-60), 0, math.radians(150))
    for o in (key, rim):
        coll.objects.link(o)
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs[0].default_value = dc.hex_rgba("#14212E")
        bg.inputs[1].default_value = 0.5


# ---------------------------------------------------------------------------
# Step 2: rig + weights
# ---------------------------------------------------------------------------

def step_rig():
    arm = rig.build_armature(f"{NAME}_Rig", joints(), PARENTS, NON_DEFORM)
    dc.move_to(arm, dc.collection("Beheaded"))
    for obj in list(dc.collection("Beheaded").objects):
        if obj.type != "MESH":
            continue
        if "dc_rigid" in obj:
            dc.weight_by_segments(obj, [], arm, rigid=obj["dc_rigid"])
        elif "dc_bones" in obj:
            dc.weight_by_segments(obj, obj["dc_bones"].split(","), arm, power=obj.get("dc_power", 6.0))
    arm.show_in_front = True
    print("[beheaded] rig: bones", len(arm.data.bones))
    return arm


# ---------------------------------------------------------------------------
# Step 3: high-poly bake
# ---------------------------------------------------------------------------

BAKE_EXCLUDE = ("Beheaded_Flame", "Beheaded_Eye", "Beheaded_Smoke")
UV_IMPORTANCE = {"M_Scarf": 1.35, "M_Iron": 1.3, "M_Leather": 1.1, "M_Bandage": 0.9, "M_Sole": 0.5,
                 "M_NeckGlow": 0.5}


def step_bake(size=2048):
    coll = dc.collection("Beheaded")
    arm = bpy.data.objects.get(f"{NAME}_Rig")
    if arm:
        arm.data.pose_position = "REST"
    for o in list(coll.objects):
        if o.name.startswith("Preview"):
            bpy.data.objects.remove(o, do_unlink=True)
    body_parts = [o for o in coll.objects if o.type == "MESH" and o.name not in BAKE_EXCLUDE]
    dc.uv_atlas_multi(body_parts, island_margin=0.003, importance=UV_IMPORTANCE)
    pairs = []
    for o in body_parts:
        mat = o.active_material.name if o.active_material else ""
        bevel = 0.006 if mat in ("M_Iron", "M_LeatherDark", "M_Sole") else 0.004
        pairs.append((o, dc.make_highpoly(o, bevel_width=bevel, subsurf=1)))
    paths = dc.bake_texture_set(body_parts, TEX_DIR, NAME, size=size, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    body = dc.join(body_parts, f"{NAME}_Body")
    baked = dc.baked_material(f"M_{NAME}", paths, emission_strength=2.0)
    body.data.materials.clear()
    body.data.materials.append(baked)
    if arm:
        arm.data.pose_position = "POSE"
    print("[beheaded] bake:", {k: str(v) for k, v in paths.items()}, "tris", _tris(body))
    return body


# ---------------------------------------------------------------------------
# Step 4: animation
# ---------------------------------------------------------------------------

STANCE = {
    "hips_loc": (0, 0.0, -0.06),
    "spine": (10, 0, 0), "chest": (6, 10, 0), "neck": (-8, -4, 0), "head": (-6, -4, 0),
    "feet": {"L": (-0.17, 0.11, 0), "R": (0.19, 0.11, 0)},
    "arm.L": (-22, -72, 0, -10, 0),
    "arm.R": (12, -14, 40, 14, 0),
}


def M_(base, **kw):
    return rig.merge(base, **kw)


SCARF = ["scarf_01", "scarf_02", "scarf_03", "scarf_04"]
COAT_L = ["coat_L_01", "coat_L_02", "coat_L_03"]
COAT_R = ["coat_R_01", "coat_R_02", "coat_R_03"]


def chains(period, scarf_base, scarf_amp, coat_base, coat_amp, scarf_z=6.0, speed=1.0):
    def fn(f, pose):
        out = {}
        out.update(rig.wave_chain(SCARF, f * speed, period, scarf_base, scarf_amp, phase_step=0.9, z_amp=scarf_z))
        out.update(rig.wave_chain(COAT_L, f * speed, period, coat_base, coat_amp, phase_step=0.8))
        out.update(rig.wave_chain(COAT_R, f * speed, period, coat_base, coat_amp, phase_step=0.8, offset=math.pi * 0.6))
        return out
    return fn


def anim_idle(arm):
    breathe = M_(STANCE, hips_loc=(0, 0.0, -0.078), chest=(9, 10, 0), neck=(-10, -4, 0),
                 **{"chest:scale": (1.035, 1.0, 1.03), "arm.L": (-25, -76, 0, -12, 0), "arm.R": (14, -11, 44, 15, 0)})
    rig.author_action(arm, "Idle", 61, [(1, STANCE), (31, breathe), (61, STANCE)],
                      chain_fn=chains(30, (2, 4, 6, 8), (4, 7, 10, 13), (0, 2, 3), (2, 3, 4)), chain_step=3)


def _run_foot(q):
    """Ankle (y, z, pitch) for run phase q in [0,1)."""
    stance = 0.4
    if q < stance:
        u = q / stance
        y = lerp(-0.36, 0.33, u)
        pitch = lerp(-4, 28, max(0.0, (u - 0.55) / 0.45))
        return (y, 0.11, pitch)
    u = (q - stance) / (1 - stance)
    e = u * u * (3 - 2 * u)
    y = lerp(0.33, -0.36, e) + 0.14 * math.sin(math.pi * u) * (1 - u)
    z = 0.11 + 0.40 * math.sin(math.pi * min(1.0, u * 1.08)) ** 0.9
    pitch = lerp(45, -12, u)
    return (y, z, pitch)


def anim_run(arm):
    keys = []
    for f in range(1, 26, 2):
        p = (f - 1) / 24.0
        c = math.cos(math.tau * p)
        s = math.sin(math.tau * p)
        pose = {
            "hips_loc": (0, -0.02, -0.105 - 0.035 * math.cos(2 * math.tau * (p - 0.1))),
            "spine": (16, 0, 0), "chest": (12, 12 * s, 0), "neck": (-14, -6 * s, 0), "head": (-10, 0, 0),
            "feet": {"L": _run_foot(p), "R": _run_foot((p + 0.5) % 1.0)},
            "arm.L": (10 + 48 * c, 10 + 48 * c - 80 - 12 * s, 0, -12, 0),
            "arm.R": (52 - 10 * c, 22 - 10 * c, 160 + 6 * s, 22, 0),
        }
        keys.append((f, pose))
    rig.author_action(arm, "Run", 25, keys,
                      chain_fn=chains(12, (30, 22, 16, 10), (6, 10, 14, 18), (28, 16, 10), (6, 9, 13), scarf_z=10),
                      chain_step=1)


def anim_slashes(arm):
    # Combo 1: diagonal down-forward cut.
    ant = M_(STANCE, hips_loc=(0, 0.04, -0.10), spine=(4, -10, 0), chest=(-6, -28, 0), neck=(-2, 8, 0),
             head=(-4, 6, 0), feet={"L": (-0.20, 0.11, 0), "R": (0.22, 0.11, 0)},
             **{"arm.L": (-75, -100, 0, -15, 0), "arm.R": (150, 60, 150, 25, 0)})
    strike = M_(STANCE, hips_loc=(0, -0.12, -0.12), spine=(24, 18, 0), chest=(16, 30, 0), neck=(-16, -10, 0),
                head=(-10, -8, 0), feet={"L": (-0.42, 0.11, 0), "R": (0.30, 0.11, 10)},
                **{"arm.L": (45, 20, 0, -25, 0), "arm.R": (-62, -66, 50, 10, 0), "chest:scale": (1, 1.06, 1)})
    rec = M_(strike, hips_loc=(0, -0.11, -0.135), spine=(26, 14, 0), chest=(14, 24, 0),
             **{"arm.R": (-50, -60, 70, 12, 0), "chest:scale": (1, 1, 1)})
    snappy = {1: "LINEAR", 2: "LINEAR", 3: "CONSTANT", 4: "LINEAR", 8: "BEZIER"}
    slash_chains = chains(18, (12, 10, 8, 6), (10, 14, 18, 22), (8, 6, 4), (6, 8, 10), scarf_z=10)
    rig.author_action(arm, "Slash_Combo_1", 18,
                      [(1, STANCE), (2, rig.blend(STANCE, ant, 0.75)), (3, ant), (4, strike), (8, rec), (18, STANCE)],
                      modes=snappy, chain_fn=slash_chains, chain_step=1)

    # Combo 2: rising back-hand.
    ant2 = M_(STANCE, hips_loc=(0, 0.02, -0.13), spine=(18, 10, 0), chest=(10, 30, 0), neck=(-14, -12, 0),
              head=(-8, -8, 0), feet={"L": (-0.22, 0.11, 0), "R": (0.24, 0.11, 0)},
              **{"arm.L": (-40, -120, 0, -15, 0), "arm.R": (55, 30, 165, 28, 0)})
    strike2 = M_(STANCE, hips_loc=(0, -0.10, -0.03), spine=(-2, -12, 0), chest=(-10, -28, 0), neck=(4, 10, 0),
                 head=(0, 8, 0), feet={"L": (-0.36, 0.11, 0), "R": (0.26, 0.15, 25)},
                 **{"arm.L": (35, 0, 0, -30, 0), "arm.R": (-150, -165, -75, 15, 0), "chest:scale": (1, 1.05, 1)})
    rec2 = M_(strike2, hips_loc=(0, -0.09, -0.06), spine=(2, -10, 0), chest=(-6, -24, 0),
              **{"arm.R": (-140, -158, -60, 15, 0), "chest:scale": (1, 1, 1)})
    rig.author_action(arm, "Slash_Combo_2", 18,
                      [(1, STANCE), (2, rig.blend(STANCE, ant2, 0.75)), (3, ant2), (4, strike2), (8, rec2), (18, STANCE)],
                      modes=snappy, chain_fn=slash_chains, chain_step=1)

    # Combo 3: overhead finisher chop.
    ant3 = M_(STANCE, hips_loc=(0, 0.05, 0.0), spine=(-6, 0, 0), chest=(-14, -8, 0), neck=(6, 0, 0), head=(4, 0, 0),
              feet={"L": (-0.18, 0.16, -10), "R": (0.20, 0.11, 15)},
              **{"arm.L": (-165, -175, 0, -10, 0), "arm.R": (178, 108, 170, 8, 0)})
    strike3 = M_(STANCE, hips_loc=(0, -0.16, -0.22), spine=(32, 0, 0), chest=(22, 6, 0), neck=(-22, 0, 0),
                 head=(-14, 0, 0), feet={"L": (-0.45, 0.11, 0), "R": (0.34, 0.13, 20)},
                 **{"arm.L": (40, 10, 0, -40, 0), "arm.R": (-50, -62, 72, 6, 0), "spine:scale": (1, 1.05, 1)})
    rec3 = M_(strike3, hips_loc=(0, -0.15, -0.24), spine=(34, 0, 0),
              **{"arm.R": (-45, -55, 80, 6, 0), "spine:scale": (1, 1, 1)})
    rig.author_action(arm, "Slash_Combo_3", 24,
                      [(1, STANCE), (2, rig.blend(STANCE, ant3, 0.6)), (4, ant3), (5, strike3), (11, rec3), (24, STANCE)],
                      modes={1: "LINEAR", 2: "BEZIER", 4: "CONSTANT", 5: "LINEAR", 11: "BEZIER"},
                      chain_fn=chains(24, (14, 12, 10, 8), (12, 16, 20, 24), (10, 8, 6), (8, 10, 12), scarf_z=10),
                      chain_step=1)


def anim_dodge(arm):
    crouch = M_(STANCE, hips_loc=(0, -0.05, -0.30), spine=(30, 0, 0), chest=(24, 0, 0), neck=(10, 0, 0), head=(0, 0, 0),
                feet={"L": (-0.20, 0.11, 0), "R": (0.15, 0.11, 25)},
                **{"arm.L": (-60, -140, 0, -10, 0), "arm.R": (-50, -110, -150, 10, 0)})

    def tuck(angle):
        return {
            "hips_loc": (0, -0.02, -0.47), "hips": (angle, 0, 0), "spine": (30, 0, 0), "chest": (28, 0, 0),
            "neck": (20, 0, 0), "head": (10, 0, 0),
            "thigh.L": (-118, 0, 0), "shin.L": (128, 0, 0), "foot.L": (30, 0, 0),
            "thigh.R": (-108, 0, 0), "shin.R": (122, 0, 0), "foot.R": (30, 0, 0),
            "upper_arm.L": (-60, 0, -10), "forearm.L": (-100, 0, 0),
            "upper_arm.R": (-50, 0, 10), "forearm.R": (-80, 0, 0), "hand.R": (60, 0, 0),
        }
    crouch2 = M_(crouch, hips=(360, 0, 0))
    stance2 = M_(STANCE, hips=(360, 0, 0))
    keys = [(1, STANCE), (3, crouch), (4, tuck(0)), (7, tuck(90)), (10, tuck(180)), (13, tuck(270)),
            (16, tuck(360)), (18, crouch2), (20, stance2)]
    modes = {1: "LINEAR", 3: "LINEAR", 4: "LINEAR", 7: "LINEAR", 10: "LINEAR", 13: "LINEAR", 16: "BEZIER", 18: "BEZIER"}
    rig.author_action(arm, "Dodge_Roll", 20, keys, modes=modes,
                      chain_fn=chains(10, (20, 18, 14, 10), (15, 18, 22, 26), (20, 14, 10), (10, 12, 14), scarf_z=12),
                      chain_step=1)


def anim_air(arm):
    rise_a = M_(STANCE, hips_loc=(0, 0, 0.0), spine=(12, 0, 0), chest=(4, 6, 0), neck=(-8, 0, 0), head=(-6, 0, 0),
                legs={"L": (-80, -10, 30), "R": (25, 75, 40)},
                **{"arm.L": (-110, -150, 0, -20, 0), "arm.R": (40, 10, 150, 25, 0)})
    rise_a.pop("feet")
    rise_b = M_(rise_a, legs={"L": (-86, -16, 30), "R": (28, 82, 42)},
                **{"arm.L": (-116, -156, 0, -22, 0), "arm.R": (44, 12, 154, 25, 0)})
    rig.author_action(arm, "Jump_Rise", 13, [(1, rise_a), (7, rise_b), (13, rise_a)],
                      chain_fn=chains(12, (-25, -15, -10, -5), (4, 6, 8, 10), (-10, -5, 0), (3, 4, 5)), chain_step=2)
    fall_a = M_(STANCE, hips_loc=(0, 0, 0.0), spine=(2, 0, 0), chest=(-4, 4, 0), neck=(0, 0, 0), head=(0, 0, 0),
                legs={"L": (-30, 5, -10), "R": (10, 40, 15)},
                **{"arm.L": (-140, -170, 0, -35, 0), "arm.R": (-120, -150, -100, 30, 0)})
    fall_a.pop("feet")
    fall_b = M_(fall_a, legs={"L": (-34, 2, -10), "R": (13, 44, 15)},
                **{"arm.L": (-146, -174, 0, -38, 0), "arm.R": (-126, -154, -104, 30, 0)})
    rig.author_action(arm, "Jump_Fall", 13, [(1, fall_a), (7, fall_b), (13, fall_a)],
                      chain_fn=chains(6, (55, 40, 30, 20), (8, 12, 16, 20), (55, 35, 25), (8, 12, 16), scarf_z=12),
                      chain_step=1)


def anim_ground_pound(arm):
    tuck = M_(STANCE, hips_loc=(0, 0, 0.02), spine=(18, 0, 0), chest=(10, 0, 0), neck=(-6, 0, 0), head=(-6, 0, 0),
              legs={"L": (-95, -20, 30), "R": (-70, 0, 30)},
              **{"arm.L": (-150, -170, 0, -20, 0), "arm.R": (-175, -185, -90, 10, 0)})
    tuck.pop("feet")
    tuck2 = M_(tuck, hips_loc=(0, 0, 0.06), spine=(8, 0, 0), chest=(-4, 0, 0),
               **{"arm.R": (-178, -195, -95, 10, 0)})
    plunge = M_(STANCE, hips_loc=(0, 0, 0.05), spine=(4, 0, 0), chest=(0, 0, 0), neck=(-4, 0, 0), head=(-4, 0, 0),
                legs={"L": (-8, 0, 35), "R": (6, 12, 40)},
                **{"arm.L": (-30, -60, 0, -45, 0), "arm.R": (-12, -18, 92, 8, 0)})
    plunge.pop("feet")
    impact = M_(STANCE, hips_loc=(0, -0.04, -0.32), spine=(36, 0, 0), chest=(22, 0, 0), neck=(-24, 0, 0),
                head=(-16, 0, 0), feet={"L": (-0.26, 0.11, 0), "R": (0.26, 0.13, 30)},
                **{"arm.L": (50, 20, 0, -50, 0), "arm.R": (-40, -45, 95, 10, 0), "spine:scale": (1.04, 0.94, 1.04)})
    settle = M_(impact, hips_loc=(0, -0.04, -0.30), spine=(34, 0, 0), **{"spine:scale": (1, 1, 1)})
    rig.author_action(arm, "Ground_Pound_Slam", 24,
                      [(1, tuck), (4, tuck2), (6, tuck2), (7, plunge), (8, plunge), (9, impact), (15, settle), (24, STANCE)],
                      modes={1: "BEZIER", 4: "LINEAR", 6: "CONSTANT", 7: "CONSTANT", 8: "CONSTANT", 9: "LINEAR", 15: "BEZIER"},
                      chain_fn=chains(8, (60, 45, 35, 25), (8, 12, 16, 20), (60, 40, 30), (8, 12, 16), scarf_z=10),
                      chain_step=1)


def anim_block_hurt(arm):
    block = M_(STANCE, hips_loc=(0, 0.03, -0.12), spine=(14, -6, 0), chest=(8, -14, 0), neck=(-10, 6, 0),
               head=(-6, 4, 0), feet={"L": (-0.22, 0.11, 0), "R": (0.24, 0.11, 0)},
               **{"arm.L": (-75, -170, 0, -12, 0), "arm.R": (30, -20, 40, 20, 0)})
    over = M_(block, hips_loc=(0, 0.04, -0.14), **{"arm.L": (-80, -176, 0, -12, 0)})
    rig.author_action(arm, "Shield_Block", 12, [(1, STANCE), (3, over), (5, block), (12, block)],
                      modes={1: "LINEAR", 3: "BEZIER"},
                      chain_fn=chains(12, (8, 6, 5, 4), (5, 7, 9, 11), (4, 3, 2), (3, 4, 5)), chain_step=2)
    hurt = M_(STANCE, hips_loc=(0, 0.10, -0.08), spine=(-14, 0, 0), chest=(-16, -10, 0), neck=(-10, 0, 0),
              head=(-8, 0, 0), feet={"L": (-0.12, 0.11, 0), "R": (0.26, 0.11, 0)},
              **{"arm.L": (-70, -100, 0, -30, 0), "arm.R": (-40, -70, 10, 25, 0)})
    hold = M_(hurt, hips_loc=(0, 0.08, -0.09), spine=(-8, 0, 0), chest=(-10, -8, 0))
    rig.author_action(arm, "Hurt", 14, [(1, STANCE), (2, hurt), (6, hold), (14, STANCE)],
                      modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"},
                      chain_fn=chains(14, (20, 16, 12, 8), (12, 16, 20, 24), (14, 10, 8), (8, 10, 12), scarf_z=10),
                      chain_step=1)


def step_animate():
    arm = bpy.data.objects[f"{NAME}_Rig"]
    for act in list(bpy.data.actions):
        if act.get("dc_owner", NAME) == NAME:
            bpy.data.actions.remove(act)
    existing = set(bpy.data.actions.keys())
    anim_idle(arm)
    anim_run(arm)
    anim_slashes(arm)
    anim_dodge(arm)
    anim_air(arm)
    anim_ground_pound(arm)
    anim_block_hurt(arm)
    for act in bpy.data.actions:
        if act.name not in existing:
            act["dc_owner"] = NAME
    arm.animation_data.action = bpy.data.actions["Idle"]
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 60
    print("[beheaded] actions:", [a.name for a in bpy.data.actions])


def bind_meshes():
    arm = bpy.data.objects[f"{NAME}_Rig"]
    for obj in dc.collection("Beheaded").objects:
        if obj.type == "MESH" and not any(m.type == "ARMATURE" for m in obj.modifiers):
            rig.bind(obj, arm)
    return arm


# ---------------------------------------------------------------------------
# Step 5: export
# ---------------------------------------------------------------------------

def step_export():
    arm = bpy.data.objects[f"{NAME}_Rig"]
    meshes = [o for o in dc.collection("Beheaded").objects if o.type == "MESH"]
    for o in meshes:
        if not any(m.type == "TRIANGULATE" for m in o.modifiers):
            tri = o.modifiers.new("NgonTriangulate", "TRIANGULATE")
            tri.min_vertices = 5
            tri.ngon_method = "BEAUTY"
            with bpy.context.temp_override(object=o):
                bpy.ops.object.modifier_move_to_index(modifier=tri.name, index=0)
    # Neutral rest pose in the bind frame.
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    path = dc.export_fbx(OUT_DIR / f"{NAME}.fbx", [arm] + meshes, animated=True)
    arm.animation_data.action = bpy.data.actions.get("Idle")
    meta = {a.name: int(a.get("dc_length", a.frame_range[1])) for a in bpy.data.actions
            if a.get("dc_owner", NAME) == NAME}
    import json
    (OUT_DIR / f"{NAME}_clips.json").write_text(json.dumps(meta, indent=2))
    dc.ensure_dir(BLEND_PATH.parent)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), copy=True)
    print("[beheaded] export:", path, meta)
    return path


def build_all(live=False, size=2048):
    step_model(live=live)
    step_rig()
    step_bake(size=size)
    bind_meshes()
    step_animate()
    step_export()


if __name__ == "__main__":
    build_all(live=False)
