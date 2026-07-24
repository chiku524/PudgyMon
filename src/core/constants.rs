pub const DEFAULT_PORT: u16 = 7777;
pub const MAX_PLAYERS: usize = 16;
pub const PROTOCOL_ID: u64 = 0x5348_4950;

pub const CRANE_JOB_ID: &str = "crane_of_regret";
pub const POWER_HOUR_JOB_ID: &str = "power_hour";

pub const INTERACT_RADIUS: f32 = 3.5;

pub const PLAYER_SPEED: f32 = 7.0;
pub const PLAYER_SPRINT_MULTIPLIER: f32 = 1.6;
pub const PLAYER_FLOOR_Y: f32 = 1.0;
/// Peak height ≈ v² / (2g). First hop 4.5u, double-jump 6.5u at this gravity.
pub const PLAYER_GRAVITY: f32 = 24.0;
pub const PLAYER_JUMP_VELOCITY: f32 = 14.697; // sqrt(2 * 24 * 4.5)
pub const PLAYER_DOUBLE_JUMP_VELOCITY: f32 = 17.664; // sqrt(2 * 24 * 6.5)
pub const PLAYER_MAX_AIR_JUMPS: u8 = 1;

/// Soft playable bounds for the arena shell (XZ half-extent).
/// Nest floor / walls should stay slightly outside this.
pub const ARENA_BOUNDS: f32 = 36.0;

/// Seconds of grace after a room clears before elimination/finale advance.
pub const ROOM_CLEAR_GRACE_SECS: f32 = 1.25;

pub const MOUSE_SENSITIVITY: f32 = 0.0025;
pub const MIN_CAMERA_PITCH: f32 = -35.0_f32.to_radians();
pub const MAX_CAMERA_PITCH: f32 = 55.0_f32.to_radians();
pub const CAMERA_MIN_DISTANCE: f32 = 2.5;
pub const CAMERA_MAX_DISTANCE: f32 = 12.0;
pub const CAMERA_DEFAULT_DISTANCE: f32 = 6.5;

/// Breaker Panic sequence (12 switches — GDD party scale; labels lie).
pub const POWER_HOUR_SEQUENCE: [u8; 12] = [0, 5, 2, 9, 1, 7, 3, 11, 4, 8, 6, 10];

pub const CRANE_CONSOLE_ASSET: &str = "env_cargo_crane_operator_console_01";
pub const BREAKER_PANEL_ASSET: &str = "env_breaker_panel_01";

/// Fully Tripo-generated (baked JPEG Color/Normal/ORM) — prefer these for layout polish.
pub const FREIGHT_CRATE_ASSET: &str = "env_freight_crate_01";
pub const GANTRY_HOOK_ASSET: &str = "env_cargo_gantry_hook_01";
pub const COOLANT_CONSOLE_ASSET: &str = "prop_coolant_console_01";
pub const COOLANT_WHEEL_A_ASSET: &str = "prop_coolant_pipe_wheel_01";
pub const COOLANT_WHEEL_B_ASSET: &str = "prop_coolant_pipe_wheel_02";
pub const SHUTTLE_BAY_ASSET: &str = "shuttle_bay_escape_zone_01";
pub const HOT_DOG_CRATE_ASSET: &str = "s1_galactic_hot_dog_crate_01";
pub const CARGO_SCANNER_ASSET: &str = "prop_cargo_scanner_platform";
pub const ALIEN_SLOT_MACHINE_ASSET: &str = "prop_alien_slot_machine";
pub const DUCT_TAPE_CART_ASSET: &str = "duct_tape_dispenser_cart_01";
pub const MOP_BUCKET_CART_ASSET: &str = "prop_janitor_mop_bucket_cart_01";
pub const MAINTENANCE_LADDER_ASSET: &str = "prop_wobbly_maintenance_ladder_01";
pub const SATELLITE_DISH_ASSET: &str = "prop_satellite_dish_array_01";
pub const HULL_PATCH_ASSET: &str = "prop_hull_patch_plate_01";
pub const SLIME_PUDDLE_ASSET: &str = "prop_slime_puddle_floor_01";
