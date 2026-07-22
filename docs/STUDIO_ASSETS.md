# Immersive Studio → PudgyMon workflow

PudgyMon uses [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) to generate **Tripo AI** meshes with baked PBR, then imports GLBs into `assets/models/` for the Bevy runtime.

Placement is **data-driven**: import a pack → register the asset → add a marker in `data/rooms/*.json` → play. No Rust spawn code required for props/stations.

**This-week drop checklist (meshes + audio):** [DROP_IN.md](DROP_IN.md)

## Prerequisites

1. **Immersive Studio desktop** v0.1.7+ (or local worker) with `STUDIO_TRIPO_API_KEY` set — see `scripts/studio/worker.env.example`.
2. Python 3 for the import / register scripts.

## Generate a pack (Studio)

1. Open Immersive Studio and run a job with **Tripo textures** and **Generate 3D mesh** enabled.
2. Download `pack.zip` when complete.
3. In `pack_diagnostics.json`, confirm Tripo mesh + textures succeeded (not Comfy-only sidecars).

From the repo root:

```bash
python scripts/import_immersive_studio_pack.py path/to/pack.zip
```

With `--update` to refresh `target_height` for assets already in the registry.

The script:

- Copies `Models/<asset_id>/` → `assets/models/<asset_id>/`
- Optionally copies `Textures/<asset_id>/` sidecars (skip with `--no-textures` when Tripo baked PBR into the GLB)
- Merges entries into `assets/studio_registry.json`

Register a single id without a full pack:

```bash
python scripts/register_studio_asset.py my_new_prop_01 --height 1.2
```

Validate registry ↔ disk ↔ room layouts:

```bash
python scripts/validate_studio_assets.py
cargo test room_asset_ids_exist_in_registry_or_are_null
```

## Place in a room (required for playable)

Edit the vault JSON under `data/rooms/` (or `arena.json` for the persistent shell).

**Marker template** — copy/paste and fill in:

```json
{
  "id": "my_station_slot",
  "role": "station",
  "asset_id": "my_new_prop_01",
  "position": [0.0, 0.0, 0.0],
  "rotation_y_deg": 0.0,
  "scale": 1.0,
  "interactable": { "kind": "vault_objective" },
  "greybox": {
    "size": [1.0, 1.0, 1.0],
    "color": [0.5, 0.5, 0.5],
    "label": "My Station"
  }
}
```

| Field | Notes |
|-------|-------|
| `id` | Stable slot name (used by interact RPCs). Never rename casually. |
| `role` | `station` / `decoration` / `zone` / `sign` / `sort_chute` / `floor_vfx` / `floor` / `wall` / `ceiling` |
| `asset_id` | Must exist in `studio_registry.json`. Omit or `null` to keep greybox-only. |
| `position` | World meters. Floor-pivoted GLBs use `y = 0`. |
| `scale` | Extra multiplier on top of registry scale (default `1.0`). |
| `interactable` | Optional. Kinds: `crane`, `vault_objective`, `sort_chute`, `breaker`, `coolant_valve`, `meltdown_door`. |
| `greybox` | **Required** for interactables — CI/headless fallback when GLB missing. |

Then verify:

```bash
cargo run -- local
```

Walk to the marker and press **F** if it has an `interactable`.

## Runtime wiring (Bevy)

| Piece | Location |
|-------|----------|
| Asset registry JSON | `assets/studio_registry.json` |
| Room / arena layouts | `data/rooms/*.json` |
| Registry loader | `src/data/studio_registry.rs` |
| Layout schema | `src/data/room_layout.rs` |
| GLB spawn | `src/assets/mod.rs` (`WorldAssetRoot`) |
| Marker spawn | `src/rooms/spawner.rs` |
| Room swap | `src/rooms/layout.rs` |
| Character hook | `PlayerVisualSpec` in `src/player/mod.rs` |

## Character models

Players use a shared **Pudgy** figure (`char_pudgy_base_01`) with optional species skins and detachable accessories. Set `PlayerVisualSpec.model_id` to a registry `asset_id` and fill `accessories` slots (`hat`, `necklace`, `shoes`, `back`, `face`, `hands`) with `acc_*` ids — see [CHARACTERS.md](CHARACTERS.md) and [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md).

Until accessory GLBs exist, leave those fields empty; `hat_slot` 0–7 remains a legacy roster index.

## Regenerating existing assets with Tripo

Older packs may use ComfyUI sidecars or placeholder meshes. Re-run Studio jobs with the same `asset_id`, import with `--update`, and re-test scale/placement in the Bevy level. Use marker `"scale"` or registry `"uniform_scale"` to fine-tune without re-exporting.

## Still needed (wishlist)

See [ASSET_WISHLIST.md](ASSET_WISHLIST.md) for Nest props, stage props, species skins, and accessory batches that still use stand-ins.

**Ready-to-paste Immersive Studio / Tripo prompts:** [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md)
