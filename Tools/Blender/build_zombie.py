"""Undead Prisoner (Zombie) -- the Prisoners' Quarters grunt.

Same skeleton naming as the Beheaded (minus scarf/sockets) so the shared
pose solver and Unity tooling apply. Clips: Idle, Run, Attack, Hurt, Death.
"""

import json
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
from build_beheaded import chains, delete_faces, limb, solidify, tag, torus, transform, _tris  # noqa: E402

NAME = "Zombie"
COLL = "Zombie"
OUT_DIR = dc.ART_ROOT / "Characters" / NAME
TEX_DIR = OUT_DIR / "Textures"
DISPLAY_OFFSET = Vector((1.6, 0.0, 0.0))

JOINTS_L = {
    "root": ((0, 0, 0), (0, 0, 0.25)),
    "hips": ((0, 0, 0.90), (0, 0, 1.0)),
    "spine": ((0, 0, 1.0), (0, 0, 1.16)),
    "chest": ((0, 0, 1.16), (0, 0, 1.38)),
    "neck": ((0, 0, 1.38), (0, -0.02, 1.47)),
    "head": ((0, -0.02, 1.47), (0, -0.04, 1.70)),
    "shoulder.L": ((0.04, 0.0, 1.33), (0.17, 0.01, 1.34)),
    "upper_arm.L": ((0.18, 0.01, 1.33), (0.22, 0.02, 1.02)),
    "forearm.L": ((0.22, 0.02, 1.02), (0.24, -0.02, 0.73)),
    "hand.L": ((0.24, -0.02, 0.73), (0.25, -0.04, 0.60)),
    "thigh.L": ((0.09, 0, 0.89), (0.10, -0.03, 0.48)),
    "shin.L": ((0.10, -0.03, 0.48), (0.10, 0.02, 0.09)),
    "foot.L": ((0.10, 0.02, 0.09), (0.10, -0.14, 0.02)),
    "coat_L_01": ((0.08, 0.10, 0.90), (0.09, 0.12, 0.78)),
    "coat_L_02": ((0.09, 0.12, 0.78), (0.10, 0.14, 0.66)),
    "coat_L_03": ((0.10, 0.14, 0.66), (0.10, 0.15, 0.54)),
}
PARENTS = {"root": None, "hips": "root", "spine": "hips", "chest": "spine", "neck": "chest", "head": "neck"}
for s in ("L", "R"):
    PARENTS.update({
        f"shoulder.{s}": "chest", f"upper_arm.{s}": f"shoulder.{s}", f"forearm.{s}": f"upper_arm.{s}",
        f"hand.{s}": f"forearm.{s}", f"thigh.{s}": "hips", f"shin.{s}": f"thigh.{s}", f"foot.{s}": f"shin.{s}",
        f"coat_{s}_01": "hips", f"coat_{s}_02": f"coat_{s}_01", f"coat_{s}_03": f"coat_{s}_02",
    })


def make_materials():
    M = {}
    M["skin"] = dc.make_material("M_ZSkin", "#7E9B66", dark="#3C5233", light="#B4C995", noise_scale=8, noise_amt=0.9,
                                 rough=0.7, edge_wear="#D2E0B4", edge_wear_amt=0.7, cavity_dirt=0.9, bump_scale=70,
                                 bump_strength=0.35, bevel_radius=0.01)
    M["rag"] = dc.make_material("M_ZRag", "#38424E", dark="#161B21", light="#5A6672", noise_scale=6, noise_amt=0.9,
                                rough=0.9, edge_wear="#7A8590", edge_wear_amt=0.5, cavity_dirt=0.8, bump_scale=110,
                                bump_strength=0.25, bevel_radius=0.006)
    M["pants"] = dc.make_material("M_ZPants", "#4E3B2A", dark="#20160E", light="#76593E", noise_scale=7, noise_amt=0.9,
                                  rough=0.88, edge_wear="#9A7A58", edge_wear_amt=0.5, cavity_dirt=0.8, bump_scale=120,
                                  bump_strength=0.25, bevel_radius=0.006)
    M["rope"] = dc.make_material("M_ZRope", "#8E7550", dark="#4A3A24", light="#B89A6C", rough=0.9,
                                 stripes=("z", 120.0, 0.25, "#3A2C18"), bump_scale=150, bevel_radius=0.004)
    M["iron"] = dc.make_material("M_ZIron", "#4A5058", dark="#1C2026", light="#7D8792", metal=1.0, rough=0.45,
                                 noise_scale=16, edge_wear="#C0C8CE", edge_wear_amt=1.0, cavity_dirt=0.9,
                                 bevel_radius=0.006)
    M["eye"] = dc.make_material("M_ZEye", "#FFB347", dark="#FF8A1A", light="#FFE0A0", rough=0.3,
                                emission="#FFFFFF", emission_strength=6.0)
    M["mouth"] = dc.make_material("M_ZMouth", "#120A08", dark="#050302", light="#2A1712", rough=0.6)
    M["bone"] = dc.make_material("M_ZBone", "#CFC6A8", dark="#7E7458", light="#EDE6CF", rough=0.6,
                                 cavity_dirt=0.9, edge_wear="#FFFFFF", edge_wear_amt=0.4, bevel_radius=0.004)
    return M


def build_body(M):
    parts = []
    rnd = random.Random(13)
    # Torso: skinny, ribby.
    torso = dc.lathe("Z_Torso", [(0.13, 0.86), (0.145, 0.93), (0.13, 1.00), (0.125, 1.08), (0.15, 1.17),
                                 (0.17, 1.26), (0.172, 1.32), (0.14, 1.37), (0.08, 1.41), (0.05, 1.44)],
                     segments=16, scale_xy=(1.0, 0.72))

    def ribs(v):
        if 1.08 < v.z < 1.30 and v.y < 0:
            v.y *= 1.0 + 0.05 * math.sin((v.z - 1.08) * 110.0)
        if v.y > 0 and v.z > 1.15:
            v.y *= 1.12  # hunched upper back
        return v
    dc.deform(torso, ribs)
    dc.subdivide(torso, 1)
    parts.append(tag(torso, M["skin"], ["hips", "spine", "chest", "neck"]))

    # Torn shirt shell with holes and a ragged hem.
    shirt = dc.lathe("Z_Shirt", [(0.142, 0.98), (0.135, 1.06), (0.158, 1.16), (0.18, 1.25), (0.182, 1.31),
                                 (0.15, 1.365)], segments=20, scale_xy=(1.03, 0.76), cap_top=False, cap_bottom=False)
    dc.deform(shirt, lambda v: Vector((v.x, v.y * (1.12 if (v.y > 0 and v.z > 1.15) else 1.0), v.z)))
    delete_faces(shirt, lambda c: rnd.random() < 0.12 or (c.y < -0.05 and c.z > 1.30 and abs(c.x) < 0.06))
    for v in shirt.data.vertices:
        if v.co.z < 1.0:
            v.co.z += rnd.uniform(-0.05, 0.02)
    solidify(shirt, 0.01, offset=1.0)
    parts.append(tag(shirt, M["rag"], ["hips", "spine", "chest"]))

    # Rag loincloth flaps (front + back), driven by the coat chains at the back.
    for name, y_sign in (("Z_RagFront", -1), ("Z_RagBack", 1)):
        bm = bmesh.new()
        rows, cols = 5, 4
        grid = []
        for r in range(rows):
            row = []
            t = r / (rows - 1)
            for c in range(cols):
                u = c / (cols - 1) - 0.5
                x = u * (0.22 - 0.06 * t)
                z = 0.93 - 0.38 * t + (rnd.uniform(-0.04, 0.0) if r == rows - 1 else 0.0)
                y = y_sign * (0.105 + 0.04 * t)
                row.append(bm.verts.new((x, y, z)))
            grid.append(row)
        for r in range(rows - 1):
            for c in range(cols - 1):
                f = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
                bm.faces.new(f if y_sign > 0 else tuple(reversed(f)))
        flap = dc.mesh_object(name, bm)
        solidify(flap, 0.01, offset=0.0)
        bones = ["hips", "coat_L_01", "coat_L_02", "coat_L_03", "coat_R_01", "coat_R_02", "coat_R_03"] if y_sign > 0 \
            else ["hips", "thigh.L", "thigh.R"]
        parts.append(tag(flap, M["pants"], bones, power=5))

    belt = torus("Z_Rope", Vector((0, 0.0, 0.93)), 0.16, 0.016, 24, 6, scale=(1.0, 0.76, 1.0))
    parts.append(tag(belt, M["rope"], rigid="hips"))

    # Head: elongated skull, jaw, sunken glowing eyes.
    head = dc.ico("Z_Head", 0.125, (0, 0, 0), subdiv=3)

    def skull(v):
        p = Vector((v.x * 0.92, v.y * 1.05, v.z * 1.12))
        if p.z < -0.02 and p.y < 0:
            p.y -= 0.03 * min(1.0, -p.z / 0.08)  # jutting jaw
        if p.y < -0.06 and abs(p.x) > 0.02 and -0.01 < p.z < 0.05:
            p.y += 0.018  # brow / socket recess
        return p + Vector((0, -0.04, 1.59))
    dc.deform(head, skull)
    parts.append(tag(head, M["skin"], ["neck", "head"], power=10))
    for sx in (1, -1):
        eye = dc.ico(f"Z_Eye{sx}", 0.022, (0.045 * sx, -0.152, 1.61), subdiv=2)
        dc.deform(eye, lambda v, sx=sx: Vector((0.045 * sx + (v.x - 0.045 * sx) * 1.2, -0.152 + (v.y + 0.152) * 0.5, v.z)))
        parts.append(tag(eye, M["eye"], rigid="head"))
    mouth = dc.box("Z_Mouth", (0.085, 0.02, 0.026), (0.0, -0.162, 1.53), bevel=0.006)
    parts.append(tag(mouth, M["mouth"], rigid="head"))
    for k in range(5):
        tooth = dc.box(f"Z_Tooth{k}", (0.008, 0.008, 0.016), (-0.032 + k * 0.016, -0.17, 1.53 + (0.007 if k % 2 else -0.005)))
        parts.append(tag(tooth, M["bone"], rigid="head"))
    neck = limb("Z_Neck", (0, -0.005, 1.37), (0, -0.03, 1.52), [0.065, 0.06, 0.058], segments=10)
    parts.append(tag(neck, M["skin"], ["chest", "neck", "head"]))

    for side, sx in (("L", 1.0), ("R", -1.0)):
        def P(x, y, z):
            return Vector((x * sx, y, z))
        upper = limb(f"Z_Upper{side}", P(0.17, 0.01, 1.35), P(0.222, 0.02, 1.0), [0.08, 0.072, 0.064, 0.06, 0.058],
                     segments=10)
        parts.append(tag(upper, M["skin"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        sleeve = limb(f"Z_Sleeve{side}", P(0.17, 0.01, 1.36), P(0.20, 0.015, 1.20), [0.088, 0.085, 0.08], segments=10)
        for v in sleeve.data.vertices:
            if v.co.z < 1.24:
                v.co.z += rnd.uniform(-0.03, 0.01)
        parts.append(tag(sleeve, M["rag"], ["chest", f"upper_arm.{side}"]))
        fore = limb(f"Z_Fore{side}", P(0.222, 0.02, 1.04), P(0.24, -0.02, 0.74), [0.064, 0.062, 0.056, 0.05, 0.046],
                    segments=10)
        parts.append(tag(fore, M["skin"], [f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"]))
        palm = dc.box(f"Z_Palm{side}", (0.065, 0.095, 0.085), P(0.245, -0.035, 0.69), bevel=0.015)
        fingers = [palm]
        for k in range(3):
            fx = 0.245 * sx + (k - 1) * 0.017
            pts = [(fx, -0.06, 0.66), (fx, -0.075, 0.6), (fx, -0.06, 0.555), (fx, -0.035, 0.535)]
            claw = dc.tube_along(f"Z_Claw{side}{k}", pts, [0.016, 0.013, 0.008, 0.0], segments=6)
            fingers.append(claw)
        hand = dc.join(fingers, f"Z_Hand{side}")
        parts.append(tag(hand, M["skin"], rigid=f"hand.{side}"))
        if side == "R":
            cuff = torus("Z_Manacle", P(0.238, -0.015, 0.79), 0.066, 0.016, 16, 6, scale=(1.0, 1.0, 1.3))
            links = [cuff]
            for k in range(3):
                link = torus(f"Z_ChainLink{k}", P(0.27, -0.02, 0.74 - k * 0.045), 0.02, 0.006, 10, 5,
                             rot=(0, math.pi / 2 if k % 2 else 0, math.pi / 2))
                links.append(link)
            chain = dc.join(links, "Z_Manacle")
            parts.append(tag(chain, M["iron"], [f"forearm.{side}", f"hand.{side}"], power=8))

        thigh = limb(f"Z_Thigh{side}", P(0.088, 0.0, 0.94), P(0.10, -0.03, 0.47), [0.1, 0.095, 0.086, 0.077, 0.07],
                     segments=10)
        parts.append(tag(thigh, M["pants"], ["hips", f"thigh.{side}", f"shin.{side}"]))
        pant_shin = limb(f"Z_PantShin{side}", P(0.10, -0.03, 0.52), P(0.10, -0.01, 0.34), [0.075, 0.072, 0.078],
                         segments=10)
        for v in pant_shin.data.vertices:
            if v.co.z < 0.38:
                v.co.z += rnd.uniform(-0.05, 0.02)
        parts.append(tag(pant_shin, M["pants"], [f"thigh.{side}", f"shin.{side}"]))
        shin = limb(f"Z_Shin{side}", P(0.10, -0.01, 0.4), P(0.10, 0.02, 0.08), [0.062, 0.058, 0.052, 0.048], segments=10)
        parts.append(tag(shin, M["skin"], [f"shin.{side}", f"foot.{side}"]))
        foot = dc.box(f"Z_Foot{side}", (0.10, 0.22, 0.07), P(0.10, -0.05, 0.035), bevel=0.02)
        dc.deform(foot, lambda v: Vector((v.x, v.y, v.z * (0.7 if v.y < -0.1 else 1.0))))
        parts.append(tag(foot, M["skin"], [f"shin.{side}", f"foot.{side}"], power=8))
    return parts


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

STANCE = {
    "hips_loc": (0, 0.03, -0.07),
    "spine": (22, 0, 0), "chest": (16, 6, 0), "neck": (-22, 0, 0), "head": (-14, 8, 0),
    "feet": {"L": (-0.16, 0.09, 0), "R": (0.17, 0.09, 0)},
    "arm.L": (-12, -32, 0, -6, 0),
    "arm.R": (-4, -24, 0, 6, 0),
}


def M_(base, **kw):
    return rig.merge(base, **kw)


RAG = lambda period, base, amp: chains(period, (0, 0, 0, 0), (0, 0, 0, 0), base, amp)  # noqa: E731


def anim_idle(arm):
    sway = M_(STANCE, hips_loc=(0.0, 0.03, -0.085), spine=(24, 0, 4), chest=(18, 2, 3), head=(-12, 14, -6),
              **{"arm.L": (-8, -26, 0, -4, 0), "arm.R": (-8, -30, 0, 8, 0)})
    rig.author_action(arm, f"{NAME}_Idle", 61, [(1, STANCE), (31, sway), (61, STANCE)],
                      chain_fn=RAG(30, (2, 3, 4), (3, 4, 5)), chain_step=3)


def _shamble(q):
    stance = 0.45
    if q < stance:
        u = q / stance
        return (0.18 - 0.40 * (1 - u) + 0.0, 0.09, 0) if False else (-0.22 + 0.44 * u, 0.09, 0)
    u = (q - stance) / (1 - stance)
    e = u * u * (3 - 2 * u)
    return (0.22 - 0.44 * e, 0.09 + 0.22 * math.sin(math.pi * u), 30 * (1 - u) - 10 * u)


def anim_run(arm):
    keys = []
    for f in range(1, 26, 2):
        p = (f - 1) / 24.0
        c, s = math.cos(math.tau * p), math.sin(math.tau * p)
        keys.append((f, {
            "hips_loc": (0, 0.0, -0.10 - 0.03 * math.cos(2 * math.tau * p)),
            "spine": (30, 0, 6 * s), "chest": (18, 10 * s, 0), "neck": (-30, 0, 0), "head": (-16, 6 * s, 0),
            "feet": {"L": _shamble(p), "R": _shamble((p + 0.5) % 1.0)},
            "arm.L": (-70 + 14 * c, -95 + 10 * c, 0, -10, 0),
            "arm.R": (-62 - 14 * c, -90 - 10 * c, 0, 10, 0),
        }))
    rig.author_action(arm, f"{NAME}_Run", 25, keys, chain_fn=RAG(12, (20, 14, 10), (6, 9, 12)), chain_step=1)


def anim_attack(arm):
    windup = M_(STANCE, hips_loc=(0, 0.10, -0.04), spine=(-4, 0, 0), chest=(-14, 0, 0), neck=(-6, 0, 0),
                head=(-18, 0, 0), feet={"L": (-0.18, 0.09, 0), "R": (0.24, 0.09, 0)},
                **{"arm.L": (165, 120, 0, -15, 0), "arm.R": (160, 112, 0, 15, 0)})
    windup2 = M_(windup, hips_loc=(0, 0.12, -0.03), chest=(-18, 0, 0),
                 **{"arm.L": (172, 126, 0, -15, 0), "arm.R": (168, 118, 0, 15, 0)})
    strike = M_(STANCE, hips_loc=(0, -0.22, -0.16), spine=(40, 0, 0), chest=(24, 0, 0), neck=(-30, 0, 0),
                head=(-10, 0, 0), feet={"L": (-0.48, 0.09, 0), "R": (0.30, 0.12, 25)},
                **{"arm.L": (-75, -95, 0, -10, 0), "arm.R": (-65, -88, 0, 10, 0), "chest:scale": (1, 1.06, 1)})
    hold = M_(strike, hips_loc=(0, -0.20, -0.18), spine=(42, 0, 0), **{"chest:scale": (1, 1, 1)})
    rig.author_action(arm, f"{NAME}_Attack", 36,
                      [(1, STANCE), (8, windup), (18, windup2), (19, strike), (26, hold), (36, STANCE)],
                      modes={1: "BEZIER", 8: "LINEAR", 18: "CONSTANT", 19: "LINEAR", 26: "BEZIER"},
                      chain_fn=RAG(18, (10, 8, 6), (8, 10, 12)), chain_step=1)


def anim_hurt_death(arm):
    hurt = M_(STANCE, hips_loc=(0, 0.12, -0.06), spine=(0, 0, 0), chest=(-12, -8, 0), neck=(-8, 0, 0), head=(-20, 0, 0),
              feet={"L": (-0.10, 0.09, 0), "R": (0.24, 0.09, 0)},
              **{"arm.L": (-60, -70, 0, -30, 0), "arm.R": (-50, -60, 0, 30, 0)})
    rig.author_action(arm, f"{NAME}_Hurt", 14, [(1, STANCE), (2, hurt), (6, hurt), (14, STANCE)],
                      modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"}, chain_fn=RAG(14, (14, 10, 8), (8, 10, 12)),
                      chain_step=1)
    stagger = M_(STANCE, hips_loc=(0, 0.14, -0.06), spine=(-6, 0, 0), chest=(-16, -10, 0), head=(-26, 0, 0),
                 feet={"L": (-0.06, 0.09, 0), "R": (0.28, 0.09, 0)},
                 **{"arm.L": (-80, -90, 0, -40, 0), "arm.R": (-70, -80, 0, 40, 0)})
    knees = M_(STANCE, hips_loc=(0, 0.02, -0.46), spine=(30, 0, 0), chest=(20, 0, 0), neck=(-10, 0, 0), head=(10, 0, 0),
               **{"arm.L": (-10, -20, 0, -10, 0), "arm.R": (0, -10, 0, 10, 0)})
    knees.pop("feet")
    knees["legs"] = {"L": (-90, 0, 60), "R": (-80, 10, 60)}
    down = {
        "hips_loc": (0, -0.35, -0.74), "hips": (78, 0, 0), "spine": (10, 0, 0), "chest": (6, 0, 0),
        "neck": (-20, 0, 0), "head": (-10, 20, 0),
        "legs": {"L": (95, 105, 40), "R": (88, 98, 40)},
        "upper_arm.L": (-150, 0, -20), "forearm.L": (-20, 0, 0),
        "upper_arm.R": (-140, 0, 20), "forearm.R": (-30, 0, 0),
    }
    rig.author_action(arm, f"{NAME}_Death", 40, [(1, STANCE), (5, stagger), (16, knees), (26, down), (40, down)],
                      modes={1: "LINEAR", 5: "BEZIER", 16: "BEZIER", 26: "CONSTANT"},
                      chain_fn=RAG(20, (20, 14, 10), (6, 8, 10)), chain_step=2)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build(live=True, size=2048):
    if not live:
        dc.reset_scene()
    coll = dc.collection(COLL)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for act in [a for a in bpy.data.actions if a.get("dc_owner") == NAME]:
        bpy.data.actions.remove(act)
    M = make_materials()
    parts = build_body(M)
    for p in parts:
        dc.move_to(p, coll)
    joints = rig.mirror_joints(JOINTS_L)
    arm = rig.build_armature(f"{NAME}_Rig", joints, PARENTS, non_deform=("root",))
    dc.move_to(arm, coll)
    for obj in parts:
        if "dc_rigid" in obj:
            dc.weight_by_segments(obj, [], arm, rigid=obj["dc_rigid"])
        else:
            dc.weight_by_segments(obj, obj["dc_bones"].split(","), arm, power=obj.get("dc_power", 6.0))
    print(f"[zombie] model tris={sum(_tris(o) for o in parts)}")

    # Bake far from everything else so AO is self-contained.
    for p in parts:
        p.location = (0, 30, 0)
    dc.uv_atlas_multi(parts, island_margin=0.003, importance={"M_ZSkin": 1.2, "M_ZEye": 0.6, "M_ZRope": 0.7})
    pairs = [(p, dc.make_highpoly(p, bevel_width=0.004, subsurf=1)) for p in parts]
    paths = dc.bake_texture_set(parts, TEX_DIR, NAME, size=size, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    for p in parts:
        p.location = (0, 0, 0)
    body = dc.join(parts, f"{NAME}_Body")
    body.data.materials.clear()
    body.data.materials.append(dc.baked_material(f"M_{NAME}", paths, emission_strength=3.0))
    rig.bind(body, arm)
    tri = body.modifiers.new("NgonTriangulate", "TRIANGULATE")
    tri.min_vertices = 5
    with bpy.context.temp_override(object=body):
        bpy.ops.object.modifier_move_to_index(modifier=tri.name, index=0)

    existing = set(bpy.data.actions.keys())
    arm["dc_zombie"] = 1.0
    anim_idle(arm)
    anim_run(arm)
    anim_attack(arm)
    anim_hurt_death(arm)
    new_actions = [a for a in bpy.data.actions if a.name not in existing]
    for a in new_actions:
        a["dc_owner"] = NAME
        # A channel only this rig can resolve keeps the FBX exporter from
        # attaching these clips to other armatures in the same file.
        arm.animation_data.action = a
        arm.keyframe_insert('["dc_zombie"]', frame=1)

    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    dc.export_fbx(OUT_DIR / f"{NAME}.fbx", [arm, body], animated=True)
    meta = {a.name[len(NAME) + 1:]: int(a.get("dc_length", a.frame_range[1])) for a in new_actions}
    (OUT_DIR / f"{NAME}_clips.json").write_text(json.dumps(meta, indent=2))
    arm.animation_data.action = bpy.data.actions[f"{NAME}_Idle"]
    arm.location = DISPLAY_OFFSET
    print("[zombie] exported", meta)
    return arm


if __name__ == "__main__":
    build(live=False)
