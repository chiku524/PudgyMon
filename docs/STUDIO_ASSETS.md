# Immersive Studio → PudgyMon workflow

PudgyMon uses [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) to generate **Tripo AI** meshes with baked PBR, then imports GLBs into `assets/models/` for the Unity runtime.

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
cargo test --lib room_asset_ids_exist_in_registry_or_are_null
```

## Optimize dense Tripo GLBs

Best path for **no holes + candy paint + fast loads**: remesh a closed low-poly cage, then **bake** Tripo diffuse onto it (Unity-safe JPEG, no Draco/KTX2):

```bash
# From dense .pre_opt backups (recommended)
python scripts/blender_bake_optimize_glb.py --batch assets/models --glob "*/*.glb" --from-pre-opt

# single asset
python scripts/blender_bake_optimize_glb.py assets/models/env_nest_bench_01/env_nest_bench_01.glb --from-pre-opt
```

- **Static props / accessories / env:** default **preserve** path keeps Tripo UVs + paint (meshopt simplify + PNG baseColor). This avoids remesh+bake color bleed that made balloon arches / striped umbrellas look muddy. Files are larger (~10–20 MB) because Tripo topology resists aggressive decimation — prefer that over muddy candy. Use `--path remesh` only when the mesh is too broken (holes).
- **Skinned characters:** preserve Tripo UVs + meshopt simplify (~48k tris) + PNG basecolor (keeps armature clips):

```bash
python scripts/blender_char_optimize_glb.py --all --from-pre-opt
```

Do not skin-preserve Decimate characters alone — Tripo topology tears into holes. Prefer the preserve path above; remesh+bake+weight-transfer is the fallback for broken meshes.

Fallback UV-only decimate (no bake): `scripts/blender_decimate_glb.py` — can leave holes on Tripo topology; prefer bake-optimize (props) / char-optimize (skins).

**Quality policy:** face/tex budgets are quality-first (not max compression). `optimize_glb.py` never JPEG-encodes baseColor (chroma smear). Baked atlases stay PNG.
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

Then verify in Unity Play mode (The Nest). Stage props use `asset_id` on map blocks.

## Runtime wiring (Unity)

| Piece | Location |
|-------|----------|
| Asset registry JSON | `assets/studio_registry.json` |
| Official maps | `data/maps/*.json` |
| Registry + GLB spawn | `unity/Assets/PudgyMon/Scripts/Assets/` |
| Character / accessories | `CrewRoster` + `AccessoryCatalog` in `Scripts/Meta/` |

## Character models

Players use playable Pudgys (`char_pudgy_pink_01` / `char_pudgy_stylized_01`) with a **shared skinned armature + clips**, optional species skins, and detachable accessories. After importing a static Tripo body, run `python scripts/rig_and_animate_pudgy.py --asset-id <id>`. Set `PlayerVisualSpec.model_id` to a registry `asset_id` and fill `accessories` slots with `acc_*` ids — see [CHARACTERS.md](CHARACTERS.md).

Until accessory GLBs exist, leave those fields empty; `hat_slot` 0–7 remains a legacy roster index.

## Regenerating existing assets with Tripo

Older packs may use ComfyUI sidecars or placeholder meshes. Re-run Studio jobs with the same `asset_id`, import with `--update`, and re-test scale/placement in Unity. Use registry `"uniform_scale"` to fine-tune without re-exporting.

## Still needed (wishlist)

See [ASSET_WISHLIST.md](ASSET_WISHLIST.md) for Nest props, stage props, species skins, and accessory batches that still use stand-ins.

**Ready-to-paste Immersive Studio / Tripo prompts:** [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md) (core ~47) · [STUDIO_PROMPTS_V2.md](STUDIO_PROMPTS_V2.md) (volume ~2500)
