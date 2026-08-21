using UnityEngine;

namespace PudgyMon
{
    public sealed class ThirdPersonCameraRig : MonoBehaviour
    {
        public Transform Target;
        public float Yaw = 180f;
        public float Pitch = 18f;
        public float Distance = GameConstants.CameraDefaultDistance;
        public bool Captured = true;

        public Vector3 PlanarForward { get; private set; } = Vector3.back;
        public Vector3 PlanarRight { get; private set; } = Vector3.left;

        static readonly int OcclusionMask = Physics.DefaultRaycastLayers & ~(1 << GameConstants.PlayerLayer);

        public void Snap()
        {
            RefreshPlanar();
            ApplyPose(1f);
        }

        public void TickInput()
        {
            if (Input.GetKeyDown(KeyCode.BackQuote))
            {
                Captured = !Captured;
                Cursor.lockState = Captured ? CursorLockMode.Locked : CursorLockMode.None;
                Cursor.visible = !Captured;
            }

            if (Captured)
            {
                var delta = Input.mousePositionDelta;
                Yaw += delta.x * GameConstants.MouseSensitivity * Mathf.Rad2Deg;
                Pitch = Mathf.Clamp(
                    Pitch - delta.y * GameConstants.MouseSensitivity * Mathf.Rad2Deg,
                    -55f, 35f);
                Distance = Mathf.Clamp(
                    Distance - Input.mouseScrollDelta.y * 0.5f,
                    GameConstants.CameraMinDistance,
                    GameConstants.CameraMaxDistance);
            }

            RefreshPlanar();
        }

        public void FollowTarget()
        {
            if (Target == null)
                return;
            ApplyPose(1f - Mathf.Exp(-22f * Time.deltaTime));
        }

        void RefreshPlanar()
        {
            var rot = Quaternion.Euler(0f, Yaw, 0f);
            PlanarForward = rot * Vector3.forward;
            PlanarRight = rot * Vector3.right;
        }

        void ApplyPose(float follow)
        {
            var focus = Target.position + Vector3.up * GameConstants.CameraFocusHeight;
            var rot = Quaternion.Euler(Pitch, Yaw, 0f);
            var desiredEye = focus + rot * new Vector3(0f, 0f, -Distance);
            desiredEye = Occlude(focus, desiredEye);
            transform.position = follow >= 0.999f
                ? desiredEye
                : Vector3.Lerp(transform.position, desiredEye, follow);
            transform.LookAt(focus, Vector3.up);
        }

        static Vector3 Occlude(Vector3 focus, Vector3 desiredEye)
        {
            var offset = desiredEye - focus;
            var dist = offset.magnitude;
            if (dist < 0.05f)
                return desiredEye;
            var dir = offset / dist;
            if (Physics.SphereCast(focus, GameConstants.CameraOcclusionRadius, dir, out var hit, dist,
                    OcclusionMask, QueryTriggerInteraction.Ignore))
                return hit.point + hit.normal * 0.12f;
            return desiredEye;
        }
    }
}
