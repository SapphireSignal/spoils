class_name EnvironmentSystem
extends Node
## Living world: day/night tint cycle, random rain spells with visible ground
## impacts and occasional subtle lightning, and puddles that form while it
## rains and dry out when the sun returns.

const DAY_SECONDS := 480.0          # one full day/night cycle
const RAIN_ALPHA := 0.85

var day_time := 0.18                # 0..1, start in the morning
var rain_intensity := 0.0           # 0..1, ramps in and out
var _raining := false
var _weather_timer := 0.0
var _lightning_timer := 999.0
var _flash: ColorRect
var _tint: CanvasModulate
var _rain: CPUParticles2D
var _impacts: CPUParticles2D
var _puddles: Array[Sprite2D] = []
var _tint_gradient: Gradient


func setup(root: Node2D, floor_layer: TileMapLayer, puddle_spots: Array) -> void:
	_tint = CanvasModulate.new()
	root.add_child(_tint)

	# puddles live just above the floor, below the y-sorted world
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

	var sky := CanvasLayer.new()
	sky.layer = 30
	add_child(sky)
	var view := Vector2(root.get_window().content_scale_size)

	_rain = CPUParticles2D.new()
	_rain.texture = load("res://art/gen/rain_streak.png")
	_rain.amount = 340
	_rain.lifetime = 0.9
	_rain.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_rain.emission_rect_extents = Vector2(view.x / 2.0 + 100.0, 12)
	_rain.position = Vector2(view.x / 2.0, -30)
	_rain.direction = Vector2(-0.12, 1)
	_rain.spread = 3.0
	_rain.gravity = Vector2.ZERO
	_rain.initial_velocity_min = 520.0
	_rain.initial_velocity_max = 640.0
	_rain.emitting = false
	sky.add_child(_rain)

	# impact ticks where drops meet the ground — tiny, everywhere, brief
	_impacts = CPUParticles2D.new()
	_impacts.texture = load("res://art/gen/dust.png")
	_impacts.amount = 130
	_impacts.lifetime = 0.30
	_impacts.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_impacts.emission_rect_extents = Vector2(view.x / 2.0 + 40.0, view.y / 2.0 + 40.0)
	_impacts.position = view / 2.0
	_impacts.gravity = Vector2.ZERO
	_impacts.initial_velocity_min = 0.0
	_impacts.initial_velocity_max = 0.0
	_impacts.scale_amount_min = 0.6
	_impacts.scale_amount_max = 1.4
	_impacts.color = Color("73bed3", 0.75)
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	_impacts.color_ramp = ramp
	_impacts.emitting = false
	sky.add_child(_impacts)

	_flash = ColorRect.new()
	_flash.color = Color("a4dddb", 0.0)
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sky.add_child(_flash)

	_tint_gradient = Gradient.new()
	_tint_gradient.set_color(0, Color(0.52, 0.58, 0.78))   # deep night
	_tint_gradient.add_point(0.10, Color(0.85, 0.72, 0.72))  # dawn
	_tint_gradient.add_point(0.22, Color(1.0, 1.0, 1.0))     # day
	_tint_gradient.add_point(0.58, Color(1.0, 0.98, 0.94))   # late day
	_tint_gradient.add_point(0.68, Color(0.88, 0.72, 0.68))  # dusk
	_tint_gradient.add_point(0.80, Color(0.55, 0.60, 0.80))  # nightfall
	_tint_gradient.set_color(1, Color(0.52, 0.58, 0.78))
	_weather_timer = randf_range(45.0, 160.0)
	add_to_group("environment")


func force_weather(rain_on: bool) -> void:  # harness hook
	_raining = rain_on
	rain_intensity = 1.0 if rain_on else 0.0
	_weather_timer = 9999.0
	for puddle in _puddles:
		puddle.modulate.a = 0.9 if rain_on else 0.0


func force_time(t: float) -> void:  # harness hook, 0..1
	day_time = t


func _process(delta: float) -> void:
	day_time = fmod(day_time + delta / DAY_SECONDS, 1.0)
	var tint := _tint_gradient.sample(day_time)
	if rain_intensity > 0.0:  # storms darken the world a touch
		tint = tint.darkened(0.12 * rain_intensity)
	_tint.color = tint

	# weather state machine
	_weather_timer -= delta
	if _weather_timer <= 0.0:
		_raining = not _raining
		_weather_timer = randf_range(50.0, 130.0) if _raining \
			else randf_range(120.0, 300.0)
		if _raining:
			_lightning_timer = randf_range(12.0, 40.0)
	rain_intensity = move_toward(rain_intensity, 1.0 if _raining else 0.0, delta / 6.0)

	_rain.emitting = rain_intensity > 0.05
	_impacts.emitting = rain_intensity > 0.15
	_rain.modulate.a = RAIN_ALPHA * rain_intensity
	_impacts.modulate.a = rain_intensity

	# puddles fill while raining, dry out under the sun
	var puddle_target := clampf(rain_intensity, 0.0, 0.9)
	var rate := delta / (22.0 if _raining else 45.0)
	for puddle in _puddles:
		puddle.modulate.a = move_toward(puddle.modulate.a, puddle_target if _raining
			else 0.0, rate)

	# subtle lightning during rain
	if _raining and rain_intensity > 0.6:
		_lightning_timer -= delta
		if _lightning_timer <= 0.0:
			_lightning_timer = randf_range(16.0, 45.0)
			var tween := create_tween()
			tween.tween_property(_flash, "color:a", 0.18, 0.05)
			tween.tween_property(_flash, "color:a", 0.02, 0.10)
			tween.tween_property(_flash, "color:a", 0.12, 0.06)
			tween.tween_property(_flash, "color:a", 0.0, 0.22)
