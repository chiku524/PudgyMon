//! Default crew model / hat hooks — swap when Studio GLBs land.

use std::{fs, path::Path, path::PathBuf};

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

use crate::brand::APP_DATA_DIR;

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct PlayerDefaults {
    pub crew_model_id: String,
}

impl Default for PlayerDefaults {
    fn default() -> Self {
        Self {
            crew_model_id: "char_pudgy_base_01".into(),
        }
    }
}

#[derive(Deserialize)]
struct PlayerDefaultsFile {
    crew_model_id: String,
}

impl PlayerDefaults {
    /// User override beside settings (survives repo resets of the sample defaults file).
    fn user_path() -> PathBuf {
        if let Ok(base) = std::env::var("LOCALAPPDATA") {
            PathBuf::from(base).join(APP_DATA_DIR).join("player_defaults.json")
        } else {
            PathBuf::from("player_defaults.json")
        }
    }

    pub fn load(path: impl AsRef<Path>) -> Self {
        // Prefer user override, then repo sample.
        for candidate in [Self::user_path(), path.as_ref().to_path_buf()] {
            if let Ok(raw) = fs::read_to_string(&candidate) {
                match serde_json::from_str::<PlayerDefaultsFile>(&raw) {
                    Ok(file) => {
                        return Self {
                            crew_model_id: file.crew_model_id,
                        };
                    }
                    Err(err) => warn!("player_defaults parse failed ({}): {err}", candidate.display()),
                }
            }
        }
        Self::default()
    }

    pub fn save(&self) {
        let path = Self::user_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let body = serde_json::json!({
            "schema_version": 1,
            "crew_model_id": self.crew_model_id,
        });
        if let Ok(json) = serde_json::to_string_pretty(&body) {
            let _ = fs::write(path, json);
        }
    }

    pub fn set_crew_model(&mut self, model_id: impl Into<String>) {
        self.crew_model_id = model_id.into();
        self.save();
    }

    /// Returns crew model id when the GLB exists on disk (registry optional for scale).
    pub fn resolved_crew_model(&self) -> Option<String> {
        let path = format!(
            "{}/assets/models/{}/{}.glb",
            env!("CARGO_MANIFEST_DIR"),
            self.crew_model_id,
            self.crew_model_id
        );
        std::path::Path::new(&path)
            .is_file()
            .then(|| self.crew_model_id.clone())
    }
}

pub fn load_player_defaults(mut commands: Commands) {
    let path = format!("{}/data/player_defaults.json", env!("CARGO_MANIFEST_DIR"));
    commands.insert_resource(PlayerDefaults::load(path));
}
