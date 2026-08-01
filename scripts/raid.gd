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
var kills: Array[Dictionary] = []    # {name, player, bone, at (seconds)}
var haul: Array[Dictionary] = []     # {name, count} — the stash lands in M4

var _started_ms := 0
var _ended_at := 0.0


func begin() -> void:
	running = true
	xp = 0
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
