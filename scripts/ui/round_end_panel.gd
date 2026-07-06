extends CanvasLayer

## Post-round results overlay with stats.

@onready var panel: PanelContainer = $Panel
@onready var title_label: Label = $Panel/MarginContainer/VBoxContainer/TitleLabel
@onready var body_label: Label = $Panel/MarginContainer/VBoxContainer/BodyLabel
@onready var stats_label: RichTextLabel = $Panel/MarginContainer/VBoxContainer/StatsLabel
@onready var menu_button: Button = $Panel/MarginContainer/VBoxContainer/MenuButton
@onready var rematch_button: Button = $Panel/MarginContainer/VBoxContainer/RematchButton


func _ready() -> void:
	visible = false
	menu_button.pressed.connect(_return_to_menu)
	rematch_button.pressed.connect(_request_rematch)
	RoundManager.round_ended.connect(_on_round_ended)


func _on_round_ended(result: Dictionary) -> void:
	visible = true
	var winner: String = result.get("winner", "none")
	match winner:
		"crew":
			title_label.text = "CREW WIN"
		"stowaway":
			title_label.text = "STOWAWAY WIN"
		_:
			title_label.text = "EVERYONE FIRED"

	body_label.text = "%s\n\nJobs: %d/%d\nSatisfaction: %d%%\nMeetings used: %d" % [
		result.get("reason", ""),
		result.get("jobs_completed", 0),
		GameState.jobs_required,
		int(result.get("satisfaction", 0)),
		result.get("meetings_used", 0),
	]
	var stats: Dictionary = result.get("stats", {})
	stats_label.text = stats.get("text", "")
	rematch_button.visible = multiplayer.is_server()


func _return_to_menu() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	NetworkManager.disconnect_from_game()
	get_tree().change_scene_to_file("res://scenes/main/main_menu.tscn")


func _request_rematch() -> void:
	if multiplayer.is_server():
		get_tree().reload_current_scene()
	else:
		_ask_server_rematch.rpc_id(1)


@rpc("any_peer", "call_remote", "reliable")
func _ask_server_rematch() -> void:
	if multiplayer.is_server():
		get_tree().reload_current_scene()
