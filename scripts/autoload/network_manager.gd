extends Node

## Handles ENet host/join and connection signals for ShipHappens multiplayer.

const DEFAULT_PORT := 7777
const MAX_PLAYERS := 8

const PLAYER_SCENE := preload("res://scenes/player/player.tscn")

var peer: ENetMultiplayerPeer = null

signal connection_succeeded
signal connection_failed
signal server_disconnected
signal player_joined(peer_id: int)
signal player_left(peer_id: int)


func _ready() -> void:
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	multiplayer.connected_to_server.connect(_on_connected_to_server)
	multiplayer.connection_failed.connect(_on_connection_failed)
	multiplayer.server_disconnected.connect(_on_server_disconnected)


func host_game(port: int = DEFAULT_PORT) -> Error:
	disconnect_from_game()
	peer = ENetMultiplayerPeer.new()
	var err := peer.create_server(port, MAX_PLAYERS)
	if err != OK:
		peer = null
		return err
	multiplayer.multiplayer_peer = peer
	return OK


func join_game(address: String, port: int = DEFAULT_PORT) -> Error:
	disconnect_from_game()
	peer = ENetMultiplayerPeer.new()
	var err := peer.create_client(address.strip_edges(), port)
	if err != OK:
		peer = null
		return err
	multiplayer.multiplayer_peer = peer
	return OK


func disconnect_from_game() -> void:
	if peer != null:
		peer.close()
	peer = null
	multiplayer.multiplayer_peer = null


func is_online() -> bool:
	return peer != null and multiplayer.multiplayer_peer != null


func get_local_player_name() -> String:
	return GameState.local_player_name


func _on_peer_connected(id: int) -> void:
	player_joined.emit(id)
	if multiplayer.is_server():
		connection_succeeded.emit()


func _on_peer_disconnected(id: int) -> void:
	player_left.emit(id)


func _on_connected_to_server() -> void:
	connection_succeeded.emit()


func _on_connection_failed() -> void:
	disconnect_from_game()
	connection_failed.emit()


func _on_server_disconnected() -> void:
	disconnect_from_game()
	server_disconnected.emit()
