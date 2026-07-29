#!/usr/bin/env python3
"""Bind a static Tripo mesh onto an existing Studio 41-bone crew armature + clips.

Copies skin weights from the donor mesh (nearest-face transfer) so dense Tripo
bodies skip Blender heat-weight failures, then keeps the donor NLA locomotion.

  python scripts/bind_mesh_to_studio_rig.py \\
    --mesh "C:/Downloads/sky-static.glb" \\
    --donor char_pudgy_lava_01 \\
    --asset-id char_pudgy_sky_01 \\
    --notes "Sky Pudgy — Studio skeleton + lava locomotion"
"""

from __future__ import annotations

import argparse
import importlib.util
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

MESH_PATH = Path(r"__MESH_PATH__")
DONOR_PATH = Path(r"__DONOR_PATH__")
OUT_PATH = Path(r"__OUT_PATH__")
ASSET_ID = "__ASSET_ID__"
TARGET_HEIGHT = float("__TARGET_HEIGHT__")
MAX_TEX = int("__MAX_TEX__")
JPEG_QUALITY = int("__JPEG_QUALITY__")

bpy.ops.wm.read_factory_settings(use_empty=True)

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

# --- Donor: keep armature + skinned mesh (weights) + NLA ---
bpy.ops.import_scene.gltf(filepath=str(DONOR_PATH))
donor_meshes = [o for o in list(bpy.context.scene.objects) if o.type == "MESH"]
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
if not arms:
    raise RuntimeError(f"no armature in donor {DONOR_PATH}")
if not donor_meshes:
    raise RuntimeError(f"no mesh in donor {DONOR_PATH} (need skin weights to transfer)")
arm = arms[0]
arm.name = f"{ASSET_ID}_Armature"
if arm.data:
    arm.data.name = f"{ASSET_ID}_Armature"
donor_meshes.sort(key=lambda o: len(o.data.polygons), reverse=True)
donor_body = donor_meshes[0]
donor_body.name = "_donor_skin_source"
for o in donor_meshes[1:]:
    print("DROP_DONOR_EXTRA", o.name, "faces", len(o.data.polygons))
    bpy.data.objects.remove(o, do_unlink=True)

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

dmin, dmax = world_aabb([donor_body])
donor_h = max(dmax.z - dmin.z, 1e-4)
donor_scale = TARGET_HEIGHT / donor_h
if abs(donor_scale - 1.0) > 0.05:
    arm.scale = (donor_scale, donor_scale, donor_scale)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    donor_body.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
dmin, dmax = world_aabb([donor_body])
delta = mathutils.Vector(
    (0.5 * (dmin.x + dmax.x), 0.5 * (dmin.y + dmax.y), dmin.z)
)
arm.location -= delta
if donor_body.parent is None:
    donor_body.location -= delta
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
if donor_body.parent is None:
    donor_body.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
dmin, dmax = world_aabb([donor_body])
print(
    "DONOR_AABB",
    tuple(round(x, 3) for x in (dmax - dmin)),
    "groups",
    len(donor_body.vertex_groups),
)

# --- Incoming static body ---
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(MESH_PATH))
added = [o for o in bpy.context.scene.objects if o not in before]
for o in list(added):
    if o.type == "ARMATURE":
        print("DROP_MESH_ARMATURE", o.name)
        bpy.data.objects.remove(o, do_unlink=True)
meshes = [
    o for o in bpy.context.scene.objects if o.type == "MESH" and o != donor_body
]
if not meshes:
    raise RuntimeError(f"no mesh in {MESH_PATH}")
meshes.sort(key=lambda o: len(o.data.polygons), reverse=True)
body = meshes[0]
for o in meshes[1:]:
    print("DROP_EXTRA_MESH", o.name, "faces", len(o.data.polygons))
    bpy.data.objects.remove(o, do_unlink=True)
body.name = ASSET_ID
if body.data:
    body.data.name = ASSET_ID

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

# Match body to donor AABB so nearest-face weight transfer lands.
minv, maxv = world_aabb([body])
bh = max(maxv.z - minv.z, 1e-4)
dh = max(dmax.z - dmin.z, 1e-4)
scale = dh / bh
body.scale = (scale, scale, scale)
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
minv, maxv = world_aabb([body])
body.location += mathutils.Vector(
    (
        0.5 * (dmin.x + dmax.x) - 0.5 * (minv.x + maxv.x),
        0.5 * (dmin.y + dmax.y) - 0.5 * (minv.y + maxv.y),
        dmin.z - minv.z,
    )
)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
minv, maxv = world_aabb([body])
print("BODY_AABB", tuple(round(x, 3) for x in (maxv - minv)))

for mod in list(body.modifiers):
    body.modifiers.remove(mod)
body.vertex_groups.clear()
body.parent = None

xfer = body.modifiers.new(name="WeightXfer", type="DATA_TRANSFER")
xfer.object = donor_body
xfer.use_vert_data = True
xfer.data_types_verts = {"VGROUP_WEIGHTS"}
xfer.vert_mapping = "POLYINTERP_NEAREST"
xfer.layers_vgroup_select_src = "ALL"
xfer.mix_mode = "REPLACE"
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.datalayout_transfer(modifier=xfer.name)
bpy.ops.object.modifier_apply(modifier=xfer.name)

body.parent = arm
body.parent_type = "OBJECT"
arm_mod = body.modifiers.new(name="Armature", type="ARMATURE")
arm_mod.object = arm
arm_mod.use_vertex_groups = True

weighted = sum(
    1 for v in body.data.vertices if any(g.weight > 1e-6 for g in v.groups)
)
print(
    "BOUND",
    body.name,
    "->",
    arm.name,
    "groups",
    len(body.vertex_groups),
    "weighted_verts",
    weighted,
    "/",
    len(body.data.vertices),
)
if weighted < max(100, len(body.data.vertices) // 20):
    raise RuntimeError(
        f"weight transfer failed ({weighted} weighted verts) — mesh may not overlap donor"
    )

print("DROP_DONOR_MESH", donor_body.name, "faces", len(donor_body.data.polygons))
bpy.data.objects.remove(donor_body, do_unlink=True)
for block in list(bpy.data.meshes):
    if block.users == 0:
        bpy.data.meshes.remove(block)

if arm.animation_data:
    for t in arm.animation_data.nla_tracks:
        t.mute = False
    arm.animation_data.action = None

existing = {t.name for t in (arm.animation_data.nla_tracks if arm.animation_data else [])}

def ensure_hold_clip(name: str, frames: int = 24):
    if name in existing:
        return
    if arm.animation_data is None:
        arm.animation_data_create()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.transforms_clear()
    action = bpy.data.actions.new(name=name)
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

for clip_name, nframes in (
    ("idle", 48),
    ("walk", 24),
    ("run", 16),
    ("jump", 15),
    ("emote_wave", 30),
    ("emote_dance", 24),
):
    ensure_hold_clip(clip_name, nframes)

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

for sname, bname in socket_bones.items():
    if sname in bpy.data.objects:
        continue
    empty = bpy.data.objects.new(sname, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.08
    bpy.context.scene.collection.objects.link(empty)
    empty.parent = arm
    empty.parent_type = "BONE"
    empty.parent_bone = bname
    empty.location = mathutils.Vector(socket_local[sname])
    empty.rotation_euler = (0, 0, 0)
    empty.scale = (1, 1, 1)
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
    export_optimize_animation_size=False,
)
try:
    bpy.ops.export_scene.gltf(**export_kwargs, export_jpeg_quality=JPEG_QUALITY)
except TypeError:
    for drop in ("export_nla_strips", "export_optimize_animation_size", "export_def_bones"):
        export_kwargs.pop(drop, None)
    bpy.ops.export_scene.gltf(**export_kwargs)

minv, maxv = world_aabb([body])
print("BIND_OK", ASSET_ID)
print("height", round(maxv.z - minv.z, 4))
print("faces", len(body.data.polygons))
print("clips", [t.name for t in arm.animation_data.nla_tracks])
print("vgroups", len(body.vertex_groups))
print("weighted_verts", weighted)
print("bytes", OUT_PATH.stat().st_size)
'''


def _optimize_mesh(glb: Path, *, ratio: float, error: float, max_tex: int) -> None:
    opt_path = Path(__file__).resolve().parent / "optimize_glb.py"
    spec = importlib.util.spec_from_file_location("optimize_glb", opt_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {opt_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.optimize_file(
        glb,
        preset="game",
        ratio=ratio,
        error=error,
        max_tex=max_tex,
        backup=False,
    )


def _register(asset_id: str, notes: str, *, height: float) -> None:
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
        "uniform_scale": 1.0,
        "notes": notes,
    }
    registry["assets"] = sorted(by_id.values(), key=lambda x: x["asset_id"])
    _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True, help="Static Tripo body GLB")
    parser.add_argument(
        "--donor",
        required=True,
        help="Crew asset id with Studio 41-bone rig + clips (e.g. char_pudgy_lava_01)",
    )
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--height", type=float, default=1.2)
    parser.add_argument("--max-tex", type=int, default=1024)
    parser.add_argument("--jpeg-quality", type=int, default=90)
    parser.add_argument("--simplify-ratio", type=float, default=0.25)
    parser.add_argument("--simplify-error", type=float, default=0.010)
    parser.add_argument(
        "--notes",
        default="Static mesh bound to Studio 41-bone donor armature + clips.",
    )
    args = parser.parse_args()

    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1
    if not args.mesh.is_file():
        print(f"error: missing mesh {args.mesh}", file=sys.stderr)
        return 1
    donor_glb = _MODELS / args.donor / f"{args.donor}.glb"
    if not donor_glb.is_file():
        print(f"error: missing donor {donor_glb}", file=sys.stderr)
        return 1

    out_dir = _MODELS / args.asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_glb = out_dir / f"{args.asset_id}.glb"
    if out_glb.is_file() and not (out_dir / f"{args.asset_id}.glb.stubby_bak").is_file():
        shutil.copy2(out_glb, out_dir / f"{args.asset_id}.glb.stubby_bak")

    worker = (
        _WORKER.replace("__MESH_PATH__", str(args.mesh.resolve()).replace("\\", "\\\\"))
        .replace("__DONOR_PATH__", str(donor_glb.resolve()).replace("\\", "\\\\"))
        .replace("__OUT_PATH__", str(out_glb.resolve()).replace("\\", "\\\\"))
        .replace("__ASSET_ID__", args.asset_id)
        .replace("__TARGET_HEIGHT__", str(args.height))
        .replace("__MAX_TEX__", str(args.max_tex))
        .replace("__JPEG_QUALITY__", str(args.jpeg_quality))
    )
    script_path = out_dir / "_bind_studio_worker.py"
    script_path.write_text(worker, encoding="utf-8")

    cmd = [str(_BLENDER), "--background", "--python", str(script_path)]
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    print(proc.stdout[-6000:] if proc.stdout else "")
    if proc.returncode != 0:
        print(proc.stderr[-4000:] if proc.stderr else "", file=sys.stderr)
        return proc.returncode

    if args.simplify_ratio > 0:
        print(f"simplify ratio={args.simplify_ratio} max_tex={args.max_tex}")
        _optimize_mesh(
            out_glb,
            ratio=args.simplify_ratio,
            error=args.simplify_error,
            max_tex=args.max_tex,
        )

    (out_dir / "README.txt").write_text(
        f"{args.asset_id}\n"
        f"Mesh: {args.mesh.name}\n"
        f"Donor rig/clips: {args.donor}\n"
        f"{args.notes}\n"
        "Rebuild: python scripts/bind_mesh_to_studio_rig.py "
        f'--mesh "<mesh>" --donor {args.donor} --asset-id {args.asset_id}\n',
        encoding="utf-8",
    )
    _register(args.asset_id, args.notes, height=args.height)
    script_path.unlink(missing_ok=True)
    print("DONE", out_glb, "bytes", out_glb.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
