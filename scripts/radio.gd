class_name Radio
extends CanvasLayer
## mara on the duty radio.
##
## There is no voice acting in SPOILS and there isn't going to be one by
## accident — bespoke lines can't be sourced from a sound library. The
## popup is APPEAR-ONLY on sound (user calls 2026-08-01): the squelch pair
## is gone and nothing at all plays when a call drops off, but one very
## quiet tick (`Sfx.play_radio_tick`, -30 dB) plays as she keys up — added
## back after the user asked for "a really subtle sound effect", so do NOT
## delete it. (This comment used to say the popup is silent outright.)
## `Sfx.play_radio`, the full squelch, still exists if M2 ever wants it
## back. The writing is the performance: she writes like
## a dispatcher because she was one — clipped, procedural, uses your
## callsign, never exclaims.
##
## Reusable on purpose: the walk-in tutorial in M2 is entirely her voice.

const HOLD := 6.5              # how long a call stays up (user: they went
                               # by too quickly at 4.6)
const FADE := 0.7

var _panel: PanelContainer
var _line: Label
var _left := 0.0
var _queue: Array[String] = []


func _ready() -> void:
	layer = 72
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UITheme.get_theme()
	add_child(root)

	# upper CENTRE, and small: a big panel in the corner pulled the eye
	# away from the world every time she keyed up (user call)
	_panel = PanelContainer.new()
	_panel.anchor_left = 0.5
	_panel.anchor_right = 0.5
	_panel.anchor_top = 0.13
	_panel.anchor_bottom = 0.13
	_panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.modulate.a = 0.0
	root.add_child(_panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 5)
	_panel.add_child(margin)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 2)
	margin.add_child(rows)
	# no name plate: she is the only voice on this channel, and a label
	# saying "mara" over a line that ALSO said "magpie, mara." named her
	# twice in three words (user report, with a screenshot)
	_line = Label.new()
	_line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_line.custom_minimum_size = Vector2(240, 0)
	_line.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_line.add_theme_color_override("font_color", UITheme.TEXT)
	rows.add_child(_line)
	# a window is up: her call goes off screen and comes back with the
	# world. The hold is frozen with the tree, so nothing is missed.
	add_to_group("hud")


func set_hud_hidden(hidden: bool) -> void:
	if hidden:
		_panel.visible = false
	elif _left > 0.0:
		_panel.visible = true


func say(text: String) -> void:
	## key up, speak, key down. Calls queue rather than clip each other —
	## a dispatcher waits for the channel.
	if _left > 0.0:
		_queue.append(text)
		return
	_speak(text)


func _speak(text: String) -> void:
	_line.text = text
	_left = HOLD
	_panel.visible = not Ui.blocks_gameplay()
	_panel.modulate.a = 1.0
	# one very quiet tick as she keys up, and nothing at all when she
	# drops off (user: subtle, and appear only)
	Sfx.play_radio_tick()


func _process(delta: float) -> void:
	if _left <= 0.0:
		return
	_left -= delta
	if _left <= FADE:
		_panel.modulate.a = maxf(0.0, _left / FADE)
	if _left <= 0.0:
		_panel.modulate.a = 0.0
		if not _queue.is_empty():
			await get_tree().create_timer(0.5).timeout
			# the timer outlives a freed scene: extracting mid-queue used
			# to resume this on a dead Radio
			if not is_inside_tree():
				return
			if _left <= 0.0 and not _queue.is_empty():
				_speak(_queue.pop_front())
