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
var _last_roof_upper := -2   # the floor that cell test was last answered for
var _respawning := false
var _debrief_open := false     # one debrief per raid, whichever path gets there
var _prompt: Label
var _prompt_target: Node2D
var _prompt_open := false
var _prompt_upper := -1     # which floor the cached prompt text was built for
var _uppers: Array = []
var _environment: EnvironmentSystem
var _grade_layer: CanvasLayer
var _grade_mat: ShaderMaterial
var _shaft_mat: ShaderMaterial
var _shaft_now := 0.0           # eased, so a doorway fades the light out
var _indoors_now := false       # roof over your head: kills the shafts
var _grade_night := -1.0        # last value pushed; the grade only updates
                                # when the cycle actually moves it
var _player_upper := -1        # index into _uppers while on a second story
var _car_hint: RichTextLabel
var _car_hint_until := 0.0
var _was_driving := false
var _extract_screen: ExtractScreen
var _death_screen: DeathScreen
var _toll_dialog: TollDialog


func _enter_tree() -> void:
	add_to_group("hud")   # the window stack takes the world's labels down


func _ready() -> void:
	# The window stack lives in an AUTOLOAD, so it outlives the scene that
	# pushed to it. Quitting to the menu with the pause menu (or the map)
	# open left the stack occupied forever: the next raid read no input at
	# all, and ESC and M were both dead, so there was no way out of it.
	# Every scene root now starts from an empty stack.
	Ui.clear()
	# Juice is an autoload too, so a raid that ended mid hit-stop would hand
	# the next one a world running at 4% speed
	Juice.reset()
	_show_deploy_screen()
	_build_world.call_deferred()


func _exit_tree() -> void:
	# world audio is driven from THIS scene every frame; without the scene
	# nothing winds it down, so the engine bed and the rain wash kept
	# playing under the main menu (and into the next raid)
	Sfx.silence_world()
	Ui.clear()
	Juice.reset()


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
	Music.stop_menu()  # the theme fades under the deploy screen
	# let the deploy screen actually render before the heavy lifting
	await get_tree().process_frame
	await get_tree().process_frame
	# aim a temporary camera at the MAP CENTRE during the build, so tile
	# chunks and sprites render — and warm up — behind the deploy screen
	# rather than on the first visible frame. It has to be a fixed point:
	# this runs before builder.build() is awaited, so _spawn_cell does not
	# exist yet. NOTE it is therefore NOT what the player first sees — the
	# spawn is inside the safehouse in the north-east corner, ~3200 px
	# east of here. (This said "the spawn crossroads": there is no
	# crossroads spawn any more, and this was never aimed at the spawn.)
	var warm_cam := Camera2D.new()
	add_child(warm_cam)
	warm_cam.global_position = Vector2(0.0, WorldBuilder.MAP_H * 16.0)
	warm_cam.make_current()
	# render every light type once behind the deploy screen: the FIRST frame
	# a 2D light (or canvas modulate) draws, the GPU pipeline for it compiles
	# — that stall must happen here, covered, not mid-raid
	var warm_fx := Node2D.new()
	warm_fx.position = warm_cam.global_position
	var warm_radial := PointLight2D.new()
	warm_radial.texture = load("res://art/gen/light_radial.png")
	warm_radial.energy = 0.4
	warm_fx.add_child(warm_radial)
	var warm_cone := PointLight2D.new()
	warm_cone.texture = load("res://art/gen/light_cone.png")
	warm_cone.energy = 0.4
	warm_cone.position = Vector2(24, 0)
	warm_fx.add_child(warm_cone)
	var warm_mod := CanvasModulate.new()
	warm_mod.color = Color(0.999, 0.999, 0.999)
	warm_fx.add_child(warm_mod)
	add_child(warm_fx)
	await _prewarm_textures()
	var builder := WorldBuilder.new()
	var info: Dictionary = await builder.build(self, Harness.world_seed)
	_floor_layer = info["floor"]
	_roofs = info["roofs"]
	var ysort: Node2D = info["ysort"]
	warm_fx.queue_free()  # before the environment adds its own modulate
	_player = Authority.spawn_player(ysort, info["spawn"])
	_player.died.connect(_on_player_died)
	warm_cam.queue_free()  # the player camera takes over
	await get_tree().process_frame

	# the tail is spread over frames too: environment pools, the edge guard,
	# and the whole pause-menu UI each land on their own frame instead of
	# stacking ~1000 node instantiations into one
	var environment := EnvironmentSystem.new()
	_environment = environment       # the screen grade reads the clock off it
	add_child(environment)
	await environment.setup(self, _floor_layer, info["puddle_spots"], _roofs,
		info["fog_spots"], info["leaf_trees"],
		info.get("leaf_trees_red", PackedVector2Array()),
		info.get("leaf_trees_needle", PackedVector2Array()))
	# dust in the air, riding the camera: one emitter, not one per lamp
	var motes := Motes.new()
	motes.name = "Motes"
	ysort.add_child(motes)
	motes.setup(_player)

	# NO WorldEnvironment GLOW HERE, and it is not an oversight — see the
	# measurement recorded in TASKS.md. Godot's 2D glow does nothing at all
	# unless rendering/viewport/hdr_2d is on, and turning that on re-renders
	# the canvas in linear space: the whole tuned night went near-black and
	# the frame rate fell 240 -> 183. Without it the glow pass is a literal
	# no-op (two shots came out byte-identical). Bright things bleed via
	# ADDITIVE GLOW SPRITES instead, which cost nothing and cannot smear the
	# pixel grid.

	# SUN SHAFTS, under the grade so the grade treats them as part of the
	# picture rather than paint on top of it
	var shaft_layer := CanvasLayer.new()
	shaft_layer.layer = 23
	var shafts := ColorRect.new()
	shafts.set_anchors_preset(Control.PRESET_FULL_RECT)
	shafts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shaft_mat = ShaderMaterial.new()
	_shaft_mat.shader = load("res://scripts/sunshafts.gdshader")
	shafts.material = _shaft_mat
	shaft_layer.add_child(shafts)
	add_child(shaft_layer)

	# SCREEN GRADE: contrast, split-tone, a highlight lift and a vignette,
	# in one pass over the finished frame. Engine-side, so it lifts every
	# sprite at once and the art on disk is untouched (user's direction).
	# Sits UNDER the dither film on purpose — the film's whole job is to
	# break up smooth ramps, and the grade makes new ones.
	_grade_layer = CanvasLayer.new()
	_grade_layer.layer = 24
	var grade := ColorRect.new()
	grade.set_anchors_preset(Control.PRESET_FULL_RECT)
	grade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_grade_mat = ShaderMaterial.new()
	_grade_mat.shader = load("res://scripts/grade.gdshader")
	grade.material = _grade_mat
	_grade_layer.add_child(grade)
	add_child(_grade_layer)

	# anti-banding film: breaks the day-cycle's uniform 8-bit tint steps into
	# per-pixel grain (a slow full-screen fade otherwise visibly "clicks")
	var dither_layer := CanvasLayer.new()
	dither_layer.layer = 25
	var film := TextureRect.new()
	film.texture = load("res://art/gen/dither.png")
	film.stretch_mode = TextureRect.STRETCH_TILE
	film.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	film.set_anchors_preset(Control.PRESET_FULL_RECT)
	film.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dither_layer.add_child(film)
	add_child(dither_layer)
	await get_tree().process_frame

	var guard := EdgeGuard.new()
	guard.name = "EdgeGuard"
	add_child(guard)
	guard.setup(_player, self, info["map_center"], info["barrier_f"])
	var alarms := CarAlarms.new()
	alarms.name = "CarAlarms"
	add_child(alarms)
	for entry in (info["alarm_cars"] as Array):
		alarms.register(entry["node"] as Node2D, entry["lights"] as Array)
	alarms.setup(_player)
	var foliage := Foliage.new()
	foliage.name = "Foliage"
	add_child(foliage)
	for bush in (info["bushes"] as Array):
		foliage.register(bush as Node2D)
	foliage.setup(_player)
	_uppers = info.get("uppers", [])
	for i in _uppers.size():
		((_uppers[i] as Dictionary)["stairs_node"] as Stairs).used.connect(
			_on_stairs_used.bind(i))
	_player.setup_surfaces(_floor_layer, _surface_kinds_from(info["floor_coords"]))
	# (zoom never widens past the native view, so no edge camera-guard needed)
	_build_prompt()
	await get_tree().process_frame

	var map_view := MapView.new()
	map_view.name = "MapView"
	add_child(map_view)
	map_view.setup(info, _player, environment, _floor_layer)
	await map_view.prewarm()   # first-open draw cost, paid behind the curtain
	add_child(PauseMenu.new())

	# the ways out, and the screen you get when you take one
	_extract_screen = ExtractScreen.new()
	_extract_screen.name = "ExtractScreen"
	add_child(_extract_screen)
	# ...and the bill if you don't make it out, walking away included
	_death_screen = DeathScreen.new()
	_death_screen.name = "DeathScreen"
	_death_screen.visible = false
	add_child(_death_screen)
	var extraction := Extraction.new()
	extraction.name = "Extraction"
	add_child(extraction)
	extraction.setup(_player)
	for zone in (info.get("extracts", []) as Array):
		var z: Dictionary = zone
		extraction.register(str(z["name"]), z["pos"] as Vector2,
			float(z["radius"]), str(z["kind"]), bool(z["auto"]))
		if str(z["kind"]) == "lift":
			var beacon := LzBeacon.new()
			beacon.position = z["pos"] as Vector2
			ysort.add_child(beacon)
	extraction.extracted.connect(_on_extracted)
	# mara on the radio — reusable; the M2 walk-in is entirely her voice
	var radio := Radio.new()
	radio.name = "Radio"
	add_child(radio)
	# the night freight: arrives at in-game MIDNIGHT, 3 nights in 7, one
	# real minute in the yard. (This said "five minutes away" — a real-time
	# cycle the user replaced with the clock on 2026-08-01. The earliest a
	# raid can see her is ~12.6 real minutes in, and only on a night she
	# runs at all; night_freight.gd's own header already said so.)
	var freight := NightFreight.new()
	freight.name = "NightFreight"
	ysort.add_child(freight)
	freight.setup(info["freight_stop"] as Vector2, _player, radio,
		info["manifest"] as Dictionary, environment)
	freight.extracted.connect(_on_extracted)
	# the warden's crossing: his window, and what paying him buys
	var toll: TollGate = info.get("toll_gate", null)
	if toll != null:
		_toll_dialog = TollDialog.new()
		_toll_dialog.name = "TollDialog"
		add_child(_toll_dialog)
		toll.wants_dialog.connect(_toll_dialog.open)
		_toll_dialog.paid.connect(func() -> void:
			toll.open_barrier()
			extraction.arm("toll")
			var edge := get_node_or_null("EdgeGuard") as EdgeGuard
			if edge != null:
				edge.stood_down = true)
	Raid.begin()
	await get_tree().process_frame
	Music.play_raid()  # sparse ambient with long silences, -26 dB
	world_info = info  # publish LAST: the harness polls this to detect readiness

	var tween := create_tween()
	tween.tween_property(_deploy_screen, "modulate:a", 0.0, 0.4)
	tween.tween_callback(func() -> void:
		_deploy_screen.get_parent().queue_free()
		_deploy_screen = null)


func _prewarm_textures() -> void:
	## Touch every generated texture while the deploy screen covers the game.
	##
	## THIS USED TO ONLY CALL `load()` AND THROW THE RESULT AWAY, with a comment
	## claiming that did "decode + GPU upload". Loading populates the resource
	## cache; **the upload to the GPU happens the first time a texture is
	## actually DRAWN**. So the cost this function exists to pay was still being
	## paid during play - once per texture, the first time an object carrying it
	## came on screen, and never again. That is exactly what the user described:
	## "it just appears on my screen ... like it loads on my screen weirdly, but
	## once its loaded then its fine", "only happens on one thing per time, then
	## it wont happen again on that object".
	##
	## So it draws them now, one pixel each, behind the deploy screen. Batched
	## across frames on the same time budget as the builder, because the deploy
	## has to hold the refresh rate.
	var dir := DirAccess.open("res://art/gen")
	if dir == null:
		return
	var texes: Array[Texture2D] = []
	var deadline := Time.get_ticks_usec() + 2400
	for file in dir.get_files():
		if file.ends_with(".png"):
			var tex := load("res://art/gen/" + file) as Texture2D
			if tex != null:
				texes.append(tex)
			if Time.get_ticks_usec() >= deadline:
				await get_tree().process_frame
				deadline = Time.get_ticks_usec() + 2400
	if texes.is_empty():
		return
	# HEADLESS HAS NO GPU AND NEVER DRAWS, so there is nothing to upload - and
	# `RenderingServer.frame_post_draw` never fires there, which hung the whole
	# deploy forever. --smoke caught it as "world never became ready (30s)".
	if DisplayServer.get_name() == "headless":
		return
	# a throwaway canvas that draws a 1 px sliver of each texture. One pixel is
	# enough: the upload is per RESOURCE, not per area drawn.
	var warm := Control.new()
	var first := 0
	var last := 0
	warm.name = "TexturePrewarm"
	warm.mouse_filter = Control.MOUSE_FILTER_IGNORE
	warm.modulate = Color(1, 1, 1, 0.004)   # present, but invisible over the
											# deploy screen
	warm.draw.connect(func() -> void:
		for i in range(first, last):
			warm.draw_texture_rect(texes[i],
				Rect2(Vector2(float(i % 64), float(i / 64)), Vector2.ONE), false))
	add_child(warm)
	const PER_FRAME := 48
	while first < texes.size():
		last = mini(first + PER_FRAME, texes.size())
		warm.queue_redraw()
		await get_tree().process_frame
		await get_tree().process_frame
		first = last
	warm.queue_free()


func _surface_kinds_from(floor_coords: Dictionary) -> Dictionary:
	# tile atlas coords -> footstep surface, derived from tile names
	var kinds: Dictionary = {}
	for tile_name in floor_coords:
		var tc: Array = floor_coords[tile_name]
		var name_str := str(tile_name)
		var kind := "concrete"
		if name_str.begins_with("asphalt"):
			kind = "asphalt"
		elif name_str.begins_with("wood"):
			kind = "wood"
		elif name_str.begins_with("forest") or name_str.begins_with("grass"):
			kind = "grass"
		elif name_str.begins_with("dirt"):
			kind = "dirt"
		kinds[Vector2i(int(tc[0]), int(tc[1]))] = kind
	return kinds


func _build_prompt() -> void:
	# floats in screen space but PINNED to the thing it belongs to
	var layer := CanvasLayer.new()
	layer.layer = 70
	_prompt = Label.new()
	_prompt.theme = UITheme.get_theme()
	_prompt.add_theme_color_override("font_color", UITheme.TEXT)
	_prompt.visible = false
	layer.add_child(_prompt)
	# the driving crash course — the KEYS pop amber against dim text and
	# the card hangs around longer (user: "make the buttons distinct from
	# the description... last a bit longer")
	_car_hint = RichTextLabel.new()
	_car_hint.theme = UITheme.get_theme()
	_car_hint.bbcode_enabled = true
	_car_hint.fit_content = true
	_car_hint.scroll_active = false
	_car_hint.autowrap_mode = TextServer.AUTOWRAP_OFF
	_car_hint.custom_minimum_size = Vector2(460, 0)
	_car_hint.text = "[center][color=#de9e41]w a s d[/color] [color=#819796]drive[/color]     [color=#de9e41]e[/color] [color=#819796]lights[/color]     [color=#de9e41]f[/color] [color=#819796]step out[/color][/center]"
	_car_hint.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_car_hint.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_car_hint.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_car_hint.offset_bottom = -26
	_car_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_car_hint.visible = false
	layer.add_child(_car_hint)
	add_child(layer)


func _on_stairs_used(index: int) -> void:
	# the floor switch: hide the room you left, show the one you're in.
	# No teleport — you flip beside the flight and the lift does the rest.
	if _player_upper == index:
		_set_upper_state(index, false)
		_player_upper = -1
		_player.floor_lift = 0.0
		_player.upstairs = false
		_block_ground_doors(index, false)
	elif _player_upper == -1:
		_set_upper_state(index, true)
		_player_upper = index
		# `wall_h`, not `story_h` — the player has to rise by the height of the
		# storey they are now standing ON TOP OF, which is the same lift the
		# slab and its furniture take. See _build_upper: story_h is what the
		# storey ABOVE adds, and using it left everything upstairs 8 px low.
		_player.floor_lift = float(world_info.get("wall_h", 40))
		_player.upstairs = true
		_block_ground_doors(index, true)


func _block_ground_doors(index: int, blocked: bool) -> void:
	## Seal this building's ground doorways while the player is upstairs.
	##
	## COLLISION ONLY — the door keeps its state, its frame and its silence.
	## It used to be slammed shut behind the climber, and the user rejected
	## that: "when going up the stiars to a second floor, the main door
	## entrance closes automatically, it should stay open".
	##
	## The guard itself has to stay. `_build_upper` lays floor tiles and
	## nothing else, so the upper room reuses the GROUND SHELL for collision —
	## an open doorway really is a hole at storey height, and someone walked
	## out of one.
	if index < 0 or index >= _uppers.size():
		return
	var cells: Rect2i = (_uppers[index] as Dictionary)["cells"]
	for node in get_tree().get_nodes_in_group("doors"):
		var door := node as Door
		var door_cell := _floor_layer.local_to_map(door.wall_position())
		if cells.grow(2).has_point(door_cell):
			door.set_floor_blocked(blocked)


func _set_upper_state(index: int, up: bool) -> void:
	## Show the room you're on, hide the one you left. The floor is a list
	## of individually y-sorted tiles, not one slab — see _build_upper for
	## why. No z_index anywhere: a z band puts the floor in front of ALL
	## walls, which made it clip over the top of the house.
	var upper: Dictionary = _uppers[index]
	# COLLISION AND THE STAIRS SWITCH AT ONCE; only the ART crossfades. What
	# you can walk into must never wait on an animation.
	for node in (upper["upper_props"] as Array):
		if node is StaticBody2D:
			(node as StaticBody2D).collision_layer = 1 if up else 0
	for node in (upper["ground_props"] as Array):
		if node is StaticBody2D:
			(node as StaticBody2D).collision_layer = 0 if up else 1
	# the slab is a complete floor, so the flight below it is out of sight
	# while you are standing on it — art AND collider, see Stairs.set_covered
	for node in get_tree().get_nodes_in_group("stairs"):
		var flight := node as Stairs
		if flight.upper_index == index:
			flight.set_covered(up)
	_fade_floor(upper, up)


func _fade_floor(upper: Dictionary, up: bool) -> void:
	## Cross-fade the two floors instead of cutting between them. A whole
	## storey appearing in one frame reads as a glitch — the same reason the
	## roof fades rather than popping (user: "the second floor just dissapears
	## instantly, it should fade out and back in like the roof, as well as when
	## you go up the stairs").
	##
	## Same 0.28 s EASE_IN_OUT quad as RoofReveal, deliberately: a climb fades
	## the roof and the floors together, and two different curves on the same
	## action would read as two separate events.
	var old: Variant = upper.get("fade_tween")
	if old is Tween and (old as Tween).is_valid():
		(old as Tween).kill()
	var rising: Array = []
	rising.append_array(upper["floor_tiles"] as Array)
	rising.append_array(upper["upper_props"] as Array)
	var falling: Array = upper["ground_props"] as Array
	# everything on screen for the duration; visibility settles at the end
	for n in rising:
		(n as Node2D).visible = true
		(n as Node2D).modulate.a = 0.0 if up else 1.0
	for n in falling:
		(n as Node2D).visible = true
		(n as Node2D).modulate.a = 1.0 if up else 0.0
	var tw := create_tween()
	tw.tween_method(
		func(a: float) -> void:
			for n in rising:
				(n as Node2D).modulate.a = a
			for n in falling:
				(n as Node2D).modulate.a = 1.0 - a,
		0.0 if up else 1.0, 1.0 if up else 0.0, 0.28) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	tw.tween_callback(func() -> void:
		for n in rising:
			(n as Node2D).visible = up
			(n as Node2D).modulate.a = 1.0
		for n in falling:
			(n as Node2D).visible = not up
			(n as Node2D).modulate.a = 1.0)
	upper["fade_tween"] = tw


func set_hud_hidden(hidden: bool) -> void:
	## called by the window stack (group "hud"): a menu is up, so the
	## world's own labels come down. Works while the tree is PAUSED, which
	## is the whole point — _process isn't running to do it itself.
	if hidden:
		if _prompt != null:
			_prompt.visible = false
			_prompt_target = null
			if _player != null:
				_player.prompt_target = null
		if _car_hint != null:
			_car_hint.visible = false


func _update_prompt() -> void:
	# "press f to ..." — doors, stairs, and cars worth taking. Hidden while
	# driving (the car hint covers that) and behind any open window.
	if Ui.blocks_gameplay():
		# the map doesn't pause the tree, so this path still runs with it
		# open — the group call above only covers the paused windows
		_prompt.visible = false
		_prompt_target = null
		_player.prompt_target = null
		return
	if _player.extracting:
		_prompt.visible = false
		_prompt_target = null
		_player.prompt_target = null
		return
	if _player.driving != null:
		# driving hides everything EXCEPT the warden: you pull up to his
		# window in a car, every time, because a car is how you leave
		# (user). The car itself acts on the F press.
		var from_car: TollGate = null
		for node in get_tree().get_nodes_in_group("toll_gates"):
			var g := node as TollGate
			if g != null and g.can_use() \
					and g.global_position.distance_to(_player.global_position) \
					< TollGate.INTERACT_RANGE:
				from_car = g
				break
		if from_car == null:
			_prompt.visible = false
			_prompt_target = null
			_player.prompt_target = null
			return
		if from_car != _prompt_target:
			_prompt_target = from_car
			_prompt.text = "press %s to talk to the warden" \
				% Settings.bind_label("interact").to_lower()
		_place_prompt_over(from_car)
		return
	var best: Node2D = null
	var best_d := 30.0 * 30.0
	if not _player.upstairs:   # no door prompts on the second floor
		for node in get_tree().get_nodes_in_group("doors"):
			# wall_position(), not global_position: an OPEN door's node is
			# pushed off the wall line so its leaf sorts right, and this is
			# what decides whether "press f to close" shows at all
			var d := (node as Door).wall_position().distance_squared_to(
				_player.global_position)
			if d < best_d:
				best_d = d
				best = node
	for node in get_tree().get_nodes_in_group("stairs"):
		var d := (node as Node2D).global_position.distance_squared_to(
			_player.global_position)
		if d < 38.0 * 38.0 and d < best_d:
			best_d = d
			best = node
	for node in get_tree().get_nodes_in_group("cars"):
		var car := node as DriveableCar
		if car == null or not car.can_enter():
			continue
		var d := car.global_position.distance_squared_to(_player.global_position)
		if d < 42.0 * 42.0 and d < best_d:
			best_d = d
			best = car
	# the freight, but only while it's actually standing in the yard
	for node in get_tree().get_nodes_in_group("trains"):
		var train := node as NightFreight
		if train == null or not train.can_board():
			continue
		var d := train.global_position.distance_squared_to(_player.global_position)
		if d < NightFreight.BOARD_RANGE * NightFreight.BOARD_RANGE and d < best_d:
			best_d = d
			best = train
	# the toll warden answers from a car's length away — you pull UP to
	# his window, you don't get out and knock
	for node in get_tree().get_nodes_in_group("toll_gates"):
		var gate := node as TollGate
		if gate == null or not gate.can_use():
			continue
		var d := gate.global_position.distance_squared_to(_player.global_position)
		if d < TollGate.INTERACT_RANGE * TollGate.INTERACT_RANGE and d < best_d:
			best_d = d
			best = gate
	if best == null:
		_prompt.visible = false
		_prompt_target = null
		_player.prompt_target = null
		return
	# the prompt IS the permission: nothing else can be interacted with
	_player.prompt_target = best
	# rebuild the text only when the target or its state changes — bind_label
	# asks the display server and must not run per frame
	# THE FLOOR IS PART OF THAT STATE. The stairs prompt reads "go upstairs" or
	# "back down" off _player_upper, and climbing does NOT change the target —
	# it is the same Stairs node — so without this the text was never rebuilt
	# and still read "press f to go upstairs" while you stood on the second
	# floor.
	var open_now := best is Door and (best as Door).is_open()
	var restale := best != _prompt_target or open_now != _prompt_open
	if _player_upper != _prompt_upper:
		restale = true
	if restale:
		_prompt_target = best
		_prompt_open = open_now
		_prompt_upper = _player_upper
		var key := Settings.bind_label("interact").to_lower()
		if best is Door:
			_prompt.text = "press %s to %s" % [key, "close" if open_now else "open"]
		elif best is Stairs:
			var going_up := _player_upper != (best as Stairs).upper_index
			_prompt.text = "press %s to go %s" % [key,
				"upstairs" if going_up else "back down"]
		elif best is TollGate:
			_prompt.text = "press %s to talk to the warden" % key
		elif best is NightFreight:
			_prompt.text = "press %s to get on the train" % key
		else:
			_prompt.text = "press %s to enter the car" % key
	_place_prompt_over(best)
	_prompt.visible = true


func _place_prompt_over(best: Node2D) -> void:
	# pin the label just above the target, following it on screen
	var camera := get_viewport().get_camera_2d()
	if camera != null:
		var view := Vector2(get_window().content_scale_size)
		var on_screen := best.global_position - camera.get_screen_center_position() \
			+ view * 0.5
		var pos := on_screen + Vector2(-_prompt.size.x * 0.5, -56.0)
		pos.x = clampf(pos.x, 4.0, view.x - _prompt.size.x - 4.0)
		pos.y = clampf(pos.y, 4.0, view.y - 16.0)
		_prompt.position = pos.round()
	_prompt.visible = true


func _process(delta: float) -> void:
	if _deploy_screen != null:
		_deploy_time += delta
		_deploy_label.text = "deploying to %s%s" % [
			MAP_NAME, ".".repeat(1 + int(_deploy_time * 3.0) % 3)]
	# the grade follows the clock: shadows go colder and the split-tone
	# firms up after dark. Only pushed when it actually moves — a uniform
	# set every frame at 240 Hz is a wasted shader param upload.
	if _grade_mat != null and _environment != null:
		var n := float(_environment.get("night_amount"))
		if absf(n - _grade_night) > 0.004:
			_grade_night = n
			_grade_mat.set_shader_parameter("night", n)
	if _shaft_mat != null and _environment != null:
		# the sun only rakes when it is LOW: nothing at night, nothing at
		# noon overhead, strongest mid-morning and late afternoon. Two
		# bumps on the clock, killed by the roof over your head and by
		# heavy weather — you do not get shafts through a storm.
		var d := float(_environment.get("day_time"))
		var lit := 1.0 - float(_environment.get("night_amount"))
		# rain OR cloud blots out the sun — an overcast day must not get
		# beams just because it isn't raining
		var wet := float(_environment.call("sun_blocked"))
		# THE PLAYER'S SHADOW RIDES THE SAME CLOCK READ. The sun is up from
		# 05:00 to 21:00 (see the day arc in CLAUDE.md), so u runs 0..1 across
		# the lit part of the day and the elevation is a single arc over it:
		# flat on the horizon at both ends, highest in the middle. A low sun
		# throws a long shadow, a high one throws almost none.
		if _player != null:
			var u := clampf((d - 0.2083) / (0.875 - 0.2083), 0.0, 1.0)
			var elev := sin(u * PI)
			# the sun crosses east to west, so the shadow is thrown the other
			# way and sweeps back across the ground through the day
			var sun_dir := Vector2(lerpf(-1.0, 1.0, u), 0.45).normalized()
			# no sun means no cast shadow: night, rain and heavy cloud all kill
			# it, leaving only the soft contact darkening underfoot
			var sun_str := clampf(elev * 1.5, 0.0, 1.0) * lit * (1.0 - wet * 0.9)
			_player.set_sun(sun_dir, 1.0 - elev, clampf(sun_str, 0.0, 1.0))
		var low := maxf(_bump(d, 0.335, 0.075), _bump(d, 0.700, 0.095))
		var want := clampf(low * lit * (1.0 - wet * 0.92), 0.0, 1.0)
		if _last_roof_cell != Vector2i(-9999, -9999) and _indoors_now:
			want = 0.0
		_shaft_now = move_toward(_shaft_now, want, delta * 1.6)
		_shaft_mat.set_shader_parameter("strength", _shaft_now * 0.55)
		# the bearing swings through the day, so morning light and evening
		# light do not come from the same side
		_shaft_mat.set_shader_parameter("angle", lerpf(-0.95, -0.30,
			clampf((d - 0.30) / 0.42, 0.0, 1.0)))
		_shaft_mat.set_shader_parameter("drift",
			float(Time.get_ticks_msec()) * 0.001)
	if _player == null or _floor_layer == null:
		return
	# This runs EVERY frame on purpose. It walks five node groups, which
	# is real work, but `prompt_target` is what F is allowed to act on —
	# throttling it to 20 Hz opened a window where the prompt said one
	# thing and F did another (the smoke test caught exactly that). The
	# interaction rule is worth more than the allocations; revisit only
	# by making the search cheaper, never by running it less often.
	if _prompt != null:
		_update_prompt()
	# the driving crash course pops for a few seconds whenever you get in
	var now_driving := _player.driving != null
	if now_driving and not _was_driving:
		_car_hint_until = Time.get_ticks_msec() / 1000.0 + 12.0
	_was_driving = now_driving
	if _car_hint != null:
		_car_hint.visible = now_driving and not Ui.blocks_gameplay() \
			and Time.get_ticks_msec() / 1000.0 < _car_hint_until
	var cell := _floor_layer.local_to_map(_player.position)
	# THE FLOOR IS PART OF THIS GATE. Climbing the stairs does not change your
	# CELL, so gating on the cell alone left the walls in whatever state they
	# had downstairs until you happened to take a step (user: "if you go up the
	# stairs, then dont move your character, it only shows the first floor
	# still, it should show both").
	if cell == _last_roof_cell and _player_upper == _last_roof_upper:
		return
	_last_roof_cell = cell
	_last_roof_upper = _player_upper
	# INSIDE MEANS INSIDE. v0.6.65 also counted "standing on a door cell" as
	# inside, to fix the player being visible through their own open doorway -
	# but a door sits ON the wall line, so that cell reads the same whether you
	# are in front of it or behind it, and the roof lifted while you were still
	# out on the street (user: "i can see the inside of the building when im
	# outside ... the roof should only disappear when the user goes inside,
	# like they go past the doorway"). Their rule, stated plainly, so the
	# interior rect is the whole test again.
	var indoors := false
	for roof in _roofs:
		var reveal := roof as RoofReveal
		var here := reveal.cells.has_point(cell)
		reveal.set_inside(here)
		# WHICH STOREY'S WALL YOU SEE. Three states, and every one of them was
		# paid for by a user report — read set_wall_storey before changing any
		# of them.
		#
		#   outside        everything
		#   ground floor   ground bands only; an upper storey would tower over
		#                  the room the roof fade just opened up
		#   upstairs       upper band + the NEAR ground bands
		#
		# THE NEAR GROUND BAND IS NEVER HIDDEN. v0.6.86 hid every ground band
		# upstairs and deleted the storey out from under the player — the room
		# hung in the air over open street with only the door frame holding it
		# up ("the bottom of the houses are gone when i enter the second floor
		# ... it looks like its floating right now").
		#
		# THE FAR GROUND BAND MUST GO WHEN UPSTAIRS. v0.6.87 showed it again
		# and it drew straight over the back of the upper floor, because the
		# slab sorts a storey north of the walls — so the room lost its back
		# rows of boards and the furniture there was left standing on brick
		# ("the floor is still on the ground ... you can see the furniture
		# floating"). It is the storey below your feet, seen from behind: your
		# own floor is what should be hiding it.
		var up_here := here and _player.upstairs
		reveal.set_wall_storey(true, not up_here, (not here) or up_here)
		indoors = indoors or here
	_indoors_now = indoors
	# a roof over your head muffles the weather (user). Same test that
	# reveals the interior, so the sound can never disagree with the view.
	Sfx.set_indoors(indoors)


func _bump(x: float, centre: float, width: float) -> float:
	## 1 at `centre`, falling to 0 by `width` either side. Used to give the
	## sun two low passes a day instead of one flat value.
	return maxf(0.0, 1.0 - absf(x - centre) / maxf(width, 0.001))


func abandon_raid() -> void:
	## quitting to the menu mid-raid: you don't get to walk away clean
	## (user call). Same debrief you'd get for dying, because that is what
	## leaving a raid on foot amounts to.
	if _death_screen == null or _player == null:
		get_tree().paused = false
		get_tree().change_scene_to_file("res://scenes/menu.tscn")
		return
	# ONE debrief per raid. Dying holds for 1.2s on a SceneTreeTimer before
	# it builds its own, and that timer keeps counting under the paused tree
	# (process_always defaults true) — so pressing esc and abandoning during
	# the hold used to build the screen twice and stack two panels.
	if _debrief_open:
		return
	_debrief_open = true
	Music.stop_raid(1.0)
	Sfx.set_engine(0.0)
	_death_screen.show_debrief(_player, true)


func _on_extracted(method: String) -> void:
	Music.stop_raid(1.5)
	Sfx.set_engine(0.0)
	_extract_screen.show_debrief(method)


func _on_player_died() -> void:
	if _respawning:
		return
	_respawning = true
	Music.stop_raid(2.5)  # the raid ends with you; a fresh one restarts it
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
	# SceneTreeTimers are owned by the tree and fire even after this scene
	# is freed — quitting to the menu during the death hold resumed this
	# coroutine on a dead instance
	if not is_inside_tree():
		return
	if _player_upper != -1:      # tidy the world you left behind
		_set_upper_state(_player_upper, false)
		# unseal before dropping the index, or the doorways of the building
		# you died in stay solid for the rest of the raid
		_block_ground_doors(_player_upper, false)
		_player_upper = -1
		_player.floor_lift = 0.0
		_player.upstairs = false
	if _player.driving != null:  # death at the wheel leaves the car behind
		# the car cleans up its whole cabin state — engine, headlights,
		# driver ref — or the wreck sits there running all night
		_player.driving.abandon()
		_player.driving = null
		_player.visible = true
		_player.collision_layer = 1
		Sfx.set_engine(0.0)
	# DYING ENDS THE RAID (user call). It used to respawn you where you
	# woke up, which was the placeholder from before extraction existed —
	# and it made walking out (which now costs you everything) harsher
	# than being killed. Same debrief either way; the doll is drawn from
	# the rounds that actually landed.
	if _death_screen != null and not Harness.suppress_debrief:
		layer.queue_free()
		if _debrief_open:
			return           # abandoned during the hold; that screen stands
		_debrief_open = true
		_death_screen.show_debrief(_player, false)
		return
	# no debrief available (a raid that never finished building): fall
	# back to the old respawn so the player is never stranded
	_player.respawn(world_info["spawn"])
	label.visible = false
	await get_tree().process_frame
	var fade_out := create_tween()
	fade_out.tween_property(black, "color:a", 0.0, 0.45)
	await fade_out.finished
	layer.queue_free()
	_respawning = false
	Music.play_raid()
