extends Interactable

## Two-step coolant job: hold valves and spin wheel.

@export var step_kind: String = "valve"

@onready var label: Label3D = $Label3D
var _hold_time: float = 0.0


func _ready() -> void:
	super._ready()
	collision_layer = 8
	_refresh()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.is_job_complete(JobSystem.COOLANT_JOB_ID):
		return "Coolant stable"
	if not JobSystem.is_active(JobSystem.COOLANT_JOB_ID):
		return "Start Coolant Gargle"
	if step_kind == "wheel":
		return "Spin wheel"
	return "Hold valve"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.is_job_complete(JobSystem.COOLANT_JOB_ID)


func interact(_player: Node3D) -> void:
	if not can_interact(_player):
		return
	if not JobSystem.is_active(JobSystem.COOLANT_JOB_ID):
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.COOLANT_JOB_ID)
		else:
			_request_start.rpc_id(1)
		_refresh()
		return
	if multiplayer.is_server():
		JobSystem.set_progress(JobSystem.COOLANT_JOB_ID, mini(JobSystem.get_progress(JobSystem.COOLANT_JOB_ID) + 25, 100))
		if JobSystem.get_progress(JobSystem.COOLANT_JOB_ID) >= 100:
			JobSystem.complete_job(JobSystem.COOLANT_JOB_ID)
	else:
		_request_progress.rpc_id(1)
	_refresh()


func _refresh() -> void:
	if JobSystem.is_job_complete(JobSystem.COOLANT_JOB_ID):
		label.text = "COOLANT\nStable"
	elif JobSystem.is_active(JobSystem.COOLANT_JOB_ID):
		label.text = "COOLANT\n%d%%" % JobSystem.get_progress(JobSystem.COOLANT_JOB_ID)
	else:
		label.text = "COOLANT\nPress E"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.COOLANT_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_progress() -> void:
	if not multiplayer.is_server():
		return
	JobSystem.set_progress(JobSystem.COOLANT_JOB_ID, mini(JobSystem.get_progress(JobSystem.COOLANT_JOB_ID) + 25, 100))
	if JobSystem.get_progress(JobSystem.COOLANT_JOB_ID) >= 100:
		JobSystem.complete_job(JobSystem.COOLANT_JOB_ID)
