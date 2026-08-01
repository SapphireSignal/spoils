class_name RoofReveal
extends Node2D
## A building's roof group. Fades out while the player is inside the building
## footprint ("interior reveal") and back in when they leave.

var cells: Rect2i

var _inside := false
var _tween: Tween


func set_inside(inside: bool) -> void:
	if inside == _inside:
		return
	_inside = inside
	if _tween != null:
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(self, "modulate:a", 0.06 if inside else 1.0, 0.25) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
