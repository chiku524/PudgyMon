#!/usr/bin/env python3
"""Blender inner script: weld-by-distance, then decimate toward a face budget.

Invoked as:
  blender --background --python this.py -- <src.glb> <dst.glb> <target_faces>
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


def _mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _total_faces(meshes) -> int:
    return sum(len(o.data.polygons) for o in meshes)


def _ensure_object_mode(obj) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def _weld_and_decimate(obj, target_faces: int, *, weld_eps: float = 0.0005) -> None:
    _ensure_object_mode(obj)
    n0 = len(obj.data.polygons)
    v0 = len(obj.data.vertices)
    print(f"start {obj.name}: faces={n0} verts={v0}")

    has_skin = bool(obj.vertex_groups) or any(
        m.type == "ARMATURE" for m in obj.modifiers
    )

    # Tripo static props are often fully split (unique verts per corner). Merge
    # by distance so Decimate can collapse. Skip weld on skinned meshes — it
    # can scramble joint weights.
    if not has_skin:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        try:
            bpy.ops.mesh.remove_doubles(threshold=weld_eps)
        except TypeError:
            bpy.ops.mesh.remove_doubles(merge_distance=weld_eps)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        print(
            f"weld {obj.name}: faces={len(obj.data.polygons)} "
            f"verts={len(obj.data.vertices)}"
        )
    else:
        print(f"skip weld {obj.name}: skinned mesh")

    n = len(obj.data.polygons)
    if n <= target_faces:
        print(f"skip decimate {obj.name}: already {n} <= {target_faces}")
        return

    ratio = max(0.02, min(0.95, target_faces / max(1, n)))
    mod = obj.modifiers.new(name="DecimateCollapse", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(
        f"decimate {obj.name}: {n} -> {len(obj.data.polygons)} "
        f"(ratio={ratio:.4f}, target={target_faces})"
    )

    # Second pass if still well over budget (static meshes only).
    n = len(obj.data.polygons)
    if (not has_skin) and n > int(target_faces * 1.25):
        ratio = max(0.02, min(0.95, target_faces / max(1, n)))
        mod = obj.modifiers.new(name="DecimateCollapse2", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"decimate2 {obj.name}: -> {len(obj.data.polygons)}")

    _ensure_object_mode(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def main() -> None:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]
    src, dst, faces_s = argv[0], argv[1], argv[2]
    target_faces = int(faces_s)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)

    meshes = _mesh_objects()
    if not meshes:
        raise SystemExit("no mesh objects imported")

    total_before = _total_faces(meshes)
    print(f"DECIMATE_IN faces={total_before} target={target_faces} meshes={len(meshes)}")

    for obj in meshes:
        n = len(obj.data.polygons)
        share = max(400, int(target_faces * (n / max(1, total_before))))
        _weld_and_decimate(obj, share)

    total_after = _total_faces(meshes)
    print(f"DECIMATE_OUT faces={total_after}")

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    try:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_morph=True,
            export_apply=True,
        )
    except TypeError:
        bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB")
    print(f"DECIMATE_WROTE {dst}")


if __name__ == "__main__":
    main()
