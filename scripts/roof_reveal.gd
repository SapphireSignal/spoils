class_name RoofReveal
extends Node2D
## A building's roof. Fades out completely while the player is inside the
## building footprint ("interior reveal") and back in when they leave.
## Walls are never faded — user call: walls always stay visible.

var cells: Rect2i
## [sprite, full_texture, low_texture_or_null] for every wall piece of this
## building that carries a second storey. A null low texture means the piece is
## second storey ONLY (the door transom) and is hidden rather than swapped.
var low_walls: Array = []

var _inside := false
var _low := false
var _tween: Tween


func set_walls_low(low: bool) -> void:
	## Stood inside on the GROUND floor, the second storey's wall towered over
	## the room with its own row of windows (user: "the second floors walls
	## shouldnt show if im on the first floor, make it so only if im on second
	## floor, the walls will show up").
	##
	## A texture SWAP, not a fade: the low piece is the same canvas at the same
	## origin, drawn from the same rng stream, so it is the full wall with the
	## upper band absent and nothing moves or reshuffles. It stops at the string
	## course, which is already a pale concrete band and reads as a finished
	## top edge.
	##
	## No tween here on purpose. The roof fades because it is one big shape
	## whose sudden change reads as a glitch; a wall losing its top band is a
	## silhouette change that cross-fading would only turn into a ghost.
	if low == _low:
		return
	_low = low
	for entry in low_walls:
		var sprite := entry[0] as Sprite2D
		if sprite == null:
			continue
		var tex := entry[2] as Texture2D if low else entry[1] as Texture2D
		if tex == null:
			sprite.visible = not low
		else:
			sprite.visible = true
			sprite.texture = tex


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
