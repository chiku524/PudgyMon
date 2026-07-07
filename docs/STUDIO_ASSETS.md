# Immersive Studio → ShipHappens workflow

ShipHappens uses [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) to generate **Tripo AI** meshes with baked PBR, then imports them into Godot via `third_party/immersive_studio` helpers.

## Prerequisites

1. **Immersive Studio desktop** v0.1.7+ (or local worker) with `STUDIO_TRIPO_API_KEY` set — see `scripts/studio/worker.env.example`.
2. Godot **4.3+** for ShipHappens.

## Generate a pack (Studio)

1. Open Immersive Studio → **Import target: Godot 4**.
2. Enable **Tripo textures** and **Generate 3D mesh**.
3. Run a job; download `pack.zip` when complete.
4. In `pack_diagnostics.json`, confirm Tripo mesh + textures succeeded (not Comfy-only sidecars).

## Import into ShipHappens

From the repo root:

```bash
python scripts/import_immersive_studio_pack.py path/to/pack.zip
```

With `--update` to refresh `target_height` for assets already in the registry.

The script:

- Copies `Models/<asset_id>/` → `assets/models/<asset_id>/`
- Optionally copies `Textures/<asset_id>/` sidecars (skip with `--no-textures` when Tripo baked PBR into the GLB)
- Merges entries into `assets/studio_registry.json`

Then open Godot so GLBs reimport.

## Runtime wiring

| Piece | Location |
|-------|----------|
| Godot helpers | `third_party/immersive_studio/` (sync via `scripts/sync-immersive-studio-godot.sh`) |
| Asset registry JSON | `assets/studio_registry.json` |
| Autoload | `ImmersiveStudioAssets` → `ImmersiveStudioRegistry.register_all()` |
| Job props | `immersive_studio_prop.gd` on interactable scenes (`asset_id` in inspector) |
| Station dressing | `station_visuals.gd` → `ImmersiveStudioModel.spawn_at()` |

## Place a new prop in a scene

**Interactable job:**

1. Add a `Node3D` child with `third_party/immersive_studio/scripts/immersive_studio_prop.gd`.
2. Set `asset_id` in the inspector.

**Station layout (code):**

```gdscript
ImmersiveStudioModel.spawn_at(parent, "my_asset_id", Vector3(1, 0, 2), 0.0, 1.2)
```

Heights come from `studio_registry.json` unless you pass `target_height` / `target_width`.

## Regenerating existing assets with Tripo

Older packs may use ComfyUI sidecars or placeholder meshes. Re-run Studio jobs with the same `asset_id`, import with `--update`, and re-test scale/placement in `station_visuals.gd` or job scenes.

## Sync helpers from immersive.labs

```bash
bash scripts/sync-immersive-studio-godot.sh
```

Set `IMMERSIVE_LABS_ROOT` if your monorepo clone is not at `../../Desktop/vibe-code/immersive.labs`.
