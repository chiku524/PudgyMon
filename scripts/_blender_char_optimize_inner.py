#!/usr/bin/env python3
"""Blender: optimize skinned Pudgy characters while keeping painted eyes sharp.

Default path (preserve):
  1. Import dense Tripo GLB (armature + clips + painted UVs)
  2. Hole-fill + UV-preserving decimate (no remesh — remesh + smart-UV was
     starving eyes of texels and JPEG-smearing the rebake)
  3. Resize existing base-color textures to tex_size
  4. Export GLB with PNG atlases (JPEG chroma destroyes black/white eyes)

Fallback path (remesh) via 5th argv == "remesh":
  closed voxel cage + bake + weight transfer (used only when preserve fails).

  blender --background --python this.py -- <src.glb> <dst.glb> <faces> <tex> [preserve|remesh]
"""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
import mathutils


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


def _decimate_preserve_uv(obj, target_faces: int) -> None:
    """Collapse-decimate while asking Blender to keep UVs / weights intact."""
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
    # Keep seams / UV continuity as much as Collapse allows.
    if hasattr(mod, "use_dissolve_boundaries"):
        mod.use_dissolve_boundaries = False
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
    bpy.ops.uv.smart_project(angle_limit=45.0, island_margin=0.04)
    bpy.ops.object.mode_set(mode="OBJECT")


def _boost_upper_uv(obj, boost: float = 2.4, upper_frac: float = 0.42) -> None:
    """Give the upper (head/face) UV islands more atlas space so eyes stay sharp."""
    import bmesh

    _activate(obj)
    me = obj.data
    if not me.uv_layers:
        return
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        bpy.ops.object.mode_set(mode="OBJECT")
        return

    zs = [v.co.z for v in bm.verts]
    z_min, z_max = min(zs), max(zs)
    thresh = z_min + (z_max - z_min) * (1.0 - upper_frac)

    # Collect UV loops belonging to upper faces and scale around their centroid.
    upper_loops = []
    for face in bm.faces:
        if sum(1 for v in face.verts if v.co.z >= thresh) < 2:
            continue
        for loop in face.loops:
            upper_loops.append(loop[uv_layer])
    if len(upper_loops) < 8:
        bpy.ops.object.mode_set(mode="OBJECT")
        print("uv-boost: skipped (no upper loops)")
        return

    cx = sum(l.uv.x for l in upper_loops) / len(upper_loops)
    cy = sum(l.uv.y for l in upper_loops) / len(upper_loops)
    for l in upper_loops:
        l.uv.x = cx + (l.uv.x - cx) * boost
        l.uv.y = cy + (l.uv.y - cy) * boost
    bmesh.update_edit_mesh(me)

    # Repack so boosted islands fit the 0-1 atlas.
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(margin=0.04)
    except Exception as err:  # noqa: BLE001
        print(f"warn: pack_islands {err}")
    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"uv-boost: upper_frac={upper_frac} x{boost:.2f} loops={len(upper_loops)}")


def _cage_extrusion(obj) -> float:
    dim = _bbox_max_dim(obj)
    return max(0.001, min(0.012, dim * 0.005))


def _toon_mat(mat) -> None:
    if not mat or not getattr(mat, "use_nodes", False):
        return
    nt = mat.node_tree
    principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not principled:
        return
    normal_in = principled.inputs.get("Normal")
    if normal_in and normal_in.is_linked:
        for link in list(normal_in.links):
            if link.from_node.type == "NORMAL_MAP":
                link.from_node.inputs["Strength"].default_value = 0.05
            else:
                nt.links.remove(link)
    for key, val in (("Coat Weight", 0.0), ("Clearcoat", 0.0)):
        if key in principled.inputs and not principled.inputs[key].is_linked:
            principled.inputs[key].default_value = val
    if "Roughness" in principled.inputs and not principled.inputs["Roughness"].is_linked:
        principled.inputs["Roughness"].default_value = 0.7
    if "Metallic" in principled.inputs and not principled.inputs["Metallic"].is_linked:
        principled.inputs["Metallic"].default_value = 0.0
    mat.blend_method = "OPAQUE"


def _clone_as_png(img, tex_size: int):
    """Pixel-copy into a fresh PNG image so glTF cannot passthrough JPEG bytes."""
    w, h = int(img.size[0]), int(img.size[1])
    if w <= 0 or h <= 0:
        return img
    # Resize source in-place first when needed (never upscale).
    if max(w, h) > tex_size:
        if w >= h:
            nw, nh = tex_size, max(1, int(round(h * (tex_size / w))))
        else:
            nh, nw = tex_size, max(1, int(round(w * (tex_size / h))))
        img.scale(nw, nh)
        w, h = nw, nh
        print(f"tex resize {img.name}: -> {w}x{h}")
    else:
        print(f"tex keep {img.name}: {w}x{h}")

    pixels = list(img.pixels)  # force evaluate packed buffer
    fresh = bpy.data.images.new(
        name=f"{img.name}_png",
        width=w,
        height=h,
        alpha=False,
        float_buffer=False,
    )
    fresh.pixels = pixels
    fresh.file_format = "PNG"
    fresh.pack()
    return fresh


def _prepare_toon_textures(obj, tex_size: int) -> int:
    """Keep base-color only (PNG), drop normal/ORM that muddy candy eyes."""
    converted = 0
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        principled = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not principled:
            continue

        # Disconnect normal / ORM / metallic-roughness image inputs.
        for sock_name in ("Normal", "Metallic", "Roughness"):
            sock = principled.inputs.get(sock_name)
            if sock and sock.is_linked:
                for link in list(sock.links):
                    nt.links.remove(link)
        if "Roughness" in principled.inputs:
            principled.inputs["Roughness"].default_value = 0.72
        if "Metallic" in principled.inputs:
            principled.inputs["Metallic"].default_value = 0.0

        base = principled.inputs.get("Base Color")
        if not base or not base.is_linked:
            _toon_mat(mat)
            continue
        src_node = base.links[0].from_node
        if src_node.type != "TEX_IMAGE" or not src_node.image:
            _toon_mat(mat)
            continue

        png = _clone_as_png(src_node.image, tex_size)
        src_node.image = png
        converted += 1
        _toon_mat(mat)
        print(f"tex png {png.name}: {int(png.size[0])}x{int(png.size[1])}")
    return converted


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
        name=f"{low.name}_diffuse",
        width=tex_size,
        height=tex_size,
        alpha=False,
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
    bake.margin = max(12, tex_size // 64)
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
    print(
        f"bake DIFFUSE {high.name} -> {low.name} tex={tex_size} "
        f"cage={cage:.4f} margin={bake.margin}"
    )
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    nt.links.new(tex.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Roughness"].default_value = 0.7
    principled.inputs["Metallic"].default_value = 0.0
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
    bone_names = {b.name for b in arm.data.bones} if arm.data else set()

    def _pick_bone(*candidates: str) -> str:
        for c in candidates:
            if c in bone_names:
                return c
        if "Root" in bone_names:
            return "Root"
        return next(iter(bone_names)) if bone_names else ""

    socket_bones = {
        "Socket_Hat": _pick_bone("Head"),
        "Socket_Face": _pick_bone("Head"),
        "Socket_Necklace": _pick_bone("NeckTwist01", "NeckTwist02", "Spine02", "Spine01"),
        "Socket_Back": _pick_bone("Spine02", "Spine01", "Waist"),
        "Socket_Hands": _pick_bone("Spine01", "Waist", "Spine02"),
        "Socket_Shoes": _pick_bone("Root", "Hip", "Pelvis"),
    }
    socket_local = {
        "Socket_Hat": (0.0, 0.10, 0.0),
        "Socket_Face": (0.0, 0.02, -0.11),
        "Socket_Necklace": (0.0, -0.02, -0.05),
        "Socket_Back": (0.0, 0.04, 0.12),
        "Socket_Hands": (0.0, -0.05, -0.18),
        "Socket_Shoes": (0.0, 0.0, 0.0),
    }
    for sname, bname in socket_bones.items():
        if not bname or sname in bpy.data.objects:
            if sname in bpy.data.objects:
                print(f"socket keep {sname}")
            continue
        empty = bpy.data.objects.new(sname, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.08
        bpy.context.scene.collection.objects.link(empty)
        empty.parent = arm
        empty.parent_type = "BONE"
        empty.parent_bone = bname
        empty.location = mathutils.Vector(socket_local[sname])
        empty.rotation_euler = (0.0, 0.0, 0.0)
        empty.scale = (1.0, 1.0, 1.0)
        print(f"socket {sname} -> {bname}")


def _export_glb(dst: str) -> None:
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    try:
        bpy.ops.export_scene.gltf(
            filepath=dst,
            export_format="GLB",
            export_animations=True,
            export_skins=True,
            export_morph=True,
            export_apply=False,
            export_texcoords=True,
            export_normals=True,
            export_materials="EXPORT",
            # PNG keeps sharp eye edges; JPEG chroma smears black/white paint.
            export_image_format="PNG",
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


def _optimize_preserve(body, arm, target_faces: int, tex_size: int) -> None:
    """Keep Tripo UVs + paint; only hole-fill, decimate, and resize textures."""
    print(f"CHAR_PATH preserve faces_in={len(body.data.polygons)} tex={tex_size}")
    # Disable armature eval while editing topology.
    for m in body.modifiers:
        if m.type == "ARMATURE":
            m.show_viewport = False
            m.show_render = False

    _fill_holes(body)
    _decimate_preserve_uv(body, target_faces)
    _fill_holes(body)
    _prepare_toon_textures(body, tex_size)

    for m in body.modifiers:
        if m.type == "ARMATURE":
            m.show_viewport = True
            m.show_render = True

    # Ensure an armature modifier remains.
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
    """Closed cage + bake fallback (eyes less sharp — avoid unless needed)."""
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
    voxel = max(dim / 140.0, 0.0025)
    _voxel_remesh(low, voxel)
    _fill_holes(low)
    _decimate_preserve_uv(low, target_faces)
    _fill_holes(low)
    _smart_uv(low)
    _boost_upper_uv(low, boost=2.6, upper_frac=0.45)

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
        body = next(o for o in _meshes())
        arm = next(o for o in _arms())
    else:
        _optimize_preserve(body, arm, target_faces, tex_size)

    if arm.animation_data:
        for t in arm.animation_data.nla_tracks:
            t.mute = False

    _ensure_sockets(arm)
    _export_glb(dst)


if __name__ == "__main__":
    main()
