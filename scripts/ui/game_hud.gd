extends Control

## Satisfaction meter, job board, round timer, and role HUD.

@onready var satisfaction_bar: ProgressBar = $MarginContainer/HBoxContainer/LeftColumn/SatisfactionBar
@onready var satisfaction_label: Label = $MarginContainer/HBoxContainer/LeftColumn/SatisfactionLabel
@onready var jobs_label: Label = $MarginContainer/HBoxContainer/LeftColumn/JobsLabel
@onready var timer_label: Label = $MarginContainer/HBoxContainer/LeftColumn/TimerLabel
@onready var role_label: Label = $MarginContainer/HBoxContainer/LeftColumn/RoleLabel
@onready var mission_hint_label: Label = $MarginContainer/HBoxContainer/LeftColumn/MissionHintLabel
@onready var stowaway_label: Label = $MarginContainer/HBoxContainer/LeftColumn/StowawayLabel
@onready var job_board_panel: PanelContainer = $MarginContainer/HBoxContainer/JobBoardPanel
@onready var job_board_toggle: Button = $MarginContainer/HBoxContainer/JobBoardPanel/MarginContainer/VBoxContainer/HeaderRow/JobBoardToggle
@onready var job_board_summary: Label = $MarginContainer/HBoxContainer/JobBoardPanel/MarginContainer/VBoxContainer/HeaderRow/JobBoardSummary
@onready var job_board_content: VBoxContainer = $MarginContainer/HBoxContainer/JobBoardPanel/MarginContainer/VBoxContainer/JobBoardContent
@onready var job_board: RichTextLabel = $MarginContainer/HBoxContainer/JobBoardPanel/MarginContainer/VBoxContainer/JobBoardContent/JobBoard
@onready var objective_label: Label = $MarginContainer/HBoxContainer/JobBoardPanel/MarginContainer/VBoxContainer/JobBoardContent/ObjectiveLabel

var _board_collapsed: bool = false
var _active_job_count: int = 0
var _objective_text: String = ""


func _ready() -> void:
	JobSystem.satisfaction_changed.connect(_on_satisfaction_changed)
	JobSystem.job_board_changed.connect(_on_job_board_changed)
	GameState.satisfaction_changed.connect(_on_satisfaction_changed)
	GameState.jobs_progress_changed.connect(_on_jobs_progress_changed)
	GameState.role_assigned.connect(_on_role_assigned)
	RoundManager.timer_updated.connect(_on_timer_updated)
	RoundManager.round_phase_changed.connect(func(_phase): _refresh_objective())
	RoundManager.shuttle_unlocked.connect(func(_s): _refresh_objective())
	job_board_toggle.pressed.connect(toggle_job_board)
	_refresh_all()


func toggle_job_board() -> void:
	_board_collapsed = not _board_collapsed
	job_board_content.visible = not _board_collapsed
	_update_board_header()


func _update_board_header() -> void:
	if _board_collapsed:
		job_board_toggle.text = "▶ Job Board"
		job_board_summary.visible = true
		job_board_summary.text = "%d active · %s" % [_active_job_count, _objective_text]
		job_board_panel.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	else:
		job_board_toggle.text = "▼ Job Board"
		job_board_summary.visible = false
		job_board_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL


func _refresh_all() -> void:
	_on_satisfaction_changed(GameState.corporate_satisfaction)
	_on_jobs_progress_changed(GameState.jobs_completed, GameState.jobs_required)
	_on_job_board_changed(JobSystem.get_active_jobs(), JobSystem.get_board_progress_text())
	_on_timer_updated(RoundManager.round_time_remaining, RoundManager.shuttle_time_remaining)
	_on_role_assigned(GameState.local_role)
	_update_board_header()


func _on_satisfaction_changed(value: float) -> void:
	satisfaction_bar.value = value
	satisfaction_label.text = "Corporate Satisfaction: %d%%" % int(value)


func _on_jobs_progress_changed(completed: int, required: int) -> void:
	jobs_label.text = "Jobs: %d / %d" % [completed, required]


func _on_timer_updated(round_seconds: float, shuttle_seconds: float) -> void:
	if RoundManager.shuttle_active:
		timer_label.text = "Shuttle leaves in: %s" % _format_time(shuttle_seconds)
	elif RoundManager.is_meeting_active():
		timer_label.text = "Meeting: %s" % _format_time(RoundManager.meeting_time_remaining)
	else:
		timer_label.text = "Round time: %s" % _format_time(round_seconds)
	if GameState.is_local_stowaway():
		_update_smuggle_label()


func _on_role_assigned(role: GameState.Role) -> void:
	if role == GameState.Role.STOWAWAY:
		role_label.text = "Role: STOWAWAY"
		role_label.modulate = Color(1.0, 0.45, 0.45)
		stowaway_label.visible = true
		_update_smuggle_label()
	else:
		role_label.text = "Role: Crew"
		role_label.modulate = Color(0.8, 1.0, 0.8)
		stowaway_label.visible = false
	mission_hint_label.text = JobSystem.get_role_briefing(role)
	_refresh_objective()


func _update_smuggle_label() -> void:
	var count: int = GameState.smuggle_counts.get(multiplayer.get_unique_id(), 0)
	stowaway_label.text = "Smuggled: %d / %d" % [count, StowawaySystem.SMUGGLE_QUOTA]


func _on_job_board_changed(active_jobs: Array, progress_text: String) -> void:
	_active_job_count = active_jobs.size()
	var lines: PackedStringArray = ["[b]Job Board[/b] — follow floor arrows from Main Hub", ""]
	for job in active_jobs:
		var zone: String = job.get("zone", "Station")
		lines.append("• [b]%s[/b]" % job.get("name", "Unknown"))
		lines.append("  [color=#aaccff]%s[/color]" % zone)
		if job.has("progress"):
			lines.append("  %s" % job.get("progress"))
		var hint: String = job.get("hint", "")
		if not hint.is_empty() and not bool(job.get("active", false)):
			lines.append("  [i]%s[/i]" % hint)
	job_board.text = "\n".join(lines)
	_refresh_objective(progress_text)


func _refresh_objective(custom_text: String = "") -> void:
	var text := custom_text if not custom_text.is_empty() else JobSystem.get_board_progress_text()
	_objective_text = text
	objective_label.text = text
	if GameState.is_local_stowaway():
		_update_smuggle_label()
	_update_board_header()


func _format_time(seconds: float) -> String:
	var total := maxi(int(seconds), 0)
	var minutes: int = int(total / 60.0)
	var secs: int = total % 60
	return "%d:%02d" % [minutes, secs]


func _unhandled_input(event: InputEvent) -> void:
	if not GameState.is_local_stowaway():
		return
	if not event is InputEventKey or not event.pressed:
		return
	var sabotage_id := ""
	match event.keycode:
		KEY_1:
			sabotage_id = "jazz"
		KEY_2:
			sabotage_id = "gravity"
		KEY_3:
			sabotage_id = "door"
		KEY_4:
			sabotage_id = "slime"
		KEY_5:
			sabotage_id = "shuttle_delay"
	if sabotage_id.is_empty():
		return
	StowawaySystem.request_sabotage(sabotage_id)
