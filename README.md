# PudgyMon: Party Saga

Cute **Pudgy Monsters** party game — race, collect vibes, and toy-blaster FFA in **The Nest**, then earn season points and claim skins on **[Boing Network](https://boing.network/)**.

Built with **Bevy 0.19 (Rust)** · Third-person · LAN multiplayer · Boing-ready collectibles

## Elevator pitch

Drop into **The Nest**, show off your Pudgy skin, and pick a mini-game pad: **Race**, **Vibe Collect**, **Shooter**, **King of the Hill**, or the full **Party Saga** circuit. Solo bots fill empty seats; friends can host/join on LAN.

## Status

**Party + Nest hub (playable greybox)**

- [x] Social Nest (no main menu) with mode pads, themed districts + skin showcases
- [x] Race / Vibe / Shooter / King of the Hill + Party Saga loop
- [x] Season points + cosmetics unlocks
- [x] Boing RPC bridge + claim vouchers
- [ ] Art drop-in for Pudgy characters / Nest props

See [docs/PARTY_ROADMAP.md](docs/PARTY_ROADMAP.md) and [docs/BRAND.md](docs/BRAND.md).

## Requirements

- [Rust](https://rustup.rs/) (see `rust-toolchain.toml`)
- Windows PC (primary target; Linux/macOS for dev/CI)

## Quick start

```bash
git clone https://github.com/chiku524/PudgyMon.git
cd PudgyMon

cargo run                         # The Nest (offline)
cargo run -- host --port 7777
cargo run -- join --address 127.0.0.1 --port 7777
```

**Controls:** WASD · Shift sprint · mouse look · **E**/Enter on a pad to start · **C** skins · **M** Boing claim · **Q** Nest · **R** rematch · **Esc** pause

## Documentation

| Doc | Description |
|-----|-------------|
| [BRAND](docs/BRAND.md) | Locked names & tone |
| [MAP_CREATOR](docs/MAP_CREATOR.md) | Stage UGC — Race / Vibe / Shooter / Hill (create / save / play) |
| [PARTY_ROADMAP](docs/PARTY_ROADMAP.md) | Product loop + checklist |
| [BOING_INTEGRATION](docs/BOING_INTEGRATION.md) | Wallet, RPC, claims |
| [PACKAGING](docs/PACKAGING.md) | Playtester builds |
| [DROP_IN](docs/DROP_IN.md) | Art/audio drop paths |
| [TECH](docs/TECH.md) | Bevy architecture |
| [STEAM](docs/STEAM.md) | Store page draft |
| [archive/vault/](docs/archive/vault/) | Retired vault-tournament docs |

## License

All rights reserved (solo indie — license TBD before public release).
