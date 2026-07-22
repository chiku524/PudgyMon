# Boing Network integration

**PudgyMon: Party Saga** uses **[Boing Network](https://boing.network/)** for NFT skins and soft currency.

Boing is a **native L1** (32-byte `AccountId`, Ed25519, Boing VM) — not MetaMask / ERC-721.

## Config

| Source | Purpose |
|--------|---------|
| `BOING_RPC_URL` | JSON-RPC endpoint (default `http://127.0.0.1:8545`, matching `contracts.json`) |
| `BOING_ACCOUNT` | Optional external AccountId — Nest menu → Wallet → Advanced link / Ctrl+V |
| `BOING_SECRET_HEX` | Treasury/deployer seed for Market mints (accounts API + deploy/mint scripts) |
| [`data/boing/contracts.json`](../data/boing/contracts.json) | Deployed NFT collection + fungible AccountIds + preferred RPC |

Chain id (testnet): **6913** / `0x1b01`.

**Who deploys contracts:** Boing Network provides the L1, RPC, faucet, and SDK templates. **PudgyMon (this repo) deploys** its own NFT collection + Saga Token fungible — the network does not create per-game contracts for you.

Current reference deploy in `contracts.json`: **Saga Token (SAGA)** + **PudgyMon Skins (PUDGY)** on a local block-producing node at `:8545` (e.g. VibeMiner validator).

## Wallet

**Registration creates a custodial Boing wallet** (Ed25519 AccountId `0x` + 64 hex) and stores it on the user profile (`boing_wallet`). The private key is encrypted at rest (`boing_wallet_secret_enc`) and returned **once** on signup (also exportable via `GET /v1/me/wallet/secret`).

In-game, that cloud wallet is auto-linked into `BoingConfig.linked_account` after sign-in. Desktop Bevy does **not** embed Boing Express / `window.boing`.

## Nest Market — on-chain Buy

Primary purchase path (custodial):

1. Sign in (intro or Nest menu → Account).
2. Earn season points in party modes (soft currency; host-trusted MVP).
3. Esc → **Market** → **Buy** on a skin.
4. Game calls `POST /v1/market/purchase` with JWT + points.
5. Accounts API allocates a unique `boing_token_id`, runs [`scripts/boing/mint_skin.mjs`](../scripts/boing/mint_skin.mjs) (treasury-signed lazy mint via `transfer_nft` to the player’s custodial AccountId), and stores ownership in `owned_skins`.
6. Game merges `owned_skins` into local unlocks and equips as usual.

Accounts env for minting (see [`services/accounts/.env.example`](../services/accounts/.env.example)):

```bash
BOING_RPC_URL=http://127.0.0.1:8545
BOING_SECRET_HEX=0x…64 hex   # same deployer as contracts.json
BOING_SDK_PATH=…/boing-sdk/dist/index.js
# optional: BOING_MINT_SCRIPT, NODE_BIN, PUDGYMON_CATALOG_PATH
```

Manual mint (operator):

```bash
node scripts/boing/mint_skin.mjs --to 0x…recipient --token-id 1001
```

### External wallet / Express fallback

If the player replaces their custodial wallet (`PATCH /v1/me` with an external AccountId), the server drops the custodial secret and Market Buy cannot mint for them. Use:

1. Earn season points → **M** builds a voucher (`%LOCALAPPDATA%/PudgyMon/logs/claim_voucher.json`).
2. Nest menu → Wallet → **Open Claim Desk** (or Ctrl+O).
3. Complete mint in **[Boing Express](https://boing.express)** against `contracts.json`.

## Deploy reference assets

Needs a **block-producing** RPC (faucet alone is not enough). Tip only advances when mempool txs are included — empty blocks are not produced. Each reference deploy charges ~200_000 native fee; a single faucet dispense is 50_000, so fund the deployer before running the script.

**Default:** point at a local validator on `:8545` (VibeMiner or `boing-node --validator --rpc-port 8545 --faucet-enable`).

```bash
# scripts/boing/.env
# BOING_RPC_URL=http://127.0.0.1:8545
# BOING_SECRET_HEX=0x…64 hex seed
# BOING_AUTO_FAUCET_REQUEST=1
node scripts/boing/deploy_reference_assets.mjs
```

Writes AccountIds into `data/boing/contracts.json`. The game loads `rpc_url` from that file (else `BOING_RPC_URL`, else `:8545`).

**Optional solo Docker** (host port **8546** → container 8545) if you do not want to use VibeMiner:

```bash
MSYS_NO_PATHCONV=1 docker run -d --name pudgymon-boing-solo -p 8546:8545 \
  -v "C:/Users/chiku/Desktop/vibe-code/boing.network/tools/bin/boing-node:/usr/local/bin/boing-node:ro" \
  -v "C:/Users/chiku/Projects/PudgyMon/scripts/boing/local-node-data:/data" \
  --entrypoint /usr/local/bin/boing-node debian:bookworm-slim \
  --data-dir=/data --rpc-port=8545 --validator --faucet-enable
```

Then set `BOING_RPC_URL=http://127.0.0.1:8546` for that deploy only.

## In-game keys

| Key | Action |
|-----|--------|
| Esc | Nest menu (Settings, Account, Market, Wallet, …) |
| Ctrl+V | Link external `BOING_ACCOUNT` |
| M | Write claim voucher for equipped skin |
| Ctrl+O | Open claim companion page |
| C | Cycle unlocked cosmetics |

## Security

- Season points are **host-trusted** offline/LAN for MVP; synced to accounts for Market gating.
- NFT mint is the on-chain purchase artifact; SAGA debit as payment is a follow-up.
- Do not mint from raw client scores without attestation later.
- NFTs/currency ≠ gambling; see archived wager docs.
