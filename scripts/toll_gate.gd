class_name TollGate
extends StaticBody2D
## The warden's crossing on the district edge: a booth, a boom across the
## road, and a man who will talk until you pay him. Interacting opens his
## window; paying raises the boom, stands the snipers down on this stretch
## and arms the extract beyond the wire.

signal wants_dialog

const INTERACT_RANGE := 74.0     # generous: you pull up in a CAR

var paid := false

var _boom: Sprite2D
var _closed_tex: Texture2D
var _open_tex: Texture2D


func setup(manifest: Dictionary, boom_offset: Vector2,
		axis: String = "x") -> void:
	## `axis` is which iso axis the road runs along, so the boom lies ACROSS it
	## rather than down it — see make_toll_barrier. The raised texture is shared
	## because a boom standing up is vertical either way.
	var booth_info: Dictionary = manifest["props"]["toll_booth"]
	var origin: Array = booth_info["origin"]
	var booth := Sprite2D.new()
	booth.texture = load("res://art/gen/toll_booth.png")
	booth.centered = false
	booth.offset = Vector2(-float(origin[0]), -float(origin[1]))
	add_child(booth)
	var spec: Array = booth_info["collider"]
	var poly := CollisionPolygon2D.new()
	poly.polygon = PackedVector2Array([
		Vector2(0, -float(spec[2])), Vector2(float(spec[1]), 0),
		Vector2(0, float(spec[2])), Vector2(-float(spec[1]), 0)])
	add_child(poly)

	var boom_name := "toll_barrier" if axis == "x" else "toll_barrier_y"
	_closed_tex = load("res://art/gen/%s.png" % boom_name)
	_open_tex = load("res://art/gen/toll_barrier_open.png")
	var boom_info: Dictionary = manifest["props"][boom_name]
	var boom_origin: Array = boom_info["origin"]
	_boom = Sprite2D.new()
	_boom.texture = _closed_tex
	_boom.centered = false
	_boom.offset = Vector2(-float(boom_origin[0]), -float(boom_origin[1]))
	_boom.position = boom_offset
	add_child(_boom)
	add_to_group("toll_gates")


func can_use() -> bool:
	return not paid


func use() -> void:
	if paid:
		return
	wants_dialog.emit()


func open_barrier() -> void:
	paid = true
	_boom.texture = _open_tex
	Sfx.play_door(true)
