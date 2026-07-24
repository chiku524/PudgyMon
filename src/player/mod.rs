pub mod accessories;
pub mod animation;
pub mod carry;
pub mod collision;
pub mod freight;
pub mod knockback;
pub mod leaseholder;

pub use accessories::{
    accessory_glb_exists, apply_accessory_choice, apply_slot, AccessoriesPlugin, AccessoryCatalog,
    EquipAccessoryRequest,
};
pub use animation::{
    CrewAnimPlayback, CrewAnimationPlugin, PlayerMotion, PlayCrewEmote, EMOTE_LIBRARY,
    EMOTE_SLOT_COUNT,
};
pub use carry::CarryingFreight;
pub use freight::WorldFreight;
pub use knockback::Knockback;
pub use leaseholder::Leaseholder;

use std::collections::HashMap;

use bevy::input::mouse::{AccumulatedMouseMotion, MouseWheel};
use bevy::prelude::*;
use bevy::window::{CursorGrabMode, CursorOptions, PrimaryWindow};
use bevy_replicon::prelude::*;
use bevy_replicon_renet::{netcode::NetcodeClientTransport, RenetClient};
use serde::{Deserialize, Serialize};

use crate::{
    core::{
        ARENA_BOUNDS, CAMERA_DEFAULT_DISTANCE, CAMERA_MAX_DISTANCE, CAMERA_MIN_DISTANCE,
        MAX_CAMERA_PITCH, MIN_CAMERA_PITCH, PLAYER_DOUBLE_JUMP_VELOCITY, PLAYER_FLOOR_Y,
        PLAYER_GRAVITY, PLAYER_JUMP_VELOCITY, PLAYER_MAX_AIR_JUMPS, PLAYER_SPEED,
        PLAYER_SPRINT_MULTIPLIER,
    },
    flow::AppScreen,
    network::OwnedPlayer,
    world::{GameplayEntity, MainCamera},
};

/// Owner id for the listen-server / offline avatar (not a netcode client).
pub const HOST_OWNER_ID: u64 = 0;

/// Extra yaw on character GLB children so mesh forward matches Bevy −Z.
/// Studio Tripo rigs (water / pink) face +Z; older shared-rig exports face +X.
fn character_mesh_yaw_offset(model_id: &str) -> f32 {
    match model_id {
        // glTF +Z forward → 180° so local +Z aligns with parent −Z (movement).
        "char_pudgy_water_01" | "char_pudgy_pink_01" => std::f32::consts::PI,
        // glTF +X forward → +90° maps +X onto parent −Z.
        _ => std::f32::consts::FRAC_PI_2,
    }
}

pub struct PlayerPlugin;

impl Plugin for PlayerPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ThirdPersonCamera>()
            .init_resource::<freight::FreightCadence>()
            .add_plugins(animation::CrewAnimationPlugin)
            .add_client_event::<SelectCharacterRequest>(Channel::Unordered)
            .add_observer(handle_select_character)
            .add_systems(
                Update,
                (
                    sync_player_visuals,
                    assign_local_player,
                    capture_cursor_when_playing.run_if(in_state(AppScreen::Playing)),
                    toggle_cursor_capture.run_if(in_state(AppScreen::Playing)),
                    camera_mouse_look.run_if(in_state(AppScreen::Playing)),
                    camera_scroll_zoom.run_if(in_state(AppScreen::Playing)),
                    local_movement_input
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(|pause: Option<Res<crate::settings::PauseState>>| {
                            !pause.map(|p| p.paused).unwrap_or(false)
                        }),
                    offline_movement
                        .run_if(in_state(AppScreen::Playing))
                        .run_if(|pause: Option<Res<crate::settings::PauseState>>| {
                            !pause.map(|p| p.paused).unwrap_or(false)
                        })
                        .run_if(resource_exists::<crate::rooms::RoomSpawnPoint>),
                    knockback::apply_knockback_motion
                        .after(offline_movement)
                        .run_if(in_state(AppScreen::Playing)),
                    collision::resolve_player_push
                        .after(knockback::apply_knockback_motion)
                        .run_if(in_state(AppScreen::Playing)),
                    carry::sync_carry_visuals.run_if(in_state(AppScreen::Playing)),
                    // After movement so jumps / walks keep the avatar screen-centered.
                    follow_camera
                        .after(camera_mouse_look)
                        .after(collision::resolve_player_push)
                        .run_if(in_state(AppScreen::Playing)),
                ),
            );
    }
}

#[derive(Resource, Debug, Clone)]
pub struct ThirdPersonCamera {
    pub yaw: f32,
    pub pitch: f32,
    pub distance: f32,
    pub captured: bool,
}

impl Default for ThirdPersonCamera {
    fn default() -> Self {
        Self {
            yaw: 0.0,
            pitch: -0.35,
            distance: CAMERA_DEFAULT_DISTANCE,
            captured: true,
        }
    }
}

#[derive(Component, Serialize, Deserialize, Clone, Copy, Debug, PartialEq, Eq)]
pub struct NetworkPlayer {
    pub slot: u32,
}

/// Netcode [`NetworkId`] that owns this avatar. [`HOST_OWNER_ID`] = local/host.
#[derive(Component, Serialize, Deserialize, Clone, Copy, Debug, PartialEq, Eq)]
pub struct PlayerOwner(pub u64);

#[derive(Component, Serialize, Deserialize, Clone, Debug, Default)]
pub struct PlayerName(pub String);

#[derive(Component, Serialize, Deserialize, Clone, Copy, Debug)]
pub struct PlayerColor(pub [f32; 3]);

/// Detachable accessory loadout — Studio `acc_*` ids parented on shared sockets.
///
/// See `docs/CHARACTERS.md` for socket names and id patterns (`acc_hat_*`, etc.).
#[derive(Serialize, Deserialize, Clone, Debug, Default, PartialEq, Eq)]
pub struct AccessorySlots {
    pub hat: Option<String>,
    pub necklace: Option<String>,
    pub shoes: Option<String>,
    pub back: Option<String>,
    pub face: Option<String>,
    pub hands: Option<String>,
}

/// Visual swap hook for character GLBs. `model_id = None` keeps the capsule / procedural stub.
///
/// Default crew mesh is `char_pudgy_pink_01`. Species skins
/// (e.g. `oceanic_pudgymon_01`) may override `model_id` later via cosmetics, but must
/// obey the Pudgy Character Contract in `docs/CHARACTERS.md` so clips and accessories stay in sync.
#[derive(Component, Serialize, Deserialize, Clone, Debug, Default, PartialEq, Eq)]
pub struct PlayerVisualSpec {
    /// Studio `asset_id` for the equipped character GLB (`char_pudgy_pink_01` / `char_pudgy_stylized_01` or a species skin).
    pub model_id: Option<String>,
    /// Legacy roster index 0–7 (palette / stand-in). Prefer `accessories.hat` once GLBs exist.
    #[serde(default)]
    pub hat_slot: u8,
    /// Equipped accessory asset ids (hat, necklace, shoes, back, face, hands).
    #[serde(default)]
    pub accessories: AccessorySlots,
}

#[derive(Component, Debug, Clone, Copy, Default)]
pub struct LocalPlayer;

/// Procedural Pudgy body part — tinted when cosmetics change.
#[derive(Component, Debug, Clone, Copy, Default)]
pub struct PudgyTintPart;

/// Root of the spawned character mesh (GLB or procedural stub). Cleared on model swap.
#[derive(Component, Debug, Clone, Copy, Default)]
pub struct PlayerVisualRoot;

/// Tracks which crew `model_id` is currently mounted under `PlayerVisualRoot`.
/// Accessory-only edits must not remount the body (that wiped socket attachments).
#[derive(Component, Debug, Clone, PartialEq, Eq)]
pub struct MountedCrewModel(pub Option<String>);

/// Client → server: equip a playable character GLB by Studio `asset_id`.
#[derive(Event, Serialize, Deserialize, Clone, Debug)]
pub struct SelectCharacterRequest {
    pub model_id: String,
}

#[derive(Resource, Default, Debug)]
pub struct PlayerRegistry {
    pub players: HashMap<Entity, Entity>,
    pub local_player: Option<Entity>,
}

#[derive(Event, Serialize, Deserialize, Clone, Copy, Debug)]
pub struct MoveInput {
    pub direction: Vec2,
    pub sprint: bool,
    /// Space just-pressed this frame (jump / double-jump).
    #[serde(default)]
    pub jump: bool,
}

pub fn apply_move_input(
    input: On<FromClient<MoveInput>>,
    owners: Query<&OwnedPlayer>,
    mut players: Query<(&mut Transform, &mut PlayerMotion), With<NetworkPlayer>>,
    time: Res<Time>,
) {
    let Some(client_entity) = input.client_id.entity() else {
        return;
    };

    let Ok(owned) = owners.get(client_entity) else {
        return;
    };

    let Ok((mut transform, mut motion)) = players.get_mut(owned.0) else {
        return;
    };

    apply_player_move(
        &mut transform,
        &mut motion,
        input.direction,
        input.sprint,
        input.jump,
        time.delta_secs(),
    );
}

fn apply_player_move(
    transform: &mut Transform,
    motion: &mut PlayerMotion,
    direction: Vec2,
    sprint: bool,
    jump_pressed: bool,
    dt: f32,
) {
    let direction = Vec3::new(direction.x, 0.0, direction.y);
    if direction.length_squared() <= f32::EPSILON {
        motion.speed = 0.0;
        motion.sprint = false;
    } else {
        let speed = if sprint {
            PLAYER_SPEED * PLAYER_SPRINT_MULTIPLIER
        } else {
            PLAYER_SPEED
        };

        let flat = direction.normalize();
        transform.translation += flat * speed * dt;
        transform.look_to(flat, Vec3::Y);
        motion.speed = speed;
        motion.sprint = sprint;
    }

    if jump_pressed {
        if motion.grounded {
            motion.vertical_velocity = PLAYER_JUMP_VELOCITY;
            motion.grounded = false;
            motion.air_jumps_left = PLAYER_MAX_AIR_JUMPS;
            motion.jump_count = motion.jump_count.wrapping_add(1);
        } else if motion.air_jumps_left > 0 {
            motion.vertical_velocity = PLAYER_DOUBLE_JUMP_VELOCITY;
            motion.air_jumps_left = motion.air_jumps_left.saturating_sub(1);
            motion.jump_count = motion.jump_count.wrapping_add(1);
        }
    }

    if !motion.grounded {
        motion.vertical_velocity -= PLAYER_GRAVITY * dt;
        transform.translation.y += motion.vertical_velocity * dt;
    }

    if transform.translation.y <= PLAYER_FLOOR_Y {
        transform.translation.y = PLAYER_FLOOR_Y;
        if motion.vertical_velocity < 0.0 {
            motion.vertical_velocity = 0.0;
        }
        motion.grounded = true;
        motion.air_jumps_left = PLAYER_MAX_AIR_JUMPS;
    } else {
        motion.grounded = false;
    }

    transform.translation.x = transform.translation.x.clamp(-ARENA_BOUNDS, ARENA_BOUNDS);
    transform.translation.z = transform.translation.z.clamp(-ARENA_BOUNDS, ARENA_BOUNDS);
}

fn capture_cursor_when_playing(
    local_player: Query<(), With<LocalPlayer>>,
    camera: Res<ThirdPersonCamera>,
    mut cursor: Query<&mut CursorOptions, With<PrimaryWindow>>,
) {
    if local_player.is_empty() || !camera.captured {
        return;
    }

    let Ok(mut cursor) = cursor.single_mut() else {
        return;
    };

    if cursor.grab_mode != CursorGrabMode::Locked {
        cursor.grab_mode = CursorGrabMode::Locked;
        cursor.visible = false;
    }
}

fn toggle_cursor_capture(
    keyboard: Res<ButtonInput<KeyCode>>,
    local_player: Query<(), With<LocalPlayer>>,
    mut camera: ResMut<ThirdPersonCamera>,
    mut cursor: Query<&mut CursorOptions, With<PrimaryWindow>>,
) {
    // Backquote frees cursor; Esc is reserved for pause.
    if local_player.is_empty() || !keyboard.just_pressed(KeyCode::Backquote) {
        return;
    }

    camera.captured = !camera.captured;
    let Ok(mut cursor) = cursor.single_mut() else {
        return;
    };

    if camera.captured {
        cursor.grab_mode = CursorGrabMode::Locked;
        cursor.visible = false;
    } else {
        cursor.grab_mode = CursorGrabMode::None;
        cursor.visible = true;
    }
}

fn camera_mouse_look(
    local_player: Query<(), With<LocalPlayer>>,
    motion: Res<AccumulatedMouseMotion>,
    mut camera: ResMut<ThirdPersonCamera>,
    settings: Res<crate::settings::GameSettings>,
) {
    if local_player.is_empty() || !camera.captured {
        return;
    }

    let delta = motion.delta;
    if delta == Vec2::ZERO {
        return;
    }

    camera.yaw -= delta.x * settings.mouse_sensitivity;
    camera.pitch = (camera.pitch - delta.y * settings.mouse_sensitivity)
        .clamp(MIN_CAMERA_PITCH, MAX_CAMERA_PITCH);
}

fn camera_scroll_zoom(
    local_player: Query<(), With<LocalPlayer>>,
    mut scroll: MessageReader<MouseWheel>,
    mut camera: ResMut<ThirdPersonCamera>,
) {
    if local_player.is_empty() {
        return;
    }

    for event in scroll.read() {
        camera.distance = (camera.distance - event.y * 0.5)
            .clamp(CAMERA_MIN_DISTANCE, CAMERA_MAX_DISTANCE);
    }
}

fn camera_relative_direction(keyboard: &ButtonInput<KeyCode>, yaw: f32) -> Vec3 {
    let forward = Vec3::new(-yaw.sin(), 0.0, -yaw.cos());
    let right = Vec3::new(yaw.cos(), 0.0, -yaw.sin());

    let mut direction = Vec3::ZERO;
    if keyboard.pressed(KeyCode::KeyW) {
        direction += forward;
    }
    if keyboard.pressed(KeyCode::KeyS) {
        direction -= forward;
    }
    if keyboard.pressed(KeyCode::KeyA) {
        direction -= right;
    }
    if keyboard.pressed(KeyCode::KeyD) {
        direction += right;
    }

    direction
}

fn local_movement_input(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut commands: Commands,
    camera: Res<ThirdPersonCamera>,
    client: Option<Res<RenetClient>>,
    local_player: Query<(), (With<LocalPlayer>, Without<crate::session_flow::Spectating>)>,
) {
    // Pure clients only — host/offline apply movement directly in `offline_movement`.
    if client.is_none() || local_player.is_empty() {
        return;
    }

    let direction = camera_relative_direction(&keyboard, camera.yaw);
    let sprint = keyboard.pressed(KeyCode::ShiftLeft) || keyboard.pressed(KeyCode::ShiftRight);
    let jump = keyboard.just_pressed(KeyCode::Space);
    let dir = if direction.length_squared() <= f32::EPSILON {
        Vec2::ZERO
    } else {
        let flat = direction.normalize();
        Vec2::new(flat.x, flat.z)
    };
    commands.client_trigger(MoveInput {
        direction: dir,
        sprint: sprint && dir != Vec2::ZERO,
        jump,
    });
}

/// Direct movement for offline greybox and listen-server host (no RenetClient).
pub fn offline_movement(
    keyboard: Res<ButtonInput<KeyCode>>,
    camera: Res<ThirdPersonCamera>,
    mut players: Query<
        (&mut Transform, &mut PlayerMotion),
        (With<LocalPlayer>, Without<crate::session_flow::Spectating>),
    >,
    time: Res<Time>,
    client: Option<Res<RenetClient>>,
) {
    if client.is_some() {
        return;
    }

    let Ok((mut transform, mut motion)) = players.single_mut() else {
        return;
    };

    let direction = camera_relative_direction(&keyboard, camera.yaw);
    let sprint = keyboard.pressed(KeyCode::ShiftLeft) || keyboard.pressed(KeyCode::ShiftRight);
    let jump = keyboard.just_pressed(KeyCode::Space);
    let dir = if direction.length_squared() <= f32::EPSILON {
        Vec2::ZERO
    } else {
        let flat = direction.normalize();
        Vec2::new(flat.x, flat.z)
    };
    apply_player_move(
        &mut transform,
        &mut motion,
        dir,
        sprint && dir != Vec2::ZERO,
        jump,
        time.delta_secs(),
    );
}

fn assign_local_player(
    mut commands: Commands,
    mut registry: ResMut<PlayerRegistry>,
    client: Option<Res<RenetClient>>,
    transport: Option<Res<NetcodeClientTransport>>,
    client_state: Option<Res<State<ClientState>>>,
    players: Query<(Entity, &PlayerOwner), (With<NetworkPlayer>, Without<LocalPlayer>)>,
) {
    if registry.local_player.is_some() || client.is_none() {
        return;
    }

    let Some(client_state) = client_state else {
        return;
    };
    if *client_state.get() != ClientState::Connected {
        return;
    }

    let Some(transport) = transport else {
        return;
    };
    let my_id = transport.client_id();

    if let Some((player, _)) = players.iter().find(|(_, owner)| owner.0 == my_id) {
        commands.entity(player).insert(LocalPlayer);
        registry.local_player = Some(player);
        info!("local player assigned: {player:?} (owner {my_id})");
    }
}

fn handle_select_character(
    request: On<FromClient<SelectCharacterRequest>>,
    mut players: Query<&mut PlayerVisualSpec, With<NetworkPlayer>>,
    owners: Query<&OwnedPlayer>,
) {
    let Some(client_entity) = request.client_id.entity() else {
        return;
    };
    let Ok(owned) = owners.get(client_entity) else {
        return;
    };
    let model_id = request.model_id.trim();
    if model_id.is_empty() || !crate::data::character_glb_exists(model_id) {
        return;
    }
    if let Ok(mut visual) = players.get_mut(owned.0) {
        visual.model_id = Some(model_id.to_string());
    }
}

fn sync_player_visuals(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server: Res<AssetServer>,
    registry: Option<Res<crate::data::StudioRegistry>>,
    players: Query<
        (
            Entity,
            &PlayerColor,
            Option<&PlayerVisualSpec>,
            Option<&Children>,
            Option<&MountedCrewModel>,
        ),
        With<NetworkPlayer>,
    >,
    visual_roots: Query<(), With<PlayerVisualRoot>>,
) {
    for (entity, color, visual, children, mounted) in &players {
        let want_model = visual.and_then(|v| v.model_id.as_deref()).filter(|id| {
            let disk = format!(
                "{}/assets/models/{id}/{id}.glb",
                env!("CARGO_MANIFEST_DIR")
            );
            std::path::Path::new(&disk).is_file()
        });
        let want_key = want_model.map(|s| s.to_string());
        // Remount only when the crew model id changes (or the visual root is missing).
        // Accessory-only PlayerVisualSpec edits must not wipe sockets / restart GLB loads.
        if mounted.is_some_and(|m| m.0 == want_key) {
            let has_visual =
                children.is_some_and(|kids| kids.iter().any(|c| visual_roots.contains(c)));
            if has_visual {
                continue;
            }
        }

        if let Some(children) = children {
            for child in children.iter() {
                if visual_roots.contains(child) {
                    commands.entity(child).despawn();
                }
            }
        }

        commands.entity(entity).insert((
            GameplayEntity,
            Knockback::default(),
            PlayerMotion::default(),
            MountedCrewModel(want_key.clone()),
        ));

        if let Some(model_id) = want_model {
            let scale = registry
                .as_ref()
                .map(|r| r.spawn_scale(model_id))
                .unwrap_or(Vec3::ONE);
            let glb_path = format!("models/{model_id}/{model_id}.glb");
            let scene =
                asset_server.load(bevy::gltf::GltfAssetLabel::Scene(0).from_asset(glb_path.clone()));
            let gltf_handle: Handle<bevy::gltf::Gltf> = asset_server.load(glb_path);
            commands.entity(entity).with_children(|parent| {
                parent
                    .spawn((
                        PlayerVisualRoot,
                        WorldAssetRoot(scene),
                        animation::CrewAnimationSetup {
                            model_id: model_id.to_string(),
                            gltf: gltf_handle,
                        },
                        Transform {
                            translation: Vec3::ZERO,
                            rotation: Quat::from_rotation_y(character_mesh_yaw_offset(model_id)),
                            scale,
                        },
                        Visibility::default(),
                        Name::new(format!("CrewMesh:{model_id}")),
                    ))
                    .observe(animation::on_crew_scene_ready);
            });
            continue;
        }

        // Procedural Pudgy stub when no crew/species GLB is on disk.
        let [r, g, b] = color.0;
        let body_mat = materials.add(StandardMaterial {
            base_color: Color::srgb(r, g, b),
            ..Default::default()
        });
        let eye_mat = materials.add(StandardMaterial {
            base_color: Color::srgb(0.08, 0.08, 0.1),
            ..Default::default()
        });
        let cheek_mat = materials.add(StandardMaterial {
            base_color: Color::srgb((r * 0.7 + 0.3).min(1.0), g * 0.55, b * 0.55),
            ..Default::default()
        });

        commands.entity(entity).with_children(|parent| {
            parent
                .spawn((
                    PlayerVisualRoot,
                    Transform::default(),
                    Visibility::default(),
                    Name::new("PudgyStub"),
                ))
                .with_children(|stub| {
                    stub.spawn((
                        PudgyTintPart,
                        Mesh3d(meshes.add(Sphere::new(0.55))),
                        MeshMaterial3d(body_mat.clone()),
                        Transform::from_xyz(0.0, 0.55, 0.0),
                        Name::new("PudgyBody"),
                    ));
                    stub.spawn((
                        PudgyTintPart,
                        Mesh3d(meshes.add(Sphere::new(0.42))),
                        MeshMaterial3d(body_mat),
                        Transform::from_xyz(0.0, 1.25, 0.05),
                        Name::new("PudgyHead"),
                    ));
                    stub.spawn((
                        Mesh3d(meshes.add(Sphere::new(0.08))),
                        MeshMaterial3d(eye_mat.clone()),
                        Transform::from_xyz(-0.14, 1.32, 0.34),
                        Name::new("PudgyEyeL"),
                    ));
                    stub.spawn((
                        Mesh3d(meshes.add(Sphere::new(0.08))),
                        MeshMaterial3d(eye_mat),
                        Transform::from_xyz(0.14, 1.32, 0.34),
                        Name::new("PudgyEyeR"),
                    ));
                    stub.spawn((
                        Mesh3d(meshes.add(Sphere::new(0.09))),
                        MeshMaterial3d(cheek_mat),
                        Transform::from_xyz(0.0, 1.12, 0.38),
                        Name::new("PudgySnout"),
                    ));
                });
        });
    }
}

fn follow_camera(
    time: Res<Time>,
    camera_state: Res<ThirdPersonCamera>,
    local_player: Query<&Transform, (With<LocalPlayer>, Without<crate::session_flow::Spectating>)>,
    mut camera: Query<&mut Transform, (With<MainCamera>, Without<LocalPlayer>)>,
) {
    let Ok(player) = local_player.single() else {
        return;
    };
    let Ok(mut camera_transform) = camera.single_mut() else {
        return;
    };

    let yaw = camera_state.yaw;
    let pitch = camera_state.pitch;
    let distance = camera_state.distance;

    // Orbit around the character body so they stay framed at screen center,
    // including during exaggerated jumps (tracks full player translation).
    let focus = player.translation + Vec3::Y * 1.15;
    let horizontal = distance * pitch.cos();
    let desired_eye = focus
        + Vec3::new(
            horizontal * yaw.sin(),
            -distance * pitch.sin(),
            horizontal * yaw.cos(),
        );

    // Snap-follow with a tiny smooth so big vertical hops don't stutter,
    // but stay locked enough that the pudgy doesn't drift off-center.
    let t = 1.0 - (-22.0 * time.delta_secs()).exp();
    camera_transform.translation = camera_transform.translation.lerp(desired_eye, t);
    camera_transform.look_at(focus, Vec3::Y);
}
