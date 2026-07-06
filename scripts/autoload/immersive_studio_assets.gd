extends Node

## Registers Immersive Labs studio pack assets for ShipHappens at startup.


func _ready() -> void:
	ImmersiveStudioRegistry.register_all()
