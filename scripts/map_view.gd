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
# MATCHES THE WORLD'S DIRT. v0.6.58 moved the ground off Apollo's red ramp
# because it read as wine rather than earth; this was left behind on the old
# value, so the map and the world disagreed about what dirt looks like. Brown
# needs GREEN above BLUE - see make_floor_tile's dirt branch.
const DIRT := Color("7a4841")                    # yards, unmade ground
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
# the baked map's own geometry, taken from world_info so this screen can never
# disagree with the texture it is drawing
var _bake_size := Vector2.ZERO
var _bake_lo := 0.0
var _bake_n := 1.0
var _bake_top := 0.0
var _bake_hw := 8.0
var _bake_hh := 4.0
var _icons: Dictionary = {}                # poi name -> Texture2D


func setup(info: Dictionary, player: Player, environment: Node,
		floor_layer: TileMapLayer) -> void:
	_player = player
	_environment = environment
	_floor_layer = floor_layer
	# THE PAINTED ISO BAKE, not the 1px-per-cell sheet. `map_image` is still
	# published and still feeds the menu's map-select tile; this screen draws
	# the bake and its own live overlays on top.
	var map_image: Image = info.get("map_iso", info["map_image"])
	_map_tex = ImageTexture.create_from_image(map_image)
	_bake_size = Vector2(map_image.get_width(), map_image.get_height())
	_bake_lo = float(info.get("map_bake_lo", 0))
	_bake_n = float(info.get("map_bake_span", 1))
	_bake_top = float(info.get("map_bake_top", 0))
	var tile: Array = info.get("map_iso_tile", [16, 8])
	_bake_hw = float(tile[0]) * 0.5
	_bake_hh = float(tile[1]) * 0.5
	_vec = info.get("map_vec", {})
	var theme := UITheme.get_theme()
	_font = theme.default_font
	if theme.has_default_font_size():
		_font_size = theme.default_font_size
	var tiny := load("res://art/gen/spoils_tiny.fnt")
	if tiny != null:
		_tiny_font = tiny
	_build_poi_list(info)
	for poi in _pois:
		var icon_name := str(poi["name"])
		if _icons.has(icon_name):
			continue
		var tex: Texture2D = load("res://art/gen/map_icon_%s.png"
			% icon_name.replace(" ", "_"))
		if tex != null:
			_icons[icon_name] = tex
	layer = 75
	visible = false
	_build_ui()


func _playable() -> Rect2:
	## IN BAKE PIXELS, not cells — `_zoom` scales the painted texture now, so
	## everything that frames or clamps the view has to speak the same units.
	if _bake_size == Vector2.ZERO:
		var inset := float(WorldBuilder.BARRIER_INSET)
		return Rect2(inset, inset,
			float(WorldBuilder.MAP_W) - inset * 2.0,
			float(WorldBuilder.MAP_H) - inset * 2.0)
	return Rect2(Vector2.ZERO, _bake_size)


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
		var rects: Array = zones.get(zone_name, []) as Array
		# EVERY PLACE GETS A MARKER (user: "all icons on each POI"). These four
		# were the ones with a bare word and nothing else. A zone can repeat
		# over several rects and a marker on each would carpet the map, so only
		# the LARGEST rect of a zone carries one — the rest keep just the name.
		var best := -1
		var best_area := -1.0
		for i in rects.size():
			var rr: Array = rects[i]
			var area := float(rr[2]) * float(rr[3])
			if area > best_area:
				best_area = area
				best = i
		for i in rects.size():
			var r: Array = rects[i]
			_pois.append({"name": zone_name,
				"rect": Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
				"blurb": blurbs.get(zone_name, zone_name), "label": true,
				"glyph": i == best})


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
	# the bake is PIXEL ART and lands near 1:1 — smoothing it would blur every
	# painted edge the map screen exists to show
	_canvas.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
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
	# ---- the chrome, ALL OF IT DOWN ONE SIDE -----------------------------
	# User: "make sure no text is overlapping, like the 'drag to pan , wheel to
	# zoom, press m to close, weather, district stuff isnt anywhere on the map,
	# make it on the side somewhere". It was scattered: the controls hint sat
	# ON the map's bottom-right corner and the clock floated loose in a margin.
	#
	# The projection is what makes this free. A diamond in a rectangle leaves
	# four empty triangles, and the left one is dead space that no longer has to
	# be wasted — the chrome stops being an overlay and becomes the frame.
	var side := VBoxContainer.new()
	side.position = Vector2(10, 38)
	side.custom_minimum_size = Vector2(190, 0)
	side.size = Vector2(190, 0)
	side.add_theme_constant_override("separation", 6)
	side.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_transit_root.add_child(side)
	var district_tag := Label.new()
	district_tag.text = "district: transit"
	district_tag.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	district_tag.mouse_filter = Control.MOUSE_FILTER_IGNORE
	side.add_child(district_tag)
	_status = Label.new()
	_status.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	side.add_child(_status)
	_hint = Label.new()
	_hint.text = "drag to pan\nwheel to zoom\npress m to close"
	_hint.custom_minimum_size = Vector2(190, 0)
	_hint.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	side.add_child(_hint)

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
		_pan = _canvas.size * 0.5 - _cell_to_bake(cell) * _zoom
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


func _cell_to_bake(cell: Vector2) -> Vector2:
	## Cell space -> pixels in the baked texture, in the GAME'S projection. This
	## is the same arithmetic `_map_iso_px` uses in world_builder, written
	## continuously so a fractional cell lands where you would expect: an
	## integer cell gives its tile's top vertex and (cx+0.5, cy+0.5) its centre.
	##
	## IT MUST NOT BE RE-DERIVED FROM CONSTANTS HERE. Every number comes from
	## world_info, so retuning the tile size or the bake window cannot slide the
	## markers off the painting they sit on.
	return Vector2((cell.x - cell.y) * _bake_hw + (_bake_n - 1.0) * _bake_hw
			+ _bake_hw,
		(cell.x + cell.y - 2.0 * _bake_lo) * _bake_hh + _bake_top)


func _cell_to_screen(cell: Vector2) -> Vector2:
	return _pan + _cell_to_bake(cell) * _zoom


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
	if _map_tex == null:
		return
	# ONE BLIT. The district is a PAINTED TEXTURE, baked once at deploy — see
	# world_builder._bake_map_iso. This function used to rebuild the district
	# from vector shapes on every pan and every zoom step, and that is precisely
	# what capped it at flat fills and wobbled polygons: hundreds of draw calls
	# per frame leave no budget for surface detail. It is why "all the roads are
	# just like look all the same, just pure white with some border theres like
	# nothing to it" was true however many road colours were defined here.
	#
	# Everything still drawn live sits on TOP of this: markers, labels, icons and
	# the player, none of which can be baked because they move.
	_canvas.draw_texture_rect(_map_tex, Rect2(_pan, _bake_size * _zoom), false)
	# ...and the place markers on top of it. These belong to the STATIC layer,
	# not to `_markers`: they only move when you pan or zoom, while `_markers`
	# redraws every frame to follow the player.
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


func _wobble(r: Rect2, key: int, amp: float) -> PackedVector2Array:
	## A rect's outline with a HASHED wander on it, so a block or a yard is not
	## a perfect rectangle on the map (user: "i dont want to see any square
	## stuff", "i dont just want my whole game to look square").
	##
	## Hashed off the rect and the point index, never rolled: this redraws on
	## every pan, so anything random would crawl while you dragged the map.
	## Points are laid along each side rather than at the corners only, or the
	## shape stays a quadrilateral and just leans.
	var pts := PackedVector2Array()
	var per := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
	var steps := 5
	for side in 4:
		var a: Vector2 = per[side]
		var b: Vector2 = per[(side + 1) % 4]
		for i in steps:
			var f := float(i) / float(steps)
			var u: Vector2 = a.lerp(b, f)
			var h: int = absi(int(key) ^ (side * 73856093) ^ (i * 19349663))
			var ox := (float(h & 255) / 255.0 - 0.5) * 2.0 * amp
			var oy := (float((h >> 8) & 255) / 255.0 - 0.5) * 2.0 * amp
			pts.append(Vector2(r.position.x + u.x * r.size.x + ox,
				r.position.y + u.y * r.size.y + oy))
	return pts


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
	## ONE HAND-PAINTED MARKER PER PLACE (user, 2026-08-08: "all icons on each
	## POI"). This drew vector arcs and strokes before; every marker is now a
	## painted 20x20 plaque from `art/gen/map_icon_*.png`, made in gen_art with
	## the rest of the art and in the Apollo palette.
	##
	## FIXED PIXEL SIZE on purpose — a map symbol does not grow when you zoom,
	## and these have to stay readable at whole-district zoom, which is where the
	## map opens.
	##
	## THE PLAQUE BORDER IS COLOURED BY WHAT THE PLACE IS FOR: green means you
	## can leave from here, red is home, grey is somewhere to go. That is legible
	## before a single word is read.
	var tex: Texture2D = _icons.get(name)
	if tex == null:
		return
	var size := Vector2(tex.get_width(), tex.get_height())
	# a soft drop shadow, so a marker survives landing on pale road or bright roof
	on.draw_rect(Rect2((at - size * 0.5 + Vector2(1.0, 2.0)).round(), size),
		Color(0.035, 0.04, 0.08, 0.5), true)
	on.draw_texture_rect(tex, Rect2((at - size * 0.5).round(), size), false)


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
		var drop := 16.0 if has_glyph else float(_font_size) * 0.5
		var pos := (centre + Vector2(-tw * 0.5, drop)).round()
		# NOTHING HANGS OFF THE EDGE (user: "the toll gate extraction icon and
		# text isnt inside of the map, make sure everythign is inside"). The
		# toll gate sits hard against the south edge, and a label was placed
		# straight off its cell with no regard for its own width. Clamp both the
		# name and the marker into the canvas.
		var map_rect := Rect2(_pan, _bake_size * _zoom)
		var lim := map_rect.intersection(Rect2(Vector2.ZERO, _canvas.size))
		if lim.size.x > tw + 8.0 and lim.size.y > float(_font_size) * 3.0:
			pos.x = clampf(pos.x, lim.position.x + 3.0,
				lim.end.x - tw - 3.0)
			pos.y = clampf(pos.y, lim.position.y + float(_font_size) + 2.0,
				lim.end.y - 3.0)
			centre.x = clampf(centre.x, lim.position.x + 11.0, lim.end.x - 11.0)
			centre.y = clampf(centre.y, lim.position.y + 11.0,
				lim.end.y - float(_font_size) - 14.0)
			pos = pos.round()
		var bounds := Rect2(pos - Vector2(3.0, float(_font_size)),
			Vector2(tw + 6.0, float(_font_size) + 4.0))
		if has_glyph:
			# the symbol is part of what must not be landed on, or a
			# neighbour's name prints straight through it
			bounds = bounds.merge(Rect2(centre - Vector2(11.0, 11.0),
				Vector2(22.0, 22.0)))
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
