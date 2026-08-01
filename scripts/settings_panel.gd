class_name SettingsPanel
extends PanelContainer
## Shared settings UI, used by both the pause menu and the main menu.
## Cycle-buttons instead of OptionButtons and ON/OFF toggles instead of
## CheckBoxes: text-only controls stay pixel-crisp with the bitmap font.

signal closed
signal keybinds_requested

var _display_btn: Button
var _fps_value: Label
var _fps_slider: HSlider


func _ready() -> void:
	theme = UITheme.get_theme()
	# fixed width with headroom: value text changes (e.g. "synced (240hz)")
	# must never resize the panel
	custom_minimum_size = Vector2(272, 0)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 7)
	add_child(box)

	var title := Label.new()
	title.text = "SETTINGS"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)
	box.add_child(_spacer(2))

	_display_btn = _cycle_button(["BORDERLESS FULLSCREEN", "WINDOWED"],
		func() -> int: return Settings.display_mode,
		func(index: int) -> void:
			Settings.display_mode = index
			Settings.apply_all())
	box.add_child(_row("DISPLAY", _display_btn))

	var res_labels: Array[String] = []
	for i in Settings.RESOLUTIONS.size():
		res_labels.append(Settings.resolution_label(i))
	box.add_child(_row("RESOLUTION", _cycle_button(res_labels,
		func() -> int: return Settings.resolution,
		func(index: int) -> void:
			Settings.resolution = index
			if index != 0 and Settings.display_mode == Settings.DISPLAY_BORDERLESS:
				# picking an explicit size means windowed; fullscreen is desktop-size
				Settings.display_mode = Settings.DISPLAY_WINDOWED
				_display_btn.text = "WINDOWED"
			Settings.apply_all())))

	box.add_child(_row("GRAPHICS", _cycle_button(["LOW", "MEDIUM", "HIGH"],
		func() -> int: return Settings.quality,
		func(index: int) -> void:
			Settings.quality = index
			Settings.apply_all())))

	var fps_box := HBoxContainer.new()
	fps_box.add_theme_constant_override("separation", 6)
	_fps_slider = HSlider.new()
	_fps_slider.min_value = 0
	_fps_slider.max_value = 240
	_fps_slider.step = 10
	_fps_slider.value = Settings.max_fps
	_fps_slider.custom_minimum_size = Vector2(90, 12)
	_fps_slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_fps_value = Label.new()
	_fps_value.custom_minimum_size = Vector2(86, 0)
	_fps_slider.value_changed.connect(func(value: float) -> void:
		Settings.max_fps = int(value)
		_update_fps_row()
		Settings.apply_all())
	fps_box.add_child(_fps_slider)
	fps_box.add_child(_fps_value)
	box.add_child(_row("FPS CAP", fps_box))

	box.add_child(_row("VSYNC", _toggle_button(
		func() -> bool: return Settings.vsync,
		func(on: bool) -> void:
			Settings.vsync = on
			_update_fps_row()
			Settings.apply_all())))
	_update_fps_row()

	box.add_child(_row("SHOW FPS", _toggle_button(
		func() -> bool: return Settings.show_fps,
		func(on: bool) -> void:
			Settings.show_fps = on
			Settings.apply_all())))

	box.add_child(_spacer(2))
	var keybinds := Button.new()
	keybinds.text = "keybinds"
	keybinds.pressed.connect(func() -> void: keybinds_requested.emit())
	box.add_child(keybinds)

	var back := Button.new()
	back.text = "< back"
	back.pressed.connect(func() -> void: closed.emit())
	box.add_child(back)


func focus_first() -> void:
	_display_btn.grab_focus()


func _spacer(height: int) -> Control:
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, height)
	return spacer


func _row(label_text: String, control: Control) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size = Vector2(72, 0)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	row.add_child(label)
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(control)
	return row


func _cycle_button(options: Array, get_index: Callable, set_index: Callable) -> Button:
	var button := Button.new()
	button.text = str(options[get_index.call()])
	button.pressed.connect(func() -> void:
		var next: int = (int(get_index.call()) + 1) % options.size()
		set_index.call(next)
		button.text = str(options[next]))
	return button


func _toggle_button(get_on: Callable, set_on: Callable) -> Button:
	var button := Button.new()
	button.text = "ON" if get_on.call() else "OFF"
	button.pressed.connect(func() -> void:
		var now: bool = not get_on.call()
		set_on.call(now)
		button.text = "ON" if now else "OFF")
	return button


func _update_fps_row() -> void:
	# with vsync on, the display drives the frame rate — the cap is moot
	_fps_slider.editable = not Settings.vsync
	if Settings.vsync:
		_fps_value.text = "synced (%dhz)" % roundi(DisplayServer.screen_get_refresh_rate())
		_fps_value.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	else:
		_fps_value.text = _fps_cap_text(Settings.max_fps)
		_fps_value.add_theme_color_override("font_color", UITheme.TEXT)


func _fps_cap_text(cap: int) -> String:
	return "uncapped" if cap == 0 else str(cap)
