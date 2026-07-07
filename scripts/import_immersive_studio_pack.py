#!/usr/bin/env python3
"""
Import an Immersive Studio pack (zip or unpacked folder) into ShipHappens.

Copies GLB meshes (and optional sidecar textures), merges asset entries into
assets/studio_registry.json, and optionally copies ATTRIBUTION files.

Usage:
  python scripts/import_immersive_studio_pack.py path/to/pack.zip
  python scripts/import_immersive_studio_pack.py path/to/pack_folder --update
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _REPO_ROOT / "assets" / "models"
_REGISTRY_PATH = _REPO_ROOT / "assets" / "studio_registry.json"
_ATTRIBUTION_DIR = _REPO_ROOT / "assets"


def _load_registry() -> dict:
    if _REGISTRY_PATH.is_file():
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"import_root": "res://assets/models", "assets": []}


def _save_registry(data: dict) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_manifest(pack_root: Path) -> dict | None:
    manifest_path = pack_root / "manifest.json"
    if not manifest_path.is_file():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _import_root_for_asset(asset: dict) -> str:
    godot = asset.get("godot") or {}
    sub = str(godot.get("import_subfolder") or "assets/models").strip().strip("/")
    return f"res://{sub}"


def _registry_entry_from_asset(asset: dict) -> dict:
    entry: dict = {"asset_id": asset["asset_id"]}
    height = asset.get("target_height_m")
    if isinstance(height, (int, float)) and height > 0:
        entry["target_height"] = float(height)
    return entry


def _merge_registry(
    registry: dict,
    manifest_assets: list[dict],
    *,
    update: bool,
) -> tuple[int, int, int]:
    by_id = {a["asset_id"]: a for a in registry.get("assets", []) if isinstance(a, dict) and a.get("asset_id")}
    added = updated = skipped = 0

    for asset in manifest_assets:
        aid = asset.get("asset_id")
        if not isinstance(aid, str) or not aid.strip():
            continue
        aid = aid.strip()
        new_entry = _registry_entry_from_asset(asset)
        if aid in by_id:
            if update:
                by_id[aid].update(new_entry)
                updated += 1
            else:
                skipped += 1
        else:
            by_id[aid] = new_entry
            added += 1

    registry["assets"] = sorted(by_id.values(), key=lambda x: x.get("asset_id", ""))
    return added, updated, skipped


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.is_dir():
        return
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _import_pack(pack_root: Path, *, update: bool, copy_textures: bool) -> int:
    manifest = _read_manifest(pack_root)
    if manifest is None:
        print("error: manifest.json not found in pack", file=sys.stderr)
        return 1

    assets = manifest.get("assets") or []
    if not assets:
        print("error: manifest has no assets", file=sys.stderr)
        return 1

    models_root = pack_root / "Models"
    if not models_root.is_dir():
        print("error: Models/ folder not found in pack", file=sys.stderr)
        return 1

    copied_models: list[str] = []
    for asset in assets:
        aid = asset.get("asset_id")
        if not isinstance(aid, str) or not aid.strip():
            continue
        aid = aid.strip()
        src = models_root / aid
        if not src.is_dir():
            print(f"warn: Models/{aid}/ missing — skipped mesh copy")
            continue
        dest = _MODELS_DIR / aid
        _copy_tree(src, dest)
        copied_models.append(aid)

        if copy_textures:
            tex_src = pack_root / "Textures" / aid
            if tex_src.is_dir():
                _copy_tree(tex_src, dest)

    for attr in pack_root.glob("ATTRIBUTION*.md"):
        shutil.copy2(attr, _ATTRIBUTION_DIR / attr.name)
    for attr in (_REPO_ROOT / "assets").glob("ATTRIBUTION_*.md"):
        pass  # keep existing attribution files in assets/

    root_attr = pack_root / "ATTRIBUTION.md"
    if root_attr.is_file():
        shutil.copy2(root_attr, _ATTRIBUTION_DIR / f"ATTRIBUTION_{manifest.get('job_id', 'pack')}.md")

    registry = _load_registry()
    if manifest_assets := assets:
        first_root = _import_root_for_asset(manifest_assets[0])
        if first_root:
            registry["import_root"] = first_root
    added, upd, skipped = _merge_registry(registry, assets, update=update)
    _save_registry(registry)

    print(f"Imported {len(copied_models)} model folder(s) into {_MODELS_DIR.relative_to(_REPO_ROOT)}")
    for aid in copied_models:
        print(f"  - {aid}")
    print(f"Registry: +{added} new, ~{upd} updated, {skipped} unchanged (use --update to refresh heights)")
    print(f"Updated {_REGISTRY_PATH.relative_to(_REPO_ROOT)}")
    print("Next: open Godot to reimport GLBs, then run the game.")
    return 0


def _resolve_pack_root(path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if path.is_dir():
        return path, None
    if path.suffix.lower() != ".zip" or not path.is_file():
        raise FileNotFoundError(path)

    tmp = tempfile.TemporaryDirectory(prefix="studio-pack-")
    with zipfile.ZipFile(path) as zf:
        zf.extractall(tmp.name)
    root = Path(tmp.name)
    # Pack zip may contain a single top-level folder.
    children = [p for p in root.iterdir() if p.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir() and (children[0] / "manifest.json").is_file():
        return children[0], tmp
    return root, tmp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path, help="pack.zip or unpacked pack folder")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update target_height for assets already in studio_registry.json",
    )
    parser.add_argument(
        "--no-textures",
        action="store_true",
        help="Skip copying Textures/ sidecars (Tripo PBR is usually embedded in the GLB)",
    )
    args = parser.parse_args()

    try:
        pack_root, tmp = _resolve_pack_root(args.pack.resolve())
    except FileNotFoundError:
        print(f"error: pack not found: {args.pack}", file=sys.stderr)
        return 1

    try:
        return _import_pack(pack_root, update=args.update, copy_textures=not args.no_textures)
    finally:
        if tmp is not None:
            tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
