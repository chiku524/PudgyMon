class_name ImmersiveStudioRegistry
extends RefCounted

## ShipHappens asset registry — uses generic helpers from third_party/immersive_studio.

const IMPORT_ROOT := "res://assets/models"


static func register_all() -> void:
	_register("env_space_station_wall_04", 2.0)
	_register("env_light_oval_panel_01", 0.6)
	_register("env_blue_yellow_welcome_sign_01", 3.0)
	_register("cargo_ring_sign_01", 1.5)
	_register("env_freight_deck_panel_01", 0.5)
	_register("prop_wall_janitor_vent_grille", 1.0)
	_register("env_break_glass_panel_01", 0.5)
	_register("wall_panel_breach_hole_01", 1.0)
	_register("safety_mat_floor_pad_01", -1.0, 2.0)
	_register("satellite_dish_maintenance_wheel_crank_01", 0.5)
	_register("env_cargo_crane_operator_console_01", 1.2)
	_register("env_freight_deck_pad_01", 0.5)
	_register("prop_cartoon_vending_machine", 1.9)
	_register("env_freestanding_maintenance_cabinet_01", 1.8)
	_register("env_breaker_panel_01", 1.0)
	_register("prop_pneumatic_tube_intake_funnel", 1.2)
	_register("office_printer_cartoon_space_station_01", 0.8)
	_register("blue_cartoon_sci_fi_job_terminal_kiosk_01", 1.5)


static func _register(asset_id: String, target_height: float, target_width: float = -1.0) -> void:
	var folder := "%s/%s" % [IMPORT_ROOT, asset_id]
	ImmersiveStudioMaterial.register_asset(
		asset_id,
		"%s/%s.glb" % [folder, asset_id],
		target_height,
		target_width,
		folder,
	)
