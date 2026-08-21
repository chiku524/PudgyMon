# PudgyMon: Party Saga

Cute **Pudgy Monsters** party game — race, collect vibes, and toy-blaster FFA in **The Nest**, then earn season points and claim skins on **[Boing Network](https://boing.network/)**.

Built with **Unity 6.5** · Third-person · LAN · Boing-ready collectibles

## Elevator pitch

Drop into **The Nest**, show off your Pudgy skin, and pick a mini-game pad: **Race**, **Vibe Collect**, **Shooter**, **King of the Hill**, or the full **Party Saga** circuit. Solo bots fill empty seats; friends can host/join on LAN.

## Status

**Party + Nest hub (Unity client)**

- [x] Social Nest (no main menu) with mode pads, themed districts + skin showcases
- [x] Race / Vibe / Shooter / King of the Hill + Party Saga loop
- [x] Season points + cosmetics unlocks
- [x] Map creator + My Maps catalog
- [x] Boing claim companion + accounts website
- [x] LAN host/join
- [ ] Art drop-in polish for remaining Studio GLBs

See [docs/PARTY_ROADMAP.md](docs/PARTY_ROADMAP.md) and [docs/BRAND.md](docs/BRAND.md).

## Requirements

- [Unity Hub](https://unity.com/download) + **Unity 6.5** (`6000.5.9f1`; open the inner `unity/` folder, not the repo root)
- Windows PC (primary target)
- Rust only for the optional accounts API (`services/accounts`)

## Quick start

```bash
git clone https://github.com/chiku524/PudgyMon.git
cd PudgyMon
```

Unity Hub → **Add project from disk** → select the inner `unity/` folder (not the repo root). Open with **Unity 6.5.9f1**. Play `Assets/PudgyMon/Scenes/Nest.unity`.

Cursor MCP: [docs/UNITY.md](docs/UNITY.md).

**Controls:** WASD · Shift sprint · mouse look · **E**/Enter on a pad · **C** skins · **N** crew · **H** hat · **M** claim · **Q** Nest · **R** rematch · **Esc** pause

LAN: pause **H** to host, **J** to join `127.0.0.1`, or `--host` / `--join --address <ip> --port 7777`

## Documentation

| Doc | Description |
|-----|-------------|
| [BRAND](docs/BRAND.md) | Locked names & tone |
| [UNITY](docs/UNITY.md) | Unity 6 client + Cursor MCP |
| [MAP_CREATOR](docs/MAP_CREATOR.md) | Stage UGC — Race / Vibe / Shooter / Hill |
| [PARTY_ROADMAP](docs/PARTY_ROADMAP.md) | Product loop + checklist |
| [BOING_INTEGRATION](docs/BOING_INTEGRATION.md) | Wallet, RPC, claims |
| [PACKAGING](docs/PACKAGING.md) | Playtester builds |
| [DROP_IN](docs/DROP_IN.md) | Art/audio drop paths |
| [TECH](docs/TECH.md) | Unity architecture |
| [STEAM](docs/STEAM.md) | Store page draft |
| [archive/vault/](docs/archive/vault/) | Retired vault-tournament docs |

## License

All rights reserved (solo indie — license TBD before public release).
