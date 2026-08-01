class_name EnvironmentSystem
extends Node
## Living world: day/night tint cycle, rain spells and puddles, lightning,
## street-lamp nightfall, and WORLD-ANCHORED rain.
##
## Rain is simulated, not decorated: each drop is a world-space sprite that
## falls to a real ground point, dies there, and leaves a splash AT THAT SPOT.
## Splashes never move with the camera, and no drop lands inside a roofed
## building. Every rain pixel — drop and splash — is the puddles' blue.

const DAY_SECONDS := 1200.0         # one full day/night cycle (20 min)
const DEEP_NIGHT := Color(0.14, 0.16, 0.34)  # night is DARK — that's the fun
const STORM_TINT_SECONDS := 45.0    # storm darkening fades in over ~45 s —
                                    # the screen must never visibly "switch"

const DROP_COUNT := 240
const SPLASH_COUNT := 220
const DROP_SPEED_MIN := 540.0
const DROP_SPEED_MAX := 660.0
const DROP_DRIFT := -55.0           # slight westward wind
const DROP_FALL_MIN := 240.0
const DROP_FALL_MAX := 360.0
const SPLASH_LIFE := 0.34
const SPLASH_FRAMES := 4

var day_time := 0.18                # 0..1, start in the morning
var rain_intensity := 0.0           # 0..1, ramps in and out
var night_amount := 0.0             # 0 day .. 1 deep night

var _raining := false
var _storm_tint := 0.0              # visual darkening, slower than the rain
var _weather_timer := 0.0
var _lightning_timer := 999.0
var _flash: ColorRect
var _tint: CanvasModulate
var _puddles: Array[Sprite2D] = []
var _puddles_resting := true
var _tint_gradient: Gradient
var _window: Window
var _floor_layer: TileMapLayer
var _roof_rects: Array[Rect2i] = []

# drop pool (parallel arrays — no per-frame allocation, no per-drop objects)
var _drop_sprites: Array[Sprite2D] = []
var _drop_pos: PackedVector2Array = PackedVector2Array()
var _drop_vel: PackedVector2Array = PackedVector2Array()
var _drop_ground: PackedFloat32Array = PackedFloat32Array()
var _drop_active: PackedByteArray = PackedByteArray()
var _drops_live := 0

# splash pool
var _splash_sprites: Array[Sprite2D] = []
var _splash_age: PackedFloat32Array = PackedFloat32Array()
var _splash_free: Array[int] = []


func setup(root: Node2D, floor_layer: TileMapLayer, puddle_spots: Array,
		roofs: Array) -> void:
	# setup is async (pool creation yields) — _process must not run until
	# everything below exists
	set_process(false)
	_window = root.get_window()
	_floor_layer = floor_layer
	for roof in roofs:
		_roof_rects.append((roof as RoofReveal).cells)

	_tint = CanvasModulate.new()
	root.add_child(_tint)

	# puddles + splashes live just above the floor, below the y-sorted world
	var puddle_layer := Node2D.new()
	puddle_layer.name = "Puddles"
	root.add_child(puddle_layer)
	root.move_child(puddle_layer, floor_layer.get_index() + 1)
	for spot in puddle_spots:
		var sprite := Sprite2D.new()
		sprite.texture = load("res://art/gen/puddle_%d.png" % (randi() % 3))
		sprite.position = (spot as Vector2).round()
		sprite.flip_h = randf() < 0.5
		sprite.modulate.a = 0.0
		puddle_layer.add_child(sprite)
		_puddles.append(sprite)

	var splash_layer := Node2D.new()
	splash_layer.name = "RainSplashes"
	root.add_child(splash_layer)
	root.move_child(splash_layer, puddle_layer.get_index() + 1)
	var splash_tex: Texture2D = load("res://art/gen/rain_splash.png")
	for i in SPLASH_COUNT:
		var sprite := Sprite2D.new()
		sprite.texture = splash_tex
		sprite.hframes = SPLASH_FRAMES
		sprite.visible = false
		splash_layer.add_child(sprite)
		_splash_sprites.append(sprite)
		_splash_age.append(0.0)
		_splash_free.append(i)
		if i % 80 == 79:
			await get_tree().process_frame

	# drops render above the whole world (they are in the air)
	var drop_layer := Node2D.new()
	drop_layer.name = "RainDrops"
	drop_layer.z_index = 60
	root.add_child(drop_layer)
	var drop_tex: Texture2D = load("res://art/gen/rain_streak.png")
	_drop_pos.resize(DROP_COUNT)
	_drop_vel.resize(DROP_COUNT)
	_drop_ground.resize(DROP_COUNT)
	_drop_active.resize(DROP_COUNT)
	for i in DROP_COUNT:
		var sprite := Sprite2D.new()
		sprite.texture = drop_tex
		sprite.visible = false
		drop_layer.add_child(sprite)
		_drop_sprites.append(sprite)
		_drop_active[i] = 0
		if i % 80 == 79:
			await get_tree().process_frame

	var sky := CanvasLayer.new()
	sky.layer = 30
	add_child(sky)
	_flash = ColorRect.new()
	_flash.color = Color("a4dddb", 0.0)
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sky.add_child(_flash)

	# one continuous gradient around the whole clock. The first and last
	# points are the SAME deep night, so midnight can never snap — the old
	# table left the endpoint at default white, which brightened the late
	# evening and then jump-cut to night when the day wrapped
	_tint_gradient = Gradient.new()
	_tint_gradient.offsets = PackedFloat32Array(
		[0.0, 0.06, 0.16, 0.26, 0.58, 0.70, 0.84, 0.92, 1.0])
	_tint_gradient.colors = PackedColorArray([
		DEEP_NIGHT, DEEP_NIGHT,
		Color(0.85, 0.72, 0.72),   # dawn
		Color(1.0, 1.0, 1.0),      # day
		Color(1.0, 0.98, 0.94),    # late day
		Color(0.88, 0.72, 0.68),   # dusk
		Color(0.50, 0.52, 0.72),   # nightfall
		DEEP_NIGHT, DEEP_NIGHT,
	])
	_weather_timer = randf_range(60.0, 200.0)
	add_to_group("environment")
	set_process(true)


func force_weather(rain_on: bool) -> void:  # harness hook
	_raining = rain_on
	rain_intensity = 1.0 if rain_on else 0.0
	_storm_tint = rain_intensity
	_weather_timer = 9999.0
	for puddle in _puddles:
		puddle.modulate.a = 0.9 if rain_on else 0.0
	if rain_on:  # prefill the sky so captures show rain mid-fall
		for i in DROP_COUNT:
			_spawn_drop(i, true)


func force_time(t: float) -> void:  # harness hook, 0..1
	day_time = t


func _process(delta: float) -> void:
	day_time = fmod(day_time + delta / DAY_SECONDS, 1.0)
	var tint := _tint_gradient.sample(day_time)
	# storm darkening on its own slow, eased fade — decoupled from the rain
	# density ramp so the screen color NEVER visibly steps
	_storm_tint = move_toward(_storm_tint, 1.0 if _raining else 0.0,
		delta / STORM_TINT_SECONDS)
	if _storm_tint > 0.0:
		tint = tint.darkened(0.12 * smoothstep(0.0, 1.0, _storm_tint))
	_tint.color = tint
	night_amount = _night_amount_for(day_time)
	get_tree().call_group("street_lamps", "set_night", night_amount)

	# weather state machine — long spells, slow ramps
	_weather_timer -= delta
	if _weather_timer <= 0.0:
		_raining = not _raining
		_weather_timer = randf_range(140.0, 320.0) if _raining \
			else randf_range(240.0, 540.0)
		if _raining:
			_lightning_timer = randf_range(12.0, 40.0)
	rain_intensity = move_toward(rain_intensity, 1.0 if _raining else 0.0, delta / 14.0)

	_update_rain(delta)

	# puddles fill while raining, dry out under the sun — and the loop sleeps
	# entirely once every puddle has settled
	if _raining or not _puddles_resting:
		var puddle_target := clampf(rain_intensity, 0.0, 0.9) if _raining else 0.0
		var rate := delta / (22.0 if _raining else 45.0)
		_puddles_resting = true
		for puddle in _puddles:
			var a := puddle.modulate.a
			if a != puddle_target:
				puddle.modulate.a = move_toward(a, puddle_target, rate)
				_puddles_resting = false

	# the rain bed follows the density, always subtle
	Sfx.set_rain(rain_intensity)

	# lightning during heavy rain: a real double-strike that lingers, thunder
	# rolling in behind it (the delay is the distance)
	if _raining and rain_intensity > 0.6:
		_lightning_timer -= delta
		if _lightning_timer <= 0.0:
			_lightning_timer = randf_range(18.0, 50.0)
			var peak := 0.20 + 0.10 * night_amount
			var tween := create_tween()
			tween.tween_property(_flash, "color:a", peak, 0.09)
			tween.tween_property(_flash, "color:a", 0.05, 0.16)
			tween.tween_property(_flash, "color:a", peak * 0.75, 0.08)
			tween.tween_property(_flash, "color:a", 0.0, 0.50)
			get_tree().create_timer(randf_range(0.4, 1.4)).timeout.connect(
				Sfx.play_thunder)


func _night_amount_for(t: float) -> float:
	if t < 0.06:
		return 1.0
	if t < 0.16:
		return 1.0 - smoothstep(0.06, 0.16, t)
	if t < 0.72:
		return 0.0
	if t < 0.86:
		return smoothstep(0.72, 0.86, t)
	return 1.0


# ------------------------------------------------------------- world rain ---

func _update_rain(delta: float) -> void:
	var want := int(DROP_COUNT * rain_intensity)
	for i in DROP_COUNT:
		if _drop_active[i] == 1:
			var pos := _drop_pos[i] + _drop_vel[i] * delta
			if pos.y >= _drop_ground[i]:
				# the drop is gone the moment it lands; only the splash stays,
				# fixed to the ground where it fell
				_spawn_splash(Vector2(pos.x, _drop_ground[i]))
				_drop_active[i] = 0
				_drops_live -= 1
				_drop_sprites[i].visible = false
			else:
				_drop_pos[i] = pos
				_drop_sprites[i].position = pos
		elif _drops_live < want:
			_spawn_drop(i, false)

	if _splash_free.size() < SPLASH_COUNT:
		for i in SPLASH_COUNT:
			var sprite := _splash_sprites[i]
			if not sprite.visible:
				continue
			var age := _splash_age[i] + delta
			if age >= SPLASH_LIFE:
				sprite.visible = false
				_splash_free.append(i)
			else:
				_splash_age[i] = age
				sprite.frame = int(age / SPLASH_LIFE * SPLASH_FRAMES)


func _spawn_drop(index: int, prefill: bool) -> void:
	var camera := get_viewport().get_camera_2d()
	if camera == null:
		return
	var view := Vector2(_window.content_scale_size) * 0.5
	var center := camera.get_screen_center_position()
	var ground := Vector2.ZERO
	var found := false
	for attempt in 3:
		ground = center + Vector2(randf_range(-view.x - 40.0, view.x + 40.0),
			randf_range(-view.y - 30.0, view.y + 30.0))
		if not _roofed(ground):
			found = true
			break
	if not found:
		return
	var fall := randf_range(DROP_FALL_MIN, DROP_FALL_MAX)
	var vel := Vector2(DROP_DRIFT * randf_range(0.7, 1.3),
		randf_range(DROP_SPEED_MIN, DROP_SPEED_MAX))
	var progress := randf() if prefill else 0.0
	var start := ground + Vector2(-vel.x * (fall / vel.y), -fall)
	_drop_pos[index] = start.lerp(Vector2(ground.x, ground.y), progress)
	_drop_vel[index] = vel
	_drop_ground[index] = ground.y
	_drop_active[index] = 1
	_drops_live += 1
	var sprite := _drop_sprites[index]
	sprite.position = _drop_pos[index]
	sprite.visible = true


func _spawn_splash(at: Vector2) -> void:
	if _splash_free.is_empty():
		return
	var index: int = _splash_free.pop_back()
	_splash_age[index] = 0.0
	var sprite := _splash_sprites[index]
	sprite.position = at.round()
	sprite.frame = 0
	sprite.visible = true


func _roofed(point: Vector2) -> bool:
	if _roof_rects.is_empty():
		return false
	var cell := _floor_layer.local_to_map(point)
	for rect in _roof_rects:
		if rect.has_point(cell):
			return true
	return false
