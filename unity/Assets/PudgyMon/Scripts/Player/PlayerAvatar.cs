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

            root.layer = GameConstants.PlayerLayer;
            var cc = root.AddComponent<CharacterController>();
            cc.height = GameConstants.PlayerHeight;
            cc.radius = GameConstants.PlayerRadius;
            cc.center = new Vector3(0f, GameConstants.PlayerHeight * 0.5f, 0f);
            cc.slopeLimit = 50f;
            cc.stepOffset = 0.4f;
            cc.minMoveDistance = 0f;
            cc.skinWidth = 0.08f;
            motor.BindController(cc);

            var body = PrimitiveFactory.Create(PrimitiveType.Capsule, position, new Vector3(0.45f, 1.6f, 0.45f),
                tint, root.transform, "Body");
            body.transform.localPosition = new Vector3(0f, 0.8f, 0f);

            var avatar = root.AddComponent<PlayerAvatar>();
            avatar.Motor = motor;
            avatar._body = body.transform;
            avatar._tinted = root.GetComponentsInChildren<Renderer>();
            avatar.ApplyTint(tint);
            SetLayerRecurse(root.transform, GameConstants.PlayerLayer);
            return avatar;
        }

        static void SetLayerRecurse(Transform t, int layer)
        {
            t.gameObject.layer = layer;
            for (int i = 0; i < t.childCount; i++)
                SetLayerRecurse(t.GetChild(i), layer);
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
                    if (!loaded)
                        return;
                    if (_body != null)
                        _body.gameObject.SetActive(false);
                    AlignMeshToMotorForward(go.transform);
                    SetLayerRecurse(go.transform, GameConstants.PlayerLayer);
                    var loco = GetComponent<CrewLocomotion>();
                    if (loco == null)
                        loco = gameObject.AddComponent<CrewLocomotion>();
                    loco.Motor = Motor;
                    loco.Bind(go);
                });
        }

        // Nest props keep a 180° glTF spin so authored yaws stay valid.
        // The player motor already faces the move vector, so undo that spin here.
        static void AlignMeshToMotorForward(Transform crewRoot)
        {
            var fit = crewRoot.Find("UnityFit");
            if (fit != null)
                fit.localRotation = Quaternion.identity;
        }
    }
}
