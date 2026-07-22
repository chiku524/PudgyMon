#!/usr/bin/env python3
"""Apply a Blankos/Pokemon-like vinyl material pass to an existing character GLB (no geo rebuild)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")

_WORKER = r'''
import bpy
from pathlib import Path

IN_PATH = Path(r"__IN_PATH__")
OUT_PATH = Path(r"__OUT_PATH__")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(IN_PATH))

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

        normal_in = principled.inputs.get("Normal")
        if normal_in and normal_in.is_linked:
            link = normal_in.links[0]
            from_node = link.from_node
            if from_node.type == "NORMAL_MAP":
                from_node.inputs["Strength"].default_value = 0.22

        rough_in = principled.inputs.get("Roughness")
        if rough_in and rough_in.is_linked:
            src = rough_in.links[0].from_socket
            nt.links.remove(rough_in.links[0])
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = 0.32
            mul.location = (principled.location.x - 220, principled.location.y - 120)
            nt.links.new(src, mul.inputs[0])
            nt.links.new(mul.outputs["Value"], rough_in)
        elif rough_in:
            rough_in.default_value = 0.2

        if "Coat Weight" in principled.inputs and not principled.inputs["Coat Weight"].is_linked:
            principled.inputs["Coat Weight"].default_value = 0.5
        if "Coat Roughness" in principled.inputs and not principled.inputs["Coat Roughness"].is_linked:
            principled.inputs["Coat Roughness"].default_value = 0.1
        if "Clearcoat" in principled.inputs and not principled.inputs["Clearcoat"].is_linked:
            principled.inputs["Clearcoat"].default_value = 0.5
        if "Clearcoat Roughness" in principled.inputs and not principled.inputs["Clearcoat Roughness"].is_linked:
            principled.inputs["Clearcoat Roughness"].default_value = 0.1

        base_in = principled.inputs.get("Base Color")
        if base_in and base_in.is_linked:
            src = base_in.links[0].from_socket
            nt.links.remove(base_in.links[0])
            hsv = nt.nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Saturation"].default_value = 1.25
            hsv.inputs["Value"].default_value = 1.06
            hsv.location = (principled.location.x - 220, principled.location.y + 80)
            nt.links.new(src, hsv.inputs["Color"])
            nt.links.new(hsv.outputs["Color"], base_in)

        mat.blend_method = "OPAQUE"

bpy.ops.export_scene.gltf(
    filepath=str(OUT_PATH),
    export_format="GLB",
    use_selection=False,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_yup=True,
)
print("VINYL_OK", IN_PATH.name)
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_ids", nargs="+")
    args = parser.parse_args()
    if not _BLENDER.is_file():
        print("error: Blender not found", file=sys.stderr)
        return 1

    for aid in args.asset_ids:
        glb = _MODELS / aid / f"{aid}.glb"
        if not glb.is_file():
            print(f"error: missing {glb}", file=sys.stderr)
            return 1
        out = _MODELS / aid / f"{aid}.vinyl.glb"
        worker = _MODELS / aid / "_vinyl_worker.py"
        script = (
            _WORKER.replace("__IN_PATH__", str(glb.resolve()).replace("\\", "/"))
            .replace("__OUT_PATH__", str(out.resolve()).replace("\\", "/"))
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
        if proc.returncode != 0 or not out.is_file():
            print(proc.stderr[-3000:], file=sys.stderr)
            return 1
        out.replace(glb)
        print(f"vinyl -> {glb.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
