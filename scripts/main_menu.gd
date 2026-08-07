extends Node2D
## Main menu. SIX generated backdrop scenes rotate with a slow crossfade, in a
## shuffle-bag order (see _bag_next) so no backdrop repeats until every one of
## them has been shown. ALL SIX are ALIVE and tick every frame:
##   0 den       - the traders at home: candle vs radio glow, smoke, rig LEDs
##   1 drain     - the tunnel under the district: god-ray, motes, ringing drips
##   2 yard      - the trainyard: the signal ticks red, drizzle, eave runoff
##   3 warden    - the toll gate: lamp and road spill on one clock, a moth, a blink
##   4 underpass - the flood: a failing sodium tube, three leaks ringing the water
##   5 counter   - mara's booth: the COLD light breathes here, and an ember drips
## (the storm scene retired 2026-08-01 — user call). DEPLOY starts the raid.

const SCENE_SECONDS := 15.0   # 30 -> 10 (v0.6.31) -> 15, all user calls
const FADE_SECONDS := 1.4

# preloaded once for the process lifetime: re-entering the menu from the game
# must not re-decode these (that decode was a visible 1-2 frame hitch)
const TEX_DEN := preload("res://art/gen/menu_den.png")
const TEX_DEN_GLOW := preload("res://art/gen/menu_den_glow.png")
const TEX_DEN_NEEDLES := preload("res://art/gen/menu_den_needles.png")
const TEX_DRAIN := preload("res://art/gen/menu_drain.png")
const TEX_DRAIN_RAY := preload("res://art/gen/menu_drain_ray.png")
const TEX_DRAIN_RIPPLE := preload("res://art/gen/menu_drain_ripple.png")
const TEX_DRAIN_SLUICE := preload("res://art/gen/menu_drain_sluice.png")
const TEX_DRAIN_LANT := preload("res://art/gen/menu_drain_lant.png")
const TEX_DRAIN_CHOP := preload("res://art/gen/menu_drain_chop.png")
const TEX_DRAIN_MIST := preload("res://art/gen/menu_drain_mist.png")
const TEX_YARD := preload("res://art/gen/menu_yard.png")
const TEX_YARD_HALO := preload("res://art/gen/menu_yard_halo.png")
const TEX_YARD_SPLASH := preload("res://art/gen/menu_yard_splash.png")
const TEX_YARD_GLINT := preload("res://art/gen/menu_yard_glint.png")
const TEX_YARD_BIRD := preload("res://art/gen/menu_yard_bird.png")
const TEX_YARD_WIN := preload("res://art/gen/menu_yard_window.png")
const TEX_WARDEN := preload("res://art/gen/menu_warden.png")
const TEX_WARDEN_LAMP := preload("res://art/gen/menu_warden_lamp.png")
const TEX_WARDEN_SPILL := preload("res://art/gen/menu_warden_spill.png")
const TEX_WARDEN_BLINK := preload("res://art/gen/menu_warden_blink.png")
const TEX_WARDEN_MOTH := preload("res://art/gen/menu_warden_moth.png")
const TEX_UNDERPASS := preload("res://art/gen/menu_underpass.png")
const TEX_UP_TUBE := preload("res://art/gen/menu_underpass_tube.png")
const TEX_UP_HALO := preload("res://art/gen/menu_underpass_halo.png")
const TEX_UP_POOL := preload("res://art/gen/menu_underpass_pool.png")
const TEX_UP_RING := preload("res://art/gen/menu_underpass_ring.png")
const TEX_UP_WET := preload("res://art/gen/menu_underpass_wet.png")
const TEX_UP_CHOP := preload("res://art/gen/menu_underpass_chop.png")
const TEX_UP_PEND := preload("res://art/gen/menu_underpass_pend.png")
const TEX_UP_PENDPOOL := preload("res://art/gen/menu_underpass_pendpool.png")
const TEX_UP_MIST := preload("res://art/gen/menu_underpass_mist.png")
const TEX_COUNTER := preload("res://art/gen/menu_counter.png")
const TEX_CTR_BOX := preload("res://art/gen/menu_counter_box.png")
const TEX_CTR_LAMP := preload("res://art/gen/menu_counter_lamp.png")
const TEX_CTR_ARC := preload("res://art/gen/menu_counter_arc.png")
const TEX_CTR_FLARE := preload("res://art/gen/menu_counter_flare.png")
const TEX_CTR_DUST := preload("res://art/gen/menu_counter_dust.png")
const TEX_CTR_RAT := preload("res://art/gen/menu_counter_rat.png")
const TEX_RAIN := preload("res://art/gen/rain_streak.png")
const TEX_DUST := preload("res://art/gen/dust.png")
# SHARED. The same event on the yard's lines, the warden's isolator and
# the counter's taped splice, so it is one asset and one helper.
const TEX_SPARK := preload("res://art/gen/menu_spark.png")
# THE WORLD RAIN'S OWN SPLASH, not a menu-only copy. gen_art already has a
# make_rain_splash() and it is the 4-frame ground splash the raid uses — I
# wrote a second one with the same name and Python silently kept the later
# definition, which broke the whole build. The right answer was reuse.
const TEX_RAINSPLASH := preload("res://art/gen/rain_splash.png")
const TEX_DRAIN_BUBBLE := preload("res://art/gen/menu_drain_bubble.png")
const TEX_DRAIN_DROP := preload("res://art/gen/menu_drain_drop.png")
const TEX_VIGNETTE := preload("res://art/gen/vignette.png")
const TEX_MAP_THUMB := preload("res://art/gen/menu_map_transit.png")
const TEX_TITLE := preload("res://art/gen/title.png")
const TEX_TAGLINE := preload("res://art/gen/tagline.png")
const SHADER_GLEAM := preload("res://scripts/gleam.gdshader")

# painting-space -> scene-space (backdrops are 960x544, centered on origin)
const PC := Vector2(-480, -272)

var _scenes: Array[Node2D] = []
var _scene_index := 0
var _rotate_timer := 0.0
var _bag: Array[int] = []   # remaining draws this round — see _bag_next()
var _fade_tween: Tween
var _time := 0.0

# den life
var _candle_glow: Sprite2D
var _needles: Array[Sprite2D] = []
var _leds: Array[Sprite2D] = []
# drain life
var _ray: Sprite2D
var _ripples: Array[Sprite2D] = []
var _ripple_age: Array[float] = []
var _drips: Array[Sprite2D] = []
var _drip_t: Array[float] = []
var _sluice: Sprite2D
var _lant: Sprite2D
var _drain_chop: Sprite2D
var _drain_mist: Sprite2D
var _drain_anim := 0.0
# FOUR leaks, and every one of them owns exactly one ripple at the same index.
# Sources sit under the soffit; they land on the pool. See _tick_drain.
# FIVE leaks, and FOUR of them hang off the manhole's own rim — user:
# "the drain backdrop should have the water coming from the top of the hole,
# like where it opens up, like water is leaking from there and hitting the
# water on the ground, which should show a bubble ... a couple drops and maybe
# a bigger drop with a bigger bubble". Index 2 is the FAT one: it falls
# slower, rings wider and pushes up the big bubble.
const DRAIN_DRIP_X := [596.0, 608.0, 618.0, 630.0, 672.0]
const DRAIN_DRIP_TOP := [126.0, 110.0, 118.0, 132.0, 158.0]
const DRAIN_DRIP_Y := [510.0, 510.0, 511.0, 512.0, 516.0]
const DRAIN_DRIP_BIG := [false, false, true, false, false]
var _bubbles: Array[Sprite2D] = []
var _bubble_age: Array[float] = []
# yard life
var _yard_halo: Sprite2D
var _yard_glint: Sprite2D
var _yard_leds: Array[Sprite2D] = []
var _yard_splash: Sprite2D
var _yard_splash_age := -1.0
var _yard_drip: Sprite2D
var _yard_drip_t := 0.0
# Every one of these is a SILHOUETTE cell read out of the bake with the
# sunset directly behind it — a lit window floating in open sky would be
# the exact 'anchor points at nothing' mistake this project keeps making.
const YARD_WINDOWS := [Vector2(127, 253), Vector2(155, 253),
	Vector2(176, 256), Vector2(204, 255), Vector2(302, 262),
	Vector2(323, 262), Vector2(435, 258), Vector2(463, 255),
	Vector2(484, 252)]
var _yard_wins: Array[Sprite2D] = []
var _birds: Array[Sprite2D] = []
var _bird_x: Array[float] = []      # TRUE positions, kept continuous
var _bird_y: Array[float] = []
var _bird_age: Array[float] = []
var _bird_life: Array[float] = []
var _bird_spd: Array[float] = []
# warden life
var _w_lamp: Sprite2D
var _w_spill: Sprite2D
var _w_blink: Sprite2D
var _w_led: Sprite2D
var _w_moth: Sprite2D
var _w_moth_a := 0.0
var _w_flap := 0.0
var _w_gutter := 0.0      # seconds of gutter left, set when the moth touches
var _w_gutter_t := 4.0    # seconds until the moth is allowed to touch again
# underpass life
var _up_lights: Array[Sprite2D] = []   # tube, wall halo, walkway pool: ONE lamp
var _up_drips: Array[Sprite2D] = []
var _up_drip_t: Array[float] = []
var _up_rings: Array[Sprite2D] = []
var _up_ring_age: Array[float] = []
var _up_chop: Sprite2D
var _up_chop_t := 0.0
var _up_pend: Array[Sprite2D] = []   # the dead pendant, switched on and dying
var _up_mist: Sprite2D
# SIX leak columns, not three (v0.6.37). Three drips over a 960px frame is
# one every few seconds somewhere you are probably not looking; six reads
# as a roof that leaks. All over open water, all outside the button box.
const UP_DRIP_X := [148.0, 262.0, 330.0, 372.0, 592.0, 268.0]
const UP_DRIP_TOP := 108.0                 # the portal beam's underside
const UP_WATER := 406.0
# counter life
var _ctr_box: Sprite2D
var _ctr_lamp: Sprite2D
var _ctr_arc: Sprite2D
var _ctr_flare: Sprite2D
var _ctr_flare_age := -1.0
var _ctr_ember: Sprite2D
var _ctr_ember_t := 1.4
var _ctr_haze: Sprite2D
var _ctr_rat: Sprite2D
var _ctr_rat_t := 2.2
var _ctr_rat_x := 0.0   # TRUE position; only the draw rounds    # long enough for the arc's swell to read first
const CTR_SPLICE := Vector2(837, 254)      # the live pilot bead in _cables
const CTR_TIN_Y := 399.0                   # the parts tin's baked scorch ring

# arcing joints. Each entry: [sprite, seconds until the next strike].
# ANCHORED ON REAL FITTINGS, never in open air — the yard's two are on wire
# pixels sampled out of the bake (x 170 y 175 and x 230 y 205), the warden's
# is the isolator on the shift lamp's conduit, the counter's is the taped
# splice whose pilot bead is already painted live.
var _arcs: Array[Array] = []

# MENU RAIN, simulated the way the raid's is. Each field is one scene's
# weather: parallel arrays, one sprite per drop, one splash sprite per drop.
var _rain: Array[Dictionary] = []

var _title: TextureRect
var _title_base_y := 0.0
var _buttons: VBoxContainer
var _settings: SettingsPanel
var _keybinds: KeybindsPanel
var _volume: VolumePanel
var _changelog: PanelContainer
var _changelog_btn: Button     # hidden while a full-screen panel owns the menu
var _changelog_list: VBoxContainer
var _changelog_open := false   # the USER opened it (vs the boot prewarm)
var _map_select: PanelContainer
var _ms_name: Label
var _ms_blurb: Label
var _ms_clock: Label
var _ms_clock_stamp := ""
var _ms_deploy: Button
var _ms_transit_frame: PanelContainer

# readable in-game summary; the full detail lives in CHANGELOG.md
const CHANGELOG_ENTRIES := [
	# ONE STRING PER BULLET. The labels autowrap, so hand-wrapping a
	# sentence across several entries put a dash on every line (user).
	["v0.6.80", [
		"the corner pillars finally sit level with the walls - worked out from where each piece is anchored this time instead of nudged until it looked right. too high, invisible, and level is the full history in three attempts",
		"the upper floors wall fades in and out like the roof does, instead of switching in one frame. the ground floors wall stays solid underneath the whole time",
	]],
	["v0.6.79", [
		"the corner pillars are properly flat with the wall now. i had matched their height to the walls, but a corner sits on a different anchor point than the wall pieces do, so equal height still left them sticking up",
		"the two floors fade into each other instead of switching in one frame, same fade as the roof. what you can bump into still switches instantly",
	]],
	["v0.6.78", [
		"theres a stairwell opening in the second floor now, so you can see where the stairs are. its painted as a shaft rather than cut as a hole - the last version of this showed the room below through it and stopped the floor reading as a floor",
		"standing on the ground floor of a two storey house, the upper floors wall doesnt tower over the room any more - including the six corner and door pillars, which needed their own shortened version. from outside its still two storeys, and upstairs its still there",
		"going up the stairs shows the upper floor straight away instead of waiting for you to take a step",
		"the click you could hear every couple of seconds in a vehicle is gone. the engine loop was just under 3 seconds long and didnt join back onto itself cleanly, so it clicked once every time it came round. it loops seamlessly now",
		"you cant walk through staircases any more - the solid part of them was a tiny circle at the bottom of the flight",
		"the corner pillars line up with the top of the wall instead of sitting just under it, so they read as part of the building",
		"everything is another 3 decibels louder",
	]],
	["v0.6.77", [
		"the second floor is a proper floor now - the staircase used to be drawn straight through it and sit on the floorboards. its covered while youre up there, and the solid part goes with it so theres nothing invisible to walk into",
		"the stairs prompt said go upstairs while you were already upstairs. the text is only rebuilt when what youre looking at changes, and climbing doesnt change it - its the same staircase",
	]],
	["v0.6.76", [
		"going up to a second floor leaves the front door exactly as you left it. it was shutting the door on purpose - upstairs has no walls of its own, so an open doorway is a hole you can walk out of at roof height - but the doorway is just held solid now instead, and the door itself is left alone",
	]],
	["v0.6.75", [
		"opening a door from right up against it doesnt shove you back any more. to make a door sit at the right depth i was moving the door itself, and a door is solid - so nudging it nudged you with it. only the picture moves now, never the solid part",
	]],
	["v0.6.74", [
		"open doors stop slicing into the wall on half the buildings. a door on one of the two wall directions sticks out past the wall when its open, and i was sorting it by its middle - which sits exactly on the wall line, so the wall drew over the bit that was sticking out. it goes by the leading edge now",
		"my door test could only ever see the other half of the doors, so it never caught this. it can reach any door now and lists them all",
	]],
	["v0.6.73", [
		"the wall right beside a door stops changing when you open it. the boards down the sides of a doorway are wall, but they were painted into the door picture - so giving the door its own depth last version dragged the wall along with it. theyre their own piece now",
		"the black line between a doorway and the wall beside it is gone. that join was being outlined like an edge when it isnt one - its wall meeting wall, the same as every other seam in a building",
		"an open door has a clean edge against the wall again instead of looking sunk into it. a shut door is flush with the wall so it shouldnt have one there, but i was carrying that into the swung frames too, where the door is standing out in front",
	]],
	["v0.6.72", [
		"standing behind an open door hides you now. the door was being sorted from where its frame sits in the wall, but an open leaf swings out toward the camera - so it could never cover anyone stood behind it, however far it swung",
	]],
	["v0.6.71", [
		"when youre exactly level with a wall you now go behind it instead of the game picking at random. that was a side effect of the flicker fix - it put you on the same grid as the walls, so dead ties became common and a tie had no defined winner",
	]],
	["v0.6.70", [
		"the wall above a doorway follows the slope now instead of stopping in a straight line, so most of the gap you could see through is gone - measured 8 pixels down to 3. not fully closed yet, and its written up rather than called done",
		"the car starting up is a lot quieter. it was already at the loudest a one-shot is allowed to be, and then last versions overall volume lift pushed it past that",
	]],
	["v0.6.69", [
		"the camera follows cars again. that was mine - a change a few versions back moved where the players position is stored, and the driving code was still writing the old one, so the car drove off without the camera",
		"the roof only lifts once youre actually inside now. i had made standing on the doorstep count as inside, and a doorway looks the same from both sides",
	]],
	["v0.6.68", [
		"the boards down the sides of a doorway are the buildings own brick now instead of the doors colour - they are the edge of the hole in the wall, so they belong to the wall",
	]],
	["v0.6.67", [
		"the bit of wall above a door is made from that buildings own wall now, so it matches instead of looking like a patch stuck on. a door can be wood on a grey building - the door type follows what the building is for, the wall colour is rolled separately",
		"the warehouse doors were already sealed, what was wrong there was the same colour mismatch",
	]],
	["v0.6.66", [
		"every door had a gap above it that let you see inside a house through a shut door. the walls either side are five pixels taller than the door was, and a door tile has no wall behind it - theres a proper header over the opening now",
		"the three identical trucks outside the warehouse are actually fixed this time. last version i fixed the ones parked on roads and missed the ones that were actually bothering you",
		"rain through a wall is much easier to hear",
		"everything is a little louder overall",
	]],
	["v0.6.65", [
		"doors were painted in the exact same two colours as the wall around them, so on the shady side you could barely find them. theyre a different shade now - and one of those was my own fault from the grey house fix a few versions back",
		"standing in a doorway now counts as being inside, so the roof lifts instead of leaving you visible through your own door",
		"no two vehicles parked in a row are the same model any more",
	]],
	["v0.6.64", [
		"the loading screen was supposed to get every texture ready before you play. it was only half doing it - it loaded them but never drew them, and the real cost lands the first time a thing is actually drawn. so every object still paid it the first time it came on screen, once, and never again. that is the thing you described",
		"it draws them all behind the deploy screen now. loading takes a tenth of a second longer and nothing changed about the frame pacing",
	]],
	["v0.6.63", [
		"found the flicker. the character was being SORTED at a slightly different spot from where it was DRAWN - up to half a pixel out - so anything you walked past could be put in front of you for a single frame even though it was behind you. thats the thing you kept seeing on walls and never being able to walk back to",
		"measured it before and after: on frames where you were level with something, 46% of them were sorted wrong. its zero now",
		"walking speed is untouched - the exact position is still what moves you, only what gets drawn is snapped",
	]],
	["v0.6.62", [
		"found and fixed a real one-frame flash: when a roof fades away as you step inside, it was doing over half of the fade in the very first frame, so it read as the roof snapping rather than fading. it eases in from nothing now - measured at 28 brightness levels of jump before, 1 after",
		"this might not be the exact flicker you spotted, a clean walk past a house came out frame-perfect, but it was a genuine one and its gone",
	]],
	["v0.6.61", [
		"nothing you can see - this one is measuring the thing you noticed while walking around. the games frame timer only ever watched a still camera, so it could never have caught it",
		"there is a moving one now, and it says the frame rate is genuinely solid while walking - 240fps with nothing dropped over nine thousand pixels of ground. so what you were seeing isnt the framerate, its something drawing in the wrong order for a single frame, which is a different problem and is written up",
	]],
	["v0.6.60", [
		"the dirt is properly brown now instead of leaning red",
		"where dirt spreads over a road it spreads in uneven lobes instead of a neat band following the kerb, so it doesnt read as a straight strip any more",
	]],
	["v0.6.59", [
		"those little squiggles that looked like question marks are gone from every surface. the routine that was meant to paint small wear patches was actually drawing a wandering one-pixel line, so the whole game had tiny glyphs scattered over the ground",
		"buildings dont have dirt blowing through their walls any more - every building keeps its own clean floor",
		"fewer pale specks on the concrete",
		"the map isnt made of rectangles any more. blocks and yards have wandering edges, and the broken ground on it was literally drawn as little squares - thats round now",
		"the dirt on the map is the same brown as the dirt in the world",
	]],
	["v0.6.58", [
		"the ground got a proper pass. dirt, stone, roads, the forest floor and the rail bed all have slow tonal variation across them now instead of being one flat colour with specks on it",
		"the dirt is brown instead of red. it was mixed from the wrong end of the palette - the reds - so it came out like wine no matter how much of it there was",
		"the roads stay smooth, just with old repair patches showing through",
	]],
	["v0.6.57", [
		"whole patches of ground were never getting blended at all - a lone bit of grass in the dirt, or the pocket under a dead tree, stayed a hard diamond. the blending now runs at the very end of building the world, so it covers everything no matter what put it there",
		"dirt spreads onto the roads properly now instead of just outlining them. it can wash right over the tarmac, which is what it should have looked like",
		"some stretches of road have broken up completely and gone back to bare earth, and they blend into whatever is around them. the map shows them too, so the roads arent perfectly straight lines on it any more",
		"more grass coming through the cracks on the stone tiles",
	]],
	["v0.6.56", [
		"the last hard lines are out of the ground blending. two tiles were each growing into the other, which meant they still met in a straight line right on the join - now only one side of any boundary spreads, so the only edge you see is a ragged one in the middle of a tile",
		"and the grass can no longer thin out to nothing along an edge, which was leaving short straight gaps of bare concrete",
	]],
	["v0.6.55", [
		"the ground blending is rebuilt. the last go left a thin line of grass tracing round every tile, which looked worse than the hard edges did - now one material genuinely wanders into the next, and it works on every surface instead of only three of them, so roads and paving fray too",
		"the tile underneath keeps its own cracks and stains now instead of being replaced",
		"dead trees dont sway any more. only things with leaves on them move - the bare ones were waving like sticks",
		"the car on your safehouse drive is always a working one. it could roll up as a wreck before",
		"the bodies out past the wire have blood under them. they always had a stain, it was just so dark and so small you couldnt see it",
	]],
	["v0.6.54", [
		"the ground blends now. grass, dirt and concrete used to meet at a hard diamond edge so you could see every single tile - they fray into each other, with grass creeping out over the pavement and the pavement breaking up into the woods",
		"it works both ways round, so the edge of a wood isnt a cut-out shape any more",
		"grey houses were painted in exactly the same two colours as the ground they stand on, so on the shady side they had no edge at all. theyre a shade lighter now and you can actually see the building",
		"same district, same buildings, nothing moved - still 240fps",
	]],
	["v0.6.53", [
		"the district isnt laid out on a perfect grid any more. the streets used to be evenly spaced to the cell - theyre uneven now, so some blocks are wide and some are narrow, and it looks like a place instead of graph paper",
		"the landmarks arent snapped to the middle of their block either. the depot slid along its road, the playground isnt centred, the relay and the gallery sit off their corners",
		"its the same district, not a new one - your safehouse is where it was, and every building, road and prop is the one that was already there, just nudged. theres actually one more building than before",
		"the town square stayed dead centre on purpose. moving it squeezed the houses around it and cost two of them",
	]],
	["v0.6.52", [
		"the map has colour on it now. it was all one shade of brown like a paper map youd unfold - the ground, the woods, the yards and the buildings are all their own colour, so you can tell what youre looking at without reading the labels",
		"the woods are actual trees instead of little scratchy lines - clumps of canopy with light coming from one side, and the turned autumn patch stands out in orange",
		"the roads arent all the same any more. the ones that run right through the district are wide and bright with a dashed line down the middle, the ones that stop halfway are thinner and duller - so you can see at a glance which way you can actually drive",
		"every place on the map is colour coded by what its for - green means you can get out there, red is your safehouse, blue is somewhere worth going. they used to all be the same symbol in the same little box",
		"still 240fps with the map open over a live raid",
	]],
	["v0.6.51", [
		"the title on the menu is cast metal now instead of a flat white word - it has thickness, its lit from above, and its got wear and rust on it like everything else in the game does",
		"light moves across it properly. it used to be a straight-edged bar that slid over the letters once every six seconds and did nothing in between - now theres a soft angled gleam that never stops drifting, and a brighter one that sweeps through now and then",
		"it floats slower too. heavy metal letters bouncing looked wrong",
	]],
	["v0.6.50", [
		"the transit tile on the map-select screen is an actual picture now instead of a little top-down diagram - the district at dusk, the spires on the horizon, the sun going down behind the roofs, the comms mast, the treeline, and the wire in front of it all",
		"its drawn at the exact size of the button, so its sharp - the old one was a smaller image stretched up, which is why it looked soft",
	]],
	["v0.6.49", [
		"the trees and bushes move now. every one of them leans in the wind on its own timing, with the trunk staying put and only the leaves shifting, so a wood doesnt look like a field of identical statues any more",
		"it shifts by whole pixels only, so nothing goes blurry, and it costs nothing - still 240fps in the middle of the forest and on a storm night",
	]],
	["v0.6.48", [
		"your shadow follows the sun now. it used to be one blob under your feet that never changed - it stretches out long in the early morning, shrinks to almost nothing at midday, and swings round to the other side by evening",
		"it fades out under heavy cloud and at night, because there isnt a sun to cast it - you keep a soft dark patch underfoot so you dont look like youre floating",
	]],
	["v0.6.47", [
		"nothing you can see in game - this one is about keeping the notes honest. the docs are full of numbers about how the game is built, and a few of them had quietly gone wrong over time. theres a check now that reads each number out of the notes and compares it against what the game actually does, and the build fails if they disagree",
		"the games own test log used to print about fifty harmless errors every run, which made a real error easy to miss. it prints none now",
	]],
	["v0.6.46", [
		"the map is a proper drawn map now instead of coloured squares - paper, inked edges, roads with a pale channel down the middle, the woods hatched in, the rail as a ladder and the wire as a broken red line",
		"every place on it has its own little drawn symbol - a bus at the depot, a crane at the scrapyard, a swing at the playground, a mast at comms, the boom at the toll gate, an h pad at the lift, and a red house on your safehouse",
		"the car and truck names dont print until you zoom in. all thirty-odd of them used to appear the moment you opened the map and you couldnt see the map for the labels",
	]],
	["v0.6.45", [
		"walls block light now. lamps, room lights, your flashlight and car headlights all stop at a wall instead of shining straight through it, so standing in a dark house with the torch on no longer lights up the street outside",
		"light still comes through a doorway - an open door lets it through, a shut one blocks it, and a wall thats been blown open leaves a gap the light falls through",
		"no cost to it: still 240fps at midnight with every working lamp casting",
	]],
	["v0.6.44", [
		"a safety fix in the art generator. it used to delete all the games art first and then redraw it, so any small mistake in one drawing left the art folder empty until it was run again - that happened twice yesterday. it now writes everything first and only clears out leftovers at the very end, so a mistake leaves your art exactly where it was",
	]],
	["v0.6.43", [
		"the underpass door has a wired glass panel now, and theres blood spattered on the far side of it",
		"kettle has a proper beard in the den. he was always meant to have one but it rendered as a bare chin - it has an edge against his cheek, strands through it and a ragged bottom now",
	]],
	["v0.6.42", [
		"the thing on the right of the underpass was a bricked-up service door all along - its a real door now, with a frame, ribs, hinges and a handle. and two notices on the wall beside it: a transit shelter sign pointing down into the underworks, and a wardens cordon notice",
		"the birds and the rat werent moving at all. both of them were rounding their position every frame, and at 240fps thats less than half a pixel of movement, so it got rounded straight back and they sat still. they move now",
		"the rat actually looks like a rat - snout, ear, arched back and a long tail - and it fades in and out instead of blinking out of existence halfway across the counter",
	]],
	["v0.6.41", [
		"the birds work now. they were flying at exactly the height of the menu buttons so most of every crossing happened behind them, and on top of that the code had them switching between two states and they were silently never drawing at all. theyre spread across the sky at their own heights and their own speeds now, and they fade in and out instead of popping",
		"mara is holding her pencil properly - its drawn behind her hand now so her fingers close over it and the lead reaches the map. her forearms are slimmer and rounded instead of square slabs, and shes slimmer in the den painting too",
	]],
	["v0.6.40", [
		"rain lands properly now. every drop knows where its own ground is, falls to it, dies there and leaves a splash on that exact spot - the same way rain already works in the raids. the ground splash marks from last version are gone, they were a separate thing lying on the floor and you were right that it wasnt what you meant",
		"the birds in the trainyard are bigger, there are five of them, and they cross slower so theyre easier to catch",
	]],
	["v0.6.39", [
		"the trainyard and mara's counter have things that actually move in them now, not just more light. birds cross the sunset, the sparks off the pole lines are bigger and there are five of them going much more often, and there are little lit windows on the far buildings that flicker",
		"and a rat runs along the empty end of mara's counter - it was there before but painted almost the same colour as the counter, so it was invisible. its lighter now",
	]],
	["v0.6.38", [
		"backdrops change every fifteen seconds now instead of ten",
		"the drain: water leaks from the manhole opening itself now, four drips off the rim including one fat slow one, and every drop blows a bubble on the water when it lands - a bigger bubble for the big drop. the sheet from the sluice gate reaches the channel instead of stopping in mid air",
		"the shimmer on the drain water was a visible rectangle - it fades out at every edge now so it blends into the pool",
		"rain actually lands. the trainyard and the toll gate now splash where it hits the ground, using the same splash the rain uses in game",
	]],
	["v0.6.37", [
		"the menu backgrounds move a lot more now. you said the living layers were too minimal and you were right - i was being too careful with them",
		"new things that move, rather than just more of the old ones: sparks arc off the telegraph lines in the trainyard, off the isolator box by the warden's booth and off the taped splice over mara's head. the dead hanging lamp in the underpass is lit now and failing badly, out of step with the sodium tube. its rain across the whole frame in the trainyard and at the toll gate. the candle in the den actually behaves like a flame instead of a lamp with a loose wire",
		"the drain: the sluice gate is pouring a real sheet of water into the channel now - it was always described that way but painted almost black so you never saw it. and a bug you spotted, rings appearing on the water with nothing falling into them: the two ripples had their own timers and only one of them was ever caused by a drip. theres four drips now and every ring is something landing",
	]],
	["v0.6.36", [
		"the test that checks you cant walk through a closed door was giving a different answer on different runs, on the same build. it was measuring where you ended up one frame AFTER the shove, and by then the player's own movement had nudged them back out of the door - so which way they popped came down to rounding. it reads the result straight away now. no change to the game itself",
	]],
	["v0.6.35", [
		"mara's counter is alive now, and that's all six menu backgrounds moving. here it's the COLD light that breathes - the light box under her map - while the work lamp holds steady, which is the opposite way round to every other scene and is the whole point of this one",
		"the taped splice up in the corner swells just before it lets an ember go, and the ember drops into the parts tin and flares on the scorch ring thats been baked into that tin all along",
		"the painting is untouched, checked byte for byte, same as the other three",
	]],
	["v0.6.34", [
		"the flooded underpass is alive now. the sodium tube is failing - it stammers out and strikes again every few seconds, and the glow on the wall behind it and the pool of light on the walkway go out with it, because theyre the same lamp. three leaks in the deck overhead drip into the flood and push a broken ring out of the water where they land",
		"the painting is untouched again, checked byte for byte",
	]],
	["v0.6.33", [
		"the warden's gate is alive now. his desk lamp breathes and the pool of light out on the wet road breathes with it, which is what finally makes that pool read as light coming out of his window. a moth works the lampshade and the lamp guts when it touches. the fuse box behind the glass has a pilot light again. and he blinks",
		"the painting is untouched again - the blink is a twenty-eight pixel overlay laid exactly over his eyes, with the bridge of his nose left alone",
	]],
	["v0.6.32", [
		"the trainyard menu background is alive now. the signal ticks red on a slow beat, the cabinet indicator and the far signal down the line blink on their own timings, drizzle blows through the left of the yard, and water runs off the boxcar roof and bursts on the ballast. the sunset moves in the puddle between the rails",
		"the painting itself is untouched - every one of those is a light or a moving piece laid over the picture you already approved, checked byte for byte",
	]],
	["v0.6.31", [
		"the menu now changes backdrop every ten seconds instead of thirty",
	]],
	["v0.6.30", [
		"the four new menu paintings are in the game. six backgrounds now instead of two - the den, the drain, the trainyard, the warden at his gate, the underpass and the counter. the four new ones are still pictures for the moment, the moving parts come next",
		"they change every thirty seconds instead of twenty, and the order is random now rather than the same loop every time. you cant get the same one twice in a row, and you wont see one come back until youve been shown all six",
	]],
	["v0.6.29", [
		"both menu backgrounds repainted to match the new ones being auditioned. the den: mara now actually looks like mara, verne finally looks like the medic he is with his instruments and bottles and basin, and kettle has a face and the shelf of pawned stock he keeps. the light is properly banded instead of two soft blobs, the wall is real boards and the floor is concrete",
		"the drain was mostly empty black - it now has the tunnel arching overhead, the drain carrying on through an archway, a pipe run, a big cast iron sluice gate cracked open and pouring water, and a lantern down on the bank so theres something warm against the cold light from the manhole",
		"speckled dot noise removed from the den, which had been breaking one of the standing rules for a long time - the board shadow, the rug and the coins were all made of scattered loose pixels and are now actually drawn",
		"caught before it shipped: mara's head in the den used to sit exactly where the animated dial needle is drawn, so the needle would have been twitching on top of her hair",
	]],
	["v0.6.28", [
		"dying at the wheel could stand your body up on the pavement. if you pressed f to get out in the second or so after being killed, the game put the corpse down beside the car mid-fade. getting in already guarded against this, getting out only half did",
		"the handoff notes for two whole releases were never written, and nothing could tell. the check that guards these docs now fails the build if the current version isnt named in them - and it was proven by watching it fail on the real gap before it was filled",
		"a third pass over the written docs against the actual code, this time including the notes inside the code itself. thirteen wrong statements found and fixed - including one telling a future session that artwork for the guns already existed when none of it had ever been made",
	]],
	["v0.6.27", [
		"running the audio debug tool used to leave the whole game muted - permanently, on every future launch, with no sign of why. it turned the master volume down to test the slider and never turned it back up, and that setting is saved to disk. it now puts it back, and i tested that end to end rather than assuming",
		"thunder no longer keeps rolling over the main menu. if lightning struck a second or two before you got out, the clip carried on playing through the scene change and over the menu music",
		"dying at the wheel while the car door was still swinging open left the car door stuck open for the rest of the raid. getting in already handled this, getting out didnt",
	]],
	["v0.6.26", [
		"the menu and the studio card now reset the effects clock themselves instead of relying on the raid to tidy up on its way out. nothing was broken, but it meant one path was holding the whole thing up - and the guns coming in the next milestone lean on it constantly",
		"the camera kick and the hit flash were fading about a fifth too slowly during the freeze-frame on impact. a safety limit had been set just above the value it was meant to protect, so it was clamping the real number rather than guarding it",
	]],
	["v0.6.25", [
		"grey days. it can be dry without being sunny now - overcast is its own weather, flat and a little cold, and the sun doesnt break through it. before this, every day that wasnt raining was a sunny one",
	]],
	["v0.6.24", [
		"the car and truck labels on the map are much smaller. the games font only comes in one size, so this is a second font drawn from scratch at half the height rather than the old one shrunk down and blurred",
		"two vehicles parked together used to print their names on top of each other. now the second one waits its turn",
		"the safehouse moved to the open ground in the top right corner of the district. it was sitting in the middle of the playground",
	]],
	["v0.6.23", [
		"walking away from the lift no longer lets you extract from halfway across the district. that was my fault - a grace period meant for driving out through the toll gate had been applied to the lift as well",
		"you cant walk through the front of the extraction train any more. the engine sticks out further than its collision did, and there were gaps between the carriages too",
		"vehicles on the map are smaller dots now, and each one says whether its a car or a truck. trucks are blue, cars are amber",
		"trees drop the right leaves. which leaves a tree sheds is read straight off the tree itself now, so a green one cant drop autumn leaves",
		"a few turned trees out around the edges of the district",
	]],
	["v0.6.22", [
		"the sun gets into the district now. light rakes across the ground when its low - mid morning and late afternoon - and comes from a different side depending on which. nothing at noon when its overhead, nothing at night, and it shuts off when you step under a roof or when the weather turns",
	]],
	["v0.6.21", [
		"the time of day actually changes now. half past seven to five in the afternoon used to be one flat unchanging light - nearly forty percent of the day looking identical. the sun is low and warm in the morning, high and neutral at noon, and golden again by late afternoon",
		"the faint rings that followed you around the screen are gone. that was the darkening at the edges of the picture stepping in visible bands instead of fading smoothly",
		"rain and thunder are muffled when youre inside. the wall takes the top off them as you step through a door, and comes back as you step out. your own footsteps stay clear, because a wall you are standing behind doesnt muffle those",
	]],
	["v0.6.20", [
		"the new grade was making everything darker, your character most of all, because the cold shadow colour it was blending in is itself dark. it shifts the colour now without touching the brightness, and dark sprites keep their detail instead of going flat",
	]],
	["v0.6.19", [
		"the whole picture is graded now - more contrast, cold shadows against warm light, a glow on lamps and windows, and the corners pulled down. it shifts with the clock, so night doesnt look like day with the brightness turned off",
		"theres dust in the air. faint on purpose - its there to stop the space between you and the buildings looking like flat empty colour",
	]],
	["v0.6.18", [
		"shaders are built once between the studio card and the menu, so the first flash in a raid cant cost you a frame. it only happens after an update - restarting the game with nothing changed skips it entirely",
		"theres a compiling screen with a bar behind it, but it stays out of your way unless theres actually enough work to be worth showing",
	]],
	["v0.6.17", [
		"getting shot hits harder. the camera kicks, time holds for a fraction of a second, and the raider flashes white - none of which touches the artwork itself",
		"crashing a car shoves the screen, scaled by how hard you hit it, and close thunder gives the world a small shove of its own",
	]],
	["v0.6.16", [
		"the changelog is rewritten. the older entries were cut into fifty-character scraps to fit an old narrow window, so one sentence came out as five stubby bullets - sixty-five versions now say what actually changed and why, using the detail that was only ever in the developer notes",
		"the window is a little smaller again, and the text fills it properly instead of stopping halfway across",
	]],
	["v0.6.15", [
		"a test flag that does nothing now says so and exits, instead of leaving the game running forever in the background",
	]],
	["v0.6.14", [
		"the changelog window is much bigger, so there is a lot less scrolling",
		"the changelog button is hidden while the district select screen is open, it used to still be clickable underneath it",
		"the district description doesn't list every place twice any more, and it tells you the three ways out instead",
	]],
	["v0.6.13", [
		"the extraction train is solid. you could walk and drive straight through it before",
		"the freight countdown moved to the top middle, it was printing over the fps counter",
		"the map remembers where you left it. pan and zoom survive closing and reopening it",
	]],
	["v0.6.12", [
		"you could drive straight through the toll extraction before the counter finished. the zone is much bigger now, and clipping the edge of it at speed doesn't reset the count",
		"paying the warden lasts the whole raid. it used to buy one crossing, so you could drive back in, turn around, and get shot on the way out through a gate you already paid for",
		"the benches are benches. they had a one pixel seat, which is why they looked like a fence going up with nowhere to sit",
	]],
	["v0.6.11", [
		"the telegraph poles along the railway have wires now. they were just posts before",
		"the big power pylons keep to the woods and the outskirts. the middle of the district belongs to the telegraph line",
	]],
	["v0.6.10", [
		"opening a door from inside no longer cuts it in half. the wall was being drawn over the front of it, but a door swinging out toward you should cover the wall instead",
	]],
	["v0.6.9", [
		"doors swing away from you now. open one from outside and it goes into the room, open it from inside and it goes out to the street. it never shoves back at you",
	]],
	["v0.6.8", [
		"the second floor was clipping over the top of the house. every floorboard is now sorted on its own, so the walls in front of you cover it and the walls behind you do'nt",
	]],
	["v0.6.7", [
		"the upstairs floor is actually there now. the furniture was standing on nothing because the buildings own walls were being drawn on top of the floorboards, leaving only a strip of them showing",
		"dying and then abandoning the raid during the fade gave you two debrief screens stacked on each other. now whichever one gets there first is the one you get",
		"sniper rounds were appearing inside your view instead of flying in from off the screen. they were spawning at a distance picked for a much smaller window than the one you actually play in",
		"the maps place names stopped redrawing themselves every single frame while the map is open",
	]],
	["v0.6.6", [
		"doors are solid in every state now - shut, open, and while they're still swinging. the open leaf stands where the art actually draws it, a quarter turn into the room",
		"south facing doors were the ghost ones. their open collider was being placed a whole cell away on the wrong side of the doorway, so you walked straight through the panel",
		"east facing doors had half their leaf cut off the edge of the sprite and nobody noticed, because doors were the one thing the art build was told not to check",
		"the door frame beside the opening is solid too, so you can't slip through the boards next to an open door",
		"opening a door no longer clears the doorway on the first frame - for a quarter of a second you could walk through a door that still looked shut",
		"the test that was meant to catch all of this was moving the player a fraction of a pixel per step and never actually reached the door. it walks into them properly now",
	]],
	["v0.6.5", [
		"the warden gets a prompt while you're in a car, because that's how you'll always arrive at his window",
		"doors carry a second collider for the open leaf - though the open frames still need redrawing before that lands properly",
	]],
	["v0.6.4", [
		"the black lines running down every building are gone. each wall piece was drawing its own outline, so every join between them became a dark seam",
		"the gap between two of those outlines is what let you see your own arm through the wall. walls read as one surface now",
	]],
	["v0.6.3", [
		"the freight only runs three nights out of seven now, and which nights is different every week - two together and one at the far end, or spread out. you have to learn the timetable",
		"the cables inside houses are gone",
		"closed doors are covered by a test that walks into one from five different angles",
	]],
	["v0.6.2", [
		"opening a menu takes the world's labels down with it. press f to open, the driving hint, the freight's departure notice and mara's radio call all come off the screen while a window is up, and come back when you close it.",
		"they couldn't do that for themselves: most windows freeze the game, so the labels stop thinking at the exact moment they'd need to hide. the window takes them down now instead.",
		"whatever you were standing next to is let go of along with the prompt, so f can't reach through a menu and act on something behind it.",
	]],
	["v0.6.1", [
		"the power lines actually connect tower to tower now. the towers were being nudged a cell off the line like every other prop in the district, so a span could leave one crossarm and never reach the next. the run is dead straight, which is what a transmission line is.",
		"only a building or the railway can turn a tower away now. junk on the ground used to be enough, and every tower skipped took two spans with it - a pylon foot standing in the litter is fine.",
		"damage is the exception instead of the rule: about one tower in twenty-five is down and one span in twenty snapped, rather than a quarter of each. a stretch where most spans were broken just read as disconnected.",
		"a downed tower still gets the wire coming in to it, drawn as the snapped one - you see the line arrive and drop, instead of it stopping short of nothing.",
	]],
	["v0.6.0", [
		"the grid runs the width of the district: lattice towers with the wire sagging between them, deepest mid-span, hanging above everything - it crosses roads, pavements and shelters the way overhead lines do.",
		"a good deal of it is down. towers lean with a bent arm or stand snapped off above the waist with their cables trailing, and spans go missing altogether or end snapped in mid-air where the rest came down.",
		"the run walks to the comms relay and goes underground into a yellow cabinet on the back of the last tower, with the toolbox, drums and crate somebody left on the ground around it.",
	]],
	["v0.5.14", [
		"dying ends the raid now. three rounds used to fade to black and wake you at the safehouse like nothing had happened, which left dying cheaper than walking out. it hands you the same debrief instead: the doll, what you lost, who did it and where they hit you.",
		"it tidies up after you first - you're brought down off the second floor and out of the car, engine and lights off, before the screen comes up.",
	]],
	["v0.5.13", [
		"walking out of a raid isn't free any more. the pause menu says abandon raid, and it hands you the same debrief dying would - quitting mid-raid used to be a clean escape.",
		"the debrief reads like a report: how long you lasted, the xp, kills and raider kills, rounds taken, and what was lost with you - money for now, the haul once the stash lands.",
		"a doll marks where you were hit. every round records the part and the man who sent it, the doll reddens with the count, one tick per round, and the list underneath gives the minute, the part and the shooter - thorax, stomach, head, eyes, arms, legs.",
		"the snipers roll a real hit location now: centre mass most of the time, with the head, eyes and limbs taking the rest.",
	]],
	["v0.5.12", [
		"every place has its own things in it now - four to seven pieces each, belonging there and nowhere else. enough to know where you are without the place looking dumped.",
		"planters, benches, a vending machine and a news box round the dry fountain in the courtyard. fare boxes, tyres, drums and a mechanic's leavings among the buses at the depot. tyres to climb on, a bench and litter in the grass at the playground.",
		"cans, pallets and a dumpster at the gallery - what the painters brought and never took home. cable drums, a toolbox and the crate the dish came in at the relay. sleepers, drums and gear beside the running line in the yard.",
		"fuel and freight stacked round the rim of the lift clearing, which stays clear enough to land in, and the warden's own chair, brazier and crates just off his booth.",
	]],
	["v0.5.11", [
		"freight moved to where freight belongs. the crates and shelves are out of the scrapyard and piled around the warehouses instead: two or three times the stock in the yards, stacks spilling out of the doors, loaded shelving stood against the outside wall, trucks backed up with their load at the tailgate, and the halls packed inside.",
		"a scrapyard is where things get taken apart, so it keeps the machines - the vehicle rows, the crane, forklifts, drums, gas cylinders and toolboxes standing open where somebody put them down.",
		"no more foggy on the weather line. the mist rolls in every morning, so reporting it as a forecast said nothing. the weather is clear, rain or storm now, and the morning still reads morning mist because that's a time of day.",
	]],
	["v0.5.10", [
		"rain and storms are genuinely different weather now. a storm rains at full strength and throws lightning every 7 to 19 seconds; plain rain is visibly lighter and only flashes every 45 seconds to a couple of minutes. clear runs longest.",
		"fog is its own weather as well, rolling in and out over about 18 seconds, on top of the dawn mist that was always there.",
		"the map bar reads the clock, the part of the day and the weather - 07:12 morning - raining. dawn, morning, afternoon, evening or night.",
		"court and depot are courtyard and bus depot now, and the lz, gallery, comms relay, trainyard, scrapyard and playground are outlined on the map like the paved places, so they read as somewhere instead of a word floating over open ground.",
	]],
	["v0.5.9", [
		"the clock and the light agree now: dawn at 06:00, full daylight by 07:30, the light going warm from 20:00, dusk at 21:00, dark by 22:15 and still dark at 05:00 - night is about nine hours of the day",
		"the dawn fog moved with dawn, a raid now starts at 07:12 instead of 04:19, and the freight's midnight arrival sits deeper in the dark than it used to",
		"master volume at zero silences everything now - it pulls music, effects and ambient down with it instead of only leaning on the master",
		"the broken power boxes throw blue sparks: two to four thrown clear of the housing on each burst, arcing out, falling and burning out. blue is what a real short throws, and it reads against the warm arc inside the box",
	]],
	["v0.5.8", [
		"the map select screen shows the district's clock and whether it's day or night, ticking, before you commit - and the time you read there is the time you deploy into",
		"there is one world clock now. the district keeps its own time while you sit in the menu, and the raid picks it up exactly where the menu left it",
	]],
	["v0.5.7", [
		"the freight keeps a timetable now: she comes at 24:00, the darkest point of the night, once per day. she was running on a five minute clock before, which is why she kept turning up in the morning",
		"mara calls her in just before she arrives, so the warning and the train are the same event, and she has stopped promising another one in five minutes - the freight is back tomorrow night",
		"the day is longer: a full cycle runs eighteen minutes now instead of ten, so the light takes its time getting anywhere",
		"mara's calls hold on screen 6.5 seconds instead of 4.6, the name plate is gone, and she doesn't say her own name twice in three words anymore. she keys up with a very quiet tick and still drops off in silence",
		"stranded boxcars sit beside the running line on the ballast now instead of on it - the freight used to drive straight through one. the sidings keep their rolling stock",
	]],
	["v0.5.6", [
		"every house has a light inside now: a tin shade on a short flex hung mid-room. they come on with the dark and about a third of them flicker and drop out the way a bad supply does. the pool is deliberately tight - a wide one washed straight through the walls and lit the street",
		"every light has a cable you can follow across the floor to the power box on the outside wall. anything that draws power has to show where the power comes from",
		"the safehouse is wired the same way and stays dark - its box is the broken, arcing one, so the flex is there and nothing comes down it. that's the whole reason it's a repair job later",
	]],
	["v0.5.5", [
		"pines shed now, and they drop needles rather than leaves - a fresh green and a dried tan, both a touch brighter than the canopy so they don't vanish into the forest floor. a needle has no blade to catch the air, so it falls straight down with a slight lean, faster than a leaf and from tighter in against the trunk",
		"dead bare snags still drop nothing, on purpose",
	]],
	["v0.5.4", [
		"transit isn't laid out on graph paper any more. every road carries a length now and most of them stop short - the council never finished this district. the middle road past the toll and two crosstown roads run edge to edge; the other five stop, one of them at both ends, and the north-west and north-east corners have no road at all",
		"where a road gives up, the last few slabs crack and pothole and the cut is buried under rubble, with the odd barrel and stick spilled a couple of paces past the end",
		"pavements, crossings, traffic lights, street lamps and the level crossing signals all follow the new lengths - no walkway running off past a road that was never built, no zebra crossing to nowhere, no lit pole standing on unpaved ground",
		"every building, every place and your safehouse are exactly where they were; only the road network changed, and the map screen draws the real thing, stubs and all",
	]],
	["v0.5.3", [
		"the stutter the first time you open the changelog is gone. it was building every line of every version in the frame you clicked it - it does that during the menu's own fade-in now, a slice at a time, so the first open has nothing left to pay for",
		"the map's first-open dip went the same way: it used to draw the whole district in one frame. it takes that draw behind the deploying screen now, so the first press of m is already warm",
	]],
	["v0.5.2", [
		"the yellow centre line finally runs down the middle of the road. measured before the fix it sat almost a full lane out; measured after, it straddles the true centre, with the dash exactly as thick as it was",
		"two things were wrong at once. half of every dash was painted onto the part of the tile that its neighbour owns, so it rendered as nothing at all - and the two road directions lay their tiles out opposite ways, so whatever suited one was wrong for the other. that's why it looked right on half the roads and a lane off on the rest",
	]],
	["v0.5.1", [
		"bus shelters stopped parking half in the road at crossings. a shelter is longer than the spot it stands on, so one built beside an intersection hung its roof and glass out over the asphalt.",
		"any shelter whose length would reach a crossing road simply doesn't get built there now. the ones standing in legitimate places are untouched, and nothing else on the street moved.",
	]],
	["v0.5.0", [
		"settings grew a volume page: master, music, effects and ambient each get their own slider. changes apply the moment you drag them and stick between sessions.",
		"everything is sorted properly underneath - footsteps, doors, horns and the car alarm ride effects; the rain, the thunder and the engine bed ride ambient - so pulling one down leaves the rest alone.",
		"the page opens from the pause menu as well as the main menu, and esc steps back out of it.",
	]],
	["v0.4.14", [
		"the broken, sparking power box is always the safehouse's own now - lid hanging open, arcing away beside your own front door. somebody should really fix that.",
		"mara's radio popup is silent both ways: no chirp when she keys up, and none when she drops off.",
	]],
	["v0.4.13", [
		"your car finally faces the way you're driving. the side-on sprites were wrong twice over - the body drawn facing one way, the headlights and tail lamps painted on the wrong ends, and then the left and right versions registered the wrong way round.",
		"the open-door frames and the light positions follow the fix. the diagonal and head-on views were already right and haven't been touched.",
		"steering is instant now: tap a direction, or two together for a diagonal, and the nose snaps straight to it. the slow carve is gone. speed, braking, coasting and crashes feel exactly the same.",
	]],
	["v0.4.12", [
		"housekeeping: the audits turned up a pile of code and artwork nothing calls anymore - helpers with no callers, signals nobody listens to, sprites the world never places. all of it deleted.",
		"the game draws and plays exactly the same - every surviving sprite came out identical to the pixel - there's just less of it left for the next bug to hide in.",
	]],
	["v0.4.11", [
		"the sweep, part two: the remaining fifteen findings, and not one of them was quiet.",
		"dying on the rope used to strand the helicopter in the sky and quietly kill every other way out for the rest of the raid. death now aborts the lift cleanly and the bird goes home.",
		"you can't walk or drive away from your own lift anymore - the rope really does freeze you - and the countdown won't run while you're sat in a car. it takes a raider, not a sedan.",
		"paying the warden buys one crossing now. come back inside the wire and the snipers shoulder their rifles again, and dying re-arms them too. before, one payment blinded the whole ring for the rest of the raid.",
		"dying at the wheel left the car running with its headlights burning all night, and the next person to get in had the light switch backwards. death shuts it all down properly now.",
		"the ground floor door under a second story could be left hanging open when you climbed, and an open doorway up there is a hole you can walk out of. it now shuts from any state, mid-swing included.",
		"a knocked-over barricade could land on top of the toll booth, and in transit one did - the barricade line was being laid before the booth was there. the booth's ground is reserved first now, and nothing else in the district moved.",
		"the safehouse's overlap checks were running before the courtyard, the depot and the gallery even existed, so they never checked anything. the plaza and the apron paint around your spawn house instead.",
		"power box sparks were re-rolling every frame at 240hz, which reads as shimmer rather than electricity - each arc holds for a fraction of a second now. the smoker's exhale showed all its wisps at once, fully lit; they drift off one at a time now, like smoke does.",
		"the deploy tail lost its last unbudgeted stalls - the map bake and the final whole-district passes tick on the same frame budget as everything else, the freight stopped re-reading a large file it already had, and the smoke column at the lift stops working once it's off screen.",
	]],
	["v0.4.10", [
		"a code sweep read the whole game end to end. these are the bad ones.",
		"quitting to the menu with a window still open bricked every raid after it. the next deploy read no input at all - esc and m were dead too, so there was no way out but killing the game. every screen starts from a clean slate now.",
		"dying aboard the freight was an unrecoverable softlock: after the fade you were put back onto the departed train every frame, invisible, unable to move or be touched. respawning clears the ride properly now.",
		"the first train was nearly ten minutes late, not twenty seconds - the cycle clock was running with its sign flipped, which makes the last update's note about it flatly wrong.",
		"extracting worked underneath an open map, which then poisoned everything after it. extraction stands down while any window is up now, and the green counter no longer sits over the death fade.",
		"snipers could still hit you up to a second after you'd paid the warden or boarded the train - rounds already queued kept coming out. they get dropped now.",
		"the outer rim of the district was bare: no lamps, no lone trees, no vehicles, no puddles, no litter. when the wire moved inward the content margin never followed, so everything stopped well short of the barricades.",
		"half the street scatter was never being placed - junk piles counted twice against the budget, so the streets ran out of clutter early.",
		"rain and the engine bed kept playing under the main menu after you quit a raid, and could carry into the next one.",
		"a few things outlived the raid that made them: the death sequence could resume on a dead one, mara could speak from nowhere, and lightning could clap thunder over the main menu.",
	]],
	["v0.4.9", [
		"loading into transit had a 233 millisecond stall in it - the frame drop you could see. it was a developer contact sheet: half a megabyte of artwork the game never shows, decoded and uploaded every single raid.",
		"it doesn't sit with the game's art anymore. the worst frame of a deploy went from 233ms down to 29ms, and that last one is the menu to game switch itself.",
	]],
	["v0.4.8", [
		"the snipers stand down once you're riding the freight out, the same way paying the warden does. catching the train is a real way out of the district, not a death sentence.",
		"the first freight comes in twenty seconds after you land instead of forty-five - the old wait just read as the train being late. after that she's back every five minutes as before.",
		"she carries her own light now, because she runs at night: a headlamp thrown down the rails ahead of her and a warm spill out of the cab windows.",
		"steam breathes off the stack - slow while she stands in the yard, much harder once she's pulling away.",
		"mara's radio sits small and centred at the top instead of filling the corner of the screen - the old panel pulled your eye off the world every time she keyed up.",
	]],
	["v0.4.7", [
		"the freight engine was missing its back end - the exact bug the cars had, an end drawn as a stub off the corner instead of a wall across the body, so the loco looked sawn off. the cab end is a proper wall now, with a lit top rim, a sill, red marker lamps and a cab window.",
		"the nose got the same treatment: the side wraps round the corner properly and the coupler plate is rebuilt.",
	]],
	["v0.4.6", [
		"the map shows which way you're facing. your marker draws a cone pointing where the raider is looking, so it tells you which way to walk instead of only where you're standing.",
		"while you're driving the cone follows the car's heading, so the map still reads right from behind the wheel.",
	]],
	["v0.4.5", [
		"furniture stopped repeating. every table, chair, bookshelf, cabinet, couch, tv stand and bed in the district was the same single sprite - there are four or five of each now, every one worn its own way and set at its own slight lean.",
		"furniture only leans a little, on purpose: a cabinet tipped over like a crate reads as falling down, not as lived in.",
		"racks went from four versions to seven, after two identical ones turned up standing side by side in a yard.",
		"and nothing picks the same version twice in a row anymore, which is the repeat the eye actually catches.",
	]],
	["v0.4.4", [
		"the district is bigger - roughly a quarter wider edge to edge. every block has more room, and the scrapyard hall builds as a proper warehouse again instead of shrinking to squeeze past the rails.",
		"one railway the whole way across: wooden ties under steel rail, the identical tile end to end, properly connected.",
		"the worn and overgrown stretches of track are gone - they broke the line into what read as separate broken bits of railway. the poles, signals and lineside junk beside it stay, the track surface was the problem, not them.",
	]],
	["v0.4.2", [
		"the scrapyard warehouse is back. stopping it being built on top of the railway had quietly deleted it instead, which put the racks and crates back out in the open with no building around them.",
		"it now searches for smaller and smaller footprints until one fits clear of the track and the crossings, rather than giving up. a smaller hall is still a hall; no hall was the old bug.",
	]],
	["v0.4.1", [
		"the rail line reads as a railway instead of a drawn line. real mainlines are straight, so the fix wasn't to bend it - it was to put things alongside it at human spacing.",
		"telegraph poles march the whole run at uneven gaps and swap sides of the track here and there, in different heights and leans, and one in three has lost a crossarm.",
		"colour-light signals stand where they'd really stand, on the approach to each level crossing and at the throat of the yard. most are dead; one still shows an aspect.",
		"junk piles up along the ballast, because that is where a railway collects things.",
		"the track wears in stretches rather than tile by tile: a run of overgrown ballast with grass up between the rails, a run of rusted rail with the odd tie rotted away, then clean again.",
	]],
	["v0.4.0", [
		"the night freight runs. a locomotive hauling two cars slides into the trainyard every five real minutes, stands for exactly one, and leaves whether you're aboard or not - miss her and you wait five minutes or you walk.",
		"press f to get on while she stands, then departing in 10... and she pulls away slowly, builds speed down the rails and off the map into your debrief.",
		"the engine is unmistakable next to the dead stock in the yard: longer than a boxcar, taller at the cab, charcoal with an amber stripe, warm lit cab windows, a burning headlight and a stack.",
		"mara calls her in twenty seconds out, tells you when the wait is down to twenty-five, tells you to sit tight once you're aboard, and tells you off when she rolls without you. her calls queue up instead of talking over each other.",
		"you can hear the mic key up and drop either side of every transmission, and her horn carries right across the district.",
	]],
	["v0.3.14", [
		"leaves fall from every leafy tree now - the oaks, the autumn grove and the bushes all shed, and the trees near you take turns, so no single tree gets spammed while the one beside it drops nothing. the same amount falls overall, it just comes from more places",
		"pines and dead bare snags keep theirs, on purpose. a conifer used to be able to win the coin flip and drop broadleaf leaves out of its needles, while a lone oak lost it and stood there inert all raid",
		"a building could stand on the railway. the scrapyard hall now hunts for a footprint clear of track, ballast and crossings, and if there isn't one it simply doesn't get built",
	]],
	["v0.3.13", [
		"the second way out: the toll gate. where the middle road breaches the wire on the south side there is a booth with a lit serving window, a warden sitting in it, and a striped boom lying across the asphalt",
		"pull up in a car and press f - at the wheel it talks to him instead of getting you out, because the whole point of the gate is that you drive to it. walking up works the same way",
		"his window opens with his face in it and three answers: a reply that shows the line you'd actually say and changes every time, pay 30 to extract, or back away",
		"he has 26 things to say and 14 ways to answer him, never the same one twice running, and he never runs out - the eleven gates he's worked, his brother on the harbour gate, the raider who cried at this window, and how much he's made off people like you",
		"pay him and the boom goes up, the snipers on the wire look away, and driving out past the line starts the green counter and hands you the debrief",
		"the toll gate and the landing zone are named places on the map now",
	]],
	["v0.3.12", [
		"clutter looks dumped now, not placed. crates went from six versions to ten, tires from four to seven, pallets three to six and rubble four to seven - each one leaning its own way and worn its own way, so it reads as a different object instead of the same one stamped down again",
		"junk piles up unevenly: a heavy piece with stragglers thinning out and spilling off one side along the lean, rather than tidy stacks. a quarter of the barrels, tires and rubble on the street land as heaps, and over half the scrapyard does - it's where things get dumped",
		"nothing hands you the same version twice in a row. two identical things side by side is what the eye catches first",
	]],
	["v0.3.11", [
		"you can only interact with what the prompt is offering. doors answered from a good deal further back than the game ever said they would, and cars further still - it told you at one distance and acted at another. one distance decides both now, so if the prompt isn't up, f does nothing",
		"every prompt works this way, and every new one will inherit it - which matters with the toll warden, the freight and the tunnel ladders coming",
	]],
	["v0.3.10", [
		"you can get out. the first way out is the lift: a clearing off a dirt track, stamped flat, a worn marker painted on the ground, waiting-room junk round the rim and a beacon in the middle pushing green smoke that reads at noon as well as at midnight",
		"stand in it and it counts you down from five on its own. then a helicopter comes in over the treeline with its rotor turning, hangs a rope, and pulls you up out of the district",
		"then the debrief: how you got out, how long you lasted, the xp, the kill count, and every kill listed with the minute and the bone. the haul column stays empty until the stash arrives",
		"an exit can count you down on its own or wait to be opened by something else - the toll gate and the night freight are next",
	]],
	["v0.3.9", [
		"the map is drawn now, not screenshotted. roads are real edged strokes, the woods are soft overlapping green, buildings are solid footprints with a lit north edge and a soft core where there's an upstairs, the rail has ties, and the wire is a dashed red ring around the district",
		"no boxes around anything. names sit straight on the map with a dark halo behind them, the blocks sit a hair off the ground colour instead of reading as panels, and home is a thin amber ring round the safehouse - the old bright slab was swallowing your marker while you stood on it",
		"you are a pulsing disc with a ring, four cross ticks and a bright core, and you can pick yourself out over roads, woods or rooftops",
		"it opens at the scale that fits the whole district in the window, and the wheel zooms smoothly under the cursor instead of jumping between whole steps - that ladder only existed because the map used to be a picture",
	]],
	["v0.3.8", [
		"whatever window you have open owns the screen, and nothing behind it listens - the world used to keep reading your input the whole time a window was up",
		"esc closes the map instead of opening the pause menu behind it, the scroll wheel zooms the map or the world but never both at once, no window can open behind another, and dying with the map open no longer wedges it there",
		"every window says how to leave it - the cordon screen gave you no way of knowing",
		"lore: rewritten at the top so the first thing it says is unmissable - every enemy is a human being, no robots, drones, monsters or infected, ever. where the mills chapter said machines it meant looms, presses and furnaces, and now says so. transit is written down as a real place, with what sits where",
	]],
	["v0.3.7", [
		"cars point where they're going. the four angles the old sheets could never draw exist now - side on, with the flank facing you dead on and the roof lying as a flat band above it, and head on as solid bands of end face, hood, glass and roof. a car keeps its shape whichever way it's pointed",
		"every vehicle got wider. they were narrower than real cars - you couldn't see it on the diagonals, but head on they'd have read as a plank, and they sit more solidly on the road now",
		"new controls: get in and the engine starts itself, get out and it shuts off. wasd drives all eight headings, e for the lights, f in and out. the engine key is gone, and so is clicking to follow the cursor",
		"the car still carves toward your steering and turns tighter as you slow, and one crossing the map north to south now covers ground at the rate the tiles imply",
	]],
	["v0.3.6", [
		"the map is a real map now: press m and it opens near-fullscreen at the biggest zoom that still fits the whole district, centred, with every place named on it, a pulsing marker for you that moves as you move, and live dots for the cars",
		"clicking transit finally opens the district - the window used to eat the click and nothing happened. the tile shows a live crop of the real map, with the three sealed districts on the board beside it",
		"the map draws the trees in their true colours, so the autumn grove reads rust, and it shows the wire ring around the district and a bright outline on your safehouse",
		"second floors read like floors now: wood boards throughout, a lit edge along every open side, and the town is guaranteed at least four two-story houses - the fixed map had rolled none at all",
		"the school is a school again after standing nearly empty for two versions: a chalkboard with chalk ghosts still on it, a teacher's desk, and rows of desks and chairs facing the front",
		"the safehouse got a small parking pad with one car that never sets its alarm off - it reads as yours. the fence ring is thinner, and no power box hangs under a window anywhere in the district now",
		"bushes and benches are solid things instead of stickers - lumpy lit crowns with dark undersides, and benches built as boxes with a grooved top face and two-tone legs",
		"driving has weight to it: the car carves toward the cursor and its turns tighten as you slow, every real crash lands a soft thump, full-speed hits puff smoke off the impact, and the controls card stays up twelve seconds with the keys picked out in amber",
		"the static at full speed is gone - the engine sound was being re-pitched hundreds of times a second, which dragged its hiss into earshot. leaf brushing goes quiet while you drive, too",
		"dirt trails stopped painting straight across the sidewalks, and the two halves of a yellow dash live and die together instead of leaving orphan halves off the middle of the road",
	]],
	["v0.3.5", [
		"the district is fixed now. every raid builds the same transit - the same streets, the same houses, the same yards - chosen by auditioning five candidate layouts. learn it, because quests will hand out addresses. only the weather and the time still change raid to raid",
		"the scrapyard got its own warehouse back, so the rack line out front reads as its overflow instead of shelves and boxes standing in the open",
		"bushes are walk-in cover: taller than you are standing, and you fade to half along with the bush while you're inside, so you always know when you're hidden. the rummage is a slow lazy sway now instead of a shiver, and the rustle carries going in",
		"the gallery regular is your size at last, sitting on benches built for grown raiders, and his spray cans come four ways - different colours and counts, standing, tipped or crushed, with dried spills. no more two identical drops",
		"under the hood: one real placement bug dead, three build steps that used to hitch now spread their work out, and the world runs leaner - the bushes, the street lamps and the car alarms all stop doing work when nothing is happening",
	]],
	["v0.3.4", [
		"the bushes grew up - chest-high mounds instead of little clumps, big enough to disappear into. they're still walk-through on purpose; hiding from people in them comes when the people do",
		"half the woods turned: the east side of the forest is an autumn grove of orange and red oaks, and leaf fall is colour-true now - red leaves only come off those, and green trees drop green. the comms relay clearing sits right against it",
	]],
	["v0.3.3", [
		"you start in the safehouse now - the same squat house near the south edge every raid, ringed by lattice fence with a gap at the door and pylons on the corners, a couch and a crate inside, and a spawn spot that can never leave you wedged behind the furniture",
		"cars drive free on the cursor instead of stepping between four fixed directions, and the top speed came down from a rocket to something you can actually steer",
		"real collision at last: cars, buses and boxcars block along their whole body instead of leaving the nose and tail open, tree trunks and lamp posts push back, and pallets stop your feet instead of swallowing them",
		"bushes stay walk-through on purpose - that's what the rustle is for",
		"trucks stopped flashing a different colour for a second when you open the door. the door frame is the same truck now, down to its rust",
		"the warehouse always gets built - racks and stock standing out in the open with no building around them was the bug you screenshotted",
		"the comms relay moved out to the edge of the woods where it belongs, and the gallery keeps the open block",
		"half of all trees and bushes shed leaves now, and they drop more often",
		"the fleet got new paint - steel blue and tan join the lot, and matching trucks are far less likely to turn up as twins",
		"one yellow line per road, dead centre, where it was painted - the two halves used to sit on the outer edges",
		"stairs sit in the corner of a room now, and you can't use the ground floor door from upstairs. it shuts itself as you climb, so you can't walk out of the building mid-air",
	]],
	["v0.3.2", [
		"press m for the map. the first open shows the cordon - transit in the middle, three sealed districts under question marks - and clicking transit opens the district itself, drawn from the same plans the ground is built from",
		"drag to pan, scroll to zoom in on the cursor, and hover anything for a tooltip. it shows where you are, where the cars are, the time and the weather, on both views",
		"play replaces deploy on the menu: you pick your raid off the cordon map now, with a painted preview of transit and a few words about it, and deploy from there",
		"two new places: the scrapyard, rows of dead and driveable vehicles with two forklifts, industrial racks and one lattice crane, and the gallery - free-standing graffiti walls, spray cans, benches, and a man who sits there working a cigarette",
		"the walkways picked up vending machines and newspaper boxes, and there are roughly twice as many dumpsters",
		"every house has a power box on its wall, and exactly one in the district hangs open with its wires out, sparking every few seconds",
		"driving changed: one click and the car chases the cursor at full throttle, click again and it rolls down to idle. doors, engine and alarms all sit quieter, and the alarm flashers throw real light at night",
		"bushes and falling leaves actually work now - both were quietly broken. push into a bush and it rustles the whole time you're inside, and leaves come off the trees you can actually see instead of one tree somewhere across the district",
		"one thunder per flash, and it stopped cutting itself off halfway. rain is a step quieter, thunder a hair louder",
		"upstairs has a real floor - the stairwell hole used to show you the ground - and your flashlight rides up with you instead of sitting inside you",
		"worn dirt trails link the houses and the courtyard, pausing at every road and sidewalk and picking up again on the far side",
		"the yellow line sits on the true middle of the road, the broken sidewalk slabs lost their little green weeds, and the district is a bit smaller again",
		"your raider stands a touch taller in every stance, and prone got real shoulders instead of a stick",
		"the den's job board reads like a board now - district names in tall ink with underlines, every sheet hanging off its own coloured pin - and the splash takes its time so you can watch the signal go out",
	]],
	["v0.3.1", [
		"the map got way smaller again, under half the area, and what's left is zoned into real places instead of one long sprawl: two blocks of town, two of forest, the warehouses, the school, the trainyard, the bus depot, and an open block holding the comms relay",
		"the town is houses packed around a paved courtyard - plaza pavers, a dry fountain, overgrown planters and benches. you start on its southern lip",
		"about half the town houses and the school grew a second floor: taller walls, stacked windows, a transom over the door, and wooden stairs inside. press f at them to climb, and upstairs you only ever see the room you're in",
		"new places: the school and its playground - swings, slide, sandbox, flagpole and a sign you can't read; a trainyard with a rail line crossing the whole district, sidings and boxcars; the bus depot and its rank of buses; and a fenced comms relay pointing at nothing",
		"cars drive now: f to get in, q to wake the engine, w and s for throttle and reverse, a and d to steer, e for the headlights, f again to step out beside the door. a short crash course shows when you get in, and boarding an armed car shuts its alarm up for good",
		"windows are glass instead of black holes - blue panes with a diagonal sheen and a cross through the middle. boarded ones keep their planks",
		"sidewalks run the full length of every road side, so grass never touches asphalt, and the roads themselves keep only their cracks and potholes - nothing else is painted on them",
		"the world is quieter: far less scattered junk, far fewer lone trees, and fewer bodies, wreck pieces and puddles",
		"fog comes in mixed sizes now and breathes in instead of popping into existence, and it drifts about twice as far before it dissolves",
		"music fades in and out longer and softer everywhere, and the storm menu backdrop is retired - the den and the drain rotate",
	]],
	["v0.3.0", [
		"morning fog: soft mist banks drift through the woods and along the roads through a window at dawn, pushed by that morning's wind, then thin out and go",
		"leaves fall - a quarter of the oaks shed, and every leaf takes two to four seconds to come down, swaying, zigzagging or riding the wind before it fades out",
		"a full day is ten minutes now, down from twenty, and the nights are properly hard to see. night is about a quarter of the loop, nightfall leans blue-violet, and the lamps and your flashlight come up together as it goes",
		"raid tracks bow out on a fade instead of stopping dead, with about thirty seconds of quiet between them. the rain wash eases in and out rather than switching on and sits quieter, and thunder is softer and follows the flash faster",
	]],
	["v0.2.14", [
		"raid music is your three picks - guitar, harp and piano, kept out of the twenty-three you listened through - rotating at random and never the same one twice in a row",
		"the music runs from the start of the raid until you die, with only a couple of seconds between tracks. the old minute-and-a-half silences read as broken audio. dying stops it, respawning starts it again",
		"the roads are smooth now and the damage lives in its own tiles: wandering cracks and the odd chipped pothole. sidewalks are clean jointed slabs, some hairline-cracked, some broken open to the dirt",
		"the world grew little lives: bushes in the greens and against the buildings that rustle, wiggle and fade around you when you push through, grass tufts coming up through bare concrete, and benches and bus shelters along the walkways",
		"anywhere a whole corner scanned empty now gets a tuft, a bush or a scrap of litter dropped into it",
		"colour fixes: forest floors are green only - the old warm-brown patches read as red confetti through every wood - and the dirt paths mix in grey mud so long stretches stop looking blood-red",
	]],
	["v0.2.13", [
		"three new menu backdrops, and every one of them is alive. the den: kettle, verne and mara at home in two-tone light, candle against radio glow, with the job board pinning every district and transit ringed in red.",
		"the drain is the tunnel under the district seen side on - one shaft of light down an open manhole, dust sinking through it, drips ringing the water, a ladder and somebody's cache.",
		"the storm is the whole sealed city under a cloud deck: rain that gusts on the strikes, double-flash lightning that edge-lights the skyline, forked bolts, thunder that arrives late, and building windows that flicker, brown out, die and struggle back.",
		"quiet music drifts through raids now - three sparse loops, felt more than heard, with long silences between them. the menu keeps its guitar theme.",
		"the single-pixel grit is gone everywhere: surfaces wear in small honest patches, the menu paintings light in bands, and dirt shows ruts, clods and stones instead of red noise.",
		"far more variety baked into the ground - asphalt, screed, house wood, forest floor, dirt, sidewalks and roof tiles all gained versions, and plain wall segments roll between three, so a long wall never repeats one image.",
	]],
	["v0.2.12", [
		"the district is about half the area it was - the barricade ring moved a long way in and the roads, buildings, woods and scatter all pack into a tighter core. no more hiking, and the sniper buffer past the ring is more than twice as deep.",
		"streets grew furniture: pale slab sidewalks flanking many roads, about one slab in eight cracked open to the dirt with weeds in the bite, worn-down crosswalks on every arm of every intersection, the odd manhole in the asphalt, and dead traffic lights at the crossings - one municipal design in five states, dark, bent, smashed with the wire dangling, or knocked flat.",
		"the ground has moods now: two new concrete tones, sun-worn and damp mossy, laid in district-wide zones so whole blocks read differently aged, with the borders dissolving into grain rather than a visible patch grid.",
		"warehouses are proper industrial halls - up to five racks and roughly double the floor stock. the racks are wider and deeper, and the boxes look human-stacked: staggered heights, shoved together, mixed sizes, nothing square to the grid.",
		"snipers lead their shots. they aim where you are going to be, each shooter over or under leading a little, and volleys stagger across a fraction of a second so you hear separate cracks instead of one wall of fire.",
		"the turn-back warning sits dead centre, a touch above the middle, on any resolution.",
		"locked into the plan: the underground tunnels - bookshelf passages in some houses and two manholes you can actually climb down - arrive with the guns update.",
	]],
	["v0.2.11", [
		"cars and trucks have real backs and fronts now, and that is the end of that saga. you circled it and that was it: the end was drawn as a short stub carrying on off the near corner, so the rear read as hanging out beside the body instead of closing it. it is a full-width wall now - tailgate on the pickups, trunk on the cars, grille on anything coming at you - with lights at both corners, a shutline and a bumper strip.",
		"real recorded audio arrives. the menu theme is a lonely guitar loop from davidkbd's the last pack, footsteps are real recordings for each surface and mixed quieter than before, and thunder is cut from an actual storm field recording instead of the synth burst that sounded like a blowtorch lighting.",
		"the ui blips, door thunks, sniper crack, flashlight click, rain bed and car alarms stay made by code - those were already right.",
	]],
	["v0.2.10", [
		"the car end caps rolled back to the original dark look - the brightened ones from the visibility fix read worse. your call.",
		"the rest of that pass stayed: the raked ramp fills, the smaller wheel arches, and the broken car's door hanging attached at the sill.",
	]],
	["v0.2.9", [
		"everything reads three-dimensional now, the way the barrels and the cars do. pillars are true iso columns with diamond caps, a lit west face, a shaded east face and a plinth at the base; snapped ones show a rough broken top with the rebar sticking out.",
		"upright gas cylinders got rounded shoulders, domed crowns, valve stubs and safety bands that curve round with the body.",
		"tire stacks are stacked rings - the top tire shows its tread and the dark hole down the middle.",
		"rubble piles have a lit western slope, a shaded eastern one, a bright crest along the top and dark contact where they meet the ground.",
	]],
	["v0.2.8", [
		"the car ends were there all along, just painted invisible. the caps used each paint scheme's darkest tone and vanished against dark asphalt, which is why they kept reading as missing through three separate geometry fixes. they use the mid body tone now, with a lit top edge and a visible steel bumper.",
		"the wheel arch carve was oversized and bit clean through the hood and trunk sections - it is smaller now and stays below the trim.",
		"a broken-into car's open door hinges attached at the sill instead of floating underneath the body.",
		"holes in ruined roofs show attic darkness instead of whatever happened to be rendering underneath - usually the exterior ground, projected wrong, sometimes wall pieces.",
		"sniper volleys converge: two or three rounds arrive at once from different off-screen angles on a single crack, and they fly at 1150 pixels a second. dodging on reaction should barely work.",
		"zoom reworked - the overpowered zoom-out is gone (native is as wide as the view ever gets), the ladder reaches 6x, and it glides between stops, always resting on a whole pixel factor.",
	]],
	["v0.2.7", [
		"the missing car parts are actually fixed this time. the raked windshield and trunk ramps climbed two pixels at a time between strokes, leaving ladder gaps in the roof plane - that was the real hole. the ramps bridge every step now.",
		"barrels are properly 3d: an elliptical top face, walls hanging off the curve, and hoops that follow it round. no more flat front-on drums.",
		"the barricade line is lattice fencing, the style you pointed at - dense diagonal mesh as the dominant piece, concrete jerseys demoted to accents, tighter runs and smaller gaps. roads can no longer generate running parallel along the ring.",
		"the mouse wheel zooms on a whole-factor ladder: two steps in, one honest step out. near the barricade line the camera tightens a step by itself so the true edge of the world can never scroll into view, and rain coverage and sniper distances scale with the view.",
		"the day cycle can't visibly step any more - an imperceptible film of grain breaks up the full-screen brightness jumps you were seeing click past every couple of seconds.",
		"lightning comes in bursts of one, two or three strikes, each with its own flash and its own rolling thunder.",
		"footsteps rebuilt surface by surface: a crisp tick on concrete, a low thud on asphalt, a hollow two-tone knock on wood, a slow brush through grass, a grainy crunch on dirt - and all of it quieter.",
		"rain is a soft distant wash now. the old bed fired something like 176 random pops a second - that was the crackle - and looped audibly every two seconds; this one drifts and never repeats to the ear. car alarms lost their static edge too, every pulse ramping in and out instead of switching on hard.",
		"the splash goes into the menu as one continuous dip to black. the hard cut into a fully formed menu read as a glitch.",
		"boxes belong to industry: crates, stacks and pallets only spawn around warehouses and their yards, never out on the open street.",
		"the art pipeline now refuses to ship a sprite with pixels clipped at the edge of its canvas, and everything it caught is fixed - the tv stand from your screenshot, the couch, the dumpster, racks, crates, cylinders, a single tire, the fallen pillar, roof vents and hatches, bottles, paper, every barricade and the bodies.",
	]],
	["v0.2.6", [
		"the sapphire signal splash: the gem wakes, broadcasts rings out with a sonar ping, and the first beam sweeps across to reveal the studio name in the game font. any input skips it. the game boots into it before the menu now.",
		"the main menu has music - a dark ambient theme in a minor, made entirely by code: a detuned low drone, slow pad swells, a lonely echoing motif and a breath of wind, looping seamlessly and fading out under the deploy screen.",
		"footsteps read the tile under your boot as you plant it: concrete, asphalt, hollow hardwood, brushed grass, muffled dirt, each with a little pitch variation. quieter when you crouch, a slow drag when you're prone.",
		"thunder rolls in after every strike, delayed by the distance - half a second to a second and a half - and a soft rain bed rises and falls with how hard it's coming down.",
		"about half the intact cars are armed. come within reach and a short two-tone alarm goes off from the car itself while its lights flash amber for three seconds. once per car, re-armed only when you die and come back. the broken-into ones never alarm - they were stripped long ago.",
		"vehicles are solid. the stepped roof strokes were leaving a checkerboard of transparent holes that the outliner rimmed into dots, and that was the missing-parts look. both rows fill now, and the hidden end wraps closed with a bumper hint and a sliver of light, so no car ends in a flat cutoff.",
		"broken-into cars read as an event instead of noise: a door hanging open, one flat tire, dark side windows with a couple of glints, rust - not a field of shattered glass across the roof.",
	]],
	["v0.2.5", [
		"the barricade line reads as one barrier instead of a sampler. each stretch repeats a single dominant jersey design with the cracked versions as wear, fences drop back to occasional accents, about one piece in ten is knocked visibly askew, some lie flat, and every piece is jittered off the line and spaced in clusters and gaps.",
		"past the line is bare dead district - no woods out there, and the roads dead-end under the wreckage of the breach. rubble, dead snags, litter and the fallen are all there is. every tree, fringe, forest and grove alike, now lives inside the map.",
		"biomes blend: grass creeps onto the concrete wherever the two touch, dirt paths get soft edges, groves have a five-cell minimum and lone trees grow their own small organic pockets with blended rims. no more single green tiles, no more hard seams.",
		"the fallen out past the line are character-sized, drawn through the same lying figure as your own prone sheet - which also got true standing proportions: wider torso, full-size head, thicker limbs, most noticeable on the diagonals.",
	]],
	["v0.2.4", [
		"go prone on z: a full eight-direction crawl, pack on your back, boot soles when you're facing away, the head turned right for each direction, six frames to the cycle. slower than crouch - low, slow and hard to spot - and any crouch input stands you back up out of it.",
		"the door prompt floats pinned above the door itself instead of sitting at the bottom of the screen.",
	]],
	["v0.2.3", [
		"the barricade line: a randomised ring of concrete jerseys and metal fences - intact, cracked, bent, knocked flat, with gaps you can slip through and wreckage where the roads breach it - now marks the real edge of the playable district. the world visibly carries on past it, but crossing starts the sniper warning, and the fire gets faster and more accurate the deeper you go, so the buffer can't be outrun.",
		"the camera never clamps any more. it stays welded to you everywhere - the old shift at the edge is gone, and so is the playable area quietly shrinking on you.",
		"fallen raiders lie past the barricades, sparse and randomised - different jackets, hats, beards, packs and poses - wherever the sniper left them.",
		"a prompt appears when you stand at a door: press f to open, press f to close, showing whatever key you have it bound to.",
		"deploying is dip-free. the world builds in small slices behind the cover, the spawn and environment work afterwards is spread across frames, every texture prewarms, the camera pre-bakes the spawn area and the light shaders compile while you're still looking at the screen. the one frame left is the swap into the game itself.",
		"weather can't jump any more - the storm darkening eases in over about 45 seconds instead of snapping on with the rain.",
		"deep night is much darker, with the flashlight and the lamps turned up to match. lamp glow really reads in the dark now.",
		"vehicles got real end faces - a capped end with a bumper band, head lights and grille or tail lights and a trunk seam, wrapped round the corner - and pickup cargo now sits strictly inside the measured bed, so a box can't overlap the cab.",
		"the flashlight toggle is a dry click now, not a musical blip.",
		"new on the roadmap, your call: tarkov-style loot with a grid inventory, item footprints and searchable containers, plus character doll gear slots. quests and a second map get milestones of their own. machines are cut - every enemy will be a human with a gun - and rarity colour tiers are cut with them.",
	]],
	["v0.2.2", [
		"the blurry, shimmering walk is fixed, and it was worst on the diagonals. the camera was snapping to the screen pixel grid while your sprite rendered at whatever sub-pixel offset it landed on in between, and the engine was rounding transforms on its own terms on top of that.",
		"your true position still moves continuously, so nothing about the speed changed - but the sprite and its shadow now park on the same screen pixel grid as the camera every frame, and the camera is measured off that same point. you are pixel-welded to the screen and the world scrolls on one coherent grid.",
	]],
	["v0.2.1", [
		"the map is four times the area again, and it has a name: transit. every deploy builds a fresh district from a seed.",
		"you can walk to the true edge now. the border hugs the real diamond of the world with the tips chamfered for the camera, and the void outside the tiles can never appear on screen.",
		"the edge is sniper country. a warning comes up centre screen - turn back or you will get sniped - and three seconds later tracer rounds arrive from off-screen. three hits kill you: hurt flash, death fade, respawn at the crossroads. the first damage, health and death in the game.",
		"doors are real. closed by default, sitting flush in the wall plane so no leaf clips through, and f swings them open or shut over four frames with a thunk. they block you while they're closed.",
		"flashlight on e - a cone snapped to the eight facings. deep night is properly dark now, so it matters.",
		"street lamps live and die. there are fewer of them and under half work; the working ones glow and cast a real pool of light at night, each with its own flicker and dropouts. the rest are bent or smashed.",
		"rain is anchored to the world. each drop falls to a real point on the ground and splashes there, the splash stays where it landed instead of riding the camera, nothing falls inside a roofed building, and all of it is the same blue as the puddles.",
		"a full day is twenty minutes, rain spells run two and a half to five minutes with slow ramps, and lightning is a longer double strike that hits harder at night.",
		"dusk fades properly at last. the tint gradient's last stop was never set, so late evening was drifting toward pure white and then jump-cutting to night at the wrap.",
		"the woods came inside: 26 large stands, around 90 small groves, and roughly 240 lone trees breaking through the concrete on their own green pockets. trees are rebuilt so the canopy always overlaps the trunk - tall pines used to float - there's a new leafy oak, and the dead snags fork properly. fallen branches lie in the woods, and cans, bottles and paper collect around the broken-into cars.",
		"vehicles v2: wider bodies, a visible end cap with head or tail lights, roof glass that tells you which way they're pointing, all four lane headings baked in, and broken-into versions with shattered glass, rust, dents and a sprung door. road cars sit in the correct lane, yard cars face their building.",
		"walking is smooth - the camera scrolls in screen pixels now, so at native scale you move exactly one screen pixel per frame on a 240hz display. the smeary, looks-like-lower-fps walk is gone. deploying doesn't dip either: the world builds across frames behind an animated deploying to transit screen while every texture prewarms.",
		"a pile of things that were off: one floor look per building instead of a per-cell patchwork, centre dashes on both road directions that tessellate seamlessly from tile to tile, roof edges closed off clean (the old speckled eave rippled like a mesh hanging off the roof), crate stacks that no longer clip their top box, furniture that can never block an entrance, and about a third less speckle on all the outdoor ground - the forest floor worst of all, it shimmered when you walked back and forth.",
		"the character's left arm had no seam and blended into the torso. both arms read separately on every sheet now - symmetric again.",
	]],
	["v0.2.0", [
		"the map is ten times bigger - a whole district with a road network across it, dirt roads wandering off into the forests, and about a dozen randomised buildings, houses and warehouses in random sizes, styles, damage and door placements, with yards where they fit.",
		"it never visibly ends. the outer band is deep impassable forest and the camera stays well inside it - no void, no floating square of world.",
		"forests of pines and dead trees with their own forest floor, and street lights along the roads.",
		"vehicles that read as vehicles: side-on cars and pickups with real silhouettes, windows, wheel arches and lights, cargo in the pickup beds, parked in yards and abandoned along the roads.",
		"every building has a door leaf beside its doorway - wood on the houses, metal on the warehouses.",
		"day turns to night and back on an eight-minute cycle, and weather arrives with it: random rain spells with visible drop impacts on the ground, the occasional flicker of lightning, and puddles that form while it rains and dry out afterwards.",
		"entering a raid shows a deploying screen while the district builds, instead of dipping the framerate on the scene change.",
		"warehouse floors are smooth grey concrete now - the green screed looked wrong.",
		"house furnishing fixed: the bookshelf and cabinet could silently vanish when both rolled the same wall slot, and industrial barrels were spawning indoors. ambient junk is rarer too, and gathers around buildings instead of sitting everywhere.",
	]],
	["v0.1.14", [
		"a loading yard south of the warehouse: an asphalt pad with faded stall lines, pickup trucks backed into it in random numbers, colours and stalls with boxes in their beds, and stray stock scattered around.",
		"crouch can be hold or toggle - the option sits right next to its keybind.",
		"the warehouse floor is a distinct green sealed screed. the dark asphalt just read as more street.",
		"racks and crate stacks are variant families now, with messy jostled loads randomised box by box - no two look alike and nothing stacks perfectly. the racks are also shorter than the walls, so top boxes stop poking past the cap.",
		"roof corner caps are post-sized and carry the fascia and rim lines straight through the corners.",
		"the gold in the vault backdrop falls down the light shaft instead of rising up it.",
		"menu buttons are exactly centred and stay centred as buttons get added, the tagline is smaller and no longer bobs with the title, and a silver gleam sweeps across the title every few seconds.",
		"the version plan from here: patch bumps for polish and fix batches, and the minor number only moves when a milestone lands - 0.7 guns, 0.8 enemies, 0.9 the raid loop. 1.0 is the complete game.",
	]],
	["v0.1.13", [
		"a keybinds screen in settings: every action rebindable - click a key, press the new one - with a reset to defaults, and it saves. movement, interact, crouch, reload, flashlight and the three weapon slots are all listed; some of them stay inert until later milestones.",
		"crouch on ctrl: a dedicated crouched sprite sheet in all eight directions, a little over half speed, and a slower step cycle.",
		"real interiors. the house has wooden plank floors and furniture - a couch facing the tv, a cabinet, a bookshelf, a table and chairs. the warehouse has a dark screed floor, shelving racks along the back wall and randomised stacked stock. none of it is hand-placed.",
		"broken roof sections with exposed joists over the warehouse's ruined corner.",
		"the house and the warehouse are different sizes now, and both doors sit on a side the camera can see.",
		"all roofs are black, in two subtle shades - the purplish tone is gone.",
		"the menu title is bigger with the tagline baked in and outlined, because it was unreadable over the bright scenes, and the neon scrapyard sign is smaller.",
		"vsync on greys out the fps cap slider and shows your display's refresh instead, and the settings window is a fixed, slightly wider size so it stops resizing whenever a value's text changes.",
	]],
	["v0.1.12", [
		"wall symmetry, settled for good: the flipped-coping experiment is gone and every wall uses the identical cap, so all four corners match. the flipped ones were overlapping their own faces and colliding at the top corner.",
		"wall caps are slimmed to a flush 3 pixel top - the wide cap read as a fat lid on a thin wall. the roof is what overhangs now: new eave pieces carry the roof plane out over the wall tops on the far sides, and every post gets a roof-coloured cap so corners and door jambs read identical underneath it.",
		"buttons restyled once more - near-black translucent fill, a light border and bright text. contrast by brightness instead of hue, so they read over the gold vault, the purple cave and the blue-grey scenes alike. the changelog button, which had gone invisible on the dark backdrops, is a normal themed button again.",
	]],
	["v0.1.11", ["more detail in this changelog",
		"new burgundy buttons that stand out on every backdrop",
		"changelog link dimmed to match the footer"]],
	["v0.1.10", ["changelog viewer (this!)",
		"menu art stays loaded so returning from a raid does not hitch",
		"only the first backdrop pre-warms its particles"]],
	["v0.1.9", ["roofs rebuilt from modular pieces placed by exact formula",
		"one roof tile per floor cell + trim pieces on the eaves",
		"wall caps now tuck under the roof instead of poking past it",
		"corner posts sit flush in the roofline - clean corners everywhere"]],
	["v0.1.8", ["roofs sit flush on the walls (were overhanging)",
		"roof only hides when you are actually inside the walls",
		"buildings are different materials: red brick vs gray masonry",
		"the two roofs are different shades of black",
		"back-view neck fixed and verified with an in-game capture"]],
	["v0.1.7", ["menu buttons: no box around them, slightly see-through",
		"first sounds in the game: soft hover + click blips, made by code",
		"walls always stay visible inside buildings (no see-through)",
		"one doorway per building (a frame post was splitting it in two)",
		"character has hair now instead of the beanie",
		"arms are truly symmetric", "main menu button on the pause screen"]],
	["v0.1.6", ["text crisp for real - found the font bug that blurred all ui",
		"new lowercase-only pixel font, no capitals anywhere",
		"buildings became real thin walls with door frames and posts",
		"three rotating menu backdrops with sparkles, neon and clouds",
		"treasure vault, scrapyard and cliff overlook scenes"]],
	["v0.1.5", ["first main menu with a live background",
		"first pixel font for the ui", "roofs + walk-inside roof reveal",
		"every prop family got real variations: sizes, damage, fallen poses",
		"barrels, crates, cylinders, tires, pallets, dumpsters, rubble, pillars",
		"resolution option in settings", "fps counter moved and restyled"]],
	["v0.1.4", ["pause menu on esc with settings and quit",
		"display mode, fps cap slider, vsync, show fps",
		"settings save and reload on launch",
		"fullscreen fills the whole screen at crisp pixel scale"]],
	["v0.1.3", ["motion updates every frame - smooth on 240hz monitors",
		"camera locked to whole pixels: no more shimmer while walking",
		"fullscreen by default"]],
	["v0.1.2", ["ground is one smooth surface, no more tile grid",
		"buildings rebuilt in brick with windows",
		"props got distinct shapes instead of recolors",
		"6-frame walk cycle with real leg movement"]],
	["v0.1.1", ["fixed the play shortcut not launching"]],
	["v0.1.0", ["the first build: a walkable ruined block",
		"iso world, roads, two buildings, scattered props",
		"8-direction movement and collision",
		"all art generated from a 46-color palette"]],
]


func _ready() -> void:
	_menu_reset_windows()
	Sfx.silence_world()   # no rain wash or engine bed carried in from a raid
	add_to_group("main_menu")
	var camera := Camera2D.new()
	add_child(camera)
	camera.make_current()
	_build_scenes()
	_build_ui()
	_activate(0, true)
	_bag_reset(0)         # the den is on screen, so it is already spent
	Music.play_menu()
	# emerge from black — pairs with the splash's fade-out so the handoff
	# is one continuous dip instead of a hard cut
	var cover := ColorRect.new()
	cover.color = Color("090a14")
	cover.set_anchors_preset(Control.PRESET_FULL_RECT)
	cover.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var cover_layer := CanvasLayer.new()
	cover_layer.layer = 100
	cover_layer.add_child(cover)
	add_child(cover_layer)
	var fade := create_tween()
	fade.tween_property(cover, "color:a", 0.0, 0.5)
	fade.tween_callback(cover_layer.queue_free)
	_prewarm_changelog()   # builds under the fade; first open costs nothing


func show_backdrop(index: int) -> void:  # harness hook for screenshots
	var shown := clampi(index, 0, _scenes.size() - 1)
	_activate(shown, true)
	_rotate_timer = 0.0
	_bag_reset(shown)     # jumping counts as a draw, same as menu entry


func _process(delta: float) -> void:
	_time += delta
	# the district keeps its own time while you stand in the menu, so the
	# clock on the map-select screen is the one you deploy into
	Raid.advance_clock(delta)
	if _ms_clock != null and _map_select.visible:
		var stamp := "%s   -   %s" % [Raid.time_label(),
			"night" if Raid.is_night() else "day"]
		if stamp != _ms_clock_stamp:      # relabel only when it changes
			_ms_clock_stamp = stamp
			_ms_clock.text = stamp
	_tick_rain(delta)
	_tick_arcs(delta)
	_rotate_timer += delta
	if _rotate_timer >= SCENE_SECONDS:
		_rotate_timer = 0.0
		_activate(_bag_next(), false)

	# A SLOW float, and it is no longer the only thing the title does. The bob
	# ran at 1.3 rad/s, which on cast letters this heavy read as bouncing;
	# gleam.gdshader now carries the life, so this only has to breathe.
	_title.position.y = _title_base_y + roundf(sin(_time * 0.6) * 2.0)

	# per-scene life (also during crossfades — anything visible stays alive).
	# ALL SIX are alive as of v0.6.35. A seventh would tick nothing until it
	# is listed here, so this is the place to add it.
	if _scenes[0].visible:
		_tick_den()
	if _scenes[1].visible:
		_tick_drain(delta)
	if _scenes[2].visible:
		_tick_yard(delta)
	if _scenes[3].visible:
		_tick_warden(delta)
	if _scenes[4].visible:
		_tick_underpass(delta)
	if _scenes[5].visible:
		_tick_counter(delta)


func _menu_reset_windows() -> void:
	## belt and braces with main.gd: whichever scene we arrive from, the
	## menu starts with no windows claimed (see the Ui.clear note there) and
	## at full speed. Both calls are idempotent, so this costs nothing when
	## main.gd's _exit_tree already did it — and it holds if some future
	## path reaches the menu WITHOUT passing through that exit (a crash to
	## menu, a new scene, a harness jump). Every scene root defends itself.
	Ui.clear()
	Juice.reset()


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed("ui_cancel"):
		return
	if _keybinds.visible:
		get_viewport().set_input_as_handled()
		_close_keybinds()
	elif _volume.visible:
		get_viewport().set_input_as_handled()
		_close_volume()
	elif _settings.visible:
		get_viewport().set_input_as_handled()
		_close_settings()
	elif _changelog.visible:
		get_viewport().set_input_as_handled()
		_close_changelog()
	elif _map_select.visible:
		get_viewport().set_input_as_handled()
		_close_map_select()


# ------------------------------------------------------------- backdrops ----

func _backdrop(scene_root: Node2D, texture: Texture2D) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.texture = texture
	scene_root.add_child(sprite)
	return sprite


func _build_scenes() -> void:
	# 1: THE DEN — candle breathing, needles dancing, smoke, rig LEDs
	var den := Node2D.new()
	_backdrop(den, TEX_DEN)
	_candle_glow = Sprite2D.new()
	_candle_glow.texture = TEX_DEN_GLOW
	_candle_glow.position = PC + Vector2(150, 344)
	var add_mat := CanvasItemMaterial.new()
	add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_candle_glow.material = add_mat
	den.add_child(_candle_glow)
	for pos in [Vector2(746, 262), Vector2(814, 272)]:
		var needle := Sprite2D.new()
		needle.texture = TEX_DEN_NEEDLES
		needle.hframes = 3
		needle.position = PC + pos
		den.add_child(needle)
		_needles.append(needle)
	for pos in [Vector2(760, 312), Vector2(860, 372)]:
		var led := Sprite2D.new()
		led.texture = TEX_DUST
		led.modulate = Color("73bed3")
		led.position = PC + pos
		den.add_child(led)
		_leds.append(led)
	var smoke := CPUParticles2D.new()
	smoke.texture = TEX_DUST
	smoke.amount = 16      # 5 was a thread; a kettle on a stove makes a plume
	smoke.lifetime = 7.0
	smoke.preprocess = 7.0
	smoke.position = PC + Vector2(334, 372)
	smoke.direction = Vector2(-0.15, -1)
	smoke.spread = 22.0
	smoke.gravity = Vector2(-2, -6)
	smoke.initial_velocity_min = 7.0
	smoke.initial_velocity_max = 16.0
	smoke.color = Color("819796", 0.42)
	smoke.color_ramp = _fade_ramp()
	den.add_child(smoke)
	add_child(den)
	_scenes.append(den)

	# 2: THE DRAIN — the ray breathes, motes sink, drips ring the water
	var drain := Node2D.new()
	_backdrop(drain, TEX_DRAIN)
	_ray = Sprite2D.new()
	_ray.texture = TEX_DRAIN_RAY
	_ray.position = PC + Vector2(615, 287)
	_ray.material = add_mat
	drain.add_child(_ray)
	var motes := CPUParticles2D.new()
	motes.texture = TEX_DUST
	motes.amount = 30      # 13 read as a few specks in a very large shaft
	motes.lifetime = 10.0
	motes.preprocess = 10.0
	motes.position = PC + Vector2(615, 200)
	motes.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	motes.emission_rect_extents = Vector2(20, 150)
	motes.direction = Vector2(0, 1)
	motes.spread = 4.0
	motes.gravity = Vector2(0, 4)
	motes.initial_velocity_min = 3.0
	motes.initial_velocity_max = 8.0
	motes.color = Color("a8b5b2", 0.5)
	motes.color_ramp = _fade_ramp()
	drain.add_child(motes)
	# THE SLUICE ACTUALLY RUNS NOW. The penstock has always been described as
	# leaking a sheet into the channel and the bake draws that sheet in
	# 090a14 — invisible. User: "i dont see any water dripping down from the
	# top". Six scrolling frames, sheet and foam in one object so they can
	# never fall out of step.
	_sluice = Sprite2D.new()
	_sluice.texture = TEX_DRAIN_SLUICE
	_sluice.hframes = 6
	# 463, not 452: the sheet is 98 tall now so its foam lands ON the
	# channel surface (~y 505 at this column) instead of 15px above it
	_sluice.position = PC + Vector2(822, 463)
	drain.add_child(_sluice)
	# OVER THE LIT WATER, not the dark half. The first placement centred this
	# at y 512, which put two thirds of it below the pool's lit band — it
	# measured 967 changed pixels against the bake and the scene still read as
	# a photograph. The water under the shaft runs roughly y 446-510.
	_drain_chop = Sprite2D.new()               # the pool's surface, moving
	_drain_chop.texture = TEX_DRAIN_CHOP
	_drain_chop.hframes = 6
	_drain_chop.position = PC + Vector2(600, 478)
	_drain_chop.material = add_mat
	drain.add_child(_drain_chop)
	_drain_mist = Sprite2D.new()               # drifts on every single frame
	_drain_mist.texture = TEX_DRAIN_MIST
	_drain_mist.material = add_mat
	drain.add_child(_drain_mist)
	_lant = Sprite2D.new()                     # the raider's lantern flame
	_lant.texture = TEX_DRAIN_LANT
	_lant.position = PC + Vector2(250, 456)    # LANT, from the generator
	_lant.material = add_mat
	drain.add_child(_lant)
	# ONE RIPPLE PER DRIP, PAIRED BY INDEX. The old build gave the two ripples
	# their OWN random timers, so ripple #1 fired with nothing above it — the
	# user saw exactly that: "theres just water droplets in water with no
	# water coming down". A ring in this scene is now only ever the result of
	# something landing.
	for i in DRAIN_DRIP_X.size():
		var ripple := Sprite2D.new()
		ripple.texture = TEX_DRAIN_RIPPLE
		ripple.hframes = 3
		ripple.position = PC + Vector2(DRAIN_DRIP_X[i], DRAIN_DRIP_Y[i])
		ripple.visible = false
		drain.add_child(ripple)
		_ripples.append(ripple)
		_ripple_age.append(-1.0)
		var bub := Sprite2D.new()
		bub.texture = TEX_DRAIN_BUBBLE
		bub.hframes = 8              # 0-3 small dome, 4-7 the big one
		bub.position = PC + Vector2(DRAIN_DRIP_X[i], DRAIN_DRIP_Y[i] - 3.0)
		bub.visible = false
		drain.add_child(bub)
		_bubbles.append(bub)
		_bubble_age.append(-1.0)
		var dr := Sprite2D.new()
		dr.texture = TEX_DRAIN_DROP
		dr.hframes = 2               # 0 thin, 1 the fat one off the rim
		dr.frame = 1 if DRAIN_DRIP_BIG[i] else 0
		dr.modulate = Color(1, 1, 1, 0.92)
		dr.visible = false
		drain.add_child(dr)
		_drips.append(dr)
		_drip_t.append(0.15 + i * 0.34)
	add_child(drain)
	_scenes.append(drain)

	# 3: THE YARD — the signal ticks red, two dead-lens LEDs wake on their own
	# offsets, drizzle blows through the halo, and runoff comes off the near
	# boxcar's eave to burst on the ballast. Every anchor below is a landmark
	# named in make_scene_yard's docstring; they are not eyeballed.
	var yard := Node2D.new()
	_backdrop(yard, TEX_YARD)
	_yard_glint = Sprite2D.new()               # sunset in the four-foot puddle
	_yard_glint.texture = TEX_YARD_GLINT
	_yard_glint.position = PC + Vector2(286, 418)
	# NO add_mat here, deliberately — see the note in make_scene_yard. This
	# one is a reflection on a surface, not light in air, and ADD over a blue
	# puddle can only make grey.
	yard.add_child(_yard_glint)
	_yard_halo = Sprite2D.new()                # the signal lens
	_yard_halo.texture = TEX_YARD_HALO
	_yard_halo.position = PC + Vector2(340, 224)
	_yard_halo.material = add_mat
	yard.add_child(_yard_halo)
	# THE +1,+1 IS NOT A FUDGE. TEX_DUST is 3x3, and an ODD-sized sprite
	# centred on P covers [P-1.5, P+1.5], which rasterises its middle texel
	# onto pixel P-1 — measured, not guessed: the far eye at CAB_LED/FAR_LED
	# exactly lit the pixel up-and-left of the baked lens. The anchors below
	# are the docstring's, plus that one-pixel raster correction. Every other
	# overlay in this scene has an EVEN size and needs none.
	for spec in [[Vector2(347, 287), "e8c170", false], [Vector2(306, 258), "cf573c", true]]:
		var led := Sprite2D.new()              # cabinet indicator, far signal
		led.texture = TEX_DUST
		led.modulate = Color(spec[1])
		led.position = PC + (spec[0] as Vector2)
		# THE FAR SIGNAL'S EYE IS ADDITIVE AND THE CABINET'S IS NOT, and that
		# is not an oversight. The cabinet lens sits on grey steel, so a solid
		# warm dot reads. The far eye is baked 752438 against a de9e41 SUNSET —
		# a red dot there is DARKER than its own sky and reads as a speck of
		# dirt. Additive clips it up off the orange instead, which is what a
		# distant lamp against a bright sky actually does.
		if spec[2]:
			led.material = add_mat
		yard.add_child(led)
		_yard_leds.append(led)
	_yard_splash = Sprite2D.new()
	_yard_splash.texture = TEX_YARD_SPLASH
	_yard_splash.hframes = 3
	_yard_splash.position = PC + Vector2(100, 358)
	_yard_splash.visible = false
	yard.add_child(_yard_splash)
	_yard_drip = Sprite2D.new()
	_yard_drip.texture = TEX_RAIN
	_yard_drip.modulate = Color("a8b5b2", 0.75)
	_yard_drip.visible = false
	yard.add_child(_yard_drip)
	# the yard's ground: nothing lands above the middle distance at y 300,
	# and the near four-foot runs off the bottom of the frame
	_add_rain(yard, 2, -30.0, 990.0, 300.0, 540.0, 200)
	# SPARKS OFF THE POLE LINES (user's own example). Both points are wire
	# pixels read out of the bake, not eyeballed.
	# the yard's ground runs from the far shoulder down to the near four-foot
	# THREE BIRDS, on their own staggered clocks, crossing the sunset band —
	# the one bright thing in the frame, so they read as hard silhouettes.
	for i in YARD_WINDOWS.size():
		var w := Sprite2D.new()
		w.texture = TEX_YARD_WIN
		w.position = PC + (YARD_WINDOWS[i] as Vector2)
		yard.add_child(w)
		_yard_wins.append(w)
	# FIVE BIRDS, each living its own life anywhere in the sky. They FADE IN
	# rather than entering from behind anything — user: "it doesnt matter if
	# they spawn in the sky, just make them fade in" — which is both simpler
	# and the only way to guarantee they stay spread, because a shared entry
	# point stacks them into a column the moment a fast one catches a slow one.
	for i in 5:
		var bd := Sprite2D.new()
		bd.texture = TEX_YARD_BIRD
		bd.hframes = 3
		yard.add_child(bd)
		_birds.append(bd)
		_bird_age.append(randf_range(0.0, 9.0))   # already mid-life at boot
		_bird_life.append(randf_range(7.0, 15.0))
		_bird_spd.append(randf_range(26.0, 78.0))
		_bird_x.append(randf_range(150.0, 660.0))
		_bird_y.append(randf_range(206.0, 226.0))
		bd.position = PC + Vector2(_bird_x[i], _bird_y[i])
	# FIVE points, all on wire pixels sampled out of the bake, and they fire
	# every 1.4-4.5s instead of every 3.5-9 — user: "make the trainyards
	# sparks from the poles more noticable, and make more of them".
	for spec in [[Vector2(170, 175), 0.6], [Vector2(200, 198), 1.9],
				 [Vector2(230, 205), 3.1], [Vector2(260, 229), 4.4],
				 [Vector2(182, 183), 5.6]]:
		_add_arc(yard, spec[0] as Vector2, add_mat, spec[1])
	add_child(yard)
	_scenes.append(yard)

	# 4: THE WARDEN — his desk lamp breathes and the road spill breathes with
	# it (that shared clock is what joins the pool to the window it comes out
	# of), the fuse box wakes, a moth works the lamp and guts it when it
	# touches, and he blinks. Anchors are mapped off the bake, see
	# make_scene_warden's docstring.
	var warden := Node2D.new()
	_backdrop(warden, TEX_WARDEN)
	_w_spill = Sprite2D.new()                  # the window's light on wet road
	_w_spill.texture = TEX_WARDEN_SPILL
	_w_spill.position = PC + Vector2(490, 494)   # the warm pixels' own centroid
	_w_spill.material = add_mat
	warden.add_child(_w_spill)
	_w_lamp = Sprite2D.new()
	_w_lamp.texture = TEX_WARDEN_LAMP
	_w_lamp.position = PC + Vector2(632, 312)
	_w_lamp.material = add_mat
	warden.add_child(_w_lamp)
	# NO DUST FIELD IN THE LAMP LIGHT, and that is a decision not an omission.
	# `dust.png` is a PLUS: full-alpha centre, four neighbours at 90, corners
	# empty. Dense and overlapping it reads as smoke (the den) and around a
	# lens it reads as a glow (the LEDs here and in the yard) — but SIX of
	# them drifting alone over the ledger each read as a little four-pointed
	# STAR, which is sparkle, not dust, and the moth already owns that air.
	_w_led = Sprite2D.new()                    # fuse box pilot, dead in the bake
	_w_led.texture = TEX_DUST
	_w_led.modulate = Color("cf573c")
	_w_led.position = PC + Vector2(811, 269)   # the 3x3 raster correction again
	warden.add_child(_w_led)
	_w_moth = Sprite2D.new()
	_w_moth.texture = TEX_WARDEN_MOTH
	_w_moth.hframes = 3
	warden.add_child(_w_moth)
	_w_blink = Sprite2D.new()
	_w_blink.texture = TEX_WARDEN_BLINK
	# 28 wide (EVEN) so texel 0 lands on x 662; 3 tall (ODD) so the middle row
	# lands on P-1 and the sprite has to sit a pixel low to cover rows 253-255.
	_w_blink.position = PC + Vector2(676, 255)
	_w_blink.visible = false
	warden.add_child(_w_blink)
	# the toll road: the verge starts around y 430 and the tarmac runs out
	# of frame at the bottom
	_add_rain(warden, 3, -30.0, 990.0, 430.0, 540.0, 170)
	# the isolator on the shift lamp's conduit — a real fitting, and the only
	# thing in the booth's dead upper-left that could plausibly arc
	_add_arc(warden, Vector2(813, 147), add_mat, 2.7)
	add_child(warden)
	_scenes.append(warden)

	# 5: THE UNDERPASS — one failing sodium tube. Its own bar, the halo it
	# throws on the wall and its pool on the walkway are ONE LAMP and share
	# one stutter value; three ceiling leaks drip into the flood and break
	# the reflections. Anchors: make_scene_underpass's docstring.
	var underpass := Node2D.new()
	_backdrop(underpass, TEX_UNDERPASS)
	# THE REFLECTION IS ONE OF THE LIGHTS. It is a quarter of the frame and it
	# was entirely baked, so the tube could stammer out while the huge bright
	# patch it throws on the flood sat perfectly still. On the same value, a
	# stammer now takes the whole bottom-right of the picture with it.
	for spec in [[TEX_UP_HALO, Vector2(720, 215)],      # wall behind the tube
				 [TEX_UP_WET, Vector2(700, 470)],       # its reflection, flooded
				 [TEX_UP_POOL, Vector2(748, 382)],      # its pool on the walkway
				 [TEX_UP_TUBE, Vector2(702, 152)]]:     # the tube itself
		var light := Sprite2D.new()
		light.texture = spec[0]
		light.position = PC + (spec[1] as Vector2)
		light.material = add_mat
		underpass.add_child(light)
		_up_lights.append(light)
	# THE PENDANT. A conical shade hangs at 307-353 x 193-231 and the bake
	# leaves it stone dead — in the half of the picture where nothing else
	# moves at all. Cold mercury against the sodium's amber, and it fails
	# HARDER and never in step, so the two ends of the underpass argue.
	for spec in [[TEX_UP_PENDPOOL, Vector2(330, 412)],   # on the flood below
				 [TEX_UP_PEND, Vector2(330, 246)]]:      # under the shade
		var pl := Sprite2D.new()
		pl.texture = spec[0]
		pl.position = PC + (spec[1] as Vector2)
		pl.material = add_mat
		underpass.add_child(pl)
		_up_pend.append(pl)
	_up_mist = Sprite2D.new()                  # drifts every single frame
	_up_mist.texture = TEX_UP_MIST
	_up_mist.material = add_mat
	underpass.add_child(_up_mist)
	_up_chop = Sprite2D.new()                  # the surface itself, moving
	_up_chop.texture = TEX_UP_CHOP
	_up_chop.hframes = 6
	_up_chop.position = PC + Vector2(700, 462)
	_up_chop.material = add_mat
	underpass.add_child(_up_chop)
	for i in UP_DRIP_X.size():
		var ring := Sprite2D.new()
		ring.texture = TEX_UP_RING
		ring.hframes = 3
		ring.position = PC + Vector2(UP_DRIP_X[i], UP_WATER)
		ring.visible = false
		underpass.add_child(ring)
		_up_rings.append(ring)
		_up_ring_age.append(-1.0)
		var drip := Sprite2D.new()
		drip.texture = TEX_RAIN
		# PALE, not a tint. `rain_streak` is already a 3c5e8b at 20-76% alpha
		# and modulate MULTIPLIES it — a 577277 here took the drip to (20,42,65),
		# which is DARKER than the 202e37 wall it falls down, so it rendered as
		# nothing. Same trap the yard's drizzle fell into; check a moving light
		# against what is BEHIND it, every time.
		drip.modulate = Color("c7cfcc", 0.9)
		drip.visible = false
		underpass.add_child(drip)
		_up_drips.append(drip)
		# staggered so the three never fall together — a leaking roof is not
		# a metronome, and three drips in step read as one mechanism. The
		# first is almost immediate so the scene is already dripping when it
		# fades in, rather than standing still for most of a second.
		_up_drip_t.append(0.08 + i * 0.63)
	add_child(underpass)
	_scenes.append(underpass)

	# 6: MARA'S COUNTER — THE COLD LIGHT IS THE ONE THAT BREATHES here, and
	# that is the whole pitch: every other lit scene breathes its warm source,
	# and this room's key light is the box under her map. The work lamp holds
	# steady against it. The taped splice arcs and drops an ember into the
	# parts tin, onto a scorch ring the bake already carries.
	var counter := Node2D.new()
	_backdrop(counter, TEX_COUNTER)
	_ctr_box = Sprite2D.new()
	_ctr_box.texture = TEX_CTR_BOX
	_ctr_box.position = PC + Vector2(670, 400)   # the plate's true middle
	_ctr_box.material = add_mat
	counter.add_child(_ctr_box)
	_ctr_lamp = Sprite2D.new()
	_ctr_lamp.texture = TEX_CTR_LAMP
	_ctr_lamp.position = PC + Vector2(806, 404)  # LAMP, from the generator
	_ctr_lamp.material = add_mat
	counter.add_child(_ctr_lamp)
	# NOT `motes` — the drain's emitter above already owns that name, and
	# _build_scenes is ONE scope from top to bottom.
	var ctr_motes := CPUParticles2D.new()        # dust over the warm counter
	ctr_motes.texture = TEX_CTR_DUST             # ROUND, not dust.png's plus
	ctr_motes.amount = 34
	ctr_motes.lifetime = 9.0
	ctr_motes.preprocess = 9.0
	ctr_motes.position = PC + Vector2(700, 330)
	ctr_motes.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	ctr_motes.emission_rect_extents = Vector2(200, 90)
	ctr_motes.direction = Vector2(-0.35, -1)
	ctr_motes.spread = 16.0
	ctr_motes.gravity = Vector2(-1, -2)
	ctr_motes.initial_velocity_min = 2.0
	ctr_motes.initial_velocity_max = 6.0
	ctr_motes.color = Color("e8c170", 0.40)
	ctr_motes.color_ramp = _fade_ramp()
	counter.add_child(ctr_motes)
	_ctr_flare = Sprite2D.new()
	_ctr_flare.texture = TEX_CTR_FLARE
	_ctr_flare.hframes = 3
	_ctr_flare.position = PC + Vector2(838, CTR_TIN_Y)
	_ctr_flare.visible = false
	# NOT additive, unlike every other light in this scene. Added over the
	# tin's baked 602c2c scorch ring, e8c170 clips to a near-white c9c9c1 and
	# reads as an electrical SPARK; drawn normally it stays gold and reads as
	# what it is, a bit of hot metal landing in a tin.
	counter.add_child(_ctr_flare)
	_ctr_ember = Sprite2D.new()
	_ctr_ember.texture = TEX_DUST                # a 3px plus IS right for an
	_ctr_ember.modulate = Color("cf573c")        # ember: a point with a glow
	_ctr_ember.material = add_mat
	_ctr_ember.visible = false
	counter.add_child(_ctr_ember)
	# it measured the least motion of all six. A slow band of warm air over
	# the counter, so this scene also has something moving on every frame
	# rather than only when a timer fires.
	_ctr_haze = Sprite2D.new()
	_ctr_haze.texture = TEX_DRAIN_MIST     # a generic soft lobe, not drain-specific
	_ctr_haze.modulate = Color("e8c170")
	_ctr_haze.material = add_mat
	counter.add_child(_ctr_haze)
	_ctr_rat = Sprite2D.new()
	_ctr_rat.texture = TEX_CTR_RAT
	_ctr_rat.hframes = 4   # 15x9 each
	_ctr_rat.visible = false
	counter.add_child(_ctr_rat)
	_ctr_arc = Sprite2D.new()
	_ctr_arc.texture = TEX_CTR_ARC
	_ctr_arc.position = PC + CTR_SPLICE
	_ctr_arc.material = add_mat
	counter.add_child(_ctr_arc)
	# the taped splice. Its pilot bead is already painted LIVE in the bake, so
	# an arc here is the picture keeping its own promise.
	_add_arc(counter, CTR_SPLICE, add_mat, 3.4)
	add_child(counter)
	_scenes.append(counter)

	for scene in _scenes:
		scene.modulate.a = 0.0
		scene.visible = false


func _tick_den() -> void:
	# a candle is a FLAME. The old curve moved 14% and gutted once every nine
	# seconds, which is a lamp with a loose wire, not a flame.
	var a := 0.78 + 0.20 * sin(_time * 6.7) + 0.11 * sin(_time * 17.3) \
		+ 0.06 * sin(_time * 3.1)
	if fmod(_time, 5.3) < 0.30:                     # the flame gutters
		a *= 0.38
	_candle_glow.modulate.a = clampf(a, 0.0, 1.0)
	for i in _needles.size():
		var wob := sin(_time * (7.0 + i * 1.7) + i * 2.6) + sin(_time * 3.1 + i)
		_needles[i].frame = clampi(roundi(wob * 0.8 + 1.0), 0, 2)
	for i in _leds.size():
		_leds[i].visible = fmod(_time + i * 1.3, 3.7 + i) < 2.8


func _tick_drain(delta: float) -> void:
	_ray.modulate.a = 0.86 + 0.12 * sin(_time * 0.8)
	# the sluice and the pool run every frame — this scene is never still now
	_drain_anim += delta
	_sluice.frame = int(_drain_anim / 0.075) % 6
	_drain_chop.frame = int(_drain_anim / 0.10) % 6
	_drain_chop.modulate.a = 0.85 + 0.12 * sin(_time * 1.1)
	_drain_mist.position = PC + Vector2(
		470.0 + sin(_time * 0.17) * 210.0,
		486.0 + sin(_time * 0.29) * 7.0)
	_drain_mist.modulate.a = 0.6 + 0.2 * sin(_time * 0.53)
	# the lantern is a FLAME: three periods that do not divide, plus the odd
	# gutter when the draught off the channel catches it
	var fl := 0.74 + 0.13 * sin(_time * 9.3) + 0.08 * sin(_time * 21.7) \
		+ 0.05 * sin(_time * 2.9)
	if fmod(_time, 6.7) < 0.22:
		fl *= 0.55
	_lant.modulate.a = clampf(fl, 0.0, 1.0)
	# four leaks, each owning the ripple at its own index
	for i in _drips.size():
		if _ripple_age[i] >= 0.0:
			_ripple_age[i] += delta
			var rf := int(_ripple_age[i] / 0.3)
			if rf > 2:
				_ripples[i].visible = false
				_ripple_age[i] = -1.0
			else:
				_ripples[i].frame = rf
		var dr := _drips[i]
		_drip_t[i] -= delta
		if _bubble_age[i] >= 0.0:
			_bubble_age[i] += delta
			var bf := int(_bubble_age[i] / 0.13)
			if bf > 3:
				_bubbles[i].visible = false
				_bubble_age[i] = -1.0
			else:
				_bubbles[i].frame = bf + (4 if DRAIN_DRIP_BIG[i] else 0)
		if _drip_t[i] <= 0.0 and not dr.visible:
			_drip_t[i] = randf_range(0.9, 2.6) \
				if not DRAIN_DRIP_BIG[i] else randf_range(3.0, 6.5)
			dr.visible = true
			dr.position = PC + Vector2(DRAIN_DRIP_X[i], DRAIN_DRIP_TOP[i])
		if dr.visible:
			# 470, not the old 900: at 900 px/s a drip crossed the whole frame
			# in under half a second and you could watch this scene for a
			# minute without ever catching one in the air
			# the fat one is heavier and reads slower
			dr.position.y += (380.0 if DRAIN_DRIP_BIG[i] else 470.0) * delta
			if dr.position.y >= PC.y + DRAIN_DRIP_Y[i] - 2.0:
				dr.visible = false
				_ripples[i].visible = true
				_ripples[i].frame = 0
				_ripple_age[i] = 0.0
				_bubbles[i].visible = true          # and it blows a bubble
				_bubbles[i].frame = 4 if DRAIN_DRIP_BIG[i] else 0
				_bubble_age[i] = 0.0


func _tick_yard(delta: float) -> void:
	# THE SIGNAL TICKS. A railway lamp does not breathe like a candle — it
	# comes up, holds, and drops, on a beat you can count. 3.4 s round: up
	# 0.35, hold 1.15, down 0.5, dark 1.4.
	var t := fmod(_time, 3.4)
	var lit := 0.0
	if t < 0.35:
		lit = t / 0.35
	elif t < 1.5:
		lit = 1.0 - 0.06 * sin(_time * 21.0)     # a little ballast buzz
	elif t < 2.0:
		lit = 1.0 - (t - 1.5) / 0.5
	_yard_halo.modulate.a = clampf(lit, 0.0, 1.0)
	# the puddle answers the sky, not the signal, so it shimmers on its own
	# slow beat — two periods that do not divide, so it never pulses.
	_yard_glint.modulate.a = 0.80 + 0.14 * sin(_time * 0.6) + 0.06 * sin(_time * 1.9)
	# the cabinet indicator ticks; the far signal HOLDS ITS ASPECT and only
	# drops out for half a second now and then, because a signal that winks
	# on for a moment reads as a firefly and this one is the depth cue. No
	# two of these three periods divide into each other.
	_yard_leds[0].visible = fmod(_time, 2.6) < 1.5
	_yard_leds[1].visible = fmod(_time + 3.0, 6.7) >= 0.5
	# the far windows. Nine periods that share no common factor, so the row
	# never pulses together — some hold, some blink, one is nearly dead.
	for i in _yard_wins.size():
		var per := 3.1 + i * 1.37
		var on := fmod(_time + i * 2.3, per) < per * (0.34 + 0.06 * i)
		if i == 4:                              # one bad connection
			on = on and fmod(_time * 7.3, 1.0) > 0.35
		_yard_wins[i].visible = on
	# THE BIRDS. One state, no gates: age, drift left, fade in and out, respawn
	# somewhere else. Every extra piece of state between "should be on screen"
	# and "is on screen" is another place for a sprite to silently not draw,
	# and an earlier two-state version did exactly that for a long time.
	#
	# They fly at painting y 204-228, on the 752438 maroon band and ABOVE the
	# menu buttons — at y 234 they flew at screen row 464, inside the "play"
	# button, and spent most of every crossing behind the menu.
	for i in _birds.size():
		var bd := _birds[i]
		_bird_age[i] += delta
		# THE TRUE POSITION STAYS CONTINUOUS AND ONLY THE DRAWN ONE ROUNDS.
		# Writing roundf(position.x - spd * delta) back into position was a
		# real bug and a straight violation of rule 1: at 240 fps and 26-78
		# px/s a bird moves 0.11-0.33 px per frame, so the round snapped it
		# back to where it started and they hung in the sky, motionless
		# ("the birds arent moving, they are in the same spot the whole time").
		_bird_x[i] -= _bird_spd[i] * delta
		bd.position = PC + Vector2(roundf(_bird_x[i]),
			roundf(_bird_y[i] + sin(_time * (1.3 + i * 0.29) + i * 2.1) * 2.5))
		bd.frame = clampi(int(fmod(_time * (7.0 + i * 1.3), 3.0)), 0, 2)
		var life: float = _bird_life[i]
		var age: float = _bird_age[i]
		# fade in over 1.1 s, out over the last 1.1 s, so nothing ever pops
		bd.modulate.a = clampf(minf(age / 1.1, (life - age) / 1.1), 0.0, 1.0)
		if age >= life or _bird_x[i] < 110.0:
			_bird_age[i] = 0.0
			_bird_life[i] = randf_range(7.0, 15.0)
			_bird_spd[i] = randf_range(26.0, 78.0)
			_bird_x[i] = randf_range(170.0, 690.0)
			_bird_y[i] = randf_range(206.0, 226.0)
	# runoff off the near boxcar's eave (x 100), bursting on the ballast
	if _yard_splash_age >= 0.0:
		_yard_splash_age += delta
		var f := int(_yard_splash_age / 0.11)
		if f > 2:
			_yard_splash.visible = false
			_yard_splash_age = -1.0
		else:
			_yard_splash.frame = f
	_yard_drip_t -= delta
	if _yard_drip_t <= 0.0 and not _yard_drip.visible:
		_yard_drip_t = randf_range(2.2, 5.5)
		_yard_drip.visible = true
		_yard_drip.position = PC + Vector2(100, 143)
	if _yard_drip.visible:
		_yard_drip.position.y += 620.0 * delta
		if _yard_drip.position.y >= PC.y + 356.0:
			_yard_drip.visible = false
			_yard_splash.visible = true
			_yard_splash.frame = 0
			_yard_splash_age = 0.0


func _tick_warden(delta: float) -> void:
	# THE LAMP AND THE ROAD SPILL SHARE ONE VALUE. That is the whole point of
	# them: the review note on this painting was that nothing joined the pool
	# on the tarmac to the window it comes out of, and two lights breathing on
	# one clock say it in motion.
	if _w_gutter > 0.0:
		_w_gutter -= delta
	var burn := 0.80 + 0.09 * sin(_time * 1.7) + 0.04 * sin(_time * 4.3)
	if _w_gutter > 0.0:
		burn *= 0.55                            # the moth is on the shade
	_w_lamp.modulate.a = clampf(burn, 0.0, 1.0)
	_w_spill.modulate.a = clampf(burn * 0.9, 0.0, 1.0)
	# the fuse box pilot — slower than anything else in the frame
	_w_led.visible = fmod(_time + 1.2, 4.9) < 2.2
	# the moth works the shade. Its position is ROUNDED: a pixel-art sprite
	# on a fractional position crawls between two rasterisations.
	_w_moth_a += delta * 2.3
	_w_flap += delta * 17.0
	_w_moth.frame = int(_w_flap) % 3
	_w_moth.position = PC + Vector2(
		roundf(626.0 + cos(_w_moth_a) * 22.0),
		roundf(276.0 + sin(_w_moth_a) * 13.0 + sin(_time * 5.1) * 1.5))
	_w_gutter_t -= delta
	if _w_gutter_t <= 0.0 and sin(_w_moth_a) > 0.94:
		_w_gutter = 0.16                        # it touched: the lamp guts
		_w_gutter_t = randf_range(5.0, 11.0)
	# HE BLINKS. Two closes in quick succession now and then, which is what a
	# tired man does; one lone blink on a fixed period reads as a machine.
	# The +2.0 keeps his eyes OPEN for the first couple of seconds after the
	# menu opens (and in every harness shot, which lands ~0.17 s in) — landing
	# on the scene mid-blink reads as a man with his eyes shut, not a blink.
	var b := fmod(_time + 2.0, 6.3)
	_w_blink.visible = b < 0.11 or (b > 0.27 and b < 0.36)


func _tick_underpass(delta: float) -> void:
	# THE TUBE IS FAILING. A sodium tube does not fade — it drops out and
	# strikes again, so this is a steady burn with a short stammer punched
	# through it every 7.4 s, not a sine. The bar, the wall halo and the pool
	# all take the SAME value: they are one lamp, and a lamp whose reflection
	# keeps burning while the lamp itself is out is two lamps.
	var lit := 0.88 + 0.05 * sin(_time * 2.1) + 0.03 * sin(_time * 5.3)
	var cyc := fmod(_time, 7.4)
	if cyc < 0.44 and fmod(cyc, 0.13) < 0.075:
		lit *= 0.16                            # the stammer
	for light in _up_lights:
		light.modulate.a = clampf(lit, 0.0, 1.0)
	# the surface breaks up continuously — six frames of dashes in the water's
	# own language, ~9 a second. This is the one thing in the scene that is
	# ALWAYS moving; everything else waits for its own timer.
	_up_chop_t += delta
	_up_chop.frame = int(_up_chop_t / 0.11) % 6
	_up_chop.modulate.a = clampf(lit * 0.95, 0.0, 1.0)
	# THE PENDANT IS DYING, and it is on nothing's clock but its own: a fast
	# irregular flutter built from three periods that do not divide, with a
	# hard cut-out every 5.1 s. Never in step with the sodium tube — two
	# failing lights blinking together read as one switch being thrown.
	var pf := 0.62 + 0.24 * sin(_time * 11.3) + 0.14 * sin(_time * 27.1) \
		+ 0.10 * sin(_time * 3.7)
	if fmod(_time, 5.1) < 0.30:
		pf *= 0.08
	elif fmod(_time, 1.7) < 0.06:
		pf *= 0.35
	for pl in _up_pend:
		pl.modulate.a = clampf(pf, 0.0, 1.0)
	# the mist never stops moving — it is the scene's baseline life, so no
	# frame of this backdrop is ever completely still
	_up_mist.position = PC + Vector2(
		420.0 + sin(_time * 0.13) * 250.0,
		470.0 + sin(_time * 0.31) * 9.0)
	_up_mist.modulate.a = 0.55 + 0.18 * sin(_time * 0.47)
	# three leaks in the deck, each on its own clock
	for i in _up_drips.size():
		var drip := _up_drips[i]
		if _up_ring_age[i] >= 0.0:
			_up_ring_age[i] += delta
			var f := int(_up_ring_age[i] / 0.15)
			if f > 2:
				_up_rings[i].visible = false
				_up_ring_age[i] = -1.0
			else:
				_up_rings[i].frame = f
		_up_drip_t[i] -= delta
		if _up_drip_t[i] <= 0.0 and not drip.visible:
			_up_drip_t[i] = randf_range(1.6, 4.4)
			drip.visible = true
			drip.position = PC + Vector2(UP_DRIP_X[i], UP_DRIP_TOP)
		if drip.visible:
			drip.position.y += 780.0 * delta
			if drip.position.y >= PC.y + UP_WATER - 2.0:
				drip.visible = false
				_up_rings[i].visible = true
				_up_rings[i].frame = 0
				_up_ring_age[i] = 0.0


func _tick_counter(delta: float) -> void:
	# THE COLD ONE MOVES. Every other lit scene in this menu breathes its warm
	# source; here the key light is the box under her map, so the plate is
	# what wavers and the work lamp holds steady against it.
	# a drafting box is a fluorescent tube under glass, and a tired one
	# flutters. Three periods that do not divide, plus an occasional dip.
	var bx := 0.74 + 0.14 * sin(_time * 0.9) + 0.09 * sin(_time * 8.3) \
		+ 0.05 * sin(_time * 19.7)
	if fmod(_time, 4.3) < 0.09:
		bx *= 0.42
	_ctr_box.modulate.a = clampf(bx, 0.0, 1.0)
	_ctr_lamp.modulate.a = 0.88 + 0.06 * sin(_time * 1.3) + 0.04 * sin(_time * 6.1)
	_ctr_haze.position = PC + Vector2(
		700.0 + sin(_time * 0.19) * 190.0,
		352.0 + sin(_time * 0.33) * 14.0)
	_ctr_haze.modulate.a = 0.34 + 0.16 * sin(_time * 0.61)
	# the splice is LIVE and it knows it: the bead swells just before it lets
	# an ember go, so the drip has a visible cause instead of arriving out of
	# a dark ceiling.
	var due := clampf(1.0 - _ctr_ember_t / 1.2, 0.0, 1.0)
	_ctr_arc.modulate.a = clampf(0.34 + 0.10 * sin(_time * 3.1) + due * 0.62,
		0.0, 1.0)
	if _ctr_flare_age >= 0.0:
		_ctr_flare_age += delta
		var f := int(_ctr_flare_age / 0.13)
		if f > 2:
			_ctr_flare.visible = false
			_ctr_flare_age = -1.0
		else:
			_ctr_flare.frame = f
	# THE RAT crosses the counter's empty left third. It is the only body in
	# this picture besides mara, and it is the reason the scene stopped
	# reading as a photograph of a room.
	_ctr_rat_t -= delta
	if not _ctr_rat.visible:
		if _ctr_rat_t <= 0.0:
			_ctr_rat.visible = true
			# 66, not 24: the viewport shows painting x 60-900, so a rat that
			# starts at 24 starts OFF SCREEN — and since it never moved (see
			# below) it stayed there. It now walks in from just inside the
			# left edge.
			_ctr_rat_x = 40.0
			_ctr_rat.position = PC + Vector2(_ctr_rat_x, 402.0)
	else:
		# THE TRUE POSITION IS KEPT SEPARATELY. Writing roundf(x + 34*delta)
		# back into position rounded the step away entirely: at 240 fps that
		# is 0.14 px a frame, so the rat never moved from where it spawned and
		# the user simply never saw one. Identical bug to the birds, same day.
		_ctr_rat_x += 34.0 * delta
		_ctr_rat.position = Vector2(PC.x + roundf(_ctr_rat_x), PC.y + 402.0)
		_ctr_rat.frame = clampi(int(fmod(_time * 9.0, 4.0)), 0, 3)
		# FADE IN AND OUT over the first and last 26px of the run. It used to
		# blink out of existence in the middle of an empty counter — user:
		# "the rat just dissapeared". Same fix as the birds.
		var run := _ctr_rat_x - 40.0
		_ctr_rat.modulate.a = clampf(minf(run / 26.0, (368.0 - _ctr_rat_x) / 26.0),
			0.0, 1.0)
		if _ctr_rat_x > 368.0:
			_ctr_rat.visible = false
			_ctr_rat_t = randf_range(4.0, 10.0)
	_ctr_ember_t -= delta
	if _ctr_ember_t <= 0.0 and not _ctr_ember.visible:
		_ctr_ember_t = randf_range(6.0, 13.0)
		_ctr_ember.visible = true
		_ctr_ember.position = PC + CTR_SPLICE
	if _ctr_ember.visible:
		# slower than a drip of water, and it dims as it falls — an ember is
		# dying on the way down, not falling to a schedule
		_ctr_ember.position.y += 210.0 * delta
		var fall := (_ctr_ember.position.y - PC.y - CTR_SPLICE.y) / (CTR_TIN_Y - CTR_SPLICE.y)
		_ctr_ember.modulate.a = clampf(1.0 - fall * 0.55, 0.0, 1.0)
		if _ctr_ember.position.y >= PC.y + CTR_TIN_Y - 2.0:
			_ctr_ember.visible = false
			_ctr_ember.modulate.a = 1.0
			_ctr_flare.visible = true
			_ctr_flare.frame = 0
			_ctr_flare_age = 0.0


func _add_rain(parent: Node2D, scene_i: int, x0: float, x1: float,
		gy0: float, gy1: float, count: int) -> void:
	## RAIN THAT LANDS. User: "i meant like the actual raindrops coming down on
	## the screen should physically hit something on the screen".
	##
	## This is `environment_system.gd`'s model, not a particle system: every
	## drop carries its own GROUND ROW, falls to it, dies there and leaves a
	## splash AT THAT SPOT — the raid has worked this way all along and the
	## menu was the odd one out. A CPUParticles2D cannot do it, because a
	## particle has no idea where the floor is; the splashes it fires are a
	## second unrelated system, which is exactly what the user spotted.
	##
	## The ground row is ROLLED PER DROP between gy0 and gy1 rather than
	## derived from x. In this projection a column is not one depth — a drop
	## at any x can land anywhere from the middle distance to the near kerb —
	## so a scatter is not an approximation here, it is the correct model.
	var f := {
		"scene": scene_i, "x0": x0, "x1": x1, "gy0": gy0, "gy1": gy1,
		"drop": [], "splash": [], "pos": [], "gnd": [], "spd": [], "age": [],
	}
	for i in count:
		var d := Sprite2D.new()
		d.texture = TEX_RAIN
		# 0.85, not 0.62: rain_streak is already a 3c5e8b at 20-76% of its own
		# alpha, and over dark ballast the first cut measured but did not read
		d.modulate = Color(1, 1, 1, 0.85)
		parent.add_child(d)
		(f["drop"] as Array).append(d)
		var s := Sprite2D.new()
		s.texture = TEX_RAINSPLASH
		s.hframes = 4
		s.modulate = Color(1, 1, 1, 0.9)
		s.visible = false
		parent.add_child(s)
		(f["splash"] as Array).append(s)
		# spread down the whole fall on the first frame, so it is already
		# raining when the backdrop fades in rather than starting empty
		(f["pos"] as Array).append(Vector2(randf_range(x0, x1),
			randf_range(-60.0, gy1)))
		(f["gnd"] as Array).append(randf_range(gy0, gy1))
		(f["spd"] as Array).append(randf_range(150.0, 205.0))
		(f["age"] as Array).append(-1.0)
	_rain.append(f)


func _tick_rain(delta: float) -> void:
	for f in _rain:
		if not _scenes[f["scene"]].visible:
			continue
		var drops: Array = f["drop"]
		var splashes: Array = f["splash"]
		var pos: Array = f["pos"]
		var gnd: Array = f["gnd"]
		var spd: Array = f["spd"]
		var age: Array = f["age"]
		for i in drops.size():
			var p: Vector2 = pos[i]
			p.y += (spd[i] as float) * delta
			p.x += 13.0 * delta                     # the same lean as the wires
			if p.y >= (gnd[i] as float):
				# IT LANDED. The splash goes exactly where it stopped and does
				# not move again; the drop starts over at the top.
				var s := splashes[i] as Sprite2D
				s.position = PC + Vector2(roundf(p.x), roundf(gnd[i]))
				s.visible = true
				s.frame = 0
				age[i] = 0.0
				p = Vector2(randf_range(f["x0"], f["x1"]),
					randf_range(-70.0, -12.0))
				gnd[i] = randf_range(f["gy0"], f["gy1"])
				spd[i] = randf_range(150.0, 205.0)
			pos[i] = p
			# whole pixels: a pixel-art sprite on a fractional position crawls
			(drops[i] as Sprite2D).position = PC + Vector2(roundf(p.x),
				roundf(p.y))
			if (age[i] as float) >= 0.0:
				age[i] = (age[i] as float) + delta
				var fr := int((age[i] as float) / 0.055)
				if fr > 3:
					(splashes[i] as Sprite2D).visible = false
					age[i] = -1.0
				else:
					(splashes[i] as Sprite2D).frame = fr


func _add_arc(parent: Node2D, at: Vector2, add_mat: CanvasItemMaterial,
		first: float) -> void:
	var s := Sprite2D.new()
	s.texture = TEX_SPARK
	s.hframes = 5
	s.position = PC + at
	s.material = add_mat        # an arc blows out against a night sky
	s.visible = false
	parent.add_child(s)
	_arcs.append([s, first, 0.0])


func _tick_arcs(delta: float) -> void:
	## One strike is 5 frames at 0.06 s — a twelfth of a second, which is what
	## a short actually looks like. The gap between strikes is long and random
	## so it never reads as a blinking light.
	for a in _arcs:
		var s := a[0] as Sprite2D
		var t: float = a[1] - delta
		if s.visible:
			var age: float = a[2] + delta
			a[2] = age
			var f := int(age / 0.075)
			if f > 4:
				s.visible = false
				t = randf_range(1.4, 4.5)
			else:
				s.frame = f
		elif t <= 0.0:
			s.visible = true
			s.frame = 0
			a.resize(3)
			a[2] = 0.0
			t = 0.0
		a[1] = t


func _fade_ramp() -> Gradient:
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0))
	ramp.add_point(0.2, Color(1, 1, 1, 1))
	ramp.add_point(0.8, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	return ramp


# ------------------------------------------------------- rotation order ----
#
# A SHUFFLE BAG, not a cycle. The bag holds every scene index once; each
# rotation pops one off the back, and the bag is only refilled once it is
# empty. So within any round every backdrop is shown exactly once and a
# backdrop cannot come back until all the others have had their turn.
#
# The one hole a plain bag leaves is the SEAM: the last draw of one bag and
# the first draw of the next are independent, so the same backdrop can land
# twice in a row across the join. _bag_next closes that.
#
# Unlike the world builder this is DELIBERATELY UNSEEDED — the map must be
# bit-identical every deploy, the menu should differ every launch. Godot's
# global rng is randomized at startup, which is what randi_range draws from.
# Array.shuffle() stays banned project-wide, hence the hand-rolled
# Fisher-Yates below.

func _bag_shuffle() -> void:
	for i in range(_bag.size() - 1, 0, -1):
		var j := randi_range(0, i)
		var tmp := _bag[i]
		_bag[i] = _bag[j]
		_bag[j] = tmp


func _bag_reset(shown: int) -> void:
	## Start a fresh round with `shown` already spent — the backdrop standing
	## on screen when the menu opens (or when the harness jumps to one) counts
	## as drawn, so it is left out of this bag entirely instead of being
	## eligible to come straight back round.
	_bag.clear()
	for i in _scenes.size():
		if i != shown:
			_bag.append(i)
	_bag_shuffle()


func _bag_next() -> int:
	if _bag.is_empty():
		for i in _scenes.size():
			_bag.append(i)
		_bag_shuffle()
		# we draw from the BACK, so the last element is the next backdrop up.
		# If the refill put the scene that is already on screen there, swap it
		# with any other slot: that is the bag seam, and it is the only way
		# this rotation could ever show the same painting twice running.
		var last := _bag.size() - 1
		if last > 0 and _bag[last] == _scene_index:
			var j := randi_range(0, last - 1)
			_bag[last] = _bag[j]
			_bag[j] = _scene_index
	return _bag.pop_back()


func _activate(index: int, instant: bool) -> void:
	var prev := _scenes[_scene_index]
	var next := _scenes[index]
	_scene_index = index
	next.visible = true
	if _fade_tween != null:
		_fade_tween.kill()
	if instant:
		next.modulate.a = 1.0
		for scene in _scenes:
			if scene != next:
				scene.visible = false
				scene.modulate.a = 0.0
		return
	_fade_tween = create_tween().set_parallel(true)
	_fade_tween.tween_property(next, "modulate:a", 1.0, FADE_SECONDS)
	if prev != next:
		_fade_tween.tween_property(prev, "modulate:a", 0.0, FADE_SECONDS)
		_fade_tween.chain().tween_callback(func() -> void: prev.visible = false)


# ------------------------------------------------------------------- ui ------

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UITheme.get_theme()
	layer.add_child(root)

	var vignette := TextureRect.new()
	vignette.texture = TEX_VIGNETTE
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(vignette)

	_title = TextureRect.new()
	_title.texture = TEX_TITLE
	var tw := float(_title.texture.get_width())
	_title.anchor_left = 0.5
	_title.anchor_right = 0.5
	_title.offset_left = -tw / 2.0
	_title.offset_right = tw / 2.0
	_title.offset_top = 52
	_title.offset_bottom = 52 + _title.texture.get_height()
	_title.stretch_mode = TextureRect.STRETCH_KEEP
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_title_base_y = _title.offset_top
	# the gleam rides the wordmark itself. It used to be a second TextureRect
	# holding a flat silver copy, shown through a 34 px clipping Control that
	# slid across — a hard-edged vertical bar, and dark for 5.1 of every 6
	# seconds. The shader does it diagonally, softly, and never goes idle.
	var gleam := ShaderMaterial.new()
	gleam.shader = SHADER_GLEAM
	_title.material = gleam
	root.add_child(_title)

	# tagline: its own small static image (not animated with the title)
	var tagline := TextureRect.new()
	tagline.texture = TEX_TAGLINE
	var tag_w := float(tagline.texture.get_width())
	tagline.anchor_left = 0.5
	tagline.anchor_right = 0.5
	tagline.offset_left = -tag_w / 2.0
	tagline.offset_right = tag_w / 2.0
	tagline.offset_top = 52 + _title.texture.get_height() + 4
	tagline.offset_bottom = tagline.offset_top + tagline.texture.get_height()
	tagline.stretch_mode = TextureRect.STRETCH_KEEP
	tagline.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(tagline)

	# dead-center, growing both ways: stays perfectly centered no matter how
	# many buttons this list gains later
	_buttons = VBoxContainer.new()
	_buttons.anchor_left = 0.5
	_buttons.anchor_right = 0.5
	_buttons.anchor_top = 0.5
	_buttons.anchor_bottom = 0.5
	_buttons.offset_left = -85
	_buttons.offset_right = 85
	_buttons.grow_vertical = Control.GROW_DIRECTION_BOTH
	_buttons.add_theme_constant_override("separation", 8)
	_menu_button(_buttons, "play", _open_map_select)
	_menu_button(_buttons, "settings", _open_settings)
	_menu_button(_buttons, "quit", func() -> void: get_tree().quit())
	root.add_child(_buttons)

	_map_select = _build_map_select()
	var ms_center := CenterContainer.new()
	ms_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	ms_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ms_center.add_child(_map_select)
	root.add_child(ms_center)

	_settings = SettingsPanel.new()
	_settings.visible = false
	_settings.closed.connect(_close_settings)
	_settings.keybinds_requested.connect(_open_keybinds)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	center.add_child(_settings)
	root.add_child(center)

	_keybinds = KeybindsPanel.new()
	_keybinds.visible = false
	_keybinds.closed.connect(_close_keybinds)
	var kb_center := CenterContainer.new()
	kb_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	kb_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	kb_center.add_child(_keybinds)
	root.add_child(kb_center)

	_settings.volume_requested.connect(_open_volume)
	_volume = VolumePanel.new()
	_volume.visible = false
	_volume.closed.connect(_close_volume)
	var vol_center := CenterContainer.new()
	vol_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	vol_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vol_center.add_child(_volume)
	root.add_child(vol_center)

	# same look as every other button (a flat/dim version was invisible on
	# the darker backdrops)
	_changelog_btn = Button.new()
	var changelog_btn := _changelog_btn
	changelog_btn.text = "changelog"
	changelog_btn.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	changelog_btn.offset_left = -96
	changelog_btn.offset_top = -44
	changelog_btn.offset_right = -6
	changelog_btn.offset_bottom = -22
	changelog_btn.pressed.connect(_open_changelog)
	root.add_child(changelog_btn)

	# single source of truth: the corner label always shows the newest
	# changelog entry's version, so the two can never drift apart again
	var version := Label.new()
	version.text = "pre-alpha %s" % str(CHANGELOG_ENTRIES[0][0])
	version.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	version.offset_left = -130
	version.offset_top = -16
	version.offset_right = -6
	version.offset_bottom = -4
	version.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	version.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	root.add_child(version)

	_changelog = _build_changelog_panel()
	var changelog_center := CenterContainer.new()
	changelog_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	changelog_center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	changelog_center.add_child(_changelog)
	root.add_child(changelog_center)


func _build_changelog_panel() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.visible = false
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	var title := Label.new()
	title.text = "changelog"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	box.add_child(title)

	# A MUCH bigger window so there is far less scrolling (user). The text
	# itself stays at 9: the font is a BITMAP font drawn at that size, and
	# asking for 8 does not re-cut the glyphs, it resamples them — which is
	# the blurry-text failure this project has hit before. More rows on
	# screen and tighter leading buys the same thing without the blur.
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(548, 330)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_changelog_list = VBoxContainer.new()
	_changelog_list.add_theme_constant_override("separation", 1)
	_changelog_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	# rows are built LAZILY on first open — a few hundred labels made the
	# menu heavy to build and heavy to tear down on deploy (frame spike)
	scroll.add_child(_changelog_list)
	box.add_child(scroll)

	var back := Button.new()
	back.text = "< back"
	back.pressed.connect(_close_changelog)
	box.add_child(back)
	panel.add_child(box)
	return panel


func _add_changelog_entry(entry: Array) -> void:
	var version_label := Label.new()
	version_label.text = str(entry[0])
	version_label.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
	_changelog_list.add_child(version_label)
	for line in (entry[1] as Array):
		var item := Label.new()
		item.text = "- " + str(line)
		item.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		item.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		item.add_theme_color_override("font_color", UITheme.TEXT_DIM)
		_changelog_list.add_child(item)
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 4)
	_changelog_list.add_child(gap)


func _prewarm_changelog() -> void:
	## Every shipped version lives in this panel — that is ~300 Labels, and
	## building plus text-shaping them ALL in the frame the user first
	## clicked "changelog" is the dip they reported. Build them during the
	## menu's own boot instead, a slice per frame on the same kind of time
	## budget the world builder uses, then take one invisible layout pass so
	## the first open has nothing left to pay for.
	await get_tree().process_frame
	var deadline := Time.get_ticks_usec() + 1200
	for entry in CHANGELOG_ENTRIES:
		if not is_inside_tree():
			return                       # menu left while warming
		_add_changelog_entry(entry)
		if Time.get_ticks_usec() >= deadline:
			await get_tree().process_frame
			deadline = Time.get_ticks_usec() + 1200
	_changelog.modulate.a = 0.0
	_changelog.visible = true
	await get_tree().process_frame       # the container sorts its children
	await get_tree().process_frame       # ...and everything shapes and draws
	if not is_inside_tree():
		return
	_changelog.modulate.a = 1.0
	if not _changelog_open:              # the user beat us to it: leave it up
		_changelog.visible = false


func _open_changelog() -> void:
	if _changelog_list.get_child_count() == 0:
		# opened before the prewarm got there (or it never ran)
		for entry in CHANGELOG_ENTRIES:
			_add_changelog_entry(entry)
	_changelog_open = true
	_changelog.modulate.a = 1.0
	_buttons.visible = false
	_changelog.visible = true


func _close_changelog() -> void:
	_changelog_open = false
	_changelog.visible = false
	_buttons.visible = true


func _build_map_select() -> PanelContainer:
	# PLAY opens this: the cordon's maps. Transit is open — pick it, read
	# it, deploy. The other corridors sit blacked out under question marks
	# until their milestones unseal them.
	var panel := PanelContainer.new()
	panel.visible = false
	panel.custom_minimum_size = Vector2(500, 272)
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 8)
	margin.add_child(rows)
	var title := Label.new()
	title.text = "the cordon - pick your raid"
	title.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
	rows.add_child(title)
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 16)
	rows.add_child(columns)

	var tiles := GridContainer.new()
	tiles.columns = 2
	tiles.add_theme_constant_override("h_separation", 10)
	tiles.add_theme_constant_override("v_separation", 10)
	columns.add_child(tiles)
	_ms_transit_frame = PanelContainer.new()
	var transit_btn := Button.new()
	transit_btn.custom_minimum_size = Vector2(120, 120)
	transit_btn.icon = TEX_MAP_THUMB
	transit_btn.expand_icon = true
	transit_btn.pressed.connect(_select_transit)
	_ms_transit_frame.add_child(transit_btn)
	tiles.add_child(_ms_transit_frame)
	for i in 3:
		var locked := PanelContainer.new()
		locked.custom_minimum_size = Vector2(120, 120)
		var lock_rect := ColorRect.new()
		lock_rect.color = Color("090a14", 0.85)   # blacked out
		lock_rect.custom_minimum_size = Vector2(120, 120)
		locked.add_child(lock_rect)
		var q := Label.new()
		q.text = "?"
		q.set_anchors_preset(Control.PRESET_CENTER)
		q.grow_horizontal = Control.GROW_DIRECTION_BOTH
		q.grow_vertical = Control.GROW_DIRECTION_BOTH
		q.add_theme_color_override("font_color", UITheme.TEXT_DIM)
		locked.add_child(q)
		tiles.add_child(locked)

	var info := VBoxContainer.new()
	info.add_theme_constant_override("separation", 6)
	info.custom_minimum_size = Vector2(200, 0)
	columns.add_child(info)
	# the district's NAME has to read as a heading, not as another line of
	# body copy (user: "you cant even tell transit is like the title").
	# The bitmap font is one size, so the heading is carried by the accent
	# colour and a rule underneath it.
	_ms_name = Label.new()
	_ms_name.text = "select a district"
	_ms_name.add_theme_color_override("font_color", UITheme.ACCENT)
	info.add_child(_ms_name)
	var name_rule := ColorRect.new()
	name_rule.color = Color(UITheme.ACCENT.r, UITheme.ACCENT.g,
		UITheme.ACCENT.b, 0.45)
	name_rule.custom_minimum_size = Vector2(0, 1)
	name_rule.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_child(name_rule)
	_ms_blurb = Label.new()
	_ms_blurb.text = "the wardens sealed four districts.\nonly one answers the radio."
	_ms_blurb.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_ms_blurb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ms_blurb.add_theme_color_override("font_color", UITheme.TEXT_DIM)
	info.add_child(_ms_blurb)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	info.add_child(spacer)
	# the district's clock, live, BEFORE you commit to it (user call): the
	# time you read here is the time you deploy into
	_ms_clock = Label.new()
	_ms_clock.add_theme_color_override("font_color", UITheme.ACCENT)
	info.add_child(_ms_clock)
	_ms_deploy = Button.new()
	_ms_deploy.text = "deploy"
	_ms_deploy.disabled = true
	_ms_deploy.pressed.connect(func() -> void:
		get_tree().change_scene_to_file("res://scenes/main.tscn"))
	info.add_child(_ms_deploy)
	var back := Button.new()
	back.text = "back"
	back.pressed.connect(_close_map_select)
	info.add_child(back)
	return panel


func _select_transit() -> void:
	_ms_name.text = "transit"
	# ONE pass over the places, then what actually matters before you
	# commit: how you get out, and what kills you. The old copy listed
	# every poi twice — once as prose and again under "on the board",
	# which meant nothing to anyone (user).
	_ms_blurb.text = "a town around its courtyard, the school and its playground to the south, a trainyard cut straight through the middle, the bus depot, a scrapyard, the comms relay - and woods on every side.\n\nthree ways out: the lift, the toll gate, the night freight.\n\nsnipers own everything past the wire."
	_ms_deploy.disabled = false


func _open_map_select() -> void:
	_buttons.visible = false
	_map_select.visible = true
	# the changelog button lives on the menu root, outside this panel, so
	# it stayed clickable underneath it (user)
	if _changelog_btn != null:
		_changelog_btn.visible = false


func _close_map_select() -> void:
	_map_select.visible = false
	_buttons.visible = true
	if _changelog_btn != null:
		_changelog_btn.visible = true


func _menu_button(parent: Container, text: String, handler: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(160, 0)
	button.pressed.connect(handler)
	parent.add_child(button)
	return button


func _open_settings() -> void:
	_buttons.visible = false
	_settings.visible = true
	_settings.focus_first()


func _close_settings() -> void:
	_settings.visible = false
	_buttons.visible = true


func _open_keybinds() -> void:
	_settings.visible = false
	_keybinds.visible = true


func _close_keybinds() -> void:
	_keybinds.visible = false
	_settings.visible = true


func _open_volume() -> void:
	_settings.visible = false
	_volume.visible = true


func _close_volume() -> void:
	_volume.visible = false
	_settings.visible = true
