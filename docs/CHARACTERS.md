# Pudgy Monsters roster

Chunky party creatures for **PudgyMon: Party Saga**. One shared base figure, species skins that match the same proportions, and **detachable accessories** on fixed sockets so movement and cosmetics stay in sync.

Selectable crew matches [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md) Priority 0 (**5 characters**).

## Playable roster

| Id | Label | Notes |
|----|-------|-------|
| `char_pudgy_base_01` | Base Pudgy | Shared coral-peach base (default) |
| `oceanic_pudgymon_01` | Ocean Pudgy | Ocean species — Studio locomotion + emotes |
| `char_pudgy_forest_01` | Forest Pudgy | Forest/leaf — Studio 41-bone rig + walk/run clips |
| `char_pudgy_lava_01` | Lava Pudgy | Lava — Studio 41-bone rig + walk/run clips |
| `char_pudgy_sky_01` | Sky Pudgy | Sky Tripo mesh on Studio 41-bone (lava donor clips) |

Default crew id: [`data/player_defaults.json`](../data/player_defaults.json). Roster: [`data/characters/roster.json`](../data/characters/roster.json). Switch live in Esc Nest → **Characters**.

Short vs tall: `auto_rig_glb.py --height 0.95` / `--height 1.35` bakes playable size for stubby bodies. Studio-rigged imports (`import_rigged_character_glb.py`) scale to ~1.2 m and rename NLA tracks to the shared clip names. `transfer_crew_clips.py` copies locomotion between matching 41-bone Studio bodies.

## Sync + tooling

```bash
# Align assets/models to STUDIO_PROMPTS.md (prune extras, materialize the 5 crew)
python scripts/sync_studio_prompt_assets.py

# Pre-rigged Studio body (41-bone + NLA) → party clip names + Bevy-safe GLB
python scripts/import_rigged_character_glb.py --src path.glb --asset-id char_pudgy_forest_01

# Static mesh + donor Studio rig/clips (when Tripo didn't ship animation)
python scripts/bind_mesh_to_studio_rig.py --mesh sky.glb --donor char_pudgy_lava_01 --asset-id char_pudgy_sky_01

# Static body → stubby rig + clips (legacy fallback)
python scripts/auto_rig_glb.py --src path.glb --asset-id char_pudgy_sky_01 --force stubby

# Copy clips between same-rig Studio bodies
python scripts/transfer_crew_clips.py --from oceanic_pudgymon_01 --to char_pudgy_base_01

# Bevy-safe size pass
python scripts/optimize_glb.py --batch assets/models --glob "*/*.glb"
```

## Pudgy Character Contract

| Rule | Value |
|------|--------|
| Base asset id | `char_pudgy_base_01` |
| Species ids | `oceanic_pudgymon_01`, `char_pudgy_forest_01`, `char_pudgy_lava_01`, `char_pudgy_sky_01` |
| Playable height | ~1.2 m |
| Pivot | Floor center, +Y up, character faces **−Z** (Bevy forward) |
| Shared clip names | `idle`, `walk`, `run`, `jump`, `emote_wave`, `emote_dance` (+ `emote_scared` when present) |
| Accessory sockets | Created at runtime on `Head` / spine / limb bones (`Socket_Hat`, `Socket_Necklace`, `Socket_Shoes`, `Socket_Back`, `Socket_Face`, `Socket_Hands`). Not embedded in crew GLBs. |

**Texture format:** PNG for painted/baked baseColor (sharp eyes & edges). JPEG is OK for ORM/emissive only. See optimizer notes in [DROP_IN.md](DROP_IN.md) and [STUDIO_ASSETS.md](STUDIO_ASSETS.md).
