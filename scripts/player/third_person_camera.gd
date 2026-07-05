extends Node3D

## Orbits the third-person camera around the player via SpringArm3D.

@export var min_zoom := 2.5
@export var max_zoom := 8.0
@export var zoom_step := 0.5


func _ready() -> void:
	var spring_arm: SpringArm3D = $SpringArm3D
	spring_arm.spring_length = 5.0


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var spring_arm: SpringArm3D = $SpringArm3D
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			spring_arm.spring_length = max(min_zoom, spring_arm.spring_length - zoom_step)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			spring_arm.spring_length = min(max_zoom, spring_arm.spring_length + zoom_step)
