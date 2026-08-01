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
		elif arg == "--perf-deploy":
			_perf_deploy.call_deferred()
		elif arg == "--probe-sniper":
			_probe_sniper.call_deferred()
		elif arg.begins_with("--shot-splash="):
			_shot_splash.call_deferred(arg.trim_prefix("--shot-splash="))
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
			return
		await get_tree().create_timer(0.2).timeout
		waited += 0.2
	# FAIL FAST: a world that never readied means broken art/scripts — die
	# loudly instead of letting the next step hang forever (the "stuck
	# background task" the user kept killing on 2026-08-01)
	printerr("HARNESS FAIL: world never became ready (30s) — aborting")
	get_tree().quit(1)


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
		# prone crawl: slower again than the crouch (stance forced directly —
		# simulated key presses can't make just_pressed edges, same as the
		# crouch-toggle note above; the Z bind itself is covered below)
		start = player.position
		player.prone = true
		Input.action_press("move_right")
		await get_tree().create_timer(0.8).timeout
		Input.action_release("move_right")
		var prone_moved := player.position.x - start.x
		player.prone = false
		if prone_moved >= crouch_moved * 0.85:
			failures.append("prone not slower than crouch (dx=%.1f vs %.1f)" % [
				prone_moved, crouch_moved])
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

	# edge sniper: standing past the barricades past the grace period draws
	# fire (deep in the buffer the fire escalates and may kill + respawn
	# within the window, so track HITS, not remaining hp)
	if player != null and floor_layer != null:
		# array capture: GDScript lambdas copy captured LOCALS by value, so a
		# bare bool flag would never reach this scope
		var hit_flag: Array[bool] = [false]
		player.hurt.connect(func() -> void: hit_flag[0] = true)
		player.position = floor_layer.map_to_local(Vector2i(12, 160))
		await get_tree().create_timer(5.6).timeout
		if not hit_flag[0]:
			failures.append("edge sniper never hit past the barricades")
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
		# THE PROMPT IS THE PERMISSION (user call): F must work standing at
		# the door and do NOTHING from across the street. Toggling the door
		# object directly can never catch a break in that rule.
		if player != null:
			player.global_position = door.global_position + Vector2(0.0, 20.0)
			await get_tree().process_frame
			await get_tree().process_frame
			player.call("_interact")
			await get_tree().create_timer(0.45).timeout
			if not door.is_open():
				failures.append("f did not open the door while prompted")
			else:
				player.call("_interact")
				await get_tree().create_timer(0.45).timeout
			player.global_position = door.global_position + Vector2(0.0, 300.0)
			await get_tree().process_frame
			await get_tree().process_frame
			var was_open := door.is_open()
			player.call("_interact")
			await get_tree().create_timer(0.45).timeout
			if door.is_open() != was_open:
				failures.append("f reached a door with no prompt on screen")

	# second stories: use the nearest stairs — the upper room appears, the
	# player lifts, using them again comes back down
	var stairs_nodes := get_tree().get_nodes_in_group("stairs")
	if stairs_nodes.is_empty():
		failures.append("no stairs in the world (two-story houses missing)")
	elif player != null:
		var stairs := stairs_nodes[0] as Stairs
		player.position = stairs.global_position + Vector2(2.0, 16.0)
		stairs.use()
		await get_tree().create_timer(0.3).timeout
		if player.floor_lift <= 0.0:
			failures.append("stairs up did not lift the player")
		stairs.use()
		await get_tree().create_timer(0.3).timeout
		if player.floor_lift != 0.0:
			failures.append("stairs down did not ground the player")

	# driveable cars: enter, start the engine, roll forward, step out
	var car_nodes := get_tree().get_nodes_in_group("cars")
	if car_nodes.is_empty():
		failures.append("no driveable cars in the world")
	elif player != null:
		var car := car_nodes[0] as DriveableCar
		player.position = car.global_position + Vector2(0.0, 30.0)
		car.enter(player)
		await get_tree().create_timer(0.6).timeout
		if player.driving != car:
			failures.append("player did not end up driving after enter()")
		elif not car.engine_on:
			failures.append("the engine did not start on entry")
		else:
			# headless sends no input — feed the drive vector directly
			car.auto_drive = Vector2(0.8944, 0.4472)
			var car_start := car.global_position
			await get_tree().create_timer(1.0).timeout
			car.auto_drive = Vector2.ZERO
			if car.global_position.distance_to(car_start) < 40.0:
				failures.append("car barely moved while driving (%.1f px)" %
					car.global_position.distance_to(car_start))
			car.exit_car()
			await get_tree().create_timer(0.6).timeout
			if player.driving != null or not player.visible:
				failures.append("player did not step out of the car")
			elif car.engine_on:
				failures.append("the engine kept running after stepping out")
		player.respawn(info["spawn"])
		await get_tree().process_frame

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


func _find_player() -> Player:
	return get_tree().current_scene.get_node_or_null("World/Player") as Player


func _apply_env_flags() -> void:
	# --weather=rain / --tod=<0..1> — shared by --shot and --perf
	var environment := get_tree().get_first_node_in_group("environment")
	if environment == null:
		return
	for arg in OS.get_cmdline_user_args():
		if arg == "--weather=rain":
			environment.call("force_weather", true)
		elif arg.begins_with("--tod="):
			environment.call("force_time", float(arg.trim_prefix("--tod=")))


func _shot(shot_name: String) -> void:
	if _shot_scene != "menu":
		await _ensure_game_scene()
	for i in 6:
		await get_tree().process_frame
	var player := _find_player()
	if _shot_at != "":
		var parts := _shot_at.split(",")
		var floor_layer := get_tree().current_scene.get_node_or_null("Floor") as TileMapLayer
		if player != null and floor_layer != null and parts.size() == 2:
			player.position = floor_layer.map_to_local(
				Vector2i(int(parts[0]), int(parts[1])))
	if player != null and _shot_face != "":
		var dirs := ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]
		if dirs.has(_shot_face):
			player._dir_index = dirs.find(_shot_face)
	if "--crouch" in OS.get_cmdline_user_args():
		Input.action_press("crouch")
	if player != null and "--prone" in OS.get_cmdline_user_args():
		player.prone = true
	if player != null and "--flashlight" in OS.get_cmdline_user_args():
		player.set_flashlight(true)
	_apply_env_flags()
	for i in 10:                # let the camera settle on the teleported
		await get_tree().process_frame
	_apply_env_flags()          # re-apply: env prefills (fog) at THIS view
	if player != null and "--upstairs" in OS.get_cmdline_user_args():
		# climb the nearest flight for second-story captures
		var best_stairs: Node2D = null
		var best_d := 1.0e12
		for node in get_tree().get_nodes_in_group("stairs"):
			var d: float = (node as Node2D).global_position.distance_squared_to(
				player.global_position)
			if d < best_d:
				best_d = d
				best_stairs = node
		if best_stairs != null:
			player.global_position = best_stairs.global_position + Vector2(2.0, 16.0)
			(best_stairs as Stairs).use()
			for i in 6:
				await get_tree().process_frame
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
	if _shot_menu == "mapselect" and _shot_scene == "menu":
		var select_scene := get_tree().get_first_node_in_group("main_menu")
		if select_scene != null:
			select_scene.call("_open_map_select")
			select_scene.call("_select_transit")
	for arg in OS.get_cmdline_user_args():
		if arg == "--freight":
			var train := get_tree().get_first_node_in_group("trains")
			if train != null:
				train.call("force_waiting")
		if arg == "--toll":
			var dialog := get_tree().current_scene.get_node_or_null("TollDialog")
			if dialog != null:
				dialog.call("open")
		if arg.begins_with("--extract="):
			# jump straight to the debrief with a sample ledger, so the
			# screen can be judged before enemies exist to fill it
			var screen := get_tree().current_scene.get_node_or_null("ExtractScreen")
			if screen != null:
				Raid.add_xp(340)
				Raid.record_kill("stray", "chest")
				Raid.record_kill("stray", "head")
				Raid.record_kill("magpie", "leg", true)
				screen.call("show_debrief", arg.trim_prefix("--extract="))
		if arg.begins_with("--map="):
			var wanted := arg.trim_prefix("--map=")
			var map_view := get_tree().current_scene.get_node_or_null("MapView")
			if map_view != null:
				map_view.call("set_open", true)
				map_view.call("_set_mode", wanted)
				for i in 4:
					await get_tree().process_frame
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
	_apply_env_flags()  # same scene flags as --shot
	if "--flashlight" in OS.get_cmdline_user_args():
		var player := _find_player()
		if player != null:
			player.set_flashlight(true)
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


func _perf_deploy() -> void:
	## Frame pacing THROUGH a deploy: menu -> scene change -> async build ->
	## first second of play. The worst frame is the number that matters —
	## the deploy screen must hold the user's refresh rate.
	for i in 5:
		await get_tree().process_frame
	var t0 := Time.get_ticks_usec()
	get_tree().change_scene_to_file("res://scenes/main.tscn")
	var frames := 0
	var prev_us := Time.get_ticks_usec()
	var built_us := 0
	var spikes: Array[Vector2] = []  # (ms, seconds since deploy click)
	while true:
		await get_tree().process_frame
		var now_us := Time.get_ticks_usec()
		var ms := float(now_us - prev_us) / 1000.0
		spikes.append(Vector2(ms, float(now_us - t0) / 1_000_000.0))
		prev_us = now_us
		frames += 1
		var current := get_tree().current_scene
		if built_us == 0 and current != null and current.name == "Main" \
				and not (current.get("world_info") as Dictionary).is_empty():
			built_us = now_us
		if built_us != 0 and now_us - built_us > 1_000_000:
			break
	spikes.sort_custom(func(a: Vector2, b: Vector2) -> bool: return a.x > b.x)
	var top := ""
	for i in mini(4, spikes.size()):
		top += " %.1fms@%.2fs" % [spikes[i].x, spikes[i].y]
	print("PERF-DEPLOY frames=%d build_s=%.2f worst:%s" % [
		frames, float(built_us - t0) / 1_000_000.0, top])
	get_tree().quit(0)


func _shot_splash(shot_name: String) -> void:
	## Capture the studio splash mid-animation (just after the shatter:
	## the revealed signal, its rings, the last shards).
	await get_tree().create_timer(2.4).timeout
	var image := get_viewport().get_texture().get_image()
	var dir := ProjectSettings.globalize_path("res://shots")
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join(shot_name + ".png")
	image.save_png(path)
	print("SHOT SAVED: " + path)
	get_tree().quit(0)


func _probe_sniper() -> void:
	## Live EdgeGuard internals while parked past the barricades.
	await _ensure_game_scene()
	var main := get_tree().current_scene
	var info: Dictionary = main.get("world_info")
	var floor_layer: TileMapLayer = info["floor"]
	var player := main.get_node_or_null("World/Player") as Player
	var guard := main.get_node_or_null("EdgeGuard") as EdgeGuard
	print("barrier_f=%s guard=%s" % [info.get("barrier_f"), guard])
	player.position = floor_layer.map_to_local(Vector2i(12, 160))
	for step in 12:
		await get_tree().create_timer(0.5).timeout
		var u: Vector2 = player.global_position - (info["map_center"] as Vector2)
		var f := absf(u.x) * 0.5 + absf(u.y)
		print("t=%.1f pos=%s f=%.0f depth=%.0f label=%s zone_t=%.2f rounds=%d hp=%d" % [
			step * 0.5 + 0.5, player.global_position, f,
			f - float(info["barrier_f"]), str((guard.get("_label") as Label).visible),
			float(guard.get("_zone_time")), (guard.get("_rounds") as Array).size(),
			player.hp])
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
	var door_cells: Array[Vector2i] = []
	for door in get_tree().get_nodes_in_group("doors"):
		door_cells.append(floor_layer.local_to_map((door as Node2D).global_position))
	print("DOORS total=%d cells=%s" % [door_cells.size(), door_cells.slice(0, 5)])
	var traffic: Array = info.get("traffic_cells", [])
	print("TRAFFIC total=%d cells=%s" % [traffic.size(), traffic.slice(0, 6)])
	var bush_cells: Array[Vector2i] = []
	for bush in (info.get("bushes", []) as Array):
		bush_cells.append(floor_layer.local_to_map((bush as Node2D).position))
	print("FOLIAGE bushes=%d cells=%s" % [bush_cells.size(), bush_cells.slice(0, 6)])
	print("WALKS cells=%d" % int(info.get("walk_cells", -1)))
	# v0.6.18 places: zone block rects (cell coords) + the interactables
	var zones: Dictionary = info.get("zones", {})
	for zone_name in zones:
		print("ZONE %s blocks=%s" % [zone_name, zones[zone_name]])
	var poi: Dictionary = info.get("poi", {})
	for poi_name in poi:
		print("POI %s=%s" % [poi_name, poi[poi_name]])
	var stairs_cells: Array[Vector2i] = []
	for s in get_tree().get_nodes_in_group("stairs"):
		stairs_cells.append(floor_layer.local_to_map((s as Node2D).global_position))
	print("STAIRS total=%d cells=%s" % [stairs_cells.size(), stairs_cells.slice(0, 8)])
	var car_cells: Array[Vector2i] = []
	for car in get_tree().get_nodes_in_group("cars"):
		car_cells.append(floor_layer.local_to_map((car as Node2D).global_position))
	print("CARS driveable=%d cells=%s" % [car_cells.size(), car_cells.slice(0, 8)])
	var env := get_tree().get_first_node_in_group("environment")
	if env != null:
		env.call("force_time", 0.18)         # dawn: the fog window
		for i in 40:
			await get_tree().process_frame
		var active := 0
		var fog_flags: PackedByteArray = env.get("_fog_active")
		for flag in fog_flags:
			active += flag
		var cam := get_viewport().get_camera_2d()
		var nearest := 1e9
		if cam != null:
			for s in (env.get("_fog_spots") as PackedVector2Array):
				nearest = minf(nearest, s.distance_to(cam.get_screen_center_position()))
		print("FOG nearest_spot=%.0f" % nearest)
		var manual_inside := 0
		if cam != null:
			var mc := cam.get_screen_center_position()
			for s in (env.get("_fog_spots") as PackedVector2Array):
				if absf(s.x - mc.x) <= 410.0 and absf(s.y - mc.y) <= 240.0:
					manual_inside += 1
		print("FOG manual_inside=%d cs=%s refresh=%.2f" % [manual_inside,
			str(get_window().content_scale_size), float(env.get("_fog_refresh"))])
		print("FOG spots=%d active=%d near=%d wind=%.1f morning_ok=%s cam=%s at=%s" % [
			(env.get("_fog_spots") as PackedVector2Array).size(), active,
			(env.get("_fog_near") as Array).size(),
			float(env.get("_fog_wind")),
			str(env.call("_morning_amount", 0.18)), str(cam != null),
			str(cam.get_screen_center_position() if cam != null else Vector2.ZERO)])

	# the interact prompt must appear when parked right at a door
	var player := main.get_node_or_null("World/Player") as Player
	var first_door := get_tree().get_first_node_in_group("doors") as Door
	if player != null and first_door != null:
		player.position = first_door.global_position + Vector2(0, 18)
		for i in 3:
			await get_tree().process_frame
		var prompt := main.get("_prompt") as Label
		print("PROMPT visible=%s text='%s'" % [str(prompt.visible), prompt.text])
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
