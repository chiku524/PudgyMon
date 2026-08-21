# Unity migration

PudgyMon's **game client** is Unity 6.3 LTS. Cursor talks to the running editor through MCP.

## MCP

| Source | What it is |
|--------|------------|
| [Unity MCP](https://docs.unity3d.com/Packages/com.unity.ai.assistant@2.0/manual/unity-mcp-overview.html) (official) | Unity 6 + `com.unity.ai.assistant`. Relay: `%USERPROFILE%\.unity\relay\relay_win.exe --mcp`. |
| [MCP for Unity](https://github.com/CoplayDev/unity-mcp) (Coplay, MIT) | Wired in `unity/Packages/manifest.json`. HTTP at `http://localhost:8080/mcp`. |

This repo uses **MCP for Unity** as the Cursor server.

## Layout

```
unity/                         Unity 6 project (open this folder in Hub)
  Assets/PudgyMon/Scripts/     Nest, player, stages, maps, LAN, HUD
  Packages/manifest.json       glTFast + MCP for Unity
assets/models/                 Studio GLBs
data/                          JSON catalogs + official maps
services/accounts/             Cloud accounts API (Rust)
web/                           Marketing + login
companion/                     Claim + map share desks
.cursor/mcp.json               Cursor → Unity MCP HTTP
```

## Open

Unity Hub → Open → `unity/`. Install **6000.3.22f1** (or current 6.3 LTS) when prompted. Play `Assets/PudgyMon/Scenes/Nest.unity`.

1. **Window → MCP for Unity → Configure All Detected Clients**
2. Cursor Settings → MCP shows `unityMCP` connected
3. Prompt: *Create a cube at the origin*
