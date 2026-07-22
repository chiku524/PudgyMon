# PudgyMon Accounts API

Email/password auth + profile for Nest / web.

## Quick start (Docker)

```bash
cd services/accounts
cp .env.example .env
# edit POSTGRES_PASSWORD and JWT_SECRET
docker compose up --build
```

- API: `http://127.0.0.1:8788`
- Health: `GET /health`
- Postgres (host): `127.0.0.1:5434`
- Public (free tunnel): `https://pudgymon-api.boing.network`

## Local cargo run

```bash
docker compose up -d db
export DATABASE_URL=postgres://pudgymon:$POSTGRES_PASSWORD@127.0.0.1:5434/pudgymon_accounts
export JWT_SECRET=your-secret
cargo run -p pudgymon-accounts
```

## Endpoints

| Method | Path | Body |
|--------|------|------|
| POST | `/v1/auth/signup` | `{ email, password, display_name }` |
| POST | `/v1/auth/login` | `{ email, password }` |
| GET | `/v1/me` | Bearer token → profile + `owned_skins` + `season_points` |
| POST | `/v1/me/season` | `{ points }` — sync soft season points |
| PATCH | `/v1/me` | `{ display_name?, boing_wallet? }` |
| GET | `/v1/me/wallet/secret` | Bearer — export custodial key |
| POST | `/v1/market/purchase` | `{ skin_id, points? }` — mint PUDGY NFT to custodial wallet |

Signup creates a custodial Boing AccountId, stores `boing_wallet` + encrypted secret, and returns:

`{ access_token, profile, boing_wallet_secret? }`

Set `WALLET_MASTER_KEY` in `.env` (falls back to `JWT_SECRET`).

### On-chain Market mint

Purchase runs [`scripts/boing/mint_skin.mjs`](../../scripts/boing/mint_skin.mjs) with the treasury `BOING_SECRET_HEX`. Prefer **local cargo run** of the API (Docker image has no Node/boing-sdk by default):

```bash
# scripts/boing/.env also works for the mint script
export BOING_RPC_URL=http://127.0.0.1:8545
export BOING_SECRET_HEX=0x…
export BOING_SDK_PATH=/path/to/boing-sdk/dist/index.js
cargo run -p pudgymon-accounts
```
