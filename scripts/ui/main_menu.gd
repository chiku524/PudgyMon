extends Control

## Main menu — host or join a Phase 0 LAN session.

@onready var name_edit: LineEdit = $Panel/MarginContainer/VBoxContainer/NameRow/NameEdit
@onready var address_edit: LineEdit = $Panel/MarginContainer/VBoxContainer/AddressRow/AddressEdit
@onready var port_edit: LineEdit = $Panel/MarginContainer/VBoxContainer/PortRow/PortEdit
@onready var host_button: Button = $Panel/MarginContainer/VBoxContainer/HostButton
@onready var join_button: Button = $Panel/MarginContainer/VBoxContainer/JoinButton
@onready var status_label: Label = $Panel/MarginContainer/VBoxContainer/StatusLabel

const GAME_WORLD_SCENE := "res://scenes/game/game_world.tscn"


func _ready() -> void:
	name_edit.text = GameState.local_player_name
	address_edit.text = "127.0.0.1"
	port_edit.text = str(NetworkManager.DEFAULT_PORT)

	host_button.pressed.connect(_on_host_pressed)
	join_button.pressed.connect(_on_join_pressed)
	NetworkManager.connection_succeeded.connect(_on_connection_succeeded)
	NetworkManager.connection_failed.connect(_on_connection_failed)
	NetworkManager.server_disconnected.connect(_on_server_disconnected)


func _on_host_pressed() -> void:
	_set_status("Starting host...")
	GameState.set_local_player_name(name_edit.text)
	var port := _read_port()
	var err := NetworkManager.host_game(port)
	if err != OK:
		_set_status("Failed to host (error %d)." % err)
		return
	_set_status("Hosting on port %d..." % port)
	if multiplayer.is_server():
		get_tree().change_scene_to_file(GAME_WORLD_SCENE)


func _on_join_pressed() -> void:
	_set_status("Connecting...")
	GameState.set_local_player_name(name_edit.text)
	var port := _read_port()
	var address := address_edit.text.strip_edges()
	var err := NetworkManager.join_game(address, port)
	if err != OK:
		_set_status("Failed to join (error %d)." % err)


func _on_connection_succeeded() -> void:
	_set_status("Connected!")
	get_tree().change_scene_to_file(GAME_WORLD_SCENE)


func _on_connection_failed() -> void:
	_set_status("Connection failed. Check IP/port and try again.")


func _on_server_disconnected() -> void:
	_set_status("Disconnected from host.")


func _read_port() -> int:
	var parsed := port_edit.text.strip_edges().to_int()
	return parsed if parsed > 0 else NetworkManager.DEFAULT_PORT


func _set_status(text: String) -> void:
	status_label.text = text
