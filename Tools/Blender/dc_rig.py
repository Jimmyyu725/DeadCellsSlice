"""Rig + animation authoring framework shared by the Beheaded and enemies.

Every limb bone is rolled so that its local X axis equals world +X (see
dc_common.bone_roll_axis). Rotations about X therefore compose additively
down a chain, which lets poses be authored as *world sagittal angles*:

  * limb angle  phi: direction = (0, sin phi, -cos phi)
      0 = straight down, +90 = pointing backward, -90 = pointing forward,
      +-180 = straight up.
  * blade angle theta (weapon held in hand.R, rest pointing forward):
      direction = (0, -cos theta, -sin theta)
      0 = forward, 90 = down, -90 = up, 180 = backward.

A pose is a dict:
  "hips_loc": (dx, dy, dz) world offset of the pelvis
  "<bone>": (x, y, z) local euler degrees (torso, neck, head, chains...)
  "<bone>:scale": (sx, sy, sz)
  "feet": {"L": (y, z, pitch), "R": (...)}  ankle targets solved with IK
  "legs": {"L": (thigh_phi, shin_phi, foot_pitch)}  FK legs in world angles
  "arm.L" / "arm.R": (upper_phi, fore_phi, hand_angle, upper_z, upper_y)
      hand_angle is the blade angle theta for arm.R and a plain world
      angle offset for arm.L.
"""

import math

import bpy
from mathutils import Euler, Vector

import dc_common as dc

TORSO_CHAIN = ("hips", "spine", "chest")


# ---------------------------------------------------------------------------
# Armature
# ---------------------------------------------------------------------------

def build_armature(name, joints, parents, non_deform=()):
    arm_data = bpy.data.armatures.new(name)
    arm_data.display_type = "STICK"
    arm = dc.link(bpy.data.objects.new(name, arm_data))
    dc.set_active(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for bone, (h, t) in joints.items():
        eb = arm_data.edit_bones.new(bone)
        eb.head = Vector(h)
        eb.tail = Vector(t)
        eb.align_roll(dc.bone_roll_axis(Vector(t) - Vector(h)))
        eb.use_deform = bone not in non_deform
        ebs[bone] = eb
    for bone, parent in parents.items():
        if parent:
            ebs[bone].parent = ebs[parent]
            ebs[bone].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def mirror_joints(joints):
    """Create .R bones from .L bones by negating X."""
    out = dict(joints)
    for name, (h, t) in joints.items():
        if name.endswith(".L"):
            out[name[:-2] + ".R"] = ((-h[0], h[1], h[2]), (-t[0], t[1], t[2]))
        elif "_L_" in name:
            out[name.replace("_L_", "_R_")] = ((-h[0], h[1], h[2]), (-t[0], t[1], t[2]))
    return out


def bind(mesh_obj, arm):
    mesh_obj.parent = arm
    mod = mesh_obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return mod


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _rot_x(v, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return Vector((v.x, v.y * c - v.z * s, v.y * s + v.z * c))


def _angle_x(v, w):
    """Signed rotation about +X taking v to w (degrees, YZ plane)."""
    v2 = Vector((0, v.y, v.z))
    w2 = Vector((0, w.y, w.z))
    return math.degrees(math.atan2(v2.cross(w2).x, v2.dot(w2)))


def _limb_dir(phi):
    r = math.radians(phi)
    return Vector((0, math.sin(r), -math.cos(r)))


def _wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def rest_dir(arm, bone):
    b = arm.data.bones[bone]
    return (b.tail_local - b.head_local).normalized()


def torso_x(pose):
    return sum(pose.get(b, (0, 0, 0))[0] for b in TORSO_CHAIN)


# ---------------------------------------------------------------------------
# Pose solving
# ---------------------------------------------------------------------------

def solve_leg_ik(arm, side, target, hips_offset, hips_x, pitch=0.0):
    """Planar two-bone IK; returns local X degrees for thigh, shin, foot."""
    th = arm.data.bones[f"thigh.{side}"]
    sh = arm.data.bones[f"shin.{side}"]
    hip = th.head_local + Vector(hips_offset)
    knee_rest = th.tail_local
    ankle_rest = sh.tail_local
    l1 = (knee_rest - th.head_local).length
    l2 = (ankle_rest - knee_rest).length
    tgt = Vector((hip.x, target[0], target[1]))
    d_vec = tgt - hip
    d = max(0.05, min(d_vec.length, (l1 + l2) * 0.9995))
    dir_ha = Vector((0, d_vec.y, d_vec.z)).normalized()
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    alpha = math.degrees(math.acos(max(-1.0, min(1.0, cos_a))))
    thigh_dir = _rot_x(dir_ha, -alpha)  # knee points forward
    knee = hip + thigh_dir * l1
    ankle = hip + dir_ha * d
    shin_dir = (ankle - knee).normalized()
    phi_th = _angle_x(rest_dir(arm, f"thigh.{side}"), thigh_dir)
    phi_sh = _angle_x(rest_dir(arm, f"shin.{side}"), shin_dir)
    return (_wrap(phi_th - hips_x), _wrap(phi_sh - phi_th), _wrap(pitch - phi_sh))


def solve_leg_fk(arm, side, thigh_phi, shin_phi, pitch, hips_x):
    """World limb angles -> local X, relative to the rest directions."""
    rd_th = rest_dir(arm, f"thigh.{side}")
    rd_sh = rest_dir(arm, f"shin.{side}")
    phi_th = _angle_x(rd_th, _limb_dir(thigh_phi))
    phi_sh = _angle_x(rd_sh, _limb_dir(shin_phi))
    return (_wrap(phi_th - hips_x), _wrap(phi_sh - phi_th), _wrap(pitch - phi_sh))


def solve_arm(arm, side, pose, upper_phi, fore_phi, hand, upper_z=0.0, upper_y=0.0):
    parent_x = torso_x(pose) + pose.get(f"shoulder.{side}", (0, 0, 0))[0]
    phi_up = _angle_x(rest_dir(arm, f"upper_arm.{side}"), _limb_dir(upper_phi))
    phi_fo = _angle_x(rest_dir(arm, f"forearm.{side}"), _limb_dir(fore_phi))
    up = (_wrap(phi_up - parent_x), upper_y, upper_z)
    fo = (_wrap(phi_fo - phi_up), 0.0, 0.0)
    if side == "R":
        # Blade rest direction is forward; theta adds to the chain.
        hand_x = _wrap(hand - phi_fo)
    else:
        hand_x = hand
    return up, fo, (hand_x, 0.0, 0.0)


def apply_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    pbs = arm.pose.bones
    hips_offset = pose.get("hips_loc", (0, 0, 0))
    hips_x = pose.get("hips", (0, 0, 0))[0]

    resolved = {}
    for key, val in pose.items():
        if key in ("hips_loc", "feet", "legs") or key.startswith("arm.") or key.endswith(":scale"):
            continue
        resolved[key] = val
    for side, (y, z, pitch) in pose.get("feet", {}).items():
        t, s, f = solve_leg_ik(arm, side, (y, z), hips_offset, hips_x, pitch)
        resolved[f"thigh.{side}"] = (t, 0, 0)
        resolved[f"shin.{side}"] = (s, 0, 0)
        resolved[f"foot.{side}"] = (f, 0, 0)
    for side, (tphi, sphi, pitch) in pose.get("legs", {}).items():
        t, s, f = solve_leg_fk(arm, side, tphi, sphi, pitch, hips_x)
        resolved[f"thigh.{side}"] = (t, 0, 0)
        resolved[f"shin.{side}"] = (s, 0, 0)
        resolved[f"foot.{side}"] = (f, 0, 0)
    for side in ("L", "R"):
        spec = pose.get(f"arm.{side}")
        if spec:
            up, fo, ha = solve_arm(arm, side, pose, *spec)
            resolved[f"upper_arm.{side}"] = up
            resolved[f"forearm.{side}"] = fo
            resolved[f"hand.{side}"] = ha

    for bone, deg in resolved.items():
        if bone in pbs:
            pbs[bone].rotation_euler = Euler([math.radians(a) for a in deg], "XYZ")
    for key, val in pose.items():
        if key.endswith(":scale"):
            bone = key[:-6]
            if bone in pbs:
                pbs[bone].scale = val
    if "hips" in pbs:
        rest = arm.data.bones["hips"].matrix_local.to_3x3()
        pbs["hips"].location = rest.inverted() @ Vector(hips_offset)


def blend(a, b, t):
    """Linear blend of two poses (numeric leaves only)."""
    out = {}
    for key in set(a) | set(b):
        va, vb = a.get(key), b.get(key)
        if va is None:
            out[key] = vb
        elif vb is None:
            out[key] = va
        elif isinstance(va, dict):
            out[key] = {k: tuple(x * (1 - t) + y * t for x, y in zip(va[k], vb.get(k, va[k]))) for k in va}
        else:
            out[key] = tuple(x * (1 - t) + y * t for x, y in zip(va, vb))
    return out


def merge(base, **over):
    out = dict(base)
    for k, v in over.items():
        out[k.replace("__", ".")] = v
    return out


# ---------------------------------------------------------------------------
# Keying
# ---------------------------------------------------------------------------

def _is_chain(bone, chain_prefixes):
    return any(bone.startswith(p) for p in chain_prefixes)


def new_action(arm, name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    return act


def key_bones(arm, frame, bones):
    for bone in bones:
        pb = arm.pose.bones[bone]
        pb.keyframe_insert("rotation_euler", frame=frame, group=bone)
        pb.keyframe_insert("location", frame=frame, group=bone)
        pb.keyframe_insert("scale", frame=frame, group=bone)


def author_action(arm, name, length, keys, modes=None, chain_fn=None, chain_step=2,
                  chain_prefixes=("scarf_", "coat_")):
    """keys: [(frame, pose)], modes: {frame: interpolation for body keys}.

    chain_fn(frame, body_pose) -> {bone: (x, y, z)} keys secondary chains on
    every `chain_step` frames with smooth interpolation, independent of the
    snappy body timing.
    """
    act = new_action(arm, name)
    body = [b.name for b in arm.pose.bones if not _is_chain(b.name, chain_prefixes)]
    chains = [b.name for b in arm.pose.bones if _is_chain(b.name, chain_prefixes)]
    key_frames = sorted(keys, key=lambda k: k[0])
    for frame, pose in key_frames:
        apply_pose(arm, pose)
        key_bones(arm, frame, body)
    if chain_fn and chains:
        frames = list(range(1, length + 1, chain_step))
        if frames[-1] != length:
            frames.append(length)
        for f in frames:
            pose = _pose_at(key_frames, f)
            for bone in chains:
                pb = arm.pose.bones[bone]
                pb.rotation_euler = (0, 0, 0)
            for bone, deg in chain_fn(f, pose).items():
                if bone in arm.pose.bones:
                    arm.pose.bones[bone].rotation_euler = Euler([math.radians(a) for a in deg], "XYZ")
            key_bones(arm, f, chains)
    modes = modes or {}
    unwrap_rotations(act)
    for fc in dc.action_fcurves(act):
        bone = fc.data_path.split('"')[1] if '"' in fc.data_path else ""
        chain = _is_chain(bone, chain_prefixes)
        for kp in fc.keyframe_points:
            f = int(round(kp.co.x))
            kp.interpolation = "BEZIER" if chain else modes.get(f, "BEZIER")
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()
    act.frame_range = (1, length)
    try:
        act.use_frame_range = True
    except AttributeError:
        pass
    act["dc_length"] = length
    return act


def unwrap_rotations(act):
    """Keep consecutive euler keys within 180 deg so interpolation takes the
    short way round (matches the quaternion slerp Unity performs)."""
    for fc in dc.action_fcurves(act):
        if "rotation_euler" not in fc.data_path:
            continue
        pts = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        prev = None
        for kp in pts:
            if prev is not None:
                shift = 0.0
                while kp.co.y + shift - prev > math.pi:
                    shift -= math.tau
                while kp.co.y + shift - prev < -math.pi:
                    shift += math.tau
                if shift:
                    kp.co.y += shift
                    kp.handle_left.y += shift
                    kp.handle_right.y += shift
            prev = kp.co.y
        fc.update()


def _pose_at(key_frames, f):
    prev = key_frames[0]
    for k in key_frames:
        if k[0] <= f:
            prev = k
    nxt = next((k for k in key_frames if k[0] >= f), key_frames[-1])
    if nxt[0] == prev[0]:
        return prev[1]
    t = (f - prev[0]) / (nxt[0] - prev[0])
    return blend(prev[1], nxt[1], t)


def wave_chain(names, f, period, base, amp, phase_step=0.9, z_amp=0.0, z_base=0.0, offset=0.0):
    """Sinusoidal secondary motion down a chain (degrees)."""
    out = {}
    for i, n in enumerate(names):
        ph = math.tau * (f / period) - i * phase_step + offset
        out[n] = (base[i] + amp[i] * math.sin(ph), 0.0, z_base + z_amp * math.sin(ph * 0.5 + i))
    return out
