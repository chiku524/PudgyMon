//! Cloud PudgyMon account session (JWT from web signup/login).

use std::fs;
use std::path::PathBuf;
use std::process::Command;

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

use crate::brand::APP_DATA_DIR;

#[derive(Resource, Debug, Clone, Serialize, Deserialize, Default)]
pub struct PlayerAccount {
    pub user_id: String,
    pub email: String,
    pub display_name: String,
    pub boing_wallet: Option<String>,
    #[serde(default)]
    pub owned_skins: Vec<String>,
    pub access_token: String,
    pub api_base: String,
    pub note: String,
}

impl PlayerAccount {
    pub fn signed_in(&self) -> bool {
        !self.access_token.is_empty() && !self.user_id.is_empty()
    }

    pub fn session_path() -> PathBuf {
        app_data_dir().join("account_session.json")
    }

    pub fn pending_token_path() -> PathBuf {
        app_data_dir().join("pending_token.txt")
    }

    pub fn load() -> Self {
        let path = Self::session_path();
        let Ok(raw) = fs::read_to_string(&path) else {
            return Self {
                api_base: default_api_base(),
                ..Default::default()
            };
        };
        let mut account: Self = serde_json::from_str(&raw).unwrap_or_default();
        if account.api_base.is_empty() {
            account.api_base = default_api_base();
        }
        account
    }

    pub fn save(&self) {
        let path = Self::session_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(json) = serde_json::to_string_pretty(self) {
            let _ = fs::write(path, json);
        }
    }

    pub fn clear(&mut self) {
        let api = if self.api_base.is_empty() {
            default_api_base()
        } else {
            self.api_base.clone()
        };
        *self = Self {
            api_base: api,
            note: "Signed out.".into(),
            ..Default::default()
        };
        self.save();
    }
}

fn app_data_dir() -> PathBuf {
    if let Ok(base) = std::env::var("LOCALAPPDATA") {
        PathBuf::from(base).join(APP_DATA_DIR)
    } else {
        PathBuf::from(APP_DATA_DIR)
    }
}

fn default_api_base() -> String {
    std::env::var("PUDGYMON_ACCOUNTS_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8788".into())
}

pub fn web_index_path() -> PathBuf {
    if let Ok(url) = std::env::var("PUDGYMON_WEB_URL") {
        return PathBuf::from(url);
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("web/index.html")
}

pub fn open_path_or_url(path: &str) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", path])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        Command::new("xdg-open")
            .arg(path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[derive(Debug, Deserialize)]
struct ApiProfile {
    #[serde(deserialize_with = "deserialize_id")]
    id: String,
    email: String,
    display_name: String,
    boing_wallet: Option<String>,
    #[serde(default)]
    owned_skins: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct PurchaseResponse {
    skin_id: String,
    #[serde(default)]
    boing_token_id: i64,
    #[serde(default)]
    tx_hash: Option<String>,
    #[serde(default)]
    owned_skins: Vec<String>,
    #[serde(default)]
    note: String,
}

fn deserialize_id<'de, D>(deserializer: D) -> Result<String, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let v = serde_json::Value::deserialize(deserializer)?;
    Ok(match v {
        serde_json::Value::String(s) => s,
        other => other.to_string().trim_matches('"').to_string(),
    })
}

#[derive(Debug, Deserialize)]
struct ApiErrorBody {
    error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct AuthResponse {
    access_token: String,
    profile: ApiProfile,
}

pub struct AccountPlugin;

impl Plugin for AccountPlugin {
    fn build(&self, app: &mut App) {
        let mut account = PlayerAccount::load();
        if let Ok(token) = std::env::var("PUDGYMON_ACCOUNT_TOKEN") {
            if !token.trim().is_empty() {
                account.access_token = token.trim().to_string();
                account.note = "Loaded PUDGYMON_ACCOUNT_TOKEN env.".into();
                account.save();
            }
        }
        app.insert_resource(account)
            .add_systems(Startup, (refresh_account_on_boot, sync_owned_skins_on_boot).chain())
            .add_systems(Update, sync_owned_skins_when_account_changes);
    }
}

fn refresh_account_on_boot(mut account: ResMut<PlayerAccount>) {
    if account.access_token.is_empty() {
        return;
    }
    match fetch_me(&account.api_base, &account.access_token) {
        Ok(profile) => {
            apply_profile(&mut account, profile);
            account.note = "Account session restored.".into();
            account.save();
        }
        Err(err) => {
            account.note = format!("Session refresh failed: {err}");
        }
    }
}

/// Merge cloud owned skins into the local season unlock list after login/refresh.
pub fn merge_owned_skins_into_ledger(
    account: &PlayerAccount,
    ledger: &mut crate::season::SeasonLedger,
) {
    let mut dirty = false;
    for id in &account.owned_skins {
        if !ledger.unlocked.contains(id) {
            ledger.unlocked.push(id.clone());
            dirty = true;
        }
    }
    if dirty {
        ledger.save();
    }
}

fn sync_owned_skins_on_boot(
    account: Res<PlayerAccount>,
    mut ledger: ResMut<crate::season::SeasonLedger>,
) {
    merge_owned_skins_into_ledger(&account, &mut ledger);
}

fn sync_owned_skins_when_account_changes(
    account: Res<PlayerAccount>,
    mut ledger: ResMut<crate::season::SeasonLedger>,
) {
    if !account.is_changed() {
        return;
    }
    merge_owned_skins_into_ledger(&account, &mut ledger);
}

pub fn open_website(account: &mut PlayerAccount) -> String {
    let path = web_index_path();
    let target = if path.is_file() {
        path.to_string_lossy().to_string()
    } else if let Ok(url) = std::env::var("PUDGYMON_WEB_URL") {
        url
    } else {
        account.note = "Website missing (web/index.html). Set PUDGYMON_WEB_URL.".into();
        return account.note.clone();
    };
    match open_path_or_url(&target) {
        Ok(()) => {
            account.note = "Opened PudgyMon website.".into();
        }
        Err(e) => {
            account.note = format!("Could not open website: {e}");
        }
    }
    account.note.clone()
}

/// Consume `%LOCALAPPDATA%/PudgyMon/pending_token.txt` or `PUDGYMON_ACCOUNT_TOKEN`.
pub fn link_pending_token(account: &mut PlayerAccount) -> String {
    let mut token = std::env::var("PUDGYMON_ACCOUNT_TOKEN")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty());

    if token.is_none() {
        let path = PlayerAccount::pending_token_path();
        if let Ok(raw) = fs::read_to_string(&path) {
            let t = raw.trim().to_string();
            if !t.is_empty() {
                token = Some(t);
                let _ = fs::remove_file(path);
            }
        }
    }

    let Some(token) = token else {
        account.note = format!(
            "No token found. Download pending_token.txt from the website into {}",
            PlayerAccount::pending_token_path().display()
        );
        return account.note.clone();
    };

    account.access_token = token;
    match fetch_me(&account.api_base, &account.access_token) {
        Ok(profile) => {
            apply_profile(account, profile);
            account.note = format!("Signed in as {}", account.display_name);
            account.save();
        }
        Err(err) => {
            account.note = format!("Token rejected: {err}");
        }
    }
    account.note.clone()
}

pub fn refresh_profile(account: &mut PlayerAccount) -> String {
    if account.access_token.is_empty() {
        account.note = "Not signed in.".into();
        return account.note.clone();
    }
    match fetch_me(&account.api_base, &account.access_token) {
        Ok(profile) => {
            apply_profile(account, profile);
            account.note = "Profile refreshed.".into();
            account.save();
        }
        Err(err) => {
            account.note = format!("Refresh failed: {err}");
        }
    }
    account.note.clone()
}

/// Email/password login against accounts API; persists JWT session on success.
pub fn login(account: &mut PlayerAccount, email: &str, password: &str) -> String {
    match auth_request(
        &account.api_base,
        "/v1/auth/login",
        &serde_json::json!({ "email": email, "password": password }),
    ) {
        Ok(auth) => {
            account.access_token = auth.access_token;
            apply_profile(account, auth.profile);
            account.note = match account.boing_wallet.as_deref() {
                Some(w) => format!("Signed in as {} · wallet {}", account.display_name, w),
                None => format!("Signed in as {}", account.display_name),
            };
            account.save();
            account.note.clone()
        }
        Err(err) => {
            account.note = format!("Sign in failed: {err}");
            account.note.clone()
        }
    }
}

/// Register a new account; persists JWT session on success.
pub fn signup(
    account: &mut PlayerAccount,
    email: &str,
    password: &str,
    display_name: &str,
) -> String {
    match auth_request(
        &account.api_base,
        "/v1/auth/signup",
        &serde_json::json!({
            "email": email,
            "password": password,
            "display_name": display_name,
        }),
    ) {
        Ok(auth) => {
            account.access_token = auth.access_token;
            apply_profile(account, auth.profile);
            account.note = match account.boing_wallet.as_deref() {
                Some(w) => format!(
                    "Registered as {} · Boing wallet linked {}",
                    account.display_name, w
                ),
                None => format!("Registered as {}", account.display_name),
            };
            account.save();
            account.note.clone()
        }
        Err(err) => {
            account.note = format!("Register failed: {err}");
            account.note.clone()
        }
    }
}

fn apply_profile(account: &mut PlayerAccount, profile: ApiProfile) {
    account.user_id = profile.id;
    account.email = profile.email;
    account.display_name = profile.display_name;
    account.boing_wallet = profile.boing_wallet;
    account.owned_skins = profile.owned_skins;
}

/// Push local season points to the accounts service (Market purchase gating).
pub fn sync_season_points(account: &mut PlayerAccount, points: u32) -> Result<(), String> {
    if account.access_token.is_empty() {
        return Err("Not signed in.".into());
    }
    let url = format!(
        "{}/v1/me/season",
        account.api_base.trim_end_matches('/')
    );
    let body = serde_json::json!({ "points": points });
    let resp = match http_agent()
        .post(&url)
        .set("Authorization", &format!("Bearer {}", account.access_token))
        .set("Content-Type", "application/json")
        .set("Accept", "application/json")
        .send_json(body)
    {
        Ok(resp) => resp,
        Err(ureq::Error::Status(_, resp)) => {
            let body = read_json_body(resp)?;
            return Err(parse_api_error(&body).unwrap_or(body));
        }
        Err(e) => return Err(format!("accounts API unreachable: {e}")),
    };
    let body = read_json_body(resp)?;
    let profile: ApiProfile =
        serde_json::from_str(&body).map_err(|e| format!("bad season json: {e}"))?;
    apply_profile(account, profile);
    account.save();
    Ok(())
}

/// Buy a skin via custodial on-chain mint (`POST /v1/market/purchase`).
pub fn purchase_skin(
    account: &mut PlayerAccount,
    skin_id: &str,
    points: u32,
) -> Result<String, String> {
    if account.access_token.is_empty() {
        return Err("Not signed in.".into());
    }
    let url = format!(
        "{}/v1/market/purchase",
        account.api_base.trim_end_matches('/')
    );
    let body = serde_json::json!({
        "skin_id": skin_id,
        "points": points,
    });
    let resp = match http_agent_long()
        .post(&url)
        .set("Authorization", &format!("Bearer {}", account.access_token))
        .set("Content-Type", "application/json")
        .set("Accept", "application/json")
        .send_json(body)
    {
        Ok(resp) => resp,
        Err(ureq::Error::Status(_, resp)) => {
            let body = read_json_body(resp)?;
            return Err(parse_api_error(&body).unwrap_or(body));
        }
        Err(e) => return Err(format!("accounts API unreachable: {e}")),
    };
    let body = read_json_body(resp)?;
    let purchase: PurchaseResponse =
        serde_json::from_str(&body).map_err(|e| format!("bad purchase json: {e}"))?;
    account.owned_skins = purchase.owned_skins;
    if !account.owned_skins.contains(&purchase.skin_id) {
        account.owned_skins.push(purchase.skin_id.clone());
    }
    let note = if purchase.note.is_empty() {
        format!(
            "Bought {} · token {} · {}",
            purchase.skin_id,
            purchase.boing_token_id,
            purchase.tx_hash.unwrap_or_else(|| "ok".into())
        )
    } else {
        purchase.note
    };
    account.note = note.clone();
    account.save();
    Ok(note)
}

fn http_agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(5))
        .timeout(std::time::Duration::from_secs(10))
        .build()
}

fn http_agent_long() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(5))
        .timeout(std::time::Duration::from_secs(120))
        .build()
}

fn read_json_body(resp: ureq::Response) -> Result<String, String> {
    resp.into_string()
        .map_err(|e| format!("read response failed: {e}"))
}

fn parse_api_error(body: &str) -> Option<String> {
    serde_json::from_str::<ApiErrorBody>(body)
        .ok()
        .and_then(|e| e.error)
}

fn auth_request(
    api_base: &str,
    path: &str,
    body: &serde_json::Value,
) -> Result<AuthResponse, String> {
    let url = format!("{}{}", api_base.trim_end_matches('/'), path);
    let resp = match http_agent()
        .post(&url)
        .set("Content-Type", "application/json")
        .set("Accept", "application/json")
        .send_json(body)
    {
        Ok(resp) => resp,
        Err(ureq::Error::Status(_, resp)) => {
            let body = read_json_body(resp)?;
            return Err(parse_api_error(&body).unwrap_or(body));
        }
        Err(e) => return Err(format!("accounts API unreachable: {e}")),
    };
    let body = read_json_body(resp)?;
    if let Some(msg) = parse_api_error(&body) {
        if serde_json::from_str::<AuthResponse>(&body).is_err() {
            return Err(msg);
        }
    }
    serde_json::from_str::<AuthResponse>(&body).map_err(|e| format!("bad auth json: {e}"))
}

fn fetch_me(api_base: &str, token: &str) -> Result<ApiProfile, String> {
    let url = format!("{}/v1/me", api_base.trim_end_matches('/'));
    let resp = match http_agent()
        .get(&url)
        .set("Authorization", &format!("Bearer {token}"))
        .set("Accept", "application/json")
        .call()
    {
        Ok(resp) => resp,
        Err(ureq::Error::Status(_, resp)) => {
            let body = read_json_body(resp)?;
            return Err(parse_api_error(&body).unwrap_or(body));
        }
        Err(e) => return Err(format!("accounts API unreachable: {e}")),
    };
    let body = read_json_body(resp)?;
    if let Some(msg) = parse_api_error(&body) {
        if serde_json::from_str::<ApiProfile>(&body).is_err() {
            return Err(msg);
        }
    }
    serde_json::from_str::<ApiProfile>(&body).map_err(|e| format!("bad profile json: {e}"))
}
