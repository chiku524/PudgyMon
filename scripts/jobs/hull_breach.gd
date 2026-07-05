extends Interactable

## Patch hull breaches on the docking arm.

@export var breach_index: int = 0

@onready var label: Label3D = $Label3D
var _patching: bool = false
var _patch_time: float = 0.0


func _ready() -> void:
	super._ready()
	collision_layer = 8
	_refresh()


func _process(delta: float) -> void:
	if not _patching:
		return
	_patch_time += delta
	if _patch_time >= 3.0:
		_patching = false
		if multiplayer.is_server() and get_progress() == breach_index:
			JobSystem.add_progress(JobSystem.DUCT_TAPE_JOB_ID, 1)
		elif not multiplayer.is_server():
			_request_progress.rpc_id(1, breach_index)
		_refresh()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.is_job_complete(JobSystem.DUCT_TAPE_JOB_ID):
		return "Hull secure"
	if not JobSystem.is_active(JobSystem.DUCT_TAPE_JOB_ID):
		return "Start Duct Tape OR ELSE"
	if get_progress() > breach_index:
		return "Patched"
	return "Hold E to tape breach"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.is_job_complete(JobSystem.DUCT_TAPE_JOB_ID)


func interact(_player: Node3D) -> void:
	if not can_interact(_player):
		return
	if not JobSystem.is_active(JobSystem.DUCT_TAPE_JOB_ID):
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.DUCT_TAPE_JOB_ID)
		else:
			_request_start.rpc_id(1)
		_refresh()
		return
	if get_progress() > breach_index or _patching:
		return
	_patching = true
	_patch_time = 0.0
	label.text = "TAPE\nHold..."


func get_progress() -> int:
	return JobSystem.get_progress(JobSystem.DUCT_TAPE_JOB_ID)


func _refresh() -> void:
	if JobSystem.is_job_complete(JobSystem.DUCT_TAPE_JOB_ID):
		label.text = "BREACH %d\nOK" % (breach_index + 1)
	elif get_progress() > breach_index:
		label.text = "BREACH %d\nOK" % (breach_index + 1)
	elif JobSystem.is_active(JobSystem.DUCT_TAPE_JOB_ID):
		label.text = "BREACH %d\nTape me" % (breach_index + 1)
	else:
		label.text = "BREACH %d\nIdle" % (breach_index + 1)


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.DUCT_TAPE_JOB_ID)


@rpc("any_peer", "call_remote", "reliable")
func _request_progress(breach_idx: int) -> void:
	if multiplayer.is_server() and JobSystem.get_progress(JobSystem.DUCT_TAPE_JOB_ID) == breach_idx:
		JobSystem.add_progress(JobSystem.DUCT_TAPE_JOB_ID, 1)
