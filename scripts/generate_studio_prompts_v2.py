#!/usr/bin/env python3
"""Generate PudgyMon Party Saga Immersive Studio / Tripo prompt pack V2 (~1500 assets).

Outputs:
  data/studio_prompts_v2/catalog.json   — machine-readable full catalog
  data/studio_prompts_v2/by_category/   — one JSON per category
  docs/STUDIO_PROMPTS_V2.md             — index + workflow
  docs/studio_prompts_v2/*.md           — copy-paste prompt chapters

Usage:
  python scripts/generate_studio_prompts_v2.py
  python scripts/generate_studio_prompts_v2.py --print-id acc_hat_ocean_shell_01
  python scripts/generate_studio_prompts_v2.py --stats
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_OUT_DATA = _REPO / "data" / "studio_prompts_v2"
_OUT_DOCS = _REPO / "docs" / "studio_prompts_v2"
_INDEX = _REPO / "docs" / "STUDIO_PROMPTS_V2.md"

MAX_PROMPT_CHARS = 1000

# ---------------------------------------------------------------------------
# Shared prompt fragments (restated in every prompt — Studio does not cache)
# ---------------------------------------------------------------------------

STYLE_PROP = (
    "Stylized cartoon 3D game prop for PudgyMon: Party Saga — cute chunky monster party world. "
    "Bright readable candy colors, soft rounded edges, soft matte painted cartoon materials "
    "(not clay, not glossy vinyl), exaggerated silhouettes, soft even shading, no gore, "
    "no realistic dirt, no photorealism. Single isolated object, centered, floor-pivoted at "
    "ground center, game-ready low-to-mid poly, no base/plinth, no floating text, no characters."
)

STYLE_CHAR = (
    "Stylized cartoon 3D PudgyMon Party Saga. Soft Pokémon/Kirby painted matte look — "
    "NOT clay, vinyl, shiny plastic, or photoreal. Match shared base: ~1.2 m, stubby equal limbs, "
    "round dumpling torso, oversized head, A-pose arms out feet flat, floor pivot, faces camera-forward. "
    "Clear wear volumes (crown, neck, feet, back, face, hands) — no baked accessories. "
    "Single character, idle A-pose only, no weapons/text/plinth, family-friendly, low-mid poly."
)

ACC_LOCK = (
    "OBJECT ONLY — single isolated wearable prop on empty background. "
    "NO character, creature, mascot, head, face, body, limbs, mannequin, dummy, or avatar. "
    "NO one wearing it. Product turntable shot of the item alone. "
    "Stylized cartoon 3D game prop, soft matte candy colors, rounded toy edges, "
    "not clay, not glossy vinyl, not photoreal. Game-ready low poly. No base, plinth, or text."
)

NEGATIVE = (
    "photorealistic, grimdark, horror, blood, realistic weapons, space freight, corporate office, "
    "tiny unreadable labels, multiple objects, diorama, landscape, adult human proportions, "
    "clay, polymer clay, ceramic, earthen texture, stone, mud, fingerprint texture, "
    "glossy vinyl, shiny plastic, injection molded, clearcoat, specular hotspots, "
    "subsurface wax, dirty, scratched, fuzzy fur, uncanny realism"
)

ACC_NEGATIVE = (
    "character, creature, mascot, monster, animal, person, human, avatar, mannequin, dummy head, "
    "bust, torso, body, face, eyes, mouth, arms, legs, hands, feet, wearer, model wearing item, "
    "full figure, chibi character, cartoon creature, pudgy monster body"
)

# V1 ids already shipped — skip duplicates in V2
_V1_IDS = {
    "char_pudgy_base_01",
    "oceanic_pudgymon_01",
    "char_pudgy_forest_01",
    "char_pudgy_lava_01",
    "char_pudgy_sky_01",
    "acc_hat_party_crown_01",
    "acc_hat_racer_cap_01",
    "acc_hat_vibe_mushroom_01",
    "acc_hat_blaster_beanie_01",
    "acc_hat_propeller_01",
    "acc_hat_flower_01",
    "acc_hat_chef_01",
    "acc_hat_sleep_01",
    "acc_necklace_shell_01",
    "acc_necklace_medal_01",
    "acc_necklace_beads_01",
    "acc_necklace_bell_01",
    "acc_shoes_racer_01",
    "acc_shoes_party_01",
    "acc_shoes_boots_01",
    "acc_shoes_slippers_01",
    "acc_back_cape_01",
    "acc_back_wings_01",
    "acc_back_pack_01",
    "acc_face_shades_01",
    "acc_face_goggles_01",
    "acc_face_mask_01",
    "acc_hands_mittens_01",
    "acc_hands_gloves_01",
    "env_nest_egg_01",
    "env_nest_bench_01",
    "prop_vibe_mushroom_01",
    "env_pad_race_01",
    "env_pad_vibe_01",
    "env_pad_shooter_01",
    "env_pad_party_01",
    "prop_race_checkpoint_01",
    "prop_race_cone_01",
    "prop_race_banner_01",
    "env_race_ramp_01",
    "prop_vibe_orb_01",
    "prop_vibe_flower_01",
    "prop_vibe_crystal_01",
    "prop_blaster_toy_01",
    "prop_target_star_01",
    "prop_cover_block_01",
    "vfx_ko_burst_marker_01",
}


@dataclass
class PromptEntry:
    asset_id: str
    category: str
    priority: int
    kind: str  # character | accessory | env | prop | vfx
    label: str
    prompt: str
    target_height: float | None = None
    target_width: float | None = None
    slot: str | None = None
    notes: str = ""
    job_batch: str = "core"


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _fit(prompt: str) -> str:
    prompt = re.sub(r"\s+", " ", prompt).strip()
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt
    # Trim from middle of style if somehow over — should not happen with templates
    return prompt[: MAX_PROMPT_CHARS - 1].rstrip() + "."


def _prop(item: str, height: float | None = None, width: float | None = None) -> str:
    size = ""
    if height is not None and width is not None:
        size = f" About {height} meters tall and {width} meters wide."
    elif height is not None:
        size = f" About {height} meters tall."
    elif width is not None:
        size = f" About {width} meters wide."
    return _fit(f"{STYLE_PROP} {item.rstrip('.')}." + size)


def _char(biome_line: str) -> str:
    return _fit(f"{STYLE_CHAR} Only biome differs: {biome_line.rstrip('.')}.")


def _acc(item: str, pivot: str, size: str) -> str:
    return _fit(f"{ACC_LOCK} Item: {item.rstrip('.')}. Pivot at {pivot}. {size.rstrip('.')}.")


# ---------------------------------------------------------------------------
# Catalog builders
# ---------------------------------------------------------------------------


def build_characters() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    species = [
        ("candy", "Candy", "soft frosting swirls, sprinkle freckles, pink/cream candy palette"),
        ("ice", "Ice", "soft frost tufts, icy freckles, pale blue/white candy palette; no sharp ice"),
        ("desert", "Desert", "tiny sand freckles, soft cactus-bud ears, warm sand/coral candy palette"),
        ("meadow", "Meadow", "tiny flower freckles, soft petal cheeks, soft green/cream candy palette"),
        ("storm", "Storm", "soft thunder freckles, tiny cloud tufts, indigo/lavender candy palette; no scary"),
        ("crystal", "Crystal", "soft gem freckles, rounded crystal tufts, teal/lilac candy palette; not sharp glass"),
        ("berry", "Berry", "berry-seed freckles, soft berry blush, magenta/cream candy palette"),
        ("bubble", "Bubble", "soft bubble freckles, translucent candy sheen (matte painted), aqua/pink palette"),
        ("aurora", "Aurora", "soft aurora freckles, pastel ribbon tufts, mint/violet candy palette"),
        ("honey", "Honey", "soft honeycomb freckles, warm amber/cream candy palette, tiny bee-stripe cheeks"),
        ("mint", "Mint", "soft mint freckles, cool green/white candy palette, tiny leaf cheeks"),
        ("night", "Night", "soft star freckles, deep indigo/cream candy palette, cute moon blush; not scary"),
        ("coral", "Coral reef", "soft coral freckles, tiny reef buds, peach/teal candy palette"),
        ("ember", "Ember glow", "soft glow freckles, warm ember/charcoal candy palette; no real fire/smoke"),
        ("cloud", "Cloud puff", "extra puffball cheeks, soft white/sky candy palette, floaty silhouette"),
        ("sprout", "Sprout", "tiny sprout tuft on crown area (part of body, not accessory), lime/cream palette"),
        ("peach", "Peach", "soft peach freckles, warm peach/cream candy palette, dumpling blush"),
        ("grape", "Grape", "soft grape freckles, purple/cream candy palette, round berry cheeks"),
        ("lemon", "Lemon", "soft citrus freckles, yellow/lime candy palette, bright cheerful cheeks"),
        ("cocoa", "Cocoa", "soft cocoa freckles, chocolate/cream candy palette, warm friendly look"),
    ]
    for slug, label, line in species:
        aid = f"char_pudgy_{slug}_01"
        out.append(
            PromptEntry(
                asset_id=aid,
                category="characters_species",
                priority=0,
                kind="character",
                label=f"{label} species",
                prompt=_char(line),
                target_height=1.2,
                notes="Species skin on char_pudgy_base_01 contract",
                job_batch="characters",
            )
        )
        # Rare morph
        rare = f"char_pudgy_{slug}_rare_01"
        out.append(
            PromptEntry(
                asset_id=rare,
                category="characters_species",
                priority=0,
                kind="character",
                label=f"{label} rare morph",
                prompt=_char(
                    f"{line}; rare morph with soft iridescent candy highlights and tiny star freckles "
                    f"(still matte painted, not metallic chrome)"
                ),
                target_height=1.2,
                notes="Rare morph species skin",
                job_batch="characters",
            )
        )

    npcs = [
        ("npc_nest_dj_01", "Nest DJ Pudgy", "tiny soft headphone marks painted on ears area as body markings only, indigo/coral DJ candy palette, still clear wear volumes"),
        ("npc_nest_ref_01", "Nest referee Pudgy", "soft whistle freckles and cyan stripe cheeks, race-ref candy palette, still clear wear volumes"),
        ("npc_nest_shop_01", "Nest shopkeep Pudgy", "warm apricot candy palette, tiny coin freckles, friendly merchant look, still clear wear volumes"),
        ("npc_nest_photo_01", "Nest photographer Pudgy", "cream/teal candy palette, soft camera-shutter freckles, still clear wear volumes"),
        ("npc_nest_coach_01", "Nest coach Pudgy", "coral/yellow candy palette, soft whistle freckles, sporty but cute, still clear wear volumes"),
        ("npc_nest_bard_01", "Nest bard Pudgy", "lavender/cream candy palette, soft music-note freckles, still clear wear volumes"),
    ]
    for aid, label, line in npcs:
        out.append(
            PromptEntry(
                asset_id=aid,
                category="characters_npc",
                priority=0,
                kind="character",
                label=label,
                prompt=_char(line),
                target_height=1.2,
                notes="Nest NPC — same playable contract",
                job_batch="characters",
            )
        )

    # Seasonal variants of core biomes
    seasonal = [
        ("ocean_winter", "Ocean winter", "ocean fins plus soft snow freckles, teal/white candy palette"),
        ("forest_autumn", "Forest autumn", "leaf tufts in warm orange-lime candy, soft maple freckles"),
        ("lava_party", "Lava party", "ember freckles plus tiny party sparkles, coral-orange/gold candy palette; no fire"),
        ("sky_sunset", "Sky sunset", "cloud tufts with peach/rose candy sunset palette"),
        ("ocean_festival", "Ocean festival", "soft fins plus confetti freckles, teal/coral festival palette"),
        ("forest_bloom", "Forest bloom", "leaf tufts plus flower freckles, lime/pink candy palette"),
    ]
    for slug, label, line in seasonal:
        out.append(
            PromptEntry(
                asset_id=f"char_pudgy_{slug}_01",
                category="characters_seasonal",
                priority=0,
                kind="character",
                label=label,
                prompt=_char(line),
                target_height=1.2,
                notes="Seasonal species skin",
                job_batch="characters",
            )
        )
    return out


def _hat_items() -> list[tuple[str, str, float]]:
    """(slug, item description, height_m)"""
    items: list[tuple[str, str, float]] = []
    base = [
        ("ocean_shell", "soft ocean shell helmet hat, teal and cream candy, stubby ridges", 0.28),
        ("forest_leaf", "soft layered leaf crown hat, lime and olive candy", 0.26),
        ("lava_ember", "soft rounded ember crown hat, coral-orange and charcoal candy; no fire", 0.26),
        ("sky_cloud", "soft puffy cloud beret, sky-blue and cream candy", 0.24),
        ("ice_crown", "soft frosty candy crown, pale blue and white, rounded points; not sharp ice", 0.28),
        ("candy_scoop", "soft ice-cream scoop hat with sprinkle rim, pink and cream", 0.32),
        ("desert_cactus", "cute stubby cactus hat with soft spines as candy nubs, sand and teal", 0.30),
        ("meadow_wreath", "soft flower wreath hat, pink and lime candy petals", 0.22),
        ("storm_cap", "soft thundercloud cap with tiny candy bolt, indigo and cream; not scary", 0.26),
        ("crystal_tiara", "soft rounded crystal tiara, teal and lilac candy gems", 0.20),
        ("berry_bowl", "soft berry-bowl hat overflowing with candy berries, magenta and cream", 0.30),
        ("bubble_helm", "soft translucent-look bubble helmet (matte painted), aqua and pink", 0.28),
        ("aurora_halo", "soft aurora ribbon halo hat, mint and violet candy", 0.24),
        ("honey_pot", "soft honey-pot hat with candy drip rim, amber and cream", 0.30),
        ("mint_leaf", "soft mint-leaf beret, cool green and white candy", 0.22),
        ("night_moon", "soft crescent-moon hat, indigo and cream candy; cute not scary", 0.28),
        ("race_helmet", "chunky soft racing helmet with cyan speed stripe, rounded toy look", 0.26),
        ("vibe_sun", "soft smiling sun-disk hat, yellow and orange candy glow", 0.30),
        ("shooter_star", "soft oversized star beret, pink and magenta candy", 0.28),
        ("party_top", "chunky candy top hat with coral band and blank face (no text)", 0.34),
        ("bowler_party", "soft round bowler hat with star pin, gold and coral", 0.22),
        ("visor_racer", "soft candy racing visor, cyan and white", 0.14),
        ("bandana_party", "soft folded bandana hat, rainbow candy stripes", 0.16),
        ("earmuff_cloud", "connected soft cloud earmuffs as one hat mesh, cream and sky", 0.20),
        ("frog_hood", "soft friendly frog hood (hood only, no face/body), lime candy", 0.30),
        ("bunny_hood", "soft bunny-ear hood (hood only), cream and pink candy", 0.32),
        ("cat_hood", "soft cat-ear beanie (beanie only), coral and cream", 0.26),
        ("dino_hood", "soft stubby dino-spike hood (hood only), teal candy", 0.30),
        ("wizard_cute", "soft stubby wizard hat with star tip, purple and cream; cute not scary", 0.34),
        ("pirate_cute", "soft rounded pirate hat with candy plume, indigo and coral; family-friendly", 0.28),
        ("safari", "soft safari hat with rounded brim, sand and olive candy", 0.24),
        ("bucket_beach", "soft beach bucket hat, aqua and yellow candy", 0.22),
        ("pom_rainbow", "soft beanie with oversized rainbow pom-pom, multi candy colors", 0.26),
        ("halo_angel", "soft candy angel halo ring hat, cream and gold", 0.18),
        ("horn_candy", "pair of soft candy party horns as one hat mesh, coral and gold", 0.24),
        ("antler_soft", "soft stubby candy antlers hat, cream and coral", 0.28),
        ("tophat_mini", "tiny soft mini top hat on a clip base, black and gold candy matte", 0.20),
        ("flat_cap", "soft newsboy flat cap, teal and cream candy", 0.18),
        ("beret_artist", "soft artist beret, magenta and cream", 0.16),
        ("crown_gold", "soft rounded gold candy crown with blank gem faces, coral accents", 0.26),
        ("crown_silver", "soft rounded silver-candy crown with teal gems, matte not chrome", 0.26),
        ("crown_rainbow", "soft rainbow candy crown with stubby points", 0.28),
        ("helmet_star", "soft star-knight helmet toy, pink and cream; not military", 0.28),
        ("helmet_bubble", "soft bubble-knight helmet toy, aqua candy", 0.28),
        ("cap_trucker", "soft candy trucker cap with blank foam front, yellow and cyan", 0.20),
        ("cap_snap", "soft snapback candy cap with speed stripe, white and coral", 0.20),
        ("hat_witch_cute", "soft stubby witch hat with star buckle, purple and cream; cute", 0.34),
        ("hat_santa_cute", "soft stubby santa hat, coral and cream; party not holiday-cluttered", 0.30),
        ("hat_elf_cute", "soft elf hat with curled tip, lime and cream", 0.30),
        ("hat_pumpkin", "soft rounded pumpkin hat, orange and cream; cute Jack blank face no carve scary", 0.30),
        ("hat_heart", "soft oversized heart beret, pink and cream candy", 0.26),
        ("hat_clover", "soft four-leaf clover hat, lime candy", 0.24),
        ("hat_egg", "soft speckled egg shell hat, pastel cream and coral", 0.28),
        ("hat_gift", "soft gift-box hat with candy bow, coral and gold", 0.28),
        ("hat_lamp", "soft party lampshade hat, yellow and teal candy", 0.30),
        ("hat_teapot", "soft teapot hat with stubby spout, cream and coral", 0.30),
        ("hat_cupcake", "soft cupcake hat with frosting swirl, pink and cream", 0.32),
        ("hat_donut", "soft frosted donut hat with sprinkles, coral and cream", 0.24),
        ("hat_waffle", "soft waffle cone hat with scoop top, amber and pink", 0.34),
        ("hat_sushi", "soft sushi-roll hat, teal and cream candy; cute food toy", 0.22),
        ("hat_taco", "soft taco hat with candy filling nubs, yellow and coral", 0.24),
        ("hat_burger", "soft burger hat with candy layers, warm browns and green (matte)", 0.26),
        ("hat_pizza", "soft pizza-slice hat, coral and cream candy", 0.24),
        ("hat_banana", "soft banana peel hat, yellow and cream candy", 0.26),
        ("hat_mushroom_red", "soft red mushroom-cap hat with cream spots", 0.30),
        ("hat_mushroom_blue", "soft blue mushroom-cap hat with cream spots", 0.30),
        ("hat_acorn", "soft acorn hat, warm brown and cream candy matte", 0.26),
        ("hat_pine", "soft pinecone hat with rounded scales, olive and cream", 0.28),
        ("hat_sunflower", "soft sunflower hat with big petals, yellow and brown candy", 0.32),
        ("hat_rose", "soft rose blossom hat, pink candy petals", 0.28),
        ("hat_tulip", "soft tulip cup hat, coral and green candy", 0.28),
        ("hat_lotus", "soft lotus bloom hat, cream and lilac candy", 0.28),
        ("hat_lightning", "soft rounded lightning-bolt hat, yellow and indigo candy", 0.28),
        ("hat_raindrop", "soft raindrop hat, aqua and white candy", 0.26),
        ("hat_snowflake", "soft rounded snowflake hat, white and sky candy; not sharp", 0.26),
        ("hat_comet", "soft comet hat with stubby trail, gold and indigo candy", 0.30),
        ("hat_planet", "soft planet hat with candy ring, teal and cream", 0.28),
        ("hat_rocket", "soft stubby toy rocket hat, coral and cyan candy; family toy", 0.32),
        ("hat_ufo", "soft UFO saucer hat, silver-candy matte and teal lights", 0.24),
        ("hat_robot", "soft rounded robot dome hat, cyan and cream; cute toy", 0.26),
        ("hat_tv", "soft retro TV hat with blank screen, cream and coral", 0.28),
        ("hat_boombox", "soft boombox hat, magenta and yellow candy", 0.26),
        ("hat_headphones", "soft oversized headphone hat (band+cups as one mesh), indigo and coral", 0.24),
        ("hat_camera", "soft toy camera hat, cream and teal candy", 0.24),
        ("hat_trophy", "soft mini trophy cup hat, gold candy matte and coral", 0.28),
        ("hat_medal", "soft oversized medal hat on ribbon base, gold and cyan", 0.26),
        ("hat_flag", "soft checkered race flag hat, cyan and white candy", 0.28),
        ("hat_whistle", "soft oversized whistle hat, yellow and coral candy", 0.24),
        ("hat_megaphone", "soft megaphone hat, coral and cream candy", 0.28),
        ("hat_confetti", "soft confetti-burst hat with stubby streamers, rainbow candy", 0.28),
        ("hat_balloon", "soft balloon-cluster hat, coral pink yellow candy balloons", 0.34),
        ("hat_party_popper", "soft party-popper hat with candy streamers, yellow and pink", 0.30),
        ("hat_dice", "soft rounded dice hat with blank soft pips, cream and coral", 0.24),
        ("hat_controller", "soft game-controller hat, teal and cream candy", 0.22),
        ("hat_arcade", "soft arcade-cabinet hat, magenta and cyan candy", 0.32),
        ("hat_ticket", "soft folded ticket hat, coral and cream with blank face", 0.20),
        ("hat_popcorn", "soft popcorn bucket hat overflowing candy kernels, red-white stripes", 0.30),
        ("hat_cotton", "soft cotton-candy swirl hat, pink and blue candy", 0.32),
        ("hat_lollipop", "soft oversized lollipop hat, swirl coral and cream", 0.34),
        ("hat_gumball", "soft gumball-machine dome hat, teal glass-look matte and cream", 0.32),
        ("hat_pretzel", "soft pretzel hat, amber candy twist", 0.24),
        ("hat_cookie", "soft cookie hat with candy chips, warm brown and cream", 0.22),
        ("hat_jam", "soft jam-jar hat, magenta and cream candy", 0.28),
        ("hat_milk", "soft milk-carton hat, cream and sky with blank face", 0.28),
        ("hat_toast", "soft toast-slice hat with candy butter pat, cream and gold", 0.24),
        ("hat_egg_fried", "soft sunny-side-up egg hat, cream and yellow candy", 0.22),
        ("hat_bacon", "soft candy bacon-strip hat, coral and cream stripes", 0.18),
        ("hat_avocado", "soft avocado half hat with candy pit, lime and cream", 0.24),
        ("hat_strawberry", "soft strawberry hat with leaf top, pink and green candy", 0.28),
        ("hat_blueberry", "soft blueberry cluster hat, indigo and cream", 0.24),
        ("hat_watermelon", "soft watermelon-slice hat, pink green and cream candy", 0.24),
        ("hat_kiwi", "soft kiwi-slice hat, lime and cream candy", 0.22),
        ("hat_dragonfruit", "soft dragonfruit hat, magenta and cream candy", 0.28),
        ("hat_peach_fruit", "soft peach fruit hat with leaf, peach and green candy", 0.26),
        ("hat_cherry", "soft twin-cherry hat on stems, coral and green candy", 0.28),
        ("hat_grape_bunch", "soft grape-bunch hat, purple and green candy", 0.28),
        ("hat_lemon_fruit", "soft lemon fruit hat with leaf, yellow and lime candy", 0.26),
        ("hat_coconut", "soft coconut half hat, cream and brown candy matte", 0.24),
        ("hat_pineapple", "soft pineapple hat with leafy top, yellow and green candy", 0.34),
        ("hat_chili", "soft chili-pepper hat, coral and green candy; cute not spicy-scary", 0.28),
        ("hat_olive", "soft olive hat with toothpick bow, olive and cream", 0.22),
        ("hat_cheese", "soft Swiss-cheese wedge hat, yellow candy with soft holes", 0.24),
        ("hat_bread", "soft loaf-bread hat, warm cream candy", 0.24),
        ("hat_baguette", "soft curved baguette hat, cream and gold candy", 0.20),
        ("hat_croissant", "soft croissant hat, amber candy flaky look (matte painted)", 0.22),
        ("hat_macaron", "soft macaron hat, pastel pink and cream sandwich", 0.20),
        ("hat_pudding", "soft pudding cup hat with candy cream dollop, caramel and cream", 0.26),
        ("hat_jelly", "soft jelly-mold hat, translucent-look matte coral candy", 0.24),
        ("hat_mochi", "soft mochi cube hat, pastel pink candy", 0.20),
        ("hat_taiaki", "soft fish-shaped pastry hat, gold and cream candy", 0.24),
        ("hat_onigiri", "soft onigiri triangle hat with seaweed band, cream and charcoal candy", 0.24),
        ("hat_bento", "soft bento-box hat with candy food nubs, cream and coral", 0.26),
        ("hat_ramen", "soft ramen-bowl hat with candy noodle swirls, cream and coral", 0.28),
        ("hat_tea", "soft teacup hat with candy steam nubs, cream and teal", 0.26),
        ("hat_coffee", "soft coffee-cup hat with candy lid, cream and brown matte", 0.26),
        ("hat_smoothie", "soft smoothie cup hat with candy straw, pink and teal", 0.30),
        ("hat_soda", "soft soda-can hat with blank label, coral and cream", 0.28),
        ("hat_juice", "soft juice-box hat with candy straw, orange and cream", 0.26),
        ("hat_water", "soft water-bottle hat, aqua and cream candy", 0.28),
        ("hat_thermos", "soft thermos bottle hat, yellow and teal candy", 0.30),
        ("hat_lantern", "soft paper-lantern hat, coral and cream candy glow", 0.30),
        ("hat_candle", "soft birthday-candle hat with soft flame candy tip (not real fire)", 0.32),
        ("hat_cake_slice", "soft cake-slice hat with frosting, pink and cream", 0.26),
        ("hat_birthday", "soft birthday party hat cone, rainbow candy stripes", 0.30),
        ("hat_graduation", "soft stubby graduation cap, indigo and gold candy; blank", 0.20),
        ("hat_nurse_cute", "soft rounded nurse hat, white and coral candy cross blank", 0.18),
        ("hat_builder", "soft toy hard-hat, yellow candy; family construction toy look", 0.22),
        ("hat_firefighter", "soft toy firefighter helmet, coral candy; cute toy not realistic", 0.26),
        ("hat_astronaut", "soft stubby astronaut helmet dome, white and cyan candy", 0.30),
        ("hat_pilot", "soft pilot cap with candy goggles band, teal and cream", 0.22),
        ("hat_sailor", "soft sailor hat, white and navy candy matte", 0.20),
        ("hat_cowboy", "soft stubby cowboy hat, sand and coral candy", 0.24),
        ("hat_sombrero", "soft wide sombrero, yellow and coral candy trim", 0.22),
        ("hat_fez", "soft candy fez with tassel, coral and gold", 0.24),
        ("hat_turban", "soft wrapped turban hat, teal and gold candy; respectful stylized toy", 0.26),
        ("hat_kimono_ribbon", "soft oversized kimono bow hat, pink and cream candy", 0.28),
        ("hat_lei", "soft flower lei worn as crown hat, rainbow candy petals", 0.20),
        ("hat_lei_shell", "soft shell lei crown hat, teal and cream candy", 0.20),
        ("hat_viking_cute", "soft stubby viking hat with candy horns, cream and coral; cute", 0.28),
        ("hat_samurai_cute", "soft stubby samurai kabuto toy, teal and gold candy; family toy", 0.28),
        ("hat_knight_cute", "soft stubby knight helm toy, silver-candy matte and coral plume", 0.28),
        ("hat_pharaoh_cute", "soft stubby pharaoh crown toy, gold and teal candy; respectful stylized", 0.28),
        ("hat_jester", "soft jester hat with three stubby points and bells, rainbow candy", 0.32),
        ("hat_clown_cute", "soft clown hat cone with pom, coral and cream; cute not creepy", 0.30),
        ("hat_mime", "soft rounded mime beret, black and white candy matte", 0.16),
        ("hat_superhero", "soft stubby superhero cowl (mask-hat only), coral and cream", 0.26),
        ("hat_sidekick", "soft sidekick ear-hood, yellow and cyan candy", 0.28),
        ("hat_ninja_cute", "soft ninja headwrap hat, indigo candy; cute toy not scary", 0.18),
        ("hat_spy", "soft spy fedora, charcoal and cream candy matte", 0.22),
        ("hat_detective", "soft deerstalker hat, brown and cream candy matte", 0.22),
        ("hat_librarian", "soft book-stack hat, cream and coral candy spines blank", 0.28),
        ("hat_scientist", "soft beaker hat with candy bubble nubs, teal and cream", 0.30),
        ("hat_gamer", "soft headset-crown hat, magenta and cyan candy", 0.24),
        ("hat_streamer", "soft glow-ring hat, coral and cream candy", 0.22),
        ("hat_influencer", "soft phone-shaped hat with blank screen, cream and teal", 0.26),
        ("hat_tourist", "soft camera-strap bucket combo hat, yellow and teal", 0.24),
        ("hat_camper", "soft camping beanie with tiny candy patch, olive and cream", 0.22),
        ("hat_fisher", "soft fishing hat with candy lure blank, teal and sand", 0.22),
        ("hat_gardener", "soft gardener sun hat with candy flower pin, lime and cream", 0.24),
        ("hat_baker", "soft baker skullcap, white and coral candy", 0.16),
        ("hat_butcher_cute", "soft striped butcher-toy hat, coral and cream; cute food party", 0.20),
        ("hat_waiter", "soft waiter bow-hat, black and white candy matte", 0.18),
        ("hat_mail", "soft mail-bag cap, teal and cream candy", 0.22),
        ("hat_post", "soft stamp hat with blank face, coral and cream", 0.20),
        ("hat_train", "soft toy train-engine hat, cyan and yellow candy", 0.28),
        ("hat_car", "soft stubby race-car hat, coral and cyan candy", 0.24),
        ("hat_bike", "soft bike-helmet candy toy, yellow and teal", 0.22),
        ("hat_skate", "soft skateboard hat deck-up, magenta and cyan candy", 0.18),
        ("hat_surf", "soft surfboard hat, aqua and coral candy", 0.20),
        ("hat_ski", "soft ski-beanie with candy goggle band, white and sky", 0.22),
        ("hat_snowboard", "soft snowboard hat, indigo and yellow candy", 0.18),
        ("hat_soccer", "soft soccer-ball hat, white and coral candy pentagons soft", 0.24),
        ("hat_basketball", "soft basketball hat, coral and cream candy", 0.24),
        ("hat_tennis", "soft tennis-ball hat, lime candy with soft curve", 0.22),
        ("hat_baseball", "soft baseball-cap with blank front, white and coral", 0.20),
        ("hat_football", "soft football helmet toy, brown and white candy; family toy", 0.26),
        ("hat_hockey", "soft hockey helmet toy, teal and cream candy", 0.24),
        ("hat_golf", "soft golf-visor hat, white and lime candy", 0.14),
        ("hat_bowling", "soft bowling-ball hat with soft finger holes, indigo and cream", 0.24),
        ("hat_dart", "soft dartboard hat with blank soft rings, coral and cream", 0.24),
        ("hat_chess", "soft chess-king piece hat, cream and coral candy", 0.30),
        ("hat_pawn", "soft chess-pawn hat, teal candy", 0.26),
        ("hat_card", "soft playing-card hat with blank face, cream and coral", 0.24),
        ("hat_joker", "soft joker-card hat cute, purple and gold candy", 0.26),
        ("hat_domino", "soft domino tile hat with soft pips, cream and indigo", 0.20),
        ("hat_puzzle", "soft puzzle-piece hat, yellow and teal candy", 0.22),
        ("hat_rubik", "soft rounded cube puzzle hat, rainbow candy faces blank", 0.24),
        ("hat_yoyo", "soft yo-yo hat, coral and cream candy", 0.22),
        ("hat_kite", "soft kite hat with stubby tail, cyan and yellow candy", 0.28),
        ("hat_pinwheel", "soft pinwheel hat, rainbow candy blades", 0.28),
        ("hat_windmill", "soft stubby windmill hat, cream and teal candy", 0.30),
        ("hat_lighthouse", "soft lighthouse hat, coral and white candy stripes", 0.34),
        ("hat_castle", "soft stubby castle-turret hat, cream and coral candy", 0.32),
        ("hat_tent", "soft camping-tent hat, yellow and teal candy", 0.28),
        ("hat_igloo", "soft igloo dome hat, white and sky candy", 0.26),
        ("hat_pyramid", "soft rounded pyramid hat, sand and gold candy", 0.28),
        ("hat_temple", "soft stubby temple-roof hat, teal and cream candy", 0.28),
        ("hat_pagoda", "soft pagoda-tier hat, coral and cream candy", 0.32),
        ("hat_totem", "soft friendly totem-face hat blank cute, teal and coral", 0.30),
        ("hat_mask_tribal", "soft friendly tribal-pattern hat blank, lime and cream; respectful stylized", 0.26),
        ("hat_feather", "soft feather-plume hat, coral and cream candy", 0.30),
        ("hat_peacock", "soft peacock-fan hat, teal and gold candy; cute", 0.32),
        ("hat_owl", "soft owl-hood hat (hood only), cream and brown candy; cute", 0.28),
        ("hat_fox", "soft fox-ear hood (hood only), coral and cream", 0.28),
        ("hat_bear", "soft bear-ear beanie, warm brown and cream candy", 0.24),
        ("hat_panda", "soft panda-ear beanie, cream and charcoal candy", 0.24),
        ("hat_penguin", "soft penguin hood (hood only), indigo and cream candy", 0.28),
        ("hat_chick", "soft chick hood (hood only), yellow and cream candy", 0.26),
        ("hat_duckling", "soft duckling hood, yellow and orange candy", 0.26),
        ("hat_piglet", "soft piglet-ear beanie, pink candy", 0.24),
        ("hat_lamb", "soft lamb-ear beanie, cream candy fluff look (matte painted)", 0.24),
        ("hat_cow", "soft cow-ear beanie with soft spots, cream and brown", 0.24),
        ("hat_horse", "soft horse-ear beanie, brown and cream candy", 0.26),
        ("hat_unicorn", "soft unicorn-horn hat with candy mane nubs, cream and pink", 0.30),
        ("hat_dragon_cute", "soft stubby dragon-horn hat, teal and coral candy; cute", 0.28),
        ("hat_phoenix", "soft phoenix-plume hat, coral and gold candy; no real fire", 0.32),
        ("hat_griffin", "soft griffin-ear hat, cream and gold candy", 0.28),
        ("hat_mermaid", "soft mermaid-crown shell hat, teal and pink candy", 0.26),
        ("hat_trident", "soft stubby trident crown, gold and teal candy", 0.28),
        ("hat_anchor", "soft anchor hat, navy and cream candy", 0.26),
        ("hat_wheel", "soft ship-wheel hat, wood-candy brown and cream", 0.26),
        ("hat_compass", "soft compass hat with blank face, gold and teal candy", 0.22),
        ("hat_map", "soft folded map hat, cream and coral candy blank", 0.20),
        ("hat_binoculars", "soft binoculars hat, teal and cream candy", 0.22),
        ("hat_telescope", "soft stubby telescope hat, indigo and gold candy", 0.30),
        ("hat_hourglass", "soft hourglass hat, cream and coral candy", 0.28),
        ("hat_clock", "soft clock hat with blank soft hands, cream and gold", 0.24),
        ("hat_alarm", "soft alarm-clock hat, coral and cream candy", 0.26),
        ("hat_bell_big", "soft oversized bell hat, gold and cream candy", 0.28),
        ("hat_gong", "soft gong hat, gold and teal candy", 0.24),
        ("hat_drum", "soft drum hat, coral and cream candy", 0.24),
        ("hat_guitar", "soft stubby guitar hat, wood-candy and coral", 0.28),
        ("hat_piano", "soft piano-key hat strip, cream and charcoal candy", 0.18),
        ("hat_mic", "soft microphone hat, silver-candy matte and coral", 0.28),
        ("hat_vinyl", "soft vinyl-record hat, charcoal and coral candy", 0.18),
        ("hat_cd", "soft disc hat with candy rainbow sheen matte, silver-candy", 0.16),
        ("hat_cassette", "soft cassette-tape hat, yellow and cream candy", 0.18),
        ("hat_radio", "soft radio hat with candy dial, teal and coral", 0.24),
        ("hat_walkie", "soft walkie-talkie hat, yellow and charcoal candy", 0.28),
        ("hat_phone_old", "soft rotary-phone hat, coral and cream candy", 0.26),
        ("hat_typewriter", "soft typewriter hat, cream and coral candy", 0.24),
        ("hat_pencil", "soft oversized pencil hat, yellow and pink candy eraser", 0.34),
        ("hat_crayon", "soft crayon hat, rainbow candy wrapper", 0.32),
        ("hat_paintbrush", "soft paintbrush hat with candy bristle tip, wood and coral", 0.32),
        ("hat_palette", "soft paint-palette hat with candy blobs, cream and rainbow", 0.22),
        ("hat_scissors", "soft toy scissors hat closed, teal and cream; blunt cute", 0.24),
        ("hat_ruler", "soft ruler hat, yellow candy with blank marks", 0.18),
        ("hat_globe", "soft globe hat, teal and cream candy continents soft", 0.26),
        ("hat_atom", "soft atom-orbit hat, cyan and cream candy", 0.28),
        ("hat_dna", "soft DNA-helix hat, pink and teal candy twist", 0.30),
        ("hat_heart_pixel", "soft pixel-heart hat, coral candy chunky pixels", 0.24),
        ("hat_star_pixel", "soft pixel-star hat, yellow candy chunky pixels", 0.24),
        ("hat_gem_pixel", "soft pixel-gem hat, teal candy chunky pixels", 0.24),
        ("hat_coin_pixel", "soft pixel-coin hat, gold candy chunky pixels", 0.20),
        ("hat_sword_toy", "soft toy sword hilt hat, coral and gold candy; blunt family toy", 0.28),
        ("hat_shield_toy", "soft toy shield hat, teal and cream candy", 0.26),
        ("hat_bow_toy", "soft toy bow hat, wood-candy and coral string", 0.24),
        ("hat_wand", "soft stubby magic wand hat, gold and star tip candy", 0.32),
        ("hat_potion", "soft potion-bottle hat with candy swirl, purple and teal", 0.30),
        ("hat_cauldron", "soft cute cauldron hat, charcoal and green candy glow; not scary", 0.26),
        ("hat_crystal_ball", "soft crystal-ball hat on stubby base, teal candy glow", 0.28),
        ("hat_tarot", "soft tarot-card hat blank cute, indigo and gold candy", 0.24),
        ("hat_ouija_cute", "soft planchette hat cute blank, cream and coral; playful not occult-scary", 0.20),
        ("hat_ghost_cute", "soft ghost-sheet hat cute, cream candy; friendly not scary", 0.28),
        ("hat_bat_cute", "soft bat-wing hat cute, indigo and cream; friendly", 0.26),
        ("hat_spider_cute", "soft spider-charm hat cute, charcoal and coral; friendly toy", 0.22),
        ("hat_web_cute", "soft candy web beret, cream and teal; cute", 0.20),
        ("hat_skull_candy", "soft candy skull hat cute blank smile, cream and pink; not scary", 0.26),
        ("hat_bone", "soft candy bone hat, cream candy", 0.20),
        ("hat_zombie_cute", "soft mismatched candy stitch hat, lime and cream; cute not gore", 0.24),
        ("hat_mummy_cute", "soft bandage-wrap hat, cream candy; cute not scary", 0.22),
        ("hat_vampire_cute", "soft vampire widow-peak hat, indigo and cream; cute", 0.24),
        ("hat_werewolf_cute", "soft wolf-ear hat, brown and cream; cute", 0.26),
        ("hat_alien_cute", "soft alien antenna hat, lime and cream candy", 0.28),
        ("hat_monster_cute", "soft one soft-horn monster hat, teal and coral; cute", 0.28),
        ("hat_slime", "soft slime-drip hat, lime candy translucent-look matte", 0.24),
        ("hat_goo", "soft goo-blob hat, magenta candy", 0.22),
        ("hat_gelatin", "soft gelatin cube hat, coral translucent-look matte", 0.22),
        ("hat_neon", "soft neon-tube halo hat, cyan candy glow matte", 0.20),
        ("hat_glowstick", "soft glowstick crown, rainbow candy sticks", 0.24),
        ("hat_disco", "soft disco-ball hat, silver-candy facets matte not chrome mirror", 0.26),
        ("hat_mirror", "soft hand-mirror hat, gold and cream candy blank face", 0.28),
        ("hat_comb", "soft oversized comb hat, coral candy", 0.22),
        ("hat_brush", "soft hairbrush hat, pink and cream candy", 0.26),
        ("hat_soap", "soft soap-bar hat with candy bubbles, cream and aqua", 0.18),
        ("hat_sponge", "soft sponge hat, yellow candy", 0.20),
        ("hat_towel", "soft wrapped towel turban hat, coral and cream", 0.26),
        ("hat_shower", "soft shower-cap hat, clear-look matte aqua candy", 0.20),
        ("hat_rubber_duck", "soft rubber-duck hat, yellow candy", 0.26),
        ("hat_bathtub", "soft stubby bathtub hat, cream and coral candy", 0.24),
        ("hat_toilet_cute", "soft cute toilet-lid hat joke prop, white and teal; tasteful silly", 0.24),
        ("hat_plunger_cute", "soft plunger hat joke, coral and cream; silly party", 0.28),
        ("hat_boot_single", "soft oversized single boot hat, yellow candy", 0.28),
        ("hat_sock", "soft mismatched sock hat, rainbow candy stripes", 0.26),
        ("hat_glove_single", "soft oversized mitten hat, coral candy", 0.24),
        ("hat_scarf_wrap", "soft scarf-wrap hat, teal and cream candy", 0.22),
        ("hat_tie", "soft oversized necktie hat, indigo and coral candy", 0.28),
        ("hat_bowtie_big", "soft oversized bowtie hat, gold and coral candy", 0.22),
        ("hat_suspenders", "soft suspenders-arch hat, yellow and cream candy", 0.24),
        ("hat_belt", "soft coiled belt hat with candy buckle blank, brown and gold", 0.20),
        ("hat_watch", "soft oversized watch hat, gold and cream candy blank face", 0.22),
        ("hat_ring_big", "soft oversized gem ring hat, gold and teal candy", 0.20),
        ("hat_key", "soft oversized key hat, gold candy", 0.28),
        ("hat_lock", "soft padlock hat, silver-candy and coral", 0.24),
        ("hat_safe", "soft stubby safe hat, charcoal and gold candy", 0.26),
        ("hat_piggy", "soft piggy-bank hat, pink candy", 0.26),
        ("hat_wallet", "soft wallet hat, brown and cream candy", 0.18),
        ("hat_purse", "soft purse hat, coral and gold candy", 0.24),
        ("hat_backpack_mini", "soft mini backpack hat, teal and yellow candy", 0.26),
        ("hat_suitcase", "soft suitcase hat, cream and coral candy", 0.24),
        ("hat_umbrella", "soft open umbrella hat, yellow and teal candy", 0.28),
        ("hat_parasol", "soft parasol hat, pink and cream candy", 0.28),
        ("hat_fan", "soft folding fan hat open, coral and cream candy", 0.22),
        ("hat_flag_party", "soft party pennant hat, rainbow candy", 0.28),
        ("hat_banner_mini", "soft mini banner hat on posts, cyan and cream blank", 0.26),
        ("hat_ribbon", "soft giant ribbon bow hat, magenta candy", 0.24),
        ("hat_gift_bow", "soft gift-bow explosion hat, gold and coral candy", 0.26),
        ("hat_tag", "soft price-tag hat blank, cream and coral", 0.22),
        ("hat_barcode", "soft barcode-stripe hat blank, cream and charcoal", 0.18),
        ("hat_qr_cute", "soft chunky QR-look square hat blank cute pattern, cream and teal", 0.20),
        ("hat_wifi", "soft wifi-signal arc hat, cyan candy", 0.24),
        ("hat_battery", "soft battery hat, yellow and cream candy", 0.26),
        ("hat_plug", "soft electrical-plug hat, coral and cream; toy safe look", 0.24),
        ("hat_lightbulb", "soft lightbulb hat, yellow and cream candy glow", 0.30),
        ("hat_candle_jar", "soft candle-jar hat, cream and coral candy soft flame tip", 0.28),
        ("hat_fireplace", "soft stubby fireplace mantel hat, coral and cream; no real fire", 0.28),
        ("hat_chimney", "soft chimney hat with soft smoke puff nubs, brick-candy coral", 0.32),
        ("hat_roof", "soft house-roof hat, teal and cream candy", 0.26),
        ("hat_door", "soft door hat with candy knob, coral and cream", 0.28),
        ("hat_window", "soft window-frame hat, teal and cream candy", 0.24),
        ("hat_fence", "soft picket-fence hat arc, cream candy", 0.22),
        ("hat_mailbox", "soft mailbox hat, coral and cream candy", 0.28),
        ("hat_hydrant", "soft fire-hydrant hat, coral candy toy", 0.30),
        ("hat_traffic", "soft traffic-light hat, charcoal with soft candy lights", 0.32),
        ("hat_stop", "soft octagon stop-sign hat blank, coral candy", 0.26),
        ("hat_yield", "soft yield-triangle hat blank, yellow candy", 0.24),
        ("hat_arrow", "soft arrow-sign hat blank, cyan candy", 0.26),
        ("hat_parking", "soft parking-meter hat, teal and cream candy", 0.30),
        ("hat_meter", "soft coin-meter hat, gold and charcoal candy", 0.28),
        ("hat_gas", "soft toy gas-pump hat, yellow and teal candy; cute", 0.32),
        ("hat_ev", "soft EV-charger hat, cyan and cream candy", 0.30),
        ("hat_solar", "soft solar-panel hat, indigo and cream candy", 0.18),
        ("hat_wind", "soft wind-turbine hat, white and teal candy", 0.32),
        ("hat_recycle", "soft recycle-arrows loop hat, lime candy", 0.24),
        ("hat_leaf_eco", "soft eco-leaf hat, green candy", 0.24),
        ("hat_earth", "soft earth-globe hat, teal and green candy", 0.26),
        ("hat_moon_full", "soft full-moon hat, cream candy crater soft", 0.26),
        ("hat_sun_simple", "soft simple sun hat, yellow candy rays soft", 0.28),
        ("hat_eclipse", "soft eclipse hat, indigo and gold candy ring", 0.26),
        ("hat_milky", "soft milky-way swirl hat, indigo and cream candy", 0.26),
        ("hat_blackhole_cute", "soft swirl portal hat cute, indigo and pink candy; not scary", 0.24),
        ("hat_portal", "soft oval portal-frame hat, teal and magenta candy", 0.28),
        ("hat_wormhole", "soft twisted ring hat, purple and cyan candy", 0.24),
        ("hat_dimension", "soft stacked-square hat, rainbow candy frames", 0.26),
        ("hat_glitch", "soft glitch-slice hat, magenta and cyan candy offsets", 0.24),
        ("hat_error_cute", "soft error-popup hat blank cute, cream and coral", 0.22),
        ("hat_loading", "soft loading-spinner hat, teal candy ring", 0.22),
        ("hat_cursor", "soft mouse-cursor arrow hat, cream candy", 0.24),
        ("hat_pointer", "soft hand-pointer hat, cream and coral candy", 0.24),
        ("hat_click", "soft click-ripple hat, cyan candy rings", 0.20),
        ("hat_like", "soft thumbs-up hat, coral candy", 0.24),
        ("hat_love", "soft double-heart hat, pink candy", 0.24),
        ("hat_fire_emoji", "soft cartoon fire emoji hat, coral and gold; no real fire", 0.26),
        ("hat_100", "soft chunky 100 badge hat blank stylized, coral and cream", 0.22),
        ("hat_star_eyes", "soft star-eyes emoji hat, yellow candy", 0.22),
        ("hat_sparkles", "soft sparkles burst hat, gold and pink candy", 0.24),
        ("hat_zzz", "soft ZZZ sleep hat, indigo and cream candy", 0.24),
        ("hat_music_note", "soft music-note hat, magenta candy", 0.28),
        ("hat_eightbit", "soft 8-bit smile hat, cream and coral chunky pixels", 0.22),
    ]
    items.extend(base)
    return items


def _necklace_items() -> list[tuple[str, str, float]]:
    return [
        ("ocean_pearl", "soft pearl strand necklace, teal and cream candy pearls", 0.18),
        ("forest_vine", "soft leafy vine collar, lime candy leaves", 0.16),
        ("lava_charm", "soft ember charm on thick candy chain, coral-orange; no fire", 0.18),
        ("sky_cloud", "soft cloud pendant on sky-blue ribbon, cream candy", 0.18),
        ("ice_flake", "soft rounded snowflake pendant, white and sky candy", 0.18),
        ("candy_heart", "soft heart locket on pink candy chain", 0.18),
        ("race_whistle", "soft toy whistle on cyan lanyard", 0.16),
        ("vibe_orb", "soft mini vibe-orb pendant, yellow glow candy", 0.18),
        ("shooter_star", "soft star pendant on pink ribbon", 0.18),
        ("party_lei", "soft flower lei collar, rainbow candy petals", 0.16),
        ("gold_chain", "soft chunky gold candy chain, matte not chrome", 0.16),
        ("silver_chain", "soft chunky silver-candy chain, matte", 0.16),
        ("rainbow_chain", "soft rainbow candy bead chain", 0.16),
        ("tooth_cute", "soft candy tooth charm on chain, cream; cute", 0.16),
        ("key_charm", "soft key charm on coral ribbon", 0.18),
        ("locket_blank", "soft round locket blank face, gold and cream", 0.18),
        ("camera_charm", "soft toy camera charm, teal and cream", 0.16),
        ("mic_charm", "soft mic charm on magenta cord", 0.16),
        ("ticket_charm", "soft ticket charm blank, coral and cream", 0.16),
        ("coin_charm", "soft oversized coin pendant blank, gold candy", 0.18),
        ("gem_teal", "soft teal gem pendant on cream chain", 0.18),
        ("gem_pink", "soft pink gem pendant on gold chain", 0.18),
        ("gem_lime", "soft lime gem pendant on teal chain", 0.18),
        ("gem_indigo", "soft indigo gem pendant on cream chain", 0.18),
        ("amulet_sun", "soft sun amulet, yellow and coral candy", 0.18),
        ("amulet_moon", "soft moon amulet, indigo and cream candy", 0.18),
        ("amulet_star", "soft star amulet, gold and pink candy", 0.18),
        ("amulet_leaf", "soft leaf amulet, lime candy", 0.16),
        ("amulet_shell", "soft spiral shell amulet, teal candy", 0.18),
        ("amulet_flame", "soft cute flame amulet, coral candy; no real fire", 0.18),
        ("amulet_wave", "soft wave amulet, aqua candy", 0.16),
        ("amulet_bolt", "soft rounded bolt amulet, yellow and indigo", 0.16),
        ("collar_spikes_soft", "soft candy spike collar, rounded nubs, coral", 0.14),
        ("collar_bow", "soft bow-tie collar, pink and cream", 0.14),
        ("collar_bells", "soft multi-bell collar, gold and coral", 0.16),
        ("collar_tag", "soft pet-tag collar blank, teal and cream", 0.14),
        ("scarf_loop", "soft short scarf loop necklace, cyan candy", 0.16),
        ("bandana_neck", "soft bandana neckerchief, rainbow candy", 0.14),
        ("choker_heart", "soft heart choker, pink candy", 0.12),
        ("choker_star", "soft star choker, yellow candy", 0.12),
        ("choker_pearl", "soft single pearl choker, cream candy", 0.12),
        ("choker_velvet", "soft velvet-look candy choker, indigo matte", 0.12),
        ("pendant_egg", "soft mini nest-egg pendant, pastel cream", 0.16),
        ("pendant_mushroom", "soft mini mushroom pendant, teal candy", 0.16),
        ("pendant_crystal", "soft mini crystal pendant, lilac candy", 0.16),
        ("pendant_orb", "soft mini collect orb pendant, yellow candy", 0.16),
        ("pendant_target", "soft star-target pendant, pink candy", 0.16),
        ("pendant_blaster", "soft toy blaster charm, pink and yellow; toy only", 0.16),
        ("pendant_cone", "soft race-cone charm, coral and white", 0.16),
        ("pendant_flag", "soft checkered flag charm, cyan and white", 0.16),
        ("pendant_trophy", "soft mini trophy charm, gold candy", 0.18),
        ("pendant_medal_alt", "soft star medal on ribbon, gold and magenta", 0.18),
        ("pendant_crown", "soft mini crown pendant, gold and coral", 0.16),
        ("pendant_cake", "soft cake-slice pendant, pink candy", 0.16),
        ("pendant_donut", "soft donut pendant, coral sprinkles", 0.14),
        ("pendant_cookie", "soft cookie pendant, warm brown candy", 0.14),
        ("pendant_lolli", "soft lollipop pendant, swirl pink", 0.18),
        ("pendant_ice", "soft popsicle pendant, aqua and cream", 0.18),
        ("pendant_popcorn", "soft popcorn charm, yellow and coral", 0.14),
        ("pendant_balloon", "soft balloon charm, pink candy", 0.16),
        ("pendant_gift", "soft gift-box charm, coral and gold", 0.16),
        ("pendant_letter", "soft envelope charm blank, cream and coral", 0.14),
        ("pendant_heart_lock", "soft heart-lock pendant, gold and pink", 0.16),
        ("pendant_music", "soft music-note pendant, magenta candy", 0.16),
        ("pendant_game", "soft controller pendant, teal candy", 0.14),
        ("pendant_dice", "soft dice pendant soft pips, cream and coral", 0.14),
        ("pendant_clover", "soft four-leaf clover pendant, lime candy", 0.14),
        ("pendant_horseshoe", "soft horseshoe pendant, gold candy", 0.14),
        ("pendant_anchor", "soft anchor pendant, navy and cream", 0.16),
        ("pendant_compass", "soft compass pendant blank, gold and teal", 0.14),
        ("pendant_planet", "soft planet pendant with ring, teal candy", 0.16),
        ("pendant_rocket", "soft toy rocket pendant, coral and cyan", 0.16),
        ("pendant_alien", "soft cute alien-head pendant, lime candy", 0.14),
        ("pendant_ghost", "soft cute ghost pendant, cream candy", 0.14),
        ("pendant_pumpkin", "soft cute pumpkin pendant, orange candy", 0.14),
        ("pendant_snowman", "soft cute snowman pendant, cream and coral", 0.16),
        ("pendant_tree", "soft candy tree pendant, green and brown", 0.16),
        ("pendant_flower", "soft daisy pendant, cream and lime", 0.14),
        ("pendant_bee", "soft cute bee pendant, yellow and charcoal", 0.14),
        ("pendant_butterfly", "soft butterfly pendant, pink and teal", 0.14),
        ("pendant_fish", "soft cute fish pendant, aqua candy", 0.14),
        ("pendant_cat", "soft cat-face pendant blank cute, coral cream", 0.14),
        ("pendant_dog", "soft dog-face pendant blank cute, brown cream", 0.14),
        ("pendant_frog", "soft frog-face pendant blank cute, lime candy", 0.14),
        ("pendant_duck", "soft duck pendant, yellow candy", 0.14),
        ("pendant_unicorn", "soft unicorn pendant, cream and pink", 0.16),
        ("pendant_dragon", "soft cute dragon pendant, teal candy", 0.16),
        ("pendant_phoenix", "soft phoenix pendant, coral and gold; no fire", 0.16),
        ("pendant_rainbow", "soft rainbow arch pendant, multi candy", 0.14),
        ("pendant_cloud_rain", "soft raincloud pendant, sky and aqua", 0.14),
        ("pendant_suncloud", "soft sun-behind-cloud pendant, yellow cream", 0.14),
        ("pendant_lightning", "soft rounded lightning pendant, yellow indigo", 0.14),
        ("pendant_heart_pixel", "soft pixel-heart pendant, coral candy", 0.14),
        ("pendant_star_pixel", "soft pixel-star pendant, yellow candy", 0.14),
        ("pendant_coin_stack", "soft coin-stack pendant, gold candy", 0.16),
        ("pendant_gem_cluster", "soft gem cluster pendant, teal lilac pink", 0.16),
        ("pendant_party_pop", "soft party-popper pendant, yellow pink", 0.16),
        ("pendant_confetti", "soft confetti burst pendant, rainbow candy", 0.14),
        ("pendant_hype", "soft Hype badge pendant blank stylized, coral gold", 0.16),
        ("pendant_nest", "soft nest emblem pendant, cream and coral", 0.16),
        ("pendant_pudgy", "soft simple dumpling silhouette pendant, peach candy", 0.14),
        ("beads_ocean", "chunky ocean teal cream bead collar", 0.16),
        ("beads_forest", "chunky lime olive bead collar", 0.16),
        ("beads_lava", "chunky coral charcoal bead collar", 0.16),
        ("beads_sky", "chunky sky cream bead collar", 0.16),
        ("beads_party", "chunky rainbow party bead collar oversized", 0.16),
        ("beads_gold", "chunky gold candy bead collar matte", 0.16),
        ("beads_pastel", "chunky pastel pink mint lilac bead collar", 0.16),
        ("beads_neon", "chunky neon cyan magenta bead collar matte glow", 0.16),
        ("beads_ice", "chunky ice white sky bead collar", 0.16),
        ("beads_candy", "chunky candy-cane stripe bead collar coral cream", 0.16),
        ("ribbon_cyan", "soft cyan racing ribbon necktie short", 0.16),
        ("ribbon_pink", "soft pink shooter ribbon necktie short", 0.16),
        ("ribbon_yellow", "soft yellow vibe ribbon necktie short", 0.16),
        ("ribbon_rainbow", "soft rainbow ribbon necktie short", 0.16),
        ("ribbon_gold", "soft gold medal ribbon short blank", 0.16),
        ("scarf_racer", "soft short racer scarf cyan white", 0.16),
        ("scarf_vibe", "soft short vibe scarf yellow orange", 0.16),
        ("scarf_shooter", "soft short shooter scarf pink magenta", 0.16),
        ("scarf_party", "soft short party scarf coral gold", 0.16),
        ("scarf_winter", "soft short winter scarf indigo cream", 0.16),
        ("lei_shell", "soft shell lei necklace teal cream", 0.16),
        ("lei_candy", "soft candy lei necklace rainbow sweets", 0.16),
        ("lei_light", "soft candy string-light lei, glow matte bulbs", 0.16),
        ("lei_paper", "soft paper-flower lei cream coral", 0.16),
        ("medal_bronze", "soft bronze-candy race medal on ribbon blank", 0.18),
        ("medal_silver", "soft silver-candy race medal on ribbon blank", 0.18),
        ("medal_rainbow", "soft rainbow face medal on ribbon blank", 0.18),
        ("medal_star", "soft star-shaped medal on pink ribbon", 0.18),
        ("medal_heart", "soft heart-shaped medal on cream ribbon", 0.18),
        ("medal_egg", "soft egg-shaped nest medal on pastel ribbon", 0.18),
        ("bell_gold", "soft gold jingle bell on short chain", 0.16),
        ("bell_silver", "soft silver-candy jingle bell on short chain", 0.16),
        ("bell_rainbow", "soft rainbow jingle bell on short chain", 0.16),
        ("bell_star", "soft star-shaped jingle charm on chain", 0.16),
        ("shell_pink", "soft pink shell pendant on cream chain", 0.18),
        ("shell_gold", "soft gold shell pendant on teal chain", 0.18),
        ("shell_spiral", "soft spiral candy shell on coral chain", 0.18),
        ("tooth_gold", "soft gold candy tooth charm cute", 0.14),
        ("fang_cute", "soft cute candy fang charm pair on chain", 0.14),
        ("claw_soft", "soft rounded candy claw charm, coral", 0.14),
        ("wing_charm", "soft mini wing charm pair on chain, cream pink", 0.14),
        ("halo_charm", "soft mini halo ring charm, gold candy", 0.12),
        ("horn_charm", "soft mini candy horn charm, coral", 0.14),
        ("spike_charm", "soft rounded spike charm cluster, teal", 0.14),
        ("gem_rainbow", "soft rainbow gem pendant on gold chain", 0.18),
        ("orb_teal", "soft teal glow orb pendant", 0.16),
        ("orb_pink", "soft pink glow orb pendant", 0.16),
        ("orb_lime", "soft lime glow orb pendant", 0.16),
        ("orb_indigo", "soft indigo glow orb pendant", 0.16),
        ("orb_gold", "soft gold glow orb pendant", 0.16),
        ("crystal_pink", "soft pink crystal pendant rounded", 0.16),
        ("crystal_gold", "soft gold crystal pendant rounded", 0.16),
        ("crystal_mint", "soft mint crystal pendant rounded", 0.16),
        ("flower_rose", "soft rose pendant, pink candy", 0.14),
        ("flower_tulip", "soft tulip pendant, coral candy", 0.14),
        ("flower_sun", "soft sunflower pendant, yellow candy", 0.14),
        ("flower_lotus", "soft lotus pendant, lilac candy", 0.14),
        ("flower_daisy", "soft daisy pendant, cream lime", 0.14),
        ("leaf_maple", "soft maple leaf pendant, orange candy", 0.14),
        ("leaf_ginkgo", "soft ginkgo leaf pendant, gold candy", 0.14),
        ("acorn_charm", "soft acorn pendant, brown cream", 0.14),
        ("pinecone_charm", "soft pinecone pendant, olive cream", 0.14),
        ("berry_charm", "soft berry cluster pendant, magenta", 0.14),
        ("chili_charm", "soft chili pendant cute, coral green", 0.14),
        ("mushroom_red", "soft red mushroom pendant cream spots", 0.14),
        ("mushroom_teal", "soft teal mushroom pendant cream spots", 0.14),
        ("honey_charm", "soft honey-pot pendant, amber cream", 0.16),
        ("bee_charm", "soft bee charm, yellow charcoal", 0.14),
        ("ladybug", "soft ladybug charm, coral cream spots", 0.12),
        ("snail", "soft snail charm, cream teal shell", 0.14),
        ("crab", "soft cute crab charm, coral candy", 0.14),
        ("starfish", "soft starfish pendant, peach candy", 0.14),
        ("seahorse", "soft seahorse pendant, aqua candy", 0.16),
        ("whale", "soft cute whale pendant, sky candy", 0.14),
        ("dolphin", "soft dolphin pendant, teal candy", 0.14),
        ("octopus", "soft cute octopus pendant, magenta candy", 0.14),
        ("jellyfish", "soft jelly pendant, translucent-look aqua matte", 0.16),
        ("turtle", "soft turtle pendant, lime and cream", 0.14),
        ("axolotl", "soft axolotl pendant, pink candy", 0.14),
        ("capybara", "soft capybara pendant cute, brown cream", 0.14),
        ("sloth", "soft sloth pendant cute, brown cream", 0.14),
        ("koala", "soft koala pendant cute, grey cream", 0.14),
        ("hamster", "soft hamster pendant cute, cream coral", 0.12),
        ("bunny_charm", "soft bunny pendant, cream pink", 0.14),
        ("chick_charm", "soft chick pendant, yellow candy", 0.12),
        ("penguin_charm", "soft penguin pendant, indigo cream", 0.14),
        ("owl_charm", "soft owl pendant, cream brown", 0.14),
        ("parrot", "soft parrot pendant, rainbow candy", 0.14),
        ("flamingo", "soft flamingo pendant, pink candy", 0.16),
        ("peacock_charm", "soft peacock pendant, teal gold", 0.16),
        ("toucan", "soft toucan pendant, black coral cream", 0.14),
        ("kiwi_bird", "soft kiwi-bird pendant, brown cream", 0.12),
        ("dino_charm", "soft stubby dino pendant, teal candy", 0.14),
        ("trex_cute", "soft cute t-rex pendant, lime candy", 0.14),
        ("stego", "soft stego pendant soft plates, coral candy", 0.14),
        ("pterodactyl", "soft pterodactyl pendant, sky candy", 0.14),
        ("mammoth", "soft cute mammoth pendant, brown cream", 0.14),
        ("yeti_cute", "soft cute yeti pendant, white sky", 0.14),
        ("bigfoot_cute", "soft cute bigfoot pendant, brown cream", 0.14),
        ("jackalope", "soft jackalope pendant, cream coral antlers", 0.14),
        ("narwhal", "soft narwhal pendant, aqua cream horn", 0.16),
        ("corgi", "soft corgi pendant, brown cream", 0.12),
        ("shiba", "soft shiba pendant, cream coral", 0.12),
        ("pug_cute", "soft pug pendant, cream brown; cute", 0.12),
        ("corgi_butt", "soft corgi-butt charm silly, brown cream", 0.12),
        ("bread_charm", "soft loaf pendant, cream gold", 0.12),
        ("toast_charm", "soft toast pendant with butter, cream", 0.12),
        ("egg_charm", "soft fried-egg pendant, cream yellow", 0.12),
        ("bacon_charm", "soft bacon strip pendant, coral cream", 0.12),
        ("waffle_charm", "soft waffle pendant, amber candy", 0.12),
        ("pancake", "soft pancake stack pendant, cream coral", 0.14),
        ("syrup", "soft syrup-bottle pendant, amber", 0.14),
        ("butter", "soft butter pat pendant, gold cream", 0.10),
        ("cheese_charm", "soft cheese wedge pendant, yellow", 0.12),
        ("olive_charm", "soft olive pendant, olive cream", 0.10),
        ("pickle", "soft pickle pendant, lime candy", 0.14),
        ("hotdog", "soft hotdog pendant, coral cream", 0.12),
        ("burger_charm", "soft burger pendant, warm browns green", 0.14),
        ("taco_charm", "soft taco pendant, yellow coral", 0.12),
        ("sushi_charm", "soft sushi roll pendant, teal cream", 0.12),
        ("ramen_charm", "soft ramen bowl pendant, cream coral", 0.14),
        ("dumpling_charm", "soft dumpling pendant, cream peach", 0.12),
        ("bao", "soft bao bun pendant, cream pink", 0.12),
        ("mochi_charm", "soft mochi pendant, pastel pink", 0.10),
        ("taiaki_charm", "soft fish pastry pendant, gold cream", 0.12),
        ("pudding_charm", "soft pudding cup pendant, caramel cream", 0.12),
        ("jelly_charm", "soft jelly mold pendant, coral translucent-look", 0.12),
        ("icecream_charm", "soft ice-cream cone pendant, pink cream", 0.16),
        ("popsicle_charm", "soft popsicle pendant, aqua cream", 0.16),
        ("milkshake", "soft milkshake cup pendant, pink cream", 0.16),
        ("boba", "soft boba cup pendant, tea-brown cream pearls", 0.16),
        ("coffee_charm", "soft coffee cup pendant, cream brown", 0.14),
        ("tea_charm", "soft teacup pendant, cream teal", 0.14),
        ("soda_charm", "soft soda can pendant blank, coral cream", 0.14),
        ("water_charm", "soft water bottle pendant, aqua", 0.14),
        ("juice_charm", "soft juice box pendant, orange cream", 0.14),
        ("smoothie_charm", "soft smoothie pendant, pink teal", 0.14),
        ("chocolate", "soft chocolate bar pendant, brown cream", 0.12),
        ("gummy", "soft gummy bear pendant, coral candy", 0.12),
        ("marshmallow", "soft marshmallow pendant, cream pink", 0.12),
        ("cotton_charm", "soft cotton-candy pendant, pink blue", 0.14),
        ("pretzel_charm", "soft pretzel pendant, amber", 0.12),
        ("cookie_charm", "soft cookie pendant, warm brown", 0.12),
        ("cupcake_charm", "soft cupcake pendant, pink cream", 0.14),
        ("cake_charm", "soft cake slice pendant, pink cream", 0.14),
        ("pie_charm", "soft pie slice pendant, coral cream", 0.12),
        ("donut_charm", "soft donut pendant, coral sprinkles", 0.12),
        ("macaron_charm", "soft macaron pendant, pastel pink", 0.10),
        ("brownie", "soft brownie pendant, brown cream", 0.10),
        ("fudge", "soft fudge square pendant, brown", 0.10),
        ("caramel", "soft caramel cube pendant, amber", 0.10),
        ("toffee", "soft toffee pendant, gold brown", 0.10),
        ("taffy", "soft taffy twist pendant, pink cream", 0.12),
        ("rockcandy", "soft rock-candy stick pendant, rainbow", 0.16),
        ("jawbreaker", "soft jawbreaker orb pendant, rainbow swirl", 0.12),
        ("gum", "soft gum pack pendant blank, teal cream", 0.10),
        ("mint_charm", "soft mint candy pendant, green white", 0.10),
        ("peppermint", "soft peppermint disc pendant, coral cream", 0.10),
        ("candy_cane", "soft candy-cane pendant, coral cream", 0.16),
        ("ribbon_candy", "soft ribbon-candy pendant, pastel swirl", 0.12),
        ("chocolate_coin", "soft chocolate coin pendant, gold wrap matte", 0.10),
        ("gold_foil", "soft gold-foil candy pendant, gold cream", 0.10),
        ("truffle", "soft truffle pendant, brown dust matte", 0.10),
        ("bonbon", "soft bonbon pendant, pink wrap", 0.10),
        ("praline", "soft praline pendant, cream brown", 0.10),
        ("nougat", "soft nougat bar pendant, cream nuts soft", 0.10),
        ("halva", "soft halva slice pendant, cream gold", 0.10),
        ("lokum", "soft Turkish-delight cube pendant, pink dust", 0.10),
        ("mochi_ice", "soft mochi ice-cream pendant, pastel green", 0.12),
        ("dango", "soft dango skewer pendant, pastel balls", 0.16),
        ("imagawayaki", "soft imagawayaki pendant, gold cream", 0.12),
        ("melonpan", "soft melonpan pendant, cream gold grid", 0.12),
        ("castella", "soft castella slice pendant, gold cream", 0.12),
        ("taiyaki_alt", "soft taiyaki pendant alt glaze, coral cream", 0.12),
        ("pocky", "soft stick-snack pendant, brown pink", 0.16),
        ("kit_cute", "soft wafer-stick pack pendant blank, red cream", 0.12),
        ("chip_bag", "soft chip-bag pendant blank, yellow coral", 0.14),
        ("pretzel_bag", "soft pretzel-bag pendant blank, orange cream", 0.14),
        ("cookie_box", "soft cookie-box pendant blank, teal cream", 0.14),
        ("candy_box", "soft candy-box pendant blank, pink gold", 0.14),
        ("gift_tag", "soft gift-tag pendant blank, cream coral", 0.12),
        ("balloon_dog", "soft balloon-dog charm, pink candy", 0.14),
        ("balloon_heart", "soft heart balloon charm, coral candy", 0.14),
        ("balloon_star", "soft star balloon charm, yellow candy", 0.14),
        ("balloon_party", "soft party balloon cluster charm, rainbow", 0.16),
        ("streamer", "soft streamer loop necklace, rainbow candy", 0.14),
        ("tinsel", "soft tinsel loop necklace, gold candy matte", 0.14),
        ("lights_mini", "soft mini string-light necklace, glow bulbs matte", 0.14),
        ("pom_garland", "soft pom-pom garland necklace, rainbow", 0.14),
        ("paper_chain", "soft paper-chain necklace, coral cream cyan", 0.14),
        ("bead_letter", "soft letter-bead necklace blank cute shapes not readable words", 0.14),
        ("charm_holder", "soft charm-holder necklace with three blank candy charms", 0.18),
        ("multi_charm", "soft multi-charm necklace star heart shell, gold coral teal", 0.18),
        ("layered_gold", "soft layered double candy chain gold matte", 0.16),
        ("layered_rainbow", "soft layered triple rainbow bead strands", 0.16),
        ("choker_racer", "soft cyan speed-stripe choker", 0.12),
        ("choker_vibe", "soft yellow glow-ring choker", 0.12),
        ("choker_shooter", "soft pink star choker", 0.12),
        ("choker_party", "soft coral gold party choker", 0.12),
        ("choker_ocean", "soft teal wave choker", 0.12),
        ("choker_forest", "soft lime leaf choker", 0.12),
        ("choker_lava", "soft coral ember choker; no fire", 0.12),
        ("choker_sky", "soft sky cloud choker", 0.12),
        ("choker_ice", "soft ice white sky choker", 0.12),
        ("choker_candy", "soft candy sprinkle choker pink cream", 0.12),
        ("choker_night", "soft indigo star choker", 0.12),
        ("choker_aurora", "soft aurora mint violet choker", 0.12),
        ("choker_honey", "soft honey amber choker", 0.12),
        ("choker_mint", "soft mint green white choker", 0.12),
        ("choker_berry", "soft berry magenta choker", 0.12),
        ("choker_crystal", "soft crystal teal lilac choker", 0.12),
        ("choker_bubble", "soft bubble aqua pink choker", 0.12),
        ("choker_desert", "soft sand coral choker", 0.12),
        ("choker_meadow", "soft meadow green cream choker", 0.12),
        ("choker_storm", "soft storm indigo lavender choker", 0.12),
    ]


def _shoes_items() -> list[tuple[str, str, float]]:
    themes = [
        ("ocean", "connected left+right soft ocean fin sneakers in one mesh, teal cream candy", 0.14),
        ("forest", "connected left+right soft moss sneakers in one mesh, lime olive candy", 0.14),
        ("lava", "connected left+right soft ember sneakers in one mesh, coral charcoal; no fire", 0.14),
        ("sky", "connected left+right soft cloud sneakers in one mesh, sky cream candy", 0.14),
        ("ice", "connected left+right soft frost boots in one mesh, white sky candy", 0.16),
        ("candy", "connected left+right soft sprinkle sneakers in one mesh, pink cream", 0.14),
        ("desert", "connected left+right soft sand sandals in one mesh, sand teal candy", 0.12),
        ("meadow", "connected left+right soft flower sneakers in one mesh, green cream", 0.14),
        ("storm", "connected left+right soft thunder sneakers in one mesh, indigo cream", 0.14),
        ("crystal", "connected left+right soft gem sneakers in one mesh, teal lilac", 0.14),
        ("berry", "connected left+right soft berry sneakers in one mesh, magenta cream", 0.14),
        ("bubble", "connected left+right soft bubble boots in one mesh, aqua pink", 0.16),
        ("aurora", "connected left+right soft aurora sneakers in one mesh, mint violet", 0.14),
        ("honey", "connected left+right soft honey boots in one mesh, amber cream", 0.16),
        ("mint", "connected left+right soft mint sneakers in one mesh, green white", 0.14),
        ("night", "connected left+right soft star slippers in one mesh, indigo cream", 0.12),
        ("race_pro", "connected left+right pro racing sneakers in one mesh, cyan white stripe", 0.14),
        ("vibe_glow", "connected left+right glow vibe sneakers in one mesh, yellow orange", 0.14),
        ("shooter_star", "connected left+right star sneakers in one mesh, pink magenta", 0.14),
        ("party_glitter", "connected left+right party loafers in one mesh, coral gold glitter matte", 0.12),
        ("boots_rain_teal", "connected left+right toy rain boots in one mesh, teal yellow", 0.16),
        ("boots_rain_pink", "connected left+right toy rain boots in one mesh, pink cream", 0.16),
        ("boots_work", "connected left+right soft toy work boots in one mesh, brown cream", 0.16),
        ("boots_cowboy", "connected left+right soft cowboy boots in one mesh, sand coral", 0.18),
        ("boots_space", "connected left+right soft space boots in one mesh, white cyan", 0.16),
        ("boots_knight", "connected left+right soft knight boots toy in one mesh, silver-candy coral", 0.16),
        ("slippers_bunny", "connected left+right bunny slippers in one mesh, cream pink", 0.12),
        ("slippers_bear", "connected left+right bear slippers in one mesh, brown cream", 0.12),
        ("slippers_frog", "connected left+right frog slippers in one mesh, lime candy", 0.12),
        ("slippers_duck", "connected left+right duck slippers in one mesh, yellow candy", 0.12),
        ("slippers_cat", "connected left+right cat slippers in one mesh, coral cream", 0.12),
        ("slippers_dino", "connected left+right dino slippers in one mesh, teal candy", 0.12),
        ("slippers_unicorn", "connected left+right unicorn slippers in one mesh, cream pink", 0.12),
        ("slippers_monster", "connected left+right cute monster slippers in one mesh, magenta", 0.12),
        ("sandals_beach", "connected left+right beach sandals in one mesh, aqua yellow", 0.10),
        ("sandals_sport", "connected left+right sport sandals in one mesh, coral teal", 0.10),
        ("sandals_fancy", "connected left+right fancy candy sandals in one mesh, gold cream", 0.10),
        ("heels_cute", "connected left+right stubby cute candy heels in one mesh, pink cream; chunky not sharp", 0.14),
        ("platforms", "connected left+right chunky platform shoes in one mesh, magenta cyan", 0.16),
        ("rollers", "connected left+right soft roller-skate shoes in one mesh, coral cream wheels", 0.16),
        ("inline", "connected left+right soft inline skates in one mesh, teal yellow", 0.16),
        ("ice_skates", "connected left+right soft ice-skate boots in one mesh, white sky; blunt blade candy", 0.16),
        ("ski_boots", "connected left+right soft ski boots in one mesh, indigo cream", 0.16),
        ("hike", "connected left+right soft hiking shoes in one mesh, olive cream", 0.14),
        ("trail", "connected left+right soft trail runners in one mesh, lime teal", 0.14),
        ("cleats_soft", "connected left+right soft soccer cleats toy in one mesh, white coral; soft studs", 0.14),
        ("high_tops", "connected left+right high-top sneakers in one mesh, indigo gold", 0.16),
        ("low_tops", "connected left+right low-top sneakers in one mesh, cream coral", 0.12),
        ("moccasin", "connected left+right soft moccasins in one mesh, brown cream", 0.12),
        ("loafer_gold", "connected left+right gold candy loafers in one mesh, gold coral", 0.12),
        ("loafer_teal", "connected left+right teal loafers in one mesh, teal cream", 0.12),
        ("maryjane", "connected left+right soft mary-jane shoes in one mesh, coral cream", 0.12),
        ("ballet", "connected left+right soft ballet slippers in one mesh, pink cream", 0.10),
        ("tap_cute", "connected left+right soft tap shoes toy in one mesh, black cream matte", 0.12),
        ("clog", "connected left+right soft candy clogs in one mesh, yellow coral", 0.12),
        ("crocs_cute", "connected left+right soft clog shoes with candy charms in one mesh, teal pink", 0.12),
        ("flipper_toy", "connected left+right soft swim flippers in one mesh, aqua yellow", 0.14),
        ("snow_boots", "connected left+right soft snow boots in one mesh, white coral", 0.16),
        ("moon_boots", "connected left+right soft moon boots in one mesh, silver-candy pink", 0.18),
        ("rocket_boots", "connected left+right soft rocket boots toy in one mesh, coral cyan; no real thrusters fire", 0.18),
        ("wing_shoes", "connected left+right soft winged sneakers in one mesh, cream gold", 0.14),
        ("spring_shoes", "connected left+right soft spring shoes toy in one mesh, yellow teal coils soft", 0.16),
        ("magnet_shoes", "connected left+right soft magnet sneakers in one mesh, indigo silver-candy", 0.14),
        ("glow_soles", "connected left+right sneakers with glow soles in one mesh, white cyan glow", 0.14),
        ("led_toy", "connected left+right LED-look sneakers matte painted glow in one mesh, pink cyan", 0.14),
        ("checkered", "connected left+right checkered race sneakers in one mesh, cyan white", 0.14),
        ("stripe_triple", "connected left+right triple-stripe sneakers in one mesh, coral cream", 0.14),
        ("star_print", "connected left+right star-print sneakers in one mesh, pink cream", 0.14),
        ("heart_print", "connected left+right heart-print sneakers in one mesh, magenta cream", 0.14),
        ("dot_print", "connected left+right polka-dot sneakers in one mesh, yellow teal", 0.14),
        ("camo_candy", "connected left+right candy camo sneakers in one mesh, lime coral cream", 0.14),
        ("tie_dye", "connected left+right tie-dye sneakers in one mesh, rainbow soft", 0.14),
        ("hologram", "connected left+right hologram-look sneakers matte painted sheen in one mesh, teal pink", 0.14),
        ("velvet", "connected left+right velvet-look candy loafers in one mesh, indigo gold", 0.12),
        ("denim", "connected left+right denim-look candy sneakers in one mesh, blue cream", 0.14),
        ("plaid", "connected left+right plaid candy slippers in one mesh, coral cream", 0.12),
        ("fur_soft", "connected left+right soft fur-look slippers matte painted in one mesh, cream pink", 0.12),
        ("knit", "connected left+right knit booties in one mesh, teal cream", 0.14),
        ("sock_shoes", "connected left+right thick sock-shoes in one mesh, rainbow stripes", 0.12),
        ("bare_wrap", "connected left+right soft foot wraps in one mesh, cream coral", 0.10),
        ("tabi_cute", "connected left+right soft tabi shoes in one mesh, indigo cream", 0.12),
        ("geta_cute", "connected left+right soft geta sandals toy in one mesh, wood-candy coral", 0.12),
        ("zori", "connected left+right soft zori sandals in one mesh, cream teal", 0.10),
        ("espadrille", "connected left+right soft espadrilles in one mesh, sand coral", 0.12),
        ("boat", "connected left+right soft boat shoes in one mesh, navy cream", 0.12),
        ("deck", "connected left+right soft deck shoes in one mesh, white teal", 0.12),
        ("wrestling_cute", "connected left+right soft wrestling shoes toy in one mesh, red cream", 0.12),
        ("boxing_cute", "connected left+right soft boxing boots toy in one mesh, coral cream", 0.16),
        ("cheer", "connected left+right soft cheer sneakers in one mesh, pink white", 0.14),
        ("marching", "connected left+right soft marching boots toy in one mesh, black cream matte", 0.16),
        ("parade", "connected left+right soft parade shoes in one mesh, gold coral", 0.12),
        ("clown_cute", "connected left+right oversized clown shoes cute in one mesh, rainbow; not creepy", 0.14),
        ("bigfoot", "connected left+right oversized fuzzy feet slippers in one mesh, brown cream", 0.14),
        ("chicken", "connected left+right chicken-foot slippers silly in one mesh, yellow coral", 0.12),
        ("banana_shoes", "connected left+right banana slippers in one mesh, yellow cream", 0.12),
        ("toast_shoes", "connected left+right toast slippers in one mesh, cream gold", 0.12),
        ("egg_shoes", "connected left+right egg slippers in one mesh, cream yellow", 0.12),
        ("avocado_shoes", "connected left+right avocado slippers in one mesh, lime cream", 0.12),
        ("sushi_shoes", "connected left+right sushi slippers in one mesh, teal cream", 0.12),
        ("donut_shoes", "connected left+right donut slippers in one mesh, coral cream", 0.12),
        ("cookie_shoes", "connected left+right cookie slippers in one mesh, brown cream", 0.12),
        ("cake_shoes", "connected left+right cake slippers in one mesh, pink cream", 0.12),
        ("pizza_shoes", "connected left+right pizza slippers in one mesh, coral cream", 0.12),
        ("burger_shoes", "connected left+right burger slippers in one mesh, brown green", 0.12),
        ("taco_shoes", "connected left+right taco slippers in one mesh, yellow coral", 0.12),
        ("waffle_shoes", "connected left+right waffle slippers in one mesh, amber", 0.12),
        ("lolli_shoes", "connected left+right lollipop slippers in one mesh, swirl pink", 0.12),
        ("gummy_shoes", "connected left+right gummy-bear slippers in one mesh, coral", 0.12),
        ("marsh_shoes", "connected left+right marshmallow slippers in one mesh, cream pink", 0.12),
        ("popcorn_shoes", "connected left+right popcorn slippers in one mesh, yellow coral", 0.12),
        ("icecream_shoes", "connected left+right ice-cream slippers in one mesh, pink cream", 0.12),
        ("cupcake_shoes", "connected left+right cupcake slippers in one mesh, pink cream", 0.12),
        ("boba_shoes", "connected left+right boba slippers in one mesh, tea-brown cream", 0.12),
        ("coffee_shoes", "connected left+right coffee-cup slippers in one mesh, cream brown", 0.12),
        ("tea_shoes", "connected left+right teacup slippers in one mesh, cream teal", 0.12),
        ("soda_shoes", "connected left+right soda-can slippers blank in one mesh, coral cream", 0.12),
        ("juice_shoes", "connected left+right juice-box slippers in one mesh, orange cream", 0.12),
        ("milk_shoes", "connected left+right milk-carton slippers in one mesh, cream sky", 0.12),
        ("honey_shoes", "connected left+right honey-pot slippers in one mesh, amber cream", 0.12),
        ("jam_shoes", "connected left+right jam-jar slippers in one mesh, magenta cream", 0.12),
        ("pickle_shoes", "connected left+right pickle slippers in one mesh, lime candy", 0.12),
        ("olive_shoes", "connected left+right olive slippers in one mesh, olive cream", 0.12),
        ("cheese_shoes", "connected left+right cheese slippers in one mesh, yellow", 0.12),
        ("bread_shoes", "connected left+right bread-loaf slippers in one mesh, cream gold", 0.12),
        ("bagel", "connected left+right bagel slippers in one mesh, cream gold", 0.12),
        ("pretzel_shoes", "connected left+right pretzel slippers in one mesh, amber", 0.12),
        ("croissant_shoes", "connected left+right croissant slippers in one mesh, amber", 0.12),
        ("baguette_shoes", "connected left+right baguette slippers in one mesh, cream gold", 0.12),
        ("mochi_shoes", "connected left+right mochi slippers in one mesh, pastel pink", 0.12),
        ("dango_shoes", "connected left+right dango slippers in one mesh, pastel", 0.12),
        ("onigiri_shoes", "connected left+right onigiri slippers in one mesh, cream charcoal", 0.12),
        ("ramen_shoes", "connected left+right ramen-bowl slippers in one mesh, cream coral", 0.12),
        ("dumpling_shoes", "connected left+right dumpling slippers in one mesh, cream peach", 0.12),
        ("bao_shoes", "connected left+right bao slippers in one mesh, cream pink", 0.12),
        ("takoyaki", "connected left+right takoyaki slippers in one mesh, gold cream", 0.12),
        ("tempura", "connected left+right tempura shrimp slippers silly in one mesh, gold cream", 0.12),
        ("fishcake", "connected left+right fishcake slippers in one mesh, pink cream", 0.12),
        ("narutomaki", "connected left+right narutomaki slippers in one mesh, cream pink swirl", 0.12),
        ("seaweed", "connected left+right seaweed wrap slippers in one mesh, charcoal green", 0.12),
        ("coral_shoes", "connected left+right coral-branch slippers in one mesh, peach teal", 0.12),
        ("shell_shoes", "connected left+right shell slippers in one mesh, teal cream", 0.12),
        ("pearl_shoes", "connected left+right pearl slippers in one mesh, cream pink", 0.12),
        ("star_shoes_alt", "connected left+right starfish slippers in one mesh, peach candy", 0.12),
        ("crab_shoes", "connected left+right crab slippers in one mesh, coral candy", 0.12),
        ("fish_shoes", "connected left+right fish slippers in one mesh, aqua candy", 0.12),
        ("whale_shoes", "connected left+right whale slippers in one mesh, sky candy", 0.12),
        ("dolphin_shoes", "connected left+right dolphin slippers in one mesh, teal candy", 0.12),
        ("turtle_shoes", "connected left+right turtle slippers in one mesh, lime cream", 0.12),
        ("axolotl_shoes", "connected left+right axolotl slippers in one mesh, pink candy", 0.12),
        ("frog_boots", "connected left+right frog rain boots in one mesh, lime candy", 0.16),
        ("duck_boots", "connected left+right duck rain boots in one mesh, yellow candy", 0.16),
        ("dino_boots", "connected left+right dino rain boots in one mesh, teal candy", 0.16),
        ("unicorn_boots", "connected left+right unicorn rain boots in one mesh, cream pink", 0.16),
        ("dragon_boots", "connected left+right dragon rain boots in one mesh, coral teal", 0.16),
        ("monster_boots", "connected left+right cute monster rain boots in one mesh, magenta", 0.16),
        ("robot_boots", "connected left+right robot boots toy in one mesh, silver-candy cyan", 0.16),
        ("pixel_shoes", "connected left+right pixel sneakers in one mesh, chunky coral cream", 0.14),
        ("glitch_shoes", "connected left+right glitch sneakers in one mesh, magenta cyan offsets", 0.14),
        ("neon_shoes", "connected left+right neon sneakers matte glow in one mesh, cyan pink", 0.14),
        ("disco_shoes", "connected left+right disco sneakers in one mesh, silver-candy facets matte", 0.14),
        ("mirror_shoes", "connected left+right mirror-look loafers matte painted in one mesh, cream gold", 0.12),
        ("glass_shoes", "connected left+right glass-slipper candy look matte in one mesh, aqua cream", 0.12),
        ("crystal_boots", "connected left+right crystal boots rounded in one mesh, lilac teal", 0.16),
        ("gem_shoes", "connected left+right gem sneakers in one mesh, gold teal gems soft", 0.14),
        ("crown_shoes", "connected left+right crown-crest loafers in one mesh, gold coral", 0.12),
        ("medal_shoes", "connected left+right medal-badge sneakers in one mesh, gold cyan", 0.14),
        ("trophy_shoes", "connected left+right trophy sneakers in one mesh, gold cream", 0.14),
        ("flag_shoes", "connected left+right checkered-flag sneakers in one mesh, cyan white", 0.14),
        ("whistle_shoes", "connected left+right whistle-accent sneakers in one mesh, yellow coral", 0.14),
        ("megaphone_shoes", "connected left+right megaphone sneakers silly in one mesh, coral cream", 0.14),
        ("ticket_shoes", "connected left+right ticket sneakers blank in one mesh, coral cream", 0.14),
        ("camera_shoes", "connected left+right camera sneakers in one mesh, teal cream", 0.14),
        ("music_shoes", "connected left+right music-note sneakers in one mesh, magenta cream", 0.14),
        ("game_shoes", "connected left+right controller sneakers in one mesh, teal cream", 0.14),
        ("arcade_shoes", "connected left+right arcade sneakers in one mesh, magenta cyan", 0.14),
        ("vinyl_shoes", "connected left+right vinyl-record sneakers in one mesh, charcoal coral", 0.14),
        ("cassette_shoes", "connected left+right cassette sneakers in one mesh, yellow cream", 0.14),
        ("radio_shoes", "connected left+right radio sneakers in one mesh, teal coral", 0.14),
        ("phone_shoes", "connected left+right phone sneakers blank screen in one mesh, cream teal", 0.14),
        ("wifi_shoes", "connected left+right wifi-arc sneakers in one mesh, cyan cream", 0.14),
        ("battery_shoes", "connected left+right battery sneakers in one mesh, yellow cream", 0.14),
        ("plug_shoes", "connected left+right plug sneakers toy in one mesh, coral cream", 0.14),
        ("bulb_shoes", "connected left+right lightbulb sneakers in one mesh, yellow cream", 0.14),
        ("leaf_shoes", "connected left+right leaf sneakers in one mesh, lime cream", 0.14),
        ("flower_shoes", "connected left+right flower sneakers in one mesh, pink lime", 0.14),
        ("mushroom_shoes", "connected left+right mushroom sneakers in one mesh, teal cream", 0.14),
        ("acorn_shoes", "connected left+right acorn sneakers in one mesh, brown cream", 0.14),
        ("pine_shoes", "connected left+right pinecone sneakers in one mesh, olive cream", 0.14),
        ("maple_shoes", "connected left+right maple-leaf sneakers in one mesh, orange cream", 0.14),
        ("snow_shoes", "connected left+right snowflake sneakers in one mesh, white sky", 0.14),
        ("rain_shoes", "connected left+right raindrop sneakers in one mesh, aqua white", 0.14),
        ("sun_shoes", "connected left+right sun sneakers in one mesh, yellow orange", 0.14),
        ("moon_shoes", "connected left+right moon sneakers in one mesh, indigo cream", 0.14),
        ("planet_shoes", "connected left+right planet sneakers in one mesh, teal cream", 0.14),
        ("comet_shoes", "connected left+right comet sneakers in one mesh, gold indigo", 0.14),
        ("rocket_shoes", "connected left+right rocket sneakers in one mesh, coral cyan", 0.14),
        ("ufo_shoes", "connected left+right UFO sneakers in one mesh, silver-candy teal", 0.14),
        ("alien_shoes", "connected left+right alien sneakers in one mesh, lime cream", 0.14),
        ("ghost_shoes", "connected left+right cute ghost slippers in one mesh, cream", 0.12),
        ("pumpkin_shoes", "connected left+right cute pumpkin slippers in one mesh, orange cream", 0.12),
        ("bat_shoes", "connected left+right cute bat slippers in one mesh, indigo cream", 0.12),
        ("spider_shoes", "connected left+right cute spider slippers in one mesh, charcoal coral", 0.12),
        ("skull_candy_shoes", "connected left+right cute candy skull slippers in one mesh, cream pink", 0.12),
        ("bone_shoes", "connected left+right candy bone slippers in one mesh, cream", 0.12),
        ("zombie_shoes", "connected left+right cute stitch sneakers in one mesh, lime cream; no gore", 0.14),
        ("mummy_shoes", "connected left+right bandage wrap sneakers in one mesh, cream", 0.14),
        ("vampire_shoes", "connected left+right cute vampire loafers in one mesh, indigo cream", 0.12),
        ("witch_shoes", "connected left+right cute witch boots in one mesh, purple cream", 0.16),
        ("wizard_shoes", "connected left+right cute wizard shoes in one mesh, indigo gold", 0.14),
        ("elf_shoes", "connected left+right curly elf shoes in one mesh, lime cream", 0.14),
        ("santa_shoes", "connected left+right cute santa boots in one mesh, coral cream", 0.16),
        ("reindeer", "connected left+right reindeer slippers in one mesh, brown cream", 0.12),
        ("snowman_shoes", "connected left+right snowman slippers in one mesh, cream coral", 0.12),
        ("gingerbread", "connected left+right gingerbread slippers in one mesh, brown cream", 0.12),
        ("ornament", "connected left+right ornament ball slippers in one mesh, coral gold", 0.12),
        ("stocking", "connected left+right stocking slippers in one mesh, coral cream", 0.12),
        ("gift_shoes", "connected left+right gift-box slippers in one mesh, coral gold", 0.12),
        ("tree_shoes", "connected left+right candy tree slippers in one mesh, green brown", 0.12),
        ("wreath_shoes", "connected left+right wreath slippers in one mesh, green coral", 0.12),
        ("egg_hunt", "connected left+right speckled egg slippers in one mesh, pastel cream", 0.12),
        ("bunny_shoes", "connected left+right bunny sneakers in one mesh, cream pink", 0.14),
        ("chick_shoes", "connected left+right chick sneakers in one mesh, yellow cream", 0.14),
        ("clover_shoes", "connected left+right clover sneakers in one mesh, lime cream", 0.14),
        ("heart_shoes", "connected left+right heart sneakers in one mesh, pink cream", 0.14),
        ("fireworks", "connected left+right fireworks sneakers in one mesh, gold coral bursts", 0.14),
        ("confetti_shoes", "connected left+right confetti sneakers in one mesh, rainbow", 0.14),
        ("balloon_shoes", "connected left+right balloon sneakers in one mesh, coral yellow pink", 0.14),
        ("streamer_shoes", "connected left+right streamer sneakers in one mesh, rainbow", 0.14),
        ("party_hat_shoes", "connected left+right party-hat accent sneakers in one mesh, rainbow", 0.14),
        ("crown_sneakers", "connected left+right crown sneakers in one mesh, gold coral", 0.14),
        ("nest_shoes", "connected left+right nest-egg accent sneakers in one mesh, pastel cream", 0.14),
        ("pudgy_shoes", "connected left+right dumpling silhouette sneakers in one mesh, peach cream", 0.14),
    ]
    return themes


def build_accessories() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    for slug, item, h in _hat_items():
        aid = f"acc_hat_{slug}_01"
        out.append(
            PromptEntry(
                asset_id=aid,
                category="acc_hats",
                priority=1,
                kind="accessory",
                label=slug.replace("_", " ").title(),
                prompt=_acc(item, "crown wear origin", f"About {h:.2f} m tall"),
                target_height=h,
                slot="hat",
                notes="Socket_Hat",
                job_batch="accessories",
            )
        )
    for slug, item, h in _necklace_items():
        aid = f"acc_necklace_{slug}_01"
        out.append(
            PromptEntry(
                asset_id=aid,
                category="acc_necklaces",
                priority=1,
                kind="accessory",
                label=slug.replace("_", " ").title(),
                prompt=_acc(item, "neck wear origin", f"About {h:.2f} m tall"),
                target_height=h,
                slot="necklace",
                notes="Socket_Necklace",
                job_batch="accessories",
            )
        )
    for slug, item, h in _shoes_items():
        aid = f"acc_shoes_{slug}_01"
        out.append(
            PromptEntry(
                asset_id=aid,
                category="acc_shoes",
                priority=1,
                kind="accessory",
                label=slug.replace("_", " ").title(),
                prompt=_acc(item, "floor between both shoes", f"About {h:.2f} m tall"),
                target_height=h,
                slot="shoes",
                notes="Socket_Shoes — connected pair",
                job_batch="accessories",
            )
        )

    # Back
    backs = [
        ("ocean_fins", "pair of soft ocean fin backpack wings as one mesh, teal cream", 0.40),
        ("forest_leaf", "soft leaf cape backpack, lime olive candy", 0.42),
        ("lava_cape", "soft ember cape, coral charcoal; no fire", 0.45),
        ("sky_cloud", "soft cloud backpack puff, sky cream", 0.38),
        ("ice_cape", "soft frost cape, white sky candy", 0.45),
        ("candy_bow", "oversized candy bow backpack, pink cream", 0.35),
        ("race_jet", "soft toy jetpack backpack, cyan yellow; no real flames", 0.40),
        ("vibe_speaker", "soft boombox backpack, yellow magenta", 0.38),
        ("shooter_quiver", "soft star-foam dart quiver backpack, pink cream; toy only", 0.40),
        ("party_balloon", "balloon cluster backpack, rainbow candy balloons", 0.45),
        ("angel_gold", "soft gold candy angel wings one mesh, gold cream", 0.40),
        ("bat_cute", "soft cute bat wings one mesh, indigo cream", 0.38),
        ("butterfly", "soft butterfly wings one mesh, pink teal", 0.40),
        ("dragon_wings", "soft stubby dragon wings one mesh, teal coral; cute", 0.42),
        ("bee_wings", "soft bee wings one mesh, cream yellow", 0.36),
        ("fairy", "soft fairy wings one mesh, mint lilac", 0.38),
        ("cape_race", "short race cape cyan white speed stripe", 0.45),
        ("cape_vibe", "short vibe cape yellow orange glow", 0.45),
        ("cape_shooter", "short shooter cape pink star pattern", 0.45),
        ("cape_party", "short party cape rainbow candy", 0.45),
        ("cape_gold", "short royal cape gold coral lining", 0.45),
        ("cape_invisible", "short translucent-look cape matte aqua", 0.45),
        ("pack_egg", "nest-egg backpack, pastel cream speckled", 0.36),
        ("pack_mushroom", "mushroom backpack, teal cream spots", 0.38),
        ("pack_crystal", "crystal cluster backpack rounded, lilac teal", 0.38),
        ("pack_orb", "multi-orb backpack, yellow glow candy", 0.36),
        ("pack_gift", "gift-box backpack with bow, coral gold", 0.36),
        ("pack_basket", "picnic basket backpack, cream coral", 0.36),
        ("pack_bucket", "sand bucket backpack, aqua yellow", 0.34),
        ("pack_cooler", "soft cooler backpack, teal cream", 0.36),
        ("pack_tent", "rolled tent backpack, yellow olive", 0.40),
        ("pack_sleeping", "sleeping-bag roll backpack, indigo cream", 0.38),
        ("pack_camera", "camera bag backpack, cream teal", 0.34),
        ("pack_instrument", "soft instrument case backpack, magenta cream", 0.38),
        ("pack_skate", "skateboard backpack deck, magenta cyan", 0.36),
        ("pack_surf", "surfboard backpack, aqua coral", 0.42),
        ("pack_rocket", "toy rocket backpack, coral cyan; no fire", 0.40),
        ("pack_ufo", "UFO backpack, silver-candy teal", 0.34),
        ("pack_robot", "robot pack backpack cute, cyan cream", 0.36),
        ("pack_battery", "battery pack backpack, yellow cream", 0.34),
        ("pack_toolbox", "soft toy toolbox backpack, red cream", 0.36),
        ("pack_firstaid", "soft first-aid pack, white coral cross blank", 0.34),
        ("pack_school", "soft school backpack, teal yellow", 0.38),
        ("pack_messenger", "soft messenger bag pack, brown cream", 0.36),
        ("pack_purse", "soft purse pack, coral gold", 0.32),
        ("pack_duffel", "soft duffel pack, indigo cream", 0.36),
        ("pack_suit", "soft suitcase pack mini, cream coral", 0.36),
        ("pack_treasure", "soft treasure chest pack, gold brown candy", 0.36),
        ("pack_safe", "soft safe pack, charcoal gold", 0.34),
        ("pack_piggy", "soft piggy-bank pack, pink candy", 0.34),
        ("pack_gumball", "soft gumball machine pack, teal cream", 0.38),
        ("pack_popcorn", "soft popcorn bucket pack, red white", 0.36),
        ("pack_soda", "soft soda six-pack blank, coral cream", 0.34),
        ("pack_boba", "soft boba tray pack, tea-brown cream", 0.34),
        ("pack_cake", "soft cake box pack, pink cream", 0.34),
        ("pack_pizza", "soft pizza box pack blank, coral cream", 0.32),
        ("pack_taco", "soft taco holder pack, yellow coral", 0.32),
        ("pack_burger", "soft burger box pack, brown cream", 0.32),
        ("pack_sushi", "soft sushi tray pack, teal cream", 0.32),
        ("pack_ramen", "soft ramen box pack, cream coral", 0.34),
        ("pack_honey", "soft honey crate pack, amber cream", 0.34),
        ("pack_jam", "soft jam crate pack, magenta cream", 0.34),
        ("pack_milk", "soft milk crate pack, cream sky", 0.34),
        ("pack_egg_carton", "soft egg carton pack, pastel cream", 0.30),
        ("pack_flower", "soft flower basket pack, pink lime", 0.36),
        ("pack_plant", "soft potted plant pack, teal cream", 0.38),
        ("pack_tree", "soft mini tree pack, green brown", 0.40),
        ("pack_mushroom_duo", "soft twin mushroom pack, red teal cream", 0.38),
        ("pack_crystal_duo", "soft twin crystal pack rounded, pink teal", 0.38),
        ("pack_orb_trio", "soft trio orb pack, yellow pink cyan", 0.36),
        ("pack_star_wing", "soft star-wing pack one mesh, pink gold", 0.40),
        ("pack_heart_wing", "soft heart-wing pack one mesh, pink cream", 0.40),
        ("pack_leaf_wing", "soft leaf-wing pack one mesh, lime cream", 0.40),
        ("pack_fin_wing", "soft fin-wing pack one mesh, aqua cream", 0.40),
        ("pack_ember_wing", "soft ember-wing pack one mesh, coral gold; no fire", 0.40),
        ("pack_frost_wing", "soft frost-wing pack one mesh, white sky", 0.40),
        ("pack_aurora_wing", "soft aurora-wing pack one mesh, mint violet", 0.40),
        ("pack_bubble_wing", "soft bubble-wing pack one mesh, aqua pink", 0.40),
        ("pack_candy_wing", "soft candy-wing pack one mesh, sprinkle pink", 0.40),
        ("pack_party_cape", "layered party cape with streamers, rainbow", 0.48),
        ("pack_hero_cape", "hero cape with soft emblem blank, coral cream", 0.48),
        ("pack_villain_cute", "cute short villain cape, indigo coral; not scary", 0.45),
        ("pack_scarf_long", "long soft scarf draped backpack style, teal cream", 0.50),
        ("pack_blanket", "soft blanket roll cape, indigo cream", 0.45),
        ("pack_towel", "soft beach towel cape, yellow aqua stripes", 0.45),
        ("pack_flag_cape", "soft flag cape blank, cyan cream", 0.48),
        ("pack_banner_cape", "soft banner cape blank, coral gold", 0.48),
        ("pack_checkered", "soft checkered race cape, cyan white", 0.45),
        ("pack_target", "soft star-target shield pack, pink cream", 0.36),
        ("pack_cover", "soft mini cover-block pack, teal candy", 0.34),
        ("pack_cone", "soft race-cone pack, coral white", 0.34),
        ("pack_ramp", "soft mini ramp pack, teal yellow", 0.32),
        ("pack_checkpoint", "soft mini arch pack, cyan candy", 0.36),
        ("pack_pad", "soft mode-pad disc pack thin, rainbow candy", 0.28),
        ("pack_trophy", "soft trophy pack, gold cream", 0.40),
        ("pack_medal_rack", "soft medal rack pack with blank medals, gold cyan", 0.38),
        ("pack_crown_case", "soft crown display pack, gold coral", 0.36),
        ("pack_nest_emblem", "soft nest emblem shield pack, cream coral", 0.36),
        ("pack_pudgy", "soft dumpling plush pack, peach cream", 0.36),
        ("pack_hype", "soft Hype meter pack blank stylized, coral gold", 0.36),
        ("pack_season", "soft season badge pack blank, teal cream", 0.34),
        ("pack_boing", "soft Boing coin stack pack, gold cream", 0.34),
        ("pack_wallet_nft", "soft wallet badge pack blank, indigo gold", 0.32),
        ("pack_photo", "soft photo-frame pack blank, cream coral", 0.34),
        ("pack_poster", "soft rolled poster pack blank, teal cream", 0.38),
        ("pack_map", "soft map tube pack blank, cream coral", 0.38),
        ("pack_scroll", "soft scroll pack blank, cream gold", 0.38),
        ("pack_book", "soft book stack pack, cream coral spines blank", 0.36),
        ("pack_laptop", "soft laptop pack closed blank, silver-candy teal", 0.32),
        ("pack_tablet", "soft tablet pack blank, cream cyan", 0.30),
        ("pack_console", "soft game console pack, magenta cream", 0.32),
        ("pack_arcade_stick", "soft arcade stick pack, black coral matte", 0.34),
        ("pack_drums", "soft mini drum pack, coral cream", 0.34),
        ("pack_guitar", "soft mini guitar pack, wood-candy coral", 0.40),
        ("pack_keytar", "soft keytar pack, magenta cyan", 0.40),
        ("pack_sax", "soft toy sax pack, gold candy", 0.40),
        ("pack_trumpet", "soft toy trumpet pack, gold candy", 0.38),
        ("pack_violin", "soft toy violin pack, wood-candy cream", 0.40),
        ("pack_harp", "soft toy harp pack, gold cream", 0.42),
        ("pack_maracas", "soft maracas pair pack, coral yellow", 0.34),
        ("pack_tambourine", "soft tambourine pack, cream coral", 0.32),
        ("pack_xylophone", "soft xylophone pack, rainbow candy bars", 0.34),
        ("pack_synth", "soft synth pack, indigo pink", 0.32),
        ("pack_speaker_duo", "soft twin speaker pack, yellow magenta", 0.36),
        ("pack_lights", "soft party light bar pack, rainbow glow matte", 0.34),
        ("pack_disco", "soft disco ball pack, silver-candy facets matte", 0.34),
        ("pack_fog", "soft cute fog machine pack, cream teal; no scary smoke", 0.34),
        ("pack_confetti_cannon", "soft confetti cannon pack, yellow pink; toy", 0.38),
        ("pack_bubble_gun", "soft bubble-gun pack toy, aqua pink", 0.36),
        ("pack_water_gun", "soft water-gun pack toy, cyan yellow; clearly toy", 0.36),
        ("pack_foam_bat", "soft foam bat pack, pink cream; toy", 0.40),
        ("pack_foam_sword", "soft foam sword pack, coral gold; blunt toy", 0.42),
        ("pack_foam_shield", "soft foam shield pack, teal cream", 0.36),
        ("pack_wand_back", "soft wand holster pack, gold star", 0.38),
        ("pack_staff", "soft cute staff pack, wood-candy teal gem", 0.50),
        ("pack_trident", "soft toy trident pack, gold teal", 0.48),
        ("pack_bow", "soft toy bow pack, wood-candy coral", 0.40),
        ("pack_sling", "soft toy sling pack, cream teal", 0.34),
        ("pack_boomerang", "soft toy boomerang pack, coral cream", 0.32),
        ("pack_frisbee", "soft frisbee pack, yellow cyan", 0.28),
        ("pack_ball", "soft beach ball pack, coral yellow aqua", 0.32),
        ("pack_yo", "soft yo-yo pack, coral cream", 0.28),
        ("pack_kite", "soft kite pack with tail, cyan yellow", 0.42),
        ("pack_balloon_animal", "soft balloon-animal pack, pink candy", 0.36),
        ("pack_plush", "soft plush buddy pack blank cute, cream coral", 0.36),
        ("pack_teddy", "soft teddy pack, brown cream", 0.36),
        ("pack_dino_plush", "soft dino plush pack, teal candy", 0.36),
        ("pack_unicorn_plush", "soft unicorn plush pack, cream pink", 0.36),
        ("pack_dragon_plush", "soft dragon plush pack, coral teal", 0.36),
        ("pack_ghost_plush", "soft cute ghost plush pack, cream", 0.34),
        ("pack_pumpkin_plush", "soft pumpkin plush pack, orange cream", 0.34),
        ("pack_snowman_plush", "soft snowman plush pack, cream coral", 0.36),
        ("pack_tree_plush", "soft candy tree plush pack, green brown", 0.38),
        ("pack_star_plush", "soft star plush pack, yellow candy", 0.32),
        ("pack_heart_plush", "soft heart plush pack, pink candy", 0.32),
        ("pack_moon_plush", "soft moon plush pack, cream indigo", 0.32),
        ("pack_sun_plush", "soft sun plush pack, yellow orange", 0.32),
        ("pack_cloud_plush", "soft cloud plush pack, sky cream", 0.32),
        ("pack_rainbow_plush", "soft rainbow arch plush pack, multi candy", 0.34),
    ]
    for slug, item, h in backs:
        out.append(
            PromptEntry(
                asset_id=f"acc_back_{slug}_01",
                category="acc_back",
                priority=1,
                kind="accessory",
                label=slug.replace("_", " ").title(),
                prompt=_acc(item, "upper-back wear origin", f"About {h:.2f} m tall"),
                target_height=h,
                slot="back",
                notes="Socket_Back",
                job_batch="accessories",
            )
        )

    faces = [
        ("ocean_mask", "soft ocean wave half-mask, teal cream; cute", 0.14),
        ("forest_mask", "soft leaf half-mask, lime olive; cute", 0.14),
        ("lava_mask", "soft ember half-mask, coral charcoal; cute no fire", 0.14),
        ("sky_mask", "soft cloud half-mask, sky cream; cute", 0.14),
        ("ice_mask", "soft frost half-mask, white sky; cute", 0.14),
        ("candy_mask", "soft sprinkle half-mask, pink cream; cute", 0.14),
        ("race_visor", "soft racing visor shades, cyan white", 0.12),
        ("vibe_shades", "soft oversized vibe shades, yellow orange lenses candy", 0.12),
        ("shooter_shades", "soft star shades, pink magenta lenses candy", 0.12),
        ("party_shades", "soft rainbow party shades, multi candy lenses", 0.12),
        ("heart_shades", "soft heart-shaped shades, pink lenses", 0.12),
        ("star_shades", "soft star-shaped shades, yellow lenses", 0.12),
        ("round_shades", "soft round toy shades, black gold", 0.12),
        ("square_shades", "soft square toy shades, teal cream", 0.12),
        ("aviator", "soft aviator shades toy, gold teal lenses", 0.12),
        ("cat_eye", "soft cat-eye shades, coral cream", 0.12),
        ("monocle", "soft monocle on candy chain, gold cream", 0.10),
        ("goggles_swim", "soft swim goggles, aqua lenses candy", 0.12),
        ("goggles_ski", "soft ski goggles, white sky lenses", 0.14),
        ("goggles_night", "soft night goggles toy, indigo lime lenses; cute", 0.14),
        ("goggles_sci", "soft scientist goggles, teal clear-look matte", 0.14),
        ("goggles_pilot", "soft pilot goggles, cream brown strap", 0.14),
        ("goggles_steam", "soft steampunk goggles cute, gold teal; toy", 0.14),
        ("mask_hero", "soft hero eye-mask, coral cream", 0.12),
        ("mask_sidekick", "soft sidekick eye-mask, yellow cyan", 0.12),
        ("mask_ninja", "soft ninja eye-wrap, indigo; cute not scary", 0.10),
        ("mask_bandit", "soft bandit eye-mask, charcoal cream; cute", 0.10),
        ("mask_domino", "soft domino mask, black white candy", 0.12),
        ("mask_masquerade", "soft masquerade half-mask with candy gems, gold pink", 0.14),
        ("mask_fox", "soft fox half-mask, coral cream; cute", 0.14),
        ("mask_cat", "soft cat half-mask, cream coral; cute", 0.14),
        ("mask_owl", "soft owl half-mask, cream brown; cute", 0.14),
        ("mask_frog", "soft frog half-mask, lime candy; cute", 0.14),
        ("mask_bunny", "soft bunny half-mask, cream pink; cute", 0.14),
        ("mask_bear", "soft bear half-mask, brown cream; cute", 0.14),
        ("mask_panda", "soft panda half-mask, cream charcoal; cute", 0.14),
        ("mask_dino", "soft dino half-mask, teal candy; cute", 0.14),
        ("mask_dragon", "soft dragon half-mask, coral teal; cute", 0.14),
        ("mask_unicorn", "soft unicorn half-mask, cream pink; cute", 0.14),
        ("mask_alien", "soft alien half-mask, lime cream; cute", 0.14),
        ("mask_robot", "soft robot visor mask, cyan cream; cute", 0.14),
        ("mask_ghost", "soft ghost half-mask, cream; cute not scary", 0.14),
        ("mask_pumpkin", "soft pumpkin half-mask, orange cream; cute blank", 0.14),
        ("mask_skull_candy", "soft candy skull half-mask smile, cream pink; not scary", 0.14),
        ("mask_clown_cute", "soft clown half-mask cute, coral cream; not creepy", 0.14),
        ("mask_mime", "soft mime half-mask, white charcoal; cute", 0.14),
        ("mask_jester", "soft jester half-mask, rainbow candy", 0.14),
        ("mask_pharaoh", "soft pharaoh eye-mask toy, gold teal; respectful stylized", 0.14),
        ("mask_samurai", "soft samurai half-mask toy, teal gold; family toy", 0.14),
        ("mask_knight", "soft knight visor mask toy, silver-candy coral", 0.14),
        ("mask_viking", "soft viking half-mask cute, cream coral", 0.14),
        ("nose_clown", "soft clown nose prop only, coral candy sphere", 0.08),
        ("nose_pig", "soft pig snout prop only, pink candy", 0.08),
        ("nose_witch", "soft cute witch nose prop, cream; not scary", 0.08),
        ("mustache", "soft toy mustache prop, charcoal candy", 0.06),
        ("mustache_curl", "soft curly mustache prop, brown candy", 0.06),
        ("beard_cute", "soft stubby beard prop, brown cream; cute", 0.10),
        ("whiskers", "soft whisker prop set, cream charcoal", 0.08),
        ("blush_stickers", "soft blush sticker discs pair as one mesh, pink candy", 0.06),
        ("freckle_stickers", "soft freckle sticker sheet prop, coral dots", 0.06),
        ("star_stickers", "soft star sticker props as one mesh, yellow candy", 0.08),
        ("heart_stickers", "soft heart sticker props as one mesh, pink candy", 0.08),
        ("tear_cute", "soft cute tear-drop prop, aqua candy", 0.06),
        ("sweat_cute", "soft cute sweat-drop prop, sky candy", 0.06),
        ("anger_vein_cute", "soft cute anger-mark prop, coral candy; playful", 0.06),
        ("sleep_zzz", "soft ZZZ prop near face origin, indigo cream", 0.10),
        ("bubble_gum", "soft bubble-gum bubble prop, pink candy", 0.10),
        ("lolli_mouth", "soft lollipop held at snout origin, swirl pink", 0.12),
        ("pipe_bubbles", "soft bubble pipe toy, cream aqua; cute", 0.12),
        ("flower_nose", "soft flower on snout prop, cream lime", 0.10),
        ("bow_face", "soft face bow prop, pink candy", 0.10),
        ("bandage_cute", "soft cute bandage strip prop, cream coral", 0.06),
        ("eyepatch_cute", "soft cute eyepatch, charcoal coral; playful", 0.08),
        ("scar_sticker", "soft cute stitch sticker prop, cream teal; no gore", 0.06),
        ("jewel_forehead", "soft forehead jewel prop, teal gold", 0.08),
        ("bindi_cute", "soft cute bindi jewel prop, coral gold; respectful stylized", 0.06),
        ("third_eye_cute", "soft cute third-eye jewel prop, indigo gold; playful", 0.08),
        ("antenna_face", "soft alien antenna prop pair as one mesh, lime cream", 0.14),
        ("horn_face", "soft mini horn prop pair as one mesh, coral cream", 0.12),
        ("halo_face", "soft mini halo prop floating at face origin, gold candy", 0.10),
        ("crown_mini_face", "soft mini crown at face/forehead origin, gold coral", 0.10),
        ("headphones_face", "soft mini headphone cups at face origin, indigo coral", 0.12),
        ("earring_hoop", "soft hoop earring pair as one mesh, gold candy", 0.10),
        ("earring_star", "soft star earring pair as one mesh, yellow candy", 0.10),
        ("earring_shell", "soft shell earring pair as one mesh, teal cream", 0.10),
        ("earring_candy", "soft candy earring pair as one mesh, pink cream", 0.10),
        ("earring_gem", "soft gem earring pair as one mesh, lilac gold", 0.10),
        ("earring_feather", "soft feather earring pair as one mesh, coral cream", 0.12),
        ("earring_bell", "soft bell earring pair as one mesh, gold candy", 0.10),
        ("earring_heart", "soft heart earring pair as one mesh, pink candy", 0.10),
        ("earring_bolt", "soft bolt earring pair as one mesh, yellow indigo", 0.10),
        ("earring_moon", "soft moon earring pair as one mesh, cream indigo", 0.10),
        ("earring_planet", "soft planet earring pair as one mesh, teal cream", 0.10),
        ("earring_dice", "soft dice earring pair as one mesh, cream coral", 0.10),
        ("earring_note", "soft music-note earring pair as one mesh, magenta", 0.10),
        ("earring_game", "soft controller earring pair as one mesh, teal", 0.10),
        ("earring_pixel", "soft pixel-heart earring pair as one mesh, coral", 0.10),
        ("shades_pixel", "soft pixel shades, chunky coral cream", 0.12),
        ("shades_glitch", "soft glitch shades, magenta cyan offsets", 0.12),
        ("shades_neon", "soft neon shades matte glow, cyan pink", 0.12),
        ("shades_disco", "soft disco shades, silver-candy facets matte", 0.12),
        ("shades_mirror", "soft mirror shades matte painted, cream gold", 0.12),
        ("shades_heart_pixel", "soft pixel heart shades, pink chunky", 0.12),
        ("shades_star_pixel", "soft pixel star shades, yellow chunky", 0.12),
        ("mask_vr", "soft VR headset prop, white cyan; cute toy", 0.14),
        ("mask_ar", "soft AR glasses prop, clear-look matte teal", 0.12),
        ("mask_snorkel", "soft snorkel mask prop, aqua yellow", 0.14),
        ("mask_gas_cute", "soft cute gas-mask toy round filters, cream teal; not military scary", 0.14),
        ("mask_plague_cute", "soft cute bird-mask toy, cream coral; playful carnival not scary", 0.16),
        ("mask_oni_cute", "soft cute oni half-mask, coral cream; friendly festival", 0.14),
        ("mask_kitsune", "soft kitsune half-mask, cream coral; cute", 0.14),
        ("mask_tengu_cute", "soft cute tengu half-mask, cream coral; playful", 0.14),
        ("mask_hannya_cute", "soft stylized hannya half-mask cute not scary, cream coral", 0.14),
        ("mask_balinese", "soft friendly balinese-style half-mask blank, gold teal; respectful", 0.14),
        ("mask_african_cute", "soft friendly geometric half-mask blank, lime cream; respectful stylized", 0.14),
        ("mask_aztec_cute", "soft friendly sun half-mask blank, gold coral; respectful stylized", 0.14),
        ("mask_egyptian", "soft egyptian eye-mask toy, gold teal; respectful stylized", 0.12),
        ("mask_greek", "soft greek comedy half-mask cute, cream gold", 0.14),
        ("mask_tragedy_cute", "soft greek tragedy half-mask cute soft frown, cream gold; not scary", 0.14),
        ("mask_comedy", "soft greek comedy half-mask big smile, cream gold", 0.14),
        ("mask_venetian", "soft venetian half-mask with candy gems, cream gold", 0.14),
        ("mask_carnival", "soft carnival half-mask feathers soft, rainbow candy", 0.16),
        ("mask_daydead_cute", "soft sugar-skull half-mask colorful cute, cream pink; respectful festive", 0.14),
        ("mask_luchador", "soft luchador mask, coral teal; cute sport", 0.14),
        ("mask_hockey_cute", "soft hockey mask toy cute blank, cream teal; not horror", 0.14),
        ("mask_catcher", "soft catcher mask toy, brown cream", 0.14),
        ("mask_fencing", "soft fencing mask toy mesh look matte, silver-candy", 0.14),
        ("mask_scuba", "soft scuba mask, aqua clear-look matte", 0.14),
        ("mask_welding_cute", "soft welding mask toy up, yellow charcoal; cute builder", 0.14),
        ("mask_chef", "soft chef mask/visor, white coral", 0.12),
        ("mask_doctor_cute", "soft doctor mask toy, white teal; cute", 0.10),
        ("mask_nurse_cute", "soft nurse mask toy, white coral; cute", 0.10),
        ("mask_dentist_cute", "soft dentist visor toy, clear-look cream; cute", 0.12),
        ("mask_lab", "soft lab goggles mask, teal clear-look", 0.12),
        ("mask_hazmat_cute", "soft hazmat visor toy cute, yellow cream; not scary", 0.14),
        ("mask_astronaut_face", "soft astronaut visor insert, white cyan", 0.14),
        ("mask_pilot_oxy", "soft pilot oxygen mask toy, cream teal", 0.12),
        ("mask_gas_round", "soft round filter mask toy, charcoal cream; cute", 0.12),
        ("mask_surgical_cute", "soft surgical mask toy, teal cream; cute", 0.10),
        ("mask_cloth", "soft cloth face mask toy, coral cream patterns soft", 0.10),
        ("mask_bandana_face", "soft bandana face wrap, rainbow candy", 0.10),
        ("mask_scarf_face", "soft scarf face wrap, indigo cream", 0.12),
        ("mask_balaclava_cute", "soft balaclava toy cute openings, charcoal cream; not scary", 0.14),
        ("mask_ski_face", "soft ski face mask, white sky", 0.12),
        ("mask_neoprene", "soft neoprene half-mask toy, teal charcoal", 0.12),
        ("mask_leather_cute", "soft leather-look half-mask matte, brown cream; cute", 0.12),
        ("mask_lace", "soft lace half-mask, cream pink", 0.12),
        ("mask_sequin", "soft sequin half-mask matte candy dots, gold pink", 0.12),
        ("mask_glitter", "soft glitter half-mask matte sparkle paint, coral cream", 0.12),
        ("mask_hologram", "soft hologram half-mask matte sheen, teal pink", 0.12),
        ("mask_neon_face", "soft neon outline half-mask matte glow, cyan magenta", 0.12),
        ("mask_pixel_face", "soft pixel half-mask, chunky cream coral", 0.12),
        ("mask_glitch_face", "soft glitch half-mask, magenta cyan", 0.12),
        ("mask_error_face", "soft error-popup half-mask blank cute, cream coral", 0.12),
        ("mask_smile", "soft big-smile half-mask, yellow cream", 0.12),
        ("mask_wink", "soft wink half-mask, pink cream", 0.12),
        ("mask_cool", "soft cool shades-mask combo, black gold", 0.12),
        ("mask_shy", "soft shy blush half-mask, cream pink", 0.12),
        ("mask_sparkle_eyes", "soft sparkle-eye sticker mask, gold pink", 0.10),
        ("mask_heart_eyes", "soft heart-eye mask, pink candy", 0.10),
        ("mask_star_eyes", "soft star-eye mask, yellow candy", 0.10),
        ("mask_spiral_cute", "soft cute spiral-eye mask, teal cream; playful not dizzy-scary", 0.10),
        ("mask_x_eyes_cute", "soft cute X-eye mask, coral cream; playful KO party", 0.10),
        ("mask_dot_eyes", "soft simple dot-eye mask, cream charcoal", 0.10),
        ("mask_lash", "soft oversized lash prop pair as one mesh, charcoal candy", 0.08),
        ("mask_brow", "soft brow prop pair as one mesh, brown candy", 0.06),
        ("mask_freckle_heart", "soft heart freckle stickers, pink candy", 0.06),
        ("mask_jewel_tear", "soft jewel tear prop, teal gold", 0.08),
        ("mask_candy_tear", "soft candy tear prop, pink cream", 0.08),
        ("mask_glitter_tear", "soft glitter tear prop matte sparkle, gold", 0.08),
        ("mask_rainbow_cheek", "soft rainbow cheek streak prop, multi candy", 0.08),
        ("mask_speed_cheek", "soft cyan speed lines cheek prop", 0.08),
        ("mask_vibe_cheek", "soft yellow vibe rings cheek prop", 0.08),
        ("mask_star_cheek", "soft pink star cheek prop", 0.08),
        ("mask_party_cheek", "soft confetti cheek prop, rainbow", 0.08),
    ]
    for slug, item, h in faces:
        out.append(
            PromptEntry(
                asset_id=f"acc_face_{slug}_01",
                category="acc_face",
                priority=1,
                kind="accessory",
                label=slug.replace("_", " ").title(),
                prompt=_acc(item, "snout/eye wear origin", f"About {h:.2f} m wide"),
                target_height=h,
                slot="face",
                notes="Socket_Face",
                job_batch="accessories",
            )
        )

    hands = [
        ("ocean_fins", "connected left+right soft ocean fin mittens in one mesh, teal cream", 0.12),
        ("forest_leaf", "connected left+right soft leaf mittens in one mesh, lime olive", 0.12),
        ("lava_ember", "connected left+right soft ember mittens in one mesh, coral charcoal; no fire", 0.12),
        ("sky_cloud", "connected left+right soft cloud mittens in one mesh, sky cream", 0.12),
        ("ice_frost", "connected left+right soft frost mittens in one mesh, white sky", 0.12),
        ("candy_sprinkle", "connected left+right soft sprinkle mittens in one mesh, pink cream", 0.12),
        ("race_grip", "connected left+right soft racing grip gloves in one mesh, cyan white", 0.12),
        ("vibe_glow", "connected left+right soft glow vibe gloves in one mesh, yellow orange", 0.12),
        ("shooter_foam", "connected left+right soft foam shooter gloves in one mesh, pink magenta", 0.12),
        ("party_sparkle", "connected left+right soft party sparkle gloves in one mesh, coral gold", 0.12),
        ("mittens_heart", "connected left+right heart mittens in one mesh, pink candy", 0.12),
        ("mittens_star", "connected left+right star mittens alt in one mesh, yellow candy", 0.12),
        ("mittens_bunny", "connected left+right bunny mittens in one mesh, cream pink", 0.12),
        ("mittens_bear", "connected left+right bear mittens in one mesh, brown cream", 0.12),
        ("mittens_frog", "connected left+right frog mittens in one mesh, lime candy", 0.12),
        ("mittens_cat", "connected left+right cat mittens in one mesh, coral cream", 0.12),
        ("mittens_dino", "connected left+right dino mittens in one mesh, teal candy", 0.12),
        ("mittens_monster", "connected left+right cute monster mittens in one mesh, magenta", 0.12),
        ("gloves_box", "connected left+right soft boxing gloves toy in one mesh, coral cream", 0.14),
        ("gloves_goalie", "connected left+right soft goalie gloves toy in one mesh, teal yellow", 0.14),
        ("gloves_baseball", "connected left+right soft baseball mitt pair toy in one mesh, brown cream", 0.14),
        ("gloves_garden", "connected left+right soft garden gloves in one mesh, lime cream", 0.12),
        ("gloves_oven", "connected left+right soft oven mitts in one mesh, coral cream", 0.14),
        ("gloves_dish", "connected left+right soft dish gloves in one mesh, yellow aqua", 0.12),
        ("gloves_lab", "connected left+right soft lab gloves in one mesh, cream teal", 0.12),
        ("gloves_space", "connected left+right soft space gloves in one mesh, white cyan", 0.12),
        ("gloves_knight", "connected left+right soft knight gauntlets toy in one mesh, silver-candy coral", 0.14),
        ("gloves_wizard", "connected left+right soft wizard gloves in one mesh, indigo gold", 0.12),
        ("gloves_ninja", "connected left+right soft ninja hand wraps in one mesh, indigo; cute", 0.12),
        ("gloves_hero", "connected left+right soft hero gloves in one mesh, coral cream", 0.12),
        ("gloves_winter", "connected left+right soft winter gloves in one mesh, indigo cream", 0.12),
        ("gloves_fingerless", "connected left+right soft fingerless gloves in one mesh, charcoal coral", 0.12),
        ("gloves_lace", "connected left+right soft lace gloves in one mesh, cream pink", 0.12),
        ("gloves_opera", "connected left+right soft long opera gloves in one mesh, coral cream", 0.16),
        ("gloves_pixel", "connected left+right soft pixel gloves in one mesh, chunky cyan cream", 0.12),
        ("gloves_neon", "connected left+right soft neon gloves matte glow in one mesh, cyan pink", 0.12),
        ("gloves_disco", "connected left+right soft disco gloves in one mesh, silver-candy facets matte", 0.12),
        ("gloves_rubber", "connected left+right soft rubber toy gloves in one mesh, yellow candy", 0.12),
        ("gloves_foam_star", "connected left+right foam star gloves in one mesh, pink yellow", 0.14),
        ("gloves_foam_heart", "connected left+right foam heart gloves in one mesh, pink cream", 0.14),
        ("gloves_foam_fist", "connected left+right foam fist props in one mesh, coral cream; toy", 0.14),
        ("gloves_maraca", "connected left+right maraca hand props in one mesh, coral yellow", 0.14),
        ("gloves_pompom", "connected left+right cheer pom-poms in one mesh, rainbow candy", 0.14),
        ("gloves_flags", "connected left+right mini checkered flags in one mesh, cyan white", 0.14),
        ("gloves_signs", "connected left+right blank handheld signs in one mesh, cream coral", 0.14),
        ("gloves_fans", "connected left+right folding fans in one mesh, pink cream", 0.12),
        ("gloves_castanet", "connected left+right castanets in one mesh, wood-candy coral", 0.10),
        ("gloves_clicker", "connected left+right toy clickers in one mesh, yellow teal", 0.10),
        ("gloves_yoyo", "connected left+right yo-yos in one mesh, coral cream", 0.12),
        ("gloves_ball", "connected left+right soft balls in one mesh, yellow cyan", 0.12),
        ("gloves_frisbee", "connected left+right mini frisbees in one mesh, coral teal", 0.10),
        ("gloves_bubble", "connected left+right bubble wands in one mesh, aqua pink", 0.14),
        ("gloves_sparkler", "connected left+right soft sparkler props in one mesh, gold cream; no real fire", 0.14),
        ("gloves_glowstick", "connected left+right glowsticks in one mesh, cyan magenta", 0.14),
        ("gloves_flashlight", "connected left+right toy flashlights in one mesh, yellow cream", 0.14),
        ("gloves_camera", "connected left+right toy cameras in one mesh, teal cream", 0.12),
        ("gloves_phone", "connected left+right toy phones blank screen in one mesh, cream coral", 0.12),
        ("gloves_mic", "connected left+right toy mics in one mesh, silver-candy coral", 0.14),
        ("gloves_controller", "connected left+right toy controllers in one mesh, teal cream", 0.12),
        ("gloves_wand", "connected left+right toy wands in one mesh, gold star", 0.16),
        ("gloves_sword_foam", "connected left+right foam swords in one mesh, coral gold; blunt", 0.18),
        ("gloves_shield_foam", "connected left+right foam shields in one mesh, teal cream", 0.14),
        ("gloves_blaster", "connected left+right toy foam blasters in one mesh, pink yellow; clearly toys", 0.16),
        ("gloves_watergun", "connected left+right toy water guns in one mesh, cyan yellow", 0.16),
        ("gloves_hammer_foam", "connected left+right foam hammers in one mesh, yellow coral; toy", 0.16),
        ("gloves_bat_foam", "connected left+right foam bats in one mesh, pink cream; toy", 0.16),
        ("gloves_racket", "connected left+right toy rackets in one mesh, lime cream", 0.16),
        ("gloves_club", "connected left+right toy golf clubs in one mesh, silver-candy teal", 0.18),
        ("gloves_cue", "connected left+right toy pool cues in one mesh, wood-candy cream", 0.18),
        ("gloves_brush", "connected left+right paintbrushes in one mesh, wood coral", 0.14),
        ("gloves_crayon", "connected left+right oversized crayons in one mesh, rainbow", 0.14),
        ("gloves_pencil", "connected left+right oversized pencils in one mesh, yellow pink", 0.16),
        ("gloves_spatula", "connected left+right spatulas in one mesh, coral cream", 0.14),
        ("gloves_whisk", "connected left+right whisks in one mesh, silver-candy cream", 0.14),
        ("gloves_ladle", "connected left+right ladles in one mesh, gold cream", 0.14),
        ("gloves_tongs", "connected left+right tongs in one mesh, teal cream", 0.14),
        ("gloves_fork", "connected left+right toy forks in one mesh, silver-candy; blunt", 0.14),
        ("gloves_spoon", "connected left+right toy spoons in one mesh, gold candy", 0.14),
        ("gloves_knife_butter", "connected left+right butter knives blunt toy in one mesh, silver-candy", 0.14),
        ("gloves_chopsticks", "connected left+right chopsticks pairs in one mesh, wood-candy", 0.16),
        ("gloves_lolli", "connected left+right lollipops in one mesh, swirl pink", 0.14),
        ("gloves_icecream", "connected left+right ice-cream cones in one mesh, pink cream", 0.14),
        ("gloves_donut", "connected left+right donuts in one mesh, coral cream", 0.12),
        ("gloves_cookie", "connected left+right cookies in one mesh, brown cream", 0.10),
        ("gloves_cupcake", "connected left+right cupcakes in one mesh, pink cream", 0.12),
        ("gloves_candy", "connected left+right wrapped candies in one mesh, rainbow", 0.10),
        ("gloves_balloon", "connected left+right balloons on strings in one mesh, coral yellow", 0.16),
        ("gloves_flower", "connected left+right flower bouquets in one mesh, pink lime", 0.14),
        ("gloves_gift", "connected left+right mini gifts in one mesh, coral gold", 0.12),
        ("gloves_trophy", "connected left+right mini trophies in one mesh, gold cream", 0.14),
        ("gloves_medal", "connected left+right mini medals in one mesh, gold cyan", 0.12),
        ("gloves_ticket", "connected left+right tickets blank in one mesh, coral cream", 0.10),
        ("gloves_map", "connected left+right folded maps blank in one mesh, cream teal", 0.12),
        ("gloves_book", "connected left+right mini books blank in one mesh, cream coral", 0.12),
        ("gloves_scroll", "connected left+right scrolls blank in one mesh, cream gold", 0.14),
        ("gloves_orb", "connected left+right vibe orbs in one mesh, yellow glow", 0.12),
        ("gloves_crystal", "connected left+right crystals rounded in one mesh, teal lilac", 0.12),
        ("gloves_egg", "connected left+right nest eggs in one mesh, pastel cream", 0.12),
        ("gloves_mushroom", "connected left+right mini mushrooms in one mesh, teal cream", 0.12),
        ("gloves_cone", "connected left+right mini race cones in one mesh, coral white", 0.12),
        ("gloves_star_target", "connected left+right mini star targets in one mesh, pink cream", 0.12),
        ("gloves_dice", "connected left+right soft dice in one mesh, cream coral", 0.10),
        ("gloves_cards", "connected left+right card fans blank in one mesh, cream coral", 0.12),
        ("gloves_coins", "connected left+right coin stacks in one mesh, gold candy", 0.10),
        ("gloves_gems", "connected left+right gem clusters in one mesh, teal pink", 0.10),
        ("gloves_keys", "connected left+right keys in one mesh, gold candy", 0.12),
        ("gloves_lock", "connected left+right padlocks in one mesh, silver-candy coral", 0.12),
        ("gloves_clock", "connected left+right clocks blank in one mesh, cream gold", 0.12),
        ("gloves_compass", "connected left+right compasses blank in one mesh, gold teal", 0.12),
        ("gloves_magnet", "connected left+right horseshoe magnets in one mesh, coral cream", 0.12),
        ("gloves_battery", "connected left+right batteries in one mesh, yellow cream", 0.12),
        ("gloves_bulb", "connected left+right lightbulbs in one mesh, yellow cream", 0.12),
        ("gloves_plug", "connected left+right plugs toy in one mesh, coral cream", 0.12),
        ("gloves_wifi", "connected left+right wifi symbols props in one mesh, cyan candy", 0.12),
        ("gloves_heart", "connected left+right hearts in one mesh, pink candy", 0.10),
        ("gloves_star", "connected left+right stars in one mesh, yellow candy", 0.10),
        ("gloves_moon", "connected left+right moons in one mesh, cream indigo", 0.10),
        ("gloves_sun", "connected left+right suns in one mesh, yellow orange", 0.10),
        ("gloves_cloud", "connected left+right clouds in one mesh, sky cream", 0.10),
        ("gloves_rainbow", "connected left+right rainbow arcs in one mesh, multi candy", 0.12),
        ("gloves_lightning", "connected left+right rounded lightning bolts in one mesh, yellow indigo", 0.12),
        ("gloves_snow", "connected left+right snowflakes rounded in one mesh, white sky", 0.10),
        ("gloves_leaf", "connected left+right leaves in one mesh, lime candy", 0.10),
        ("gloves_shell", "connected left+right shells in one mesh, teal cream", 0.10),
        ("gloves_feather", "connected left+right feathers in one mesh, coral cream", 0.12),
        ("gloves_bone", "connected left+right candy bones in one mesh, cream", 0.10),
        ("gloves_skull_cute", "connected left+right cute candy skulls in one mesh, cream pink", 0.10),
        ("gloves_ghost", "connected left+right cute ghosts in one mesh, cream", 0.10),
        ("gloves_pumpkin", "connected left+right cute pumpkins in one mesh, orange cream", 0.10),
        ("gloves_bat", "connected left+right cute bats in one mesh, indigo cream", 0.10),
        ("gloves_spider", "connected left+right cute spiders in one mesh, charcoal coral", 0.10),
        ("gloves_alien", "connected left+right cute aliens in one mesh, lime cream", 0.10),
        ("gloves_robot", "connected left+right cute robots in one mesh, cyan cream", 0.10),
        ("gloves_ufo", "connected left+right mini UFOs in one mesh, silver-candy teal", 0.10),
        ("gloves_rocket", "connected left+right mini rockets in one mesh, coral cyan", 0.14),
        ("gloves_planet", "connected left+right mini planets in one mesh, teal cream", 0.10),
        ("gloves_pudgy", "connected left+right mini dumpling charms in one mesh, peach cream", 0.10),
        ("gloves_nest", "connected left+right mini nest eggs in one mesh, pastel cream", 0.10),
        ("gloves_hype", "connected left+right Hype badges blank stylized in one mesh, coral gold", 0.10),
        ("gloves_boing", "connected left+right Boing coins in one mesh, gold cream", 0.10),
    ]
    for slug, item, h in hands:
        out.append(
            PromptEntry(
                asset_id=f"acc_hands_{slug}_01",
                category="acc_hands",
                priority=1,
                kind="accessory",
                label=slug.replace("_", " ").title(),
                prompt=_acc(item, "midpoint between both hands", f"About {h:.2f} m tall"),
                target_height=h,
                slot="hands",
                notes="Socket_Hands — connected pair / dual props",
                job_batch="accessories",
            )
        )
    return out


def build_nest() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    items = [
        ("env_nest_lamp_01", "A cute candy plaza lamp for The Nest: soft rounded post and glowing globe, coral and cream", 2.2, None),
        ("env_nest_lamp_teal_01", "A cute candy plaza lamp: teal post and soft yellow glow globe", 2.2, None),
        ("env_nest_lamp_short_01", "A short candy path light: stubby post and soft glow cap, pink and cream", 1.0, None),
        ("env_nest_fountain_01", "A soft candy fountain centerpiece: rounded tiers with soft water nubs, teal and cream", 2.5, None),
        ("env_nest_arch_01", "A freestanding Nest welcome arch: soft rounded posts and arch, coral cream, blank face", 3.0, None),
        ("env_nest_arch_race_01", "A Nest arch with cyan speed-stripe candy trim for Race plaza", 3.0, None),
        ("env_nest_arch_vibe_01", "A Nest arch with yellow orange glow trim for Vibe plaza", 3.0, None),
        ("env_nest_arch_shooter_01", "A Nest arch with pink star trim for Shooter plaza", 3.0, None),
        ("env_nest_sign_blank_01", "A freestanding blank candy signboard on stubby posts, cream and coral, no readable text", 1.8, None),
        ("env_nest_sign_arrow_01", "A soft candy arrow wayfinding sign, cyan and cream, blank", 1.5, None),
        ("env_nest_sign_map_01", "A soft candy map kiosk with blank board, teal and cream", 2.0, None),
        ("env_nest_booth_shop_01", "A cute Nest shop booth stall: rounded canopy and counter, coral gold, blank signs", 2.4, None),
        ("env_nest_booth_dj_01", "A cute Nest DJ booth: soft decks and speaker nubs, indigo coral, blank", 1.8, None),
        ("env_nest_booth_photo_01", "A Nest photo booth: soft curtain frame and camera nub, cream teal", 2.2, None),
        ("env_nest_booth_claim_01", "A Nest claim / rewards booth: soft pedestal and blank board, gold coral", 2.0, None),
        ("env_nest_booth_maps_01", "A Nest Create Map booth: soft drafting desk look candy, orange cream", 1.8, None),
        ("env_nest_podium_01", "A three-tier winners podium for The Nest: soft rounded steps, gold silver bronze candy", 1.2, None),
        ("env_nest_podium_single_01", "A single soft spotlight podium disc, gold candy rim, thin", 0.3, 2.0),
        ("env_nest_bench_long_01", "A long candy plaza bench seating three, coral cream stubby legs", 0.6, None),
        ("env_nest_bench_curve_01", "A curved candy bench arc, teal cream", 0.6, None),
        ("env_nest_bench_heart_01", "A heart-shaped candy loveseat bench, pink cream", 0.7, None),
        ("env_nest_chair_01", "A single cute candy plaza chair, yellow teal", 0.8, None),
        ("env_nest_table_01", "A round candy cafe table, cream coral", 0.8, None),
        ("env_nest_umbrella_01", "A freestanding candy patio umbrella, yellow aqua stripes", 2.5, None),
        ("env_nest_planter_01", "A soft candy planter pot with stubby plant nubs, teal cream", 0.9, None),
        ("env_nest_planter_large_01", "A large candy planter with oversized soft foliage, lime coral", 1.6, None),
        ("env_nest_hedge_01", "A soft rounded hedge block for Nest plaza, lime candy", 1.2, None),
        ("env_nest_hedge_arch_01", "A soft hedge archway, lime cream", 2.5, None),
        ("env_nest_fence_01", "A soft picket fence segment, cream coral", 1.0, None),
        ("env_nest_fence_gate_01", "A soft picket fence gate, cream teal", 1.2, None),
        ("env_nest_balloon_arch_01", "A freestanding balloon arch, rainbow candy balloons", 3.0, None),
        ("env_nest_balloon_cluster_01", "A grounded balloon cluster weight, coral yellow pink", 1.8, None),
        ("env_nest_banner_pole_01", "A soft banner on a candy pole, blank face, cyan cream", 2.5, None),
        ("env_nest_flag_race_01", "A soft Race flag on pole, cyan white speed look blank", 2.5, None),
        ("env_nest_flag_vibe_01", "A soft Vibe flag on pole, yellow orange blank", 2.5, None),
        ("env_nest_flag_shooter_01", "A soft Shooter flag on pole, pink star blank", 2.5, None),
        ("env_nest_flag_party_01", "A soft Party Saga flag on pole, rainbow blank", 2.5, None),
        ("env_nest_speaker_01", "A soft candy plaza speaker stack, magenta yellow", 1.6, None),
        ("env_nest_jukebox_01", "A cute candy jukebox, coral teal glow, blank face", 1.5, None),
        ("env_nest_disco_01", "A soft disco ball on a stubby stand, silver-candy facets matte", 1.8, None),
        ("env_nest_confetti_cannon_01", "A soft confetti cannon prop on stand, yellow pink; toy", 1.4, None),
        ("env_nest_spotlight_01", "A soft stage spotlight on stand, cream gold", 2.0, None),
        ("env_nest_stage_01", "A low Nest performance stage platform, rounded candy edges, teal cream", 0.5, 4.0),
        ("env_nest_rug_01", "A flat soft Nest plaza rug disc, coral cream pattern, very thin", 0.05, 3.0),
        ("env_nest_tile_01", "A single Nest plaza floor tile prop, soft candy pattern, thin", 0.08, 2.0),
        ("env_nest_path_01", "A short Nest path segment slab, cream teal, thin", 0.1, 3.0),
        ("env_nest_bridge_01", "A short soft Nest footbridge, wood-candy and coral rails", 1.5, None),
        ("env_nest_stairs_01", "A soft Nest stair block, cream coral, about four steps", 1.2, None),
        ("env_nest_ramp_plaza_01", "A soft Nest accessibility ramp, teal yellow edge", 0.8, None),
        ("env_nest_portal_01", "A soft oval Nest portal frame standing, magenta teal glow, open center", 2.8, None),
        ("env_nest_portal_race_01", "A Race portal frame, cyan glow open center", 2.8, None),
        ("env_nest_portal_vibe_01", "A Vibe portal frame, yellow orange glow open center", 2.8, None),
        ("env_nest_portal_shooter_01", "A Shooter portal frame, pink glow open center", 2.8, None),
        ("env_nest_egg_gold_01", "A giant decorative gold candy Nest egg sculpture, speckled, no creatures emerging", 2.0, None),
        ("env_nest_egg_teal_01", "A giant decorative teal Nest egg sculpture, speckled pastel", 2.0, None),
        ("env_nest_egg_rainbow_01", "A giant decorative rainbow swirl Nest egg sculpture", 2.0, None),
        ("env_nest_egg_mini_01", "A small decorative Nest egg prop cluster base, pastel cream", 0.6, None),
        ("env_nest_statue_pudgy_01", "A soft Nest statue of a simple dumpling mascot silhouette on a low plinth-free base, peach candy, friendly", 2.2, None),
        ("env_nest_statue_star_01", "A soft oversized star statue for Nest plaza, yellow candy", 2.0, None),
        ("env_nest_statue_orb_01", "A soft oversized vibe orb statue, yellow glow candy", 1.8, None),
        ("env_nest_clock_01", "A soft Nest plaza clock tower stubby, cream gold blank face", 3.5, None),
        ("env_nest_well_01", "A soft Nest wishing well, stone-candy look matte teal cream", 1.4, None),
        ("env_nest_mailbox_01", "A soft Nest mailbox prop, coral cream", 1.3, None),
        ("env_nest_bin_01", "A soft Nest trash bin cute, teal yellow; clean look", 1.0, None),
        ("env_nest_hydrant_01", "A soft Nest toy hydrant prop, coral candy", 0.9, None),
        ("env_nest_vendor_cart_01", "A soft Nest snack cart, yellow coral blank signs", 1.6, None),
        ("env_nest_ice_cream_cart_01", "A soft Nest ice-cream cart, pink cream", 1.6, None),
        ("env_nest_balloon_cart_01", "A soft Nest balloon cart, rainbow accents", 1.6, None),
        ("env_nest_ticket_booth_01", "A soft Nest ticket booth window, coral cream blank", 2.2, None),
        ("env_nest_info_kiosk_01", "A soft Nest info kiosk touch-panel look blank, cyan cream", 1.8, None),
        ("env_nest_wardrobe_01", "A soft Nest accessories wardrobe cabinet, indigo gold", 2.0, None),
        ("env_nest_mirror_01", "A freestanding Nest vanity mirror, gold cream blank", 1.8, None),
        ("env_nest_maniquin_stand_01", "A soft accessory display stand (stand only, NO mannequin body), teal cream pegs", 1.4, None),
        ("env_nest_shelf_01", "A soft Nest display shelf, cream coral", 1.6, None),
        ("env_nest_crate_deco_01", "A soft Nest deco crate, teal candy bevels", 0.8, None),
        ("env_nest_barrel_deco_01", "A soft Nest deco barrel, wood-candy coral bands", 1.0, None),
        ("env_nest_chest_01", "A soft Nest treasure chest, gold brown candy", 0.9, None),
        ("env_nest_safe_01", "A soft Nest toy safe, charcoal gold", 1.0, None),
        ("env_nest_piggy_01", "A soft oversized Nest piggy bank, pink candy", 1.2, None),
        ("env_nest_atm_01", "A soft Nest Boing claim ATM kiosk blank, indigo gold", 1.8, None),
        ("env_nest_leaderboard_01", "A soft Nest leaderboard stand blank face, cyan cream", 2.2, None),
        ("env_nest_challenge_board_01", "A soft weekly challenge board blank, coral cream", 2.0, None),
        ("env_nest_calendar_01", "A soft Nest season calendar stand blank, teal cream", 1.8, None),
        ("env_nest_tree_candy_01", "A soft candy Nest tree with rounded canopy, lime cream trunk", 3.5, None),
        ("env_nest_tree_cloud_01", "A soft cloud-canopy Nest tree, sky cream", 3.2, None),
        ("env_nest_tree_crystal_01", "A soft crystal-canopy Nest tree rounded gems, lilac teal", 3.2, None),
        ("env_nest_tree_candy_pink_01", "A soft pink candy blossom Nest tree", 3.5, None),
        ("env_nest_rock_soft_01", "A soft candy boulder deco, teal cream rounded", 1.2, None),
        ("env_nest_rock_cluster_01", "A soft candy rock cluster, coral cream", 1.0, None),
        ("env_nest_pond_01", "A soft Nest pond disc with candy water surface, aqua cream rim, thin", 0.2, 4.0),
        ("env_nest_lily_01", "A soft oversized lily pad prop, lime candy", 0.15, 1.5),
        ("env_nest_mushroom_ring_01", "A ring of soft Nest mushrooms as one mesh, coral teal cream", 0.8, None),
        ("env_nest_flower_bed_01", "A soft Nest flower bed planter strip, pink lime cream", 0.5, 2.5),
        ("env_nest_grass_tuft_01", "A soft candy grass tuft clump, lime", 0.4, None),
        ("env_nest_bush_01", "A soft Nest bush, olive cream", 1.0, None),
        ("env_nest_bush_flower_01", "A soft flowering Nest bush, pink lime", 1.1, None),
        ("env_nest_vine_post_01", "A soft vine-wrapped candy post, lime teal", 2.0, None),
        ("env_nest_string_lights_01", "A freestanding candy string-light arch, glow bulbs matte", 2.5, None),
        ("env_nest_lantern_row_01", "A row of soft Nest lanterns on a low bar, coral cream", 1.2, None),
        ("env_nest_candle_cluster_01", "A soft Nest candle cluster prop, cream coral soft flame tips; no real fire", 0.6, None),
        ("env_nest_campfire_cute_01", "A cute Nest campfire prop with soft candy flames, coral gold; clearly toy not real fire", 0.8, None),
        ("env_nest_picnic_01", "A soft Nest picnic blanket with basket, cream coral", 0.2, 2.5),
        ("env_nest_hammock_01", "A soft Nest hammock on candy posts, teal cream", 1.4, None),
        ("env_nest_swing_01", "A soft Nest swing on an A-frame, yellow coral", 2.2, None),
        ("env_nest_seesaw_01", "A soft Nest seesaw, cyan yellow", 1.0, None),
        ("env_nest_slide_01", "A soft Nest playground slide, coral cream", 2.0, None),
        ("env_nest_climber_01", "A soft Nest climbing dome, teal yellow", 1.8, None),
        ("env_nest_sandbox_01", "A soft Nest sandbox with candy rim, sand yellow aqua", 0.4, 3.0),
        ("env_nest_pool_kiddie_01", "A soft Nest kiddie pool ring, pink aqua", 0.4, 3.0),
        ("env_nest_trampoline_01", "A soft Nest trampoline, yellow cyan", 0.6, 2.5),
        ("env_nest_bounce_castle_01", "A soft Nest bounce-castle tower stubby, rainbow candy", 2.5, None),
        ("env_nest_carousel_01", "A soft Nest mini carousel, coral cream gold", 2.2, None),
        ("env_nest_ferris_mini_01", "A soft Nest mini ferris wheel, teal yellow", 3.0, None),
        ("env_nest_wheel_fortune_01", "A soft Nest prize wheel blank segments, rainbow candy", 2.2, None),
        ("env_nest_claw_machine_01", "A soft Nest claw machine blank, magenta cyan glass-look matte", 2.0, None),
        ("env_nest_arcade_cabinet_01", "A soft Nest arcade cabinet blank screen, coral cream", 1.8, None),
        ("env_nest_air_hockey_01", "A soft Nest air-hockey table, teal cream", 0.9, None),
        ("env_nest_pingpong_01", "A soft Nest ping-pong table, teal white", 0.8, None),
        ("env_nest_foosball_01", "A soft Nest foosball table, coral cream", 0.9, None),
        ("env_nest_pool_table_01", "A soft Nest pool table, green cream wood-candy", 0.9, None),
        ("env_nest_bowling_01", "A soft Nest mini bowling lane segment, cream coral", 0.4, 4.0),
        ("env_nest_skeeball_01", "A soft Nest skee-ball machine, yellow teal", 1.6, None),
        ("env_nest_basketball_01", "A soft Nest basketball hoop on stand, coral cream", 2.5, None),
        ("env_nest_soccer_goal_01", "A soft Nest soccer goal, white teal", 1.5, None),
        ("env_nest_scoreboard_01", "A soft Nest scoreboard blank, charcoal cyan", 2.0, None),
        ("env_nest_camera_crane_01", "A soft Nest toy camera crane, cream teal", 2.5, None),
        ("env_nest_drone_stand_01", "A soft Nest drone on landing pad, cyan cream; toy", 0.8, None),
        ("env_nest_satellite_01", "A soft Nest toy satellite dish, silver-candy teal", 1.8, None),
        ("env_nest_weather_01", "A soft Nest weather vane cute, gold cream", 2.0, None),
        ("env_nest_wind_sock_01", "A soft Nest windsock on pole, coral yellow", 2.2, None),
        ("env_nest_telescope_01", "A soft Nest plaza telescope, indigo gold", 1.6, None),
        ("env_nest_observatory_01", "A soft Nest mini observatory dome, cream teal", 2.5, None),
        ("env_nest_planetarium_01", "A soft Nest planetarium orb prop, indigo cream stars soft", 2.0, None),
        ("env_nest_globe_01", "A soft Nest oversized globe, teal cream", 1.5, None),
        ("env_nest_library_cart_01", "A soft Nest book cart, cream coral spines blank", 1.4, None),
        ("env_nest_art_easel_01", "A soft Nest art easel with blank canvas, wood-candy cream", 1.8, None),
        ("env_nest_pottery_01", "A soft Nest pottery wheel prop, cream teal", 1.0, None),
        ("env_nest_loom_01", "A soft Nest craft loom, wood-candy coral", 1.4, None),
        ("env_nest_sewing_01", "A soft Nest sewing machine prop cute, cream coral", 1.0, None),
        ("env_nest_kitchen_01", "A soft Nest play kitchen, yellow coral", 1.4, None),
        ("env_nest_fridge_01", "A soft Nest toy fridge, teal cream", 1.8, None),
        ("env_nest_oven_01", "A soft Nest toy oven, coral cream", 1.2, None),
        ("env_nest_sink_01", "A soft Nest toy sink, cream aqua", 1.0, None),
        ("env_nest_bed_01", "A soft Nest nap bed / lounge, indigo cream", 0.7, None),
        ("env_nest_pillow_pile_01", "A soft Nest pillow pile, pastel candy", 0.6, None),
        ("env_nest_closet_01", "A soft Nest wardrobe closet, cream gold", 2.0, None),
        ("env_nest_dresser_01", "A soft Nest dresser, coral cream", 1.2, None),
        ("env_nest_vanity_01", "A soft Nest vanity desk, pink cream gold", 1.3, None),
        ("env_nest_rug_race_01", "A flat Race-themed Nest rug, cyan speed stripes thin", 0.05, 3.0),
        ("env_nest_rug_vibe_01", "A flat Vibe-themed Nest rug, yellow orange rings thin", 0.05, 3.0),
        ("env_nest_rug_shooter_01", "A flat Shooter-themed Nest rug, pink stars thin", 0.05, 3.0),
        ("env_nest_rug_party_01", "A flat Party Saga Nest rug, rainbow swirl thin", 0.05, 3.0),
        ("env_pad_spectate_01", "A circular floor pad for Spectate zone: soft disc raised rim, indigo cream glow, very thin about 2.5 m wide", 0.15, 2.5),
        ("env_pad_create_01", "A circular floor pad for Create Map: soft disc raised rim, orange cream glow, very thin about 2.5 m wide", 0.15, 2.5),
        ("env_pad_claim_01", "A circular floor pad for Boing claim: soft disc raised rim, gold indigo glow, very thin about 2.5 m wide", 0.15, 2.5),
        ("env_pad_wardrobe_01", "A circular floor pad for Accessories: soft disc raised rim, magenta cream glow, very thin about 2.5 m wide", 0.15, 2.5),
        ("env_pad_photo_01", "A circular floor pad for Photo spot: soft disc raised rim, teal cream glow, very thin about 2.5 m wide", 0.15, 2.5),
        ("env_pad_vip_01", "A circular floor pad for VIP lounge: soft disc raised rim, gold coral glow, very thin about 2.5 m wide", 0.15, 2.5),
    ]
    # Expand with numbered variants of flora / lamps / crates for UGC volume
    for i in range(2, 21):
        items.append(
            (
                f"env_nest_planter_{i:02d}",
                f"A soft candy Nest planter variant {i}: rounded pot with unique soft plant silhouette, rotating pastel candy palette",
                0.9 + (i % 5) * 0.1,
                None,
            )
        )
    for i in range(2, 16):
        items.append(
            (
                f"env_nest_bush_{i:02d}",
                f"A soft Nest bush variant {i}: unique rounded canopy shape, lime/olive/teal candy mix",
                0.9 + (i % 4) * 0.15,
                None,
            )
        )
    for i in range(2, 16):
        items.append(
            (
                f"env_nest_lamp_{i:02d}",
                f"A Nest plaza lamp variant {i}: unique soft post silhouette and glow globe style, candy colors",
                1.8 + (i % 5) * 0.15,
                None,
            )
        )
    for i in range(2, 13):
        items.append(
            (
                f"env_nest_crate_{i:02d}",
                f"A soft Nest deco crate variant {i}: unique candy bevel pattern and color (teal/coral/cream/yellow)",
                0.6 + (i % 4) * 0.15,
                None,
            )
        )

    for aid, desc, h, w in items:
        out.append(
            PromptEntry(
                asset_id=aid,
                category="nest",
                priority=2,
                kind="env" if aid.startswith("env_") else "prop",
                label=aid,
                prompt=_prop(desc, h, w),
                target_height=h,
                target_width=w,
                notes="The Nest hub",
                job_batch="nest",
            )
        )
    return out


def build_race() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    items = [
        ("prop_race_checkpoint_tall_01", "A tall soft race checkpoint arch, cyan candy stripes, open walk-through", 2.8, None),
        ("prop_race_checkpoint_wide_01", "A wide soft race checkpoint arch, cyan cream, open center", 2.0, None),
        ("prop_race_checkpoint_ring_01", "A soft freestanding race ring gate to drive through, cyan yellow", 2.2, None),
        ("prop_race_checkpoint_hex_01", "A soft hexagonal race gate, teal white", 2.0, None),
        ("prop_race_start_gate_01", "A soft race start gate with blank banner, cyan cream", 2.2, None),
        ("prop_race_finish_gate_01", "A soft race finish gate with blank banner, gold cyan", 2.2, None),
        ("prop_race_cone_tall_01", "A tall candy race cone, coral white stripes", 1.0, None),
        ("prop_race_cone_mini_01", "A mini candy race cone, yellow coral", 0.4, None),
        ("prop_race_cone_stripe_01", "A candy race cone with bold soft stripes, teal white", 0.7, None),
        ("prop_race_barrier_01", "A soft race barrier segment, cyan cream", 1.0, None),
        ("prop_race_barrier_curve_01", "A curved soft race barrier, teal yellow", 1.0, None),
        ("prop_race_barrier_low_01", "A low soft race curb barrier, coral cream", 0.4, None),
        ("prop_race_wall_01", "A soft race wall panel, cyan white speed marks blank", 2.0, None),
        ("prop_race_wall_boost_01", "A soft race wall with boost-stripe paint, yellow cyan", 2.0, None),
        ("prop_race_billboard_01", "A soft race billboard on posts, blank face, cyan cream", 2.5, None),
        ("prop_race_billboard_wide_01", "A wide soft race billboard blank, teal yellow", 2.2, None),
        ("prop_race_arrow_01", "A freestanding soft race direction arrow, cyan yellow", 1.2, None),
        ("prop_race_arrow_left_01", "A soft race left-turn arrow sign, coral cream", 1.2, None),
        ("prop_race_arrow_right_01", "A soft race right-turn arrow sign, coral cream", 1.2, None),
        ("prop_race_arrow_up_01", "A soft race straight arrow sign, yellow cyan", 1.2, None),
        ("env_race_ramp_steep_01", "A steep soft toy race ramp, teal yellow edge", 1.8, None),
        ("env_race_ramp_wide_01", "A wide soft race ramp, cyan cream", 1.2, None),
        ("env_race_ramp_curve_01", "A curved soft race ramp, teal coral", 1.2, None),
        ("env_race_ramp_long_01", "A long soft race ramp, yellow cyan", 1.0, None),
        ("env_race_boost_pad_01", "A flat soft race boost pad disc, yellow arrows blank, very thin about 2 m wide", 0.1, 2.0),
        ("env_race_boost_pad_cyan_01", "A flat soft race boost pad, cyan chevrons blank, thin about 2 m wide", 0.1, 2.0),
        ("env_race_slow_pad_01", "A flat soft race slow pad, coral sticky look candy, thin about 2 m wide", 0.1, 2.0),
        ("env_race_jump_pad_01", "A soft race jump pad cushion, pink cyan, about 0.4 m tall", 0.4, 2.0),
        ("env_race_bridge_01", "A soft race bridge span, wood-candy cyan rails", 2.0, None),
        ("env_race_bridge_arch_01", "A soft arched race bridge, teal cream", 2.5, None),
        ("env_race_tunnel_01", "A soft race tunnel tube segment open ends, cyan cream", 2.5, None),
        ("env_race_tunnel_stripe_01", "A soft striped race tunnel segment, yellow teal", 2.5, None),
        ("env_race_loop_quarter_01", "A soft race loop-de-loop quarter piece, coral cyan; toy track", 3.0, None),
        ("env_race_track_straight_01", "A soft race track straight segment with candy edge, cyan cream thin deck", 0.2, 4.0),
        ("env_race_track_curve_01", "A soft race track curve segment, teal yellow", 0.2, 4.0),
        ("env_race_track_s_01", "A soft race track S-curve segment, cyan coral", 0.2, 4.0),
        ("env_race_track_wide_01", "A soft wide race track segment, cream teal", 0.2, 5.0),
        ("env_race_tire_stack_01", "A soft candy tire stack (rounded toy tires), charcoal cyan; not realistic dirty", 1.5, None),
        ("env_race_tire_single_01", "A soft candy single race tire prop, charcoal yellow", 0.8, None),
        ("env_race_hay_soft_01", "A soft candy hay-bale look barrier, gold cream; matte painted not straw photo", 1.0, None),
        ("env_race_water_hazard_01", "A soft race water-hazard disc, aqua cream rim thin", 0.15, 3.0),
        ("env_race_oil_cute_01", "A soft cute race oil-slick disc, charcoal rainbow sheen matte thin", 0.08, 2.5),
        ("env_race_mud_cute_01", "A soft cute race mud patch disc, brown candy matte thin; not dirty photo", 0.1, 2.5),
        ("prop_race_banner_start_01", "A soft start banner on posts, cyan cream blank", 1.5, None),
        ("prop_race_banner_lap_01", "A soft lap banner on posts, yellow cyan blank", 1.5, None),
        ("prop_race_banner_final_01", "A soft final-lap banner on posts, coral gold blank", 1.5, None),
        ("prop_race_flag_check_01", "A soft checkered flag on pole, cyan white", 2.0, None),
        ("prop_race_flag_green_01", "A soft green start flag on pole, lime cream", 2.0, None),
        ("prop_race_flag_yellow_01", "A soft yellow caution flag on pole, yellow cream", 2.0, None),
        ("prop_race_flag_red_01", "A soft red stop flag on pole, coral cream; party race", 2.0, None),
        ("prop_race_podium_01", "A race winners podium three tiers, gold silver bronze candy", 1.2, None),
        ("prop_race_trophy_01", "A soft race trophy cup, gold cyan", 0.8, None),
        ("prop_race_trophy_grand_01", "A grand soft race trophy with handles, gold coral", 1.2, None),
        ("prop_race_medal_stand_01", "A soft race medal display stand with blank medals, gold cream", 1.4, None),
        ("prop_race_timer_01", "A soft race timer board blank, charcoal cyan", 1.6, None),
        ("prop_race_leaderboard_01", "A soft race leaderboard blank, teal cream", 2.0, None),
        ("prop_race_camera_01", "A soft race trackside camera on stand, cream teal", 1.5, None),
        ("prop_race_drone_01", "A soft race drone prop grounded, cyan yellow; toy", 0.5, None),
        ("prop_race_light_tree_01", "A soft race starting light tree, charcoal with soft candy lights", 2.2, None),
        ("prop_race_pit_sign_01", "A soft pit lane sign blank, coral cream", 1.8, None),
        ("prop_race_pit_box_01", "A soft pit box stall, cyan cream blank", 2.0, None),
        ("prop_race_fuel_cute_01", "A soft cute race fuel can toy, yellow coral; candy", 0.7, None),
        ("prop_race_wrench_cute_01", "A soft oversized toy wrench prop, silver-candy teal", 0.8, None),
        ("prop_race_jack_cute_01", "A soft toy car jack prop, coral cream", 0.6, None),
        ("prop_race_cone_row_01", "A connected row of three soft race cones as one mesh, coral white", 0.7, None),
        ("prop_race_barrier_row_01", "A connected row of soft race barriers as one mesh, cyan cream", 1.0, None),
        ("prop_race_grandstand_01", "A soft race grandstand seating block, teal cream", 2.5, None),
        ("prop_race_grandstand_small_01", "A small soft race bleacher, coral cream", 1.5, None),
        ("prop_race_umbrella_table_01", "A soft race hospitality table with umbrella, yellow cyan", 2.2, None),
        ("prop_race_cooler_01", "A soft race cooler prop, teal yellow", 0.8, None),
        ("prop_race_speaker_01", "A soft race PA speaker on stand, charcoal cyan", 1.8, None),
        ("prop_race_confetti_01", "A soft race finish confetti cannon, gold pink", 1.2, None),
        ("env_race_stripe_decal_01", "A flat soft race speed-stripe floor decal, cyan white thin about 3 m long", 0.05, 3.0),
        ("env_race_grid_01", "A flat soft starting grid decal, white cyan boxes thin about 4 m wide", 0.05, 4.0),
        ("env_race_finish_line_01", "A flat soft checkered finish line decal, cyan white thin about 4 m wide", 0.05, 4.0),
        ("env_race_number_pad_01", "A flat soft race number disc blank stylized shape not readable digits, yellow cyan thin", 0.05, 1.5),
    ]
    for i in range(2, 31):
        items.append(
            (
                f"prop_race_cone_{i:02d}",
                f"A chunky candy race cone variant {i}: unique stripe style and candy color combo (coral/cyan/yellow/white)",
                0.5 + (i % 6) * 0.08,
                None,
            )
        )
    for i in range(2, 21):
        items.append(
            (
                f"prop_race_barrier_{i:02d}",
                f"A soft race barrier segment variant {i}: unique candy bevel and color",
                0.8 + (i % 5) * 0.1,
                None,
            )
        )
    for i in range(2, 16):
        items.append(
            (
                f"env_race_ramp_{i:02d}",
                f"A soft toy race ramp variant {i}: unique slope profile and candy edge color",
                0.8 + (i % 6) * 0.15,
                None,
            )
        )
    for i in range(2, 16):
        items.append(
            (
                f"prop_race_checkpoint_{i:02d}",
                f"A soft race checkpoint arch variant {i}: unique frame silhouette, cyan candy family",
                1.8 + (i % 5) * 0.2,
                None,
            )
        )
    for i in range(2, 13):
        items.append(
            (
                f"env_race_boost_pad_{i:02d}",
                f"A flat soft race boost pad variant {i}: unique chevron pattern blank, candy glow, thin about 2 m wide",
                0.1,
                2.0,
            )
        )

    for aid, desc, h, w in items:
        out.append(
            PromptEntry(
                asset_id=aid,
                category="race",
                priority=3,
                kind="env" if aid.startswith("env_") else "prop",
                label=aid,
                prompt=_prop(desc, h, w),
                target_height=h,
                target_width=w,
                notes="Race stage kit",
                job_batch="race",
            )
        )
    return out


def build_vibe() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    colors = [
        ("yellow", "soft yellow glow"),
        ("orange", "soft orange glow"),
        ("pink", "soft pink glow"),
        ("coral", "soft coral glow"),
        ("teal", "soft teal glow"),
        ("cyan", "soft cyan glow"),
        ("lime", "soft lime glow"),
        ("mint", "soft mint glow"),
        ("lilac", "soft lilac glow"),
        ("indigo", "soft indigo glow"),
        ("gold", "soft gold glow"),
        ("cream", "soft cream glow"),
        ("rainbow", "soft rainbow swirl glow"),
        ("aurora", "soft aurora mint-violet glow"),
        ("berry", "soft berry magenta glow"),
    ]
    items: list[tuple[str, str, float, float | None]] = []
    for slug, glow in colors:
        items.append(
            (
                f"prop_vibe_orb_{slug}_01",
                f"A candy vibe collectible orb with {glow}, round cartoon candy shell, optional tiny floor stand, floaty but grounded",
                0.5,
                None,
            )
        )
        items.append(
            (
                f"prop_vibe_orb_{slug}_large_01",
                f"An oversized candy vibe orb with {glow}, round shell, grounded stand",
                1.0,
                None,
            )
        )
        items.append(
            (
                f"prop_vibe_orb_{slug}_mini_01",
                f"A mini candy vibe orb with {glow}, tiny grounded stand",
                0.25,
                None,
            )
        )

    flowers = [
        ("daisy", "oversized daisy collectible flower, cream lime petals"),
        ("rose", "oversized rose collectible flower, pink candy petals"),
        ("tulip", "oversized tulip collectible flower, coral green"),
        ("sunflower", "oversized sunflower collectible, yellow brown candy"),
        ("lotus", "oversized lotus collectible, lilac cream"),
        ("lily", "oversized lily collectible, white pink candy"),
        ("orchid", "oversized orchid collectible, magenta cream"),
        ("hibiscus", "oversized hibiscus collectible, coral yellow"),
        ("peony", "oversized peony collectible, soft pink cream"),
        ("lavender", "oversized lavender stalk cluster, lilac green"),
        ("dandelion", "oversized dandelion puff collectible, cream lime"),
        ("poppy", "oversized poppy collectible, coral cream"),
        ("marigold", "oversized marigold collectible, orange gold"),
        ("violet", "oversized violet collectible, indigo cream"),
        ("cherry_blossom", "oversized cherry blossom branch prop, pink cream"),
    ]
    for slug, desc in flowers:
        items.append((f"prop_vibe_flower_{slug}_01", f"An {desc}, thick stubby stem, cartoon candy look", 1.0, None))

    crystals = [
        ("teal", "rounded toy crystal cluster with teal emissive tips"),
        ("pink", "rounded toy crystal cluster with pink emissive tips"),
        ("gold", "rounded toy crystal cluster with gold emissive tips"),
        ("lilac", "rounded toy crystal cluster with lilac emissive tips"),
        ("mint", "rounded toy crystal cluster with mint emissive tips"),
        ("coral", "rounded toy crystal cluster with coral emissive tips"),
        ("indigo", "rounded toy crystal cluster with indigo emissive tips"),
        ("rainbow", "rounded toy crystal cluster with rainbow emissive tips"),
        ("clear", "rounded toy crystal cluster with cream clear-look matte tips"),
        ("aurora", "rounded toy crystal cluster with aurora glow tips"),
    ]
    for slug, desc in crystals:
        items.append((f"prop_vibe_crystal_{slug}_01", f"A {desc}, soft candy facets not sharp glass, friendly silhouette", 0.8, None))

    mushrooms = [
        ("red", "oversized cartoon mushroom glowing red cap cream spots"),
        ("teal", "oversized cartoon mushroom glowing teal cap"),
        ("purple", "oversized cartoon mushroom glowing purple cap"),
        ("gold", "oversized cartoon mushroom glowing gold cap"),
        ("pink", "oversized cartoon mushroom glowing pink cap"),
        ("blue", "oversized cartoon mushroom glowing blue cap"),
        ("rainbow", "oversized cartoon mushroom rainbow freckle cap"),
        ("star", "oversized cartoon mushroom star-spotted cap yellow"),
        ("heart", "oversized cartoon mushroom heart-spotted cap pink"),
        ("glow", "oversized cartoon mushroom strongly emissive lime cap"),
    ]
    for slug, desc in mushrooms:
        items.append((f"prop_vibe_mushroom_{slug}_01", f"An {desc}, thick stem, about 1.8 m tall candy look", 1.8, None))

    extras = [
        ("prop_vibe_pedestal_01", "A soft vibe collectible pedestal, cream teal glow rim", 0.6, None),
        ("prop_vibe_pedestal_gold_01", "A soft gold vibe pedestal, gold cream", 0.6, None),
        ("prop_vibe_totem_01", "A soft vibe score totem with orb niches, teal yellow", 2.2, None),
        ("prop_vibe_totem_tall_01", "A tall soft vibe totem, lilac mint", 3.0, None),
        ("prop_vibe_ring_01", "A soft freestanding vibe collect ring, yellow glow open center", 1.5, None),
        ("prop_vibe_ring_large_01", "A large soft vibe collect ring, pink glow", 2.2, None),
        ("prop_vibe_spiral_01", "A soft vibe spiral pillar, coral cream glow", 2.0, None),
        ("prop_vibe_garden_01", "A soft vibe garden planter with mixed candy flora", 1.2, None),
        ("prop_vibe_tree_01", "A soft vibe glow tree, lime canopy cream trunk", 3.0, None),
        ("prop_vibe_tree_crystal_01", "A soft vibe crystal tree, lilac teal canopy", 3.0, None),
        ("prop_vibe_bush_01", "A soft vibe glow bush, mint cream", 1.0, None),
        ("prop_vibe_grass_01", "A soft vibe grass tuft glowing tips, lime", 0.5, None),
        ("prop_vibe_path_01", "A soft vibe path stone disc row as one mesh, cream teal thin", 0.1, 3.0),
        ("prop_vibe_bridge_01", "A soft vibe garden bridge, wood-candy pink rails", 1.5, None),
        ("prop_vibe_gazebo_01", "A soft vibe gazebo, cream coral", 2.5, None),
        ("prop_vibe_fountain_01", "A soft vibe fountain with orb water nubs, teal yellow", 2.0, None),
        ("prop_vibe_bench_01", "A soft vibe garden bench, lime cream", 0.6, None),
        ("prop_vibe_lantern_01", "A soft vibe garden lantern on post, yellow glow", 1.8, None),
        ("prop_vibe_lantern_hang_01", "A soft vibe hanging lantern on stand, pink glow", 2.0, None),
        ("prop_vibe_windchime_01", "A soft vibe wind chime on stand, teal cream", 1.8, None),
        ("prop_vibe_mobile_01", "A soft vibe hanging mobile on stand with orbs, rainbow", 2.2, None),
        ("prop_vibe_score_board_01", "A soft vibe score board blank, yellow cream", 1.8, None),
        ("prop_vibe_spawn_marker_01", "A flat soft vibe spawn marker disc, yellow rings thin about 1.5 m wide", 0.05, 1.5),
        ("prop_vibe_trail_marker_01", "A soft vibe trail marker post with orb top, teal yellow", 1.2, None),
        ("prop_vibe_basket_01", "A soft vibe collect basket, cream coral", 0.7, None),
        ("prop_vibe_jar_01", "A soft vibe orb jar display, glass-look matte aqua", 0.9, None),
        ("prop_vibe_shelf_01", "A soft vibe orb display shelf, cream teal", 1.4, None),
        ("prop_vibe_altar_01", "A soft vibe offer altar with crystal niche, lilac gold", 1.0, None),
        ("prop_vibe_mirror_pond_01", "A soft vibe mirror pond disc, aqua cream thin", 0.15, 3.0),
        ("prop_vibe_stepping_01", "A set of soft vibe stepping stones as one mesh, cream teal", 0.2, None),
        ("prop_vibe_arch_flower_01", "A soft flower arch for vibe garden, pink lime", 2.8, None),
        ("prop_vibe_arch_crystal_01", "A soft crystal arch for vibe garden, teal lilac", 2.8, None),
        ("prop_vibe_gate_01", "A soft vibe garden gate, cream coral", 2.0, None),
        ("prop_vibe_fence_01", "A soft vibe garden fence segment, lime cream", 1.0, None),
        ("prop_vibe_sign_01", "A soft vibe garden sign blank, yellow cream", 1.5, None),
        ("prop_vibe_map_01", "A soft vibe garden map kiosk blank, teal cream", 1.8, None),
        ("prop_vibe_clock_01", "A soft vibe garden clock blank, cream gold", 1.6, None),
        ("prop_vibe_bee_hive_01", "A soft cute vibe bee hive prop, amber cream", 1.2, None),
        ("prop_vibe_butterfly_01", "A soft oversized vibe butterfly deco on stand, pink teal", 1.5, None),
        ("prop_vibe_snail_01", "A soft oversized vibe snail deco, cream teal shell", 1.0, None),
        ("prop_vibe_frog_deco_01", "A soft oversized vibe frog deco statue, lime candy", 1.2, None),
        ("prop_vibe_birdbath_01", "A soft vibe birdbath, cream aqua", 1.0, None),
        ("prop_vibe_watering_01", "A soft vibe watering can prop oversized, yellow teal", 0.9, None),
        ("prop_vibe_wheelbarrow_01", "A soft vibe wheelbarrow with flora, lime cream", 1.0, None),
        ("prop_vibe_compost_cute_01", "A soft cute vibe compost bin, green cream; clean candy", 1.0, None),
        ("prop_vibe_greenhouse_01", "A soft vibe mini greenhouse, aqua cream glass-look matte", 2.2, None),
        ("prop_vibe_pot_stack_01", "A soft stacked flower pot tower, coral cream", 1.4, None),
        ("prop_vibe_seed_bag_01", "A soft vibe seed bag prop blank, cream lime", 0.7, None),
        ("prop_vibe_shovel_01", "A soft oversized vibe shovel prop, wood-candy teal", 1.2, None),
        ("prop_vibe_rake_01", "A soft oversized vibe rake prop, wood-candy lime", 1.2, None),
        ("prop_vibe_hose_01", "A soft coiled vibe hose prop, aqua yellow", 0.6, None),
        ("prop_vibe_sprinkler_01", "A soft vibe sprinkler prop, teal cream", 0.5, None),
        ("prop_vibe_cloud_deco_01", "A soft grounded vibe cloud deco on stubby stand, sky cream", 1.5, None),
        ("prop_vibe_rainbow_arch_01", "A soft vibe rainbow arch deco, multi candy", 2.5, None),
        ("prop_vibe_sun_deco_01", "A soft vibe sun deco on stand, yellow orange", 1.8, None),
        ("prop_vibe_moon_deco_01", "A soft vibe moon deco on stand, cream indigo", 1.8, None),
        ("prop_vibe_star_deco_01", "A soft vibe star deco on stand, gold pink", 1.5, None),
        ("prop_vibe_combo_orb_flower_01", "A soft vibe combo prop: orb resting in flower cup, yellow pink", 1.0, None),
        ("prop_vibe_combo_crystal_orb_01", "A soft vibe combo prop: orb inside crystal nest, teal yellow", 1.0, None),
    ]
    items.extend(extras)

    for i in range(2, 41):
        items.append(
            (
                f"prop_vibe_orb_var_{i:02d}",
                f"A candy vibe collectible orb variant {i}: unique shell pattern and soft glow candy color, grounded stand",
                0.4 + (i % 5) * 0.1,
                None,
            )
        )
    for i in range(2, 21):
        items.append(
            (
                f"prop_vibe_flower_var_{i:02d}",
                f"An oversized vibe flower variant {i}: unique petal silhouette and candy palette",
                0.8 + (i % 5) * 0.1,
                None,
            )
        )

    for aid, desc, h, w in items:
        out.append(
            PromptEntry(
                asset_id=aid,
                category="vibe",
                priority=3,
                kind="prop",
                label=aid,
                prompt=_prop(desc, h, w),
                target_height=h,
                target_width=w,
                notes="Vibe Collect stage kit",
                job_batch="vibe",
            )
        )
    return out


def build_shooter() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    items: list[tuple[str, str, float, float | None]] = [
        ("prop_cover_block_wide_01", "A wide rounded soft cover block for party shooter, teal candy bevels", 1.2, None),
        ("prop_cover_block_tall_01", "A tall rounded soft cover block, coral candy", 1.8, None),
        ("prop_cover_block_low_01", "A low soft cover block / curb, yellow teal", 0.6, None),
        ("prop_cover_block_round_01", "A round soft cover cylinder, pink cream", 1.2, None),
        ("prop_cover_block_L_01", "An L-shaped soft cover block as one mesh, cyan cream", 1.2, None),
        ("prop_cover_block_T_01", "A T-shaped soft cover block as one mesh, coral teal", 1.2, None),
        ("prop_cover_block_ramp_01", "A soft cover block with ramp face, yellow pink", 1.2, None),
        ("prop_cover_block_window_01", "A soft cover block with cute window cutout, teal cream", 1.4, None),
        ("prop_cover_block_door_01", "A soft cover block with arch doorway, coral cream", 1.6, None),
        ("prop_cover_crate_01", "A soft shooter crate cover, teal candy", 1.0, None),
        ("prop_cover_barrel_01", "A soft shooter barrel cover, wood-candy pink bands", 1.1, None),
        ("prop_cover_bag_01", "A soft sandbag-look candy cover stack, cream coral; matte not dirty", 0.9, None),
        ("prop_target_star_large_01", "A large soft star pop target on stand, cream coral", 1.5, None),
        ("prop_target_star_mini_01", "A mini soft star pop target on stand, pink cream", 0.6, None),
        ("prop_target_circle_01", "A soft circle pop target on stand, yellow coral rings blank", 1.0, None),
        ("prop_target_heart_01", "A soft heart pop target on stand, pink cream", 1.0, None),
        ("prop_target_orb_01", "A soft orb pop target on stand, teal yellow", 1.0, None),
        ("prop_target_diamond_01", "A soft diamond pop target on stand, lilac cream", 1.0, None),
        ("prop_target_moving_look_01", "A soft target on a candy rail sled (static mesh), pink cyan", 1.2, None),
        ("prop_target_duo_01", "A dual star target on one stand as one mesh, coral cream", 1.3, None),
        ("prop_target_trio_01", "A triple mini target stand as one mesh, yellow pink teal", 1.4, None),
        ("prop_blaster_toy_pink_01", "A chunky foam toy blaster decoration, pink yellow rounded nozzle; clearly soft party toy not realistic weapon", 0.4, None),
        ("prop_blaster_toy_cyan_01", "A chunky foam toy blaster, cyan yellow; clearly toy", 0.4, None),
        ("prop_blaster_toy_lime_01", "A chunky foam toy blaster, lime coral; clearly toy", 0.4, None),
        ("prop_blaster_toy_gold_01", "A chunky foam toy blaster, gold cream; clearly toy", 0.4, None),
        ("prop_blaster_toy_mega_01", "An oversized foam toy blaster prop, pink cyan; clearly toy", 0.7, None),
        ("prop_blaster_toy_dual_01", "A dual-nozzle foam toy blaster, yellow magenta; clearly toy", 0.45, None),
        ("prop_foam_dart_crate_01", "A soft crate of foam darts (blunt tips), pink cream; toy ammo box", 0.8, None),
        ("prop_foam_shield_01", "A soft foam shooter shield prop, teal cream", 1.0, None),
        ("prop_foam_bat_01", "A soft foam bat prop, pink yellow; toy", 0.9, None),
        ("prop_water_gun_toy_01", "A soft toy water gun prop, aqua yellow; clearly toy", 0.4, None),
        ("prop_bubble_blaster_01", "A soft bubble blaster toy prop, pink aqua", 0.4, None),
        ("prop_cover_wall_01", "A soft shooter arena wall panel, pink cream", 2.2, None),
        ("prop_cover_wall_star_01", "A soft shooter wall with star pattern, magenta cream", 2.2, None),
        ("prop_cover_wall_window_01", "A soft shooter wall with window, teal pink", 2.2, None),
        ("prop_cover_corner_01", "A soft shooter corner cover piece, coral cyan", 1.4, None),
        ("prop_cover_bunker_01", "A soft shooter bunker hood, yellow teal", 1.5, None),
        ("prop_cover_tower_01", "A soft short shooter cover tower, pink cream", 2.0, None),
        ("env_shooter_spawn_pad_01", "A flat soft shooter spawn pad disc, pink star pattern thin about 2 m wide", 0.1, 2.0),
        ("env_shooter_bounce_pad_01", "A soft shooter bounce pad cushion, yellow pink", 0.4, 2.0),
        ("env_shooter_speed_pad_01", "A flat soft shooter speed pad, cyan pink thin about 2 m wide", 0.1, 2.0),
        ("env_shooter_heal_pad_01", "A flat soft shooter heal pad, mint cream plus blank thin about 2 m wide", 0.1, 2.0),
        ("env_shooter_hazard_pad_01", "A flat soft shooter hazard pad cute, coral warning stripes thin about 2 m wide", 0.1, 2.0),
        ("vfx_ko_burst_pink_01", "A flat soft KO burst decal disc, pink star burst, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_ko_burst_cyan_01", "A flat soft KO burst decal disc, cyan burst, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_ko_burst_gold_01", "A flat soft KO burst decal disc, gold burst, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_ko_burst_rainbow_01", "A flat soft KO burst decal disc, rainbow burst, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_hit_marker_01", "A flat soft hit marker decal, star ping, very thin about 0.8 m wide", 0.05, 0.8),
        ("vfx_spawn_burst_01", "A flat soft spawn burst decal, teal rings, very thin about 1.5 m wide", 0.05, 1.5),
        ("prop_shooter_scoreboard_01", "A soft shooter scoreboard blank, charcoal pink", 2.0, None),
        ("prop_shooter_timer_01", "A soft shooter timer board blank, cream magenta", 1.6, None),
        ("prop_shooter_ammo_station_01", "A soft foam ammo restock station, pink yellow; toy", 1.4, None),
        ("prop_shooter_health_station_01", "A soft heal station pedestal, mint cream", 1.4, None),
        ("prop_shooter_flag_01", "A soft shooter arena flag on pole, pink cream blank", 2.2, None),
        ("prop_shooter_banner_01", "A soft shooter banner on posts blank, magenta cream", 1.5, None),
        ("prop_shooter_light_01", "A soft shooter arena light on stand, pink gold", 2.0, None),
        ("prop_shooter_speaker_01", "A soft shooter PA speaker, charcoal magenta", 1.6, None),
        ("prop_shooter_camera_01", "A soft shooter cam on stand, cream pink", 1.5, None),
        ("prop_shooter_drone_01", "A soft shooter drone toy grounded, cyan pink", 0.5, None),
        ("prop_shooter_trophy_01", "A soft shooter trophy, gold pink", 0.8, None),
        ("prop_shooter_medal_01", "A soft shooter medal on stand, gold magenta", 0.6, None),
        ("prop_shooter_podium_01", "A soft shooter winners podium, gold silver bronze candy", 1.2, None),
        ("prop_shooter_gate_01", "A soft shooter arena entry gate, pink cream open", 2.5, None),
        ("prop_shooter_fence_01", "A soft shooter arena fence segment, teal pink", 1.2, None),
        ("prop_shooter_bench_01", "A soft shooter sideline bench, coral cream", 0.6, None),
        ("prop_shooter_locker_01", "A soft shooter toy locker, charcoal pink", 1.8, None),
        ("prop_shooter_bench_cover_01", "A soft sideline cover bench combo, yellow teal", 1.0, None),
    ]
    for i in range(2, 41):
        items.append(
            (
                f"prop_cover_block_{i:02d}",
                f"A rounded soft cover block variant {i}: unique silhouette and candy color for party shooter arena",
                0.8 + (i % 7) * 0.15,
                None,
            )
        )
    for i in range(2, 26):
        items.append(
            (
                f"prop_target_star_{i:02d}",
                f"A soft star pop target variant {i}: unique stand style and candy color",
                0.7 + (i % 6) * 0.1,
                None,
            )
        )
    for i in range(2, 16):
        items.append(
            (
                f"prop_blaster_toy_{i:02d}",
                f"A chunky foam toy blaster decoration variant {i}: unique candy color and rounded silhouette — clearly a soft party toy, not a realistic weapon",
                0.35 + (i % 4) * 0.05,
                None,
            )
        )

    for aid, desc, h, w in items:
        kind = "vfx" if aid.startswith("vfx_") else ("env" if aid.startswith("env_") else "prop")
        out.append(
            PromptEntry(
                asset_id=aid,
                category="shooter",
                priority=3,
                kind=kind,
                label=aid,
                prompt=_prop(desc, h, w),
                target_height=h,
                target_width=w,
                notes="Shooter stage kit",
                job_batch="shooter",
            )
        )
    return out


def build_rewards_vfx() -> list[PromptEntry]:
    out: list[PromptEntry] = []
    items = [
        ("prop_trophy_gold_01", "A soft gold candy trophy cup with blank face, friendly silhouette", 0.9, None),
        ("prop_trophy_silver_01", "A soft silver-candy trophy cup blank, matte not chrome", 0.9, None),
        ("prop_trophy_bronze_01", "A soft bronze-candy trophy cup blank", 0.9, None),
        ("prop_trophy_star_01", "A soft star trophy, gold pink", 0.8, None),
        ("prop_trophy_egg_01", "A soft Nest egg trophy, pastel cream gold", 0.9, None),
        ("prop_trophy_orb_01", "A soft vibe orb trophy, yellow gold", 0.8, None),
        ("prop_trophy_blaster_01", "A soft toy blaster trophy, pink gold; clearly toy motif", 0.8, None),
        ("prop_trophy_grand_01", "A grand soft party trophy with handles, rainbow candy accents", 1.3, None),
        ("prop_medal_gold_01", "A soft gold medal on stand blank", 0.5, None),
        ("prop_medal_silver_01", "A soft silver-candy medal on stand blank", 0.5, None),
        ("prop_medal_bronze_01", "A soft bronze-candy medal on stand blank", 0.5, None),
        ("prop_medal_star_01", "A soft star medal on stand, pink gold", 0.5, None),
        ("prop_medal_heart_01", "A soft heart medal on stand, coral cream", 0.5, None),
        ("prop_cup_party_01", "A soft party cup prize, coral cream", 0.6, None),
        ("prop_plaque_01", "A soft award plaque blank on stand, gold cream", 0.7, None),
        ("prop_ribbon_prize_01", "A soft prize ribbon rosette, rainbow candy", 0.5, None),
        ("prop_crown_prize_01", "A soft prize crown on stand, gold coral", 0.6, None),
        ("prop_scepter_01", "A soft party scepter prop, gold star tip", 1.2, None),
        ("prop_boing_coin_01", "A soft oversized Boing coin prop, gold cream blank", 0.5, None),
        ("prop_boing_coin_stack_01", "A soft Boing coin stack, gold cream", 0.8, None),
        ("prop_boing_chest_01", "A soft Boing rewards chest, gold indigo", 1.0, None),
        ("prop_hype_meter_01", "A soft Nest Hype meter prop blank stylized, coral gold", 1.6, None),
        ("prop_season_badge_01", "A soft season badge stand blank, teal cream", 0.7, None),
        ("prop_challenge_token_01", "A soft weekly challenge token prop, magenta cream", 0.4, None),
        ("vfx_confetti_burst_01", "A flat soft confetti burst decal disc, rainbow, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_star_burst_01", "A flat soft star burst decal, gold pink, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_heart_burst_01", "A flat soft heart burst decal, pink cream, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_orb_burst_01", "A flat soft orb collect burst decal, yellow rings, very thin about 1.5 m wide", 0.05, 1.5),
        ("vfx_boost_burst_01", "A flat soft boost burst decal, cyan chevrons, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_finish_burst_01", "A flat soft finish burst decal, checkered glow, very thin about 2.5 m wide", 0.05, 2.5),
        ("vfx_portal_ring_01", "A flat soft portal ring decal, magenta teal, very thin about 2.5 m wide", 0.05, 2.5),
        ("vfx_shadow_blob_01", "A flat soft contact shadow blob decal, soft charcoal transparent-look matte, very thin about 1.2 m wide", 0.03, 1.2),
        ("vfx_spotlight_pool_01", "A flat soft spotlight pool decal, cream glow, very thin about 2 m wide", 0.05, 2.0),
        ("vfx_arrow_floor_01", "A flat soft floor arrow decal, cyan yellow, very thin about 1.5 m long", 0.05, 1.5),
        ("vfx_crosshair_cute_01", "A flat soft cute crosshair decal, pink cream, very thin about 1 m wide", 0.05, 1.0),
        ("vfx_mode_icon_race_01", "A soft freestanding 3D Race mode icon prop, cyan speed shape blank", 1.2, None),
        ("vfx_mode_icon_vibe_01", "A soft freestanding 3D Vibe mode icon prop, yellow orb shape", 1.2, None),
        ("vfx_mode_icon_shooter_01", "A soft freestanding 3D Shooter mode icon prop, pink star shape", 1.2, None),
        ("vfx_mode_icon_party_01", "A soft freestanding 3D Party Saga mode icon prop, rainbow swirl", 1.2, None),
        ("prop_ui_button_stand_01", "A soft oversized candy UI button on stand blank, coral cream", 1.0, None),
        ("prop_ui_panel_01", "A soft freestanding UI panel blank, teal cream", 1.8, None),
        ("prop_ui_cursor_01", "A soft oversized cursor arrow prop, cream coral", 0.8, None),
        ("prop_photo_frame_01", "A soft Nest photo frame blank on stand, gold cream", 1.4, None),
        ("prop_photo_frame_wide_01", "A wide soft photo frame blank, coral cream", 1.2, None),
        ("prop_camera_tripod_01", "A soft camera on tripod, cream teal", 1.6, None),
        ("prop_clapboard_01", "A soft clapboard prop blank, charcoal cream", 0.5, None),
        ("prop_director_chair_01", "A soft director chair, teal cream", 1.0, None),
    ]
    for i in range(2, 21):
        items.append(
            (
                f"prop_trophy_var_{i:02d}",
                f"A soft party trophy variant {i}: unique cup silhouette and candy metal color (gold/silver/coral/teal)",
                0.7 + (i % 5) * 0.1,
                None,
            )
        )
    for i in range(2, 16):
        items.append(
            (
                f"vfx_burst_var_{i:02d}",
                f"A flat soft VFX burst decal variant {i}: unique candy burst pattern, very thin about 2 m wide",
                0.05,
                2.0,
            )
        )

    for aid, desc, h, w in items:
        kind = "vfx" if aid.startswith("vfx_") else "prop"
        out.append(
            PromptEntry(
                asset_id=aid,
                category="rewards_vfx",
                priority=4,
                kind=kind,
                label=aid,
                prompt=_prop(desc, h, w),
                target_height=h,
                target_width=w,
                notes="Rewards / VFX / UI props",
                job_batch="rewards",
            )
        )
    return out


def build_ugc_deco() -> list[PromptEntry]:
    """Extra map-creator deco palette pieces."""
    out: list[PromptEntry] = []
    items: list[tuple[str, str, float, float | None]] = []
    shapes = [
        "cube", "sphere", "cylinder", "wedge", "pyramid_soft", "torus", "star_prism",
        "heart_prism", "capsule", "dome", "arch_block", "ramp_block", "stair_block",
        "pillar", "beam", "slab", "ring_block", "cross_block", "tee_block", "corner_block",
    ]
    palettes = [
        "coral cream", "cyan white", "yellow orange", "pink magenta", "teal lime",
        "indigo cream", "gold coral", "mint lilac", "rainbow soft", "charcoal cyan",
    ]
    n = 0
    for shape in shapes:
        for pal in palettes:
            n += 1
            items.append(
                (
                    f"prop_deco_{shape}_{n:03d}",
                    f"A soft candy map-deco {shape.replace('_', ' ')} block, {pal} palette, rounded toy edges, single solid piece for UGC map creator",
                    0.8 + (n % 8) * 0.1,
                    None,
                )
            )
            if n >= 180:
                break
        if n >= 180:
            break

    for i in range(1, 41):
        items.append(
            (
                f"prop_deco_flora_{i:02d}",
                f"A soft UGC flora deco variant {i}: unique plant/mushroom/flower silhouette, candy colors",
                0.6 + (i % 7) * 0.15,
                None,
            )
        )
    for i in range(1, 31):
        items.append(
            (
                f"prop_deco_rock_{i:02d}",
                f"A soft UGC candy rock deco variant {i}: rounded boulder silhouette, teal/cream/coral matte",
                0.5 + (i % 6) * 0.12,
                None,
            )
        )

    for aid, desc, h, w in items:
        out.append(
            PromptEntry(
                asset_id=aid,
                category="ugc_deco",
                priority=4,
                kind="prop",
                label=aid,
                prompt=_prop(desc, h, w),
                target_height=h,
                target_width=w,
                notes="Map Creator deco palette",
                job_batch="ugc",
            )
        )
    return out


def build_all() -> list[PromptEntry]:
    chunks = [
        build_characters(),
        build_accessories(),
        build_nest(),
        build_race(),
        build_vibe(),
        build_shooter(),
        build_rewards_vfx(),
        build_ugc_deco(),
    ]
    seen: set[str] = set()
    out: list[PromptEntry] = []
    for chunk in chunks:
        for e in chunk:
            if e.asset_id in _V1_IDS or e.asset_id in seen:
                continue
            if len(e.prompt) > MAX_PROMPT_CHARS:
                raise SystemExit(f"Prompt too long ({len(e.prompt)}): {e.asset_id}")
            seen.add(e.asset_id)
            out.append(e)
    return out


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def write_outputs(entries: list[PromptEntry]) -> None:
    _OUT_DATA.mkdir(parents=True, exist_ok=True)
    (_OUT_DATA / "by_category").mkdir(parents=True, exist_ok=True)
    _OUT_DOCS.mkdir(parents=True, exist_ok=True)

    catalog = {
        "pack": "studio_prompts_v2",
        "game": "PudgyMon: Party Saga",
        "count": len(entries),
        "max_prompt_chars": MAX_PROMPT_CHARS,
        "negative_prompt": NEGATIVE,
        "accessory_negative_prompt": ACC_NEGATIVE,
        "export": {
            "format": "GLB with baked Tripo PBR",
            "units": "1 unit ≈ 1 meter",
            "character_height": 1.2,
        },
        "assets": [asdict(e) for e in entries],
    }
    (_OUT_DATA / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    # Manifest CSV for spreadsheet / batch tracking
    lines = ["asset_id,category,priority,kind,slot,target_height,target_width,job_batch,label,prompt_chars"]
    for e in entries:
        lines.append(
            ",".join(
                [
                    e.asset_id,
                    e.category,
                    str(e.priority),
                    e.kind,
                    e.slot or "",
                    "" if e.target_height is None else str(e.target_height),
                    "" if e.target_width is None else str(e.target_width),
                    e.job_batch,
                    json.dumps(e.label),
                    str(len(e.prompt)),
                ]
            )
        )
    (_OUT_DATA / "manifest.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    by_cat: dict[str, list[PromptEntry]] = {}
    for e in entries:
        by_cat.setdefault(e.category, []).append(e)

    for cat, items in sorted(by_cat.items()):
        (_OUT_DATA / "by_category" / f"{cat}.json").write_text(
            json.dumps({"category": cat, "count": len(items), "assets": [asdict(e) for e in items]}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        write_category_md(cat, items)

    write_index_md(entries, by_cat)
    print(f"Wrote {len(entries)} prompts -> {_OUT_DATA} and {_OUT_DOCS}")


def write_category_md(category: str, items: list[PromptEntry]) -> None:
    title = category.replace("_", " ").title()
    parts = [
        f"# Studio prompts V2 — {title}",
        "",
        f"**{len(items)}** copy-paste jobs. Each fenced block is a complete prompt (≤{MAX_PROMPT_CHARS} chars). Studio does not cache prior jobs.",
        "",
        "Parent index: [STUDIO_PROMPTS_V2.md](../STUDIO_PROMPTS_V2.md) · Pack 1: [STUDIO_PROMPTS.md](../STUDIO_PROMPTS.md)",
        "",
    ]
    for e in items:
        meta = []
        if e.target_height is not None:
            meta.append(f"height **{e.target_height}**")
        if e.target_width is not None:
            meta.append(f"width **~{e.target_width}**")
        if e.slot:
            meta.append(f"slot `{e.slot}`")
        meta_s = f" · {' · '.join(meta)}" if meta else ""
        parts.append(f"### `{e.asset_id}`{meta_s}")
        parts.append("")
        if e.notes:
            parts.append(f"_{e.notes}_")
            parts.append("")
        parts.append("```")
        parts.append(e.prompt)
        parts.append("```")
        parts.append("")
    (_OUT_DOCS / f"{category}.md").write_text("\n".join(parts), encoding="utf-8")


def write_index_md(entries: list[PromptEntry], by_cat: dict[str, list[PromptEntry]]) -> None:
    counts = {k: len(v) for k, v in sorted(by_cat.items())}
    total = len(entries)
    rows = "\n".join(
        f"| [{cat}](studio_prompts_v2/{cat}.md) | {n} |" for cat, n in counts.items()
    )
    batches: dict[str, int] = {}
    for e in entries:
        batches[e.job_batch] = batches.get(e.job_batch, 0) + 1
    batch_rows = "\n".join(f"| `{b}` | {n} |" for b, n in sorted(batches.items()))

    md = f"""# Immersive Studio prompt pack V2 — PudgyMon: Party Saga

**{total} new assets** on top of pack 1 ([STUDIO_PROMPTS.md](STUDIO_PROMPTS.md)). Built to burn Tripo credits on reusable Party Saga content: cosmetics, Nest, Race / Vibe / Shooter kits, UGC deco, rewards.

Copy-paste prompts for [Immersive Labs Studio](https://github.com/chiku524/immersive.labs) / Tripo jobs.

**Important:** Studio does **not** cache prior prompts. Every job is independent. Each fenced prompt is complete — paste it alone. **Hard limit: ≤ {MAX_PROMPT_CHARS} characters.**

After generation → import → place: [STUDIO_ASSETS.md](STUDIO_ASSETS.md). Character contract: [CHARACTERS.md](CHARACTERS.md).

**Theme lock:** cute chunky **Pudgy Monsters** in a party playground — The Nest + Race / Vibe Collect / Shooter. Not freight, vaults, or corporate comedy.

## Export settings (all jobs)

| Setting | Value |
|---------|--------|
| Format | GLB with baked Tripo PBR |
| Pivot | Floor center (characters / props) · wear origin (accessories) |
| Facing | Character faces −Z (Bevy forward) when possible |
| Units | 1 unit ≈ 1 meter |
| Naming | Folder + file = `asset_id` / `asset_id.glb` |
| Characters | After polish: baked ~1.2 m height, `uniform_scale` `1.0` |

**Art direction:** soft stylized cartoon 3D (Pokémon / Kirby / Animal Crossing / Fall Guys softness). Matte painted candy — **not** clay, vinyl, or photoreal.

## Optional negative prompt

```
{NEGATIVE}
```

**Accessory negative (if separate field):**

```
{ACC_NEGATIVE}
```

## Pack contents ({total} assets)

| Category | Count |
|----------|------:|
{rows}

### By job batch

| Batch | Count |
|-------|------:|
{batch_rows}

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
"""
    _INDEX.write_text(md, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-id", help="Print a single prompt and exit")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--no-write", action="store_true", help="Build in memory only")
    args = parser.parse_args()

    entries = build_all()

    if args.print_id:
        for e in entries:
            if e.asset_id == args.print_id:
                print(e.prompt)
                print(f"\n# chars: {len(e.prompt)}", file=sys.stderr)
                return 0
        print(f"Unknown id: {args.print_id}", file=sys.stderr)
        return 1

    if args.stats:
        by_cat: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for e in entries:
            by_cat[e.category] = by_cat.get(e.category, 0) + 1
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        print(f"total: {len(entries)}")
        print("by category:")
        for k, v in sorted(by_cat.items()):
            print(f"  {k}: {v}")
        print("by kind:")
        for k, v in sorted(by_kind.items()):
            print(f"  {k}: {v}")
        over = [e.asset_id for e in entries if len(e.prompt) > MAX_PROMPT_CHARS]
        print(f"over_limit: {len(over)}")
        return 0

    if not args.no_write:
        write_outputs(entries)
    else:
        print(f"Built {len(entries)} prompts (not written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
