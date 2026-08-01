extends Node2D
## Game scene entry point. Shows a brief "deploying" screen while the whole
## district builds (25k tiles + ~2000 props in one go would otherwise be a
## visible frame hitch), then fades into the raid.

var world_info: Dictionary = {}

var _player: Player
var _floor_layer: TileMapLayer
var _roofs: Array = []
var _deploy_screen: Control


func _ready() -> void:
	_show_deploy_screen()
	_build_world.call_deferred()


func _show_deploy_screen() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 95
	_deploy_screen = Control.new()
	_deploy_screen.set_anchors_preset(Control.PRESET_FULL_RECT)
	_deploy_screen.theme = UITheme.get_theme()
	var black := ColorRect.new()
	black.color = Color("090a14")
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	_deploy_screen.add_child(black)
	var label := Label.new()
	label.text = "deploying..."
	label.set_anchors_preset(Control.PRESET_CENTER)
	label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_deploy_screen.add_child(label)
	layer.add_child(_deploy_screen)
	add_child(layer)


func _build_world() -> void:
	# let the deploy screen actually render before the heavy build
	await get_tree().process_frame
	await get_tree().process_frame
	var builder := WorldBuilder.new()
	world_info = builder.build(self)
	_floor_layer = world_info["floor"]
	_roofs = world_info["roofs"]
	var ysort: Node2D = world_info["ysort"]
	_player = Authority.spawn_player(ysort, world_info["spawn"])
	_limit_camera(_player.camera)

	var environment := EnvironmentSystem.new()
	add_child(environment)
	environment.setup(self, _floor_layer, world_info["puddle_spots"])

	add_child(PauseMenu.new())

	var tween := create_tween()
	tween.tween_property(_deploy_screen, "modulate:a", 0.0, 0.4)
	tween.tween_callback(func() -> void: _deploy_screen.get_parent().queue_free())


func _process(_delta: float) -> void:
	if _player == null or _floor_layer == null:
		return
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
