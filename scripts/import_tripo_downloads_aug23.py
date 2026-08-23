#!/usr/bin/env python3
"""Import the Aug 23 Tripo Downloads batch with visually assigned asset_ids."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_IMPORT = _REPO / "scripts" / "import_dense_character_glb.py"
_DL = Path(r"C:\Users\chiku\Downloads")

# (src filename, asset_id, height, notes)
_BATCH: list[tuple[str, str, float, str]] = [
    # Nest / stage props
    ("cute+monster+prop+3d+model.glb", "env_nest_booth_photo_01", 2.2,
     "Hollow log photo booth with curtains and a tiny vendor."),
    ("trophy+cup+3d+model.glb", "prop_trophy_gold_01", 0.9,
     "Tan candy trophy cup with blank plaque."),
    ("stylized+egg+trophy+3d+model.glb", "prop_trophy_egg_01", 0.9,
     "Chocolate egg trophy in a candy cup."),
    ("coin+prop+3d+model.glb", "env_nest_logo_01", 0.7,
     "PudgyMon Party Joy logo on a cookie disc (labeled coin)."),
    ("stylized+monster+3d+model (9).glb", "env_nest_dessert_cup_01", 0.6,
     "Cream dumpling peeking from a garnished dessert bowl."),
    ("shield+prop+3d+model.glb", "prop_foam_shield_01", 1.0,
     "Tan toy heater shield."),
    ("round+cake+3d+model.glb", "env_nest_layer_cake_01", 0.5,
     "Short layered frosting cake with a loose cherry."),
    ("donut+torus+3d+model.glb", "env_nest_donut_01", 0.4,
     "Braided cream donut / torus deco."),
    ("stylized+game+prop+3d+model (3).glb", "env_nest_booth_claim_01", 2.0,
     "Blank-sign stall with a smiling vendor."),
    ("stylized+3d+game+prop (2).glb", "env_pad_create_01", 0.15,
     "Wide party disk / Create Map pad."),
    ("candy+arch+3d+model.glb", "env_nest_hedge_arch_01", 2.5,
     "Terracotta candy/moss arch."),
    ("colorful+arch+3d+model.glb", "env_nest_arch_vibe_01", 3.0,
     "Colorful candy-blob arch."),
    ("stylized+arch+prop+3d+model.glb", "env_nest_arch_race_01", 3.0,
     "Gingerbread star-rim arch."),
    ("stylized+cartoon+3d+model (1).glb", "env_nest_arch_shooter_01", 3.0,
     "Rounded arch framing a pudgy (labeled cartoon model)."),
    ("stylized+monster+3d+model (7).glb", "env_nest_portal_race_01", 2.8,
     "Brown bolted gate with an orange pudgy in the opening."),
    ("stylized+party+disk+3d+model.glb", "env_pad_claim_01", 0.15,
     "Shallow party basin / claim disk with baked figures."),
    ("cartoon+creature+3d+model.glb", "prop_target_circle_01", 1.0,
     "Round gold-rim emblem shield with a mascot face."),
    ("stylized+candy+cube+3d+model.glb", "prop_cover_block_round_01", 1.2,
     "Rounded candy cube on a pad — shooter cover."),
    ("dumpling+mascot+3d+model.glb", "env_nest_statue_pudgy_01", 2.2,
     "Cream dumpling mascot on a pink pedestal."),
    ("stylized+monster+slide+3d+model.glb", "env_nest_slide_01", 2.0,
     "Monster-head playground slide."),
    ("colorful+inflatable+castle+3d+model.glb", "env_nest_bounce_castle_01", 2.5,
     "Inflatable bounce-castle frame."),
    ("soft+nest+seesaw+3d+model.glb", "env_nest_seesaw_01", 1.0,
     "Low wide Nest seesaw / ring board."),
    ("three-tier+candy+podium+3d+model (1).glb", "env_nest_podium_01", 1.2,
     "Three-tier chocolate candy podium."),
    ("cute+dessert+stall+3d+model (1).glb", "env_nest_booth_shop_01", 2.4,
     "Pink-canopy dessert stall."),
    ("pink+speaker+stack+3d+model (1).glb", "env_nest_speaker_01", 1.6,
     "Stacked coral-pink toy speakers."),
    ("disco+ball+3d+model (1).glb", "env_nest_disco_01", 1.8,
     "Grid disco ball with candy nubs."),
    ("confetti+cannon+3d+model (1).glb", "env_nest_confetti_cannon_01", 1.4,
     "Orb cannon on a stubby stand."),
    ("stylized+cartoon+game+prop (1).glb", "env_pad_wardrobe_01", 0.15,
     "Spotted party disk / wardrobe pad."),
    ("stylized+game+prop+3d+model (1).glb", "env_nest_booth_dj_01", 1.8,
     "Toy boombox / DJ deck."),
    # Extra crew (unused species / rare IDs)
    ("cute+3d+game+prop.glb", "char_pudgy_sky_sunset_01", 1.2,
     "Star-belt pudgy with cloud collar."),
    ("stylized+monster+3d+model (10).glb", "char_pudgy_honey_rare_01", 1.2,
     "Cream-belly charcoal pudgy on a cookie pad."),
    ("cute+heart+monster+3d+model.glb", "char_pudgy_berry_rare_01", 1.2,
     "Heart-headed cream pudgy."),
    ("stylized+cartoon+monster+3d+model (2).glb", "char_pudgy_forest_autumn_01", 1.2,
     "Floral-shoulder pudgy with a pale helm."),
    ("3d+cartoon+monster+model.glb", "char_pudgy_ember_rare_01", 1.2,
     "Brown horned grinning pudgy."),
    ("stylized+cartoon+monster+3d+model (1).glb", "char_pudgy_coral_rare_01", 1.2,
     "Tan pudgy with coral-pink hood."),
    ("stylized+monster+3d+model (8).glb", "char_pudgy_ocean_winter_01", 1.2,
     "Brown pudgy holding a star flag."),
    ("cute+monster+3d+model (17).glb", "char_pudgy_candy_rare_01", 1.2,
     "Tan pudgy with a SUN flag."),
    ("stylized+cartoon+monster+3d+model.glb", "char_pudgy_night_rare_01", 1.2,
     "Gray pudgy with a tiny gold crown."),
    ("cute+monster+3d+model (16).glb", "char_pudgy_sprout_rare_01", 1.2,
     "Candy-decorated cream pudgy."),
    ("cute+monster+3d+model (15).glb", "char_pudgy_bubble_rare_01", 1.2,
     "White pudgy with heart strap and star flag."),
    ("cute+cartoon+backpack+3d+model.glb", "char_pudgy_cloud_rare_01", 1.2,
     "Hooded blue-red pudgy (labeled backpack)."),
    ("cute+monster+3d+model (14).glb", "char_pudgy_ice_rare_01", 1.2,
     "Blue-gray pudgy with cloud scarf and belt."),
    ("stylized+3d+monster (1).glb", "char_pudgy_lemon_rare_01", 1.2,
     "Yellow spotted pudgy with a red hat."),
    ("stylized+3d+monster+model (1).glb", "char_pudgy_desert_rare_01", 1.2,
     "Brown bear-suit pudgy with a tiny crown."),
]


def main() -> int:
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    failed = 0
    for src_name, asset_id, height, notes in _BATCH:
        if only and asset_id not in only and src_name not in only:
            continue
        src = _DL / src_name
        if not src.is_file():
            print(f"MISSING {src}", file=sys.stderr)
            failed += 1
            continue
        dest = _REPO / "assets" / "models" / asset_id / f"{asset_id}.glb"
        if dest.is_file() and dest.stat().st_size > 100_000:
            print(f"SKIP exists {asset_id}")
            continue
        cmd = [
            sys.executable, str(_IMPORT),
            "--src", str(src),
            "--asset-id", asset_id,
            "--height", str(height),
            "--max-tex", "1024",
            "--jpeg-quality", "88",
            "--notes", notes,
        ]
        print("+", asset_id, "<-", src_name)
        proc = subprocess.run(cmd, cwd=_REPO)
        if proc.returncode != 0:
            print(f"FAIL {asset_id}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
