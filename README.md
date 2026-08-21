# PudgyMon: Party Saga

Cute **Pudgy Monsters** party game — race, collect vibes, and toy-blaster FFA in **The Nest**, then earn season points and claim skins on **[Boing Network](https://boing.network/)**.

Built with **Unity 6** (Nest + mini-games, Cursor MCP) · Bevy 0.19 still in `src/` as the previous client · Third-person · Boing-ready collectibles

## Elevator pitch

Drop into **The Nest**, show off your Pudgy skin, and pick a mini-game pad: **Race**, **Vibe Collect**, **Shooter**, **King of the Hill**, or the full **Party Saga** circuit. Solo bots fill empty seats; friends can host/join on LAN.

## Status

**Party + Nest hub (playable greybox)**

- [x] Social Nest (no main menu) with mode pads, themed districts + skin showcases
- [x] Unity 6 Nest + four mini-games (see [UNITY.md](UNITY.md); LAN still Bevy-only)
- [x] Season points + cosmetics unlocks
- [x] Boing RPC bridge + claim vouchers
- [ ] Art drop-in for Pudgy characters / Nest props

See [docs/PARTY_ROADMAP.md](docs/PARTY_ROADMAP.md) and [docs/BRAND.md](docs/BRAND.md).

## Requirements

- [Unity Hub](https://unity.com/download) + **Unity 6.3 LTS** (open the `unity/` folder)
- Windows PC (primary target)
- [Rust](https://rustup.rs/) only if you still run the legacy Bevy client

## Quick start

```bash
git clone https://github.com/chiku524/PudgyMon.git
cd PudgyMon
```

**Unity (current client):** Unity Hub → Open → `unity/` → Play `Assets/PudgyMon/Scenes/Nest.unity`. MCP setup: [docs/UNITY.md](docs/UNITY.md).

**Bevy (legacy):** `cargo run` still boots The Nest from `src/`.

**Controls:** WASD · Shift sprint · mouse look · **E**/Enter on a pad to start · **C** skins · **Q** Nest · **R** rematch · **Esc** pause

## Documentation

| Doc | Description |
|-----|-------------|
| [BRAND](docs/BRAND.md) | Locked names & tone |
| [MAP_CREATOR](docs/MAP_CREATOR.md) | Stage UGC — Race / Vibe / Shooter / Hill (create / save / play) |
| [PARTY_ROADMAP](docs/PARTY_ROADMAP.md) | Product loop + checklist |
| [BOING_INTEGRATION](docs/BOING_INTEGRATION.md) | Wallet, RPC, claims |
| [PACKAGING](docs/PACKAGING.md) | Playtester builds |
| [DROP_IN](docs/DROP_IN.md) | Art/audio drop paths |
| [UNITY](docs/UNITY.md) | Unity 6 client + Cursor MCP |
| [TECH](docs/TECH.md) | Engine notes (Unity current, Bevy legacy) |
| [STEAM](docs/STEAM.md) | Store page draft |
| [archive/vault/](docs/archive/vault/) | Retired vault-tournament docs |

## License

All rights reserved (solo indie — license TBD before public release).
