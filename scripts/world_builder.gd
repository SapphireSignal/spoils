class_name WorldBuilder
extends RefCounted
## Builds the raid map: a 320x320 ruined district. Deterministic per seed.
## Consumes art/gen/manifest.json — sprite sizes, origins, colliders and
## variant families all come from the art pipeline.
##
## Layout is PLANNED first (roads, forests, dirt paths, building plots), then
## painted and populated. The map is a true iso diamond and is walkable to its
## real edge: the border collision hugs the diamond (tips chamfered just
## enough that the camera can always keep the player on screen), and the
## camera itself is clamped to an inset diamond so the void outside the tiles
## can never be seen. The last stretch before the edge is sniper country —
## the EdgeGuard handles that.
##
## build() is a COROUTINE: it yields to the render loop while it works, so
## the deploy screen keeps animating and no frame ever hitches, no matter how
## big the district gets.

const MAP_W := 256
const MAP_H := 256
const TILE := Vector2i(64, 32)
const EDGE_FOREST := 85      # content margin: gameplay stays inside the
                             # treeline fringe (inset 78..85, inside the ring)
const BARRIER_INSET := 78    # the barricade ring — the map's ADVERTISED edge.
# v0.6.19: nudged in again ("just make the map a bit smaller again") —
# playable diamond ~100 cells now.
# v0.6.18: the district shrank AGAIN ("way smaller, its still huge" — user,
# third time) — total map 320 -> 256 and the ring pulled to 68, leaving a
# ~120-cell playable diamond, under half the old area. What's left is now
# ZONED into distinct places (town / forest / warehouses / school /
# trainyard / bus depot / courtyard / comms relay) instead of a uniform
# sprawl. The 68-cell band beyond the ring stays sniper country, deep
# enough that ignoring the warning kills you long before the camera —
# which never clamps — could reach the void.
const ROAD_COUNT := 4        # per axis
const LAMP_WORKING_CHANCE := 0.42  # the district is dead; most lamps are too
const BUILD_BUDGET_US := 2400  # max build work per frame: the deploy screen
                               # must hold the user's full refresh rate
# border collision at the true diamond edge (an absolute backstop; the
# sniper is the real wall). Tips chamfered a little for good measure.
const TIP_CUT_X := 560.0
const TIP_CUT_Y := 256.0
# THE district (user call 2026-08-01: procedural rerolls are OFF — one
# fixed, learnable transit layout, because quests will point at real
# addresses and players must be able to remember where everything is).
# Change ONLY as a deliberate map revision; harness --seed still
# overrides for tests. Picked by auditioning candidates in v0.6.22.
const DISTRICT_SEED := "transit-01"

var _rng := RandomNumberGenerator.new()
var _manifest: Dictionary = {}
var _floor_coords: Dictionary = {}
var _families: Dictionary = {}
var _wall_h := 40
var _story_h := 32
var _floor_layer: TileMapLayer
var _ysort: Node2D
var _roofs: Array[RoofReveal] = []
var _occupied: Dictionary = {}
var _scene_tree: SceneTree
var _deadline_us := 0

# plan state
var _roads_v: Array[Vector2i] = []   # (x_start, width)
var _roads_h: Array[Vector2i] = []
var _forest: Dictionary = {}         # Vector2i -> true
var _dirt_path: Dictionary = {}
var _plots: Array[Dictionary] = []   # {rect, kind, style, tone, ruined, door_side, door_out}
var _yards: Array[Rect2i] = []
var _spawn_cell := Vector2i(160, 160)
var _puddle_spots: Array[Vector2] = []
var _alarm_cars: Array[Dictionary] = []  # {node, lights} — armed intact cars
var _sidewalk: Dictionary = {}       # cell -> "v"/"h" (walkways flanking roads)
var _traffic_cells: Array[Vector2i] = []
var _zone_salt := 0                  # per-build salt for the weathering zones
var _bush_nodes: Array[Node2D] = []  # registered with the Foliage manager
var _fog_spots := PackedVector2Array()   # dawn-fog anchors (woods + roads)
var _leaf_trees := PackedVector2Array()  # green shedder canopies
var _leaf_trees_red := PackedVector2Array()  # the autumn grove's shedders
var _autumn_rect := Rect2i()             # east half of the woods turns

# zoning (v0.6.18): the district is PLACES now, not sprawl
var _zones: Dictionary = {}          # block Vector2i(bx,by) -> zone name
var _block_rects: Dictionary = {}    # block -> Rect2i of interior cells
var _plaza: Dictionary = {}          # cell -> true (courtyard pavers)
var _apron: Dictionary = {}          # cell -> true (bus depot asphalt)
var _rail_cells: Dictionary = {}     # cell -> "x"/"y" (rail over ballast)
var _ballast: Dictionary = {}        # cell -> true (gravel shoulders)
var _rail_cross: Dictionary = {}     # cell -> "x"/"y" (rails let into roads)
var _rail_row := -1                  # main-line row (rails run along +x)
var _sidings: Array = []             # arrays of siding cells (trainyard)
var _court_rect := Rect2i()          # the courtyard plaza
var _depot_rect := Rect2i()          # the bus depot apron
var _school_rect := Rect2i()         # the school building
var _playground := Rect2i()          # the schoolyard
var _comms_rect := Rect2i()          # the relay compound
var _gallery_rect := Rect2i()        # the graffiti gallery corner
var _scrap_rect := Rect2i()          # the scrapyard block
var _map_marks: Array = []           # [cell, kind] static marks for the map
var _map_trees: Array[Vector3i] = [] # (x, y, autumn) — every planted tree,
                                     # so the baked map shows the woods
var _lz_rect := Rect2i()             # the lift's clearing
var _toll_gate: Node2D = null        # the warden's crossing
var _toll_cell := Vector2i.ZERO
var _freight_cell := Vector2i.ZERO   # where the night freight stands
var _extracts: Array[Dictionary] = []  # ways out, handed to Extraction
var _window_cells: Dictionary = {}   # (x, y, side_id) -> true where a wall
                                     # segment carries glass
const _EDGE_SIDE_IDS := {"yp": 0, "yn": 1, "xp": 2, "xn": 3}
var _spark_house := -1               # which house got the broken power box
var _safehouse_rect := Rect2i()      # the spawn safehouse
var _uppers: Array[Dictionary] = []  # second-story registries for main.gd
var _cars: Array[Dictionary] = []    # driveable car records for main.gd


func build(root: Node2D, seed_text: String = "") -> Dictionary:
	# ONE canonical district every deploy (fixed-map call, v0.6.22) —
	# ALL randomness below flows from _rng, so the layout is bit-identical
	# every time. Harness --seed=x still swaps worlds for testing.
	if seed_text.is_empty():
		seed_text = DISTRICT_SEED
	_rng.seed = hash(seed_text)
	_scene_tree = root.get_tree()
	_deadline_us = Time.get_ticks_usec() + BUILD_BUDGET_US
	_manifest = _load_manifest()

	_floor_layer = TileMapLayer.new()
	_floor_layer.name = "Floor"
	_floor_layer.tile_set = _make_tileset()
	root.add_child(_floor_layer)

	_ysort = Node2D.new()
	_ysort.name = "World"
	_ysort.y_sort_enabled = true
	root.add_child(_ysort)

	_zone_salt = _rng.randi()
	_plan_roads()
	_plan_zones()
	await _plan_forest()
	_plan_paths()
	_plan_rail()
	_plan_sidewalks()
	await _plan_plots()

	await _paint_terrain()
	for plot in _plots:
		await _build_shell(plot)
	await _place_yards()
	await _place_courtyard()
	await _place_trainyard()
	await _place_depot()
	await _place_comms()
	await _place_safehouse_ring()
	await _place_gallery()
	await _place_lz()
	await _place_scrapyard()
	await _place_power_boxes()
	await _place_school_grounds()
	await _place_lamps()
	await _place_traffic_lights()
	await _place_street_furniture()
	await _place_barricades()
	await _place_trees()
	await _place_lone_trees()
	await _place_road_vehicles()
	await _scatter_props()
	await _place_foliage()
	await _fill_dead_spots()
	_collect_puddle_spots()
	_collect_fog_spots()
	_build_border_collision(root)

	var spawn := _floor_layer.map_to_local(_spawn_cell)
	var top_c := _floor_layer.map_to_local(Vector2i(0, 0)) + Vector2(0, -16)
	var bottom_c := _floor_layer.map_to_local(Vector2i(MAP_W - 1, MAP_H - 1)) + Vector2(0, 16)
	return {
		"ysort": _ysort,
		"floor": _floor_layer,
		"spawn": spawn,
		"map_rect": _map_rect(),
		"map_center": (top_c + bottom_c) / 2.0,
		# f-metric value of the barricade ring (|dx|/2 + |dy| from center);
		# crossing it puts you in sniper country
		"barrier_f": 32.0 * ((float(MAP_W) - 1.0) * 0.5 - float(BARRIER_INSET)),
		"roofs": _roofs,
		"cells": Vector2i(MAP_W, MAP_H),
		"puddle_spots": _puddle_spots,
		"floor_coords": _floor_coords,
		"alarm_cars": _alarm_cars,
		"traffic_cells": _traffic_cells,
		"bushes": _bush_nodes,
		"walk_cells": _sidewalk.size(),
		"fog_spots": _fog_spots,
		"leaf_trees": _leaf_trees,
		"leaf_trees_red": _leaf_trees_red,
		"uppers": _uppers,
		"cars": _cars,
		"zones": _zone_summary(),
		"story_h": _story_h,
		"map_image": _bake_map_image(),
		"map_vec": _map_vectors(),
		"poi": {
			"court": [_court_rect.position.x, _court_rect.position.y,
				_court_rect.size.x, _court_rect.size.y],
			"depot": [_depot_rect.position.x, _depot_rect.position.y,
				_depot_rect.size.x, _depot_rect.size.y],
			"school": [_school_rect.position.x, _school_rect.position.y,
				_school_rect.size.x, _school_rect.size.y],
			"playground": [_playground.position.x, _playground.position.y,
				_playground.size.x, _playground.size.y],
			"comms": [_comms_rect.position.x, _comms_rect.position.y,
				_comms_rect.size.x, _comms_rect.size.y],
			"gallery": [_gallery_rect.position.x, _gallery_rect.position.y,
				_gallery_rect.size.x, _gallery_rect.size.y],
			"scrapyard": [_scrap_rect.position.x, _scrap_rect.position.y,
				_scrap_rect.size.x, _scrap_rect.size.y],
			"safehouse": [_safehouse_rect.position.x, _safehouse_rect.position.y,
				_safehouse_rect.size.x, _safehouse_rect.size.y],
			"lz": [_lz_rect.position.x, _lz_rect.position.y,
				_lz_rect.size.x, _lz_rect.size.y],
			"toll gate": [_toll_cell.x - 2, _toll_cell.y - 2, 5, 5],
			"rail_row": _rail_row,
		},
		"extracts": _extracts,
		"toll_gate": _toll_gate,
		# where the freight stands: the trainyard's stretch of the main line
		"freight_stop": _floor_layer.map_to_local(_freight_cell),
	}


func _tick() -> void:
	# time-budgeted yielding: the moment this frame's build budget is spent,
	# hand the frame back — fixed work-counts per frame caused visible fps
	# dips on the deploy screen
	if Time.get_ticks_usec() >= _deadline_us:
		await _scene_tree.process_frame
		_deadline_us = Time.get_ticks_usec() + BUILD_BUDGET_US


func _cell_inset(cell: Vector2i) -> int:
	# distance (in cells) from the nearest true map edge
	return mini(mini(cell.x, MAP_W - 1 - cell.x), mini(cell.y, MAP_H - 1 - cell.y))


func _map_rect() -> Rect2:
	var min_x := _floor_layer.map_to_local(Vector2i(0, MAP_H - 1)).x - 32.0
	var max_x := _floor_layer.map_to_local(Vector2i(MAP_W - 1, 0)).x + 32.0
	var min_y := _floor_layer.map_to_local(Vector2i(0, 0)).y - 16.0
	var max_y := _floor_layer.map_to_local(Vector2i(MAP_W - 1, MAP_H - 1)).y + 16.0
	return Rect2(min_x, min_y, max_x - min_x, max_y - min_y)


func _load_manifest() -> Dictionary:
	var file := FileAccess.open("res://art/gen/manifest.json", FileAccess.READ)
	assert(file != null, "art/gen/manifest.json missing — run tools/gen_art.py")
	var data: Dictionary = JSON.parse_string(file.get_as_text())
	_floor_coords = data["floors"]
	_families = data["families"]
	_wall_h = int(data["wall_h"])
	_story_h = int(data.get("story_h", 32))
	return data


func _make_tileset() -> TileSet:
	var ts := TileSet.new()
	ts.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	ts.tile_layout = TileSet.TILE_LAYOUT_DIAMOND_DOWN
	ts.tile_size = TILE
	var src := TileSetAtlasSource.new()
	src.texture = load("res://art/gen/floors.png")
	src.texture_region_size = TILE
	for tile_name in _floor_coords:
		var tc: Array = _floor_coords[tile_name]
		src.create_tile(Vector2i(int(tc[0]), int(tc[1])))
	ts.add_source(src, 0)
	return ts


# ---------------------------------------------------------------- plan -------

func _plan_roads() -> void:
	# roads live INSIDE the district: the outermost ones stay clear of the
	# barricade ring (a jittered road could land parallel along the line).
	# Jitter is small now: the 3x3 blocks between roads ARE the districts,
	# and a squeezed block can't hold its place (the one-door map bug).
	var lo := BARRIER_INSET + 8
	var span := MAP_W - 2 * lo
	for i in ROAD_COUNT:
		@warning_ignore("integer_division")
		var base := lo + span * i / (ROAD_COUNT - 1)
		_roads_v.append(Vector2i(clampi(base + _rng.randi_range(-4, 4),
			lo - 2, MAP_W - lo - 2), 4))
	for i in ROAD_COUNT:
		@warning_ignore("integer_division")
		var base := lo + span * i / (ROAD_COUNT - 1)
		_roads_h.append(Vector2i(clampi(base + _rng.randi_range(-4, 4),
			lo - 2, MAP_H - lo - 2), 4))


func _road_v_at(cell: Vector2i) -> int:
	for r in _roads_v:
		if cell.x >= r.x and cell.x < r.x + r.y:
			return r.x
	return -1


func _road_h_at(cell: Vector2i) -> int:
	for r in _roads_h:
		if cell.y >= r.x and cell.y < r.x + r.y:
			return r.x
	return -1


func _on_road(cell: Vector2i) -> bool:
	return _road_v_at(cell) >= 0 or _road_h_at(cell) >= 0


func _plan_zones() -> void:
	# v0.6.18: carve the 3x3 grid of blocks between the roads and deal out
	# the PLACES — a two-block town, a two-block forest, one block each for
	# the warehouses, the school, the trainyard and the bus depot; the last
	# block stays open with the comms relay in one corner. Every district
	# now has an address ("the stuff in our map is like all scattered
	# around theres like no distinct locations" — user).
	for by in ROAD_COUNT - 1:
		for bx in ROAD_COUNT - 1:
			var x0: int = _roads_v[bx].x + _roads_v[bx].y + 2
			var x1: int = _roads_v[bx + 1].x - 2
			var y0: int = _roads_h[by].x + _roads_h[by].y + 2
			var y1: int = _roads_h[by + 1].x - 2
			_block_rects[Vector2i(bx, by)] = Rect2i(x0, y0, x1 - x0, y1 - y0)
	var order: Array = _block_rects.keys()
	_shuffle(order)
	var town_a: Vector2i = order[0]
	var town_b := Vector2i(-1, -1)
	for cand in order:
		if cand != town_a and (cand - town_a as Vector2i).length_squared() == 1:
			town_b = cand
			break
	_zones[town_a] = "town"
	_zones[town_b] = "town"
	var rest: Array = []
	for b in order:
		if b != town_a and b != town_b:
			rest.append(b)
	# forest went 2 blocks -> 1 (denser instead) to make room for the
	# SCRAPYARD (user request); the open block hosts the comms relay in one
	# corner and the little graffiti gallery in another
	var deals := ["forest", "warehouse", "school", "trainyard",
		"depot", "scrapyard", "open"]
	for i in rest.size():
		_zones[rest[i]] = deals[mini(i, deals.size() - 1)]


func _zone_blocks(zone: String) -> Array:
	var out: Array = []
	for b in _zones:
		if _zones[b] == zone:
			out.append(b)
	return out


func _zone_summary() -> Dictionary:
	# probe food: zone name -> [block rects] so shots can aim at places
	var out: Dictionary = {}
	for b in _zones:
		var r: Rect2i = _block_rects[b]
		var key: String = _zones[b]
		var entry: Array = out.get(key, [])
		entry.append([r.position.x, r.position.y, r.size.x, r.size.y])
		out[key] = entry
	return out


func _next_to_road(cell: Vector2i) -> bool:
	# grass may NEVER touch asphalt (user call) — sidewalks or concrete
	# always sit between them
	for off in [Vector2i.ZERO, Vector2i.RIGHT, Vector2i.LEFT, Vector2i.UP, Vector2i.DOWN]:
		if _on_road(cell + off):
			return true
	return false


func _plan_forest() -> void:
	# The WOODS are a place now: the two forest blocks fill with real tree
	# cover. A blobby treeline fringe still hugs the inside of the ring, and
	# a few stray groves land anywhere (the randomness the user asked to
	# keep). Grass never grows against asphalt (_next_to_road guard).
	var blobs: Array[Vector3i] = []
	for i in 90:   # fringe clumps hugging the inside of the ring
		var inset := BARRIER_INSET + _rng.randi_range(0, 6)
		var along := _rng.randi_range(BARRIER_INSET, MAP_W - 1 - BARRIER_INSET)
		var seed_cell := Vector2i(along, inset)
		match _rng.randi_range(0, 3):
			1: seed_cell = Vector2i(along, MAP_H - 1 - inset)
			2: seed_cell = Vector2i(inset, along)
			3: seed_cell = Vector2i(MAP_W - 1 - inset, along)
		blobs.append(Vector3i(_rng.randi_range(6, 18), seed_cell.x, seed_cell.y))
	for b in _zone_blocks("forest"):   # the forest district proper (ONE
		# block since the scrapyard arrived - so it packs DENSER)
		var r: Rect2i = _block_rects[b]
		for i in 8:
			blobs.append(Vector3i(int(r.get_area() * 0.20),
				_rng.randi_range(r.position.x + 2, r.end.x - 3),
				_rng.randi_range(r.position.y + 2, r.end.y - 3)))
	for i in 14:   # stray groves — min size 5 so grass never spawns lonely
		blobs.append(Vector3i(_rng.randi_range(5, 12),
			_rng.randi_range(EDGE_FOREST + 6, MAP_W - EDGE_FOREST - 6),
			_rng.randi_range(EDGE_FOREST + 6, MAP_H - EDGE_FOREST - 6)))
	for blob in blobs:
		var cx := blob.y
		var cy := blob.z
		if _on_road(Vector2i(cx, cy)):
			continue
		var target := blob.x
		var frontier: Array[Vector2i] = [Vector2i(cx, cy)]
		var grown := 0
		while grown < target and not frontier.is_empty():
			var cell: Vector2i = frontier.pop_at(_rng.randi_range(0, frontier.size() - 1))
			if _forest.has(cell) or _next_to_road(cell):
				continue
			if _cell_inset(cell) < BARRIER_INSET:
				continue  # the woods stop AT the line — never leak into the buffer
			if cell.x < 4 or cell.y < 4 or cell.x >= MAP_W - 4 or cell.y >= MAP_H - 4:
				continue
			_forest[cell] = true
			grown += 1
			for off in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
				if _rng.randf() < 0.8:
					frontier.append(cell + off)
		await _tick()


func _plan_paths() -> void:
	# dirt roads wandering from the road grid into the woods
	for i in 5:
		var road: Vector2i = _roads_v[_rng.randi_range(0, _roads_v.size() - 1)]
		var y := _rng.randi_range(EDGE_FOREST + 4, MAP_H - EDGE_FOREST - 4)
		var x := road.x + road.y
		var dir := 1 if _rng.randf() < 0.5 else -1
		if dir < 0:
			x = road.x - 1
		var length := _rng.randi_range(24, 70)
		for step in length:
			for w in 2:
				_dirt_path[Vector2i(clampi(x, 1, MAP_W - 2), clampi(y + w, 1, MAP_H - 2))] = true
			x += dir
			if _rng.randf() < 0.35:
				y += _rng.randi_range(-1, 1)


func _plan_rail() -> void:
	# ONE main line crosses the whole district through the trainyard block —
	# level crossings where it meets roads — plus short parallel sidings
	# inside the yard for the rolling stock. Cells only; props come later.
	var yard_blocks := _zone_blocks("trainyard")
	if yard_blocks.is_empty():
		return
	var r: Rect2i = _block_rects[yard_blocks[0]]
	_rail_row = r.position.y + r.size.y / 2 + _rng.randi_range(-2, 2)
	# the freight stands mid-yard, where the platform would have been
	_freight_cell = Vector2i(r.position.x + r.size.x / 2, _rail_row)
	for x in range(BARRIER_INSET - 2, MAP_W - BARRIER_INSET + 2):
		var cell := Vector2i(x, _rail_row)
		if _on_road(cell):
			_rail_cross[cell] = "x"
			continue
		_rail_cells[cell] = "x"
		_forest.erase(cell)
		for dy in [-1, 1]:
			var shoulder := Vector2i(x, _rail_row + dy)
			if not _on_road(shoulder):
				_ballast[shoulder] = true
				_forest.erase(shoulder)
	# sidings on the deeper side of the yard
	var side := 1 if r.get_center().y > _rail_row else -1
	var count := _rng.randi_range(2, 3)
	for s in count:
		var srow: int = _rail_row + side * (4 + s * 3)
		if srow <= r.position.y or srow >= r.end.y:
			continue
		var length := _rng.randi_range(12, mini(18, r.size.x - 4))
		var sx := r.position.x + _rng.randi_range(1, maxi(1, r.size.x - length - 2))
		var cells: Array[Vector2i] = []
		for x in range(sx, sx + length):
			var cell := Vector2i(x, srow)
			if _on_road(cell):
				continue
			_rail_cells[cell] = "x"
			_forest.erase(cell)
			cells.append(cell)
			for dy in [-1, 1]:
				var shoulder := Vector2i(x, srow + dy)
				if not _on_road(shoulder) and not _rail_cells.has(shoulder):
					_ballast[shoulder] = true
					_forest.erase(shoulder)
		if not cells.is_empty():
			_sidings.append(cells)


func _plan_sidewalks() -> void:
	# walkways flank EVERY road side now (user: grass right next to the
	# road looks odd — a slab band always separates them). Wear comes from
	# the broken tiles, not gaps; a sidewalk even EVICTS forest cells,
	# because the slabs were poured first and the green came later.
	for r in _roads_v:
		for side_x in [r.x - 1, r.x + r.y]:
			for y in range(BARRIER_INSET, MAP_H - BARRIER_INSET):
				var cell := Vector2i(side_x, y)
				if _on_road(cell) or _dirt_path.has(cell) \
						or _rail_cells.has(cell) or _ballast.has(cell) \
						or _rail_cross.has(cell):
					continue
				_forest.erase(cell)
				_sidewalk[cell] = "v"
	for r in _roads_h:
		for side_y in [r.x - 1, r.x + r.y]:
			for x in range(BARRIER_INSET, MAP_W - BARRIER_INSET):
				var cell := Vector2i(x, side_y)
				if _on_road(cell) or _dirt_path.has(cell) \
						or _rail_cells.has(cell) or _ballast.has(cell) \
						or _rail_cross.has(cell) or _sidewalk.has(cell):
					continue
				_forest.erase(cell)
				_sidewalk[cell] = "h"


func _crosswalk_at(cell: Vector2i, road_v: int, road_h: int) -> String:
	# zebra tiles on the road arms right before a crossing
	if road_v >= 0 and road_h < 0:
		for r in _roads_h:
			if cell.y == r.x - 1 or cell.y == r.x + r.y:
				return "v"
	elif road_h >= 0 and road_v < 0:
		for r in _roads_v:
			if cell.x == r.x - 1 or cell.x == r.x + r.y:
				return "h"
	return ""


func _plan_plots() -> void:
	# buildings live where their zone says: houses pack the TOWN blocks
	# around the courtyard, the industrial halls own the WAREHOUSE block,
	# the SCHOOL gets its two-story building over a playground half, and
	# the DEPOT block reserves its bus apron. No more uniform sprawl.
	_plan_safehouse()
	var court_placed := false
	for b in _zones:
		match _zones[b]:
			"town":
				await _plan_town_block(b, not court_placed)
				court_placed = true
			"warehouse":
				await _plan_warehouse_block(b)
			"scrapyard":
				await _plan_scrap_hall(b)
			"school":
				_plan_school_block(b)
			"depot":
				_plan_depot_block(b)
			"forest":
				_plan_comms_corner(b)
			"open":
				_plan_gallery_corner(b)
	# GUARANTEE upstairs homes: a fixed district must always hold real
	# two-story houses — the 45% dice CAN roll a bungalow-only town, and
	# with one permanent map that would be forever (it nearly was)
	var two_story := 0
	var upgrade_candidates: Array[int] = []
	for i in _plots.size():
		var story_plot: Dictionary = _plots[i]
		if story_plot["kind"] == "house" and not story_plot.get("safehouse", false):
			if int(story_plot["stories"]) == 2:
				two_story += 1
			elif not bool(story_plot["ruined"]):
				upgrade_candidates.append(i)
	_shuffle(upgrade_candidates)
	while two_story < 4 and not upgrade_candidates.is_empty():
		_plots[upgrade_candidates.pop_back()]["stories"] = 2
		two_story += 1
	# one house per district gets the sparking power box (quest fodder)
	var house_indices: Array[int] = []
	for i in _plots.size():
		if _plots[i]["kind"] == "house":
			house_indices.append(i)
	if not house_indices.is_empty():
		_spark_house = house_indices[_rng.randi_range(0, house_indices.size() - 1)]
	# every plot rolls its door NOW so the village paths can find them
	for plot in _plots:
		var interior: Rect2i = (plot["rect"] as Rect2i).grow(-1)
		var cell := _roll_door_cell(interior, plot["door_side"])
		plot["door_cell"] = cell
		plot["door_out"] = cell + (_DOOR_OUTWARD[plot["door_side"]] as Vector2i) * 2
	_plan_house_paths()
	# spawn: INSIDE the safehouse, dead center, every raid (user call — the
	# roaming spawn once put them behind a bookshelf)
	_spawn_cell = _safehouse_rect.grow(-1).get_center()


func _plan_house_paths() -> void:
	# worn dirt paths connect the houses to each other and the courtyard
	# (user request). They SKIP roads, sidewalks and plazas — the trail
	# pauses at the slabs and picks up on the far side.
	var stops: Array[Vector2i] = []
	for plot in _plots:
		if plot["kind"] == "house":
			stops.append(plot["door_out"])
	if stops.is_empty():
		return
	stops.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		return (a.x + a.y) < (b.x + b.y))
	if _court_rect.size.x > 0:
		stops.insert(stops.size() / 2,
			Vector2i(_court_rect.get_center().x, _court_rect.end.y + 1))
	for i in range(stops.size() - 1):
		_walk_dirt_path(stops[i], stops[i + 1])


func _walk_dirt_path(from: Vector2i, to: Vector2i) -> void:
	# a NARROW wobbly walk from door to door — a worn trail, not a mud
	# river (the 2-wide first cut braided into highways)
	var cell := from
	var guard := 0
	while cell != to and guard < 400:
		guard += 1
		var step := Vector2i.ZERO
		if cell.x != to.x and (cell.y == to.y or _rng.randf() < 0.55):
			step.x = signi(to.x - cell.x)
		else:
			step.y = signi(to.y - cell.y)
		if _rng.randf() < 0.10:            # the wobble, gentle
			step = Vector2i(step.y, step.x)
		cell += step
		if cell.x < 4 or cell.y < 4 or cell.x >= MAP_W - 4 or cell.y >= MAP_H - 4:
			return
		if _on_road(cell) or _sidewalk.has(cell) or _plaza.has(cell) \
				or _apron.has(cell) or _rail_cells.has(cell) \
				or _ballast.has(cell) or _rail_cross.has(cell) \
				or _forest.has(cell):
			continue                   # skip the slabs; resume past them
		if _court_rect.has_point(cell) or _comms_rect.has_point(cell) \
				or _gallery_rect.has_point(cell) or _playground.has_point(cell) \
				or _scrap_rect.has_point(cell):
			continue                   # trails go AROUND the places
		var inside_plot := false
		for plot in _plots:
			if (plot["rect"] as Rect2i).has_point(cell):
				inside_plot = true
				break
		if not inside_plot:
			_dirt_path[cell] = true


func _plan_safehouse() -> void:
	# the SAFEHOUSE: the same squat house near the map's south edge every
	# raid, ringed with barriers — where every deploy begins
	var size := Vector2i(7, 6)
	# just NORTH of the southmost road: "near the bottom" without landing
	# on the road band or its sidewalks (the first probe row did exactly
	# that and thirty x-shifts never escaped it)
	var base_y: int = _roads_h[ROAD_COUNT - 1].x - size.y - 4
	var base_x: int = MAP_W / 2
	var placed := false
	for probe in 240:
		var dx := ((probe % 30) / 2 + 1) * (1 if probe % 2 == 0 else -1) * 2
		var dy := -3 * (probe / 30)   # climb north band by band — a rail
		var pos := Vector2i(base_x + dx - size.x / 2, base_y + dy)
		var rect := Rect2i(pos, size)  # line can cross several of them
		var blocked := false
		for y in range(rect.position.y - 2, rect.end.y + 3):
			for x in range(rect.position.x - 2, rect.end.x + 3):
				var cell := Vector2i(x, y)
				if _on_road(cell) or _rail_cells.has(cell) \
						or _ballast.has(cell) or _sidewalk.has(cell) \
						or _plaza.has(cell) or _apron.has(cell):
					blocked = true
					break
			if blocked:
				break
		if blocked:
			continue
		if _comms_rect.grow(2).intersects(rect) \
				or _gallery_rect.grow(2).intersects(rect) \
				or _depot_rect.grow(2).intersects(rect) \
				or _court_rect.grow(2).intersects(rect):
			continue
		_claim_building_ground(rect.grow(2))
		_safehouse_rect = rect
		_plots.append({
			"rect": rect, "kind": "house",
			"style": "brick_b",
			"tone": "pitch",
			"ruined": false,
			"stories": 1,
			"safehouse": true,
			"door_side": "yp",
			"door_out": Vector2i(-99, -99),
		})
		placed = true
		break
	if not placed:
		# exhaustive sweep: walk north row by row, first clear slot wins —
		# a seed once landed rail+court+depot across every probe band and
		# left the spawn at the map corner (sniper country)
		var y := base_y
		while not placed and y > BARRIER_INSET + 6:
			var x := BARRIER_INSET + 4
			while not placed and x < MAP_W - BARRIER_INSET - size.x - 4:
				var rect := Rect2i(Vector2i(x, y), size)
				var blocked := false
				for sy in range(rect.position.y - 2, rect.end.y + 3):
					for sx in range(rect.position.x - 2, rect.end.x + 3):
						var cell := Vector2i(sx, sy)
						if _on_road(cell) or _rail_cells.has(cell) 								or _ballast.has(cell) or _sidewalk.has(cell) 								or _plaza.has(cell) or _apron.has(cell):
							blocked = true
							break
					if blocked:
						break
				if not blocked:
					_claim_building_ground(rect.grow(2))
					_safehouse_rect = rect
					_plots.append({
						"rect": rect, "kind": "house",
						"style": "brick_b", "tone": "pitch",
						"ruined": false, "stories": 1, "safehouse": true,
						"door_side": "yp", "door_out": Vector2i(-99, -99),
					})
					placed = true
				x += 3
			y -= 3


func _place_safehouse_ring() -> void:
	# barriers and pylons around the spawn house; the door side stays open
	if _safehouse_rect.size.x == 0:
		return
	var ring := _safehouse_rect.grow(2)
	var door_out := Vector2i(-99, -99)
	for plot in _plots:
		if plot.get("safehouse", false):
			door_out = plot["door_out"]
	# SPARSER ring (user: "we dont need that many"): every third cell,
	# corners pinned by the pillars — reads guarded, not caged
	for x in range(ring.position.x, ring.end.x, 3):
		await _tick()
		if absi(x - door_out.x) > 2:
			_fence_piece(Vector2i(x, ring.position.y), "x")
		if absi(x - door_out.x) > 2 or ring.end.y - 1 != door_out.y + 1:
			_fence_piece(Vector2i(x, ring.end.y - 1), "x")
	for y in range(ring.position.y + 1, ring.end.y - 1, 3):
		await _tick()
		_fence_piece(Vector2i(ring.position.x, y), "y")
		_fence_piece(Vector2i(ring.end.x - 1, y), "y")
	for corner in [ring.position, Vector2i(ring.end.x - 1, ring.position.y),
			Vector2i(ring.position.x, ring.end.y - 1), ring.end - Vector2i(1, 1)]:
		if not _occupied.has(corner):
			_add_prop_at_cell("pillar_%d" % _rng.randi_range(0, 1), corner,
				Vector2(3, 2))
	# the parking pad (user request): a small asphalt apron with a stall
	# line and one car off the ring — east side first, west as fallback.
	# The pad car never arms its alarm; it reads as YOURS.
	var pad := Rect2i(ring.end.x + 1, ring.position.y + 2, 4, 4)
	if not _pad_clear(pad):
		pad.position.x = ring.position.x - 5
	if _pad_clear(pad):
		for y in range(pad.position.y, pad.end.y):
			for x in range(pad.position.x, pad.end.x):
				var pcell := Vector2i(x, y)
				if x - pad.position.x == 1 and y < pad.end.y - 1:
					_set_tile(pcell, "asphalt_stall")
				else:
					_set_tile(pcell, "asphalt_%d" % _rng.randi_range(0, 1))
		var pad_fam := "vehicle_ne" if pad.position.x > ring.end.x \
			else "vehicle_nw"
		var pad_variant := _pick_variant(pad_fam)
		var pad_pos := _floor_layer.map_to_local(Vector2i(
			pad.position.x + 1, pad.position.y + 1)) + Vector2(
			_rng.randf_range(-3.0, 3.0), _rng.randf_range(-2.0, 2.0))
		if pad_variant.ends_with("_5") or pad_variant.ends_with("_6"):
			_add_prop(pad_variant, pad_pos)
		else:
			_spawn_driveable(pad_variant,
				pad_fam.trim_prefix("vehicle_"), pad_pos)
		for y in range(pad.position.y, pad.end.y):
			for x in range(pad.position.x, pad.end.x):
				_occupied[Vector2i(x, y)] = true
		_map_marks.append([pad.get_center(), "car"])


func _pad_clear(pad: Rect2i) -> bool:
	# a parking pad needs honest ground: no roads, rails, walks, woods,
	# claimed cells, or another plot breathing on it
	for y in range(pad.position.y, pad.end.y):
		for x in range(pad.position.x, pad.end.x):
			var cell := Vector2i(x, y)
			if _on_road(cell) or _rail_cells.has(cell) or _ballast.has(cell) \
					or _sidewalk.has(cell) or _plaza.has(cell) \
					or _apron.has(cell) or _occupied.has(cell) \
					or _forest.has(cell):
				return false
	for plot in _plots:
		if (plot["rect"] as Rect2i).grow(1).intersects(pad):
			return false
	return true


func _plan_town_block(b: Vector2i, with_court: bool) -> void:
	var r: Rect2i = _block_rects[b]
	if with_court:
		# the courtyard: a paved plaza in the middle of the first town block,
		# sized so houses still fit AROUND it
		var cw := clampi(r.size.x - 14, 9, 12)
		var ch := clampi(r.size.y - 14, 9, 12)
		_court_rect = Rect2i(r.position + (r.size - Vector2i(cw, ch)) / 2,
			Vector2i(cw, ch))
		for y in range(_court_rect.position.y, _court_rect.end.y):
			for x in range(_court_rect.position.x, _court_rect.end.x):
				var cell := Vector2i(x, y)
				_plaza[cell] = true
				_forest.erase(cell)
	var placed := 0
	var attempts := 0
	while placed < 8 and attempts < 320:
		attempts += 1
		await _tick()
		var size := Vector2i(_rng.randi_range(6, 8), _rng.randi_range(5, 7))
		if size.x > r.size.x - 2 or size.y > r.size.y - 2:
			continue
		var pos := Vector2i(
			_rng.randi_range(r.position.x, r.end.x - size.x),
			_rng.randi_range(r.position.y, r.end.y - size.y))
		var rect := Rect2i(pos, size)
		if with_court and rect.grow(1).intersects(_court_rect):
			continue
		if not _rect_clear(rect.grow(1)):
			continue
		_plots.append({
			"rect": rect, "kind": "house",
			"style": "brick_a" if _rng.randf() < 0.5 else "brick_b",
			"tone": "charcoal" if _rng.randf() < 0.5 else "pitch",
			"ruined": _rng.randf() < 0.14,
			"stories": 2 if _rng.randf() < 0.45 else 1,
			"door_side": "xp" if _rng.randf() < 0.5 else "yp",
			"door_out": Vector2i(-99, -99),
		})
		placed += 1


func _plan_warehouse_block(b: Vector2i) -> void:
	# the hall is the POINT of this block: placement is GUARANTEED. A dirt
	# trail is no reason not to build (the slab just covers it), and if the
	# rolls all fail, the hall goes down at the block's center anyway —
	# racks in the open with no warehouse was the bug the user screenshotted.
	var r: Rect2i = _block_rects[b]
	var placed := 0
	var attempts := 0
	while placed < 2 and attempts < 240:
		attempts += 1
		await _tick()
		var size := Vector2i(
			_rng.randi_range(12, maxi(12, mini(17, r.size.x - 4))),
			_rng.randi_range(8, maxi(8, mini(12, r.size.y - 4))))
		if size.x > r.size.x - 2 or size.y > r.size.y - 2:
			continue
		var pos := Vector2i(
			_rng.randi_range(r.position.x, r.end.x - size.x),
			_rng.randi_range(r.position.y, r.end.y - size.y))
		var rect := Rect2i(pos, size)
		if not _rect_clear_for_building(rect.grow(2)):
			continue
		_claim_building_ground(rect)
		_plots.append({
			"rect": rect, "kind": "warehouse",
			"style": "brick_a" if _rng.randf() < 0.5 else "brick_b",
			"tone": "charcoal" if _rng.randf() < 0.5 else "pitch",
			"ruined": _rng.randf() < 0.35,
			"stories": 1,
			"door_side": "xp" if _rng.randf() < 0.5 else "yp",
			"door_out": Vector2i(-99, -99),
		})
		placed += 1
	if placed == 0:
		var size := Vector2i(mini(13, r.size.x - 2), mini(9, r.size.y - 2))
		var pos := r.position + (r.size - size) / 2
		if _rail_row >= r.position.y - 2 and _rail_row <= r.end.y + 2:
			# dodge the rail line if it cuts this block
			if _rail_row <= r.get_center().y:
				pos.y = mini(r.end.y - size.y, _rail_row + 3)
			else:
				pos.y = maxi(r.position.y, _rail_row - size.y - 3)
		var rect := Rect2i(pos, size)
		_claim_building_ground(rect)
		_plots.append({
			"rect": rect, "kind": "warehouse",
			"style": "brick_b",
			"tone": "pitch",
			"ruined": false,
			"stories": 1,
			"door_side": "yp",
			"door_out": Vector2i(-99, -99),
		})


func _plan_scrap_hall(b: Vector2i) -> void:
	# the yard's own hall (user: racks and boxes in the open read wrong —
	# "i know there used to be one there"). ONE modest warehouse anchors
	# the scrapyard, GUARANTEED, in the south half so the rack line out
	# front becomes its overflow storage.
	var r: Rect2i = _block_rects[b]
	var attempts := 0
	while attempts < 200:
		attempts += 1
		await _tick()
		var size := Vector2i(
			_rng.randi_range(11, maxi(11, mini(14, r.size.x - 6))),
			_rng.randi_range(7, maxi(7, mini(9, (r.size.y / 2) - 2))))
		if size.x > r.size.x - 2 or size.y > r.size.y - 2:
			continue
		var lo_y := maxi(r.position.y, r.end.y - size.y - 5)
		var pos := Vector2i(
			_rng.randi_range(r.position.x + 1,
				maxi(r.position.x + 1, r.end.x - size.x - 1)),
			_rng.randi_range(lo_y, maxi(lo_y, r.end.y - size.y - 3)))
		var rect := Rect2i(pos, size)
		if not _rect_clear_for_building(rect.grow(2)):
			continue
		_claim_building_ground(rect)
		_plots.append({
			"rect": rect, "kind": "warehouse",
			"style": "brick_a" if _rng.randf() < 0.5 else "brick_b",
			"tone": "charcoal" if _rng.randf() < 0.5 else "pitch",
			"ruined": false,
			"stories": 1,
			"door_side": "yp",
			"door_out": Vector2i(-99, -99),
		})
		return
	# Every roll failed. The hall is GUARANTEED — the whole reason it
	# exists is that racks and crates in the open with no warehouse was a
	# bug the user reported (v0.6.22), and skipping it brought that bug
	# straight back. So: walk the block for a rail-free slot, and if the
	# full footprint won't fit between the rail and the block edge, keep
	# SHRINKING it until something does. A smaller hall is a building; no
	# hall is the old bug.
	for size in [Vector2i(12, 8), Vector2i(11, 7), Vector2i(10, 6),
			Vector2i(9, 6), Vector2i(8, 5), Vector2i(7, 5), Vector2i(6, 4)]:
		if size.x > r.size.x - 2 or size.y > r.size.y - 2:
			continue
		for y in range(r.position.y, r.end.y - size.y + 1):
			await _tick()
			for x in range(r.position.x, r.end.x - size.x + 1):
				var cand := Rect2i(Vector2i(x, y), size)
				if _rect_rail_free(cand.grow(1)) \
						and _rect_clear_for_building(cand):
					_claim_building_ground(cand)
					_plots.append({
						"rect": cand, "kind": "warehouse",
						"style": "brick_b", "tone": "charcoal",
						"ruined": false, "stories": 1, "door_side": "yp",
						"door_out": Vector2i(-99, -99),
					})
					return
	# the block is genuinely impossible (rail + sidings + roads across all
	# of it): put the hall in the trainyard's spare corner rather than
	# leave the yard's stock standing in the open
	push_warning("scrapyard hall: block unusable, falling back to a corner")
	var last := Vector2i(6, 4)
	for y in range(r.position.y, r.end.y - last.y + 1):
		for x in range(r.position.x, r.end.x - last.x + 1):
			var spot := Rect2i(Vector2i(x, y), last)
			if _rect_rail_free(spot):
				_claim_building_ground(spot)
				_plots.append({
					"rect": spot, "kind": "warehouse",
					"style": "brick_b", "tone": "charcoal", "ruined": false,
					"stories": 1, "door_side": "yp",
					"door_out": Vector2i(-99, -99),
				})
				return


func _rect_rail_free(rect: Rect2i) -> bool:
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var cell := Vector2i(x, y)
			if _rail_cells.has(cell) or _ballast.has(cell) \
					or _rail_cross.has(cell):
				return false
	return true


func _rect_clear_for_building(rect: Rect2i) -> bool:
	# like _rect_clear but dirt trails don't block — the building just
	# covers them (they get erased at claim time)
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var cell := Vector2i(x, y)
			if _on_road(cell) or _forest.has(cell) \
					or _rail_cells.has(cell) or _ballast.has(cell) \
					or _plaza.has(cell) or _apron.has(cell) \
					or _sidewalk.has(cell):
				return false
	for plot in _plots:
		if (plot["rect"] as Rect2i).grow(2).intersects(rect):
			return false
	for yard in _yards:
		if yard.grow(2).intersects(rect):
			return false
	return true


func _claim_building_ground(rect: Rect2i) -> void:
	# the slab wins: trails and stray green under a footprint get erased
	for y in range(rect.position.y - 1, rect.end.y + 1):
		for x in range(rect.position.x - 1, rect.end.x + 1):
			var cell := Vector2i(x, y)
			_dirt_path.erase(cell)
			_forest.erase(cell)


func _plan_school_block(b: Vector2i) -> void:
	# the school: one big two-story building on the block's north half,
	# the playground on the south half (quest country, someday soon)
	var r: Rect2i = _block_rects[b]
	var size := Vector2i(mini(14, maxi(10, r.size.x - 8)),
		mini(9, maxi(7, (r.size.y - 6) / 2)))
	var pos := Vector2i(r.position.x + (r.size.x - size.x) / 2, r.position.y + 1)
	_school_rect = Rect2i(pos, size)
	for y in range(_school_rect.position.y, _school_rect.end.y):
		for x in range(_school_rect.position.x, _school_rect.end.x):
			_forest.erase(Vector2i(x, y))
	_plots.append({
		"rect": _school_rect, "kind": "school",
		"style": "brick_a",
		"tone": "charcoal" if _rng.randf() < 0.5 else "pitch",
		"ruined": false,
		"stories": 2,
		"door_side": "yp",   # faces the playground, camera-visible
		"door_out": Vector2i(-99, -99),
	})
	var py := _school_rect.end.y + 3
	_playground = Rect2i(r.position.x + 2, py, r.size.x - 4,
		maxi(6, r.end.y - py - 1))


func _plan_depot_block(b: Vector2i) -> void:
	# the bus depot: an asphalt apron hugging the block's south road
	var r: Rect2i = _block_rects[b]
	var aw := mini(18, maxi(12, r.size.x - 4))
	var ah := mini(9, maxi(7, r.size.y / 2))
	var pos := Vector2i(r.position.x + (r.size.x - aw) / 2, r.end.y - ah)
	_depot_rect = Rect2i(pos, Vector2i(aw, ah))
	for y in range(_depot_rect.position.y, _depot_rect.end.y):
		for x in range(_depot_rect.position.x, _depot_rect.end.x):
			var cell := Vector2i(x, y)
			if not _rail_cells.has(cell) and not _ballast.has(cell):
				_apron[cell] = true
				_forest.erase(cell)


func _plan_comms_corner(b: Vector2i) -> void:
	# (the same forest block also donates its EAST half to autumn)
	var forest_r: Rect2i = _block_rects[b]
	_autumn_rect = Rect2i(
		Vector2i(forest_r.get_center().x, forest_r.position.y - 2),
		Vector2i(forest_r.end.x - forest_r.get_center().x + 3,
			forest_r.size.y + 4))
	# the relay lives at the WOODS' edge now (user: "near some empty space
	# ... by some trees at least") — a clearing carved from a forest-block
	# corner, trees crowding its fence
	var r: Rect2i = _block_rects[b]
	var cw := mini(9, r.size.x - 3)
	var ch := mini(9, r.size.y - 3)
	var corner := _rng.randi_range(0, 3)
	var pos := r.position + Vector2i(1, 1)
	match corner:
		1: pos = Vector2i(r.end.x - cw - 1, r.position.y + 1)
		2: pos = Vector2i(r.position.x + 1, r.end.y - ch - 1)
		3: pos = Vector2i(r.end.x - cw - 1, r.end.y - ch - 1)
	_comms_rect = Rect2i(pos, Vector2i(cw, ch))
	for y in range(_comms_rect.position.y, _comms_rect.end.y):
		for x in range(_comms_rect.position.x, _comms_rect.end.x):
			_forest.erase(Vector2i(x, y))


func _plan_gallery_corner(b: Vector2i) -> void:
	# the gallery keeps a corner of the open block
	var r: Rect2i = _block_rects[b]
	var gw := mini(10, r.size.x - 3)
	var gh := mini(8, r.size.y - 3)
	var corner := _rng.randi_range(0, 3)
	var gpos := r.position + Vector2i(1, 1)
	match corner:
		1: gpos = Vector2i(r.end.x - gw - 1, r.position.y + 1)
		2: gpos = Vector2i(r.position.x + 1, r.end.y - gh - 1)
		3: gpos = Vector2i(r.end.x - gw - 1, r.end.y - gh - 1)
	_gallery_rect = Rect2i(gpos, Vector2i(gw, gh))
	for y in range(_gallery_rect.position.y, _gallery_rect.end.y):
		for x in range(_gallery_rect.position.x, _gallery_rect.end.x):
			_forest.erase(Vector2i(x, y))


func _rect_clear(rect: Rect2i) -> bool:
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var cell := Vector2i(x, y)
			if _on_road(cell) or _forest.has(cell) or _dirt_path.has(cell) \
					or _rail_cells.has(cell) or _ballast.has(cell) \
					or _plaza.has(cell) or _apron.has(cell) \
					or _sidewalk.has(cell):
				return false
	for plot in _plots:
		if (plot["rect"] as Rect2i).grow(3).intersects(rect):
			return false
	for yard in _yards:
		if yard.grow(2).intersects(rect):
			return false
	return true


# ------------------------------------------------------------- terrain ------

func _paint_terrain() -> void:
	for y in MAP_H:
		for x in MAP_W:
			var cell := Vector2i(x, y)
			var tile_name := "concrete_%d" % _rng.randi_range(0, 5)
			# district-scale weathering: two offset 8-cell hash grids AND-ed
			# together bias whole blocks lighter (sun-bleached) or darker
			# (damp/mossy), with a probabilistic mix so zone borders dissolve
			# as grain instead of reading as an aligned patch grid
			var zone := posmod(hash(Vector3i(cell.x >> 3, cell.y >> 3, _zone_salt)), 100)
			var zone2 := posmod(hash(Vector3i((cell.x + 4) >> 3, (cell.y + 4) >> 3,
				_zone_salt ^ 0x5bd1)), 100)
			if zone < 24 and zone2 < 60 and _rng.randf() < 0.6:
				tile_name = "concrete_worn_%d" % _rng.randi_range(0, 2)
			elif zone >= 76 and zone2 >= 40 and _rng.randf() < 0.6:
				tile_name = "concrete_damp_%d" % _rng.randi_range(0, 2)
			var roll := _rng.randf()
			if roll < 0.03:
				tile_name = "crack_%d" % _rng.randi_range(0, 3)
			elif roll < 0.045:
				tile_name = "stain_%d" % _rng.randi_range(0, 2)
			elif roll < 0.055:
				tile_name = "moss_%d" % _rng.randi_range(0, 1)
			var is_forest := _forest.has(cell)
			var is_dirt := _dirt_path.has(cell)
			if is_forest:
				tile_name = "forest_%d" % _rng.randi_range(0, 3)
			if is_dirt:
				tile_name = "dirt_%d" % _rng.randi_range(0, 3)
			var road_v := _road_v_at(cell)
			var road_h := _road_h_at(cell)
			# roads DEAD-END at the barricade line: the buffer beyond is bare
			# district, so the stubs stop under the wreckage (user call)
			if _rail_cross.has(cell) and _cell_inset(cell) >= BARRIER_INSET - 2:
				tile_name = "rail_cross_%s" % str(_rail_cross[cell])
			elif _rail_cells.has(cell) and _cell_inset(cell) >= BARRIER_INSET - 2:
				# the track wears in STRETCHES, not per tile: a run of
				# overgrown, a run of rusted, then clean again. Per-cell
				# rolls would read as noise instead of neglect.
				var axis := str(_rail_cells[cell])
				var run := posmod(hash(Vector3i((cell.x + cell.y) / 7,
					0, _zone_salt)), 100)
				if run < 26:
					tile_name = "rail_%s_weeds" % axis
				elif run < 40:
					tile_name = "rail_%s_rust" % axis
				else:
					tile_name = "rail_%s" % axis
			elif _ballast.has(cell) and _cell_inset(cell) >= BARRIER_INSET - 2:
				tile_name = "ballast_%d" % _rng.randi_range(0, 2)
			elif _plaza.has(cell):
				# courtyard pavers: mostly clean, the odd cracked slab
				tile_name = "plaza_2" if _rng.randf() < 0.12 \
					else "plaza_%d" % _rng.randi_range(0, 1)
			elif _apron.has(cell):
				# depot apron: plain asphalt with its own wear
				var apron_roll := _rng.randf()
				if apron_roll < 0.045:
					tile_name = "asphalt_crack_%d" % _rng.randi_range(0, 1)
				elif apron_roll < 0.065:
					tile_name = "asphalt_hole_%d" % _rng.randi_range(0, 1)
				else:
					tile_name = "asphalt_%d" % _rng.randi_range(0, 1)
			elif (road_v >= 0 or road_h >= 0) and _cell_inset(cell) >= BARRIER_INSET - 2:
				tile_name = "asphalt_%d" % _rng.randi_range(0, 1)
				var cw := _crosswalk_at(cell, road_v, road_h)
				# crosswalks at the crossings, center dashes elsewhere (on
				# BOTH road directions, never at crossings), the odd manhole.
				# The dash is TWO half-tiles sharing the middle boundary of
				# the 4-wide road, so the painted line sits on its true
				# center (user: "the yellow line seems a bit off")
				if cw != "":
					tile_name = "crosswalk_%s" % cw
				elif road_v >= 0 and road_h < 0 and (cell.x == road_v + 1 \
						or cell.x == road_v + 2) and _dash_here(cell.y, road_v):
					tile_name = "asphalt_line" if cell.x == road_v + 1 \
						else "asphalt_line_b"
				elif road_h >= 0 and road_v < 0 and (cell.y == road_h + 1 \
						or cell.y == road_h + 2) and _dash_here(cell.x, road_h):
					tile_name = "asphalt_line_h" if cell.y == road_h + 1 \
						else "asphalt_line_h_b"
				elif _rng.randf() < 0.006:
					tile_name = "manhole_0"
				elif _rng.randf() < 0.045:
					tile_name = "asphalt_crack_%d" % _rng.randi_range(0, 1)
				elif _rng.randf() < 0.02:
					tile_name = "asphalt_hole_%d" % _rng.randi_range(0, 1)
			elif _sidewalk.has(cell) and not is_forest \
					and _cell_inset(cell) >= BARRIER_INSET - 2:
				# sidewalks BEAT dirt trails (a trail used to paint straight
				# across the slabs — the "overlapping road" screenshot)
				# walkway slabs: mostly intact, some cracked open (the broken
				# tile eats through to the dirt and grows weeds)
				var sw_roll := _rng.randf()
				if sw_roll < 0.10:
					tile_name = "sidewalk_%s_broken_%d" % [str(_sidewalk[cell]),
						_rng.randi_range(0, 1)]
				elif sw_roll < 0.26:
					tile_name = "sidewalk_%s_crack_%d" % [str(_sidewalk[cell]),
						_rng.randi_range(0, 1)]
				else:
					tile_name = "sidewalk_%s_0" % str(_sidewalk[cell])
			elif not is_forest and not is_dirt:
				# biome blending: concrete touching grass grows grass; concrete
				# touching a dirt path picks up dirt — no hard tile seams.
				# NEVER against asphalt (user: no grass on intersections)
				if _touches(cell, _forest) and not _next_to_road(cell):
					tile_name = "grass_blend_%d" % _rng.randi_range(0, 2)
				elif _touches(cell, _dirt_path):
					tile_name = "dirt_blend_%d" % _rng.randi_range(0, 2)
			_set_tile(cell, tile_name)
		await _tick()


func _dash_here(along: int, road_pos: int) -> bool:
	# BOTH half-tiles of a center dash exist or neither: the old per-cell
	# rolls left orphan halves reading as off-center dashes (user
	# screenshot). Deterministic per (position, road); gaps stay rare.
	return posmod(hash(Vector3i(along, road_pos, _zone_salt)), 100) < 96


func _touches(cell: Vector2i, field: Dictionary) -> bool:
	return field.has(cell + Vector2i.RIGHT) or field.has(cell + Vector2i.LEFT) \
		or field.has(cell + Vector2i.UP) or field.has(cell + Vector2i.DOWN)


func _set_tile(cell: Vector2i, tile_name: String) -> void:
	var tc: Array = _floor_coords[tile_name]
	_floor_layer.set_cell(cell, 0, Vector2i(int(tc[0]), int(tc[1])))


# ------------------------------------------------------------- props --------

func _prop_sprite(prop_name: String) -> Sprite2D:
	var info: Dictionary = _manifest["props"][prop_name]
	var origin: Array = info["origin"]
	var sprite := Sprite2D.new()
	sprite.texture = load("res://art/gen/%s.png" % prop_name)
	sprite.centered = false
	sprite.offset = Vector2(-float(origin[0]), -float(origin[1]))
	return sprite


func _add_prop(prop_name: String, pos: Vector2) -> Node2D:
	var info: Dictionary = _manifest["props"][prop_name]
	var collider: Variant = info["collider"]
	var node: Node2D
	if collider == null:
		node = Node2D.new()
	else:
		var body := StaticBody2D.new()
		var spec: Array = collider
		var shape_kind: String = spec[0]
		if shape_kind == "diamond":
			var poly := CollisionPolygon2D.new()
			poly.polygon = PackedVector2Array([
				Vector2(0, -float(spec[2])), Vector2(float(spec[1]), 0),
				Vector2(0, float(spec[2])), Vector2(-float(spec[1]), 0)])
			body.add_child(poly)
		elif shape_kind == "poly":
			var flat: Array = spec[1]
			var points := PackedVector2Array()
			for i in range(0, flat.size(), 2):
				points.append(Vector2(float(flat[i]), float(flat[i + 1])))
			var poly2 := CollisionPolygon2D.new()
			poly2.polygon = points
			body.add_child(poly2)
		else:
			var cs := CollisionShape2D.new()
			var circle := CircleShape2D.new()
			circle.radius = float(spec[1])
			cs.shape = circle
			body.add_child(cs)
		node = body
	# whole-pixel positions ALWAYS: at native-res rendering a static prop on a
	# half pixel would sit off the world's pixel grid
	node.position = pos.round()
	node.add_child(_prop_sprite(prop_name))
	_ysort.add_child(node)
	return node


func _add_prop_at_cell(prop_name: String, cell: Vector2i,
		jitter: Vector2 = Vector2.ZERO) -> Node2D:
	var pos := _floor_layer.map_to_local(cell)
	if jitter != Vector2.ZERO:
		pos += Vector2(_rng.randf_range(-jitter.x, jitter.x), _rng.randf_range(-jitter.y, jitter.y))
	var node := _add_prop(prop_name, pos)
	_occupied[cell] = true
	return node


func _maybe_arm_car(variant: String, node: Node2D) -> void:
	# 50/50 on INTACT cars only — broken-into ones were stripped long ago
	if variant.ends_with("_5") or variant.ends_with("_6"):
		return
	if _rng.randf() < 0.5:
		var info: Dictionary = _manifest["props"][variant]
		_alarm_cars.append({"node": node, "lights": info.get("lights", [])})


func _add_door(door_name: String, pos: Vector2) -> void:
	var info: Dictionary = _manifest["props"][door_name]
	var origin: Array = info["origin"]
	var spec: Array = info["collider"]
	var flat: Array = spec[1]
	var points := PackedVector2Array()
	for i in range(0, flat.size(), 2):
		points.append(Vector2(float(flat[i]), float(flat[i + 1])))
	var door := Door.new()
	door.position = pos.round()
	_ysort.add_child(door)
	door.setup(load("res://art/gen/%s.png" % door_name),
		Vector2(float(origin[0]), float(origin[1])), points)


func _pick_variant(family: String) -> String:
	var names: Array = _families[family]
	return names[_rng.randi_range(0, names.size() - 1)]


# ---------------------------------------------------------- clutter ---------
# Breaking visual repetition. NOT procedural generation — the layout is
# fixed and hand-picked (hard rule). This is only about making identical
# objects stop looking stamped: they sit at their own offsets, wear their
# own damage, and pile up unevenly the way dumped things actually do.

var _last_variant: Dictionary = {}   # family -> the variant used last

func _pick_variant_varied(family: String) -> String:
	## Same as _pick_variant, but never hands out the same variant twice
	## running. One repeat in a row is what the eye catches first.
	var names: Array = _families[family]
	if names.size() < 2:
		return names[0]
	var pick: String = names[_rng.randi_range(0, names.size() - 1)]
	if pick == _last_variant.get(family, ""):
		pick = names[(names.find(pick) + 1 + _rng.randi_range(0, names.size() - 2))
			% names.size()]
	_last_variant[family] = pick
	return pick


func _clutter_offset(spread: float = 10.0) -> Vector2:
	## A whole-pixel offset inside a cell. Whole pixels because static props
	## must sit on the world grid (rule 1); the iso floor is twice as wide
	## as it is tall, so the vertical spread is halved to match.
	return Vector2(roundf(_rng.randf_range(-spread, spread)),
		roundf(_rng.randf_range(-spread * 0.5, spread * 0.5)))


func _place_pile(family: String, cell: Vector2i, heap: int,
		spread: float = 13.0) -> void:
	## An ASYMMETRIC pile: one anchor piece, then satellites that fall away
	## from it at a decreasing rate and drift further as they go. Real
	## dumped clutter has a heavy middle and stragglers — never a tidy row,
	## never a ring, and never the same variant beside itself.
	if not _families.has(family):
		return
	var base := _floor_layer.map_to_local(cell)
	_add_prop(_pick_variant_varied(family), base + _clutter_offset(spread * 0.35))
	_occupied[cell] = true
	var lean := Vector2(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0))
	for i in range(1, heap):
		if _rng.randf() > 0.85 - 0.12 * float(i):   # the tail thins out
			break
		# each satellite pushes further along the pile's own lean, so the
		# heap has a direction — the way a load spills off one side
		var reach := spread * (0.5 + 0.42 * float(i))
		var at := base + lean * reach + _clutter_offset(spread * 0.55)
		_add_prop(_pick_variant_varied(family), at)


func _scatter_around(families: Array, cell: Vector2i, count: int,
		spread: float = 22.0) -> void:
	## Loose debris around a landmark: mixed families, uneven spacing, and
	## a bias toward one side so it never reads as a halo.
	var base := _floor_layer.map_to_local(cell)
	var bias := Vector2(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0))
	for i in count:
		var family: String = families[_rng.randi_range(0, families.size() - 1)]
		if not _families.has(family):
			continue
		var at := base + bias * _rng.randf_range(0.0, spread) \
			+ _clutter_offset(spread * 0.7)
		_add_prop(_pick_variant_varied(family), at)


func _take_random_cell(cells: Array[Vector2i]) -> Vector2i:
	var index := _rng.randi_range(0, cells.size() - 1)
	var cell: Vector2i = cells[index]
	cells.remove_at(index)
	return cell


func _shuffle(arr: Array) -> void:
	# Array.shuffle() draws from the GLOBAL rng and silently broke seeded
	# determinism — every shuffle must flow from _rng instead
	for i in range(arr.size() - 1, 0, -1):
		var j := _rng.randi_range(0, i)
		var tmp: Variant = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp


func _near_a_door(cell: Vector2i) -> bool:
	# entrances stay clear: nothing may spawn within 2 cells of any doorway
	for plot in _plots:
		var dout: Vector2i = plot["door_out"]
		if absi(cell.x - dout.x) <= 2 and absi(cell.y - dout.y) <= 2:
			return true
	return false


# ------------------------------------------------------------ buildings -----

const _EDGE_OFFSET := {
	"yp": Vector2(-16, 8), "yn": Vector2(16, -8),
	"xp": Vector2(16, 8), "xn": Vector2(-16, -8),
}
const _EDGE_AXIS := {"yp": "x", "yn": "x", "xp": "y", "xn": "y"}
const _EDGE_VERTS := {
	"yp": [Vector2(-32, 0), Vector2(0, 16)], "yn": [Vector2(32, 0), Vector2(0, -16)],
	"xp": [Vector2(0, 16), Vector2(32, 0)], "xn": [Vector2(0, -16), Vector2(-32, 0)],
}
const _DOOR_INWARD := {"yp": Vector2i(0, -1), "xp": Vector2i(-1, 0)}
const _DOOR_OUTWARD := {"yp": Vector2i(0, 1), "xp": Vector2i(1, 0)}
const _DOOR_ALONG := {"yp": Vector2i(1, 0), "xp": Vector2i(0, 1)}


func _edge_sides(cell: Vector2i, interior: Rect2i) -> Array[String]:
	# which perimeter sides of the interior this cell sits on
	var sides: Array[String] = []
	if cell.x == interior.position.x:
		sides.append("xn")
	if cell.x == interior.end.x - 1:
		sides.append("xp")
	if cell.y == interior.position.y:
		sides.append("yn")
	if cell.y == interior.end.y - 1:
		sides.append("yp")
	return sides


func _roll_door_cell(interior: Rect2i, door_side: String) -> Vector2i:
	var door_cell := Vector2i(
		interior.end.x - 1 if door_side == "xp" else 0,
		interior.end.y - 1 if door_side == "yp" else 0)
	if door_side == "xp":
		door_cell.y = _rng.randi_range(interior.position.y + 1, interior.end.y - 2)
	else:
		door_cell.x = _rng.randi_range(interior.position.x + 1, interior.end.x - 2)
	return door_cell


func _build_shell(plot: Dictionary) -> void:
	var rect: Rect2i = plot["rect"]
	var style: String = plot["style"]
	var kind: String = plot["kind"]
	var stories: int = int(plot.get("stories", 1))
	var ruined: bool = plot["ruined"] and stories == 1  # tall shells stay whole
	var door_side: String = plot["door_side"]
	var interior: Rect2i = rect.grow(-1)
	var ruin_corner: Vector2i = interior.end - Vector2i(1, 1)
	var posts: Dictionary = {}
	# the door cell is rolled at PLAN time now (the house paths need it
	# before terrain paints); legacy fallback for plots without one
	var door_cell: Vector2i = plot.get("door_cell", Vector2i(-99, -99))
	if door_cell.x < -90:
		door_cell = _roll_door_cell(interior, door_side)
	plot["door_out"] = door_cell + (_DOOR_OUTWARD[door_side] as Vector2i) * 2

	# ONE floor for the whole building — per-cell variants made interiors a
	# patchwork of mismatched tiles (user call: uniform flooring per house)
	var floor_tile := ("wood_%d" % _rng.randi_range(0, 4)) if kind == "house" \
		else ("screed_%d" % _rng.randi_range(0, 3))
	var seg_prefix := "seg2" if stories == 2 else "seg"
	var post_prefix := "post2" if stories == 2 else "post"

	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			_occupied[cell] = true
			_set_tile(cell, floor_tile)
			var sides := _edge_sides(cell, interior)
			await _tick()
			for side in sides:
				var center := _floor_layer.map_to_local(cell)
				var verts: Array = _EDGE_VERTS[side]
				if side == door_side and cell == door_cell:
					for v in verts:
						posts[(center + (v as Vector2)).round()] = true
					# a REAL door, closed in the wall plane; F opens it
					var leaf := "wood" if kind == "house" else "metal"
					var axis: String = _EDGE_AXIS[side]
					_add_door("door_%s_%s" % [leaf, axis],
						center + (_EDGE_OFFSET[side] as Vector2))
					if stories == 2:
						# the transom: the upper band still needs its wall
						# (a bare door segment left a hole into the stairwell)
						_add_prop("seg2_%s_%s_upper" % [style, axis],
							center + (_EDGE_OFFSET[side] as Vector2))
					continue
				var axis2: String = _EDGE_AXIS[side]
				# plain segments roll among three variants, weighted to the
				# base look so long walls vary without reading as patchwork
				var seg_roll := _rng.randf()
				var seg_suffix := "" if seg_roll < 0.5 \
					else ("_v1" if seg_roll < 0.75 else "_v2")
				var piece := "%s_%s_%s%s" % [seg_prefix, style, axis2, seg_suffix]
				if ruined and Vector2(cell - ruin_corner).length() < 3.0:
					if _rng.randf() < 0.25:
						for v in verts:
							posts[(center + (v as Vector2)).round()] = true
						continue
					piece = "seg_%s_%s_broken_%d" % [style, axis2, _rng.randi_range(0, 1)]
				elif _rng.randf() < (0.42 if stories == 2 else 0.3):
					piece = "%s_%s_%s_win_%d" % [seg_prefix, style, axis2,
						_rng.randi_range(0, 2)]
					# remember where the glass is: power boxes must never
					# hang under a window (user call)
					_window_cells[Vector3i(cell.x, cell.y,
						(_EDGE_SIDE_IDS[side] as int))] = true
				_add_prop(piece, center + (_EDGE_OFFSET[side] as Vector2))

	var corner_cells := [
		[interior.position, Vector2(0, -16)],
		[Vector2i(interior.end.x - 1, interior.position.y), Vector2(32, 0)],
		[interior.end - Vector2i(1, 1), Vector2(0, 16)],
		[Vector2i(interior.position.x, interior.end.y - 1), Vector2(-32, 0)],
	]
	for entry in corner_cells:
		var pos := _floor_layer.map_to_local(entry[0] as Vector2i) + (entry[1] as Vector2)
		posts[pos.round()] = true
	for pos in posts:
		_add_prop("%s_%s" % [post_prefix, style], pos as Vector2)

	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			_occupied[Vector2i(x, y)] = true

	await _build_roof(interior, plot["tone"], posts.keys(), ruined,
		_wall_h + (_story_h if stories == 2 else 0))

	# the entrance pocket: the door cell and everything around it stays empty
	var pocket: Array[Vector2i] = [door_cell]
	var inward: Vector2i = _DOOR_INWARD[door_side]
	var along: Vector2i = _DOOR_ALONG[door_side]
	for offset in [inward, inward + along, inward - along, along, -along]:
		var pcell: Vector2i = door_cell + offset
		if interior.has_point(pcell):
			pocket.append(pcell)

	# two-story buildings claim a stairs corner BEFORE furnishing, so no
	# couch ever blocks the flight
	var stairs_cell := Vector2i(-99, -99)
	if stories == 2:
		# a full cell in from every wall: the flight's art is wider than one
		# cell and poked through the west facade when it hugged the corner
		var stair_corners: Array[Vector2i] = [
			interior.position + Vector2i(1, 1),
			Vector2i(interior.end.x - 2, interior.position.y + 1),
			Vector2i(interior.position.x + 1, interior.end.y - 2),
			interior.end - Vector2i(2, 2),
		]
		stairs_cell = stair_corners[0]
		for cand in stair_corners:
			if cand not in pocket:
				stairs_cell = cand
				break
		pocket.append(stairs_cell)
		pocket.append(stairs_cell + Vector2i(0, 1))   # the approach stays clear
		pocket.append(stairs_cell + Vector2i(1, 0))

	var ground_props: Array[Node2D] = []
	if plot.get("safehouse", false):
		# the safehouse: one couch, one crate, and ROOM — the center cell
		# is the spawn and stays clear forever
		var couch_cell := Vector2i(interior.position.x + 1, interior.position.y + 1)
		if couch_cell not in pocket:
			ground_props.append(_add_prop_at_cell("couch", couch_cell, Vector2(4, 2)))
		var crate_cell := Vector2i(interior.end.x - 2, interior.position.y + 1)
		if crate_cell not in pocket:
			ground_props.append(_add_prop_at_cell(
				"crate_%d" % _rng.randi_range(0, 5), crate_cell, Vector2(4, 2)))
	elif kind == "house":
		_furnish_house(interior, pocket, ground_props)
	elif kind == "school":
		_furnish_school(interior, pocket, ground_props)
	else:
		_furnish_warehouse(interior, pocket, ground_props)
		var yard := Rect2i(rect.position.x + 1, rect.end.y + 1, rect.size.x - 1, 4)
		if _yard_fits(yard):
			_yards.append(yard)

	if stories == 2:
		_build_upper(interior, stairs_cell, kind, floor_tile, ground_props)


func _yard_fits(yard: Rect2i) -> bool:
	if yard.end.y >= MAP_H - EDGE_FOREST:
		return false
	for y in range(yard.position.y, yard.end.y):
		for x in range(yard.position.x, yard.end.x):
			var cell := Vector2i(x, y)
			if _on_road(cell) or _forest.has(cell) or _occupied.has(cell):
				return false
	return true


func _build_roof(interior: Rect2i, tone: String, post_positions: Array,
		ruined: bool, roof_h: int = -1) -> void:
	var south_corner := interior.end - Vector2i(1, 1)  # position anchor AND ruin bite corner
	var roof := RoofReveal.new()
	roof.cells = interior
	roof.position = _floor_layer.map_to_local(south_corner) + Vector2(0, 24)
	var lift := Vector2(0, -float(roof_h if roof_h > 0 else _wall_h))
	for y in range(interior.position.y, interior.end.y):
		await _tick()
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			var tile_name := "roof_tile_%s_%d" % [tone, _rng.randi_range(0, 3)]
			if ruined and Vector2(cell - south_corner).length() < 3.0 and _rng.randf() < 0.6:
				tile_name = "roof_tile_%s_broken_%d" % [tone, _rng.randi_range(0, 1)]
			var tile := _prop_sprite(tile_name)
			tile.position = _floor_layer.map_to_local(cell) - roof.position + lift
			roof.add_child(tile)
			for side in _edge_sides(cell, interior):
				var module := ""
				match side:
					"yp": module = "roof_fascia_%s_s" % tone
					"xp": module = "roof_fascia_%s_e" % tone
					"yn": module = "roof_eave_%s_n" % tone
					"xn": module = "roof_eave_%s_w" % tone
				var edge := _prop_sprite(module)
				edge.position = _floor_layer.map_to_local(cell) \
					+ (_EDGE_OFFSET[side] as Vector2) - roof.position + lift
				roof.add_child(edge)
	for post_pos in post_positions:
		var cap := _prop_sprite("roof_corner_%s" % tone)
		cap.position = (post_pos as Vector2) - roof.position + lift
		roof.add_child(cap)
	for i in 2:
		var cell := Vector2i(_rng.randi_range(interior.position.x, interior.end.x - 1),
			_rng.randi_range(interior.position.y, interior.end.y - 1))
		var deco := _prop_sprite("roof_vent" if i == 0 else "roof_hatch")
		deco.position = _floor_layer.map_to_local(cell) - roof.position + lift
		roof.add_child(deco)
	_ysort.add_child(roof)
	_roofs.append(roof)


func _interior_free_cells(interior: Rect2i, keep_clear: Array[Vector2i]) -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			if cell in keep_clear:
				continue
			cells.append(cell)
	return cells


func _furnish_house(interior: Rect2i, pocket: Array[Vector2i],
		collect: Array[Node2D] = []) -> void:
	var p := interior.position
	var couch_side := _rng.randi_range(0, 1)
	var couch_cell := p + Vector2i(1, 1 + couch_side)
	var tv_cell := p + Vector2i(3, 1 + couch_side)
	# never let the pair sit in the entrance pocket — slide it along the wall
	var slide := 0
	while (couch_cell in pocket or tv_cell in pocket) and slide < 4:
		couch_cell.x += 1
		tv_cell.x += 1
		slide += 1
	if couch_cell in pocket or tv_cell in pocket \
			or not interior.has_point(couch_cell) or not interior.has_point(tv_cell):
		var fallback := _interior_free_cells(interior, pocket)
		_shuffle(fallback)
		couch_cell = fallback.pop_front()
		tv_cell = fallback.pop_front()
	collect.append(_add_prop_at_cell("couch", couch_cell, Vector2(6, 3)))
	collect.append(_add_prop_at_cell("tv_stand", tv_cell, Vector2(4, 2)))
	# back-wall pieces: distinct random slots, both always present
	var wall_cells: Array[Vector2i] = []
	for x in range(interior.position.x, interior.end.x):
		var cell := Vector2i(x, p.y)
		if cell != couch_cell and cell != tv_cell and cell not in pocket:
			wall_cells.append(cell)
	_shuffle(wall_cells)
	for piece in ["cabinet", "bookshelf"]:
		if wall_cells.is_empty():
			break
		collect.append(_add_prop_at_cell(piece, wall_cells.pop_front(), Vector2(6, 2)))
	# domestic extras only — no industrial barrels indoors (user call)
	var keep := pocket.duplicate()
	keep.append(couch_cell)
	keep.append(tv_cell)
	var cells := _interior_free_cells(interior, keep)
	var extras := ["table", "chair", "chair", "crate_%d" % _rng.randi_range(0, 5)]
	_shuffle(extras)
	for i in _rng.randi_range(2, 3):
		if cells.is_empty():
			break
		collect.append(_add_prop_at_cell(extras[i - 1], _take_random_cell(cells),
			Vector2(8, 4)))


func _furnish_warehouse(interior: Rect2i, pocket: Array[Vector2i],
		collect: Array[Node2D] = []) -> void:
	var p := interior.position
	var rack_slots: Array[int] = []
	for x_offset in range(1, interior.size.x - 1, 2):
		rack_slots.append(x_offset)
	_shuffle(rack_slots)
	var used: Array[Vector2i] = pocket.duplicate()
	for i in _rng.randi_range(3, mini(5, rack_slots.size())):
		var cell := Vector2i(p.x + rack_slots[i - 1], p.y)
		if cell in pocket:
			continue
		collect.append(_add_prop_at_cell(_pick_variant("rack"), cell, Vector2(8, 2)))
		used.append(cell)
	var cells := _interior_free_cells(interior, used)
	var stock_mix := [
		["crate_stack", 0.24], ["crate", 0.22], ["pallet", 0.18],
		["barrel", 0.20], ["cylinder", 0.16],
	]
	var total := 0.0
	for opt in stock_mix:
		total += opt[1]
	for i in _rng.randi_range(8, 14):  # halls are big now — stock to match
		if cells.is_empty():
			break
		var cell := _take_random_cell(cells)
		var roll := _rng.randf() * total
		for opt in stock_mix:
			roll -= opt[1]
			if roll <= 0.0:
				collect.append(_add_prop_at_cell(_pick_variant(opt[0]), cell,
					Vector2(10, 5)))
				break


func _furnish_school(interior: Rect2i, pocket: Array[Vector2i],
		collect: Array[Node2D] = []) -> void:
	# a real classroom (user request): the chalkboard on the front wall, a
	# teacher's desk under it, then rows of desk+chair PAIRS all facing the
	# board, shelves along the back. NOTE: never gate on _occupied here —
	# the shell marks its whole interior occupied before furnishing (that
	# silent gate left the school empty for two versions).
	var p := interior.position
	var used: Dictionary = {}
	# the board hangs on the interior face of the north wall, centered-ish
	var board_cell := Vector2i(clampi(p.x + interior.size.x / 2,
		p.x + 1, interior.end.x - 2), p.y)
	if board_cell in pocket:
		board_cell.x += 2
	collect.append(_add_prop_at_cell("chalkboard", board_cell, Vector2(2, 0)))
	used[board_cell] = true
	# the teacher's desk, one row in, off the board's shoulder
	var teacher := Vector2i(board_cell.x + (1 if _rng.randf() < 0.5 else -1),
		p.y + 1)
	if interior.grow(-1).has_point(teacher) and teacher not in pocket:
		collect.append(_add_prop_at_cell("table", teacher, Vector2(4, 2)))
		used[teacher] = true
	# desk rows: chair SOUTH of each desk, every pair facing the board
	var y := p.y + 3
	while y < interior.end.y - 1:
		var x := p.x + 1 + _rng.randi_range(0, 1)
		while x < interior.end.x - 1:
			var desk := Vector2i(x, y)
			var chair := Vector2i(x, y + 1)
			if desk not in pocket and chair not in pocket \
					and not used.has(desk) and not used.has(chair) \
					and interior.has_point(chair) and chair.y < interior.end.y:
				collect.append(_add_prop_at_cell("table", desk, Vector2(4, 2)))
				collect.append(_add_prop_at_cell("chair", chair, Vector2(4, 2)))
				used[desk] = true
				used[chair] = true
			x += _rng.randi_range(2, 3)
		y += 3
	# shelves along the back wall, clear of the door pocket
	var wall_cells: Array[Vector2i] = []
	for x in range(interior.position.x + 1, interior.end.x - 1):
		var cell := Vector2i(x, interior.end.y - 1)
		if cell not in pocket and not used.has(cell):
			wall_cells.append(cell)
	_shuffle(wall_cells)
	for i in mini(2, wall_cells.size()):
		collect.append(_add_prop_at_cell("bookshelf", wall_cells[i], Vector2(5, 2)))


func _build_upper(interior: Rect2i, stairs_cell: Vector2i, kind: String,
		ground_floor_tile: String, ground_props: Array[Node2D]) -> void:
	# the SECOND STORY: an upper room drawn only while the player is up
	# there. Floor sprites live in a container anchored NORTH of the whole
	# footprint (always under the player in the y-sort); furniture nodes
	# keep their TRUE ground position for collision/sorting and lift only
	# their sprites by story_h. The stairs prop is shared by both floors.
	var upper := Node2D.new()
	upper.name = "Upper%d" % _uppers.size()
	upper.position = _floor_layer.map_to_local(interior.position) \
		+ Vector2(0, -24.0 - float(_story_h))
	upper.visible = false
	_ysort.add_child(upper)

	var atlas: Texture2D = load("res://art/gen/floors.png")
	# WOOD upstairs in EVERY building — the school's screed-over-screed
	# melted into the ground room at night ("theres no second floor");
	# classroom parquet reads instantly at any hour
	var upper_tile := "wood_%d" % _rng.randi_range(0, 4)
	if upper_tile == ground_floor_tile:
		upper_tile = "wood_%d" % ((int(upper_tile.substr(5)) + 1) % 5)
	var tc: Array = _floor_coords[upper_tile]
	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			# EVERY cell gets floor — the upper room is the ground room's
			# ceiling, complete (user: the stairwell hole showed the ground
			# and broke it). The flight's art still rises through the slab.
			var tile := Sprite2D.new()
			tile.texture = atlas
			tile.region_enabled = true
			tile.region_rect = Rect2(float(int(tc[0]) * 64), float(int(tc[1]) * 32),
				64.0, 32.0)
			tile.position = _floor_layer.map_to_local(cell) - upper.position \
				+ Vector2(0.0, -float(_story_h))
			upper.add_child(tile)

	# the slab lip: a dark edge along the south and east borders — the
	# plane needs a silhouette or it melts into the room below (user:
	# "the floor is not showing up when im on the second floor")
	var edge_x_tex: Texture2D = load("res://art/gen/floor_edge_x.png")
	var edge_y_tex: Texture2D = load("res://art/gen/floor_edge_y.png")
	for x in range(interior.position.x, interior.end.x):
		var lip := Sprite2D.new()
		lip.texture = edge_x_tex
		lip.centered = false
		lip.offset = Vector2(-32, -16)
		lip.position = _floor_layer.map_to_local(
			Vector2i(x, interior.end.y - 1)) - upper.position \
			+ Vector2(0.0, -float(_story_h))
		upper.add_child(lip)
	for y in range(interior.position.y, interior.end.y):
		var lip2 := Sprite2D.new()
		lip2.texture = edge_y_tex
		lip2.centered = false
		lip2.offset = Vector2(-32, -16)
		lip2.position = _floor_layer.map_to_local(
			Vector2i(interior.end.x - 1, y)) - upper.position \
			+ Vector2(0.0, -float(_story_h))
		upper.add_child(lip2)

	# the stairs themselves (ground object, tall enough to arrive upstairs)
	var stairs_info: Dictionary = _manifest["props"]["stairs"]
	var stairs := Stairs.new()
	stairs.position = _floor_layer.map_to_local(stairs_cell).round()
	_ysort.add_child(stairs)
	var stairs_origin: Array = stairs_info["origin"]
	stairs.setup(load("res://art/gen/stairs.png"),
		Vector2(float(stairs_origin[0]), float(stairs_origin[1])), _uppers.size())
	_occupied[stairs_cell] = true

	# upstairs furniture: true positions, lifted sprites, colliders off
	var upper_props: Array[Node2D] = []
	var keep: Array[Vector2i] = [stairs_cell, stairs_cell + Vector2i(0, 1),
		stairs_cell + Vector2i(1, 0)]
	var cells := _interior_free_cells(interior, keep)
	_shuffle(cells)
	var pieces: Array[String] = []
	if kind == "house":
		pieces = ["bed", "cabinet", "bookshelf", "crate_%d" % _rng.randi_range(0, 5)]
		if _rng.randf() < 0.4:
			pieces.append("bed")
	else:
		pieces = ["table", "chair", "table", "chair", "bookshelf"]
	for piece in pieces:
		if cells.is_empty():
			break
		var node := _add_prop_at_cell(piece, cells.pop_front(), Vector2(6, 3))
		for child in node.get_children():
			if child is Sprite2D:
				child.position += Vector2(0.0, -float(_story_h))
		node.visible = false
		if node is StaticBody2D:
			(node as StaticBody2D).collision_layer = 0
		upper_props.append(node)

	_uppers.append({
		"cells": interior,
		"container": upper,
		"upper_props": upper_props,
		"ground_props": ground_props,
		"stairs_cell": stairs_cell,
		"stairs_node": stairs,
	})


func _place_yards() -> void:
	for yard in _yards:
		await _tick()
		for y in range(yard.position.y, yard.end.y):
			for x in range(yard.position.x, yard.end.x):
				var cell := Vector2i(x, y)
				if (x - yard.position.x) % 3 == 2 and y < yard.end.y - 1:
					_set_tile(cell, "asphalt_stall")
				else:
					_set_tile(cell, "asphalt_%d" % _rng.randi_range(0, 1))
		var stall_cells: Array[Vector2i] = []
		for sx in range(yard.position.x + 1, yard.end.x - 1, 3):
			var stall := Vector2i(sx, yard.position.y + 1)
			if not _near_a_door(stall):
				stall_cells.append(stall)
		_shuffle(stall_cells)
		for i in mini(_rng.randi_range(1, 3), stall_cells.size()):
			# parked facing the building they were left at
			var fam := "vehicle_nw" if _rng.randf() < 0.5 else "vehicle_ne"
			var stall_variant := _pick_variant(fam)
			var stall_cell: Vector2i = stall_cells[i - 1]
			var stall_pos := _floor_layer.map_to_local(stall_cell) + Vector2(
				_rng.randf_range(-6.0, 6.0), _rng.randf_range(-3.0, 3.0))
			if stall_variant.ends_with("_5") or stall_variant.ends_with("_6"):
				_add_prop(stall_variant, stall_pos)
				_occupied[stall_cell] = true
			else:
				var stall_car := _spawn_driveable(stall_variant, fam, stall_pos)
				_occupied[stall_cell] = true
				_maybe_arm_car(stall_variant, stall_car)
		var spill_cells: Array[Vector2i] = []
		for y in range(yard.position.y, yard.end.y):
			for x in range(yard.position.x, yard.end.x):
				var cell := Vector2i(x, y)
				if not _occupied.has(cell) and not _near_a_door(cell):
					spill_cells.append(cell)
		for i in _rng.randi_range(2, 4):
			if spill_cells.is_empty():
				break
			var item := _pick_variant(["crate", "crate_stack", "pallet"][_rng.randi_range(0, 2)])
			_add_prop_at_cell(item, _take_random_cell(spill_cells), Vector2(6, 3))
		for y in range(yard.position.y, yard.end.y):
			for x in range(yard.position.x, yard.end.x):
				_occupied[Vector2i(x, y)] = true


func _place_courtyard() -> void:
	# the town square: dry fountain center, planter ring, benches, lamps
	if _court_rect.size.x == 0:
		return
	var center := _court_rect.get_center()
	_add_prop_at_cell("fountain_dry", center)
	for i in 4:
		await _tick()
		var corner := Vector2i(
			_court_rect.position.x + 1 + _rng.randi_range(0, 1),
			_court_rect.position.y + 1 + _rng.randi_range(0, 1))
		match i:
			1: corner = Vector2i(_court_rect.end.x - 2 - _rng.randi_range(0, 1),
				_court_rect.position.y + 1 + _rng.randi_range(0, 1))
			2: corner = Vector2i(_court_rect.position.x + 1 + _rng.randi_range(0, 1),
				_court_rect.end.y - 2 - _rng.randi_range(0, 1))
			3: corner = Vector2i(_court_rect.end.x - 2 - _rng.randi_range(0, 1),
				_court_rect.end.y - 2 - _rng.randi_range(0, 1))
		if not _occupied.has(corner):
			_add_prop_at_cell(_pick_variant("planter"), corner, Vector2(4, 2))
	for i in _rng.randi_range(2, 4):
		await _tick()
		var cell := Vector2i(
			_rng.randi_range(_court_rect.position.x + 1, _court_rect.end.x - 2),
			_rng.randi_range(_court_rect.position.y + 1, _court_rect.end.y - 2))
		if _occupied.has(cell) or Vector2(cell - center).length() < 2.5:
			continue
		var axis := "x" if _rng.randf() < 0.5 else "y"
		_add_prop_at_cell("bench_%s_%d" % [axis, 0 if _rng.randf() < 0.75 else 1],
			cell, Vector2(3, 2))
	var lamp_cell := Vector2i(_court_rect.position.x, _court_rect.get_center().y)
	if not _occupied.has(lamp_cell):
		_add_lamp(lamp_cell)


func _place_trainyard() -> void:
	# rolling stock on the sidings, buffers at their ends, freight spill
	for siding in _sidings:
		await _tick()
		var cells: Array = siding
		if cells.is_empty():
			continue
		var end_cell: Vector2i = cells[cells.size() - 1]
		_add_prop_at_cell("buffer_stop_%d" % _rng.randi_range(0, 1),
			end_cell + Vector2i(1, 0))
		var x_index := 1
		while x_index < cells.size() - 3:
			if _rng.randf() < 0.62:
				var cell: Vector2i = cells[x_index + 1]
				var boxcar := _pick_variant("boxcar_x")
				_add_prop_at_cell(boxcar, cell, Vector2(3, 1))
				x_index += 4
			else:
				x_index += 3
		for i in _rng.randi_range(2, 4):    # freight that never shipped
			var near: Vector2i = cells[_rng.randi_range(0, cells.size() - 1)]
			var spot := near + Vector2i(_rng.randi_range(-1, 1), _rng.randi_range(2, 3))
			if _occupied.has(spot) or _rail_cells.has(spot) or _ballast.has(spot) \
					or _on_road(spot):
				continue
			var item := _pick_variant(["crate", "crate_stack", "pallet"][_rng.randi_range(0, 2)])
			_add_prop_at_cell(item, spot, Vector2(6, 3))
	# a couple of boxcars stranded on the main line too
	for i in _rng.randi_range(1, 2):
		await _tick()
		var x := _rng.randi_range(BARRIER_INSET + 8, MAP_W - BARRIER_INSET - 8)
		var cell := Vector2i(x, _rail_row)
		if _occupied.has(cell) or _on_road(cell) or _rail_cross.has(cell) \
				or _near_a_door(cell):
			continue
		_add_prop_at_cell(_pick_variant("boxcar_x"), cell, Vector2(4, 1))


func _place_depot() -> void:
	# the bus depot: a rank of buses on the apron, shelters at its lip,
	# some broken into with their litter dragged out
	if _depot_rect.size.x == 0:
		return
	var row_y := _depot_rect.position.y + _depot_rect.size.y / 2
	var x := _depot_rect.position.x + 2
	var parked := 0
	while x < _depot_rect.end.x - 2 and parked < 4:
		await _tick()
		var cell := Vector2i(x, row_y + _rng.randi_range(-1, 1))
		if not _occupied.has(cell) and not _near_a_door(cell):
			var fam := "bus_nw" if _rng.randf() < 0.5 else "bus_se"
			var variant := _pick_variant(fam)
			_add_prop_at_cell(variant, cell, Vector2(4, 2))
			parked += 1
			if variant.ends_with("_2") or variant.ends_with("_3"):
				# broken into: whatever was worth taking came out messily
				for t in _rng.randi_range(2, 3):
					var spot := cell + Vector2i(_rng.randi_range(-2, 2), _rng.randi_range(2, 3))
					if not _occupied.has(spot) and not _on_road(spot):
						_add_prop_at_cell(_pick_variant("trash"), spot, Vector2(8, 4))
		x += _rng.randi_range(4, 6)
	for i in 2:   # shelters on the apron's north lip
		var sx := _depot_rect.position.x + 3 + i * (_depot_rect.size.x / 2)
		var cell := Vector2i(sx + _rng.randi_range(0, 2), _depot_rect.position.y - 1)
		if not _occupied.has(cell) and not _on_road(cell) and not _near_a_door(cell):
			_add_prop_at_cell("shelter_x_%d" % (0 if _rng.randf() < 0.6 else 1),
				cell, Vector2(2, 1))
	var bench_cell := Vector2i(_depot_rect.get_center().x, _depot_rect.position.y - 1)
	if not _occupied.has(bench_cell) and not _on_road(bench_cell):
		_add_prop_at_cell("bench_x_0", bench_cell, Vector2(3, 2))


func _place_comms() -> void:
	# the relay compound: fence ring with a gap, the mast, shed, dish,
	# fuel drums — small, distinct, very quest-shaped
	if _comms_rect.size.x == 0:
		return
	var center := _comms_rect.get_center()
	_add_prop_at_cell("comms_tower", center)
	var shed_cell := center + Vector2i(-2, 2)
	if not _occupied.has(shed_cell):
		_add_prop_at_cell("equip_shed", shed_cell, Vector2(2, 1))
	var dish_cell := center + Vector2i(2, -2)
	if not _occupied.has(dish_cell):
		_add_prop_at_cell("dish_ground", dish_cell, Vector2(3, 2))
	for i in _rng.randi_range(2, 3):
		var cell := center + Vector2i(_rng.randi_range(-3, 3), _rng.randi_range(-3, 3))
		if not _occupied.has(cell) and cell != center:
			_add_prop_at_cell(_pick_variant("barrel"), cell, Vector2(5, 3))
	# the fence: lattice panels around the rect, one gap left open
	var gap_side := _rng.randi_range(0, 3)
	var fence_step := 2
	for x in range(_comms_rect.position.x, _comms_rect.end.x, fence_step):
		await _tick()
		if gap_side != 0 or absi(x - center.x) > 2:
			_fence_piece(Vector2i(x, _comms_rect.position.y), "x")
		if gap_side != 1 or absi(x - center.x) > 2:
			_fence_piece(Vector2i(x, _comms_rect.end.y - 1), "x")
	for y in range(_comms_rect.position.y + 1, _comms_rect.end.y - 1, fence_step):
		await _tick()
		if gap_side != 2 or absi(y - center.y) > 2:
			_fence_piece(Vector2i(_comms_rect.position.x, y), "y")
		if gap_side != 3 or absi(y - center.y) > 2:
			_fence_piece(Vector2i(_comms_rect.end.x - 1, y), "y")


func _fence_piece(cell: Vector2i, axis: String) -> void:
	if _occupied.has(cell) or _on_road(cell) or _sidewalk.has(cell) \
			or _rail_cells.has(cell) or _ballast.has(cell):
		return
	var names: Array = _families["barricade_%s" % axis]
	var piece: String = names[_rng.randi_range(2, 3)]   # the lattice designs
	var pos := _floor_layer.map_to_local(cell) + Vector2(
		_rng.randf_range(-3.0, 3.0), _rng.randf_range(-2.0, 2.0))
	_add_prop(piece, pos)
	_occupied[cell] = true


func _place_school_grounds() -> void:
	# the schoolyard: swings, slide, sandbox, flagpole out front, the sign
	# by the road, a partial fence. Recess never came back.
	if _playground.size.x <= 0 or _playground.size.y <= 0:
		return
	var spots: Array[Vector2i] = []
	for y in range(_playground.position.y + 1, _playground.end.y - 1):
		await _tick()
		for x in range(_playground.position.x + 2, _playground.end.x - 2):
			var cell := Vector2i(x, y)
			if not _occupied.has(cell) and not _on_road(cell) \
					and not _forest.has(cell) and not _near_a_door(cell) \
					and not _sidewalk.has(cell) and not _rail_cells.has(cell) \
					and not _ballast.has(cell) and not _dirt_path.has(cell):
				spots.append(cell)
	_shuffle(spots)
	var pieces := ["swing_set_%d" % _rng.randi_range(0, 1), "slide", "sandbox"]
	for piece in pieces:
		var placed := false
		while not spots.is_empty() and not placed:
			var cell := _take_random_cell(spots)
			var clear := true
			for off in [Vector2i.RIGHT, Vector2i.LEFT]:
				if _occupied.has(cell + off):
					clear = false
			if clear:
				_add_prop_at_cell(piece, cell, Vector2(4, 2))
				placed = true
	# flagpole near the school door, sign toward the block edge
	var door_out := Vector2i(-99, -99)
	for plot in _plots:
		if plot["kind"] == "school":
			door_out = plot["door_out"]
	if door_out.x > -99:
		var flag_cell := door_out + Vector2i(_rng.randi_range(2, 3), 1)
		if not _occupied.has(flag_cell) and not _near_a_door(flag_cell):
			_add_prop_at_cell("flagpole", flag_cell, Vector2(3, 2))
	var sign_cell := Vector2i(_playground.get_center().x, _playground.end.y)
	if not _occupied.has(sign_cell) and not _on_road(sign_cell) \
			and not _sidewalk.has(sign_cell):
		_add_prop_at_cell("school_sign", sign_cell, Vector2(4, 2))
	# a stretch of fence along the playground's south edge, gappy
	for x in range(_playground.position.x, _playground.end.x, 2):
		if _rng.randf() < 0.7:
			_fence_piece(Vector2i(x, _playground.end.y - 1), "x")


func _place_lz() -> void:
	# THE LIFT: a clearing somebody keeps clear, with a painted marker,
	# a dirt track running to it and enough junk around the rim to say
	# people wait here. The green smoke and glow are runtime.
	var blocks := _zone_blocks("open")
	if blocks.is_empty():
		blocks = _zone_blocks("forest")
	if blocks.is_empty():
		return
	var r: Rect2i = _block_rects[blocks[0]]
	# the far corner from the gallery, so the two POIs don't crowd
	var size := Vector2i(9, 8)
	var pos := Vector2i(r.end.x - size.x - 2, r.end.y - size.y - 2)
	if _gallery_rect.size.x > 0 and _gallery_rect.get_center().x > r.get_center().x:
		pos.x = r.position.x + 2
	_lz_rect = Rect2i(pos, size)
	var centre := _lz_rect.get_center()
	for y in range(_lz_rect.position.y, _lz_rect.end.y):
		await _tick()
		for x in range(_lz_rect.position.x, _lz_rect.end.x):
			var cell := Vector2i(x, y)
			if _on_road(cell) or _rail_cells.has(cell):
				continue
			_forest.erase(cell)
			_dirt_path[cell] = true          # a stamped-flat clearing
			_set_tile(cell, "dirt_%d" % _rng.randi_range(0, 3))
			_occupied[cell] = true
	# the track in: a dirt road from the nearest road to the clearing
	var road_x: int = _roads_v[0].x
	for r_v in _roads_v:
		if absi(r_v.x - centre.x) < absi(road_x - centre.x):
			road_x = r_v.x
	var walk_x := centre.x
	var step := 1 if road_x > centre.x else -1
	while walk_x != road_x:
		var tcell := Vector2i(walk_x, centre.y + _rng.randi_range(-1, 1))
		if not _occupied.has(tcell) and not _on_road(tcell):
			_dirt_path[tcell] = true
			_set_tile(tcell, "dirt_%d" % _rng.randi_range(0, 3))
		walk_x += step
	# the painted marker in the middle, and the waiting-room junk
	_add_prop_at_cell("lz_marker", centre, Vector2(0, 0))
	var rim: Array[Vector2i] = []
	for y in range(_lz_rect.position.y, _lz_rect.end.y):
		for x in range(_lz_rect.position.x, _lz_rect.end.x):
			var cell := Vector2i(x, y)
			if Vector2(cell - centre).length() > 3.2:
				rim.append(cell)
	_shuffle(rim)
	for i in mini(6, rim.size()):
		var junk: String = ["barrel", "crate", "crate_stack", "pallet",
			"tires"][_rng.randi_range(0, 4)]
		_add_prop_at_cell(_pick_variant(junk), rim[i], Vector2(0, 0))
	_extracts.append({
		"name": "the lift",
		"kind": "lift",
		"pos": _floor_layer.map_to_local(centre),
		"radius": 150.0,        # about the clearing itself
		"auto": true,
	})
	_map_marks.append([centre, "lz"])


func _place_scrapyard() -> void:
	# the scrapyard: rows of dead and not-so-dead vehicles, forklifts that
	# stopped mid-shift, ONE crane over it all, industrial racks, junk deep
	# enough to get lost in (user request)
	var blocks := _zone_blocks("scrapyard")
	if blocks.is_empty():
		return
	var r: Rect2i = _block_rects[blocks[0]]
	_scrap_rect = r
	var row_count := 2 if r.size.y < 18 else 3
	for row in row_count:
		await _tick()
		var y: int = r.position.y + 3 + row * maxi(5, (r.size.y - 6) / row_count)
		var x: int = r.position.x + 2
		while x < r.end.x - 3:
			var cell := Vector2i(x, y + _rng.randi_range(-1, 1))
			if not _occupied.has(cell) and not _forest.has(cell) \
					and not _on_road(cell) and not _near_a_door(cell) \
					and not _rail_cells.has(cell) and not _ballast.has(cell):
				var fam: String = ["vehicle_nw", "vehicle_ne", "vehicle_se",
					"vehicle_sw"][_rng.randi_range(0, 3)]
				var variant := _pick_variant(fam)
				var pos := _floor_layer.map_to_local(cell) + Vector2(
					_rng.randf_range(-4.0, 4.0), _rng.randf_range(-2.0, 2.0))
				if variant.ends_with("_5") or variant.ends_with("_6"):
					_add_prop(variant, pos)
					_occupied[cell] = true
				else:
					var scrap_car := _spawn_driveable(variant,
						fam.trim_prefix("vehicle_"), pos)
					_occupied[cell] = true
					_maybe_arm_car(variant, scrap_car)
				_map_marks.append([cell, "car"])
			x += _rng.randi_range(4, 6)
	for i in 2:                                  # forklifts between the rows
		await _tick()
		var cell := Vector2i(
			_rng.randi_range(r.position.x + 3, r.end.x - 4),
			_rng.randi_range(r.position.y + 2, r.end.y - 3))
		if not _occupied.has(cell) and not _forest.has(cell) \
				and not _on_road(cell) and not _rail_cells.has(cell):
			_add_prop_at_cell("forklift_%d" % i, cell, Vector2(6, 3))
	var crane_cell := Vector2i(r.get_center().x + _rng.randi_range(-3, 3),
		r.position.y + 2)
	if not _occupied.has(crane_cell) and not _rail_cells.has(crane_cell) \
			and not _forest.has(crane_cell) and not _on_road(crane_cell):
		_add_prop_at_cell("crane", crane_cell, Vector2(3, 2))
		_map_marks.append([crane_cell, "crane"])
	var rack_y := r.end.y - 2                    # rack line along the south
	var rack_x := r.position.x + 2
	while rack_x < r.end.x - 3:
		await _tick()
		var cell := Vector2i(rack_x, rack_y)
		if not _occupied.has(cell) and not _forest.has(cell) \
				and not _on_road(cell) and not _near_a_door(cell) \
				and not _rail_cells.has(cell) and not _sidewalk.has(cell):
			_add_prop_at_cell(_pick_variant("rack"), cell, Vector2(4, 2))
		rack_x += _rng.randi_range(3, 5)
	for i in 12:                                 # the junk between everything
		await _tick()
		var cell := Vector2i(
			_rng.randi_range(r.position.x + 1, r.end.x - 2),
			_rng.randi_range(r.position.y + 1, r.end.y - 2))
		if _occupied.has(cell) or _forest.has(cell) or _on_road(cell) \
				or _rail_cells.has(cell) or _ballast.has(cell) \
				or _near_a_door(cell) or _sidewalk.has(cell):
			continue
		# the scrapyard is where things get DUMPED — heaps, not placements
		var junk: String = ["tires", "rubble", "barrel", "pallet", "crate",
			"crate_stack"][_rng.randi_range(0, 5)]
		if _rng.randf() < 0.55:
			_place_pile(junk, cell, _rng.randi_range(2, 5), 15.0)
		else:
			_add_prop(_pick_variant_varied(junk),
				_floor_layer.map_to_local(cell) + _clutter_offset(10.0))
			_occupied[cell] = true


func _place_gallery() -> void:
	# the gallery: a couple of tagged walls, the cans that did it, benches,
	# and the one regular who still comes here (user request)
	if _gallery_rect.size.x == 0:
		return
	var r := _gallery_rect
	var wall_y := r.position.y + 2
	var wall_x := r.position.x + 1
	var walls := 0
	while walls < 3 and wall_x < r.end.x - 2:
		await _tick()
		var cell := Vector2i(wall_x, wall_y + _rng.randi_range(0, 1))
		if not _occupied.has(cell) and not _on_road(cell) \
				and not _forest.has(cell) and not _sidewalk.has(cell):
			_add_prop_at_cell("graffiti_x_%d" % (walls % 3), cell, Vector2(3, 1))
			walls += 1
			# cans where the artists crouched: 1-2 per wall, varied drops
			# in varied spots (user: the two placements looked identical)
			for ci in _rng.randi_range(1, 2):
				var can_cell := cell + Vector2i(_rng.randi_range(-1, 2),
					_rng.randi_range(1, 3))
				if not _occupied.has(can_cell) and not _on_road(can_cell) \
						and not _sidewalk.has(can_cell):
					_add_prop_at_cell(_pick_variant("spray_cans"), can_cell,
						Vector2(10, 5))
		wall_x += 2
	for i in 2:                                  # strays dropped mid-flight
		await _tick()
		var stray_cell := Vector2i(
			_rng.randi_range(r.position.x + 1, r.end.x - 2),
			_rng.randi_range(r.position.y + 1, r.end.y - 2))
		if not _occupied.has(stray_cell) and not _on_road(stray_cell) \
				and not _forest.has(stray_cell) \
				and not _sidewalk.has(stray_cell):
			_add_prop_at_cell(_pick_variant("spray_cans"), stray_cell,
				Vector2(10, 5))
	var bench_y := r.end.y - 2
	var smoker_placed := false
	for i in 2:
		var cell := Vector2i(r.position.x + 2 + i * 3 + _rng.randi_range(0, 1),
			bench_y)
		if _occupied.has(cell) or _on_road(cell) or _forest.has(cell) \
				or _sidewalk.has(cell):
			continue
		var bench := _add_prop_at_cell("bench_x_0" if not smoker_placed
			else _pick_variant("bench_x"), cell, Vector2(2, 1))
		if not smoker_placed:
			smoker_placed = true
			var smoker := Smoker.new()
			smoker.position = (bench.position + Vector2(0.0, 1.0)).round()
			_ysort.add_child(smoker)
	_map_marks.append([r.get_center(), "gallery"])


func _place_power_boxes() -> void:
	# a power box on every house wall — all of them humming along except
	# ONE, which hangs open and spits sparks (repair quest, someday)
	for i in _plots.size():
		await _tick()
		var plot: Dictionary = _plots[i]
		if plot["kind"] != "house":
			continue
		var door_side: String = plot["door_side"]
		var door_cell: Vector2i = plot["door_cell"]
		var interior: Rect2i = (plot["rect"] as Rect2i).grow(-1)
		var along: Vector2i = _DOOR_ALONG[door_side]
		var side_id: int = _EDGE_SIDE_IDS[door_side]
		var box_cell := Vector2i(-99, -99)
		for step in [2, -2, 3, -3, 1, -1]:
			var cand: Vector2i = door_cell + along * step
			# on the wall, inside the room, NEVER under a window (user:
			# "i dont want it underneath a window")
			if interior.has_point(cand) and not _window_cells.has(
					Vector3i(cand.x, cand.y, side_id)):
				box_cell = cand
				break
		if box_cell.x < -90:
			continue
		var axis: String = _EDGE_AXIS[door_side]
		var broken := i == _spark_house
		var box_name := "power_box_%s%s" % [axis, "_broken" if broken else ""]
		var center := _floor_layer.map_to_local(box_cell)
		var pos := center + (_EDGE_OFFSET[door_side] as Vector2) \
			+ Vector2(0.0, 1.0)
		if broken:
			var box := PowerBox.new()
			box.position = pos.round()
			_ysort.add_child(box)
			box.setup(box_name)
			_map_marks.append([box_cell, "spark"])
		else:
			_add_prop(box_name, pos)


func _place_lamps() -> void:
	# sparse and mostly dead: a lamp every 14-22 tiles, well under half working
	for r in _roads_v:
		var y := EDGE_FOREST + _rng.randi_range(2, 8)
		while y < MAP_H - EDGE_FOREST:
			var cell := Vector2i(r.x - 1, y)
			if not _occupied.has(cell) and not _forest.has(cell) \
					and not _on_road(cell) and not _near_a_door(cell):
				_add_lamp(cell)
			y += _rng.randi_range(14, 22)
			await _tick()
	for r in _roads_h:
		var x := EDGE_FOREST + _rng.randi_range(2, 8)
		while x < MAP_W - EDGE_FOREST:
			var cell := Vector2i(x, r.x + r.y)
			if not _occupied.has(cell) and not _forest.has(cell) \
					and not _on_road(cell) and not _near_a_door(cell):
				_add_lamp(cell)
			x += _rng.randi_range(14, 22)
			await _tick()


func _place_traffic_lights() -> void:
	# dead traffic lights at the crossings — the same municipal design
	# everywhere, differing only in damage (the barricade lesson). Counts,
	# corners, damage state and jitter all rolled; heads hang over the
	# asphalt (mirrored family on the far-side corners).
	for rv in _roads_v:
		for rh in _roads_h:
			await _tick()
			var count_roll := _rng.randf()
			var count := 0 if count_roll < 0.30 else (1 if count_roll < 0.75 else 2)
			if count == 0:
				continue
			var corners := [
				[Vector2i(rv.x - 1, rh.x - 1), false],
				[Vector2i(rv.x + rv.y, rh.x - 1), true],
				[Vector2i(rv.x - 1, rh.x + rh.y), false],
				[Vector2i(rv.x + rv.y, rh.x + rh.y), true],
			]
			_shuffle(corners)
			var placed := 0
			for corner in corners:
				if placed >= count:
					break
				var cell: Vector2i = corner[0]
				if _occupied.has(cell) or _forest.has(cell) or _on_road(cell) \
						or _dirt_path.has(cell) or _near_a_door(cell) \
						or _cell_inset(cell) < BARRIER_INSET:
					continue
				var roll := _rng.randf()
				if roll < 0.10:
					_add_prop_at_cell(_pick_variant("traffic_light_flat"), cell,
						Vector2(6, 3))
				else:
					var fam := "traffic_light_m" if corner[1] else "traffic_light"
					var idx := 0
					var damage := _rng.randf()
					if damage < 0.35:
						idx = 0        # dark, long arm
					elif damage < 0.60:
						idx = 1        # dark, short arm + sign plate
					elif damage < 0.80:
						idx = 2        # bent arm
					else:
						idx = 3        # smashed head
					_add_prop_at_cell("%s_%d" % [fam, idx], cell, Vector2(3, 2))
				_traffic_cells.append(cell)
				placed += 1


func _place_street_furniture() -> void:
	# benches and bus shelters on the walkways — it IS the transit district.
	# Sparse, spaced, never near doors; the piece's axis follows the road's.
	var since_shelter := 99
	var since_bench := 99
	var since_vend := 99
	var since_news := 99
	for cell in _sidewalk:
		await _tick()
		since_shelter += 1
		since_bench += 1
		since_vend += 1
		since_news += 1
		if _occupied.has(cell) or _near_a_door(cell) \
				or _cell_inset(cell) < BARRIER_INSET:
			continue
		var axis: String = "y" if str(_sidewalk[cell]) == "v" else "x"
		var roll := _rng.randf()
		if roll < 0.012 and since_shelter > 14:
			_add_prop_at_cell("shelter_%s_%d" % [axis,
				0 if _rng.randf() < 0.7 else 1], cell, Vector2(2, 1))
			since_shelter = 0
		elif roll < 0.042 and since_bench > 8:
			_add_prop_at_cell("bench_%s_%d" % [axis,
				0 if _rng.randf() < 0.75 else 1], cell, Vector2(3, 2))
			since_bench = 0
		elif roll < 0.052 and since_vend > 16:
			# dead vending machines + news boxes live on the walkways too
			_add_prop_at_cell("vending_%d" % _rng.randi_range(0, 1), cell,
				Vector2(2, 1))
			since_vend = 0
		elif roll < 0.068 and since_news > 10:
			_add_prop_at_cell("newsbox_%d" % _rng.randi_range(0, 1), cell,
				Vector2(3, 2))
			since_news = 0


func _place_foliage() -> void:
	# bushes in the green pockets, plus planters hugging building walls —
	# they register with the Foliage manager (wiggle + see-through)
	for cell in _forest:
		await _tick()
		if _occupied.has(cell) or _dirt_path.has(cell) \
				or _cell_inset(cell) < BARRIER_INSET:
			continue
		if _rng.randf() < 0.06:
			var forest_bush := _add_prop_at_cell(_pick_variant("bush"),
				cell as Vector2i, Vector2(12, 6))
			_bush_nodes.append(forest_bush)
			_maybe_shed_bush(forest_bush)
	for plot in _plots:
		var ring: Rect2i = (plot["rect"] as Rect2i).grow(1)
		for i in _rng.randi_range(2, 5):
			await _tick()
			var cell := Vector2i(
				_rng.randi_range(ring.position.x, ring.end.x - 1),
				_rng.randi_range(ring.position.y, ring.end.y - 1))
			if _occupied.has(cell) or _on_road(cell) or _sidewalk.has(cell) \
					or _forest.has(cell) or _near_a_door(cell) \
					or (plot["rect"] as Rect2i).has_point(cell):
				continue
			var ring_bush := _add_prop_at_cell(_pick_variant("bush"),
				cell, Vector2(8, 4))
			_bush_nodes.append(ring_bush)
			_maybe_shed_bush(ring_bush)


func _fill_dead_spots() -> void:
	# the emptiness pass (user: "add stuff wherever theres nothing"): walk a
	# coarse lattice; where a whole neighborhood is bare, drop a grass tuft,
	# a bush, or a scrap of litter — quiet life, never clutter
	for gy in range(EDGE_FOREST, MAP_H - EDGE_FOREST, 4):
		for gx in range(EDGE_FOREST, MAP_W - EDGE_FOREST, 4):
			await _tick()
			var cell := Vector2i(gx + _rng.randi_range(-1, 1),
				gy + _rng.randi_range(-1, 1))
			if _occupied.has(cell) or _forest.has(cell) or _dirt_path.has(cell) \
					or _on_road(cell) or _sidewalk.has(cell) or _near_a_door(cell) \
					or _plaza.has(cell) or _apron.has(cell) \
					or _rail_cells.has(cell) or _ballast.has(cell):
				continue
			var bare := true
			for dy in range(-2, 3):
				for dx in range(-2, 3):
					var n := cell + Vector2i(dx, dy)
					if _occupied.has(n) or _forest.has(n) or _on_road(n):
						bare = false
						break
				if not bare:
					break
			if not bare:
				continue
			var roll := _rng.randf()
			if roll < 0.22:
				_add_prop_at_cell(_pick_variant("tuft"), cell, Vector2(14, 7))
			elif roll < 0.28:
				var spot_bush := _add_prop_at_cell(_pick_variant("bush"),
					cell, Vector2(10, 5))
				_bush_nodes.append(spot_bush)
				_maybe_shed_bush(spot_bush)
			elif roll < 0.33:
				_add_prop_at_cell(_pick_variant("trash"), cell, Vector2(12, 6))


func _place_barricades() -> void:
	# the barricade ring — the map's ADVERTISED edge. Randomized pieces with
	# slip-through gaps, some knocked flat; roads breach the line with
	# flattened wreckage on the asphalt. The world continues beyond it.
	var lo := BARRIER_INSET
	var hi_x := MAP_W - 1 - BARRIER_INSET
	var hi_y := MAP_H - 1 - BARRIER_INSET
	await _ring_side("x", lo, lo, hi_x)
	await _ring_side("x", hi_y, lo, hi_x)
	await _ring_side("y", lo, lo + 2, hi_y - 2)
	await _ring_side("y", hi_x, lo + 2, hi_y - 2)
	await _place_bodies()
	await _dress_buffer()
	await _dress_rail_line()
	await _place_toll_gate()


func _dress_rail_line() -> void:
	# A dead-straight line reads as a drawn line until something repeats
	# ALONGSIDE it at human intervals (user: "it does look a bit odd the
	# track being all a straight line"). Poles march the whole run at
	# uneven spacing, signals stand where they'd really stand — near the
	# yard and the crossings — and the ballast collects the usual junk.
	if _rail_row <= 0:
		return
	var side := 2 if _rng.randf() < 0.5 else -2
	var x := BARRIER_INSET + _rng.randi_range(2, 6)
	while x < MAP_W - BARRIER_INSET - 2:
		await _tick()
		var cell := Vector2i(x, _rail_row + side)
		if not _occupied.has(cell) and not _on_road(cell) \
				and not _rail_cells.has(cell) and not _ballast.has(cell) \
				and not _near_a_door(cell):
			_add_prop(_pick_variant_varied("telegraph_pole"),
				_floor_layer.map_to_local(cell) + _clutter_offset(7.0))
			_occupied[cell] = true
		# poles run at a rhythm, but never a metronome
		x += _rng.randi_range(7, 10)
		if _rng.randf() < 0.12:
			side = -side                      # the line changes sides
	# signals: one at each level crossing approach, one at the yard throat
	var signal_spots: Array[Vector2i] = []
	for road in _roads_v:
		signal_spots.append(Vector2i(road.x - 3, _rail_row - 2))
	signal_spots.append(Vector2i(_freight_cell.x - 9, _rail_row - 2))
	for spot in signal_spots:
		await _tick()
		if spot.x < BARRIER_INSET or spot.x > MAP_W - BARRIER_INSET:
			continue
		if _occupied.has(spot) or _on_road(spot) or _rail_cells.has(spot):
			continue
		_add_prop_at_cell(_pick_variant("rail_signal"), spot, Vector2(5, 3))
	# the stuff that collects beside a railway
	for i in 14:
		await _tick()
		var junk_cell := Vector2i(
			_rng.randi_range(BARRIER_INSET + 3, MAP_W - BARRIER_INSET - 3),
			_rail_row + (2 if _rng.randf() < 0.5 else -2)
				+ _rng.randi_range(-1, 1))
		if _occupied.has(junk_cell) or _on_road(junk_cell) \
				or _rail_cells.has(junk_cell) or _ballast.has(junk_cell) \
				or _near_a_door(junk_cell):
			continue
		var junk: String = ["barrel", "rubble", "pallet", "tires",
			"crate"][_rng.randi_range(0, 4)]
		_place_pile(junk, junk_cell, _rng.randi_range(2, 3), 12.0)


func _place_toll_gate() -> void:
	# THE TOLL GATE: where a road breaches the wire on the south side, a
	# booth, a boom, and a warden who is a business. Paying him opens this
	# crossing and the extract sits out past the line.
	var road: Vector2i = _roads_v[_roads_v.size() / 2]
	var gate_x := road.x + 1
	var gate_y := MAP_H - 1 - BARRIER_INSET       # the south ring line
	var booth_cell := Vector2i(gate_x + 3, gate_y)
	var gate := TollGate.new()
	gate.position = _floor_layer.map_to_local(booth_cell).round()
	# the boom spans the ROAD, so it has to travel along the map's x axis
	# (4 cells west of the booth) — a straight screen offset lands it on
	# the shoulder instead of across the asphalt
	gate.setup(_manifest, Vector2(-4.0 * 32.0, -4.0 * 16.0))
	_ysort.add_child(gate)
	for dx in range(-1, 2):
		for dy in range(-1, 2):
			_occupied[booth_cell + Vector2i(dx, dy)] = true
	_toll_gate = gate
	_toll_cell = booth_cell
	# the way out sits BEYOND the wire, straight down the road — you drive
	# out through the buffer and the counter runs (user spec)
	_extracts.append({
		"name": "the toll gate",
		"kind": "toll",
		"pos": _floor_layer.map_to_local(Vector2i(gate_x, gate_y + 16)),
		"radius": 240.0,
		"auto": false,
	})
	_map_marks.append([booth_cell, "toll"])


func _ring_side(axis: String, fixed: int, from: int, to: int) -> void:
	# a REAL barrier line: one dominant piece repeated in runs (a municipal
	# line is made of the same barrier over and over), a second design mixed
	# in sparingly, the odd one knocked askew or flat, uneven spacing
	# (clusters then gaps), and every piece shoved a little off the line
	# the LATTICE FENCE panels are the line (user call — the concrete runs
	# read as train tracks); jerseys are occasional accents. Denser line:
	# long runs, small rare gaps, everything jittered a little off-line.
	var names: Array = _families["barricade_%s" % axis]
	var dominant: String = names[_rng.randi_range(2, 3)]
	var second: String = names[_rng.randi_range(0, 1)]
	var i := from + _rng.randi_range(0, 2)
	while i <= to:
		var run := _rng.randi_range(3, 7)
		for r in run:
			if i > to:
				break
			var cell := Vector2i(i, fixed) if axis == "x" else Vector2i(fixed, i)
			i += _rng.randi_range(1, 2)
			await _tick()
			if _occupied.has(cell):
				continue
			if _on_road(cell):
				# the road breaches the line: wreckage shoved onto the stub
				if _rng.randf() < 0.6:
					_add_prop_at_cell(_pick_variant("barricade_%s_flat" % axis),
						cell, Vector2(10, 5))
				continue
			var roll := _rng.randf()
			var piece := dominant
			if roll < 0.08:
				piece = _pick_variant("barricade_%s_askew" % axis)
			elif roll < 0.18:
				piece = _pick_variant("barricade_%s_flat" % axis)
			elif roll < 0.28:
				piece = second
			var pos := _floor_layer.map_to_local(cell) + Vector2(
				_rng.randf_range(-7.0, 7.0), _rng.randf_range(-4.0, 4.0))
			_add_prop(piece, pos)
			_occupied[cell] = true
		i += _rng.randi_range(2, 4) if _rng.randf() < 0.8 else _rng.randi_range(5, 7)


func _dress_buffer() -> void:
	# past the line: bare dead district — rubble, the odd snag, litter. No
	# forests, no roads, nothing to loot. The emptiness IS the message.
	var placed := 0
	var attempts := 0
	while placed < 90 and attempts < 1500:  # the buffer band is deeper now
		attempts += 1
		await _tick()
		var depth := _rng.randi_range(4, BARRIER_INSET - 3)
		var along := _rng.randi_range(4, MAP_W - 5)
		var cell := Vector2i.ZERO
		match _rng.randi_range(0, 3):
			0: cell = Vector2i(along, depth)
			1: cell = Vector2i(along, MAP_H - 1 - depth)
			2: cell = Vector2i(depth, along)
			3: cell = Vector2i(MAP_W - 1 - depth, along)
		if _occupied.has(cell) or _on_road(cell) or _cell_inset(cell) >= BARRIER_INSET:
			continue
		var roll := _rng.randf()
		if roll < 0.48:
			_add_prop_at_cell(_pick_variant("rubble"), cell, Vector2(10, 5))
		elif roll < 0.62:
			_add_prop_at_cell("tree_%d" % _rng.randi_range(7, 8), cell, Vector2(10, 5))
		elif roll < 0.8:
			_add_prop_at_cell(_pick_variant("stick"), cell, Vector2(12, 6))
		else:
			_add_prop_at_cell(_pick_variant("trash"), cell, Vector2(12, 6))
		placed += 1


func _place_bodies() -> void:
	# fallen raiders PAST the line, sparse — the sniper warning, made visible
	var count := _rng.randi_range(10, 15)
	var placed := 0
	var attempts := 0
	while placed < count and attempts < 300:
		attempts += 1
		await _tick()
		var depth := BARRIER_INSET - _rng.randi_range(2, 12)
		var along := _rng.randi_range(BARRIER_INSET - 8, MAP_W - 1 - BARRIER_INSET + 8)
		var cell := Vector2i.ZERO
		match _rng.randi_range(0, 3):
			0: cell = Vector2i(along, depth)
			1: cell = Vector2i(along, MAP_H - 1 - depth)
			2: cell = Vector2i(depth, along)
			3: cell = Vector2i(MAP_W - 1 - depth, along)
		if _occupied.has(cell):
			continue
		_add_prop_at_cell(_pick_variant("body"), cell, Vector2(10, 5))
		placed += 1


func _add_lamp(cell: Vector2i) -> void:
	var working := _rng.randf() < LAMP_WORKING_CHANCE
	var lamp_name := "street_lamp" if working else _pick_variant("street_lamp_dead")
	var lamp := StreetLamp.new()
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 3.5   # a pole you actually bump into (user: collision)
	shape.shape = circle
	lamp.add_child(shape)
	lamp.add_child(_prop_sprite(lamp_name))
	var pos := _floor_layer.map_to_local(cell) \
		+ Vector2(_rng.randf_range(-4.0, 4.0), _rng.randf_range(-2.0, 2.0))
	lamp.position = pos.round()
	_ysort.add_child(lamp)
	lamp.setup(working, _rng.randi())
	_occupied[cell] = true


func _place_trees() -> void:
	# every forest cell is inside the map now — uniform woods density
	for cell in _forest:
		if _dirt_path.has(cell) or _occupied.has(cell):
			continue
		var roll := _rng.randf()
		if roll < 0.28:
			var autumn := _autumn_rect.has_point(cell as Vector2i)
			var variant := _pick_variant("tree_autumn" if autumn else "tree")
			var node := _add_prop_at_cell(variant, cell as Vector2i, Vector2(12, 6))
			_maybe_shed_leaves(variant, node, autumn)
			_map_trees.append(Vector3i((cell as Vector2i).x, (cell as Vector2i).y,
				1 if autumn else 0))
		elif roll < 0.33:
			_add_prop_at_cell(_pick_variant("stick"), cell as Vector2i, Vector2(14, 7))
		await _tick()


func _maybe_shed_leaves(variant: String, node: Node2D, red: bool = false) -> void:
	# EVERY broadleaf tree sheds, and only broadleaf trees do.
	# The old flat 50% roll had two faults the user caught between them:
	# a lone oak could lose the coin flip and sit there inert forever
	# ("a tree that doesnt have any leaves falling down, its the only
	# tree on the screen"), and a PINE or a bare DEAD snag could win it
	# and drop leaves out of a conifer. The tree family is pine 0-3,
	# oak 4-6, dead 7-8. More shedders costs nothing: the environment's
	# leaf timer caps the overall fall rate, so this buys variety in
	# where leaves come from, not more leaves.
	assert(variant != "")
	if red:
		_leaf_trees_red.append(node.position + Vector2(0, -30.0))
		return
	var index := int(variant.get_slice("_", 1))
	if index < 4 or index > 6:
		return                      # conifers and bare snags keep theirs
	_leaf_trees.append(node.position + Vector2(0, -30.0))


func _maybe_shed_bush(node: Node2D) -> void:
	# bushes are leafy too, and the same reasoning applies — all of them
	_leaf_trees.append(node.position + Vector2(0, -16.0))


func _place_lone_trees() -> void:
	# nature reclaiming the district: single trees and tiny green pockets
	# breaking through the concrete anywhere on the map
	var placed := 0
	var attempts := 0
	while placed < 55 and attempts < 1400:
		attempts += 1
		var cell := Vector2i(_rng.randi_range(EDGE_FOREST, MAP_W - EDGE_FOREST),
			_rng.randi_range(EDGE_FOREST, MAP_H - EDGE_FOREST))
		if _occupied.has(cell) or _forest.has(cell) or _dirt_path.has(cell) \
				or _next_to_road(cell) or _near_a_door(cell) \
				or _plaza.has(cell) or _apron.has(cell) \
				or _rail_cells.has(cell) or _ballast.has(cell):
			continue
		var inside_plot := false
		for plot in _plots:
			if (plot["rect"] as Rect2i).grow(1).has_point(cell):
				inside_plot = true
				break
		if inside_plot or Vector2(cell - _spawn_cell).length() < 4.0:
			continue
		# a small organic grass pocket, not a lone green tile — painted after
		# the terrain pass, so its concrete rim gets blend tiles here too
		var pocket: Array[Vector2i] = [cell]
		for extra in _rng.randi_range(1, 3):
			var gcell := cell + Vector2i(_rng.randi_range(-1, 1), _rng.randi_range(-1, 1))
			if not _occupied.has(gcell) and not _next_to_road(gcell) \
					and not _forest.has(gcell) and not _sidewalk.has(gcell) \
					and not _rail_cells.has(gcell) and not _ballast.has(gcell) \
					and not _plaza.has(gcell) and not _apron.has(gcell):
				pocket.append(gcell)
		for pcell in pocket:
			_set_tile(pcell, "forest_%d" % _rng.randi_range(0, 2))
			_forest[pcell] = true
		for pcell in pocket:
			for off in [Vector2i.RIGHT, Vector2i.LEFT, Vector2i.UP, Vector2i.DOWN]:
				var ncell: Vector2i = pcell + off
				if not _forest.has(ncell) and not _dirt_path.has(ncell) \
						and not _on_road(ncell) and not _occupied.has(ncell):
					_set_tile(ncell, "grass_blend_%d" % _rng.randi_range(0, 1))
		var lone_variant := _pick_variant("tree")
		_maybe_shed_leaves(lone_variant, _add_prop_at_cell(lone_variant, cell, Vector2(10, 5)))
		_map_trees.append(Vector3i(cell.x, cell.y, 0))
		if _rng.randf() < 0.5:
			var scell := cell + Vector2i(_rng.randi_range(-1, 1), _rng.randi_range(-1, 1))
			if not _occupied.has(scell) and not _on_road(scell):
				_add_prop_at_cell(_pick_variant("stick"), scell, Vector2(12, 6))
		placed += 1
		await _tick()


func _place_road_vehicles() -> void:
	# abandoned vehicles in their lanes — right way round, some broken into.
	# INTACT ones are driveable now: they spawn as DriveableCar bodies.
	for i in 20:
		await _tick()
		var vertical := _rng.randf() < 0.5
		var fam := ""
		var cell := Vector2i.ZERO
		var road_lo := 0
		var road_w := 4
		if vertical:
			var r: Vector2i = _roads_v[_rng.randi_range(0, _roads_v.size() - 1)]
			var left := _rng.randf() < 0.5
			cell = Vector2i(r.x + (_rng.randi_range(0, 1) if left else _rng.randi_range(2, 3)),
				_rng.randi_range(EDGE_FOREST + 2, MAP_H - EDGE_FOREST - 2))
			fam = "vehicle_ne" if left else "vehicle_sw"
			road_lo = r.x
			road_w = r.y
		else:
			var r: Vector2i = _roads_h[_rng.randi_range(0, _roads_h.size() - 1)]
			var top := _rng.randf() < 0.5
			cell = Vector2i(_rng.randi_range(EDGE_FOREST + 2, MAP_W - EDGE_FOREST - 2),
				r.x + (_rng.randi_range(0, 1) if top else _rng.randi_range(2, 3)))
			fam = "vehicle_se" if top else "vehicle_nw"
			road_lo = r.x
			road_w = r.y
		if _occupied.has(cell) or _near_a_door(cell) or _rail_cross.has(cell):
			continue
		var variant := _pick_variant(fam)
		var pos := _floor_layer.map_to_local(cell) \
			+ Vector2(_rng.randf_range(-5.0, 5.0), _rng.randf_range(-3.0, 3.0))
		_occupied[cell] = true
		if variant.ends_with("_5") or variant.ends_with("_6"):
			var wreck := _add_prop(variant, pos)
			# its litter got dragged to the SHOULDER — the road itself stays
			# clean (user: nothing on the asphalt but cracks and holes)
			for t in _rng.randi_range(2, 3):
				var lcell := cell
				if vertical:
					lcell.x = (road_lo - 1 - _rng.randi_range(0, 1)) \
						if _rng.randf() < 0.5 else (road_lo + road_w + _rng.randi_range(0, 1))
					lcell.y += _rng.randi_range(-1, 1)
				else:
					lcell.y = (road_lo - 1 - _rng.randi_range(0, 1)) \
						if _rng.randf() < 0.5 else (road_lo + road_w + _rng.randi_range(0, 1))
					lcell.x += _rng.randi_range(-1, 1)
				if not _occupied.has(lcell) and not _on_road(lcell):
					_add_prop_at_cell(_pick_variant("trash"), lcell, Vector2(10, 5))
			assert(wreck != null)
		else:
			var car := _spawn_driveable(variant, fam, pos)
			_maybe_arm_car(variant, car)


func _spawn_driveable(variant: String, fam: String, pos: Vector2) -> Node2D:
	# an intact car is a vehicle, not a prop: press F and drive it away
	var car := DriveableCar.new()
	car.position = pos.round()
	_ysort.add_child(car)
	car.setup(variant, fam.trim_prefix("vehicle_"), _manifest)
	_cars.append({"node": car})
	return car


func _scatter_props() -> void:
	# NO boxes in the open (user call): crates/stacks/pallets spawn only
	# around warehouses (below) and in their yards — the street junk is
	# barrels, tires, rubble, and the like
	await _scatter_warehouse_stock()
	var mix := [
		["barrel", 0.18], ["cylinder", 0.09], ["tires", 0.15],
		["dumpster", 0.15], ["rubble", 0.28], ["pillar", 0.07],
	]
	var total := 0.0
	for opt in mix:
		total += opt[1]
	var placed := 0
	var attempts := 0
	while placed < 210 and attempts < 6000:
		attempts += 1
		await _tick()
		var cell: Vector2i
		if _rng.randf() < 0.65 and not _plots.is_empty():
			# cluster near a building — loot gathers where people were
			var plot: Dictionary = _plots[_rng.randi_range(0, _plots.size() - 1)]
			var ring: Rect2i = (plot["rect"] as Rect2i).grow(_rng.randi_range(2, 4))
			cell = Vector2i(_rng.randi_range(ring.position.x, ring.end.x - 1),
				_rng.randi_range(ring.position.y, ring.end.y - 1))
		else:
			cell = Vector2i(_rng.randi_range(4, MAP_W - 5), _rng.randi_range(4, MAP_H - 5))
		if _cell_inset(cell) < EDGE_FOREST + 2:
			continue  # junk belongs INSIDE the barricade line
		if _occupied.has(cell) or _forest.has(cell) or _on_road(cell) \
				or _near_a_door(cell) or _plaza.has(cell) or _apron.has(cell) \
				or _rail_cells.has(cell) or _ballast.has(cell):
			continue
		var inside_plot := false
		for plot in _plots:
			if (plot["rect"] as Rect2i).has_point(cell):
				inside_plot = true
				break
		if inside_plot:
			continue
		if Vector2(cell - _spawn_cell).length() < 3.0:
			continue
		var roll := _rng.randf() * total
		for opt in mix:
			roll -= opt[1]
			if roll <= 0.0:
				var family: String = opt[0]
				# most junk lands alone; a quarter of it lands as a MESSY
				# heap — one anchor piece with stragglers spilling off one
				# side, never a tidy stack (user: asymmetrical piling)
				if _rng.randf() < 0.26 and family in ["barrel", "tires", "rubble"]:
					_place_pile(family, cell, _rng.randi_range(2, 4))
					placed += 1
				else:
					_add_prop(_pick_variant_varied(family),
						_floor_layer.map_to_local(cell) + _clutter_offset(11.0))
					_occupied[cell] = true
				break
		placed += 1
		if placed % 150 == 0:
			await _scene_tree.process_frame


func _scatter_warehouse_stock() -> void:
	# spilled stock hugs the warehouses it fell off of
	for plot in _plots:
		if plot["kind"] != "warehouse":
			continue
		await _tick()
		var ring: Rect2i = (plot["rect"] as Rect2i).grow(_rng.randi_range(2, 4))
		for i in _rng.randi_range(3, 6):
			var cell := Vector2i(_rng.randi_range(ring.position.x, ring.end.x - 1),
				_rng.randi_range(ring.position.y, ring.end.y - 1))
			if _occupied.has(cell) or _forest.has(cell) or _on_road(cell) \
					or _near_a_door(cell) or (plot["rect"] as Rect2i).has_point(cell):
				continue
			var item := _pick_variant(["crate", "crate_stack", "pallet"][_rng.randi_range(0, 2)])
			_add_prop_at_cell(item, cell, Vector2(8, 4))


func _bake_map_image() -> Image:
	# the district map the M key opens: one pixel per cell, drawn from the
	# same plans the terrain painted from, plus building/POI marks
	var img := Image.create(MAP_W, MAP_H, false, Image.FORMAT_RGBA8)
	for y in MAP_H:
		for x in MAP_W:
			var cell := Vector2i(x, y)
			var col := Color("202e37")
			var map_inset := _cell_inset(cell)
			if map_inset < BARRIER_INSET - 1:
				col = Color("10141f")            # sniper country, faded out
			elif map_inset < BARRIER_INSET:
				col = Color("4f5b66")            # the barricade ring itself
			elif _rail_cross.has(cell) or _rail_cells.has(cell):
				col = Color("341c27")
			elif _ballast.has(cell):
				col = Color("241527")
			elif _on_road(cell):
				col = Color("151d28")
			elif _sidewalk.has(cell):
				col = Color("577277")
			elif _plaza.has(cell):
				col = Color("819796")
			elif _apron.has(cell):
				col = Color("2a3540") if false else Color("151d28")
			elif _forest.has(cell):
				col = Color("19332d")
			elif _dirt_path.has(cell):
				col = Color("4d2b32")
			img.set_pixel(x, y, col)
	for plot in _plots:                          # buildings pop on the map
		var rect: Rect2i = plot["rect"]
		var fill := Color("884b2b") if plot["style"] == "brick_a" else Color("6a7f88")
		if plot["kind"] != "house":
			fill = Color("ad7757") if plot["kind"] == "school" else Color("8a9aa0")
		for y in range(rect.position.y, rect.end.y):
			for x in range(rect.position.x, rect.end.x):
				var edge: bool = x == rect.position.x or x == rect.end.x - 1 \
					or y == rect.position.y or y == rect.end.y - 1
				img.set_pixel(x, y, fill.darkened(0.25) if edge else fill)
	for t in _map_trees:                         # the woods, color-true
		img.set_pixel(t.x, t.y, Color("602c2c") if t.z == 1 else Color("25562e"))
	for plot in _plots:                          # home base pops bright
		if plot.get("safehouse", false):
			var r: Rect2i = plot["rect"]
			for x in range(r.position.x, r.end.x):
				img.set_pixel(x, r.position.y, Color("c7cfcc"))
				img.set_pixel(x, r.end.y - 1, Color("c7cfcc"))
			for y in range(r.position.y, r.end.y):
				img.set_pixel(r.position.x, y, Color("c7cfcc"))
				img.set_pixel(r.end.x - 1, y, Color("c7cfcc"))
	for mark in _map_marks:                      # static machine marks
		var cell: Vector2i = mark[0]
		if cell.x >= 0 and cell.y >= 0 and cell.x < MAP_W and cell.y < MAP_H:
			img.set_pixel(cell.x, cell.y, Color("de9e41"))
	return img


func _map_vectors() -> Dictionary:
	# SHAPES, not pixels: the map screen draws the district with real
	# strokes and fills (user: "vector drawn nice art, not pixel"), so it
	# needs the plan itself, not a 1px-per-cell bake.
	var roads_v: Array = []
	for r in _roads_v:
		roads_v.append([r.x, r.y])
	var roads_h: Array = []
	for r in _roads_h:
		roads_h.append([r.x, r.y])
	var blocks: Array = []
	for b in _block_rects:
		var br: Rect2i = _block_rects[b]
		blocks.append([br.position.x, br.position.y, br.size.x, br.size.y,
			str(_zones.get(b, "open"))])
	var buildings: Array = []
	for plot in _plots:
		var pr: Rect2i = plot["rect"]
		var kind := str(plot["kind"])
		if plot.get("safehouse", false):
			kind = "safehouse"
		buildings.append([pr.position.x, pr.position.y, pr.size.x, pr.size.y,
			kind, int(plot.get("stories", 1))])
	# the woods as coarse 3-cell buckets: a few hundred soft blobs read as
	# forest, where a per-tree pass would be thousands of draw calls
	var green: Dictionary = {}
	for cell in _forest:
		var c := cell as Vector2i
		var key := Vector2i(c.x / 3, c.y / 3)
		green[key] = int(green.get(key, 0)) + 1
	var groves: Array = []
	for key in green:
		var k := key as Vector2i
		var autumn := _autumn_rect.has_point(Vector2i(k.x * 3, k.y * 3))
		groves.append([k.x * 3, k.y * 3, int(green[key]), 1 if autumn else 0])
	var water: Array = []          # nothing wet in transit — the mills map
	return {                        # will want this slot
		"size": [MAP_W, MAP_H],
		"inset": BARRIER_INSET,
		"roads_v": roads_v,
		"roads_h": roads_h,
		"blocks": blocks,
		"buildings": buildings,
		"groves": groves,
		"water": water,
		"rail_row": _rail_row,
		"plaza": [_court_rect.position.x, _court_rect.position.y,
			_court_rect.size.x, _court_rect.size.y],
		"apron": [_depot_rect.position.x, _depot_rect.position.y,
			_depot_rect.size.x, _depot_rect.size.y],
		"spawn_cell": [_spawn_cell.x, _spawn_cell.y],
	}


func _collect_fog_spots() -> void:
	# where the dawn fog is allowed to live: through the woods, down the
	# roads — never anchored inside buildings (roofed cells are skipped by
	# the environment at spawn time anyway)
	for cell in _forest:
		if _rng.randf() < 0.05 and _cell_inset(cell as Vector2i) >= BARRIER_INSET:
			_fog_spots.append(_floor_layer.map_to_local(cell as Vector2i))
	for r in _roads_v:
		var y := BARRIER_INSET + 4
		while y < MAP_H - BARRIER_INSET:
			if _rng.randf() < 0.4:
				_fog_spots.append(_floor_layer.map_to_local(Vector2i(r.x + 1, y)))
			y += 9
	for r in _roads_h:
		var x := BARRIER_INSET + 4
		while x < MAP_W - BARRIER_INSET:
			if _rng.randf() < 0.4:
				_fog_spots.append(_floor_layer.map_to_local(Vector2i(x, r.x + 1)))
			x += 9
	if _rail_row >= 0:   # mist hangs over the rails at dawn — of course it does
		var rx := BARRIER_INSET + 4
		while rx < MAP_W - BARRIER_INSET:
			if _rng.randf() < 0.45:
				_fog_spots.append(_floor_layer.map_to_local(Vector2i(rx, _rail_row)))
			rx += 9


func _collect_puddle_spots() -> void:
	var tries := 0
	while _puddle_spots.size() < 70 and tries < 2000:
		tries += 1
		var cell := Vector2i(_rng.randi_range(EDGE_FOREST, MAP_W - EDGE_FOREST),
			_rng.randi_range(EDGE_FOREST, MAP_H - EDGE_FOREST))
		if not _on_road(cell) and _rng.randf() < 0.5:
			continue
		if _forest.has(cell) or _occupied.has(cell):
			continue
		_puddle_spots.append(_floor_layer.map_to_local(cell)
			+ Vector2(_rng.randf_range(-14, 14), _rng.randf_range(-7, 7)))


# ----------------------------------------------------------- boundaries -----

func _build_border_collision(root: Node2D) -> void:
	# 8-gon hugging the true diamond edge, tips chamfered so the camera clamp
	# can always keep the player on screen
	var top_c := _floor_layer.map_to_local(Vector2i(0, 0)) + Vector2(0, -16)
	var bottom_c := _floor_layer.map_to_local(Vector2i(MAP_W - 1, MAP_H - 1)) + Vector2(0, 16)
	var center := (top_c + bottom_c) / 2.0
	var half_h := (bottom_c.y - top_c.y) / 2.0
	var lb := half_h - 12.0                 # wall just inside the tiled edge
	var x_max := 2.0 * half_h - TIP_CUT_X
	var y_max := half_h - TIP_CUT_Y
	var xe := 2.0 * (lb - y_max)            # where the tip caps meet the edges
	var ye := lb - x_max / 2.0
	var corners: Array[Vector2] = [
		center + Vector2(xe, -y_max), center + Vector2(x_max, -ye),
		center + Vector2(x_max, ye), center + Vector2(xe, y_max),
		center + Vector2(-xe, y_max), center + Vector2(-x_max, ye),
		center + Vector2(-x_max, -ye), center + Vector2(-xe, -y_max),
	]
	var border := StaticBody2D.new()
	border.name = "Border"
	for i in corners.size():
		var a := corners[i]
		var b := corners[(i + 1) % corners.size()]
		var dir := (b - a).normalized()
		var normal := Vector2(dir.y, -dir.x)
		if normal.dot((a + b) / 2.0 - center) < 0.0:
			normal = -normal
		var poly := CollisionPolygon2D.new()
		poly.polygon = PackedVector2Array([a, b, b + normal * 96.0, a + normal * 96.0])
		border.add_child(poly)
	root.add_child(border)
