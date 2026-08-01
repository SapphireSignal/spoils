class_name ExtractScreen
extends CanvasLayer
## "successfully extracted" — the debrief. How you got out, how long you
## lasted, what you earned, and every kill with the minute it happened
## and the bone that ended it (user spec). The haul column is stubbed
## until the stash and the grid inventory land in M4.


var _root: Control
var _method_label: Label
var _stat_rows: VBoxContainer
var _kill_rows: VBoxContainer
var _haul_rows: VBoxContainer


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 92
	visible = false

	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = UITheme.get_theme()
	add_child(_root)
	var black := ColorRect.new()
	black.color = Color("090a14", 0.92)
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(black)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(520, 300)
	center.add_child(panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 16)
	panel.add_child(margin)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 8)
	margin.add_child(rows)

	var title := Label.new()
	title.text = "successfully extracted"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", Color("75a743"))
	rows.add_child(title)
	_method_label = Label.new()
	_method_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_method_label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	rows.add_child(_method_label)

	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 20)
	rows.add_child(columns)
	_stat_rows = _column(columns, "the raid", 150)
	_kill_rows = _column(columns, "kills", 210)
	_haul_rows = _column(columns, "the haul", 140)

	var out := Button.new()
	out.text = "back to the den"
	out.custom_minimum_size = Vector2(180, 0)
	out.pressed.connect(_leave)
	var out_center := CenterContainer.new()
	out_center.add_child(out)
	rows.add_child(out_center)


func _column(parent: HBoxContainer, heading: String, width: float) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.custom_minimum_size = Vector2(width, 150)
	box.add_theme_constant_override("separation", 3)
	var head := Label.new()
	head.text = heading
	head.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(head)
	parent.add_child(box)
	return box


func show_debrief(method: String) -> void:
	Raid.end()
	_method_label.text = "out by %s" % method
	for box in [_stat_rows, _kill_rows, _haul_rows]:
		for child in box.get_children():
			if child is Label and (child as Label).get_index() > 0:
				child.queue_free()
	_line(_stat_rows, "time survived   %s" % Raid.clock(Raid.elapsed()))
	_line(_stat_rows, "xp earned       %d" % Raid.xp)
	_line(_stat_rows, "kills           %d" % Raid.kills.size())
	_line(_stat_rows, "raiders killed  %d" % Raid.player_kills())
	if Raid.kills.is_empty():
		_line(_kill_rows, "nobody. quiet raid.", UITheme.TEXT_DIM)
	else:
		for k in Raid.kills:
			var tag := "raider" if bool(k["player"]) else str(k["name"])
			_line(_kill_rows, "%s  %s  %s" % [Raid.clock(float(k["at"])),
				tag, str(k["bone"])])
	if Raid.haul.is_empty():
		_line(_haul_rows, "the stash arrives", UITheme.TEXT_DIM)
		_line(_haul_rows, "with the loot", UITheme.TEXT_DIM)
		_line(_haul_rows, "update.", UITheme.TEXT_DIM)
	else:
		for item in Raid.haul:
			_line(_haul_rows, "%s x%d" % [str(item["name"]), int(item["count"])])
	visible = true
	Ui.open(&"extract")
	get_tree().paused = true


func _line(box: VBoxContainer, text: String, col: Color = UITheme.TEXT) -> void:
	var label := Label.new()
	label.text = text
	label.add_theme_color_override("font_color", col)
	box.add_child(label)


func _leave() -> void:
	visible = false
	Ui.close(&"extract")
	get_tree().paused = false
	get_tree().change_scene_to_file("res://scenes/menu.tscn")
