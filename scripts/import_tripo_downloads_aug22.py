#!/usr/bin/env python3
"""Import the Aug 22 Tripo Downloads batch with visually assigned asset_ids.

Filenames from Studio were mixed up — IDs below come from rendered previews,
not the download names.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_IMPORT = _REPO / "scripts" / "import_dense_character_glb.py"
_DL = Path(r"C:\Users\chiku\Downloads")

# (src filename, asset_id, height, notes)
_BATCH: list[tuple[str, str, float, str]] = [
    # Isolated hats (visual ID — filenames were wrong)
    ("ember+crown+hat+3d+model.glb", "acc_hat_candy_scoop_01", 0.32,
     "Ice-cream swirl crown + cherry (download was labeled ember crown)."),
    ("ocean+shell+helmet+3d+model.glb", "acc_hat_honey_pot_01", 0.28,
     "Cream dessert beanie, chocolate brim and star (labeled ocean shell)."),
    ("soft+thundercloud+cap+3d+model.glb", "acc_hat_storm_cap_01", 0.26,
     "Puffy thundercloud cap."),
    ("racing+helmet+3d+model.glb", "acc_hat_race_helmet_01", 0.26,
     "Stubby racing helmet, cream/tan with cyan ear cup."),
    ("flower+wreath+3d+model.glb", "acc_hat_forest_leaf_01", 0.26,
     "Green leaf wreath (no flowers)."),
    ("soft+candy+crown+3d+model.glb", "acc_hat_ice_crown_01", 0.28,
     "Soft cream crown with candy spots."),
    ("ice+cream+hat+3d+model.glb", "acc_hat_sprinkle_cap_01", 0.28,
     "Gray sprinkle-dome hat."),
    ("crescent+moon+hat+3d+model.glb", "acc_hat_night_moon_01", 0.28,
     "Crescent moon hat."),
    ("crystal+tiara+3d+model.glb", "acc_hat_lava_ember_01", 0.26,
     "Rocky ember crown (labeled crystal tiara)."),
    ("cloud+beret+3d+model.glb", "acc_hat_sky_cloud_01", 0.24,
     "Puffy cloud-lobe beret."),
    ("leaf+crown+hat+3d+model.glb", "acc_hat_meadow_wreath_01", 0.22,
     "Cream crown with mixed leaf nubs."),
    # Characters
    ("pudgymon+3d+model (1).glb", "char_pudgy_candy_01", 1.2,
     "Peach dumpling with hovering cherry — candy species."),
    ("cute+pink+character+3d+model.glb", "char_pudgy_coral_01", 1.2,
     "Peach body, coral side-fins — coral reef species."),
    ("stylized+character+3d+model.glb", "char_pudgy_sprout_01", 1.2,
     "Tan body, orange sprout nub."),
    ("stylized+pudgy+monster+3d+model.glb", "npc_nest_dj_01", 1.2,
     "Gray pudgy wearing brown headphones — Nest DJ."),
    ("pudgy+cartoon+character+3d+model (1).glb", "char_pudgy_berry_01", 1.2,
     "Gray body, salmon berry spots + loose orbs."),
    ("pudgy+monster+3d+model (2).glb", "char_pudgy_cloud_01", 1.2,
     "Peach pudgy with extra shoulder puffs / crest."),
    ("stylized+3d+creature.glb", "npc_nest_ref_01", 1.2,
     "Cream pudgy with tiny horns and freckle spots — Nest ref look."),
    ("stylized+cartoon+character+3d+model.glb", "char_pudgy_night_01", 1.2,
     "Dark untextured night-palette body, head fin."),
    ("pudgymon+character+3d+model (5).glb", "char_pudgy_ice_01", 1.2,
     "Slate body with white pearl frost spots."),
    ("pudgymon+3d+model.glb", "char_pudgy_lava_party_01", 1.2,
     "Tan body, charcoal wavy cap, pink nub — lava party seasonal."),
    ("stylized+creature+3d+model.glb", "npc_nest_shop_01", 1.2,
     "Gray spotted pudgy — Nest shopkeep stand-in."),
    ("cute+dumpling+creature+3d+model.glb", "char_pudgy_meadow_01", 1.2,
     "Beige dumpling, petal tuft and pink ear nubs."),
    ("pudgy+cartoon+character+3d+model.glb", "char_pudgy_peach_01", 1.2,
     "Peach chick-dumpling, three head bumps."),
    ("stylized+3d+character (1).glb", "char_pudgy_lemon_01", 1.2,
     "Peach-pink, lime-yellow eyes, tiny horn."),
    ("pudgymon+character+3d+model (4).glb", "npc_nest_photo_01", 1.2,
     "Beige pudgy with dark beret — Nest photographer."),
    ("stylized+cartoon+3d+model.glb", "char_pudgy_forest_bloom_01", 1.2,
     "Tan, pink spots, leaf sprout — forest bloom seasonal."),
    ("stylized+dragon+3d+model.glb", "char_pudgy_storm_01", 1.2,
     "Gray dragon-pudgy, horns and back spikes."),
    ("stylized+pudgy+creature+3d+model (1).glb", "char_pudgy_honey_01", 1.2,
     "Cream dumpling with beak snout — honey stand-in."),
    ("pudgy+monster+3d+model (1).glb", "char_pudgy_cocoa_01", 1.2,
     "Cream body, chocolate-chip spots."),
    ("pudgymon+character+3d+model (3).glb", "char_pudgy_peach_rare_01", 1.2,
     "Soft peach dumpling, three tufts — peach rare."),
    ("stylized+chibi+creature+3d+model.glb", "char_pudgy_grape_01", 1.2,
     "Gray pudgy, grape-nodule hat and backpack bake."),
    ("pudgy+monster+3d+model.glb", "char_pudgy_mint_01", 1.2,
     "Olive-sage body, pink orb shoulder."),
    ("pudgymon+character+3d+model (2).glb", "char_pudgy_cocoa_rare_01", 1.2,
     "Beige body, chocolate-pour hair."),
    ("stylized+monster+3d+model (6).glb", "char_pudgy_crystal_01", 1.2,
     "Charcoal body, tan crystal/rock growths."),
    ("pudgymon+character+3d+model (1).glb", "npc_nest_coach_01", 1.2,
     "Tan pudgy with spiked cap — Nest coach stand-in."),
    ("stylized+3d+monster.glb", "npc_nest_bard_01", 1.2,
     "Gray rocky pudgy — Nest bard stand-in."),
    ("pudgy+pastel+character+3d+model.glb", "char_pudgy_aurora_01", 1.2,
     "Charcoal body, gold leaf crown, star dots."),
    ("stylized+pudgy+creature+3d+model.glb", "char_pudgy_bubble_01", 1.2,
     "Gray pudgy with bubble cluster on the back."),
    ("cactus+hat+3d+model.glb", "char_pudgy_desert_01", 1.2,
     "Full cactus-spined pudgy (download was labeled hat)."),
    ("cute+pudgy+monster+3d+model.glb", "char_pudgy_ocean_festival_01", 1.2,
     "Gray/yellow/brown festival markings, pink blush."),
    ("pudgymon+character+3d+model (6).glb", "char_pudgy_storm_rare_01", 1.2,
     "Dark spiky-snout pudgy — storm rare."),
    ("stylized+3d+pokemon+character.glb", "char_pudgy_ember_01", 1.2,
     "Peach pudgy, orange-ember tail and horns."),
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
            sys.executable,
            str(_IMPORT),
            "--src",
            str(src),
            "--asset-id",
            asset_id,
            "--height",
            str(height),
            "--max-tex",
            "1024",
            "--jpeg-quality",
            "88",
            "--notes",
            notes,
        ]
        print("+", asset_id, "<-", src_name)
        proc = subprocess.run(cmd, cwd=_REPO)
        if proc.returncode != 0:
            print(f"FAIL {asset_id}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
