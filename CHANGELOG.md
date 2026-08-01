# Changelog

All notable changes to SPOILS are documented here. Versions follow a simple
`0.minor.patch` scheme while the game is pre-release.

## [0.6.28] — 2026-08-01

### Fixed
- **The prompt is the permission** (user report: "im a bit further back
  and can still interact"). Interaction ranges lived in two places and
  disagreed — the player reached doors at 44 px and cars at 46 px while
  the prompt only appeared at 30 px and 42 px, so F answered things the
  game never offered. There is now ONE source of truth: main.gd's prompt
  logic picks the target each frame into `player.prompt_target`, and F
  acts on that and nothing else. **Every future interactable inherits
  the rule for free** by going through the prompt — which is the point,
  since the toll warden, the freight and the tunnel ladders are all
  coming.
- Smoke now proves it end to end instead of calling `toggle()` behind
  the game's back: F must open the door while standing at it, and must
  do nothing at all from across the street.

## [0.6.27] — 2026-08-01

### Added
- **EXTRACTION — you can leave the raid.** New `Extraction` manager holds
  every exit on the map, watches the raider's distance to each, runs the
  green "extracting in N" counter, and plays the leaving sequence.
  Exits can be automatic (stand in it) or armed by something else — the
  toll gate and the freight will arm theirs.
- **Extract 1: THE LIFT** (user design). The builder carves a clearing in
  the open block, stamps it flat, paints a worn marker on the ground,
  runs a dirt track to it from the nearest road, and scatters waiting-
  room junk around the rim. A beacon sits in the middle throwing green
  smoke (soft fog puffs, tinted and billowing) over an additive ground
  wash that reads at noon as well as midnight. Walk in, it counts down
  from five on its own, then a **helicopter** flies in over the treeline
  with its rotor turning, hangs a rope, and lifts you out of frame.
  New art: a 3-frame helicopter (lit fuselage, glass nose, tail boom and
  fin, skids, a rotor disc that sweeps across the frames) and the LZ
  ground marker.
- **The debrief: "successfully extracted"** (user spec). How you got out,
  time survived, xp earned, kill count and raiders killed — plus a kill
  log listing the minute and the BONE for each one. The haul column is
  stubbed until the stash and grid inventory land in M4. New `Raid`
  autoload keeps the ledger (start time, xp, kills with timestamp, bone
  and whether it was a real raider), so the screen is real the day M3's
  strays arrive. Harness: `--extract=<method>` opens the debrief with a
  sample ledger.

### Changed
- LORE.md §7c and DESIGN.md §8.4 now carry the picked exits as canon —
  the toll gate (a warden running the crossing as a business), the night
  freight, and the lift — with the drain, outfall and fog window kept
  for later. CLAUDE.md gained an IN FLIGHT section tracking all three.

## [0.6.26] — 2026-08-01

### Changed
- **The district map is DRAWN, not sampled** (user: "make it all vector
  drawn... maps with pixel dont really look too good"). The builder now
  exports the plan itself — `_map_vectors()`: road lines, block rects,
  building footprints with kind and storey count, the woods bucketed
  into coarse groves, the rail row, plaza and apron. The map screen
  strokes and fills that with antialiased primitives: roads as edged
  strokes, woods as overlapping soft circles (autumn muted, not
  bleeding red), buildings as solid footprints with a lit north edge
  and a soft core when they have an upstairs, the rail as a line with
  ties, and the wire as a dashed red ring around the playable district.
- **No boxes anywhere** (user: "remove all of the squares"): POI names
  are drawn with a dark halo instead of a label chip, and city blocks
  now sit a hair off the ground colour instead of reading as panels.
  Home is a thin amber ring around the safehouse rather than a bright
  slab — the slab was swallowing the player marker standing on it.
- **"me" is unmissable** (user ask): a pulsing translucent disc, a ring,
  four cross ticks, a dark-backed bright core, and the label riding
  above it — over roads, woods or rooftops.
- **Fills the window and zooms smoothly**: the map opens at the scale
  that fits the whole playable district and the wheel now zooms
  continuously (1.25×/step, cursor-anchored) — the old integer pixel
  ladder existed only because the map was a bitmap.
- Perf: the district is heavy to draw but only changes when you pan or
  zoom, so it lives on its own layer and the markers redraw alone each
  frame. 240 avg, worst 5.34 ms, ~5.3k nodes. SMOKE PASS.

## [0.6.25] — 2026-08-01

### Fixed
- **Windows own the screen** (user: "once a window is open i want only
  that window to be functional"). New `Ui` autoload tracks open windows;
  gameplay POLLS input every frame, so consuming events was never
  enough — the player and the car now ask `Ui.blocks_gameplay()` and
  stop reading input entirely while a window is up. Consequences the
  user reported, all fixed: **ESC closes the map** instead of opening
  the pause menu behind it, **the mouse wheel zooms the map OR the
  world, never both at once**, and no window can open behind another.
  Dying with the map open no longer wedges it open.
- **Every window says how to leave it**: "press m to close" now sits on
  the world view as well as the district view (there was no way to know
  how to get out of the cordon screen).

### Changed
- **LORE.md rewritten at the top** (user asked, after seeing the word
  "machines"): the hard rules are now the first thing in the document,
  and rule 1 is unmissable — **every enemy is a human being; there are
  no robots, drones, monsters or infected, ever.** Where the mills
  chapter says "machines" it means industrial plant (looms, presses,
  furnaces) and now says so in as many words. Added: the fixed-district
  rule, transit written down as the real place it now is (which POI
  sits where, plus the safehouse), the den's build-up loop — the wings
  you restore and what each unlocks — and an extraction chapter with
  six exit pitches for the user to pick from. DESIGN.md's "dead overrun
  district" line reworded: nothing overran this city.

## [0.6.24] — 2026-08-01

### Changed
- **EIGHT-DIRECTION VEHICLES** (user request, sample approved first): the
  four angles a (2,1) sheet cannot draw now exist for every car and
  pickup — `make_vehicle_flank` (screen-horizontal heading: the flank
  faces the camera dead-on, the roof lies as a flat band straight above
  it, both ends go edge-on) and `make_vehicle_head` (screen-vertical
  heading: both flanks go edge-on, so the view is FOUR solid bands —
  end face, hood or trunk, raked glass, roof — drawn far-to-near with
  skirt fills; a per-station loop ladders into stripes, which is what
  the first cut did). `_veh_profile` gives every view the same
  length-agnostic silhouette, so a car keeps its shape at any heading.
  Registered as `vehicle_{n,s,e,w}_i` beside the existing
  `vehicle_{nw,ne,se,sw}_i`, with door-open frames, light coordinates
  and per-facing colliders — `_base_variant_name()` picks them up with
  no special cases.
- **Wider vehicles** (user approved): ROOF_DEPTH 12 → 18. The old cars
  were narrower than real cars — invisible in the diagonal views, but
  the head-on view would have read as a plank. Every vehicle in the
  district is now built on the true body width, which also makes them
  sit more solidly on the road.
- **New driving controls** (user call): **get in and the engine starts
  itself; get out and it shuts off** — the engine action is gone from
  the input map, the settings binds and the keybinds panel. **WASD
  drives** across all eight headings (cursor-follow removed), keeping
  the steering inertia from v0.6.23 — the car carves toward your input
  and turns tighten as you slow — plus iso squash on the vertical so a
  car crossing north-south covers ground at the rate the tiles imply.
  **E** headlights, **F** in and out. Controls card rewritten to match.
- Smoke harness drives via `auto_drive` now (headless sends no input)
  and asserts both halves of the new rule: the engine must be running
  after entry and silent after stepping out.

Perf: 240 avg, worst 4.72 ms, ~5.3k nodes. SMOKE PASS.

## [0.6.23] — 2026-08-01

### Changed
- **THE MAP, rebuilt** (user: "make it something how a real triple a
  senior dev would make it"): near-fullscreen window; the district view
  opens at the largest whole zoom that fits the WHOLE playable district,
  centered — centering DEFERS to the first draw (layout reports zero
  sizes at open time; that panned the old first look into nowhere), and
  the UI space is measured, never assumed 640×360 (expand-aspect makes
  it 840×540 on the user's display). POI names draw ON the map with
  backing chips (crowded labels yield), a pulsing "me" marker with its
  label tracks the player in REALTIME, live car dots, drag-pan /
  cursor-anchored zoom / tooltips kept, clock+weather bar, control
  hints. World view: the transit tile is a REAL TextureButton showing a
  live crop of the actual baked district — the old unhandled-input hit
  test was swallowed by the panel ("i clicked on transit and nothing
  happens") — with the sealed tiles on a self-centering board.
- **Map bake**: every planted tree drawn color-true (the autumn grove
  reads rust on the map), the barricade ring line, a bright safehouse
  outline. Map-select screen: bigger tiles, district briefing + POI
  list in the info column.
- **Second stories, readable** (user: furniture "floating because
  theres no second floor"): upper floors are WOOD everywhere (the
  school's screed-over-screed vanished into the night), every upper
  slab gets a LIT edge lip along its open borders, and a quota
  guarantees ≥4 two-story houses — the fixed seed had rolled ZERO
  (45% dice across ~15 homes; with one permanent map that would have
  been forever). The school stood nearly empty since v0.6.19: its desks
  were the only furniture gated on `_occupied`, which the shell sets
  for its whole interior before furnishing.
- **The classroom** (user request): chalkboard with chalk ghosts on the
  front wall, a teacher's desk, desk+chair pairs in rows facing the
  board, shelves at the back. Handled as quiet environmental
  storytelling — a place evacuated six years ago.
- **Safehouse yard**: a small parking pad off the ring (stall line, one
  never-alarmed car — it reads as YOURS), the fence ring thinned to
  every third cell, and power boxes never hang under a window anywhere
  (window positions are tracked at shell build now).
- **3D pass** (user: "make it all look visually 3d"): bushes rebuilt as
  lit lumpy masses — crowns with lit/shaded sides, dark under-skirt,
  sky-lit rim; benches rebuilt as boxes — grooved top face, front face,
  under-shadow, two-tone legs. (The catalog-wide 3D pass shipped in
  v0.6.9; these two were the stragglers. Circle anything else.)
- **Driving feel** (user: "add some sort of physics"): steering
  inertia — the car carves toward the cursor and turns tighten as you
  slow; facing swaps get hysteresis (no diagonal flicker); every real
  crash lands a soft synthesized body-thump (with cooldown) and
  full-speed crashes puff smoke off the impact point; the controls card
  lasts 12 s with amber KEYS distinct from dim descriptions.
- **The static at full speed** (user report): the engine bed's pitch
  was being micro-stepped 240×/s (zipper noise) and pitching the
  recording's hiss into earshot — pitch is slewed and capped now and
  the bed plays through a low-passed bus. Foliage also mutes its
  leaf-brush sounds while driving (a car crossing a bush line
  machine-gunned them into crackle).

### Fixed
- Dirt trails painted straight across sidewalks (the "overlapping road"
  screenshot) — sidewalks win over trails now.
- The center line's two half-tiles rolled independently, so ~8% of
  dashes were orphan halves sitting off the road's middle (user
  screenshot) — the halves live and die as a pair.

Perf: 240 avg, worst 4.48 ms day / 4.63 ms storm-night, ~5.3k nodes.
SMOKE PASS.

### Next (vehicles, deliberately staged)
- Sprites still swap between FOUR baked facings while motion is
  free-angle. The 8-direction sheets (nose within 45° of the cursor)
  need their own art round: ONE sample sedan sheet for user sign-off
  first, then the fleet — the end-face saga earned that process.

## [0.6.22] — 2026-08-01

### Changed
- **The fixed district** (user call: "i want everything on the map to be
  fixed... theres going to be quests telling you to goto specific POIs and
  do things there"): procedural rerolls are GONE. Every deploy builds the
  same canonical transit — `DISTRICT_SEED = "transit-01"` in
  world_builder.gd, picked by auditioning five candidate layouts (probes +
  map shots). transit-01 won on city logic: both town blocks north, the
  rail line running through the middle industrial belt
  (depot/scrapyard/trainyard), school and gallery in the south band,
  safehouse spawn south-center, autumn grove in the south-east corner.
  The deterministic generator + pinned seed ARE the map file; changing the
  seed is a deliberate map revision. Builder audited: zero unseeded
  randomness in the layout path. Per-raid variety stays weather/time (and
  later loot/AI). Harness `--seed` still overrides for tests.
- **Scrapyard warehouse** (user: shelves and boxes in the open, "i know
  there used to be one there"): the scrapyard block now plans its own
  GUARANTEED hall in its south half (rail-dodging fallback like the main
  warehouse), so the rack line out front reads as its overflow storage.
- **Walk-in bushes** (user: "as if the character model can literally fit
  inside of it and hide"): clumps 30-42 → 40-52 px, taller than the
  standing sprite; the PLAYER now fades to half-alpha alongside the bush
  while inside, so concealment is readable at a glance (foliage radius
  24→28). Sway rebuilt: a slow 4-beat whole-pixel rummage with per-bush
  phase — the old 6-frame toggle shivered, and in sync. The rustle plays
  at full step volume going in (softer leaving), with an anti-spam gap.
- **The gallery, grown up**: the smoker rebuilt at player scale (28×36
  frames, seated height ~30 px vs the 36 px standing character), benches
  lengthened and raised to match (four slats, taller backrest, bigger
  collider), and spray cans became a 4-variant family — different colors,
  counts, standing/tipped/crushed poses, dried spills — scattered 1-2 per
  graffiti wall plus loose strays. The two identical drops are gone.

### Fixed
- The editor's one real warning was real: safehouse-ring fence placement
  ran through a STANDALONE TERNARY (`_fence_piece(...) if cond else null`)
  — rewritten as honest conditionals. Three build steps
  (safehouse ring / gallery / school grounds) awaited functions that never
  yielded; they are now true time-budgeted coroutines. Intentional iso
  integer division no longer warns (project setting), so the Errors tab
  stays meaningful.

### Performance (audit pass, user request)
- Foliage manager rebuilt on packed arrays with cached static positions
  and an idle early-out (one distance check per idle bush per frame).
- Street-lamp night broadcast only fires when the level changes (it ran
  every frame, all day long).
- Car alarms early-out when nothing is flashing (was a per-frame group
  lookup + reflection get); edge guard, car alarms and the power box now
  cache textures instead of re-`load()`ing per shot/burst.
- Verified: 240 avg fps, worst frame 4.45 ms (day) / 6.25 ms (storm
  night), ~5.2k nodes. SMOKE PASS.

## [0.6.21] — 2026-08-01

### Changed
- **Big bushes** (user: "make them alot bigger please so the user can hide
  in there against enemies or something later"): 16-24 px clumps → 30-42 px
  chest-height mounds; rustle radius 17→24; still walk-through by design —
  they're concealment now, ready for M3's human enemies.
- **The autumn grove** (user: red leaves were falling off green trees): the
  forest block's east half turns — new autumn oak family (orange/red
  canopies), and leaf fall is color-true: autumn shedders drop the two new
  red leaf sprites, everything green drops only green. The comms relay
  clearing sits right against it.

## [0.6.20] — 2026-08-01

### Added
- **The safehouse**: every raid now starts inside the same squat house near
  the map's south edge — lattice-fence ring with a door-side gap, pillar
  "pylons" at the corners, a couch, a crate, and a spawn cell that can
  never be furniture-trapped (the roaming spawn once put the user behind
  a bookshelf). Placement is bulletproof: probe bands, then an exhaustive
  row-walk (one seed landed rail+courtyard+depot across every band and
  silently dumped the spawn into sniper country). On the map + POI dict.

### Changed
- **Free-angle driving** (user: "it can move around freely right?"): the
  car moves on the true cursor vector; the sprite snaps to the nearest of
  its four baked facings and the collision parallelogram swaps diagonals
  with it. Top speed 260→190 ("way too fast").
- **Collision pass** (user: walked through a bus, a broken car, trees,
  lamps): vehicles/buses/boxcars now carry parallelogram colliders
  ALIGNED to their (2,1) diagonal (the axis diamonds left nose and tail
  open — mirrored variants flip the poly too), pallets got a low diamond,
  tree trunks 3-3.5→5.5/4.0, lamp poles 2→3.5. Bushes stay walk-through
  on purpose — that's the rustle feature.
- **The truck door-flash** (user: "turns colours for a second when i click
  f"): the door-open frame's art seed included the door flag, so pickup
  bed cargo re-rolled for the swap. Seed unified — the door frame is the
  same vehicle down to its rust.
- **The warehouse always builds**: dirt trails no longer veto placement
  (the slab claims the ground), and a forced center-of-block fallback
  dodging the rail line guarantees the hall — racks/stock out in the open
  with no warehouse was the screenshotted bug.
- **Comms relay moved to the woods' edge** (user call): the compound now
  carves a clearing in a forest-block corner; the gallery keeps the open
  block.
- **Leaves everywhere they should be** (user: "half of all the
  bushes/trees"): 50% of ALL trees shed (was 25% of oaks), bushes shed
  too, pool 22→36, drip 0.22-0.55 s.
- **Fleet variety** (user: "3 green ones... two of the exact same truck"):
  steel-blue and tan palettes join, intact specs 3→5 (three pickup
  colors), broken indexes moved to _5/_6.
- **One centerline**: the half-tile pair drew on the OUTER edges — swapped
  to the shared boundary; roads show a single centered dash line again.
- **Stairs in room corners** (user call), and the ground-floor door is
  unusable from upstairs — it also shuts itself as you climb (you could
  walk out of the building mid-air).
- Perf: 240 avg, ~4.5 ms worst, ~5.0k nodes.

## [0.6.19] — 2026-08-01

### Added
- **The map (M)**: a big window; the FIRST open shows the world view — the
  cordon with transit clickable in the middle and three sealed districts
  under question marks — and clicking transit opens the district map: a
  1px-per-cell image baked from the same plans the terrain paints from
  (roads, walks, woods, rails, trails, buildings, machine marks), live
  player + car markers, drag-pan, wheel zoom (cursor-anchored), 0.5 s
  hover tooltips on every POI (both views), the in-game clock and current
  weather, a back button, and view memory (world only on the very first
  open). M closes it again.
- **Play → map select**: the menu's deploy button is now "play" — it opens
  the cordon map-select screen (transit with a painted preview + district
  blurb + deploy; locked maps blacked out under "?"), and deploy launches
  the raid from there.
- **The scrapyard** (new POI, its own block): rows of dead and driveable
  vehicles, two forklifts, ONE lattice-boom crane, industrial racks, junk.
- **The gallery** (new small POI): free-standing graffiti walls (three tag
  palettes, drips, shine ticks), spray cans, benches — and a SMOKER who
  sits there working a cigarette: 3-frame drag/exhale cycle with drifting
  smoke wisps.
- **Street extras**: vending machines and newspaper boxes on the walkways,
  roughly double the dumpsters.
- **Power boxes** on every house wall; exactly ONE per district hangs open
  with dangling wires and periodic spark bursts + glow (repair quest
  fodder). Keybinds panel lists m (map), q (start engine) and tab
  (inventory — future).

### Changed
- **Cursor-follow driving** (user: the wasd steering "seems off"): one left
  click and the car chases the cursor at full throttle, stepping its four
  baked headings toward it; click again and it rolls to idle. The in-car
  hint teaches exactly that. Engine start/doors/alarm all quieter (the
  standing rule now: every new sound ships quiet), and alarm flashers
  THROW light at night.
- **Bushes and leaves actually visible** (user: "not working"): bush
  trigger radius 14→17 with a continuous whole-pixel rustle the entire
  time you're inside (plus a half-second settle), and leaves now spawn
  from a refreshed NEAR-VIEW shedder list — the old code rolled one tree
  from the whole district and almost never hit the screen.
- **One thunder per flash** (user call): the 2-3 strike chains are gone —
  they also restarted the thunder player mid-clap, which was the "cut
  out". Rain a step quieter, thunder a hair louder.
- **Second stories are sealed**: the upper floor covers every cell — the
  stairwell hole showed the ground floor. The flashlight rides the
  32 px floor lift too (it sat "inside" the character upstairs).
- **Village trails**: narrow worn dirt paths connect the houses and the
  courtyard, pausing at roads/sidewalks/plazas and resuming on the far
  side, detouring around the compounds.
- **Clean walkways**: the broken sidewalk tiles lost their baked weed
  pixels (the "little green bits").
- **The yellow line sits on the road's true center**: the dash is two
  half-tiles sharing the middle boundary of the 4-cell road (it used to
  run down one cell, half a lane off).
- **Map smaller again**: ring inset 68→78, playable diamond ~100 cells.
- **The character**: +2 px taller in all stances (crouch included), same
  proportions in every direction; PRONE is properly bigger — real
  shoulder span lying N/S, thick diagonal silhouettes (they were sticks).
- **The den board reads like a board**: district names in tall near-black
  ink strokes with underlines, and every sheet hangs from a colored pin
  tack with a glint.
- **The splash breathes**: 3.4→5.2 s — flickers, rings and the beam sweep
  are all watchable now.
- **Perf** on the user's box: 240 avg fps day/dawn/night, worst ~4.5 ms,
  ~4.6k nodes.

## [0.6.18] — 2026-08-01

### Changed
- **The districts update.** The map shrank AGAIN (user: "way smaller, its
  still huge") — total grid 320→256, ring inset 68, playable diamond ~120
  cells (under half the old area) — and what's left is ZONED: the 3x3 road
  blocks are dealt out as a two-block **town**, two-block **forest**, the
  **warehouses**, the **school**, the **trainyard**, the **bus depot**, and
  an open block hosting the **comms relay**. Distinct places for the quests
  to point at, with stray trees/groves keeping the randomness.
- **Town**: houses packed around a paved **courtyard** — plaza pavers, dry
  fountain, overgrown planters, benches. Spawn is on the courtyard's lip.
- **Second stories** (user: "get some floors to it maybe, with stairs"):
  ~45% of town houses and the school get two-story shells (taller walls,
  stacked windows, a floor string course, transom over the door), interior
  wooden stairs with an F-prompt, and an upper room that exists ONLY while
  you're up there — floor sprites in a north-anchored container, furniture
  with true-position colliders and lifted sprites, player sprite+camera
  rise a whole 32 px together. You never see the floor you're not on.
- **New POIs**: the school (two-story hall, desk rows, playground with
  swings/slide/sandbox, flagpole, unreadable sign, gappy fence), the
  trainyard (a main rail line crossing the whole district with level
  crossings, ballast, sidings, boxcars — one livery burst open — and
  buffer stops), the bus depot (asphalt apron, a rank of buses with
  broken-into variants, shelters), and the comms relay (lattice mast,
  dish, hazard-striped equipment shed, fenced with a gap).
- **Driveable cars** (user request): every intact car starts F-enterable —
  door-swing frame + real door recording, seat, door closes. Q wakes the
  engine (real recording), W/S throttle/reverse, A/D step the four baked
  headings (reverse steering mirrored), E throws twin headlight cones,
  F steps out beside the door. A controls crash-course shows for a few
  seconds after entering. Quiet engine loop bed follows the throttle;
  entering an armed car disarms its alarm for good. Broken-into cars stay
  the props they were. Sounds: CC0 pack by ggbotnet (LICENSES.md).
- **Clean asphalt** (user: "i dont want any on the road"): the centerline,
  crosswalk, manhole and stall tiles lost their baked wear patches — the
  road family is smooth except cracks and potholes; broken-car litter now
  lands on the shoulder, never the lanes.
- **Sidewalks everywhere**: every road side gets its slab band full-length
  (evicting forest cells if needed) and grass blends are suppressed beside
  asphalt — grass never touches a road, intersections stay green-free.
- **Glass windows** (user: "make them see through"): every wall window is
  sky-blue panes with a diagonal sheen, interior shadow low, and a mullion
  cross — boarded variants keep their planks.
- **Quieter world**: scatter 380→210, coarser dead-spot lattice, lone
  trees 130→55, fewer bodies/buffer pieces/puddles ("a bit too many
  objects" — user).
- **Fog**: two big bank sprites join the wisps (baked sizes, never runtime
  scale), a 3.5 s breathe-in kills the spawn pop, and drift-before-dissolve
  doubled — no more appearing/disappearing churn (user call).
- **Longer music fades** (user call): menu in 5 s / out 2.5 s, raid tracks
  in 7 s with a 7 s end tail, death stop 2.5 s.
- **The storm menu backdrop retired** (user call) — den and drain rotate;
  its generator and textures are gone.
- **Perf** on the user's 240 Hz box: 240 avg fps day/dawn/night, worst
  frame ~4.5 ms, process ~0.9-1.5 ms, ~6.3k nodes (down from ~10.4k).

## [0.6.17] — 2026-08-01

### Added
- **Morning fog**: soft-alpha mist puffs (3 sprites, gen_art `make_fog_puffs`)
  drift through a dawn window (~0.10–0.38 of the day). The builder marks fog
  spots (5% of forest cells + road spots every ~9 cells); the environment
  keeps a 32-puff pool that spawns only near the view (0.25 s refresh,
  ≤3/frame), pushes each puff with a per-morning wind, and dissolves it
  ~90 px past its anchor. Forcing a time of day prefills 90 sim iterations
  so screenshots show a settled bank.
- **Falling leaves**: 25% of oaks shed; a 22-leaf pool spawns near the view
  (one per 0.5–1.4 s), each leaf falling 2.2–3.8 s in one of three patterns
  (sway / zigzag / wind-drift, 2 flutter frames) and fading over its last
  stretch.

### Changed
- **Days are 10 minutes** (was 20; user call — 8 stays on the table) and
  **nights are properly hard to see** (user: "that's why we have a
  flashlight"): deep-night floor dropped to (0.085, 0.095, 0.24), night is
  ~26% of the loop via new gradient offsets, nightfall leans blue-violet,
  and lamps + flashlight now come up from 0.64 of the day.
- **Audio fades** (user calls): raid tracks end on a 4 s fade tail instead
  of a hard stop, with 24–38 s breaths between tracks ("like 30 secs");
  the rain wash slews in/out at 6 dB/s and sits quieter (−49..−34 dB);
  thunder is quieter (−24..−18 dB) and follows the flash faster
  (0.15–0.5 s).
- **Harness**: the world probe prints FOG lines (nearest/spots/active/near);
  `--shot` re-applies env flags after the camera settles so the fog prefill
  anchors to the framed view; headless runs fall back to a 640×360 assumed
  view when the window reports a degenerate size.

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


