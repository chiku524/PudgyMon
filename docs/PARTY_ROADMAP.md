# Party Product Roadmap — PudgyMon: Party Saga

**PudgyMon: Party Saga** is a **Pudgy Monsters** mini-game loop: Race → Vibe Collect → Shooter, season points, and Boing Network NFT/currency rewards.

Brand lock: [BRAND.md](BRAND.md). Vault tournament docs live under `docs/archive/vault/`.

Related: [BOING_INTEGRATION.md](BOING_INTEGRATION.md) · [PACKAGING.md](PACKAGING.md) · [DROP_IN.md](DROP_IN.md)

## Loop

1. **The Nest** (no main menu) — walk, show Pudgy skins, link wallet
2. Stand on a mode pad → **E** / Enter: Race, Vibe, Shooter, or full **Party Saga**
3. Play stage(s) → Results → season points → back to Nest
4. Claim cosmetics / currency on Boing (testnet)
5. LAN: `pudgymon host` / `join` CLI

## Checklist

### Core loop
- [x] Nest hub + stage state machine
- [x] Race / Vibe / Shooter greybox
- [x] Party Saga full circuit
- [x] Season points + cosmetics
- [x] Boing RPC bridge + claim docs
- [x] Weekly challenges JSON
- [x] Spectate after race finish
- [x] PudgyMon brand pass

### Next
- [x] Procedural Pudgy stub + `char_pudgy_base_01` drop path
- [x] Nest props greybox (egg, benches, vibe mushrooms)
- [x] Companion claim page (`companion/claim`, Ctrl+O)
- [x] Race map creator (Nest Create Map / My Maps) — see [MAP_CREATOR.md](MAP_CREATOR.md)
- [x] Vibe / Shooter map kits + Party Saga pack save/play/share — [MAP_CREATOR.md](MAP_CREATOR.md)
- [x] Companion map share desk (`companion/maps`)
- [ ] Drop real Pudgy / Nest GLBs via Studio (Party Saga prompts + accessory slots — see STUDIO_PROMPTS.md)
- [ ] Live GLB meshes for map deco `asset_id` in stage boot
- [ ] Host-attested anti-cheat for claims
- [x] LAN Nest + stage co-op (director sync, pad RPC, stage boot, shoot RPC) — soak 2–8 still open
- [x] Online accounts API + marketing site (`web/`, Nest Account page) — see [ACCOUNTS.md](ACCOUNTS.md)
- [ ] Real LAN soak 2–8 players
