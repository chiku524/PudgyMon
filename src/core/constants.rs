pub const DEFAULT_PORT: u16 = 7777;
pub const MAX_PLAYERS: usize = 8;
pub const PROTOCOL_ID: u64 = 0x5348_4950;

pub const CRANE_JOB_ID: &str = "crane_of_regret";
pub const POWER_HOUR_JOB_ID: &str = "power_hour";

pub const INTERACT_RADIUS: f32 = 3.5;

pub const PLAYER_SPEED: f32 = 6.0;
pub const PLAYER_SPRINT_MULTIPLIER: f32 = 1.6;

pub const MOUSE_SENSITIVITY: f32 = 0.0025;
pub const MIN_CAMERA_PITCH: f32 = -35.0_f32.to_radians();
pub const MAX_CAMERA_PITCH: f32 = 55.0_f32.to_radians();
pub const CAMERA_MIN_DISTANCE: f32 = 2.5;
pub const CAMERA_MAX_DISTANCE: f32 = 8.0;
pub const CAMERA_DEFAULT_DISTANCE: f32 = 5.0;

/// Godot `JobSystem.POWER_HOUR_SEQUENCE`
pub const POWER_HOUR_SEQUENCE: [u8; 4] = [0, 2, 1, 3];

pub const CRANE_CONSOLE_ASSET: &str = "env_cargo_crane_operator_console_01";
pub const BREAKER_PANEL_ASSET: &str = "env_breaker_panel_01";
pub const FREIGHT_CRATE_ASSET: &str = "env_freight_crate_01";
pub const GANTRY_HOOK_ASSET: &str = "env_cargo_gantry_hook_01";
pub const JOB_KIOSK_ASSET: &str = "blue_cartoon_sci_fi_job_terminal_kiosk_01";
pub const COOLANT_CONSOLE_ASSET: &str = "prop_coolant_console_01";
pub const SHUTTLE_BAY_ASSET: &str = "shuttle_bay_escape_zone_01";
