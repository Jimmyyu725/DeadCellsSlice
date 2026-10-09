"""Arsenal kit: Cleaver, Spear, Dagger, Bow, Arrow, FireGrenade, IceGrenade,
Harpoon, Flask and Scroll, sharing one 2048 atlas "Arsenal".

Same conventions as build_weapons.py: grip centre at the origin, primary axis
Blender +Z (blade / shaft direction), width along X, thickness along Y.
Blender (x, y, z) == Unity (x, z, y).

This module also hosts the shared "kit" pipeline used by build_props.py:
Asset/Piece builders (one baked object per piece, one temporary bake object per
piece+material), bmesh shape helpers, painted glyph decals, extra material
layers, atlas bake with pairwise high-poly normals, export, manifest, preview
sheets and the fresh-scene re-import check.

Run (headless only, never in the live Blender):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P Tools/Blender/build_arsenal.py
Options after "--":
  --fast          1024 atlas (iteration only; do not ship)
  --build-only    model + EEVEE previews with procedural materials, no bake/export
  --only=A,B      restrict --build-only to these assets
  --verify        fresh scene: re-import every FBX and check bounds, pivots, sockets
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

TAU = math.tau
X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))


def cli_args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def lerp(a, b, t):
    return a + (b - a) * t


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# bmesh shape helpers (all return a fresh bmesh in "asset space")
# ---------------------------------------------------------------------------

def translate(bm, d):
    return eh.translate(bm, Vector(d))


def xform(bm, fn):
    for v in bm.verts:
        v.co = Vector(fn(v.co.copy()))
    bm.normal_update()
    return bm


def aim(bm, direction, origin=(0, 0, 0)):
    """Rotate local +Z onto `direction`, then move to `origin`."""
    q = Z.rotation_difference(Vector(direction).normalized())
    eh.transform(bm, Matrix.Translation(Vector(origin)) @ q.to_matrix().to_4x4())
    return bm


def rot(bm, angle, axis, origin=(0, 0, 0)):
    return eh.rotate(bm, angle, axis, origin)


def box(lo, hi, bev=0.0, segs=1):
    bm = eh.bm_box(lo, hi)
    if bev > 0:
        eh.bm_bevel(bm, bev, segs, min_angle=20)
    return bm


def cbox(center, size, bev=0.0, segs=1):
    c, s = Vector(center), Vector(size) * 0.5
    return box(c - s, c + s, bev, segs)


def loft(rings, cap0=True, cap1=True, tip0=None, tip1=None, closed=True):
    """Quad strips between consecutive rings (equal point counts)."""
    bm = bmesh.new()
    vr = [[bm.verts.new(Vector(p)) for p in r] for r in rings]
    n = len(rings[0])
    m = n if closed else n - 1
    for k in range(len(vr) - 1):
        for i in range(m):
            j = (i + 1) % n
            try:
                bm.faces.new((vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]))
            except ValueError:
                pass

    def cap(ring, tip, rev):
        if tip is not None:
            t = bm.verts.new(Vector(tip))
            for i in range(m):
                j = (i + 1) % n
                f = (ring[i], ring[j], t)
                try:
                    bm.faces.new(f[::-1] if rev else f)
                except ValueError:
                    pass
        elif n > 2:
            try:
                bm.faces.new(ring[::-1] if rev else ring)
            except ValueError:
                pass

    if tip0 is not None or cap0:
        cap(vr[0], tip0, True)
    if tip1 is not None or cap1:
        cap(vr[-1], tip1, False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lathe(profile, segs=12, center=(0, 0, 0), axis=None, scale_xy=(1.0, 1.0), phase=0.0, cap0=True, cap1=True,
          jitter=0.0, rng=None):
    """Revolve (r, z) around local Z; zero-radius ends become clean tips."""
    prof = list(profile)
    tip0 = tip1 = None
    if prof[0][0] <= 1e-5:
        tip0 = Vector((0, 0, prof[0][1]))
        prof = prof[1:]
    if prof[-1][0] <= 1e-5:
        tip1 = Vector((0, 0, prof[-1][1]))
        prof = prof[:-1]
    rings = []
    for r, z in prof:
        ring = []
        for i in range(segs):
            a = phase + TAU * i / segs
            rr = r * (1.0 + (rng.uniform(-jitter, jitter) if rng and jitter else 0.0))
            ring.append(Vector((math.cos(a) * rr * scale_xy[0], math.sin(a) * rr * scale_xy[1], z)))
        rings.append(ring)
    bm = loft(rings, cap0=cap0 and tip0 is None, cap1=cap1 and tip1 is None, tip0=tip0, tip1=tip1)
    if axis is not None:
        aim(bm, axis)
    return translate(bm, center)


def ridged(z0, z1, r_lo, r_hi, n, end_r=None):
    """Lathe profile for wraps/bindings: alternating radii between z0 and z1."""
    prof = [(end_r or r_lo * 0.92, z0)]
    for k in range(n + 1):
        prof.append((r_hi if k % 2 == 0 else r_lo, lerp(z0, z1, (k + 0.5) / (n + 1))))
    prof.append((end_r or r_lo * 0.92, z1))
    return prof


def cone(base, direction, length, radius, segs=6, tip_r=0.0):
    bm = lathe([(radius, 0.0), (max(tip_r, 0.0), length)], segs=segs)
    return aim(bm, direction, base)


def tube(points, radii, segs=6, up=None, flatten=1.0, cap=True, closed=False):
    return eh.bm_tube([Vector(p) for p in points], radii, segs=segs, up=up, flatten=flatten, cap=cap, closed=closed)


def torus(center, R, r, normal=(0, 0, 1), seg=16, rseg=6, flatten=1.0, phase=0.0):
    pts = [Vector((math.cos(phase + TAU * i / seg) * R, math.sin(phase + TAU * i / seg) * R, 0)) for i in range(seg)]
    bm = eh.bm_tube(pts, r, segs=rseg, closed=True, flatten=flatten, up=Z)
    return aim(bm, normal, center)


def blob(center, radius, scale=(1, 1, 1), segs=8, rings=6, rng=None, jitter=0.0):
    return eh.bm_blob(center, radius, scale=scale, segs=segs, rings=rings, rng=rng, jitter=jitter)


def catmull(points, n=4, closed=False):
    """Catmull-Rom resample of control points (n samples per span)."""
    P = [Vector(p) for p in points]
    out = []
    cnt = len(P)
    spans = cnt if closed else cnt - 1
    for i in range(spans):
        p0 = P[(i - 1) % cnt] if closed or i > 0 else P[0]
        p1 = P[i]
        p2 = P[(i + 1) % cnt]
        p3 = P[(i + 2) % cnt] if closed or i + 2 < cnt else P[-1]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1].copy())
    return out


def frames(path, side_hint=None):
    """Parallel-transport frames (p, tangent, side, normal); side starts on
    side_hint projected off the tangent, normal = tangent x side."""
    pts = [Vector(p) for p in path]
    n = len(pts)
    tans = []
    for k in range(n):
        if k == 0:
            t = pts[1] - pts[0]
        elif k == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[k + 1] - pts[k - 1]
        tans.append(t.normalized())
    h = Vector(side_hint) if side_hint is not None else (X if abs(tans[0].dot(X)) < 0.9 else Z)
    side = (h - tans[0] * h.dot(tans[0])).normalized()
    out = []
    for k in range(n):
        t = tans[k]
        if k:
            side = side - t * side.dot(t)
            if side.length < 1e-6:
                side = t.cross(Y)
            side.normalize()
        out.append((pts[k], t, side, t.cross(side).normalized()))
    return out


def sweep(path, profile, side_hint=None, cap0=True, cap1=True, tip0=None, tip1=None):
    """profile: list of (a, b) or callable(k, frame) -> list; a along side, b along normal."""
    fr = frames(path, side_hint)
    rings = []
    for k, f in enumerate(fr):
        p, t, s, nn = f
        prof = profile(k, f) if callable(profile) else profile
        rings.append([p + s * a + nn * b for a, b in prof])
    return loft(rings, cap0=cap0, cap1=cap1, tip0=tip0, tip1=tip1)


def ellipse_prof(a, b, n=8, phase=0.0):
    return [(math.cos(phase + TAU * i / n) * a, math.sin(phase + TAU * i / n) * b) for i in range(n)]


def thick_sheet(grid, th, normal_hint=(0, -1, 0)):
    """Closed thin slab around a point grid (rows x cols) -- cloth, paper."""
    R, C = len(grid), len(grid[0])
    P = [[Vector(p) for p in row] for row in grid]
    hint = Vector(normal_hint)
    N = []
    for r in range(R):
        row = []
        for c in range(C):
            du = P[r][min(c + 1, C - 1)] - P[r][max(c - 1, 0)]
            dv = P[min(r + 1, R - 1)][c] - P[max(r - 1, 0)][c]
            nn = du.cross(dv)
            if nn.length < 1e-9:
                nn = hint.copy()
            nn.normalize()
            if nn.dot(hint) < 0:
                nn = -nn
            row.append(nn)
        N.append(row)
    bm = bmesh.new()
    F = [[bm.verts.new(P[r][c] + N[r][c] * th * 0.5) for c in range(C)] for r in range(R)]
    B = [[bm.verts.new(P[r][c] - N[r][c] * th * 0.5) for c in range(C)] for r in range(R)]
    for r in range(R - 1):
        for c in range(C - 1):
            bm.faces.new((F[r][c], F[r][c + 1], F[r + 1][c + 1], F[r + 1][c]))
            bm.faces.new((B[r][c], B[r + 1][c], B[r + 1][c + 1], B[r][c + 1]))
    ring = [(0, c) for c in range(C)] + [(r, C - 1) for r in range(1, R)] + \
           [(R - 1, c) for c in range(C - 2, -1, -1)] + [(r, 0) for r in range(R - 2, 0, -1)]
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        try:
            bm.faces.new((F[a[0]][a[1]], B[a[0]][a[1]], B[b[0]][b[1]], F[b[0]][b[1]]))
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def prism_xz(poly, y0, y1):
    """Extrude an x-z polygon (concave allowed) along +Y."""
    rings = [[Vector((x, y0, z)) for x, z in poly], [Vector((x, y1, z)) for x, z in poly]]
    return loft(rings)


def bm_boolean(bm, cutter, op="DIFFERENCE"):
    """Exact boolean of two bmeshes (both consumed)."""
    me = bpy.data.meshes.new("_bool_a")
    bm.to_mesh(me)
    bm.free()
    a = dc.link(bpy.data.objects.new("_bool_a", me))
    mc = bpy.data.meshes.new("_bool_b")
    cutter.to_mesh(mc)
    cutter.free()
    b = dc.link(bpy.data.objects.new("_bool_b", mc))
    mod = a.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.object = b
    try:
        mod.solver = "EXACT"
    except TypeError:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    out = bmesh.new()
    out.from_object(a, dg)
    bpy.data.objects.remove(a, do_unlink=True)
    bpy.data.objects.remove(b, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(mc)
    out.normal_update()
    return out


def jitter_bm(bm, amount, rng, axes=(1, 1, 1)):
    for v in bm.verts:
        v.co += Vector((rng.uniform(-1, 1) * axes[0], rng.uniform(-1, 1) * axes[1], rng.uniform(-1, 1) * axes[2])) * amount
    bm.normal_update()
    return bm


# ---------------------------------------------------------------------------
# Painted glyph masks (numpy rasterised strokes -> PNG -> image texture)
# ---------------------------------------------------------------------------

RUNES = [
    [[(0.3, 0.0), (0.3, 1.0)], [(0.3, 0.72), (0.78, 1.0)], [(0.3, 0.42), (0.78, 0.7)]],
    [[(0.28, 0.0), (0.28, 1.0), (0.72, 0.72), (0.72, 0.0)]],
    [[(0.3, 0.0), (0.3, 1.0)], [(0.3, 0.78), (0.72, 0.5), (0.3, 0.22)]],
    [[(0.72, 1.0), (0.28, 0.5), (0.72, 0.0)]],
    [[(0.18, 0.0), (0.82, 1.0)], [(0.18, 1.0), (0.82, 0.0)]],
    [[(0.28, 0.0), (0.28, 1.0)], [(0.72, 0.0), (0.72, 1.0)], [(0.28, 0.66), (0.72, 0.34)]],
    [[(0.5, 0.0), (0.5, 1.0)], [(0.22, 0.68), (0.78, 0.38)]],
    [[(0.5, 0.0), (0.5, 1.0)], [(0.18, 0.66), (0.5, 1.0), (0.82, 0.66)]],
    [[(0.5, 0.0), (0.5, 1.0)], [(0.14, 0.95), (0.5, 0.55), (0.86, 0.95)]],
    [[(0.74, 1.0), (0.26, 0.66), (0.74, 0.34), (0.26, 0.0)]],
    [[(0.18, 0.0), (0.5, 0.42), (0.82, 0.0)], [(0.5, 0.42), (0.15, 0.72), (0.5, 1.0), (0.85, 0.72), (0.5, 0.42)]],
    [[(0.18, 0.0), (0.18, 1.0), (0.82, 0.0), (0.82, 1.0), (0.18, 0.0)]],
    [[(0.3, 0.0), (0.3, 1.0), (0.74, 0.74), (0.3, 0.46)]],
    [[(0.5, 0.0), (0.5, 1.0)], [(0.2, 0.25), (0.5, 0.5), (0.8, 0.25)], [(0.2, 0.75), (0.5, 0.5)]],
]


def rune_strokes(rng, x, y, w, h, width, value=1.0, wobble=0.06):
    """One random rune fitted to the cell (x, y, w, h); jittered like a scratch."""
    out = []
    for line in rng.choice(RUNES):
        pts = [(x + (px + rng.uniform(-wobble, wobble)) * w, y + (py + rng.uniform(-wobble, wobble)) * h)
               for px, py in line]
        out.append(dict(pts=pts, w=width * rng.uniform(0.8, 1.15), v=value))
    return out


def arc_pts(cx, cy, r, a0, a1, n=24):
    return [(cx + math.cos(lerp(a0, a1, i / n)) * r, cy + math.sin(lerp(a0, a1, i / n)) * r) for i in range(n + 1)]


def glyph_image(name, rect_w, rect_h, strokes, out_dir, max_px=1024, soft=1.2):
    """Rasterise strokes (metres from the rect's lower-left) into a mask PNG.
    Returns the loaded (Non-Color) image."""
    import numpy as np
    ppm = max_px / max(rect_w, rect_h)
    W, H = max(8, int(math.ceil(rect_w * ppm))), max(8, int(math.ceil(rect_h * ppm)))
    acc = np.zeros((H, W), dtype=np.float32)
    for s in strokes:
        pts = s["pts"]
        hw = s.get("w", 0.002) * 0.5
        val = s.get("v", 1.0)
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            pad = hw + 3.0 / ppm
            c0 = max(int((min(x0, x1) - pad) * ppm), 0)
            c1 = min(int((max(x0, x1) + pad) * ppm) + 1, W)
            r0 = max(int((min(y0, y1) - pad) * ppm), 0)
            r1 = min(int((max(y0, y1) + pad) * ppm) + 1, H)
            if c1 <= c0 or r1 <= r0:
                continue
            ys, xs = np.mgrid[r0:r1, c0:c1].astype(np.float32)
            px, py = (xs + 0.5) / ppm, (ys + 0.5) / ppm
            dx, dy = x1 - x0, y1 - y0
            l2 = dx * dx + dy * dy or 1e-12
            t = np.clip(((px - x0) * dx + (py - y0) * dy) / l2, 0.0, 1.0)
            d = np.hypot(px - (x0 + t * dx), py - (y0 + t * dy))
            a = np.clip((hw - d) * ppm / soft + 0.5, 0.0, 1.0) * val
            acc[r0:r1, c0:c1] = np.maximum(acc[r0:r1, c0:c1], a)
    rgba = np.ones((H, W, 4), dtype=np.float32)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = acc
    out_dir = dc.ensure_dir(out_dir)
    path = Path(out_dir) / f"{name}.png"
    img = bpy.data.images.new(name + "_tmp", W, H, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    loaded = bpy.data.images.load(str(path), check_existing=False)
    loaded.name = name
    loaded.colorspace_settings.name = "Non-Color"
    return loaded


# ---------------------------------------------------------------------------
# Material layering on top of dc.make_material
# ---------------------------------------------------------------------------

class MatEdit:
    """Re-route the DC_* bake taps through extra painterly layers."""

    def __init__(self, mat):
        self.mat = mat
        self.nt = nt = mat.node_tree
        self._x = -2600
        tc = dc.new_node(nt, "ShaderNodeTexCoord", (-3200, 600))
        self.coord = dc._sock(tc.outputs, "Object")
        self.sep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-3000, 600))
        nt.links.new(self.coord, dc._sock(self.sep.inputs, "Vector"))
        geo = dc.new_node(nt, "ShaderNodeNewGeometry", (-3200, 200))
        self.normal = dc._sock(geo.outputs, "Normal")
        self.nsep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-3000, 200))
        nt.links.new(self.normal, dc._sock(self.nsep.inputs, "Vector"))
        self.bsdf = dc.principled(nt)
        self.emit_fac = None

    def _loc(self):
        self._x += 7
        return (self._x, 900 + (self._x % 400))

    def axis(self, a):
        return dc._sock(self.sep.outputs, a.upper())

    def naxis(self, a):
        return dc._sock(self.nsep.outputs, a.upper())

    @property
    def x(self):
        return self.axis("X")

    @property
    def y(self):
        return self.axis("Y")

    @property
    def z(self):
        return self.axis("Z")

    def m(self, op, a, b=0.0, c=None, clamp=False):
        n = dc.new_node(self.nt, "ShaderNodeMath", self._loc())
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    def rng(self, v, a, b, c=0.0, d=1.0, smooth=False):
        n = dc.new_node(self.nt, "ShaderNodeMapRange", self._loc())
        if smooth:
            n.interpolation_type = "SMOOTHSTEP"
        self.nt.links.new(v, dc._sock(n.inputs, "Value"))
        dc._sock(n.inputs, "From Min").default_value = a
        dc._sock(n.inputs, "From Max").default_value = b
        dc._sock(n.inputs, "To Min").default_value = c
        dc._sock(n.inputs, "To Max").default_value = d
        n.clamp = True
        return dc._sock(n.outputs, "Result")

    def vlen(self, v):
        n = dc.new_node(self.nt, "ShaderNodeVectorMath", self._loc())
        n.operation = "LENGTH"
        self.nt.links.new(v, n.inputs[0])
        return n.outputs["Value"]

    def vec(self, x, y, z=0.0):
        n = dc.new_node(self.nt, "ShaderNodeCombineXYZ", self._loc())
        for name, v in (("X", x), ("Y", y), ("Z", z)):
            s = dc._sock(n.inputs, name)
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, s)
            else:
                s.default_value = v
        return n.outputs[0]

    def noise(self, scale, detail=3.0, rough=0.55, coord=None, distortion=0.0, dims="3D", stretch=None):
        n = dc.new_node(self.nt, "ShaderNodeTexNoise", self._loc())
        try:
            n.noise_dimensions = dims
        except (TypeError, AttributeError):
            pass
        dc._sock(n.inputs, "Scale").default_value = scale
        dc._sock(n.inputs, "Detail").default_value = detail
        dc._sock(n.inputs, "Roughness").default_value = rough
        dc._sock(n.inputs, "Distortion").default_value = distortion
        c = coord or self.coord
        if stretch is not None:
            mp = dc.new_node(self.nt, "ShaderNodeMapping", self._loc())
            dc._sock(mp.inputs, "Scale").default_value = stretch
            self.nt.links.new(c, dc._sock(mp.inputs, "Vector"))
            c = dc._sock(mp.outputs, "Vector")
        self.nt.links.new(c, dc._sock(n.inputs, "Vector"))
        return dc._sock(n.outputs, "Fac")

    def voronoi(self, scale, coord=None, feature="F1", out="Distance"):
        n = dc.new_node(self.nt, "ShaderNodeTexVoronoi", self._loc())
        n.feature = feature
        dc._sock(n.inputs, "Scale").default_value = scale
        self.nt.links.new(coord or self.coord, dc._sock(n.inputs, "Vector"))
        return dc._sock(n.outputs, out)

    def ramp(self, fac, stops):
        r = dc.ramp(self.nt, [(p, dc.hex_rgba(h) if isinstance(h, str) else h) for p, h in stops], loc=self._loc())
        self.nt.links.new(fac, dc._sock(r.inputs, "Fac"))
        return dc._sock(r.outputs, "Color")

    def _src(self, tag):
        lk = self.nt.nodes[tag].inputs[0].links
        return lk[0].from_socket if lk else None

    def _set(self, tag, sock):
        node = self.nt.nodes[tag]
        for lk in list(node.inputs[0].links):
            self.nt.links.remove(lk)
        self.nt.links.new(sock, node.inputs[0])

    def albedo(self, col, fac=1.0, blend="MIX"):
        c = dc.hex_rgba(col) if isinstance(col, str) else col
        _, out = dc.mix_rgb(self.nt, self._src("DC_ALBEDO"), c, fac, blend=blend, loc=self._loc())
        self._set("DC_ALBEDO", out)

    def _fmix(self, tag, val, fac):
        n = dc.new_node(self.nt, "ShaderNodeMix", self._loc())
        n.data_type = "FLOAT"
        n.clamp_factor = True
        for name, v in (("Factor_Float", fac), ("A_Float", self._src(tag)), ("B_Float", val)):
            s = dc._sock(n.inputs, name)
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, s)
            else:
                s.default_value = v
        self._set(tag, dc._sock(n.outputs, "Result_Float"))

    def rough(self, val, fac=1.0):
        self._fmix("DC_ROUGH", val, fac)

    def metal(self, val, fac=1.0):
        self._fmix("DC_METAL", val, fac)

    def const(self, v):
        n = dc.new_node(self.nt, "ShaderNodeValue", self._loc())
        n.outputs[0].default_value = v
        return n.outputs[0]

    def emit(self, fac):
        """Greyscale emission mask (white = glow; Unity applies the HDR tint)."""
        if not isinstance(fac, bpy.types.NodeSocket):
            fac = self.const(fac)
        self.emit_fac = fac if self.emit_fac is None else self.m("MAXIMUM", self.emit_fac, fac)
        cc = dc.new_node(self.nt, "ShaderNodeCombineColor", self._loc())
        for ch in ("Red", "Green", "Blue"):
            self.nt.links.new(self.emit_fac, dc._sock(cc.inputs, ch))
        self._set("DC_EMIT", dc._sock(cc.outputs, "Color"))
        self.nt.links.new(self.nt.nodes["DC_EMIT"].outputs[0], dc._sock(self.bsdf.inputs, "Emission Color"))
        dc._sock(self.bsdf.inputs, "Emission Strength").default_value = 3.0

    def bump(self, height, amount):
        bump = next(n for n in self.nt.nodes if n.type == "BUMP")
        hin = dc._sock(bump.inputs, "Height")
        prev = hin.links[0].from_socket if hin.links else None
        add = self.m("MULTIPLY_ADD", height, amount, prev if prev is not None else 0.0)
        self.nt.links.new(add, hin)

    def facing(self, axis, lo=0.35, hi=0.6):
        return self.rng(self.m("ABSOLUTE", self.naxis(axis)), lo, hi)

    def decal(self, img, rect, u="X", v="Z", face=None, face_lo=0.35, face_hi=0.6):
        """Planar projection of a glyph mask over rect=(u0, v0, w, h) metres."""
        u0, v0, w, h = rect
        uu = self.m("MULTIPLY_ADD", self.axis(u), 1.0 / w, -u0 / w)
        vv = self.m("MULTIPLY_ADD", self.axis(v), 1.0 / h, -v0 / h)
        tex = dc.new_node(self.nt, "ShaderNodeTexImage", self._loc())
        tex.image = img
        tex.extension = "CLIP"
        tex.interpolation = "Linear"
        self.nt.links.new(self.vec(uu, vv, 0.0), dc._sock(tex.inputs, "Vector"))
        sepc = dc.new_node(self.nt, "ShaderNodeSeparateColor", self._loc())
        self.nt.links.new(dc._sock(tex.outputs, "Color"), dc._sock(sepc.inputs, "Color"))
        mask = dc._sock(sepc.outputs, "Red")
        if face:
            mask = self.m("MULTIPLY", mask, self.facing(face, face_lo, face_hi))
        return mask


def make_mat(name, base, **kw):
    """dc.make_material without its pointiness-driven edge wear / cavity dirt:
    on low-poly bake targets pointiness is per-vertex and smears across whole
    faces.  Worn edges and cavities come from eh.enhance (bevel node + AO),
    which is evaluated per texel."""
    kw["edge_wear_amt"] = 0.0
    kw["cavity_dirt"] = 0.0
    return dc.make_material(name, base, **kw)


def rust_layer(mat, amt, scale=7.0, hexes=("#4A2412", "#8A4A22", "#B36A2E"), flake=0.12):
    """build_weapons.blade_material's rust approach: noise patches recolour
    albedo, raise roughness and kill metalness; flakes read in the bump."""
    E = MatEdit(mat)
    n = E.noise(scale, detail=6.0, rough=0.65)
    mask = E.rng(n, 0.62 - amt * 0.15, 0.7 - amt * 0.15)
    E.albedo(E.ramp(n, [(0.0, hexes[0]), (0.5, hexes[1]), (1.0, hexes[2])]), mask)
    E.rough(0.92, mask)
    E.metal(0.0, mask)
    E.bump(mask, flake)
    return E


def iron_mat(name, rust=0.35, edge_r=0.005, base="#4D555E", scale=1.0, metal=0.6, edge=("#D0D8DE", 0.9)):
    m = make_mat(name, base, dark="#262B31", light="#7E8892", metal=metal, rough=0.48, noise_scale=8.0 / scale,
                         noise_amt=0.5, edge_wear="#D8E0E6", edge_wear_amt=1.0, cavity_dirt=0.9,
                         bump_scale=40.0 / scale, bump_strength=0.12, bevel_radius=0.004 * scale)
    if rust:
        rust_layer(m, rust, scale=6.0 / scale)
    eh.enhance(m, edge_hex=edge[0], edge_amt=edge[1], edge_radius=edge_r, top_hex="#A3AEB8", top_amt=0.18,
               cavity_amt=0.6, cavity_dist=edge_r * 8)
    return m


def brass_mat(name, edge_r=0.005, patina=0.25, scale=1.0):
    m = make_mat(name, "#A8803A", dark="#5A4018", light="#E0BC6A", metal=0.7, rough=0.4,
                         noise_scale=7.0 / scale, noise_amt=0.45, edge_wear="#FBE6A8", edge_wear_amt=1.0,
                         cavity_dirt=0.8, bump_scale=40.0 / scale, bump_strength=0.1, bevel_radius=0.004 * scale)
    eh.enhance(m, blotch=("#2F6B58", 6.0 / scale, patina) if patina else None, edge_hex="#FFF0C0", edge_amt=1.0,
               edge_radius=edge_r, top_hex="#F2D488", top_amt=0.22, cavity_amt=0.7, cavity_dist=edge_r * 8,
               cavity_hex="#1E2A20")
    return m


def wood_mat(name, base, dark, light, grain=0.08, edge_r=0.006, stripes=None, rough=0.78, axis="z", scale=1.0):
    m = make_mat(name, base, dark=dark, light=light, rough=rough, noise_scale=5.0 / scale, noise_amt=0.9,
                         edge_wear=light, edge_wear_amt=0.6, cavity_dirt=0.8, bump_scale=40 / scale,
                         bump_strength=0.3, bevel_radius=0.004 * scale, stripes=stripes)
    st = (grain, 1.0, 1.0) if axis == "x" else (1.0, 1.0, grain)
    eh.stretch_coords(m, st)
    E = MatEdit(m)
    g = E.noise(60.0 / scale, 2.0, 0.5, stretch=tuple(c * 0.5 if c != 1.0 else 1.0 for c in st))
    E.albedo(dark, E.rng(g, 0.6, 0.72, 0.0, 0.55))
    E.bump(E.rng(g, 0.55, 0.75), -0.25)
    eh.enhance(m, edge_hex=light, edge_amt=0.7, edge_radius=edge_r, top_hex=light, top_amt=0.2, cavity_amt=0.6,
               cavity_dist=edge_r * 8)
    return m


def cloth_mat(name, base, dark, light, stripes=None, edge_r=0.004, weave=200.0):
    m = make_mat(name, base, dark=dark, light=light, rough=0.92, rough_var=0.05, noise_scale=7.0,
                         noise_amt=0.8, cavity_dirt=0.5, bump_scale=weave, bump_strength=0.18, bevel_radius=0.003,
                         stripes=stripes)
    eh.enhance(m, edge_hex=light, edge_amt=0.45, edge_radius=edge_r, top_hex=light, top_amt=0.2, bottom_amt=0.25,
               cavity_amt=0.5, cavity_dist=edge_r * 8)
    return m


def leather_mat(name, base="#4A2E1C", dark="#1C0F08", light="#7A5236", stripes=None, edge_r=0.003):
    m = make_mat(name, base, dark=dark, light=light, rough=0.68, noise_scale=9.0, noise_amt=0.8,
                         edge_wear=light, edge_wear_amt=0.8, cavity_dirt=0.7, bump_scale=110, bump_strength=0.2,
                         bevel_radius=0.003, stripes=stripes)
    eh.enhance(m, edge_hex=light, edge_amt=0.6, edge_radius=edge_r, top_hex=light, top_amt=0.15, cavity_amt=0.5,
               cavity_dist=edge_r * 8)
    return m


def bone_mat(name, edge_r=0.004, scale=1.0):
    m = make_mat(name, "#D6CBAA", dark="#9A8C6A", light="#F3ECD6", rough=0.6, noise_scale=6.0 / scale,
                         noise_amt=0.5, edge_wear="#FFF8E8", edge_wear_amt=0.6, cavity_dirt=0.9, bump_scale=70,
                         bump_strength=0.18, bevel_radius=0.003)
    E = MatEdit(m)
    crack = E.noise(30.0 / scale, 4.0, 0.6, stretch=(1.0, 1.0, 0.35))
    E.albedo("#5E5238", E.rng(E.m("ABSOLUTE", E.m("SUBTRACT", crack, 0.5)), 0.012, 0.0, 0.0, 0.7))
    eh.enhance(m, edge_hex="#FFF6E0", edge_amt=0.7, edge_radius=edge_r, top_hex="#FFF6E0", top_amt=0.18,
               cavity_amt=0.8, cavity_dist=edge_r * 8, cavity_hex="#3A2E1C")
    return m


def glass_material(name, liquid, level, wobble=0.004, frost=False, glass=("#2C3C44", "#121A22", "#557078"),
                   highlight_dir=(-0.55, -0.55, 0.65), depth=0.12):
    """Opaque stylised glass: liquid below `level` (object z) is painted
    bright and goes white in the emission mask; above it smoky glass with a
    painted specular streak."""
    deep, mid, top, bubble = liquid
    m = make_mat(name, glass[0], dark=glass[1], light=glass[2], rough=0.1, rough_var=0.04,
                         noise_scale=9.0, noise_amt=0.6, bump_scale=30, bump_strength=0.04, bevel_radius=0.002)
    E = MatEdit(m)
    wob = E.m("MULTIPLY", E.m("SUBTRACT", E.noise(18.0, 2.0, 0.5), 0.5), wobble)
    zl = E.m("SUBTRACT", E.m("SUBTRACT", E.z, level), wob)
    liq = E.rng(zl, 0.0012, -0.0012)
    dep = E.rng(E.z, level, level - depth)
    col = E.ramp(dep, [(0.0, top), (0.22, mid), (1.0, deep)])
    bub = E.m("MULTIPLY", E.rng(E.voronoi(70.0), 0.12, 0.05), E.rng(E.noise(9.0), 0.45, 0.6))
    _, col = dc.mix_rgb(E.nt, col, dc.hex_rgba(bubble), bub, loc=E._loc())
    E.albedo(col, liq)
    men = E.m("MULTIPLY", E.rng(E.m("ABSOLUTE", zl), 0.0035, 0.0012), liq)
    E.albedo(bubble, E.m("MULTIPLY", men, 0.7))
    E.rough(0.2, liq)
    E.emit(E.m("MULTIPLY", liq, E.m("ADD", E.m("MULTIPLY", bub, 0.25), 0.75)))
    if frost:
        fr = E.rng(E.noise(26.0, 5.0, 0.7), 0.5, 0.62)
        fr = E.m("MULTIPLY", fr, E.m("SUBTRACT", 1.0, liq, clamp=True))
        E.albedo("#DDF6FF", E.m("MULTIPLY", fr, 0.85))
        E.rough(0.65, fr)
        E.bump(fr, 0.3)
    # Painted specular streak + rim darkening (hand-painted glass read).
    L = Vector(highlight_dir).normalized()
    dot = dc.new_node(E.nt, "ShaderNodeVectorMath", E._loc())
    dot.operation = "DOT_PRODUCT"
    E.nt.links.new(E.normal, dot.inputs[0])
    dot.inputs[1].default_value = L
    d = dot.outputs["Value"]
    hl = E.m("SUBTRACT", E.rng(d, 0.8, 0.86), E.rng(d, 0.93, 0.965), clamp=True)
    hl = E.m("MAXIMUM", hl, E.rng(d, 0.975, 0.99))
    E.albedo("#F4FBFF", E.m("MULTIPLY", hl, 0.85))
    rim = E.rng(E.naxis("Z"), -0.3, -0.95, 0.0, 0.45)
    E.albedo("#05080C", rim)
    return m, E


# ---------------------------------------------------------------------------
# Asset / Piece builders
# ---------------------------------------------------------------------------

FLIPPED = []


def make_outward(bm, label=""):
    """Closed primitives must have outward normals (positive signed volume)."""
    bm.normal_update()
    if bm.faces and all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) < 0.0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.normal_update()
        FLIPPED.append(label)
    return bm


class Piece:
    """One exported mesh object: per-material bmeshes in asset space."""

    def __init__(self, name, pivot=(0, 0, 0)):
        self.name = name
        self.pivot = Vector(pivot)
        self.parts = {}
        self.objs = []
        self.obj = None

    def add(self, mat, *bms):
        dst = self.parts.setdefault(mat, bmesh.new())
        for b in bms:
            if isinstance(b, (list, tuple)):
                self.add(mat, *b)
                continue
            make_outward(b, f"{self.name}/{mat}")
            eh.bm_append(dst, b)
            b.free()
        return self


class Asset:
    def __init__(self, name, usage="", weight=1.0, tint="#FFFFFF", floor=False):
        self.name = name
        self.floor = floor
        self.usage = usage
        self.weight = weight
        self.tint = tint
        self.pieces = []
        self.sockets = {}
        self.empties = []

    def piece(self, name=None, pivot=(0, 0, 0)):
        p = Piece(name or self.name, pivot)
        self.pieces.append(p)
        return p

    def socket(self, name, pos):
        self.sockets[name] = Vector(pos)

    @property
    def objs(self):
        out = []
        for p in self.pieces:
            out.extend([p.obj] if p.obj else p.objs)
        return out


def realize(assets, M, flat=(), mat_weight=None):
    """Turn every piece+material bmesh into a mesh object (asset origin at the
    world origin so Object-space procedural textures are stable)."""
    mat_weight = mat_weight or {}
    weights = {}
    for a in assets:
        for p in a.pieces:
            p.objs = []
            for mk, bm in p.parts.items():
                if a.floor:
                    for v in bm.verts:
                        if v.co.z < 0.0:
                            v.co.z = 0.0
                ng = [f for f in bm.faces if len(f.verts) > 4]
                if ng:
                    bmesh.ops.triangulate(bm, faces=ng, quad_method="BEAUTY", ngon_method="EAR_CLIP")
                bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-12], context="FACES")
                me = bpy.data.meshes.new(f"{p.name}__{mk}")
                bm.to_mesh(me)
                bm.free()
                me.materials.append(M[mk])
                me.polygons.foreach_set("use_smooth", [mk not in flat] * len(me.polygons))
                o = dc.link(bpy.data.objects.new(me.name, me))
                o["dc_mat"] = mk
                p.objs.append(o)
                weights[o.name] = a.weight * mat_weight.get(mk, 1.0)
            p.parts = {}
    return weights


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def spread(assets, gap=0.6):
    """Lay assets out along +X so AO from one never darkens another."""
    x = 0.0
    for a in assets:
        lo, hi = bounds_of(a.objs)
        for o in a.objs:
            o.location = (x - lo.x, 0.0, 0.0)
        x += (hi.x - lo.x) + gap


def bounds_of(objs, world=False):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for v in o.data.vertices:
            w = (o.matrix_world @ v.co) if world else v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def to_unity(v):
    return [round(v[0], 4), round(v[2], 4), round(v[1], 4)]


def bake_kit(assets, weights, out_tex, prefix, size, hp_cfg, default_hp=(0.002, 1), margin=0.003):
    t0 = time.time()
    objs = [o for a in assets for o in a.objs]
    spread(assets)
    dc.uv_atlas_multi(objs, island_margin=margin, importance=weights)
    print(f"[kit] {prefix}: UV atlas for {len(objs)} bake objects in {time.time() - t0:.1f}s")
    pairs = []
    for o in objs:
        bw, ss = hp_cfg.get(o["dc_mat"], default_hp)
        hp = dc.make_highpoly(o, bevel_width=bw, subsurf=ss)
        hp.location = o.location
        pairs.append((o, hp))
    t1 = time.time()
    paths = dc.bake_texture_set(objs, out_tex, prefix, size=size, highpoly=pairs)
    print(f"[kit] {prefix}: baked {size}px in {time.time() - t1:.1f}s")
    for _, h in pairs:
        bpy.data.objects.remove(h, do_unlink=True)
    return paths


def assemble(assets, baked):
    """Join each piece's bake objects, assign the atlas material, set pivots
    and create socket empties.  Returns nothing; sets piece.obj."""
    for a in assets:
        for p in a.pieces:
            for o in p.objs:
                o.location = (0, 0, 0)
            if len(p.objs) == 1:
                obj = p.objs[0]
                obj.name = p.name
                obj.data.name = p.name
            else:
                obj = dc.join(p.objs, p.name)
            obj.data.materials.clear()
            obj.data.materials.append(baked)
            for poly in obj.data.polygons:
                poly.material_index = 0
            obj.data.transform(Matrix.Translation(-p.pivot))
            obj.location = p.pivot
            p.obj = obj
            p.objs = [obj]
        main = a.pieces[0].obj
        a.empties = []
        for sname, pos in a.sockets.items():
            e = bpy.data.objects.new(sname, None)
            e.empty_display_type = "ARROWS"
            e.empty_display_size = 0.1
            dc.link(e)
            e.parent = main
            e.location = pos - a.pieces[0].pivot
            a.empties.append(e)
        bpy.context.view_layer.update()


def export_assets(assets, fbx_dir, atlas, manifest, budget):
    for a in assets:
        meshes = [p.obj for p in a.pieces]
        path = Path(fbx_dir) / f"{a.name}.fbx"
        dc.export_fbx(path, meshes + a.empties, static=True)
        lo, hi = bounds_of(meshes, world=True)
        tris = sum(tri_count(o) for o in meshes)
        entry = dict(name=a.name, fbx=str(path.relative_to(dc.PROJECT_ROOT)), atlas=atlas,
                     unity_bounds_min=to_unity(lo), unity_bounds_max=to_unity(hi),
                     sockets={e.name: to_unity(e.matrix_world.translation) for e in a.empties},
                     tris=tris, usage=a.usage)
        if len(meshes) > 1:
            parts = {}
            for p in a.pieces:
                plo, phi = bounds_of([p.obj], world=True)
                parts[p.name] = dict(pivot=to_unity(p.pivot), unity_bounds_min=to_unity(plo),
                                     unity_bounds_max=to_unity(phi), tris=tri_count(p.obj))
            entry["pieces"] = parts
        manifest["modules"].append(entry)
        flag = "" if tris <= budget(a) else f"  OVER BUDGET ({budget(a)})"
        print(f"[kit] {a.name:14s} tris={tris}{flag}")


def tinted_preview_material(baked, tint):
    m = baked.copy()
    m.name = baked.name + "_preview"
    nt = m.node_tree
    bsdf = dc.principled(nt)
    sock = dc._sock(bsdf.inputs, "Emission Color")
    if sock.links:
        src = sock.links[0].from_socket
        _, out = dc.mix_rgb(nt, src, dc.hex_rgba(tint), 1.0, blend="MULTIPLY", loc=(-300, -700))
        nt.links.new(out, sock)
    return m


def preview_assets(assets, out_dir, tag, views=("three_quarter",), res=512, cols=5, baked=None):
    out_dir = dc.ensure_dir(out_dir)
    sheets = {v: [] for v in views}
    every = [o for o in bpy.context.scene.objects]
    hidden = {o: o.hide_render for o in every}
    for o in every:
        o.hide_render = True
    for a in assets:
        objs = a.objs
        saved = []
        if baked is not None:
            pm = tinted_preview_material(baked, a.tint)
            for o in objs:
                saved.append((o, o.data.materials[0]))
                o.data.materials[0] = pm
        for o in objs:
            o.hide_render = False
        for v in views:
            sheets[v] += dc.preview_render(str(out_dir / f"{a.name}"), objs, views=(v,), res=res)
        for o in objs:
            o.hide_render = True
        for o, mat in saved:
            o.data.materials[0] = mat
    for o, h in hidden.items():
        o.hide_render = h
    out = []
    for v in views:
        out.append(eh.compose_sheet(sheets[v], Path(out_dir) / f"sheet_{tag}_{v}.png",
                                    cols=min(cols, len(sheets[v])), cell=res))
    print(f"[kit] preview sheets {out}  order: {[a.name for a in assets]}")
    return out


def run_kit(*, assets_fn, materials_fn, atlas, tex_dir, fbx_dir, manifest_path, prev_dir, generator, size,
            hp_cfg, flat, mat_weight, budget, emission_colors, views=("three_quarter", "front"), cols=5,
            default_hp=(0.002, 1)):
    args = cli_args()
    t_start = time.time()
    dc.reset_scene()
    M = materials_fn()
    assets = assets_fn()
    only = [a.split("=", 1)[1].split(",") for a in args if a.startswith("--only=")]
    if only:
        assets = [a for a in assets if a.name in only[0]]
    weights = realize(assets, M, flat=flat, mat_weight=mat_weight)
    for a in assets:
        print(f"[kit] built {a.name:14s} raw tris={sum(tri_count(o) for o in a.objs)}")
    if FLIPPED:
        print(f"[kit] flipped {len(FLIPPED)} inside-out primitives: {sorted(set(FLIPPED))}")
    res = int(next((a.split("=", 1)[1] for a in args if a.startswith("--res=")), "512"))
    if "--build-only" in args:
        preview_assets(assets, Path(prev_dir) / "wip", "wip", views=views, res=res, cols=cols)
        return
    if "--fast" in args:
        size = size // 2
    paths = bake_kit(assets, weights, tex_dir, atlas, size, hp_cfg, default_hp=default_hp)
    baked = dc.baked_material(f"M_{atlas}", paths, emission_strength=4.0)
    assemble(assets, baked)
    manifest = {"generator": generator, "unity_axes": "Unity (x,y,z) = Blender (x,z,y)",
                "atlases": {atlas: {k: str(Path(v).relative_to(dc.PROJECT_ROOT)) for k, v in paths.items()}},
                "materials": {atlas: f"M_{atlas}"}, "emission_colors": emission_colors, "modules": []}
    export_assets(assets, fbx_dir, atlas, manifest, budget)
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(json.dumps(manifest, indent=2))
    print(f"[kit] manifest {manifest_path}")
    preview_assets(assets, prev_dir, atlas, views=views, res=res, cols=cols, baked=baked)
    eh.compose_sheet([str(paths[k]) for k in ("albedo", "normal", "orm", "emission")],
                     Path(prev_dir) / f"atlas_{atlas}.png", cols=4, cell=768)
    try:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(prev_dir) / f"{atlas}.blend"), compress=True)
    except RuntimeError as exc:
        print("[kit] blend save failed", exc)
    print(f"[kit] {atlas} DONE in {time.time() - t_start:.1f}s")


def verify_kit(manifest_path):
    """Fresh scene: re-import each FBX; compare bounds, piece pivots, sockets."""
    dc.reset_scene()
    man = json.loads(Path(manifest_path).read_text())
    bad = 0
    for m in man["modules"]:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(dc.PROJECT_ROOT / m["fbx"]), axis_forward="Z", axis_up="Y")
        new = [o for o in bpy.data.objects if o not in before]
        bpy.context.view_layer.update()
        meshes = [o for o in new if o.type == "MESH"]
        lo, hi = bounds_of(meshes, world=True)
        ulo, uhi = to_unity(lo), to_unity(hi)
        err = max(abs(a - b) for a, b in zip(ulo + uhi, m["unity_bounds_min"] + m["unity_bounds_max"]))
        socks = {o.name.split(".")[0]: to_unity(o.matrix_world.translation) for o in new if o.type == "EMPTY"}
        s_err = max([0.0] + [max(abs(a - b) for a, b in zip(socks.get(k, [9, 9, 9]), v))
                             for k, v in m["sockets"].items()])
        p_err = 0.0
        pivots = {}
        for o in meshes:
            key = o.name.split(".")[0]
            pivots[key] = to_unity(o.matrix_world.translation)
            if "pieces" in m and key in m["pieces"]:
                p_err = max(p_err, max(abs(a - b) for a, b in zip(pivots[key], m["pieces"][key]["pivot"])))
        mats = sorted({s.material.name.split(".")[0] for o in meshes for s in o.material_slots if s.material})
        tris = sum(tri_count(o) for o in meshes)
        single_pivot_ok = "pieces" in m or max(abs(c) for c in meshes[0].matrix_world.translation) < 1e-4
        ok = err < 2e-3 and s_err < 2e-3 and p_err < 2e-3 and len(mats) == 1 and tris == m["tris"] and single_pivot_ok
        bad += not ok
        print(f"[verify] {m['name']:14s} ok={ok} bounds_err={err:.5f} unity_min={ulo} unity_max={uhi} "
              f"pivots={pivots} sockets={socks} mats={mats} tris={tris}")
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    print(f"[verify] {len(man['modules']) - bad}/{len(man['modules'])} modules OK")
    return bad == 0


# ===========================================================================
# Arsenal
# ===========================================================================

OUT_DIR = dc.ART_ROOT / "Weapons" / "Arsenal"
TEX_DIR = OUT_DIR / "Textures"
MANIFEST = OUT_DIR / "arsenal_manifest.json"
PREV = dc.OUT_ROOT / "arsenal"
GLYPHS = PREV / "glyphs"

# Decal rectangles (metres, asset space) shared by geometry and materials.
CLEAVER_RUNES = (-0.040, 0.150, 0.110, 0.385)      # x0, z0, w, h on the blade flats
SPEAR_GROOVE = (-0.012, 1.505, 0.024, 0.29)
SCROLL_SEAL = (-0.026, -0.026, 0.052, 0.052)       # x, z around the seal centre


def cleaver_glyphs():
    rng = random.Random(41)
    x0, z0, w, h = CLEAVER_RUNES
    strokes = []
    # A column of scratched runes close to the spine, a second shorter column.
    cy = h - 0.012
    cells = [(0.012, 0.036, 0.042, 6), (0.060, 0.030, 0.036, 4)]
    for cx, cw, ch, count in cells:
        y = cy - ch
        for _ in range(count):
            strokes += rune_strokes(rng, cx, y, cw, ch, 0.0024, value=1.0, wobble=0.07)
            y -= ch + 0.016
    # A ring sigil near the heel and loose scratch marks.
    strokes.append(dict(pts=arc_pts(0.074, 0.05, 0.017, 0.3, TAU + 0.1, 28), w=0.0022))
    strokes.append(dict(pts=[(0.062, 0.05), (0.086, 0.05)], w=0.002))
    strokes.append(dict(pts=[(0.074, 0.036), (0.074, 0.064)], w=0.002))
    for _ in range(26):
        sx, sy = rng.uniform(0.0, w), rng.uniform(0.0, h)
        a = rng.uniform(-0.6, 0.6) + (math.pi / 2 if rng.random() < 0.3 else 0.0)
        ln = rng.uniform(0.008, 0.026)
        strokes.append(dict(pts=[(sx, sy), (sx + math.cos(a) * ln, sy + math.sin(a) * ln)], w=0.0011, v=0.45))
    return glyph_image("Cleaver_Runes", w, h, strokes, GLYPHS, max_px=1024)


def spear_glyphs():
    x0, z0, w, h = SPEAR_GROOVE
    cx = w * 0.5
    strokes = [dict(pts=[(cx, 0.004), (cx, h - 0.004)], w=0.0042)]
    rng = random.Random(7)
    y = 0.03
    while y < h - 0.03:
        k = rng.random()
        if k < 0.4:
            strokes.append(dict(pts=[(cx - 0.0045, y - 0.004), (cx, y + 0.001), (cx + 0.0045, y - 0.004)], w=0.0018))
        elif k < 0.7:
            strokes.append(dict(pts=[(cx - 0.004, y), (cx + 0.004, y)], w=0.0018))
        else:
            strokes.append(dict(pts=[(cx, y - 0.005), (cx + 0.004, y), (cx, y + 0.005), (cx - 0.004, y), (cx, y - 0.005)],
                                w=0.0016))
        y += rng.uniform(0.022, 0.034)
    return glyph_image("Spear_Groove", w, h, strokes, GLYPHS, max_px=512)


def scroll_glyph():
    x0, z0, w, h = SCROLL_SEAL
    c = w * 0.5
    s = [dict(pts=arc_pts(c, c, 0.0175, 0, TAU, 40), w=0.0022)]
    # Hourglass-eye sigil: two triangles, a pupil ring and four ticks.
    s.append(dict(pts=[(c - 0.010, c + 0.012), (c + 0.010, c + 0.012), (c, c), (c - 0.010, c + 0.012)], w=0.0019))
    s.append(dict(pts=[(c - 0.010, c - 0.012), (c + 0.010, c - 0.012), (c, c), (c - 0.010, c - 0.012)], w=0.0019))
    s.append(dict(pts=arc_pts(c, c, 0.0045, 0, TAU, 16), w=0.0016))
    for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        s.append(dict(pts=[(c + math.cos(a) * 0.0195, c + math.sin(a) * 0.0195),
                           (c + math.cos(a) * 0.0235, c + math.sin(a) * 0.0235)], w=0.0018))
    return glyph_image("Scroll_Seal", w, h, s, GLYPHS, max_px=512)


def arsenal_materials():
    M = {}
    # Cleaver: heavy rust, hammered flats, violet rune scratches (mask only).
    m = make_mat("A_CleaverBlade", "#86909A", dark="#525A62", light="#BCC6CE", metal=0.6, rough=0.42,
                         rough_var=0.12, noise_scale=5.0, noise_amt=0.45, edge_wear="#F2F6F8", edge_wear_amt=1.3,
                         cavity_dirt=0.9, bump_scale=30, bump_strength=0.1, bevel_radius=0.004)
    E2 = MatEdit(m)
    E2.albedo("#2E3338", E2.m("MULTIPLY", E2.rng(E2.x, 0.03, -0.058), 0.55))
    E2.albedo("#DCE4EA", E2.m("MULTIPLY", E2.rng(E2.z, 0.45, 0.66), 0.18))
    rust_layer(m, 0.92, scale=4.5, flake=0.22, hexes=("#3A1A0E", "#7A3A1A", "#C0702E"))
    E2 = MatEdit(m)
    hammer = E2.voronoi(30.0)
    E2.bump(E2.rng(hammer, 0.0, 0.5), 0.14)
    runes = E2.decal(cleaver_glyphs(), CLEAVER_RUNES, "X", "Z", face="Y", face_lo=0.6, face_hi=0.8)
    E2.albedo("#2A2030", E2.m("MULTIPLY", runes, 0.55))
    E2.albedo("#C9B8E6", E2.m("MULTIPLY", E2.rng(runes, 0.55, 0.95), 0.6))
    E2.rough(0.3, runes)
    E2.metal(0.6, runes)
    E2.bump(runes, -0.9)
    E2.emit(E2.rng(runes, 0.5, 0.95))
    edge = E2.rng(E2.x, 0.084, 0.1)
    E2.albedo("#E4EBEF", E2.m("MULTIPLY", edge, 0.75))
    E2.rough(0.22, edge)
    eh.enhance(m, edge_hex="#E6EDF1", edge_amt=1.0, edge_radius=0.004, top_hex="#B6C0C8", top_amt=0.15,
               cavity_amt=0.6, cavity_dist=0.03)
    M["cleaver_blade"] = m

    m = make_mat("A_SpearHead", "#8C969E", dark="#4E565C", light="#C8D0D6", metal=0.6, rough=0.38,
                         rough_var=0.1, noise_scale=7.0, noise_amt=0.45, edge_wear="#F4F8FA", edge_wear_amt=1.2,
                         cavity_dirt=0.9, bump_scale=35, bump_strength=0.1, bevel_radius=0.003)
    E = MatEdit(m)
    E.albedo("#30363C", E.m("MULTIPLY", E.rng(E.m("ABSOLUTE", E.x), 0.012, 0.0), 0.35))
    E.albedo("#E8EEF2", E.m("MULTIPLY", E.rng(E.m("ABSOLUTE", E.x), 0.025, 0.05), 0.5))
    rust_layer(m, 0.4, scale=7.0)
    E = MatEdit(m)
    g = E.decal(spear_glyphs(), SPEAR_GROOVE, "X", "Z", face="Y", face_lo=0.3, face_hi=0.55)
    E.albedo("#E8DDFF", E.m("MULTIPLY", g, 0.8))
    E.rough(0.25, g)
    E.metal(0.0, g)
    E.emit(g)
    eh.enhance(m, edge_hex="#F2F6F8", edge_amt=1.0, edge_radius=0.003, top_hex="#C4CCD2", top_amt=0.15,
               cavity_amt=0.5, cavity_dist=0.02)
    M["spear_head"] = m

    m = make_mat("A_DaggerBlade", "#88929A", dark="#4C545A", light="#C2CAD0", metal=0.6, rough=0.42,
                         noise_scale=8.0, noise_amt=0.45, edge_wear="#EEF3F5", edge_wear_amt=1.3, cavity_dirt=0.9,
                         bump_scale=40, bump_strength=0.1, bevel_radius=0.002)
    E = MatEdit(m)
    E.albedo("#2A3036", E.m("MULTIPLY", E.rng(E.x, 0.03, -0.02), 0.5))
    rust_layer(m, 0.45, scale=9.0, hexes=("#3E1E10", "#7A3E1C", "#A65E28"))
    eh.enhance(m, edge_hex="#F0F4F6", edge_amt=1.0, edge_radius=0.0025, top_hex="#B4BCC2", top_amt=0.15,
               cavity_amt=0.6, cavity_dist=0.02)
    M["dagger_blade"] = m

    M["iron"] = iron_mat("A_Iron", rust=0.45, edge_r=0.004)
    M["brass"] = brass_mat("A_Brass", edge_r=0.003, patina=0.18)
    M["grip"] = leather_mat("A_GripWrap", "#3B2618", "#160C06", "#6E4C30", stripes=("z", 85.0, 0.2, "#140A05"))
    M["leather"] = leather_mat("A_Leather", "#5E3B22", "#26150A", "#8E6440")
    M["ash"] = wood_mat("A_AshWood", "#A48A68", "#5E4A34", "#CDB896", grain=0.06, edge_r=0.004)
    M["bow_wood"] = wood_mat("A_BowWood", "#5A2A1E", "#22100A", "#8A4A32", grain=0.05, edge_r=0.004,
                             stripes=("z", 30.0, 0.04, "#1A0A06"), rough=0.5)
    M["drift_wood"] = wood_mat("A_DriftWood", "#6A5440", "#2A1C10", "#9A7E5E", grain=0.05, edge_r=0.005,
                               stripes=("z", 14.0, 0.05, "#20140A"))
    M["rope"] = cloth_mat("A_Rope", "#8A7350", "#3E3020", "#BBA27A", stripes=("z", 140.0, 0.25, "#3A2C1C"),
                          edge_r=0.002, weave=260)
    M["string"] = cloth_mat("A_String", "#D8CDB0", "#8A7E62", "#F4ECD6", edge_r=0.001, weave=300)
    M["red_cloth"] = cloth_mat("A_RedCloth", "#9A1826", "#4A0610", "#D23A44", stripes=("x", 16.0, 0.05, "#5A0A14"),
                               edge_r=0.003)
    M["rag"] = cloth_mat("A_Rag", "#9C8C6A", "#4A3E2A", "#C8B890", edge_r=0.002)
    M["bone"] = bone_mat("A_Bone", edge_r=0.003)
    M["feather"] = cloth_mat("A_Feather", "#B21E28", "#5A0A10", "#E04048", stripes=("z", 22.0, 0.12, "#EDE4D0"),
                             edge_r=0.0015, weave=400)
    M["cork"] = make_mat("A_Cork", "#A47C4E", dark="#5E4024", light="#D2A872", rough=0.85, noise_scale=40,
                                 noise_amt=0.9, cavity_dirt=0.6, bump_scale=160, bump_strength=0.45, bevel_radius=0.002)
    eh.enhance(M["cork"], edge_hex="#E2BE8A", edge_amt=0.5, edge_radius=0.003, top_hex="#E2BE8A", top_amt=0.2)
    M["copper_wire"] = brass_mat("A_CopperWire", edge_r=0.0015, patina=0.3)
    M["steel_wire"] = iron_mat("A_SteelWire", rust=0.0, edge_r=0.0015, base="#8A949C")
    M["char"] = make_mat("A_Char", "#2A1A12", dark="#0C0604", light="#5A3220", rough=0.9, noise_scale=30,
                                 noise_amt=0.9, bump_scale=120, bump_strength=0.4)
    M["frost"] = make_mat("A_Frost", "#B8ECFF", dark="#5AA8D8", light="#F2FCFF", rough=0.25, noise_scale=20,
                                  noise_amt=0.8, edge_wear="#FFFFFF", edge_wear_amt=1.0, bevel_radius=0.002)
    eh.enhance(M["frost"], edge_hex="#FFFFFF", edge_amt=1.0, edge_radius=0.002, top_hex="#FFFFFF", top_amt=0.3)
    M["glass_fire"], _ = glass_material("A_GlassFire", ("#B02006", "#FF6A12", "#FFC24A", "#FFE9A0"), 0.02,
                                        glass=("#4A2C1C", "#180C06", "#8A5C3C"))
    M["glass_ice"], _ = glass_material("A_GlassIce", ("#1460B0", "#2FC8F2", "#B8F6FF", "#F2FFFF"), 0.02, frost=True,
                                       glass=("#234052", "#0C1822", "#5E8AA2"))
    M["glass_heal"], _ = glass_material("A_GlassHeal", ("#5E0612", "#C8142C", "#FF5A64", "#FFC0C4"), 0.094,
                                        wobble=0.005, depth=0.09, glass=("#40202A", "#16080C", "#80505E"))

    m = make_mat("A_Crystal", "#8FD8FF", dark="#24408C", light="#E6FAFF", rough=0.15, rough_var=0.08,
                         noise_scale=18, noise_amt=0.9, bump_scale=30, bump_strength=0.1, bevel_radius=0.0015)
    E = MatEdit(m)
    n = E.noise(22.0, 4.0, 0.6, distortion=0.6)
    vein = E.rng(E.m("ABSOLUTE", E.m("SUBTRACT", n, 0.5)), 0.035, 0.0)
    core = E.rng(E.vlen(E.vec(E.x, E.y, 0.0)), 0.016, 0.0)
    E.albedo("#F2FDFF", E.m("MAXIMUM", vein, E.m("MULTIPLY", core, 0.6)))
    facet = E.rng(E.naxis("X"), -0.5, 0.8)
    E.albedo("#2C4CA0", E.m("MULTIPLY", E.m("SUBTRACT", 1.0, facet, clamp=True), 0.45))
    E.emit(E.m("MAXIMUM", E.m("ADD", E.m("MULTIPLY", n, 0.3), 0.5), E.m("MAXIMUM", vein, core)))
    eh.enhance(m, edge_hex="#FFFFFF", edge_amt=1.0, edge_radius=0.0025)
    M["crystal"] = m

    m = make_mat("A_Parchment", "#DCC79A", dark="#A0804E", light="#F2E4BE", rough=0.85, noise_scale=6,
                         noise_amt=0.8, cavity_dirt=0.5, bump_scale=90, bump_strength=0.12, bevel_radius=0.002)
    E = MatEdit(m)
    stain = E.rng(E.noise(14.0, 4.0, 0.6), 0.6, 0.7)
    E.albedo("#8C6436", E.m("MULTIPLY", stain, 0.35))
    ink = E.m("MULTIPLY", E.rng(E.m("SINE", E.m("MULTIPLY", E.x, 330.0)), 0.75, 0.95),
              E.rng(E.noise(60.0, 2.0, 0.5, stretch=(0.15, 1.0, 1.0)), 0.45, 0.6))
    E.albedo("#3A2A1C", E.m("MULTIPLY", ink, 0.3))
    eh.enhance(m, edge_hex="#6A4A26", edge_amt=0.9, edge_radius=0.003, top_hex="#FFF4D6", top_amt=0.2,
               cavity_amt=0.8, cavity_dist=0.02, cavity_hex="#3A2410")
    M["parchment"] = m

    m = make_mat("A_Wax", "#A3121E", dark="#4E040C", light="#E0404A", rough=0.4, noise_scale=20,
                         noise_amt=0.6, edge_wear="#FF8088", edge_wear_amt=0.8, cavity_dirt=0.7, bump_scale=50,
                         bump_strength=0.2, bevel_radius=0.002)
    E = MatEdit(m)
    sg = E.decal(scroll_glyph(), (SCROLL_SEAL[0], SCROLL_SEAL[1], SCROLL_SEAL[2], SCROLL_SEAL[3]), "X", "Z",
                 face="Y", face_lo=0.45, face_hi=0.7)
    E.albedo("#FFD27A", E.m("MULTIPLY", sg, 0.85))
    E.bump(sg, -0.7)
    E.emit(sg)
    eh.enhance(m, edge_hex="#E8505C", edge_amt=0.6, edge_radius=0.002, top_hex="#D83A48", top_amt=0.12)
    M["wax"] = m
    M["ribbon"] = cloth_mat("A_Ribbon", "#2C3A8C", "#10163C", "#5A6ED0", stripes=("x", 120.0, 0.08, "#D8B050"),
                            edge_r=0.0015, weave=350)
    return M


# ---------------------------------------------------------------------------
# Arsenal geometry
# ---------------------------------------------------------------------------

def build_cleaver():
    A = Asset("Cleaver", weight=1.25, tint="#9B5CFF",
              usage="Starting weapon (rusted executioner's cleaver). Grip centre at origin, blade along +Y, cutting "
                    "edge toward +X, flats face +-Z. Emission = violet rune scratches on both flats.")
    P = A.piece("Cleaver")
    xs = -0.056

    def xe(t):
        return 0.112 + 0.007 * math.sin(math.pi * t)

    def zb(x):
        return 0.09 + 0.034 * smooth01((x + 0.004) / 0.112)

    def zt(x, e):
        return 0.622 + 0.03 * (x - xs) / (e - xs)

    chips = [(0.18, 0.012, 0.035), (0.43, 0.022, 0.04), (0.62, 0.009, 0.025), (0.84, 0.018, 0.035)]
    rows = 48
    rings = []
    for i in range(rows + 1):
        t = i / rows
        e = xe(t)
        for tc, dep, hw in chips:
            d = abs(t - tc)
            if d < hw:
                e -= dep * (1.0 - d / hw) ** 1.3
        sh = min(0.088, e - 0.015)
        prof = [(e, 0.0), (sh, -0.0048), (0.055, -0.0066), (0.012, -0.0082), (-0.03, -0.0096), (-0.048, -0.0108),
                (xs + 0.002, -0.009), (xs - 0.003, 0.0), (xs + 0.002, 0.009), (-0.048, 0.0108), (-0.03, 0.0096),
                (0.012, 0.0082), (0.055, 0.0066), (sh, 0.0048)]
        ring = [Vector((x, y, lerp(zb(x), zt(x, e), t))) for x, y in prof]
        if i == rows:
            ring = [p + Vector((0, 0, 0.004 * math.sin(p.x * 90.0))) for p in ring]
        rings.append(ring)
    blade = loft(rings)
    hole = lathe([(0.0165, -0.03), (0.0165, 0.03)], segs=14)
    aim(hole, (0, 1, 0), (-0.024, 0, 0.568))
    blade = bm_boolean(blade, hole)
    P.add("cleaver_blade", blade)

    # Forged bolster, rivets, spine collar.
    P.add("iron", cbox((-0.012, 0, 0.082), (0.104, 0.034, 0.05), bev=0.008, segs=2))
    for x, z in ((-0.036, 0.128), (0.012, 0.13), (-0.01, 0.168)):
        for sgn in (-1, 1):
            P.add("iron", blob((x, sgn * 0.0095, z), 0.0075, scale=(1, 0.55, 1), segs=8, rings=5))
    # Short wrapped handle.
    P.add("grip", lathe(ridged(-0.084, 0.06, 0.0192, 0.0222, 11, end_r=0.019), segs=10))
    P.add("iron", lathe([(0.02, 0.06), (0.0245, 0.064), (0.0245, 0.072)], segs=10, cap0=False))
    # Iron pommel cap + hanging ring (in the X-Z plane, hole faces the camera).
    P.add("iron", lathe([(0.0, -0.114), (0.012, -0.113), (0.0225, -0.104), (0.024, -0.091), (0.021, -0.083),
                         (0.019, -0.08)], segs=10))
    P.add("iron", torus((0, 0, -0.146), 0.031, 0.0088, normal=(0, 1, 0), seg=18, rseg=6))
    return A


def build_spear():
    A = Asset("Spear", weight=1.0, tint="#7FD0FF",
              usage="Ash spear, grip point at origin (0.55 m from the butt); shaft y=-0.55..1.35, leaf head above. "
                    "Emission = rune groove on the head.")
    P = A.piece("Spear")

    def c(z):
        return Vector((0.003 * math.sin(z * 3.7 + 0.4) - 0.003 * math.sin(0.4), 0.002 * math.sin(z * 2.8 + 1.2) -
                       0.002 * math.sin(1.2), z))

    zs = [lerp(-0.545, 1.33, i / 28) for i in range(29)]
    P.add("ash", tube([c(z) for z in zs], [0.0196 - 0.0026 * (z + 0.545) / 1.875 for z in zs], segs=8))

    def at(z, bm):
        return translate(bm, c(z) - Vector((0, 0, z)))

    P.add("grip", at(0.0, lathe(ridged(-0.13, 0.13, 0.021, 0.0232, 15, end_r=0.0202), segs=8)))
    P.add("iron", at(-0.55, lathe([(0.0, -0.605), (0.009, -0.598), (0.0165, -0.578), (0.0205, -0.552),
                                   (0.0208, -0.505), (0.0182, -0.497)], segs=8)))
    P.add("iron", at(-0.52, torus((0, 0, -0.522), 0.021, 0.0035, seg=10, rseg=4)))
    for z in (1.075, 1.248):
        P.add("rope", at(z, torus((0, 0, z), 0.0192, 0.0045, seg=10, rseg=4)))
    P.add("rope", at(1.28, lathe(ridged(1.255, 1.302, 0.0186, 0.0208, 5), segs=8)))
    P.add("brass", at(1.33, lathe([(0.0165, 1.298), (0.0235, 1.302), (0.0255, 1.311), (0.021, 1.318), (0.021, 1.334),
                                   (0.026, 1.341), (0.026, 1.352), (0.021, 1.359), (0.0195, 1.372),
                                   (0.0155, 1.377)], segs=12)))
    P.add("iron", at(1.33, lathe([(0.0175, 1.37), (0.0178, 1.40), (0.0152, 1.44), (0.012, 1.466),
                                  (0.0105, 1.474)], segs=10)))
    for sgn in (-1, 1):
        P.add("brass", at(1.33, blob((sgn * 0.0172, 0, 1.405), 0.0048, segs=6, rings=4)))
        lug = [(sgn * 0.014, 0, 1.392), (sgn * 0.034, 0, 1.4), (sgn * 0.05, 0, 1.425)]
        P.add("iron", at(1.33, tube(lug, [0.0075, 0.0058, 0.0025], segs=6, flatten=0.55, up=Y)))
    # Leaf head with a sunken rune groove along the midrib.
    z0, L = 1.452, 0.42
    rings = []
    rows = 26
    for i in range(rows):
        t = i / rows
        w = 0.0105 * (1.0 - t) + 0.058 * math.sin(math.pi * t ** 0.72) ** 1.1
        th = 0.0115 * (1.0 - t) ** 0.6 + 0.002
        groove = 0.0 if t < 0.1 or t > 0.8 else th * 0.3 * min(1.0, (t - 0.1) / 0.06, (0.8 - t) / 0.06)
        fr = [1.0, 0.62, 0.3, 0.13]
        hy = [0.0, 0.45, 0.86, 1.0]
        top = [(w * f, th * h) for f, h in zip(fr, hy)] + [(0.0, th - groove)] + \
              [(-w * f, th * h) for f, h in reversed(list(zip(fr, hy)))]
        bot = [(-w * f, -th * h) for f, h in zip(fr[1:], hy[1:])] + [(0.0, -th + groove)] + \
              [(w * f, -th * h) for f, h in reversed(list(zip(fr[1:], hy[1:])))]
        rings.append([Vector((x, y, z0 + L * t)) for x, y in top + bot])
    head = loft(rings, tip1=Vector((0, 0, z0 + L)))
    P.add("spear_head", head)
    # Tattered red pennant lashed below the head (+X side, visible flat).
    rng = random.Random(5)
    R, C = 6, 9
    grid = []
    for r in range(R):
        v = r / (R - 1)
        Lr = 0.29 - 0.085 * (1.0 - abs(2.0 * v - 1.0)) ** 1.2 + rng.uniform(-0.018, 0.018)
        row = []
        for ci in range(C):
            u = ci / (C - 1)
            zc = lerp(1.085, 1.24, v)
            mid = 1.16
            z = mid + (zc - mid) * (1.0 - 0.3 * u) - 0.05 * u ** 1.5 + (rng.uniform(-0.006, 0.006) if ci == C - 1 else 0)
            y = 0.016 * math.sin(u * 5.2 + v * 0.7) * u ** 0.8
            row.append((0.016 + u * Lr, y, z))
        grid.append(row)
    P.add("red_cloth", thick_sheet(grid, 0.004))
    return A


def build_dagger():
    A = Asset("Dagger", weight=1.15, tint="#FFFFFF",
              usage="Curved tavern shiv (used as two instances for Twin Daggers). Grip centre at origin, blade +Y, "
                    "edge on the concave +X side. No emission.")
    P = A.piece("Dagger")

    def c(t):
        return Vector((0.044 * t * t - 0.006 * t, 0.0, 0.058 + 0.2 * t))

    rows = 44
    rings = []
    for i in range(rows):
        t = i / rows
        tg = (c(min(1.0, t + 0.01)) - c(max(0.0, t - 0.01))).normalized()
        side = Vector((tg.z, 0.0, -tg.x)).normalized()
        W = 0.042 * (1.0 - t ** 2.2) * (1.0 + 0.12 * math.sin(math.pi * min(1.0, t * 1.6)))
        we, ws = W * 0.56, W * 0.44
        for tn in (0.22, 0.34, 0.46):
            d = t - tn
            if -0.05 < d < 0.0:
                ws -= 0.009 * (1.0 + d / 0.05)
        if t > 0.7:
            ws *= 1.0 - 0.55 * smooth01((t - 0.7) / 0.18)
        if i in (11, 23):
            we -= 0.004
        tk = 0.0042 * (1.0 - 0.6 * t)
        sh = min(0.0015, 0.4 * ws)
        prof = [(we, 0.0), (0.45 * we, tk * 0.55), (-0.3 * ws, tk), (-ws + sh, tk * 0.8), (-ws, 0.0),
                (-ws + sh, -tk * 0.8), (-0.3 * ws, -tk), (0.45 * we, -tk * 0.55)]
        p = c(t)
        rings.append([p + side * a + Y * b for a, b in prof])
    tip = c(1.0) + Vector((0.004, 0, 0.004))
    P.add("dagger_blade", loft(rings, tip1=tip))
    # Crude bent-bar guard and lug.
    P.add("iron", tube([(-0.034, 0, 0.044), (-0.016, 0, 0.054), (0.012, 0, 0.055), (0.03, 0, 0.064), (0.04, 0, 0.08)],
                       [0.0058, 0.0062, 0.0062, 0.0055, 0.0042], segs=6))
    P.add("iron", cbox((0.0, 0, 0.051), (0.032, 0.017, 0.016), bev=0.004))
    # Rag binding + dangling tail.
    rng = random.Random(3)
    P.add("rag", lathe([(0.0128, 0.016), (0.0158, 0.021), (0.0152, 0.028), (0.0165, 0.035), (0.0148, 0.041),
                        (0.0125, 0.045)], segs=9, jitter=0.08, rng=rng))
    grid = [[(0.011 + 0.01 * u, -0.006 - 0.006 * u, 0.032 - 0.058 * u + 0.004 * math.sin(u * 6)) for u in (0, 0.33, 0.66, 1)],
            [(0.019 + 0.012 * u, -0.006 - 0.006 * u, 0.032 - 0.05 * u + 0.004 * math.sin(u * 6)) for u in (0, 0.33, 0.66, 1)]]
    grid = [list(r) for r in zip(*grid)]
    P.add("rag", thick_sheet(grid, 0.003))
    # Bone handle with a knuckle pommel.
    P.add("bone", lathe([(0.0128, 0.03), (0.0136, 0.018), (0.0122, 0.0), (0.0114, -0.022), (0.0122, -0.045),
                         (0.0145, -0.062), (0.0158, -0.072)], segs=10, cap0=False, cap1=False))
    P.add("bone", blob((0.0, 0, -0.077), 0.0175, scale=(1.05, 0.85, 0.75), segs=10, rings=7))
    for sgn in (-1, 1):
        P.add("bone", blob((sgn * 0.0095, 0, -0.087), 0.0118, scale=(1, 0.9, 0.9), segs=8, rings=6))
    for z in (-0.012, -0.024, -0.036):
        P.add("string", torus((0, 0, z), 0.0121, 0.0021, seg=10, rseg=4))
    return A


def bow_path():
    up = [(0.0, 0.0), (-0.004, 0.06), (-0.010, 0.12), (-0.010, 0.17), (-0.003, 0.24), (0.012, 0.32), (0.031, 0.40),
          (0.049, 0.47), (0.060, 0.515), (0.064, 0.55), (0.057, 0.582), (0.040, 0.604), (0.018, 0.617)]
    full = [(y, -z) for y, z in reversed(up[1:])] + up
    pts = catmull([Vector((0.0, y, z)) for y, z in full], n=2)
    return pts


def build_bow():
    A = Asset("Bow", weight=1.0, tint="#FFFFFF",
              usage="Spiked recurve bow. Grip at origin, limbs along +-Y, string on the +Z side 0.08 m behind the "
                    "grip; a nocked arrow flies toward -Z. No emission.")
    P = A.piece("Bow")
    path = bow_path()
    zs = [p.z for p in path]

    def dims(z):
        a = abs(z)
        if a < 0.08:
            return 0.038, 0.052
        if a < 0.17:
            k = (a - 0.08) / 0.09
            return lerp(0.038, 0.052, k), lerp(0.052, 0.038, k)
        k = (a - 0.17) / 0.45
        return lerp(0.052, 0.026, k), lerp(0.034, 0.016, k)

    base = [(1.0, 0.0), (0.82, 0.72), (0.0, 1.0), (-0.82, 0.72), (-1.0, 0.0), (-0.82, -0.72), (0.0, -1.0),
            (0.82, -0.72)]

    def prof(k, f, s=1.0):
        w, t = dims(zs[k])
        return [(a * w * 0.5 * s, b * t * 0.5 * s) for a, b in base]

    P.add("bow_wood", sweep(path, prof, side_hint=X))
    fr = frames(path, X)

    def sub(z0, z1, scale, mat):
        idx = [k for k, z in enumerate(zs) if z0 <= z <= z1]
        if len(idx) < 2:
            return
        pp = [path[k] for k in idx]
        P.add(mat, sweep(pp, lambda k, f: prof(idx[k], f, scale), side_hint=X))

    # Leather grip with ridges, brass bands at the riser, iron tip sheaths.
    gz = [lerp(-0.075, 0.075, i / 14) for i in range(15)]
    gp = [Vector((0, 0.0005 * math.sin(z * 30), z)) for z in gz]
    P.add("grip", sweep(gp, lambda k, f: [(a * 0.021 * (1.07 if k % 2 else 1.0), b * 0.0275 * (1.07 if k % 2 else 1.0))
                                          for a, b in base], side_hint=X))
    for z0, z1 in ((0.155, 0.19), (-0.19, -0.155), (0.33, 0.35), (-0.35, -0.33)):
        sub(z0, z1, 1.18, "brass")
    sub(0.565, 0.7, 1.16, "iron")
    sub(-0.7, -0.565, 1.16, "iron")
    # Spikes: one off each tip (continuing the curl), one up/down, two along the back of each limb.
    for sgn in (1, -1):
        k_tip = len(path) - 1 if sgn > 0 else 0
        p, t, s, nn = fr[k_tip]
        tdir = t if sgn > 0 else -t
        P.add("iron", cone(p - tdir * 0.012, tdir, 0.1, 0.016, segs=6))
        P.add("iron", cone(p + Vector((0, 0.004, -sgn * 0.012)), Vector((0, -0.3, sgn)), 0.085, 0.0145, segs=6))
        P.add("iron", cone(p + Vector((0, 0.0, -sgn * 0.024)), Vector((0, 0.35, sgn)), 0.055, 0.011, segs=5))
        k = min(range(len(zs)), key=lambda i: abs(zs[i] - sgn * 0.11))
        p2, t2, s2, n2 = fr[k]
        back2 = -n2 if n2.y > 0 else n2
        P.add("iron", cone(p2 + back2 * 0.014, back2 + Vector((0, 0, sgn * 0.25)), 0.068, 0.013, segs=6))
        for zz in (0.36, 0.43, 0.5):
            k = min(range(len(zs)), key=lambda i: abs(zs[i] - sgn * zz))
            p, t, s, nn = fr[k]
            w, th = dims(zs[k])
            back = -nn if nn.y > 0 else nn
            P.add("iron", cone(p + back * th * 0.3, back + Vector((0, 0, sgn * 0.55)), 0.072, 0.0125, segs=5))
    # Bone arrow shelf on the riser.
    P.add("bone", cbox((0.0175, 0.0, 0.083), (0.012, 0.03, 0.012), bev=0.003))
    # String: hugs the recurve bellies, straight at y=+0.08 between them.
    pts = []
    for k in range(len(path)):
        z = zs[k]
        if abs(z) > 0.556:
            p, t, s, nn = fr[k]
            w, th = dims(z)
            belly = nn if nn.y > 0 else -nn
            pts.append(p + belly * (th * 0.5 + 0.003))
    upper = [p for p in pts if p.z > 0]
    lower = [p for p in pts if p.z < 0]
    upper.sort(key=lambda p: -p.z)
    lower.sort(key=lambda p: p.z)
    straight_top = Vector((0, 0.08, 0.5))
    straight_bot = Vector((0, 0.08, -0.5))
    spts = upper + [straight_top] + [Vector((0, 0.08, z)) for z in (0.25, 0.0, -0.25)] + [straight_bot] + \
        list(reversed(lower))
    spts.sort(key=lambda p: -p.z)
    P.add("string", tube(spts, [0.0024] * len(spts), segs=5))
    P.add("string", lathe([(0.0028, -0.035), (0.0036, -0.03), (0.0036, 0.03), (0.0028, 0.035)], segs=6,
                          center=(0, 0.08, 0)))
    return A


def build_arrow():
    A = Asset("Arrow", weight=0.9, tint="#FFFFFF",
              usage="Arrow, 0.75 m along +Y, origin at its centre, head at +Y. No emission.")
    P = A.piece("Arrow")
    P.add("ash", tube([(0, 0, -0.362), (0, 0, 0.0), (0, 0, 0.302)], [0.0052, 0.0055, 0.0052], segs=6))
    # Barbed broadhead (thin plate with sharpened edges) + socket.
    out = [(0.0, 0.375), (0.0105, 0.347), (0.0175, 0.318), (0.0185, 0.300), (0.0062, 0.314), (0.0048, 0.305)]
    poly = out + [(-x, z) for x, z in reversed(out[1:])]
    head = prism_xz(poly, -0.0021, 0.0021)
    for v in head.verts:
        if abs(v.co.x) > 0.007 or v.co.z > 0.36:
            v.co.y *= 0.3
    P.add("iron", head)
    P.add("iron", lathe([(0.0055, 0.288), (0.0066, 0.292), (0.0062, 0.306), (0.0046, 0.318)], segs=6))
    P.add("string", lathe(ridged(0.272, 0.288, 0.0056, 0.0064, 3), segs=6))
    # Three vanes, one in the camera-facing plane.
    vane = [(0.0045, -0.338), (0.020, -0.337), (0.0235, -0.318), (0.0215, -0.288), (0.017, -0.262), (0.011, -0.236),
            (0.0045, -0.212)]
    for a in (0.0, TAU / 3, 2 * TAU / 3):
        b = prism_xz(vane, -0.0009, 0.0009)
        rot(b, a, "Z")
        P.add("feather", b)
    P.add("string", lathe(ridged(-0.345, -0.334, 0.0054, 0.0062, 2), segs=6))
    P.add("string", lathe(ridged(-0.216, -0.205, 0.0054, 0.0062, 2), segs=6))
    P.add("bone", lathe([(0.0054, -0.36), (0.0068, -0.364), (0.0068, -0.372), (0.0042, -0.375)], segs=6))
    return A


def build_grenade(kind):
    fire = kind == "fire"
    name = "FireGrenade" if fire else "IceGrenade"
    A = Asset(name, weight=1.3, tint="#FF7A1A" if fire else "#5FE6FF",
              usage=f"Thrown {'fire' if fire else 'ice'} flask, origin at the flask centre, neck +Y. "
                    "Emission = liquid (mask white; Unity applies the HDR colour).")
    P = A.piece(name)
    glass = "glass_fire" if fire else "glass_ice"
    wire = "copper_wire" if fire else "steel_wire"
    P.add(glass, blob((0, 0, 0), 0.071, scale=(1.0, 1.0, 0.94), segs=16, rings=11))
    P.add(glass, lathe([(0.0265, 0.054), (0.0215, 0.068), (0.0205, 0.084), (0.026, 0.089), (0.0262, 0.097),
                        (0.0205, 0.1)], segs=12, cap0=False))
    P.add("cork", lathe([(0.0, 0.086), (0.0172, 0.086), (0.0186, 0.1), (0.021, 0.114), (0.0222, 0.123),
                         (0.0175, 0.1295), (0.0, 0.1305)], segs=10))
    # Wire cage: two meridian loops, an equator band, neck twist and a bail over the cork.
    for a in (math.radians(20), math.radians(110)):
        pts = []
        for i in range(22):
            th = lerp(0.62, TAU - 0.62, i / 21)
            pts.append(Vector((math.sin(th) * math.cos(a), math.sin(th) * math.sin(a), math.cos(th) * 0.94)) * 0.0735)
        P.add(wire, tube(pts, [0.0022] * len(pts), segs=4))
    P.add(wire, torus((0, 0, 0), 0.0738, 0.0026, seg=26, rseg=4))
    P.add(wire, torus((0, 0, 0.069), 0.0232, 0.003, seg=12, rseg=4))
    P.add(wire, torus((0, 0, 0.0765), 0.0222, 0.0026, seg=12, rseg=4))
    P.add(wire, tube([(-0.024, 0, 0.073), (-0.022, 0, 0.11), (-0.012, 0, 0.133), (0.0, 0, 0.1365), (0.012, 0, 0.133),
                      (0.022, 0, 0.11), (0.024, 0, 0.073)], [0.0021] * 7, segs=4))
    P.add(wire, blob((0.0235, -0.008, 0.072), 0.0045, segs=6, rings=4))
    P.add(wire, tube([(0.024, -0.009, 0.072), (0.036, -0.016, 0.068), (0.044, -0.02, 0.06)], [0.0018] * 3, segs=4))
    if fire:
        P.add("rag", tube([(0.004, 0, 0.122), (0.012, 0, 0.142), (0.026, -0.002, 0.156), (0.04, -0.004, 0.16),
                           (0.05, -0.005, 0.156)], [0.0058, 0.0055, 0.005, 0.0046, 0.004], segs=6, flatten=0.6))
        P.add("char", blob((0.054, -0.005, 0.155), 0.0062, scale=(1.2, 0.9, 1), segs=6, rings=5,
                           rng=random.Random(2), jitter=0.2))
    else:
        rng = random.Random(9)
        for a, el, ln in ((0.3, 0.9, 0.05), (1.9, 0.75, 0.042), (3.6, 0.95, 0.056), (4.9, 0.7, 0.04), (2.7, 0.5, 0.032)):
            d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
            base = d * 0.062 + Vector((0, 0, 0.012))
            b = cone(base, d + Vector((0, 0, 0.35)), ln, 0.009, segs=5)
            jitter_bm(b, 0.0015, rng)
            P.add("frost", b)
    return A


def build_harpoon():
    A = Asset("Harpoon", weight=1.1, tint="#9FE8FF",
              usage="Enemy projectile: harpoon forged from crystallized lightning. 1.2 m along +Y, origin at centre, "
                    "head toward +Y. Emission = crystal (greyscale veins).")
    P = A.piece("Harpoon")
    rng = random.Random(23)

    def c(z):
        return Vector((0.006 * math.sin(z * 4.1 + 0.3) + 0.0025 * math.sin(z * 11.0), 0.004 * math.sin(z * 3.3 + 1.1), z))

    zs = [lerp(-0.555, 0.30, i / 30) for i in range(31)]
    radii = []
    for z in zs:
        r = 0.0205 + sum(0.0045 * math.exp(-((z - zk) / 0.022) ** 2) for zk in (-0.31, 0.02, 0.17))
        radii.append(r * rng.uniform(0.96, 1.04))
    P.add("drift_wood", tube([c(z) for z in zs], radii, segs=8))

    def at(z, bm):
        return translate(bm, c(z) - Vector((0, 0, z)))

    P.add("iron", at(-0.55, lathe([(0.0, -0.566), (0.012, -0.566), (0.0205, -0.558), (0.0215, -0.522),
                                   (0.0195, -0.512)], segs=8)))
    P.add("iron", at(-0.56, cbox((0, 0, -0.568), (0.012, 0.01, 0.014), bev=0.002)))
    P.add("iron", at(-0.56, torus((0, 0, -0.5815), 0.0135, 0.0045, normal=(0, 1, 0), seg=12, rseg=5)))
    P.add("rope", at(-0.56, tube([(0.0, 0.0, -0.594), (0.012, -0.004, -0.6), (0.026, -0.006, -0.592),
                                  (0.036, -0.006, -0.575)], [0.0045, 0.0045, 0.0042, 0.0036], segs=5)))
    P.add("rope", at(0.24, lathe(ridged(0.19, 0.282, 0.0228, 0.0255, 9), segs=8)))
    P.add("iron", at(0.29, lathe([(0.023, 0.276), (0.028, 0.281), (0.029, 0.302), (0.025, 0.31)], segs=10)))
    for z in (-0.12, 0.08):
        P.add("iron", at(z, lathe([(0.019, z - 0.009), (0.0212, z - 0.006), (0.0212, z + 0.006), (0.019, z + 0.009)],
                                  segs=8, cap0=False, cap1=False)))
    # Crystal head: a kinked lightning bolt shard plus backward barbs.
    top = c(0.3)
    spine = [top + Vector(v) for v in ((0, 0, 0.0), (0.014, 0.0, 0.07), (-0.012, 0.002, 0.13), (0.011, -0.002, 0.2),
                                        (-0.003, 0.0, 0.255))]
    tip = top + Vector((0.001, 0, 0.3))
    rings = []
    radii = [0.029, 0.034, 0.027, 0.02, 0.011]
    fr = frames(spine, X)
    for k, (p, t, s, nn) in enumerate(fr):
        ph = rng.uniform(0, TAU)
        rings.append([p + (s * math.cos(ph + TAU * i / 5) + nn * math.sin(ph + TAU * i / 5)) * radii[k] *
                      rng.uniform(0.85, 1.15) * (0.8 if i % 2 else 1.0) for i in range(5)])
    P.add("crystal", loft(rings, tip1=tip))
    for (z, sgn, ln) in ((0.06, 1, 0.105), (0.1, -1, 0.11), (0.165, 1, 0.085), (0.21, -1, 0.07), (0.03, -1, 0.065)):
        base = top + Vector((sgn * 0.006, rng.uniform(-0.004, 0.004), z))
        d = Vector((sgn * 0.75, rng.uniform(-0.15, 0.15), -0.62)).normalized()
        mid = base + d * ln * 0.55 + Vector((sgn * 0.004, 0, 0.012))
        end = base + d * ln
        bpath = [base, mid]
        br = []
        bfr = frames(bpath, Y)
        for k, (p, t, s, nn) in enumerate(bfr):
            r = (0.013 if k == 0 else 0.008)
            br.append([p + (s * math.cos(TAU * i / 4 + 0.4) + nn * math.sin(TAU * i / 4 + 0.4)) * r for i in range(4)])
        P.add("crystal", loft(br, tip1=end))
    for a in (0.5, 2.6, 4.4):
        d = Vector((math.cos(a), math.sin(a), 0.9)).normalized()
        b = cone(top + Vector((math.cos(a) * 0.018, math.sin(a) * 0.018, 0.0)), d, 0.035, 0.008, segs=4)
        P.add("crystal", jitter_bm(b, 0.0015, rng))
    return A


def build_flask():
    A = Asset("Flask", weight=1.3, tint="#FF2A3A",
              usage="Health flask, origin at the bottom centre, 0.22 m tall. Emission = red liquid.")
    P = A.piece("Flask")
    body = [(0.0, 0.0), (0.05, 0.0), (0.074, 0.01), (0.088, 0.034), (0.09, 0.062), (0.083, 0.092), (0.064, 0.114),
            (0.036, 0.128), (0.027, 0.136)]
    P.add("glass_heal", lathe(body, segs=16, scale_xy=(1.0, 0.74)))
    P.add("glass_heal", lathe([(0.03, 0.128), (0.025, 0.142), (0.024, 0.163), (0.0305, 0.168), (0.031, 0.176),
                               (0.0245, 0.179)], segs=12, cap0=False))
    P.add("cork", lathe([(0.0, 0.172), (0.0195, 0.172), (0.021, 0.186), (0.0235, 0.196)], segs=10, cap1=False))
    rng = random.Random(4)
    P.add("wax", lathe([(0.0225, 0.188), (0.029, 0.192), (0.0295, 0.204), (0.024, 0.214), (0.012, 0.2185),
                        (0.0, 0.219)], segs=12, jitter=0.05, rng=rng))
    for a, ln in ((0.4, 0.016), (1.9, 0.024), (3.3, 0.012), (4.6, 0.02)):
        d = Vector((math.cos(a), math.sin(a), 0))
        P.add("wax", tube([d * 0.029 + Vector((0, 0, 0.193)), d * 0.0315 + Vector((0, 0, 0.193 - ln * 0.6)),
                           d * 0.0305 + Vector((0, 0, 0.193 - ln))], [0.0028, 0.0024, 0.0017], segs=5))
    P.add("brass", torus((0, 0, 0.139), 0.0272, 0.0042, seg=12, rseg=4))
    # Leather waist band with a brass buckle, and a carry strap loop on +X.
    band = []
    for i in range(24):
        a = TAU * i / 24
        band.append(Vector((math.cos(a) * 0.0918, math.sin(a) * 0.0918 * 0.74, 0.058)))
    P.add("leather", tube(band, [0.0026] * 24, segs=6, flatten=3.2, closed=True, up=Z))
    P.add("brass", cbox((0, -0.069, 0.058), (0.026, 0.006, 0.024), bev=0.0025))
    P.add("leather", cbox((0, -0.0725, 0.058), (0.012, 0.004, 0.017), bev=0.0015))
    strap = [(0.03, 0.0, 0.148), (0.05, 0.0, 0.175), (0.08, 0.0, 0.19), (0.104, 0.0, 0.17), (0.112, 0.0, 0.13),
             (0.103, 0.0, 0.09), (0.093, 0.0, 0.064)]
    P.add("leather", tube(catmull(strap, 2), [0.0026] * 13, segs=6, flatten=2.6, up=Y))
    P.add("leather", torus((0, 0, 0.151), 0.0262, 0.0026, seg=12, rseg=6, flatten=2.4))
    P.add("brass", torus((0.094, 0, 0.068), 0.008, 0.0022, normal=(0, 1, 0), seg=10, rseg=4))
    return A


def build_scroll():
    A = Asset("Scroll", weight=1.2, tint="#FFC94A",
              usage="Scroll of Power pickup: rolled parchment 0.35 m along X, origin at the roll centre, wax seal "
                    "toward the camera (-Z). Emission = seal glyph.")
    P = A.piece("Scroll")
    turns, r0, r1, th = 2.25, 0.011, 0.033, 0.0026
    n = 46
    outer, inner = [], []
    a_end = 1.75
    for i in range(n + 1):
        a = TAU * turns * (i / n - 1.0) + a_end
        r = lerp(r0, r1, i / n)
        dirv = (math.cos(a), math.sin(a))
        outer.append((r + th * 0.5, dirv))
        inner.append((r - th * 0.5, dirv))
    # Loose outer flap continuing tangentially.
    tng = (-math.sin(a_end), math.cos(a_end))
    end = (math.cos(a_end) * r1, math.sin(a_end) * r1)
    flap = [(end[0] + tng[0] * d + math.cos(a_end) * d * d * 3.0, end[1] + tng[1] * d + math.sin(a_end) * d * d * 3.0)
            for d in (0.012, 0.024)]
    poly = [(d[0] * r, d[1] * r) for r, d in outer] + [(fx + math.cos(a_end) * th * 0.5, fz + math.sin(a_end) * th * 0.5)
                                                     for fx, fz in flap]
    poly += [(fx - math.cos(a_end) * th * 0.5, fz - math.sin(a_end) * th * 0.5) for fx, fz in reversed(flap)]
    poly += [(d[0] * r, d[1] * r) for r, d in reversed(inner)]
    rings = []
    for x, s in ((-0.175, 1.05), (-0.16, 1.0), (-0.08, 0.985), (0.0, 0.98), (0.08, 0.985), (0.16, 1.0), (0.175, 1.05)):
        rings.append([Vector((x, py * s, pz * s)) for py, pz in poly])
    P.add("parchment", loft(rings))
    # Ribbon band around the middle, tails hanging from under the seal.
    rad = r1 + th * 0.5 + 0.0018
    band = [Vector((0.0, math.cos(TAU * i / 24) * rad, math.sin(TAU * i / 24) * rad)) for i in range(24)]
    P.add("ribbon", tube(band, [0.0016] * 24, segs=6, flatten=7.0, closed=True, up=X))
    for sgn in (-1, 1):
        grid = []
        for k in range(5):
            u = k / 4
            row = []
            for w in (-0.008, 0.008):
                x = sgn * (0.006 + 0.03 * u) + w * 0.6
                zz = -0.012 - 0.065 * u - (0.006 if (w > 0) == (sgn > 0) and k == 4 else 0.0)
                row.append((x, -rad - 0.003 - 0.004 * math.sin(u * 3), zz))
            grid.append(row)
        P.add("ribbon", thick_sheet(grid, 0.002))
    # Wax seal facing the camera.
    rng = random.Random(8)
    seal = lathe([(0.0, -0.002), (0.022, -0.002), (0.0255, 0.002), (0.0245, 0.0062), (0.019, 0.0092), (0.0, 0.0098)],
                 segs=16, jitter=0.07, rng=rng)
    aim(seal, (0, -1, 0), (0.0, -r1 - 0.004, 0.0))
    P.add("wax", seal)
    for a in (0.6, 2.2, 3.9, 5.1):
        P.add("wax", blob((math.cos(a) * 0.025, -r1 - 0.002, math.sin(a) * 0.025), 0.0055, scale=(1, 0.6, 1), segs=6,
                          rings=4))
    return A


def arsenal_assets():
    return [build_cleaver(), build_spear(), build_dagger(), build_bow(), build_arrow(), build_grenade("fire"),
            build_grenade("ice"), build_harpoon(), build_flask(), build_scroll()]


ARSENAL_HP = {
    "crystal": (0.0008, 0), "frost": (0.0008, 0), "red_cloth": (0.0, 1), "rag": (0.0, 1), "ribbon": (0.0, 1),
    "feather": (0.0, 0), "string": (0.0, 1), "rope": (0.0, 1), "glass_fire": (0.0, 1), "glass_ice": (0.0, 1),
    "glass_heal": (0.0, 1), "parchment": (0.0008, 0), "cleaver_blade": (0.0015, 1), "dagger_blade": (0.001, 1),
    "spear_head": (0.001, 1),
}
ARSENAL_MAT_WEIGHT = {"cleaver_blade": 1.2, "spear_head": 1.3, "ash": 0.75, "string": 0.6, "rope": 0.8,
                      "crystal": 1.15, "wax": 1.5, "drift_wood": 0.85}


def main():
    if "--verify" in cli_args():
        ok = verify_kit(MANIFEST)
        print("[arsenal] verify", "PASSED" if ok else "FAILED")
        return
    run_kit(assets_fn=arsenal_assets, materials_fn=arsenal_materials, atlas="Arsenal", tex_dir=TEX_DIR,
            fbx_dir=OUT_DIR, manifest_path=MANIFEST, prev_dir=PREV, generator="Tools/Blender/build_arsenal.py",
            size=2048, hp_cfg=ARSENAL_HP, flat=("crystal", "frost"), mat_weight=ARSENAL_MAT_WEIGHT,
            budget=lambda a: 4000,
            emission_colors={"Cleaver runes": "#9B5CFF", "Spear rune groove": "#7FD0FF", "FireGrenade liquid": "#FF7A1A",
                             "IceGrenade liquid": "#5FE6FF", "Harpoon crystal": "#9FE8FF", "Flask liquid": "#FF2A3A",
                             "Scroll seal glyph": "#FFC94A"},
            views=("three_quarter", "front"), cols=5)


if __name__ == "__main__":
    main()
