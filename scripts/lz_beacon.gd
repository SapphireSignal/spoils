class_name LzBeacon
extends Node2D
## The lift's marker: green smoke curling up out of the clearing and a
## low green glow on the ground. Visible from a street away — it is the
## thing you run toward when you're carrying too much to fight.

const PUFF_LIFE := 3.2
const SPAWN_EVERY := 0.16
const SMOKE := Color(0.459, 0.655, 0.263)
# past this the smoke can't be on screen at any zoom — the column stops
# simulating entirely (it used to churn sprites for the whole raid)
const SLEEP_DIST := 700.0

var _puffs: Array[Dictionary] = []
var _timer := 0.0
var _glow: PointLight2D
var _wash: Sprite2D
var _smoke_tex: Array[Texture2D] = []
var _dormant := false


func _ready() -> void:
	# the soft fog puffs, not dust specks — dust reads as grit at this
	# size, and this has to be visible from the next street over
	for i in 3:
		_smoke_tex.append(load("res://art/gen/fog_%d.png" % i))
	var radial: Texture2D = load("res://art/gen/light_radial.png")
	# an ADDITIVE ground wash: a PointLight2D alone only shows once the
	# world is dark, and this marker has to read at noon too
	_wash = Sprite2D.new()
	_wash.texture = radial
	_wash.modulate = Color(SMOKE.r, SMOKE.g, SMOKE.b, 0.30)
	_wash.scale = Vector2(2.4, 1.4)      # squashed to sit on the iso ground
	var additive := CanvasItemMaterial.new()
	additive.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_wash.material = additive
	_wash.z_index = -1
	add_child(_wash)
	_glow = PointLight2D.new()
	_glow.texture = radial
	_glow.color = SMOKE
	_glow.energy = 0.55
	_glow.texture_scale = 1.9
	add_child(_glow)


func _process(delta: float) -> void:
	var camera := get_viewport().get_camera_2d()
	if camera != null and camera.get_screen_center_position() \
			.distance_squared_to(global_position) > SLEEP_DIST * SLEEP_DIST:
		if not _dormant:
			_dormant = true
			for puff in _puffs:   # offscreen anyway; fresh ones fade back in
				(puff["sprite"] as Sprite2D).queue_free()
			_puffs.clear()
		return
	_dormant = false
	var breathe := sin(float(Time.get_ticks_msec()) / 620.0)
	_glow.energy = 0.42 + 0.16 * breathe
	_wash.modulate.a = 0.26 + 0.08 * breathe
	_timer -= delta
	if _timer <= 0.0:
		_timer = SPAWN_EVERY
		_spawn()
	var i := _puffs.size() - 1
	while i >= 0:
		var puff: Dictionary = _puffs[i]
		var sprite := puff["sprite"] as Sprite2D
		puff["age"] = float(puff["age"]) + delta
		var age: float = puff["age"]
		if age >= PUFF_LIFE:
			sprite.queue_free()
			_puffs.remove_at(i)
		else:
			var t := age / PUFF_LIFE
			sprite.position += (puff["drift"] as Vector2) * delta
			sprite.modulate.a = 0.55 * (1.0 - t) * minf(1.0, age * 3.0)
			sprite.scale = Vector2.ONE * (0.7 + t * 1.3)   # it billows
		i -= 1


func _spawn() -> void:
	var sprite := Sprite2D.new()
	sprite.texture = _smoke_tex[randi() % _smoke_tex.size()]
	sprite.modulate = Color(SMOKE.r, SMOKE.g, SMOKE.b, 0.0)
	sprite.position = Vector2(randf_range(-9.0, 9.0), randf_range(-4.0, 4.0))
	sprite.z_index = 8
	add_child(sprite)
	_puffs.append({"sprite": sprite, "age": 0.0,
		"drift": Vector2(randf_range(-11.0, 5.0), randf_range(-30.0, -18.0))})
