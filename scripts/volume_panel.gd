class_name VolumePanel
extends PanelContainer
## Four mix sliders — master, music, sound effects, ambient (user call
## 2026-08-01). Values apply LIVE through the audio buses and persist
## with the rest of settings; player volume_db is never touched, so the
## music fades and the per-sound levels keep working underneath.

signal closed


func _ready() -> void:
	theme = UITheme.get_theme()
	custom_minimum_size = Vector2(272, 0)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 7)
	add_child(box)

	var title := Label.new()
	title.text = "VOLUME"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 2)
	box.add_child(spacer)

	box.add_child(_slider_row("MASTER", "master"))
	box.add_child(_slider_row("MUSIC", "music"))
	box.add_child(_slider_row("EFFECTS", "sfx"))
	box.add_child(_slider_row("AMBIENT", "ambient"))

	var back := Button.new()
	back.text = "< back"
	back.pressed.connect(func() -> void: closed.emit())
	box.add_child(back)


func _slider_row(label_text: String, which: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var label := Label.new()
	label.text = label_text
	label.custom_minimum_size = Vector2(72, 0)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	row.add_child(label)
	var slider := HSlider.new()
	slider.min_value = 0
	slider.max_value = 100
	slider.step = 5
	slider.value = roundf(Settings.get_volume(which) * 100.0)
	slider.custom_minimum_size = Vector2(90, 12)
	slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var value := Label.new()
	value.custom_minimum_size = Vector2(42, 0)
	value.text = "%d%%" % int(slider.value)
	slider.value_changed.connect(func(v: float) -> void:
		Settings.set_volume(which, v / 100.0)
		value.text = "%d%%" % int(v))
	row.add_child(slider)
	row.add_child(value)
	return row
