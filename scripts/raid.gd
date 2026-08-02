extends Node
## Raid bookkeeping (autoload "Raid"). One raid's worth of facts: when it
## started, what you earned, and who you put down — the summary screen
## reads all of it when you extract.
##
## Kills are recorded with the MINUTE they happened and the BONE that
## ended it (user spec), so the debrief reads like a report rather than
## a number. Nothing kills anybody yet — M3 brings the strays — but the
## ledger is here so the screen is real the day they arrive.

var running := false
var xp := 0
# STUB currency until the stash and the economy land in M4: you start a
# raid with a little walking-around money so the toll gate is usable.
# When the stash arrives this moves there and persists between raids.
var money := 120
var kills: Array[Dictionary] = []    # {name, player, bone, at (seconds)}
var haul: Array[Dictionary] = []     # {name, count} — the stash lands in M4

# THE WORLD CLOCK, 0..1. Shared by the menu and the raid so the time the
# map-select screen shows is the time you actually deploy into (user
# call), and it keeps running while you sit in the menu — the district
# does not wait for you. The environment owns the real length and pushes
# it here on setup, so there is still ONE source for the day length.
var world_time := 0.30          # a raid starts mid-morning, 07:12
var day_seconds := 1080.0
# dusk / dawn, mirroring environment_system's gradient stops
const NIGHT_FROM := 0.875       # 21:00, dusk — the light starts closing
const NIGHT_UNTIL := 0.229      # 05:30, halfway up the dawn ramp: before
                                # that it still reads dark on screen

var _started_ms := 0
var _ended_at := 0.0


func advance_clock(delta: float) -> void:
	world_time = fmod(world_time + delta / day_seconds, 1.0)


func time_label() -> String:
	var minutes := int(world_time * 1440.0) % 1440
	@warning_ignore("integer_division")
	return "%02d:%02d" % [minutes / 60, minutes % 60]


func is_night() -> bool:
	return world_time >= NIGHT_FROM or world_time < NIGHT_UNTIL


func begin() -> void:
	running = true
	xp = 0
	money = 120
	kills.clear()
	haul.clear()
	_started_ms = Time.get_ticks_msec()
	_ended_at = 0.0


func end() -> void:
	if running:
		_ended_at = elapsed()
	running = false


func elapsed() -> float:
	if not running:
		return _ended_at
	return float(Time.get_ticks_msec() - _started_ms) / 1000.0


func add_xp(amount: int) -> void:
	xp += amount


func record_kill(who: String, bone: String, is_player: bool = false) -> void:
	kills.append({"name": who, "bone": bone, "player": is_player,
		"at": elapsed()})
	add_xp(120 if is_player else 40)


func player_kills() -> int:
	var n := 0
	for k in kills:
		if bool(k["player"]):
			n += 1
	return n


func clock(seconds: float) -> String:
	return "%02d:%02d" % [int(seconds) / 60, int(seconds) % 60]
