-- On-chain skin ownership mirror + soft season points for Market gating.
ALTER TABLE users
ADD COLUMN IF NOT EXISTS season_points INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS owned_skins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    skin_id TEXT NOT NULL,
    boing_token_id BIGINT NOT NULL,
    tx_hash TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, skin_id)
);

CREATE INDEX IF NOT EXISTS owned_skins_user_idx ON owned_skins (user_id);

CREATE SEQUENCE IF NOT EXISTS owned_skins_token_seq START WITH 1001;