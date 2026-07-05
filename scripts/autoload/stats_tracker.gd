extends Node

## Tracks per-player and global round stats for the post-round screen.

var _player_stats: Dictionary = {}
var _global_stats: Dictionary = {
	"jobs_completed": 0,
	"sabotages": 0,
	"meetings": 0,
	"bonks": 0,
}


func reset_stats() -> void:
	_player_stats.clear()
	_global_stats = {
		"jobs_completed": 0,
		"sabotages": 0,
		"meetings": 0,
		"bonks": 0,
	}


func record(peer_id: int, stat_name: String, amount: int = 1) -> void:
	if not _player_stats.has(peer_id):
		_player_stats[peer_id] = {
			"bonks": 0,
			"smuggled": 0,
			"escaped": false,
			"votes_cast": 0,
		}
	_player_stats[peer_id][stat_name] = _player_stats[peer_id].get(stat_name, 0) + amount


func record_global(stat_name: String, amount: int = 1) -> void:
	_global_stats[stat_name] = _global_stats.get(stat_name, 0) + amount


func build_summary() -> Dictionary:
	var lines: PackedStringArray = []
	lines.append("[b]Round Stats[/b]")
	lines.append("Jobs completed: %d" % _global_stats.get("jobs_completed", 0))
	lines.append("Sabotages triggered: %d" % _global_stats.get("sabotages", 0))
	lines.append("Emergency meetings: %d" % _global_stats.get("meetings", 0))
	lines.append("Total bonks: %d" % _global_stats.get("bonks", 0))
	lines.append("")
	for peer_id in _player_stats.keys():
		var data: Dictionary = _player_stats[peer_id]
		lines.append("Player %d — bonks: %d, smuggled: %d" % [
			peer_id,
			data.get("bonks", 0),
			data.get("smuggled", 0),
		])
	return {
		"text": "\n".join(lines),
		"global": _global_stats.duplicate(true),
		"players": _player_stats.duplicate(true),
	}
