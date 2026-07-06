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
@onready var top_panel: PanelContainer = $HUD/TopPanel
@onready var status_label: Label = $HUD/TopPanel/MarginContainer/VBoxContainer/StatusLabel
@onready var hint_label: Label = $HUD/TopPanel/MarginContainer/VBoxContainer/HintLabel
@onready var mission_briefing: Control = $HUD/MissionBriefing
@onready var briefing_body: RichTextLabel = $HUD/MissionBriefing/Panel/MarginContainer/VBoxContainer/BodyLabel
@onready var briefing_dismiss: Button = $HUD/MissionBriefing/Panel/MarginContainer/VBoxContainer/DismissButton
@onready var disconnect_button: Button = $HUD/GameHUD/MarginContainer/HBoxContainer/LeftColumn/DisconnectButton
@onready var game_hud: Control = $HUD/GameHUD

var _spawn_points: Array[Marker3D] = []
var _briefing_visible: bool = false


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
	mission_briefing.visible = false
	briefing_dismiss.pressed.connect(_dismiss_mission_briefing)
	GameState.role_assigned.connect(_on_role_assigned_briefing)
	JobSystem.job_completed.connect(func(_id): _dismiss_mission_briefing())
	RoundManager.shuttle_unlocked.connect(func(_s): _dismiss_mission_briefing())

	if multiplayer.is_server():
		_spawn_player(1)
		for peer_id in multiplayer.get_peers():
			_spawn_player(peer_id)
		await get_tree().create_timer(0.5).timeout
		RoundManager.start_round(_gather_peer_ids())
	else:
		_request_spawn.rpc_id(1)


func _unhandled_input(event: InputEvent) -> void:
	if _briefing_visible and event.is_action_pressed("toggle_job_board"):
		_dismiss_mission_briefing()
		return
	if event.is_action_pressed("toggle_job_board") and game_hud.has_method("toggle_job_board"):
		game_hud.toggle_job_board()


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

	var spawn_index := (peer_id - 1) % maxi(_spawn_points.size(), 1)
	players_root.add_child(player, true)
	if _spawn_points.size() > 0:
		var spawn_pos := _spawn_points[spawn_index].global_position
		spawn_pos.y = 0.0
		player.global_position = spawn_pos
	else:
		player.global_position = Vector3((peer_id - 1) * 2.0, 1.0, 0.0)
	player.set_player_color(PLAYER_COLORS[(peer_id - 1) % PLAYER_COLORS.size()])
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
	status_label.text = "%s | Port %d | Players: %d" % [
		role,
		NetworkManager.DEFAULT_PORT,
		player_count,
	]
	hint_label.text = "WASD · Mouse look · F interact · Tab job board · Esc cursor"


func _on_role_assigned_briefing(role: GameState.Role) -> void:
	if _briefing_visible:
		return
	_show_mission_briefing(role)


func _show_mission_briefing(role: GameState.Role) -> void:
	_briefing_visible = true
	mission_briefing.visible = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

	var role_block := ""
	if role == GameState.Role.STOWAWAY:
		role_block = """
[b]Your role: STOWAWAY[/b]
• Find contraband in each zone (colored floor tiles)
• Carry items to the [b]Janitor Vent[/b] on the west side of Main Hub
• Smuggle [b]3 items[/b] before the crew escapes
• Sabotage keys: [b]1[/b] Jazz  [b]2[/b] Gravity  [b]3[/b] Door  [b]4[/b] Slime  [b]5[/b] Shuttle delay
"""
	else:
		role_block = """
[b]Your role: CREW[/b]
• Complete [b]7 of 10[/b] station jobs before time runs out
• One player is the Stowaway — call [b]Emergency Meetings[/b] in the Break Room if suspicious
• Keep Corporate Satisfaction above zero
"""

	briefing_body.text = """[center][b]MEGABARGAIN ORBIT #12[/b][/center]

%s
[b]How to start[/b]
• Go to the [b]blue Job Kiosk[/b] in Main Hub (west side, pulsing floor marker)
• Press [b]F[/b] at any job station to begin that task
• Press [b]Tab[/b] anytime for the job board with locations

[b]Station layout[/b] — follow colored floor arrows from center:
• [color=#d4a060]West[/color] = Cargo Ring  ·  [color=#6aa0d4]East[/color] = Ops Deck
• [color=#70c090]South[/color] = Break Room  ·  [color=#d06060]SE[/color] = Docking Arm
• [color=#f0c840]North[/color] = Shuttle Bay (opens after 7 jobs)

[b]Controls[/b]: WASD move · Mouse look · F interact · Esc frees cursor
""" % role_block.strip_edges()


func _dismiss_mission_briefing() -> void:
	if not _briefing_visible:
		return
	_briefing_visible = false
	mission_briefing.visible = false
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	_fade_controls_hint()


func _fade_controls_hint() -> void:
	hint_label.text = "Tab = job board · Floor arrows point to each zone · F at glowing stations"
	hint_label.modulate.a = 1.0
	status_label.modulate.a = 1.0
	top_panel.visible = true
	top_panel.modulate.a = 1.0
	await get_tree().create_timer(12.0).timeout
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(hint_label, "modulate:a", 0.0, 0.8)
	tween.tween_property(status_label, "modulate:a", 0.0, 0.8)
	await tween.finished
	hint_label.visible = false
	status_label.visible = false
	var panel_tween := create_tween()
	panel_tween.tween_property(top_panel, "modulate:a", 0.0, 0.6)
	await panel_tween.finished
	top_panel.visible = false

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
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	get_tree().change_scene_to_file("res://scenes/main/main_menu.tscn")


@rpc("any_peer", "call_remote", "reliable")
func _request_spawn() -> void:
	if not multiplayer.is_server():
		return
	_spawn_player(multiplayer.get_remote_sender_id())
