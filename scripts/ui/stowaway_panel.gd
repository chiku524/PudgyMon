extends Control

## Stowaway sabotage hotkeys (1-5).

@onready var panel: PanelContainer = $Panel


func _ready() -> void:
	visible = false
	GameState.role_assigned.connect(_on_role)
	_on_role(GameState.local_role)


func _on_role(role: GameState.Role) -> void:
	visible = role == GameState.Role.STOWAWAY


func _unhandled_input(event: InputEvent) -> void:
	if not visible or not GameState.is_local_stowaway():
		return
	if not event is InputEventKey or not event.pressed:
		return
	var sabotage_id := ""
	match event.keycode:
		KEY_1:
			sabotage_id = "jazz"
		KEY_2:
			sabotage_id = "gravity"
		KEY_3:
			sabotage_id = "door"
		KEY_4:
			sabotage_id = "slime"
		KEY_5:
			sabotage_id = "shuttle_delay"
	if sabotage_id.is_empty():
		return
	StowawaySystem.request_sabotage(sabotage_id)
