class_name MapView
extends CanvasLayer
## The M-key map, rebuilt (user: make it like a senior AAA dev would).
## WORLD view: the cordon — transit as a live thumbnail cut from the real
## baked district, three sealed corridors under question marks. DISTRICT
## view: the WHOLE playable district fits on screen the moment it opens —
## roads, color-true woods, buildings, the barricade ring, every POI
## named on the map — plus a live "me" marker that tracks the player in
## realtime, drag-pan, cursor-anchored wheel zoom, hover blurbs, and the
## clock/weather bar. The clickable tiles are REAL buttons now — the old
## unhandled-input hit test was eaten by the panel and clicking transit
## did nothing (user report).

const ZOOMS := [2, 3, 4, 5, 6, 8]
const TOOLTIP_DELAY := 0.5
const LABEL_BG := Color(0.035, 0.039, 0.078, 0.72)

var _player: Player
var _environment: Node
var _floor_layer: TileMapLayer
var _map_tex: ImageTexture
var _pois: Array[Dictionary] = []     # {name, rect (cells), blurb, label}
var _font: Font
var _font_size := 8

var _mode := "world"                  # remembered across open/close
var _panel: PanelContainer
var _canvas: Control
var _world_root: Control
var _transit_root: Control
var _status: Label
var _hint: Label
var _tooltip: PanelContainer
var _tooltip_label: Label
var _zoom_index := 0                  # ZOOMS[0] shows the whole district
var _pan := Vector2.ZERO
var _recenter := false                # centering waits for real layout
var _dragging := false
var _hover_key := ""
var _hover_time := 0.0
var _time_accum := 0.0
var _world_tiles: Array[Dictionary] = []   # {control, blurb}


func setup(info: Dictionary, player: Player, environment: Node,
		floor_layer: TileMapLayer) -> void:
	_player = player
	_environment = environment
	_floor_layer = floor_layer
	var map_image: Image = info["map_image"]
	_map_tex = ImageTexture.create_from_image(map_image)
	var theme := UITheme.get_theme()
	_font = theme.default_font
	if theme.has_default_font_size():
		_font_size = theme.default_font_size
	_build_poi_list(info)
	layer = 75
	visible = false
	_build_ui()


func _playable() -> Rect2:
	var inset := float(WorldBuilder.BARRIER_INSET)
	return Rect2(inset, inset,
		float(WorldBuilder.MAP_W) - inset * 2.0,
		float(WorldBuilder.MAP_H) - inset * 2.0)


func _build_poi_list(info: Dictionary) -> void:
	var blurbs := {
		"town": "the town - packed houses, some with a second floor",
		"forest": "the woods - dense cover and shedding oaks",
		"warehouse": "the warehouses - racks and freight worth taking",
		"school": "the school - classrooms over a playground",
		"playground": "the playground - swings, slide, sandbox",
		"court": "the courtyard - the town square and its dry fountain",
		"trainyard": "the trainyard - boxcars and rails going nowhere",
		"depot": "the bus depot - the last buses, some pried open",
		"comms": "the comms relay - a mast still blinking at nobody",
		"gallery": "the gallery - fresh paint on old walls",
		"scrapyard": "the scrapyard - wrecks, machines, and one crane",
		"safehouse": "home base - you wake up here every raid",
	}
	var poi: Dictionary = info.get("poi", {})
	for key in poi:
		if key == "rail_row":
			continue
		var r: Array = poi[key]
		if r.size() < 4 or int(r[2]) <= 0:
			continue
		_pois.append({"name": key,
			"rect": Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
			"blurb": blurbs.get(key, key), "label": true})
	var zones: Dictionary = info.get("zones", {})
	for zone_name in ["town", "forest", "warehouse", "trainyard"]:
		for r in (zones.get(zone_name, []) as Array):
			_pois.append({"name": zone_name,
				"rect": Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
				"blurb": blurbs.get(zone_name, zone_name), "label": true})


func _build_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	# near-fullscreen window: the map deserves the screen, not a postcard
	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.offset_left = 10
	_panel.offset_top = 10
	_panel.offset_right = -10
	_panel.offset_bottom = -10
	root.add_child(_panel)

	var stack := Control.new()
	stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	stack.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel.add_child(stack)

	# ---- the world view -------------------------------------------------
	_world_root = Control.new()
	_world_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	stack.add_child(_world_root)
	var world_title := Label.new()
	world_title.text = "the cordon"
	world_title.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
	world_title.position = Vector2(14, 8)
	_world_root.add_child(world_title)
	var world_sub := Label.new()
	world_sub.text = "one city. sealed. only one district answers."
	world_sub.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	world_sub.position = Vector2(14, 22)
	_world_root.add_child(world_sub)
	# the way out, always on screen: there was NO way to know how to
	# leave this window (user report — esc was opening settings)
	var world_close := Label.new()
	world_close.text = "press m to close"
	world_close.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	world_close.offset_left = -180
	world_close.offset_top = -22
	world_close.offset_right = -12
	world_close.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	world_close.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	world_close.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_world_root.add_child(world_close)
	# the tile board self-centers whatever the window aspect turns the
	# UI space into (expand-aspect means it is NOT always 640x360)
	var board := Control.new()
	board.custom_minimum_size = Vector2(560, 330)
	board.set_anchors_preset(Control.PRESET_CENTER)
	board.grow_horizontal = Control.GROW_DIRECTION_BOTH
	board.grow_vertical = Control.GROW_DIRECTION_BOTH
	board.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_world_root.add_child(board)

	# transit: a REAL button showing the real district, cut from the bake
	var thumb_tex := AtlasTexture.new()
	thumb_tex.atlas = _map_tex
	var crop := _playable().grow(6.0)
	thumb_tex.region = crop
	var frame := PanelContainer.new()
	frame.position = Vector2(218, 86)
	board.add_child(frame)
	var transit_btn := TextureButton.new()
	transit_btn.texture_normal = thumb_tex
	transit_btn.ignore_texture_size = true
	transit_btn.stretch_mode = TextureButton.STRETCH_SCALE
	transit_btn.custom_minimum_size = Vector2(124, 124)
	transit_btn.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	transit_btn.pressed.connect(func() -> void: _set_mode("transit"))
	frame.add_child(transit_btn)
	var transit_tag := Label.new()
	transit_tag.text = "transit - open"
	transit_tag.position = Vector2(234, 220)
	transit_tag.add_theme_color_override("font_color", UITheme.TEXT)
	board.add_child(transit_tag)
	_world_tiles.append({"control": transit_btn,
		"blurb": "transit - the sealed district you raid. click it."})

	var sealed := [
		{"pos": Vector2(52, 56), "size": Vector2(84, 84),
			"blurb": "??? - the wardens keep this corridor shut"},
		{"pos": Vector2(424, 56), "size": Vector2(84, 84),
			"blurb": "??? - the wardens keep this corridor shut"},
		{"pos": Vector2(238, 252), "size": Vector2(84, 56),
			"blurb": "??? - nothing broadcasts from there anymore"},
	]
	for tile in sealed:
		var box := PanelContainer.new()
		box.position = tile["pos"]
		box.custom_minimum_size = tile["size"]
		box.mouse_filter = Control.MOUSE_FILTER_PASS
		board.add_child(box)
		var q := Label.new()
		q.text = "?"
		q.set_anchors_preset(Control.PRESET_CENTER)
		q.grow_horizontal = Control.GROW_DIRECTION_BOTH
		q.grow_vertical = Control.GROW_DIRECTION_BOTH
		q.add_theme_color_override("font_color", UITheme.TEXT_DIM)
		box.add_child(q)
		_world_tiles.append({"control": box, "blurb": tile["blurb"]})

	# ---- the district view ----------------------------------------------
	_transit_root = Control.new()
	_transit_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_transit_root.visible = false
	stack.add_child(_transit_root)
	_canvas = Control.new()
	_canvas.set_anchors_preset(Control.PRESET_FULL_RECT)
	_canvas.clip_contents = true
	_canvas.mouse_filter = Control.MOUSE_FILTER_STOP
	_canvas.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_canvas.draw.connect(_draw_transit)
	_canvas.gui_input.connect(_on_canvas_input)
	_transit_root.add_child(_canvas)
	var back := Button.new()
	back.text = "back"
	back.position = Vector2(10, 8)
	back.custom_minimum_size = Vector2(64, 22)
	back.pressed.connect(func() -> void: _set_mode("world"))
	_transit_root.add_child(back)
	var district_tag := Label.new()
	district_tag.text = "district: transit"
	district_tag.position = Vector2(84, 13)
	district_tag.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	district_tag.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_transit_root.add_child(district_tag)
	_status = Label.new()
	_status.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_status.offset_left = 12
	_status.offset_top = -22
	_status.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_transit_root.add_child(_status)
	_hint = Label.new()
	_hint.text = "drag to pan  -  wheel to zoom  -  press m to close"
	_hint.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	_hint.offset_left = -260
	_hint.offset_top = -22
	_hint.offset_right = -12
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_hint.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_transit_root.add_child(_hint)

	# ---- shared tooltip --------------------------------------------------
	_tooltip = PanelContainer.new()
	_tooltip.visible = false
	_tooltip_label = Label.new()
	_tooltip_label.add_theme_color_override("font_color", UITheme.TEXT)
	_tooltip.add_child(_tooltip_label)
	root.add_child(_tooltip)


func _set_mode(mode: String) -> void:
	_mode = mode
	_world_root.visible = mode == "world"
	_transit_root.visible = mode == "transit"
	_hover_key = ""
	_tooltip.visible = false
	if mode == "transit":
		_recenter = true
	_canvas.queue_redraw()


func _center_view() -> void:
	# whole-map zooms center the PLAYABLE district; closer zooms center
	# the raider
	var zoom := float(ZOOMS[_zoom_index])
	var play := _playable()
	if play.size.x * zoom <= _canvas.size.x \
			and play.size.y * zoom <= _canvas.size.y:
		_pan = _canvas.size * 0.5 - play.get_center() * zoom
	else:
		var cell := Vector2(_floor_layer.local_to_map(_player.global_position))
		_pan = _canvas.size * 0.5 - cell * zoom
	_clamp_pan()


func _clamp_pan() -> void:
	# a map smaller than the window CENTERS; a bigger one pans within it
	var zoom := float(ZOOMS[_zoom_index])
	var span := 256.0 * zoom
	if span <= _canvas.size.x:
		_pan.x = (_canvas.size.x - span) * 0.5
	else:
		_pan.x = clampf(_pan.x, _canvas.size.x - span, 0.0)
	if span <= _canvas.size.y:
		# keep the PLAYABLE middle centered vertically, not the whole image
		_pan.y = (_canvas.size.y - span) * 0.5
	else:
		_pan.y = clampf(_pan.y, _canvas.size.y - span, 0.0)


func toggle() -> void:
	set_open(not visible)


func set_open(open: bool) -> void:
	visible = open
	if open:
		Ui.open(&"map")
		if _mode == "transit":
			_recenter = true
	else:
		Ui.close(&"map")
	_tooltip.visible = false
	_hover_key = ""
	_dragging = false


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		# escape closes the map instead of opening the pause menu behind
		# it (user report) — the window on top owns the key
		get_viewport().set_input_as_handled()
		set_open(false)
		return
	if not event.is_action_pressed("map") or _player == null or _player.dead:
		return
	if not visible and Ui.any_open():
		return                      # another window owns the screen
	get_viewport().set_input_as_handled()
	toggle()


func _on_canvas_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_dragging = mb.pressed
			_canvas.accept_event()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_step_zoom(1)
			_canvas.accept_event()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_step_zoom(-1)
			_canvas.accept_event()
	elif event is InputEventMouseMotion and _dragging:
		_pan += (event as InputEventMouseMotion).relative
		_clamp_pan()
		_canvas.queue_redraw()


func _step_zoom(direction: int) -> void:
	var old_zoom := float(ZOOMS[_zoom_index])
	_zoom_index = clampi(_zoom_index + direction, 0, ZOOMS.size() - 1)
	var new_zoom := float(ZOOMS[_zoom_index])
	if old_zoom != new_zoom:
		# keep the point under the cursor put while zooming
		var mouse := _canvas.get_local_mouse_position()
		var map_at := (mouse - _pan) / old_zoom
		_pan = mouse - map_at * new_zoom
		_clamp_pan()
		_canvas.queue_redraw()


func _process(delta: float) -> void:
	if not visible:
		return
	if _player == null or _player.dead:
		set_open(false)     # dying with the map up must not wedge it open
		return
	_time_accum += delta
	if _mode == "transit":
		_canvas.queue_redraw()          # live markers move in realtime
		var t: float = float(_environment.get("day_time"))
		var hour := int(t * 24.0)
		var minute := int(fmod(t * 24.0, 1.0) * 60.0)
		var rain: float = float(_environment.get("rain_intensity"))
		var weather := "clear"
		if rain > 0.65:
			weather = "storming"
		elif rain > 0.1:
			weather = "raining"
		elif t >= 0.10 and t <= 0.38:
			weather = "morning mist"
		_status.text = "time %02d:%02d   -   %s" % [hour, minute, weather]
	_update_tooltip(delta)


func _update_tooltip(delta: float) -> void:
	var key := ""
	var blurb := ""
	var mouse_global := get_viewport().get_mouse_position()
	if _mode == "world":
		for tile in _world_tiles:
			var control := tile["control"] as Control
			if control.get_global_rect().has_point(mouse_global):
				key = str(tile["blurb"])
				blurb = tile["blurb"]
				break
	else:
		var zoom := float(ZOOMS[_zoom_index])
		var mouse := _canvas.get_local_mouse_position()
		if Rect2(Vector2.ZERO, _canvas.size).has_point(mouse):
			var cell := (mouse - _pan) / zoom
			for poi in _pois:
				if (poi["rect"] as Rect2).has_point(cell):
					key = str(poi["name"]) + str(poi["rect"])
					blurb = poi["blurb"]
					break
	if key != _hover_key:
		_hover_key = key
		_hover_time = 0.0
		_tooltip.visible = false
		return
	if key == "":
		return
	_hover_time += delta
	if _hover_time >= TOOLTIP_DELAY:
		_tooltip_label.text = blurb
		_tooltip.visible = true
		var at := mouse_global + Vector2(14.0, 16.0)
		var view := Vector2(get_viewport().get_visible_rect().size)
		at.x = clampf(at.x, 4.0, view.x - _tooltip.size.x - 4.0)
		at.y = clampf(at.y, 4.0, view.y - _tooltip.size.y - 4.0)
		_tooltip.position = at.round()


func _draw_transit() -> void:
	# centering DEFERS to the first real draw: at _set_mode time the
	# layout hasn't flowed and the canvas reports zero size (the map once
	# opened panned to nowhere because of it)
	if _recenter and _canvas.size.x > 100.0:
		_recenter = false
		# open at the LARGEST whole zoom that still fits the district —
		# the map should fill the window, not float in it
		var play := _playable()
		_zoom_index = 0
		for zi in ZOOMS.size():
			if play.size.x * ZOOMS[zi] <= _canvas.size.x \
					and play.size.y * ZOOMS[zi] <= _canvas.size.y:
				_zoom_index = zi
		_center_view()
	var zoom := float(ZOOMS[_zoom_index])
	_canvas.draw_texture_rect(_map_tex, Rect2(_pan, Vector2(256, 256) * zoom),
		false)
	# POI names ON the map (user: "where all the pois are") — small type
	# with a dark backing; crowded labels yield to whoever drew first
	var drawn: Array[Rect2] = []
	for poi in _pois:
		if not bool(poi["label"]):
			continue
		var text := str(poi["name"])
		var center: Vector2 = (poi["rect"] as Rect2).get_center() * zoom + _pan
		var w := _font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1,
			_font_size).x
		var pos := (center + Vector2(-w * 0.5, float(_font_size) * 0.5 - 1.0)).round()
		var bg := Rect2(pos + Vector2(-2.0, -float(_font_size)),
			Vector2(w + 4.0, float(_font_size) + 3.0))
		var clash := false
		for r in drawn:
			if r.intersects(bg):
				clash = true
				break
		if clash:
			continue
		drawn.append(bg)
		var col := Color("c7cfcc") if text == "safehouse" else Color("a8b5b2")
		_canvas.draw_rect(bg, LABEL_BG)
		_canvas.draw_string(_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1,
			_font_size, col)
	# live car markers (the driveable ones wander)
	for node in get_tree().get_nodes_in_group("cars"):
		var car_cell := Vector2(_floor_layer.local_to_map(
			(node as Node2D).global_position)) + Vector2(0.5, 0.5)
		_canvas.draw_rect(Rect2(_pan + car_cell * zoom - Vector2(1, 1),
			Vector2(2, 2)), Color("de9e41"))
	# the raider: a pulsing marker that says exactly who it is
	var cell := Vector2(_floor_layer.local_to_map(_player.global_position)) \
		+ Vector2(0.5, 0.5)
	var ppos := (_pan + cell * zoom).round()
	var pulse := 0.7 + 0.3 * sin(_time_accum * 5.0)
	_canvas.draw_rect(Rect2(ppos - Vector2(3, 3), Vector2(6, 6)),
		Color(0.035, 0.039, 0.078, 0.9))
	_canvas.draw_rect(Rect2(ppos - Vector2(2, 2), Vector2(4, 4)),
		Color(0.92, 0.93, 0.91, pulse))
	var me_w := _font.get_string_size("me", HORIZONTAL_ALIGNMENT_LEFT, -1,
		_font_size).x
	var me_pos := (ppos + Vector2(-me_w * 0.5, -6.0)).round()
	_canvas.draw_rect(Rect2(me_pos + Vector2(-2.0, -float(_font_size)),
		Vector2(me_w + 4.0, float(_font_size) + 3.0)), LABEL_BG)
	_canvas.draw_string(_font, me_pos, "me", HORIZONTAL_ALIGNMENT_LEFT, -1,
		_font_size, UITheme.TEXT_BRIGHT)
