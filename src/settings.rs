//! Game settings + Esc Nest menu (pause overlay).

use std::fs;
use std::path::PathBuf;

use bevy::prelude::*;
use bevy::window::{CursorGrabMode, CursorOptions, PrimaryWindow, WindowMode};
use bevy_replicon::prelude::*;
use serde::{Deserialize, Serialize};

use crate::{
    account::PlayerAccount,
    boing::{self, BoingConfig, BoingStatus, ClaimVoucher},
    brand::APP_DATA_DIR,
    challenges::ChallengeBoard,
    cosmetics::{CosmeticsCatalog, EquippedCosmetic},
    data::{CharacterRoster, PlayerDefaults},
    flow::AppScreen,
    hub::EditorMode,
    player::{PlayerName, PlayerVisualSpec, SelectCharacterRequest, ThirdPersonCamera},
    season::SeasonLedger,
    session_flow::{LeaveToNestRequest, NetworkBanner},
};

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct GameSettings {
    pub mouse_sensitivity: f32,
    pub master_volume: f32,
    pub fullscreen: bool,
}

impl Default for GameSettings {
    fn default() -> Self {
        Self {
            mouse_sensitivity: crate::core::MOUSE_SENSITIVITY,
            master_volume: 1.0,
            fullscreen: true,
        }
    }
}

impl GameSettings {
    fn path() -> PathBuf {
        if let Ok(base) = std::env::var("LOCALAPPDATA") {
            PathBuf::from(base).join(APP_DATA_DIR).join("settings.json")
        } else {
            PathBuf::from("settings.json")
        }
    }

    pub fn load() -> Self {
        let Ok(raw) = fs::read_to_string(Self::path()) else {
            return Self::default();
        };
        serde_json::from_str(&raw).unwrap_or_default()
    }

    pub fn save(&self) {
        let path = Self::path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(json) = serde_json::to_string_pretty(self) {
            let _ = fs::write(path, json);
        }
    }
}

#[derive(Resource, Debug, Default)]
pub struct PauseState {
    pub paused: bool,
}

#[derive(Resource, Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum MenuPage {
    #[default]
    Settings,
    Profile,
    Account,
    Characters,
    Inventory,
    Wallet,
    Market,
    Challenges,
    Controls,
    ConfirmQuit,
}

#[derive(Component)]
struct PauseRoot;

#[derive(Component)]
struct MenuPageRoot(MenuPage);

#[derive(Component)]
struct MenuNavButton(MenuAction);

/// Top-bar tab; `page` marks which content page this tab highlights when active.
#[derive(Component, Clone, Copy)]
struct TopNavTab {
    action: MenuAction,
    page: Option<MenuPage>,
}

#[derive(Component)]
struct SettingsActionButton(SettingsAction);

#[derive(Component)]
struct MarketEquipButton {
    id: String,
}

#[derive(Component)]
struct CharacterSelectButton {
    id: String,
}

#[derive(Component)]
struct CharacterRowLabel {
    id: String,
}

#[derive(Component)]
struct MarketBoingButton(BoingAction);

#[derive(Component, Clone, Copy, PartialEq, Eq)]
enum MenuBodyText {
    Settings,
    Profile,
    Account,
    Characters,
    Inventory,
    Wallet,
    Challenges,
    MarketStatus,
}

#[derive(Component)]
struct MarketRowLabel {
    id: String,
}

#[derive(Clone, Copy, Debug)]
enum MenuAction {
    Resume,
    Open(MenuPage),
    ReturnToNest,
    ConfirmQuitYes,
}

#[derive(Clone, Copy, Debug)]
enum SettingsAction {
    VolumeDown,
    VolumeUp,
    SensDown,
    SensUp,
    ToggleFullscreen,
}

#[derive(Clone, Copy, Debug)]
enum BoingAction {
    LinkWallet,
    ClaimVoucher,
    OpenCompanion,
}

#[derive(Clone, Copy, Debug)]
enum AccountAction {
    OpenWebsite,
    LinkPendingToken,
    RefreshProfile,
    SignOut,
    ModeSignIn,
    ModeRegister,
    SubmitAuth,
}

#[derive(Component)]
struct AccountActionButton(AccountAction);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
enum NestAuthMode {
    #[default]
    SignIn,
    Register,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
enum NestAuthField {
    #[default]
    Email,
    Password,
    DisplayName,
}

#[derive(Resource, Debug, Default)]
struct NestAuthForm {
    mode: NestAuthMode,
    focus: NestAuthField,
    email: String,
    password: String,
    display_name: String,
    busy: bool,
}

impl NestAuthForm {
    fn focused_mut(&mut self) -> &mut String {
        match self.focus {
            NestAuthField::Email => &mut self.email,
            NestAuthField::Password => &mut self.password,
            NestAuthField::DisplayName => &mut self.display_name,
        }
    }

    fn cycle_focus(&mut self) {
        self.focus = match self.mode {
            NestAuthMode::SignIn => match self.focus {
                NestAuthField::Email => NestAuthField::Password,
                _ => NestAuthField::Email,
            },
            NestAuthMode::Register => match self.focus {
                NestAuthField::DisplayName => NestAuthField::Email,
                NestAuthField::Email => NestAuthField::Password,
                NestAuthField::Password => NestAuthField::DisplayName,
            },
        };
    }

    fn set_mode(&mut self, mode: NestAuthMode) {
        self.mode = mode;
        self.focus = match mode {
            NestAuthMode::SignIn => NestAuthField::Email,
            NestAuthMode::Register => NestAuthField::DisplayName,
        };
    }
}

#[derive(Component)]
struct MarketBuyButton {
    id: String,
}

const BTN_BG: Color = Color::srgb(0.16, 0.30, 0.26);
const BTN_HOVER: Color = Color::srgb(0.22, 0.40, 0.34);
const BTN_PRESS: Color = Color::srgb(0.12, 0.24, 0.20);
const ACCENT: Color = Color::srgb(1.0, 0.55, 0.35);
const TEAL: Color = Color::srgb(0.35, 0.85, 0.72);
const MUTED: Color = Color::srgb(0.72, 0.82, 0.78);
const DANGER: Color = Color::srgb(0.85, 0.35, 0.32);

pub struct SettingsPlugin;

impl Plugin for SettingsPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(GameSettings::load())
            .init_resource::<PauseState>()
            .init_resource::<MenuPage>()
            .init_resource::<NestAuthForm>()
            .add_systems(Startup, (apply_fullscreen_on_boot, spawn_nest_menu).chain())
            .add_systems(
                Update,
                (
                    toggle_pause.run_if(in_state(AppScreen::Playing)),
                    sync_pause_cursor.run_if(in_state(AppScreen::Playing)),
                    update_pause_visibility,
                    sync_menu_page_visibility,
                    sync_top_nav_highlight,
                    menu_button_hover,
                    handle_menu_nav,
                    handle_settings_buttons,
                    handle_market_equip,
                    handle_character_select,
                    handle_market_buy,
                    handle_market_boing,
                    handle_account_buttons,
                    handle_nest_auth_typing,
                    sync_player_name_from_account,
                    refresh_menu_labels.run_if(in_state(AppScreen::Playing)),
                    apply_settings_hotkeys,
                    persist_settings,
                ),
            );
    }
}

fn apply_fullscreen_on_boot(
    settings: Res<GameSettings>,
    mut windows: Query<&mut Window, With<PrimaryWindow>>,
) {
    let Ok(mut window) = windows.single_mut() else {
        return;
    };
    // Always strip OS chrome (no title bar / min / max / close).
    window.decorations = false;
    window.resizable = false;
    window.enabled_buttons = bevy::window::EnabledButtons {
        minimize: false,
        maximize: false,
        close: false,
    };
    window.mode = if settings.fullscreen {
        WindowMode::BorderlessFullscreen(MonitorSelection::Current)
    } else {
        WindowMode::Windowed
    };
}

fn persist_settings(settings: Res<GameSettings>) {
    if settings.is_changed() {
        settings.save();
    }
}

fn spawn_nest_menu(mut commands: Commands, catalog: Res<CosmeticsCatalog>, roster: Res<CharacterRoster>) {
    commands
        .spawn((
            PauseRoot,
            Node {
                position_type: PositionType::Absolute,
                width: Val::Percent(100.0),
                height: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                justify_content: JustifyContent::FlexStart,
                align_items: AlignItems::Stretch,
                padding: UiRect::axes(Val::Px(20.0), Val::Px(18.0)),
                row_gap: Val::Px(16.0),
                overflow: Overflow::scroll_y(),
                ..Default::default()
            },
            BackgroundColor(Color::srgba(0.03, 0.07, 0.06, 0.96)),
            GlobalZIndex(600),
            Visibility::Hidden,
        ))
        .with_children(|panel| {
            panel.spawn((
                Node {
                    width: Val::Percent(100.0),
                    flex_direction: FlexDirection::Row,
                    justify_content: JustifyContent::SpaceBetween,
                    align_items: AlignItems::Center,
                    ..Default::default()
                },
                children![
                    (
                        Text::new("NEST MENU"),
                        TextFont {
                            font_size: FontSize::Px(28.0),
                            ..Default::default()
                        },
                        TextColor(ACCENT),
                    ),
                    (
                        Text::new("Esc closes · Quit exits"),
                        TextFont {
                            font_size: FontSize::Px(13.0),
                            ..Default::default()
                        },
                        TextColor(MUTED),
                    ),
                ],
            ));

            spawn_top_nav(panel);

            // Content pages — Settings is the default first tab.
            spawn_page_settings(panel);
            spawn_page_profile(panel);
            spawn_page_account(panel);
            spawn_page_characters(panel, &roster);
            spawn_page_inventory(panel, &catalog);
            spawn_page_wallet(panel);
            spawn_page_market(panel, &catalog);
            spawn_page_challenges(panel);
            spawn_page_controls(panel);
            spawn_page_confirm_quit(panel);
        });
}

fn spawn_top_nav(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Row,
                flex_wrap: FlexWrap::Wrap,
                column_gap: Val::Px(8.0),
                row_gap: Val::Px(8.0),
                align_items: AlignItems::Stretch,
                padding: UiRect::all(Val::Px(10.0)),
                border_radius: BorderRadius::all(Val::Px(14.0)),
                border: UiRect::all(Val::Px(1.0)),
                ..Default::default()
            },
            BackgroundColor(Color::srgba(0.06, 0.12, 0.11, 0.95)),
            BorderColor::all(Color::srgba(1.0, 0.55, 0.35, 0.28)),
        ))
        .with_children(|bar| {
            // First nav item = Settings (default open page).
            top_nav_btn(bar, "⚙", "Settings", MenuAction::Open(MenuPage::Settings), Some(MenuPage::Settings), false);
            top_nav_btn(bar, "◆", "Profile", MenuAction::Open(MenuPage::Profile), Some(MenuPage::Profile), false);
            top_nav_btn(bar, "☺", "Characters", MenuAction::Open(MenuPage::Characters), Some(MenuPage::Characters), false);
            top_nav_btn(bar, "@", "Account", MenuAction::Open(MenuPage::Account), Some(MenuPage::Account), false);
            top_nav_btn(bar, "▣", "Inventory", MenuAction::Open(MenuPage::Inventory), Some(MenuPage::Inventory), false);
            top_nav_btn(bar, "¤", "Wallet", MenuAction::Open(MenuPage::Wallet), Some(MenuPage::Wallet), false);
            top_nav_btn(bar, "✦", "Market", MenuAction::Open(MenuPage::Market), Some(MenuPage::Market), false);
            top_nav_btn(bar, "★", "Challenges", MenuAction::Open(MenuPage::Challenges), Some(MenuPage::Challenges), false);
            top_nav_btn(bar, "⌨", "Controls", MenuAction::Open(MenuPage::Controls), Some(MenuPage::Controls), false);
            top_nav_btn(bar, "⌂", "Nest", MenuAction::ReturnToNest, None, false);
            top_nav_btn(bar, "▶", "Resume", MenuAction::Resume, None, false);
            top_nav_btn(bar, "✕", "Quit", MenuAction::Open(MenuPage::ConfirmQuit), Some(MenuPage::ConfirmQuit), true);
        });
}

fn top_nav_btn(
    parent: &mut ChildSpawnerCommands,
    symbol: &str,
    label: &str,
    action: MenuAction,
    page: Option<MenuPage>,
    danger: bool,
) {
    let bg = if danger { DANGER } else { BTN_BG };
    parent
        .spawn((
            Button,
            MenuNavButton(action),
            TopNavTab { action, page },
            Node {
                width: Val::Px(88.0),
                min_height: Val::Px(72.0),
                padding: UiRect::axes(Val::Px(8.0), Val::Px(10.0)),
                flex_direction: FlexDirection::Column,
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                row_gap: Val::Px(4.0),
                border_radius: BorderRadius::all(Val::Px(12.0)),
                border: UiRect::all(Val::Px(2.0)),
                ..Default::default()
            },
            BackgroundColor(bg),
            BorderColor::all(Color::NONE),
        ))
        .with_children(|b| {
            // Icon plate (colored glyph block — works without image assets).
            b.spawn((
                Node {
                    width: Val::Px(36.0),
                    height: Val::Px(36.0),
                    justify_content: JustifyContent::Center,
                    align_items: AlignItems::Center,
                    border_radius: BorderRadius::all(Val::Px(10.0)),
                    ..Default::default()
                },
                BackgroundColor(if danger {
                    Color::srgba(0.95, 0.35, 0.3, 0.35)
                } else {
                    Color::srgba(0.35, 0.85, 0.72, 0.22)
                }),
                children![(
                    Text::new(symbol.to_string()),
                    TextFont {
                        font_size: FontSize::Px(20.0),
                        ..Default::default()
                    },
                    TextColor(if danger {
                        Color::srgb(1.0, 0.85, 0.82)
                    } else {
                        TEAL
                    }),
                )],
            ));
            b.spawn((
                Text::new(label.to_string()),
                TextFont {
                    font_size: FontSize::Px(12.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.96, 0.95, 0.9)),
            ));
        });
}

fn spawn_page_confirm_quit(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::ConfirmQuit),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Quit Game?"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                Text::new("Close PudgyMon and leave The Nest."),
                TextFont {
                    font_size: FontSize::Px(14.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            menu_btn(page, "Yes, quit", MenuAction::ConfirmQuitYes, true);
            menu_btn(page, "Cancel", MenuAction::Open(MenuPage::Settings), false);
        });
}

fn spawn_page_settings(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Settings),
            Node {
                width: Val::Percent(100.0),
                max_width: Val::Px(720.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Visible,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Settings"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Settings,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(14.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            settings_btn(page, "Volume −", SettingsAction::VolumeDown);
            settings_btn(page, "Volume +", SettingsAction::VolumeUp);
            settings_btn(page, "Sensitivity −", SettingsAction::SensDown);
            settings_btn(page, "Sensitivity +", SettingsAction::SensUp);
            settings_btn(page, "Toggle Fullscreen", SettingsAction::ToggleFullscreen);
        });
}

fn spawn_page_profile(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Profile),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Profile"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Profile,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(14.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
        });
}

fn spawn_page_account(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Account),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Account"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Account,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(13.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            account_btn(page, "Open website", AccountAction::OpenWebsite);
            account_btn(page, "Link pending token", AccountAction::LinkPendingToken);
            account_btn(page, "Refresh profile", AccountAction::RefreshProfile);
            account_btn(page, "Sign In mode", AccountAction::ModeSignIn);
            account_btn(page, "Register mode", AccountAction::ModeRegister);
            account_btn(page, "Submit email/password", AccountAction::SubmitAuth);
            account_btn(page, "Sign out", AccountAction::SignOut);
        });
}

fn spawn_page_characters(parent: &mut ChildSpawnerCommands, roster: &CharacterRoster) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Characters),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Characters"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Characters,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(13.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            for entry in roster.available() {
                let id = entry.id.clone();
                let label = format!("{}\n{}", entry.label, entry.blurb);
                page.spawn((
                    Node {
                        width: Val::Percent(100.0),
                        flex_direction: FlexDirection::Row,
                        column_gap: Val::Px(8.0),
                        align_items: AlignItems::Center,
                        justify_content: JustifyContent::SpaceBetween,
                        padding: UiRect::axes(Val::Px(4.0), Val::Px(6.0)),
                        ..Default::default()
                    },
                    children![
                        (
                            CharacterRowLabel { id: id.clone() },
                            Text::new(label),
                            TextFont {
                                font_size: FontSize::Px(13.0),
                                ..Default::default()
                            },
                            TextColor(MUTED),
                            Node {
                                flex_grow: 1.0,
                                ..Default::default()
                            },
                        ),
                        (
                            Button,
                            CharacterSelectButton { id },
                            Node {
                                padding: UiRect::axes(Val::Px(12.0), Val::Px(8.0)),
                                justify_content: JustifyContent::Center,
                                border_radius: BorderRadius::all(Val::Px(8.0)),
                                ..Default::default()
                            },
                            BackgroundColor(BTN_BG),
                            children![(
                                Text::new("Use"),
                                TextFont {
                                    font_size: FontSize::Px(13.0),
                                    ..Default::default()
                                },
                                TextColor(Color::srgb(0.95, 0.95, 0.9)),
                            )],
                        ),
                    ],
                ));
            }
        });
}

fn spawn_page_inventory(parent: &mut ChildSpawnerCommands, catalog: &CosmeticsCatalog) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Inventory),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Inventory"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Inventory,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(13.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            for item in &catalog.items {
                let id = item.id.clone();
                page.spawn((
                    Node {
                        width: Val::Percent(100.0),
                        flex_direction: FlexDirection::Row,
                        column_gap: Val::Px(8.0),
                        align_items: AlignItems::Center,
                        justify_content: JustifyContent::SpaceBetween,
                        ..Default::default()
                    },
                    children![
                        (
                            MarketRowLabel { id: id.clone() },
                            Text::new(item.label.clone()),
                            TextFont {
                                font_size: FontSize::Px(13.0),
                                ..Default::default()
                            },
                            TextColor(MUTED),
                            Node {
                                flex_grow: 1.0,
                                ..Default::default()
                            },
                        ),
                        (
                            Button,
                            MarketEquipButton { id },
                            Node {
                                padding: UiRect::axes(Val::Px(12.0), Val::Px(6.0)),
                                justify_content: JustifyContent::Center,
                                border_radius: BorderRadius::all(Val::Px(8.0)),
                                ..Default::default()
                            },
                            BackgroundColor(BTN_BG),
                            children![(
                                Text::new("Equip"),
                                TextFont {
                                    font_size: FontSize::Px(13.0),
                                    ..Default::default()
                                },
                                TextColor(Color::srgb(0.95, 0.95, 0.9)),
                            )],
                        ),
                    ],
                ));
            }
        });
}

fn spawn_page_wallet(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Wallet),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Wallet"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Wallet,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(13.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            boing_btn(page, "Prepare claim voucher", BoingAction::ClaimVoucher);
            boing_btn(page, "Open Claim Desk (Express)", BoingAction::OpenCompanion);
            boing_btn(
                page,
                "Advanced: link BOING_ACCOUNT",
                BoingAction::LinkWallet,
            );
        });
}

fn spawn_page_market(parent: &mut ChildSpawnerCommands, catalog: &CosmeticsCatalog) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Market),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Nest Market"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::MarketStatus,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(13.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
            for item in &catalog.items {
                let id = item.id.clone();
                let label = format!("{} · {} pts", item.label, item.cost_points);
                page.spawn((
                    Node {
                        width: Val::Percent(100.0),
                        flex_direction: FlexDirection::Row,
                        column_gap: Val::Px(6.0),
                        align_items: AlignItems::Center,
                        justify_content: JustifyContent::SpaceBetween,
                        ..Default::default()
                    },
                    children![
                        (
                            MarketRowLabel { id: id.clone() },
                            Text::new(label),
                            TextFont {
                                font_size: FontSize::Px(13.0),
                                ..Default::default()
                            },
                            TextColor(MUTED),
                            Node {
                                flex_grow: 1.0,
                                ..Default::default()
                            },
                        ),
                        (
                            Button,
                            MarketBuyButton { id: id.clone() },
                            Node {
                                padding: UiRect::axes(Val::Px(10.0), Val::Px(6.0)),
                                justify_content: JustifyContent::Center,
                                border_radius: BorderRadius::all(Val::Px(8.0)),
                                ..Default::default()
                            },
                            BackgroundColor(BTN_BG),
                            children![(
                                Text::new("Buy"),
                                TextFont {
                                    font_size: FontSize::Px(13.0),
                                    ..Default::default()
                                },
                                TextColor(Color::srgb(0.95, 0.95, 0.9)),
                            )],
                        ),
                        (
                            Button,
                            MarketEquipButton { id },
                            Node {
                                padding: UiRect::axes(Val::Px(10.0), Val::Px(6.0)),
                                justify_content: JustifyContent::Center,
                                border_radius: BorderRadius::all(Val::Px(8.0)),
                                ..Default::default()
                            },
                            BackgroundColor(BTN_BG),
                            children![(
                                Text::new("Equip"),
                                TextFont {
                                    font_size: FontSize::Px(13.0),
                                    ..Default::default()
                                },
                                TextColor(Color::srgb(0.95, 0.95, 0.9)),
                            )],
                        ),
                    ],
                ));
            }
            page.spawn((
                Text::new("External wallet (Express)"),
                TextFont {
                    font_size: FontSize::Px(16.0),
                    ..Default::default()
                },
                TextColor(ACCENT),
            ));
            boing_btn(page, "Prepare claim voucher", BoingAction::ClaimVoucher);
            boing_btn(page, "Open Claim Desk", BoingAction::OpenCompanion);
        });
}

fn spawn_page_challenges(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Challenges),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Weekly Challenges"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                MenuBodyText::Challenges,
                Text::new(""),
                TextFont {
                    font_size: FontSize::Px(14.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
        });
}

fn spawn_page_controls(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn((
            MenuPageRoot(MenuPage::Controls),
            Node {
                width: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(8.0),
                ..Default::default()
            },
            Visibility::Hidden,
        ))
        .with_children(|page| {
            page.spawn((
                Text::new("Controls"),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..Default::default()
                },
                TextColor(TEAL),
            ));
            page.spawn((
                Text::new(
                    "WASD move · mouse look · scroll zoom\n\
                     Pads · E / Enter start mode\n\
                     Create Map / My Maps · C skins · M claim\n\
                     Esc Nest menu → Characters to swap bases\n\
                     Ctrl+V link wallet · Ctrl+O claim desk\n\
                     Esc Nest menu · Q return Nest · R rematch\n\
                     ` free cursor · F11 fullscreen",
                ),
                TextFont {
                    font_size: FontSize::Px(13.0),
                    ..Default::default()
                },
                TextColor(MUTED),
            ));
        });
}

fn menu_btn(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    action: MenuAction,
    danger: bool,
) {
    let bg = if danger { DANGER } else { BTN_BG };
    parent
        .spawn((
            Button,
            MenuNavButton(action),
            Node {
                width: Val::Percent(100.0),
                padding: UiRect::axes(Val::Px(14.0), Val::Px(10.0)),
                justify_content: JustifyContent::Center,
                border_radius: BorderRadius::all(Val::Px(10.0)),
                ..Default::default()
            },
            BackgroundColor(bg),
        ))
        .with_children(|b| {
            b.spawn((
                Text::new(label.to_string()),
                TextFont {
                    font_size: FontSize::Px(16.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.96, 0.95, 0.9)),
            ));
        });
}

fn settings_btn(parent: &mut ChildSpawnerCommands, label: &str, action: SettingsAction) {
    parent
        .spawn((
            Button,
            SettingsActionButton(action),
            Node {
                width: Val::Percent(100.0),
                padding: UiRect::axes(Val::Px(14.0), Val::Px(8.0)),
                justify_content: JustifyContent::Center,
                border_radius: BorderRadius::all(Val::Px(10.0)),
                ..Default::default()
            },
            BackgroundColor(BTN_BG),
        ))
        .with_children(|b| {
            b.spawn((
                Text::new(label.to_string()),
                TextFont {
                    font_size: FontSize::Px(15.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.96, 0.95, 0.9)),
            ));
        });
}

fn boing_btn(parent: &mut ChildSpawnerCommands, label: &str, action: BoingAction) {
    parent
        .spawn((
            Button,
            MarketBoingButton(action),
            Node {
                width: Val::Percent(100.0),
                padding: UiRect::axes(Val::Px(14.0), Val::Px(8.0)),
                justify_content: JustifyContent::Center,
                border_radius: BorderRadius::all(Val::Px(10.0)),
                ..Default::default()
            },
            BackgroundColor(BTN_BG),
        ))
        .with_children(|b| {
            b.spawn((
                Text::new(label.to_string()),
                TextFont {
                    font_size: FontSize::Px(14.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.96, 0.95, 0.9)),
            ));
        });
}

fn account_btn(parent: &mut ChildSpawnerCommands, label: &str, action: AccountAction) {
    parent
        .spawn((
            Button,
            AccountActionButton(action),
            Node {
                width: Val::Percent(100.0),
                padding: UiRect::axes(Val::Px(14.0), Val::Px(8.0)),
                justify_content: JustifyContent::Center,
                border_radius: BorderRadius::all(Val::Px(10.0)),
                ..Default::default()
            },
            BackgroundColor(BTN_BG),
        ))
        .with_children(|b| {
            b.spawn((
                Text::new(label.to_string()),
                TextFont {
                    font_size: FontSize::Px(14.0),
                    ..Default::default()
                },
                TextColor(Color::srgb(0.96, 0.95, 0.9)),
            ));
        });
}

fn toggle_pause(
    keyboard: Res<ButtonInput<KeyCode>>,
    editor: Res<EditorMode>,
    mut pause: ResMut<PauseState>,
    mut page: ResMut<MenuPage>,
    mut camera: ResMut<ThirdPersonCamera>,
) {
    if editor.active || !keyboard.just_pressed(KeyCode::Escape) {
        return;
    }

    // Esc toggles Nest menu; always reopen on the first tab (Settings).
    if pause.paused {
        pause.paused = false;
        *page = MenuPage::Settings;
        camera.captured = true;
    } else {
        pause.paused = true;
        *page = MenuPage::Settings;
        camera.captured = false;
    }
}

fn sync_pause_cursor(
    pause: Res<PauseState>,
    camera: Res<ThirdPersonCamera>,
    mut cursor: Query<&mut CursorOptions, With<PrimaryWindow>>,
) {
    let Ok(mut cursor) = cursor.single_mut() else {
        return;
    };
    if pause.paused || !camera.captured {
        cursor.grab_mode = CursorGrabMode::None;
        cursor.visible = true;
    } else {
        cursor.grab_mode = CursorGrabMode::Locked;
        cursor.visible = false;
    }
}

fn update_pause_visibility(
    pause: Res<PauseState>,
    mut roots: Query<&mut Visibility, With<PauseRoot>>,
) {
    let Ok(mut vis) = roots.single_mut() else {
        return;
    };
    *vis = if pause.paused {
        Visibility::Visible
    } else {
        Visibility::Hidden
    };
}

fn sync_menu_page_visibility(
    pause: Res<PauseState>,
    page: Res<MenuPage>,
    mut pages: Query<(&MenuPageRoot, &mut Visibility, &mut Node), Without<PauseRoot>>,
) {
    for (root, mut vis, mut node) in &mut pages {
        let active = pause.paused && root.0 == *page;
        *vis = if active {
            Visibility::Visible
        } else {
            Visibility::Hidden
        };
        // Hidden still reserves flex space — collapse inactive pages.
        node.display = if active {
            Display::Flex
        } else {
            Display::None
        };
    }
}

fn sync_top_nav_highlight(
    pause: Res<PauseState>,
    page: Res<MenuPage>,
    mut tabs: Query<(&TopNavTab, &Interaction, &mut BackgroundColor, &mut BorderColor)>,
) {
    if !pause.paused {
        return;
    }
    for (tab, interaction, mut bg, mut border) in &mut tabs {
        let selected = tab.page == Some(*page);
        let danger = matches!(
            tab.action,
            MenuAction::ConfirmQuitYes | MenuAction::Open(MenuPage::ConfirmQuit)
        );
        let base = if danger { DANGER } else { BTN_BG };
        match *interaction {
            Interaction::Pressed => {
                *bg = BackgroundColor(if danger {
                    Color::srgb(0.65, 0.22, 0.2)
                } else {
                    BTN_PRESS
                });
            }
            Interaction::Hovered => {
                *bg = BackgroundColor(if danger {
                    Color::srgb(0.95, 0.42, 0.38)
                } else {
                    BTN_HOVER
                });
            }
            Interaction::None => {
                *bg = BackgroundColor(if selected {
                    Color::srgb(0.22, 0.42, 0.36)
                } else {
                    base
                });
            }
        }
        *border = BorderColor::all(if selected {
            ACCENT
        } else {
            Color::NONE
        });
    }
}

fn menu_button_hover(
    pause: Res<PauseState>,
    mut buttons: Query<
        (
            &Interaction,
            &mut BackgroundColor,
            Option<&MenuNavButton>,
            Option<&TopNavTab>,
        ),
        (Changed<Interaction>, With<Button>),
    >,
) {
    if !pause.paused {
        return;
    }
    for (interaction, mut bg, nav, top) in &mut buttons {
        // Top nav colors are driven by sync_top_nav_highlight.
        if top.is_some() {
            continue;
        }
        let danger = nav.is_some_and(|n| {
            matches!(
                n.0,
                MenuAction::ConfirmQuitYes | MenuAction::Open(MenuPage::ConfirmQuit)
            )
        });
        match *interaction {
            Interaction::Pressed => {
                *bg = BackgroundColor(if danger {
                    Color::srgb(0.65, 0.22, 0.2)
                } else {
                    BTN_PRESS
                });
            }
            Interaction::Hovered => {
                *bg = BackgroundColor(if danger {
                    Color::srgb(0.95, 0.42, 0.38)
                } else {
                    BTN_HOVER
                });
            }
            Interaction::None => {
                *bg = BackgroundColor(if danger { DANGER } else { BTN_BG });
            }
        }
    }
}

fn handle_menu_nav(
    mut pause: ResMut<PauseState>,
    mut page: ResMut<MenuPage>,
    mut camera: ResMut<ThirdPersonCamera>,
    mut leave: ResMut<LeaveToNestRequest>,
    mut exit: MessageWriter<AppExit>,
    mut banner: ResMut<NetworkBanner>,
    interactions: Query<(&Interaction, &MenuNavButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, nav) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        match nav.0 {
            MenuAction::Resume => {
                pause.paused = false;
                camera.captured = true;
                *page = MenuPage::Settings;
            }
            MenuAction::Open(next) => {
                *page = next;
            }
            MenuAction::ReturnToNest => {
                leave.pending = true;
                pause.paused = false;
                camera.captured = true;
                *page = MenuPage::Settings;
                banner.show("Returning to The Nest…", 2.5);
            }
            MenuAction::ConfirmQuitYes => {
                // Leave pause cleanly, then exit the process (no OS close chrome in borderless).
                pause.paused = false;
                camera.captured = false;
                exit.write(AppExit::Success);
            }
        }
    }
}

fn handle_settings_buttons(
    pause: Res<PauseState>,
    mut settings: ResMut<GameSettings>,
    mut windows: Query<&mut Window, With<PrimaryWindow>>,
    interactions: Query<(&Interaction, &SettingsActionButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, btn) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        apply_settings_action(&mut settings, &mut windows, btn.0);
    }
}

fn handle_market_equip(
    pause: Res<PauseState>,
    ledger: Res<SeasonLedger>,
    catalog: Res<crate::cosmetics::CosmeticsCatalog>,
    mut equipped: ResMut<EquippedCosmetic>,
    mut banner: ResMut<NetworkBanner>,
    mut commands: Commands,
    mut colors: Query<&mut crate::player::PlayerColor, With<crate::player::LocalPlayer>>,
    client: Option<Res<bevy_replicon_renet::RenetClient>>,
    interactions: Query<(&Interaction, &MarketEquipButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, btn) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        if ledger.unlocked.contains(&btn.id) {
            equipped.id = btn.id.clone();
            let tint = catalog
                .items
                .iter()
                .find(|i| i.id == btn.id)
                .map(|i| i.tint)
                .unwrap_or([0.95, 0.45, 0.35]);
            if client.is_some() {
                commands.client_trigger(crate::cosmetics::EquipCosmeticRequest {
                    id: btn.id.clone(),
                    tint,
                });
            } else if let Ok(mut color) = colors.single_mut() {
                color.0 = tint;
            }
            banner.show(format!("Equipped {}", btn.id), 2.0);
        } else {
            banner.show("Skin locked — earn more season points", 2.5);
        }
    }
}

fn handle_character_select(
    pause: Res<PauseState>,
    roster: Res<CharacterRoster>,
    mut defaults: ResMut<PlayerDefaults>,
    mut banner: ResMut<NetworkBanner>,
    mut commands: Commands,
    mut visuals: Query<&mut PlayerVisualSpec, With<crate::player::LocalPlayer>>,
    client: Option<Res<bevy_replicon_renet::RenetClient>>,
    interactions: Query<(&Interaction, &CharacterSelectButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, btn) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        if !crate::data::character_glb_exists(&btn.id) {
            banner.show(format!("Missing mesh for {}", btn.id), 2.5);
            continue;
        }
        defaults.set_crew_model(&btn.id);
        if client.is_some() {
            commands.client_trigger(SelectCharacterRequest {
                model_id: btn.id.clone(),
            });
        } else if let Ok(mut visual) = visuals.single_mut() {
            visual.model_id = Some(btn.id.clone());
        }
        let label = roster.label_for(&btn.id);
        banner.show(format!("Character: {label}"), 2.0);
    }
}

fn handle_account_buttons(
    pause: Res<PauseState>,
    mut account: ResMut<PlayerAccount>,
    mut form: ResMut<NestAuthForm>,
    mut banner: ResMut<NetworkBanner>,
    mut boing: ResMut<BoingConfig>,
    mut ledger: ResMut<SeasonLedger>,
    interactions: Query<(&Interaction, &AccountActionButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, btn) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        let note = match btn.0 {
            AccountAction::OpenWebsite => crate::account::open_website(&mut account),
            AccountAction::LinkPendingToken => {
                let note = crate::account::link_pending_token(&mut account);
                merge_owned_into_ledger(&account, &mut ledger);
                let _ = boing::link_cloud_wallet(&account, &mut boing, None);
                note
            }
            AccountAction::RefreshProfile => {
                let note = crate::account::refresh_profile(&mut account);
                merge_owned_into_ledger(&account, &mut ledger);
                let _ = boing::link_cloud_wallet(&account, &mut boing, None);
                note
            }
            AccountAction::ModeSignIn => {
                form.set_mode(NestAuthMode::SignIn);
                "Account: Sign In mode (Tab fields · type · Submit)".into()
            }
            AccountAction::ModeRegister => {
                form.set_mode(NestAuthMode::Register);
                "Account: Register mode (Tab fields · type · Submit)".into()
            }
            AccountAction::SubmitAuth => {
                let note = submit_nest_auth(&mut form, &mut account);
                if account.signed_in() {
                    merge_owned_into_ledger(&account, &mut ledger);
                    let _ = boing::link_cloud_wallet(&account, &mut boing, None);
                }
                note
            }
            AccountAction::SignOut => {
                account.clear();
                account.note.clone()
            }
        };
        banner.show(note, 3.5);
    }
}

fn handle_nest_auth_typing(
    pause: Res<PauseState>,
    page: Res<MenuPage>,
    mut form: ResMut<NestAuthForm>,
    mut account: ResMut<PlayerAccount>,
    mut banner: ResMut<NetworkBanner>,
    mut boing: ResMut<BoingConfig>,
    mut ledger: ResMut<SeasonLedger>,
    mut reader: bevy::ecs::message::MessageReader<bevy::input::keyboard::KeyboardInput>,
    keyboard: Res<ButtonInput<KeyCode>>,
) {
    use bevy::input::{keyboard::Key, ButtonState};

    if !pause.paused || *page != MenuPage::Account || form.busy {
        return;
    }

    for event in reader.read() {
        if event.state != ButtonState::Pressed {
            continue;
        }
        match &event.logical_key {
            Key::Tab => {
                form.cycle_focus();
                continue;
            }
            Key::Enter => {
                let note = submit_nest_auth(&mut form, &mut account);
                if account.signed_in() {
                    merge_owned_into_ledger(&account, &mut ledger);
                    let _ = boing::link_cloud_wallet(&account, &mut boing, None);
                }
                banner.show(note, 3.5);
                continue;
            }
            Key::Backspace => {
                form.focused_mut().pop();
                continue;
            }
            _ => {}
        }
        if keyboard.pressed(KeyCode::ControlLeft) || keyboard.pressed(KeyCode::ControlRight) {
            continue;
        }
        if let Some(text) = &event.text {
            for ch in text.chars() {
                if ch.is_control() {
                    continue;
                }
                let field = form.focused_mut();
                if field.len() < 96 {
                    field.push(ch);
                }
            }
        }
    }
}

fn submit_nest_auth(form: &mut NestAuthForm, account: &mut PlayerAccount) -> String {
    if form.busy {
        return "Busy…".into();
    }
    let email = form.email.trim().to_string();
    let password = form.password.clone();
    if email.is_empty() || password.is_empty() {
        return "Email and password are required.".into();
    }
    if password.len() < 8 {
        return "Password must be at least 8 characters.".into();
    }
    form.busy = true;
    let note = match form.mode {
        NestAuthMode::SignIn => crate::account::login(account, &email, &password),
        NestAuthMode::Register => {
            let name = form.display_name.trim().to_string();
            if name.is_empty() {
                form.busy = false;
                return "Display name is required to register.".into();
            }
            crate::account::signup(account, &email, &password, &name)
        }
    };
    form.busy = false;
    if account.signed_in() {
        form.password.clear();
    }
    note
}

fn merge_owned_into_ledger(account: &PlayerAccount, ledger: &mut SeasonLedger) {
    for id in &account.owned_skins {
        if !ledger.unlocked.contains(id) {
            ledger.unlocked.push(id.clone());
        }
    }
    ledger.save();
}

fn handle_market_buy(
    pause: Res<PauseState>,
    mut account: ResMut<PlayerAccount>,
    mut ledger: ResMut<SeasonLedger>,
    catalog: Res<CosmeticsCatalog>,
    mut banner: ResMut<NetworkBanner>,
    interactions: Query<(&Interaction, &MarketBuyButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, btn) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        if !account.signed_in() {
            banner.show("Sign in under Account to buy on-chain skins.", 3.5);
            continue;
        }
        let Some(item) = catalog.items.iter().find(|i| i.id == btn.id) else {
            banner.show("Unknown skin.", 2.5);
            continue;
        };
        if account.owned_skins.contains(&btn.id) {
            banner.show(format!("{} already owned on-chain.", item.label), 2.5);
            continue;
        }
        if ledger.points < item.cost_points {
            banner.show(
                format!(
                    "Need {} season pts (have {}).",
                    item.cost_points, ledger.points
                ),
                3.0,
            );
            continue;
        }
        let _ = crate::account::sync_season_points(&mut account, ledger.points);
        match crate::account::purchase_skin(&mut account, &btn.id, ledger.points) {
            Ok(msg) => {
                merge_owned_into_ledger(&account, &mut ledger);
                banner.show(msg, 4.0);
            }
            Err(err) => banner.show(err, 4.0),
        }
    }
}

fn sync_player_name_from_account(
    account: Res<PlayerAccount>,
    mut names: Query<&mut PlayerName, With<crate::player::LocalPlayer>>,
) {
    if !account.is_changed() || !account.signed_in() {
        return;
    }
    if let Ok(mut name) = names.single_mut() {
        name.0 = account.display_name.clone();
    }
}

fn handle_market_boing(
    pause: Res<PauseState>,
    mut config: ResMut<BoingConfig>,
    ledger: Res<SeasonLedger>,
    equipped: Res<EquippedCosmetic>,
    mut voucher: ResMut<ClaimVoucher>,
    mut banner: ResMut<NetworkBanner>,
    interactions: Query<(&Interaction, &MarketBoingButton), Changed<Interaction>>,
) {
    if !pause.paused {
        return;
    }
    for (interaction, btn) in &interactions {
        if *interaction != Interaction::Pressed {
            continue;
        }
        match btn.0 {
            BoingAction::LinkWallet => {
                let note = boing::link_wallet_from_env(&mut config, &mut voucher);
                banner.show(note, 3.0);
            }
            BoingAction::ClaimVoucher => {
                let note = boing::prepare_claim_voucher(
                    &config,
                    &ledger,
                    &equipped,
                    &mut voucher,
                );
                banner.show(note, 3.5);
            }
            BoingAction::OpenCompanion => {
                let note = boing::open_claim_companion_page(&mut voucher);
                banner.show(note, 3.0);
            }
        }
    }
}

fn refresh_menu_labels(
    pause: Res<PauseState>,
    page: Res<MenuPage>,
    settings: Res<GameSettings>,
    ledger: Res<SeasonLedger>,
    equipped: Res<EquippedCosmetic>,
    catalog: Res<CosmeticsCatalog>,
    roster: Res<CharacterRoster>,
    defaults: Res<PlayerDefaults>,
    config: Res<BoingConfig>,
    status: Res<BoingStatus>,
    board: Res<ChallengeBoard>,
    voucher: Res<ClaimVoucher>,
    account: Res<PlayerAccount>,
    form: Res<NestAuthForm>,
    mut texts: ParamSet<(
        Query<(&MenuBodyText, &mut Text)>,
        Query<(&MarketRowLabel, &mut Text)>,
        Query<(&CharacterRowLabel, &mut Text)>,
    )>,
) {
    if !pause.paused {
        return;
    }

    for (kind, mut text) in &mut texts.p0() {
        match (*kind, *page) {
            (MenuBodyText::Settings, MenuPage::Settings) => {
                **text = format!(
                    "Volume {:.0}% · Sensitivity {:.4} · Fullscreen {}",
                    settings.master_volume * 100.0,
                    settings.mouse_sensitivity,
                    if settings.fullscreen { "ON" } else { "off" }
                );
            }
            (MenuBodyText::Profile, MenuPage::Profile) => {
                let wallet = truncate_wallet(
                    account
                        .boing_wallet
                        .as_deref()
                        .or(config.linked_account.as_deref()),
                );
                let skin = catalog
                    .items
                    .iter()
                    .find(|i| i.id == equipped.id)
                    .map(|i| i.label.as_str())
                    .unwrap_or(equipped.id.as_str());
                let character = roster.label_for(&defaults.crew_model_id);
                let who = if account.signed_in() {
                    format!("{} ({})", account.display_name, account.email)
                } else {
                    "Guest — open Account to sign in".into()
                };
                **text = format!(
                    "{who}\nSeason {} · {} pts · {} parties\nCharacter: {}\nSkin tint: {}\nWallet: {}\nCharacters / Inventory / Wallet / Account for more",
                    ledger.season_id,
                    ledger.points,
                    ledger.parties_played,
                    character,
                    skin,
                    wallet,
                );
            }
            (MenuBodyText::Characters, MenuPage::Characters) => {
                let label = roster.label_for(&defaults.crew_model_id);
                **text = format!(
                    "Active: {label} (`{}`)\nPick a base to swap live — compare Soft vs Vivid in The Nest.",
                    defaults.crew_model_id
                );
            }
            (MenuBodyText::Account, MenuPage::Account) => {
                let mark = |field: NestAuthField| -> &'static str {
                    if form.focus == field {
                        ">"
                    } else {
                        " "
                    }
                };
                let masked: String = form.password.chars().map(|_| '*').collect();
                let mode = match form.mode {
                    NestAuthMode::SignIn => "Sign In",
                    NestAuthMode::Register => "Register",
                };
                let fields = match form.mode {
                    NestAuthMode::SignIn => format!(
                        "{} Email: {}\n{} Password: {}",
                        mark(NestAuthField::Email),
                        if form.email.is_empty() {
                            "_"
                        } else {
                            form.email.as_str()
                        },
                        mark(NestAuthField::Password),
                        if masked.is_empty() {
                            "_"
                        } else {
                            masked.as_str()
                        },
                    ),
                    NestAuthMode::Register => format!(
                        "{} Name: {}\n{} Email: {}\n{} Password: {}",
                        mark(NestAuthField::DisplayName),
                        if form.display_name.is_empty() {
                            "_"
                        } else {
                            form.display_name.as_str()
                        },
                        mark(NestAuthField::Email),
                        if form.email.is_empty() {
                            "_"
                        } else {
                            form.email.as_str()
                        },
                        mark(NestAuthField::Password),
                        if masked.is_empty() {
                            "_"
                        } else {
                            masked.as_str()
                        },
                    ),
                };
                if account.signed_in() {
                    let wallet = account
                        .boing_wallet
                        .as_deref()
                        .unwrap_or("(no Boing wallet)");
                    **text = format!(
                        "Signed in as {}\n{}\nBoing wallet {}\nOwned skins: {}\nAPI {}\n{}\n— or switch account ({mode}) —\n{fields}\nTab · type · Submit / Enter",
                        account.display_name,
                        account.email,
                        wallet,
                        account.owned_skins.len(),
                        account.api_base,
                        if account.note.is_empty() {
                            "Ready."
                        } else {
                            account.note.as_str()
                        },
                    );
                } else {
                    **text = format!(
                        "Not signed in · mode {mode}\n{fields}\nTab · type · Submit / Enter\nOr link website token at {}\nAPI: {}\n{}",
                        PlayerAccount::pending_token_path().display(),
                        account.api_base,
                        if account.note.is_empty() {
                            ""
                        } else {
                            account.note.as_str()
                        }
                    );
                }
            }
            (MenuBodyText::Inventory, MenuPage::Inventory) => {
                let owned = ledger.unlocked.len();
                let total = catalog.items.len();
                let cloud = account.owned_skins.len();
                let skin = catalog
                    .items
                    .iter()
                    .find(|i| i.id == equipped.id)
                    .map(|i| i.label.as_str())
                    .unwrap_or(equipped.id.as_str());
                **text = format!(
                    "Owned {owned}/{total} cosmetics · cloud NFTs {cloud} · equipped: {skin}\nBuy in Market (on-chain mint) or unlock via season pts."
                );
            }
            (MenuBodyText::Wallet, MenuPage::Wallet) => {
                let cloud = truncate_wallet(account.boing_wallet.as_deref());
                let local = truncate_wallet(config.linked_account.as_deref());
                let balance = status
                    .native_balance
                    .clone()
                    .unwrap_or_else(|| "—".into());
                let reach = if status.reachable {
                    "reachable"
                } else if status.last_error.is_empty() {
                    "unknown"
                } else {
                    "unreachable"
                };
                **text = format!(
                    "Season soft balance: {} pts (season {})\n\
                     Cloud wallet: {}\n\
                     Session wallet: {}\n\
                     Boing chain {} · RPC {}\n\
                     On-chain balance: {}\n\
                     Claim note: {}",
                    ledger.points,
                    ledger.season_id,
                    cloud,
                    local,
                    config.chain_id,
                    reach,
                    balance,
                    if voucher.note.is_empty() {
                        "none yet"
                    } else {
                        voucher.note.as_str()
                    }
                );
            }
            (MenuBodyText::Challenges, MenuPage::Challenges) => {
                if board.defs.is_empty() {
                    **text = "No weekly challenges loaded.".into();
                } else {
                    let mut lines = vec![format!("Week {}", board.week)];
                    for d in &board.defs {
                        let p = board.progress.get(&d.id).copied().unwrap_or(0);
                        let mark = if board.claimed.contains(&d.id) {
                            "[done]"
                        } else if p >= d.target {
                            "[ready]"
                        } else {
                            "[…]"
                        };
                        lines.push(format!(
                            "{} {} — {}/{} (+{} pts)",
                            mark,
                            d.label,
                            p.min(d.target),
                            d.target,
                            d.reward_points
                        ));
                    }
                    **text = lines.join("\n");
                }
            }
            (MenuBodyText::MarketStatus, MenuPage::Market) => {
                **text = format!(
                    "{} season pts · equipped {} · cloud NFTs {}\nBuy mints a PUDGY NFT to your custodial wallet · {}",
                    ledger.points,
                    equipped.id,
                    account.owned_skins.len(),
                    if voucher.note.is_empty() {
                        "Express fallback ready"
                    } else {
                        voucher.note.as_str()
                    }
                );
            }
            _ => {}
        }
    }

    if matches!(*page, MenuPage::Characters) {
        for (row, mut text) in &mut texts.p2() {
            let Some(entry) = roster.characters.iter().find(|c| c.id == row.id) else {
                continue;
            };
            let mark = if defaults.crew_model_id == row.id {
                "● Active"
            } else {
                "○"
            };
            **text = format!("{mark} {}\n{}", entry.label, entry.blurb);
        }
    }

    if matches!(*page, MenuPage::Market | MenuPage::Inventory) {
        for (row, mut text) in &mut texts.p1() {
            let Some(item) = catalog.items.iter().find(|i| i.id == row.id) else {
                continue;
            };
            let cloud = account.owned_skins.contains(&row.id);
            let unlocked = ledger.unlocked.contains(&row.id) || cloud;
            if matches!(*page, MenuPage::Inventory) {
                let state = if equipped.id == row.id {
                    "Equipped"
                } else if unlocked {
                    if cloud {
                        "Owned (NFT) — Equip"
                    } else {
                        "Owned — Equip"
                    }
                } else {
                    "Locked"
                };
                **text = format!("{} · {state}", item.label);
            } else {
                let state = if equipped.id == row.id {
                    "Equipped"
                } else if cloud {
                    "Owned on-chain"
                } else if unlocked {
                    "Unlocked"
                } else {
                    "Buy"
                };
                **text = format!("{} · {} pts · {state}", item.label, item.cost_points);
            }
        }
    }
}

fn truncate_wallet(account: Option<&str>) -> String {
    match account {
        Some(a) if a.len() > 14 => format!("{}…{}", &a[..8], &a[a.len() - 4..]),
        Some(a) => a.to_string(),
        None => "not linked".into(),
    }
}

fn apply_settings_hotkeys(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut settings: ResMut<GameSettings>,
    mut windows: Query<&mut Window, With<PrimaryWindow>>,
) {
    if keyboard.just_pressed(KeyCode::BracketLeft) {
        apply_settings_action(&mut settings, &mut windows, SettingsAction::VolumeDown);
    }
    if keyboard.just_pressed(KeyCode::BracketRight) {
        apply_settings_action(&mut settings, &mut windows, SettingsAction::VolumeUp);
    }
    if keyboard.just_pressed(KeyCode::Minus) {
        apply_settings_action(&mut settings, &mut windows, SettingsAction::SensDown);
    }
    if keyboard.just_pressed(KeyCode::Equal) {
        apply_settings_action(&mut settings, &mut windows, SettingsAction::SensUp);
    }
    if keyboard.just_pressed(KeyCode::F11) {
        apply_settings_action(
            &mut settings,
            &mut windows,
            SettingsAction::ToggleFullscreen,
        );
    }
}

fn apply_settings_action(
    settings: &mut GameSettings,
    windows: &mut Query<&mut Window, With<PrimaryWindow>>,
    action: SettingsAction,
) {
    match action {
        SettingsAction::VolumeDown => {
            settings.master_volume = (settings.master_volume - 0.1).clamp(0.0, 1.0);
        }
        SettingsAction::VolumeUp => {
            settings.master_volume = (settings.master_volume + 0.1).clamp(0.0, 1.0);
        }
        SettingsAction::SensDown => {
            settings.mouse_sensitivity =
                (settings.mouse_sensitivity - 0.0004).clamp(0.0005, 0.008);
        }
        SettingsAction::SensUp => {
            settings.mouse_sensitivity =
                (settings.mouse_sensitivity + 0.0004).clamp(0.0005, 0.008);
        }
        SettingsAction::ToggleFullscreen => {
            settings.fullscreen = !settings.fullscreen;
            if let Ok(mut window) = windows.single_mut() {
                window.decorations = false;
                window.resizable = false;
                window.enabled_buttons = bevy::window::EnabledButtons {
                    minimize: false,
                    maximize: false,
                    close: false,
                };
                window.mode = if settings.fullscreen {
                    WindowMode::BorderlessFullscreen(MonitorSelection::Current)
                } else {
                    WindowMode::Windowed
                };
            }
        }
    }
}
