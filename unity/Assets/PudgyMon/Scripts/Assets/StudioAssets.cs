using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using UnityEngine;
#if PUDGYMON_GLTFAST
using GLTFast;
#endif

namespace PudgyMon
{
    [System.Serializable]
    public class StudioAssetEntry
    {
        public string asset_id;
        public float target_height = 1f;
        public float uniform_scale;
        public string notes;
    }

    [System.Serializable]
    class StudioRegistryFile
    {
        public string import_root;
        public StudioAssetEntry[] assets;
    }

    public sealed class StudioRegistry
    {
        public readonly Dictionary<string, StudioAssetEntry> Assets = new Dictionary<string, StudioAssetEntry>();

        public static StudioRegistry Load()
        {
            var registry = new StudioRegistry();
            var path = Path.Combine(RepoPaths.Root, "assets", "studio_registry.json");
            if (!File.Exists(path))
                return registry;
            try
            {
                var parsed = JsonUtility.FromJson<StudioRegistryFile>(File.ReadAllText(path));
                if (parsed?.assets == null)
                    return registry;
                foreach (var entry in parsed.assets)
                {
                    if (string.IsNullOrEmpty(entry.asset_id) || entry.asset_id.StartsWith("_"))
                        continue;
                    if (entry.target_height <= 0f)
                        entry.target_height = 1f;
                    registry.Assets[entry.asset_id] = entry;
                }
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"Studio registry failed to load: {e.Message}");
            }

            return registry;
        }

        public bool ExistsOnDisk(string assetId) => RepoPaths.GlbPath(assetId) != null;

        public float ScaleFor(string assetId, GameObject instance)
        {
            if (!Assets.TryGetValue(assetId, out var entry))
                return 1f;
            if (entry.uniform_scale > 0f)
                return entry.uniform_scale;

            var bounds = BoundsOf(instance);
            if (bounds.size.y < 0.01f)
                return 1f;
            return entry.target_height / bounds.size.y;
        }

        static Bounds BoundsOf(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0)
                return new Bounds(go.transform.position, Vector3.one);
            var bounds = renderers[0].bounds;
            for (int i = 1; i < renderers.Length; i++)
                bounds.Encapsulate(renderers[i].bounds);
            return bounds;
        }
    }

    public sealed class StudioAssets : MonoBehaviour
    {
        public StudioRegistry Registry { get; private set; }
        readonly Queue<SpawnRequest> _queue = new Queue<SpawnRequest>();
        bool _busy;

        struct SpawnRequest
        {
            public string AssetId;
            public Vector3 Position;
            public Quaternion Rotation;
            public Transform Parent;
            public string Name;
            public PrimitiveType Fallback;
            public Vector3 FallbackScale;
            public Color FallbackColor;
            public bool Unlit;
        }

        public void Init(StudioRegistry registry)
        {
            Registry = registry;
        }

        public void QueueProp(string assetId, Vector3 position, Quaternion rotation, Transform parent, string name,
            PrimitiveType fallback = PrimitiveType.Cube, Vector3? fallbackScale = null, Color? color = null,
            bool unlit = false)
        {
            _queue.Enqueue(new SpawnRequest
            {
                AssetId = assetId,
                Position = position,
                Rotation = rotation,
                Parent = parent,
                Name = name,
                Fallback = fallback,
                FallbackScale = fallbackScale ?? Vector3.one,
                FallbackColor = color ?? new Color(0.85f, 0.55f, 0.35f),
                Unlit = unlit
            });
        }

        void Update()
        {
            if (_busy || _queue.Count == 0)
                return;
            var req = _queue.Dequeue();
            _ = Spawn(req);
        }

        async Task Spawn(SpawnRequest req)
        {
            _busy = true;
            var go = new GameObject(req.Name);
            go.transform.SetParent(req.Parent, false);
            go.transform.SetPositionAndRotation(req.Position, req.Rotation);

            var glb = RepoPaths.GlbPath(req.AssetId);
            var loaded = false;
#if PUDGYMON_GLTFAST
            if (glb != null)
            {
                try
                {
                    var import = new GltfImport();
                    var uri = new System.Uri(glb).AbsoluteUri;
                    loaded = await import.Load(uri);
                    if (loaded)
                        loaded = await import.InstantiateMainSceneAsync(go.transform);
                    if (loaded)
                    {
                        var scale = Registry.ScaleFor(req.AssetId, go);
                        if (Mathf.Abs(scale - 1f) > 0.01f)
                            go.transform.localScale = Vector3.one * scale;
                    }
                }
                catch (System.Exception e)
                {
                    Debug.LogWarning($"GLB load failed for {req.AssetId}: {e.Message}");
                    loaded = false;
                }
            }
#else
            await Task.Yield();
#endif
            if (!loaded)
                PrimitiveFactory.Attach(go, req.Fallback, req.FallbackScale, req.FallbackColor, req.Unlit);

            _busy = false;
        }
    }

    public static class PrimitiveFactory
    {
        public static Material Lit(Color color, Color? emission = null, bool unlit = false)
        {
            Shader shader;
            if (unlit)
            {
                shader = Shader.Find("Universal Render Pipeline/Unlit")
                         ?? Shader.Find("Unlit/Color")
                         ?? Shader.Find("Standard");
            }
            else
            {
                shader = Shader.Find("Universal Render Pipeline/Lit")
                         ?? Shader.Find("Universal Render Pipeline/Simple Lit")
                         ?? Shader.Find("Standard")
                         ?? Shader.Find("Unlit/Color");
            }

            var mat = new Material(shader);
            if (mat.HasProperty("_BaseColor"))
                mat.SetColor("_BaseColor", color);
            if (mat.HasProperty("_Color"))
                mat.color = color;
            if (mat.HasProperty("_Metallic"))
                mat.SetFloat("_Metallic", 0f);
            if (mat.HasProperty("_Smoothness"))
                mat.SetFloat("_Smoothness", 0.18f);
            if (emission.HasValue && mat.HasProperty("_EmissionColor"))
            {
                mat.EnableKeyword("_EMISSION");
                mat.SetColor("_EmissionColor", emission.Value);
                if (mat.HasProperty("_Emission"))
                    mat.SetColor("_Emission", emission.Value);
            }

            return mat;
        }

        public static GameObject Create(PrimitiveType type, Vector3 position, Vector3 scale, Color color,
            Transform parent, string name, bool unlit = false, Color? emission = null)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.position = position;
            go.transform.localScale = ScaleFor(type, scale);
            var renderer = go.GetComponent<Renderer>();
            renderer.sharedMaterial = Lit(color, emission, unlit);
            var col = go.GetComponent<Collider>();
            if (col != null)
                Object.Destroy(col);
            return go;
        }

        public static void Attach(GameObject host, PrimitiveType type, Vector3 scale, Color color, bool unlit)
        {
            var child = GameObject.CreatePrimitive(type);
            child.name = "fallback";
            child.transform.SetParent(host.transform, false);
            child.transform.localScale = ScaleFor(type, scale);
            child.GetComponent<Renderer>().sharedMaterial = Lit(color, null, unlit);
            var col = child.GetComponent<Collider>();
            if (col != null)
                Object.Destroy(col);
        }

        /// <summary>
        /// Unity primitives: cube=1m, sphere radius 0.5, cylinder radius 0.5 height 2.
        /// <paramref name="size"/> is world size (xyz). For cylinders, x=radius, y=height, z unused.
        /// </summary>
        public static Vector3 ScaleFor(PrimitiveType type, Vector3 size)
        {
            return type switch
            {
                PrimitiveType.Sphere => Vector3.one * (size.x * 2f),
                PrimitiveType.Cylinder => new Vector3(size.x * 2f, size.y / 2f, size.x * 2f),
                PrimitiveType.Capsule => new Vector3(size.x * 2f, size.y / 2f, size.x * 2f),
                _ => size
            };
        }
    }
}
