class_name WorldBuilder
extends RefCounted
## Builds the M1 map: a ruined industrial block, ~48x48 iso tiles.
## Deterministic (fixed RNG seed). Consumes art/gen/manifest.json — sprite
## sizes, origins, collider shapes and prop families all come from the art
## pipeline, so the game never hardcodes what the generator produced.

const MAP_W := 48
const MAP_H := 48
const TILE := Vector2i(64, 32)
const ROAD_A_X := Vector2i(22, 25)  # column band, runs screen down-left
const ROAD_B_Y := Vector2i(26, 29)  # row band, runs screen down-right
# deliberately different footprints: A is a small house, B a big warehouse
const BUILDING_A := Rect2i(9, 8, 7, 6)
const BUILDING_B := Rect2i(29, 32, 10, 8)
const SPAWN_CELL := Vector2i(18, 13)
const LOT := Rect2i(30, 40, 9, 4)  # loading yard south of the warehouse

var _rng := RandomNumberGenerator.new()
var _manifest: Dictionary = {}
var _floor_coords: Dictionary = {}
var _families: Dictionary = {}
var _wall_h := 40
var _floor_layer: TileMapLayer
var _ysort: Node2D
var _roofs: Array[RoofReveal] = []
var _occupied: Dictionary = {}  # Vector2i -> true, cells that block scatter


func build(root: Node2D) -> Dictionary:
	_rng.seed = hash("spoils-m1-map")
	_manifest = _load_manifest()

	_floor_layer = TileMapLayer.new()
	_floor_layer.name = "Floor"
	_floor_layer.tile_set = _make_tileset()
	root.add_child(_floor_layer)

	_ysort = Node2D.new()
	_ysort.name = "World"
	_ysort.y_sort_enabled = true
	root.add_child(_ysort)

	var terrain := _layout_terrain()
	for y in MAP_H:
		var row: Array = terrain[y]
		for x in MAP_W:
			var tile_name: String = row[x]
			var tc: Array = _floor_coords[tile_name]
			_floor_layer.set_cell(Vector2i(x, y), 0, Vector2i(int(tc[0]), int(tc[1])))

	_place_buildings()
	_place_warehouse_yard()
	_place_perimeter()
	_place_fixed_props()
	_scatter_props()
	_build_border_collision(root)

	var spawn := _floor_layer.map_to_local(SPAWN_CELL)
	return {
		"ysort": _ysort,
		"floor": _floor_layer,
		"spawn": spawn,
		"bounds": _world_bounds(),
		"roofs": _roofs,
	}


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


# ------------------------------------------------------------- terrain ------

func _layout_terrain() -> Array:
	var terrain: Array = []
	for y in MAP_H:
		var row: Array = []
		for x in MAP_W:
			row.append("concrete_%d" % _rng.randi_range(0, 5))
		terrain.append(row)

	for y in MAP_H:
		for x in MAP_W:
			var roll := _rng.randf()
			if roll < 0.035:
				terrain[y][x] = "crack_%d" % _rng.randi_range(0, 2)
			elif roll < 0.055:
				terrain[y][x] = "stain_%d" % _rng.randi_range(0, 1)
			elif roll < 0.068:
				terrain[y][x] = "moss_0"

	var dirt: Dictionary = {}
	for i in 7:
		var cx := _rng.randi_range(4, MAP_W - 5)
		var cy := _rng.randi_range(4, MAP_H - 5)
		var radius := _rng.randi_range(2, 4)
		for y in range(cy - radius, cy + radius + 1):
			for x in range(cx - radius, cx + radius + 1):
				if x < 0 or y < 0 or x >= MAP_W or y >= MAP_H:
					continue
				if Vector2(x - cx, y - cy).length() <= radius + _rng.randf() - 0.5:
					terrain[y][x] = "dirt_%d" % _rng.randi_range(0, 2)
					dirt[Vector2i(x, y)] = true
	for y in MAP_H:
		for x in MAP_W:
			var cell := Vector2i(x, y)
			if dirt.has(cell):
				continue
			for off in [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1)]:
				if dirt.has(cell + off):
					terrain[y][x] = "dirt_blend_%d" % _rng.randi_range(0, 1)
					break

	for y in MAP_H:
		for x in MAP_W:
			var on_a: bool = x >= ROAD_A_X.x and x <= ROAD_A_X.y
			var on_b: bool = y >= ROAD_B_Y.x and y <= ROAD_B_Y.y
			if on_a and on_b:
				terrain[y][x] = "asphalt_%d" % _rng.randi_range(0, 1)
			elif on_a:
				if x == 23 and _rng.randf() < 0.8:
					terrain[y][x] = "asphalt_line"
				else:
					terrain[y][x] = "asphalt_%d" % _rng.randi_range(0, 1)
			elif on_b:
				terrain[y][x] = "asphalt_%d" % _rng.randi_range(0, 1)

	# interior floors: the house gets worn wood planks, the warehouse a
	# smooth dark screed — both clearly distinct from the street outside
	var inner_a: Rect2i = BUILDING_A.grow(-1)
	for y in range(inner_a.position.y, inner_a.end.y):
		for x in range(inner_a.position.x, inner_a.end.x):
			terrain[y][x] = "wood_%d" % _rng.randi_range(0, 2)
	var inner_b: Rect2i = BUILDING_B.grow(-1)
	for y in range(inner_b.position.y, inner_b.end.y):
		for x in range(inner_b.position.x, inner_b.end.x):
			terrain[y][x] = "screed_%d" % _rng.randi_range(0, 1)

	# loading yard south of the warehouse: asphalt pad with stall lines
	for y in range(LOT.position.y, LOT.end.y):
		for x in range(LOT.position.x, LOT.end.x):
			if x >= 0 and y >= 0 and x < MAP_W and y < MAP_H:
				if (x == 32 or x == 35) and y < LOT.end.y - 1:
					terrain[y][x] = "asphalt_stall"
				else:
					terrain[y][x] = "asphalt_%d" % _rng.randi_range(0, 1)
	return terrain


# --------------------------------------------------------------- props ------

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
			var half_w: float = float(spec[1])
			var half_h: float = float(spec[2])
			var poly := CollisionPolygon2D.new()
			poly.polygon = PackedVector2Array([
				Vector2(0, -half_h), Vector2(half_w, 0),
				Vector2(0, half_h), Vector2(-half_w, 0)])
			body.add_child(poly)
		elif shape_kind == "poly":
			var flat: Array = spec[1]
			var points := PackedVector2Array()
			for i in range(0, flat.size(), 2):
				points.append(Vector2(float(flat[i]), float(flat[i + 1])))
			var poly := CollisionPolygon2D.new()
			poly.polygon = points
			body.add_child(poly)
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


func _place_buildings() -> void:
	# ONE door each, always on a camera-facing side (east or south)
	_build_shell(BUILDING_A, "brick_a", "charcoal", "house",
		[[Vector2i(BUILDING_A.end.x - 2, 10), "xp"]], false)
	_build_shell(BUILDING_B, "brick_b", "pitch", "warehouse",
		[[Vector2i(33, BUILDING_B.end.y - 2), "yp"]], true)


# edge midpoint offset and segment sprite axis per side of a cell
const _EDGE_OFFSET := {
	"yp": Vector2(-16, 8), "yn": Vector2(16, -8),
	"xp": Vector2(16, 8), "xn": Vector2(-16, -8),
}
const _EDGE_AXIS := {"yp": "x", "yn": "x", "xp": "y", "xn": "y"}
# endpoints of each edge relative to the cell center (for corner/jamb posts)
const _EDGE_VERTS := {
	"yp": [Vector2(-32, 0), Vector2(0, 16)], "yn": [Vector2(32, 0), Vector2(0, -16)],
	"xp": [Vector2(0, 16), Vector2(32, 0)], "xn": [Vector2(0, -16), Vector2(-32, 0)],
}


func _build_shell(rect: Rect2i, style: String, roof_tone: String, kind: String,
		doors: Array, ruined: bool) -> void:
	var interior: Rect2i = rect.grow(-1)
	var ruin_corner: Vector2i = interior.end - Vector2i(1, 1)
	var posts: Dictionary = {}  # rounded Vector2 -> true

	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			_occupied[cell] = true  # keep random scatter out of interiors
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
				var is_door := false
				for door in doors:
					if door[0] == cell and door[1] == side:
						is_door = true
				var center := _floor_layer.map_to_local(cell)
				var verts: Array = _EDGE_VERTS[side]
				if is_door:
					for v in verts:  # door jamb posts
						posts[(center + (v as Vector2)).round()] = true
					continue
				var axis: String = _EDGE_AXIS[side]
				# every wall uses the identical piece per axis — symmetric caps
				# and matching corners on all four sides (user call)
				var piece := "seg_%s_%s" % [style, axis]
				if ruined and Vector2(cell - ruin_corner).length() < 3.0:
					if _rng.randf() < 0.25:
						for v in verts:  # collapsed gap: posts mark the stumps
							posts[(center + (v as Vector2)).round()] = true
						continue
					piece = "seg_%s_%s_broken_%d" % [style, axis, _rng.randi_range(0, 1)]
				elif _rng.randf() < 0.3:
					piece = "seg_%s_%s_win_%d" % [style, axis, _rng.randi_range(0, 2)]
				_add_prop(piece, center + (_EDGE_OFFSET[side] as Vector2))

	# posts at the four outer corners of the shell
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

	# the wall ring cells are plain ground now, but keep scatter off them
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			_occupied[Vector2i(x, y)] = true

	_build_roof(interior, roof_tone, posts.keys(), ruined)
	if kind == "house":
		_furnish_house(interior)
	else:
		_furnish_warehouse(interior)


func _interior_free_cells(interior: Rect2i, keep_clear: Array[Vector2i]) -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			if cell in keep_clear:
				continue
			cells.append(cell)
	return cells


func _take_random_cell(cells: Array[Vector2i]) -> Vector2i:
	var index := _rng.randi_range(0, cells.size() - 1)
	var cell: Vector2i = cells[index]
	cells.remove_at(index)
	return cell


func _furnish_house(interior: Rect2i) -> void:
	# the big furniture keeps a sensible room layout (couch faces the tv),
	# everything else lands randomly
	var p := interior.position
	var couch_side := _rng.randi_range(0, 1)  # which side of the room
	_add_prop_at_cell("couch", p + Vector2i(1, 1 + couch_side), Vector2(6, 3))
	_add_prop_at_cell("tv_stand", p + Vector2i(3, 1 + couch_side), Vector2(4, 2))
	var used: Array[Vector2i] = [
		p + Vector2i(1, 1 + couch_side), p + Vector2i(3, 1 + couch_side)]
	var cells := _interior_free_cells(interior, used)
	var wall_pieces := ["cabinet", "bookshelf"]
	wall_pieces.shuffle()
	for piece in wall_pieces:  # against the back wall, random slots
		var x_offset := _rng.randi_range(0, interior.size.x - 1)
		var cell := Vector2i(p.x + x_offset, p.y)
		if cells.has(cell):
			cells.erase(cell)
			_add_prop_at_cell(piece, cell, Vector2(6, 2))
	var extras := ["table", "chair", "crate_%d" % _rng.randi_range(0, 5),
		_pick_variant("barrel")]
	for i in _rng.randi_range(2, extras.size()):
		if cells.is_empty():
			break
		_add_prop_at_cell(extras[i - 1], _take_random_cell(cells), Vector2(8, 4))


func _furnish_warehouse(interior: Rect2i) -> void:
	# random rack count along the back wall, random gaps; stock lands wherever
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
	for i in _rng.randi_range(6, 10):
		if cells.is_empty():
			break
		var cell := _take_random_cell(cells)
		var roll := _rng.randf() * total
		for opt in stock_mix:
			roll -= opt[1]
			if roll <= 0.0:
				_add_prop_at_cell(_pick_variant(opt[0]), cell, Vector2(10, 5))
				break


func _build_roof(interior: Rect2i, tone: String, post_positions: Array,
		ruined: bool) -> void:
	# Modular roof, one module per cell/edge by explicit formula:
	#   tile   at map_to_local(cell)          + (0, -wall_h)
	#   fascia at cell center + edge offset   + (0, -wall_h)  (south/east)
	#   rim    likewise                                        (north/west)
	# RoofReveal fades the whole group when the player is inside the walls.
	var south_corner := interior.end - Vector2i(1, 1)
	var roof := RoofReveal.new()
	roof.cells = interior  # trigger strictly inside the walls
	# y-sort: draws over everything of this building (walls, posts, interior)
	roof.position = _floor_layer.map_to_local(south_corner) + Vector2(0, 24)
	var lift := Vector2(0, -float(_wall_h))

	var ruin_corner := interior.end - Vector2i(1, 1)
	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			var tile_name := "roof_tile_%s_%d" % [tone, _rng.randi_range(0, 1)]
			if ruined and Vector2(cell - ruin_corner).length() < 3.0 and _rng.randf() < 0.6:
				# collapsed roof section over the broken corner
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

	# a roof-colored cap over every post, so all corners and door jambs read
	# identical when the roof is on
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


func _place_warehouse_yard() -> void:
	# box trucks backed into random stalls (one always has its rear open),
	# stray stock scattered around the yard
	var stalls: Array[Vector2i] = [Vector2i(31, 41), Vector2i(34, 41), Vector2i(37, 41)]
	stalls.shuffle()
	var variants: Array[int] = [2, _rng.randi_range(0, 1), _rng.randi_range(0, 1)]
	for i in _rng.randi_range(2, 3):
		var cell: Vector2i = stalls[i - 1]
		_add_prop_at_cell("truck_%d" % variants[i - 1], cell, Vector2(6, 3))
		_occupied[cell + Vector2i(0, -1)] = true  # trucks are long: keep clear
		_occupied[cell + Vector2i(0, 1)] = true

	var yard_cells: Array[Vector2i] = []
	for y in range(BUILDING_B.end.y, LOT.end.y):
		for x in range(LOT.position.x, LOT.end.x):
			var cell := Vector2i(x, y)
			if not _occupied.has(cell):
				yard_cells.append(cell)
	var spill := ["crate", "crate", "crate_stack", "pallet", "barrel"]
	for i in _rng.randi_range(4, 6):
		if yard_cells.is_empty():
			break
		var item: String = _pick_variant(spill[_rng.randi_range(0, spill.size() - 1)])
		_add_prop_at_cell(item, _take_random_cell(yard_cells), Vector2(6, 3))
	# the yard is dressed: keep the ambient scatter pass out of it entirely
	for y in range(LOT.position.y, LOT.end.y):
		for x in range(LOT.position.x, LOT.end.x):
			_occupied[Vector2i(x, y)] = true


func _place_perimeter() -> void:
	for i in MAP_W:
		for cell in [Vector2i(i, 0), Vector2i(i, MAP_H - 1), Vector2i(0, i), Vector2i(MAP_H - 1, i)]:
			if _occupied.has(cell):
				continue
			var roll := _rng.randf()
			if roll < 0.30:
				_add_prop_at_cell(_pick_variant("rubble"), cell)
			elif roll < 0.42:
				var style := "brick_a" if _rng.randf() < 0.5 else "brick_b"
				var axis := "x" if _rng.randf() < 0.5 else "y"
				_add_prop_at_cell("seg_%s_%s_broken_%d" % [style, axis, _rng.randi_range(0, 1)], cell)


func _place_fixed_props() -> void:
	# hand-placed set dressing near spawn so the first screen composes well
	_add_prop_at_cell("barrel_0", Vector2i(16, 15))
	_add_prop_at_cell("crate_0", Vector2i(17, 16))
	_add_prop_at_cell("tires_0", Vector2i(20, 11))
	_add_prop_at_cell("rubble_1", Vector2i(21, 16))
	_add_prop_at_cell("cylinder_0", Vector2i(16, 12))


func _scatter_props() -> void:
	var mix := [
		["barrel", 0.16], ["cylinder", 0.10], ["crate", 0.14], ["tires", 0.12],
		["pallet", 0.10], ["dumpster", 0.06], ["rubble", 0.14], ["pillar", 0.06],
	]
	var total := 0.0
	for opt in mix:
		total += opt[1]
	var placed := 0
	var attempts := 0
	while placed < 52 and attempts < 500:
		attempts += 1
		var cell := Vector2i(_rng.randi_range(2, MAP_W - 3), _rng.randi_range(2, MAP_H - 3))
		if _occupied.has(cell):
			continue
		if cell.x >= ROAD_A_X.x and cell.x <= ROAD_A_X.y and _rng.randf() < 0.85:
			continue
		if cell.y >= ROAD_B_Y.x and cell.y <= ROAD_B_Y.y and _rng.randf() < 0.85:
			continue
		if BUILDING_A.grow(1).has_point(cell) or BUILDING_B.grow(1).has_point(cell):
			continue
		if Vector2(cell - SPAWN_CELL).length() < 2.5:
			continue
		var roll := _rng.randf() * total
		for opt in mix:
			roll -= opt[1]
			if roll <= 0.0:
				_add_prop_at_cell(_pick_variant(opt[0]), cell, Vector2(10, 5))
				break
		placed += 1


# ----------------------------------------------------------- boundaries -----

func _playable_corners() -> Array[Vector2]:
	return [
		_floor_layer.map_to_local(Vector2i(1, 1)),
		_floor_layer.map_to_local(Vector2i(MAP_W - 2, 1)),
		_floor_layer.map_to_local(Vector2i(MAP_W - 2, MAP_H - 2)),
		_floor_layer.map_to_local(Vector2i(1, MAP_H - 2)),
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


func _world_bounds() -> Rect2:
	var corners := _playable_corners()
	var top_left := corners[0]
	var bottom_right := corners[0]
	for c in corners:
		top_left = Vector2(minf(top_left.x, c.x), minf(top_left.y, c.y))
		bottom_right = Vector2(maxf(bottom_right.x, c.x), maxf(bottom_right.y, c.y))
	return Rect2(top_left, bottom_right - top_left).grow(48.0)
