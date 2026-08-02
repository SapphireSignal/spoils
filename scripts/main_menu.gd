extends Node2D
## Main menu. Generated backdrop scenes rotate with a slow crossfade,
## each with its own living detail:
##   den   - the traders at home: candle vs radio glow, smoke, rig LEDs
##   drain - the tunnel under the district: god-ray, motes, ringing drips
## (the storm scene retired 2026-08-01 — user call). DEPLOY starts the raid.

const SCENE_SECONDS := 20.0
const FADE_SECONDS := 1.4

# preloaded once for the process lifetime: re-entering the menu from the game
# must not re-decode these (that decode was a visible 1-2 frame hitch)
const TEX_DEN := preload("res://art/gen/menu_den.png")
const TEX_DEN_GLOW := preload("res://art/gen/menu_den_glow.png")
const TEX_DEN_NEEDLES := preload("res://art/gen/menu_den_needles.png")
const TEX_DRAIN := preload("res://art/gen/menu_drain.png")
const TEX_DRAIN_RAY := preload("res://art/gen/menu_drain_ray.png")
const TEX_DRAIN_RIPPLE := preload("res://art/gen/menu_drain_ripple.png")
const TEX_RAIN := preload("res://art/gen/rain_streak.png")
const TEX_DUST := preload("res://art/gen/dust.png")
const TEX_VIGNETTE := preload("res://art/gen/vignette.png")
const TEX_MAP_THUMB := preload("res://art/gen/menu_map_transit.png")
const TEX_TITLE := preload("res://art/gen/title.png")
const TEX_SHINE := preload("res://art/gen/title_shine.png")
const TEX_TAGLINE := preload("res://art/gen/tagline.png")

# painting-space -> scene-space (backdrops are 960x544, centered on origin)
const PC := Vector2(-480, -272)

const SHINE_PERIOD := 6.0   # seconds between gleams
const SHINE_SWEEP := 0.9    # gleam travel time
const SHINE_WIDTH := 34.0

var _scenes: Array[Node2D] = []
var _scene_index := 0
var _rotate_timer := 0.0
var _fade_tween: Tween
var _time := 0.0

# den life
var _candle_glow: Sprite2D
var _needles: Array[Sprite2D] = []
var _leds: Array[Sprite2D] = []
# drain life
var _ray: Sprite2D
var _ripples: Array[Sprite2D] = []
var _ripple_t: Array[float] = []
var _ripple_age: Array[float] = []
var _drip: Sprite2D
var _drip_t := 0.0

var _title: TextureRect
var _title_base_y := 0.0
var _shine_clip: Control
var _shine: TextureRect
var _buttons: VBoxContainer
var _settings: SettingsPanel
var _keybinds: KeybindsPanel
var _volume: VolumePanel
var _changelog: PanelContainer
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
	["v0.6.63", ["the power lines actually connect tower to tower now.",
		"they were getting a cell of random jitter like every",
		"other prop, which knocked each tower off the line so a",
		"span could never reach the next crossarm. the line is",
		"dead straight, and damage is rare instead of constant -",
		"a downed tower still shows the wire arriving and",
		"dropping, rather than the run just stopping"]],
	["v0.6.62", ["the grid runs across the district: lattice towers with",
		"the wires sagging between them, spans missing, whole",
		"runs snapped and left hanging in the air. it walks to",
		"the relay and goes underground into a yellow cabinet on",
		"the back of the last tower, with the gear somebody left",
		"on the ground around it"]],
	["v0.6.61", ["dying ends the raid now. three rounds and you get the",
		"same debrief walking out gives you - the doll, what you",
		"lost, who did it and where they hit you. no more waking",
		"up back at the safehouse like nothing happened"]],
	["v0.6.60", ["walking out of a raid is not free any more. the pause",
		"menu says abandon raid, and it hands you the same",
		"debrief dying would: how long you lasted, the xp, what",
		"you were carrying when you lost it, who put rounds in",
		"you and exactly where - a doll marks the parts that",
		"took them, one tick per round, thorax, stomach, head,",
		"eyes, arms, legs"]],
	["v0.6.59", ["every place has its own things in it now. benches,",
		"planters and a vending machine round the courtyard",
		"fountain. fare boxes and a mechanics leavings at the",
		"bus depot. tyres and a bench at the playground. paint",
		"and pallets at the gallery. cable drums and a toolbox",
		"at the relay. fuel and freight stacked at the lift.",
		"the wardens own chair and brazier by his booth. drums",
		"and sleepers along the yard. a handful each - enough",
		"to know where you are without the place looking dumped"]],
	["v0.6.58", ["freight moved to where freight belongs: the crates and",
		"shelves are out of the scrapyard and piled around the",
		"warehouses instead - stacks in the yard, loaded racks",
		"against the outside wall, trucks backed up with their",
		"load at the tailgate, and halls packed inside",
		"the scrapyard keeps the machines: forklifts, drums,",
		"cylinders and toolboxes left where somebody put them",
		"no more foggy on the weather line - the mist comes",
		"every morning, so it isnt a forecast"]],
	["v0.6.57", ["rain and storms are actually different weather now. a",
		"storm rains harder and throws lightning several times",
		"as often; plain rain only rarely flashes. fog is its",
		"own weather too, not just a dawn thing",
		"the map bar says the time, the part of the day and the",
		"weather - 07:12 morning - raining",
		"court and depot are now courtyard and bus depot, and",
		"the lz, gallery, comms and trainyard are outlined on",
		"the map like the other places"]],
	["v0.6.56", ["the clock and the light agree now: dawn at 06:00, dusk",
		"at 21:00, dark by 22:15 and still dark at 05:00. the",
		"dawn fog moved with it, and a raid starts at 07:12",
		"master volume at zero silences everything - it now",
		"pulls every channel down with it, not just the master",
		"the broken power boxes throw blue sparks that arc off",
		"the housing and burn out"]],
	["v0.6.55", ["the map select screen shows the districts clock and",
		"whether its day or night, ticking, before you commit -",
		"and the time you read there is the time you deploy",
		"into. the district keeps its own time while you sit in",
		"the menu"]],
	["v0.6.54", ["the freight keeps a timetable now: she comes at 24:00,",
		"the darkest point of the night, once per day - never in",
		"the morning - and mara only calls her in when shes",
		"actually coming",
		"the day is longer (18 minutes end to end)",
		"maras calls stay up two seconds longer, dont say her",
		"own name twice, and key up with a very quiet tick",
		"stranded boxcars sit BESIDE the running line instead of",
		"on it - the freight used to drive straight through one"]],
	["v0.6.53", ["houses have lights inside now. they come on with the",
		"dark, a third of them flicker, and every one has a",
		"cable you can follow across the floor to the power box",
		"on the outside wall. the safehouse is wired the same",
		"way but stays dark - its box is the broken one"]],
	["v0.6.52", ["pines shed now. they drop needles, not leaves - a",
		"thinner sprite that falls straight down instead of",
		"fluttering, because a needle has no blade to catch",
		"the air. dead bare snags still drop nothing, on",
		"purpose"]],
	["v0.6.51", ["transit is not laid out on graph paper any more.",
		"half the roads stop somewhere - the council never",
		"finished this district - and where the paving gives",
		"up it breaks apart and disappears under rubble.",
		"whole corners have no road at all now. every building,",
		"every place and your safehouse are exactly where they",
		"were; only the road network changed",
		"the map screen draws the real network, stubs and all"]],
	["v0.6.50", ["the stutter on first opening the changelog and the",
		"first time you open the map is gone. both were doing",
		"all their work in the frame you asked for them - the",
		"changelog builds every version now while the menu is",
		"still fading in, and the map draws itself once behind",
		"the deploying screen"]],
	["v0.6.49", ["the yellow centre line finally runs down the middle",
		"of the road. it was drawing on the half of the tile",
		"the neighbouring tile owns, so half the dash rendered",
		"as nothing and the rest sat a full lane off - and only",
		"on roads running one direction, which is why it looked",
		"fine half the time"]],
	["v0.6.48", ["bus shelters stopped parking half-in the road at",
		"crossings - any shelter whose roof would reach the",
		"crossing asphalt simply doesnt get built there"]],
	["v0.6.47", ["settings grew a volume page: master, music, effects",
		"and ambient each get their own slider - changes apply",
		"live and stick between sessions"]],
	["v0.6.46", ["the broken sparking power box is now always the",
		"safehouses own - somebody should really fix that",
		"maras radio popup is silent now - no more chirp when",
		"she keys up or drops off"]],
	["v0.6.45", ["your car finally faces the way youre driving - the",
		"left-right sprites had the body drawn one way, the",
		"lights painted the other way, and the pair swapped",
		"steering is instant now: tap any direction, or two",
		"keys for a diagonal, and the nose snaps right there -",
		"the slow carve is gone"]],
	["v0.6.44", ["housekeeping: the audits verified a pile of code that",
		"nothing calls anymore - unused helpers, signals nobody",
		"listens to, art nothing ever places - all deleted",
		"the game draws and plays exactly the same, theres just",
		"less of it left to go wrong"]],
	["v0.6.43", ["the sweep, part two - fifteen more, none silent:",
		"dying on the rope used to strand the helicopter in the",
		"sky and quietly kill every later way out of the raid",
		"you cant walk or drive away from your own lift anymore",
		"paying the warden buys one crossing now - come back",
		"inside the wire and the snipers shoulder their rifles",
		"dying at the wheel left the headlights burning all night",
		"a knocked-over barricade stopped clipping the toll booth",
		"the deploy tail lost its last unbudgeted stalls",
		"power box sparks arc in steps instead of shimmering",
		"the smokers exhale drifts off in puffs like it should"]],
	["v0.6.42", ["a code sweep found some bad ones:",
		"quitting to the menu with a window open used to leave",
		"every later raid unable to read your input at all",
		"dying on the freight was an unrecoverable softlock",
		"the first train was ten minutes late, not twenty seconds",
		"snipers could still hit you after youd paid to leave",
		"the edge of the district had no lamps, trees or vehicles",
		"rain kept playing under the menu after you quit"]],
	["v0.6.41", ["loading into transit had a 233ms stall in it. it was a",
		"developer contact sheet - half a megabyte of artwork the",
		"game never shows - being loaded every single raid"]],
	["v0.6.40", ["the snipers stop shooting once youre riding the freight",
		"out - catching it is a real way out, not a death sentence",
		"the first train now comes 20 seconds in, not 45",
		"it carries a headlamp down the rails and a warm cab glow,",
		"and steam breathes off the stack - harder when it pulls",
		"maras radio sits small and centred instead of filling",
		"the top left corner"]],
	["v0.6.39", ["the freight engine was missing its back end - the same",
		"bug the cars had. it has a proper wall now, with marker",
		"lamps and a cab window"]],
	["v0.6.38", ["the map shows which way youre facing now - a cone off",
		"your marker instead of just a dot, so you can tell",
		"which way to walk. it follows the car when youre driving"]],
	["v0.6.37", ["furniture stopped repeating. every house used to have",
		"the identical table, chair, bookshelf and cabinet -",
		"there are five of each now, worn and set their own way",
		"racks come in seven versions instead of four, so the",
		"yards stop showing you the same pair twice",
		"nothing picks the same version twice in a row anymore"]],
	["v0.6.36", ["the district is bigger: every block has more room, and",
		"the scrapyard warehouse is a proper hall again",
		"one railway all the way across the map now - same ties,",
		"same rail, tile to tile, properly connected",
		"(the worn and overgrown stretches are gone, they made it",
		"look like separate broken bits of track)"]],
	["v0.6.34", ["the scrapyard warehouse is back. fixing the track",
		"running under it had quietly deleted it instead,",
		"which put the racks back out in the open",
		"it now shrinks to fit beside the rails rather than",
		"vanishing - a smaller hall is still a hall"]],
	["v0.6.33", ["the railway stopped looking like a drawn line:",
		"telegraph poles march beside it at uneven spacing and",
		"swap sides, signals stand at the crossings and the yard",
		"throat, and junk piles up along the ballast",
		"the track itself wears in stretches now - some of it is",
		"overgrown, some is rusted with ties rotted away"]],
	["v0.6.32", ["the night freight runs. it comes into the yard every",
		"five minutes, stands for one, and goes without you",
		"mara calls it in on the radio before it arrives, warns",
		"you when its nearly out of time, and tells you off if",
		"you miss it",
		"press f to get on, then departing in 10... and it pulls",
		"out of the district with you aboard",
		"you can hear the mic key up and drop - thats her radio"]],
	["v0.6.31", ["leaves fall from every leafy tree now, and they take",
		"turns - no more one tree getting spammed while the tree",
		"beside it drops nothing",
		"pines and dead trees keep theirs, like they should",
		"a building could land on the railway. it cannot now"]],
	["v0.6.30", ["the toll gate: a warden in a booth on the south road,",
		"a boom across the asphalt, and a man who will talk",
		"until you pay him",
		"pull up in a car and press f - his window opens with",
		"his face in it. keep replying and he never runs out",
		"pay the fee and the boom goes up, the snipers look",
		"away, and you drive out past the wire to extract"]],
	["v0.6.29", ["clutter looks dumped now, not placed: crates, tires,",
		"barrels and rubble come in many more versions, each",
		"leaning its own way and worn its own way",
		"junk piles up unevenly with stragglers spilling off",
		"one side, instead of sitting in tidy stacks",
		"the same object never appears twice in a row"]],
	["v0.6.28", ["you can only interact with what the prompt is",
		"offering - doors and cars used to answer from further",
		"back than the game ever told you they would",
		"every prompt works this way now, and every new one will"]],
	["v0.6.27", ["you can get out now. the first way out is the lift:",
		"a clearing off a dirt track with green smoke coming",
		"out of it - stand in it and it counts you down",
		"a helicopter comes in over the trees, drops a rope,",
		"and pulls you up out of the district",
		"then the debrief: how you got out, how long you lasted,",
		"xp, and every kill with the minute and the bone",
		"(the haul column waits for the stash update)",
		"the toll gate and the night freight are next"]],
	["v0.6.26", ["the map is drawn now, not screenshotted: roads are",
		"real strokes, woods are soft green, buildings are solid,",
		"the rail has ties and the wire is a dashed red line",
		"no more boxes around anything - names sit on the map",
		"you are a pulsing ring you cannot lose",
		"it fills the window, and the zoom is smooth"]],
	["v0.6.25", ["windows behave now: whatever you have open owns the",
		"screen, and nothing behind it listens",
		"esc closes the map instead of opening settings behind it",
		"the scroll wheel zooms the map OR the world, never both",
		"every window says how to close it",
		"lore: rewritten so its clear nothing but people ever",
		"attacked this city (the mills machines are just factory",
		"equipment) - and transit is written down as a real place"]],
	["v0.6.24", ["cars point where theyre going - eight real angles now,",
		"drawn from the side and head on, not just the four corners",
		"every vehicle got wider: they were narrower than real cars",
		"and it showed the moment they turned",
		"new controls: get in and the engine starts itself, wasd to",
		"drive, e for lights, f to get out (and it shuts off)",
		"no more engine key, no more clicking to follow the cursor"]],
	["v0.6.23", ["the map is real now: press m for the whole district,",
		"every place named, and a little me that moves as you do",
		"clicking transit works (it didnt - the window ate it)",
		"second floors read like floors: wood, a lit edge, and",
		"the town has proper two-story houses again",
		"the school is a school: chalkboard, desks and chairs",
		"safehouse: a parking pad, fewer fences, and the power",
		"box walked away from the window",
		"bushes and benches got real depth - masses, not stickers",
		"driving: steering carves, crashes thump, smoke at full",
		"speed, and the controls card is clearer and stays longer",
		"the static at speed is gone. trails respect sidewalks.",
		"the yellow line got its other half back"]],
	["v0.6.22", ["the district is fixed now - one map, the same streets",
		"every raid. learn it: quests will hand out addresses",
		"the scrapyard got its warehouse back - the racks and",
		"boxes finally belong to something",
		"bushes are walk-in cover: taller than you, and you fade",
		"with the bush so you always know when youre hidden",
		"the rummage is slow and lazy now, and the rustle carries",
		"the gallery regular is your size, on benches built for",
		"grown raiders - and his spray cans differ drop to drop",
		"under the hood: leaner frames, one real fence bug dead"]],
	["v0.6.21", ["the bushes grew up - big enough to disappear into",
		"(hiding from people in them comes with the people)",
		"half the woods turned: an autumn grove of orange oaks",
		"red leaves fall only there - green trees drop green now"]],
	["v0.6.20", ["you spawn in the safehouse now - same squat house every raid,",
		"fenced and pyloned, near the south of the map",
		"cars drive free on the cursor now, not locked to directions",
		"top speed pulled down - it was a rocket",
		"trucks no longer flash a different colour for the door swing",
		"real collision: cars, buses and boxcars block along their",
		"whole body - no more walking through a nose or tail",
		"tree trunks and lamp posts push back too (bushes stay soft,",
		"thats what the rustle is for)",
		"half of all trees and bushes shed leaves now, and faster",
		"the warehouse always builds - no more shelves in the open",
		"pallets stop your feet instead of swallowing them",
		"the comms relay moved out by the woods where it belongs",
		"the fleet got new paint: steel blue and tan join the lot,",
		"and matching trucks are far less likely twins",
		"one yellow line per road, dead center, as painted",
		"stairs sit in a corner of the room now",
		"no more using the front door from the second floor"]],
	["v0.6.19", ["press m: the map. world view first, then transit in detail",
		"drag to pan, scroll to zoom, hover anything for a tooltip",
		"it shows where you are, the cars, the time and the weather",
		"play replaces deploy: pick your raid off the cordon map",
		"new places: the scrapyard (with its crane) and the gallery",
		"someone still smokes at the gallery. he brought his cans",
		"buses stop nowhere, but vending machines and newspaper",
		"boxes and extra dumpsters still hold the corners down",
		"every house got a power box - one is having a bad day",
		"cars drive by cursor now: click and they chase it, click to stop",
		"car doors, engines and alarms all sit quieter",
		"the alarm lights actually glow at night",
		"bushes really rustle now and oaks really shed - both were broken",
		"one thunder per flash, and it doesn't cut out anymore",
		"upstairs is a real ceiling - no peeking at the ground floor",
		"worn trails link the houses, pausing at every road and walk",
		"the yellow line sits on the true middle of the road",
		"the map itself is a bit smaller again",
		"your raider stands a touch taller - and prone got shoulders",
		"the den board is legible now, and properly pinned up",
		"the splash takes its time - watch the signal go out"]],
	["v0.6.18", ["the map got way smaller again - and it has real places now",
		"the town: houses packed around a paved courtyard with a dry fountain",
		"some houses grew a second floor - press f at the stairs to go up",
		"upstairs you only see the room youre in, the way it should be",
		"new spots: the school and its playground, a trainyard with boxcars,",
		"the bus depot, and a fenced comms relay pointing at nothing",
		"a real forest district too - with stray trees everywhere else",
		"windows are glass now instead of black holes",
		"sidewalks line every road, so grass never touches asphalt",
		"roads keep only their cracks and potholes - nothing else on them",
		"cars drive now: f to enter, q for the engine, e for headlights,",
		"w s a d to roll around, f again to step out",
		"fog comes in mixed sizes and stopped blinking in and out",
		"music fades in and out longer and softer everywhere",
		"the storm menu backdrop retired - the den and the drain remain"]],
	["v0.6.17", ["morning fog: mist banks drift through the woods and roads at dawn",
		"the oaks shed leaves now - watch them flutter down on the wind",
		"a full day is 10 minutes now, down from 20",
		"nights are properly dark - you will want the flashlight",
		"raid tracks bow out with a gentle fade instead of stopping dead",
		"about thirty seconds of quiet between raid tracks",
		"rain eases in and out instead of switching on, and sits quieter",
		"thunder cracks sooner after the flash, and softer"]],
	["v0.6.16", ["raid music: your three picks rotate randomly, never twice in a row",
		"music plays from raid start until you die - no more random cuts",
		"a music folder in the game directory holds the whole audition list",
		"roads are smooth now, with real cracks and the odd pothole",
		"sidewalks: clean slabs, some hairline-cracked, some broken open",
		"bushes grow in the greens - push through and they rustle, wiggle,",
		"and go see-through around you",
		"grass tufts, benches and bus shelters fill the empty corners",
		"the woods lost their red confetti - green floors, brown for dirt only",
		"dirt paths got gray mud mixed in - no more blood-red stripes"]],
	["v0.6.15", ["three new living menu backdrops: the den, the drain, the storm",
		"the den: kettle, verne and mara at home - candle vs radio glow",
		"the job board pins every district - transit ringed red, tonight's job",
		"the drain: one shaft of light, dust sinking, drips ringing the water",
		"the storm: the sealed city under lightning, rain, real thunder",
		"building windows flicker, brown out, die, struggle back - all live",
		"quiet music drifts through raids now - sparse tracks, long silences",
		"the dot-grit is gone everywhere: clean surfaces, honest wear",
		"dirt paths show ruts and clods instead of red noise",
		"more tile and wall variety so nothing repeats down a long street"]],
	["v0.6.14", ["the map is half the size - a tight district, no more hiking",
		"sidewalks line many roads, slab by slab, some cracked open with weeds",
		"crosswalks at every intersection, worn down to almost nothing",
		"dead traffic lights watch the crossings - bent, smashed, or face down",
		"the ground has moods now: sun-worn blocks, damp mossy blocks, manholes",
		"warehouses are huge industrial halls with more racks and stock",
		"shelves grew to hold their boxes, and the boxes look human-stacked",
		"snipers lead their shots - they aim where you are going, so juke",
		"volleys come staggered from different shooters, never one wall",
		"the turn-back warning sits dead center, a touch above the middle",
		"locked into the plan: the tunnels arrive with the guns update"]],
	["v0.6.13", ["cars and trucks have real backs now - you circled it, that was it",
		"the rear is a full wall across the body: tailgate, trunk, grille",
		"tail lights and head lights sit at both corners like they should",
		"real menu music: a lonely guitar theme (the last pack, by davidkbd)",
		"real recorded footsteps on every surface - and quieter overall",
		"real thunder, cut from an actual storm recording. no more torch",
		"code spring-clean under the hood - nothing should look different"]],
	["v0.6.12", ["car look rolled back to the original dark ends (your call)",
		"kept: the ramp fills, smaller wheel arches, attached door"]],
	["v0.6.11", ["everything is 3d now: pillars are real columns with caps",
		"snapped pillars show their broken tops - rebar and all",
		"gas tanks got domed shoulders and curved bands like the barrels",
		"tire stacks show the dark hole down the middle",
		"rubble piles have lit and shaded slopes with a bright ridge"]],
	["v0.6.10", ["car ends are visible now - they existed but were painted too dark",
		"wheel arches no longer bite into hoods and trunks",
		"the broken-into door hangs attached to the car, not floating below",
		"holes in ruined roofs show attic darkness, not the ground outside",
		"sniper volleys: 2-3 shots converge at once, and they fly faster",
		"zoom reworked: no more overpowered zoom-out, ladder reaches 6x",
		"zoom glides smoothly between stops and always rests pixel-perfect"]],
	["v0.6.9", ["the missing car parts are ACTUALLY fixed (raked windshields had gaps)",
		"barrels are properly 3d now - real top faces, curved hoops",
		"the barricade line is lattice fencing now, denser, with concrete accents",
		"no more road running along the barriers",
		"footsteps are properly distinct per surface - and quieter",
		"rain is a soft distant wash now - no crackle, no repeating, no swelling",
		"car alarms lost their static edge",
		"lightning comes in bursts of 1, 2 or 3 strikes",
		"mouse wheel zooms: two steps in, one honest step out",
		"the day cycle can't visibly step anymore (anti-banding film)",
		"boxes only spawn near warehouses now",
		"splash fades into the menu instead of cutting",
		"tv stand, couch, dumpster and more were clipped at their edges - all",
		"fixed, and the art pipeline now refuses to ship a clipped sprite"]],
	["v0.6.8", ["the sapphire signal splash: the gem, the ping, the first beam",
		"main menu music - a dark theme for a dead district, made by code",
		"footsteps: concrete, asphalt, hardwood, grass and dirt all sound right",
		"steps go quiet when crouched, drag when prone",
		"thunder rolls in after every lightning strike - distance included",
		"a soft rain bed rises and falls with the storm",
		"car alarms: get close to the wrong intact car and it goes off",
		"alarm lights flash for 3 seconds - once per car, until you die",
		"vehicles are fully solid now - the dotted roof lattice is gone",
		"broken-into cars read honest: a door hanging open, a flat tire",
		"every car has both ends now - the hidden side closes properly",
		"the flashlight click, door thunks and sniper crack all kept company"]],
	["v0.6.7", ["the barricade line is a real line now: one piece repeated, worn",
		"some barriers knocked askew, some flat, uneven gaps - not a sampler",
		"past the line is bare dead concrete - the woods live inside the map",
		"roads dead-end at the wreckage on the line",
		"biomes blend: grass creeps onto touching concrete, dirt smears too",
		"no more lone grass tiles - pockets and groves have real shapes",
		"the fallen out past the line are full character-sized now",
		"prone is beefier - same proportions as standing, all 8 directions"]],
	["v0.6.6", ["go prone on z: flat on your stomach, crawling",
		"prone is slower than crouch - low, slow, hard to spot",
		"crouch input stands you back up out of prone",
		"the door prompt now floats on the door itself"]],
	["v0.6.5", ["the playable map is smaller - barricades mark the real edge now",
		"the world visibly continues past the line, but the sniper owns it",
		"fallen raiders lie out past the barricades. let them be a warning",
		"the camera never shifts at the edge - locked on you, always",
		"push deeper past the line and the shots only come faster",
		"cars have real fronts and backs - grilles, lights, bumpers, trunks",
		"truck cargo sits inside the bed now, nothing pokes through the cab",
		"deploying no longer dips the framerate",
		"a prompt appears at doors: press f to open, press f to close",
		"the flashlight actually clicks",
		"weather fades in and out slowly - no more sudden color shifts",
		"deep night is much darker - the flashlight and lamps matter now",
		"new on the roadmap: tarkov-style loot and gear slots, quests, a second map"]],
	["v0.6.4", ["fixed the blurry walk: character and camera share one pixel grid now",
		"diagonal walking no longer shimmers the world",
		"the character is pixel-locked to the screen while moving"]],
	["v0.6.3", ["the map is 4x bigger again - and it has a name: transit",
		"every deploy now builds a fresh district",
		"walk to the true edge of the map - no early wall, no black void",
		"but the edge is sniper country: heed the warning or take 3 hits",
		"hurt flashes, death and respawn - the game's first damage",
		"doors are real: closed until you walk up and press f",
		"flashlight on e - nights are properly dark now",
		"street lights glow and flicker at night - most are dead, like the district",
		"rain is real: drops fall in the world and splash where they land",
		"splashes stay on the ground instead of following you",
		"all rain is the same blue as the puddles",
		"storms and lightning last longer; a full day is 20 minutes",
		"dusk fades properly - no more instant nighttime (found the bug)",
		"cars are wider, face the right way in their lanes, some broken into",
		"litter around broken cars; sticks under the trees",
		"trees rebuilt: connected tops, a new leafy kind, groves inside the map",
		"crate stacks no longer clip their top box",
		"roof edges are clean - removed the rippling overhang",
		"one floor per building - no more patchwork interiors",
		"center dashes on every road, seamless from tile to tile",
		"furniture can never block an entrance again",
		"left arm seam restored - symmetric character again",
		"fewer dots on the ground everywhere",
		"walking is smoother: camera scrolls in screen pixels now",
		"deploy no longer dips the framerate - the world builds across frames",
		"fps counter updates five times a second"]],
	["v0.6.2", ["the map is 10x bigger - a whole district, and it never ends",
		"edges fade into deep woods, no more visible void",
		"road network across the map + dirt roads into the forests",
		"forests full of pines and dead trees",
		"12 randomized buildings to explore, houses and warehouses",
		"street lights along the roads",
		"real vehicles: cars and loaded pickups, parked and abandoned",
		"doors on every building", "warehouse floors are gray concrete now",
		"day turns to night and back", "rain comes and goes, with lightning",
		"raindrops visibly hit the ground", "puddles form in rain, dry in sun",
		"deploying screen when you enter a raid (no more frame dip)",
		"house furniture fixed - bookshelf is back, no barrels indoors",
		"less random junk, and it gathers around buildings now"]],
	["v0.6.1", ["loading yard by the warehouse: stall lines, pickup trucks",
		"boxes in the truck beds, stray stock around the yard",
		"crouch: hold or toggle option next to its keybind",
		"warehouse floor is a green sealed screed now",
		"racks + crate stacks: messy randomized loads, nothing identical",
		"roof corner caps flush, trim lines continue through corners",
		"gold in the vault falls down the light shaft",
		"menu buttons exactly centered, smaller static tagline",
		"silver shine sweeps the title",
		"version plan: 0.7 guns, 0.8 enemies, 0.9 raid loop, 1.0 full game"]],
	["v0.6.0", ["keybinds screen in settings: rebind every key",
		"crouch on ctrl: lower profile, slower movement, crouched sprites",
		"interact, reload, flashlight and weapon slot keys registered",
		"house and warehouse are different sizes, doors always visible",
		"wooden floors in the house, dark screed in the warehouse",
		"furniture: couch, tv, cabinet, bookshelf, table, chairs",
		"warehouse racks and stacked stock - all randomized placement",
		"broken roof sections over the ruined corner", "all roofs black",
		"bigger title with a readable outlined tagline",
		"vsync now greys out the fps cap (it drives the frame rate)",
		"settings window is a fixed, slightly wider size"]],
	["v0.5.6", ["all walls and corners symmetrical again",
		"slim wall tops - the wide cap looked like a lid on a thin wall",
		"roof eaves now overhang and fully cover the wall tops",
		"roof caps over every corner post and door jamb",
		"buttons restyled: dark with a light border - readable on every scene", "changelog button visible again"]],
	["v0.5.5", ["more detail in this changelog",
		"new burgundy buttons that stand out on every backdrop",
		"changelog link dimmed to match the footer"]],
	["v0.5.4", ["changelog viewer (this!)",
		"menu art stays loaded so returning from a raid does not hitch",
		"only the first backdrop pre-warms its particles"]],
	["v0.5.3", ["roofs rebuilt from modular pieces placed by exact formula",
		"one roof tile per floor cell + trim pieces on the eaves",
		"wall caps now tuck under the roof instead of poking past it",
		"corner posts sit flush in the roofline - clean corners everywhere"]],
	["v0.5.2", ["roofs sit flush on the walls (were overhanging)",
		"roof only hides when you are actually inside the walls",
		"buildings are different materials: red brick vs gray masonry",
		"the two roofs are different shades of black",
		"back-view neck fixed and verified with an in-game capture"]],
	["v0.5.1", ["menu buttons: no box around them, slightly see-through",
		"first sounds in the game: soft hover + click blips, made by code",
		"walls always stay visible inside buildings (no see-through)",
		"one doorway per building (a frame post was splitting it in two)",
		"character has hair now instead of the beanie",
		"arms are truly symmetric", "main menu button on the pause screen"]],
	["v0.5.0", ["text crisp for real - found the font bug that blurred all ui",
		"new lowercase-only pixel font, no capitals anywhere",
		"buildings became real thin walls with door frames and posts",
		"three rotating menu backdrops with sparkles, neon and clouds",
		"treasure vault, scrapyard and cliff overlook scenes"]],
	["v0.4.0", ["first main menu with a live background",
		"first pixel font for the ui", "roofs + walk-inside roof reveal",
		"every prop family got real variations: sizes, damage, fallen poses",
		"barrels, crates, cylinders, tires, pallets, dumpsters, rubble, pillars",
		"resolution option in settings", "fps counter moved and restyled"]],
	["v0.3.0", ["pause menu on esc with settings and quit",
		"display mode, fps cap slider, vsync, show fps",
		"settings save and reload on launch",
		"fullscreen fills the whole screen at crisp pixel scale"]],
	["v0.2.1", ["motion updates every frame - smooth on 240hz monitors",
		"camera locked to whole pixels: no more shimmer while walking",
		"fullscreen by default"]],
	["v0.2.0", ["ground is one smooth surface, no more tile grid",
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
	_activate(clampi(index, 0, _scenes.size() - 1), true)
	_rotate_timer = 0.0


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
	_rotate_timer += delta
	if _rotate_timer >= SCENE_SECONDS:
		_rotate_timer = 0.0
		_activate((_scene_index + 1) % _scenes.size(), false)

	_title.position.y = _title_base_y + roundf(sin(_time * 1.3) * 2.0)

	# silver gleam sweeping across the wordmark every few seconds
	var phase := fmod(_time, SHINE_PERIOD)
	if phase < SHINE_SWEEP:
		_shine_clip.visible = true
		var title_pos := _title.global_position
		var travel := _title.size.x + SHINE_WIDTH * 2.0
		_shine_clip.global_position = Vector2(
			roundf(title_pos.x - SHINE_WIDTH + travel * (phase / SHINE_SWEEP)),
			title_pos.y)
		_shine.global_position = title_pos
	else:
		_shine_clip.visible = false

	# per-scene life (also during crossfades — anything visible stays alive)
	if _scenes[0].visible:
		_tick_den()
	if _scenes[1].visible:
		_tick_drain(delta)


func _menu_reset_windows() -> void:
	## belt and braces with main.gd: whichever scene we arrive from, the
	## menu starts with no windows claimed (see the Ui.clear note there)
	Ui.clear()


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
	smoke.amount = 5
	smoke.lifetime = 7.0
	smoke.preprocess = 7.0
	smoke.position = PC + Vector2(334, 372)
	smoke.direction = Vector2(-0.15, -1)
	smoke.spread = 9.0
	smoke.gravity = Vector2(0, -3)
	smoke.initial_velocity_min = 4.0
	smoke.initial_velocity_max = 8.0
	smoke.color = Color("577277", 0.35)
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
	motes.amount = 13
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
	for pos in [Vector2(608, 514), Vector2(646, 524)]:
		var ripple := Sprite2D.new()
		ripple.texture = TEX_DRAIN_RIPPLE
		ripple.hframes = 3
		ripple.position = PC + pos
		ripple.visible = false
		drain.add_child(ripple)
		_ripples.append(ripple)
		_ripple_t.append(randf_range(0.5, 2.5))
		_ripple_age.append(-1.0)
	_drip = Sprite2D.new()
	_drip.texture = TEX_RAIN
	_drip.modulate = Color("a8b5b2", 0.8)
	_drip.visible = false
	drain.add_child(_drip)
	add_child(drain)
	_scenes.append(drain)

	for scene in _scenes:
		scene.modulate.a = 0.0
		scene.visible = false


func _tick_den() -> void:
	var a := 0.82 + 0.14 * sin(_time * 6.7) + 0.05 * sin(_time * 17.3)
	if fmod(_time, 9.1) < 0.35:                     # the flame gutters
		a *= 0.45
	_candle_glow.modulate.a = clampf(a, 0.0, 1.0)
	for i in _needles.size():
		var wob := sin(_time * (7.0 + i * 1.7) + i * 2.6) + sin(_time * 3.1 + i)
		_needles[i].frame = clampi(roundi(wob * 0.8 + 1.0), 0, 2)
	for i in _leds.size():
		_leds[i].visible = fmod(_time + i * 1.3, 3.7 + i) < 2.8


func _tick_drain(delta: float) -> void:
	_ray.modulate.a = 0.86 + 0.12 * sin(_time * 0.8)
	for i in _ripples.size():
		if _ripple_age[i] >= 0.0:
			_ripple_age[i] += delta
			var f := int(_ripple_age[i] / 0.3)
			if f > 2:
				_ripples[i].visible = false
				_ripple_age[i] = -1.0
				_ripple_t[i] = randf_range(1.6, 4.5)
			else:
				_ripples[i].frame = f
		else:
			_ripple_t[i] -= delta
			if _ripple_t[i] <= 0.0:
				_ripple_age[i] = 0.0
				_ripples[i].visible = true
				_ripples[i].frame = 0
	_drip_t -= delta                                # one drip at a time
	if _drip_t <= 0.0 and not _drip.visible:
		_drip_t = randf_range(2.5, 6.0)
		_drip.visible = true
		_drip.position = PC + Vector2(608, 110)
	if _drip.visible:
		_drip.position.y += 900.0 * delta
		if _drip.position.y >= PC.y + 508.0:        # hits the water: ring it
			_drip.visible = false
			_ripple_age[0] = 0.0
			_ripples[0].visible = true
			_ripples[0].frame = 0


func _fade_ramp() -> Gradient:
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0))
	ramp.add_point(0.2, Color(1, 1, 1, 1))
	ramp.add_point(0.8, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	return ramp


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
	root.add_child(_title)

	# gleam layer: a narrow clipping window sweeps over a silver copy
	_shine_clip = Control.new()
	_shine_clip.clip_contents = true
	_shine_clip.size = Vector2(SHINE_WIDTH, _title.texture.get_height())
	_shine_clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shine_clip.visible = false
	_shine = TextureRect.new()
	_shine.texture = TEX_SHINE
	_shine.stretch_mode = TextureRect.STRETCH_KEEP
	_shine.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shine_clip.add_child(_shine)
	root.add_child(_shine_clip)

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
	var changelog_btn := Button.new()
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

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(280, 210)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_changelog_list = VBoxContainer.new()
	_changelog_list.add_theme_constant_override("separation", 3)
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
	_ms_name = Label.new()
	_ms_name.text = "select a district"
	_ms_name.add_theme_color_override("font_color", UITheme.TEXT_BRIGHT)
	info.add_child(_ms_name)
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
	_ms_blurb.text = "the sealed transit district: a town and its courtyard, the school, a trainyard, the bus depot, a scrapyard, the comms relay - and the woods between them. snipers own the edge. bring a flashlight.\n\non the board: home base - courtyard - school - trainyard - depot - comms - gallery - scrapyard"
	_ms_deploy.disabled = false


func _open_map_select() -> void:
	_buttons.visible = false
	_map_select.visible = true


func _close_map_select() -> void:
	_map_select.visible = false
	_buttons.visible = true


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
