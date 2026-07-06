extends CarryableItem

## Stowaway-only contraband crate.

@onready var label: Label3D = $Label3D


func _ready() -> void:
	item_id = "hot_dog"
	display_name = "Hot Dog Crate"
	super._ready()
	label.text = "HOT DOG CRATE\nSpace Goods?"


func get_prompt(_player: Node3D) -> String:
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
