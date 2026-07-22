# Immersive Studio prompt pack — PudgyMon: Party Saga

Copy-paste prompts for [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) / Tripo jobs. Each entry includes the **`asset_id`**, target height, where it plugs into PudgyMon, and a ready prompt.

After generation → import → place (see [STUDIO_ASSETS.md](STUDIO_ASSETS.md)). Stand-in map: [ASSET_WISHLIST.md](ASSET_WISHLIST.md). Character + accessory contract: [CHARACTERS.md](CHARACTERS.md).

**Theme lock:** cute chunky **Pudgy Monsters** in a party playground — The Nest social hub + Race / Vibe Collect / Shooter. Not freight, vaults, or corporate comedy.

---

## Global style (prepend to every prompt)

Use this block (or Studio’s style preset) on **every** job so the set matches:

```
Cartoon stylized 3D game asset for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted (origin at ground center) unless noted as an accessory,
game-ready low-to-mid poly, no base/plinth, no floating text UI, no people unless the job is a Pudgy.
```

**Negative / avoid (if Studio supports it):**

```
photorealistic, grimdark, horror, blood, weapons with realistic ammo, space freight, corporate office,
tiny unreadable labels, multiple objects, diorama, landscape, character holding prop, adult human proportions
```

**Export settings**

| Setting | Value |
|---------|--------|
| Format | GLB with baked Tripo PBR |
| Pivot | Floor center (characters / props) · wear origin (accessories) |
| Facing | Character faces −Z (Bevy forward) when possible |
| Units | 1 unit ≈ 1 meter |
| Naming | Folder + file = `asset_id` / `asset_id.glb` |
| Characters | Register with `uniform_scale` (do not use large Studio `target_height_m` as spawn scale) |

---

## Priority 0 — Shared Pudgy base + species

All playable Pudgys share one figure. Species change palette and silhouette details only. Accessories attach to fixed sockets on this base.

### `char_pudgy_base_01` · playable height **1.2** · `uniform_scale` **0.27**

**Plugs into:** `data/player_defaults.json` / `PlayerVisualSpec.model_id`  
**Contract:** [CHARACTERS.md — Pudgy Character Contract](CHARACTERS.md)

Canonical shared base. Future species and every accessory must match its proportions and sockets.

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — the SHARED BASE body.
Cute chunky monster, round soft dumpling body, oversized round head, stubby limbs of equal length,
big friendly eyes, tiny snout, rubbery plastic toy materials, coral-peach base color.
Neutral A-pose only: arms slightly away from sides, feet planted flat, standing upright.
Leave clear wear volumes: flat crown for hats, bare neck band for necklaces, simple stubby feet for shoes,
clean back for capes/wings, open face for glasses/masks, stubby hands for mittens.
Floor-pivoted at ground center, faces camera-forward, single character, no weapons, no text, no accessories baked on.
Do NOT pose swimming, running, or mid-action — idle A-pose only so animations can drive motion.
Clean PBR, exaggerated silhouette, game-ready low-to-mid poly, about 1.2 meters tall playable.
```

**Import:**

```bash
python scripts/register_studio_asset.py char_pudgy_base_01 --height 1.2 --scale 0.27 --update
```

### Pudgy species variant template · same scale as base

**Plugs into:** cosmetics / `PlayerVisualSpec.model_id` override  
**Id pattern:** `char_pudgy_<biome>_01` or `*_pudgymon_01` (example: `oceanic_pudgymon_01`)

Copy this block for every new species. Change only the biome details line; keep proportions and sockets locked.

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — SPECIES VARIANT of char_pudgy_base_01.
MUST match the shared base: same overall height, same stubby limb lengths, same torso roundness,
same head-to-body ratio, same A-pose (arms slightly out, feet planted), floor-pivoted ground center.
Same accessory wear volumes (crown, neck band, feet, back, face, hands) — do not bake hats/jewelry/shoes onto the mesh.
Only change biome silhouette details and palette — e.g. [FINS / GILLS / HORNS / FUR / SHELL / SPARKLES].
Theme: [BIOME VIBE — ocean / forest / lava / sky / candy / …]. Colors: [PALETTE].
Single character, no weapons, no text, family-friendly, clean PBR, game-ready low-to-mid poly.
Do NOT invent a unique locomotion pose; idle A-pose only for animation retarget compatibility.
```

**Starter species to generate**

| asset_id | Biome line |
|----------|------------|
| `oceanic_pudgymon_01` | Soft fins + gill freckles, teal/coral ocean candy palette |
| `char_pudgy_forest_01` | Leaf tuft ears + moss freckles, lime/olive forest party palette |
| `char_pudgy_lava_01` | Ember freckles + tiny magma belly glow, coral/orange/charcoal |
| `char_pudgy_sky_01` | Puffball cheeks + soft cloud tufts, sky blue/cream |

**Import rule:** same `uniform_scale` as the base (`0.27`) unless you measure a different mesh height:

```bash
python scripts/import_immersive_studio_pack.py path/to/pack
python scripts/register_studio_asset.py <asset_id> --height 1.2 --scale 0.27 --update \
  --notes "Species skin on char_pudgy_base_01 contract"
```

---

## Priority 1 — Accessory slots (shared sockets)

Accessories are **separate GLBs**, never baked into the body. Parent under the matching socket on `char_pudgy_base_01` (see [CHARACTERS.md](CHARACTERS.md)).

| Slot | Socket (target) | Pivot | Id pattern |
|------|-----------------|-------|------------|
| Hat | `Socket_Hat` (crown) | Wear origin at crown contact | `acc_hat_<name>_01` |
| Necklace | `Socket_Necklace` (neck band) | Wear origin at neck center | `acc_necklace_<name>_01` |
| Shoes | `Socket_Shoes` (pair, ground) | Floor between both feet | `acc_shoes_<name>_01` |
| Back | `Socket_Back` (upper back) | Wear origin at spine contact | `acc_back_<name>_01` |
| Face | `Socket_Face` (eyes/nose) | Wear origin at bridge of snout | `acc_face_<name>_01` |
| Hands | `Socket_Hands` (pair) | Midpoint between stubby hands | `acc_hands_<name>_01` |

**Shared accessory wrapper** (prepend global style, then):

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga.
Single isolated accessory only — no head, no body, no full character.
Centered at the wear origin for slot [HAT / NECKLACE / SHOES / BACK / FACE / HANDS],
sized for a 1.2 m chunky dumpling Pudgy (same as char_pudgy_base_01).
Soft rubber / candy plastic materials, exaggerated silhouette readable from third-person camera,
clean PBR, family-friendly, game-ready low poly.
```

### Batch A — Starter hats

| asset_id | Prompt focus |
|----------|--------------|
| `acc_hat_party_crown_01` | Soft candy party crown with round gems, coral/gold |
| `acc_hat_racer_cap_01` | Tiny bill racing cap with stripe, cyan/white |
| `acc_hat_vibe_mushroom_01` | Mini mushroom cap hat, teal glow freckles |
| `acc_hat_blaster_beanie_01` | Soft beanie with star pom, pink/magenta |
| `acc_hat_propeller_01` | Silly soft propeller beanie, yellow/sky |
| `acc_hat_flower_01` | Big plush daisy flower, cream/lime |
| `acc_hat_chef_01` | Chunky toy chef hat, white/coral trim |
| `acc_hat_sleep_01` | Floppy nightcap with star tip, indigo/cream |

**Example full prompt (`acc_hat_party_crown_01`):**

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic materials,
exaggerated silhouettes, clean PBR, no photorealism.
Single isolated hat only — no head, no body — centered at crown wear origin,
sized for a 1.2 m chunky dumpling monster, game-ready low poly.

A soft candy party crown with round gem studs, coral and gold toy plastic,
short stubby points, friendly party silhouette, readable from third-person camera.
```

### Batch B — Necklaces

| asset_id | Prompt focus |
|----------|--------------|
| `acc_necklace_shell_01` | Soft shell pendant on thick candy chain, teal/cream |
| `acc_necklace_medal_01` | Oversized round race medal, gold/cyan ribbon |
| `acc_necklace_beads_01` | Chunky rainbow bead collar, party candy colors |
| `acc_necklace_bell_01` | Soft jingle bell charm, yellow/coral |

### Batch C — Shoes

| asset_id | Prompt focus |
|----------|--------------|
| `acc_shoes_racer_01` | Pair of stubby racing sneakers with stripe, cyan/white |
| `acc_shoes_party_01` | Pair of soft party loafers with stars, coral/gold |
| `acc_shoes_boots_01` | Pair of chunky toy rain boots, yellow/teal |
| `acc_shoes_slippers_01` | Pair of plush cloud slippers, cream/sky |

**Shoes note:** Generate as a **connected pair** at floor pivot (left + right), not two separate jobs.

### Batch D — Back / face / hands

| asset_id | Slot | Prompt focus |
|----------|------|--------------|
| `acc_back_cape_01` | Back | Short soft hero cape, coral lining |
| `acc_back_wings_01` | Back | Stubby candy angel wings, cream/pink |
| `acc_back_pack_01` | Back | Round vibe-orb backpack, teal glow |
| `acc_face_shades_01` | Face | Oversized toy sunglasses, black/gold |
| `acc_face_goggles_01` | Face | Soft racer goggles on forehead, cyan |
| `acc_face_mask_01` | Face | Friendly party half-mask, pink sparkles |
| `acc_hands_mittens_01` | Hands | Pair of stubby star mittens, coral |
| `acc_hands_gloves_01` | Hands | Pair of soft racing gloves, cyan |

---

## Priority 2 — The Nest (social hub)

### `env_nest_egg_01` · target height **2.0**

**Plugs into:** Nest centerpiece (replace greybox egg)

```
Giant decorative party egg sculpture for The Nest social hub in PudgyMon: Party Saga.
Soft speckled shell, warm pastel orange and cream, rounded cartoon prop,
floor-pivoted, single object, no cracks with creatures emerging, no text, no characters.
```

### `env_nest_bench_01` · target height **0.6**

**Plugs into:** Nest seating ring

```
Cute chunky outdoor bench for a monster party plaza.
Soft rounded seat and back, candy coral and cream toy plastic, short stubby legs,
floor-pivoted, single object, seats about two Pudgys, no characters, no text.
```

### `prop_vibe_mushroom_01` · target height **1.8**

**Plugs into:** Nest flora décor

```
Oversized cartoon mushroom prop with glowing cap for The Nest party playground.
Thick stem, wide soft cap in coral or teal, slightly emissive toy plastic look,
floor-pivoted, single object, no characters.
```

### Mode pads (optional mesh upgrade)

| asset_id | Color vibe | For pad |
|----------|------------|---------|
| `env_pad_race_01` | Cyan speed stripes | Race |
| `env_pad_vibe_01` | Yellow/orange glow rings | Vibe Collect |
| `env_pad_shooter_01` | Pink star burst | Shooter |
| `env_pad_party_01` | Rainbow candy swirl | Full Party Saga |

```
Circular floor mode pad for PudgyMon: Party Saga Nest hub.
Flat soft disc with raised candy rim, [COLOR VIBE], subtle emissive pattern,
floor-pivoted, very thin, about 2.5 meters wide, no characters, no text glyphs (icon silhouette ok).
```

---

## Priority 3 — Stage props

### Race

| asset_id | height | Prompt seed |
|----------|--------|-------------|
| `prop_race_checkpoint_01` | 2.0 | Soft arch checkpoint gate with cyan stripes, freestanding |
| `prop_race_cone_01` | 0.7 | Chunky candy traffic cone, coral/white |
| `prop_race_banner_01` | 1.5 | Soft finish-line banner on two stubby posts, cyan/cream |
| `env_race_ramp_01` | 1.2 | Short rounded toy ramp, teal deck with yellow edge |

### Vibe Collect

| asset_id | height | Prompt seed |
|----------|--------|-------------|
| `prop_vibe_orb_01` | 0.5 | Floating-looking candy vibe orb (floor-pivoted stand ok), yellow glow |
| `prop_vibe_flower_01` | 1.0 | Oversized collectible flower prop, soft petals, lime/pink |
| `prop_vibe_crystal_01` | 0.8 | Rounded toy crystal cluster, teal emissive tips |

### Shooter

| asset_id | height | Prompt seed |
|----------|--------|-------------|
| `prop_blaster_toy_01` | 0.4 | Chunky foam toy blaster prop (decoration only), pink/yellow — no realistic gun |
| `prop_target_star_01` | 1.0 | Soft star-shaped pop target on a stubby stand, cream/coral |
| `prop_cover_block_01` | 1.2 | Rounded soft cover block / crate for arena cover, teal candy plastic |
| `vfx_ko_burst_marker_01` | 0.05 | Flat soft KO burst decal disc, pink stars, very thin |

Use **global style** + the one-line seed as the full prompt for each.

---

## Suggested Studio job order

1. `char_pudgy_base_01` (if regenerating) — lock sockets
2. Species pack (`oceanic_pudgymon_01`, forest / lava / sky)
3. Accessory Batch A hats (8) → B necklaces → C shoes → D back/face/hands
4. Nest: `env_nest_egg_01`, `env_nest_bench_01`, `prop_vibe_mushroom_01`
5. Mode pads (optional)
6. Race props → Vibe props → Shooter props

---

## After each pack

```bash
python scripts/import_immersive_studio_pack.py path/to/pack.zip
python scripts/validate_studio_assets.py
# Swap asset_id on Nest / stage markers, or equip accessories via PlayerVisualSpec
cargo run -- local
```

If scale looks wrong: set `"uniform_scale"` in `studio_registry.json` or `"scale"` on the room marker — no re-export needed.
