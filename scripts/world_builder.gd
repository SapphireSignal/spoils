class_name WorldBuilder
extends RefCounted
## Builds the M1 map: a ruined industrial block, ~48x48 iso tiles.
## Deterministic (fixed RNG seed). Consumes art/gen/manifest.json so sprite
## sizes/origins always match whatever tools/gen_art.py produced.

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
var _floor_layer: TileMapLayer
var _ysort: Node2D
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
	}


func _load_manifest() -> Dictionary:
	var file := FileAccess.open("res://art/gen/manifest.json", FileAccess.READ)
	assert(file != null, "art/gen/manifest.json missing — run tools/gen_art.py")
	var data: Dictionary = JSON.parse_string(file.get_as_text())
	_floor_coords = data["floors"]
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

func _pick_weighted(options: Array) -> String:
	# options: [[name, weight], ...]
	var total := 0.0
	for opt in options:
		total += opt[1]
	var roll := _rng.randf() * total
	for opt in options:
		roll -= opt[1]
		if roll <= 0.0:
			return opt[0]
	return options[0][0]


func _layout_terrain() -> Array:
	var base_mix := [
		["concrete_a", 0.52], ["concrete_b", 0.16], ["concrete_c", 0.10],
		["concrete_cracked_a", 0.08], ["concrete_cracked_b", 0.06],
		["moss_a", 0.04], ["moss_b", 0.04],
	]
	var terrain: Array = []
	for y in MAP_H:
		var row: Array = []
		for x in MAP_W:
			row.append(_pick_weighted(base_mix))
		terrain.append(row)

	# dirt patches
	for i in 7:
		var cx := _rng.randi_range(4, MAP_W - 5)
		var cy := _rng.randi_range(4, MAP_H - 5)
		var radius := _rng.randi_range(2, 4)
		for y in range(cy - radius, cy + radius + 1):
			for x in range(cx - radius, cx + radius + 1):
				if x < 0 or y < 0 or x >= MAP_W or y >= MAP_H:
					continue
				if Vector2(x - cx, y - cy).length() <= radius + _rng.randf() - 0.5:
					terrain[y][x] = "dirt_a" if _rng.randf() < 0.7 else "dirt_b"

	# roads (over everything so far)
	for y in MAP_H:
		for x in MAP_W:
			var on_a := x >= ROAD_A_X.x and x <= ROAD_A_X.y
			var on_b := y >= ROAD_B_Y.x and y <= ROAD_B_Y.y
			if on_a and on_b:
				terrain[y][x] = "asphalt_a" if _rng.randf() < 0.8 else "asphalt_b"
			elif on_a:
				if x == 23 and _rng.randf() < 0.8:
					terrain[y][x] = "asphalt_line"
				else:
					terrain[y][x] = "asphalt_a" if _rng.randf() < 0.75 else "asphalt_b"
			elif on_b:
				terrain[y][x] = "asphalt_a" if _rng.randf() < 0.75 else "asphalt_b"

	# building interiors: cleaner concrete slab
	for rect in [BUILDING_A, BUILDING_B]:
		var inner: Rect2i = rect.grow(-1)
		for y in range(inner.position.y, inner.end.y):
			for x in range(inner.position.x, inner.end.x):
				terrain[y][x] = "concrete_a" if _rng.randf() < 0.8 else "concrete_c"
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


func _add_prop(prop_name: String, pos: Vector2, collider_kind: String) -> void:
	var node: Node2D
	if collider_kind == "none":
		node = Node2D.new()
	else:
		var body := StaticBody2D.new()
		var col: Node2D
		match collider_kind:
			"tile":  # full 64x32 tile diamond (walls)
				var poly := CollisionPolygon2D.new()
				poly.polygon = PackedVector2Array([
					Vector2(0, -16), Vector2(32, 0), Vector2(0, 16), Vector2(-32, 0)])
				col = poly
			"crate":
				var poly := CollisionPolygon2D.new()
				poly.polygon = PackedVector2Array([
					Vector2(0, -8), Vector2(15, 0), Vector2(0, 8), Vector2(-15, 0)])
				col = poly
			_:  # "circle" small round base
				var cs := CollisionShape2D.new()
				var shape := CircleShape2D.new()
				shape.radius = 7.0
				cs.shape = shape
				col = cs
		body.add_child(col)
		node = body
	node.position = pos
	node.add_child(_prop_sprite(prop_name))
	_ysort.add_child(node)


func _add_prop_at_cell(prop_name: String, cell: Vector2i, collider_kind: String,
		jitter: Vector2 = Vector2.ZERO) -> void:
	var pos := _floor_layer.map_to_local(cell)
	if jitter != Vector2.ZERO:
		pos += Vector2(_rng.randf_range(-jitter.x, jitter.x), _rng.randf_range(-jitter.y, jitter.y))
	_add_prop(prop_name, pos, collider_kind)
	_occupied[cell] = true


func _wall_variant() -> String:
	var roll := _rng.randf()
	if roll < 0.42:
		return "wall_a"
	if roll < 0.80:
		return "wall_b"
	if roll < 0.92:
		return "wall_window"
	return "wall_broken_a" if _rng.randf() < 0.5 else "wall_broken_b"


func _place_buildings() -> void:
	for rect in [BUILDING_A, BUILDING_B]:
		var doors: Array[Vector2i] = []
		if rect == BUILDING_A:  # door on the +x side, facing road A
			doors = [Vector2i(rect.end.x - 1, 10), Vector2i(rect.end.x - 1, 11)]
		else:  # door on the -y side, facing road B
			doors = [Vector2i(33, rect.position.y), Vector2i(34, rect.position.y)]
		var broken_corner: Vector2i = rect.end - Vector2i(1, 1)
		for y in range(rect.position.y, rect.end.y):
			for x in range(rect.position.x, rect.end.x):
				var cell := Vector2i(x, y)
				var edge: bool = (x == rect.position.x or x == rect.end.x - 1
					or y == rect.position.y or y == rect.end.y - 1)
				if not edge:
					_occupied[cell] = true  # keep random scatter out of interiors
					continue
				if cell in doors:
					_occupied[cell] = true
					continue
				var variant := _wall_variant()
				if rect == BUILDING_B and cell.distance_to(broken_corner) < 3.5:
					var roll := _rng.randf()
					if roll < 0.35:  # collapsed: rubble instead of wall
						_add_prop_at_cell("rubble_a" if _rng.randf() < 0.5 else "rubble_b",
							cell, "none")
						continue
					variant = "wall_broken_a" if _rng.randf() < 0.5 else "wall_broken_b"
				_add_prop_at_cell(variant, cell, "tile")


func _place_perimeter() -> void:
	# collapsed-city edge dressing just inside the void
	for i in MAP_W:
		for cell in [Vector2i(i, 0), Vector2i(i, MAP_H - 1), Vector2i(0, i), Vector2i(MAP_H - 1, i)]:
			if _occupied.has(cell):
				continue
			var roll := _rng.randf()
			if roll < 0.30:
				_add_prop_at_cell("rubble_a" if _rng.randf() < 0.5 else "rubble_b", cell, "none")
			elif roll < 0.42:
				_add_prop_at_cell("wall_broken_a" if _rng.randf() < 0.5 else "wall_broken_b",
					cell, "tile")


func _place_fixed_props() -> void:
	# hand-placed set dressing near spawn so the first screen composes well
	_add_prop_at_cell("barrel_rust", Vector2i(16, 15), "circle")
	_add_prop_at_cell("crate_wood", Vector2i(17, 16), "crate")
	_add_prop_at_cell("crate_mil", Vector2i(20, 11), "crate")
	_add_prop_at_cell("rubble_a", Vector2i(21, 16), "none")
	_add_prop_at_cell("barrel_olive", Vector2i(15, 12), "circle")
	# a few crates inside each building
	_add_prop_at_cell("crate_wood", Vector2i(10, 10), "crate")
	_add_prop_at_cell("crate_mil", Vector2i(14, 12), "crate")
	_add_prop_at_cell("barrel_rust", Vector2i(12, 13), "circle")
	_add_prop_at_cell("crate_wood", Vector2i(32, 35), "crate")
	_add_prop_at_cell("crate_mil", Vector2i(35, 37), "crate")


func _scatter_props() -> void:
	var mix := [
		["barrel_rust", 0.20, "circle"], ["barrel_olive", 0.11, "circle"],
		["crate_wood", 0.17, "crate"], ["crate_mil", 0.11, "crate"],
		["rubble_a", 0.19, "none"], ["rubble_b", 0.13, "none"],
		["pillar", 0.09, "circle"],
	]
	var placed := 0
	var attempts := 0
	while placed < 52 and attempts < 500:
		attempts += 1
		var cell := Vector2i(_rng.randi_range(2, MAP_W - 3), _rng.randi_range(2, MAP_H - 3))
		if _occupied.has(cell):
			continue
		if cell.x >= ROAD_A_X.x and cell.x <= ROAD_A_X.y and _rng.randf() < 0.85:
			continue  # keep roads mostly clear
		if cell.y >= ROAD_B_Y.x and cell.y <= ROAD_B_Y.y and _rng.randf() < 0.85:
			continue
		if BUILDING_A.grow(1).has_point(cell) or BUILDING_B.grow(1).has_point(cell):
			continue
		if Vector2(cell - SPAWN_CELL).length() < 2.5:
			continue
		var total := 0.0
		for opt in mix:
			total += opt[1]
		var roll := _rng.randf() * total
		for opt in mix:
			roll -= opt[1]
			if roll <= 0.0:
				_add_prop_at_cell(opt[0], cell, opt[2], Vector2(10, 5))
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
