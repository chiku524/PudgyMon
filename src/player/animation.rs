//! Shared Pudgy clip playback — idle / walk / run + bindable emote wheel.

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

/// Performance clips that can be bound to wheel slots 1–5 (not locomotion / idle / jump).
pub const EMOTE_LIBRARY: &[(&str, &str, f32, bool)] = &[
    // clip name, UI label, lock seconds, loops
    ("emote_scared", "Scared", 1.4, false),
    ("emote_wave", "Wave", 1.3, false),
    ("emote_dance", "Dance", 0.0, true),
    ("emote_cheer", "Cheer", 1.5, false),
];

pub const EMOTE_SLOT_COUNT: usize = 5;
/// Walk/run → idle blend. Long enough to hide pose pops; short enough that feet don't keep striding.
const IDLE_CROSSFADE: Duration = Duration::from_millis(520);
const CROSSFADE: Duration = Duration::from_millis(180);
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
    /// Bound wheel slot index (0–4). Only valid when that slot has a binding.
    Emote(u8),
}

#[derive(Debug, Clone)]
pub struct CrewEmoteDef {
    pub node: AnimationNodeIndex,
    pub label: String,
    pub clip_name: String,
    pub lock_secs: f32,
    pub loops: bool,
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
    /// All performance clips present on this crew GLB (for binding UI / playback).
    pub library: Vec<CrewEmoteDef>,
    pub lock_until: f32,
    pub player_entity: Entity,
    /// Elapsed time when the avatar last became still (unused settle; kept for debug).
    pub still_since: Option<f32>,
}

impl CrewAnimPlayback {
    fn node(&self, kind: CrewAnimKind, bindings: &crate::settings::EmoteBindings) -> AnimationNodeIndex {
        match kind {
            CrewAnimKind::Idle => self.idle,
            CrewAnimKind::Walk => self.walk,
            CrewAnimKind::Run => self.run,
            CrewAnimKind::Jump => self.jump,
            CrewAnimKind::Emote(i) => self
                .resolve_bound(i, bindings)
                .map(|e| e.node)
                .unwrap_or(self.idle),
        }
    }

    fn loops(&self, kind: CrewAnimKind, bindings: &crate::settings::EmoteBindings) -> bool {
        match kind {
            CrewAnimKind::Idle | CrewAnimKind::Walk | CrewAnimKind::Run => true,
            CrewAnimKind::Jump => false,
            CrewAnimKind::Emote(i) => self
                .resolve_bound(i, bindings)
                .map(|e| e.loops)
                .unwrap_or(false),
        }
    }

    pub fn resolve_bound<'a>(
        &'a self,
        slot: u8,
        bindings: &'a crate::settings::EmoteBindings,
    ) -> Option<&'a CrewEmoteDef> {
        let clip = bindings.slots.get(slot as usize)?.as_ref()?;
        self.library.iter().find(|e| e.clip_name == *clip)
    }

    pub fn trigger_bound_emote(
        &mut self,
        slot: u8,
        now: f32,
        bindings: &crate::settings::EmoteBindings,
    ) -> bool {
        let Some(emote) = self.resolve_bound(slot, bindings) else {
            return false;
        };
        let loops = emote.loops;
        let lock = emote.lock_secs;
        self.kind = CrewAnimKind::Emote(slot);
        self.lock_until = if loops { f32::MAX } else { now + lock };
        self.applied = None;
        self.still_since = None;
        true
    }

    pub fn trigger_jump_anim(&mut self, now: f32) {
        self.kind = CrewAnimKind::Jump;
        // Longer hang so the clip covers exaggerated hops.
        self.lock_until = now + 0.85;
        self.applied = None;
        self.still_since = None;
    }
}

#[derive(Component, Debug, Clone, Copy)]
pub struct PlayerMotion {
    pub speed: f32,
    pub sprint: bool,
    pub vertical_velocity: f32,
    pub grounded: bool,
    /// Air jumps remaining after leaving the ground (double-jump).
    pub air_jumps_left: u8,
}

impl Default for PlayerMotion {
    fn default() -> Self {
        Self {
            speed: 0.0,
            sprint: false,
            vertical_velocity: 0.0,
            grounded: true,
            air_jumps_left: crate::core::PLAYER_MAX_AIR_JUMPS,
        }
    }
}

/// Queued from the Nest Animations menu (plays bound wheel slot on local crew).
#[derive(Message, Debug, Clone, Copy)]
pub struct PlayCrewEmote(pub u8);

#[derive(Component)]
struct CrewSceneReady;

pub struct CrewAnimationPlugin;

impl Plugin for CrewAnimationPlugin {
    fn build(&self, app: &mut App) {
        app.add_message::<PlayCrewEmote>().add_systems(
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
    commands
        .entity(ready.entity)
        .remove::<CrewAnimPlayback>()
        .insert(CrewSceneReady);
}

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

        let mut clip_handles = vec![idle.clone(), walk, run, jump];
        let mut library_meta: Vec<(String, String, f32, bool)> = Vec::new();
        for &(clip_name, label, lock_secs, loops) in EMOTE_LIBRARY {
            if let Some(handle) = gltf.named_animations.get(clip_name).cloned() {
                clip_handles.push(handle);
                library_meta.push((
                    clip_name.to_string(),
                    label.to_string(),
                    lock_secs,
                    loops,
                ));
            }
        }

        let (graph, nodes) = AnimationGraph::from_clips(clip_handles);
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

        let mut library = Vec::new();
        for (i, (clip_name, label, lock_secs, loops)) in library_meta.into_iter().enumerate() {
            library.push(CrewEmoteDef {
                node: nodes[4 + i],
                label,
                clip_name,
                lock_secs,
                loops,
            });
        }

        info!(
            "crew animation ready for `{}` (player={player_entity:?}, library={:?})",
            setup.model_id,
            library.iter().map(|e| e.clip_name.as_str()).collect::<Vec<_>>()
        );

        commands.entity(entity).insert(CrewAnimPlayback {
            kind: CrewAnimKind::Idle,
            applied: Some(CrewAnimKind::Idle),
            graph: graph_handle,
            idle: nodes[0],
            walk: nodes[1],
            run: nodes[2],
            jump: nodes[3],
            library,
            lock_until: 0.0,
            player_entity,
            still_since: Some(0.0),
        });
        commands.entity(entity).remove::<CrewSceneReady>();
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
    bindings: Res<crate::settings::EmoteBindings>,
    mut emote_events: MessageReader<PlayCrewEmote>,
    players: Query<(&PlayerMotion, &Children, Option<&crate::player::LocalPlayer>)>,
    visual_roots: Query<(), With<PlayerVisualRoot>>,
    mut visuals: Query<&mut CrewAnimPlayback>,
) {
    let paused = pause.map(|p| p.paused).unwrap_or(false);
    let now = time.elapsed_secs();
    let menu_emotes: Vec<u8> = emote_events.read().map(|e| e.0).collect();

    for (motion, children, local) in &players {
        let Some(visual) = children.iter().find(|c| visual_roots.contains(*c)) else {
            continue;
        };
        let Ok(mut anim) = visuals.get_mut(visual) else {
            continue;
        };

        if local.is_some() {
            for slot in &menu_emotes {
                let _ = anim.trigger_bound_emote(*slot, now, &bindings);
            }
        }

        let moving = motion.speed > WALK_SPEED_EPS;
        let airborne = !motion.grounded;
        let locked = now < anim.lock_until;

        if local.is_some() && !paused {
            let digit_slot = [
                (KeyCode::Digit1, 0u8),
                (KeyCode::Digit2, 1),
                (KeyCode::Digit3, 2),
                (KeyCode::Digit4, 3),
                (KeyCode::Digit5, 4),
                (KeyCode::Numpad1, 0),
                (KeyCode::Numpad2, 1),
                (KeyCode::Numpad3, 2),
                (KeyCode::Numpad4, 3),
                (KeyCode::Numpad5, 4),
            ]
            .into_iter()
            .find_map(|(key, slot)| keyboard.just_pressed(key).then_some(slot));
            if let Some(slot) = digit_slot {
                if anim.trigger_bound_emote(slot, now, &bindings) {
                    continue;
                }
            }
        }

        // Jump anim follows physics jump (rising).
        if airborne && motion.vertical_velocity > 0.5 {
            if anim.kind != CrewAnimKind::Jump {
                anim.trigger_jump_anim(now);
            }
        }

        if locked {
            match anim.kind {
                CrewAnimKind::Jump => continue,
                CrewAnimKind::Emote(i) => {
                    let loops = anim
                        .resolve_bound(i, &bindings)
                        .map(|e| e.loops)
                        .unwrap_or(false);
                    if loops {
                        if moving || airborne {
                            anim.lock_until = 0.0;
                        } else {
                            continue;
                        }
                    } else {
                        continue;
                    }
                }
                _ => {}
            }
        }

        if moving || airborne {
            anim.still_since = None;
            let desired = if airborne {
                if motion.vertical_velocity > 0.15 {
                    CrewAnimKind::Jump
                } else if motion.speed > WALK_SPEED_EPS {
                    if motion.sprint {
                        CrewAnimKind::Run
                    } else {
                        CrewAnimKind::Walk
                    }
                } else {
                    // Falling while mostly still — keep jump until land.
                    CrewAnimKind::Jump
                }
            } else if motion.sprint {
                CrewAnimKind::Run
            } else {
                CrewAnimKind::Walk
            };
            if anim.kind != desired {
                anim.kind = desired;
                anim.applied = None;
            }
            continue;
        }

        // Keys released — stop locomotion immediately and ease into idle.
        anim.still_since = None;
        if anim.kind != CrewAnimKind::Idle {
            anim.kind = CrewAnimKind::Idle;
            anim.applied = None;
        }
    }
}

fn apply_crew_anim_kind(
    mut commands: Commands,
    bindings: Res<crate::settings::EmoteBindings>,
    mut visuals: Query<(Entity, &mut CrewAnimPlayback)>,
    mut players: Query<(&mut AnimationPlayer, &mut AnimationTransitions)>,
) {
    for (entity, mut anim) in &mut visuals {
        if anim.applied == Some(anim.kind) {
            continue;
        }
        let Ok((mut player, mut transitions)) = players.get_mut(anim.player_entity) else {
            commands
                .entity(entity)
                .remove::<CrewAnimPlayback>()
                .insert(CrewSceneReady);
            continue;
        };

        let to_idle = anim.kind == CrewAnimKind::Idle;
        if to_idle {
            // Ease locomotion down instead of a hard freeze (hard 0-speed snaps look "clicky").
            for (_, playing) in player.playing_animations_mut() {
                playing.set_speed(0.2);
            }
        } else {
            for (_, playing) in player.playing_animations_mut() {
                playing.set_speed(1.0);
            }
        }

        let fade = if to_idle { IDLE_CROSSFADE } else { CROSSFADE };
        let node = anim.node(anim.kind, &bindings);
        let active = transitions.play(&mut player, node, fade);
        active.set_speed(1.0);
        if anim.loops(anim.kind, &bindings) {
            active.repeat();
        }
        anim.applied = Some(anim.kind);
    }
}
