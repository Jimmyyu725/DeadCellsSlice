"""Weapon arsenal: Rusty Sword, Broadsword, Frontline Shield.

Convention: grip (or shield handle) at the origin, primary axis = Blender +Z
(blade direction / shield facing) -> Unity +Y. Blade width along X,
thickness along Y. All three share the 1024 "Weapons" atlas.
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

OUT_DIR = dc.ART_ROOT / "Weapons"
TEX_DIR = OUT_DIR / "Textures"
COLL = "Weapons"


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def blade_material(name, rune_hex, rust_amt=0.6, z0=0.12, z1=0.62, rune_freq=26.0):
    """Rusty iron with a rune channel down the fuller (emission mask)."""
    mat = dc.make_material(name, "#7B848C", dark="#3A3F44", light="#B9C2C8", metal=1.0, rough=0.35,
                           rough_var=0.18, noise_scale=16, noise_amt=0.7, edge_wear="#F2F6F8",
                           edge_wear_amt=1.2, cavity_dirt=0.9, bump_scale=55, bump_strength=0.22,
                           bevel_radius=0.004)
    nt = mat.node_tree
    alb_tag = nt.nodes["DC_ALBEDO"]
    rough_tag = nt.nodes["DC_ROUGH"]
    metal_tag = nt.nodes["DC_METAL"]
    emit_tag = nt.nodes["DC_EMIT"]
    coord = dc.tex_coord(nt, "Object", loc=(-1700, -1400))

    # Rust patches.
    rust_n = dc.noise(nt, scale=7.0, detail=6.0, roughness=0.65, loc=(-1400, -1300), coord=coord)
    rust_mask = dc.map_range(nt, dc._sock(rust_n.outputs, "Fac"), 0.62 - rust_amt * 0.15, 0.7 - rust_amt * 0.15,
                             loc=(-1200, -1300))
    rust_col = dc.ramp(nt, [(0.0, dc.hex_rgba("#4A2412")), (0.5, dc.hex_rgba("#8A4A22")), (1.0, dc.hex_rgba("#B36A2E"))],
                       loc=(-1050, -1450))
    nt.links.new(dc._sock(rust_n.outputs, "Fac"), dc._sock(rust_col.inputs, "Fac"))
    prev_alb = alb_tag.inputs[0].links[0].from_socket
    _, alb = dc.mix_rgb(nt, prev_alb, dc._sock(rust_col.outputs, "Color"), rust_mask, loc=(-450, 250))
    nt.links.new(alb, alb_tag.inputs[0])
    prev_r = rough_tag.inputs[0].links[0].from_socket
    rough = dc.math_node(nt, "MAXIMUM", prev_r, dc.math_node(nt, "MULTIPLY", rust_mask, 0.92, loc=(-600, -1200)),
                         loc=(-450, -150))
    nt.links.new(rough, rough_tag.inputs[0])
    prev_m = metal_tag.inputs[0].links[0].from_socket
    metal = dc.math_node(nt, "MULTIPLY", prev_m, dc.math_node(nt, "SUBTRACT", 1.0, rust_mask, loc=(-600, -1300)),
                         loc=(-450, -250))
    nt.links.new(metal, metal_tag.inputs[0])

    # Rune glyphs: dashes + crosses inside the fuller, |x| < 0.006.
    sep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-1500, -1700))
    nt.links.new(coord, dc._sock(sep.inputs, "Vector"))
    x_abs = dc.math_node(nt, "ABSOLUTE", dc._sock(sep.outputs, "X"), loc=(-1300, -1650), clamp=False)
    in_channel = dc.math_node(nt, "LESS_THAN", x_abs, 0.0065, loc=(-1150, -1650), clamp=False)
    z = dc._sock(sep.outputs, "Z")
    z_in = dc.math_node(nt, "MULTIPLY", dc.math_node(nt, "GREATER_THAN", z, z0, loc=(-1300, -1800), clamp=False),
                        dc.math_node(nt, "LESS_THAN", z, z1, loc=(-1300, -1900), clamp=False), loc=(-1150, -1850))
    glyph_wave = dc.math_node(nt, "FRACT", dc.math_node(nt, "MULTIPLY", z, rune_freq, loc=(-1300, -2000), clamp=False),
                              loc=(-1150, -2000), clamp=False)
    glyph = dc.math_node(nt, "LESS_THAN", glyph_wave, 0.62, loc=(-1000, -2000), clamp=False)
    glyph_n = dc.noise(nt, scale=90.0, detail=1.0, roughness=0.4, loc=(-1300, -2150), coord=coord)
    glyph2 = dc.math_node(nt, "GREATER_THAN", dc._sock(glyph_n.outputs, "Fac"), 0.42, loc=(-1000, -2150), clamp=False)
    m = dc.math_node(nt, "MULTIPLY", in_channel, z_in, loc=(-850, -1800))
    m = dc.math_node(nt, "MULTIPLY", m, glyph, loc=(-750, -1900))
    m = dc.math_node(nt, "MULTIPLY", m, glyph2, loc=(-650, -1950))
    _, emit_col = dc.mix_rgb(nt, (0, 0, 0, 1), dc.hex_rgba(rune_hex), m, loc=(-450, -500))
    for l in list(emit_tag.inputs[0].links):
        nt.links.remove(l)
    nt.links.new(emit_col, emit_tag.inputs[0])
    bsdf = dc.principled(nt)
    nt.links.new(emit_tag.outputs[0], dc._sock(bsdf.inputs, "Emission Color"))
    dc._sock(bsdf.inputs, "Emission Strength").default_value = 4.0
    # Runes also read as engraved grooves in the normal bake.
    bump = next(n for n in nt.nodes if n.type == "BUMP")
    h_link = bump.inputs["Height"].links[0].from_socket
    carved = dc.math_node(nt, "SUBTRACT", h_link, dc.math_node(nt, "MULTIPLY", m, 0.8, loc=(-300, -1100)),
                          loc=(-150, -1050), clamp=False)
    nt.links.new(carved, bump.inputs["Height"])
    return mat


def materials():
    M = {}
    M["rusty_blade"] = blade_material("M_RustyBlade", "#FFFFFF", rust_amt=0.9, z0=0.13, z1=0.55)
    M["broad_blade"] = blade_material("M_BroadBlade", "#FFFFFF", rust_amt=0.4, z0=0.20, z1=1.05, rune_freq=18.0)
    M["iron"] = dc.make_material("M_WeaponIron", "#4D555E", dark="#1F2329", light="#88929C", metal=1.0, rough=0.42,
                                 noise_scale=18, noise_amt=0.7, edge_wear="#D8E0E6", edge_wear_amt=1.0,
                                 cavity_dirt=0.9, bump_scale=60, bump_strength=0.2, bevel_radius=0.004)
    M["brass"] = dc.make_material("M_Brass", "#8C6A32", dark="#4A3416", light="#C9A35C", metal=1.0, rough=0.4,
                                  noise_scale=14, edge_wear="#F0D79A", edge_wear_amt=1.0, cavity_dirt=0.8,
                                  bevel_radius=0.004)
    M["grip"] = dc.make_material("M_GripWrap", "#3B2618", dark="#1A0F09", light="#6A4A30", rough=0.7,
                                 stripes=("z", 85.0, 0.2, "#160C06"), cavity_dirt=0.6, bump_scale=120,
                                 bevel_radius=0.003)
    M["wood"] = dc.make_material("M_ShieldWood", "#6B4426", dark="#2E1A0D", light="#94663D", rough=0.8,
                                 noise_scale=4.0, noise_amt=0.9, stripes=("x", 9.0, 0.05, "#20120A"),
                                 edge_wear="#B98C5E", edge_wear_amt=0.7, cavity_dirt=0.8, bump_scale=35,
                                 bump_strength=0.35, bevel_radius=0.006)
    M["shield_paint"] = dc.make_material("M_ShieldPaint", "#780016", dark="#3D000B", light="#A31A2E", rough=0.75,
                                         noise_scale=6.0, noise_amt=0.9, edge_wear="#6B4426", edge_wear_amt=1.4,
                                         cavity_dirt=0.7, bump_scale=40, bevel_radius=0.005)
    return M


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def blade_mesh(name, length, w_base, w_tip, thick, z0, fuller=(0.15, 0.7), nicks=5, seed=0, tip_len=0.12,
               serrate=0.0):
    """Diamond cross-section blade along +Z with a sunken fuller and nicks."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    rows = 28
    rings = []
    nick_z = sorted(rnd.uniform(0.12, 0.85) for _ in range(nicks))
    for i in range(rows + 1):
        t = i / rows
        z = z0 + length * t
        body_t = min(1.0, (length * t) / (length - tip_len))
        w = w_base + (w_tip - w_base) * body_t
        if length * t > length - tip_len:
            u = (length * t - (length - tip_len)) / tip_len
            w = w_tip * (1.0 - u) ** 0.85
        w *= 0.5
        for nz in nick_z:
            d = abs(t - nz)
            if d < 0.025:
                w *= 1.0 - 0.28 * (1.0 - d / 0.025)
        if serrate > 0 and 0.1 < t < 0.85:
            w *= 1.0 - serrate * (0.5 + 0.5 * math.sin(t * 90.0))
        th = thick * 0.5 * (1.0 - 0.75 * max(0.0, body_t - 0.85) / 0.15 if body_t > 0.85 else 1.0)
        in_fuller = fuller[0] < t < fuller[1]
        f_depth = th * 0.55 if in_fuller else 0.0
        # Cross-section: edge, bevel shoulder, fuller lip, fuller centre (mirrored).
        prof = [(w, 0.0), (w * 0.62, th * 0.85), (w * 0.22, th), (0.0, th - f_depth),
                (-w * 0.22, th), (-w * 0.62, th * 0.85), (-w, 0.0),
                (-w * 0.62, -th * 0.85), (-w * 0.22, -th), (0.0, -th + f_depth), (w * 0.22, -th), (w * 0.62, -th * 0.85)]
        rings.append([bm.verts.new((x, y, z)) for x, y in prof])
    n = len(rings[0])
    for k in range(rows):
        for j in range(n):
            j2 = (j + 1) % n
            bm.faces.new((rings[k][j], rings[k][j2], rings[k + 1][j2], rings[k + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bmesh.ops.remove_doubles(bm, verts=rings[-1], dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return dc.mesh_object(name, bm)


def build_rusty_sword(M):
    blade = blade_mesh("RS_Blade", 0.70, 0.07, 0.056, 0.014, 0.075, fuller=(0.06, 0.72), nicks=6, seed=3)
    dc.assign_material(blade, M["rusty_blade"])
    guard = dc.tube_along("RS_Guard", [(-0.11, 0, 0.09), (-0.06, 0, 0.068), (0.0, 0, 0.064), (0.06, 0, 0.068),
                                       (0.11, 0, 0.09)], [0.016, 0.014, 0.018, 0.014, 0.016], segments=8)
    dc.assign_material(guard, M["iron"])
    block = dc.box("RS_GuardBlock", (0.05, 0.03, 0.035), (0, 0, 0.066), bevel=0.006)
    dc.assign_material(block, M["iron"])
    grip = dc.lathe("RS_Grip", [(0.015, -0.058), (0.018, -0.03), (0.019, 0.0), (0.018, 0.03), (0.016, 0.05)],
                    segments=10)
    dc.assign_material(grip, M["grip"])
    pommel = dc.ico("RS_Pommel", 0.026, (0, 0, -0.078), subdiv=2)
    dc.deform(pommel, lambda v: Vector((v.x, v.y * 0.7, -0.078 + (v.z + 0.078) * 1.15)))
    dc.assign_material(pommel, M["iron"])
    return [blade, guard, block, grip, pommel]


def build_broadsword(M):
    blade = blade_mesh("BS_Blade", 1.18, 0.14, 0.11, 0.022, 0.12, fuller=(0.05, 0.78), nicks=8, seed=9,
                       tip_len=0.2, serrate=0.04)
    dc.assign_material(blade, M["broad_blade"])
    guard = dc.tube_along("BS_Guard", [(-0.20, 0, 0.16), (-0.14, 0, 0.11), (-0.06, 0, 0.10), (0.0, 0, 0.10),
                                       (0.06, 0, 0.10), (0.14, 0, 0.11), (0.20, 0, 0.16)],
                          [0.026, 0.022, 0.024, 0.03, 0.024, 0.022, 0.026], segments=8)
    dc.assign_material(guard, M["brass"])
    ricasso = dc.box("BS_Ricasso", (0.10, 0.04, 0.06), (0, 0, 0.11), bevel=0.01)
    dc.assign_material(ricasso, M["iron"])
    grip = dc.lathe("BS_Grip", [(0.020, -0.17), (0.023, -0.12), (0.024, -0.04), (0.023, 0.04), (0.021, 0.085)],
                    segments=10)
    dc.assign_material(grip, M["grip"])
    pommel = dc.lathe("BS_Pommel", [(0.0, -0.25), (0.03, -0.245), (0.042, -0.22), (0.036, -0.19), (0.02, -0.175),
                                    (0.0, -0.172)], segments=12)
    dc.assign_material(pommel, M["brass"])
    return [blade, guard, ricasso, grip, pommel]


def build_shield(M):
    """Round iron-trimmed buckler. Faces +Z; handle centred at the origin."""
    radius = 0.29
    face_z = 0.06
    planks = []
    for i in range(5):
        x0 = -radius + i * (2 * radius / 5)
        plank = dc.box(f"SH_Plank{i}", (2 * radius / 5 - 0.004, 2 * radius, 0.03),
                       (x0 + radius / 5, 0, face_z), bevel=0.004)
        planks.append(plank)
    board = dc.join(planks, "SH_Board")
    # Cut the planks to a disc.
    bm = bmesh.new()
    bm.from_mesh(board.data)
    for v in bm.verts:
        r = math.hypot(v.co.x, v.co.y)
        if r > radius:
            v.co.x *= radius / r
            v.co.y *= radius / r
        # Slight convex dish.
        v.co.z += 0.05 * (1.0 - (math.hypot(v.co.x, v.co.y) / radius) ** 2)
    bm.to_mesh(board.data)
    bm.free()
    dc.assign_material(board, M["wood"])
    paint = dc.lathe("SH_Paint", [(0.0, 0.0), (0.12, -0.004), (0.2, -0.015), (0.255, -0.03)], segments=28,
                     cap_bottom=False)
    dc.deform(paint, lambda v: Vector((v.x, v.y, v.z + face_z + 0.02 + 0.05 * (1.0 - (math.hypot(v.x, v.y) / radius) ** 2) + 0.001)))
    dc.assign_material(paint, M["shield_paint"])
    rim = dc.lathe("SH_Rim", [(radius - 0.02, face_z + 0.035), (radius + 0.012, face_z + 0.02), (radius + 0.016, face_z - 0.005),
                              (radius + 0.008, face_z - 0.02), (radius - 0.02, face_z - 0.018)], segments=32,
                   cap_top=False, cap_bottom=False)
    dc.assign_material(rim, M["iron"])
    boss = dc.lathe("SH_Boss", [(0.085, face_z + 0.06), (0.075, face_z + 0.09), (0.05, face_z + 0.115),
                                (0.02, face_z + 0.125), (0.0, face_z + 0.127)], segments=20, cap_bottom=False)
    dc.assign_material(boss, M["iron"])
    straps = []
    for ang in (0.0, math.pi / 2):
        st = dc.box(f"SH_Strap{int(ang * 10)}", (0.045, 2 * radius - 0.03, 0.012), (0, 0, 0), bevel=0.004)
        dc.deform(st, lambda v: Vector((v.x, v.y, v.z + face_z + 0.03 + 0.05 * (1.0 - min(1.0, abs(v.y) / radius) ** 2))))
        st.data.transform(Matrix.Rotation(ang, 4, "Z"))
        dc.assign_material(st, M["iron"])
        straps.append(st)
    rivets = []
    for k in range(16):
        a = math.tau * k / 16
        rv = dc.ico(f"SH_Rivet{k}", 0.011, (math.cos(a) * (radius - 0.03), math.sin(a) * (radius - 0.03), face_z + 0.04), 1)
        dc.assign_material(rv, M["iron"])
        rivets.append(rv)
    handle = dc.tube_along("SH_Handle", [(-0.07, 0, 0.035), (-0.05, 0, 0.0), (0.05, 0, 0.0), (0.07, 0, 0.035)],
                           [0.014] * 4, segments=8)
    dc.assign_material(handle, M["grip"])
    return [board, paint, rim, boss] + straps + rivets + [handle]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build(live=True, size=1024):
    if not live:
        dc.reset_scene()
    coll = dc.collection(COLL)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    M = materials()
    weapons = {
        "RustySword": build_rusty_sword(M),
        "Broadsword": build_broadsword(M),
        "FrontlineShield": build_shield(M),
    }
    for parts in weapons.values():
        for p in parts:
            dc.move_to(p, coll)
            for poly in p.data.polygons:
                poly.use_smooth = True
    # Temporarily lay them out apart so AO from one never darkens another.
    offsets = {"RustySword": Vector((10, 0, 0)), "Broadsword": Vector((12, 0, 0)), "FrontlineShield": Vector((14, 0, 0))}
    for key, parts in weapons.items():
        for p in parts:
            p.location = offsets[key]
    all_parts = [p for parts in weapons.values() for p in parts]
    importance = {"M_RustyBlade": 1.4, "M_BroadBlade": 1.25, "M_ShieldPaint": 1.1, "M_ShieldWood": 1.0}
    dc.uv_atlas_multi(all_parts, island_margin=0.004, importance=importance)
    pairs = [(p, dc.make_highpoly(p, bevel_width=0.002, subsurf=1)) for p in all_parts]
    paths = dc.bake_texture_set(all_parts, TEX_DIR, "Weapons", size=size, highpoly=pairs)
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    baked = dc.baked_material("M_Weapons", paths, emission_strength=3.0)
    results = {}
    for key, parts in weapons.items():
        for p in parts:
            p.location = (0, 0, 0)
        obj = dc.join(parts, key)
        obj.data.materials.clear()
        obj.data.materials.append(baked)
        tri = obj.modifiers.new("NgonTriangulate", "TRIANGULATE")
        tri.min_vertices = 5
        dc.export_fbx(OUT_DIR / f"{key}.fbx", [obj], static=True)
        results[key] = obj
    # Display layout next to the character (does not affect the exported pivots).
    results["RustySword"].location = (-0.9, 0.0, 0.9)
    results["Broadsword"].location = (-1.25, 0.0, 0.6)
    results["FrontlineShield"].location = (-1.75, 0.0, 1.0)
    results["FrontlineShield"].rotation_euler = (math.radians(90), 0, 0)
    print("[weapons] exported", list(results), {k: str(v) for k, v in paths.items()})
    return results


if __name__ == "__main__":
    build(live=False)
