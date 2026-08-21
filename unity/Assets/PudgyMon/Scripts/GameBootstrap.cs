using System.Collections.Generic;
using UnityEngine;
#if PUDGYMON_URP
using UnityEngine.Rendering.Universal;
#endif

namespace PudgyMon
{
    public sealed class GameBootstrap : MonoBehaviour
    {
        public int BotFill = 4;

        PartyDirector _director;
        SeasonLedger _season;
        CosmeticsCatalog _cosmetics;
        ChallengeBoard _challenges;
        CrewRoster _roster;
        AccessoryCatalog _hats;
        BoingBridge _boing;
        AccountSession _account;
        ActiveMaps _maps;
        StudioAssets _studio;
        NestHub _nest;
        StageRuntime _stages;
        MapEditor _editor;
        GameHud _hud;
        PartyAudio _audio;
        LanSession _lan;
        ThirdPersonCameraRig _camera;
        Light _key;
        Light _fill;
        readonly List<PlayerMotor> _players = new List<PlayerMotor>();
        readonly List<PlayerMotor> _active = new List<PlayerMotor>();
        PlayerAvatar _localAvatar;
        bool _cursorBound;
        int _catalogIndex;
        string _banner = "";

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
            QualitySettings.vSyncCount = 1;
            Application.targetFrameRate = -1;
            QualitySettings.shadowDistance = 80f;
            DontDestroyOnLoad(gameObject);
            EnsureCameraAndLights();

            _director = new PartyDirector();
            _season = SeasonLedger.Load();
            _cosmetics = CosmeticsCatalog.Load();
            _challenges = ChallengeBoard.Load();
            _roster = CrewRoster.Load();
            _hats = AccessoryCatalog.Load();
            _boing = BoingBridge.Load();
            _account = AccountSession.Load();
            _maps = new ActiveMaps();
            if (!string.IsNullOrEmpty(_account.BoingWallet))
                _boing.LinkedAccount = _account.BoingWallet;
            _lan = new LanSession();
            _lan.TryParseCommandLine();

            _studio = gameObject.AddComponent<StudioAssets>();
            _studio.Init(StudioRegistry.Load());
            NestWorld.Build(transform);
            _nest = NestHub.Build(transform, _studio, _cosmetics);
            _audio = gameObject.AddComponent<PartyAudio>();
            _audio.Init();
            _stages = gameObject.AddComponent<StageRuntime>();
            _stages.Init(_director, _studio, _maps, _challenges, _audio);
            _editor = gameObject.AddComponent<MapEditor>();
            _editor.Init(_studio);
            _hud = GameHud.Create();

            SpawnRoster();
            BindCamera();
            _hud.BindCursor(true);
            _cursorBound = true;
        }

        void EnsureCameraAndLights()
        {
            Camera cam;
            if (Camera.main == null)
            {
                var camGo = new GameObject("Main Camera");
                camGo.tag = "MainCamera";
                cam = camGo.AddComponent<Camera>();
                camGo.AddComponent<AudioListener>();
            }
            else
            {
                cam = Camera.main;
            }

            cam.nearClipPlane = 0.15f;
            cam.farClipPlane = 400f;
            cam.fieldOfView = 50f;
            cam.allowHDR = true;
            cam.useOcclusionCulling = true;
            cam.clearFlags = CameraClearFlags.SolidColor;
            var keyGo = new GameObject("KeyLight");
            keyGo.transform.SetParent(transform, false);
            _key = keyGo.AddComponent<Light>();
            _key.type = LightType.Directional;
            _key.shadows = LightShadows.Soft;
            _key.color = new Color(1f, 0.95f, 0.88f);
            _key.intensity = 1.1f;
            keyGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            var fillGo = new GameObject("FillLight");
            fillGo.transform.SetParent(transform, false);
            _fill = fillGo.AddComponent<Light>();
            _fill.type = LightType.Point;
            _fill.range = 55f;
            _fill.color = new Color(0.55f, 0.45f, 1f);
            _fill.intensity = 1.4f;
            fillGo.transform.position = new Vector3(-8f, 8f, 8f);
#if PUDGYMON_URP
            var camData = cam.GetUniversalAdditionalCameraData();
            camData.renderType = CameraRenderType.Base;
            camData.renderShadows = true;
            camData.antialiasing = AntialiasingMode.FastApproximateAntialiasing;
            camData.renderPostProcessing = false;
#endif
        }

        void OnApplicationFocus(bool focus)
        {
            if (_hud == null || _camera == null)
                return;
            if (!focus)
            {
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
            else if (!_hud.Paused)
            {
                _hud.BindCursor(_camera.Captured);
            }
        }

        void OnApplicationQuit()
        {
            Time.timeScale = 1f;
            AudioListener.pause = false;
            _season?.Save();
            _challenges?.Save();
        }

        void SpawnRoster()
        {
            var tint = _cosmetics.Equipped.Color;
            _localAvatar = PlayerAvatar.Spawn(transform, 0, true, false, GameConstants.HubSpawn, tint, "LocalPlayer");
            _localAvatar.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
            _players.Add(_localAvatar.Motor);
            _localAvatar.AttachCrewMesh(_studio, _roster.Current.Id);
            for (int i = 0; i < BotFill; i++)
            {
                var slot = i + 1;
                var bot = PlayerAvatar.Spawn(transform, slot, false, true,
                    GameConstants.HubSpawn + new Vector3(slot * 2.2f, 0f, 0f), new Color(0.5f, 0.55f, 0.65f),
                    $"PartyBot_{slot}");
                bot.gameObject.SetActive(false);
                _players.Add(bot.Motor);
            }
        }

        void BindCamera()
        {
            var cam = Camera.main;
            cam.nearClipPlane = 0.15f;
            cam.farClipPlane = 400f;
            cam.fieldOfView = 50f;
            cam.orthographic = false;
            cam.rect = new Rect(0f, 0f, 1f, 1f);
            cam.depth = -1f;
            _camera = cam.gameObject.GetComponent<ThirdPersonCameraRig>()
                      ?? cam.gameObject.AddComponent<ThirdPersonCameraRig>();
            _camera.Target = _localAvatar.transform;
            _camera.Yaw = GameConstants.CameraDefaultYaw;
            _camera.Pitch = GameConstants.CameraDefaultPitch;
            _camera.Distance = GameConstants.CameraDefaultDistance;
            _camera.Snap();
        }

        void LateUpdate()
        {
            if (_hud != null && _hud.Paused)
                return;
            if (_camera != null && _camera.Target != null)
                _camera.FollowTarget();
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape) && !_editor.Active)
                _hud.TogglePause();

            if (_hud.Paused)
            {
                HandlePauseKeys();
                return;
            }

            NestWorld.ApplyAtmosphere(_key, _fill, _director.Phase);
            _camera.TickInput();
            if (_cursorBound != _camera.Captured)
            {
                _hud.BindCursor(_camera.Captured);
                _cursorBound = _camera.Captured;
            }

            var local = _localAvatar.Motor;
            var look = _camera.PlanarForward;
            if (_editor.Tick(local.transform.position, look, _maps, _director))
            {
                local.ApplyMove(MoveDir(),
                    Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift),
                    Input.GetKeyDown(KeyCode.Space) || Input.GetButtonDown("Jump"),
                    Time.deltaTime);
                _banner = _editor.Status;
                _hud.Render(_director, _nest, _season, _cosmetics, _challenges, _boing, _account, _lan, _banner);
                if (_director.Queued.HasValue)
                    SetBotsActive(true);
                var prevEd = _director.Phase;
                _director.Tick(Time.deltaTime, _season, _challenges);
                _stages.Tick(Time.deltaTime, ActivePlayers(), _camera);
                if (prevEd != PartyPhase.Hub && _director.Phase == PartyPhase.Hub)
                    SetBotsActive(false);
                return;
            }

            local.ApplyMove(MoveDir(),
                Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift),
                Input.GetKeyDown(KeyCode.Space) || Input.GetButtonDown("Jump"),
                Time.deltaTime);

            if (_director.Phase == PartyPhase.Hub)
                HandleHub(local);

            HandleGlobalHotkeys();

            var previous = _director.Phase;
            _director.Tick(Time.deltaTime, _season, _challenges);
            if (previous != PartyPhase.Hub && _director.Phase == PartyPhase.Hub)
                SetBotsActive(false);

            var active = ActivePlayers();
            _stages.Tick(Time.deltaTime, active, _camera);
            if (_lan.Hosting)
            {
                _lan.ApplyRemotes(active);
                _lan.TickHost(Time.deltaTime, active, _director);
            }
            else if (_lan.Joining)
            {
                _lan.TickJoin(Time.deltaTime, local, _director);
                _lan.ApplyRemotes(active);
            }

            _hud.Render(_director, _nest, _season, _cosmetics, _challenges, _boing, _account, _lan, _banner);
        }

        Vector3 MoveDir()
        {
            var h = Input.GetAxisRaw("Horizontal");
            var v = Input.GetAxisRaw("Vertical");
            if (Mathf.Abs(h) < 0.01f && Mathf.Abs(v) < 0.01f)
            {
                if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) v = 1f;
                if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) v = -1f;
                if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) h = 1f;
                if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) h = -1f;
            }

            var dir = _camera.PlanarForward * v + _camera.PlanarRight * h;
            if (dir.sqrMagnitude > 1f)
                dir.Normalize();
            return dir;
        }

        void HandleHub(PlayerMotor local)
        {
            var pos = local.transform.position;
            _nest.RefreshPrompt(pos, _director, _cosmetics, _season, string.IsNullOrEmpty(_banner) ? null : _banner);
            var util = _nest.NearestUtility(pos, GameConstants.InteractRadius);
            var catalog = MapCatalog.ListAll();
            if (util != null && util.Action == NestAction.BrowseMaps)
            {
                if (Input.GetKeyDown(KeyCode.LeftBracket) || Input.GetKeyDown(KeyCode.RightBracket))
                {
                    if (catalog.Count > 0)
                    {
                        var delta = Input.GetKeyDown(KeyCode.RightBracket) ? 1 : -1;
                        _catalogIndex = (_catalogIndex + delta + catalog.Count) % catalog.Count;
                        _banner = $"My Maps · {catalog[_catalogIndex].Label}  (E play)";
                    }
                    else _banner = "No maps found — create one on Create Map";
                }
            }

            if (!(Input.GetKeyDown(KeyCode.E) || Input.GetKeyDown(KeyCode.Return)))
                return;

            if (util != null)
            {
                if (util.Action == NestAction.OpenEditor)
                {
                    _editor.Open();
                    _audio.Pad();
                    _banner = _editor.Status;
                    return;
                }

                if (catalog.Count == 0)
                {
                    _banner = "No maps found — create one on Create Map";
                    return;
                }

                _catalogIndex = Mathf.Clamp(_catalogIndex, 0, catalog.Count - 1);
                var entry = catalog[_catalogIndex];
                _maps.Apply(entry);
                _director.Queue(entry.Plan);
                SetBotsActive(true);
                _audio.Pad();
                _banner = "Starting " + entry.Label;
                return;
            }

            var pad = _nest.NearestPad(pos, GameConstants.InteractRadius);
            if (pad != null)
            {
                _maps.Clear();
                _director.Queue(pad.Plan);
                SetBotsActive(true);
                _audio.Pad();
            }
        }

        void HandleGlobalHotkeys()
        {
            if (Input.GetKeyDown(KeyCode.C))
            {
                _cosmetics.Cycle(_season);
                _localAvatar.ApplyTint(_cosmetics.Equipped.Color);
                _director.Announcer = "Skin " + _cosmetics.Equipped.label;
            }

            if (Input.GetKeyDown(KeyCode.N))
            {
                var crew = _roster.Cycle();
                _localAvatar.AttachCrewMesh(_studio, crew.Id);
                _director.Announcer = "Crew " + crew.Label;
            }

            if (Input.GetKeyDown(KeyCode.H) && !Input.GetKey(KeyCode.LeftControl))
            {
                var hat = _hats.CycleHat();
                if (hat != null)
                {
                    var existing = _localAvatar.transform.Find("Hat");
                    if (existing != null)
                        Object.Destroy(existing.gameObject);
                    _studio.QueueProp(hat, new Vector3(0f, 1.15f, 0f), Quaternion.identity, _localAvatar.transform,
                        "Hat", PrimitiveType.Sphere, new Vector3(0.22f, 0.22f, 0.22f), Color.white,
                        localSpace: true);
                    _director.Announcer = "Hat " + hat;
                }
            }

            if (Input.GetKeyDown(KeyCode.M))
                _banner = _boing.PrepareClaim(_season, _cosmetics.EquippedId);
            if (Input.GetKeyDown(KeyCode.O) && Input.GetKey(KeyCode.LeftControl))
                _banner = _boing.OpenCompanion();
            if (Input.GetKeyDown(KeyCode.V) && Input.GetKey(KeyCode.LeftControl))
                _banner = _boing.LinkFromEnv();
            if (Input.GetKeyDown(KeyCode.L) && Input.GetKey(KeyCode.LeftControl))
            {
                _account.OpenWebsite();
                _banner = _account.Note;
            }

            if (Input.GetKeyDown(KeyCode.Q) && _director.Phase != PartyPhase.Hub)
            {
                _director.ReturnToNest();
                SetBotsActive(false);
            }

            if (Input.GetKeyDown(KeyCode.R) && _director.Phase == PartyPhase.Results &&
                _director.Plan.Kind != PartyPlanKind.Idle)
            {
                _director.Queue(_director.Plan);
                SetBotsActive(true);
            }
        }

        void HandlePauseKeys()
        {
            if (Input.GetKeyDown(KeyCode.Q))
            {
                _director.ReturnToNest();
                SetBotsActive(false);
                _hud.TogglePause();
            }

            if (Input.GetKeyDown(KeyCode.H))
            {
                _lan.StartHost();
                _banner = _lan.Status;
            }

            if (Input.GetKeyDown(KeyCode.J))
            {
                _lan.StartJoin(_lan.JoinAddress);
                _banner = _lan.Status;
            }

            if (Input.GetKeyDown(KeyCode.A))
            {
                _account.OpenWebsite();
                _banner = _account.Note;
            }

            _hud.Render(_director, _nest, _season, _cosmetics, _challenges, _boing, _account, _lan, _banner);
        }

        List<PlayerMotor> ActivePlayers()
        {
            _active.Clear();
            for (int i = 0; i < _players.Count; i++)
            {
                var p = _players[i];
                if (p != null && p.gameObject.activeInHierarchy)
                    _active.Add(p);
            }

            return _active;
        }

        void SetBotsActive(bool active)
        {
            if (_lan.Joining)
                return;
            foreach (var p in _players)
                if (p.IsBot)
                    p.gameObject.SetActive(active);
        }
    }
}
