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

            PrimitiveFactory.Create(PrimitiveType.Cylinder, origin + new Vector3(0f, 0.05f, -4f),
                new Vector3(5.5f, 0.18f, 5.5f), new Color(0.2f, 0.38f, 0.32f), hubGo.transform, "NestPlaza",
                unlit: true, emission: new Color(0.08f, 0.2f, 0.14f));

            studio.QueueProp("env_nest_egg_01", origin + new Vector3(0f, 0f, -4f), Quaternion.identity,
                hubGo.transform, "NestEgg", PrimitiveType.Sphere, new Vector3(1.8f, 1.8f, 1.8f),
                new Color(0.95f, 0.72f, 0.45f), true);

            Vector3[] benches = { new Vector3(-8f, 0f, 1f), new Vector3(8f, 0f, 1f), new Vector3(0f, 0f, 12f) };
            for (int i = 0; i < benches.Length; i++)
            {
                studio.QueueProp("env_nest_bench_01", origin + benches[i], Quaternion.identity, hubGo.transform,
                    $"NestBench_{i}", PrimitiveType.Cube, new Vector3(2.8f, 0.35f, 0.8f),
                    new Color(0.85f, 0.55f, 0.35f));
            }

            (string id, Vector3 offset, float yaw)[] npcs =
            {
                ("char_pudgy_base_01", new Vector3(-16f, 0f, 2f), 70f),
                ("oceanic_pudgymon_01", new Vector3(16f, 0f, 2f), -70f),
                ("char_pudgy_forest_01", new Vector3(-14f, 0f, 10f), 120f),
                ("char_pudgy_lava_01", new Vector3(14f, 0f, 10f), -120f),
                ("char_pudgy_sky_01", new Vector3(0f, 0f, 14f), 180f)
            };
            for (int i = 0; i < npcs.Length; i++)
            {
                studio.QueueProp(npcs[i].id, origin + npcs[i].offset,
                    Quaternion.Euler(0f, npcs[i].yaw + 180f, 0f), hubGo.transform, $"NestNpc_{i}_{npcs[i].id}",
                    PrimitiveType.Capsule, new Vector3(0.5f, 1.4f, 0.5f), new Color(0.95f, 0.55f, 0.4f));
            }

            Vector3[] mushrooms =
            {
                new Vector3(-22f, 0f, -16f), new Vector3(22f, 0f, -16f), new Vector3(-20f, 0f, 16f),
                new Vector3(20f, 0f, 16f), new Vector3(-28f, 0f, 2f), new Vector3(28f, 0f, 2f)
            };
            for (int i = 0; i < mushrooms.Length; i++)
            {
                studio.QueueProp("prop_vibe_mushroom_01", origin + mushrooms[i], Quaternion.identity,
                    hubGo.transform, $"VibeMushroom_{i}", PrimitiveType.Sphere, new Vector3(0.85f, 0.85f, 0.85f),
                    i % 2 == 0 ? new Color(1f, 0.45f, 0.4f) : new Color(0.45f, 0.85f, 1f), true);
            }

            (string id, Vector3 offset, float yaw)[] scenery =
            {
                ("env_nest_tree_01", new Vector3(-34f, 0f, -6f), 25f),
                ("env_nest_tree_candy_02", new Vector3(36f, 0f, -8f), -20f),
                ("env_nest_fountain_01", new Vector3(0f, 0f, -38f), 0f),
                ("env_nest_lamp_01", new Vector3(-12f, 0f, -8f), 15f),
                ("env_nest_lamp_01", new Vector3(12f, 0f, -8f), -15f),
                ("env_nest_plant_01", new Vector3(-24f, 0f, 8f), 40f),
                ("env_nest_plant_02", new Vector3(24f, 0f, 8f), -40f),
                ("env_nest_crate_01", new Vector3(-18f, 0f, 18f), 10f)
            };
            for (int i = 0; i < scenery.Length; i++)
            {
                studio.QueueProp(scenery[i].id, origin + scenery[i].offset,
                    Quaternion.Euler(0f, scenery[i].yaw, 0f), hubGo.transform, $"NestScenery_{i}",
                    PrimitiveType.Cube, Vector3.one, new Color(0.35f, 0.5f, 0.38f));
            }

            SpawnPad(hubGo.transform, studio, origin, PartyPlan.Single(StageKind.Race),
                new Vector3(-20f, 0f, -14f), new Color(0.2f, 0.85f, 1f), "Race", "env_pad_race_01");
            SpawnPad(hubGo.transform, studio, origin, PartyPlan.Single(StageKind.Vibe),
                new Vector3(-8f, 0f, -24f), new Color(1f, 0.85f, 0.2f), "Vibe", "env_pad_vibe_01");
            SpawnPad(hubGo.transform, studio, origin, PartyPlan.Single(StageKind.Shooter),
                new Vector3(20f, 0f, -14f), new Color(1f, 0.4f, 0.55f), "Shooter", "env_pad_shooter_01");
            SpawnPad(hubGo.transform, studio, origin, PartyPlan.Single(StageKind.Koth),
                new Vector3(8f, 0f, -24f), new Color(0.75f, 0.5f, 1f), "Hill", "env_pad_koth_01");
            SpawnPad(hubGo.transform, studio, origin, PartyPlan.FullParty,
                new Vector3(0f, 0f, 8f), new Color(0.55f, 1f, 0.45f), "PartySaga", "env_pad_party_01");

            QueueShowcase(studio, hubGo.transform, origin + new Vector3(-20f, 0f, -14f), "Race");
            QueueShowcase(studio, hubGo.transform, origin + new Vector3(-8f, 0f, -24f), "Vibe");
            QueueShowcase(studio, hubGo.transform, origin + new Vector3(20f, 0f, -14f), "Shooter");
            QueueShowcase(studio, hubGo.transform, origin + new Vector3(8f, 0f, -24f), "Hill");
            QueueShowcase(studio, hubGo.transform, origin + new Vector3(0f, 0f, 8f), "PartySaga");

            if (cosmetics != null)
            {
                for (int i = 0; i < cosmetics.Items.Count; i++)
                {
                    var item = cosmetics.Items[i];
                    var angle = i * 1.05f;
                    var pos = origin + new Vector3(Mathf.Cos(angle) * 20f, 0.55f, Mathf.Sin(angle) * 20f + 4f);
                    PrimitiveFactory.Create(PrimitiveType.Sphere, pos, new Vector3(0.5f, 0.5f, 0.5f), item.Color,
                        hubGo.transform, $"SkinShowcase_{item.id}", true, item.Color * 0.4f);
                }
            }

            SpawnUtility(hubGo.transform, origin, new Vector3(-12f, 0.12f, 16f),
                new Color(0.95f, 0.65f, 0.25f), NestAction.OpenEditor, "CreateMap");
            SpawnUtility(hubGo.transform, origin, new Vector3(12f, 0.12f, 16f),
                new Color(0.65f, 0.45f, 1f), NestAction.BrowseMaps, "MyMaps");

            hub._pads = hub.GetComponentsInChildren<ModePad>(true);
            hub._utils = hub.GetComponentsInChildren<UtilityPad>(true);
            return hub;
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
                    ("prop_target_star_01", new Vector3(3.5f, 0f, 2f), -20f),
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
                    ("prop_race_cone_01", new Vector3(-4f, 0f, 2.5f), 0f),
                    ("prop_vibe_orb_01", new Vector3(0f, 0f, 3.5f), 0f),
                    ("prop_target_star_01", new Vector3(4f, 0f, 2.5f), 0f)
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
