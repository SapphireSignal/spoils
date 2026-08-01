class_name KeybindsPanel
extends PanelContainer
## Rebinding screen (opened from settings). Click an action's key, press the
## new key. Esc cancels a listen; "reset to defaults" restores everything.
## Binds persist via the Settings autoload.

signal closed

var _listening_action := ""
var _bind_buttons: Dictionary = {}  # action -> Button


func _ready() -> void:
	theme = UITheme.get_theme()
	process_mode = Node.PROCESS_MODE_ALWAYS
	custom_minimum_size = Vector2(250, 0)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	add_child(box)

	var title := Label.new()
	title.text = "keybinds"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)

	var hint := Label.new()
	hint.text = "click a key, then press the new one"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	box.add_child(hint)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(240, 190)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 4)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for action in Settings.BIND_ACTIONS:
		list.add_child(_bind_row(action))
	scroll.add_child(list)
	box.add_child(scroll)

	var reset := Button.new()
	reset.text = "reset to defaults"
	reset.pressed.connect(func() -> void:
		_cancel_listen()
		Settings.reset_binds()
		_refresh_all())
	box.add_child(reset)

	var back := Button.new()
	back.text = "< back"
	back.pressed.connect(func() -> void:
		_cancel_listen()
		closed.emit())
	box.add_child(back)


func _bind_row(action: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var label := Label.new()
	label.text = Settings.BIND_LABELS[action]
	label.custom_minimum_size = Vector2(120, 0)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	row.add_child(label)
	var button := Button.new()
	button.text = Settings.bind_label(action)
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.pressed.connect(func() -> void: _start_listen(action))
	_bind_buttons[action] = button
	row.add_child(button)
	if action == "crouch":
		var mode := Button.new()
		mode.text = "toggle" if Settings.crouch_toggle else "hold"
		mode.custom_minimum_size = Vector2(48, 0)
		mode.pressed.connect(func() -> void:
			Settings.set_crouch_toggle(not Settings.crouch_toggle)
			mode.text = "toggle" if Settings.crouch_toggle else "hold")
		row.add_child(mode)
	return row


func _start_listen(action: String) -> void:
	_cancel_listen()
	_listening_action = action
	(_bind_buttons[action] as Button).text = "press a key..."


func _cancel_listen() -> void:
	if _listening_action != "":
		_refresh(_listening_action)
		_listening_action = ""


func _refresh(action: String) -> void:
	(_bind_buttons[action] as Button).text = Settings.bind_label(action)


func _refresh_all() -> void:
	for action in _bind_buttons:
		_refresh(action)


func _unhandled_key_input(event: InputEvent) -> void:
	if _listening_action == "" or not visible:
		return
	var key := event as InputEventKey
	if key == null or not key.pressed:
		return
	get_viewport().set_input_as_handled()
	if key.physical_keycode == KEY_ESCAPE:
		_cancel_listen()
		return
	var action := _listening_action
	_listening_action = ""
	Settings.set_bind(action, key.physical_keycode)
	_refresh(action)
	Sfx.play_press()
