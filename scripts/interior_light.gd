class_name InteriorLight
extends Node2D
## A room's ceiling light. Comes on with the dark, the same broadcast the
## street lamps ride, and a third of them flicker — the district's power
## is not well. Every one of these has a CABLE the builder lays cell by
## cell to its building's exterior power box (standing rule: nothing in
## this world is powered by magic).

const LIGHT_COLOR := Color("e8c170")

var flickers := false

var _glow: Sprite2D
var _light: PointLight2D
var _rng := RandomNumberGenerator.new()
var _night := 0.0
var _time := 0.0
var _phase := 0.0
var _drop_timer := 0.0
var _drop_left := 0.0


func setup(sprite_offset: Vector2, seed_value: int, does_flicker: bool) -> void:
	_rng.seed = seed_value
	flickers = does_flicker
	_phase = _rng.randf() * TAU
	_drop_timer = _rng.randf_range(2.0, 11.0)

	var body := Sprite2D.new()
	body.texture = load("res://art/gen/interior_lamp.png")
	body.centered = false
	body.offset = sprite_offset
	add_child(body)

	_glow = Sprite2D.new()
	_glow.texture = load("res://art/gen/lamp_glow.png")
	_glow.modulate = Color(LIGHT_COLOR.r, LIGHT_COLOR.g, LIGHT_COLOR.b, 0.0)
	_glow.position = Vector2(0.0, -8.0)
	_glow.z_index = 1
	add_child(_glow)

	_light = PointLight2D.new()
	_light.texture = load("res://art/gen/light_radial.png")
	_light.color = LIGHT_COLOR
	_light.energy = 0.0
	# deliberately tight: a room light lights its ROOM. A wide pool washed
	# straight through the walls and lit the street outside.
	_light.texture_scale = _rng.randf_range(0.55, 0.75)
	_light.position = Vector2(0.0, -6.0)
	add_child(_light)

	add_to_group("street_lamps")   # rides the environment's night broadcast
	set_process(false)


func set_night(amount: float) -> void:
	_night = amount
	var lit := amount > 0.02
	if lit != is_processing():
		set_process(lit)
		if not lit:
			_glow.modulate.a = 0.0
			_light.energy = 0.0


func _process(delta: float) -> void:
	_time += delta
	var flick := 1.0
	if flickers:
		flick = 0.94 + 0.06 * sin(_time * 5.5 + _phase)
		_drop_timer -= delta
		if _drop_timer <= 0.0:
			_drop_left = _rng.randf_range(0.06, 0.3)
			_drop_timer = _rng.randf_range(3.5, 14.0)
		if _drop_left > 0.0:
			_drop_left -= delta
			flick *= 0.15 if fmod(_time * 37.0, 1.0) < 0.55 else 0.6
	_glow.modulate.a = clampf(_night * flick * 0.75, 0.0, 1.0)
	_light.energy = 0.9 * _night * flick
