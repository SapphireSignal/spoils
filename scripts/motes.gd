class_name Motes
extends GPUParticles2D
## Dust hanging in the air. One node that rides the camera, not one per
## lamp — the district has fifty lamps and a particle system on each would
## be fifty systems mostly emitting off-screen for nobody.
##
## It is deliberately faint. The job is to stop the air between the player
## and the buildings reading as empty flat colour; the moment you can point
## at individual specks it has gone too far and it reads as snow.
##
## Uses the existing dust texture. No new art (user: "keep the base art
## as-is, just use godot's visual toolkit").

const COUNT := 46
const SPAN := Vector2(420.0, 300.0)   # emission box, a bit wider than view

var _player: Player


func setup(player: Player) -> void:
	_player = player
	texture = load("res://art/gen/dust.png")
	amount = COUNT
	lifetime = 7.0
	preprocess = 7.0                   # already drifting when you arrive
	randomness = 1.0
	local_coords = false               # motes stay in the world as you walk
	z_index = 6                        # above the ground, under the roofs

	var mat := ParticleProcessMaterial.new()
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	mat.emission_box_extents = Vector3(SPAN.x, SPAN.y, 1.0)
	# a slow drift with a little rise: dust in still air settles, dust in a
	# doorway draught does this
	mat.direction = Vector3(1.0, -0.35, 0.0)
	mat.spread = 40.0
	mat.initial_velocity_min = 3.0
	mat.initial_velocity_max = 11.0
	mat.gravity = Vector3(0.0, -1.5, 0.0)
	mat.damping_min = 0.4
	mat.damping_max = 1.2
	mat.scale_min = 1.0
	mat.scale_max = 1.0                # NEVER scale: the pixel grid (rule 1)
	# fade in and back out so nothing ever pops into or out of existence
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0.0))
	ramp.set_color(1, Color(1, 1, 1, 0.0))
	ramp.add_point(0.22, Color(1, 1, 1, 0.30))
	ramp.add_point(0.72, Color(1, 1, 1, 0.24))
	var ramp_tex := GradientTexture1D.new()
	ramp_tex.gradient = ramp
	mat.color_ramp = ramp_tex
	process_material = mat
	modulate = Color("c7cfcc", 0.5)
	emitting = true


func _process(_delta: float) -> void:
	if _player == null:
		return
	# follow the camera in WHOLE WORLD PIXELS. The emitter is not drawn, but
	# its children are, and a fractional emitter position would hand every
	# mote a fractional spawn point — which is how you get shimmer.
	global_position = _player.global_position.round()
