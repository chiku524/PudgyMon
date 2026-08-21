# Unity client — PudgyMon: Party Saga

The playable Nest + mini-game loop lives in this Unity 6 project. Cursor drives the editor through **MCP**.

## Requirements

- [Unity Hub](https://unity.com/download)
- **Unity 6.3 LTS** (`6000.3.22f1` or newer in the 6.3 line)
- Git (Package Manager pulls [MCP for Unity](https://github.com/CoplayDev/unity-mcp))
- Python 3.10+ with [`uv`](https://docs.astral.sh/uv/) (MCP for Unity's local server)

## Open and play

1. Unity Hub → **Open** → this `unity/` folder.
2. Install **Unity 6.3 LTS** if Hub prompts, then sign in (Personal license is enough).
3. Play `Assets/PudgyMon/Scenes/Nest.unity` (`GameBootstrap` auto-spawns).
4. **Window → MCP for Unity → Configure All Detected Clients**.

### Controls

WASD · Shift sprint · Space jump · mouse look · **E** / Enter on a glowing pad · **C** skins · **N** crew · **H** hat · **M** claim · **Ctrl+O** companion · **Q** Nest · **R** rematch · **Esc** pause · **`** free cursor

Pads: Race · Vibe Collect · Shooter · King of the Hill · Party Saga. Orange **Create Map** / purple **My Maps**.

Pause: **H** host LAN on 7777 · **J** join `127.0.0.1`. CLI: `--host --port 7777` / `--join --address <ip> --port 7777`.

Studio GLBs drop in at repo-root `assets/models/<id>/<id>.glb` and load at runtime via glTFast (greybox fallback).

## MCP (Cursor)

Repo-root `.cursor/mcp.json` points at MCP for Unity:

```json
{ "mcpServers": { "unityMCP": { "url": "http://localhost:8080/mcp" } } }
```

That URL is live only while the Unity Editor is open and MCP for Unity shows **Connected**.

Official Unity MCP (AI Assistant package) is optional: **Edit → Project Settings → AI → Unity MCP**.
