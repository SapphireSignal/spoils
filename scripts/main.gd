extends Node2D
## Game scene entry point: builds the world, spawns the player, wires the
## camera and the roof interior-reveal.

var world_info: Dictionary = {}

var _player: Player
var _floor_layer: TileMapLayer
var _roofs: Array = []


func _ready() -> void:
	var builder := WorldBuilder.new()
	world_info = builder.build(self)
	var ysort: Node2D = world_info["ysort"]
	var spawn: Vector2 = world_info["spawn"]
	_floor_layer = world_info["floor"]
	_roofs = world_info["roofs"]
	_player = Authority.spawn_player(ysort, spawn)
	_limit_camera(_player.camera)
	add_child(PauseMenu.new())


func _process(_delta: float) -> void:
	var cell := _floor_layer.local_to_map(_player.position)
	for roof in _roofs:
		var reveal := roof as RoofReveal
		reveal.set_inside(reveal.cells.has_point(cell))


func _limit_camera(camera: Camera2D) -> void:
	var bounds: Rect2 = world_info["bounds"]
	camera.limit_left = int(bounds.position.x)
	camera.limit_top = int(bounds.position.y)
	camera.limit_right = int(bounds.end.x)
	camera.limit_bottom = int(bounds.end.y)
