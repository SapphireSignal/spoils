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
const JAMB_EPS := 0.01     # sub-pixel; decides leaf-vs-jamb ties ONLY

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
var _sort_shift := 0.0             # node pushed off the wall line, Y-SORT ONLY
var _floor_blocked := false        # sealed for an UPPER floor, state untouched


func setup(texture: Texture2D, origin: Vector2, poly_points: PackedVector2Array,
		open_points: PackedVector2Array, open_out_points: PackedVector2Array,
		jambs: Array) -> void:
	## Every polygon here comes from the manifest, because the GENERATOR is
	## what knows where the art puts the panel. The previous cut derived the
	## swung leaf in here and mirrored it for south doors — the collider sat
	## a cell away from the visible panel, which is why open doors could be
	## walked straight through.
	# the sprite carries this door's depth on its own (see _apply_sort_shift),
	# so the body itself never has to move to sort correctly
	y_sort_enabled = true
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
	# poly.position is included for completeness; the colliders no longer carry
	# any y-sort compensation, because only the SPRITE moves now.
	var sum := Vector2.ZERO
	for p in poly.polygon:
		sum += p
	return to_global(poly.position + sum / float(poly.polygon.size()))


func _panel_normal(poly: CollisionPolygon2D) -> Vector2:
	## Square across the panel in SCREEN space — the shortest line that
	## crosses it, which is what you drive along to prove it is solid.
	var along: Vector2 = poly.polygon[1] - poly.polygon[0]
	return Vector2(-along.y, along.x).normalized()


func wall_position() -> Vector2:
	## Where this door sits IN THE WALL LINE, with the y-sort shift taken back
	## out. `global_position` is not that while the door is open — it is pushed
	## to wherever the leaf stands so the leaf sorts correctly. Anything asking
	## "which cell is this door in" or "how far is the player from it" wants
	## THIS; the node's own position answers a different question now.
	return global_position


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


func doorway_sealed() -> bool:
	## Is the panel across the doorway solid right now? A LIVENESS FIGURE for
	## the floor probe: it separates "the seal never got applied" from "the
	## seal is on and my movement test is measuring the wrong axis".
	return not _poly.disabled


func sort_shift() -> float:
	## How far the node is currently pushed off the wall line for y-sort. Zero
	## when shut. Exposed so a probe can report a liveness figure beside its
	## verdict — a "no disagreements" result read off a door that never moved
	## has fooled this project three times.
	return _sort_shift


func _leaf_sort_depth() -> float:
	## How far toward the camera the OPEN leaf actually stands, taken from the
	## manifest polygon rather than derived here — the door-collider lesson: a
	## hand-derived offset is how the open leaf's collider ended up a cell from
	## its own art for a whole release.
	##
	## Two of the four kind/axis combinations come out ZERO and want no shift
	## at all: measured off the manifest, an 'x' door swings out along -x and a
	## 'y' door swings in along -x, neither of which moves in y. The other two
	## move a full 10 px — 'y' swinging out toward the camera (+10), 'x'
	## swinging in away from it (-10). Reading the centroid covers all four
	## without a special case anywhere.
	## The epsilon settles the two cases where that depth is exactly ZERO and
	## the leaf would TIE with the jamb boards - which are their own piece at
	## the wall line now, so a tie is reachable and y-sort has no defined
	## winner for one. The SIGN must match what the generator used to
	## guarantee by draw order, and still states in make_door_strip: swinging
	## OUT the leaf covers the jamb, swinging IN the jamb covers the leaf.
	## Far below a pixel, so it cannot move where anything rasterises.
	##
	## THE LEADING EDGE, NOT THE CENTROID. On one of the two wall facings the
	## open leaf STRADDLES the wall line - hinge end at it, far end standing
	## out in front - so its centroid depth is exactly 0 and the whole sprite
	## sorted level with the wall it was standing in front of. Half the leaf
	## then drew behind its own building: *"the door clips in the wall when its
	## opened outside"*, and it is 8 of the 16 doors in the district.
	##
	## Taking the extreme in the direction of travel makes the leaf clear its
	## own wall by construction, whichever way it swings and whichever facing
	## it is on.
	var span := _leaf_span(_active_leaf())
	var eps := JAMB_EPS if _swing_out else -JAMB_EPS
	return (span.y if _swing_out else span.x) + eps


func _leaf_span(poly: CollisionPolygon2D) -> Vector2:
	var lo := INF
	var hi := -INF
	for p in poly.polygon:
		lo = minf(lo, p.y)
		hi = maxf(hi, p.y)
	return Vector2(lo, hi)


func _poly_depth(poly: CollisionPolygon2D) -> float:
	var sum := 0.0
	for p in poly.polygon:
		sum += p.y
	return sum / float(poly.polygon.size())


func leaf_depth(out_swing: bool) -> float:
	## What the shift WOULD be if this door swung that way, without opening it.
	## A probe needs this to pick a door where the bug can actually happen: two
	## of the four kind/axis combinations swing sideways on screen and shift by
	## zero, and a screenshot of one of those looks perfect while proving
	## nothing at all.
	return _poly_depth(_leaf_out if out_swing else _leaf)


func leaf_span(out_swing: bool) -> Vector2:
	## The lowest and highest y the leaf covers, for the probe's door table.
	## THE CENTROID IS NOT ENOUGH: on one facing the open leaf STRADDLES the
	## wall line, so its centroid depth is zero while part of it genuinely
	## stands in front of the wall.
	return _leaf_span(_leaf_out if out_swing else _leaf)


func _apply_sort_shift(shift: float) -> void:
	## THE OPEN LEAF COULD NEVER HIDE ANYTHING (user: "i can still see my
	## character when he should be behind the door"). Y-sort orders by the
	## NODE, and the node sits on the wall line while an open leaf stands up to
	## 10 px off it — so a player standing behind the leaf out-sorted it every
	## time. Nothing about the art was wrong; the sort ANCHOR was.
	##
	## The fix is CLAUDE.md's second-floor pattern verbatim: give the piece its
	## own sort position and offset the art, never the node. Push the node to
	## where the leaf really is, then pull every child back by the same amount.
	## The sort key moves; not one pixel of art or collision does.
	##
	## Compensating EVERY child rather than a named list is deliberate — a
	## child added here later is then correct by construction instead of
	## silently sliding off the wall whenever a door opens.
	var delta := shift - _sort_shift
	if is_zero_approx(delta):
		return
	# ONLY THE SPRITE MOVES. The first cut moved this NODE and pulled every
	# child back to compensate, which is correct on paper - the colliders end
	# up in the same global place - but this node is a StaticBody2D, and
	# nudging a static body the player is resting against depenetrates them.
	# Measured standing 6 px from a door and opening it: 1.12 px of shove
	# without the shift, 3.35 px with it (user: "when im close to the door,
	# and i open it, it pushes me back a bit").
	#
	# y_sort_enabled makes this node sort its own children, so the sprite
	# carries the depth on its own and the body never moves at all.
	_sprite.position.y += delta
	_sprite.offset.y -= delta
	_sort_shift = shift


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


func set_floor_blocked(blocked: bool) -> void:
	## Seal the doorway for COLLISION ONLY, leaving the door exactly as the
	## player left it — same state, same frame, same sound (none).
	##
	## The upper room has NO WALLS OF ITS OWN: `_build_upper` lays floor tiles
	## and the building reuses the ground shell for collision. So an open
	## ground-floor doorway is a real hole at storey height, and walking out of
	## one was a real bug. That used to be handled by slamming the door shut
	## behind the climber, which the user rejected outright: *"when going up
	## the stiars to a second floor, the main door entrance closes
	## automatically, it should stay open"*. Blocking the gap without touching
	## `_open` satisfies both.
	##
	## The occluder deliberately stays with the VISUAL state — the door looks
	## open, so light still comes through it. This is a floor abstraction, not
	## a door that quietly shut itself.
	if _floor_blocked == blocked:
		return
	_floor_blocked = blocked
	if blocked:
		_poly.set_deferred("disabled", false)
	elif _open and not _animating:
		_poly.set_deferred("disabled", true)


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
			# ...unless an upper floor is standing on this shell, in which
			# case the gap stays sealed while the door still reads as open
			_poly.set_deferred("disabled", not _floor_blocked)
			_occ.occluder = null                    # ...and light comes through
		else:
			_poly.set_deferred("disabled", false)
			_occ.occluder = _occ_poly
			_leaf.set_deferred("disabled", true)
			_leaf_out.set_deferred("disabled", true)
			_apply_sort_shift(0.0)   # back on the wall line; the ramp below
			                         # already lands here, this is the guarantee
		return
	_frame += 1 if target > _frame else -1
	# the outward swing lives in the second half of the sheet
	_sprite.frame = (FRAMES if _swing_out else 0) + _frame
	# ...and the sort key rides the same frame, so the leaf starts occluding as
	# it comes round instead of snapping at one end of the swing
	_apply_sort_shift(_leaf_sort_depth() * float(_frame) / float(FRAMES - 1))
