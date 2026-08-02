class_name Extraction
extends Node
## The way out. Holds every exit on the map, watches how close the raider
## is to one, and runs the countdown + the leaving sequence.
##
## Each zone is a Dictionary: {name, pos, radius, kind, auto}. An `auto`
## zone starts counting the moment you're inside it (the lift's green
## smoke); a non-auto zone waits to be armed, and TODAY THE TOLL GATE IS
## THE ONLY ONE — `arm("toll")` from main.gd is the sole caller.
##
## The night freight is NOT a zone here at all: `night_freight.gd` owns its
## own `extracted` signal and emits it directly when a boarded train pulls
## out, and main.gd wires both signals to the same debrief. (This comment
## used to list the freight as something that arms a zone.)

signal extracted(method: String)

const COUNT_FROM := 5.0
# Clipping the edge of a zone at speed used to reset the whole count, so you
# could pay the warden and then drive straight out through the extract
# without it ever firing (user). A short grace keeps the count running while
# you're briefly outside — you're still leaving.
const LEAVE_GRACE := 2.0

var _zones: Array[Dictionary] = []
var _player: Player
var _label: Label
var _active := -1
var _grace := 0.0
var _count := 0.0
var _count_shown := -1          # label re-shapes only when the digit changes
var _leaving := false
var _heli: Helicopter
var _seq_tween: Tween           # whichever leg of the lift is in flight
var _aborted := false           # death mid-sequence bailed it out


func setup(player: Player) -> void:
	_player = player
	# dying mid-lift used to leave the bird parked in the sky, the raider
	# invisible at floor_lift 104, and _leaving stuck true — no way out for
	# the rest of the raid
	player.died.connect(_abort_on_death)
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
		if bool(zone["auto"]) and _player.driving != null:
			continue   # the rope takes a raider, not a sedan — step out first
		if here.distance_to(zone["pos"] as Vector2) <= float(zone["radius"]):
			inside = i
			break
	if inside == -1:
		if _active == -1:
			return
		# The grace is for DRIVING exits only. The toll zone is something
		# you cross at 190 px/s, where clipping the edge must not reset a
		# five second count. The lift is somewhere you STAND, and walking
		# off it has to cancel at once — with the grace applied to every
		# zone you could stroll away from the pad and still get extracted
		# (user: "it kept letting me extract when i was nowhere near").
		if bool((_zones[_active] as Dictionary)["auto"]):
			_active = -1
			_label.visible = false
			return
		_grace -= delta
		if _grace <= 0.0:
			_active = -1
			_label.visible = false
			return
		inside = _active        # still on your way out; keep counting
	else:
		_grace = LEAVE_GRACE
	if inside != _active:
		_active = inside
		_count = COUNT_FROM
	_count -= delta
	if _count <= 0.0:
		_begin_leaving(_zones[inside])
		return
	var n := int(ceilf(_count))
	if n != _count_shown:
		_count_shown = n
		_label.text = "extracting in %d" % n
	_label.visible = true


func _begin_leaving(zone: Dictionary) -> void:
	_leaving = true
	_label.visible = false
	var kind := str(zone["kind"])
	if kind == "lift":
		_aborted = false
		await _lift_sequence(zone["pos"] as Vector2)
		if _aborted:
			_aborted = false   # death already cleaned up; the raid goes on
			return
	extracted.emit(str(zone["name"]))


func _lift_sequence(at: Vector2) -> void:
	## the bird comes in over the treeline, hangs a rope, and takes you.
	## The raider is frozen through `extracting` — movement runs in _process,
	## so the old set_physics_process(false) never gated anything and you
	## could simply walk away from your own rope.
	_player.extracting = true
	_heli = Helicopter.new()
	_heli.position = at + Vector2(360.0, -300.0)
	_player.get_parent().add_child(_heli)
	_heli.z_index = 80
	_seq_tween = create_tween()
	_seq_tween.tween_property(_heli, "position", at + Vector2(0.0, -110.0), 2.2) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await _seq_wait()
	if _aborted:
		return
	_heli.drop_rope(96.0)
	await _seq_delay(0.9)
	if _aborted:
		return
	# the raider goes up the rope: the sprite rises, the camera rides with
	# it (floor_lift already moves sprite + shadow + camera as one)
	_seq_tween = create_tween()
	_seq_tween.tween_property(_player, "floor_lift", 104.0, 1.6) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await _seq_wait()
	if _aborted:
		return
	_heli.raise_rope()
	_seq_tween = create_tween()
	_seq_tween.tween_property(_heli, "position", at + Vector2(-420.0, -360.0), 1.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	_player.visible = false
	await _seq_wait()


func _seq_wait() -> void:
	# a killed tween never fires `finished`, so await-ing it would park this
	# coroutine forever — poll instead, and an abort falls straight out
	while not _aborted and _seq_tween != null and _seq_tween.is_valid() \
			and _seq_tween.is_running():
		await get_tree().process_frame


func _seq_delay(seconds: float) -> void:
	# same reason as _seq_wait: a SceneTreeTimer can't be cancelled by death
	var left := seconds
	while not _aborted and left > 0.0:
		left -= get_process_delta_time()
		await get_tree().process_frame


func _abort_on_death() -> void:
	# hand the raid back: kill the live leg, clear the bird, reset the state
	# machine. respawn() restores the raider's visibility and floor_lift.
	if not _leaving:
		return
	_aborted = true
	if _seq_tween != null and _seq_tween.is_valid():
		_seq_tween.kill()
	if is_instance_valid(_heli):
		_heli.queue_free()
	_heli = null
	_player.extracting = false
	_leaving = false
	_active = -1
