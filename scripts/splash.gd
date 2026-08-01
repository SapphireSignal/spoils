extends Node2D
## SapphireSignal studio splash. The sapphire wakes, broadcasts a signal
## ping, and the FIRST BEAM sweeps across to reveal the studio name letter by
## letter — then everything breathes once and hands off to the menu.
## Any input skips it. Harness runs (shots/smoke/perf) skip it instantly.

const GEM_LIFT := Vector2(0, -30)
const WORD_DROP := 26.0
const BEAM_TIME := 0.9
const DONE_AT := 3.4

var _t := 0.0
var _gem: Sprite2D
var _word_clip: Control
var _word: TextureRect
var _beam: Sprite2D
var _word_width := 0.0
var _word_left := 0.0
var _rings_fired := 0
var _second_ping := false
var _finishing := false
var _center := Vector2.ZERO
var _ring_texs: Array[Texture2D] = []


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot=") or arg == "--smoke" or arg.begins_with("--perf") \
				or arg.begins_with("--probe") or arg.begins_with("--scene"):
			_finish()
			return

	var black := ColorRect.new()
	black.color = Color("090a14")
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	var layer := CanvasLayer.new()
	layer.layer = -1
	layer.add_child(black)
	add_child(layer)

	var view := Vector2(get_window().content_scale_size)
	_center = (view * 0.5).floor()

	for i in 6:
		_ring_texs.append(load("res://art/gen/signal_ring_%d.png" % i))

	_gem = Sprite2D.new()
	_gem.texture = load("res://art/gen/studio_gem.png")
	_gem.position = _center + GEM_LIFT
	_gem.modulate.a = 0.0
	add_child(_gem)

	var word_tex: Texture2D = load("res://art/gen/studio_word.png")
	_word_width = float(word_tex.get_width())
	_word_left = _center.x - _word_width * 0.5
	_word_clip = Control.new()
	_word_clip.clip_contents = true
	_word_clip.position = Vector2(_word_left, _center.y + WORD_DROP)
	_word_clip.size = Vector2(0, float(word_tex.get_height()))
	_word = TextureRect.new()
	_word.texture = word_tex
	_word.stretch_mode = TextureRect.STRETCH_KEEP
	_word_clip.add_child(_word)
	add_child(_word_clip)

	_beam = Sprite2D.new()
	_beam.texture = load("res://art/gen/signal_beam.png")
	_beam.position = Vector2(_word_left, _center.y + WORD_DROP + 6.0)
	_beam.visible = false
	add_child(_beam)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey or event is InputEventMouseButton:
		if event.is_pressed():
			_finish(false)


func _process(delta: float) -> void:
	if _finishing:
		return
	_t += delta

	# the sapphire locks on: two flickers, then solid
	if _t > 0.25:
		_gem.modulate.a = 0.45
	if _t > 0.38:
		_gem.modulate.a = 0.2
	if _t > 0.46:
		_gem.modulate.a = 1.0

	# first ping + expanding broadcast rings
	if _t > 0.65 and _rings_fired == 0:
		Sfx.play_splash_ping()
		_rings_fired = 1
	if _rings_fired >= 1 and _rings_fired <= 6 and _t > 0.65 + 0.07 * _rings_fired:
		_spawn_ring(_rings_fired - 1)
		_rings_fired += 1

	# the first beam sweeps the name in
	var sweep := clampf((_t - 1.05) / BEAM_TIME, 0.0, 1.0)
	if sweep > 0.0:
		var eased := 1.0 - pow(1.0 - sweep, 2.0)
		_word_clip.size.x = roundf(_word_width * eased)
		_beam.visible = sweep < 1.0
		_beam.position.x = roundf(_word_left + _word_width * eased)

	# a second, quieter breath of signal
	if _t > 2.25 and not _second_ping:
		_second_ping = true
		Sfx.play_splash_ping(true)
		_spawn_ring(2)
		_spawn_ring(4)

	if _t > DONE_AT:
		_finish(false)


func _spawn_ring(index: int) -> void:
	var ring := Sprite2D.new()
	ring.texture = _ring_texs[index]
	ring.position = _gem.position
	ring.modulate.a = 0.9 - 0.12 * index
	add_child(ring)
	var tween := create_tween()
	tween.tween_property(ring, "modulate:a", 0.0, 0.5)
	tween.tween_callback(ring.queue_free)


func _finish(instant: bool = true) -> void:
	# harness runs cut instantly; a person gets a clean fade to black first
	# (the hard cut into the fully-formed menu read as a glitch)
	if _finishing:
		return
	_finishing = true
	if instant:
		get_tree().change_scene_to_file.call_deferred("res://scenes/menu.tscn")
		return
	var cover := ColorRect.new()
	cover.color = Color("090a14", 0.0)
	cover.set_anchors_preset(Control.PRESET_FULL_RECT)
	var layer := CanvasLayer.new()
	layer.layer = 100
	layer.add_child(cover)
	add_child(layer)
	var tween := create_tween()
	tween.tween_property(cover, "color:a", 1.0, 0.45)
	tween.tween_callback(func() -> void:
		get_tree().change_scene_to_file("res://scenes/menu.tscn"))
