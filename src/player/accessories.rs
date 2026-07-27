//! Accessory catalog + live socket attachment for Pudgy characters.

use std::path::Path;

use bevy::prelude::*;
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    data::studio_glb_on_disk,
    network::OwnedPlayer,
    player::{AccessorySlots, NetworkPlayer, PlayerVisualRoot, PlayerVisualSpec},
};

#[derive(Debug, Clone, Deserialize)]
pub struct AccessoryItem {
    pub id: String,
    pub label: String,
    /// Tripo delivered a full dressed figure instead of an isolated prop.
    /// Equipping swaps the player's character model to this GLB.
    #[serde(default)]
    pub character_look: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AccessorySlotCatalog {
    pub id: String,
    pub label: String,
    pub items: Vec<AccessoryItem>,
}

#[derive(Resource, Debug, Clone, Deserialize, Default)]
pub struct AccessoryCatalog {
    pub slots: Vec<AccessorySlotCatalog>,
}

impl AccessoryCatalog {
    pub fn load(path: impl AsRef<Path>) -> Self {
        let Ok(raw) = std::fs::read_to_string(path.as_ref()) else {
            return Self::default();
        };
        serde_json::from_str(&raw).unwrap_or_default()
    }

    pub fn available_in_slot(&self, slot: &str) -> Vec<&AccessoryItem> {
        self.slots
            .iter()
            .find(|s| s.id == slot)
            .map(|s| {
                s.items
                    .iter()
                    .filter(|i| accessory_glb_exists(&i.id))
                    .collect()
            })
            .unwrap_or_default()
    }

    pub fn label_for(&self, id: &str) -> String {
        for slot in &self.slots {
            if let Some(item) = slot.items.iter().find(|i| i.id == id) {
                return item.label.clone();
            }
        }
        id.to_string()
    }

    pub fn item(&self, id: &str) -> Option<&AccessoryItem> {
        self.slots
            .iter()
            .flat_map(|s| s.items.iter())
            .find(|i| i.id == id)
    }

    pub fn is_character_look(&self, id: &str) -> bool {
        self.item(id).is_some_and(|i| i.character_look)
    }
}

pub fn accessory_glb_exists(asset_id: &str) -> bool {
    studio_glb_on_disk(asset_id)
}

#[derive(Component, Debug, Clone)]
pub struct EquippedAccessoryVisual {
    pub slot: String,
    pub asset_id: String,
}

/// Marks that contract `Socket_*` empties have been ensured under this visual root.
#[derive(Component, Debug, Clone, Copy, Default)]
pub struct AccessorySocketsReady;

/// Last loadout we fully synced onto sockets (skip redundant Update work).
#[derive(Component, Debug, Clone, PartialEq, Eq, Default)]
pub struct MountedAccessoryLoadout(pub AccessorySlots);

#[derive(Event, Serialize, Deserialize, Clone, Debug)]
pub struct EquipAccessoryRequest {
    pub slot: String,
    pub asset_id: Option<String>,
}

pub struct AccessoriesPlugin;

impl Plugin for AccessoriesPlugin {
    fn build(&self, app: &mut App) {
        let path = format!(
            "{}/data/accessories/catalog.json",
            env!("CARGO_MANIFEST_DIR")
        );
        app.insert_resource(AccessoryCatalog::load(path))
            .add_client_event::<EquipAccessoryRequest>(Channel::Unordered)
            .add_observer(handle_equip_accessory)
            .add_systems(
                Update,
                (
                    sync_accessory_meshes,
                    retarget_pair_sockets.after(sync_accessory_meshes),
                ),
            )
            .add_systems(
                PostUpdate,
                apply_wear_volume_scales.before(TransformSystems::Propagate),
            );
    }
}

fn handle_equip_accessory(
    request: On<FromClient<EquipAccessoryRequest>>,
    catalog: Res<AccessoryCatalog>,
    defaults: Res<crate::data::PlayerDefaults>,
    mut players: Query<&mut PlayerVisualSpec, With<NetworkPlayer>>,
    owners: Query<&OwnedPlayer>,
) {
    let Some(client_entity) = request.client_id.entity() else {
        return;
    };
    let Ok(owned) = owners.get(client_entity) else {
        return;
    };
    let Ok(mut visual) = players.get_mut(owned.0) else {
        return;
    };
    apply_accessory_choice(
        &mut visual,
        &catalog,
        &defaults,
        &request.slot,
        request.asset_id.clone(),
    );
}

pub fn apply_slot(slots: &mut AccessorySlots, slot: &str, asset_id: Option<String>) {
    let cleaned = asset_id.and_then(|id| {
        let id = id.trim().to_string();
        if id.is_empty() || !accessory_glb_exists(&id) {
            None
        } else {
            Some(id)
        }
    });
    match slot {
        "hat" => slots.hat = cleaned,
        "necklace" => slots.necklace = cleaned,
        "shoes" => slots.shoes = cleaned,
        "back" => slots.back = cleaned,
        "face" => slots.face = cleaned,
        "hands" => slots.hands = cleaned,
        _ => {}
    }
}

/// Equip an accessory — isolated props attach to sockets; `character_look` items
/// swap the whole player mesh (Tripo often ships a dressed figure, not a prop).
pub fn apply_accessory_choice(
    visual: &mut PlayerVisualSpec,
    catalog: &AccessoryCatalog,
    defaults: &crate::data::PlayerDefaults,
    slot: &str,
    asset_id: Option<String>,
) {
    let cleaned = asset_id.and_then(|id| {
        let id = id.trim().to_string();
        if id.is_empty() || !accessory_glb_exists(&id) {
            None
        } else {
            Some(id)
        }
    });

    let clearing_look = cleaned.is_none()
        && slot_value(&visual.accessories, slot)
            .is_some_and(|id| catalog.is_character_look(id));

    apply_slot(&mut visual.accessories, slot, cleaned.clone());

    if let Some(id) = cleaned {
        if catalog.is_character_look(&id) {
            visual.model_id = Some(id);
            return;
        }
    } else if clearing_look {
        let remaining = [
            visual.accessories.hat.as_deref(),
            visual.accessories.necklace.as_deref(),
            visual.accessories.shoes.as_deref(),
            visual.accessories.back.as_deref(),
            visual.accessories.face.as_deref(),
            visual.accessories.hands.as_deref(),
        ]
        .into_iter()
        .flatten()
        .find(|id| catalog.is_character_look(id));
        visual.model_id = remaining
            .map(|id| id.to_string())
            .or_else(|| defaults.resolved_crew_model());
    }
}

fn slot_value<'a>(slots: &'a AccessorySlots, slot: &str) -> Option<&'a str> {
    match slot {
        "hat" => slots.hat.as_deref(),
        "necklace" => slots.necklace.as_deref(),
        "shoes" => slots.shoes.as_deref(),
        "back" => slots.back.as_deref(),
        "face" => slots.face.as_deref(),
        "hands" => slots.hands.as_deref(),
        _ => None,
    }
}

fn socket_name(slot: &str) -> &'static str {
    match slot {
        "hat" => "Socket_Hat",
        "necklace" => "Socket_Necklace",
        "shoes" => "Socket_Shoes",
        "back" => "Socket_Back",
        "face" => "Socket_Face",
        "hands" => "Socket_Hands",
        _ => "",
    }
}

/// Contract sockets + preferred bone parents + bone-local offset (Bevy Y-up).
///
/// Hat/face sit on `Head` (Y along bone ≈ up the skull). Pair shoes/hands start
/// on a torso/root bone and are retargeted each frame to the limb midpoint.
const ACCESSORY_SOCKETS: &[(&str, &[&str], Vec3)] = &[
    ("Socket_Hat", &["Head"], Vec3::new(0.0, 0.1, 0.0)),
    ("Socket_Face", &["Head"], Vec3::new(0.0, 0.02, -0.11)),
    (
        "Socket_Necklace",
        &["NeckTwist01", "NeckTwist02", "Spine02", "Spine01"],
        Vec3::new(0.0, -0.02, -0.05),
    ),
    (
        "Socket_Back",
        &["Spine02", "Spine01", "Waist"],
        Vec3::new(0.0, 0.04, 0.12),
    ),
    (
        "Socket_Hands",
        &["Spine01", "Waist", "Spine02"],
        Vec3::new(0.0, -0.05, -0.18),
    ),
    (
        "Socket_Shoes",
        &["Root", "Hip", "Pelvis"],
        Vec3::ZERO,
    ),
];

/// Bones collapsed when a covering accessory is worn (monolithic body mesh).
const SHOE_HIDE_BONES: &[&str] = &["L_Foot", "R_Foot", "L_ToeBase", "R_ToeBase"];
const HAND_HIDE_BONES: &[&str] = &["L_Hand", "R_Hand"];

fn find_named(
    root: Entity,
    want: &str,
    names: &Query<&Name>,
    children: &Query<&Children>,
) -> Option<Entity> {
    let mut stack = vec![root];
    while let Some(entity) = stack.pop() {
        if names
            .get(entity)
            .ok()
            .map(|n| n.as_str() == want)
            .unwrap_or(false)
        {
            return Some(entity);
        }
        if let Ok(kids) = children.get(entity) {
            stack.extend(kids.iter());
        }
    }
    None
}

fn ensure_accessory_sockets(
    commands: &mut Commands,
    root: Entity,
    names: &Query<&Name>,
    children: &Query<&Children>,
    transforms: &mut Query<&mut Transform>,
) -> bool {
    let mut ready = true;
    for (socket, bone_candidates, local) in ACCESSORY_SOCKETS {
        if let Some(existing) = find_named(root, socket, names, children) {
            // Refresh authored offsets for static sockets. Pair sockets are
            // driven by `retarget_pair_sockets` instead.
            if !matches!(*socket, "Socket_Shoes" | "Socket_Hands") {
                if let Ok(mut xf) = transforms.get_mut(existing) {
                    xf.translation = *local;
                }
            }
            continue;
        }
        let Some(bone) = bone_candidates
            .iter()
            .find_map(|b| find_named(root, b, names, children))
        else {
            ready = false;
            continue;
        };
        commands.entity(bone).with_children(|p| {
            p.spawn((
                Name::new(socket.to_string()),
                Transform::from_translation(*local),
                Visibility::default(),
            ));
        });
        // Spawned via commands — visible next frame.
        ready = false;
    }
    ready
}

fn is_under(ancestor: Entity, node: Entity, children: &Query<&Children>) -> bool {
    if ancestor == node {
        return true;
    }
    let mut stack = vec![ancestor];
    while let Some(e) = stack.pop() {
        if let Ok(kids) = children.get(e) {
            for child in kids.iter() {
                if child == node {
                    return true;
                }
                stack.push(child);
            }
        }
    }
    false
}

/// Pair props (shoes / mittens) are authored as one mesh — keep the socket between
/// the matching L/R bones so stance and animation stay centered.
fn retarget_pair_sockets(
    roots: Query<Entity, (With<PlayerVisualRoot>, With<AccessorySocketsReady>)>,
    names: Query<&Name>,
    children: Query<&Children>,
    parents: Query<&ChildOf>,
    global_xf: Query<&GlobalTransform>,
    mut transforms: Query<&mut Transform>,
) {
    for root in &roots {
        retarget_midpoint_socket(
            root,
            "Socket_Shoes",
            "L_Foot",
            "R_Foot",
            true,
            &names,
            &children,
            &parents,
            &global_xf,
            &mut transforms,
        );
        retarget_midpoint_socket(
            root,
            "Socket_Hands",
            "L_Hand",
            "R_Hand",
            false,
            &names,
            &children,
            &parents,
            &global_xf,
            &mut transforms,
        );
    }
}

fn retarget_midpoint_socket(
    root: Entity,
    socket_name: &str,
    left: &str,
    right: &str,
    floor_y: bool,
    names: &Query<&Name>,
    children: &Query<&Children>,
    parents: &Query<&ChildOf>,
    global_xf: &Query<&GlobalTransform>,
    transforms: &mut Query<&mut Transform>,
) {
    let (Some(sock), Some(l), Some(r)) = (
        find_named(root, socket_name, names, children),
        find_named(root, left, names, children),
        find_named(root, right, names, children),
    ) else {
        return;
    };
    let Ok(lg) = global_xf.get(l) else {
        return;
    };
    let Ok(rg) = global_xf.get(r) else {
        return;
    };
    let mut mid = (lg.translation() + rg.translation()) * 0.5;
    if floor_y {
        mid.y = lg.translation().y.min(rg.translation().y);
    }
    let Ok(parent) = parents.get(sock) else {
        return;
    };
    let Ok(parent_gt) = global_xf.get(parent.parent()) else {
        return;
    };
    let local = parent_gt.affine().inverse().transform_point3(mid);
    if let Ok(mut xf) = transforms.get_mut(sock) {
        xf.translation = local;
        // Face the average limb forward projected onto XZ so pairs stay aligned.
        let l_fwd = lg.forward();
        let r_fwd = rg.forward();
        let avg = Vec3::new(l_fwd.x + r_fwd.x, 0.0, l_fwd.z + r_fwd.z);
        if avg.length_squared() > 1e-6 {
            let world_rot = Quat::from_rotation_arc(Vec3::NEG_Z, avg.normalize());
            let parent_rot = parent_gt.rotation();
            xf.rotation = parent_rot.inverse() * world_rot;
        }
    }
}

/// After animation writes bone transforms, squash covered wear volumes so big
/// pudgy feet/hands don't poke through shoes/gloves.
fn apply_wear_volume_scales(
    players: Query<(&PlayerVisualSpec, Option<&Children>), With<NetworkPlayer>>,
    visual_roots: Query<(), With<PlayerVisualRoot>>,
    names: Query<&Name>,
    children_q: Query<&Children>,
    mut transforms: Query<&mut Transform>,
) {
    for (visual, player_children) in &players {
        let Some(kids) = player_children else {
            continue;
        };
        let Some(root) = kids.iter().find(|c| visual_roots.contains(*c)) else {
            continue;
        };

        let hide_feet = visual
            .accessories
            .shoes
            .as_deref()
            .is_some_and(accessory_glb_exists);
        let hide_hands = visual
            .accessories
            .hands
            .as_deref()
            .is_some_and(accessory_glb_exists);

        set_bone_scales(
            root,
            SHOE_HIDE_BONES,
            if hide_feet {
                Vec3::splat(0.02)
            } else {
                Vec3::ONE
            },
            &names,
            &children_q,
            &mut transforms,
        );
        set_bone_scales(
            root,
            HAND_HIDE_BONES,
            if hide_hands {
                Vec3::splat(0.02)
            } else {
                Vec3::ONE
            },
            &names,
            &children_q,
            &mut transforms,
        );
    }
}

fn set_bone_scales(
    root: Entity,
    bones: &[&str],
    scale: Vec3,
    names: &Query<&Name>,
    children: &Query<&Children>,
    transforms: &mut Query<&mut Transform>,
) {
    for bone in bones {
        let Some(entity) = find_named(root, bone, names, children) else {
            continue;
        };
        if let Ok(mut xf) = transforms.get_mut(entity) {
            xf.scale = scale;
        }
    }
}

/// Local accessory transform (registry scale). Pair sockets are retargeted to
/// limb forward; static sockets inherit bone orientation from the crew armature.
fn accessory_attach_transform(_slot: &str, scale: Vec3) -> Transform {
    Transform {
        translation: Vec3::ZERO,
        rotation: Quat::IDENTITY,
        scale,
    }
}

fn sync_accessory_meshes(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    catalog: Res<AccessoryCatalog>,
    registry: Option<Res<crate::data::StudioRegistry>>,
    players: Query<
        (
            Entity,
            &PlayerVisualSpec,
            Option<&Children>,
            Option<&MountedAccessoryLoadout>,
        ),
        With<NetworkPlayer>,
    >,
    visual_roots: Query<(Entity, Option<&AccessorySocketsReady>), With<PlayerVisualRoot>>,
    names: Query<&Name>,
    children_q: Query<&Children>,
    mut transforms: Query<&mut Transform>,
    equipped: Query<(Entity, &EquippedAccessoryVisual)>,
) {
    for (_player, visual, player_children, mounted_loadout) in &players {
        let Some(kids) = player_children else {
            continue;
        };
        let Some(root) = kids
            .iter()
            .find_map(|c| visual_roots.get(c).ok().map(|(e, ready)| (e, ready)))
        else {
            continue;
        };
        let (root, sockets_ready_marker) = root;

        let sockets_ready = if sockets_ready_marker.is_some() {
            true
        } else if ensure_accessory_sockets(
            &mut commands,
            root,
            &names,
            &children_q,
            &mut transforms,
        ) {
            commands.entity(root).insert(AccessorySocketsReady);
            true
        } else {
            false
        };

        if !sockets_ready {
            continue;
        }

        if mounted_loadout.is_some_and(|m| m.0 == visual.accessories) {
            continue;
        }

        let desired = [
            ("hat", visual.accessories.hat.as_deref()),
            ("necklace", visual.accessories.necklace.as_deref()),
            ("shoes", visual.accessories.shoes.as_deref()),
            ("back", visual.accessories.back.as_deref()),
            ("face", visual.accessories.face.as_deref()),
            ("hands", visual.accessories.hands.as_deref()),
        ];

        let mut all_ok = true;
        for (slot, want_id) in desired {
            let existing: Vec<(Entity, String)> = equipped
                .iter()
                .filter(|(e, mark)| mark.slot == slot && is_under(root, *e, &children_q))
                .map(|(e, mark)| (e, mark.asset_id.clone()))
                .collect();

            let want = want_id
                .filter(|id| accessory_glb_exists(id))
                .filter(|id| !catalog.is_character_look(id));
            let up_to_date = match (&want, existing.as_slice()) {
                (Some(id), [(e, have)]) if have == id && is_under(root, *e, &children_q) => true,
                (None, []) => true,
                _ => false,
            };
            if up_to_date {
                continue;
            }

            for (e, _) in &existing {
                commands.entity(*e).despawn();
            }

            let Some(asset_id) = want else {
                continue;
            };
            let socket = socket_name(slot);
            let Some(parent) = find_named(root, socket, &names, &children_q) else {
                all_ok = false;
                continue;
            };
            let scale = registry
                .as_ref()
                .map(|r| r.spawn_scale(asset_id))
                .unwrap_or(Vec3::ONE);
            let glb_path = format!("models/{asset_id}/{asset_id}.glb");
            let scene =
                asset_server.load(bevy::gltf::GltfAssetLabel::Scene(0).from_asset(glb_path));
            commands.entity(parent).with_children(|p| {
                p.spawn((
                    EquippedAccessoryVisual {
                        slot: slot.to_string(),
                        asset_id: asset_id.to_string(),
                    },
                    WorldAssetRoot(scene),
                    accessory_attach_transform(slot, scale),
                    Visibility::default(),
                    Name::new(format!("Acc:{slot}:{asset_id}")),
                ));
            });
        }

        if all_ok {
            commands
                .entity(_player)
                .insert(MountedAccessoryLoadout(visual.accessories.clone()));
        }
    }
}
