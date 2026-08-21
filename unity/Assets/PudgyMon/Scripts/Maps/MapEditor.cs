using System.Collections.Generic;
using UnityEngine;

namespace PudgyMon
{
    public enum EditLayer { Race, Vibe, Shooter, Koth }
    public enum EditorPalette { Primary, Spawn, Block, Deco }

    public sealed class MapEditor : MonoBehaviour
    {
        public bool Active;
        public PartyPack Pack = new PartyPack();
        public EditLayer Layer;
        public EditorPalette Palette;
        public int DecoIndex;
        public string Status = "";
        Transform _root;
        StudioAssets _studio;

        public void Init(StudioAssets studio)
        {
            _studio = studio;
            _root = new GameObject("EditorRoot").transform;
            _root.SetParent(transform, false);
        }

        public string LayerLabel => Layer switch
        {
            EditLayer.Race => "Race",
            EditLayer.Vibe => "Vibe",
            EditLayer.Shooter => "Shooter",
            EditLayer.Koth => "Hill",
            _ => "Layer"
        };

        public string PaletteLabel => Palette switch
        {
            EditorPalette.Primary => Layer switch
            {
                EditLayer.Race => "Gate",
                EditLayer.Vibe => "Orb",
                EditLayer.Shooter => "Cover",
                _ => "Hill"
            },
            EditorPalette.Spawn => "Spawn",
            EditorPalette.Block => "Block",
            _ => "Deco " + CurrentDeco
        };

        public string CurrentDeco => MapCatalog.DecoIds[Mathf.Clamp(DecoIndex, 0, MapCatalog.DecoIds.Length - 1)];

        public void Open()
        {
            Active = true;
            Pack = new PartyPack
            {
                Id = "pack_" + System.DateTime.Now.ToString("HHmmss"),
                Label = "My Party Saga"
            };
            Pack.SyncIds();
            Layer = EditLayer.Race;
            Palette = EditorPalette.Primary;
            Status = "Tab layer · 1 primary · 2 spawn · 3 block · 4 deco · F place · X delete · F5 save · F8 pack · F6 play · F9 saga · Esc exit";
            Rebuild();
        }

        public void Close()
        {
            Active = false;
            ClearVisuals();
        }

        public bool Tick(Vector3 playerPos, Vector3 lookFlat, ActiveMaps active, PartyDirector director)
        {
            if (!Active) return false;

            if (Input.GetKeyDown(KeyCode.Escape))
            {
                Close();
                return true;
            }

            if (Input.GetKeyDown(KeyCode.Tab))
            {
                Layer = (EditLayer)(((int)Layer + 1) % 4);
                Palette = EditorPalette.Primary;
                Status = "Editing " + LayerLabel;
                Rebuild();
            }

            if (Input.GetKeyDown(KeyCode.Alpha1)) Palette = EditorPalette.Primary;
            if (Input.GetKeyDown(KeyCode.Alpha2)) Palette = EditorPalette.Spawn;
            if (Input.GetKeyDown(KeyCode.Alpha3)) Palette = EditorPalette.Block;
            if (Input.GetKeyDown(KeyCode.Alpha4)) Palette = EditorPalette.Deco;
            if (Palette == EditorPalette.Deco && Input.GetKeyDown(KeyCode.Comma))
                DecoIndex = (DecoIndex + MapCatalog.DecoIds.Length - 1) % MapCatalog.DecoIds.Length;
            if (Palette == EditorPalette.Deco && Input.GetKeyDown(KeyCode.Period))
                DecoIndex = (DecoIndex + 1) % MapCatalog.DecoIds.Length;

            var place = playerPos + lookFlat.normalized * 4f;
            place.y = Palette == EditorPalette.Primary && Layer == EditLayer.Vibe ? 0.6f : 1f;
            place.x = Mathf.Clamp(place.x, -GameConstants.ArenaBounds, GameConstants.ArenaBounds);
            place.z = Mathf.Clamp(place.z, -GameConstants.ArenaBounds, GameConstants.ArenaBounds);

            if (Input.GetKeyDown(KeyCode.F) || Input.GetMouseButtonDown(0))
            {
                Place(place);
                Rebuild();
            }

            if (Input.GetKeyDown(KeyCode.X))
            {
                DeleteLast();
                Rebuild();
            }

            if (Input.GetKeyDown(KeyCode.F5))
            {
                var path = SaveLayer();
                Status = "Saved " + path;
            }

            if (Input.GetKeyDown(KeyCode.F8))
            {
                Pack.SyncIds();
                var path = MapCatalog.Save(Pack.ToJson(), Pack.Id);
                Status = "Saved pack " + path;
            }

            if (Input.GetKeyDown(KeyCode.F6))
            {
                ApplyLayer(active);
                director.Queue(PartyPlan.Single(Layer switch
                {
                    EditLayer.Vibe => StageKind.Vibe,
                    EditLayer.Shooter => StageKind.Shooter,
                    EditLayer.Koth => StageKind.Koth,
                    _ => StageKind.Race
                }));
                Close();
                return false;
            }

            if (Input.GetKeyDown(KeyCode.F9))
            {
                Pack.SyncIds();
                active.Race = Pack.Race;
                active.Vibe = Pack.Vibe;
                active.Shooter = Pack.Shooter;
                active.Koth = Pack.Koth;
                director.Queue(PartyPlan.FullParty);
                Close();
                return false;
            }

            if (Input.GetKeyDown(KeyCode.F7))
            {
                Pack.SyncIds();
                var code = "PM-" + Pack.Id.ToUpperInvariant();
                var path = System.IO.Path.Combine(AppPaths.SharesDir, code + ".json");
                System.IO.File.WriteAllText(path, JsonWrite.Pretty(Pack.ToJson()));
                Status = "Share " + code;
            }

            return true;
        }

        void Place(Vector3 p)
        {
            var v = new[] { p.x, p.y, p.z };
            switch (Layer)
            {
                case EditLayer.Race:
                    if (Palette == EditorPalette.Primary) Pack.Race.Gates.Add(v);
                    else if (Palette == EditorPalette.Spawn) Pack.Race.Spawns.Add(v);
                    else Pack.Race.Blocks.Add(BlockAt(p));
                    break;
                case EditLayer.Vibe:
                    if (Palette == EditorPalette.Primary) Pack.Vibe.Orbs.Add(v);
                    else if (Palette == EditorPalette.Spawn) Pack.Vibe.Spawns.Add(v);
                    else Pack.Vibe.Blocks.Add(BlockAt(p));
                    break;
                case EditLayer.Shooter:
                    if (Palette == EditorPalette.Spawn) Pack.Shooter.Spawns.Add(v);
                    else Pack.Shooter.Cover.Add(BlockAt(p));
                    break;
                case EditLayer.Koth:
                    if (Palette == EditorPalette.Primary) Pack.Koth.Hills.Add(v);
                    else if (Palette == EditorPalette.Spawn) Pack.Koth.Spawns.Add(v);
                    else Pack.Koth.Blocks.Add(BlockAt(p));
                    break;
            }
            Status = $"Placed {PaletteLabel} on {LayerLabel}";
        }

        MapBlock BlockAt(Vector3 p)
        {
            var b = MapBlock.Greybox(p.x, 0.5f, p.z, 2.5f, 1.2f, 2.5f);
            if (Palette == EditorPalette.Deco)
                b.AssetId = CurrentDeco;
            return b;
        }

        void DeleteLast()
        {
            switch (Layer)
            {
                case EditLayer.Race:
                    if (Palette == EditorPalette.Primary && Pack.Race.Gates.Count > 2) Pack.Race.Gates.RemoveAt(Pack.Race.Gates.Count - 1);
                    else if (Palette == EditorPalette.Spawn && Pack.Race.Spawns.Count > 1) Pack.Race.Spawns.RemoveAt(Pack.Race.Spawns.Count - 1);
                    else if (Pack.Race.Blocks.Count > 0) Pack.Race.Blocks.RemoveAt(Pack.Race.Blocks.Count - 1);
                    break;
                case EditLayer.Vibe:
                    if (Palette == EditorPalette.Primary && Pack.Vibe.Orbs.Count > 3) Pack.Vibe.Orbs.RemoveAt(Pack.Vibe.Orbs.Count - 1);
                    else if (Palette == EditorPalette.Spawn && Pack.Vibe.Spawns.Count > 1) Pack.Vibe.Spawns.RemoveAt(Pack.Vibe.Spawns.Count - 1);
                    else if (Pack.Vibe.Blocks.Count > 0) Pack.Vibe.Blocks.RemoveAt(Pack.Vibe.Blocks.Count - 1);
                    break;
                case EditLayer.Shooter:
                    if (Palette == EditorPalette.Spawn && Pack.Shooter.Spawns.Count > 1) Pack.Shooter.Spawns.RemoveAt(Pack.Shooter.Spawns.Count - 1);
                    else if (Pack.Shooter.Cover.Count > 0) Pack.Shooter.Cover.RemoveAt(Pack.Shooter.Cover.Count - 1);
                    break;
                case EditLayer.Koth:
                    if (Palette == EditorPalette.Primary && Pack.Koth.Hills.Count > 1) Pack.Koth.Hills.RemoveAt(Pack.Koth.Hills.Count - 1);
                    else if (Palette == EditorPalette.Spawn && Pack.Koth.Spawns.Count > 1) Pack.Koth.Spawns.RemoveAt(Pack.Koth.Spawns.Count - 1);
                    else if (Pack.Koth.Blocks.Count > 0) Pack.Koth.Blocks.RemoveAt(Pack.Koth.Blocks.Count - 1);
                    break;
            }
        }

        string SaveLayer()
        {
            return Layer switch
            {
                EditLayer.Vibe => MapCatalog.Save(Pack.Vibe.ToJson(), Pack.Vibe.Id),
                EditLayer.Shooter => MapCatalog.Save(Pack.Shooter.ToJson(), Pack.Shooter.Id),
                EditLayer.Koth => MapCatalog.Save(Pack.Koth.ToJson(), Pack.Koth.Id),
                _ => MapCatalog.Save(Pack.Race.ToJson(), Pack.Race.Id)
            };
        }

        void ApplyLayer(ActiveMaps active)
        {
            active.Clear();
            switch (Layer)
            {
                case EditLayer.Race: active.Race = Pack.Race; break;
                case EditLayer.Vibe: active.Vibe = Pack.Vibe; break;
                case EditLayer.Shooter: active.Shooter = Pack.Shooter; break;
                case EditLayer.Koth: active.Koth = Pack.Koth; break;
            }
        }

        void Rebuild()
        {
            ClearVisuals();
            List<float[]> points = Layer switch
            {
                EditLayer.Race => Pack.Race.Gates,
                EditLayer.Vibe => Pack.Vibe.Orbs,
                EditLayer.Koth => Pack.Koth.Hills,
                _ => new List<float[]>()
            };
            var color = Layer switch
            {
                EditLayer.Race => new Color(0.2f, 0.85f, 1f),
                EditLayer.Vibe => new Color(1f, 0.9f, 0.2f),
                EditLayer.Shooter => new Color(1f, 0.4f, 0.55f),
                _ => new Color(0.75f, 0.5f, 1f)
            };
            for (int i = 0; i < points.Count; i++)
            {
                var p = points[i];
                PrimitiveFactory.Create(Layer == EditLayer.Vibe ? PrimitiveType.Sphere : PrimitiveType.Cube,
                    new Vector3(p[0], p[1], p[2]), Layer == EditLayer.Vibe ? new Vector3(0.45f, 0.45f, 0.45f) : new Vector3(2.2f, 1.6f, 0.4f),
                    color, _root, $"EditPrimary_{i}", true, color);
            }

            List<MapBlock> blocks = Layer switch
            {
                EditLayer.Race => Pack.Race.Blocks,
                EditLayer.Vibe => Pack.Vibe.Blocks,
                EditLayer.Shooter => Pack.Shooter.Cover,
                _ => Pack.Koth.Blocks
            };
            for (int i = 0; i < blocks.Count; i++)
            {
                var b = blocks[i];
                var pos = new Vector3(b.Pos[0], b.Pos[1], b.Pos[2]);
                var size = new Vector3(b.Size[0], b.Size[1], b.Size[2]);
                if (!string.IsNullOrEmpty(b.AssetId) && _studio != null)
                    _studio.QueueProp(b.AssetId, pos, Quaternion.identity, _root, $"EditDeco_{i}",
                        PrimitiveType.Cube, size, new Color(0.55f, 0.4f, 0.3f));
                else
                    PrimitiveFactory.Create(PrimitiveType.Cube, pos, size, new Color(0.55f, 0.4f, 0.3f),
                        _root, $"EditBlock_{i}");
            }
        }

        void ClearVisuals()
        {
            if (_root == null) return;
            for (int i = _root.childCount - 1; i >= 0; i--)
                Destroy(_root.GetChild(i).gameObject);
        }
    }
}
