# Immersive Studio prompt pack — PudgyMon: Party Saga

Copy-paste prompts for [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) / Tripo jobs.

**Important:** Studio does **not** cache prior prompts. Every job is independent. Each fenced block below is a **complete** prompt — paste it alone. Do not rely on a shared style block, a previous job, or a “prepend this” wrapper. **Hard limit: each prompt ≤ 1000 characters.**

After generation → import → place (see [STUDIO_ASSETS.md](STUDIO_ASSETS.md)). Stand-in map: [ASSET_WISHLIST.md](ASSET_WISHLIST.md). Character + accessory contract: [CHARACTERS.md](CHARACTERS.md).

**Theme lock:** cute chunky **Pudgy Monsters** in a party playground — The Nest + Race / Vibe Collect / Shooter. Not freight, vaults, or corporate comedy.

**Export settings (all jobs)**

| Setting | Value |
|---------|--------|
| Format | GLB with baked Tripo PBR |
| Pivot | Floor center (characters / props) · wear origin (accessories) |
| Facing | Character faces −Z (Bevy forward) when possible |
| Units | 1 unit ≈ 1 meter |
| Naming | Folder + file = `asset_id` / `asset_id.glb` |
| Characters | After polish: baked ~1.2 m height, `uniform_scale` `1.0`. Raw Tripo imports: run `scripts/polish_character_glb.py` |

**Art direction (characters):** soft **stylized cartoon 3D** — think Pokémon (recent 3D games), Kirby, Animal Crossing villagers, Fall Guys softness. Flat-to-soft painted color, big graphic shapes, friendly readability. **Not** clay, polymer clay, ceramic, glossy vinyl, injection-molded plastic shine, or photoreal toys.

**Optional negative prompt (if Studio supports a separate field):**

```
photorealistic, grimdark, horror, blood, realistic weapons, space freight, corporate office,
tiny unreadable labels, multiple objects, diorama, landscape, adult human proportions,
clay, polymer clay, ceramic, earthen texture, stone, mud, fingerprint texture,
glossy vinyl, shiny plastic, injection molded, clearcoat, specular hotspots,
subsurface wax, dirty, scratched, fuzzy fur, uncanny realism
```

---

## Priority 0 — Shared Pudgy base + species

All playable Pudgys share one figure. Each species job below is a full standalone prompt (proportions restated every time because jobs are not cached).

### `char_pudgy_base_01` · playable height **1.2** · `uniform_scale` **1.0** (after polish)

**Plugs into:** `data/player_defaults.json` / `PlayerVisualSpec.model_id`

```
Stylized cartoon 3D PudgyMon Party Saga SHARED BASE body. Soft Pokémon/Kirby mascot look:
painted matte candy color, big graphic shapes — NOT clay, vinyl, shiny plastic, or photoreal.
Coral-peach dumpling body, oversized round head, stubby equal limbs, huge simple friendly eyes,
tiny snout, soft even shading, no pores. Neutral A-pose: arms slightly out, feet flat.
Clear wear volumes: flat crown, bare neck, stubby feet/hands, clean back, open face — no baked accessories.
Floor pivot, faces camera-forward, single character, no weapons/text/plinth.
Idle A-pose only (~1.2 m), game-ready low-mid poly, family-friendly.
```

**Import + polish:**

```bash
python scripts/register_studio_asset.py char_pudgy_base_01 --height 1.2 --scale 1.0 --update
python scripts/polish_character_glb.py char_pudgy_base_01
python scripts/toon_material_pass.py char_pudgy_base_01
```

### `oceanic_pudgymon_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Stylized cartoon 3D PudgyMon Party Saga — Ocean species. Soft Pokémon/Kirby painted matte look —
NOT clay, vinyl, shiny plastic, or photoreal. Match shared base: ~1.2 m, stubby equal limbs,
round dumpling torso, oversized head, A-pose arms out feet flat, floor pivot, faces camera-forward.
Clear wear volumes (crown, neck, feet, back, face, hands) — no baked accessories.
Only biome differs: soft cartoon fins, gill freckles, teal/coral candy palette.
Single character, idle A-pose only, no weapons/text/plinth, family-friendly, low-mid poly.
```

### `char_pudgy_forest_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Stylized cartoon 3D PudgyMon Party Saga — Forest species. Soft Pokémon/Kirby painted matte look —
NOT clay, vinyl, shiny plastic, or photoreal. Match shared base: ~1.2 m, stubby equal limbs,
round dumpling torso, oversized head, A-pose arms out feet flat, floor pivot, faces camera-forward.
Clear wear volumes (crown, neck, feet, back, face, hands) — no baked accessories.
Only biome differs: leaf tuft ears, soft moss freckles, lime/olive candy palette.
Single character, idle A-pose only, no weapons/text/plinth, family-friendly, low-mid poly.
```

### `char_pudgy_lava_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Stylized cartoon 3D PudgyMon Party Saga — Lava species. Soft Pokémon/Kirby painted matte look —
NOT clay, vinyl, shiny plastic, or photoreal. Match shared base: ~1.2 m, stubby equal limbs,
round dumpling torso, oversized head, A-pose arms out feet flat, floor pivot, faces camera-forward.
Clear wear volumes (crown, neck, feet, back, face, hands) — no baked accessories.
Only biome differs: ember freckles, tiny cartoon glow belly, coral-orange/charcoal palette; no real fire.
Single character, idle A-pose only, no weapons/text/plinth, family-friendly, low-mid poly.
```

### `char_pudgy_sky_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Stylized cartoon 3D PudgyMon Party Saga — Sky species. Soft Pokémon/Kirby painted matte look —
NOT clay, vinyl, shiny plastic, or photoreal. Match shared base: ~1.2 m, stubby equal limbs,
round dumpling torso, oversized head, A-pose arms out feet flat, floor pivot, faces camera-forward.
Clear wear volumes (crown, neck, feet, back, face, hands) — no baked accessories.
Only biome differs: puffball cheeks, soft cloud tufts, sky-blue/cream palette.
Single character, idle A-pose only, no weapons/text/plinth, family-friendly, low-mid poly.
```

**Species import:**

```bash
python scripts/register_studio_asset.py <asset_id> --height 1.2 --scale 1.0 --update \
  --notes "Species skin on char_pudgy_base_01 contract"
python scripts/toon_material_pass.py <asset_id>
```

---

## Priority 1 — Accessories (each job independent)

Accessories are **standalone wearable props**. Tripo often ignores weak “no character” wording and returns a dressed mascot instead — so every prompt below leads with a hard **OBJECT ONLY** lock and never uses a creature/body as the subject.

Parent under sockets on `char_pudgy_base_01` (see [CHARACTERS.md](CHARACTERS.md)). Every prompt is complete on its own. **≤ 1000 characters.**

| Slot | Socket | Pivot | Id pattern |
|------|--------|-------|------------|
| Hat | `Socket_Hat` | Crown wear origin | `acc_hat_*_01` |
| Necklace | `Socket_Necklace` | Neck center | `acc_necklace_*_01` |
| Shoes | `Socket_Shoes` | Floor between both feet (pair) | `acc_shoes_*_01` |
| Back | `Socket_Back` | Upper back | `acc_back_*_01` |
| Face | `Socket_Face` | Bridge of snout | `acc_face_*_01` |
| Hands | `Socket_Hands` | Midpoint between hands (pair) | `acc_hands_*_01` |

**Accessory negative prompt (paste if Studio has a separate negative field):**

```
character, creature, mascot, monster, animal, person, human, avatar, mannequin, dummy head,
bust, torso, body, face, eyes, mouth, arms, legs, hands, feet, wearer, model wearing item,
full figure, chibi character, cartoon creature, pudgy monster body
```

### Hats

#### `acc_hat_party_crown_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: soft candy party crown with round gem studs, coral and gold, short stubby points
Pivot at crown wear origin. About 0.28 m tall.
```

#### `acc_hat_racer_cap_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: tiny soft racing cap with short bill and cyan-white speed stripe
Pivot at crown wear origin. About 0.18 m tall.
```

#### `acc_hat_vibe_mushroom_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: mini mushroom-cap hat with teal freckles and thick stubby stem rim
Pivot at crown wear origin. About 0.30 m tall.
```

#### `acc_hat_blaster_beanie_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: soft beanie with star pom-pom, pink and magenta candy colors, floppy silhouette
Pivot at crown wear origin. About 0.22 m tall.
```

#### `acc_hat_propeller_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: silly propeller beanie with stubby candy propeller on top, yellow and sky blue
Pivot at crown wear origin. About 0.26 m tall.
```

#### `acc_hat_flower_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: big plush daisy flower hat with soft petals, cream and lime candy colors
Pivot at crown wear origin. About 0.32 m tall.
```

#### `acc_hat_chef_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: chunky toy chef hat, white with coral trim, soft rounded puff top
Pivot at crown wear origin. About 0.30 m tall.
```

#### `acc_hat_sleep_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: floppy nightcap with soft star tip, indigo and cream candy colors
Pivot at crown wear origin. About 0.28 m tall.
```

### Necklaces

#### `acc_necklace_shell_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: soft shell pendant on a thick candy chain, teal and cream
Pivot at neck wear origin. About 0.20 m tall.
```

#### `acc_necklace_medal_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: oversized round race medal on soft cyan ribbon, gold face blank (no readable text)
Pivot at neck wear origin. About 0.22 m tall.
```

#### `acc_necklace_beads_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: chunky rainbow bead collar, thick soft party beads
Pivot at neck wear origin. About 0.16 m tall.
```

#### `acc_necklace_bell_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: soft jingle-bell charm on a short candy chain, yellow and coral
Pivot at neck wear origin. About 0.18 m tall.
```

### Shoes (connected pair per job)

#### `acc_shoes_racer_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: connected left+right stubby racing sneakers in one mesh, cyan-white speed stripe, soft chunky soles
Floor pivot between both shoes. About 0.14 m tall.
```

#### `acc_shoes_party_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: connected left+right soft party loafers in one mesh, coral-gold with star accents
Floor pivot between both shoes. About 0.12 m tall.
```

#### `acc_shoes_boots_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: connected left+right chunky toy rain boots in one mesh, yellow and teal, soft rounded toes
Floor pivot between both shoes. About 0.16 m tall.
```

#### `acc_shoes_slippers_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: connected left+right plush cloud slippers in one mesh, cream and sky blue
Floor pivot between both shoes. About 0.12 m tall.
```

### Back / face / hands

#### `acc_back_cape_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: short soft hero cape, coral lining and cream outer, stubby friendly shape
Pivot at upper-back wear origin. About 0.45 m tall.
```

#### `acc_back_wings_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: pair of stubby candy angel wings as one mesh, cream and pink, soft rounded feathers
Pivot at upper-back wear origin. About 0.40 m tall.
```

#### `acc_back_pack_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: round vibe-orb backpack with soft teal glow shell, stubby straps at wear origin
Pivot at upper-back wear origin. About 0.35 m tall.
```

#### `acc_face_shades_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: oversized toy sunglasses, black lenses and gold frame, chunky cartoon look
Pivot at snout/eye wear origin. About 0.12 m wide.
```

#### `acc_face_goggles_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: soft racer goggles with cyan candy lenses and strap, chunky friendly silhouette
Pivot at snout/eye wear origin. About 0.14 m wide.
```

#### `acc_face_mask_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: friendly party half-mask with pink sparkles, cute not scary
Pivot at snout/eye wear origin. About 0.16 m wide.
```

#### `acc_hands_mittens_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: connected left+right stubby star mittens in one mesh, coral with soft star accents
Pivot at midpoint between both mittens. About 0.12 m tall.
```

#### `acc_hands_gloves_01`

```
OBJECT ONLY — single isolated wearable prop on empty background.
NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar.
NO one wearing it. Product turntable shot of the item alone.
Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges,
not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text.
Item: connected left+right soft racing gloves in one mesh, cyan with stripe accents, stubby chunky fingers
Pivot at midpoint between both gloves. About 0.12 m tall.
```

---

## Priority 2 — The Nest

### `env_nest_egg_01` · target height **2.0**

**Plugs into:** Nest centerpiece

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A giant decorative party egg sculpture for The Nest social hub:
soft speckled shell, warm pastel orange and cream, rounded cartoon prop about 2 meters tall,
no cracks with creatures emerging.
```

### `env_nest_bench_01` · target height **0.6**

**Plugs into:** Nest seating ring

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A cute chunky outdoor bench for a monster party plaza:
soft rounded seat and back, candy coral and cream cartoon candy, short stubby legs,
about 0.6 meters tall, seats about two small chunky monsters.
```

### `prop_vibe_mushroom_01` · target height **1.8**

**Plugs into:** Nest flora décor

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
An oversized cartoon mushroom with a glowing cap for The Nest party playground:
thick stem, wide soft cap in coral or teal, slightly emissive cartoon candy look, about 1.8 meters tall.
```

### `env_pad_race_01` · target width **~2.5**

**Plugs into:** Nest Race mode pad

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the Race mini-game: flat soft disc with raised candy rim,
cyan speed-stripe pattern, subtle emissive glow, very thin, about 2.5 meters wide.
```

### `env_pad_vibe_01` · target width **~2.5**

**Plugs into:** Nest Vibe Collect mode pad

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the Vibe Collect mini-game: flat soft disc with raised candy rim,
yellow and orange glow rings, subtle emissive pattern, very thin, about 2.5 meters wide.
```

### `env_pad_shooter_01` · target width **~2.5**

**Plugs into:** Nest Shooter mode pad

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the Shooter mini-game: flat soft disc with raised candy rim,
pink star-burst pattern, subtle emissive glow, very thin, about 2.5 meters wide.
```

### `env_pad_party_01` · target width **~2.5**

**Plugs into:** Nest full Party Saga mode pad

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the full Party Saga circuit: flat soft disc with raised candy rim,
rainbow candy swirl pattern, subtle emissive glow, very thin, about 2.5 meters wide.
```

---

## Priority 3 — Stage props

### Race

#### `prop_race_checkpoint_01` · target height **2.0**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A soft freestanding arch checkpoint gate for a monster race course:
cyan candy stripes, rounded cartoon candy posts and arch, about 2 meters tall, open walk-through center.
```

#### `prop_race_cone_01` · target height **0.7**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A chunky candy traffic cone for a race course: coral and white stripes, soft rounded tip,
about 0.7 meters tall, cartoon candy look.
```

#### `prop_race_banner_01` · target height **1.5**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A soft finish-line banner on two stubby posts for a monster race:
cyan and cream candy colors, blank banner face (no readable letters), about 1.5 meters tall.
```

#### `env_race_ramp_01` · target height **1.2**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A short rounded toy ramp for a monster race course: teal deck with yellow candy edge,
soft bevels, about 1.2 meters tall at the high end, freestanding.
```

### Vibe Collect

#### `prop_vibe_orb_01` · target height **0.5**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A candy vibe collectible orb with a soft yellow glow, round cartoon candy shell,
optional tiny floor stand so it stays upright, about 0.5 meters tall, looks floaty but is grounded.
```

#### `prop_vibe_flower_01` · target height **1.0**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
An oversized collectible flower prop with soft petals, lime and pink candy colors,
thick stubby stem, about 1.0 meters tall, cartoon candy look.
```

#### `prop_vibe_crystal_01` · target height **0.8**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A rounded toy crystal cluster with teal emissive tips, soft candy facets (not sharp glass),
about 0.8 meters tall, friendly silhouette.
```

### Shooter

#### `prop_blaster_toy_01` · target height **0.4**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A chunky foam toy blaster decoration only — clearly a soft party toy, not a realistic weapon —
pink and yellow cartoon candy, rounded nozzle, about 0.4 meters long/tall, family-friendly.
```

#### `prop_target_star_01` · target height **1.0**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A soft star-shaped pop target on a stubby stand for a party shooter arena:
cream and coral candy colors, about 1.0 meters tall, cartoon candy look.
```

#### `prop_cover_block_01` · target height **1.2**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A rounded soft cover block / crate for a party shooter arena: teal cartoon candy,
chunky bevels, about 1.2 meters tall, one solid piece, friendly silhouette.
```

#### `vfx_ko_burst_marker_01` · target height **0.05** · width **~2.0**

```
Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials (not clay, not glossy vinyl),
exaggerated silhouettes, soft even shading, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A flat soft KO burst decal disc for a party shooter floor: pink star burst pattern,
very thin, about 2 meters wide, looks like a glowing candy sticker on the ground.
```

---

## Suggested Studio job order

Each row is a separate uncached job — paste that asset’s full prompt only.

1. `char_pudgy_base_01` (if regenerating)
2. Species: `oceanic_pudgymon_01`, `char_pudgy_forest_01`, `char_pudgy_lava_01`, `char_pudgy_sky_01`
3. Hats → necklaces → shoes → back / face / hands (one prompt each)
4. Nest: egg, bench, mushroom, mode pads
5. Race props → Vibe props → Shooter props

---

## After each pack

```bash
python scripts/import_immersive_studio_pack.py path/to/pack.zip
python scripts/validate_studio_assets.py
cargo run -- local
```

If scale looks wrong: set `"uniform_scale"` in `studio_registry.json` or `"scale"` on the room marker — no re-export needed.
