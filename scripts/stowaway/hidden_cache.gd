extends Interactable

## Hidden vent cache for all smuggle contraband.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	super._ready()
	collision_layer = 8
	RoundManager.timer_updated.connect(func(_a, _b): _refresh_label())


func get_prompt(player: Node3D) -> String:
	if not GameState.is_local_stowaway():
		return "Janitor vent"
	if player.has_method("is_carrying_contraband") and player.is_carrying_contraband():
		return "Deposit contraband"
	return "Need contraband"


func can_interact(player: Node3D) -> bool:
	return GameState.is_local_stowaway() and player.has_method("is_carrying_contraband") and player.is_carrying_contraband()


func interact(player: Node3D) -> void:
	if not can_interact(player):
		return
	if multiplayer.is_server():
		_deposit(player)
	else:
		_request_deposit.rpc_id(1)


func _deposit(player: Node3D) -> void:
	if not player.has_method("consume_contraband"):
		return
	if not player.consume_contraband():
		return
	RoundManager.deposit_smuggle(int(player.name))
	_refresh_label()


func _refresh_label() -> void:
	var count: int = GameState.smuggle_counts.get(multiplayer.get_unique_id(), 0)
	if GameState.is_local_stowaway():
		label.text = "HIDDEN CACHE\nSmuggled: %d/%d" % [count, StowawaySystem.SMUGGLE_QUOTA]
	else:
		label.text = "JANITOR VENT"


@rpc("any_peer", "call_remote", "reliable")
func _request_deposit() -> void:
	if not multiplayer.is_server():
		return
	var peer_id := multiplayer.get_remote_sender_id()
	var player := _find_player(peer_id)
	if player != null:
		_deposit(player)


func _find_player(peer_id: int) -> Node3D:
	for node in get_tree().get_nodes_in_group("players"):
		if node.name == str(peer_id):
			return node
	return null
