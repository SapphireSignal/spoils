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
##   --shaderwarm     run the boot shader warm-up cold then warm; the
##                    second must be a no-op or every launch pays the cost
##   --checkdocs      prove the handoff docs still match the repo: every
##                    version claim agrees with the newest git tag, the
##                    renumbered tags still sit on their recorded commits,
##                    and no doc names a file that does not exist. Runs
##                    inside --smoke too; this flag is the one-second
##                    standalone version. Must print "DOCS PASS".
##   --checkclaims    THE NUMBERS GATE. Reads numeric claims out of
##                    CLAUDE.md's own prose and compares each against the
##                    constant the game actually uses at runtime. Exists
##                    because --checkdocs cannot verify a sentence, and the
##                    sentences that rot here are overwhelmingly numeric.
##                    Fails closed: a claim it can no longer parse is a
##                    FAIL. Must print "CLAIMS PASS".
##   --checksec       the security audit: the git remote has not moved, no
##                    network calls exist anywhere, the python toolchain
##                    imports only vetted modules, shelling out is confined
##                    to this file and only to git, and nothing
##                    credential-shaped is tracked. Also runs inside
##                    --smoke. Must print "SEC PASS".

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
	## "the slider does nothing" report gets measured instead of guessed.
	##
	## NOT A STANDALONE ACTION TODAY. It is parsed in the FIRST arg loop,
	## which only sets state and never sets `acted`, and the action loop has
	## no branch for it — so passing it alone prints "HARNESS: no action in
	## [--audiodebug]" and quits 2 before this can print (the first `await`
	## below never resumes). Until it is moved into the second loop, pair it
	## with a real action flag, e.g. `--perf --audiodebug`.
	await get_tree().process_frame
	# THE SLIDER WRITES THE USER'S REAL SETTINGS FILE. Settings.set_volume()
	# calls _save(), which persists master to user://settings.cfg — so
	# without the restore at the bottom of this function, running this once
	# left the GAME MUTED on every future launch, with no on-screen cause
	# and a slider the user never touched sitting at 0%. Never leave a
	# harness path holding a persisted setting.
	var prev_master := Settings.volume_master
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
	# put the user's volume back — LAST, so every dump above still shows the
	# muted graph this flag exists to measure. Re-applies the buses and
	# rewrites settings.cfg. Same save/restore convention as _smoke()'s
	# crouch_toggle.
	Settings.set_volume("master", prev_master)
	print("RESTORED master=%.2f" % Settings.volume_master)


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
	var acted := false
	for arg in args:
		if arg == "--smoke":
			_smoke.call_deferred()
		elif arg.begins_with("--shot="):
			_shot.call_deferred(arg.trim_prefix("--shot="))
		elif arg == "--probe-sort":
			_probe_sort.call_deferred()
		elif arg.begins_with("--film-walk="):
			_film_walk.call_deferred(arg.trim_prefix("--film-walk="))
		elif arg.begins_with("--film="):
			_film.call_deferred(arg.trim_prefix("--film="))
		elif arg == "--perf-walk":
			_perf_walk.call_deferred()
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
		elif arg == "--shaderwarm":
			_shaderwarm.call_deferred()
		elif arg == "--checkdocs":
			_checkdocs.call_deferred()
		elif arg == "--checkclaims":
			_checkclaims.call_deferred()
		elif arg == "--checksec":
			_checksec.call_deferred()
		else:
			continue
		acted = true
	# FAIL LOUD ON A FLAG THAT DOES NOTHING. Args like --toll, --freight and
	# --at= are MODIFIERS for --shot, not actions of their own. Passing one on
	# its own used to boot the game to the menu and sit there forever, which
	# looks exactly like a hung test and holds the shell open until somebody
	# kills it by hand. If args were given at all, one of them has to be an
	# action.
	if not args.is_empty() and not acted:
		printerr("HARNESS: no action in %s" % str(args))
		printerr("HARNESS: expected --smoke, --shot=<name>, "
			+ "--shot-splash=<name>, --perf, "
			+ "--perf-deploy, --probe-world, --probe-sniper, "
			+ "--probe-exclusive, --shaderwarm, --checkdocs, --checkclaims, "
			+ "--checksec or "
			+ "--leakcheck. --toll/--freight/--at=/--seed= are MODIFIERS, "
			+ "not actions of their own — and --seed= pins the district for "
			+ "ANY action that builds a world (--shot, --probe-world, "
			+ "--perf, --probe-sniper, --smoke), not just --shot.")
		get_tree().quit.call_deferred(2)


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
	# DOCS FIRST. It costs a millisecond, needs no world, and a stale handoff
	# is a real failure — there is no sense building a district to find it.
	var failures: Array[String] = _check_docs()
	failures.append_array(_check_claims())
	failures.append_array(_check_security())
	await _ensure_game_scene()

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
	# EVERY door, not just the first. Testing doors[0] alone hid a real seam
	# for releases: when an unrelated change shifted the layout, a DIFFERENT
	# door failed this same check. One sample is not a test.
	var leaky_doors: Array[String] = []
	if player != null:
		for di in block_doors.size():
			var blocker := block_doors[di] as Door
			if blocker == null or blocker.is_open():
				continue
			var shut_mid := blocker.doorway_center()
			var shut_thru := blocker.doorway_through()
			var shut_along := blocker.doorway_along()
			var shut_norm := blocker.doorway_normal()
			for lateral in gap_offsets:
				var at: Vector2 = shut_mid + shut_along * float(lateral)
				# from BOTH sides: a seam you can only reach from the street
				# is still a seam
				for face in [-1.0, 1.0]:
					player.position = at - shut_thru * 20.0 * face
					await get_tree().process_frame
					# only measure from a start that is actually CLEAR. 20 px
					# inside a room can land on furniture or in a wall, and
					# the physics then ejects the body to resolve the
					# overlap — which can put it the far side of the door and
					# read as walking through one. That is the test spawning
					# badly, not the door leaking.
					#
					# recovery_as_collision MUST be true here and it was not,
					# which made this guard a NO-OP for its own stated purpose.
					# A zero-length sweep with recovery off reports "clear"
					# for a body that is already inside geometry — depenetration
					# is not counted as a collision — so a bad spawn sailed
					# straight past the check, and whether the ejection then
					# happened to cross the wall plane came down to float
					# ordering. That is exactly how this check FAILED ONCE AND
					# PASSED ON RE-RUN with an identical binary at v0.6.35.
					# A flaky mandatory gate is worse than no gate: it teaches
					# whoever hits it to run it again instead of reading it.
					if player.test_move(player.global_transform, Vector2.ZERO,
							null, 0.08, true):
						continue
					# which side of the wall PLANE we set off from —
					# crossing it is the only thing that counts as through
					var side_before: float = signf(
						(player.position - at).dot(shut_norm))
					_shove(player, shut_thru * face, 34.0)
					# MEASURE BEFORE YIELDING. _shove uses move_and_collide,
					# which writes global_position synchronously, so the answer
					# is ready the instant it returns — and it has to be read
					# there, because player.gd's own _process runs
					# move_and_slide() EVERY RENDERED FRAME (player.gd:311).
					# The shove parks the body flush against the leaf; that
					# next move_and_slide then depenetrates it, and which way
					# it pops out depends on float error in an overlap of a
					# fraction of a pixel. Reading the position after an await
					# measured that recovery instead of the shove, which is why
					# this check failed on one run and passed on the next with
					# an identical binary — at v0.6.35, and on a DIFFERENT door
					# each time.
					var crossed: bool = (player.position - at).dot(shut_norm) \
						* side_before < -1.0
					await get_tree().process_frame
					if crossed:
						leaky_doors.append("#%d off %d side %d"
							% [di, int(lateral), int(face)])
						break
	if not leaky_doors.is_empty():
		failures.append("walked through closed doors: %s"
			% ", ".join(leaky_doors))

	# an OPEN door's leaf is still solid — it just stands somewhere else.
	# Not a flag check: SHOVE INTO the swung panel where the art draws it.
	if player != null and not block_doors.is_empty():
		var swung := block_doors[0] as Door
		if swung != null:
			# the swing is 4 frames at 0.06s — wait it OUT, not a fixed
			# frame count (at 240 fps twelve frames is a twentieth of it,
			# and the door was still open when the next check ran)
			# stand OUTSIDE and open it: a door swings away from whoever
			# opens it, so from out here the leaf goes into the room and the
			# swing is deterministic for everything below
			player.position = swung.doorway_center() \
				- swung.doorway_through() * 22.0
			await get_tree().process_frame
			swung.toggle(player.global_position)
			if swung.swings_out():
				failures.append("a door opened TOWARD the player")
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
	# with the hit locations on it, not respawn you (v0.5.14)
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


func _shaderwarm() -> void:
	## --shaderwarm: exercise the boot-time shader warm-up, which the smoke
	## never reaches because the harness skips the splash. Runs it COLD, then
	## again WARM, and reports both — the second run must be a no-op or the
	## fingerprint is not sticking and every launch would pay the cost.
	await get_tree().process_frame
	var stamp := "user://shader_stamp.txt"
	if FileAccess.file_exists(stamp):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(stamp))
	print("SHADERWARM cold=%s (stamp cleared)" % str(ShaderWarm.is_cold()))
	var warm := ShaderWarm.new()
	get_tree().root.add_child(warm)
	var t0 := Time.get_ticks_msec()
	await warm.run()
	var cold_ms := Time.get_ticks_msec() - t0
	warm.queue_free()
	await get_tree().process_frame
	print("SHADERWARM first_run_ms=%d now_cold=%s" % [cold_ms,
		str(ShaderWarm.is_cold())])
	# and a second boot with nothing changed must skip entirely
	var t1 := Time.get_ticks_msec()
	var again := ShaderWarm.is_cold()
	print("SHADERWARM second_boot_cold=%s check_ms=%d" % [str(again),
		Time.get_ticks_msec() - t1])
	if again:
		printerr("SHADERWARM FAIL: the stamp did not stick — every launch "
			+ "would recompile")
		get_tree().quit(1)
		return
	get_tree().quit(0)


func _shove(body: CharacterBody2D, dir: Vector2, distance: float) -> void:
	## Push a body along dir in fixed 1 px steps until it has tried to cover
	## `distance`. Each step stops at whatever it hits and then spends the
	## REST of that step sliding along the surface, the way move_and_slide
	## would — so a body can work its way AROUND an obstacle instead of
	## halting at it. (This line used to say "stopping dead on whatever it
	## hits", which the loop below contradicts.) Consequence worth keeping
	## in mind: a non-zero displacement does NOT by itself mean the body got
	## through something. Measure crossing against the wall PLANE.
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


func _root_dir() -> String:
	return ProjectSettings.globalize_path("res://")


func _read_doc(rel: String) -> String:
	# absolute path, NOT res://. docs/ carries a .gdignore so the editor skips
	# it, and .md files are not imported resources — globalize and read the
	# real file instead of hoping the resource loader cooperates.
	var f := FileAccess.open(_root_dir() + rel, FileAccess.READ)
	if f == null:
		return ""
	var text := f.get_as_text()
	f.close()
	return text


func _first_match(text: String, pattern: String) -> String:
	var re := RegEx.new()
	re.compile(pattern)
	var m := re.search(text)
	return "" if m == null else m.get_string(1)


func _git(args: PackedStringArray) -> Array:
	## -> [exit_code, combined output]
	var out := []
	var code := OS.execute("git", args, out, true)
	var text := ""
	for chunk in out:
		text += str(chunk)
	return [code, text]


func _check_docs() -> Array[String]:
	## THE ANTI-ROT CHECK. Every place a version is written must agree with
	## every other place and with the newest git tag.
	##
	## This exists because the handoff docs went NINETEEN releases stale
	## without anything noticing — CLAUDE.md claimed v0.6.6 while the repo was
	## on v0.6.25 — and a fresh chat inherited that as fact. It also catches
	## the two other ways the handoff has actually broken: a doc naming a file
	## that does not exist (CLAUDE.md once pointed at a session temp folder
	## that gets deleted), and a renumbered tag sliding off its commit.
	var fails: Array[String] = []
	var root := _root_dir()

	# --- 0. the docs this check reads must actually be readable -----------
	# _read_doc() returns "" for a missing file, and "" matches no pattern.
	# So without this, DELETING a doc makes every check below scan nothing
	# and report nothing — a silent green. Same vacuous-pass class as the
	# door smoke test that stayed green for three releases without ever
	# touching a door.
	#
	# HONEST LIMIT — do not let a future session oversell this: it catches
	# GONE or EMPTY. It does not catch gutted (one byte passes) and it does
	# NOT catch stale, which is the failure this project has actually lived
	# through. Nothing here can tell you a sentence is false.
	var docs_required: Array[String] = ["CLAUDE.md", "TASKS.md", "HANDOFF.md",
		"CHANGELOG.md", "DESIGN.md", "README.md", "LORE.md",
		"scripts/main_menu.gd"]
	var text := {}
	var gone := {}
	for doc in docs_required:
		var body := _read_doc(doc)
		text[doc] = body
		if body.strip_edges() == "":
			gone[doc] = true
			fails.append("%s is missing or empty — this check reads it, and " % doc
				+ "an unreadable doc makes the checks below vacuous")

	# --- 1. what each source claims the current version is ----------------
	var claims := {}
	if not gone.has("CLAUDE.md"):
		claims["CLAUDE.md"] = _first_match(str(text["CLAUDE.md"]),
			"\\*\\*v(\\d+\\.\\d+\\.\\d+) shipped")
	if not gone.has("TASKS.md"):
		claims["TASKS.md"] = _first_match(str(text["TASKS.md"]),
			"Current version: v(\\d+\\.\\d+\\.\\d+)")
	if not gone.has("CHANGELOG.md"):
		claims["CHANGELOG.md"] = _first_match(str(text["CHANGELOG.md"]),
			"(?m)^## \\[(\\d+\\.\\d+\\.\\d+)\\]")
	if not gone.has("scripts/main_menu.gd"):
		claims["the in-game list"] = _first_match(str(text["scripts/main_menu.gd"]),
			"\\[\"v(\\d+\\.\\d+\\.\\d+)\"")
	# DESIGN.md is an OPTIONAL claim, and that is deliberate. It carried
	# v0.6.6 for nineteen releases precisely because nothing read it — but
	# making it a fifth MANDATORY source would add a fifth number to hand-bump
	# every release, which is how numbers go stale in the first place. So:
	# state no version there and this never fires; state one and it must agree
	# with everyone else. That turns re-adding a hardcoded version from silent
	# rot into an enforced claim. The anchor cannot cross a newline ([ \t]*,
	# not \s*) so reflowing the paragraph cannot make it fire.
	var design_claim := _first_match(str(text.get("DESIGN.md", "")),
		"Current project state:[ \\t]*\\*\\*v(\\d+\\.\\d+\\.\\d+)")
	if design_claim != "":
		claims["DESIGN.md"] = design_claim
	var newest_tag := ""
	if DirAccess.dir_exists_absolute(root + ".git"):
		var described := _git(PackedStringArray(
			["-C", root, "describe", "--tags", "--abbrev=0"]))
		if described[0] != 0:
			fails.append("git could not name the newest tag (exit %d)" % described[0])
		else:
			newest_tag = str(described[1]).strip_edges().trim_prefix("v")
			claims["the newest git tag"] = newest_tag

	var seen := {}
	for source in claims:
		var claimed := str(claims[source])
		if claimed == "":
			fails.append("no version found in %s — was that line reworded? "
				% source + "the check anchors on it")
			continue
		if not seen.has(claimed):
			seen[claimed] = []
		seen[claimed].append(source)
	if seen.size() > 1:
		var parts: Array[String] = []
		for value in seen:
			parts.append("v%s (%s)" % [value, ", ".join(seen[value])])
		fails.append("version disagreement — " + " vs ".join(parts))

	# --- 2. the renumbered tags still sit on their recorded commits -------
	var record_rel := "docs/version_renumber_2026-08-02/tag_commits.json"
	var record_text := _read_doc(record_rel)
	if record_text == "":
		fails.append("the renumber record is gone (%s) — it is the ONLY way "
			% record_rel + "to undo the 2026-08-02 renumbering")
	elif newest_tag != "":
		var record: Variant = JSON.parse_string(record_text)
		if typeof(record) != TYPE_DICTIONARY:
			fails.append("%s will not parse as json" % record_rel)
		else:
			var listed := _git(PackedStringArray(["-C", root, "show-ref", "--tags"]))
			var tag_at := {}
			for line in str(listed[1]).split("\n"):
				var bits := line.strip_edges().split(" ")
				if bits.size() == 2:
					tag_at[bits[1].trim_prefix("refs/tags/")] = bits[0]
			var wrong := 0
			var example := ""
			for old_name in record:
				var entry: Dictionary = record[old_name]
				var new_name := str(entry.get("new", ""))
				var sha := str(entry.get("sha", ""))
				if not tag_at.has(new_name):
					wrong += 1
					if example == "":
						example = "%s (was %s) has no tag" % [new_name, old_name]
				elif str(tag_at[new_name]) != sha:
					wrong += 1
					if example == "":
						example = "%s is on %s but the record says %s" % [
							new_name, str(tag_at[new_name]).substr(0, 7),
							sha.substr(0, 7)]
			if wrong > 0:
				fails.append("%d renumbered tag(s) moved off the commit the "
					% wrong + "record pins them to — e.g. %s" % example)

	# --- 3. every repo path the handoff docs name still exists ------------
	# the exact bug that shipped: CLAUDE.md pointed at the renumber undo-map
	# in a session temp folder, so a new chat found a dead reference to the
	# one artefact that can reverse the renumbering.
	#
	# SCOPE, stated honestly because CLAUDE.md used to overclaim this: it sees
	# only BACKTICKED references, and only two shapes — a repo path under one
	# of the six known dirs, or a bare root-level doc/config filename. It is
	# blind to BACKSLASH paths, so `python tools\gen_art.py` — the most-run
	# command in the docs — is NOT covered by this.
	#
	# CONVENTION this check imposes, and it is not "backticks mean it exists":
	# a path in one of those two shapes is checked. If you are naming a file
	# that is PLANNED (milestone-2 work in DESIGN.md/TASKS.md), or one that
	# lives outside the repo (user://, %APPDATA%), or one you are telling a
	# reader to DELETE, write it so it does not match — unbackticked, or
	# without the checked prefix. Several correct lines in these docs already
	# do exactly that; do not "fix" them into matching.
	# ALL SEVEN. CHANGELOG.md was excluded at first on the theory that a
	# changelog is frozen history and will name files that were later deleted.
	# Measured before believing it: CHANGELOG.md has 4 unique backticked refs
	# and ZERO dead ones, so the theory did not describe this repo. The
	# exclusion was also INCONSISTENT — HANDOFF.md is append-only history too
	# and has always been scanned. The real protection for a frozen entry is
	# the writing convention below (name a doomed file so it does not match),
	# not carving a hole in the check.
	var docs_with_paths: Array[String] = ["CLAUDE.md", "TASKS.md", "HANDOFF.md",
		"DESIGN.md", "README.md", "LORE.md", "CHANGELOG.md"]
	var path_re := RegEx.new()
	if path_re.compile("`((?:(?:scripts|tools|docs|art|assets|scenes)/[A-Za-z0-9_./-]+)"
			+ "|(?:[A-Za-z0-9_-]+\\.(?:md|bat|godot)))`") != OK:
		fails.append("the doc-path regex failed to COMPILE — this check has "
			+ "been silently inert, which is worse than absent")
	else:
		for doc in docs_with_paths:
			if gone.has(doc):
				continue
			for m in path_re.search_all(str(text[doc])):
				var named := m.get_string(1)
				var abs := root + named
				if FileAccess.file_exists(abs):
					continue
				if DirAccess.dir_exists_absolute(abs.trim_suffix("/")):
					continue
				fails.append("%s names `%s`, which does not exist" % [doc, named])

	# --- 4. every executable the docs tell you to RUN actually resolves ----
	# The bug this exists for: the two commands at the TOP of CLAUDE.md — the
	# first thing a migrating session is told to run — were `godot_console …`
	# for a long time, and that token resolves to nothing on this machine. No
	# alias, no shim, not on PATH. Both gates printed PASS the entire time,
	# because nothing here had ever checked that a documented command RUNS.
	#
	# Deliberately NOT done: resolving arbitrary command names. That needs a
	# PATH search, is platform-specific, and would fire on prose that quotes a
	# dead command on purpose (the docs do this in at least three places, to
	# record what used to be broken). Two narrow, robust rules instead.
	var exe_re := RegEx.new()
	if exe_re.compile("(?i)([A-Za-z]:[\\\\/][^\\s`\"'<>|]*\\.exe)") != OK:
		fails.append("the exe regex failed to COMPILE — check 4 was inert")
	else:
		for doc in docs_with_paths:
			if gone.has(doc):
				continue
			var body := str(text[doc])
			# 4a. an absolute .exe the doc names must exist on disk. This is
			# what catches an engine upgrade that leaves the docs behind.
			# The path is never hardcoded here on purpose — that would make
			# harness.gd a SEVENTH copy of a fact the docs already state six
			# times, and copies drift. Disk is the authority.
			var defined := false
			for m in exe_re.search_all(body):
				var exe := m.get_string(1)
				if FileAccess.file_exists(exe):
					defined = true
				else:
					fails.append("%s names the executable %s, which does not "
						% [doc, exe] + "exist — a documented command that "
						+ "cannot run is worse than no command")
			# 4b. the `godot_console` SHORTHAND must never be left orphaned.
			# It is not on PATH and never will be; it is only safe while the
			# doc also spells out the real path somewhere. Lose the definition
			# and every command in the file silently becomes unrunnable again.
			#
			# Fires on the COMMAND shape (`godot_console -…`) and NOT on a bare
			# prose mention — because the docs deliberately quote dead commands
			# to record what used to be broken, and HANDOFF.md does exactly
			# that. This check fired on that line on its first run; that was a
			# false positive, and a check that cries wolf is one a later
			# session quietly weakens. Narrowed here rather than exempting the
			# file, which would have made it lie instead.
			if _first_match(body, "(godot_console)\\s+-") != "" and not defined:
				fails.append("%s uses the godot_console shorthand but no " % doc
					+ "longer names a real exe path defining it — that "
					+ "shorthand resolves to NOTHING on this machine")

	# --- 5. HANDOFF.md must NAME the current release ----------------------
	# The chain is this project's memory, and CLAUDE.md's loudest process rule
	# is to write an entry BEFORE you push. That rule was broken the same day
	# it was written: v0.6.26 and v0.6.27 both shipped while the newest entry
	# still read "still v0.6.25 … tree clean at v0.6.25", and NOTHING noticed.
	# HANDOFF.md is read by parts 0 and 3, but neither reads it for a VERSION,
	# so a two-release gap sat behind a green gate for the next session to
	# inherit as current fact.
	#
	# HONEST LIMIT — do not oversell this: it proves the current version is
	# MENTIONED in the file, not that the entry is true, complete, or even
	# about that release. A session could satisfy it by typing the number.
	# It closes the gap that actually happened — shipping releases and never
	# touching the file at all — and nothing more. Prose stays unverifiable.
	var current := newest_tag
	if current == "" and not gone.has("CHANGELOG.md"):
		current = _first_match(str(text["CHANGELOG.md"]),
			"(?m)^## \\[(\\d+\\.\\d+\\.\\d+)\\]")
	if current != "" and not gone.has("HANDOFF.md"):
		if not str(text["HANDOFF.md"]).contains("v" + current):
			fails.append("HANDOFF.md never mentions v%s, the current " % current
				+ "release — the chain is the memory, and the entry is due "
				+ "BEFORE the push, not after it")
	return fails


# ---------------------------------------------------------------------------
# THE SECURITY AUDIT (--checksec, and it runs inside --smoke)
#
# These are INVARIANTS, not warnings. Each one is currently true of this repo,
# and each maps to a concrete way the project could be turned against the
# user — most sharply, code that quietly ships their data somewhere.
#
# MIXED, and the difference decides what this can promise. SEC_PY_IMPORTS
# and expected_autoloads are ALLOWLISTS: they fail CLOSED, so anything new
# is a red build until someone widens the list on purpose. SEC_REMOTE is a
# single expected value, same idea. But SEC_NET_GD, SEC_NET_PY,
# SEC_EXEC_PY, SEC_SECRET_NAMES and SEC_SECRET_CONTENT are DENYLISTS of
# named strings and they fail OPEN — a socket class, exec primitive or
# credential format nobody listed passes silently. This comment used to
# call every list below an allowlist, which overstated the guarantee.
#
# SECOND HOLE: _check_security returns an EMPTY failure list (i.e. prints
# SEC PASS having asserted nothing) when there is no .git at the project
# root — including check 6, which reads project.godot and needs no git.
#
# HONEST LIMITATION: the auditor cannot fully audit itself. harness.gd is
# skipped by the pattern scans because it necessarily contains the very
# strings it searches for. It gets its own narrower check instead (every
# OS.execute here must invoke git). A self-audit always has this hole; better
# to name it than to pretend otherwise.
# ---------------------------------------------------------------------------

const SEC_REMOTE := "https://github.com/SapphireSignal/spoils.git"

## stdlib + Pillow + this project's own tool modules. Nothing else has ever
## been imported; a new name here is a supply-chain decision, so it stops.
const SEC_PY_IMPORTS := [
	"json", "math", "pathlib", "random", "itertools", "collections",
	"functools", "typing", "dataclasses", "struct", "hashlib", "colorsys",
	"sys", "os", "re", "time", "copy", "textwrap", "argparse", "shutil",
	"PIL", "gen_font", "gen_art",
]

## anything that can open a socket. The game is single-player and offline;
## when multiplayer genuinely lands (DESIGN.md keeps the door open) this
## list gets edited on purpose, not discovered after the fact.
const SEC_NET_GD := [
	"HTTPRequest", "HTTPClient", "StreamPeerTCP", "StreamPeerTLS",
	"PacketPeerUDP", "WebSocketPeer", "ENetConnection", "ENetMultiplayerPeer",
	"UPNP", "IP.resolve_hostname",
]
const SEC_NET_PY := [
	"import socket", "import urllib", "from urllib", "import requests",
	"import http", "from http", "urlopen", "httpx", "aiohttp", "smtplib",
	"ftplib", "telnetlib", "import ssl",
]

## process execution and dynamic evaluation, in tools/. gen_art.py draws
## pixels; it has never needed to run a program or eval a string.
const SEC_EXEC_PY := [
	"subprocess", "os.system", "os.popen", "eval(", "exec(", "__import__",
	"pickle.loads", "marshal.loads",
]

## credential-shaped things that must never be tracked
const SEC_SECRET_NAMES := [
	".env", ".pem", "id_rsa", "id_dsa", "id_ecdsa", ".pfx", ".p12",
	".netrc", ".npmrc", "credentials.json", "secrets.json", ".keystore",
]
const SEC_SECRET_CONTENT := [
	"AKIA[0-9A-Z]{16}",                      # aws access key
	"ghp_[A-Za-z0-9]{36}",                   # github personal token
	"github_pat_[A-Za-z0-9_]{20,}",
	"xox[baprs]-[A-Za-z0-9-]{10,}",          # slack
	"-----BEGIN [A-Z ]*PRIVATE KEY-----",
	"AIza[0-9A-Za-z_-]{35}",                 # google api key
]


func _sec_tracked_files(root: String, suffixes: Array) -> Array[String]:
	## git's view of the repo is the right boundary for this: a secret that
	## is not tracked cannot be pushed, and a file git does not know about
	## cannot reach the remote.
	##
	## Returns Array[String], NOT Array — an untyped array hands back Variant
	## elements and every `var x := rel.something()` downstream fails to infer,
	## which is a PARSE error, which makes the autoload fail to load, which
	## looks exactly like a hang. (It did. See CLAUDE.md.)
	## --others --exclude-standard also catches files sitting in the working
	## tree that nobody has committed yet. Tracked-only would mean a freshly
	## written backdoor is invisible until it is already in a commit, which
	## is precisely too late.
	var listed := _git(PackedStringArray(
		["-C", root, "ls-files", "--cached", "--others", "--exclude-standard"]))
	var out: Array[String] = []
	if listed[0] != 0:
		return out
	for line in str(listed[1]).split("\n"):
		var rel := line.strip_edges()
		if rel == "":
			continue
		if suffixes.is_empty():
			out.append(rel)
			continue
		for suffix in suffixes:
			if rel.ends_with(suffix):
				out.append(rel)
				break
	return out


func _check_security() -> Array[String]:
	var fails: Array[String] = []
	var root := _root_dir()
	if not DirAccess.dir_exists_absolute(root + ".git"):
		return fails      # not a checkout; nothing to assert against

	# --- 1. the remote has not moved ------------------------------------
	# the cheapest possible guard against "push their work somewhere else".
	var remotes := _git(PackedStringArray(["-C", root, "remote", "-v"]))
	var reported := {}          # -v lists fetch AND push; report each once
	for line in str(remotes[1]).split("\n"):
		var row := line.strip_edges()
		if row == "":
			continue
		var parts := row.split("\t")
		if parts.size() < 2:
			continue
		var url := parts[1].split(" ")[0]
		if url == SEC_REMOTE or reported.has(parts[0]):
			continue
		reported[parts[0]] = true
		fails.append("git remote '%s' points at %s, expected %s"
			% [parts[0], url, SEC_REMOTE])

	# --- 2. no network capability anywhere in the project ----------------
	for rel in _sec_tracked_files(root, [".gd"]):
		if rel.ends_with("harness.gd"):
			continue                      # the auditor names its own patterns
		var body := _read_doc(rel)
		for needle in SEC_NET_GD:
			if body.contains(needle):
				fails.append("%s uses %s — this project makes NO network "
					% [rel, needle] + "calls; if that is changing, say so")
	for rel in _sec_tracked_files(root, [".py"]):
		var body := _read_doc(rel)
		for needle in SEC_NET_PY:
			if body.contains(needle):
				fails.append("%s uses '%s' — the tools are offline by design"
					% [rel, needle])
		for needle in SEC_EXEC_PY:
			if body.contains(needle):
				fails.append("%s uses '%s' — the art tools do not run "
					% [rel, needle] + "programs or evaluate strings")

	# --- 3. the python toolchain's imports are the ones we vetted --------
	# two patterns, not one clever one: "import a, b" and "from x import y"
	# parse differently, and a combined regex misfires on prose that happens
	# to begin with the word "from".
	var plain_re := RegEx.new()
	plain_re.compile("(?m)^[ \\t]*import[ \\t]+([A-Za-z_][A-Za-z0-9_., \\t]*)")
	var from_re := RegEx.new()
	from_re.compile("(?m)^[ \\t]*from[ \\t]+([A-Za-z_][A-Za-z0-9_.]*)[ \\t]+import[ \\t]")
	for rel in _sec_tracked_files(root, [".py"]):
		var body := _read_doc(rel)
		var modules: Array[String] = []
		for m in plain_re.search_all(body):
			for piece in m.get_string(1).split(","):
				modules.append(piece.strip_edges())
		for m in from_re.search_all(body):
			modules.append(m.get_string(1))
		for module in modules:
			var top := module.split(".")[0].split(" ")[0]     # drop "as x"
			if top == "":
				continue
			if not SEC_PY_IMPORTS.has(top):
				fails.append("%s imports '%s', which is not on the vetted "
					% [rel, top] + "list — new dependency, decide on purpose")

	# --- 4. shelling out is confined to the harness, and only to git -----
	for rel in _sec_tracked_files(root, [".gd"]):
		var body := _read_doc(rel)
		if rel.ends_with("harness.gd"):
			# narrower check for the one file exempt above: every execute
			# call here must be a git call.
			var exec_re := RegEx.new()
			exec_re.compile("OS\\.execute\\(\\s*\"([^\"]*)\"")
			for m in exec_re.search_all(body):
				if m.get_string(1) != "git":
					fails.append("harness.gd runs '%s' — only git is allowed"
						% m.get_string(1))
			continue
		for needle in ["OS.execute", "OS.create_process", "OS.shell_open"]:
			if body.contains(needle):
				fails.append("%s calls %s — running programs is confined "
					% [rel, needle] + "to harness.gd, and only git")

	# --- 5. nothing credential-shaped is tracked -------------------------
	for rel in _sec_tracked_files(root, []):
		var lower := rel.to_lower()
		for needle in SEC_SECRET_NAMES:
			if lower.ends_with(needle) or lower.get_file() == needle:
				fails.append("%s is tracked by git and looks like a "
					% rel + "credential file")
	# --- 6. the autoload list is exactly the eight we know about ---------
	# an autoload runs on EVERY launch before anything else. It is the
	# natural place to hide something persistent, and it is one line of
	# project.godot. CLAUDE.md documents these eight; this enforces them.
	var expected_autoloads := {
		"Authority": "*res://scripts/authority.gd",
		"Settings": "*res://scripts/settings.gd",
		"Sfx": "*res://scripts/sfx.gd",
		"Music": "*res://scripts/music.gd",
		"Ui": "*res://scripts/ui_state.gd",
		"Raid": "*res://scripts/raid.gd",
		"Juice": "*res://scripts/juice.gd",
		"Harness": "*res://scripts/harness.gd",
	}
	var in_section := false
	var found := {}
	for line in _read_doc("project.godot").split("\n"):
		var row := line.strip_edges()
		if row.begins_with("["):
			in_section = row == "[autoload]"
			continue
		if not in_section or row == "" or row.begins_with(";"):
			continue
		var eq := row.find("=")
		if eq < 0:
			continue
		found[row.substr(0, eq)] = row.substr(eq + 1).strip_edges().trim_prefix("\"").trim_suffix("\"")
	for name in found:
		if not expected_autoloads.has(name):
			fails.append("project.godot autoloads '%s' (%s), which is not "
				% [name, found[name]] + "one of the eight known autoloads")
		elif str(found[name]) != str(expected_autoloads[name]):
			fails.append("autoload %s points at %s, expected %s"
				% [name, found[name], expected_autoloads[name]])
	for name in expected_autoloads:
		if not found.has(name):
			fails.append("autoload %s is missing from project.godot" % name)

	var secret_res: Array[RegEx] = []
	for pattern in SEC_SECRET_CONTENT:
		var re := RegEx.new()
		re.compile(pattern)
		secret_res.append(re)
	for rel in _sec_tracked_files(root, [".gd", ".py", ".md", ".json", ".cfg",
			".tscn", ".bat", ".txt", ".gdshader"]):
		var body := _read_doc(rel)
		for i in secret_res.size():
			if secret_res[i].search(body) != null:
				fails.append("%s contains something shaped like a secret "
					% rel + "(pattern %d) — check before it is pushed" % i)
	return fails


func _check_claims() -> Array[String]:
	## THE NUMBERS GATE.
	##
	## `--checkdocs` proves a version agrees and a path exists. It cannot read
	## a SENTENCE, and CLAUDE.md says so plainly — "a check cannot verify
	## prose". That is true, and it is not the whole story, because the
	## sentences that have actually rotted on this project were overwhelmingly
	## NUMERIC. Every one of these was written down as fact and was false:
	##
	##   "~818 nodes" (1717)        "~34k nodes" (~8k)
	##   "~34 buildings" (15)       "a 20 min day" (18)
	##   "BARRIER_INSET 72" (66)    "3 rotating backdrops" (2)
	##   "clear 52%, the most common weather" (overcast, and 42%)
	##
	## A NUMBER IS CHECKABLE. This reads the claim out of the doc's own prose —
	## no duplicated copy that can drift from the sentence beside it — and
	## compares it against the value THE GAME ACTUALLY USES, read off the real
	## constant at runtime rather than regexed out of the source, so the code
	## side cannot be fooled by formatting or by a comment.
	##
	## IT FAILS CLOSED, deliberately. If a sentence is reworded so its number
	## no longer parses, that is a FAILURE and not a pass. The alternative is
	## the vacuous green this project has already been bitten by twice: the
	## door smoke test that stayed green for three releases without touching a
	## door, and `_read_doc` returning "" for a missing file so every pattern
	## below it matched nothing and reported nothing.
	var fails: Array[String] = []
	var claude := _read_doc("CLAUDE.md")
	if claude.strip_edges().is_empty():
		fails.append("CLAUDE.md is missing or empty — not one claim could be checked")
		return fails

	var claims := [
		{"what": "the day length in minutes",
			"re": "day/night tint \\(\\*\\*(\\d+) min\\*\\*",
			"is": EnvironmentSystem.DAY_SECONDS / 60.0},
		{"what": "DAY_SECONDS itself",
			"re": "`DAY_SECONDS` ([0-9.]+)",
			"is": EnvironmentSystem.DAY_SECONDS},
		{"what": "the barricade ring inset",
			"re": "BARRICADE RING at inset (\\d+)",
			"is": float(WorldBuilder.BARRIER_INSET)},
		{"what": "the planned map size in cells",
			"re": "(\\d+)×\\d+ planned map",
			"is": float(WorldBuilder.MAP_W)},
	]
	for c in claims:
		var found := _first_match(claude, str(c["re"]))
		if found.is_empty():
			fails.append(("CLAUDE.md no longer states %s in a form this check "
				+ "can read (pattern /%s/). Fix the sentence or fix the "
				+ "pattern — an unreadable claim FAILS, it never passes.")
				% [str(c["what"]), str(c["re"])])
			continue
		if absf(found.to_float() - float(c["is"])) > 0.001:
			fails.append("CLAUDE.md says %s is %s — the code says %s"
				% [str(c["what"]), found, str(c["is"])])

	# the district seed is a STRING, not a number, and it is the one value the
	# whole fixed-map promise rests on: change it and every quest address,
	# every screenshot and every remembered street moves.
	var seed_said := _first_match(claude, "DISTRICT_SEED = \"([a-z0-9-]+)\"")
	if seed_said.is_empty():
		fails.append("CLAUDE.md no longer states DISTRICT_SEED in a readable "
			+ "form (pattern /DISTRICT_SEED = \"...\"/)")
	elif seed_said != WorldBuilder.DISTRICT_SEED:
		fails.append("CLAUDE.md says the district seed is \"%s\" — the code says \"%s\""
			% [seed_said, WorldBuilder.DISTRICT_SEED])
	return fails


func _checkclaims() -> void:
	var fails := _check_claims()
	if fails.is_empty():
		print("CLAIMS PASS")
		get_tree().quit(0)
	else:
		for failure in fails:
			printerr("CLAIMS FAIL: " + failure)
		get_tree().quit(1)


func _checksec() -> void:
	var fails := _check_security()
	if fails.is_empty():
		print("SEC PASS")
		get_tree().quit(0)
	else:
		for failure in fails:
			printerr("SEC FAIL: " + failure)
		get_tree().quit(1)


func _checkdocs() -> void:
	var fails := _check_docs()
	if fails.is_empty():
		print("DOCS PASS")
		get_tree().quit(0)
	else:
		for failure in fails:
			printerr("DOCS FAIL: " + failure)
		get_tree().quit(1)


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
		if arg.begins_with("--door="):
			# --door=inside|outside: stand on that side of a door and open
			# it. The leaf must swing AWAY from wherever you are standing.
			var side := arg.trim_prefix("--door=")
			var d := get_tree().get_first_node_in_group("doors") as Door
			var pl2 := _find_player()
			if d != null and pl2 != null:
				var thru := d.doorway_through()
				var sign_in := 1.0 if side == "inside" else -1.0
				pl2.global_position = d.doorway_center() + thru * 22.0 * sign_in
				await get_tree().process_frame
				d.toggle(pl2.global_position)
				await get_tree().create_timer(0.45).timeout
				print("DOOR side=%s swings_out=%s open=%s"
					% [side, str(d.swings_out()), str(d.is_open())])
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
					var tiles: Array = reg["floor_tiles"] as Array
					var shown := 0
					for t in tiles:
						if (t as Node2D).visible:
							shown += 1
					print("UPSTAIRS idx=%d upstairs=%s lift=%.1f cells=%s"
						% [idx, str(pl.upstairs), pl.floor_lift,
							str(reg["cells"])])
					print("UPSTAIRS slab tiles=%d visible=%d props=%d"
						% [tiles.size(), shown,
							(reg["upper_props"] as Array).size()])
		if arg.begins_with("--map="):
			var wanted := arg.trim_prefix("--map=")
			# REJECT AN UNKNOWN MODE. `_set_mode` shows the world root only for
			# "world" and the transit root only for "transit", so ANY other
			# string hides both and the shot comes out as an empty panel with
			# no error anywhere — I lost a README screenshot to `--map=district`
			# before noticing. Same class as the modifier flags that used to
			# hang when passed alone: fail loudly, never produce a useless
			# capture.
			if wanted != "world" and wanted != "transit":
				push_error("--map=%s is not a mode; use world or transit" % wanted)
				print("HARNESS ERROR: --map=%s is not a mode (world|transit)"
					% wanted)
				get_tree().quit(1)
				return
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


func _perf_walk() -> void:
	## Frame pacing WHILE MOVING THROUGH UNVISITED GROUND.
	##
	## --perf holds a STATIC camera, so it can only ever measure a settled
	## view. That makes it structurally blind to a FIRST-USE cost - anything
	## paid the first time a thing is drawn - which is exactly what the user
	## reported: "i only see it while im walking and i only see it once, when
	## i try and walk back where i was to see if it happens again, it doesnt
	## happen". Every perf figure quoted before this was from a stationary
	## camera and could not have caught it.
	##
	## This sweeps the player across the district and reports the WORST FRAMES
	## WITH THE CELL THEY HAPPENED AT, so a hitch can be gone back to and
	## looked at rather than guessed about.
	await _ensure_game_scene()
	_apply_env_flags()
	var player := _find_player()
	if player == null:
		print("PERFWALK ERROR: no player")
		get_tree().quit(1)
		return
	# THE PLAYER FIGHTS THE SWEEP OTHERWISE. They spawn INSIDE the safehouse,
	# and player._process runs move_and_slide() every frame, which depenetrates
	# them straight back out of whatever this teleports them into - so the
	# first cut of this probe never left the spawn building and measured a
	# stationary camera all over again, which is the exact blind spot it exists
	# to remove. Collision off for the duration.
	for shape in player.find_children("*", "CollisionShape2D", true, false):
		(shape as CollisionShape2D).set_deferred("disabled", true)
	player.collision_mask = 0
	for i in 60:
		await get_tree().process_frame
	# a long diagonal sweep across the playable band, on the iso ground axis
	var dir := Vector2(2.0, 1.0).normalized()
	var speed := 420.0
	var samples: Array = []
	var frames := 0
	var t0 := Time.get_ticks_usec()
	var prev_us := t0
	while Time.get_ticks_usec() - t0 < 24_000_000:
		await get_tree().process_frame
		var now_us := Time.get_ticks_usec()
		var dt_ms := float(now_us - prev_us) / 1000.0
		prev_us = now_us
		frames += 1
		player.global_position += dir * speed * (dt_ms / 1000.0)
		samples.append([dt_ms, player.global_position.round()])
	var seconds := float(Time.get_ticks_usec() - t0) / 1_000_000.0
	samples.sort_custom(func(a, b): return float(a[0]) > float(b[0]))
	var over := 0
	for s in samples:
		if float(s[0]) > 8.34:            # a dropped frame at 120hz or worse
			over += 1
	print("PERFWALK frames=%d avg_fps=%.1f worst_ms=%.2f over8ms=%d nodes=%d" % [
		frames, frames / seconds, float(samples[0][0]), over,
		int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))])
	for i in mini(8, samples.size()):
		print("PERFWALK hitch %.2f ms at %s" % [
			float(samples[i][0]), str(samples[i][1])])
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


func _film(film_name: String) -> void:
	## Capture a SEQUENCE, not a frame — `--film=<name> [--scene=menu]
	## [--backdrop=N] [--film-seconds=N] [--film-fps=N]`. Frames land in
	## `shots/film_<name>/f000.png` and up; turn them into something watchable
	## with ffmpeg.
	##
	## WHY THIS EXISTS: the menu backdrops' living layers are MOTION, and a
	## still cannot show motion — not to the user and not to whoever is
	## building them. Every judgement about whether a scene "reads as alive"
	## made off a single frame is a guess. (It is also the frame-capture half
	## of the parked trailer work, which needs exactly this.)
	##
	## Deliberately simple: it does the menu/backdrop setup only. A raid film
	## would need the whole --shot flag surface and nothing needs it yet.
	var seconds := 4.0
	var fps := 12.0
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--film-seconds="):
			seconds = maxf(0.5, float(arg.trim_prefix("--film-seconds=")))
		elif arg.begins_with("--film-fps="):
			fps = clampf(float(arg.trim_prefix("--film-fps=")), 2.0, 60.0)
	if _shot_scene != "menu":
		await _ensure_game_scene()
	for i in 8:
		await get_tree().process_frame
	if _shot_backdrop >= 0:
		var main_menu := get_tree().get_first_node_in_group("main_menu")
		if main_menu != null:
			main_menu.call("show_backdrop", _shot_backdrop)
	_apply_env_flags()
	for i in 6:
		await get_tree().process_frame
	var dir := ProjectSettings.globalize_path("res://shots").path_join(
		"film_" + film_name)
	DirAccess.make_dir_recursive_absolute(dir)
	# clear any earlier take, or ffmpeg silently splices two runs together
	var old := DirAccess.open(dir)
	if old != null:
		for stale in old.get_files():
			if stale.ends_with(".png"):
				DirAccess.remove_absolute(dir.path_join(stale))
	var total := int(seconds * fps)
	for i in total:
		await get_tree().create_timer(1.0 / fps).timeout
		var frame := get_viewport().get_texture().get_image()
		frame.save_png(dir.path_join("f%03d.png" % i))
	print("FILM SAVED: %d frames at %.0f fps -> %s" % [total, fps, dir])
	get_tree().quit()


func _probe_sort() -> void:
	## DOES THE PLAYER'S SORT KEY EVER DISAGREE WITH WHERE IT IS DRAWN?
	##
	## Filming for a rare pop is impractical: at real walking speed 1400 frames
	## covers ~560 px, so catching something rare needs ~10k frames and hours.
	## But the suspected cause makes an EXACT prediction, and predictions can be
	## tested directly.
	##
	## player.gd keeps `global_position` continuous and draws the sprite at
	## `snapped_pos` (rule 1 - the sprite parks on the screen-pixel grid), while
	## y-sorting sorts on the NODE's y. So for any neighbour at height `oy`
	## there can be frames where
	##     sign(node_y - oy) != sign(drawn_y - oy)
	## i.e. the player SORTS in front while being DRAWN behind, or the reverse.
	## Every such frame is a frame rendered in the wrong order. Counting them
	## settles the theory without a camera.
	await _ensure_game_scene()
	_apply_env_flags()
	var player := _find_player()
	if player == null:
		print("SORT ERROR: no player")
		get_tree().quit(1)
		return
	var ysort := get_tree().current_scene.get_node_or_null("World/YSort")
	if ysort == null:
		for n in get_tree().current_scene.find_children("*", "Node2D", true, false):
			if n.y_sort_enabled and n.get_child_count() > 50:
				ysort = n
				break
	if ysort == null:
		print("SORT ERROR: no y-sorted parent found")
		get_tree().quit(1)
		return
	for shape in player.find_children("*", "CollisionShape2D", true, false):
		(shape as CollisionShape2D).set_deferred("disabled", true)
	player.collision_mask = 0
	for i in 30:
		await get_tree().process_frame
	var start_pos := player.global_position
	var heading := Vector2(1.0, 1.0).normalized()
	var step := 0.37
	var disagreements := 0
	var checked := 0
	var worst := 0.0
	var samples := 4000
	for i in samples:
		# DRIVE THE AUTHORITATIVE POSITION. player.gd restores `_true_pos` onto
		# global_position every frame before moving, so a probe that only writes
		# global_position is silently overwritten and the player never moves -
		# which reads as a flawless zero here. It did, once.
		# ACCUMULATE ON THE TRUE POSITION. Adding to global_position instead
		# adds to the SNAPPED value, which the next frame rounds straight back -
		# a 0.26 px step off a whole-pixel base never escapes the rounding, so
		# the player sits still while every counter looks healthy. That is how
		# this probe reported a flawless zero twice.
		var tp: Vector2 = player.get("_true_pos")
		player.set("_true_pos", tp + heading * step)
		await get_tree().process_frame
		var s := float(maxi(1, Settings.pixel_scale))
		var c := s if player.zoom_combined == 0 else float(player.zoom_combined)
		var node_y := player.global_position.y
		var drawn_y := (player.global_position * c).round().y / c
		worst = maxf(worst, absf(drawn_y - node_y))
		# only neighbours close enough to overlap the player on screen matter
		for child in ysort.get_children():
			var o := child as Node2D
			if o == null or o == player:
				continue
			if absf(o.global_position.x - player.global_position.x) > 48.0:
				continue
			var oy := o.global_position.y
			if absf(oy - node_y) > 3.0:
				continue
			checked += 1
			var a := node_y - oy
			var b := drawn_y - oy
			if (a > 0.0) != (b > 0.0):
				disagreements += 1
	# ALWAYS REPORT THE TRAVEL. A probe that silently stops moving reports a
	# perfect score, and this one did exactly that once.
	var travelled := player.global_position.distance_to(start_pos)
	print("SORT frames=%d travelled=%.1f px near_pairs=%d disagreements=%d max_offset=%.4f px" % [
		samples, travelled, checked, disagreements, worst])
	get_tree().quit(0)


func _film_walk(film_name: String) -> void:
	## EVERY RENDERED FRAME while the player creeps forward, for hunting a
	## ONE-FRAME visual pop (user: "random stuff glitch for like a milisecond",
	## "on a wall on a house", "things next to my character").
	##
	## Why not --film: it samples on a timer, so at 12 fps a one-frame artefact
	## is invisible about 95% of the time. This captures consecutively.
	##
	## Why a FIXED STEP and not a speed: saving a PNG per frame makes delta
	## enormous, so a delta-scaled walk would teleport metres per frame and
	## every pair of frames would differ wildly - the diff would be all signal
	## and no baseline. A fixed 0.25 px keeps consecutive frames nearly
	## identical, which is what makes a pop stand out, AND it sweeps the
	## sub-pixel phase finely, which is where the suspected sort flip lives.
	##
	## Direction is +x+y: in this projection screen y = (x + y) * 16, so this
	## walks straight DOWN the screen and crosses the y-sort line of anything
	## it passes - which is the event under test.
	await _ensure_game_scene()
	_apply_env_flags()
	var player := _find_player()
	if player == null:
		print("FILMWALK ERROR: no player")
		get_tree().quit(1)
		return
	# COLLISION STAYS ON BY DEFAULT, and that is a correction. The first cut
	# disabled it (copying --perf-walk, where it is right) and the player
	# walked straight THROUGH a house - so the roof-reveal fired, the roof
	# faded, and the frame diff dutifully flagged it as the biggest artefact in
	# the run. It was correct behaviour caused by the probe itself. A test that
	# creates the thing it is looking for is worse than no test.
	#
	# Pass --film-noclip only when sweeping open ground, and use --at= to start
	# somewhere the player can actually walk.
	if "--film-noclip" in OS.get_cmdline_user_args():
		for shape in player.find_children("*", "CollisionShape2D", true, false):
			(shape as CollisionShape2D).set_deferred("disabled", true)
		player.collision_mask = 0
	var frames := 240
	var step := 0.25
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--film-frames="):
			frames = clampi(int(arg.trim_prefix("--film-frames=")), 8, 2000)
		elif arg.begins_with("--film-step="):
			step = clampf(float(arg.trim_prefix("--film-step=")), 0.02, 8.0)
	for i in 30:
		await get_tree().process_frame
	var dir_path := ProjectSettings.globalize_path("res://shots").path_join(
		"film_" + film_name)
	DirAccess.make_dir_recursive_absolute(dir_path)
	var old_dir := DirAccess.open(dir_path)
	if old_dir != null:
		for stale in old_dir.get_files():
			if stale.ends_with(".png"):
				DirAccess.remove_absolute(dir_path.path_join(stale))
	var heading := Vector2(1.0, 1.0).normalized()
	var solid := not ("--film-noclip" in OS.get_cmdline_user_args())
	# CAPTURE AT NATIVE RESOLUTION. The game renders 560x360 and integer-scales
	# it up, so dividing the grab back down by that factor with NEAREST is
	# lossless - it recovers the exact pixels the game drew. It also cuts the
	# file to a ninth, which is what makes a thousand-frame sweep possible at
	# all, and makes the diff ~9x cheaper.
	var shrink := maxi(1, Settings.pixel_scale)
	# The camera's own position per frame, so the diff can align on the EXACT
	# integer scroll instead of searching for it. Searching a +/-3 window cost
	# 49 full-image compares per frame and was the reason the first analysis
	# had to be killed at ten minutes.
	var cam_log := PackedStringArray()
	var cam := player.get_node_or_null("Camera2D") as Camera2D
	var stuck := 0
	for i in frames:
		if solid:
			# move_and_collide respects walls and is frame-rate independent, so
			# the sweep walks the world the way the player really does
			var hit := player.move_and_collide(heading * step)
			if hit != null:
				# WANDER instead of grinding into the wall. A long sweep that
				# stalls on the first building measures one static view for a
				# thousand frames - the exact failure --perf-walk already had.
				stuck += 1
				heading = heading.rotated(deg_to_rad(90.0 if stuck % 2 == 0 else -90.0))
		else:
			player.global_position += heading * step
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		if shrink > 1:
			img.resize(int(img.get_width() / shrink), int(img.get_height() / shrink),
				Image.INTERPOLATE_NEAREST)
		img.save_png(dir_path.path_join("f%04d.png" % i))
		var cp := cam.global_position if cam != null else player.global_position
		cam_log.append("%d %.4f %.4f" % [i, cp.x, cp.y])
	var log_file := FileAccess.open(dir_path.path_join("camera.txt"),
		FileAccess.WRITE)
	if log_file != null:
		log_file.store_string("
".join(cam_log))
		log_file.close()
	print("FILMWALK SAVED: %d frames step=%.2f turns=%d -> %s" % [
		frames, step, stuck, dir_path])
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
	# v0.3.1 places: zone block rects (cell coords) + the interactables
	var zones: Dictionary = info.get("zones", {})
	for zone_name in zones:
		print("ZONE %s blocks=%s" % [zone_name, zones[zone_name]])
	var poi: Dictionary = info.get("poi", {})
	for poi_name in poi:
		print("POI %s=%s" % [poi_name, poi[poi_name]])
	# roads carry [x, width, span_from, span_to] — a road that stops short
	# has a span narrower than the playable band (v0.5.4)
	var vec: Dictionary = info.get("map_vec", {})
	print("ROADS_V %s" % [vec.get("roads_v", [])])
	print("ROADS_H %s" % [vec.get("roads_h", [])])
	var wb_stats: Dictionary = info.get("fringe_stats", {})
	print("FRINGE %s" % str(wb_stats))
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
		if (reg["floor_tiles"] as Array).is_empty():
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
