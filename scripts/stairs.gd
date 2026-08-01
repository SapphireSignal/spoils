class_name Stairs
extends StaticBody2D
## The flight to a building's second story. F beside it flips the player's
## floor — main.gd owns the actual switch (it also swaps which room's
## furniture exists). The prop itself is solid and lives on both floors.

signal used

const INTERACT_RANGE := 44.0

var upper_index := -1


func setup(texture: Texture2D, origin: Vector2, index: int) -> void:
	upper_index = index
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.offset = -origin
	add_child(sprite)
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 6.0
	shape.shape = circle
	add_child(shape)
	add_to_group("stairs")


func use() -> void:
	used.emit()
