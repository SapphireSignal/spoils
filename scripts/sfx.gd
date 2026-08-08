extends Node
## Sfx autoload. SUBTLE by direction: quiet, clean, matched to what it's for.
## Since v0.2.11 the organic sounds are licensed recordings (per-surface
## footsteps, thunder — see assets/audio/LICENSES.md); the mechanical ones
## stay synthesized (UI blips, door thunks, sniper crack, flashlight click,
## splash ping, rain bed, car alarm). THE ONE EXCEPTION is the car doors and
## engine, which are recordings too (ggbotnet, cc0 — see _car_* below); this
## comment used to omit them. UI blips auto-wire to every Button.
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

## how open the weather sounds. Outdoors is effectively unfiltered; indoors
## the wall eats the top end, which is what "muffled" actually is.
const OUTDOOR_CUTOFF := 20000.0
## RAISED 2026-08-06 (user: "the muffled rain i can barely hear, increase the
## volume a bit for it"). Indoors was losing BOTH ends at once - a -7 dB duck
## on top of a 1250 Hz cutoff that already removes most of rain's energy - so
## it fell under the room tone. The cutoff is what makes it read as "through a
## wall", so that keeps most of its work (1250 -> 1600) and the duck, which
## was only stacking loss on loss, comes back to -3.
const INDOOR_CUTOFF := 1600.0
const INDOOR_DUCK_DB := -3.0
const MUFFLE_SPEED := 3.5        # per second — a doorway is a fast fade, but
                                 # never an instant switch

var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _step_player: AudioStreamPlayer
var _rain_player: AudioStreamPlayer
var _weather_bus := -1
var _weather_lowpass: AudioEffectLowPassFilter
var _indoor := 0.0               # 0 outside .. 1 fully inside
var _indoor_want := 0.0
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
	# every player routes through a mix bus (volume panel, user call):
	# one-shots and steps are "sfx", the weather/engine beds "ambient"
	for i in 4:
		var player := AudioStreamPlayer.new()
		player.volume_db = -8.0
		player.bus = "sfx"
		add_child(player)
		_players.append(player)
	_step_player = AudioStreamPlayer.new()
	_step_player.bus = "sfx"
	add_child(_step_player)
	# WEATHER GETS ITS OWN BUS so it can be muffled from indoors (user).
	# Rain and thunder only — NOT the whole sfx group: your own footsteps
	# and the door beside you are not muffled by the wall you are stood
	# behind, and dulling those would just sound broken.
	var weather_bus := AudioServer.bus_count
	AudioServer.add_bus(weather_bus)
	AudioServer.set_bus_name(weather_bus, "weather")
	AudioServer.set_bus_send(weather_bus, "ambient")
	_weather_lowpass = AudioEffectLowPassFilter.new()
	_weather_lowpass.cutoff_hz = OUTDOOR_CUTOFF
	AudioServer.add_bus_effect(weather_bus, _weather_lowpass)
	_weather_bus = weather_bus

	_rain_player = AudioStreamPlayer.new()
	_rain_player.volume_db = -80.0
	_rain_player.bus = "weather"
	add_child(_rain_player)
	_engine_player = AudioStreamPlayer.new()
	_engine_player.volume_db = -80.0
	add_child(_engine_player)
	# the engine bed gets its own low-passed bus: at speed the loop plays
	# pitched up and the recording's hiss climbs into earshot ("static at
	# full speed" — user report). The filter keeps only the engine body.
	var engine_bus := AudioServer.bus_count
	AudioServer.add_bus(engine_bus)
	AudioServer.set_bus_name(engine_bus, "engine")
	# the engine bed is an ambient loop: it rides the ambient mix group
	AudioServer.set_bus_send(engine_bus, "ambient")
	var lowpass := AudioEffectLowPassFilter.new()
	lowpass.cutoff_hz = 5200.0
	AudioServer.add_bus_effect(engine_bus, lowpass)
	_engine_player.bus = "engine"
	_car_player = AudioStreamPlayer.new()
	_car_player.volume_db = -13.0
	_car_player.bus = "sfx"
	add_child(_car_player)
	_bump_player = AudioStreamPlayer.new()
	_bump_player.bus = "sfx"
	add_child(_bump_player)
	_car_bump = _synth_bump()
	_horn_player = AudioStreamPlayer.new()
	_horn_player.bus = "sfx"
	add_child(_horn_player)
	_horn = _synth_horn()
	_radio_open = _synth_squelch(true)
	_radio_close = _synth_squelch(false)
	_thunder_player = AudioStreamPlayer.new()
	_thunder_player.bus = "weather"
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


func play_click(quiet: bool = false) -> void:
	_play(_click, -20.0 if quiet else -8.0)


func play_radio_tick() -> void:
	## mara keying up. DELIBERATELY tiny (user: "a really subtle sound
	## effect") — the old squelch was too much and got cut entirely in
	## v0.4.14. Nothing plays when the call drops off.
	_play(_click, -30.0)


func play_bird_flush(_at: Vector2) -> void:
	## Wings clattering out of a tree. QUIET ON FIRST CUT, per the standing
	## rule that every new sound ships at or under -18 dB and only comes up on
	## ask — and a startle that is louder than a footstep would read as a
	## threat rather than as scenery.
	_play(_click, -26.0)


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
var _engine_pitch := 1.0
var _bump_player: AudioStreamPlayer
var _car_bump: AudioStreamWAV
var _horn_player: AudioStreamPlayer
var _horn: AudioStreamWAV
var _radio_open: AudioStreamWAV
var _radio_close: AudioStreamWAV
var _engine_target := 0.0   # intensity 0..1; Sfx slews it DOWN on its own
                            # (the loop once played forever after an exit —
                            # nobody was calling set_engine anymore)

func play_car_door(open: bool) -> void:
	# STANDING RULE (user, after asking for the third time): every NEW
	# sound ships QUIET first — organic/mechanical one-shots start at
	# -18 dB or below and only come up if the user asks
	_car_player.volume_db = -19.0
	_car_player.stream = _car_door_open if open else _car_door_close
	_car_player.play()


func play_car_bump(intensity: float) -> void:
	# a car meeting something it shouldn't — subtle always (standing
	# rule): -22 dB scrape up to -18 dB flat-out, tiny pitch spread
	_bump_player.volume_db = lerpf(-22.0, -18.0, clampf(intensity, 0.0, 1.0))
	_bump_player.pitch_scale = randf_range(0.92, 1.08)
	_bump_player.stream = _car_bump
	_bump_player.play()


func play_engine_start() -> void:
	# QUIETER (user, 2026-08-06: "decrease the engine sound, its too loud ...
	# like the engine startup sound ... for the vehicles"). It sat at the -18 dB
	# ceiling the standing quiet rule sets for one-shots, which was already the
	# loudest a new sound may ship at - and then v0.6.66 put +3 dB on the master
	# for everything, which pushed it over. Dropped 6 dB, so it lands below
	# where it was even before that trim.
	_car_player.volume_db = -24.0
	_car_player.stream = _car_engine_start
	_car_player.play()


func play_engine_off() -> void:
	# matched to the start, keeping the 1 dB it always sat below it
	_car_player.volume_db = -25.0
	_car_player.stream = _car_engine_off
	_car_player.play()


func set_engine(intensity: float) -> void:
	# callers just declare the throttle; the slew/stop lives in _process so
	# the bed ALWAYS winds down even if the caller goes quiet
	_engine_target = clampf(intensity, 0.0, 1.0)
	if _engine_target > 0.02 and not _engine_player.playing:
		_engine_db = -60.0
		_engine_player.stream = _car_engine_loop
		_engine_player.play()


func set_indoors(inside: bool) -> void:
	## main.gd already knows which interior cells the player is standing in
	## (it drives the roof reveal off the same test), so this just follows it.
	_indoor_want = 1.0 if inside else 0.0


func _process(delta: float) -> void:
	# the weather muffle, eased so a doorway is a quick fade and never a
	# switch — audio that snaps reads as a bug even when it is correct
	if _weather_bus >= 0 and not is_equal_approx(_indoor, _indoor_want):
		_indoor = move_toward(_indoor, _indoor_want, delta * MUFFLE_SPEED)
		_weather_lowpass.cutoff_hz = lerpf(OUTDOOR_CUTOFF, INDOOR_CUTOFF,
			_indoor)
		AudioServer.set_bus_volume_db(_weather_bus, INDOOR_DUCK_DB * _indoor)
	if _engine_player == null or not _engine_player.playing:
		return
	var want_on := _engine_target > 0.02
	var target := -60.0
	if want_on:
		target = lerpf(-38.0, -28.0, _engine_target)
	_engine_db = move_toward(_engine_db, target, delta * 8.0)
	if not want_on and _engine_db <= -58.0:
		_engine_player.stop()
		return
	_engine_player.volume_db = _engine_db
	# pitch follows the throttle SMOOTHLY, capped lower: per-frame
	# pitch_scale micro-jumps zipper into crackle at 240 Hz (the "static"
	# at full speed), and the higher the pitch the harsher the loop
	var want_pitch := 0.9 + 0.26 * _engine_target
	_engine_pitch = move_toward(_engine_pitch, want_pitch, delta * 0.5)
	# APPLIED EVERY FRAME, WITH NO THRESHOLD - and the threshold is what this
	# fixes. Guarding the write with `> 0.004` HELD the pitch and then jumped
	# it by a whole 0.004, roughly 120 times a second at 240 Hz. That is a
	# staircase, and a staircase is precisely what zippers: it traded many
	# tiny rate changes for fewer, BIGGER discontinuities. A continuous ramp of
	# ~0.002 per frame resamples smoothly.
	#
	# User: "i can hear some sort of static like very subtle static sometimes
	# when im driving". The earlier pass named the same symptom and slowed the
	# slew; the residual was the guard it added.
	_engine_player.pitch_scale = _engine_pitch


func silence_world() -> void:
	## Cut every looping world bed at once. Both of these are driven per
	## frame from the raid scene, so when that scene goes away there is
	## nobody left to slew them down and they just keep playing.
	_engine_target = 0.0
	_engine_db = -60.0
	if _engine_player != null:
		_engine_player.stop()
	_rain_db = -60.0
	if _rain_player != null:
		_rain_player.stop()
	# thunder is a multi-second ONE-SHOT on this same persistent node, so a
	# strike a few seconds before you extract kept rolling over the menu
	# theme. environment_system already guards the DEFERRED half of a
	# strike; this covers the clap already in flight. The hard stop lands on
	# the black scene-swap cut at -22..-16 dB, so it is inaudible.
	if _thunder_player != null:
		_thunder_player.stop()


func alarm_stream() -> AudioStreamWAV:
	return _alarm  # null until the background render lands — callers skip


func _play(stream: AudioStreamWAV, db: float = -8.0) -> void:
	var player := _players[_next]
	_next = (_next + 1) % _players.size()
	player.volume_db = db
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


func play_radio(open: bool) -> void:
	## The mic keying up and keying down. This is what actually sells a
	## radio — the squelch either side of the words, not the words.
	_bump_player.volume_db = -24.0
	_bump_player.pitch_scale = 1.0 if open else 0.88
	_bump_player.stream = _radio_open if open else _radio_close
	_bump_player.play()


func _synth_squelch(open: bool) -> AudioStreamWAV:
	## Key-up is a short rising hiss that snaps into carrier; key-down is
	## the carrier dropping out with a click and a tail of static.
	var count := int((0.13 if open else 0.17) * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-squelch-%s" % str(open))
	var lp := 0.0
	for i in count:
		var t := float(i) / count
		var n := rng.randf_range(-1.0, 1.0)
		lp = n * 0.35 + lp * 0.65          # band-limited: radio, not white
		var env := 0.0
		if open:
			# hiss swells, then the carrier clamps it
			env = smoothstep(0.0, 0.45, t) * (1.0 - smoothstep(0.55, 1.0, t))
		else:
			# a click, then the hiss falls away
			env = pow(1.0 - t, 2.2)
			if i < int(0.004 * RATE):
				env = 1.0
		var s := lp * env * 0.5
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	return _wav(data)


func _synth_horn() -> AudioStreamWAV:
	## A freight horn, two tones a fifth apart, heard across a district —
	## still quiet by this game's rules, just LONG.
	var count := int(1.6 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var p1 := 0.0
	var p2 := 0.0
	for i in count:
		var t := float(i) / count
		p1 += TAU * 138.0 / RATE
		p2 += TAU * 207.0 / RATE
		var env := minf(t / 0.06, 1.0) * (1.0 - smoothstep(0.6, 1.0, t))
		var s := (sin(p1) * 0.6 + sin(p2) * 0.4
			+ 0.18 * sin(p1 * 2.0)) * env * 0.3
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
	return _wav(data)


func play_horn() -> void:
	_horn_player.volume_db = -21.0     # distant, per the standing rule
	_horn_player.stream = _horn
	_horn_player.play()


func _synth_bump() -> AudioStreamWAV:
	## A dull body thump with a hint of metal rattle — short, soft, never
	## a movie crash (user: "really subtle").
	var count := int(0.16 * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-carbump")
	var phase := 0.0
	var prev := 0.0
	for i in count:
		var t := float(i) / count
		var env := minf(float(i) / (0.003 * RATE), 1.0) * pow(1.0 - t, 2.6)
		phase += TAU * lerpf(96.0, 54.0, t) / RATE
		var body := sin(phase) * 0.8
		var n := rng.randf_range(-1.0, 1.0)
		var rattle := (n * 0.5 + prev * 0.5) * 0.35 * pow(1.0 - t, 5.0)
		prev = n
		var s := (body + rattle) * env * 0.5
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))
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
