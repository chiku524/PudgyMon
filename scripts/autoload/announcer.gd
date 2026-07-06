extends Node

## PA announcer barks for ShipHappens.

signal bark_displayed(text: String)

const BARKS := {
	"round_start": "Mission start: complete 7 jobs, then evac north. Job Kiosk is your first stop.",
	"job_started": "A new task has entered your life. Good luck.",
	"job_complete": "Corporate Satisfaction slightly less doomed.",
	"shuttle_open": "Shuttle bay open. Try not to miss the ramp.",
	"meeting_called": "Emergency Stand-Up Meeting. Bring your accusations.",
	"sabotage_jazz": "Mandatory jazz break initiated.",
	"sabotage_slime": "Slime spill detected. Mop optional.",
	"sabotage_gravity": "Gravity hiccup in progress. Bonk responsibly.",
	"sabotage_door": "Door labels may or may not be lies.",
	"sabotage_shuttle": "Shuttle paperwork delayed. Blame someone.",
	"stowaway_smuggle": "Unregistered cargo detected. Probably fine.",
	"written_up": "HR has entered the chat.",
	"round_crew_win": "Performance adequate. Barely.",
	"round_stowaway_win": "Contraband wins again. HR is crying.",
	"round_fail": "Everyone is fired. Please vacate the station.",
	"low_satisfaction": "Corporate Satisfaction critical. Panic politely.",
}

var _last_bark_time: float = 0.0


func bark_event(event_key: String) -> void:
	if not BARKS.has(event_key):
		return
	var now := Time.get_ticks_msec() / 1000.0
	if now - _last_bark_time < 2.0:
		return
	_last_bark_time = now
	var text: String = BARKS[event_key]
	_show_bark(text)


func bark_custom(text: String) -> void:
	_show_bark(text)


func _show_bark(text: String) -> void:
	if multiplayer.is_server():
		bark_displayed.emit(text)
	_display.rpc(text)


@rpc("authority", "call_remote", "reliable")
func _display(text: String) -> void:
	if multiplayer.is_server():
		return
	bark_displayed.emit(text)
