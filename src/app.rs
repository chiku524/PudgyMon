use bevy::prelude::*;
use bevy::render::{
    settings::{Backends, RenderCreation, WgpuSettings},
    RenderPlugin,
};
use bevy::window::{EnabledButtons, MonitorSelection, WindowMode};
use bevy_replicon::prelude::*;
use bevy_replicon_renet::RepliconRenetPlugins;

use crate::{
    account::AccountPlugin,
    assets::{load_studio_registry, AssetsPlugin},
    audio_fx::AudioFxPlugin,
    boing::BoingPlugin,
    challenges::ChallengesPlugin,
    cli::Cli,
    cosmetics::CosmeticsPlugin,
    data::load_player_defaults,
    hub::HubPlugin,
    juice::JuicePlugin,
    map_editor::MapEditorPlugin,
    maps::MapsPlugin,
    network::{boot_session_at_startup, NetworkPlugin},
    party::PartyPlugin,
    player::PlayerPlugin,
    season::SeasonPlugin,
    session_flow::SessionFlowPlugin,
    settings::SettingsPlugin,
    smoke::SmokeAutomationPlugin,
    stages::StagesPlugin,
    ui::UiPlugin,
    world::{spawn_camera, WorldPlugin},
};

/// Shared app builder for interactive and headless smoke binaries.
pub fn build_app(headless: bool, enable_smoke: bool) -> App {
    crate::logging::install_crash_hook();

    let asset_root = format!("{}/assets", env!("CARGO_MANIFEST_DIR"));
    let mut app = App::new();
    app.init_resource::<Cli>();

    let window_plugin = if headless {
        WindowPlugin {
            primary_window: Some(Window {
                title: crate::brand::smoke_window_title(),
                resolution: (1u32, 1u32).into(),
                visible: false,
                ..default()
            }),
            ..default()
        }
    } else {
        WindowPlugin {
            primary_window: Some(Window {
                title: crate::brand::window_title(),
                mode: WindowMode::BorderlessFullscreen(MonitorSelection::Current),
                decorations: false,
                resizable: false,
                enabled_buttons: EnabledButtons {
                    minimize: false,
                    maximize: false,
                    close: false,
                },
                ..default()
            }),
            ..default()
        }
    };

    let default_plugins = if headless {
        // CI runners have no discrete GPU — prefer GL (llvmpipe under Xvfb) over Vulkan.
        DefaultPlugins
            .set(AssetPlugin {
                file_path: asset_root,
                ..default()
            })
            .set(window_plugin)
            .set(RenderPlugin {
                render_creation: RenderCreation::Automatic(Box::new(WgpuSettings {
                    // Prefer software adapters (llvmpipe / lavapipe) on GPU-less CI runners.
                    force_fallback_adapter: true,
                    backends: Some(Backends::VULKAN | Backends::GL),
                    ..default()
                })),
                ..default()
            })
    } else {
        DefaultPlugins
            .set(AssetPlugin {
                file_path: asset_root,
                ..default()
            })
            .set(window_plugin)
    };

    app.add_plugins((default_plugins, RepliconPlugins, RepliconRenetPlugins));
    let initial = {
        let cli = app.world().resource::<Cli>().clone();
        crate::flow::initial_screen(headless, enable_smoke, &cli)
    };
    app.insert_state(initial);

    app.add_plugins((
        AssetsPlugin,
        WorldPlugin,
        NetworkPlugin,
        PlayerPlugin,
        crate::player::AccessoriesPlugin,
        PartyPlugin,
        StagesPlugin,
        SeasonPlugin,
        CosmeticsPlugin,
    ));
    app.add_plugins((
        MapsPlugin,
        HubPlugin,
        MapEditorPlugin,
        ChallengesPlugin,
        AccountPlugin,
        BoingPlugin,
        JuicePlugin,
        AudioFxPlugin,
        SettingsPlugin,
        SessionFlowPlugin,
    ));

    if !headless {
        app.add_plugins(UiPlugin);
    }

    app.add_systems(
        Startup,
        (
            load_studio_registry,
            load_player_defaults,
            ensure_party_spawn_point,
            spawn_camera,
            spawn_party_arena,
            boot_session_at_startup,
        )
            .chain(),
    );

    if enable_smoke {
        app.add_plugins(SmokeAutomationPlugin);
    }

    app
}

fn ensure_party_spawn_point(mut commands: Commands, spawn: Res<crate::party::PartySpawn>) {
    commands.insert_resource(crate::rooms::RoomSpawnPoint {
        lobby: spawn.hub,
        current: spawn.hub,
    });
}

fn spawn_party_arena(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    // Open-world Nest island — no walls. Movement is softly clamped to the
    // WORLD_BOUNDS circle at the beach line (see core::clamp_to_island).
    let island_radius = crate::core::WORLD_BOUNDS + 1.5;

    // Grass island top.
    commands.spawn((
        crate::world::ArenaPiece,
        Mesh3d(meshes.add(Cylinder::new(island_radius, 0.2))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(0.16, 0.28, 0.26),
            ..Default::default()
        })),
        Transform::from_xyz(0.0, -0.1, 0.0),
        Name::new("NestIsland"),
    ));
    // Sandy beach rim sloping to the water.
    commands.spawn((
        crate::world::ArenaPiece,
        Mesh3d(meshes.add(Cylinder::new(island_radius + 6.0, 0.12))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(0.86, 0.76, 0.55),
            ..Default::default()
        })),
        Transform::from_xyz(0.0, -0.22, 0.0),
        Name::new("NestBeach"),
    ));
    // Endless ocean plane to the horizon.
    commands.spawn((
        crate::world::ArenaPiece,
        Mesh3d(meshes.add(Cuboid::new(600.0, 0.1, 600.0))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(0.16, 0.42, 0.62),
            emissive: LinearRgba::rgb(0.01, 0.05, 0.09),
            ..Default::default()
        })),
        Transform::from_xyz(0.0, -0.42, 0.0),
        Name::new("NestOcean"),
    ));

    // Distant islets for horizon interest (outside the playable circle).
    let islet_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.24, 0.36, 0.3),
        ..Default::default()
    });
    let islet_mesh = meshes.add(Sphere::new(1.0));
    for (i, (angle_deg, dist, scale)) in [
        (25.0_f32, 120.0_f32, 9.0_f32),
        (110.0, 145.0, 14.0),
        (185.0, 130.0, 7.0),
        (250.0, 155.0, 12.0),
        (320.0, 125.0, 8.0),
    ]
    .into_iter()
    .enumerate()
    {
        let a = angle_deg.to_radians();
        commands.spawn((
            crate::world::ArenaPiece,
            Mesh3d(islet_mesh.clone()),
            MeshMaterial3d(islet_mat.clone()),
            Transform::from_xyz(a.cos() * dist, -scale * 0.55, a.sin() * dist)
                .with_scale(Vec3::new(scale, scale * 0.6, scale)),
            Name::new(format!("HorizonIslet_{i}")),
        ));
    }
}
