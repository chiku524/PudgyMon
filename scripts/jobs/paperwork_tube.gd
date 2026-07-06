extends Interactable

## Accepts paperwork forms. Sucks in players who arrive empty-handed.

@onready var label: Label3D = $Label3D
@onready var suck_point: Marker3D = $SuckPoint


func _ready() -> void:
	super._ready()
	collision_layer = 8
	JobSystem.paperwork_state_changed.connect(_refresh_label)
	_refresh_label()


func get_prompt(player: Node3D) -> String:
	if not JobSystem.paperwork_active:
		return "Tube offline"
	if player.has_method("is_carrying_forms") and player.is_carrying_forms():
		return "Feed form"
	return "Do not touch the tube"


func can_interact(_player: Node3D) -> bool:
	return JobSystem.paperwork_active and not JobSystem.paperwork_complete


func interact(player: Node3D) -> void:
	if not can_interact(player):
		return
	if multiplayer.is_server():
		_handle_feed(player)
	else:
		_request_feed.rpc_id(1)


func _handle_feed(player: Node3D) -> void:
	if player.has_method("is_carrying_forms") and player.is_carrying_forms():
		var consumed: bool = player.consume_carried_form()
		if consumed and JobSystem.feed_paperwork_form():
			_refresh_label()
		return

	if player.has_method("trigger_dizzy"):
		player.global_position = suck_point.global_position
		player.trigger_dizzy(3.0)


func _refresh_label(_active: bool = false, _forms_fed: int = 0, _complete: bool = false) -> void:
	if JobSystem.paperwork_active and not JobSystem.paperwork_complete:
		label.text = "PNEUMATIC TUBE\nForms: %d/%d" % [
			JobSystem.forms_fed,
			JobSystem.PAPERWORK_FORMS_REQUIRED,
		]
	else:
		label.text = "PNEUMATIC TUBE\nOffline"


@rpc("any_peer", "call_remote", "reliable")
func _request_feed() -> void:
	if not multiplayer.is_server():
		return
	var peer_id := multiplayer.get_remote_sender_id()
	var player := _find_player(peer_id)
	if player != null:
		_handle_feed(player)


func _find_player(peer_id: int) -> Node3D:
	for node in get_tree().get_nodes_in_group("players"):
		if node.name == str(peer_id):
			return node
	return null
