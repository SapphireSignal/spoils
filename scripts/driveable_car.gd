class_name DriveableCar
extends CharacterBody2D
## An intact car you can actually drive (user request): F opens the door
## and seats you (door swing = a baked texture-swap frame + a real door
## recording), Q wakes the engine, W/S is throttle/reverse, A/D steps the
## heading around the four baked facings, E throws the headlights, F steps
## back out. The sprite parks on the same screen-pixel grid as the player,
## so the camera weld stays shimmer-free at any zoom. Broken-into cars
## never become one of these — they stay the static props they are.

const MAX_SPEED := 260.0
const ACCEL := 220.0
const BRAKE := 340.0
const COAST := 150.0            # engine braking while idling down
const ARRIVE_DIST := 34.0       # ease off when the cursor is this close
const TURN_COOLDOWN := 0.22     # seconds between 90-degree heading steps
const DOOR_TIME := 0.34
const HEADINGS := ["nw", "ne", "se", "sw"]   # clockwise on screen
const DIRS := {
	"nw": Vector2(-0.8944, -0.4472), "ne": Vector2(0.8944, -0.4472),
	"se": Vector2(0.8944, 0.4472), "sw": Vector2(-0.8944, 0.4472),
}
# where the driver steps out, per heading (beside the visible door)
const EXIT_OFFSET := {
	"nw": Vector2(-8.0, 14.0), "ne": Vector2(8.0, 14.0),
	"se": Vector2(-16.0, 10.0), "sw": Vector2(16.0, 10.0),
}

var heading := "nw"
var index := 0                  # family variant index (intact: 0..2)
var driven := false
var engine_on := false
var following := false          # left click toggles cursor-follow
var speed := 0.0

var _sprite: Sprite2D
var _manifest: Dictionary = {}
var _player: Player
var _busy := false              # a door swing is in flight
var _turn_left := 0.0
var _click_held := false
var _lights: Array[PointLight2D] = []


func _init() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING


func setup(start_variant: String, start_heading: String, manifest: Dictionary) -> void:
	_manifest = manifest
	heading = start_heading
	index = int(start_variant.get_slice("_", 2))
	_sprite = Sprite2D.new()
	_sprite.centered = false
	add_child(_sprite)
	_apply_variant(_base_variant_name())
	var poly := CollisionPolygon2D.new()
	var spec: Array = (_manifest["props"][_base_variant_name()] as Dictionary)["collider"]
	poly.polygon = PackedVector2Array([
		Vector2(0, -float(spec[2])), Vector2(float(spec[1]), 0),
		Vector2(0, float(spec[2])), Vector2(-float(spec[1]), 0)])
	add_child(poly)
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
	player.board_car(self)
	Sfx.play_car_door(false)
	_apply_variant(_base_variant_name())
	driven = true
	_busy = false
	set_process(true)


func exit_car() -> void:
	if _busy:
		return
	_busy = true
	set_process(false)
	speed = 0.0
	velocity = Vector2.ZERO
	if engine_on:
		engine_on = false
		Sfx.play_engine_off()
	following = false
	Sfx.set_engine(0.0)
	for light in _lights:
		light.enabled = false
	Sfx.play_car_door(true)
	_apply_variant("%s_door" % _base_variant_name())
	await get_tree().create_timer(DOOR_TIME).timeout
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
	if Input.is_action_just_pressed("interact"):
		exit_car()
		return
	if Input.is_action_just_pressed("flashlight"):
		for light in _lights:
			light.enabled = not light.enabled
		Sfx.play_click()
	if Input.is_action_just_pressed("engine") and not engine_on:
		engine_on = true
		Sfx.play_engine_start()

	# cursor-follow driving (user call — the wasd steering "seems off"):
	# one left CLICK and the car chases the cursor at full throttle; another
	# click and it rolls to an idle stop
	var click := Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)
	if click and not _click_held and engine_on:
		following = not following
	_click_held = click
	if not engine_on:
		following = false

	if following:
		var to_cursor := get_global_mouse_position() - global_position
		if to_cursor.length() < ARRIVE_DIST:
			speed = move_toward(speed, 0.0, BRAKE * delta)   # you're there
		else:
			# steer: step the heading toward whichever baked facing points
			# most at the cursor, one 90-degree notch per cooldown
			_turn_left -= delta
			var want := ""
			var best_dot := -2.0
			for h in HEADINGS:
				var d := (DIRS[h] as Vector2).normalized().dot(to_cursor.normalized())
				if d > best_dot:
					best_dot = d
					want = h
			if want != heading and _turn_left <= 0.0:
				_turn_left = TURN_COOLDOWN
				var hi := HEADINGS.find(heading)
				var wi := HEADINGS.find(want)
				var step := 1 if wrapi(wi - hi, 0, 4) <= 2 else -1
				heading = HEADINGS[wrapi(hi + step, 0, 4)]
				_apply_variant(_base_variant_name())
				_aim_lights()
			speed = move_toward(speed, MAX_SPEED, ACCEL * delta)
	else:
		speed = move_toward(speed, 0.0, COAST * delta)

	velocity = (DIRS[heading] as Vector2) * speed
	move_and_slide()
	if get_slide_collision_count() > 0:
		speed *= 0.35           # you hit something; the car noticed
	Sfx.set_engine((0.3 + 0.7 * absf(speed) / MAX_SPEED) if engine_on else 0.0)

	# park the sprite on the SAME screen-pixel grid the player camera uses
	var s := float(maxi(1, Settings.pixel_scale))
	var c := s
	if _player != null and _player.zoom_combined != 0:
		c = float(_player.zoom_combined)
	_sprite.position = (global_position * c).round() / c - global_position


func _aim_lights() -> void:
	var dir := DIRS[heading] as Vector2
	var side := Vector2(-dir.y, dir.x)
	var angle := dir.angle()
	for i in _lights.size():
		var light := _lights[i]
		light.rotation = angle
		light.position = dir * 16.0 + side * (7.0 if i == 0 else -7.0) \
			+ Vector2(0.0, -8.0)
