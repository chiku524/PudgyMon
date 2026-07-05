extends CharacterBody3D

## Third-person cartoon movement for ShipHappens Phase 0.

const MOVE_SPEED := 6.0
const SPRINT_SPEED := 9.0
const JUMP_VELOCITY := 7.5
const ROTATION_LERP := 12.0
const PUSH_FORCE := 4.0

@export var player_name: String = "Crew Member"
@export var body_color: Color = Color(0.95, 0.75, 0.2)

@onready var camera_rig: Node3D = $CameraRig
@onready var spring_arm: SpringArm3D = $CameraRig/SpringArm3D
@onready var mesh_root: Node3D = $Visuals
@onready var body_mesh: MeshInstance3D = $Visuals/Body
@onready var head_mesh: MeshInstance3D = $Visuals/Head
@onready var name_label: Label3D = $Visuals/NameLabel
@onready var push_area: Area3D = $PushArea

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var camera_yaw: float = 0.0


func _enter_tree() -> void:
	set_multiplayer_authority(name.to_int())


func _ready() -> void:
	_apply_colors()
	_update_name_label()
	camera_yaw = rotation.y
	if not is_multiplayer_authority():
		spring_arm.get_node("Camera3D").current = false
		set_process_input(false)


func _physics_process(delta: float) -> void:
	if not is_multiplayer_authority():
		return

	if not is_on_floor():
		velocity.y -= gravity * delta

	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY

	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var speed := SPRINT_SPEED if Input.is_action_pressed("interact") else MOVE_SPEED
	var cam_basis := camera_rig.global_transform.basis
	var direction := (cam_basis * Vector3(input_dir.x, 0.0, input_dir.y)).normalized()
	direction.y = 0.0

	if direction.length_squared() > 0.001:
		velocity.x = direction.x * speed
		velocity.z = direction.z * speed
		var target_rotation := atan2(direction.x, direction.z)
		rotation.y = lerp_angle(rotation.y, target_rotation, ROTATION_LERP * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, speed)
		velocity.z = move_toward(velocity.z, 0.0, speed)

	move_and_slide()
	_try_push_props()


func _input(event: InputEvent) -> void:
	if not is_multiplayer_authority():
		return

	if event.is_action_pressed("camera_left"):
		camera_yaw -= deg_to_rad(3.0)
	elif event.is_action_pressed("camera_right"):
		camera_yaw += deg_to_rad(3.0)

	camera_rig.rotation.y = camera_yaw


func set_display_name(new_name: String) -> void:
	player_name = new_name
	_update_name_label()


func set_player_color(color: Color) -> void:
	body_color = color
	_apply_colors()


func _apply_colors() -> void:
	var body_mat := StandardMaterial3D.new()
	body_mat.albedo_color = body_color
	body_mesh.material_override = body_mat

	var head_mat := StandardMaterial3D.new()
	head_mat.albedo_color = body_color.lightened(0.25)
	head_mesh.material_override = head_mat


func _update_name_label() -> void:
	name_label.text = player_name


func _try_push_props() -> void:
	for body in push_area.get_overlapping_bodies():
		if body is RigidBody3D and body.has_method("apply_player_push"):
			var push_dir := -global_transform.basis.z
			push_dir.y = 0.0
			body.apply_player_push(push_dir.normalized() * PUSH_FORCE)
