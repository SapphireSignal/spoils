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
const TEX_SHINE := preload("res://art/gen/title_shine.png")
const TEX_TAGLINE := preload("res://art/gen/tagline.png")

const SHINE_PERIOD := 6.0   # seconds between gleams
const SHINE_SWEEP := 0.9    # gleam travel time
const SHINE_WIDTH := 34.0

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
var _shine_clip: Control
var _shine: TextureRect
var _buttons: VBoxContainer
var _settings: SettingsPanel
var _keybinds: KeybindsPanel
var _changelog: PanelContainer
var _changelog_list: VBoxContainer

# readable in-game summary; the full detail lives in CHANGELOG.md
const CHANGELOG_ENTRIES := [
	["v0.6.7", ["the barricade line is a real line now: one piece repeated, worn",
		"some barriers knocked askew, some flat, uneven gaps - not a sampler",
		"past the line is bare dead concrete - the woods live inside the map",
		"roads dead-end at the wreckage on the line",
		"biomes blend: grass creeps onto touching concrete, dirt smears too",
		"no more lone grass tiles - pockets and groves have real shapes",
		"the fallen out past the line are full character-sized now",
		"prone is beefier - same proportions as standing, all 8 directions"]],
	["v0.6.6", ["go prone on z: flat on your stomach, crawling",
		"prone is slower than crouch - low, slow, hard to spot",
		"crouch input stands you back up out of prone",
		"the door prompt now floats on the door itself"]],
	["v0.6.5", ["the playable map is smaller - barricades mark the real edge now",
		"the world visibly continues past the line, but the sniper owns it",
		"fallen raiders lie out past the barricades. let them be a warning",
		"the camera never shifts at the edge - locked on you, always",
		"push deeper past the line and the shots only come faster",
		"cars have real fronts and backs - grilles, lights, bumpers, trunks",
		"truck cargo sits inside the bed now, nothing pokes through the cab",
		"deploying no longer dips the framerate",
		"a prompt appears at doors: press f to open, press f to close",
		"the flashlight actually clicks",
		"weather fades in and out slowly - no more sudden color shifts",
		"deep night is much darker - the flashlight and lamps matter now",
		"new on the roadmap: tarkov-style loot and gear slots, quests, a second map"]],
	["v0.6.4", ["fixed the blurry walk: character and camera share one pixel grid now",
		"diagonal walking no longer shimmers the world",
		"the character is pixel-locked to the screen while moving"]],
	["v0.6.3", ["the map is 4x bigger again - and it has a name: transit",
		"every deploy now builds a fresh district",
		"walk to the true edge of the map - no early wall, no black void",
		"but the edge is sniper country: heed the warning or take 3 hits",
		"hurt flashes, death and respawn - the game's first damage",
		"doors are real: closed until you walk up and press f",
		"flashlight on e - nights are properly dark now",
		"street lights glow and flicker at night - most are dead, like the district",
		"rain is real: drops fall in the world and splash where they land",
		"splashes stay on the ground instead of following you",
		"all rain is the same blue as the puddles",
		"storms and lightning last longer; a full day is 20 minutes",
		"dusk fades properly - no more instant nighttime (found the bug)",
		"cars are wider, face the right way in their lanes, some broken into",
		"litter around broken cars; sticks under the trees",
		"trees rebuilt: connected tops, a new leafy kind, groves inside the map",
		"crate stacks no longer clip their top box",
		"roof edges are clean - removed the rippling overhang",
		"one floor per building - no more patchwork interiors",
		"center dashes on every road, seamless from tile to tile",
		"furniture can never block an entrance again",
		"left arm seam restored - symmetric character again",
		"fewer dots on the ground everywhere",
		"walking is smoother: camera scrolls in screen pixels now",
		"deploy no longer dips the framerate - the world builds across frames",
		"fps counter updates five times a second"]],
	["v0.6.2", ["the map is 10x bigger - a whole district, and it never ends",
		"edges fade into deep woods, no more visible void",
		"road network across the map + dirt roads into the forests",
		"forests full of pines and dead trees",
		"12 randomized buildings to explore, houses and warehouses",
		"street lights along the roads",
		"real vehicles: cars and loaded pickups, parked and abandoned",
		"doors on every building", "warehouse floors are gray concrete now",
		"day turns to night and back", "rain comes and goes, with lightning",
		"raindrops visibly hit the ground", "puddles form in rain, dry in sun",
		"deploying screen when you enter a raid (no more frame dip)",
		"house furniture fixed - bookshelf is back, no barrels indoors",
		"less random junk, and it gathers around buildings now"]],
	["v0.6.1", ["loading yard by the warehouse: stall lines, pickup trucks",
		"boxes in the truck beds, stray stock around the yard",
		"crouch: hold or toggle option next to its keybind",
		"warehouse floor is a green sealed screed now",
		"racks + crate stacks: messy randomized loads, nothing identical",
		"roof corner caps flush, trim lines continue through corners",
		"gold in the vault falls down the light shaft",
		"menu buttons exactly centered, smaller static tagline",
		"silver shine sweeps the title",
		"version plan: 0.7 guns, 0.8 enemies, 0.9 raid loop, 1.0 full game"]],
	["v0.6.0", ["keybinds screen in settings: rebind every key",
		"crouch on ctrl: lower profile, slower movement, crouched sprites",
		"interact, reload, flashlight and weapon slot keys registered",
		"house and warehouse are different sizes, doors always visible",
		"wooden floors in the house, dark screed in the warehouse",
		"furniture: couch, tv, cabinet, bookshelf, table, chairs",
		"warehouse racks and stacked stock - all randomized placement",
		"broken roof sections over the ruined corner", "all roofs black",
		"bigger title with a readable outlined tagline",
		"vsync now greys out the fps cap (it drives the frame rate)",
		"settings window is a fixed, slightly wider size"]],
	["v0.5.6", ["all walls and corners symmetrical again",
		"slim wall tops - the wide cap looked like a lid on a thin wall",
		"roof eaves now overhang and fully cover the wall tops",
		"roof caps over every corner post and door jamb",
		"buttons restyled: dark with a light border - readable on every scene", "changelog button visible again"]],
	["v0.5.5", ["more detail in this changelog",
		"new burgundy buttons that stand out on every backdrop",
		"changelog link dimmed to match the footer"]],
	["v0.5.4", ["changelog viewer (this!)",
		"menu art stays loaded so returning from a raid does not hitch",
		"only the first backdrop pre-warms its particles"]],
	["v0.5.3", ["roofs rebuilt from modular pieces placed by exact formula",
		"one roof tile per floor cell + trim pieces on the eaves",
		"wall caps now tuck under the roof instead of poking past it",
		"corner posts sit flush in the roofline - clean corners everywhere"]],
	["v0.5.2", ["roofs sit flush on the walls (were overhanging)",
		"roof only hides when you are actually inside the walls",
		"buildings are different materials: red brick vs gray masonry",
		"the two roofs are different shades of black",
		"back-view neck fixed and verified with an in-game capture"]],
	["v0.5.1", ["menu buttons: no box around them, slightly see-through",
		"first sounds in the game: soft hover + click blips, made by code",
		"walls always stay visible inside buildings (no see-through)",
		"one doorway per building (a frame post was splitting it in two)",
		"character has hair now instead of the beanie",
		"arms are truly symmetric", "main menu button on the pause screen"]],
	["v0.5.0", ["text crisp for real - found the font bug that blurred all ui",
		"new lowercase-only pixel font, no capitals anywhere",
		"buildings became real thin walls with door frames and posts",
		"three rotating menu backdrops with sparkles, neon and clouds",
		"treasure vault, scrapyard and cliff overlook scenes"]],
	["v0.4.0", ["first main menu with a live background",
		"first pixel font for the ui", "roofs + walk-inside roof reveal",
		"every prop family got real variations: sizes, damage, fallen poses",
		"barrels, crates, cylinders, tires, pallets, dumpsters, rubble, pillars",
		"resolution option in settings", "fps counter moved and restyled"]],
	["v0.3.0", ["pause menu on esc with settings and quit",
		"display mode, fps cap slider, vsync, show fps",
		"settings save and reload on launch",
		"fullscreen fills the whole screen at crisp pixel scale"]],
	["v0.2.1", ["motion updates every frame - smooth on 240hz monitors",
		"camera locked to whole pixels: no more shimmer while walking",
		"fullscreen by default"]],
	["v0.2.0", ["ground is one smooth surface, no more tile grid",
		"buildings rebuilt in brick with windows",
		"props got distinct shapes instead of recolors",
		"6-frame walk cycle with real leg movement"]],
	["v0.1.1", ["fixed the play shortcut not launching"]],
	["v0.1.0", ["the first build: a walkable ruined block",
		"iso world, roads, two buildings, scattered props",
		"8-direction movement and collision",
		"all art generated from a 46-color palette"]],
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

	# silver gleam sweeping across the wordmark every few seconds
	var phase := fmod(_time, SHINE_PERIOD)
	if phase < SHINE_SWEEP:
		_shine_clip.visible = true
		var title_pos := _title.global_position
		var travel := _title.size.x + SHINE_WIDTH * 2.0
		_shine_clip.global_position = Vector2(
			roundf(title_pos.x - SHINE_WIDTH + travel * (phase / SHINE_SWEEP)),
			title_pos.y)
		_shine.global_position = title_pos
	else:
		_shine_clip.visible = false

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
	if _keybinds.visible:
		get_viewport().set_input_as_handled()
		_close_keybinds()
	elif _settings.visible:
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
	# gold dust FALLING down the light shaft onto the pile (user call)
	_sparkles = CPUParticles2D.new()
	_sparkles.texture = TEX_DUST
	_sparkles.amount = 30
	_sparkles.lifetime = 12.0
	_sparkles.preprocess = 12.0
	_sparkles.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_sparkles.emission_rect_extents = Vector2(70, 10)
	_sparkles.position = Vector2(0, -250)
	_sparkles.direction = Vector2(0, 1)
	_sparkles.spread = 8.0
	_sparkles.gravity = Vector2(0, 6)
	_sparkles.initial_velocity_min = 18.0
	_sparkles.initial_velocity_max = 34.0
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

	# gleam layer: a narrow clipping window sweeps over a silver copy
	_shine_clip = Control.new()
	_shine_clip.clip_contents = true
	_shine_clip.size = Vector2(SHINE_WIDTH, _title.texture.get_height())
	_shine_clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shine_clip.visible = false
	_shine = TextureRect.new()
	_shine.texture = TEX_SHINE
	_shine.stretch_mode = TextureRect.STRETCH_KEEP
	_shine.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shine_clip.add_child(_shine)
	root.add_child(_shine_clip)

	# tagline: its own small static image (not animated with the title)
	var tagline := TextureRect.new()
	tagline.texture = TEX_TAGLINE
	var tag_w := float(tagline.texture.get_width())
	tagline.anchor_left = 0.5
	tagline.anchor_right = 0.5
	tagline.offset_left = -tag_w / 2.0
	tagline.offset_right = tag_w / 2.0
	tagline.offset_top = 52 + _title.texture.get_height() + 4
	tagline.offset_bottom = tagline.offset_top + tagline.texture.get_height()
	tagline.stretch_mode = TextureRect.STRETCH_KEEP
	tagline.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(tagline)

	# dead-center, growing both ways: stays perfectly centered no matter how
	# many buttons this list gains later
	_buttons = VBoxContainer.new()
	_buttons.anchor_left = 0.5
	_buttons.anchor_right = 0.5
	_buttons.anchor_top = 0.5
	_buttons.anchor_bottom = 0.5
	_buttons.offset_left = -85
	_buttons.offset_right = 85
	_buttons.grow_vertical = Control.GROW_DIRECTION_BOTH
	_buttons.add_theme_constant_override("separation", 8)
	_menu_button(_buttons, "deploy", func() -> void:
		get_tree().change_scene_to_file("res://scenes/main.tscn"))
	_menu_button(_buttons, "settings", _open_settings)
	_menu_button(_buttons, "quit", func() -> void: get_tree().quit())
	root.add_child(_buttons)

	_settings = SettingsPanel.new()
	_settings.visible = false
	_settings.closed.connect(_close_settings)
	_settings.keybinds_requested.connect(_open_keybinds)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	center.add_child(_settings)
	root.add_child(center)

	_keybinds = KeybindsPanel.new()
	_keybinds.visible = false
	_keybinds.closed.connect(_close_keybinds)
	var kb_center := CenterContainer.new()
	kb_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	kb_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	kb_center.add_child(_keybinds)
	root.add_child(kb_center)

	# same look as every other button (a flat/dim version was invisible on
	# the darker backdrops)
	var changelog_btn := Button.new()
	changelog_btn.text = "changelog"
	changelog_btn.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	changelog_btn.offset_left = -96
	changelog_btn.offset_top = -44
	changelog_btn.offset_right = -6
	changelog_btn.offset_bottom = -22
	changelog_btn.pressed.connect(_open_changelog)
	root.add_child(changelog_btn)

	# single source of truth: the corner label always shows the newest
	# changelog entry's version, so the two can never drift apart again
	var version := Label.new()
	version.text = "pre-alpha %s" % str(CHANGELOG_ENTRIES[0][0])
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
	_changelog_list = VBoxContainer.new()
	_changelog_list.add_theme_constant_override("separation", 3)
	_changelog_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	# rows are built LAZILY on first open — a few hundred labels made the
	# menu heavy to build and heavy to tear down on deploy (frame spike)
	scroll.add_child(_changelog_list)
	box.add_child(scroll)

	var back := Button.new()
	back.text = "< back"
	back.pressed.connect(_close_changelog)
	box.add_child(back)
	panel.add_child(box)
	return panel


func _open_changelog() -> void:
	if _changelog_list.get_child_count() == 0:
		for entry in CHANGELOG_ENTRIES:
			var version_label := Label.new()
			version_label.text = str(entry[0])
			version_label.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
			_changelog_list.add_child(version_label)
			for line in (entry[1] as Array):
				var item := Label.new()
				item.text = "- " + str(line)
				item.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				item.size_flags_horizontal = Control.SIZE_EXPAND_FILL
				item.add_theme_color_override("font_color", UITheme.TEXT_DIM)
				_changelog_list.add_child(item)
			var gap := Control.new()
			gap.custom_minimum_size = Vector2(0, 4)
			_changelog_list.add_child(gap)
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


func _open_keybinds() -> void:
	_settings.visible = false
	_keybinds.visible = true


func _close_keybinds() -> void:
	_keybinds.visible = false
	_settings.visible = true
