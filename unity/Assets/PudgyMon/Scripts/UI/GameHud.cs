using UnityEngine;
using UnityEngine.UI;

namespace PudgyMon
{
    public sealed class GameHud : MonoBehaviour
    {
        Text _title;
        Text _main;
        Text _sub;
        Text _hint;
        GameObject _pause;

        public bool Paused { get; private set; }

        public static GameHud Create()
        {
            var canvasGo = new GameObject("HUD");
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGo.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasGo.AddComponent<GraphicRaycaster>();

            var hud = canvasGo.AddComponent<GameHud>();
            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf")
                       ?? Font.CreateDynamicFontFromOSFont("Segoe UI", 16)
                       ?? Font.CreateDynamicFontFromOSFont("Arial", 16);

            hud._title = MakeText(canvasGo.transform, "Title", new Vector2(20, -18), 22,
                new Color(1f, 0.55f, 0.35f), font, "PUDGYMON · THE NEST");
            hud._main = MakeText(canvasGo.transform, "Main", new Vector2(20, -48), 24,
                new Color(0.95f, 0.95f, 0.9f), font, "");
            hud._sub = MakeText(canvasGo.transform, "Sub", new Vector2(20, -120), 16,
                new Color(0.7f, 0.85f, 0.95f), font, "");
            hud._hint = MakeText(canvasGo.transform, "Hint", new Vector2(20, -200), 13,
                new Color(0.55f, 0.6f, 0.7f), font,
                "WASD · Shift sprint · Space jump · pads E · Create Map · My Maps · C skin · N crew · H hat · M claim · Ctrl+O companion · Q Nest · R rematch · Esc pause · ` cursor");

            var hintRect = hud._hint.rectTransform;
            hintRect.anchorMin = new Vector2(0f, 0f);
            hintRect.anchorMax = new Vector2(1f, 0f);
            hintRect.pivot = new Vector2(0f, 0f);
            hintRect.anchoredPosition = new Vector2(20f, 18f);

            hud._pause = new GameObject("Pause");
            hud._pause.transform.SetParent(canvasGo.transform, false);
            var pauseImg = hud._pause.AddComponent<Image>();
            pauseImg.color = new Color(0.05f, 0.07f, 0.1f, 0.72f);
            var pauseRect = hud._pause.GetComponent<RectTransform>();
            pauseRect.anchorMin = Vector2.zero;
            pauseRect.anchorMax = Vector2.one;
            pauseRect.offsetMin = Vector2.zero;
            pauseRect.offsetMax = Vector2.zero;
            MakeText(hud._pause.transform, "PauseLabel", new Vector2(40, -80), 28,
                Color.white, font,
                "Paused\nEsc resume · Q Nest\nH host LAN · J join 127.0.0.1\nA accounts website · Ctrl+O claim companion");
            hud._pause.SetActive(false);
            return hud;
        }

        static Text MakeText(Transform parent, string name, Vector2 anchored, int size, Color color, Font font,
            string value)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var rect = go.AddComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(1f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = anchored;
            rect.sizeDelta = new Vector2(-40f, 80f);
            var text = go.AddComponent<Text>();
            text.font = font;
            text.fontSize = size;
            text.color = color;
            text.alignment = TextAnchor.UpperLeft;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            text.text = value;
            return text;
        }

        public bool TogglePause()
        {
            Paused = !Paused;
            _pause.SetActive(Paused);
            Cursor.lockState = Paused ? CursorLockMode.None : CursorLockMode.Locked;
            Cursor.visible = Paused;
            return Paused;
        }

        public void BindCursor(bool captured)
        {
            if (Paused)
                return;
            Cursor.lockState = captured ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !captured;
        }

        public void Render(PartyDirector director, NestHub nest, SeasonLedger season, CosmeticsCatalog cosmetics,
            ChallengeBoard challenges = null, BoingBridge boing = null, AccountSession account = null,
            LanSession lan = null, string banner = null)
        {
            var phaseLabel = director.Phase switch
            {
                PartyPhase.Hub => "THE NEST",
                PartyPhase.Race => "RACE",
                PartyPhase.Vibe => "VIBE COLLECT",
                PartyPhase.Shooter => "SHOOTER",
                PartyPhase.Koth => "KING OF THE HILL",
                PartyPhase.Intermission => "INTERMISSION",
                PartyPhase.Results => "RESULTS",
                _ => director.Phase.ToString()
            };
            var timerBit = director.Phase == PartyPhase.Hub || director.PhaseTimer >= 9000f
                ? ""
                : $"  ·  {director.PhaseTimer:0}s";
            var prompt = director.Phase == PartyPhase.Hub && nest != null && !string.IsNullOrEmpty(nest.Prompt)
                ? nest.Prompt
                : director.Announcer;
            _main.text = $"{phaseLabel}{timerBit}\n{prompt}";
            var wallet = string.IsNullOrEmpty(boing?.LinkedAccount)
                ? "unlinked"
                : boing.LinkedAccount.Substring(0, Mathf.Min(10, boing.LinkedAccount.Length));
            var acc = account != null && account.SignedIn ? account.DisplayName : "guest";
            var net = lan == null || lan.Status == "Offline" ? "solo" : lan.Status;
            _sub.text =
                $"Party pts {director.MatchPoints[0]} · Season {season.points} · Skin {cosmetics.EquippedId} · {acc} · {net} · {wallet}\n" +
                (challenges != null ? challenges.SummaryLine() : "") + "\n" +
                (banner ?? boing?.Note ?? "");
        }
    }
}
