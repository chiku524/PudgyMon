using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace PudgyMon
{
    [System.Serializable]
    public class SeasonLedger
    {
        public string season_id = "s1";
        public uint points;
        public uint parties_played;
        public List<string> unlocked = new List<string> { "skin_starter" };

        public static string PathOnDisk()
        {
            var dir = System.IO.Path.Combine(
                System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData),
                Brand.AppDataDir);
            Directory.CreateDirectory(dir);
            return System.IO.Path.Combine(dir, "season.json");
        }

        public static SeasonLedger Load()
        {
            var path = PathOnDisk();
            if (!File.Exists(path))
                return new SeasonLedger();
            try
            {
                var loaded = JsonUtility.FromJson<SeasonLedger>(File.ReadAllText(path));
                return loaded ?? new SeasonLedger();
            }
            catch
            {
                return new SeasonLedger();
            }
        }

        public void Save()
        {
            File.WriteAllText(PathOnDisk(), JsonUtility.ToJson(this, true));
        }

        public void AddPoints(uint amount)
        {
            points += amount;
            parties_played += 1;
            Save();
        }
    }

    [System.Serializable]
    public class CosmeticItem
    {
        public string id;
        public string label;
        public uint cost_points;
        public float[] tint = { 0.95f, 0.45f, 0.35f };
        public Color Color =>
            new Color(tint != null && tint.Length > 0 ? tint[0] : 1f,
                tint != null && tint.Length > 1 ? tint[1] : 1f,
                tint != null && tint.Length > 2 ? tint[2] : 1f);
    }

    [System.Serializable]
    class CosmeticsFile
    {
        public CosmeticItem[] items;
    }

    public sealed class CosmeticsCatalog
    {
        public readonly List<CosmeticItem> Items = new List<CosmeticItem>();
        public string EquippedId = "skin_starter";

        public CosmeticItem Equipped =>
            Items.Find(i => i.id == EquippedId) ?? (Items.Count > 0 ? Items[0] : DefaultStarter());

        public static CosmeticsCatalog Load()
        {
            var catalog = new CosmeticsCatalog();
            var path = RepoPaths.DataFile("cosmetics/catalog.json");
            if (path != null && File.Exists(path))
            {
                try
                {
                    var parsed = JsonUtility.FromJson<CosmeticsFile>(File.ReadAllText(path));
                    if (parsed?.items != null)
                        catalog.Items.AddRange(parsed.items);
                }
                catch
                {
                    // fall through to defaults
                }
            }

            if (catalog.Items.Count == 0)
            {
                catalog.Items.Add(DefaultStarter());
                catalog.Items.Add(Make("skin_vibe", "Sunny Blob", 50, 1f, 0.85f, 0.25f));
                catalog.Items.Add(Make("skin_racer", "Turbo Dumpling", 120, 0.25f, 0.8f, 0.95f));
                catalog.Items.Add(Make("skin_blaster", "Party Peep", 200, 1f, 0.4f, 0.65f));
            }

            return catalog;
        }

        public void Cycle(SeasonLedger season)
        {
            if (Items.Count == 0)
                return;
            var idx = Items.FindIndex(i => i.id == EquippedId);
            for (int n = 0; n < Items.Count; n++)
            {
                idx = (idx + 1) % Items.Count;
                if (season.points >= Items[idx].cost_points)
                {
                    EquippedId = Items[idx].id;
                    return;
                }
            }
        }

        static CosmeticItem DefaultStarter() => Make("skin_starter", "Pudgy Sprout", 0, 0.95f, 0.45f, 0.35f);

        static CosmeticItem Make(string id, string label, uint cost, float r, float g, float b) =>
            new CosmeticItem
            {
                id = id,
                label = label,
                cost_points = cost,
                tint = new[] { r, g, b }
            };
    }
}
