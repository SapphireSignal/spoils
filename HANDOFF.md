# SPOILS — the handoff chain

**What this file is:** one short entry per chat session, newest first. A chat
does not survive. This file is how the next one inherits what the last one
knew — not just what shipped (that is `CHANGELOG.md`) but what the user
*said*, what turned out to be *wrong*, and where the work was *put down*.

**Read the top two entries and you are caught up.** Then `TASKS.md` for the
work, `CLAUDE.md` for the rules.

---

## How to write an entry (the ritual — do not skip it)

Write your entry **before the session ends**, not after — there is no after.
Practically: write it whenever you finish a batch and are about to push, so a
chat that dies mid-session still leaves a record.

1. **Append at the top**, under the divider. Never edit an older entry —
   the chain is append-only. A past entry being wrong is itself a fact worth
   keeping; correct it in the *new* entry and say what was wrong.
2. **Four headings, always.** Shipped / The user's words / Learned / Picked up
   at. If a heading has nothing in it, write "nothing" — an absent heading
   reads as a lost one.
3. **Quote the user verbatim.** Paraphrase is where intent dies. Their exact
   phrasing is what steers art and feel decisions, and it is the single
   thing most likely to be lost forever.
4. **Record what was WRONG, loudly.** A previous session's confident-but-false
   diagnosis has cost real time on this project twice (the door swing, the
   second-floor leads). If you disproved something, say so here.
5. **Keep it short.** A dozen lines. This file must stay readable at entry
   fifty, or it rots the way `CLAUDE.md` did — 977 lines of stacked history
   nobody trusted.
6. **Compress on the way out.** When an entry is older than the newest three,
   cut it to two or three lines: version range, and anything still load-bearing.
   Detail that still matters belongs in `CLAUDE.md` or `TASKS.md` by then, not
   here.
7. **Run `--checkdocs` before you commit the entry.** It proves the version
   claims in `CLAUDE.md`, `TASKS.md`, `CHANGELOG.md`, the in-game list and the
   git tags all still agree.

---

## 2026-08-05 — the title got a material; the map got sent back

**Shipped: v0.6.51 — the title is cast metal.** Both halves of the user's
complaint were real. *"just white"*: the wordmark was the 1× font blown up 7×
in two flat tones, five colours in the whole image, and — the root cause —
every edge was a 7 px slab while the rest of the menu renders at 1 px, so it
read as a placeholder over finished art. Letterforms still come from the
game's own font; the DETAIL is native resolution now (banded cel gradient,
1 px lit/shaded rims, chamfered corners, directional weathering, a real
extrusion). *"goes up and down a bit thats all"*: `scripts/gleam.gdshader`,
which replaced a 34 px `clip_contents` bar that was **idle 5.1 seconds out of
every 6**. Full write-up in TASKS.md A3.

**The user's words:**
- *"finish the polish pass"* — the same pass as the last session's, so the
  waiver they gave then (batching allowed, no per-item screenshot sign-off)
  still reads as live. Do NOT extend it past this pass.
- **On the map screen, which v0.6.46 marked DONE:** *"the in game map looks
  like an actual map that youd hold, i dont want it like that, i want there to
  be colour on there, the trees are just lines in there too, and all the roads
  are the same size oin the map, all the pois are like in the same spot, the
  map just doesnt look good, like all the roads are symmetrical, the POIs too,
  i just want it to at least look real a bit. like the map just looks like
  squares and lines, doesnt look like an actual map. remember i dont want a
  real looking map i just want it to look like a good real map that youd see
  in other video games"*

**THE MAP IS REOPENED. A1 item 1 is NOT done — v0.6.46 built the wrong
thing.** It chased "a chart, not a screenshot of the ground" and landed on a
surveyor's paper sheet: monochrome sienna, woods drawn as diagonal hatch
strokes, every road an identical pale band, every POI an identical bordered
square. The user wants a VIDEO GAME map — coloured terrain, tree masses,
road hierarchy, POIs that read apart from each other.

**Verified before touching anything, and one finding changes the brief:**
**every road in the world is literally width 4** — `_plan_roads` appends
`Vector2i(base, 4)` for all of them, vertical and horizontal. So *"all the
roads are the same size"* is true of the WORLD, not just the drawing. The map
cannot invent a hierarchy without lying — except that two roads genuinely are
the through-routes (`keep_v`, the middle vertical carrying the toll crossing,
and `_roads_h` index 1, the crosstown route kept whole so the district stays
drivable). Draw those as arterials and it is TRUE. The rest of the grid
symmetry is the FIXED district and is not the map's to fix.

**Shipped: v0.6.52 — the map is a game map now.** Terrain coloured by what it
is (open land, city blocks, paved aprons, dirt yards, dim ground beyond the
wire), woods as canopy masses with a light direction instead of hatch
strokes, a road hierarchy, markers keyed to what a place is FOR (green = a way
out, red = home, blue = somewhere to go), and ground mottle hashed off the
cell so it cannot crawl while you pan.

**Three things from it that will bite again:**
- **`antialiased: true` on `draw_circle` is expensive, and the cost is
  PER FRAME.** The rebuild measured 240 -> 210 fps and 4.61 -> 7.09 ms worst
  frame with the map open over a live raid. AA off on the grove and mottle
  circles: **240.0 fps / 4.45 ms**, no visible difference. The district layer
  is re-rasterised every frame even though its draw callback only runs on pan
  and zoom — so primitive count there is not a one-off cost. I nearly shipped
  the regression on the strength of a screenshot's fps counter; `--perf
  --map=transit` is what caught it.
- **Patch size decides whether mottle reads as texture or as a fault.** First
  cut was 1.6-4.3 CELLS across and read as grey smudges drifting over the
  district.
- **The road hierarchy had to be earned, not invented.** Every road in the
  world is `Vector2i(base, 4)` — four cells, all of them — so the old map was
  telling the truth. The honest signal is the SPAN: a road that crosses the
  whole district is a through route, one that stops short is a stub. That is
  real, it is in the data, and it is the distinction a player acts on.

**NOT DONE, and deliberately — it needs the user's call.** They also said
*"all the roads are symmetrical, the POIs too"*. That is the DISTRICT, not
the drawing, and **THE MAP IS FIXED** is a standing rule: changing it means a
new `DISTRICT_SEED` or a builder change, and it moves every building, POI and
the safehouse. Written up as TASKS.md **A1b** with a cheaper middle ground
(the road jitter is only ±4 cells on a ~124-cell span). Do not start it
without asking.

**Shipped: v0.6.53 — the district came off the grid. A DELIBERATE,
USER-APPROVED MAP REVISION**, asked for in these words: *"yeah but just by a
little bit, like you can move it a couple centimeters around. currently its
like perfect, the raods, the pois"*. Road pitch 36-flat -> 40/33/33 and
41/33/36; POIs off their exact centres and corners.

**`DISTRICT_SEED` IS UNCHANGED — still `"transit-01"`. Any capture or
coordinate from before 2026-08-05 shows a different district than that seed
builds now.** Flagged at the top of CLAUDE.md's world state too.

**The technique is the reusable part: it cost the layout rng ZERO draws.**
Every nudge reads `_side_rng` or a local RNG seeded off `DISTRICT_SEED` plus a
per-place key. One `_rng` draw would have re-rolled every block assignment,
plot and prop after it — a new map, not a nudge. Block zoning, plot rolls and
the safehouse ([174, 73]) all survived.

**Three of four attempts broke something, and the detector is cheap:**
- **`--probe-world`'s DOORS count catches the squeezed-block bug for free.**
  Baseline 15, first attempt **10**. Blocks between roads are the districts;
  a narrow one fits fewer house plots. Final: **16**.
- **The courtyard nudge alone cost two houses** (15 -> 13), isolated by
  neutralising it by itself. Reverted — it stays dead centre. Do not
  re-attempt without re-probing DOORS.
- **`MIN_PITCH` is what makes a wide nudge safe**: clamp every road to a
  minimum pitch from its neighbours AFTER the roll, forward pass then a
  backward pass so overflow does not pile onto the barricade.
- **I nearly measured the wrong baseline.** The backup copy I diffed against
  had the road-nudge call already stripped, so a run came back "unchanged"
  and looked like the nudge did nothing. Check the call site is live before
  concluding a change had no effect.

**`--at=` TAKES CELL COORDINATES, NOT WORLD PIXELS.** I converted cells to
world pixels by hand and the shot landed outside the barricade with the
sniper warning up. The cells `--probe-world` prints are aimable as-is.

**Shipped: v0.6.54 — terrain fringes and a visible grey house.**
- *"can we make all of the biomes blend more together with another"*, *"like
  the grass, dirt, stone, try blending them"*, *"yes they are hard edges
  blocks everywhere"*. There WAS a blend and it could not work: one cell deep
  and **non-directional** — a tile with grass scattered generally over it,
  picked at random, with no idea which side the grass was on. 135 baked
  fringe tiles now (3 pairs x 15 edge masks x 3 variants), composited from
  the real tiles of both materials. **Zero extra `_rng` draws** — DOORS stayed
  16 on identical cells, so nothing rerolled.
- *"the edge of this house is like barely seeable"* — measured, not judged:
  `brick_b`'s shaded face was **`394a50`, byte-identical to `CONC_BASE`**, and
  its mortar matched `CONC_D1`. The grey house was drawn in the pavement's own
  two colours. Lifted one step. **An outline was the wrong tool** — wall
  segments tile edge to edge and `outline_auto(sides=False)` exists precisely
  because outlining the joins blacks every seam and shows the world through
  the wall.

**TWO PROCESS FAILURES, BOTH ALREADY IN THE DOCS, BOTH REPEATED ANYWAY:**
- **I skipped the reimport after `gen_art.py` and it painted BLACK TILES.**
  The atlas GREW by 135 tiles, so every new (col,row) pointed past the stale
  cached texture. **The user saw it before I did** — *"i saw black squares, is
  it not finished yet?"*. Run all three steps of the art workflow, always.
- **A quoted `<<'PY'` heredoc STILL ate backslashes**, landing a literal `\n`
  mid-line in `world_builder.gd`. CLAUDE.md said quoting was the fix; it is
  not, and I have corrected that line. **The symptom was a HANG, not an
  error** — `--probe-world` ran past 300 s because the script failed to parse.
  `--check-only --script <file>` diagnoses it in seconds. Do not put a literal
  backslash in heredoc'd source; restructure so none is needed.

**Shipped: v0.6.55 — the blend rebuilt, plus four things the user caught.**

**THE BLENDING TOOK THREE ARCHITECTURES AND THE FIRST TWO ARE THE LESSON:**
- v0.6.54 baked a fringe **per material pair**. It explodes combinatorially,
  so only three pairs existed and the rest of the district kept hard edges —
  *"some parts of the road are still square too, and some parts of the grass,
  like all over the map"*. It also REPLACED the tile, throwing away the
  crack/stain/worn variant underneath.
- Its tear was varied by **screen x/y**, so the boundary ran roughly PARALLEL
  to the tile edge and read as piping traced around every tile — *"the grass
  just has some gras line around it all now, it still looks weird"*.
- **What works: one overlay per INTRUDING material on a second TileMapLayer.**
  180 tiles (4 materials x 15 edge masks x 3 variants) composite over
  anything, base wear shows through, and the front wanders along a coordinate
  that runs ALONG the edge so it cuts across the tile. Reach is per material,
  so a boundary is one ragged line and not two bands facing each other.

**The user's words, all of them worth keeping:**
- *"i want it to look naturally blended together with whatever other tile is
  next to a tile"*, *"for every tile in the game"*
- *"you made all of the trees with no leaves on them swing back and forth, i
  only want that on the bushes and trees with leaves on them, right now the
  sticks are moving back and forth"* — sway matched the prefix `tree_`, which
  catches the DEAD trees (variants 7-8 of the same family). **Now
  manifest-driven**: the generator writes a `sway` field, because only it
  knows which variants it drew bare. Dead trees stay IN the `tree` family on
  purpose — splitting them out changes what `_pick_variant` sees and rerolls
  the district.
- *"the car that spawns next to the safehouse should be working, not a broken
  one"* — the roll is still TAKEN and only its result remapped; re-rolling
  would shift every draw after it.
- *"the dead bodies outside of the map dont have any blood"* — there was a
  stain: 5-9 SINGLE PIXELS of `241527`, near-black on dark ground, drawn
  under the figure. Invisible, and strictly the dot noise this project bans.

**STILL OPEN, asked for this session and NOT started** — all in TASKS.md:
- **Parking lots / aprons joined to the road network** by short access roads
  (*"a parking lot can have a small road going from it and then it connects
  into the road"*). A layout change; needs the same zero-draw discipline.
- **Broken cars made distinct** — *"i cant even tell it was broken, like make
  the door opened with some stuff on the ground near it, the windshield can
  be broken, little bit of smoke can come out of the engine too"*.
- **UI and icons** — PARKED MID-WAY. `make_ui_frames`/`make_ui_icons` exist in
  `tools/gen_art.py` and are **not called or wired**; `scripts/ui_theme.gd` is
  untouched. The plan: nine-patch frames because a StyleBoxFlat has one border
  colour for all four sides and so cannot bevel.

**Shipped: v0.6.56 - the last straight lines out of the blending.** User:
*"theres still some lines on the grass, like i can tell it doesnt look
natural"*. Both causes were GEOMETRIC, not tuning, which is why v0.6.55's
softer settings had not touched them:
- **The blend ran BOTH WAYS across every boundary.** Grass into concrete AND
  concrete back into grass puts both overlays hard against the SHARED TILE
  EDGE, so the join is a dead-straight line at the iso angle. Reducing the
  reverse reach only thinned it. Materials are totally ordered now
  (grass > dirt > gravel > hard surfaces) and may only creep DOWN the
  ranking, so exactly one side of any boundary carries an overlay.
- **The front could recede to zero**, leaving bare concrete meeting solid
  grass along a stretch of the join. `_wander` has a floor now.

**The generalisable bit: with tile-based blending, ask what happens AT THE
SHARED EDGE, not what a single tile looks like on its own.** Three of the
four failures in this system were invisible when looking at one tile.

**Shipped: v0.6.57 - the blending reaches everywhere, and roads rot.**
- **The fringe pass ran too early.** It was at the end of `_paint_terrain`,
  but `_place_lone_trees` and others write floor tiles AFTER that pass, so
  whole areas never got blended - the user found a lone grass tile in the
  dirt and a pocket under a dead tree, both hard diamonds. It runs once at
  the END OF THE BUILD now, so it is complete by construction rather than by
  remembering which passes matter.
- **Dirt washes two cells ONTO hard surfaces.** A one-cell blend traces a
  road's outline instead of covering it.
- **Road decay patches**, clustered off a hash grid, drawn on the map too.

**STILL OPEN - a large user backlog from this session, all in TASKS.md
B0-NEW.** The unifying complaint is GEOMETRY: *"i dont just want my whole
game to look square"*. Rail corridor still a hard parallelogram (rails
should stay crisp, the BALLAST should fray - `fr_gravel_*` already exists);
houses are rectangles (C3); three trucks parked identically in a row; a door
invisible against its own wall; fallen trees at ~10%; puddles with varied
sizes and an animated reflection. Plus the earlier B0/B0b: parking lots
joined to roads, and broken cars reading as broken. **UI and icons remain
PARKED mid-way** - `make_ui_frames`/`make_ui_icons` exist in gen_art and are
not wired.

**Shipped: v0.6.58 - the ground pass.** *"lets give it the ground pass ...
also the dirt looks more red than brown"*.
- **The dirt was built on the RED ramp.** `341c27` over `241527` are the
  darkest values of Apollo's ORANGE and RED ramps. **A colour reads as brown
  only when GREEN leads BLUE** - both of those have blue above green, so the
  earth came out wine however much of it there was. `7a4841`/`ad7757` lead
  green. Darkening is by COVERAGE, because every Apollo brown darker than
  `7a4841` flips blue-over-green and goes mauve again.
- **`_tonal`: large low-contrast blotches on every surface.** Each floor was
  one flat base plus per-pixel wear, which is flat at any distance - speckle
  averages back to the same tone, so more of it never helps. Patch-scale
  drift is what makes a field of tiles stop reading as one colour.
- Asphalt keeps NO speckle (smooth roads is a standing call); its blotches
  read as old repairs.

**ON GEMINI'S ADVICE, which the user pasted:** most of it matches rules this
project already has. **TWO ITEMS WOULD BREAK THE GAME and were declined, with
the reason given to the user:** runtime tilt ("rotate cars 5-15 degrees") and
runtime scale jitter ("+/-15%") both resample pixel art off its grid and
shimmer under a moving camera - this project bakes `bake_lean()` and per
instance variants at GENERATION time for exactly that reason. Curved/spline
roads were also declined for now: roads are axis-aligned tile bands that
sidewalks, crosswalks and lane-correct vehicles all key off.

**Shipped: v0.6.59 - two real bugs, both long-standing or self-inflicted.**
- **`blob()` WAS A RANDOM WALK.** It claimed to return "soft blob-shaped
  patches" and actually kept every cell a wandering cursor visited, which is
  a thin hooked trail. **Every wear patch in the game was a 1 px squiggle**
  - the user read them as *"question marks on the road"*. It grows a
  connected clump now. This is the single highest-leverage art fix of the
  session: `speckle`, every floor, every prop wear pass and the menu
  paintings all route through it.
- **The v0.6.57 dirt wash went THROUGH WALLS**, filling building interiors
  with earth and breaking the standing "ONE uniform floor per building" rule.
  `_indoors` is tracked now and excluded from the wash and the fringes.
  **A ground-weathering pass must always ask what is a floor.**
- Map: blocks/areas/slabs are wobbled polygons, not rects; the decay patches
  were one rect PER CELL (literal squares) and are discs now; its dirt colour
  was left behind on the red ramp when the world moved to brown.

**A NOTE ON PACE.** The user sent ~15 separate requests during this stretch,
faster than they could be shipped. Everything is recorded in TASKS.md B0-NEW
rather than held in the chat. **If you inherit this, read that list before
starting anything** - several items are still open and at least one (the map
redesign as "a painting") is a direction change that needs their sign-off on
a sample first.

**Shipped: v0.6.60 - brown dirt, and the wash stops running straight.**
- **Brown vs red is decided by how far GREEN clears BLUE.** `7a4841` clears
  it by 7 and still reads warm; `884b2b`/`ad7757` clear it by 32. Measure the
  channels, do not judge the swatch.
- **A uniform-probability spread makes a STRAIGHT band.** The dirt wash was
  ~solid at one cell and sparse at two, so it hugged its source: ragged at
  the pixel level, dead straight in SHAPE. A coarse per-block reach makes it
  lobed. **Shape is what the user sees, not pixel-level raggedness** - that
  distinction cost several iterations.
- `--probe-world` prints `FRINGE {...}` now. It settled this one: 1000+
  overlays were being placed, which ruled out the fringe pass and pointed at
  the wash. **Add the measurement before the third guess, not after.**

**OPEN AND EXPLICITLY NOT GUESSED AT: a one-off visual hitch while walking**
(TASKS.md B0-NEW item 10). "Once per thing, never again in the same spot" is
a first-use cost. `--perf` holds a STATIC camera so it has never been able to
see it; the first job is a walking perf mode, not a fix. Note
`_prewarm_textures`'s comment claims `load()` does the GPU upload - that
claim is unverified and is the first thing to test.

**Shipped: v0.6.61 - `--perf-walk`, and what it RULED OUT.**

**EVERY PERF NUMBER THIS PROJECT HAS EVER QUOTED CAME FROM A STATIONARY
CAMERA.** `--perf` never moved, so it was structurally blind to anything paid
on first draw. That is a real gap in the verification workflow, not just a
missing feature.

Measured with the player sweeping ~9000 px across unvisited ground: **5761
frames, 240.0 fps, worst 6.91 ms, ZERO over 8.34 ms**, and the user's own
counter agrees. **So the thing they can see is NOT frame rate** - it is a
one-frame draw-order or visibility pop. Aiming a fix at performance would
have been aiming at the wrong thing entirely.

**Gotcha in the probe itself:** the player spawns INSIDE the safehouse and
`player._process` runs `move_and_slide()` every frame, which depenetrates
them back out of anything a teleport puts them in - the first cut never left
the spawn building and measured a static camera again. Collision off for the
duration.

**The user corrected the symptom mid-investigation** - *"the weird glitch
happens on things next to my character too, like not when it first appears on
the screen"* - which killed the first-use theory and cleared
`_prewarm_textures`. **Listen for that: they had described it as
first-appearance twice before that correction.**

**LIVE CANDIDATE, NOT PROVEN, DO NOT SHIP A FIX WITHOUT THE FRAME-DIFF:** the
player's y-sort key and drawn position are different values.
`global_position` stays continuous while the sprite draws at `snapped_pos`,
but y-sorting sorts on the NODE's y - so the player can sort against a wall a
frame before or after the sprites visually cross. Full write-up and proof
method in TASKS.md B0-NEW item 10. Snapping the node instead would quantise
movement - that is the v0.2.1 "low fps walk" bug, already paid for once.

**THE USER ASKED TO RESUME ON THE ONE-FRAME POP.** Their words on the way
out: *"is continuing on this glitch saved? ... you were talking about some
frame by frame thing, lets do that when i get back"*. It is TASKS.md B0-NEW
item 10, and that entry now leads with the measured conclusion and the exact
next step (film while walking -> diff consecutive frames -> crop the flagged
pair). **Start there, not at the top of the backlog.**

**Shipped: v0.6.62 - the roof reveal stops announcing itself.**

**FOUND AND FIXED A REAL ONE-FRAME FLASH.** The interior reveal tweened the
roof with `TRANS_QUAD` + **`EASE_OUT`**, which is fastest at the START - 19%
of the fade done by t=0.1, 51% by t=0.3. Measured walking past a house: the
roof dropped **28 brightness levels between two consecutive frames**, ~56% of
the whole fade, then crawled. `EASE_IN_OUT` moves 2% by t=0.1. Re-measured on
the identical route: **28.0 -> 1.0 levels**.

**BE HONEST ABOUT WHAT THIS DOES NOT PROVE.** A clean walk past a house with
collision ON showed **median residual 0** - consecutive frames pixel-identical
after motion compensation, no outlier at all. So this is a genuine artefact
that is now gone, but it is **NOT proven to be the one the user saw**; their
report was rare and the sample was ~90 px of travel. TASKS.md B0-NEW item 10
stays open with that stated.

**TWO METHOD MISTAKES, both worth not repeating:**
- **A frame diff on a scrolling game is meaningless without motion
  compensation.** The first pass flagged every other frame as a 137,000 px
  full-screen change; that was the camera advancing ONE PIXEL. Align on the
  integer camera shift first, then diff. Median residual goes 137k -> 0.
- **The probe created the artefact it found.** `--film-walk` copied
  `--perf-walk`'s collision-off sweep, so the player walked THROUGH a house,
  the roof reveal fired, and the diff flagged it as the biggest event in the
  run. Correct behaviour, manufactured by the test. Collision is on by
  default now; `--film-noclip` opts out. **A test that creates what it looks
  for is worse than no test.**

**Shipped: v0.6.63 - THE ONE-FRAME POP IS FOUND, PROVEN AND FIXED.**

**The bug:** `player.gd` kept `global_position` continuous and pushed the
sprite onto the pixel grid with `_sprite.position = visual_err`, but
**y-sorting sorts on the NODE** - the unsnapped value. So within half a pixel
the player could SORT in front while being DRAWN behind, and that frame
renders in the wrong order. Only while moving, unreproducible, because it
depends on a sub-pixel phase that never repeats.

**Proven, not guessed.** Filming was impractical (real walking speed covers
~560 px in 1400 frames). The theory made an exact prediction, so
`--probe-sort` tested it directly: **1062 disagreements in 2311 near-pair
frames - 46% - max offset exactly 0.5 px. After: 0.**

**The fix's trap:** `global_position` is snapped now, so the sort key IS the
drawn position - but `_true_pos` holds the exact position and is restored
before each move and captured after. Snapping the position and letting the
physics continue from it is the v0.2.1 "low fps walk" bug.

**THREE TIMES THIS SESSION A PROBE REPORTED A PERFECT SCORE WHILE MEASURING
NOTHING**, and each one nearly shipped:
- `--film-walk` copied `--perf-walk`'s collision-off sweep, so the player
  walked THROUGH a house and the diff flagged the roof reveal - correct
  behaviour, manufactured by the test.
- The first frame diff flagged every other frame as a 137,000 px change:
  that was the camera scrolling one pixel. Motion-compensate first.
- `--probe-sort` reported `disagreements=0` TWICE while the player sat
  perfectly still - once because the fix overwrote the probe's teleport, then
  again because it accumulated onto the SNAPPED position, which rounds
  straight back.
**Every probe must report a liveness figure** (travel, count, delta) next to
its verdict, or a zero is unreadable. `--probe-sort` prints `travelled=` for
exactly this reason.

**Shipped: v0.6.64 - the prewarm never actually warmed anything.**
`_prewarm_textures` called `load()` on every PNG **and threw the result
away**, under a comment claiming that did "decode + GPU upload". It does not:
loading fills the resource cache, **the upload happens on first DRAW**. So
the cost it exists to hide was still paid during play, once per texture, the
first time an object carrying it appeared - and never again for that object.
That is the user's remaining symptom verbatim: *"it just appears on my screen
... like it loads on my screen weirdly, but once its loaded then its fine"*,
*"only happens on one thing per time, then it wont happen again on that
object"*. It draws a 1 px sliver of each texture now. Deploy worst frames
measured against the same run without it: **34.3/24.7/21.7/11.1 ms before,
33.6/23.8/21.0/10.6 after** - identical.

**IT HUNG HEADLESS FIRST.** `await RenderingServer.frame_post_draw` never
fires under `--headless`, so the deploy waited forever and `--smoke` said
"world never became ready (30s)". Headless returns early now. **This is the
third time this project has learned that a wait which never resolves reads as
a hang, not an error - and the second time --smoke was the thing that caught
it.** Do not add an `await` on a rendering signal without a headless guard.

**The user confirmed v0.6.63 fixed the OTHER half:** *"it doesnt happen
anymore near my character"*. The sort fix was correct; this was a second,
unrelated cause with a similar description. **Two bugs wearing one report** -
worth remembering before declaring a vague symptom fixed.

**Ruled out by measurement, do not re-suspect it:** the sway shader hashing
its phase off `MODEL_MATRIX` in the vertex stage. 419 frames walking into the
forest, camera-motion compensated: median residual 41 px, max 239, no
outlier. The sway steps smoothly.

**Shipped: v0.6.66 candidates -> v0.6.65 - doors you can see, no two trucks
alike.**
- **A door was painted in its own wall's two colours**, byte-identical, both
  kinds. **The metal one was self-inflicted**: v0.6.54 lifted `brick_b` to fix
  the grey house and landed it exactly on the door. **Changing a wall palette
  means re-checking everything mounted on that wall.**
- **A doorway now counts as inside** for the roof reveal, gated on actually
  standing on a door so it cannot fire from outside a wall.
- **`_pick_variant_norepeat`** - one draw, always, picking over the names
  EXCLUDING the last. `_pick_variant_varied` takes a second draw on a repeat,
  so dropping it into an existing call site re-rolls the fixed district.
  Use the new one when retro-fitting anti-repetition anywhere.

**A CONFLICT WORTH CATCHING: the stairwell hole was BUILT ONCE AND REMOVED
AT THE USER'S REQUEST.** `_build_upper`'s comment records it - *"the
stairwell hole showed the ground and broke it"* - and they have now asked for
it again. The concept is wanted; the old execution failed because the gap
showed the ground room through it. Build it as a dark SHAFT with the stair
top inside and a lip on the near edges, and check one screenshot with them
first. **Reading the comment before coding is what caught this.**

**PICKED UP AT: TASKS.md B0c, the second floor** - the user reported four
distinct things in one message (clipping into the slab, the stair top
visible, clipping on props up there, and wanting a stairwell hole). B0d is a
closed door not sealing at its top edge. Both are written up with the
relevant standing lesson quoted.

**Picked up at: the polish pass, ART half — three of six done.** Shipped this
session: the title (v0.6.51), the map screen redo (v0.6.52), the layout
revision (v0.6.53), terrain blending + house contrast (v0.6.54), the blend
rebuild + four fixes (v0.6.55). **Still untouched: ui and icons, the player model, world
objects and textures.** Engine half still open: wet-ground reflections,
window light spill, heat shimmer. Nothing in progress, nothing blocked, all
gates green.

---

## 2026-08-04 → 08-05 — walls stop light, and the map became a map

*(Amended before the final push, which is the rule this file learned the hard
way: an entry written mid-session goes stale the instant the session carries
on. It was written at v0.6.45 and v0.6.46 shipped after it.)*

**Also shipped: v0.6.46 — the map screen**, item 1 of the art half and the
one the user sees every raid. It was flat coloured rectangles with a bare
word on each place — *"its like some minecraft map"*. It is a drawn chart
now: aged paper, a ruled ink border, roads CASED with a pale channel inside
an ink stroke, the woods HATCHED instead of blobbed, the rail a ladder, the
wire a broken red ink line, and **a drawn symbol for every place** (bus,
crane, chimney, swing, mast, boom, fountain, boxcar, picture frame, H pad,
bell, and a red home for the safehouse).

**Three defects in it that only showed up by shooting it and looking** — the
same lesson as the birds, and it is cheap to relearn badly:
- the town blocks were a SOLID fill covering nearly the whole sheet, so the
  paper only survived as margins. Brown boxes with pale gaps — the exact
  "diagram" read being fixed. A 45% tint now.
- the vehicle labels turned on at zoom 3.0 **and the map opens at ~3.6**, so
  all ~33 printed at once and carpeted it. Threshold is 7.0 now.
- the safehouse's name printed under the live "me" marker, because you spawn
  on it. It has no name now; the red home glyph and ring carry it.

**One deliberate deviation, flagged so nobody thinks it was missed:** the
brief said a glyph *instead of* a text label. It got the glyph **and** the
name — a symbol with no toponym is unreadable until the set is memorised, and
real drawn maps carry both. Regions take the name only. Trivial to make
literal if the user wants it.

**Shipped: v0.6.45.** Real 2D shadows — the biggest item left on the visual
polish pass. `LightOccluder2D` on every building wall segment, built off the
cell EDGE the wall art already occupies, merged into one occluder per
contiguous RUN (+113 nodes, not ~330). The door carries its own, toggled in
lockstep with its collider off the same manifest polygon. Lamps, interior
lights, the flashlight and headlights all cast. **This closed B7** — the
flashlight no longer shines through walls — and closed the same leak on
interior room lights, which had been hiding it behind a small radius.

**The user's words** (whole day in `docs/sessions/2026-08-04.md`):
- *"im here for migration for my spoils gam"* — the migration was clean:
  both gates green, tree clean, tag and remote in sync at v0.6.44.
- *"the visual polish pass isnt done yet is it?"* — correct, and worth being
  blunt about: the ENGINE half was about half done and the **ART half had
  not been started at all** (map screen, map tile, title, ui/icons, player
  model, world objects — zero of six).
- *"sure pick whatever you want just finish the polish pass"*, then
  *"lets not do the screenshot thing, just finish the polish pass please"*,
  then *"you dont need to do one item per version either"*, then
  *"ship whenever you think its a good time for it"*.
  **They waived the one-family-per-version + screenshot sign-off rule for
  THIS PASS.** I raised it once, they reaffirmed twice, and that is their
  call. Do NOT read it as a permanent repeal of the sample → sign-off → fleet
  rule; it was scoped to finishing this pass.

**Learned:**
- **GLOW/BLOOM VIA `WorldEnvironment` DOES NOT WORK HERE. Built it, measured
  it, threw it away** — and the numbers are in TASKS.md so nobody retries it
  blind. Godot's 2D glow is a **no-op unless `rendering/viewport/hdr_2d` is
  on**: a glowing frame and a non-glowing frame came out **byte-identical**.
  Turn `hdr_2d` on and the canvas renders in linear space — the tuned night
  went **near-black** and fps fell **240 -> 183**. TASKS.md had recommended
  it on the grounds that "the renderer is Forward+, so it is available".
  Available is not the same as viable.
- **The occluder must be an OPEN polyline.** `closed = true` fills the
  building solid and blacks out its own interior.
- **Measure the light, do not look at it.** The flashlight fix was confirmed
  with a brightness scan straight out through the cone — 90-334 inside the
  shell, a flat 52-56 (pure ambient) across the whole street beyond. The
  first lamp shot LOOKED like it had no shadow; it was simply too far from
  the house to cast one. Nearly wrote that up as a bug.

**Wrong prose found and fixed (fourth session running, both gates green
throughout):** `CLAUDE.md`'s OPEN DECISIONS said *"which menu backdrops to
build … nothing is painted right now"* and TASKS.md said *"which menu
backdrops to keep, once all five are painted"*. **Both false for fourteen
releases** — all six are painted, shipped and living since v0.6.35, and
CLAUDE.md's own systems map says so three sections above its own wrong line.
A fresh session would have asked the user to re-decide something they settled
on 2026-08-02. Both deleted.

**Also shipped: v0.6.47 — two structural fixes, on the user's explicit green
light** (*"i give you clear creative direction, validation, and the green
light to fix any structural issues you find. build anything you want"*):

- **`--checkclaims`, the numbers gate.** `--checkdocs` cannot verify a
  sentence — but **the sentences that rot here are overwhelmingly NUMERIC**,
  and a number is checkable. It reads each claim out of CLAUDE.md's own prose
  (no duplicated copy to drift) and compares it against the constant the game
  really uses, read at runtime off `WorldBuilder`/`EnvironmentSystem` rather
  than regexed out of source. Covers the day length, `DAY_SECONDS`,
  `BARRIER_INSET`, `MAP_W`, `DISTRICT_SEED`. Runs inside `--smoke`.
  **It FAILS CLOSED** — reword a sentence so its number stops parsing and you
  get a failure naming the pattern. All five claims AND the fail-closed path
  were fire-tested by planting real violations; CLAUDE.md was restored
  byte-identical afterwards, verified with `git diff`.
- **The headless log is quiet.** ~50 `Not supported by this display server`
  blocks per run, all from `Settings.bind_label` asking headless to translate
  a physical keycode. **50 → 0.** That noise is why the docs had to tell every
  session to check the HEAD of the log for `Parse Error` — it buried real
  errors. **If a future session sees that spam again, the guard has been
  removed; do not re-adapt the docs around it.**

**Also shipped: v0.6.48 — the player's shadow follows the sun.** Thrown away
from it, leaning with it, long at dawn and dusk, almost nothing at midday,
faded to a soft contact patch under cloud or at night. Rides main.gd's
EXISTING clock read (the one already feeding the grade and the shafts), so
the clock is read once. Verified at three times of day rather than eyeballed
once — left at 07:00, under the feet at 13:00, right at 19:55.

**And a TASKS.md claim disproved while doing it:** it said "everything shares
one static blob now". **Wrong.** `shadow.png` has exactly ONE user in the
project — `player.gd`. **Props have no shadow node at all**; their shading is
baked into the art. So prop cast shadows are a NEW SYSTEM, not a tweak, and
the naive version (a sprite per prop) costs thousands of nodes against a
~8.0k budget. Left undone deliberately and written up as such — that is a
cost decision the user should make, not one to slip into a polish batch.

**Also shipped: v0.6.49 — foliage sway.** Every tree and bush leans, trunk
pinned, crown moving, each on its own clock. Whole-pixel UV shift in the
FRAGMENT stage (a vertex shear samples off-axis and raggeds every column).
**Zero new nodes and two materials district-wide**, because the per-instance
phase is hashed from the instance's world position in the vertex stage rather
than stored per tree — which also means **no rng draw**, and an extra draw
would have re-rolled the FIXED district. Filmed to verify, not screenshotted.
240 fps in the forest and on a storm night.

**And a prop contact-shadow attempt that was BUILT, MEASURED AND BACKED OUT**
(user: *"just leave the props how they are but is there not another way to
make them look better?"*). Props genuinely cast nothing — confirmed three
ways, the old TASKS.md line "everything shares one static blob" was false.
The one-node custom `_draw()` architecture is free and should be reused; what
killed it was OVERLAP — clustered props stack semi-transparent blobs and they
compound into a grey smear. Full write-up with a starting point is in
TASKS.md. **Do not re-attempt it by just lowering the alpha.**

**Also shipped: v0.6.50 — the map-select tile.** A painted dusk vista of the
district at EXACTLY 120x120 (the button size, so nothing resamples it),
replacing a 96x96 top-down diagram that Godot stretched 1.25x. Spires, low
sun, lit windows, comms mast, treeline, rail, and the wire in silhouette
across the foreground. **Two already-recorded lessons were relearned the hard
way while drawing it:** a treeline built from `abs(sin(x))` came out a regular
SAWTOOTH that reads as a mountain range (rebuilt from overlapping crowns —
never build a natural silhouette from a periodic function), and the chain-link
mesh at `10141f` on an `090a14` fence was four values apart so the whole fence
read as a black bar. **Both are in this file already. Read the lessons before
drawing, not after.**

**Picked up at: THE POLISH PASS IS NOT FINISHED — see TASKS.md section A.**
Six versions shipped this session, v0.6.45 → v0.6.50.

- **ENGINE HALF — done bar three small items.** Shipped: wall occluder
  shadows (+ B7), the player's sun-tracking shadow, foliage sway. Built,
  measured and REJECTED: glow/bloom, and prop contact shadows. Still open:
  **wet-ground reflections, window light spill, heat shimmer.**
- **ART HALF — two of six.** Shipped: the map screen (v0.6.46), the
  map-select tile (v0.6.50). **Still untouched: the title, ui and icons, the
  player model, world objects and textures.** Each is a real job in an
  18,000-line generator, not a tweak — do not read "finish the pass" as a
  short list.
- **NEXT UP was THE TITLE** (*"its just white, and it goes up and down a bit
  thats all, it seems boring"*), TASKS.md section A item 3.

**Nothing is in progress and nothing is blocked.** Tree clean, everything
pushed, **all gates green at v0.6.50** (`SEC PASS`, `DOCS PASS`,
`CLAIMS PASS`, `SMOKE PASS`), 240 fps held in every case measured — forest at
midday 4.63 ms, storm night 4.79 ms, map open over a live raid 4.61 ms, nodes
~8.0k. Some untracked debug shots sit in `shots/`; they were deliberately not
committed (see C7, repo weight) and can be deleted freely.

**Two process failures worth not repeating.** A chained `git tag` fired twice
while the command before it had failed, landing the tag on the PREVIOUS
release's commit both times — caught by `git tag --points-at HEAD` before
pushing, undone with `git tag -d`. **Tag on its own line, and verify before
pushing.** And a commit message with double quotes inside a PowerShell
here-string split the argument, exactly as this file already warns: **use
`git commit -F`, always.**

---

## 2026-08-02 → 08-03 — every backdrop made to move, and four bugs that hid

**Shipped: v0.6.32 → v0.6.44, thirteen releases, plus a README rewrite.**
Living layers for all six menu backdrops (yard, warden, underpass, counter —
den and drain already had one), then a second pass making them **noticeable**
on the user's push. Menu rain rebuilt on the raid's own model. The underpass
door, its wired glass and two lore notices. Mara's arms, pencil and den
silhouette; kettle's beard. A new `--film` harness mode. `gen_art` made
crash-safe. Every base painting stayed byte-identical except where a change
was explicitly asked for, and each of those diffs is quoted in `CHANGELOG.md`.

**The user's words** (the whole day is in `docs/sessions/2026-08-03.md`):
- *"these living layers are very minimal, can we add some more to it, to every
  backdrop, i want it to be noticable"*
- *"dont just amp up the current ones, find new ones on the screen and create
  some, like some flcikering lights, or some pole lines sparks coming off
  them"* — **this is the sharper half of the brief and the one to keep.**
- *"i dont see any rat"* / *"the birds arent moving, they are in the same spot
  the whole time"* / *"they are on the thing on the right, they should be in
  the sky"*
- *"i meant like the actual raindrops coming down on the screen should
  physically hit something on the screen, so remove that water stuff on the
  ground and do what i wanted"* — *"we already have that system in our raids"*
- *"lets keep both the backdrops for now, no harm"* (on the drain/underpass
  camera angles being similar — they ARE, it is a base-art issue, not acted on)
- *"and about that rule, what if the fix needs more rebuild in order to work?"*
  → answered: **the rule is not "never rebuild more", it is "never rebuild more
  SILENTLY". Say what will move, get a yes, then prove the rest did not.**
- *"also make mara skinnier in the den backdrop"*, *"give kettle a beard"*,
  *"make a rectangle see through glass on there and show some blood splatter"*
- *"ill tell you when to be scarce"* — do not self-ration context unasked.

**Learned. Every one of these is now a standing rule in `CLAUDE.md`** — go
there for the full text, this is the index:
- **Never round a position you then read back to accumulate.** Killed the birds
  AND the rat: at 240 fps a 34 px/s walk is 0.14 px a frame and the round puts
  it straight back. Both read as "it isn't there", not as a rounding bug.
- **Every new element must beat the background it lands on — measured.** Failed
  four times in a day (far signal eye, underpass drip, rat, birds).
- **Check whether the UI is on top of it.** The birds flew at screen row 464,
  inside the "play" button.
- **`modulate` MULTIPLIES**, so "force it bright to see if it renders" does not
  work on a dark sprite. Swap the TEXTURE instead.
- **Do not answer "why is X not showing" with a theory. Measure.** I gave two
  confident wrong answers about the birds and the user rejected both, correctly.
  And you cannot diff a shot against the BAKE for this — the vignette darkens
  everything and swamps the signal. Diff CONSECUTIVE FILM FRAMES.
- **Delete the indirection rather than bisecting it.** The birds only worked
  once the two-state + gate logic was thrown away for one flat loop.
- **Release order: bump docs → commit → TAG → smoke → push** (user's call).
- **`gen_art` deletes before it writes** — fixed in v0.6.44 so it purges at the
  END, proven by planting a crash (528 PNGs before, 528 after).

**What went wrong that is worth saying plainly:** the birds cost most of a
session — four wrong explanations, an invalid test, and several scans that
measured wires and rain instead of birds — before anyone cropped the flight
path and looked at it. **Looking should have been the first move, not the
fifth.**

**And the docs lied twice while both gates printed PASS** (third session
running): `DESIGN.md` still described a TWO-backdrop menu with the others as
unwired pitches, thirteen releases out of date; `CLAUDE.md`'s menu node count
still read ~818 when it is 1717 (not a leak — ~740 of those are rain sprites).
Both fixed. A check cannot verify a sentence.

**Two things the user DEFERRED on purpose — they are in `TASKS.md` as C6 and
C7, and NEITHER blocks a migration:** a **full doc sweep** (*"the sweep will
happen later"* — only menu-related claims were checked on 08-03, and two of
those were wrong, so assume more stale prose elsewhere) and **repo weight**
(*"i will optimize the repo later too"* — `shots/` is 373 files / 77 MB and
`.git` is 109 MB; 57 files landed in one day of debug captures).

**Picked up at: NOTHING IS IN PROGRESS.** Tree clean, everything pushed, all
gates green at v0.6.44, leaks flat, 240 fps in a raid and 245 on every menu
backdrop. `TASKS.md` is accurate and is the work list. The two most useful
next moves are **B4, the smoker on the bench** (small, queued longest) or
**real 2D shadows** (biggest visual change left, and it kills the
flashlight-through-walls bug at the same time). **M2 — guns — still waits on
the user's explicit "go".** One open note nobody has acted on: the drain and
the underpass share a camera angle and the user has parked it deliberately.

---


## 2026-08-02 — four backdrops auditioned, and the den and drain repainted

**Shipped:** **v0.6.28** (the migration audit — see the entry below),
**v0.6.29** (both shipped menu backdrops repainted) and **v0.6.30** (the four
candidate backdrops promoted into the game — **the menu now rotates SIX**).

*(This paragraph originally ended "the menu still rotates den + drain only",
which was true when it was written and false ninety minutes later. Amended
before the push rather than left to rot — that is the correction to the
mid-session-staleness lesson recorded three entries down, and it is the whole
point of it.)*

**On the six:** all four were promoted **byte-identical** to the versions the
user approved — hashes checked both ways, because a promotion that quietly
re-rolls a painting would undo many rounds of their review. Rotation is a
**shuffle bag at 10 s** (`_bag_next`/`_bag_reset` in `main_menu.gd`; shipped
at 30 s in v0.6.30, dropped to 10 on a user call in v0.6.31), with the
seam case closed: a refill that would put the on-screen scene up next swaps it
away, so nothing repeats back to back. Hand-rolled Fisher-Yates because
`Array.shuffle()` is banned project-wide, and deliberately UNSEEDED — the menu
should differ every launch, unlike the fixed district. **Indices 2-5 are still
STATIC**; their living layers are the next version.

**The user's words:** *"im here for the migration"*, then on the gap:
*"Why does the handoff have a gap? I just had the last session spend like 2
hours fixing and making sure the migration would all be clean and working"*.
On the one pitch anyone had painted: *"yes just drop it"*. On choosing:
*"show me the pitches again and what the living layer would be, I will pick a
couple and we make them"*. On the tally: *"nobody is dying out there anymore
it's just me so the tally amount can stay the same forever"*, then *"there's
too many tallies on both the screens let's half the amount of both"*. On a
fix that made things worse: *"this fix is probably worse than how we had it
before, the arms and hands are all messed up"*. On the shipped scenes:
*"can you upgrade the den and the drain paintings a bit to like match all of
these 4"*, *"yes a redesign would be good too for these that's what I meant"*,
and *"the blue and the brown areas of the screen is too much, like all the
colours of the screen should be blended together nicely"*.

**Learned:**
- **PARALLEL AGENTS MUST NEVER RUN REPO-WIDE GIT.** Twice today an agent ran
  `git stash` / snapshot-and-restore on a file another agent was editing.
  **Nothing was lost either time** — verified by hashing — but only by luck.
  Every agent prompt now forbids `git stash/checkout/reset`; read-only git is
  fine. When agents run in parallel, give each ONE file and say so.
- **A FIX THAT REBUILDS MORE THAN WAS COMPLAINED ABOUT WILL BE REJECTED.** The
  shoulder pass rebuilt the whole limb system to fix "shoulders look cropped",
  which moved the arms and detached the hands. Reverted, then redone with a
  hard constraint AND A PROOF: hands pixel-identical, arm centrelines fixed,
  only the width profile and the outer silhouette may change. It worked.
  **Constrain the fix to the complaint and prove the rest is untouched.**
- **AMBIGUOUS SHAPES GET READ AS WHATEVER THE BRAIN SUPPLIES.** A downpipe read
  as "the back of a car". A shoulder read as a hooded figure. A light spill on
  wet tarmac read as **a dead body in blood** — the user asked outright.
  Every time the cure was the same: give the object a lit face, a shade face
  and a visible connection to something. **Light with no visible path back to
  its source cannot read as light; it reads as a stain.**
- **A THING CAN BE DRAWN AND INVISIBLE.** The car tarp's fill was `151d28` and
  the sky behind it is also `151d28`, so two thirds of it never showed and all
  that read was a 3 px rib — a bandstand hoop. Check a fill against what is
  BEHIND it, not just against its own neighbours.
- **DO NOT BUMP THE VERSION BEFORE THE WORK IS FINISHED.** I bumped to v0.6.29
  early; the user then found a problem, and the repo sat RED (`DOCS FAIL`, tag
  lag) while it was fixed. Bump at commit time.
- **I got two things wrong that cost agent runs.** I called the den's VU meter
  needles "kettle's knitting needles" and nearly had an agent pin kettle's
  hands to coordinates on the opposite side of the frame; and I sent the tarp
  fix to `yard.py`, which has no tarp (that agent correctly changed nothing
  rather than inventing one). **Verify what an anchor IS before briefing it.**
- **The den's two-tone was a hard `if warm >= cool` switch**, and that switch
  WAS the visible boundary. One shared neutral ramp that both lamps tint at the
  same value is what makes two lights read as one room.
- Smooth lump functions render as mountain ranges: a smooth function has one
  highest point, and one highest point in a 10 px silhouette is a peak.

**Picked up at:** **THE LIVING LAYERS FOR BACKDROPS 2-5.** The user kept all
four (*"let's add all 4 of those menu backdrops to the game, just like the den
and drain"*), so they are in and rotating, but static. Next version gives them
what den and drain have, using only the five techniques that already exist in
`main_menu.gd` (listed in TASKS.md A1): a breathing additive glow, a 3-frame
sprite swap, a visibility blink on offset timers, dust particles with a fade
ramp, and one travelling sprite that triggers something when it lands. Each
per-scene brief must name the anchor pixel it hangs off and require the base
painting to stay byte-identical — that is one hash instead of a review round.
`tools/pitches/` still holds the four source modules and can be deleted once
the living layers are in. Nothing is blocked. All gates green at v0.6.30.

---

## 2026-08-02 — the chain skipped two releases, and nothing could see it

**Shipped:** **v0.6.28**, plus the record of **v0.6.26 and v0.6.27 that this
file never had**. A third migration audit (6 lenses, 19 candidates, **13
confirmed / 6 refuted** by adversarial verifiers) fixed 13 defects across
CLAUDE.md, TASKS.md, DESIGN.md, CHANGELOG.md and five .gd files. New
**`--checkdocs` part 5**. One real code fix.

**The user's words:** *"im here for the migration"*, then — on being told the
chain had a hole — *"Why does the handoff have a gap? I just had the last
session spend like 2 hours fixing and making sure the migration would all be
clean and working"*. Fair, and the answer was not negligence; see below.

**Learned:**
- **THE GAP, precisely: the last session DID write its entry, on time, at
  `fa00e67` — then worked another ~75 minutes and shipped v0.6.26, v0.6.27
  and three doc commits without ever touching it again.** So the file said
  "still v0.6.25 … tree clean at v0.6.25" while the repo was two releases
  ahead. **An entry written mid-session goes stale the instant the session
  continues.** The entry directly below this one warned about exactly that
  ("a handoff entry written in stages rots exactly like any other doc") and
  it then happened to that very session. Writing early is right; the missing
  half of the rule is **come back and amend before the last push**.
- **No gate could see it, and now one can.** `--checkdocs` read HANDOFF.md
  for dead paths but never for a VERSION. New part 5: the current release
  must be NAMED in HANDOFF.md. **Fire-tested on the real violation** — it
  failed with "HANDOFF.md never mentions v0.6.27" before this entry existed,
  which is a better proof than a planted one. Its honest limit is in the
  code comment: it proves the number is mentioned, never that the entry is
  true.
- **Third audit, third time BOTH GATES WERE GREEN THROUGHOUT.** Stop
  expecting that to change.
- **v0.6.27's changelog OVERCLAIMED ITS OWN BUG, and the overclaim hid a
  real one.** It said dying at the wheel left the car "wedged for the rest
  of the raid" — false: `abandon()` clears `driven`/`_busy` itself two lines
  after nulling `_player`, so the car stayed enterable and the only residue
  was a cosmetic open-door sprite. It also called the two guards "identical"
  and said `enter()` had carried its one "all along" — not identical
  (`enter()` must also test `.dead`), and it arrived in v0.6.43. **Chasing
  that down found the bug the entry had papered over:** `exit_car()` guarded
  only `null`, so F pressed in the ~1.2 s between death and `abandon()`
  stood the corpse up on the pavement. Fixed in v0.6.28.
- **A doc can invent work that was never done.** TASKS.md told every future
  M2 session the gun art was "already generated and waiting" —
  `make_muzzle_flash`, `make_tracer` and `make_impact_frames` have **zero
  call sites**, the save block never emits them, and no such sprite has ever
  existed. It would have sent M2 hunting a manifest key that isn't there.
- **CLAUDE.md commanded work the user had deleted.** Its "VISIBLE POWER
  CABLES" standing rule demanded an interior flex from fixture to power box
  — the exact floor clutter the user had cut ("the cables inside houses are
  gone"). `world_builder.gd` said the same thing directly above the call to
  a function whose own docstring says no cable is drawn.
- **Two more "fix one copy, leave the twin":** CLAUDE.md still said "death
  fade → respawn" (dying ends the raid into the debrief; DESIGN.md had
  already been corrected), and still listed the licensed audio as footsteps
  + thunder only — **the car doors and engine are recordings too**
  (ggbotnet, cc0), with an attribution obligation, stated correctly in four
  other places.

**Picked up at:** **The smoker on the bench (TASKS.md B4)** — still
untouched, still nothing blocked, unchanged from the last three entries.
Rebuild him from the PLAYER's character sheet so his shading matches, black
hat, bigger smoke, seat him on the bench BELOW facing away from the
backrest, move the ground item off his head. Then the LZ green smoke (B4b).

---

## 2026-08-02 — the migration works; the docs still lied in ~50 places

*(compressed — the ritual says entries older than the newest three drop to a
few lines, and every fix below is in the repo now.)* No version bump, still
v0.6.25. **~45 unique defects fixed across 16 files.** Both gates printed PASS
throughout — second audit running. Dominant failure mode: **"fix one copy,
leave the twin"** — the same false fact repeated in another file. All of it was
wrong-FACT, never wrong-ACTION; nothing found could have destroyed data.

## 2026-08-02 — the migration was broken and both gates said PASS

*(compressed.)* No game changes. A docs audit after the user asked for the
migration and the security to be solid. **The two commands at the TOP of
`CLAUDE.md` resolved to nothing on this machine** — `godot_console` was never
on PATH — so the documented workflow was unrunnable while both gates were
green. **One doc instruction would have destroyed user data**: `DESIGN.md`
claimed smoke runs pollute a stash file under `%APPDATA%` and told sessions to
clean it up; that folder holds the user's real keybinds, resolution and
volumes, and there is no stash file. The permanent lesson — **a check cannot
verify prose** — is now its own section in `CLAUDE.md`.

## 2026-08-02 — migration hardening

*(Compressed per entry rule 6.)* No game changes. Built this file, added
`--checkdocs`, then `--checksec` (six enforced invariants, **every one
fire-tested by planting a real violation**), and the SAFETY & TRUST section
in `CLAUDE.md` — all at the user's request: *"i want my game to be secure,
and the migrations to work"*, and they asked for *"a chain of migrations
that we will never forget"*. On permissions they declined full bypass:
*"auto is fine, i can run a couple commands whenever you need me to."*

Still load-bearing: **the renumbering left `v0.6.14` on the wrong commit**
(`f8e83ae` instead of `9c79c9b`) — found, fixed, and now guarded by
`--checkdocs` part 2. **Commit messages still carry PRE-renumber version
numbers**, so never read a version out of a commit subject before
`f8e83ae` — use `git tag --points-at`. And the parse-error-looks-like-a-hang
trap bit again: return TYPED arrays, and read the HEAD of the log.

## 2026-08-02 — overcast, and the docs rebuilt

*(compressed.)* **v0.6.15 → v0.6.25**: OVERCAST weather, a real day-arc, the
boot shader warm-up, indoor weather muffling, and the docs rebuilt around
them. Its renumbering-ORDER claim was wrong and is corrected in a later entry.
