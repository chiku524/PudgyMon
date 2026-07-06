extends Interactable

## Starts Power Hour and tracks breaker flips.

@export var breaker_index: int = 0

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	prompt_text = "Flip breaker %d" % (breaker_index + 1)
	JobSystem.job_board_changed.connect(func(_a, _b): _refresh_label())
	_refresh_label()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.power_hour_complete:
		return "Power restored"
	if not JobSystem.power_hour_active:
		return "Start Power Hour"
	return "Flip breaker %d" % (breaker_index + 1)


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.power_hour_complete


func interact(player: Node3D) -> void:
	if JobSystem.power_hour_complete:
		return
	if not JobSystem.power_hour_active:
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.POWER_HOUR_JOB_ID)
		else:
			_request_start.rpc_id(1)
		return
	if multiplayer.is_server():
		_handle_breaker(player)
	else:
		_request_breaker.rpc_id(1)


func _handle_breaker(player: Node3D) -> void:
	var result: Dictionary = JobSystem.try_power_hour_breaker(breaker_index)
	if result.get("zap", false) and player.has_method("trigger_bonk"):
		player.trigger_bonk(2.0)
	_refresh_label()


func _refresh_label() -> void:
	if JobSystem.power_hour_complete:
		label.text = "BREAKER %d\nOK" % (breaker_index + 1)
	elif JobSystem.power_hour_active:
		label.text = "BREAKER %d\nStep %d" % [breaker_index + 1, JobSystem.power_hour_step + 1]
	else:
		label.text = "BREAKER %d\nIdle" % (breaker_index + 1)


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.POWER_HOUR_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_breaker() -> void:
	if not multiplayer.is_server():
		return
	var peer_id := multiplayer.get_remote_sender_id()
	var player := _find_player(peer_id)
	if player != null:
		_handle_breaker(player)


func _find_player(peer_id: int) -> Node3D:
	for node in get_tree().get_nodes_in_group("players"):
		if node.name == str(peer_id):
			return node
	return null
