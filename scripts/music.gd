extends Node
## Music autoload. Licensed loops from "The Last" pack by DavidKBD
## (CC-BY 4.0, assets/audio/LICENSES.md). Two moods, one player:
##  - menu: the guitar theme, looping under the menu.
##  - raid: SUBTLE ambient tracks with long silences between them — one
##    sparse track at very low volume, then minutes of quiet, then the
##    next. In an extraction game the silence is part of the mix; the
##    music must never bury a footstep (user: subtle, never loud).
## Contract: play_menu()/stop_menu()/play_raid()/stop_raid(), all safe to
## call at any time in any order.

const MENU_DB := -18.0
const RAID_DB := -26.0                # under everything, felt more than heard
const RAID_GAP_MIN := 70.0            # silence between raid tracks (s)
const RAID_GAP_MAX := 180.0

var _player: AudioStreamPlayer
var _fade: Tween
var _menu_stream: AudioStreamOggVorbis
var _raid_streams: Array[AudioStreamOggVorbis] = []
var _mode := ""                       # "", "menu", "raid"
var _raid_gap := 0.0
var _raid_last := -1

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_menu_stream = load("res://assets/audio/music/menu_theme.ogg")
	_menu_stream.loop = true
	for i in 3:
		var s: AudioStreamOggVorbis = load("res://assets/audio/music/raid_%d.ogg" % i)
		s.loop = false                # raid tracks play ONCE, then silence
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
		_stop_all(fade_seconds)

func play_raid() -> void:
	_mode = "raid"
	_player.stop()
	_player.stream = null
	# let the district speak first; the first track drifts in later
	_raid_gap = randf_range(20.0, 55.0)
	set_process(true)

func stop_raid(fade_seconds: float = 1.0) -> void:
	if _mode == "raid":
		_stop_all(fade_seconds)

func _stop_all(fade_seconds: float) -> void:
	_mode = ""
	set_process(false)
	if _fade != null:
		_fade.kill()
	if _player.playing:
		_fade = create_tween()
		_fade.tween_property(_player, "volume_db", -60.0, fade_seconds)
		_fade.tween_callback(_player.stop)

func _process(delta: float) -> void:
	if _mode != "raid" or _player.playing:
		return
	_raid_gap -= delta
	if _raid_gap > 0.0:
		return
	_raid_gap = randf_range(RAID_GAP_MIN, RAID_GAP_MAX)
	var pick := randi_range(0, _raid_streams.size() - 1)
	if pick == _raid_last:            # never the same track twice running
		pick = (pick + 1) % _raid_streams.size()
	_raid_last = pick
	if _fade != null:
		_fade.kill()
	_player.stream = _raid_streams[pick]
	_player.volume_db = -60.0
	_player.play()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", RAID_DB, 6.0)
