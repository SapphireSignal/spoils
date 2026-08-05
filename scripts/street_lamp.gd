class_name StreetLamp
extends StaticBody2D
## A street lamp. Working lamps light up as night falls: a warm glow sprite on
## the head plus a real PointLight2D pool on the street, with a per-lamp
## randomized flicker (soft shimmer + rare dropouts). Dead lamps are dressing.
## The district is overrun — most lamps do NOT work, and none of them behave
## like their neighbors.

const GLOW_OFFSET := Vector2(12, -49)   # bulb center relative to the base
const LIGHT_OFFSET := Vector2(12, -16)  # light pool aims at the street below
const LIGHT_COLOR := Color("e8c170")

var working := false

var _glow: Sprite2D
var _light: PointLight2D
var _night := 0.0
var _time := 0.0
var _phase := 0.0
var _shimmer_rate := 7.0
var _drop_timer := 0.0
var _drop_left := 0.0
var _rng := RandomNumberGenerator.new()


func setup(is_working: bool, seed_value: int) -> void:
	working = is_working
	add_to_group("street_lamps")
	set_process(false)
	if not working:
		return
	_rng.seed = seed_value
	_phase = _rng.randf_range(0.0, TAU)
	_shimmer_rate = _rng.randf_range(5.0, 11.0)
	_drop_timer = _rng.randf_range(3.0, 14.0)

	_glow = Sprite2D.new()
	_glow.texture = load("res://art/gen/lamp_glow.png")
	_glow.position = GLOW_OFFSET
	_glow.modulate.a = 0.0
	# above the fixture sprite, still y-sorted with the lamp itself
	_glow.z_index = 1
	add_child(_glow)

	_light = PointLight2D.new()
	_light.texture = load("res://art/gen/light_radial.png")
	_light.color = LIGHT_COLOR
	_light.energy = 0.0
	_light.texture_scale = _rng.randf_range(1.3, 1.7)
	_light.position = LIGHT_OFFSET
	# REAL SHADOWS: the wall occluders stop this pool at the building line
	# instead of washing through it. NO PCF blur — a soft shadow edge fights
	# the pixel grid, and the light texture is already smooth alpha, so a hard
	# boundary against it reads correctly.
	_light.shadow_enabled = true
	_light.shadow_filter = Light2D.SHADOW_FILTER_NONE
	add_child(_light)


func set_night(amount: float) -> void:
	_night = amount
	if working:
		var lit := amount > 0.02
		if lit != is_processing():
			set_process(lit)
			if not lit:
				_glow.modulate.a = 0.0
				_light.energy = 0.0


func _process(delta: float) -> void:
	_time += delta
	var flick := 0.92 + 0.08 * sin(_time * _shimmer_rate + _phase) \
		+ 0.03 * sin(_time * 23.0 + _phase * 2.0)
	_drop_timer -= delta
	if _drop_timer <= 0.0:
		_drop_left = _rng.randf_range(0.05, 0.28)
		_drop_timer = _rng.randf_range(4.0, 16.0)
	if _drop_left > 0.0:
		_drop_left -= delta
		flick *= 0.12 if fmod(_time * 41.0, 1.0) < 0.6 else 0.55
	_glow.modulate.a = clampf(_night * flick, 0.0, 1.0)
	_light.energy = 1.35 * _night * flick  # keeps its pool in the darker night
