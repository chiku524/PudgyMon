extends Node

## Session and round state for ShipHappens.

enum Role { CREW, STOWAWAY }

enum RoundPhase { LOBBY, PLAYING, MEETING, EXTRACTION, REVIEW }

signal satisfaction_changed(value: float)
signal jobs_progress_changed(completed: int, required: int)
signal role_assigned(role: Role)
signal written_up_changed(peer_id: int, active: bool)

var local_player_name: String = "Crew Member"
var local_role: Role = Role.CREW
var round_phase: RoundPhase = RoundPhase.LOBBY
var corporate_satisfaction: float = 100.0
var jobs_completed: int = 0
var jobs_required: int = 7
var stowaway_revealed: int = -1
var written_up_peer_ids: Dictionary[int, float] = {}
var smuggle_counts: Dictionary[int, int] = {}
var escaped_peer_ids: Array[int] = []

var _player_roles: Dictionary[int, Role] = {}


func reset_round() -> void:
	round_phase = RoundPhase.LOBBY
	local_role = Role.CREW
	corporate_satisfaction = 100.0
	jobs_completed = 0
	stowaway_revealed = -1
	written_up_peer_ids.clear()
	smuggle_counts.clear()
	escaped_peer_ids.clear()
	_player_roles.clear()
	satisfaction_changed.emit(corporate_satisfaction)
	jobs_progress_changed.emit(jobs_completed, jobs_required)


func add_satisfaction(amount: float) -> void:
	corporate_satisfaction = clampf(corporate_satisfaction + amount, 0.0, 100.0)
	satisfaction_changed.emit(corporate_satisfaction)
	if corporate_satisfaction <= 0.0:
		RoundManager.on_satisfaction_depleted()


func set_local_player_name(player_name: String) -> void:
	var trimmed := player_name.strip_edges()
	local_player_name = trimmed if not trimmed.is_empty() else "Crew Member"


func assign_role(peer_id: int, role: Role) -> void:
	_player_roles[peer_id] = role


func apply_local_role(role: Role) -> void:
	local_role = role
	role_assigned.emit(role)


func get_role(peer_id: int) -> Role:
	return _player_roles.get(peer_id, Role.CREW)


func is_stowaway(peer_id: int) -> bool:
	return get_role(peer_id) == Role.STOWAWAY


func is_local_stowaway() -> bool:
	return local_role == Role.STOWAWAY


func mark_written_up(peer_id: int, duration_seconds: float = 120.0) -> void:
	written_up_peer_ids[peer_id] = Time.get_unix_time_from_system() + duration_seconds
	written_up_changed.emit(peer_id, true)


func is_written_up(peer_id: int) -> bool:
	if not written_up_peer_ids.has(peer_id):
		return false
	if Time.get_unix_time_from_system() > int(written_up_peer_ids[peer_id]):
		written_up_peer_ids.erase(peer_id)
		written_up_changed.emit(peer_id, false)
		return false
	return true


func get_peer_ids() -> Array:
	return _player_roles.keys()
