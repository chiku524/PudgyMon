# PudgyMon accounts + website

Online email/password accounts for Nest identity, plus a small marketing site.

## Pieces

| Path | Role |
|------|------|
| [`web/`](../web/) | Landing, Learn, Signup, Login, Account |
| [`services/accounts/`](../services/accounts/) | Axum + Postgres API (host `:8788`) |
| Game intro (Title) | Sign In / Register → JWT → Nest |
| Nest menu → **Account** | Sign in / register, open site, link token, refresh, sign out |
| Nest menu → **Market** | Buy → on-chain PUDGY mint to custodial wallet |

## Run the API (local, free)

```bash
cd services/accounts
cp .env.example .env   # then set strong POSTGRES_PASSWORD + JWT_SECRET
docker compose up --build
```

- Health: `http://127.0.0.1:8788/health`
- Postgres (host): `127.0.0.1:5434`
- Containers: `accounts-db-1` + `accounts-api-1`

`.env` is gitignored. Never commit real secrets.

## Free public API URL (no Fly/Railway)

**Yes — free via Cloudflare Tunnel** (you already use this for Boing).

| Piece | Cost |
|-------|------|
| Cloudflare named tunnel + DNS on `boing.network` | Free |
| Hostname | `https://pudgymon-api.boing.network` |
| Origin | Your PC running Docker Compose on `:8788` |

Keep the tunnel up:

```powershell
pwsh scripts/run_accounts_tunnel.ps1
```

Caveat: your machine must be online. That is still $0.

### Always-on without your PC (still free / freemium)

If you need 24/7 without a home PC later:

1. **Oracle Cloud Always Free** VM — run the same Docker Compose there, point the tunnel (or open a port)
2. **Neon** free Postgres + free-tier container host (Render/Fly free allowances) — API may sleep on free tiers
3. Paid hosts (Railway/Fly) — not required for this setup

## Website

Production: [https://pudgymon.vercel.app](https://pudgymon.vercel.app)  
Vercel Hobby is free. Root directory: `web/`.  
Hosted pages call `https://pudgymon-api.boing.network` via [`web/js/config.js`](../web/js/config.js).

Optional custom domain (free): `pudgymon.boing.network` is already added on Vercel.  
In Cloudflare DNS for `boing.network`, create:

`A` `pudgymon` → `76.76.21.21` (proxied or DNS-only both work; Vercel recommends the A record)

Until that record exists, use [https://pudgymon.vercel.app](https://pudgymon.vercel.app).

Local preview: open [`web/index.html`](../web/index.html).

Optional query override: `?api=http://127.0.0.1:8788`

## Play (in-game intro)

1. Start accounts API (+ tunnel if you want the hosted site to work)
2. `cargo run` / `pudgymon`
3. **Register** or **Sign In** on the intro
4. JWT persisted at `%LOCALAPPDATA%\PudgyMon\account_session.json`

Controls: **Sign In** / **Register** · `F1`/`F2` · `Tab` · type · `Enter` / **Continue**

Game env:

- `PUDGYMON_ACCOUNTS_URL` — default `http://127.0.0.1:8788` (game talks to local API; use the public URL if you want)
- `PUDGYMON_ACCOUNT_TOKEN` — inject JWT
- `PUDGYMON_WEB_URL` — Nest “Open website”
- `PUDGYMON_SKIP_AUTH=1` — skip intro (smoke / tooling); Host/Join CLI also skip

## API sketch

- `POST /v1/auth/signup` `{ email, password, display_name }` → creates + links a Boing wallet; response may include `boing_wallet_secret` (once)
- `POST /v1/auth/login` `{ email, password }` → backfills a wallet if the account is missing one
- `GET /v1/me` Bearer → profile + `owned_skins` + `season_points`
- `POST /v1/me/season` `{ points }` → sync soft season points for Market gating
- `PATCH /v1/me` `{ display_name?, boing_wallet? }` (Boing AccountId = `0x` + 64 hex)
- `GET /v1/me/wallet/secret` Bearer → export custodial private key
- `POST /v1/market/purchase` `{ skin_id, points? }` → treasury mint NFT to custodial wallet

Market mint needs Node + `boing-sdk` on the API host (prefer `cargo run -p pudgymon-accounts` with `BOING_SECRET_HEX` set). See [`docs/BOING_INTEGRATION.md`](BOING_INTEGRATION.md).

See [`services/accounts/README.md`](../services/accounts/README.md).
