//! Short FFA toy-blaster stage — LMB / F to fire.

use bevy::prelude::*;
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    challenges::ChallengeBoard,
    maps::ActiveStageMaps,
    network::OwnedPlayer,
    party::{PartyBot, PartyDirector, PartySpawn},
    player::{LocalPlayer, NetworkPlayer, ThirdPersonCamera},
    stages::StageProp,
    world::GameplayEntity,
};

#[derive(Resource, Debug, Default)]
pub struct ShooterState {
    pub kos: [u32; 16],
    pub cooldown: [f32; 16],
}

#[derive(Component, Serialize, Deserialize, Clone, Debug)]
pub struct Projectile {
    pub owner: u32,
    pub velocity: Vec3,
    pub ttl: f32,
}

#[derive(Event, Serialize, Deserialize, Clone, Copy, Debug)]
pub struct ShootRequest {
    pub yaw: f32,
}

pub fn setup_shooter(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server: &AssetServer,
    registry: Option<&crate::data::StudioRegistry>,
    mut state: ResMut<ShooterState>,
    spawn: Res<PartySpawn>,
    active: &ActiveStageMaps,
    mut players: Query<(&NetworkPlayer, &mut Transform)>,
    teleport_players: bool,
) {
    *state = ShooterState::default();

    let (spawns, cover) = if let Some(map) = &active.shooter {
        (map.spawns.clone(), map.cover.clone())
    } else {
        (Vec::new(), Vec::new())
    };

    if teleport_players {
        for (net, mut tf) in &mut players {
            if let Some(pos) = spawns.get(net.slot as usize).or_else(|| spawns.first()) {
                tf.translation = Vec3::new(pos[0], pos[1], pos[2]);
            } else {
                let angle = net.slot as f32 * 0.9;
                tf.translation =
                    spawn.hub + Vec3::new(angle.cos() * 12.0, 1.0, angle.sin() * 12.0 - 8.0);
            }
        }
    }

    let hub = spawn.hub;
    if cover.is_empty() {
        // Default arena cover + targets when no custom map.
        let defaults: [(&str, Vec3, f32); 6] = [
            ("prop_cover_block_01", Vec3::new(-6.0, 0.0, -6.0), 20.0),
            ("prop_cover_block_01", Vec3::new(6.0, 0.0, -6.0), -20.0),
            ("prop_cover_block_01", Vec3::new(0.0, 0.0, -12.0), 0.0),
            ("prop_target_star_01", Vec3::new(-10.0, 0.0, -10.0), 45.0),
            ("prop_target_star_01", Vec3::new(10.0, 0.0, -10.0), -45.0),
            ("prop_blaster_toy_01", Vec3::new(0.0, 0.0, -4.0), 180.0),
        ];
        if let Some(reg) = registry {
            for (i, (asset_id, offset, yaw)) in defaults.into_iter().enumerate() {
                let _ = crate::assets::spawn_studio_prop(
                    &mut commands,
                    asset_server,
                    reg,
                    asset_id,
                    Transform::from_translation(hub + offset)
                        .with_rotation(Quat::from_rotation_y(yaw.to_radians())),
                    (StageProp, Name::new(format!("ShooterDefault_{i}"))),
                );
            }
        }
    }

    for (i, block) in cover.iter().enumerate() {
        let [sx, sy, sz] = block.size;
        let tf = Transform::from_translation(Vec3::new(block.pos[0], block.pos[1], block.pos[2]));
        let deco_id = block.asset_id.as_deref().unwrap_or("prop_cover_block_01");
        let spawned = registry.and_then(|reg| {
            if crate::assets::studio_asset_exists(reg, deco_id) {
                crate::assets::spawn_studio_prop(
                    &mut commands,
                    asset_server,
                    reg,
                    deco_id,
                    tf,
                    (StageProp, Name::new(format!("ShooterCover_{i}"))),
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
                    base_color: Color::srgb(0.45, 0.5, 0.55),
                    ..Default::default()
                })),
                tf,
                Name::new(format!("ShooterCover_{i}")),
            ));
        }
    }
}

pub fn client_fire_input(
    keyboard: Res<ButtonInput<KeyCode>>,
    mouse: Res<ButtonInput<MouseButton>>,
    camera: Res<ThirdPersonCamera>,
    local: Query<(), (With<LocalPlayer>, With<NetworkPlayer>)>,
    mut commands: Commands,
) {
    if local.is_empty() {
        return;
    }
    if !(mouse.just_pressed(MouseButton::Left) || keyboard.just_pressed(KeyCode::KeyF)) {
        return;
    }
    commands.client_trigger(ShootRequest { yaw: camera.yaw });
}

pub fn handle_shoot_request(
    request: On<FromClient<ShootRequest>>,
    mut state: ResMut<ShooterState>,
    mut commands: Commands,
    owners: Query<&OwnedPlayer>,
    players: Query<(&NetworkPlayer, &Transform), With<NetworkPlayer>>,
) {
    let Some(client_entity) = request.client_id.entity() else {
        return;
    };
    let Ok(owned) = owners.get(client_entity) else {
        return;
    };
    let Ok((net, tf)) = players.get(owned.0) else {
        return;
    };
    let slot = net.slot as usize;
    if slot >= state.cooldown.len() || state.cooldown[slot] > 0.0 {
        return;
    }
    state.cooldown[slot] = 0.35;
    spawn_projectile(&mut commands, net.slot, tf.translation, request.yaw);
}

pub fn init_projectile_visuals(
    add: On<Add, Projectile>,
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    existing: Query<(), With<Mesh3d>>,
) {
    if existing.get(add.entity).is_ok() {
        return;
    }
    commands.entity(add.entity).insert((
        StageProp,
        GameplayEntity,
        Mesh3d(meshes.add(Sphere::new(0.18))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(1.0, 0.4, 0.2),
            emissive: LinearRgba::rgb(2.0, 0.6, 0.2),
            unlit: true,
            ..Default::default()
        })),
        Name::new("Projectile"),
    ));
}

fn spawn_projectile(commands: &mut Commands, owner: u32, origin: Vec3, yaw: f32) {
    let forward = Vec3::new(-yaw.sin(), 0.0, -yaw.cos());
    commands.spawn((
        Replicated,
        StageProp,
        Projectile {
            owner,
            velocity: forward * 22.0,
            ttl: 1.2,
        },
        GameplayEntity,
        Transform::from_translation(origin + Vec3::Y * 1.1 + forward),
        Visibility::default(),
        Name::new("Projectile"),
    ));
}

pub fn tick_shooter(
    time: Res<Time>,
    keyboard: Res<ButtonInput<KeyCode>>,
    mouse: Res<ButtonInput<MouseButton>>,
    camera: Res<ThirdPersonCamera>,
    mut state: ResMut<ShooterState>,
    mut director: ResMut<PartyDirector>,
    mut challenges: ResMut<ChallengeBoard>,
    mut commands: Commands,
    mut players: Query<(&NetworkPlayer, &mut Transform, Has<PartyBot>, Has<LocalPlayer>)>,
    mut projectiles: Query<(Entity, &mut Projectile, &mut Transform), Without<NetworkPlayer>>,
) {
    let dt = time.delta_secs();

    for (net, tf, is_bot, is_local) in &players {
        let slot = net.slot as usize;
        if slot >= state.cooldown.len() {
            continue;
        }
        state.cooldown[slot] = (state.cooldown[slot] - dt).max(0.0);

        let want_fire = if is_local {
            mouse.just_pressed(MouseButton::Left) || keyboard.just_pressed(KeyCode::KeyF)
        } else if is_bot {
            state.cooldown[slot] <= 0.0
                && (time.elapsed_secs() * 2.7 + net.slot as f32).sin() > 0.9
        } else {
            false
        };

        if want_fire && state.cooldown[slot] <= 0.0 {
            state.cooldown[slot] = if is_bot { 0.95 } else { 0.35 };
            let yaw = if is_local {
                camera.yaw
            } else {
                tf.translation.x.atan2(tf.translation.z + 0.01)
            };
            spawn_projectile(&mut commands, net.slot, tf.translation, yaw);
        }
    }

    let snapshots: Vec<(u32, Vec3, bool)> = players
        .iter()
        .map(|(net, tf, _, is_local)| (net.slot, tf.translation, is_local))
        .collect();

    let mut hits: Vec<(u32, u32)> = Vec::new();
    for (entity, mut proj, mut tf) in &mut projectiles {
        proj.ttl -= dt;
        tf.translation += proj.velocity * dt;
        if proj.ttl <= 0.0 {
            commands.entity(entity).despawn();
            continue;
        }
        for (slot, pos, _) in &snapshots {
            if *slot == proj.owner {
                continue;
            }
            if tf.translation.distance(*pos) < 1.15 {
                hits.push((proj.owner, *slot));
                commands.entity(entity).despawn();
                break;
            }
        }
    }

    for (owner, victim) in hits {
        let oi = owner as usize;
        if oi < state.kos.len() {
            state.kos[oi] += 1;
            director.add_points(owner, 8);
            if snapshots.iter().any(|(s, _, loc)| *s == owner && *loc) {
                challenges.set_max("ko_5", state.kos[oi]);
                director.announcer = format!("KO! ({} total)", state.kos[oi]);
            }
        }
        for (net, mut tf, _, _) in &mut players {
            if net.slot == victim {
                let push = Vec3::new(
                    (time.elapsed_secs() * 11.0).sin(),
                    0.0,
                    (time.elapsed_secs() * 9.0).cos(),
                )
                .normalize_or_zero();
                tf.translation += push * 1.4;
                tf.translation.y = 1.0;
            }
        }
    }

    for (_, mut tf, is_bot, _) in &mut players {
        if is_bot {
            let t = time.elapsed_secs();
            tf.translation.x += t.sin() * 0.9 * dt;
            tf.translation.z += t.cos() * 0.9 * dt;
            tf.translation.y = 1.0;
        }
    }
}
