#!/usr/bin/env python3
"""Import remaining Studio-prompt Tripo downloads (optimized-models batch 2).

Re-exports for Bevy (no Draco / EXT_texture_webp), bakes prompt heights, UV-simplify,
and registers into assets/studio_registry.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = Path(r"C:\Users\chiku\Downloads\optimized-models (2)")
_IMPORT = _REPO / "scripts" / "import_dense_character_glb.py"
_CATALOG = _REPO / "data" / "accessories" / "catalog.json"

# (source filename, asset_id, height_m, notes, extra_import_args)
_BATCH: list[tuple[str, str, float, str, list[str]]] = [
    # Hats
    ("candy+crown+3d+model-optimized.glb", "acc_hat_party_crown_01", 0.28, "Studio prop — party crown", []),
    ("stylized+racing+cap+3d+model-optimized.glb", "acc_hat_racer_cap_01", 0.18, "Studio prop — racer cap", []),
    ("mushroom-cap+hat+3d+model (1)-optimized.glb", "acc_hat_vibe_mushroom_01", 0.30, "Studio prop — mushroom hat", []),
    ("pink+beanie+3d+model-optimized.glb", "acc_hat_blaster_beanie_01", 0.22, "Studio prop — star beanie", []),
    ("propeller+beanie+3d+model-optimized.glb", "acc_hat_propeller_01", 0.26, "Studio prop — propeller beanie", []),
    ("daisy+flower+hat+3d+model-optimized.glb", "acc_hat_flower_01", 0.32, "Studio prop — daisy hat", []),
    ("chef+hat+3d+model-optimized.glb", "acc_hat_chef_01", 0.30, "Studio prop — chef hat", []),
    ("floppy+nightcap+3d+model-optimized.glb", "acc_hat_sleep_01", 0.28, "Studio prop — sleep cap", []),
    # Necklaces
    ("soft+shell+pendant+3d+model-optimized.glb", "acc_necklace_shell_01", 0.18, "Studio prop — shell pendant", []),
    ("round+medal+3d+model-optimized.glb", "acc_necklace_medal_01", 0.18, "Studio prop — party medal", []),
    ("rainbow+bead+bracelet+3d+model-optimized.glb", "acc_necklace_beads_01", 0.16, "Studio prop — bead bracelet", []),
    ("jingle+bell+charm+3d+model-optimized.glb", "acc_necklace_bell_01", 0.16, "Studio prop — jingle bell", []),
    # Shoes
    ("stylized+sneakers+3d+model-optimized.glb", "acc_shoes_racer_01", 0.16, "Studio prop — racer sneakers", []),
    ("stylized+loafers+3d+model-optimized.glb", "acc_shoes_party_01", 0.16, "Studio prop — party loafers", []),
    ("toy+rain+boots+3d+model-optimized.glb", "acc_shoes_boots_01", 0.20, "Studio prop — rain boots", []),
    ("plush+cloud+slippers+3d+model-optimized.glb", "acc_shoes_slippers_01", 0.12, "Studio prop — cloud slippers", []),
    # Back / face / hands
    ("cape+prop+3d+model-optimized.glb", "acc_back_cape_01", 0.55, "Studio prop — party cape", []),
    ("candy+wings+3d+model-optimized.glb", "acc_back_wings_01", 0.45, "Studio prop — candy wings", []),
    ("vibe-orb+backpack+3d+model-optimized.glb", "acc_back_pack_01", 0.40, "Studio prop — vibe backpack", []),
    ("toy+sunglasses+3d+model-optimized.glb", "acc_face_shades_01", 0.12, "Studio prop — sunglasses", []),
    ("racer+goggles+3d+model-optimized.glb", "acc_face_goggles_01", 0.12, "Studio prop — racer goggles", []),
    ("pink+party+mask+3d+model-optimized.glb", "acc_face_mask_01", 0.14, "Studio prop — party mask", []),
    ("star+mitten+3d+model-optimized.glb", "acc_hands_mittens_01", 0.18, "Studio prop — star mittens", []),
    ("racing+gloves+3d+model-optimized.glb", "acc_hands_gloves_01", 0.18, "Studio prop — racing gloves", []),
    # Nest
    ("stylized+egg+prop+3d+model-optimized.glb", "env_nest_egg_01", 2.0, "Studio prop — Nest egg", []),
    ("cute+candy+bench+3d+model-optimized.glb", "env_nest_bench_01", 0.6, "Studio prop — Nest bench", []),
    ("cute+mushroom+3d+model-optimized.glb", "prop_vibe_mushroom_01", 1.8, "Studio prop — Nest mushroom", []),
    # Mode pads (flat discs — bake ~2.5 m wide via height from aspect)
    (
        "candy+disc+3d+model-optimized.glb",
        "env_pad_race_01",
        0.35,
        "Studio prop — Race mode pad",
        ["--width", "2.5"],
    ),
    (
        "decorative+floor+decal+3d+model-optimized.glb",
        "env_pad_vibe_01",
        0.52,
        "Studio prop — Vibe mode pad",
        ["--width", "2.5"],
    ),
    (
        "colorful+game+prop+3d+model-optimized.glb",
        "env_pad_shooter_01",
        1.25,
        "Studio prop — Shooter mode pad (best-effort Tripo match)",
        ["--width", "2.5"],
    ),
    (
        "stylized+game+prop+3d+model-optimized.glb",
        "env_pad_party_01",
        1.04,
        "Studio prop — Party mode pad (best-effort Tripo match)",
        ["--width", "2.5"],
    ),
    # Race stage
    ("candy+traffic+cone+3d+model-optimized.glb", "prop_race_cone_01", 0.7, "Studio prop — race cone", []),
    ("party+banner+prop+3d+model-optimized.glb", "prop_race_banner_01", 1.5, "Studio prop — race banner", []),
    ("stylized+toy+ramp+3d+model-optimized.glb", "env_race_ramp_01", 1.2, "Studio prop — race ramp", []),
    ("cute+monster+prop+3d+model-optimized.glb", "prop_race_checkpoint_01", 2.0, "Studio prop — race checkpoint (best-effort)", []),
    # Vibe stage
    ("candy+orb+3d+model-optimized.glb", "prop_vibe_orb_01", 0.5, "Studio prop — vibe orb", []),
    ("stylized+candy+flower+3d+model-optimized.glb", "prop_vibe_flower_01", 1.0, "Studio prop — vibe flower", []),
    ("crystal+cluster+3d+model-optimized.glb", "prop_vibe_crystal_01", 0.8, "Studio prop — vibe crystal", []),
    # Shooter stage
    ("star+shaped+candy+3d+model-optimized.glb", "prop_target_star_01", 1.0, "Studio prop — star target", []),
    ("cute+monster+toy+3d+model-optimized.glb", "prop_cover_block_01", 1.2, "Studio prop — cover block (best-effort)", []),
    ("cute+candy+monster+3d+model-optimized.glb", "prop_blaster_toy_01", 0.4, "Studio prop — toy blaster (best-effort)", []),
    # Species skins (remaining cute-monster figures)
    ("cute+monster+3d+model-optimized.glb", "char_pudgy_forest_01", 1.2, "Studio species — forest Pudgy", []),
]


def _clear_character_look_flags(asset_ids: set[str]) -> None:
    if not _CATALOG.is_file():
        return
    data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    changed = 0
    for slot in data.get("slots", []):
        for item in slot.get("items", []):
            if item.get("id") in asset_ids and item.get("character_look"):
                item.pop("character_look", None)
                # Drop the "Crew" suffix from labels when switching to real props.
                label = item.get("label", "")
                if label.endswith(" Crew"):
                    item["label"] = label[: -len(" Crew")]
                changed += 1
    if changed:
        _CATALOG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"catalog: cleared character_look on {changed} items")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", help="Comma-separated asset_ids to import")
    parser.add_argument("--src", type=Path, default=_SRC)
    parser.add_argument("--simplify-ratio", type=float, default=0.18)
    parser.add_argument("--max-tex", type=int, default=768)
    args = parser.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if not args.src.is_dir():
        print(f"error: missing {args.src}", file=sys.stderr)
        return 1

    failed = 0
    imported: list[str] = []
    for src_name, asset_id, height, notes, extra in _BATCH:
        if only and asset_id not in only:
            continue
        src = args.src / src_name
        if not src.is_file():
            print(f"SKIP missing {src_name}", file=sys.stderr)
            failed += 1
            continue
        cmd = [
            sys.executable,
            str(_IMPORT),
            "--src",
            str(src),
            "--asset-id",
            asset_id,
            "--height",
            str(height),
            "--max-tex",
            str(args.max_tex),
            "--simplify-ratio",
            str(args.simplify_ratio),
            "--simplify-error",
            "0.06",
            "--notes",
            notes,
            *extra,
        ]
        print("+", " ".join(cmd), flush=True)
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print(f"FAIL {asset_id}", file=sys.stderr)
            failed += 1
        else:
            print(f"OK {asset_id}", flush=True)
            imported.append(asset_id)

    _clear_character_look_flags(set(imported))
    print(f"done: {len(imported)} ok, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
