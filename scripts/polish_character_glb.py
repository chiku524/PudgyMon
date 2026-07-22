#!/usr/bin/env python3
"""
Polish a Pudgy character GLB via Blender (headless).

- Floor-pivot (feet at ground)
- Upright on +Z in Blender (= +Y in glTF / Bevy)
- Face −Y in Blender (= −Z Bevy forward)
- Bake playable height (~1.2 m)
- Rename mesh, tidy Principled BSDF for candy/rubber look
- Add accessory socket empties (hat / necklace / shoes / back / face / hands)

Usage:
  python scripts/polish_character_glb.py char_pudgy_base_01
  python scripts/polish_character_glb.py oceanic_pudgymon_01 --height 1.2
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"

_BLENDER_CANDIDATES = [
    Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
    Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"),
    Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
]


def _find_blender() -> Path:
    for p in _BLENDER_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError("Blender executable not found")


_WORKER = r'''
import bpy
import math
import mathutils
from pathlib import Path

IN_PATH = Path(r"__IN_PATH__")
OUT_PATH = Path(r"__OUT_PATH__")
ASSET_ID = "__ASSET_ID__"
TARGET_HEIGHT = float("__TARGET_HEIGHT__")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(IN_PATH))

# Collect mesh objects (skip cameras/lights)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("no mesh in GLB")

# Join into one mesh for a clean character root
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = ASSET_ID
if body.data:
    body.data.name = ASSET_ID

# Apply object transforms into mesh data
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def world_aabb(obj):
    minv = mathutils.Vector((1e9, 1e9, 1e9))
    maxv = mathutils.Vector((-1e9, -1e9, -1e9))
    for corner in obj.bound_box:
        w = obj.matrix_world @ mathutils.Vector(corner)
        minv = mathutils.Vector((min(minv.x, w.x), min(minv.y, w.y), min(minv.z, w.z)))
        maxv = mathutils.Vector((max(maxv.x, w.x), max(maxv.y, w.y), max(maxv.z, w.z)))
    return minv, maxv

minv, maxv = world_aabb(body)
size = maxv - minv
# Upright axis = largest extent
axes = [("X", size.x), ("Y", size.y), ("Z", size.z)]
up_axis = max(axes, key=lambda t: t[1])[0]

# Rotate so upright becomes +Z (Blender up → glTF/Bevy +Y)
if up_axis == "Y":
    body.rotation_euler = (math.radians(90.0), 0.0, 0.0)
elif up_axis == "X":
    body.rotation_euler = (0.0, 0.0, math.radians(-90.0))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    body.rotation_euler = (math.radians(90.0), 0.0, 0.0)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

minv, maxv = world_aabb(body)
size = maxv - minv
height = max(size.z, 1e-6)

# Scale to target playable height
s = TARGET_HEIGHT / height
body.scale = (s, s, s)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

minv, maxv = world_aabb(body)
# Floor pivot: feet at Z=0, center X/Y
offset = mathutils.Vector((
    -((minv.x + maxv.x) * 0.5),
    -((minv.y + maxv.y) * 0.5),
    -minv.z,
))
body.location = offset
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Face −Y in Blender (= −Z Bevy forward). Raw Tripo faces −X after upright;
# +90° around Z maps −X → −Y. Runtime also applies CHARACTER_MESH_YAW_OFFSET.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
body.rotation_euler = (0.0, 0.0, math.radians(90.0))
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
minv, maxv = world_aabb(body)
body.location = mathutils.Vector((
    -((minv.x + maxv.x) * 0.5),
    -((minv.y + maxv.y) * 0.5),
    -minv.z,
))
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Material polish — rubbery candy toy
for slot in body.material_slots:
    mat = slot.material
    if not mat:
        continue
    mat.name = f"{ASSET_ID}_mat"
    if not getattr(mat, "use_nodes", True):
        continue
    nt = mat.node_tree
    if not nt:
        continue
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        continue
    # Vinyl / designer-toy plastic (finer pass: scripts/vinyl_material_pass.py)
    if "Roughness" in principled.inputs and not principled.inputs["Roughness"].is_linked:
        principled.inputs["Roughness"].default_value = 0.22
    if "Coat Weight" in principled.inputs and not principled.inputs["Coat Weight"].is_linked:
        principled.inputs["Coat Weight"].default_value = 0.45
    if "Coat Roughness" in principled.inputs and not principled.inputs["Coat Roughness"].is_linked:
        principled.inputs["Coat Roughness"].default_value = 0.12
    if "Specular IOR Level" in principled.inputs and not principled.inputs["Specular IOR Level"].is_linked:
        principled.inputs["Specular IOR Level"].default_value = 0.5
    elif "Specular" in principled.inputs and not principled.inputs["Specular"].is_linked:
        principled.inputs["Specular"].default_value = 0.5
    if "Metallic" in principled.inputs and not principled.inputs["Metallic"].is_linked:
        principled.inputs["Metallic"].default_value = 0.0
    if "Alpha" in principled.inputs and not principled.inputs["Alpha"].is_linked:
        principled.inputs["Alpha"].default_value = 1.0
    mat.blend_method = "OPAQUE"

# Accessory sockets (local Z-up character space, meters)
minv, maxv = world_aabb(body)
h = maxv.z - minv.z
w = maxv.x - minv.x
d = maxv.y - minv.y
cx = (minv.x + maxv.x) * 0.5
cy = (minv.y + maxv.y) * 0.5

sockets = {
    "Socket_Hat": (cx, cy, maxv.z * 0.98),
    "Socket_Necklace": (cx, cy - d * 0.05, h * 0.62),
    "Socket_Shoes": (cx, cy, 0.02),
    "Socket_Back": (cx, cy + d * 0.35, h * 0.55),
    "Socket_Face": (cx, cy - d * 0.42, h * 0.78),
    "Socket_Hands": (cx, cy, h * 0.42),
}

# Parent sockets under an empty root so Bevy can find them beside the mesh
root = bpy.data.objects.new(f"{ASSET_ID}_Root", None)
bpy.context.scene.collection.objects.link(root)

def parent_keep(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw

parent_keep(body, root)

for name, loc in sockets.items():
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.08
    empty.location = loc
    bpy.context.scene.collection.objects.link(empty)
    parent_keep(empty, root)

# Export
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT_PATH),
    export_format="GLB",
    use_selection=False,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_yup=True,
)

minv, maxv = world_aabb(body)
print("POLISH_OK", ASSET_ID)
print("height", round(maxv.z - minv.z, 4))
print("feet_z", round(minv.z, 4))
print("center_xy", round((minv.x+maxv.x)*0.5, 4), round((minv.y+maxv.y)*0.5, 4))
'''


def polish(asset_id: str, height: float, blender: Path) -> int:
    folder = _MODELS / asset_id
    glb = folder / f"{asset_id}.glb"
    if not glb.is_file():
        print(f"error: missing {glb}", file=sys.stderr)
        return 1

    backup = folder / f"{asset_id}.pre_polish.glb"
    if not backup.is_file():
        shutil.copy2(glb, backup)
        print(f"backup -> {backup.relative_to(_REPO)}")
    else:
        shutil.copy2(backup, glb)
        print(f"restored source -> {backup.name}")

    out_tmp = folder / f"{asset_id}.polished.glb"
    script = _WORKER
    script = script.replace("__IN_PATH__", str(glb.resolve()).replace("\\", "/"))
    script = script.replace("__OUT_PATH__", str(out_tmp.resolve()).replace("\\", "/"))
    script = script.replace("__ASSET_ID__", asset_id)
    script = script.replace("__TARGET_HEIGHT__", str(height))

    worker_path = folder / "_polish_worker.py"
    worker_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [str(blender), "--background", "--python", str(worker_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        if worker_path.is_file():
            worker_path.unlink()

    # Surface useful lines
    for line in (proc.stdout or "").splitlines():
        if line.startswith("POLISH_OK") or line.startswith("height") or line.startswith("feet") or line.startswith("center"):
            print(line)
    if proc.returncode != 0 or not out_tmp.is_file():
        print(proc.stdout[-4000:] if proc.stdout else "", file=sys.stderr)
        print(proc.stderr[-4000:] if proc.stderr else "", file=sys.stderr)
        print(f"error: Blender polish failed for {asset_id}", file=sys.stderr)
        return 1

    out_tmp.replace(glb)
    print(f"polished -> {glb.relative_to(_REPO)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_ids", nargs="+", help="asset folder / glb basename(s)")
    parser.add_argument("--height", type=float, default=1.2, help="baked playable height meters")
    parser.add_argument("--blender", type=Path, default=None, help="path to blender.exe")
    args = parser.parse_args()

    blender = args.blender or _find_blender()
    print(f"using {blender}")
    rc = 0
    for aid in args.asset_ids:
        rc = polish(aid.strip(), args.height, blender) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
