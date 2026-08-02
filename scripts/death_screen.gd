class_name DeathScreen
extends CanvasLayer
## The bill for a raid that ended badly — walking out on one counts
## (user call: quitting to the menu mid-raid is not a free escape).
##
## It reads like a report rather than a score: how long you lasted, what
## you earned, what you were carrying when you lost it, who put you
## down, and WHERE — a doll marking the parts that actually took rounds,
## from `player.hits`. Nothing kills you but the wire yet; the ledger is
## built so the screen is already real when M2's guns arrive.

const BONES := ["head", "eyes", "thorax", "stomach",
	"left arm", "right arm", "left leg", "right leg"]

var _doll: Control
var _hits: Array[Dictionary] = []
var _counts: Dictionary = {}


func show_debrief(player: Player, walked_out: bool) -> void:
	_hits = player.hits.duplicate() if player != null else []
	_counts.clear()
	for hit in _hits:
		var bone := str(hit["bone"])
		_counts[bone] = int(_counts.get(bone, 0)) + 1
	Raid.end()
	_build(walked_out)
	Ui.open(&"death")
	get_tree().paused = true
	visible = true


func _build(walked_out: bool) -> void:
	layer = 88
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	add_child(root)
	var black := ColorRect.new()
	black.color = Color("090a14", 0.93)
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(black)

	var centre := CenterContainer.new()
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(centre)
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(430, 0)
	centre.add_child(panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 10)
	panel.add_child(margin)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 5)
	margin.add_child(rows)

	var title := Label.new()
	title.text = "you left the district" if walked_out else "you did not make it out"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", Color("cf573c"))
	rows.add_child(title)

	var cause := Label.new()
	cause.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cause.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	cause.custom_minimum_size = Vector2(400, 0)
	cause.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	cause.text = _cause_line(walked_out)
	rows.add_child(cause)

	# the doll and the ledger, side by side
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 12)
	rows.add_child(body)
	_doll = Control.new()
	_doll.custom_minimum_size = Vector2(120, 168)
	_doll.draw.connect(_draw_doll)
	body.add_child(_doll)

	var ledger := VBoxContainer.new()
	ledger.add_theme_constant_override("separation", 3)
	ledger.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(ledger)
	_stat(ledger, "survived", Raid.clock(Raid.elapsed()))
	_stat(ledger, "xp", str(Raid.xp))
	_stat(ledger, "kills", str(Raid.kills.size()))
	_stat(ledger, "raiders", str(Raid.player_kills()))
	_stat(ledger, "rounds taken", str(_hits.size()))
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 4)
	ledger.add_child(gap)
	var lost := Label.new()
	lost.text = "lost with you"
	lost.add_theme_color_override("font_color", Color("de9e41"))
	ledger.add_child(lost)
	_stat(ledger, "money", str(Raid.money))
	if Raid.haul.is_empty():
		var none := Label.new()
		none.text = "carrying nothing worth the trip"
		none.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		none.custom_minimum_size = Vector2(180, 0)
		none.add_theme_color_override("font_color", UITheme.TEXT_DIM)
		ledger.add_child(none)
	else:
		for item in Raid.haul:
			_stat(ledger, str(item.get("name", "?")),
				"x%d" % int(item.get("count", 1)))

	# every round, in order, with the minute it landed
	if not _hits.is_empty():
		var log_title := Label.new()
		log_title.text = "where they hit you"
		log_title.add_theme_color_override("font_color", Color("de9e41"))
		rows.add_child(log_title)
		for hit in _hits:
			var line := Label.new()
			line.text = "%s   %s   %s" % [Raid.clock(float(hit.get("at", 0.0))),
				str(hit["bone"]), str(hit.get("who", ""))]
			line.add_theme_color_override("font_color", UITheme.TEXT_DIM)
			rows.add_child(line)

	var out := Button.new()
	out.text = "back to the menu"
	out.pressed.connect(_leave)
	rows.add_child(out)
	out.grab_focus()


func _stat(parent: Container, label_text: String, value_text: String) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var name_label := Label.new()
	name_label.text = label_text
	name_label.custom_minimum_size = Vector2(96, 0)
	name_label.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	row.add_child(name_label)
	var value := Label.new()
	value.text = value_text
	value.add_theme_color_override("font_color", UITheme.TEXT)
	row.add_child(value)
	parent.add_child(row)


func _cause_line(walked_out: bool) -> String:
	if _hits.is_empty():
		return "you walked out on the raid. nothing you were carrying " \
			+ "comes home with you." if walked_out \
			else "the district got you."
	var last: Dictionary = _hits[-1]
	var who := str(last.get("who", "somebody"))
	var bone := str(last["bone"])
	if walked_out:
		return "you walked out bleeding. %s put the last one through your %s." \
			% [who, bone]
	return "%s put the last one through your %s." % [who, bone]


func _zone_rects() -> Dictionary:
	# a plain iso-ish doll: head, eyes over it, chest, gut, two arms, two
	# legs. Deliberately blocky — it reads at a glance, like the tarkov
	# health panel the user asked for
	return {
		"head": Rect2(48, 6, 24, 20),
		"eyes": Rect2(52, 12, 16, 6),
		"thorax": Rect2(42, 30, 36, 38),
		"stomach": Rect2(44, 70, 32, 24),
		"left arm": Rect2(24, 32, 15, 46),
		"right arm": Rect2(81, 32, 15, 46),
		"left leg": Rect2(44, 98, 14, 58),
		"right leg": Rect2(62, 98, 14, 58),
	}


func _draw_doll() -> void:
	var zones := _zone_rects()
	for bone in BONES:
		var rect: Rect2 = zones[bone]
		var count := int(_counts.get(bone, 0))
		# untouched parts stay the dull steel of the panel; anything that
		# took a round goes red, and harder the more it took
		var fill := Color("394a50")
		if count > 0:
			fill = Color("a53030").lerp(Color("cf573c"), minf(1.0, (count - 1) * 0.5))
		_doll.draw_rect(rect, fill)
		_doll.draw_rect(rect, Color("151d28"), false, 1.0)
		if count > 0:
			# a tick per round, so two in the chest reads as two
			for i in mini(count, 4):
				_doll.draw_rect(Rect2(rect.position.x + 2.0 + i * 4.0,
					rect.end.y - 4.0, 3.0, 2.0), Color("e8c170"))
	# the eyes sit ON the head, so outline them again to keep them readable
	_doll.draw_rect(zones["eyes"], Color("151d28"), false, 1.0)


func dismiss() -> void:
	## take the screen down and hand the world back. The button does this
	## on its way to the menu; the smoke test does it to carry on probing
	## a raid it deliberately died in.
	visible = false
	Ui.close(&"death")
	get_tree().paused = false


func _leave() -> void:
	dismiss()
	get_tree().change_scene_to_file("res://scenes/menu.tscn")
