extends Node
## Settings autoload: persisted user options (user://settings.cfg), applied
## globally at boot and whenever a settings panel changes them.
## `quality` is read by future systems (lighting, effects density).

const PATH := "user://settings.cfg"

const DISPLAY_BORDERLESS := 0
const DISPLAY_WINDOWED := 1

# index 0 = desktop resolution; explicit sizes apply to windowed mode
const RESOLUTIONS: Array[Vector2i] = [
	Vector2i.ZERO, Vector2i(1920, 1080), Vector2i(1680, 1080),
	Vector2i(1600, 900), Vector2i(1366, 768), Vector2i(1280, 720),
]

# design-base view size; the real view EXPANDS from this to fill the window
# at the largest whole-number pixel scale (no letterbox, no fractional blur)
const BASE_VIEW := Vector2i(640, 360)

# rebindable actions and their default physical keys
const BIND_ACTIONS: Array[String] = [
	"move_up", "move_down", "move_left", "move_right",
	"interact", "crouch", "prone", "reload", "flashlight",
	"map", "inventory",
	"slot_primary", "slot_secondary", "slot_melee",
]
const BIND_LABELS := {
	"move_up": "move up", "move_down": "move down",
	"move_left": "move left", "move_right": "move right",
	"interact": "interact", "crouch": "crouch", "prone": "prone",
	"reload": "reload", "flashlight": "flashlight",
	"map": "open map", "inventory": "inventory",
	"slot_primary": "primary weapon", "slot_secondary": "secondary weapon",
	"slot_melee": "melee weapon",
}
const DEFAULT_BINDS := {
	"move_up": KEY_W, "move_down": KEY_S, "move_left": KEY_A, "move_right": KEY_D,
	"interact": KEY_F, "crouch": KEY_CTRL, "prone": KEY_Z, "reload": KEY_R,
	"flashlight": KEY_E,
	"map": KEY_M, "inventory": KEY_TAB,
	"slot_primary": KEY_1, "slot_secondary": KEY_2, "slot_melee": KEY_3,
}
# arrows stay as secondary movement keys while on default binds
const ARROW_EXTRAS := {
	"move_up": KEY_UP, "move_down": KEY_DOWN,
	"move_left": KEY_LEFT, "move_right": KEY_RIGHT,
}

var display_mode := DISPLAY_BORDERLESS
var resolution := 0
var quality := 2       # 0 low, 1 medium, 2 high
var max_fps := 0       # 0 = uncapped
var vsync := true
var show_fps := false
var crouch_toggle := false  # false = hold to crouch, true = toggle
var binds: Dictionary = {}  # action -> physical keycode
var pixel_scale := 1   # current integer window scale (world px -> screen px)
# mix volumes, 0..1 — applied to audio buses, never to player volume_db
# (fades and per-sound levels own those)
var volume_master := 1.0
var volume_music := 1.0
var volume_sfx := 1.0
var volume_ambient := 1.0

var _fps_label: Label
var _fps_frames := 0
var _fps_time := 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	# Settings autoloads before Sfx and Music, so the mix buses exist
	# before any player asks to route through them
	_ensure_audio_buses()
	for action in BIND_ACTIONS:
		binds[action] = DEFAULT_BINDS[action]
	_load()
	_build_fps_overlay()
	get_window().size_changed.connect(_update_scale)
	apply_all()
	apply_binds()
	apply_volumes()
	_update_scale()


func _ensure_audio_buses() -> void:
	for bus_name in ["music", "sfx", "ambient"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			var i := AudioServer.bus_count
			AudioServer.add_bus(i)
			AudioServer.set_bus_name(i, bus_name)
			AudioServer.set_bus_send(i, "Master")


func apply_volumes() -> void:
	_apply_bus("Master", volume_master)
	_apply_bus("music", volume_music)
	_apply_bus("sfx", volume_sfx)
	_apply_bus("ambient", volume_ambient)


func _apply_bus(bus_name: String, v: float) -> void:
	var i := AudioServer.get_bus_index(bus_name)
	if i == -1:
		return
	AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.0001)))
	AudioServer.set_bus_mute(i, v <= 0.001)


func get_volume(which: String) -> float:
	match which:
		"master": return volume_master
		"music": return volume_music
		"sfx": return volume_sfx
		"ambient": return volume_ambient
	return 1.0


func set_volume(which: String, v: float) -> void:
	v = clampf(v, 0.0, 1.0)
	match which:
		"master": volume_master = v
		"music": volume_music = v
		"sfx": volume_sfx = v
		"ambient": volume_ambient = v
	apply_volumes()
	_save()


func apply_binds() -> void:
	for action in BIND_ACTIONS:
		InputMap.action_erase_events(action)
		var event := InputEventKey.new()
		event.physical_keycode = binds[action]
		InputMap.action_add_event(action, event)
		if ARROW_EXTRAS.has(action) and binds[action] == DEFAULT_BINDS[action]:
			var arrow := InputEventKey.new()
			arrow.physical_keycode = ARROW_EXTRAS[action]
			InputMap.action_add_event(action, arrow)


func set_bind(action: String, physical_keycode: int) -> void:
	binds[action] = physical_keycode
	apply_binds()
	_save()


func set_crouch_toggle(on: bool) -> void:
	crouch_toggle = on
	_save()


func reset_binds() -> void:
	for action in BIND_ACTIONS:
		binds[action] = DEFAULT_BINDS[action]
	apply_binds()
	_save()


func bind_label(action: String) -> String:
	var code: int = binds[action]
	var keycode := DisplayServer.keyboard_get_keycode_from_physical(code)
	var label := OS.get_keycode_string(keycode)
	return label if label != "" else OS.get_keycode_string(code)


func _process(delta: float) -> void:
	# own 0.2 s window instead of Engine.get_frames_per_second() (which only
	# updates once a second — too slow to catch a real dip)
	_fps_frames += 1
	_fps_time += delta
	if _fps_time >= 0.2:
		_fps_label.text = "%d fps" % roundi(_fps_frames / _fps_time)
		_fps_frames = 0
		_fps_time = 0.0


func resolution_label(index: int) -> String:
	if index == 0:
		var s := DisplayServer.screen_get_size()
		return "desktop (%dx%d)" % [s.x, s.y]
	var r := RESOLUTIONS[index]
	return "%dx%d" % [r.x, r.y]


func apply_all() -> void:
	var want_mode := DisplayServer.WINDOW_MODE_FULLSCREEN \
		if display_mode == DISPLAY_BORDERLESS else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != want_mode:
		DisplayServer.window_set_mode(want_mode)
	if want_mode == DisplayServer.WINDOW_MODE_WINDOWED:
		var size: Vector2i = RESOLUTIONS[resolution]
		if size == Vector2i.ZERO:
			size = DisplayServer.screen_get_size()
		if DisplayServer.window_get_size() != size:
			DisplayServer.window_set_size(size)
			@warning_ignore("integer_division")
			DisplayServer.window_set_position(DisplayServer.screen_get_position()
				+ (DisplayServer.screen_get_size() - size) / 2)
	Engine.max_fps = max_fps
	DisplayServer.window_set_vsync_mode(
		DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)
	_fps_label.visible = show_fps
	set_process(show_fps)  # the counter costs nothing while hidden
	_fps_frames = 0
	_fps_time = 0.0
	_save()
	_update_scale()


func _update_scale() -> void:
	var win := get_window()
	var size: Vector2i = win.size
	if size.x < 1 or size.y < 1:
		return
	@warning_ignore("integer_division")
	var scale := maxi(1, mini(size.x / BASE_VIEW.x, size.y / BASE_VIEW.y))
	pixel_scale = scale
	win.content_scale_size = Vector2i(
		ceili(size.x / float(scale)), ceili(size.y / float(scale)))


func _build_fps_overlay() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 100
	_fps_label = Label.new()
	_fps_label.anchor_left = 1.0
	_fps_label.anchor_right = 1.0
	_fps_label.offset_left = -84
	_fps_label.offset_right = -4
	_fps_label.offset_top = 3
	_fps_label.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_fps_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_fps_label.add_theme_font_override("font", UITheme.font())
	_fps_label.add_theme_font_size_override("font_size", 9)
	_fps_label.add_theme_color_override("font_color", UITheme.GOOD)
	_fps_label.add_theme_color_override("font_shadow_color", UITheme.SHADOW)
	_fps_label.add_theme_constant_override("shadow_offset_x", 1)
	_fps_label.add_theme_constant_override("shadow_offset_y", 1)
	_fps_label.visible = false
	layer.add_child(_fps_label)
	add_child(layer)


func _load() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	display_mode = int(cfg.get_value("video", "display_mode", display_mode))
	resolution = clampi(int(cfg.get_value("video", "resolution", resolution)),
		0, RESOLUTIONS.size() - 1)
	quality = int(cfg.get_value("video", "quality", quality))
	max_fps = int(cfg.get_value("video", "max_fps", max_fps))
	vsync = bool(cfg.get_value("video", "vsync", vsync))
	show_fps = bool(cfg.get_value("video", "show_fps", show_fps))
	crouch_toggle = bool(cfg.get_value("input", "crouch_toggle", crouch_toggle))
	for action in BIND_ACTIONS:
		binds[action] = int(cfg.get_value("input", action, binds[action]))
	volume_master = clampf(float(cfg.get_value("audio", "master", volume_master)), 0.0, 1.0)
	volume_music = clampf(float(cfg.get_value("audio", "music", volume_music)), 0.0, 1.0)
	volume_sfx = clampf(float(cfg.get_value("audio", "sfx", volume_sfx)), 0.0, 1.0)
	volume_ambient = clampf(float(cfg.get_value("audio", "ambient", volume_ambient)), 0.0, 1.0)


func _save() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("video", "display_mode", display_mode)
	cfg.set_value("video", "resolution", resolution)
	cfg.set_value("video", "quality", quality)
	cfg.set_value("video", "max_fps", max_fps)
	cfg.set_value("video", "vsync", vsync)
	cfg.set_value("video", "show_fps", show_fps)
	cfg.set_value("input", "crouch_toggle", crouch_toggle)
	for action in BIND_ACTIONS:
		cfg.set_value("input", action, binds[action])
	cfg.set_value("audio", "master", volume_master)
	cfg.set_value("audio", "music", volume_music)
	cfg.set_value("audio", "sfx", volume_sfx)
	cfg.set_value("audio", "ambient", volume_ambient)
	cfg.save(PATH)
