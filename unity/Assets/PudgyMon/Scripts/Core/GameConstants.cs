using UnityEngine;

namespace PudgyMon
{
    public static class GameConstants
    {
        public const float PlayerSpeed = 5.5f;
        public const float PlayerSprintMultiplier = 1.45f;
        public const float PlayerFloorY = 1.0f;
        public const float PlayerGravity = 24.0f;
        public const float PlayerJumpVelocity = 14.697f;
        public const float PlayerDoubleJumpVelocity = 17.664f;
        public const int PlayerMaxAirJumps = 1;

        public const float WorldBounds = 70.0f;
        public const float ArenaBounds = 48.0f;
        public const float InteractRadius = 2.8f;

        public const float MouseSensitivity = 0.0025f;
        public const float CameraMinDistance = 2.5f;
        public const float CameraMaxDistance = 12.0f;
        public const float CameraDefaultDistance = 6.5f;
        public const float CameraFocusHeight = 1.15f;
        public const float CameraDefaultYaw = 180f;
        public const float CameraDefaultPitch = 18f;
        public const float CameraOcclusionRadius = 0.22f;

        public const int PlayerLayer = 8;
        public const int GroundLayer = 9;
        public const float PlayerHeight = 1.6f;
        public const float PlayerRadius = 0.38f;

        public static Vector3 HubSpawn = new Vector3(0f, PlayerFloorY, 14f);

        public static Vector3 ClampToIsland(Vector3 pos)
        {
            var xz = new Vector2(pos.x, pos.z);
            var len = xz.magnitude;
            if (len > WorldBounds)
            {
                xz *= WorldBounds / len;
                pos.x = xz.x;
                pos.z = xz.y;
            }

            return pos;
        }
    }

    public enum PartyPhase
    {
        Hub,
        Race,
        Intermission,
        Vibe,
        Shooter,
        Koth,
        Results
    }

    public enum StageKind
    {
        Race,
        Vibe,
        Shooter,
        Koth
    }

    public enum PartyPlanKind
    {
        Idle,
        FullParty,
        Single
    }

    public struct PartyPlan
    {
        public PartyPlanKind Kind;
        public StageKind Stage;

        public static PartyPlan Idle => new PartyPlan { Kind = PartyPlanKind.Idle };
        public static PartyPlan FullParty => new PartyPlan { Kind = PartyPlanKind.FullParty };

        public static PartyPlan Single(StageKind stage) =>
            new PartyPlan { Kind = PartyPlanKind.Single, Stage = stage };

        public string Label => Kind switch
        {
            PartyPlanKind.FullParty => "Party Saga (all 4)",
            PartyPlanKind.Single => StageLabel(Stage),
            _ => "Idle"
        };

        public static string StageLabel(StageKind kind) => kind switch
        {
            StageKind.Race => "Race",
            StageKind.Vibe => "Vibe Collect",
            StageKind.Shooter => "Shooter",
            StageKind.Koth => "King of the Hill",
            _ => "Stage"
        };

        public static PartyPhase PhaseFor(StageKind kind) => kind switch
        {
            StageKind.Race => PartyPhase.Race,
            StageKind.Vibe => PartyPhase.Vibe,
            StageKind.Shooter => PartyPhase.Shooter,
            StageKind.Koth => PartyPhase.Koth,
            _ => PartyPhase.Hub
        };

        public static float StageSecs(StageKind kind) => kind switch
        {
            StageKind.Race => 45f,
            StageKind.Vibe => 40f,
            StageKind.Shooter => 35f,
            StageKind.Koth => 40f,
            _ => 40f
        };
    }
}
