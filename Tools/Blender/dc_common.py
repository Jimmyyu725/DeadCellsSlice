"""Shared Blender utilities for the Dead Cells vertical slice asset pipeline.

Every generator script imports this module. It covers scene setup, procedural
"bakeable" materials, UV atlasing, Cycles texture baking (albedo / normal /
ORM / emission) and Unity-oriented FBX export.

Conventions (see Tools/PIPELINE.md):
  * 1 Blender unit = 1 metre, Z up, characters face -Y, feet on the origin.
  * Export axis: forward=Z, up=Y  ->  Blender (x, y, z) == Unity (x, z, y).
    The game camera looks down Unity +Z, i.e. Blender +Y: visible faces of
    environment pieces point to Blender -Y, depth grows with Blender +Y.
    Characters face Blender -Y, i.e. Unity -Z (towards the camera).
  * Procedural materials expose four named nodes that the baker re-routes:
      DC_ALBEDO (color), DC_ROUGH (float), DC_METAL (float), DC_EMIT (color)
"""

import math
import os
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ART_ROOT = PROJECT_ROOT / "Assets" / "_Project" / "Art"
OUT_ROOT = PROJECT_ROOT / "Tools" / "_out"

BAKE_NODE_TAGS = ("DC_ALBEDO", "DC_ROUGH", "DC_METAL", "DC_EMIT")
AO_DISTANCE = 0.15  # metres; local cavity occlusion for textures


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

def reset_scene(fps=60):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def clear_scene_live(fps=60):
    """Empty the *current* file without resetting preferences (safe to run
    inside the user's live Blender, where read_factory_settings would also
    unload the MCP add-on)."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.actions,
                 bpy.data.cameras, bpy.data.lights, bpy.data.images, bpy.data.textures, bpy.data.curves):
        for block in list(coll):
            if block.users == 0 or coll in (bpy.data.actions,):
                coll.remove(block)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def move_to(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def setup_cycles(samples=8, use_gpu=True):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    if os.environ.get("DC_CYCLES_CPU"):
        use_gpu = False  # e.g. when another Blender already holds the GPU memory
    if use_gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        try:
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            scene.cycles.device = "GPU"
        except (TypeError, AttributeError):
            scene.cycles.device = "CPU"
    return scene


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def deselect_all():
    for o in bpy.context.scene.objects:
        if o is not None:
            o.select_set(False)


def set_active(obj, select_only=True):
    if select_only:
        deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_all_modifiers(obj):
    set_active(obj)
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError as exc:
            print(f"[dc] modifier {mod.name} on {obj.name} not applied: {exc}")
            obj.modifiers.remove(mod)


def apply_transforms(obj):
    set_active(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def join(objects, name):
    objects = [o for o in objects if o is not None]
    set_active(objects[0])
    for o in objects:
        o.select_set(True)
    bpy.ops.object.join()
    result = bpy.context.view_layer.objects.active
    result.name = name
    result.data.name = name
    return result


def shade_smooth(obj, angle_deg=40.0):
    for poly in obj.data.polygons:
        poly.use_smooth = True
    set_active(obj)
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle_deg))
    except (RuntimeError, AttributeError, TypeError):
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))
        except (RuntimeError, AttributeError, TypeError):
            pass


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(hex_str, alpha=1.0):
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def mix_hex(a, b, t):
    ca, cb = hex_rgba(a), hex_rgba(b)
    return tuple(ca[i] * (1 - t) + cb[i] * t for i in range(4))


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------

def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident:
            return s
    for s in sockets:
        if s.name == ident:
            return s
    raise KeyError(f"socket {ident} not found in {[s.identifier for s in sockets]}")


def principled(nt):
    return next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")


def output_node(nt):
    return next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")


def new_node(nt, type_name, location=(0, 0), label=None):
    node = nt.nodes.new(type_name)
    node.location = location
    if label:
        node.label = label
        node.name = label
    return node


def tag_node(nt, tag, location):
    """A reroute node used as a stable bake tap point."""
    node = new_node(nt, "NodeReroute", location)
    node.name = tag
    node.label = tag
    return node


def noise(nt, scale=6.0, detail=4.0, roughness=0.55, loc=(-1200, 0), coord=None, dims="3D"):
    n = new_node(nt, "ShaderNodeTexNoise", loc)
    try:
        n.noise_dimensions = dims
    except (AttributeError, TypeError):
        pass
    _sock(n.inputs, "Scale").default_value = scale
    _sock(n.inputs, "Detail").default_value = detail
    _sock(n.inputs, "Roughness").default_value = roughness
    if coord is not None:
        nt.links.new(coord, _sock(n.inputs, "Vector"))
    return n


def ramp(nt, stops, loc=(-900, 0)):
    """stops: list of (position, rgba)."""
    n = new_node(nt, "ShaderNodeValToRGB", loc)
    cr = n.color_ramp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos)
        e.color = col
    return n


def mix_rgb(nt, a, b, fac, blend="MIX", loc=(-600, 0)):
    """a, b, fac may be sockets or constants."""
    n = new_node(nt, "ShaderNodeMix", loc)
    n.data_type = "RGBA"
    n.blend_type = blend
    f_in, a_in, b_in = _sock(n.inputs, "Factor_Float"), _sock(n.inputs, "A_Color"), _sock(n.inputs, "B_Color")
    for sock, val in ((f_in, fac), (a_in, a), (b_in, b)):
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, sock)
        else:
            sock.default_value = val
    n.clamp_result = True
    return n, _sock(n.outputs, "Result_Color")


def math_node(nt, op, a, b=0.0, loc=(-600, -300), clamp=True):
    n = new_node(nt, "ShaderNodeMath", loc)
    n.operation = op
    n.use_clamp = clamp
    for idx, val in ((0, a), (1, b)):
        if isinstance(val, bpy.types.NodeSocket):
            nt.links.new(val, n.inputs[idx])
        else:
            n.inputs[idx].default_value = val
    return n.outputs[0]


def map_range(nt, value, from_min, from_max, to_min=0.0, to_max=1.0, loc=(-700, -200)):
    n = new_node(nt, "ShaderNodeMapRange", loc)
    nt.links.new(value, _sock(n.inputs, "Value"))
    _sock(n.inputs, "From Min").default_value = from_min
    _sock(n.inputs, "From Max").default_value = from_max
    _sock(n.inputs, "To Min").default_value = to_min
    _sock(n.inputs, "To Max").default_value = to_max
    n.clamp = True
    return _sock(n.outputs, "Result")


def tex_coord(nt, kind="Object", loc=(-1600, 0)):
    n = new_node(nt, "ShaderNodeTexCoord", loc)
    return _sock(n.outputs, kind)


# ---------------------------------------------------------------------------
# Procedural bakeable material
# ---------------------------------------------------------------------------

def make_material(
    name,
    base,
    *,
    dark=None,
    light=None,
    rough=0.75,
    rough_var=0.12,
    metal=0.0,
    noise_scale=9.0,
    noise_amt=0.55,
    edge_wear=None,
    edge_wear_amt=0.0,
    cavity_dirt=0.0,
    bevel_radius=0.012,
    bump_strength=0.25,
    bump_scale=40.0,
    stripes=None,
    emission=None,
    emission_strength=0.0,
    emission_mask=None,
):
    """Build a Cycles material that looks hand painted once baked.

    base/dark/light are hex strings forming a 3-stop value ramp driven by
    noise.  edge_wear lightens convex edges (pointiness), cavity_dirt darkens
    concave areas.  stripes=(axis, frequency, width, hex) paints bands such as
    bandage wraps or trims.  emission_mask:
        None        -> whole surface emits `emission` (if given)
        "stripes"   -> emission only on the stripe bands (rune channels)
        "noise"     -> emission on bright noise blobs
    """
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    bsdf = principled(nt)
    out = output_node(nt)
    bsdf.location = (300, 0)
    out.location = (650, 0)

    coord = tex_coord(nt, "Object")
    n_big = noise(nt, scale=noise_scale, detail=5.0, roughness=0.6, loc=(-1300, 250), coord=coord)
    n_fine = noise(nt, scale=noise_scale * 6.0, detail=3.0, roughness=0.5, loc=(-1300, -50), coord=coord)

    dark = dark or base
    light = light or base
    value_ramp = ramp(nt, [(0.25, hex_rgba(dark)), (0.5, hex_rgba(base)), (0.78, hex_rgba(light))], loc=(-1000, 250))
    fac = map_range(nt, _sock(n_big.outputs, "Fac"), 0.5 - noise_amt * 0.5, 0.5 + noise_amt * 0.5, loc=(-1150, 250))
    nt.links.new(fac, _sock(value_ramp.inputs, "Fac"))
    color = _sock(value_ramp.outputs, "Color")

    # Fine grain multiply (cloth weave / leather pores / stone grit).
    grain = map_range(nt, _sock(n_fine.outputs, "Fac"), 0.3, 0.7, 0.88, 1.06, loc=(-1000, -50))
    _, color = mix_rgb(nt, color, (1, 1, 1, 1), 1.0, blend="MULTIPLY", loc=(-800, 150))
    mult_node = color.node
    grain_rgb = new_node(nt, "ShaderNodeCombineColor", (-850, -50))
    for ch in ("Red", "Green", "Blue"):
        nt.links.new(grain, _sock(grain_rgb.inputs, ch))
    nt.links.new(_sock(grain_rgb.outputs, "Color"), _sock(mult_node.inputs, "B_Color"))

    stripe_mask = None
    if stripes:
        axis, freq, width, stripe_hex = stripes
        sep = new_node(nt, "ShaderNodeSeparateXYZ", (-1400, -400))
        nt.links.new(coord, _sock(sep.inputs, "Vector"))
        axis_val = _sock(sep.outputs, axis.upper())
        # Slight diagonal skew makes wraps read as spiral bandages.
        skew = math_node(nt, "MULTIPLY_ADD", _sock(sep.outputs, "X" if axis.upper() != "X" else "Y"), 0.35, loc=(-1250, -420), clamp=False)
        nt.links.new(axis_val, skew.node.inputs[2])
        wave = new_node(nt, "ShaderNodeMath", (-1100, -420))
        wave.operation = "SINE"
        scaled = math_node(nt, "MULTIPLY", skew, freq * math.tau, loc=(-1180, -420), clamp=False)
        nt.links.new(scaled, wave.inputs[0])
        stripe_mask = map_range(nt, wave.outputs[0], 1.0 - width * 2.0, 1.0 - width * 2.0 + 0.08, loc=(-950, -420))
        _, color = mix_rgb(nt, color, hex_rgba(stripe_hex), stripe_mask, loc=(-650, 0))

    geo = new_node(nt, "ShaderNodeNewGeometry", (-1400, -700))
    if edge_wear and edge_wear_amt > 0:
        edge = map_range(nt, _sock(geo.outputs, "Pointiness"), 0.52, 0.58, loc=(-1100, -700))
        edge_n = math_node(nt, "MULTIPLY", edge, _sock(n_fine.outputs, "Fac"), loc=(-950, -700))
        edge_n = math_node(nt, "MULTIPLY", edge_n, edge_wear_amt * 2.0, loc=(-850, -700))
        _, color = mix_rgb(nt, color, hex_rgba(edge_wear), edge_n, loc=(-500, 0))
    if cavity_dirt > 0:
        cav = map_range(nt, _sock(geo.outputs, "Pointiness"), 0.47, 0.5, 1.0, 0.0, loc=(-1100, -900))
        cav = math_node(nt, "MULTIPLY", cav, cavity_dirt, loc=(-950, -900))
        _, color = mix_rgb(nt, color, hex_rgba("#05070C"), cav, loc=(-400, 0))

    albedo_tag = tag_node(nt, "DC_ALBEDO", (-200, 100))
    nt.links.new(color, albedo_tag.inputs[0])
    nt.links.new(albedo_tag.outputs[0], _sock(bsdf.inputs, "Base Color"))

    rough_val = map_range(nt, _sock(n_fine.outputs, "Fac"), 0.3, 0.7, rough - rough_var, rough + rough_var, loc=(-700, -250))
    rough_tag = tag_node(nt, "DC_ROUGH", (-200, -100))
    nt.links.new(rough_val, rough_tag.inputs[0])
    nt.links.new(rough_tag.outputs[0], _sock(bsdf.inputs, "Roughness"))

    metal_val = new_node(nt, "ShaderNodeValue", (-700, -350))
    metal_val.outputs[0].default_value = metal
    metal_tag = tag_node(nt, "DC_METAL", (-200, -200))
    nt.links.new(metal_val.outputs[0], metal_tag.inputs[0])
    nt.links.new(metal_tag.outputs[0], _sock(bsdf.inputs, "Metallic"))

    # Emission colour (LDR) -- intensity is applied in Unity as HDR.
    emit_tag = tag_node(nt, "DC_EMIT", (-200, -300))
    if emission:
        if emission_mask == "stripes" and stripe_mask is not None:
            _, emit_col = mix_rgb(nt, (0, 0, 0, 1), hex_rgba(emission), stripe_mask, loc=(-500, -500))
        elif emission_mask == "noise":
            blobs = map_range(nt, _sock(n_big.outputs, "Fac"), 0.55, 0.7, loc=(-700, -550))
            _, emit_col = mix_rgb(nt, (0, 0, 0, 1), hex_rgba(emission), blobs, loc=(-500, -500))
        else:
            rgb = new_node(nt, "ShaderNodeRGB", (-500, -500))
            rgb.outputs[0].default_value = hex_rgba(emission)
            emit_col = rgb.outputs[0]
        nt.links.new(emit_col, emit_tag.inputs[0])
        nt.links.new(emit_tag.outputs[0], _sock(bsdf.inputs, "Emission Color"))
        _sock(bsdf.inputs, "Emission Strength").default_value = max(emission_strength, 1.0)
    else:
        black = new_node(nt, "ShaderNodeRGB", (-500, -500))
        black.outputs[0].default_value = (0, 0, 0, 1)
        nt.links.new(black.outputs[0], emit_tag.inputs[0])

    # Surface detail for the normal bake: rounded edges + micro bump.
    bevel = new_node(nt, "ShaderNodeBevel", (-300, -700))
    bevel.samples = 8
    _sock(bevel.inputs, "Radius").default_value = bevel_radius
    bump = new_node(nt, "ShaderNodeBump", (0, -700))
    _sock(bump.inputs, "Strength").default_value = bump_strength
    _sock(bump.inputs, "Distance").default_value = 0.02
    n_bump = noise(nt, scale=bump_scale, detail=6.0, roughness=0.6, loc=(-300, -950), coord=coord)
    bump_height = _sock(n_bump.outputs, "Fac")
    if stripe_mask is not None:
        bump_height = math_node(nt, "ADD", bump_height, math_node(nt, "MULTIPLY", stripe_mask, 0.6, loc=(-200, -1050)), loc=(-100, -950), clamp=False)
    nt.links.new(bump_height, _sock(bump.inputs, "Height"))
    nt.links.new(_sock(bevel.outputs, "Normal"), _sock(bump.inputs, "Normal"))
    nt.links.new(_sock(bump.outputs, "Normal"), _sock(bsdf.inputs, "Normal"))

    mat["dc_base_hex"] = base
    return mat


def make_flat_material(name, hex_color, emission=None, strength=1.0):
    """Simple material for non-baked parts (flame cards etc.)."""
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    bsdf = principled(nt)
    _sock(bsdf.inputs, "Base Color").default_value = hex_rgba(hex_color)
    if emission:
        _sock(bsdf.inputs, "Emission Color").default_value = hex_rgba(emission)
        _sock(bsdf.inputs, "Emission Strength").default_value = strength
    return mat


def assign_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------------------
# Mesh construction helpers (all return linked objects)
# ---------------------------------------------------------------------------

def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    return link(obj)


def lathe(name, profile, segments=16, scale_xy=(1.0, 1.0), cap_top=True, cap_bottom=True, phase=0.0):
    """Revolve a (radius, z) profile around Z. Produces clean quad rings."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(segments):
            a = phase + math.tau * i / segments
            ring.append(bm.verts.new((math.cos(a) * r * scale_xy[0], math.sin(a) * r * scale_xy[1], z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if cap_bottom and profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


def tube_along(name, points, radii, segments=10, up=Vector((0, 0, 1)), cap=True, flatten=1.0):
    """Sweep a circle along a polyline. radii per point. flatten squashes the
    cross-section (ribbon-like scarf/tendrils when < 1)."""
    bm = bmesh.new()
    rings = []
    n = len(points)
    for k, p in enumerate(points):
        p = Vector(p)
        if k == 0:
            t = (Vector(points[1]) - p).normalized()
        elif k == n - 1:
            t = (p - Vector(points[k - 1])).normalized()
        else:
            t = (Vector(points[k + 1]) - Vector(points[k - 1])).normalized()
        ref = up if abs(t.dot(up)) < 0.95 else Vector((1, 0, 0))
        side = t.cross(ref).normalized()
        nrm = side.cross(t).normalized()
        ring = []
        for i in range(segments):
            a = math.tau * i / segments
            offset = side * math.cos(a) * radii[k] + nrm * math.sin(a) * radii[k] * flatten
            ring.append(bm.verts.new(p + offset))
        rings.append(ring)
    for k in range(n - 1):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    if cap:
        if radii[0] > 1e-4:
            bm.faces.new(list(reversed(rings[0])))
        if radii[-1] > 1e-4:
            bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


def box(name, size, location=(0, 0, 0), bevel=0.0, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(location)
    obj = mesh_object(name, bm)
    if bevel > 0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
        apply_all_modifiers(obj)
    return obj


def ico(name, radius, location=(0, 0, 0), subdiv=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        v.co += Vector(location)
    return mesh_object(name, bm)


def deform(obj, fn):
    """Apply fn(Vector)->Vector to every vertex (object space)."""
    for v in obj.data.vertices:
        v.co = fn(v.co.copy())
    obj.data.update()


def jitter(obj, amount, seed=0):
    rnd = random.Random(seed)
    for v in obj.data.vertices:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * amount
    obj.data.update()


def add_modifier(obj, kind, **props):
    mod = obj.modifiers.new(kind.lower(), kind)
    for k, v in props.items():
        setattr(mod, k, v)
    return mod


def subdivide(obj, levels=1, apply=True):
    add_modifier(obj, "SUBSURF", levels=levels, render_levels=levels)
    if apply:
        apply_all_modifiers(obj)


def mirror_x(obj):
    add_modifier(obj, "MIRROR", use_axis=(True, False, False), use_clip=True, use_mirror_merge=True)
    apply_all_modifiers(obj)


# ---------------------------------------------------------------------------
# UV atlas
# ---------------------------------------------------------------------------

def uv_atlas(obj, island_margin=0.004, angle_limit=62.0, importance=None):
    """Seam-aware unwrap + importance-weighted island packing.

    importance: {material_name: scale}; islands of more important materials
    get proportionally more texels before the final pack.
    """
    set_active(obj)
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # Seams from hard edges first, so that the projection respects them.
    bpy.ops.mesh.select_mode(type="EDGE")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(angle_limit))
    bpy.ops.mesh.mark_seam(clear=False)
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limit), island_margin=island_margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")

    if importance:
        me = obj.data
        uv = me.uv_layers.active.data
        mats = [m.name if m else "" for m in me.materials]
        for poly in me.polygons:
            s = importance.get(mats[poly.material_index] if poly.material_index < len(mats) else "", 1.0)
            if s == 1.0:
                continue
            for li in poly.loop_indices:
                uv[li].uv *= s
        me.update()

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, margin=island_margin, shape_method="CONCAVE")
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=island_margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def uv_atlas_multi(objs, island_margin=0.003, angle_limit=62.0, importance=None):
    """Like uv_atlas but packs several objects into one shared 0-1 space
    (multi-object edit mode), so they can be baked separately and joined
    afterwards without overlapping islands."""
    deselect_all()
    for o in objs:
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="EDGE")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(angle_limit))
    bpy.ops.mesh.mark_seam(clear=False)
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limit), island_margin=island_margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    if importance:
        for o in objs:
            mat = o.active_material.name if o.active_material else ""
            s = importance.get(o.name, importance.get(mat, 1.0))
            if s != 1.0:
                for d in o.data.uv_layers.active.data:
                    d.uv *= s
    deselect_all()
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, margin=island_margin, shape_method="CONCAVE")
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=island_margin)
    bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------------------
# Baking
# ---------------------------------------------------------------------------

def new_image(name, size, non_color=False, alpha=False):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=False)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    img.generated_color = (0.5, 0.5, 1.0, 1.0) if non_color else (0, 0, 0, 1)
    return img


def _materials_of(objs):
    seen = []
    for o in objs:
        for slot in o.material_slots:
            if slot.material and slot.material not in seen:
                seen.append(slot.material)
    return seen


def _set_bake_target(mats, image):
    for mat in mats:
        nt = mat.node_tree
        node = nt.nodes.get("DC_BAKE_TARGET")
        if node is None:
            node = new_node(nt, "ShaderNodeTexImage", (600, 400), label="DC_BAKE_TARGET")
        node.image = image
        for n in nt.nodes:
            n.select = False
        node.select = True
        nt.nodes.active = node


def _route_tag_to_output(mat, tag):
    """Temporarily plug a tagged value into an emission-only output."""
    nt = mat.node_tree
    out = output_node(nt)
    old = [l.from_socket for l in out.inputs["Surface"].links]
    emit = nt.nodes.get("DC_BAKE_EMIT") or new_node(nt, "ShaderNodeEmission", (450, 300), label="DC_BAKE_EMIT")
    src = nt.nodes.get(tag)
    if tag == "DC_AO":
        src = nt.nodes.get("DC_AO") or new_node(nt, "ShaderNodeAmbientOcclusion", (200, 500), label="DC_AO")
        src.samples = 24
        src.only_local = False
        _sock(src.inputs, "Distance").default_value = AO_DISTANCE
        nt.links.new(_sock(src.outputs, "AO"), _sock(emit.inputs, "Color"))
        src = None
        tag = None
    if tag is None:
        pass
    elif src is None:
        _sock(emit.inputs, "Color").default_value = (0, 0, 0, 1)
        for l in list(emit.inputs["Color"].links):
            nt.links.remove(l)
    else:
        nt.links.new(src.outputs[0], _sock(emit.inputs, "Color"))
    _sock(emit.inputs, "Strength").default_value = 1.0
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    return old


def _restore_output(mat, old):
    nt = mat.node_tree
    out = output_node(nt)
    for l in list(out.inputs["Surface"].links):
        nt.links.remove(l)
    if old:
        nt.links.new(old[0], out.inputs["Surface"])


def bake_pass(targets, image, kind, sources=None, cage_extrusion=0.03, max_ray=0.08, samples=4, margin=8, clear=True):
    """Bake one channel of `targets` (object or list sharing one UV atlas).

    kind: ALBEDO | ROUGH | METAL | EMIT_MASK | NORMAL | AO
    sources: optional high-poly objects for a selected-to-active NORMAL bake
    (single target only). They are hidden from every other pass so they do
    not occlude the low-poly surface.
    """
    targets = targets if isinstance(targets, (list, tuple)) else [targets]
    scene = bpy.context.scene
    scene.cycles.samples = samples
    bake = scene.render.bake
    bake.margin = margin
    bake.use_clear = clear
    try:
        bake.target = "IMAGE_TEXTURES"
    except TypeError:
        pass
    sources = list(sources or [])
    use_s2a = bool(sources) and kind == "NORMAL"
    if use_s2a and len(targets) != 1:
        raise ValueError("selected-to-active bakes need exactly one target")
    for s in sources:
        s.hide_render = not use_s2a
    mats = _materials_of(targets + (sources if use_s2a else []))
    _set_bake_target(_materials_of(targets), image)

    deselect_all()
    for t in targets:
        t.select_set(True)
    if use_s2a:
        for s in sources:
            s.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]

    try:
        if kind in ("ALBEDO", "ROUGH", "METAL", "EMIT_MASK", "AO"):
            tag = {"ALBEDO": "DC_ALBEDO", "ROUGH": "DC_ROUGH", "METAL": "DC_METAL", "EMIT_MASK": "DC_EMIT",
                   "AO": "DC_AO"}[kind]
            if kind == "AO":
                scene.cycles.samples = max(samples, 32)
            saved = {m.name: _route_tag_to_output(m, tag) for m in mats}
            try:
                bpy.ops.object.bake(type="EMIT", use_selected_to_active=False, margin=margin, use_clear=clear)
            finally:
                for m in mats:
                    _restore_output(m, saved[m.name])
        elif kind == "NORMAL":
            bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_selected_to_active=use_s2a,
                                cage_extrusion=cage_extrusion, max_ray_distance=max_ray, margin=margin, use_clear=clear)
        else:
            raise ValueError(kind)
    finally:
        for s in sources:
            s.hide_render = True
    return image


def save_image(image, path):
    path = Path(path)
    ensure_dir(path.parent)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    print(f"[dc] saved {path.relative_to(PROJECT_ROOT) if PROJECT_ROOT in path.parents else path}")
    return path


def pack_orm(ao_img, rough_img, metal_img, name, size):
    """R = occlusion, G = roughness, B = metallic, A = 1."""
    import numpy as np
    n = size * size * 4
    out = new_image(name, size, non_color=True)
    buf = [np.empty(n, dtype=np.float32) for _ in range(3)]
    for b, img in zip(buf, (ao_img, rough_img, metal_img)):
        img.pixels.foreach_get(b)
    orm = np.empty(n, dtype=np.float32)
    orm[0::4] = buf[0][0::4]
    orm[1::4] = buf[1][0::4]
    orm[2::4] = buf[2][0::4]
    orm[3::4] = 1.0
    out.pixels.foreach_set(orm)
    out.update()
    return out


def uv_coverage_mask(objs, size, inset=0.02):
    """Boolean (size, size) mask of texels whose centres lie inside a UV
    triangle of any object (rows bottom-up like Image.pixels)."""
    import numpy as np
    mask = np.zeros((size, size), dtype=bool)
    for o in objs:
        me = o.data
        uv = me.uv_layers.active.data
        me.calc_loop_triangles()
        tris = np.array([[uv[li].uv[:] for li in t.loops] for t in me.loop_triangles], dtype=np.float64) * size
        for p in tris:
            x0, y0 = np.floor(p.min(0)).astype(int)
            x1, y1 = np.ceil(p.max(0)).astype(int)
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size), min(y1, size)
            if x1 <= x0 or y1 <= y0:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            a, b, c = p
            area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(area) < 1e-12:
                continue
            sgn = 1.0 if area > 0 else -1.0
            inside = np.ones(xs.shape, dtype=bool)
            for e0, e1 in ((a, b), (b, c), (c, a)):
                ex, ey = e1[0] - e0[0], e1[1] - e0[1]
                ln = math.hypot(ex, ey) or 1e-12
                d = sgn * (ex * (ys - e0[1]) - ey * (xs - e0[0])) / ln
                inside &= d >= inset
            mask[y0:y1, x0:x1] |= inside
    return mask


def dilate_image(img, mask, iterations=16):
    """Push island colours outwards into uncovered texels (edge padding)."""
    import numpy as np
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    filled = mask.copy()
    for _ in range(iterations):
        pad = np.pad(a * filled[..., None], ((1, 1), (1, 1), (0, 0)))
        cnt = np.pad(filled.astype(np.float32), 1)
        acc = np.zeros_like(a)
        n = np.zeros((h, w), dtype=np.float32)
        for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2), (0, 0), (0, 2), (2, 0), (2, 2)):
            acc += pad[dy:dy + h, dx:dx + w]
            n += cnt[dy:dy + h, dx:dx + w]
        grow = (~filled) & (n > 0)
        if not grow.any():
            break
        a[grow] = acc[grow] / n[grow][:, None]
        filled |= grow
    a[..., 3] = 1.0
    img.pixels.foreach_set(a.ravel())
    img.update()


def bake_texture_set(target, out_dir, prefix, size=2048, highpoly=None, ao=True, emission=True, dilate=16):
    """Full PBR texture set for `target` (one object, or a list of objects
    whose UVs were packed into one shared atlas). Returns {kind: path}.

    With several objects Blender applies the bake margin per object, so each
    object's margin would overwrite its neighbours' texels. Multi-object and
    pairwise bakes therefore run with margin 0 and the finished atlas is
    padded once with a global dilation instead.
    """
    setup_cycles(samples=4)
    out_dir = ensure_dir(out_dir)
    targets = list(target) if isinstance(target, (list, tuple)) else [target]
    pairwise = bool(highpoly) and isinstance(highpoly[0], tuple)
    shared = len(targets) > 1 or pairwise
    margin = 0 if shared else 8
    mask = uv_coverage_mask(targets, size) if shared else None

    def finish(img, name):
        if mask is not None:
            dilate_image(img, mask, dilate)
        return save_image(img, out_dir / f"{prefix}_{name}.png")

    paths = {}
    img = new_image(f"{prefix}_Albedo", size)
    bake_pass(targets, img, "ALBEDO", margin=margin)
    paths["albedo"] = finish(img, "Albedo")

    img = new_image(f"{prefix}_Normal", size, non_color=True)
    if pairwise:
        # Pairwise low->high bakes into one shared atlas: rays never land on
        # a neighbouring part's shell.
        for i, (low, high) in enumerate(highpoly):
            bake_pass(low, img, "NORMAL", sources=[high], samples=8, clear=(i == 0),
                      cage_extrusion=0.02, max_ray=0.05, margin=0)
    else:
        bake_pass(targets if len(targets) > 1 else targets[0], img, "NORMAL", sources=highpoly, samples=8, margin=margin)
    paths["normal"] = finish(img, "Normal")

    rough = bake_pass(targets, new_image(f"{prefix}_R", size, non_color=True), "ROUGH", margin=margin)
    metal = bake_pass(targets, new_image(f"{prefix}_M", size, non_color=True), "METAL", margin=margin)
    if ao:
        occ = bake_pass(targets, new_image(f"{prefix}_AO", size, non_color=True), "AO", samples=32, margin=margin)
    else:
        occ = new_image(f"{prefix}_AO", size, non_color=True)
        occ.generated_color = (1, 1, 1, 1)
    orm = pack_orm(occ, rough, metal, f"{prefix}_ORM", size)
    paths["orm"] = finish(orm, "ORM")

    if emission:
        img = new_image(f"{prefix}_Emission", size)
        bake_pass(targets, img, "EMIT_MASK", margin=margin)
        paths["emission"] = finish(img, "Emission")
    return paths


def make_highpoly(obj, bevel_width=0.01, subsurf=1, displace=0.0, seed=0):
    """Duplicate `obj` into a bevelled, smoothed high-poly bake source."""
    hp = obj.copy()
    hp.data = obj.data.copy()
    hp.name = obj.name + "_HP"
    link(hp)
    for mod in list(hp.modifiers):
        if mod.type == "ARMATURE":
            hp.modifiers.remove(mod)
    if bevel_width > 0:
        add_modifier(hp, "BEVEL", width=bevel_width, segments=3, limit_method="ANGLE",
                     angle_limit=math.radians(35), harden_normals=False)
    if subsurf > 0:
        add_modifier(hp, "SUBSURF", levels=subsurf, render_levels=subsurf)
    if displace > 0:
        tex = bpy.data.textures.new(hp.name + "_disp", "CLOUDS")
        tex.noise_scale = 0.06
        tex.noise_depth = 2
        add_modifier(hp, "DISPLACE", texture=tex, strength=displace, mid_level=0.5)
    apply_all_modifiers(hp)
    for p in hp.data.polygons:
        p.use_smooth = True
    return hp


def baked_material(name, paths, emission_strength=0.0):
    """Preview material wired to baked textures (for Blender renders)."""
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    bsdf = principled(nt)

    def tex(path, non_color, loc):
        n = new_node(nt, "ShaderNodeTexImage", loc)
        n.image = bpy.data.images.load(str(path), check_existing=True)
        n.image.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
        return n

    alb = tex(paths["albedo"], False, (-600, 300))
    nt.links.new(alb.outputs["Color"], _sock(bsdf.inputs, "Base Color"))
    nrm = tex(paths["normal"], True, (-600, -300))
    nmap = new_node(nt, "ShaderNodeNormalMap", (-300, -300))
    nt.links.new(nrm.outputs["Color"], _sock(nmap.inputs, "Color"))
    nt.links.new(_sock(nmap.outputs, "Normal"), _sock(bsdf.inputs, "Normal"))
    orm = tex(paths["orm"], True, (-900, 0))
    sep = new_node(nt, "ShaderNodeSeparateColor", (-600, 0))
    nt.links.new(orm.outputs["Color"], _sock(sep.inputs, "Color"))
    nt.links.new(_sock(sep.outputs, "Green"), _sock(bsdf.inputs, "Roughness"))
    nt.links.new(_sock(sep.outputs, "Blue"), _sock(bsdf.inputs, "Metallic"))
    if "emission" in paths and emission_strength > 0:
        em = tex(paths["emission"], False, (-600, -600))
        nt.links.new(em.outputs["Color"], _sock(bsdf.inputs, "Emission Color"))
        _sock(bsdf.inputs, "Emission Strength").default_value = emission_strength
    return mat


# ---------------------------------------------------------------------------
# Preview rendering (headless sanity checks)
# ---------------------------------------------------------------------------

def preview_render(path, targets=None, views=("front", "side", "three_quarter"), res=512,
                   engine="BLENDER_EEVEE", ortho_scale=None, bg="#1B2A3A", frame=None):
    """Render each view to `<path>_<view>.png`."""
    scene = bpy.context.scene
    if frame is not None:
        scene.frame_set(frame)
    objs = targets or [o for o in scene.objects if o.type == "MESH" and not o.hide_render]
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    center = (lo + hi) * 0.5
    extent = max((hi - lo).length, 0.1)

    prev_engine = scene.render.engine
    try:
        scene.render.engine = engine
    except TypeError:
        scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bgn = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bgn:
        _sock(bgn.inputs, "Color").default_value = hex_rgba(bg)
        _sock(bgn.inputs, "Strength").default_value = 0.6

    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale or extent * 1.05
    cam = link(bpy.data.objects.new("PreviewCam", cam_data))
    scene.camera = cam
    key = link(bpy.data.objects.new("PreviewKey", bpy.data.lights.new("PreviewKey", "SUN")))
    key.data.energy = 3.0
    key.rotation_euler = (math.radians(50), 0, math.radians(30))
    rim = link(bpy.data.objects.new("PreviewRim", bpy.data.lights.new("PreviewRim", "SUN")))
    rim.data.energy = 4.0
    rim.data.color = (0.5, 0.8, 1.0)
    rim.rotation_euler = (math.radians(-60), 0, math.radians(200))

    dirs = {
        "front": Vector((0, -1, 0.05)),
        "back": Vector((0, 1, 0.05)),
        "side": Vector((1, 0, 0.05)),
        # Matches the in-game camera relative to a model yawed -65 deg.
        "game": Vector((-0.906, -0.42, 0.06)),
        "three_quarter": Vector((0.7, -0.7, 0.35)),
        "top": Vector((0, -0.01, 1)),
    }
    written = []
    for view in views:
        d = dirs[view].normalized() if isinstance(view, str) else Vector(view).normalized()
        cam.location = center + d * extent * 3
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = f"{path}_{view}.png"
        bpy.ops.render.render(write_still=True)
        written.append(scene.render.filepath)
    for o in (cam, key, rim):
        bpy.data.objects.remove(o, do_unlink=True)
    scene.render.engine = prev_engine
    return written


# ---------------------------------------------------------------------------
# Rig helpers
# ---------------------------------------------------------------------------

def bone_roll_axis(direction):
    """Pick the roll vector so that every limb's local X points to world +X.

    Z_local = X_world x Y_bone keeps sagittal swings on the local X axis.
    """
    d = Vector(direction).normalized()
    x = Vector((1, 0, 0))
    if abs(d.dot(x)) > 0.9:
        return Vector((0, 0, 1)) if d.x > 0 else Vector((0, 0, -1))
    return x.cross(d).normalized()


def weight_by_segments(obj, bones, arm_obj, power=6.0, rigid=None, radius_falloff=None):
    """Assign smooth weights to `obj` using inverse distance to bone segments.

    bones: list of bone names considered for this part.
    rigid: if given, all vertices go 100% to this bone.
    """
    arm = arm_obj.data
    for name in bones + ([rigid] if rigid else []):
        if name and name not in obj.vertex_groups:
            obj.vertex_groups.new(name=name)
    if rigid:
        vg = obj.vertex_groups[rigid]
        vg.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
        return
    segs = []
    for name in bones:
        b = arm.bones[name]
        segs.append((name, arm_obj.matrix_world @ b.head_local, arm_obj.matrix_world @ b.tail_local))
    mw = obj.matrix_world
    for v in obj.data.vertices:
        p = mw @ v.co
        ws = []
        for name, h, t in segs:
            ht = t - h
            l2 = max(ht.length_squared, 1e-8)
            u = max(0.0, min(1.0, (p - h).dot(ht) / l2))
            d = (p - (h + ht * u)).length
            ws.append(1.0 / max(d, 1e-3) ** power)
        total = sum(ws)
        for (name, _, _), w in zip(segs, ws):
            w /= total
            if w > 0.01:
                obj.vertex_groups[name].add([v.index], w, "REPLACE")


# ---------------------------------------------------------------------------
# Animation helpers (Blender 4.4+ layered actions)
# ---------------------------------------------------------------------------

def action_fcurves(action, owner=None):
    """Return the F-Curves of an action across the legacy/layered APIs."""
    if hasattr(action, "layers") and len(action.layers):
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot) if hasattr(strip, "channelbag") else None
                    if bag:
                        curves.extend(bag.fcurves)
        return curves
    return list(getattr(action, "fcurves", []))


def set_interpolation(action, frames_to_mode, default="BEZIER"):
    """frames_to_mode: {frame: 'CONSTANT'|'LINEAR'|'BEZIER'} for the key that
    starts at that frame."""
    for fc in action_fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = frames_to_mode.get(int(round(kp.co.x)), default)
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_fbx(path, objects, animated=False, actions_all=True, static=False, colors_type="LINEAR"):
    """Unified export: axis_forward=Z, axis_up=Y.

    Blender (x, y, z) lands in Unity as (x, z, y) with no mirroring, so the
    Blender front view (looking +Y) equals the Unity game camera (looking +Z).
    static=True bakes the axis conversion into vertex data (identity object
    transforms in Unity); keep it False for armatures.
    """
    path = Path(path)
    ensure_dir(path.parent)
    deselect_all()
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="Z",
        axis_up="Y",
        bake_space_transform=static,
        object_types={"ARMATURE", "MESH", "EMPTY"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        colors_type=colors_type,
        use_tspace=True,
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        use_armature_deform_only=False,
        armature_nodetype="NULL",
        bake_anim=animated,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=actions_all,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="STRIP",
        embed_textures=False,
    )
    print(f"[dc] exported {path}")
    return path
