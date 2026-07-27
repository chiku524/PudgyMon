use std::{fs, path::Path};

use bevy::prelude::*;
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct StudioAssetEntry {
    pub asset_id: String,
    /// Intended world-space height in meters (authoring guide + default uniform scale).
    #[serde(default = "default_target_height")]
    pub target_height: f32,
    /// Optional intended width for floor pads / mats (XZ scale when set).
    #[serde(default)]
    pub target_width: Option<f32>,
    /// Explicit uniform scale override. When set, wins over height/width heuristics.
    #[serde(default)]
    pub uniform_scale: Option<f32>,
    /// Free-form notes for artists (placement hints, pivot, etc.).
    #[serde(default)]
    pub notes: Option<String>,
}

fn default_target_height() -> f32 {
    1.0
}

#[derive(Debug, Deserialize)]
struct StudioRegistryFile {
    import_root: String,
    assets: Vec<StudioAssetEntry>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StudioRegistryError {
    Io(String),
    Parse(String),
}

impl std::fmt::Display for StudioRegistryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(msg) => write!(f, "failed to read studio registry: {msg}"),
            Self::Parse(msg) => write!(f, "failed to parse studio registry: {msg}"),
        }
    }
}

impl std::error::Error for StudioRegistryError {}

#[derive(Resource, Debug, Clone)]
pub struct StudioRegistry {
    pub import_root: String,
    pub assets: Vec<StudioAssetEntry>,
}

impl StudioRegistry {
    pub fn load(path: impl AsRef<Path>) -> Result<Self, StudioRegistryError> {
        let raw = fs::read_to_string(path.as_ref())
            .map_err(|err| StudioRegistryError::Io(err.to_string()))?;
        let mut parsed: StudioRegistryFile = serde_json::from_str(&raw)
            .map_err(|err| StudioRegistryError::Parse(err.to_string()))?;
        // `_`-prefixed ids (e.g. `_TEMPLATE`) are authoring stencils for the
        // import scripts — never real assets, so drop them at load time.
        parsed.assets.retain(|entry| !entry.asset_id.starts_with('_'));
        Ok(Self {
            import_root: parsed.import_root,
            assets: parsed.assets,
        })
    }

    pub fn entry(&self, asset_id: &str) -> Option<&StudioAssetEntry> {
        self.assets.iter().find(|entry| entry.asset_id == asset_id)
    }

    pub fn target_height(&self, asset_id: &str) -> Option<f32> {
        self.entry(asset_id).map(|entry| entry.target_height)
    }

    pub fn target_width(&self, asset_id: &str) -> Option<f32> {
        self.entry(asset_id).and_then(|entry| entry.target_width)
    }

    /// Scale applied at spawn time.
    ///
    /// Priority: `uniform_scale` → width-based XZ for floor pads → `target_height` as
    /// uniform scale (legacy Tripo import convention until bounds-based scaling lands).
    pub fn spawn_scale(&self, asset_id: &str) -> Vec3 {
        let Some(entry) = self.entry(asset_id) else {
            return Vec3::ONE;
        };

        if let Some(scale) = entry.uniform_scale {
            return Vec3::splat(scale.max(0.01));
        }

        if let Some(width) = entry.target_width {
            let w = width.max(0.01);
            return Vec3::new(w, 1.0, w);
        }

        Vec3::splat(entry.target_height.max(0.01))
    }

    pub fn glb_asset_path(&self, asset_id: &str) -> String {
        format!("models/{asset_id}/{asset_id}.glb")
    }

    pub fn glb_disk_path(&self, asset_id: &str, assets_root: impl AsRef<Path>) -> std::path::PathBuf {
        assets_root.as_ref().join(self.glb_asset_path(asset_id))
    }

    pub fn contains(&self, asset_id: &str) -> bool {
        self.entry(asset_id).is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loads_studio_registry() {
        let registry =
            StudioRegistry::load("assets/studio_registry.json").expect("registry loads");
        assert!(registry.target_height("env_nest_egg_01").is_some());
        // Authoring stencils must be filtered out at load time.
        assert!(!registry.contains("_TEMPLATE"));
    }

    #[test]
    fn floor_pad_uses_target_width() {
        let registry = StudioRegistry {
            import_root: String::new(),
            assets: vec![StudioAssetEntry {
                asset_id: "test_pad".into(),
                target_height: 1.0,
                target_width: Some(2.0),
                uniform_scale: None,
                notes: None,
            }],
        };
        let scale = registry.spawn_scale("test_pad");
        assert!((scale.x - 2.0).abs() < f32::EPSILON);
        assert!((scale.z - 2.0).abs() < f32::EPSILON);
    }

    #[test]
    fn every_registry_asset_has_glb_on_disk() {
        let registry =
            StudioRegistry::load("assets/studio_registry.json").expect("registry loads");
        let mut missing = Vec::new();
        for entry in &registry.assets {
            let path = registry.glb_disk_path(&entry.asset_id, "assets");
            if !path.exists() {
                missing.push(entry.asset_id.clone());
            }
        }
        assert!(
            missing.is_empty(),
            "registry assets missing GLB files: {missing:?}"
        );
    }
}
