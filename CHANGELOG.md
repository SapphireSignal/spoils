# Changelog

All notable changes to SPOILS are documented here. Versions follow a simple
`0.minor.patch` scheme while the game is pre-release.

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


