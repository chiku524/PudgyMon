extends CarryableItem

## Stowaway-only contraband pickup — generic smuggle items.

@export var smuggle_item_id: String = "hot_dog"
@export var smuggle_display_name: String = "Contraband"
@export var label_text: String = "CONTRABAND"

@onready var label: Label3D = $Label3D


func _ready() -> void:
	item_id = smuggle_item_id
	display_name = smuggle_display_name
	super._ready()
	if label:
		label.text = label_text


func get_prompt(player: Node3D) -> String:
	if is_carried:
		return ""
	if GameState.is_local_stowaway():
		return "Take contraband"
	return "Space goods crate"


func can_interact(player: Node3D) -> bool:
	if is_carried:
		return false
	if not GameState.is_local_stowaway():
		return false
	return player.has_method("can_pickup_item") and player.can_pickup_item()
