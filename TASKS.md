# SPOILS — open work

Everything outstanding, with the diagnosis already done where there is
one. **Read `CLAUDE.md` first** (project rules, systems map, verification
workflow), then this file for what to actually build. `CHANGELOG.md`
records what already shipped.

**Current version: v0.6.31.** The release history was renumbered evenly on
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

- **Real 2D shadows.** `LightOccluder2D` on the wall segments so lamps and
  the flashlight cast actual shadows. Single biggest atmosphere change
  left, and it fixes B7 (flashlight through walls) in the same stroke.
- **Glow / bloom** via a `WorldEnvironment`. The renderer is Forward+, so
  it is available. Lamps, lit windows, sparks, the muzzle flash and the LZ
  smoke would bleed light properly instead of being flat bright pixels;
  right now the grade only fakes it with a highlight lift.
- **Directional cast shadows** from props and the player, angled to the
  sun and swinging through the day. Everything shares one static blob now.
- **Wet-ground reflections** in rain; **contact shadows** so props sit in
  the world rather than on it; **window light spill** onto pavement at
  night; **heat shimmer** at midday.
- **Sway shader** on bushes and trees — a WHOLE-PIXEL horizontal offset,
  never a rotation.
- NOT recommended: depth of field, chromatic aberration, motion blur.
  They fight pixel art and just smear it.

Agreed order for the remaining art work:

1. **The in-game map screen (M).** *(user: "its like some minecraft map")*
   It is drawn as flat coloured rectangles — building footprints as solid
   fills, roads as grey bands — so it reads as a diagram. It should read
   as a DRAWN MAP: paper-toned base, ink edges, hatching for the woods,
   the rail as a ladder, the wire as a broken red ink line. **Every POI
   gets its own drawn glyph** instead of a text label — a bus for the
   depot, a crane hook for the scrapyard, a chimney for the warehouse, a
   swing for the playground, a mast for comms, a boom for the toll gate,
   a home marker for the safehouse.
2. **The map-select tile.** *(user)* Currently a 96×96 mini-map of grid
   and orange/green blobs, stretched 1.25× into a 120×120 button — so it
   is blurred as well as dull. Wants "an actual picture of the map from a
   scenic view, very detailed". **Generate at exactly 120×120** so it maps
   1:1. (This said the overlook backdrop could serve double duty; that
   pitch was dropped 2026-08-02, so the tile needs its own art now.)
3. **The title.** *(user: "its just white, and it goes up and down a bit
   thats all, it seems boring")* Needs real treatment — weight, depth, a
   material, something happening beyond a bob.
4. **UI and icons** — buttons, panels, the HUD.
5. **The player model.**
6. **World objects and textures.**

## A1. Menu backdrops — FOUR pitches, the user picks a couple

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

## B5. Power box repair — the first quest interaction

1. Near the broken box: a subtle spark sound (positional, quiet — the
   standing rule is one-shots ≤ -18 dB on the `sfx` bus).
2. Prompt: **"press f to open the power box"**.
3. F opens a window showing the box **and the player's inventory**, with
   **"drag electricians kit on the power box"**.
4. Dragging the kit plays a wire-cutter animation of a couple of seconds.
5. Repaired: no further interaction, and the sparks, arc and glow stop.

Needs a stub inventory holding an "electricians kit" (the real one is M4),
drag-and-drop, cutter frames, a repaired sprite, and a repaired state in
`power_box.gd`. The box is pinned to the safehouse so it is always
findable.

## B6. Cosy safehouse

**Inside:** bookshelf, cabinet, TV, plus **posters and pictures on the
walls** — new art, wall-face decals like the graffiti walls. Mind that
walls are drawn as segments and only the camera-facing interior faces
show. **Outside:** a little dirt road from the safehouse door to the
nearest POI — reuse `_walk_dirt_path(from, to)` with the safehouse's
`door_out` cell and the closest POI centre; it already skips roads and
slabs. Keep it restrained.

## B7. Flashlight shines through walls

Standing inside a building, the cone is visible outside. Godot 2D lights
ignore walls without occluders. Either add `LightOccluder2D` to the wall
segments built in `_build_shell`, or take the cheap route: `main.gd`
already tracks which interior cells the player is in for the roof reveal,
so the cone can be masked or shrunk while inside. **Check the same leak**
on the interior room lights and on street lamps standing near buildings.

## B8. Warden: opposite sidewalk, facing the road

He sits on the wrong side and faces away — *"hes like facing the void"* —
which makes pulling up awkward. `_toll_booth_cell()` returns
`Vector2i(road.x + 1 + 3, MAP_H - 1 - BARRIER_INSET)`; the `+3` puts him
on one side, so mirror it. `_place_barricades` reserves his cells via
`_toll_reserve` using the **same helper**, so changing the helper moves
both together. The booth art may need a mirrored facing so the window
faces the asphalt. Re-verify `TollGate.setup`'s boom offset still spans
the road, and that the extract zone beyond the wire still lines up.

## B9. Flat ground props draw over the player

**Repro:** a small flat orange-brown object renders **on top of** the
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

## C2. v0.4.3 has no in-game changelog entry

It has a git tag and a `CHANGELOG.md` entry but no `CHANGELOG_ENTRIES`
row — the policy says every version gets one. Write it from the commit.

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
- **Which menu backdrops to keep**, once all five are painted.

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
