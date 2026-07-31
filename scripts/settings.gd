extends Node
## Settings autoload: persisted user options (user://settings.cfg), applied
## globally at boot and whenever the pause menu changes them.
## `quality` is read by future systems (lighting, effects density).

const PATH := "user://settings.cfg"

const DISPLAY_BORDERLESS := 0
const DISPLAY_WINDOWED := 1

# design-base view size; the real view EXPANDS from this to fill the window
# at the largest whole-number pixel scale (no letterbox, no fractional blur)
const BASE_VIEW := Vector2i(640, 360)

var display_mode := DISPLAY_BORDERLESS
var quality := 2       # 0 low, 1 medium, 2 high
var max_fps := 0       # 0 = uncapped
var vsync := true
var show_fps := false

var _fps_label: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_load()
	_build_fps_overlay()
	get_window().size_changed.connect(_update_scale)
	apply_all()
	_update_scale()


func _update_scale() -> void:
	var win := get_window()
	var size: Vector2i = win.size
	if size.x < 1 or size.y < 1:
		return
	@warning_ignore("integer_division")
	var scale := maxi(1, mini(size.x / BASE_VIEW.x, size.y / BASE_VIEW.y))
	win.content_scale_size = Vector2i(
		ceili(size.x / float(scale)), ceili(size.y / float(scale)))


func _process(_delta: float) -> void:
	if _fps_label.visible:
		_fps_label.text = "%d FPS" % roundi(Engine.get_frames_per_second())


func apply_all() -> void:
	var want_mode := DisplayServer.WINDOW_MODE_FULLSCREEN \
		if display_mode == DISPLAY_BORDERLESS else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != want_mode:
		DisplayServer.window_set_mode(want_mode)
		if want_mode == DisplayServer.WINDOW_MODE_WINDOWED:
			var size := Vector2i(1280, 720)
			DisplayServer.window_set_size(size)
			DisplayServer.window_set_position(
				DisplayServer.screen_get_position() + (DisplayServer.screen_get_size() - size) / 2)
	Engine.max_fps = max_fps
	DisplayServer.window_set_vsync_mode(
		DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)
	_fps_label.visible = show_fps
	_save()


func _build_fps_overlay() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 100
	_fps_label = Label.new()
	_fps_label.position = Vector2(4, 2)
	_fps_label.add_theme_font_size_override("font_size", 10)
	_fps_label.add_theme_color_override("font_color", Color("d0da91"))
	_fps_label.add_theme_color_override("font_outline_color", Color("090a14"))
	_fps_label.add_theme_constant_override("outline_size", 2)
	_fps_label.visible = false
	layer.add_child(_fps_label)
	add_child(layer)


func _load() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	display_mode = int(cfg.get_value("video", "display_mode", display_mode))
	quality = int(cfg.get_value("video", "quality", quality))
	max_fps = int(cfg.get_value("video", "max_fps", max_fps))
	vsync = bool(cfg.get_value("video", "vsync", vsync))
	show_fps = bool(cfg.get_value("video", "show_fps", show_fps))


func _save() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("video", "display_mode", display_mode)
	cfg.set_value("video", "quality", quality)
	cfg.set_value("video", "max_fps", max_fps)
	cfg.set_value("video", "vsync", vsync)
	cfg.set_value("video", "show_fps", show_fps)
	cfg.save(PATH)
