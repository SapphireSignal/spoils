class_name PowerBox
extends Node2D
## The one broken power box in the district: lid ajar, wires down, and every
## few seconds it spits a little arc of sparks. A repair quest waiting for
## its milestone. Quiet on purpose — sparks are seen, not heard.

var _spark: Sprite2D
var _glow: PointLight2D
var _timer := 0.0
var _burst_left := 0.0
var _flick := 0.0                       # holds each arc frame a few frames
var _spark_tex: Array[Texture2D] = []   # cached; not re-fetched mid-burst


func setup(box_name: String) -> void:
	var body := Sprite2D.new()
	body.texture = load("res://art/gen/%s.png" % box_name)
	body.centered = false
	var info_offset := Vector2(-9, -21)
	body.offset = info_offset
	add_child(body)
	for i in 3:
		_spark_tex.append(load("res://art/gen/spark_%d.png" % i))
	_spark = Sprite2D.new()
	_spark.texture = _spark_tex[0]
	_spark.position = Vector2(-2.0, -9.0)
	_spark.visible = false
	add_child(_spark)
	_glow = PointLight2D.new()
	_glow.texture = load("res://art/gen/light_radial.png")
	_glow.texture_scale = 0.22
	_glow.color = Color("e8c170")
	_glow.energy = 0.0
	_glow.position = _spark.position
	add_child(_glow)
	_timer = randf_range(1.0, 3.0)


func _process(delta: float) -> void:
	if _burst_left > 0.0:
		_burst_left -= delta
		# a real arc JUMPS between shapes — rerolling the texture every frame
		# at 240 Hz read as shimmer, not electricity
		_flick -= delta
		if _flick <= 0.0:
			_flick = randf_range(0.045, 0.08)
			_spark.texture = _spark_tex[randi() % 3]
		_spark.visible = fmod(_burst_left, 0.08) > 0.03
		_glow.energy = 0.5 if _spark.visible else 0.15
		if _burst_left <= 0.0:
			_spark.visible = false
			_glow.energy = 0.0
			_timer = randf_range(1.2, 4.0)
		return
	_timer -= delta
	if _timer <= 0.0:
		_burst_left = randf_range(0.18, 0.4)
