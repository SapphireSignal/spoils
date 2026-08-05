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

const TOOLTIP_DELAY := 0.5
# ---------------------------------------------------------------------------
# THE MAP'S PALETTE — a DRAWN CHART, not a screenshot and not a diagram.
#
# It was a dark blue-grey scheme of flat filled rectangles and the user's
# verdict was "its like some minecraft map". The fix is not more colours: it
# is to draw the thing the way a paper map is drawn — aged paper, sepia INK
# for every edge, pale channels for roads, hatching for woods, and a symbol
# for every place instead of a word floating on open ground.
#
# All Apollo, like everything else in the project.
# ---------------------------------------------------------------------------
const PAPER := Color("d7b594")                   # the sheet itself
const PAPER_HI := Color("e7d5b3")                # roads, paved ground
const PAPER_LO := Color("c09473")                # town blocks, a shade down
const INK := Color("341c27")                     # every edge and every glyph
const INK_SOFT := Color("4d2b32")                # secondary rules, ties
const GREEN := Color("25562e")                   # the woods, hatched
const GREEN_AUTUMN := Color("884b2b")            # turned, not bleeding
const BUILDING := Color("819796")                # civic / warehouse
const BUILDING_WARM := Color("ad7757")           # houses
const RAIL := Color("4d2b32")
const RING := Color("602c2c")                    # the wire: broken red ink
const ME := Color("a53030")                      # you. The loudest thing here.
const CAR_DOT := Color("be772b")                 # amber
const TRUCK_DOT := Color("3c5e8b")               # blue, so the two read apart
const LABEL := Color("341c27")                   # place names are ink too

var _player: Player
var _environment: Node
var _floor_layer: TileMapLayer
var _map_tex: ImageTexture
var _pois: Array[Dictionary] = []     # {name, rect (cells), blurb, label}
var _font: Font
var _font_size := 8
# a SECOND, much smaller cut for the vehicle dots (user: "way smaller").
# The main font is a bitmap at one size — asking it for a smaller size
# resamples the glyphs and they blur, so the tiny text is its own font,
# drawn at 3px x-height.
var _tiny_font: Font
var _tiny_size := 6

var _mode := "world"                  # remembered across open/close
var _panel: PanelContainer
var _canvas: Control
var _markers: Control
var _vec: Dictionary = {}             # the district as shapes, not pixels
var _world_root: Control
var _transit_root: Control
var _status: Label
var _hint: Label
var _tooltip: PanelContainer
var _tooltip_label: Label
var _zoom := 3.0                      # screen px per map cell, continuous
var _pan := Vector2.ZERO
var _recenter := false                # centering waits for real layout
var _ever_centred := false            # ...and only happens once per raid
var _status_stamp := -1               # last minute shown on the clock bar
var _status_weather := ""
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
	_vec = info.get("map_vec", {})
	var theme := UITheme.get_theme()
	_font = theme.default_font
	if theme.has_default_font_size():
		_font_size = theme.default_font_size
	var tiny := load("res://art/gen/spoils_tiny.fnt")
	if tiny != null:
		_tiny_font = tiny
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
		"courtyard": "the courtyard - the town square and its dry fountain",
		"trainyard": "the trainyard - boxcars and rails going nowhere",
		"bus depot": "the bus depot - the last buses, some pried open",
		"comms": "the comms relay - a mast still blinking at nobody",
		"gallery": "the gallery - fresh paint on old walls",
		"scrapyard": "the scrapyard - wrecks, machines, and one crane",
		"safehouse": "home base - you wake up here every raid",
		"lz": "the lift - green smoke, and a bird if you can pay for it",
		"toll gate": "the toll gate - the warden sells his blind eye",
	}
	var poi: Dictionary = info.get("poi", {})
	for key in poi:
		if key == "rail_row":
			continue
		var r: Array = poi[key]
		if r.size() < 4 or int(r[2]) <= 0:
			continue
		# a PLACE gets a drawn symbol (see _draw_poi_glyph)
		_pois.append({"name": key,
			"rect": Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
			"blurb": blurbs.get(key, key), "label": true, "glyph": true})
	var zones: Dictionary = info.get("zones", {})
	for zone_name in ["town", "forest", "warehouse", "trainyard"]:
		for r in (zones.get(zone_name, []) as Array):
			# a REGION gets a name and no symbol — that is how a drawn map
			# handles an area, and a zone repeats over several rects, so a
			# symbol on each would carpet the sheet
			_pois.append({"name": zone_name,
				"rect": Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
				"blurb": blurbs.get(zone_name, zone_name), "label": true,
				"glyph": false})


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
	_canvas.draw.connect(_draw_district)
	_canvas.gui_input.connect(_on_canvas_input)
	_transit_root.add_child(_canvas)
	# markers live on their own layer: the district is heavy to draw and
	# only changes when you pan or zoom, while "me" moves every frame
	_markers = Control.new()
	_markers.set_anchors_preset(Control.PRESET_FULL_RECT)
	_markers.clip_contents = true
	_markers.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_markers.draw.connect(_draw_markers)
	_transit_root.add_child(_markers)
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
	_redraw_all()


func _redraw_all() -> void:
	_canvas.queue_redraw()
	_markers.queue_redraw()


func _center_view() -> void:
	# a whole-district view centres the district; zoomed in, centre on
	# the raider
	var play := _playable()
	if play.size.x * _zoom <= _canvas.size.x \
			and play.size.y * _zoom <= _canvas.size.y:
		_pan = _canvas.size * 0.5 - play.get_center() * _zoom
	else:
		var cell := Vector2(_floor_layer.local_to_map(_player.global_position))
		_pan = _canvas.size * 0.5 - cell * _zoom
	_clamp_pan()


func _clamp_pan() -> void:
	# clamp against the PLAYABLE district (the buffer beyond the wire is
	# nobody's business), centring it whenever it fits
	var play := _playable()
	var span := play.size * _zoom
	var origin := play.position * _zoom
	if span.x <= _canvas.size.x:
		_pan.x = (_canvas.size.x - span.x) * 0.5 - origin.x
	else:
		_pan.x = clampf(_pan.x, _canvas.size.x - span.x - origin.x, -origin.x)
	if span.y <= _canvas.size.y:
		_pan.y = (_canvas.size.y - span.y) * 0.5 - origin.y
	else:
		_pan.y = clampf(_pan.y, _canvas.size.y - span.y - origin.y, -origin.y)


func prewarm() -> void:
	## The district layer draws its ENTIRE vector plan the first time it is
	## shown — roads, blocks, every building, the groves — and that first
	## draw cost a visible hitch on the first M press (user measured a drop
	## to ~80 fps for a moment). Pay it here instead: the deploy screen is
	## an opaque layer 95 and this is layer 75, so the map can draw for
	## real behind it. Deliberately does NOT touch Ui — this is not an open.
	var remembered := _mode
	visible = true
	_set_mode("transit")
	await get_tree().process_frame   # layout flows; the canvas gets a size
	await get_tree().process_frame   # ...and the draw itself lands
	visible = false
	_set_mode(remembered)


func toggle() -> void:
	set_open(not visible)


func set_open(open: bool) -> void:
	visible = open
	if open:
		Ui.open(&"map")
		# Fit the district ONCE. After that the map stays where you left
		# it — close it half-zoomed on the trainyard and that is what you
		# get back (user). _pan and _zoom already persisted; it was this
		# unconditional recentre that threw them away every open.
		if _mode == "transit" and not _ever_centred:
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
		_redraw_all()


func _step_zoom(direction: int) -> void:
	# smooth zoom now the map is drawn, not sampled — no pixel ladder
	var play := _playable()
	var fit := minf(_canvas.size.x / (play.size.x + 8.0),
		_canvas.size.y / (play.size.y + 8.0))
	var old_zoom := _zoom
	_zoom = clampf(_zoom * (1.25 if direction > 0 else 0.8), fit, 24.0)
	if not is_equal_approx(old_zoom, _zoom):
		# keep the point under the cursor put while zooming
		var mouse := _canvas.get_local_mouse_position()
		var map_at := (mouse - _pan) / old_zoom
		_pan = mouse - map_at * _zoom
		_clamp_pan()
		_redraw_all()


func _process(delta: float) -> void:
	if not visible:
		return
	if _player == null or _player.dead:
		set_open(false)     # dying with the map up must not wedge it open
		return
	_time_accum += delta
	if _mode == "transit":
		_markers.queue_redraw()         # only the markers move each frame
		if _recenter:
			_canvas.queue_redraw()
		var t: float = float(_environment.get("day_time"))
		var hour := int(t * 24.0)
		var minute := int(fmod(t * 24.0, 1.0) * 60.0)
		var stamp := hour * 60 + minute
		# the environment names its own weather now — rain and storm are
		# different spells, and fog is one too
		var weather := str(_environment.call("weather_label"))
		# ...and say which part of the day it is, not just the clock
		var part := "night"
		if t >= 0.208 and t < 0.29:
			part = "dawn"
		elif t < 0.5:
			part = "morning"
		elif t < 0.72:
			part = "afternoon"
		elif t < 0.875:
			part = "evening"
		if stamp != _status_stamp or weather != _status_weather:
			_status_stamp = stamp
			_status_weather = weather
			_status.text = "%02d:%02d %s   -   %s" % [hour, minute, part, weather]
	_update_tooltip(delta)


func _update_tooltip(delta: float) -> void:
	var key := ""
	var blurb := ""
	var mouse_global := get_viewport().get_mouse_position()
	if _mode == "world":
		for i in _world_tiles.size():
			var control := _world_tiles[i]["control"] as Control
			if control.get_global_rect().has_point(mouse_global):
				# key on the TILE, not its text — two "???" tiles share a
				# blurb, and sliding between them kept the tooltip stuck
				key = "world_%d" % i
				blurb = _world_tiles[i]["blurb"]
				break
	else:
		var mouse := _canvas.get_local_mouse_position()
		if Rect2(Vector2.ZERO, _canvas.size).has_point(mouse):
			var cell := (mouse - _pan) / _zoom
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


func _cell_to_screen(cell: Vector2) -> Vector2:
	return _pan + cell * _zoom


func _draw_district() -> void:
	# centering DEFERS to the first real draw: at _set_mode time the
	# layout hasn't flowed and the canvas reports zero size (the map once
	# opened panned to nowhere because of it)
	if _recenter and _canvas.size.x > 100.0:
		_recenter = false
		var play := _playable()
		# fill the window: the map is the point of this screen
		_zoom = minf(_canvas.size.x / (play.size.x + 8.0),
			_canvas.size.y / (play.size.y + 8.0))
		_center_view()
	if _vec.is_empty():
		_canvas.draw_texture_rect(_map_tex,
			Rect2(_pan, Vector2(256, 256) * _zoom), false)
		return
	var z := _zoom
	var inset := float(_vec["inset"])
	var w := float((_vec["size"] as Array)[0])
	var h := float((_vec["size"] as Array)[1])

	# THE SHEET. Paper first, then a ruled ink border. Everything below is
	# drawn ON it, which is the whole difference between a chart and a
	# screenshot of the ground.
	var land := Rect2(_cell_to_screen(Vector2(inset, inset)),
		Vector2(w - inset * 2.0, h - inset * 2.0) * z)
	_canvas.draw_rect(land, PAPER)
	_canvas.draw_rect(land.grow(1.0), INK_SOFT, false, 1.0)
	# city blocks: a shade DOWN from the paper now, so the grain of the town
	# reads without any of the hollow boxes the old map drew
	for b in (_vec["blocks"] as Array):
		var br := Rect2(_cell_to_screen(Vector2(float(b[0]), float(b[1]))),
			Vector2(float(b[2]), float(b[3])) * z)
		# A TINT, not a fill. At full opacity the blocks cover almost the whole
		# sheet and the paper only survives as margins, which inverts the whole
		# look — you get brown boxes with pale gaps instead of a paper map with
		# the town shaded on it. It also buried the buildings, which are warm
		# brown themselves.
		_canvas.draw_rect(br, Color(PAPER_LO.r, PAPER_LO.g, PAPER_LO.b, 0.45))
	# THE WOODS ARE HATCHED, not blobbed — short diagonal strokes, the way a
	# surveyor draws tree cover. A filled circle was the single most "diagram"
	# thing on the old map.
	#
	# The stroke pattern is HASHED OFF THE GROVE'S OWN CELL, never rolled: this
	# runs on every redraw, so anything random would crawl while you pan.
	for g in (_vec["groves"] as Array):
		var density := float(g[2])
		if density < 2.0:
			continue
		var gx := int(g[0])
		var gy := int(g[1])
		var centre := _cell_to_screen(Vector2(float(gx) + 1.5, float(gy) + 1.5))
		var radius := (1.4 + minf(density, 9.0) * 0.16) * z
		var col: Color = GREEN_AUTUMN if int(g[3]) == 1 else GREEN
		var strokes := clampi(int(density * 0.8), 2, 8)
		var sl := maxf(1.5, z * 0.45)
		for i in strokes:
			var hsh: int = absi((gx * 73856093) ^ (gy * 19349663) ^ (i * 83492791))
			var ang := float(hsh & 1023) / 1023.0 * TAU
			var rr := radius * (0.2 + float((hsh >> 10) & 255) / 255.0 * 0.75)
			var at := centre + Vector2(cos(ang), sin(ang)) * rr
			_canvas.draw_line(at + Vector2(-sl, sl), at + Vector2(sl, -sl),
				col, maxf(1.0, z * 0.15), true)
	# the plaza and the depot apron: paved clearings
	for paved in [_vec["plaza"], _vec["apron"]]:
		var pr: Array = paved
		if float(pr[2]) <= 0.0:
			continue
		_canvas.draw_rect(Rect2(
			_cell_to_screen(Vector2(float(pr[0]), float(pr[1]))),
			Vector2(float(pr[2]), float(pr[3])) * z), PAPER_HI)
	# the places that aren't paved get an OUTLINE, so the lz, the gallery,
	# the comms relay and the trainyard read as somewhere instead of a
	# word floating over open ground (user call)
	for area in (_vec.get("areas", []) as Array):
		var ar: Array = area
		if float(ar[2]) <= 0.0:
			continue
		_canvas.draw_rect(Rect2(
			_cell_to_screen(Vector2(float(ar[0]), float(ar[1]))),
			Vector2(float(ar[2]), float(ar[3])) * z),
			INK_SOFT, false, maxf(1.0, z * 0.18))
	# roads: real strokes, edged, with a hairline centre — a chart, not
	# a grid of squares (user: "just make it a normal map")
	for r in (_vec["roads_v"] as Array):
		var x := float(r[0])
		var rw := float(r[1]) * z
		# a road that stops short is drawn stopping short (v0.5.4)
		var from_y := float(r[2]) if r.size() > 3 else inset
		var to_y := float(r[3]) if r.size() > 3 else h - inset
		var top := _cell_to_screen(Vector2(x, maxf(from_y, inset)))
		var bot := _cell_to_screen(Vector2(x, minf(to_y, h - inset)))
		var mid := top.x + rw * 0.5
		# CASED like a drawn road: an ink stroke with a pale channel inside it
		_canvas.draw_line(Vector2(mid, top.y), Vector2(mid, bot.y),
			INK, rw + 2.0, true)
		_canvas.draw_line(Vector2(mid, top.y), Vector2(mid, bot.y),
			PAPER_HI, rw, true)
	for r in (_vec["roads_h"] as Array):
		var y := float(r[0])
		var rw2 := float(r[1]) * z
		var from_x := float(r[2]) if r.size() > 3 else inset
		var to_x := float(r[3]) if r.size() > 3 else w - inset
		var left := _cell_to_screen(Vector2(maxf(from_x, inset), y))
		var right := _cell_to_screen(Vector2(minf(to_x, w - inset), y))
		var mid2 := left.y + rw2 * 0.5
		_canvas.draw_line(Vector2(left.x, mid2), Vector2(right.x, mid2),
			INK, rw2 + 2.0, true)
		_canvas.draw_line(Vector2(left.x, mid2), Vector2(right.x, mid2),
			PAPER_HI, rw2, true)
	# the rail line, with ties
	var rail_row := float(_vec["rail_row"])
	if rail_row > 0.0:
		var ry := _cell_to_screen(Vector2(0.0, rail_row + 0.5)).y
		var rx0 := _cell_to_screen(Vector2(inset, 0.0)).x
		var rx1 := _cell_to_screen(Vector2(w - inset, 0.0)).x
		_canvas.draw_line(Vector2(rx0, ry), Vector2(rx1, ry), RAIL,
			maxf(2.0, z * 1.6), true)
		var tie := rx0
		while tie < rx1:
			_canvas.draw_line(Vector2(tie, ry - z), Vector2(tie, ry + z),
				INK, 1.0, true)
			tie += maxf(6.0, z * 3.0)
	# buildings: solid footprints with a lit north edge
	for b in (_vec["buildings"] as Array):
		var rect := Rect2(_cell_to_screen(Vector2(float(b[0]), float(b[1]))),
			Vector2(float(b[2]), float(b[3])) * z)
		var kind := str(b[4])
		var col := BUILDING
		if kind == "house" or kind == "safehouse":
			col = BUILDING_WARM
		elif kind == "school":
			col = BUILDING_WARM.lightened(0.12)
		_canvas.draw_rect(rect, col)
		# EVERY FOOTPRINT IS INKED. This one line is most of what stops the
		# buildings reading as flat coloured blocks — on a drawn map a
		# structure has an edge, and the fill is only what sits inside it.
		_canvas.draw_rect(rect, INK, false, maxf(1.0, z * 0.15))
		if int(b[5]) == 2:                       # two-story: a lighter core
			_canvas.draw_rect(rect.grow(-maxf(1.0, z * 0.5)), col.lightened(0.14))
		if kind == "safehouse":
			# home is RINGED, not lit up: a bright slab here competed with
			# the "me" marker that stands on it half the time
			_canvas.draw_rect(rect.grow(maxf(1.5, z * 0.4)),
				ME, false, 1.5)
	# the wire: a broken red line all the way round the playable district
	var ring := Rect2(_cell_to_screen(Vector2(inset, inset)),
		Vector2(w - inset * 2.0, h - inset * 2.0) * z)
	_draw_dashed_rect(_canvas, ring, RING, 2.0, 7.0, 5.0)
	# the place names belong to THIS layer: they only move when you pan or
	# zoom, exactly like everything else here. They used to sit on the
	# markers layer, which redraws every frame, so ~135 text-shaping calls
	# ran at render rate the whole time the map was up — on top of the raid,
	# because the map deliberately does not pause the tree.
	_draw_poi_labels(_canvas)


func _draw_dashed_rect(on: Control, rect: Rect2, col: Color, width: float,
		dash: float, gap: float) -> void:
	var corners := [rect.position, Vector2(rect.end.x, rect.position.y),
		rect.end, Vector2(rect.position.x, rect.end.y)]
	for i in 4:
		var a: Vector2 = corners[i]
		var b: Vector2 = corners[(i + 1) % 4]
		var span := a.distance_to(b)
		var dir := (b - a).normalized()
		var t := 0.0
		while t < span:
			var t2 := minf(t + dash, span)
			on.draw_line(a + dir * t, a + dir * t2, col, width, true)
			t = t2 + gap


func _draw_poi_glyph(on: Control, name: String, at: Vector2) -> void:
	## ONE DRAWN SYMBOL PER PLACE, in ink. The old map put a word on open
	## ground and nothing else, which is most of why it read as a diagram
	## (user: "its like some minecraft map").
	##
	## FIXED PIXEL SIZE on purpose — a map symbol does not grow when you zoom,
	## and these have to stay readable at whole-district zoom, which is where
	## the map opens. Each sits on a paper disc so it survives landing on a
	## road, a wood or a rooftop, the same job the text halo does.
	const S := 5.0
	const LW := 1.4
	on.draw_circle(at, S + 2.0, Color(PAPER.r, PAPER.g, PAPER.b, 0.88),
		true, -1.0, true)
	on.draw_arc(at, S + 2.0, 0.0, TAU, 20, INK_SOFT, 1.0, true)
	match name:
		"bus depot":                                  # a bus
			on.draw_rect(Rect2(at + Vector2(-S, -S * 0.75),
				Vector2(S * 2.0, S * 1.3)), INK, false, LW)
			on.draw_line(at + Vector2(-S + 1.0, -S * 0.2),
				at + Vector2(S - 1.0, -S * 0.2), INK, 1.0, true)
			on.draw_circle(at + Vector2(-S * 0.45, S * 0.75), 1.1, INK, true, -1.0, true)
			on.draw_circle(at + Vector2(S * 0.45, S * 0.75), 1.1, INK, true, -1.0, true)
		"scrapyard":                                  # a crane and its hook
			on.draw_line(at + Vector2(-S * 0.3, S), at + Vector2(-S * 0.3, -S), INK, LW, true)
			on.draw_line(at + Vector2(-S, -S), at + Vector2(S, -S), INK, LW, true)
			on.draw_line(at + Vector2(S * 0.6, -S), at + Vector2(S * 0.6, S * 0.2), INK, 1.0, true)
			on.draw_arc(at + Vector2(S * 0.6, S * 0.45), 1.5, PI, TAU + 0.7, 10, INK, 1.0, true)
		"warehouse":                                  # a shed with a chimney
			on.draw_rect(Rect2(at + Vector2(-S, 0.0), Vector2(S * 2.0, S)), INK, false, LW)
			on.draw_line(at + Vector2(-S, 0.0), at + Vector2(0.0, -S * 0.85), INK, LW, true)
			on.draw_line(at + Vector2(S, 0.0), at + Vector2(0.0, -S * 0.85), INK, LW, true)
			on.draw_line(at + Vector2(S * 0.5, -S * 0.42), at + Vector2(S * 0.5, -S * 1.3),
				INK, LW, true)
		"playground":                                 # a swing
			on.draw_line(at + Vector2(-S, S), at + Vector2(0.0, -S), INK, LW, true)
			on.draw_line(at + Vector2(S, S), at + Vector2(0.0, -S), INK, LW, true)
			on.draw_line(at + Vector2(-S * 0.6, -S * 0.1), at + Vector2(S * 0.6, -S * 0.1),
				INK, 1.0, true)
			on.draw_line(at + Vector2(S * 0.2, -S * 0.1), at + Vector2(S * 0.2, S * 0.55),
				INK, 1.0, true)
			on.draw_line(at + Vector2(S * 0.55, S * 0.55), at + Vector2(-S * 0.15, S * 0.55),
				INK, LW, true)
		"comms":                                      # a mast, still blinking
			on.draw_line(at + Vector2(-S * 0.7, S), at + Vector2(0.0, -S), INK, LW, true)
			on.draw_line(at + Vector2(S * 0.7, S), at + Vector2(0.0, -S), INK, LW, true)
			on.draw_line(at + Vector2(-S * 0.45, S * 0.3), at + Vector2(S * 0.45, S * 0.3),
				INK, 1.0, true)
			on.draw_arc(at + Vector2(0.0, -S), 2.6, PI * 1.15, PI * 1.85, 8, INK, 1.0, true)
			on.draw_arc(at + Vector2(0.0, -S), 4.0, PI * 1.2, PI * 1.8, 8, INK, 1.0, true)
		"toll gate":                                  # the boom across the road
			on.draw_line(at + Vector2(-S * 0.8, S), at + Vector2(-S * 0.8, -S * 0.5),
				INK, LW, true)
			on.draw_line(at + Vector2(-S * 0.8, -S * 0.3), at + Vector2(S, S * 0.5),
				INK, LW, true)
			on.draw_line(at + Vector2(-S * 1.3, S), at + Vector2(-S * 0.3, S), INK, LW, true)
		"safehouse":                                  # home
			on.draw_line(at + Vector2(-S, 0.0), at + Vector2(0.0, -S), ME, LW, true)
			on.draw_line(at + Vector2(S, 0.0), at + Vector2(0.0, -S), ME, LW, true)
			on.draw_rect(Rect2(at + Vector2(-S * 0.7, 0.0),
				Vector2(S * 1.4, S * 0.9)), ME, false, LW)
			on.draw_rect(Rect2(at + Vector2(-S * 0.2, S * 0.3),
				Vector2(S * 0.45, S * 0.6)), ME, false, 1.0)
		"lz":                                         # the landing pad: an H
			on.draw_arc(at, S * 0.95, 0.0, TAU, 22, INK, LW, true)
			on.draw_line(at + Vector2(-S * 0.4, -S * 0.5), at + Vector2(-S * 0.4, S * 0.5),
				INK, LW, true)
			on.draw_line(at + Vector2(S * 0.4, -S * 0.5), at + Vector2(S * 0.4, S * 0.5),
				INK, LW, true)
			on.draw_line(at + Vector2(-S * 0.4, 0.0), at + Vector2(S * 0.4, 0.0), INK, LW, true)
		"school":                                     # a schoolhouse bell
			on.draw_rect(Rect2(at + Vector2(-S, -S * 0.2),
				Vector2(S * 2.0, S * 1.1)), INK, false, LW)
			on.draw_line(at + Vector2(-S, -S * 0.2), at + Vector2(0.0, -S * 0.9), INK, LW, true)
			on.draw_line(at + Vector2(S, -S * 0.2), at + Vector2(0.0, -S * 0.9), INK, LW, true)
			on.draw_arc(at + Vector2(0.0, -S * 0.95), 1.5, PI, TAU, 8, INK, LW, true)
		"courtyard":                                  # the dry fountain
			on.draw_arc(at, S * 0.9, 0.0, TAU, 22, INK, LW, true)
			on.draw_arc(at, S * 0.35, 0.0, TAU, 12, INK, 1.0, true)
			on.draw_line(at + Vector2(0.0, -S * 0.35), at + Vector2(0.0, -S * 0.95),
				INK, 1.0, true)
		"trainyard":                                  # a boxcar on rails
			on.draw_rect(Rect2(at + Vector2(-S, -S * 0.8),
				Vector2(S * 2.0, S * 1.2)), INK, false, LW)
			on.draw_line(at + Vector2(-S, S * 0.85), at + Vector2(S, S * 0.85), INK, 1.0, true)
			on.draw_circle(at + Vector2(-S * 0.45, S * 0.5), 1.0, INK, true, -1.0, true)
			on.draw_circle(at + Vector2(S * 0.45, S * 0.5), 1.0, INK, true, -1.0, true)
		"gallery":                                    # a framed picture
			on.draw_rect(Rect2(at + Vector2(-S * 0.9, -S * 0.8),
				Vector2(S * 1.8, S * 1.6)), INK, false, LW)
			on.draw_line(at + Vector2(-S * 0.6, S * 0.5), at + Vector2(-S * 0.05, -S * 0.3),
				INK, 1.0, true)
			on.draw_line(at + Vector2(-S * 0.05, -S * 0.3), at + Vector2(S * 0.6, S * 0.5),
				INK, 1.0, true)
		_:
			# anything without its own symbol still gets a surveyor's mark
			# rather than nothing — a ringed dot reads as "a place".
			on.draw_circle(at, 1.6, INK, true, -1.0, true)
			on.draw_arc(at, S * 0.75, 0.0, TAU, 16, INK, 1.0, true)


func _draw_poi_labels(on: Control) -> void:
	# POI names ON the map — no boxes any more (user: "remove all of the
	# squares"), just type with a dark halo so it reads over anything.
	# Collision-yield: a name that would land on one already placed is
	# dropped rather than stacked.
	var drawn: Array[Rect2] = []
	for poi in _pois:
		if not bool(poi["label"]):
			continue
		var text := str(poi["name"])
		var has_glyph := bool(poi.get("glyph", false))
		var centre: Vector2 = _cell_to_screen((poi["rect"] as Rect2).get_center())
		var tw := _font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1,
			_font_size).x
		# the name sits UNDER its symbol; a region has no symbol and keeps the
		# centred placement it always had
		var drop := 13.0 if has_glyph else float(_font_size) * 0.5
		var pos := (centre + Vector2(-tw * 0.5, drop)).round()
		var bounds := Rect2(pos - Vector2(3.0, float(_font_size)),
			Vector2(tw + 6.0, float(_font_size) + 4.0))
		if has_glyph:
			# the symbol is part of what must not be landed on, or a
			# neighbour's name prints straight through it
			bounds = bounds.merge(Rect2(centre - Vector2(8.0, 8.0),
				Vector2(16.0, 16.0)))
		var clash := false
		for r in drawn:
			if r.intersects(bounds):
				clash = true
				break
		if clash:
			continue
		drawn.append(bounds)
		if has_glyph:
			_draw_poi_glyph(on, text, centre)
		# THE SAFEHOUSE GETS NO NAME. You spawn on it, so the live "me" marker
		# sits on top of it for the first stretch of every raid and the two
		# labels printed straight through each other. Its red home glyph and
		# the red ring round its footprint already make it the one unmistakable
		# building on the sheet, and the hover blurb still says what it is.
		if text == "safehouse":
			continue
		_halo_text(on, pos, text, LABEL)


func _draw_markers() -> void:
	if _vec.is_empty() and _map_tex == null:
		return
	# live vehicle dots: SMALLER than they were, coloured by what they are,
	# and named. Trucks read blue, cars amber (user).
	var dot_labels: Array[Rect2] = []
	for node in get_tree().get_nodes_in_group("cars"):
		var car := node as DriveableCar
		var car_cell := Vector2(_floor_layer.local_to_map(
			(node as Node2D).global_position)) + Vector2(0.5, 0.5)
		var at := _cell_to_screen(car_cell)
		var truck := car != null and car.kind == "truck"
		_markers.draw_circle(at, maxf(1.5, _zoom * 0.45),
			TRUCK_DOT if truck else CAR_DOT, true, -1.0, true)
		# the name only when the map is zoomed in far enough to read it — at
		# a whole-district zoom every label would land on its neighbour and
		# the whole thing turns to soup.
		#
		# THIS THRESHOLD WAS 3.0 AND THE MAP OPENS AT ~3.6, so every one of the
		# ~33 vehicles printed its name the moment you pressed m and carpeted
		# the sheet. The dots alone say "a vehicle is here"; the word is only
		# worth the ink once you have zoomed in to go and find it.
		if _zoom >= 7.0:
			var word := "truck" if truck else "car"
			var f: Font = _tiny_font if _tiny_font != null else _font
			var fs: int = _tiny_size if _tiny_font != null else _font_size
			var tw := f.get_string_size(word, HORIZONTAL_ALIGNMENT_LEFT,
				-1, fs).x
			var tp := (at + Vector2(-tw * 0.5, -3.0)).round()
			# two vehicles parked together printed their names straight over
			# each other and came out as "truckck" (seen on a map capture).
			# Same collision-yield the place names use: if it would land on
			# one already drawn, it does not draw.
			var box := Rect2(tp - Vector2(1.0, float(fs)),
				Vector2(tw + 2.0, float(fs) + 2.0))
			var clash := false
			for r in dot_labels:
				if r.intersects(box):
					clash = true
					break
			if clash:
				continue
			dot_labels.append(box)
			for off in [Vector2(-1, 0), Vector2(1, 0), Vector2(0, -1),
					Vector2(0, 1)]:
				_markers.draw_string(f, tp + off, word,
					HORIZONTAL_ALIGNMENT_LEFT, -1, fs,
					Color(PAPER.r, PAPER.g, PAPER.b, 0.9))
			_markers.draw_string(f, tp, word, HORIZONTAL_ALIGNMENT_LEFT, -1, fs,
				TRUCK_DOT if truck else CAR_DOT)
	# ME: impossible to lose (user: "alot more noticable"). A pulsing ring,
	# a bright core, cross ticks, and the label riding above it.
	var cell := Vector2(_floor_layer.local_to_map(_player.global_position)) \
		+ Vector2(0.5, 0.5)
	var p := _cell_to_screen(cell)
	var beat := 0.5 + 0.5 * sin(_time_accum * 3.4)
	var ring_r := 9.0 + 5.0 * beat
	_markers.draw_circle(p, ring_r, Color(ME.r, ME.g, ME.b, 0.14 + 0.16 * (1.0 - beat)),
		true, -1.0, true)
	_markers.draw_arc(p, ring_r, 0.0, TAU, 28,
		Color(ME.r, ME.g, ME.b, 0.55), 1.5, true)
	# WHICH WAY YOU'RE FACING (user: "a circle i cant really tell"). The
	# player's sheet rows are E,SE,S,SW,W,NW,N,NE, so the facing index maps
	# straight onto screen degrees — and on an iso map screen direction is
	# exactly the direction you'd walk.
	var facing := _player.facing_angle()
	var aim := Vector2(cos(facing), sin(facing))
	var side := aim.orthogonal()
	var tip := p + aim * 17.0
	_markers.draw_colored_polygon(PackedVector2Array([
		tip, p + aim * 6.0 + side * 5.5, p + aim * 6.0 - side * 5.5]),
		Color(ME.r, ME.g, ME.b, 0.92))
	_markers.draw_line(p + aim * 6.0 + side * 5.5, tip,
		Color(0.043, 0.055, 0.086, 0.6), 1.0, true)
	_markers.draw_line(p + aim * 6.0 - side * 5.5, tip,
		Color(0.043, 0.055, 0.086, 0.6), 1.0, true)
	for i in 4:                                  # cross ticks
		var dir := [Vector2.UP, Vector2.RIGHT, Vector2.DOWN, Vector2.LEFT][i] as Vector2
		_markers.draw_line(p + dir * 5.0, p + dir * 8.5, ME, 1.5, true)
	_markers.draw_circle(p, 4.5, Color(0.043, 0.055, 0.086, 0.95), true, -1.0, true)
	_markers.draw_circle(p, 3.0, ME, true, -1.0, true)
	var me_w := _font.get_string_size("me", HORIZONTAL_ALIGNMENT_LEFT, -1,
		_font_size).x
	_halo_text(_markers, (p + Vector2(-me_w * 0.5, -ring_r - 4.0)).round(),
		"me", ME)


func _halo_text(on: Control, pos: Vector2, text: String, col: Color) -> void:
	# a PAPER halo instead of a label box — ink type stays legible over a
	# road, a wood or a rooftop without cutting a rectangle out of the map.
	# (This was a DARK halo, which was correct while the sheet was dark and
	# turns the type to mud now that the sheet is paper.)
	for off in [Vector2(-1, 0), Vector2(1, 0), Vector2(0, -1), Vector2(0, 1),
			Vector2(-1, -1), Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1)]:
		on.draw_string(_font, pos + off, text, HORIZONTAL_ALIGNMENT_LEFT, -1,
			_font_size, Color(PAPER.r, PAPER.g, PAPER.b, 0.92))
	on.draw_string(_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1,
		_font_size, col)
