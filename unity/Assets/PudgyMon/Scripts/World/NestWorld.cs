using UnityEngine;

namespace PudgyMon
{
    public static class NestWorld
    {
        public static void Build(Transform parent)
        {
            const float islandRadius = GameConstants.WorldBounds + 1.5f;
            PrimitiveFactory.Create(PrimitiveType.Cylinder, new Vector3(0f, -0.1f, 0f),
                new Vector3(islandRadius, 0.2f, islandRadius),
                new Color(0.16f, 0.28f, 0.26f), parent, "NestIsland");
            PrimitiveFactory.Create(PrimitiveType.Cylinder, new Vector3(0f, -0.22f, 0f),
                new Vector3(islandRadius + 6f, 0.12f, islandRadius + 6f),
                new Color(0.86f, 0.76f, 0.55f), parent, "NestBeach");
            PrimitiveFactory.Create(PrimitiveType.Cube, new Vector3(0f, -0.42f, 0f),
                new Vector3(600f, 0.1f, 600f),
                new Color(0.16f, 0.42f, 0.62f), parent, "NestOcean",
                unlit: true, emission: new Color(0.01f, 0.05f, 0.09f));

            (float angle, float dist, float scale)[] islets =
            {
                (25f, 120f, 9f), (110f, 145f, 14f), (185f, 130f, 7f), (250f, 155f, 12f), (320f, 125f, 8f)
            };
            for (int i = 0; i < islets.Length; i++)
            {
                var a = islets[i].angle * Mathf.Deg2Rad;
                var scale = islets[i].scale;
                var pos = new Vector3(Mathf.Cos(a) * islets[i].dist, -scale * 0.55f,
                    Mathf.Sin(a) * islets[i].dist);
                PrimitiveFactory.Create(PrimitiveType.Sphere, pos, Vector3.one * scale,
                    new Color(0.24f, 0.36f, 0.3f), parent, $"HorizonIslet_{i}");
                var go = parent.Find($"HorizonIslet_{i}");
                if (go != null)
                    go.localScale = new Vector3(scale * 2f, scale * 1.2f, scale * 2f);
            }

            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = new Color(0.62f, 0.78f, 0.9f);
            RenderSettings.fogStartDistance = 95f;
            RenderSettings.fogEndDistance = 260f;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.74f, 0.92f);
            Camera.main.backgroundColor = new Color(0.55f, 0.74f, 0.92f);
            Camera.main.clearFlags = CameraClearFlags.SolidColor;
        }

        public static void ApplyAtmosphere(Light key, Light fill, PartyPhase phase)
        {
            Color keyColor, fillColor;
            float keyLux, fillI;
            switch (phase)
            {
                case PartyPhase.Race:
                    keyColor = new Color(0.7f, 0.9f, 1f);
                    fillColor = new Color(0.2f, 0.85f, 1f);
                    keyLux = 1.3f;
                    fillI = 1.6f;
                    break;
                case PartyPhase.Vibe:
                    keyColor = new Color(1f, 0.95f, 0.55f);
                    fillColor = new Color(1f, 0.85f, 0.2f);
                    keyLux = 1.2f;
                    fillI = 1.7f;
                    break;
                case PartyPhase.Shooter:
                    keyColor = new Color(1f, 0.55f, 0.45f);
                    fillColor = new Color(1f, 0.35f, 0.55f);
                    keyLux = 1.4f;
                    fillI = 1.8f;
                    break;
                case PartyPhase.Koth:
                    keyColor = new Color(0.9f, 0.7f, 1f);
                    fillColor = new Color(0.75f, 0.5f, 1f);
                    keyLux = 1.35f;
                    fillI = 1.75f;
                    break;
                default:
                    keyColor = new Color(1f, 0.95f, 0.88f);
                    fillColor = new Color(0.55f, 0.45f, 1f);
                    keyLux = 1.1f;
                    fillI = 1.4f;
                    break;
            }

            if (key != null)
            {
                key.color = Color.Lerp(key.color, keyColor, 0.08f);
                key.intensity = Mathf.Lerp(key.intensity, keyLux, 0.08f);
            }

            if (fill != null)
            {
                fill.color = Color.Lerp(fill.color, fillColor, 0.08f);
                fill.intensity = Mathf.Lerp(fill.intensity, fillI, 0.08f);
            }
        }
    }
}
