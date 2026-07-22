//! Authoritative Party Saga phase machine.

use bevy::prelude::*;
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    challenges::ChallengeBoard,
    flow::AppScreen,
    hub::ModeQueued,
    party::{is_party_authority, PartyBot, PartyConfig, PartySpawn},
    player::{NetworkPlayer, PlayerName, PlayerOwner, HOST_OWNER_ID},
    season::SeasonLedger,
    world::GameplayEntity,
    Cli,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum PartyPhase {
    #[default]
    Hub,
    Race,
    Intermission,
    Vibe,
    Shooter,
    Results,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum StageKind {
    Race,
    Vibe,
    Shooter,
}

impl StageKind {
    pub fn label(self) -> &'static str {
        match self {
            Self::Race => "Race",
            Self::Vibe => "Vibe Collect",
            Self::Shooter => "Shooter",
        }
    }

    pub fn phase(self) -> PartyPhase {
        match self {
            Self::Race => PartyPhase::Race,
            Self::Vibe => PartyPhase::Vibe,
            Self::Shooter => PartyPhase::Shooter,
        }
    }
}

/// What the Nest launched — full Party Saga or a single mini-game.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum PartyPlan {
    #[default]
    Idle,
    FullParty,
    Single(StageKind),
}

impl PartyPlan {
    pub fn label(self) -> &'static str {
        match self {
            Self::Idle => "Idle",
            Self::FullParty => "Party Saga (all 3)",
            Self::Single(StageKind::Race) => "Race",
            Self::Single(StageKind::Vibe) => "Vibe Collect",
            Self::Single(StageKind::Shooter) => "Shooter",
        }
    }
}

#[derive(Resource, Debug, Clone)]
pub struct PartyDirector {
    pub phase: PartyPhase,
    pub phase_timer: f32,
    pub stage_index: usize,
    pub announcer: String,
    pub plan: PartyPlan,
    /// Per network slot party points this match.
    pub match_points: [u32; 16],
    pub finish_order: Vec<u32>,
}

impl Default for PartyDirector {
    fn default() -> Self {
        Self {
            phase: PartyPhase::Hub,
            phase_timer: 9999.0,
            stage_index: 0,
            announcer: "Welcome to The Nest — walk a pad and press E to play.".into(),
            plan: PartyPlan::Idle,
            match_points: [0; 16],
            finish_order: Vec::new(),
        }
    }
}

impl PartyDirector {
    pub fn reset_party(&mut self) {
        *self = Self::default();
    }

    pub fn add_points(&mut self, slot: u32, pts: u32) {
        if (slot as usize) < self.match_points.len() {
            self.match_points[slot as usize] =
                self.match_points[slot as usize].saturating_add(pts);
        }
    }

    pub fn current_stage(&self) -> Option<StageKind> {
        match self.phase {
            PartyPhase::Race => Some(StageKind::Race),
            PartyPhase::Vibe => Some(StageKind::Vibe),
            PartyPhase::Shooter => Some(StageKind::Shooter),
            _ => None,
        }
    }
}

#[derive(Component, Debug, Clone, Serialize, Deserialize, Default)]
pub struct PartySnapshot {
    pub phase: PartyPhase,
    pub phase_timer: f32,
    pub stage_index: u8,
    pub announcer: String,
    pub match_points: [u32; 8],
    pub plan: PartyPlan,
    /// Empty = built-in defaults. Otherwise catalog / bundled map id.
    pub race_map_id: String,
    pub vibe_map_id: String,
    pub shooter_map_id: String,
}

pub struct PartyPlugin;

impl Plugin for PartyPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<PartyDirector>()
            .init_resource::<PartyConfig>()
            .init_resource::<PartySpawn>()
            .init_resource::<HubReady>()
            .replicate::<PartySnapshot>()
            .replicate::<PartyBot>()
            .add_plugins(crate::party::PartyNetPlugin)
            .add_systems(Startup, spawn_party_snapshot_on_authority)
            .add_systems(
                Update,
                (
                    despawn_bots_in_hub,
                    spawn_bots_for_match,
                    tick_party_director,
                    sync_party_snapshot,
                )
                    .chain()
                    .run_if(is_party_authority)
                    .run_if(in_state(AppScreen::Playing))
                    .run_if(not(crate::hub::editor_is_active)),
            );
    }
}

#[derive(Resource, Debug, Default)]
pub struct HubReady {
    pub host_ready: bool,
}

fn spawn_party_snapshot_on_authority(mut commands: Commands, cli: Res<Cli>) {
    // Join clients must not spawn a local snapshot — it races the replicated one and
    // breaks `Query::single` in apply_party_snapshot_on_clients (phase stays Hub forever).
    if matches!(*cli, Cli::Join { .. }) {
        return;
    }
    commands.spawn((
        PartySnapshot::default(),
        Replicated,
        Name::new("PartySnapshot"),
    ));
}

fn despawn_bots_in_hub(
    director: Res<PartyDirector>,
    bots: Query<Entity, With<PartyBot>>,
    mut commands: Commands,
) {
    if director.phase != PartyPhase::Hub {
        return;
    }
    for entity in &bots {
        commands.entity(entity).despawn();
    }
}

fn spawn_bots_for_match(
    mut commands: Commands,
    director: Res<PartyDirector>,
    config: Res<PartyConfig>,
    spawn: Res<PartySpawn>,
    humans: Query<&NetworkPlayer>,
    bots: Query<&PartyBot>,
    defaults: Res<crate::data::PlayerDefaults>,
) {
    if matches!(director.phase, PartyPhase::Hub | PartyPhase::Results) {
        return;
    }
    let human_count = humans.iter().count();
    let bot_count = bots.iter().count();
    let want = config.bot_fill.saturating_sub(human_count);
    if bot_count >= want {
        return;
    }
    for i in bot_count..want {
        let slot = (human_count + i) as u32;
        let offset = Vec3::new((slot as f32) * 2.2, 0.0, 0.0);
        commands.spawn((
            GameplayEntity,
            Replicated,
            PartyBot { slot },
            NetworkPlayer { slot },
            PlayerName(format!("Bot{slot}")),
            crate::player::PlayerColor([0.5, 0.55, 0.65]),
            crate::player::PlayerVisualSpec {
                model_id: defaults.resolved_crew_model(),
                hat_slot: (slot % 8) as u8,
                accessories: Default::default(),
            },
            crate::player::Knockback::default(),
            PlayerOwner(HOST_OWNER_ID.wrapping_add(100 + slot as u64)),
            Transform::from_translation(spawn.hub + offset),
            Visibility::default(),
            Name::new(format!("PartyBot_{slot}")),
        ));
    }
}

fn tick_party_director(
    time: Res<Time>,
    mut director: ResMut<PartyDirector>,
    mut ready: ResMut<HubReady>,
    mut queued: ResMut<ModeQueued>,
    mut season: ResMut<SeasonLedger>,
    mut challenges: ResMut<ChallengeBoard>,
    cli: Res<Cli>,
) {
    // Hub: wait for a mode pad selection (or smoke HubReady → FullParty).
    if director.phase == PartyPhase::Hub {
        if ready.host_ready && queued.0.is_none() {
            queued.0 = Some(PartyPlan::FullParty);
            ready.host_ready = false;
        }
        // Join clients follow host snapshot; if somehow stuck, no auto-start.
        let _ = cli;

        if let Some(plan) = queued.0.take() {
            director.plan = plan;
            director.match_points = [0; 16];
            match plan {
                PartyPlan::Idle => {}
                PartyPlan::FullParty => {
                    begin_stage(
                        &mut director,
                        PartyPhase::Race,
                        45.0,
                        "Party Saga — Race first!",
                    );
                    director.stage_index = 0;
                }
                PartyPlan::Single(kind) => {
                    begin_stage(
                        &mut director,
                        kind.phase(),
                        45.0,
                        &format!("{} — go!", kind.label()),
                    );
                    director.stage_index = 0;
                }
            }
        }
        return;
    }

    director.phase_timer -= time.delta_secs();
    if director.phase_timer > 0.0 {
        return;
    }

    let plan = director.plan;
    match (director.phase, plan) {
        (PartyPhase::Race, PartyPlan::Single(StageKind::Race))
        | (PartyPhase::Vibe, PartyPlan::Single(StageKind::Vibe))
        | (PartyPhase::Shooter, PartyPlan::Single(StageKind::Shooter)) => {
            finish_match(&mut director, &mut season, &mut challenges);
        }
        (PartyPhase::Race, PartyPlan::FullParty) => {
            begin_stage(
                &mut director,
                PartyPhase::Intermission,
                3.0,
                "Vibe Collect up next…",
            );
            director.stage_index = 1;
        }
        (PartyPhase::Intermission, PartyPlan::FullParty) if director.stage_index == 1 => {
            begin_stage(
                &mut director,
                PartyPhase::Vibe,
                40.0,
                "Grab the vibes — yellow orbs!",
            );
        }
        (PartyPhase::Vibe, PartyPlan::FullParty) => {
            begin_stage(
                &mut director,
                PartyPhase::Intermission,
                3.0,
                "Shooter finale incoming…",
            );
            director.stage_index = 2;
        }
        (PartyPhase::Intermission, PartyPlan::FullParty) if director.stage_index == 2 => {
            begin_stage(
                &mut director,
                PartyPhase::Shooter,
                35.0,
                "Toy blasters — rack up KOs!",
            );
        }
        (PartyPhase::Shooter, PartyPlan::FullParty) => {
            finish_match(&mut director, &mut season, &mut challenges);
        }
        (PartyPhase::Results, _) => {
            director.reset_party();
            director.announcer = "Back in The Nest — pick another pad.".into();
        }
        (PartyPhase::Intermission, _) => {
            begin_stage(
                &mut director,
                PartyPhase::Hub,
                9999.0,
                "Back at the hub.",
            );
            director.plan = PartyPlan::Idle;
        }
        _ => {
            begin_stage(
                &mut director,
                PartyPhase::Hub,
                9999.0,
                "Back at the hub.",
            );
            director.plan = PartyPlan::Idle;
        }
    }
}

fn finish_match(
    director: &mut PartyDirector,
    season: &mut SeasonLedger,
    challenges: &mut ChallengeBoard,
) {
    let earned: u32 = director.match_points.iter().take(8).sum::<u32>().max(10) / 4;
    let local_best = director.match_points[0];
    let award = local_best.max(earned.min(50));
    season.add_points(award);
    challenges.bump("play_3", 1);
    begin_stage(
        director,
        PartyPhase::Results,
        6.0,
        "Match complete — season points filed.",
    );
    director.announcer = format!(
        "Results! You scored {local_best} party pts · season +{award}"
    );
}

fn begin_stage(director: &mut PartyDirector, phase: PartyPhase, secs: f32, line: &str) {
    director.phase = phase;
    director.phase_timer = secs;
    director.announcer = line.into();
    director.finish_order.clear();
}

fn sync_party_snapshot(
    director: Res<PartyDirector>,
    active: Res<crate::maps::ActiveStageMaps>,
    mut snaps: Query<&mut PartySnapshot>,
) {
    let Ok(mut snap) = snaps.single_mut() else {
        return;
    };
    snap.phase = director.phase;
    snap.phase_timer = director.phase_timer;
    snap.stage_index = director.stage_index as u8;
    snap.announcer = director.announcer.clone();
    snap.plan = director.plan;
    snap.race_map_id = active
        .race
        .as_ref()
        .map(|m| m.id.clone())
        .unwrap_or_default();
    snap.vibe_map_id = active
        .vibe
        .as_ref()
        .map(|m| m.id.clone())
        .unwrap_or_default();
    snap.shooter_map_id = active
        .shooter
        .as_ref()
        .map(|m| m.id.clone())
        .unwrap_or_default();
    for i in 0..8 {
        snap.match_points[i] = director.match_points[i];
    }
}
