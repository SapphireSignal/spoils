class_name Player
extends CharacterBody2D
## Raider avatar: 8-direction WASD movement with iso perspective squash.
## Built entirely in code (no .tscn) — the whole game is code-authored.

const SPEED := 120.0
const Y_SQUASH := 0.6  # screen-vertical speed factor; sells iso perspective
const WALK_FPS := 8.0

var camera: Camera2D

var _sprite: Sprite2D
var _dir_index := 2  # sheet rows are E,SE,S,SW,W,NW,N,NE — start facing S
var _anim_time := 0.0


func _init() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING

	var shadow := Sprite2D.new()
	shadow.texture = load("res://art/gen/shadow.png")
	shadow.centered = false
	shadow.offset = Vector2(-12, -6)
	add_child(shadow)

	_sprite = Sprite2D.new()
	_sprite.texture = load("res://art/gen/char.png")
	_sprite.hframes = 5
	_sprite.vframes = 8
	_sprite.frame = _dir_index * 5
	_sprite.offset = Vector2(0, -17)  # feet (frame y=37 of 40) sit on origin
	add_child(_sprite)

	var shape := CircleShape2D.new()
	shape.radius = 5.0
	var collider := CollisionShape2D.new()
	collider.shape = shape
	collider.position = Vector2(0, -3)
	add_child(collider)

	camera = Camera2D.new()
	camera.position = Vector2(0, -16)
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 8.0
	add_child(camera)


func _physics_process(delta: float) -> void:
	var input_vec := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	velocity = Vector2(input_vec.x, input_vec.y * Y_SQUASH) * SPEED
	move_and_slide()
	_animate(input_vec, delta)


func _animate(input_vec: Vector2, delta: float) -> void:
	if input_vec.length_squared() > 0.01:
		_dir_index = wrapi(roundi(rad_to_deg(input_vec.angle()) / 45.0), 0, 8)
		_anim_time += delta
		var step := int(_anim_time * WALK_FPS) % 4
		_sprite.frame = _dir_index * 5 + 1 + step
	else:
		_anim_time = 0.0
		_sprite.frame = _dir_index * 5
