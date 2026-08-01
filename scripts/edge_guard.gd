class_name EdgeGuard
extends Node
## The map edge is sniper country. Get close to the boundary and a warning
## appears dead center (a touch above the middle); stay past the grace period
## and rounds start coming in from off-screen — three hits and the raid ends.
## Turn back and it all resets.

const WARN_MARGIN := 96.0        # f-metric distance from the edge (6 tile rings)
const GRACE_SECONDS := 3.0
const SHOT_INTERVAL_MIN := 1.3
const SHOT_INTERVAL_MAX := 2.1
const SHOT_SPEED := 950.0
const SHOT_SPAWN_DIST := 430.0   # beyond every supported view half-diagonal
const SHOT_LIFE := 1.4
const HIT_RADIUS := 8.0

var _player: Player
var _map_center := Vector2.ZERO
var _map_half_h := 0.0
var _world: Node2D
var _label: Label
var _zone_time := 0.0
var _shot_timer := 0.0
var _rng := RandomNumberGenerator.new()

# a tiny fixed pool of live rounds (a sniper is patient, not a machine gun)
var _rounds: Array[Node2D] = []
var _round_vel: Array[Vector2] = []
var _round_age: Array[float] = []


func setup(player: Player, world: Node2D, map_center: Vector2, map_half_h: float) -> void:
	_player = player
	_world = world
	_map_center = map_center
	_map_half_h = map_half_h
	_rng.randomize()

	var layer := CanvasLayer.new()
	layer.layer = 75
	_label = Label.new()
	_label.text = "turn back or you will get sniped"
	_label.theme = UITheme.get_theme()
	_label.set_anchors_preset(Control.PRESET_CENTER)
	_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_label.grow_vertical = Control.GROW_DIRECTION_BOTH
	_label.position.y -= 58.0  # a bit higher than the middle, per spec
	_label.add_theme_color_override("font_color", Color("cf573c"))
	_label.visible = false
	layer.add_child(_label)
	add_child(layer)


func _process(delta: float) -> void:
	_update_rounds(delta)
	if _player == null or _player.dead:
		_leave_zone()
		return
	var u := _player.global_position - _map_center
	var f := absf(u.x) * 0.5 + absf(u.y)
	if f < _map_half_h - WARN_MARGIN:
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
		_shot_timer = _rng.randf_range(SHOT_INTERVAL_MIN, SHOT_INTERVAL_MAX)
		_fire_round(u)


func _leave_zone() -> void:
	if _label.visible:
		_label.visible = false
	_zone_time = 0.0
	_shot_timer = 0.0


func _fire_round(u: Vector2) -> void:
	# the shot comes from OUTSIDE — the direction of the nearest edge
	var out_dir := Vector2(0.5 * signf(u.x), signf(u.y)).normalized()
	var side := out_dir.orthogonal()
	var target := _player.global_position
	var start := target + out_dir * SHOT_SPAWN_DIST \
		+ side * _rng.randf_range(-60.0, 60.0)
	var aim := target + side * _rng.randf_range(-8.0, 8.0)
	var vel := (aim - start).normalized() * SHOT_SPEED

	var round_node := Node2D.new()
	round_node.z_index = 70
	var tex: Texture2D = load("res://art/gen/sniper_round.png")
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
	Sfx.play_crack()


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
