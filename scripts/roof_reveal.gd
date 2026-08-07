class_name RoofReveal
extends Node2D
## A building's roof. Fades out completely while the player is inside the
## building footprint ("interior reveal") and back in when they leave.
## Walls are never faded — user call: walls always stay visible.

var cells: Rect2i
## [full_sprite, low_sprite_or_null] for every wall piece of this building that
## carries a second storey. The low sprite sits UNDER the full one and stays
## put; the full one fades, so the upper band dissolves while the ground band
## holds. A null low sprite means the piece is second storey ONLY (the door
## transom) and simply fades away.
var low_walls: Array = []

var _inside := false
var _low := false
var _tween: Tween
var _wall_tween: Tween


func set_walls_low(low: bool) -> void:
	## Stood inside on the GROUND floor, the second storey's wall towered over
	## the room with its own row of windows (user: "the second floors walls
	## shouldnt show if im on the first floor, make it so only if im on second
	## floor, the walls will show up").
	##
	## IT FADES, on the same 0.28 s quad EASE_IN_OUT as the roof above it —
	## a climb changes the roof and the upper wall band together, and two
	## different curves on one action would read as two separate events (user:
	## "it should fade out and back in like the roof ... i meant the second
	## floor wall for the fade, not the actual second floor").
	##
	## The low piece is a SEPARATE SPRITE underneath that never moves. Only the
	## full piece's alpha runs, so the upper band dissolves while the ground
	## band stays solid throughout — which a texture swap could not do at all,
	## and cross-fading a whole wall against nothing would have ghosted.
	if low == _low:
		return
	_low = low
	if _wall_tween != null and _wall_tween.is_valid():
		_wall_tween.kill()
	_wall_tween = create_tween()
	_wall_tween.tween_method(
		func(a: float) -> void:
			for entry in low_walls:
				var sprite := entry[0] as Sprite2D
				if sprite != null:
					sprite.modulate.a = a,
		1.0 if low else 0.0, 0.0 if low else 1.0, 0.28) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)


func set_inside(inside: bool) -> void:
	if inside == _inside:
		return
	_inside = inside
	if _tween != null:
		_tween.kill()
	# EASE_IN_OUT, NOT EASE_OUT, AND IT WAS MEASURED. A quad EASE_OUT is
	# fastest at the START: 19% of the fade is done by t=0.1 and 51% by t=0.3.
	# On a whole roof that is a visible STEP the instant it begins - a frame
	# capture walking past a house measured the roof dropping 28 brightness
	# levels between two consecutive frames, ~56% of the whole fade, then
	# crawling the rest of the way. That is what a "glitch on a house for a
	# millisecond" looks like, and the user reported exactly that.
	#
	# EASE_IN_OUT moves 2% by t=0.1 and 18% by t=0.3, so the reveal starts
	# from nothing and lands softly. Same duration; it only stops the fade
	# announcing itself.
	_tween = create_tween()
	_tween.tween_property(self, "modulate:a", 0.0 if inside else 1.0, 0.28) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
