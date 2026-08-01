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
const BUILDING_A := Rect2i(8, 8, 9, 7)
const BUILDING_B := Rect2i(30, 33, 8, 7)
const SPAWN_CELL := Vector2i(18, 13)

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

	for rect in [BUILDING_A, BUILDING_B]:
		var inner: Rect2i = rect.grow(-1)
		for y in range(inner.position.y, inner.end.y):
			for x in range(inner.position.x, inner.end.x):
				terrain[y][x] = "concrete_%d" % _rng.randi_range(0, 1)
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
	# doors: ONE (interior cell, side) edge each — a single doorway per building
	_build_shell(BUILDING_A, "brick_a", "charcoal",
		[[Vector2i(BUILDING_A.end.x - 2, 10), "xp"]], false)
	_build_shell(BUILDING_B, "brick_b", "umber",
		[[Vector2i(33, BUILDING_B.position.y + 1), "yn"]], true)


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


func _build_shell(rect: Rect2i, style: String, roof_tone: String,
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

	_build_roof(interior, roof_tone, posts.keys())


func _build_roof(interior: Rect2i, tone: String, post_positions: Array) -> void:
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

	for y in range(interior.position.y, interior.end.y):
		for x in range(interior.position.x, interior.end.x):
			var cell := Vector2i(x, y)
			var tile := _prop_sprite("roof_tile_%s_%d" % [tone, _rng.randi_range(0, 1)])
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
	_add_prop_at_cell("cylinder_0", Vector2i(15, 12))
	# building interiors
	_add_prop_at_cell("crate_1", Vector2i(10, 10))
	_add_prop_at_cell("crate_3", Vector2i(14, 12))
	_add_prop_at_cell("barrel_2", Vector2i(12, 13))
	_add_prop_at_cell("crate_2", Vector2i(32, 35))
	_add_prop_at_cell("crate_0", Vector2i(35, 37))
	_add_prop_at_cell("pallet_0", Vector2i(33, 36))


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
