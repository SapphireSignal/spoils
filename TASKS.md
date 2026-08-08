# SPOILS — open work

Everything outstanding, with the diagnosis already done where there is
one. **Read `CLAUDE.md` first** (project rules, systems map, verification
workflow), then this file for what to actually build. `CHANGELOG.md`
records what already shipped.

**Current version: v0.6.96.** The release history was renumbered evenly on
2026-08-02 — read the versioning note in CLAUDE.md before quoting any old
version number, because they were all remapped.

Ordered by priority. The user playtests and reacts; items marked *(user)*
came straight from them.

---

# A. THE VISUAL POLISH PASS (the big current direction)

The user wants the whole game to look markedly better while staying pixel
art: *"the ui, the icons, the in game stuff as well, like the player
model, the textures, the objects, everything all visually appealing but
still keeping that pixel look."*

**HOW THIS RUNS — do not batch it.** One family at a time, each shipped as
its own version with a screenshot, so a direction they dislike costs one
version instead of five. This is the sample → sign-off → fleet rule that
saved the 8-direction vehicles. Reverting is exact: all art is generated
from code, so `git revert <tag>` restores the old sprites byte for byte,
and each family ships separately so disliking one does not cost the rest.

**ALREADY SHIPPED from this pass** (v0.6.17-v0.6.25): camera kick,
hit-stop and a per-sprite hit flash; a full-screen colour grade; dust in
the air; sun shafts tied to the clock; rain and thunder muffled indoors;
a boot shader warm-up; a real day-arc (07:30-17:00 used to be one flat
light); and OVERCAST weather so a dry day isn't automatically a sunny one.

**STILL TO DO, biggest first:**

- **Real 2D shadows — DONE in v0.6.45.** `LightOccluder2D` runs on the wall
  segments, built in `_build_shell` from the cell EDGE the wall art already
  occupies. One occluder per contiguous RUN, not per segment (+113 nodes,
  not ~330), and a gap in the wall breaks the run so light spills through a
  doorway or a blown-out ruin corner. The door carries its own, toggled in
  lockstep with its collider off the same manifest polygon. Lamps, interior
  lights, the flashlight and car headlights all cast. **This closed B7 too.**

- **Glow / bloom — ATTEMPTED AND REJECTED, with numbers. Do not retry it
  blind.** This item used to read "via a `WorldEnvironment`; the renderer is
  Forward+, so it is available". It is available and it does not work here:
  - Godot's 2D glow is a **no-op unless `rendering/viewport/hdr_2d` is on**.
    Measured: a WorldEnvironment with glow enabled and the threshold at 0.85
    produced a frame **byte-identical** to one with no glow at all.
  - Turning `hdr_2d` on re-renders the canvas in linear space. The tuned
    night went **near-black** — the whole day/night gradient, the grade and
    every light energy are authored for sRGB — and the frame rate fell
    **240 -> 183 fps**. Both were shot and measured, not estimated.
  - Making it work means re-tuning the day arc, `grade.gdshader` and every
    light energy against a linear pipeline, then paying that 24% anyway. That
    is a re-tune of work the user has already signed off, not a polish pass.
  - **The intent is still worth delivering** — "lamps, lit windows and sparks
    should bleed light instead of being flat bright pixels" — via **additive
    glow sprites**, the way `lamp_glow.png` already works on lamps and
    interior lights. Costs nothing, cannot smear the pixel grid, and is
    per-object controllable. Lit WINDOWS are the obvious next customer.
- **Directional cast shadows — THE PLAYER IS DONE (v0.6.48). PROPS ARE NOT,
  and that is a decision, not an oversight.**

  The player's shadow is thrown away from the sun, leans with it, stretches
  as the sun drops and shrinks to almost nothing at midday, and fades to a
  soft contact darkening at night or under heavy cloud. Driven from
  `main.gd`'s existing clock read (the one that already feeds the grade and
  the sun shafts), so the clock is read once, not twice. Verified across
  three times of day: thrown LEFT at 07:00, compact under the feet at 13:00,
  thrown RIGHT at 19:55.

  It is legal under the no-runtime-transform rule because the blob is a
  SOFT-ALPHA texture — the same carve-out the LZ beacon's ground wash and the
  freight's steam already use. The throw is still rounded to whole pixels,
  because it slides under a sprite that is itself parked on the grid.

  **PROPS HAVE NO SHADOW NODE AT ALL.** This task said "everything shares one
  static blob"; that was wrong. `shadow.png` has exactly ONE user in the
  whole project — `player.gd`. Prop shading is baked into the art. So giving
  props cast shadows is not a tweak to an existing system, it is a new one,
  and the obvious version (a Sprite2D per prop) would add **thousands** of
  nodes against a ~8.0k budget. **It needs the shader route below, and it
  needs a deliberate decision about cost — do not start it casually.**

  **THE PREMISE WAS CHECKED BEFORE STARTING (2026-08-05) AND IT IS NOT WHAT
  YOU WOULD ASSUME. Read this before writing a line of the PROP version:**
  - **Godot 2D has no sun / directional light that casts shadows.** Still an
    open engine issue (godotengine/godot#25486). So this CANNOT come from a
    `Light2D`, and it is not an extension of the v0.6.45 wall occluders.
  - **In isometric specifically, occluder shadows project across a wall as
    if it were not there** — a wall sprite has no height as far as the engine
    is concerned. So adding `LightOccluder2D` to props would produce a flat,
    wrong-looking result. The wall occluders are the right tool for BLOCKING
    light and the wrong tool for CASTING a prop's shadow.
  - **The real mechanism is `SHADOW_VERTEX`**, a CanvasItem shader built-in
    that displaces shadow geometry: you shear a sprite's shadow by the sun
    angle. It is a shader, it moves in whole pixels, and it needs no runtime
    rotation or scale — so it fits the standing pixel-grid rules.
  - Sources: the Godot 2D lights and shadows docs, godotshaders' "2D cast
    shadow", and Connor Wolf's write-up on isometric lighting in 4.4.
- **Wet-ground reflections** in rain; **window light spill** onto pavement at
  night; **heat shimmer** at midday.

- **Contact shadows so props sit in the world rather than on it — ATTEMPTED
  2026-08-05, BUILT, MEASURED AND BACKED OUT. Read this before retrying: the
  architecture was right and the TUNING is what failed.**

  **The problem is real and confirmed.** Props cast nothing at all, verified
  three ways: `shadow.png` has exactly ONE loader in the project
  (`player.gd`), `_add_prop` builds only a Sprite2D plus an optional collider
  with no shadow child, and a midday crop of open pavement shows a planter
  and a vending machine with no darkening under them whatever. They read as
  pasted on rather than standing there.

  **The cheap architecture WORKS — reuse it.** Not a Sprite2D per prop; that
  is thousands of nodes against a ~8.0k budget for something that never
  moves. One `Node2D` with a custom `_draw()` that draws every blob is **1
  node**, `_draw` runs once, the renderer caches it, per-frame cost nil.

  **What actually killed it: OVERLAP.** Clustered props — `_place_pile` puts
  an anchor plus thinning satellites — stack their blobs, and semi-transparent
  shadows COMPOUND where they overlap. Four on top of each other read as one
  grey rectangular smear, not as four things sitting on the ground.

  **Two findings worth keeping:**
  - **Integer scale only.** Sizing the blob continuously off the footprint
    stretched the 24x12 texture to ~67x34 — a 2.8x nearest-neighbour blow-up
    that lands blocks of uneven size and reads as a slab. This game renders
    on an integer pixel ladder and its shadows have to as well.
  - **The footprints are SMALL, so the native blob is already about right.**
    `planter_0` is `['diamond', 10.0, 5.0]`, `barrel_0` is `['circle', 9.0]`.
    Sizing was never the problem.

  **Where to start next time:** gate on footprint so small clutter takes no
  shadow at all — that alone removes most of the soup — and/or composite the
  layer with MAX alpha instead of letting overlaps accumulate, so a cluster
  gets one merged silhouette rather than four stacked blobs. Note
  `shadow.png` is a 24x12 ellipse whose own peak alpha is only ~50%, so it is
  already faint: the fix is NOT simply turning the alpha down further.
- **Sway shader on bushes and trees — DONE in v0.6.49.** A whole-pixel
  horizontal offset, never a rotation, exactly as specced.
  `scripts/sway.gdshader`, applied in `_add_prop` by PREFIX (`tree_`,
  `bush_` — note `street_lamp` CONTAINS "tree", so a substring test would
  have every lamp post waving).
  - It works in the FRAGMENT stage. A vertex shear moves the quad's corners
    and the texture is then sampled off-axis, which raggeds every column;
    shifting the UV by an INTEGER number of texels moves whole rows instead,
    so nothing is ever resampled.
  - The base is pinned and only the crown moves (`base_hold`), or the whole
    tree slides sideways and reads as a rendering fault rather than wind.
  - **The phase comes from the instance's own world position**, hashed in the
    vertex stage and passed down as a varying — so every tree is on its own
    clock from ONE SHARED MATERIAL. That is why it adds **zero nodes** and
    two materials rather than one per tree. It also takes **no rng draw**,
    which matters more than it looks: the district is FIXED, and an extra
    draw from the builder's rng would re-roll the whole map.
  - Verified by FILM, not by a still — a still cannot show motion. Canopies
    shift between consecutive frames, trunks do not, edges stay crisp.
  - Perf: **240 fps** in the forest at midday (worst frame 4.63 ms) and on a
    storm night (4.79 ms), nodes unchanged at ~8.0k.
- NOT recommended: depth of field, chromatic aberration, motion blur.
  They fight pixel art and just smear it.

Agreed order for the remaining art work:

1. **The in-game map screen (M) — REDONE in v0.6.52. v0.6.46 built the wrong
   thing and this entry is kept as the record of it.**

   v0.6.46 (below) chased *"its like some minecraft map"* and landed on a
   surveyor's paper chart. The user rejected it outright: *"the in game map
   looks like an actual map that youd hold, i dont want it like that, i want
   there to be colour on there, the trees are just lines in there too, and all
   the roads are the same size oin the map, all the pois are like in the same
   spot ... the map just looks like squares and lines, doesnt look like an
   actual map. remember i dont want a real looking map i just want it to look
   like a good real map that youd see in other video games"*

   **THE LESSON, and it is the useful part:** v0.6.46 answered "this reads as
   a diagram" with *"make it look hand-drawn"*. The real problem was that
   everything was the SAME — one hue, one road width, one marker treatment.
   **Sameness is what reads as a diagram, not colour.** The paper look then
   made it worse by forcing every element into one sepia family.

   v0.6.52: terrain coloured by what it is, woods as canopy masses with a
   light direction, a road hierarchy off the SPAN (through routes wide and
   bright with a centre line, stubs narrow and dull — the world really does
   make every road 4 cells wide, so span is the only honest hierarchy in the
   data), markers keyed to what a place is FOR, and ground mottle hashed off
   the cell.

   **Two measurements worth keeping:**
   - **`antialiased: true` on `draw_circle` is the expensive thing here.**
     The rebuild cost 240 -> 210 fps and 4.61 -> 7.09 ms worst frame with the
     map open over a live raid; turning AA off on the grove and mottle circles
     restored 240.0 fps / 4.45 ms with no visible difference. **The district
     layer is re-rasterised every frame even though its draw callback only
     runs on pan and zoom**, so primitive count there is a per-frame cost, not
     a one-off.
   - **Patch size decides whether mottle reads as texture or as a fault.** At
     1.6-4.3 cells across it looked like grey smudges drifting over the
     district. Under a cell, it reads as ground.

## A1b. The district layout — DONE in v0.6.53 *(user-approved map revision)*

The user asked for it directly: **"yeah but just by a little bit, like you can
move it a couple centimeters around. currently its like perfect, the raods,
the pois"**. Road pitch was a flat 36 cells with +/-4 jitter (4% — invisible),
and every POI was placed with exact arithmetic: `_court_rect` dead centre,
`_corner_pos` at exactly +1 into a corner, `_playground` flush at +2 both
sides. Now 40/33/33 and 41/33/36, and the POIs sit off their marks.

**THE SEED DID NOT CHANGE.** `DISTRICT_SEED` is still `"transit-01"`, so any
capture from before 2026-08-05 shows a different district than the same seed
builds now.

**HOW IT COST THE LAYOUT RNG ZERO DRAWS, which is the whole reason the
district did not reroll:** every nudge reads `_side_rng` (roads) or a local
RNG seeded off `DISTRICT_SEED` plus a per-place key (POIs). A single `_rng`
draw here would have re-rolled every block assignment, plot and prop after it
— a new map, which is not what was asked for.

**THE MEASUREMENTS, because three of the four attempts broke something:**
- **`--probe-world`'s DOORS count is the cheapest detector of the
  squeezed-block bug.** Baseline 15. First attempt: **10**. The blocks between
  the roads ARE the districts and a narrow one fits fewer house plots.
- **The courtyard nudge alone cost TWO houses** (15 -> 13), isolated by
  neutralising it on its own. The ring of plots is laid around it, so shifting
  it three cells squeezes one side below a plot width. **It was reverted and
  the courtyard stays dead centre** — a town square being central is also just
  correct. Do not re-attempt it without re-probing DOORS.
- **`MIN_PITCH` is what makes a wide nudge safe.** Rolling each road
  independently at +/-7 could bring two 14 cells together. Clamping every road
  to a minimum pitch from its neighbours after the roll (forward pass, then a
  backward pass so overflow does not pile onto the barricade) holds the block
  floor. NUDGE 5 / MIN_PITCH 33 lands DOORS at **16**, one better than
  baseline.
- Verified beyond the probe: `SMOKE PASS`, 240 fps / 4.62 ms, UPPERS 6 with
  floorless=0 propless=0, and **all three extractions re-checked because they
  moved** — toll gate dialogue opens, LZ counts down on its pad, rail line
  intact. The safehouse did not move ([174, 73]).

### the v0.6.46 chart (superseded, kept for the record)
1. **The in-game map screen (M) — DONE in v0.6.46.**
   *(user: "its like some minecraft map")* Rebuilt as a drawn chart:
   aged-paper sheet with a ruled ink border, roads CASED (an ink stroke with
   a pale channel inside), **woods hatched** with short diagonal strokes
   instead of filled blobs, the rail a ladder, the wire a broken red ink
   line, and **every place carries its own drawn symbol** — a bus, a crane
   and hook, a shed and chimney, a swing, a mast with signal arcs, a boom, a
   fountain, a boxcar, a framed picture, an H pad, a schoolhouse bell, and a
   red home marker for the safehouse.

   **Three things learned doing it, all found by shooting it and looking:**
   - The town blocks were drawn as a SOLID fill and covered nearly the whole
     sheet, so the paper only survived as margins — brown boxes with pale
     gaps, which is the same "diagram" read the user complained about. They
     are a 45% tint now.
   - The vehicle name labels turned on at `_zoom >= 3.0` **and the map opens
     at ~3.6**, so all ~33 of them printed at once and carpeted the map. The
     dots already say "a vehicle is here"; the threshold is 7.0 now.
   - The safehouse gets NO text label. You spawn on it, so the live "me"
     marker sat on top of its name for the first stretch of every raid. Its
     red home glyph and the red ring round its footprint are unmistakable
     without it, and the hover blurb still names it.

   **One deliberate deviation from the brief above:** it said each POI gets a
   glyph *instead of* a text label. It got the glyph **and** the name,
   because a symbol with no toponym is unreadable until you have memorised
   the set — and that is how real drawn maps do it. Regions (town, forest,
   warehouse, trainyard) get the name only, with no symbol, which is also the
   cartographic convention and stops a zone's several rects carpeting the
   sheet with repeats. Easy to change if the user wants it literal.
2. **The map-select tile — DONE in v0.6.50.** *(user: "an actual picture of
   the map from a scenic view, very detailed")* It was a 96×96 top-down
   diamond of grid lines and blobs, stretched 1.25× into a 120×120 button —
   blurred as well as dull. It is now a **painted dusk vista at exactly
   120×120**, so it maps 1:1 and no scaling touches it: banded cel sky with
   wavy seams, the spires on the horizon, the low sun, the town's roofs with
   lit windows, the comms mast and its red light, a treeline, the rail, and
   **the wire in silhouette across the foreground** — the district's whole
   premise as the nearest thing in frame.

   **Two defects caught by looking at it, both already-known lessons:**
   - The treeline was first built from `abs(sin(x))`, which gave a regular
     **sawtooth that reads as a mountain range** — the exact failure recorded
     in HANDOFF.md. Rebuilt from overlapping crowns of varying width and
     height. **Never build a natural silhouette from a periodic function.**
   - The chain-link mesh was `10141f` on a `090a14` fence — four values apart,
     so the whole fence read as a black bar. Every new element must beat the
     background it lands on, measured, not assumed.

   Verified only `menu_map_transit.png` changed in `art/gen` — the generator
   rewrites everything, so that check is what proves no other art moved.
3. **The title — DONE in v0.6.51.** *(user: "its just white, and it goes up
   and down a bit thats all, it seems boring")* Both halves of that were
   real and both were fixed.

   **"just white"** — it was the 1× font blown up 7×, two flat tones split by
   a hard seam across every letter, five colours in the whole image. The
   blow-up was the root cause: every edge was a 7 px slab while the rest of
   the menu renders at 1 px, so it read as a placeholder pasted over finished
   art. The letterforms still come from the game's own font (rule 2 — it is
   the only lowercase cut), but the DETAIL is native resolution now: a banded
   cel gradient with wavy seams, 1 px lit and shaded rims, chamfered corners
   so the silhouette is not an 8 px staircase, directional weathering, and a
   real extrusion so the letters have thickness.

   **"goes up and down a bit thats all"** — `scripts/gleam.gdshader`. The old
   gleam was a 34 px `clip_contents` Control sliding a flat silver copy
   across: a hard-edged vertical bar, and **idle 5.1 seconds out of every 6**.
   Now a wide dim band drifts continuously and a bright one sweeps
   diagonally every six seconds. The bob went 1.3 → 0.6 rad/s; letters that
   heavy should not bounce.

   **Two things worth keeping from it:**
   - **Depth must be well under the stroke width.** A 45° extrusion as deep
     as the stroke is thick fills the letters' own counters — the hole in the
     `o` closed up and the word stopped being readable at DEPTH 7 of an 8 px
     stroke. It is 4.
   - **Gradient over the INKED rows, not the glyph cell.** Spanning the full
     9-row cell put every letter in the middle bands, because nothing in
     "spoils" fills the ascender and descender space — the wordmark came out
     uniformly grey, the exact opposite of the fix.
4. **UI and icons** — buttons, panels, the HUD.
5. **The player model.**
6. **World objects and textures.**

## A1. Menu backdrops — DONE (v0.6.29 - v0.6.35)

**ALL SIX BACKDROPS NOW EXIST AND ALL SIX ARE LIVING.** The user kept all
four pitches rather than two (*"let's add all 4 of those menu backdrops to the
game, just like the den and drain"*), they were promoted in v0.6.30, the den
and the drain were repainted to match in v0.6.29, and the living layers landed
one version each: yard v0.6.32, warden v0.6.33, underpass v0.6.34, counter
v0.6.35. `tools/pitches/` still holds the four source modules and can be
deleted whenever — the promoted copies in gen_art.py are what ship.

The history below is kept because it records what was decided and why.

### the original item

**THE OVERLOOK WAS DROPPED (user call 2026-08-02.)** It was the only pitch
anyone had painted; the user looked at it and said *"yes just drop it"*.
`make_scene_overlook()` is DELETED from gen_art.py — it was never wired into
the menu and never emitted a file, so removing it left `manifest.json`
byte-identical. Restore from git history if that ever reverses.

**The plan also changed with it:** the old note here said they wanted to see
all five painted rather than choose from descriptions. Having seen one, they
asked instead to pick from the written pitches — *"show me the pitches again
and what the living layer would be, I will pick a couple and we make them"*.
So it is **two picks, not five paintings.**

Paint each pick as a complete STATIC scene at 960×544 first; add the living
layer only once they keep it. The living layer has exactly five techniques
and they all already exist in `scripts/main_menu.gd`: a breathing additive
glow, a 3-frame sprite swap, a visibility blink on offset timers, dust
particles with a fade ramp, and one travelling sprite that triggers
something when it lands. Anything else needs new engine work.

1. **the yard at dusk** — down the rail between two boxcars, telegraph
   poles to a vanishing point, signal lamp ticking red, rain starting.
2. **the warden's window** — from outside the booth looking in: him lit
   from below, tally marks on the wall, the boom across the foreground.
3. **the flooded underpass** — knee-deep water, one stuttering strip
   light, reflections breaking as drips land.
4. **mara's counter** — over the shoulder at the trade counter: her
   hands, the radio set, the job board, a mug going cold.

Also asked for: **upgrade the two existing backdrops** (den, drain).

---

# B. GAMEPLAY THE USER HAS ASKED FOR

## B0-NEW. THE 2026-08-05 BACKLOG - "i dont just want my whole game to look
## square" *(user)*

All of these came in one burst while the terrain blending was being fixed.
None are started. **The unifying complaint is GEOMETRY: the user can see the
grid.** Their words: *"all the houses are square too, i want some variation
to it, you know what i mean? like i dont just want my whole game to look
square"*.

1. **The rail corridor reads as a hard parallelogram** - *"train tracks road
   just looks square when blended into the dirt, i dont want to see any
   square stuff"*. `_cell_material` returns "rail" for `_rail_cells`/
   `_rail_cross` and `_paint_fringes` skips those cells outright, so the bed
   never frays. The RAILS should stay crisp; the BALLAST should not. The
   `fr_gravel_*` overlays already exist and are barely used.
2. **Houses are rectangles.** Already logged as C3 (non-rectangular
   buildings) - it is a real builder job: L and T footprints, and every
   downstream system assumes `Rect2i` (roof, interior reveal, door side,
   entrance pockets).
3. **Three trucks parked identically, evenly spaced, same variant** - *"why
   are these 3 trucks just side by side all perfectly lined up? looks odd"*.
   This is the standing NO VISUAL REPETITION rule being broken outright.
   Whatever places the loading-dock trucks needs per-instance offset, spacing
   jitter and `_pick_variant_varied`.
4. **A door is invisible against its own wall** - *"the door on this building
   i can barely see it because its the same colour as the building"*. Same
   class of defect as the grey house in v0.6.54, and that one was found by
   COMPARING THE ACTUAL VALUES rather than by eye - do that again.
5. **Fallen trees** - *"lets make some trees fallen over on the ground, not
   but alot, maybe like 10% of trees are, not bushes though"*. A new baked
   variant (`bake_lean` will not do it - a felled trunk is a different
   sprite), placed at ~10%, trees only. NOTE: it must not change how many
   variants `_pick_variant` sees for the `tree` family, or the district
   re-rolls - add them as their own family and roll membership from
   `_side_rng`.
6. **Puddles: varied sizes and an animated reflection** - *"make the puddles
   on the ground from the rain, some bigger, some smaller, make it animated
   too, like the puddle haas reflection"*. Wet-ground reflections were
   already on the polish list (section A); this is the same item with a size
   spread and animation attached.

7. **Map redesign as "a painting"** *(user, 2026-08-05)* - *"can you make
   it look better, like draw it or something make it a painting, redesign
   the whole map because it doesnt look good"*. **NEEDS A SAMPLE AND A
   SIGN-OFF BEFORE BUILDING**: this is the THIRD direction for the map
   screen (flat rects -> paper chart, rejected -> game map), and the second
   was rebuilt in full and thrown away. Do not rebuild it blind again.
   Note the constraint the paper version violated: they also said *"i dont
   want a real looking map i just want it to look like a good real map that
   youd see in other video games"*.
8. **Power pylons: only three, and unconnected** *(user)* - *"is there only 3
   power pylons? add some more in the forest area and around comms, and make
   them all connected like how it is in this picture like with the lines"*.
   `_place_power_line` exists; it wants more pylons and a continuous run.
9. **Green trees shedding autumn leaves** *(user)*. NOTE: `_maybe_shed_leaves`
   already derives the leaf colour from the variant name and a comment says
   this exact bug was fixed once before - so **the remaining cause is
   elsewhere**, most likely `environment_system.gd`'s `_leaf_near`
   encoding (`>=100000 = red`). Measure before changing anything.

10. **A one-frame visual POP while walking** *(user, 2026-08-05)* -
    **NEXT STEP IS THE FRAME-DIFF, described at the bottom of this item. The
    user asked to resume here.**

    Their words, in the order given - the LAST one is the important one and
    it overturned the earlier reading:
    - *"i only see it while im walking and i only see it once, when i try and
      walk back where i was to see if it happens again, it doesnt happen"*
    - *"like sometimes i see it happen on a wall on a house"*
    - *"random stuff glitch for like a milisecond"*
    - *"the weird glitch happens on things next to my character too, like not
      when it first appears on the screen"*

    **MEASURED, so do not re-derive it: IT IS NOT FRAME RATE.** `--perf-walk`
    (added v0.6.61) swept the player ~9000 px across unvisited ground: 5761
    frames, **240.0 fps, worst frame 6.91 ms, ZERO frames over 8.34 ms**. The
    user's own counter agrees (*"i look at my fps too and its solid"*). It is
    a DRAW-ORDER or VISIBILITY flip lasting one frame. **Any fix aimed at
    performance is aimed at the wrong thing.**

    **RULED OUT - do not spend time here again:**
    - *A first-use / first-draw cost.* Killed by the user's last quote: it
      happens on things ALREADY on screen beside them. `_prewarm_textures`
      and `shader_warm.gd` are both off the hook. (An unrelated note kept
      because it is still true: `_prewarm_textures`'s comment claims `load()`
      performs the GPU upload, and that claim is unverified. It is not the
      cause of THIS, but it may still be wrong.)

    **THE LIVE CANDIDATE - NOT PROVEN. DO NOT SHIP A FIX WITHOUT THE
    FRAME-DIFF.** The player's Y-SORT KEY AND ITS DRAWN POSITION ARE DIFFERENT
    VALUES. `player.gd` keeps `global_position` continuous and draws the
    sprite at `snapped_pos` via `_sprite.position = visual_err` (rule 1 - the
    sprite parks on the screen-pixel grid), but y-sorting sorts on the NODE's
    global y, the UNSNAPPED value. So the player can sort against a wall a
    frame before or after the drawn sprites actually cross: a wall pops in
    front of the character for one frame, only while moving, and
    unreproducible because it depends on the sub-pixel phase. Every detail of
    the report fits, **which is exactly why it must be proven rather than
    believed** - this project has twice acted on a confident wrong diagnosis.

    **HOW TO PROVE IT (the next session's first job):**
    1. Film while walking. `--film` already writes frames to `shots/`; it
       will need the same collision-off sweep `--perf-walk` uses, or the
       player never leaves the safehouse (see that function's comment).
    2. **DIFF CONSECUTIVE FRAMES**, the technique that settled the menu
       birds. A pop shows as a large LOCALISED change between two frames with
       the frames either side identical - distinct from motion, which changes
       smoothly frame to frame.
    3. Crop the flagged frame pair and LOOK at it. If a wall swaps in front
       of the player and back, the sort theory is confirmed.

    **IF CONFIRMED, MIND THE FIX.** Snapping the node's own position is the
    obvious move and it is WRONG: quantising the true position inflates and
    deflates speed, which is the v0.2.1 "low fps walk" bug this project has
    already paid for once (rule 1). The fix has to make the SORT KEY agree
    with the drawn position without quantising movement - e.g. sorting on a
    value derived from `snapped_pos` while movement keeps using the
    continuous one.

## B0c. THE SECOND FLOOR IS ROUGH *(user)* — **2 of 4 DONE in v0.6.77**

**Item 2 (stair top visible) FIXED.** The slab covers the flight while you are
on it — art AND collider, so nothing invisible is left standing there. Plus a
bug found on the way: the prompt still said *"go upstairs"* from upstairs,
because the text cache keys on (target, door-open) and **the floor was not in
that key** while climbing does not change the target.

**Item 1 (clipping into the floor) FIXED in v0.6.85 — the user's photo was the
repro, and BOTH of my earlier verdicts were wrong in different ways.** The
first "confirmed" was a HUD label misread; the "not reproduced" after it was a
sampling miss: the sink depends on the position within a cell AND the
building's own phase, so the same pose that draws whole in the grey house
sinks to the waist in the school. The slab tiles sorted at their true cells,
so the tile one row SOUTH of a stander drew its lifted art over their legs.
Every slab tile and lip now sorts a STOREY NORTH with the art pushed back
level — the second-floor pattern applied to the floor itself. Reproduced
deterministically first (`--upstairs-px=` sub-pixel pose), verified at the
same pose after, plus wall-to-wall shots of both rooms.

**Item 3 (clipping on props) NOT REPRODUCED.** `--probe-upper` lists every body
still on a collision layer inside an upper room: **19 solid, 0 invisible** — 14
wall segments and posts, the door, the stairs, 4 pieces of furniture, all
drawing. There is no ghost collider up there. **Needs a repro.**

**Item 4 (the stairwell hole) DONE in v0.6.78** — sampled on one building,
user kept it (*"yea i like the shaft keep it"*), now on all of them. **It is
PAINTED, not cut**: no transparency anywhere, so the ground room can never show
through, which is why the first attempt was removed. Drawn over the building's
own floor tile as a CHILD of it, so it needs no wood match and cannot tie in
the sort.

**Also DONE in v0.6.78, a separate report:** *"the second floors walls shouldnt
show if im on the first floor"*. A two-storey wall was one tall sprite, so each
piece now also generates a ground-band-only version swapped in while inside
downstairs. Full height outside and upstairs. The low band takes the SAME rng
draws and throws them away, so the bricks are identical and the swap does not
reshuffle the wall.

### the original report

Their words: *"when i go up the stairs in the two floor buildings, i clip
inside of the floor, and i can see the top of the stairs, it should all be
clean like the bottom floor when i walk around, i clip on stuff when walking
around on the second floor, also can you make a hole in the second floor to
show where the stairs are"*.

**Four separate things in one report — do not treat it as one bug:**
1. **Clipping into the floor slab** on the way up the stairs.
2. **The top of the stairs is visible** through/above the upper floor when it
   should be covered.
3. **Clipping on props** while walking the second floor - colliders there do
   not match what is drawn.
4. **A stairwell opening in the upper slab** — **THIS WAS BUILT ONCE AND THE
   USER HAD IT REMOVED. DO NOT JUST REBUILD IT.** `_build_upper` carries the
   note: *"EVERY cell gets floor - the upper room is the ground room's
   ceiling, complete (user: the stairwell hole showed the ground and broke
   it). The flight's art still rises through the slab."*

   So the CONCEPT is wanted again (*"can you make a hole in the second floor
   to show where the stairs are"*) but the previous EXECUTION failed for a
   specific reason: the hole was a gap, so you saw the ground room through
   it, which broke the illusion that you are standing on a floor.

   **The version that satisfies both:** the opening must read as a SHAFT, not
   a gap. Dark well below the lip, the stair top drawn inside it, and a lip or
   railing on the near edges so the slab still has a silhouette. What must NOT
   happen is the ground-floor room showing through. Confirm with the user
   before building, and show them one screenshot before doing every building.

**Read this before starting** - CLAUDE.md's standing lesson, which is about
this exact system: *"Sort position and draw position are different things.
The second-floor slab is the reference fix: give each piece its own sort
position and offset the ART, never the node. A z-band puts a thing in front
of EVERYTHING - that is how the upper floor ended up clipping over the
roofline."* Items 1-3 are all sort/collision mismatches of that family.

Note also that v0.6.63 changed `player.gd` so `global_position` is now
SNAPPED each frame and `_true_pos` carries the exact position. Anything on
the second floor that compares the player's position against slab geometry
should be re-read with that in mind - `floor_lift` already offsets the sprite
and camera together.

## B0e. The player draws THROUGH a wall — **FIXED in v0.6.71**
## (kept: the mechanism is a reusable warning)

*"right now im behind the door, my character shouldnt be seen, but i am seen
still"*, with a screenshot: standing in an open doorway, the character is
drawn over the wall instead of behind it.

**THE SUSPECTED CAUSE IS MY OWN FIX.** v0.6.63 snapped the player's
`global_position` onto the screen-pixel grid so the SORT KEY matches the DRAWN
position (that fixed a measured 46% wrong-order rate near the character, and
the user confirmed it worked). But the world's props and wall segments already
sit on whole pixels - so snapping the player onto the same grid makes their
sort y land **EXACTLY EQUAL** to a wall's far more often than before. Godot's
y-sort has no defined order for a tie, so the player can win against a wall
they should be behind. A doorway is exactly where you stand level with a wall.

**Before/after evidence is cheap here:** `--probe-sort` already walks the
player and compares sort keys; extend it to count EXACT TIES against
neighbours (`node_y == other_y`) and compare against the tag v0.6.62 build.
If ties jumped, this is confirmed.

**Do not fix it by un-snapping** - that reintroduces the flicker that was
measured and fixed. The fix is a deterministic TIE-BREAK: keep the snap and
offset the sort key by a sub-pixel epsilon so an exact tie is impossible. An
epsilon well under half a pixel cannot move where the sprite rasterises, so
the v0.6.63 guarantee holds. **Work out the correct SIGN first** - in this
projection the piece that should occlude the player at equal y is the one
nearer the camera, so check against a real wall rather than assuming.

## B0g. 3 px still visible above a door — **CLOSED 2026-08-07 by the user in
## play** *("the door gap at the top is fine now too")*

**This item's own option 1 was the thing that closed it:** *"check whether
those columns are actually above the roofline — if so the remaining 3 px may
be invisible in play and this is already done."* The user playtested and
reports no gap. No code changed after v0.6.70; the 3 px of geometry are still
there and are simply not visible from a playing camera.

**Kept because it is the measurement, not the verdict** — if a gap is ever
reported here again, start from this rather than re-deriving it:

*"its still cut off at the top a bit ... i shouldnt see anything from
outside"*. v0.6.70 took the worst gap from **8 px to 3 px**. Do not eyeball
this one - measure it:

```
for each world column across the opening:
    lintel_bottom = lowest opaque row of door_lintel_<style>_<axis>
    door_top      = highest opaque row of door_<kind>_<axis>_<style> frame 0
    gap = door_top - lintel_bottom - 1        # > 0 means see-through
```
(both converted to world y by subtracting the manifest `origin` y.)

**Why 3 px remain:** the header is cut FROM the wall segment, so it can only
cover where the segment itself has pixels. The residue is columns where the
segment is transparent above the door's top edge - the header has nothing to
give there. Options, in order of preference:
1. Check whether those columns are actually above the roofline (showing roof,
   not interior) - if so the remaining 3 px may be invisible in play and this
   is already done. **Shoot it before building anything.**
2. Extend the DOOR art upward instead, so the leaf's own top reaches the wall
   line - `DOOR_H` is 34 against `WALL_H` 40.
3. Draw the header procedurally along the edge slope rather than cutting it
   from the segment, accepting that it then has to match the brick by hand.

## B0h. An OPEN door leaf does not hide the player behind it — **FIXED**
## *(kept: the probe trap in it is the reusable part)*

**Fixed exactly as the mechanism below predicted**, and PROVEN with an A/B on
one frame: same door, same pose (`player_y-leaf_y=-10.0` in both runs), the
only variable the shift. Before, the character is drawn fully over the open
leaf — the user's screenshot reproduced. After, they are completely hidden by
it. The opposite pose is guarded too: stood in the street at `+10` in front of
the leaf, the player is still fully drawn, so the shift does not overshoot.

**`--door=behind` and `--door=front` are the new probes** (`harness.gd`), and
B0h's own note — *"there is no probe for occlusion, and `--smoke` will not
catch it"* — is why they exist. Both print `shift=` and `player_y-leaf_y=` as
LIVENESS FIGURES beside the pose.

**THE TRAP, and it nearly took me: `get_first_node_in_group("doors")` returns
a door this bug CANNOT happen on.** Measured off the manifest, only two of the
four kind/axis combinations move in y when they swing — a `y` door opening out
(+10, toward the camera) and an `x` door opening in (-10). The other two swing
sideways on screen and shift by exactly 0. The first door in the district is
one of those, so the first shot came back `shift=0.0`: a frame that looked
perfectly correct while measuring nothing. **The probe now picks the door with
the deepest outward leaf, not the first one.** Same vacuous-green failure this
project has now hit four times.

**The known cost, stated rather than discovered later:** the jamb boards are
structurally WALL but they ride the same sprite as the leaf, so they take the
shift with it. While a door is open, its frame edges sort up to 10 px nearer
the camera than they really are. Splitting them needs the generator to emit
the jambs as their own piece (8 strips: kind x axis x style). Not done — the
sliver where it could show is a player stood within 10 px of an open doorway
and overlapping a 6 px board, and being clipped by a door frame you are
standing in reads as correct.

*"i can still see my character when he should be behind the door"*, with the
door OPEN and the player standing in the opening. **This is NOT the v0.6.71
tie-break** (that closed B0e and is verified: 0 disagreements over 810 px).

**The mechanism.** A door node sits on the WALL LINE, but an open leaf swings
several pixels TOWARD THE CAMERA. Y-sort orders by the node, so the leaf can
never occlude anything whose node is south of the wall line - including a
player standing right behind the open leaf. The sprite's screen extent and its
sort anchor disagree.

**CLAUDE.md already names the fix pattern, from the second-floor slab:** *"give
each piece its own sort position and offset the ART, never the node."* So when
the door opens OUTWARD, push `door.position.y` toward the camera by the leaf's
depth and subtract the same from `_sprite.offset.y`. The art does not move; the
sort does. Reverse it on close. `scripts/door.gd` already tracks `_swing_out`
and has `leaf_center()` / `leaf_normal()` to size the shift from.

**Verify with a screenshot of a player standing behind an open leaf** - there
is no probe for occlusion, and `--smoke` will not catch it.

## B0i. Door vs wall contrast on SHADED faces — **CLOSED 2026-08-07 by the
## user in play** *("the door colours are fine now")*

**Nothing shipped between the complaint and the verdict** — verified by
reading `make_door_strip` in `tools/gen_art.py`, whose comment carries the
same **37** luminance figure this item quotes. So v0.6.65's colours were
already enough in play, and the 37 gap the analysis called thin reads fine on
screen. The user is the ground truth on a visual judgement; the number was
not.

**Kept because the numbers are worth having** if a door ever disappears into
a wall again — and because the standing lesson under the table is still live:

*"that door is also the same color as the warehouse, make sure all doors on
all buildings are different colours than the building"*. v0.6.65 set the door
colours against the wall's **lit** face; measured against the **shaded** one
the margin is much thinner:

| surface | luminance |
|---|---|
| `brick_b` lit face `819796` | 144 |
| `brick_b` shaded face `577277` | 106 |
| metal door `394a50` | 70 |

37 against the shaded face, versus 74 against the lit one. **Check every
door/wall/face combination, not just the lit one** - the same mistake as
v0.6.54's grey house, which was measured against the wrong thing. A door
should clear BOTH faces by a wide margin; consider giving doors a hue that no
wall uses rather than chasing luminance.

## B0f. Going upstairs shuts the front door — **FIXED in v0.6.76**
## *(kept: the guard it removed was RIGHT, and must not come back)*

**Do not "simplify" this by deleting the seal.** The door was being slammed
shut ON PURPOSE. `_build_upper` lays floor tiles and nothing else, so the upper
room reuses the GROUND SHELL for collision — an open ground-floor doorway is a
real hole at storey height and someone walked out of one. The fix separates the
two concerns: `Door.set_floor_blocked()` seals the doorway for COLLISION while
the door keeps its state, frame and silence. The occluder deliberately stays
with the visual state, so a door that looks open still passes light.

Covered by `--probe-floordoor`, which asserts both halves at once plus the
unseal on the way down. `force_closed()` is deleted — it had one caller.

**The probe's first cut FAILED falsely** by measuring crossing along the
through-axis: an 18.2 px slide along the wall read as walking through a sealed
doorway. It measures against `doorway_normal()` now. Same trap CLAUDE.md
already names, walked into anyway.

### the original report

*"when going up the stiars to a second floor, the main door entrance closes
automatically, it should stay open"*. Changing floor should not touch a
door's state at all. `main.gd` owns the floor switch and swaps which room's
furniture exists - check whether it rebuilds or re-adds the ground-floor
props (the door among them) rather than just hiding them, which would reset
the swing to frame 0. `scripts/door.gd` holds the open/closed state.

## B0d. A closed door does not seal — **CLOSED 2026-08-07 by the user in
## play** *("b0d already fixed, dont need to do that")*

Closed by the same v0.6.66-v0.6.70 door work that closed B0g; nothing further
shipped for it. Third item this session closed by playing rather than by code
(with B0g and B0i) — **when a fix lands, the items it silently closed do not
close themselves, and TASKS.md is what a fresh session trusts.** The original
report is kept below for the measurement.

*"i can see a bit of the inside of the house because the door isnt fully
closed, the top shows a bit of the inside of the house, it should be sealed"*
- with a screenshot showing daylight/interior through the top edge of a shut
door. Frame 0 of the door strip is meant to be flush IN the wall plane;
whatever it is, it does not cover the full opening height. `make_door_strip`
in `tools/gen_art.py`, and the opening is cut in `_build_shell`. Compare the
leaf's drawn height against the hole the wall leaves.

## B0m. Two open items from the second-floor pass — **BOTH FIXED in v0.6.81**

**Item 1 (the door line) FIXED**: it was the transom's bottom outline, drawn
where the upper wall band sits on the door lintel — a butt join, which never
gets an outline anywhere else. It faded with the band, which is why it
"went away inside". Stripped; the join is seamless brick in both states.

**Item 2 (stairs clipping furniture) FIXED**: the flight's art leans into
`stairs_cell + (0,-1)` and nothing reserved that cell. `lean_blocked` probed
**5 -> 0** across all six buildings. The fix erases the cell from furnisher
candidate lists AFTER shuffling — pocket entries change the shuffle's draw
count and reroll the district, which is why it could not just be added to
pocket. DOORS stayed 16 on identical cells.

The original diagnosis below is kept for the record.

1. **A line above the door that disappears when you go inside.** *"theres a
   line on top of the door, and it goes away when i go inside, can you remove
   that line completely, there should also be nohting changed ontop of the door
   when going inside"*. **This is mine.** The transom above a door is
   `seg2_*_upper`, which is second-storey wall, so it is registered with a null
   low texture and HIDES with the rest of the upper band. The user wants
   nothing above a door changing at all, and the line itself gone — so the
   transom needs to either not exist for the low state or be replaced by
   something that is identical inside and out. Check `door_lintel_*` too: that
   is a separate always-visible piece and may be the line itself.

2. **The stairs clip into ground-floor furniture.** *"i can see it clipping
   into the tv"*. Confirmed in a capture of my own — the flight overlaps a dark
   cabinet. `_occupied[stairs_cell] = true` is set in `_build_upper` AFTER the
   ground furnishing has already run, so nothing stopped a piece taking that
   cell. **This matters more now that the stairs are solid (v0.6.78)** — a
   player could be wedged between a staircase and a cabinet. Reserve the
   flight's cells before furnishing, and remember the flight's ART spans about
   two cells up-right of its anchor, not one.

## B0n. Upper and ground furniture overlap — **DONE in v0.6.90**

*"same with the furniture"*, then *"i dont want the same furniture on the floors
of one house"*, *"it should be different"*. Shipped as the split this entry
proposed:

| floor | families |
|---|---|
| ground (house) | couch, tv_stand, table, chair, crate — the living room |
| upstairs (house) | bed, cabinet, bookshelf — the bedroom |
| upstairs (hall/school) | crate, crate_stack, pallet — storage over the desks |

**Nothing appears on both floors of one building.** Route 3 from the list below
did it: every original `_rng` roll is still taken and thrown away, and the
replacement families are picked off a LOCAL generator seeded from
`DISTRICT_SEED` plus that building's own corner (`_local_variant`). The one
family swap that WAS draw-neutral on its own — `_pick_variant("crate")` to
`_pick_variant_norepeat("bed")`, one draw either way — was done directly.
Verified: DOORS 16, LAMPS 53/15, VEHICLES 30, UPPERS 6, identical cells.

**Kept for the next person, because the reasoning still applies:**

**NOT a simple list edit, and this is the whole difficulty.** The picks go
through `_pick_variant_varied`, which takes **one draw usually and TWO when it
happens to repeat** — so swapping a family in place changes the draw count and
rerolls the entire fixed district. `_pick_variant_norepeat` exists for exactly
this and costs one draw always, but switching an existing call site to it also
shifts the stream.

Draw-neutral routes, in order of preference:
1. Swap only `_pick_variant(...)` call sites — those are a single
   `randi_range` and are genuinely neutral (v0.6.86 used this reasoning).
2. Change families and ACCEPT a furniture reroll, then verify with
   `--probe-world` that DOORS/LAMPS/VEHICLES are unchanged — if only furniture
   moved, the fixed *district* is intact and that is what the rule protects.
3. Re-pick after placement, swapping the sprite on the node — no draws at all.

Verify with DOORS 16 on identical cells, plus LAMPS and VEHICLES.

## B0. Parking lots and aprons should JOIN the road network *(user, 2026-08-05)*

Their words: *"lets make all parking lots or roads connected to eachother,
like a parking lot can have a small road going from it and then it connects
into the road"*. Today the depot apron, the safehouse pad and the stalls are
islands of asphalt with no route onto the grid - you drive over grass to
reach them.

**NOT STARTED.** It is a layout change, so it inherits the whole discipline
from the v0.6.53 road nudge:
- **Zero `_rng` draws**, or the fixed district rerolls. Use `_side_rng` or a
  hash seeded off `DISTRICT_SEED`.
- **Re-probe `DOORS` after.** It is the cheapest detector of the
  squeezed-block bug, and an access road eats block cells.
- The spur wants the same fringe treatment as everything else or it will
  reintroduce hard edges the blending just removed.

## B0b. Broken cars must READ as broken *(user, 2026-08-05)*

*"lets make all broken cars more distinct, i cant even tell it was broken,
like make the door opened with some stuff on the ground near it, the
windshield can be broken, little bit of smoke can come out of the engine
too"*. **NOT STARTED.** Wreck variants are `_5`/`_6` of each `vehicle_*`
family (that is also what the safehouse pad now remaps away from). The ask is
three separate pieces: a sprung door and spill on the ground (generator), a
broken windshield (generator), and a thin smoke wisp (runtime, and the
soft-alpha carve-out already lets that scale - see the LZ beacon).



## B0j. The underpass door and posters — **DONE in v0.6.42**
*(was filed as B0c, renumbered 2026-08-07: there were two B0c sections and
`HANDOFF.md` points at the OTHER one, "the second floor", as where to pick up.
The open item keeps the letter; this completed one moved.)*

*"in the underpass backdrop is that a door on the right? if so make it look
more like a door and add a handle on it, and add a poster or two on the walls
near the door, make sure it doesnt cover anything already on the wall though,
make the posters show something about our games lore, like a small painting"*.

**IT IS NOT A DOOR — it is a brick PIER.** Verified by cropping the bake:
x 828-900, y 228-380, a brick buttress against the wall with a pale capping
stone on top and the walkway railing crossing in front of its foot. The user
read it as a door, which is itself the finding: **an ambiguous shape gets read
as whatever the brain supplies** (the same failure as the downpipe that read
as a car and the light spill that read as a body). So either commit to a door
or make the pier unmistakably a pier.

**Recommended: make it a door**, because the user wants one and a service door
in an underpass wall is plausible. It is BASE ART — `make_scene_underpass`.
- Give it a frame, a visible reveal, panel lines or a corrugated skin, and a
  **handle** at ~4/10 of its height on the side away from its hinges.
- Keep the capping stone or convert it to a lintel; the railing in front is
  fine and helps it sit in the scene.
- **The tube's light comes from the LEFT of it** — the lit and shade faces
  must agree with that or it will read as pasted on.

**The posters:** one or two, on the flat wall NEAR the door and **covering
nothing that is already drawn**. Free wall in that area: roughly x 902-956,
y 240-330 (right of the pier, above the walkway) — re-measure before drawing.
Lore to draw from is in `LORE.md`; small painted images, not text blocks,
because the font is 5px and a readable poster would be enormous. Candidates:
the district wire, the tally, a transit-authority evacuation notice.
**Check `--checkdocs` still passes** — the quiet button box is x 395-565 and
none of this goes near it.

## B0a. Rain must actually LAND — **DONE in v0.6.40**

*"i meant like the actual raindrops coming down on the screen should
physically hit something on the screen, so remove that water stuff on the
ground and do what i wanted"*.

**What was tried and REMOVED in v0.6.39:** a second `CPUParticles2D` of splash
marks sitting on the ground band. It reads as decoration lying on the floor,
not as a drop landing, because the splash has no relationship to any
individual streak — the user spotted that immediately.

**What it actually needs:** drop the particle system for menu rain and
hand-roll it. An array of drops, each with its own x / y / speed and a
**per-column ground row**; a drop falls until it reaches that row, then dies
and leaves a splash AT THAT EXACT POINT for ~0.2 s. ~40 lines in
`main_menu.gd`, and the splash art already exists (`rain_splash.png`, the
world's own). The ground row is not flat — the yard recedes to a vanishing
point and the warden's road slopes — so each scene needs a small function
mapping x to the row where its ground starts, sampled off the bake the way
the window and wire anchors were.

Applies to the **trainyard** and the **warden**. Do it before adding rain to
any other backdrop.

## B0k. Mara's arms and pencil — **DONE in v0.6.41**
*(was filed as B0b, renumbered 2026-08-07: there were two B0b sections and
`HANDOFF.md` points at the OTHER one, "broken cars reading as broken", as open
work. The open item keeps the letter; this completed one moved.)*

*"in maras counter, shes not holding the pencil right, like its not in her
hands. also make her arms not square and a bit smaller"*.

**This is BASE ART, not a living layer** — `make_scene_counter` in gen_art.py,
the `_mara_body` / hand / pencil code. The base painting hash WILL change and
that is expected here; every other backdrop must stay byte-identical.

**CONSTRAIN THE FIX TO THE COMPLAINT** (the shoulder-pass rule, CLAUDE.md):
only the pencil's position/grip and the arms' width profile may change. Her
face, hair, headset, jacket, the ledger, the light box, the counter and both
light pools must come out pixel-identical — **prove it with a diff**, not by
eye. A pass that rebuilt more than was asked has been rejected on this project
before and had to be reverted.

## B1. Sprint *(user)*

Left shift, **hold-or-toggle like crouch**. Needs a run cycle for all 8
facings — a new `char_run.png` matching the existing sheet layout exactly,
so the stance system can switch to it the way crouch and prone already do.
Speed clearly above the 120 walk but nowhere near the car's 190: *"i dont
want it as fast as a car, but still faster than walking speed."* Add
`sprint` to project.godot `[input]` AND to `Settings.BIND_ACTIONS` +
labels + defaults — it is a keyboard bind, so it is rebindable.

## B2. The warden should actually converse *(user)*

*"make them actually talk to one another, the user and the warden."*

**The player DOES already say something** — this task used to claim they
never do, which sent the work in the wrong direction. The reply button
carries one of the 14 lines in `REPLIES` (`toll_dialog.gd:54`), shown in
quotation marks and picked so it never repeats twice running. What is
actually missing is the LINK: pressing it draws the warden's answer at
random from the unrelated `LINES` pile, so what he says never follows on
from what the player just said. **The player lines exist; thread the
warden's responses off the line that was actually pressed** — topic
threads, not a random ramble. `toll_dialog.gd`.

## B3. The scrapyard building *(user)*

- **Recolour to red/orange.** Walls have only two styles today: `brick_a`
  (red brick) and `brick_b` (grey masonry), both in `BRICK_STYLES` in
  gen_art.py (~line 621; there is no `WALL_STYLES` — this task said so for
  weeks and sent a grep to nothing). Add a **rust** style so it reads as a different building
  from the warehouse POI, not a redder copy of it.
- **Strip every box and shelf, inside and out.** Root cause found: the
  hall is created in `_plan_scrap_hall` with `"kind": "warehouse"`, so
  `_furnish_warehouse` fills it with racks and crates. It needs its own
  kind and its own furnisher.
- **Restock with scrapyard material** — machines, cable drums, toolboxes,
  cylinders, tires, part-stripped wrecks. Keep it restrained; their
  standing note is that too many objects looks odd.

## B4. The smoker on the bench *(user)* — NEXT UP

Benches were rebuilt with a real seat (v0.6.12). The smoker still needs:
- **Rebuild him from the PLAYER's character sheet** so his shading and
  contrast match everything else — the user's words: "why does this guy on
  the bench look so much different than me". Give him **a black hat** to
  tell him apart.
- **Bigger smoke** off his puffs; they read as a small white blob now.
- **Seat him on the bench BELOW him**, not the one he is currently inside,
  and have him **face away from the backrest**, not into it.
- Move the ground item that sits over his head.
`make_smoker_sheet` in gen_art.py; placement at world_builder.gd ~2530.

## B4b. The LZ green smoke reads as mist *(user)*

The extraction marker smoke "just looks like mist" — it needs to read as
a thick coloured signal plume: denser, more saturated green, rising in
distinct billows rather than a soft haze. It is also a good first customer
for the glow pass above.

## B6. Cosy safehouse

**Inside:** bookshelf, cabinet, TV, plus **posters and pictures on the
walls** — new art, wall-face decals like the graffiti walls. Mind that
walls are drawn as segments and only the camera-facing interior faces
show. **Outside:** a little dirt road from the safehouse door to the
nearest POI — reuse `_walk_dirt_path(from, to)` with the safehouse's
`door_out` cell and the closest POI centre; it already skips roads and
slabs. Keep it restrained.

## B7. Flashlight shines through walls — **DONE in v0.6.45**

Fixed properly, with the occluders, not with the cheap interior-cell mask.
`_build_shell` now hangs a `LightOccluder2D` on every wall segment, so the
cone is stopped by the wall itself.

**Verified by measurement, not by eye:** stood inside a building at midnight
with the flashlight on, a brightness scan straight out through the lit cone
reads 90-334 inside the shell and a flat 52-56 — the pure ambient night
floor — for the entire street beyond it. Nothing leaks.

**The same leak on the other two lights is closed by the same change.**
Interior room lights no longer wash onto the street; `interior_light.gd` was
carrying a deliberately tight `texture_scale` to hide exactly that, and the
comment there now says so.

## B8. Warden: opposite sidewalk, facing the road

He sits on the wrong side and faces away — *"hes like facing the void"* —
which makes pulling up awkward. `_toll_booth_cell()` returns
`Vector2i(road.x + 1 + 3, MAP_H - 1 - BARRIER_INSET)`; the `+3` puts him
on one side, so mirror it. `_place_barricades` reserves his cells via
`_toll_reserve` using the **same helper**, so changing the helper moves
both together. The booth art may need a mirrored facing so the window
faces the asphalt. Re-verify `TollGate.setup`'s boom offset still spans
the road, and that the extract zone beyond the wire still lines up.

## B9. Flat ground props draw over the player — **FIXED in v0.6.83**

The generator writes `"flat": true` for its collider-less litter families
(trash, sticks, spray cans) and `_add_prop` parents flagged props into the
`Flat` layer — over the tiles, under everything that stands. 124 decals moved
off the y-sort; verified by standing the player on one (the new `FLAT` probe
prints cells to aim at). Deterministic layering, cannot recur. The original
notes below stand for any future flat family: flag it in the GENERATOR, and
anything with real height stays y-sorted.

**Repro was:** a small flat orange-brown object renders **on top of** the
raider standing on it. It does **not** block — purely draw order.

**The fix already exists:** `_flat` in `world_builder.gd` is a `Node2D`
sibling between the floor `TileMapLayer` and the y-sorted `_ysort`.
Anything lying flat belongs there; add a helper mirroring `_add_cable`.

**Trap:** do **not** use a negative `z_index` inside `_ysort` — z sorts
globally within the canvas layer, so the sprite vanishes behind the floor
entirely. That is exactly what happened to the cables, and to the second
floor when a z band was tried on it. Where a thing has HEIGHT, the
second-floor fix is the better pattern: give each piece its own sort
position and offset the ART, not the node.

Sweep the catalogue for others that read as ground: spilled trash, paint,
spray cans, painted markers. Anything with real height stays y-sorted.

## B10. Door sound: a real creak

`Sfx.play_door(open)` plays `_synth_blip` tones, which read as a thunk,
not timber. Either synthesise a creak (a slow pitch-sweeping resonant
scrape with irregular stick-slip amplitude, plus a soft latch thunk on
close) or source a CC0 recording the way the car doors and thunder were.
**Ship it quiet on the first cut** — ≤ -18 dB on the `sfx` bus. The swing
is 4 frames × 0.06 s, so the creak should be about that long or it
outlasts the animation.

---

# C. HOUSEKEEPING

## C1. Changelog bullets in the wrong places *(user)* — **DONE, nothing left**

`CHANGELOG_ENTRIES` stores each entry as an array of strings and the
renderer prefixes **every** element with `- `, so the convention is **one
string per bullet, unwrapped** (the labels autowrap, so the renderer needs
no change). That still governs every new entry.

**The rewrap already shipped in v0.6.16** and this task was left open
describing work that no longer exists. Re-measured 2026-08-02 by parsing
the array: **100 entries, and not one wrapped fragment remains.** Only four
versions (v0.1.0, v0.1.2, v0.1.4, v0.1.11) have every bullet under 58
characters, and reading them settles it — "8-direction movement and
collision", "settings save and reload on launch" — those are **genuinely
separate short bullets, not fragments of a wrapped sentence.** There is
nothing to join.

The old note here claimed "**55 older entries** hand-wrapped at ~52
characters" and offered "verified: v0.2.4's three bullets become two" as
proof a blind join would misfire. **Both are false now**: v0.2.4 has two
bullets and the first is 269 characters, fully unwrapped, so the stated
verification cannot be reproduced. If a future pass ever does touch this
array, note the menu's version label derives from `CHANGELOG_ENTRIES[0][0]`
— do not disturb ordering.

## C2. v0.4.3 has no in-game changelog entry — **DONE in v0.6.83**

Row written from the shipped CHANGELOG.md entry and inserted in
chronological position, so `CHANGELOG_ENTRIES[0][0]` — the menu's version
label source — was untouched.

## C3. Non-rectangular buildings *(user)*

*"make all the houses and warehouses and stuff like that not all a square
or rectangle."* **Architectural, not a tweak.** Plots are `Rect2i` end to
end: `_plan_plots`, `_rect_clear`, `_build_shell`, `_furnish_*`,
`RoofReveal.cells`, the upper-floor containers, `_claim_building_ground`,
and the map screen's building rects all assume a rectangle.

**Suggested approach:** keep a bounding `Rect2i` but add an optional
**cell set** (an L or T from two unioned rects), and drive wall, roof and
interior generation off cell membership plus neighbour masks rather than
rect edges. The wall art is **already neighbour-masked**, which is the
piece that makes this feasible. Expect the roof reveal and the map drawing
to need matching work. Do it sample → sign-off → fleet.

## C6. A full doc sweep *(user, deferred by them 2026-08-03)*

*"the sweep will happen later"* — **deferred on purpose, not forgotten, and it
does NOT block a migration.**

**Why it is worth doing anyway:** the only defence against a document that
confidently says something false is reading it, and **three sessions running
have found stale prose while `--checksec` and `--checkdocs` both printed
PASS**. A check can prove versions agree and paths exist; it can never prove a
sentence is true.

On 2026-08-03 only the MENU-related claims were spot-checked, and two of those
were wrong: `DESIGN.md` still described a two-backdrop menu (thirteen releases
stale) and `CLAUDE.md`'s menu node count still read ~818 when it is 1717.
**The rest of `CLAUDE.md`, `DESIGN.md`, `LORE.md` and `TASKS.md` has NOT been
read against the code since 2026-08-02.** Assume there are more wrong
sentences in there.

## C7b. `tools/__pycache__` is TRACKED

`tools/__pycache__/gen_art.cpython-314.pyc` is in git, so every generator
edit dirties a binary blob and it rides along in the commit. It wants
`git rm -r --cached tools/__pycache__` plus a `.gitignore` line. Left alone
for now because it is pure noise, not a bug — but note the `.gitignore` half
has a real cost worth reading first: `--checksec` scans only files git will
LIST, so anything added to `.gitignore` becomes invisible to it. A `.pyc` is
not in any of its scanned suffixes today, so this particular line costs
nothing; the general rule still stands.

## C7. Repo weight *(user, deferred by them 2026-08-03)*

*"i will optimize the repo later too"* — **their call, and it does NOT block a
migration.**

Measured 2026-08-03: `shots/` is **373 tracked files / 77 MB**, `.git` is
**109 MB**, and **57 files went into `shots/` on that day alone** — every
debug capture from a long bug hunt is committed forever. Tracking shots is the
project's existing convention (313 of them predate this), which is why nobody
has changed it unilaterally.

**Options, for the user to pick:** keep curating `docs/` for the README and
add `shots/` to `.gitignore` going forward; or prune the debug captures and
keep the deliberate ones; or leave it. A history rewrite would shrink `.git`
but is a force-push and needs their explicit go.

## C4. Older standing queue

- **Pickup bed** — shade the interior so it reads as a container, put a
  box in it, sample sheet across all angles. *Sample → sign-off first.*
- **Catalogue variety** — families still on two variants (bench, dumpster,
  shelter, vending, newsbox, forklift, planter, swing) plus singleton
  crane/sandbox. The deeper fix is parameterising the builders so
  **shapes** differ, not just wear.

## C5. The autoload-reset rule is only half-obeyed — **DONE in v0.6.26**

Found by the 2026-08-02 docs audit. It was a **latent** gap, never a live
bug: `Juice._process` runs `PROCESS_MODE_ALWAYS` and unscales its own delta,
so a hit-stop always expired on its own within ~50 ms, and `main.gd`
cleared it on `_exit_tree` anyway.

Closed regardless, because M2's guns lean on hit-stop constantly and the
protection ran through a single path. `main_menu.gd` and `splash.gd` now
call `Ui.clear()` and `Juice.reset()` themselves, so every scene root starts
from a known state instead of trusting whoever ran last.

**Audited at the same time, all clean:** `Raid.begin()` resets the per-raid
ledger on deploy; `Sfx.silence_world()` and `Music.play_menu()` run on menu
entry; `Ui.clear()` already ran in both directions. `Authority` and
`Settings` hold nothing per-raid by design.

Also fixed in the same pass: `player.gd` floored its hit-stop divisor at
**0.05** while `Juice.hit_stop` sets exactly **0.04**, so the floor clamped
a legitimate value instead of guarding division by zero, and the camera kick
and hit flash decayed 20% slow through every hit-stop. Now `0.001`, matching
Juice.

# WAITING ON THE USER

- **M2 — guns, tunnels, story.** The gunplay design is settled (below);
  it starts on their explicit go.
- **Trailer — PARKED, not dropped** (user, 2026-08-02: "were not dropping
  it, just putting it aside for now"). Pick it back up after the polish
  pass. State when it was parked:
  - **ffmpeg IS NOW INSTALLED** (Gyan build 8.1.2 via winget, hash
    verified). The old note in this file saying it wasn't is dead — the
    pipeline is no longer blocked on tooling.
  - **Concept (a) "the wire" is the one to build**, ~50 s: black + radio
    crackle, lowercase cards ("six years since they sealed the districts"
    / "one still answers"), dawn-fog pans, night lamp flicker, rain on the
    courtyard, ONE sniper tracer, hard cut to black on the crack, title +
    "loot. extract. survive." + date. It works before guns exist, which
    (b) "one raid" does not — that one needs M2.
  - Pipeline: godot `--write-movie` PNG frames at 640x360 -> 3x nearest ->
    ffmpeg to 1080p60 with fades and a music bed -> mp4 plus a 9:16 crop.
    Four tracks already in `assets/audio/music` to pull a bed from.
  - **Render the title cards INSIDE godot** using the game's own bitmap
    font, not ffmpeg's text drawing — it keeps the pixel look exact and
    avoids a font mismatch between the cards and the footage.
  - Nothing was built yet; no cinematic harness mode exists.

*(A third item lived here — "which menu backdrops to keep, once all five are
painted". **Deleted 2026-08-04 as false.** All SIX are painted, shipped and
living since v0.6.35, which section A1 above says plainly; the user chose
them back on 2026-08-02. CLAUDE.md carried the same dead claim and it went
with it.)*

---

# THE GUNPLAY DESIGN (settled, ready to build)

A three-way design panel was run and judged; the "weight and consequence"
approach won. What it settled, and the two traps it caught:

- **The muzzle position must come from the GENERATOR via the manifest**,
  never derived in GDScript. This is the door-collider lesson verbatim: a
  hand-derived offset is exactly how the open-door collider ended up a
  cell away from its own art for a whole release.
- **`fire` must NOT go in `Settings.BIND_ACTIONS`.** That list erases every
  event on each listed action and replaces it with an `InputEventKey`, so a
  mouse binding is silently destroyed on the first settings load — which is
  why the mouse-wheel zoom actions are already excluded from it.
- Continuous mouse aim is authoritative; the 8-facing sprite is a READOUT
  of it, with a small deadband so a cursor parked on a facing boundary does
  not flip the row every frame at 240 Hz.
- Weight comes from TIME and PIXELS, not scale or rotation (both banned):
  a fire-rate gate, recoil that visibly shoves the reticle off the mouse
  and drifts home, a whole-screen-pixel camera kick, and a tracer with real
  flight time so the impact lands after the report.

The GENERATOR CODE is written and waiting — but **no sprite has ever been
produced**, so M2's art step is three moves, not zero. `make_muzzle_flash`
(gen_art.py:3091, 2 frames x the 8 facings in `GUN_DIRS`, since rotation is
banned), `make_tracer` (:3142, a warm head distinct from the sniper's) and
`make_impact_frames` (:3158, impact grit) all have **zero call sites**, and
the save block never emits them — it writes the sniper's round at :7089 and
nothing for these three. So `art/gen/` holds no muzzle/tracer/grit file and
`manifest.json` has no such key. **Add the `.save()` calls to the emit
block, re-run `python tools\gen_art.py` (plus the orphan-import cleanup and
`--import`), and only then wire it in GDScript** — the manifest is where the
muzzle origin has to come from, per the trap named above. (This line said
"art already generated and waiting", which would send an M2 session hunting
a manifest key that has never existed.)

---

# Milestones — the road to 1.0

Full design detail lives in `DESIGN.md` §8; `LORE.md` carries the world
bible. **1.0 = the complete v1 game.** Minor versions bump only when a
milestone lands; everything else is a patch (0.6.x). With the history
renumbered to fifteen per minor line, if 0.6 fills up before guns land it
keeps counting (0.6.16, 0.6.17…) rather than stealing 0.7.

- **M1 — a walkable world. DONE.** Shipped across v0.1.2 → v0.6.x: the
  fixed transit district, barricade ring and sniper buffer, weather and
  a day/night cycle, driveable cars, interiors with second floors, the
  map screen, three working extractions, and the debrief.

- **M2 → v0.7.0 — GUNPLAY, TUNNELS, STORY.** *Starts on the user's
  "go".* Mouse aim, hitscan with tracers, muzzle flash, screen shake,
  destructible props, synthesised gun sounds. Plus the **underground
  tunnel system**: secret bookshelf passages in some houses, exactly
  **two** interactive street manholes, F-interact ladders down *and*
  back up, dark tight corridors where the flashlight matters. Plus the
  **story opening**: "the wire", a ~2 minute painted cinematic that
  dissolves through dawn mist straight into gameplay, and mara's
  walk-in tutorial (her radio is already built and reusable — there is
  no voice acting and there won't be; the squelch and the clipped
  dispatcher writing *are* the performance).

- **M3 → v0.8 — human enemies.** AI raiders. **Human only — no
  machines** (user call). Enemy red/orange accents are specced.
  `Raid.record_kill(who, bone, is_player)` and the hit-location doll
  already exist for this.

- **M4 → v0.9 — the loop, with Tarkov-style loot.** Grid inventory,
  containers, a character doll with gear slots, and **the stash**.
  This is where persistence between raids finally lands — right now
  nothing carries over, which is why `Raid.money` is a stub and the
  debrief says "carrying nothing worth the trip". **No rarity colour
  tiers** (user call).

- **M5 → v1.0 — fake-player bots, lighting, the trader.** Bots that
  read as other raiders, the real lighting pass (the "graphics quality"
  setting is stored but drives nothing until this), and trading.

- **M6 → v1.1 — quests.** The safehouse power box repair (B5 above) is
  the first one and is deliberately built to be quest fodder.

- **M7 → v1.2 — a second map.** **DO NOT reuse the transit district
  system for this.** DESIGN.md §8.7 carries a HARD RULE (user call,
  2026-08-01): every map is structurally *nothing* like transit — no
  reruns of roads, houses, warehouses or tunnels — and each is built
  for massive scale and depth. The mills = one colossal continuous
  interior (halls, catwalks, furnaces); the harbor = water *as* the
  map (piers, container canyons, ships, rowboat crossings); the old
  ward = an alley warren with courtyards and a rooftop road. The
  spires are end-game and unnumbered. The next district is the one off
  mara's board; LORE.md §3 has the map canon. The only transit
  machinery that carries over is generic plumbing (the seeded builder,
  `map_vec` including its unused `water` slot) — not the zone layout.
