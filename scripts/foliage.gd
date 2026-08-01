class_name Foliage
extends Node
## Bushes the player pushes through: they sway, go half-transparent,
## and rustle on the way in and out. The bushes are FULL cover now
## (taller than the standing sprite), so the player sprite fades too —
## that's how you read "i'm hidden" (user request). Sway is a slow
## whole-pixel rummage with a per-bush phase: never subpixel, never
## rotation, never the old synchronized shiver.
##
## PERF: bushes are STATIC props, so positions are cached into packed
## arrays at register time — the 240 Hz loop costs one distance check
## per idle bush and only does real work for the handful near the player.

const RADIUS := 28.0                  # scaled with the walk-in bushes
const SWAY_STEP := 0.16               # seconds per sway beat — rummaging,
                                      # not shivering (user: "move slowly")
const HIDE_ALPHA := 0.5               # bush AND player while inside
const RUSTLE_GAP_MS := 250            # clumps overlap; don't machine-gun it

var _player: Player
var _sprites: Array[Sprite2D] = []
var _pos := PackedVector2Array()      # bush world positions (never move)
var _base_x := PackedFloat32Array()
var _settle := PackedFloat32Array()
var _sway_t := PackedFloat32Array()
var _inside := PackedByteArray()
var _last_rustle := 0


func setup(player: Player) -> void:
	_player = player


func register(node: Node2D) -> void:
	for child in node.get_children():
		if child is Sprite2D:
			_sprites.append(child)
			_pos.append(node.global_position)
			_base_x.append((child as Sprite2D).position.x)
			_settle.append(0.0)
			_sway_t.append(randf() * SWAY_STEP * 4.0)
			_inside.append(0)
			return


func _process(delta: float) -> void:
	var p := _player.global_position
	var dead := _player.dead
	# at the wheel the bushes still sway as the car plows through, but the
	# leaf-brush sounds stay OFF — a car crossing a clump line fired them
	# several times a second, which read as "static" (user report)
	var muted := _player.driving != null
	var r2 := RADIUS * RADIUS
	var any_inside := false
	for i in _sprites.size():
		var was: bool = _inside[i] == 1
		var inside: bool = not dead and _pos[i].distance_squared_to(p) < r2
		if not inside and not was and _settle[i] <= 0.0:
			continue                  # idle bush: one distance check, done
		var sprite := _sprites[i]
		if inside:
			any_inside = true
			if not was and not muted:
				_rustle(false)        # a real push through leaves (user:
				                      # louder, like passing the trees)
		elif was:
			_settle[i] = 0.6          # rustles a moment after you leave
			if not muted:
				_rustle(true)         # softer brush on the way out
		_inside[i] = 1 if inside else 0
		sprite.modulate.a = move_toward(sprite.modulate.a,
			HIDE_ALPHA if inside else 1.0, delta * 4.0)
		if not inside and _settle[i] > 0.0:
			_settle[i] = maxf(0.0, _settle[i] - delta)
		if inside or _settle[i] > 0.0:
			_sway_t[i] += delta
			# slow 4-beat sway: lean, center, lean the other way, center —
			# whole pixels only, phase offset per bush so clumps don't march
			var beat := int(floorf(_sway_t[i] / SWAY_STEP)) % 4
			var offset := 0.0
			if beat == 0:
				offset = 1.0
			elif beat == 2:
				offset = -1.0
			sprite.position.x = _base_x[i] + offset
		else:
			_sway_t[i] = randf() * SWAY_STEP * 4.0
			sprite.position.x = _base_x[i]
	_player.hidden_in_bush = any_inside and not muted


func _rustle(quiet: bool) -> void:
	var now := Time.get_ticks_msec()
	if now - _last_rustle < RUSTLE_GAP_MS:
		return
	_last_rustle = now
	Sfx.play_step("grass", quiet)
