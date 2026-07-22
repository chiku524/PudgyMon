#!/usr/bin/env python3
"""Build a procedural cartoon Pudgy character GLB via Blender (no Tripo).

Creates a game-ready soft-matte mascot matching the Pudgy contract:
~1.2 m, floor pivot, faces −Y in Blender (−Z in Bevy), A-pose, accessory sockets.

Usage:
  python scripts/build_procedural_pudgy.py
  python scripts/build_procedural_pudgy.py --asset-id char_pudgy_procedural_01
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")

_WORKER = r'''
import bpy
import math
import mathutils
from pathlib import Path

OUT_PATH = Path(r"__OUT_PATH__")
ASSET_ID = "__ASSET_ID__"
TARGET_HEIGHT = 1.2

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, roughness=0.62):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    nt = m.node_tree
    principled = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = 0.0
    if "Coat Weight" in principled.inputs:
        principled.inputs["Coat Weight"].default_value = 0.0
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.3
    m.blend_method = "OPAQUE"
    return m


def uv_sphere(name, radius, loc, mat, scale=(1, 1, 1), segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=loc, segments=segments, ring_count=rings
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.shade_smooth()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return obj


def cylinder(name, radius, depth, loc, mat, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=loc, vertices=16
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rot
    obj.scale = scale
    bpy.ops.object.shade_smooth()
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return obj


body_mat = mat("PudgyBody", (1.0, 0.72, 0.62), 0.65)
belly_mat = mat("PudgyBelly", (1.0, 0.88, 0.78), 0.7)
eye_white = mat("EyeWhite", (0.98, 0.98, 0.96), 0.45)
eye_pupil = mat("EyePupil", (0.08, 0.08, 0.1), 0.35)
cheek_mat = mat("Cheek", (1.0, 0.55, 0.55), 0.7)
snout_mat = mat("Snout", (1.0, 0.78, 0.7), 0.65)

# Build in Blender Z-up; character faces −Y (Bevy −Z after glTF).
# Proportions for a ~1.2 m dumpling mascot.
parts = []

# Body dumpling
parts.append(uv_sphere("Body", 0.38, (0, 0, 0.42), body_mat, scale=(1.05, 0.95, 0.92)))
# Soft belly patch
parts.append(uv_sphere("Belly", 0.22, (0, -0.18, 0.40), belly_mat, scale=(0.85, 0.45, 0.95), segments=20, rings=12))
# Oversized head
parts.append(uv_sphere("Head", 0.34, (0, 0.02, 0.95), body_mat, scale=(1.05, 1.0, 0.95)))
# Cheeks
parts.append(uv_sphere("CheekL", 0.09, (-0.22, -0.12, 0.90), cheek_mat, scale=(1.0, 0.85, 0.9), segments=12, rings=8))
parts.append(uv_sphere("CheekR", 0.09, (0.22, -0.12, 0.90), cheek_mat, scale=(1.0, 0.85, 0.9), segments=12, rings=8))
# Snout
parts.append(uv_sphere("Snout", 0.10, (0, -0.28, 0.88), snout_mat, scale=(1.15, 0.7, 0.75), segments=14, rings=10))

# Eyes — huge friendly cartoon whites + pupils (facing −Y)
parts.append(uv_sphere("EyeWhiteL", 0.11, (-0.12, -0.28, 1.02), eye_white, scale=(1.0, 0.55, 1.05), segments=16, rings=12))
parts.append(uv_sphere("EyeWhiteR", 0.11, (0.12, -0.28, 1.02), eye_white, scale=(1.0, 0.55, 1.05), segments=16, rings=12))
parts.append(uv_sphere("PupilL", 0.055, (-0.12, -0.34, 1.02), eye_pupil, scale=(1.0, 0.5, 1.1), segments=12, rings=8))
parts.append(uv_sphere("PupilR", 0.055, (0.12, -0.34, 1.02), eye_pupil, scale=(1.0, 0.5, 1.1), segments=12, rings=8))

# Stubby arms A-pose (slightly out)
parts.append(uv_sphere("ArmL", 0.11, (-0.42, 0.0, 0.55), body_mat, scale=(1.4, 0.85, 0.85), segments=14, rings=10))
parts.append(uv_sphere("ArmR", 0.11, (0.42, 0.0, 0.55), body_mat, scale=(1.4, 0.85, 0.85), segments=14, rings=10))
parts.append(uv_sphere("HandL", 0.09, (-0.58, 0.0, 0.52), body_mat, scale=(1.0, 0.9, 0.9), segments=12, rings=8))
parts.append(uv_sphere("HandR", 0.09, (0.58, 0.0, 0.52), body_mat, scale=(1.0, 0.9, 0.9), segments=12, rings=8))

# Stubby legs / feet
parts.append(uv_sphere("LegL", 0.12, (-0.14, 0.0, 0.14), body_mat, scale=(0.95, 0.9, 1.1), segments=14, rings=10))
parts.append(uv_sphere("LegR", 0.12, (0.14, 0.0, 0.14), body_mat, scale=(0.95, 0.9, 1.1), segments=14, rings=10))
parts.append(uv_sphere("FootL", 0.11, (-0.14, -0.06, 0.05), body_mat, scale=(1.05, 1.25, 0.55), segments=12, rings=8))
parts.append(uv_sphere("FootR", 0.11, (0.14, -0.06, 0.05), body_mat, scale=(1.05, 1.25, 0.55), segments=12, rings=8))

# Join into one mesh
bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = ASSET_ID
body.data.name = ASSET_ID
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Floor pivot + bake height
def world_aabb(obj):
    minv = mathutils.Vector((1e9, 1e9, 1e9))
    maxv = mathutils.Vector((-1e9, -1e9, -1e9))
    for corner in obj.bound_box:
        w = obj.matrix_world @ mathutils.Vector(corner)
        minv = mathutils.Vector((min(minv.x, w.x), min(minv.y, w.y), min(minv.z, w.z)))
        maxv = mathutils.Vector((max(maxv.x, w.x), max(maxv.y, w.y), max(maxv.z, w.z)))
    return minv, maxv

minv, maxv = world_aabb(body)
h = max(maxv.z - minv.z, 1e-4)
scale = TARGET_HEIGHT / h
body.scale = (scale, scale, scale)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
minv, maxv = world_aabb(body)
cx = 0.5 * (minv.x + maxv.x)
cy = 0.5 * (minv.y + maxv.y)
body.location -= mathutils.Vector((cx, cy, minv.z))
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Face +X in mesh space so the shared runtime CHARACTER_MESH_YAW_OFFSET (+90° Y)
# maps face to Bevy −Z — same convention as Tripo imports.
body.rotation_euler[2] = math.radians(90.0)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

# Accessory sockets (match polish_character_glb.py convention)
minv, maxv = world_aabb(body)
h = maxv.z - minv.z
w = maxv.x - minv.x
sockets = {
    "Socket_Hat": (0.0, 0.0, maxv.z + 0.01),
    "Socket_Necklace": (0.0, -0.05 * w, minv.z + 0.72 * h),
    "Socket_Shoes": (0.0, 0.0, 0.0),
    "Socket_Back": (0.0, 0.12 * w, minv.z + 0.62 * h),
    "Socket_Face": (0.0, -0.22 * w, minv.z + 0.82 * h),
    "Socket_Hands": (0.0, 0.0, minv.z + 0.48 * h),
}
for name, loc in sockets.items():
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.08
    empty.location = loc
    bpy.context.collection.objects.link(empty)
    empty.parent = body

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT_PATH),
    export_format="GLB",
    use_selection=False,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_yup=True,
)
print("PROCEDURAL_OK", ASSET_ID, "height", TARGET_HEIGHT)
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", default="char_pudgy_procedural_01")
    args = parser.parse_args()
    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1

    aid = args.asset_id.strip()
    dest_dir = _MODELS / aid
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{aid}.glb"
    worker = dest_dir / "_build_procedural_worker.py"
    script = (
        _WORKER.replace("__OUT_PATH__", str(out.resolve()).replace("\\", "/"))
        .replace("__ASSET_ID__", aid)
    )
    worker.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [str(_BLENDER), "--background", "--python", str(worker)],
            capture_output=True,
            text=True,
        )
    finally:
        worker.unlink(missing_ok=True)
    if proc.returncode != 0 or not out.is_file():
        print(proc.stderr[-4000:], file=sys.stderr)
        print(proc.stdout[-2000:], file=sys.stderr)
        return 1
    print(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else f"wrote {out}")
    print(f"glb -> {out.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
