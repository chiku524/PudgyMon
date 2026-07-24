#!/usr/bin/env python3
"""Align assets/models with docs/STUDIO_PROMPTS.md and ensure 5 selectable crew.

1. Map legacy pink/water into Studio ids (base / oceanic)
2. Stand in lava/sky from base until dedicated Studio downloads exist
3. Delete model folders not listed in STUDIO_PROMPTS.md
4. Rewrite roster.json + prune studio_registry.json

Usage:
  python scripts/sync_studio_prompt_assets.py
  python scripts/sync_studio_prompt_assets.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PROMPTS = _REPO / "docs" / "STUDIO_PROMPTS.md"
_MODELS = _REPO / "assets" / "models"
_ROSTER = _REPO / "data" / "characters" / "roster.json"
_REGISTRY = _REPO / "assets" / "studio_registry.json"
_DEFAULTS = _REPO / "data" / "player_defaults.json"

_KEEP_ALWAYS = {"_TEMPLATE"}

_CREW = [
    ("char_pudgy_base_01", "Base Pudgy", "Shared coral-peach party base"),
    ("oceanic_pudgymon_01", "Ocean Pudgy", "Ocean species — fins and teal candy palette"),
    ("char_pudgy_forest_01", "Forest Pudgy", "Forest species — leaf tufts and lime palette"),
    ("char_pudgy_lava_01", "Lava Pudgy", "Lava species — ember freckles and charcoal crust"),
    ("char_pudgy_sky_01", "Sky Pudgy", "Sky species — puffball cheeks and sky-blue coat"),
]


def prompt_asset_ids(text: str) -> set[str]:
    ids = set(re.findall(r"`([a-z][a-z0-9_]*(?:_\d+)?)`", text))
    out = set()
    for i in ids:
        if i.startswith("Socket"):
            continue
        if i in {"uniform_scale", "target_height", "asset_id", "PlayerVisualSpec"}:
            continue
        if "_" not in i:
            continue
        out.add(i)
    return out


def ensure_dir_copy(src_dir: Path, dst_id: str, *, dry: bool) -> Path:
    dst = _MODELS / dst_id
    src_glb = src_dir / f"{src_dir.name}.glb"
    # Prefer denser pre_opt backup when present.
    src_pre = src_dir / f"{src_dir.name}.glb.pre_opt"
    pick = src_pre if src_pre.is_file() else src_glb
    if not pick.is_file():
        raise FileNotFoundError(pick)
    dst_glb = dst / f"{dst_id}.glb"
    if dry:
        print(f"DRY ensure {dst_id} from {pick.relative_to(_REPO)}")
        return dst
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pick, dst_glb)
    readme = dst / "README.txt"
    readme.write_text(
        f"{dst_id}\nSynced from Studio prompt pack / legacy mesh {src_dir.name}.\n",
        encoding="utf-8",
    )
    print(f"ensure {dst_id} <- {pick.relative_to(_REPO)} ({pick.stat().st_size / 1e6:.2f} MB)")
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    text = _PROMPTS.read_text(encoding="utf-8")
    allow = prompt_asset_ids(text) | _KEEP_ALWAYS
    print(f"allowlist {len(allow)} ids from STUDIO_PROMPTS.md")

    pink = _MODELS / "char_pudgy_pink_01"
    water = _MODELS / "char_pudgy_water_01"
    if not pink.is_dir() and not (_MODELS / "char_pudgy_base_01").is_dir():
        print("error: missing pink/base source mesh", file=sys.stderr)
        return 1
    if not water.is_dir() and not (_MODELS / "oceanic_pudgymon_01").is_dir():
        print("error: missing water/oceanic source mesh", file=sys.stderr)
        return 1

    # 1) Materialize base + ocean from known sources; species bodies are imported separately.
    base_src = pink if pink.is_dir() else _MODELS / "char_pudgy_base_01"
    ocean_src = water if water.is_dir() else _MODELS / "oceanic_pudgymon_01"
    ensure_dir_copy(base_src, "char_pudgy_base_01", dry=dry)
    ensure_dir_copy(ocean_src, "oceanic_pudgymon_01", dry=dry)
    for crew_id in ("char_pudgy_forest_01", "char_pudgy_lava_01", "char_pudgy_sky_01"):
        if not (_MODELS / crew_id).is_dir() and not dry:
            print(f"error: missing {crew_id} (import via auto_rig_glb.py)", file=sys.stderr)
            return 1

    # 2) Delete folders not in the prompt allowlist.
    removed = []
    for child in sorted(_MODELS.iterdir()):
        if not child.is_dir():
            continue
        if child.name in allow:
            continue
        removed.append(child.name)
        if dry:
            print(f"DRY remove {child.name}")
        else:
            shutil.rmtree(child)
            print(f"remove {child.name}")

    # 3) Roster = exactly the five Studio Priority-0 characters.
    roster = {
        "schema_version": 1,
        "characters": [
            {"id": cid, "label": label, "blurb": blurb} for cid, label, blurb in _CREW
        ],
    }
    if dry:
        print("DRY write roster.json with", [c["id"] for c in roster["characters"]])
    else:
        _ROSTER.write_text(json.dumps(roster, indent=2) + "\n", encoding="utf-8")
        print("wrote", _ROSTER.relative_to(_REPO))

    # 4) Defaults → base
    if _DEFAULTS.is_file() and not dry:
        defaults = json.loads(_DEFAULTS.read_text(encoding="utf-8"))
        defaults["crew_model_id"] = "char_pudgy_base_01"
        _DEFAULTS.write_text(json.dumps(defaults, indent=2) + "\n", encoding="utf-8")
        print("defaults crew_model_id -> char_pudgy_base_01")

    # 5) Registry: keep only allowlisted entries + ensure crew rows exist.
    registry = {"import_root": "res://assets/models", "assets": []}
    if _REGISTRY.is_file():
        registry = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    by_id = {
        a["asset_id"]: a
        for a in registry.get("assets", [])
        if isinstance(a, dict) and a.get("asset_id")
    }
    kept = {k: v for k, v in by_id.items() if k in allow}
    for cid, label, blurb in _CREW:
        kept[cid] = {
            "asset_id": cid,
            "target_height": 1.2,
            "uniform_scale": 1.0,
            "notes": blurb,
        }
    # Ensure accessory / nest / prop rows for folders that still exist.
    for folder in sorted(_MODELS.iterdir()):
        if not folder.is_dir() or folder.name not in allow or folder.name in kept:
            continue
        kept[folder.name] = {
            "asset_id": folder.name,
            "target_height": 1.0,
            "uniform_scale": 1.0,
            "notes": "Studio prompt pack asset",
        }
    registry["assets"] = sorted(kept.values(), key=lambda x: x["asset_id"])
    if dry:
        print(f"DRY registry assets={len(registry['assets'])}")
    else:
        _REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        print(f"wrote registry ({len(registry['assets'])} assets)")

    print(f"removed_folders={len(removed)}")
    print("crew=", [c[0] for c in _CREW])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
