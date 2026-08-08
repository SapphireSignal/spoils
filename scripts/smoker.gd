class_name Smoker
extends Node2D
## The gallery regular: sits on his bench, spray can in one hand, and works
## a cigarette with the other. Idle → drag (ember flares) → exhale, with
## little smoke wisps drifting off the exhale. Never in a hurry.

var _sprite: Sprite2D
var _phase := 0          # 0 idle, 1 drag, 2 exhale
var _timer := 0.0
var _wisps: Array[Dictionary] = []
var _dust_tex: Texture2D

const WISP_LIFE := 2.2      # a puff hangs and thins; 1.4 s cut it off mid-rise


func _ready() -> void:
	_sprite = Sprite2D.new()
	_sprite.texture = load("res://art/gen/smoker.png")
	_sprite.hframes = 3
	_sprite.centered = false
	# he is built from the PLAYER's sheet now, so the frames are the player's
	# 32x40 on the player's feet anchor — and the sheet is MIRRORED, which puts
	# the body centre at 31 - CX = 15 (see make_smoker_sheet)
	_sprite.offset = Vector2(-15, -37)
	add_child(_sprite)
	# SOFT-ALPHA SMOKE, NOT A DUST PIXEL. `dust.png` is a 3x3 plus: two or
	# three of them read as a small white blob, which is what the user saw.
	# `light_radial` is a soft radial with no pixel grid to break, so it is in
	# the class this project explicitly lets scale and grow (the LZ beacon's
	# ground wash and the freight's steam do the same) — a puff can start
	# tight and billow out the way smoke actually does.
	_dust_tex = load("res://art/gen/light_radial.png")
	_timer = randf_range(2.0, 5.0)


func _process(delta: float) -> void:
	_timer -= delta
	if _timer <= 0.0:
		match _phase:
			0:
				_phase = 1
				_timer = 0.8            # the drag
			1:
				_phase = 2
				_timer = 0.6            # the exhale
				_spawn_wisps()
			2:
				_phase = 0
				_timer = randf_range(2.5, 6.0)
		_sprite.frame = _phase
	var i := _wisps.size() - 1
	while i >= 0:
		var wisp: Dictionary = _wisps[i]
		var sprite := wisp["sprite"] as Sprite2D
		wisp["age"] = float(wisp["age"]) + delta
		var age: float = wisp["age"]
		if age >= WISP_LIFE:
			sprite.queue_free()
			_wisps.remove_at(i)
		elif age >= 0.0:
			# a negative age is the stagger: the wisp hasn't left the
			# exhale yet (they all used to show at once, fully lit)
			sprite.visible = true
			var t := age / WISP_LIFE
			sprite.position += (wisp["drift"] as Vector2) * delta
			# BILLOW. A puff of breath opens out as it rises and thins as it
			# opens — holding one size was most of why it read as a blob.
			#
			# `seed` IS THE SCALE, not a factor of one: light_radial is 256 px,
			# so 0.04 is a 10 px puff and 0.11 is 28 px. Multiplying it by a
			# 0.16..0.46 ramp gave 3 px specks — smaller than the dust pixel
			# this replaced, which is the opposite of the ask.
			var grow: float = float(wisp["seed"]) * (1.0 + 1.6 * t)
			sprite.scale = Vector2(grow, grow)
			# fades in over the first sixth, then thins the rest of the way
			sprite.modulate.a = 0.52 * (1.0 - t) * minf(1.0, t * 6.0)
		i -= 1


func _spawn_wisps() -> void:
	## FOUR OR FIVE, NOT TWO OR THREE, and each on its own line — an exhale is
	## a cloud that comes apart, not a couple of dots on one track (user: the
	## smoke "reads as a small white blob").
	for w in randi_range(4, 5):
		var wisp := Sprite2D.new()
		wisp.texture = _dust_tex
		wisp.modulate = Color("a8b5b2", 0.0)
		wisp.visible = false
		wisp.z_index = 1                       # over his own shoulder
		# he faces down-LEFT, so the breath leaves past that cheek
		wisp.position = Vector2(-5.0 + randf_range(-1.5, 1.5),
			-27.0 + randf_range(-2.0, 1.0))
		add_child(wisp)
		_wisps.append({
			"sprite": wisp,
			"age": -0.18 * w,
			"seed": randf_range(0.038, 0.058),   # 10-15 px puffs, growing to ~26-38
			"drift": Vector2(randf_range(-9.0, -3.0), randf_range(-15.0, -9.0)),
		})
