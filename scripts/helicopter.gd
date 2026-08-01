class_name Helicopter
extends Node2D
## The lift. Flies in over the treeline with its rotor turning, hangs a
## rope, and takes the raider out. Purely presentational — Extraction
## tweens it around and the debrief screen follows.

const ROTOR_FPS := 22.0

var _sprite: Sprite2D
var _rope: Line2D
var _anim := 0.0
var _rope_len := 0.0


func _ready() -> void:
	_sprite = Sprite2D.new()
	_sprite.texture = load("res://art/gen/helicopter.png")
	_sprite.hframes = 3
	_sprite.centered = false
	_sprite.offset = Vector2(-46, -47)
	add_child(_sprite)
	_rope = Line2D.new()
	_rope.width = 1.0
	_rope.default_color = Color("341c27")
	_rope.visible = false
	add_child(_rope)


func drop_rope(length: float) -> void:
	_rope_len = 0.0
	_rope.visible = true
	var tw := create_tween()
	tw.tween_method(_set_rope, 0.0, length, 0.7)


func raise_rope() -> void:
	var tw := create_tween()
	tw.tween_method(_set_rope, _rope_len, 0.0, 0.6)
	tw.tween_callback(func() -> void: _rope.visible = false)


func _set_rope(length: float) -> void:
	_rope_len = length
	_rope.points = PackedVector2Array([Vector2(0, -4), Vector2(0, length)])


func _process(delta: float) -> void:
	_anim += delta * ROTOR_FPS
	_sprite.frame = int(_anim) % 3
