extends Node2D
## Main menu. Generated backdrop scenes rotate with a slow crossfade,
## each with its own living detail:
##   hoard      - gold sparkles rising past the buttons
##   scrapyard  - flickering neon sign + drifting smog
##   overlook   - clouds drifting over a dead city, dust on the wind
## DEPLOY starts the raid.

const SCENE_SECONDS := 20.0
const FADE_SECONDS := 1.4

# preloaded once for the process lifetime: re-entering the menu from the game
# must not re-decode these (that decode was a visible 1-2 frame hitch)
const TEX_HOARD := preload("res://art/gen/menu_hoard.png")
const TEX_SCRAP := preload("res://art/gen/menu_scrapyard.png")
const TEX_SCRAP_NEON := preload("res://art/gen/menu_scrapyard_neon.png")
const TEX_OVERLOOK := preload("res://art/gen/menu_overlook.png")
const TEX_CLOUDS := preload("res://art/gen/menu_overlook_clouds.png")
const TEX_DUST := preload("res://art/gen/dust.png")
const TEX_VIGNETTE := preload("res://art/gen/vignette.png")
const TEX_TITLE := preload("res://art/gen/title.png")

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
var _changelog: PanelContainer

# readable in-game summary; the full detail lives in CHANGELOG.md
const CHANGELOG_ENTRIES := [
	["v0.5.4", ["changelog viewer (this!)", "smoother return to menu from a raid"]],
	["v0.5.3", ["roofs rebuilt from modular pieces - clean corners everywhere"]],
	["v0.5.2", ["roofs sit flush on walls", "roof only hides when actually inside",
		"red brick + gray masonry buildings, two roof shades", "back-view neck fixed"]],
	["v0.5.1", ["clean floating menu buttons", "first sounds: button hover blips",
		"walls always stay visible", "one doorway per building",
		"hair + symmetric arms", "main menu button while paused"]],
	["v0.5.0", ["text crisp for real (font bug found)", "new lowercase pixel font",
		"real thin walls with door frames", "rotating menu backdrops"]],
	["v0.4.0", ["first main menu", "pixel font everywhere",
		"roofs + walk-inside reveal", "every prop got variations",
		"resolution setting"]],
	["v0.3.0", ["pause menu + settings", "fullscreen fills the whole screen"]],
	["v0.2.1", ["smooth motion on high-refresh monitors", "fullscreen by default"]],
	["v0.2.0", ["smooth ground, no tile grid", "brick buildings",
		"props with real variety", "better walk animation"]],
	["v0.1.1", ["fixed the play shortcut"]],
	["v0.1.0", ["the first build: a walkable ruined block"]],
]


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
	if not event.is_action_pressed("ui_cancel"):
		return
	if _settings.visible:
		get_viewport().set_input_as_handled()
		_close_settings()
	elif _changelog.visible:
		get_viewport().set_input_as_handled()
		_close_changelog()


# ------------------------------------------------------------- backdrops ----

func _backdrop(scene_root: Node2D, texture: Texture2D) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.texture = texture
	scene_root.add_child(sprite)
	return sprite


func _build_scenes() -> void:
	# 1: the master hoard
	var hoard := Node2D.new()
	_backdrop(hoard, TEX_HOARD)
	_sparkles = CPUParticles2D.new()
	_sparkles.texture = TEX_DUST
	_sparkles.amount = 26
	_sparkles.lifetime = 7.0
	_sparkles.preprocess = 5.0
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
	_backdrop(scrap, TEX_SCRAP)
	_neon = Sprite2D.new()
	_neon.texture = TEX_SCRAP_NEON
	_neon.centered = false
	_neon.position = Vector2(-480 + 148, -272 + 110)  # over the dark sign panel
	scrap.add_child(_neon)
	_smog = CPUParticles2D.new()
	_smog.texture = TEX_DUST
	_smog.amount = 30
	_smog.lifetime = 11.0
	_smog.preprocess = 0.0
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
	_backdrop(overlook, TEX_OVERLOOK)
	_clouds_a = Sprite2D.new()
	_clouds_a.texture = TEX_CLOUDS
	_clouds_a.position = Vector2(0, -180)
	overlook.add_child(_clouds_a)
	_clouds_b = Sprite2D.new()
	_clouds_b.texture = _clouds_a.texture
	_clouds_b.position = Vector2(960, -180)
	overlook.add_child(_clouds_b)
	_dust = CPUParticles2D.new()
	_dust.texture = TEX_DUST
	_dust.amount = 24
	_dust.lifetime = 8.0
	_dust.preprocess = 0.0
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
	vignette.texture = TEX_VIGNETTE
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(vignette)

	_title = TextureRect.new()
	_title.texture = TEX_TITLE
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

	var changelog_btn := Button.new()
	changelog_btn.text = "changelog"
	changelog_btn.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	changelog_btn.offset_left = -86
	changelog_btn.offset_top = -40
	changelog_btn.offset_right = -6
	changelog_btn.offset_bottom = -20
	changelog_btn.pressed.connect(_open_changelog)
	root.add_child(changelog_btn)

	var version := Label.new()
	version.text = "pre-alpha v0.5.4"
	version.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	version.offset_left = -130
	version.offset_top = -16
	version.offset_right = -6
	version.offset_bottom = -4
	version.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	version.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	root.add_child(version)

	_changelog = _build_changelog_panel()
	var changelog_center := CenterContainer.new()
	changelog_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	changelog_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	changelog_center.add_child(_changelog)
	root.add_child(changelog_center)


func _build_changelog_panel() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.visible = false
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	var title := Label.new()
	title.text = "changelog"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(280, 210)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 3)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for entry in CHANGELOG_ENTRIES:
		var version_label := Label.new()
		version_label.text = str(entry[0])
		version_label.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
		list.add_child(version_label)
		for line in (entry[1] as Array):
			var item := Label.new()
			item.text = "- " + str(line)
			item.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			item.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			item.add_theme_color_override("font_color", UITheme.TEXT_DIM)
			list.add_child(item)
		var gap := Control.new()
		gap.custom_minimum_size = Vector2(0, 4)
		list.add_child(gap)
	scroll.add_child(list)
	box.add_child(scroll)

	var back := Button.new()
	back.text = "< back"
	back.pressed.connect(_close_changelog)
	box.add_child(back)
	panel.add_child(box)
	return panel


func _open_changelog() -> void:
	_buttons.visible = false
	_changelog.visible = true


func _close_changelog() -> void:
	_changelog.visible = false
	_buttons.visible = true


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
