# Unity client — PudgyMon: Party Saga

The playable Nest + mini-game loop now lives in this Unity 6 project so Cursor can drive the editor through **MCP**.

Bevy (`src/`, `cargo run`) remains in the repo as the previous engine. New client work happens here.

## Requirements

- [Unity Hub](https://unity.com/download) (already installable via `winget install Unity.UnityHub`)
- **Unity 6.3 LTS** (`6000.3.22f1` or newer in the 6.3 line)
- Git (Package Manager pulls [MCP for Unity](https://github.com/CoplayDev/unity-mcp))
- Python 3.10+ with [`uv`](https://docs.astral.sh/uv/) (MCP for Unity's local server)

## Open and play

1. Unity Hub → **Open** → select this `unity/` folder.
2. Install **Unity 6.3 LTS** if Hub prompts for it, then sign in (Personal license is enough).
3. Open scene `Assets/PudgyMon/Scenes/Nest.unity` (or press Play — `GameBootstrap` auto-spawns).
4. **Window → MCP for Unity → Configure All Detected Clients** so Cursor can talk to the running editor.

### Controls

WASD · Shift sprint · Space jump · mouse look · **E** / Enter on a glowing pad · **C** skins · **Q** Nest · **R** rematch · **Esc** pause · **`** free cursor

Pads: Race · Vibe Collect · Shooter · King of the Hill · Party Saga (all four).

Studio GLBs still drop in at repo-root `assets/models/<id>/<id>.glb`. The Unity client loads them at runtime via glTFast and falls back to greybox primitives.

## MCP (Cursor)

Repo-root `.cursor/mcp.json` points Cursor at MCP for Unity's HTTP server:

```json
{ "mcpServers": { "unityMCP": { "url": "http://localhost:8080/mcp" } } }
```

That URL is live only while the Unity Editor is open and MCP for Unity shows **Connected**.

Unity also ships an official MCP bridge in the AI Assistant package (`com.unity.ai.assistant`) under **Edit → Project Settings → AI → Unity MCP**. Use that later if you prefer Unity's own relay (`%USERPROFILE%\.unity\relay\relay_win.exe --mcp`). Coplay's MCP for Unity is wired in `Packages/manifest.json` because it is the Cursor-ready path today.

## Not yet ported

- LAN host/join (Bevy replicon)
- Map creator / companion share desk
- Boing claim flow and account website (those stay as `companion/` + `web/` + `services/accounts`)
- Animation clip playback on crew GLBs

See [docs/TECH.md](../docs/TECH.md) and [docs/UNITY.md](../docs/UNITY.md).
