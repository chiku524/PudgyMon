//! Accessory catalog + live socket attachment for Pudgy characters.

use std::path::Path;

use bevy::prelude::*;
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    network::OwnedPlayer,
    player::{AccessorySlots, NetworkPlayer, PlayerVisualRoot, PlayerVisualSpec},
};

#[derive(Debug, Clone, Deserialize)]
pub struct AccessoryItem {
    pub id: String,
    pub label: String,
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
}

pub fn accessory_glb_exists(asset_id: &str) -> bool {
    let path = format!(
        "{}/assets/models/{asset_id}/{asset_id}.glb",
        env!("CARGO_MANIFEST_DIR")
    );
    Path::new(&path).is_file()
}

#[derive(Component, Debug, Clone)]
pub struct EquippedAccessoryVisual {
    pub slot: String,
    pub asset_id: String,
}

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
            .add_systems(Update, sync_accessory_meshes);
    }
}

fn handle_equip_accessory(
    request: On<FromClient<EquipAccessoryRequest>>,
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
    apply_slot(
        &mut visual.accessories,
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

fn sync_accessory_meshes(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    players: Query<(Entity, &PlayerVisualSpec, Option<&Children>), With<NetworkPlayer>>,
    visual_roots: Query<(), With<PlayerVisualRoot>>,
    names: Query<&Name>,
    children_q: Query<&Children>,
    equipped: Query<(Entity, &EquippedAccessoryVisual)>,
) {
    for (_player, visual, player_children) in &players {
        let Some(kids) = player_children else {
            continue;
        };
        let Some(root) = kids.iter().find(|c| visual_roots.contains(*c)) else {
            continue;
        };

        let desired = [
            ("hat", visual.accessories.hat.as_deref()),
            ("necklace", visual.accessories.necklace.as_deref()),
            ("shoes", visual.accessories.shoes.as_deref()),
            ("back", visual.accessories.back.as_deref()),
            ("face", visual.accessories.face.as_deref()),
            ("hands", visual.accessories.hands.as_deref()),
        ];

        for (slot, want_id) in desired {
            let existing: Vec<(Entity, String)> = equipped
                .iter()
                .filter(|(e, mark)| mark.slot == slot && is_under(root, *e, &children_q))
                .map(|(e, mark)| (e, mark.asset_id.clone()))
                .collect();

            let want = want_id.filter(|id| accessory_glb_exists(id));
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
            let parent = find_named(root, socket, &names, &children_q).unwrap_or(root);
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
                    Transform::default(),
                    Visibility::default(),
                    Name::new(format!("Acc:{slot}:{asset_id}")),
                ));
            });
        }
    }
}
