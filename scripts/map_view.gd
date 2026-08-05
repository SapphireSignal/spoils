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
# THE MAP'S PALETTE — a GAME map, not a paper one.
#
# v0.6.46 rebuilt this as a surveyor's chart: aged paper, sepia ink on every
# edge, woods as diagonal hatch strokes, a symbol on a paper disc for every
# place. It was internally consistent and the user rejected it —
#
#   "the in game map looks like an actual map that youd hold, i dont want it
#    like that, i want there to be colour on there, the trees are just lines
#    in there too, and all the roads are the same size oin the map ... the map
#    just looks like squares and lines, doesnt look like an actual map.
#    remember i dont want a real looking map i just want it to look like a
#    good real map that youd see in other video games"
#
# So: TERRAIN, not paper. The ground is coloured by what it actually is, the
# woods are canopy masses, the road network is the brightest thing on the
# sheet and it has a hierarchy, and every place is a coloured marker keyed to
# what it is FOR rather than one more ink disc.
#
# The old scheme's mistake is worth naming so it is not repeated: it answered
# "this reads as a diagram" with "make it look hand-drawn", when the actual
# problem was that everything was the SAME — one hue, one road width, one
# marker treatment. Sameness is what reads as a diagram, not colour.
#
# All Apollo, like everything else in the project.
# ---------------------------------------------------------------------------
const LAND := Color("394a50")                    # open ground: lots, verges
const URBAN := Color("202e37")                   # city blocks, a shade denser
const PAVED := Color("577277")                   # plazas, aprons, hardstanding
const OUTSIDE := Color("151d28")                 # ground beyond the wire
const DIRT := Color("4d2b32")                    # yards, unmade ground
const WOOD_DEEP := Color("19332d")               # under the canopy
const WOOD := Color("25562e")                    # canopy body
const WOOD_HI := Color("468232")                 # the sunlit tops
const WOOD_AUT := Color("884b2b")                # the turned stand
const WOOD_AUT_HI := Color("be772b")
const ROAD_MAJOR := Color("a8b5b2")              # the through routes
const ROAD_MINOR := Color("819796")              # everything else
const ROAD_CASE := Color("10141f")               # the casing under both
const RAIL := Color("4d2b32")
const TIE := Color("819796")                     # sleepers, light on dark rail
const BUILDING := Color("577277")                # civic / warehouse
const BUILDING_WARM := Color("7a4841")           # houses
const RING := Color("a53030")                    # the wire
const ME := Color("cf573c")                      # you. The loudest thing here.
const CAR_DOT := Color("de9e41")                 # amber
const TRUCK_DOT := Color("4f8fba")               # blue, so the two read apart
const LABEL := Color("ebede9")                   # place names, light on dark
const HALO := Color("090a14")                    # ...and the dark behind them
const GLYPH := Color("ebede9")                   # marker symbols
const GLYPH_DIM := Color("a8b5b2")               # their secondary strokes
# MARKER DISCS BY WHAT THE PLACE IS FOR. The user's "all the pois are like in
# the same spot" is partly the fixed layout, but they also all LOOKED the
# same: one ink disc, one ink symbol, and a thin hollow rectangle round each.
# A player should be able to tell "this is how I get out" from "this is worth
# looting" without reading a word.
const DISC_EXIT := Color("468232")               # ways out of the district
const DISC_HOME := Color("a53030")               # the safehouse
const DISC_PLACE := Color("3c5e8b")              # landmarks and loot
const DISC_EDGE := Color("090a14")

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

	# THE GROUND. Open land first; everything below is a different SURFACE
	# drawn on it, which is what makes this terrain rather than a sheet.
	# BEYOND THE WIRE FIRST. The buffer band has real woods in it and they were
	# being drawn onto the panel background, so trees floated on nothing
	# outside the ring. Dim ground under them says "this is still the world,
	# you just can't go there" — which is true; crossing it gets you sniped.
	_canvas.draw_rect(Rect2(_cell_to_screen(Vector2.ZERO), Vector2(w, h) * z),
		OUTSIDE)
	var land := Rect2(_cell_to_screen(Vector2(inset, inset)),
		Vector2(w - inset * 2.0, h - inset * 2.0) * z)
	_canvas.draw_rect(land, LAND)
	# city blocks: denser, darker ground. A FULL fill, not the 45% tint the
	# paper map needed — that tint existed only so the paper showed through,
	# and there is no paper any more.
	for b in (_vec["blocks"] as Array):
		var br := Rect2(_cell_to_screen(Vector2(float(b[0]), float(b[1]))),
			Vector2(float(b[2]), float(b[3])) * z)
		_canvas.draw_rect(br, URBAN)
	# GROUND MOTTLE. Without it the open ground and the blocks are two flat
	# colour fields, which is most of what still read as "squares and lines"
	# once the colour was in. These are broken concrete, weeds and rubble —
	# the district really is weathered in patches (the builder mixes
	# concrete_worn/damp off two offset hash grids), so this is texture the
	# ground genuinely has, not invented structure.
	#
	# HASHED OFF THE CELL, never rolled — this redraws on every pan, and a
	# random patch would crawl across the map while you dragged it.
	# SMALL AND TIGHT. The first cut used radius 1.6-4.3 CELLS at ~0.16 alpha
	# and it read as soft grey smudges drifting over the district — closer to
	# fog than to ground, and this user spots an artifact instantly. Patch
	# size is what decides whether this reads as texture or as a rendering
	# fault; it is well under a cell now.
	var step := 5
	var mx := int(inset)
	while mx < int(w - inset):
		var my := int(inset)
		while my < int(h - inset):
			var hsh: int = absi((mx * 374761393) ^ (my * 668265263))
			if (hsh & 255) < 132:
				var jx := float((hsh >> 8) & 3)
				var jy := float((hsh >> 10) & 3)
				var rr := (0.45 + float((hsh >> 12) & 3) * 0.3) * z
				var dark := ((hsh >> 16) & 1) == 0
				_canvas.draw_circle(
					_cell_to_screen(Vector2(float(mx) + jx, float(my) + jy)),
					rr,
					Color(0.02, 0.03, 0.05, 0.13) if dark
						else Color(0.62, 0.70, 0.68, 0.05),
					true, -1.0, false)
			my += step
		mx += step
	# the plaza and the depot apron: paved clearings
	for paved in [_vec["plaza"], _vec["apron"]]:
		var pr: Array = paved
		if float(pr[2]) <= 0.0:
			continue
		_canvas.draw_rect(Rect2(
			_cell_to_screen(Vector2(float(pr[0]), float(pr[1]))),
			Vector2(float(pr[2]), float(pr[3])) * z), PAVED)
	# named areas get a SURFACE, keyed to what the ground there actually is.
	# They used to get a thin hollow rectangle each, which is most of what the
	# user meant by "the map just looks like squares and lines" — seven empty
	# boxes with a word in them.
	for area in (_vec.get("areas", []) as Array):
		var ar: Array = area
		if float(ar[2]) <= 0.0:
			continue
		var kind_a := str(ar[4]) if ar.size() > 4 else ""
		var surface := PAVED
		match kind_a:
			"scrapyard", "trainyard":
				surface = DIRT
			"playground":
				surface = WOOD
			"lz":
				surface = PAVED.lightened(0.08)
		# A TINT, NOT A FILL. The trainyard area is a whole block and the
		# scrapyard nearly one, so at full opacity they came out as two big
		# solid slabs — "squares", the exact thing being fixed. At 0.72 the
		# ground underneath still reads through and they land as surfaces.
		surface.a = 0.72
		_canvas.draw_rect(Rect2(
			_cell_to_screen(Vector2(float(ar[0]), float(ar[1]))),
			Vector2(float(ar[2]), float(ar[3])) * z), surface)
	# THE WOODS ARE CANOPY MASSES. They were diagonal hatch strokes — the way
	# a surveyor draws tree cover, and the user's words were "the trees are
	# just lines in there too".
	#
	# Each grove is a clump of overlapping discs rather than one circle: a
	# single circle per bucket is the "diagram" read the hatching was trying
	# to escape, but the answer is an IRREGULAR EDGE, not a different stroke.
	# Deep tone first, canopy over it, a sunlit cap offset up-left, so the
	# wood has a light direction like everything else in the game.
	#
	# Everything here is HASHED OFF THE GROVE'S OWN CELL, never rolled: this
	# runs on every redraw, so anything random would crawl while you pan.
	for g in (_vec["groves"] as Array):
		var density := float(g[2])
		if density < 2.0:
			continue
		var gx := int(g[0])
		var gy := int(g[1])
		var autumn := int(g[3]) == 1
		var centre := _cell_to_screen(Vector2(float(gx) + 1.5, float(gy) + 1.5))
		var radius := (1.1 + minf(density, 9.0) * 0.19) * z
		var deep: Color = WOOD_AUT.darkened(0.4) if autumn else WOOD_DEEP
		var body: Color = WOOD_AUT if autumn else WOOD
		var lit: Color = WOOD_AUT_HI if autumn else WOOD_HI
		var lobes := clampi(int(density * 0.5), 2, 4)
		for i in lobes:
			var hsh: int = absi((gx * 73856093) ^ (gy * 19349663) ^ (i * 83492791))
			var ang := float(hsh & 1023) / 1023.0 * TAU
			var off := radius * 0.45 * float((hsh >> 10) & 255) / 255.0
			var at := centre + Vector2(cos(ang), sin(ang)) * off
			var rr := radius * (0.62 + float((hsh >> 18) & 127) / 127.0 * 0.38)
			# ANTIALIASING OFF, deliberately. These are the single most
			# numerous primitive on the map — hundreds of groves, several
			# lobes each — and an antialiased draw_circle builds edge geometry
			# every frame the map is up. The whole district layer is re-
			# rasterised per frame whether or not the draw callback re-runs,
			# so this is a per-frame cost, and it measured 240 -> 210 fps.
			# At these radii the aliased edge is also the more correct look
			# for a game that renders on a pixel grid.
			_canvas.draw_circle(at + Vector2(rr * 0.16, rr * 0.2), rr, deep,
				true, -1.0, false)
			_canvas.draw_circle(at, rr * 0.92, body, true, -1.0, false)
			_canvas.draw_circle(at - Vector2(rr * 0.22, rr * 0.26), rr * 0.44,
				lit, true, -1.0, false)
	# ROADS, AND THEY HAVE A HIERARCHY (user: "all the roads are the same size
	# oin the map"). They were — and so is the WORLD: _plan_roads appends
	# Vector2i(base, 4) for every road, so all of them really are four cells
	# wide and the old map was telling the truth.
	#
	# The honest hierarchy is the SPAN. A road that runs the full height or
	# width of the district is a through route you can drive end to end; one
	# that stops short is a stub the council never finished. That is a real
	# difference, it is in the data, and it is the one a player cares about —
	# so through routes are drawn wide and bright with a centre line, stubs
	# narrow and dull. Nothing here invents a width the world does not have;
	# it picks which roads to EMPHASISE, which is what a map is for.
	for r in (_vec["roads_v"] as Array):
		var x := float(r[0])
		# a road that stops short is drawn stopping short (v0.5.4)
		var from_y := float(r[2]) if r.size() > 3 else inset
		var to_y := float(r[3]) if r.size() > 3 else h - inset
		var through := from_y <= inset + 1.0 and to_y >= h - inset - 1.0
		var rw := float(r[1]) * z * (1.0 if through else 0.62)
		var top := _cell_to_screen(Vector2(x, maxf(from_y, inset)))
		var bot := _cell_to_screen(Vector2(x, minf(to_y, h - inset)))
		var mid := top.x + float(r[1]) * z * 0.5
		_canvas.draw_line(Vector2(mid, top.y), Vector2(mid, bot.y),
			ROAD_CASE, rw + maxf(2.0, z * 0.5), true)
		_canvas.draw_line(Vector2(mid, top.y), Vector2(mid, bot.y),
			ROAD_MAJOR if through else ROAD_MINOR, rw, true)
		if through and z > 1.6:
			_dashed_line(Vector2(mid, top.y), Vector2(mid, bot.y),
				ROAD_CASE, maxf(1.0, z * 0.18), z * 2.2, z * 2.2)
	for r in (_vec["roads_h"] as Array):
		var y := float(r[0])
		var from_x := float(r[2]) if r.size() > 3 else inset
		var to_x := float(r[3]) if r.size() > 3 else w - inset
		var through2 := from_x <= inset + 1.0 and to_x >= w - inset - 1.0
		var rw2 := float(r[1]) * z * (1.0 if through2 else 0.62)
		var left := _cell_to_screen(Vector2(maxf(from_x, inset), y))
		var right := _cell_to_screen(Vector2(minf(to_x, w - inset), y))
		var mid2 := left.y + float(r[1]) * z * 0.5
		_canvas.draw_line(Vector2(left.x, mid2), Vector2(right.x, mid2),
			ROAD_CASE, rw2 + maxf(2.0, z * 0.5), true)
		_canvas.draw_line(Vector2(left.x, mid2), Vector2(right.x, mid2),
			ROAD_MAJOR if through2 else ROAD_MINOR, rw2, true)
		if through2 and z > 1.6:
			_dashed_line(Vector2(left.x, mid2), Vector2(right.x, mid2),
				ROAD_CASE, maxf(1.0, z * 0.18), z * 2.2, z * 2.2)
	# BROKEN STRETCHES, drawn over the road lines. Without these the network is
	# a set of perfectly ruled bands, which is exactly what the user objected to
	# ("the straight roads just look really weird, especially on the map"). They
	# are real: the same cells the world paints as bare earth.
	for rc in (_vec.get("road_rot", []) as Array):
		var rcell: Array = rc
		var rp := _cell_to_screen(Vector2(float(rcell[0]), float(rcell[1])))
		_canvas.draw_rect(Rect2(rp, Vector2(z, z) * 1.15), DIRT, true)
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
				TIE, 1.0, true)
			tie += maxf(6.0, z * 3.0)
	# buildings: solid footprints, lit from the top-left like the rest of the
	# game. The edge is a DARK GROUND SHADOW on the bottom-right rather than a
	# full ink outline — an outline on all four sides is what made these read
	# as boxes drawn on a diagram instead of structures standing on ground.
	for b in (_vec["buildings"] as Array):
		var rect := Rect2(_cell_to_screen(Vector2(float(b[0]), float(b[1]))),
			Vector2(float(b[2]), float(b[3])) * z)
		var kind := str(b[4])
		var col := BUILDING
		if kind == "house" or kind == "safehouse":
			col = BUILDING_WARM
		elif kind == "school":
			col = BUILDING_WARM.lightened(0.12)
		var lip := maxf(1.0, z * 0.22)
		_canvas.draw_rect(Rect2(rect.position + Vector2(lip, lip), rect.size),
			Color(0.035, 0.04, 0.08, 0.5))
		_canvas.draw_rect(rect, col)
		if int(b[5]) == 2:                       # two-story: a lighter core
			_canvas.draw_rect(rect.grow(-maxf(1.0, z * 0.5)), col.lightened(0.16))
		# a lit top edge and a shaded bottom one: the same 1 px rim trick the
		# wordmark uses, and it is what stops a filled rect reading as flat
		_canvas.draw_line(rect.position, Vector2(rect.end.x, rect.position.y),
			col.lightened(0.3), maxf(1.0, z * 0.14), false)
		_canvas.draw_line(Vector2(rect.position.x, rect.end.y), rect.end,
			col.darkened(0.45), maxf(1.0, z * 0.14), false)
		if kind == "safehouse":
			# home is RINGED, not lit up: a bright slab here competed with
			# the "me" marker that stands on it half the time
			_canvas.draw_rect(rect.grow(maxf(1.5, z * 0.4)),
				DISC_HOME, false, 1.5)
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


func _poi_disc(name: String) -> Color:
	## What is this place FOR? The three answers a player acts on.
	match name:
		"lz", "toll gate", "trainyard":
			return DISC_EXIT              # the three ways out (DESIGN.md 8.4)
		"safehouse":
			return DISC_HOME
		_:
			return DISC_PLACE


func _dashed_line(from: Vector2, to: Vector2, col: Color, width: float,
		dash: float, gap: float) -> void:
	var span := from.distance_to(to)
	if span <= 0.0 or dash <= 0.0:
		return
	var dir := (to - from) / span
	var at := 0.0
	while at < span:
		var end := minf(at + dash, span)
		_canvas.draw_line(from + dir * at, from + dir * end, col, width, true)
		at = end + gap


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
	# THE DISC IS COLOURED BY WHAT THE PLACE IS FOR. Every marker used to be
	# the same ink symbol on the same paper disc, inside the same thin hollow
	# rectangle — so a way out of the district and a building worth looting
	# were visually identical, and the user's read was "all the pois are like
	# in the same spot". Green means you can leave from here, red is home,
	# blue is somewhere to go. That is legible before you read a single word.
	var disc := _poi_disc(name)
	on.draw_circle(at + Vector2(1.0, 1.2), S + 2.0, Color(0.035, 0.04, 0.08, 0.55),
		true, -1.0, true)
	on.draw_circle(at, S + 2.0, disc, true, -1.0, true)
	on.draw_arc(at, S + 2.0, 0.0, TAU, 20, DISC_EDGE, 1.4, true)
	on.draw_arc(at, S + 1.0, PI * 1.05, PI * 1.75, 12,
		Color(1.0, 1.0, 1.0, 0.28), 1.0, true)
	match name:
		"bus depot":                                  # a bus
			on.draw_rect(Rect2(at + Vector2(-S, -S * 0.75),
				Vector2(S * 2.0, S * 1.3)), GLYPH, false, LW)
			on.draw_line(at + Vector2(-S + 1.0, -S * 0.2),
				at + Vector2(S - 1.0, -S * 0.2), GLYPH, 1.0, true)
			on.draw_circle(at + Vector2(-S * 0.45, S * 0.75), 1.1, GLYPH, true, -1.0, true)
			on.draw_circle(at + Vector2(S * 0.45, S * 0.75), 1.1, GLYPH, true, -1.0, true)
		"scrapyard":                                  # a crane and its hook
			on.draw_line(at + Vector2(-S * 0.3, S), at + Vector2(-S * 0.3, -S), GLYPH, LW, true)
			on.draw_line(at + Vector2(-S, -S), at + Vector2(S, -S), GLYPH, LW, true)
			on.draw_line(at + Vector2(S * 0.6, -S), at + Vector2(S * 0.6, S * 0.2), GLYPH, 1.0, true)
			on.draw_arc(at + Vector2(S * 0.6, S * 0.45), 1.5, PI, TAU + 0.7, 10, GLYPH, 1.0, true)
		"warehouse":                                  # a shed with a chimney
			on.draw_rect(Rect2(at + Vector2(-S, 0.0), Vector2(S * 2.0, S)), GLYPH, false, LW)
			on.draw_line(at + Vector2(-S, 0.0), at + Vector2(0.0, -S * 0.85), GLYPH, LW, true)
			on.draw_line(at + Vector2(S, 0.0), at + Vector2(0.0, -S * 0.85), GLYPH, LW, true)
			on.draw_line(at + Vector2(S * 0.5, -S * 0.42), at + Vector2(S * 0.5, -S * 1.3),
				GLYPH, LW, true)
		"playground":                                 # a swing
			on.draw_line(at + Vector2(-S, S), at + Vector2(0.0, -S), GLYPH, LW, true)
			on.draw_line(at + Vector2(S, S), at + Vector2(0.0, -S), GLYPH, LW, true)
			on.draw_line(at + Vector2(-S * 0.6, -S * 0.1), at + Vector2(S * 0.6, -S * 0.1),
				GLYPH, 1.0, true)
			on.draw_line(at + Vector2(S * 0.2, -S * 0.1), at + Vector2(S * 0.2, S * 0.55),
				GLYPH, 1.0, true)
			on.draw_line(at + Vector2(S * 0.55, S * 0.55), at + Vector2(-S * 0.15, S * 0.55),
				GLYPH, LW, true)
		"comms":                                      # a mast, still blinking
			on.draw_line(at + Vector2(-S * 0.7, S), at + Vector2(0.0, -S), GLYPH, LW, true)
			on.draw_line(at + Vector2(S * 0.7, S), at + Vector2(0.0, -S), GLYPH, LW, true)
			on.draw_line(at + Vector2(-S * 0.45, S * 0.3), at + Vector2(S * 0.45, S * 0.3),
				GLYPH, 1.0, true)
			on.draw_arc(at + Vector2(0.0, -S), 2.6, PI * 1.15, PI * 1.85, 8, GLYPH, 1.0, true)
			on.draw_arc(at + Vector2(0.0, -S), 4.0, PI * 1.2, PI * 1.8, 8, GLYPH, 1.0, true)
		"toll gate":                                  # the boom across the road
			on.draw_line(at + Vector2(-S * 0.8, S), at + Vector2(-S * 0.8, -S * 0.5),
				GLYPH, LW, true)
			on.draw_line(at + Vector2(-S * 0.8, -S * 0.3), at + Vector2(S, S * 0.5),
				GLYPH, LW, true)
			on.draw_line(at + Vector2(-S * 1.3, S), at + Vector2(-S * 0.3, S), GLYPH, LW, true)
		"safehouse":                                  # home
			on.draw_line(at + Vector2(-S, 0.0), at + Vector2(0.0, -S), ME, LW, true)
			on.draw_line(at + Vector2(S, 0.0), at + Vector2(0.0, -S), ME, LW, true)
			on.draw_rect(Rect2(at + Vector2(-S * 0.7, 0.0),
				Vector2(S * 1.4, S * 0.9)), ME, false, LW)
			on.draw_rect(Rect2(at + Vector2(-S * 0.2, S * 0.3),
				Vector2(S * 0.45, S * 0.6)), ME, false, 1.0)
		"lz":                                         # the landing pad: an H
			on.draw_arc(at, S * 0.95, 0.0, TAU, 22, GLYPH, LW, true)
			on.draw_line(at + Vector2(-S * 0.4, -S * 0.5), at + Vector2(-S * 0.4, S * 0.5),
				GLYPH, LW, true)
			on.draw_line(at + Vector2(S * 0.4, -S * 0.5), at + Vector2(S * 0.4, S * 0.5),
				GLYPH, LW, true)
			on.draw_line(at + Vector2(-S * 0.4, 0.0), at + Vector2(S * 0.4, 0.0), GLYPH, LW, true)
		"school":                                     # a schoolhouse bell
			on.draw_rect(Rect2(at + Vector2(-S, -S * 0.2),
				Vector2(S * 2.0, S * 1.1)), GLYPH, false, LW)
			on.draw_line(at + Vector2(-S, -S * 0.2), at + Vector2(0.0, -S * 0.9), GLYPH, LW, true)
			on.draw_line(at + Vector2(S, -S * 0.2), at + Vector2(0.0, -S * 0.9), GLYPH, LW, true)
			on.draw_arc(at + Vector2(0.0, -S * 0.95), 1.5, PI, TAU, 8, GLYPH, LW, true)
		"courtyard":                                  # the dry fountain
			on.draw_arc(at, S * 0.9, 0.0, TAU, 22, GLYPH, LW, true)
			on.draw_arc(at, S * 0.35, 0.0, TAU, 12, GLYPH, 1.0, true)
			on.draw_line(at + Vector2(0.0, -S * 0.35), at + Vector2(0.0, -S * 0.95),
				GLYPH, 1.0, true)
		"trainyard":                                  # a boxcar on rails
			on.draw_rect(Rect2(at + Vector2(-S, -S * 0.8),
				Vector2(S * 2.0, S * 1.2)), GLYPH, false, LW)
			on.draw_line(at + Vector2(-S, S * 0.85), at + Vector2(S, S * 0.85), GLYPH, 1.0, true)
			on.draw_circle(at + Vector2(-S * 0.45, S * 0.5), 1.0, GLYPH, true, -1.0, true)
			on.draw_circle(at + Vector2(S * 0.45, S * 0.5), 1.0, GLYPH, true, -1.0, true)
		"gallery":                                    # a framed picture
			on.draw_rect(Rect2(at + Vector2(-S * 0.9, -S * 0.8),
				Vector2(S * 1.8, S * 1.6)), GLYPH, false, LW)
			on.draw_line(at + Vector2(-S * 0.6, S * 0.5), at + Vector2(-S * 0.05, -S * 0.3),
				GLYPH, 1.0, true)
			on.draw_line(at + Vector2(-S * 0.05, -S * 0.3), at + Vector2(S * 0.6, S * 0.5),
				GLYPH, 1.0, true)
		_:
			# anything without its own symbol still gets a surveyor's mark
			# rather than nothing — a ringed dot reads as "a place".
			on.draw_circle(at, 1.6, GLYPH, true, -1.0, true)
			on.draw_arc(at, S * 0.75, 0.0, TAU, 16, GLYPH, 1.0, true)


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
					Color(HALO.r, HALO.g, HALO.b, 0.9))
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
	# A HALO instead of a label box, so type stays legible over a road, a wood
	# or a rooftop without cutting a rectangle out of the map.
	#
	# THE HALO FOLLOWS THE SHEET, and it has now flipped twice: dark while the
	# map was dark, pale for the paper chart, dark again now the ground is
	# terrain. If the sheet ever changes tone again, this flips with it — a
	# pale halo on a dark map turns the type to mud, and the reverse.
	for off in [Vector2(-1, 0), Vector2(1, 0), Vector2(0, -1), Vector2(0, 1),
			Vector2(-1, -1), Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1)]:
		on.draw_string(_font, pos + off, text, HORIZONTAL_ALIGNMENT_LEFT, -1,
			_font_size, Color(HALO.r, HALO.g, HALO.b, 0.92))
	on.draw_string(_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1,
		_font_size, col)
