//! Client → host party commands for Nest / rematch / leave.

use bevy::prelude::*;
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    hub::ModeQueued,
    maps::ActiveStageMaps,
    party::{
        is_party_authority, HubReady, PartyDirector, PartyPhase, PartyPlan, PartySpawn,
        PartySnapshot,
    },
    session_flow::NetworkBanner,
};

#[derive(Event, Serialize, Deserialize, Clone, Debug)]
pub enum PartyClientCommand {
    /// Start a mode from a Nest pad (or My Maps play).
    QueuePlan {
        plan: PartyPlan,
        race_map_id: String,
        vibe_map_id: String,
        shooter_map_id: String,
        koth_map_id: String,
    },
    /// Replay current/last plan.
    Rematch,
    /// Everyone back to Nest hub.
    ReturnToHub,
}

impl PartyClientCommand {
    pub fn queue_builtin(plan: PartyPlan) -> Self {
        Self::QueuePlan {
            plan,
            race_map_id: String::new(),
            vibe_map_id: String::new(),
            shooter_map_id: String::new(),
            koth_map_id: String::new(),
        }
    }

    pub fn queue_with_maps(plan: PartyPlan, active: &ActiveStageMaps) -> Self {
        Self::QueuePlan {
            plan,
            race_map_id: active
                .race
                .as_ref()
                .map(|m| m.id.clone())
                .unwrap_or_default(),
            vibe_map_id: active
                .vibe
                .as_ref()
                .map(|m| m.id.clone())
                .unwrap_or_default(),
            shooter_map_id: active
                .shooter
                .as_ref()
                .map(|m| m.id.clone())
                .unwrap_or_default(),
            koth_map_id: active
                .koth
                .as_ref()
                .map(|m| m.id.clone())
                .unwrap_or_default(),
        }
    }
}

pub struct PartyNetPlugin;

impl Plugin for PartyNetPlugin {
    fn build(&self, app: &mut App) {
        app.add_client_event::<PartyClientCommand>(Channel::Ordered)
            .add_observer(handle_party_client_command)
            .add_systems(
                Update,
                (
                    apply_party_snapshot_on_clients,
                    apply_maps_from_snapshot_on_clients,
                )
                    .run_if(not(is_party_authority)),
            );
    }
}

fn handle_party_client_command(
    request: On<FromClient<PartyClientCommand>>,
    mut director: ResMut<PartyDirector>,
    mut ready: ResMut<HubReady>,
    mut queued: ResMut<ModeQueued>,
    mut active: ResMut<ActiveStageMaps>,
    mut banner: ResMut<NetworkBanner>,
    spawn: Res<PartySpawn>,
    mut players: Query<&mut Transform, With<crate::player::NetworkPlayer>>,
) {
    let command = request.message.clone();
    match command {
        PartyClientCommand::QueuePlan {
            plan,
            race_map_id,
            vibe_map_id,
            shooter_map_id,
            koth_map_id,
        } => {
            if director.phase != PartyPhase::Hub {
                return;
            }
            *active = crate::maps::resolve_active_from_ids(
                &race_map_id,
                &vibe_map_id,
                &shooter_map_id,
                &koth_map_id,
            );
            queued.0 = Some(plan);
            banner.show(format!("Party queued: {}", plan.label()), 2.5);
        }
        PartyClientCommand::Rematch => {
            let plan = if director.plan == PartyPlan::Idle {
                PartyPlan::FullParty
            } else {
                director.plan
            };
            director.reset_party();
            ready.host_ready = false;
            queued.0 = Some(plan);
            banner.show("Rematch queued.", 3.0);
        }
        PartyClientCommand::ReturnToHub => {
            director.reset_party();
            ready.host_ready = false;
            queued.0 = None;
            for mut tf in &mut players {
                tf.translation = spawn.hub;
            }
            banner.show("Back in The Nest.", 3.5);
        }
    }
}

fn apply_party_snapshot_on_clients(
    snaps: Query<&PartySnapshot>,
    mut director: ResMut<PartyDirector>,
) {
    let Ok(snap) = snaps.single() else {
        return;
    };
    director.phase = snap.phase;
    director.phase_timer = snap.phase_timer;
    director.stage_index = snap.stage_index as usize;
    director.announcer = snap.announcer.clone();
    director.plan = snap.plan;
    for i in 0..8.min(director.match_points.len()) {
        director.match_points[i] = snap.match_points[i];
    }
}

fn apply_maps_from_snapshot_on_clients(
    snaps: Query<&PartySnapshot>,
    mut active: ResMut<ActiveStageMaps>,
    mut last: Local<(String, String, String, String)>,
) {
    let Ok(snap) = snaps.single() else {
        return;
    };
    let key = (
        snap.race_map_id.clone(),
        snap.vibe_map_id.clone(),
        snap.shooter_map_id.clone(),
        snap.koth_map_id.clone(),
    );
    if *last == key {
        return;
    }
    *last = key;
    *active = crate::maps::resolve_active_from_ids(
        &snap.race_map_id,
        &snap.vibe_map_id,
        &snap.shooter_map_id,
        &snap.koth_map_id,
    );
}
