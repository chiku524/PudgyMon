# PudgyMon — Technical Design

## Stack

| Layer | Choice |
|-------|--------|
| Engine | **Unity 6.5** + URP (`unity/`) |
| Language | C# (game) · Rust (accounts API only) |
| MCP | [MCP for Unity](https://github.com/CoplayDev/unity-mcp) + optional official Unity MCP |
| Networking | UDP listen-server (`LanSession`, port 7777) |
| Version control | Git + GitHub |
| Assets | Blender + Immersive Studio / Tripo + kitbash (GLB via glTFast at runtime) |
| Target | Windows PC, Steam |

## Why Unity

- MCP so Cursor can create scenes, edit objects, run tests, and inspect the editor
- Mature animation, lighting, and GLB import for the Studio drop-in pipeline
- Steam / Windows packaging path

## Architecture

```
unity/Assets/PudgyMon
 ├── GameBootstrap     — Nest boot, input, pause, LAN CLI
 ├── NestHub           — mode pads + Create Map / My Maps
 ├── PartyDirector     — hub → stages → results
 ├── StageRuntime      — Race, Vibe, Shooter, King of the Hill
 ├── MapCatalog/Editor — JSON maps under data/maps + %LOCALAPPDATA%/PudgyMon/maps
 ├── PlayerMotor       — WASD, sprint, jump / double-jump, island clamp
 ├── StudioAssets      — runtime GLB load from repo assets/models
 ├── BoingBridge       — claim voucher + companion HTML
 ├── AccountSession    — cloud JWT from web signup
 └── LanSession        — host/join snapshots
```

Accounts API remains `services/accounts` (Axum + Postgres). Marketing site is `web/`. Claim/map companions are `companion/`.

## Data files

| File | Purpose |
|------|---------|
| `assets/studio_registry.json` | Immersive Studio asset IDs → GLB paths |
| `data/maps/*.json` | Official Race / Vibe / Shooter / Hill / Party Saga packs |
| `data/cosmetics/catalog.json` | Season skins |
| `data/characters/roster.json` | Playable crew |
| `data/challenges/weekly.json` | Party-pass challenges |
| `data/boing/contracts.json` | RPC + collection addresses |

GLBs load from `assets/models/{asset_id}/{asset_id}.glb`.

## CI

`.github/workflows/ci.yml` builds the accounts API Docker image. The game client is Unity (no `cargo` game crate).

## Migration notes

- **Engine:** Godot 4.7 → Bevy 0.19 → **Unity 6.5** (Bevy client removed).
- **Design:** Crew vs Stowaway → Vault Break (archived) → **PudgyMon: Party Saga**. Vault docs: [archive/vault/](archive/vault/).
