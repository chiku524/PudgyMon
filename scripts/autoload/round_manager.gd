extends Node

## Server-authoritative round flow: roles, timers, meetings, win/lose.

signal round_started
signal round_phase_changed(phase: GameState.RoundPhase)
signal shuttle_unlocked(seconds_remaining: float)
signal meeting_started(seconds_remaining: float)
signal meeting_ended(written_up_peer_id: int)
signal round_ended(result: Dictionary)
signal timer_updated(round_seconds: float, shuttle_seconds: float)

const ROUND_DURATION := 1200.0
const SHUTTLE_DURATION := 180.0
const MEETING_DURATION := 90.0
const MAX_MEETINGS := 3
const SMUGGLE_QUOTA := 3

var round_time_remaining: float = 0.0
var shuttle_time_remaining: float = 0.0
var meeting_time_remaining: float = 0.0
var meetings_used: int = 0
var shuttle_active: bool = false
var _meeting_active: bool = false
var _votes: Dictionary = {}
var _round_running: bool = false


func _ready() -> void:
	multiplayer.connected_to_server.connect(_request_sync)


func _process(delta: float) -> void:
	if not multiplayer.is_server() or not _round_running:
		return

	if _meeting_active:
		meeting_time_remaining -= delta
		if meeting_time_remaining <= 0.0:
			_close_meeting()
		_broadcast_timer()
		return

	if shuttle_active:
		shuttle_time_remaining -= delta
		if shuttle_time_remaining <= 0.0:
			_end_round(_evaluate_shuttle_end())
		_check_stowaway_shuttle_win()
	else:
		round_time_remaining -= delta
		if round_time_remaining <= 0.0:
			_end_round({"winner": "none", "reason": "Corporate clock ran out."})

	_broadcast_timer()


func start_round(peer_ids: PackedInt32Array) -> void:
	if not multiplayer.is_server():
		return

	_reset_local()
	_assign_roles(peer_ids)
	StatsTracker.reset_stats()
	StowawaySystem.reset()
	round_time_remaining = ROUND_DURATION
	_round_running = true
	GameState.round_phase = GameState.RoundPhase.PLAYING
	JobSystem.reset_jobs()
	_broadcast_round_state()
	Announcer.bark_event("round_start")
	round_started.emit()
	round_phase_changed.emit(GameState.round_phase)


func add_shuttle_delay(seconds: float) -> void:
	if not multiplayer.is_server() or not shuttle_active:
		return
	shuttle_time_remaining += seconds
	_broadcast_timer()


func call_meeting(_caller_id: int) -> bool:
	if not multiplayer.is_server() or not _round_running or _meeting_active:
		return false
	if meetings_used >= MAX_MEETINGS:
		return false
	if GameState.round_phase != GameState.RoundPhase.PLAYING:
		return false

	_meeting_active = true
	meetings_used += 1
	meeting_time_remaining = MEETING_DURATION
	_votes.clear()
	GameState.round_phase = GameState.RoundPhase.MEETING
	_broadcast_round_state()
	StatsTracker.record_global("meetings", 1)
	Announcer.bark_event("meeting_called")
	meeting_started.emit(MEETING_DURATION)
	return true


func submit_vote(voter_id: int, target_id: int) -> void:
	if not multiplayer.is_server() or not _meeting_active:
		return
	if _votes.has(voter_id):
		return
	_votes[voter_id] = target_id


func deposit_smuggle(peer_id: int) -> bool:
	if not multiplayer.is_server():
		return false
	if not GameState.is_stowaway(peer_id):
		return false
	var count: int = GameState.smuggle_counts.get(peer_id, 0)
	count += 1
	GameState.smuggle_counts[peer_id] = count
	StatsTracker.record(peer_id, "smuggled", 1)
	Announcer.bark_event("stowaway_smuggle")
	_broadcast_round_state()
	return true


func on_satisfaction_depleted() -> void:
	if not multiplayer.is_server() or not _round_running:
		return
	_end_round({"winner": "stowaway", "reason": "Corporate Satisfaction hit zero."})


func check_shuttle_unlock() -> void:
	if not multiplayer.is_server() or shuttle_active:
		return
	if GameState.jobs_completed >= GameState.jobs_required:
		shuttle_active = true
		shuttle_time_remaining = SHUTTLE_DURATION
		GameState.round_phase = GameState.RoundPhase.EXTRACTION
		_broadcast_round_state()
		Announcer.bark_event("shuttle_open")
		shuttle_unlocked.emit(SHUTTLE_DURATION)
		round_phase_changed.emit(GameState.round_phase)


func register_shuttle_escape(peer_id: int) -> void:
	if not multiplayer.is_server() or not shuttle_active:
		return
	if peer_id not in GameState.escaped_peer_ids:
		GameState.escaped_peer_ids.append(peer_id)
	_broadcast_round_state()


func get_local_role() -> GameState.Role:
	return GameState.local_role


func is_meeting_active() -> bool:
	return _meeting_active


func _assign_roles(peer_ids: PackedInt32Array) -> void:
	var ids: Array[int] = []
	for peer_id in peer_ids:
		ids.append(peer_id)
	ids.shuffle()

	var stowaway_count := 1
	if ids.size() >= 8:
		stowaway_count = 2
	elif ids.size() >= 7:
		stowaway_count = 2

	for i in ids.size():
		var role := GameState.Role.STOWAWAY if i < stowaway_count else GameState.Role.CREW
		GameState.assign_role(ids[i], role)
		if ids[i] == multiplayer.get_unique_id():
			GameState.apply_local_role(role)
		else:
			_send_role_to_peer.rpc_id(ids[i], role)


func _close_meeting() -> void:
	var tally: Dictionary = {}
	var skip_votes := 0
	for voter_id in _votes:
		var target: int = _votes[voter_id]
		if target <= 0:
			skip_votes += 1
			continue
		tally[target] = tally.get(target, 0) + 1

	var written_up := -1
	var best_votes := 0
	for target_id in tally:
		if tally[target_id] > best_votes:
			best_votes = tally[target_id]
			written_up = target_id

	if written_up > 0:
		GameState.mark_written_up(written_up)
		if GameState.is_stowaway(written_up):
			GameState.stowaway_revealed = written_up
		Announcer.bark_event("written_up")
	elif skip_votes > 0:
		GameState.add_satisfaction(-5.0)

	_meeting_active = false
	GameState.round_phase = GameState.RoundPhase.PLAYING if not shuttle_active else GameState.RoundPhase.EXTRACTION
	_broadcast_round_state()
	meeting_ended.emit(written_up)


func _evaluate_shuttle_end() -> Dictionary:
	var crew_escaped := 0
	var stowaway_escaped := 0
	var stowaway_smuggled_enough := false

	for peer_id in GameState.escaped_peer_ids:
		if GameState.is_stowaway(peer_id):
			stowaway_escaped += 1
			if GameState.smuggle_counts.get(peer_id, 0) >= SMUGGLE_QUOTA:
				stowaway_smuggled_enough = true
		else:
			crew_escaped += 1

	if stowaway_smuggled_enough and stowaway_escaped > 0:
		return {"winner": "stowaway", "reason": "Contraband smuggled off-station."}

	if crew_escaped > 0 and GameState.stowaway_revealed > 0:
		return {"winner": "crew", "reason": "Crew escaped and the Stowaway was Written Up."}

	if crew_escaped > 0 and GameState.jobs_completed >= GameState.jobs_required:
		return {"winner": "crew", "reason": "Jobs done and crew reached the shuttle."}

	return {"winner": "none", "reason": "Nobody qualified for a corporate bonus."}


func _check_stowaway_shuttle_win() -> void:
	for peer_id in GameState.escaped_peer_ids:
		if GameState.is_stowaway(peer_id) and GameState.smuggle_counts.get(peer_id, 0) >= SMUGGLE_QUOTA:
			_end_round({"winner": "stowaway", "reason": "Stowaway escaped with contraband."})
			return


func _end_round(result: Dictionary) -> void:
	if not _round_running:
		return
	_round_running = false
	GameState.round_phase = GameState.RoundPhase.REVIEW
	result["jobs_completed"] = GameState.jobs_completed
	result["satisfaction"] = GameState.corporate_satisfaction
	result["meetings_used"] = meetings_used
	result["stats"] = StatsTracker.build_summary()
	match result.get("winner", "none"):
		"crew":
			Announcer.bark_event("round_crew_win")
		"stowaway":
			Announcer.bark_event("round_stowaway_win")
		_:
			Announcer.bark_event("round_fail")
	_broadcast_round_state()
	round_phase_changed.emit(GameState.round_phase)
	round_ended.emit(result)


func _reset_local() -> void:
	round_time_remaining = ROUND_DURATION
	shuttle_time_remaining = 0.0
	meeting_time_remaining = 0.0
	meetings_used = 0
	shuttle_active = false
	_meeting_active = false
	_votes.clear()
	_round_running = false
	GameState.reset_round()


func _broadcast_timer() -> void:
	_sync_timer.rpc(round_time_remaining, shuttle_time_remaining, meeting_time_remaining)


func _broadcast_round_state() -> void:
	_sync_round_state.rpc(
		round_time_remaining,
		shuttle_time_remaining,
		meeting_time_remaining,
		meetings_used,
		shuttle_active,
		_meeting_active,
		GameState.round_phase,
		GameState.jobs_completed,
		GameState.corporate_satisfaction,
		GameState.stowaway_revealed,
		GameState.written_up_peer_ids,
		GameState.smuggle_counts,
		GameState.escaped_peer_ids
	)
	timer_updated.emit(round_time_remaining, shuttle_time_remaining)


func _request_sync() -> void:
	if multiplayer.is_server():
		return
	_request_full_round_state.rpc_id(1)


@rpc("any_peer", "call_remote", "reliable")
func _request_full_round_state() -> void:
	if not multiplayer.is_server():
		return
	_broadcast_round_state()
	_broadcast_timer()


@rpc("authority", "call_remote", "reliable")
func _send_role_to_peer(role: GameState.Role) -> void:
	GameState.apply_local_role(role)


@rpc("authority", "call_remote", "reliable")
func _sync_timer(round_seconds: float, shuttle_seconds: float, meeting_seconds: float) -> void:
	round_time_remaining = round_seconds
	shuttle_time_remaining = shuttle_seconds
	meeting_time_remaining = meeting_seconds
	timer_updated.emit(round_time_remaining, shuttle_time_remaining)


@rpc("authority", "call_remote", "reliable")
func _sync_round_state(
	round_seconds: float,
	shuttle_seconds: float,
	meeting_seconds: float,
	used_meetings: int,
	shuttle_is_active: bool,
	meeting_is_active: bool,
	phase: GameState.RoundPhase,
	jobs_done: int,
	satisfaction: float,
	revealed_stowaway: int,
	written_up: Dictionary,
	smuggle_counts: Dictionary,
	escaped: Array
) -> void:
	round_time_remaining = round_seconds
	shuttle_time_remaining = shuttle_seconds
	meeting_time_remaining = meeting_seconds
	meetings_used = used_meetings
	shuttle_active = shuttle_is_active
	_meeting_active = meeting_is_active
	GameState.round_phase = phase
	GameState.jobs_completed = jobs_done
	GameState.corporate_satisfaction = satisfaction
	GameState.stowaway_revealed = revealed_stowaway
	GameState.written_up_peer_ids = written_up.duplicate(true)
	GameState.smuggle_counts = smuggle_counts.duplicate(true)
	GameState.escaped_peer_ids = escaped.duplicate()
	GameState.satisfaction_changed.emit(GameState.corporate_satisfaction)
	GameState.jobs_progress_changed.emit(GameState.jobs_completed, GameState.jobs_required)
	timer_updated.emit(round_time_remaining, shuttle_time_remaining)
