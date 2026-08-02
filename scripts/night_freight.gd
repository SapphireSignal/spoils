class_name NightFreight
extends Node2D
## The night freight: the one train still running in transit. She keeps to
## the IN-GAME CLOCK, not a stopwatch — she slides into the yard at
## midnight, stands for one real minute, and goes whether you're aboard or
## not. Only that sixty-second platform wait is real time.
##
## She does NOT run every night (user call 2026-08-01): three nights out of
## every seven, drawn fresh each week. So miss her and the next one is at
## least a full day/night cycle off and can be several — walking may be
## quicker. The whistle and the corner notice exist so you're never
## guessing where she is inside that minute.
##
## (This header used to say "every five minutes… timing is REAL time",
## which the clock block directly below it has contradicted since
## 2026-08-01.)

signal extracted(method: String)

## THE CLOCK RUNS IT (user call 2026-08-01): she arrives at 24:00, the
## darkest point of the night, every in-game day — not on a real-time
## cycle, and never in daylight. ARRIVE_AT is a fraction of the day, so
## a longer day cycle just means a longer wait for her.
const ARRIVE_AT := 0.0         # midnight — day_time wraps 0..1
const WARN_AT := 0.985         # mara calls it in a little before
const ARRIVE_TIME := 9.0       # the slide into the yard
const WAIT_TIME := 60.0        # one real minute standing
const WARN_LEAD := 18.0        # whistle this long before it appears
const BOARD_RANGE := 96.0      # the length of a carriage, near enough
const DEPART_COUNT := 10       # "departing in 10..."
const RAIL_DIR := Vector2(0.8944, 0.4472)   # +x along the iso rail

enum { AWAY, ARRIVING, WAITING, DEPARTING, GONE }

var state := AWAY
var boarded := false
var _hull: StaticBody2D        # the rake's collision; off while you ride it

var _stop_pos := Vector2.ZERO
var _clock := 0.0              # seconds into the current cycle
var _speed := 0.0
var _count_left := 0.0
var _warned := false
var _half_called := false
var _player: Player
var _radio: Radio
var _environment: Node          # owns day_time — the freight runs on it
var _last_day := -1.0           # so midnight only triggers once per day
# she does NOT run every night (user call): three nights out of every
# seven, on whatever days they happen to fall — they can bunch at the
# start of a week or straggle to the end of it
var _nights_seen := 0
var _week_nights: Array[int] = []
var _week_rng := RandomNumberGenerator.new()
var _notice: Label
var _countdown: Label
var _steam_tex: Texture2D
var _steam_timer := 0.0
var _puffs: Array[Dictionary] = []
var _notice_shown := -1        # last second on each label — text re-shapes
var _count_shown := -1         # only when the number actually changes


func _radio_say(text: String) -> void:
	if _radio != null:
		_radio.say(text)


func setup(stop_pos: Vector2, player: Player, radio: Radio,
		manifest: Dictionary, environment: Node) -> void:
	_stop_pos = stop_pos
	_player = player
	_radio = radio
	_environment = environment
	position = _stop_pos - RAIL_DIR * 2600.0
	visible = false
	_clock = 0.0
	_week_rng.randomize()
	_roll_week()

	# origins come from the manifest like every other prop — guessing them
	# put the hauled cars off the rails. The builder already parsed the
	# json; re-reading 137 KB here used to stall the deploy tail.
	var props: Dictionary = manifest.get("props", {})
	var rake := ["locomotive", "boxcar_x_0", "boxcar_x_2"]
	var back := 0.0
	for prop_name in rake:
		var sprite := Sprite2D.new()
		sprite.texture = load("res://art/gen/%s.png" % prop_name)
		sprite.centered = false
		var origin: Array = (props.get(prop_name, {}) as Dictionary).get(
			"origin", [48, 60])
		sprite.offset = Vector2(-float(origin[0]), -float(origin[1]))
		# every rail sprite sits on the same (2,1) axis, so the rake just
		# steps back along it, each car behind the last
		sprite.position = (-RAIL_DIR * back).round()
		add_child(sprite)
		back += 104.0

	# THE RAKE IS SOLID. It was three sprites and nothing else, so you could
	# walk — or drive — straight through the train you are supposed to board
	# (user). One parallelogram per car, laid along the rail axis.
	_hull = StaticBody2D.new()
	_hull.name = "Hull"
	add_child(_hull)
	# ONE continuous hull, nose to tail, instead of a quad per car.
	#
	# Per-car quads left two kinds of gap and the user found both: they
	# started at each car's ORIGIN, but the locomotive's art reaches ~46 px
	# PAST its origin, so you could walk straight through the front of the
	# engine; and the cars sit 104 apart while each quad was only 96 long,
	# leaving a slot between every pair. A train is one solid object —
	# model it as one.
	var across := Vector2(RAIL_DIR.x, -RAIL_DIR.y) * 16.0
	# extents measured off the manifest art, converted from screen px to
	# distance along the rail (RAIL_DIR.x is 0.894, not 1)
	var nose := 46.0 / RAIL_DIR.x
	var tail_len := (104.0 * float(rake.size() - 1)) + (42.0 / RAIL_DIR.x)
	var head := RAIL_DIR * nose
	var tail := -RAIL_DIR * tail_len
	var poly := CollisionPolygon2D.new()
	poly.polygon = PackedVector2Array([head - across, tail - across,
		tail + across, head + across])
	_hull.add_child(poly)

	# it runs at night, so it has to carry its own light: a headlamp
	# throwing down the rails, and a warm spill out of the cab windows
	var lamp := PointLight2D.new()
	lamp.texture = load("res://art/gen/light_cone.png")
	lamp.offset = Vector2(128.0, 0.0)
	lamp.color = Color("e7d5b3")
	lamp.energy = 1.25
	lamp.rotation = RAIL_DIR.angle() + PI      # it points the way it came
	lamp.position = Vector2(-46.0, -18.0)
	add_child(lamp)
	var cab := PointLight2D.new()
	cab.texture = load("res://art/gen/light_radial.png")
	cab.color = Color("e8c170")
	cab.energy = 0.75
	cab.texture_scale = 0.7
	cab.position = Vector2(18.0, -26.0)
	add_child(cab)
	_steam_tex = load("res://art/gen/fog_1.png")
	add_to_group("trains")
	add_to_group("hud")     # her notices come down behind a window too

	var layer := CanvasLayer.new()
	layer.layer = 73
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_notice = Label.new()
	_notice.theme = UITheme.get_theme()
	_notice.add_theme_color_override("font_color", Color("de9e41"))
	# TOP CENTRE, not top right: the fps counter lives in the right corner
	# and the two were printing over each other (user). Fractional anchors
	# so it stays centred at any resolution.
	_notice.anchor_left = 0.5
	_notice.anchor_right = 0.5
	_notice.anchor_top = 0.0
	_notice.anchor_bottom = 0.0
	_notice.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_notice.offset_top = 8
	_notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_notice.visible = false
	root.add_child(_notice)
	_countdown = Label.new()
	_countdown.theme = UITheme.get_theme()
	_countdown.add_theme_color_override("font_color", Color("75a743"))
	_countdown.anchor_left = 0.5
	_countdown.anchor_right = 0.5
	_countdown.anchor_top = 0.30
	_countdown.anchor_bottom = 0.30
	_countdown.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_countdown.grow_vertical = Control.GROW_DIRECTION_BOTH
	_countdown.visible = false
	root.add_child(_countdown)
	layer.add_child(root)
	add_child(layer)


func _roll_week() -> void:
	## three running nights out of the seven, drawn without replacement so
	## they land wherever they land — two together at the start of a week
	## and one at the far end is a perfectly good week
	_week_nights.clear()
	var days := [0, 1, 2, 3, 4, 5, 6]
	for i in 3:
		var pick := _week_rng.randi_range(0, days.size() - 1)
		_week_nights.append(days[pick])
		days.remove_at(pick)


func _runs_on(night: int) -> bool:
	return _week_nights.has(night % 7)


func force_waiting() -> void:
	## harness hook: put it in the yard now instead of waiting out the
	## real-time cycle
	visible = true
	position = _stop_pos
	state = WAITING
	_clock = 0.0
	_half_called = false


func can_board() -> bool:
	return state == WAITING and not boarded


func board() -> void:
	if not can_board():
		return
	boarded = true
	# you're inside it now: a solid hull riding with you would only fight
	# the weld that keeps you aboard
	if _hull != null:
		_hull.collision_layer = 0
	_player.board_ride(self, Vector2(0.0, -18.0))
	_count_left = float(DEPART_COUNT)
	Sfx.play_door(false)
	# riding out past the wire is a LEGITIMATE exit — the marksmen were
	# still shooting at the train (user report). Same stand-down the toll
	# gate buys, except this one you earned by catching the freight.
	var guard := get_tree().current_scene.get_node_or_null("EdgeGuard")
	if guard != null:
		guard.set("stood_down", true)
	_radio_say("good. stay down and stay in the car until she's clear of "
		+ "the wire. see you at the depot, magpie.")


func _process(delta: float) -> void:
	if state != AWAY and state != GONE:
		_steam(delta)
	if state == GONE:
		return
	_clock += delta
	match state:
		AWAY:
			# the in-game clock decides, not a stopwatch: she is a NIGHT
			# freight and she keeps to the timetable (user call)
			var day: float = _environment.get("day_time") if _environment != null else 0.0
			var wrapped := day < _last_day - 0.5   # the clock passed 24:00
			_last_day = day
			if wrapped:
				_nights_seen += 1
				if _nights_seen % 7 == 0:
					_roll_week()               # a fresh timetable each week
			# ...and only on the nights she actually runs
			if not _warned and day >= WARN_AT and _runs_on(_nights_seen + 1):
				# she is called in just BEFORE midnight, so the warning and
				# the arrival are the same event from the raider's side
				_warned = true
				Sfx.play_horn()
				_radio_say("magpie, ive got a freight inbound to the "
					+ "trainyard. give or take.")
			elif _warned and wrapped:
				_warned = false
				_clock = 0.0
				state = ARRIVING
				visible = true
				Sfx.play_horn()
		ARRIVING:
			var t := clampf(_clock / ARRIVE_TIME, 0.0, 1.0)
			# eases in and brakes to a stand
			position = (_stop_pos - RAIL_DIR * 2600.0).lerp(_stop_pos,
				1.0 - pow(1.0 - t, 3.0))
			if t >= 1.0:
				_clock = 0.0
				state = WAITING
				_half_called = false
				Sfx.play_door(true)
				_radio_say("she's in. one minute on the platform, magpie. "
					+ "she does not wait for anybody, including me.")
		WAITING:
			if boarded:
				_tick_countdown(delta)
			else:
				var left := WAIT_TIME - _clock
				if not _half_called and left <= 25.0:
					_half_called = true
					_radio_say("twenty five seconds. if you're not close, "
						+ "don't run for it - she's back tomorrow night.")
				_show_notice(maxi(0, int(left)))
				if left <= 0.0:
					_leave()
		DEPARTING:
			# slow pull, then it really goes
			_speed = minf(_speed + 62.0 * delta, 700.0)
			position += RAIL_DIR * _speed * delta
			if boarded:
				_countdown.visible = false
			if position.distance_to(_stop_pos) > 2400.0:
				state = GONE
				visible = false
				_notice.visible = false
				if boarded:
					extracted.emit("the night freight")
				else:
					_clock = 0.0
					_speed = 0.0
					_warned = false        # ...and again tomorrow night
					position = _stop_pos - RAIL_DIR * 2600.0
					state = AWAY


func _steam(delta: float) -> void:
	## the stack breathes while she stands, and works harder pulling away
	_steam_timer -= delta
	if _steam_timer <= 0.0:
		_steam_timer = 0.55 if state != DEPARTING else 0.16
		var puff := Sprite2D.new()
		puff.texture = _steam_tex
		puff.modulate = Color(0.804, 0.851, 0.839, 0.0)
		puff.position = Vector2(-14.0, -44.0) \
			+ Vector2(randf_range(-2.0, 2.0), randf_range(-2.0, 2.0))
		puff.z_index = 9
		add_child(puff)
		_puffs.append({"sprite": puff, "age": 0.0})
	var i := _puffs.size() - 1
	while i >= 0:
		var puff: Dictionary = _puffs[i]
		var sprite := puff["sprite"] as Sprite2D
		puff["age"] = float(puff["age"]) + delta
		var age: float = puff["age"]
		if age >= 2.4:
			sprite.queue_free()
			_puffs.remove_at(i)
		else:
			var t := age / 2.4
			sprite.position += Vector2(-7.0, -20.0) * delta
			sprite.scale = Vector2.ONE * (0.45 + t * 1.1)
			sprite.modulate.a = 0.5 * (1.0 - t) * minf(1.0, age * 4.0)
		i -= 1


func _tick_countdown(delta: float) -> void:
	_count_left -= delta
	_notice.visible = false
	var n := maxi(0, int(ceilf(_count_left)))
	if n != _count_shown:
		_count_shown = n
		_countdown.text = "departing in %d" % n
	_countdown.visible = not Ui.blocks_gameplay()
	if _count_left <= 0.0:
		_leave()


func _leave() -> void:
	state = DEPARTING
	_speed = 0.0
	_notice.visible = false
	Sfx.play_horn()
	if not boarded:
		_radio_say("and she's rolling. that's that until tomorrow night - "
			+ "find something to do that isn't dying.")


func set_hud_hidden(hidden: bool) -> void:
	if hidden:
		_notice.visible = false
		_countdown.visible = false


func _show_notice(seconds: int) -> void:
	if seconds != _notice_shown:
		_notice_shown = seconds
		_notice.text = "the freight leaves in %d" % seconds
	_notice.visible = not Ui.blocks_gameplay()
