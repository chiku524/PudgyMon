# Asset wishlist — PudgyMon: Party Saga

Stand-ins keep The Nest and stages playable. Replace these when dedicated Tripo meshes land — prefer swapping `asset_id` (and maybe `scale`) without renaming stable marker ids.

**Copy-paste Tripo / Immersive Studio prompts:** [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md)  
**Shared figure + accessory sockets:** [CHARACTERS.md](CHARACTERS.md)

---

## Characters (shared base)

| Priority | Suggested `asset_id` | Plugs into | Current stand-in |
|----------|----------------------|------------|------------------|
| Done | `char_pudgy_base_01` | `PlayerVisualSpec.model_id` / `player_defaults.json` | Studio job 2ddc5433… imported (polished, scale 1.0) |
| High | `oceanic_pudgymon_01` | Species skin override | — |
| High | `char_pudgy_forest_01` | Species skin | — |
| High | `char_pudgy_lava_01` | Species skin | — |
| High | `char_pudgy_sky_01` | Species skin | — |
| Legacy | `char_crew_base_01` | retired (freight era) | — |

All species must obey the **Pudgy Character Contract** (same proportions + accessory sockets as the base).

---

## Accessories (separate GLBs on shared sockets)

| Priority | Slot | Suggested ids | Plugs into |
|----------|------|---------------|------------|
| Done | Hat | `acc_hat_*_01` (8 procedural) | Esc → Accessories |
| Done | Necklace | `acc_necklace_*_01` (4) | Esc → Accessories |
| Done | Shoes | `acc_shoes_*_01` (4) | Esc → Accessories |
| Done | Back | `acc_back_*_01` (3) | Esc → Accessories |
| Done | Face | `acc_face_*_01` (3) | Esc → Accessories |
| Done | Hands | `acc_hands_*_01` (2) | Esc → Accessories |

Hats are no longer roster-only tint indices — equip real meshes via Nest **Accessories**. Rebuild: `python scripts/build_procedural_party_assets.py`.

---

## The Nest

| Priority | Suggested `asset_id` | Replace / place | Current stand-in |
|----------|----------------------|-----------------|------------------|
| Done | `env_nest_egg_01` | Nest centerpiece | Procedural GLB |
| Done | `env_nest_bench_01` | Nest seating ring | Procedural GLB |
| Done | `prop_vibe_mushroom_01` | Nest flora ring | Procedural GLB |
| Done | `env_pad_race_01` / `_vibe_01` / `_shooter_01` / `_party_01` | Mode pads | Procedural GLB |

---

## Stages

### Race

| Priority | Suggested `asset_id` | Notes |
|----------|----------------------|-------|
| Medium | `prop_race_checkpoint_01` | Arch gate |
| Medium | `prop_race_cone_01` | Course markers |
| Medium | `prop_race_banner_01` | Finish / start |
| Low | `env_race_ramp_01` | Soft ramp |

### Vibe Collect

| Priority | Suggested `asset_id` | Notes |
|----------|----------------------|-------|
| High | `prop_vibe_orb_01` | Collectible orb mesh |
| Medium | `prop_vibe_flower_01` | Arena flora deco |
| Medium | `prop_vibe_crystal_01` | Alternate pickup look |

### Shooter

| Priority | Suggested `asset_id` | Notes |
|----------|----------------------|-------|
| Medium | `prop_target_star_01` | Pop target |
| Medium | `prop_cover_block_01` | Soft cover |
| Low | `prop_blaster_toy_01` | Decoration toy only |
| Low | `vfx_ko_burst_marker_01` | Floor KO decal |

---

## Drop-in checklist

1. Generate + import pack (`scripts/import_immersive_studio_pack.py`)
2. Confirm GLB at `assets/models/<id>/<id>.glb`
3. Characters → register with `--height 1.2 --scale 0.27`
4. Accessories → register; equip via `PlayerVisualSpec.accessories.*`
5. Nest / stage props → swap `asset_id` on markers (or Nest spawn later)
6. `python scripts/validate_studio_assets.py`
7. `cargo run -- local` and check scale / pivot / socket alignment
