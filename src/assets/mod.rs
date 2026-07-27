use std::collections::VecDeque;

use bevy::gltf::GltfAssetLabel;
use bevy::prelude::*;

use crate::{
    data::StudioRegistry,
    interaction::Interactable,
    world::GameplayEntity,
};

pub struct AssetsPlugin;

impl Plugin for AssetsPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<StudioPropQueue>();
    }
}

/// Deferred Studio GLB spawns so Nest décor does not starve the crew mesh at boot.
#[derive(Resource, Debug, Default)]
pub struct StudioPropQueue {
    pending: VecDeque<QueuedStudioProp>,
    /// Handles for décor GLBs that have been kicked off but may still be decoding.
    pub in_flight: Vec<Handle<bevy::gltf::Gltf>>,
}

#[derive(Debug, Clone)]
pub struct QueuedStudioProp {
    pub asset_id: String,
    pub transform: Transform,
    pub name: String,
}

impl StudioPropQueue {
    pub fn push(&mut self, asset_id: impl Into<String>, transform: Transform, name: impl Into<String>) {
        self.pending.push_back(QueuedStudioProp {
            asset_id: asset_id.into(),
            transform,
            name: name.into(),
        });
    }

    pub fn pop(&mut self) -> Option<QueuedStudioProp> {
        self.pending.pop_front()
    }

    pub fn len(&self) -> usize {
        self.pending.len()
    }

    pub fn is_empty(&self) -> bool {
        self.pending.is_empty()
    }
}

pub fn load_studio_registry(mut commands: Commands) {
    let path = format!("{}/assets/studio_registry.json", env!("CARGO_MANIFEST_DIR"));
    match StudioRegistry::load(&path) {
        Ok(registry) => {
            info!(
                "loaded {} Immersive Studio assets from registry",
                registry.assets.len()
            );
            commands.insert_resource(registry);
        }
        Err(err) => {
            warn!("studio registry unavailable ({err}); using fallback scales");
            commands.insert_resource(StudioRegistry {
                import_root: "models".into(),
                assets: Vec::new(),
            });
        }
    }
}

/// True when `assets/models/{id}/{id}.glb` exists on disk (cached at process start).
pub fn studio_asset_exists(_registry: &StudioRegistry, asset_id: &str) -> bool {
    crate::data::studio_glb_on_disk(asset_id)
}

/// Spawns a GLB scene scaled from the registry, or returns `None` if the file is missing.
pub fn spawn_studio_prop(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    asset_id: &str,
    transform: Transform,
    bundle: impl Bundle,
) -> Option<Entity> {
    if !studio_asset_exists(registry, asset_id) {
        return None;
    }

    let scale = registry.spawn_scale(asset_id) * transform.scale;
    let glb_path = registry.glb_asset_path(asset_id);
    let scene = asset_server.load(GltfAssetLabel::Scene(0).from_asset(glb_path));

    Some(
        commands
            .spawn((
                GameplayEntity,
                WorldAssetRoot(scene),
                transform.with_scale(scale),
                Visibility::default(),
                bundle,
            ))
            .id(),
    )
}

/// Queue a décor prop for staggered spawn. Prefer this for Nest fluff.
pub fn queue_studio_prop(
    queue: &mut StudioPropQueue,
    registry: &StudioRegistry,
    asset_id: &str,
    transform: Transform,
    name: impl Into<String>,
) {
    if !studio_asset_exists(registry, asset_id) {
        return;
    }
    queue.push(asset_id, transform, name);
}

/// Greybox fallback when GLB is unavailable (headless CI without assets).
pub fn spawn_greybox_prop(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    color: Color,
    size: Vec3,
    transform: Transform,
    bundle: impl Bundle,
) -> Entity {
    let mesh = meshes.add(Cuboid::new(size.x, size.y, size.z));
    let material = materials.add(StandardMaterial {
        base_color: color,
        ..Default::default()
    });

    commands
        .spawn((
            GameplayEntity,
            Mesh3d(mesh),
            MeshMaterial3d(material),
            transform,
            bundle,
        ))
        .id()
}

/// Prefer GLB; attach interactable metadata either way.
pub fn spawn_job_station(
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
) -> Entity {
    if let Some(entity) = spawn_studio_prop(
        commands,
        asset_server,
        registry,
        asset_id,
        transform,
        (interactable, Name::new(asset_id.to_string())),
    ) {
        return entity;
    }

    info!("GLB missing for `{asset_id}`, using greybox station");
    spawn_greybox_prop(
        commands,
        meshes,
        materials,
        greybox_color,
        greybox_size,
        transform,
        (interactable, Name::new(asset_id.to_string())),
    )
}

/// Decorative Studio prop. Returns `None` when the GLB is missing.
pub fn spawn_decoration(
    commands: &mut Commands,
    asset_server: &AssetServer,
    registry: &StudioRegistry,
    asset_id: &str,
    transform: Transform,
) -> Option<Entity> {
    spawn_studio_prop(
        commands,
        asset_server,
        registry,
        asset_id,
        transform,
        Name::new(asset_id.to_string()),
    )
}
