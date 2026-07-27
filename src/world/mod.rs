use bevy::pbr::{DistanceFog, FogFalloff};
use bevy::prelude::*;

use crate::flow::AppScreen;
use crate::party::{PartyDirector, PartyPhase};

/// Persistent arena shell + party lighting.
pub struct WorldPlugin;

impl Plugin for WorldPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(
            Update,
            sync_party_atmosphere.run_if(in_state(AppScreen::Playing)),
        );
    }
}

#[derive(Component)]
struct KeyLight;

#[derive(Component)]
struct FillLight;

pub fn spawn_camera(mut commands: Commands) {
    // Open-world sky: soft daylight clear color + distance fog so the ocean
    // fades into the horizon instead of ending at a hard edge.
    commands.insert_resource(ClearColor(Color::srgb(0.55, 0.74, 0.92)));
    commands.spawn((
        Camera3d::default(),
        MainCamera,
        DistanceFog {
            color: Color::srgb(0.62, 0.78, 0.9),
            falloff: FogFalloff::Linear {
                start: 95.0,
                end: 260.0,
            },
            ..Default::default()
        },
        Transform::from_xyz(0.0, 12.0, 22.0).looking_at(Vec3::ZERO, Vec3::Y),
        Name::new("MainCamera"),
    ));

    commands.spawn((
        KeyLight,
        DirectionalLight {
            illuminance: 12_000.0,
            color: Color::srgb(1.0, 0.95, 0.88),
            shadow_maps_enabled: true,
            ..Default::default()
        },
        Transform::from_xyz(10.0, 22.0, 8.0).looking_at(Vec3::ZERO, Vec3::Y),
        Name::new("KeyLight"),
    ));

    commands.spawn((
        FillLight,
        PointLight {
            intensity: 1_400_000.0,
            range: 55.0,
            color: Color::srgb(0.55, 0.45, 1.0),
            ..Default::default()
        },
        Transform::from_xyz(-8.0, 8.0, 8.0),
        Name::new("FillLight"),
    ));
}

/// Seconds to crossfade lighting when the party phase changes.
const ATMOSPHERE_FADE_SECS: f32 = 1.2;

fn sync_party_atmosphere(
    time: Res<Time>,
    director: Res<PartyDirector>,
    mut last_phase: Local<Option<PartyPhase>>,
    mut fade_left: Local<f32>,
    mut key: Query<&mut DirectionalLight, With<KeyLight>>,
    mut fill: Query<&mut PointLight, With<FillLight>>,
) {
    if *last_phase != Some(director.phase) {
        *last_phase = Some(director.phase);
        *fade_left = ATMOSPHERE_FADE_SECS;
    }
    // Steady state: don't dirty the lights (and their GPU uniforms) each frame.
    if *fade_left <= 0.0 {
        return;
    }
    *fade_left -= time.delta_secs();

    let (key_color, fill_color, key_lux, fill_i) = match director.phase {
        PartyPhase::Race => (
            Color::srgb(0.7, 0.9, 1.0),
            Color::srgb(0.2, 0.85, 1.0),
            14_000.0,
            1_000_000.0,
        ),
        PartyPhase::Vibe => (
            Color::srgb(1.0, 0.95, 0.55),
            Color::srgb(1.0, 0.85, 0.2),
            13_000.0,
            1_100_000.0,
        ),
        PartyPhase::Shooter => (
            Color::srgb(1.0, 0.55, 0.45),
            Color::srgb(1.0, 0.35, 0.55),
            15_000.0,
            1_200_000.0,
        ),
        PartyPhase::Koth => (
            Color::srgb(0.9, 0.7, 1.0),
            Color::srgb(0.75, 0.5, 1.0),
            14_500.0,
            1_150_000.0,
        ),
        _ => (
            Color::srgb(1.0, 0.95, 0.88),
            Color::srgb(0.55, 0.45, 1.0),
            12_000.0,
            900_000.0,
        ),
    };
    // Exponential ease toward the target, snapping exactly on the last tick.
    let t = if *fade_left <= 0.0 {
        1.0
    } else {
        1.0 - (-5.0 * time.delta_secs()).exp()
    };
    if let Ok(mut light) = key.single_mut() {
        light.color = light.color.mix(&key_color, t);
        light.illuminance += (key_lux - light.illuminance) * t;
    }
    if let Ok(mut light) = fill.single_mut() {
        light.color = light.color.mix(&fill_color, t);
        light.intensity += (fill_i - light.intensity) * t;
    }
}

/// Marks the main viewport camera.
#[derive(Component, Debug, Clone, Copy)]
pub struct MainCamera;

/// Marker for entities spawned as part of the greybox level.
#[derive(Component, Debug, Clone, Copy)]
pub struct GameplayEntity;

/// Persistent arena geometry — not despawned when vault stages swap.
#[derive(Component, Debug, Clone, Copy)]
pub struct ArenaPiece;
