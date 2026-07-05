extends Control

## PA announcer subtitle bar.

@onready var label: Label = $Panel/MarginContainer/Label


func _ready() -> void:
	Announcer.bark_displayed.connect(_on_bark)
	modulate.a = 0.0


func _on_bark(text: String) -> void:
	label.text = "PA: %s" % text
	modulate.a = 1.0
	var tween := create_tween()
	tween.tween_interval(4.0)
	tween.tween_property(self, "modulate:a", 0.0, 0.8)
