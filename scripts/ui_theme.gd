class_name UITheme
extends RefCounted
## Shared UI look: the generated bitmap pixel font + Apollo-palette flat
## styleboxes. Every UI root gets the same Theme instance so all text renders
## at the font's native pixel size (crisp at any integer screen scale).

const TEXT := Color("c7cfcc")
const TEXT_BRIGHT := Color("ebede9")
const TEXT_DIM := Color("819796")
const ACCENT := Color("de9e41")
const GOOD := Color("a8ca58")
const PANEL := Color("151d28")
const PANEL_BORDER := Color("394a50")
const SHADOW := Color("090a14")

static var _theme: Theme


static func get_theme() -> Theme:
	if _theme == null:
		_theme = _build()
	return _theme


static func font() -> FontFile:
	return load("res://art/gen/spoils_font.fnt")


static func _flat(bg: Color, border: Color, margin: int = 6) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(1)
	style.set_content_margin_all(margin)
	return style


static func _build() -> Theme:
	var theme := Theme.new()
	theme.default_font = font()
	theme.default_font_size = 9

	# deep burgundy, translucent: distinct from every backdrop (the gold vault
	# AND the blue-gray scenes), which the old gray-blue wasn't
	var btn_normal := _flat(Color("411d31", 0.62), Color("752438", 0.75))
	btn_normal.content_margin_top = 5
	btn_normal.content_margin_bottom = 4
	var btn_hover := _flat(Color("752438", 0.78), Color("a53030", 0.9))
	btn_hover.content_margin_top = 5
	btn_hover.content_margin_bottom = 4
	var btn_pressed := _flat(Color("241527", 0.8), Color("752438", 0.85))
	btn_pressed.content_margin_top = 5
	btn_pressed.content_margin_bottom = 4
	# keyboard-focus marker: subtle, same family as hover
	var btn_focus := StyleBoxFlat.new()
	btn_focus.bg_color = Color(0, 0, 0, 0)
	btn_focus.border_color = Color("a53030")
	btn_focus.set_border_width_all(1)
	theme.set_stylebox("normal", "Button", btn_normal)
	theme.set_stylebox("hover", "Button", btn_hover)
	theme.set_stylebox("pressed", "Button", btn_pressed)
	theme.set_stylebox("disabled", "Button", btn_pressed)
	theme.set_stylebox("focus", "Button", btn_focus)
	theme.set_color("font_color", "Button", TEXT)
	theme.set_color("font_hover_color", "Button", TEXT_BRIGHT)
	theme.set_color("font_pressed_color", "Button", TEXT_DIM)
	theme.set_color("font_focus_color", "Button", TEXT_BRIGHT)
	theme.set_color("font_disabled_color", "Button", TEXT_DIM)

	theme.set_stylebox("panel", "PanelContainer", _flat(PANEL, PANEL_BORDER, 12))

	theme.set_color("font_color", "Label", TEXT)
	theme.set_color("font_shadow_color", "Label", SHADOW)
	theme.set_constant("shadow_offset_x", "Label", 1)
	theme.set_constant("shadow_offset_y", "Label", 1)

	var track := _flat(Color("10141f"), Color("394a50"), 0)
	track.content_margin_top = 2
	track.content_margin_bottom = 2
	var filled := _flat(Color("577277"), Color("577277"), 0)
	theme.set_stylebox("slider", "HSlider", track)
	theme.set_stylebox("grabber_area", "HSlider", filled)
	theme.set_stylebox("grabber_area_highlight", "HSlider", filled)
	var grabber: Texture2D = load("res://art/gen/ui_grabber.png")
	theme.set_icon("grabber", "HSlider", grabber)
	theme.set_icon("grabber_highlight", "HSlider", grabber)
	theme.set_icon("grabber_disabled", "HSlider", grabber)

	return theme
