extends Node2D
## Main menu. SIX generated backdrop scenes rotate with a slow crossfade, in a
## shuffle-bag order (see _bag_next) so no backdrop repeats until every one of
## them has been shown. Two of them are ALIVE and tick every frame:
##   0 den   - the traders at home: candle vs radio glow, smoke, rig LEDs
##   1 drain - the tunnel under the district: god-ray, motes, ringing drips
## The other four are STATIC paintings for now — a living layer for them is
## the next version's job, so do not assume one exists:
##   2 yard      - the trainyard
##   3 warden    - the toll gate warden
##   4 underpass - the road underpass
##   5 counter   - the counter
## (the storm scene retired 2026-08-01 — user call). DEPLOY starts the raid.

const SCENE_SECONDS := 10.0
const FADE_SECONDS := 1.4

# preloaded once for the process lifetime: re-entering the menu from the game
# must not re-decode these (that decode was a visible 1-2 frame hitch)
const TEX_DEN := preload("res://art/gen/menu_den.png")
const TEX_DEN_GLOW := preload("res://art/gen/menu_den_glow.png")
const TEX_DEN_NEEDLES := preload("res://art/gen/menu_den_needles.png")
const TEX_DRAIN := preload("res://art/gen/menu_drain.png")
const TEX_DRAIN_RAY := preload("res://art/gen/menu_drain_ray.png")
const TEX_DRAIN_RIPPLE := preload("res://art/gen/menu_drain_ripple.png")
const TEX_YARD := preload("res://art/gen/menu_yard.png")
const TEX_WARDEN := preload("res://art/gen/menu_warden.png")
const TEX_UNDERPASS := preload("res://art/gen/menu_underpass.png")
const TEX_COUNTER := preload("res://art/gen/menu_counter.png")
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
	_rotate_timer += delta
	if _rotate_timer >= SCENE_SECONDS:
		_rotate_timer = 0.0
		_activate(_bag_next(), false)

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

	# per-scene life (also during crossfades — anything visible stays alive).
	# Only 0 and 1 are alive; 2-5 are still paintings and tick nothing, so
	# they are deliberately absent here rather than missing by accident.
	if _scenes[0].visible:
		_tick_den()
	if _scenes[1].visible:
		_tick_drain(delta)


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

	# 3-6: STILL PAINTINGS — no living layer yet, that is the next version.
	# They rotate on exactly the same footing as the two above; the only
	# difference is that nothing in _process ticks them.
	for texture in [TEX_YARD, TEX_WARDEN, TEX_UNDERPASS, TEX_COUNTER]:
		var still := Node2D.new()
		_backdrop(still, texture)
		add_child(still)
		_scenes.append(still)

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
