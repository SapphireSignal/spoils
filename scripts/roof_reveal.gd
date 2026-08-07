class_name RoofReveal
extends Node2D
## A building's roof. Fades out completely while the player is inside the
## building footprint ("interior reveal") and back in when they leave.
## Walls are never faded — user call: walls always stay visible.

var cells: Rect2i
## [upper_sprite, low_sprite_or_null] for every wall piece of this building
## that carries a second storey — the wall's two BANDS as separate sprites.
## A null low sprite means the piece is second storey ONLY (the door transom).
var low_walls: Array = []

var _inside := false
var _tween: Tween
var _wall_tween: Tween
var _low_on := true          # which bands are currently drawn...
var _upper_on := true
var _low_from := 1.0         # ...and where the running fade started from
var _upper_from := 1.0


func set_wall_storey(show_low: bool, show_upper: bool) -> void:
	## Which BANDS of a two-storey wall are drawn. Outside both, on the ground
	## floor the ground band alone, upstairs the upper band alone — so standing
	## on the second floor you see your own storey's wall and windows instead
	## of the whole facade (user: "if you would be on the second floor, you
	## wouldnt see all those windows").
	##
	## Fades on the same 0.28 s curve as the roof, because a climb changes the
	## roof and the walls together and two curves on one action read as two
	## events.
	if show_low == _low_on and show_upper == _upper_on:
		return
	_low_on = show_low
	_upper_on = show_upper
	if _wall_tween != null and _wall_tween.is_valid():
		_wall_tween.kill()
	_wall_tween = create_tween()
	_wall_tween.tween_method(
		func(t: float) -> void:
			for entry in low_walls:
				var up := entry[0] as Sprite2D
				var lo := entry[1] as Sprite2D
				if up != null:
					up.modulate.a = lerpf(_upper_from, 1.0 if show_upper else 0.0, t)
				if lo != null:
					lo.modulate.a = lerpf(_low_from, 1.0 if show_low else 0.0, t),
		0.0, 1.0, 0.28) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	_wall_tween.tween_callback(func() -> void:
		_upper_from = 1.0 if show_upper else 0.0
		_low_from = 1.0 if show_low else 0.0)


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
