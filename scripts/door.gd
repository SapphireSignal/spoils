class_name Door
extends StaticBody2D
## An interactive building door. Closed by default and part of the wall line;
## the player walks up and presses interact to swing it open (4-frame
## animation), and again to close it. The thin wall-line collider is disabled
## the moment it starts opening and re-enabled only once fully shut.

const FRAMES := 4
const FRAME_TIME := 0.06
const INTERACT_RANGE := 40.0

var _sprite: Sprite2D
var _poly: CollisionPolygon2D
var _open := false
var _animating := false
var _frame := 0
var _frame_timer := 0.0


func setup(texture: Texture2D, origin: Vector2, poly_points: PackedVector2Array) -> void:
	_sprite = Sprite2D.new()
	_sprite.texture = texture
	_sprite.hframes = FRAMES
	_sprite.centered = false
	_sprite.offset = -origin
	_sprite.frame = 0
	add_child(_sprite)
	_poly = CollisionPolygon2D.new()
	_poly.polygon = poly_points
	add_child(_poly)
	add_to_group("doors")
	set_process(false)


func is_open() -> bool:
	return _open


func toggle() -> void:
	if _animating:
		return
	_animating = true
	_open = not _open
	if _open:
		# passable immediately — the leaf is already swinging out of the way
		_poly.set_deferred("disabled", true)
	Sfx.play_door(_open)
	_frame_timer = 0.0
	set_process(true)


func _process(delta: float) -> void:
	_frame_timer += delta
	if _frame_timer < FRAME_TIME:
		return
	_frame_timer -= FRAME_TIME
	var target := FRAMES - 1 if _open else 0
	if _frame == target:
		_animating = false
		set_process(false)
		if not _open:
			_poly.set_deferred("disabled", false)
		return
	_frame += 1 if target > _frame else -1
	_sprite.frame = _frame
