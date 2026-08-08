class_name GroundFX
extends Node2D
## What the ground gives back: dust off the player's boots, the prints they
## leave in it, and litter the wind pushes across the district.
##
## Three user requests from 2026-08-08, built as one node because they share
## everything that matters — the same surface test, the same pooling, and the
## same pixel-grid rules:
##   "can you make small dust clouds kick up from the player's boots as they
##    run across the ground"
##   "add like 1 or 2 footprints that the character leaves when walking around"
##   "Wind debris: Blow occasional pixel leaves, tumbleweeds, or scrap paper
##    across the world"
##
## THE RULES THIS PROJECT HAS ALREADY PAID FOR, all of which bite here:
##
## - **NOTHING SCALES OR ROTATES.** Puffs grow by swapping between four BAKED
##   frames and prints are baked per facing. Runtime scale/rotation breaks the
##   pixel grid — the reason `motes.gd` pins its particle scale to 1.0.
## - **TRUE POSITIONS STAY FLOAT.** Every mover keeps its own continuous
##   position and only what is ASSIGNED to `position` is rounded. Reading a
##   rounded position back to accumulate is what silently froze the menu birds
##   and the counter rat: at 240 fps a slow drift is under half a pixel a
##   frame and the round puts it straight back.
## - **HARD CAPS, POOLED.** Prints and debris are fixed-size pools reused in
##   place. A print per step across a 256x256 district would be an unbounded
##   node leak, and `--leakcheck` has to keep reporting orphans=0.
## - **THE SURFACE DECIDES.** Dust and prints only happen on ground that would
##   actually take them — dirt and dust, never wet asphalt or slabs — read
##   from the SAME atlas->kind table `player._footstep` already uses, not from
##   a second surface test that could disagree with the footstep audio.

const PUFF_FRAMES := 4
const PUFF_POOL := 14           # ~1.5 s of walking at the emit rate
const PUFF_LIFE := 0.46
const PRINT_POOL := 12          # the "1 or 2" the user asked for, times a
                                # short trail, so the oldest fades as you go
const PRINT_LIFE := 7.0
const DEBRIS_COUNT := 10        # across the whole visible frame, not per cell
const DEBRIS_MARGIN := 120.0    # spawn/retire this far outside the view

## Ground that takes a print and raises dust. Everything else — slabs, asphalt,
## rail, water — is left alone. Keys are the kinds `setup_surfaces` publishes.
const SOFT_GROUND := {
	"dirt": true, "gravel": true, "grass": true, "wood": true,
}

var _player: Player
var _floor_layer: TileMapLayer
var _surface_kinds: Dictionary = {}
var _environment: Node

var _puffs: Array[Sprite2D] = []
var _puff_age: PackedFloat32Array = PackedFloat32Array()
var _puff_next := 0

var _prints: Array[Sprite2D] = []
var _print_age: PackedFloat32Array = PackedFloat32Array()
var _print_next := 0
var _print_left := false        # alternate feet
var _walked := 0.0              # distance since the last print

var _debris: Array[Sprite2D] = []
var _debris_tex: Array = []     # [kind][frame] -> Texture2D
var _debris_x: PackedFloat32Array = PackedFloat32Array()
var _debris_y: PackedFloat32Array = PackedFloat32Array()
var _debris_vx: PackedFloat32Array = PackedFloat32Array()
var _debris_vy: PackedFloat32Array = PackedFloat32Array()
var _debris_kind: PackedInt32Array = PackedInt32Array()
var _debris_phase: PackedFloat32Array = PackedFloat32Array()

var _puff_tex: Array = []
var _print_tex: Array = []
var _last_pos := Vector2.ZERO
var _time := 0.0
var _rng := RandomNumberGenerator.new()


func setup(player: Player, floor_layer: TileMapLayer, kinds: Dictionary,
		environment: Node) -> void:
	_player = player
	_floor_layer = floor_layer
	_surface_kinds = kinds
	_environment = environment
	_last_pos = player.global_position
	# UNSEEDED ON PURPOSE. This is per-raid life, not layout — the FIXED
	# district rule governs the builder's `_rng`, and this node never touches
	# it. Nothing here can move a building.
	_rng.randomize()
	# NESTED Y-SORT, NOT A FLAT CONTAINER. This node lives inside the y-sorted
	# world; without its own sorting every child would draw at THIS node's y
	# (zero), which puts the whole effect behind the entire district. Enabling
	# it merges the children into the parent's ordering so a puff sorts against
	# the props around it, exactly like any other sprite.
	y_sort_enabled = true

	for i in PUFF_FRAMES:
		_puff_tex.append(load("res://art/gen/boot_puff_%d.png" % i))
	for i in 8:
		_print_tex.append(load("res://art/gen/footprint_%d.png" % i))
	for kind in ["leaf", "paper", "weed"]:
		var frames: Array = []
		for f in 3:
			frames.append(load("res://art/gen/debris_%s_%d.png" % [kind, f]))
		_debris_tex.append(frames)

	# PRINTS SIT UNDER EVERYTHING that stands on the ground, so they go on
	# their own node below the y-sorted world rather than taking a z_index of
	# -1 inside it — that sorts GLOBALLY and would put them behind the floor
	# tilemap entirely, which is the bug the flat-decal layer exists to avoid.
	for i in PRINT_POOL:
		var s := Sprite2D.new()
		s.visible = false
		s.z_index = -2
		add_child(s)
		_prints.append(s)
		_print_age.append(PRINT_LIFE + 1.0)
	for i in PUFF_POOL:
		var s2 := Sprite2D.new()
		s2.visible = false
		add_child(s2)
		_puffs.append(s2)
		_puff_age.append(PUFF_LIFE + 1.0)
	for i in DEBRIS_COUNT:
		var s3 := Sprite2D.new()
		s3.visible = false
		add_child(s3)
		_debris.append(s3)
		_debris_x.append(0.0)
		_debris_y.append(0.0)
		_debris_vx.append(0.0)
		_debris_vy.append(0.0)
		_debris_kind.append(0)
		_debris_phase.append(0.0)


func _soft_here(at: Vector2) -> bool:
	if _floor_layer == null:
		return false
	var atlas := _floor_layer.get_cell_atlas_coords(
		_floor_layer.local_to_map(at))
	return SOFT_GROUND.has(_surface_kinds.get(atlas, "concrete"))


func _process(delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		return
	_time += delta
	_age_puffs(delta)
	_age_prints(delta)
	if not _player.dead and _player.driving == null:
		_track_player(delta)
	_move_debris(delta)


func _track_player(delta: float) -> void:
	var pos := _player.global_position
	var moved := pos.distance_to(_last_pos)
	_last_pos = pos
	# PRONE AND CROUCH RAISE NOTHING. A crawl does not kick dust and a crouch
	# walk barely presses the ground; this also keeps the effect off the
	# stances a player uses to be unseen.
	if _player.prone or _player.crouching or moved <= 0.0:
		return
	# lifted onto a second storey there is no ground under you to disturb
	if _player.floor_lift > 0.0:
		return
	if not _soft_here(pos):
		_walked = 0.0
		return
	_walked += moved
	if _walked < 22.0:
		return
	_walked = 0.0
	_emit_print(pos)
	_emit_puff(pos)


func _emit_print(at: Vector2) -> void:
	var s := _prints[_print_next]
	_print_age[_print_next] = 0.0
	_print_next = (_print_next + 1) % PRINT_POOL
	s.texture = _print_tex[_facing()]
	# OFF TO ONE SIDE, alternating, so a trail reads as two feet rather than a
	# dotted line down the middle
	var side := _player.facing_angle() + PI * 0.5
	var off := Vector2(cos(side), sin(side) * 0.5) * (3.0 if _print_left
		else -3.0)
	_print_left = not _print_left
	s.position = (at + off + Vector2(0.0, 2.0)).round()
	s.visible = true
	s.modulate = Color(1.0, 1.0, 1.0, 0.85)


func _facing() -> int:
	return wrapi(roundi(_player.facing_angle() / (PI / 4.0)), 0, 8)


func _emit_puff(at: Vector2) -> void:
	var s := _puffs[_puff_next]
	_puff_age[_puff_next] = 0.0
	_puff_next = (_puff_next + 1) % PUFF_POOL
	s.texture = _puff_tex[0]
	# behind the boot, never under the character's own feet where it would be
	# hidden by the sprite
	var back := _player.facing_angle() + PI
	s.position = (at + Vector2(cos(back), sin(back) * 0.5) * 4.0
		+ Vector2(0.0, 1.0)).round()
	s.visible = true


func _age_puffs(delta: float) -> void:
	for i in _puffs.size():
		if _puff_age[i] > PUFF_LIFE:
			continue
		_puff_age[i] += delta
		var s := _puffs[i]
		if _puff_age[i] >= PUFF_LIFE:
			s.visible = false
			continue
		var t := _puff_age[i] / PUFF_LIFE
		# GROWS BY FRAME, NOT BY SCALE
		s.texture = _puff_tex[mini(PUFF_FRAMES - 1, int(t * PUFF_FRAMES))]
		s.modulate = Color(1.0, 1.0, 1.0, (1.0 - t) * 0.5)
		# drifts up a little; whole pixels only
		s.position.y = s.position.y - (1.0 if fmod(t, 0.34) < delta else 0.0)


func _age_prints(delta: float) -> void:
	for i in _prints.size():
		if _print_age[i] > PRINT_LIFE:
			continue
		_print_age[i] += delta
		var s := _prints[i]
		if _print_age[i] >= PRINT_LIFE:
			s.visible = false
			continue
		# holds, then fades out over the last third
		var t := _print_age[i] / PRINT_LIFE
		s.modulate = Color(1.0, 1.0, 1.0,
			0.85 * (1.0 if t < 0.66 else (1.0 - t) * 3.0))


func _wind() -> Vector2:
	## ONE WIND FOR THE WHOLE WORLD. `environment_system` already runs a wind
	## for the dawn fog and `sway.gdshader` leans the foliage; debris drifting
	## against the trees would read as a bug, so this reads that value rather
	## than inventing a second one.
	var w := 9.0
	if _environment != null:
		var v = _environment.get("_fog_wind")
		if typeof(v) == TYPE_FLOAT and absf(float(v)) > 0.01:
			w = float(v)
	# iso: a wind blowing along the ground shows as mostly-horizontal drift
	return Vector2(w * 3.6, absf(w) * 0.55)


func _move_debris(delta: float) -> void:
	if _debris.is_empty():
		return
	var cam := _player.global_position
	var view := Vector2(get_viewport().get_visible_rect().size)
	var half := view * 0.5 + Vector2(DEBRIS_MARGIN, DEBRIS_MARGIN)
	var wind := _wind()
	for i in _debris.size():
		var s := _debris[i]
		if not s.visible:
			# OCCASIONAL, not a blizzard (user's word). Each idle piece waits
			# on its own coin flip, so they trickle in rather than arriving as
			# a wave.
			if _rng.randf() > 0.22 * delta:
				continue
			_debris_kind[i] = _rng.randi_range(0, 2)
			_debris_phase[i] = _rng.randf() * 10.0
			# enter from upwind, at a random height across the view
			var from_left := wind.x > 0.0
			_debris_x[i] = cam.x + (-half.x if from_left else half.x)
			_debris_y[i] = cam.y + _rng.randf_range(-half.y, half.y)
			var gust := _rng.randf_range(0.75, 1.4)
			_debris_vx[i] = wind.x * gust
			_debris_vy[i] = wind.y * gust * _rng.randf_range(-0.4, 0.6)
			s.visible = true
		# TRUE POSITION KEPT AS FLOAT — see the header. Only what is assigned
		# to `position` is rounded.
		_debris_x[i] += _debris_vx[i] * delta
		_debris_y[i] += _debris_vy[i] * delta
		var phase := _time * 6.0 + _debris_phase[i]
		var bob := sin(phase) * (2.0 if _debris_kind[i] != 2 else 0.0)
		s.position = Vector2(_debris_x[i], _debris_y[i] + bob).round()
		var frames: Array = _debris_tex[_debris_kind[i]]
		s.texture = frames[int(phase * 0.6) % frames.size()]
		if absf(_debris_x[i] - cam.x) > half.x + 40.0 \
				or absf(_debris_y[i] - cam.y) > half.y + 40.0:
			s.visible = false
