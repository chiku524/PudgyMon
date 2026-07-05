extends Node

## Stowaway smuggle items and sabotage abilities.

signal sabotage_triggered(sabotage_id: String)

const SMUGGLE_QUOTA := 3
const SMUGGLE_ITEM_IDS := ["hot_dog", "bootleg_toaster", "mini_bot", "holo_autograph", "mislabeled_air"]
const MAX_ACTIVE_SABOTAGES := 2

const SABOTAGE_COOLDOWNS := {
	"jazz": 90.0,
	"gravity": 120.0,
	"door": 60.0,
	"slime": 90.0,
	"shuttle_delay": 9999.0,
}

var _cooldowns: Dictionary = {}
var _active_sabotages: int = 0
var _shuttle_delay_used: bool = false


func reset() -> void:
	_cooldowns.clear()
	_active_sabotages = 0
	_shuttle_delay_used = false


func is_smuggle_item(item_id: String) -> bool:
	return item_id in SMUGGLE_ITEM_IDS


func can_sabotage(peer_id: int, sabotage_id: String) -> bool:
	if not GameState.is_stowaway(peer_id):
		return false
	if GameState.is_written_up(peer_id):
		return false
	if _active_sabotages >= MAX_ACTIVE_SABOTAGES:
		return false
	var key := "%d_%s" % [peer_id, sabotage_id]
	if _cooldowns.has(key) and _cooldowns[key] > Time.get_ticks_msec() / 1000.0:
		return false
	if sabotage_id == "shuttle_delay" and _shuttle_delay_used:
		return false
	return true


func trigger_sabotage(peer_id: int, sabotage_id: String) -> bool:
	if not multiplayer.is_server():
		return false
	if not can_sabotage(peer_id, sabotage_id):
		return false

	_active_sabotages += 1
	var key := "%d_%s" % [peer_id, sabotage_id]
	_cooldowns[key] = Time.get_ticks_msec() / 1000.0 + SABOTAGE_COOLDOWNS.get(sabotage_id, 60.0)
	StatsTracker.record_global("sabotages", 1)
	_apply_sabotage.rpc(sabotage_id)
	get_tree().create_timer(20.0).timeout.connect(func(): _active_sabotages = maxi(_active_sabotages - 1, 0))
	return true


func request_sabotage(sabotage_id: String) -> void:
	if multiplayer.is_server():
		trigger_sabotage(multiplayer.get_unique_id(), sabotage_id)
	else:
		_request_sabotage.rpc_id(1, sabotage_id)


@rpc("any_peer", "call_remote", "reliable")
func _request_sabotage(sabotage_id: String) -> void:
	if multiplayer.is_server():
		trigger_sabotage(multiplayer.get_remote_sender_id(), sabotage_id)


@rpc("authority", "call_remote", "reliable")
func _apply_sabotage(sabotage_id: String) -> void:
	match sabotage_id:
		"jazz":
			Announcer.bark_event("sabotage_jazz")
			GameState.add_satisfaction(-3.0)
		"gravity":
			Announcer.bark_event("sabotage_gravity")
			_apply_gravity_hiccup()
		"door":
			Announcer.bark_event("sabotage_door")
		"slime":
			Announcer.bark_event("sabotage_slime")
			_spawn_slime_spill()
		"shuttle_delay":
			Announcer.bark_event("sabotage_shuttle")
			RoundManager.add_shuttle_delay(30.0)
			_shuttle_delay_used = true
	sabotage_triggered.emit(sabotage_id)


func _apply_gravity_hiccup() -> void:
	for node in get_tree().get_nodes_in_group("players"):
		if node.has_method("apply_launch"):
			node.apply_launch(Vector3.UP * 6.0)


func _spawn_slime_spill() -> void:
	var spill := preload("res://scenes/jobs/slime_puddle.tscn").instantiate()
	var world := get_tree().current_scene
	if world:
		world.add_child(spill)
		spill.global_position = Vector3(randf_range(-8.0, 8.0), 0.05, randf_range(-8.0, 8.0))
