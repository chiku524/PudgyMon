using UnityEngine;

namespace PudgyMon
{
    public sealed class ThirdPersonCameraRig : MonoBehaviour
    {
        public Transform Target;
        public float Yaw;
        public float Pitch = -0.35f;
        public float Distance = GameConstants.CameraDefaultDistance;
        public bool Captured = true;

        public void TickLook()
        {
            if (Target == null)
                return;

            if (Input.GetKeyDown(KeyCode.BackQuote))
            {
                Captured = !Captured;
                Cursor.lockState = Captured ? CursorLockMode.Locked : CursorLockMode.None;
                Cursor.visible = !Captured;
            }

            if (Captured)
            {
                var delta = Input.mousePositionDelta;
                Yaw -= delta.x * GameConstants.MouseSensitivity;
                Pitch = Mathf.Clamp(
                    Pitch - delta.y * GameConstants.MouseSensitivity,
                    GameConstants.MinCameraPitch,
                    GameConstants.MaxCameraPitch);
                Distance = Mathf.Clamp(
                    Distance - Input.mouseScrollDelta.y * 0.5f,
                    GameConstants.CameraMinDistance,
                    GameConstants.CameraMaxDistance);
            }

            var focus = Target.position + Vector3.up * 1.15f;
            var horizontal = Distance * Mathf.Cos(Pitch);
            var desiredEye = focus + new Vector3(
                horizontal * Mathf.Sin(Yaw),
                -Distance * Mathf.Sin(Pitch),
                horizontal * Mathf.Cos(Yaw));
            var t = 1f - Mathf.Exp(-22f * Time.deltaTime);
            transform.position = Vector3.Lerp(transform.position, desiredEye, t);
            transform.LookAt(focus, Vector3.up);
        }

        public Vector3 PlanarForward
        {
            get
            {
                var f = new Vector3(-Mathf.Sin(Yaw), 0f, -Mathf.Cos(Yaw));
                return f.sqrMagnitude > 0f ? f.normalized : Vector3.forward;
            }
        }

        public Vector3 PlanarRight => new Vector3(Mathf.Cos(Yaw), 0f, -Mathf.Sin(Yaw));
    }
}
