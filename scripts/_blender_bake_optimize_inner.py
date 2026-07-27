#!/usr/bin/env python3
"""Blender: closed low-poly + bake Tripo paint (fixes holes + clay + size).

Pipeline for static props/accessories/env:
  1. Import dense Tripo GLB
  2. Keep high-poly source
  3. Voxel-remesh + decimate a low-poly cage (manifold → no holes)
  4. Smart UV project
  5. Bake DIFFUSE color from high → low (preserves painted candy look)
  6. Soft toon material (matte roughness, flat normals)
  7. Export GLB

Skinned characters skip remesh (would destroy weights). They get hole-fill +
mild decimate while keeping original UVs/textures.

Invoked as:
  blender --background --python this.py -- <src.glb> <dst.glb> <target_faces> <tex_size>
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


def _meshes():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _activate(obj) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def _is_skinned(obj) -> bool:
    return bool(obj.vertex_groups) or any(m.type == "ARMATURE" for m in obj.modifiers)


def _total_faces(objs) -> int:
    return sum(len(o.data.polygons) for o in objs)


def _fill_holes(obj) -> None:
    _activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.mesh.fill_holes(sides=0)
    except Exception as err:  # noqa: BLE001
        print(f"warn: fill_holes failed on {obj.name}: {err}")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def _decimate(obj, target_faces: int) -> None:
    _activate(obj)
    # Voxel remesh often leaves quads — triangulate so face counts match budgets.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.quads_convert_to_tris(quad_method="BEAUTY", ngon_method="BEAUTY")
    bpy.ops.object.mode_set(mode="OBJECT")

    n = len(obj.data.polygons)
    if n <= target_faces:
        print(f"skip decimate {obj.name}: already {n} <= {target_faces}")
        return
    ratio = max(0.05, min(0.95, target_faces / max(1, n)))
    mod = obj.modifiers.new("Decimate", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"decimate {obj.name}: {n} -> {len(obj.data.polygons)} (ratio={ratio:.3f})")


def _voxel_remesh(obj, voxel_size: float) -> None:
    _activate(obj)
    mod = obj.modifiers.new("VoxelRemesh", type="REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = voxel_size
    mod.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    print(
        f"remesh {obj.name}: faces={len(obj.data.polygons)} "
        f"voxel={voxel_size:.4f}"
    )


def _smart_uv(obj) -> None:
    _activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def _bbox_max_dim(obj) -> float:
    dims = obj.dimensions
    return max(float(dims.x), float(dims.y), float(dims.z), 0.05)


def _toon_principled(mat) -> None:
    if not mat or not mat.node_tree:
        return
    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        return
    # Flatten normal contribution if present.
    normal_in = principled.inputs.get("Normal")
    if normal_in and normal_in.is_linked:
        link = normal_in.links[0]
        if link.from_node.type == "NORMAL_MAP":
            link.from_node.inputs["Strength"].default_value = 0.05
        else:
            nt.links.remove(link)
    rough = principled.inputs.get("Roughness")
    if rough and not rough.is_linked:
        rough.default_value = 0.72
    elif rough and rough.is_linked:
        # Leave texture but nudge via unconnected default unused — skip.
        pass
    for key, val in (("Coat Weight", 0.0), ("Clearcoat", 0.0), ("Specular IOR Level", 0.2)):
        if key in principled.inputs and not principled.inputs[key].is_linked:
            principled.inputs[key].default_value = val
    mat.blend_method = "OPAQUE"


def _bake_diffuse(high, low, tex_size: int) -> None:
    """Bake high-poly base color onto a new image on the low-poly material."""
    _activate(low)
    # Ensure low has a material slot we can write into.
    if not low.data.materials:
        mat = bpy.data.materials.new(name=f"{low.name}_baked")
        mat.use_nodes = True
        low.data.materials.append(mat)
    else:
        # Copy material so we don't mutate high's datablock unexpectedly.
        src_mat = low.data.materials[0]
        mat = src_mat.copy() if src_mat else bpy.data.materials.new(name=f"{low.name}_baked")
        mat.use_nodes = True
        low.data.materials[0] = mat

    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        principled = nt.nodes.new("ShaderNodeBsdfPrincipled")

    # Remove old image links into Base Color; keep tree clean.
    base_in = principled.inputs.get("Base Color")
    if base_in and base_in.is_linked:
        for link in list(base_in.links):
            nt.links.remove(link)

    img = bpy.data.images.new(
        name=f"{low.name}_diffuse",
        width=tex_size,
        height=tex_size,
        alpha=False,
        float_buffer=False,
    )
    img.generated_color = (0.8, 0.8, 0.8, 1.0)

    tex_node = nt.nodes.new("ShaderNodeTexImage")
    tex_node.image = img
    tex_node.location = (principled.location.x - 360, principled.location.y + 40)
    # Active image node is the bake target.
    for n in nt.nodes:
        n.select = False
    tex_node.select = True
    nt.nodes.active = tex_node

    # Cycles bake setup.
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.bake_type = "DIFFUSE"
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.margin = 8
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = max(0.01, _bbox_max_dim(low) * 0.02)
    scene.render.bake.max_ray_distance = 0.0

    bpy.ops.object.select_all(action="DESELECT")
    high.hide_render = False
    low.hide_render = False
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low

    print(
        f"bake DIFFUSE {high.name} -> {low.name} "
        f"tex={tex_size} cage={scene.render.bake.cage_extrusion:.4f}"
    )
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)

    nt.links.new(tex_node.outputs["Color"], principled.inputs["Base Color"])
    # Matte candy: no normal/metal maps on baked props (avoids clay microdetail).
    for sock_name in ("Normal", "Metallic", "Roughness"):
        sock = principled.inputs.get(sock_name)
        if sock and sock.is_linked:
            for link in list(sock.links):
                nt.links.remove(link)
    if "Roughness" in principled.inputs:
        principled.inputs["Roughness"].default_value = 0.72
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = 0.0
    _toon_principled(mat)


def _optimize_static(obj, target_faces: int, tex_size: int) -> None:
    high = obj
    high_name = high.name
    print(f"static optimize {high_name}: faces_in={len(high.data.polygons)}")

    # Duplicate as low-poly target.
    _activate(high)
    high.hide_render = False
    high.hide_viewport = False
    bpy.ops.object.duplicate()
    low = bpy.context.view_layer.objects.active
    low_name = f"{high_name}_low"
    low.name = low_name
    low.hide_render = False
    low.hide_viewport = False

    # Closed manifold cage.
    dim = _bbox_max_dim(high)
    if target_faces <= 12_000:
        voxel = max(dim / 70.0, 0.004)
    elif target_faces <= 24_000:
        voxel = max(dim / 90.0, 0.003)
    else:
        voxel = max(dim / 110.0, 0.0025)

    _voxel_remesh(low, voxel)
    _fill_holes(low)
    _decimate(low, target_faces)
    _fill_holes(low)
    _smart_uv(low)

    # Re-resolve by name — Blender RNA refs can go stale across ops.
    high = bpy.data.objects.get(high_name)
    low = bpy.data.objects.get(low_name)
    if high is None or low is None:
        raise RuntimeError(f"lost objects after remesh ({high_name!r} / {low_name!r})")

    high.hide_render = False
    low.hide_render = False
    try:
        _bake_diffuse(high, low, tex_size)
    except Exception as err:  # noqa: BLE001
        print(f"warn: bake failed ({err}); keeping remeshed low with existing mats")
        if low.data.materials:
            _toon_principled(low.data.materials[0])

    bpy.data.objects.remove(high, do_unlink=True)
    low = bpy.data.objects.get(low_name)
    if low is None:
        raise RuntimeError(f"lost low mesh after removing high ({low_name!r})")
    low.name = high_name
    if low.data:
        low.data.name = high_name
    print(f"static done {low.name}: faces_out={len(low.data.polygons)}")


def _optimize_skinned(obj, target_faces: int) -> None:
    print(f"skinned optimize {obj.name}: faces_in={len(obj.data.polygons)}")
    _activate(obj)
    # Preserve weights/UVs — hole-fill + mild decimate with armature mods disabled
    # (do not apply armature; only apply Decimate).
    arm_mods = [m for m in obj.modifiers if m.type == "ARMATURE"]
    for m in arm_mods:
        m.show_viewport = False
        m.show_render = False
    _fill_holes(obj)
    _decimate(obj, target_faces)
    _fill_holes(obj)
    for m in arm_mods:
        m.show_viewport = True
        m.show_render = True
    for slot in obj.material_slots:
        _toon_principled(slot.material)
    print(f"skinned done {obj.name}: faces_out={len(obj.data.polygons)}")


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :]
    src, dst, faces_s, tex_s = argv[0], argv[1], argv[2], argv[3]
    target_faces = int(faces_s)
    tex_size = int(tex_s)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)

    meshes = _meshes()
    if not meshes:
        raise SystemExit("no mesh objects imported")

    print(
        f"BAKE_OPT_IN faces={_total_faces(meshes)} target={target_faces} "
        f"tex={tex_size} meshes={len(meshes)}"
    )

    # Drop tiny helper meshes (Tripo sometimes embeds an Icosphere, etc.).
    for obj in list(_meshes()):
        if len(obj.data.polygons) < 500 and not _is_skinned(obj):
            print(f"drop tiny helper mesh {obj.name} faces={len(obj.data.polygons)}")
            bpy.data.objects.remove(obj, do_unlink=True)

    meshes = _meshes()
    if not meshes:
        raise SystemExit("no mesh objects left after dropping helpers")

    # Prefer processing largest mesh first; allocate face budget per mesh.
    meshes_sorted = sorted(meshes, key=lambda o: len(o.data.polygons), reverse=True)
    total_before = max(1, _total_faces(meshes_sorted))
    for obj in list(meshes_sorted):
        # Object may have been removed if names collided — skip stale.
        if obj.name not in bpy.data.objects:
            continue
        n = len(obj.data.polygons)
        share = max(800, int(target_faces * (n / total_before)))
        if _is_skinned(obj):
            _optimize_skinned(obj, share)
        else:
            _optimize_static(obj, share, tex_size)

    print(f"BAKE_OPT_OUT faces={_total_faces(_meshes())}")

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    try:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_morph=True,
            export_apply=True,
            export_texcoords=True,
            export_normals=True,
            export_materials="EXPORT",
            export_image_format="JPEG",
            export_jpeg_quality=80,
            export_yup=True,
        )
    except TypeError:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_apply=True,
        )
    print(f"BAKE_OPT_WROTE {dst}")


if __name__ == "__main__":
    main()
