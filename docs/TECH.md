# ShipHappens — Technical Design

## Stack

| Layer | Choice |
|-------|--------|
| Engine | Godot 4.3+ |
| Language | GDScript |
| Networking | Godot 4 Multiplayer API + ENet |
| Voice (later) | Steam Voice via GodotSteam |
| Version control | Git + GitHub |
| Assets | Blender + kitbash kits + custom hats |
| Target | Windows PC, Steam |

## Why Godot

- Free, lightweight, fast iteration for solo dev
- Jolt physics (Godot 4) for cartoon ragdoll comedy
- ENet built-in for Phase 0 LAN
- GodotSteam plugin path for Steam release

## Architecture

```
Host (authoritative server)
 ├── GameState        — jobs, satisfaction, roles, round phase
 ├── NetworkManager   — ENet peer, connect/disconnect
 ├── PlayerManager    — spawn/despawn, ownership
 ├── JobSystem        — server validates job progress
 └── MeetingManager   — vote tally server-side

Client
 ├── Input + movement prediction (local player only)
 ├── Interact requests → server RPC
 └── UI (role card, job board, vote, stats)
```

## Networking rules (solo scope)

**Server validates:**
- Job progress
- Votes / Write-Ups
- Smuggle deposits
- Round state transitions

**Do NOT sync every frame:**
- Full ragdoll limb physics
- All prop micro-collisions

Sync: player transform, carry state, crate position (periodic or on impulse).

## Scene layout

```
scenes/
  main/main_menu.tscn      — Host / Join UI
  game/game_world.tscn     — Spawns level + players
  player/player.tscn       — CharacterBody3D + camera rig
  props/crate.tscn         — RigidBody3D test prop
  levels/hub_greybox.tscn  — Phase 0 test map
```

## Autoloads

| Name | Script | Role |
|------|--------|------|
| `NetworkManager` | `scripts/autoload/network_manager.gd` | ENet host/join |
| `GameState` | `scripts/autoload/game_state.gd` | Session + round data |

## Input actions

| Action | Default |
|--------|---------|
| `move_forward` | W |
| `move_back` | S |
| `move_left` | A |
| `move_right` | D |
| `jump` | Space |
| `interact` | E |
| `camera_left` | Q (orbit) |
| `camera_right` | E (orbit — rebind later) |

## Phase 0 test checklist

1. Run main menu → Host on port 7777
2. Second instance → Join with `127.0.0.1` or LAN IP
3. Both players spawn in hub
4. Push crate — both see it move
5. Disconnect cleanly

## Future integrations

- **GodotSteam** — lobbies, invites, achievements
- **Nakama or dedicated server** — only if sales justify ops cost
- **Data-driven jobs** — `docs/data/job_manifest.json` (Phase 2)
