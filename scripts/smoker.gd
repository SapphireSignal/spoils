class_name Smoker
extends Node2D
## The gallery regular: sits on his bench, spray can in one hand, and works
## a cigarette with the other. Idle → drag (ember flares) → exhale, with
## little smoke wisps drifting off the exhale. Never in a hurry.

var _sprite: Sprite2D
var _phase := 0          # 0 idle, 1 drag, 2 exhale
var _timer := 0.0
var _wisps: Array[Dictionary] = []


func _ready() -> void:
	_sprite = Sprite2D.new()
	_sprite.texture = load("res://art/gen/smoker.png")
	_sprite.hframes = 3
	_sprite.centered = false
	_sprite.offset = Vector2(-10, -22)
	add_child(_sprite)
	_timer = randf_range(2.0, 5.0)


func _process(delta: float) -> void:
	_timer -= delta
	if _timer <= 0.0:
		match _phase:
			0:
				_phase = 1
				_timer = 0.8            # the drag
			1:
				_phase = 2
				_timer = 0.6            # the exhale
				_spawn_wisps()
			2:
				_phase = 0
				_timer = randf_range(2.5, 6.0)
		_sprite.frame = _phase
	var i := _wisps.size() - 1
	while i >= 0:
		var wisp: Dictionary = _wisps[i]
		var sprite := wisp["sprite"] as Sprite2D
		wisp["age"] = float(wisp["age"]) + delta
		var age: float = wisp["age"]
		if age >= 1.4:
			sprite.queue_free()
			_wisps.remove_at(i)
		else:
			sprite.position += Vector2(-3.0, -9.0) * delta
			sprite.modulate.a = 0.5 * (1.0 - age / 1.4)
		i -= 1


func _spawn_wisps() -> void:
	for w in randi_range(2, 3):
		var wisp := Sprite2D.new()
		wisp.texture = load("res://art/gen/dust.png")
		wisp.modulate = Color("a8b5b2", 0.5)
		wisp.position = Vector2(5.0 + randf_range(-1.0, 1.0),
			-15.0 + randf_range(-2.0, 0.0))
		add_child(wisp)
		_wisps.append({"sprite": wisp, "age": -0.25 * w})
