extends Node3D

## Procedural station dressing — lighting, zone floors, clutter, and sky.

const MODEL_WALL := preload("res://assets/models/env_space_station_wall_04/env_space_station_wall_04.glb")
const MODEL_LIGHT := preload("res://assets/models/env_light_oval_panel_01/env_light_oval_panel_01.glb")
const MODEL_WELCOME_SIGN := preload("res://assets/models/env_blue_yellow_welcome_sign_01/env_blue_yellow_welcome_sign_01.glb")
const MODEL_CARGO_SIGN := preload("res://assets/models/cargo_ring_sign_01/cargo_ring_sign_01.glb")
const MODEL_FREIGHT_DECK := preload("res://assets/models/env_freight_deck_panel_01/env_freight_deck_panel_01.glb")
const MODEL_VENT_GRILLE := preload("res://assets/models/prop_wall_janitor_vent_grille/prop_wall_janitor_vent_grille.glb")
const MODEL_FREIGHT_PAD := preload("res://assets/models/env_freight_deck_pad_01/env_freight_deck_pad_01.glb")
const MODEL_BREAKER_PANEL := preload("res://assets/models/env_breaker_panel_01/env_breaker_panel_01.glb")
const MODEL_BREAK_GLASS := preload("res://assets/models/env_break_glass_panel_01/env_break_glass_panel_01.glb")
const MODEL_SAFETY_MAT := preload("res://assets/models/safety_mat_floor_pad_01/safety_mat_floor_pad_01.glb")

const ZONE_TILES := [
	{"name": "Main Hub", "pos": Vector3(0, 0.02, 0), "size": Vector3(18, 0.03, 18), "color": Color(0.32, 0.34, 0.42)},
	{"name": "Cargo Ring", "pos": Vector3(-28, 0.02, -10), "size": Vector3(16, 0.03, 14), "color": Color(0.42, 0.28, 0.18)},
	{"name": "Ops Deck", "pos": Vector3(28, 0.02, 0), "size": Vector3(14, 0.03, 16), "color": Color(0.18, 0.32, 0.48)},
	{"name": "Break Room", "pos": Vector3(0, 0.02, 24), "size": Vector3(16, 0.03, 12), "color": Color(0.2, 0.4, 0.28)},
	{"name": "Docking Arm", "pos": Vector3(32, 0.02, -24), "size": Vector3(12, 0.03, 12), "color": Color(0.45, 0.2, 0.2)},
]

const CLUTTER_CRATES := [
	Vector3(-24, 0.6, -6), Vector3(-30, 0.6, -12), Vector3(-26, 0.6, 2),
	Vector3(22, 0.6, 8), Vector3(30, 0.6, -8), Vector3(34, 0.6, -18),
	Vector3(-8, 0.6, 22), Vector3(6, 0.6, 26), Vector3(-2, 0.6, 14),
	Vector3(38, 0.6, -26), Vector3(28, 0.6, -30), Vector3(-16, 0.6, -2),
]

const PIPE_SEGMENTS := [
	{"from": Vector3(-38, 4, -20), "to": Vector3(38, 4, -20)},
	{"from": Vector3(-38, 4, 20), "to": Vector3(38, 4, 20)},
	{"from": Vector3(-38, 4, -20), "to": Vector3(-38, 4, 20)},
	{"from": Vector3(38, 4, -20), "to": Vector3(38, 4, 20)},
]

var _anim_time: float = 0.0
var _crane_hook: Node3D = null
var _blink_materials: Array[StandardMaterial3D] = []


func _ready() -> void:
	_setup_environment()
	_upgrade_base_geometry()
	_add_ceiling()
	_add_zone_tiles()
	_add_wall_cladding()
	_add_lights()
	_add_pipes()
	_add_clutter()
	_add_hub_props()
	_add_cargo_ring_props()
	_add_break_room_props()
	_add_ops_deck_props()
	_add_docking_arm_props()
	_add_wayfinding()
	_add_zone_borders()
	_add_kiosk_beacon()
	_add_objective_markers()
	_add_floor_grid()
	_add_wall_trim()
	_add_hub_furniture()
	_add_corridor_details()
	_add_power_hour_visuals()
	_add_trust_fall_visuals()
	_add_space_viewports()


func _process(delta: float) -> void:
	_anim_time += delta
	if _crane_hook:
		_crane_hook.position.y = 3.2 + sin(_anim_time * 0.8) * 0.35
	for mat in _blink_materials:
		mat.emission_energy_multiplier = 0.25 + maxf(sin(_anim_time * 4.0), 0.0) * 0.75


func _setup_environment() -> void:
	var world_env: WorldEnvironment = get_parent().get_node_or_null("WorldEnvironment")
	if world_env == null:
		return

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.04, 0.05, 0.1)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.35, 0.38, 0.5)
	env.ambient_light_energy = 0.45
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.05
	env.fog_enabled = true
	env.fog_light_color = Color(0.25, 0.28, 0.38)
	env.fog_density = 0.002
	env.glow_enabled = true
	env.glow_intensity = 0.35
	world_env.environment = env


func _upgrade_base_geometry() -> void:
	var map := get_parent()
	if map == null:
		return
	var floor_mesh := map.get_node_or_null("Floor/MeshInstance3D") as MeshInstance3D
	if floor_mesh:
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.16, 0.18, 0.24)
		mat.metallic = 0.15
		mat.roughness = 0.82
		floor_mesh.material_override = mat
	for wall_name in ["North", "South", "East", "West"]:
		var wall_body := map.get_node_or_null("Walls/%s" % wall_name) as Node3D
		if wall_body == null:
			continue
		var wall_mesh := wall_body.get_node_or_null("MeshInstance3D") as MeshInstance3D
		if wall_mesh:
			wall_mesh.visible = false


func _add_ceiling() -> void:
	var ceiling := MeshInstance3D.new()
	ceiling.name = "Ceiling"
	var mesh := BoxMesh.new()
	mesh.size = Vector3(78, 0.4, 78)
	ceiling.mesh = mesh
	ceiling.position = Vector3(0, 5.8, 0)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.12, 0.13, 0.18)
	mat.metallic = 0.35
	mat.roughness = 0.75
	ceiling.material_override = mat
	add_child(ceiling)


func _add_zone_tiles() -> void:
	var root := Node3D.new()
	root.name = "ZoneTiles"
	add_child(root)
	for zone in ZONE_TILES:
		if zone["name"] == "Cargo Ring":
			continue
		var tile := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = zone["size"]
		tile.mesh = mesh
		tile.position = zone["pos"]
		var mat := StandardMaterial3D.new()
		mat.albedo_color = zone["color"]
		mat.roughness = 0.85
		tile.material_override = mat
		root.add_child(tile)


func _add_lights() -> void:
	var root := Node3D.new()
	root.name = "CeilingLights"
	add_child(root)
	for x in range(-30, 35, 15):
		for z in range(-30, 35, 15):
			var light := OmniLight3D.new()
			light.position = Vector3(x, 5.2, z)
			light.light_color = Color(1.0, 0.92, 0.78)
			light.light_energy = 0.55
			light.omni_range = 14.0
			light.shadow_enabled = x % 30 == 0
			root.add_child(light)

			_spawn_scaled_model(
				root,
				MODEL_LIGHT,
				"env_light_oval_panel_01",
				light.position + Vector3(0, -0.28, 0),
				0.0,
				0.6,
				true
			)


func _add_pipes() -> void:
	var root := Node3D.new()
	root.name = "Pipes"
	add_child(root)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.45, 0.48, 0.52)
	mat.metallic = 0.7
	mat.roughness = 0.35

	for segment in PIPE_SEGMENTS:
		var start: Vector3 = segment["from"]
		var end: Vector3 = segment["to"]
		var pipe := MeshInstance3D.new()
		var mesh := CylinderMesh.new()
		mesh.top_radius = 0.18
		mesh.bottom_radius = 0.18
		mesh.height = start.distance_to(end)
		pipe.mesh = mesh
		pipe.material_override = mat
		root.add_child(pipe)
		pipe.position = (start + end) * 0.5
		pipe.look_at(end, Vector3.UP)
		pipe.rotate_object_local(Vector3.RIGHT, PI * 0.5)


func _add_clutter() -> void:
	var root := Node3D.new()
	root.name = "Clutter"
	add_child(root)
	var crate_mat := StandardMaterial3D.new()
	crate_mat.albedo_color = Color(0.55, 0.38, 0.22)
	crate_mat.roughness = 0.9

	for pos in CLUTTER_CRATES:
		var crate := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(1.1, 1.1, 1.1)
		crate.mesh = mesh
		crate.position = pos
		crate.rotation.y = randf_range(0, TAU)
		crate.material_override = crate_mat
		root.add_child(crate)


func _add_hub_props() -> void:
	var root := Node3D.new()
	root.name = "HubProps"
	add_child(root)

	var welcome := _spawn_scaled_model(
		root,
		MODEL_WELCOME_SIGN,
		"env_blue_yellow_welcome_sign_01",
		Vector3(0, 3.05, -13.55),
		PI,
		3.0,
		false
	)
	_add_sign_label(
		welcome,
		"WELCOME TO MEGABARGAIN ORBIT #12\nDiscount Freight · Questionable Safety",
		Vector3(0, 0, -0.14),
		20
	)
	_add_label_panel(root, Vector3(0, 2.8, -2), "MAIN HUB\nJob Kiosk · Printer · Manifest · Trust Fall")
	_add_caution_stripe(root, Vector3(0, 0.04, -33), Vector3(8, 0.02, 3))


func _add_label_panel(parent: Node3D, pos: Vector3, text: String) -> void:
	var panel := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(10, 2.5, 0.2)
	panel.mesh = mesh
	panel.position = pos
	var frame := StandardMaterial3D.new()
	frame.albedo_color = Color(0.15, 0.16, 0.22)
	frame.metallic = 0.4
	panel.material_override = frame
	parent.add_child(panel)

	var label := Label3D.new()
	label.text = text
	label.font_size = 22
	label.outline_size = 6
	label.position = pos + Vector3(0, 0, -0.2)
	parent.add_child(label)


func _add_caution_stripe(parent: Node3D, pos: Vector3, size: Vector3) -> void:
	var stripe := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	stripe.mesh = mesh
	stripe.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.9, 0.75, 0.1)
	mat.emission_enabled = true
	mat.emission = Color(0.8, 0.6, 0.05)
	mat.emission_energy_multiplier = 0.25
	stripe.material_override = mat
	parent.add_child(stripe)


func _add_terminal_kiosk(parent: Node3D, pos: Vector3) -> void:
	var base := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(1.2, 1.4, 0.6)
	base.mesh = mesh
	base.position = pos + Vector3(0, 0.7, 0)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.2, 0.55, 0.85)
	mat.metallic = 0.25
	base.material_override = mat
	parent.add_child(base)

	var screen := MeshInstance3D.new()
	var screen_mesh := BoxMesh.new()
	screen_mesh.size = Vector3(0.9, 0.55, 0.05)
	screen.mesh = screen_mesh
	screen.position = pos + Vector3(0, 1.25, -0.28)
	var screen_mat := StandardMaterial3D.new()
	screen_mat.albedo_color = Color(0.15, 0.85, 0.95)
	screen_mat.emission_enabled = true
	screen_mat.emission = Color(0.1, 0.7, 0.9)
	screen_mat.emission_energy_multiplier = 0.8
	screen.material_override = screen_mat
	parent.add_child(screen)


func _add_cargo_ring_props() -> void:
	var root := Node3D.new()
	root.name = "CargoRingProps"
	add_child(root)
	var origin := Vector3(-28, 0, -10)

	# Gantry crane frame
	_add_box(root, origin + Vector3(-6, 3.5, 0), Vector3(0.35, 7, 0.35), Color(0.5, 0.52, 0.58), 0.8)
	_add_box(root, origin + Vector3(6, 3.5, 0), Vector3(0.35, 7, 0.35), Color(0.5, 0.52, 0.58), 0.8)
	_add_box(root, origin + Vector3(0, 6.8, 0), Vector3(13, 0.35, 0.35), Color(0.5, 0.52, 0.58), 0.8)

	_crane_hook = Node3D.new()
	_crane_hook.name = "CraneHook"
	_crane_hook.position = origin + Vector3(0, 3.2, 0)
	root.add_child(_crane_hook)
	_add_box(_crane_hook, Vector3(0, -0.5, 0), Vector3(0.8, 0.15, 0.8), Color(0.95, 0.8, 0.15), 0.6)
	_add_box(_crane_hook, Vector3(0, -1.2, 0), Vector3(0.5, 0.5, 0.5), Color(0.55, 0.38, 0.22), 0.2)

	for offset in [Vector3(-4, 0, -4), Vector3(3, 0, 3), Vector3(-2, 0, 4), Vector3(5, 0, -3)]:
		_add_crate_stack(root, origin + offset)

	for i in 3:
		_add_cone(root, origin + Vector3(-5 + i * 2.5, 0, -5), Color(0.95, 0.55, 0.1))

	var cargo_sign := _spawn_scaled_model(
		root,
		MODEL_CARGO_SIGN,
		"cargo_ring_sign_01",
		origin + Vector3(0, 3.8, -6.15),
		PI,
		1.5,
		false
	)
	_add_sign_label(
		cargo_sign,
		"CARGO RING\nLift With Confidence™",
		Vector3(0, 0, -0.12),
		18
	)

	for gx in 4:
		for gz in 3:
			_spawn_scaled_model(
				root,
				MODEL_FREIGHT_DECK,
				"env_freight_deck_panel_01",
				origin + Vector3(-4.5 + gx * 3.0, 0.0, -3.0 + gz * 3.0),
				0.0,
				0.5,
				true
			)

	_spawn_scaled_model(
		root,
		MODEL_FREIGHT_PAD,
		"env_freight_deck_pad_01",
		origin + Vector3(0, 0.0, 0),
		0.0,
		0.5,
		true
	)


func _add_break_room_props() -> void:
	var root := Node3D.new()
	root.name = "BreakRoomProps"
	add_child(root)
	var origin := Vector3(0, 0, 24)

	_add_box(root, origin + Vector3(0, 0.45, 0), Vector3(4.5, 0.9, 2.2), Color(0.35, 0.28, 0.22), 0.3)
	for seat_offset in [Vector3(-1.2, 0.25, 1.3), Vector3(1.2, 0.25, 1.3), Vector3(0, 0.25, -1.3)]:
		_add_box(root, origin + seat_offset, Vector3(0.7, 0.5, 0.7), Color(0.25, 0.55, 0.75), 0.2)

	_add_box(root, origin + Vector3(-3.5, 0.35, 0), Vector3(1.8, 0.7, 0.9), Color(0.6, 0.25, 0.25), 0.25)
	_spawn_scaled_model(
		root,
		MODEL_BREAK_GLASS,
		"env_break_glass_panel_01",
		origin + Vector3(5.5, 1.4, -4.8),
		PI,
		0.5,
		false
	)
	_add_label_panel(root, origin + Vector3(0, 3.0, -5), "BREAK ROOM\nMandatory Fun Zone")
	_add_poster(root, origin + Vector3(4, 2.2, -2), "Employee of the Month:\nStill TBD")


func _add_ops_deck_props() -> void:
	var root := Node3D.new()
	root.name = "OpsDeckProps"
	add_child(root)
	var origin := Vector3(28, 0, 0)

	for i in 4:
		var rack_x := origin + Vector3(-4 + i * 2.2, 0, -4)
		_add_server_rack(root, rack_x)

	_add_box(root, origin + Vector3(0, 1.2, 4), Vector3(3, 2.4, 1.2), Color(0.2, 0.45, 0.65), 0.35)
	_add_cylinder(root, origin + Vector3(3, 1.0, 4), 0.45, 2.0, Color(0.55, 0.65, 0.72), Vector3.ZERO)
	_add_cylinder(root, origin + Vector3(-3, 1.0, 4), 0.35, 1.6, Color(0.45, 0.55, 0.68), Vector3.ZERO)
	_add_label_panel(root, origin + Vector3(0, 4.2, -5), "OPS DECK\nPlease Do Not Touch The Coolant")


func _add_docking_arm_props() -> void:
	var root := Node3D.new()
	root.name = "DockingArmProps"
	add_child(root)
	var origin := Vector3(32, 0, -24)

	_add_box(root, origin + Vector3(0, 2.5, -3), Vector3(8, 5, 0.4), Color(0.35, 0.38, 0.45), 0.55)
	_add_box(root, origin + Vector3(-3.5, 1.2, -2.5), Vector3(0.3, 2.4, 0.3), Color(0.4, 0.42, 0.48), 0.6)
	_add_box(root, origin + Vector3(3.5, 1.2, -2.5), Vector3(0.3, 2.4, 0.3), Color(0.4, 0.42, 0.48), 0.6)

	for i in 3:
		var blink := _make_blink_material(Color(0.95, 0.15, 0.1))
		var light_mesh := MeshInstance3D.new()
		var mesh := SphereMesh.new()
		mesh.radius = 0.12
		mesh.height = 0.24
		light_mesh.mesh = mesh
		light_mesh.position = origin + Vector3(-2 + i * 2, 3.2, -2.8)
		light_mesh.material_override = blink
		root.add_child(light_mesh)

	_add_caution_stripe(root, origin + Vector3(0, 0.07, 1), Vector3(6, 0.02, 2))
	_add_label_panel(root, origin + Vector3(0, 4.8, 0), "DOCKING ARM\nTape Required Beyond This Point")


func _add_crate_stack(parent: Node3D, base: Vector3) -> void:
	for i in 2:
		_add_box(parent, base + Vector3(0, 0.55 + i * 1.05, 0), Vector3(1.0, 1.0, 1.0), Color(0.55, 0.38, 0.22), 0.15)


func _add_cone(parent: Node3D, pos: Vector3, color: Color) -> void:
	var cone := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.02
	mesh.bottom_radius = 0.22
	mesh.height = 0.55
	cone.mesh = mesh
	cone.position = pos + Vector3(0, 0.28, 0)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	cone.material_override = mat
	parent.add_child(cone)


func _add_server_rack(parent: Node3D, pos: Vector3) -> void:
	_add_box(parent, pos + Vector3(0, 1.1, 0), Vector3(1.2, 2.2, 0.7), Color(0.14, 0.16, 0.2), 0.5)
	for row in 4:
		var led := _make_blink_material(Color(0.1, 0.85, 0.45))
		var led_mesh := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(0.8, 0.08, 0.02)
		led_mesh.mesh = mesh
		led_mesh.position = pos + Vector3(0, 0.5 + row * 0.45, -0.32)
		led_mesh.material_override = led
		parent.add_child(led_mesh)


func _add_poster(parent: Node3D, pos: Vector3, text: String) -> void:
	_add_box(parent, pos, Vector3(2.2, 1.6, 0.05), Color(0.85, 0.2, 0.35), 0.1)
	var label := Label3D.new()
	label.text = text
	label.font_size = 16
	label.outline_size = 4
	label.position = pos + Vector3(0, 0, -0.08)
	parent.add_child(label)


func _add_box(
	parent: Node3D,
	pos: Vector3,
	size: Vector3,
	color: Color,
	metallic: float = 0.0
) -> MeshInstance3D:
	var box := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	box.mesh = mesh
	box.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.metallic = metallic
	mat.roughness = 1.0 - metallic * 0.5
	box.material_override = mat
	parent.add_child(box)
	return box


func _add_cylinder(
	parent: Node3D,
	pos: Vector3,
	radius: float,
	height: float,
	color: Color,
	euler: Vector3
) -> void:
	var cyl := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	cyl.mesh = mesh
	cyl.position = pos
	cyl.rotation = euler
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.metallic = 0.4
	cyl.material_override = mat
	parent.add_child(cyl)


func _add_zone_borders() -> void:
	var root := Node3D.new()
	root.name = "ZoneBorders"
	add_child(root)
	for zone in ZONE_TILES:
		var size: Vector3 = zone["size"]
		var pos: Vector3 = zone["pos"]
		var color: Color = zone["color"].lightened(0.35)
		color.a = 1.0
		var border_mat := StandardMaterial3D.new()
		border_mat.albedo_color = color
		border_mat.emission_enabled = true
		border_mat.emission = color
		border_mat.emission_energy_multiplier = 0.2
		var half_x: float = size.x * 0.5
		var half_z: float = size.z * 0.5
		var y: float = pos.y + 0.02
		for edge in [
			{"pos": pos + Vector3(0, y - pos.y, -half_z), "size": Vector3(size.x, 0.04, 0.15)},
			{"pos": pos + Vector3(0, y - pos.y, half_z), "size": Vector3(size.x, 0.04, 0.15)},
			{"pos": pos + Vector3(-half_x, y - pos.y, 0), "size": Vector3(0.15, 0.04, size.z)},
			{"pos": pos + Vector3(half_x, y - pos.y, 0), "size": Vector3(0.15, 0.04, size.z)},
		]:
			var strip := MeshInstance3D.new()
			var mesh := BoxMesh.new()
			mesh.size = edge["size"]
			strip.mesh = mesh
			strip.position = edge["pos"]
			strip.material_override = border_mat
			root.add_child(strip)


func _add_wayfinding() -> void:
	var root := Node3D.new()
	root.name = "Wayfinding"
	add_child(root)
	var hub := Vector3(0, 0.09, 0)

	_add_floor_arrow(root, hub, Vector3(-1, 0, 0), Color(0.55, 0.35, 0.2), "CARGO")
	_add_floor_arrow(root, hub, Vector3(1, 0, 0), Color(0.25, 0.45, 0.7), "OPS")
	_add_floor_arrow(root, hub, Vector3(0, 0, 1), Color(0.3, 0.65, 0.45), "BREAK")
	_add_floor_arrow(root, hub, Vector3(0.75, 0, -0.75).normalized(), Color(0.75, 0.3, 0.3), "DOCK")
	_add_floor_arrow(root, hub, Vector3(0, 0, -1), Color(0.95, 0.78, 0.15), "SHUTTLE")

	var start_label := Label3D.new()
	start_label.text = "▼ START HERE\nJob Kiosk"
	start_label.font_size = 20
	start_label.outline_size = 6
	start_label.modulate = Color(0.4, 0.85, 1.0)
	start_label.position = Vector3(-10, 2.6, -6)
	start_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	root.add_child(start_label)


func _add_floor_arrow(
	parent: Node3D,
	origin: Vector3,
	direction: Vector3,
	color: Color,
	label_text: String
) -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 0.35
	_blink_materials.append(mat)

	for step in 4:
		var chevron := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(0.9, 0.03, 0.45)
		chevron.mesh = mesh
		var offset := direction * (2.5 + step * 2.2)
		chevron.position = origin + offset
		parent.add_child(chevron)
		chevron.look_at(chevron.global_position + direction, Vector3.UP)
		chevron.material_override = mat

	var dir_label := Label3D.new()
	dir_label.text = label_text
	dir_label.font_size = 18
	dir_label.outline_size = 5
	dir_label.modulate = color.lightened(0.25)
	dir_label.position = origin + direction * 11.0 + Vector3(0, 0.15, 0)
	dir_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	parent.add_child(dir_label)


func _add_kiosk_beacon() -> void:
	var root := Node3D.new()
	root.name = "KioskBeacon"
	root.position = Vector3(-10, 0.1, -8)
	add_child(root)

	var ring := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = 1.6
	mesh.bottom_radius = 1.6
	mesh.height = 0.06
	ring.mesh = mesh
	var mat := _make_blink_material(Color(0.2, 0.75, 1.0))
	ring.material_override = mat
	root.add_child(ring)

	var pillar := MeshInstance3D.new()
	var pillar_mesh := CylinderMesh.new()
	pillar_mesh.top_radius = 0.08
	pillar_mesh.bottom_radius = 0.08
	pillar_mesh.height = 2.4
	pillar.mesh = pillar_mesh
	pillar.position = Vector3(0, 1.2, 0)
	var pillar_mat := StandardMaterial3D.new()
	pillar_mat.albedo_color = Color(0.2, 0.55, 0.85)
	pillar_mat.emission_enabled = true
	pillar_mat.emission = Color(0.15, 0.65, 0.95)
	pillar_mat.emission_energy_multiplier = 0.5
	pillar.material_override = pillar_mat
	root.add_child(pillar)


func _add_objective_markers() -> void:
	var markers := Node3D.new()
	markers.name = "ObjectiveMarkers"
	markers.set_script(load("res://scripts/levels/objective_markers.gd"))
	add_child(markers)


func _add_floor_grid() -> void:
	var root := Node3D.new()
	root.name = "FloorGrid"
	add_child(root)
	var line_mat := StandardMaterial3D.new()
	line_mat.albedo_color = Color(0.28, 0.32, 0.42)
	line_mat.emission_enabled = true
	line_mat.emission = Color(0.35, 0.4, 0.55)
	line_mat.emission_energy_multiplier = 0.08

	for x in range(-38, 40, 4):
		var strip := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(0.06, 0.02, 76)
		strip.mesh = mesh
		strip.position = Vector3(x, 0.04, 0)
		strip.material_override = line_mat
		root.add_child(strip)

	for z in range(-38, 40, 4):
		var strip := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(76, 0.02, 0.06)
		strip.mesh = mesh
		strip.position = Vector3(0, 0.04, z)
		strip.material_override = line_mat
		root.add_child(strip)


func _add_wall_trim() -> void:
	var root := Node3D.new()
	root.name = "WallTrim"
	add_child(root)
	var trim_mat := StandardMaterial3D.new()
	trim_mat.albedo_color = Color(0.35, 0.38, 0.48)
	trim_mat.metallic = 0.35
	trim_mat.roughness = 0.55

	for edge in [
		Vector3(0, 0.35, -39.4), Vector3(0, 0.35, 39.4),
		Vector3(-39.4, 0.35, 0), Vector3(39.4, 0.35, 0),
	]:
		var trim := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(78, 0.7, 0.35) if edge.z != 0 else Vector3(0.35, 0.7, 78)
		trim.mesh = mesh
		trim.position = edge
		trim.material_override = trim_mat
		root.add_child(trim)

	for corner in [Vector3(-39, 0.35, -39), Vector3(39, 0.35, -39), Vector3(-39, 0.35, 39), Vector3(39, 0.35, 39)]:
		_add_box(root, corner, Vector3(0.8, 0.75, 0.8), Color(0.4, 0.42, 0.52), 0.45)


func _add_hub_furniture() -> void:
	var root := Node3D.new()
	root.name = "HubFurniture"
	add_child(root)

	_add_box(root, Vector3(-6, 0.45, 2), Vector3(3.5, 0.9, 1.8), Color(0.28, 0.32, 0.42), 0.25)
	_add_box(root, Vector3(6, 0.45, 2), Vector3(3.5, 0.9, 1.8), Color(0.28, 0.32, 0.42), 0.25)
	for seat_pos in [Vector3(-6.8, 0.28, 3.2), Vector3(-5.2, 0.28, 3.2), Vector3(5.2, 0.28, 3.2), Vector3(6.8, 0.28, 3.2)]:
		_add_box(root, seat_pos, Vector3(0.65, 0.55, 0.65), Color(0.22, 0.48, 0.72), 0.15)

	_add_box(root, Vector3(0, 0.55, 6), Vector3(2.2, 1.1, 1.0), Color(0.18, 0.55, 0.42), 0.2)
	_add_cylinder(root, Vector3(0, 1.35, 6), 0.08, 0.6, Color(0.85, 0.88, 0.92), Vector3.ZERO)

	for monitor_pos in [Vector3(-12, 1.6, -4), Vector3(12, 1.6, -4)]:
		var screen := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(1.8, 1.1, 0.08)
		screen.mesh = mesh
		screen.position = monitor_pos
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.08, 0.12, 0.18)
		mat.emission_enabled = true
		mat.emission = Color(0.15, 0.55, 0.75)
		mat.emission_energy_multiplier = 0.35
		screen.material_override = mat
		root.add_child(screen)


func _add_corridor_details() -> void:
	var root := Node3D.new()
	root.name = "CorridorDetails"
	add_child(root)

	for pos in [Vector3(-14, 2.8, 0), Vector3(14, 2.8, 0), Vector3(0, 2.8, 14), Vector3(0, 2.8, -14)]:
		var lamp := OmniLight3D.new()
		lamp.position = pos
		lamp.light_color = Color(0.85, 0.92, 1.0)
		lamp.light_energy = 0.35
		lamp.omni_range = 10.0
		root.add_child(lamp)
		_spawn_scaled_model(
			root,
			MODEL_LIGHT,
			"env_light_oval_panel_01",
			pos + Vector3(0, -0.22, 0),
			0.0,
			0.6,
			true
		)

	for vent_pos in [Vector3(-39.5, 2.5, -10), Vector3(-39.5, 2.5, 10), Vector3(39.5, 2.5, -10), Vector3(39.5, 2.5, 10)]:
		var rot_y := PI * 0.5 if vent_pos.x > 0.0 else -PI * 0.5
		_spawn_scaled_model(
			root,
			MODEL_VENT_GRILLE,
			"prop_wall_janitor_vent_grille",
			vent_pos,
			rot_y,
			1.0,
			false
		)

	for pillar_pos in [Vector3(-20, 2.5, -20), Vector3(20, 2.5, -20), Vector3(-20, 2.5, 20), Vector3(20, 2.5, 20)]:
		_add_cylinder(root, pillar_pos, 0.25, 5.0, Color(0.38, 0.4, 0.48), Vector3.ZERO)


func _add_space_viewports() -> void:
	var root := Node3D.new()
	root.name = "SpaceViewports"
	add_child(root)

	for window in [
		{"pos": Vector3(0, 3.2, -39.7), "size": Vector3(12, 3.5, 0.2), "rot_y": 0.0},
		{"pos": Vector3(-39.7, 3.2, 0), "size": Vector3(0.2, 3.5, 12), "rot_y": PI * 0.5},
		{"pos": Vector3(39.7, 3.2, 0), "size": Vector3(0.2, 3.5, 12), "rot_y": -PI * 0.5},
	]:
		var frame := MeshInstance3D.new()
		var frame_mesh := BoxMesh.new()
		frame_mesh.size = window["size"] + Vector3(0.4, 0.4, 0.4)
		frame.mesh = frame_mesh
		frame.position = window["pos"]
		frame.rotation.y = window["rot_y"]
		var frame_mat := StandardMaterial3D.new()
		frame_mat.albedo_color = Color(0.25, 0.28, 0.35)
		frame_mat.metallic = 0.6
		frame.material_override = frame_mat
		root.add_child(frame)

		var glass := MeshInstance3D.new()
		var glass_mesh := BoxMesh.new()
		glass_mesh.size = window["size"]
		glass.mesh = glass_mesh
		glass.position = window["pos"]
		glass.rotation.y = window["rot_y"]
		var glass_mat := StandardMaterial3D.new()
		glass_mat.albedo_color = Color(0.05, 0.08, 0.18, 0.85)
		glass_mat.emission_enabled = true
		glass_mat.emission = Color(0.12, 0.18, 0.45)
		glass_mat.emission_energy_multiplier = 0.55
		glass_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		glass.material_override = glass_mat
		root.add_child(glass)

		var starfield := Label3D.new()
		starfield.text = "✦  ✧  ·  ✦\n— void beyond —\n✧  ·  ✦  ✧"
		starfield.font_size = 20
		starfield.outline_size = 4
		starfield.modulate = Color(0.75, 0.85, 1.0)
		var window_pos: Vector3 = window["pos"]
		var label_pos: Vector3 = window_pos
		if window["rot_y"] == 0.0:
			label_pos += Vector3(0.0, 0.0, -0.2)
		else:
			label_pos += Vector3(-0.2 if window_pos.x > 0.0 else 0.2, 0.0, 0.0)
		starfield.position = label_pos
		starfield.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		root.add_child(starfield)


func _make_blink_material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 0.35
	_blink_materials.append(mat)
	return mat


func _add_wall_cladding() -> void:
	var root := Node3D.new()
	root.name = "WallCladding"
	add_child(root)

	var segment_height := 2.0
	var y := 2.0
	for x in range(-38, 39, 4):
		_spawn_scaled_model(root, MODEL_WALL, "env_space_station_wall_04", Vector3(x, y, -39.35), 0.0, segment_height, false)
		_spawn_scaled_model(root, MODEL_WALL, "env_space_station_wall_04", Vector3(x, y, 39.35), PI, segment_height, false)
	for z in range(-38, 39, 4):
		_spawn_scaled_model(root, MODEL_WALL, "env_space_station_wall_04", Vector3(-39.35, y, z), PI * 0.5, segment_height, false)
		_spawn_scaled_model(root, MODEL_WALL, "env_space_station_wall_04", Vector3(39.35, y, z), -PI * 0.5, segment_height, false)


func _add_sign_label(parent: Node3D, text: String, offset: Vector3, font_size: int) -> void:
	var label := Label3D.new()
	label.text = text
	label.font_size = font_size
	label.outline_size = 6
	label.modulate = Color(0.98, 0.96, 0.9)
	label.position = offset
	label.billboard = BaseMaterial3D.BILLBOARD_DISABLED
	parent.add_child(label)


func _add_power_hour_visuals() -> void:
	var root := Node3D.new()
	root.name = "PowerHourVisuals"
	add_child(root)
	_spawn_scaled_model(
		root,
		MODEL_BREAKER_PANEL,
		"env_breaker_panel_01",
		Vector3(14, 1.0, 7.2),
		PI,
		1.0,
		false
	)


func _add_trust_fall_visuals() -> void:
	var root := Node3D.new()
	root.name = "TrustFallVisuals"
	add_child(root)
	_spawn_scaled_model(
		root,
		MODEL_SAFETY_MAT,
		"safety_mat_floor_pad_01",
		Vector3(4, 0.02, 10),
		0.0,
		-1.0,
		true,
		2.0
	)


func _spawn_scaled_model(
	parent: Node3D,
	scene: PackedScene,
	asset_key: String,
	pos: Vector3,
	rot_y: float,
	target_height: float,
	snap_bottom: bool,
	target_width: float = -1.0
) -> Node3D:
	var inst := scene.instantiate() as Node3D
	parent.add_child(inst)
	inst.rotation.y = rot_y

	var aabb := _local_mesh_aabb(inst)
	if aabb.size.length_squared() > 0.0001:
		var uniform_scale := ImmersiveStudioMaterial.get_default_scale(
			asset_key,
			aabb,
			target_height,
			target_width
		)
		inst.scale = Vector3.ONE * uniform_scale

		var scaled_pos := aabb.position * inst.scale
		var scaled_size := aabb.size * inst.scale
		var anchor := Vector3(
			scaled_pos.x + scaled_size.x * 0.5,
			scaled_pos.y if snap_bottom else scaled_pos.y + scaled_size.y * 0.5,
			scaled_pos.z + scaled_size.z * 0.5
		)
		inst.position = pos - anchor

	return inst


func _local_mesh_aabb(node: Node) -> AABB:
	var result := AABB()
	var first := true
	for child in node.find_children("*", "MeshInstance3D", true, false):
		var mesh_inst := child as MeshInstance3D
		if mesh_inst.mesh == null:
			continue
		var mesh_aabb := mesh_inst.mesh.get_aabb()
		var corners: Array[Vector3] = [
			mesh_aabb.position,
			mesh_aabb.position + Vector3(mesh_aabb.size.x, 0.0, 0.0),
			mesh_aabb.position + Vector3(0.0, mesh_aabb.size.y, 0.0),
			mesh_aabb.position + Vector3(0.0, 0.0, mesh_aabb.size.z),
			mesh_aabb.position + Vector3(mesh_aabb.size.x, mesh_aabb.size.y, 0.0),
			mesh_aabb.position + Vector3(mesh_aabb.size.x, 0.0, mesh_aabb.size.z),
			mesh_aabb.position + Vector3(0.0, mesh_aabb.size.y, mesh_aabb.size.z),
			mesh_aabb.position + mesh_aabb.size,
		]
		for corner in corners:
			var local_corner := mesh_inst.transform * corner
			if first:
				result = AABB(local_corner, Vector3.ZERO)
				first = false
			else:
				result = result.expand(local_corner)
	return result
