//! Stage maps + Party Saga packs — bundled + user-authored JSON.

use std::collections::hash_map::DefaultHasher;
use std::fs::{self, File};
use std::hash::{Hash, Hasher};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

use crate::brand::APP_DATA_DIR;
use crate::core::ARENA_BOUNDS;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MapBlock {
    pub pos: [f32; 3],
    pub size: [f32; 3],
    /// Optional studio asset for decorative cover (greybox if missing).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub asset_id: Option<String>,
}

impl MapBlock {
    pub fn greybox(pos: [f32; 3], size: [f32; 3]) -> Self {
        Self {
            pos,
            size,
            asset_id: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RaceMap {
    pub schema_version: u32,
    pub id: String,
    pub label: String,
    pub mode: String,
    pub author: String,
    pub spawns: Vec<[f32; 3]>,
    pub gates: Vec<[f32; 3]>,
    pub blocks: Vec<MapBlock>,
}

impl Default for RaceMap {
    fn default() -> Self {
        Self {
            schema_version: 1,
            id: "untitled_race".into(),
            label: "Untitled Race".into(),
            mode: "race".into(),
            author: "local".into(),
            spawns: vec![[0.0, 1.0, 20.0]],
            gates: vec![
                [-12.0, 1.0, 4.0],
                [0.0, 1.0, -8.0],
                [12.0, 1.0, 4.0],
                [0.0, 1.0, 20.0],
            ],
            blocks: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VibeMap {
    pub schema_version: u32,
    pub id: String,
    pub label: String,
    pub mode: String,
    pub author: String,
    pub spawns: Vec<[f32; 3]>,
    pub orbs: Vec<[f32; 3]>,
    pub blocks: Vec<MapBlock>,
}

impl Default for VibeMap {
    fn default() -> Self {
        let mut orbs = Vec::new();
        for i in 0..12 {
            let angle = i as f32 * 0.7;
            orbs.push([angle.cos() * 16.0, 0.6, angle.sin() * 16.0]);
        }
        Self {
            schema_version: 1,
            id: "untitled_vibe".into(),
            label: "Untitled Vibe".into(),
            mode: "vibe".into(),
            author: "local".into(),
            spawns: vec![[0.0, 1.0, 0.0]],
            orbs,
            blocks: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShooterMap {
    pub schema_version: u32,
    pub id: String,
    pub label: String,
    pub mode: String,
    pub author: String,
    pub spawns: Vec<[f32; 3]>,
    pub cover: Vec<MapBlock>,
}

impl Default for ShooterMap {
    fn default() -> Self {
        Self {
            schema_version: 1,
            id: "untitled_shooter".into(),
            label: "Untitled Shooter".into(),
            mode: "shooter".into(),
            author: "local".into(),
            spawns: vec![[0.0, 1.0, 12.0], [8.0, 1.0, -4.0], [-8.0, 1.0, -4.0]],
            cover: vec![
                MapBlock::greybox([6.0, 0.5, 0.0], [2.5, 1.2, 2.5]),
                MapBlock::greybox([-6.0, 0.5, -6.0], [2.5, 1.2, 2.5]),
            ],
        }
    }
}

/// Full Party Saga UGC pack — three layouts, one project id.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartyPack {
    pub schema_version: u32,
    pub id: String,
    pub label: String,
    pub kind: String,
    pub author: String,
    pub race: RaceMap,
    pub vibe: VibeMap,
    pub shooter: ShooterMap,
}

impl Default for PartyPack {
    fn default() -> Self {
        let stamp = "pack";
        let mut race = RaceMap::default();
        race.id = format!("{stamp}_race");
        race.label = "Pack Race".into();
        let mut vibe = VibeMap::default();
        vibe.id = format!("{stamp}_vibe");
        vibe.label = "Pack Vibe".into();
        let mut shooter = ShooterMap::default();
        shooter.id = format!("{stamp}_shooter");
        shooter.label = "Pack Shooter".into();
        Self {
            schema_version: 2,
            id: "untitled_pack".into(),
            label: "Untitled Party Saga".into(),
            kind: "party_saga".into(),
            author: "local".into(),
            race,
            vibe,
            shooter,
        }
    }
}

impl PartyPack {
    pub fn validate(&self) -> Result<(), String> {
        if self.kind != "party_saga" {
            return Err(format!("unsupported kind '{}'", self.kind));
        }
        self.race.validate()?;
        self.vibe.validate()?;
        self.shooter.validate()?;
        Ok(())
    }

    pub fn clamp_to_arena(&mut self) {
        self.race.clamp_to_arena();
        self.vibe.clamp_to_arena();
        self.shooter.clamp_to_arena();
    }

    pub fn sync_ids_from_pack(&mut self) {
        let base = sanitize_id(&self.id);
        self.race.id = format!("{base}_race");
        self.race.label = format!("{} — Race", self.label);
        self.race.author = self.author.clone();
        self.vibe.id = format!("{base}_vibe");
        self.vibe.label = format!("{} — Vibe", self.label);
        self.vibe.author = self.author.clone();
        self.shooter.id = format!("{base}_shooter");
        self.shooter.label = format!("{} — Shooter", self.label);
        self.shooter.author = self.author.clone();
    }
}

fn clamp_xz(v: &mut [f32; 3]) {
    v[0] = v[0].clamp(-ARENA_BOUNDS, ARENA_BOUNDS);
    v[2] = v[2].clamp(-ARENA_BOUNDS, ARENA_BOUNDS);
}

fn validate_spawns(spawns: &[[f32; 3]], label: &str) -> Result<(), String> {
    if spawns.is_empty() {
        return Err(format!("{label}: need at least one spawn"));
    }
    for (i, s) in spawns.iter().enumerate() {
        if s[0].abs() > ARENA_BOUNDS || s[2].abs() > ARENA_BOUNDS {
            return Err(format!("{label}: spawn {i} outside arena"));
        }
    }
    Ok(())
}

impl RaceMap {
    pub fn validate(&self) -> Result<(), String> {
        if self.mode != "race" {
            return Err(format!("unsupported mode '{}'", self.mode));
        }
        validate_spawns(&self.spawns, "race")?;
        if self.gates.len() < 2 {
            return Err("race: need at least 2 gates".into());
        }
        for (i, g) in self.gates.iter().enumerate() {
            if g[0].abs() > ARENA_BOUNDS || g[2].abs() > ARENA_BOUNDS {
                return Err(format!("race: gate {i} outside arena"));
            }
        }
        Ok(())
    }

    pub fn clamp_to_arena(&mut self) {
        for s in &mut self.spawns {
            clamp_xz(s);
        }
        for g in &mut self.gates {
            clamp_xz(g);
        }
        for b in &mut self.blocks {
            clamp_xz(&mut b.pos);
        }
    }

    pub fn gate_positions(&self) -> Vec<Vec3> {
        self.gates
            .iter()
            .map(|g| Vec3::new(g[0], g[1], g[2]))
            .collect()
    }
}

impl VibeMap {
    pub fn validate(&self) -> Result<(), String> {
        if self.mode != "vibe" {
            return Err(format!("unsupported mode '{}'", self.mode));
        }
        validate_spawns(&self.spawns, "vibe")?;
        if self.orbs.len() < 3 {
            return Err("vibe: need at least 3 orbs".into());
        }
        Ok(())
    }

    pub fn clamp_to_arena(&mut self) {
        for s in &mut self.spawns {
            clamp_xz(s);
        }
        for o in &mut self.orbs {
            clamp_xz(o);
        }
        for b in &mut self.blocks {
            clamp_xz(&mut b.pos);
        }
    }
}

impl ShooterMap {
    pub fn validate(&self) -> Result<(), String> {
        if self.mode != "shooter" {
            return Err(format!("unsupported mode '{}'", self.mode));
        }
        validate_spawns(&self.spawns, "shooter")?;
        Ok(())
    }

    pub fn clamp_to_arena(&mut self) {
        for s in &mut self.spawns {
            clamp_xz(s);
        }
        for b in &mut self.cover {
            clamp_xz(&mut b.pos);
        }
    }
}

/// Active layouts for the next stage boots (None = built-in defaults).
#[derive(Resource, Debug, Clone, Default)]
pub struct ActiveStageMaps {
    pub race: Option<RaceMap>,
    pub vibe: Option<VibeMap>,
    pub shooter: Option<ShooterMap>,
}

impl ActiveStageMaps {
    pub fn clear(&mut self) {
        *self = Self::default();
    }

    pub fn apply_pack(&mut self, pack: &PartyPack) {
        self.race = Some(pack.race.clone());
        self.vibe = Some(pack.vibe.clone());
        self.shooter = Some(pack.shooter.clone());
    }
}

/// Resolve map ids from a party snapshot for joiners (empty id → built-in defaults).
pub fn resolve_active_from_ids(
    race_id: &str,
    vibe_id: &str,
    shooter_id: &str,
) -> ActiveStageMaps {
    let catalog = list_catalog();
    let mut active = ActiveStageMaps::default();
    if !race_id.is_empty() {
        active.race = catalog.iter().find_map(|e| match e {
            CatalogEntry::Race(m) if m.id == race_id => Some(m.clone()),
            CatalogEntry::Pack(p) if p.race.id == race_id || p.id == race_id => {
                Some(p.race.clone())
            }
            _ => None,
        });
    }
    if !vibe_id.is_empty() {
        active.vibe = catalog.iter().find_map(|e| match e {
            CatalogEntry::Vibe(m) if m.id == vibe_id => Some(m.clone()),
            CatalogEntry::Pack(p) if p.vibe.id == vibe_id || p.id == vibe_id => {
                Some(p.vibe.clone())
            }
            _ => None,
        });
    }
    if !shooter_id.is_empty() {
        active.shooter = catalog.iter().find_map(|e| match e {
            CatalogEntry::Shooter(m) if m.id == shooter_id => Some(m.clone()),
            CatalogEntry::Pack(p) if p.shooter.id == shooter_id || p.id == shooter_id => {
                Some(p.shooter.clone())
            }
            _ => None,
        });
    }
    // Full pack id on all three fields (My Maps Party Saga).
    if race_id == vibe_id && vibe_id == shooter_id && !race_id.is_empty() {
        if let Some(CatalogEntry::Pack(p)) = catalog.iter().find(|e| match e {
            CatalogEntry::Pack(p) => p.id == race_id,
            _ => false,
        }) {
            active.apply_pack(p);
        }
    }
    active
}

/// Back-compat alias used by older call sites.
#[derive(Resource, Debug, Clone, Default)]
pub struct ActiveRaceMap(pub Option<RaceMap>);

#[derive(Debug, Clone)]
pub enum CatalogEntry {
    Race(RaceMap),
    Vibe(VibeMap),
    Shooter(ShooterMap),
    Pack(PartyPack),
}

impl CatalogEntry {
    pub fn label(&self) -> &str {
        match self {
            Self::Race(m) => &m.label,
            Self::Vibe(m) => &m.label,
            Self::Shooter(m) => &m.label,
            Self::Pack(m) => &m.label,
        }
    }

    pub fn kind_label(&self) -> &'static str {
        match self {
            Self::Race(_) => "Race",
            Self::Vibe(_) => "Vibe",
            Self::Shooter(_) => "Shooter",
            Self::Pack(_) => "Party Saga",
        }
    }
}

pub struct MapsPlugin;

impl Plugin for MapsPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ActiveStageMaps>()
            .init_resource::<ActiveRaceMap>()
            .add_systems(Update, sync_active_race_alias);
    }
}

fn sync_active_race_alias(
    stages: Res<ActiveStageMaps>,
    mut race: ResMut<ActiveRaceMap>,
) {
    if stages.is_changed() {
        race.0 = stages.race.clone();
    }
}

pub fn user_maps_dir() -> PathBuf {
    if let Ok(base) = std::env::var("LOCALAPPDATA") {
        PathBuf::from(base).join(APP_DATA_DIR).join("maps")
    } else {
        PathBuf::from("maps")
    }
}

pub fn user_shares_dir() -> PathBuf {
    user_maps_dir().join("shares")
}

pub fn bundled_maps_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/maps")
}

pub fn sanitize_id(id: &str) -> String {
    let s: String = id
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '_' || c == '-' {
                c
            } else {
                '_'
            }
        })
        .collect();
    if s.is_empty() {
        "untitled".into()
    } else {
        s
    }
}

pub fn load_race_map_file(path: impl AsRef<Path>) -> Result<RaceMap, String> {
    let mut map: RaceMap = read_json(path)?;
    map.clamp_to_arena();
    map.validate()?;
    Ok(map)
}

pub fn save_race_map(map: &RaceMap) -> Result<PathBuf, String> {
    map.validate()?;
    write_json(user_maps_dir(), &sanitize_id(&map.id), map)
}

pub fn save_vibe_map(map: &VibeMap) -> Result<PathBuf, String> {
    map.validate()?;
    write_json(user_maps_dir(), &sanitize_id(&map.id), map)
}

pub fn save_shooter_map(map: &ShooterMap) -> Result<PathBuf, String> {
    map.validate()?;
    write_json(user_maps_dir(), &sanitize_id(&map.id), map)
}

pub fn save_party_pack(pack: &PartyPack) -> Result<PathBuf, String> {
    let mut pack = pack.clone();
    pack.sync_ids_from_pack();
    pack.clamp_to_arena();
    pack.validate()?;
    write_json(user_maps_dir(), &sanitize_id(&pack.id), &pack)
}

/// Export a portable share bundle + short code under maps/shares/.
pub fn export_share_code(pack: &PartyPack) -> Result<(String, PathBuf), String> {
    let mut pack = pack.clone();
    pack.sync_ids_from_pack();
    pack.clamp_to_arena();
    pack.validate()?;
    let json = serde_json::to_string(&pack).map_err(|e| e.to_string())?;
    let mut hasher = DefaultHasher::new();
    json.hash(&mut hasher);
    let code = format!(
        "PM-{:04X}-{}",
        (hasher.finish() & 0xFFFF) as u16,
        sanitize_id(&pack.id).chars().take(12).collect::<String>()
    );
    let dir = user_shares_dir();
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = dir.join(format!("{code}.json"));
    let mut file = File::create(&path).map_err(|e| e.to_string())?;
    let pretty = serde_json::to_string_pretty(&pack).map_err(|e| e.to_string())?;
    file.write_all(pretty.as_bytes())
        .map_err(|e| e.to_string())?;
    let meta = dir.join(format!("{code}.txt"));
    let _ = fs::write(
        meta,
        format!(
            "PudgyMon share code: {code}\nDrop the .json next to it into maps/ or import via My Maps.\n"
        ),
    );
    Ok((code, path))
}

pub fn import_share_code(code: &str) -> Result<PartyPack, String> {
    let code = code.trim();
    let path = user_shares_dir().join(format!("{code}.json"));
    if path.is_file() {
        return load_party_pack_file(path);
    }
    // Also scan shares for suffix match.
    if let Ok(entries) = fs::read_dir(user_shares_dir()) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();
            if name.contains(code) && name.ends_with(".json") {
                return load_party_pack_file(entry.path());
            }
        }
    }
    Err(format!("share code not found locally: {code}"))
}

pub fn load_party_pack_file(path: impl AsRef<Path>) -> Result<PartyPack, String> {
    let mut pack: PartyPack = read_json(path)?;
    pack.clamp_to_arena();
    pack.validate()?;
    Ok(pack)
}

pub fn list_catalog() -> Vec<CatalogEntry> {
    let mut out = Vec::new();
    for dir in [bundled_maps_dir(), user_maps_dir(), user_shares_dir()] {
        let Ok(entries) = fs::read_dir(&dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            push_catalog_path(&mut out, &path);
        }
    }
    out.sort_by(|a, b| a.label().cmp(b.label()));
    out
}

fn push_catalog_path(out: &mut Vec<CatalogEntry>, path: &Path) {
    let Ok(raw) = fs::read_to_string(path) else {
        return;
    };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&raw) else {
        return;
    };
    let kind = v
        .get("kind")
        .and_then(|k| k.as_str())
        .or_else(|| v.get("mode").and_then(|m| m.as_str()))
        .unwrap_or("race");
    let parsed = match kind {
        "party_saga" => load_party_pack_file(path).ok().map(CatalogEntry::Pack),
        "vibe" => serde_json::from_str::<VibeMap>(&raw).ok().and_then(|mut m| {
            m.clamp_to_arena();
            m.validate().ok()?;
            Some(CatalogEntry::Vibe(m))
        }),
        "shooter" => serde_json::from_str::<ShooterMap>(&raw).ok().and_then(|mut m| {
            m.clamp_to_arena();
            m.validate().ok()?;
            Some(CatalogEntry::Shooter(m))
        }),
        _ => load_race_map_file(path).ok().map(CatalogEntry::Race),
    };
    if let Some(entry) = parsed {
        let id = match &entry {
            CatalogEntry::Race(m) => m.id.clone(),
            CatalogEntry::Vibe(m) => m.id.clone(),
            CatalogEntry::Shooter(m) => m.id.clone(),
            CatalogEntry::Pack(m) => m.id.clone(),
        };
        if let Some(i) = out.iter().position(|e| match e {
            CatalogEntry::Race(m) => m.id == id,
            CatalogEntry::Vibe(m) => m.id == id,
            CatalogEntry::Shooter(m) => m.id == id,
            CatalogEntry::Pack(m) => m.id == id,
        }) {
            out[i] = entry;
        } else {
            out.push(entry);
        }
    }
}

/// Legacy helper — race-only list.
pub fn list_available_maps() -> Vec<RaceMap> {
    list_catalog()
        .into_iter()
        .filter_map(|e| match e {
            CatalogEntry::Race(m) => Some(m),
            _ => None,
        })
        .collect()
}

pub fn load_official_loop() -> RaceMap {
    let path = bundled_maps_dir().join("official_race_loop.json");
    load_race_map_file(path).unwrap_or_default()
}

fn read_json<T: for<'de> Deserialize<'de>>(path: impl AsRef<Path>) -> Result<T, String> {
    let mut file = File::open(path.as_ref()).map_err(|e| e.to_string())?;
    let mut buf = String::new();
    file.read_to_string(&mut buf).map_err(|e| e.to_string())?;
    serde_json::from_str(&buf).map_err(|e| e.to_string())
}

fn write_json<T: Serialize>(dir: PathBuf, slug: &str, value: &T) -> Result<PathBuf, String> {
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = dir.join(format!("{slug}.json"));
    let json = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    let mut file = File::create(&path).map_err(|e| e.to_string())?;
    file.write_all(json.as_bytes()).map_err(|e| e.to_string())?;
    Ok(path)
}

/// Decorative prop ids preferred in the map editor GLB palette.
pub const EDITOR_DECO_IDS: &[&str] = &[
    "prop_race_cone_01",
    "prop_race_banner_01",
    "prop_race_checkpoint_01",
    "env_race_ramp_01",
    "prop_vibe_orb_01",
    "prop_vibe_flower_01",
    "prop_vibe_crystal_01",
    "prop_vibe_mushroom_01",
    "prop_cover_block_01",
    "prop_target_star_01",
    "prop_blaster_toy_01",
    "env_nest_bench_01",
    "env_freight_crate_01",
    "prop_cartoon_vending_machine",
    "prop_alien_slot_machine",
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn official_map_loads_and_validates() {
        let map = load_official_loop();
        assert!(map.validate().is_ok());
        assert!(map.gates.len() >= 2);
    }

    #[test]
    fn rejects_too_few_gates() {
        let mut map = RaceMap::default();
        map.gates = vec![[0.0, 1.0, 0.0]];
        assert!(map.validate().is_err());
    }

    #[test]
    fn default_pack_validates() {
        let pack = PartyPack::default();
        assert!(pack.validate().is_ok());
    }

    #[test]
    fn vibe_needs_orbs() {
        let mut map = VibeMap::default();
        map.orbs.clear();
        assert!(map.validate().is_err());
    }
}
