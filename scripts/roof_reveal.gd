class_name RoofReveal
extends Node2D
## A building's roof. Fades out completely while the player is inside the
## building footprint ("interior reveal") and back in when they leave.
## Walls are never faded — user call: walls always stay visible.

var cells: Rect2i
## [upper_sprite, low_sprite_or_null, is_far] for every wall piece of this
## building that carries a second storey — the wall's two BANDS as separate
## sprites. A null low sprite means the piece is second storey ONLY (the door
## transom). `is_far` means the piece is on the north/west edge, so the room
## lies in front of it on screen.
var low_walls: Array = []

var _inside := false
var _tween: Tween
var _wall_tween: Tween
var _near_on := true         # which bands are currently drawn...
var _far_on := true
var _upper_on := true
var _near_from := 1.0        # ...and where the running fade started from
var _far_from := 1.0
var _upper_from := 1.0


func set_wall_storey(show_low_near: bool, show_low_far: bool,
		show_upper: bool) -> void:
	## Which BANDS of a two-storey wall are drawn:
	##
	##   outside        everything — the building reads as two storeys
	##   ground floor   the ground band alone, both sides
	##   upstairs       the upper band, plus the ground band on the NEAR walls
	##
	## THE FAR GROUND BAND IS THE ONE THAT HAS TO GO WHEN YOU ARE UPSTAIRS, and
	## it is not a cosmetic choice. That band is the storey below the floor you
	## are standing on and behind it, so your own floor should hide it. It does
	## not, because the upper slab sorts a storey NORTH of the walls and so
	## draws behind them: the far wall covers the back rows of the floor, while
	## furniture keeps its true-cell sort and draws in FRONT of the same wall,
	## which leaves it standing on bare brick with no floor under it. That is
	## the "floating furniture" the user photographed twice.
	##
	## The near ground bands stay. They are the faces between you and the
	## street, and hiding them is what made the house look like it was floating.
	##
	## Fades on the same 0.28 s curve as the roof, because a climb changes the
	## roof and the walls together and two curves on one action read as two
	## events.
	if show_low_near == _near_on and show_low_far == _far_on \
			and show_upper == _upper_on:
		return
	_near_on = show_low_near
	_far_on = show_low_far
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
				if lo == null:
					continue
				if bool(entry[2]):
					lo.modulate.a = lerpf(_far_from, 1.0 if show_low_far else 0.0, t)
				else:
					lo.modulate.a = lerpf(_near_from, 1.0 if show_low_near else 0.0, t),
		0.0, 1.0, 0.28) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	_wall_tween.tween_callback(func() -> void:
		_upper_from = 1.0 if show_upper else 0.0
		_near_from = 1.0 if show_low_near else 0.0
		_far_from = 1.0 if show_low_far else 0.0)


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
