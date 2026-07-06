extends CharacterBody3D

## Third-person cartoon movement with bonk ragdoll, carry, and interact.

enum PlayerState { NORMAL, BONKED, DIZZY }

const MOVE_SPEED := 6.0
const SPRINT_SPEED := 9.0
const CARRY_SPEED := 4.5
const JUMP_VELOCITY := 7.5
const ROTATION_LERP := 12.0
const PUSH_FORCE := 4.0
const BONK_FALL_SPEED := 10.0
const BONK_WALL_SPEED := 8.5
const BONK_DURATION := 1.5
const INTERACT_RANGE := 2.2
const MOUSE_SENSITIVITY := 0.0025
const MIN_CAMERA_PITCH := deg_to_rad(-35.0)
const MAX_CAMERA_PITCH := deg_to_rad(55.0)
const IDLE_BOB_HEIGHT := 0.035
const IDLE_BOB_SPEED := 2.2
const WALK_BOB_HEIGHT := 0.07
const WALK_BOB_SPEED := 9.0
const ARM_SWING_WALK := 0.75
const ARM_SWING_IDLE := 0.06

@export var player_name: String = "Crew Member"
@export var body_color: Color = Color(0.95, 0.75, 0.2)

@onready var camera_rig: Node3D = $CameraRig
@onready var spring_arm: SpringArm3D = $CameraRig/SpringArm3D
@onready var mesh_root: Node3D = $Visuals
@onready var body_mesh: MeshInstance3D = $Visuals/Body
@onready var head_mesh: MeshInstance3D = $Visuals/Head
@onready var name_label: Label3D = $Visuals/NameLabel
@onready var bonk_stars: Label3D = $Visuals/BonkStars
@onready var carry_anchor: Marker3D = $Visuals/CarryAnchor
@onready var push_area: Area3D = $PushArea
@onready var interact_area: Area3D = $InteractArea
@onready var prompt_label: Label3D = $Visuals/PromptLabel
@onready var dunce_hat: MeshInstance3D = $Visuals/DunceHat
@onready var arm_l: MeshInstance3D = $Visuals/ArmL
@onready var arm_r: MeshInstance3D = $Visuals/ArmR

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var camera_yaw: float = 0.0
var camera_pitch: float = -0.35
var player_state: PlayerState = PlayerState.NORMAL
var state_timer: float = 0.0
var carried_item: CarryableItem = null
var has_mop: bool = false
var _was_in_air: bool = false
var _previous_vertical_velocity: float = 0.0
var _ragdoll_spin: Vector3 = Vector3.ZERO
var _visual_base_rotation: Vector3 = Vector3.ZERO
var _bonk_total_duration: float = 1.5
var _anim_time: float = 0.0
var _last_anim_position: Vector3 = Vector3.ZERO
var _arm_l_base_rotation: Vector3 = Vector3.ZERO
var _arm_r_base_rotation: Vector3 = Vector3.ZERO
var _head_base_rotation: Vector3 = Vector3.ZERO


func _enter_tree() -> void:
	set_multiplayer_authority(name.to_int())


func _ready() -> void:
	add_to_group("players")
	_apply_colors()
	_update_name_label()
	bonk_stars.visible = false
	prompt_label.visible = false
	dunce_hat.visible = GameState.is_written_up(int(name))
	camera_yaw = rotation.y
	camera_pitch = spring_arm.rotation.x
	_apply_camera_rotation()
	_visual_base_rotation = mesh_root.rotation
	if arm_l:
		_arm_l_base_rotation = arm_l.rotation
	if arm_r:
		_arm_r_base_rotation = arm_r.rotation
	if head_mesh:
		_head_base_rotation = head_mesh.rotation
	_last_anim_position = global_position
	GameState.written_up_changed.connect(_on_written_up_changed)
	RoundManager.round_phase_changed.connect(_on_round_phase_changed)
	if is_multiplayer_authority():
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	if not is_multiplayer_authority():
		spring_arm.get_node("Camera3D").current = false
		set_process_input(false)


func _process(delta: float) -> void:
	_update_character_animation(delta)


func _update_character_animation(delta: float) -> void:
	if player_state != PlayerState.NORMAL:
		return

	_anim_time += delta
	var move_speed := Vector2(velocity.x, velocity.z).length()
	if not is_multiplayer_authority():
		move_speed = global_position.distance_to(_last_anim_position) / maxf(delta, 0.001)
	_last_anim_position = global_position

	var moving := move_speed > 0.35
	var bob_speed := WALK_BOB_SPEED if moving else IDLE_BOB_SPEED
	var bob_height := WALK_BOB_HEIGHT if moving else IDLE_BOB_HEIGHT
	# Half-wave bob keeps feet above the floor (never dips below rest pose).
	var bob_phase := (sin(_anim_time * bob_speed) * 0.5 + 0.5)
	mesh_root.position.y = bob_phase * bob_height

	if arm_l and arm_r:
		var swing_amount := ARM_SWING_WALK if moving else ARM_SWING_IDLE
		var swing := sin(_anim_time * bob_speed) * swing_amount
		arm_l.rotation = _arm_l_base_rotation + Vector3(swing, 0.0, 0.12)
		arm_r.rotation = _arm_r_base_rotation + Vector3(-swing, 0.0, -0.12)

	if head_mesh:
		head_mesh.rotation = _head_base_rotation + Vector3(
			sin(_anim_time * (bob_speed * 0.5)) * 0.04,
			0.0,
			sin(_anim_time * (bob_speed * 0.35)) * 0.03
		)


func _physics_process(delta: float) -> void:
	if not is_multiplayer_authority():
		return

	_update_interact_prompt()

	if GameState.round_phase == GameState.RoundPhase.MEETING or GameState.round_phase == GameState.RoundPhase.REVIEW:
		velocity = Vector3.ZERO
		move_and_slide()
		return

	if player_state != PlayerState.NORMAL:
		state_timer -= delta
		velocity = Vector3.ZERO
		mesh_root.rotation = _visual_base_rotation + _ragdoll_spin * (1.0 - state_timer / _bonk_total_duration)
		if state_timer <= 0.0:
			_recover_from_bonk()
		move_and_slide()
		return

	if Input.is_action_just_pressed("interact"):
		_try_interact()

	if not is_on_floor():
		velocity.y -= gravity * delta

	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY

	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var speed := _get_move_speed()
	var cam_forward := Vector3(-sin(camera_yaw), 0.0, -cos(camera_yaw))
	var cam_right := Vector3(cos(camera_yaw), 0.0, -sin(camera_yaw))
	var direction := cam_right * input_dir.x + cam_forward * (-input_dir.y)

	if direction.length_squared() > 0.001:
		direction = direction.normalized()
		velocity.x = direction.x * speed
		velocity.z = direction.z * speed
		var target_rotation := atan2(direction.x, direction.z)
		mesh_root.rotation.y = lerp_angle(mesh_root.rotation.y, target_rotation, ROTATION_LERP * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, speed)
		velocity.z = move_toward(velocity.z, 0.0, speed)

	_previous_vertical_velocity = velocity.y
	_was_in_air = not is_on_floor()
	move_and_slide()
	_check_bonk_triggers()
	_try_push_props()


func _input(event: InputEvent) -> void:
	if not is_multiplayer_authority():
		return

	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		camera_yaw -= event.relative.x * MOUSE_SENSITIVITY
		camera_pitch = clampf(
			camera_pitch - event.relative.y * MOUSE_SENSITIVITY,
			MIN_CAMERA_PITCH,
			MAX_CAMERA_PITCH
		)
		_apply_camera_rotation()

	if event.is_action_pressed("ui_cancel"):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _apply_camera_rotation() -> void:
	camera_rig.rotation.y = camera_yaw
	spring_arm.rotation.x = camera_pitch


func _get_move_speed() -> float:
	if carried_item != null:
		return CARRY_SPEED
	if Input.is_action_pressed("sprint"):
		return SPRINT_SPEED
	return MOVE_SPEED


func set_display_name(new_name: String) -> void:
	player_name = new_name
	if is_node_ready():
		_update_name_label()


func set_player_color(color: Color) -> void:
	body_color = color
	if is_node_ready():
		_apply_colors()


func can_pickup_item() -> bool:
	return player_state == PlayerState.NORMAL and carried_item == null


func is_carrying_forms() -> bool:
	return carried_item != null and carried_item.item_id == "form"


func is_carrying_contraband() -> bool:
	return carried_item != null and StowawaySystem.is_smuggle_item(carried_item.item_id)


func is_carrying_hot_dog() -> bool:
	return is_carrying_contraband()


func has_mop_equipped() -> bool:
	return has_mop


func equip_mop() -> void:
	has_mop = true


func consume_contraband() -> bool:
	if not is_carrying_contraband():
		return false
	if carried_item != null:
		carried_item.queue_free()
	carried_item = null
	if multiplayer.is_server():
		_sync_carryable_consumed.rpc()
	return true


func consume_hot_dog() -> bool:
	return consume_contraband()


func pickup_item(item: CarryableItem) -> void:
	if not can_pickup_item():
		return
	carried_item = item
	item.pickup_by(self, carry_anchor)
	if is_multiplayer_authority() and not multiplayer.is_server():
		_sync_pickup.rpc_id(1, item.name)
	elif multiplayer.is_server():
		pass


func consume_carried_form() -> bool:
	if not is_carrying_forms():
		return false
	if carried_item != null:
		carried_item.queue_free()
	carried_item = null
	if multiplayer.is_server():
		_sync_carryable_consumed.rpc()
	return true


func apply_launch(launch: Vector3) -> void:
	if player_state != PlayerState.NORMAL:
		return
	velocity = launch


func trigger_bonk(duration: float = BONK_DURATION) -> void:
	if player_state != PlayerState.NORMAL:
		return
	_apply_bonk(duration, PlayerState.BONKED)


func trigger_dizzy(duration: float = 3.0) -> void:
	_apply_bonk(duration, PlayerState.DIZZY)


func _apply_bonk(duration: float, state: PlayerState) -> void:
	if is_multiplayer_authority():
		_enter_bonk_state(state, duration)
	if multiplayer.is_server():
		_sync_bonk.rpc(duration, state)
	elif is_multiplayer_authority():
		_notify_bonk.rpc_id(1, duration, state)


func _enter_bonk_state(state: PlayerState, duration: float) -> void:
	player_state = state
	state_timer = duration
	_bonk_total_duration = maxf(duration, 0.1)
	velocity = Vector3.ZERO
	mesh_root.position = Vector3.ZERO
	_drop_carried_item()
	bonk_stars.visible = true
	bonk_stars.text = "★ BONK ★" if state == PlayerState.BONKED else "★ DIZZY ★"
	if is_multiplayer_authority():
		StatsTracker.record(int(name), "bonks", 1)
		StatsTracker.record_global("bonks", 1)
	_ragdoll_spin = Vector3(
		randf_range(-TAU, TAU),
		randf_range(-TAU, TAU),
		randf_range(-TAU, TAU)
	)


func _recover_from_bonk() -> void:
	player_state = PlayerState.NORMAL
	state_timer = 0.0
	mesh_root.rotation = _visual_base_rotation
	mesh_root.position = Vector3.ZERO
	if arm_l:
		arm_l.rotation = _arm_l_base_rotation
	if arm_r:
		arm_r.rotation = _arm_r_base_rotation
	if head_mesh:
		head_mesh.rotation = _head_base_rotation
	bonk_stars.visible = false


func _check_bonk_triggers() -> void:
	if is_on_floor() and _was_in_air and _previous_vertical_velocity < -BONK_FALL_SPEED:
		trigger_bonk()
		return

	if get_slide_collision_count() == 0:
		return

	var horizontal_speed := Vector2(velocity.x, velocity.z).length()
	if horizontal_speed >= BONK_WALL_SPEED:
		for index in get_slide_collision_count():
			var collision := get_slide_collision(index)
			var collider: Object = collision.get_collider()
			if collider != null and collider.is_in_group("bonk_pad"):
				continue
			trigger_bonk(1.2)
			return


func _try_interact() -> void:
	if player_state != PlayerState.NORMAL:
		return

	var target := _get_best_interactable()
	if target != null and target.can_interact(self):
		target.interact(self)
	elif carried_item != null:
		_drop_carried_item()


func _get_best_interactable() -> Node:
	var best: Node = null
	var best_distance := INTERACT_RANGE
	for area in interact_area.get_overlapping_areas():
		if not area.is_in_group("interactable"):
			continue
		if not area.has_method("can_interact") or not area.can_interact(self):
			continue
		var distance := global_position.distance_to(area.global_position)
		if distance < best_distance:
			best_distance = distance
			best = area
	return best


func _update_interact_prompt() -> void:
	if not is_multiplayer_authority():
		return

	if player_state != PlayerState.NORMAL:
		prompt_label.visible = false
		return

	var target := _get_best_interactable()
	if target != null and target.has_method("get_prompt"):
		prompt_label.text = "[F] %s" % target.get_prompt(self)
		prompt_label.visible = true
	elif carried_item != null:
		prompt_label.text = "[F] Drop item"
		prompt_label.visible = true
	else:
		prompt_label.visible = false


func _drop_carried_item() -> void:
	if carried_item == null:
		return
	var drop_position := global_position + mesh_root.global_transform.basis.z * 0.8 + Vector3.UP * 0.5
	carried_item.drop(drop_position)
	carried_item = null


func _apply_colors() -> void:
	if body_mesh == null or head_mesh == null:
		return

	var body_mat := StandardMaterial3D.new()
	body_mat.albedo_color = body_color
	body_mat.roughness = 0.75
	_set_mesh_material(body_mesh, body_mat)
	_set_mesh_material(_visual_mesh("ArmL"), body_mat)
	_set_mesh_material(_visual_mesh("ArmR"), body_mat)
	_set_mesh_material(_visual_mesh("LegL"), body_mat)
	_set_mesh_material(_visual_mesh("LegR"), body_mat)

	var head_mat := StandardMaterial3D.new()
	head_mat.albedo_color = body_color.lightened(0.25)
	head_mat.roughness = 0.65
	_set_mesh_material(head_mesh, head_mat)

	var dark_mat := StandardMaterial3D.new()
	dark_mat.albedo_color = body_color.darkened(0.55)
	dark_mat.roughness = 0.55
	_set_mesh_material(_visual_mesh("BootL"), dark_mat)
	_set_mesh_material(_visual_mesh("BootR"), dark_mat)
	_set_mesh_material(_visual_mesh("Backpack"), dark_mat)
	_set_mesh_material(_visual_mesh("EyeL"), dark_mat)
	_set_mesh_material(_visual_mesh("EyeR"), dark_mat)

	var visor_mat := StandardMaterial3D.new()
	visor_mat.albedo_color = body_color.lerp(Color(0.2, 0.45, 0.85), 0.65)
	visor_mat.metallic = 0.35
	visor_mat.roughness = 0.25
	_set_mesh_material(_visual_mesh("Visor"), visor_mat)

	var badge_mat := StandardMaterial3D.new()
	badge_mat.albedo_color = body_color.lightened(0.15)
	badge_mat.emission_enabled = true
	badge_mat.emission = body_color
	badge_mat.emission_energy_multiplier = 0.2
	_set_mesh_material(_visual_mesh("Badge"), badge_mat)


func _visual_mesh(node_name: String) -> MeshInstance3D:
	return mesh_root.get_node_or_null(node_name) as MeshInstance3D


func _set_mesh_material(mesh: MeshInstance3D, material: StandardMaterial3D) -> void:
	if mesh != null:
		mesh.material_override = material


func _update_name_label() -> void:
	if name_label == null:
		return
	name_label.text = player_name


func _try_push_props() -> void:
	for body in push_area.get_overlapping_bodies():
		if body is RigidBody3D and body.has_method("apply_player_push"):
			var push_dir := mesh_root.global_transform.basis.z
			push_dir.y = 0.0
			body.apply_player_push(push_dir.normalized() * PUSH_FORCE)


@rpc("any_peer", "call_remote", "reliable")
func _sync_pickup(item_name: String) -> void:
	if not multiplayer.is_server():
		return
	var peer_id := multiplayer.get_remote_sender_id()
	var player := _find_player_node(peer_id)
	var item: Node = get_tree().current_scene.get_node_or_null(item_name)
	if player == null or item == null or not item is CarryableItem:
		return
	player.carried_item = item
	item.pickup_by(player, player.carry_anchor)


func _find_player_node(peer_id: int) -> CharacterBody3D:
	for node in get_tree().get_nodes_in_group("players"):
		if node.name == str(peer_id):
			return node
	return null


@rpc("authority", "call_remote", "reliable")
func _sync_carryable_consumed() -> void:
	if carried_item != null:
		carried_item.queue_free()
	carried_item = null


@rpc("any_peer", "call_remote", "reliable")
func _notify_bonk(duration: float, state: PlayerState) -> void:
	if not multiplayer.is_server():
		return
	_sync_bonk.rpc(duration, state)


@rpc("authority", "call_remote", "reliable")
func _sync_bonk(duration: float, state: PlayerState) -> void:
	if is_multiplayer_authority():
		return
	_enter_bonk_state(state, duration)


func _on_written_up_changed(peer_id: int, active: bool) -> void:
	if int(name) != peer_id:
		return
	dunce_hat.visible = active


func _on_round_phase_changed(phase: GameState.RoundPhase) -> void:
	if phase == GameState.RoundPhase.REVIEW:
		has_mop = false
		if is_multiplayer_authority():
			velocity = Vector3.ZERO
	if is_multiplayer_authority():
		if phase == GameState.RoundPhase.MEETING or phase == GameState.RoundPhase.REVIEW:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		elif phase == GameState.RoundPhase.PLAYING or phase == GameState.RoundPhase.EXTRACTION:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
