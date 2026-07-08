use bevy::prelude::*;
use bevy_replicon::prelude::*;

use crate::{
    announcer::AnnouncerQueue,
    economy::PracticeLedger,
    interaction::InteractPrompt,
    rooms::RoomRuntime,
    tournament::{TournamentDirector, TournamentPhase, TournamentSnapshot},
};

pub struct UiPlugin;

impl Plugin for UiPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, spawn_hud_root)
            .add_systems(Update, update_hud_text);
    }
}

#[derive(Component)]
struct HudRoot;

#[derive(Component)]
struct HudStatusText;

#[derive(Component)]
struct HudPromptText;

#[derive(Component)]
struct HudTournamentText;

fn spawn_hud_root(mut commands: Commands) {
    commands.spawn((
        HudRoot,
        Node {
            width: Val::Percent(100.0),
            height: Val::Percent(100.0),
            flex_direction: FlexDirection::Column,
            padding: UiRect::all(Val::Px(16.0)),
            row_gap: Val::Px(8.0),
            ..Default::default()
        },
        children![
            (
                HudStatusText,
                Text::new("ShipHappens — Vault Break"),
                TextFont {
                    font_size: FontSize::Px(22.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.9, 0.95, 1.0)),
            ),
            (
                HudTournamentText,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(18.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.75, 0.95, 0.75)),
            ),
            (
                HudPromptText,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(18.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.95, 0.85, 0.35)),
            ),
        ],
    ));
}

fn update_hud_text(
    cli: Res<crate::Cli>,
    prompt: Res<InteractPrompt>,
    director: Res<TournamentDirector>,
    announcer: Res<AnnouncerQueue>,
    ledger: Res<PracticeLedger>,
    room_runtime: Res<RoomRuntime>,
    snapshots: Query<&TournamentSnapshot>,
    server_state: Res<State<ServerState>>,
    client_state: Res<State<ClientState>>,
    mut status: Query<
        &mut Text,
        (
            With<HudStatusText>,
            Without<HudPromptText>,
            Without<HudTournamentText>,
        ),
    >,
    mut tournament: Query<
        &mut Text,
        (
            With<HudTournamentText>,
            Without<HudStatusText>,
            Without<HudPromptText>,
        ),
    >,
    mut prompts: Query<
        &mut Text,
        (
            With<HudPromptText>,
            Without<HudStatusText>,
            Without<HudTournamentText>,
        ),
    >,
) {
    let mode = match cli.as_ref() {
        crate::Cli::Local => "local",
        crate::Cli::Host { .. } => "host",
        crate::Cli::Join { .. } => "join",
    };

    if let Ok(mut text) = status.single_mut() {
        **text = format!(
            "ShipHappens Vault Break — {mode} | server: {:?} | client: {:?}",
            server_state.get(),
            client_state.get(),
        );
    }

    let snap = snapshots.iter().next();
    let phase = snap.map(|s| s.phase).unwrap_or(director.phase);
    let room_id = snap.map(|s| s.room).unwrap_or(director.room);
    let progress = snap.map(|s| s.room_progress).unwrap_or(0);

    if let Ok(mut text) = tournament.single_mut() {
        **text = format!(
            "Phase: {:?} | Room: {} | Alive: {} | Progress: {}% | Meltdown: {}% | VC: {}\nAnnouncer: {}",
            phase,
            room_id.label(),
            director.alive_count(),
            progress,
            room_runtime.meltdown_percent(),
            ledger.balance_vc,
            announcer.last_bark,
        );
    }

    if let Ok(mut text) = prompts.single_mut() {
        let action = if prompt.message.is_empty() {
            prompt.last_action.clone()
        } else {
            format!("{}\n{}", prompt.message, prompt.last_action)
        };
        if director.phase == TournamentPhase::Complete {
            **text = format!(
                "{action}\nPodium: {:?} | last payouts: {:?}",
                director.placements, ledger.last_payouts_vc
            );
        } else {
            **text = action;
        }
    }
}
