class_name Door
extends StaticBody2D
## An interactive building door. Closed by default and part of the wall line;
## the player walks up and presses interact to swing it open (4-frame
## animation), and again to close it. The thin wall-line collider is disabled
## the moment it starts opening and re-enabled only once fully shut.

const FRAMES := 4
const FRAME_TIME := 0.06

var _sprite: Sprite2D
var _poly: CollisionPolygon2D    # the leaf across the doorway, closed
var _leaf: CollisionPolygon2D    # the leaf where it stands, open
var _open := false
var _animating := false
var _frame := 0
var _frame_timer := 0.0


func _swung_points(closed: PackedVector2Array) -> PackedVector2Array:
	## The leaf where it STANDS once it's open. A door that swings clear
	## still occupies space — you walk through the opening, never through
	## the panel (user: "i can just walk through opened doors").
	## The closed panel is a parallelogram: p0->p1 runs along the wall and
	## p0->p3 is its thickness. Swinging it is the same panel turned onto
	## the other iso axis, which is (-x, +y) of the along vector.
	if closed.size() < 4:
		return closed
	var hinge := closed[0]
	var along := closed[1] - closed[0]
	var thick := closed[3] - closed[0]
	var swung := Vector2(-along.x, along.y)
	return PackedVector2Array([hinge, hinge + swung,
		hinge + swung + thick, hinge + thick])


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
	# the swung leaf gets its own body, switched on only while open
	_leaf = CollisionPolygon2D.new()
	_leaf.polygon = _swung_points(poly_points)
	_leaf.disabled = true
	add_child(_leaf)
	add_to_group("doors")
	set_process(false)


func is_open() -> bool:
	return _open


func leaf_is_solid() -> bool:
	## true while SOMETHING of this door is blocking — the panel across
	## the doorway when shut, the swung panel when open. Never both off.
	return not _poly.disabled or not _leaf.disabled


func toggle() -> void:
	if _animating:
		return
	_animating = true
	_open = not _open
	if _open:
		# the doorway opens, but the PANEL never stops being solid — it
		# just stands somewhere else now (user: doors should have
		# collision all the time, not only when they're shut)
		_poly.set_deferred("disabled", true)
		_leaf.set_deferred("disabled", false)
	Sfx.play_door(_open)
	_frame_timer = 0.0
	set_process(true)


func force_closed() -> void:
	# the stairs slam this shut behind a climber even if the leaf is still
	# mid-swing — toggle() refuses while animating, and an open ground-floor
	# doorway under a second story lets you walk out into the air
	if not _open:
		return
	_open = false
	Sfx.play_door(false)
	_animating = true
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
			_leaf.set_deferred("disabled", true)
		return
	_frame += 1 if target > _frame else -1
	_sprite.frame = _frame
