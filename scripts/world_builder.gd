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

const MAP_W := 320
const MAP_H := 320
const TILE := Vector2i(64, 32)
const EDGE_FOREST := 34      # treeline: woods start just inside the barriers
const BARRIER_INSET := 31    # the barricade ring — the map's ADVERTISED edge.
# Everything gameplay lives inside it; the 31-tile band beyond is sniper
# country, deep enough that a player who ignores the warning dies (escalating
# fire) long before the camera — which never clamps — could reach the void.
const ROAD_COUNT := 5        # per axis
const LAMP_WORKING_CHANCE := 0.42  # the district is dead; most lamps are too
const BUILD_BUDGET_US := 2400  # max build work per frame: the deploy screen
                               # must hold the user's full refresh rate
# border collision at the true diamond edge (an absolute backstop; the
# sniper is the real wall). Tips chamfered a little for good measure.
const TIP_CUT_X := 560.0
const TIP_CUT_Y := 256.0

var _rng := RandomNumberGenerator.new()
var _manifest: Dictionary = {}
var _floor_coords: Dictionary = {}
var _families: Dictionary = {}
var _wall_h := 40
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


func build(root: Node2D, seed_text: String = "") -> Dictionary:
	# every deploy rolls a fresh district; a pinned seed (harness --seed=x)
	# reproduces a layout exactly — ALL randomness below flows from _rng
	if seed_text.is_empty():
		seed_text = "district-%d" % Time.get_ticks_usec()
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

	_plan_roads()
	await _plan_forest()
	_plan_paths()
	await _plan_plots()

	await _paint_terrain()
	for plot in _plots:
		await _build_shell(plot)
	await _place_yards()
	await _place_lamps()
	await _place_barricades()
	await _place_trees()
	await _place_lone_trees()
	await _place_road_vehicles()
	await _scatter_props()
	_collect_puddle_spots()
	_build_border_collision(root)

	var spawn := _floor_layer.map_to_local(_spawn_cell)
	var top_c := _floor_layer.map_to_local(Vector2i(0, 0)) + Vector2(0, -16)
	var bottom_c := _floor_layer.map_to_local(Vector2i(MAP_W - 1, MAP_H - 1)) + Vector2(0, 16)
	return {
		"ysort": _ysort,
		"floor": _floor_layer,
		"spawn": spawn,
		"bounds": _map_rect(),
		"map_rect": _map_rect(),
		"map_center": (top_c + bottom_c) / 2.0,
		"map_half_h": (bottom_c.y - top_c.y) / 2.0,
		# f-metric value of the barricade ring (|dx|/2 + |dy| from center);
		# crossing it puts you in sniper country
		"barrier_f": 32.0 * ((float(MAP_W) - 1.0) * 0.5 - float(BARRIER_INSET)),
		"roofs": _roofs,
		"cells": Vector2i(MAP_W, MAP_H),
		"puddle_spots": _puddle_spots,
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
	var span := MAP_W - 64
	for i in ROAD_COUNT:
		@warning_ignore("integer_division")
		var base := 32 + span * i / (ROAD_COUNT - 1)
		_roads_v.append(Vector2i(clampi(base + _rng.randi_range(-9, 9), 18, MAP_W - 24), 4))
	for i in ROAD_COUNT:
		@warning_ignore("integer_division")
		var base := 32 + span * i / (ROAD_COUNT - 1)
		_roads_h.append(Vector2i(clampi(base + _rng.randi_range(-9, 9), 18, MAP_H - 24), 4))


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


func _plan_forest() -> void:
	for y in MAP_H:
		for x in MAP_W:
			if x < EDGE_FOREST or y < EDGE_FOREST \
					or x >= MAP_W - EDGE_FOREST or y >= MAP_H - EDGE_FOREST:
				var cell := Vector2i(x, y)
				if not _on_road(cell):
					_forest[cell] = true
		await _tick()
	# interior woods: big blobs AND small groves — trees live INSIDE the map,
	# not just along its rim
	var blobs: Array[Vector2i] = []
	for i in 26:
		blobs.append(Vector2i(_rng.randi_range(160, 520), 0))
	for i in 90:
		blobs.append(Vector2i(_rng.randi_range(2, 10), 1))
	for blob in blobs:
		var cx := _rng.randi_range(EDGE_FOREST + 6, MAP_W - EDGE_FOREST - 6)
		var cy := _rng.randi_range(EDGE_FOREST + 6, MAP_H - EDGE_FOREST - 6)
		if _on_road(Vector2i(cx, cy)):
			continue
		var target := blob.x
		var frontier: Array[Vector2i] = [Vector2i(cx, cy)]
		var grown := 0
		while grown < target and not frontier.is_empty():
			var cell: Vector2i = frontier.pop_at(_rng.randi_range(0, frontier.size() - 1))
			if _forest.has(cell) or _on_road(cell):
				continue
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
	for i in 10:
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


func _plan_plots() -> void:
	var attempts := 0
	while _plots.size() < 34 and attempts < 1400:
		attempts += 1
		await _tick()
		var kind := "house" if _rng.randf() < 0.55 else "warehouse"
		var size := Vector2i(_rng.randi_range(6, 8), _rng.randi_range(5, 7)) \
			if kind == "house" else Vector2i(_rng.randi_range(9, 12), _rng.randi_range(7, 9))
		var pos := Vector2i(
			_rng.randi_range(EDGE_FOREST + 3, MAP_W - EDGE_FOREST - size.x - 3),
			_rng.randi_range(EDGE_FOREST + 3, MAP_H - EDGE_FOREST - size.y - 3))
		if _plots.is_empty() and attempts == 1:
			# try the spawn crossroads for the first building — but only once,
			# falling back to random spots if that corner happens to be blocked
			pos = Vector2i(_roads_v[2].x - size.x - 3, _roads_h[2].x - size.y - 3)
		var rect := Rect2i(pos, size)
		if not _rect_clear(rect.grow(3)):
			continue
		var door_side := "xp" if _rng.randf() < 0.5 else "yp"
		_plots.append({
			"rect": rect, "kind": kind,
			"style": "brick_a" if _rng.randf() < 0.5 else "brick_b",
			"tone": "charcoal" if _rng.randf() < 0.5 else "pitch",
			"ruined": _rng.randf() < (0.2 if kind == "house" else 0.4),
			"door_side": door_side,
			"door_out": Vector2i(-99, -99),
		})
	# spawn: near the central crossroads
	_spawn_cell = Vector2i(_roads_v[2].x + 6, _roads_h[2].x + 6)
	while _on_road(_spawn_cell) or _forest.has(_spawn_cell):
		_spawn_cell += Vector2i(1, 1)


func _rect_clear(rect: Rect2i) -> bool:
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var cell := Vector2i(x, y)
			if _on_road(cell) or _forest.has(cell) or _dirt_path.has(cell):
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
			var roll := _rng.randf()
			if roll < 0.03:
				tile_name = "crack_%d" % _rng.randi_range(0, 2)
			elif roll < 0.045:
				tile_name = "stain_%d" % _rng.randi_range(0, 1)
			elif roll < 0.055:
				tile_name = "moss_0"
			if _forest.has(cell):
				tile_name = "forest_%d" % _rng.randi_range(0, 2)
			if _dirt_path.has(cell):
				tile_name = "dirt_%d" % _rng.randi_range(0, 2)
			var road_v := _road_v_at(cell)
			var road_h := _road_h_at(cell)
			if road_v >= 0 or road_h >= 0:
				tile_name = "asphalt_%d" % _rng.randi_range(0, 1)
				# center dashes — on BOTH road directions, never at crossings
				if road_v >= 0 and road_h < 0 and cell.x == road_v + 1 \
						and _rng.randf() < 0.96:
					tile_name = "asphalt_line"
				elif road_h >= 0 and road_v < 0 and cell.y == road_h + 1 \
						and _rng.randf() < 0.96:
					tile_name = "asphalt_line_h"
			_set_tile(cell, tile_name)
		await _tick()


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
		jitter: Vector2 = Vector2.ZERO) -> void:
	var pos := _floor_layer.map_to_local(cell)
	if jitter != Vector2.ZERO:
		pos += Vector2(_rng.randf_range(-jitter.x, jitter.x), _rng.randf_range(-jitter.y, jitter.y))
	_add_prop(prop_name, pos)
	_occupied[cell] = true


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


func _build_shell(plot: Dictionary) -> void:
	var rect: Rect2i = plot["rect"]
	var style: String = plot["style"]
	var kind: String = plot["kind"]
	var ruined: bool = plot["ruined"]
	var door_side: String = plot["door_side"]
	var interior: Rect2i = rect.grow(-1)
	var ruin_corner: Vector2i = interior.end - Vector2i(1, 1)
	var posts: Dictionary = {}
	var door_cell := Vector2i(
		interior.end.x - 1 if door_side == "xp" else 0,
		interior.end.y - 1 if door_side == "yp" else 0)
	if door_side == "xp":
		door_cell.y = _rng.randi_range(interior.position.y + 1, interior.end.y - 2)
	else:
		door_cell.x = _rng.randi_range(interior.position.x + 1, interior.end.x - 2)
	plot["door_out"] = door_cell + (_DOOR_OUTWARD[door_side] as Vector2i) * 2

	# ONE floor for the whole building — per-cell variants made interiors a
	# patchwork of mismatched tiles (user call: uniform flooring per house)
	var floor_tile := ("wood_%d" % _rng.randi_range(0, 2)) if kind == "house" \
		else ("screed_%d" % _rng.randi_range(0, 1))

	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			_occupied[cell] = true
			_set_tile(cell, floor_tile)
			var sides: Array[String] = []
			if x == interior.position.x:
				sides.append("xn")
			if x == interior.end.x - 1:
				sides.append("xp")
			if y == interior.position.y:
				sides.append("yn")
			if y == interior.end.y - 1:
				sides.append("yp")
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
					continue
				var axis2: String = _EDGE_AXIS[side]
				var piece := "seg_%s_%s" % [style, axis2]
				if ruined and Vector2(cell - ruin_corner).length() < 3.0:
					if _rng.randf() < 0.25:
						for v in verts:
							posts[(center + (v as Vector2)).round()] = true
						continue
					piece = "seg_%s_%s_broken_%d" % [style, axis2, _rng.randi_range(0, 1)]
				elif _rng.randf() < 0.3:
					piece = "seg_%s_%s_win_%d" % [style, axis2, _rng.randi_range(0, 2)]
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
		_add_prop("post_%s" % style, pos as Vector2)

	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			_occupied[Vector2i(x, y)] = true

	await _build_roof(interior, plot["tone"], posts.keys(), ruined)

	# the entrance pocket: the door cell and everything around it stays empty
	var pocket: Array[Vector2i] = [door_cell]
	var inward: Vector2i = _DOOR_INWARD[door_side]
	var along: Vector2i = _DOOR_ALONG[door_side]
	for offset in [inward, inward + along, inward - along, along, -along]:
		var pcell: Vector2i = door_cell + offset
		if interior.has_point(pcell):
			pocket.append(pcell)

	if kind == "house":
		_furnish_house(interior, pocket)
	else:
		_furnish_warehouse(interior, pocket)
		var yard := Rect2i(rect.position.x + 1, rect.end.y + 1, rect.size.x - 1, 4)
		if _yard_fits(yard):
			_yards.append(yard)


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
		ruined: bool) -> void:
	var south_corner := interior.end - Vector2i(1, 1)
	var roof := RoofReveal.new()
	roof.cells = interior
	roof.position = _floor_layer.map_to_local(south_corner) + Vector2(0, 24)
	var lift := Vector2(0, -float(_wall_h))
	var ruin_corner := interior.end - Vector2i(1, 1)
	for y in range(interior.position.y, interior.end.y):
		await _tick()
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			var tile_name := "roof_tile_%s_%d" % [tone, _rng.randi_range(0, 1)]
			if ruined and Vector2(cell - ruin_corner).length() < 3.0 and _rng.randf() < 0.6:
				tile_name = "roof_tile_%s_broken_%d" % [tone, _rng.randi_range(0, 1)]
			var tile := _prop_sprite(tile_name)
			tile.position = _floor_layer.map_to_local(cell) - roof.position + lift
			roof.add_child(tile)
			var sides: Array[String] = []
			if x == interior.position.x:
				sides.append("xn")
			if x == interior.end.x - 1:
				sides.append("xp")
			if y == interior.position.y:
				sides.append("yn")
			if y == interior.end.y - 1:
				sides.append("yp")
			for side in sides:
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


func _furnish_house(interior: Rect2i, pocket: Array[Vector2i]) -> void:
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
	_add_prop_at_cell("couch", couch_cell, Vector2(6, 3))
	_add_prop_at_cell("tv_stand", tv_cell, Vector2(4, 2))
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
		_add_prop_at_cell(piece, wall_cells.pop_front(), Vector2(6, 2))
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
		_add_prop_at_cell(extras[i - 1], _take_random_cell(cells), Vector2(8, 4))


func _furnish_warehouse(interior: Rect2i, pocket: Array[Vector2i]) -> void:
	var p := interior.position
	var rack_slots: Array[int] = []
	for x_offset in range(1, interior.size.x - 1, 2):
		rack_slots.append(x_offset)
	_shuffle(rack_slots)
	var used: Array[Vector2i] = pocket.duplicate()
	for i in _rng.randi_range(2, mini(3, rack_slots.size())):
		var cell := Vector2i(p.x + rack_slots[i - 1], p.y)
		if cell in pocket:
			continue
		_add_prop_at_cell(_pick_variant("rack"), cell, Vector2(8, 2))
		used.append(cell)
	var cells := _interior_free_cells(interior, used)
	var stock_mix := [
		["crate_stack", 0.24], ["crate", 0.22], ["pallet", 0.18],
		["barrel", 0.20], ["cylinder", 0.16],
	]
	var total := 0.0
	for opt in stock_mix:
		total += opt[1]
	for i in _rng.randi_range(5, 9):
		if cells.is_empty():
			break
		var cell := _take_random_cell(cells)
		var roll := _rng.randf() * total
		for opt in stock_mix:
			roll -= opt[1]
			if roll <= 0.0:
				_add_prop_at_cell(_pick_variant(opt[0]), cell, Vector2(10, 5))
				break


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
			_add_prop_at_cell(_pick_variant(fam), stall_cells[i - 1], Vector2(6, 3))
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


func _place_barricades() -> void:
	# the barricade ring — the map's ADVERTISED edge. Randomized pieces with
	# slip-through gaps, some knocked flat; roads breach the line with
	# flattened wreckage on the asphalt. The world continues beyond it.
	var lo := BARRIER_INSET
	var hi_x := MAP_W - 1 - BARRIER_INSET
	var hi_y := MAP_H - 1 - BARRIER_INSET
	await _ring_side("x", lo, lo, hi_x, true)
	await _ring_side("x", hi_y, lo, hi_x, false)
	await _ring_side("y", lo, lo + 2, hi_y - 2, false)
	await _ring_side("y", hi_x, lo + 2, hi_y - 2, true)
	await _place_bodies()


func _ring_side(axis: String, fixed: int, from: int, to: int, _far: bool) -> void:
	var i := from + _rng.randi_range(0, 2)
	while i <= to:
		# x-running sides vary cx (cy fixed); y-running sides vary cy
		var cell := Vector2i(i, fixed) if axis == "x" else Vector2i(fixed, i)
		i += _rng.randi_range(2, 4)
		await _tick()
		if _occupied.has(cell):
			continue
		if _on_road(cell):
			if _rng.randf() < 0.55:
				_add_prop_at_cell(_pick_variant("barricade_%s_flat" % axis), cell,
					Vector2(10, 5))
			continue
		if _rng.randf() < 0.08:
			continue  # a clean gap — you can always slip through somewhere
		var fam := "barricade_" + axis
		if _rng.randf() < 0.2:
			fam += "_flat"
		_add_prop_at_cell(_pick_variant(fam), cell, Vector2(5, 2))


func _place_bodies() -> void:
	# fallen raiders PAST the line, sparse — the sniper warning, made visible
	var count := _rng.randi_range(14, 20)
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
	circle.radius = 2.0
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
	# density falls off past the barricades: full woods where the player
	# lives, thinning into the sniper's buffer (which is scenery, not a hike)
	for cell in _forest:
		if _dirt_path.has(cell) or _occupied.has(cell):
			continue
		var inset := _cell_inset(cell as Vector2i)
		var chance := 0.28
		if inset < 12:
			chance = 0.04
		elif inset < 26:
			chance = 0.12
		var roll := _rng.randf()
		if roll < chance:
			_add_prop_at_cell(_pick_variant("tree"), cell as Vector2i, Vector2(12, 6))
		elif roll < chance + 0.05 and inset >= 20:
			_add_prop_at_cell(_pick_variant("stick"), cell as Vector2i, Vector2(14, 7))
		await _tick()


func _place_lone_trees() -> void:
	# nature reclaiming the district: single trees and tiny green pockets
	# breaking through the concrete anywhere on the map
	var placed := 0
	var attempts := 0
	while placed < 240 and attempts < 3000:
		attempts += 1
		var cell := Vector2i(_rng.randi_range(EDGE_FOREST, MAP_W - EDGE_FOREST),
			_rng.randi_range(EDGE_FOREST, MAP_H - EDGE_FOREST))
		if _occupied.has(cell) or _forest.has(cell) or _dirt_path.has(cell) \
				or _on_road(cell) or _near_a_door(cell):
			continue
		var inside_plot := false
		for plot in _plots:
			if (plot["rect"] as Rect2i).grow(1).has_point(cell):
				inside_plot = true
				break
		if inside_plot or Vector2(cell - _spawn_cell).length() < 4.0:
			continue
		_set_tile(cell, "forest_%d" % _rng.randi_range(0, 2))
		_add_prop_at_cell(_pick_variant("tree"), cell, Vector2(10, 5))
		if _rng.randf() < 0.5:
			var scell := cell + Vector2i(_rng.randi_range(-1, 1), _rng.randi_range(-1, 1))
			if not _occupied.has(scell) and not _on_road(scell):
				_add_prop_at_cell(_pick_variant("stick"), scell, Vector2(12, 6))
		placed += 1
		await _tick()


func _place_road_vehicles() -> void:
	# abandoned vehicles in their lanes — right way round, some broken into
	for i in 36:
		await _tick()
		var vertical := _rng.randf() < 0.5
		var fam := ""
		var cell := Vector2i.ZERO
		if vertical:
			var r: Vector2i = _roads_v[_rng.randi_range(0, _roads_v.size() - 1)]
			var left := _rng.randf() < 0.5
			cell = Vector2i(r.x + (_rng.randi_range(0, 1) if left else _rng.randi_range(2, 3)),
				_rng.randi_range(EDGE_FOREST + 2, MAP_H - EDGE_FOREST - 2))
			fam = "vehicle_ne" if left else "vehicle_sw"
		else:
			var r: Vector2i = _roads_h[_rng.randi_range(0, _roads_h.size() - 1)]
			var top := _rng.randf() < 0.5
			cell = Vector2i(_rng.randi_range(EDGE_FOREST + 2, MAP_W - EDGE_FOREST - 2),
				r.x + (_rng.randi_range(0, 1) if top else _rng.randi_range(2, 3)))
			fam = "vehicle_se" if top else "vehicle_nw"
		if _occupied.has(cell) or _near_a_door(cell):
			continue
		var variant := _pick_variant(fam)
		var pos := _floor_layer.map_to_local(cell) \
			+ Vector2(_rng.randf_range(-5.0, 5.0), _rng.randf_range(-3.0, 3.0))
		_add_prop(variant, pos)
		_occupied[cell] = true
		if variant.ends_with("_3") or variant.ends_with("_4"):
			# broken into: it's been through some stuff — litter around it
			for t in _rng.randi_range(2, 4):
				_add_prop(_pick_variant("trash"), pos + Vector2(
					_rng.randf_range(-30.0, 30.0), _rng.randf_range(-16.0, 16.0)))


func _scatter_props() -> void:
	var mix := [
		["barrel", 0.16], ["cylinder", 0.08], ["crate", 0.14], ["tires", 0.12],
		["pallet", 0.10], ["dumpster", 0.06], ["rubble", 0.22], ["pillar", 0.06],
		["crate_stack", 0.06],
	]
	var total := 0.0
	for opt in mix:
		total += opt[1]
	var placed := 0
	var attempts := 0
	while placed < 620 and attempts < 12000:
		attempts += 1
		await _tick()
		var cell: Vector2i
		if _rng.randf() < 0.65 and not _plots.is_empty():
			# cluster near a building — loot gathers where people were
			var plot: Dictionary = _plots[_rng.randi_range(0, _plots.size() - 1)]
			var ring: Rect2i = (plot["rect"] as Rect2i).grow(_rng.randi_range(2, 5))
			cell = Vector2i(_rng.randi_range(ring.position.x, ring.end.x - 1),
				_rng.randi_range(ring.position.y, ring.end.y - 1))
		else:
			cell = Vector2i(_rng.randi_range(4, MAP_W - 5), _rng.randi_range(4, MAP_H - 5))
		if _cell_inset(cell) < EDGE_FOREST + 2:
			continue  # junk belongs INSIDE the barricade line
		if _occupied.has(cell) or _forest.has(cell) or _on_road(cell) \
				or _near_a_door(cell):
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
				_add_prop_at_cell(_pick_variant(opt[0]), cell, Vector2(10, 5))
				break
		placed += 1
		if placed % 150 == 0:
			await _scene_tree.process_frame


func _collect_puddle_spots() -> void:
	var tries := 0
	while _puddle_spots.size() < 130 and tries < 2400:
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
