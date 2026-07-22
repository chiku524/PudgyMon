#!/usr/bin/env python3
"""Build detailed procedural accessory + Nest/stage prop GLBs (Blender).

Usage:
  python scripts/build_procedural_party_assets.py
  python scripts/build_procedural_party_assets.py --only acc_hat_party_crown_01,env_nest_egg_01
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_REGISTRY = _REPO / "assets" / "studio_registry.json"
_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")

# asset_id -> (target_height_m, notes)
CATALOG: dict[str, tuple[float, str]] = {
    # Hats
    "acc_hat_party_crown_01": (0.28, "Party crown hat"),
    "acc_hat_racer_cap_01": (0.22, "Racer cap hat"),
    "acc_hat_vibe_mushroom_01": (0.32, "Mushroom hat"),
    "acc_hat_blaster_beanie_01": (0.30, "Star beanie"),
    "acc_hat_propeller_01": (0.34, "Propeller beanie"),
    "acc_hat_flower_01": (0.36, "Daisy flower hat"),
    "acc_hat_chef_01": (0.38, "Chef hat"),
    "acc_hat_sleep_01": (0.24, "Sleep cap"),
    # Necklaces
    "acc_necklace_shell_01": (0.18, "Shell pendant"),
    "acc_necklace_medal_01": (0.18, "Party medal"),
    "acc_necklace_beads_01": (0.16, "Candy beads"),
    "acc_necklace_bell_01": (0.16, "Jingle bell"),
    # Shoes (pair)
    "acc_shoes_racer_01": (0.16, "Racer shoes pair"),
    "acc_shoes_party_01": (0.16, "Party shoes pair"),
    "acc_shoes_boots_01": (0.20, "Rain boots pair"),
    "acc_shoes_slippers_01": (0.12, "Slippers pair"),
    # Back
    "acc_back_cape_01": (0.55, "Party cape"),
    "acc_back_wings_01": (0.45, "Angel wings"),
    "acc_back_pack_01": (0.40, "Vibe orb backpack"),
    # Face
    "acc_face_shades_01": (0.12, "Sunglasses"),
    "acc_face_goggles_01": (0.12, "Racer goggles"),
    "acc_face_mask_01": (0.14, "Party half-mask"),
    # Hands
    "acc_hands_mittens_01": (0.18, "Mittens pair"),
    "acc_hands_gloves_01": (0.18, "Racer gloves pair"),
    # Nest
    "env_nest_egg_01": (3.2, "Nest centerpiece egg"),
    "env_nest_bench_01": (0.7, "Nest bench"),
    "prop_vibe_mushroom_01": (1.9, "Vibe mushroom"),
    "env_pad_race_01": (0.28, "Race mode pad"),
    "env_pad_vibe_01": (0.28, "Vibe mode pad"),
    "env_pad_shooter_01": (0.28, "Shooter mode pad"),
    "env_pad_party_01": (0.28, "Full party pad"),
    # Stage
    "prop_vibe_orb_01": (0.45, "Vibe collect orb"),
    "prop_race_checkpoint_01": (2.2, "Race checkpoint arch"),
    "prop_race_cone_01": (0.75, "Race cone"),
    "prop_cover_block_01": (1.1, "Shooter cover block"),
    "prop_target_star_01": (0.7, "Shooter star target"),
}

_WORKER = r'''
import bpy
import math
import mathutils
from pathlib import Path

OUT_DIR = Path(r"__OUT_DIR__")
ONLY = set(__ONLY__)

bpy.ops.wm.read_factory_settings(use_empty=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, roughness=0.62, emission=None):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = 0.0
    if "Coat Weight" in p.inputs:
        p.inputs["Coat Weight"].default_value = 0.0
    if emission is not None and "Emission Color" in p.inputs:
        p.inputs["Emission Color"].default_value = (*emission, 1.0)
        if "Emission Strength" in p.inputs:
            p.inputs["Emission Strength"].default_value = 2.2
    m.blend_method = "OPAQUE"
    return m


def sphere(name, r, loc, material, scale=(1, 1, 1), seg=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=rings)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def cyl(name, r, depth, loc, material, rot=(0, 0, 0), scale=(1, 1, 1), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def cone(name, r1, depth, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, depth=depth, location=loc, vertices=16)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def torus(name, major, minor, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor, location=loc, major_segments=24, minor_segments=10
    )
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def cube(name, size, loc, material, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] * scale[0], size[1] * scale[1], size[2] * scale[2])
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def join_all(name):
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = name
    body.data.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return body


def floor_center(obj, keep_z=True):
    def aabb(o):
        mn = mathutils.Vector((1e9, 1e9, 1e9))
        mx = mathutils.Vector((-1e9, -1e9, -1e9))
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            mn = mathutils.Vector(tuple(min(mn[i], w[i]) for i in range(3)))
            mx = mathutils.Vector(tuple(max(mx[i], w[i]) for i in range(3)))
        return mn, mx

    mn, mx = aabb(obj)
    cx = 0.5 * (mn.x + mx.x)
    cy = 0.5 * (mn.y + mx.y)
    cz = mn.z if keep_z else 0.5 * (mn.z + mx.z)
    obj.location -= mathutils.Vector((cx, cy, cz if keep_z else cz))
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def export_asset(asset_id, wear_origin_at_zero=True):
    body = join_all(asset_id)
    if wear_origin_at_zero:
        floor_center(body, keep_z=True)
    out = OUT_DIR / asset_id / f"{asset_id}.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(out),
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_yup=True,
    )
    print("OK", asset_id)


def want(aid):
    return (not ONLY) or (aid in ONLY)


# ---------- HATS (origin = bottom of hat / crown sit point) ----------
def build_hat_party_crown():
    clear_scene()
    gold = mat("Gold", (1.0, 0.78, 0.28), 0.4)
    coral = mat("Coral", (1.0, 0.45, 0.4), 0.55)
    gem = mat("Gem", (0.35, 0.9, 1.0), 0.3, emission=(0.2, 0.55, 0.7))
    # Band
    cyl("Band", 0.16, 0.06, (0, 0, 0.03), gold)
    # Points
    for i, ang in enumerate(range(0, 360, 60)):
        a = math.radians(ang)
        x, y = math.cos(a) * 0.13, math.sin(a) * 0.13
        cone(f"Point{i}", 0.045, 0.14, (x, y, 0.12), coral)
        sphere(f"Gem{i}", 0.028, (x, y, 0.20), gem, seg=12, rings=8)
    # Front jewel
    sphere("FrontGem", 0.04, (0, -0.15, 0.06), gem, seg=12, rings=8)
    export_asset("acc_hat_party_crown_01")


def build_hat_racer_cap():
    clear_scene()
    cyan = mat("Cyan", (0.25, 0.85, 0.95), 0.55)
    white = mat("White", (0.95, 0.96, 0.98), 0.6)
    sphere("Crown", 0.15, (0, 0.02, 0.08), cyan, scale=(1.15, 1.05, 0.7), seg=20, rings=12)
    # Bill
    cube("Bill", (0.22, 0.14, 0.03), (0, -0.14, 0.04), white)
    # Stripe
    cube("Stripe", (0.04, 0.22, 0.02), (0, 0.0, 0.14), white)
    export_asset("acc_hat_racer_cap_01")


def build_hat_mushroom():
    clear_scene()
    teal = mat("Teal", (0.25, 0.8, 0.7), 0.55, emission=(0.1, 0.35, 0.3))
    cream = mat("Cream", (1.0, 0.9, 0.75), 0.65)
    stem = mat("Stem", (0.95, 0.85, 0.7), 0.7)
    cyl("Stem", 0.08, 0.08, (0, 0, 0.04), stem)
    sphere("Cap", 0.18, (0, 0, 0.14), teal, scale=(1.2, 1.2, 0.65))
    for i, ang in enumerate((0, 72, 144, 216, 288)):
        a = math.radians(ang)
        sphere(f"Dot{i}", 0.03, (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.2), cream, seg=10, rings=6)
    export_asset("acc_hat_vibe_mushroom_01")


def build_hat_beanie():
    clear_scene()
    pink = mat("Pink", (1.0, 0.45, 0.7), 0.6)
    mag = mat("Mag", (0.9, 0.25, 0.55), 0.55)
    star = mat("Star", (1.0, 0.9, 0.35), 0.45, emission=(0.5, 0.4, 0.1))
    sphere("Beanie", 0.16, (0, 0, 0.1), pink, scale=(1.1, 1.05, 0.85))
    cube("Cuff", (0.34, 0.34, 0.05), (0, 0, 0.03), mag)
    sphere("Pom", 0.055, (0, 0, 0.26), star, seg=12, rings=8)
    export_asset("acc_hat_blaster_beanie_01")


def build_hat_propeller():
    clear_scene()
    yellow = mat("Yellow", (1.0, 0.88, 0.25), 0.55)
    sky = mat("Sky", (0.4, 0.75, 1.0), 0.55)
    sphere("Hat", 0.15, (0, 0, 0.1), sky, scale=(1.1, 1.05, 0.8))
    cyl("Mast", 0.015, 0.12, (0, 0, 0.22), yellow)
    cube("Blade1", (0.22, 0.04, 0.015), (0, 0, 0.28), yellow)
    cube("Blade2", (0.04, 0.22, 0.015), (0, 0, 0.28), yellow)
    export_asset("acc_hat_propeller_01")


def build_hat_flower():
    clear_scene()
    cream = mat("Cream", (1.0, 0.95, 0.8), 0.6)
    lime = mat("Lime", (0.55, 0.9, 0.35), 0.55)
    gold = mat("Gold", (1.0, 0.8, 0.2), 0.4)
    for i in range(8):
        a = math.radians(i * 45)
        sphere(f"Petal{i}", 0.09, (math.cos(a) * 0.12, math.sin(a) * 0.12, 0.1), cream, scale=(1.3, 0.7, 0.45), seg=12, rings=8)
    sphere("Center", 0.08, (0, 0, 0.1), gold, seg=14, rings=10)
    cyl("LeafBase", 0.07, 0.05, (0, 0, 0.025), lime)
    export_asset("acc_hat_flower_01")


def build_hat_chef():
    clear_scene()
    white = mat("White", (0.97, 0.97, 0.95), 0.65)
    coral = mat("Coral", (1.0, 0.5, 0.4), 0.55)
    cyl("Band", 0.14, 0.05, (0, 0, 0.025), coral)
    sphere("Puff", 0.18, (0, 0, 0.18), white, scale=(1.05, 1.05, 1.15))
    export_asset("acc_hat_chef_01")


def build_hat_sleep():
    clear_scene()
    blue = mat("Blue", (0.55, 0.7, 1.0), 0.6)
    white = mat("White", (0.95, 0.95, 0.98), 0.55)
    sphere("Cap", 0.15, (0, 0.02, 0.08), blue, scale=(1.15, 1.1, 0.7))
    # Floppy tip
    sphere("Tip", 0.07, (0.12, 0.05, 0.16), blue, scale=(1.4, 0.8, 0.7), seg=12, rings=8)
    cube("Trim", (0.32, 0.32, 0.03), (0, 0, 0.02), white)
    export_asset("acc_hat_sleep_01")


# ---------- NECKLACES (origin = wear point at neck) ----------
def build_necklace_shell():
    clear_scene()
    teal = mat("Teal", (0.3, 0.75, 0.75), 0.5)
    cream = mat("Cream", (1.0, 0.9, 0.75), 0.55)
    gold = mat("Gold", (1.0, 0.8, 0.3), 0.4)
    torus("Chain", 0.1, 0.012, (0, 0, 0.0), gold, rot=(math.radians(90), 0, 0))
    sphere("Shell", 0.06, (0, -0.02, -0.1), teal, scale=(1.2, 0.7, 1.0), seg=14, rings=10)
    sphere("Pearl", 0.02, (0, -0.05, -0.1), cream, seg=10, rings=6)
    export_asset("acc_necklace_shell_01", wear_origin_at_zero=True)


def build_necklace_medal():
    clear_scene()
    gold = mat("Gold", (1.0, 0.82, 0.25), 0.35)
    coral = mat("Coral", (1.0, 0.45, 0.35), 0.5)
    cyl("Medal", 0.07, 0.02, (0, 0, -0.12), gold)
    cube("RibbonL", (0.04, 0.02, 0.12), (-0.03, 0, -0.02), coral)
    cube("RibbonR", (0.04, 0.02, 0.12), (0.03, 0, -0.02), coral)
    torus("Ring", 0.04, 0.008, (0, 0, 0.02), gold, rot=(math.radians(90), 0, 0))
    export_asset("acc_necklace_medal_01")


def build_necklace_beads():
    clear_scene()
    colors = [
        (1.0, 0.4, 0.45),
        (0.4, 0.85, 0.95),
        (1.0, 0.85, 0.3),
        (0.55, 0.9, 0.45),
        (0.85, 0.5, 1.0),
    ]
    for i in range(10):
        a = math.radians(i * 36)
        c = colors[i % len(colors)]
        m = mat(f"Bead{i}", c, 0.45)
        sphere(f"B{i}", 0.025, (math.cos(a) * 0.1, math.sin(a) * 0.04, math.sin(a) * 0.02 - 0.02), m, seg=10, rings=6)
    export_asset("acc_necklace_beads_01")


def build_necklace_bell():
    clear_scene()
    yellow = mat("Yellow", (1.0, 0.85, 0.25), 0.4)
    coral = mat("Coral", (1.0, 0.5, 0.4), 0.5)
    torus("Loop", 0.035, 0.008, (0, 0, 0.02), coral, rot=(math.radians(90), 0, 0))
    sphere("Bell", 0.055, (0, 0, -0.08), yellow, scale=(1.0, 1.0, 1.15), seg=14, rings=10)
    sphere("Clapper", 0.015, (0, 0, -0.13), coral, seg=8, rings=6)
    export_asset("acc_necklace_bell_01")


# ---------- SHOES (pair, origin between feet at floor) ----------
def build_shoes(aid, col_a, col_b, tall=False):
    clear_scene()
    a = mat("A", col_a, 0.55)
    b = mat("B", col_b, 0.55)
    h = 0.12 if tall else 0.07
    for side, x in (("L", -0.12), ("R", 0.12)):
        sphere(f"Shoe{side}", 0.08, (x, -0.02, h * 0.45), a, scale=(1.0, 1.35, 0.7 if not tall else 1.1), seg=14, rings=10)
        if tall:
            cyl(f"Cuff{side}", 0.07, 0.08, (x, 0.0, 0.14), b)
        cube(f"Sole{side}", (0.12, 0.18, 0.03), (x, -0.02, 0.015), b)
        cube(f"Stripe{side}", (0.03, 0.14, 0.02), (x, -0.02, h * 0.6), b)
    export_asset(aid)


# ---------- BACK ----------
def build_cape():
    clear_scene()
    coral = mat("Coral", (1.0, 0.4, 0.35), 0.6)
    gold = mat("Gold", (1.0, 0.8, 0.3), 0.4)
    # Collar
    torus("Collar", 0.12, 0.025, (0, 0.02, 0.05), gold, rot=(math.radians(70), 0, 0))
    # Cape body hanging down −Y / back +Y in Blender: hang in +Y (back)
    cube("Cape", (0.45, 0.08, 0.55), (0, 0.12, -0.2), coral)
    sphere("HemL", 0.06, (-0.18, 0.12, -0.45), coral, seg=10, rings=6)
    sphere("HemR", 0.06, (0.18, 0.12, -0.45), coral, seg=10, rings=6)
    export_asset("acc_back_cape_01")


def build_wings():
    clear_scene()
    cream = mat("Cream", (1.0, 0.92, 0.85), 0.55)
    pink = mat("Pink", (1.0, 0.7, 0.8), 0.55)
    for side, sx in (("L", -1), ("R", 1)):
        sphere(f"Wing{side}", 0.16, (sx * 0.22, 0.08, 0.05), cream, scale=(0.7, 0.35, 1.2), seg=14, rings=10)
        sphere(f"Tip{side}", 0.08, (sx * 0.34, 0.1, 0.18), pink, scale=(0.6, 0.35, 0.9), seg=12, rings=8)
    cube("Harness", (0.2, 0.06, 0.08), (0, 0.02, 0.0), pink)
    export_asset("acc_back_wings_01")


def build_pack():
    clear_scene()
    teal = mat("Teal", (0.25, 0.8, 0.85), 0.5, emission=(0.1, 0.4, 0.45))
    cream = mat("Cream", (0.95, 0.9, 0.8), 0.6)
    sphere("Orb", 0.16, (0, 0.1, 0.0), teal, seg=18, rings=12)
    cube("StrapL", (0.04, 0.08, 0.22), (-0.08, 0.0, 0.0), cream)
    cube("StrapR", (0.04, 0.08, 0.22), (0.08, 0.0, 0.0), cream)
    sphere("Glow", 0.05, (0, 0.1, 0.12), cream, seg=10, rings=6)
    export_asset("acc_back_pack_01")


# ---------- FACE ----------
def build_shades():
    clear_scene()
    black = mat("Black", (0.08, 0.08, 0.1), 0.35)
    gold = mat("Gold", (1.0, 0.8, 0.25), 0.35)
    sphere("LensL", 0.06, (-0.07, -0.02, 0.0), black, scale=(1.1, 0.35, 0.9), seg=12, rings=8)
    sphere("LensR", 0.06, (0.07, -0.02, 0.0), black, scale=(1.1, 0.35, 0.9), seg=12, rings=8)
    cube("Bridge", (0.06, 0.02, 0.02), (0, -0.02, 0.0), gold)
    cube("ArmL", (0.02, 0.1, 0.02), (-0.13, 0.04, 0.0), gold)
    cube("ArmR", (0.02, 0.1, 0.02), (0.13, 0.04, 0.0), gold)
    export_asset("acc_face_shades_01")


def build_goggles():
    clear_scene()
    cyan = mat("Cyan", (0.3, 0.9, 1.0), 0.35, emission=(0.15, 0.4, 0.5))
    grey = mat("Grey", (0.35, 0.4, 0.45), 0.5)
    torus("RingL", 0.055, 0.012, (-0.07, 0, 0), grey, rot=(math.radians(90), 0, 0))
    torus("RingR", 0.055, 0.012, (0.07, 0, 0), grey, rot=(math.radians(90), 0, 0))
    sphere("GlassL", 0.045, (-0.07, -0.01, 0), cyan, scale=(1, 0.4, 1), seg=12, rings=8)
    sphere("GlassR", 0.045, (0.07, -0.01, 0), cyan, scale=(1, 0.4, 1), seg=12, rings=8)
    cube("Strap", (0.28, 0.04, 0.03), (0, 0.06, 0), grey)
    export_asset("acc_face_goggles_01")


def build_mask():
    clear_scene()
    pink = mat("Pink", (1.0, 0.55, 0.7), 0.55)
    spark = mat("Spark", (1.0, 0.9, 0.4), 0.4, emission=(0.5, 0.4, 0.1))
    sphere("Mask", 0.12, (0, -0.02, 0.0), pink, scale=(1.3, 0.45, 0.9), seg=16, rings=10)
    for i, x in enumerate((-0.06, 0.0, 0.06)):
        sphere(f"S{i}", 0.018, (x, -0.05, 0.04), spark, seg=8, rings=6)
    export_asset("acc_face_mask_01")


# ---------- HANDS ----------
def build_mittens():
    clear_scene()
    coral = mat("Coral", (1.0, 0.5, 0.4), 0.6)
    cream = mat("Cream", (1.0, 0.9, 0.8), 0.65)
    for side, x in (("L", -0.18), ("R", 0.18)):
        sphere(f"Mitt{side}", 0.08, (x, 0, 0.0), coral, scale=(1.0, 0.85, 1.1), seg=12, rings=8)
        cyl(f"Cuff{side}", 0.06, 0.05, (x, 0, 0.08), cream)
    export_asset("acc_hands_mittens_01")


def build_gloves():
    clear_scene()
    cyan = mat("Cyan", (0.25, 0.85, 0.95), 0.55)
    white = mat("White", (0.95, 0.95, 0.98), 0.55)
    for side, x in (("L", -0.18), ("R", 0.18)):
        sphere(f"Palm{side}", 0.07, (x, 0, 0.0), cyan, scale=(1.0, 0.8, 1.15), seg=12, rings=8)
        cube(f"Stripe{side}", (0.04, 0.08, 0.02), (x, -0.04, 0.02), white)
        for f in range(3):
            sphere(f"F{side}{f}", 0.025, (x + (f - 1) * 0.03, -0.05, 0.06), cyan, seg=8, rings=6)
    export_asset("acc_hands_gloves_01")


# ---------- NEST / STAGE PROPS ----------
def build_nest_egg():
    clear_scene()
    shell = mat("Shell", (1.0, 0.78, 0.5), 0.55, emission=(0.35, 0.18, 0.05))
    speck = mat("Speck", (1.0, 0.55, 0.35), 0.5)
    sphere("Egg", 1.5, (0, 0, 1.55), shell, scale=(1.0, 1.0, 1.25), seg=28, rings=18)
    for i in range(8):
        a = math.radians(i * 45)
        sphere(f"Sp{i}", 0.18, (math.cos(a) * 0.9, math.sin(a) * 0.9, 1.3 + (i % 3) * 0.25), speck, seg=10, rings=6)
    # Nest bowl
    nest = mat("Nest", (0.55, 0.35, 0.2), 0.7)
    torus("Bowl", 1.4, 0.25, (0, 0, 0.25), nest)
    export_asset("env_nest_egg_01")


def build_bench():
    clear_scene()
    coral = mat("Coral", (0.95, 0.55, 0.35), 0.6)
    cream = mat("Cream", (1.0, 0.9, 0.8), 0.65)
    cube("Seat", (2.6, 0.7, 0.18), (0, 0, 0.35), coral)
    cube("Back", (2.6, 0.18, 0.55), (0, 0.28, 0.65), cream)
    for x in (-1.0, 1.0):
        cyl(f"Leg{x}", 0.08, 0.35, (x, 0, 0.17), cream)
    export_asset("env_nest_bench_01")


def build_mushroom():
    clear_scene()
    stem_m = mat("Stem", (0.95, 0.85, 0.65), 0.65)
    cap_m = mat("Cap", (1.0, 0.45, 0.4), 0.5, emission=(0.35, 0.12, 0.08))
    spot = mat("Spot", (1.0, 0.95, 0.85), 0.6)
    cyl("Stem", 0.22, 1.2, (0, 0, 0.6), stem_m, verts=18)
    sphere("Cap", 0.85, (0, 0, 1.35), cap_m, scale=(1.15, 1.15, 0.55), seg=24, rings=14)
    for i, ang in enumerate(range(0, 360, 45)):
        a = math.radians(ang)
        sphere(f"D{i}", 0.12, (math.cos(a) * 0.45, math.sin(a) * 0.45, 1.5), spot, seg=10, rings=6)
    export_asset("prop_vibe_mushroom_01")


def build_pad(aid, color, emission):
    clear_scene()
    m = mat("Pad", color, 0.45, emission=emission)
    rim = mat("Rim", (0.95, 0.95, 0.9), 0.5)
    cyl("Disk", 2.6, 0.22, (0, 0, 0.11), m, verts=32)
    torus("Ring", 2.55, 0.08, (0, 0, 0.22), rim)
    export_asset(aid)


def build_vibe_orb():
    clear_scene()
    orb = mat("Orb", (1.0, 0.9, 0.35), 0.4, emission=(0.6, 0.45, 0.1))
    core = mat("Core", (1.0, 1.0, 0.85), 0.3, emission=(0.8, 0.7, 0.3))
    sphere("Shell", 0.22, (0, 0, 0.22), orb, seg=20, rings=14)
    sphere("Core", 0.1, (0, 0, 0.22), core, seg=12, rings=8)
    export_asset("prop_vibe_orb_01")


def build_checkpoint():
    clear_scene()
    cyan = mat("Cyan", (0.25, 0.85, 1.0), 0.45, emission=(0.15, 0.45, 0.55))
    white = mat("White", (0.95, 0.95, 0.98), 0.55)
    for x in (-1.0, 1.0):
        cyl(f"Post{x}", 0.12, 2.0, (x, 0, 1.0), cyan, verts=12)
    # Arch
    torus("Arch", 1.05, 0.1, (0, 0, 2.0), cyan, rot=(0, math.radians(90), 0))
    cube("Banner", (1.6, 0.08, 0.35), (0, 0, 2.15), white)
    export_asset("prop_race_checkpoint_01")


def build_cone():
    clear_scene()
    orange = mat("Orange", (1.0, 0.45, 0.15), 0.5)
    white = mat("White", (0.95, 0.95, 0.95), 0.55)
    cone("Body", 0.22, 0.7, (0, 0, 0.35), orange)
    torus("Stripe", 0.16, 0.03, (0, 0, 0.35), white)
    export_asset("prop_race_cone_01")


def build_cover():
    clear_scene()
    teal = mat("Teal", (0.25, 0.75, 0.7), 0.55)
    cream = mat("Cream", (0.95, 0.9, 0.8), 0.6)
    cube("Block", (1.8, 1.2, 1.0), (0, 0, 0.5), teal)
    cube("Trim", (1.9, 1.3, 0.12), (0, 0, 1.05), cream)
    export_asset("prop_cover_block_01")


def build_star():
    clear_scene()
    yellow = mat("Yellow", (1.0, 0.88, 0.25), 0.4, emission=(0.55, 0.4, 0.08))
    # Soft star from spheres
    sphere("Core", 0.22, (0, 0, 0.35), yellow, seg=14, rings=10)
    for i in range(5):
        a = math.radians(i * 72 - 90)
        sphere(f"P{i}", 0.12, (math.cos(a) * 0.28, math.sin(a) * 0.28, 0.35), yellow, scale=(1.4, 0.7, 0.7), seg=10, rings=6)
    cyl("Stand", 0.05, 0.3, (0, 0, 0.12), yellow)
    export_asset("prop_target_star_01")


builders = [
    ("acc_hat_party_crown_01", build_hat_party_crown),
    ("acc_hat_racer_cap_01", build_hat_racer_cap),
    ("acc_hat_vibe_mushroom_01", build_hat_mushroom),
    ("acc_hat_blaster_beanie_01", build_hat_beanie),
    ("acc_hat_propeller_01", build_hat_propeller),
    ("acc_hat_flower_01", build_hat_flower),
    ("acc_hat_chef_01", build_hat_chef),
    ("acc_hat_sleep_01", build_hat_sleep),
    ("acc_necklace_shell_01", build_necklace_shell),
    ("acc_necklace_medal_01", build_necklace_medal),
    ("acc_necklace_beads_01", build_necklace_beads),
    ("acc_necklace_bell_01", build_necklace_bell),
    ("acc_shoes_racer_01", lambda: build_shoes("acc_shoes_racer_01", (0.25, 0.85, 0.95), (0.95, 0.95, 0.98))),
    ("acc_shoes_party_01", lambda: build_shoes("acc_shoes_party_01", (1.0, 0.45, 0.4), (1.0, 0.8, 0.3))),
    ("acc_shoes_boots_01", lambda: build_shoes("acc_shoes_boots_01", (0.95, 0.75, 0.25), (0.25, 0.75, 0.7), tall=True)),
    ("acc_shoes_slippers_01", lambda: build_shoes("acc_shoes_slippers_01", (1.0, 0.7, 0.85), (0.95, 0.9, 0.95))),
    ("acc_back_cape_01", build_cape),
    ("acc_back_wings_01", build_wings),
    ("acc_back_pack_01", build_pack),
    ("acc_face_shades_01", build_shades),
    ("acc_face_goggles_01", build_goggles),
    ("acc_face_mask_01", build_mask),
    ("acc_hands_mittens_01", build_mittens),
    ("acc_hands_gloves_01", build_gloves),
    ("env_nest_egg_01", build_nest_egg),
    ("env_nest_bench_01", build_bench),
    ("prop_vibe_mushroom_01", build_mushroom),
    ("env_pad_race_01", lambda: build_pad("env_pad_race_01", (0.2, 0.85, 1.0), (0.15, 0.5, 0.7))),
    ("env_pad_vibe_01", lambda: build_pad("env_pad_vibe_01", (1.0, 0.85, 0.2), (0.6, 0.45, 0.08))),
    ("env_pad_shooter_01", lambda: build_pad("env_pad_shooter_01", (1.0, 0.4, 0.55), (0.55, 0.15, 0.25))),
    ("env_pad_party_01", lambda: build_pad("env_pad_party_01", (0.55, 1.0, 0.45), (0.2, 0.55, 0.2))),
    ("prop_vibe_orb_01", build_vibe_orb),
    ("prop_race_checkpoint_01", build_checkpoint),
    ("prop_race_cone_01", build_cone),
    ("prop_cover_block_01", build_cover),
    ("prop_target_star_01", build_star),
]

for aid, fn in builders:
    if want(aid):
        fn()

print("DONE", len([a for a, _ in builders if want(a)]))
'''


def _register_all(ids: list[str]) -> None:
    registry = {"import_root": "res://assets/models", "assets": []}
    if _REGISTRY.is_file():
        registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    by_id = {
        a["asset_id"]: a
        for a in registry.get("assets", [])
        if isinstance(a, dict) and a.get("asset_id")
    }
    for aid in ids:
        height, notes = CATALOG[aid]
        by_id[aid] = {
            "asset_id": aid,
            "target_height": height,
            "uniform_scale": 1.0,
            "notes": f"Procedural party asset — {notes}",
        }
        readme = _MODELS / aid / "README.txt"
        readme.write_text(
            f"{aid}\nProcedural Blender party asset.\nRebuild: python scripts/build_procedural_party_assets.py --only {aid}\n",
            encoding="utf-8",
        )
    registry["assets"] = sorted(by_id.values(), key=lambda x: x["asset_id"])
    _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", help="Comma-separated asset ids")
    args = parser.parse_args()
    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1

    only = [s.strip() for s in args.only.split(",") if s.strip()]
    for aid in only:
        if aid not in CATALOG:
            print(f"error: unknown asset {aid}", file=sys.stderr)
            return 1

    worker = _REPO / "scripts" / "_party_assets_worker.py"
    script = _WORKER.replace("__OUT_DIR__", str(_MODELS.resolve()).replace("\\", "/")).replace(
        "__ONLY__", repr(only)
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
    if proc.returncode != 0:
        print(proc.stderr[-4000:], file=sys.stderr)
        return 1

    built = only if only else list(CATALOG.keys())
    missing = [a for a in built if not (_MODELS / a / f"{a}.glb").is_file()]
    if missing:
        print(f"error: missing glbs: {missing}", file=sys.stderr)
        return 1
    _register_all(built)
    print(f"registered {len(built)} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
