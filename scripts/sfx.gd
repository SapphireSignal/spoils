extends Node
## Sfx autoload: runtime-synthesized sounds (design doc: no audio files, ever).
## UI blips auto-wire to every Button. World sounds are SUBTLE by direction:
## quiet, clean, and matched to what they're for — per-surface footsteps,
## door thunks, the sniper's crack, thunder rolling in after lightning, a soft
## rain bed, and short two-tone car alarms. Heavy streams (thunder, rain,
## alarm) render on a background thread so boot never waits on them.

const RATE := 44100

var _hover: AudioStreamWAV
var _press: AudioStreamWAV
var _door_open: AudioStreamWAV
var _door_close: AudioStreamWAV
var _crack: AudioStreamWAV
var _click: AudioStreamWAV
var _splash_ping: AudioStreamWAV
var _steps: Dictionary = {}          # kind -> Array[AudioStreamWAV]
var _thunder: Array[AudioStreamWAV] = []
var _rain_loop: AudioStreamWAV
var _alarm: AudioStreamWAV

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
	_synth_steps()
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
	_step_player.volume_db = -24.0 if quiet else -18.0  # subtle, always
	_step_player.pitch_scale = randf_range(0.95, 1.05)  # no two steps alike
	_step_player.stream = variants[randi() % variants.size()]
	_step_player.play()


func play_thunder() -> void:
	if _thunder.is_empty():
		return
	_thunder_player.volume_db = randf_range(-18.0, -12.0)
	_thunder_player.stream = _thunder[randi() % _thunder.size()]
	_thunder_player.play()


func set_rain(intensity: float) -> void:
	if _rain_loop == null:
		return
	if intensity <= 0.02:
		if _rain_player.playing:
			_rain_player.stop()
		return
	if not _rain_player.playing:
		_rain_player.stream = _rain_loop
		_rain_player.play()
	# VERY subtle, with a slow non-loop-aligned drift so nothing about it
	# ever reads as a repeating pattern
	var drift := sin(Time.get_ticks_msec() / 1000.0 * TAU / 13.7) * 1.5
	_rain_player.volume_db = lerpf(-46.0, -30.0, clampf(intensity, 0.0, 1.0)) + drift


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


func _synth_steps() -> void:
	## Per-surface footsteps, two variants each — each surface built with its
	## OWN recipe so they are unmistakably different (user report: too samey):
	## concrete = crisp dry tick; asphalt = low dull thud; wood = hollow
	## two-tone knock; grass = a slow soft brush; dirt = a grainy crunch.
	for kind in ["concrete", "asphalt", "wood", "grass", "dirt"]:
		var variants: Array[AudioStreamWAV] = []
		for v in 2:
			variants.append(_synth_step_kind(kind, v))
		_steps[kind] = variants


func _synth_step_kind(kind: String, variant: int) -> AudioStreamWAV:
	var dur := 0.045
	match kind:
		"asphalt": dur = 0.06
		"wood": dur = 0.12
		"grass": dur = 0.10
		"dirt": dur = 0.075
	var count := int(dur * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-step-%s-%d" % [kind, variant])
	var lp1 := 0.0
	var lp2 := 0.0
	for i in count:
		var t := float(i) / count
		var n := rng.randf_range(-1.0, 1.0)
		var s := 0.0
		match kind:
			"concrete":  # bright dry tick, over instantly
				var env := minf(float(i) / (0.0015 * RATE), 1.0) * pow(1.0 - t, 5.0)
				s = n * 0.65 * env + sin(TAU * 2300.0 * float(i) / RATE) * 0.10 * env * env
			"asphalt":   # low dull thud with a little grit
				lp1 = n * 0.4 + lp1 * 0.6
				var env := minf(float(i) / (0.002 * RATE), 1.0) * pow(1.0 - t, 4.0)
				s = lp1 * 0.4 * env + sin(TAU * 105.0 * float(i) / RATE) * 0.35 * env
			"wood":      # hollow knock: two low resonances ringing briefly
				var env := minf(float(i) / (0.0015 * RATE), 1.0) * pow(1.0 - t, 2.4)
				s = (sin(TAU * 165.0 * float(i) / RATE) * 0.55
					+ sin(TAU * 332.0 * float(i) / RATE) * 0.28) * env
				if t < 0.07:
					s += n * 0.25 * (1.0 - t / 0.07)
			"grass":     # a brush, not a tap: slow swell, deeply softened
				lp1 = n * 0.15 + lp1 * 0.85
				lp2 = lp1 * 0.15 + lp2 * 0.85
				var env := smoothstep(0.0, 0.3, t) * (1.0 - smoothstep(0.35, 1.0, t))
				s = lp2 * 1.5 * env
			"dirt":      # grainy crunch: three little crush bursts inside
				lp1 = n * 0.45 + lp1 * 0.55
				var env := pow(1.0 - t, 3.0)
				var grain := 1.0
				for g in [0.08, 0.3, 0.55]:
					if absf(t - float(g)) < 0.05:
						grain = 1.9
				s = lp1 * 0.4 * env * grain
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	return _wav(data)


func _render_heavy() -> void:
	## Background render: thunder rolls, the rain bed, the car alarm.
	var thunder_a := _synth_thunder("a", 1.7, 0.30)
	var thunder_b := _synth_thunder("b", 2.2, 0.24)
	var rain := _synth_rain_bed()
	var alarm := _synth_alarm()
	_apply_heavy.call_deferred(thunder_a, thunder_b, rain, alarm)


func _apply_heavy(a: AudioStreamWAV, b: AudioStreamWAV, rain: AudioStreamWAV,
		alarm: AudioStreamWAV) -> void:
	_thunder = [a, b]
	_rain_loop = rain
	_alarm = alarm


func _synth_thunder(seed_text: String, duration: float, amp: float) -> AudioStreamWAV:
	## A crack into a rolling low rumble — brown noise with a slow envelope.
	var count := int(duration * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-thunder-" + seed_text)
	var brown := 0.0
	for i in count:
		var t := float(i) / count
		brown = clampf(brown + rng.randf_range(-1.0, 1.0) * 0.08, -1.0, 1.0)
		var env := pow(1.0 - t, 1.6)
		var s := brown * env * amp
		if t < 0.05:  # the initial crack
			s += rng.randf_range(-1.0, 1.0) * (0.05 - t) * 6.0 * amp
		var wobble := 0.75 + 0.25 * sin(t * 23.0 + float(seed_text.hash() % 7))
		data.encode_s16(i * 2, int(clampf(s * wobble, -1.0, 1.0) * 32767.0))
	return _wav(data)


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
