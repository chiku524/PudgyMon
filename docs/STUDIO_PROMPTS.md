# Immersive Studio prompt pack — PudgyMon: Party Saga

Copy-paste prompts for [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) / Tripo jobs.

**Important:** Studio does **not** cache prior prompts. Every job is independent. Each fenced block below is a **complete** prompt — paste it alone. Do not rely on a shared style block, a previous job, or a “prepend this” wrapper.

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

**Art direction (characters):** smooth **vinyl designer-toy** look — think Blankos / Pokémon figures. Glossy injection-molded plastic, clean color blocks, big simple eyes. **Not** clay, ceramic, polymer clay, matte stone, or fuzzy plush.

**Optional negative prompt (if Studio supports a separate field):**

```
photorealistic, grimdark, horror, blood, realistic weapons, space freight, corporate office,
tiny unreadable labels, multiple objects, diorama, landscape, adult human proportions,
clay, polymer clay, ceramic, matte earthen texture, stone, fuzzy fur, dirty, scratched plastic
```

---

## Priority 0 — Shared Pudgy base + species

All playable Pudgys share one figure. Each species job below is a full standalone prompt (proportions restated every time because jobs are not cached).

### `char_pudgy_base_01` · playable height **1.2** · `uniform_scale` **1.0** (after polish)

**Plugs into:** `data/player_defaults.json` / `PlayerVisualSpec.model_id`

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — the SHARED BASE body for all Pudgy Monsters.
Smooth glossy vinyl designer-toy look like Blankos or a Pokémon figure — injection-molded plastic,
clean color blocks, soft rounded edges, subtle specular shine, NOT clay, NOT ceramic, NOT matte polymer clay, NOT plush.
Bright readable candy colors, exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Cute chunky monster, round dumpling body, oversized round head, stubby limbs of equal length,
big simple friendly eyes, tiny snout, coral-peach vinyl base color, smooth painted surface.
Neutral A-pose only: arms slightly away from sides, feet planted flat, standing upright.
Leave clear wear volumes: flat crown for hats, bare neck band for necklaces, simple stubby feet for shoes,
clean back for capes/wings, open face for glasses/masks, stubby hands for mittens.
Floor-pivoted at ground center, faces camera-forward, single character only,
no weapons, no text, no accessories baked onto the mesh, no base/plinth.
Do NOT pose swimming, running, or mid-action — idle A-pose only so animations can drive motion.
Game-ready low-to-mid poly, about 1.2 meters tall playable.
```

**Import + polish:**

```bash
python scripts/register_studio_asset.py char_pudgy_base_01 --height 1.2 --scale 1.0 --update
python scripts/polish_character_glb.py char_pudgy_base_01
```

### `oceanic_pudgymon_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — Ocean PudgyMon species variant.
Smooth glossy vinyl designer-toy look like Blankos or a Pokémon figure — injection-molded plastic,
clean color blocks, subtle specular shine, NOT clay, NOT ceramic, NOT matte polymer clay, NOT plush.
Bright readable candy colors, soft rounded edges, exaggerated silhouettes, clean PBR,
no gore, no realistic dirt, no photorealism.
MUST match the shared Pudgy base figure: same overall height (~1.2 m), same stubby limb lengths,
same torso roundness, same head-to-body ratio, same neutral A-pose (arms slightly out, feet planted),
floor-pivoted at ground center, faces camera-forward.
Same accessory wear volumes (flat crown, bare neck band, stubby feet, clean back, open face, stubby hands)
— do not bake hats, jewelry, shoes, or other accessories onto the mesh.
Only biome details differ: soft fins and gill freckles, teal and coral ocean candy palette.
Single character only, no weapons, no text, no base/plinth, family-friendly.
Idle A-pose only — not swimming or mid-action. Game-ready low-to-mid poly.
```

### `char_pudgy_forest_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — Forest PudgyMon species variant.
Smooth glossy vinyl designer-toy look like Blankos or a Pokémon figure — injection-molded plastic,
clean color blocks, subtle specular shine, NOT clay, NOT ceramic, NOT matte polymer clay, NOT plush.
Bright readable candy colors, soft rounded edges, exaggerated silhouettes, clean PBR,
no gore, no realistic dirt, no photorealism.
MUST match the shared Pudgy base figure: same overall height (~1.2 m), same stubby limb lengths,
same torso roundness, same head-to-body ratio, same neutral A-pose (arms slightly out, feet planted),
floor-pivoted at ground center, faces camera-forward.
Same accessory wear volumes (flat crown, bare neck band, stubby feet, clean back, open face, stubby hands)
— do not bake hats, jewelry, shoes, or other accessories onto the mesh.
Only biome details differ: leaf tuft ears and moss freckles, lime and olive forest party palette.
Single character only, no weapons, no text, no base/plinth, family-friendly.
Idle A-pose only — not running or mid-action. Game-ready low-to-mid poly.
```

### `char_pudgy_lava_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — Lava PudgyMon species variant.
Smooth glossy vinyl designer-toy look like Blankos or a Pokémon figure — injection-molded plastic,
clean color blocks, subtle specular shine, NOT clay, NOT ceramic, NOT matte polymer clay, NOT plush.
Bright readable candy colors, soft rounded edges, exaggerated silhouettes, clean PBR,
no gore, no realistic dirt, no photorealism.
MUST match the shared Pudgy base figure: same overall height (~1.2 m), same stubby limb lengths,
same torso roundness, same head-to-body ratio, same neutral A-pose (arms slightly out, feet planted),
floor-pivoted at ground center, faces camera-forward.
Same accessory wear volumes (flat crown, bare neck band, stubby feet, clean back, open face, stubby hands)
— do not bake hats, jewelry, shoes, or other accessories onto the mesh.
Only biome details differ: ember freckles and a tiny soft magma belly glow, coral orange and charcoal palette.
Single character only, no weapons, no text, no base/plinth, family-friendly, no real fire or burns.
Idle A-pose only — not attacking or mid-action. Game-ready low-to-mid poly.
```

### `char_pudgy_sky_01` · same scale as base

**Plugs into:** species skin / `PlayerVisualSpec.model_id`

```
Cartoon stylized 3D game character for PudgyMon: Party Saga — Sky PudgyMon species variant.
Smooth glossy vinyl designer-toy look like Blankos or a Pokémon figure — injection-molded plastic,
clean color blocks, subtle specular shine, NOT clay, NOT ceramic, NOT matte polymer clay, NOT plush.
Bright readable candy colors, soft rounded edges, exaggerated silhouettes, clean PBR,
no gore, no realistic dirt, no photorealism.
MUST match the shared Pudgy base figure: same overall height (~1.2 m), same stubby limb lengths,
same torso roundness, same head-to-body ratio, same neutral A-pose (arms slightly out, feet planted),
floor-pivoted at ground center, faces camera-forward.
Same accessory wear volumes (flat crown, bare neck band, stubby feet, clean back, open face, stubby hands)
— do not bake hats, jewelry, shoes, or other accessories onto the mesh.
Only biome details differ: puffball cheeks and soft cloud tufts, sky blue and cream palette.
Single character only, no weapons, no text, no base/plinth, family-friendly.
Idle A-pose only — not flying or mid-action. Game-ready low-to-mid poly.
```

**Species import:**

```bash
python scripts/register_studio_asset.py <asset_id> --height 1.2 --scale 0.27 --update \
  --notes "Species skin on char_pudgy_base_01 contract"
```

---

## Priority 1 — Accessories (each job independent)

Accessories are separate GLBs. Parent under sockets on `char_pudgy_base_01` (see [CHARACTERS.md](CHARACTERS.md)). Every prompt below is complete on its own.

| Slot | Socket | Pivot | Id pattern |
|------|--------|-------|------------|
| Hat | `Socket_Hat` | Crown wear origin | `acc_hat_*_01` |
| Necklace | `Socket_Necklace` | Neck center | `acc_necklace_*_01` |
| Shoes | `Socket_Shoes` | Floor between both feet (pair) | `acc_shoes_*_01` |
| Back | `Socket_Back` | Upper back | `acc_back_*_01` |
| Face | `Socket_Face` | Bridge of snout | `acc_face_*_01` |
| Hands | `Socket_Hands` | Midpoint between hands (pair) | `acc_hands_*_01` |

### Hats

#### `acc_hat_party_crown_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A soft candy party crown with round gem studs, coral and gold toy plastic,
short stubby points, friendly party silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_racer_cap_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A tiny soft racing cap with a short bill and a speed stripe, cyan and white candy plastic,
chunky friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_vibe_mushroom_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A mini mushroom-cap hat with soft teal glow freckles on the cap, thick stubby stem rim,
toy plastic look, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_blaster_beanie_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A soft beanie with a star pom-pom on top, pink and magenta candy colors,
floppy friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_propeller_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A silly soft propeller beanie with a stubby candy propeller on top, yellow and sky blue,
toy plastic look, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_flower_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A big plush daisy flower hat with soft petals, cream and lime candy colors,
chunky friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_chef_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A chunky toy chef hat, white with coral trim, soft rounded puff top,
friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hat_sleep_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hat only — no head, no body, no full character, no base/plinth, no text.
Centered at crown wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A floppy nightcap with a soft star tip, indigo and cream candy colors,
cozy plush look, readable from third-person camera.
Game-ready low poly.
```

### Necklaces

#### `acc_necklace_shell_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated necklace only — no head, no body, no full character, no base/plinth, no text.
Centered at neck wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A soft shell pendant on a thick candy chain, teal and cream toy plastic,
chunky friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_necklace_medal_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated necklace only — no head, no body, no full character, no base/plinth, no text.
Centered at neck wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
An oversized round race medal on a soft ribbon, gold medal with cyan ribbon,
blank face (no readable text), chunky toy look, readable from third-person camera.
Game-ready low poly.
```

#### `acc_necklace_beads_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated necklace only — no head, no body, no full character, no base/plinth, no text.
Centered at neck wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A chunky rainbow bead collar, bright party candy colors, thick soft beads,
friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

#### `acc_necklace_bell_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated necklace only — no head, no body, no full character, no base/plinth, no text.
Centered at neck wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A soft jingle-bell charm on a short candy chain, yellow and coral toy plastic,
chunky friendly silhouette, readable from third-person camera.
Game-ready low poly.
```

### Shoes (connected pair per job)

#### `acc_shoes_racer_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated shoes accessory only — no legs, no body, no full character, no base/plinth, no text.
A connected pair of left and right stubby racing sneakers in one mesh,
floor-pivoted between both feet, sized for a 1.2 m chunky dumpling Pudgy monster.
Cyan and white candy plastic with a speed stripe, soft chunky soles,
readable from third-person camera. Game-ready low poly.
```

#### `acc_shoes_party_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated shoes accessory only — no legs, no body, no full character, no base/plinth, no text.
A connected pair of left and right soft party loafers in one mesh,
floor-pivoted between both feet, sized for a 1.2 m chunky dumpling Pudgy monster.
Coral and gold candy plastic with star accents, stubby chunky shape,
readable from third-person camera. Game-ready low poly.
```

#### `acc_shoes_boots_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated shoes accessory only — no legs, no body, no full character, no base/plinth, no text.
A connected pair of left and right chunky toy rain boots in one mesh,
floor-pivoted between both feet, sized for a 1.2 m chunky dumpling Pudgy monster.
Yellow and teal candy plastic, soft rounded toes, stubby friendly silhouette,
readable from third-person camera. Game-ready low poly.
```

#### `acc_shoes_slippers_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated shoes accessory only — no legs, no body, no full character, no base/plinth, no text.
A connected pair of left and right plush cloud slippers in one mesh,
floor-pivoted between both feet, sized for a 1.2 m chunky dumpling Pudgy monster.
Cream and sky blue soft plush look, puffy cloud silhouette,
readable from third-person camera. Game-ready low poly.
```

### Back / face / hands

#### `acc_back_cape_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated back accessory only — no body, no full character, no base/plinth, no text.
Centered at upper-back wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A short soft hero cape with coral lining and cream outer fabric, stubby friendly shape,
readable from third-person camera. Game-ready low poly.
```

#### `acc_back_wings_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated back accessory only — no body, no full character, no base/plinth, no text.
Centered at upper-back wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A pair of stubby candy angel wings as one mesh, cream and pink toy plastic,
soft rounded feathers, readable from third-person camera. Game-ready low poly.
```

#### `acc_back_pack_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated back accessory only — no body, no full character, no base/plinth, no text.
Centered at upper-back wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A round vibe-orb backpack with soft teal glow, candy plastic shell, stubby straps implied at wear origin,
readable from third-person camera. Game-ready low poly.
```

#### `acc_face_shades_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated face accessory only — no head, no body, no full character, no base/plinth, no text.
Centered at snout/eye wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
Oversized toy sunglasses with black lenses and gold frame, chunky cartoon look,
readable from third-person camera. Game-ready low poly.
```

#### `acc_face_goggles_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated face accessory only — no head, no body, no full character, no base/plinth, no text.
Centered at snout/eye wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
Soft racer goggles resting as if on a forehead ridge, cyan candy plastic lenses and strap,
chunky friendly silhouette, readable from third-person camera. Game-ready low poly.
```

#### `acc_face_mask_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated face accessory only — no head, no body, no full character, no base/plinth, no text.
Centered at snout/eye wear origin, sized for a 1.2 m chunky dumpling Pudgy monster.
A friendly party half-mask with pink sparkles, soft candy plastic, cute not scary,
readable from third-person camera. Game-ready low poly.
```

#### `acc_hands_mittens_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hands accessory only — no arms, no body, no full character, no base/plinth, no text.
A connected pair of left and right stubby star mittens in one mesh,
centered at the midpoint between both hands, sized for a 1.2 m chunky dumpling Pudgy monster.
Coral candy colors with soft star accents, readable from third-person camera.
Game-ready low poly.
```

#### `acc_hands_gloves_01`

```
Cartoon stylized 3D game accessory for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated hands accessory only — no arms, no body, no full character, no base/plinth, no text.
A connected pair of left and right soft racing gloves in one mesh,
centered at the midpoint between both hands, sized for a 1.2 m chunky dumpling Pudgy monster.
Cyan candy plastic with stripe accents, stubby chunky fingers, readable from third-person camera.
Game-ready low poly.
```

---

## Priority 2 — The Nest

### `env_nest_egg_01` · target height **2.0**

**Plugs into:** Nest centerpiece

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A giant decorative party egg sculpture for The Nest social hub:
soft speckled shell, warm pastel orange and cream, rounded cartoon prop about 2 meters tall,
no cracks with creatures emerging.
```

### `env_nest_bench_01` · target height **0.6**

**Plugs into:** Nest seating ring

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A cute chunky outdoor bench for a monster party plaza:
soft rounded seat and back, candy coral and cream toy plastic, short stubby legs,
about 0.6 meters tall, seats about two small chunky monsters.
```

### `prop_vibe_mushroom_01` · target height **1.8**

**Plugs into:** Nest flora décor

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
An oversized cartoon mushroom with a glowing cap for The Nest party playground:
thick stem, wide soft cap in coral or teal, slightly emissive toy plastic look, about 1.8 meters tall.
```

### `env_pad_race_01` · target width **~2.5**

**Plugs into:** Nest Race mode pad

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the Race mini-game: flat soft disc with raised candy rim,
cyan speed-stripe pattern, subtle emissive glow, very thin, about 2.5 meters wide.
```

### `env_pad_vibe_01` · target width **~2.5**

**Plugs into:** Nest Vibe Collect mode pad

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the Vibe Collect mini-game: flat soft disc with raised candy rim,
yellow and orange glow rings, subtle emissive pattern, very thin, about 2.5 meters wide.
```

### `env_pad_shooter_01` · target width **~2.5**

**Plugs into:** Nest Shooter mode pad

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters, no readable glyphs.
A circular floor mode pad for the Shooter mini-game: flat soft disc with raised candy rim,
pink star-burst pattern, subtle emissive glow, very thin, about 2.5 meters wide.
```

### `env_pad_party_01` · target width **~2.5**

**Plugs into:** Nest full Party Saga mode pad

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
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
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A soft freestanding arch checkpoint gate for a monster race course:
cyan candy stripes, rounded toy plastic posts and arch, about 2 meters tall, open walk-through center.
```

#### `prop_race_cone_01` · target height **0.7**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A chunky candy traffic cone for a race course: coral and white stripes, soft rounded tip,
about 0.7 meters tall, toy plastic look.
```

#### `prop_race_banner_01` · target height **1.5**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A soft finish-line banner on two stubby posts for a monster race:
cyan and cream candy colors, blank banner face (no readable letters), about 1.5 meters tall.
```

#### `env_race_ramp_01` · target height **1.2**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A short rounded toy ramp for a monster race course: teal deck with yellow candy edge,
soft bevels, about 1.2 meters tall at the high end, freestanding.
```

### Vibe Collect

#### `prop_vibe_orb_01` · target height **0.5**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A candy vibe collectible orb with a soft yellow glow, round toy plastic shell,
optional tiny floor stand so it stays upright, about 0.5 meters tall, looks floaty but is grounded.
```

#### `prop_vibe_flower_01` · target height **1.0**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
An oversized collectible flower prop with soft petals, lime and pink candy colors,
thick stubby stem, about 1.0 meters tall, toy plastic look.
```

#### `prop_vibe_crystal_01` · target height **0.8**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A rounded toy crystal cluster with teal emissive tips, soft candy facets (not sharp glass),
about 0.8 meters tall, friendly silhouette.
```

### Shooter

#### `prop_blaster_toy_01` · target height **0.4**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A chunky foam toy blaster decoration only — clearly a soft party toy, not a realistic weapon —
pink and yellow candy plastic, rounded nozzle, about 0.4 meters long/tall, family-friendly.
```

#### `prop_target_star_01` · target height **1.0**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A soft star-shaped pop target on a stubby stand for a party shooter arena:
cream and coral candy colors, about 1.0 meters tall, toy plastic look.
```

#### `prop_cover_block_01` · target height **1.2**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
Single isolated object, centered, floor-pivoted at ground center, game-ready low-to-mid poly,
no base/plinth, no floating text, no characters.
A rounded soft cover block / crate for a party shooter arena: teal candy plastic,
chunky bevels, about 1.2 meters tall, one solid piece, friendly silhouette.
```

#### `vfx_ko_burst_marker_01` · target height **0.05** · width **~2.0**

```
Cartoon stylized 3D game prop for PudgyMon: Party Saga — cute chunky monster party world.
Bright readable candy colors, soft rounded edges, slightly rubbery plastic / plush toy materials,
exaggerated silhouettes, clean PBR, no gore, no realistic dirt, no photorealism.
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
