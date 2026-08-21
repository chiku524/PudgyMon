# Unity migration

PudgyMon's **game client** is Unity 6.5. Cursor talks to the running editor through MCP.

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

**Unity 6.5.9f1 is the editor this repo targets** (`ProjectSettings/ProjectVersion.txt`). Hub shows “missing Unity version” when that file points at an editor you do not have installed.

1. Unity Hub → **Projects** → **Add** → **Add project from disk**
2. Select **`C:\Users\chiku\Projects\PudgyMon\unity`** — the inner `unity` folder, not the PudgyMon repo root and not `Assets`.
3. Open it with **Unity 6.5.9f1**. First import takes a few minutes (URP + MCP for Unity + glTFast). The Built-in Render Pipeline warning should be gone — the project uses URP.
4. Play `Assets/PudgyMon/Scenes/Nest.unity`.

If Hub still greys out the folder, open the editor directly:

```bat
"C:\Program Files\Unity\Hub\Editor\6000.5.9f1\Editor\Unity.exe" -projectPath "C:\Users\chiku\Projects\PudgyMon\unity"
```

1. **Window → MCP for Unity → Configure All Detected Clients**
2. Cursor Settings → MCP shows `unityMCP` connected
3. Prompt: *Create a cube at the origin*
