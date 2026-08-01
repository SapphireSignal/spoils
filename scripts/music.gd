extends Node
## Music autoload. Licensed loops from "The Last" pack by DavidKBD
## (CC-BY 4.0, assets/audio/LICENSES.md). Two moods, one player:
##  - menu: the guitar theme, looping under the menu.
##  - raid: the user's three picked tracks (guitar 02 / harp 01 /
##    piano 01) rotating CONTINUOUSLY from raid start until death —
##    random order, never the same track twice in a row, only a short
##    breath between them (user call).
## Contract: play_menu()/stop_menu()/play_raid()/stop_raid(), all safe to
## call at any time in any order.

const MENU_DB := -18.0
const RAID_DB := -26.0                # under everything, felt more than heard
const BREATH_MIN := 24.0              # a real pause between raid tracks
const BREATH_MAX := 38.0              # (user call: "like 30 secs")

var _player: AudioStreamPlayer
var _fade: Tween
var _menu_stream: AudioStreamOggVorbis
var _raid_streams: Array[AudioStreamOggVorbis] = []
var _mode := ""                       # "", "menu", "raid"
var _raid_last := -1
var _breath := 0.0
var _tail_started := false            # each raid track fades out at its end

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_menu_stream = load("res://assets/audio/music/menu_theme.ogg")
	_menu_stream.loop = true
	for i in 3:
		var s: AudioStreamOggVorbis = load("res://assets/audio/music/raid_%d.ogg" % i)
		s.loop = false                # each plays once, then the next rotates in
		_raid_streams.append(s)
	_player = AudioStreamPlayer.new()
	_player.volume_db = -60.0
	add_child(_player)
	set_process(false)

func play_menu() -> void:
	_mode = "menu"
	set_process(false)
	if _fade != null:
		_fade.kill()                  # a mid-flight fade-out must never win
	if _player.stream != _menu_stream or not _player.playing:
		_player.stop()
		_player.stream = _menu_stream
		_player.volume_db = -60.0
		_player.play()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", MENU_DB, 3.0)

func stop_menu(fade_seconds: float = 1.2) -> void:
	if _mode == "menu":
		_stop(fade_seconds)

func play_raid() -> void:
	_mode = "raid"
	_player.stop()
	_breath = 0.0                     # first track starts immediately
	set_process(true)

func stop_raid(fade_seconds: float = 1.0) -> void:
	if _mode == "raid":
		_stop(fade_seconds)

func _stop(fade_seconds: float) -> void:
	_mode = ""
	set_process(false)
	if _fade != null:
		_fade.kill()
	if _player.playing:
		_fade = create_tween()
		_fade.tween_property(_player, "volume_db", -60.0, fade_seconds)
		_fade.tween_callback(_player.stop)

func _process(delta: float) -> void:
	if _mode != "raid":
		return
	if _player.playing:
		# fade OUT over the track's last seconds — no cold endings
		if not _tail_started:
			var remaining := _player.stream.get_length() \
				- _player.get_playback_position()
			if remaining <= 4.0:
				_tail_started = true
				if _fade != null:
					_fade.kill()
				_fade = create_tween()
				_fade.tween_property(_player, "volume_db", -60.0,
					maxf(0.5, remaining))
		return
	_breath -= delta
	if _breath > 0.0:
		return
	_breath = randf_range(BREATH_MIN, BREATH_MAX)
	var pick := randi_range(0, _raid_streams.size() - 1)
	if pick == _raid_last:            # never the same one twice running
		pick = (pick + 1 + randi_range(0, 1)) % _raid_streams.size()
	_raid_last = pick
	_tail_started = false
	if _fade != null:
		_fade.kill()
	_player.stream = _raid_streams[pick]
	_player.volume_db = -60.0
	_player.play()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", RAID_DB, 4.0)
