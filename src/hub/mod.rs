//! The Nest — walk, show Pudgy skins, pick a mini-game.

use bevy::prelude::*;
use bevy_replicon::prelude::*;

use crate::{
    assets::{spawn_studio_prop, studio_asset_exists},
    cosmetics::{CosmeticsCatalog, EquippedCosmetic},
    data::StudioRegistry,
    flow::AppScreen,
    maps::{ActiveStageMaps, PartyPack},
    party::{PartyDirector, PartyPhase, PartyPlan, PartySpawn, StageKind},
    player::{LocalPlayer, PlayerColor, PudgyTintPart},
    season::SeasonLedger,
    world::GameplayEntity,
};

/// Queued by standing on a mode pad and pressing E / Enter.
#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ModeQueued(pub Option<PartyPlan>);

#[derive(Component, Debug, Clone, Copy)]
pub struct ModePad {
    pub plan: PartyPlan,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NestAction {
    OpenEditor,
    BrowseMaps,
}

#[derive(Component, Debug, Clone, Copy)]
pub struct NestUtilityPad {
    pub action: NestAction,
}

#[derive(Component)]
pub struct HubProp;

#[derive(Component)]
pub struct SkinShowcase {
    pub skin_id: String,
}

#[derive(Resource, Debug, Default)]
pub struct HubPrompt {
    pub line: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum EditLayer {
    #[default]
    Race,
    Vibe,
    Shooter,
}

impl EditLayer {
    pub fn label(self) -> &'static str {
        match self {
            Self::Race => "Race",
            Self::Vibe => "Vibe",
            Self::Shooter => "Shooter",
        }
    }

    pub fn next(self) -> Self {
        match self {
            Self::Race => Self::Vibe,
            Self::Vibe => Self::Shooter,
            Self::Shooter => Self::Race,
        }
    }
}

/// Shared with map editor — lives here to avoid hub ↔ editor module cycles.
#[derive(Resource, Debug, Default)]
pub struct EditorMode {
    pub active: bool,
    pub pack: PartyPack,
    pub layer: EditLayer,
    pub status: String,
    pub deco_index: usize,
}

pub fn editor_is_active(editor: Res<EditorMode>) -> bool {
    editor.active
}

pub struct HubPlugin;

impl Plugin for HubPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ModeQueued>()
            .init_resource::<HubPrompt>()
            .init_resource::<EditorMode>()
            .add_systems(Startup, spawn_social_hub)
            .add_systems(
                Update,
                (
                    sync_hub_pad_visibility,
                    detect_mode_pad_prompt,
                    activate_mode_pad,
                    apply_equipped_skin_tint,
                    pulse_showcase_lights,
                )
                    .run_if(in_state(AppScreen::Playing)),
            );
    }
}

fn spawn_mode_pad_showcase(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    pad_name: &str,
    pad_pos: Vec3,
) {
    let props: &[(&str, Vec3, f32)] = match pad_name {
        "Race" => &[
            ("prop_race_cone_01", Vec3::new(-3.5, 0.0, 1.5), 0.0),
            ("prop_race_cone_01", Vec3::new(3.5, 0.0, 1.5), 0.0),
            ("prop_race_banner_01", Vec3::new(0.0, 0.0, 4.0), 0.0),
            ("env_race_ramp_01", Vec3::new(-5.5, 0.0, -1.0), 90.0),
        ],
        "Vibe" => &[
            ("prop_vibe_orb_01", Vec3::new(-3.0, 0.0, 2.0), 0.0),
            ("prop_vibe_orb_01", Vec3::new(3.0, 0.0, 2.0), 0.0),
            ("prop_vibe_flower_01", Vec3::new(-4.5, 0.0, -1.5), 25.0),
            ("prop_vibe_crystal_01", Vec3::new(4.5, 0.0, -1.5), -25.0),
        ],
        "Shooter" => &[
            ("prop_cover_block_01", Vec3::new(-3.5, 0.0, 2.0), 15.0),
            ("prop_target_star_01", Vec3::new(3.5, 0.0, 2.0), -20.0),
            ("prop_blaster_toy_01", Vec3::new(0.0, 0.0, 4.0), 180.0),
        ],
        "PartySaga" => &[
            ("prop_race_cone_01", Vec3::new(-4.0, 0.0, 2.5), 0.0),
            ("prop_vibe_orb_01", Vec3::new(0.0, 0.0, 3.5), 0.0),
            ("prop_target_star_01", Vec3::new(4.0, 0.0, 2.5), 0.0),
        ],
        _ => &[],
    };
    for (i, (asset_id, offset, yaw_deg)) in props.iter().enumerate() {
        if !studio_asset_exists(registry, asset_id) {
            continue;
        }
        let tf = Transform::from_translation(pad_pos + *offset)
            .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
        let _ = spawn_studio_prop(
            commands,
            asset_server,
            registry,
            asset_id,
            tf,
            (
                HubProp,
                Name::new(format!("PadShowcase_{pad_name}_{i}_{asset_id}")),
            ),
        );
    }
}

fn spawn_social_hub(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    catalog: Res<CosmeticsCatalog>,
    spawn: Res<PartySpawn>,
    asset_server: Res<AssetServer>,
    registry: Option<Res<StudioRegistry>>,
) {
    let hub = spawn.hub;
    let registry = registry.as_deref();

    // Nest egg centerpiece
    let egg_tf = Transform::from_translation(hub + Vec3::new(0.0, 0.0, -4.0));
    if registry.is_some_and(|r| studio_asset_exists(r, "env_nest_egg_01")) {
        let _ = spawn_studio_prop(
            &mut commands,
            &asset_server,
            registry.unwrap(),
            "env_nest_egg_01",
            egg_tf,
            (HubProp, Name::new("NestEgg")),
        );
    } else {
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(meshes.add(Sphere::new(1.8))),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::srgb(0.95, 0.72, 0.45),
                emissive: LinearRgba::rgb(0.4, 0.2, 0.05),
                ..Default::default()
            })),
            Transform::from_translation(hub + Vec3::new(0.0, 1.5, -4.0)),
            Name::new("NestEgg"),
        ));
    }
    commands.spawn((
        HubProp,
        GameplayEntity,
        Mesh3d(meshes.add(Cylinder::new(5.5, 0.18))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(0.2, 0.38, 0.32),
            emissive: LinearRgba::rgb(0.08, 0.2, 0.14),
            ..Default::default()
        })),
        Transform::from_translation(hub + Vec3::new(0.0, 0.05, -4.0)),
        Name::new("NestPlaza"),
    ));

    // Soft benches around the egg.
    for (i, offset) in [
        Vec3::new(-8.0, 0.0, 1.0),
        Vec3::new(8.0, 0.0, 1.0),
        Vec3::new(0.0, 0.0, 12.0),
    ]
    .into_iter()
    .enumerate()
    {
        let tf = Transform::from_translation(hub + offset);
        if registry.is_some_and(|r| studio_asset_exists(r, "env_nest_bench_01")) {
            let _ = spawn_studio_prop(
                &mut commands,
                &asset_server,
                registry.unwrap(),
                "env_nest_bench_01",
                tf,
                (HubProp, Name::new(format!("NestBench_{i}"))),
            );
        } else {
            commands.spawn((
                HubProp,
                GameplayEntity,
                Mesh3d(meshes.add(Cuboid::new(2.8, 0.35, 0.8))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(0.85, 0.55, 0.35),
                    ..Default::default()
                })),
                Transform::from_translation(hub + offset + Vec3::Y * 0.35),
                Name::new(format!("NestBench_{i}")),
            ));
        }
    }

    // Ambient Nest NPCs (full figures only — accessory GLBs are wearables now).
    let nest_npcs: [(&str, Vec3, f32); 5] = [
        ("npc_nest_pink_01", Vec3::new(-16.0, 0.0, 2.0), 70.0),
        ("npc_nest_crew_a_01", Vec3::new(16.0, 0.0, 2.0), -70.0),
        ("npc_nest_crew_b_01", Vec3::new(-14.0, 0.0, 10.0), 120.0),
        ("npc_nest_stylized_a_01", Vec3::new(14.0, 0.0, 10.0), -120.0),
        ("npc_nest_monster_01", Vec3::new(0.0, 0.0, 14.0), 180.0),
    ];
    for (i, (asset_id, offset, yaw_deg)) in nest_npcs.into_iter().enumerate() {
        if !registry.is_some_and(|r| studio_asset_exists(r, asset_id)) {
            continue;
        }
        let tf = Transform::from_translation(hub + offset)
            .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
        let _ = spawn_studio_prop(
            &mut commands,
            &asset_server,
            registry.unwrap(),
            asset_id,
            tf,
            (HubProp, Name::new(format!("NestNpc_{i}_{asset_id}"))),
        );
    }

    // Vibe mushrooms — outer ring
    for (i, pos) in [
        Vec3::new(-22.0, 0.0, -16.0),
        Vec3::new(22.0, 0.0, -16.0),
        Vec3::new(-20.0, 0.0, 16.0),
        Vec3::new(20.0, 0.0, 16.0),
        Vec3::new(-28.0, 0.0, 2.0),
        Vec3::new(28.0, 0.0, 2.0),
    ]
    .into_iter()
    .enumerate()
    {
        let tf = Transform::from_translation(hub + pos);
        if registry.is_some_and(|r| studio_asset_exists(r, "prop_vibe_mushroom_01")) {
            let _ = spawn_studio_prop(
                &mut commands,
                &asset_server,
                registry.unwrap(),
                "prop_vibe_mushroom_01",
                tf,
                (HubProp, Name::new(format!("VibeMushroom_{i}"))),
            );
        } else {
            let stem = materials.add(StandardMaterial {
                base_color: Color::srgb(0.35, 0.75, 0.55),
                ..Default::default()
            });
            let cap_col = if i % 2 == 0 {
                Color::srgb(1.0, 0.45, 0.4)
            } else {
                Color::srgb(0.45, 0.85, 1.0)
            };
            commands.spawn((
                HubProp,
                GameplayEntity,
                Mesh3d(meshes.add(Cylinder::new(0.25, 1.6))),
                MeshMaterial3d(stem),
                Transform::from_translation(hub + pos + Vec3::Y * 1.2),
                Name::new(format!("VibeStem_{i}")),
            ));
            commands.spawn((
                HubProp,
                GameplayEntity,
                Mesh3d(meshes.add(Sphere::new(0.85))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: cap_col,
                    emissive: LinearRgba::rgb(0.3, 0.15, 0.1),
                    unlit: true,
                    ..Default::default()
                })),
                Transform::from_translation(hub + pos + Vec3::Y * 2.3),
                Name::new(format!("VibeCap_{i}")),
            ));
        }
    }

    let pads: [(PartyPlan, Vec3, [f32; 3], &str, &str); 4] = [
        (
            PartyPlan::Single(StageKind::Race),
            Vec3::new(-16.0, 0.0, -12.0),
            [0.2, 0.85, 1.0],
            "Race",
            "env_pad_race_01",
        ),
        (
            PartyPlan::Single(StageKind::Vibe),
            Vec3::new(0.0, 0.0, -20.0),
            [1.0, 0.85, 0.2],
            "Vibe",
            "env_pad_vibe_01",
        ),
        (
            PartyPlan::Single(StageKind::Shooter),
            Vec3::new(16.0, 0.0, -12.0),
            [1.0, 0.4, 0.55],
            "Shooter",
            "env_pad_shooter_01",
        ),
        (
            PartyPlan::FullParty,
            Vec3::new(0.0, 0.0, 8.0),
            [0.55, 1.0, 0.45],
            "PartySaga",
            "env_pad_party_01",
        ),
    ];

    for (plan, offset, [r, g, b], name, asset_id) in pads {
        let pos = hub + offset;
        let tf = Transform::from_translation(pos);
        if registry.is_some_and(|reg| studio_asset_exists(reg, asset_id)) {
            if let Some(entity) = spawn_studio_prop(
                &mut commands,
                &asset_server,
                registry.unwrap(),
                asset_id,
                tf,
                (HubProp, ModePad { plan }, Name::new(format!("ModePad_{name}"))),
            ) {
                let _ = entity;
            }
        } else {
            commands.spawn((
                HubProp,
                ModePad { plan },
                GameplayEntity,
                Mesh3d(meshes.add(Cylinder::new(2.8, 0.25))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(r, g, b),
                    emissive: LinearRgba::rgb(r * 1.4, g * 1.4, b * 1.4),
                    unlit: true,
                    ..Default::default()
                })),
                Transform::from_translation(pos + Vec3::Y * 0.12),
                Name::new(format!("ModePad_{name}")),
            ));
        }
        // Soft arch / checkpoint marker behind pad when available
        let sign_pos = pos + Vec3::new(0.0, 0.0, -3.2);
        if name == "Race"
            && registry.is_some_and(|reg| studio_asset_exists(reg, "prop_race_checkpoint_01"))
        {
            let _ = spawn_studio_prop(
                &mut commands,
                &asset_server,
                registry.unwrap(),
                "prop_race_checkpoint_01",
                Transform::from_translation(sign_pos),
                (HubProp, Name::new(format!("ModeSign_{name}"))),
            );
        } else {
            commands.spawn((
                HubProp,
                GameplayEntity,
                Mesh3d(meshes.add(Cuboid::new(3.2, 0.25, 0.25))),
                MeshMaterial3d(materials.add(StandardMaterial {
                    base_color: Color::srgb(r, g, b),
                    emissive: LinearRgba::rgb(r, g, b),
                    unlit: true,
                    ..Default::default()
                })),
                Transform::from_translation(sign_pos + Vec3::Y * 2.2),
                Name::new(format!("ModeSign_{name}")),
            ));
        }

        // Stage-prop showcases around each mode pad (Party Saga preview).
        if let Some(reg) = registry {
            spawn_mode_pad_showcase(
                &mut commands,
                &asset_server,
                reg,
                name,
                pos,
            );
        }
    }

    // Extra Nest décor ring — leftover stage props for Party Saga flavor.
    if let Some(reg) = registry {
        let deco: [(&str, Vec3, f32); 8] = [
            ("prop_race_banner_01", Vec3::new(-16.0, 0.0, -16.0), 20.0),
            ("env_race_ramp_01", Vec3::new(-22.0, 0.0, -10.0), 90.0),
            ("prop_vibe_flower_01", Vec3::new(6.0, 0.0, -24.0), -30.0),
            ("prop_vibe_crystal_01", Vec3::new(-6.0, 0.0, -24.0), 30.0),
            ("prop_vibe_orb_01", Vec3::new(0.0, 0.0, -26.0), 0.0),
            ("prop_target_star_01", Vec3::new(20.0, 0.0, -14.0), -45.0),
            ("prop_cover_block_01", Vec3::new(18.0, 0.0, -8.0), 15.0),
            ("prop_blaster_toy_01", Vec3::new(14.0, 0.0, -16.0), -90.0),
        ];
        for (i, (asset_id, offset, yaw_deg)) in deco.into_iter().enumerate() {
            if !studio_asset_exists(reg, asset_id) {
                continue;
            }
            let tf = Transform::from_translation(hub + offset)
                .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
            let _ = spawn_studio_prop(
                &mut commands,
                &asset_server,
                reg,
                asset_id,
                tf,
                (HubProp, Name::new(format!("NestDeco_{i}_{asset_id}"))),
            );
        }
    }

    // Map creator / browser utility pads — south wing, room between them.
    let utilities: [(NestAction, Vec3, [f32; 3], &str); 2] = [
        (
            NestAction::OpenEditor,
            Vec3::new(-12.0, 0.12, 16.0),
            [0.95, 0.65, 0.25],
            "CreateMap",
        ),
        (
            NestAction::BrowseMaps,
            Vec3::new(12.0, 0.12, 16.0),
            [0.65, 0.45, 1.0],
            "MyMaps",
        ),
    ];
    for (action, offset, [r, g, b], name) in utilities {
        let pos = hub + offset;
        commands.spawn((
            HubProp,
            NestUtilityPad { action },
            GameplayEntity,
            Mesh3d(meshes.add(Cylinder::new(2.6, 0.28))),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::srgb(r, g, b),
                emissive: LinearRgba::rgb(r * 1.2, g * 1.2, b * 1.2),
                unlit: true,
                ..Default::default()
            })),
            Transform::from_translation(pos),
            Name::new(format!("UtilityPad_{name}")),
        ));
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(meshes.add(Cuboid::new(2.8, 0.2, 0.2))),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::srgb(r, g, b),
                unlit: true,
                ..Default::default()
            })),
            Transform::from_translation(pos + Vec3::new(0.0, 2.0, -2.6)),
            Name::new(format!("UtilitySign_{name}")),
        ));
    }

    // Skin showcase ring — round Pudgy mannequins.
    for (i, item) in catalog.items.iter().enumerate() {
        let angle = i as f32 * 1.05;
        let pos = hub + Vec3::new(angle.cos() * 20.0, 0.55, angle.sin() * 20.0 + 4.0);
        let [r, g, b] = item.tint;
        let mat = materials.add(StandardMaterial {
            base_color: Color::srgb(r, g, b),
            emissive: LinearRgba::rgb(r * 0.4, g * 0.4, b * 0.4),
            ..Default::default()
        });
        commands
            .spawn((
                HubProp,
                SkinShowcase {
                    skin_id: item.id.clone(),
                },
                GameplayEntity,
                Transform::from_translation(pos),
                Visibility::default(),
                Name::new(format!("Showcase_{}", item.id)),
            ))
            .with_children(|parent| {
                parent.spawn((
                    Mesh3d(meshes.add(Sphere::new(0.5))),
                    MeshMaterial3d(mat.clone()),
                    Transform::from_xyz(0.0, 0.0, 0.0),
                ));
                parent.spawn((
                    Mesh3d(meshes.add(Sphere::new(0.36))),
                    MeshMaterial3d(mat),
                    Transform::from_xyz(0.0, 0.62, 0.04),
                ));
            });
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(meshes.add(Cylinder::new(0.7, 0.2))),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::srgb(0.18, 0.28, 0.24),
                ..Default::default()
            })),
            Transform::from_translation(pos - Vec3::Y * 0.55),
            Name::new(format!("ShowcaseBase_{}", item.id)),
        ));
    }
}

fn sync_hub_pad_visibility(
    director: Res<PartyDirector>,
    mut pads: Query<&mut Visibility, With<HubProp>>,
) {
    let show = director.phase == PartyPhase::Hub;
    let vis = if show {
        Visibility::Visible
    } else {
        Visibility::Hidden
    };
    for mut v in &mut pads {
        *v = vis;
    }
}

fn detect_mode_pad_prompt(
    director: Res<PartyDirector>,
    editor: Res<EditorMode>,
    local: Query<&Transform, With<LocalPlayer>>,
    pads: Query<(&ModePad, &Transform)>,
    utilities: Query<(&NestUtilityPad, &Transform)>,
    ledger: Res<SeasonLedger>,
    equipped: Res<EquippedCosmetic>,
    mut prompt: ResMut<HubPrompt>,
) {
    if editor.active {
        return;
    }
    if director.phase != PartyPhase::Hub {
        prompt.line.clear();
        return;
    }
    let Ok(player) = local.single() else {
        prompt.line = "Hatching into The Nest…".into();
        return;
    };

    for (pad, tf) in &utilities {
        if player.translation.distance(tf.translation) < 2.8 {
            prompt.line = match pad.action {
                NestAction::OpenEditor => {
                    "E / Enter — open Race Map Creator".into()
                }
                NestAction::BrowseMaps => {
                    "[ ] cycle maps · E play selected custom/official Race".into()
                }
            };
            return;
        }
    }

    let mut nearest: Option<(f32, PartyPlan)> = None;
    for (pad, tf) in &pads {
        let d = player.translation.distance(tf.translation);
        if d < 2.8 && nearest.map(|(bd, _)| d < bd).unwrap_or(true) {
            nearest = Some((d, pad.plan));
        }
    }

    if let Some((_, plan)) = nearest {
        prompt.line = format!(
            "E / Enter — start {}  ·  Skin {}  ·  Season {} pts",
            plan.label(),
            equipped.id,
            ledger.points
        );
    } else {
        prompt.line = format!(
            "The Nest — mode pads · Create Map · My Maps · C skin ({}) · Season {} pts",
            equipped.id, ledger.points
        );
    }
}

fn activate_mode_pad(
    keyboard: Res<ButtonInput<KeyCode>>,
    director: Res<PartyDirector>,
    editor: Res<EditorMode>,
    local: Query<&Transform, With<LocalPlayer>>,
    pads: Query<(&ModePad, &Transform)>,
    utilities: Query<&Transform, With<NestUtilityPad>>,
    mut queued: ResMut<ModeQueued>,
    mut active: ResMut<ActiveStageMaps>,
    mut commands: Commands,
    server: Option<Res<bevy_replicon_renet::RenetServer>>,
    client: Option<Res<bevy_replicon_renet::RenetClient>>,
) {
    if editor.active || director.phase != PartyPhase::Hub {
        return;
    }
    if !(keyboard.just_pressed(KeyCode::KeyE)
        || keyboard.just_pressed(KeyCode::Enter)
        || keyboard.just_pressed(KeyCode::NumpadEnter))
    {
        return;
    }
    let Ok(player) = local.single() else {
        return;
    };
    if utilities
        .iter()
        .any(|tf| player.translation.distance(tf.translation) < 2.8)
    {
        return;
    }
    let mut best: Option<(f32, PartyPlan)> = None;
    for (pad, tf) in &pads {
        let d = player.translation.distance(tf.translation);
        if d < 2.8 && best.map(|(bd, _)| d < bd).unwrap_or(true) {
            best = Some((d, pad.plan));
        }
    }
    if let Some((_, plan)) = best {
        // Built-in pads use official defaults unless My Maps set ActiveStageMaps.
        match plan {
            PartyPlan::Single(StageKind::Race) => active.race = None,
            PartyPlan::Single(StageKind::Vibe) => active.vibe = None,
            PartyPlan::Single(StageKind::Shooter) => active.shooter = None,
            PartyPlan::FullParty => active.clear(),
            PartyPlan::Idle => {}
        }
        if server.is_some() || client.is_none() {
            queued.0 = Some(plan);
        } else {
            commands.client_trigger(crate::party::PartyClientCommand::queue_builtin(plan));
        }
    }
}

fn apply_equipped_skin_tint(
    equipped: Res<EquippedCosmetic>,
    catalog: Res<CosmeticsCatalog>,
    mut players: Query<(Entity, &mut PlayerColor), With<LocalPlayer>>,
    children: Query<&Children>,
    tint_parts: Query<&MeshMaterial3d<StandardMaterial>, With<PudgyTintPart>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let Some(item) = catalog.items.iter().find(|i| i.id == equipped.id) else {
        return;
    };
    let [r, g, b] = item.tint;
    for (entity, mut color) in &mut players {
        color.0 = item.tint;
        if let Ok(kids) = children.get(entity) {
            for child in kids.iter() {
                if let Ok(handle) = tint_parts.get(child) {
                    if let Some(mut mat) = materials.get_mut(handle) {
                        mat.base_color = Color::srgb(r, g, b);
                    }
                }
            }
        }
    }
}

fn pulse_showcase_lights(
    time: Res<Time>,
    director: Res<PartyDirector>,
    showcases: Query<&Children, With<SkinShowcase>>,
    mats: Query<&MeshMaterial3d<StandardMaterial>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    if director.phase != PartyPhase::Hub {
        return;
    }
    let pulse = 0.35 + 0.25 * (time.elapsed_secs() * 2.0).sin();
    for kids in &showcases {
        for child in kids.iter() {
            if let Ok(handle) = mats.get(child) {
                if let Some(mut mat) = materials.get_mut(handle) {
                    let c = mat.base_color.to_srgba();
                    mat.emissive =
                        LinearRgba::rgb(c.red * pulse, c.green * pulse, c.blue * pulse);
                }
            }
        }
    }
}

/// Used by smoke / tests to start a mode without standing on a pad.
pub fn queue_full_party(mut queued: ResMut<ModeQueued>) {
    queued.0 = Some(PartyPlan::FullParty);
}
