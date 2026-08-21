#!/usr/bin/env python3
"""Register a single Studio asset_id in assets/studio_registry.json.

Usage:
  python scripts/register_studio_asset.py my_prop_01 --height 1.2
  python scripts/register_studio_asset.py safety_mat_01 --width 2.0
  python scripts/register_studio_asset.py my_prop_01 --height 1.2 --scale 0.85 --notes "floor pivot"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY_PATH = _REPO_ROOT / "assets" / "studio_registry.json"
_MODELS_DIR = _REPO_ROOT / "assets" / "models"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_id", help="Studio asset id (folder + glb basename)")
    parser.add_argument("--height", type=float, default=1.0, help="target_height meters")
    parser.add_argument("--width", type=float, default=None, help="target_width for floor pads")
    parser.add_argument("--scale", type=float, default=None, help="uniform_scale override")
    parser.add_argument("--notes", type=str, default=None, help="artist notes")
    parser.add_argument("--update", action="store_true", help="overwrite existing entry")
    args = parser.parse_args()

    aid = args.asset_id.strip()
    if not aid:
        print("error: empty asset_id", file=sys.stderr)
        return 1

    registry = {"import_root": "res://assets/models", "assets": []}
    if _REGISTRY_PATH.is_file():
        registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))

    by_id = {
        a["asset_id"]: a
        for a in registry.get("assets", [])
        if isinstance(a, dict) and a.get("asset_id")
    }

    if aid in by_id and not args.update:
        print(f"error: `{aid}` already registered (pass --update to overwrite)", file=sys.stderr)
        return 1

    entry: dict = {"asset_id": aid, "target_height": float(args.height)}
    if args.width is not None:
        entry["target_width"] = float(args.width)
    if args.scale is not None:
        entry["uniform_scale"] = float(args.scale)
    if args.notes:
        entry["notes"] = args.notes

    by_id[aid] = entry
    registry["assets"] = sorted(by_id.values(), key=lambda x: x.get("asset_id", ""))
    _REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    glb = _MODELS_DIR / aid / f"{aid}.glb"
    print(f"Registered `{aid}` in {_REGISTRY_PATH.relative_to(_REPO_ROOT)}")
    if glb.is_file():
        print(f"GLB present: {glb.relative_to(_REPO_ROOT)}")
    else:
        print(f"GLB missing (expected {glb.relative_to(_REPO_ROOT)}) — import a pack or copy the file")
    print("Next: add a marker with this asset_id to data/rooms/<room>.json")
    print("      then Play in Unity Hub → unity/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
