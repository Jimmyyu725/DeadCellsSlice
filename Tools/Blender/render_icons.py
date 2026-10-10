"""Render inventory icons for the Armory2 kits from their baked .blend files.

  Blender -b --factory-startup -P Tools/Blender/render_icons.py

Writes Assets/_Project/Art/Icons/<Asset>.png (transparent, 64 px, outlined).
Melee weapons are shown diagonally (blade up-right), ranged weapons side-on
firing right, shields face-on, skills front-on.
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "Assets" / "_Project" / "Art" / "Icons"
KITS = {"ArmoryMelee": "melee", "ArmoryRanged": "ranged", "ArmoryGear": "gear", "Relics": "gear"}
SHIELDS = {"BellShield", "MirrorMoon", "SpikedShell", "ClockfaceBuckler", "EmberTarge", "WhalescaleTower"}
SIZE = 64


def setup_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.display.render_aa = "16"
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"
    sh.show_object_outline = True
    sh.object_outline_color = (0.02, 0.015, 0.04)
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_specular_highlight = True
    scene.view_settings.view_transform = "Standard"
    cam_data = bpy.data.cameras.new("IconCam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("IconCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def frame(cam, objs, view):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    d = (hi - lo)
    if view == "front":       # look +Y, right = +X, up = +Z
        cam.rotation_euler = Euler((math.radians(90), 0, 0))
        cam.location = c + Vector((0, -5, 0))
        extent = max(d.x, d.z)
    elif view == "side":      # look +X, right = -Y, up = +Z
        cam.rotation_euler = Euler((math.radians(90), 0, math.radians(-90)))
        cam.location = c + Vector((-5, 0, 0))
        extent = max(d.y, d.z)
    else:                     # top: look -Z, up = +Y
        cam.rotation_euler = Euler((0, 0, 0))
        cam.location = c + Vector((0, 0, 5))
        extent = max(d.x, d.y)
    cam.data.ortho_scale = extent * 1.12 + 0.02


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = next((a.split("=", 1)[1].split(",") for a in argv if a.startswith("--kits=")), None)
    for kit, mode in KITS.items():
        if only and kit not in only:
            continue
        blend = ROOT / "Tools" / "_out" / kit.lower() / f"{kit}.blend"
        if not blend.exists():
            print("[icons] missing", blend)
            continue
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        scene, cam = setup_scene()
        meshes = [o for o in scene.objects if o.type == "MESH" and o.parent is None]
        for target in meshes:
            for o in scene.objects:
                if o.type == "MESH":
                    o.hide_render = o is not target and o.parent is not target
            target.rotation_euler = (0, 0, 0)
            if mode == "melee":
                target.rotation_euler = Euler((0, math.radians(40), 0))
                view = "front"
            elif mode == "ranged":
                view = "side"
            else:
                view = "top" if target.name in SHIELDS else "front"
            bpy.context.view_layer.update()
            frame(cam, [target], view)
            scene.render.filepath = str(OUT / f"{target.name}.png")
            bpy.ops.render.render(write_still=True)
            count += 1
    print(f"[icons] rendered {count} icons to {OUT}")


if __name__ == "__main__":
    main()
