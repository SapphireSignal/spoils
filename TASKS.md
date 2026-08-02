# SPOILS — open work

Everything outstanding, with the diagnosis already done. **Read
`CLAUDE.md` first** (project rules, systems map, verification workflow),
then this file for what to actually build. `CHANGELOG.md` records what
already shipped.

Ordered roughly by what's worth doing first. Every item says what is
already known so nothing gets re-derived.

---

## 1. Doors: solid at all times — SHIPPED v0.6.68, awaiting the user's eye

Asked four times. Fixed; the user has not seen it in a playtest yet.

**The old diagnosis in this file was WRONG — do not resurrect it.** It
claimed the leaf "opens roughly in place" because the sprite centroid
only moved cx 23.5 → 23.8 across the four frames. That reading is a
trap: in iso *both* ground axes point +x, so a correct 90° turn barely
moves the centroid sideways. Measuring the leaf's free end instead
shows it always went from `(+20,+10)` to `(+20,-10)` off the hinge — a
proper quarter turn into the room. The art was never the problem.

**The three real bugs, all measured:**
1. `Door._swung_points` derived the open collider as `(-along.x,
   along.y)`. Correct for east (`y`) doors, **180° wrong for south
   (`x`) doors** — the panel sat a full cell on the opposite side, so
   south doors were ghosts. Most doors are south doors.
2. The east door's open frames **ran off the left of their canvas** and
   were silently cut. `door_` was on the clip-audit exemption list, so
   the build never complained.
3. The open leaf used **wall** thickness. At that thickness the swung
   panel reached back across its own doorway and sealed the middle,
   leaving a 4.4 px corridor — narrower than the player.

**What shipped:** the leaf now rotates in the ground plane and is
sampled along its screen run (the old code lerped the step vector,
which under-sampled the middle frames — east doors lost most of their
leaf and their handle). Canvas 48×60 → 54×66. `door_` removed from the
clip-audit exemption. The panel is door-thickness. The jamb boards got
real colliders, so an open door no longer lets you walk through the
boards beside the opening. Mid-swing **both** panels are solid, so a
door that still looks shut cannot be walked through. Every polygon now
comes from the generator via `manifest.collider_open` /
`collider_jambs`; `Door` derives nothing.

**If the user still reports walk-through:** ask which door and whether
it was open, shut, or mid-swing, and get a zoomed screenshot. The smoke
now covers all three states for real (see below).

---

## 2. Second floors: furniture floats — FIXED v0.6.69

**Root cause: DRAW ORDER.** A second floor is a horizontal plane, and
y-sorting a plane against vertical walls cannot work. The container is
anchored far north so the player always sorts above it — which also
put it behind the building's OWN wall segments, sitting at much larger
y. The walls painted over most of the slab, leaving a band of boards
and furniture apparently standing on nothing.

**Fix:** `_set_upper_state` gives the upper floor its own z band while
you are on it — slab at 1 (over the ground floor and its walls),
player + upper props + the staircase at 2 (over the slab). All back to
0 on the way down, so nothing outside that building is affected. The
staircase needs to be in the band explicitly or the new floor
swallows it.

**Tooling:** `--upstairs=<n>` puts the player on second story *n*,
prints `upstairs/lift/cells` and the slab's `visible/children/pos`,
and is shot-able. Use it if this ever regresses.

*Everything below is the record of how the old leads were killed —
kept so nobody resurrects them.*

## 2b. The old leads (both dead, for the record)

**Repro:** a two-story house **at the courtyard** — climbing the stairs
shows the upper *furniture* but no upper *floor*.

**Both of the old leads are DEAD. Measured on transit-01, do not
re-derive:**
- `--probe-world` now prints
  `UPPERS total=6 floorless=0 propless=0 stairs=6`. Six flights, six
  registries, and **every** upper container has its floor sprites. So
  there is no index mismatch and no unbuilt upper.
- The "`_plan_plots` upgrades stories after the shell is built" lead is
  false: `build()` awaits `_plan_plots()` *before* the `_build_shell`
  loop, so the quota upgrade always lands first.
- An index mismatch is structurally impossible anyway —
  `main.gd` connects `used` with `_on_stairs_used.bind(i)` where the
  stairs node is read out of `_uppers[i]` itself.
- `_build_upper` paints **every** cell unconditionally, and the tile
  maths is correct: a tile's global position works out to
  `map_to_local(cell) + (0, -story_h)`.

**So the slab is built and it is not being seen — this is DRAW ORDER
or visibility, not construction.** The strongest remaining lead: the
upper container is anchored NORTH of the whole footprint
(`map_to_local(interior.position) + (0, -24 - story_h)`) so that it
y-sorts under the player. But it sorts as ONE unit at that far-north
position, which puts it *behind* every ground-floor wall segment of the
same building — and those walls are drawn at their own, much larger y.
The upper furniture keeps its TRUE cell position, so it sorts late and
stays visible. That is exactly the reported symptom: furniture visible,
slab hidden behind the ground floor's own walls. Test by temporarily
hiding the ground-floor walls while upstairs, or by giving the slab its
own sort position south of the walls.

**Also asked:** sweep every interior — houses, warehouses, school,
safehouse — for furniture that floats, sits in a wrong spot, or
overlaps.

---

## 3. Flat ground props draw over the player

**Repro:** a small flat orange-brown object on the ground renders **on
top of** the raider standing on it, so walking over it reads as walking
through it. The user confirmed it does **not** block — this is purely
draw order.

**The fix already exists:** `_flat` in `world_builder.gd` (added v0.6.53
for the interior cables) is a `Node2D` sibling between the floor
`TileMapLayer` and the y-sorted `_ysort`. Anything lying flat belongs
there. Add a helper mirroring `_add_cable` and route flat props through
it.

**Trap:** do **not** use a negative `z_index` inside `_ysort`. z sorts
globally within the canvas layer, so the sprite disappears behind the
floor entirely — this is exactly what happened to the cables.

Sweep the catalogue for others that read as ground: spilled trash,
paint, spray cans, painted markers. Anything with real height stays
y-sorted.

---

## 4. Power box repair — the first quest interaction

1. Standing near the broken box plays a **subtle spark sound**
   (positional, quiet — standing rule: one-shots ≤ -18 dB, on the `sfx`
   bus).
2. A prompt: **"press f to open the power box"**.
3. F opens a **window** showing the broken box **and the player's
   inventory**, with text **"drag electricians kit on the power box"**.
4. Dragging the kit onto the box plays a **wire-cutter animation** of a
   couple of seconds.
5. It is then **repaired**: no further interaction, and it **stops
   sparking** (kill the arc, the glow and the thrown blue sparks).

**Needs:** a stub inventory holding an "electricians kit" (the real
inventory is M4), drag-and-drop in the window, cutter animation frames,
a repaired box sprite, and a repaired state in `power_box.gd`. The box
is pinned to the safehouse (v0.6.46), so it is always findable.

---

## 5. Cosy safehouse

**Inside:** a bookshelf, a cabinet and a TV (families `bookshelf`,
`cabinet`, `tv_stand` exist — check whether a TV sprite exists
separately), plus **posters and pictures on the walls**. The posters
are new art: wall-face decals, like the graffiti walls. Mind that walls
are drawn as segments and only the camera-facing interior faces are
visible.

**Outside:** a little **dirt road from the safehouse door to the
nearest POI**. Reuse `_walk_dirt_path(from, to)` with the safehouse's
`door_out` cell and the closest POI centre — it already skips roads and
slabs.

Keep it restrained; the user's standing note is that too many objects
looks odd.

---

## 6. Flashlight shines through walls

Standing **inside** a building, the flashlight cone is visible
**outside** — it passes through the wall. It should only light the
interior while you're inside.

Godot 2D lights ignore walls without occluders. Either add
`LightOccluder2D` to the wall segments built in `_build_shell`, or take
the cheap route: `main.gd` already tracks which interior cells the
player is in for the roof reveal, so the cone can be masked or shrunk
while inside.

**Check the same leak** on the interior room lights (v0.6.53) and on
street lamps standing near buildings.

---

## 7. Warden: opposite sidewalk, facing the road

He sits on the wrong side and faces away — "hes like facing the void" —
which makes pulling up awkward.

`_toll_booth_cell()` returns `Vector2i(road.x + 1 + 3, MAP_H - 1 -
BARRIER_INSET)`; the `+3` puts him on one side, so mirror it to the
other side of the road band. `_place_barricades` reserves his cells via
`_toll_reserve` using the **same helper**, so changing the helper moves
both together. The booth art may need a mirrored facing so the window
faces the asphalt — check `toll_booth` in `gen_art.py`. Re-verify
`TollGate.setup`'s boom offset (currently -4 cells along x) still spans
the road, and that the extract zone beyond the wire still lines up.

*(Talking to him from a car already works — shipped in v0.6.67.)*

---

## 8. Door sound: a real creak

`Sfx.play_door(open)` plays `_synth_blip` tones, which read as a thunk,
not timber. Either synthesise a creak (a slow pitch-sweeping resonant
scrape with irregular stick-slip amplitude, plus a soft latch thunk on
close) or source a CC0 recording the way the car doors and thunder were
(licences in `assets/audio/LICENSES.md`; the ggbotnet CC0 pack is
already credited). **Ship it quiet on the first cut** — ≤ -18 dB, on
the `sfx` bus. The swing is 4 frames × 0.06 s ≈ 0.24 s, so the creak
should be about that long or it outlasts the animation.

---

## 9. Non-rectangular buildings

"make all the houses and warehouses and stuff like that not all a
square or rectangle... non-orthogonal layout or isometric tile
variations".

**This is architectural, not a tweak.** Plots are `Rect2i` end to end:
`_plan_plots`, `_rect_clear`, `_build_shell` (walls, roof, doors,
windows), `_furnish_*`, `RoofReveal.cells`, the upper-floor containers,
`_claim_building_ground`, and the map screen's building rects all
assume a rectangle.

**Suggested approach:** keep a bounding `Rect2i` but add an optional
**cell set** (an L or T from two unioned rects), and drive wall, roof
and interior generation off cell membership plus neighbour masks rather
than rect edges. The wall art is **already neighbour-masked**, which is
the piece that makes this feasible. Expect the roof reveal and the map
drawing to need matching work.

Do it **sample → user sign-off → fleet**, per the process rule.

---

## 10. Changelog entries: one string per bullet

`CHANGELOG_ENTRIES` in `main_menu.gd` stores each entry as an array of
strings, and the renderer prefixes **every** element with `- `. Entries
were hand-wrapped across several strings, so one sentence got a dash on
every line.

The labels already autowrap, so the convention is **one string per
bullet, unwrapped** — the renderer needs no change. **Done:** v0.6.65,
v0.6.66, v0.6.67. **To do:** every entry from v0.6.64 down to v0.6.3 —
merge each hand-wrapped run into one string per idea, keeping the
wording. Note the menu's version label derives from
`CHANGELOG_ENTRIES[0][0]`, so don't disturb ordering or version strings.

---

## Older standing queue (pre-dates this session's batch)

- **Pickup bed** — shade the interior so it reads as a container, put a
  box in it, sample sheet across all angles. *Sample → sign-off first.*
- **Catalogue variety** — families still on two variants (bench,
  dumpster, shelter, vending, newsbox, forklift, planter, swing) plus
  singleton crane/sandbox. The deeper fix is parameterising the
  builders so **shapes** differ, not just wear.

## Waiting on the user

- **M2 — guns, tunnels, story (v0.7.0).** Starts on their explicit
  "go".
- **Trailer concept.** Pitches were sent; they pick one before anything
  is built. ffmpeg is **not installed** on the box.
- **Door option A vs B** (item 1) — B is recommended and explained.

---

# Milestones — the road to 1.0

Full design detail lives in `DESIGN.md` §8; `LORE.md` carries the world
bible. **1.0 = the complete v1 game.** Minor versions bump only when a
milestone lands; everything else is a patch (0.6.x).

- **M1 — a walkable world. DONE.** Shipped across v0.2.0 → v0.6.x: the
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

- **M6 → v1.1 — quests.** The safehouse power box repair (item 4 above)
  is the first one and is deliberately built to be quest fodder.

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
