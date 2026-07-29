#!/usr/bin/env python3
"""Batch-import Tripo accessory/NPC downloads into assets/models.

Source files are full dressed figures (Tripo ignored "accessory only"), so they
are imported as ~1.2 m Bevy-safe GLBs for Nest NPCs + character-look equip.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = Path(r"C:\Users\chiku\Downloads\optimized-models (1)")
_IMPORT = _REPO / "scripts" / "import_dense_character_glb.py"

# (source filename, asset_id, notes)
_BATCH: list[tuple[str, str, str]] = [
    (
        "candy+party+crown+3d+model-optimized.glb",
        "acc_hat_party_crown_01",
        "Full-figure Tripo look (party crown); Nest NPC + character-look equip.",
    ),
    (
        "cute+chef+hat+3d+model-optimized.glb",
        "acc_hat_chef_01",
        "Full-figure Tripo look (chef hat); Nest NPC + character-look equip.",
    ),
    (
        "daisy+flower+3d+model-optimized.glb",
        "acc_hat_flower_01",
        "Full-figure Tripo look (daisy hat); Nest NPC + character-look equip.",
    ),
    (
        "mushroom-cap+hat+3d+model-optimized.glb",
        "acc_hat_vibe_mushroom_01",
        "Full-figure Tripo look (mushroom cap); Nest NPC + character-look equip.",
    ),
    (
        "stylized+propeller+hat+3d+model-optimized.glb",
        "acc_hat_propeller_01",
        "Full-figure Tripo look (propeller hat); Nest NPC + character-look equip.",
    ),
    (
        "cute+party+hat+3d+model-optimized.glb",
        "acc_hat_racer_cap_01",
        "Full-figure Tripo look (party/racer cap); Nest NPC + character-look equip.",
    ),
    (
        "cute+necklace+pendant+3d+model-optimized.glb",
        "acc_necklace_shell_01",
        "Full-figure Tripo look (pendant); Nest NPC + character-look equip.",
    ),
    (
        "stylized+bead+necklace+3d+model-optimized.glb",
        "acc_necklace_beads_01",
        "Full-figure Tripo look (bead necklace); Nest NPC + character-look equip.",
    ),
    (
        "cute+3d+game+accessory-optimized.glb",
        "acc_necklace_medal_01",
        "Full-figure Tripo look (generic accessory / medal slot); Nest NPC + character-look equip.",
    ),
    (
        "pink+pudgy+monster+3d+model-optimized.glb",
        "npc_nest_pink_01",
        "Nest ambient NPC — pink pudgy figure.",
    ),
    (
        "pudgymon+character+3d+model-optimized.glb",
        "npc_nest_crew_a_01",
        "Nest ambient NPC — crew figure A.",
    ),
    (
        "pudgymon+character+3d+model (1)-optimized.glb",
        "npc_nest_crew_b_01",
        "Nest ambient NPC — crew figure B.",
    ),
    (
        "stylized+3d+character-optimized.glb",
        "npc_nest_stylized_a_01",
        "Nest ambient NPC — stylized figure.",
    ),
    (
        "stylized+monster+3d+model-optimized.glb",
        "npc_nest_monster_01",
        "Nest ambient NPC — stylized monster.",
    ),
]


def main() -> int:
    if not _SRC.is_dir():
        print(f"error: missing {_SRC}", file=sys.stderr)
        return 1

    failed = 0
    for src_name, asset_id, notes in _BATCH:
        src = _SRC / src_name
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
            "1.2",
            "--max-tex",
            "1024",
            "--simplify-ratio",
            "0.25",
            "--simplify-error",
            "0.006",
            "--notes",
            notes,
        ]
        print("+", " ".join(cmd))
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print(f"FAIL {asset_id}", file=sys.stderr)
            failed += 1
        else:
            print(f"OK {asset_id}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
