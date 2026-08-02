extends Node
## JUICE — the engine-level polish layer (user call 2026-08-02: "keep the
## base art as-is, just use godot's visual toolkit to turn up the
## atmosphere"). Nothing in here redraws a sprite. It owns the effects that
## sit AROUND the art: held time on impact, and the shared shader material
## every flashable sprite uses.
##
## Autoload, so it outlives the scene. Anything it holds per-raid must be
## reset in `reset()`, which main.gd calls on deploy — the Ui autoload
## already taught us what a leftover entry does to the next raid.

# One shared ShaderMaterial would make every sprite flash together, so each
# sprite gets its OWN material from this one shader. The shader is the thing
# that is shared, which is what actually costs anything.
const FLASH_SHADER := "res://scripts/flash.gdshader"

var _stop_left := 0.0
var _shader: Shader


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS   # hit-stop must tick while slowed
	_shader = load(FLASH_SHADER)


func reset() -> void:
	## a fresh raid starts at full speed whatever the last one was doing
	_stop_left = 0.0
	Engine.time_scale = 1.0


func flash_material() -> ShaderMaterial:
	## a fresh material per sprite, sharing the one compiled shader
	var mat := ShaderMaterial.new()
	mat.shader = _shader
	mat.set_shader_parameter("flash", 0.0)
	mat.set_shader_parameter("flash_color", Color("ebede9"))
	return mat


func hit_stop(seconds: float) -> void:
	## A beat of held time on impact. Tiny — 40-70 ms. Long enough to read
	## as weight, short enough that it never feels like a frame drop, which
	## on a 240 Hz display would be the first thing noticed.
	_stop_left = maxf(_stop_left, seconds)
	Engine.time_scale = 0.04


func _process(delta: float) -> void:
	if _stop_left <= 0.0:
		return
	# delta arrives ALREADY scaled by time_scale, so unscale it or a 0.04x
	# world would stretch a 55 ms stop into well over a second
	_stop_left -= delta / maxf(Engine.time_scale, 0.001)
	if _stop_left <= 0.0:
		_stop_left = 0.0
		Engine.time_scale = 1.0
