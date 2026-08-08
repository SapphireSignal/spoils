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
## [wall_node, delta] for every wall piece whose face gets a SHARED sort key
## while the player is inside — see set_face_sort.
var face_walls: Array = []
var _face_on := false
## how far past the player a NEAR face parks its shared sort key
const FACE_AIM_MARGIN := 1.0

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


func set_face_sort(on: bool) -> void:
	## ONE SORT KEY PER WALL FACE, WHILE THE PLAYER IS INSIDE (B11).
	##
	## A face is one sprite per cell and each has its own y-sort key, so walking
	## along the inside of a wall crosses them one at a time — at every cell
	## boundary you are in front of the cell just passed and behind the next,
	## and that next one's brick draws across you. The user saw it as being cut
	## in half at regular intervals, one band per cell.
	##
	## A face has no reason to sort per-cell against the room it encloses: it is
	## one flat surface, wholly behind the room or wholly in front of it. So
	## every piece is pushed onto its own face's extreme — computed once at
	## build time — and the whole face becomes a single plane with no seams to
	## cross.
	##
	## ONLY WHILE INSIDE. From the street a face genuinely does interleave with
	## things standing along it, so outside it goes straight back to per-cell.
	##
	## THE SPRITE MOVES, NEVER THE NODE. These are StaticBody2D; moving one
	## would move the wall's collision and depenetrate anything resting against
	## it. `y_sort_enabled` on the piece lets its sprites carry the depth
	## instead — the same split the second-floor slab and the door leaf use.
	if on == _face_on:
		return
	_face_on = on
	# the NEAR faces are aimed at the player and must keep being aimed, so this
	# node processes for as long as the player is inside
	# AFTER THE PLAYER, every frame — the same trap the door hit. Roofs are
	# built long before the raider spawns, so at equal priority they aim at
	# LAST frame's position and the face bands by one frame on the frame you
	# cross it. Higher priority runs later.
	process_priority = 10
	set_process(on)
	for entry in face_walls:
		if on and bool(entry[2]) == false:
			continue          # near face: _process aims it, starting this frame
		_shift_face_piece(entry[0] as Node2D, float(entry[1]) if on else 0.0)
	if on:
		_aim_near_faces()


func _shift_face_piece(node: Node2D, delta: float) -> void:
	for child in node.get_children():
		var spr := child as Sprite2D
		if spr == null:
			continue
		spr.position.y = delta
		spr.offset.y = _sprite_base_offset(spr) - delta


func _aim_near_faces() -> void:
	## THE NEAR FACES AIM AT THE PLAYER, exactly as an open door leaf does.
	##
	## A near face still needs ONE key across all its pieces or the player
	## crosses their seams and gets cut into bands. But it must NOT be the
	## face's own southern extreme: that is up to a building width toward the
	## camera, far enough to out-sort an open door standing in front of the wall.
	##
	## Aiming solves both at once. Put the whole face just SOUTH of the player:
	##   - one key for every piece, so there are no seams left to cross;
	##   - the face covers the player uniformly, which is what a near wall
	##     should do to someone standing behind it;
	##   - and it lands only just past the player, who is INSIDE — so it stays
	##     well behind an open leaf, whose key is `door_y + 7.4..17.4` while an
	##     inside player has `y < door_y`. That is the exact margin v0.6.97 spent
	##     and this does not.
	## Anything outdoors south of the wall still out-sorts it, correctly.
	var player := get_tree().get_first_node_in_group("player_shake") as Node2D
	if player == null:
		return
	var target := player.global_position.y + FACE_AIM_MARGIN
	for entry in face_walls:
		if bool(entry[2]):
			continue          # far face: fixed delta, already applied
		var node := entry[0] as Node2D
		_shift_face_piece(node, target - node.global_position.y)


func _process(_delta: float) -> void:
	if _face_on:
		_aim_near_faces()


func _sprite_base_offset(spr: Sprite2D) -> float:
	## the offset the piece was BUILT with, remembered per sprite so the shift
	## can be added and taken away without accumulating
	if not spr.has_meta("base_off_y"):
		spr.set_meta("base_off_y", spr.offset.y)
	return float(spr.get_meta("base_off_y"))


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
