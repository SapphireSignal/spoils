extends Node2D
## Entry point: builds the world, spawns the player, wires the camera.

var world_info: Dictionary = {}


func _ready() -> void:
	var builder := WorldBuilder.new()
	world_info = builder.build(self)
	var ysort: Node2D = world_info["ysort"]
	var spawn: Vector2 = world_info["spawn"]
	var player: Player = Authority.spawn_player(ysort, spawn)
	_limit_camera(player.camera)
	add_child(PauseMenu.new())


func _limit_camera(camera: Camera2D) -> void:
	var bounds: Rect2 = world_info["bounds"]
	camera.limit_left = int(bounds.position.x)
	camera.limit_top = int(bounds.position.y)
	camera.limit_right = int(bounds.end.x)
	camera.limit_bottom = int(bounds.end.y)
