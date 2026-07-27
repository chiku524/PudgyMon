//! Soft AABB push volumes from layout greyboxes — no physics crate.

use bevy::prelude::*;

use crate::core::clamp_to_island;

/// Axis-aligned push volume in world space (center + half extents).
#[derive(Component, Debug, Clone, Copy)]
pub struct PushVolume {
    pub half_extents: Vec3,
}

impl PushVolume {
    pub fn from_greybox_size(size: Vec3) -> Self {
        // Slightly shrink so interact radii still reach station fronts.
        Self {
            half_extents: Vec3::new(
                (size.x * 0.5 * 0.92).max(0.15),
                (size.y * 0.5).max(0.1),
                (size.z * 0.5 * 0.92).max(0.15),
            ),
        }
    }
}

const PLAYER_RADIUS: f32 = 0.4;

/// Resolve local player against push volumes after movement / knockback.
pub fn resolve_player_push(
    mut players: Query<&mut Transform, With<crate::player::LocalPlayer>>,
    volumes: Query<(&Transform, &PushVolume), Without<crate::player::LocalPlayer>>,
) {
    let Ok(mut player) = players.single_mut() else {
        return;
    };

    // Preserve vertical motion (jumps) — only resolve horizontal overlaps.
    let mut pos = player.translation;
    let keep_y = pos.y;

    for (vol_tf, volume) in &volumes {
        // Skip flat floors / pads (short Y) — walk-on, not push.
        if volume.half_extents.y < 0.25 {
            continue;
        }

        let center = vol_tf.translation;
        let hx = volume.half_extents.x * vol_tf.scale.x.abs() + PLAYER_RADIUS;
        let hz = volume.half_extents.z * vol_tf.scale.z.abs() + PLAYER_RADIUS;

        let dx = pos.x - center.x;
        let dz = pos.z - center.z;
        if dx.abs() >= hx || dz.abs() >= hz {
            continue;
        }

        let push_x = hx - dx.abs();
        let push_z = hz - dz.abs();
        if push_x < push_z {
            pos.x = center.x + dx.signum() * hx;
        } else {
            pos.z = center.z + dz.signum() * hz;
        }
    }

    pos = clamp_to_island(pos);
    pos.y = keep_y;
    player.translation = pos;
}
