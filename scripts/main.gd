extends Node2D
## Game scene entry point. Shows a "deploying" screen while the district
## builds ASYNCHRONOUSLY (the builder yields to the render loop, so the frame
## never hitches no matter how big the map is), then fades into the raid.

const MAP_NAME := "transit"

var world_info: Dictionary = {}

var _player: Player
var _floor_layer: TileMapLayer
var _roofs: Array = []
var _deploy_screen: Control
var _deploy_label: Label
var _deploy_time := 0.0
var _last_roof_cell := Vector2i(-9999, -9999)
var _respawning := false


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
	_deploy_label = Label.new()
	_deploy_label.text = "deploying to %s" % MAP_NAME
	_deploy_label.set_anchors_preset(Control.PRESET_CENTER)
	_deploy_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_deploy_label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	_deploy_screen.add_child(_deploy_label)
	layer.add_child(_deploy_screen)
	add_child(layer)


func _build_world() -> void:
	# let the deploy screen actually render before the heavy lifting
	await get_tree().process_frame
	await get_tree().process_frame
	await _prewarm_textures()
	var builder := WorldBuilder.new()
	var info: Dictionary = await builder.build(self, Harness.world_seed)
	_floor_layer = info["floor"]
	_roofs = info["roofs"]
	var ysort: Node2D = info["ysort"]
	_player = Authority.spawn_player(ysort, info["spawn"])
	_player.set_map_diamond(info["map_center"], info["map_half_h"])
	_player.died.connect(_on_player_died)
	_limit_camera(_player.camera, info["bounds"])

	var environment := EnvironmentSystem.new()
	add_child(environment)
	environment.setup(self, _floor_layer, info["puddle_spots"], _roofs)

	var guard := EdgeGuard.new()
	guard.name = "EdgeGuard"
	add_child(guard)
	guard.setup(_player, self, info["map_center"], info["map_half_h"])

	add_child(PauseMenu.new())
	world_info = info  # publish LAST: the harness polls this to detect readiness

	var tween := create_tween()
	tween.tween_property(_deploy_screen, "modulate:a", 0.0, 0.4)
	tween.tween_callback(func() -> void:
		_deploy_screen.get_parent().queue_free()
		_deploy_screen = null)


func _prewarm_textures() -> void:
	# touch every generated texture while the deploy screen covers the game:
	# decode + GPU upload happen here, not as tiny hitches during play
	var dir := DirAccess.open("res://art/gen")
	if dir == null:
		return
	var loaded := 0
	for file in dir.get_files():
		if file.ends_with(".png"):
			load("res://art/gen/" + file)
			loaded += 1
			if loaded % 40 == 0:
				await get_tree().process_frame


func _process(delta: float) -> void:
	if _deploy_screen != null:
		_deploy_time += delta
		_deploy_label.text = "deploying to %s%s" % [
			MAP_NAME, ".".repeat(1 + int(_deploy_time * 3.0) % 3)]
	if _player == null or _floor_layer == null:
		return
	var cell := _floor_layer.local_to_map(_player.position)
	if cell == _last_roof_cell:
		return
	_last_roof_cell = cell
	for roof in _roofs:
		var reveal := roof as RoofReveal
		reveal.set_inside(reveal.cells.has_point(cell))


func _on_player_died() -> void:
	if _respawning:
		return
	_respawning = true
	var layer := CanvasLayer.new()
	layer.layer = 90
	var black := ColorRect.new()
	black.color = Color("090a14", 0.0)
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(black)
	var label := Label.new()
	label.text = "you got sniped."
	label.theme = UITheme.get_theme()
	label.set_anchors_preset(Control.PRESET_CENTER)
	label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	label.add_theme_color_override("font_color", Color("cf573c"))
	label.visible = false
	layer.add_child(label)
	add_child(layer)
	var fade_in := create_tween()
	fade_in.tween_property(black, "color:a", 1.0, 0.35)
	await fade_in.finished
	label.visible = true
	await get_tree().create_timer(1.2).timeout
	_player.respawn(world_info["spawn"])
	label.visible = false
	await get_tree().process_frame
	var fade_out := create_tween()
	fade_out.tween_property(black, "color:a", 0.0, 0.45)
	await fade_out.finished
	layer.queue_free()
	_respawning = false


func _limit_camera(camera: Camera2D, bounds: Rect2) -> void:
	# coarse rectangular backstop; the real fence is the diamond clamp in
	# Player._camera_target
	camera.limit_left = int(bounds.position.x)
	camera.limit_top = int(bounds.position.y)
	camera.limit_right = int(bounds.end.x)
	camera.limit_bottom = int(bounds.end.y)
