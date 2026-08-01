extends Node
## Music autoload. The menu theme is a licensed loop — "The Last" pack by
## DavidKBD (CC-BY 4.0, see assets/audio/LICENSES.md). The old rule that all
## audio is synthesized was retired in v0.6.13 (user call: real music).
## Contract unchanged: play_menu()/stop_menu() with slow fades, safe to call
## at any time in any order.

const MENU_DB := -18.0  # subtle always — the theme sits under the menu

var _player: AudioStreamPlayer
var _fade: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var stream: AudioStreamOggVorbis = load("res://assets/audio/music/menu_theme.ogg")
	stream.loop = true
	_player = AudioStreamPlayer.new()
	_player.stream = stream
	_player.volume_db = -60.0
	add_child(_player)


func play_menu() -> void:
	if _fade != null:
		_fade.kill()  # a mid-flight fade-out must never stop the fresh play
	if not _player.playing:
		_player.volume_db = -60.0
		_player.play()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", MENU_DB, 3.0)


func stop_menu(fade_seconds: float = 1.2) -> void:
	if not _player.playing:
		return
	if _fade != null:
		_fade.kill()
	_fade = create_tween()
	_fade.tween_property(_player, "volume_db", -60.0, fade_seconds)
	_fade.tween_callback(_player.stop)
