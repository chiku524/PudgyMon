extends Interactable

## Prints forms for Paperwork Avalanche when the job is active.

const FORM_SCENE := preload("res://scenes/props/carryable_form.tscn")

@onready var label: Label3D = $Label3D
@onready var spawn_point: Marker3D = $SpawnPoint


func _ready() -> void:
	super._ready()
	collision_layer = 8
	prompt_text = "Print form"
	JobSystem.paperwork_state_changed.connect(_refresh_label)
	_refresh_label()


func get_prompt(_player: Node3D) -> String:
	if not JobSystem.paperwork_active or JobSystem.paperwork_complete:
		return "Printer idle"
	if JobSystem.forms_fed >= JobSystem.PAPERWORK_FORMS_REQUIRED:
		return "All forms printed"
	return "Print form"


func can_interact(player: Node3D) -> bool:
	return (
		JobSystem.paperwork_active
		and not JobSystem.paperwork_complete
		and JobSystem.forms_fed < JobSystem.PAPERWORK_FORMS_REQUIRED
		and player.has_method("can_pickup_item")
		and player.can_pickup_item()
	)


func interact(player: Node3D) -> void:
	if not can_interact(player):
		return
	if multiplayer.is_server():
		_spawn_form_for(player)
	else:
		_request_print.rpc_id(1)


func _spawn_form_for(player: Node3D) -> void:
	var peer_id := int(player.name)
	var form_id := "form_%d_%d" % [peer_id, Time.get_ticks_msec()]
	_sync_spawn_form.rpc(spawn_point.global_position, peer_id, form_id)


func _refresh_label(_active: bool = false, _forms_fed: int = 0, _complete: bool = false) -> void:
	if JobSystem.paperwork_active and not JobSystem.paperwork_complete:
		label.text = "PRINTER\nPress F for form"
	else:
		label.text = "PRINTER\nIdle"


@rpc("authority", "call_remote", "reliable")
func _sync_spawn_form(spawn_position: Vector3, peer_id: int, form_id: String) -> void:
	var form := FORM_SCENE.instantiate()
	form.name = form_id
	get_tree().current_scene.add_child(form)
	form.global_position = spawn_position
	if multiplayer.get_unique_id() == peer_id:
		var player := _find_player(peer_id)
		if player != null and player.has_method("pickup_item"):
			player.pickup_item(form)


@rpc("any_peer", "call_remote", "reliable")
func _request_print() -> void:
	if not multiplayer.is_server():
		return
	var peer_id := multiplayer.get_remote_sender_id()
	var player := _find_player(peer_id)
	if player != null:
		_spawn_form_for(player)


func _find_player(peer_id: int) -> Node3D:
	for node in get_tree().get_nodes_in_group("players"):
		if node.name == str(peer_id):
			return node
	return null
