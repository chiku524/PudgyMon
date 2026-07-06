extends Interactable

## Load snack slots for vending restock job.

@export var slot_index: int = 0

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8


func get_prompt(_player: Node3D) -> String:
	if JobSystem.is_job_complete(JobSystem.VENDING_JOB_ID):
		return "Vending full"
	if not JobSystem.is_active(JobSystem.VENDING_JOB_ID):
		return "Start Vending Restock"
	return "Load slot %d" % (slot_index + 1)


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.is_job_complete(JobSystem.VENDING_JOB_ID)


func interact(_player: Node3D) -> void:
	if not can_interact(_player):
		return
	if not JobSystem.is_active(JobSystem.VENDING_JOB_ID):
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.VENDING_JOB_ID)
		else:
			_request_start.rpc_id(1)
		return
	if multiplayer.is_server():
		JobSystem.add_progress(JobSystem.VENDING_JOB_ID, 1)
	else:
		_request_progress.rpc_id(1)
	_refresh()


func get_progress_bit() -> int:
	return JobSystem.get_progress(JobSystem.VENDING_JOB_ID)


func _refresh() -> void:
	if JobSystem.is_job_complete(JobSystem.VENDING_JOB_ID):
		label.text = "VENDING\nFull"
	elif JobSystem.is_active(JobSystem.VENDING_JOB_ID):
		label.text = "VENDING\n%d/3" % JobSystem.get_progress(JobSystem.VENDING_JOB_ID)
	else:
		label.text = "VENDING\nPress F"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.VENDING_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_progress() -> void:
	if multiplayer.is_server():
		JobSystem.add_progress(JobSystem.VENDING_JOB_ID, 1)
