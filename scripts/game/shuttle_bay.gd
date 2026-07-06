extends Area3D

## Shuttle extraction zone — stand here before the timer ends.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	collision_layer = 0
	collision_mask = 2
	monitoring = true
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	label.text = "SHUTTLE BAY\nLocked"


func _process(_delta: float) -> void:
	if RoundManager.shuttle_active:
		label.text = "SHUTTLE BAY\n%.0fs left" % maxf(RoundManager.shuttle_time_remaining, 0.0)
	elif GameState.jobs_completed >= GameState.jobs_required:
		label.text = "SHUTTLE BAY\nOpening soon..."
	else:
		label.text = "SHUTTLE BAY\nNeed %d jobs (%d/%d done)" % [
			GameState.jobs_required,
			GameState.jobs_completed,
			GameState.jobs_required,
		]


func _on_body_entered(body: Node3D) -> void:
	if not body.is_in_group("players"):
		return
	if not RoundManager.shuttle_active:
		return
	if multiplayer.is_server():
		RoundManager.register_shuttle_escape(int(body.name))
	else:
		_request_escape.rpc_id(1)


func _on_body_exited(body: Node3D) -> void:
	if not multiplayer.is_server() or not body.is_in_group("players"):
		return
	var peer_id := int(body.name)
	if peer_id in GameState.escaped_peer_ids:
		GameState.escaped_peer_ids.erase(peer_id)


@rpc("any_peer", "call_remote", "reliable")
func _request_escape() -> void:
	if multiplayer.is_server() and RoundManager.shuttle_active:
		RoundManager.register_shuttle_escape(multiplayer.get_remote_sender_id())
