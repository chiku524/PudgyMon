using System.Collections.Generic;
using UnityEngine;

namespace PudgyMon
{
    public sealed class StageRuntime : MonoBehaviour
    {
        PartyDirector _director;
        StudioAssets _studio;
        ActiveMaps _maps;
        ChallengeBoard _challenges;
        PartyAudio _audio;
        Transform _stageRoot;
        PartyPhase _booted = (PartyPhase)(-1);

        readonly byte[] _nextGate = new byte[16];
        readonly List<int> _raceFinished = new List<int>();
        int _gateCount;
        readonly List<Transform> _gates = new List<Transform>();

        readonly uint[] _vibeCollected = new uint[16];
        readonly List<Transform> _orbs = new List<Transform>();

        readonly uint[] _kos = new uint[16];
        readonly float[] _shootCd = new float[16];
        readonly List<Projectile> _shots = new List<Projectile>();

        readonly float[] _hold = new float[16];
        readonly uint[] _awarded = new uint[16];
        readonly List<Vector3> _hills = new List<Vector3>();
        float _hillRadius = 4.5f;
        float _hillSwitch = 12f;
        float _hillStartTimer;
        int _announcedHill;
        Transform _hillZone;
        Renderer _hillRenderer;
        Color _hillColor;
        readonly List<PlayerMotor> _kothOccupants = new List<PlayerMotor>();

        struct Projectile
        {
            public Transform Transform;
            public int Owner;
            public Vector3 Velocity;
            public float Ttl;
        }

        public void Init(PartyDirector director, StudioAssets studio, ActiveMaps maps, ChallengeBoard challenges,
            PartyAudio audio)
        {
            _director = director;
            _studio = studio;
            _maps = maps;
            _challenges = challenges;
            _audio = audio;
            _stageRoot = new GameObject("StageRoot").transform;
            _stageRoot.SetParent(transform, false);
        }

        public void Tick(float dt, IReadOnlyList<PlayerMotor> players, ThirdPersonCameraRig cam)
        {
            if (_director.Phase != _booted)
            {
                ClearStage();
                _booted = _director.Phase;
                switch (_director.Phase)
                {
                    case PartyPhase.Race:
                        BootRace(players);
                        break;
                    case PartyPhase.Vibe:
                        BootVibe(players);
                        break;
                    case PartyPhase.Shooter:
                        BootShooter(players);
                        break;
                    case PartyPhase.Koth:
                        BootKoth(players);
                        break;
                    case PartyPhase.Hub:
                    case PartyPhase.Results:
                        ReturnPlayers(players);
                        break;
                }
            }

            switch (_director.Phase)
            {
                case PartyPhase.Race:
                    TickRace(dt, players);
                    break;
                case PartyPhase.Vibe:
                    TickVibe(dt, players);
                    break;
                case PartyPhase.Shooter:
                    TickShooter(dt, players, cam);
                    break;
                case PartyPhase.Koth:
                    TickKoth(dt, players);
                    break;
            }
        }

        void ClearStage()
        {
            _gates.Clear();
            _orbs.Clear();
            _shots.Clear();
            _hills.Clear();
            _hillZone = null;
            _hillRenderer = null;
            for (int i = _stageRoot.childCount - 1; i >= 0; i--)
                Destroy(_stageRoot.GetChild(i).gameObject);
        }

        void ReturnPlayers(IReadOnlyList<PlayerMotor> players)
        {
            foreach (var p in players)
                p.Teleport(GameConstants.HubSpawn + new Vector3(p.Slot * 2.2f - 2f, 0f, 0f));
        }

        void BootRace(IReadOnlyList<PlayerMotor> players)
        {
            System.Array.Clear(_nextGate, 0, _nextGate.Length);
            _raceFinished.Clear();
            var hub = GameConstants.HubSpawn;
            var custom = _maps?.Race;
            Vector3[] gates;
            Vector3 spawnBase;
            if (custom != null && custom.Gates.Count >= 2)
            {
                gates = new Vector3[custom.Gates.Count];
                for (int i = 0; i < custom.Gates.Count; i++)
                    gates[i] = new Vector3(custom.Gates[i][0], custom.Gates[i][1], custom.Gates[i][2]);
                var s = custom.Spawns[0];
                spawnBase = new Vector3(s[0], s[1], s[2]);
                SpawnBlocks(custom.Blocks);
            }
            else
            {
                gates = new[]
                {
                    hub + new Vector3(-12f, 1f, 4f),
                    hub + new Vector3(0f, 1f, -8f),
                    hub + new Vector3(12f, 1f, 4f),
                    hub + new Vector3(0f, 1f, 20f)
                };
                spawnBase = hub + new Vector3(0f, 0f, 20f);
            }

            _gateCount = gates.Length;
            for (int i = 0; i < gates.Length; i++)
            {
                var go = PrimitiveFactory.Create(PrimitiveType.Cube, gates[i], new Vector3(3f, 2.5f, 0.4f),
                    new Color(0.2f, 0.85f, 1f), _stageRoot, $"RaceGate_{i}", true,
                    new Color(0.2f, 1.2f, 1.8f));
                _gates.Add(go.transform);
                _studio.QueueProp("prop_race_checkpoint_01", gates[i], Quaternion.identity, _stageRoot,
                    $"RaceGateVisual_{i}", PrimitiveType.Cube, new Vector3(3f, 2.5f, 0.4f),
                    new Color(0.2f, 0.85f, 1f), true);
            }

            foreach (var p in players)
                p.Teleport(spawnBase + new Vector3(p.Slot * 2.2f - 4f, 0f, 0f));
        }

        void TickRace(float dt, IReadOnlyList<PlayerMotor> players)
        {
            foreach (var p in players)
            {
                if (p.Slot >= _nextGate.Length || _raceFinished.Contains(p.Slot))
                    continue;
                var need = _nextGate[p.Slot];
                if (need >= _gates.Count)
                    continue;
                var gatePos = _gates[need].position;
                if (p.IsBot)
                    p.ApplyMove((gatePos - p.transform.position).normalized, false, false, dt);

                if (Vector3.Distance(p.transform.position, gatePos) < 2.4f)
                {
                    _nextGate[p.Slot] = (byte)(need + 1);
                    if (_nextGate[p.Slot] >= _gateCount)
                    {
                        _raceFinished.Add(p.Slot);
                        var place = _raceFinished.Count;
                        uint pts = place switch { 1 => 25, 2 => 18, 3 => 12, _ => 6 };
                        _director.AddPoints(p.Slot, pts);
                        if (p.IsLocal)
                        {
                            _director.Announcer = $"You finished race #{place} (+{pts})";
                            _audio?.Finish();
                            if (place <= 3)
                                _challenges?.Bump("race_podium", 1);
                        }
                    }
                }
            }
        }

        void BootVibe(IReadOnlyList<PlayerMotor> players)
        {
            System.Array.Clear(_vibeCollected, 0, _vibeCollected.Length);
            var hub = GameConstants.HubSpawn;
            var custom = _maps?.Vibe;
            List<Vector3> orbs = new List<Vector3>();
            Vector3 spawnBase;
            if (custom != null && custom.Orbs.Count >= 3)
            {
                foreach (var o in custom.Orbs)
                    orbs.Add(new Vector3(o[0], o[1], o[2]));
                var s = custom.Spawns[0];
                spawnBase = new Vector3(s[0], s[1], s[2]);
                SpawnBlocks(custom.Blocks);
            }
            else
            {
                for (int i = 0; i < 16; i++)
                {
                    var angle = i * 0.7f;
                    orbs.Add(hub + new Vector3(Mathf.Cos(angle) * 16f, 0.6f, Mathf.Sin(angle) * 16f));
                }
                spawnBase = hub;
            }

            for (int i = 0; i < orbs.Count; i++)
            {
                var go = PrimitiveFactory.Create(PrimitiveType.Sphere, orbs[i], new Vector3(0.45f, 0.45f, 0.45f),
                    new Color(1f, 0.9f, 0.2f), _stageRoot, $"Vibe_{i}", true, new Color(2.5f, 2f, 0.3f));
                _orbs.Add(go.transform);
            }

            foreach (var p in players)
                p.Teleport(spawnBase + new Vector3(p.Slot * 2f - 3f, 0f, 0f));
        }

        void TickVibe(float dt, IReadOnlyList<PlayerMotor> players)
        {
            Transform firstOrb = null;
            foreach (var o in _orbs)
            {
                if (o != null)
                {
                    firstOrb = o;
                    break;
                }
            }

            foreach (var p in players)
            {
                if (p.IsBot && firstOrb != null)
                    p.ApplyMove((firstOrb.position - p.transform.position).normalized, false, false, dt);

                for (int i = 0; i < _orbs.Count; i++)
                {
                    var orb = _orbs[i];
                    if (orb == null)
                        continue;
                    if (Vector3.Distance(p.transform.position, orb.position) < 1.4f)
                    {
                        Destroy(orb.gameObject);
                        _orbs[i] = null;
                        if (p.Slot < _vibeCollected.Length)
                        {
                            _vibeCollected[p.Slot] += 1;
                            _director.AddPoints(p.Slot, 3);
                            if (p.IsLocal)
                            {
                                _challenges?.SetMax("vibe_10", _vibeCollected[p.Slot]);
                                _director.Announcer = $"Vibe! ({_vibeCollected[p.Slot]})";
                                _audio?.Pickup();
                            }
                        }

                        break;
                    }
                }
            }
        }

        void BootShooter(IReadOnlyList<PlayerMotor> players)
        {
            System.Array.Clear(_kos, 0, _kos.Length);
            System.Array.Clear(_shootCd, 0, _shootCd.Length);
            var hub = GameConstants.HubSpawn;
            var custom = _maps?.Shooter;
            if (custom != null && custom.Cover.Count > 0)
            {
                SpawnBlocks(custom.Cover);
                for (int i = 0; i < players.Count; i++)
                {
                    var s = custom.Spawns[Mathf.Min(i, custom.Spawns.Count - 1)];
                    players[i].Teleport(new Vector3(s[0], s[1], s[2]));
                }
            }
            else
            {
                (string id, Vector3 offset, float yaw)[] cover =
                {
                    ("prop_cover_block_01", new Vector3(-6f, 0f, -6f), 20f),
                    ("prop_cover_block_01", new Vector3(6f, 0f, -6f), -20f),
                    ("prop_cover_block_01", new Vector3(0f, 0f, -12f), 0f),
                    ("prop_target_star_01", new Vector3(-10f, 0f, -10f), 45f),
                    ("prop_target_star_01", new Vector3(10f, 0f, -10f), -45f),
                    ("prop_blaster_toy_01", new Vector3(0f, 0f, -4f), 180f)
                };
                foreach (var c in cover)
                {
                    _studio.QueueProp(c.id, hub + c.offset, Quaternion.Euler(0f, c.yaw, 0f), _stageRoot,
                        $"Shooter_{c.id}", PrimitiveType.Cube, new Vector3(1.6f, 1.2f, 1.6f),
                        new Color(0.45f, 0.5f, 0.55f));
                }

                foreach (var p in players)
                {
                    var angle = p.Slot * 0.9f;
                    p.Teleport(hub + new Vector3(Mathf.Cos(angle) * 12f, 0f, Mathf.Sin(angle) * 12f - 8f));
                }
            }
        }

        void TickShooter(float dt, IReadOnlyList<PlayerMotor> players, ThirdPersonCameraRig cam)
        {
            for (int i = 0; i < _shootCd.Length; i++)
                _shootCd[i] = Mathf.Max(0f, _shootCd[i] - dt);

            foreach (var p in players)
            {
                var want = p.IsLocal
                    ? Input.GetMouseButtonDown(0) || Input.GetKeyDown(KeyCode.F)
                    : p.IsBot && _shootCd[p.Slot] <= 0f && Mathf.Sin(Time.time * 2.7f + p.Slot) > 0.9f;
                if (want && p.Slot < _shootCd.Length && _shootCd[p.Slot] <= 0f)
                {
                    _shootCd[p.Slot] = p.IsBot ? 0.95f : 0.35f;
                    var forward = p.IsLocal && cam != null
                        ? cam.PlanarForward
                        : Vector3.ProjectOnPlane(p.transform.forward, Vector3.up).normalized;
                    var ball = PrimitiveFactory.Create(PrimitiveType.Sphere,
                        p.transform.position + Vector3.up * 1.1f + forward, new Vector3(0.18f, 0.18f, 0.18f),
                        new Color(1f, 0.4f, 0.2f), _stageRoot, "Projectile", true, new Color(2f, 0.6f, 0.2f));
                    _shots.Add(new Projectile
                    {
                        Transform = ball.transform,
                        Owner = p.Slot,
                        Velocity = forward * 22f,
                        Ttl = 1.2f
                    });
                }

                if (p.IsBot)
                {
                    var wander = new Vector3(Mathf.Sin(Time.time), 0f, Mathf.Cos(Time.time));
                    p.ApplyMove(wander, false, false, dt);
                }
            }

            for (int i = _shots.Count - 1; i >= 0; i--)
            {
                var shot = _shots[i];
                if (shot.Transform == null)
                {
                    _shots.RemoveAt(i);
                    continue;
                }

                shot.Ttl -= dt;
                shot.Transform.position += shot.Velocity * dt;
                var hit = false;
                if (shot.Ttl <= 0f)
                {
                    Destroy(shot.Transform.gameObject);
                    _shots.RemoveAt(i);
                    continue;
                }

                foreach (var p in players)
                {
                    if (p.Slot == shot.Owner)
                        continue;
                    if (Vector3.Distance(shot.Transform.position, p.transform.position) < 1.15f)
                    {
                        _kos[shot.Owner] += 1;
                        _director.AddPoints(shot.Owner, 8);
                        if (players[0].Slot == shot.Owner && players[0].IsLocal)
                        {
                            _director.Announcer = $"KO! ({_kos[shot.Owner]} total)";
                            _challenges?.SetMax("ko_5", _kos[shot.Owner]);
                            _audio?.Ko();
                        }
                        var push = new Vector3(Mathf.Sin(Time.time * 11f), 0f, Mathf.Cos(Time.time * 9f)).normalized;
                        p.Teleport(p.transform.position + push * 1.4f);
                        Destroy(shot.Transform.gameObject);
                        _shots.RemoveAt(i);
                        hit = true;
                        break;
                    }
                }

                if (!hit)
                    _shots[i] = shot;
            }
        }

        void BootKoth(IReadOnlyList<PlayerMotor> players)
        {
            System.Array.Clear(_hold, 0, _hold.Length);
            System.Array.Clear(_awarded, 0, _awarded.Length);
            var hub = GameConstants.HubSpawn;
            var custom = _maps?.Koth;
            _hills.Clear();
            if (custom != null && custom.Hills.Count > 0)
            {
                foreach (var h in custom.Hills)
                    _hills.Add(new Vector3(h[0], h[1], h[2]));
                _hillRadius = custom.HillRadius;
                _hillSwitch = custom.HillSwitchSecs;
                SpawnBlocks(custom.Blocks);
                for (int i = 0; i < players.Count; i++)
                {
                    var s = custom.Spawns[Mathf.Min(i, custom.Spawns.Count - 1)];
                    players[i].Teleport(new Vector3(s[0], s[1], s[2]));
                }
            }
            else
            {
                _hills.Add(hub + new Vector3(0f, 0f, -6f));
                _hills.Add(hub + new Vector3(13f, 0f, -14f));
                _hills.Add(hub + new Vector3(-13f, 0f, 2f));
                _hillRadius = 4.5f;
                _hillSwitch = 12f;
                Vector3[] spawns =
                {
                    new Vector3(hub.x, 1f, hub.z + 8f),
                    new Vector3(hub.x + 12f, 1f, hub.z - 10f),
                    new Vector3(hub.x - 12f, 1f, hub.z - 10f),
                    new Vector3(hub.x, 1f, hub.z - 18f)
                };
                foreach (var p in players)
                    p.Teleport(spawns[p.Slot % spawns.Length]);
            }

            _hillStartTimer = _director.PhaseTimer;
            _announcedHill = 0;
            var first = _hills[0];
            var zone = PrimitiveFactory.Create(PrimitiveType.Cylinder, new Vector3(first.x, 0.12f, first.z),
                new Vector3(_hillRadius, 0.25f, _hillRadius), new Color(1f, 0.8f, 0.2f, 0.65f), _stageRoot,
                "HillZone", true, new Color(1.6f, 1.1f, 0.2f));
            _hillZone = zone.transform;
            _hillRenderer = zone.GetComponent<Renderer>();
        }

        void SpawnBlocks(List<MapBlock> blocks)
        {
            if (blocks == null) return;
            for (int i = 0; i < blocks.Count; i++)
            {
                var b = blocks[i];
                var pos = new Vector3(b.Pos[0], b.Pos[1], b.Pos[2]);
                var size = new Vector3(Mathf.Max(0.5f, b.Size[0]), Mathf.Max(0.5f, b.Size[1]),
                    Mathf.Max(0.5f, b.Size[2]));
                if (!string.IsNullOrEmpty(b.AssetId))
                    _studio.QueueProp(b.AssetId, pos, Quaternion.identity, _stageRoot, $"Block_{i}",
                        PrimitiveType.Cube, size, new Color(0.5f, 0.45f, 0.4f));
                else
                    PrimitiveFactory.Create(PrimitiveType.Cube, pos, size, new Color(0.5f, 0.45f, 0.4f),
                        _stageRoot, $"Block_{i}", solid: true);
            }
        }

        void TickKoth(float dt, IReadOnlyList<PlayerMotor> players)
        {
            var center = HillCenter(_director.PhaseTimer);
            if (_hillZone != null)
                _hillZone.position = new Vector3(center.x, 0.12f, center.z);

            var idx = ActiveHillIndex(_director.PhaseTimer);
            if (_announcedHill != idx)
            {
                _announcedHill = idx;
                _director.Announcer = "The hill is on the move — chase it!";
            }

            _kothOccupants.Clear();
            foreach (var p in players)
            {
                if (p.IsBot)
                {
                    var wobble = new Vector3(Mathf.Sin(Time.time * 1.3f + p.Slot), 0f,
                        Mathf.Cos(Time.time * 1.1f + p.Slot * 2f)) * (_hillRadius * 0.4f);
                    p.ApplyMove((center + wobble - p.transform.position).normalized, false, false, dt);
                }

                var xz = new Vector2(p.transform.position.x, p.transform.position.z);
                if (Vector2.Distance(xz, new Vector2(center.x, center.z)) < _hillRadius)
                    _kothOccupants.Add(p);
            }

            Color hillColor = _kothOccupants.Count == 0
                ? new Color(1f, 0.8f, 0.2f)
                : _kothOccupants.Count == 1
                    ? new Color(0.3f, 1f, 0.45f)
                    : new Color(1f, 0.3f, 0.3f);
            if (_hillRenderer != null && _hillColor != hillColor)
            {
                _hillColor = hillColor;
                _hillRenderer.sharedMaterial = PrimitiveFactory.Lit(hillColor, hillColor * 1.4f, true);
            }

            if (_kothOccupants.Count == 1)
            {
                var slot = _kothOccupants[0].Slot;
                _hold[slot] += dt;
                var total = (uint)_hold[slot];
                if (total > _awarded[slot])
                {
                    _director.AddPoints(slot, total - _awarded[slot]);
                    _awarded[slot] = total;
                    if (_kothOccupants[0].IsLocal)
                        _director.Announcer = $"You are king! ({_hold[slot]:0}s held)";
                }
            }
        }

        int ActiveHillIndex(float phaseTimer)
        {
            if (_hills.Count == 0)
                return 0;
            var elapsed = Mathf.Max(0f, _hillStartTimer - phaseTimer);
            return (int)(elapsed / Mathf.Max(1f, _hillSwitch)) % _hills.Count;
        }

        Vector3 HillCenter(float phaseTimer)
        {
            var idx = ActiveHillIndex(phaseTimer);
            var current = _hills[idx];
            var elapsed = Mathf.Max(0f, _hillStartTimer - phaseTimer);
            var switchSecs = Mathf.Max(1f, _hillSwitch);
            if (elapsed < switchSecs || _hills.Count < 2)
                return current;
            var previous = _hills[(idx + _hills.Count - 1) % _hills.Count];
            var into = elapsed % switchSecs;
            var span = Vector3.Distance(previous, current);
            var travelled = 14f * into;
            if (travelled >= span || span <= 0.0001f)
                return current;
            return Vector3.Lerp(previous, current, travelled / span);
        }
    }
}
