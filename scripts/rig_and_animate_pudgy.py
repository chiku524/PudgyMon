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

# Flipper stubs — sit on each side's actual silhouette, not AABB halves.
l_arm = add_bone(
    "L_Arm",
    (cx + w * 0.5 * arm_xmax * 0.55, cy, h * 0.52),
    (cx + w * 0.5 * arm_xmax * 0.82, cy, h * 0.48),
    spine,
)
l_fore = add_bone(
    "L_Forearm",
    (cx + w * 0.5 * arm_xmax * 0.82, cy, h * 0.48),
    (cx + w * 0.5 * arm_xmax * 0.95, cy, h * 0.44),
    l_arm,
)
r_arm = add_bone(
    "R_Arm",
    (cx + w * 0.5 * arm_xmin * 0.55, cy, h * 0.52),
    (cx + w * 0.5 * arm_xmin * 0.82, cy, h * 0.48),
    spine,
)
r_fore = add_bone(
    "R_Forearm",
    (cx + w * 0.5 * arm_xmin * 0.82, cy, h * 0.48),
    (cx + w * 0.5 * arm_xmin * 0.95, cy, h * 0.44),
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

# Region paint: keep dumpling core on torso, give flippers/feet real influence.
# Thresholds are relative to each side's measured extent (asymmetric meshes).
mw = body.matrix_world
hw = max(w * 0.5, 1e-4)
hd = max(d * 0.5, 1e-4)
# Outer tip of each side's silhouette is limb; armpit/crotch stay on torso.
arm_L0 = arm_xmax * 0.48
arm_R0 = arm_xmin * 0.48  # negative
foot_L0 = foot_xmax * 0.26
foot_R0 = foot_xmin * 0.26
regioned = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    ny = (wp.y - cy) / hd
    nz = (wp.z - minv.z) / h
    radial = (nx * nx + ny * ny) ** 0.5

    # Whole head (hood/face/chin) on Head — inherits Root bounce via hierarchy.
    # A Head↔Root split at the mouth was creasing "bottom of head / top of body".
    if nz >= 0.58:
        set_vert(vert.index, {"Head": 1.0})
    elif 0.50 <= nz < 0.58 and radial < 0.75:
        # Thin soft collar between rigid head and dumpling body.
        t = (nz - 0.50) / 0.08
        set_vert(vert.index, {"Head": 0.35 + 0.45 * t, "Root": 0.65 - 0.45 * t})
    elif nx > arm_L0 and nz > 0.40:
        tip = min(1.0, max(0.0, (nx - arm_L0) / max(arm_xmax - arm_L0, 1e-4)))
        tip = tip ** 1.15
        set_vert(vert.index, {
            "L_Forearm": 0.20 + 0.55 * tip,
            "L_Arm": 0.35 - 0.05 * tip,
            "Spine": max(0.05, 0.45 - 0.50 * tip),
        })
    elif nx < arm_R0 and nz > 0.40:
        tip = min(1.0, max(0.0, (arm_R0 - nx) / max(arm_R0 - arm_xmin, 1e-4)))
        tip = tip ** 1.15
        set_vert(vert.index, {
            "R_Forearm": 0.20 + 0.55 * tip,
            "R_Arm": 0.35 - 0.05 * tip,
            "Spine": max(0.05, 0.45 - 0.50 * tip),
        })
    elif nz <= 0.12 and nx > foot_L0:
        # Extreme foot tips only — keeps ankles from melting into the dumpling.
        foot = min(1.0, max(0.0, (0.12 - nz) / 0.12))
        lateral = min(1.0, max(0.0, (nx - foot_L0) / max(foot_xmax - foot_L0, 1e-4)))
        limb = min(0.80, 0.85 * foot * (0.30 + 0.70 * lateral))
        set_vert(vert.index, {
            "L_Shin": 0.50 * limb,
            "L_Leg": 0.35 * limb,
            "Root": max(0.20, 1.0 - limb),
        })
    elif nz <= 0.12 and nx < foot_R0:
        foot = min(1.0, max(0.0, (0.12 - nz) / 0.12))
        lateral = min(1.0, max(0.0, (foot_R0 - nx) / max(foot_R0 - foot_xmin, 1e-4)))
        limb = min(0.80, 0.85 * foot * (0.30 + 0.70 * lateral))
        set_vert(vert.index, {
            "R_Shin": 0.50 * limb,
            "R_Leg": 0.35 * limb,
            "Root": max(0.20, 1.0 - limb),
        })
    elif radial < 0.70 and 0.08 <= nz < 0.50:
        # Dumpling body — almost pure Root (Spine bleed wrinkled the top of body).
        set_vert(vert.index, {"Root": 0.92, "Spine": 0.08})
    else:
        continue
    regioned += 1
print("REGION_PAINT", regioned)

# Fill any verts the envelope left empty (common on asymmetric Tripo meshes).
gap = count_unweighted()
if gap:
    for idx in gap:
        set_vert(idx, {"Root": 0.85, "Spine": 0.15})
    print("WEIGHT_FILL", len(gap), "verts -> Root/Spine")

# Force full head rigid on Head (clears envelope/arm bleed under the hood).
head_locked = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nz = (wp.z - minv.z) / h
    if nz < 0.58:
        continue
    set_vert(vert.index, {"Head": 1.0})
    head_locked += 1
print("HEAD_LOCK", head_locked)

# Strip Head off the dumpling body (neck seam must not leave Head on belly).
body_cleared = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    ny = (wp.y - cy) / hd
    nz = (wp.z - minv.z) / h
    radial = (nx * nx + ny * ny) ** 0.5
    if nz >= 0.50 or radial > 0.72:
        continue
    try:
        if vgs["Head"].weight(vert.index) > 1e-4:
            set_vert(vert.index, {"Root": 0.92, "Spine": 0.08})
            body_cleared += 1
    except RuntimeError:
        pass
print("BODY_CLEAR_HEAD", body_cleared)

# Hard strip: kill leftover envelope limb weights on belly + crotch + armpits.
LIMB_GROUPS = ("L_Arm", "R_Arm", "L_Forearm", "R_Forearm", "L_Leg", "R_Leg", "L_Shin", "R_Shin")
ARM_GROUPS = ("L_Arm", "R_Arm", "L_Forearm", "R_Forearm")
stripped = 0
armpit_stripped = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    ny = (wp.y - cy) / hd
    nz = (wp.z - minv.z) / h
    radial = (nx * nx + ny * ny) ** 0.5
    if nz >= 0.58:
        continue  # head is sacred
    in_arm_tip = (nx > arm_L0 or nx < arm_R0) and nz > 0.42
    in_foot_tip = nz <= 0.14 and (nx > foot_L0 or nx < foot_R0)
    if in_arm_tip or in_foot_tip:
        continue

    armpit = 0.38 <= nz <= 0.52 and abs(nx) < abs(arm_L0 if nx >= 0 else arm_R0) * 0.98
    crotch_mid = abs(nx) < 0.22 and 0.06 <= nz <= 0.36
    belly = radial <= 0.64 and 0.10 <= nz < 0.50

    if armpit:
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
            vgs["Root"].add([vert.index], 0.85, "ADD")
            vgs["Spine"].add([vert.index], 0.15, "ADD")
            armpit_stripped += 1
            stripped += 1
        continue

    if not (belly or crotch_mid):
        continue
    had_limb = False
    for vg_name in LIMB_GROUPS:
        vg = vgs[vg_name]
        try:
            if vg.weight(vert.index) > 1e-4:
                had_limb = True
            vg.add([vert.index], 0.0, "REPLACE")
        except RuntimeError:
            pass
    if had_limb:
        vgs["Root"].add([vert.index], 0.90, "ADD")
        vgs["Spine"].add([vert.index], 0.10, "ADD")
        stripped += 1
print("CORE_STRIP_LIMBS", stripped, "armpit", armpit_stripped)

# Collar must not keep arm/leg envelope weights (wrinkles bottom-of-head seam).
collar_stripped = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    if not (0.48 <= nz < 0.58):
        continue
    had = False
    for vg_name in LIMB_GROUPS:
        vg = vgs[vg_name]
        try:
            if vg.weight(vert.index) > 1e-4:
                had = True
            vg.add([vert.index], 0.0, "REPLACE")
        except RuntimeError:
            pass
    if had or True:
        # Always reassert a clean Head/Root collar (no limb leftovers).
        t = (nz - 0.48) / 0.10
        # Extreme side tips in the collar band can stay lightly on arm roots.
        if nx > arm_L0 and nz > 0.52:
            tip = min(1.0, (nx - arm_L0) / max(arm_xmax - arm_L0, 1e-4))
            set_vert(vert.index, {
                "L_Arm": 0.25 * tip,
                "Head": 0.40 + 0.20 * (1.0 - tip),
                "Root": 0.60 - 0.20 * tip - 0.25 * tip,
            })
        elif nx < arm_R0 and nz > 0.52:
            tip = min(1.0, (arm_R0 - nx) / max(arm_R0 - arm_xmin, 1e-4))
            set_vert(vert.index, {
                "R_Arm": 0.25 * tip,
                "Head": 0.40 + 0.20 * (1.0 - tip),
                "Root": 0.60 - 0.20 * tip - 0.25 * tip,
            })
        else:
            set_vert(vert.index, {"Head": 0.30 + 0.50 * t, "Root": 0.70 - 0.50 * t})
        collar_stripped += 1
print("COLLAR_STRIP_LIMBS", collar_stripped)

# Re-assert foot tip weights after strips (asymmetric meshes lose the short side).
# Use each side's own extent so the shorter foot still gets real influence.
foot_boost = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    if nz > 0.15:
        continue
    # Side-relative starts (more inclusive than paint thresholds).
    l0 = foot_xmax * 0.22
    r0 = foot_xmin * 0.22
    if nx > l0:
        foot = min(1.0, max(0.0, (0.15 - nz) / 0.15))
        lateral = min(1.0, max(0.0, (nx - l0) / max(foot_xmax - l0, 1e-4)))
        limb = min(0.80, 0.90 * foot * (0.30 + 0.70 * lateral))
        if limb < 0.10:
            continue
        set_vert(vert.index, {
            "L_Shin": 0.52 * limb,
            "L_Leg": 0.36 * limb,
            "Root": max(0.20, 1.0 - limb),
        })
        foot_boost += 1
    elif nx < r0:
        foot = min(1.0, max(0.0, (0.15 - nz) / 0.15))
        lateral = min(1.0, max(0.0, (r0 - nx) / max(r0 - foot_xmin, 1e-4)))
        limb = min(0.80, 0.90 * foot * (0.30 + 0.70 * lateral))
        if limb < 0.10:
            continue
        set_vert(vert.index, {
            "R_Shin": 0.52 * limb,
            "R_Leg": 0.36 * limb,
            "Root": max(0.20, 1.0 - limb),
        })
        foot_boost += 1
print("FOOT_TIP_BOOST", foot_boost)

# Re-assert flipper tip weights so arm flaps actually read (keep armpit on torso).
arm_boost = 0
for vert in body.data.vertices:
    wp = mw @ vert.co
    nx = (wp.x - cx) / hw
    nz = (wp.z - minv.z) / h
    if not (0.40 < nz < 0.68):
        continue
    l0 = arm_xmax * 0.45
    r0 = arm_xmin * 0.45
    if nx > l0:
        tip = min(1.0, max(0.0, (nx - l0) / max(arm_xmax - l0, 1e-4)))
        tip = tip ** 1.1
        if tip < 0.12:
            continue
        set_vert(vert.index, {
            "L_Forearm": 0.20 + 0.55 * tip,
            "L_Arm": 0.40 - 0.10 * tip,
            "Spine": max(0.05, 0.40 - 0.45 * tip),
        })
        arm_boost += 1
    elif nx < r0:
        tip = min(1.0, max(0.0, (r0 - nx) / max(r0 - arm_xmin, 1e-4)))
        tip = tip ** 1.1
        if tip < 0.12:
            continue
        set_vert(vert.index, {
            "R_Forearm": 0.20 + 0.55 * tip,
            "R_Arm": 0.40 - 0.10 * tip,
            "Spine": max(0.05, 0.40 - 0.45 * tip),
        })
        arm_boost += 1
print("ARM_TIP_BOOST", arm_boost)

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

# idle — soft Root bounce + gentle flipper settle
clear_pose()
idle = ensure_action("idle")
set_bone_keys(idle, "Root", [
    (1, (0, 0, 0), (0, 0.0, 0)),
    (24, (0, 0, 0), (0, 0.018, 0)),
    (48, (0, 0, 0), (0, 0.0, 0)),
])
set_bone_keys(idle, "L_Arm", [(1, (6, 0, 14)), (24, (12, 0, 20)), (48, (6, 0, 14))])
set_bone_keys(idle, "R_Arm", [(1, (6, 0, -14)), (24, (12, 0, -20)), (48, (6, 0, -14))])
set_bone_keys(idle, "L_Forearm", [(1, (0, 0, 4)), (24, (0, 0, 10)), (48, (0, 0, 4))])
set_bone_keys(idle, "R_Forearm", [(1, (0, 0, -4)), (24, (0, 0, -10)), (48, (0, 0, -4))])

# walk — tip-foot shuffle + opposing flipper swing
clear_pose()
walk = ensure_action("walk")
set_bone_keys(walk, "Root", [
    (1, (0, 0, 0), (0, 0.0, 0)),
    (6, (0, 0, 0), (0, 0.02, 0)),
    (11, (0, 0, 0), (0, 0.0, 0)),
    (16, (0, 0, 0), (0, 0.02, 0)),
    (22, (0, 0, 0), (0, 0.0, 0)),
])
set_bone_keys(walk, "L_Leg", [(1, (-9, 0, 0)), (11, (9, 0, 0)), (22, (-9, 0, 0))])
set_bone_keys(walk, "R_Leg", [(1, (9, 0, 0)), (11, (-9, 0, 0)), (22, (9, 0, 0))])
set_bone_keys(walk, "L_Shin", [(1, (5, 0, 0)), (11, (1, 0, 0)), (22, (5, 0, 0))])
set_bone_keys(walk, "R_Shin", [(1, (1, 0, 0)), (11, (5, 0, 0)), (22, (1, 0, 0))])
# Arms opposite the legs — readable mascot flap without melting armpits.
set_bone_keys(walk, "L_Arm", [(1, (12, 0, 20)), (11, (-10, 0, 10)), (22, (12, 0, 20))])
set_bone_keys(walk, "R_Arm", [(1, (-10, 0, -10)), (11, (12, 0, -20)), (22, (-10, 0, -10))])
set_bone_keys(walk, "L_Forearm", [(1, (0, 0, 12)), (11, (0, 0, -4)), (22, (0, 0, 12))])
set_bone_keys(walk, "R_Forearm", [(1, (0, 0, -4)), (11, (0, 0, 12)), (22, (0, 0, -4))])

# run — bigger tip kick + stronger opposing arm flaps
clear_pose()
run = ensure_action("run")
set_bone_keys(run, "Root", [
    (1, (0, 0, 0), (0, 0.01, 0)),
    (4, (0, 0, 0), (0, 0.028, 0)),
    (7, (0, 0, 0), (0, 0.01, 0)),
    (10, (0, 0, 0), (0, 0.028, 0)),
    (13, (0, 0, 0), (0, 0.01, 0)),
])
set_bone_keys(run, "L_Leg", [(1, (-12, 0, 0)), (7, (12, 0, 0)), (13, (-12, 0, 0))])
set_bone_keys(run, "R_Leg", [(1, (12, 0, 0)), (7, (-12, 0, 0)), (13, (12, 0, 0))])
set_bone_keys(run, "L_Shin", [(1, (7, 0, 0)), (7, (2, 0, 0)), (13, (7, 0, 0))])
set_bone_keys(run, "R_Shin", [(1, (2, 0, 0)), (7, (7, 0, 0)), (13, (2, 0, 0))])
set_bone_keys(run, "L_Arm", [(1, (16, 0, 24)), (7, (-14, 0, 12)), (13, (16, 0, 24))])
set_bone_keys(run, "R_Arm", [(1, (-14, 0, -12)), (7, (16, 0, -24)), (13, (-14, 0, -12))])
set_bone_keys(run, "L_Forearm", [(1, (0, 0, 14)), (7, (0, 0, -6)), (13, (0, 0, 14))])
set_bone_keys(run, "R_Forearm", [(1, (0, 0, -6)), (7, (0, 0, 14)), (13, (0, 0, -6))])

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
