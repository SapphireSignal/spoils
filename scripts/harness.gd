extends Node
## Self-verification harness (design doc section 7). User args:
##   --smoke        headless scripted checks; must end with "SMOKE PASS"
##   --shot=<name>  boot, capture shots/<name>.png, quit (needs rendering)


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--smoke":
			_smoke.call_deferred()
		elif arg.begins_with("--shot="):
			_shot.call_deferred(arg.trim_prefix("--shot="))


func _smoke() -> void:
	# let Main._ready run and the tree settle
	for i in 3:
		await get_tree().process_frame
	var failures: Array[String] = []

	var main := get_tree().current_scene
	if main == null:
		_finish_smoke(["no current scene"])
		return

	var floor_layer := main.get_node_or_null("Floor") as TileMapLayer
	if floor_layer == null:
		failures.append("Floor TileMapLayer missing")
	elif floor_layer.get_used_cells().size() != 48 * 48:
		failures.append("floor cell count %d != %d" % [floor_layer.get_used_cells().size(), 48 * 48])

	var world := main.get_node_or_null("World")
	if world == null:
		failures.append("World node missing")
	elif world.get_child_count() < 60:
		failures.append("only %d props/actors in World" % world.get_child_count())

	if main.get_node_or_null("Border") == null:
		failures.append("Border collision missing")

	var player := main.get_node_or_null("World/Player") as Player
	if player == null:
		failures.append("Player missing")
	else:
		var start: Vector2 = player.position
		Input.action_press("move_right")
		for i in 40:
			await get_tree().physics_frame
		Input.action_release("move_right")
		var moved := player.position.x - start.x
		if moved < 20.0:
			failures.append("player barely moved (dx=%.1f after 40 ticks)" % moved)
		# walk into the map border for a while: must be stopped, not escape
		Input.action_press("move_up")
		for i in 600:
			await get_tree().physics_frame
		Input.action_release("move_up")
		var bounds: Rect2 = (main.get("world_info") as Dictionary)["bounds"]
		if not bounds.grow(8.0).has_point(player.position):
			failures.append("player escaped world bounds at %s" % player.position)

	_finish_smoke(failures)


func _finish_smoke(failures: Array[String]) -> void:
	if failures.is_empty():
		print("SMOKE PASS")
		get_tree().quit(0)
	else:
		for failure in failures:
			printerr("SMOKE FAIL: " + failure)
		get_tree().quit(1)


func _shot(shot_name: String) -> void:
	for i in 10:
		await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://shots")
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join(shot_name + ".png")
	image.save_png(path)
	print("SHOT SAVED: " + path)
	get_tree().quit(0)
