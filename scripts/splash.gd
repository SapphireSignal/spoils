extends Node2D
## SapphireSignal studio splash. The sapphire wakes, CRACKS, and SHATTERS —
## revealing the signal that was always inside. The signal pings, its first
## beam sweeps across to reveal the studio name letter by letter, and a
## small "studio" line settles underneath. Any input skips it. Harness runs
## (shots/smoke/perf) skip it instantly.

const GEM_LIFT := Vector2(0, -30)
const WORD_DROP := 26.0
const BEAM_TIME := 1.4
const SHATTER_AT := 2.05
const DONE_AT := 5.8

var _t := 0.0
var _gem: Sprite2D
var _signal_core: Sprite2D
var _word_clip: Control
var _word: TextureRect
var _tag: TextureRect
var _beam: Sprite2D
var _word_width := 0.0
var _word_left := 0.0
var _rings_fired := 0
var _crack_stage := -1
var _shattered := false
var _second_ping := false
var _finishing := false
var _center := Vector2.ZERO
var _ring_texs: Array[Texture2D] = []
var _crack_texs: Array[Texture2D] = []
var _shards: Array[Dictionary] = []


func _ready() -> void:
	# The autoloads outlive every scene, so each scene ROOT starts from a
	# known state rather than trusting whoever ran last to have tidied up.
	# The splash boots into an empty stack today, so this asserts rather
	# than fixes — but it is the same three-line contract main.gd and
	# main_menu.gd keep, and it costs nothing (both calls are idempotent).
	Ui.clear()
	Juice.reset()
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
	for i in 3:
		_crack_texs.append(load("res://art/gen/studio_gem_crack_%d.png" % i))

	_gem = Sprite2D.new()
	_gem.texture = load("res://art/gen/studio_gem.png")
	_gem.position = _center + GEM_LIFT
	_gem.modulate.a = 0.0
	add_child(_gem)

	_signal_core = Sprite2D.new()
	_signal_core.texture = load("res://art/gen/studio_signal.png")
	_signal_core.position = _center + GEM_LIFT
	_signal_core.visible = false
	add_child(_signal_core)

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

	var tag_tex: Texture2D = load("res://art/gen/studio_tag.png")
	_tag = TextureRect.new()
	_tag.texture = tag_tex
	_tag.stretch_mode = TextureRect.STRETCH_KEEP
	_tag.position = Vector2(_center.x - float(tag_tex.get_width()) * 0.5,
		_center.y + WORD_DROP + float(word_tex.get_height()) + 6.0)
	_tag.modulate.a = 0.0
	add_child(_tag)

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

	# the sapphire wakes: two slow flickers, then it locks on solid
	if _t > 0.40:
		_gem.modulate.a = 0.45
	if _t > 0.62:
		_gem.modulate.a = 0.2
	if _t > 0.80:
		_gem.modulate.a = 1.0

	# cracks spread through the stone — three beats, each with a flinch
	if not _shattered:
		var want_stage := -1
		if _t > 1.75:
			want_stage = 2
		elif _t > 1.45:
			want_stage = 1
		elif _t > 1.15:
			want_stage = 0
		if want_stage > _crack_stage:
			_crack_stage = want_stage
			_gem.texture = _crack_texs[_crack_stage]
			_gem.position = _center + GEM_LIFT \
				+ Vector2(1.0 if _crack_stage % 2 == 0 else -1.0, 0.0)
			Sfx.play_click(true)   # a soft tick, not a snap (user call)

	# THE SHATTER: shards fly, and the signal inside is just... there
	if _t > SHATTER_AT and not _shattered:
		_shattered = true
		_gem.visible = false
		_signal_core.visible = true
		Sfx.play_splash_ping()
		for i in 6:
			var shard := Sprite2D.new()
			shard.texture = load("res://art/gen/studio_shard_%d.png" % i)
			shard.position = _center + GEM_LIFT
			add_child(shard)
			var angle := TAU * float(i) / 6.0 + randf_range(-0.3, 0.3)
			_shards.append({"sprite": shard, "age": 0.0,
				"vel": Vector2(cos(angle), sin(angle)) * randf_range(38.0, 64.0)})

	var i := _shards.size() - 1
	while i >= 0:
		var shard_state: Dictionary = _shards[i]
		var sprite := shard_state["sprite"] as Sprite2D
		shard_state["age"] = float(shard_state["age"]) + delta
		var age: float = shard_state["age"]
		if age >= 0.7:
			sprite.queue_free()
			_shards.remove_at(i)
		else:
			var vel: Vector2 = shard_state["vel"]
			sprite.position += vel * delta
			shard_state["vel"] = vel + Vector2(0.0, 55.0) * delta   # they fall
			sprite.modulate.a = 1.0 - age / 0.7
		i -= 1

	# the revealed signal breathes and broadcasts
	if _shattered:
		_signal_core.modulate.a = 0.85 + 0.15 * sin(_t * 9.0)
		if _rings_fired <= 6 and _t > SHATTER_AT + 0.1 + 0.12 * _rings_fired:
			if _rings_fired > 0:
				_spawn_ring(_rings_fired - 1)
			_rings_fired += 1

	# the first beam sweeps the name in
	var sweep := clampf((_t - 2.7) / BEAM_TIME, 0.0, 1.0)
	if sweep > 0.0:
		var eased := 1.0 - pow(1.0 - sweep, 2.0)
		_word_clip.size.x = roundf(_word_width * eased)
		_beam.visible = sweep < 1.0
		_beam.position.x = roundf(_word_left + _word_width * eased)

	# "studio" settles in underneath
	if _t > 4.3:
		_tag.modulate.a = move_toward(_tag.modulate.a, 1.0, delta * 2.0)

	# a second, quieter breath of signal
	if _t > 4.6 and not _second_ping:
		_second_ping = true
		Sfx.play_splash_ping(true)
		_spawn_ring(2)
		_spawn_ring(4)

	if _t > DONE_AT:
		_finish(false)


func _spawn_ring(index: int) -> void:
	var ring := Sprite2D.new()
	ring.texture = _ring_texs[index]
	ring.position = _center + GEM_LIFT
	ring.modulate.a = 0.9 - 0.12 * index
	add_child(ring)
	var tween := create_tween()
	tween.tween_property(ring, "modulate:a", 0.0, 0.85)
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
	# Pay the shader pipeline cost HERE, between the studio card and the
	# menu, rather than dropping a frame the first time something flashes
	# mid-raid. Skipped entirely unless a shader actually changed — see
	# ShaderWarm; a bar on every launch for work already cached would be
	# theatre.
	if ShaderWarm.is_cold():
		var warm := ShaderWarm.new()
		add_child(warm)
		await warm.run()
		warm.queue_free()
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
