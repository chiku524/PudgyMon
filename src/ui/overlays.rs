//! Fullscreen stage / results cards.

use bevy::prelude::*;

use crate::{
    flow::AppScreen,
    party::{PartyDirector, PartyPhase, PartySnapshot},
    season::SeasonLedger,
};

#[derive(Component)]
pub(super) struct PhaseOverlayRoot;

#[derive(Component)]
pub(super) struct PhaseOverlayTitle;

#[derive(Component)]
pub(super) struct PhaseOverlayBody;

pub fn spawn_phase_overlay(mut commands: Commands) {
    commands.spawn((
        PhaseOverlayRoot,
        Node {
            position_type: PositionType::Absolute,
            width: Val::Percent(100.0),
            height: Val::Percent(100.0),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            flex_direction: FlexDirection::Column,
            row_gap: Val::Px(12.0),
            ..Default::default()
        },
        BackgroundColor(Color::srgba(0.04, 0.03, 0.1, 0.82)),
        GlobalZIndex(400),
        Visibility::Hidden,
        children![
            (
                PhaseOverlayTitle,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(42.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(1.0, 0.82, 0.3)),
            ),
            (
                PhaseOverlayBody,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(18.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.9, 0.92, 0.98)),
            ),
        ],
    ));
}

pub fn update_phase_overlay(
    screen: Res<State<AppScreen>>,
    director: Res<PartyDirector>,
    season: Res<SeasonLedger>,
    snaps: Query<&PartySnapshot>,
    mut root: Query<&mut Visibility, With<PhaseOverlayRoot>>,
    mut title: Query<&mut Text, (With<PhaseOverlayTitle>, Without<PhaseOverlayBody>)>,
    mut body: Query<&mut Text, (With<PhaseOverlayBody>, Without<PhaseOverlayTitle>)>,
) {
    let Ok(mut visibility) = root.single_mut() else {
        return;
    };
    // Compare-before-write throughout: unconditional Visibility / Text writes
    // dirty the UI tree (and re-layout text) every frame.
    let set_visibility = |visibility: &mut Mut<Visibility>, want: Visibility| {
        if **visibility != want {
            **visibility = want;
        }
    };
    if *screen.get() != AppScreen::Playing {
        set_visibility(&mut visibility, Visibility::Hidden);
        return;
    }

    let snap = snaps.iter().next();
    let phase = snap.map(|s| s.phase).unwrap_or(director.phase);

    let content = match phase {
        PartyPhase::Results => Some((
            "PUDGYMON RESULTS".to_string(),
            format!(
                "Your party pts: {}\nSeason total: {}\nR rematch · Q Nest · M claim on Boing",
                director.match_points[0], season.points
            ),
        )),
        PartyPhase::Intermission => Some((
            "NEXT STAGE".to_string(),
            director.announcer.clone(),
        )),
        _ => None,
    };

    match content {
        Some((t, b)) => {
            set_visibility(&mut visibility, Visibility::Visible);
            if let Ok(mut text) = title.single_mut() {
                if text.0 != t {
                    **text = t;
                }
            }
            if let Ok(mut text) = body.single_mut() {
                if text.0 != b {
                    **text = b;
                }
            }
        }
        None => {
            set_visibility(&mut visibility, Visibility::Hidden);
        }
    }
}
