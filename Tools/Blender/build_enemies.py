"""Story enemies: Sentinel, Monk, Fisher, RoyalGuardian, TimeKeeper (rigged,
animated) plus the procedural-animated creatures Vermin, Tick, MossBlob and
Obelisk, and the two oversized weapons (Greatsword, Shovel).

Run headless:   Blender -b --factory-startup -P Tools/Blender/build_enemies.py -- [names...]
Live (MCP):     import build_enemies as be; be.build("Sentinel")
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
from build_zombie import JOINTS_L as ZOMBIE_JOINTS_L, PARENTS as BASE_PARENTS  # noqa: E402

CHAR_ROOT = dc.ART_ROOT / "Characters"
DISPLAY = {
    "Sentinel": (3.4, 0), "Monk": (5.0, 0), "Fisher": (6.6, 0), "RoyalGuardian": (8.6, 0), "TimeKeeper": (11.6, 0),
    "Creatures": (0, 3.0),
}


def scaled_joints(scale, overrides=None, stretch=None):
    """Zombie skeleton scaled; `stretch` = {bone: (sx, sy, sz)} per-bone multipliers on head/tail."""
    out = {}
    for name, (h, t) in ZOMBIE_JOINTS_L.items():
        h = Vector(h) * scale
        t = Vector(t) * scale
        if stretch and name in stretch:
            sx, sy, sz = stretch[name]
            h = Vector((h.x * sx, h.y * sy, h.z * sz))
            t = Vector((t.x * sx, t.y * sy, t.z * sz))
        out[name] = (tuple(h), tuple(t))
    if overrides:
        out.update(overrides)
    return rig.mirror_joints(out)


def P(pose, s):
    """Scale positional parts of a pose (hips offset, IK targets) by skeleton scale."""
    out = dict(pose)
    if "hips_loc" in out:
        out["hips_loc"] = tuple(v * s for v in out["hips_loc"])
    if "feet" in out:
        out["feet"] = {k: (v[0] * s, v[1] * s, v[2]) for k, v in out["feet"].items()}
    return out


def M_(base, **kw):
    return rig.merge(base, **kw)


# ---------------------------------------------------------------------------
# Generic character pipeline (mirrors build_zombie.build)
# ---------------------------------------------------------------------------

def build_character(name, joints, parents, make_materials, build_parts, animate, size=2048, extra_export=None):
    coll = dc.collection(name)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for act in [a for a in bpy.data.actions if a.get("dc_owner") == name]:
        bpy.data.actions.remove(act)
    out_dir = CHAR_ROOT / name
    M = make_materials()
    parts = build_parts(M)
    for p in parts:
        dc.move_to(p, coll)
    arm = rig.build_armature(f"{name}_Rig", joints, parents, non_deform=("root", "weapon_socket", "offhand_socket"))
    dc.move_to(arm, coll)
    for obj in parts:
        if "dc_rigid" in obj:
            dc.weight_by_segments(obj, [], arm, rigid=obj["dc_rigid"])
        else:
            dc.weight_by_segments(obj, obj["dc_bones"].split(","), arm, power=obj.get("dc_power", 6.0))
    print(f"[{name}] model tris={sum(_tris(o) for o in parts)}")

    for p in parts:
        p.location = (0, 40, 0)
    dc.uv_atlas_multi(parts, island_margin=0.003, importance={"Glow": 0.6})
    pairs = [(p, dc.make_highpoly(p, bevel_width=0.004, subsurf=1)) for p in parts]
    paths = dc.bake_texture_set(parts, out_dir / "Textures", name, size=size, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    for p in parts:
        p.location = (0, 0, 0)
    body = dc.join(parts, f"{name}_Body")
    body.data.materials.clear()
    body.data.materials.append(dc.baked_material(f"M_{name}", paths, emission_strength=3.0))
    rig.bind(body, arm)
    tri = body.modifiers.new("NgonTriangulate", "TRIANGULATE")
    tri.min_vertices = 5
    with bpy.context.temp_override(object=body):
        bpy.ops.object.modifier_move_to_index(modifier=tri.name, index=0)

    existing = set(bpy.data.actions.keys())
    tag_prop = f"dc_{name.lower()}"
    arm[tag_prop] = 1.0
    animate(arm, name)
    new_actions = [a for a in bpy.data.actions if a.name not in existing]
    for a in new_actions:
        a["dc_owner"] = name
        arm.animation_data.action = a
        arm.keyframe_insert(f'["{tag_prop}"]', frame=1)

    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    dc.export_fbx(out_dir / f"{name}.fbx", [arm, body], animated=True)
    meta = {a.name[len(name) + 1:]: int(a.get("dc_length", a.frame_range[1])) for a in new_actions}
    (out_dir / f"{name}_clips.json").write_text(json.dumps(meta, indent=2))
    idle = bpy.data.actions.get(f"{name}_Idle")
    if idle:
        arm.animation_data.action = idle
    dx, dy = DISPLAY.get(name, (0, 0))
    arm.location = (dx, dy, 0)
    if extra_export:
        extra_export(out_dir)
    print(f"[{name}] exported", meta)
    return arm


def act(arm, name, clip, length, keys, modes=None, chain_fn=None, step=2):
    return rig.author_action(arm, f"{name}_{clip}", length, keys, modes=modes, chain_fn=chain_fn, chain_step=step)


def rags(period, base, amp):
    return chains(period, (0, 0, 0, 0), (0, 0, 0, 0), base, amp)


def mat(name, base, dark, light, **kw):
    return dc.make_material(name, base, dark=dark, light=light, **kw)


# ===========================================================================
# 1. SENTINEL -- zombie palace sentinel whose forearms are brass clock hands
# ===========================================================================

S_SENT = 1.06


def sentinel_materials():
    return {
        "tabard": mat("M_SnTabard", "#2B3858", "#141B2C", "#465A84", noise_scale=6, noise_amt=0.8, rough=0.85,
                      stripes=("z", 6.0, 0.08, "#C9A35C"), edge_wear="#5D739C", edge_wear_amt=0.5, cavity_dirt=0.7),
        "iron": mat("M_SnIron", "#59636F", "#262C33", "#94A0AC", metal=1.0, rough=0.4, edge_wear="#E0E6EC",
                    edge_wear_amt=1.0, cavity_dirt=0.9, noise_scale=14),
        "brass": mat("M_SnBrass", "#A9824A", "#5A3E1C", "#E1BF7A", metal=1.0, rough=0.35, edge_wear="#FFE7A8",
                     edge_wear_amt=0.9, cavity_dirt=0.8, noise_scale=12),
        "skin": mat("M_SnSkin", "#8E9C86", "#4B5848", "#BCC9B0", rough=0.7, cavity_dirt=0.9, edge_wear="#DDE6CF",
                    edge_wear_amt=0.5, noise_scale=9),
        "glow": dc.make_material("Glow", "#F2E3B0", dark="#C9B27A", light="#FFF6D8", rough=0.3,
                                 emission="#FFFFFF", emission_strength=6.0),
    }


def sentinel_parts(M):
    s = S_SENT
    parts = []

    def V(x, y, z):
        return Vector((x * s, y * s, z * s))
    torso = dc.lathe("Sn_Torso", [(0.14, 0.86), (0.155, 0.95), (0.145, 1.04), (0.17, 1.15), (0.20, 1.25),
                                  (0.205, 1.32), (0.16, 1.38), (0.09, 1.42), (0.06, 1.46)],
                     segments=16, scale_xy=(1.0, 0.72))
    torso.data.transform(Matrix.Scale(s, 4))
    dc.subdivide(torso, 1)
    parts.append(tag(torso, M["tabard"], ["hips", "spine", "chest", "neck"]))
    plate = dc.lathe("Sn_Breastplate", [(0.205, 1.06), (0.215, 1.16), (0.235, 1.25), (0.235, 1.32), (0.19, 1.385)],
                     segments=18, scale_xy=(1.03, 0.8), cap_top=False, cap_bottom=False)
    delete_faces(plate, lambda c: c.y > 0.04)
    plate.data.transform(Matrix.Scale(s, 4))
    solidify(plate, 0.014, offset=1.0)
    parts.append(tag(plate, M["iron"], ["spine", "chest"]))
    # Tabard flaps front/back.
    for nm, ys in (("Sn_FlapF", -1), ("Sn_FlapB", 1)):
        bm = bmesh.new()
        grid = []
        for r in range(5):
            t = r / 4
            row = []
            for c in range(4):
                u = c / 3 - 0.5
                row.append(bm.verts.new((u * 0.24 * s, ys * (0.12 + 0.03 * t) * s, (0.98 - 0.42 * t) * s)))
            grid.append(row)
        for r in range(4):
            for c in range(3):
                f = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
                bm.faces.new(f if ys > 0 else tuple(reversed(f)))
        flap = dc.mesh_object(nm, bm)
        solidify(flap, 0.012, offset=0.0)
        bones = ["hips", "coat_L_01", "coat_L_02", "coat_R_01", "coat_R_02"] if ys > 0 else ["hips", "thigh.L", "thigh.R"]
        parts.append(tag(flap, M["tabard"], bones, power=5))
    belt = torus("Sn_Belt", V(0, 0, 0.96), 0.165 * s, 0.022 * s, 24, 6, scale=(1.0, 0.76, 1.3))
    parts.append(tag(belt, M["brass"], rigid="hips"))
    # Head: kettle helm with a clock face where the face should be.
    head = dc.ico("Sn_Head", 0.11 * s, (0, 0, 0), subdiv=2)
    dc.deform(head, lambda v: Vector((v.x, v.y * 1.05, v.z * 1.1)) + V(0, -0.03, 1.58))
    parts.append(tag(head, M["skin"], ["neck", "head"], power=10))
    helm = dc.lathe("Sn_Helm", [(0.0, 0.17), (0.08, 0.16), (0.12, 0.10), (0.13, 0.03), (0.21, 0.0), (0.22, -0.02)],
                    segments=18, cap_bottom=False)
    solidify(helm, 0.01, offset=1.0)
    transform(helm, Matrix.Translation(V(0, -0.03, 1.60)) @ Matrix.Scale(s, 4))
    parts.append(tag(helm, M["iron"], rigid="head"))
    face = dc.lathe("Sn_ClockFace", [(0.0, 0.012), (0.075, 0.01), (0.085, 0.0)], segments=20, cap_bottom=False)
    transform(face, Matrix.Translation(V(0, -0.135, 1.57)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Scale(s, 4))
    parts.append(tag(face, M["glow"], rigid="head"))
    rim = torus("Sn_FaceRim", V(0, -0.137, 1.57), 0.086 * s, 0.011 * s, 20, 6, rot=(math.pi / 2, 0, 0))
    parts.append(tag(rim, M["brass"], rigid="head"))
    for k, (ln, ang) in enumerate(((0.06, 30), (0.045, 150))):
        hand = dc.box(f"Sn_FaceHand{k}", (0.008 * s, 0.006 * s, ln * s), (0, 0, ln * s * 0.5))
        transform(hand, Matrix.Translation(V(0, -0.15, 1.57)) @ Matrix.Rotation(math.radians(ang), 4, "Y"))
        parts.append(tag(hand, M["brass"], rigid="head"))
    for side, sx in (("L", 1.0), ("R", -1.0)):
        upper = limb(f"Sn_Upper{side}", V(0.17 * sx, 0.01, 1.35), V(0.22 * sx, 0.02, 1.0),
                     [0.075 * s, 0.07 * s, 0.062 * s, 0.058 * s], segments=10)
        parts.append(tag(upper, M["tabard"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        pauld = dc.lathe(f"Sn_Pauld{side}", [(0.0, 0.06), (0.07, 0.05), (0.11, 0.0), (0.115, -0.04)], segments=12,
                         cap_bottom=False)
        solidify(pauld, 0.01, offset=1.0)
        transform(pauld, Matrix.Translation(V(0.2 * sx, 0.0, 1.37)) @ Matrix.Rotation(math.radians(25 * sx), 4, "Y") @ Matrix.Scale(s, 4))
        if sx < 0:
            pauld.data.flip_normals()
        parts.append(tag(pauld, M["brass"], [f"shoulder.{side}", f"upper_arm.{side}"], power=10))
        # Forearm replaced by a long brass clock hand: spade-tipped blade.
        e = V(0.222 * sx, 0.02, 1.02)
        w = V(0.245 * sx, -0.03, 0.55)
        pts = [e, e.lerp(w, 0.35), e.lerp(w, 0.7), w, w + (w - e).normalized() * 0.12 * s]
        blade = dc.tube_along(f"Sn_Hand{side}", pts, [0.045 * s, 0.03 * s, 0.024 * s, 0.05 * s, 0.0], segments=6,
                              up=Vector((0, 1, 0)), flatten=0.25)
        parts.append(tag(blade, M["brass"], rigid=f"forearm.{side}"))
        cog = torus(f"Sn_Cog{side}", e, 0.05 * s, 0.018 * s, 12, 6, rot=(0, math.pi / 2, 0))
        parts.append(tag(cog, M["iron"], [f"upper_arm.{side}", f"forearm.{side}"], power=8))
        thigh = limb(f"Sn_Thigh{side}", V(0.088 * sx, 0, 0.94), V(0.10 * sx, -0.03, 0.47),
                     [0.1 * s, 0.092 * s, 0.08 * s, 0.07 * s], segments=10)
        parts.append(tag(thigh, M["tabard"], ["hips", f"thigh.{side}", f"shin.{side}"]))
        greave = limb(f"Sn_Greave{side}", V(0.10 * sx, -0.03, 0.5), V(0.10 * sx, 0.02, 0.1),
                      [0.072 * s, 0.07 * s, 0.062 * s, 0.058 * s], segments=10)
        parts.append(tag(greave, M["iron"], [f"thigh.{side}", f"shin.{side}", f"foot.{side}"]))
        foot = dc.box(f"Sn_Foot{side}", (0.11 * s, 0.24 * s, 0.08 * s), V(0.10 * sx, -0.05, 0.04), bevel=0.02)
        parts.append(tag(foot, M["iron"], [f"shin.{side}", f"foot.{side}"], power=8))
    return parts


SN_STANCE = {
    "hips_loc": (0, 0.0, -0.05), "spine": (10, 0, 0), "chest": (6, 8, 0), "neck": (-10, 0, 0), "head": (-6, 4, 0),
    "feet": {"L": (-0.18, 0.09, 0), "R": (0.18, 0.09, 0)},
    "arm.L": (-40, -78, 0, -10, 0), "arm.R": (-30, -84, 0, 10, 0),
}


def sentinel_anims(arm, name):
    s = S_SENT
    st = P(SN_STANCE, s)
    breathe = P(M_(SN_STANCE, hips_loc=(0, 0, -0.065), chest=(9, 8, 0), **{"arm.L": (-44, -82, 0, -10, 0)}), s)
    act(arm, name, "Idle", 61, [(1, st), (31, breathe), (61, st)], chain_fn=rags(30, (2, 3, 4), (3, 4, 5)), step=3)
    keys = []
    for f in range(1, 26, 2):
        p = (f - 1) / 24.0
        c, sn = math.cos(math.tau * p), math.sin(math.tau * p)

        def foot(q):
            if q < 0.45:
                u = q / 0.45
                return (-0.26 + 0.52 * u, 0.09, 0)
            u = (q - 0.45) / 0.55
            return (0.26 - 0.52 * u * u * (3 - 2 * u), 0.09 + 0.24 * math.sin(math.pi * u), 25 * (1 - u))
        keys.append((f, P({"hips_loc": (0, -0.02, -0.08 - 0.03 * math.cos(2 * math.tau * p)), "spine": (20, 0, 0),
                           "chest": (10, 8 * sn, 0), "neck": (-20, 0, 0), "head": (-10, 0, 0),
                           "feet": {"L": foot(p), "R": foot((p + 0.5) % 1.0)},
                           "arm.L": (-60 + 10 * c, -84 + 8 * c, 0, -12, 0), "arm.R": (-55 - 10 * c, -84 - 8 * c, 0, 12, 0)}, s)))
    act(arm, name, "Run", 25, keys, chain_fn=rags(12, (18, 12, 8), (6, 9, 12)), step=1)
    wind = P(M_(SN_STANCE, hips_loc=(0, 0.10, -0.12), spine=(-2, 0, 0), chest=(-10, 0, 0), head=(-16, 0, 0),
                feet={"L": (-0.16, 0.09, 0), "R": (0.28, 0.09, 0)},
                **{"arm.L": (60, 20, 0, -18, 0), "arm.R": (70, 30, 0, 18, 0)}), s)
    thrust = P(M_(SN_STANCE, hips_loc=(0, -0.26, -0.13), spine=(30, 0, 0), chest=(16, 0, 0), head=(-24, 0, 0),
                  feet={"L": (-0.52, 0.09, 0), "R": (0.30, 0.12, 20)},
                  **{"arm.L": (-88, -92, 0, -6, 0), "arm.R": (-84, -90, 0, 6, 0), "chest:scale": (1, 1.06, 1)}), s)
    hold = M_(thrust, hips_loc=(0, -0.24 * s, -0.14 * s), **{"chest:scale": (1, 1, 1)})
    act(arm, name, "Attack", 34, [(1, st), (10, wind), (16, wind), (17, thrust), (24, hold), (34, st)],
        modes={1: "BEZIER", 10: "LINEAR", 16: "CONSTANT", 17: "LINEAR", 24: "BEZIER"},
        chain_fn=rags(17, (10, 8, 6), (8, 10, 12)), step=1)
    hurt = P(M_(SN_STANCE, hips_loc=(0, 0.12, -0.06), spine=(-4, 0, 0), chest=(-14, -8, 0), head=(-20, 0, 0),
                feet={"L": (-0.10, 0.09, 0), "R": (0.24, 0.09, 0)}, **{"arm.L": (-70, -60, 0, -30, 0), "arm.R": (-60, -50, 0, 30, 0)}), s)
    act(arm, name, "Hurt", 14, [(1, st), (2, hurt), (6, hurt), (14, st)], modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"},
        chain_fn=rags(14, (14, 10, 8), (8, 10, 12)), step=1)
    _death(arm, name, s, st)


def _death(arm, name, s, st, step=2):
    stagger = P({"hips_loc": (0, 0.14, -0.06), "spine": (-6, 0, 0), "chest": (-16, -10, 0), "head": (-26, 0, 0),
                 "feet": {"L": (-0.06, 0.09, 0), "R": (0.28, 0.09, 0)},
                 "arm.L": (-80, -90, 0, -40, 0), "arm.R": (-70, -80, 0, 40, 0)}, s)
    knees = P({"hips_loc": (0, 0.02, -0.46), "spine": (30, 0, 0), "chest": (20, 0, 0), "neck": (-10, 0, 0), "head": (10, 0, 0),
               "arm.L": (-10, -20, 0, -10, 0), "arm.R": (0, -10, 0, 10, 0), "legs": {"L": (-90, 0, 60), "R": (-80, 10, 60)}}, s)
    down = {
        "hips_loc": (0, -0.35 * s, -0.74 * s), "hips": (78, 0, 0), "spine": (10, 0, 0), "chest": (6, 0, 0),
        "neck": (-20, 0, 0), "head": (-10, 20, 0), "legs": {"L": (95, 105, 40), "R": (88, 98, 40)},
        "upper_arm.L": (-150, 0, -20), "forearm.L": (-20, 0, 0), "upper_arm.R": (-140, 0, 20), "forearm.R": (-30, 0, 0),
    }
    act(arm, name, "Death", 40, [(1, st), (5, stagger), (16, knees), (26, down), (40, down)],
        modes={1: "LINEAR", 5: "BEZIER", 16: "BEZIER", 26: "CONSTANT"}, chain_fn=rags(20, (20, 14, 10), (6, 8, 10)), step=step)


# ===========================================================================
# 2. MONK -- floating robed monk whose head blossomed into a carnivorous orchid lantern
# ===========================================================================

S_MONK = 1.0


def monk_materials():
    return {
        "robe": mat("M_MkRobe", "#5A1E2A", "#2A0C12", "#82343F", noise_scale=5, noise_amt=0.9, rough=0.9,
                    stripes=("z", 3.0, 0.05, "#D9CDB0"), edge_wear="#A0505A", edge_wear_amt=0.5, cavity_dirt=0.8),
        "bone": mat("M_MkBone", "#D8CFB4", "#8C8166", "#F2EBD7", rough=0.6, cavity_dirt=0.9, edge_wear="#FFFFFF",
                    edge_wear_amt=0.4, noise_scale=10),
        "petal": mat("M_MkPetal", "#C25A9A", "#5E1D4A", "#F0B6DA", rough=0.55, noise_scale=7, noise_amt=0.9,
                     stripes=("z", 40.0, 0.06, "#4A0F35"), cavity_dirt=0.6, edge_wear="#FFE3F4", edge_wear_amt=0.6),
        "glow": dc.make_material("Glow", "#E7FF8A", dark="#B6D24A", light="#FBFFD0", rough=0.3, emission="#FFFFFF",
                                 emission_strength=6.0),
    }


def monk_parts(M):
    parts = []
    rnd = random.Random(5)
    robe = dc.lathe("Mk_Robe", [(0.07, 1.46), (0.15, 1.40), (0.20, 1.30), (0.21, 1.15), (0.24, 0.95), (0.30, 0.65),
                                (0.37, 0.35), (0.42, 0.12)], segments=20, scale_xy=(1.0, 0.85), cap_bottom=False)
    for v in robe.data.vertices:
        if v.co.z < 0.2:
            v.co.z += rnd.uniform(-0.06, 0.05)
    robe.data.update()
    solidify(robe, 0.012, offset=1.0)
    parts.append(tag(robe, M["robe"], ["hips", "spine", "chest", "neck", "thigh.L", "thigh.R", "coat_L_01", "coat_L_02",
                                      "coat_L_03", "coat_R_01", "coat_R_02", "coat_R_03"], power=4))
    hood = dc.lathe("Mk_Cowl", [(0.10, 1.48), (0.17, 1.45), (0.2, 1.38), (0.17, 1.33)], segments=18, scale_xy=(1.0, 0.9))
    parts.append(tag(hood, M["robe"], ["chest", "neck"]))
    sash = dc.box("Mk_Sash", (0.1, 0.02, 0.9), (0.06, -0.205, 0.9), bevel=0.01)
    parts.append(tag(sash, M["bone"], ["hips", "spine", "chest"], power=4))
    for side, sx in (("L", 1.0), ("R", -1.0)):
        sleeve = limb(f"Mk_Sleeve{side}", Vector((0.17 * sx, 0.01, 1.36)), Vector((0.24 * sx, -0.02, 0.76)),
                      [0.07, 0.075, 0.085, 0.10, 0.12], segments=12)
        parts.append(tag(sleeve, M["robe"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        hand = dc.box(f"Mk_Hand{side}", (0.05, 0.07, 0.11), (0.25 * sx, -0.04, 0.66), bevel=0.015)
        parts.append(tag(hand, M["bone"], rigid=f"hand.{side}"))
        for k in range(3):
            fx = 0.25 * sx + (k - 1) * 0.015
            claw = dc.tube_along(f"Mk_Finger{side}{k}", [(fx, -0.06, 0.62), (fx, -0.075, 0.55), (fx, -0.06, 0.5)],
                                 [0.009, 0.007, 0.0], segments=5)
            parts.append(tag(claw, M["bone"], rigid=f"hand.{side}"))
    # Orchid lantern head on a stalk.
    stalk = dc.tube_along("Mk_Stalk", [(0, -0.01, 1.42), (0, -0.03, 1.52), (0, -0.05, 1.6)], [0.035, 0.03, 0.03], segments=8)
    parts.append(tag(stalk, M["petal"], ["neck", "head"], power=8))
    core = dc.ico("Mk_Core", 0.075, (0, -0.07, 1.66), subdiv=2)
    parts.append(tag(core, M["glow"], rigid="head"))
    for k in range(6):
        a = math.tau * k / 6 + 0.3
        d = Vector((math.cos(a), 0.0, math.sin(a)))
        base = Vector((0, -0.07, 1.66)) + d * 0.05
        pts = [base, base + d * 0.12 + Vector((0, -0.06, 0)), base + d * 0.22 + Vector((0, -0.02, 0.03 if k % 2 else -0.02))]
        petal = dc.tube_along(f"Mk_Petal{k}", pts, [0.03, 0.06, 0.0], segments=8, up=Vector((0, -1, 0)), flatten=0.25)
        parts.append(tag(petal, M["petal"], rigid="head"))
    for k in range(8):
        a = math.tau * k / 8
        p = Vector((math.cos(a) * 0.07, -0.1, 1.66 + math.sin(a) * 0.07))
        tooth = dc.tube_along(f"Mk_Tooth{k}", [p, p + Vector((-math.cos(a) * 0.02, -0.03, -math.sin(a) * 0.02))],
                              [0.01, 0.0], segments=4)
        parts.append(tag(tooth, M["bone"], rigid="head"))
    return parts


MK_STANCE = {
    "hips_loc": (0, 0, 0.18), "spine": (8, 0, 0), "chest": (4, 0, 0), "neck": (-6, 0, 0), "head": (-10, 0, 0),
    "legs": {"L": (-6, 4, 40), "R": (6, 10, 40)},
    "arm.L": (-40, -100, 0, -6, 0), "arm.R": (-40, -100, 0, 6, 0),
}


def monk_anims(arm, name):
    st = MK_STANCE
    up = M_(st, hips_loc=(0, 0, 0.26), chest=(2, 0, 0), head=(-14, 6, 0))
    act(arm, name, "Idle", 61, [(1, st), (31, up), (61, st)], chain_fn=rags(30, (4, 3, 2), (4, 6, 8)), step=3)
    lean = M_(st, spine=(22, 0, 0), chest=(10, 0, 0), head=(-4, 0, 0), **{"arm.L": (-20, -60, 0, -6, 0), "arm.R": (-20, -60, 0, 6, 0)})
    lean2 = M_(lean, hips_loc=(0, 0, 0.24))
    act(arm, name, "Run", 25, [(1, lean), (13, lean2), (25, lean)], chain_fn=rags(12, (30, 20, 12), (6, 9, 12)), step=2)
    raise_ = M_(st, hips_loc=(0, 0.04, 0.3), spine=(-6, 0, 0), chest=(-12, 0, 0), head=(-26, 0, 0),
                **{"arm.L": (-160, -175, 0, -30, 0), "arm.R": (-160, -175, 0, 30, 0)})
    push = M_(st, hips_loc=(0, -0.06, 0.2), spine=(18, 0, 0), chest=(10, 0, 0), head=(-4, 0, 0),
              **{"arm.L": (-92, -95, 0, -10, 0), "arm.R": (-92, -95, 0, 10, 0), "chest:scale": (1, 1.05, 1)})
    act(arm, name, "Cast", 40, [(1, st), (14, raise_), (20, raise_), (22, push), (30, push), (40, st)],
        modes={1: "BEZIER", 14: "LINEAR", 20: "CONSTANT", 22: "LINEAR", 30: "BEZIER"}, chain_fn=rags(20, (14, 10, 8), (8, 10, 12)), step=1)
    hurt = M_(st, hips_loc=(0, 0.14, 0.2), spine=(-12, 0, 0), chest=(-14, -10, 0), head=(-24, 0, 0),
              **{"arm.L": (-60, -50, 0, -30, 0), "arm.R": (-50, -40, 0, 30, 0)})
    act(arm, name, "Hurt", 14, [(1, st), (2, hurt), (6, hurt), (14, st)], modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"},
        chain_fn=rags(14, (16, 12, 8), (8, 10, 12)), step=1)
    sink = M_(st, hips_loc=(0, 0.05, -0.55), spine=(40, 0, 0), chest=(30, 0, 0), head=(30, 0, 0),
              **{"arm.L": (10, 0, 0, -20, 0), "arm.R": (10, 0, 0, 20, 0)})
    act(arm, name, "Death", 40, [(1, st), (6, hurt), (24, sink), (40, sink)], modes={1: "LINEAR", 6: "BEZIER", 24: "CONSTANT"},
        chain_fn=rags(20, (30, 20, 10), (6, 8, 10)), step=2)


# ===========================================================================
# 3. FISHER -- lanky fisherfolk with an eel for a tongue, harpoon thrower
# ===========================================================================

S_FISH = 1.08


def fisher_materials():
    return {
        "coat": mat("M_FiCoat", "#4B5230", "#22261A", "#6E7848", noise_scale=6, noise_amt=0.9, rough=0.55,
                    edge_wear="#8E9864", edge_wear_amt=0.6, cavity_dirt=0.8),
        "skin": mat("M_FiSkin", "#7C918A", "#3E4E4A", "#AFC4BC", rough=0.45, noise_scale=12, noise_amt=0.8,
                    cavity_dirt=0.9, edge_wear="#D3E6DE", edge_wear_amt=0.5),
        "straw": mat("M_FiStraw", "#B99D5C", "#6E5A2E", "#E2CB8C", rough=0.9, stripes=("z", 60.0, 0.2, "#7A6330"),
                     cavity_dirt=0.6),
        "eel": mat("M_FiEel", "#3E3A5E", "#1A1830", "#6B6894", rough=0.3, noise_scale=20, noise_amt=0.8,
                   cavity_dirt=0.7, edge_wear="#9C9AD0", edge_wear_amt=0.6),
        "glow": dc.make_material("Glow", "#A8F0FF", dark="#5CC8E0", light="#E8FCFF", rough=0.3, emission="#FFFFFF",
                                 emission_strength=6.0),
        "rope": mat("M_FiRope", "#8E7550", "#4A3A24", "#B89A6C", rough=0.9, stripes=("z", 120.0, 0.25, "#3A2C18")),
    }


def fisher_parts(M):
    s = S_FISH
    parts = []
    rnd = random.Random(9)

    def V(x, y, z):
        return Vector((x * s, y * s, z * s))
    torso = dc.lathe("Fi_Torso", [(0.12, 0.86), (0.135, 0.95), (0.12, 1.04), (0.14, 1.15), (0.16, 1.25), (0.16, 1.32),
                                  (0.12, 1.38), (0.07, 1.42)], segments=14, scale_xy=(1.0, 0.75))
    torso.data.transform(Matrix.Scale(s, 4))
    parts.append(tag(torso, M["skin"], ["hips", "spine", "chest", "neck"]))
    coat = dc.lathe("Fi_Coat", [(0.15, 1.38), (0.18, 1.3), (0.18, 1.15), (0.16, 1.02), (0.19, 0.85), (0.23, 0.62),
                                (0.26, 0.48)], segments=20, scale_xy=(1.05, 0.85), cap_top=False, cap_bottom=False)
    delete_faces(coat, lambda c: (c.y < -0.08 and abs(c.x) < 0.07) or (c.y > 0.08 and abs(c.x) < 0.03 and c.z < 0.8))
    for v in coat.data.vertices:
        if v.co.z < 0.55:
            v.co.z += rnd.uniform(-0.05, 0.03)
    coat.data.transform(Matrix.Scale(s, 4))
    solidify(coat, 0.012, offset=1.0)
    parts.append(tag(coat, M["coat"], ["hips", "spine", "chest", "thigh.L", "thigh.R", "coat_L_01", "coat_L_02", "coat_L_03",
                                       "coat_R_01", "coat_R_02", "coat_R_03"], power=5))
    belt = torus("Fi_Rope", V(0, 0, 0.98), 0.17 * s, 0.016 * s, 22, 6, scale=(1.0, 0.8, 1.0))
    parts.append(tag(belt, M["rope"], rigid="hips"))
    head = dc.ico("Fi_Head", 0.12 * s, (0, 0, 0), subdiv=2)

    def fishy(v):
        p = Vector((v.x * 0.95, v.y * 1.2, v.z * 0.95))
        if p.y < -0.05 and p.z < 0.0:
            p.y -= 0.03
        return p + V(0, -0.04, 1.58)
    dc.deform(head, fishy)
    parts.append(tag(head, M["skin"], ["neck", "head"], power=10))
    for sx in (1, -1):
        eye = dc.ico(f"Fi_Eye{sx}", 0.024 * s, V(0.07 * sx, -0.14, 1.62), subdiv=1)
        parts.append(tag(eye, M["glow"], rigid="head"))
    # Eel tongue hanging from the mouth, with a dorsal fin.
    pts = [V(0, -0.16, 1.53), V(0.01, -0.22, 1.47), V(0.03, -0.24, 1.38), V(0.02, -0.21, 1.28), V(-0.01, -0.2, 1.2)]
    eel = dc.tube_along("Fi_Eel", pts, [0.03 * s, 0.032 * s, 0.028 * s, 0.02 * s, 0.006 * s], segments=8)
    parts.append(tag(eel, M["eel"], ["head", "neck"], power=6))
    fin = dc.tube_along("Fi_EelFin", [V(0.01, -0.25, 1.46), V(0.03, -0.27, 1.38), V(0.02, -0.24, 1.3)],
                        [0.015 * s, 0.02 * s, 0.0], segments=6, up=Vector((1, 0, 0)), flatten=0.2)
    parts.append(tag(fin, M["eel"], ["head", "neck"], power=6))
    hat = dc.lathe("Fi_Hat", [(0.0, 0.16), (0.06, 0.14), (0.13, 0.06), (0.26, 0.0), (0.27, -0.015)], segments=20)
    transform(hat, Matrix.Translation(V(0, -0.03, 1.66)) @ Matrix.Scale(s, 4))
    parts.append(tag(hat, M["straw"], rigid="head"))
    for side, sx in (("L", 1.0), ("R", -1.0)):
        upper = limb(f"Fi_Upper{side}", V(0.15 * sx, 0.01, 1.33), V(0.2 * sx, 0.02, 0.98), [0.06 * s, 0.055 * s, 0.05 * s],
                     segments=10)
        parts.append(tag(upper, M["coat"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        fore = limb(f"Fi_Fore{side}", V(0.2 * sx, 0.02, 1.0), V(0.22 * sx, -0.02, 0.72), [0.045 * s, 0.04 * s, 0.035 * s],
                    segments=10)
        parts.append(tag(fore, M["skin"], [f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"]))
        hand = dc.box(f"Fi_Hand{side}", (0.06 * s, 0.09 * s, 0.08 * s), V(0.225 * sx, -0.035, 0.67), bevel=0.015)
        parts.append(tag(hand, M["skin"], rigid=f"hand.{side}"))
        thigh = limb(f"Fi_Thigh{side}", V(0.085 * sx, 0, 0.93), V(0.10 * sx, -0.03, 0.47), [0.075 * s, 0.07 * s, 0.06 * s],
                     segments=10)
        parts.append(tag(thigh, M["coat"], ["hips", f"thigh.{side}", f"shin.{side}"]))
        shin = limb(f"Fi_Shin{side}", V(0.10 * sx, -0.03, 0.5), V(0.10 * sx, 0.02, 0.08), [0.05 * s, 0.045 * s, 0.04 * s],
                    segments=10)
        parts.append(tag(shin, M["skin"], [f"thigh.{side}", f"shin.{side}", f"foot.{side}"]))
        foot = dc.box(f"Fi_Foot{side}", (0.1 * s, 0.24 * s, 0.05 * s), V(0.10 * sx, -0.07, 0.025), bevel=0.02)
        parts.append(tag(foot, M["skin"], [f"shin.{side}", f"foot.{side}"], power=8))
    return parts


FI_STANCE = {
    "hips_loc": (0, 0.02, -0.08), "spine": (26, 0, 0), "chest": (14, 6, 0), "neck": (-26, 0, 0), "head": (-12, 0, 0),
    "feet": {"L": (-0.17, 0.09, 0), "R": (0.18, 0.09, 0)},
    "arm.L": (-20, -50, 0, -10, 0), "arm.R": (-10, -40, -40, 10, 0),
}


def fisher_anims(arm, name):
    s = S_FISH
    st = P(FI_STANCE, s)
    sway = P(M_(FI_STANCE, hips_loc=(0, 0.02, -0.095), chest=(16, 2, 4), head=(-10, 10, -4)), s)
    act(arm, name, "Idle", 61, [(1, st), (31, sway), (61, st)], chain_fn=rags(30, (2, 3, 4), (3, 4, 5)), step=3)
    keys = []
    for f in range(1, 26, 2):
        p = (f - 1) / 24.0
        c, sn = math.cos(math.tau * p), math.sin(math.tau * p)

        def foot(q):
            if q < 0.4:
                u = q / 0.4
                return (-0.3 + 0.6 * u, 0.09, 0)
            u = (q - 0.4) / 0.6
            return (0.3 - 0.6 * u * u * (3 - 2 * u), 0.09 + 0.3 * math.sin(math.pi * u), 30 * (1 - u))
        keys.append((f, P({"hips_loc": (0, -0.02, -0.1 - 0.035 * math.cos(2 * math.tau * p)), "spine": (30, 0, 0),
                           "chest": (14, 10 * sn, 0), "neck": (-30, 0, 0), "head": (-14, 0, 0),
                           "feet": {"L": foot(p), "R": foot((p + 0.5) % 1.0)},
                           "arm.L": (10 + 40 * c, -40 + 30 * c, 0, -12, 0), "arm.R": (30 - 30 * c, 0 - 20 * c, -60, 12, 0)}, s)))
    act(arm, name, "Run", 25, keys, chain_fn=rags(12, (25, 16, 10), (6, 9, 12)), step=1)
    wind = P(M_(FI_STANCE, hips_loc=(0, 0.1, -0.1), spine=(4, -14, 0), chest=(-8, -24, 0), head=(-20, 10, 0),
                feet={"L": (-0.2, 0.09, 0), "R": (0.26, 0.09, 0)},
                **{"arm.L": (-80, -100, 0, -20, 0), "arm.R": (155, 100, 160, 20, 0)}), s)
    throw = P(M_(FI_STANCE, hips_loc=(0, -0.14, -0.12), spine=(34, 16, 0), chest=(16, 26, 0), head=(-20, -10, 0),
                 feet={"L": (-0.38, 0.09, 0), "R": (0.3, 0.12, 15)},
                 **{"arm.L": (40, 20, 0, -30, 0), "arm.R": (-100, -118, -40, 10, 0)}), s)
    act(arm, name, "Throw", 36, [(1, st), (12, wind), (18, wind), (19, throw), (26, throw), (36, st)],
        modes={1: "BEZIER", 12: "LINEAR", 18: "CONSTANT", 19: "LINEAR", 26: "BEZIER"}, chain_fn=rags(18, (12, 8, 6), (8, 10, 12)), step=1)
    crouch = P(M_(FI_STANCE, hips_loc=(0, 0.04, -0.3), spine=(40, 0, 0), chest=(20, 0, 0), feet={"L": (-0.18, 0.09, 0), "R": (0.2, 0.09, 10)},
                  **{"arm.L": (40, 10, 0, -20, 0), "arm.R": (50, 20, 0, 20, 0)}), s)
    air = P({"hips_loc": (0, 0, 0.0), "spine": (20, 0, 0), "chest": (6, 0, 0), "neck": (-20, 0, 0), "head": (-10, 0, 0),
             "legs": {"L": (-70, -10, 30), "R": (30, 80, 40)},
             "arm.L": (-120, -150, 0, -30, 0), "arm.R": (-110, -140, -60, 30, 0)}, s)
    act(arm, name, "Leap", 24, [(1, st), (6, crouch), (10, air), (24, air)], modes={1: "BEZIER", 6: "LINEAR", 10: "BEZIER"},
        chain_fn=rags(12, (30, 20, 14), (8, 10, 12)), step=1)
    hurt = P(M_(FI_STANCE, hips_loc=(0, 0.12, -0.06), spine=(4, 0, 0), chest=(-12, -8, 0), head=(-22, 0, 0),
                feet={"L": (-0.1, 0.09, 0), "R": (0.24, 0.09, 0)}, **{"arm.L": (-60, -70, 0, -30, 0), "arm.R": (-50, -60, 0, 30, 0)}), s)
    act(arm, name, "Hurt", 14, [(1, st), (2, hurt), (6, hurt), (14, st)], modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"},
        chain_fn=rags(14, (14, 10, 8), (8, 10, 12)), step=1)
    _death(arm, name, s, st)


# ===========================================================================
# 4. ROYAL GUARDIAN -- towering knight with a greatsword the size of a church door
# ===========================================================================

S_GUARD = 1.38


def guardian_materials():
    return {
        "plate": mat("M_GdPlate", "#6A7280", "#2A2F38", "#B3BCC8", metal=1.0, rough=0.32, edge_wear="#F2F6FA",
                     edge_wear_amt=1.0, cavity_dirt=0.9, noise_scale=12),
        "gold": mat("M_GdGold", "#B8924A", "#5E461F", "#F0D28A", metal=1.0, rough=0.3, edge_wear="#FFF0C0",
                    edge_wear_amt=0.9, cavity_dirt=0.8),
        "cape": mat("M_GdCape", "#5E1838", "#2A0818", "#8E2E56", rough=0.85, noise_scale=5, noise_amt=0.9,
                    edge_wear="#B04A74", edge_wear_amt=0.5, cavity_dirt=0.7),
        "cloth": mat("M_GdCloth", "#26213A", "#100D1C", "#3E3660", rough=0.85, cavity_dirt=0.7),
        "glow": dc.make_material("Glow", "#FF5A3A", dark="#C02A14", light="#FFC0A0", rough=0.3, emission="#FFFFFF",
                                 emission_strength=6.0),
    }


def guardian_parts(M):
    s = S_GUARD
    parts = []

    def V(x, y, z):
        return Vector((x * s, y * s, z * s))
    torso = dc.lathe("Gd_Torso", [(0.15, 0.86), (0.17, 0.95), (0.16, 1.04), (0.19, 1.15), (0.23, 1.25), (0.24, 1.32),
                                  (0.19, 1.39), (0.1, 1.43), (0.07, 1.46)], segments=16, scale_xy=(1.0, 0.78))
    torso.data.transform(Matrix.Scale(s, 4))
    dc.subdivide(torso, 1)
    parts.append(tag(torso, M["plate"], ["hips", "spine", "chest", "neck"]))
    for z, r in ((1.2, 0.235), (1.05, 0.2)):
        band = torus(f"Gd_Band{z}", V(0, 0, z), r * s, 0.012 * s, 24, 6, scale=(1.0, 0.8, 1.0))
        parts.append(tag(band, M["gold"], ["spine", "chest"] if z > 1.1 else ["hips", "spine"]))
    skirt = dc.lathe("Gd_Faulds", [(0.18, 1.0), (0.21, 0.9), (0.24, 0.78), (0.26, 0.7)], segments=20, scale_xy=(1.05, 0.85),
                     cap_top=False, cap_bottom=False)
    delete_faces(skirt, lambda c: c.y < -0.1 and abs(c.x) < 0.06)
    skirt.data.transform(Matrix.Scale(s, 4))
    solidify(skirt, 0.014, offset=1.0)
    parts.append(tag(skirt, M["plate"], ["hips", "thigh.L", "thigh.R"], power=5))
    cape = dc.lathe("Gd_Cape", [(0.2, 1.42), (0.26, 1.3), (0.28, 1.0), (0.3, 0.6), (0.32, 0.25)], segments=20,
                    scale_xy=(1.05, 0.9), cap_top=False, cap_bottom=False)
    delete_faces(cape, lambda c: c.y < 0.02)
    cape.data.transform(Matrix.Scale(s, 4))
    solidify(cape, 0.012, offset=1.0)
    parts.append(tag(cape, M["cape"], ["chest", "spine", "coat_L_01", "coat_L_02", "coat_L_03", "coat_R_01", "coat_R_02",
                                       "coat_R_03"], power=4))
    helm = dc.lathe("Gd_Helm", [(0.0, 0.18), (0.08, 0.17), (0.12, 0.10), (0.125, -0.02), (0.11, -0.1), (0.06, -0.13)],
                    segments=16, scale_xy=(0.95, 1.05))
    transform(helm, Matrix.Translation(V(0, -0.03, 1.6)) @ Matrix.Scale(s, 4))
    parts.append(tag(helm, M["plate"], ["neck", "head"], power=10))
    visor = dc.box("Gd_Visor", (0.12 * s, 0.02 * s, 0.018 * s), V(0, -0.155, 1.6), bevel=0.004)
    parts.append(tag(visor, M["glow"], rigid="head"))
    crest = dc.tube_along("Gd_Plume", [V(0, -0.06, 1.78), V(0, 0.05, 1.86), V(0, 0.18, 1.82), V(0, 0.28, 1.68)],
                          [0.03 * s, 0.05 * s, 0.045 * s, 0.0], segments=8, up=Vector((1, 0, 0)), flatten=0.35)
    parts.append(tag(crest, M["cape"], rigid="head"))
    for side, sx in (("L", 1.0), ("R", -1.0)):
        pauld = dc.lathe(f"Gd_Pauld{side}", [(0.0, 0.09), (0.09, 0.08), (0.15, 0.03), (0.17, -0.04), (0.17, -0.09)],
                         segments=14, cap_bottom=False)
        solidify(pauld, 0.014, offset=1.0)
        transform(pauld, Matrix.Translation(V(0.24 * sx, 0.0, 1.38)) @ Matrix.Rotation(math.radians(28 * sx), 4, "Y") @ Matrix.Scale(s, 4))
        if sx < 0:
            pauld.data.flip_normals()
        parts.append(tag(pauld, M["gold"] if side == "L" else M["plate"], [f"shoulder.{side}", f"upper_arm.{side}"], power=10))
        upper = limb(f"Gd_Upper{side}", V(0.19 * sx, 0.01, 1.35), V(0.23 * sx, 0.02, 1.0), [0.085 * s, 0.08 * s, 0.07 * s],
                     segments=10)
        parts.append(tag(upper, M["plate"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        fore = limb(f"Gd_Fore{side}", V(0.23 * sx, 0.02, 1.02), V(0.245 * sx, -0.02, 0.74), [0.07 * s, 0.075 * s, 0.065 * s],
                    segments=10)
        parts.append(tag(fore, M["plate"], [f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"]))
        fist = dc.box(f"Gd_Fist{side}", (0.085 * s, 0.11 * s, 0.1 * s), V(0.25 * sx, -0.035, 0.68), bevel=0.02)
        parts.append(tag(fist, M["plate"], rigid=f"hand.{side}"))
        thigh = limb(f"Gd_Thigh{side}", V(0.09 * sx, 0, 0.94), V(0.10 * sx, -0.03, 0.47), [0.1 * s, 0.095 * s, 0.085 * s],
                     segments=10)
        parts.append(tag(thigh, M["cloth"], ["hips", f"thigh.{side}", f"shin.{side}"]))
        greave = limb(f"Gd_Greave{side}", V(0.10 * sx, -0.03, 0.52), V(0.10 * sx, 0.02, 0.08), [0.085 * s, 0.08 * s, 0.07 * s],
                      segments=10)
        parts.append(tag(greave, M["plate"], [f"thigh.{side}", f"shin.{side}", f"foot.{side}"]))
        knee = dc.ico(f"Gd_Knee{side}", 0.06 * s, V(0.10 * sx, -0.08, 0.5), subdiv=1)
        parts.append(tag(knee, M["gold"], [f"thigh.{side}", f"shin.{side}"], power=8))
        foot = dc.box(f"Gd_Foot{side}", (0.13 * s, 0.28 * s, 0.09 * s), V(0.10 * sx, -0.06, 0.045), bevel=0.025)
        parts.append(tag(foot, M["plate"], [f"shin.{side}", f"foot.{side}"], power=8))
    return parts


GD_STANCE = {
    "hips_loc": (0, 0.02, -0.06), "spine": (6, 0, 0), "chest": (4, 14, 0), "neck": (-6, -8, 0), "head": (-4, -6, 0),
    "feet": {"L": (-0.2, 0.09, 0), "R": (0.22, 0.09, 0)},
    "arm.L": (-34, -60, 0, -12, 0), "arm.R": (-20, -70, 60, 12, 0),
}


def guardian_anims(arm, name):
    s = S_GUARD
    st = P(GD_STANCE, s)
    br = P(M_(GD_STANCE, hips_loc=(0, 0.02, -0.07), chest=(6, 14, 0)), s)
    act(arm, name, "Idle", 61, [(1, st), (31, br), (61, st)], chain_fn=rags(30, (2, 3, 4), (2, 3, 4)), step=3)
    keys = []
    for f in range(1, 26, 2):
        p = (f - 1) / 24.0
        c, sn = math.cos(math.tau * p), math.sin(math.tau * p)

        def foot(q):
            if q < 0.55:
                u = q / 0.55
                return (-0.22 + 0.44 * u, 0.09, 0)
            u = (q - 0.55) / 0.45
            return (0.22 - 0.44 * u * u * (3 - 2 * u), 0.09 + 0.14 * math.sin(math.pi * u), 10 * (1 - u))
        keys.append((f, P({"hips_loc": (0, 0, -0.07 - 0.02 * math.cos(2 * math.tau * p)), "spine": (8, 0, 4 * sn),
                           "chest": (4, 14 + 5 * sn, 0), "neck": (-8, -8, 0), "head": (-4, -6, 0),
                           "feet": {"L": foot(p), "R": foot((p + 0.5) % 1.0)},
                           "arm.L": (-20 + 15 * c, -50 + 10 * c, 0, -12, 0), "arm.R": (-20, -70, 60, 12, 0)}, s)))
    act(arm, name, "Run", 25, keys, chain_fn=rags(24, (10, 8, 6), (4, 6, 8)), step=2)
    # Overhead slam: long readable windup, devastating drop.
    wind = P(M_(GD_STANCE, hips_loc=(0, 0.1, 0.0), spine=(-10, 0, 0), chest=(-16, 0, 0), head=(-10, 0, 0),
                feet={"L": (-0.2, 0.11, 0), "R": (0.28, 0.09, 10)},
                **{"arm.L": (-175, -185, 0, -10, 0), "arm.R": (178, 120, -170, 8, 0)}), s)
    slam = P(M_(GD_STANCE, hips_loc=(0, -0.2, -0.26), spine=(38, 0, 0), chest=(22, 0, 0), head=(-24, 0, 0),
                feet={"L": (-0.48, 0.09, 0), "R": (0.34, 0.12, 20)},
                **{"arm.L": (-50, -62, 0, -8, 0), "arm.R": (-50, -62, 76, 8, 0), "spine:scale": (1.04, 0.95, 1.04)}), s)
    act(arm, name, "Attack", 50, [(1, st), (16, wind), (26, wind), (27, slam), (38, slam), (50, st)],
        modes={1: "BEZIER", 16: "LINEAR", 26: "CONSTANT", 27: "LINEAR", 38: "BEZIER"}, chain_fn=rags(25, (14, 10, 6), (8, 10, 12)), step=1)
    # Horizontal sweep.
    back = P(M_(GD_STANCE, hips_loc=(0, 0.06, -0.12), spine=(10, -30, 0), chest=(4, -40, 0), head=(-6, 24, 0),
                **{"arm.L": (-60, -90, 0, -40, 0), "arm.R": (60, 20, 140, 60, 0)}), s)
    sweep = P(M_(GD_STANCE, hips_loc=(0, -0.12, -0.16), spine=(16, 34, 0), chest=(8, 44, 0), head=(-10, -24, 0),
                 feet={"L": (-0.4, 0.09, 0), "R": (0.3, 0.1, 10)},
                 **{"arm.L": (-90, -100, 0, -60, 0), "arm.R": (-90, -96, 10, -40, 0)}), s)
    act(arm, name, "Sweep", 42, [(1, st), (14, back), (20, back), (21, sweep), (30, sweep), (42, st)],
        modes={1: "BEZIER", 14: "LINEAR", 20: "CONSTANT", 21: "LINEAR", 30: "BEZIER"}, chain_fn=rags(21, (12, 8, 6), (8, 10, 12)), step=1)
    hurt = P(M_(GD_STANCE, hips_loc=(0, 0.06, -0.08), spine=(0, 0, 0), chest=(-8, 6, 0), head=(-14, 0, 0)), s)
    act(arm, name, "Hurt", 14, [(1, st), (2, hurt), (6, hurt), (14, st)], modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"},
        chain_fn=rags(14, (8, 6, 4), (6, 8, 10)), step=1)
    _death(arm, name, s, st)


def export_greatsword(out_dir):
    """Oversized blade for the Royal Guardian (grip at origin, blade +Z)."""
    from build_weapons import blade_mesh, blade_material
    m_blade = blade_material("M_GreatBlade", "#FFFFFF", rust_amt=0.3, z0=0.3, z1=1.9, rune_freq=12.0)
    m_gold = dc.make_material("M_GreatGold", "#B8924A", dark="#5E461F", light="#F0D28A", metal=1.0, rough=0.3,
                              edge_wear="#FFF0C0", edge_wear_amt=0.9, cavity_dirt=0.8)
    m_grip = dc.make_material("M_GreatGrip", "#3B2618", dark="#1A0F09", light="#6A4A30", rough=0.7,
                              stripes=("z", 50.0, 0.2, "#160C06"))
    blade = blade_mesh("GS_Blade", 2.2, 0.34, 0.28, 0.05, 0.22, fuller=(0.05, 0.8), nicks=10, seed=17, tip_len=0.35)
    dc.assign_material(blade, m_blade)
    guard = dc.box("GS_Guard", (0.6, 0.1, 0.12), (0, 0, 0.18), bevel=0.03)
    dc.assign_material(guard, m_gold)
    grip = dc.lathe("GS_Grip", [(0.035, -0.4), (0.04, -0.2), (0.04, 0.12)], segments=10)
    dc.assign_material(grip, m_grip)
    pommel = dc.ico("GS_Pommel", 0.07, (0, 0, -0.45), subdiv=2)
    dc.assign_material(pommel, m_gold)
    parts = [blade, guard, grip, pommel]
    for p in parts:
        p.location = (0, 60, 0)
    dc.uv_atlas_multi(parts, island_margin=0.004)
    pairs = [(p, dc.make_highpoly(p, bevel_width=0.003, subsurf=1)) for p in parts]
    paths = dc.bake_texture_set(parts, out_dir / "Textures", "Greatsword", size=1024, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    for p in parts:
        p.location = (0, 0, 0)
    gs = dc.join(parts, "Greatsword")
    gs.data.materials.clear()
    gs.data.materials.append(dc.baked_material("M_Greatsword", paths, emission_strength=3.0))
    dc.export_fbx(out_dir / "Greatsword.fbx", [gs], static=True)
    dc.move_to(gs, dc.collection("RoyalGuardian"))
    gs.location = (DISPLAY["RoyalGuardian"][0] + 0.9, 0, 1.2)


# ===========================================================================
# 5. TIME KEEPER -- the final boss, shoveling crushed starlight into furnaces
# ===========================================================================

S_KEEP = 1.72


def keeper_materials():
    return {
        "robe": mat("M_TkRobe", "#252A52", "#0E1028", "#3E4680", noise_scale=5, noise_amt=0.9, rough=0.85,
                    stripes=("z", 4.0, 0.05, "#C9A35C"), edge_wear="#5A64A8", edge_wear_amt=0.5, cavity_dirt=0.8),
        "brass": mat("M_TkBrass", "#B08646", "#5A3E1C", "#E6C27C", metal=1.0, rough=0.3, edge_wear="#FFE9B0",
                     edge_wear_amt=1.0, cavity_dirt=0.9, noise_scale=12),
        "leather": mat("M_TkLeather", "#4A3122", "#22140C", "#73513A", rough=0.6, edge_wear="#B08A62",
                       edge_wear_amt=0.8, cavity_dirt=0.7),
        "glow": dc.make_material("Glow", "#FFF2C8", dark="#E8C46A", light="#FFFFFF", rough=0.3, emission="#FFFFFF",
                                 emission_strength=8.0),
    }


def keeper_parts(M):
    s = S_KEEP
    parts = []
    rnd = random.Random(21)

    def V(x, y, z):
        return Vector((x * s, y * s, z * s))
    robe = dc.lathe("Tk_Robe", [(0.08, 1.46), (0.17, 1.40), (0.22, 1.28), (0.22, 1.1), (0.25, 0.9), (0.31, 0.6),
                                (0.37, 0.3), (0.4, 0.06)], segments=22, scale_xy=(1.0, 0.85), cap_bottom=False)
    for v in robe.data.vertices:
        if v.co.z < 0.12:
            v.co.z += rnd.uniform(-0.04, 0.03)
    robe.data.update()
    delete_faces(robe, lambda c: c.y < -0.15 and abs(c.x) < 0.05 and c.z < 0.85)
    robe.data.transform(Matrix.Scale(s, 4))
    solidify(robe, 0.014, offset=1.0)
    parts.append(tag(robe, M["robe"], ["hips", "spine", "chest", "neck", "thigh.L", "thigh.R", "coat_L_01", "coat_L_02",
                                      "coat_L_03", "coat_R_01", "coat_R_02", "coat_R_03"], power=4))
    apron = dc.box("Tk_Apron", (0.3 * s, 0.03 * s, 0.7 * s), V(0, -0.21, 0.82), bevel=0.02)
    parts.append(tag(apron, M["leather"], ["hips", "spine", "thigh.L", "thigh.R"], power=4))
    hood = dc.lathe("Tk_Hood", [(0.0, 0.22), (0.1, 0.2), (0.15, 0.1), (0.16, -0.02), (0.13, -0.1)], segments=18,
                    scale_xy=(1.0, 1.1), cap_bottom=False)
    solidify(hood, 0.012, offset=1.0)
    transform(hood, Matrix.Translation(V(0, 0.0, 1.58)) @ Matrix.Scale(s, 4))
    parts.append(tag(hood, M["robe"], ["neck", "head"], power=10))
    mask = dc.lathe("Tk_Mask", [(0.0, 0.015), (0.085, 0.01), (0.095, 0.0)], segments=22, cap_bottom=False)
    transform(mask, Matrix.Translation(V(0, -0.14, 1.56)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Scale(s, 4))
    parts.append(tag(mask, M["glow"], rigid="head"))
    ring = torus("Tk_MaskRing", V(0, -0.145, 1.56), 0.097 * s, 0.013 * s, 22, 6, rot=(math.pi / 2, 0, 0))
    parts.append(tag(ring, M["brass"], rigid="head"))
    # Clockwork rig on the back: gears, pipes, a small starlight furnace.
    for k, (x, z, r) in enumerate(((0.0, 1.3, 0.16), (0.14, 1.12, 0.1), (-0.13, 1.18, 0.09))):
        gear = torus(f"Tk_Gear{k}", V(x, 0.2, z), r * s, 0.025 * s, 16, 6, rot=(math.pi / 2, 0, 0))
        teeth = []
        for t in range(12):
            a = math.tau * t / 12
            teeth.append(dc.box(f"Tk_Tooth{k}_{t}", (0.03 * s, 0.03 * s, 0.03 * s),
                                V(x + math.cos(a) * (r + 0.03), 0.2, z + math.sin(a) * (r + 0.03))))
        g = dc.join([gear] + teeth, f"Tk_GearSet{k}")
        parts.append(tag(g, M["brass"], ["spine", "chest"], power=6))
    furnace = dc.lathe("Tk_Furnace", [(0.0, 0.0), (0.09, 0.0), (0.1, 0.1), (0.07, 0.18), (0.02, 0.24)], segments=12)
    transform(furnace, Matrix.Translation(V(0, 0.24, 0.92)) @ Matrix.Scale(s, 4))
    parts.append(tag(furnace, M["brass"], ["hips", "spine"], power=6))
    core = dc.ico("Tk_FurnaceCore", 0.05 * s, V(0, 0.18, 1.0), subdiv=1)
    parts.append(tag(core, M["glow"], ["hips", "spine"], power=6))
    for k in range(3):
        x = (k - 1) * 0.08
        pipe = dc.tube_along(f"Tk_Pipe{k}", [V(x, 0.22, 1.06), V(x, 0.26, 1.35), V(x * 1.5, 0.2, 1.55)], [0.022 * s] * 3, segments=8)
        parts.append(tag(pipe, M["brass"], ["spine", "chest"], power=6))
    for side, sx in (("L", 1.0), ("R", -1.0)):
        sleeve = limb(f"Tk_Sleeve{side}", V(0.18 * sx, 0.01, 1.36), V(0.25 * sx, -0.02, 0.76), [0.075 * s, 0.08 * s, 0.09 * s, 0.11 * s],
                      segments=12)
        parts.append(tag(sleeve, M["robe"], ["chest", f"upper_arm.{side}", f"forearm.{side}"]))
        glove = dc.box(f"Tk_Glove{side}", (0.07 * s, 0.1 * s, 0.13 * s), V(0.255 * sx, -0.04, 0.66), bevel=0.02)
        parts.append(tag(glove, M["leather"], rigid=f"hand.{side}"))
        bracer = torus(f"Tk_Bracer{side}", V(0.25 * sx, -0.02, 0.78), 0.11 * s, 0.02 * s, 14, 6)
        parts.append(tag(bracer, M["brass"], [f"forearm.{side}", f"hand.{side}"], power=8))
    return parts


TK_STANCE = {
    "hips_loc": (0, 0.03, -0.05), "spine": (14, 0, 0), "chest": (10, 10, 0), "neck": (-12, 0, 0), "head": (-6, 0, 0),
    "feet": {"L": (-0.2, 0.09, 0), "R": (0.22, 0.09, 0)},
    "arm.L": (-40, -90, 0, -14, 0), "arm.R": (-30, -84, 70, 14, 0),
}


def keeper_anims(arm, name):
    s = S_KEEP
    st = P(TK_STANCE, s)
    br = P(M_(TK_STANCE, hips_loc=(0, 0.03, -0.07), chest=(13, 10, 0), head=(-10, 6, 0)), s)
    act(arm, name, "Idle", 61, [(1, st), (31, br), (61, st)], chain_fn=rags(30, (3, 3, 4), (3, 4, 5)), step=3)
    keys = []
    for f in range(1, 26, 2):
        p = (f - 1) / 24.0
        c, sn = math.cos(math.tau * p), math.sin(math.tau * p)

        def foot(q):
            if q < 0.55:
                u = q / 0.55
                return (-0.22 + 0.44 * u, 0.09, 0)
            u = (q - 0.55) / 0.45
            return (0.22 - 0.44 * u * u * (3 - 2 * u), 0.09 + 0.16 * math.sin(math.pi * u), 10 * (1 - u))
        keys.append((f, P({"hips_loc": (0, 0, -0.06 - 0.02 * math.cos(2 * math.tau * p)), "spine": (16, 0, 4 * sn),
                           "chest": (10, 10 + 5 * sn, 0), "neck": (-12, 0, 0), "head": (-6, 0, 0),
                           "feet": {"L": foot(p), "R": foot((p + 0.5) % 1.0)},
                           "arm.L": (-30 + 14 * c, -80 + 10 * c, 0, -14, 0), "arm.R": (-30, -84, 70, 14, 0)}, s)))
    act(arm, name, "Run", 25, keys, chain_fn=rags(24, (14, 10, 6), (5, 7, 9)), step=2)
    back = P(M_(TK_STANCE, hips_loc=(0, 0.08, -0.1), spine=(10, -34, 0), chest=(2, -40, 0), head=(-8, 24, 0),
                **{"arm.L": (-60, -110, 0, -40, 0), "arm.R": (70, 30, 150, 60, 0)}), s)
    swing = P(M_(TK_STANCE, hips_loc=(0, -0.14, -0.14), spine=(18, 34, 0), chest=(8, 44, 0), head=(-12, -20, 0),
                 feet={"L": (-0.42, 0.09, 0), "R": (0.3, 0.1, 10)},
                 **{"arm.L": (-90, -100, 0, -60, 0), "arm.R": (-90, -96, 10, -40, 0)}), s)
    act(arm, name, "Swing", 40, [(1, st), (14, back), (20, back), (21, swing), (30, swing), (40, st)],
        modes={1: "BEZIER", 14: "LINEAR", 20: "CONSTANT", 21: "LINEAR", 30: "BEZIER"}, chain_fn=rags(20, (16, 12, 8), (8, 10, 12)), step=1)
    up = P(M_(TK_STANCE, hips_loc=(0, 0.1, 0.02), spine=(-10, 0, 0), chest=(-16, 0, 0), head=(-16, 0, 0),
              **{"arm.L": (-170, -185, 0, -10, 0), "arm.R": (-172, -186, -90, 10, 0)}), s)
    slam = P(M_(TK_STANCE, hips_loc=(0, -0.2, -0.28), spine=(40, 0, 0), chest=(24, 0, 0), head=(-26, 0, 0),
                feet={"L": (-0.48, 0.09, 0), "R": (0.34, 0.12, 20)},
                **{"arm.L": (-60, -70, 0, -8, 0), "arm.R": (-55, -66, 80, 8, 0)}), s)
    act(arm, name, "Slam", 48, [(1, st), (16, up), (24, up), (25, slam), (36, slam), (48, st)],
        modes={1: "BEZIER", 16: "LINEAR", 24: "CONSTANT", 25: "LINEAR", 36: "BEZIER"}, chain_fn=rags(24, (18, 12, 8), (8, 10, 12)), step=1)
    scoop = P(M_(TK_STANCE, hips_loc=(0, 0.02, -0.25), spine=(36, 0, 0), chest=(20, 0, 0), **{"arm.L": (-40, -60, 0, -10, 0), "arm.R": (-30, -50, 100, 10, 0)}), s)
    fling = P(M_(TK_STANCE, hips_loc=(0, -0.06, -0.02), spine=(-12, 0, 0), chest=(-18, 0, 0), head=(-20, 0, 0),
                 **{"arm.L": (-150, -170, 0, -20, 0), "arm.R": (-150, -168, -110, 20, 0)}), s)
    act(arm, name, "Toss", 36, [(1, st), (10, scoop), (14, scoop), (18, fling), (26, fling), (36, st)],
        modes={1: "BEZIER", 10: "LINEAR", 14: "LINEAR", 18: "BEZIER", 26: "BEZIER"}, chain_fn=rags(18, (16, 12, 8), (8, 10, 12)), step=1)
    chan = P(M_(TK_STANCE, hips_loc=(0, 0, 0.04), spine=(-4, 0, 0), chest=(-10, 0, 0), head=(-24, 0, 0),
                **{"arm.L": (-120, -140, 0, -70, 0), "arm.R": (-120, -140, -40, 70, 0), "chest:scale": (1.05, 1, 1.05)}), s)
    chan2 = P(M_(TK_STANCE, hips_loc=(0, 0, 0.06), spine=(-6, 0, 0), chest=(-12, 0, 0), head=(-26, 0, 0),
                 **{"arm.L": (-126, -146, 0, -74, 0), "arm.R": (-126, -146, -40, 74, 0)}), s)
    act(arm, name, "Rewind", 61, [(1, st), (14, chan), (30, chan2), (46, chan), (61, st)], chain_fn=rags(15, (20, 14, 10), (8, 10, 12)), step=2)
    hurt = P(M_(TK_STANCE, hips_loc=(0, 0.08, -0.08), chest=(-6, 6, 0), head=(-18, 0, 0)), s)
    act(arm, name, "Hurt", 14, [(1, st), (2, hurt), (6, hurt), (14, st)], modes={1: "CONSTANT", 2: "LINEAR", 6: "BEZIER"},
        chain_fn=rags(14, (8, 6, 4), (6, 8, 10)), step=1)
    _death(arm, name, s, st)


def export_shovel(out_dir):
    m_wood = dc.make_material("M_ShovelWood", "#5A3A22", dark="#2E1A0D", light="#86603F", rough=0.8,
                              stripes=("z", 8.0, 0.05, "#20120A"), edge_wear="#B98C5E", edge_wear_amt=0.6)
    m_iron = dc.make_material("M_ShovelIron", "#4D555E", dark="#1F2329", light="#88929C", metal=1.0, rough=0.42,
                              edge_wear="#D8E0E6", edge_wear_amt=1.0, cavity_dirt=0.9)
    m_star = dc.make_material("M_ShovelStar", "#FFF4D0", dark="#F0C870", light="#FFFFFF", rough=0.3, emission="#FFFFFF",
                              emission_strength=8.0, emission_mask="noise")
    shaft = dc.lathe("Sh_Shaft", [(0.04, -0.9), (0.045, 0.0), (0.04, 1.3)], segments=10)
    dc.assign_material(shaft, m_wood)
    grip = dc.box("Sh_Grip", (0.28, 0.06, 0.06), (0, 0, -0.95), bevel=0.02)
    dc.assign_material(grip, m_wood)
    blade = dc.box("Sh_Blade", (0.62, 0.08, 0.7), (0, 0.0, 1.62), bevel=0.04)
    dc.deform(blade, lambda v: Vector((v.x * (1.0 - 0.2 * max(0.0, (v.z - 1.62) / 0.35)), v.y + 0.12 * ((v.x / 0.31) ** 2), v.z)))
    dc.assign_material(blade, m_iron)
    pile = dc.ico("Sh_Starlight", 0.24, (0, -0.08, 1.6), subdiv=2)
    dc.deform(pile, lambda v: Vector((v.x * 1.1, (v.y + 0.08) * 0.5 - 0.1, v.z)))
    dc.assign_material(pile, m_star)
    parts = [shaft, grip, blade, pile]
    for p in parts:
        p.location = (0, 70, 0)
    dc.uv_atlas_multi(parts, island_margin=0.004)
    pairs = [(p, dc.make_highpoly(p, bevel_width=0.003, subsurf=1)) for p in parts]
    paths = dc.bake_texture_set(parts, out_dir / "Textures", "Shovel", size=1024, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    for p in parts:
        p.location = (0, 0, 0)
    sh = dc.join(parts, "Shovel")
    sh.data.materials.clear()
    sh.data.materials.append(dc.baked_material("M_Shovel", paths, emission_strength=4.0))
    dc.export_fbx(out_dir / "Shovel.fbx", [sh], static=True)
    dc.move_to(sh, dc.collection("TimeKeeper"))
    sh.location = (DISPLAY["TimeKeeper"][0] + 1.4, 0, 1.6)


# ===========================================================================
# 6. CREATURES -- static meshes animated procedurally in Unity
# ===========================================================================

def creature_materials():
    return {
        "fur": mat("M_CrFur", "#4E4436", "#231D15", "#7A6C55", noise_scale=20, noise_amt=0.9, rough=0.9, cavity_dirt=0.8,
                   edge_wear="#A0917A", edge_wear_amt=0.5),
        "flesh": mat("M_CrFlesh", "#B07A7A", "#5A3434", "#DDB0A8", rough=0.6, cavity_dirt=0.8),
        "chitin": mat("M_CrChitin", "#3E3550", "#181424", "#6E6290", rough=0.35, noise_scale=10, noise_amt=0.8,
                      stripes=("z", 9.0, 0.08, "#1A1428"), edge_wear="#A898D0", edge_wear_amt=0.8, cavity_dirt=0.8),
        "wing": mat("M_CrWing", "#C8D8F0", "#7A8CB0", "#F0F6FF", rough=0.2, stripes=("x", 25.0, 0.04, "#6A7AA0")),
        "moss": mat("M_CrMoss", "#2E5A2A", "#132A12", "#5C9A44", noise_scale=14, noise_amt=0.95, rough=0.95,
                    cavity_dirt=0.9, edge_wear="#8FCB4C", edge_wear_amt=0.6),
        "obsidian": mat("M_CrObsidian", "#1A1622", "#07060B", "#3A3450", metal=0.2, rough=0.15, noise_scale=8,
                        edge_wear="#8A7AB0", edge_wear_amt=0.9, cavity_dirt=0.6),
        "glow": dc.make_material("Glow", "#B6FF6A", dark="#7ACB2A", light="#F0FFD0", rough=0.3, emission="#FFFFFF",
                                 emission_strength=6.0),
    }


def creature_parts(M):
    """Returns {fbx_name: [objects]} -- each creature exported separately."""
    out = {}
    rnd = random.Random(3)
    # Caustic vermin: rat with glowing pustules + separate tail (pivot at its base).
    body = dc.ico("Vm_Body", 0.16, (0, 0, 0), subdiv=3)
    dc.deform(body, lambda v: Vector((v.x * 0.85, v.y * 1.8, v.z * 0.85)) + Vector((0, 0, 0.16)))
    head = dc.ico("Vm_Head", 0.09, (0, 0, 0), subdiv=2)
    dc.deform(head, lambda v: Vector((v.x * 0.9, v.y * 1.5 - (0.04 if v.y < 0 else 0), v.z * 0.85)) + Vector((0, -0.33, 0.17)))
    ears = [dc.ico(f"Vm_Ear{sx}", 0.04, (0.05 * sx, -0.28, 0.25), subdiv=1) for sx in (1, -1)]
    eyes = [dc.ico(f"Vm_Eye{sx}", 0.018, (0.05 * sx, -0.4, 0.2), subdiv=1) for sx in (1, -1)]
    pust = [dc.ico(f"Vm_Pus{k}", rnd.uniform(0.025, 0.045), (rnd.uniform(-0.09, 0.09), rnd.uniform(-0.15, 0.2), rnd.uniform(0.24, 0.3)), 1)
            for k in range(6)]
    legs = []
    for k, (x, y) in enumerate(((0.09, -0.15), (-0.09, -0.15), (0.09, 0.15), (-0.09, 0.15))):
        legs.append(dc.tube_along(f"Vm_Leg{k}", [(x, y, 0.12), (x * 1.3, y, 0.05), (x * 1.3, y - 0.03, 0.0)], [0.025, 0.02, 0.015], segments=6))
    for o in [body] + legs + ears:
        dc.assign_material(o, M["fur"])
    dc.assign_material(head, M["fur"])
    for o in eyes + pust:
        dc.assign_material(o, M["glow"])
    tail = dc.tube_along("Vermin_Tail", [(0, 0, 0), (0, 0.18, 0.02), (0.04, 0.36, 0.06), (0.02, 0.52, 0.04)],
                         [0.025, 0.018, 0.01, 0.0], segments=6)
    dc.assign_material(tail, M["flesh"])
    out["Vermin"] = ([body, head] + ears + eyes + pust + legs, {"Vermin_Tail": (tail, Vector((0, 0.27, 0.14)))})

    # Gossamer-winged tick: bloated abdomen, head, 8 legs; wings separate (pivot at root).
    abd = dc.ico("Tk_Abd", 0.3, (0, 0, 0), subdiv=3)
    dc.deform(abd, lambda v: Vector((v.x * 1.0, v.y * 1.25, v.z * 0.85)) + Vector((0, 0.15, 0)))
    thorax = dc.ico("Tk_Thorax", 0.14, (0, -0.25, 0.02), subdiv=2)
    mand = [dc.tube_along(f"Tk_Mand{sx}", [(0.04 * sx, -0.36, 0.0), (0.06 * sx, -0.46, -0.04), (0.02 * sx, -0.5, -0.06)],
                          [0.02, 0.014, 0.0], segments=5) for sx in (1, -1)]
    tlegs = []
    for k in range(4):
        for sx in (1, -1):
            y = -0.3 + k * 0.08
            tlegs.append(dc.tube_along(f"Tk_Leg{k}{sx}", [(0.1 * sx, y, -0.02), (0.3 * sx, y - 0.05, 0.08), (0.42 * sx, y - 0.08, -0.25)],
                                       [0.022, 0.016, 0.006], segments=5))
    teyes = [dc.ico(f"Tk_Eye{sx}", 0.025, (0.06 * sx, -0.36, 0.06), subdiv=1) for sx in (1, -1)]
    for o in [abd, thorax] + mand + tlegs:
        dc.assign_material(o, M["chitin"])
    for o in teyes:
        dc.assign_material(o, M["glow"])
    wings = {}
    for side, sx in (("L", 1), ("R", -1)):
        bm = bmesh.new()
        pts = [(0, 0, 0), (0.25 * sx, 0.05, 0.12), (0.55 * sx, 0.2, 0.1), (0.62 * sx, 0.38, 0.0), (0.4 * sx, 0.42, -0.02), (0.1 * sx, 0.2, 0.0)]
        vs = [bm.verts.new(p) for p in pts]
        f = bm.faces.new(vs if sx > 0 else list(reversed(vs)))
        bm.loops.layers.uv.new("UVMap")
        wing = dc.mesh_object(f"Tick_Wing{side}", bm)
        solidify(wing, 0.006, offset=0.0)
        dc.assign_material(wing, M["wing"])
        wings[f"Tick_Wing{side}"] = (wing, Vector((0.08 * sx, -0.2, 0.14)))
    out["Tick"] = ([abd, thorax] + mand + tlegs + teyes, wings)

    # Moss peasant: a twitching mound of bioluminescent moss with a half-melted face.
    blob = dc.ico("Ms_Blob", 0.45, (0, 0, 0), subdiv=3)

    def mound(v):
        p = Vector((v.x * 1.2, v.y * 0.9, max(v.z, -0.2) * 1.1))
        p += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.03
        return p + Vector((0, 0, 0.32))
    dc.deform(blob, mound)
    spots = [dc.ico(f"Ms_Spot{k}", rnd.uniform(0.03, 0.06), (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.38, -0.2), rnd.uniform(0.2, 0.7)), 1)
             for k in range(10)]
    face = [dc.ico(f"Ms_EyeHole{sx}", 0.05, (0.12 * sx, -0.38, 0.55), subdiv=1) for sx in (1, -1)]
    mouth = dc.box("Ms_Mouth", (0.18, 0.04, 0.05), (0, -0.4, 0.4), bevel=0.015)
    strands = [dc.tube_along(f"Ms_Strand{k}", [(x, -0.3, 0.6), (x * 1.1, -0.38, 0.35), (x * 1.2, -0.34, 0.08)], [0.03, 0.02, 0.0], segments=5)
               for k, x in enumerate((-0.3, -0.12, 0.08, 0.26))]
    for o in [blob] + strands:
        dc.assign_material(o, M["moss"])
    for o in spots + face:
        dc.assign_material(o, M["glow"])
    dc.assign_material(mouth, M["obsidian"])
    out["MossBlob"] = ([blob] + spots + face + [mouth] + strands, {})

    # Obsidian obelisk: a calcified palace sentinel fused into a singing monolith.
    ob = dc.lathe("Ob_Monolith", [(0.42, 0.0), (0.4, 0.3), (0.34, 1.6), (0.28, 2.3), (0.0, 2.75)], segments=4, phase=math.pi / 4)
    figure = dc.ico("Ob_Figure", 0.22, (0, 0, 0), subdiv=2)
    dc.deform(figure, lambda v: Vector((v.x * 0.9, v.y * 0.5, v.z * 2.6)) + Vector((0, -0.24, 1.25)))
    fhead = dc.ico("Ob_Head", 0.13, (0, -0.28, 1.95), subdiv=2)
    sword = dc.box("Ob_Sword", (0.06, 0.03, 1.2), (0.18, -0.3, 1.1), bevel=0.01)
    transform(sword, Matrix.Translation((0.18, -0.3, 1.1)) @ Matrix.Rotation(math.radians(-15), 4, "Y") @ Matrix.Translation((-0.18, 0.3, -1.1)))
    runes = []
    for k in range(5):
        z = 0.4 + k * 0.38
        runes.append(dc.box(f"Ob_Rune{k}", (0.16, 0.02, 0.05), (rnd.uniform(-0.12, 0.12), -0.36 + 0.02 * k, z), bevel=0.005))
    for o in (ob, figure, fhead, sword):
        dc.assign_material(o, M["obsidian"])
    for o in runes:
        dc.assign_material(o, M["glow"])
    out["Obelisk"] = ([ob, figure, fhead, sword] + runes, {})
    return out


def build_creatures(size=2048):
    coll = dc.collection("Creatures")
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    M = creature_materials()
    sets = creature_parts(M)
    all_objs = []
    for name, (body_parts, extras) in sets.items():
        for o in body_parts + [e[0] for e in extras.values()]:
            dc.move_to(o, coll)
            for p in o.data.polygons:
                p.use_smooth = True
            all_objs.append(o)
    for i, o in enumerate(all_objs):
        o.location = (0, 50 + (i % 7) * 2, 0)
    dc.uv_atlas_multi(all_objs, island_margin=0.003)
    pairs = [(o, dc.make_highpoly(o, bevel_width=0.003, subsurf=1)) for o in all_objs]
    out_dir = CHAR_ROOT / "Creatures"
    paths = dc.bake_texture_set(all_objs, out_dir / "Textures", "Creatures", size=size, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    baked = dc.baked_material("M_Creatures", paths, emission_strength=3.0)
    x = 0.0
    for name, (body_parts, extras) in sets.items():
        for o in body_parts + [e[0] for e in extras.values()]:
            o.location = (0, 0, 0)
        body = dc.join(body_parts, name)
        body.data.materials.clear()
        body.data.materials.append(baked)
        export = [body]
        for ename, (eobj, pivot) in extras.items():
            # Move the extra so its origin sits at the hinge, then parent it.
            eobj.data.transform(Matrix.Translation(-pivot))
            eobj.location = pivot
            eobj.data.materials.clear()
            eobj.data.materials.append(baked)
            eobj.parent = body
            export.append(eobj)
        dc.export_fbx(out_dir / f"{name}.fbx", export, static=False)
        body.location = (DISPLAY["Creatures"][0] + x, DISPLAY["Creatures"][1], 0)
        x += 1.6
    print("[creatures] exported", list(sets))


# ---------------------------------------------------------------------------

PARENTS = dict(BASE_PARENTS, weapon_socket="hand.R")


def with_socket(joints, s):
    """Grip socket in the right fist (blade/shaft points forward at rest, like the Beheaded)."""
    j = dict(joints)
    j["weapon_socket"] = ((-0.245 * s, -0.03 * s, 0.665 * s), (-0.245 * s, -0.13 * s, 0.665 * s))
    return j


def joints_for(name):
    scale = {"Sentinel": S_SENT, "Monk": S_MONK, "Fisher": S_FISH, "RoyalGuardian": S_GUARD, "TimeKeeper": S_KEEP}[name]
    return with_socket(scaled_joints(scale), scale)


SPECS = {
    "Sentinel": (sentinel_materials, sentinel_parts, sentinel_anims, None),
    "Monk": (monk_materials, monk_parts, monk_anims, None),
    "Fisher": (fisher_materials, fisher_parts, fisher_anims, None),
    "RoyalGuardian": (guardian_materials, guardian_parts, guardian_anims, export_greatsword),
    "TimeKeeper": (keeper_materials, keeper_parts, keeper_anims, export_shovel),
}


def build(name, size=2048):
    if name == "Creatures":
        return build_creatures(size=size)
    mats, parts, anims, extra = SPECS[name]
    return build_character(name, joints_for(name), PARENTS, mats, parts, anims, size=size, extra_export=extra)


def build_all(live=True):
    if not live:
        dc.reset_scene()
    for name in list(SPECS) + ["Creatures"]:
        build(name)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dc.reset_scene()
    for n in (argv or list(SPECS) + ["Creatures"]):
        build(n)
