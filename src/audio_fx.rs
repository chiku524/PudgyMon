//! Audio catalog: drop files under `assets/audio/` and they play automatically.
//! Missing clips fall back to Pitch tones (SFX) or silence (music / VO).

use std::{collections::HashMap, fs, path::Path, time::Duration};

use bevy::prelude::*;
use serde::Deserialize;

use crate::{
    flow::AppScreen,
    party::{PartyDirector, PartyPhase, PartySnapshot},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FxKind {
    Pickup,
    SortOk,
    SortBad,
    Ok,
    Bad,
    RoomClear,
    MeltdownFail,
    Knockback,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum VoKind {
    RoomStart,
    RoomClear,
    SortWrong,
    MeltdownFail,
    Elimination,
    Podium,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MusicBed {
    Title,
    Lobby,
    HrOrientation,
    CargoGantry,
    BreakerPanic,
    ShuttleMeltdown,
    Elimination,
    Podium,
}

#[derive(Resource, Debug, Default)]
pub struct AudioFxQueue {
    pub pending: Vec<FxKind>,
}

impl AudioFxQueue {
    pub fn push(&mut self, kind: FxKind) {
        self.pending.push(kind);
    }
}

#[derive(Resource, Debug, Default)]
pub struct VoQueue {
    pub pending: Vec<VoKind>,
}

impl VoQueue {
    pub fn push(&mut self, kind: VoKind) {
        self.pending.push(kind);
    }
}

#[derive(Resource, Debug, Default)]
pub struct MusicDirector {
    pub desired: Option<MusicBed>,
    pub playing: Option<MusicBed>,
}

#[derive(Component)]
struct MusicPlayer;

#[derive(Deserialize, Debug, Default)]
struct CatalogFile {
    #[serde(default)]
    sfx: HashMap<String, String>,
    #[serde(default)]
    music: HashMap<String, String>,
    #[serde(default)]
    vo: HashMap<String, String>,
}

#[derive(Resource, Debug, Default)]
pub struct AudioCatalog {
    sfx: HashMap<FxKind, Handle<AudioSource>>,
    music: HashMap<MusicBed, Handle<AudioSource>>,
    vo: HashMap<VoKind, Handle<AudioSource>>,
}

pub struct AudioFxPlugin;

impl Plugin for AudioFxPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<AudioFxQueue>()
            .init_resource::<VoQueue>()
            .init_resource::<MusicDirector>()
            .init_resource::<AudioCatalog>()
            .add_systems(Startup, load_audio_catalog)
            .add_systems(
                Update,
                (
                    drain_audio_fx,
                    drain_vo,
                    sync_desired_music_bed,
                    apply_music_bed,
                ),
            );
    }
}

fn load_audio_catalog(mut catalog: ResMut<AudioCatalog>, asset_server: Res<AssetServer>) {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let catalog_path = manifest.join("assets/audio/catalog.json");
    let Ok(raw) = fs::read_to_string(&catalog_path) else {
        warn!("audio catalog missing at {}", catalog_path.display());
        return;
    };
    let parsed: CatalogFile = match serde_json::from_str(&raw) {
        Ok(v) => v,
        Err(err) => {
            warn!("audio catalog parse failed: {err}");
            return;
        }
    };

    let audio_root = manifest.join("assets/audio");

    for (key, kind) in [
        ("pickup", FxKind::Pickup),
        ("sort_ok", FxKind::SortOk),
        ("sort_bad", FxKind::SortBad),
        ("ok", FxKind::Ok),
        ("bad", FxKind::Bad),
        ("room_clear", FxKind::RoomClear),
        ("meltdown_fail", FxKind::MeltdownFail),
        ("knockback", FxKind::Knockback),
    ] {
        if let Some(rel) = parsed.sfx.get(key) {
            if let Some(handle) = try_load_clip(&asset_server, &audio_root, rel) {
                catalog.sfx.insert(kind, handle);
            }
        }
    }

    for (key, kind) in [
        ("title", MusicBed::Title),
        ("lobby", MusicBed::Lobby),
        ("hr_orientation", MusicBed::HrOrientation),
        ("cargo_gantry", MusicBed::CargoGantry),
        ("breaker_panic", MusicBed::BreakerPanic),
        ("shuttle_meltdown", MusicBed::ShuttleMeltdown),
        ("elimination", MusicBed::Elimination),
        ("podium", MusicBed::Podium),
    ] {
        if let Some(rel) = parsed.music.get(key) {
            if let Some(handle) = try_load_clip(&asset_server, &audio_root, rel) {
                catalog.music.insert(kind, handle);
            }
        }
    }

    for (key, kind) in [
        ("room_start", VoKind::RoomStart),
        ("room_clear", VoKind::RoomClear),
        ("sort_wrong", VoKind::SortWrong),
        ("meltdown_fail", VoKind::MeltdownFail),
        ("elimination", VoKind::Elimination),
        ("podium", VoKind::Podium),
    ] {
        if let Some(rel) = parsed.vo.get(key) {
            if let Some(handle) = try_load_clip(&asset_server, &audio_root, rel) {
                catalog.vo.insert(kind, handle);
            }
        }
    }

    info!(
        "audio catalog ready — sfx {} · music {} · vo {}",
        catalog.sfx.len(),
        catalog.music.len(),
        catalog.vo.len()
    );
}

fn try_load_clip(
    asset_server: &AssetServer,
    audio_root: &Path,
    relative: &str,
) -> Option<Handle<AudioSource>> {
    let disk = audio_root.join(relative);
    if !disk.is_file() {
        return None;
    }
    // AssetPlugin file_path is `assets/`, so catalog paths are relative to that.
    Some(asset_server.load(format!("audio/{relative}")))
}

fn drain_audio_fx(
    mut queue: ResMut<AudioFxQueue>,
    catalog: Res<AudioCatalog>,
    mut pitches: ResMut<Assets<Pitch>>,
    settings: Option<Res<crate::settings::GameSettings>>,
    mut commands: Commands,
) {
    let master = settings.map(|s| s.master_volume).unwrap_or(1.0);
    for kind in queue.pending.drain(..) {
        if let Some(handle) = catalog.sfx.get(&kind) {
            let volume = sfx_volume(kind) * master;
            commands.spawn((
                AudioPlayer(handle.clone()),
                PlaybackSettings::DESPAWN.with_volume(bevy::audio::Volume::Linear(volume)),
            ));
            continue;
        }

        let (freq, ms, volume) = pitch_fallback(kind);
        let handle = pitches.add(Pitch::new(freq, Duration::from_millis(ms)));
        commands.spawn((
            AudioPlayer(handle),
            PlaybackSettings::DESPAWN
                .with_volume(bevy::audio::Volume::Linear(volume * master)),
        ));
    }
}

fn drain_vo(
    mut queue: ResMut<VoQueue>,
    catalog: Res<AudioCatalog>,
    settings: Option<Res<crate::settings::GameSettings>>,
    mut commands: Commands,
) {
    let master = settings.map(|s| s.master_volume).unwrap_or(1.0);
    for kind in queue.pending.drain(..) {
        let Some(handle) = catalog.vo.get(&kind) else {
            continue;
        };
        commands.spawn((
            AudioPlayer(handle.clone()),
            PlaybackSettings::DESPAWN
                .with_volume(bevy::audio::Volume::Linear(0.7 * master)),
        ));
    }
}

fn sync_desired_music_bed(
    screen: Res<State<AppScreen>>,
    director: Res<PartyDirector>,
    snapshots: Query<&PartySnapshot>,
    mut music: ResMut<MusicDirector>,
) {
    if *screen.get() == AppScreen::Title {
        music.desired = Some(MusicBed::Title);
        return;
    }

    let snap = snapshots.iter().next();
    let phase = snap.map(|s| s.phase).unwrap_or(director.phase);

    music.desired = Some(match phase {
        PartyPhase::Hub => MusicBed::Title,
        PartyPhase::Race => MusicBed::CargoGantry,
        PartyPhase::Vibe => MusicBed::HrOrientation,
        PartyPhase::Shooter => MusicBed::BreakerPanic,
        PartyPhase::Intermission => MusicBed::Lobby,
        PartyPhase::Results => MusicBed::Podium,
    });
}

fn apply_music_bed(
    mut music: ResMut<MusicDirector>,
    catalog: Res<AudioCatalog>,
    settings: Option<Res<crate::settings::GameSettings>>,
    players: Query<Entity, With<MusicPlayer>>,
    mut commands: Commands,
) {
    if music.desired == music.playing {
        return;
    }

    for entity in &players {
        commands.entity(entity).despawn();
    }

    let Some(bed) = music.desired else {
        music.playing = None;
        return;
    };

    let Some(handle) = catalog.music.get(&bed) else {
        music.playing = Some(bed);
        return;
    };

    let vol = 0.35 * settings.map(|s| s.master_volume).unwrap_or(1.0);
    commands.spawn((
        MusicPlayer,
        AudioPlayer(handle.clone()),
        PlaybackSettings::LOOP.with_volume(bevy::audio::Volume::Linear(vol)),
    ));
    music.playing = Some(bed);
}

fn sfx_volume(kind: FxKind) -> f32 {
    match kind {
        FxKind::Pickup => 0.4,
        FxKind::SortOk | FxKind::RoomClear => 0.45,
        FxKind::SortBad | FxKind::MeltdownFail | FxKind::Knockback => 0.5,
        FxKind::Ok => 0.3,
        FxKind::Bad => 0.35,
    }
}

fn pitch_fallback(kind: FxKind) -> (f32, u64, f32) {
    match kind {
        FxKind::Pickup => (660.0, 70, 0.35),
        FxKind::SortOk => (784.0, 120, 0.4),
        FxKind::SortBad => (120.0, 180, 0.45),
        FxKind::Ok => (523.0, 60, 0.3),
        FxKind::Bad => (180.0, 100, 0.35),
        FxKind::RoomClear => (880.0, 220, 0.4),
        FxKind::MeltdownFail => (90.0, 400, 0.5),
        FxKind::Knockback => (150.0, 90, 0.4),
    }
}
