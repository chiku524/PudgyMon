//! Timed vibe orb collection.

use bevy::prelude::*;

use crate::{
    challenges::ChallengeBoard,
    maps::ActiveStageMaps,
    party::{PartyBot, PartyDirector, PartySpawn},
    player::{LocalPlayer, NetworkPlayer},
    stages::StageProp,
    world::GameplayEntity,
};

#[derive(Resource, Debug, Default)]
pub struct VibeState {
    pub collected: [u32; 16],
}

#[derive(Component)]
pub struct VibeOrb;

pub fn setup_vibe(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server: &AssetServer,
    registry: Option<&crate::data::StudioRegistry>,
    mut state: ResMut<VibeState>,
    spawn: Res<PartySpawn>,
    active: &ActiveStageMaps,
    mut players: Query<(&NetworkPlayer, &mut Transform)>,
    teleport_players: bool,
) {
    *state = VibeState::default();

    let (spawn_base, orbs, blocks) = if let Some(map) = &active.vibe {
        (
            map.spawns.first().copied().unwrap_or([0.0, 1.0, 0.0]),
            map.orbs.clone(),
            map.blocks.clone(),
        )
    } else {
        let mut default_orbs = Vec::new();
        for i in 0..16 {
            let angle = i as f32 * 0.7;
            default_orbs.push([angle.cos() * 16.0, 0.6, angle.sin() * 16.0]);
        }
        ([0.0, 1.0, 0.0], default_orbs, Vec::new())
    };

    if teleport_players {
        for (net, mut tf) in &mut players {
            if active.vibe.is_some() {
                tf.translation = Vec3::new(
                    spawn_base[0] + (net.slot as f32) * 2.0 - 2.0,
                    spawn_base[1],
                    spawn_base[2],
                );
            } else {
                tf.translation = spawn.hub + Vec3::new((net.slot as f32) * 2.0 - 3.0, 1.0, 0.0);
            }
        }
    }

    let hub = spawn.hub;
    for (i, pos) in orbs.iter().enumerate() {
        let world = if active.vibe.is_some() {
            Vec3::new(pos[0], pos[1], pos[2])
        } else {
            hub + Vec3::new(pos[0], pos[1], pos[2])
        };
        let tf = Transform::from_translation(world);
        let spawned = registry.and_then(|reg| {
            crate::assets::spawn_studio_prop(
                &mut commands,
                asset_server,
                reg,
                "prop_vibe_orb_01",
                tf,
                (StageProp, VibeOrb, Name::new(format!("Vibe_{i}"))),
            )
        });
        if spawned.is_none() {
            commands.spawn((
                StageProp,
                VibeOrb,
                GameplayEntity,
                Mesh3d(meshes.add(Sphere::new(0.45))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(1.0, 0.9, 0.2),
                    emissive: LinearRgba::rgb(2.5, 2.0, 0.3),
                    unlit: true,
                    ..Default::default()
                })),
                tf,
                Name::new(format!("Vibe_{i}")),
            ));
        }
    }

    // Arena flora accents.
    if let Some(reg) = registry {
        for (i, (asset_id, offset)) in [
            ("prop_vibe_flower_01", Vec3::new(-10.0, 0.0, -8.0)),
            ("prop_vibe_flower_01", Vec3::new(10.0, 0.0, -8.0)),
            ("prop_vibe_crystal_01", Vec3::new(-8.0, 0.0, 10.0)),
            ("prop_vibe_crystal_01", Vec3::new(8.0, 0.0, 10.0)),
            ("prop_vibe_mushroom_01", Vec3::new(0.0, 0.0, -14.0)),
        ]
        .into_iter()
        .enumerate()
        {
            let origin = if active.vibe.is_some() {
                Vec3::ZERO
            } else {
                hub
            };
            let _ = crate::assets::spawn_studio_prop(
                &mut commands,
                asset_server,
                reg,
                asset_id,
                Transform::from_translation(origin + offset),
                (StageProp, Name::new(format!("VibeDeco_{i}"))),
            );
        }
    }

    for (i, block) in blocks.iter().enumerate() {
        let [sx, sy, sz] = block.size;
        let tf = Transform::from_translation(Vec3::new(block.pos[0], block.pos[1], block.pos[2]));
        let deco_id = block.asset_id.as_deref().unwrap_or("prop_vibe_crystal_01");
        let spawned = registry.and_then(|reg| {
            if crate::assets::studio_asset_exists(reg, deco_id) {
                crate::assets::spawn_studio_prop(
                    &mut commands,
                    asset_server,
                    reg,
                    deco_id,
                    tf,
                    (StageProp, Name::new(format!("VibeBlock_{i}"))),
                )
            } else {
                None
            }
        });
        if spawned.is_none() {
            commands.spawn((
                StageProp,
                GameplayEntity,
                Mesh3d(meshes.add(Cuboid::new(sx.max(0.5), sy.max(0.5), sz.max(0.5)))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(0.55, 0.4, 0.3),
                    ..Default::default()
                })),
                tf,
                Name::new(format!("VibeBlock_{i}")),
            ));
        }
    }
}

pub fn tick_vibe(
    time: Res<Time>,
    mut commands: Commands,
    mut state: ResMut<VibeState>,
    mut director: ResMut<PartyDirector>,
    mut challenges: ResMut<ChallengeBoard>,
    mut players: Query<(&NetworkPlayer, &mut Transform, Has<PartyBot>, Has<LocalPlayer>)>,
    orbs: Query<(Entity, &Transform), (With<VibeOrb>, Without<NetworkPlayer>)>,
    server: Option<Res<bevy_replicon_renet::RenetServer>>,
    client: Option<Res<bevy_replicon_renet::RenetClient>>,
) {
    let authority = server.is_some() || client.is_none();
    let dt = time.delta_secs();
    let orb_list: Vec<(Entity, Vec3)> = orbs
        .iter()
        .map(|(e, t)| (e, t.translation))
        .collect();

    for (net, mut tf, is_bot, is_local) in &mut players {
        // Bot AI only on host (bots are replicated; clients just follow transforms).
        if authority && is_bot {
            if let Some((_, target)) = orb_list.first() {
                let dir = (*target - tf.translation).normalize_or_zero();
                tf.translation += dir * 4.5 * dt;
                tf.translation.y = 1.0;
            }
        }

        for (entity, pos) in &orb_list {
            if tf.translation.distance(*pos) < 1.4 {
                // Local despawn for visuals on every peer; scoring host-only.
                commands.entity(*entity).despawn();
                if authority {
                    let slot = net.slot as usize;
                    if slot < state.collected.len() {
                        state.collected[slot] += 1;
                        director.add_points(net.slot, 3);
                        if is_local {
                            challenges.set_max("vibe_10", state.collected[slot]);
                            director.announcer = format!("Vibe! ({})", state.collected[slot]);
                        }
                    }
                }
                break;
            }
        }
    }
}
