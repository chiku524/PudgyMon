//! Boing Network bridge — JSON-RPC reads + claim voucher helpers.

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct BoingConfig {
    pub rpc_url: String,
    pub chain_id: u64,
    pub nft_collection: Option<String>,
    pub fungible_token: Option<String>,
    pub linked_account: Option<String>,
}

impl Default for BoingConfig {
    fn default() -> Self {
        let rpc = std::env::var("BOING_RPC_URL")
            .unwrap_or_else(|_| "http://127.0.0.1:8545".into());
        Self {
            rpc_url: rpc,
            chain_id: 6913,
            nft_collection: None,
            fungible_token: None,
            linked_account: None,
        }
    }
}

#[derive(Resource, Debug, Clone, Default)]
pub struct BoingStatus {
    pub reachable: bool,
    pub tip_height: Option<u64>,
    pub last_error: String,
    pub native_balance: Option<String>,
}

#[derive(Resource, Debug, Clone, Default, Serialize, Deserialize)]
pub struct ClaimVoucher {
    pub skin_id: String,
    pub account: String,
    pub season_points: u32,
    pub note: String,
}

pub struct BoingPlugin;

impl Plugin for BoingPlugin {
    fn build(&self, app: &mut App) {
        let mut config = BoingConfig::default();
        if let Ok(raw) = std::fs::read_to_string(format!(
            "{}/data/boing/contracts.json",
            env!("CARGO_MANIFEST_DIR")
        )) {
            if let Ok(file) = serde_json::from_str::<BoingContractsFile>(&raw) {
                config.nft_collection = file.nft_collection;
                config.fungible_token = file.fungible_token;
                if let Some(url) = file.rpc_url {
                    config.rpc_url = url;
                }
            }
        }
        app.insert_resource(config)
            .init_resource::<BoingStatus>()
            .init_resource::<ClaimVoucher>()
            .add_systems(Startup, sync_cloud_wallet_on_boot)
            .add_systems(
                Update,
                (
                    sync_cloud_wallet_when_account_changes,
                    poll_boing_health,
                    handle_wallet_paste,
                    handle_claim_key,
                    open_claim_companion,
                ),
            );
    }
}

/// Prefer the cloud profile wallet (created at registration) as the session link.
pub fn link_cloud_wallet(
    account: &crate::account::PlayerAccount,
    config: &mut BoingConfig,
    voucher: Option<&mut ClaimVoucher>,
) -> bool {
    let Some(wallet) = account.boing_wallet.as_deref() else {
        return false;
    };
    // Boing AccountId: 0x + 64 hex (32 bytes), same check as accounts API.
    if !(wallet.starts_with("0x") && wallet.len() == 66) {
        return false;
    }
    if config.linked_account.as_deref() == Some(wallet) {
        return true;
    }
    config.linked_account = Some(wallet.to_string());
    if let Some(voucher) = voucher {
        voucher.account = wallet.to_string();
        if voucher.note.is_empty() {
            voucher.note = "Boing wallet linked from account".into();
        }
    }
    true
}

fn sync_cloud_wallet_on_boot(
    account: Res<crate::account::PlayerAccount>,
    mut config: ResMut<BoingConfig>,
    mut voucher: ResMut<ClaimVoucher>,
) {
    let _ = link_cloud_wallet(&account, &mut config, Some(&mut voucher));
}

fn sync_cloud_wallet_when_account_changes(
    account: Res<crate::account::PlayerAccount>,
    mut config: ResMut<BoingConfig>,
    mut voucher: ResMut<ClaimVoucher>,
) {
    if !account.is_changed() {
        return;
    }
    let _ = link_cloud_wallet(&account, &mut config, Some(&mut voucher));
}

#[derive(Debug, Deserialize)]
struct BoingContractsFile {
    rpc_url: Option<String>,
    nft_collection: Option<String>,
    fungible_token: Option<String>,
}

fn poll_boing_health(
    time: Res<Time>,
    config: Res<BoingConfig>,
    mut status: ResMut<BoingStatus>,
    mut timer: Local<f32>,
) {
    *timer -= time.delta_secs();
    if *timer > 0.0 {
        return;
    }
    *timer = 8.0;

    // Blocking HTTP is ok for rare polls in MVP; swap to async later.
    match boing_rpc_call(&config.rpc_url, "boing_health", "[]") {
        Ok(_) => {
            status.reachable = true;
            status.last_error.clear();
            if let Ok(info) = boing_rpc_call(&config.rpc_url, "boing_getNetworkInfo", "[]") {
                if let Some(h) = info.get("committed_height").and_then(|v| v.as_u64()) {
                    status.tip_height = Some(h);
                } else if let Some(h) = info.get("height").and_then(|v| v.as_u64()) {
                    status.tip_height = Some(h);
                }
            }
            if let Some(account) = config.linked_account.clone() {
                let params = format!("[\"{account}\"]");
                if let Ok(bal) = boing_rpc_call(&config.rpc_url, "boing_getBalance", &params) {
                    status.native_balance = bal
                        .get("balance")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());
                }
            }
        }
        Err(err) => {
            status.reachable = false;
            status.last_error = err;
        }
    }
}

fn handle_wallet_paste(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut config: ResMut<BoingConfig>,
    mut voucher: ResMut<ClaimVoucher>,
) {
    // V = paste env BOING_ACCOUNT as linked wallet (desktop can't read clipboard reliably everywhere).
    if keyboard.just_pressed(KeyCode::KeyV) && keyboard.pressed(KeyCode::ControlLeft) {
        let _ = link_wallet_from_env(&mut config, &mut voucher);
    }
}

fn handle_claim_key(
    keyboard: Res<ButtonInput<KeyCode>>,
    config: Res<BoingConfig>,
    ledger: Res<crate::season::SeasonLedger>,
    equipped: Res<crate::cosmetics::EquippedCosmetic>,
    mut voucher: ResMut<ClaimVoucher>,
) {
    if !keyboard.just_pressed(KeyCode::KeyM) {
        return;
    }
    let _ = prepare_claim_voucher(&config, &ledger, &equipped, &mut voucher);
}

fn open_claim_companion(keyboard: Res<ButtonInput<KeyCode>>, mut voucher: ResMut<ClaimVoucher>) {
    if !(keyboard.just_pressed(KeyCode::KeyO) && keyboard.pressed(KeyCode::ControlLeft)) {
        return;
    }
    let _ = open_claim_companion_page(&mut voucher);
}

/// Link `BOING_ACCOUNT` env into config/voucher. Returns a short status note.
pub fn link_wallet_from_env(config: &mut BoingConfig, voucher: &mut ClaimVoucher) -> String {
    match std::env::var("BOING_ACCOUNT") {
        Ok(account) if account.starts_with("0x") && account.len() == 66 => {
            config.linked_account = Some(account.clone());
            voucher.account = account;
            voucher.note = "Wallet linked from BOING_ACCOUNT env".into();
            voucher.note.clone()
        }
        Ok(_) => {
            voucher.note = "BOING_ACCOUNT looks invalid (want 0x + 64 hex)".into();
            voucher.note.clone()
        }
        Err(_) => {
            voucher.note = "Set BOING_ACCOUNT=0x… then link again".into();
            voucher.note.clone()
        }
    }
}

/// Build + persist a claim voucher for the companion page.
pub fn prepare_claim_voucher(
    config: &BoingConfig,
    ledger: &crate::season::SeasonLedger,
    equipped: &crate::cosmetics::EquippedCosmetic,
    voucher: &mut ClaimVoucher,
) -> String {
    let Some(account) = config.linked_account.clone() else {
        voucher.note = "Link wallet first: set BOING_ACCOUNT=0x… and Ctrl+V".into();
        return voucher.note.clone();
    };
    voucher.account = account;
    voucher.skin_id = equipped.id.clone();
    voucher.season_points = ledger.points;
    voucher.note = format!(
        "Claim voucher ready for '{}' ({} pts). Open claim companion / see docs/BOING_INTEGRATION.md",
        voucher.skin_id, voucher.season_points
    );
    let path = crate::logging::log_dir().join("claim_voucher.json");
    if let Ok(json) = serde_json::to_string_pretty(voucher) {
        let _ = std::fs::write(path, json);
    }
    voucher.note.clone()
}

/// Open the local claim companion HTML desk.
pub fn open_claim_companion_page(voucher: &mut ClaimVoucher) -> String {
    let path = format!(
        "{}/companion/claim/index.html",
        env!("CARGO_MANIFEST_DIR")
    );
    let path = std::path::PathBuf::from(path);
    if !path.is_file() {
        voucher.note = "Claim companion missing (companion/claim/index.html)".into();
        return voucher.note.clone();
    }
    #[cfg(target_os = "windows")]
    {
        let _ = std::process::Command::new("cmd")
            .args(["/C", "start", "", &path.to_string_lossy()])
            .spawn();
    }
    #[cfg(target_os = "macos")]
    {
        let _ = std::process::Command::new("open").arg(&path).spawn();
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let _ = std::process::Command::new("xdg-open").arg(&path).spawn();
    }
    voucher.note = "Opened claim companion — paste voucher JSON there".into();
    voucher.note.clone()
}

/// Minimal JSON-RPC helper via `ureq`.
pub fn boing_rpc_call(
    rpc_url: &str,
    method: &str,
    params_json: &str,
) -> Result<serde_json::Value, String> {
    let params: serde_json::Value =
        serde_json::from_str(params_json).unwrap_or(serde_json::json!([]));
    let body = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    });
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(2))
        .timeout(std::time::Duration::from_secs(3))
        .build();
    let resp = agent
        .post(rpc_url)
        .set("Content-Type", "application/json")
        .set("Accept", "application/json")
        .send_json(body)
        .map_err(|e| format!("rpc http: {e}"))?;
    let text = resp
        .into_string()
        .map_err(|e| format!("rpc read: {e}"))?;
    let v: serde_json::Value =
        serde_json::from_str(&text).map_err(|e| format!("rpc json: {e}"))?;
    if let Some(err) = v.get("error") {
        return Err(err.to_string());
    }
    Ok(v.get("result").cloned().unwrap_or(serde_json::Value::Null))
}
