//! King of the Hill — hold the glowing zone; it moves between anchors.

use bevy::prelude::*;

use crate::{
    maps::ActiveStageMaps,
    party::{PartyBot, PartyDirector, PartySpawn},
    player::{LocalPlayer, NetworkPlayer},
    stages::StageProp,
    world::GameplayEntity,
};

/// Party points earned per full second alone on the hill.
const HOLD_POINTS_PER_SEC: u32 = 1;

/// Units per second the hill glides between anchors (instead of teleporting).
const HILL_GLIDE_SPEED: f32 = 14.0;

#[derive(Resource, Debug, Default)]
pub struct KothState {
    /// Accrued uncontested hold time in seconds, per network slot.
    pub hold: [f32; 16],
    /// Party points already granted (so we can award increments).
    pub awarded: [u32; 16],
    /// Hill anchors in world space (cycled in order).
    pub hills: Vec<Vec3>,
    pub radius: f32,
    pub switch_secs: f32,
    /// director.phase_timer captured at stage boot — hill index derives from it,
    /// so host and joiners agree without extra replication.
    pub start_timer: f32,
    pub announced_hill: usize,
}

impl KothState {
    pub fn active_hill_index(&self, phase_timer: f32) -> usize {
        if self.hills.is_empty() {
            return 0;
        }
        let elapsed = (self.start_timer - phase_timer).max(0.0);
        (elapsed / self.switch_secs.max(1.0)) as usize % self.hills.len()
    }

    /// Where the hill actually is right now, mid-glide included.
    ///
    /// Derived purely from the phase timer so the host's scoring and every
    /// client's visuals agree without replicating the hill transform.
    pub fn hill_center(&self, phase_timer: f32) -> Option<Vec3> {
        if self.hills.is_empty() {
            return None;
        }
        let idx = self.active_hill_index(phase_timer);
        let current = self.hills[idx];
        let elapsed = (self.start_timer - phase_timer).max(0.0);
        let switch = self.switch_secs.max(1.0);
        // First cycle starts on the hill; later cycles glide in from the
        // previous anchor.
        if elapsed < switch || self.hills.len() < 2 {
            return Some(current);
        }
        let previous = self.hills[(idx + self.hills.len() - 1) % self.hills.len()];
        let into_segment = elapsed % switch;
        let span = previous.distance(current);
        let travelled = HILL_GLIDE_SPEED * into_segment;
        if travelled >= span || span <= f32::EPSILON {
            Some(current)
        } else {
            Some(previous.lerp(current, travelled / span))
        }
    }
}

#[derive(Component)]
pub struct HillZone;

pub fn setup_koth(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server: &AssetServer,
    registry: Option<&crate::data::StudioRegistry>,
    mut state: ResMut<KothState>,
    spawn: Res<PartySpawn>,
    active: &ActiveStageMaps,
    mut players: Query<(&NetworkPlayer, &mut Transform)>,
    teleport_players: bool,
    phase_timer: f32,
) {
    *state = KothState::default();
    state.start_timer = phase_timer;

    let hub = spawn.hub;
    let (spawns, hills, radius, switch_secs, blocks) = if let Some(map) = &active.koth {
        (
            map.spawns.clone(),
            map.hill_positions(),
            map.hill_radius,
            map.hill_switch_secs,
            map.blocks.clone(),
        )
    } else {
        (
            vec![
                [hub.x, 1.0, hub.z + 8.0],
                [hub.x + 12.0, 1.0, hub.z - 10.0],
                [hub.x - 12.0, 1.0, hub.z - 10.0],
                [hub.x, 1.0, hub.z - 18.0],
            ],
            vec![
                hub + Vec3::new(0.0, 0.0, -6.0),
                hub + Vec3::new(13.0, 0.0, -14.0),
                hub + Vec3::new(-13.0, 0.0, 2.0),
            ],
            4.5,
            12.0,
            Vec::new(),
        )
    };
    state.hills = hills;
    state.radius = radius;
    state.switch_secs = switch_secs;

    if teleport_players {
        for (net, mut tf) in &mut players {
            if let Some(pos) = spawns.get(net.slot as usize).or_else(|| spawns.first()) {
                tf.translation = Vec3::new(pos[0], pos[1], pos[2]);
            }
        }
    }

    // The hill itself — recolored every frame by occupancy.
    let first = state.hills.first().copied().unwrap_or(hub);
    commands.spawn((
        StageProp,
        HillZone,
        GameplayEntity,
        Mesh3d(meshes.add(Cylinder::new(radius, 0.25))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgba(1.0, 0.8, 0.2, 0.65),
            emissive: LinearRgba::rgb(1.6, 1.1, 0.2),
            alpha_mode: AlphaMode::Blend,
            unlit: true,
            ..Default::default()
        })),
        Transform::from_translation(Vec3::new(first.x, 0.12, first.z)),
        Name::new("HillZone"),
    ));

    // Flag every hill anchor so players can read the rotation.
    for (i, hill) in state.hills.iter().enumerate() {
        let marker_tf =
            Transform::from_translation(Vec3::new(hill.x, 0.0, hill.z));
        let spawned = registry.and_then(|reg| {
            crate::assets::spawn_studio_prop(
                &mut commands,
                asset_server,
                reg,
                "prop_target_star_01",
                marker_tf,
                (StageProp, Name::new(format!("HillAnchor_{i}"))),
            )
        });
        if spawned.is_none() {
            commands.spawn((
                StageProp,
                GameplayEntity,
                Mesh3d(meshes.add(Cylinder::new(0.18, 3.2))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(0.9, 0.75, 0.3),
                    ..Default::default()
                })),
                Transform::from_translation(Vec3::new(hill.x, 1.6, hill.z)),
                Name::new(format!("HillAnchor_{i}")),
            ));
        }
    }

    for (i, block) in blocks.iter().enumerate() {
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
                    (StageProp, Name::new(format!("KothBlock_{i}"))),
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
                    base_color: Color::srgb(0.5, 0.45, 0.4),
                    ..Default::default()
                })),
                tf,
                Name::new(format!("KothBlock_{i}")),
            ));
        }
    }
}

/// Runs on every peer — moves the hill deterministically and colors it by occupancy.
pub fn update_koth_hill(
    director: Res<PartyDirector>,
    state: Res<KothState>,
    players: Query<&Transform, With<NetworkPlayer>>,
    mut hills: Query<
        (&mut Transform, &MeshMaterial3d<StandardMaterial>),
        (With<HillZone>, Without<NetworkPlayer>),
    >,
    mut materials: ResMut<Assets<StandardMaterial>>,
    time: Res<Time>,
) {
    let Ok((mut tf, mat_handle)) = hills.single_mut() else {
        return;
    };
    let Some(center) = state.hill_center(director.phase_timer) else {
        return;
    };
    // Glides between anchors; only write the transform while actually moving.
    let goal = Vec3::new(center.x, 0.12, center.z);
    if tf.translation.distance_squared(goal) > 1e-6 {
        tf.translation = goal;
    }

    let occupants = players
        .iter()
        .filter(|p| {
            Vec2::new(p.translation.x, p.translation.z)
                .distance(Vec2::new(center.x, center.z))
                < state.radius
        })
        .count();

    if let Some(mut mat) = materials.get_mut(mat_handle) {
        let pulse = 0.8 + 0.35 * (time.elapsed_secs() * 4.0).sin();
        let (r, g, b) = match occupants {
            0 => (1.0, 0.8, 0.2),  // neutral gold
            1 => (0.3, 1.0, 0.45), // captured green
            _ => (1.0, 0.3, 0.3),  // contested red
        };
        mat.base_color = Color::srgba(r, g, b, 0.65);
        mat.emissive = LinearRgba::rgb(r * 1.8 * pulse, g * 1.4 * pulse, b * pulse);
    }
}

/// Host-authoritative scoring + bot steering.
pub fn tick_koth(
    time: Res<Time>,
    mut state: ResMut<KothState>,
    mut director: ResMut<PartyDirector>,
    mut players: Query<(&NetworkPlayer, &mut Transform, Has<PartyBot>, Has<LocalPlayer>)>,
) {
    let dt = time.delta_secs();
    let hill_index = state.active_hill_index(director.phase_timer);
    // Scoring tracks the gliding center so it always matches what players see.
    let Some(hill) = state.hill_center(director.phase_timer) else {
        return;
    };

    if state.announced_hill != hill_index {
        state.announced_hill = hill_index;
        director.announcer = "The hill is on the move — chase it!".into();
    }

    // Bots chase the hill and shuffle a little inside it.
    for (net, mut tf, is_bot, _) in &mut players {
        if !is_bot {
            continue;
        }
        let wobble = Vec3::new(
            (time.elapsed_secs() * 1.3 + net.slot as f32).sin(),
            0.0,
            (time.elapsed_secs() * 1.1 + net.slot as f32 * 2.0).cos(),
        ) * (state.radius * 0.4);
        let target = hill + wobble;
        let dir = (target - tf.translation).normalize_or_zero();
        tf.translation += dir * 4.8 * dt;
        tf.translation.y = 1.0;
    }

    let hill_xz = Vec2::new(hill.x, hill.z);
    let occupants: Vec<(u32, bool)> = players
        .iter()
        .filter(|(_, tf, _, _)| {
            Vec2::new(tf.translation.x, tf.translation.z).distance(hill_xz) < state.radius
        })
        .map(|(net, _, _, is_local)| (net.slot, is_local))
        .collect();

    // Contested (2+) or empty hills score nobody — classic king of the hill.
    if let [(slot, is_local)] = occupants.as_slice() {
        let slot_idx = *slot as usize;
        if slot_idx < state.hold.len() {
            state.hold[slot_idx] += dt;
            let total = state.hold[slot_idx] as u32 * HOLD_POINTS_PER_SEC;
            if total > state.awarded[slot_idx] {
                director.add_points(*slot, total - state.awarded[slot_idx]);
                state.awarded[slot_idx] = total;
                if *is_local {
                    director.announcer =
                        format!("You are king! ({:.0}s held)", state.hold[slot_idx]);
                }
            }
        }
    }
}
