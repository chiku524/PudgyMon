extends Node

## Applies root-window content scaling so the game fills resizes and maximize.

const DESIGN_SIZE := Vector2i(1280, 720)


func _ready() -> void:
	var root: Window = get_tree().root
	if not root.size_changed.is_connected(_apply_display_settings):
		root.size_changed.connect(_apply_display_settings)
	_apply_display_settings()


func _apply_display_settings() -> void:
	var root: Window = get_tree().root
	# canvas_items: 3D renders at native window resolution; UI scales from DESIGN_SIZE.
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	root.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
	root.content_scale_stretch = Window.CONTENT_SCALE_STRETCH_FRACTIONAL
	root.content_scale_size = DESIGN_SIZE
