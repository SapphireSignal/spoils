extends Node
## Self-verification harness (design doc section 7). User args:
##   --smoke          headless scripted checks; must end with "SMOKE PASS"
##   --shot=<name>    boot, capture shots/<name>.png, quit (needs rendering)
##   --scene=menu     stay on the main menu for the shot (default: game scene)
##   --menu=pause|settings  open that UI before the shot
##   --at=X,Y         teleport the player to tile X,Y before the shot
##   --probe-exclusive  report display mode capabilities and quit

var world_seed := ""  # --seed=<text>: pin the district layout (shots/probes)

var _shot_menu := ""
var _shot_scene := "game"
var _shot_at := ""
var _shot_backdrop := -1
var _shot_face := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var args := OS.get_cmdline_user_args()
	for arg in args:
		if arg.begins_with("--seed="):
			world_seed = arg.trim_prefix("--seed=")
		elif arg.begins_with("--menu="):
			_shot_menu = arg.trim_prefix("--menu=")
		elif arg.begins_with("--scene="):
			_shot_scene = arg.trim_prefix("--scene=")
		elif arg.begins_with("--at="):
			_shot_at = arg.trim_prefix("--at=")
		elif arg.begins_with("--backdrop="):
			_shot_backdrop = int(arg.trim_prefix("--backdrop="))
		elif arg.begins_with("--face="):
			_shot_face = arg.trim_prefix("--face=")
	for arg in args:
		if arg == "--smoke":
			_smoke.call_deferred()
		elif arg.begins_with("--shot="):
			_shot.call_deferred(arg.trim_prefix("--shot="))
		elif arg == "--perf":
			_perf.call_deferred()
		elif arg == "--probe-world":
			_probe_world.call_deferred()
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
	# the world builds asynchronously behind the deploy screen — wait for it,
	# AND for the deploy screen to fully fade (a half-faded label was ghosting
	# into captures)
	var waited := 0.0
	while waited < 30.0:
		current = get_tree().current_scene
		if current != null and not (current.get("world_info") as Dictionary).is_empty() \
				and current.get("_deploy_screen") == null:
			break
		await get_tree().create_timer(0.2).timeout
		waited += 0.2


func _smoke() -> void:
	await _ensure_game_scene()
	var failures: Array[String] = []

	var main := get_tree().current_scene
	if main == null:
		_finish_smoke(["no current scene"])
		return

	var info: Dictionary = main.get("world_info")
	var cells: Vector2i = info.get("cells", Vector2i.ZERO)
	var floor_layer := main.get_node_or_null("Floor") as TileMapLayer
	if floor_layer == null:
		failures.append("Floor TileMapLayer missing")
	elif floor_layer.get_used_cells().size() != cells.x * cells.y:
		failures.append("floor cell count %d != %d" % [
			floor_layer.get_used_cells().size(), cells.x * cells.y])

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
		# crouch: slower and using the crouch sheet (force hold mode for the
		# test — simulated presses don't produce toggle edges)
		var prev_toggle: bool = Settings.crouch_toggle
		Settings.crouch_toggle = false
		start = player.position
		Input.action_press("crouch")
		Input.action_press("move_right")
		await get_tree().create_timer(0.8).timeout
		Input.action_release("move_right")
		Input.action_release("crouch")
		var crouch_moved := player.position.x - start.x
		Settings.crouch_toggle = prev_toggle
		if crouch_moved >= moved * 0.85:
			failures.append("crouch not slower (dx=%.1f vs %.1f)" % [crouch_moved, moved])
		# keybinds registered
		for action in Settings.BIND_ACTIONS:
			if InputMap.action_get_events(action).is_empty():
				failures.append("action '%s' has no bound key" % action)
		if floor_layer != null:
			# walk into the map border from inside the deep woods: must stay in
			player.position = floor_layer.map_to_local(Vector2i(10, 10))
			Input.action_press("move_up")
			await get_tree().create_timer(2.0).timeout
			Input.action_release("move_up")
			var map_rect: Rect2 = info["map_rect"]
			if not map_rect.grow(8.0).has_point(player.position):
				failures.append("player escaped the map at %s" % player.position)
			# roof interior-reveal: fades inside a building, returns outside
			var roofs: Array = info["roofs"]
			if roofs.is_empty():
				failures.append("no roofs built")
			else:
				var roof := roofs[0] as RoofReveal
				var inside := roof.cells.get_center()
				player.position = floor_layer.map_to_local(inside)
				await get_tree().create_timer(0.6).timeout
				if roof.modulate.a > 0.5:
					failures.append("roof did not fade inside (a=%.2f)" % roof.modulate.a)
				player.position = floor_layer.map_to_local(
					roof.cells.position - Vector2i(5, 5))
				await get_tree().create_timer(0.6).timeout
				if roof.modulate.a < 0.9:
					failures.append("roof did not return outside (a=%.2f)" % roof.modulate.a)

	# edge sniper: standing at the map edge past the grace period draws fire
	if player != null and floor_layer != null:
		var full_hp: int = player.hp
		player.position = floor_layer.map_to_local(Vector2i(2, 160))
		await get_tree().create_timer(5.6).timeout
		if player.hp >= full_hp:
			failures.append("edge sniper never hit (hp still %d)" % player.hp)
		player.respawn(info["spawn"])
		await get_tree().process_frame

	# doors: closed by default, F-toggle opens (collider off) and closes back
	var doors := get_tree().get_nodes_in_group("doors")
	if doors.is_empty():
		failures.append("no doors in the world")
	else:
		var door := doors[0] as Door
		if door.is_open():
			failures.append("door started open")
		door.toggle()
		await get_tree().create_timer(0.5).timeout
		if not door.is_open():
			failures.append("door did not open on toggle")
		door.toggle()
		await get_tree().create_timer(0.5).timeout
		if door.is_open():
			failures.append("door did not close on second toggle")

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
	if _shot_face != "":
		var dirs := ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]
		var face_player := get_tree().current_scene.get_node_or_null("World/Player")
		if face_player != null and dirs.has(_shot_face):
			face_player.set("_dir_index", dirs.find(_shot_face))
	if "--crouch" in OS.get_cmdline_user_args():
		Input.action_press("crouch")
	if "--flashlight" in OS.get_cmdline_user_args():
		var lit_player := get_tree().current_scene.get_node_or_null("World/Player") as Player
		if lit_player != null:
			lit_player.set_flashlight(true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--weather=") or arg.begins_with("--tod="):
			var environment := get_tree().get_first_node_in_group("environment")
			if environment != null:
				if arg == "--weather=rain":
					environment.call("force_weather", true)
				elif arg.begins_with("--tod="):
					environment.call("force_time", float(arg.trim_prefix("--tod=")))
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
	if _shot_menu == "changelog" and _shot_scene == "menu":
		var menu_scene := get_tree().get_first_node_in_group("main_menu")
		if menu_scene != null:
			menu_scene.call("_open_changelog")
	for i in 40:
		await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://shots")
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join(shot_name + ".png")
	image.save_png(path)
	print("SHOT SAVED: " + path)
	get_tree().quit(0)


func _perf() -> void:
	## Frame pacing probe: build the district, settle, then sample 6 seconds
	## of real frames and report the average and the worst hitch.
	await _ensure_game_scene()
	for arg in OS.get_cmdline_user_args():  # same scene flags as --shot
		if arg == "--weather=rain" or arg.begins_with("--tod="):
			var environment := get_tree().get_first_node_in_group("environment")
			if environment != null:
				if arg == "--weather=rain":
					environment.call("force_weather", true)
				else:
					environment.call("force_time", float(arg.trim_prefix("--tod=")))
		elif arg == "--flashlight":
			var lit := get_tree().current_scene.get_node_or_null("World/Player") as Player
			if lit != null:
				lit.set_flashlight(true)
	for i in 40:
		await get_tree().process_frame
	var frames := 0
	var worst_ms := 0.0
	var start_us := Time.get_ticks_usec()
	var prev_us := start_us
	while Time.get_ticks_usec() - start_us < 6_000_000:
		await get_tree().process_frame
		var now_us := Time.get_ticks_usec()
		worst_ms = maxf(worst_ms, float(now_us - prev_us) / 1000.0)
		prev_us = now_us
		frames += 1
	var seconds := float(Time.get_ticks_usec() - start_us) / 1_000_000.0
	print("PERF frames=%d avg_fps=%.1f worst_frame_ms=%.2f process_ms=%.3f nodes=%d" % [
		frames, frames / seconds, worst_ms,
		Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))])
	get_tree().quit(0)


func _probe_world() -> void:
	## Content census: lamp/vehicle/door counts and shot-aimable positions.
	await _ensure_game_scene()
	var main := get_tree().current_scene
	var info: Dictionary = main.get("world_info")
	var floor_layer: TileMapLayer = info["floor"]

	var lamps := get_tree().get_nodes_in_group("street_lamps")
	var working_cells: Array[Vector2i] = []
	for lamp in lamps:
		if lamp.get("working"):
			working_cells.append(floor_layer.local_to_map((lamp as Node2D).position))
	print("LAMPS total=%d working=%d cells=%s" % [
		lamps.size(), working_cells.size(), working_cells.slice(0, 6)])

	var lit: StreetLamp = null
	for lamp in lamps:
		if lamp.get("working"):
			lit = lamp
			break
	if lit != null:
		# force night through the environment (the real driver), then sample
		var environment := get_tree().get_first_node_in_group("environment")
		if environment != null:
			environment.call("force_time", 0.0)
		for i in 10:
			await get_tree().process_frame
		var glow: Sprite2D = lit.get("_glow")
		var light: PointLight2D = lit.get("_light")
		print("SAMPLE lamp world_pos=%s glow_a=%.2f light_energy=%.2f processing=%s night=%.2f" % [
			(lit as Node2D).global_position, glow.modulate.a, light.energy,
			str(lit.is_processing()), float(environment.get("night_amount"))])

	var vehicle_cells: Array[Vector2i] = []
	var world: Node2D = info["ysort"]
	for child in world.get_children():
		for sub in child.get_children():
			if sub is Sprite2D and (sub as Sprite2D).texture != null \
					and "vehicle_" in (sub as Sprite2D).texture.resource_path:
				vehicle_cells.append(floor_layer.local_to_map((child as Node2D).position))
				break
	print("VEHICLES total=%d cells=%s" % [vehicle_cells.size(), vehicle_cells.slice(0, 10)])
	print("DOORS total=%d" % get_tree().get_nodes_in_group("doors").size())
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
