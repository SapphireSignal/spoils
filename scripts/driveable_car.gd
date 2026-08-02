class_name DriveableCar
extends CharacterBody2D
## An intact car you can actually drive (user request): F opens the door,
## seats you and WAKES THE ENGINE; WASD drives it across all EIGHT baked
## facings so the nose points where you're going; E throws the headlights;
## F steps back out and shuts the engine off behind you. No engine key —
## a car you're sitting in is a car that's running (user call 2026-08-01).
## The sprite parks on the same screen-pixel grid as the player, so the
## camera weld stays shimmer-free at any zoom. Broken-into cars never
## become one of these — they stay the static props they are.

const MAX_SPEED := 190.0        # brisk, not a rocket (user: "way too fast")
const ACCEL := 220.0
const BRAKE := 340.0
const COAST := 150.0            # engine braking while idling down
const DOOR_TIME := 0.34
# all eight screen headings; the diagonals keep the iso (2,1) slope
const HEADINGS := ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
const DIRS := {
	"n": Vector2(0.0, -1.0), "ne": Vector2(0.8944, -0.4472),
	"e": Vector2(1.0, 0.0), "se": Vector2(0.8944, 0.4472),
	"s": Vector2(0.0, 1.0), "sw": Vector2(-0.8944, 0.4472),
	"w": Vector2(-1.0, 0.0), "nw": Vector2(-0.8944, -0.4472),
}
# where the driver steps out, per heading (beside the visible door)
const EXIT_OFFSET := {
	"n": Vector2(-16.0, 8.0), "ne": Vector2(8.0, 14.0),
	"e": Vector2(-6.0, 16.0), "se": Vector2(-16.0, 10.0),
	"s": Vector2(-16.0, 8.0), "sw": Vector2(16.0, 10.0),
	"w": Vector2(6.0, 16.0), "nw": Vector2(-8.0, 14.0),
}

var heading := "nw"
var index := 0                  # family variant index (intact ones drive)
var kind := "car"               # "car" or "truck", published by the generator
var driven := false
var engine_on := false          # true the whole time you're seated
var speed := 0.0
var auto_drive := Vector2.ZERO  # harness/AI override for the WASD vector
var _drive_dir := Vector2.ZERO  # the direction the car is actually carrying

var _sprite: Sprite2D
var _poly: CollisionPolygon2D
var _manifest: Dictionary = {}
var _player: Player
var _busy := false              # a door swing is in flight
var _lights: Array[PointLight2D] = []
var _crash_cool := 0.0          # one thump per hit, not one per frame
var _dust_tex: Texture2D


func _collider_points(variant: String) -> PackedVector2Array:
	# each heading's manifest entry carries the correctly-flipped poly for
	# its diagonal (turning 90 degrees swaps diagonals — the shape must too)
	var spec: Array = (_manifest["props"][variant] as Dictionary)["collider"]
	var points := PackedVector2Array()
	if spec[0] == "poly":
		var flat: Array = spec[1]
		for i in range(0, flat.size(), 2):
			points.append(Vector2(float(flat[i]), float(flat[i + 1])))
	else:
		points = PackedVector2Array([
			Vector2(0, -float(spec[2])), Vector2(float(spec[1]), 0),
			Vector2(0, float(spec[2])), Vector2(-float(spec[1]), 0)])
	return points


func _init() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING


func setup(start_variant: String, start_heading: String, manifest: Dictionary) -> void:
	_manifest = manifest
	heading = start_heading
	index = int(start_variant.get_slice("_", 2))
	# car or truck, straight from the generator — the map labels its dots
	# off this instead of keeping its own list of which indexes are trucks
	kind = str((manifest["props"][start_variant] as Dictionary).get(
		"vehicle_kind", "car"))
	_sprite = Sprite2D.new()
	_sprite.centered = false
	add_child(_sprite)
	_apply_variant(_base_variant_name())
	_poly = CollisionPolygon2D.new()
	_poly.polygon = _collider_points(_base_variant_name())
	add_child(_poly)
	for i in 2:                 # headlights, dark until E
		var light := PointLight2D.new()
		light.texture = load("res://art/gen/light_cone.png")
		light.offset = Vector2(128.0, 0.0)
		light.color = Color("e7d5b3")
		light.energy = 1.1
		light.enabled = false
		add_child(light)
		_lights.append(light)
	_aim_lights()
	_dust_tex = load("res://art/gen/dust.png")
	add_to_group("cars")
	set_process(false)


func _base_variant_name() -> String:
	return "vehicle_%s_%d" % [heading, index]


func _apply_variant(variant: String) -> void:
	var info: Dictionary = _manifest["props"][variant]
	var origin: Array = info["origin"]
	_sprite.texture = load("res://art/gen/%s.png" % variant)
	_sprite.offset = Vector2(-float(origin[0]), -float(origin[1]))


func can_enter() -> bool:
	return not driven and not _busy


func enter(player: Player) -> void:
	if not can_enter():
		return
	_busy = true
	_player = player
	# entering your own ride shuts the alarm up for good
	var alarms := get_tree().get_first_node_in_group("car_alarms")
	if alarms != null:
		alarms.call("disarm", self)
	Sfx.play_car_door(true)
	_apply_variant("%s_door" % _base_variant_name())
	await get_tree().create_timer(DOOR_TIME).timeout
	if _player == null or _player.dead:
		# shot during the door swing: nobody gets in, nothing wakes up
		_apply_variant(_base_variant_name())
		_player = null
		_busy = false
		return
	player.board_car(self)
	Sfx.play_car_door(false)
	_apply_variant(_base_variant_name())
	driven = true
	_busy = false
	# the engine wakes with you — no separate key any more (user call)
	engine_on = true
	Sfx.play_engine_start()
	set_process(true)


func abandon() -> void:
	## death at the wheel: no door swing, no sounds — the raid already ended.
	## Everything exit_car() clears gets cleared, so the next driver finds a
	## sane car instead of burning headlights and an inverted engine state.
	set_process(false)
	speed = 0.0
	velocity = Vector2.ZERO
	engine_on = false
	Sfx.set_engine(0.0)
	for light in _lights:
		light.enabled = false
	_player = null
	driven = false
	_busy = false


func exit_car() -> void:
	if _busy:
		return
	_busy = true
	set_process(false)
	speed = 0.0
	velocity = Vector2.ZERO
	if engine_on:                # and it dies when you get out
		engine_on = false
		Sfx.play_engine_off()
	Sfx.set_engine(0.0)
	for light in _lights:
		light.enabled = false
	Sfx.play_car_door(true)
	_apply_variant("%s_door" % _base_variant_name())
	await get_tree().create_timer(DOOR_TIME).timeout
	if _player == null or _player.dead:
		# died at the wheel DURING the door swing: nobody gets put on the
		# pavement, just finish the door. TWO distinct cases, which is why
		# both arms are needed and why this is NOT identical to enter():
		#   _player == null — abandon() (main.gd, ~1.55 s after death) has
		#     already emptied the cabin and cleared driven/_busy itself.
		#   _player.dead    — F pressed in the ~1.2 s BEFORE abandon() runs.
		#     The ref is still live but the player is a corpse; without this
		#     arm unboard_car() stood the body up on the pavement mid-fade.
		#     Leave driven/_player alone here — abandon() still has to run.
		# enter() needs the mirror of this for its own reason: during ITS
		# swing you are not boarded yet, so abandon() never fires and only
		# the .dead arm can catch it. (The note here said the two guards
		# were "identical" and that enter() had carried it "all along";
		# enter() got its guard in v0.6.43, and the arms differ.)
		_apply_variant(_base_variant_name())
		_busy = false
		return
	var out := (global_position + (EXIT_OFFSET[heading] as Vector2)).round()
	_player.unboard_car(out)
	_player = null
	Sfx.play_car_door(false)
	_apply_variant(_base_variant_name())
	driven = false
	_busy = false


func _process(delta: float) -> void:
	if not driven or _busy:
		return
	if Ui.blocks_gameplay():
		# a window is up: coast to a stop, read no input
		speed = move_toward(speed, 0.0, COAST * delta)
		velocity = Vector2(_drive_dir.x, _drive_dir.y * 0.6) * speed
		move_and_slide()
		Sfx.set_engine(0.3 if engine_on else 0.0)
		return
	if Input.is_action_just_pressed("interact"):
		# pulled up at the warden's window? talk to him instead of getting
		# out — the whole point of the gate is that you drive to it
		var gate := _nearest_toll_gate()
		if gate != null:
			gate.use()
			return
		exit_car()
		return
	if Input.is_action_just_pressed("flashlight"):
		for light in _lights:
			light.enabled = not light.enabled
		Sfx.play_click()

	# WASD driving: the nose points where you press, INSTANTLY (user call
	# 2026-08-01 — the steering carve is gone). W+A is the up-left
	# diagonal, and so on; keys give exactly eight vectors, so there is
	# nothing to smooth between. Let go and the car rolls down to a stop.
	var want_dir := auto_drive
	if want_dir == Vector2.ZERO:
		want_dir = Input.get_vector("move_left", "move_right",
			"move_up", "move_down")
	if want_dir.length() > 0.1:
		_drive_dir = want_dir.normalized()
		var want := ""
		var best_dot := -2.0
		for h in HEADINGS:
			var d := (DIRS[h] as Vector2).normalized().dot(_drive_dir)
			if d > best_dot:
				best_dot = d
				want = h
		if want != heading:
			heading = want
			_apply_variant(_base_variant_name())
			_poly.set_deferred("polygon", _collider_points(_base_variant_name()))
			_aim_lights()
		speed = move_toward(speed, MAX_SPEED, ACCEL * delta)
	else:
		speed = move_toward(speed, 0.0, COAST * delta)

	# the same iso squash the player walks with, so a car crossing the
	# screen north-south covers ground at the rate the tiles imply
	velocity = Vector2(_drive_dir.x, _drive_dir.y * 0.6) * speed
	var pre_speed := absf(speed)
	move_and_slide()
	_crash_cool = maxf(0.0, _crash_cool - delta)
	if get_slide_collision_count() > 0:
		if pre_speed > 60.0 and _crash_cool <= 0.0:
			_crash_cool = 0.6
			# every real hit gets a soft metal thump (user ask); SMOKE is
			# reserved for full-speed crashes only
			Sfx.play_car_bump(pre_speed / MAX_SPEED)
			# the thump you HEAR should also be a thump you FEEL — scaled
			# by how hard you hit, in whole screen pixels
			if _player != null:
				_player.shake(1.5 + 3.5 * (pre_speed / MAX_SPEED), 0.24)
			if pre_speed >= MAX_SPEED * 0.85:
				_spawn_crash_smoke()
		speed *= 0.35           # you hit something; the car noticed
	Sfx.set_engine((0.3 + 0.7 * absf(speed) / MAX_SPEED) if engine_on else 0.0)

	# park the sprite on the SAME screen-pixel grid the player camera uses
	var s := float(maxi(1, Settings.pixel_scale))
	var c := s
	if _player != null and _player.zoom_combined != 0:
		c = float(_player.zoom_combined)
	_sprite.position = (global_position * c).round() / c - global_position


func _nearest_toll_gate() -> TollGate:
	for node in get_tree().get_nodes_in_group("toll_gates"):
		var gate := node as TollGate
		if gate == null or not gate.can_use():
			continue
		if gate.global_position.distance_to(global_position) \
				< TollGate.INTERACT_RANGE:
			return gate
	return null


func _spawn_crash_smoke() -> void:
	# a small gray gasp off the point of impact — fire-and-forget tweens,
	# so the puffs finish even if the driver steps out mid-drift
	var hit := get_slide_collision(0)
	var at := global_position
	if hit != null:
		at = hit.get_position()
	for i in randi_range(4, 6):
		var puff := Sprite2D.new()
		puff.texture = _dust_tex
		puff.modulate = Color("a8b5b2", 0.55)
		puff.position = at + Vector2(randf_range(-5.0, 5.0),
			randf_range(-4.0, 2.0))
		get_parent().add_child(puff)
		var dur := randf_range(0.8, 1.3)
		var tw := puff.create_tween()
		tw.set_parallel(true)
		tw.tween_property(puff, "position", puff.position + Vector2(
			randf_range(-10.0, 10.0), randf_range(-18.0, -9.0)), dur)
		tw.tween_property(puff, "modulate:a", 0.0, dur)
		tw.chain().tween_callback(puff.queue_free)


func _aim_lights() -> void:
	var dir := DIRS[heading] as Vector2
	var side := Vector2(-dir.y, dir.x)
	var angle := dir.angle()
	for i in _lights.size():
		var light := _lights[i]
		light.rotation = angle
		light.position = dir * 16.0 + side * (7.0 if i == 0 else -7.0) \
			+ Vector2(0.0, -8.0)
