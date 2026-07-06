extends Node3D

## Pulsing markers at job stations, power-hour hint, and shuttle extraction trail.

const MARKER_SITES: Array[Dictionary] = [
	{"job_id": "paperwork_avalanche", "pos": Vector3(-10, 0, -8)},
	{"job_id": "power_hour", "pos": Vector3(12, 0, 4)},
	{"job_id": "mop_the_future", "pos": Vector3(-14, 0, 4)},
	{"job_id": "manifest_lies", "pos": Vector3(14, 0, -4)},
	{"job_id": "crane_of_regret", "pos": Vector3(-28, 0, -8)},
	{"job_id": "coolant_gargle", "pos": Vector3(28, 0, 6)},
	{"job_id": "dish_go_brr", "pos": Vector3(32, 0, -6)},
	{"job_id": "trust_fall", "pos": Vector3(4, 3, 10)},
	{"job_id": "vending_restock", "pos": Vector3(-4, 0, 14)},
	{"job_id": "duct_tape", "pos": Vector3(32, 0, -24)},
]

const COLOR_AVAILABLE := Color(0.25, 0.95, 0.55)
const COLOR_ACTIVE := Color(1.0, 0.82, 0.15)
const COLOR_SHUTTLE := Color(0.95, 0.78, 0.12)

var _markers: Dictionary = {}
var _marker_materials: Array[StandardMaterial3D] = []
var _extraction_root: Node3D = null
var _extraction_materials: Array[StandardMaterial3D] = []
var _power_hint_label: Label3D = null
var _anim_time: float = 0.0


func _ready() -> void:
	_spawn_job_markers()
	_spawn_power_hour_hint()
	_spawn_extraction_trail()
	_refresh_markers()
	JobSystem.job_board_changed.connect(func(_a, _b): _refresh_markers())
	JobSystem.job_completed.connect(func(_id): _refresh_markers())
	GameState.jobs_progress_changed.connect(func(_c, _r): _refresh_extraction_trail())
	RoundManager.shuttle_unlocked.connect(func(_s): _refresh_extraction_trail())
	RoundManager.round_phase_changed.connect(func(_p): _refresh_extraction_trail())


func _process(delta: float) -> void:
	_anim_time += delta
	var pulse := 0.35 + maxf(sin(_anim_time * 3.5), 0.0) * 0.65
	for mat in _marker_materials:
		mat.emission_energy_multiplier = pulse
	var shuttle_pulse := 0.4 + maxf(sin(_anim_time * 5.0), 0.0) * 0.9
	for mat in _extraction_materials:
		mat.emission_energy_multiplier = shuttle_pulse


func _spawn_job_markers() -> void:
	var root := Node3D.new()
	root.name = "JobMarkers"
	add_child(root)

	for site in MARKER_SITES:
		var job_id: String = site["job_id"]
		var pos: Vector3 = site["pos"]
		var marker := Node3D.new()
		marker.name = job_id
		marker.position = pos
		root.add_child(marker)

		var ring := MeshInstance3D.new()
		var ring_mesh := CylinderMesh.new()
		ring_mesh.top_radius = 1.1
		ring_mesh.bottom_radius = 1.1
		ring_mesh.height = 0.05
		ring.mesh = ring_mesh
		ring.position.y = 0.12
		var ring_mat := _make_marker_material(COLOR_AVAILABLE)
		ring.material_override = ring_mat
		marker.add_child(ring)

		var beam := MeshInstance3D.new()
		var beam_mesh := CylinderMesh.new()
		beam_mesh.top_radius = 0.06
		beam_mesh.bottom_radius = 0.06
		beam_mesh.height = 2.8
		beam.mesh = beam_mesh
		beam.position.y = 1.5
		var beam_mat := _make_marker_material(COLOR_AVAILABLE)
		beam_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		beam_mat.albedo_color.a = 0.35
		beam.material_override = beam_mat
		marker.add_child(beam)

		var floater := Label3D.new()
		floater.name = "Floater"
		floater.font_size = 16
		floater.outline_size = 5
		floater.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		floater.position = Vector3(0, 3.2, 0)
		marker.add_child(floater)

		_markers[job_id] = {
			"root": marker,
			"ring_mat": ring_mat,
			"beam_mat": beam_mat,
			"floater": floater,
		}


func _spawn_power_hour_hint() -> void:
	var panel_root := Node3D.new()
	panel_root.name = "PowerHourHint"
	panel_root.position = Vector3(14, 0, 6)
	add_child(panel_root)

	_add_hint_panel(panel_root, Vector3(0, 2.4, 0), Vector3(4.5, 1.6, 0.12))

	_power_hint_label = Label3D.new()
	_power_hint_label.font_size = 18
	_power_hint_label.outline_size = 5
	_power_hint_label.position = Vector3(0, 2.4, -0.1)
	_power_hint_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	panel_root.add_child(_power_hint_label)
	_refresh_power_hour_hint()


func _spawn_extraction_trail() -> void:
	_extraction_root = Node3D.new()
	_extraction_root.name = "ExtractionTrail"
	add_child(_extraction_root)

	var start := Vector3(0, 0.11, -4)
	var direction := Vector3(0, 0, -1)
	for step in 8:
		var chevron := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(1.4, 0.04, 0.7)
		chevron.mesh = mesh
		var mat := _make_marker_material(COLOR_SHUTTLE)
		_extraction_materials.append(mat)
		chevron.material_override = mat
		var offset := direction * (3.0 + step * 3.5)
		chevron.position = start + offset
		_extraction_root.add_child(chevron)
		chevron.look_at(chevron.global_position + direction, Vector3.UP)

	var evac_sign := Label3D.new()
	evac_sign.text = "▲ SHUTTLE EVAC"
	evac_sign.font_size = 24
	evac_sign.outline_size = 8
	evac_sign.modulate = COLOR_SHUTTLE
	evac_sign.position = Vector3(0, 0.2, -18)
	evac_sign.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_extraction_root.add_child(evac_sign)

	_extraction_root.visible = false


func _refresh_markers() -> void:
	for site in MARKER_SITES:
		var job_id: String = site["job_id"]
		if not _markers.has(job_id):
			continue
		var data: Dictionary = _markers[job_id]
		var marker_root: Node3D = data["root"]
		if JobSystem.is_job_complete(job_id):
			marker_root.visible = false
			continue

		marker_root.visible = true
		var active := JobSystem.is_active(job_id)
		var color := COLOR_ACTIVE if active else COLOR_AVAILABLE
		var ring_mat: StandardMaterial3D = data["ring_mat"]
		var beam_mat: StandardMaterial3D = data["beam_mat"]
		ring_mat.albedo_color = color
		ring_mat.emission = color
		beam_mat.albedo_color = color
		beam_mat.emission = color
		beam_mat.albedo_color.a = 0.5 if active else 0.3

		var floater: Label3D = data["floater"]
		var job_name: String = JobSystem.JOB_NAMES.get(job_id, "Job")
		if active:
			floater.text = "▲ %s\nIn progress" % job_name
			floater.modulate = COLOR_ACTIVE
		else:
			floater.text = "○ %s\nPress F here" % job_name
			floater.modulate = COLOR_AVAILABLE

	_refresh_power_hour_hint()


func _refresh_power_hour_hint() -> void:
	if _power_hint_label == null:
		return
	if JobSystem.is_job_complete(JobSystem.POWER_HOUR_JOB_ID):
		_power_hint_label.text = "POWER HOUR\n✓ Complete"
	elif JobSystem.is_active(JobSystem.POWER_HOUR_JOB_ID):
		_power_hint_label.text = "POWER HOUR\nFlip order:\n1 → 3 → 2 → 4"
	else:
		_power_hint_label.text = "POWER HOUR\nStart at any breaker\nSequence shown when active"


func _refresh_extraction_trail() -> void:
	if _extraction_root == null:
		return
	var trail_visible := GameState.jobs_completed >= GameState.jobs_required
	trail_visible = trail_visible or RoundManager.shuttle_active
	trail_visible = trail_visible or GameState.round_phase == GameState.RoundPhase.EXTRACTION
	_extraction_root.visible = trail_visible


func _make_marker_material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 0.45
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_marker_materials.append(mat)
	return mat


func _add_hint_panel(parent: Node3D, pos: Vector3, size: Vector3) -> void:
	var panel := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	panel.mesh = mesh
	panel.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.12, 0.14, 0.2)
	mat.emission_enabled = true
	mat.emission = Color(0.2, 0.35, 0.55)
	mat.emission_energy_multiplier = 0.15
	panel.material_override = mat
	parent.add_child(panel)
