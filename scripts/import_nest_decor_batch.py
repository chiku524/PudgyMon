#!/usr/bin/env python3
"""Import the Nest décor mega-batch (candy props + monster statues).

Per asset: copy the dense Downloads GLB in as `.pre_opt`, run the Blender
remesh+bake pipeline (closed cage, baked diffuse, toon mat), normalize the
result to its target world height, Bevy-sanitize + validate, write a README,
and register in assets/studio_registry.json.

Usage:
  python scripts/import_nest_decor_batch.py                 # everything missing
  python scripts/import_nest_decor_batch.py --only env_nest_lamp_01
  python scripts/import_nest_decor_batch.py --workers 2
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MODELS = _REPO / "assets" / "models"
_REGISTRY = _REPO / "assets" / "studio_registry.json"
_DOWNLOADS = Path.home() / "Downloads"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# (downloads filename, asset_id, target world height in meters, note)
BATCH: list[tuple[str, str, float, str]] = [
    ("cute+candy+lamp+3d+model-optimized.glb", "env_nest_lamp_01", 2.4, "candy street lamp"),
    ("cute+monster+3d+model-optimized.glb", "env_nest_monster_01", 1.1, "cute monster statue"),
    ("candy+arch+prop+3d+model-optimized.glb", "env_nest_arch_01", 3.2, "candy arch gate"),
    ("cute+monster+3d+model (1)-optimized.glb", "env_nest_monster_02", 1.1, "cute monster statue"),
    ("candy+fountain+3d+model-optimized.glb", "env_nest_fountain_01", 2.6, "candy plaza fountain"),
    ("cute+arrow+sign+3d+model-optimized.glb", "env_nest_sign_arrow_01", 1.6, "arrow signpost"),
    ("stylized+candy+arch+3d+model-optimized.glb", "env_nest_arch_02", 3.2, "candy arch gate"),
    ("candy+map+kiosk+3d+model-optimized.glb", "env_nest_kiosk_map_01", 2.2, "map kiosk"),
    ("candy+signboard+3d+model-optimized.glb", "env_nest_signboard_01", 1.8, "candy signboard"),
    ("candy+couch+3d+model-optimized.glb", "env_nest_couch_01", 1.0, "candy couch"),
    ("stylized+3d+game+prop-optimized.glb", "env_nest_deco_01", 1.2, "candy deco prop"),
    ("stylized+3d+game+prop (1)-optimized.glb", "env_nest_deco_02", 1.2, "candy deco prop"),
    ("stylized+chair+3d+model-optimized.glb", "env_nest_chair_01", 1.0, "candy chair"),
    ("heart-shaped+candy+loveseat+3d+model-optimized.glb", "env_nest_loveseat_01", 1.0, "heart loveseat"),
    ("cute+candy+cart+3d+model-optimized.glb", "env_nest_cart_candy_01", 1.8, "candy vendor cart"),
    ("candy+bench+3d+model-optimized.glb", "env_nest_bench_02", 0.9, "candy bench"),
    ("stylized+game+prop+3d+model-optimized.glb", "env_nest_deco_03", 1.2, "candy deco prop"),
    ("candy+tiered+cake+3d+model-optimized.glb", "env_nest_cake_01", 1.6, "tiered party cake"),
    ("stylized+cartoon+3d+monster-optimized.glb", "env_nest_monster_03", 1.2, "cartoon monster statue"),
    ("cute+monster+3d+model (2)-optimized.glb", "env_nest_monster_04", 1.1, "cute monster statue"),
    ("cute+monster+3d+model (4)-optimized.glb", "env_nest_monster_05", 1.1, "cute monster statue"),
    ("round+candy+table+3d+model-optimized.glb", "env_nest_table_01", 0.9, "round candy table"),
    ("cute+monster+3d+model (3)-optimized.glb", "env_nest_monster_06", 1.1, "cute monster statue"),
    ("stylized+candy+planter+3d+model-optimized.glb", "env_nest_planter_01", 1.0, "candy planter"),
    ("cute+balloon+monster+3d+model-optimized.glb", "env_nest_monster_balloon_01", 1.6, "balloon monster"),
    ("stylized+3d+monster+prop-optimized.glb", "env_nest_monster_07", 1.2, "monster statue"),
    ("stylized+candy+umbrella+3d+model-optimized.glb", "env_nest_umbrella_01", 2.4, "candy parasol"),
    ("potted+plant+3d+model-optimized.glb", "env_nest_plant_01", 1.2, "potted plant"),
    ("colorful+balloon+arch+3d+model-optimized.glb", "env_nest_arch_balloon_01", 3.4, "balloon arch"),
    ("stylized+monster+3d+model-optimized.glb", "env_nest_monster_08", 1.2, "monster statue"),
    ("cute+monster+3d+model (5)-optimized.glb", "env_nest_monster_09", 1.1, "cute monster statue"),
    ("stylized+monster+3d+model (1)-optimized.glb", "env_nest_monster_10", 1.2, "monster statue"),
    ("cute+monster+3d+model (6)-optimized.glb", "env_nest_monster_11", 1.1, "cute monster statue"),
    ("stylized+spherical+character+3d+model-optimized.glb", "env_nest_char_sphere_01", 1.0, "spherical buddy"),
    ("cute+monster+3d+model (7)-optimized.glb", "env_nest_monster_12", 1.1, "cute monster statue"),
    ("stylized+cake+prop+3d+model-optimized.glb", "env_nest_cake_02", 1.2, "cake prop"),
    ("candy+colored+prop+3d+model-optimized.glb", "env_nest_deco_04", 1.2, "candy deco prop"),
    ("cute+candy+jukebox+3d+model-optimized.glb", "env_nest_jukebox_01", 1.6, "candy jukebox"),
    ("monster+prop+3d+model-optimized.glb", "env_nest_monster_13", 1.2, "monster statue"),
    ("stylized+candy+tile+prop+3d+model-optimized.glb", "env_nest_tile_01", 0.4, "candy floor tile"),
    ("stylized+cartoon+3d+game+prop-optimized.glb", "env_nest_deco_05", 1.2, "candy deco prop"),
    ("cute+monster+3d+model (8)-optimized.glb", "env_nest_monster_14", 1.1, "cute monster statue"),
    ("pink+circular+cookie+3d+model-optimized.glb", "env_nest_cookie_01", 0.8, "giant pink cookie"),
    ("stylized+game+portal+3d+model-optimized.glb", "env_nest_portal_01", 3.0, "game portal"),
    ("stylized+monster+prop+3d+model-optimized.glb", "env_nest_monster_15", 1.2, "monster statue"),
    ("stylized+cartoon+3d+game+prop (1)-optimized.glb", "env_nest_deco_06", 1.2, "candy deco prop"),
    ("stylized+monster+3d+model (3)-optimized.glb", "env_nest_monster_16", 1.2, "monster statue"),
    ("pink+stair+block+3d+model-optimized.glb", "env_nest_stair_01", 1.0, "pink stair block"),
    ("stylized+monster+3d+model (2)-optimized.glb", "env_nest_monster_17", 1.2, "monster statue"),
    ("candy+monster+3d+model-optimized.glb", "env_nest_monster_18", 1.1, "candy monster statue"),
    ("decorative+nest+egg+3d+model-optimized.glb", "env_nest_egg_02", 1.8, "decorative nest egg"),
    ("stylized+cartoon+dumpling+3d+model-optimized.glb", "env_nest_dumpling_01", 0.9, "cartoon dumpling"),
    ("pastel+game+prop+3d+model-optimized.glb", "env_nest_deco_07", 1.2, "pastel deco prop"),
    ("star+character+3d+model-optimized.glb", "env_nest_char_star_01", 1.2, "star buddy"),
    ("cute+monster+3d+model (9)-optimized.glb", "env_nest_monster_19", 1.1, "cute monster statue"),
    ("lime+green+ring+3d+model-optimized.glb", "env_nest_ring_01", 1.4, "lime ring sculpture"),
    ("rainbow+egg+sculpture+3d+model-optimized.glb", "env_nest_egg_rainbow_01", 2.0, "rainbow egg sculpture"),
    ("pudgymon+mailbox+3d+model-optimized.glb", "env_nest_mailbox_01", 1.3, "Pudgy mailbox"),
    ("cute+round+ball+3d+model-optimized.glb", "env_nest_ball_01", 0.8, "bouncy ball"),
    ("nest+snack+cart+3d+model-optimized.glb", "env_nest_cart_snack_01", 1.9, "snack cart"),
    ("cute+creature+party+3d+model-optimized.glb", "env_nest_creature_party_01", 1.3, "party creature"),
    ("cute+monster+3d+model (10)-optimized.glb", "env_nest_monster_20", 1.1, "cute monster statue"),
    ("cartoon+car+3d+model-optimized.glb", "env_nest_car_01", 1.4, "cartoon car"),
    ("ice+cream+truck+3d+model-optimized.glb", "env_nest_truck_icecream_01", 2.6, "ice cream truck"),
    ("stylized+monster+3d+model (4)-optimized.glb", "env_nest_monster_21", 1.2, "monster statue"),
    ("nest+ticket+booth+3d+model-optimized.glb", "env_nest_booth_ticket_01", 2.6, "ticket booth"),
    ("party+trash+bin+3d+model-optimized.glb", "env_nest_trashbin_01", 1.0, "party trash bin"),
    ("pink+cartoon+hydrant+3d+model-optimized.glb", "env_nest_hydrant_01", 0.9, "pink hydrant"),
    ("stylized+info+kiosk+3d+model-optimized.glb", "env_nest_kiosk_info_01", 2.2, "info kiosk"),
    ("stylized+arcade+3d+model-optimized.glb", "env_nest_arcade_01", 1.9, "arcade cabinet"),
    ("stylized+party+monster+3d+model-optimized.glb", "env_nest_monster_22", 1.2, "party monster statue"),
    ("party+monster+3d+model-optimized.glb", "env_nest_monster_23", 1.2, "party monster statue"),
    ("nest+deco+barrel+3d+model-optimized.glb", "env_nest_barrel_01", 1.0, "deco barrel"),
    ("cute+monster+3d+model (11)-optimized.glb", "env_nest_monster_24", 1.1, "cute monster statue"),
    ("pink+piggy+bank+3d+model-optimized.glb", "env_nest_piggybank_01", 1.0, "piggy bank"),
    ("candy+treasure+chest+3d+model-optimized.glb", "env_nest_chest_01", 0.9, "treasure chest"),
    ("cute+candy+tree+3d+model-optimized.glb", "env_nest_tree_candy_01", 3.4, "candy tree"),
    ("nest+deco+crate+3d+model-optimized.glb", "env_nest_crate_01", 0.9, "deco crate"),
    ("stylized+cartoon+prop+3d+model-optimized.glb", "env_nest_deco_08", 1.2, "cartoon deco prop"),
    ("cute+monster+3d+model (12)-optimized.glb", "env_nest_monster_25", 1.1, "cute monster statue"),
    ("stylized+tree+prop+3d+model-optimized.glb", "env_nest_tree_01", 3.6, "stylized tree"),
    ("round+foliage+tree+3d+model-optimized.glb", "env_nest_tree_round_01", 3.4, "round foliage tree"),
    ("stylized+candy+tree+3d+model-optimized.glb", "env_nest_tree_candy_02", 3.2, "candy tree"),
    ("green+blob+3d+model-optimized.glb", "env_nest_blob_01", 0.8, "green blob buddy"),
    ("stylized+pond+3d+model-optimized.glb", "env_nest_pond_01", 0.5, "candy pond"),
    # Stragglers (batch 2) — left out of the first drop.
    ("blue+mushroom+creature+3d+model-optimized.glb", "env_nest_creature_mushroom_01", 1.2, "mushroom creature"),
    ("stylized+cartoon+3d+prop-optimized.glb", "env_nest_deco_09", 1.2, "cartoon deco prop"),
    ("candy+rock+cluster+3d+model-optimized.glb", "env_nest_rocks_01", 1.0, "candy rock cluster"),
    ("lily+pad+3d+model-optimized.glb", "env_nest_lilypad_01", 0.3, "lily pad"),
    ("stylized+candy+hammock+3d+model-optimized.glb", "env_nest_hammock_01", 1.4, "candy hammock"),
    ("stylized+plant+3d+model-optimized.glb", "env_nest_plant_02", 1.2, "stylized plant"),
    ("candle+nest+prop+3d+model-optimized.glb", "env_nest_candle_01", 1.1, "nest candle"),
    ("cute+round+monster+3d+model-optimized.glb", "env_nest_monster_26", 1.1, "round monster statue"),
    ("cute+swing+prop+3d+model-optimized.glb", "env_nest_swing_01", 2.2, "candy swing"),
    ("candy+post+3d+model-optimized.glb", "env_nest_post_01", 1.8, "candy post"),
    ("stylized+monster+3d+model (5)-optimized.glb", "env_nest_monster_27", 1.2, "monster statue"),
    ("stylized+candy+arch+3d+model (1)-optimized.glb", "env_nest_arch_03", 3.2, "candy arch gate"),
    ("cute+monster+3d+model (13)-optimized.glb", "env_nest_monster_28", 1.1, "cute monster statue"),
]


def _world_bbox_height(gltf: dict) -> float:
    """Y extent of the default scene, node transforms applied (TRS only)."""
    import math

    def node_matrix(node: dict):
        # Column-major helpers kept minimal: TRS composition only.
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
    """Scale scene roots so bbox height == target. Returns the factor."""
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


def import_one(bake, opt, src_name: str, asset_id: str, height: float, note: str) -> dict:
    src = _DOWNLOADS / src_name
    if not src.is_file():
        raise FileNotFoundError(src)
    folder = _MODELS / asset_id
    folder.mkdir(parents=True, exist_ok=True)
    dst = folder / f"{asset_id}.glb"
    bak = dst.with_suffix(dst.suffix + ".pre_opt")

    if not bak.is_file():
        shutil.copy2(src, bak)
    shutil.copy2(src, dst)

    bake.optimize_one(dst, from_pre_opt=False)

    factor = _normalize_height(opt, dst, height)
    fixed = opt._sanitize_bevy_accessors(dst)
    opt._validate_bevy_glb(dst)

    readme = folder / "README.txt"
    if not readme.is_file():
        readme.write_text(
            f"{asset_id}\n"
            f"Source: Downloads/{src_name} (Immersive Studio / Tripo export)\n"
            f"Pipeline: blender_bake_optimize_glb (remesh+bake) via "
            f"import_nest_decor_batch.py; height-normalized to {height} m.\n"
            f"Note: {note}\n",
            encoding="utf-8",
        )
    return {
        "id": asset_id,
        "size": dst.stat().st_size,
        "scale_factor": factor,
        "sanitized": fixed,
    }


def register(entries: list[tuple[str, float, str]]) -> int:
    data = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    known = {e["asset_id"] for e in data["assets"]}
    added = 0
    for asset_id, height, note in entries:
        if asset_id in known:
            continue
        data["assets"].append(
            {
                "asset_id": asset_id,
                "target_height": height,
                "notes": f"Nest d\u00e9cor \u2014 {note}",
                # GLBs are height-normalized at import, so spawn at 1:1.
                "uniform_scale": 1.0,
            }
        )
        added += 1
    if added:
        data["assets"].sort(key=lambda e: e["asset_id"])
        _REGISTRY.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", help="comma-separated asset_ids")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--force", action="store_true", help="rebuild even if GLB exists")
    args = parser.parse_args()

    bake = _load_module("blender_bake_optimize_glb")
    opt = _load_module("optimize_glb")

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    jobs = []
    for src_name, asset_id, height, note in BATCH:
        if only and asset_id not in only:
            continue
        dst = _MODELS / asset_id / f"{asset_id}.glb"
        if dst.is_file() and not args.force:
            print(f"skip {asset_id}: already imported")
            continue
        jobs.append((src_name, asset_id, height, note))

    missing = [j[0] for j in jobs if not (_DOWNLOADS / j[0]).is_file()]
    if missing:
        print(f"error: missing downloads: {missing}", file=sys.stderr)
        return 1

    print(f"importing {len(jobs)} Nest d\u00e9cor assets with {args.workers} workers")
    ok: list[str] = []
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(import_one, bake, opt, *job[:2], job[2], job[3]): job[1]
            for job in jobs
        }
        for fut in as_completed(futs):
            aid = futs[fut]
            try:
                stats = fut.result()
                ok.append(aid)
                print(
                    f"IMPORT_OK {aid}: {stats['size'] / 1e3:.0f} KB "
                    f"(scale x{stats['scale_factor']:.3f})",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                failed.append(aid)
                print(f"IMPORT_FAIL {aid}: {exc}", file=sys.stderr, flush=True)

    added = register([(a, h, n) for _, a, h, n in BATCH if a in set(ok) or (_MODELS / a / f"{a}.glb").is_file()])
    print(f"registry: +{added} entries")
    print(f"DONE ok={len(ok)} failed={len(failed)}")
    if failed:
        print("failed:", ", ".join(failed), file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
