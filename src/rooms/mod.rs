pub mod layout;

use bevy::prelude::*;

use crate::{
    player::Leaseholder,
    scoring::{PlayerScoreId, ScoringService, ScoreAction},
    tournament::types::{RoomId, RoomProgress, SlotId, SlotSize},
};

pub use layout::{sync_room_layout, ActiveRoomLayout, RoomLayoutPiece};

#[derive(Resource, Debug, Clone, Default)]
pub struct RoomRuntime {
    pub active: Option<RoomId>,
    pub progress: RoomProgress,
    pub slot_progress: std::collections::HashMap<SlotId, u32>,
    pub meltdown_rate: f32,
    pub sort_target: u8,
    bot_entropy: u32,
}

impl RoomRuntime {
    pub fn begin(&mut self, room: RoomId, alive_slots: usize, slot_size: SlotSize) {
        self.active = Some(room);
        self.slot_progress.clear();
        let per_slot = scaled_target(room, slot_size);
        for i in 0..alive_slots {
            self.slot_progress.insert(SlotId(i as u32), 0);
        }
        self.progress = RoomProgress {
            cleared: false,
            objective_count: 0,
            objective_target: per_slot.saturating_mul(alive_slots as u32),
            meltdown_meter: 0.0,
        };
        self.meltdown_rate = if room == RoomId::ShuttleMeltdown {
            2.0
        } else {
            0.0
        };
        self.sort_target = 0;
        self.bot_entropy = 1;
    }

    pub fn progress_percent(&self) -> u8 {
        if self.progress.objective_target == 0 {
            return 0;
        }
        ((self.progress.objective_count as f32 / self.progress.objective_target as f32) * 100.0)
            .min(100.0) as u8
    }

    pub fn tick_bot_slot(&mut self, scoring: &mut ScoringService, slot: &SlotId, dt: f32) {
        if self.progress.cleared {
            return;
        }
        self.bot_entropy = self.bot_entropy.wrapping_add(1);
        let chance = dt * 0.35;
        if pseudo_rand(self.bot_entropy) < chance {
            self.advance_slot(scoring, slot, true);
        }
    }

    pub fn sort_target_label(&self) -> &'static str {
        match self.sort_target {
            0 => "Hot Dogs",
            1 => "Toasters",
            2 => "Premium Air",
            _ => "Write-Ups",
        }
    }

    pub fn meltdown_percent(&self) -> u8 {
        self.progress.meltdown_meter.min(100.0) as u8
    }

    pub fn player_action(
        &mut self,
        scoring: &mut ScoringService,
        player: PlayerScoreId,
        slot: &SlotId,
        action: ScoreAction,
    ) {
        scoring.record(player, action);
        if action.objective_delta() > 0.0 {
            let entry = self.slot_progress.entry(slot.clone()).or_insert(0);
            *entry += 1;
            self.progress.objective_count += 1;
            if self.meltdown_rate > 0.0 {
                self.progress.meltdown_meter =
                    (self.progress.meltdown_meter + self.meltdown_rate).min(100.0);
            }
            if self.progress.objective_count >= self.progress.objective_target {
                self.progress.cleared = true;
                scoring.record(player, ScoreAction::RoomClearBonus);
            }
        }
    }

    fn advance_slot(&mut self, scoring: &mut ScoringService, slot: &SlotId, positive: bool) {
        let room = self.active.unwrap_or(RoomId::HrOrientation);
        let entry = self.slot_progress.entry(slot.clone()).or_insert(0);
        let player = PlayerScoreId(slot.0 * 10);

        if positive {
            *entry += 1;
            self.progress.objective_count += 1;
            let action = match room {
                RoomId::HrOrientation => ScoreAction::CorrectSort,
                RoomId::CargoGantry => ScoreAction::CrateDelivered,
                RoomId::BreakerPanic => ScoreAction::BreakerCorrect,
                RoomId::ShuttleMeltdown => ScoreAction::CoolantValve,
            };
            scoring.record(player, action);
        } else {
            scoring.record(player, ScoreAction::IncorrectSort);
        }

        if self.meltdown_rate > 0.0 {
            self.progress.meltdown_meter =
                (self.progress.meltdown_meter + self.meltdown_rate).min(100.0);
        }

        if self.progress.objective_count >= self.progress.objective_target {
            self.progress.cleared = true;
            scoring.record(player, ScoreAction::RoomClearBonus);
        }
    }

    pub fn finish(
        &mut self,
        slot_size: SlotSize,
    ) -> std::collections::HashMap<SlotId, (bool, f32)> {
        let room = self.active.unwrap_or(RoomId::HrOrientation);
        let target = scaled_target(room, slot_size);
        let mut out = std::collections::HashMap::new();
        for (slot, count) in &self.slot_progress {
            let cleared = *count >= target;
            let time = if cleared {
                30.0
            } else {
                999.0
            };
            out.insert(slot.clone(), (cleared, time));
        }
        self.active = None;
        out
    }
}

fn scaled_target(room: RoomId, slot_size: SlotSize) -> u32 {
    let base = match room {
        RoomId::HrOrientation => 6,
        RoomId::CargoGantry => 4,
        RoomId::BreakerPanic => 4,
        RoomId::ShuttleMeltdown => 6,
    };
    base * slot_size.player_count() as u32
}

fn pseudo_rand(seed: u32) -> f32 {
    let x = seed.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
    (x % 10_000) as f32 / 10_000.0
}

pub struct RoomsPlugin;

impl Plugin for RoomsPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<RoomRuntime>()
            .init_resource::<ActiveRoomLayout>()
            .add_systems(Update, sync_room_layout);
    }
}

/// Phase 2 — rotate leaseholder at room start for team brackets.
pub fn assign_leaseholder(
    mut director: ResMut<crate::tournament::TournamentDirector>,
    mut commands: Commands,
    players: Query<(Entity, &crate::player::NetworkPlayer)>,
) {
    if director.slot_size() == SlotSize::Solo {
        return;
    }
    let alive: Vec<_> = director.slots.iter().filter(|s| s.alive).collect();
    if alive.is_empty() {
        return;
    }
    let rotate = director.room_index as usize % alive.len();
    for (idx, slot) in director.slots.iter_mut().enumerate() {
        slot.leaseholder = idx == rotate && slot.alive;
    }
    for (entity, net) in &players {
        if director
            .slots
            .iter()
            .any(|s| s.id.0 == net.slot && s.leaseholder)
        {
            commands.entity(entity).insert(Leaseholder);
        } else {
            commands.entity(entity).remove::<Leaseholder>();
        }
    }
}
