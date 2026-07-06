extends Control

## PA announcer subtitle bar — shows briefly, then fades out.

const DISPLAY_SECONDS := 4.0
const FADE_SECONDS := 0.8

@onready var panel: PanelContainer = $Panel
@onready var label: Label = $Panel/MarginContainer/Label

var _fade_tween: Tween


func _ready() -> void:
	Announcer.bark_displayed.connect(_on_bark)
	visible = false
	modulate = Color(1, 1, 1, 0)


func _on_bark(text: String) -> void:
	if _fade_tween and _fade_tween.is_running():
		_fade_tween.kill()

	label.text = "PA: %s" % text
	visible = true
	modulate = Color(1, 1, 1, 1)

	_fade_tween = create_tween()
	_fade_tween.tween_interval(DISPLAY_SECONDS)
	_fade_tween.tween_property(self, "modulate", Color(1, 1, 1, 0), FADE_SECONDS)
	_fade_tween.tween_callback(_hide)


func _hide() -> void:
	visible = false
	label.text = ""
