# SPOILS — session handoff (read this first)

2D isometric extraction shooter, pixel art, Godot 4.7, Windows. **Read
`DESIGN.md` for the full game design & workflow contract** — it is the source
of truth for what we're building. `CHANGELOG.md` records everything shipped.
This file carries everything a fresh session needs that isn't in those two.

## Where we are

- **Version v0.6.21 SHIPPED** (25th release on 2026-08-01 — read
  CHANGELOG.md for v0.6.19/20/21; all same-day). v0.6.20: safehouse
  spawn (bulletproof placement — probe bands + exhaustive row-walk),
  free-angle cursor driving (max 190, `auto_target` hook for harness/
  future AI), diagonal-parallelogram colliders on all (2,1) vehicles
  (mirror_prop flips polys; DriveableCar swaps poly with heading),
  trunk 5.5/lamp 3.5/pallet colliders, door-frame art seed excludes
  door_open (truck color-flash), warehouse GUARANTEED (+fallback dodges
  rail), comms → forest-block corner, fleet +steel-blue/tan (BROKEN
  INDEXES NOW _5/_6 — four builder check sites), single centered
  road line (edge-halves were swapped), corner stairs, upstairs door
  lockout (player.upstairs + auto-close on climb), Sfx engine bed
  self-decays (_engine_target + Sfx._process — it played forever once),
  splash SHATTER (crack frames → shards → studio_signal core → beams →
  studio_tag; _shot_splash captures at 2.4s; soft click ticks).
  v0.6.21: bushes 30-42px hide-in size (foliage RADIUS 24), AUTUMN
  GROVE = east half of the forest block (tree_autumn family, leaves
  0-1 green / 2-3 red, color-true shedding via _leaf_trees_red +
  encoded near-list). Perf 240/4.5ms/~5k. **AWAITING REACTIONS**;
  next = M2 on "go". TRAILER: ffmpeg NOT installed; pitches sent —
  user picks a concept before any build (pipeline: --write-movie PNG
  frames 640x360 → 3x nearest → ffmpeg 1080p60 + davidkbd bed).
- Watch-list: map size (~100 diamond now), THE MAP window (layout/zoom/
  tooltips), map-select screen, cursor driving feel, scrapyard/gallery,
  smoker read, power-box sparks, prone/standing size, den board text,
  splash pacing, trails width, all sound levels.

## v0.6.19 systems (shipped 2026-08-01)

- MAP (map_view.gd, CanvasLayer 75, action "map"=M): builder bakes
  info["map_image"] (_bake_map_image: 1px/cell from plan dicts + plot
  fills + _map_marks) → ImageTexture. World view (transit tile w/ painted
  menu_map_transit.png thumb + 3 "?" tiles) ↔ transit view (custom-draw
  canvas: draw_texture_rect + live car/player markers, ZOOMS [2,3,4,5,6,
  8] cursor-anchored, drag-pan, clamp CENTERS when map < canvas — that
  was the empty-left-half bug), back button, bottom "time %02d:%02d -
  weather" bar, 0.5s POI tooltips both views (_pois from info poi+zones),
  view remembered (_mode) across opens. Harness: --map=world|transit.
- MENU: "play" → _open_map_select panel (thumb button + 3 blacked "?" +
  info column + deploy/back); harness --menu=mapselect. Blurb single
  string + autowrap (manual \\n double-wrapped).
- SCRAPYARD zone block (forest went 2→1 block, DENSER 0.20 fill):
  vehicle rows (driveables mixed), forklift_0/1, ONE crane, rack line,
  junk. GALLERY corner of open block (opposite comms): graffiti_x_0..2
  walls + spray_cans + benches + Smoker (smoker.gd: 3-frame drag/exhale
  + dust-wisp smoke). Street extras: vending_0/1 + newsbox_0/1 on
  sidewalk spacing counters; dumpster mix 0.08→0.15.
- POWER BOXES (_place_power_boxes): power_box_{x,y}[_broken] on the door
  wall ±2 cells; ONE house (_spark_house rolled at plan) gets PowerBox
  node (power_box.gd: spark_0..2 frames, 1.2-4s bursts + light blink).
- DRIVING: cursor-follow (click toggle `following`, heading steps toward
  best-dot facing, ARRIVE_DIST ease); WASD steering REMOVED (user).
  Sounds: doors -19, start -18, off -19, loop -38..-28, alarm -14.
  Alarm flashers get PointLight2D glows (night>0.35, blink-synced).
  STANDING SOUND RULE in prefs memory + sfx comment: new one-shots
  ≤-18dB, beds ≤-28dB.
- FIXES: bushes radius 17 + continuous wiggle while inside (+0.5s
  settle); leaves near-view list refresh 0.5s (old: rolled 1 tree from
  the whole district = never); ONE strike/thunder (chains restarted the
  clap = "cut out"); rain -52..-37, thunder -22..-16; upper floor paints
  EVERY cell (hole showed ground); flashlight rides floor_lift; dirt
  trails 1-wide wobble 0.10 skipping POI rects (2-wide braided into
  mud rivers); sidewalk broken tiles lost weed pixels; centerline =
  asphalt_line[_h] + _b half-tile pairs on road cells +1/+2 (true
  center); BARRIER_INSET 78 (playable ~100); char +2px tall all stances,
  prone rebuilt (10-wide torso + 12 shoulder span N/S, thick diagonals);
  den board titles tall-stretched 090a14 ink + underline + 3px colored
  pin tacks; splash 5.2s slower timeline.
- KEYBINDS: engine=Q, map=M, inventory=TAB (inert until M4) — in
  project.godot [input] + settings BIND_* (panel auto-lists).

## v0.6.18 systems (shipped 2026-08-01)

- ZONED MAP: 256×256 grid, BARRIER_INSET 68 (playable ~120), ROAD_COUNT
  4/axis (jitter ±4 — bigger jitter squeezed blocks into the one-door
  bug), 3x3 blocks dealt in _plan_zones: town×2(adjacent) forest×2
  warehouse school trainyard depot open(+comms corner). _zone_summary →
  info["zones"], POI rects → info["poi"] (probe prints ZONE/POI lines).
- TOWN: houses 6-8×5-7 grow(1) packed, courtyard plaza (clampi(size-14,
  9,12)) in first town block: fountain_dry/planters/benches/lamp; spawn
  at court south lip. SCHOOL: 2-story, screed, desks+shelves
  (_furnish_school), playground (swings/slide/sandbox/flagpole/sign +
  gappy lattice fence, skips dirt paths). TRAINYARD: _plan_rail main
  line full-width on _rail_row (rail_x tiles + ballast ±1, rail_cross on
  roads), 2-3 sidings (12-18 long) w/ boxcar_x + buffer_stop props +
  freight spill. DEPOT: apron rect (asphalt-painted) hugging south road,
  ≤4 bus_nw/se (broken variants spill trash), shelters/bench on lip.
  COMMS: 9×9 corner compound, tower+shed+dish+barrels, lattice-fence
  ring w/ gap (_fence_piece reuses barricade fence family).
- TWO-STORY: plot.stories=2 (~45% town houses + school; ruined forces 1)
  → seg2_/post2_ pieces (STORY_H 32, string course, stacked windows,
  door gets seg2_..._upper TRANSOM — bare door left a hole), roof lift
  wall_h+story_h. _build_upper: floor-sprite container anchored NORTH
  (-24-story_h) so it y-sorts under the player; upper furniture at TRUE
  cell pos w/ sprite child lifted -32 (colliders toggle via
  collision_layer); stairs prop (Stairs class, group "stairs", F) a full
  cell in from walls (art pokes through facades when cornered); registry
  info["uppers"] {container/upper_props/ground_props/stairs_node}.
  main.gd _on_stairs_used flips visibility+colliders, player.floor_lift
  (sprite+shadow+camera rise TOGETHER, whole px); no teleport. Death
  upstairs/driving resets state.
- DRIVEABLE CARS (driveable_car.gd, group "cars"): intact vehicles spawn
  as CharacterBody2D via _spawn_driveable (roads + yard stalls; broken
  _3/_4 stay props). F enter: door texture-swap frame (vehicle_*_door,
  baked via make_vehicle door_open) + ggbotnet CC0 recordings
  (assets/audio/car/, LICENSES.md), player.board_car (hidden, layer 0,
  welded — camera math unchanged); Q engine (must be on to drive), W/S
  ±speed (260 max, 90 reverse), A/D step heading nw→ne→se→sw (0.26s
  cooldown, reverse mirrored), E twin headlight cones, F exit beside
  door. Sfx.set_engine slewed loop bed w/ pitch 0.9-1.25. Car sprite
  parks on the SAME screen-pixel grid (player zoom factor). Entering
  disarms CarAlarms (group "car_alarms", disarm()). Controls hint label
  ~7s on entry (main.gd). "engine" action = Q (project.godot +
  settings.gd binds — rebindable).
- ART: glass windows (_draw_seg_window: 3c5e8b/253a5e + 73bed3/a4dddb
  sheen + 151d28 mullion; boarded keeps planks), smooth asphalt-family
  bases (line/crosswalk/manhole/stall 0.0,0.0 — the "things along the
  yellow line" were baked speckle), plaza tiles (joints + 1-2 whole worn
  pavers — NO checker/dots, first cut violated no-dots), ballast/rail_x/
  rail_y/rail_cross_x/y tiles (period 8), fog_3/4 big banks (env pool
  i%5), buses (make_vehicle kind bus: L64, door, hatches, stripe),
  make_boxcar/buffer/swings/slide/sandbox/flagpole/school_sign/planter/
  fountain/comms_tower/dish/equip_shed/stairs/bed. Clip-audit exempts
  seg2_/post2_ (grid modules).
- DENSITY (user "tone it down"): scatter 210, dead-spot lattice step 4 +
  lower rolls, lone trees 55 (never beside roads/rails/plaza/apron),
  bodies 10-15, buffer 90, puddles 70, road vehicles 20.
- FOG CHURN FIX: _fog_age breathe-in 3.5s (spawn-at-full-alpha was the
  pop), dissolve slide 90/110 (was 46/52), prefill 300 iters.
- MUSIC FADES LONGER (user): menu in 5s/out 2.5s, raid in 7s/tail 7s
  (remaining ≤7), stops 2.5s; Music._exit_tree stops player (headless
  leak noise). NOTE: ~4-6 ObjectDB instances "leaked at exit" in
  headless runs = benign audio teardown noise, varies run to run.
- STORM BACKDROP REMOVED (user): menu = den/drain only (scenes.size()
  drives rotation; --backdrop=2 clamps to drain); make_scene_storm +
  saves deleted from gen_art. Den board verified against the user's
  08:49 spec (paper notes, tacked photos, transit ringed, traders).
- v0.6.17 (same day): morning fog + falling leaves + 10-min day w/ hard
  nights (DEEP_NIGHT .085/.095/.24, night ~26%, lamps from 0.64) + rain
  slew (-49..-34) + thunder -24..-18 & 0.15-0.5s after flash; breaths
  24-38s. Fog window 0.10-0.38; force_time prefills; _shot re-applies
  env flags after camera settle.
- v0.6.16: raid music = USER'S 3 AUDITIONED PICKS (guitar02/harp01/piano01
  as raid_0..2) rotating random-no-repeat, CONTINUOUS from raid start to
  death (2-5s breaths; stop on died, restart post-respawn; the audition
  folder music/"in game music"/ is .gdignore'd — more candidates go there,
  assets/audio/music/raid_N.ogg are the installed picks). Streets: smooth
  asphalt + asphalt_crack/_hole tiles; sidewalk plain/crack/broken rolls.
  scripts/foliage.gd = bush manager (wiggle ±1 WHOLE px on 6-frame toggle,
  alpha→0.55 inside, grass rustle on enter; bushes registered via
  info["bushes"]). Benches/shelters (bench_/shelter_ x/y families) spaced
  on walk cells; _fill_dead_spots lattice pass (tuft/bush/trash on bare
  3x3 neighborhoods). Forest tiles = green family only; dirt gets gray
  mud. HARNESS: _ensure_game_scene aborts loudly after 30s (fail-fast —
  never let a broken world hang a probe again); probe prints WALKS +
  FOLIAGE cells.
- v0.6.15: menu backdrops = den/drain/storm (LIVING: candle/needles/LEDs/
  smoke; ray/motes/drips; rain/strikes/bolts/thunder/flickering windows —
  scene coords use PC offset const, backdrop 0/1/2), raid music (music.gd
  play_raid: 3 tracks -26dB, 70-180s gaps, never same twice), NO-DOTS
  texture language (speckle()=1-3 small solid patches; menu light =
  banded cel; dirt = ruts/clods/stones), variants expanded everywhere +
  wall segs roll 3 variants (seg_..._v1/_v2, weighted 50/25/25).
  KNOWN ARTIFACT: menu screenshots always read 1-20 fps in the corner —
  capture-harness quirk since forever (old shots show "1 fps"); the real
  menu holds refresh. Do NOT chase it.
- v0.6.14 = "the streets update": map HALVED (ring inset 31→72, playable
  ~176², counts rebalanced, nodes ~11k), sidewalks + worn crosswalks +
  manholes + dead traffic lights (5 damage states, mirrored per corner),
  weathering zones (concrete_worn/damp via offset hash grids), warehouses
  now 13-17×9-12 halls with wider human-stacked racks, snipers PREDICT
  (lead = velocity × flight time, 0.75-1.05 per-shooter) and volleys
  STAGGER (0.14-0.42s × index, _pending array in edge_guard._process),
  turn-back warning anchored at (0.5, 0.44) fractional — never px offsets.

## RESOLVED 2026-08-01: the missing-car-part saga (six rounds)

The user circled the exact spot on a 6x truck sheet and that cracked it:
the END FACE was drawn as a 5px stub CONTINUING LENGTHWISE off the near
corner, instead of a full-width wall across the body's iso width axis.
Rebuilt as full-width walls (tailgate/trunk/grille + corner lights +
shutline + bumper strip) in v0.6.13. Trucks confirmed by the user ("yes
thats it, exactly like that"); cars got the same treatment at their
request ("i think the cars had that problem too") — they will confirm
cars in their next playtest. LESSON: when the user reports something
"missing/off" repeatedly, ask them to CIRCLE it on a zoomed sheet —
five theory-driven fixes found real bugs but missed the actual one.
Audio taste addendum learned the same day: footsteps at -18dB were
"loud and obnoxious" — organic sounds now sit at -22dB and below.

## Recent-history context (v0.6.6-v0.6.11: prone stance on Z,
  splash screen + menu music + full audio suite, lattice-fence barricade
  line, 3D barrels, complete vehicles, wheel zoom ladder w/ edge
  auto-tighten, anti-banding dither film, clip audit in gen_art — generation
  FAILS on canvas-edge content, keep it that way). Older baseline: v0.6.5
  ("the barricade update"), committed & pushed. Map
  **"transit"** (user-named), 320×320 total with the PLAYABLE district inside
  a randomized barricade ring (inset 72 cells since v0.6.14); the world visibly continues
  beyond it but escalating sniper fire owns the buffer (fallen-raider bodies
  past the line sell it). Camera NEVER clamps (user call). Doors interactive
  (F, with prompt), flashlight (E, real click), DARK nights, flickering lamps,
  world-anchored rain, ~45 s weather tint fades, dip-free time-budgeted
  deploys, fresh seeded layout per deploy.
- **Milestone 1 (walkable world) is DONE** (~18 user feedback passes, see
  CHANGELOG v0.2.0 → v0.6.5).
- **NEXT: Milestone 2 — GUNPLAY + TUNNELS + STORY, to ship as v0.7.0.**
  Story foundation is drafted in LORE.md (the cordon/wardens lore, magpie +
  traders mara/kettle/verne, and the full shot list for "the wire" — the
  first-launch 2-min painted cinematic that dissolves through dawn mist
  onto the live district, film straight into gameplay). Menu-backdrop
  pitches also live there — THE USER PICKS which to build; do not build
  unpicked ones. Mouse
  aim, hitscan with tracers, muzzle flash, screen shake, destructible props,
  synthesized gun sounds — PLUS the underground tunnel system (user request
  2026-08-01, specced in DESIGN.md §8): secret bookshelf passages in some
  houses, exactly TWO interactive street manholes, F-interact ladders down
  AND back up, dark tight corridors where the flashlight matters. The user
  starts it by saying "go".
- After that (design doc §8): M3 human enemies (0.8), M4 the loop with
  TARKOV-STYLE loot: grid inventory, containers, character doll gear slots
  (0.9), M5 fake-player bots/lighting/trader (1.0), M6 quests (1.1), M7 second
  map (1.2). **User calls 2026-08-01: NO machine enemies (human AI only), NO
  rarity color tiers on loot.**

## Versioning policy (user-agreed, do not drift)

Patch bumps (0.6.x) for polish/fix/content batches. Minor bumps ONLY when a
design-doc milestone lands (0.7 guns, 0.8 enemies, 0.9 loop). **1.0 = the
complete v1 game.** The in-game changelog (CHANGELOG_ENTRIES in
`scripts/main_menu.gd`) must gain an entry EVERY version — the menu's corner
version label derives from its newest entry (single source of truth). Also
update CHANGELOG.md. Tag releases (`git tag vX.Y.Z`, push with `--tags`).

## What exists (systems map)

- `tools/gen_art.py` — generates ALL art deterministically from
  `art/palettes/apollo.gpl` (46 colors) into `art/gen/` + `manifest.json`
  (sizes, origins, collision shapes, variant families — the game hardcodes
  none of it). `tools/gen_font.py` (invoked by gen_art) builds the lowercase
  bitmap font. `tools/gen_banner.py` → repo banner.
- `scripts/world_builder.gd` — 256×256 planned map (ZONED since v0.6.18 —
  see the systems section above), FRESH SEED PER DEPLOY
  (build(root, seed_text); harness --seed pins it; ALL randomness through the
  seeded _rng — `Array.shuffle()` is banned, use `_shuffle()`). Road grid with
  center dashes both axes, dirt roads, forests + interior groves + lone trees
  on green pockets, ~34 buildings (thin-wall shells, modular roofs, ONE floor
  look per building, interactive Door on a visible side, entrance pockets kept
  clear inside AND out), lane-correct road vehicles (some broken + litter),
  sparse mostly-dead street lamps, sticks, clustered scatter, puddle spots.
  sidewalks flanking ~62% of road sides (pale slab tiles, v/h orientations,
  13% broken), worn crosswalks on every intersection arm, rare manhole
  tiles, dead traffic lights at crossings (traffic_light[_m]_0-3 + _flat,
  placed 0-2 per intersection, mirrored so heads hang over the asphalt),
  district weathering zones (concrete_worn/damp picked by two offset
  8-cell hash grids off _zone_salt — probabilistic mix, no patch grid).
  BARRICADE RING at inset 72 = the advertised map edge (art axis x/y, flats
  walkable-over, road breaches get wreckage) + sparse bodies past it; tree
  density tiers off through the buffer band. Border collision at the true
  diamond edge is only a backstop. build() is a COROUTINE with TIME-BUDGETED
  yielding (~2.4 ms/frame via _tick() — never fixed work-counts; that caused
  deploy fps dips).
- `scripts/environment_system.gd` — day/night tint (20 min, continuous
  gradient loop — endpoints MUST match or midnight snaps), world-anchored
  rain (drop pool falls to real ground points, splash pool stays put, roofed
  cells skipped, all puddle-blue), long storms, double-strike lightning,
  puddles, night_amount broadcast to "street_lamps" group.
- `scripts/street_lamp.gd` — working/dead lamps; working ones glow + cast a
  PointLight2D pool at night with per-lamp flicker/dropouts.
- `scripts/door.gd` — closed-by-default door: F toggles, 4-frame swing,
  thin wall-line collider disabled while open, group "doors".
- `scripts/stairs.gd` — second-story flight, group "stairs", F flips the
  floor via main.gd. `scripts/driveable_car.gd` — intact cars as
  CharacterBody2D: F enter/exit w/ door frames+sounds, Q engine, WASD
  drive, E headlights (see v0.6.18 systems).
- `scripts/edge_guard.gd` — barricade-line snipers with PREDICTIVE aim
  (lead the player's velocity by flight time, per-shooter 0.75-1.05x) and
  STAGGERED volleys (first shot instant, rest via _pending countdowns in
  _process — never scene-tree timers, they outlive scene swaps); each
  spawned round plays its own crack. Warning label: fractional anchors
  (0.5, 0.44) under a full-rect root — centered warning ("turn
  back or you will get sniped") on crossing barrier_f, 3 s grace, off-screen
  tracer rounds, ESCALATING interval/accuracy with depth, 3 hits = death.
- `scripts/player.gd` — render-rate movement (NOT physics tick), THREE
  stances: stand / crouch (ctrl, hold-or-toggle) / prone (Z toggle, 0.32x
  speed, crouch input exits it; char_prone.png sheet, same layout as the
  others), flashlight cone on E (8 facings; smooth light textures may rotate,
  sprites never), hp/take_hit/hurt-flash/died + respawn, camera UNCLAMPED and
  welded to the character, snapped to SCREEN pixels (see rule 1).
- `scripts/main.gd` — deploy screen ("deploying to transit", animated
  dots) → texture prewarm → awaited async world build → environment → edge
  guard → pause menu; death fade → respawn. `scripts/main_menu.gd` — 3
  rotating LIVING backdrops (0=den w/ the traders + job board, 1=drain,
  2=storm; painting coords via the PC offset const; per-scene ticks drive
  candle/needles/LEDs/smoke, ray/motes/drips, rain/strikes/bolts/thunder
  + window-flicker state machines), title shine, changelog viewer.
  `scripts/settings.gd` —
  display/res/quality/fps/vsync/show-fps + rebindable keys + pixel_scale (the
  integer window scale) + 0.2s-window fps counter. `scripts/keybinds_panel.gd`,
  `scripts/settings_panel.gd`, `scripts/pause_menu.gd`, `scripts/ui_theme.gd`
  (bitmap font + near-black/light-border buttons), `scripts/sfx.gd`
  (HYBRID since v0.6.13: synth for UI blips, door thunks, sniper crack,
  flashlight click, splash ping, rain bed (set_rain), car alarm; LICENSED
  RECORDINGS under assets/audio/ for per-surface footsteps
  (play_step(kind, quiet), -22/-27dB) and thunder — licenses in
  assets/audio/LICENSES.md, DESIGN.md §5 amended; rain+alarm still render
  on a Thread), `scripts/music.gd` (menu theme = licensed guitar loop at
  -18dB; RAID mode since v0.6.15: play_raid()/stop_raid() — dongxiao/
  harp/guitar loops at -26dB, one at a time, 70-180s silences, never the
  same twice; main.gd starts it post-build, menu _ready switches back;
  42 more pack tracks re-downloadable), `scripts/splash.gd` +
  `scenes/splash.tscn` (SapphireSignal
  studio card — THE BOOT SCENE; harness args skip it instantly),
  `scripts/car_alarms.gd` (armed intact cars: proximity alarm + flashing
  light overlays from manifest "lights" coords, once per car until death),
  `scripts/authority.gd` (state seam: spawn_player, damage_player),
  `scripts/harness.gd` (see Verification; also --shot-splash=<name>).

## Verification workflow (design doc §7 — never skip)

After ANY art change: `python tools\gen_art.py`, then delete orphan imports:
`python -c "import pathlib; [p.unlink() for p in pathlib.Path('art/gen').glob('*.png.import') if not p.with_suffix('').exists()]"`
then `godot_console --headless --path . --import`.
- Smoke: `godot_console --headless --path . -- --smoke` → must print SMOKE PASS
  (covers movement, crouch, border, roofs, doors, edge sniper, pause).
- Shots: `godot_console --path . -- --shot=<name>` (+ optional flags:
  `--scene=menu`, `--menu=pause|settings|changelog`, `--backdrop=N`,
  `--at=X,Y`, `--face=N|S|E...`, `--crouch`, `--weather=rain`, `--tod=0..1`,
  `--flashlight`, `--seed=<text>`). Read the PNG yourself, judge it, iterate,
  send the user a 2× upscale (scratchpad) of the good one.
- `--seed=<text>` pins the district; ALWAYS pair `--probe-world` (prints
  lamp/vehicle/door/traffic-light counts + shot-aimable cells) with the same
  seed you then shoot, or your coordinates aim at a different world.
- Perf: `godot_console --path . -- --perf [--weather=rain --tod=0 ...]` →
  prints avg fps / worst frame ms / node count. v0.6.3 baseline on the user's
  240 Hz box: 240 avg, worst ~5 ms, ~34k nodes.
- Godot: `D:\Godot\Godot_v4.7.1-stable_win64_console.exe` (CLI) / non-console
  exe in Play.bat. Console exe for everything scripted.

## Hard-won rules (violating these caused user complaints — never regress)

1. **User's display: 240 Hz, desktop 1680×1080 (stretched, non-native — do
   not relitigate it).** ALL motion updates in `_process` at render rate.
   Rendering is NATIVE RES (`canvas_items` stretch + integer scale) with ONE
   EXPLICIT screen-pixel grid (multiples of 1/Settings.pixel_scale world px):
   the player's TRUE position stays continuous, but each frame the rendered
   sprite+shadow park on the grid and the camera is defined off that SAME
   snapped point (constant character-to-camera offset — see player._process).
   120 px/s walking = exactly 1 screen px/frame at 240 Hz. Do NOT round the
   camera to whole WORLD pixels (halves scroll rate → "low fps walk", v0.6.3),
   do NOT let camera and sprite round independently (shimmer, v0.6.4), and
   snap_2d_transforms_to_pixel stays OFF — engine auto-snap fights the grid
   at half-pixel positions. Static props/splashes sit on whole world pixels
   (_add_prop rounds); the player settles to whole world px when idle.
2. **Text**: only the generated lowercase bitmap font (no capitals anywhere,
   user preference). If text ever looks blurry: the .fnt import silently
   failed — delete `art/gen/spoils_font.fnt.import` + `.godot/imported/
   spoils_font*` and reimport (Godot caches import failures for unchanged
   files).
3. **RANDOMIZE placement/variants everywhere.** The user repeatedly and
   angrily flagged hand-placed grids and cloned props ("do you not understand
   that yet?"). Counts, positions, variants, offsets — all rolled. Baked
   variation (sizes/damage/poses) in the generator; NEVER runtime
   scale/rotation (breaks pixel grid).
4. **Symmetry & flushness**: character must be symmetric (arms/neck history);
   walls identical on all sides; roofs flush with walls, trim lines continuous
   through corners. The user zooms in and checks corners.
5. Palette purity: every game sprite from Apollo only (white font/dust/rain +
   alpha assets exempt by design). One palette per asset.
6. Interior reveal: roof fades to 0 ONLY when the player is inside the
   interior cells; walls always stay visible (user rejected wall fading).
   Buildings: one door each, on a camera-visible side (south/east) — CLOSED
   until F-toggled, flush in the wall plane (an open-leaning leaf clipped
   through walls: user complaint). Floors: ONE uniform tile per building
   (per-cell variants read as patchwork: user complaint). Entrances must stay
   prop-free inside and outside (couch-in-doorway complaint).
7. Menus: buttons near-black translucent with light border (hue-based fills
   blended into backdrops); menu buttons exactly centered, self-centering;
   settings panel fixed width; VSync ON greys the FPS cap slider.
8. PowerShell 5.1 quirks: no `&&`; heredocs don't work (use the Bash tool for
   python heredocs, or scratchpad files); .bat files must be ASCII+CRLF; git
   line-ending warnings are normal noise; `git commit` exit 255 with warnings
   still commits — verify with `git log`. NEVER put double quotes inside a
   commit-message here-string passed to git -m — PS 5.1 splits the argument
   at the embedded quote (a commit silently failed and a tag landed on the
   wrong commit; recovery: commit, `git tag -f`, force-push the tag).
9. Costly-to-rediscover: Godot won't mode-switch displays (no exclusive-res
   change); stretch `viewport`+`integer` ignores `expand` (manual
   content_scale_size math in settings.gd); iso prisms need w == 2*d, d even;
   brick/pattern period must divide 64 for seam continuity.

## Additional never-regress rules (learned 2026-08-01, the hard way)

- The user perceives SINGLE 8-bit tint steps of slow full-screen fades: the
  dither film overlay (main.gd, dither.png) exists for this — never remove.
- Audio taste: SUBTLE always. Rain = quiet smooth wash (no pops — 0.4%%/sample
  reads as crackle; no audible loops), footsteps distinct per surface but
  quiet, alarm pulses need attack/release ramps (hard gating reads "static").
  STANDING RULE (user, third correction): every NEW sound ships QUIET on
  first cut — one-shots ≤ -18 dB, beds/loops ≤ -28 dB; raise only on ask.
- Lines of repeated infrastructure (barricades) = ONE dominant design with
  wear, not per-piece variety ("every one different is weird"); lattice
  fences dominant, jerseys accents; uneven spacing + off-line jitter.
- Everything must read 3D ("angular view illusion"): iso top faces, curved
  hoops/shoulders, lit/shade faces — no front-view flat props. The gen
  CLIP AUDIT fails the build on canvas-edge content: keep it.
- **NO single-pixel dot noise anywhere** (user call 2026-08-01: "remove
  those little dots everywhere"): texture = structural detail (joints,
  cracks, ruts, mortar) + a few SMALL solid wear patches (speckle() bakes
  1-3 blobs, ~old coverage — the first cut at 3x read as camo clutter,
  retuned) + smooth-alpha light overlays. Menu paintings use banded cel
  light, wavy solid gradient seams. ONE exception: the 1/255 anti-banding
  dither film in main.gd — imperceptible, load-bearing, never remove.
- Boxes (crates/stacks/pallets) only near warehouses/yards, never open
  streets. Roads never parallel-hug the barricade ring. Broken roof holes
  are attic-dark, never transparent.
- Zoom: whole-factor ladder only (native..6x), glide between stops, NO
  wider-than-native view (was "too OP").
- Deploy + boot: time-budgeted work only (~2.4ms/frame); the one remaining
  ~30ms frame is the menu→game scene swap itself (documented, accepted).

## User preferences (communication & product)

- Plain, short, non-technical summaries; they playtest and react — build,
  verify, ship, send screenshots, stop. Milestones proceed on their "go".
- Very sensitive to frame pacing and visual artifacts (spots 1px issues, fps
  wobbles, single-frame hitches — always explain honestly, fix structurally;
  loading moments get masked behind transitions like the deploy screen).
- Dislikes clutter, clones, visible grids/patterns, anything "off"/asymmetric.
- Wants the world to feel alive/real (weather, time, POIs, furniture).
- GitHub: https://github.com/SapphireSignal/spoils (PRIVATE, account
  SapphireSignal, branch main, tags v0.1.0…v0.6.2). Push after each batch.
  Commits end with the Claude Co-Authored-By trailer.

## Registered-but-inert (activate in later milestones)

- LIVE: interact(F → doors), flashlight(E), prone(Z). Still inert:
  reload(R), weapon slots(1/2/3) — wire in M2 (guns).
- Settings "graphics quality" is stored but drives nothing until M5
  lighting/effects.
- Night darkness + flashlight + lamp lights shipped in v0.6.3, deepened in
  v0.6.5 (CanvasModulate + PointLight2D — real 2D lighting still expands in
  M5). Known minor: monitor panel-stretch shimmer is out of our control. One
  ~30 ms frame on the menu→game scene swap remains (hard cut, invisible in
  motion; the fps counter blips ~200 for one window) — everything after holds
  refresh rate; fixing it needs keep-menu-resident scene switching, deferred.
