# Immersive Studio prompt pack V2 — PudgyMon: Party Saga

**2513 new assets** on top of pack 1 ([STUDIO_PROMPTS.md](STUDIO_PROMPTS.md)). Built to burn Tripo credits on reusable Party Saga content: cosmetics, Nest, Race / Vibe / Shooter kits, UGC deco, rewards.

Copy-paste prompts for [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) / Tripo jobs.

**Important:** Studio does **not** cache prior prompts. Every job is independent. Each fenced prompt is complete — paste it alone. **Hard limit: ≤ 1000 characters.**

After generation → import → place: [STUDIO_ASSETS.md](STUDIO_ASSETS.md). Character contract: [CHARACTERS.md](CHARACTERS.md).

**Theme lock:** cute chunky **Pudgy Monsters** in a party playground — The Nest + Race / Vibe Collect / Shooter. Not freight, vaults, or corporate comedy.

## Export settings (all jobs)

| Setting | Value |
|---------|--------|
| Format | GLB with baked Tripo PBR |
| Pivot | Floor center (characters / props) · wear origin (accessories) |
| Facing | Character faces −Z (Unity/glTF forward) when possible |
| Units | 1 unit ≈ 1 meter |
| Naming | Folder + file = `asset_id` / `asset_id.glb` |
| Characters | After polish: baked ~1.2 m height, `uniform_scale` `1.0` |

**Art direction:** soft stylized cartoon 3D (Pokémon / Kirby / Animal Crossing / Fall Guys softness). Matte painted candy — **not** clay, vinyl, or photoreal.

## Optional negative prompt

```
photorealistic, grimdark, horror, blood, realistic weapons, space freight, corporate office, tiny unreadable labels, multiple objects, diorama, landscape, adult human proportions, clay, polymer clay, ceramic, earthen texture, stone, mud, fingerprint texture, glossy vinyl, shiny plastic, injection molded, clearcoat, specular hotspots, subsurface wax, dirty, scratched, fuzzy fur, uncanny realism
```

**Accessory negative (if separate field):**

```
character, creature, mascot, monster, animal, person, human, avatar, mannequin, dummy head, bust, torso, body, face, eyes, mouth, arms, legs, hands, feet, wearer, model wearing item, full figure, chibi character, cartoon creature, pudgy monster body
```

## Pack contents (2513 assets)

| Category | Count |
|----------|------:|
| [acc_back](studio_prompts_v2/acc_back.md) | 159 |
| [acc_face](studio_prompts_v2/acc_face.md) | 175 |
| [acc_hands](studio_prompts_v2/acc_hands.md) | 140 |
| [acc_hats](studio_prompts_v2/acc_hats.md) | 389 |
| [acc_necklaces](studio_prompts_v2/acc_necklaces.md) | 316 |
| [acc_shoes](studio_prompts_v2/acc_shoes.md) | 232 |
| [characters_npc](studio_prompts_v2/characters_npc.md) | 6 |
| [characters_seasonal](studio_prompts_v2/characters_seasonal.md) | 6 |
| [characters_species](studio_prompts_v2/characters_species.md) | 40 |
| [nest](studio_prompts_v2/nest.md) | 216 |
| [race](studio_prompts_v2/race.md) | 163 |
| [rewards_vfx](studio_prompts_v2/rewards_vfx.md) | 80 |
| [shooter](studio_prompts_v2/shooter.md) | 144 |
| [ugc_deco](studio_prompts_v2/ugc_deco.md) | 250 |
| [vibe](studio_prompts_v2/vibe.md) | 197 |

### By job batch

| Batch | Count |
|-------|------:|
| `accessories` | 1411 |
| `characters` | 52 |
| `nest` | 216 |
| `race` | 163 |
| `rewards` | 80 |
| `shooter` | 144 |
| `ugc` | 250 |
| `vibe` | 197 |

## Machine-readable catalog

| File | Use |
|------|-----|
| [`data/studio_prompts_v2/catalog.json`](../data/studio_prompts_v2/catalog.json) | Full prompts + metadata |
| [`data/studio_prompts_v2/manifest.csv`](../data/studio_prompts_v2/manifest.csv) | Spreadsheet tracking |
| [`data/studio_prompts_v2/by_category/`](../data/studio_prompts_v2/by_category/) | Per-category JSON |

```bash
# Regenerate this pack from the generator
python scripts/generate_studio_prompts_v2.py

# Print one prompt
python scripts/generate_studio_prompts_v2.py --print-id acc_hat_ocean_shell_01

# Stats
python scripts/generate_studio_prompts_v2.py --stats
```

## Suggested credit burn order

1. **Characters** — new biomes + rare morphs + Nest NPCs (`characters`)
2. **Accessories** — hats → necklaces → shoes → back → face → hands (`accessories`)
3. **Nest** — lamps, booths, flora, pads, playground (`nest`)
4. **Race kit** — gates, barriers, ramps, boost pads, track (`race`)
5. **Vibe kit** — orb / flower / crystal variants (`vibe`)
6. **Shooter kit** — cover, targets, toy blasters, KO decals (`shooter`)
7. **Rewards / VFX** — trophies, bursts, mode icons (`rewards`)
8. **UGC deco** — map creator palette fillers (`ugc`)

Work in batches of 20–50 jobs. After each batch:

```bash
python scripts/import_immersive_studio_pack.py path/to/pack.zip
python scripts/validate_studio_assets.py
```

Characters:

```bash
python scripts/register_studio_asset.py <asset_id> --height 1.2 --scale 1.0 --update
python scripts/polish_character_glb.py <asset_id>
python scripts/toon_material_pass.py <asset_id>
```

## Copy-paste chapters

Browse prompts by category under [`docs/studio_prompts_v2/`](studio_prompts_v2/).

## Relation to pack 1

Pack 1 (~47) remains the **Priority 0–3** core set. V2 **does not duplicate** those `asset_id`s. Prefer regenerating pack-1 “best-effort” meshes (pads, checkpoint, cover, blaster, KO marker) from pack 1 prompts before burning V2 volume.
