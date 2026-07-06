extends Interactable

## Accept Paperwork Avalanche and confirm completion.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	prompt_text = "Accept job"
	JobSystem.paperwork_state_changed.connect(_refresh_label)
	_refresh_label()


func get_prompt(_player: Node3D) -> String:
	if JobSystem.paperwork_complete:
		return "Job complete"
	if JobSystem.paperwork_active:
		if JobSystem.forms_fed >= JobSystem.PAPERWORK_FORMS_REQUIRED:
			return "Confirm paperwork"
		return "Job in progress"
	return "Accept Paperwork Avalanche"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.paperwork_complete


func interact(player: Node3D) -> void:
	if not can_interact(player):
		return
	if multiplayer.is_server():
		_handle_interact()
	else:
		_request_interact.rpc_id(1)


func _handle_interact() -> void:
	if JobSystem.paperwork_complete:
		return

	if not JobSystem.paperwork_active:
		JobSystem.start_paperwork_job(multiplayer.get_unique_id())
		_refresh_label()
		return

	if JobSystem.forms_fed >= JobSystem.PAPERWORK_FORMS_REQUIRED:
		JobSystem.complete_paperwork_job()
		_refresh_label()


func _refresh_label(_active: bool = false, _forms_fed: int = 0, _complete: bool = false) -> void:
	if JobSystem.paperwork_complete:
		label.text = "JOB KIOSK\n✓ Paperwork Done"
	elif JobSystem.paperwork_active:
		label.text = "JOB KIOSK\nPaperwork %d/%d" % [
			JobSystem.forms_fed,
			JobSystem.PAPERWORK_FORMS_REQUIRED,
		]
	else:
		label.text = "JOB KIOSK\nPress F to start"


@rpc("any_peer", "call_remote", "reliable")
func _request_interact() -> void:
	if not multiplayer.is_server():
		return
	_handle_interact()
