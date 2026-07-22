//! Weekly party-pass challenges (JSON-driven, off-chain).

use std::collections::HashMap;
use std::fs;

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

use crate::season::SeasonLedger;

#[derive(Debug, Clone, Deserialize)]
pub struct ChallengeDef {
    pub id: String,
    pub label: String,
    pub target: u32,
    pub reward_points: u32,
}

#[derive(Debug, Clone, Deserialize)]
struct ChallengesFile {
    week: u32,
    challenges: Vec<ChallengeDef>,
}

#[derive(Resource, Debug, Clone)]
pub struct ChallengeBoard {
    pub week: u32,
    pub defs: Vec<ChallengeDef>,
    pub progress: HashMap<String, u32>,
    pub claimed: Vec<String>,
}

impl Default for ChallengeBoard {
    fn default() -> Self {
        Self {
            week: 1,
            defs: Vec::new(),
            progress: HashMap::new(),
            claimed: Vec::new(),
        }
    }
}

impl ChallengeBoard {
    pub fn load() -> Self {
        let path = format!(
            "{}/data/challenges/weekly.json",
            env!("CARGO_MANIFEST_DIR")
        );
        let Ok(raw) = fs::read_to_string(&path) else {
            return Self::default();
        };
        let Ok(file) = serde_json::from_str::<ChallengesFile>(&raw) else {
            return Self::default();
        };
        let mut board = Self {
            week: file.week,
            defs: file.challenges,
            progress: HashMap::new(),
            claimed: Vec::new(),
        };
        if let Some(saved) = ChallengeProgressFile::load() {
            if saved.week == board.week {
                board.progress = saved.progress;
                board.claimed = saved.claimed;
            }
        }
        board
    }

    pub fn bump(&mut self, id: &str, amount: u32) {
        *self.progress.entry(id.to_string()).or_insert(0) += amount;
    }

    pub fn set_max(&mut self, id: &str, value: u32) {
        let entry = self.progress.entry(id.to_string()).or_insert(0);
        *entry = (*entry).max(value);
    }

    pub fn summary_line(&self) -> String {
        let parts: Vec<String> = self
            .defs
            .iter()
            .take(3)
            .map(|d| {
                let p = self.progress.get(&d.id).copied().unwrap_or(0);
                let done = if self.claimed.contains(&d.id) {
                    "✓"
                } else if p >= d.target {
                    "!"
                } else {
                    ""
                };
                format!("{} {}/{}/{}", done, d.label, p.min(d.target), d.target)
            })
            .collect();
        if parts.is_empty() {
            "No weekly challenges loaded".into()
        } else {
            format!("W{} · {}", self.week, parts.join(" · "))
        }
    }

    pub fn save(&self) {
        ChallengeProgressFile {
            week: self.week,
            progress: self.progress.clone(),
            claimed: self.claimed.clone(),
        }
        .save();
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct ChallengeProgressFile {
    week: u32,
    progress: HashMap<String, u32>,
    claimed: Vec<String>,
}

impl ChallengeProgressFile {
    fn path() -> std::path::PathBuf {
        if let Ok(base) = std::env::var("LOCALAPPDATA") {
            std::path::PathBuf::from(base)
                .join(crate::brand::APP_DATA_DIR)
                .join("challenges.json")
        } else {
            std::path::PathBuf::from("challenges.json")
        }
    }

    fn load() -> Option<Self> {
        let raw = fs::read_to_string(Self::path()).ok()?;
        serde_json::from_str(&raw).ok()
    }

    fn save(&self) {
        let path = Self::path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(json) = serde_json::to_string_pretty(self) {
            let _ = fs::write(path, json);
        }
    }
}

pub struct ChallengesPlugin;

impl Plugin for ChallengesPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(ChallengeBoard::load())
            .add_systems(Update, (claim_completed_challenges, persist_challenges));
    }
}

fn claim_completed_challenges(
    mut board: ResMut<ChallengeBoard>,
    mut season: ResMut<SeasonLedger>,
    mut banner: ResMut<crate::session_flow::NetworkBanner>,
) {
    let mut reward = 0u32;
    let mut newly = Vec::new();
    let mut labels = Vec::new();
    for def in &board.defs {
        if board.claimed.contains(&def.id) {
            continue;
        }
        let p = board.progress.get(&def.id).copied().unwrap_or(0);
        if p >= def.target {
            newly.push(def.id.clone());
            labels.push(def.label.clone());
            reward = reward.saturating_add(def.reward_points);
        }
    }
    if newly.is_empty() {
        return;
    }
    for id in newly {
        board.claimed.push(id);
    }
    // Award challenge points without bumping parties_played.
    season.points = season.points.saturating_add(reward);
    board.save();
    let summary = if labels.len() == 1 {
        format!("Challenge complete: {} (+{} pts)", labels[0], reward)
    } else {
        format!(
            "{} challenges complete (+{} pts)",
            labels.len(),
            reward
        )
    };
    banner.show(summary, 3.5);
}

fn persist_challenges(board: Res<ChallengeBoard>) {
    if board.is_changed() {
        board.save();
    }
}
