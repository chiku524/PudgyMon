extends Node

## Session and round state for ShipHappens (expanded in Phase 2).

enum Role { CREW, STOWAWAY }

enum RoundPhase { LOBBY, PLAYING, MEETING, EXTRACTION, REVIEW }

var local_player_name: String = "Crew Member"
var round_phase: RoundPhase = RoundPhase.LOBBY
var corporate_satisfaction: float = 100.0
var jobs_completed: int = 0
var jobs_required: int = 7

var _player_roles: Dictionary = {}


func reset_round() -> void:
	round_phase = RoundPhase.LOBBY
	corporate_satisfaction = 100.0
	jobs_completed = 0
	_player_roles.clear()


func set_local_player_name(player_name: String) -> void:
	var trimmed := player_name.strip_edges()
	local_player_name = trimmed if not trimmed.is_empty() else "Crew Member"


func assign_role(peer_id: int, role: Role) -> void:
	_player_roles[peer_id] = role


func get_role(peer_id: int) -> Role:
	return _player_roles.get(peer_id, Role.CREW)


func is_stowaway(peer_id: int) -> bool:
	return get_role(peer_id) == Role.STOWAWAY
