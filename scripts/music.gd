extends Node
## Music autoload: the main-menu theme, synthesized at runtime like every
## other sound in the game (design doc: no audio files, ever).
##
## The track is dark ambient in A minor, built to the game's mood: a low
## detuned drone that never leaves, slow pad swells cycling a minor
## progression, a lonely echoing motif with long silences, and a breath of
## wind. Rendered ONCE on a background thread at boot (11 kHz — the lo-fi
## haze is part of the sound), then looped seamlessly; pad envelopes reach
## zero at the loop point so it cannot click.

const MRATE := 11025
const SECONDS := 48.0
const CHORD_SECONDS := 6.0

# A minor progression, two bars each of: Am, F, C, Em, Am, F, Em, Am
const CHORDS: Array = [
	[110.0, 130.81, 164.81], [87.31, 110.0, 130.81],
	[130.81, 164.81, 196.0], [82.41, 98.0, 123.47],
	[110.0, 130.81, 164.81], [87.31, 110.0, 130.81],
	[82.41, 98.0, 123.47], [110.0, 130.81, 164.81],
]
# the motif: (start s, length s, freq) — A minor pentatonic, mostly silence.
# Echo copies are baked below.
const MOTIF: Array = [
	[2.0, 1.6, 329.63], [5.0, 0.9, 293.66], [7.0, 2.6, 220.0],
	[14.5, 1.2, 261.63], [17.0, 1.8, 329.63], [20.5, 2.8, 392.0],
	[26.0, 1.4, 329.63], [29.0, 2.4, 220.0],
	[38.0, 1.2, 293.66], [40.5, 1.0, 261.63], [42.0, 3.4, 220.0],
]

var _player: AudioStreamPlayer
var _thread: Thread
var _stream: AudioStreamWAV
var _want_menu := false
var _fade: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_player = AudioStreamPlayer.new()
	_player.volume_db = -60.0
	add_child(_player)
	_thread = Thread.new()
	_thread.start(_render)


func _exit_tree() -> void:
	if _thread != null and _thread.is_started():
		_thread.wait_to_finish()


func play_menu() -> void:
	_want_menu = true
	if _stream != null:
		_start_playing()


func stop_menu(fade_seconds: float = 1.2) -> void:
	_want_menu = false
	if not _player.playing:
		return
	if _fade != null:
		_fade.kill()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", -60.0, fade_seconds)
	_fade.tween_callback(_player.stop)


func _start_playing() -> void:
	if _player.playing:
		return
	_player.stream = _stream
	_player.volume_db = -60.0
	_player.play()
	if _fade != null:
		_fade.kill()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", -16.0, 4.0)


func _on_rendered(stream: AudioStreamWAV) -> void:
	_stream = stream
	if _want_menu:
		_start_playing()


func _render() -> void:
	var count := int(SECONDS * MRATE)
	var data := PackedByteArray()
	data.resize(count * 2)

	# bake motif echoes: +0.55s at -9 dB, +1.1s at -16 dB
	var notes: Array = []
	for n in MOTIF:
		notes.append([n[0], n[1], n[2], 1.0])
		notes.append([n[0] + 0.55, n[1], n[2], 0.36])
		notes.append([n[0] + 1.1, n[1], n[2], 0.16])

	var rng := RandomNumberGenerator.new()
	rng.seed = hash("spoils-menu-theme")
	var wind_prev := 0.0
	var chord_samples := int(CHORD_SECONDS * MRATE)
	for i in count:
		var t := float(i) / MRATE
		# drone: root + a detuned twin, slow beating dread (integer cycles
		# over the loop, so the seam is silent)
		var s := (sin(TAU * 55.0 * t) + sin(TAU * 55.25 * t)) * 0.055
		# pads: current chord swells in and out inside its own window
		var seg := i / chord_samples
		var ts := float(i % chord_samples) / chord_samples
		var pad_env := smoothstep(0.0, 0.3, ts) * (1.0 - smoothstep(0.7, 1.0, ts))
		var chord: Array = CHORDS[mini(seg, CHORDS.size() - 1)]
		for f in chord:
			s += sin(TAU * float(f) * t) * pad_env * 0.030
		# the motif, far away
		for n in notes:
			var nt: float = t - float(n[0])
			if nt >= 0.0 and nt < float(n[1]):
				var env := minf(nt / 0.12, 1.0) * pow(1.0 - nt / float(n[1]), 1.7)
				s += sin(TAU * float(n[2]) * t) * env * 0.075 * float(n[3])
		# wind
		var w := rng.randf_range(-1.0, 1.0) * 0.16 + wind_prev * 0.84
		wind_prev = w
		s += w * 0.040 * (0.7 + 0.3 * sin(TAU * t / 19.0))
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32767.0))

	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = MRATE
	wav.stereo = false
	wav.data = data
	wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
	wav.loop_begin = 0
	wav.loop_end = count
	_on_rendered.call_deferred(wav)
