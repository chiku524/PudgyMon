#!/usr/bin/env python3
"""Re-bake every registered Studio GLB from its dense .pre_opt backup.

After the bake quality pass (sharper atlases, tighter cage, higher JPEG),
restores each asset from `.glb.pre_opt`, runs the appropriate Blender bake
pipeline, then re-applies registry `target_height` normalization so in-game
scale stays correct (all studio assets ship at uniform_scale=1.0).

Usage:
  python scripts/rebake_all_from_pre_opt.py
  python scripts/rebake_all_from_pre_opt.py --only env_nest_lamp_01,char_pudgy_base_01
  python scripts/rebake_all_from_pre_opt.py --workers 3 --skip-chars
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_REGISTRY = _REPO / "assets" / "studio_registry.json"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _world_bbox_height(gltf: dict) -> float:
    def node_matrix(node: dict):
        t = node.get("translation", [0.0, 0.0, 0.0])
        r = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        s = node.get("scale", [1.0, 1.0, 1.0])
        x, y, z, w = r
        rot = [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
        return t, rot, s

    def apply(node: dict, point):
        t, rot, s = node_matrix(node)
        p = [point[i] * s[i] for i in range(3)]
        p = [sum(rot[i][j] * p[j] for j in range(3)) for i in range(3)]
        return [p[i] + t[i] for i in range(3)]

    nodes = gltf.get("nodes", [])
    accessors = gltf.get("accessors", [])
    meshes = gltf.get("meshes", [])
    y_min, y_max = math.inf, -math.inf

    def visit(index: int, chain: list[dict]):
        nonlocal y_min, y_max
        node = nodes[index]
        chain = chain + [node]
        if "mesh" in node:
            for prim in meshes[node["mesh"]].get("primitives", []):
                pos = prim.get("attributes", {}).get("POSITION")
                if pos is None:
                    continue
                acc = accessors[pos]
                lo, hi = acc.get("min"), acc.get("max")
                if not lo or not hi:
                    continue
                for cx in (lo[0], hi[0]):
                    for cy in (lo[1], hi[1]):
                        for cz in (lo[2], hi[2]):
                            p = [cx, cy, cz]
                            for n in reversed(chain):
                                p = apply(n, p)
                            y_min = min(y_min, p[1])
                            y_max = max(y_max, p[1])
        for child in node.get("children", []):
            visit(child, chain)

    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    for root in scene.get("nodes", []):
        visit(root, [])
    if y_max <= y_min:
        return 0.0
    return y_max - y_min


def _normalize_height(opt, glb: Path, target: float) -> float:
    gltf, bin_chunk = opt._load_glb(glb)
    height = _world_bbox_height(gltf)
    if height <= 1e-5:
        print(f"warn: {glb.name} has no measurable height; leaving scale")
        return 1.0
    factor = target / height
    if abs(factor - 1.0) < 0.02:
        return 1.0
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)]
    for root in scene.get("nodes", []):
        node = gltf["nodes"][root]
        s = node.get("scale", [1.0, 1.0, 1.0])
        node["scale"] = [s[0] * factor, s[1] * factor, s[2] * factor]
    opt._write_glb(glb, gltf, bin_chunk)
    return factor


def _is_char(asset_id: str) -> bool:
    return asset_id.startswith(("char_", "oceanic_", "npc_"))


def rebake_one(bake, char_bake, opt, asset_id: str, height: float) -> dict:
    glb = _MODELS / asset_id / f"{asset_id}.glb"
    bak = glb.with_suffix(glb.suffix + ".pre_opt")
    if not bak.is_file():
        raise FileNotFoundError(f"missing pre_opt for {asset_id}")

    if _is_char(asset_id):
        char_bake.optimize_one(asset_id, from_pre_opt=True)
        # Resample clips without restoring the dense backup over the bake.
        # Resample clips only — keep the fresh 1024 atlas (game preset
        # defaults to max_tex=512 which would re-blur eyes).
        opt.optimize_file(
            glb,
            preset="game",
            backup=False,
            force=False,
            max_tex=1024,
            jpeg_quality=92,
        )
    else:
        bake.optimize_one(glb, from_pre_opt=True)

    factor = _normalize_height(opt, glb, height)
    opt._sanitize_bevy_accessors(glb)
    opt._validate_bevy_glb(glb)
    return {
        "id": asset_id,
        "size": glb.stat().st_size,
        "scale_factor": factor,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--skip-chars", action="store_true")
    parser.add_argument("--chars-only", action="store_true")
    args = parser.parse_args()

    bake = _load("blender_bake_optimize_glb")
    char_bake = _load("blender_char_optimize_glb")
    opt = _load("optimize_glb")

    registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    jobs: list[tuple[str, float]] = []
    for entry in registry["assets"]:
        aid = entry["asset_id"]
        if aid.startswith("_"):
            continue
        if only and aid not in only:
            continue
        if args.skip_chars and _is_char(aid):
            continue
        if args.chars_only and not _is_char(aid):
            continue
        glb = _MODELS / aid / f"{aid}.glb"
        bak = glb.with_suffix(glb.suffix + ".pre_opt")
        if not bak.is_file():
            print(f"skip {aid}: no .pre_opt backup")
            continue
        jobs.append((aid, float(entry.get("target_height", 1.0))))

    print(f"rebaking {len(jobs)} assets with {args.workers} workers")
    ok: list[str] = []
    failed: list[str] = []

    # Characters stay serial — Blender + animation resample is heavy and
    # shares temp dirs poorly under high concurrency.
    statics = [(a, h) for a, h in jobs if not _is_char(a)]
    chars = [(a, h) for a, h in jobs if _is_char(a)]

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {
            pool.submit(rebake_one, bake, char_bake, opt, aid, h): aid
            for aid, h in statics
        }
        for fut in as_completed(futs):
            aid = futs[fut]
            try:
                stats = fut.result()
                ok.append(aid)
                print(
                    f"REBAKE_OK {aid}: {stats['size'] / 1e3:.0f} KB "
                    f"(scale x{stats['scale_factor']:.3f})",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                failed.append(aid)
                print(f"REBAKE_FAIL {aid}: {exc}", file=sys.stderr, flush=True)

    for aid, h in chars:
        try:
            stats = rebake_one(bake, char_bake, opt, aid, h)
            ok.append(aid)
            print(
                f"REBAKE_OK {aid}: {stats['size'] / 1e3:.0f} KB "
                f"(scale x{stats['scale_factor']:.3f})",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            failed.append(aid)
            print(f"REBAKE_FAIL {aid}: {exc}", file=sys.stderr, flush=True)

    print(f"DONE ok={len(ok)} failed={len(failed)}")
    if failed:
        print("failed:", ", ".join(failed), file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
