class_name RoofReveal
extends Node2D
## A building's roof. Fades out completely while the player is inside the
## building footprint ("interior reveal") and back in when they leave.
## Walls are never faded — user call: walls always stay visible.

var cells: Rect2i

var _inside := false
var _tween: Tween


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
