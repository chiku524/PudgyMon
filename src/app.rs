use bevy::prelude::*;
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
    flow::AppScreen,
    hub::HubPlugin,
    juice::JuicePlugin,
    map_editor::MapEditorPlugin,
    maps::MapsPlugin,
    network::{boot_session_at_startup, NetworkPlugin},
    party::PartyPlugin,
    player::{offline_movement, PlayerPlugin},
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

    let default_plugins = DefaultPlugins
        .set(AssetPlugin {
            file_path: asset_root,
            ..default()
        })
        .set(window_plugin);

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
    )
    .add_systems(
        Update,
        offline_movement
            .run_if(resource_exists::<crate::rooms::RoomSpawnPoint>)
            .run_if(in_state(AppScreen::Playing))
            .run_if(not_paused),
    );

    if enable_smoke {
        app.add_plugins(SmokeAutomationPlugin);
    }

    app
}

fn not_paused(pause: Option<Res<crate::settings::PauseState>>) -> bool {
    !pause.map(|p| p.paused).unwrap_or(false)
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
    // Nest playground floor + soft coral walls (PudgyMon greybox).
    // Sized for spacious hub + room for future pads / props (~72×72).
    let floor_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.16, 0.28, 0.26),
        ..Default::default()
    });
    let wall_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.92, 0.45, 0.38),
        ..Default::default()
    });
    commands.spawn((
        crate::world::ArenaPiece,
        Mesh3d(meshes.add(Cuboid::new(72.0, 0.2, 72.0))),
        MeshMaterial3d(floor_mat),
        Transform::from_xyz(0.0, -0.1, 0.0),
        Name::new("NestFloor"),
    ));
    for (name, pos, size) in [
        ("WallL", Vec3::new(-36.0, 2.0, 0.0), Vec3::new(0.4, 4.0, 72.0)),
        ("WallR", Vec3::new(36.0, 2.0, 0.0), Vec3::new(0.4, 4.0, 72.0)),
        ("WallN", Vec3::new(0.0, 2.0, -36.0), Vec3::new(72.0, 4.0, 0.4)),
        ("WallS", Vec3::new(0.0, 2.0, 36.0), Vec3::new(72.0, 4.0, 0.4)),
    ] {
        commands.spawn((
            crate::world::ArenaPiece,
            Mesh3d(meshes.add(Cuboid::new(size.x, size.y, size.z))),
            MeshMaterial3d(wall_mat.clone()),
            Transform::from_translation(pos),
            Name::new(name),
        ));
    }
}
