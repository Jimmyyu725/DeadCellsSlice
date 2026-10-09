"""Environment-kit helpers for the Prisoners' Quarters kit.

Builds on dc_common (never edited from here). Everything below works on
bmesh "pieces" that are appended into one Builder per module, so a module is
a single mesh with per-face material slots, a per-corner tint attribute
(dc_tint: R = brightness, G = green grime, B = darkening) used by the
procedural materials, and a per-face UV density weight (dc_uvw).
"""

import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils import noise as mnoise
from mathutils.bvhtree import BVHTree

import dc_common as dc

TAU = math.tau
UP = Vector((0, 0, 1))
NEUTRAL = (0.5, 0.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# bmesh primitives (each returns a fresh bmesh)
# ---------------------------------------------------------------------------

def bm_box(lo, hi):
    bm = bmesh.new()
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    co = ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
          (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
    v = [bm.verts.new(c) for c in co]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])
    bm.normal_update()
    return bm


def bm_prism_xz(poly, y0, y1):
    """Extrude a convex x-z polygon along +Y from y0 to y1 (closed)."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in poly]
    back = [bm.verts.new((x, y1, z)) for x, z in poly]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_lathe(profile, segs=12, phase=0.0, cap_top=True, cap_bottom=True, scale_xy=(1.0, 1.0)):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rings = []
    for r, z in profile:
        rings.append([bm.verts.new((math.cos(phase + TAU * i / segs) * r * scale_xy[0],
                                    math.sin(phase + TAU * i / segs) * r * scale_xy[1], z))
                      for i in range(segs)])
    cum = [0.0]
    for k in range(1, len(profile)):
        cum.append(cum[-1] + math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]))
    rmean = sum(abs(r) for r, _ in profile) / len(profile) * (scale_xy[0] + scale_xy[1]) / 2
    du = TAU * max(rmean, 1e-4) / segs
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            f = bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
            for lp, uv in zip(f.loops, ((i * du, cum[k]), ((i + 1) * du, cum[k]), ((i + 1) * du, cum[k + 1]),
                                         (i * du, cum[k + 1]))):
                lp[uvl].uv = uv
    if cap_bottom and profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_tube(points, radii, segs=6, up=None, flatten=1.0, cap=True, closed=False, twist=0.0):
    """Sweep a ring along a polyline (parallel-transport frames)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    if isinstance(radii, (int, float)):
        radii = [radii] * n
    bm = bmesh.new()
    tangents = []
    for k in range(n):
        if closed:
            t = pts[(k + 1) % n] - pts[k - 1]
        elif k == 0:
            t = pts[1] - pts[0]
        elif k == n - 1:
            t = pts[k] - pts[k - 1]
        else:
            t = pts[k + 1] - pts[k - 1]
        tangents.append(t.normalized())
    ref = Vector(up) if up is not None else (UP if abs(tangents[0].dot(UP)) < 0.9 else Vector((1, 0, 0)))
    side = tangents[0].cross(ref).normalized()
    rings = []
    for k in range(n):
        t = tangents[k]
        if k > 0:
            side = side - t * side.dot(t)
            if side.length < 1e-6:
                side = t.cross(ref)
            side.normalize()
        nrm = side.cross(t).normalized()
        ring = []
        for i in range(segs):
            a = TAU * i / segs + twist
            off = side * math.cos(a) * radii[k] + nrm * math.sin(a) * radii[k] * flatten
            ring.append(bm.verts.new(pts[k] + off))
        rings.append(ring)
    uvl = bm.loops.layers.uv.new("UVMap")
    cum = [0.0]
    for k in range(1, n):
        cum.append(cum[-1] + (pts[k] - pts[k - 1]).length)
    total = cum[-1] + ((pts[0] - pts[-1]).length if closed else 0.0)
    rmean = max(sum(radii) / n, 1e-4)
    du = TAU * rmean * (1.0 + flatten) / 2 / segs
    last = n if closed else n - 1
    for k in range(last):
        k2 = (k + 1) % n
        v0, v1 = cum[k], (cum[k2] if k2 != 0 else total)
        for i in range(segs):
            j = (i + 1) % segs
            f = bm.faces.new((rings[k][i], rings[k][j], rings[k2][j], rings[k2][i]))
            for lp, uv in zip(f.loops, ((i * du, v0), ((i + 1) * du, v0), ((i + 1) * du, v1), (i * du, v1))):
                lp[uvl].uv = uv
    if cap and not closed:
        if radii[0] > 1e-4:
            bm.faces.new(list(reversed(rings[0])))
        else:
            _collapse_ring(bm, rings[0])
        if radii[-1] > 1e-4:
            bm.faces.new(rings[-1])
        else:
            _collapse_ring(bm, rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def _collapse_ring(bm, ring):
    bmesh.ops.pointmerge(bm, verts=ring, merge_co=sum((v.co for v in ring), Vector()) / len(ring))


def bm_blob(center, radius, scale=(1, 1, 1), segs=7, rings=5, rng=None, jitter=0.0, rot=None):
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0, calc_uvs=True)
    for v in bm.verts:
        c = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) * radius
        if rng and jitter:
            c += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jitter * radius
        if rot is not None:
            c = rot @ c
        v.co = c + Vector(center)
    bm.normal_update()
    return bm


def bm_ico(center, radius, scale=(1, 1, 1), subdiv=1, rng=None, jitter=0.0):
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0, calc_uvs=True)
    for v in bm.verts:
        c = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) * radius
        if rng and jitter:
            c += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jitter * radius
        v.co = c + Vector(center)
    bm.normal_update()
    return bm


def bm_hull(points):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    bmesh.ops.delete(bm, geom=list(set(res.get("geom_interior", []) + res.get("geom_unused", []))), context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(4), verts=list(bm.verts), edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def look_matrix(p0, p1, roll=0.0):
    """Matrix mapping local +Z to the segment p0->p1, origin at p0."""
    d = Vector(p1) - Vector(p0)
    q = UP.rotation_difference(d.normalized())
    m = q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, "Z")
    m.translation = Vector(p0)
    return m


def transform(bm, m):
    bmesh.ops.transform(bm, matrix=m, verts=list(bm.verts))
    return bm


def translate(bm, d):
    return transform(bm, Matrix.Translation(Vector(d)))


def rotate(bm, angle, axis, origin=(0, 0, 0)):
    o = Vector(origin)
    m = Matrix.Translation(o) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-o)
    return transform(bm, m)


def scale(bm, s, origin=(0, 0, 0)):
    o = Vector(origin)
    if isinstance(s, (int, float)):
        s = (s, s, s)
    m = Matrix.Translation(o) @ Matrix.Diagonal((s[0], s[1], s[2], 1.0)) @ Matrix.Translation(-o)
    return transform(bm, m)


# ---------------------------------------------------------------------------
# bmesh operations
# ---------------------------------------------------------------------------

def bm_cut(bm, co, no):
    """Remove everything on the +no side of a plane and cap the hole."""
    co, no = Vector(co), Vector(no).normalized()
    if not any((v.co - co).dot(no) > 1e-5 for v in bm.verts):
        return bm
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_split(bm, co, no):
    """Insert an edge loop along a plane (no removal)."""
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector(co), plane_no=Vector(no))
    return bm


def chip_corner(bm, corner, outward, rng, size=(0.03, 0.1), dims=None):
    corner = Vector(corner)
    a = [rng.uniform(*size) for _ in range(3)]
    if dims:
        a = [min(a[i], dims[i] * 0.42) for i in range(3)]
    p1 = corner - Vector((outward[0] * a[0], 0, 0))
    p2 = corner - Vector((0, outward[1] * a[1], 0))
    p3 = corner - Vector((0, 0, outward[2] * a[2]))
    no = (p2 - p1).cross(p3 - p1).normalized()
    if no.dot(Vector(outward)) < 0:
        no = -no
    return bm_cut(bm, p1, no)


def bm_bevel(bm, offset, segs=2, profile=0.5, min_angle=20.0, edge_filter=None):
    bm.normal_update()
    lim = math.radians(min_angle)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim]
    if edge_filter:
        edges = [e for e in edges if edge_filter(e)]
    if edges and offset > 0:
        bmesh.ops.bevel(bm, geom=edges, offset=offset, offset_type="OFFSET", segments=segs, profile=profile,
                        affect="EDGES", clamp_overlap=True)
    bm.normal_update()
    return bm


def delete_faces(bm, pred):
    bm.normal_update()
    dead = [f for f in bm.faces if pred(f.calc_center_median(), f.normal)]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context="FACES")
    return bm


def mirror_x(bm, cx=0.0):
    for v in bm.verts:
        v.co.x = 2 * cx - v.co.x
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.normal_update()
    return bm


def block(lo, hi, rng, *, chips=0, chip_size=(0.03, 0.1), corners=None, bevel=0.02, segs=2, jitter=0.0,
          fixed_top=None, splits_y=(), cuts=(), crack=None, crack_gap=0.018, back_delete=None, min_angle=20.0,
          pre=None, bevel_back=None):
    """Chunky stone/wood block.  Returns a list of bmeshes (two if cracked).

    corners: list of (sx, sy, sz) sign triples that may be chipped (default:
    the four front corners).  fixed_top: z value that must not move (walkable
    tops).  crack: (point, normal) splits the block into two pieces.
    back_delete: delete faces facing +Y whose centre y > value (hidden).
    """
    lo, hi = Vector(lo), Vector(hi)
    bm = bm_box(lo, hi)
    if jitter:
        for v in bm.verts:
            if abs(v.co.y - lo.y) < 1e-6:
                v.co.x += rng.uniform(-jitter, jitter)
                if fixed_top is None or abs(v.co.z - fixed_top) > 1e-6:
                    v.co.z += rng.uniform(-jitter, jitter)
    if pre:
        pre(bm)
    for co, no in cuts:
        bm_cut(bm, co, no)
    corners = corners or [(-1, -1, -1), (1, -1, -1), (-1, -1, 1), (1, -1, 1)]
    dims = hi - lo
    for c in rng.sample(corners, min(chips, len(corners))):
        p = Vector((hi.x if c[0] > 0 else lo.x, hi.y if c[1] > 0 else lo.y, hi.z if c[2] > 0 else lo.z))
        chip_corner(bm, p, c, rng, chip_size, dims)
    for s in splits_y:
        if lo.y + 0.05 < s < hi.y - 0.05:
            bm_split(bm, (0, s, 0), (0, 1, 0))
    pieces = [bm]
    if crack:
        pco, pno = Vector(crack[0]), Vector(crack[1]).normalized()
        other = bm.copy()
        bm_cut(bm, pco + pno * crack_gap * 0.5, pno)
        bm_cut(other, pco - pno * crack_gap * 0.5, -pno)
        pieces = [bm, other]
    flt = None
    if bevel_back is not None:
        def flt(e):
            return not all(v.co.y > bevel_back for v in e.verts)
    for p in pieces:
        bm_bevel(p, bevel, segs, min_angle=min_angle, edge_filter=flt)
        if back_delete is not None:
            delete_faces(p, lambda c, n: n.y > 0.9 and c.y > back_delete)
    return pieces


# ---------------------------------------------------------------------------
# Module builder
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.tint = self.bm.loops.layers.float_color.new("dc_tint")
        self.uvw = self.bm.faces.layers.float.new("dc_uvw")
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.hasuv = self.bm.faces.layers.int.new("dc_hasuv")
        self.mats = []
        self.sockets = {}

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def add(self, src, mat, tint=None, uvw=1.0, smooth=False, hard=28.0, tint_fn=None, uvw_fn=None):
        """Append bmesh `src` (consumed).  src may be a list of bmeshes."""
        if isinstance(src, (list, tuple)):
            for s in src:
                self.add(s, mat, tint, uvw, smooth, hard, tint_fn, uvw_fn)
            return
        src.normal_update()
        tint = tint or NEUTRAL
        mi = self._mi(mat)
        src_uv = src.loops.layers.uv.active
        vmap = {v: self.bm.verts.new(v.co) for v in src.verts}
        for f in src.faces:
            vs = [vmap[v] for v in f.verts]
            try:
                nf = self.bm.faces.new(vs)
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = True
            c = f.calc_center_median()
            nf[self.uvw] = uvw_fn(c, f.normal) if uvw_fn else uvw
            nf[self.hasuv] = 1 if src_uv else 0
            for loop, old in zip(nf.loops, f.loops):
                loop[self.tint] = tint_fn(loop.vert.co, f.normal) if tint_fn else tint
                if src_uv:
                    loop[self.uv].uv = old[src_uv].uv
        lim = math.radians(hard)
        for e in src.edges:
            sharp = False
            if not smooth and len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
                sharp = True
            if sharp:
                ne = self.bm.edges.get((vmap[e.verts[0]], vmap[e.verts[1]]))
                if ne:
                    ne.smooth = False
        src.free()

    def mirror_x(self, cx):
        mirror_x(self.bm, cx)

    def build(self):
        tri = [f for f in self.bm.faces if len(f.verts) > 4]
        if tri:
            bmesh.ops.triangulate(self.bm, faces=tri, quad_method="BEAUTY", ngon_method="EAR_CLIP")
        self.bm.normal_update()
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(self.name, me)
        dc.link(obj)
        for sname, pos in self.sockets.items():
            e = bpy.data.objects.new(sname, None)
            e.empty_display_type = "ARROWS"
            e.empty_display_size = 0.15
            dc.link(e)
            e.parent = obj
            e.location = Vector(pos)
        return obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ---------------------------------------------------------------------------
# Moss blanket (projected onto a smooth "envelope" so tiles join seamlessly)
# ---------------------------------------------------------------------------

def envelope_bvh(bm):
    bm.normal_update()
    return BVHTree.FromBMesh(bm)


def sheet_from_grids(grids):
    """Quads from row-major point grids; points shared between grids (same
    coordinates) become shared vertices.  Returns (bm, key->vert)."""
    bm = bmesh.new()
    keyed = {}

    def V(p):
        k = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        if k not in keyed:
            keyed[k] = bm.verts.new(p)
        return keyed[k]

    for g in grids:
        for r in range(len(g) - 1):
            for c in range(len(g[r]) - 1):
                vs = list(dict.fromkeys([V(g[r][c]), V(g[r][c + 1]), V(g[r + 1][c + 1]), V(g[r + 1][c])]))
                if len(vs) < 3:
                    continue
                try:
                    bm.faces.new(vs)
                except ValueError:
                    pass
    return bm, keyed


def key_of(p):
    return (round(p[0], 5), round(p[1], 5), round(p[2], 5))


def project_sheet(bm, bvh, *, offset=0.022, lump=None, tuck_verts=(), tuck=0.003, smooth=1,
                  zmax=None, zmax_xrange=(-0.01, 1.01)):
    """Shrink-wrap every vertex onto the envelope (nearest point + offset)."""
    tuck_verts = set(tuck_verts)
    new = {}
    for v in bm.verts:
        loc, nrm, _, _ = bvh.find_nearest(v.co)
        d = v.co - loc
        direction = d.normalized() if d.length > 1e-6 else nrm
        off = tuck if v in tuck_verts else offset + (lump(loc) if lump else 0.0)
        new[v] = loc + direction * off
    for v, co in new.items():
        v.co = co
    for _ in range(smooth):
        inner = [v for v in bm.verts if not v.is_boundary]
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.45, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    if zmax is not None:
        for v in bm.verts:
            if zmax_xrange[0] <= v.co.x <= zmax_xrange[1]:
                v.co.z = min(v.co.z, zmax)
    bm.normal_update()
    for f in bm.faces:
        _, nrm, _, _ = bvh.find_nearest(f.calc_center_median())
        if f.normal.dot(nrm) < 0:
            f.normal_flip()
    bm.normal_update()
    return bm


def moss_net(bvh, xs, top_ys, front_ts, drape, *, y_out=-1.3, z_out=1.3, z_ref=1.0,
             side_ys=None, side_drape=None, side_x_out=None,
             offset=0.022, lump=None, zmax=None, zmax_xrange=(-0.01, 1.01), tuck=0.003, smooth=1,
             tuck_back=False):
    """Moss sheet = folded box net (top + front [+ one side]) shrink-projected
    onto an envelope.  Rows are generated outside the envelope and pulled to
    the nearest surface point + offset along the outward direction.

    xs: x columns (front/top), top_ys: y rows back->front (top patch),
    front_ts: 0..1 drape rows, drape(x): drape depth below z_ref.
    side_*: optional side patch at x = side_x_out (must equal xs[0]).
    """
    grids = []
    top = [[(x, y, z_out) for x in xs] for y in top_ys] + [[(x, y_out, z_out) for x in xs]]
    grids.append(top)
    front = [top[-1]] + [[(x, y_out, z_ref - t * drape(x)) for x in xs] for t in front_ts]
    grids.append(front)
    tuck_pts = list(front[-1])
    if side_ys is not None:
        ys = [y_out] + list(side_ys)
        side = [[(side_x_out, y, z_out) for y in ys]] + \
               [[(side_x_out, y, z_ref - t * side_drape(y)) for y in ys] for t in front_ts]
        grids.append(side)
        tuck_pts += side[-1]
    if tuck_back:
        # covering that stops part-way back: feather its back edge into the surface
        tuck_pts += top[0]
        if side_ys is not None:
            tuck_pts += [row[-1] for row in grids[-1]]
    bm, keyed = sheet_from_grids(grids)
    tv = [keyed[key_of(p)] for p in tuck_pts if key_of(p) in keyed]
    return project_sheet(bm, bvh, offset=offset, lump=lump, tuck_verts=tv, tuck=tuck, smooth=smooth,
                         zmax=zmax, zmax_xrange=zmax_xrange)


def bm_rounded_prism(profile_xz, y0, y1, r):
    """Convex envelope: prism of an (inset) x-z profile Minkowski-summed with
    a sphere of radius r (all edges rounded by r)."""
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=1.0)
    dirs = [v.co.normalized() for v in tmp.verts]
    tmp.free()
    pts = []
    for x, z in profile_xz:
        for y in (y0, y1):
            for d in dirs:
                pts.append(Vector((x, y, z)) + d * r)
    return bm_hull(pts)


def bm_append(dst, src):
    """Copy geometry of src into dst (no custom data)."""
    vmap = {v: dst.verts.new(v.co) for v in src.verts}
    for f in src.faces:
        try:
            dst.faces.new([vmap[v] for v in f.verts])
        except ValueError:
            pass
    return dst


def chip_vertex(bm, rng, size, pick=None, wobble=0.35):
    """Knock a chunk off a (convex) piece at one of its corners."""
    cands = [v for v in bm.verts if (pick is None or pick(v.co))]
    if not cands:
        return bm
    v = rng.choice(cands)
    cen = sum((u.co for u in bm.verts), Vector()) / len(bm.verts)
    n = (v.co - cen).normalized()
    n = (n + Vector((rng.uniform(-wobble, wobble), rng.uniform(-wobble, wobble), rng.uniform(-wobble, wobble)))).normalized()
    return bm_cut(bm, v.co - n * size, n)


def moss_strand(top, length, rng, width=0.035, sway=0.03, segs=4, face_dir=Vector((0, -1, 0)), rings=5):
    """Hanging moss tendril, flattened against the wall it hangs on."""
    top = Vector(top)
    pts, radii = [], []
    phase = rng.uniform(0, TAU)
    for k in range(rings):
        t = k / (rings - 1)
        side = Vector((1, 0, 0)) if abs(face_dir.x) < 0.5 else Vector((0, 1, 0))
        p = top + Vector((0, 0, -length * t)) + side * math.sin(phase + t * 3.0) * sway * t
        p += face_dir * (0.006 * t)
        pts.append(p)
        radii.append(width * (1.0 - 0.82 * t ** 0.8))
    up = -face_dir
    return bm_tube(pts, radii, segs=segs, up=up, flatten=0.5, cap=True)


def periodic_noise(x, y, z, freq=6.0, seed=0.0):
    """Noise periodic in x with period 1 (tile-seamless)."""
    a = TAU * x
    r = freq / TAU
    return mnoise.noise(Vector((math.cos(a) * r + seed, math.sin(a) * r, (y + z) * freq * 0.7)))


# ---------------------------------------------------------------------------
# Materials: dc.make_material + extra hand-painted layers
# ---------------------------------------------------------------------------

def _first_link(sock):
    return sock.links[0] if sock.is_linked else None


def stretch_coords(mat, scale_xyz):
    """Insert a Mapping node after the Object coordinates (wood grain)."""
    nt = mat.node_tree
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    out = dc._sock(tc.outputs, "Object")
    mp = dc.new_node(nt, "ShaderNodeMapping", (-1500, 300))
    dc._sock(mp.inputs, "Scale").default_value = scale_xyz
    targets = [l.to_socket for l in list(out.links)]
    for l in list(out.links):
        nt.links.remove(l)
    nt.links.new(out, dc._sock(mp.inputs, "Vector"))
    for t in targets:
        nt.links.new(dc._sock(mp.outputs, "Vector"), t)
    return dc._sock(mp.outputs, "Vector")


def make_periodic(mat, period_x, period_z):
    """Make every noise in the material periodic in object X and Z (4D torus
    mapping) so a module tiles without texture seams."""
    nt = mat.node_tree
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    obj = dc._sock(tc.outputs, "Object")
    sep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-1900, 600))
    nt.links.new(obj, dc._sock(sep.inputs, "Vector"))

    def circ(sock, period, fn):
        a = dc.math_node(nt, "MULTIPLY", sock, TAU / period, loc=(-1800, 600), clamp=False)
        b = dc.math_node(nt, fn, a, 0.0, loc=(-1700, 600), clamp=False)
        return dc.math_node(nt, "MULTIPLY", b, period / TAU, loc=(-1600, 600), clamp=False)

    xc = circ(dc._sock(sep.outputs, "X"), period_x, "COSINE")
    xs = circ(dc._sock(sep.outputs, "X"), period_x, "SINE")
    zc = circ(dc._sock(sep.outputs, "Z"), period_z, "COSINE")
    zs = circ(dc._sock(sep.outputs, "Z"), period_z, "SINE")
    comb = dc.new_node(nt, "ShaderNodeCombineXYZ", (-1500, 600))
    nt.links.new(xc, dc._sock(comb.inputs, "X"))
    nt.links.new(xs, dc._sock(comb.inputs, "Y"))
    nt.links.new(zc, dc._sock(comb.inputs, "Z"))
    for n in nt.nodes:
        if n.type == "TEX_NOISE":
            n.noise_dimensions = "4D"
            nt.links.new(dc._sock(comb.outputs, "Vector"), dc._sock(n.inputs, "Vector"))
            nt.links.new(zs, dc._sock(n.inputs, "W"))
    return dc._sock(comb.outputs, "Vector"), zs


def _coord_socket(nt):
    """Coordinate socket feeding dc's big noise (after any mapping)."""
    for n in nt.nodes:
        if n.type == "TEX_NOISE":
            lk = _first_link(dc._sock(n.inputs, "Vector"))
            if lk:
                return lk.from_socket
    tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
    return dc._sock(tc.outputs, "Object")


def enhance(mat, *, tint_amt=0.0, grime_hex=None, grime_amt=0.0, blotch=None,
            top_hex=None, top_amt=0.0, bottom_amt=0.0,
            edge_hex=None, edge_amt=0.0, edge_radius=0.04, edge_top_bias=0.5,
            cavity_amt=0.0, cavity_dist=0.12, cavity_hex="#05080C",
            brick=None, periodic_w=None, extra=None):
    """Re-route DC_ALBEDO through extra painterly layers.

    blotch: (hex, noise_scale, coverage) e.g. rust patches on iron.
    brick: (brick_w, brick_h, mortar_hex) object-space brick overlay (BG kit).
    extra: callable(nt, color_socket, coord_socket, geo_node) -> color socket.
    """
    nt = mat.node_tree
    tag = nt.nodes["DC_ALBEDO"]
    lk = tag.inputs[0].links[0]
    col = lk.from_socket
    nt.links.remove(lk)
    coord = _coord_socket(nt)
    geo = dc.new_node(nt, "ShaderNodeNewGeometry", (-1700, -1300))
    nsep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-1500, -1300))
    nt.links.new(dc._sock(geo.outputs, "Normal"), dc._sock(nsep.inputs, "Vector"))
    nz = dc._sock(nsep.outputs, "Z")
    x = -400

    def nxt():
        nonlocal x
        x += 60
        return (x, 400)

    if brick:
        bw, bh, mortar_hex = brick
        bsep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-1700, 900))
        tc = next(n for n in nt.nodes if n.type == "TEX_COORD")
        nt.links.new(dc._sock(tc.outputs, "Object"), dc._sock(bsep.inputs, "Vector"))
        u = dc.math_node(nt, "ADD", dc._sock(bsep.outputs, "X"), dc._sock(bsep.outputs, "Y"), loc=(-1600, 900), clamp=False)
        comb = dc.new_node(nt, "ShaderNodeCombineXYZ", (-1500, 900))
        nt.links.new(u, dc._sock(comb.inputs, "X"))
        nt.links.new(dc._sock(bsep.outputs, "Z"), dc._sock(comb.inputs, "Y"))
        br = dc.new_node(nt, "ShaderNodeTexBrick", (-1400, 900))
        nt.links.new(dc._sock(comb.outputs, "Vector"), dc._sock(br.inputs, "Vector"))
        dc._sock(br.inputs, "Scale").default_value = 1.0
        dc._sock(br.inputs, "Mortar Size").default_value = 0.035
        dc._sock(br.inputs, "Mortar Smooth").default_value = 0.2
        dc._sock(br.inputs, "Brick Width").default_value = bw
        dc._sock(br.inputs, "Row Height").default_value = bh
        dc._sock(br.inputs, "Color1").default_value = (0.82, 0.82, 0.82, 1)
        dc._sock(br.inputs, "Color2").default_value = (1.12, 1.12, 1.12, 1)
        dc._sock(br.inputs, "Mortar").default_value = (0, 0, 0, 1)
        br.offset = 0.5
        br.squash = 1.0
        _, col = dc.mix_rgb(nt, col, dc._sock(br.outputs, "Color"), 1.0, blend="MULTIPLY", loc=nxt())
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba(mortar_hex), dc._sock(br.outputs, "Fac"), loc=nxt())

    if tint_amt or grime_hex:
        attr = dc.new_node(nt, "ShaderNodeAttribute", (-1700, -1600))
        attr.attribute_type = "GEOMETRY"
        attr.attribute_name = "dc_tint"
        sep = dc.new_node(nt, "ShaderNodeSeparateColor", (-1500, -1600))
        nt.links.new(dc._sock(attr.outputs, "Color"), dc._sock(sep.inputs, "Color"))
        if tint_amt:
            f = dc.map_range(nt, dc._sock(sep.outputs, "Red"), 0.0, 1.0, 1.0 - tint_amt, 1.0 + tint_amt, loc=(-1300, -1600))
            cc = dc.new_node(nt, "ShaderNodeCombineColor", (-1200, -1600))
            for ch in ("Red", "Green", "Blue"):
                nt.links.new(f, dc._sock(cc.inputs, ch))
            _, col = dc.mix_rgb(nt, col, dc._sock(cc.outputs, "Color"), 1.0, blend="MULTIPLY", loc=nxt())
            dark = dc.math_node(nt, "MULTIPLY", dc._sock(sep.outputs, "Blue"), 0.75, loc=(-1300, -1750))
            _, col = dc.mix_rgb(nt, col, dc.hex_rgba("#05080C"), dark, loc=nxt())
        if grime_hex:
            gn = dc.noise(nt, scale=7.0, detail=3.0, roughness=0.6, loc=(-1500, -1900), coord=coord)
            gm = dc.map_range(nt, dc._sock(gn.outputs, "Fac"), 0.35, 0.65, 0.4, 1.0, loc=(-1300, -1900))
            g = dc.math_node(nt, "MULTIPLY", dc._sock(sep.outputs, "Green"), gm, loc=(-1200, -1800))
            g = dc.math_node(nt, "MULTIPLY", g, grime_amt or 1.0, loc=(-1100, -1800))
            _, col = dc.mix_rgb(nt, col, dc.hex_rgba(grime_hex), g, loc=nxt())

    if blotch:
        bhex, bscale, cover = blotch
        bn = dc.noise(nt, scale=bscale, detail=4.0, roughness=0.65, loc=(-1500, 1200), coord=coord)
        if periodic_w is not None:
            bn.noise_dimensions = "4D"
            nt.links.new(periodic_w, dc._sock(bn.inputs, "W"))
        bm_ = dc.map_range(nt, dc._sock(bn.outputs, "Fac"), 1.0 - cover, 1.0 - cover + 0.08, loc=(-1300, 1200))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba(bhex), bm_, loc=nxt())

    if top_hex and top_amt:
        t = dc.map_range(nt, nz, 0.25, 0.95, 0.0, top_amt, loc=(-1300, -1300))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba(top_hex), t, loc=nxt())
    if bottom_amt:
        b = dc.map_range(nt, nz, -0.2, -0.95, 0.0, bottom_amt, loc=(-1300, -1400))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba("#05080C"), b, loc=nxt())

    if edge_hex and edge_amt:
        bev = dc.new_node(nt, "ShaderNodeBevel", (-1500, -2200))
        bev.samples = 16
        dc._sock(bev.inputs, "Radius").default_value = edge_radius
        dot = dc.new_node(nt, "ShaderNodeVectorMath", (-1300, -2200))
        dot.operation = "DOT_PRODUCT"
        nt.links.new(dc._sock(bev.outputs, "Normal"), dot.inputs[0])
        nt.links.new(dc._sock(geo.outputs, "Normal"), dot.inputs[1])
        e = dc.map_range(nt, dot.outputs["Value"], 0.992, 0.9, 0.0, 1.0, loc=(-1150, -2200))
        en = dc.noise(nt, scale=22.0, detail=3.0, roughness=0.6, loc=(-1500, -2400), coord=coord)
        if periodic_w is not None:
            en.noise_dimensions = "4D"
            nt.links.new(periodic_w, dc._sock(en.inputs, "W"))
        brk = dc.map_range(nt, dc._sock(en.outputs, "Fac"), 0.38, 0.58, 0.2, 1.0, loc=(-1150, -2400))
        e = dc.math_node(nt, "MULTIPLY", e, brk, loc=(-1000, -2200))
        bsep = dc.new_node(nt, "ShaderNodeSeparateXYZ", (-1300, -2500))
        nt.links.new(dc._sock(bev.outputs, "Normal"), dc._sock(bsep.inputs, "Vector"))
        bias = dc.map_range(nt, dc._sock(bsep.outputs, "Z"), -0.6, 0.7, 1.0 - edge_top_bias, 1.0, loc=(-1150, -2500))
        e = dc.math_node(nt, "MULTIPLY", e, bias, loc=(-900, -2200))
        e = dc.math_node(nt, "MULTIPLY", e, edge_amt, loc=(-800, -2200))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba(edge_hex), e, loc=nxt())

    if cavity_amt:
        ao = dc.new_node(nt, "ShaderNodeAmbientOcclusion", (-1500, -2800))
        ao.samples = 16
        ao.only_local = True
        ao.inside = False
        dc._sock(ao.inputs, "Distance").default_value = cavity_dist
        c = dc.map_range(nt, dc._sock(ao.outputs, "AO"), 0.92, 0.3, 0.0, cavity_amt, loc=(-1300, -2800))
        _, col = dc.mix_rgb(nt, col, dc.hex_rgba(cavity_hex), c, loc=nxt())

    if extra:
        col = extra(nt, col, coord, geo)

    nt.links.new(col, tag.inputs[0])
    return mat


# ---------------------------------------------------------------------------
# UV atlas across many objects
# ---------------------------------------------------------------------------

def _uv_area(me, uv, poly):
    pts = [uv[li].uv for li in poly.loop_indices]
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return abs(a) * 0.5


def _face_uv_area(f, uvl):
    pts = [lp[uvl].uv for lp in f.loops]
    a = 0.0
    for i in range(len(pts)):
        a += pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
    return abs(a) * 0.5


def triangulate_ngons(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tri = [f for f in bm.faces if len(f.verts) > 4]
    if tri:
        bmesh.ops.triangulate(bm, faces=tri, quad_method="BEAUTY", ngon_method="EAR_CLIP")
        bm.to_mesh(obj.data)
    bm.free()


def normalize_islands(obj, weight):
    """Scale every UV island (split further by dc_uvw class) to 1 UV unit
    per metre * weight * face weight, so density is uniform before packing."""
    from bpy_extras import bmesh_utils
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active
    uvw = bm.faces.layers.float.get("dc_uvw")
    n_isl = 0
    for isl in bmesh_utils.bmesh_linked_uv_islands(bm, uvl):
        groups = {}
        for f in isl:
            groups.setdefault(round(f[uvw], 3) if uvw else 1.0, []).append(f)
        for w, faces in groups.items():
            n_isl += 1
            a3 = sum(f.calc_area() for f in faces)
            auv = sum(_face_uv_area(f, uvl) for f in faces)
            if a3 < 1e-10 or auv < 1e-14:
                continue
            sc = math.sqrt(a3 / auv) * weight * (w if w > 0 else 1.0)
            c = Vector((0.0, 0.0))
            k = 0
            for f in faces:
                for lp in f.loops:
                    c += lp[uvl].uv
                    k += 1
            c /= k
            for f in faces:
                for lp in f.loops:
                    lp[uvl].uv = c + (lp[uvl].uv - c) * sc
    bm.to_mesh(me)
    bm.free()
    return n_isl


def atlas_uv(objs, weights, margin=0.0015, angle=66.0, shape="CONCAVE"):
    """Shared atlas: procedural primitives keep their own UVs (one island per
    tube / lathe / sphere); everything else is smart-projected.  Islands are
    normalised to a common texel density (times per-object weight and
    per-face dc_uvw), then all objects are packed into one 0-1 space."""
    dc.deselect_all()
    for o in objs:
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    for o in objs:
        bm = bmesh.from_edit_mesh(o.data)
        uvl = bm.loops.layers.uv.active
        flag = bm.faces.layers.int.get("dc_hasuv")
        for f in bm.faces:
            f.select_set(False)
        for f in bm.faces:
            need = flag is None or f[flag] == 0 or _face_uv_area(f, uvl) < 1e-12
            f.select_set(need)
        bm.select_flush_mode()
        bmesh.update_edit_mesh(o.data)
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    n_isl = sum(normalize_islands(o, weights.get(o.name, 1.0)) for o in objs)
    dc.deselect_all()
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="ANY", scale=True,
                            merge_overlap=False, margin_method="FRACTION", margin=margin, shape_method=shape)
    bpy.ops.object.mode_set(mode="OBJECT")
    dens, cover = {}, 0.0
    for o in objs:
        me = o.data
        uv = me.uv_layers.active.data
        fa3 = fauv = 0.0
        for p in me.polygons:
            a = _uv_area(me, uv, p)
            cover += a
            if p.normal.y < -0.9 or not dens.get(o.name):
                pass
            if p.normal.y < -0.9:
                fa3 += p.area
                fauv += a
        if fa3 == 0:
            fa3 = sum(p.area for p in me.polygons)
            fauv = sum(_uv_area(me, uv, p) for p in me.polygons)
        dens[o.name] = math.sqrt(fauv / max(fa3, 1e-12))
    print(f"[env] atlas: {n_isl} islands, UV coverage {cover:.3f}")
    return dens


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def render_framed(path, center, ortho_scale, direction, res=(960, 540), engine="BLENDER_EEVEE", bg="#101A24",
                  key_energy=3.0, rim_energy=3.5, sun_dir=(50, 0, 30)):
    """Explicitly framed ortho render (for level-chunk and pixelation checks)."""
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("PreviewWorld")
    scene.world = world
    bgn = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None) if world.node_tree else None
    if bgn:
        dc._sock(bgn.inputs, "Color").default_value = dc.hex_rgba(bg)
        dc._sock(bgn.inputs, "Strength").default_value = 0.6
    cam_data = bpy.data.cameras.new("FrameCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho_scale
    cam_data.clip_end = 500
    cam = dc.link(bpy.data.objects.new("FrameCam", cam_data))
    scene.camera = cam
    d = Vector(direction).normalized()
    cam.location = Vector(center) + d * 60
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    key = dc.link(bpy.data.objects.new("FrameKey", bpy.data.lights.new("FrameKey", "SUN")))
    key.data.energy = key_energy
    key.rotation_euler = tuple(math.radians(a) for a in sun_dir)
    rim = dc.link(bpy.data.objects.new("FrameRim", bpy.data.lights.new("FrameRim", "SUN")))
    rim.data.energy = rim_energy
    rim.data.color = (0.5, 0.8, 1.0)
    rim.rotation_euler = (math.radians(-60), 0, math.radians(200))
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    for o in (cam, key, rim):
        bpy.data.objects.remove(o, do_unlink=True)
    return str(path)


def _load_px(path):
    import numpy as np
    img = bpy.data.images.load(str(path), check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def _save_px(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(Path(path).stem, w, h, alpha=True)
    img.pixels.foreach_set(arr.astype("float32").ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return str(path)


def _resize_nearest(a, w, h):
    import numpy as np
    sh, sw = a.shape[:2]
    ys = (np.arange(h) * sh / h).astype(int)
    xs = (np.arange(w) * sw / w).astype(int)
    return a[ys][:, xs]


def compose_sheet(paths, out_path, cols, cell, bg=(0.06, 0.08, 0.11, 1.0)):
    """Grid of images, first image at top-left."""
    import numpy as np
    n = len(paths)
    rows = (n + cols - 1) // cols
    sheet = np.zeros((rows * cell, cols * cell, 4), dtype=np.float32)
    sheet[:] = bg
    for i, p in enumerate(paths):
        a = _resize_nearest(_load_px(p), cell, cell)
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * cell
        sheet[y0:y0 + cell, c * cell:(c + 1) * cell] = a
    return _save_px(sheet, out_path)


def pixelate(src, out_path, factor):
    """Downsample by `factor` (box) then upscale nearest - pixel-art read test."""
    import numpy as np
    a = _load_px(src)
    h, w = a.shape[:2]
    h2, w2 = h // factor, w // factor
    small = a[:h2 * factor, :w2 * factor].reshape(h2, factor, w2, factor, 4).mean(axis=(1, 3))
    big = np.repeat(np.repeat(small, factor, axis=0), factor, axis=1)
    return _save_px(big, out_path)


# ---------------------------------------------------------------------------
# Multi-object baking without cross-object margin bleed
# ---------------------------------------------------------------------------

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


def bake_atlas(objs, out_dir, prefix, size, dilate=16):
    """dc.bake_texture_set with bake margin 0 (Blender applies the margin per
    object, so with several objects in one image each object's margin
    overwrites its neighbours' texels), then one global dilation pass."""
    import functools
    orig = dc.bake_pass
    dc.bake_pass = functools.partial(orig, margin=0)
    try:
        paths = dc.bake_texture_set(objs, out_dir, prefix, size=size, highpoly=None)
    finally:
        dc.bake_pass = orig
    mask = uv_coverage_mask(objs, size)
    for kind, path in paths.items():
        img = next((im for im in bpy.data.images if im.filepath_raw == str(path)), None)
        if img is None:
            img = bpy.data.images.load(str(path), check_existing=True)
        dilate_image(img, mask, dilate)
        img.filepath_raw = str(path)
        img.file_format = "PNG"
        img.save()
    print(f"[env] {prefix}: texel coverage {mask.mean():.3f}, dilated {dilate}px")
    return paths
