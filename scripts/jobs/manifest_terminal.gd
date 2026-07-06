extends Interactable

## Starts Manifest Lies job.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	JobSystem.job_board_changed.connect(func(_a, _b): _refresh_label())
	_refresh_label()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.manifest_complete:
		return "Manifest verified"
	if not JobSystem.manifest_active:
		return "Start Manifest Lies"
	return "Scan crates at orange pad"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.manifest_complete


func interact(_player: Node3D) -> void:
	if JobSystem.manifest_complete or JobSystem.manifest_active:
		return
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.MANIFEST_JOB_ID)
	else:
		_request_start.rpc_id(1)
	_refresh_label()


func _refresh_label() -> void:
	if JobSystem.manifest_complete:
		label.text = "MANIFEST\nVerified"
	elif JobSystem.manifest_active:
		label.text = "MANIFEST\n%d/%d scanned" % [JobSystem.manifest_scanned, JobSystem.MANIFEST_CRATES_REQUIRED]
	else:
		label.text = "MANIFEST\nPress F to start"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.MANIFEST_JOB_ID)
