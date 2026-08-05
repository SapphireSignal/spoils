class_name Door
extends StaticBody2D
## An interactive building door. Closed by default and part of the wall line;
## the player walks up and presses interact to swing it open (4-frame
## animation), and again to close it.
##
## The panel is solid in EVERY state. Shut, it seals the doorway. Open, it
## stands where the art actually draws it — a quarter turn into the room.
## Mid-swing both are solid, so a door that still looks closed cannot be
## walked through. The jamb boards beside the opening are always solid.
## Every polygon comes from the manifest; none of it is derived here.

const FRAMES := 4          # frames per swing; the sheet holds two swings
const FRAME_TIME := 0.06

var _sprite: Sprite2D
var _occ: LightOccluder2D          # blocks LIGHT exactly when _poly blocks bodies
var _occ_poly: OccluderPolygon2D
var _poly: CollisionPolygon2D      # the leaf across the doorway, closed
var _leaf: CollisionPolygon2D      # the leaf standing open INTO the room
var _leaf_out: CollisionPolygon2D  # ...and open out into the street
var _open := false
var _swing_out := false            # which way this opening is going
var _animating := false
var _frame := 0
var _frame_timer := 0.0


func setup(texture: Texture2D, origin: Vector2, poly_points: PackedVector2Array,
		open_points: PackedVector2Array, open_out_points: PackedVector2Array,
		jambs: Array) -> void:
	## Every polygon here comes from the manifest, because the GENERATOR is
	## what knows where the art puts the panel. The previous cut derived the
	## swung leaf in here and mirrored it for south doors — the collider sat
	## a cell away from the visible panel, which is why open doors could be
	## walked straight through.
	_sprite = Sprite2D.new()
	_sprite.texture = texture
	_sprite.hframes = FRAMES * 2
	_sprite.centered = false
	_sprite.offset = -origin
	_sprite.frame = 0
	add_child(_sprite)
	_poly = CollisionPolygon2D.new()
	_poly.polygon = poly_points
	add_child(_poly)
	# The shut panel blocks LIGHT as well as bodies, off the SAME manifest
	# polygon — so the shadow and the collider can never disagree about where
	# the door is. Toggled in lockstep with _poly in _process: a doorway you
	# can walk through is one you can see through.
	_occ_poly = OccluderPolygon2D.new()
	_occ_poly.polygon = poly_points
	_occ_poly.cull_mode = OccluderPolygon2D.CULL_DISABLED
	_occ = LightOccluder2D.new()
	_occ.occluder = _occ_poly
	add_child(_occ)
	# one swung leaf per direction; only the one actually being used is on
	_leaf = CollisionPolygon2D.new()
	_leaf.polygon = open_points
	_leaf.disabled = true
	add_child(_leaf)
	_leaf_out = CollisionPolygon2D.new()
	_leaf_out.polygon = open_out_points
	_leaf_out.disabled = true
	add_child(_leaf_out)
	# the jamb boards beside the opening are drawn solid in every frame, so
	# they stay solid in every state
	for jamb in jambs:
		var stub := CollisionPolygon2D.new()
		stub.polygon = jamb
		add_child(stub)
	add_to_group("doors")
	set_process(false)


func is_open() -> bool:
	return _open


func _panel_center(poly: CollisionPolygon2D) -> Vector2:
	var sum := Vector2.ZERO
	for p in poly.polygon:
		sum += p
	return to_global(sum / float(poly.polygon.size()))


func _panel_normal(poly: CollisionPolygon2D) -> Vector2:
	## Square across the panel in SCREEN space — the shortest line that
	## crosses it, which is what you drive along to prove it is solid.
	var along: Vector2 = poly.polygon[1] - poly.polygon[0]
	return Vector2(-along.y, along.x).normalized()


func doorway_center() -> Vector2:
	return _panel_center(_poly)


func doorway_normal() -> Vector2:
	## Square across the WALL PLANE. Use this to decide whether something
	## actually crossed the wall — never the through-axis. The two iso ground
	## axes sit only 53 degrees apart on screen, so sliding ALONG a wall
	## scores 0.6x on the through-axis and a legitimate slide reads as
	## walking through the door.
	return _panel_normal(_poly)


func doorway_through() -> Vector2:
	## The way you actually WALK through this doorway. Not the doorway's
	## screen normal — in iso the two ground axes are 53 degrees apart on
	## screen, so the perpendicular-looking direction is not the one that
	## crosses the wall. The open leaf swings a quarter turn in the ground
	## plane, so its along vector IS the through direction (pointing in).
	var along: Vector2 = _leaf.polygon[1] - _leaf.polygon[0]
	return along.normalized()


func doorway_along() -> Vector2:
	## Along the wall line, so the smoke can sweep sideways across the gap.
	## Starts at the far edge of a jamb, not at the hinge.
	var along: Vector2 = _poly.polygon[1] - _poly.polygon[0]
	return along.normalized()


func _active_leaf() -> CollisionPolygon2D:
	return _leaf_out if _swing_out else _leaf


func leaf_center() -> Vector2:
	return _panel_center(_active_leaf())


func leaf_normal() -> Vector2:
	return _panel_normal(_active_leaf())


func swings_out() -> bool:
	return _swing_out


func leaf_is_solid() -> bool:
	## true while SOMETHING of this door is blocking — the panel across
	## the doorway when shut, the swung panel when open. Never both off.
	return not _poly.disabled or not _active_leaf().disabled


func toggle(from: Vector2 = Vector2.INF) -> void:
	if _animating:
		return
	_animating = true
	_open = not _open
	if _open:
		# A door swings AWAY from whoever opens it (user call): stood
		# outside it opens into the room, stood inside it opens out to the
		# street. doorway_through() points INTO the room, so a positive dot
		# means the opener is already inside and the leaf goes the other way.
		if from.x < INF:
			_swing_out = (from - global_position).dot(doorway_through()) > 0.0
		# The swung panel becomes solid immediately, but the doorway stays
		# SHUT until the leaf has actually finished swinging clear. Opening
		# the doorway on frame one let you walk through a door that still
		# looked closed for its whole 0.24s animation — a small version of
		# the exact complaint this whole change is about. _poly comes off in
		# _process once the swing lands.
		_active_leaf().set_deferred("disabled", false)
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
		if _open:
			_poly.set_deferred("disabled", true)    # the gap is real now
			_occ.occluder = null                    # ...and light comes through
		else:
			_poly.set_deferred("disabled", false)
			_occ.occluder = _occ_poly
			_leaf.set_deferred("disabled", true)
			_leaf_out.set_deferred("disabled", true)
		return
	_frame += 1 if target > _frame else -1
	# the outward swing lives in the second half of the sheet
	_sprite.frame = (FRAMES if _swing_out else 0) + _frame
