class_name Player
extends CharacterBody2D
## Raider avatar: 8-direction WASD movement with iso perspective squash.
## Built entirely in code (no .tscn) — the whole game is code-authored.
##
## Camera: manual follow, clamped to an inset DIAMOND matching the iso map
## (a rectangle can never hug a diamond — that is where the old edge-void
## came from), then snapped to SCREEN pixels (multiples of 1/scale world px).
## At 2x window scale that makes 120 px/s walking exactly one screen pixel
## per frame at 240 Hz — perfectly even scroll, zero blur, no more
## "looks like lower fps" while moving.

signal hurt
signal died

const SPEED := 120.0
const CROUCH_SPEED_MULT := 0.55
const PRONE_SPEED_MULT := 0.32  # a crawl — slower than the crouch
const PRONE_CRAWL_FPS := 6.0
const Y_SQUASH := 0.6  # screen-vertical speed factor; sells iso perspective
const WALK_FPS := 12.0
const CROUCH_WALK_FPS := 9.0
const WALK_FRAMES := 6
const SHEET_COLS := 7  # idle + 6 walk frames
const CAM_OFFSET := Vector2(0, -16)
const MAX_HP := 3
const HURT_FLASH_TIME := 0.24

var camera: Camera2D
var crouching := false
var prone := false
var flashlight_on := false
var hp := MAX_HP
var dead := false
var hits: Array[Dictionary] = []   # {bone, who, at} — read by the debrief
var floor_lift := 0.0           # sprite+camera rise while on a second story
var upstairs := false           # gates ground-floor doors while up there
var driving: DriveableCar = null
var extracting := false         # on the rope: input frozen, camera still live
var hidden_in_bush := false     # Foliage sets it; the sprite fades so the
                                # player can READ their own concealment
# THE INTERACTION RULE (user call 2026-08-01): you can only interact with
# the thing the on-screen prompt is offering. main.gd's prompt logic picks
# this target every frame and it is the ONLY thing F can act on — no more
# opening doors from further away than the prompt appears. Every future
# interactable inherits the rule for free by going through the prompt.
var prompt_target: Node2D = null
# riding something that isn't a car (the freight): welded to it, hidden,
# and out of the input loop until it puts you down or takes you out
var riding: Node2D = null
var ride_offset := Vector2.ZERO


func facing_angle() -> float:
	## Screen-space direction the raider is pointing, in radians. The map
	## draws a cone off this so you can tell which way you're facing — a
	## dot alone told you nothing (user report). Sheet rows run
	## E,SE,S,SW,W,NW,N,NE, which is exactly 45 degrees per row from east.
	if driving != null:
		return (DriveableCar.DIRS[driving.heading] as Vector2).angle()
	return float(_dir_index) * (PI / 4.0)


func board_ride(what: Node2D, offset: Vector2) -> void:
	riding = what
	ride_offset = offset
	visible = false
	collision_layer = 0
	set_flashlight(false)

var _sprite: Sprite2D
var _shadow: Sprite2D
var _tex_stand: Texture2D
var _tex_crouch: Texture2D
var _tex_prone: Texture2D
var _dir_index := 2  # sheet rows are E,SE,S,SW,W,NW,N,NE — start facing S
var _anim_time := 0.0
var _was_moving := false
var _light: PointLight2D
var _hurt_rect: ColorRect
var _hurt_left := 0.0
var _floor_layer: TileMapLayer
var _surface_kinds: Dictionary = {}  # atlas coords -> footstep kind
var _prev_anim_step := -1
# camera zoom ladder: combined world-px -> screen-px factors. Only WHOLE
# factors stay pixel-crisp; native window scale is the WIDEST view (a wider
# one was "too OP" — user call), 6x is the closest. The camera GLIDES
# between stops so scrolling feels continuous; it always settles on a
# whole factor.
var zoom_combined := 0
var _zoom_view := 0.0


func _init() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING

	_shadow = Sprite2D.new()
	_shadow.texture = load("res://art/gen/shadow.png")
	_shadow.centered = false
	_shadow.offset = Vector2(-12, -6)
	add_child(_shadow)

	_tex_stand = load("res://art/gen/char.png")
	_tex_crouch = load("res://art/gen/char_crouch.png")
	_tex_prone = load("res://art/gen/char_prone.png")
	_sprite = Sprite2D.new()
	_sprite.texture = _tex_stand
	_sprite.hframes = SHEET_COLS
	_sprite.vframes = 8
	_sprite.frame = _dir_index * SHEET_COLS
	_sprite.offset = Vector2(0, -17)  # feet (frame y=37 of 40) sit on origin
	add_child(_sprite)

	var shape := CircleShape2D.new()
	shape.radius = 5.0
	var collider := CollisionShape2D.new()
	collider.shape = shape
	collider.position = Vector2(0, -3)
	add_child(collider)

	# flashlight: a cone of real light, snapped to the 8 facings (E toggles).
	# The cone texture is smooth alpha (light), so rotating it cannot break
	# the pixel grid — sprites themselves never rotate.
	_light = PointLight2D.new()
	_light.texture = load("res://art/gen/light_cone.png")
	_light.offset = Vector2(128.0, 0.0)  # apex sits on the light pos
	_light.color = Color("e7d5b3")
	_light.energy = 1.35  # nights are DARK now; the beam has to earn its keep
	_light.position = Vector2(0, -14)
	_light.enabled = false
	add_child(_light)

	camera = Camera2D.new()
	camera.top_level = true  # followed manually; must never inherit subpixels
	add_child(camera)


func _ready() -> void:
	var hurt_layer := CanvasLayer.new()
	hurt_layer.layer = 80
	_hurt_rect = ColorRect.new()
	_hurt_rect.color = Color("a53030", 0.0)
	_hurt_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_hurt_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hurt_layer.add_child(_hurt_rect)
	add_child(hurt_layer)
	var s := float(maxi(1, Settings.pixel_scale))
	camera.global_position = _camera_target(global_position, s)
	camera.make_current()


func take_hit(bone: String = "", who: String = "") -> void:
	if dead:
		return
	# WHERE it landed and WHO sent it — the debrief draws a doll from
	# this, so every hit has to say more than "you lost a point"
	if bone != "":
		hits.append({"bone": bone, "who": who, "at": Raid.elapsed()})
	hp -= 1
	_hurt_left = HURT_FLASH_TIME
	_hurt_rect.color.a = 0.30
	hurt.emit()
	if hp <= 0:
		dead = true
		died.emit()


func respawn(at: Vector2) -> void:
	position = at
	hp = MAX_HP
	dead = false
	hits.clear()
	velocity = Vector2.ZERO
	# dying aboard the freight left `riding` set with no way to clear it:
	# respawn teleported you straight back onto the departed train every
	# frame, invisible and collisionless, with input never read — an
	# unrecoverable softlock
	if riding != null:
		riding = null
		ride_offset = Vector2.ZERO
	extracting = false
	visible = true
	collision_layer = 1
	floor_lift = 0.0


func set_flashlight(on: bool) -> void:
	flashlight_on = on
	_light.enabled = on


func board_car(car: DriveableCar) -> void:
	driving = car
	visible = false
	collision_layer = 0          # the car must not collide with its driver
	set_flashlight(false)


func unboard_car(at: Vector2) -> void:
	position = at
	velocity = Vector2.ZERO
	driving = null
	visible = true
	collision_layer = 1


func setup_surfaces(floor_layer: TileMapLayer, kinds: Dictionary) -> void:
	_floor_layer = floor_layer
	_surface_kinds = kinds


func _footstep() -> void:
	if _floor_layer == null:
		return
	var atlas := _floor_layer.get_cell_atlas_coords(_floor_layer.local_to_map(position))
	var kind: String = _surface_kinds.get(atlas, "concrete")
	# crawling drags softly whatever the ground; crouching just treads lighter
	Sfx.play_step(kind, crouching or prone)


func _process(delta: float) -> void:
	# Movement runs at RENDER rate, not the 60 Hz physics tick: on high-refresh
	# monitors a 60 Hz world reads as stutter. (A future multiplayer server
	# would re-run this on a fixed tick; the seam stays in Authority.)
	if _hurt_left > 0.0:
		_hurt_left -= delta
		_hurt_rect.color.a = maxf(0.0, 0.30 * (_hurt_left / HURT_FLASH_TIME))

	if riding != null:
		# aboard the freight: the camera rides with it, nothing else runs
		global_position = riding.global_position + ride_offset
		_update_camera(delta)
		return

	if driving != null:
		# riding: the body is welded to the car (so the camera weld, zoom
		# and snap all keep working off the same position they always use)
		global_position = driving.global_position
		if not dead and not Ui.blocks_gameplay():
			if Input.is_action_just_pressed("zoom_in"):
				_step_zoom(1)
			elif Input.is_action_just_pressed("zoom_out"):
				_step_zoom(-1)
		_update_camera(delta)
		return

	var input_vec := Vector2.ZERO
	if not dead and not extracting and not Ui.blocks_gameplay():
		# stances: prone (Z, toggle) beats crouch; taking a crouch input
		# stands you back up out of prone
		if Input.is_action_just_pressed("prone"):
			prone = not prone
			if prone:
				crouching = false
		if Settings.crouch_toggle:
			if Input.is_action_just_pressed("crouch"):
				crouching = not crouching
				if crouching:
					prone = false
		else:
			if Input.is_action_pressed("crouch"):
				crouching = true
				prone = false
			else:
				crouching = false
		if Input.is_action_just_pressed("flashlight"):
			set_flashlight(not flashlight_on)
			Sfx.play_click()
		if Input.is_action_just_pressed("interact"):
			_interact()
		input_vec = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var speed := SPEED
	if prone:
		speed *= PRONE_SPEED_MULT
	elif crouching:
		speed *= CROUCH_SPEED_MULT
	velocity = Vector2(input_vec.x, input_vec.y * Y_SQUASH) * speed
	move_and_slide()

	var moving := input_vec.length_squared() > 0.01
	if _was_moving and not moving:
		# settle on the world pixel grid, so an idle raider never rests
		# half a screen pixel off the scenery around him
		position = position.round()
	_was_moving = moving

	# wheel zoom: whole-factor steps only (fractional zoom shimmers).
	# A window on screen owns the wheel — it used to zoom the world AND
	# the map at once (user report)
	if not dead and not extracting and not Ui.blocks_gameplay():
		if Input.is_action_just_pressed("zoom_in"):
			_step_zoom(1)
		elif Input.is_action_just_pressed("zoom_out"):
			_step_zoom(-1)

	# hidden in a bush: raider fades like the bush does, so concealment
	# is readable at a glance (user request). Same ramp speed as foliage.
	var hide_a := 0.5 if (hidden_in_bush and not dead) else 1.0
	_sprite.modulate.a = move_toward(_sprite.modulate.a, hide_a, delta * 4.0)
	_shadow.modulate.a = _sprite.modulate.a

	_update_camera(delta)
	_animate(input_vec, delta)


func _update_camera(delta: float) -> void:
	# ONE grid for everything on screen: the TRUE position stays continuous
	# (never quantize it — that would inflate speed), but the RENDERED sprite
	# parks on the screen-pixel grid, and the camera is defined off that same
	# snapped point. Character-to-camera offset is therefore constant: the
	# raider is pixel-welded to the screen, and the world scrolls on the
	# identical grid. Two disagreeing grids read as shimmer/blur while
	# walking (v0.6.4 lesson). The grid is 1/combined-zoom-factor wide.
	# floor_lift raises sprite AND camera together (whole px) — the second
	# story reads higher while the true position stays on the ground grid.
	var s := float(maxi(1, Settings.pixel_scale))
	var c := s if zoom_combined == 0 else float(zoom_combined)
	# glide toward the target stop; rest states are always whole factors
	if _zoom_view <= 0.0:
		_zoom_view = c
	_zoom_view = move_toward(_zoom_view, c, delta * maxf(4.0, absf(c - _zoom_view) * 10.0))
	camera.zoom = Vector2(_zoom_view / s, _zoom_view / s)
	var snapped_pos := (global_position * c).round() / c
	var visual_err := snapped_pos - global_position
	var lift := Vector2(0.0, -floor_lift)
	_sprite.position = visual_err + lift
	_shadow.position = visual_err + lift
	# the flashlight rides the same lift — it lagged behind on the second
	# floor and sat "inside" the character (user report)
	_light.position = Vector2(0.0, -14.0) + lift
	camera.global_position = _camera_target(snapped_pos + lift, c)


func _step_zoom(direction: int) -> void:
	var s := maxi(1, Settings.pixel_scale)
	var current := s if zoom_combined == 0 else zoom_combined
	var next := clampi(current + direction, s, 6)  # native view is the widest
	zoom_combined = 0 if next == s else next


func _camera_target(from: Vector2, s: float) -> Vector2:
	# the camera NEVER clamps — it is welded to the character (user call).
	# The world past the barricade ring is real and deep enough that the
	# sniper ends any trip long before the void could scroll into view.
	return ((from + CAM_OFFSET) * s).round() / s


func _interact() -> void:
	# ONLY what the prompt is offering (see prompt_target): the reach used
	# to be wider than the prompt, so doors and cars answered from
	# further away than the game ever said they would (user report)
	var best: Node2D = prompt_target
	if best == null or not is_instance_valid(best):
		return
	if best is Door:
		# pass where we're standing: the leaf swings away from us
		(best as Door).toggle(global_position)
	elif best is Stairs:
		(best as Stairs).use()
	elif best is DriveableCar:
		(best as DriveableCar).enter(self)
	elif best is TollGate:
		(best as TollGate).use()
	elif best is NightFreight:
		(best as NightFreight).board()


func _animate(input_vec: Vector2, delta: float) -> void:
	if prone:
		_sprite.texture = _tex_prone
	else:
		_sprite.texture = _tex_crouch if crouching else _tex_stand
	if input_vec.length_squared() > 0.01:
		_dir_index = wrapi(roundi(rad_to_deg(input_vec.angle()) / 45.0), 0, 8)
		_light.rotation = _dir_index * (PI / 4.0)
		_anim_time += delta
		var fps := WALK_FPS
		if prone:
			fps = PRONE_CRAWL_FPS
		elif crouching:
			fps = CROUCH_WALK_FPS
		var step := int(_anim_time * fps) % WALK_FRAMES
		_sprite.frame = _dir_index * SHEET_COLS + 1 + step
		# footfalls land on the plant frames (one per crawl pull when prone)
		if step != _prev_anim_step and (step == 1 or (step == 4 and not prone)):
			_footstep()
		_prev_anim_step = step
	else:
		_anim_time = 0.0
		_prev_anim_step = -1
		_sprite.frame = _dir_index * SHEET_COLS
