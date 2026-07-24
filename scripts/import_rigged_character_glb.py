#!/usr/bin/env python3
"""Import a pre-rigged / pre-animated Tripo GLB as a playable Pudgy.

Unlike import_dense_character_glb.py (static mesh → later re-rig), this keeps the
incoming Armature + NLA clips, renames locomotion to the party contract names,
adds accessory sockets, floors/scales to ~1.2 m, and re-exports Bevy-safe JPEG
(no Draco / WebP extensions).

Usage:
  python scripts/import_rigged_character_glb.py \\
    --src "C:/Users/.../water-optimized.glb" \\
    --asset-id char_pudgy_water_01 \\
    --notes "Water Pudgy — Studio rig with walk/run"
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

# Drop leftover studio/debug meshes (e.g. unbound Icosphere).
junk = [
    o
    for o in list(bpy.context.scene.objects)
    if o.type == "MESH"
    and (
        o.name.lower().startswith("ico")
        or "sphere" in o.name.lower()
        or (
            o.parent is None
            and "tripo" not in o.name.lower()
            and not o.name.startswith(ASSET_ID)
            and len(o.data.polygons) < 2000
        )
    )
]
for o in junk:
    print("DROP_JUNK", o.name, "faces", len(o.data.polygons))
    bpy.data.objects.remove(o, do_unlink=True)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
if not meshes:
    raise RuntimeError("no mesh in GLB")
if not armatures:
    raise RuntimeError("no armature in GLB — use import_dense_character_glb.py + rig_and_animate_pudgy.py")

arm = armatures[0]
arm.name = f"{ASSET_ID}_Armature"
if arm.data:
    arm.data.name = f"{ASSET_ID}_Armature"

for o in meshes:
    if o.name.startswith("tripo_") or o.name.startswith("Object_"):
        o.name = ASSET_ID
        if o.data:
            o.data.name = ASSET_ID

# Opaque cartoon materials + texture downscale.
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

for mat in bpy.data.materials:
    if hasattr(mat, "blend_method"):
        mat.blend_method = "OPAQUE"
    if not getattr(mat, "use_nodes", False):
        continue
    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        continue
    if "Alpha" in principled.inputs:
        for link in list(principled.inputs["Alpha"].links):
            nt.links.remove(link)
        principled.inputs["Alpha"].default_value = 1.0
    for key in ("Transmission Weight", "Transmission"):
        if key in principled.inputs and not principled.inputs[key].is_linked:
            principled.inputs[key].default_value = 0.0

def world_aabb(objs):
    minv = mathutils.Vector((1e9, 1e9, 1e9))
    maxv = mathutils.Vector((-1e9, -1e9, -1e9))
    for obj in objs:
        for corner in obj.bound_box:
            w = obj.matrix_world @ mathutils.Vector(corner)
            minv = mathutils.Vector(
                (min(minv.x, w.x), min(minv.y, w.y), min(minv.z, w.z))
            )
            maxv = mathutils.Vector(
                (max(maxv.x, w.x), max(maxv.y, w.y), max(maxv.z, w.z))
            )
    return minv, maxv

# Scale whole hierarchy via armature root so skins stay coherent.
bodies = meshes
minv, maxv = world_aabb(bodies)
h = max(maxv.z - minv.z, 1e-4)
scale = TARGET_HEIGHT / h
arm.scale = (scale, scale, scale)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
# Apply scale on meshes too if they are siblings (OBJECT-parented skins).
for o in meshes:
    o.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

minv, maxv = world_aabb(bodies)
cx = 0.5 * (minv.x + maxv.x)
cy = 0.5 * (minv.y + maxv.y)
delta = mathutils.Vector((cx, cy, minv.z))
arm.location -= delta
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
for o in meshes:
    if o.parent is None:
        o.location -= delta
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

minv, maxv = world_aabb(bodies)
h = maxv.z - minv.z
w = maxv.x - minv.x
d = maxv.y - minv.y
cx = (minv.x + maxv.x) * 0.5
cy = (minv.y + maxv.y) * 0.5

# --- Rename locomotion NLA tracks to party clip names ---
if arm.animation_data is None:
    arm.animation_data_create()

tracks = list(arm.animation_data.nla_tracks)
# Length heuristic (longest → shortest) mapped to party contract names.
# Studio packs vary: 5 clips ≈ idle/emote/jump/walk/run; 3 ≈ idle/walk/run.
strips_meta = []
for t in tracks:
    for s in t.strips:
        length = max(1.0, float(s.frame_end) - float(s.frame_start))
        strips_meta.append((length, t, s))
strips_meta.sort(key=lambda x: -x[0])

_CONTRACT_BY_COUNT = {
    1: ("walk",),
    2: ("walk", "run"),
    3: ("idle", "walk", "run"),
    4: ("idle", "jump", "walk", "run"),
    5: ("idle", "emote_wave", "jump", "walk", "run"),
    6: ("idle", "emote_dance", "emote_wave", "jump", "walk", "run"),
}
names = _CONTRACT_BY_COUNT.get(
    len(strips_meta),
    ("idle", "emote_dance", "emote_wave", "jump", "walk", "run")[: len(strips_meta)],
)
rename_plan = {}
for name, (length, track, _strip) in zip(names, strips_meta):
    rename_plan[track.name] = name
    print("MAP_CLIP", track.name, f"len={length:.0f}", "->", name)

for t in tracks:
    new_name = rename_plan.get(t.name)
    if not new_name:
        continue
    print("RENAME_CLIP", t.name, "->", new_name)
    t.name = new_name
    for s in t.strips:
        s.name = new_name
        if s.action:
            s.action.name = new_name

def zero_root_motion_location(action, bone_names=("Root", "Hip", "Pelvis", "Hips")):
    """Strip translational root motion so walk/run stay in-place under the player entity."""
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in list(bag.fcurves):
                        if "location" not in fc.data_path:
                            continue
                        if not any(
                            f'["{b}"]' in fc.data_path or f"['{b}']" in fc.data_path
                            for b in bone_names
                        ):
                            continue
                        for kp in fc.keyframe_points:
                            kp.co[1] = 0.0
                            kp.handle_left[1] = 0.0
                            kp.handle_right[1] = 0.0
                        print("ZERO_ROOT_LOC", action.name, fc.data_path, fc.array_index)
    except Exception as err:
        print("ZERO_ROOT_LOC_ERR", action.name, err)

for clip_name in ("walk", "run", "jump", "idle", "emote_wave", "emote_dance"):
    action = bpy.data.actions.get(clip_name)
    if action:
        zero_root_motion_location(action)

# Clear pose + mute strips so floor pivot uses bind pose, not a mid-stride offset.
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.select_all(action="SELECT")
bpy.ops.pose.transforms_clear()
bpy.ops.object.mode_set(mode="OBJECT")
if arm.animation_data:
    for t in arm.animation_data.nla_tracks:
        t.mute = True
    arm.animation_data.action = None
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()

# Re-floor / re-center after stripping root motion (Studio clips often leave the
# bind pose a meter off the entity origin).
minv, maxv = world_aabb(bodies)
cx = 0.5 * (minv.x + maxv.x)
cy = 0.5 * (minv.y + maxv.y)
delta = mathutils.Vector((cx, cy, minv.z))
print("BIND_RECENTER", tuple(round(x, 4) for x in delta))
arm.location -= delta
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
for o in bpy.context.scene.objects:
    if o.parent is None and o != arm:
        o.location -= delta
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Unmute NLA for export.
if arm.animation_data:
    for t in arm.animation_data.nla_tracks:
        t.mute = False

# Final sweep — Studio downloads sometimes leave helper spheres that survive
# earlier cleanup and wreck floor pivots / Bevy bounds.
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name != ASSET_ID and not o.name.startswith(ASSET_ID):
        print("DROP_PRE_EXPORT", o.name)
        bpy.data.objects.remove(o, do_unlink=True)
for block in list(bpy.data.meshes):
    if block.users == 0:
        bpy.data.meshes.remove(block)

existing = {t.name for t in arm.animation_data.nla_tracks}

def ensure_hold_clip(name: str, frames: int = 24):
    if name in existing:
        return
    # Rest-pose hold so missing contract clips still resolve.
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.transforms_clear()
    action = bpy.data.actions.new(name=name)
    # Blender 5 layered actions: assign via NLA strip after keying with old API fallback.
    arm.animation_data.action = action
    bpy.context.scene.frame_set(1)
    try:
        bpy.ops.anim.keyframe_insert_by_name(type="LocRotScale")
    except Exception:
        for pb in arm.pose.bones:
            pb.keyframe_insert(data_path="location", frame=1)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=1)
            pb.keyframe_insert(data_path="scale", frame=1)
    bpy.context.scene.frame_set(frames)
    try:
        bpy.ops.anim.keyframe_insert_by_name(type="LocRotScale")
    except Exception:
        for pb in arm.pose.bones:
            pb.keyframe_insert(data_path="location", frame=frames)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=frames)
            pb.keyframe_insert(data_path="scale", frame=frames)
    arm.animation_data.action = None
    bpy.ops.object.mode_set(mode="OBJECT")
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, action)
    strip.frame_start = 1
    strip.frame_end = frames
    strip.action_frame_start = 1
    strip.action_frame_end = frames
    existing.add(name)
    print("SYNTH_CLIP", name, frames)

ensure_hold_clip("idle", 48)
# Optional contract clips — runtime falls back to idle if export skips these.
for clip_name, nframes in (("jump", 15), ("emote_wave", 30), ("emote_dance", 24)):
    ensure_hold_clip(clip_name, nframes)

arm.animation_data.action = None

# Accessory sockets parented to closest contract-ish bones.
bone_names = {b.name for b in arm.data.bones}

def pick_bone(*candidates):
    for c in candidates:
        if c in bone_names:
            return c
    return "Root" if "Root" in bone_names else next(iter(bone_names))

socket_bones = {
    "Socket_Hat": pick_bone("Head"),
    "Socket_Face": pick_bone("Head"),
    "Socket_Necklace": pick_bone("Spine02", "Spine01", "Waist", "NeckTwist01"),
    "Socket_Back": pick_bone("Spine02", "Spine01", "Waist"),
    "Socket_Hands": pick_bone("Spine01", "Waist", "Spine02"),
    "Socket_Shoes": pick_bone("Root", "Hip", "Pelvis"),
}
socket_local = {
    "Socket_Hat": (0.0, 0.0, 0.12),
    "Socket_Face": (0.0, -0.08, 0.02),
    "Socket_Necklace": (0.0, -0.04, 0.06),
    "Socket_Back": (0.0, 0.08, 0.0),
    "Socket_Hands": (0.0, 0.0, 0.0),
    "Socket_Shoes": (0.0, 0.0, 0.0),
}

def parent_to_bone(obj, armature, bone_name):
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.location = mathutils.Vector(socket_local[obj.name])
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)

for sname, bname in socket_bones.items():
    if sname in bpy.data.objects:
        continue
    empty = bpy.data.objects.new(sname, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.08
    bpy.context.scene.collection.objects.link(empty)
    parent_to_bone(empty, arm, bname)
    print("SOCKET", sname, "->", bname)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
export_kwargs = dict(
    filepath=str(OUT_PATH),
    export_format="GLB",
    use_selection=False,
    export_apply=False,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="JPEG",
    export_yup=True,
    export_skins=True,
    export_animations=True,
    export_nla_strips=True,
    export_def_bones=False,
    export_optimize_animation_size=True,
)
try:
    bpy.ops.export_scene.gltf(**export_kwargs, export_jpeg_quality=JPEG_QUALITY)
except TypeError:
    for drop in ("export_nla_strips", "export_optimize_animation_size", "export_def_bones"):
        export_kwargs.pop(drop, None)
    bpy.ops.export_scene.gltf(**export_kwargs)

minv, maxv = world_aabb(bodies)
print("IMPORT_OK", ASSET_ID)
print("height", round(maxv.z - minv.z, 4))
print("faces", sum(len(o.data.polygons) for o in bodies))
print("clips", [t.name for t in arm.animation_data.nla_tracks])
print("bytes", OUT_PATH.stat().st_size)
'''


def _gltf_transform(*args: str) -> None:
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        candidate = Path(r"C:\Program Files\nodejs\npx.cmd")
        npx = str(candidate) if candidate.is_file() else None
    if not npx:
        raise RuntimeError("npx not found on PATH")
    cmd = [npx, "--yes", "@gltf-transform/cli@4.1.1", *args]
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if proc.stdout:
        print(proc.stdout[-2000:])
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr[-2000:], file=sys.stderr)
        raise RuntimeError(f"gltf-transform failed: {' '.join(args[:2])}")


def _optimize_mesh(glb: Path, *, ratio: float, error: float) -> None:
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


def _register(asset_id: str, notes: str, *, height: float, uniform_scale: float = 1.0) -> None:
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
        "target_height": float(height),
        "uniform_scale": float(uniform_scale),
        "notes": notes,
    }
    registry["assets"] = sorted(by_id.values(), key=lambda x: x["asset_id"])
    _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--height", type=float, default=1.2)
    parser.add_argument("--max-tex", type=int, default=1024)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument(
        "--simplify-ratio",
        type=float,
        default=0.35,
        help="Vertex keep ratio after import (default 0.35 ≈ pink crew density).",
    )
    parser.add_argument("--simplify-error", type=float, default=0.05)
    parser.add_argument("--notes", default="Imported rigged creature GLB (walk/run preserved).")
    args = parser.parse_args()

    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1
    if not args.src.is_file():
        print(f"error: missing source {args.src}", file=sys.stderr)
        return 1

    out_dir = _MODELS / args.asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_glb = out_dir / f"{args.asset_id}.glb"
    worker = (
        _WORKER.replace("__IN_PATH__", str(args.src.resolve()).replace("\\", "\\\\"))
        .replace("__OUT_PATH__", str(out_glb.resolve()).replace("\\", "\\\\"))
        .replace("__ASSET_ID__", args.asset_id)
        .replace("__TARGET_HEIGHT__", str(args.height))
        .replace("__MAX_TEX__", str(args.max_tex))
        .replace("__JPEG_QUALITY__", str(args.jpeg_quality))
    )
    script_path = out_dir / "_import_rigged_worker.py"
    script_path.write_text(worker, encoding="utf-8")

    cmd = [str(_BLENDER), "--background", "--python", str(script_path)]
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    print(proc.stdout[-4000:] if proc.stdout else "")
    if proc.returncode != 0:
        print(proc.stderr[-4000:] if proc.stderr else "", file=sys.stderr)
        return proc.returncode

    if args.simplify_ratio > 0:
        print(f"simplify ratio={args.simplify_ratio}")
        _optimize_mesh(out_glb, ratio=args.simplify_ratio, error=args.simplify_error)

    readme = out_dir / "README.txt"
    readme.write_text(
        f"{args.asset_id}\n"
        f"Source: {args.src.name}\n"
        f"{args.notes}\n"
        "Rebuild: python scripts/import_rigged_character_glb.py "
        f'--src "<src>" --asset-id {args.asset_id}\n',
        encoding="utf-8",
    )
    _register(args.asset_id, args.notes, height=args.height, uniform_scale=1.0)
    script_path.unlink(missing_ok=True)
    print("DONE", out_glb, "bytes", out_glb.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
