extends Node

## Server-authoritative job tracking — all 10 station jobs.

signal satisfaction_changed(value: float)
signal job_board_changed(active_jobs: Array, progress_text: String)
signal job_completed(job_id: String)
signal paperwork_state_changed(active: bool, forms_fed: int, complete: bool)

const PAPERWORK_JOB_ID := "paperwork_avalanche"
const POWER_HOUR_JOB_ID := "power_hour"
const MOP_JOB_ID := "mop_the_future"
const MANIFEST_JOB_ID := "manifest_lies"
const CRANE_JOB_ID := "crane_of_regret"
const COOLANT_JOB_ID := "coolant_gargle"
const DISH_JOB_ID := "dish_go_brr"
const TRUST_FALL_JOB_ID := "trust_fall"
const VENDING_JOB_ID := "vending_restock"
const DUCT_TAPE_JOB_ID := "duct_tape"

const ALL_JOB_IDS: Array[String] = [
	PAPERWORK_JOB_ID,
	POWER_HOUR_JOB_ID,
	MOP_JOB_ID,
	MANIFEST_JOB_ID,
	CRANE_JOB_ID,
	COOLANT_JOB_ID,
	DISH_JOB_ID,
	TRUST_FALL_JOB_ID,
	VENDING_JOB_ID,
	DUCT_TAPE_JOB_ID,
]

const JOB_NAMES := {
	PAPERWORK_JOB_ID: "Paperwork Avalanche",
	POWER_HOUR_JOB_ID: "Power Hour",
	MOP_JOB_ID: "Mop the Future",
	MANIFEST_JOB_ID: "Manifest Lies",
	CRANE_JOB_ID: "Crane of Regret",
	COOLANT_JOB_ID: "Coolant Gargle",
	DISH_JOB_ID: "Dish Go Brr",
	TRUST_FALL_JOB_ID: "Trust Fall Certification",
	VENDING_JOB_ID: "Vending Restock",
	DUCT_TAPE_JOB_ID: "Duct Tape OR ELSE",
}

const JOB_SATISFACTION := {
	PAPERWORK_JOB_ID: 6.0,
	POWER_HOUR_JOB_ID: 7.0,
	MOP_JOB_ID: 5.0,
	MANIFEST_JOB_ID: 8.0,
	CRANE_JOB_ID: 12.0,
	COOLANT_JOB_ID: 8.0,
	DISH_JOB_ID: 10.0,
	TRUST_FALL_JOB_ID: 10.0,
	VENDING_JOB_ID: 6.0,
	DUCT_TAPE_JOB_ID: 12.0,
}

const JOB_TARGETS := {
	PAPERWORK_JOB_ID: 5,
	POWER_HOUR_JOB_ID: 4,
	MOP_JOB_ID: 8,
	MANIFEST_JOB_ID: 2,
	CRANE_JOB_ID: 3,
	COOLANT_JOB_ID: 100,
	DISH_JOB_ID: 100,
	TRUST_FALL_JOB_ID: 3,
	VENDING_JOB_ID: 3,
	DUCT_TAPE_JOB_ID: 5,
}

const PAPERWORK_FORMS_REQUIRED := 5
const MOP_PUDDLES_REQUIRED := 8
const MANIFEST_CRATES_REQUIRED := 2
const POWER_HOUR_SEQUENCE := [0, 2, 1, 3]

var job_states: Dictionary = {}


func _ready() -> void:
	multiplayer.connected_to_server.connect(_on_connected_to_server)
	_init_states()


func _init_states() -> void:
	job_states.clear()
	for job_id in ALL_JOB_IDS:
		job_states[job_id] = {"active": false, "complete": false, "progress": 0}


func reset_jobs() -> void:
	if multiplayer.is_server():
		_reset_local()
		_broadcast_state()
	else:
		_request_reset.rpc_id(1)


func _reset_local() -> void:
	_init_states()
	GameState.jobs_completed = 0
	GameState.corporate_satisfaction = 100.0
	_emit_board()


func is_active(job_id: String) -> bool:
	return bool(job_states.get(job_id, {}).get("active", false))


func is_job_complete(job_id: String) -> bool:
	return bool(job_states.get(job_id, {}).get("complete", false))


func get_progress(job_id: String) -> int:
	return int(job_states.get(job_id, {}).get("progress", 0))


func set_progress(job_id: String, value: int) -> void:
	if not job_states.has(job_id):
		return
	job_states[job_id]["progress"] = value
	_broadcast_state()


func start_job(job_id: String) -> bool:
	if not multiplayer.is_server() or is_job_complete(job_id) or is_active(job_id):
		return false
	if not job_states.has(job_id):
		return false
	job_states[job_id]["active"] = true
	job_states[job_id]["progress"] = 0
	_broadcast_state()
	Announcer.bark_event("job_started")
	return true


func add_progress(job_id: String, amount: int = 1) -> bool:
	if not multiplayer.is_server() or not is_active(job_id) or is_job_complete(job_id):
		return false
	var target: int = JOB_TARGETS.get(job_id, 1)
	job_states[job_id]["progress"] = mini(get_progress(job_id) + amount, target)
	if get_progress(job_id) >= target:
		complete_job(job_id)
	else:
		_broadcast_state()
	return true


func complete_job(job_id: String) -> bool:
	if not multiplayer.is_server() or is_job_complete(job_id):
		return false
	job_states[job_id]["active"] = false
	job_states[job_id]["complete"] = true
	GameState.jobs_completed += 1
	GameState.add_satisfaction(JOB_SATISFACTION.get(job_id, 5.0))
	GameState.jobs_progress_changed.emit(GameState.jobs_completed, GameState.jobs_required)
	StatsTracker.record_global("jobs_completed", 1)
	_broadcast_state()
	job_completed.emit(job_id)
	Announcer.bark_event("job_complete")
	RoundManager.check_shuttle_unlock()
	return true


func start_paperwork_job(_requester_id: int) -> bool:
	return start_job(PAPERWORK_JOB_ID)


func feed_paperwork_form() -> bool:
	if not multiplayer.is_server() or not is_active(PAPERWORK_JOB_ID):
		return false
	if get_progress(PAPERWORK_JOB_ID) >= PAPERWORK_FORMS_REQUIRED:
		return false
	job_states[PAPERWORK_JOB_ID]["progress"] += 1
	_broadcast_state()
	return true


func complete_paperwork_job() -> bool:
	if not is_active(PAPERWORK_JOB_ID) or get_progress(PAPERWORK_JOB_ID) < PAPERWORK_FORMS_REQUIRED:
		return false
	return complete_job(PAPERWORK_JOB_ID)


func try_power_hour_breaker(breaker_index: int) -> Dictionary:
	if not is_active(POWER_HOUR_JOB_ID) or is_job_complete(POWER_HOUR_JOB_ID):
		return {"ok": false}
	var step := get_progress(POWER_HOUR_JOB_ID)
	if breaker_index == POWER_HOUR_SEQUENCE[step]:
		job_states[POWER_HOUR_JOB_ID]["progress"] = step + 1
		if get_progress(POWER_HOUR_JOB_ID) >= POWER_HOUR_SEQUENCE.size():
			complete_job(POWER_HOUR_JOB_ID)
		else:
			_broadcast_state()
		return {"ok": true, "done": is_job_complete(POWER_HOUR_JOB_ID)}
	_broadcast_state()
	return {"ok": false, "zap": true}


func clean_mop_puddle() -> bool:
	return add_progress(MOP_JOB_ID, 1)


func scan_manifest_crate() -> bool:
	return add_progress(MANIFEST_JOB_ID, 1)


func get_active_jobs() -> Array:
	var jobs: Array = []
	for job_id in ALL_JOB_IDS:
		if is_job_complete(job_id):
			continue
		jobs.append({
			"id": job_id,
			"name": JOB_NAMES[job_id],
			"progress": _job_progress_text(job_id),
		})
	return jobs.slice(0, 3)


func get_board_progress_text() -> String:
	if GameState.round_phase == GameState.RoundPhase.EXTRACTION:
		return "Shuttle bay open — get to the yellow ramp!"
	if GameState.round_phase == GameState.RoundPhase.MEETING:
		return "Emergency Stand-Up Meeting in progress."
	if GameState.jobs_completed >= GameState.jobs_required:
		return "Required jobs done — shuttle is available."
	return "Complete 7 jobs across the station. Watch for the Stowaway."


func _job_progress_text(job_id: String) -> String:
	if is_active(job_id):
		return "%d/%d" % [get_progress(job_id), JOB_TARGETS.get(job_id, 1)]
	return "Available at station"


func _broadcast_state() -> void:
	_sync_state.rpc(job_states.duplicate(true), GameState.corporate_satisfaction, GameState.jobs_completed)


func _emit_board() -> void:
	var jobs := get_active_jobs()
	job_board_changed.emit(jobs, get_board_progress_text())
	paperwork_state_changed.emit(
		is_active(PAPERWORK_JOB_ID),
		get_progress(PAPERWORK_JOB_ID),
		is_job_complete(PAPERWORK_JOB_ID)
	)
	satisfaction_changed.emit(GameState.corporate_satisfaction)


func _on_connected_to_server() -> void:
	_request_full_state.rpc_id(1)


@rpc("any_peer", "call_remote", "reliable")
func _request_reset() -> void:
	if not multiplayer.is_server():
		return
	_reset_local()
	_broadcast_state()


@rpc("any_peer", "call_remote", "reliable")
func _request_full_state() -> void:
	if not multiplayer.is_server():
		return
	_broadcast_state()


@rpc("authority", "call_remote", "reliable")
func _sync_state(states: Dictionary, satisfaction: float, jobs_done: int) -> void:
	job_states = states.duplicate(true)
	GameState.corporate_satisfaction = satisfaction
	GameState.jobs_completed = jobs_done
	_emit_board()


# Backward-compatible accessors used by existing Phase 2 scripts.
var paperwork_active: bool:
	get: return is_active(PAPERWORK_JOB_ID)

var paperwork_complete: bool:
	get: return is_job_complete(PAPERWORK_JOB_ID)

var forms_fed: int:
	get: return get_progress(PAPERWORK_JOB_ID)

var power_hour_active: bool:
	get: return is_active(POWER_HOUR_JOB_ID)

var power_hour_complete: bool:
	get: return is_job_complete(POWER_HOUR_JOB_ID)

var power_hour_step: int:
	get: return get_progress(POWER_HOUR_JOB_ID)

var mop_active: bool:
	get: return is_active(MOP_JOB_ID)

var mop_complete: bool:
	get: return is_job_complete(MOP_JOB_ID)

var mop_cleaned: int:
	get: return get_progress(MOP_JOB_ID)

var manifest_active: bool:
	get: return is_active(MANIFEST_JOB_ID)

var manifest_complete: bool:
	get: return is_job_complete(MANIFEST_JOB_ID)

var manifest_scanned: int:
	get: return get_progress(MANIFEST_JOB_ID)
