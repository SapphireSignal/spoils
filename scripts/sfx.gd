extends Node
## Sfx autoload. SUBTLE by direction: quiet, clean, matched to what it's for.
## Since v0.6.13 the organic sounds are licensed recordings (per-surface
## footsteps, thunder — see assets/audio/LICENSES.md); the mechanical ones
## stay synthesized (UI blips, door thunks, sniper crack, flashlight click,
## splash ping, rain bed, car alarm). UI blips auto-wire to every Button.
## Heavy synth streams (rain, alarm) render on a background thread.

const RATE := 44100
const STEP_KINDS := ["concrete", "asphalt", "wood", "grass", "dirt"]
const STEP_VARIANTS := 4
const THUNDER_COUNT := 3

var _hover: AudioStreamWAV
var _press: AudioStreamWAV
var _door_open: AudioStreamWAV
var _door_close: AudioStreamWAV
var _crack: AudioStreamWAV
var _click: AudioStreamWAV
var _splash_ping: AudioStreamWAV
var _steps: Dictionary = {}          # kind -> Array[AudioStream]
var _thunder: Array[AudioStream] = []
var _rain_loop: AudioStreamWAV
var _alarm: AudioStreamWAV
var _car_door_open: AudioStream      # licensed recordings (ggbotnet, cc0)
var _car_door_close: AudioStream
var _car_engine_start: AudioStream
var _car_engine_off: AudioStream
var _car_engine_loop: AudioStreamOggVorbis

var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _step_player: AudioStreamPlayer
var _rain_player: AudioStreamPlayer
var _thunder_player: AudioStreamPlayer
var _heavy_thread: Thread


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS  # UI sounds must work while paused
	_hover = _synth_blip(0.05, 700.0, 940.0, 0.16)
	_press = _synth_blip(0.07, 520.0, 390.0, 0.22)
	_door_open = _synth_blip(0.11, 180.0, 110.0, 0.30)
	_door_close = _synth_blip(0.09, 130.0, 82.0, 0.36)
	_crack = _synth_noise(0.07, 0.34)
	_click = _synth_click()
	_splash_ping = _synth_ping()
	for kind in STEP_KINDS:
		var variants: Array[AudioStream] = []
		for i in STEP_VARIANTS:
			variants.append(load("res://assets/audio/steps/%s_%d.ogg" % [kind, i]))
		_steps[kind] = variants
	for i in THUNDER_COUNT:
		_thunder.append(load("res://assets/audio/thunder_%d.ogg" % i))
	_car_door_open = load("res://assets/audio/car/car_door_open.ogg")
	_car_door_close = load("res://assets/audio/car/car_door_close.ogg")
	_car_engine_start = load("res://assets/audio/car/car_engine_start.ogg")
	_car_engine_off = load("res://assets/audio/car/car_engine_off.ogg")
	_car_engine_loop = load("res://assets/audio/car/car_engine_loop.ogg")
	_car_engine_loop.loop = true
	for i in 4:
		var player := AudioStreamPlayer.new()
		player.volume_db = -8.0
		add_child(player)
		_players.append(player)
	_step_player = AudioStreamPlayer.new()
	add_child(_step_player)
	_rain_player = AudioStreamPlayer.new()
	_rain_player.volume_db = -80.0
	add_child(_rain_player)
	_engine_player = AudioStreamPlayer.new()
	_engine_player.volume_db = -80.0
	add_child(_engine_player)
	_car_player = AudioStreamPlayer.new()
	_car_player.volume_db = -13.0
	add_child(_car_player)
	_thunder_player = AudioStreamPlayer.new()
	add_child(_thunder_player)
	_heavy_thread = Thread.new()
	_heavy_thread.start(_render_heavy)
	get_tree().node_added.connect(_on_node_added)
	_wire_existing(get_tree().root)


func _exit_tree() -> void:
	if _heavy_thread != null and _heavy_thread.is_started():
		_heavy_thread.wait_to_finish()


# ---------------------------------------------------------------- playback --

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


func play_splash_ping(quiet: bool = false) -> void:
	var player := _players[_next]
	_next = (_next + 1) % _players.size()
	player.volume_db = -14.0 if quiet else -10.0
	player.stream = _splash_ping
	player.play()


func play_step(kind: String, quiet: bool) -> void:
	var variants: Array = _steps.get(kind, _steps.get("concrete", []))
	if variants.is_empty():
		return
	_step_player.volume_db = -27.0 if quiet else -22.0  # subtle, always
	                                                    # (user: never loud)
	_step_player.pitch_scale = randf_range(0.95, 1.05)  # no two steps alike
	_step_player.stream = variants[randi() % variants.size()]
	_step_player.play()


func play_thunder() -> void:
	if _thunder.is_empty():
		return
	_thunder_player.volume_db = randf_range(-22.0, -16.0)  # subtle, always
	                                                       # (user: rain down
	                                                       # a step, thunder
	                                                       # up a hair)
	_thunder_player.stream = _thunder[randi() % _thunder.size()]
	_thunder_player.play()


var _rain_db := -60.0

func set_rain(intensity: float) -> void:
	if _rain_loop == null:
		return
	var want_on := intensity > 0.02
	# SLEWED gain: the wash always fades in from silence and out to silence
	# (it used to pop in mid-level when a storm was already rolling), and a
	# touch quieter overall (user call)
	var target := -60.0
	if want_on:
		target = lerpf(-52.0, -37.0, clampf(intensity, 0.0, 1.0))
	_rain_db = move_toward(_rain_db, target, get_process_delta_time() * 6.0)
	if want_on and not _rain_player.playing:
		_rain_db = -60.0
		_rain_player.stream = _rain_loop
		_rain_player.play()
	elif not want_on and _rain_player.playing and _rain_db <= -58.0:
		_rain_player.stop()
	if _rain_player.playing:
		# slow non-loop-aligned drift so nothing reads as a repeating pattern
		var drift := sin(Time.get_ticks_msec() / 1000.0 * TAU / 13.7) * 1.5
		_rain_player.volume_db = _rain_db + drift


var _engine_player: AudioStreamPlayer
var _car_player: AudioStreamPlayer
var _engine_db := -60.0

func play_car_door(open: bool) -> void:
	# STANDING RULE (user, after asking for the third time): every NEW
	# sound ships QUIET first — organic/mechanical one-shots start at
	# -18 dB or below and only come up if the user asks
	_car_player.volume_db = -19.0
	_car_player.stream = _car_door_open if open else _car_door_close
	_car_player.play()


func play_engine_start() -> void:
	_car_player.volume_db = -18.0
	_car_player.stream = _car_engine_start
	_car_player.play()


func play_engine_off() -> void:
	_car_player.volume_db = -19.0
	_car_player.stream = _car_engine_off
	_car_player.play()


func set_engine(intensity: float) -> void:
	# the driving bed: quiet rumble that follows the throttle, slewed like
	# the rain wash so it never pops (subtle always — user taste)
	var want_on := intensity > 0.02
	var target := -60.0
	if want_on:
		target = lerpf(-38.0, -28.0, clampf(intensity, 0.0, 1.0))
	_engine_db = move_toward(_engine_db, target, get_process_delta_time() * 8.0)
	if want_on and not _engine_player.playing:
		_engine_db = -60.0
		_engine_player.stream = _car_engine_loop
		_engine_player.play()
	elif not want_on and _engine_player.playing and _engine_db <= -58.0:
		_engine_player.stop()
	if _engine_player.playing:
		_engine_player.volume_db = _engine_db
		_engine_player.pitch_scale = 0.9 + 0.35 * clampf(intensity, 0.0, 1.0)


func alarm_stream() -> AudioStreamWAV:
	return _alarm  # null until the background render lands — callers skip


func _play(stream: AudioStreamWAV) -> void:
	var player := _players[_next]
	_next = (_next + 1) % _players.size()
	player.volume_db = -8.0
	player.stream = stream
	player.play()


func _wire_existing(node: Node) -> void:
	_on_node_added(node)
	for child in node.get_children():
		_wire_existing(child)


func _on_node_added(node: Node) -> void:
	if node is Button:
		node.mouse_entered.connect(play_hover)
		node.focus_entered.connect(play_hover)
		node.pressed.connect(play_press)


# --------------------------------------------------------------- synthesis --

func _wav(data: PackedByteArray, loop_frames: int = 0) -> AudioStreamWAV:
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = RATE
	wav.stereo = false
	wav.data = data
	if loop_frames > 0:
		wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
		wav.loop_begin = 0
		wav.loop_end = loop_frames
	return wav


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
	return _wav(data)


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
	return _wav(data)


func _synth_ping() -> AudioStreamWAV:
	## The signal ping: a soft sonar tone with a long gentle tail.
	var count := int(0.9 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var phase := 0.0
	for i in count:
		var t := float(i) / count
		phase += TAU * lerpf(660.0, 648.0, t) / RATE
		var env := minf(float(i) / (0.008 * RATE), 1.0) * pow(1.0 - t, 2.8)
		var s := (sin(phase) + 0.2 * sin(phase * 2.001)) * env * 0.22
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	return _wav(data)


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
	return _wav(data)


func _render_heavy() -> void:
	## Background render: the rain bed and the car alarm (thunder is a
	## licensed field recording now, loaded in _ready like the footsteps).
	var rain := _synth_rain_bed()
	var alarm := _synth_alarm()
	_apply_heavy.call_deferred(rain, alarm)


func _apply_heavy(rain: AudioStreamWAV, alarm: AudioStreamWAV) -> void:
	_rain_loop = rain
	_alarm = alarm


func _synth_rain_bed() -> AudioStreamWAV:
	## A pure smooth distant wash — no pops, no texture that could read as
	## repetition (user: "just normal rain, very subtle"). 8 s of doubly
	## lowpassed noise; any loop seam in that is inaudible.
	var count := int(8.0 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-rainbed")
	var lp1 := 0.0
	var lp2 := 0.0
	for i in count:
		var n := rng.randf_range(-1.0, 1.0)
		lp1 = n * 0.18 + lp1 * 0.82
		lp2 = lp1 * 0.18 + lp2 * 0.82
		data.encode_s16(i * 2, int(clampf(lp2 * 0.9, -1.0, 1.0) * 32767.0))
	return _wav(data, count)


func _synth_alarm() -> AudioStreamWAV:
	## Two-tone car alarm, 3 seconds, small and non-obnoxious. Every pulse
	## has a real attack/release ramp — hard gating clicked ("static").
	var count := int(3.0 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var phase := 0.0
	for i in count:
		var t := float(i) / count
		var cycle := fmod(t * 3.2, 1.0)
		var freq := 700.0 if cycle < 0.5 else 540.0
		phase += TAU * freq / RATE
		var pt := fmod(cycle, 0.5) / 0.5  # position inside this pulse window
		var pulse := smoothstep(0.0, 0.12, pt) * (1.0 - smoothstep(0.72, 0.92, pt))
		var fade := minf(t / 0.08, 1.0) * minf((1.0 - t) / 0.2, 1.0)
		var s := sin(phase) * pulse * fade * 0.15
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	return _wav(data)
