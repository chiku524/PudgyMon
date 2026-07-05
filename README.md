# ShipHappens

**6–8 player cartoon space freight co-op** with social deduction. Friends complete absurd jobs on a discount orbital station while one or two **Stowaways** smuggle contraband and sabotage the run.

Built with **Godot 4** · Third-person · Full cartoon physics · Steam-bound indie

## Elevator pitch

You and your friends are the worst freight crew in the galaxy. Load weird **space goods**, survive slapstick physics, and catch the Stowaway before ShipHappens Logistics fires you all.

## Status

**Phase 0 — Network prototype**

- [x] Project scaffold + documentation
- [ ] Third-person movement + orbit camera
- [ ] Host / join over LAN (ENet)
- [ ] Synced physics crate
- [ ] Main Hub greybox

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full solo-dev plan.

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

## Project structure

```
ShipHappens/
├── docs/           # Design & planning markdown
├── scenes/         # Godot scenes (.tscn)
│   ├── main/       # Main menu
│   ├── game/       # Game world orchestrator
│   ├── player/     # Player character
│   ├── props/      # Interactables (crates, etc.)
│   └── levels/     # Station maps
├── scripts/        # GDScript
│   ├── autoload/   # NetworkManager, GameState
│   ├── player/     # Movement, camera
│   ├── ui/         # Menus
│   ├── props/      # Prop logic
│   └── game/       # Session flow
└── project.godot
```

## License

All rights reserved (solo indie — license TBD before public release).
