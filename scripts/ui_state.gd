extends Node
## Window traffic control (autoload "Ui").
##
## Exactly ONE window owns the screen at a time. Before this existed the
## map let its wheel zoom the world camera underneath it, and ESC opened
## the pause menu THROUGH the open map (user report). Gameplay polls
## Input directly every frame, so consuming events is not enough — the
## player and the car ask `blocks_gameplay()` and simply stop reading
## input while any window is up.

var _stack: Array[StringName] = []


func open(window: StringName) -> void:
	if window in _stack:
		return
	_stack.append(window)
	_sync_hud()


func close(window: StringName) -> void:
	_stack.erase(window)
	_sync_hud()


func _sync_hud() -> void:
	## A window owns the screen, so nothing from the world sits on top of
	## it: no "press f to open", no driving hint, no train notice, no
	## radio call (user report — the door prompt stayed up behind the
	## pause menu). The HUD cannot hide ITSELF, because most windows pause
	## the tree and its owners stop processing the moment they'd need to;
	## the stack has to do it for them.
	if not is_inside_tree():
		return
	get_tree().call_group("hud", "set_hud_hidden", not _stack.is_empty())


func any_open() -> bool:
	return not _stack.is_empty()


func blocks_gameplay() -> bool:
	## while a window is up the world does not read the keyboard, the
	## mouse wheel or the mouse buttons
	return not _stack.is_empty()


func clear() -> void:
	## scene swaps (death, quit to menu) drop every window
	_stack.clear()
	_sync_hud()
