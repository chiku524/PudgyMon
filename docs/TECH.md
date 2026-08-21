# PudgyMon — Technical Design

## Stack

| Layer | Choice |
|-------|--------|
| Engine | **Unity 6.3 LTS** (`unity/`) — current client |
| Language | C# (Unity) · Rust still used for accounts API |
| MCP | [MCP for Unity](https://github.com/CoplayDev/unity-mcp) + optional official Unity MCP |
| Networking | Unity Netcode — not ported yet; Bevy LAN remains in `src/` |
| Voice (later) | Steam Voice |
| Version control | Git + GitHub |
| Assets | Blender + Immersive Studio / Tripo + kitbash (GLB via glTFast) |
| Target | Windows PC, Steam |

## Why Unity

- Official and community **MCP** so Cursor can create scenes, edit objects, run tests, and inspect the editor
- Mature animation, lighting, and GLB import for the Studio drop-in pipeline
- Steam / Windows packaging path

Bevy 0.19 (`src/`, `cargo run`) is the previous client. Do not extend it unless you are fixing a playtest blocker that Unity has not reached yet. See [UNITY.md](UNITY.md).

## Architecture (Unity client)

```
unity/Assets/PudgyMon
 ├── GameBootstrap     — boots Nest, HUD, player, bots, MCP-ready scene
 ├── NestHub           — mode pads (Race / Vibe / Shooter / Hill / Party Saga)
 ├── PartyDirector     — phase machine (hub → stages → results)
 ├── StageRuntime      — greybox Race, Vibe, Shooter, King of the Hill
 ├── PlayerMotor       — WASD, sprint, jump / double-jump, island clamp
 ├── StudioAssets      — runtime GLB load from repo assets/models
 └── GameHud           — phase, announcer, season points, skins
```

LAN / replicon still lives in the Bevy tree (`src/network`, `src/party`). Unity Netcode is the next port.

## Architecture (legacy Bevy prototype)

```
Host (authoritative server)
 ├── JobSystem        — legacy greybox job validation (to be replaced)
 ├── NetworkPlugin    — renet transport, player spawn on connect
 ├── InteractionPlugin — InteractRequest client → server RPC
 └── SmokeAutomation  — headless CI checks

Client
 ├── LocalPlayer      — assigned on connect (online) or at spawn (offline)
 ├── MoveInput        — camera-relative WASD sent to server when online
 ├── ThirdPersonCamera — mouse orbit, scroll zoom
 └── UiPlugin         — minimal debug HUD
```

## Planned tournament architecture (Phase 1)

See [GDD.md](GDD.md), [TOURNAMENT.md](TOURNAMENT.md), [SCORING.md](SCORING.md).

```
Dedicated server / listen host
 ├── TournamentDirector  — lobby → rooms → elimination → finale → podium
 ├── RoomRuntime         — per-stage objectives, timers, scaling by slot size
 ├── ScoringService      — server-side CI + composite (all raw events logged)
 ├── SlotRegistry        — solo / duo / trio / squad slots
 └── WagerLedger         — practice currency now; real wallet gated (Phase 4)

Replicated state
 ├── TournamentPhase, RoomId, TimeRemaining
 ├── SlotCompositeScores, PlayerCI
 ├── StrikeCount (team modes)
 └── EliminationOrder
```

**Server validates:** all objective progress, scoring, elimination, buy-in lock.
**Clients send:** movement + interaction intent only.

## Networking rules

**Server validates:**
- Job progress (`JobSystem::handle_interact`)
- Player movement (`apply_move_input` from `MoveInput` events)

**Replicated:**
- `JobBoard`, `NetworkPlayer`, `PlayerName`, `PlayerColor`
- `SmokeJobFlags` (CI smoke test helper)

**Client sends:**
- `MoveInput { direction, sprint }` each frame when moving
- `InteractRequest { station: Entity }` on F press

Default port: **7777**

## Data files

| File | Purpose |
|------|---------|
| `data/job_manifest.json` | All 10 job definitions (id, zone, target, satisfaction) |
| `assets/studio_registry.json` | Immersive Studio asset IDs → GLB paths |

GLBs load from `assets/models/{asset_id}/{asset_id}.glb` via Bevy `AssetServer`.

## Binaries

| Binary | Purpose |
|--------|---------|
| `pudgymon` | Interactive game (`cargo run` / `host` / `join`) |
| `pudgymon_smoke` | Headless LAN smoke test for CI |

## CI

`.github/workflows/multiplayer-smoke.yml` runs `cargo test` and `scripts/run_mp_smoke_test.sh`.

## Migration notes

- **Engine:** Godot 4.7 → Bevy 0.19 (2026) → **Unity 6.3** (current client in `unity/`).
- **Design:** Pivoted from Crew vs Stowaway co-op to **Vault Break**, then to **PudgyMon: Party Saga**. Vault docs: [archive/vault/](archive/vault/).
