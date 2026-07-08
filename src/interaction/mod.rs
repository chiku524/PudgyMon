use bevy::ecs::entity::MapEntities;
use bevy::prelude::*;
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    core::{CRANE_JOB_ID, INTERACT_RADIUS, POWER_HOUR_JOB_ID},
    jobs::{apply_job_action, BreakerResult, JobActionResult, JobBoard, JobSystem, SmokeJobFlags},
    player::{Leaseholder, LocalPlayer},
    rooms::RoomRuntime,
    scoring::{PlayerScoreId, ScoreAction, ScoringService},
    tournament::{TournamentConfig, TournamentDirector, TournamentPhase},
    Cli,
};

pub struct InteractionPlugin;

impl Plugin for InteractionPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<InteractPrompt>()
            .add_mapped_client_event::<InteractRequest>(Channel::Ordered)
            .add_observer(handle_interact_request)
            .add_systems(Update, (show_interact_prompt, handle_local_interact));
    }
}

#[derive(Component, Debug, Clone, Copy)]
pub struct Interactable {
    pub kind: StationKind,
    pub radius: f32,
}

impl Interactable {
    pub fn crane() -> Self {
        Self {
            kind: StationKind::CraneConsole,
            radius: INTERACT_RADIUS,
        }
    }

    pub fn breaker(index: u8) -> Self {
        Self {
            kind: StationKind::PowerHourBreaker { index },
            radius: INTERACT_RADIUS,
        }
    }

    pub fn vault_objective() -> Self {
        Self {
            kind: StationKind::VaultObjective,
            radius: INTERACT_RADIUS,
        }
    }

    pub fn sort_chute(chute: u8) -> Self {
        Self {
            kind: StationKind::SortChute { chute },
            radius: INTERACT_RADIUS,
        }
    }

    pub fn coolant_valve(index: u8) -> Self {
        Self {
            kind: StationKind::CoolantValve { index },
            radius: INTERACT_RADIUS,
        }
    }

    pub fn meltdown_door(index: u8) -> Self {
        Self {
            kind: StationKind::MeltdownDoor { index },
            radius: INTERACT_RADIUS,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StationKind {
    CraneConsole,
    PowerHourBreaker { index: u8 },
    VaultObjective,
    SortChute { chute: u8 },
    CoolantValve { index: u8 },
    MeltdownDoor { index: u8 },
}

#[derive(Event, Serialize, Deserialize, Clone, Copy, Debug, MapEntities)]
pub struct InteractRequest {
    #[entities]
    pub station: Entity,
}

#[derive(Resource, Default)]
pub struct InteractPrompt {
    pub message: String,
    pub last_action: String,
}

fn handle_local_interact(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut commands: Commands,
    cli: Res<Cli>,
    config: Res<TournamentConfig>,
    director: Res<TournamentDirector>,
    mut room: ResMut<RoomRuntime>,
    mut scoring: ResMut<ScoringService>,
    local_player: Query<(&Transform, Has<Leaseholder>), With<LocalPlayer>>,
    stations: Query<(Entity, &Transform, &Interactable)>,
    mut jobs: Option<ResMut<JobSystem>>,
    mut boards: Query<(&mut JobBoard, &mut SmokeJobFlags)>,
    mut prompt: ResMut<InteractPrompt>,
) {
    if !keyboard.just_pressed(KeyCode::KeyF) {
        return;
    }

    let Ok((player_transform, is_leaseholder)) = local_player.single() else {
        return;
    };

    if is_leaseholder {
        prompt.last_action = "Leaseholder: direct only — use pings.".into();
        return;
    }

    let Some((station_entity, _, interactable)) =
        nearest_interactable(player_transform.translation, &stations)
    else {
        return;
    };

    let tournament_active = matches!(
        director.phase,
        TournamentPhase::RoomActive | TournamentPhase::Finale
    );

    if tournament_active {
        let player = PlayerScoreId(config.human_slot.0 * 10);
        let slot = &config.human_slot;
        match interactable.kind {
            StationKind::SortChute { chute } => {
                let action = if chute == room.sort_target {
                    room.sort_target = (room.sort_target + 1) % 4;
                    ScoreAction::CorrectSort
                } else {
                    ScoreAction::IncorrectSort
                };
                room.player_action(scoring.as_mut(), player, slot, action);
                prompt.last_action = format!(
                    "Sorted! Vault progress: {}% (next: {})",
                    room.progress_percent(),
                    room.sort_target_label()
                );
                return;
            }
            StationKind::VaultObjective => {
                let action = if director.room == crate::tournament::types::RoomId::ShuttleMeltdown {
                    ScoreAction::EscapeCrate
                } else {
                    ScoreAction::CrateDelivered
                };
                room.player_action(scoring.as_mut(), player, slot, action);
                prompt.last_action = format!("Vault progress: {}%", room.progress_percent());
                return;
            }
            StationKind::CoolantValve { .. } => {
                room.player_action(scoring.as_mut(), player, slot, ScoreAction::CoolantValve);
                prompt.last_action = format!(
                    "Coolant valve turned — meltdown {}%",
                    room.progress.meltdown_meter as u32
                );
                return;
            }
            StationKind::MeltdownDoor { .. } => {
                room.player_action(scoring.as_mut(), player, slot, ScoreAction::DoorSealed);
                prompt.last_action = format!("Door sealed — progress {}%", room.progress_percent());
                return;
            }
            StationKind::CraneConsole => {
                room.player_action(scoring.as_mut(), player, slot, ScoreAction::CrateDelivered);
                if let Some(jobs) = jobs.as_deref_mut() {
                    let msg = apply_station_interact(jobs, interactable.kind);
                    apply_job_action(jobs, &mut boards);
                    prompt.last_action = format!("Gantry: {msg} | {}%", room.progress_percent());
                } else {
                    prompt.last_action = format!("Gantry delivery — {}%", room.progress_percent());
                }
                return;
            }
            StationKind::PowerHourBreaker { index } => {
                if let Some(jobs) = jobs.as_deref_mut() {
                    let msg = apply_station_interact(jobs, interactable.kind);
                    apply_job_action(jobs, &mut boards);
                    let action = if msg.contains("zapped") {
                        ScoreAction::BreakerWrong
                    } else {
                        ScoreAction::BreakerCorrect
                    };
                    room.player_action(scoring.as_mut(), player, slot, action);
                    prompt.last_action = format!("Breaker {index}: {msg}");
                } else {
                    room.player_action(scoring.as_mut(), player, slot, ScoreAction::BreakerCorrect);
                    prompt.last_action = format!("Breaker {index} flipped");
                }
                return;
            }
        }
    }

    if cli.is_online() {
        prompt.last_action = format!("Sent interact to `{station_entity:?}`");
        commands.client_trigger(InteractRequest {
            station: station_entity,
        });
    } else if let Some(jobs) = jobs.as_deref_mut() {
        let result = apply_station_interact(jobs, interactable.kind);
        prompt.last_action = format_result(interactable.kind, result);
        apply_job_action(jobs, &mut boards);
    }
}

fn handle_interact_request(
    request: On<FromClient<InteractRequest>>,
    mut jobs: Option<ResMut<JobSystem>>,
    owners: Query<&crate::network::OwnedPlayer>,
    players: Query<&Transform, With<crate::player::NetworkPlayer>>,
    stations: Query<(Entity, &Transform, &Interactable)>,
    mut boards: Query<(&mut JobBoard, &mut SmokeJobFlags)>,
) {
    let Some(client_entity) = request.client_id.entity() else {
        return;
    };

    let Ok(owned) = owners.get(client_entity) else {
        warn!("interact from unknown client `{client_entity}`");
        return;
    };

    let Ok(player_transform) = players.get(owned.0) else {
        return;
    };

    let Ok((_, station_transform, interactable)) = stations.get(request.station) else {
        return;
    };

    if player_transform
        .translation
        .distance(station_transform.translation)
        > interactable.radius
    {
        return;
    }

    let Some(jobs) = jobs.as_deref_mut() else {
        return;
    };

    let result = apply_station_interact(jobs, interactable.kind);
    apply_job_action(jobs, &mut boards);
    info!(
        "client `{client_entity}` interacted with {:?}: {}",
        interactable.kind,
        format_result(interactable.kind, result)
    );
}

fn apply_station_interact(jobs: &mut JobSystem, kind: StationKind) -> String {
    match kind {
        StationKind::CraneConsole => match jobs.try_crane_interact() {
            JobActionResult::Progressed => "crane advanced".into(),
            JobActionResult::Completed => "crane complete".into(),
            JobActionResult::AlreadyComplete => "crane already done".into(),
            JobActionResult::WrongSequence => "crane wrong sequence".into(),
            JobActionResult::NotActive => "crane inactive".into(),
            JobActionResult::Ignored => "crane ignored".into(),
        },
        StationKind::PowerHourBreaker { index } => match jobs.try_power_hour_interact(index) {
            BreakerResult::Flipped => format!("breaker {index} flipped"),
            BreakerResult::Completed => "power hour complete".into(),
            BreakerResult::WrongBreaker => format!("breaker {index} zapped (wrong order)"),
        },
        StationKind::VaultObjective => "vault objective advanced".into(),
        StationKind::SortChute { .. } => "sort chute".into(),
        StationKind::CoolantValve { index } => format!("coolant valve {index}"),
        StationKind::MeltdownDoor { index } => format!("sealed door {index}"),
    }
}

fn format_result(kind: StationKind, message: String) -> String {
    match kind {
        StationKind::CraneConsole => format!("Crane: {message}"),
        StationKind::PowerHourBreaker { index } => format!("Breaker {index}: {message}"),
        StationKind::VaultObjective => format!("Vault: {message}"),
        StationKind::SortChute { chute } => format!("Chute {chute}: {message}"),
        StationKind::CoolantValve { index } => format!("Coolant {index}: {message}"),
        StationKind::MeltdownDoor { index } => format!("Door {index}: {message}"),
    }
}

fn show_interact_prompt(
    director: Res<TournamentDirector>,
    room: Res<RoomRuntime>,
    local_player: Query<&Transform, With<LocalPlayer>>,
    stations: Query<(Entity, &Transform, &Interactable)>,
    jobs: Option<Res<JobSystem>>,
    boards: Query<&JobBoard>,
    mut prompt: ResMut<InteractPrompt>,
) {
    let Ok(player_transform) = local_player.single() else {
        prompt.message.clear();
        return;
    };

    let Some((_, _, interactable)) =
        nearest_interactable(player_transform.translation, &stations)
    else {
        prompt.message.clear();
        return;
    };

    prompt.message = prompt_for_station(
        interactable,
        jobs.as_deref(),
        boards.iter().next(),
        director.as_ref(),
        room.as_ref(),
    );
}

fn prompt_for_station(
    interactable: &Interactable,
    jobs: Option<&JobSystem>,
    board: Option<&JobBoard>,
    director: &TournamentDirector,
    room: &RoomRuntime,
) -> String {
    match interactable.kind {
        StationKind::CraneConsole => {
            let (current, target) = jobs
                .map(|jobs| jobs.progress_for(CRANE_JOB_ID))
                .unwrap_or((0, 3));
            if jobs.is_some_and(|jobs| jobs.is_complete(CRANE_JOB_ID))
                || board.is_some_and(|board| {
                    board
                        .states
                        .get(CRANE_JOB_ID)
                        .is_some_and(|state| state.complete)
                })
            {
                "Crane of Regret — complete".into()
            } else if jobs.is_some_and(|jobs| jobs.is_active(CRANE_JOB_ID)) {
                format!("Press F — Crane of Regret ({current}/{target})")
            } else {
                "Press F — Start Crane of Regret".into()
            }
        }
        StationKind::PowerHourBreaker { index } => {
            if jobs.is_some_and(|jobs| jobs.is_complete(POWER_HOUR_JOB_ID)) {
                return format!("Breaker {} — power restored", index + 1);
            }
            if jobs.is_some_and(|jobs| !jobs.is_active(POWER_HOUR_JOB_ID)) {
                return format!("Press F — Start Power Hour (breaker {})", index + 1);
            }
            let step = jobs.map(|jobs| jobs.power_hour_step()).unwrap_or(0);
            format!(
                "Press F — Flip breaker {} (step {})",
                index + 1,
                step + 1
            )
        }
        StationKind::VaultObjective => {
            if director.room == crate::tournament::types::RoomId::ShuttleMeltdown {
                "Press F — load escape crate".into()
            } else {
                "Press F — deliver crate".into()
            }
        }
        StationKind::SortChute { chute } => {
            format!(
                "Press F — sort into chute {} (want: {})",
                chute + 1,
                room.sort_target_label()
            )
        }
        StationKind::CoolantValve { index } => {
            format!("Press F — turn coolant valve {}", index + 1)
        }
        StationKind::MeltdownDoor { index } => {
            format!("Press F — seal door {}", index + 1)
        }
    }
}

pub fn nearest_interactable<'a>(
    player: Vec3,
    stations: &'a Query<(Entity, &Transform, &Interactable)>,
) -> Option<(Entity, &'a Transform, &'a Interactable)> {
    stations
        .iter()
        .filter(|(_, transform, interactable)| {
            player.distance(transform.translation) <= interactable.radius
        })
        .min_by(|(_, left, _), (_, right, _)| {
            left.translation
                .distance(player)
                .partial_cmp(&right.translation.distance(player))
                .unwrap_or(std::cmp::Ordering::Equal)
        })
        .map(|(entity, transform, interactable)| (entity, transform, interactable))
}

/// Headless smoke helper — interact with nearest station without input.
pub fn auto_interact_nearest(
    player_pos: Vec3,
    stations: &Query<(Entity, &Transform, &Interactable)>,
    jobs: &mut JobSystem,
    boards: &mut Query<'_, '_, (&mut JobBoard, &mut SmokeJobFlags)>,
) -> bool {
    let Some((_, _, interactable)) = nearest_interactable(player_pos, stations) else {
        return false;
    };
    apply_station_interact(jobs, interactable.kind);
    apply_job_action(jobs, boards);
    true
}
