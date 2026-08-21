using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace PudgyMon
{
    public sealed class MapBlock
    {
        public float[] Pos = { 0, 0.5f, 0 };
        public float[] Size = { 2.5f, 1.2f, 2.5f };
        public string AssetId;

        public static MapBlock Greybox(float x, float y, float z, float sx, float sy, float sz) =>
            new MapBlock { Pos = new[] { x, y, z }, Size = new[] { sx, sy, sz } };

        public static MapBlock FromJson(JNode node)
        {
            var o = node.AsObject();
            if (o == null) return new MapBlock();
            var pos = o.Arr("pos");
            var size = o.Arr("size");
            return new MapBlock
            {
                Pos = pos.Count >= 3 ? new[] { pos[0].AsFloat(), pos[1].AsFloat(), pos[2].AsFloat() } : new[] { 0f, 0.5f, 0f },
                Size = size.Count >= 3 ? new[] { size[0].AsFloat(), size[1].AsFloat(), size[2].AsFloat() } : new[] { 2.5f, 1.2f, 2.5f },
                AssetId = o.Has("asset_id") ? o.Str("asset_id") : null
            };
        }

        public JObject ToJson()
        {
            var o = new JObject();
            o.Fields["pos"] = Arr3(Pos);
            o.Fields["size"] = Arr3(Size);
            if (!string.IsNullOrEmpty(AssetId))
                o.Fields["asset_id"] = new JString(AssetId);
            return o;
        }

        public static JArray Arr3(float[] v)
        {
            var a = new JArray();
            a.Items.Add(new JNumber(v[0]));
            a.Items.Add(new JNumber(v.Length > 1 ? v[1] : 0));
            a.Items.Add(new JNumber(v.Length > 2 ? v[2] : 0));
            return a;
        }

        public static JArray Arr3List(List<float[]> list)
        {
            var a = new JArray();
            foreach (var v in list)
                a.Items.Add(Arr3(v));
            return a;
        }

        public static JArray BlockList(List<MapBlock> blocks)
        {
            var a = new JArray();
            foreach (var b in blocks)
                a.Items.Add(b.ToJson());
            return a;
        }

        public static List<MapBlock> ReadBlocks(JArray arr)
        {
            var list = new List<MapBlock>();
            if (arr == null) return list;
            for (int i = 0; i < arr.Count; i++)
                list.Add(FromJson(arr[i]));
            return list;
        }
    }

    public sealed class RaceMap
    {
        public int SchemaVersion = 1;
        public string Id = "untitled_race";
        public string Label = "Untitled Race";
        public string Mode = "race";
        public string Author = "local";
        public List<float[]> Spawns = new List<float[]> { new[] { 0f, 1f, 20f } };
        public List<float[]> Gates = new List<float[]>
        {
            new[] { -12f, 1f, 4f }, new[] { 0f, 1f, -8f }, new[] { 12f, 1f, 4f }, new[] { 0f, 1f, 20f }
        };
        public List<MapBlock> Blocks = new List<MapBlock>();

        public static RaceMap FromJson(JObject o)
        {
            var m = new RaceMap();
            if (o == null) return m;
            m.SchemaVersion = o.Int("schema_version", 1);
            m.Id = o.Str("id", m.Id);
            m.Label = o.Str("label", m.Label);
            m.Mode = o.Str("mode", "race");
            m.Author = o.Str("author", "local");
            m.Spawns = o.Arr("spawns").Float3List();
            m.Gates = o.Arr("gates").Float3List();
            m.Blocks = MapBlock.ReadBlocks(o.Arr("blocks"));
            if (m.Spawns.Count == 0) m.Spawns.Add(new[] { 0f, 1f, 20f });
            return m;
        }

        public JObject ToJson()
        {
            var o = new JObject();
            o.Fields["schema_version"] = new JNumber(SchemaVersion);
            o.Fields["id"] = new JString(Id);
            o.Fields["label"] = new JString(Label);
            o.Fields["mode"] = new JString(Mode);
            o.Fields["author"] = new JString(Author);
            o.Fields["spawns"] = MapBlock.Arr3List(Spawns);
            o.Fields["gates"] = MapBlock.Arr3List(Gates);
            o.Fields["blocks"] = MapBlock.BlockList(Blocks);
            return o;
        }
    }

    public sealed class VibeMap
    {
        public int SchemaVersion = 1;
        public string Id = "untitled_vibe";
        public string Label = "Untitled Vibe";
        public string Mode = "vibe";
        public string Author = "local";
        public List<float[]> Spawns = new List<float[]> { new[] { 0f, 1f, 0f } };
        public List<float[]> Orbs = new List<float[]>();
        public List<MapBlock> Blocks = new List<MapBlock>();

        public VibeMap()
        {
            for (int i = 0; i < 12; i++)
            {
                var a = i * 0.7f;
                Orbs.Add(new[] { Mathf.Cos(a) * 16f, 0.6f, Mathf.Sin(a) * 16f });
            }
        }

        public static VibeMap FromJson(JObject o)
        {
            var m = new VibeMap { Orbs = new List<float[]>() };
            if (o == null) return m;
            m.SchemaVersion = o.Int("schema_version", 1);
            m.Id = o.Str("id", m.Id);
            m.Label = o.Str("label", m.Label);
            m.Mode = o.Str("mode", "vibe");
            m.Author = o.Str("author", "local");
            m.Spawns = o.Arr("spawns").Float3List();
            m.Orbs = o.Arr("orbs").Float3List();
            m.Blocks = MapBlock.ReadBlocks(o.Arr("blocks"));
            if (m.Spawns.Count == 0) m.Spawns.Add(new[] { 0f, 1f, 0f });
            if (m.Orbs.Count == 0)
            {
                for (int i = 0; i < 12; i++)
                {
                    var a = i * 0.7f;
                    m.Orbs.Add(new[] { Mathf.Cos(a) * 16f, 0.6f, Mathf.Sin(a) * 16f });
                }
            }
            return m;
        }

        public JObject ToJson()
        {
            var o = new JObject();
            o.Fields["schema_version"] = new JNumber(SchemaVersion);
            o.Fields["id"] = new JString(Id);
            o.Fields["label"] = new JString(Label);
            o.Fields["mode"] = new JString(Mode);
            o.Fields["author"] = new JString(Author);
            o.Fields["spawns"] = MapBlock.Arr3List(Spawns);
            o.Fields["orbs"] = MapBlock.Arr3List(Orbs);
            o.Fields["blocks"] = MapBlock.BlockList(Blocks);
            return o;
        }
    }

    public sealed class ShooterMap
    {
        public int SchemaVersion = 1;
        public string Id = "untitled_shooter";
        public string Label = "Untitled Shooter";
        public string Mode = "shooter";
        public string Author = "local";
        public List<float[]> Spawns = new List<float[]>
        {
            new[] { 0f, 1f, 12f }, new[] { 8f, 1f, -4f }, new[] { -8f, 1f, -4f }
        };
        public List<MapBlock> Cover = new List<MapBlock>
        {
            MapBlock.Greybox(6f, 0.5f, 0f, 2.5f, 1.2f, 2.5f),
            MapBlock.Greybox(-6f, 0.5f, -6f, 2.5f, 1.2f, 2.5f)
        };

        public static ShooterMap FromJson(JObject o)
        {
            var m = new ShooterMap();
            if (o == null) return m;
            m.SchemaVersion = o.Int("schema_version", 1);
            m.Id = o.Str("id", m.Id);
            m.Label = o.Str("label", m.Label);
            m.Mode = o.Str("mode", "shooter");
            m.Author = o.Str("author", "local");
            m.Spawns = o.Arr("spawns").Float3List();
            m.Cover = MapBlock.ReadBlocks(o.Arr("cover"));
            if (m.Spawns.Count == 0) m.Spawns.Add(new[] { 0f, 1f, 12f });
            return m;
        }

        public JObject ToJson()
        {
            var o = new JObject();
            o.Fields["schema_version"] = new JNumber(SchemaVersion);
            o.Fields["id"] = new JString(Id);
            o.Fields["label"] = new JString(Label);
            o.Fields["mode"] = new JString(Mode);
            o.Fields["author"] = new JString(Author);
            o.Fields["spawns"] = MapBlock.Arr3List(Spawns);
            o.Fields["cover"] = MapBlock.BlockList(Cover);
            return o;
        }
    }

    public sealed class KothMap
    {
        public int SchemaVersion = 1;
        public string Id = "untitled_koth";
        public string Label = "Untitled King of the Hill";
        public string Mode = "koth";
        public string Author = "local";
        public List<float[]> Spawns = new List<float[]>
        {
            new[] { 0f, 1f, 16f }, new[] { 12f, 1f, -8f }, new[] { -12f, 1f, -8f }, new[] { 0f, 1f, -16f }
        };
        public List<float[]> Hills = new List<float[]>
        {
            new[] { 0f, 0.5f, 0f }, new[] { 14f, 0.5f, -10f }, new[] { -14f, 0.5f, 10f }
        };
        public float HillRadius = 4.5f;
        public float HillSwitchSecs = 12f;
        public List<MapBlock> Blocks = new List<MapBlock>();

        public static KothMap FromJson(JObject o)
        {
            var m = new KothMap();
            if (o == null) return m;
            m.SchemaVersion = o.Int("schema_version", 1);
            m.Id = o.Str("id", m.Id);
            m.Label = o.Str("label", m.Label);
            m.Mode = o.Str("mode", "koth");
            m.Author = o.Str("author", "local");
            m.Spawns = o.Arr("spawns").Float3List();
            m.Hills = o.Arr("hills").Float3List();
            m.HillRadius = o.Num("hill_radius", 4.5f);
            m.HillSwitchSecs = o.Num("hill_switch_secs", 12f);
            m.Blocks = MapBlock.ReadBlocks(o.Arr("blocks"));
            if (m.Hills.Count == 0) m.Hills.Add(new[] { 0f, 0.5f, 0f });
            return m;
        }

        public JObject ToJson()
        {
            var o = new JObject();
            o.Fields["schema_version"] = new JNumber(SchemaVersion);
            o.Fields["id"] = new JString(Id);
            o.Fields["label"] = new JString(Label);
            o.Fields["mode"] = new JString(Mode);
            o.Fields["author"] = new JString(Author);
            o.Fields["spawns"] = MapBlock.Arr3List(Spawns);
            o.Fields["hills"] = MapBlock.Arr3List(Hills);
            o.Fields["hill_radius"] = new JNumber(HillRadius);
            o.Fields["hill_switch_secs"] = new JNumber(HillSwitchSecs);
            o.Fields["blocks"] = MapBlock.BlockList(Blocks);
            return o;
        }
    }

    public sealed class PartyPack
    {
        public int SchemaVersion = 3;
        public string Id = "untitled_pack";
        public string Label = "Untitled Party Saga";
        public string Kind = "party_saga";
        public string Author = "local";
        public RaceMap Race = new RaceMap();
        public VibeMap Vibe = new VibeMap();
        public ShooterMap Shooter = new ShooterMap();
        public KothMap Koth = new KothMap();

        public void SyncIds()
        {
            var baseId = MapCatalog.Sanitize(Id);
            Race.Id = baseId + "_race";
            Race.Label = Label + " — Race";
            Race.Author = Author;
            Vibe.Id = baseId + "_vibe";
            Vibe.Label = Label + " — Vibe";
            Vibe.Author = Author;
            Shooter.Id = baseId + "_shooter";
            Shooter.Label = Label + " — Shooter";
            Shooter.Author = Author;
            Koth.Id = baseId + "_koth";
            Koth.Label = Label + " — King of the Hill";
            Koth.Author = Author;
        }

        public static PartyPack FromJson(JObject o)
        {
            var p = new PartyPack();
            if (o == null) return p;
            p.SchemaVersion = o.Int("schema_version", 3);
            p.Id = o.Str("id", p.Id);
            p.Label = o.Str("label", p.Label);
            p.Kind = o.Str("kind", "party_saga");
            p.Author = o.Str("author", "local");
            p.Race = RaceMap.FromJson(o.Obj("race"));
            p.Vibe = VibeMap.FromJson(o.Obj("vibe"));
            p.Shooter = ShooterMap.FromJson(o.Obj("shooter"));
            p.Koth = o.Has("koth") ? KothMap.FromJson(o.Obj("koth")) : new KothMap();
            return p;
        }

        public JObject ToJson()
        {
            SyncIds();
            var o = new JObject();
            o.Fields["schema_version"] = new JNumber(SchemaVersion);
            o.Fields["id"] = new JString(Id);
            o.Fields["label"] = new JString(Label);
            o.Fields["kind"] = new JString(Kind);
            o.Fields["author"] = new JString(Author);
            o.Fields["race"] = Race.ToJson();
            o.Fields["vibe"] = Vibe.ToJson();
            o.Fields["shooter"] = Shooter.ToJson();
            o.Fields["koth"] = Koth.ToJson();
            return o;
        }
    }

    public enum CatalogKind { Race, Vibe, Shooter, Koth, Pack }

    public sealed class CatalogEntry
    {
        public CatalogKind Kind;
        public string Id;
        public string Label;
        public RaceMap Race;
        public VibeMap Vibe;
        public ShooterMap Shooter;
        public KothMap Koth;
        public PartyPack Pack;
        public string Path;

        public PartyPlan Plan => Kind switch
        {
            CatalogKind.Race => PartyPlan.Single(StageKind.Race),
            CatalogKind.Vibe => PartyPlan.Single(StageKind.Vibe),
            CatalogKind.Shooter => PartyPlan.Single(StageKind.Shooter),
            CatalogKind.Koth => PartyPlan.Single(StageKind.Koth),
            _ => PartyPlan.FullParty
        };
    }

    public sealed class ActiveMaps
    {
        public RaceMap Race;
        public VibeMap Vibe;
        public ShooterMap Shooter;
        public KothMap Koth;

        public void Clear()
        {
            Race = null;
            Vibe = null;
            Shooter = null;
            Koth = null;
        }

        public void Apply(CatalogEntry e)
        {
            Clear();
            switch (e.Kind)
            {
                case CatalogKind.Race: Race = e.Race; break;
                case CatalogKind.Vibe: Vibe = e.Vibe; break;
                case CatalogKind.Shooter: Shooter = e.Shooter; break;
                case CatalogKind.Koth: Koth = e.Koth; break;
                case CatalogKind.Pack:
                    Race = e.Pack.Race;
                    Vibe = e.Pack.Vibe;
                    Shooter = e.Pack.Shooter;
                    Koth = e.Pack.Koth;
                    break;
            }
        }
    }

    public static class MapCatalog
    {
        public static readonly string[] DecoIds =
        {
            "prop_race_cone_01", "prop_race_banner_01", "prop_race_checkpoint_01", "env_race_ramp_01",
            "prop_vibe_orb_01", "prop_vibe_flower_01", "prop_vibe_crystal_01", "prop_vibe_mushroom_01",
            "prop_cover_block_01", "prop_target_star_01", "prop_blaster_toy_01", "env_nest_bench_01",
            "env_nest_egg_01", "env_pad_race_01", "env_pad_vibe_01", "env_pad_shooter_01", "env_pad_party_01"
        };

        public static string Sanitize(string id)
        {
            if (string.IsNullOrEmpty(id)) return "untitled";
            var sb = new StringBuilder();
            foreach (var c in id)
                sb.Append(char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_');
            return sb.Length == 0 ? "untitled" : sb.ToString();
        }

        public static List<CatalogEntry> ListAll()
        {
            var list = new List<CatalogEntry>();
            foreach (var dir in new[] { AppPaths.BundledMaps, AppPaths.MapsDir, AppPaths.SharesDir })
            {
                if (!Directory.Exists(dir)) continue;
                foreach (var file in Directory.GetFiles(dir, "*.json"))
                {
                    var e = LoadEntry(file);
                    if (e != null) list.Add(e);
                }
            }
            return list;
        }

        public static CatalogEntry LoadEntry(string path)
        {
            try
            {
                var node = JNode.LoadFile(path)?.AsObject();
                if (node == null) return null;
                if (node.Str("kind") == "party_saga" || node.Has("race"))
                {
                    var pack = PartyPack.FromJson(node);
                    return new CatalogEntry
                    {
                        Kind = CatalogKind.Pack, Id = pack.Id, Label = pack.Label, Pack = pack, Path = path
                    };
                }

                var mode = node.Str("mode");
                switch (mode)
                {
                    case "race":
                        var r = RaceMap.FromJson(node);
                        return new CatalogEntry { Kind = CatalogKind.Race, Id = r.Id, Label = r.Label, Race = r, Path = path };
                    case "vibe":
                        var v = VibeMap.FromJson(node);
                        return new CatalogEntry { Kind = CatalogKind.Vibe, Id = v.Id, Label = v.Label, Vibe = v, Path = path };
                    case "shooter":
                        var s = ShooterMap.FromJson(node);
                        return new CatalogEntry { Kind = CatalogKind.Shooter, Id = s.Id, Label = s.Label, Shooter = s, Path = path };
                    case "koth":
                        var k = KothMap.FromJson(node);
                        return new CatalogEntry { Kind = CatalogKind.Koth, Id = k.Id, Label = k.Label, Koth = k, Path = path };
                }
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"Map load failed {path}: {e.Message}");
            }
            return null;
        }

        public static string Save(JObject obj, string id)
        {
            var path = Path.Combine(AppPaths.MapsDir, Sanitize(id) + ".json");
            File.WriteAllText(path, JsonWrite.Pretty(obj));
            return path;
        }
    }
}
