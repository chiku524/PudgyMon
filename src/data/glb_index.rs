//! Cached on-disk Studio GLB presence — avoids per-frame `Path::is_file` hitches.

use std::{
    collections::HashSet,
    path::{Path, PathBuf},
    sync::OnceLock,
};

fn models_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("assets/models")
}

fn build_index() -> HashSet<String> {
    let mut present = HashSet::new();
    let root = models_root();
    let Ok(entries) = std::fs::read_dir(&root) else {
        return present;
    };
    for entry in entries.flatten() {
        if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        let name = entry.file_name();
        let Some(id) = name.to_str() else {
            continue;
        };
        let glb = entry.path().join(format!("{id}.glb"));
        if glb.is_file() {
            present.insert(id.to_string());
        }
    }
    present
}

fn index() -> &'static HashSet<String> {
    static INDEX: OnceLock<HashSet<String>> = OnceLock::new();
    INDEX.get_or_init(build_index)
}

/// True when `assets/models/{id}/{id}.glb` existed at process start.
pub fn studio_glb_on_disk(asset_id: &str) -> bool {
    let id = asset_id.trim();
    if id.is_empty() {
        return false;
    }
    index().contains(id)
}
