class_name Stairs
extends StaticBody2D
## The flight to a building's second story. F beside it flips the player's
## floor — main.gd owns the actual switch (it also swaps which room's
## furniture exists). The prop itself is solid and lives on both floors.

signal used

var upper_index := -1
var _sprite: Sprite2D


func setup(texture: Texture2D, origin: Vector2, index: int,
		collider: Variant = null) -> void:
	upper_index = index
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.offset = -origin
	add_child(sprite)
	_sprite = sprite
	# THE SHAPE COMES FROM THE MANIFEST, like every other prop. It used to be a
	# hardcoded 6 px circle at the foot of a flight that climbs most of a cell,
	# so you could walk through the staircase (user: "make the stairs have
	# collision, like make it a solid object so i cant walk through it"). This
	# is the door-collider lesson again: a shape derived in GDScript drifts
	# away from the art the generator drew.
	if collider is Array and (collider as Array).size() == 2 \
			and str((collider as Array)[0]) == "poly":
		var flat: Array = (collider as Array)[1]
		var pts := PackedVector2Array()
		for i in range(0, flat.size(), 2):
			pts.append(Vector2(float(flat[i]), float(flat[i + 1])))
		var poly := CollisionPolygon2D.new()
		poly.polygon = pts
		add_child(poly)
	else:
		var shape := CollisionShape2D.new()
		var circle := CircleShape2D.new()
		circle.radius = 6.0
		shape.shape = circle
		add_child(shape)
	add_to_group("stairs")


func set_covered(covered: bool) -> void:
	## The slab is a COMPLETE floor, so while the player is up on it the flight
	## below is out of sight — you cannot see through a floor with no hole in
	## it. Arriving upstairs used to leave the flight drawn straight through
	## the slab, which cut the player in half at the stairs cell and left the
	## stair top floating on the floorboards (user: "i clip inside of the
	## floor, and i can see the top of the stairs, it should all be clean like
	## the bottom floor").
	##
	## The COLLIDER goes with the sprite, deliberately. Hiding the art alone
	## would leave a solid thing you cannot see standing in the middle of the
	## room — the exact complaint one line further down the same report. Going
	## back down is a proximity prompt, not a collision, so nothing is lost.
	if _sprite != null:
		_sprite.visible = not covered
	collision_layer = 0 if covered else 1


func use() -> void:
	used.emit()
