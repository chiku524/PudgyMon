# Drop-in guide (art + audio)

Wired so you can drop files and play — **no Rust required** for normal replacements.

Related: [CHARACTERS.md](CHARACTERS.md) · [STUDIO_ASSETS.md](STUDIO_ASSETS.md) · [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md) · [ASSET_WISHLIST.md](ASSET_WISHLIST.md)

---

## Pudgy character (priority)

| What | Drop path | Then |
|------|-----------|------|
| Base / species | `assets/models/<id>/<id>.glb` | `python scripts/sync_studio_prompt_assets.py` then auto-rig / transfer / optimize |
| Clip reuse | — | `python scripts/transfer_crew_clips.py --from oceanic_pudgymon_01 --to <id>` |
| Accessories | `assets/models/acc_*_01/…` | Must match [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md) |
| Nest props | `env_nest_*`, `prop_vibe_*`, pads | Same |

Selectable crew (**5**): `char_pudgy_base_01`, `oceanic_pudgymon_01`, `char_pudgy_forest_01`, `char_pudgy_lava_01`, `char_pudgy_sky_01`.

## GLB size optimization

Quality-first (preserves painted candy detail; Bevy-safe, no Draco/KTX2/WebP):

```bash
# Prefer Blender bake/char pipelines for Tripo exports
python scripts/blender_bake_optimize_glb.py --batch assets/models --glob "env_*/*.glb" --from-pre-opt
python scripts/blender_char_optimize_glb.py --all --from-pre-opt

# Light UV-safe pass (never JPEG-encodes baseColor)
python scripts/optimize_glb.py assets/models/char_pudgy_base_01/char_pudgy_base_01.glb --preset game
python scripts/optimize_glb.py --batch assets/models --glob "acc_*/*.glb"   # guesses prop
```

Import pipelines call the same optimizer after export with quality-first defaults (1024px, high JPEG for non-baseColor only).

---

## Audio

| Kind | Folder | Fallback |
|------|--------|----------|
| SFX | `assets/audio/sfx/` | Pitch tones |
| Music | `assets/audio/music/` | Silence |
| VO | `assets/audio/vo/` | HUD text |

Restart after dropping clips.

---

## Quick checklist

1. [x] `char_pudgy_pink_01` / `char_pudgy_stylized_01` playable roster (see CHARACTERS.md)  
2. [ ] Accessory starter pack (hats / necklaces / shoes)  
3. [ ] Nest props (`env_nest_egg_01`, benches, mushrooms)  
4. [ ] Music bed for The Nest / Party Saga  
5. [ ] SFX: pickup / KO / finish  
6. [ ] Open claim companion (`Ctrl+O`) after minting path is live  
