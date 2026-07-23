//! Shared Pudgy clip playback — idle / walk / run / jump / emotes.

use std::time::Duration;

use bevy::{
    animation::{transition::AnimationTransitions, AnimationPlayer},
    gltf::Gltf,
    prelude::*,
    world_serialization::WorldInstanceReady,
};

use crate::{flow::AppScreen, player::PlayerVisualRoot};

pub const CREW_CLIP_IDLE: &str = "idle";
pub const CREW_CLIP_WALK: &str = "walk";
pub const CREW_CLIP_RUN: &str = "run";
pub const CREW_CLIP_JUMP: &str = "jump";
pub const CREW_CLIP_WAVE: &str = "emote_wave";
pub const CREW_CLIP_DANCE: &str = "emote_dance";

const CROSSFADE: Duration = Duration::from_millis(150);
const WALK_SPEED_EPS: f32 = 0.05;

#[derive(Component, Debug, Clone)]
pub struct CrewAnimationSetup {
    pub model_id: String,
    pub gltf: Handle<Gltf>,
}

#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum CrewAnimKind {
    #[default]
    Idle,
    Walk,
    Run,
    Jump,
    EmoteWave,
    EmoteDance,
}

impl CrewAnimKind {
    fn loops(self) -> bool {
        !matches!(self, Self::Jump | Self::EmoteWave)
    }
}

#[derive(Component, Debug)]
pub struct CrewAnimPlayback {
    pub kind: CrewAnimKind,
    pub applied: Option<CrewAnimKind>,
    pub graph: Handle<AnimationGraph>,
    pub idle: AnimationNodeIndex,
    pub walk: AnimationNodeIndex,
    pub run: AnimationNodeIndex,
    pub jump: AnimationNodeIndex,
    pub wave: AnimationNodeIndex,
    pub dance: AnimationNodeIndex,
    pub lock_until: f32,
    pub player_entity: Entity,
}

impl CrewAnimPlayback {
    fn node(&self, kind: CrewAnimKind) -> AnimationNodeIndex {
        match kind {
            CrewAnimKind::Idle => self.idle,
            CrewAnimKind::Walk => self.walk,
            CrewAnimKind::Run => self.run,
            CrewAnimKind::Jump => self.jump,
            CrewAnimKind::EmoteWave => self.wave,
            CrewAnimKind::EmoteDance => self.dance,
        }
    }
}

#[derive(Component, Debug, Clone, Copy, Default)]
pub struct PlayerMotion {
    pub speed: f32,
    pub sprint: bool,
}

#[derive(Component)]
struct CrewSceneReady;

pub struct CrewAnimationPlugin;

impl Plugin for CrewAnimationPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(
            Update,
            (
                recover_stale_crew_playback,
                poll_crew_scene_ready,
                finish_crew_animation_setup,
                choose_crew_anim_kind.run_if(in_state(AppScreen::Playing)),
                apply_crew_anim_kind.run_if(in_state(AppScreen::Playing)),
            )
                .chain(),
        );
    }
}

/// Attach after spawning `WorldAssetRoot` (prefer spawning setup+observe together).
pub fn attach_crew_animation(
    entity: Entity,
    commands: &mut Commands,
    asset_server: &AssetServer,
    model_id: &str,
) {
    let glb_path = format!("models/{model_id}/{model_id}.glb");
    let gltf: Handle<Gltf> = asset_server.load(glb_path);
    commands
        .entity(entity)
        .insert(CrewAnimationSetup {
            model_id: model_id.to_string(),
            gltf,
        })
        .observe(on_crew_scene_ready);
}

pub fn on_crew_scene_ready(
    ready: On<WorldInstanceReady>,
    mut commands: Commands,
    setups: Query<&CrewAnimationSetup>,
) {
    if !setups.contains(ready.entity) {
        return;
    }
    // WorldAsset may respawn when dependencies finish loading (AssetEvent::Modified).
    // Drop any prior binding so we re-attach to the new AnimationPlayer.
    commands
        .entity(ready.entity)
        .remove::<CrewAnimPlayback>()
        .insert(CrewSceneReady);
}

/// If the skinned instance was respawned, `player_entity` goes stale — force a rebind.
fn recover_stale_crew_playback(
    mut commands: Commands,
    playback: Query<(Entity, &CrewAnimPlayback), With<CrewAnimationSetup>>,
    players: Query<(), With<AnimationPlayer>>,
) {
    for (entity, anim) in &playback {
        if !players.contains(anim.player_entity) {
            commands
                .entity(entity)
                .remove::<CrewAnimPlayback>()
                .insert(CrewSceneReady);
        }
    }
}

/// Fallback when `WorldInstanceReady` was missed (observe registered too late).
fn poll_crew_scene_ready(
    mut commands: Commands,
    pending: Query<
        Entity,
        (
            With<CrewAnimationSetup>,
            With<WorldAssetRoot>,
            Without<CrewSceneReady>,
            Without<CrewAnimPlayback>,
        ),
    >,
    children: Query<&Children>,
    players: Query<(), With<AnimationPlayer>>,
) {
    for entity in &pending {
        let has_player = players.contains(entity)
            || children
                .iter_descendants(entity)
                .any(|desc| players.contains(desc));
        if has_player {
            commands.entity(entity).insert(CrewSceneReady);
        }
    }
}

fn finish_crew_animation_setup(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    gltfs: Res<Assets<Gltf>>,
    mut graphs: ResMut<Assets<AnimationGraph>>,
    pending: Query<
        (Entity, &CrewAnimationSetup),
        (With<CrewSceneReady>, Without<CrewAnimPlayback>),
    >,
    children: Query<&Children>,
    mut players: Query<&mut AnimationPlayer>,
) {
    for (entity, setup) in &pending {
        if !asset_server.is_loaded_with_dependencies(&setup.gltf) {
            continue;
        }
        let Some(gltf) = gltfs.get(&setup.gltf) else {
            continue;
        };

        let Some(idle) = gltf.named_animations.get(CREW_CLIP_IDLE).cloned() else {
            warn!(
                "crew GLB `{}` missing clip `{CREW_CLIP_IDLE}` — keys: {:?}",
                setup.model_id,
                gltf.named_animations.keys().collect::<Vec<_>>()
            );
            commands
                .entity(entity)
                .remove::<(CrewSceneReady, CrewAnimationSetup)>();
            continue;
        };
        let walk = named_or(gltf, CREW_CLIP_WALK, &idle);
        let run = named_or(gltf, CREW_CLIP_RUN, &walk);
        let jump = named_or(gltf, CREW_CLIP_JUMP, &idle);
        let wave = named_or(gltf, CREW_CLIP_WAVE, &idle);
        let dance = named_or(gltf, CREW_CLIP_DANCE, &idle);

        let (graph, nodes) = AnimationGraph::from_clips([idle, walk, run, jump, wave, dance]);
        let graph_handle = graphs.add(graph);

        let mut player_entity = None;
        if players.contains(entity) {
            player_entity = Some(entity);
        } else {
            for desc in children.iter_descendants(entity) {
                if players.contains(desc) {
                    player_entity = Some(desc);
                    break;
                }
            }
        }
        let Some(player_entity) = player_entity else {
            continue;
        };

        // Match Bevy's animated_mesh_control example: start via AnimationTransitions
        // before/with the graph handle so the transitions component owns playback.
        let Ok(mut player) = players.get_mut(player_entity) else {
            continue;
        };
        let mut transitions = AnimationTransitions::new();
        transitions
            .play(&mut player, nodes[0], Duration::ZERO)
            .repeat();

        commands.entity(player_entity).insert((
            AnimationGraphHandle(graph_handle.clone()),
            transitions,
        ));
        commands.entity(entity).insert(CrewAnimPlayback {
            kind: CrewAnimKind::Idle,
            applied: Some(CrewAnimKind::Idle),
            graph: graph_handle,
            idle: nodes[0],
            walk: nodes[1],
            run: nodes[2],
            jump: nodes[3],
            wave: nodes[4],
            dance: nodes[5],
            lock_until: 0.0,
            player_entity,
        });
        commands.entity(entity).remove::<CrewSceneReady>();
        info!(
            "crew animation ready for `{}` (player={player_entity:?})",
            setup.model_id
        );
    }
}

fn named_or(gltf: &Gltf, name: &str, fallback: &Handle<AnimationClip>) -> Handle<AnimationClip> {
    gltf.named_animations
        .get(name)
        .cloned()
        .unwrap_or_else(|| fallback.clone())
}

fn choose_crew_anim_kind(
    time: Res<Time>,
    keyboard: Res<ButtonInput<KeyCode>>,
    pause: Option<Res<crate::settings::PauseState>>,
    players: Query<(&PlayerMotion, &Children, Option<&crate::player::LocalPlayer>)>,
    visual_roots: Query<(), With<PlayerVisualRoot>>,
    mut visuals: Query<&mut CrewAnimPlayback>,
) {
    let paused = pause.map(|p| p.paused).unwrap_or(false);
    let now = time.elapsed_secs();

    for (motion, children, local) in &players {
        let Some(visual) = children.iter().find(|c| visual_roots.contains(*c)) else {
            continue;
        };
        let Ok(mut anim) = visuals.get_mut(visual) else {
            continue;
        };

        let moving = motion.speed > WALK_SPEED_EPS;
        let locked = now < anim.lock_until;

        if local.is_some() && !paused {
            if keyboard.just_pressed(KeyCode::Space) {
                anim.kind = CrewAnimKind::Jump;
                anim.lock_until = now + 0.65;
                anim.applied = None;
                continue;
            }
            if keyboard.just_pressed(KeyCode::KeyG) {
                anim.kind = CrewAnimKind::EmoteWave;
                anim.lock_until = now + 1.25;
                anim.applied = None;
                continue;
            }
            if keyboard.just_pressed(KeyCode::KeyT) {
                if anim.kind == CrewAnimKind::EmoteDance {
                    anim.kind = CrewAnimKind::Idle;
                    anim.lock_until = 0.0;
                } else {
                    anim.kind = CrewAnimKind::EmoteDance;
                    anim.lock_until = f32::MAX;
                }
                anim.applied = None;
                continue;
            }
        }

        if locked && matches!(anim.kind, CrewAnimKind::Jump | CrewAnimKind::EmoteWave) {
            continue;
        }

        if anim.kind == CrewAnimKind::EmoteDance {
            if moving {
                anim.lock_until = 0.0;
            } else {
                continue;
            }
        }

        let desired = if !moving {
            CrewAnimKind::Idle
        } else if motion.sprint {
            CrewAnimKind::Run
        } else {
            CrewAnimKind::Walk
        };
        if anim.kind != desired {
            anim.kind = desired;
            anim.applied = None;
        }
    }
}

fn apply_crew_anim_kind(
    mut commands: Commands,
    mut visuals: Query<(Entity, &mut CrewAnimPlayback)>,
    mut players: Query<(&mut AnimationPlayer, &mut AnimationTransitions)>,
) {
    for (entity, mut anim) in &mut visuals {
        if anim.applied == Some(anim.kind) {
            continue;
        }
        let Ok((mut player, mut transitions)) = players.get_mut(anim.player_entity) else {
            // Instance was respawned — recover next frame.
            commands
                .entity(entity)
                .remove::<CrewAnimPlayback>()
                .insert(CrewSceneReady);
            continue;
        };
        let node = anim.node(anim.kind);
        let active = transitions.play(&mut player, node, CROSSFADE);
        if anim.kind.loops() {
            active.repeat();
        }
        anim.applied = Some(anim.kind);
    }
}
