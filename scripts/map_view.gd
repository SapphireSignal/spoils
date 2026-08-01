class_name MapView
extends CanvasLayer
## The M-key map. First open shows the WORLD view: transit in the middle,
## three sealed districts around it with question marks. Clicking transit
## swaps to the DISTRICT view: the real baked map, the POIs, live player
## and car markers, drag-pan, wheel zoom, hover tooltips (0.5 s), the
## in-game clock and the weather. M closes it; the window remembers which
## view you were on for the rest of the raid.

const ZOOMS := [2, 3, 4, 5, 6, 8]
const TOOLTIP_DELAY := 0.5

var _player: Player
var _environment: Node
var _floor_layer: TileMapLayer
var _map_tex: ImageTexture
var _pois: Array[Dictionary] = []     # {name, rect (cells), blurb}

var _mode := "world"                  # remembered across open/close
var _panel: PanelContainer
var _canvas: Control
var _world_root: Control
var _transit_root: Control
var _status: Label
var _tooltip: PanelContainer
var _tooltip_label: Label
var _zoom_index := 1
var _pan := Vector2.ZERO
var _dragging := false
var _hover_key := ""
var _hover_time := 0.0
var _time_accum := 0.0
var _world_tiles: Array[Dictionary] = []   # {rect (screen), name, blurb}


func setup(info: Dictionary, player: Player, environment: Node,
		floor_layer: TileMapLayer) -> void:
	_player = player
	_environment = environment
	_floor_layer = floor_layer
	var map_image: Image = info["map_image"]
	_map_tex = ImageTexture.create_from_image(map_image)
	_build_poi_list(info)
	layer = 75
	visible = false
	_build_ui()


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
			"blurb": blurbs.get(key, key)})
	var zones: Dictionary = info.get("zones", {})
	for zone_name in ["town", "forest", "warehouse", "trainyard"]:
		for r in (zones.get(zone_name, []) as Array):
			_pois.append({"name": zone_name,
				"rect": Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
				"blurb": blurbs.get(zone_name, zone_name)})


func _build_ui() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.custom_minimum_size = Vector2(560, 318)
	_panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	root.add_child(_panel)

	var stack := Control.new()
	stack.custom_minimum_size = Vector2(552, 310)
	_panel.add_child(stack)

	# ---- the world view -------------------------------------------------
	_world_root = Control.new()
	_world_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	stack.add_child(_world_root)
	var world_title := Label.new()
	world_title.text = "the cordon"
	world_title.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
	world_title.position = Vector2(12, 8)
	_world_root.add_child(world_title)
	_world_tiles = [
		{"name": "transit", "pos": Vector2(226, 105), "size": Vector2(100, 100),
			"blurb": "transit - the sealed district you raid", "open": true},
		{"name": "???", "pos": Vector2(86, 55), "size": Vector2(72, 72),
			"blurb": "??? - the wardens keep this corridor shut", "open": false},
		{"name": "???", "pos": Vector2(394, 55), "size": Vector2(72, 72),
			"blurb": "??? - the wardens keep this corridor shut", "open": false},
		{"name": "???", "pos": Vector2(240, 226), "size": Vector2(72, 60),
			"blurb": "??? - nothing broadcasts from there anymore", "open": false},
	]
	for tile in _world_tiles:
		var box := PanelContainer.new()
		box.position = tile["pos"]
		box.custom_minimum_size = tile["size"]
		_world_root.add_child(box)
		tile["rect"] = Rect2(tile["pos"] as Vector2, tile["size"] as Vector2)
		if tile["open"]:
			var thumb := TextureRect.new()
			thumb.texture = load("res://art/gen/menu_map_transit.png")
			thumb.stretch_mode = TextureRect.STRETCH_SCALE
			thumb.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			thumb.custom_minimum_size = tile["size"]
			thumb.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			box.add_child(thumb)
			var name_tag := Label.new()
			name_tag.text = "transit"
			name_tag.position = Vector2((tile["pos"] as Vector2).x + 30,
				(tile["pos"] as Vector2).y + (tile["size"] as Vector2).y + 4)
			name_tag.add_theme_color_override("font_color", UITheme.TEXT)
			_world_root.add_child(name_tag)
		else:
			var q := Label.new()
			q.text = "?"
			q.set_anchors_preset(Control.PRESET_CENTER)
			q.grow_horizontal = Control.GROW_DIRECTION_BOTH
			q.grow_vertical = Control.GROW_DIRECTION_BOTH
			q.add_theme_color_override("font_color", UITheme.TEXT_DIM)
			box.add_child(q)

	# ---- the transit view -----------------------------------------------
	_transit_root = Control.new()
	_transit_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_transit_root.visible = false
	stack.add_child(_transit_root)
	_canvas = Control.new()
	_canvas.set_anchors_preset(Control.PRESET_FULL_RECT)
	_canvas.clip_contents = true
	_canvas.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_canvas.draw.connect(_draw_transit)
	_transit_root.add_child(_canvas)
	var back := Button.new()
	back.text = "back"
	back.position = Vector2(10, 8)
	back.custom_minimum_size = Vector2(64, 22)
	back.pressed.connect(func() -> void: _set_mode("world"))
	_transit_root.add_child(back)
	_status = Label.new()
	_status.position = Vector2(12, 288)
	_status.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_transit_root.add_child(_status)

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
		_center_on_player()
	_canvas.queue_redraw()


func _center_on_player() -> void:
	var zoom := float(ZOOMS[_zoom_index])
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
		_pan.y = (_canvas.size.y - span) * 0.5
	else:
		_pan.y = clampf(_pan.y, _canvas.size.y - span, 0.0)


func toggle() -> void:
	visible = not visible
	if visible and _mode == "transit":
		_center_on_player()
	_tooltip.visible = false
	_hover_key = ""


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("map") and _player != null and not _player.dead:
		get_viewport().set_input_as_handled()
		toggle()
		return
	if not visible:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if _mode == "world" and mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed:
			var local := _panel.get_local_mouse_position()
			for tile in _world_tiles:
				if tile["open"] and (tile["rect"] as Rect2).has_point(local):
					get_viewport().set_input_as_handled()
					_set_mode("transit")
					return
		elif _mode == "transit":
			if mb.button_index == MOUSE_BUTTON_LEFT:
				_dragging = mb.pressed
				get_viewport().set_input_as_handled()
			elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
				_step_zoom(1)
				get_viewport().set_input_as_handled()
			elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				_step_zoom(-1)
				get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _mode == "transit" and _dragging:
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
	_time_accum += delta
	if _mode == "transit":
		_canvas.queue_redraw()          # live markers
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
	if _mode == "world":
		var local := _panel.get_local_mouse_position()
		for tile in _world_tiles:
			if (tile["rect"] as Rect2).has_point(local):
				key = str(tile["name"]) + str(tile["rect"])
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
		var at := _panel.position + _panel.get_local_mouse_position() \
			+ Vector2(14.0, 16.0)
		var view := Vector2(get_viewport().get_visible_rect().size)
		at.x = clampf(at.x, 4.0, view.x - _tooltip.size.x - 4.0)
		at.y = clampf(at.y, 4.0, view.y - _tooltip.size.y - 4.0)
		_tooltip.position = at.round()


func _draw_transit() -> void:
	var zoom := float(ZOOMS[_zoom_index])
	_canvas.draw_texture_rect(_map_tex, Rect2(_pan, Vector2(256, 256) * zoom),
		false)
	# live car markers (driveable ones move around)
	for node in get_tree().get_nodes_in_group("cars"):
		var car_cell := Vector2(_floor_layer.local_to_map((node as Node2D).global_position))
		_canvas.draw_rect(Rect2(_pan + car_cell * zoom, Vector2(zoom, zoom) * 0.9),
			Color("de9e41"))
	# the player: a pulsing pale marker
	var cell := Vector2(_floor_layer.local_to_map(_player.global_position))
	var pulse := 0.7 + 0.3 * sin(_time_accum * 5.0)
	var marker_size := Vector2(zoom, zoom) * 1.4
	_canvas.draw_rect(Rect2(_pan + cell * zoom - marker_size * 0.2, marker_size),
		Color(0.92, 0.93, 0.91, pulse))
