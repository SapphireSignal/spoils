class_name PauseMenu
extends CanvasLayer
## Esc pause menu. Main panel: RESUME / SETTINGS / QUIT TO DESKTOP.
## Settings live in the shared SettingsPanel. Everything renders with the
## bitmap pixel font via UITheme — no vector-font blur.

var _root: Control
var _dim: ColorRect
var _main_panel: PanelContainer
var _resume_btn: Button
var _settings: SettingsPanel


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 50

	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = UITheme.get_theme()
	add_child(_root)

	_dim = ColorRect.new()
	_dim.color = Color(0.035, 0.039, 0.078, 0.62)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(_dim)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)

	_main_panel = PanelContainer.new()
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	var title := Label.new()
	title.text = "RAID PAUSED"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)
	var hint := Label.new()
	hint.text = "THE TIMER DOES NOT CARE."
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	box.add_child(hint)
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(150, 3)
	box.add_child(spacer)
	_resume_btn = _button(box, "RESUME", close)
	_button(box, "SETTINGS", _show_settings)
	_button(box, "QUIT TO DESKTOP", func() -> void: get_tree().quit())
	_main_panel.add_child(box)
	center.add_child(_main_panel)

	_settings = SettingsPanel.new()
	_settings.visible = false
	_settings.closed.connect(_show_main)
	center.add_child(_settings)

	visible = false
	add_to_group("pause_menu")


func _button(parent: Container, text: String, handler: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(150, 0)
	button.pressed.connect(handler)
	parent.add_child(button)
	return button


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed("ui_cancel"):
		return
	get_viewport().set_input_as_handled()
	if not visible:
		open()
	elif _settings.visible:
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
	_main_panel.visible = true
	_settings.visible = false
	_resume_btn.grab_focus()


func _show_settings() -> void:
	_main_panel.visible = false
	_settings.visible = true
	_settings.focus_first()
