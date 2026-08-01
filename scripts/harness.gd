extends Node
## Self-verification harness (design doc section 7). User args:
##   --smoke          headless scripted checks; must end with "SMOKE PASS"
##   --shot=<name>    boot, capture shots/<name>.png, quit (needs rendering)
##   --scene=menu     stay on the main menu for the shot (default: game scene)
##   --menu=pause|settings  open that UI before the shot
##   --at=X,Y         teleport the player to tile X,Y before the shot
##   --probe-exclusive  report display mode capabilities and quit

var _shot_menu := ""
var _shot_scene := "game"
var _shot_at := ""
var _shot_backdrop := -1


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var args := OS.get_cmdline_user_args()
	for arg in args:
		if arg.begins_with("--menu="):
			_shot_menu = arg.trim_prefix("--menu=")
		elif arg.begins_with("--scene="):
			_shot_scene = arg.trim_prefix("--scene=")
		elif arg.begins_with("--at="):
			_shot_at = arg.trim_prefix("--at=")
		elif arg.begins_with("--backdrop="):
			_shot_backdrop = int(arg.trim_prefix("--backdrop="))
	for arg in args:
		if arg == "--smoke":
			_smoke.call_deferred()
		elif arg.begins_with("--shot="):
			_shot.call_deferred(arg.trim_prefix("--shot="))
		elif arg == "--probe-exclusive":
			_probe_exclusive.call_deferred()


func _ensure_game_scene() -> void:
	for i in 2:
		await get_tree().process_frame
	var current := get_tree().current_scene
	if current == null or current.name != "Main":
		get_tree().change_scene_to_file("res://scenes/main.tscn")
		for i in 4:
			await get_tree().process_frame


func _smoke() -> void:
	await _ensure_game_scene()
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
		# movement runs in _process (render rate), so checks are wall-time based
		var start: Vector2 = player.position
		Input.action_press("move_right")
		await get_tree().create_timer(0.8).timeout
		Input.action_release("move_right")
		var moved := player.position.x - start.x
		if moved < 40.0:
			failures.append("player barely moved (dx=%.1f after 0.8s)" % moved)
		if floor_layer != null:
			# walk into the map border from just inside it: must be stopped
			player.position = floor_layer.map_to_local(Vector2i(4, 4))
			Input.action_press("move_up")
			await get_tree().create_timer(2.0).timeout
			Input.action_release("move_up")
			var bounds: Rect2 = (main.get("world_info") as Dictionary)["bounds"]
			if not bounds.grow(8.0).has_point(player.position):
				failures.append("player escaped world bounds at %s" % player.position)
			# roof interior-reveal: fades inside a building, returns outside
			var roofs: Array = (main.get("world_info") as Dictionary)["roofs"]
			if roofs.is_empty():
				failures.append("no roofs built")
			else:
				var roof := roofs[0] as RoofReveal
				player.position = floor_layer.map_to_local(Vector2i(12, 11))
				await get_tree().create_timer(0.6).timeout
				if roof.modulate.a > 0.5:
					failures.append("roof did not fade inside (a=%.2f)" % roof.modulate.a)
				player.position = floor_layer.map_to_local(Vector2i(20, 20))
				await get_tree().create_timer(0.6).timeout
				if roof.modulate.a < 0.9:
					failures.append("roof did not return outside (a=%.2f)" % roof.modulate.a)

	# pause menu: Esc opens + pauses, Esc again closes + resumes
	_tap_action("ui_cancel")
	for i in 3:
		await get_tree().process_frame
	if not get_tree().paused:
		failures.append("Esc did not open the pause menu")
	_tap_action("ui_cancel")
	for i in 3:
		await get_tree().process_frame
	if get_tree().paused:
		failures.append("Esc did not close the pause menu")

	_finish_smoke(failures)


func _tap_action(action: String) -> void:
	var press := InputEventAction.new()
	press.action = action
	press.pressed = true
	Input.parse_input_event(press)
	var release := InputEventAction.new()
	release.action = action
	release.pressed = false
	Input.parse_input_event(release)


func _finish_smoke(failures: Array[String]) -> void:
	if failures.is_empty():
		print("SMOKE PASS")
		get_tree().quit(0)
	else:
		for failure in failures:
			printerr("SMOKE FAIL: " + failure)
		get_tree().quit(1)


func _shot(shot_name: String) -> void:
	if _shot_scene != "menu":
		await _ensure_game_scene()
	for i in 6:
		await get_tree().process_frame
	if _shot_at != "":
		var parts := _shot_at.split(",")
		var main := get_tree().current_scene
		var player := main.get_node_or_null("World/Player") as Player
		var floor_layer := main.get_node_or_null("Floor") as TileMapLayer
		if player != null and floor_layer != null and parts.size() == 2:
			player.position = floor_layer.map_to_local(
				Vector2i(int(parts[0]), int(parts[1])))
	if _shot_menu != "":
		var menu := get_tree().get_first_node_in_group("pause_menu") as PauseMenu
		if menu != null:
			if _shot_menu == "settings":
				menu.open_settings()
			else:
				menu.open()
	if _shot_backdrop >= 0:
		var main_menu := get_tree().get_first_node_in_group("main_menu")
		if main_menu != null:
			main_menu.call("show_backdrop", _shot_backdrop)
	for i in 40:
		await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://shots")
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join(shot_name + ".png")
	image.save_png(path)
	print("SHOT SAVED: " + path)
	get_tree().quit(0)


func _probe_exclusive() -> void:
	print("PROBE before: screen=", DisplayServer.screen_get_size(),
		" window=", DisplayServer.window_get_size())
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN)
	DisplayServer.window_set_size(Vector2i(1920, 1080))
	for i in 40:
		await get_tree().process_frame
	print("PROBE after: screen=", DisplayServer.screen_get_size(),
		" window=", DisplayServer.window_get_size())
	get_tree().quit(0)
