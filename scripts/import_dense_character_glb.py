#!/usr/bin/env python3
"""Import a dense Tripo/download GLB as a playable Pudgy character.

Avoids Blender Decimate (it shreds Tripo UVs → see-through textures).
Instead:
  1. Floor-pivot + ~1.2 m + accessory sockets
  2. Force opaque materials (Tripo ships HASHED alpha)
  3. Downscale / re-encode textures as JPEG (Bevy cannot use EXT_texture_webp)
  4. Strip Draco / meshopt (Bevy cannot decode KHR_draco_mesh_compression)
  5. Optional UV-aware simplify via gltf-transform (off by default)

Already-optimized Downloads (Draco+WebP ~3MB) must still be re-exported this way
or Bevy will spawn an empty / invisible mesh.

Usage:
  python scripts/import_dense_character_glb.py \\
    --src "C:/Users/.../stylized+pink+creature+3d+model.glb" \\
    --asset-id char_pudgy_pink_01
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_REGISTRY = _REPO / "assets" / "studio_registry.json"
_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")

_WORKER = r'''
import bpy
import math
import mathutils
from pathlib import Path

IN_PATH = Path(r"__IN_PATH__")
OUT_PATH = Path(r"__OUT_PATH__")
ASSET_ID = "__ASSET_ID__"
TARGET_HEIGHT = float("__TARGET_HEIGHT__")
MAX_TEX = int("__MAX_TEX__")
JPEG_QUALITY = int("__JPEG_QUALITY__")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(IN_PATH))

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("no mesh in GLB")

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

bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Never use Blender Decimate here — it wrecks Tripo UVs. Mesh size is handled
# after export by gltf-transform simplify (UV-aware meshoptimizer).
print("KEEP_FACES", len(body.data.polygons))

# Downscale textures — main GLB weight on Tripo exports (often 3× 4K).
for img in list(bpy.data.images):
    w, h = img.size
    if w <= 0 or h <= 0:
        continue
    longest = max(w, h)
    if longest > MAX_TEX:
        scale = MAX_TEX / float(longest)
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))
        print("TEX_RESIZE", img.name, f"{w}x{h}", "->", f"{nw}x{nh}")
        img.scale(nw, nh)
    img.pack()

# Force opaque cartoon materials (Tripo often ships HASHED alpha → see-through in engine).
for slot in body.material_slots:
    mat = slot.material
    if not mat:
        continue
    if hasattr(mat, "blend_method"):
        mat.blend_method = "OPAQUE"
    if hasattr(mat, "surface_render_method"):
        # Blender 4.2+ EEVEE: avoid dithered transparency paths.
        try:
            mat.surface_render_method = "DITHERED"
            # Still mark as opaque for export intent; glTF uses alphaMode.
        except Exception:
            pass
    if not getattr(mat, "use_nodes", False):
        continue
    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        continue
    if "Roughness" in principled.inputs and not principled.inputs["Roughness"].is_linked:
        principled.inputs["Roughness"].default_value = 0.62
    if "Coat Weight" in principled.inputs and not principled.inputs["Coat Weight"].is_linked:
        principled.inputs["Coat Weight"].default_value = 0.0
    if "Metallic" in principled.inputs and not principled.inputs["Metallic"].is_linked:
        principled.inputs["Metallic"].default_value = 0.0
    if "Alpha" in principled.inputs:
        # Unlink any accidental alpha map and lock fully opaque.
        for link in list(principled.inputs["Alpha"].links):
            nt.links.remove(link)
        principled.inputs["Alpha"].default_value = 1.0
    for key in ("Transmission Weight", "Transmission"):
        if key in principled.inputs and not principled.inputs[key].is_linked:
            principled.inputs[key].default_value = 0.0

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

# Ensure exporter writes opaque alphaMode.
for mat in bpy.data.materials:
    if hasattr(mat, "blend_method"):
        mat.blend_method = "OPAQUE"

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
# Blender 5.x export kwargs vary slightly — try quality if present.
export_kwargs = dict(
    filepath=str(OUT_PATH),
    export_format="GLB",
    use_selection=False,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="JPEG",
    export_yup=True,
)
try:
    bpy.ops.export_scene.gltf(**export_kwargs, export_jpeg_quality=JPEG_QUALITY)
except TypeError:
    bpy.ops.export_scene.gltf(**export_kwargs)

minv, maxv = world_aabb(body)
print("IMPORT_OK", ASSET_ID)
print("height", round(maxv.z - minv.z, 4))
print("faces", len(body.data.polygons))
print("bytes", OUT_PATH.stat().st_size)
'''


def _gltf_transform(*args: str) -> None:
    cmd = ["npx", "--yes", "@gltf-transform/cli@4.1.1", *args]
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout[-2000:])
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr[-2000:], file=sys.stderr)
        raise RuntimeError(f"gltf-transform failed: {' '.join(args[:2])}")


def _optimize_mesh(glb: Path, *, ratio: float, error: float) -> None:
    """UV-aware simplify. Bevy cannot load Draco/meshopt compression extensions."""
    weld = glb.with_name(glb.stem + "_weld.glb")
    simp = glb.with_name(glb.stem + "_simp.glb")
    try:
        _gltf_transform("weld", str(glb), str(weld))
        _gltf_transform(
            "simplify",
            str(weld),
            str(simp),
            "--ratio",
            str(ratio),
            "--error",
            str(error),
            "--lock-border",
            "true",
        )
        shutil.move(str(simp), str(glb))
    finally:
        weld.unlink(missing_ok=True)
        simp.unlink(missing_ok=True)


def _register(asset_id: str, notes: str) -> None:
    registry = {"import_root": "res://assets/models", "assets": []}
    if _REGISTRY.is_file():
        registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    by_id = {
        a["asset_id"]: a
        for a in registry.get("assets", [])
        if isinstance(a, dict) and a.get("asset_id")
    }
    by_id[asset_id] = {
        "asset_id": asset_id,
        "target_height": 1.2,
        "uniform_scale": 1.0,
        "notes": notes,
    }
    registry["assets"] = sorted(by_id.values(), key=lambda x: x["asset_id"])
    _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--height", type=float, default=1.2)
    parser.add_argument(
        "--faces",
        type=int,
        default=0,
        help="Deprecated (ignored). Mesh reduction uses --simplify-ratio instead.",
    )
    parser.add_argument(
        "--max-tex",
        type=int,
        default=1024,
        help="Longest texture edge after downscale (default 1024).",
    )
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument(
        "--simplify-ratio",
        type=float,
        default=0.0,
        help="Vertex keep ratio for UV-aware simplify (0 = skip; default). "
        "Do not use on already-optimized Tripo downloads unless needed.",
    )
    parser.add_argument(
        "--simplify-error",
        type=float,
        default=0.05,
        help="Max simplify error as fraction of mesh radius.",
    )
    parser.add_argument(
        "--notes",
        default="Imported dense creature GLB (opaque textures + UV-aware simplify).",
    )
    args = parser.parse_args()

    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1
    if not args.src.is_file():
        print(f"error: missing {args.src}", file=sys.stderr)
        return 1

    aid = args.asset_id.strip()
    dest_dir = _MODELS / aid
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"{aid}.glb"
    worker = dest_dir / "_import_dense_worker.py"
    script = (
        _WORKER.replace("__IN_PATH__", str(args.src.resolve()).replace("\\", "/"))
        .replace("__OUT_PATH__", str(out.resolve()).replace("\\", "/"))
        .replace("__ASSET_ID__", aid)
        .replace("__TARGET_HEIGHT__", str(args.height))
        .replace("__MAX_TEX__", str(args.max_tex))
        .replace("__JPEG_QUALITY__", str(args.jpeg_quality))
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

    print(proc.stdout[-4000:] if proc.stdout else "")
    if proc.returncode != 0 or not out.is_file():
        print(proc.stderr[-4000:], file=sys.stderr)
        return 1

    if args.simplify_ratio > 0:
        if shutil.which("npx") is None:
            print("error: npx required for UV-aware simplify", file=sys.stderr)
            return 1
        _optimize_mesh(out, ratio=args.simplify_ratio, error=args.simplify_error)

    (dest_dir / "README.txt").write_text(
        f"{aid}\nSource: {args.src.name}\n"
        f"Playable import (height {args.height}, textures ≤{args.max_tex}px "
        f"JPEG q{args.jpeg_quality}, opaque, simplify ratio {args.simplify_ratio}).\n",
        encoding="utf-8",
    )
    _register(aid, args.notes)
    print(f"glb -> {out.relative_to(_REPO)} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
