using UnityEngine;

namespace PudgyMon
{
    public sealed class PlayerMotor : MonoBehaviour
    {
        public int Slot;
        public bool IsLocal;
        public bool IsBot;
        public bool Frozen;

        public float Speed;
        public bool Sprint;
        public float VerticalVelocity;
        public bool Grounded = true;
        public int AirJumpsLeft = GameConstants.PlayerMaxAirJumps;

        CharacterController _cc;

        public void BindController(CharacterController cc) => _cc = cc;

        public void ApplyMove(Vector3 direction, bool sprint, bool jumpPressed, float dt)
        {
            if (Frozen)
                return;

            EnsureController();
            direction.y = 0f;

            var motion = Vector3.zero;
            if (direction.sqrMagnitude <= Mathf.Epsilon)
            {
                Speed = 0f;
                Sprint = false;
            }
            else
            {
                Speed = sprint
                    ? GameConstants.PlayerSpeed * GameConstants.PlayerSprintMultiplier
                    : GameConstants.PlayerSpeed;
                Sprint = sprint;
                var flat = direction.normalized;
                motion = flat * Speed;
                transform.rotation = Quaternion.LookRotation(flat, Vector3.up);
            }

            if (jumpPressed)
            {
                if (Grounded)
                {
                    VerticalVelocity = GameConstants.PlayerJumpVelocity;
                    Grounded = false;
                    AirJumpsLeft = GameConstants.PlayerMaxAirJumps;
                }
                else if (AirJumpsLeft > 0)
                {
                    VerticalVelocity = GameConstants.PlayerDoubleJumpVelocity;
                    AirJumpsLeft -= 1;
                }
            }

            if (Grounded && VerticalVelocity < 0f)
                VerticalVelocity = -2f;
            else
                VerticalVelocity -= GameConstants.PlayerGravity * dt;

            motion.y = VerticalVelocity;

            if (_cc != null && _cc.enabled)
            {
                var flags = _cc.Move(motion * dt);
                Grounded = (flags & CollisionFlags.Below) != 0;
                if ((flags & CollisionFlags.Above) != 0 && VerticalVelocity > 0f)
                    VerticalVelocity = 0f;
            }
            else
            {
                transform.position += motion * dt;
            }

            var pos = transform.position;
            if (pos.y < GameConstants.PlayerFloorY - 0.05f)
            {
                pos.y = GameConstants.PlayerFloorY;
                if (VerticalVelocity < 0f)
                    VerticalVelocity = 0f;
                Grounded = true;
                AirJumpsLeft = GameConstants.PlayerMaxAirJumps;
                SetPosition(pos);
            }

            var clamped = GameConstants.ClampToIsland(transform.position);
            if ((clamped - transform.position).sqrMagnitude > 0.0001f)
                SetPosition(clamped);

            if (Grounded)
                AirJumpsLeft = GameConstants.PlayerMaxAirJumps;
        }

        public void Teleport(Vector3 world)
        {
            world.y = GameConstants.PlayerFloorY;
            world = GameConstants.ClampToIsland(world);
            VerticalVelocity = 0f;
            Grounded = true;
            AirJumpsLeft = GameConstants.PlayerMaxAirJumps;
            SetPosition(world);
        }

        void SetPosition(Vector3 world)
        {
            if (_cc != null)
            {
                _cc.enabled = false;
                transform.position = world;
                _cc.enabled = true;
            }
            else
            {
                transform.position = world;
            }
        }

        void EnsureController()
        {
            if (_cc == null)
                _cc = GetComponent<CharacterController>();
        }
    }
}
