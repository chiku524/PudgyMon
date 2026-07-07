# ShipHappens

**6–8 player cartoon space freight co-op** with social deduction. Friends complete absurd jobs on a discount orbital station while one or two **Stowaways** smuggle contraband and sabotage the run.

Built with **Godot 4** · Third-person · Full cartoon physics · Steam-bound indie

## Elevator pitch

You and your friends are the worst freight crew in the galaxy. Load weird **space goods**, survive slapstick physics, and catch the Stowaway before ShipHappens Logistics fires you all.

## Status

**Phase 3 — Vertical slice (Steam playtest ready)**

- [x] MegaBargain Orbit #12 map with all zones
- [x] All 10 jobs (complete 7 to launch shuttle)
- [x] 5 smuggle item types + 5 sabotages (keys 1–5)
- [x] PA announcer + post-round stats
- [x] 7 jobs required · 3 smuggle quota · 20-min rounds

See [docs/ROADMAP.md](docs/ROADMAP.md) for Phase 4 polish plan.

## How to play a full round

1. **Host** with 2–8 players.
2. Complete **7 of 10 jobs** across the station.
3. **Stowaway:** smuggle **3 contraband** items to the Janitor Vent; press **1–5** for sabotage.
4. **Crew:** call meetings, Write Up suspects, reach the **Shuttle Bay** when it opens.

## Controls

| Key | Action |
|-----|--------|
| WASD | Move (relative to camera) |
| Mouse | Look around |
| Shift | Sprint |
| Space | Jump |
| F | Interact / drop item |
| Tab | Collapse / expand job board |
| Esc | Release / capture mouse |
| 1–5 | Stowaway sabotages |
| Scroll | Zoom camera |

## Requirements

- [Godot 4.3+](https://godotengine.org/download)
- Windows PC (primary target)

## Quick start

1. Clone the repo:
   ```bash
   git clone https://github.com/chiku524/ShipHappens.git
   cd ShipHappens
   ```
2. Open the project folder in **Godot 4.3+** (`project.godot`).
3. Press **F5** to run the main menu.
4. **Host** on one machine, **Join** from another on the same network (default port `7777`).

## Documentation

| Doc | Description |
|-----|-------------|
| [GDD](docs/GDD.md) | Full game design document |
| [ROADMAP](docs/ROADMAP.md) | Solo dev milestones |
| [TECH](docs/TECH.md) | Engine, networking, architecture |
| [CHARACTERS](docs/CHARACTERS.md) | Eight default crew roster |
| [JOBS](docs/JOBS.md) | All 10 station jobs |
| [STOWAWAY](docs/STOWAWAY.md) | Smuggle routes and sabotage |
| [STEAM](docs/STEAM.md) | Store page draft and tags |
| [STUDIO_ASSETS](docs/STUDIO_ASSETS.md) | Immersive Studio → Tripo → Godot import workflow |

## Immersive Studio assets (Tripo → Godot)

3D props and environment pieces are generated with **Immersive Labs Studio** (Tripo mesh + PBR) and imported via:

```bash
python scripts/import_immersive_studio_pack.py path/to/pack.zip
```

See [docs/STUDIO_ASSETS.md](docs/STUDIO_ASSETS.md) for the full workflow, registry format, and worker settings.

## Project structure

```
ShipHappens/
├── assets/         # Studio GLBs, textures, studio_registry.json
├── docs/           # Design & planning markdown
├── scenes/         # Godot scenes (.tscn)
│   ├── main/       # Main menu
│   ├── game/       # Game world orchestrator
│   ├── player/     # Player character
│   ├── props/      # Interactables (crates, etc.)
│   └── levels/     # Station maps
├── scripts/        # GDScript
│   ├── autoload/   # NetworkManager, GameState, ImmersiveStudioAssets
│   ├── assets/     # Immersive Studio registry loader
│   ├── levels/     # Station visuals, objective markers
│   ├── player/     # Movement, camera
│   ├── ui/         # Menus
│   ├── props/      # Prop logic
│   └── game/       # Session flow
├── third_party/    # immersive_studio Godot helpers (from immersive.labs)
└── project.godot
```

## License

All rights reserved (solo indie — license TBD before public release).
