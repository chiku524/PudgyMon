using UnityEngine;

namespace PudgyMon
{
    public sealed class ModePad : MonoBehaviour
    {
        public PartyPlan Plan;
        public string Label;
    }

    public enum NestAction
    {
        OpenEditor,
        BrowseMaps
    }

    public sealed class UtilityPad : MonoBehaviour
    {
        public NestAction Action;
    }

    public sealed class NestHub : MonoBehaviour
    {
        public string Prompt = "";
        ModePad[] _pads = System.Array.Empty<ModePad>();
        UtilityPad[] _utils = System.Array.Empty<UtilityPad>();

        public static NestHub Build(Transform parent, StudioAssets studio, CosmeticsCatalog cosmetics)
        {
            var hubGo = new GameObject("TheNest");
            hubGo.transform.SetParent(parent, false);
            var hub = hubGo.AddComponent<NestHub>();
            var origin = GameConstants.HubSpawn;
            var root = hubGo.transform;

            BuildPlaza(studio, root, origin);
            BuildPartyStage(studio, root, origin);
            BuildWardrobe(studio, root, origin, cosmetics);
            BuildMarket(studio, root, origin);
            BuildPlayground(studio, root, origin);
            BuildRaceDistrict(studio, root, origin);
            BuildShooterDistrict(studio, root, origin);
            BuildSouthGarden(studio, root, origin);

            SpawnPad(root, studio, origin, PartyPlan.Single(StageKind.Race),
                new Vector3(-20f, 0f, -14f), new Color(0.2f, 0.85f, 1f), "Race", "env_pad_race_01");
            SpawnPad(root, studio, origin, PartyPlan.Single(StageKind.Vibe),
                new Vector3(-8f, 0f, -24f), new Color(1f, 0.85f, 0.2f), "Vibe", "env_pad_vibe_01");
            SpawnPad(root, studio, origin, PartyPlan.Single(StageKind.Shooter),
                new Vector3(20f, 0f, -14f), new Color(1f, 0.4f, 0.55f), "Shooter", "env_pad_shooter_01");
            SpawnPad(root, studio, origin, PartyPlan.Single(StageKind.Koth),
                new Vector3(8f, 0f, -24f), new Color(0.75f, 0.5f, 1f), "Hill", "env_pad_koth_01");
            SpawnPad(root, studio, origin, PartyPlan.FullParty,
                new Vector3(0f, 0f, 8f), new Color(0.55f, 1f, 0.45f), "PartySaga", "env_pad_party_01");

            QueueShowcase(studio, root, origin + new Vector3(-20f, 0f, -14f), "Race");
            QueueShowcase(studio, root, origin + new Vector3(-8f, 0f, -24f), "Vibe");
            QueueShowcase(studio, root, origin + new Vector3(20f, 0f, -14f), "Shooter");
            QueueShowcase(studio, root, origin + new Vector3(8f, 0f, -24f), "Hill");
            QueueShowcase(studio, root, origin + new Vector3(0f, 0f, 8f), "PartySaga");

            SpawnUtility(root, origin, new Vector3(-12f, 0.12f, 16f),
                new Color(0.95f, 0.65f, 0.25f), NestAction.OpenEditor, "CreateMap");
            SpawnUtility(root, origin, new Vector3(12f, 0.12f, 16f),
                new Color(0.65f, 0.45f, 1f), NestAction.BrowseMaps, "MyMaps");
            Place(studio, root, origin, "env_pad_create_01", new Vector3(-12f, 0f, 16f), 0f,
                "UtilityVisual_Create", PrimitiveType.Cylinder, new Vector3(2.8f, 0.2f, 2.8f),
                new Color(0.95f, 0.65f, 0.25f), true);
            Place(studio, root, origin, "env_pad_claim_01", new Vector3(12f, 0f, 16f), 0f,
                "UtilityVisual_Maps", PrimitiveType.Cylinder, new Vector3(2.8f, 0.2f, 2.8f),
                new Color(0.65f, 0.45f, 1f), true);

            hub._pads = hub.GetComponentsInChildren<ModePad>(true);
            hub._utils = hub.GetComponentsInChildren<UtilityPad>(true);
            return hub;
        }

        static void BuildPlaza(StudioAssets studio, Transform root, Vector3 origin)
        {
            PrimitiveFactory.Create(PrimitiveType.Cylinder, origin + new Vector3(0f, 0.05f, -4f),
                new Vector3(5.5f, 0.18f, 5.5f), new Color(0.2f, 0.38f, 0.32f), root, "NestPlaza",
                unlit: true, emission: new Color(0.08f, 0.2f, 0.14f));

            Place(studio, root, origin, "env_nest_egg_01", new Vector3(0f, 0f, -4f), 0f, "NestEgg",
                PrimitiveType.Sphere, new Vector3(1.8f, 1.8f, 1.8f), new Color(0.95f, 0.72f, 0.45f), true);
            Place(studio, root, origin, "env_nest_logo_01", new Vector3(0f, 0f, -9f), 0f, "NestLogo");
            Place(studio, root, origin, "env_nest_statue_pudgy_01", new Vector3(7f, 0f, -1f), -20f, "NestStatue");
            Place(studio, root, origin, "env_nest_lamp_01", new Vector3(-7f, 0f, -7f), 15f, "NestLamp_L");
            Place(studio, root, origin, "env_nest_lamp_01", new Vector3(7f, 0f, -7f), -15f, "NestLamp_R");
            Place(studio, root, origin, "env_nest_bench_01", new Vector3(-8f, 0f, 1f), 10f, "NestBench_L");
            Place(studio, root, origin, "env_nest_bench_01", new Vector3(8f, 0f, 1f), -10f, "NestBench_R");
            Place(studio, root, origin, "env_nest_tree_01", new Vector3(-34f, 0f, -6f), 25f, "NestTree_W");
            Place(studio, root, origin, "env_nest_tree_candy_02", new Vector3(36f, 0f, -8f), -20f, "NestTree_E");

            PlaceCrew(studio, root, origin, "char_pudgy_base_01", new Vector3(-5.5f, 0f, -1.5f), 40f);
            PlaceCrew(studio, root, origin, "oceanic_pudgymon_01", new Vector3(5.5f, 0f, -1.5f), -40f);
            PlaceCrew(studio, root, origin, "char_pudgy_sky_01", new Vector3(-4f, 0f, 3f), 160f);
            PlaceCrew(studio, root, origin, "char_pudgy_forest_01", new Vector3(4.5f, 0f, 3.2f), -160f);
            PlaceCrew(studio, root, origin, "npc_nest_bard_01", new Vector3(-9.5f, 0f, 2.2f), 90f);
        }

        static void BuildPartyStage(StudioAssets studio, Transform root, Vector3 origin)
        {
            Place(studio, root, origin, "env_nest_podium_01", new Vector3(0f, 0f, 12.4f), 180f, "PartyPodium");
            Place(studio, root, origin, "env_nest_booth_dj_01", new Vector3(6.5f, 0f, 11f), -150f, "PartyDjBooth");
            Place(studio, root, origin, "env_nest_speaker_01", new Vector3(-5.2f, 0f, 10.2f), 20f, "PartySpeaker_L");
            Place(studio, root, origin, "env_nest_speaker_01", new Vector3(5.2f, 0f, 10.2f), -20f, "PartySpeaker_R");
            Place(studio, root, origin, "env_nest_disco_01", new Vector3(-3.2f, 0f, 12.6f), 30f, "PartyDisco");
            Place(studio, root, origin, "env_nest_confetti_cannon_01", new Vector3(-6.8f, 0f, 6.5f), 25f, "PartyCannon_L");
            Place(studio, root, origin, "env_nest_confetti_cannon_01", new Vector3(6.8f, 0f, 6.5f), -25f, "PartyCannon_R");
            Place(studio, root, origin, "env_nest_jukebox_01", new Vector3(-6.4f, 0f, 11.2f), 40f, "PartyJukebox");

            PlaceCrew(studio, root, origin, "npc_nest_dj_01", new Vector3(5.4f, 0f, 9.4f), -150f);
            PlaceCrew(studio, root, origin, "char_pudgy_lava_01", new Vector3(-8.2f, 0f, 8.6f), 110f);
            PlaceCrew(studio, root, origin, "char_pudgy_lava_party_01", new Vector3(8.4f, 0f, 8.2f), -110f);
            PlaceCrew(studio, root, origin, "char_pudgy_aurora_01", new Vector3(-3.6f, 0f, 14.2f), 180f);
            PlaceCrew(studio, root, origin, "char_pudgy_night_01", new Vector3(3.4f, 0f, 14.2f), 180f);
            PlaceCrew(studio, root, origin, "char_pudgy_night_rare_01", new Vector3(0f, 0f, 14.8f), 180f);
            PlaceCrew(studio, root, origin, "char_pudgy_candy_rare_01", new Vector3(-8.8f, 0f, 5.4f), 50f);
            PlaceCrew(studio, root, origin, "char_pudgy_sky_sunset_01", new Vector3(8.8f, 0f, 5.4f), -50f);
        }

        static void BuildWardrobe(StudioAssets studio, Transform root, Vector3 origin, CosmeticsCatalog cosmetics)
        {
            Place(studio, root, origin, "env_pad_wardrobe_01", new Vector3(0f, 0f, 20f), 0f, "UtilityVisual_Wardrobe",
                PrimitiveType.Cylinder, new Vector3(2.8f, 0.2f, 2.8f), new Color(0.95f, 0.8f, 0.45f), true);
            Place(studio, root, origin, "env_nest_table_01", new Vector3(0f, 0f, 23.2f), 0f, "WardrobeTable");
            Place(studio, root, origin, "env_nest_crate_01", new Vector3(-4.2f, 0f, 22.4f), 12f, "WardrobeCrate");

            string[] hats =
            {
                "acc_hat_candy_scoop_01", "acc_hat_honey_pot_01", "acc_hat_storm_cap_01",
                "acc_hat_race_helmet_01", "acc_hat_forest_leaf_01", "acc_hat_ice_crown_01",
                "acc_hat_sprinkle_cap_01", "acc_hat_night_moon_01", "acc_hat_lava_ember_01",
                "acc_hat_sky_cloud_01", "acc_hat_meadow_wreath_01"
            };
            for (int i = 0; i < hats.Length; i++)
            {
                var col = i % 6;
                var row = i / 6;
                Place(studio, root, origin, hats[i], new Vector3(-2.4f + col * 0.95f, 0f, 22.6f + row * 1.1f),
                    180f, $"NestHatRack_{i}", PrimitiveType.Sphere, new Vector3(0.35f, 0.35f, 0.35f),
                    new Color(0.85f, 0.7f, 0.45f));
            }

            PlaceCrew(studio, root, origin, "char_pudgy_cloud_01", new Vector3(-3.2f, 0f, 19.2f), 20f);
            PlaceCrew(studio, root, origin, "char_pudgy_cloud_rare_01", new Vector3(3.2f, 0f, 19.2f), -20f);
            PlaceCrew(studio, root, origin, "char_pudgy_ice_01", new Vector3(-5.4f, 0f, 20.6f), 40f);
            PlaceCrew(studio, root, origin, "char_pudgy_ice_rare_01", new Vector3(5.4f, 0f, 20.6f), -40f);

            if (cosmetics == null)
                return;
            for (int i = 0; i < cosmetics.Items.Count; i++)
            {
                var item = cosmetics.Items[i];
                var t = cosmetics.Items.Count <= 1 ? 0f : i / (float)(cosmetics.Items.Count - 1);
                var pos = origin + new Vector3(-3.6f + t * 7.2f, 0.55f, 24.6f);
                PrimitiveFactory.Create(PrimitiveType.Sphere, pos, new Vector3(0.42f, 0.42f, 0.42f), item.Color,
                    root, $"SkinShowcase_{item.id}", true, item.Color * 0.4f);
            }
        }

        static void BuildMarket(StudioAssets studio, Transform root, Vector3 origin)
        {
            Place(studio, root, origin, "env_nest_booth_shop_01", new Vector3(8.5f, 0f, 30f), 180f, "MarketShop");
            Place(studio, root, origin, "env_nest_booth_photo_01", new Vector3(-8.5f, 0f, 30f), 180f, "MarketPhoto");
            Place(studio, root, origin, "env_nest_booth_claim_01", new Vector3(16.5f, 0f, 19.5f), -90f, "MarketClaim");
            Place(studio, root, origin, "env_nest_booth_ticket_01", new Vector3(-16.5f, 0f, 19.5f), 90f, "MarketTicket");
            Place(studio, root, origin, "env_nest_cart_snack_01", new Vector3(3.2f, 0f, 27.4f), -20f, "MarketCart");
            Place(studio, root, origin, "env_nest_layer_cake_01", new Vector3(6.2f, 0f, 27.8f), 15f, "MarketCake");
            Place(studio, root, origin, "env_nest_donut_01", new Vector3(10.6f, 0f, 27.6f), -10f, "MarketDonut");
            Place(studio, root, origin, "env_nest_dessert_cup_01", new Vector3(5.1f, 0f, 29.2f), 25f, "MarketCup");
            Place(studio, root, origin, "env_nest_cake_01", new Vector3(11.4f, 0f, 29.4f), -15f, "MarketCakeTall");

            PlaceCrew(studio, root, origin, "npc_nest_shop_01", new Vector3(7.4f, 0f, 28.2f), 180f);
            PlaceCrew(studio, root, origin, "npc_nest_photo_01", new Vector3(-7.4f, 0f, 28.2f), 180f);
            PlaceCrew(studio, root, origin, "char_pudgy_candy_01", new Vector3(4.4f, 0f, 26.2f), 20f);
            PlaceCrew(studio, root, origin, "char_pudgy_honey_01", new Vector3(12.2f, 0f, 26.6f), -30f);
            PlaceCrew(studio, root, origin, "char_pudgy_honey_rare_01", new Vector3(13.6f, 0f, 28.8f), -160f);
            PlaceCrew(studio, root, origin, "char_pudgy_cocoa_01", new Vector3(2.2f, 0f, 29.6f), 160f);
            PlaceCrew(studio, root, origin, "char_pudgy_cocoa_rare_01", new Vector3(9.8f, 0f, 31.4f), 180f);
            PlaceCrew(studio, root, origin, "char_pudgy_grape_01", new Vector3(-4.8f, 0f, 27.6f), 10f);
            PlaceCrew(studio, root, origin, "char_pudgy_peach_rare_01", new Vector3(-11.2f, 0f, 27.8f), 30f);
        }

        static void BuildPlayground(StudioAssets studio, Transform root, Vector3 origin)
        {
            Place(studio, root, origin, "env_nest_slide_01", new Vector3(-30f, 0f, 22f), 50f, "PlaySlide");
            Place(studio, root, origin, "env_nest_bounce_castle_01", new Vector3(-24f, 0f, 28f), 180f, "PlayCastle");
            Place(studio, root, origin, "env_nest_seesaw_01", new Vector3(-32f, 0f, 16.5f), 20f, "PlaySeesaw");
            Place(studio, root, origin, "env_nest_swing_01", new Vector3(-22f, 0f, 21f), 15f, "PlaySwing");
            Place(studio, root, origin, "env_nest_hedge_arch_01", new Vector3(-18f, 0f, 16f), 40f, "PlayGate");
            Place(studio, root, origin, "env_nest_plant_01", new Vector3(-27f, 0f, 14f), 25f, "PlayPlant");

            PlaceCrew(studio, root, origin, "char_pudgy_peach_01", new Vector3(-27.4f, 0f, 19.2f), 40f);
            PlaceCrew(studio, root, origin, "char_pudgy_sprout_01", new Vector3(-21.2f, 0f, 24.6f), 160f);
            PlaceCrew(studio, root, origin, "char_pudgy_sprout_rare_01", new Vector3(-26.6f, 0f, 25.4f), 180f);
            PlaceCrew(studio, root, origin, "char_pudgy_berry_01", new Vector3(-33.2f, 0f, 19.8f), 70f);
            PlaceCrew(studio, root, origin, "char_pudgy_berry_rare_01", new Vector3(-29.4f, 0f, 26.8f), 200f);
            PlaceCrew(studio, root, origin, "char_pudgy_bubble_01", new Vector3(-20.4f, 0f, 27.6f), -140f);
            PlaceCrew(studio, root, origin, "char_pudgy_bubble_rare_01", new Vector3(-23.8f, 0f, 18.4f), 20f);
            PlaceCrew(studio, root, origin, "char_pudgy_lemon_01", new Vector3(-34.2f, 0f, 23.6f), 100f);
            PlaceCrew(studio, root, origin, "char_pudgy_lemon_rare_01", new Vector3(-19.6f, 0f, 19.2f), -20f);
        }

        static void BuildRaceDistrict(StudioAssets studio, Transform root, Vector3 origin)
        {
            Place(studio, root, origin, "env_nest_arch_race_01", new Vector3(-14f, 0f, -8f), 40f, "RaceGate");
            Place(studio, root, origin, "env_nest_portal_race_01", new Vector3(-26f, 0f, -18f), 50f, "RacePortal");
            Place(studio, root, origin, "env_nest_plant_02", new Vector3(-28f, 0f, -8f), 30f, "RacePlant");

            PlaceCrew(studio, root, origin, "npc_nest_ref_01", new Vector3(-17.4f, 0f, -11.2f), 40f);
            PlaceCrew(studio, root, origin, "npc_nest_coach_01", new Vector3(-22.8f, 0f, -10.4f), 20f);
            PlaceCrew(studio, root, origin, "char_pudgy_storm_01", new Vector3(-24.6f, 0f, -16.8f), 50f);
            PlaceCrew(studio, root, origin, "char_pudgy_storm_rare_01", new Vector3(-16.2f, 0f, -17.6f), 10f);
            PlaceCrew(studio, root, origin, "char_pudgy_ocean_winter_01", new Vector3(-13.2f, 0f, -12.6f), 30f);
            PlaceCrew(studio, root, origin, "char_pudgy_ocean_festival_01", new Vector3(-27.4f, 0f, -12.2f), 70f);
        }

        static void BuildShooterDistrict(StudioAssets studio, Transform root, Vector3 origin)
        {
            Place(studio, root, origin, "env_nest_arch_shooter_01", new Vector3(14f, 0f, -8f), -40f, "ShooterGate");
            Place(studio, root, origin, "env_nest_plant_02", new Vector3(28f, 0f, -8f), -30f, "ShooterPlant");

            PlaceCrew(studio, root, origin, "char_pudgy_ember_01", new Vector3(17.2f, 0f, -10.8f), -40f);
            PlaceCrew(studio, root, origin, "char_pudgy_ember_rare_01", new Vector3(23.6f, 0f, -10.2f), -20f);
            PlaceCrew(studio, root, origin, "char_pudgy_desert_01", new Vector3(24.8f, 0f, -16.6f), -50f);
            PlaceCrew(studio, root, origin, "char_pudgy_desert_rare_01", new Vector3(16.4f, 0f, -17.4f), -10f);
            PlaceCrew(studio, root, origin, "char_pudgy_crystal_01", new Vector3(27.6f, 0f, -12.4f), -70f);
        }

        static void BuildSouthGarden(StudioAssets studio, Transform root, Vector3 origin)
        {
            Place(studio, root, origin, "env_nest_fountain_01", new Vector3(0f, 0f, -38f), 0f, "SouthFountain");
            Place(studio, root, origin, "env_nest_arch_vibe_01", new Vector3(-14f, 0f, -28f), 15f, "VibeGate");
            Place(studio, root, origin, "env_nest_hedge_arch_01", new Vector3(14f, 0f, -30f), -15f, "HillGate");

            Vector3[] mushrooms =
            {
                new Vector3(-12f, 0f, -20f), new Vector3(-4f, 0f, -28f), new Vector3(-14f, 0f, -32f),
                new Vector3(12f, 0f, -20f), new Vector3(4f, 0f, -32f), new Vector3(16f, 0f, -34f)
            };
            for (int i = 0; i < mushrooms.Length; i++)
            {
                Place(studio, root, origin, "prop_vibe_mushroom_01", mushrooms[i], i * 25f, $"VibeMushroom_{i}",
                    PrimitiveType.Sphere, new Vector3(0.85f, 0.85f, 0.85f),
                    i % 2 == 0 ? new Color(1f, 0.45f, 0.4f) : new Color(0.45f, 0.85f, 1f), true);
            }

            PlaceCrew(studio, root, origin, "char_pudgy_meadow_01", new Vector3(-11.2f, 0f, -21.6f), 20f);
            PlaceCrew(studio, root, origin, "char_pudgy_mint_01", new Vector3(-5.4f, 0f, -27.2f), 10f);
            PlaceCrew(studio, root, origin, "char_pudgy_forest_bloom_01", new Vector3(-15.4f, 0f, -26.4f), 40f);
            PlaceCrew(studio, root, origin, "char_pudgy_forest_autumn_01", new Vector3(-9.6f, 0f, -31.2f), 0f);
            PlaceCrew(studio, root, origin, "char_pudgy_coral_01", new Vector3(11.4f, 0f, -21.8f), -20f);
            PlaceCrew(studio, root, origin, "char_pudgy_coral_rare_01", new Vector3(6.2f, 0f, -27.6f), -10f);
        }

        static void Place(StudioAssets studio, Transform root, Vector3 origin, string id, Vector3 offset, float yaw,
            string name, PrimitiveType fallback = PrimitiveType.Cube, Vector3 fallbackScale = default,
            Color fallbackColor = default, bool unlit = false)
        {
            if (fallbackScale == default)
                fallbackScale = Vector3.one;
            if (fallbackColor == default)
                fallbackColor = new Color(0.35f, 0.5f, 0.38f);
            studio.QueueProp(id, origin + offset, Quaternion.Euler(0f, yaw, 0f), root, name,
                fallback, fallbackScale, fallbackColor, unlit);
        }

        static void PlaceCrew(StudioAssets studio, Transform root, Vector3 origin, string id, Vector3 offset, float yaw)
        {
            studio.QueueProp(id, origin + offset, Quaternion.Euler(0f, yaw, 0f), root, $"NestCrew_{id}",
                PrimitiveType.Capsule, new Vector3(0.5f, 1.4f, 0.5f), new Color(0.95f, 0.6f, 0.45f));
        }

        static void SpawnUtility(Transform parent, Vector3 hub, Vector3 offset, Color color, NestAction action,
            string name)
        {
            var pos = hub + offset;
            var go = PrimitiveFactory.Create(PrimitiveType.Cylinder, pos, new Vector3(2.6f, 0.28f, 2.6f),
                color, parent, $"UtilityPad_{name}", true, color * 1.2f);
            go.AddComponent<UtilityPad>().Action = action;
            PrimitiveFactory.Create(PrimitiveType.Cube, pos + new Vector3(0f, 2f, -2.6f),
                new Vector3(2.8f, 0.2f, 0.2f), color, parent, $"UtilitySign_{name}", true, color);
        }

        static void SpawnPad(Transform parent, StudioAssets studio, Vector3 hub, PartyPlan plan, Vector3 offset,
            Color color, string name, string assetId)
        {
            var pos = hub + offset;
            var padGo = PrimitiveFactory.Create(PrimitiveType.Cylinder, pos + Vector3.up * 0.12f,
                new Vector3(2.8f, 0.25f, 2.8f), color, parent, $"ModePad_{name}", true, color * 1.4f);
            var pad = padGo.AddComponent<ModePad>();
            pad.Plan = plan;
            pad.Label = name;
            studio.QueueProp(assetId, pos, Quaternion.identity, parent, $"ModePadVisual_{name}",
                PrimitiveType.Cylinder, new Vector3(3.2f, 0.2f, 3.2f), color, true);
            PrimitiveFactory.Create(PrimitiveType.Cube, pos + new Vector3(0f, 2.2f, -3.2f),
                new Vector3(3.2f, 0.25f, 0.25f), color, parent, $"ModeSign_{name}", true, color);
        }

        static void QueueShowcase(StudioAssets studio, Transform parent, Vector3 padPos, string padName)
        {
            (string id, Vector3 offset, float yaw)[] props = padName switch
            {
                "Race" => new[]
                {
                    ("prop_race_cone_01", new Vector3(-3.5f, 0f, 1.5f), 0f),
                    ("prop_race_cone_01", new Vector3(3.5f, 0f, 1.5f), 0f),
                    ("prop_race_banner_01", new Vector3(0f, 0f, 4f), 0f),
                    ("env_race_ramp_01", new Vector3(-5.5f, 0f, -1f), 90f)
                },
                "Vibe" => new[]
                {
                    ("prop_vibe_orb_01", new Vector3(-3f, 0f, 2f), 0f),
                    ("prop_vibe_orb_01", new Vector3(3f, 0f, 2f), 0f),
                    ("prop_vibe_flower_01", new Vector3(-4.5f, 0f, -1.5f), 25f),
                    ("prop_vibe_crystal_01", new Vector3(4.5f, 0f, -1.5f), -25f)
                },
                "Shooter" => new[]
                {
                    ("prop_cover_block_01", new Vector3(-3.5f, 0f, 2f), 15f),
                    ("prop_cover_block_round_01", new Vector3(-5.5f, 0f, 0.5f), 0f),
                    ("prop_target_star_01", new Vector3(3.5f, 0f, 2f), -20f),
                    ("prop_target_circle_01", new Vector3(5.2f, 0f, 0.5f), -20f),
                    ("prop_foam_shield_01", new Vector3(0f, 0f, 5.4f), 180f),
                    ("prop_blaster_toy_01", new Vector3(0f, 0f, 4f), 180f)
                },
                "Hill" => new[]
                {
                    ("env_koth_hill_01", new Vector3(0f, 0f, 3.5f), 0f),
                    ("env_nest_crown_01", new Vector3(-3.2f, 0f, 1.5f), 15f),
                    ("prop_koth_flag_01", new Vector3(3.2f, 0f, 1.5f), -15f)
                },
                "PartySaga" => new[]
                {
                    ("prop_trophy_gold_01", new Vector3(-2.2f, 0f, 4.6f), 20f),
                    ("prop_trophy_egg_01", new Vector3(2.2f, 0f, 4.6f), -20f)
                },
                _ => System.Array.Empty<(string, Vector3, float)>()
            };

            for (int i = 0; i < props.Length; i++)
            {
                studio.QueueProp(props[i].id, padPos + props[i].offset,
                    Quaternion.Euler(0f, props[i].yaw, 0f), parent, $"PadShowcase_{padName}_{i}",
                    PrimitiveType.Cube, Vector3.one, Color.white);
            }
        }

        public ModePad NearestPad(Vector3 playerPos, float radius)
        {
            ModePad best = null;
            var bestDist = radius;
            foreach (var pad in _pads)
            {
                var d = Vector3.Distance(playerPos, pad.transform.position);
                if (d < bestDist)
                {
                    bestDist = d;
                    best = pad;
                }
            }

            return best;
        }

        public UtilityPad NearestUtility(Vector3 playerPos, float radius)
        {
            UtilityPad best = null;
            var bestDist = radius;
            foreach (var pad in _utils)
            {
                var d = Vector3.Distance(playerPos, pad.transform.position);
                if (d < bestDist)
                {
                    bestDist = d;
                    best = pad;
                }
            }

            return best;
        }

        public void RefreshPrompt(Vector3 playerPos, PartyDirector director, CosmeticsCatalog cosmetics,
            SeasonLedger season, string extra = null)
        {
            if (director.Phase != PartyPhase.Hub)
            {
                Prompt = extra ?? "";
                return;
            }

            var util = NearestUtility(playerPos, GameConstants.InteractRadius);
            if (util != null)
            {
                Prompt = util.Action == NestAction.OpenEditor
                    ? "E / Enter — open Race Map Creator"
                    : "[ ] cycle maps · E play selected custom/official map";
                return;
            }

            var pad = NearestPad(playerPos, GameConstants.InteractRadius);
            if (pad != null)
            {
                Prompt =
                    $"E / Enter — start {pad.Plan.Label}  ·  Skin {cosmetics.EquippedId}  ·  Season {season.points} pts";
            }
            else
            {
                Prompt =
                    $"The Nest — mode pads · Create Map · My Maps · C skin ({cosmetics.EquippedId}) · N crew · Season {season.points} pts";
            }

            if (!string.IsNullOrEmpty(extra))
                Prompt = extra;
        }
    }
}
