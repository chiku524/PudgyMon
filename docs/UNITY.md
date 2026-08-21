# Unity migration

PudgyMon's **game client** is moving from Bevy 0.19 (Rust) to **Unity 6.3 LTS** so agents in Cursor can drive the editor through MCP.

## Why Unity

Unity has first-class Model Context Protocol support:

| Source | What it is |
|--------|------------|
| [Unity MCP](https://docs.unity3d.com/Packages/com.unity.ai.assistant@2.0/manual/unity-mcp-overview.html) (official) | Unity 6 + `com.unity.ai.assistant`. Editor bridge + `~/.unity/relay` binary. Cursor config uses `relay_win.exe --mcp`. |
| [MCP for Unity](https://github.com/CoplayDev/unity-mcp) (Coplay, MIT) | Package in `unity/Packages/manifest.json`. 47 editor tools (scenes, GameObjects, scripts, tests, builds). HTTP at `http://localhost:8080/mcp`. |

This repo uses **MCP for Unity** as the Cursor server because it configures itself from **Window → MCP for Unity** and does not require the preview AI Assistant package. Official Unity MCP remains an optional second server once AI Assistant is installed.

## Layout

```
unity/                         Unity 6 project (open this folder in Hub)
  Assets/PudgyMon/Scripts/     Nest, player, stages, HUD
  Packages/manifest.json       glTFast + MCP for Unity
src/                           Legacy Bevy client (still `cargo run`)
assets/models/                 Shared Studio GLBs (both engines)
data/                          Shared JSON catalogs
.cursor/mcp.json               Cursor → Unity MCP HTTP
```

## Open

Unity Hub → Open → `unity/`. Install **6000.3.22f1** (or current 6.3 LTS) when prompted. Play `Assets/PudgyMon/Scenes/Nest.unity`.

After the editor is running, enable MCP:

1. **Window → MCP for Unity → Configure All Detected Clients**
2. Confirm Cursor Settings → MCP shows `unityMCP` connected
3. Prompt: *Create a cube at the origin* — it should appear in the open scene
