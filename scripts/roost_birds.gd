class_name RoostBirds
extends Node2D
## Birds that sit in the district's trees and leave when you get too close
## (user, 2026-08-08: "Environmental Reactions: Make birds fly away from
## trees").
##
## THE LINE THIS STAYS THE RIGHT SIDE OF. The standing rule is that nothing in
## the world changes how it LOOKS because of where the player is — "everything
## is static unless i asked otherwise". A reaction is not a violation of that,
## but only if it is a real EVENT rather than a visibility flip:
##
##   **A FLUSHED BIRD ACTUALLY LEAVES AND STAYS GONE.** It does not toggle
##   with distance. Walk back and the branch is empty, because the bird flew
##   off it — which is what would really happen, and it means nothing ever
##   pops at a threshold. A roost only ever refills when the player is far
##   away and out of sight of it, so a refill can never be witnessed either.
##
## The other trap this inherits, from the menu birds that sat still for three
## sessions: **keep the true position in a float**. `position = roundf(position
## + speed * delta)` rounds a slow drift straight back to zero at 240 fps.

const ROOSTS := 22              # trees that hold birds, district-wide
const PER_ROOST := 3
const FLUSH_RANGE := 132.0      # they go before you are on top of them
const REFILL_RANGE := 900.0     # ...and only come back well out of sight
const REFILL_DELAY := 26.0
const FLY_SECONDS := 3.4

var _player: Player
var _sprites: Array[Sprite2D] = []
var _home: PackedVector2Array = PackedVector2Array()   # the branch it sits on
var _x: PackedFloat32Array = PackedFloat32Array()      # TRUE position, float
var _y: PackedFloat32Array = PackedFloat32Array()
var _vx: PackedFloat32Array = PackedFloat32Array()
var _vy: PackedFloat32Array = PackedFloat32Array()
var _state: PackedInt32Array = PackedInt32Array()      # 0 perched, 1 flying
var _timer: PackedFloat32Array = PackedFloat32Array()
var _phase: PackedFloat32Array = PackedFloat32Array()
var _tex: Array = []
var _time := 0.0
var _rng := RandomNumberGenerator.new()


func setup(player: Player, tree_points: PackedVector2Array) -> void:
	_player = player
	# UNSEEDED: this is per-raid life, not layout. It never touches the
	# builder's `_rng`, so the FIXED district cannot move.
	_rng.randomize()
	# see the same note in ground_fx.gd — a plain container inside the y-sorted
	# world draws every child at the container's own y
	y_sort_enabled = true
	for i in 4:
		_tex.append(load("res://art/gen/roost_bird_%d.png" % i))
	if tree_points.is_empty():
		return
	var picked: Dictionary = {}
	for r in ROOSTS:
		var idx := _rng.randi_range(0, tree_points.size() - 1)
		if picked.has(idx):
			continue
		picked[idx] = true
		var base: Vector2 = tree_points[idx]
		for k in PER_ROOST:
			var perch := base + Vector2(_rng.randf_range(-7.0, 7.0),
				_rng.randf_range(-26.0, -14.0))
			var s := Sprite2D.new()
			s.texture = _tex[0]
			s.position = perch.round()
			add_child(s)
			_sprites.append(s)
			_home.append(perch)
			_x.append(perch.x)
			_y.append(perch.y)
			_vx.append(0.0)
			_vy.append(0.0)
			_state.append(0)
			_timer.append(0.0)
			_phase.append(_rng.randf() * 6.0)


func _process(delta: float) -> void:
	if _player == null or not is_instance_valid(_player) or _sprites.is_empty():
		return
	_time += delta
	var at := _player.global_position
	for i in _sprites.size():
		var s := _sprites[i]
		if _state[i] == 0:
			if s.visible and at.distance_to(Vector2(_x[i], _y[i])) < FLUSH_RANGE:
				_flush(i, at)
			continue
		# FLYING: away from where it was startled, climbing, then gone
		_timer[i] -= delta
		_x[i] += _vx[i] * delta
		_y[i] += _vy[i] * delta
		_vy[i] -= 26.0 * delta                  # climbing away
		var flap := _time * 15.0 + _phase[i]
		s.texture = _tex[1 + (int(flap) % 3)]
		s.position = Vector2(_x[i], _y[i]).round()
		s.modulate = Color(1.0, 1.0, 1.0, clampf(_timer[i] / 1.2, 0.0, 1.0))
		if _timer[i] <= 0.0:
			s.visible = false
			_state[i] = 2                        # gone; waiting to refill
			_timer[i] = REFILL_DELAY
		continue
	_refill(at, delta)


func _flush(i: int, from: Vector2) -> void:
	_state[i] = 1
	_timer[i] = FLY_SECONDS
	var away := (Vector2(_x[i], _y[i]) - from)
	if away.length() < 1.0:
		away = Vector2(1.0, -0.5)
	away = away.normalized()
	# iso: horizontal reads twice as fast as vertical, so the flight path has
	# to be flattened or they look like they are climbing out of the screen
	_vx[i] = away.x * _rng.randf_range(52.0, 78.0)
	_vy[i] = away.y * _rng.randf_range(26.0, 39.0) - 14.0
	Sfx.play_bird_flush(Vector2(_x[i], _y[i]))


func _refill(at: Vector2, delta: float) -> void:
	for i in _sprites.size():
		if _state[i] != 2:
			continue
		_timer[i] -= delta
		if _timer[i] > 0.0:
			continue
		# ONLY WELL OUT OF SIGHT. A bird reappearing on a branch you can see is
		# exactly the pop the static rule forbids; at this range the roost is
		# far off screen, so the refill can never be witnessed.
		if at.distance_to(Vector2(_home[i].x, _home[i].y)) < REFILL_RANGE:
			_timer[i] = 4.0
			continue
		var s := _sprites[i]
		_x[i] = _home[i].x
		_y[i] = _home[i].y
		s.position = _home[i].round()
		s.texture = _tex[0]
		s.modulate = Color(1.0, 1.0, 1.0, 1.0)
		s.visible = true
		_state[i] = 0
