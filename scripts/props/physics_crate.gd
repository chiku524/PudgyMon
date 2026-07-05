extends RigidBody3D

## Physics crate for Phase 0 push/sync testing.

const SYNC_INTERVAL := 0.05

var _sync_timer: float = 0.0


func _ready() -> void:
	add_to_group("synced_props")
	if not multiplayer.is_server():
		freeze = true


func apply_player_push(force: Vector3) -> void:
	if not multiplayer.is_server():
		return
	apply_central_impulse(force)


func _physics_process(delta: float) -> void:
	if not multiplayer.is_server():
		return

	_sync_timer -= delta
	if _sync_timer <= 0.0:
		_sync_timer = SYNC_INTERVAL
		_rpc_sync_state.rpc(global_position, global_rotation, linear_velocity)


@rpc("authority", "unreliable")
func _rpc_sync_state(pos: Vector3, rot: Vector3, vel: Vector3) -> void:
	if multiplayer.is_server():
		return
	global_position = pos
	global_rotation = rot
	linear_velocity = vel
