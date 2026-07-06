extends Interactable

## Simplified crane: deliver crates to drop zones.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	JobSystem.job_board_changed.connect(func(_a, _b): _refresh())
	_refresh()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.is_job_complete(JobSystem.CRANE_JOB_ID):
		return "Crane offline"
	if not JobSystem.is_active(JobSystem.CRANE_JOB_ID):
		return "Start Crane of Regret"
	return "Use crane magnet at cargo crate"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.is_job_complete(JobSystem.CRANE_JOB_ID)


func interact(_player: Node3D) -> void:
	if JobSystem.is_job_complete(JobSystem.CRANE_JOB_ID):
		return
	if not JobSystem.is_active(JobSystem.CRANE_JOB_ID):
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.CRANE_JOB_ID)
		else:
			_request_start.rpc_id(1)
		_refresh()
		return
	if multiplayer.is_server():
		JobSystem.add_progress(JobSystem.CRANE_JOB_ID, 1)
	else:
		_request_progress.rpc_id(1)
	_refresh()


func _refresh() -> void:
	if JobSystem.is_job_complete(JobSystem.CRANE_JOB_ID):
		label.text = "CRANE\nDone"
	elif JobSystem.is_active(JobSystem.CRANE_JOB_ID):
		label.text = "CRANE\nDeliveries %d/3" % JobSystem.get_progress(JobSystem.CRANE_JOB_ID)
	else:
		label.text = "CRANE\nPress F"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.CRANE_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_progress() -> void:
	if multiplayer.is_server():
		JobSystem.add_progress(JobSystem.CRANE_JOB_ID, 1)
