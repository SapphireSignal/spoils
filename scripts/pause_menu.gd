class_name PauseMenu
extends CanvasLayer
## Esc pause menu. Main panel, in order: RESUME / SETTINGS / ABANDON RAID /
## QUIT TO DESKTOP. "abandon raid" is not a free exit — it hands you the same
## debrief dying does (main.gd:abandon_raid). This list said three buttons
## and omitted it, which is the one with a scoring side-effect.
## Settings live in the shared SettingsPanel. Everything renders with the
## bitmap pixel font via UITheme — no vector-font blur.

var _root: Control
var _dim: ColorRect
var _main_panel: PanelContainer
var _resume_btn: Button
var _settings: SettingsPanel
var _keybinds: KeybindsPanel
var _volume: VolumePanel


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
	title.text = "raid paused"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)
	var hint := Label.new()
	hint.text = "the timer does not care."
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	box.add_child(hint)
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(150, 3)
	box.add_child(spacer)
	_resume_btn = _button(box, "resume", close)
	_button(box, "settings", _show_settings)
	# leaving mid-raid is not a free exit any more (user call): the raid
	# owner hands you the same debrief dying would. Outside a raid (or if
	# something went wrong building it) this still just leaves.
	_button(box, "abandon raid", func() -> void:
		close()
		var raid := get_tree().current_scene
		if raid != null and raid.has_method("abandon_raid"):
			raid.call("abandon_raid")
		else:
			get_tree().paused = false
			get_tree().change_scene_to_file("res://scenes/menu.tscn"))
	_button(box, "quit to desktop", func() -> void: get_tree().quit())
	_main_panel.add_child(box)
	center.add_child(_main_panel)

	_settings = SettingsPanel.new()
	_settings.visible = false
	_settings.closed.connect(_show_main)
	_settings.keybinds_requested.connect(_show_keybinds)
	_settings.volume_requested.connect(_show_volume)
	center.add_child(_settings)

	_keybinds = KeybindsPanel.new()
	_keybinds.visible = false
	_keybinds.closed.connect(_show_settings)
	center.add_child(_keybinds)

	_volume = VolumePanel.new()
	_volume.visible = false
	_volume.closed.connect(_show_settings)
	center.add_child(_volume)

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
	# another window owns the screen: it gets the escape, not us (esc used
	# to open the pause menu straight through the open map — user report)
	if not visible and Ui.any_open():
		return
	get_viewport().set_input_as_handled()
	if not visible:
		open()
	elif _keybinds.visible or _volume.visible:
		_show_settings()
	elif _settings.visible:
		_show_main()
	else:
		close()


func open() -> void:
	visible = true
	get_tree().paused = true
	Ui.open(&"pause")
	_show_main()


func open_settings() -> void:
	open()
	_show_settings()


func open_volume() -> void:
	open()
	_show_volume()


func close() -> void:
	visible = false
	get_tree().paused = false
	Ui.close(&"pause")


func _show_main() -> void:
	_main_panel.visible = true
	_settings.visible = false
	_keybinds.visible = false
	_volume.visible = false
	_resume_btn.grab_focus()


func _show_settings() -> void:
	_main_panel.visible = false
	_settings.visible = true
	_keybinds.visible = false
	_volume.visible = false
	_settings.focus_first()


func _show_keybinds() -> void:
	_main_panel.visible = false
	_settings.visible = false
	_keybinds.visible = true


func _show_volume() -> void:
	_main_panel.visible = false
	_settings.visible = false
	_volume.visible = true
