# Drop-in guide (art + audio)

Wired so you can drop files and play — **no Rust required** for normal replacements.

Related: [CHARACTERS.md](CHARACTERS.md) · [STUDIO_ASSETS.md](STUDIO_ASSETS.md) · [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md) · [ASSET_WISHLIST.md](ASSET_WISHLIST.md)

---

## Pudgy character (priority)

| What | Drop path | Then |
|------|-----------|------|
| Pink Pudgy | `assets/models/char_pudgy_pink_01/char_pudgy_pink_01.glb` | `python scripts/import_rigged_character_glb.py … --asset-id char_pudgy_pink_01` |
| Cartoon Pudgy | `assets/models/char_pudgy_stylized_01/char_pudgy_stylized_01.glb` | `python scripts/import_dense_character_glb.py` then `rig_and_animate_pudgy.py` |
| Water Pudgy | `assets/models/char_pudgy_water_01/char_pudgy_water_01.glb` | `python scripts/import_rigged_character_glb.py … --asset-id char_pudgy_water_01` |
| Species skin | `assets/models/<species_id>/<species_id>.glb` | Same scale as base; see CHARACTERS.md |
| Accessories | `assets/models/acc_hat_*/…`, `acc_necklace_*`, `acc_shoes_*`, … | Register; equip via `PlayerVisualSpec.accessories` |
| Nest egg | `assets/models/env_nest_egg_01/env_nest_egg_01.glb` | Register; later wire into Nest spawn |
| Nest bench | `assets/models/env_nest_bench_01/…` | Same |
| Vibe mushroom | `assets/models/prop_vibe_mushroom_01/…` | Same |

Until the Pudgy GLB exists, players use a **procedural stub** (round body + head). Accessory GLBs are optional until sockets are parented in-engine.

Validate:

```bash
python scripts/validate_studio_assets.py
cargo test
cargo run
```

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
