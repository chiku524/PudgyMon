use std::{
    net::{Ipv4Addr, SocketAddr, UdpSocket},
    time::SystemTime,
};

use bevy::prelude::*;
use bevy_replicon::prelude::*;
use bevy_replicon::shared::backend::connected_client::NetworkId;
use bevy_replicon_renet::{
    netcode::{
        ClientAuthentication, NetcodeClientTransport, NetcodeServerTransport, ServerAuthentication,
        ServerConfig,
    },
    renet::ConnectionConfig,
    RenetChannelsExt, RenetClient, RenetServer,
};

use crate::{
    cli::Cli,
    core::{MAX_PLAYERS, PROTOCOL_ID},
    data::PlayerDefaults,
    jobs::{JobBoard, JobSystem},
    player::{
        CarryingFreight, Knockback, LocalPlayer, NetworkPlayer, PlayerColor, PlayerName, PlayerOwner,
        PlayerRegistry, PlayerVisualSpec, HOST_OWNER_ID,
    },
    world::GameplayEntity,
};

#[derive(Resource, Default)]
pub struct SessionBooted(pub bool);

#[derive(Resource, Default)]
pub struct PlayerSlotCounter(u32);

impl PlayerSlotCounter {
    pub fn next(&mut self) -> u32 {
        let slot = self.0;
        self.0 += 1;
        slot
    }
}

/// Host/join party line for HUD (contractor count + remotes).
#[derive(Resource, Debug, Default, Clone)]
pub struct PartyStatus {
    pub contractors: usize,
    pub remotes: usize,
    pub line: String,
}

pub struct NetworkPlugin;

impl Plugin for NetworkPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<PlayerRegistry>()
            .init_resource::<PlayerSlotCounter>()
            .init_resource::<SessionBooted>()
            .init_resource::<PartyStatus>()
            .replicate::<Transform>()
            .replicate::<NetworkPlayer>()
            .replicate::<PlayerName>()
            .replicate::<PlayerColor>()
            .replicate::<PlayerOwner>()
            .replicate::<PlayerVisualSpec>()
            .replicate::<CarryingFreight>()
            .replicate::<JobBoard>()
            .replicate::<crate::jobs::SmokeJobFlags>()
            .add_client_event::<crate::player::MoveInput>(Channel::Unordered)
            .add_observer(spawn_player_for_client)
            .add_observer(despawn_player_for_client)
            .add_observer(crate::player::apply_move_input)
            .add_systems(Update, (sync_job_board_from_resource, update_party_status));
    }
}

fn update_party_status(
    cli: Res<Cli>,
    clients: Query<(), With<ConnectedClient>>,
    players: Query<(), With<NetworkPlayer>>,
    mut status: ResMut<PartyStatus>,
) {
    let remotes = clients.iter().count();
    let contractors = players.iter().count();
    status.remotes = remotes;
    status.contractors = contractors;
    status.line = match cli.as_ref() {
        Cli::Local => {
            if contractors <= 1 {
                "Solo practice".into()
            } else {
                format!("Solo · {contractors} in bay (bots fill bracket)")
            }
        }
        Cli::Host { port, dedicated, .. } => {
            let mode = if *dedicated { "dedicated" } else { "listen" };
            if remotes == 0 {
                format!("Hosting :{port} ({mode}) · waiting for joiners")
            } else {
                format!("Hosting :{port} ({mode}) · {contractors} contractors ({remotes} remote)")
            }
        }
        Cli::Join { address, port, .. } => {
            format!("Joined {address}:{port} · {contractors} in bay")
        }
    };
}

/// Boot network + local avatar once. Safe to call from Startup (headless/CLI) or title menu.
pub fn boot_session(
    commands: &mut Commands,
    booted: &mut SessionBooted,
    cli: &Cli,
    channels: &RepliconChannels,
    registry: &mut PlayerRegistry,
    slots: &mut PlayerSlotCounter,
    spawn_point: Option<&crate::rooms::RoomSpawnPoint>,
    defaults: &PlayerDefaults,
) -> Result<(), String> {
    if booted.0 {
        return Ok(());
    }

    init_network_backend_inner(commands, cli, channels).map_err(|e| e.to_string())?;

    match cli {
        Cli::Local => {
            let Some(spawn_point) = spawn_point else {
                return Err("RoomSpawnPoint missing — layouts not loaded".into());
            };
            let slot = slots.next();
            let player = spawn_player_entity(
                commands,
                slot,
                spawn_point.lobby,
                PlayerOwner(HOST_OWNER_ID),
                defaults,
            );
            registry.local_player = Some(player);
            commands.entity(player).insert(LocalPlayer);
            info!("authority local player spawned: slot {slot}, entity {player:?}");
        }
        Cli::Host { dedicated, .. } => {
            if *dedicated {
                info!("dedicated host — no local contractor body");
            } else {
                let Some(spawn_point) = spawn_point else {
                    return Err("RoomSpawnPoint missing — layouts not loaded".into());
                };
                let slot = slots.next();
                let player = spawn_player_entity(
                    commands,
                    slot,
                    spawn_point.lobby,
                    PlayerOwner(HOST_OWNER_ID),
                    defaults,
                );
                registry.local_player = Some(player);
                commands.entity(player).insert(LocalPlayer);
                info!("listen-server host spawned: slot {slot}, entity {player:?}");
            }
        }
        Cli::Join { .. } => {}
    }

    booted.0 = true;
    Ok(())
}

pub fn boot_session_at_startup(
    mut commands: Commands,
    mut booted: ResMut<SessionBooted>,
    cli: Res<Cli>,
    screen: Res<State<crate::flow::AppScreen>>,
    channels: Res<RepliconChannels>,
    mut registry: ResMut<PlayerRegistry>,
    mut slots: ResMut<PlayerSlotCounter>,
    spawn_point: Option<Res<crate::rooms::RoomSpawnPoint>>,
    defaults: Res<PlayerDefaults>,
) {
    // Interactive local waits on auth intro (Title) before Nest boot.
    if *screen.get() == crate::flow::AppScreen::Title {
        return;
    }
    if let Err(err) = boot_session(
        &mut commands,
        &mut booted,
        cli.as_ref(),
        channels.as_ref(),
        &mut registry,
        &mut slots,
        spawn_point.as_deref(),
        defaults.as_ref(),
    ) {
        panic!("session boot failed: {err}");
    }
}

fn init_network_backend_inner(
    commands: &mut Commands,
    cli: &Cli,
    channels: &RepliconChannels,
) -> Result {
    match cli.clone() {
        Cli::Local => {
            info!("offline greybox — no network backend");
        }
        Cli::Host { port, .. } => {
            info!("hosting on port {port}");
            let server_channels_config = channels.server_configs();
            let client_channels_config = channels.client_configs();

            let server = RenetServer::new(ConnectionConfig {
                server_channels_config,
                client_channels_config,
                ..Default::default()
            });

            let current_time = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH)?;
            let socket = UdpSocket::bind((Ipv4Addr::UNSPECIFIED, port))?;
            let server_config = ServerConfig {
                current_time,
                max_clients: MAX_PLAYERS,
                protocol_id: PROTOCOL_ID,
                authentication: ServerAuthentication::Unsecure,
                public_addresses: Default::default(),
            };
            let transport = NetcodeServerTransport::new(server_config, socket)?;

            commands.insert_resource(server);
            commands.insert_resource(transport);
        }
        Cli::Join { address, port } => {
            info!("joining {address}:{port}");
            let server_channels_config = channels.server_configs();
            let client_channels_config = channels.client_configs();

            let client = RenetClient::new(ConnectionConfig {
                server_channels_config,
                client_channels_config,
                ..Default::default()
            });

            let current_time = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH)?;
            let client_id = current_time.as_millis() as u64;
            let server_addr = SocketAddr::new(address, port);
            let socket = UdpSocket::bind((Ipv4Addr::UNSPECIFIED, 0))?;
            let authentication = ClientAuthentication::Unsecure {
                client_id,
                protocol_id: PROTOCOL_ID,
                server_addr,
                user_data: None,
            };
            let transport = NetcodeClientTransport::new(current_time, authentication, socket)?;

            commands.insert_resource(client);
            commands.insert_resource(transport);
        }
    }

    Ok(())
}

fn spawn_player_for_client(
    add: On<Add, ConnectedClient>,
    mut commands: Commands,
    mut slots: ResMut<PlayerSlotCounter>,
    network_ids: Query<&NetworkId>,
    spawn_point: Res<crate::rooms::RoomSpawnPoint>,
    defaults: Res<PlayerDefaults>,
) {
    let slot = slots.next();
    let Ok(network_id) = network_ids.get(add.entity) else {
        warn!(
            "ConnectedClient {:?} missing NetworkId — skipping player spawn",
            add.entity
        );
        return;
    };
    let owner_id = network_id.get();
    // Fan out joiners beside the room spawn so they don't stack on the host.
    let position = spawn_point.current + Vec3::new((slot as f32) * 2.5, 0.0, 0.0);
    let player = spawn_player_entity(
        &mut commands,
        slot,
        position,
        PlayerOwner(owner_id),
        defaults.as_ref(),
    );
    commands.entity(add.entity).insert(OwnedPlayer(player));
}

/// Links a connected client entity to its spawned player on the server.
#[derive(Component, Clone, Copy, Debug)]
pub struct OwnedPlayer(pub Entity);

fn despawn_player_for_client(
    remove: On<Remove, ConnectedClient>,
    mut commands: Commands,
    mut registry: ResMut<PlayerRegistry>,
    owners: Query<&OwnedPlayer>,
    names: Query<&PlayerName>,
    mut banner: Option<ResMut<crate::session_flow::NetworkBanner>>,
) {
    if let Ok(owned) = owners.get(remove.entity) {
        let player = owned.0;
        let label = names
            .get(player)
            .map(|n| n.0.clone())
            .unwrap_or_else(|_| "A contractor".into());
        registry.players.remove(&remove.entity);
        if registry.local_player == Some(player) {
            registry.local_player = None;
        }
        commands.entity(player).despawn();
        if let Some(banner) = banner.as_mut() {
            banner.show(format!("{label} disconnected"), 5.5);
        }
    }
}

/// Tear down listen-server / client transport so the title menu can boot a fresh session.
pub fn teardown_session(
    commands: &mut Commands,
    booted: &mut SessionBooted,
    registry: &mut PlayerRegistry,
    slots: &mut PlayerSlotCounter,
    players: &Query<Entity, With<NetworkPlayer>>,
) {
    for entity in players.iter() {
        commands.entity(entity).despawn();
    }
    registry.local_player = None;
    registry.players.clear();
    slots.0 = 0;
    booted.0 = false;

    commands.remove_resource::<RenetServer>();
    commands.remove_resource::<NetcodeServerTransport>();
    commands.remove_resource::<RenetClient>();
    commands.remove_resource::<NetcodeClientTransport>();
    info!("session torn down — ready for menu re-boot");
}

fn spawn_player_entity(
    commands: &mut Commands,
    slot: u32,
    position: Vec3,
    owner: PlayerOwner,
    defaults: &PlayerDefaults,
) -> Entity {
    let color = player_color_for_slot(slot);
    let name = if owner.0 == HOST_OWNER_ID && slot == 0 {
        "You".into()
    } else {
        format!("Player{slot}")
    };
    commands
        .spawn((
            GameplayEntity,
            NetworkPlayer { slot },
            PlayerName(name),
            PlayerColor(color),
            PlayerVisualSpec {
                model_id: defaults.resolved_crew_model(),
                hat_slot: (slot % 8) as u8,
                accessories: Default::default(),
            },
            Knockback::default(),
            owner,
            Transform::from_translation(position),
            Replicated,
            Visibility::default(),
        ))
        .id()
}

fn player_color_for_slot(slot: u32) -> [f32; 3] {
    const PALETTE: [[f32; 3]; 8] = [
        [0.95, 0.35, 0.35],
        [0.35, 0.75, 0.95],
        [0.45, 0.90, 0.45],
        [0.95, 0.85, 0.35],
        [0.80, 0.45, 0.95],
        [0.95, 0.55, 0.25],
        [0.35, 0.90, 0.85],
        [0.95, 0.45, 0.70],
    ];
    PALETTE[slot as usize % PALETTE.len()]
}

fn sync_job_board_from_resource(
    jobs: Option<Res<JobSystem>>,
    mut boards: Query<(&mut JobBoard, &mut crate::jobs::SmokeJobFlags)>,
) {
    let Some(jobs) = jobs else {
        return;
    };
    for (mut board, mut flags) in &mut boards {
        board.sync_from(&jobs);
        *flags = crate::jobs::SmokeJobFlags::sync_from(&jobs);
    }
}

pub fn setup_job_board(mut commands: Commands, jobs: Res<JobSystem>) {
    let mut board = JobBoard::default();
    board.sync_from(&jobs);
    let flags = crate::jobs::SmokeJobFlags::sync_from(&jobs);
    commands.spawn((
        GameplayEntity,
        board,
        flags,
        Replicated,
        Name::new("JobBoard"),
    ));
}
