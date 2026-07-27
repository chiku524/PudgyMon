//! Knockback impulse applied after bad interacts.

use bevy::prelude::*;

/// Horizontal shove applied each frame until it decays.
#[derive(Component, Debug, Clone, Copy, Default)]
pub struct Knockback {
    pub velocity: Vec3,
}

impl Knockback {
    pub fn shove_away_from(from: Vec3, toward: Vec3, strength: f32) -> Self {
        let mut dir = toward - from;
        dir.y = 0.0;
        if dir.length_squared() < 1e-4 {
            dir = Vec3::NEG_Z;
        }
        Self {
            velocity: dir.normalize() * strength,
        }
    }
}

pub fn apply_knockback_motion(
    time: Res<Time>,
    mut players: Query<(&mut Transform, &mut Knockback)>,
) {
    let dt = time.delta_secs();
    for (mut transform, mut knock) in &mut players {
        if knock.velocity.length_squared() < 1e-4 {
            knock.velocity = Vec3::ZERO;
            continue;
        }
        transform.translation += knock.velocity * dt;
        // Keep vertical motion owned by jump/gravity — only shove on XZ.
        let keep_y = transform.translation.y;
        transform.translation = crate::core::clamp_to_island(transform.translation);
        transform.translation.y = keep_y;
        knock.velocity *= (1.0 - 6.0 * dt).max(0.0);
        if knock.velocity.length() < 0.2 {
            knock.velocity = Vec3::ZERO;
        }
    }
}
