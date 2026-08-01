class_name CarAlarms
extends Node
## Dynamic car alarms. Half of the INTACT vehicles are armed (rolled at
## build); walking up to one sets it off — a short two-tone alarm from the
## car itself and its baked light pixels flashing amber — for three seconds.
## Each car can only ever fire once, until the raider dies and re-enters.
## Broken-into cars were stripped long ago; they never alarm.

const TRIGGER_DIST := 70.0
const FLASH_SECONDS := 3.0
const BLINK_PERIOD := 0.3

var _entries: Array[Dictionary] = []   # {node, lights, fired}
var _active: Array[Dictionary] = []    # {sprites, until}
var _player: Player
var _time := 0.0
var _light_tex: Texture2D


func _ready() -> void:
	_light_tex = load("res://art/gen/alarm_light.png")
	add_to_group("car_alarms")


func disarm(car: Node2D) -> void:
	# climbing into your own ride ends the argument — permanently
	for entry in _entries:
		if entry["node"] == car:
			entry["fired"] = true


func register(car: Node2D, lights: Array) -> void:
	_entries.append({"node": car, "lights": lights, "fired": false})


func setup(player: Player) -> void:
	_player = player
	player.died.connect(_rearm)


func _rearm() -> void:
	# death resets the district's nerves — every armed car can fire again
	# (except one you already claimed and are still sitting in)
	for entry in _entries:
		var car := entry["node"] as Node2D
		if car is DriveableCar and (car as DriveableCar).driven:
			continue
		entry["fired"] = false


func _process(delta: float) -> void:
	_time += delta
	if not _player.dead:
		var ppos := _player.global_position
		for entry in _entries:
			if entry["fired"]:
				continue
			var car := entry["node"] as Node2D
			if car.global_position.distance_squared_to(ppos) \
					< TRIGGER_DIST * TRIGGER_DIST:
				entry["fired"] = true
				_fire(car, entry["lights"] as Array)

	var blink_on := fmod(_time, BLINK_PERIOD) < BLINK_PERIOD * 0.5
	var night := 0.0
	var environment := get_tree().get_first_node_in_group("environment")
	if environment != null:
		night = float(environment.get("night_amount"))
	var i := _active.size() - 1
	while i >= 0:
		var active: Dictionary = _active[i]
		var done: bool = _time >= float(active["until"])
		for s in (active["sprites"] as Array):
			var sprite := s as Sprite2D
			if is_instance_valid(sprite):
				if done:
					sprite.queue_free()
				else:
					sprite.visible = blink_on
		for g in (active["glows"] as Array):
			var glow := g as PointLight2D
			if is_instance_valid(glow):
				if done:
					glow.queue_free()
				else:
					# at night the flashers actually THROW light (user call)
					glow.enabled = blink_on and night > 0.35
					glow.energy = 0.55 * night
		if done:
			_active.remove_at(i)
		i -= 1


func _fire(car: Node2D, lights: Array) -> void:
	var stream := Sfx.alarm_stream()
	if stream != null:
		var audio := AudioStreamPlayer2D.new()
		audio.stream = stream
		audio.max_distance = 900.0
		audio.volume_db = -14.0   # quieter (user; the standing sound rule)
		car.add_child(audio)
		audio.play()
		audio.finished.connect(audio.queue_free)
	var sprites: Array = []
	var glows: Array = []
	for l in lights:
		var dot := Sprite2D.new()
		dot.texture = _light_tex
		dot.position = Vector2(float(l[0]), float(l[1]))
		dot.z_index = 1
		dot.visible = false
		car.add_child(dot)
		sprites.append(dot)
		var glow := PointLight2D.new()
		glow.texture = load("res://art/gen/light_radial.png")
		glow.position = dot.position
		glow.color = Color("de9e41")
		glow.texture_scale = 0.5
		glow.enabled = false
		car.add_child(glow)
		glows.append(glow)
	_active.append({"sprites": sprites, "glows": glows,
		"until": _time + FLASH_SECONDS})
