class_name EnvironmentSystem
extends Node
## Living world: day/night tint cycle, rain spells and puddles, lightning,
## street-lamp nightfall, and WORLD-ANCHORED rain.
##
## Rain is simulated, not decorated: each drop is a world-space sprite that
## falls to a real ground point, dies there, and leaves a splash AT THAT SPOT.
## Splashes never move with the camera, and no drop lands inside a roofed
## building. Every rain pixel — drop and splash — is the puddles' blue.

const DAY_SECONDS := 600.0          # one full day/night cycle (10 min, user
                                    # call) — night must ARRIVE every session
const DEEP_NIGHT := Color(0.085, 0.095, 0.24)  # HARD-to-see dark (user call:
                                    # "that's why we have a flashlight")
const STORM_TINT_SECONDS := 45.0    # storm darkening fades in over ~45 s —
                                    # the screen must never visibly "switch"

const FOG_COUNT := 32               # dawn fog puffs alive at once, near view
const FOG_ALPHA_MAX := 0.5          # clearly visible — still never a wall
const FOG_FADE_IN := 3.5            # long breathe-in — puffs must never pop
const FOG_TEX_COUNT := 5            # small wisps + the big banks (fog_3/4)
const LEAF_COUNT := 22              # falling leaves alive at once

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

# dawn fog pool: puffs anchor to forest/road spots, drift with the wind,
# and dissolve once they've slid clear of their anchor (out of the trees)
var _fog_spots := PackedVector2Array()
var _fog_sprites: Array[Sprite2D] = []
var _fog_anchor := PackedVector2Array()
var _fog_speed := PackedFloat32Array()
var _fog_level := PackedFloat32Array()   # per-puff alpha factor
var _fog_age := PackedFloat32Array()     # seconds alive — drives the fade-in
var _fog_active := PackedByteArray()
var _fog_wind := 1.0
var _was_morning := false
var _fog_near: Array[int] = []      # spot indices near the view, kept fresh
var _fog_refresh := 0.0
var _fog_alive := 0                 # capped vs nearby spots — never a wall

# falling leaves: a few shedder oaks flutter one leaf at a time
var _leaf_trees := PackedVector2Array()
var _leaf_sprites: Array[Sprite2D] = []
var _leaf_state: Array[Dictionary] = []
var _leaf_timer := 0.0


func setup(root: Node2D, floor_layer: TileMapLayer, puddle_spots: Array,
		roofs: Array, fog_spots := PackedVector2Array(),
		leaf_trees := PackedVector2Array()) -> void:
	_fog_spots = fog_spots
	_leaf_trees = leaf_trees
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

	# dawn fog drifts ABOVE the world, below the rain
	var fog_layer := Node2D.new()
	fog_layer.name = "DawnFog"
	fog_layer.z_index = 55
	root.add_child(fog_layer)
	for i in FOG_COUNT:
		var sprite := Sprite2D.new()
		# mixed sizes (user call): most slots wisps, every third slot one of
		# the BIG banks — variety baked in art, never runtime scaling
		sprite.texture = load("res://art/gen/fog_%d.png" % (i % FOG_TEX_COUNT))
		sprite.visible = false
		fog_layer.add_child(sprite)
		_fog_sprites.append(sprite)
		_fog_anchor.append(Vector2.ZERO)
		_fog_speed.append(1.0)
		_fog_level.append(1.0)
		_fog_age.append(0.0)
		_fog_active.append(0)

	# leaves tumble just above the props
	var leaf_layer := Node2D.new()
	leaf_layer.name = "Leaves"
	leaf_layer.z_index = 45
	root.add_child(leaf_layer)
	for i in LEAF_COUNT:
		var sprite := Sprite2D.new()
		sprite.texture = load("res://art/gen/leaves_%d.png" % (i % 3))
		sprite.hframes = 2
		sprite.visible = false
		leaf_layer.add_child(sprite)
		_leaf_sprites.append(sprite)
		_leaf_state.append({"active": false, "t": 0.0, "dur": 3.0,
			"pattern": 0, "origin": Vector2.ZERO})

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
	# night owns ~26% of the clock now (was ~14%) and dusk lands earlier —
	# a raid that starts at dawn reaches real darkness in the same sitting
	_tint_gradient.offsets = PackedFloat32Array(
		[0.0, 0.08, 0.17, 0.26, 0.52, 0.62, 0.74, 0.82, 1.0])
	_tint_gradient.colors = PackedColorArray([
		DEEP_NIGHT, DEEP_NIGHT,
		Color(0.85, 0.72, 0.72),   # dawn
		Color(1.0, 1.0, 1.0),      # day
		Color(1.0, 0.98, 0.94),    # late day
		Color(0.88, 0.72, 0.68),   # dusk
		Color(0.36, 0.38, 0.60),   # nightfall, deeper than before
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
	var morning := _morning_amount(t)
	if morning > 0.0 and not _fog_sprites.is_empty():
		# pre-fill the dawn fog (like force_weather prefills rain): shots
		# teleport and capture faster than the 0.5s spot-refresh cadence
		_fog_wind = (1.0 if randf() < 0.5 else -1.0) * randf_range(6.0, 11.0)
		_was_morning = true
		_fog_refresh = 0.0
		for i in 300:   # ~10 s of sim: past the slow breathe-in, banks settled
			_update_fog(1.0 / 30.0, morning)


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
	var morning := _morning_amount(day_time)
	if morning > 0.0 and not _was_morning:
		# a fresh morning rolls the wind: everything drifts one way today
		_fog_wind = (1.0 if randf() < 0.5 else -1.0) * randf_range(6.0, 11.0)
	_was_morning = morning > 0.0
	_update_fog(delta, morning)
	_update_leaves(delta)

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

	# lightning during heavy rain: sometimes one strike, sometimes a burst of
	# two or three chasing each other, each with its own thunder behind it
	if _raining and rain_intensity > 0.6:
		_lightning_timer -= delta
		if _lightning_timer <= 0.0:
			_lightning_timer = randf_range(18.0, 50.0)
			var strikes := 1
			var roll := randf()
			if roll < 0.18:
				strikes = 3
			elif roll < 0.48:
				strikes = 2
			_strike()
			for s in range(1, strikes):
				get_tree().create_timer(
					randf_range(0.5, 1.3) * float(s)).timeout.connect(_strike)


func _strike() -> void:
	var peak := (0.20 + 0.10 * night_amount) * randf_range(0.8, 1.15)
	var tween := create_tween()
	tween.tween_property(_flash, "color:a", peak, 0.09)
	tween.tween_property(_flash, "color:a", 0.05, 0.16)
	tween.tween_property(_flash, "color:a", peak * 0.75, 0.08)
	tween.tween_property(_flash, "color:a", 0.0, 0.50)
	# tight on the flash's heels — a second of lag read as disconnected
	get_tree().create_timer(randf_range(0.15, 0.5)).timeout.connect(Sfx.play_thunder)


func _night_amount_for(t: float) -> float:
	# tracks the retuned gradient: lamps and the flashlight matter from
	# nightfall (0.64) all the way to the deep-dark plateau (0.80..0.08)
	if t < 0.08:
		return 1.0
	if t < 0.17:
		return 1.0 - smoothstep(0.08, 0.17, t)
	if t < 0.64:
		return 0.0
	if t < 0.80:
		return smoothstep(0.64, 0.80, t)
	return 1.0


func _morning_amount(t: float) -> float:
	# the dawn fog window ("out before the fog lifts" — it's canon)
	if t < 0.10 or t > 0.38:
		return 0.0
	if t < 0.14:
		return smoothstep(0.10, 0.14, t)
	if t > 0.30:
		return 1.0 - smoothstep(0.30, 0.38, t)
	return 1.0


func _update_fog(delta: float, morning: float) -> void:
	if _fog_spots.is_empty():
		return
	var camera := get_viewport().get_camera_2d()
	if camera == null:
		return
	var center := camera.get_screen_center_position()
	var cs := Vector2(_window.content_scale_size)
	if cs.x < 128.0:                 # headless/degenerate window (reports 64):
		cs = Vector2(640, 360)       # assume the base view instead
	var view := cs * 0.5 + Vector2(90, 60)
	_fog_refresh -= delta
	if _fog_refresh <= 0.0:
		# keep a fresh list of spots the camera can actually see — spawning
		# from global random picks was a 0.3% lottery and fog never came
		_fog_refresh = 0.25
		_fog_near.clear()
		for si in _fog_spots.size():
			var s := _fog_spots[si]
			if absf(s.x - center.x) <= view.x and absf(s.y - center.y) <= view.y:
				_fog_near.append(si)
	var spawned := 0
	for i in FOG_COUNT:
		var sprite := _fog_sprites[i]
		if _fog_active[i] == 1:
			sprite.position.x += _fog_wind * _fog_speed[i] * delta
			_fog_age[i] += delta
			var slide := absf(sprite.position.x - _fog_anchor[i].x)
			# a LONG drift before the dissolve even starts, then a slow melt —
			# short lives read as fog blinking in and out (user call)
			var edge := 1.0 - clampf((slide - 90.0) / 110.0, 0.0, 1.0)
			# slow breathe-in from nothing; spawning at full alpha was the pop
			var breathe: float = clampf(_fog_age[i] / FOG_FADE_IN, 0.0, 1.0)
			var out_of_view := absf(sprite.position.x - center.x) > view.x + 80.0 \
				or absf(sprite.position.y - center.y) > view.y + 60.0
			sprite.modulate.a = FOG_ALPHA_MAX * _fog_level[i] * morning \
				* edge * breathe
			if edge <= 0.0 or morning <= 0.0 or out_of_view:
				if sprite.modulate.a <= 0.02:
					_fog_active[i] = 0
					_fog_alive -= 1
					sprite.visible = false
		elif morning > 0.05 and spawned < 3 and not _fog_near.is_empty() \
				and _fog_alive < _fog_near.size() * 4:
			var spot := _fog_spots[_fog_near[randi_range(0, _fog_near.size() - 1)]]
			if _roofed(spot):
				continue
			spawned += 1
			_fog_active[i] = 1
			_fog_alive += 1
			_fog_anchor[i] = spot
			_fog_speed[i] = randf_range(0.7, 1.3)
			_fog_level[i] = randf_range(0.55, 1.0)
			_fog_age[i] = 0.0
			sprite.position = spot + Vector2(randf_range(-18.0, 18.0),
				randf_range(-10.0, 4.0))
			sprite.modulate.a = 0.0
			sprite.visible = true


func _update_leaves(delta: float) -> void:
	if _leaf_trees.is_empty():
		return
	_leaf_timer -= delta
	if _leaf_timer <= 0.0:
		_leaf_timer = randf_range(0.5, 1.4)
		var camera := get_viewport().get_camera_2d()
		if camera != null:
			var center := camera.get_screen_center_position()
			var view := Vector2(_window.content_scale_size) * 0.5 + Vector2(40, 30)
			var tree := _leaf_trees[randi_range(0, _leaf_trees.size() - 1)]
			if absf(tree.x - center.x) <= view.x and absf(tree.y - center.y) <= view.y:
				for i in LEAF_COUNT:
					if not _leaf_state[i]["active"]:
						var state := _leaf_state[i]
						state["active"] = true
						state["t"] = 0.0
						state["dur"] = randf_range(2.2, 3.8)
						state["pattern"] = randi_range(0, 2)
						state["origin"] = tree + Vector2(
							randf_range(-11.0, 11.0), randf_range(-8.0, 2.0))
						_leaf_sprites[i].visible = true
						break
	for i in LEAF_COUNT:
		var state := _leaf_state[i]
		if not state["active"]:
			continue
		var sprite := _leaf_sprites[i]
		state["t"] = float(state["t"]) + delta
		var t: float = state["t"]
		var p: float = t / float(state["dur"])
		if p >= 1.0:
			state["active"] = false
			sprite.visible = false
			continue
		var origin: Vector2 = state["origin"]
		var fall := 30.0
		match int(state["pattern"]):
			0:  # lazy sway
				sprite.position = origin + Vector2(sin(t * 3.1) * 5.0, p * fall)
			1:  # quick flutter zigzag
				sprite.position = origin + Vector2(sin(t * 6.3) * 3.0, p * fall * 0.85)
			2:  # caught by the wind
				sprite.position = origin + Vector2(
					t * 0.9 * _fog_wind + sin(t * 4.0) * 2.0, p * fall * 1.1)
		sprite.frame = int(t * 6.0) % 2
		sprite.modulate.a = 1.0 if p < 0.8 else 1.0 - (p - 0.8) / 0.2


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
