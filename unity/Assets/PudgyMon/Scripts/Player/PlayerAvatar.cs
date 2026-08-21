using UnityEngine;

namespace PudgyMon
{
    public sealed class PlayerAvatar : MonoBehaviour
    {
        public PlayerMotor Motor;
        Renderer[] _tinted;
        Transform _body;

        public static PlayerAvatar Spawn(Transform parent, int slot, bool isLocal, bool isBot, Vector3 position,
            Color tint, string name)
        {
            var root = new GameObject(name);
            root.transform.SetParent(parent, false);
            root.transform.position = position;

            var motor = root.AddComponent<PlayerMotor>();
            motor.Slot = slot;
            motor.IsLocal = isLocal;
            motor.IsBot = isBot;

            var body = PrimitiveFactory.Create(PrimitiveType.Capsule, position, new Vector3(0.45f, 1.6f, 0.45f),
                tint, root.transform, "Body");
            body.transform.localPosition = new Vector3(0f, 0.8f, 0f);

            var avatar = root.AddComponent<PlayerAvatar>();
            avatar.Motor = motor;
            avatar._body = body.transform;
            avatar._tinted = root.GetComponentsInChildren<Renderer>();
            avatar.ApplyTint(tint);
            return avatar;
        }

        public void ApplyTint(Color tint)
        {
            if (_tinted == null)
                return;
            var mat = PrimitiveFactory.Lit(tint, tint * 0.25f);
            foreach (var r in _tinted)
            {
                if (r != null)
                    r.sharedMaterial = mat;
            }
        }

        public void AttachCrewMesh(StudioAssets studio, string modelId)
        {
            if (studio == null || string.IsNullOrEmpty(modelId))
                return;

            foreach (Transform child in transform)
            {
                if (child.name.StartsWith("Crew_"))
                    Destroy(child.gameObject);
            }

            if (_body != null)
                _body.gameObject.SetActive(true);

            studio.QueueProp(modelId, Vector3.zero, Quaternion.identity, transform, $"Crew_{modelId}",
                PrimitiveType.Capsule, new Vector3(0.45f, 1.6f, 0.45f), Color.white,
                localSpace: true,
                onSpawned: (go, loaded) =>
                {
                    if (loaded && _body != null)
                        _body.gameObject.SetActive(false);
                });
        }
    }
}
