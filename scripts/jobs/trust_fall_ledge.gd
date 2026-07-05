extends Interactable

## Trust fall ledge — volunteer steps off to progress job.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	JobSystem.job_board_changed.connect(func _a, _b: _refresh())
	_refresh()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.is_job_complete(JobSystem.TRUST_FALL_JOB_ID):
		return "Certified"
	if not JobSystem.is_active(JobSystem.TRUST_FALL_JOB_ID):
		return "Start Trust Fall"
	return "Trust fall (step forward)"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.is_job_complete(JobSystem.TRUST_FALL_JOB_ID)


func interact(player: Node3D) -> void:
	if not can_interact(player):
		return
	if not JobSystem.is_active(JobSystem.TRUST_FALL_JOB_ID):
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.TRUST_FALL_JOB_ID)
		else:
			_request_start.rpc_id(1)
		return
	if player.has_method("apply_launch"):
		player.apply_launch(Vector3(0, 4, -3))
	if multiplayer.is_server():
		JobSystem.add_progress(JobSystem.TRUST_FALL_JOB_ID, 1)
	else:
		_request_progress.rpc_id(1)
	_refresh()


func _refresh() -> void:
	if JobSystem.is_job_complete(JobSystem.TRUST_FALL_JOB_ID):
		label.text = "TRUST FALL\nCertified"
	elif JobSystem.is_active(JobSystem.TRUST_FALL_JOB_ID):
		label.text = "TRUST FALL\n%d/3" % JobSystem.get_progress(JobSystem.TRUST_FALL_JOB_ID)
	else:
		label.text = "TRUST FALL\nPress E"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.TRUST_FALL_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_progress() -> void:
	if multiplayer.is_server():
		JobSystem.add_progress(JobSystem.TRUST_FALL_JOB_ID, 1)
