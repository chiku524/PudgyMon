//! Playable character roster for Nest menu selection / comparison.

use std::{fs, path::Path};

use bevy::prelude::*;
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct CharacterEntry {
    pub id: String,
    pub label: String,
    #[serde(default)]
    pub blurb: String,
}

#[derive(Resource, Debug, Clone)]
pub struct CharacterRoster {
    pub characters: Vec<CharacterEntry>,
}

impl Default for CharacterRoster {
    fn default() -> Self {
        Self {
            characters: vec![CharacterEntry {
                id: "char_pudgy_base_01".into(),
                label: "Soft Cartoon".into(),
                blurb: "Shared Pudgy base".into(),
            }],
        }
    }
}

#[derive(Deserialize)]
struct RosterFile {
    characters: Vec<CharacterEntry>,
}

impl CharacterRoster {
    pub fn load(path: impl AsRef<Path>) -> Self {
        let Ok(raw) = fs::read_to_string(path.as_ref()) else {
            return Self::default();
        };
        match serde_json::from_str::<RosterFile>(&raw) {
            Ok(file) => Self {
                characters: file.characters,
            },
            Err(err) => {
                warn!("characters/roster.json parse failed: {err}");
                Self::default()
            }
        }
    }

    /// Roster entries whose GLB exists on disk.
    pub fn available(&self) -> Vec<&CharacterEntry> {
        self.characters
            .iter()
            .filter(|c| character_glb_exists(&c.id))
            .collect()
    }

    pub fn label_for(&self, id: &str) -> String {
        self.characters
            .iter()
            .find(|c| c.id == id)
            .map(|c| c.label.clone())
            .unwrap_or_else(|| id.to_string())
    }
}

pub fn character_glb_exists(model_id: &str) -> bool {
    let path = format!(
        "{}/assets/models/{model_id}/{model_id}.glb",
        env!("CARGO_MANIFEST_DIR")
    );
    Path::new(&path).is_file()
}

pub fn load_character_roster(mut commands: Commands) {
    let path = format!(
        "{}/data/characters/roster.json",
        env!("CARGO_MANIFEST_DIR")
    );
    commands.insert_resource(CharacterRoster::load(path));
}
