class_name PauseMenu
extends CanvasLayer
## Esc pause menu, built in code. Main panel: Back / Settings / Quit.
## Settings panel: display mode, graphics quality, FPS cap slider, VSync,
## FPS counter. Changes apply immediately and persist via the Settings autoload.

const PANEL_BG := Color("151d28")
const DIM := Color(0.035, 0.039, 0.078, 0.6)

var _dim: ColorRect
var _root: CenterContainer
var _main_box: VBoxContainer
var _settings_box: VBoxContainer
var _fps_value_label: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 50
	add_to_group("pause_menu")

	_dim = ColorRect.new()
	_dim.color = DIM
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_dim)

	_root = CenterContainer.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)

	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = PANEL_BG
	style.border_color = Color("577277")
	style.set_border_width_all(1)
	style.set_content_margin_all(12)
	panel.add_theme_stylebox_override("panel", style)
	_root.add_child(panel)

	_main_box = _build_main_box()
	panel.add_child(_main_box)
	_settings_box = _build_settings_box()
	_settings_box.visible = false
	panel.add_child(_settings_box)

	visible = false


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed("ui_cancel"):
		return
	get_viewport().set_input_as_handled()
	if not visible:
		open()
	elif _settings_box.visible:
		_show_main()
	else:
		close()


func open() -> void:
	visible = true
	get_tree().paused = true
	_show_main()


func open_settings() -> void:
	open()
	_show_settings()


func close() -> void:
	visible = false
	get_tree().paused = false


func _show_main() -> void:
	_main_box.visible = true
	_settings_box.visible = false


func _show_settings() -> void:
	_main_box.visible = false
	_settings_box.visible = true


# ------------------------------------------------------------------ UI ------

func _title(text: String) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", 14)
	label.add_theme_color_override("font_color", Color("ebede9"))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return label


func _button(text: String, handler: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(150, 22)
	button.add_theme_font_size_override("font_size", 11)
	button.pressed.connect(handler)
	return button


func _row(label_text: String, control: Control) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size = Vector2(92, 0)
	label.add_theme_font_size_override("font_size", 10)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	row.add_child(label)
	row.add_child(control)
	return row


func _build_main_box() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.add_child(_title("PAUSED"))
	box.add_child(_button("Back", close))
	box.add_child(_button("Settings", _show_settings))
	box.add_child(_button("Quit", func() -> void: get_tree().quit()))
	return box


func _build_settings_box() -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	box.add_child(_title("SETTINGS"))

	var display := OptionButton.new()
	display.add_item("Borderless Fullscreen", Settings.DISPLAY_BORDERLESS)
	display.add_item("Windowed", Settings.DISPLAY_WINDOWED)
	display.selected = Settings.display_mode
	display.custom_minimum_size = Vector2(150, 0)
	display.add_theme_font_size_override("font_size", 10)
	display.item_selected.connect(func(index: int) -> void:
		Settings.display_mode = index
		Settings.apply_all())
	box.add_child(_row("Display", display))

	var quality := OptionButton.new()
	for entry in ["Low", "Medium", "High"]:
		quality.add_item(entry)
	quality.selected = Settings.quality
	quality.custom_minimum_size = Vector2(150, 0)
	quality.add_theme_font_size_override("font_size", 10)
	quality.item_selected.connect(func(index: int) -> void:
		Settings.quality = index
		Settings.apply_all())
	box.add_child(_row("Graphics", quality))

	var fps_row := HBoxContainer.new()
	fps_row.add_theme_constant_override("separation", 6)
	var slider := HSlider.new()
	slider.min_value = 0
	slider.max_value = 240
	slider.step = 10
	slider.value = Settings.max_fps
	slider.custom_minimum_size = Vector2(110, 14)
	slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_fps_value_label = Label.new()
	_fps_value_label.add_theme_font_size_override("font_size", 10)
	_fps_value_label.custom_minimum_size = Vector2(56, 0)
	_fps_value_label.text = _fps_cap_text(Settings.max_fps)
	slider.value_changed.connect(func(value: float) -> void:
		Settings.max_fps = int(value)
		_fps_value_label.text = _fps_cap_text(Settings.max_fps)
		Settings.apply_all())
	fps_row.add_child(slider)
	fps_row.add_child(_fps_value_label)
	box.add_child(_row("FPS Cap", fps_row))

	var vsync := CheckBox.new()
	vsync.button_pressed = Settings.vsync
	vsync.add_theme_font_size_override("font_size", 10)
	vsync.toggled.connect(func(pressed: bool) -> void:
		Settings.vsync = pressed
		Settings.apply_all())
	box.add_child(_row("VSync", vsync))

	var show_fps := CheckBox.new()
	show_fps.button_pressed = Settings.show_fps
	show_fps.add_theme_font_size_override("font_size", 10)
	show_fps.toggled.connect(func(pressed: bool) -> void:
		Settings.show_fps = pressed
		Settings.apply_all())
	box.add_child(_row("Show FPS", show_fps))

	box.add_child(_button("Back", _show_main))
	return box


func _fps_cap_text(cap: int) -> String:
	return "Uncapped" if cap == 0 else str(cap)
