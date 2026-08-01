class_name WorldBuilder
extends RefCounted
## Builds the raid map: a 160x160 ruined district. Deterministic per seed.
## Consumes art/gen/manifest.json — sprite sizes, origins, colliders and
## variant families all come from the art pipeline.
##
## Layout is PLANNED first (roads, forests, dirt paths, building plots), then
## painted and populated. The outer band of the map is dense forest and the
## camera is limited well inside it, so the world visually never ends.

const MAP_W := 160
const MAP_H := 160
const TILE := Vector2i(64, 32)
const EDGE_FOREST := 14      # outer band that is always deep woods
const CAM_INSET := Vector2(560.0, 330.0)  # keep the void off-screen forever

var _rng := RandomNumberGenerator.new()
var _manifest: Dictionary = {}
var _floor_coords: Dictionary = {}
var _families: Dictionary = {}
var _wall_h := 40
var _floor_layer: TileMapLayer
var _ysort: Node2D
var _roofs: Array[RoofReveal] = []
var _occupied: Dictionary = {}

# plan state
var _roads_v: Array[Vector2i] = []   # (x_start, width)
var _roads_h: Array[Vector2i] = []
var _forest: Dictionary = {}         # Vector2i -> true
var _dirt_path: Dictionary = {}
var _plots: Array[Dictionary] = []   # {rect, kind, style, tone, ruined, door}
var _yards: Array[Rect2i] = []
var _spawn_cell := Vector2i(80, 80)
var _puddle_spots: Array[Vector2] = []


func build(root: Node2D) -> Dictionary:
	_rng.seed = hash("spoils-district-1")
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
	_plan_forest()
	_plan_paths()
	_plan_plots()

	_paint_terrain()
	for plot in _plots:
		_build_shell(plot)
	_place_yards()
	_place_lamps()
	_place_trees()
	_place_road_vehicles()
	_scatter_props()
	_collect_puddle_spots()
	_build_border_collision(root)

	var spawn := _floor_layer.map_to_local(_spawn_cell)
	return {
		"ysort": _ysort,
		"floor": _floor_layer,
		"spawn": spawn,
		"bounds": _camera_bounds(),
		"map_rect": _map_rect(),
		"roofs": _roofs,
		"cells": Vector2i(MAP_W, MAP_H),
		"puddle_spots": _puddle_spots,
	}


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
	var xs := [_rng.randi_range(34, 50), _rng.randi_range(74, 90), _rng.randi_range(114, 130)]
	for x in xs:
		_roads_v.append(Vector2i(x, 4))
	var ys := [_rng.randi_range(38, 54), _rng.randi_range(78, 94), _rng.randi_range(116, 132)]
	for y in ys:
		_roads_h.append(Vector2i(y, 4))


func _on_road(cell: Vector2i) -> bool:
	for r in _roads_v:
		if cell.x >= r.x and cell.x < r.x + r.y:
			return true
	for r in _roads_h:
		if cell.y >= r.x and cell.y < r.x + r.y:
			return true
	return false


func _plan_forest() -> void:
	for y in MAP_H:
		for x in MAP_W:
			if x < EDGE_FOREST or y < EDGE_FOREST \
					or x >= MAP_W - EDGE_FOREST or y >= MAP_H - EDGE_FOREST:
				var cell := Vector2i(x, y)
				if not _on_road(cell):
					_forest[cell] = true
	for i in 8:  # interior woods
		var cx := _rng.randi_range(EDGE_FOREST + 6, MAP_W - EDGE_FOREST - 6)
		var cy := _rng.randi_range(EDGE_FOREST + 6, MAP_H - EDGE_FOREST - 6)
		if _on_road(Vector2i(cx, cy)):
			continue
		var target := _rng.randi_range(140, 420)
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


func _plan_paths() -> void:
	# dirt roads wandering from the road grid into the woods
	for i in 4:
		var road := _roads_v[_rng.randi_range(0, _roads_v.size() - 1)]
		var y := _rng.randi_range(EDGE_FOREST + 4, MAP_H - EDGE_FOREST - 4)
		var x := road.x + road.y
		var dir := 1 if _rng.randf() < 0.5 else -1
		if dir < 0:
			x = road.x - 1
		var length := _rng.randi_range(18, 44)
		for step in length:
			for w in 2:
				_dirt_path[Vector2i(clampi(x, 1, MAP_W - 2), clampi(y + w, 1, MAP_H - 2))] = true
			x += dir
			if _rng.randf() < 0.35:
				y += _rng.randi_range(-1, 1)


func _plan_plots() -> void:
	var attempts := 0
	while _plots.size() < 12 and attempts < 300:
		attempts += 1
		var kind := "house" if _rng.randf() < 0.55 else "warehouse"
		var size := Vector2i(_rng.randi_range(6, 8), _rng.randi_range(5, 7)) \
			if kind == "house" else Vector2i(_rng.randi_range(9, 12), _rng.randi_range(7, 9))
		var pos := Vector2i(
			_rng.randi_range(EDGE_FOREST + 3, MAP_W - EDGE_FOREST - size.x - 3),
			_rng.randi_range(EDGE_FOREST + 3, MAP_H - EDGE_FOREST - size.y - 3))
		if _plots.size() == 0:  # first building near the spawn crossroads
			pos = Vector2i(_roads_v[1].x - size.x - 3, _roads_h[1].x - size.y - 3)
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
		})
	# spawn: near the central crossroads
	_spawn_cell = Vector2i(_roads_v[1].x + 6, _roads_h[1].x + 6)
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
			if _on_road(cell):
				tile_name = "asphalt_%d" % _rng.randi_range(0, 1)
				for r in _roads_v:
					if cell.x == r.x + 1 and _rng.randf() < 0.8:
						tile_name = "asphalt_line"
			_set_tile(cell, tile_name)


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
	node.position = pos
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


func _pick_variant(family: String) -> String:
	var names: Array = _families[family]
	return names[_rng.randi_range(0, names.size() - 1)]


func _take_random_cell(cells: Array[Vector2i]) -> Vector2i:
	var index := _rng.randi_range(0, cells.size() - 1)
	var cell: Vector2i = cells[index]
	cells.remove_at(index)
	return cell


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
		interior.end.x - 1 if door_side == "xp" else _rng.randi_range(interior.position.x + 1, interior.end.x - 2),
		interior.end.y - 1 if door_side == "yp" else _rng.randi_range(interior.position.y + 1, interior.end.y - 2))
	if door_side == "xp":
		door_cell.y = _rng.randi_range(interior.position.y + 1, interior.end.y - 2)
	else:
		door_cell.x = _rng.randi_range(interior.position.x + 1, interior.end.x - 2)

	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			_occupied[cell] = true
			# interior floor
			_set_tile(cell, ("wood_%d" % _rng.randi_range(0, 2)) if kind == "house"
				else ("screed_%d" % _rng.randi_range(0, 1)))
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
				var center := _floor_layer.map_to_local(cell)
				var verts: Array = _EDGE_VERTS[side]
				if side == door_side and cell == door_cell:
					for v in verts:
						posts[(center + (v as Vector2)).round()] = true
					# the door leaf, open against the inner wall beside the jamb
					var leaf := "door_wood" if kind == "house" else "door_metal"
					var along := (verts[1] as Vector2) - (verts[0] as Vector2)
					_add_prop(leaf, center + (_EDGE_OFFSET[side] as Vector2)
						- along.normalized() * 26.0 + Vector2(0, -2))
					continue
				var axis: String = _EDGE_AXIS[side]
				var piece := "seg_%s_%s" % [style, axis]
				if ruined and Vector2(cell - ruin_corner).length() < 3.0:
					if _rng.randf() < 0.25:
						for v in verts:
							posts[(center + (v as Vector2)).round()] = true
						continue
					piece = "seg_%s_%s_broken_%d" % [style, axis, _rng.randi_range(0, 1)]
				elif _rng.randf() < 0.3:
					piece = "seg_%s_%s_win_%d" % [style, axis, _rng.randi_range(0, 2)]
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

	_build_roof(interior, plot["tone"], posts.keys(), ruined)
	if kind == "house":
		_furnish_house(interior)
	else:
		_furnish_warehouse(interior)
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


func _furnish_house(interior: Rect2i) -> void:
	var p := interior.position
	var couch_side := _rng.randi_range(0, 1)
	var couch_cell := p + Vector2i(1, 1 + couch_side)
	var tv_cell := p + Vector2i(3, 1 + couch_side)
	_add_prop_at_cell("couch", couch_cell, Vector2(6, 3))
	_add_prop_at_cell("tv_stand", tv_cell, Vector2(4, 2))
	# back-wall pieces: distinct random slots, both always present
	var wall_cells: Array[Vector2i] = []
	for x in range(interior.position.x, interior.end.x):
		var cell := Vector2i(x, p.y)
		if cell != couch_cell and cell != tv_cell:
			wall_cells.append(cell)
	wall_cells.shuffle()
	for piece in ["cabinet", "bookshelf"]:
		if wall_cells.is_empty():
			break
		_add_prop_at_cell(piece, wall_cells.pop_front(), Vector2(6, 2))
	# domestic extras only — no industrial barrels indoors (user call)
	var cells := _interior_free_cells(interior, [couch_cell, tv_cell])
	var extras := ["table", "chair", "chair", "crate_%d" % _rng.randi_range(0, 5)]
	extras.shuffle()
	for i in _rng.randi_range(2, 3):
		if cells.is_empty():
			break
		_add_prop_at_cell(extras[i - 1], _take_random_cell(cells), Vector2(8, 4))


func _furnish_warehouse(interior: Rect2i) -> void:
	var p := interior.position
	var rack_slots: Array[int] = []
	for x_offset in range(1, interior.size.x - 1, 2):
		rack_slots.append(x_offset)
	rack_slots.shuffle()
	var used: Array[Vector2i] = []
	for i in _rng.randi_range(2, mini(3, rack_slots.size())):
		var cell := Vector2i(p.x + rack_slots[i - 1], p.y)
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
		for y in range(yard.position.y, yard.end.y):
			for x in range(yard.position.x, yard.end.x):
				var cell := Vector2i(x, y)
				if (x - yard.position.x) % 3 == 2 and y < yard.end.y - 1:
					_set_tile(cell, "asphalt_stall")
				else:
					_set_tile(cell, "asphalt_%d" % _rng.randi_range(0, 1))
		var stall_cells: Array[Vector2i] = []
		for sx in range(yard.position.x + 1, yard.end.x - 1, 3):
			stall_cells.append(Vector2i(sx, yard.position.y + 1))
		stall_cells.shuffle()
		for i in mini(_rng.randi_range(1, 3), stall_cells.size()):
			_add_prop_at_cell(_pick_variant("vehicle"), stall_cells[i - 1], Vector2(6, 3))
		var spill_cells: Array[Vector2i] = []
		for y in range(yard.position.y, yard.end.y):
			for x in range(yard.position.x, yard.end.x):
				if not _occupied.has(Vector2i(x, y)):
					spill_cells.append(Vector2i(x, y))
		for i in _rng.randi_range(2, 4):
			if spill_cells.is_empty():
				break
			var item := _pick_variant(["crate", "crate_stack", "pallet"][_rng.randi_range(0, 2)])
			_add_prop_at_cell(item, _take_random_cell(spill_cells), Vector2(6, 3))
		for y in range(yard.position.y, yard.end.y):
			for x in range(yard.position.x, yard.end.x):
				_occupied[Vector2i(x, y)] = true


func _place_lamps() -> void:
	for r in _roads_v:
		var y := EDGE_FOREST + _rng.randi_range(2, 6)
		while y < MAP_H - EDGE_FOREST:
			var cell := Vector2i(r.x - 1, y)
			if not _occupied.has(cell) and not _forest.has(cell) and not _on_road(cell):
				_add_prop_at_cell("street_lamp", cell, Vector2(4, 2))
			y += _rng.randi_range(7, 10)
	for r in _roads_h:
		var x := EDGE_FOREST + _rng.randi_range(2, 6)
		while x < MAP_W - EDGE_FOREST:
			var cell := Vector2i(x, r.x + r.y)
			if not _occupied.has(cell) and not _forest.has(cell) and not _on_road(cell):
				_add_prop_at_cell("street_lamp", cell, Vector2(4, 2))
			x += _rng.randi_range(7, 10)


func _place_trees() -> void:
	for cell in _forest:
		if _dirt_path.has(cell) or _occupied.has(cell):
			continue
		if _rng.randf() < 0.3:
			_add_prop_at_cell(_pick_variant("tree"), cell as Vector2i, Vector2(12, 6))


func _place_road_vehicles() -> void:
	# a few abandoned vehicles along the roads
	for i in 8:
		var r: Vector2i = _roads_v[_rng.randi_range(0, _roads_v.size() - 1)]
		var cell := Vector2i(r.x + _rng.randi_range(0, r.y - 1),
			_rng.randi_range(EDGE_FOREST + 2, MAP_H - EDGE_FOREST - 2))
		if _occupied.has(cell):
			continue
		_add_prop_at_cell(_pick_variant("vehicle"), cell, Vector2(8, 4))


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
	while placed < 170 and attempts < 3000:
		attempts += 1
		var cell: Vector2i
		if _rng.randf() < 0.65 and not _plots.is_empty():
			# cluster near a building — loot gathers where people were
			var plot: Dictionary = _plots[_rng.randi_range(0, _plots.size() - 1)]
			var ring: Rect2i = (plot["rect"] as Rect2i).grow(_rng.randi_range(2, 5))
			cell = Vector2i(_rng.randi_range(ring.position.x, ring.end.x - 1),
				_rng.randi_range(ring.position.y, ring.end.y - 1))
		else:
			cell = Vector2i(_rng.randi_range(4, MAP_W - 5), _rng.randi_range(4, MAP_H - 5))
		if _occupied.has(cell) or _forest.has(cell) or _on_road(cell):
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


func _collect_puddle_spots() -> void:
	var tries := 0
	while _puddle_spots.size() < 40 and tries < 600:
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

func _playable_corners() -> Array[Vector2]:
	var inset := EDGE_FOREST - 6  # the wall stands deep inside the woods
	return [
		_floor_layer.map_to_local(Vector2i(inset, inset)),
		_floor_layer.map_to_local(Vector2i(MAP_W - inset, inset)),
		_floor_layer.map_to_local(Vector2i(MAP_W - inset, MAP_H - inset)),
		_floor_layer.map_to_local(Vector2i(inset, MAP_H - inset)),
	]


func _build_border_collision(root: Node2D) -> void:
	var corners := _playable_corners()
	var center := (corners[0] + corners[2]) / 2.0
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


func _camera_bounds() -> Rect2:
	# camera limits sit far enough inside the filled map that the void can
	# never appear on screen — the world reads as endless
	var min_x := _floor_layer.map_to_local(Vector2i(0, MAP_H - 1)).x - 32.0
	var max_x := _floor_layer.map_to_local(Vector2i(MAP_W - 1, 0)).x + 32.0
	var min_y := _floor_layer.map_to_local(Vector2i(0, 0)).y - 16.0
	var max_y := _floor_layer.map_to_local(Vector2i(MAP_W - 1, MAP_H - 1)).y + 16.0
	return Rect2(min_x + CAM_INSET.x, min_y + CAM_INSET.y,
		(max_x - min_x) - CAM_INSET.x * 2.0, (max_y - min_y) - CAM_INSET.y * 2.0)
