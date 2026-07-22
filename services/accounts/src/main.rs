//! PudgyMon accounts API — email/password auth + custodial Boing wallets.

mod wallet;

use std::{
    env, fs,
    net::SocketAddr,
    path::PathBuf,
    process::Stdio,
    sync::Arc,
    time::Duration,
};

use argon2::{
    password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use axum::{
    extract::State,
    http::{header, HeaderMap, Method, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use chrono::{Duration as ChronoDuration, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use rand_core::OsRng;
use serde::{Deserialize, Serialize};
use sqlx::{postgres::PgPoolOptions, FromRow, PgPool};
use tokio::process::Command;
use tower_http::cors::{Any, CorsLayer};
use uuid::Uuid;

#[derive(Clone)]
struct AppState {
    pool: PgPool,
    jwt_secret: String,
    /// AES master for encrypting custodial Boing secrets (defaults to JWT_SECRET).
    wallet_master: String,
    catalog: Arc<Vec<CatalogItem>>,
    mint_script: PathBuf,
    node_bin: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    email: String,
    exp: i64,
}

#[derive(Debug, FromRow)]
struct UserRow {
    id: Uuid,
    email: String,
    password_hash: String,
    display_name: String,
    boing_wallet: Option<String>,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Serialize, Clone)]
struct Profile {
    id: Uuid,
    email: String,
    display_name: String,
    boing_wallet: Option<String>,
    created_at: chrono::DateTime<Utc>,
    #[serde(default)]
    owned_skins: Vec<String>,
    #[serde(default)]
    season_points: i32,
}

impl From<UserRow> for Profile {
    fn from(u: UserRow) -> Self {
        Self {
            id: u.id,
            email: u.email,
            display_name: u.display_name,
            boing_wallet: u.boing_wallet,
            created_at: u.created_at,
            owned_skins: Vec::new(),
            season_points: 0,
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
struct CatalogItem {
    id: String,
    label: String,
    cost_points: u32,
    #[serde(default)]
    #[allow(dead_code)]
    boing_token_id: Option<u64>,
}

#[derive(Debug, Deserialize)]
struct CatalogFile {
    items: Vec<CatalogItem>,
}

#[derive(Debug, Deserialize)]
struct SeasonSyncRequest {
    points: u32,
}

#[derive(Debug, Deserialize)]
struct PurchaseRequest {
    skin_id: String,
    /// Client-reported season points (also synced to users.season_points).
    #[serde(default)]
    points: Option<u32>,
}

#[derive(Debug, Serialize)]
struct PurchaseResponse {
    skin_id: String,
    boing_token_id: i64,
    tx_hash: Option<String>,
    owned_skins: Vec<String>,
    note: String,
}

#[derive(Debug, Deserialize)]
struct MintScriptResult {
    ok: bool,
    #[serde(default)]
    #[allow(dead_code)]
    token_id: Option<u64>,
    #[serde(default)]
    tx_hash: Option<String>,
    #[serde(default)]
    error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct SignupRequest {
    email: String,
    password: String,
    display_name: String,
}

#[derive(Debug, Deserialize)]
struct LoginRequest {
    email: String,
    password: String,
}

#[derive(Debug, Deserialize)]
struct PatchMeRequest {
    display_name: Option<String>,
    boing_wallet: Option<String>,
}

#[derive(Debug, Serialize)]
struct AuthResponse {
    access_token: String,
    profile: Profile,
    /// Present only when a new custodial wallet was just created (save this offline).
    #[serde(skip_serializing_if = "Option::is_none")]
    boing_wallet_secret: Option<String>,
}

#[derive(Debug, Serialize)]
struct WalletSecretResponse {
    boing_wallet: String,
    boing_wallet_secret: String,
}

#[derive(Debug, Serialize)]
struct ErrorBody {
    error: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| {
        "postgres://pudgymon:pudgymon@127.0.0.1:5434/pudgymon_accounts".into()
    });
    let jwt_secret = env::var("JWT_SECRET").unwrap_or_else(|_| "dev-only-change-me".into());
    let wallet_master = env::var("WALLET_MASTER_KEY")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| jwt_secret.clone());
    let port: u16 = env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8787);

    let pool = PgPoolOptions::new()
        .max_connections(10)
        .acquire_timeout(Duration::from_secs(10))
        .connect(&database_url)
        .await?;

    run_migrations(&pool).await?;

    let catalog = Arc::new(load_catalog());
    let mint_script = env::var("BOING_MINT_SCRIPT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../scripts/boing/mint_skin.mjs")
        });
    let node_bin = env::var("NODE_BIN").unwrap_or_else(|_| "node".into());

    let state = AppState {
        pool,
        jwt_secret,
        wallet_master,
        catalog,
        mint_script,
        node_bin,
    };

    // Open CORS for local web + Vercel static site talking to this API.
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST, Method::PATCH, Method::OPTIONS])
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/v1/auth/signup", post(signup))
        .route("/v1/auth/login", post(login))
        .route("/v1/me", get(me).patch(patch_me))
        .route("/v1/me/season", post(sync_season))
        .route("/v1/me/wallet/secret", get(export_wallet_secret))
        .route("/v1/market/purchase", post(purchase_skin))
        .layer(cors)
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("pudgymon-accounts listening on {addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

async fn run_migrations(pool: &PgPool) -> Result<(), sqlx::Error> {
    // sqlx prepared statements allow one command each.
    sqlx::query(r#"CREATE EXTENSION IF NOT EXISTS "pgcrypto""#)
        .execute(pool)
        .await?;
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            boing_wallet TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        "#,
    )
    .execute(pool)
    .await?;
    sqlx::query(r#"CREATE INDEX IF NOT EXISTS users_email_idx ON users (email)"#)
        .execute(pool)
        .await?;
    sqlx::query(
        r#"
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS boing_wallet_secret_enc TEXT NULL
        "#,
    )
    .execute(pool)
    .await?;
    sqlx::query(
        r#"
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS season_points INTEGER NOT NULL DEFAULT 0
        "#,
    )
    .execute(pool)
    .await?;
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS owned_skins (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            skin_id TEXT NOT NULL,
            boing_token_id BIGINT NOT NULL,
            tx_hash TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, skin_id)
        )
        "#,
    )
    .execute(pool)
    .await?;
    sqlx::query(r#"CREATE INDEX IF NOT EXISTS owned_skins_user_idx ON owned_skins (user_id)"#)
        .execute(pool)
        .await?;
    sqlx::query(r#"CREATE SEQUENCE IF NOT EXISTS owned_skins_token_seq START WITH 1001"#)
        .execute(pool)
        .await?;
    Ok(())
}

fn load_catalog() -> Vec<CatalogItem> {
    let path = env::var("PUDGYMON_CATALOG_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../data/cosmetics/catalog.json")
        });
    match fs::read_to_string(&path) {
        Ok(raw) => match serde_json::from_str::<CatalogFile>(&raw) {
            Ok(file) => {
                tracing::info!(
                    path = %path.display(),
                    items = file.items.len(),
                    "loaded cosmetics catalog"
                );
                file.items
            }
            Err(e) => {
                tracing::warn!("catalog parse failed ({}): {e}", path.display());
                Vec::new()
            }
        },
        Err(e) => {
            tracing::warn!("catalog missing ({}): {e}", path.display());
            Vec::new()
        }
    }
}

async fn load_owned_skins(pool: &PgPool, user_id: Uuid) -> Result<Vec<String>, ApiError> {
    let rows = sqlx::query_as::<_, (String,)>(
        r#"SELECT skin_id FROM owned_skins WHERE user_id = $1 ORDER BY created_at"#,
    )
    .bind(user_id)
    .fetch_all(pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?;
    Ok(rows.into_iter().map(|r| r.0).collect())
}

async fn load_season_points(pool: &PgPool, user_id: Uuid) -> Result<i32, ApiError> {
    let pts = sqlx::query_as::<_, (i32,)>(r#"SELECT season_points FROM users WHERE id = $1"#)
        .bind(user_id)
        .fetch_optional(pool)
        .await
        .map_err(|e| ApiError::internal(e.to_string()))?
        .map(|r| r.0)
        .unwrap_or(0);
    Ok(pts)
}

async fn enrich_profile(pool: &PgPool, mut profile: Profile) -> Result<Profile, ApiError> {
    profile.owned_skins = load_owned_skins(pool, profile.id).await?;
    profile.season_points = load_season_points(pool, profile.id).await?;
    Ok(profile)
}

async fn signup(
    State(state): State<AppState>,
    Json(body): Json<SignupRequest>,
) -> Result<Json<AuthResponse>, ApiError> {
    let email = normalize_email(&body.email)?;
    let display_name = body.display_name.trim().to_string();
    if display_name.is_empty() || display_name.len() > 48 {
        return Err(ApiError::bad("display_name must be 1–48 characters"));
    }
    if body.password.len() < 8 {
        return Err(ApiError::bad("password must be at least 8 characters"));
    }

    let (boing_wallet, boing_secret) = wallet::generate_boing_wallet();
    let secret_enc = wallet::encrypt_wallet_secret(&state.wallet_master, &boing_secret)
        .map_err(ApiError::internal)?;

    let hash = hash_password(&body.password)?;
    let row = sqlx::query_as::<_, UserRow>(
        r#"
        INSERT INTO users (email, password_hash, display_name, boing_wallet, boing_wallet_secret_enc)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, email, password_hash, display_name, boing_wallet, created_at
        "#,
    )
    .bind(&email)
    .bind(&hash)
    .bind(&display_name)
    .bind(&boing_wallet)
    .bind(&secret_enc)
    .fetch_one(&state.pool)
    .await
    .map_err(|e| {
        if let sqlx::Error::Database(db) = &e {
            if db.constraint() == Some("users_email_key") {
                return ApiError::conflict("email already registered");
            }
        }
        ApiError::internal(e.to_string())
    })?;

    let profile = enrich_profile(&state.pool, Profile::from(row)).await?;
    let token = issue_token(&state.jwt_secret, &profile)?;
    tracing::info!(
        user_id = %profile.id,
        wallet = %boing_wallet,
        "created custodial Boing wallet on signup"
    );
    Ok(Json(AuthResponse {
        access_token: token,
        profile,
        boing_wallet_secret: Some(boing_secret),
    }))
}

async fn login(
    State(state): State<AppState>,
    Json(body): Json<LoginRequest>,
) -> Result<Json<AuthResponse>, ApiError> {
    let email = normalize_email(&body.email)?;
    let row = sqlx::query_as::<_, UserRow>(
        r#"
        SELECT id, email, password_hash, display_name, boing_wallet, created_at
        FROM users WHERE email = $1
        "#,
    )
    .bind(&email)
    .fetch_optional(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?
    .ok_or_else(|| ApiError::unauthorized("invalid email or password"))?;

    verify_password(&body.password, &row.password_hash)?;

    let (profile, new_secret) = ensure_custodial_wallet(&state, row).await?;
    let profile = enrich_profile(&state.pool, profile).await?;
    let token = issue_token(&state.jwt_secret, &profile)?;
    Ok(Json(AuthResponse {
        access_token: token,
        profile,
        boing_wallet_secret: new_secret,
    }))
}

/// Backfill a custodial wallet for accounts created before wallet-on-signup.
async fn ensure_custodial_wallet(
    state: &AppState,
    row: UserRow,
) -> Result<(Profile, Option<String>), ApiError> {
    if row
        .boing_wallet
        .as_deref()
        .is_some_and(wallet::is_valid_boing_account)
    {
        return Ok((Profile::from(row), None));
    }

    let (boing_wallet, boing_secret) = wallet::generate_boing_wallet();
    let secret_enc = wallet::encrypt_wallet_secret(&state.wallet_master, &boing_secret)
        .map_err(ApiError::internal)?;
    sqlx::query(
        r#"
        UPDATE users
        SET boing_wallet = $1, boing_wallet_secret_enc = $2
        WHERE id = $3
        "#,
    )
    .bind(&boing_wallet)
    .bind(&secret_enc)
    .bind(row.id)
    .execute(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?;

    let mut profile = Profile::from(row);
    profile.boing_wallet = Some(boing_wallet);
    tracing::info!(user_id = %profile.id, "backfilled custodial Boing wallet");
    Ok((profile, Some(boing_secret)))
}

async fn me(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<Profile>, ApiError> {
    let user_id = auth_user_id(&state, &headers)?;
    let row = sqlx::query_as::<_, UserRow>(
        r#"
        SELECT id, email, password_hash, display_name, boing_wallet, created_at
        FROM users WHERE id = $1
        "#,
    )
    .bind(user_id)
    .fetch_optional(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?
    .ok_or_else(|| ApiError::unauthorized("user not found"))?;
    Ok(Json(
        enrich_profile(&state.pool, Profile::from(row)).await?,
    ))
}

async fn sync_season(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<SeasonSyncRequest>,
) -> Result<Json<Profile>, ApiError> {
    let user_id = auth_user_id(&state, &headers)?;
    sqlx::query(r#"UPDATE users SET season_points = $1 WHERE id = $2"#)
        .bind(body.points as i32)
        .bind(user_id)
        .execute(&state.pool)
        .await
        .map_err(|e| ApiError::internal(e.to_string()))?;
    let row = sqlx::query_as::<_, UserRow>(
        r#"
        SELECT id, email, password_hash, display_name, boing_wallet, created_at
        FROM users WHERE id = $1
        "#,
    )
    .bind(user_id)
    .fetch_one(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?;
    Ok(Json(
        enrich_profile(&state.pool, Profile::from(row)).await?,
    ))
}

async fn purchase_skin(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<PurchaseRequest>,
) -> Result<Json<PurchaseResponse>, ApiError> {
    let user_id = auth_user_id(&state, &headers)?;
    let skin_id = body.skin_id.trim().to_string();
    if skin_id.is_empty() {
        return Err(ApiError::bad("skin_id required"));
    }

    let item = state
        .catalog
        .iter()
        .find(|i| i.id == skin_id)
        .cloned()
        .ok_or_else(|| ApiError::bad("unknown skin_id"))?;

    // Already owned → idempotent success.
    if let Some(existing) = sqlx::query_as::<_, (i64, Option<String>)>(
        r#"SELECT boing_token_id, tx_hash FROM owned_skins WHERE user_id = $1 AND skin_id = $2"#,
    )
    .bind(user_id)
    .bind(&skin_id)
    .fetch_optional(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?
    {
        let owned = load_owned_skins(&state.pool, user_id).await?;
        return Ok(Json(PurchaseResponse {
            skin_id,
            boing_token_id: existing.0,
            tx_hash: existing.1,
            owned_skins: owned,
            note: "Already owned.".into(),
        }));
    }

    if let Some(points) = body.points {
        sqlx::query(r#"UPDATE users SET season_points = $1 WHERE id = $2"#)
            .bind(points as i32)
            .bind(user_id)
            .execute(&state.pool)
            .await
            .map_err(|e| ApiError::internal(e.to_string()))?;
    }

    let season_points = load_season_points(&state.pool, user_id).await?;
    if (season_points as u32) < item.cost_points {
        return Err(ApiError::bad(format!(
            "need {} season points (have {})",
            item.cost_points, season_points
        )));
    }

    let row = sqlx::query_as::<_, (Option<String>, Option<String>)>(
        r#"SELECT boing_wallet, boing_wallet_secret_enc FROM users WHERE id = $1"#,
    )
    .bind(user_id)
    .fetch_optional(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?
    .ok_or_else(|| ApiError::unauthorized("user not found"))?;

    let wallet = row
        .0
        .filter(|w| wallet::is_valid_boing_account(w))
        .ok_or_else(|| ApiError::bad("no Boing wallet on this account"))?;
    if row.1.is_none() {
        return Err(ApiError::bad(
            "no custodial secret — use Claim Desk / Boing Express for external wallets",
        ));
    }

    let token_id: i64 = sqlx::query_as::<_, (i64,)>(r#"SELECT nextval('owned_skins_token_seq')"#)
        .fetch_one(&state.pool)
        .await
        .map_err(|e| ApiError::internal(e.to_string()))?
        .0;

    let mint = run_mint_script(&state, &wallet, token_id as u64).await?;
    if !mint.ok {
        return Err(ApiError::internal(
            mint.error.unwrap_or_else(|| "mint failed".into()),
        ));
    }

    sqlx::query(
        r#"
        INSERT INTO owned_skins (user_id, skin_id, boing_token_id, tx_hash)
        VALUES ($1, $2, $3, $4)
        "#,
    )
    .bind(user_id)
    .bind(&skin_id)
    .bind(token_id)
    .bind(mint.tx_hash.as_deref())
    .execute(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?;

    let owned = load_owned_skins(&state.pool, user_id).await?;
    tracing::info!(
        user_id = %user_id,
        skin = %skin_id,
        token_id,
        tx = ?mint.tx_hash,
        "minted skin NFT"
    );
    Ok(Json(PurchaseResponse {
        skin_id: skin_id.clone(),
        boing_token_id: token_id,
        tx_hash: mint.tx_hash.clone(),
        owned_skins: owned,
        note: format!(
            "Minted {} (token {}) · {}",
            item.label,
            token_id,
            mint.tx_hash.unwrap_or_else(|| "ok".into())
        ),
    }))
}

async fn run_mint_script(
    state: &AppState,
    recipient: &str,
    token_id: u64,
) -> Result<MintScriptResult, ApiError> {
    if !state.mint_script.is_file() {
        return Err(ApiError::internal(format!(
            "mint script missing: {}",
            state.mint_script.display()
        )));
    }
    let output = Command::new(&state.node_bin)
        .arg(&state.mint_script)
        .arg("--to")
        .arg(recipient)
        .arg("--token-id")
        .arg(token_id.to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await
        .map_err(|e| ApiError::internal(format!("failed to spawn node mint: {e}")))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if stdout.is_empty() {
        return Err(ApiError::internal(format!(
            "mint script produced no stdout (exit {:?}): {stderr}",
            output.status.code()
        )));
    }
    // Prefer last JSON line (script may log to stderr; stdout is one JSON object).
    let line = stdout.lines().last().unwrap_or(&stdout);
    match serde_json::from_str::<MintScriptResult>(line) {
        Ok(result) => Ok(result),
        Err(e) => Err(ApiError::internal(format!(
            "bad mint json ({e}): {line} stderr={stderr}"
        ))),
    }
}

async fn patch_me(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<PatchMeRequest>,
) -> Result<Json<Profile>, ApiError> {
    let user_id = auth_user_id(&state, &headers)?;

    if let Some(name) = body.display_name.as_ref() {
        let name = name.trim();
        if name.is_empty() || name.len() > 48 {
            return Err(ApiError::bad("display_name must be 1–48 characters"));
        }
        sqlx::query("UPDATE users SET display_name = $1 WHERE id = $2")
            .bind(name)
            .bind(user_id)
            .execute(&state.pool)
            .await
            .map_err(|e| ApiError::internal(e.to_string()))?;
    }

    if let Some(wallet) = body.boing_wallet.as_ref() {
        let wallet = wallet.trim();
        let value = if wallet.is_empty() {
            None
        } else if wallet::is_valid_boing_account(wallet) {
            Some(wallet.to_string())
        } else {
            return Err(ApiError::bad(
                "boing_wallet must be a Boing AccountId (0x + 64 hex)",
            ));
        };
        // Replacing/clearing the public address drops the custodial secret.
        sqlx::query(
            r#"
            UPDATE users
            SET boing_wallet = $1, boing_wallet_secret_enc = NULL
            WHERE id = $2
            "#,
        )
        .bind(value)
        .bind(user_id)
        .execute(&state.pool)
        .await
        .map_err(|e| ApiError::internal(e.to_string()))?;
    }

    let row = sqlx::query_as::<_, UserRow>(
        r#"
        SELECT id, email, password_hash, display_name, boing_wallet, created_at
        FROM users WHERE id = $1
        "#,
    )
    .bind(user_id)
    .fetch_one(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?;
    Ok(Json(
        enrich_profile(&state.pool, Profile::from(row)).await?,
    ))
}

async fn export_wallet_secret(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Json<WalletSecretResponse>, ApiError> {
    let user_id = auth_user_id(&state, &headers)?;
    let row = sqlx::query_as::<_, (Option<String>, Option<String>)>(
        r#"
        SELECT boing_wallet, boing_wallet_secret_enc
        FROM users WHERE id = $1
        "#,
    )
    .bind(user_id)
    .fetch_optional(&state.pool)
    .await
    .map_err(|e| ApiError::internal(e.to_string()))?
    .ok_or_else(|| ApiError::unauthorized("user not found"))?;

    let (wallet, enc) = row;
    let wallet = wallet
        .filter(|w| wallet::is_valid_boing_account(w))
        .ok_or_else(|| ApiError::bad("no Boing wallet on this account"))?;
    let enc = enc.ok_or_else(|| {
        ApiError::bad("no custodial secret (wallet was linked externally)")
    })?;
    let secret = wallet::decrypt_wallet_secret(&state.wallet_master, &enc)
        .map_err(ApiError::internal)?;
    Ok(Json(WalletSecretResponse {
        boing_wallet: wallet,
        boing_wallet_secret: secret,
    }))
}

fn normalize_email(email: &str) -> Result<String, ApiError> {
    let email = email.trim().to_lowercase();
    if !email.contains('@') || email.len() < 5 || email.len() > 254 {
        return Err(ApiError::bad("invalid email"));
    }
    Ok(email)
}

fn hash_password(password: &str) -> Result<String, ApiError> {
    let salt = SaltString::generate(&mut OsRng);
    Argon2::default()
        .hash_password(password.as_bytes(), &salt)
        .map(|h| h.to_string())
        .map_err(|e| ApiError::internal(e.to_string()))
}

fn verify_password(password: &str, hash: &str) -> Result<(), ApiError> {
    let parsed = PasswordHash::new(hash).map_err(|_| ApiError::unauthorized("invalid email or password"))?;
    Argon2::default()
        .verify_password(password.as_bytes(), &parsed)
        .map_err(|_| ApiError::unauthorized("invalid email or password"))
}

fn issue_token(secret: &str, profile: &Profile) -> Result<String, ApiError> {
    let exp = (Utc::now() + ChronoDuration::days(7)).timestamp();
    let claims = Claims {
        sub: profile.id.to_string(),
        email: profile.email.clone(),
        exp,
    };
    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
    .map_err(|e| ApiError::internal(e.to_string()))
}

fn auth_user_id(state: &AppState, headers: &HeaderMap) -> Result<Uuid, ApiError> {
    let auth = headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| ApiError::unauthorized("missing Authorization"))?;
    let token = auth
        .strip_prefix("Bearer ")
        .ok_or_else(|| ApiError::unauthorized("expected Bearer token"))?;
    let data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(state.jwt_secret.as_bytes()),
        &Validation::default(),
    )
    .map_err(|_| ApiError::unauthorized("invalid or expired token"))?;
    Uuid::parse_str(&data.claims.sub).map_err(|_| ApiError::unauthorized("invalid token subject"))
}

struct ApiError {
    status: StatusCode,
    message: String,
}

impl ApiError {
    fn bad(msg: impl Into<String>) -> Self {
        Self {
            status: StatusCode::BAD_REQUEST,
            message: msg.into(),
        }
    }
    fn unauthorized(msg: impl Into<String>) -> Self {
        Self {
            status: StatusCode::UNAUTHORIZED,
            message: msg.into(),
        }
    }
    fn conflict(msg: impl Into<String>) -> Self {
        Self {
            status: StatusCode::CONFLICT,
            message: msg.into(),
        }
    }
    fn internal(msg: impl Into<String>) -> Self {
        Self {
            status: StatusCode::INTERNAL_SERVER_ERROR,
            message: msg.into(),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (
            self.status,
            Json(ErrorBody {
                error: self.message,
            }),
        )
            .into_response()
    }
}
