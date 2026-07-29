#!/usr/bin/env python3
"""Blender: optimize skinned Pudgy characters without losing painted eyes.

Default path ("preserve"):
  1. Import dense Tripo GLB (armature + clips + painted UVs)
  2. Hole-fill + UV-preserving collapse decimate (keeps weights + UV paint)
  3. Unlink normal / ORM inputs (matte candy look, smaller files)
  4. Export GLB — the original basecolor rides through untouched; the
     wrapper post-sharpens it to PNG (Blender cannot unsharp-mask).

Rebaking a fresh atlas (remesh + smart UV) was starving the authored eye
paint of texels, which is why crew eyes kept coming out blurry. Only use
the "remesh" fallback when a mesh is too broken to decimate.

  blender --background --python this.py -- <src.glb> <dst.glb> <faces> <tex> [preserve|remesh]
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


def _meshes():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _arms():
    return [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]


def _activate(obj) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def _bbox_max_dim(obj) -> float:
    d = obj.dimensions
    return max(float(d.x), float(d.y), float(d.z), 0.05)


def _rest_pose(arm) -> None:
    _activate(arm)
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


def _fill_holes(obj) -> None:
    _activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.mesh.fill_holes(sides=0)
    except Exception as err:  # noqa: BLE001
        print(f"warn: fill_holes {err}")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def _triangulate(obj) -> None:
    _activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.quads_convert_to_tris(quad_method="BEAUTY", ngon_method="BEAUTY")
    bpy.ops.object.mode_set(mode="OBJECT")


def _decimate(obj, target_faces: int) -> None:
    """Collapse decimate — preserves UV layers and vertex groups."""
    _activate(obj)
    _triangulate(obj)
    n = len(obj.data.polygons)
    if n <= target_faces:
        print(f"skip decimate {obj.name}: {n} <= {target_faces}")
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
    print(f"remesh {obj.name}: faces={len(obj.data.polygons)} voxel={voxel_size:.4f}")


def _smart_uv(obj) -> None:
    _activate(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=45.0, island_margin=0.03)
    bpy.ops.object.mode_set(mode="OBJECT")


def _cage_extrusion(obj) -> float:
    dim = _bbox_max_dim(obj)
    return max(0.001, min(0.012, dim * 0.005))


def _toon_mat(mat) -> None:
    """Matte candy look: unlink normal/ORM images, flat roughness/metallic."""
    if not mat or not getattr(mat, "use_nodes", False):
        return
    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        return
    for sock_name in ("Normal", "Metallic", "Roughness"):
        sock = principled.inputs.get(sock_name)
        if sock and sock.is_linked:
            for link in list(sock.links):
                nt.links.remove(link)
    for key, val in (("Coat Weight", 0.0), ("Clearcoat", 0.0)):
        if key in principled.inputs and not principled.inputs[key].is_linked:
            principled.inputs[key].default_value = val
    if "Roughness" in principled.inputs:
        principled.inputs["Roughness"].default_value = 0.72
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = 0.0
    mat.blend_method = "OPAQUE"


def _bake_diffuse(high, low, tex_size: int) -> None:
    _activate(low)
    mat = bpy.data.materials.new(name=f"{low.name}_baked")
    mat.use_nodes = True
    if low.data.materials:
        low.data.materials[0] = mat
    else:
        low.data.materials.append(mat)

    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (0, 0)
    out.location = (300, 0)
    nt.links.new(principled.outputs["BSDF"], out.inputs["Surface"])

    img = bpy.data.images.new(
        name=f"{low.name}_diffuse", width=tex_size, height=tex_size, alpha=False
    )
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-350, 80)
    nt.nodes.active = tex
    tex.select = True

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    bake = scene.render.bake
    bake.use_pass_direct = False
    bake.use_pass_indirect = False
    bake.use_pass_color = True
    bake.margin = max(8, tex_size // 64)
    if hasattr(bake, "margin_type"):
        bake.margin_type = "EXTEND"
    bake.use_selected_to_active = True
    cage = _cage_extrusion(low)
    bake.cage_extrusion = cage
    bake.max_ray_distance = cage * 3.0

    high.hide_render = False
    low.hide_render = False
    high.hide_viewport = False
    low.hide_viewport = False
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    print(f"bake DIFFUSE {high.name} -> {low.name} tex={tex_size} cage={cage:.4f}")
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    nt.links.new(tex.outputs["Color"], principled.inputs["Base Color"])
    _toon_mat(mat)


def _transfer_weights(src, dst, arm) -> int:
    _activate(dst)
    for mod in list(dst.modifiers):
        dst.modifiers.remove(mod)
    dst.vertex_groups.clear()
    dst.parent = None

    xfer = dst.modifiers.new(name="WeightXfer", type="DATA_TRANSFER")
    xfer.object = src
    xfer.use_vert_data = True
    xfer.data_types_verts = {"VGROUP_WEIGHTS"}
    xfer.vert_mapping = "POLYINTERP_NEAREST"
    xfer.layers_vgroup_select_src = "ALL"
    xfer.mix_mode = "REPLACE"
    bpy.ops.object.datalayout_transfer(modifier=xfer.name)
    bpy.ops.object.modifier_apply(modifier=xfer.name)

    dst.parent = arm
    dst.parent_type = "OBJECT"
    arm_mod = dst.modifiers.new(name="Armature", type="ARMATURE")
    arm_mod.object = arm
    arm_mod.use_vertex_groups = True

    weighted = sum(1 for v in dst.data.vertices if any(g.weight > 1e-6 for g in v.groups))
    print(
        f"weights {dst.name}: groups={len(dst.vertex_groups)} "
        f"weighted_verts={weighted}/{len(dst.data.vertices)}"
    )
    if weighted < max(100, len(dst.data.vertices) // 20):
        raise RuntimeError(f"weight transfer failed ({weighted} weighted verts)")
    return weighted


def _ensure_sockets(arm) -> None:
    """Strip authored Socket_* empties — Bevy creates them at runtime.

    Blender bone-parented empties export with a +90° X rest tilt that tips
    every wearable onto its side. Runtime `ensure_accessory_sockets` parents
    clean identity-rotation sockets to the same bones with tuned offsets.
    """
    _ = arm  # armature still required by caller for skin validation
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Socket_"):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    if removed:
        print(f"socket strip removed={removed} (runtime will recreate)")
    else:
        print("socket strip: none present")


def _optimize_preserve(body, arm, target_faces: int) -> None:
    """Keep Tripo UVs + painted textures; geometry untouched.

    Blender's collapse decimate drifts UVs at island seams — on Tripo's
    edge-to-edge fragment atlases that sampled neighbouring fragments
    and covered characters in dark speckles. Decimation is done by the
    wrapper with meshopt (gltf-transform simplify), which never merges
    vertices across UV seams.
    """
    print(f"CHAR_PATH preserve faces_in={len(body.data.polygons)} (simplify deferred)")
    for slot in body.material_slots:
        _toon_mat(slot.material)

    if not any(m.type == "ARMATURE" for m in body.modifiers):
        arm_mod = body.modifiers.new(name="Armature", type="ARMATURE")
        arm_mod.object = arm
        arm_mod.use_vertex_groups = True
    body.parent = arm
    body.parent_type = "OBJECT"
    print(
        f"CHAR_OPT_OUT faces={len(body.data.polygons)} "
        f"groups={len(body.vertex_groups)} arm={arm.name} path=preserve"
    )


def _optimize_remesh(body, arm, target_faces: int, tex_size: int) -> None:
    """Closed-cage fallback for meshes too broken to decimate."""
    print(f"CHAR_PATH remesh faces_in={len(body.data.polygons)} tex={tex_size}")
    body_name = body.name
    arm_name = arm.name

    _activate(body)
    for m in body.modifiers:
        if m.type == "ARMATURE":
            m.show_viewport = False
            m.show_render = False

    bpy.ops.object.duplicate()
    high = bpy.context.view_layer.objects.active
    high.name = "_char_high_src"
    for m in list(high.modifiers):
        if m.type == "ARMATURE":
            high.modifiers.remove(m)

    _activate(body)
    bpy.ops.object.duplicate()
    low = bpy.context.view_layer.objects.active
    low.name = "_char_low"
    for m in list(low.modifiers):
        low.modifiers.remove(m)
    low.vertex_groups.clear()
    low.parent = None

    dim = _bbox_max_dim(body)
    voxel = max(dim / 120.0, 0.0025)
    _voxel_remesh(low, voxel)
    _fill_holes(low)
    _decimate(low, target_faces)
    _fill_holes(low)
    _smart_uv(low)

    high = bpy.data.objects.get("_char_high_src")
    low = bpy.data.objects.get("_char_low")
    body = bpy.data.objects.get(body_name)
    arm = bpy.data.objects.get(arm_name)
    if not all((high, low, body, arm)):
        raise RuntimeError("lost objects mid-remesh")

    try:
        _bake_diffuse(high, low, tex_size)
    except Exception as err:  # noqa: BLE001
        print(f"warn: bake failed ({err}); using flat matte fallback")
        mat = bpy.data.materials.new(name=f"{low.name}_flat")
        mat.use_nodes = True
        low.data.materials.clear()
        low.data.materials.append(mat)
        _toon_mat(mat)

    _transfer_weights(high, low, arm)

    for name in (body_name, "_char_high_src"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    low = bpy.data.objects.get("_char_low")
    arm = bpy.data.objects.get(arm_name)
    if low is None or arm is None:
        raise RuntimeError("lost low/arm after cleanup")
    low.name = body_name
    if low.data:
        low.data.name = body_name
    print(
        f"CHAR_OPT_OUT faces={len(low.data.polygons)} "
        f"groups={len(low.vertex_groups)} arm={arm.name} path=remesh"
    )


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :]
    src, dst, faces_s, tex_s = argv[0], argv[1], argv[2], argv[3]
    path = (argv[4] if len(argv) > 4 else "preserve").lower()
    target_faces = int(faces_s)
    tex_size = int(tex_s)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)

    for obj in list(_meshes()):
        if len(obj.data.polygons) < 500:
            print(f"drop tiny {obj.name} faces={len(obj.data.polygons)}")
            bpy.data.objects.remove(obj, do_unlink=True)

    meshes = _meshes()
    arms = _arms()
    if not meshes:
        raise SystemExit("no mesh")
    if not arms:
        raise SystemExit("no armature — character optimize requires a skinned rig")

    meshes.sort(key=lambda o: len(o.data.polygons), reverse=True)
    body = meshes[0]
    for o in meshes[1:]:
        print(f"drop extra mesh {o.name} faces={len(o.data.polygons)}")
        bpy.data.objects.remove(o, do_unlink=True)

    arm = arms[0]
    print(
        f"CHAR_OPT_IN body={body.name} faces={len(body.data.polygons)} "
        f"arm={arm.name} groups={len(body.vertex_groups)} target={target_faces} "
        f"path={path}"
    )

    _rest_pose(arm)

    if path == "remesh":
        _optimize_remesh(body, arm, target_faces, tex_size)
    else:
        _optimize_preserve(body, arm, target_faces)

    arm = _arms()[0]
    if arm.animation_data:
        for t in arm.animation_data.nla_tracks:
            t.mute = False

    _ensure_sockets(arm)

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    try:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_morph=True,
            export_apply=False,  # keep armature modifier as skin
            export_texcoords=True,
            export_normals=True,
            export_materials="EXPORT",
            # AUTO passes the original basecolor bytes through unchanged;
            # the wrapper post-sharpens to PNG (Blender has no unsharp).
            export_image_format="AUTO",
            export_yup=True,
        )
    except TypeError:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_apply=False,
        )
    print(f"CHAR_OPT_WROTE {dst}")


if __name__ == "__main__":
    main()
