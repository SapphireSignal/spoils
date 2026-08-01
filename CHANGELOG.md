# Changelog

All notable changes to SPOILS are documented here. Versions follow a simple
`0.minor.patch` scheme while the game is pre-release.

## [0.6.16] — 2026-08-01

### Changed
- **Raid music, the user's way:** they auditioned 23 candidate tracks from
  a listening folder (`music/in game music/`, .gdignore'd) and kept three
  (guitar 02 / harp 01 / piano 01). Those now rotate randomly — never the
  same twice in a row — playing continuously from raid start until death
  with only a 2–5 s breath between tracks (the old 70–180 s silences read
  as broken audio). Death stops the music; respawn restarts it.
- **Streets cleaned up** (user call): asphalt is SMOOTH, with damage moved
  into dedicated tiles — wandering cracks (~4.5%) and chipped potholes
  (~2%). Sidewalks are clean slabs with joints; ~16% carry a hairline
  crack, ~10% are broken open to the dirt.
- **The world got little lives** (user request): BUSHES in the greens and
  against buildings — walk through one and it rustles, wiggles (whole-
  pixel, grid-safe), and fades to 55% around you (new Foliage manager);
  grass TUFTS breaking through bare concrete; BENCHES and BUS SHELTERS
  (it is the transit district) spaced along the walkways; and a dead-spot
  pass that drops a tuft, bush, or scrap of litter wherever a whole
  neighborhood scanned empty.
- **Color corrections:** forest floors are green-family only (the old
  warm-brown patches read as red confetti across every wood); dirt paths
  mix in gray mud so long strips no longer read blood-red.
- **Harness hardening:** any run whose world never readies now aborts
  loudly after 30 s instead of hanging (the "stuck background task" the
  user kept having to kill); the world probe reports WALKS and FOLIAGE.

## [0.6.15] — 2026-08-01

### Changed
- **Three new living menu backdrops** (user's picks, replacing hoard/
  scrapyard/overlook): **the den** — kettle, verne and mara at home in
  two-tone light (candle vs radio), the job board pinning every district
  with transit ringed red; **the drain** — the tunnel under the district,
  side-on, one god-ray from an open manhole, ladder, raider cache;
  **the storm** — the whole sealed city under a cloud deck. Every scene is
  alive at runtime: breathing candle glow and dancing VU needles and rig
  LEDs and ashtray smoke (den); sinking dust motes, a breathing ray, drips
  that ring the water (drain); rain that gusts on strikes, double-flash
  lightning that edge-lights the skyline, forked bolts, delayed real
  thunder, and building windows that flicker, brown out, die and struggle
  back (storm). Backdrop indices for the harness: 0=den 1=drain 2=storm.
- **In-raid music** (user request): three sparse loops from "The Last"
  pack (dongxiao / harp / guitar) at -26 dB with 70–180 s of silence
  between tracks — felt more than heard. Menu keeps its guitar theme.
- **The dot-grit is dead everywhere** (user call): per-pixel speckle
  replaced by small solid wear patches across every floor tile, banded
  cel light in the menu paintings, wavy solid gradient seams, structured
  dirt (ruts, clods, stones). The invisible 1/255 anti-banding film stays
  — it is imperceptible and prevents visible day-cycle tint stepping.
- **More baked variety everywhere** (user request): asphalt 2→4, screed
  2→4, house wood 3→5, forest 3→4, dirt 3→4, sidewalks 2→4 (+2 broken),
  blends +1 each, crack/stain/moss +1 each, roof tiles 2→4 per tone, and
  plain WALL SEGMENTS now roll among three variants per style/axis so
  long walls never repeat one image.
- Note for future sessions: menu screenshots have ALWAYS reported absurd
  fps in the corner counter (historical shots show "1 fps"); it is a
  capture-harness artifact, not a menu regression.

## [0.6.14] — 2026-08-01

### Changed
- **The district tightened to roughly half its area** (user: "the map is way
  too big", second report). The barricade ring moved from inset 31 to 72 on
  the 320×320 world; the road grid, ~21 buildings, forests and scatter now
  pack a ~176×176 playable core (placement counts rebalanced to match). The
  sniper buffer beyond the ring more than doubled in depth. Deploy builds in
  ~1 s; node count nearly halved.
- **Streets grew street furniture:** sidewalks flank many roads (pale slab
  bands, joint lines every half tile, ~13% of slabs cracked open to the dirt
  with weeds in the bites), heavily worn zebra crosswalks mark every
  intersection arm, rare manholes dot the asphalt, and dead traffic lights
  stand at the crossings — one municipal design in five states: dark (two
  arm lengths), bent, smashed (glass down, wire dangling), knocked flat.
- **Ground pass:** two new concrete tones (sun-worn, damp/mossy) applied in
  district-scale weathering zones via doubled offset hash grids — blocks
  read differently aged, with borders dissolving as grain, never a patch
  grid.
- **Warehouses are huge industrial halls now** (13-17 × 9-12 cells), with up
  to five racks and roughly doubled floor stock. Racks got wider, deeper
  frames (user: shelves read too small) and human stacking: staggered
  heights, off-grid offsets, boxes shoved together, mixed sizes.
- **Snipers predict.** Rounds lead the runner (aim at position + velocity ×
  flight time, with per-shooter over/under-lead), and volleys stagger across
  fractions of a second — separate shooters, separate cracks, never one
  simultaneous wall. The turn-back warning now anchors to true screen
  center (a touch above middle) on any resolution.
- Roadmap: the underground TUNNELS (bookshelf passages in some houses + two
  interactive manholes with ladders) are specced into Milestone 2 alongside
  gunplay; enemy high-visibility accents specced into M3.

## [0.6.13] — 2026-08-01

### Fixed
- **Vehicles have real backs and fronts now — the saga is over.** The user's
  circled screenshot pinpointed it: the end face was drawn as a short stub
  continuing off the near corner (lengthwise), so the rear read as "hanging
  out" beside the body instead of closing it. End faces are now FULL-WIDTH
  walls spanning the body along the iso width axis — tailgate on pickups,
  trunk wall on cars, grille face on front-on vehicles — with lights at both
  corners, a shutline, and a bumper strip. Confirmed by the user on trucks
  ("yes thats it, exactly like that"); the same fix applied to cars at their
  request.

### Changed
- **Real audio arrives (design-doc amendment, user call).** The synth-only
  rule is retired for organic sounds; licenses tracked in
  `assets/audio/LICENSES.md`:
  - **Menu music:** a lonely guitar loop from DavidKBD's "The Last"
    post-apocalyptic pack (CC-BY 4.0) replaces the synthesized drone theme.
  - **Footsteps:** real recordings per surface (concrete, tile-as-asphalt,
    wood, grass, gravel-as-dirt) from congusbongus's OpenGameArt pack
    (CC-BY 3.0), peak-normalized and mixed quieter than before — subtle,
    never obnoxious (user report: steps were too loud).
  - **Thunder:** three distant-rumble cuts from Gregor Quendel's storm field
    recording (CC-BY 4.0) replace the synth burst that read as "a torch
    starting up".
- UI blips, door thunks, the sniper crack, flashlight click, splash ping,
  rain bed and car alarms stay synthesized — they were approved as-is.

## [0.6.12] — 2026-08-01

### Changed
- **Car end-cap colors rolled back to the original dark look** (user call —
  the brightened caps from the visibility fix read worse). The v0.6.10
  geometry fixes stayed: raked-ramp fills, smaller wheel arches, the
  attached broken-car door.

## [0.6.11] — 2026-08-01

### Changed
- **The 3D-illusion pass** (user call: everything should read like the
  barrels and cars): pillars rebuilt as true iso columns — diamond caps on
  intact ones, rough broken tops with exposed rebar on snapped ones, lit
  west / shaded east faces, a plinth at the base. Upright gas cylinders got
  elliptical shoulders, domed crowns, valve stubs, and safety bands that
  follow the curvature. Tire stacks are stacked tori — the top tire shows
  its tread ellipse and the dark hole through the middle. Rubble piles have
  a lit western slope, a shaded eastern slope, a bright crest ridge, and
  dark ground contact. Everything else (crates, furniture, buildings) was
  already prism-built.

## [0.6.10] — 2026-08-01

### Fixed
- **The car ends were there all along — painted invisibly.** The end caps
  used each scheme's darkest tone, which vanished against dark asphalt and
  kept reading as "missing front/back" through three geometry fixes. Caps
  now use the mid body tone with a lit top edge and a visible steel bumper.
  Also: the wheel-arch carve was oversized and bit through the 8px-tall
  hood/trunk sections (shrunk, kept below the trim), and the broken-variant
  open door now hinges attached at the sill instead of floating underneath.
- **Ruined roof holes show attic darkness** instead of being transparent —
  a true hole displayed whatever rendered beneath the lifted roof sprite
  (misprojected exterior ground, even wall pieces).

### Changed
- **Sniper volleys**: 2–3 rounds converge at once from different off-screen
  angles (one crack per volley), and rounds fly at 1150 px/s — dodging on
  reaction should barely work.
- **Zoom rework**: the overpowered extra zoom-out is gone (native view is
  the widest); the ladder now reaches 6x with smooth glides between stops,
  always resting on whole pixel factors.

## [0.6.9] — 2026-08-01

The polish storm: everything the playtest surfaced in one pass.

### Added
- **Mouse-wheel zoom**: a whole-factor ladder (fractional zoom would break
  the pixel grid) — two steps in, one step out beyond the default. Near the
  barricade line the camera auto-tightens a step so the world's true edge
  can never scroll into view. Rain coverage and sniper spawn distances scale
  with the view.
- **Anti-banding film**: a 1/255-alpha noise overlay that breaks the day
  cycle's full-screen 8-bit tint steps into imperceptible per-pixel grain
  (the user could SEE the screen click one brightness step every couple of
  seconds).
- **Multi-strike lightning**: bursts of 1/2/3 strikes, each with its own
  flash intensity and its own rolling thunder.
- **Clip audit in the art pipeline**: generation now FAILS if any sprite has
  opaque pixels on its canvas border (grid modules exempt). Fixed everything
  it caught: tv stand (the user's screenshot), couch, dumpster, racks,
  crates, cylinders, single tire, fallen pillar, roof vent/hatch, bottle,
  paper, all barricades, bodies.

### Changed
- **Vehicles, actually complete**: the raked windshield/trunk ramps left
  ladder gaps in the roof plane (profile jumps of 2px per column between
  strokes) — the real "missing front/back". Ramps now bridge every step.
- **Barrels are 3D**: elliptical top face, walls hanging off the ellipse's
  curve, hoops that follow the curvature — no more flat front-view drums.
- **The barricade line is lattice fencing** (the style the user pointed at):
  dense diagonal-mesh panels as the dominant piece, concrete jerseys demoted
  to accents, tighter runs, smaller gaps. Roads can no longer generate
  parallel along the ring (outermost road span pulled well inside).
- **Footsteps rebuilt per surface with distinct recipes**: crisp concrete
  tick, low asphalt thud, hollow two-tone wood knock, slow grass brush,
  grainy dirt crunch — and everything quieter (-18 dB, -24 crouched/prone).
- **Rain bed rebuilt**: the old one added ~176 random pops per second
  (heard as crackle/"messed up") and looped audibly every 2 s. Now a pure
  doubly-lowpassed 8 s wash, much quieter (-46..-30 dB), with a slow
  non-loop-aligned drift so nothing repeats perceptibly.
- **Car alarm de-clicked**: every pulse gets a real attack/release ramp
  (hard gating read as static).
- **Splash → menu is one continuous dip to black** (fade out, fade in) —
  the hard cut into the fully-formed menu read as a glitch.
- **Boxes belong to industry**: crates/stacks/pallets only spawn around
  warehouses and their yards, never in the open street.

## [0.6.8] — 2026-08-01

The sound update: the district found its voice — and its studio card.

### Added
- **SapphireSignal splash screen**: the sapphire wakes, broadcasts signal
  rings with a sonar ping, and the first beam sweeps across to reveal
  "sapphire signal" in the game font. Skippable with any input; harness runs
  bypass it. The game now boots into it before the menu.
- **Main menu music**: a synthesized dark-ambient theme in A minor — detuned
  low drone, slow pad swells, a lonely echoing motif, a breath of wind —
  rendered once on a background thread (11 kHz lo-fi by design), looping
  seamlessly, fading out under the deploy screen.
- **Per-surface footsteps**: concrete, asphalt, hollow hardwood, brushed
  grass, muffled dirt — resolved from the tile under the raider each plant
  frame, with pitch variation, quieter when crouched, a slow drag when prone.
- **Thunder**: every lightning strike rolls thunder in after a random
  0.4–1.4 s distance delay (two synthesized rolls, subtle).
- **Rain bed**: a soft looping patter that rises and falls with rain density.
- **Car alarms**: ~half of the INTACT vehicles are armed. Come within reach
  and a short two-tone alarm fires from the car itself (positional audio)
  while its baked light pixels flash amber for 3 seconds — once per car,
  re-armed only when the raider dies and re-enters. Broken-into cars never
  alarm; they were stripped long ago.

### Fixed
- **The dotted vehicle lattice**: the roof plane's 2:1 strokes left a
  checkerboard of transparent holes that the outliner rimmed into dots —
  the "missing parts" look. Both rounding rows now fill; vehicles are solid.
- **Hidden vehicle ends close properly**: a 2px body wrap with a bumper hint
  and a light sliver, so no car ever ends in a flat cutoff.
- **Broken-into rework**: no more shattered-glass field across the roof —
  a door hanging open, one flat tire, dark side windows with a couple of
  glints, rust. Reads as an event, not noise.

## [0.6.7] — 2026-08-01

### Changed
- **The barricade line reads as one barrier**: each stretch repeats a single
  dominant jersey design (cracked variants as wear), fences demoted to
  occasional accents, ~10% knocked visibly askew (new baked angled art), some
  flat, clusters-then-gaps spacing, and every piece jittered off the line.
- **The buffer past the line is bare dead district**: no forests, and roads
  dead-end under the breach wreckage. Rubble, dead snags, litter, and the
  fallen are all that's out there. All woods — treeline fringe, forests,
  groves — live INSIDE the map (fringe growth is clamped at the ring).
- **Biome blending**: new grass-creep transition tiles wherever concrete
  touches woodland; the (previously unused) dirt blends wired up for path
  edges; groves have a 5-cell minimum and lone trees grow small organic
  pockets with blended rims — no more single green tiles or hard seams.
- **Fallen raiders are character-sized**: bodies now draw through the same
  lying-figure geometry as the player's prone sheet (which also got true
  standing proportions — wider torso, full-size head, thicker limbs,
  most noticeably on diagonals).

## [0.6.6] — 2026-08-01

### Added
- **Prone** on Z (rebindable): a full 8-direction crawl sheet (pack on the
  back, boot soles when facing away, per-direction head orientation, 6-frame
  crawl cycle). Slower than crouch (0.32x vs 0.55x); Z toggles, and any crouch
  input stands you back up out of prone. Covered by the smoke test.

### Changed
- The door prompt ("press f to open/close") floats pinned above the door
  itself instead of sitting at the bottom of the screen.

## [0.6.5] — 2026-08-01

The barricade update: the map got honest edges, the deploy got smooth, and the
roadmap got bigger.

### Added
- **The barricade line**: a randomized ring of concrete jersey barriers and
  metal fences (intact / cracked / bent / knocked flat, with slip-through gaps
  and wreckage where roads breach it) now marks the playable edge. The world
  visibly continues beyond it — but crossing the line starts the sniper
  warning, and the fire escalates with depth (faster, more accurate) so the
  buffer cannot be outrun. **The camera never clamps anymore** — it stays
  welded to the character everywhere; the old edge camera-shift is gone,
  along with the playable area shrinking to a tighter district.
- **Fallen raiders** past the barricades: sparse randomized bodies (jacket
  colors, hats, beards, packs, poses) where the sniper left them.
- **Door prompts**: "press f to open" / "press f to close" appears when
  standing right at a door (shows the current interact bind).
- Roadmap additions (user direction): **Tarkov-style loot** (grid inventory,
  item footprints, searchable containers) and **character doll gear slots**
  land in M4; **quests** become M6 (v1.1); **a second map** becomes M7 (v1.2).
  **Machines are cut** — every enemy will be human AI with guns — and
  **rarity color tiers are cut** (Tarkov loot doesn't have them). README
  rewritten to match reality.

### Changed
- **Deploy is dip-free**: world building is time-budgeted per frame (~2.4 ms),
  the post-build spawn/environment/UI tail is spread over frames, textures
  prewarm behind the cover, a warm camera pre-bakes the spawn area, and light
  shaders compile covered. Worst case is now a single unavoidable frame at the
  menu→game scene swap; the build itself holds refresh rate.
- **Weather can't jump anymore**: storm darkening fades over ~45 s with
  easing, decoupled from rain density.
- **Deep night is much darker** (flashlight and lamp energy raised to match);
  street lamp glow reads strong in the dark.
- Vehicles: **real end faces** — 5px-deep caps with bumper band, head lights +
  grille or tail lights + trunk seam, wrapped corner — and pickup cargo is
  placed strictly inside the measured bed (a box could overlap the cab).
- The flashlight toggle is an actual dry **click** (impulse + tiny ping), not
  a musical blip.
- The main menu builds its changelog rows lazily (a few hundred labels made
  the menu heavy to tear down on deploy).

### Fixed
- Environment could process for a few frames before its async setup finished
  (null gradient errors in headless runs).
- The smoke test's sniper check used a lambda-captured bool that GDScript
  copies by value — it now uses reference capture and passes for the right
  reason.

## [0.6.4] — 2026-08-01

### Fixed
- **Blurry/shimmering walk** (worst on diagonals): the camera snapped to the
  screen-pixel grid but the character's sprite rendered at arbitrary
  sub-pixel offsets between grid points, and the engine's
  `snap_2d_transforms_to_pixel` was rounding transforms on its own terms at
  half-pixel positions. Now the player's TRUE position stays continuous (no
  speed distortion), but the rendered sprite+shadow park on the same
  screen-pixel grid as the camera each frame, and the camera is defined off
  that snapped point — the character-to-camera offset is constant, so the
  raider is pixel-welded to the screen and the world scrolls on one coherent
  grid. Engine auto-snap is OFF: every placement is explicit (static props on
  whole world pixels, movers on the screen-pixel grid).

## [0.6.3] — 2026-08-01

The transit update: the district got a name, real edges, real doors, real rain —
and the first damage in the game.

### Added
- **320x320 map** (4x the area) named **"transit"**. Every deploy generates a
  fresh district from a seed; `--seed=<text>` pins a layout for testing. All
  builder randomness now flows through the seeded rng (`Array.shuffle()` had
  silently broken determinism).
- **Walkable map edge**: the border collision hugs the true iso-diamond edge
  (tips chamfered for the camera), and the camera clamps to an inset diamond —
  the void outside the tiles can never appear on screen.
- **Edge sniper**: near the boundary a centered warning appears ("turn back or
  you will get sniped"); after 3 seconds, tracer rounds come in from off-screen.
  Three hits kill: hurt flash per hit, death fade, respawn at the spawn
  crossroads. First damage/health/death systems in the game (routed through
  Authority).
- **Interactive doors**: closed by default, flush in the wall plane (no more
  leaf clipping through walls). Walk up and press F to swing them open or shut
  (4-frame animation, synthesized thunk, collision while closed).
- **Flashlight** on E: a cone of light snapped to the 8 facings. Deep night is
  now actually dark, so it matters.
- **Street lamps live and die**: fewer lamps overall, under half of them work.
  Working lamps glow and cast a real light pool at night with per-lamp
  randomized flicker and dropouts; the rest are bent or smashed.
- **World-anchored rain**: each drop falls to a real ground point, splashes
  there (4-frame splash that STAYS in the world), and never lands inside a
  roofed building. Drops and splashes are the puddles' blue (3c5e8b).
- **Interior greenery**: 26 large woods + ~90 small groves inside the map, plus
  ~240 lone trees breaking through the concrete on their own green pockets.
- **Trees rebuilt**: canopy always overlaps the trunk by construction (tall
  pines used to float), new leafy oak kind, better dead snags with twig forks.
- **Sticks and litter**: fallen branches in the woods; cans/bottles/paper
  around broken-into vehicles.
- **Vehicles v2**: wider bodies (12px roof plane), a visible end cap with head
  or tail lights, roof glass that shows the facing, all four lane headings
  pre-baked, and broken-into variants (shattered glass, rust, dents, sprung
  door). Road cars sit in correct lanes; yard cars face their buildings.
- Harness: `--perf` (frame pacing probe), `--probe-world` (content census),
  `--seed=`, `--flashlight`; smoke now covers doors and the edge sniper.

### Changed
- **Native-resolution rendering** (`canvas_items` stretch): the camera snaps to
  screen pixels instead of world pixels. At 2x scale, walking at 120 px/s is
  exactly one screen pixel per frame at 240 Hz — the "smeary / looks like lower
  fps" walk is gone. Art stays pixel-perfect; props sit on whole world pixels.
- **The deploy hitch is gone**: the world builds as a coroutine across frames
  behind an animated "deploying to transit..." screen, and every texture is
  pre-warmed during it.
- Day is 20 minutes (was 8); deep night is much darker.
- Rain spells last 2.5–5 minutes with slow ramps; lightning is a longer
  double-strike, stronger at night.
- One floor look per building (single wood tone per house, single clean screed
  per warehouse) — interiors were a per-cell patchwork. Screed lost its baked
  oil blob (it repeated like wallpaper), wood grain is subtler.
- Road center dashes on BOTH road directions with a 16px period that
  tessellates seamlessly (was one direction, 20px, phase-broken at seams).
- Ground speckle reduced ~35% on all outdoor tiles (forest floor most —
  it shimmered when walking back and forth).
- Roof north/west edges are a clean flush 3px closure (the old 10px speckled
  eave read as a rippling mesh hanging off half the roof).
- Fewer street lamps (every 14–22 tiles), FPS counter updates 5x/second from
  its own frame window, entrances (inside and out) always spawn clear.

### Fixed
- **Instant day-to-night snap**: the tint gradient's endpoint was never set
  (index bug), so late evening lerped toward pure white and jump-cut to night
  at the wrap. The gradient is now one continuous loop.
- Crate stacks could paste their top box above the sprite canvas, clipping it
  flat. Sprites now auto-crop to content.
- The character's left arm had no separating seam and blended into the torso;
  both arms now read separately (symmetric), on all sheets.
- Rain splashes rode the camera (they were screen-space particles).
- Couch (or any furniture/stock) could block a building entrance.
- Non-deterministic world layout across runs with the same seed.

## [0.6.2] — 2026-07-31

The district update: the world got 10x bigger and came alive.

### Added
- **160x160 map** (was 48x48): a full district with a road network, dirt
  roads wandering into forests, and ~12 randomized buildings (houses and
  warehouses, random sizes/styles/damage/doors) with yards where they fit.
- **The map never visibly ends**: the outer band is deep impassable forest and
  the camera is limited well inside it — no void, no floating square.
- **Forests** of generated pines and dead trees; forest-floor terrain.
- **Street lights** along the roads.
- **Vehicles that read as vehicles**: side-profile cars and pickups with real
  silhouettes, windows, wheel arches and lights; pickups carry bed cargo.
  Parked in yards and abandoned along roads.
- **Doors**: every building has an open door leaf (wood for houses, metal for
  warehouses) beside its doorway.
- **Day/night cycle** (subtle palette tint, 8-minute day) and **weather**:
  random rain spells with visible raindrop ground impacts, occasional subtle
  lightning, and puddles that form while it rains and dry out afterwards.
- **Deploying screen**: entering a raid shows a brief transition while the
  district builds — replaces the frame dip on scene change.

### Fixed
- House furnishing: the bookshelf/cabinet could silently vanish when two
  pieces rolled the same wall slot; both always place now. Industrial barrels
  no longer spawn inside houses.

### Changed
- Warehouse floors are smooth gray concrete (the green screed looked wrong).
- Ambient junk is rarer and clusters around buildings instead of everywhere.
## [0.6.1] — 2026-07-31

> Versioning from here on: patch bumps (0.6.x) for polish and fix batches;
> the minor only moves when a MILESTONE lands (0.7 gunplay, 0.8 enemies,
> 0.9 the raid loop). 1.0 = the complete v1 game from the design doc.

### Added
- Loading yard south of the warehouse: asphalt pad with faded stall lines,
  pickup trucks backed in (random count/colors/stalls; boxes in the beds),
  and stray stock scattered around — all randomized.
- Crouch mode option next to the crouch keybind: hold or toggle.
- Silver gleam that sweeps across the title every few seconds.

### Changed
- Warehouse floor is a distinct green sealed screed (dark asphalt read as
  "same as the street").
- Racks and crate stacks are variant families with messy, jostled, per-box
  randomized loads — no two look alike, nothing stacks perfectly.
- Racks are shorter than the walls (top boxes no longer poke past the cap).
- Roof corner caps are post-sized and carry the fascia/rim lines through the
  corners.
- The gold in the vault backdrop now falls down the light shaft (was rising).
- Menu buttons are exactly centered (and stay centered as buttons are added);
  the tagline is smaller and no longer bobs with the title.
## [0.6.0] — 2026-07-31

### Added
- **Keybinds screen** (settings → keybinds): every action rebindable — click a
  key, press the new one; reset to defaults; persisted. Actions: movement
  (WASD), interact (F), crouch (Ctrl), reload (R), flashlight (E), weapon
  slots (1/2/3). Reload/flashlight/interact/slots activate in later milestones.
- **Crouch** (hold Ctrl): dedicated crouched sprite sheet in all 8 directions,
  55% movement speed, slower step cycle.
- **Real interiors**: the house has wooden plank floors and furniture (couch
  facing the TV, cabinet, bookshelf, table, chairs); the warehouse has a dark
  screed floor, shelving racks along the back wall and randomized stacked
  stock. Interior placement is randomized, not hand-placed.
- Broken roof sections (exposed joists) over the warehouse's ruined corner.

### Changed
- Buildings are different sizes now (small house, big warehouse) and both
  doors are on camera-visible sides.
- All roofs are black (two subtle shades); the purple-ish tone is gone.
- Main menu: bigger title with the tagline baked in and outlined (it was
  unreadable over bright scenes); the neon scrapyard sign is smaller.
- VSync ON greys out the FPS cap slider and shows the display refresh instead.
- Settings window has a fixed, slightly wider size (no more resizing when
  value text changes).
## [0.5.6] — 2026-07-31

### Fixed
- Wall symmetry for good: the coping-flip experiment is removed — every wall
  uses the identical cap, all four corners match (the flipped caps were
  overlapping their own faces and colliding at the top corner).
- Wall caps slimmed to a flush 3px top — the wide cap read as a fat lid on a
  thin wall. The ROOF is what overhangs now: new eave modules extend the roof
  plane over the wall tops on the far sides, and every post gets a
  roof-colored cap so corners and door jambs read identical under the roof.
- The changelog button was invisible on dark backdrops (flat + dim) — it is a
  normal themed button again.

### Changed
- Buttons restyled once more: near-black translucent fill with a light border
  and bright text — contrast by brightness instead of hue, so they read on
  the gold vault, the purple cave and the blue-gray scenes alike.
## [0.5.5] — 2026-07-31

### Changed
- Buttons are deep burgundy now — clearly visible over every menu backdrop
  (the old gray-blue blended into the darker scenes).
- The changelog link is a dim flat footer link, matching the version label.
- In-game changelog entries expanded with more detail per version.

## [0.5.4] — 2026-07-31

### Added
- In-game changelog viewer on the main menu (bottom-right, above the version):
  every version since the first build, summarized in plain language.

### Fixed
- Returning to the menu from a raid caused a 1–2 frame hitch (backdrop images
  re-decoding + particle pre-simulation). Backdrops are now preloaded for the
  process lifetime and only the first scene pre-warms its particles.

## [0.5.3] — 2026-07-31

### Changed
- Roof rebuilt as modular pieces placed by explicit formula: one tile per
  interior cell, fascia modules on south/east eaves, lit rims on north/west.
- Wall coping on north/west walls now extends under the roof (mirrored
  variants), and corner posts are exactly wall height so their caps close the
  fascia line at the corners instead of poking through the roof.

## [0.5.2] — 2026-07-31

### Fixed
- Roofs sit flush on the walls (the slab was overhanging ~8px past them);
  corners line up with the wall corners.
- The interior reveal triggers only when the player is actually INSIDE the
  walls — standing next to a building no longer hides its roof.
- The back-view neck for good: no exposed skin sliver from behind at all —
  hair tapers straight into the collar, mirroring the front. Verified with an
  in-game capture, not just the sprite sheet.

### Changed
- The two buildings are different materials now: red brick vs. gray weathered
  masonry — and their roofs are two different near-blacks (charcoal blue vs.
  dark umber). More per-thing variation, per the standing direction.

## [0.5.1] — 2026-07-31

### Added
- First synthesized audio: soft UI hover/press blips, generated in code at
  startup (no audio files, per the project's rules) and auto-wired to every
  button in the game.

### Changed
- Main menu buttons: no more panel box around them, slightly translucent, and
  all identical — DEPLOY's orange accent and the loud focus outline are gone.
- Character sprite: arms are now truly symmetric (the torso is an even width,
  so arm columns are placed off the body edges, not the center), and the
  beanie is replaced with brown hair with a proper fringe.
- Buildings have exactly one doorway each.

### Fixed
- Walls no longer turn see-through when inside a building — walls always stay
  fully visible; only the roof fades.
- Roof rebuilt for the thin-wall system: one generated slab per building that
  caps the walls exactly (fascia trim, baked vents), replacing the
  tile-assembled roof and its corner glitches for good.

## [0.5.0] — 2026-07-31

### Fixed
- **The blurry UI text, for real this time.** The bitmap font had silently
  failed to import once (its atlas was briefly missing during regeneration),
  and the engine cached the failure and fell back to its default vector font —
  which is what was blurry. The import is fixed and font subpixel positioning
  is disabled, so text now renders pixel-perfect. Verified with OS-level
  screenshots of the actual screen output.
- Roof/wall corner misalignment: roofs covered the wall tiles and fought them
  in draw order (the south corner's roof vanished entirely). Roofs now cover
  exactly the interior, tucked inside the parapet.
- Interior reveal leaves no ghost tint — the roof fades fully invisible.

### Changed
- **Buildings are real thin-walled architecture now**, not rows of full-tile
  blocks: slim brick wall segments along tile edges, corner and door-frame
  posts, varied window sizes, jagged broken sections. Interiors show proper
  inner wall faces, dollhouse-style.
- **New UI font**: lowercase-only proportional pixel type (capitals render as
  lowercase by design), used everywhere including the wordmark.
- When inside a building, the camera-facing walls also fade to 30% so nothing
  in the interior hides behind them.

### Added
- **Four rotating main-menu backdrops** (crossfade every 20 s), each alive:
  a treasure-vault hoard with rising gold sparkles, a neon scrapyard with a
  flickering sign and drifting smog, a lamplit safehouse cross-section, and a
  cliff-edge overlook with drifting clouds over a dead city. The gameplay map
  is no longer the menu background.

## [0.4.0] — 2026-07-31

The presentation update.

### Added
- **Main menu**: the live game world as a dynamic background (slow drifting
  camera, a raider walking his patrol, dust motes, vignette) with an animated
  SPOILS wordmark, DEPLOY / SETTINGS / QUIT, and full keyboard focus support.
- **Bitmap pixel font**, generated by the pipeline like everything else, used
  across all UI — text is now crisp at every screen scale.
- **Roofs + interior reveal**: buildings have tar roofs with vents and hatches;
  step inside and the roof fades away so you can see the interior, fades back
  when you leave.
- **Procedural prop variation**: every prop family is a parameterized generator
  — barrels (4 styles, heights, dents, standing/fallen), crates (3 sizes, wood
  tones, damage, stencils), gas cylinders (3 colors, standing/toppled), tire
  stacks and singles, pallets (intact/broken/stacked), dumpsters (closed/open),
  rubble in four sizes, pillars (tall/snapped/fallen). Collision shapes are
  computed per variant and shipped in the art manifest.
- **Resolution setting** (windowed sizes + desktop), joining display mode,
  graphics quality, FPS cap, VSync and the FPS counter.

### Changed
- Brick walls re-textured: dithered mortar and sparse staggered joints — brick
  reads as texture, not grid. Windows now vary in size and placement, including
  boarded-up ones.
- Menu copy re-flavored for the raid fantasy (RAID PAUSED / RESUME /
  QUIT TO DESKTOP).
- FPS counter: smaller, green, top-right, pixel font.
- Player sprite: arms are now symmetric — the darker right arm (and its
  side-swap on mirrored directions) is gone.

### Fixed
- Blurry UI text: tiny vector-font rendering replaced by the bitmap font.

## [0.3.0] — 2026-07-31

### Added
- Pause menu on **Esc** with Back / Settings / Quit.
- Settings panel: display mode (borderless fullscreen or windowed), graphics
  quality (will drive lighting & effects in upcoming milestones), FPS cap
  slider (0–240, 0 = uncapped), VSync toggle, and an on-screen FPS counter.
- Settings persist to disk and re-apply on launch.
- Project README, banner, and this changelog.

### Changed
- Esc no longer quits the game directly — quitting now lives in the menu.

### Fixed
- Fullscreen letterboxing: the view now expands to fill the entire screen at
  the largest whole-number pixel scale — no black frame, on any resolution,
  with pixels staying perfectly crisp.

## [0.2.1] — 2026-07-31

### Fixed
- **High-refresh judder:** movement and camera now update every rendered frame
  instead of at the 60 Hz physics tick. On high-refresh monitors (e.g. 240 Hz)
  the old behavior read as constant stutter.
- **Motion blur/shimmer while walking:** the camera is hard-locked to whole
  pixels every frame, so the low-res screen never resamples mid-scroll.

### Changed
- Game now launches fullscreen (borderless) by default, integer-scaled.

## [0.2.0] — 2026-07-31

First playtest feedback pass.

### Changed
- **Ground rebuilt:** removed all per-tile edge lines and repeating blotches.
  The ground now reads as one continuous surface — six low-contrast concrete
  variants, rare one-off cracks/stains/moss, and dirt patches that blend out
  at their borders instead of ending in hard diamond edges.
- **Buildings rebuilt in brick:** two brick styles with mortar courses and a
  concrete coping cap. Wall pieces are neighbor-aware, so wall runs render as
  continuous walls with framed windows and proper corners — not rows of cubes.
- **Walk animation:** 6-frame cycle (was 4) at a higher frame rate, with real
  leg scissor, foot lifts, and arm swing.

### Added
- New props with deliberately distinct silhouettes: flat ammo crate, steel
  gas cylinder, tire stack, wooden pallet, and a dumpster. Rubble piles now
  carry brick chunks so debris ties into the buildings.

### Removed
- Recolored duplicate props (olive barrel, military crate clone).

## [0.1.1] — 2026-07-31

### Fixed
- `Play.bat` failed to launch (Windows batch needs ASCII + CRLF line endings,
  and the project path argument was being mangled). Batch line endings are now
  enforced via `.gitattributes`.

## [0.1.0] — 2026-07-31

Milestone 1: the walkable world. First playtest build.

### Added
- Godot 4.7 project scaffold, 640×360 pixel-perfect rendering, isometric
  Y-sorted world.
- Deterministic art pipeline (`tools/gen_art.py`): every asset generated from
  the 46-color Apollo palette — floor tiles, wall blocks, props, drop shadow,
  and an 8-direction player sprite sheet.
- 48×48-tile ruined city block: roads with worn lane paint, two building
  shells, scattered props, rubble perimeter.
- Player: 8-direction WASD/arrow movement with collision, follow camera.
- Self-verification harness: headless smoke test (`--smoke`) and screenshot
  capture (`--shot=<name>`).
- `Play.bat` one-click launcher.


