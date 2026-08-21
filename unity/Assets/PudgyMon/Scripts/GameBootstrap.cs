using System.Collections.Generic;
using UnityEngine;

namespace PudgyMon
{
    /// <summary>
    /// Boots The Nest and the Party Saga loop inside Unity.
    /// Drop this on an empty scene object (or open Scenes/Nest).
    /// </summary>
    public sealed class GameBootstrap : MonoBehaviour
    {
        public int BotFill = 4;

        PartyDirector _director;
        SeasonLedger _season;
        CosmeticsCatalog _cosmetics;
        StudioAssets _studio;
        NestHub _nest;
        StageRuntime _stages;
        GameHud _hud;
        ThirdPersonCameraRig _camera;
        Light _key;
        Light _fill;
        readonly List<PlayerMotor> _players = new List<PlayerMotor>();
        PlayerAvatar _localAvatar;
        bool _cursorBound;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void AutoBoot()
        {
            if (FindFirstObjectByType<GameBootstrap>() != null)
                return;
            var go = new GameObject("PudgyMon");
            go.AddComponent<GameBootstrap>();
        }

        void Awake()
        {
            Application.runInBackground = true;
            Application.targetFrameRate = 60;
            DontDestroyOnLoad(gameObject);

            EnsureCameraAndLights();

            _director = new PartyDirector();
            _season = SeasonLedger.Load();
            _cosmetics = CosmeticsCatalog.Load();

            _studio = gameObject.AddComponent<StudioAssets>();
            _studio.Init(StudioRegistry.Load());

            NestWorld.Build(transform);
            _nest = NestHub.Build(transform, _studio, _cosmetics);
            _stages = gameObject.AddComponent<StageRuntime>();
            _stages.Init(_director, _studio);
            _hud = GameHud.Create();

            SpawnRoster();
            BindCamera();
            _hud.BindCursor(true);
            _cursorBound = true;
        }

        void EnsureCameraAndLights()
        {
            if (Camera.main == null)
            {
                var camGo = new GameObject("Main Camera");
                camGo.tag = "MainCamera";
                camGo.AddComponent<Camera>();
                camGo.AddComponent<AudioListener>();
            }

            Camera.main.nearClipPlane = 0.15f;
            Camera.main.farClipPlane = 400f;

            var keyGo = new GameObject("KeyLight");
            _key = keyGo.AddComponent<Light>();
            _key.type = LightType.Directional;
            _key.shadows = LightShadows.Soft;
            _key.color = new Color(1f, 0.95f, 0.88f);
            _key.intensity = 1.1f;
            keyGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            var fillGo = new GameObject("FillLight");
            _fill = fillGo.AddComponent<Light>();
            _fill.type = LightType.Point;
            _fill.range = 55f;
            _fill.color = new Color(0.55f, 0.45f, 1f);
            _fill.intensity = 1.4f;
            fillGo.transform.position = new Vector3(-8f, 8f, 8f);
        }

        void SpawnRoster()
        {
            var tint = _cosmetics.Equipped.Color;
            _localAvatar = PlayerAvatar.Spawn(transform, 0, true, false, GameConstants.HubSpawn, tint, "LocalPlayer");
            _players.Add(_localAvatar.Motor);
            _localAvatar.AttachCrewMesh(_studio, "char_pudgy_base_01");

            for (int i = 0; i < BotFill; i++)
            {
                var slot = i + 1;
                var botTint = new Color(0.5f, 0.55f, 0.65f);
                var bot = PlayerAvatar.Spawn(transform, slot, false, true,
                    GameConstants.HubSpawn + new Vector3(slot * 2.2f, 0f, 0f), botTint, $"PartyBot_{slot}");
                bot.gameObject.SetActive(false);
                _players.Add(bot.Motor);
            }
        }

        void BindCamera()
        {
            _camera = Camera.main.gameObject.AddComponent<ThirdPersonCameraRig>();
            _camera.Target = _localAvatar.transform;
            Camera.main.transform.position = GameConstants.HubSpawn + new Vector3(0f, 12f, 8f);
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape))
                _hud.TogglePause();

            if (_hud.Paused)
            {
                if (Input.GetKeyDown(KeyCode.Q))
                {
                    _director.ReturnToNest();
                    SetBotsActive(false);
                    _hud.TogglePause();
                }

                return;
            }

            NestWorld.ApplyAtmosphere(_key, _fill, _director.Phase);
            _camera.TickLook();
            if (_cursorBound != _camera.Captured)
            {
                _hud.BindCursor(_camera.Captured);
                _cursorBound = _camera.Captured;
            }

            var local = _localAvatar.Motor;
            if (_director.Phase == PartyPhase.Hub || _director.Phase == PartyPhase.Intermission ||
                _director.Phase == PartyPhase.Results || !_localAvatar.Motor.Frozen)
            {
                var dir = Vector3.zero;
                if (Input.GetKey(KeyCode.W)) dir += _camera.PlanarForward;
                if (Input.GetKey(KeyCode.S)) dir -= _camera.PlanarForward;
                if (Input.GetKey(KeyCode.A)) dir -= _camera.PlanarRight;
                if (Input.GetKey(KeyCode.D)) dir += _camera.PlanarRight;
                local.ApplyMove(dir, Input.GetKey(KeyCode.LeftShift), Input.GetKeyDown(KeyCode.Space),
                    Time.deltaTime);
            }

            if (_director.Phase == PartyPhase.Hub)
            {
                _nest.RefreshPrompt(local.transform.position, _director, _cosmetics, _season);
                if (Input.GetKeyDown(KeyCode.E) || Input.GetKeyDown(KeyCode.Return))
                {
                    var pad = _nest.NearestPad(local.transform.position, GameConstants.InteractRadius);
                    if (pad != null)
                    {
                        _director.Queue(pad.Plan);
                        SetBotsActive(true);
                    }
                }

                if (Input.GetKeyDown(KeyCode.C))
                {
                    _cosmetics.Cycle(_season);
                    _localAvatar.ApplyTint(_cosmetics.Equipped.Color);
                    _director.Announcer = $"Skin {_cosmetics.Equipped.label}";
                }
            }

            if (Input.GetKeyDown(KeyCode.Q) && _director.Phase != PartyPhase.Hub)
            {
                _director.ReturnToNest();
                SetBotsActive(false);
            }

            if (Input.GetKeyDown(KeyCode.R) && _director.Phase == PartyPhase.Results && _director.Plan.Kind != PartyPlanKind.Idle)
            {
                _director.Queue(_director.Plan);
                SetBotsActive(true);
            }

            var previous = _director.Phase;
            _director.Tick(Time.deltaTime, _season);
            if (previous != PartyPhase.Hub && _director.Phase == PartyPhase.Hub)
                SetBotsActive(false);

            _stages.Tick(Time.deltaTime, _players.FindAll(p => p.gameObject.activeInHierarchy), _camera);
            _hud.Render(_director, _nest, _season, _cosmetics);
        }

        void SetBotsActive(bool active)
        {
            foreach (var p in _players)
            {
                if (p.IsBot)
                    p.gameObject.SetActive(active);
            }
        }
    }
}
