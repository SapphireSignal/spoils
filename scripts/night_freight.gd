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
const FIRST_ARRIVAL := 45.0    # the first one comes early enough to catch
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


func _radio_say(text: String) -> void:
	if _radio != null:
		_radio.say(text)


func setup(stop_pos: Vector2, player: Player, radio: Radio) -> void:
	_stop_pos = stop_pos
	_player = player
	_radio = radio
	position = _stop_pos - RAIL_DIR * 2600.0
	visible = false
	_clock = FIRST_ARRIVAL - PERIOD    # first arrival at FIRST_ARRIVAL

	# origins come from the manifest like every other prop — guessing them
	# put the hauled cars off the rails
	var manifest: Dictionary = {}
	var file := FileAccess.open("res://art/gen/manifest.json", FileAccess.READ)
	if file != null:
		var parsed: Variant = JSON.parse_string(file.get_as_text())
		if parsed is Dictionary:
			manifest = (parsed as Dictionary).get("props", {})
	var rake := ["locomotive", "boxcar_x_0", "boxcar_x_2"]
	var back := 0.0
	for prop_name in rake:
		var sprite := Sprite2D.new()
		sprite.texture = load("res://art/gen/%s.png" % prop_name)
		sprite.centered = false
		var origin: Array = (manifest.get(prop_name, {}) as Dictionary).get(
			"origin", [48, 60])
		sprite.offset = Vector2(-float(origin[0]), -float(origin[1]))
		# every rail sprite sits on the same (2,1) axis, so the rake just
		# steps back along it, each car behind the last
		sprite.position = (-RAIL_DIR * back).round()
		add_child(sprite)
		back += 104.0
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


func in_range_of(at: Vector2) -> bool:
	return global_position.distance_to(at) < BOARD_RANGE


func board() -> void:
	if not can_board():
		return
	boarded = true
	_player.board_ride(self, Vector2(0.0, -18.0))
	_count_left = float(DEPART_COUNT)
	Sfx.play_door(false)
	_radio_say("good. stay down and stay in the car until she's clear of "
		+ "the wire. see you at the depot, magpie.")


func _process(delta: float) -> void:
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
				_show_notice("the freight leaves in %d" % maxi(0, int(left)))
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
					state = AWAY
					_speed = 0.0
					position = _stop_pos - RAIL_DIR * 2600.0
					state = AWAY


func _tick_countdown(delta: float) -> void:
	_count_left -= delta
	_notice.visible = false
	_countdown.text = "departing in %d" % maxi(0, int(ceilf(_count_left)))
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


func _show_notice(text: String) -> void:
	_notice.text = text
	_notice.visible = true
