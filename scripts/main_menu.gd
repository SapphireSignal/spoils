extends Node2D
## Main menu. The background IS the game world: the real map with a slow
## drifting camera, dust motes, a raider walking his patrol, and a vignette.
## DEPLOY starts the raid.

const CAM_PATH: Array[Vector2i] = [
	Vector2i(12, 11), Vector2i(20, 20), Vector2i(24, 30),
	Vector2i(32, 36), Vector2i(24, 30), Vector2i(20, 20),
]
const CAM_SPEED := 10.0
const WALKER_PATH_X := 23  # walks road A up and down
const WALKER_SPEED := 55.0

var _world_info: Dictionary = {}
var _camera: Camera2D
var _cam_pos := Vector2.ZERO
var _cam_target_index := 0
var _title: TextureRect
var _title_base_y := 0.0
var _time := 0.0
var _walker: Sprite2D
var _walker_going := 1.0
var _walker_anim := 0.0
var _buttons: PanelContainer
var _settings: SettingsPanel


func _ready() -> void:
	var builder := WorldBuilder.new()
	_world_info = builder.build(self)

	_camera = Camera2D.new()
	var floor_layer: TileMapLayer = _world_info["floor"]
	_cam_pos = floor_layer.map_to_local(CAM_PATH[0])
	_camera.position = _cam_pos.round()
	add_child(_camera)
	_camera.make_current()

	_spawn_walker(floor_layer)
	_build_dust()
	_build_ui()


func _process(delta: float) -> void:
	_time += delta

	# slow cinematic drift between waypoints
	var floor_layer: TileMapLayer = _world_info["floor"]
	var target := floor_layer.map_to_local(CAM_PATH[_cam_target_index])
	var to_target := target - _cam_pos
	if to_target.length() < 4.0:
		_cam_target_index = (_cam_target_index + 1) % CAM_PATH.size()
	else:
		_cam_pos += to_target.normalized() * CAM_SPEED * delta
	_camera.position = _cam_pos.round()

	# title breathes
	_title.position.y = _title_base_y + roundf(sin(_time * 1.3) * 2.0)

	# the raider walks his patrol along the road
	var going_to := floor_layer.map_to_local(
		Vector2i(WALKER_PATH_X, 42 if _walker_going > 0 else 8))
	var dir := (going_to - _walker.position).normalized()
	_walker.position += dir * WALKER_SPEED * delta
	if _walker.position.distance_to(going_to) < 8.0:
		_walker_going *= -1.0
	_walker_anim += delta
	var row := 3 if _walker_going > 0 else 7  # SW out, NE back
	var frame := 1 + (int(_walker_anim * 10.0) % 6)
	_walker.frame = row * 7 + frame


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") and _settings.visible:
		get_viewport().set_input_as_handled()
		_close_settings()


func _spawn_walker(floor_layer: TileMapLayer) -> void:
	_walker = Sprite2D.new()
	_walker.texture = load("res://art/gen/char.png")
	_walker.hframes = 7
	_walker.vframes = 8
	_walker.offset = Vector2(0, -17)
	_walker.position = floor_layer.map_to_local(Vector2i(WALKER_PATH_X, 16))
	(_world_info["ysort"] as Node2D).add_child(_walker)


func _build_dust() -> void:
	var dust := CPUParticles2D.new()
	dust.texture = load("res://art/gen/dust.png")
	dust.amount = 40
	dust.lifetime = 9.0
	dust.preprocess = 9.0
	dust.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	dust.emission_rect_extents = Vector2(460, 300)
	dust.direction = Vector2(1, -0.25)
	dust.spread = 20.0
	dust.gravity = Vector2.ZERO
	dust.initial_velocity_min = 5.0
	dust.initial_velocity_max = 14.0
	dust.color = Color("a8b5b2", 0.35)
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0))
	ramp.add_point(0.15, Color(1, 1, 1, 1))
	ramp.add_point(0.85, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	dust.color_ramp = ramp
	_camera.add_child(dust)


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	layer.add_child(root)

	var vignette := TextureRect.new()
	vignette.texture = load("res://art/gen/vignette.png")
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(vignette)

	_title = TextureRect.new()
	_title.texture = load("res://art/gen/title.png")
	_title.anchor_left = 0.5
	_title.anchor_right = 0.5
	_title.offset_left = -117
	_title.offset_right = 117
	_title.offset_top = 56
	_title.offset_bottom = 120
	_title.stretch_mode = TextureRect.STRETCH_KEEP
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_title_base_y = _title.offset_top
	root.add_child(_title)

	var tagline := Label.new()
	tagline.text = "L O O T .   E X T R A C T .   S U R V I V E ."
	tagline.anchor_left = 0.5
	tagline.anchor_right = 0.5
	tagline.offset_left = -160
	tagline.offset_right = 160
	tagline.offset_top = 128
	tagline.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tagline.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	root.add_child(tagline)

	_buttons = PanelContainer.new()
	_buttons.anchor_left = 0.5
	_buttons.anchor_right = 0.5
	_buttons.anchor_top = 0.62
	_buttons.anchor_bottom = 0.62
	_buttons.offset_left = -85
	_buttons.offset_right = 85
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 7)
	var deploy := _menu_button(box, "DEPLOY", func() -> void:
		get_tree().change_scene_to_file("res://scenes/main.tscn"))
	deploy.add_theme_color_override("font_color", UITheme.ACCENT)
	_menu_button(box, "SETTINGS", _open_settings)
	_menu_button(box, "QUIT", func() -> void: get_tree().quit())
	_buttons.add_child(box)
	root.add_child(_buttons)
	deploy.grab_focus()

	_settings = SettingsPanel.new()
	_settings.visible = false
	_settings.closed.connect(_close_settings)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	center.add_child(_settings)
	root.add_child(center)

	var version := Label.new()
	version.text = "PRE-ALPHA  V0.4.0"
	version.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	version.offset_left = -130
	version.offset_top = -16
	version.offset_right = -6
	version.offset_bottom = -4
	version.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	version.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	root.add_child(version)


func _menu_button(parent: Container, text: String, handler: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(160, 0)
	button.pressed.connect(handler)
	parent.add_child(button)
	return button


func _open_settings() -> void:
	_buttons.visible = false
	_settings.visible = true
	_settings.focus_first()


func _close_settings() -> void:
	_settings.visible = false
	_buttons.visible = true
	_buttons.get_child(0).get_child(0).grab_focus()
