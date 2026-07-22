# Pudgy Monsters roster

Chunky party creatures for **PudgyMon: Party Saga**. One shared base figure, species skins that match the same proportions, and **detachable accessories** on fixed sockets so movement and cosmetics stay in sync.

## Base rigs

### `char_pudgy_base_01` — Soft Cartoon
- Round body, oversized head, stubby limbs
- Soft **stylized cartoon 3D** look (Pokémon / Kirby / Animal Crossing vibes) — painted matte candy colors, not clay or glossy vinyl; family-friendly
- Playable height ~1.2 m (read as “cute chunky,” not adult humanoid)
- GLB: `assets/models/char_pudgy_base_01/char_pudgy_base_01.glb`
- Studio job `5a0db910-520c-406d-987f-b3914d7ab296` (pack id `pudgy_mon_shared_base_01`, remapped)

### `char_pudgy_base_02` — Vivid Cartoon
- Same contract as base_01 (compare in Esc Nest menu → **Characters**)
- GLB: `assets/models/char_pudgy_base_02/char_pudgy_base_02.glb`
- Studio job `c00ebe10-82b0-4f59-8f67-477d3852e0d4` (pack id `pudgy_mon_body_shared_base_01`, remapped)

Default crew id: [`data/player_defaults.json`](../data/player_defaults.json) (user pick saved under `%LOCALAPPDATA%/…/player_defaults.json`). Roster: [`data/characters/roster.json`](../data/characters/roster.json). If the GLB is missing, runtime uses a **procedural Pudgy stub**.

## Pudgy Character Contract

All playable Pudgys (base + species skins) must obey this contract so one animation set and one accessory set can drive every variant.

| Rule | Value |
|------|--------|
| Base asset id | `char_pudgy_base_01` |
| Species id pattern | `char_pudgy_<biome>_01` or descriptive `*_pudgymon_01` |
| Playable height | ~1.2 m |
| Pivot | Floor center, +Y up, character faces **−Z** (Bevy forward) |
| Studio pose | Neutral **A-pose**, arms slightly out, feet planted — not a swim/run pose |
| Registry scale | Prefer `uniform_scale` `1.0` after polish (baked ~1.2 m height). Do **not** put raw Studio `target_height_m` straight into spawn scale |
| Required nodes (retarget target) | `Root`, `Hips`, `Spine`, `Head`, `L_Arm`, `R_Arm`, `L_Leg`, `R_Leg` |
| Accessory sockets | See table below — leave wear volumes clear (do not bake accessories into the body) |
| Shared clip names | `idle`, `walk`, `run`, `jump`, `emote_wave` |

**Tripo note:** exports often use a soft hierarchy. The node list above is the **retarget target** for future clips. Variants that do not match get root-transform motion only until retargeted.

**Import rule:** register species with the same `uniform_scale` as the base unless you measure a different mesh height.

## Accessory slots

Every Pudgy shares these sockets. Accessories are **separate Studio GLBs** (`acc_*`) parented at the wear origin — never part of the body mesh.

| Slot | Socket name | Wear origin | Id pattern | Runtime field |
|------|-------------|-------------|------------|---------------|
| Hat | `Socket_Hat` | Crown / top of head | `acc_hat_*_01` | `PlayerVisualSpec.accessories.hat` |
| Necklace | `Socket_Necklace` | Front of neck band | `acc_necklace_*_01` | `…necklace` |
| Shoes | `Socket_Shoes` | Floor between both feet (pair mesh) | `acc_shoes_*_01` | `…shoes` |
| Back | `Socket_Back` | Upper back / spine | `acc_back_*_01` | `…back` |
| Face | `Socket_Face` | Bridge of snout / eyes | `acc_face_*_01` | `…face` |
| Hands | `Socket_Hands` | Midpoint between hands (pair mesh) | `acc_hands_*_01` | `…hands` |

**Studio rules for accessories**

1. Single isolated mesh — no head, no body.
2. Pivot at the wear origin for that slot (shoes: floor pair pivot).
3. Sized for the 1.2 m base; readable from third-person.
4. Soft candy / rubber materials; family-friendly.
5. Full prompt pack: [STUDIO_PROMPTS.md](STUDIO_PROMPTS.md).

Until GLBs exist, `accessories.*` may be empty and `hat_slot` remains a legacy tint/roster index (0–7).

## Species skins

| Id | Label | Notes |
|----|-------|--------|
| `oceanic_pudgymon_01` | Ocean PudgyMon | Wishlist (regen after base sign-off) |
| `char_pudgy_forest_01` | Forest PudgyMon | Wishlist |
| `char_pudgy_lava_01` | Lava PudgyMon | Wishlist |
| `char_pudgy_sky_01` | Sky PudgyMon | Wishlist |

Future biomes change silhouette details and palette only — **same limb lengths, torso proportions, and accessory sockets** as the base.

## Starter color skins (season catalog)

Palette swaps on top of the equipped model (cycle with **C** in The Nest). These are tints, not new meshes — accessories and species override mesh separately.

| Id | Label | Vibe |
|----|-------|------|
| `skin_starter` | Pudgy Sprout | Coral default |
| `skin_vibe` | Sunny Blob | Yellow party |
| `skin_racer` | Turbo Dumpling | Cyan speed |
| `skin_blaster` | Party Peep | Pink blaster |

## Nest showcase

Mannequins around The Nest preview each catalog tint. Unlock by season points, then claim on Boing (see [BOING_INTEGRATION.md](BOING_INTEGRATION.md)).

## Art pipeline

1. Shared base `char_pudgy_base_01` ← **current crew default** (clear accessory sockets)
2. Species variants via Studio using the species-variant prompt ([STUDIO_PROMPTS.md](STUDIO_PROMPTS.md))
3. Accessory batches per slot (`acc_hat_*`, `acc_necklace_*`, `acc_shoes_*`, …)
4. Shared clips (`idle` / `walk` / `run` / …) authored on the base, retargeted to matching species
5. Nest + stage props from the Party Saga wishlist ([ASSET_WISHLIST.md](ASSET_WISHLIST.md))

## Runtime hook

```rust
PlayerVisualSpec {
    model_id: Some("char_pudgy_base_01".into()), // or a species asset_id
    hat_slot: 0, // legacy roster index; prefer accessories.hat
    accessories: AccessorySlots {
        hat: Some("acc_hat_party_crown_01".into()),
        necklace: Some("acc_necklace_shell_01".into()),
        shoes: Some("acc_shoes_racer_01".into()),
        back: None,
        face: None,
        hands: None,
    },
}
```

Default body id: `data/player_defaults.json`. Cosmetics may later override `model_id` to a species skin that still matches this contract, and fill accessory ids independently.
