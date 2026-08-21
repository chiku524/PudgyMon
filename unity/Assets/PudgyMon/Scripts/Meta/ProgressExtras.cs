using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace PudgyMon
{
    public sealed class ChallengeDef
    {
        public string Id;
        public string Label;
        public uint Target;
        public uint RewardPoints;
    }

    public sealed class ChallengeBoard
    {
        public uint Week = 1;
        public readonly List<ChallengeDef> Defs = new List<ChallengeDef>();
        public readonly Dictionary<string, uint> Progress = new Dictionary<string, uint>();
        public readonly List<string> Claimed = new List<string>();

        public static ChallengeBoard Load()
        {
            var board = new ChallengeBoard();
            var path = RepoPaths.DataFile("challenges/weekly.json");
            var node = JNode.LoadFile(path)?.AsObject();
            if (node != null)
            {
                board.Week = (uint)node.Int("week", 1);
                var arr = node.Arr("challenges");
                for (int i = 0; i < arr.Count; i++)
                {
                    var c = arr[i].AsObject();
                    if (c == null) continue;
                    board.Defs.Add(new ChallengeDef
                    {
                        Id = c.Str("id"),
                        Label = c.Str("label"),
                        Target = (uint)c.Int("target"),
                        RewardPoints = (uint)c.Int("reward_points")
                    });
                }
            }

            var save = Path.Combine(AppPaths.DataDir, "challenges.json");
            var saved = JNode.LoadFile(save)?.AsObject();
            if (saved != null && saved.Int("week") == board.Week)
            {
                var p = saved.Obj("progress");
                if (p != null)
                    foreach (var kv in p.Fields)
                        board.Progress[kv.Key] = (uint)kv.Value.AsInt();
                var claimed = saved.Arr("claimed");
                for (int i = 0; i < claimed.Count; i++)
                    board.Claimed.Add(claimed[i].AsString());
            }

            return board;
        }

        public void Save()
        {
            var o = new JObject();
            o.Fields["week"] = new JNumber(Week);
            var p = new JObject();
            foreach (var kv in Progress)
                p.Fields[kv.Key] = new JNumber(kv.Value);
            o.Fields["progress"] = p;
            var claimed = new JArray();
            foreach (var id in Claimed)
                claimed.Items.Add(new JString(id));
            o.Fields["claimed"] = claimed;
            File.WriteAllText(Path.Combine(AppPaths.DataDir, "challenges.json"), JsonWrite.Pretty(o));
        }

        public void Bump(string id, uint amount)
        {
            Progress.TryGetValue(id, out var v);
            Progress[id] = v + amount;
            Save();
        }

        public void SetMax(string id, uint value)
        {
            Progress.TryGetValue(id, out var v);
            if (value > v)
            {
                Progress[id] = value;
                Save();
            }
        }

        public void ClaimReady(SeasonLedger season)
        {
            foreach (var def in Defs)
            {
                if (Claimed.Contains(def.Id)) continue;
                Progress.TryGetValue(def.Id, out var v);
                if (v >= def.Target)
                {
                    Claimed.Add(def.Id);
                    season.AddPoints(def.RewardPoints);
                }
            }
            Save();
        }

        public string SummaryLine()
        {
            if (Defs.Count == 0) return "No weekly challenges loaded.";
            var parts = new List<string>();
            foreach (var def in Defs)
            {
                Progress.TryGetValue(def.Id, out var v);
                var mark = Claimed.Contains(def.Id) ? "✓" : $"{v}/{def.Target}";
                parts.Add($"{def.Label} {mark}");
            }
            return "Week " + Week + " · " + string.Join(" · ", parts);
        }
    }

    public sealed class CrewRoster
    {
        public readonly List<CharacterEntry> Characters = new List<CharacterEntry>();
        public int Index;

        public CharacterEntry Current =>
            Characters.Count == 0 ? new CharacterEntry { Id = "char_pudgy_base_01", Label = "Base Pudgy" }
            : Characters[Mathf.Clamp(Index, 0, Characters.Count - 1)];

        public static CrewRoster Load()
        {
            var roster = new CrewRoster();
            var node = JNode.LoadFile(RepoPaths.DataFile("characters/roster.json"))?.AsObject();
            var arr = node?.Arr("characters");
            if (arr != null)
            {
                for (int i = 0; i < arr.Count; i++)
                {
                    var c = arr[i].AsObject();
                    if (c == null) continue;
                    roster.Characters.Add(new CharacterEntry
                    {
                        Id = c.Str("id"),
                        Label = c.Str("label"),
                        Blurb = c.Str("blurb")
                    });
                }
            }

            if (roster.Characters.Count == 0)
                roster.Characters.Add(new CharacterEntry { Id = "char_pudgy_base_01", Label = "Base Pudgy" });

            var defaults = JNode.LoadFile(RepoPaths.DataFile("player_defaults.json"))?.AsObject();
            var crew = defaults?.Str("crew_model_id");
            if (!string.IsNullOrEmpty(crew))
            {
                var idx = roster.Characters.FindIndex(c => c.Id == crew);
                if (idx >= 0) roster.Index = idx;
            }

            return roster;
        }

        public CharacterEntry Cycle()
        {
            if (Characters.Count == 0) return Current;
            Index = (Index + 1) % Characters.Count;
            return Current;
        }
    }

    public sealed class CharacterEntry
    {
        public string Id;
        public string Label;
        public string Blurb;
    }

    public sealed class AccessoryCatalog
    {
        public readonly List<string> HatIds = new List<string>();
        public int HatIndex = -1;

        public static AccessoryCatalog Load()
        {
            var cat = new AccessoryCatalog();
            var node = JNode.LoadFile(RepoPaths.DataFile("accessories/catalog.json"))?.AsObject();
            var slots = node?.Arr("slots");
            if (slots == null) return cat;
            for (int i = 0; i < slots.Count; i++)
            {
                var slot = slots[i].AsObject();
                if (slot == null || slot.Str("id") != "hat") continue;
                var items = slot.Arr("items");
                for (int j = 0; j < items.Count; j++)
                {
                    var id = items[j].AsObject()?.Str("id");
                    if (!string.IsNullOrEmpty(id) && RepoPaths.GlbPath(id) != null)
                        cat.HatIds.Add(id);
                }
            }
            return cat;
        }

        public string CycleHat()
        {
            if (HatIds.Count == 0) return null;
            HatIndex = (HatIndex + 1) % HatIds.Count;
            return HatIds[HatIndex];
        }
    }
}
