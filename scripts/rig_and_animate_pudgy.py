#!/usr/bin/env python3
"""Rig a playable Pudgy GLB with the shared armature + party animation clips.

Pipeline:
  1. UV-aware simplify (~100k faces) via gltf-transform
  2. Blender: shared bones, automatic weights, sockets on bones
  3. Author idle/walk/run/jump/emote_wave/emote_dance
  4. Export Bevy-safe skinned GLB (no Draco/WebP)

Usage:
  python scripts/rig_and_animate_pudgy.py --asset-id char_pudgy_pink_01
  python scripts/rig_and_animate_pudgy.py --asset-id char_pudgy_stylized_01
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

_CLIP_NAMES = (
    "idle",
    "walk",
    "run",
    "jump",
    "emote_wave",
    "emote_dance",
)

_WORKER = r'''
import bpy
import math
import mathutils
from pathlib import Path

IN_PATH = Path(r"__IN_PATH__")
OUT_PATH = Path(r"__OUT_PATH__")
ASSET_ID = "__ASSET_ID__"
FPS = 24

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = FPS
bpy.ops.import_scene.gltf(filepath=str(IN_PATH))

# Drop prior armature / clips so re-rigging an already-skinned GLB is clean.
for obj in list(bpy.context.scene.objects):
    if obj.type == "ARMATURE":
        bpy.data.objects.remove(obj, do_unlink=True)
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

# Collect mesh + existing sockets
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
# Strip old skin modifiers / vertex groups before a fresh bind.
for mod in list(body.modifiers):
    if mod.type == "ARMATURE":
        body.modifiers.remove(mod)
body.vertex_groups.clear()
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Clean topology so automatic weights succeed on Tripo meshes.
bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")

sockets = {
    o.name: o
    for o in bpy.context.scene.objects
    if o.type == "EMPTY" and o.name.startswith("Socket_")
}

# Opaque materials
for slot in body.material_slots:
    mat = slot.material
    if not mat:
        continue
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
w = max(maxv.x - minv.x, 1e-4)
d = max(maxv.y - minv.y, 1e-4)
cx = 0.5 * (minv.x + maxv.x)
cy = 0.5 * (minv.y + maxv.y)

# --- Shared Pudgy armature (stubby mascot proportions) ---
arm_data = bpy.data.armatures.new(f"{ASSET_ID}_Armature")
arm_obj = bpy.data.objects.new(f"{ASSET_ID}_Armature", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
arm_obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones

def add_bone(name, head, tail, parent=None):
    b = eb.new(name)
    b.head = head
    b.tail = tail
    if parent is not None:
        b.parent = parent
    return b

# Z-up floor pivot (matches imported polish). Short flipper/foot bones stay near surface.
root = add_bone("Root", (cx, cy, 0.0), (cx, cy, h * 0.06))
hips = add_bone("Hips", (cx, cy, h * 0.32), (cx, cy, h * 0.42), root)
spine = add_bone("Spine", (cx, cy, h * 0.42), (cx, cy, h * 0.58), hips)
head = add_bone("Head", (cx, cy, h * 0.58), (cx, cy, h * 0.88), spine)

# Measure real L/R extents — Tripo pudgies are often asymmetric, so fixed
# ±fractions of AABB width bury the short side inside the core strip.
arm_xmax = arm_xmin = foot_xmax = foot_xmin = 0.0
for vert in body.data.vertices:
    wp = body.matrix_world @ vert.co
    nx = (wp.x - cx) / max(w * 0.5, 1e-4)
    nz = (wp.z - minv.z) / h
    if 0.38 < nz < 0.72:
        arm_xmax = max(arm_xmax, nx)
        arm_xmin = min(arm_xmin, nx)
    if nz <= 0.20:
        foot_xmax = max(foot_xmax, nx)
        foot_xmin = min(foot_xmin, nx)
arm_xmax = max(arm_xmax, 0.45)
arm_xmin = min(arm_xmin, -0.45)
foot_xmax = max(foot_xmax, 0.35)
foot_xmin = min(foot_xmin, -0.35)
print(
    "SIDE_EXTENTS",
    f"arm=({arm_xmin:.3f},{arm_xmax:.3f})",
    f"foot=({foot_xmin:.3f},{foot_xmax:.3f})",
)

# Flipper stubs — mid-body lateral tips (not up into the hood/collar).
l_arm = add_bone(
    "L_Arm",
    (cx + w * 0.5 * arm_xmax * 0.58, cy, h * 0.46),
    (cx + w * 0.5 * arm_xmax * 0.82, cy, h * 0.44),
    spine,
)
l_fore = add_bone(
    "L_Forearm",
    (cx + w * 0.5 * arm_xmax * 0.82, cy, h * 0.44),
    (cx + w * 0.5 * arm_xmax * 0.96, cy, h * 0.42),
    l_arm,
)
r_arm = add_bone(
    "R_Arm",
    (cx + w * 0.5 * arm_xmin * 0.58, cy, h * 0.46),
    (cx + w * 0.5 * arm_xmin * 0.82, cy, h * 0.44),
    spine,
)
r_fore = add_bone(
    "R_Forearm",
    (cx + w * 0.5 * arm_xmin * 0.82, cy, h * 0.44),
    (cx + w * 0.5 * arm_xmin * 0.96, cy, h * 0.42),
    r_arm,
)

# Tiny feet under the dumpling — kept low/out so strides don't melt the belly.
l_leg = add_bone(
    "L_Leg",
    (cx + w * 0.5 * foot_xmax * 0.45, cy, h * 0.16),
    (cx + w * 0.5 * foot_xmax * 0.55, cy, h * 0.07),
    hips,
)
l_shin = add_bone(
    "L_Shin",
    (cx + w * 0.5 * foot_xmax * 0.55, cy, h * 0.07),
    (cx + w * 0.5 * foot_xmax * 0.55, cy, 0.015),
    l_leg,
)
r_leg = add_bone(
    "R_Leg",
    (cx + w * 0.5 * foot_xmin * 0.45, cy, h * 0.16),
    (cx + w * 0.5 * foot_xmin * 0.55, cy, h * 0.07),
    hips,
)
r_shin = add_bone(
    "R_Shin",
    (cx + w * 0.5 * foot_xmin * 0.55, cy, h * 0.07),
    (cx + w * 0.5 * foot_xmin * 0.55, cy, 0.015),
    r_leg,
)

bpy.ops.object.mode_set(mode="OBJECT")

# Envelope bind as a base, then region-paint limbs so flaps actually deform.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj

# Narrower limb envelopes — keep auto-weights off the dumpling core.
ENVELOPE = {
    "Root": (0.48, 0.18, 0.14),
    "Hips": (0.38, 0.16, 0.13),
    "Spine": (0.40, 0.16, 0.13),
    "Head": (0.28, 0.14, 0.12),
    "L_Arm": (0.10, 0.07, 0.05),
    "R_Arm": (0.10, 0.07, 0.05),
    "L_Forearm": (0.08, 0.05, 0.04),
    "R_Forearm": (0.08, 0.05, 0.04),
    "L_Leg": (0.08, 0.05, 0.04),
    "R_Leg": (0.08, 0.05, 0.04),
    "L_Shin": (0.07, 0.045, 0.035),
    "R_Shin": (0.07, 0.045, 0.035),
}
bpy.ops.object.mode_set(mode="POSE")
for pb in arm_obj.pose.bones:
    dist, head_r, tail_r = ENVELOPE.get(pb.name, (0.2, 0.1, 0.08))
    pb.bone.envelope_distance = dist
    pb.bone.head_radius = head_r
    pb.bone.tail_radius = tail_r
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")

def count_unweighted():
    bad = []
    for vert in body.data.vertices:
        total = sum(g.weight for g in vert.groups)
        if total < 1e-4:
            bad.append(vert.index)
    return bad

unweighted = count_unweighted()
print("weight groups", len(body.vertex_groups), "unweighted", len(unweighted))

BONE_NAMES = (
    "Root", "Hips", "Spine", "Head",
    "L_Arm", "L_Forearm", "R_Arm", "R_Forearm",
    "L_Leg", "L_Shin", "R_Leg", "R_Shin",
)
vgs = {n: body.vertex_groups.get(n) or body.vertex_groups.new(name=n) for n in BONE_NAMES}

def clear_vert(idx):
    for vg in vgs.values():
        try:
            vg.remove([idx])
        except RuntimeError:
            pass

def set_vert(idx, weights):
    clear_vert(idx)
    for name, w in weights.items():
        if w > 1e-4:
            vgs[name].add([idx], float(w), "REPLACE")

# Region paint. Critical rule: NEVER soft-blend a parent with a descendant
# (Head↔Root, Arm↔Root, etc.) — LBS averages different bind matrices and
# permanently pinches the mesh (the neck crease in recordings).
mw = body.matrix_world
hw = max(w * 0.5, 1e-4)
hd = max(d * 0.5, 1e-4)
HEAD_CUT = 0.52  # hard seam; Head inherits Root motion via hierarchy
arm_L0 = arm_xmax * 0.42
arm_R0 = arm_xmin * 0.42  # negative
foot_L0 = foot_xmax * 0.22
foot_R0 = foot_xmin * 0.22
LIMB_GROUPS = ("L_Arm", "R_Arm", "L_Forearm", "R_Forearm", "L_Leg", "R_Leg", "L_Shin", "R_Shin")
ARM_GROUPS = ("L_Arm", "R_Arm", "L_Forearm", "R_Forearm")

regioned = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    ny = (wp.y - cy) / hd
    nz = (wp.z - minv.z) / h
    radial = (nx * nx + ny * ny) ** 0.5

    if nz >= HEAD_CUT:
        # Entire hood/face/chin — pure Head (follows Root bounce via parents).
        set_vert(vert.index, {"Head": 1.0})
    elif nx > arm_L0 and 0.34 < nz < HEAD_CUT - 0.01:
        tip = min(1.0, max(0.0, (nx - arm_L0) / max(arm_xmax - arm_L0, 1e-4)))
        tip = tip ** 0.85
        # Pure arm chain only — no Root mix on flippers.
        set_vert(vert.index, {
            "L_Forearm": 0.20 + 0.65 * tip,
            "L_Arm": 0.80 - 0.65 * tip,
        })
    elif nx < arm_R0 and 0.34 < nz < HEAD_CUT - 0.01:
        tip = min(1.0, max(0.0, (arm_R0 - nx) / max(arm_R0 - arm_xmin, 1e-4)))
        tip = tip ** 0.85
        set_vert(vert.index, {
            "R_Forearm": 0.20 + 0.65 * tip,
            "R_Arm": 0.80 - 0.65 * tip,
        })
    elif nz <= 0.14 and nx > foot_L0:
        foot = min(1.0, max(0.0, (0.14 - nz) / 0.14))
        lateral = min(1.0, max(0.0, (nx - foot_L0) / max(foot_xmax - foot_L0, 1e-4)))
        limb = min(1.0, foot * (0.25 + 0.75 * lateral))
        if limb < 0.12:
            set_vert(vert.index, {"Root": 1.0})
        else:
            set_vert(vert.index, {
                "L_Shin": 0.55 * limb,
                "L_Leg": 0.45 * limb,
            })
    elif nz <= 0.14 and nx < foot_R0:
        foot = min(1.0, max(0.0, (0.14 - nz) / 0.14))
        lateral = min(1.0, max(0.0, (foot_R0 - nx) / max(foot_R0 - foot_xmin, 1e-4)))
        limb = min(1.0, foot * (0.25 + 0.75 * lateral))
        if limb < 0.12:
            set_vert(vert.index, {"Root": 1.0})
        else:
            set_vert(vert.index, {
                "R_Shin": 0.55 * limb,
                "R_Leg": 0.45 * limb,
            })
    elif nz < HEAD_CUT:
        set_vert(vert.index, {"Root": 1.0})
    else:
        continue
    regioned += 1
print("REGION_PAINT", regioned, "HEAD_CUT", HEAD_CUT)

gap = count_unweighted()
if gap:
    for idx in gap:
        set_vert(idx, {"Root": 1.0})
    print("WEIGHT_FILL", len(gap), "verts -> Root")

# Re-lock head (envelope leftovers) and clear Head from the body.
head_locked = body_cleared = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nz = (wp.z - minv.z) / h
    if nz >= HEAD_CUT:
        set_vert(vert.index, {"Head": 1.0})
        head_locked += 1
    else:
        try:
            if vgs["Head"].weight(vert.index) > 1e-4:
                # Preserve limb verts; only scrub Head off torso.
                limb = False
                for g in vert.groups:
                    if body.vertex_groups[g.group].name in LIMB_GROUPS and g.weight > 0.05:
                        limb = True
                        break
                if not limb:
                    set_vert(vert.index, {"Root": 1.0})
                    body_cleared += 1
        except RuntimeError:
            pass
print("HEAD_LOCK", head_locked, "BODY_CLEAR_HEAD", body_cleared)

# Kill limb bleed on belly / crotch / armpit (keep far lateral flippers).
stripped = armpit_stripped = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    radial = ((nx * nx) + (((wp.y - cy) / hd) ** 2)) ** 0.5
    if nz >= HEAD_CUT:
        continue
    in_arm_tip = (nx > arm_L0 or nx < arm_R0) and 0.34 < nz < HEAD_CUT - 0.01
    in_foot_tip = nz <= 0.14 and (nx > foot_L0 or nx < foot_R0)
    if in_arm_tip or in_foot_tip:
        continue
    armpit = 0.34 <= nz < HEAD_CUT and abs(nx) < abs(arm_L0 if nx >= 0 else arm_R0) * 0.98
    belly = radial <= 0.68 and 0.08 <= nz < HEAD_CUT
    crotch_mid = abs(nx) < 0.22 and 0.06 <= nz <= 0.36
    if not (armpit or belly or crotch_mid):
        continue
    had = False
    groups = ARM_GROUPS if armpit else LIMB_GROUPS
    for vg_name in groups:
        vg = vgs[vg_name]
        try:
            if vg.weight(vert.index) > 1e-4:
                had = True
            vg.add([vert.index], 0.0, "REPLACE")
        except RuntimeError:
            pass
    if had:
        set_vert(vert.index, {"Root": 1.0})
        stripped += 1
        if armpit:
            armpit_stripped += 1
print("CORE_STRIP_LIMBS", stripped, "armpit", armpit_stripped)

# Re-assert pure foot tips after strips.
foot_boost = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    if nz > 0.15:
        continue
    if nx > foot_L0:
        foot = min(1.0, max(0.0, (0.15 - nz) / 0.15))
        lateral = min(1.0, max(0.0, (nx - foot_L0) / max(foot_xmax - foot_L0, 1e-4)))
        limb = min(1.0, foot * (0.25 + 0.75 * lateral))
        if limb < 0.12:
            continue
        set_vert(vert.index, {"L_Shin": 0.55 * limb, "L_Leg": 0.45 * limb})
        foot_boost += 1
    elif nx < foot_R0:
        foot = min(1.0, max(0.0, (0.15 - nz) / 0.15))
        lateral = min(1.0, max(0.0, (foot_R0 - nx) / max(foot_R0 - foot_xmin, 1e-4)))
        limb = min(1.0, foot * (0.25 + 0.75 * lateral))
        if limb < 0.12:
            continue
        set_vert(vert.index, {"R_Shin": 0.55 * limb, "R_Leg": 0.45 * limb})
        foot_boost += 1
print("FOOT_TIP_BOOST", foot_boost)

# Re-assert pure flipper tips (readable swing volume, never into head band).
arm_boost = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    if not (0.34 < nz < HEAD_CUT - 0.01):
        continue
    if nx > arm_L0:
        tip = min(1.0, max(0.0, (nx - arm_L0) / max(arm_xmax - arm_L0, 1e-4)))
        tip = tip ** 0.85
        if tip < 0.08:
            continue
        set_vert(vert.index, {
            "L_Forearm": 0.20 + 0.65 * tip,
            "L_Arm": 0.80 - 0.65 * tip,
        })
        arm_boost += 1
    elif nx < arm_R0:
        tip = min(1.0, max(0.0, (arm_R0 - nx) / max(arm_R0 - arm_xmin, 1e-4)))
        tip = tip ** 0.85
        if tip < 0.08:
            continue
        set_vert(vert.index, {
            "R_Forearm": 0.20 + 0.65 * tip,
            "R_Arm": 0.80 - 0.65 * tip,
        })
        arm_boost += 1
print("ARM_TIP_BOOST", arm_boost)

# Final hard cut: no Head below HEAD_CUT, no limbs on head, no Head↔Root blends.
safe_head = armpit_clear = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    if nz >= HEAD_CUT:
        set_vert(vert.index, {"Head": 1.0})
        safe_head += 1
        continue
    # Scrub any Head bleed onto body.
    try:
        if vgs["Head"].weight(vert.index) > 1e-4:
            # Keep limb assignment if present.
            limb_w = {}
            for g in vert.groups:
                name = body.vertex_groups[g.group].name
                if name in LIMB_GROUPS and g.weight > 0.05:
                    limb_w[name] = g.weight
            if limb_w:
                set_vert(vert.index, limb_w)
            else:
                set_vert(vert.index, {"Root": 1.0})
            safe_head += 1
    except RuntimeError:
        pass
    # Medial mid-band: never keep arm weights (armpit melt).
    if 0.34 <= nz < HEAD_CUT and not (nx > arm_L0 or nx < arm_R0):
        had = False
        for vg_name in ARM_GROUPS:
            vg = vgs[vg_name]
            try:
                if vg.weight(vert.index) > 1e-4:
                    had = True
                vg.add([vert.index], 0.0, "REPLACE")
            except RuntimeError:
                pass
        if had:
            set_vert(vert.index, {"Root": 1.0})
            armpit_clear += 1
print("SAFE_HEAD_COLLAR", safe_head, "ARMPIT_CLEAR", armpit_clear)

# Normalize weights per vertex (mesh must be active).
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

unweighted = count_unweighted()
if unweighted:
    vgs["Hips"].add(unweighted, 1.0, "REPLACE")
    print("WEIGHT_REPAIR", len(unweighted), "verts -> Hips")

# Parent sockets to bones (keep world transform)
SOCKET_BONE = {
    "Socket_Hat": "Head",
    "Socket_Face": "Head",
    "Socket_Necklace": "Spine",
    "Socket_Back": "Spine",
    "Socket_Hands": "Spine",
    "Socket_Shoes": "Root",
}

def parent_to_bone(obj, armature, bone_name):
    mw = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = mw

for sname, bone in SOCKET_BONE.items():
    if sname in sockets:
        parent_to_bone(sockets[sname], arm_obj, bone)

# --- Readable mascot clips (vertical bounce on bone local Y + clear flaps) ---
def ensure_action(name):
    action = bpy.data.actions.get(name) or bpy.data.actions.new(name)
    action.use_fake_user = True
    return action

def set_bone_keys(action, bone_name, frames_euler):
    """frames_euler: list of (frame, (rx, ry, rz degrees)) plus optional location delta.

    Pose-bone location uses Blender bone space (Y along the bone). For vertical
    Hips/Root bones, bounce must be (0, dy, 0) — not Z, which only slides sideways.
    """
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones.get(bone_name)
    if pb is None:
        bpy.ops.object.mode_set(mode="OBJECT")
        return
    pb.rotation_mode = "XYZ"
    for item in frames_euler:
        if len(item) == 2:
            frame, eul = item
            loc = None
        else:
            frame, eul, loc = item
        bpy.context.scene.frame_set(int(frame))
        pb.rotation_euler = (
            math.radians(eul[0]),
            math.radians(eul[1]),
            math.radians(eul[2]),
        )
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)
        if loc is not None:
            pb.location = mathutils.Vector(loc)
            pb.keyframe_insert(data_path="location", frame=frame)
    bpy.ops.object.mode_set(mode="OBJECT")

def clear_pose():
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.transforms_clear()
    bpy.ops.object.mode_set(mode="OBJECT")

# idle — tiny whole-body bob + soft flipper settle (tucked, not T-pose)
clear_pose()
idle = ensure_action("idle")
set_bone_keys(idle, "Root", [
    (1, (0, 0, 0), (0, 0.0, 0)),
    (24, (0, 0, 0), (0, 0.012, 0)),
    (48, (0, 0, 0), (0, 0.0, 0)),
])
set_bone_keys(idle, "L_Arm", [(1, (8, 0, 8)), (24, (18, 0, 18)), (48, (8, 0, 8))])
set_bone_keys(idle, "R_Arm", [(1, (8, 0, -8)), (24, (18, 0, -18)), (48, (8, 0, -8))])
set_bone_keys(idle, "L_Forearm", [(1, (0, 0, 6)), (24, (0, 0, 16)), (48, (0, 0, 6))])
set_bone_keys(idle, "R_Forearm", [(1, (0, 0, -6)), (24, (0, 0, -16)), (48, (0, 0, -6))])

# walk — foot shuffle + big opposing flipper swing (readable from third person)
clear_pose()
walk = ensure_action("walk")
set_bone_keys(walk, "Root", [
    (1, (0, 0, 0), (0, 0.0, 0)),
    (6, (0, 0, 0), (0, 0.01, 0)),
    (11, (0, 0, 0), (0, 0.0, 0)),
    (16, (0, 0, 0), (0, 0.01, 0)),
    (22, (0, 0, 0), (0, 0.0, 0)),
])
set_bone_keys(walk, "L_Leg", [(1, (-12, 0, 0)), (11, (12, 0, 0)), (22, (-12, 0, 0))])
set_bone_keys(walk, "R_Leg", [(1, (12, 0, 0)), (11, (-12, 0, 0)), (22, (12, 0, 0))])
set_bone_keys(walk, "L_Shin", [(1, (6, 0, 0)), (11, (1, 0, 0)), (22, (6, 0, 0))])
set_bone_keys(walk, "R_Shin", [(1, (1, 0, 0)), (11, (6, 0, 0)), (22, (1, 0, 0))])
# X = forward/back swing, Z = tuck↔flare — large deltas so stubs read in-game.
set_bone_keys(walk, "L_Arm", [(1, (35, 0, 28)), (11, (-30, 0, 6)), (22, (35, 0, 28))])
set_bone_keys(walk, "R_Arm", [(1, (-30, 0, -6)), (11, (35, 0, -28)), (22, (-30, 0, -6))])
set_bone_keys(walk, "L_Forearm", [(1, (10, 0, 22)), (11, (-8, 0, 4)), (22, (10, 0, 22))])
set_bone_keys(walk, "R_Forearm", [(1, (-8, 0, -4)), (11, (10, 0, -22)), (22, (-8, 0, -4))])

# run — bigger kick + stronger opposing arm flaps
clear_pose()
run = ensure_action("run")
set_bone_keys(run, "Root", [
    (1, (0, 0, 0), (0, 0.006, 0)),
    (4, (0, 0, 0), (0, 0.016, 0)),
    (7, (0, 0, 0), (0, 0.006, 0)),
    (10, (0, 0, 0), (0, 0.016, 0)),
    (13, (0, 0, 0), (0, 0.006, 0)),
])
set_bone_keys(run, "L_Leg", [(1, (-16, 0, 0)), (7, (16, 0, 0)), (13, (-16, 0, 0))])
set_bone_keys(run, "R_Leg", [(1, (16, 0, 0)), (7, (-16, 0, 0)), (13, (16, 0, 0))])
set_bone_keys(run, "L_Shin", [(1, (8, 0, 0)), (7, (2, 0, 0)), (13, (8, 0, 0))])
set_bone_keys(run, "R_Shin", [(1, (2, 0, 0)), (7, (8, 0, 0)), (13, (2, 0, 0))])
set_bone_keys(run, "L_Arm", [(1, (42, 0, 32)), (7, (-36, 0, 8)), (13, (42, 0, 32))])
set_bone_keys(run, "R_Arm", [(1, (-36, 0, -8)), (7, (42, 0, -32)), (13, (-36, 0, -8))])
set_bone_keys(run, "L_Forearm", [(1, (12, 0, 26)), (7, (-10, 0, 4)), (13, (12, 0, 26))])
set_bone_keys(run, "R_Forearm", [(1, (-10, 0, -4)), (7, (12, 0, -26)), (13, (-10, 0, -4))])

# jump — squash / stretch on torso
clear_pose()
jump = ensure_action("jump")
set_bone_keys(jump, "Root", [
    (1, (0, 0, 0), (0, -0.03, 0)),
    (4, (0, 0, 0), (0, 0.07, 0)),
    (8, (0, 0, 0), (0, 0.09, 0)),
    (12, (0, 0, 0), (0, 0.015, 0)),
    (15, (0, 0, 0), (0, 0.0, 0)),
])
set_bone_keys(jump, "Spine", [(1, (6, 0, 0)), (4, (-4, 0, 0)), (15, (0, 0, 0))])
set_bone_keys(jump, "L_Arm", [(1, (8, 0, 12)), (4, (-18, 0, 18)), (15, (4, 0, 8))])
set_bone_keys(jump, "R_Arm", [(1, (8, 0, -12)), (4, (-18, 0, -18)), (15, (4, 0, -8))])
set_bone_keys(jump, "L_Leg", [(1, (8, 0, 0)), (4, (-8, 0, 0)), (15, (0, 0, 0))])
set_bone_keys(jump, "R_Leg", [(1, (8, 0, 0)), (4, (-8, 0, 0)), (15, (0, 0, 0))])
set_bone_keys(jump, "Head", [(1, (5, 0, 0)), (4, (-6, 0, 0)), (15, (0, 0, 0))])

# emote_wave — clear flipper wave
clear_pose()
wave = ensure_action("emote_wave")
set_bone_keys(wave, "Spine", [(1, (0, 0, 0)), (8, (0, 0, -8)), (30, (0, 0, 0))])
set_bone_keys(wave, "R_Arm", [
    (1, (8, 0, -12)),
    (6, (-55, 0, -20)),
    (12, (-55, 0, 16)),
    (18, (-55, 0, -16)),
    (24, (-55, 0, 14)),
    (30, (8, 0, -12)),
])
set_bone_keys(wave, "R_Forearm", [
    (1, (0, 0, 0)), (6, (-10, 0, 0)), (12, (8, 0, 0)), (18, (-10, 0, 0)), (24, (8, 0, 0)), (30, (0, 0, 0)),
])
set_bone_keys(wave, "Head", [(1, (0, 0, 0)), (8, (0, 0, 10)), (30, (0, 0, 0))])

# emote_dance — playful Root bounce (no Hip twist melt)
clear_pose()
dance = ensure_action("emote_dance")
set_bone_keys(dance, "Root", [
    (1, (0, 0, 0), (0, 0.0, 0)),
    (6, (0, 0, 0), (0, 0.04, 0)),
    (12, (0, 0, 0), (0, 0.0, 0)),
    (18, (0, 0, 0), (0, 0.04, 0)),
    (24, (0, 0, 0), (0, 0.0, 0)),
])
set_bone_keys(dance, "Spine", [(1, (0, 0, -5)), (12, (0, 0, 5)), (24, (0, 0, -5))])
set_bone_keys(dance, "Head", [(1, (0, 0, 4)), (12, (0, 0, -4)), (24, (0, 0, 4))])
set_bone_keys(dance, "L_Arm", [(1, (-20, 0, 16)), (12, (-14, 0, 22)), (24, (-20, 0, 16))])
set_bone_keys(dance, "R_Arm", [(1, (-14, 0, -22)), (12, (-20, 0, -16)), (24, (-14, 0, -22))])
set_bone_keys(dance, "L_Leg", [(1, (6, 0, 4)), (12, (6, 0, -4)), (24, (6, 0, 4))])
set_bone_keys(dance, "R_Leg", [(1, (6, 0, -4)), (12, (6, 0, 4)), (24, (6, 0, -4))])

# Push actions into NLA strips so glTF exports all clips (Blender 4+/5)
clear_pose()
arm_obj.animation_data_create()
clip_meta = [
    ("idle", idle, 1, 48),
    ("walk", walk, 1, 22),
    ("run", run, 1, 13),
    ("jump", jump, 1, 15),
    ("emote_wave", wave, 1, 30),
    ("emote_dance", dance, 1, 24),
]
for name, action, f0, f1 in clip_meta:
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, int(f0), action)
    strip.action_frame_start = f0
    strip.action_frame_end = f1
    strip.frame_start = f0
    strip.frame_end = f1

# Prefer active action cleared so NLA drives export
arm_obj.animation_data.action = None

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
    bpy.ops.export_scene.gltf(**export_kwargs, export_jpeg_quality=85)
except TypeError:
    # Older/newer kw variants
    for drop in ("export_nla_strips", "export_optimize_animation_size", "export_def_bones"):
        export_kwargs.pop(drop, None)
    bpy.ops.export_scene.gltf(**export_kwargs)

print("RIG_OK", ASSET_ID)
print("faces", len(body.data.polygons))
print("bones", [b.name for b in arm_data.bones])
print("clips", [t.name for t in arm_obj.animation_data.nla_tracks])
print("bytes", OUT_PATH.stat().st_size)
'''


def _gltf_transform(*args: str) -> None:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise RuntimeError("npx not found on PATH")
    cmd = [npx, "--yes", "@gltf-transform/cli@4.1.1", *args]
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if proc.stdout:
        print(proc.stdout[-1500:])
    if proc.returncode != 0:
        print(proc.stderr[-2000:], file=sys.stderr)
        raise RuntimeError(f"gltf-transform failed: {' '.join(args[:2])}")


def _simplify(src: Path, dst: Path, *, ratio: float, error: float) -> None:
    weld = dst.with_name(dst.stem + "_weld.glb")
    try:
        _gltf_transform("weld", str(src), str(weld))
        _gltf_transform(
            "simplify",
            str(weld),
            str(dst),
            "--ratio",
            str(ratio),
            "--error",
            str(error),
            "--lock-border",
            "true",
        )
    finally:
        weld.unlink(missing_ok=True)


def _register_notes(asset_id: str) -> None:
    if not _REGISTRY.is_file():
        return
    registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    for entry in registry.get("assets", []):
        if entry.get("asset_id") == asset_id:
            entry["notes"] = (
                "Skinned Pudgy contract + clips "
                f"({', '.join(_CLIP_NAMES)}); game-res ~100k; Bevy-safe JPEG."
            )
            break
    _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        help="Source GLB (default: assets/models/<id>/<id>.glb)",
    )
    parser.add_argument("--simplify-ratio", type=float, default=0.35,
                        help="Vertex keep ratio before skinning (0 skips). "
                             "0.35 keeps more detail and avoids holey meshopt collapses.")
    parser.add_argument("--simplify-error", type=float, default=0.05)
    parser.add_argument(
        "--skip-simplify",
        action="store_true",
        help="Rig the current GLB without a pre-simplify pass",
    )
    args = parser.parse_args()

    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1
    if shutil.which("npx") is None and not args.skip_simplify:
        print("error: npx required for UV-aware simplify", file=sys.stderr)
        return 1

    aid = args.asset_id.strip()
    dest_dir = _MODELS / aid
    out = dest_dir / f"{aid}.glb"
    src = args.src if args.src is not None else out
    if not src.is_file():
        print(f"error: missing {src}", file=sys.stderr)
        return 1

    dest_dir.mkdir(parents=True, exist_ok=True)
    work_src = dest_dir / f"{aid}_rig_src.glb"
    if args.skip_simplify:
        shutil.copy2(src, work_src)
    else:
        print(f"simplify {src} -> {work_src} (ratio={args.simplify_ratio})")
        _simplify(src, work_src, ratio=args.simplify_ratio, error=args.simplify_error)

    worker = dest_dir / "_rig_worker.py"
    script = (
        _WORKER.replace("__IN_PATH__", str(work_src.resolve()).replace("\\", "/"))
        .replace("__OUT_PATH__", str(out.resolve()).replace("\\", "/"))
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
        work_src.unlink(missing_ok=True)

    print(proc.stdout[-5000:] if proc.stdout else "")
    if proc.stderr:
        err_tail = proc.stderr[-2000:]
        if "Error" in err_tail or "Traceback" in err_tail:
            print(err_tail, file=sys.stderr)
    if proc.returncode != 0 or not out.is_file() or "RIG_OK" not in (proc.stdout or ""):
        print(proc.stderr[-5000:] if proc.stderr else "", file=sys.stderr)
        print("error: Blender rig export did not complete", file=sys.stderr)
        return 1

    (dest_dir / "README.txt").write_text(
        f"{aid}\n"
        "Skinned Pudgy character (shared armature contract).\n"
        f"Clips: {', '.join(_CLIP_NAMES)}\n"
        "Bones: Root, Hips, Spine, Head, L_Arm, R_Arm, L_Forearm, R_Forearm, "
        "L_Leg, R_Leg, L_Shin, R_Shin\n"
        "Sockets parented to bones. Bevy-safe (no Draco/WebP).\n"
        "Rebuild: python scripts/rig_and_animate_pudgy.py --asset-id "
        f"{aid}\n",
        encoding="utf-8",
    )
    _register_notes(aid)
    print(f"glb -> {out.relative_to(_REPO)} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
