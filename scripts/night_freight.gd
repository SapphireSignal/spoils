class_name NightFreight
extends Node2D
## The night freight: the one train still running in transit. It comes
## into the yard every five minutes, stands for one, and goes — whether
## you're aboard or not.
##
## Timing is REAL time and deliberately indifferent to you (user spec):
## arrive, wait sixty seconds, leave. Miss it and you wait five minutes
## or walk. The whistle and the corner notice exist so you're never
## guessing where it is in that cycle.

signal extracted(method: String)

const PERIOD := 300.0          # five real minutes between arrivals
const FIRST_ARRIVAL := 20.0    # the first one comes early enough to catch
                               # (45 s read as "late" from inside a raid)
const ARRIVE_TIME := 9.0       # the slide into the yard
const WAIT_TIME := 60.0        # one real minute standing
const WARN_LEAD := 18.0        # whistle this long before it appears
const BOARD_RANGE := 96.0      # the length of a carriage, near enough
const DEPART_COUNT := 10       # "departing in 10..."
const RAIL_DIR := Vector2(0.8944, 0.4472)   # +x along the iso rail

enum { AWAY, ARRIVING, WAITING, DEPARTING, GONE }

var state := AWAY
var boarded := false

var _stop_pos := Vector2.ZERO
var _clock := 0.0              # seconds into the current cycle
var _speed := 0.0
var _count_left := 0.0
var _warned := false
var _half_called := false
var _player: Player
var _radio: Radio
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
		manifest: Dictionary) -> void:
	_stop_pos = stop_pos
	_player = player
	_radio = radio
	position = _stop_pos - RAIL_DIR * 2600.0
	visible = false
	# AWAY fires when _clock reaches PERIOD, so to arrive FIRST_ARRIVAL
	# seconds from now the clock must START that far short of PERIOD.
	# The sign was inverted, which put the first train 580 s out — the
	# v0.6.40 note claiming "20 seconds in" was simply wrong.
	_clock = PERIOD - FIRST_ARRIVAL

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

	var layer := CanvasLayer.new()
	layer.layer = 73
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_notice = Label.new()
	_notice.theme = UITheme.get_theme()
	_notice.add_theme_color_override("font_color", Color("de9e41"))
	_notice.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_notice.offset_left = -300
	_notice.offset_top = 8
	_notice.offset_right = -12
	_notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
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
			var until := PERIOD - _clock
			if not _warned and until <= WARN_LEAD:
				_warned = true
				Sfx.play_horn()
				_radio_say("magpie, mara. i've got a freight inbound to the "
					+ "yard. twenty seconds, give or take.")
			if _clock >= PERIOD:
				_clock = 0.0
				_warned = false
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
						+ "don't run for it - next one's five minutes.")
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
	_countdown.visible = true
	if _count_left <= 0.0:
		_leave()


func _leave() -> void:
	state = DEPARTING
	_speed = 0.0
	_notice.visible = false
	Sfx.play_horn()
	if not boarded:
		_radio_say("and she's rolling. that's that. five minutes till the "
			+ "next one - find something to do that isn't dying.")


func _show_notice(seconds: int) -> void:
	if seconds != _notice_shown:
		_notice_shown = seconds
		_notice.text = "the freight leaves in %d" % seconds
	_notice.visible = true
