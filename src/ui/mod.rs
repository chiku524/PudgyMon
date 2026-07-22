mod auth;
mod overlays;
pub mod menu_options;

use bevy::prelude::*;

use crate::{
    boing::{BoingConfig, BoingStatus, ClaimVoucher},
    challenges::ChallengeBoard,
    cosmetics::EquippedCosmetic,
    flow::AppScreen,
    hub::HubPrompt,
    party::{PartyDirector, PartyPhase, PartySnapshot},
    player::LocalPlayer,
    season::SeasonLedger,
    session_flow::{NetworkBanner, Spectating},
};

pub struct UiPlugin;

impl Plugin for UiPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<menu_options::MenuPartyOptions>()
            .add_plugins(auth::AuthIntroPlugin)
            .add_systems(
                Startup,
                (spawn_hud_root, overlays::spawn_phase_overlay).chain(),
            )
            .add_systems(
                Update,
                (
                    update_hud.run_if(in_state(AppScreen::Playing)),
                    overlays::update_phase_overlay.run_if(in_state(AppScreen::Playing)),
                    set_hud_visible,
                ),
            );
    }
}

#[derive(Component)]
struct HudRoot;

#[derive(Component)]
struct HudMainText;

#[derive(Component)]
struct HudSubText;

#[derive(Component)]
struct HudHintText;

fn spawn_hud_root(mut commands: Commands) {
    commands.spawn((
        HudRoot,
        Node {
            width: Val::Percent(100.0),
            height: Val::Percent(100.0),
            flex_direction: FlexDirection::Column,
            padding: UiRect::all(Val::Px(18.0)),
            row_gap: Val::Px(8.0),
            ..Default::default()
        },
        Visibility::Hidden,
        children![
            (
                Text::new("PUDGYMON · THE NEST"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(1.0, 0.55, 0.35)),
            ),
            (
                HudMainText,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(24.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.95, 0.95, 0.9)),
            ),
            (
                HudSubText,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(15.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.7, 0.85, 0.95)),
            ),
            (
                HudHintText,
                Text::new(
                    "WASD · pads · E · Esc menu · C skin · M claim · Ctrl+O · Q Nest",
                ),
                TextFont {
                    font_size: FontSize::Px(12.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.55, 0.6, 0.7)),
                Node {
                    margin: UiRect::top(Val::Auto),
                    ..Default::default()
                },
            ),
        ],
    ));
}

fn set_hud_visible(
    screen: Res<State<AppScreen>>,
    mut roots: Query<&mut Visibility, With<HudRoot>>,
) {
    let Ok(mut vis) = roots.single_mut() else {
        return;
    };
    *vis = if *screen.get() == AppScreen::Playing {
        Visibility::Visible
    } else {
        Visibility::Hidden
    };
}

fn update_hud(
    director: Res<PartyDirector>,
    snaps: Query<&PartySnapshot>,
    season: Res<SeasonLedger>,
    challenges: Res<ChallengeBoard>,
    equipped: Res<EquippedCosmetic>,
    banner: Res<NetworkBanner>,
    hub_prompt: Res<HubPrompt>,
    boing: Res<BoingConfig>,
    status: Res<BoingStatus>,
    voucher: Res<ClaimVoucher>,
    spectating: Query<(), (With<LocalPlayer>, With<Spectating>)>,
    mut main: Query<&mut Text, (With<HudMainText>, Without<HudSubText>)>,
    mut sub: Query<&mut Text, (With<HudSubText>, Without<HudMainText>)>,
) {
    let snap = snaps.iter().next();
    let phase = snap.map(|s| s.phase).unwrap_or(director.phase);
    let timer = snap.map(|s| s.phase_timer).unwrap_or(director.phase_timer);
    let line = snap
        .map(|s| s.announcer.as_str())
        .unwrap_or(director.announcer.as_str());
    let pts = snap
        .map(|s| s.match_points[0])
        .unwrap_or(director.match_points[0]);

    let phase_label = match phase {
        PartyPhase::Hub => "THE NEST",
        PartyPhase::Race => "RACE",
        PartyPhase::Vibe => "VIBE COLLECT",
        PartyPhase::Shooter => "SHOOTER",
        PartyPhase::Intermission => "INTERMISSION",
        PartyPhase::Results => "RESULTS",
    };

    if let Ok(mut text) = main.single_mut() {
        let timer_bit = if phase == PartyPhase::Hub {
            String::new()
        } else if timer < 9000.0 {
            format!("  ·  {timer:.0}s")
        } else {
            String::new()
        };
        let spec = if !spectating.is_empty() {
            " · SPECTATING (Tab)"
        } else {
            ""
        };
        let prompt = if phase == PartyPhase::Hub && !hub_prompt.line.is_empty() {
            hub_prompt.line.as_str()
        } else {
            line
        };
        **text = format!("{phase_label}{timer_bit}{spec}\n{prompt}");
    }

    if let Ok(mut text) = sub.single_mut() {
        let wallet = boing
            .linked_account
            .as_ref()
            .map(|a| &a[..10.min(a.len())])
            .unwrap_or("unlinked");
        let rpc = if status.reachable {
            format!("Boing ok h={}", status.tip_height.unwrap_or(0))
        } else if status.last_error.is_empty() {
            "Boing offline".into()
        } else {
            "Boing err".into()
        };
        let banner_line = if banner.message.is_empty() {
            voucher.note.clone()
        } else {
            banner.message.clone()
        };
        **text = format!(
            "Party pts {pts} · Season {} · Skin {} · {rpc} · {wallet}\n{}\n{banner_line}",
            season.points,
            equipped.id,
            challenges.summary_line()
        );
    }
}
