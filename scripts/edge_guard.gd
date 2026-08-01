class_name EdgeGuard
extends Node
## The map edge is sniper country. Get close to the boundary and a warning
## appears dead center (a touch above the middle); stay past the grace period
## and rounds start coming in from off-screen — three hits and the raid ends.
## Turn back and it all resets.

const GRACE_SECONDS := 3.0
const SHOT_INTERVAL_MIN := 1.3
const SHOT_INTERVAL_MAX := 2.1
const SHOT_SPEED := 1150.0  # dodging one on reaction should barely work
const SHOT_SPAWN_DIST := 430.0   # beyond every supported view half-diagonal
const SHOT_LIFE := 1.4
const HIT_RADIUS := 8.0
# past these depths beyond the barricades the sniper stops playing fair —
# the fire rate and accuracy escalate so nobody outruns the buffer zone
const ESCALATE_DEPTH := 240.0
const LETHAL_DEPTH := 480.0

var _player: Player
var _map_center := Vector2.ZERO
var _barrier_f := 0.0
var _world: Node2D
var _label: Label
var _zone_time := 0.0
var _shot_timer := 0.0
var _rng := RandomNumberGenerator.new()

# a tiny fixed pool of live rounds (a sniper is patient, not a machine gun)
var _rounds: Array[Node2D] = []
var _round_vel: Array[Vector2] = []
var _round_age: Array[float] = []
var _pending: Array[float] = []  # countdowns to the volley's staggered shots
var _round_tex: Texture2D        # cached once — not re-fetched per shot
var stood_down := false          # the toll was paid: this stretch looks away
var _was_beyond := false         # the runner actually went past the line


func setup(player: Player, world: Node2D, map_center: Vector2, barrier_f: float) -> void:
	_player = player
	_world = world
	_map_center = map_center
	_barrier_f = barrier_f
	_rng.randomize()
	_round_tex = load("res://art/gen/sniper_round.png")

	var layer := CanvasLayer.new()
	layer.layer = 75
	# a full-rect root gives the anchors a real rect to center against (the
	# label used to hang bare under the CanvasLayer and could drift off-center
	# on scaled displays — user report). Fractional anchors: dead center
	# horizontally, a touch above the middle vertically, on ANY resolution.
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label = Label.new()
	_label.text = "turn back or you will get sniped"
	_label.theme = UITheme.get_theme()
	_label.anchor_left = 0.5
	_label.anchor_right = 0.5
	_label.anchor_top = 0.44
	_label.anchor_bottom = 0.44
	_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_label.grow_vertical = Control.GROW_DIRECTION_BOTH
	_label.add_theme_color_override("font_color", Color("cf573c"))
	_label.visible = false
	root.add_child(_label)
	layer.add_child(root)
	add_child(layer)


func _process(delta: float) -> void:
	_update_rounds(delta)
	# staggered volley shots come due even while retreating — _spawn_round
	# itself holds fire once the runner is back inside the line
	var pi_ := _pending.size() - 1
	while pi_ >= 0:
		_pending[pi_] -= delta
		if _pending[pi_] <= 0.0:
			_pending.remove_at(pi_)
			_spawn_round()
		pi_ -= 1
	if _player == null or _player.dead:
		# a new life gets no old favors: whatever the last one paid the
		# warden, the ring is watching again when you respawn
		stood_down = false
		_was_beyond = false
		_pending.clear()
		_leave_zone()
		return
	if stood_down:
		# paying the warden buys exactly this: the guns stop caring while
		# you drive out past the line. Rounds ALREADY QUEUED have to die
		# too — the staggered volley kept landing up to 0.84 s after the
		# stand-down, which is the very thing v0.6.40 claimed to fix.
		_pending.clear()
		_leave_zone()
		# but it buys ONE crossing: go past the wire and come back inside
		# and the marksmen pick their rifles back up (the stand-down used
		# to blind the whole ring for the rest of the raid)
		var su := _player.global_position - _map_center
		var sdepth := absf(su.x) * 0.5 + absf(su.y) - _barrier_f
		if sdepth >= 8.0:
			_was_beyond = true
		elif _was_beyond:
			stood_down = false
			_was_beyond = false
		return
	var u := _player.global_position - _map_center
	var f := absf(u.x) * 0.5 + absf(u.y)
	var depth := f - _barrier_f  # how far past the barricade line
	if depth < 8.0:
		_leave_zone()
		return
	if not _label.visible:
		_label.visible = true
		_zone_time = 0.0
	_zone_time += delta
	if _zone_time < GRACE_SECONDS:
		return
	_shot_timer -= delta
	if _shot_timer <= 0.0:
		if depth > LETHAL_DEPTH:
			_shot_timer = 0.55
		elif depth > ESCALATE_DEPTH:
			_shot_timer = 0.8
		else:
			_shot_timer = _rng.randf_range(SHOT_INTERVAL_MIN, SHOT_INTERVAL_MAX)
		_fire_volley(depth)


func _leave_zone() -> void:
	if _label.visible:
		_label.visible = false
	_zone_time = 0.0
	_shot_timer = 0.0


func _fire_volley(depth: float) -> void:
	# a VOLLEY: more than one sniper owns this buffer, but they are separate
	# people — the first fires now, the rest come STAGGERED fractions of a
	# second later (user call: never all at the same time), each with its
	# own crack and its own fresh read on the runner.
	var volley := 2 if depth <= ESCALATE_DEPTH else 3
	if depth <= ESCALATE_DEPTH and _rng.randf() < 0.35:
		volley = 3
	_spawn_round()
	for extra in range(1, volley):
		_pending.append(_rng.randf_range(0.14, 0.42) * float(extra))


func _spawn_round() -> void:
	if _player == null or _player.dead or stood_down:
		return
	var u := _player.global_position - _map_center
	var depth := absf(u.x) * 0.5 + absf(u.y) - _barrier_f
	if depth < 8.0:
		return  # turned back mid-volley: the shooters hold fire
	var out_dir := Vector2(0.5 * signf(u.x), signf(u.y)).normalized()
	# each shooter sits at a different angle along the treeline
	out_dir = out_dir.rotated(_rng.randf_range(-0.5, 0.5))
	var side := out_dir.orthogonal()
	# PREDICTED aim (user call): lead the runner — the round flies at where
	# you are HEADED, not where you are. Slight per-shooter over/under-lead
	# keeps direction changes worth something.
	var lead_time := SHOT_SPAWN_DIST / SHOT_SPEED
	var target := _player.global_position \
		+ _player.velocity * lead_time * _rng.randf_range(0.75, 1.05)
	var start := target + out_dir * SHOT_SPAWN_DIST \
		+ side * _rng.randf_range(-140.0, 140.0)
	var err := 2.0 if depth > ESCALATE_DEPTH else 7.0
	var aim := target + side * _rng.randf_range(-err, err)
	var vel := (aim - start).normalized() * SHOT_SPEED
	Sfx.play_crack()

	var round_node := Node2D.new()
	round_node.z_index = 70
	var tex: Texture2D = _round_tex
	var head := Sprite2D.new()
	head.texture = tex
	round_node.add_child(head)
	for trail in 2:  # faint motion trail behind the head
		var ghost := Sprite2D.new()
		ghost.texture = tex
		ghost.position = -vel * (0.006 * float(trail + 1))
		ghost.modulate.a = 0.45 - 0.2 * float(trail)
		round_node.add_child(ghost)
	round_node.position = start
	_world.add_child(round_node)
	_rounds.append(round_node)
	_round_vel.append(vel)
	_round_age.append(0.0)


func _update_rounds(delta: float) -> void:
	var i := _rounds.size() - 1
	while i >= 0:
		var node := _rounds[i]
		node.position += _round_vel[i] * delta
		_round_age[i] += delta
		var done := _round_age[i] >= SHOT_LIFE
		if not done and _player != null and not _player.dead \
				and node.position.distance_squared_to(_player.global_position + Vector2(0, -10)) \
				< HIT_RADIUS * HIT_RADIUS:
			Authority.damage_player(_player)
			done = true
		if done:
			node.queue_free()
			_rounds.remove_at(i)
			_round_vel.remove_at(i)
			_round_age.remove_at(i)
		i -= 1
