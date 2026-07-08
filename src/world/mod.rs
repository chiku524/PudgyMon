use bevy::prelude::*;

/// Persistent arena floor — room props are spawned separately per vault stage.
pub struct WorldPlugin;

impl Plugin for WorldPlugin {
    fn build(&self, _app: &mut App) {}
}

pub fn spawn_camera(mut commands: Commands) {
    commands.spawn((
        Camera3d::default(),
        MainCamera,
        Transform::from_xyz(0.0, 8.0, 14.0).looking_at(Vec3::ZERO, Vec3::Y),
        Name::new("MainCamera"),
    ));

    commands.spawn((
        DirectionalLight {
            illuminance: light_consts::lux::OVERCAST_DAY,
            ..Default::default()
        },
        Transform::from_xyz(4.0, 12.0, 4.0).looking_at(Vec3::ZERO, Vec3::Y),
    ));
}

pub fn spawn_greybox_level(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let floor_material = materials.add(StandardMaterial {
        base_color: Color::srgb(0.18, 0.20, 0.24),
        ..Default::default()
    });
    let floor_mesh = meshes.add(Cuboid::new(40.0, 0.5, 40.0));

    commands.spawn((
        GameplayEntity,
        Mesh3d(floor_mesh),
        MeshMaterial3d(floor_material),
        Transform::from_xyz(0.0, -0.25, 0.0),
        Name::new("Floor"),
    ));

    info!("spawned vault arena floor — room layouts load per tournament stage");
}

/// Marks the main viewport camera.
#[derive(Component, Debug, Clone, Copy)]
pub struct MainCamera;

/// Marker for entities spawned as part of the greybox level.
#[derive(Component, Debug, Clone, Copy)]
pub struct GameplayEntity;
