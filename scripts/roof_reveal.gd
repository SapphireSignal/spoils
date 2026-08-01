class_name RoofReveal
extends Node2D
## A building's roof group. While the player is inside the footprint, the roof
## fades out completely and the camera-facing (south/east) walls drop to low
## alpha so the interior is fully readable ("interior reveal").

var cells: Rect2i
var near_walls: Array[Node2D] = []

var _inside := false
var _tween: Tween


func set_inside(inside: bool) -> void:
	if inside == _inside:
		return
	_inside = inside
	if _tween != null:
		_tween.kill()
	_tween = create_tween().set_parallel(true)
	_tween.tween_property(self, "modulate:a", 0.0 if inside else 1.0, 0.25) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	for wall in near_walls:
		_tween.tween_property(wall, "modulate:a", 0.3 if inside else 1.0, 0.25) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
