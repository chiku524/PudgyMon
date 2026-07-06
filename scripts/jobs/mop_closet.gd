extends Interactable

## Gives the player a mop to clean slime puddles.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	prompt_text = "Take mop"
	JobSystem.job_board_changed.connect(func(_a, _b): _refresh_label())
	_refresh_label()


func get_prompt(player: Node3D) -> String:
	if JobSystem.mop_complete:
		return "Floor spotless"
	if not JobSystem.mop_active:
		return "Start Mop the Future"
	if player.has_method("has_mop_equipped") and player.has_mop_equipped():
		return "Mop equipped"
	return "Take mop"


func can_interact(_player: Node3D) -> bool:
	return not JobSystem.mop_complete


func interact(player: Node3D) -> void:
	if JobSystem.mop_complete:
		return
	if not JobSystem.mop_active:
		if multiplayer.is_server():
			JobSystem.start_job(JobSystem.MOP_JOB_ID)
		else:
			_request_start.rpc_id(1)
		_refresh_label()
		return
	if player.has_method("equip_mop"):
		player.equip_mop()


func _refresh_label() -> void:
	if JobSystem.mop_complete:
		label.text = "MOP CLOSET\nDone"
	elif JobSystem.mop_active:
		label.text = "MOP CLOSET\n%d/%d cleaned" % [JobSystem.mop_cleaned, JobSystem.MOP_PUDDLES_REQUIRED]
	else:
		label.text = "MOP CLOSET\nPress F"


@rpc("any_peer", "call_remote", "reliable")
func _request_start() -> void:
	if multiplayer.is_server():
		JobSystem.start_job(JobSystem.MOP_JOB_ID)
