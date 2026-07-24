//! Checkpoint race — run through gates in order.

use bevy::prelude::*;

use crate::{
    challenges::ChallengeBoard,
    maps::ActiveStageMaps,
    party::{PartyBot, PartyDirector, PartySpawn},
    player::{LocalPlayer, NetworkPlayer},
    session_flow::Spectating,
    stages::StageProp,
    world::GameplayEntity,
};

#[derive(Resource, Debug, Default)]
pub struct RaceState {
    pub next_gate: [u8; 16],
    pub finished: Vec<u32>,
    pub gate_count: u8,
}

#[derive(Component)]
pub struct RaceGate {
    pub index: u8,
}

#[derive(Component)]
pub struct RaceBlock;

pub fn setup_race(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server: &AssetServer,
    registry: Option<&crate::data::StudioRegistry>,
    mut race: ResMut<RaceState>,
    spawn: Res<PartySpawn>,
    active: &ActiveStageMaps,
    mut players: Query<(&NetworkPlayer, &mut Transform)>,
    teleport_players: bool,
) {
    *race = RaceState::default();

    let (gate_positions, spawn_base, blocks) = if let Some(map) = &active.race {
        (
            map.gate_positions(),
            map.spawns.first().copied().unwrap_or([0.0, 1.0, 20.0]),
            map.blocks.clone(),
        )
    } else {
        (
            vec![
                Vec3::new(-12.0, 1.0, 4.0),
                Vec3::new(0.0, 1.0, -8.0),
                Vec3::new(12.0, 1.0, 4.0),
                Vec3::new(0.0, 1.0, 20.0),
            ],
            [0.0, 1.0, 20.0],
            Vec::new(),
        )
    };

    race.gate_count = gate_positions.len() as u8;

    for (net, mut tf) in &mut players {
        if (net.slot as usize) < race.next_gate.len() {
            race.next_gate[net.slot as usize] = 0;
        }
        if !teleport_players {
            continue;
        }
        let offset = (net.slot as f32) * 2.2 - 2.0;
        tf.translation = Vec3::new(spawn_base[0] + offset, spawn_base[1], spawn_base[2]);
        // Keep relative to hub if using defaults without ActiveRaceMap absolute coords.
        if active.race.is_none() {
            tf.translation = spawn.hub + Vec3::new((net.slot as f32) * 2.2 - 4.0, 1.0, 20.0);
        }
    }

    let hub = spawn.hub;
    for (i, pos) in gate_positions.iter().enumerate() {
        let world = if active.race.is_some() {
            *pos
        } else {
            hub + *pos
        };
        let tf = Transform::from_translation(world);
        let spawned = registry.and_then(|reg| {
            crate::assets::spawn_studio_prop(
                &mut commands,
                asset_server,
                reg,
                "prop_race_checkpoint_01",
                tf,
                (
                    StageProp,
                    RaceGate { index: i as u8 },
                    Name::new(format!("RaceGate_{i}")),
                ),
            )
        });
        if spawned.is_none() {
            commands.spawn((
                StageProp,
                RaceGate { index: i as u8 },
                GameplayEntity,
                Mesh3d(meshes.add(Cuboid::new(3.0, 2.5, 0.4))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(0.2, 0.85, 1.0),
                    emissive: LinearRgba::rgb(0.2, 1.2, 1.8),
                    unlit: true,
                    ..Default::default()
                })),
                tf,
                Name::new(format!("RaceGate_{i}")),
            ));
        }
        // Cone markers flanking each gate when available.
        if let Some(reg) = registry {
            for (side, x) in [("L", -2.2_f32), ("R", 2.2)] {
                let cone_tf = Transform::from_translation(world + Vec3::new(x, 0.0, 0.0));
                let _ = crate::assets::spawn_studio_prop(
                    &mut commands,
                    asset_server,
                    reg,
                    "prop_race_cone_01",
                    cone_tf,
                    (
                        StageProp,
                        Name::new(format!("RaceCone_{i}_{side}")),
                    ),
                );
            }
        }
    }

    // Finish banner near last gate.
    if let (Some(reg), Some(last)) = (registry, gate_positions.last()) {
        let world = if active.race.is_some() {
            *last
        } else {
            hub + *last
        };
        let _ = crate::assets::spawn_studio_prop(
            &mut commands,
            asset_server,
            reg,
            "prop_race_banner_01",
            Transform::from_translation(world + Vec3::new(0.0, 0.0, 3.0)),
            (StageProp, Name::new("RaceBanner")),
        );
        let _ = crate::assets::spawn_studio_prop(
            &mut commands,
            asset_server,
            reg,
            "env_race_ramp_01",
            Transform::from_translation(world + Vec3::new(-6.0, 0.0, -2.0))
                .with_rotation(Quat::from_rotation_y(90f32.to_radians())),
            (StageProp, Name::new("RaceRamp")),
        );
    }

    for (i, block) in blocks.iter().enumerate() {
        let [sx, sy, sz] = block.size;
        let [px, py, pz] = block.pos;
        let tf = Transform::from_translation(Vec3::new(px, py, pz));
        let deco_id = block.asset_id.as_deref().unwrap_or("env_race_ramp_01");
        let spawned = registry.and_then(|reg| {
            if crate::assets::studio_asset_exists(reg, deco_id) {
                crate::assets::spawn_studio_prop(
                    &mut commands,
                    asset_server,
                    reg,
                    deco_id,
                    tf,
                    (StageProp, RaceBlock, Name::new(format!("RaceBlock_{i}"))),
                )
            } else {
                None
            }
        });
        if spawned.is_none() {
            commands.spawn((
                StageProp,
                RaceBlock,
                GameplayEntity,
                Mesh3d(meshes.add(Cuboid::new(sx.max(0.5), sy.max(0.5), sz.max(0.5)))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(0.55, 0.4, 0.3),
                    ..Default::default()
                })),
                tf,
                Name::new(format!("RaceBlock_{i}")),
            ));
        }
    }
}

pub fn tick_race(
    time: Res<Time>,
    mut race: ResMut<RaceState>,
    mut director: ResMut<PartyDirector>,
    mut challenges: ResMut<ChallengeBoard>,
    mut commands: Commands,
    mut players: Query<(
        Entity,
        &NetworkPlayer,
        &mut Transform,
        Has<PartyBot>,
        Has<LocalPlayer>,
    )>,
    gates: Query<(&RaceGate, &Transform), Without<NetworkPlayer>>,
) {
    let dt = time.delta_secs();
    let gate_count = race.gate_count.max(1);
    let gate_positions: Vec<(u8, Vec3)> = gates
        .iter()
        .map(|(g, t)| (g.index, t.translation))
        .collect();

    for (entity, net, mut tf, is_bot, is_local) in &mut players {
        let slot = net.slot as usize;
        if slot >= race.next_gate.len() || race.finished.contains(&net.slot) {
            continue;
        }
        let need = race.next_gate[slot];
        let Some((_, gate_pos)) = gate_positions.iter().find(|(i, _)| *i == need) else {
            continue;
        };

        if is_bot {
            let dir = (*gate_pos - tf.translation).normalize_or_zero();
            tf.translation += dir * 5.5 * dt;
            tf.translation.y = 1.0;
        }

        if tf.translation.distance(*gate_pos) < 2.4 {
            race.next_gate[slot] = need + 1;
            if race.next_gate[slot] >= gate_count {
                race.finished.push(net.slot);
                let place = race.finished.len() as u32;
                let pts = match place {
                    1 => 25,
                    2 => 18,
                    3 => 12,
                    _ => 6,
                };
                director.add_points(net.slot, pts);
                if is_local {
                    director.announcer =
                        format!("You finished race #{place} (+{pts}) — spectating");
                    commands.entity(entity).insert(Spectating);
                    if place <= 3 {
                        challenges.bump("race_podium", 1);
                    }
                }
            }
        }
    }
}
