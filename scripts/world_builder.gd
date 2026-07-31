class_name WorldBuilder
extends RefCounted
## Builds the M1 map: a ruined industrial block, ~48x48 iso tiles.
## Deterministic (fixed RNG seed). Consumes art/gen/manifest.json so sprite
## sizes/origins always match whatever tools/gen_art.py produced.
##
## Buildings are brick: wall pieces are chosen by neighbor mask (see
## tools/gen_art.py) so straight runs render as continuous walls, not cubes.

const MAP_W := 48
const MAP_H := 48
const TILE := Vector2i(64, 32)
const ROAD_A_X := Vector2i(22, 25)  # column band, runs screen down-left
const ROAD_B_Y := Vector2i(26, 29)  # row band, runs screen down-right
const BUILDING_A := Rect2i(8, 8, 9, 7)
const BUILDING_B := Rect2i(30, 33, 8, 7)
const SPAWN_CELL := Vector2i(18, 13)

# collider shape per prop; anything absent gets no collision (rubble, pallet)
const PROP_COLLIDERS := {
	"crate_wood": ["diamond", 15.0, 8.0],
	"crate_ammo": ["diamond", 17.0, 9.0],
	"dumpster": ["diamond", 19.0, 10.0],
	"barrel_rust": ["circle", 7.0],
	"gas_cylinder": ["circle", 5.0],
	"tire_stack": ["circle", 8.0],
	"pillar": ["circle", 6.0],
}

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

func _layout_terrain() -> Array:
	var terrain: Array = []
	for y in MAP_H:
		var row: Array = []
		for x in MAP_W:
			row.append("concrete_%d" % _rng.randi_range(0, 5))
		terrain.append(row)

	# rare one-off detail tiles (kept sparse so nothing reads as a pattern)
	for y in MAP_H:
		for x in MAP_W:
			var roll := _rng.randf()
			if roll < 0.035:
				terrain[y][x] = "crack_%d" % _rng.randi_range(0, 2)
			elif roll < 0.055:
				terrain[y][x] = "stain_%d" % _rng.randi_range(0, 1)
			elif roll < 0.068:
				terrain[y][x] = "moss_0"

	# dirt patches, with blended edges so they don't cut hard diamond borders
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

	# roads over everything so far
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

	# building interiors: cleaner slab
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


func _add_prop(prop_name: String, pos: Vector2, kind: String) -> void:
	var spec: Array = []
	if kind == "wall":
		spec = ["diamond", 32.0, 16.0]
	elif kind == "auto" and PROP_COLLIDERS.has(prop_name):
		spec = PROP_COLLIDERS[prop_name]

	var node: Node2D
	if spec.is_empty():
		node = Node2D.new()
	else:
		var body := StaticBody2D.new()
		var shape_kind: String = spec[0]
		if shape_kind == "diamond":
			var half_w: float = spec[1]
			var half_h: float = spec[2]
			var poly := CollisionPolygon2D.new()
			poly.polygon = PackedVector2Array([
				Vector2(0, -half_h), Vector2(half_w, 0),
				Vector2(0, half_h), Vector2(-half_w, 0)])
			body.add_child(poly)
		else:
			var cs := CollisionShape2D.new()
			var circle := CircleShape2D.new()
			circle.radius = spec[1]
			cs.shape = circle
			body.add_child(cs)
		node = body
	node.position = pos
	node.add_child(_prop_sprite(prop_name))
	_ysort.add_child(node)


func _add_prop_at_cell(prop_name: String, cell: Vector2i, kind: String = "auto",
		jitter: Vector2 = Vector2.ZERO) -> void:
	var pos := _floor_layer.map_to_local(cell)
	if jitter != Vector2.ZERO:
		pos += Vector2(_rng.randf_range(-jitter.x, jitter.x), _rng.randf_range(-jitter.y, jitter.y))
	_add_prop(prop_name, pos, kind)
	_occupied[cell] = true


# mask bit order must match tools/gen_art.py: xn, xp, yn, yp
const _MASK_OFFSETS := [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1)]

func _place_buildings() -> void:
	_build_shell(BUILDING_A, "brick_a",
		[Vector2i(BUILDING_A.end.x - 1, 10), Vector2i(BUILDING_A.end.x - 1, 11)], false)
	_build_shell(BUILDING_B, "brick_b",
		[Vector2i(33, BUILDING_B.position.y), Vector2i(34, BUILDING_B.position.y)], true)


func _build_shell(rect: Rect2i, style: String, doors: Array, ruined: bool) -> void:
	var full: Dictionary = {}
	var broken: Array[Vector2i] = []
	var collapsed: Array[Vector2i] = []
	var ruin_corner: Vector2i = rect.end - Vector2i(1, 1)

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
			if ruined and Vector2(cell - ruin_corner).length() < 3.5:
				if _rng.randf() < 0.3:
					collapsed.append(cell)
				else:
					broken.append(cell)
				continue
			full[cell] = true

	for cell in full:
		var bits := ""
		for off in _MASK_OFFSETS:
			bits += "1" if full.has(cell + off) else "0"
		var piece := "wall_%s_m%s" % [style, bits]
		if bits == "1100" and _rng.randf() < 0.25:
			piece = "wall_%s_win_x" % style
		elif bits == "0011" and _rng.randf() < 0.25:
			piece = "wall_%s_win_y" % style
		_add_prop_at_cell(piece, cell, "wall")
	for cell in broken:
		var suffix := "a" if _rng.randf() < 0.5 else "b"
		_add_prop_at_cell("wall_%s_broken_%s" % [style, suffix], cell, "wall")
	for cell in collapsed:
		_add_prop_at_cell("rubble_a" if _rng.randf() < 0.5 else "rubble_b", cell)


func _place_perimeter() -> void:
	# collapsed-city edge dressing just inside the void
	for i in MAP_W:
		for cell in [Vector2i(i, 0), Vector2i(i, MAP_H - 1), Vector2i(0, i), Vector2i(MAP_H - 1, i)]:
			if _occupied.has(cell):
				continue
			var roll := _rng.randf()
			if roll < 0.30:
				_add_prop_at_cell("rubble_a" if _rng.randf() < 0.5 else "rubble_b", cell)
			elif roll < 0.42:
				var style := "brick_a" if _rng.randf() < 0.5 else "brick_b"
				var suffix := "a" if _rng.randf() < 0.5 else "b"
				_add_prop_at_cell("wall_%s_broken_%s" % [style, suffix], cell, "wall")


func _place_fixed_props() -> void:
	# hand-placed set dressing near spawn so the first screen composes well
	_add_prop_at_cell("barrel_rust", Vector2i(16, 15))
	_add_prop_at_cell("crate_wood", Vector2i(17, 16))
	_add_prop_at_cell("tire_stack", Vector2i(20, 11))
	_add_prop_at_cell("rubble_a", Vector2i(21, 16))
	_add_prop_at_cell("gas_cylinder", Vector2i(15, 12))
	# building interiors
	_add_prop_at_cell("crate_wood", Vector2i(10, 10))
	_add_prop_at_cell("crate_ammo", Vector2i(14, 12))
	_add_prop_at_cell("barrel_rust", Vector2i(12, 13))
	_add_prop_at_cell("crate_ammo", Vector2i(32, 35))
	_add_prop_at_cell("crate_wood", Vector2i(35, 37))
	_add_prop_at_cell("pallet", Vector2i(33, 36))


func _scatter_props() -> void:
	var mix := [
		["barrel_rust", 0.16], ["gas_cylinder", 0.10],
		["crate_wood", 0.13], ["crate_ammo", 0.12],
		["tire_stack", 0.12], ["pallet", 0.10], ["dumpster", 0.07],
		["rubble_a", 0.09], ["rubble_b", 0.06], ["pillar", 0.05],
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
			continue  # keep roads mostly clear
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
				_add_prop_at_cell(opt[0], cell, "auto", Vector2(10, 5))
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
