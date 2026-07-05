extends Interactable

## Spin dish wheel to fill RPM progress.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	JobSystem.job_board_changed.connect(func _a, _b: _refresh())
	_refresh()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.is_job_complete(JobSystem.DISH_JOB_ID):
		return "Dish aligned"
	if not JobSystem.is_active(JobSystem.DISH_JOB_ID):
		return "Start Dish Go Brr"
	return "Spin dish wheel"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.is_job_complete(JobSystem.DISH_JOB_ID)


func interact(_player: Node3D) -> void:
	if not can_interact(_player):
		return
	if not JobSystem.is_active(JobSystem.DISH_JOB_ID):
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.DISH_JOB_ID)
		else:
			_request_start.rpc_id(1)
		return
	if multiplayer.is_server():
		JobSystem.set_progress(JobSystem.DISH_JOB_ID, mini(JobSystem.get_progress(JobSystem.DISH_JOB_ID) + 20, 100))
		if JobSystem.get_progress(JobSystem.DISH_JOB_ID) >= 100:
			JobSystem.complete_job(JobSystem.DISH_JOB_ID)
	else:
		_request_progress.rpc_id(1)
	_refresh()


func _refresh() -> void:
	if JobSystem.is_job_complete(JobSystem.DISH_JOB_ID):
		label.text = "DISH\nBrr!"
	elif JobSystem.is_active(JobSystem.DISH_JOB_ID):
		label.text = "DISH\nRPM %d%%" % JobSystem.get_progress(JobSystem.DISH_JOB_ID)
	else:
		label.text = "DISH\nPress E"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.DISH_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_progress() -> void:
	if not multiplayer.is_server():
		return
	JobSystem.set_progress(JobSystem.DISH_JOB_ID, mini(JobSystem.get_progress(JobSystem.DISH_JOB_ID) + 20, 100))
	if JobSystem.get_progress(JobSystem.DISH_JOB_ID) >= 100:
		JobSystem.complete_job(JobSystem.DISH_JOB_ID)
