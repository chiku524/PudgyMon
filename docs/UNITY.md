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

**Unity 6.5 is fine.** This folder was authored against 6.3 LTS; Hub will offer to upgrade it when you open with 6.5. Accept that.

Hub only treats a folder as a Unity project if it contains **both**:

- `Assets/`
- `ProjectSettings/ProjectSettings.asset`

1. Unity Hub → **Projects** → **Add** → **Add project from disk**
2. Select **`C:\Users\chiku\Projects\PudgyMon\unity`** — the inner `unity` folder, not the PudgyMon repo root and not `Assets`.
3. Open it with the installed **Unity 6.5** editor. First import takes a few minutes (MCP for Unity + glTFast download over Git).
4. Play `Assets/PudgyMon/Scenes/Nest.unity`.

If Hub still greys out the folder, open the editor directly:

```bat
"%USERPROFILE%\Unity\Hub\Editor\<6.5-version>\Editor\Unity.exe" -projectPath "C:\Users\chiku\Projects\PudgyMon\unity"
```

Replace `<6.5-version>` with the folder Hub lists under Installs (for example `6000.5.x`).

1. **Window → MCP for Unity → Configure All Detected Clients**
2. Cursor Settings → MCP shows `unityMCP` connected
3. Prompt: *Create a cube at the origin*
