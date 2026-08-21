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

        public void ApplyMove(Vector3 direction, bool sprint, bool jumpPressed, float dt)
        {
            if (Frozen)
                return;

            direction.y = 0f;
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
                transform.position += flat * Speed * dt;
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

            if (!Grounded)
            {
                VerticalVelocity -= GameConstants.PlayerGravity * dt;
                var p = transform.position;
                p.y += VerticalVelocity * dt;
                transform.position = p;
            }

            var pos = transform.position;
            if (pos.y <= GameConstants.PlayerFloorY)
            {
                pos.y = GameConstants.PlayerFloorY;
                if (VerticalVelocity < 0f)
                    VerticalVelocity = 0f;
                Grounded = true;
                AirJumpsLeft = GameConstants.PlayerMaxAirJumps;
            }
            else
            {
                Grounded = false;
            }

            transform.position = GameConstants.ClampToIsland(pos);
        }

        public void Teleport(Vector3 world)
        {
            world.y = GameConstants.PlayerFloorY;
            transform.position = GameConstants.ClampToIsland(world);
            VerticalVelocity = 0f;
            Grounded = true;
        }
    }
}
