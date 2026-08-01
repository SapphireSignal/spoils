class_name Extraction
extends Node
## The way out. Holds every exit on the map, watches how close the raider
## is to one, and runs the countdown + the leaving sequence.
##
## Each zone is a Dictionary: {name, pos, radius, kind, auto}. An `auto`
## zone starts counting the moment you're inside it (the lift's green
## smoke); the others are armed by something else — paying the warden at
## the toll gate, climbing aboard the freight.

signal extracted(method: String)

const COUNT_FROM := 5.0

var _zones: Array[Dictionary] = []
var _player: Player
var _label: Label
var _active := -1
var _count := 0.0
var _leaving := false
var _heli: Helicopter


func setup(player: Player) -> void:
	_player = player
	var layer := CanvasLayer.new()
	layer.layer = 74
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label = Label.new()
	_label.theme = UITheme.get_theme()
	_label.add_theme_color_override("font_color", Color("75a743"))
	_label.anchor_left = 0.5
	_label.anchor_right = 0.5
	_label.anchor_top = 0.30
	_label.anchor_bottom = 0.30
	_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_label.grow_vertical = Control.GROW_DIRECTION_BOTH
	_label.visible = false
	root.add_child(_label)
	layer.add_child(root)
	add_child(layer)


func register(zone_name: String, pos: Vector2, radius: float,
		kind: String, auto: bool) -> void:
	_zones.append({"name": zone_name, "pos": pos, "radius": radius,
		"kind": kind, "auto": auto, "armed": auto})


func arm(kind: String) -> void:
	## the toll gate opens the wire; the freight opens itself
	for zone in _zones:
		if zone["kind"] == kind:
			zone["armed"] = true


func zone_position(kind: String) -> Vector2:
	for zone in _zones:
		if zone["kind"] == kind:
			return zone["pos"]
	return Vector2.ZERO


func _process(delta: float) -> void:
	if _player != null and _player.dead and _label.visible:
		_label.visible = false          # no green counter over the death fade
		_active = -1
	# a window is open: don't extract underneath it. The map doesn't pause
	# the tree, so standing in the LZ and pressing M used to extract you
	# with the map still up.
	if _leaving or _player == null or _player.dead or _zones.is_empty() \
			or Ui.blocks_gameplay():
		return
	var here := _player.global_position
	var inside := -1
	for i in _zones.size():
		var zone: Dictionary = _zones[i]
		if not bool(zone["armed"]):
			continue
		if here.distance_to(zone["pos"] as Vector2) <= float(zone["radius"]):
			inside = i
			break
	if inside == -1:
		if _active != -1:
			_active = -1
			_label.visible = false
		return
	if inside != _active:
		_active = inside
		_count = COUNT_FROM
	_count -= delta
	if _count <= 0.0:
		_begin_leaving(_zones[inside])
		return
	_label.text = "extracting in %d" % int(ceilf(_count))
	_label.visible = true


func _begin_leaving(zone: Dictionary) -> void:
	_leaving = true
	_label.visible = false
	var kind := str(zone["kind"])
	if kind == "lift":
		await _lift_sequence(zone["pos"] as Vector2)
	extracted.emit(str(zone["name"]))


func _lift_sequence(at: Vector2) -> void:
	## the bird comes in over the treeline, hangs a rope, and takes you
	_player.set_physics_process(false)
	_heli = Helicopter.new()
	_heli.position = at + Vector2(360.0, -300.0)
	_player.get_parent().add_child(_heli)
	_heli.z_index = 80
	var fly_in := create_tween()
	fly_in.tween_property(_heli, "position", at + Vector2(0.0, -110.0), 2.2) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await fly_in.finished
	_heli.drop_rope(96.0)
	await get_tree().create_timer(0.9).timeout
	# the raider goes up the rope: the sprite rises, the camera rides with
	# it (floor_lift already moves sprite + shadow + camera as one)
	var lift := create_tween()
	lift.tween_property(_player, "floor_lift", 104.0, 1.6) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await lift.finished
	_heli.raise_rope()
	var away := create_tween()
	away.tween_property(_heli, "position", at + Vector2(-420.0, -360.0), 1.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	_player.visible = false
	await away.finished
