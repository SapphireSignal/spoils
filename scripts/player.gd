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
var flashlight_on := false
var hp := MAX_HP
var dead := false

var _sprite: Sprite2D
var _tex_stand: Texture2D
var _tex_crouch: Texture2D
var _dir_index := 2  # sheet rows are E,SE,S,SW,W,NW,N,NE — start facing S
var _anim_time := 0.0
var _was_moving := false
var _light: PointLight2D
var _hurt_rect: ColorRect
var _hurt_left := 0.0
var _map_center := Vector2.ZERO
var _map_half_h := 0.0
var _window: Window


func _init() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING

	var shadow := Sprite2D.new()
	shadow.texture = load("res://art/gen/shadow.png")
	shadow.centered = false
	shadow.offset = Vector2(-12, -6)
	add_child(shadow)

	_tex_stand = load("res://art/gen/char.png")
	_tex_crouch = load("res://art/gen/char_crouch.png")
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
	_light.energy = 1.05
	_light.position = Vector2(0, -14)
	_light.enabled = false
	add_child(_light)

	camera = Camera2D.new()
	camera.top_level = true  # followed manually; must never inherit subpixels
	add_child(camera)


func _ready() -> void:
	_window = get_window()
	var hurt_layer := CanvasLayer.new()
	hurt_layer.layer = 80
	_hurt_rect = ColorRect.new()
	_hurt_rect.color = Color("a53030", 0.0)
	_hurt_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_hurt_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hurt_layer.add_child(_hurt_rect)
	add_child(hurt_layer)
	camera.global_position = _camera_target()
	camera.make_current()


func set_map_diamond(center: Vector2, half_h: float) -> void:
	_map_center = center
	_map_half_h = half_h


func take_hit() -> void:
	if dead:
		return
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
	velocity = Vector2.ZERO


func set_flashlight(on: bool) -> void:
	flashlight_on = on
	_light.enabled = on


func _process(delta: float) -> void:
	# Movement runs at RENDER rate, not the 60 Hz physics tick: on high-refresh
	# monitors a 60 Hz world reads as stutter. (A future multiplayer server
	# would re-run this on a fixed tick; the seam stays in Authority.)
	if _hurt_left > 0.0:
		_hurt_left -= delta
		_hurt_rect.color.a = maxf(0.0, 0.30 * (_hurt_left / HURT_FLASH_TIME))

	var input_vec := Vector2.ZERO
	if not dead:
		if Settings.crouch_toggle:
			if Input.is_action_just_pressed("crouch"):
				crouching = not crouching
		else:
			crouching = Input.is_action_pressed("crouch")
		if Input.is_action_just_pressed("flashlight"):
			set_flashlight(not flashlight_on)
			Sfx.play_click()
		if Input.is_action_just_pressed("interact"):
			_interact()
		input_vec = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var speed := SPEED * (CROUCH_SPEED_MULT if crouching else 1.0)
	velocity = Vector2(input_vec.x, input_vec.y * Y_SQUASH) * speed
	move_and_slide()

	var moving := input_vec.length_squared() > 0.01
	if _was_moving and not moving:
		# settle on the world pixel grid, so an idle raider never rests
		# half a screen pixel off the scenery around him
		position = position.round()
	_was_moving = moving

	camera.global_position = _camera_target()
	_animate(input_vec, delta)


func _camera_target() -> Vector2:
	var target := global_position + CAM_OFFSET
	if _map_half_h > 0.0:
		var view_half := Vector2(_window.content_scale_size) * 0.5
		var limit := _map_half_h - (view_half.x * 0.5 + view_half.y)
		target = _clamp_to_diamond(target, limit)
	# snap to SCREEN pixels: whole-pixel on screen, sub-pixel in the world
	var s := float(maxi(1, Settings.pixel_scale))
	return (target * s).round() / s


func _clamp_to_diamond(point: Vector2, limit: float) -> Vector2:
	var u := point - _map_center
	# project onto the diamond |x|/2 + |y| <= limit (two passes settle corners)
	for pass_i in 2:
		for sx: float in [1.0, -1.0]:
			for sy: float in [1.0, -1.0]:
				var over := u.x * (0.5 * sx) + u.y * sy - limit
				if over > 0.0:
					var n := Vector2(0.5 * sx, sy)
					u -= n * (over / n.length_squared())
	return _map_center + u


func _interact() -> void:
	var best: Door = null
	var best_d := Door.INTERACT_RANGE * Door.INTERACT_RANGE
	for node in get_tree().get_nodes_in_group("doors"):
		var door := node as Door
		var d := door.global_position.distance_squared_to(global_position)
		if d < best_d:
			best_d = d
			best = door
	if best != null:
		best.toggle()


func _animate(input_vec: Vector2, delta: float) -> void:
	_sprite.texture = _tex_crouch if crouching else _tex_stand
	if input_vec.length_squared() > 0.01:
		_dir_index = wrapi(roundi(rad_to_deg(input_vec.angle()) / 45.0), 0, 8)
		_light.rotation = _dir_index * (PI / 4.0)
		_anim_time += delta
		var fps := CROUCH_WALK_FPS if crouching else WALK_FPS
		var step := int(_anim_time * fps) % WALK_FRAMES
		_sprite.frame = _dir_index * SHEET_COLS + 1 + step
	else:
		_anim_time = 0.0
		_sprite.frame = _dir_index * SHEET_COLS
