class_name ShaderWarm
extends CanvasLayer
## "compiling shaders" — the boot step that pays the pipeline cost ONCE,
## behind a screen, instead of dropping a frame the first time something
## flashes mid-raid.
##
## IT ONLY APPEARS WHEN THERE IS REAL WORK. Godot already keeps a compiled
## shader cache on disk, so a restart with nothing changed does not
## recompile — which is how the user expects it to behave, and how it
## already behaved. Showing a progress bar on every launch to pay a
## fraction of a millisecond would be theatre.
##
## So: fingerprint the engine version plus the contents of every .gdshader,
## and keep it in user://. Same fingerprint means the cache is warm and this
## screen never shows. A changed shader — i.e. a game update — invalidates
## it, the cache is cold, and the bar earns its place.

const STAMP := "user://shader_stamp.txt"
const SHADER_DIR := "res://scripts"
# below this the screen would flash past faster than it can be read, so it
# stays hidden and the warm-up just happens
const SHOW_ABOVE := 0.12

var _bar: ColorRect
var _bar_max := 0.0
var _label: Label


static func fingerprint() -> String:
	## engine build + every shader's contents. Any change to any of them
	## means the driver has to build new pipelines.
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(str(Engine.get_version_info()).to_utf8_buffer())
	for path in _shader_paths():
		ctx.update(path.to_utf8_buffer())
		var f := FileAccess.open(path, FileAccess.READ)
		if f != null:
			ctx.update(f.get_buffer(f.get_length()))
	return ctx.finish().hex_encode()


static func _shader_paths() -> PackedStringArray:
	var out := PackedStringArray()
	var dir := DirAccess.open(SHADER_DIR)
	if dir == null:
		return out
	for name in dir.get_files():
		# exported builds rename resources; accept both
		if name.ends_with(".gdshader") or name.ends_with(".gdshader.remap"):
			out.append(SHADER_DIR + "/" + name.trim_suffix(".remap"))
	out.sort()
	return out


static func is_cold() -> bool:
	if not FileAccess.file_exists(STAMP):
		return true
	var f := FileAccess.open(STAMP, FileAccess.READ)
	if f == null:
		return true
	return f.get_as_text().strip_edges() != fingerprint()


static func mark_warm() -> void:
	var f := FileAccess.open(STAMP, FileAccess.WRITE)
	if f != null:
		f.store_string(fingerprint())


func run() -> void:
	## Compile every shader, showing the bar only if it turns out to be slow
	## enough to be worth showing. Returns when everything is built.
	var paths := _shader_paths()
	if paths.is_empty():
		mark_warm()
		return
	var started := Time.get_ticks_msec()
	var shown := false
	var host := Node2D.new()          # somewhere for the throwaway quads
	add_child(host)
	for i in paths.size():
		var shader: Shader = load(paths[i])
		if shader == null:
			continue
		# a material on a real, drawn CanvasItem is what actually forces the
		# driver to build the pipeline — loading the .gdshader alone does not
		var quad := ColorRect.new()
		quad.color = Color(1, 1, 1, 0.004)   # present, effectively invisible
		quad.size = Vector2(4, 4)
		var mat := ShaderMaterial.new()
		mat.shader = shader
		quad.material = mat
		host.add_child(quad)
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		if not shown and Time.get_ticks_msec() - started > SHOW_ABOVE * 1000.0:
			shown = true
			visible = true
		if shown:
			_set_progress(float(i + 1) / float(paths.size()))
			await get_tree().process_frame
	host.queue_free()
	if shown:
		# a bar that appears and vanishes in the same breath reads as a
		# glitch; give it a beat once it has earned the screen
		_set_progress(1.0)
		await get_tree().create_timer(0.25).timeout
	mark_warm()


func _set_progress(t: float) -> void:
	if _bar != null:
		_bar.size.x = maxf(1.0, _bar_max * clampf(t, 0.0, 1.0))


func _ready() -> void:
	layer = 95
	visible = false                    # only shown if the work is real
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var back := ColorRect.new()
	back.color = Color("090a14")
	back.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(back)

	_label = Label.new()
	_label.text = "compiling shaders"
	_label.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
	_label.anchor_left = 0.5
	_label.anchor_right = 0.5
	_label.anchor_top = 0.5
	_label.anchor_bottom = 0.5
	_label.offset_top = -22.0
	_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(_label)

	# the trough and the fill, measured off the REAL content size — this
	# project renders at 840x540 on the user's display, not 640x360
	var span := float(get_window().content_scale_size.x)
	if span < 100.0:
		span = 640.0
	_bar_max = minf(320.0, span * 0.42)
	var trough := ColorRect.new()
	trough.color = Color("202e37")
	trough.anchor_left = 0.5
	trough.anchor_top = 0.5
	trough.grow_horizontal = Control.GROW_DIRECTION_BOTH
	trough.offset_left = -_bar_max * 0.5
	trough.offset_top = 0.0
	trough.custom_minimum_size = Vector2(_bar_max, 6)
	trough.size = Vector2(_bar_max, 6)
	root.add_child(trough)
	_bar = ColorRect.new()
	_bar.color = Color("de9e41")
	_bar.position = Vector2(0, 0)
	_bar.size = Vector2(1, 6)
	trough.add_child(_bar)
