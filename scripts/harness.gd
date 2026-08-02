extends Node
## Self-verification harness (design doc section 7). User args:
##   --smoke          headless scripted checks; must end with "SMOKE PASS"
##   --shot=<name>    boot, capture shots/<name>.png, quit (needs rendering)
##   --scene=menu     stay on the main menu for the shot (default: game scene)
##   --menu=pause|settings  open that UI before the shot
##   --at=X,Y         teleport the player to tile X,Y before the shot
##   --probe-exclusive  report display mode capabilities and quit
##   --leakcheck      raid -> menu, four times; prints node/orphan/object/
##                    memory retention per cycle and a growth verdict

var world_seed := ""  # --seed=<text>: pin the district layout (shots/probes)
# the smoke needs a LIVING world to probe: dying ends the raid and pauses
# the tree behind the debrief, which would strand every later check. The
# probe suppresses it while it works, then turns it back on and asserts
# the debrief really does appear (see the end of _smoke).
var suppress_debrief := false

var _shot_menu := ""
var _shot_scene := "game"
var _shot_at := ""
var _shot_backdrop := -1
var _shot_face := ""


func _audio_debug() -> void:
	## --audiodebug: drop the master to zero and dump the bus graph, so a
	## "the slider does nothing" report gets measured instead of guessed
	await get_tree().process_frame
	# drive the REAL panel, not the setter behind it: the report is "the
	# slider does nothing", so the slider is what has to be tested
	var panel := VolumePanel.new()
	get_tree().root.add_child(panel)
	await get_tree().process_frame
	var sliders := panel.find_children("", "HSlider", true, false)
	print("PANEL sliders=%d" % sliders.size())
	if not sliders.is_empty():
		(sliders[0] as HSlider).value = 0.0
	await get_tree().process_frame
	print("AFTER master=%.2f music=%.2f" % [Settings.volume_master,
		Settings.volume_music])
	panel.queue_free()
	for i in AudioServer.bus_count:
		print("BUS %d %-8s vol=%6.1f mute=%s send=%s" % [i,
			AudioServer.get_bus_name(i), AudioServer.get_bus_volume_db(i),
			AudioServer.is_bus_mute(i), AudioServer.get_bus_send(i)])
	for node in get_tree().root.get_children():
		for child in node.get_children():
			if child is AudioStreamPlayer:
				var p := child as AudioStreamPlayer
				print("PLAYER %s/%s bus=%s playing=%s db=%.1f" % [
					node.name, p.name, p.bus, p.playing, p.volume_db])


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var args := OS.get_cmdline_user_args()
	for arg in args:
		if arg.begins_with("--seed="):
			world_seed = arg.trim_prefix("--seed=")
		elif arg == "--audiodebug":
			_audio_debug.call_deferred()
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
		elif arg == "--leakcheck":
			_leakcheck.call_deferred()


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
	suppress_debrief = true      # a living world to probe; asserted at the end
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

	# a CLOSED door has to be a wall: shove straight at one and stay put.
	# Sweep along the leaf as well as dead centre — a collider that is too
	# SHORT lets you round its ends, which reads as walking through the door.
	var block_doors := get_tree().get_nodes_in_group("doors")
	var gap_offsets := [-8.0, -4.0, 0.0, 4.0, 8.0]
	if player != null and not block_doors.is_empty():
		var blocker := block_doors[0] as Door
		if blocker != null and not blocker.is_open():
			var shut_mid := blocker.doorway_center()
			var shut_thru := blocker.doorway_through()
			var shut_along := blocker.doorway_along()
			var shut_norm := blocker.doorway_normal()
			for lateral in gap_offsets:
				var at: Vector2 = shut_mid + shut_along * float(lateral)
				player.position = at - shut_thru * 20.0
				await get_tree().process_frame
				# which side of the wall PLANE we set off from — crossing it
				# is the only thing that counts as walking through
				var side_before: float = signf(
					(player.position - at).dot(shut_norm))
				_shove(player, shut_thru, 34.0)
				await get_tree().process_frame
				if (player.position - at).dot(shut_norm) * side_before < -1.0:
					failures.append("walked through a closed door (offset %d)"
						% int(lateral))
					break

	# an OPEN door's leaf is still solid — it just stands somewhere else.
	# Not a flag check: SHOVE INTO the swung panel where the art draws it.
	if player != null and not block_doors.is_empty():
		var swung := block_doors[0] as Door
		if swung != null:
			# the swing is 4 frames at 0.06s — wait it OUT, not a fixed
			# frame count (at 240 fps twelve frames is a twentieth of it,
			# and the door was still open when the next check ran)
			swung.toggle()
			# MID-SWING the doorway is still shut. _shove takes no frames, so
			# this lands inside the 0.24s animation: a door that still looks
			# closed must not be walkable.
			await get_tree().process_frame
			await get_tree().process_frame      # let set_deferred land
			var mid := swung.doorway_center()
			var mid_thru := swung.doorway_through()
			var mid_norm := swung.doorway_normal()
			player.position = mid - mid_thru * 20.0
			await get_tree().process_frame
			var mid_side: float = signf((player.position - mid).dot(mid_norm))
			_shove(player, mid_thru, 34.0)
			if (player.position - mid).dot(mid_norm) * mid_side < -1.0:
				failures.append("walked through a door that was still swinging")
			await get_tree().create_timer(0.45).timeout
			if swung.is_open() and not swung.leaf_is_solid():
				failures.append("an open door's leaf lost its collision")
			if swung.is_open():
				var leaf_at := swung.leaf_center()
				var into := swung.leaf_normal()
				for side in [1.0, -1.0]:
					player.position = leaf_at + into * 20.0 * float(side)
					await get_tree().process_frame
					_shove(player, -into * float(side), 34.0)
					await get_tree().process_frame
					# crossing the panel line means the swung leaf is a ghost
					if (player.position - leaf_at).dot(into) * float(side) < 1.0:
						failures.append(
							"walked through an open door's leaf (side %d)"
								% int(side))
						break
				# ...and the OPENING itself must still let you in, or the
				# door is just a wall with extra steps. A player walks round
				# a swung leaf, so sweep across the gap and require that SOME
				# line through it works.
				var gap := swung.doorway_center()
				var thru := swung.doorway_through()
				var side_step := swung.doorway_along()
				var gap_norm := swung.doorway_normal()
				var got_in := false
				for lateral in gap_offsets:
					# float(): the loop var is a Variant out of an untyped
					# array literal, so := cannot infer the sum's type
					var aim: Vector2 = gap + side_step * float(lateral)
					player.position = aim - thru * 20.0
					await get_tree().process_frame
					var was: float = signf((player.position - aim).dot(gap_norm))
					_shove(player, thru, 40.0)
					await get_tree().process_frame
					# got in == crossed the wall plane, not merely slid along it
					if (player.position - aim).dot(gap_norm) * was < -1.0:
						got_in = true
						break
				if not got_in:
					failures.append("an open doorway was not passable")
			swung.toggle()
			await get_tree().create_timer(0.45).timeout

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
			# DRIVE, in whichever direction is open. This asserts that the
			# driving system works — not that one particular car happens to
			# be parked with room. A car boxed in by a wall genuinely can't
			# move, and the test used to fail the whole build for it the
			# moment the layout shifted a parked car's neighbours.
			var best_move := 0.0
			for dir in [Vector2(0.8944, 0.4472), Vector2(-0.8944, -0.4472),
					Vector2(0.8944, -0.4472), Vector2(-0.8944, 0.4472)]:
				var car_start := car.global_position
				car.auto_drive = dir
				await get_tree().create_timer(0.8).timeout
				car.auto_drive = Vector2.ZERO
				best_move = maxf(best_move,
					car.global_position.distance_to(car_start))
				if best_move >= 40.0:
					break
				await get_tree().create_timer(0.3).timeout   # roll to a stop
			if best_move < 40.0:
				failures.append("car would not drive in any direction "
					+ "(best %.1f px)" % best_move)
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

	# LAST, because it ends the raid: three rounds must put up the debrief
	# with the hit locations on it, not respawn you (v0.6.61)
	suppress_debrief = false
	var dying := _find_player()
	if dying != null:
		dying.take_hit("thorax", "a marksman on the wire")
		dying.take_hit("head", "a marksman on the wire")
		dying.take_hit("thorax", "a marksman on the wire")
		var waited := 0.0
		var debrief := main.get_node_or_null("DeathScreen") as DeathScreen
		while waited < 4.0 and (debrief == null or not debrief.visible):
			await get_tree().create_timer(0.2).timeout
			waited += 0.2
			debrief = main.get_node_or_null("DeathScreen") as DeathScreen
		if debrief == null or not debrief.visible:
			failures.append("dying did not end the raid into the debrief")
		elif not dying.dead:
			failures.append("the debrief came up but the raider is not dead")
		else:
			debrief.dismiss()

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


func _leakcheck() -> void:
	## --leakcheck: deploy into a raid and back out to the menu, over and
	## over, printing what the process is still holding each time.
	##
	## Code review is weak at finding leaks; this measures them. What matters
	## is the TREND across cycles, not the absolute numbers — the first cycle
	## always looks worse because caches and autoload buffers fill once.
	## ORPHANS is the sharpest signal: a node that left the tree without being
	## freed is a leak with no excuse.
	suppress_debrief = true
	var rows: Array[Dictionary] = []
	for cycle in 4:
		await _ensure_game_scene()
		await get_tree().create_timer(1.5).timeout
		var in_raid := {
			"nodes": Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
			"orphans": Performance.get_monitor(
				Performance.OBJECT_ORPHAN_NODE_COUNT),
			"objects": Performance.get_monitor(Performance.OBJECT_COUNT),
			"mem": Performance.get_monitor(Performance.MEMORY_STATIC),
		}
		get_tree().change_scene_to_file("res://scenes/menu.tscn")
		# a scene swap frees the old tree over the following frames; give it
		# real time or every cycle reads as a leak
		await get_tree().create_timer(2.0).timeout
		var at_menu := {
			"nodes": Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
			"orphans": Performance.get_monitor(
				Performance.OBJECT_ORPHAN_NODE_COUNT),
			"objects": Performance.get_monitor(Performance.OBJECT_COUNT),
			"mem": Performance.get_monitor(Performance.MEMORY_STATIC),
		}
		rows.append(at_menu)
		print("LEAK cycle=%d raid_nodes=%d | menu nodes=%d orphans=%d objects=%d mem=%.2fMB"
			% [cycle, int(in_raid["nodes"]), int(at_menu["nodes"]),
				int(at_menu["orphans"]), int(at_menu["objects"]),
				float(at_menu["mem"]) / 1048576.0])
	# verdict off the settled cycles: cycle 0 pays for one-time caches
	if rows.size() >= 3:
		var first: Dictionary = rows[1]
		var last: Dictionary = rows[rows.size() - 1]
		var node_growth := int(last["nodes"]) - int(first["nodes"])
		var obj_growth := int(last["objects"]) - int(first["objects"])
		var mem_growth := (float(last["mem"]) - float(first["mem"])) / 1048576.0
		print("LEAK VERDICT nodes+%d objects+%d mem+%.2fMB orphans=%d" % [
			node_growth, obj_growth, mem_growth, int(last["orphans"])])
	get_tree().quit(0)


func _shove(body: CharacterBody2D, dir: Vector2, distance: float) -> void:
	## Push a body along dir in fixed 1 px steps until it has tried to cover
	## `distance`, stopping dead on whatever it hits.
	##
	## NOT velocity + move_and_slide. move_and_slide scales by the frame
	## delta, and a headless run is uncapped — each call advanced the player
	## a fraction of a pixel, so every "did it walk through?" assertion passed
	## without the player ever reaching the thing it was meant to hit. The
	## closed-door test was green for that reason alone. move_and_collide
	## takes the motion outright, so this is frame-rate independent.
	var step := dir.normalized()
	for i in int(ceil(distance)):
		var hit := body.move_and_collide(step)
		if hit != null:
			# spend what is left of the step sliding along the surface, the
			# way move_and_slide would. Without this a graze reads as a wall,
			# and a door you can actually slide around would test as solid.
			body.move_and_collide(hit.get_remainder().slide(hit.get_normal()))


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
			elif _shot_menu == "volume":
				menu.open_volume()
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
		if arg == "--death":
			# take a few rounds somewhere believable, then abandon: the
			# debrief has to be shootable to be judged
			var hurt := _find_player()
			var scene := get_tree().current_scene
			if hurt != null and scene != null and scene.has_method("abandon_raid"):
				Raid.add_xp(260)
				hurt.take_hit("thorax", "a marksman on the wire")
				hurt.take_hit("left leg", "a marksman on the wire")
				hurt.take_hit("thorax", "a marksman on the wire")
				scene.call("abandon_raid")
				for i in 4:
					await get_tree().process_frame
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
		if arg.begins_with("--upstairs="):
			# put the player on a second story and look at it. The reported
			# bug is "furniture floats, no floor" and the slab is MEASURABLY
			# built (see --probe-world UPPERS), so the only way to settle it
			# is to photograph the thing.
			var idx := int(arg.trim_prefix("--upstairs="))
			var main_node := get_tree().current_scene
			var uppers: Array = (main_node.get("world_info") as Dictionary).get(
				"uppers", []) as Array
			if idx >= 0 and idx < uppers.size():
				var reg := uppers[idx] as Dictionary
				var stairs_cell: Vector2i = reg["stairs_cell"]
				var pl := _find_player()
				var fl := main_node.get("_floor_layer") as TileMapLayer
				if pl != null and fl != null:
					pl.global_position = fl.map_to_local(stairs_cell)
					await get_tree().process_frame
					main_node.call("_on_stairs_used", idx)
					for i in 6:
						await get_tree().process_frame
					var cont := reg["container"] as Node2D
					print("UPSTAIRS idx=%d upstairs=%s lift=%.1f cells=%s"
						% [idx, str(pl.upstairs), pl.floor_lift,
							str(reg["cells"])])
					print("UPSTAIRS slab visible=%s children=%d pos=%s props=%d"
						% [str(cont.visible), cont.get_child_count(),
							str(cont.global_position),
							(reg["upper_props"] as Array).size()])
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
	# --perf --map=transit measures the map screen HELD OPEN over the live
	# raid. It does not pause the tree, so whatever it redraws lands on top
	# of everything else — the one place a UI panel can cost real frames.
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--map="):
			var map_view := get_tree().current_scene.get_node_or_null("MapView")
			if map_view != null:
				map_view.call("set_open", true)
				map_view.call("_set_mode", arg.trim_prefix("--map="))
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
	# roads carry [x, width, span_from, span_to] — a road that stops short
	# has a span narrower than the playable band (v0.6.51)
	var vec: Dictionary = info.get("map_vec", {})
	print("ROADS_V %s" % [vec.get("roads_v", [])])
	print("ROADS_H %s" % [vec.get("roads_h", [])])
	print("SHEDDERS green=%d red=%d needle=%d" % [
		(info.get("leaf_trees", PackedVector2Array()) as PackedVector2Array).size(),
		(info.get("leaf_trees_red", PackedVector2Array()) as PackedVector2Array).size(),
		(info.get("leaf_trees_needle", PackedVector2Array()) as PackedVector2Array).size()])
	var stairs_cells: Array[Vector2i] = []
	for s in get_tree().get_nodes_in_group("stairs"):
		stairs_cells.append(floor_layer.local_to_map((s as Node2D).global_position))
	print("STAIRS total=%d cells=%s" % [stairs_cells.size(), stairs_cells.slice(0, 8)])
	# second floors: every flight of stairs must have an upper registry, and
	# every registry must have actually painted a floor. A building whose
	# furniture shows with no slab under it lands here.
	var uppers: Array = info.get("uppers", []) as Array
	var floorless := 0
	var propless := 0
	for u in uppers:
		var reg := u as Dictionary
		var container := reg["container"] as Node2D
		if container == null or container.get_child_count() == 0:
			floorless += 1
		if (reg["upper_props"] as Array).is_empty():
			propless += 1
	print("UPPERS total=%d floorless=%d propless=%d stairs=%d" % [
		uppers.size(), floorless, propless, stairs_cells.size()])
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
