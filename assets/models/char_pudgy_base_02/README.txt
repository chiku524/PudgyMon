PudgyMon shared base variant — char_pudgy_base_02
=================================================

Source: Immersive Studio job c00ebe10-82b0-4f59-8f67-477d3852e0d4
Pack asset_id: pudgy_mon_body_shared_base_01 (remapped to char_pudgy_base_02)

Compare with char_pudgy_base_01 via Esc Nest menu → Characters.

Pipeline:
  1. polish_character_glb.py (floor-pivot, height 1.2, sockets)
  2. toon_material_pass.py (soft matte cartoon)
  Runtime: CHARACTER_MESH_YAW_OFFSET (+90° Y) for Bevy −Z forward

Registry: target_height 1.2 · uniform_scale 1.0
Contract: docs/CHARACTERS.md
