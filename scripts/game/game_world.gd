extends Node3D

## Spawns players and loads MegaBargain Orbit #12 when a network session starts.

const HUB_SCENE := preload("res://scenes/levels/megabargain_orbit_12.tscn")
const PLAYER_SCENE := preload("res://scenes/player/player.tscn")
const MEETING_PANEL_SCENE := preload("res://scenes/ui/meeting_panel.tscn")
const ROUND_END_SCENE := preload("res://scenes/ui/round_end_panel.tscn")
const PLAYER_COLORS: Array[Color] = [
	Color(0.95, 0.78, 0.2),
	Color(0.95, 0.45, 0.2),
	Color(0.2, 0.85, 0.9),
	Color(0.95, 0.35, 0.75),
	Color(0.55, 0.55, 0.6),
	Color(0.55, 0.25, 0.85),
	Color(0.45, 0.9, 0.55),
	Color(0.55, 0.75, 0.45),
]

@onready var players_root: Node3D = $Players
@onready var level_root: Node3D = $Level
@onready var status_label: Label = $HUD/TopPanel/MarginContainer/VBoxContainer/StatusLabel
@onready var hint_label: Label = $HUD/TopPanel/MarginContainer/VBoxContainer/HintLabel
@onready var disconnect_button: Button = $HUD/TopPanel/MarginContainer/VBoxContainer/DisconnectButton

var _spawn_points: Array[Marker3D] = []


func _ready() -> void:
	disconnect_button.pressed.connect(_on_disconnect_pressed)
	NetworkManager.player_joined.connect(_on_player_joined)
	NetworkManager.player_left.connect(_on_player_left)
	NetworkManager.server_disconnected.connect(_on_server_disconnected)

	add_child(MEETING_PANEL_SCENE.instantiate())
	add_child(ROUND_END_SCENE.instantiate())

	_load_hub()
	_collect_spawn_points()
	_update_status()

	if multiplayer.is_server():
		_spawn_player(1)
		for peer_id in multiplayer.get_peers():
			_spawn_player(peer_id)
		await get_tree().create_timer(0.5).timeout
		RoundManager.start_round(_gather_peer_ids())
	else:
		_request_spawn.rpc_id(1)


func _gather_peer_ids() -> PackedInt32Array:
	var ids := PackedInt32Array()
	for child in players_root.get_children():
		ids.append(int(child.name))
	return ids


func _load_hub() -> void:
	for child in level_root.get_children():
		child.queue_free()
	var hub := HUB_SCENE.instantiate()
	level_root.add_child(hub)


func _collect_spawn_points() -> void:
	_spawn_points.clear()
	var hub := level_root.get_child(0) if level_root.get_child_count() > 0 else null
	if hub == null:
		return
	var spawn_root := hub.get_node_or_null("SpawnPoints")
	if spawn_root == null:
		return
	for child in spawn_root.get_children():
		if child is Marker3D:
			_spawn_points.append(child)


func _spawn_player(peer_id: int) -> void:
	if players_root.has_node(str(peer_id)):
		return

	var player := PLAYER_SCENE.instantiate()
	player.name = str(peer_id)
	player.player_name = _player_name_for_peer(peer_id)
	player.set_player_color(PLAYER_COLORS[(peer_id - 1) % PLAYER_COLORS.size()])

	var spawn_index := (peer_id - 1) % maxi(_spawn_points.size(), 1)
	if _spawn_points.size() > 0:
		player.global_position = _spawn_points[spawn_index].global_position
	else:
		player.global_position = Vector3((peer_id - 1) * 2.0, 1.0, 0.0)

	players_root.add_child(player, true)
	_update_status()


func _player_name_for_peer(peer_id: int) -> String:
	if peer_id == multiplayer.get_unique_id():
		return GameState.local_player_name
	return "Crew %d" % peer_id


func _despawn_player(peer_id: int) -> void:
	var node_name := str(peer_id)
	if players_root.has_node(node_name):
		players_root.get_node(node_name).queue_free()
	_update_status()


func _update_status() -> void:
	var role := "Host" if multiplayer.is_server() else "Client"
	var player_count := players_root.get_child_count()
	status_label.text = "%s | Port %d | Players: %d | Complete 4 jobs, catch the Stowaway, escape shuttle" % [
		role,
		NetworkManager.DEFAULT_PORT,
		player_count,
	]
	hint_label.text = "Complete 7 jobs. Stowaway: smuggle 3 items (vent) + sabotage keys 1-5."


func _on_player_joined(peer_id: int) -> void:
	if multiplayer.is_server():
		_spawn_player(peer_id)


func _on_player_left(peer_id: int) -> void:
	_despawn_player(peer_id)


func _on_server_disconnected() -> void:
	_return_to_menu()


func _on_disconnect_pressed() -> void:
	NetworkManager.disconnect_from_game()
	_return_to_menu()


func _return_to_menu() -> void:
	get_tree().change_scene_to_file("res://scenes/main/main_menu.tscn")


@rpc("any_peer", "call_remote", "reliable")
func _request_spawn() -> void:
	if not multiplayer.is_server():
		return
	_spawn_player(multiplayer.get_remote_sender_id())
