class_name Foliage
extends Node
## Bushes the player pushes through: they wiggle, go half-transparent,
## and give a soft leaf-brush sound on entry (user: "little things like
## that"). The wiggle is a whole-pixel ±1 toggle — never subpixel, never
## rotation, so the grid stays clean. Registered by the builder via
## main.gd, driven at render rate.

const RADIUS := 24.0                  # scaled with the BIG hide-in bushes
                                      # (they're cover now, not garnish)

var _bushes: Array[Dictionary] = []   # {node, sprite, base_x, inside, settle}
var _player: Player


func setup(player: Player) -> void:
	_player = player


func register(node: Node2D) -> void:
	for child in node.get_children():
		if child is Sprite2D:
			_bushes.append({"node": node, "sprite": child,
				"base_x": (child as Sprite2D).position.x,
				"inside": false, "settle": 0.0})
			return


func _process(delta: float) -> void:
	var p := _player.global_position
	for b in _bushes:
		var node := b["node"] as Node2D
		var sprite := b["sprite"] as Sprite2D
		var inside: bool = not _player.dead \
			and node.global_position.distance_squared_to(p) < RADIUS * RADIUS
		if inside and not b["inside"]:
			Sfx.play_step("grass", true)     # a soft brush of leaves
		if not inside and b["inside"]:
			b["settle"] = 0.5                # rustles a moment after you leave
		b["inside"] = inside
		sprite.modulate.a = move_toward(sprite.modulate.a,
			0.5 if inside else 1.0, delta * 4.0)
		# the wiggle runs the WHOLE time you're in the clump (user: "the
		# bushs wiggle when you go on them" — the old half-second on entry
		# read as nothing at all), whole pixels only
		var shaking: bool = inside or float(b["settle"]) > 0.0
		if not inside:
			b["settle"] = maxf(0.0, float(b["settle"]) - delta)
		if shaking:
			var offset := 1.0 if fmod(Engine.get_process_frames() / 6.0, 2.0) < 1.0 else -1.0
			sprite.position.x = float(b["base_x"]) + offset
		elif sprite.position.x != float(b["base_x"]):
			sprite.position.x = float(b["base_x"])
