extends Node2D
## Main menu. Generated backdrop scenes rotate with a slow crossfade,
## each with its own living detail:
##   hoard      - gold sparkles rising past the buttons
##   scrapyard  - flickering neon sign + drifting smog
##   overlook   - clouds drifting over a dead city, dust on the wind
## DEPLOY starts the raid.

const SCENE_SECONDS := 20.0
const FADE_SECONDS := 1.4

var _scenes: Array[Node2D] = []
var _scene_index := 0
var _rotate_timer := 0.0
var _fade_tween: Tween
var _time := 0.0

var _neon: Sprite2D
var _clouds_a: Sprite2D
var _clouds_b: Sprite2D
var _sparkles: CPUParticles2D
var _smog: CPUParticles2D
var _dust: CPUParticles2D

var _title: TextureRect
var _title_base_y := 0.0
var _buttons: VBoxContainer
var _settings: SettingsPanel


func _ready() -> void:
	add_to_group("main_menu")
	var camera := Camera2D.new()
	add_child(camera)
	camera.make_current()
	_build_scenes()
	_build_ui()
	_activate(0, true)


func show_backdrop(index: int) -> void:  # harness hook for screenshots
	_activate(clampi(index, 0, _scenes.size() - 1), true)
	_rotate_timer = 0.0


func _process(delta: float) -> void:
	_time += delta
	_rotate_timer += delta
	if _rotate_timer >= SCENE_SECONDS:
		_rotate_timer = 0.0
		_activate((_scene_index + 1) % _scenes.size(), false)

	_title.position.y = _title_base_y + roundf(sin(_time * 1.3) * 2.0)

	# per-scene life
	if _neon.visible:
		var flick := 1.0
		if fmod(_time, 7.3) < 0.4:
			flick = 0.15 if fmod(_time * 31.0, 1.0) < 0.5 else 0.9
		elif fmod(_time * 13.0, 1.0) < 0.06:
			flick = 0.55
		_neon.modulate.a = flick
	if _clouds_a.visible:
		var w := 960.0
		_clouds_a.position.x = wrapf(_clouds_a.position.x - 3.5 * delta, -w, w)
		_clouds_b.position.x = _clouds_a.position.x + (w if _clouds_a.position.x < 0 else -w)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") and _settings.visible:
		get_viewport().set_input_as_handled()
		_close_settings()


# ------------------------------------------------------------- backdrops ----

func _backdrop(scene_root: Node2D, texture_name: String) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.texture = load("res://art/gen/%s.png" % texture_name)
	scene_root.add_child(sprite)
	return sprite


func _build_scenes() -> void:
	# 1: the master hoard
	var hoard := Node2D.new()
	_backdrop(hoard, "menu_hoard")
	_sparkles = CPUParticles2D.new()
	_sparkles.texture = load("res://art/gen/dust.png")
	_sparkles.amount = 26
	_sparkles.lifetime = 7.0
	_sparkles.preprocess = 7.0
	_sparkles.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_sparkles.emission_rect_extents = Vector2(220, 40)
	_sparkles.position = Vector2(0, 130)
	_sparkles.direction = Vector2(0, -1)
	_sparkles.spread = 12.0
	_sparkles.gravity = Vector2.ZERO
	_sparkles.initial_velocity_min = 8.0
	_sparkles.initial_velocity_max = 20.0
	_sparkles.color = Color("e8c170")
	_sparkles.color_ramp = _fade_ramp()
	hoard.add_child(_sparkles)
	add_child(hoard)
	_scenes.append(hoard)

	# 2: the neon scrapyard
	var scrap := Node2D.new()
	_backdrop(scrap, "menu_scrapyard")
	_neon = Sprite2D.new()
	_neon.texture = load("res://art/gen/menu_scrapyard_neon.png")
	_neon.centered = false
	_neon.position = Vector2(-480 + 148, -272 + 110)  # over the dark sign panel
	scrap.add_child(_neon)
	_smog = CPUParticles2D.new()
	_smog.texture = load("res://art/gen/dust.png")
	_smog.amount = 30
	_smog.lifetime = 11.0
	_smog.preprocess = 11.0
	_smog.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_smog.emission_rect_extents = Vector2(460, 60)
	_smog.position = Vector2(0, 200)
	_smog.direction = Vector2(0.2, -1)
	_smog.spread = 25.0
	_smog.gravity = Vector2.ZERO
	_smog.initial_velocity_min = 6.0
	_smog.initial_velocity_max = 14.0
	_smog.scale_amount_min = 2.0
	_smog.scale_amount_max = 4.0
	_smog.color = Color("577277", 0.4)
	_smog.color_ramp = _fade_ramp()
	scrap.add_child(_smog)
	add_child(scrap)
	_scenes.append(scrap)

	# 3: the overlook
	var overlook := Node2D.new()
	_backdrop(overlook, "menu_overlook")
	_clouds_a = Sprite2D.new()
	_clouds_a.texture = load("res://art/gen/menu_overlook_clouds.png")
	_clouds_a.position = Vector2(0, -180)
	overlook.add_child(_clouds_a)
	_clouds_b = Sprite2D.new()
	_clouds_b.texture = _clouds_a.texture
	_clouds_b.position = Vector2(960, -180)
	overlook.add_child(_clouds_b)
	_dust = CPUParticles2D.new()
	_dust.texture = load("res://art/gen/dust.png")
	_dust.amount = 24
	_dust.lifetime = 8.0
	_dust.preprocess = 8.0
	_dust.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_dust.emission_rect_extents = Vector2(460, 200)
	_dust.direction = Vector2(1, 0.1)
	_dust.spread = 10.0
	_dust.gravity = Vector2.ZERO
	_dust.initial_velocity_min = 18.0
	_dust.initial_velocity_max = 40.0
	_dust.color = Color("819796", 0.4)
	_dust.color_ramp = _fade_ramp()
	overlook.add_child(_dust)
	add_child(overlook)
	_scenes.append(overlook)

	for scene in _scenes:
		scene.modulate.a = 0.0
		scene.visible = false


func _fade_ramp() -> Gradient:
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0))
	ramp.add_point(0.2, Color(1, 1, 1, 1))
	ramp.add_point(0.8, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	return ramp


func _activate(index: int, instant: bool) -> void:
	var prev := _scenes[_scene_index]
	var next := _scenes[index]
	_scene_index = index
	next.visible = true
	if _fade_tween != null:
		_fade_tween.kill()
	if instant:
		next.modulate.a = 1.0
		for scene in _scenes:
			if scene != next:
				scene.visible = false
				scene.modulate.a = 0.0
		return
	_fade_tween = create_tween().set_parallel(true)
	_fade_tween.tween_property(next, "modulate:a", 1.0, FADE_SECONDS)
	if prev != next:
		_fade_tween.tween_property(prev, "modulate:a", 0.0, FADE_SECONDS)
		_fade_tween.chain().tween_callback(func() -> void: prev.visible = false)


# ------------------------------------------------------------------- ui ------

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
	var tw := float(_title.texture.get_width())
	_title.anchor_left = 0.5
	_title.anchor_right = 0.5
	_title.offset_left = -tw / 2.0
	_title.offset_right = tw / 2.0
	_title.offset_top = 52
	_title.offset_bottom = 52 + _title.texture.get_height()
	_title.stretch_mode = TextureRect.STRETCH_KEEP
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_title_base_y = _title.offset_top
	root.add_child(_title)

	var tagline := Label.new()
	tagline.text = "loot. extract. survive."
	tagline.anchor_left = 0.5
	tagline.anchor_right = 0.5
	tagline.offset_left = -160
	tagline.offset_right = 160
	tagline.offset_top = 126
	tagline.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tagline.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	root.add_child(tagline)

	_buttons = VBoxContainer.new()
	_buttons.anchor_left = 0.5
	_buttons.anchor_right = 0.5
	_buttons.anchor_top = 0.62
	_buttons.anchor_bottom = 0.62
	_buttons.offset_left = -85
	_buttons.offset_right = 85
	_buttons.add_theme_constant_override("separation", 8)
	_menu_button(_buttons, "deploy", func() -> void:
		get_tree().change_scene_to_file("res://scenes/main.tscn"))
	_menu_button(_buttons, "settings", _open_settings)
	_menu_button(_buttons, "quit", func() -> void: get_tree().quit())
	root.add_child(_buttons)

	_settings = SettingsPanel.new()
	_settings.visible = false
	_settings.closed.connect(_close_settings)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	center.add_child(_settings)
	root.add_child(center)

	var version := Label.new()
	version.text = "pre-alpha v0.5.2"
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
