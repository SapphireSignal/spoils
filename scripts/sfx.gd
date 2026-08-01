extends Node
## Sfx autoload: runtime-synthesized sounds (design doc: no audio files, ever).
## The first sounds in the game are UI blips. Every Button in the tree gets
## auto-wired for hover/press via the SceneTree node_added signal, so menus
## never wire audio by hand.

const RATE := 44100

var _hover: AudioStreamWAV
var _press: AudioStreamWAV
var _door_open: AudioStreamWAV
var _door_close: AudioStreamWAV
var _crack: AudioStreamWAV
var _click: AudioStreamWAV
var _players: Array[AudioStreamPlayer] = []
var _next := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS  # UI sounds must work while paused
	_hover = _synth_blip(0.05, 700.0, 940.0, 0.16)
	_press = _synth_blip(0.07, 520.0, 390.0, 0.22)
	_door_open = _synth_blip(0.11, 180.0, 110.0, 0.30)
	_door_close = _synth_blip(0.09, 130.0, 82.0, 0.36)
	_crack = _synth_noise(0.07, 0.34)
	_click = _synth_click()
	for i in 4:
		var player := AudioStreamPlayer.new()
		player.volume_db = -8.0
		add_child(player)
		_players.append(player)
	get_tree().node_added.connect(_on_node_added)
	_wire_existing(get_tree().root)


func play_hover() -> void:
	_play(_hover)


func play_press() -> void:
	_play(_press)


func play_door(open: bool) -> void:
	_play(_door_open if open else _door_close)


func play_crack() -> void:
	_play(_crack)


func play_click() -> void:
	_play(_click)


func _wire_existing(node: Node) -> void:
	_on_node_added(node)
	for child in node.get_children():
		_wire_existing(child)


func _on_node_added(node: Node) -> void:
	if node is Button:
		node.mouse_entered.connect(play_hover)
		node.focus_entered.connect(play_hover)
		node.pressed.connect(play_press)


func _play(stream: AudioStreamWAV) -> void:
	var player := _players[_next]
	_next = (_next + 1) % _players.size()
	player.stream = stream
	player.play()


func _synth_blip(duration: float, freq_from: float, freq_to: float, amp: float) -> AudioStreamWAV:
	## Soft sine chirp: 4ms attack, smooth squared decay, one gentle overtone.
	var count := int(duration * RATE)
	var attack := int(0.004 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var phase := 0.0
	for i in count:
		var t := float(i) / count
		phase += TAU * lerpf(freq_from, freq_to, t) / RATE
		var env := minf(float(i) / attack, 1.0) * pow(1.0 - t, 2.2)
		var s := (sin(phase) + 0.15 * sin(phase * 2.0)) * env * amp
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = RATE
	wav.stereo = false
	wav.data = data
	return wav


func _synth_click() -> AudioStreamWAV:
	## A dry mechanical CLICK (flashlight switch): one sharp impulse with an
	## instant decay and a faint metallic ping — no musical chirp.
	var count := int(0.018 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-click")
	for i in count:
		var t := float(i) / count
		var env := pow(1.0 - t, 6.0)
		var s := rng.randf_range(-1.0, 1.0) * 0.5 * env
		s += 0.25 * sin(TAU * 1800.0 * float(i) / RATE) * env * env
		data.encode_s16(i * 2, int(clampf(s * 0.5, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = RATE
	wav.stereo = false
	wav.data = data
	return wav


func _synth_noise(duration: float, amp: float) -> AudioStreamWAV:
	## Sharp filtered noise burst — the sniper's distant crack.
	var count := int(duration * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-crack")
	var prev := 0.0
	for i in count:
		var t := float(i) / count
		var env := minf(float(i) / (0.002 * RATE), 1.0) * pow(1.0 - t, 3.0)
		var n := rng.randf_range(-1.0, 1.0)
		var s := (n * 0.6 + prev * 0.4) * env * amp  # one-pole lowpass takes the hiss off
		prev = n
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = RATE
	wav.stereo = false
	wav.data = data
	return wav
