ShipHappens model notes
=======================

asset_id: REPLACE_ME
target_height_m: 1.0
pivot: floor (origin at ground center)
suggested_room: hr_orientation | cargo_gantry | breaker_panic | shuttle_meltdown | arena
suggested_marker_id: (stable id in data/rooms/*.json)
interactable: none | crane | vault_objective | sort_chute | breaker | coolant_valve | meltdown_door

After Tripo export:
  1. python scripts/import_immersive_studio_pack.py path/to/pack.zip
     OR copy this folder to assets/models/<asset_id>/ and run
        python scripts/register_studio_asset.py <asset_id> --height 1.0
  2. Set "asset_id" on the room marker (keep greybox for CI fallback)
  3. Play in Unity Hub → unity/
