using UnityEngine;

namespace PudgyMon
{
    /// <summary>
    /// Authoritative Party Saga phase machine.
    /// </summary>
    public sealed class PartyDirector
    {
        public PartyPhase Phase = PartyPhase.Hub;
        public float PhaseTimer = 9999f;
        public int StageIndex;
        public string Announcer = "Welcome to The Nest — walk a pad and press E to play.";
        public PartyPlan Plan = PartyPlan.Idle;
        public readonly uint[] MatchPoints = new uint[16];
        public PartyPlan? Queued;

        public void ResetParty()
        {
            Phase = PartyPhase.Hub;
            PhaseTimer = 9999f;
            StageIndex = 0;
            Announcer = "Welcome to The Nest — walk a pad and press E to play.";
            Plan = PartyPlan.Idle;
            System.Array.Clear(MatchPoints, 0, MatchPoints.Length);
            Queued = null;
        }

        public void AddPoints(int slot, uint pts)
        {
            if (slot >= 0 && slot < MatchPoints.Length)
                MatchPoints[slot] += pts;
        }

        public void Queue(PartyPlan plan) => Queued = plan;

        public void Tick(float dt, SeasonLedger season, ChallengeBoard challenges = null)
        {
            if (Phase == PartyPhase.Hub)
            {
                if (Queued.HasValue)
                {
                    var plan = Queued.Value;
                    Queued = null;
                    Plan = plan;
                    System.Array.Clear(MatchPoints, 0, MatchPoints.Length);
                    switch (plan.Kind)
                    {
                        case PartyPlanKind.FullParty:
                            Begin(PartyPhase.Race, PartyPlan.StageSecs(StageKind.Race), "Party Saga — Race first!");
                            StageIndex = 0;
                            break;
                        case PartyPlanKind.Single:
                            Begin(PartyPlan.PhaseFor(plan.Stage), PartyPlan.StageSecs(plan.Stage),
                                $"{plan.Label} — go!");
                            StageIndex = 0;
                            break;
                    }
                }

                return;
            }

            PhaseTimer -= dt;
            if (PhaseTimer > 0f)
                return;

            switch (Phase)
            {
                case PartyPhase.Race when Plan.Kind == PartyPlanKind.Single && Plan.Stage == StageKind.Race:
                case PartyPhase.Vibe when Plan.Kind == PartyPlanKind.Single && Plan.Stage == StageKind.Vibe:
                case PartyPhase.Shooter when Plan.Kind == PartyPlanKind.Single && Plan.Stage == StageKind.Shooter:
                case PartyPhase.Koth when Plan.Kind == PartyPlanKind.Single && Plan.Stage == StageKind.Koth:
                case PartyPhase.Koth when Plan.Kind == PartyPlanKind.FullParty:
                    FinishMatch(season, challenges);
                    break;
                case PartyPhase.Race when Plan.Kind == PartyPlanKind.FullParty:
                    Begin(PartyPhase.Intermission, 3f, "Vibe Collect up next…");
                    StageIndex = 1;
                    break;
                case PartyPhase.Intermission when Plan.Kind == PartyPlanKind.FullParty && StageIndex == 1:
                    Begin(PartyPhase.Vibe, PartyPlan.StageSecs(StageKind.Vibe), "Grab the vibes — yellow orbs!");
                    break;
                case PartyPhase.Vibe when Plan.Kind == PartyPlanKind.FullParty:
                    Begin(PartyPhase.Intermission, 3f, "Shooter up next…");
                    StageIndex = 2;
                    break;
                case PartyPhase.Intermission when Plan.Kind == PartyPlanKind.FullParty && StageIndex == 2:
                    Begin(PartyPhase.Shooter, PartyPlan.StageSecs(StageKind.Shooter), "Toy blasters — rack up KOs!");
                    break;
                case PartyPhase.Shooter when Plan.Kind == PartyPlanKind.FullParty:
                    Begin(PartyPhase.Intermission, 3f, "King of the Hill finale incoming…");
                    StageIndex = 3;
                    break;
                case PartyPhase.Intermission when Plan.Kind == PartyPlanKind.FullParty && StageIndex == 3:
                    Begin(PartyPhase.Koth, PartyPlan.StageSecs(StageKind.Koth), "Hold the glowing hill — it moves!");
                    break;
                case PartyPhase.Results:
                    ResetParty();
                    Announcer = "Back in The Nest — pick another pad.";
                    break;
                default:
                    Begin(PartyPhase.Hub, 9999f, "Back at the hub.");
                    Plan = PartyPlan.Idle;
                    break;
            }
        }

        public void ReturnToNest()
        {
            ResetParty();
            Announcer = "Back in The Nest — pick another pad.";
        }

        void Begin(PartyPhase phase, float secs, string line)
        {
            Phase = phase;
            PhaseTimer = secs;
            Announcer = line;
        }

        void FinishMatch(SeasonLedger season, ChallengeBoard challenges)
        {
            uint sum = 0;
            for (int i = 0; i < 8; i++)
                sum += MatchPoints[i];
            uint earned = System.Math.Max(sum, 10u) / 4u;
            uint localBest = MatchPoints[0];
            uint award = System.Math.Max(localBest, System.Math.Min(earned, 50u));
            season.AddPoints(award);
            challenges?.Bump("play_3", 1);
            challenges?.ClaimReady(season);
            Begin(PartyPhase.Results, 6f, $"Results! You scored {localBest} party pts · season +{award}");
        }
    }
}
