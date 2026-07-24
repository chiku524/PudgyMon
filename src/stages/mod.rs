//! Greybox mini-game stages: Race, Vibe Collect, Shooter.

mod race;
mod shooter;
mod vibe;

use bevy::prelude::*;
use bevy_replicon::prelude::*;

use crate::flow::AppScreen;
use crate::party::{is_party_authority, PartyDirector, PartyPhase};

pub struct StagesPlugin;

impl Plugin for StagesPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<race::RaceState>()
            .init_resource::<vibe::VibeState>()
            .init_resource::<shooter::ShooterState>()
            .init_resource::<StageBoot>()
            .add_client_event::<shooter::ShootRequest>(Channel::Unordered)
            .add_observer(shooter::handle_shoot_request)
            .add_observer(shooter::init_projectile_visuals)
            .replicate::<shooter::Projectile>()
            .add_systems(
                Update,
                (
                    // All peers boot local stage greybox when phase changes.
                    boot_stages
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(not(crate::hub::editor_is_active)),
                    // Scoring / bots / projectiles — host authority.
                    race::tick_race
                        .run_if(is_party_authority)
                        .run_if(in_phase(PartyPhase::Race))
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(not(crate::hub::editor_is_active)),
                    vibe::tick_vibe
                        .run_if(in_phase(PartyPhase::Vibe))
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(not(crate::hub::editor_is_active)),
                    shooter::tick_shooter
                        .run_if(is_party_authority)
                        .run_if(in_phase(PartyPhase::Shooter))
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(not(crate::hub::editor_is_active)),
                    shooter::client_fire_input
                        .run_if(not(is_party_authority))
                        .run_if(in_phase(PartyPhase::Shooter))
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(not(crate::hub::editor_is_active)),
                    cleanup_stage_props
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(not(crate::hub::editor_is_active)),
                ),
            );
    }
}

#[derive(Component)]
pub struct StageProp;

#[derive(Resource, Debug, Default)]
struct StageBoot {
    last: Option<PartyPhase>,
}

fn in_phase(phase: PartyPhase) -> impl Fn(Res<PartyDirector>) -> bool {
    move |director: Res<PartyDirector>| director.phase == phase
}

fn boot_stages(
    mut boot: ResMut<StageBoot>,
    director: Res<PartyDirector>,
    commands: Commands,
    meshes: ResMut<Assets<Mesh>>,
    materials: ResMut<Assets<StandardMaterial>>,
    asset_server: Res<AssetServer>,
    registry: Option<Res<crate::data::StudioRegistry>>,
    race: ResMut<race::RaceState>,
    vibe: ResMut<vibe::VibeState>,
    shooter: ResMut<shooter::ShooterState>,
    spawn: Res<crate::party::PartySpawn>,
    mut active: ResMut<crate::maps::ActiveStageMaps>,
    players: Query<(&crate::player::NetworkPlayer, &mut Transform)>,
    snaps: Query<&crate::party::PartySnapshot>,
    server: Option<Res<bevy_replicon_renet::RenetServer>>,
    client: Option<Res<bevy_replicon_renet::RenetClient>>,
) {
    let phase = director.phase;
    if boot.last == Some(phase) {
        return;
    }
    let entered = boot.last;
    boot.last = Some(phase);

    let teleport = server.is_some() || client.is_none();
    // Joiners: pull map ids from the replicated snapshot before spawning greybox.
    if !teleport {
        if let Ok(snap) = snaps.single() {
            *active = crate::maps::resolve_active_from_ids(
                &snap.race_map_id,
                &snap.vibe_map_id,
                &snap.shooter_map_id,
            );
        }
    }

    let maps = active.clone();
    let registry = registry.as_deref();
    match phase {
        PartyPhase::Race => race::setup_race(
            commands,
            meshes,
            materials,
            &asset_server,
            registry,
            race,
            spawn,
            &maps,
            players,
            teleport,
        ),
        PartyPhase::Vibe => vibe::setup_vibe(
            commands,
            meshes,
            materials,
            &asset_server,
            registry,
            vibe,
            spawn,
            &maps,
            players,
            teleport,
        ),
        PartyPhase::Shooter => shooter::setup_shooter(
            commands,
            meshes,
            materials,
            &asset_server,
            registry,
            shooter,
            spawn,
            &maps,
            players,
            teleport,
        ),
        _ => {
            let _ = entered;
        }
    }
}

fn cleanup_stage_props(
    director: Res<PartyDirector>,
    mut last: Local<Option<PartyPhase>>,
    props: Query<Entity, With<StageProp>>,
    mut commands: Commands,
) {
    let phase = director.phase;
    let leave_stage = matches!(
        *last,
        Some(PartyPhase::Race | PartyPhase::Vibe | PartyPhase::Shooter)
    ) && !matches!(
        phase,
        PartyPhase::Race | PartyPhase::Vibe | PartyPhase::Shooter
    );
    if leave_stage {
        for entity in &props {
            commands.entity(entity).despawn();
        }
    }
    *last = Some(phase);
}
