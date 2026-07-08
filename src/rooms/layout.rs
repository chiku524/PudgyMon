use bevy::prelude::*;

use crate::{
    assets::spawn_job_station,
    core::{
        BREAKER_PANEL_ASSET, COOLANT_CONSOLE_ASSET, CRANE_CONSOLE_ASSET, FREIGHT_CRATE_ASSET,
        GANTRY_HOOK_ASSET, SHUTTLE_BAY_ASSET,
    },
    data::StudioRegistry,
    interaction::Interactable,
    tournament::types::{RoomId, TournamentPhase},
    world::GameplayEntity,
};

/// Despawned and rebuilt when the tournament enters a new vault stage.
#[derive(Component, Debug, Clone, Copy)]
pub struct RoomLayoutPiece;

#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ActiveRoomLayout {
    pub room: Option<RoomId>,
    pub phase: Option<TournamentPhase>,
}

pub fn sync_room_layout(
    director: Res<crate::tournament::TournamentDirector>,
    mut active: ResMut<ActiveRoomLayout>,
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    registry: Res<StudioRegistry>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    pieces: Query<Entity, With<RoomLayoutPiece>>,
) {
    let desired_room = match director.phase {
        TournamentPhase::RoomActive | TournamentPhase::Finale => Some(director.room),
        _ => None,
    };

    if active.room == desired_room && active.phase == Some(director.phase) {
        return;
    }

    for entity in &pieces {
        commands.entity(entity).despawn();
    }

    active.room = desired_room;
    active.phase = Some(director.phase);

    let Some(room) = desired_room else {
        return;
    };

    match room {
        RoomId::HrOrientation => spawn_orientation_bay(
            &mut commands,
            &asset_server,
            registry.as_ref(),
            &mut meshes,
            &mut materials,
        ),
        RoomId::CargoGantry => spawn_cargo_gantry(
            &mut commands,
            &asset_server,
            registry.as_ref(),
            &mut meshes,
            &mut materials,
        ),
        RoomId::BreakerPanic => spawn_breaker_panic(
            &mut commands,
            &asset_server,
            registry.as_ref(),
            &mut meshes,
            &mut materials,
        ),
        RoomId::ShuttleMeltdown => spawn_shuttle_meltdown(
            &mut commands,
            &asset_server,
            registry.as_ref(),
            &mut meshes,
            &mut materials,
        ),
    }

    info!("room layout spawned: {}", room.label());
}

fn spawn_orientation_bay(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    spawn_room_sign(
        commands,
        meshes,
        materials,
        "HR ORIENTATION BAY — sort freight into chutes",
        Vec3::new(0.0, 3.0, -10.0),
        Color::srgb(0.95, 0.85, 0.2),
    );

    let chutes = [
        (Vec3::new(-7.0, 0.0, 0.0), 0u8, Color::srgb(0.95, 0.45, 0.15), "Hot Dogs"),
        (Vec3::new(-2.5, 0.0, 0.0), 1u8, Color::srgb(0.75, 0.75, 0.8), "Toasters"),
        (Vec3::new(2.5, 0.0, 0.0), 2u8, Color::srgb(0.35, 0.7, 0.95), "Premium Air"),
        (Vec3::new(7.0, 0.0, 0.0), 3u8, Color::srgb(0.9, 0.3, 0.3), "Write-Ups"),
    ];

    for (pos, chute, color, label) in chutes {
        spawn_sort_chute(commands, meshes, materials, pos, chute, color, label);
    }

    spawn_layout_station(
        commands,
        asset_server,
        registry,
        meshes,
        materials,
        FREIGHT_CRATE_ASSET,
        Transform::from_xyz(-4.0, 0.0, 5.0),
        Interactable::vault_objective(),
        Color::srgb(0.55, 0.4, 0.25),
        Vec3::new(1.0, 1.0, 1.0),
    );
}

fn spawn_cargo_gantry(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    spawn_room_sign(
        commands,
        meshes,
        materials,
        "CARGO RING GANTRY — deliver crates",
        Vec3::new(0.0, 3.5, -12.0),
        Color::srgb(0.85, 0.55, 0.15),
    );

    spawn_layout_station(
        commands,
        asset_server,
        registry,
        meshes,
        materials,
        CRANE_CONSOLE_ASSET,
        Transform::from_xyz(0.0, 0.0, -6.0),
        Interactable::crane(),
        Color::srgb(0.85, 0.55, 0.15),
        Vec3::new(1.5, 1.2, 1.0),
    );

    spawn_layout_station(
        commands,
        asset_server,
        registry,
        meshes,
        materials,
        GANTRY_HOOK_ASSET,
        Transform::from_xyz(5.0, 2.0, -2.0),
        Interactable::vault_objective(),
        Color::srgb(0.6, 0.6, 0.65),
        Vec3::new(0.8, 0.8, 0.8),
    );

    for x in [-5.0_f32, 5.0] {
        spawn_layout_station(
            commands,
            asset_server,
            registry,
            meshes,
            materials,
            FREIGHT_CRATE_ASSET,
            Transform::from_xyz(x, 0.0, 4.0),
            Interactable::vault_objective(),
            Color::srgb(0.55, 0.4, 0.25),
            Vec3::new(1.0, 1.0, 1.0),
        );
    }

    spawn_delivery_zone(commands, meshes, materials, Vec3::new(0.0, 0.0, 8.0));
}

fn spawn_breaker_panic(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    spawn_room_sign(
        commands,
        meshes,
        materials,
        "BREAKER PANIC — flip in sequence",
        Vec3::new(0.0, 3.5, -10.0),
        Color::srgb(0.35, 0.55, 0.95),
    );

    let positions = [
        Vec3::new(-9.0, 0.0, 0.0),
        Vec3::new(-3.0, 0.0, 0.0),
        Vec3::new(3.0, 0.0, 0.0),
        Vec3::new(9.0, 0.0, 0.0),
    ];

    for (index, position) in positions.into_iter().enumerate() {
        spawn_layout_station(
            commands,
            asset_server,
            registry,
            meshes,
            materials,
            BREAKER_PANEL_ASSET,
            Transform::from_xyz(position.x, position.y, position.z)
                .with_rotation(Quat::from_rotation_y(std::f32::consts::FRAC_PI_2)),
            Interactable::breaker(index as u8),
            Color::srgb(0.35, 0.55, 0.95),
            Vec3::new(0.8, 1.2, 0.4),
        );
    }
}

fn spawn_shuttle_meltdown(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    spawn_room_sign(
        commands,
        meshes,
        materials,
        "SHUTTLE BAY MELTDOWN — coolant + load + seal",
        Vec3::new(0.0, 4.0, -14.0),
        Color::srgb(0.95, 0.35, 0.25),
    );

    spawn_layout_station(
        commands,
        asset_server,
        registry,
        meshes,
        materials,
        SHUTTLE_BAY_ASSET,
        Transform::from_xyz(0.0, 0.0, -10.0),
        Interactable::vault_objective(),
        Color::srgb(0.5, 0.55, 0.6),
        Vec3::new(3.0, 2.0, 2.0),
    );

    for (i, x) in [-6.0_f32, 6.0].into_iter().enumerate() {
        spawn_layout_station(
            commands,
            asset_server,
            registry,
            meshes,
            materials,
            COOLANT_CONSOLE_ASSET,
            Transform::from_xyz(x, 0.0, -2.0),
            Interactable::coolant_valve(i as u8),
            Color::srgb(0.2, 0.75, 0.85),
            Vec3::new(1.0, 1.2, 0.8),
        );
    }

    for (index, x) in [(-4.0_f32), 4.0].into_iter().enumerate() {
        spawn_layout_station(
            commands,
            asset_server,
            registry,
            meshes,
            materials,
            BREAKER_PANEL_ASSET,
            Transform::from_xyz(x, 0.0, 3.0)
                .with_rotation(Quat::from_rotation_y(std::f32::consts::FRAC_PI_2)),
            Interactable::meltdown_door(index as u8),
            Color::srgb(0.35, 0.55, 0.95),
            Vec3::new(0.8, 1.2, 0.4),
        );
    }

    spawn_delivery_zone(commands, meshes, materials, Vec3::new(0.0, 0.0, 8.0));

    let warn_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.9, 0.2, 0.15),
        emissive: LinearRgba::rgb(0.4, 0.05, 0.05),
        alpha_mode: AlphaMode::Blend,
        ..Default::default()
    });
    commands.spawn((
        RoomLayoutPiece,
        GameplayEntity,
        Mesh3d(meshes.add(Cuboid::new(20.0, 0.05, 20.0))),
        MeshMaterial3d(warn_mat),
        Transform::from_xyz(0.0, 0.02, 0.0),
        Name::new("MeltdownGlow"),
    ));
}

fn mark_layout(commands: &mut Commands, entity: Entity) {
    commands.entity(entity).insert(RoomLayoutPiece);
}

fn spawn_layout_station(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    asset_id: &str,
    transform: Transform,
    interactable: Interactable,
    greybox_color: Color,
    greybox_size: Vec3,
) {
    let entity = spawn_job_station(
        commands,
        asset_server,
        registry,
        meshes,
        materials,
        asset_id,
        transform,
        interactable,
        greybox_color,
        greybox_size,
    );
    mark_layout(commands, entity);
}

fn spawn_sort_chute(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    position: Vec3,
    chute: u8,
    color: Color,
    label: &str,
) {
    let mat = materials.add(StandardMaterial {
        base_color: color,
        emissive: LinearRgba::from(color) * 0.15,
        ..Default::default()
    });
    commands.spawn((
        RoomLayoutPiece,
        GameplayEntity,
        Interactable::sort_chute(chute),
        Mesh3d(meshes.add(Cuboid::new(2.5, 1.5, 2.5))),
        MeshMaterial3d(mat),
        Transform::from_translation(position),
        Name::new(format!("SortChute_{label}")),
    ));
}

fn spawn_delivery_zone(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    position: Vec3,
) {
    let mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.2, 0.85, 0.45),
        emissive: LinearRgba::rgb(0.1, 0.4, 0.2),
        ..Default::default()
    });
    commands.spawn((
        RoomLayoutPiece,
        GameplayEntity,
        Interactable::vault_objective(),
        Mesh3d(meshes.add(Cuboid::new(3.0, 0.15, 3.0))),
        MeshMaterial3d(mat),
        Transform::from_translation(position),
        Name::new("DeliveryZone"),
    ));
}

fn spawn_room_sign(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    label: &str,
    position: Vec3,
    color: Color,
) {
    let mat = materials.add(StandardMaterial {
        base_color: color,
        emissive: LinearRgba::from(color) * 0.2,
        ..Default::default()
    });
    commands.spawn((
        RoomLayoutPiece,
        GameplayEntity,
        Mesh3d(meshes.add(Cuboid::new(8.0, 1.0, 0.3))),
        MeshMaterial3d(mat),
        Transform::from_translation(position),
        Name::new(label.to_string()),
    ));
}
