class_name TollDialog
extends CanvasLayer
## The warden's window. His face on the left, whatever he's decided to
## tell you on the right, and three ways to answer: keep him talking,
## pay the fee, or walk away.
##
## He is mean, bored, and proud of it — the cordon is a business and he
## is the counter it runs across. He never quite says what the wardens
## are FOR (that stays a mystery, LORE.md hard rule 3), but he'll tell
## you what everything costs.

signal paid

const FEE := 30

# he does not repeat himself twice running; there is no end to this
const GREETINGS := [
	"well. look what walked up to my window.",
	"evening. or morning. i stopped keeping track of which.",
	"you again. or someone shaped like you.",
	"stop there. everybody stops there.",
	"you're carrying. i can tell from here.",
]

const LINES := [
	"thirty. same as yesterday, same as the man before you.",
	"i've worked eleven gates. this is the best one. nobody important ever comes here.",
	"you know what i've made off people like you? no. neither does the ledger.",
	"there was a raider cried at this window once. paid double after. i let him.",
	"my brother works the harbor gate. he gets weather. i get you.",
	"the wire doesn't care about you. i do, professionally, for thirty.",
	"you think this is corruption. it's overtime.",
	"i don't ask what's in the bag. asking costs me time and you money.",
	"six years i've sat here. six. the paint on this booth is younger than the job.",
	"the ones who argue always have the least. write that down.",
	"i had a man offer me a watch once. i don't want a watch. i want thirty.",
	"you're all the same shape coming out. bent, and heavier on one side.",
	"they told us it'd be nine days. i packed for nine days.",
	"nobody crosses. that's the rule. rules have a price, that's just what a price is.",
	"i can see the fog coming in behind you. clock's yours, not mine.",
	"my supervisor is a name on a sheet. i've never met him. i suspect nobody has.",
	"you want to know what we're keeping in. everybody does. thirty.",
	"the lift charges more and lands on your head. i'm a bargain and i'm dry.",
	"i've seen your face before. don't tell me. i genuinely don't care.",
	"eat before a raid. you look like a coat somebody left out.",
	"the freight is free, if you like schedules and being crushed.",
	"i keep a tally too. mine's got more marks and better handwriting.",
	"one of you tried to bribe me with a photograph. of people. imagine.",
	"i'm not the worst thing between you and out. i'm just the politest.",
	"pay, don't pay. the buffer's open either way and it's very fast.",
	"you'd think six years would make people quicker at counting.",
]

const REPLIES := [
	"you talk a lot for a man in a box.",
	"how much have you actually made?",
	"what are you keeping in there?",
	"do you ever go inside yourself?",
	"nice booth.",
	"thirty seems steep.",
	"who signs your paychecks?",
	"you sound tired.",
	"i'm not paying you a compliment too.",
	"does anyone ever refuse?",
	"what happened to the nine days?",
	"i've heard about you.",
	"you must hate this job.",
	"say that again slower.",
]

var _portrait: TextureRect
var _speech: Label
var _reply_button: Button
var _pay_button: Button
var _line_index := -1
var _reply_index := -1
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 78
	visible = false
	_rng.randomize()

	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	add_child(root)
	var dim := ColorRect.new()
	dim.color = Color("090a14", 0.55)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(dim)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(470, 210)
	center.add_child(panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 14)
	panel.add_child(margin)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 10)
	margin.add_child(rows)

	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 14)
	rows.add_child(top)
	var frame := PanelContainer.new()
	_portrait = TextureRect.new()
	_portrait.texture = load("res://art/gen/warden_portrait.png")
	_portrait.custom_minimum_size = Vector2(96, 96)
	_portrait.stretch_mode = TextureRect.STRETCH_SCALE
	_portrait.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	frame.add_child(_portrait)
	top.add_child(frame)

	var words := VBoxContainer.new()
	words.add_theme_constant_override("separation", 6)
	words.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(words)
	var who := Label.new()
	who.text = "the tollman's warden"
	who.add_theme_color_override("font_color", UITheme.ACCENT)
	words.add_child(who)
	_speech = Label.new()
	_speech.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_speech.custom_minimum_size = Vector2(320, 74)
	_speech.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_speech.add_theme_color_override("font_color", UITheme.TEXT)
	words.add_child(_speech)

	_reply_button = Button.new()
	_reply_button.pressed.connect(_on_reply)
	rows.add_child(_reply_button)
	_pay_button = Button.new()
	_pay_button.pressed.connect(_on_pay)
	rows.add_child(_pay_button)
	var back := Button.new()
	back.text = "back away"
	back.pressed.connect(close)
	rows.add_child(back)


func open() -> void:
	visible = true
	Ui.open(&"toll")
	get_tree().paused = true
	_speech.text = GREETINGS[_rng.randi_range(0, GREETINGS.size() - 1)]
	_next_reply()
	_refresh_pay()
	_reply_button.grab_focus()


func close() -> void:
	visible = false
	Ui.close(&"toll")
	get_tree().paused = false


func _next_reply() -> void:
	var pick := _rng.randi_range(0, REPLIES.size() - 1)
	if pick == _reply_index:
		pick = (pick + 1) % REPLIES.size()
	_reply_index = pick
	_reply_button.text = "\"%s\"" % REPLIES[pick]


func _on_reply() -> void:
	# he always has another one. that IS the joke.
	var pick := _rng.randi_range(0, LINES.size() - 1)
	if pick == _line_index:
		pick = (pick + 1) % LINES.size()
	_line_index = pick
	_speech.text = LINES[pick]
	_next_reply()
	Sfx.play_click(true)


func _refresh_pay() -> void:
	if Raid.money >= FEE:
		_pay_button.text = "pay %d to extract" % FEE
		_pay_button.disabled = false
	else:
		_pay_button.text = "pay %d to extract  (you have %d)" % [FEE, Raid.money]
		_pay_button.disabled = true


func _on_pay() -> void:
	if Raid.money < FEE:
		return
	Raid.money -= FEE
	_speech.text = "pleasure. barrier's up. don't come back through here today."
	_pay_button.disabled = true
	_pay_button.text = "paid"
	paid.emit()
	await get_tree().create_timer(1.1).timeout
	if visible:
		close()
