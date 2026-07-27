#!/usr/bin/env python3
"""Blender inner script: UV-safe decimate (no weld) + optional toon material tweak.

Invoked as:
  blender --background --python this.py -- <src.glb> <dst.glb> <target_faces> [toon=0|1]
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


def _decimate_uv_safe(obj, target_faces: int) -> None:
    """Collapse-decimate only — never weld / never recalc normals.

    Tripo meshes are split-vertex; welding by position merges different UVs and
    produces muddy clay-looking textures. Prefer a higher face count over weld.
    """
    _ensure_object_mode(obj)
    n0 = len(obj.data.polygons)
    print(f"start {obj.name}: faces={n0} verts={len(obj.data.vertices)}")

    if n0 <= target_faces:
        print(f"skip decimate {obj.name}: already {n0} <= {target_faces}")
        return

    # Soft first pass — Decimate preserves UVs when we do not weld first.
    ratio = max(0.08, min(0.95, target_faces / max(1, n0)))
    mod = obj.modifiers.new(name="DecimateCollapse", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    # Keep UV seams / borders from dissolving when possible.
    if hasattr(mod, "use_symmetry"):
        mod.use_symmetry = False
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(
        f"decimate {obj.name}: {n0} -> {len(obj.data.polygons)} "
        f"(ratio={ratio:.4f}, target={target_faces})"
    )

    # Optional mild second pass if still far over — stop early to protect UVs.
    n = len(obj.data.polygons)
    if n > int(target_faces * 1.6):
        ratio = max(0.15, min(0.95, target_faces / max(1, n)))
        mod = obj.modifiers.new(name="DecimateCollapse2", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"decimate2 {obj.name}: -> {len(obj.data.polygons)}")


def _toon_materials() -> None:
    """Steer Tripo PBR away from clay/vinyl toward painted cartoon."""
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.node_tree:
                continue
            nt = mat.node_tree
            principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if not principled:
                continue

            # Flatten micro-detail so it reads painted, not clay scan.
            normal_in = principled.inputs.get("Normal")
            if normal_in and normal_in.is_linked:
                link = normal_in.links[0]
                from_node = link.from_node
                if from_node.type == "NORMAL_MAP":
                    from_node.inputs["Strength"].default_value = 0.08
                else:
                    nt.links.remove(link)

            rough_in = principled.inputs.get("Roughness")
            if rough_in and rough_in.is_linked:
                src = rough_in.links[0].from_socket
                nt.links.remove(rough_in.links[0])
                mul = nt.nodes.new("ShaderNodeMath")
                mul.operation = "MULTIPLY"
                mul.inputs[1].default_value = 1.35
                mul.location = (principled.location.x - 220, principled.location.y - 120)
                nt.links.new(src, mul.inputs[0])
                nt.links.new(mul.outputs["Value"], rough_in)
            elif rough_in:
                rough_in.default_value = 0.58

            for coat_key, val in (
                ("Coat Weight", 0.0),
                ("Coat Roughness", 0.5),
                ("Clearcoat", 0.0),
                ("Clearcoat Roughness", 0.5),
                ("Metallic", 0.0),
            ):
                if coat_key in principled.inputs and not principled.inputs[coat_key].is_linked:
                    # Don't force metallic to 0 if a texture drives it via separate path;
                    # only touch unlinked metallic.
                    if coat_key == "Metallic":
                        continue
                    principled.inputs[coat_key].default_value = val

            # Slight color punch without wet plastic.
            base_in = principled.inputs.get("Base Color")
            if base_in and base_in.is_linked:
                # Avoid stacking HSV if we re-run.
                already = any(n.type == "HUE_SAT" for n in nt.nodes)
                if not already:
                    src = base_in.links[0].from_socket
                    nt.links.remove(base_in.links[0])
                    hsv = nt.nodes.new("ShaderNodeHueSaturation")
                    hsv.inputs["Saturation"].default_value = 1.14
                    hsv.inputs["Value"].default_value = 1.03
                    hsv.location = (principled.location.x - 220, principled.location.y + 80)
                    nt.links.new(src, hsv.inputs["Color"])
                    nt.links.new(hsv.outputs["Color"], base_in)

            mat.blend_method = "OPAQUE"


def main() -> None:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]
    src, dst, faces_s = argv[0], argv[1], argv[2]
    toon = True
    if len(argv) >= 4:
        toon = argv[3] not in ("0", "false", "False", "no")
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
        share = max(800, int(target_faces * (n / max(1, total_before))))
        _decimate_uv_safe(obj, share)

    total_after = _total_faces(meshes)
    print(f"DECIMATE_OUT faces={total_after}")

    if toon:
        _toon_materials()
        print("TOON_MATERIALS_APPLIED")

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    export_kwargs = dict(
        filepath=dst,
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_morph=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_yup=True,
    )
    try:
        bpy.ops.export_scene.gltf(**export_kwargs)
    except TypeError:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_apply=True,
        )
    print(f"DECIMATE_WROTE {dst}")


if __name__ == "__main__":
    main()
