//! The Nest — walk, show Pudgy skins, pick a mini-game.

use bevy::prelude::*;
use bevy_replicon::prelude::*;

use crate::{
    assets::{queue_studio_prop, spawn_studio_prop, studio_asset_exists, StudioPropQueue},
    cosmetics::{CosmeticsCatalog, EquippedCosmetic},
    data::StudioRegistry,
    flow::AppScreen,
    maps::{ActiveStageMaps, PartyPack},
    party::{PartyDirector, PartyPhase, PartyPlan, PartySpawn, StageKind},
    player::{CrewAnimPlayback, LocalPlayer, PlayerColor, PudgyTintPart},
    season::SeasonLedger,
    world::GameplayEntity,
};

/// Only one Nest décor GLB decode at a time after the crew mesh is ready.
const NEST_DECOR_MAX_IN_FLIGHT: usize = 1;

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
    Koth,
}

impl EditLayer {
    pub fn label(self) -> &'static str {
        match self {
            Self::Race => "Race",
            Self::Vibe => "Vibe",
            Self::Shooter => "Shooter",
            Self::Koth => "Hill",
        }
    }

    pub fn next(self) -> Self {
        match self {
            Self::Race => Self::Vibe,
            Self::Vibe => Self::Shooter,
            Self::Shooter => Self::Koth,
            Self::Koth => Self::Race,
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
            .add_systems(Startup, spawn_social_hub.after(crate::assets::load_studio_registry))
            .add_systems(Update, drain_nest_decor_queue)
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

fn drain_nest_decor_queue(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    registry: Option<Res<StudioRegistry>>,
    mut queue: ResMut<StudioPropQueue>,
    crew_ready: Query<(), With<CrewAnimPlayback>>,
) {
    let Some(registry) = registry.as_deref() else {
        return;
    };
    if queue.is_empty() {
        return;
    }
    // Crew mesh first — Nest décor was starving the player GLB (~700MB of Tripo files).
    if crew_ready.is_empty() {
        return;
    }

    queue
        .in_flight
        .retain(|handle| !asset_server.is_loaded_with_dependencies(handle));
    if queue.in_flight.len() >= NEST_DECOR_MAX_IN_FLIGHT {
        return;
    }

    let Some(item) = queue.pop() else {
        return;
    };
    let glb_path = registry.glb_asset_path(&item.asset_id);
    let gltf_handle: Handle<bevy::gltf::Gltf> = asset_server.load(glb_path);
    queue.in_flight.push(gltf_handle);
    let _ = spawn_studio_prop(
        &mut commands,
        &asset_server,
        registry,
        &item.asset_id,
        item.transform,
        (HubProp, Name::new(item.name)),
    );
}

fn queue_mode_pad_showcase(
    queue: &mut StudioPropQueue,
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
        "Hill" => &[
            ("prop_target_star_01", Vec3::new(0.0, 0.0, 4.0), 0.0),
            ("prop_cover_block_01", Vec3::new(-3.5, 0.0, 2.0), 30.0),
            ("prop_cover_block_01", Vec3::new(3.5, 0.0, 2.0), -30.0),
        ],
        "PartySaga" => &[
            ("prop_race_cone_01", Vec3::new(-4.0, 0.0, 2.5), 0.0),
            ("prop_vibe_orb_01", Vec3::new(0.0, 0.0, 3.5), 0.0),
            ("prop_target_star_01", Vec3::new(4.0, 0.0, 2.5), 0.0),
        ],
        _ => &[],
    };
    for (i, (asset_id, offset, yaw_deg)) in props.iter().enumerate() {
        let tf = Transform::from_translation(pad_pos + *offset)
            .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
        queue_studio_prop(
            queue,
            registry,
            asset_id,
            tf,
            format!("PadShowcase_{pad_name}_{i}_{asset_id}"),
        );
    }
}

fn spawn_social_hub(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    catalog: Res<CosmeticsCatalog>,
    spawn: Res<PartySpawn>,
    registry: Option<Res<StudioRegistry>>,
    mut prop_queue: ResMut<StudioPropQueue>,
) {
    let hub = spawn.hub;
    let registry = registry.as_deref();

    // Nest egg centerpiece — queued so mode pads + crew load first.
    let egg_tf = Transform::from_translation(hub + Vec3::new(0.0, 0.0, -4.0));
    if registry.is_some_and(|r| studio_asset_exists(r, "env_nest_egg_01")) {
        queue_studio_prop(
            &mut prop_queue,
            registry.unwrap(),
            "env_nest_egg_01",
            egg_tf,
            "NestEgg",
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
            queue_studio_prop(
                &mut prop_queue,
                registry.unwrap(),
                "env_nest_bench_01",
                tf,
                format!("NestBench_{i}"),
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

    // Ambient Nest showcase — the five Studio Priority-0 selectable crew.
    let nest_npcs: [(&str, Vec3, f32); 5] = [
        ("char_pudgy_base_01", Vec3::new(-16.0, 0.0, 2.0), 70.0),
        ("oceanic_pudgymon_01", Vec3::new(16.0, 0.0, 2.0), -70.0),
        ("char_pudgy_forest_01", Vec3::new(-14.0, 0.0, 10.0), 120.0),
        ("char_pudgy_lava_01", Vec3::new(14.0, 0.0, 10.0), -120.0),
        ("char_pudgy_sky_01", Vec3::new(0.0, 0.0, 14.0), 180.0),
    ];
    for (i, (asset_id, offset, yaw_deg)) in nest_npcs.into_iter().enumerate() {
        if !registry.is_some_and(|r| studio_asset_exists(r, asset_id)) {
            continue;
        }
        let tf = Transform::from_translation(hub + offset)
            .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
        queue_studio_prop(
            &mut prop_queue,
            registry.unwrap(),
            asset_id,
            tf,
            format!("NestNpc_{i}_{asset_id}"),
        );
    }

    // Vibe mushrooms — outer ring (fallback greybox shares handles).
    let stem_mesh = meshes.add(Cylinder::new(0.25, 1.6));
    let stem_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.35, 0.75, 0.55),
        ..Default::default()
    });
    let cap_mesh = meshes.add(Sphere::new(0.85));
    let cap_mats = [
        materials.add(StandardMaterial {
            base_color: Color::srgb(1.0, 0.45, 0.4),
            emissive: LinearRgba::rgb(0.3, 0.15, 0.1),
            unlit: true,
            ..Default::default()
        }),
        materials.add(StandardMaterial {
            base_color: Color::srgb(0.45, 0.85, 1.0),
            emissive: LinearRgba::rgb(0.3, 0.15, 0.1),
            unlit: true,
            ..Default::default()
        }),
    ];
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
            queue_studio_prop(
                &mut prop_queue,
                registry.unwrap(),
                "prop_vibe_mushroom_01",
                tf,
                format!("VibeMushroom_{i}"),
            );
        } else {
            commands.spawn((
                HubProp,
                GameplayEntity,
                Mesh3d(stem_mesh.clone()),
                MeshMaterial3d(stem_mat.clone()),
                Transform::from_translation(hub + pos + Vec3::Y * 1.2),
                Name::new(format!("VibeStem_{i}")),
            ));
            commands.spawn((
                HubProp,
                GameplayEntity,
                Mesh3d(cap_mesh.clone()),
                MeshMaterial3d(cap_mats[i % 2].clone()),
                Transform::from_translation(hub + pos + Vec3::Y * 2.3),
                Name::new(format!("VibeCap_{i}")),
            ));
        }
    }

    let pads: [(PartyPlan, Vec3, [f32; 3], &str, &str); 5] = [
        (
            PartyPlan::Single(StageKind::Race),
            Vec3::new(-20.0, 0.0, -14.0),
            [0.2, 0.85, 1.0],
            "Race",
            "env_pad_race_01",
        ),
        (
            PartyPlan::Single(StageKind::Vibe),
            Vec3::new(-8.0, 0.0, -24.0),
            [1.0, 0.85, 0.2],
            "Vibe",
            "env_pad_vibe_01",
        ),
        (
            PartyPlan::Single(StageKind::Shooter),
            Vec3::new(20.0, 0.0, -14.0),
            [1.0, 0.4, 0.55],
            "Shooter",
            "env_pad_shooter_01",
        ),
        (
            PartyPlan::Single(StageKind::Koth),
            Vec3::new(8.0, 0.0, -24.0),
            [0.75, 0.5, 1.0],
            "Hill",
            "env_pad_koth_01",
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
        // Interactive pad marker is always immediate (greybox). Studio pad GLBs are
        // queued so they cannot block the crew character load.
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
        if let Some(reg) = registry {
            queue_studio_prop(
                &mut prop_queue,
                reg,
                asset_id,
                tf,
                format!("ModePadVisual_{name}_{asset_id}"),
            );
        }
        // Soft arch / checkpoint marker behind pad when available
        let sign_pos = pos + Vec3::new(0.0, 0.0, -3.2);
        if name == "Race"
            && registry.is_some_and(|reg| studio_asset_exists(reg, "prop_race_checkpoint_01"))
        {
            queue_studio_prop(
                &mut prop_queue,
                registry.unwrap(),
                "prop_race_checkpoint_01",
                Transform::from_translation(sign_pos),
                format!("ModeSign_{name}"),
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
            queue_mode_pad_showcase(&mut prop_queue, reg, name, pos);
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
            let tf = Transform::from_translation(hub + offset)
                .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
            queue_studio_prop(
                &mut prop_queue,
                reg,
                asset_id,
                tf,
                format!("NestDeco_{i}_{asset_id}"),
            );
        }
        if !prop_queue.is_empty() {
            info!(
                "queued {} Nest Studio props (load after crew mesh)",
                prop_queue.len()
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

    spawn_nest_zones(
        &mut commands,
        &mut meshes,
        &mut materials,
        registry,
        &mut prop_queue,
    );

    // Skin showcase ring — round Pudgy mannequins. Meshes and the base
    // material are shared; only the per-skin tint material is unique.
    let body_mesh = meshes.add(Sphere::new(0.5));
    let head_mesh = meshes.add(Sphere::new(0.36));
    let base_mesh = meshes.add(Cylinder::new(0.7, 0.2));
    let base_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.18, 0.28, 0.24),
        ..Default::default()
    });
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
                    Mesh3d(body_mesh.clone()),
                    MeshMaterial3d(mat.clone()),
                    Transform::from_xyz(0.0, 0.0, 0.0),
                ));
                parent.spawn((
                    Mesh3d(head_mesh.clone()),
                    MeshMaterial3d(mat),
                    Transform::from_xyz(0.0, 0.62, 0.04),
                ));
            });
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(base_mesh.clone()),
            MeshMaterial3d(base_mat.clone()),
            Transform::from_translation(pos - Vec3::Y * 0.55),
            Name::new(format!("ShowcaseBase_{}", item.id)),
        ));
    }
}

/// Themed districts that turn the Nest plaza into a small open world:
/// Hill Lookout (north), Race Training Strip (west), Vibe Garden (east),
/// plus lamps and far-corner flora. World coordinates, arena is ±48.
fn spawn_nest_zones(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    registry: Option<&StudioRegistry>,
    prop_queue: &mut StudioPropQueue,
) {
    // Hill Lookout — stepped mound players can rally around (KOTH flavor).
    let mound_center = Vec3::new(0.0, 0.0, -38.0);
    let mound_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.5, 0.42, 0.55),
        ..Default::default()
    });
    for (i, (radius, height)) in [(7.0, 0.8), (4.6, 1.8), (2.6, 2.8)].into_iter().enumerate() {
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(meshes.add(Cylinder::new(radius, 0.5))),
            MeshMaterial3d(mound_mat.clone()),
            Transform::from_translation(mound_center + Vec3::Y * height),
            Name::new(format!("HillLookout_{i}")),
        ));
    }
    commands.spawn((
        HubProp,
        GameplayEntity,
        Mesh3d(meshes.add(Sphere::new(0.7))),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: Color::srgb(1.0, 0.8, 0.25),
            emissive: LinearRgba::rgb(1.8, 1.3, 0.3),
            unlit: true,
            ..Default::default()
        })),
        Transform::from_translation(mound_center + Vec3::Y * 4.0),
        Name::new("HillLookoutBeacon"),
    ));

    // Studio props per zone (skipped when the GLB is not on disk yet).
    if let Some(reg) = registry {
        let zone_props: [(&str, Vec3, f32); 14] = [
            // Hill Lookout flags
            ("prop_target_star_01", Vec3::new(-6.0, 0.0, -42.0), 30.0),
            ("prop_target_star_01", Vec3::new(6.0, 0.0, -42.0), -30.0),
            // Race Training Strip (west): slalom + ramp + banner
            ("prop_race_banner_01", Vec3::new(-40.0, 0.0, -6.0), 90.0),
            ("prop_race_cone_01", Vec3::new(-38.0, 0.0, 0.0), 0.0),
            ("prop_race_cone_01", Vec3::new(-34.0, 0.0, 5.0), 0.0),
            ("prop_race_cone_01", Vec3::new(-38.0, 0.0, 10.0), 0.0),
            ("prop_race_cone_01", Vec3::new(-34.0, 0.0, 15.0), 0.0),
            ("env_race_ramp_01", Vec3::new(-40.0, 0.0, 20.0), 90.0),
            // Vibe Garden (east)
            ("prop_vibe_mushroom_01", Vec3::new(38.0, 0.0, 2.0), 0.0),
            ("prop_vibe_flower_01", Vec3::new(35.0, 0.0, 8.0), 40.0),
            ("prop_vibe_flower_01", Vec3::new(41.0, 0.0, 8.0), -40.0),
            ("prop_vibe_crystal_01", Vec3::new(36.0, 0.0, 14.0), 20.0),
            ("prop_vibe_crystal_01", Vec3::new(40.0, 0.0, 14.0), -20.0),
            ("prop_vibe_orb_01", Vec3::new(38.0, 0.0, 20.0), 0.0),
        ];
        for (i, (asset_id, pos, yaw_deg)) in zone_props.into_iter().enumerate() {
            let tf = Transform::from_translation(pos)
                .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
            queue_studio_prop(
                prop_queue,
                reg,
                asset_id,
                tf,
                format!("NestZone_{i}_{asset_id}"),
            );
        }

        queue_candy_districts(reg, prop_queue);
    }

    // Vibe Garden pond — candy pond GLB when imported, greybox disc otherwise.
    if !registry.is_some_and(|r| studio_asset_exists(r, "env_nest_pond_01")) {
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(meshes.add(Cylinder::new(4.5, 0.12))),
            MeshMaterial3d(materials.add(StandardMaterial {
                base_color: Color::srgb(0.25, 0.6, 0.85),
                emissive: LinearRgba::rgb(0.08, 0.25, 0.4),
                ..Default::default()
            })),
            Transform::from_xyz(38.0, 0.03, 30.0),
            Name::new("VibeGardenPond"),
        ));
    }

    // Lamps marking paths out to each district — candy lamp GLBs when
    // imported, shared-handle greyboxes otherwise.
    let lamp_glb = registry.is_some_and(|r| studio_asset_exists(r, "env_nest_lamp_01"));
    let mut greybox_lamp = None;
    if !lamp_glb {
        let post_mesh = meshes.add(Cylinder::new(0.14, 3.0));
        let post_mat = materials.add(StandardMaterial {
            base_color: Color::srgb(0.3, 0.32, 0.38),
            ..Default::default()
        });
        let glow_mesh = meshes.add(Sphere::new(0.4));
        let glow_mat = materials.add(StandardMaterial {
            base_color: Color::srgb(1.0, 0.9, 0.6),
            emissive: LinearRgba::rgb(1.6, 1.3, 0.7),
            unlit: true,
            ..Default::default()
        });
        greybox_lamp = Some((post_mesh, post_mat, glow_mesh, glow_mat));
    }
    for (i, pos) in [
        Vec3::new(-14.0, 0.0, -30.0),
        Vec3::new(14.0, 0.0, -30.0),
        Vec3::new(-28.0, 0.0, 8.0),
        Vec3::new(28.0, 0.0, 8.0),
        Vec3::new(0.0, 0.0, 30.0),
        Vec3::new(-30.0, 0.0, 30.0),
        Vec3::new(30.0, 0.0, -34.0),
        Vec3::new(-6.0, 0.0, -20.0),
        Vec3::new(6.0, 0.0, -20.0),
    ]
    .into_iter()
    .enumerate()
    {
        if lamp_glb {
            queue_studio_prop(
                prop_queue,
                registry.unwrap(),
                "env_nest_lamp_01",
                Transform::from_translation(pos),
                format!("NestLamp_{i}"),
            );
            continue;
        }
        let (post_mesh, post_mat, glow_mesh, glow_mat) = greybox_lamp.as_ref().unwrap();
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(post_mesh.clone()),
            MeshMaterial3d(post_mat.clone()),
            Transform::from_translation(pos + Vec3::Y * 1.5),
            Name::new(format!("NestLampPost_{i}")),
        ));
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(glow_mesh.clone()),
            MeshMaterial3d(glow_mat.clone()),
            Transform::from_translation(pos + Vec3::Y * 3.2),
            Name::new(format!("NestLampGlow_{i}")),
        ));
    }

    // Far-corner flora so the island edges feel alive.
    let shroom_mesh = meshes.add(Sphere::new(1.1));
    let shroom_mat = materials.add(StandardMaterial {
        base_color: Color::srgb(0.4, 0.8, 0.55),
        ..Default::default()
    });
    for (i, pos) in [
        Vec3::new(-42.0, 0.0, -42.0),
        Vec3::new(42.0, 0.0, -42.0),
        Vec3::new(-42.0, 0.0, 42.0),
        Vec3::new(42.0, 0.0, 42.0),
    ]
    .into_iter()
    .enumerate()
    {
        if let Some(reg) = registry {
            if studio_asset_exists(reg, "prop_vibe_mushroom_01") {
                queue_studio_prop(
                    prop_queue,
                    reg,
                    "prop_vibe_mushroom_01",
                    Transform::from_translation(pos),
                    format!("NestCornerShroom_{i}"),
                );
                continue;
            }
        }
        commands.spawn((
            HubProp,
            GameplayEntity,
            Mesh3d(shroom_mesh.clone()),
            MeshMaterial3d(shroom_mat.clone()),
            Transform::from_translation(pos + Vec3::Y * 1.0),
            Name::new(format!("NestCornerShroom_{i}")),
        ));
    }
}

/// Candy-district décor pass — the Nest prop mega-batch laid out as themed
/// neighborhoods. World coordinates (hub plaza at origin, island grass ~±48):
/// Gateway Boulevard runs north to the mode pads, Candy Plaza + Food Boardwalk
/// + Arcade Corner fill the south, the Gardens extend the east, and two
/// monster meadows bookend the northwest/northeast island edges.
/// Missing GLBs are skipped, so partial imports degrade gracefully.
fn queue_candy_districts(reg: &StudioRegistry, prop_queue: &mut StudioPropQueue) {
    // (asset_id, x, z, yaw_degrees)
    const DISTRICTS: &[(&str, f32, f32, f32)] = &[
        // Gateway Boulevard — arches + wayfinding on the walk to the pads.
        ("env_nest_arch_01", 0.0, -10.0, 0.0),
        ("env_nest_arch_02", 0.0, -30.0, 0.0),
        ("env_nest_sign_arrow_01", -7.0, -9.0, 40.0),
        ("env_nest_sign_arrow_01", 7.0, -9.0, -40.0),
        ("env_nest_kiosk_map_01", 5.0, -13.0, -30.0),
        ("env_nest_kiosk_info_01", -5.0, -13.0, 30.0),
        ("env_nest_tile_01", 1.5, -16.0, 0.0),
        ("env_nest_tile_01", -1.5, -22.0, 30.0),
        ("env_nest_booth_ticket_01", 10.0, -34.0, -20.0),
        // Candy Plaza — fountain court south of the spawn plaza.
        ("env_nest_fountain_01", 0.0, 26.0, 0.0),
        ("env_nest_arch_balloon_01", 0.0, 18.0, 0.0),
        ("env_nest_couch_01", -7.0, 28.0, 130.0),
        ("env_nest_loveseat_01", 7.0, 28.0, -130.0),
        ("env_nest_chair_01", -4.0, 31.0, 60.0),
        ("env_nest_table_01", 4.0, 31.0, 0.0),
        ("env_nest_umbrella_01", 5.0, 32.0, 0.0),
        ("env_nest_cake_01", 0.0, 34.0, 0.0),
        ("env_nest_trashbin_01", 10.0, 26.0, 0.0),
        ("env_nest_hydrant_01", -10.0, 24.0, 0.0),
        ("env_nest_mailbox_01", 4.0, 19.0, 180.0),
        ("env_nest_signboard_01", -3.0, 20.0, 160.0),
        // Food Boardwalk — southwest snack row.
        ("env_nest_truck_icecream_01", -28.0, 30.0, 55.0),
        ("env_nest_cart_snack_01", -20.0, 27.0, 25.0),
        ("env_nest_cart_candy_01", -34.0, 24.0, 90.0),
        ("env_nest_car_01", -16.0, 34.0, -70.0),
        ("env_nest_bench_02", -22.0, 33.0, 0.0),
        ("env_nest_bench_02", -17.0, 30.0, 45.0),
        ("env_nest_cookie_01", -24.0, 26.0, 0.0),
        ("env_nest_dumpling_01", -26.0, 24.0, 0.0),
        ("env_nest_cake_02", -31.0, 27.0, 0.0),
        ("env_nest_barrel_01", -30.0, 34.0, 0.0),
        ("env_nest_crate_01", -32.0, 33.0, 15.0),
        ("env_nest_creature_party_01", -24.0, 37.0, 180.0),
        // Arcade Corner — southeast games alley.
        ("env_nest_arcade_01", 24.0, 28.0, -35.0),
        ("env_nest_arcade_01", 27.0, 29.0, -55.0),
        ("env_nest_jukebox_01", 21.0, 26.0, -20.0),
        ("env_nest_portal_01", 32.0, 36.0, -45.0),
        ("env_nest_piggybank_01", 29.0, 24.0, 0.0),
        ("env_nest_chest_01", 33.0, 27.0, -60.0),
        ("env_nest_ring_01", 26.0, 36.0, 0.0),
        ("env_nest_ball_01", 23.0, 33.0, 0.0),
        ("env_nest_stair_01", 31.0, 31.0, 20.0),
        ("env_nest_blob_01", 19.0, 36.0, 0.0),
        // Gardens & Grove — extends the Vibe Garden east with real flora.
        ("env_nest_pond_01", 38.0, 30.0, 0.0),
        ("env_nest_tree_01", 44.0, 24.0, 0.0),
        ("env_nest_tree_round_01", 34.0, 40.0, 0.0),
        ("env_nest_tree_candy_01", 44.0, 36.0, 70.0),
        ("env_nest_tree_candy_02", 28.0, 44.0, -30.0),
        ("env_nest_planter_01", 36.0, 24.0, 0.0),
        ("env_nest_planter_01", 40.0, 22.0, 0.0),
        ("env_nest_plant_01", 32.0, 26.0, 0.0),
        ("env_nest_egg_rainbow_01", 40.0, 42.0, 0.0),
        ("env_nest_egg_02", 46.0, 30.0, 0.0),
        // Monster Meadow — northwest island edge.
        ("env_nest_char_star_01", -36.0, -16.0, 140.0),
        ("env_nest_monster_01", -30.0, -20.0, 60.0),
        ("env_nest_monster_02", -34.0, -24.0, 120.0),
        ("env_nest_monster_03", -38.0, -20.0, -40.0),
        ("env_nest_monster_04", -42.0, -26.0, 30.0),
        ("env_nest_monster_05", -32.0, -30.0, -120.0),
        ("env_nest_monster_06", -36.0, -34.0, 0.0),
        ("env_nest_monster_07", -42.0, -34.0, 45.0),
        ("env_nest_monster_08", -28.0, -26.0, 90.0),
        ("env_nest_monster_balloon_01", -38.0, -28.0, 0.0),
        ("env_nest_monster_09", -30.0, -38.0, 160.0),
        ("env_nest_monster_10", -44.0, -30.0, -90.0),
        ("env_nest_monster_11", -34.0, -40.0, -20.0),
        ("env_nest_monster_12", -40.0, -40.0, 75.0),
        // Monster Cove — northeast island edge.
        ("env_nest_char_sphere_01", 36.0, -16.0, -140.0),
        ("env_nest_monster_13", 30.0, -20.0, -60.0),
        ("env_nest_monster_14", 34.0, -24.0, -120.0),
        ("env_nest_monster_15", 38.0, -20.0, 40.0),
        ("env_nest_monster_16", 42.0, -26.0, -30.0),
        ("env_nest_monster_17", 32.0, -30.0, 120.0),
        ("env_nest_monster_18", 36.0, -34.0, 0.0),
        ("env_nest_monster_19", 42.0, -34.0, -45.0),
        ("env_nest_monster_20", 28.0, -26.0, -90.0),
        ("env_nest_monster_21", 30.0, -38.0, -160.0),
        ("env_nest_monster_22", 44.0, -30.0, 90.0),
        ("env_nest_monster_23", 34.0, -40.0, 20.0),
        ("env_nest_monster_24", 40.0, -40.0, -75.0),
        ("env_nest_monster_25", 46.0, -36.0, 10.0),
        // Stragglers (batch 2) — hammock nook, pond details, meadow fill.
        ("env_nest_hammock_01", -40.0, 34.0, 110.0),
        ("env_nest_swing_01", -44.0, 30.0, 100.0),
        ("env_nest_arch_03", -13.0, 28.0, 90.0),
        ("env_nest_candle_01", -5.0, 26.0, 0.0),
        ("env_nest_post_01", 3.0, -5.0, 0.0),
        ("env_nest_deco_09", 12.0, 30.0, 40.0),
        ("env_nest_rocks_01", 42.0, 33.0, 0.0),
        ("env_nest_lilypad_01", 37.0, 29.0, 20.0),
        ("env_nest_plant_02", 17.0, 28.0, 0.0),
        ("env_nest_creature_mushroom_01", 24.0, 42.0, -40.0),
        ("env_nest_monster_26", -46.0, -22.0, 60.0),
        ("env_nest_monster_27", 46.0, -24.0, -60.0),
        ("env_nest_monster_28", -26.0, -34.0, 40.0),
        // Deco accents flanking the main walkways.
        ("env_nest_deco_01", -12.0, -18.0, 30.0),
        ("env_nest_deco_02", 12.0, -18.0, -30.0),
        ("env_nest_deco_03", -16.0, 22.0, 0.0),
        ("env_nest_deco_04", 16.0, 22.0, 0.0),
        ("env_nest_deco_05", -8.0, 35.0, 20.0),
        ("env_nest_deco_06", 8.0, 35.0, -20.0),
        ("env_nest_deco_07", -24.0, 12.0, 90.0),
        ("env_nest_deco_08", 24.0, 12.0, -90.0),
    ];

    for (i, (asset_id, x, z, yaw_deg)) in DISTRICTS.iter().enumerate() {
        if !studio_asset_exists(reg, asset_id) {
            continue;
        }
        let tf = Transform::from_xyz(*x, 0.0, *z)
            .with_rotation(Quat::from_rotation_y(yaw_deg.to_radians()));
        queue_studio_prop(
            prop_queue,
            reg,
            asset_id,
            tf,
            format!("CandyDistrict_{i}_{asset_id}"),
        );
    }
}

fn sync_hub_pad_visibility(
    director: Res<PartyDirector>,
    mut last: Local<Option<PartyPhase>>,
    mut pads: Query<&mut Visibility, With<HubProp>>,
) {
    // Only write visibility when the phase flips, or per prop as it streams
    // in (queued Studio GLBs spawn over many frames). Checking `is_added()`
    // reads change ticks without marking anything changed.
    let phase_changed = *last != Some(director.phase);
    *last = Some(director.phase);
    let vis = if director.phase == PartyPhase::Hub {
        Visibility::Visible
    } else {
        Visibility::Hidden
    };
    for mut v in &mut pads {
        if phase_changed || v.is_added() {
            *v = vis;
        }
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
    // Assign through `set_line` only when the text differs — a per-frame write
    // marks HubPrompt changed and cascades into HUD text re-layout.
    let mut set_line = |line: String| {
        if prompt.line != line {
            prompt.line = line;
        }
    };
    if director.phase != PartyPhase::Hub {
        set_line(String::new());
        return;
    }
    let Ok(player) = local.single() else {
        set_line("Hatching into The Nest…".into());
        return;
    };

    for (pad, tf) in &utilities {
        if player.translation.distance(tf.translation) < 2.8 {
            set_line(match pad.action {
                NestAction::OpenEditor => {
                    "E / Enter — open Race Map Creator".into()
                }
                NestAction::BrowseMaps => {
                    "[ ] cycle maps · E play selected custom/official Race".into()
                }
            });
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
        set_line(format!(
            "E / Enter — start {}  ·  Skin {}  ·  Season {} pts",
            plan.label(),
            equipped.id,
            ledger.points
        ));
    } else {
        set_line(format!(
            "The Nest — mode pads · Create Map · My Maps · C skin ({}) · Season {} pts",
            equipped.id, ledger.points
        ));
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
            PartyPlan::Single(StageKind::Koth) => active.koth = None,
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
    fresh_parts: Query<(), Added<PudgyTintPart>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    // Writing PlayerColor (replicated) and material assets every frame forces
    // network + GPU re-uploads. Only run when the skin changes or a new
    // procedural stub spawns and needs its first tint.
    if !equipped.is_changed() && fresh_parts.is_empty() {
        return;
    }
    let Some(item) = catalog.items.iter().find(|i| i.id == equipped.id) else {
        return;
    };
    let [r, g, b] = item.tint;
    for (entity, mut color) in &mut players {
        if color.0 != item.tint {
            color.0 = item.tint;
        }
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
