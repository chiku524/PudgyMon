//! Nest map creator — Race / Vibe / Shooter layers + Party Saga packs.

use bevy::prelude::*;
use bevy_replicon::prelude::*;

use crate::{
    core::ARENA_BOUNDS,
    data::StudioRegistry,
    flow::AppScreen,
    hub::{EditLayer, EditorMode, HubPrompt, ModeQueued, NestAction, NestUtilityPad},
    maps::{
        export_share_code, list_catalog, save_party_pack, save_race_map, save_shooter_map,
        save_vibe_map, sanitize_id, ActiveStageMaps, CatalogEntry, EDITOR_DECO_IDS, MapBlock,
        PartyPack,
    },
    party::{PartyDirector, PartyPhase, PartyPlan, PartySpawn, StageKind},
    player::{LocalPlayer, ThirdPersonCamera},
    world::GameplayEntity,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum EditorPalette {
    #[default]
    Primary,
    Spawn,
    Block,
    Deco,
}

impl EditorPalette {
    pub fn label(self, layer: EditLayer) -> &'static str {
        match (layer, self) {
            (EditLayer::Race, Self::Primary) => "Gate",
            (EditLayer::Vibe, Self::Primary) => "Orb",
            (EditLayer::Shooter, Self::Primary) => "Cover",
            (_, Self::Spawn) => "Spawn",
            (_, Self::Block) => "Block",
            (_, Self::Deco) => "Deco GLB",
        }
    }
}

#[derive(Component)]
pub struct EditorProp {
    pub kind: EditorPalette,
    pub index: u8,
}

#[derive(Component)]
struct EditorGhost;

#[derive(Component)]
pub struct EditorHudRoot;

#[derive(Component)]
struct EditorHudText;

#[derive(Resource, Debug, Default)]
struct EditorTool(EditorPalette);

pub struct MapEditorPlugin;

impl Plugin for MapEditorPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<EditorTool>()
            .add_systems(Startup, spawn_editor_hud)
            .add_systems(
                Update,
                (
                    enter_editor_from_nest,
                    browse_maps_from_nest,
                    editor_layer_and_palette,
                    editor_place_delete,
                    editor_save_playtest_exit,
                    sync_editor_ghost,
                    update_editor_hud,
                )
                    .chain()
                    .run_if(in_state(AppScreen::Playing)),
            );
    }
}

pub use crate::hub::editor_is_active;

fn spawn_editor_hud(mut commands: Commands) {
    commands.spawn((
        EditorHudRoot,
        Node {
            position_type: PositionType::Absolute,
            top: Val::Px(12.0),
            right: Val::Px(16.0),
            width: Val::Px(420.0),
            padding: UiRect::all(Val::Px(12.0)),
            flex_direction: FlexDirection::Column,
            row_gap: Val::Px(6.0),
            ..Default::default()
        },
        BackgroundColor(Color::srgba(0.05, 0.12, 0.1, 0.85)),
        GlobalZIndex(450),
        Visibility::Hidden,
        children![(
            EditorHudText,
            Text::new(""),
            TextFont {
                font_size: FontSize::Px(13.0),
                ..Default::default()
            },
            TextColor(Color::srgb(0.95, 0.95, 0.9)),
        )],
    ));
}

fn enter_editor_from_nest(
    keyboard: Res<ButtonInput<KeyCode>>,
    director: Res<PartyDirector>,
    local: Query<&Transform, With<LocalPlayer>>,
    pads: Query<(&NestUtilityPad, &Transform)>,
    mut editor: ResMut<EditorMode>,
    mut tool: ResMut<EditorTool>,
    mut prompt: ResMut<HubPrompt>,
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    props: Query<Entity, With<EditorProp>>,
) {
    if editor.active || director.phase != PartyPhase::Hub {
        return;
    }
    let want = keyboard.just_pressed(KeyCode::KeyE)
        || keyboard.just_pressed(KeyCode::Enter)
        || keyboard.just_pressed(KeyCode::NumpadEnter);
    if !want {
        return;
    }
    let Ok(player) = local.single() else {
        return;
    };
    let on_create = pads.iter().any(|(pad, tf)| {
        pad.action == NestAction::OpenEditor && player.translation.distance(tf.translation) < 2.8
    });
    if !on_create {
        return;
    }

    for entity in &props {
        commands.entity(entity).despawn();
    }
    editor.active = true;
    editor.pack = PartyPack::default();
    editor.pack.id = format!("pack_{}", short_stamp());
    editor.pack.label = "My Party Saga".into();
    editor.pack.sync_ids_from_pack();
    editor.layer = EditLayer::Race;
    editor.deco_index = 0;
    tool.0 = EditorPalette::Primary;
    editor.status =
        "Tab layer · 1 primary · 2 spawn · 3 block · 4 deco · F place · F5/F8 save · F6/F9 play · F7 share"
            .into();
    prompt.line = editor.status.clone();
    rebuild_visuals(&mut commands, &mut meshes, &mut materials, &editor);
}

fn browse_maps_from_nest(
    keyboard: Res<ButtonInput<KeyCode>>,
    director: Res<PartyDirector>,
    local: Query<&Transform, With<LocalPlayer>>,
    pads: Query<(&NestUtilityPad, &Transform)>,
    editor: Res<EditorMode>,
    mut active: ResMut<ActiveStageMaps>,
    mut queued: ResMut<ModeQueued>,
    mut prompt: ResMut<HubPrompt>,
    mut picker: Local<usize>,
    mut commands: Commands,
    server: Option<Res<bevy_replicon_renet::RenetServer>>,
    client: Option<Res<bevy_replicon_renet::RenetClient>>,
) {
    if editor.active || director.phase != PartyPhase::Hub {
        return;
    }
    let Ok(player) = local.single() else {
        return;
    };
    let on_browse = pads.iter().any(|(pad, tf)| {
        pad.action == NestAction::BrowseMaps && player.translation.distance(tf.translation) < 2.8
    });
    if !on_browse {
        return;
    }

    let catalog = list_catalog();
    if catalog.is_empty() {
        prompt.line = "No maps found — create one on Create Map".into();
        return;
    }

    if keyboard.just_pressed(KeyCode::BracketLeft) {
        *picker = picker.saturating_sub(1);
    }
    if keyboard.just_pressed(KeyCode::BracketRight) {
        *picker = (*picker + 1).min(catalog.len().saturating_sub(1));
    }
    *picker = (*picker).min(catalog.len() - 1);
    let selected = &catalog[*picker];
    prompt.line = format!(
        "[ ] · E play \"{}\" [{}] ({}/{})",
        selected.label(),
        selected.kind_label(),
        *picker + 1,
        catalog.len()
    );

    let start = keyboard.just_pressed(KeyCode::KeyE)
        || keyboard.just_pressed(KeyCode::Enter)
        || keyboard.just_pressed(KeyCode::NumpadEnter);
    if !start {
        return;
    }

    let plan = match selected {
        CatalogEntry::Race(m) => {
            active.clear();
            active.race = Some(m.clone());
            PartyPlan::Single(StageKind::Race)
        }
        CatalogEntry::Vibe(m) => {
            active.clear();
            active.vibe = Some(m.clone());
            PartyPlan::Single(StageKind::Vibe)
        }
        CatalogEntry::Shooter(m) => {
            active.clear();
            active.shooter = Some(m.clone());
            PartyPlan::Single(StageKind::Shooter)
        }
        CatalogEntry::Pack(p) => {
            active.apply_pack(p);
            PartyPlan::FullParty
        }
    };
    if server.is_some() || client.is_none() {
        queued.0 = Some(plan);
    } else {
        commands.client_trigger(crate::party::PartyClientCommand::queue_with_maps(
            plan, &active,
        ));
    }
    prompt.line = format!("Starting {}", selected.label());
}

fn editor_layer_and_palette(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut editor: ResMut<EditorMode>,
    mut tool: ResMut<EditorTool>,
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    props: Query<Entity, With<EditorProp>>,
    registry: Option<Res<StudioRegistry>>,
) {
    if !editor.active {
        return;
    }
    if keyboard.just_pressed(KeyCode::Tab) {
        editor.layer = editor.layer.next();
        tool.0 = EditorPalette::Primary;
        editor.status = format!("Editing {} layer", editor.layer.label());
        for entity in &props {
            commands.entity(entity).despawn();
        }
        rebuild_visuals(&mut commands, &mut meshes, &mut materials, &editor);
    }
    if keyboard.just_pressed(KeyCode::Digit1) {
        tool.0 = EditorPalette::Primary;
        editor.status = format!("Palette: {}", tool.0.label(editor.layer));
    }
    if keyboard.just_pressed(KeyCode::Digit2) {
        tool.0 = EditorPalette::Spawn;
        editor.status = "Palette: Spawn".into();
    }
    if keyboard.just_pressed(KeyCode::Digit3) {
        tool.0 = EditorPalette::Block;
        editor.status = "Palette: Block".into();
    }
    if keyboard.just_pressed(KeyCode::Digit4) {
        tool.0 = EditorPalette::Deco;
        editor.status = format!(
            "Palette: Deco · {}",
            current_deco_id(&editor, registry.as_deref())
        );
    }
    if tool.0 == EditorPalette::Deco
        && (keyboard.just_pressed(KeyCode::Comma) || keyboard.just_pressed(KeyCode::Period))
    {
        let count = deco_count(registry.as_deref()).max(1);
        if keyboard.just_pressed(KeyCode::Comma) {
            editor.deco_index = editor.deco_index.saturating_sub(1);
        } else {
            editor.deco_index = (editor.deco_index + 1) % count;
        }
        editor.status = format!(
            "Deco: {}",
            current_deco_id(&editor, registry.as_deref())
        );
    }
}

fn editor_place_delete(
    keyboard: Res<ButtonInput<KeyCode>>,
    mouse: Res<ButtonInput<MouseButton>>,
    camera: Res<ThirdPersonCamera>,
    mut editor: ResMut<EditorMode>,
    tool: Res<EditorTool>,
    local: Query<&Transform, With<LocalPlayer>>,
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    props: Query<(Entity, &EditorProp, &Transform)>,
    registry: Option<Res<StudioRegistry>>,
) {
    if !editor.active {
        return;
    }
    let Ok(player) = local.single() else {
        return;
    };

    let place = mouse.just_pressed(MouseButton::Left) || keyboard.just_pressed(KeyCode::KeyF);
    if place {
        let pos = place_point(player, camera.yaw);
        match (editor.layer, tool.0) {
            (EditLayer::Race, EditorPalette::Primary) => {
                editor.pack.race.gates.push([pos.x, 1.0, pos.z]);
                editor.status = format!("Gate #{}", editor.pack.race.gates.len());
            }
            (EditLayer::Vibe, EditorPalette::Primary) => {
                editor.pack.vibe.orbs.push([pos.x, 0.6, pos.z]);
                editor.status = format!("Orb #{}", editor.pack.vibe.orbs.len());
            }
            (EditLayer::Shooter, EditorPalette::Primary)
            | (_, EditorPalette::Block) => {
                let block = MapBlock::greybox([pos.x, 0.5, pos.z], [2.0, 1.0, 2.0]);
                push_block(&mut editor, block);
            }
            (_, EditorPalette::Spawn) => {
                set_spawn(&mut editor, [pos.x, 1.0, pos.z]);
                editor.status = "Spawn set".into();
            }
            (_, EditorPalette::Deco) => {
                let id = current_deco_id(&editor, registry.as_deref());
                let block = MapBlock {
                    pos: [pos.x, 0.5, pos.z],
                    size: [2.0, 1.2, 2.0],
                    asset_id: Some(id.clone()),
                };
                push_block(&mut editor, block);
                editor.status = format!("Deco {id}");
            }
        }
        editor.pack.clamp_to_arena();
        for (entity, _, _) in &props {
            commands.entity(entity).despawn();
        }
        rebuild_visuals(&mut commands, &mut meshes, &mut materials, &editor);
    }

    if keyboard.just_pressed(KeyCode::KeyX) {
        let mut nearest: Option<(EditorPalette, usize)> = None;
        let mut best = f32::MAX;
        for (_e, prop, tf) in &props {
            let d = player.translation.distance(tf.translation);
            if d < 3.0 && d < best {
                best = d;
                nearest = Some((prop.kind, prop.index as usize));
            }
        }
        if let Some((kind, idx)) = nearest {
            delete_prop(&mut editor, kind, idx);
            for (entity, _, _) in &props {
                commands.entity(entity).despawn();
            }
            rebuild_visuals(&mut commands, &mut meshes, &mut materials, &editor);
            editor.status = "Deleted".into();
        }
    }
}

fn editor_save_playtest_exit(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut editor: ResMut<EditorMode>,
    mut active: ResMut<ActiveStageMaps>,
    mut queued: ResMut<ModeQueued>,
    mut director: ResMut<PartyDirector>,
    mut commands: Commands,
    props: Query<Entity, With<EditorProp>>,
    ghosts: Query<Entity, With<EditorGhost>>,
    spawn: Res<PartySpawn>,
    mut local: Query<&mut Transform, With<LocalPlayer>>,
) {
    if !editor.active {
        return;
    }

    if keyboard.just_pressed(KeyCode::F5) {
        editor.pack.sync_ids_from_pack();
        let result = match editor.layer {
            EditLayer::Race => {
                editor.pack.race.id = sanitize_id(&editor.pack.race.id);
                save_race_map(&editor.pack.race)
            }
            EditLayer::Vibe => {
                editor.pack.vibe.id = sanitize_id(&editor.pack.vibe.id);
                save_vibe_map(&editor.pack.vibe)
            }
            EditLayer::Shooter => {
                editor.pack.shooter.id = sanitize_id(&editor.pack.shooter.id);
                save_shooter_map(&editor.pack.shooter)
            }
        };
        editor.status = match result {
            Ok(p) => format!("Saved layer {}", p.display()),
            Err(e) => format!("Save failed: {e}"),
        };
    }

    if keyboard.just_pressed(KeyCode::F8) {
        editor.pack.id = sanitize_id(&editor.pack.id);
        editor.pack.sync_ids_from_pack();
        editor.status = match save_party_pack(&editor.pack) {
            Ok(p) => format!("Saved pack {}", p.display()),
            Err(e) => format!("Pack save failed: {e}"),
        };
    }

    if keyboard.just_pressed(KeyCode::F7) {
        editor.pack.id = sanitize_id(&editor.pack.id);
        editor.status = match export_share_code(&editor.pack) {
            Ok((code, path)) => {
                open_maps_companion();
                format!("Share {code} → {} (opened Map Share Desk)", path.display())
            }
            Err(e) => format!("Share failed: {e}"),
        };
    }

    if keyboard.just_pressed(KeyCode::F6) {
        let ok = match editor.layer {
            EditLayer::Race => editor.pack.race.validate(),
            EditLayer::Vibe => editor.pack.vibe.validate(),
            EditLayer::Shooter => editor.pack.shooter.validate(),
        };
        match ok {
            Ok(()) => {
                active.clear();
                match editor.layer {
                    EditLayer::Race => {
                        active.race = Some(editor.pack.race.clone());
                        queued.0 = Some(PartyPlan::Single(StageKind::Race));
                    }
                    EditLayer::Vibe => {
                        active.vibe = Some(editor.pack.vibe.clone());
                        queued.0 = Some(PartyPlan::Single(StageKind::Vibe));
                    }
                    EditLayer::Shooter => {
                        active.shooter = Some(editor.pack.shooter.clone());
                        queued.0 = Some(PartyPlan::Single(StageKind::Shooter));
                    }
                }
                exit_editor_world(
                    &mut editor,
                    &mut commands,
                    &props,
                    &ghosts,
                );
                editor.status = "Playtesting layer…".into();
            }
            Err(e) => editor.status = format!("Cannot playtest: {e}"),
        }
    }

    if keyboard.just_pressed(KeyCode::F9) {
        match editor.pack.validate() {
            Ok(()) => {
                active.apply_pack(&editor.pack);
                queued.0 = Some(PartyPlan::FullParty);
                exit_editor_world(
                    &mut editor,
                    &mut commands,
                    &props,
                    &ghosts,
                );
                editor.status = "Playtesting Party Saga pack…".into();
            }
            Err(e) => editor.status = format!("Pack invalid: {e}"),
        }
    }

    if keyboard.just_pressed(KeyCode::Escape) || keyboard.just_pressed(KeyCode::KeyQ) {
        exit_editor_world(&mut editor, &mut commands, &props, &ghosts);
        director.announcer = "Back in The Nest.".into();
        if let Ok(mut tf) = local.single_mut() {
            tf.translation = spawn.hub;
        }
    }
}

fn sync_editor_ghost(
    editor: Res<EditorMode>,
    tool: Res<EditorTool>,
    camera: Res<ThirdPersonCamera>,
    local: Query<&Transform, With<LocalPlayer>>,
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    ghosts: Query<Entity, With<EditorGhost>>,
) {
    for entity in &ghosts {
        commands.entity(entity).despawn();
    }
    if !editor.active {
        return;
    }
    let Ok(player) = local.single() else {
        return;
    };
    let pos = place_point(player, camera.yaw);
    let (color, mesh, y) = match (editor.layer, tool.0) {
        (EditLayer::Race, EditorPalette::Primary) => (
            Color::srgba(0.2, 0.85, 1.0, 0.45),
            meshes.add(Cuboid::new(3.0, 2.5, 0.4)),
            1.0,
        ),
        (EditLayer::Vibe, EditorPalette::Primary) => (
            Color::srgba(1.0, 0.9, 0.2, 0.5),
            meshes.add(Sphere::new(0.45)),
            0.6,
        ),
        (_, EditorPalette::Spawn) => (
            Color::srgba(0.4, 1.0, 0.5, 0.45),
            meshes.add(Cylinder::new(0.6, 0.2)),
            0.15,
        ),
        _ => (
            Color::srgba(0.8, 0.5, 0.3, 0.45),
            meshes.add(Cuboid::new(2.0, 1.0, 2.0)),
            0.5,
        ),
    };
    commands.spawn((
        EditorGhost,
        GameplayEntity,
        Mesh3d(mesh),
        MeshMaterial3d(materials.add(StandardMaterial {
            base_color: color,
            alpha_mode: AlphaMode::Blend,
            unlit: true,
            ..Default::default()
        })),
        Transform::from_translation(Vec3::new(pos.x, y, pos.z)),
        Name::new("EditorGhost"),
    ));
}

fn update_editor_hud(
    editor: Res<EditorMode>,
    tool: Res<EditorTool>,
    mut root: Query<&mut Visibility, With<EditorHudRoot>>,
    mut text: Query<&mut Text, With<EditorHudText>>,
) {
    let Ok(mut vis) = root.single_mut() else {
        return;
    };
    if !editor.active {
        *vis = Visibility::Hidden;
        return;
    }
    *vis = Visibility::Visible;
    if let Ok(mut t) = text.single_mut() {
        **t = format!(
            "MAP EDITOR · {} · layer {}\nTool: {} · Race g{} · Vibe o{} · Shooter c{}\nTab layer · F5 layer · F8 pack · F6 play layer · F9 Party Saga · F7 share · Q exit\n{}",
            editor.pack.label,
            editor.layer.label(),
            tool.0.label(editor.layer),
            editor.pack.race.gates.len(),
            editor.pack.vibe.orbs.len(),
            editor.pack.shooter.cover.len(),
            editor.status
        );
    }
}

fn rebuild_visuals(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    editor: &EditorMode,
) {
    match editor.layer {
        EditLayer::Race => {
            for (i, g) in editor.pack.race.gates.iter().enumerate() {
                spawn_prop(
                    commands,
                    meshes,
                    materials,
                    EditorPalette::Primary,
                    i as u8,
                    Cuboid::new(3.0, 2.5, 0.4),
                    Color::srgb(0.2, 0.85, 1.0),
                    Vec3::new(g[0], g[1], g[2]),
                    true,
                );
            }
            for (i, s) in editor.pack.race.spawns.iter().enumerate() {
                spawn_spawn_marker(commands, meshes, materials, i as u8, s);
            }
            for (i, b) in editor.pack.race.blocks.iter().enumerate() {
                spawn_block(commands, meshes, materials, i as u8, b);
            }
        }
        EditLayer::Vibe => {
            for (i, o) in editor.pack.vibe.orbs.iter().enumerate() {
                spawn_prop(
                    commands,
                    meshes,
                    materials,
                    EditorPalette::Primary,
                    i as u8,
                    Sphere::new(0.45),
                    Color::srgb(1.0, 0.9, 0.2),
                    Vec3::new(o[0], o[1], o[2]),
                    true,
                );
            }
            for (i, s) in editor.pack.vibe.spawns.iter().enumerate() {
                spawn_spawn_marker(commands, meshes, materials, i as u8, s);
            }
            for (i, b) in editor.pack.vibe.blocks.iter().enumerate() {
                spawn_block(commands, meshes, materials, i as u8, b);
            }
        }
        EditLayer::Shooter => {
            for (i, s) in editor.pack.shooter.spawns.iter().enumerate() {
                spawn_spawn_marker(commands, meshes, materials, i as u8, s);
            }
            for (i, b) in editor.pack.shooter.cover.iter().enumerate() {
                spawn_block(commands, meshes, materials, i as u8, b);
            }
        }
    }
}

fn spawn_spawn_marker(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    index: u8,
    s: &[f32; 3],
) {
    spawn_prop(
        commands,
        meshes,
        materials,
        EditorPalette::Spawn,
        index,
        Cylinder::new(0.7, 0.25),
        Color::srgb(0.35, 1.0, 0.45),
        Vec3::new(s[0], 0.15, s[2]),
        true,
    );
}

fn spawn_block(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    index: u8,
    b: &MapBlock,
) {
    let kind = if b.asset_id.is_some() {
        EditorPalette::Deco
    } else {
        EditorPalette::Block
    };
    let color = if b.asset_id.is_some() {
        Color::srgb(0.55, 0.75, 0.95)
    } else {
        Color::srgb(0.7, 0.45, 0.3)
    };
    let [sx, sy, sz] = b.size;
    spawn_prop(
        commands,
        meshes,
        materials,
        kind,
        index,
        Cuboid::new(sx, sy, sz),
        color,
        Vec3::new(b.pos[0], b.pos[1], b.pos[2]),
        false,
    );
}

fn spawn_prop(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    kind: EditorPalette,
    index: u8,
    mesh: impl Into<Mesh>,
    color: Color,
    translation: Vec3,
    emissive: bool,
) {
    let mut mat = StandardMaterial {
        base_color: color,
        unlit: true,
        ..Default::default()
    };
    if emissive {
        let c = color.to_srgba();
        mat.emissive = LinearRgba::rgb(c.red, c.green, c.blue);
    }
    commands.spawn((
        EditorProp { kind, index },
        GameplayEntity,
        Mesh3d(meshes.add(mesh)),
        MeshMaterial3d(materials.add(mat)),
        Transform::from_translation(translation),
        Name::new("EditorProp"),
    ));
}

fn push_block(editor: &mut EditorMode, block: MapBlock) {
    match editor.layer {
        EditLayer::Race => editor.pack.race.blocks.push(block),
        EditLayer::Vibe => editor.pack.vibe.blocks.push(block),
        EditLayer::Shooter => editor.pack.shooter.cover.push(block),
    }
}

fn set_spawn(editor: &mut EditorMode, spawn: [f32; 3]) {
    match editor.layer {
        EditLayer::Race => {
            editor.pack.race.spawns.clear();
            editor.pack.race.spawns.push(spawn);
        }
        EditLayer::Vibe => {
            editor.pack.vibe.spawns.clear();
            editor.pack.vibe.spawns.push(spawn);
        }
        EditLayer::Shooter => {
            editor.pack.shooter.spawns.push(spawn);
        }
    }
}

fn delete_prop(editor: &mut EditorMode, kind: EditorPalette, idx: usize) {
    match (editor.layer, kind) {
        (EditLayer::Race, EditorPalette::Primary) if idx < editor.pack.race.gates.len() => {
            editor.pack.race.gates.remove(idx);
        }
        (EditLayer::Vibe, EditorPalette::Primary) if idx < editor.pack.vibe.orbs.len() => {
            editor.pack.vibe.orbs.remove(idx);
        }
        (EditLayer::Race, EditorPalette::Spawn) => {
            editor.pack.race.spawns = vec![[0.0, 1.0, 10.0]];
        }
        (EditLayer::Vibe, EditorPalette::Spawn) => {
            editor.pack.vibe.spawns = vec![[0.0, 1.0, 0.0]];
        }
        (EditLayer::Shooter, EditorPalette::Spawn) if idx < editor.pack.shooter.spawns.len() => {
            editor.pack.shooter.spawns.remove(idx);
        }
        (EditLayer::Race, EditorPalette::Block | EditorPalette::Deco)
            if idx < editor.pack.race.blocks.len() =>
        {
            editor.pack.race.blocks.remove(idx);
        }
        (EditLayer::Vibe, EditorPalette::Block | EditorPalette::Deco)
            if idx < editor.pack.vibe.blocks.len() =>
        {
            editor.pack.vibe.blocks.remove(idx);
        }
        (EditLayer::Shooter, EditorPalette::Primary | EditorPalette::Block | EditorPalette::Deco)
            if idx < editor.pack.shooter.cover.len() =>
        {
            editor.pack.shooter.cover.remove(idx);
        }
        _ => {}
    }
}

fn exit_editor_world(
    editor: &mut EditorMode,
    commands: &mut Commands,
    props: &Query<Entity, With<EditorProp>>,
    ghosts: &Query<Entity, With<EditorGhost>>,
) {
    for entity in props.iter() {
        commands.entity(entity).despawn();
    }
    for entity in ghosts.iter() {
        commands.entity(entity).despawn();
    }
    editor.active = false;
}

fn current_deco_id(editor: &EditorMode, registry: Option<&StudioRegistry>) -> String {
    let ids = available_deco_ids(registry);
    ids.get(editor.deco_index % ids.len().max(1))
        .cloned()
        .unwrap_or_else(|| EDITOR_DECO_IDS[0].to_string())
}

fn deco_count(registry: Option<&StudioRegistry>) -> usize {
    available_deco_ids(registry).len().max(1)
}

fn available_deco_ids(registry: Option<&StudioRegistry>) -> Vec<String> {
    let present: Vec<String> = EDITOR_DECO_IDS
        .iter()
        .filter(|id| {
            crate::data::studio_glb_on_disk(id)
                || registry.map(|r| r.contains(id)).unwrap_or(false)
        })
        .map(|s| (*s).to_string())
        .collect();
    if present.is_empty() {
        EDITOR_DECO_IDS.iter().map(|s| (*s).to_string()).collect()
    } else {
        present
    }
}

fn place_point(player: &Transform, yaw: f32) -> Vec3 {
    let forward = Vec3::new(-yaw.sin(), 0.0, -yaw.cos());
    let raw = player.translation + forward * 2.5;
    Vec3::new(
        raw.x.round().clamp(-ARENA_BOUNDS, ARENA_BOUNDS),
        1.0,
        raw.z.round().clamp(-ARENA_BOUNDS, ARENA_BOUNDS),
    )
}

fn open_maps_companion() {
    let path = format!(
        "{}/companion/maps/index.html",
        env!("CARGO_MANIFEST_DIR")
    );
    let path = std::path::PathBuf::from(path);
    if !path.is_file() {
        return;
    }
    #[cfg(target_os = "windows")]
    {
        let _ = std::process::Command::new("cmd")
            .args(["/C", "start", "", &path.to_string_lossy()])
            .spawn();
    }
    #[cfg(target_os = "macos")]
    {
        let _ = std::process::Command::new("open").arg(&path).spawn();
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let _ = std::process::Command::new("xdg-open").arg(&path).spawn();
    }
}

fn short_stamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| (d.as_secs() % 100_000).to_string())
        .unwrap_or_else(|_| "0".into())
}
