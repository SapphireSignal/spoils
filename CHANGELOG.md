# Changelog

All notable changes to SPOILS are documented here. Versions follow a simple
`0.minor.patch` scheme while the game is pre-release.

## [0.6.77] - 2026-08-07 - the second floor is a floor

### Fixed - the stairs were drawn straight through the upper floor
*"i can see the top of the stairs, it should all be clean like the bottom
floor"*. The flight rose through the slab and sat on the floorboards, so a
complete floor had a staircase growing out of it.

The slab covers the flight while you are standing on it now — **art AND
collider together**. Hiding the art alone would have left a solid thing you
cannot see in the middle of the room, which is the complaint one line further
down the same report. Going back down is a proximity prompt, not a collision,
so nothing is lost.

### Fixed - the stairs prompt still said "go upstairs" from upstairs
The prompt text is cached and only rebuilt when the target or a door's
open-state changes, because `bind_label` asks the display server and must not
run per frame. **The floor was not part of that cache key** — and climbing
does not change the target, it is the same `Stairs` node — so the prompt kept
reading *"press f to go upstairs"* while you stood on the second floor. It
reads "back down" now.

### NOT REPRODUCED - and I had one of them wrong
- **"i clip inside of the floor"** — I recorded this as confirmed off a
  screenshot and it was **my mistake**: what cut the character in half was the
  HUD prompt label sitting across their legs, in that shot and in every other.
  An aligned frame diff settled it — removing the stairs changed the stairs
  region and **nothing where the legs are**. At the room centre the player
  draws complete, feet on the boards.
- **"i clip on stuff when walking around"** — no invisible collider exists up
  there. `--probe-upper` lists every body still on a collision layer inside
  the upper room: **19 solid, 0 invisible** — 14 wall segments and posts, the
  door, the stairs and 4 pieces of furniture, every one of them drawing.

Both need a repro before anything is changed. Guessing at them would mean
rebuilding a system that measures clean.

### Added - `--probe-upper` and `--upstairs-at=dx,dy`
The probe enumerates solid-but-invisible bodies in an upper room, which is the
only honest way to answer "am I clipping on something up here". `--upstairs-at`
stands the player at the room's CENTRE plus an offset — anchored to the centre
rather than the stairs cell, because offsetting from the stairs walked straight
out of the room and put the roof back over the shot.

### Verified
`FLOORDOOR PASS` still, DOORS 16 on identical cells, UPPERS 6 with floorless=0
propless=0. `SEC PASS`, `DOCS PASS`, `CLAIMS PASS`, `SMOKE PASS`.

## [0.6.76] - 2026-08-07 - the front door stays open when you go up

### Fixed - climbing the stairs slammed the front door
*"when going up the stiars to a second floor, the main door entrance closes
automatically, it should stay open"*.

It was doing it **on purpose**, and the reason is real, so this is not a
deletion. `_build_upper` lays floor tiles and nothing else — the upper room
reuses the GROUND SHELL for collision — so an open ground-floor doorway is a
genuine hole at storey height, and someone walked out of one. The old guard
shut the door behind the climber to plug it.

The doorway is sealed for **collision only** now (`Door.set_floor_blocked`),
while the door keeps its state, its frame and its silence. The occluder stays
tied to the VISUAL state on purpose: the door looks open, so light still comes
through it. This is a floor abstraction, not a door that quietly shut itself.

`force_closed()` had exactly one caller and is gone with it — recoverable from
git history if a real one ever appears, the same call made for
`_scatter_around` in v0.4.12.

### Added - `--probe-floordoor`
Two things have to hold at once here and they pull against each other, which
is why this is a probe and not a screenshot: the door is still open upstairs
**and** the doorway is still solid up there. It also checks the seal lifts on
the way back down, and that dying upstairs does not leave a building's
doorways solid for the rest of the raid.

**The first cut of it reported a false FAIL, from the mistake CLAUDE.md
already names:** it measured crossing along the through-axis, where the two
iso ground axes sit only 53 degrees apart, so an **18.2 px slide along the
wall** read as walking through a sealed doorway. It measures against
`doorway_normal()` — the wall plane — now. The probe prints `solid=` beside
the movement result as a liveness figure, and that is what showed the seal was
working and the *measurement* was wrong.

### Verified
`FLOORDOOR PASS`: open before/upstairs/after all true, `upstairs solid=true
crossed=false`, `downstairs solid=false crossed=true`. DOORS 16 on identical
cells, UPPERS 6 with floorless=0 propless=0.
`SEC PASS`, `DOCS PASS`, `CLAIMS PASS`, `SMOKE PASS`.

## [0.6.75] - 2026-08-07 - opening a door stops shoving you

### Fixed - a door pushed the player back when opened from close up
*"how come when im close to the door, and i open it, it pushes me back a bit?
i should stay in place"*.

v0.6.72 gave the leaf its own sort position by moving the DOOR NODE and pulling
every child back to compensate. That is correct on paper - the colliders end up
in the same global place - but **the node is a `StaticBody2D`, and nudging a
static body the player is resting against depenetrates them.**

Measured, standing at several distances and opening:

| distance | v0.6.74 | with the shift off | now |
|---|---|---|---|
| 22 px | 0.00 | 0.00 | 0.00 |
| 14 px | 2.24 | 0.00 | 0.00 |
| 10 px | 3.16 | 1.12 | 1.12 |
| 6 px  | 3.35 | 1.12 | 1.12 |

Only the SPRITE moves now, with `y_sort_enabled` on the door so it carries the
depth on its own. **The body never moves at all**, and the shove is back to the
pre-existing baseline at every distance.

**The probe stood 22 px away by default - comfortably clear of the sweep -
which is why it never saw this.** `--door-dist=N` sets the standing distance
and every run prints `SHOVED=`.

### Still open
**~1.1 px of shove remains within about 10 px of a doorway, and it predates all
of this** (the column above shows it unchanged with the shift removed
entirely). It comes from the swung leaf's collider going solid the instant you
press the key, which is deliberate - it stops you walking through a door that
still looks shut. Not chased.

### Verified
All four earlier invariants re-checked: player behind an open leaf still
hidden, the straddling facing still whole, closed door still **0 changed
pixels** in the wall band against v0.6.72, and **no brick-for-brick swaps**.
`SEC PASS`, `DOCS PASS`, `CLAIMS PASS`, `SMOKE PASS`.

## [0.6.74] - 2026-08-07 - the other half of the doors

### Fixed - an open door sliced into the wall on HALF the district's doors
*"i dont think you tested it on a building like the safehouse, the door needs
to be on a specific facing wall for it to show this glitch, its still
happening"*. Correct on every count.

**The sort key was the leaf's CENTROID.** On one of the two wall facings the
open leaf STRADDLES the wall line - hinge end at it, far end standing out in
front - so the centroid depth is exactly **0** while part of the leaf really is
in front of the wall. The whole sprite then sorted level with the wall it was
standing in front of, and the wall drew over its protruding corner. **8 of the
16 doors in the district are that facing** (`--probe-world` prints the table
now: `span_out=-7.4..7.4 straddles=true`).

The key is the leaf's **leading edge** now - the extreme in the direction of
travel, `span.y` swinging out and `span.x` swinging in - so a leaf clears its
own wall by construction on either facing. On the straddling doors the shift
goes 0.0 -> 7.4; on the others 10.0 -> 17.4.

### Fixed - the probe could not see half the doors
`--door=` picked the door with the DEEPEST outward leaf, which always lands on
the same facing. **The probe was built around the bug it was written to catch,
so it never once shot the other half of the district across three releases of
door work.** `--door-pick=N` selects any door, and the run now prints every
door with its depth, span and a `straddles=` flag, so a facing cannot go
untested by accident again.

### Verified
Reproduced first, with the shift neutralised: the wall visibly drawn over the
leaf's top corner. After: whole leaf, standing clear. The three invariants from
v0.6.72-73 all re-checked on the deep facing - player behind an open leaf still
hidden, closed door still **0 changed pixels** in the wall band against v0.6.72,
and **no brick-for-brick swaps** when a door opens.
`SEC PASS`, `DOCS PASS`, `CLAIMS PASS`, `SMOKE PASS`.

## [0.6.73] - 2026-08-07 - the jamb boards leave the door

### Fixed - the wall beside a door changed when the door opened
*"you can see theres a line beside the door when its closed, and not anymore
while its open, the side of the door like changes when opening it, not the
door, the wall right beside it"*. **A v0.6.72 regression, and one that release
predicted and shipped anyway** as an acceptable cost. It was not: the user
found it immediately in ordinary play.

The jamb boards down each side of a doorway are structurally WALL, but they
were composited into the door sprite - so leaf and wall were ONE NODE, and
giving the leaf its own sort position dragged the wall's draw order with it.

Measured rather than judged. In the wall band beside the door, opening it
swapped **272 pixels between two BRICK renderings** - `(82,109,119)` against
`(50,66,75)`, wall for wall. With the shift neutralised: **0**. The boards are
their own piece now, placed by the builder in the building's own style, the
same move v0.6.67 made for the header. After: **0**, and what remains in the
frame is the leaf's own edge sweeping across the wall, which is what an
opening door does.

`door.gd` carries a sub-pixel `JAMB_EPS` so the leaf cannot TIE with the
boards: two of the four kind/axis combinations have zero leaf depth, and
y-sort has no defined winner for a tie. Its sign matches the ordering
`make_door_strip` used to guarantee by draw order - out, the leaf covers the
jamb; in, the jamb covers the leaf.

### Fixed - a black bar between every doorway and its wall
Splitting the boards out exposed a second defect and then briefly made a
third. The jamb piece outlined ALL round, including the joins against the wall
and against the leaf - `outline_auto`'s own docstring says pieces that tile
edge to edge must not do that, which is why wall segments pass `sides=False`.
A jamb IS a wall segment. The first cut of the split put a **2 px black bar
between the wall and every shut door, measured at 140 px**; with `sides=False`
the closed door is **byte-identical in that band** to what v0.6.72 shipped,
and the pre-existing dark line on the far side of the opening is gone too.

### Fixed - an open leaf read as sunk INTO the wall
*"the door clips in the wall when its opened outside"*, on both a wood door in
masonry and a metal one in brick. Suppressing the outline where the leaf meets
the jamb is right **only for the SHUT frame**, where the leaf genuinely is part
of the wall plane - and the first cut carried it into the swung frames too, so
an open leaf butted against brick with no edge at all.

Only `f % DOOR_FRAMES == 0` is flush now; every other frame outlines the leaf
on its own, because in those it stands clear of the wall. The remaining
brick-to-outline pixels when a door opens are exactly that silhouette drawn
over the wall it stands in front of - **the swap list is the check: 140
brick-to-outline and ZERO brick-to-brick**, where v0.6.72 was 272
brick-to-brick.

### Verified
Closed door vs v0.6.72: **0 changed pixels** in the wall band. Shut vs open:
**no brick-for-brick swaps at all**. The player standing behind an open leaf is still fully hidden, so
v0.6.72's fix is intact. `--probe-world` DOORS **16** on identical cells - the
new piece takes no rng draw, so the fixed district did not reroll. 240.0 fps,
worst frame 4.71 ms, 8374 nodes (+16, one board pair per door).
`SEC PASS`, `DOCS PASS`, `CLAIMS PASS`, `SMOKE PASS`.

### Housekeeping
B0d closed by the user in play - *"b0d already fixed, dont need to do that"* -
the third item this session closed by playing rather than by code.

## [0.6.72] - 2026-08-07 - the open leaf finally hides you

### Fixed - an open door drew behind the player standing behind it
*"i can still see my character when he should be behind the door"*.
**Not the v0.6.71 tie-break** - that closed B0e and is verified clean. A door
node sits on the WALL LINE while an open leaf stands up to **10 px toward the
camera**, and y-sort orders by the NODE - so the leaf could never occlude
anyone behind it, however far it swung. The sprite's screen extent and its
sort anchor disagreed.

The node is now pushed to where the leaf really stands and **every child is
pulled back by the same amount**: the sort key moves, the art and the
colliders do not. The depth comes off the manifest polygon rather than being
derived here (the door-collider lesson), and compensating every child rather
than a named list means a child added later cannot silently slide off the wall
whenever a door opens.

`_panel_center` had to start counting the child's own position, or every
helper on the class - and `--smoke`, which aims at them - would drift by the
shift the moment a door opened. `main.gd` uses a new `wall_position()` at the
two places that ask which cell a door is in and how far the player is from it.

**Proven with an A/B on one frame**: same door, same pose
(`player_y-leaf_y=-10.0` in both runs), the only variable the shift. Before,
the character draws over the open leaf; after, they are completely hidden by
it. Stood in front of the leaf instead, they are still fully drawn - the shift
does not overshoot.

**A known cost, stated rather than left to be rediscovered:** the jamb boards
are structurally wall but ride the leaf's sprite, so they take the shift with
it. Bounded, and written up in TASKS.md B0h.

### Added - `--door=behind` and `--door=front`
There was no probe for occlusion and `--smoke` cannot see it. Both print
`shift=` and `player_y-leaf_y=` as liveness figures beside the pose, because
**the first shot came back `shift=0.0`**: `get_first_node_in_group("doors")`
returns a door this bug cannot happen on - only two of the four kind/axis
combinations move in y when they swing - so the frame looked perfect while
measuring nothing.

### Housekeeping
`TASKS.md` carried two `B0b` sections and two `B0c` sections, one open and one
done in each pair, while `HANDOFF.md` points at "B0c, the second floor". The
completed ones are now `B0j`/`B0k`. B0g (3 px above a door) and B0i (door vs
wall contrast) are closed by the user in play - nothing shipped between the
complaint and the verdict, so their measurements are kept and the verdict is
theirs.

### Verified
`SEC PASS`, `DOCS PASS`, `CLAIMS PASS`, `SMOKE PASS`.

## [0.6.71] - 2026-08-06 - the player loses ties to the scenery

### Fixed - drawing over a wall at exactly equal depth
*"he should be behind the door right now but i can still see him"*.
**A v0.6.63 side-effect.** Snapping the player's node onto the pixel grid
fixed a measured 46% wrong-order rate near the character - but it also put the
sort key on the **same whole-pixel grid the walls and props already sit on**,
so EXACT depth ties became common. Y-sort has no defined order for a tie, so
the player could win against a wall they were standing behind.

The node now sits **0.002 px above the grid**. That is far below a pixel, so
it rasterises identically and the v0.6.63 guarantee still holds - it only
decides ties, and it decides them the safe way: **at equal depth the player
goes behind the scenery.** Being hidden by something you are standing behind
is right; clipping through it never is.

Measured with `--probe-sort`: 810 px walked, **0 disagreements**, max offset
0.002 px.

### Verified
`SMOKE PASS`, `--probe-sort` clean.

## [0.6.70] - 2026-08-06 - the door header follows the slope (8 px -> 3 px)

### Improved, NOT finished - the gap above a door
*"its still cut off at the top a bit ... i shouldnt see anything from
outside"*, with the spot circled. Measured column by column, and the header
was wrong in a way a screenshot could not show:

**the header's bottom was a flat horizontal line while a doorway's head
follows the (2,1) iso slope**, so it sealed one end of the opening and left a
hole that widened to **8 px** at the other.

Two rules were tried and both measured:
- *keep every row above the door's topmost pixel in this column* - down to
  3 px, but it stops at the first covered row and drops any wall further down
- *keep every wall pixel the shut door does not cover* (shipped) - exact by
  construction, since the union of the two is the whole segment

**It measures 3 px at worst, not 0.** The remaining gap is columns where the
wall SEGMENT itself has no pixel above the door's top edge, which a header cut
from that segment cannot fill. `TASKS.md` carries the measurement script and
the next step.

### Changed - the vehicle engine start is 6 dB quieter
*"decrease the engine sound, its too loud ... like the engine startup sound
... for the vehicles"*. It sat at **-18 dB, exactly the ceiling the standing
quiet rule sets for one-shots** - already the loudest a new sound may ship at -
and then v0.6.66 added +3 dB on the master for everything, which pushed it
over. Now -24 dB (and the shutdown -25, keeping the 1 dB it always sat below
the start), so it lands below where it was even before that trim.

### Verified
`SMOKE PASS`, `DOORS` 16 on unchanged cells. Worst gap 8 px -> 3 px.

## [0.6.69] - 2026-08-06 - two of my own regressions

### Fixed - the camera stopped following vehicles
*"when im in vehicles the camera doesnt follow the vehicle"*. **A v0.6.63
regression.** That release made `_true_pos` the authority for the player's
node position, and the camera derives the snapped node position from it - but
the driving branch moves the player by writing `global_position` directly and
never handed `_true_pos` over. So the car drove off and the camera stayed at
the spot you got in. The `riding` branch (the night freight) had the identical
hole.

**A parse check and `--smoke` both passed while this was broken**, because
neither drives anything. `--probe-drive` now measures the one thing that
matters - the distance from camera to car, before and after the car moves:
**before 0.0, after 0.0, FOLLOWS.**

### Fixed - the roof lifted while you were still outside
*"i can see the inside of the building when im outside ... the roof should
only disappear when the user goes inside, like they go past the doorway"*.
**A v0.6.65 regression, and an over-correction of mine.** That release counted
"standing on a door cell" as being inside, to fix the player showing through
their own open doorway - but a door sits ON the wall line, so that cell reads
the same whether you are in front of it or behind it.

The interior rect is the whole test again, which is the rule as the user
stated it.

### Verified
`SMOKE PASS`, `--probe-drive` FOLLOWS.

## [0.6.68] - 2026-08-06 - the doorway reveal is wall, not door

### Fixed - the boards either side of a door were the door's colour
*"the side of the door is still not the same colour"*. The 6 px jamb boards
flanking the leaf are **the edge of the hole in the wall**, so they belong to
the building - but they were painted in the door's own material, which put
brown boards down both sides of grey masonry.

The door strip is generated per **style** as well as per kind and axis now, so
the jambs take that building's brick while the leaf keeps its own material. A
wooden door in a masonry building is intentional; brown *reveals* in a
masonry building were not.

This is the third piece of the same root cause, and worth stating plainly:
**the door KIND follows the building's purpose (wood for houses, metal
otherwise) while the wall STYLE is rolled independently, so neither can be
derived from the other.** Anything that is structurally WALL - the header, the
jambs - has to be told the style; only the leaf may follow the kind.

### Verified
`SMOKE PASS`, `DOORS` 16 on unchanged cells.

## [0.6.67] - 2026-08-06 - the door header is the building's own wall

### Fixed - the header above a door was the door's colour, not the wall's
*"can we make the door patch the same color as whatever building its on? and
i dont think it worked for the warehouses"*.

v0.6.66 sealed the hole above every door by drawing the header **into the door
art**, which cannot be right: the door KIND follows the building's purpose
(wood for houses, metal otherwise) while the wall STYLE is rolled
**independently** per building. A tan wood door legitimately lands on grey
`brick_b` masonry - so the header arrived the wrong colour on roughly half the
buildings, reading as a patch stuck over the wall.

The header is its own piece now, `door_lintel_<style>_<axis>`, placed by the
builder in **that building's** style beside the door - the same pattern the
two-storey transom already used. It is **cut from the real wall segment**
rather than redrawn, so it can never drift out of step with the wall it sits
in. (Same reasoning as the terrain fringes being composited from the real
tiles.)

**On the warehouses:** measured all four door/wall pairs and they were already
sealed geometrically - the complaint there was the same colour mismatch, since
warehouses are `brick_b` and can carry a wood door.

### Fixed while doing it - the clip audit was right
Cutting the band as a tight crop made the cut edge opaque and the generator's
CLIP AUDIT failed the build on all four pieces. That audit exists to catch
genuinely clipped art and is worth keeping, so the band keeps the segment's
FULL canvas with only the top rows copied and the rest transparent - it then
touches exactly the edges the wall segment already touches. **No exemption
was added.**

### Verified
`SMOKE PASS`, `DOORS` 16 on unchanged cells, 240 fps.

## [0.6.66] - 2026-08-06 - doors that seal, trucks that differ, a louder mix

### Fixed - every door had a hole above it
*"theres still a hole at the top of all the doors that lets the user see
inside the house before he even goes inside"*. **Measured rather than
eyeballed:** the closed leaf topped out at -45 world px above its anchor while
the wall segments either side reach -50. **A door cell gets no wall segment**
- the door prop replaces it - so those 5 px were a hole straight into the
building, visible through a shut door.

The door now draws a LINTEL across the full opening, both jambs included, on
every frame (an open door still has a header over it). The frame grew 68 -> 78
and the hinge dropped 50 -> 60 **together**, which is a no-op for placement:
`origin` is computed from the hinge and the sprite draws at `-origin`, so
shifting both cancels exactly - it only buys blank rows to draw into.
Re-measured: door top -51, wall top -50. Sealed.

### Fixed - the three identical trucks, for real this time
v0.6.65 fixed the ROAD vehicles and **missed the call site that actually made
them** (*"i still see these three same trucks outside the warehouse, i thought
you fixed that"*). The warehouse stalls had three separate faults:
- `_pick_variant` could hand out the same model repeatedly -> now
  `_pick_variant_norepeat`
- **`stall_cells[i - 1]` indexed -1 on the first pass**, which wraps to the
  last element in GDScript, so the first car took the end of the list and one
  stall could never be used
- stalls sit every 3 cells, so filling them in order lines vehicles up like a
  showroom - a hashed +/-1 cell nudge staggers them, at no rng cost

### Changed - audio
- **Indoor rain was inaudible.** It was losing both ends at once: a -7 dB duck
  on top of a 1250 Hz cutoff that already removes most of rain's energy. The
  cutoff is what makes it read as "through a wall" so it keeps most of its
  work (1250 -> 1600 Hz); the duck, which was stacking loss on loss, comes
  back to -3 dB. **Both changes make it LOUDER.**
- **A +3 dB master trim**, applied on the master bus rather than by raising
  each sound - every cut is governed by the standing quiet rule (one-shots
  <= -18 dB, beds <= -28 dB), which is exactly why the headroom exists. The
  mute still keys off the slider alone, so master 0 is still silent.

### Verified
`SMOKE PASS`, `DOORS` 16 on unchanged cells.

## [0.6.65] - 2026-08-06 - doors you can see, and no two trucks alike

### Fixed - a door was painted in its own wall's colours
*"the door on this building i can barely see it because its the same colour
as the building"*. Measured, not judged - both door kinds were **byte
identical** to the wall they sit in:

- metal door `577277`/`394a50` == `brick_b`'s shaded face `577277`/`394a50`
- wood door `7a4841`/`4d2b32` == `brick_a`'s shaded face `7a4841`/`4d2b32`

**The metal collision was self-inflicted.** v0.6.54 lifted `brick_b` a step to
stop grey houses vanishing into the ground, and landed it exactly on the door.
*Changing a wall palette means re-checking everything mounted on that wall.*

Metal now goes darker than its wall (a recessed steel door reads as a hole),
wood goes lighter than its brick. Luminance gaps 37 and 45.

### Fixed - standing in a doorway did not reveal the interior
*"im still inside the house but the door is opened towards outside but i can
still see my character, i shouldnt be able to see him here"*. The door sits ON
the wall line, which is outside the interior rect, so a player in the
threshold got no reveal: the roof stayed solid while they were plainly in the
building and visible through their own open door. The reveal now accepts a
one-cell grow **gated on actually standing on a door**, so it cannot fire by
walking along the outside of a wall.

### Fixed - three identical trucks in a row
*"why are these 3 trucks just side by side all perfectly lined up? looks
odd"*. Same lane means same facing, which is correct - three of the same
MODEL is the standing no-visual-repetition rule broken.

`_pick_variant_norepeat` picks over the names **excluding the last one**, so a
repeat is impossible by construction. It exists because
`_pick_variant_varied` takes a SECOND draw whenever it happens to repeat -
swapping that into an existing call site varies the draw count and re-rolls
the whole fixed district. One draw, always. `DOORS` stayed 16 on identical
cells, proving nothing moved.

### Verified
`SMOKE PASS`, `DOORS` 16 unchanged.

## [0.6.64] - 2026-08-06 - the prewarm never actually warmed anything

### Fixed - textures uploaded to the GPU during play, not on the loading screen
`_prewarm_textures` existed to pay the cost of every generated texture behind
the deploy screen. It called `load()` on each PNG **and threw the result
away**, under a comment claiming that performed "decode + GPU upload".

Loading populates the resource cache. **The upload happens the first time a
texture is actually DRAWN.** So the cost it exists to prevent was still being
paid during play - once per texture, the first time an object carrying it
came on screen, and never again for that object.

That is the user's report almost word for word: *"it happens on things in my
world while im walking towards it, and it just appears on my screen"*, *"it
only happens on one thing on my world per time, then it wont happen again on
that object"*, *"like it loads on my screen weirdly, but once its loaded then
its fine"*.

It now draws a 1 px sliver of every texture behind the deploy screen, batched
across frames on the builder's time budget. One pixel is enough - the upload
is per resource, not per area.

**Cost, measured against the same run without it:** deploy worst frames
34.3 / 24.7 / 21.7 / 11.1 ms before, **33.6 / 23.8 / 21.0 / 10.6 ms after** -
identical within noise. Build time +0.1 s, on a loading screen.

### Fixed - and it hung headless first
`await RenderingServer.frame_post_draw` never fires under `--headless`
(nothing draws), so the deploy waited forever and `--smoke` reported *"world
never became ready (30s)"*. Headless has no GPU and nothing to upload, so it
returns early now, and the batching waits on `process_frame` instead.

### Not the cause, and ruled out by measurement
The sway shader hashes its phase from `MODEL_MATRIX` in the vertex stage,
which looked like a strong suspect for a one-off wobble as items enter view
under 2D batching. **419 frames walking into the forest, camera-motion
compensated: median residual 41 px, max 239, no outlier at all.** The sway
steps smoothly. Left alone.

### Verified
`SMOKE PASS`, 240 fps, deploy unchanged.

## [0.6.63] - 2026-08-06 - the character sorted where it was not drawn

**The one-frame pop the user has been reporting is found, proven and fixed.**

### The bug
`player.gd` kept `global_position` continuous and pushed the sprite onto the
screen-pixel grid with `_sprite.position = visual_err` (rule 1 - the sprite
must park on the grid or walking shimmers). The sprite was drawn in the right
place, but **y-sorting sorts on the NODE, i.e. on the unsnapped value**.

So for any neighbour within half a pixel, the player could SORT in front
while being DRAWN behind. That frame renders in the wrong order: a prop or a
wall flicks across the character for a single frame, only while moving, and
unreproducible - it depends on the sub-pixel phase, which never repeats.

### Proven, not guessed
Filming for it was impractical (at real walking speed 1400 frames covers
~560 px). But the theory makes an exact prediction, so `--probe-sort` tests
it directly: for every neighbour within 3 px, does
`sign(node_y - other_y)` differ from `sign(drawn_y - other_y)`?

**Before: 1062 disagreements across 2311 near-pair frames - 46% - at a max
offset of exactly 0.5 px, half the grid, as predicted. After: 0.**

### The fix, and the trap in it
`global_position` is now snapped every frame, so the sort key IS the drawn
position. **`_true_pos` is what keeps rule 1 intact**: the exact position is
restored before each move and captured again after, so the snap never feeds
back into movement. Snapping the position and letting the physics carry on
from it is the v0.2.1 "low fps walk" bug - the quantisation accumulates and
the walk speed wobbles.

### Verified
`SMOKE PASS` (movement, crouch, border, roofs, doors, sniper, pause), 240 fps
static and 240 fps walking with zero frames over 8.34 ms.

## [0.6.62] - 2026-08-05 - the roof reveal stops announcing itself

### Added - `--film-walk`, consecutive-frame capture
`--film` samples on a timer, so at 12 fps a one-frame artefact is invisible
about 95% of the time. `--film-walk` captures EVERY rendered frame while the
player creeps forward in fixed 0.25 px steps - small enough that consecutive
frames are nearly identical, so a pop stands out, and fine enough to sweep
the sub-pixel phase.

**Two mistakes in building it, both worth keeping:**
- The first cut disabled collision (copying `--perf-walk`, where it is
  correct) and the player walked straight THROUGH a house. The roof-reveal
  fired, and the frame diff dutifully flagged it as the biggest artefact in
  the run - **correct behaviour, created by the probe itself.** Collision is
  on by default now; `--film-noclip` opts out.
- The first diff flagged every other frame as a 137,000 px full-screen
  change. That was **the camera advancing one pixel** - ordinary scrolling.
  A frame diff on a scrolling game is meaningless without motion
  compensation; align on the integer camera shift first, then diff.

### Fixed - the roof reveal started with a visible step
The interior reveal tweened `modulate:a` with `TRANS_QUAD` + **`EASE_OUT`**,
which is fastest at the START: 19% of the fade is done by t=0.1 and 51% by
t=0.3. On a whole roof that is a visible jump the instant it begins.

Measured walking past a house: the roof dropped **28 brightness levels
between two consecutive frames** - about 56% of the entire fade - then
crawled the rest of the way. That is what "a glitch on a house for a
millisecond" looks like.

`EASE_IN_OUT` moves 2% by t=0.1 and 18% by t=0.3, so the reveal starts from
nothing and lands softly. Re-measured on the identical route: **28.0 levels
-> 1.0 level**.

### Honest limit
A clean walk past a house with collision on showed **median residual 0** -
consecutive frames pixel-identical once camera motion is compensated, with
no outlier at all. So this fixes a real, measured one-frame flash, but it is
**not proven to be the same one the user saw**; their report was rare and
this sample was ~90 px of travel.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.49 ms.

## [0.6.61] - 2026-08-05 - a walking perf probe, and what it ruled out

### Added - `--perf-walk`
`--perf` holds a STATIC camera, so it can only measure a settled view. That
made it structurally blind to anything paid the first time a thing is drawn -
which is what the user reported: *"i only see it while im walking and i only
see it once, when i try and walk back where i was to see if it happens again,
it doesnt happen"*. **Every perf figure this project has ever quoted came
from a stationary camera.**

`--perf-walk` sweeps the player across the district and reports the worst
frames with the position each happened at.

**The player fights the sweep** unless collision is disabled: they spawn
inside the safehouse and `player._process` runs `move_and_slide()` every
frame, which depenetrates them straight back out of whatever a teleport puts
them in. The first cut of this probe never left the spawn building and
measured a stationary camera all over again - the exact blind spot it exists
to remove. Collision is disabled for the duration now.

### Measured - it is NOT frame rate
Sweeping ~9000 px across unvisited ground: **5761 frames, 240.0 fps, worst
frame 6.91 ms, zero frames over 8.34 ms**. The user's own counter agrees. So
the artefact is a ONE-FRAME VISUAL POP - a draw-order or visibility flip -
and not a hitch. Any fix aimed at performance would be aimed at the wrong
thing.

The user then corrected the symptom - *"the weird glitch happens on things
next to my character too, like not when it first appears on the screen"* -
which rules out a first-use cost and clears `_prewarm_textures`.

### Not fixed - and deliberately not guessed at
A live candidate is written up in `TASKS.md` with the proof method: the
player's **y-sort key and its drawn position are different values**
(`global_position` stays continuous, the sprite is drawn at `snapped_pos`),
so sorting against a wall can flip a frame before or after the sprites
visually cross. Every detail of the report fits, which is exactly why it
needs proving by frame-diff before anything in `player.gd` changes -
snapping the node instead would quantise movement, which is the v0.2.1 "low
fps walk" bug already paid for once.

## [0.6.60] - 2026-08-05 - brown dirt, and the wash stops running straight

### Changed - the dirt is brown, measured rather than judged
*"the dirt seems still a bit red, lets make it more brown"*. **How far GREEN
clears BLUE is what decides brown against red.** `7a4841` clears it by only
7, which still reads warm; `884b2b` and `ad7757` both clear it by 32. The
base moves up to `884b2b` with `ad7757` highlights. `4d2b32` stays as the
shadow ONLY - it is -7, blue over green, and would drag the whole surface
back toward wine if it were the base.

### Fixed - the dirt wash ran in straight bands
*"i still see some square ground here"*. The wash used a flat "74% at one
cell, 30% at two", which makes an almost solid ring one cell thick. That ring
hugs whatever it grew from, so along a straight road the wash came out as a
straight band - **ragged at the pixel level and dead straight in SHAPE**, and
shape is what was being seen.

A coarse hash now gives each 4x4 block its own reach, so the wash pushes
three cells deep in places and stops short in others, and its outline is
lobed instead of parallel to its source.

### Changed - the overlay front has a ceiling as well as a floor
`d` runs 0 at the masked edge to 2 at the far vertex, so a front much past
0.85 can swallow a whole tile - especially with two edges masked. A fully
covered tile looks like the other material but still REPORTS as its own, so
the next tile gets no overlay and the visible boundary jumps to that tile's
edge. The width of a transition comes from the wash, which genuinely
converts cells; an overlay's job is only to ragged the edge.

### Added - a fringe diagnostic
`--probe-world` prints `FRINGE {grass: n, dirt: n, gravel: n}`, so "is the
blending running at all" is now a measurement rather than a guess. It was
the thing that settled this one: 1000+ overlays were being placed, which
ruled the pass out and pointed at the wash instead.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.79 ms, `DOORS` 16 on unchanged cells.

## [0.6.59] - 2026-08-05 - the question marks, and dirt indoors

### Fixed - `blob()` was a random walk, not a blob
*"theres what looks like question marks on the road, can you remove that"*.
`blob()` claimed to return "soft blob-shaped patches" and was in fact a
RANDOM WALK that kept every cell a cursor visited. A random walk is a thin
meandering trail, so **every wear patch in the game was a 1 px squiggle**,
often hooked or self-crossing - little glyphs scattered over every surface.

It grows a connected clump now: repeatedly pick a cell already in the patch
and claim a neighbour. That is what every caller already believed it was
getting, and what the no-dot-noise rule means by "small SOLID wear patches".
It touches every floor, every prop wear pass and the menu paintings.

### Fixed - the dirt wash went through walls
**A regression from v0.6.57.** The wash that spreads dirt onto hard surfaces
had no idea what a building was, so interiors filled with earth - breaking
the standing "ONE uniform floor per building" rule. Interior cells are
tracked now and excluded from both the wash and the fringe overlays: a floor
is a floor, not terrain.

### Fixed - too many pale specks
*"theres too many white circles in some areas of the map, lets reduce it"*.
The ground pass put six of the brightest concrete value per tile; three of
the next value down reads as aggregate instead of confetti.

### Changed - the map is not made of rectangles
Blocks, named areas and paved slabs are drawn as hashed wobbled polygons
rather than `draw_rect`, so the map stops being a grid of boxes. The road
decay patches were **one rect per cell** - literally squares (*"all the dirt
just looks like squares on the map too"*); they are overlapping discs now,
sized off each cell's hash so a run of them does not read as identical dots.

### Fixed - the map's dirt disagreed with the world's
v0.6.58 moved the ground off the red ramp; the map was left on the old wine
value. Both are brown now.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.57 ms, `DOORS` 16 on unchanged cells.

## [0.6.58] - 2026-08-05 - the ground pass

User: *"lets make make the ground look visually better, lets give it the
ground pass, make all of the dirt, grass, stone, roads, railroads, everything
on the ground. also the dirt looks more red than brown"*.

### Fixed - the dirt was built on the RED ramp
It based on `341c27` over `241527` - the darkest values of Apollo's ORANGE
and RED ramps - so however much of it you laid down it came out wine, not
earth. **A colour only reads as brown when GREEN leads BLUE**, and both of
those have blue above green. `7a4841` (122,72,65) and `ad7757` (173,119,87)
do not. Darkening is then done by COVERAGE - more shadow and more grey mud -
because every Apollo brown below `7a4841` goes blue-over-green and turns
mauve again.

Same "measure it, do not judge it" lesson as the grey house in v0.6.54 that
was painted in its own ground's colours.

### Added - tonal drift on every surface
Every floor was one flat base colour plus fine per-pixel wear, so a large
area read as a single value with dust on it - flat at any distance, and no
amount of extra speckle fixes that because speckle averages back to the same
tone. `_tonal` lays a few large low-contrast blotches per tile instead, so
across a field of tiles the ground drifts. Applied to concrete, asphalt,
forest floor, ballast and dirt.

`_aggregate` adds small stones as 2x1 pairs, never single pixels, so they
read as aggregate in the surface rather than noise on it.

**Asphalt keeps NO speckle** - smooth road surface is a standing user call.
Its blotches are patch-scale only, reading as old repairs and settled tar,
which gives a long straight road tonal drift without granulating it.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.47 ms, `DOORS` 16 on unchanged cells.

## [0.6.57] - 2026-08-05 - the blending reaches everywhere, and roads rot

### Fixed - whole areas were never blended at all
The user found a lone grass tile inside the dirt and another under a dead
tree, both hard unblended diamonds: *"just a random tile inside of the dirt,
looks completely off, can you make sure its not like that anywhere else"*,
*"for everywhere in my map not just in these screenshots"*.

**The fringe pass ran at the end of `_paint_terrain` - far too early.**
`_place_lone_trees`, `_place_scrapyard` and several others write floor tiles
and add cells to `_forest`/`_dirt_path` AFTER the terrain pass, so anything
they painted never got a fringe. It now runs once, at the end of the whole
build, where it sees the FINAL ground whatever wrote it - complete by
construction rather than by listing the passes that matter.

### Changed - dirt spreads ONTO hard surfaces, two cells deep
*"the dirt on the road looks odd in this picture, its ok to go over the road
with some stuff, liek the road doesnt need to be perfect, but in that picture
the dirt should be filled up, it can overlap the road"*. A one-cell blend
traces the road's outline rather than covering it, so the road read as a
clean shape with a ragged border drawn around it. Dirt now washes two cells
in, thinning with distance, and the fringe frays the new outer edge.

### Added - road decay
*"can we make some spots on the main roads broken, and the broken pieces are
like all blended into whatever is near ... because the straight roads just
look really weird, especially on the map"*. Clustered patches - a coarse hash
grid picks which blocks carry one and a rounded blob keeps it off the block
edges, because a per-cell roll scatters single broken tiles and reads as
noise. A decayed cell becomes bare earth, so the blending frays it into the
asphalt for free. Intersections are never eaten. **The map draws them too**,
so its roads are no longer perfect ruled lines.

### Changed - more grass on the transition tiles
*"the stone tiles that have little grass specks on them, can you make the
specks have a bit more specks"*. Roughly double the clumps and blades.

### Verified
`SMOKE PASS`, 240 fps, worst frame 5.69 ms, `DOORS` 16 on unchanged cells.
All of it is hash-driven, so it costs the layout rng nothing.

## [0.6.56] - 2026-08-05 - the last straight lines out of the blending

User: *"theres still some lines on the grass, like i can tell it doesnt look
natural"*. They were right, and both causes were GEOMETRIC rather than a
matter of tuning - which is why v0.6.55's softer settings had not removed
them.

### Fixed - the blend ran BOTH WAYS across every boundary
Grass crept into concrete and concrete crept back into grass. Both overlays
sit hard against the **shared tile edge** - grass on the concrete tile's side
of it, concrete on the grass tile's side - so the join came out as a
dead-straight line at the iso angle. Reducing the reverse direction's reach
in v0.6.55 only made the line thinner.

Materials are now **totally ordered** by what is taking ground back
(grass > dirt > gravel > every hard surface) and a material may only creep
DOWN the ranking. Across any boundary exactly one side carries an overlay, so
the only edge the eye can find is that overlay's wandering front, well inside
a tile. The `fr_stone_*` overlays are gone with it.

### Fixed - the front could recede to nothing
`_wander` was free to return zero, and wherever it did, bare concrete met
solid grass along a stretch of the tile join - another straight segment. It
now has a floor of `0.24 * reach`, so an overlay always covers the whole of
its masked edge and meets the neighbouring tile's material continuously.
Deep variation is fine; reaching zero is not.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.71 ms, `DOORS` 16 on unchanged cells.

## [0.6.55] — 2026-08-05 — the blend rebuilt, plus four things the user caught

### Changed — terrain blending, rebuilt on the right architecture
v0.6.54's fringe was **wrong twice over**, and the user saw both:

> *"the grass just has some gras line around it all now, it still looks
> weird, i want it to look naturally blended together with whatever other
> tile is next to a tile"* … *"for every tile in the game"* … *"some parts of
> the road are still square too, and some parts of the grass, like all over
> the map"*

1. **The boundary ran parallel to the tile edge.** The tear was varied by
   screen x/y, so the overlay came out as a band hugging the edge — piping
   traced around every tile. The front is now driven by a coordinate that
   runs **along** each edge, so it wanders *across* the tile the way a real
   material boundary does.
2. **Baking a fringe per MATERIAL PAIR does not scale.** It exploded
   combinatorially, so only three pairs ever existed and every other
   boundary in the district stayed hard. Replacing the whole tile also threw
   away the crack/stain/worn variant underneath.

Now there is **one overlay per intruding material** (grass, dirt, stone,
gravel × 15 edge masks × 3 variants = 180), drawn on a second `TileMapLayer`
above the floor. One overlay composites over *anything* — grass onto
concrete, asphalt, ballast or paving from the same tile — and the base
tile's own wear still shows through. Reach is per material, so whatever is
taking ground back pushes deep while pavement only creeps a little: a
boundary is one ragged line, not two bands facing each other.

Intersections still keep clean markings — a crosswalk with grass through it
is unreadable, which is the standing "no grass on intersections" call.

**Zero `_rng` draws**: the pass hashes its variant off the cell. `DOORS`
stayed 16 on identical cells, so nothing rerolled.

### Fixed — bare trees were swaying
*"you made all of the trees with no leaves on them swing back and forth, i
only want that on the bushes and trees with leaves on them, right now the
sticks are moving back and forth"*. The sway was applied by name prefix, and
`tree_` catches the **dead** trees — they are variants 7 and 8 of the same
family. A bare trunk has no crown for a height-weighted sway to move, so the
whole stick waved.

The generator is the only thing that knows which variants it drew bare, so
it now writes a `sway` field into the manifest and the game reads that
instead of guessing from a name. The dead trees deliberately stay inside the
`tree` family — splitting them out would change how many variants
`_pick_variant` sees and reroll the district.

### Fixed — the safehouse car could spawn wrecked
*"the car that spawns next to the safehouse should be working, not a broken
one"*. Variants `_5`/`_6` are the wrecks and the roll could hand you one. The
roll is **still taken** and only its result is remapped — re-rolling until it
came up intact would consume extra draws and shift every placement after it.

### Fixed — the bodies past the wire had no blood
*"the dead bodies outside of the map dont have any blood"*. There *was* a
stain, and it could not be seen: 5–9 **single pixels** of `241527` (near
black, on ground that is already dark), drawn *under* the figure so the body
covered most of it. It was also, strictly, the single-pixel dot noise banned
everywhere else in this project. It is a solid pool now that spreads out from
under the body, in reds that clear the concrete it lands on.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.75 ms, `DOORS` 16 on unchanged cells.

## [0.6.54] — 2026-08-05 — the ground blends, and grey houses have a silhouette

### Changed — directional terrain fringes
User: *"can we make all of the biomes blend more together with another … like
the grass, dirt, stone, try blending them"*, then *"yes they are hard edges
blocks everywhere"*.

There **was** a blend — a concrete cell touching forest picked one of three
`grass_blend` tiles — and it could not possibly work. It was one cell deep,
and it was **non-directional**: a tile with grass scattered generally over it,
chosen at random, with no idea which side the grass was actually on. Softening
a diamond edge requires knowing *which edge*, so the boundary stayed a
razor-straight 64×32 diamond.

`gen_art._fringe_entries` now bakes **135 tiles** — 3 material pairs
(grass-into-stone, dirt-into-stone, and stone-into-grass so the wood frays
into the pavement too, not only the pavement into the wood) × 15 edge masks ×
3 variants. Each is composited from **the real tiles of both materials**, so a
fringe can never drift out of step with what it blends into. The tear line is
two out-of-phase waves plus a few detached clumps — never a per-pixel roll,
which would be exactly the single-pixel dot noise banned project-wide.

**It costs the layout rng nothing.** The two concrete-side branches still take
exactly one `_rng` draw each, and the new forest-side branch takes none (it
hashes off the cell). Verified: `--probe-world` DOORS stays **16 on identical
cells**, so nothing rerolled.

### Fixed — a grey house had no silhouette
User, on a screenshot: *"the edge of this house is like barely seeable"*. Not
a matter of taste — `brick_b`'s shaded face was **`394a50`, byte-identical to
`CONC_BASE`**, the ground it stands on, and its mortar `202e37` is `CONC_D1`.
A grey house was drawn in the pavement's own two colours.

Lifted one step to `819796`/`577277` over `577277`/`394a50`. **The fix is
value, not an outline**: wall segments tile edge to edge, so `outline_auto`
has a `sides=False` mode precisely because outlining the joins draws a black
line down every seam and the gap between two outlines shows the world through
the wall. Every neutral grey in Apollo is used by the ground somewhere, so
separation has to come from being consistently lighter than the ground mass;
the full-screen night grade scales both together, so it holds at every hour.

### Verified
`SMOKE PASS`, 240 fps, worst frame 4.50 ms, DOORS 16 on unchanged cells.

## [0.6.53] — 2026-08-05 — the district is no longer on graph paper

**A deliberate, user-approved map revision.** Their words, on v0.6.52's map
making the regularity obvious: *"yeah but just by a little bit, like you can
move it a couple centimeters around. currently its like perfect, the raods,
the pois"*.

**`DISTRICT_SEED` is unchanged (`"transit-01"`).** Any screenshot or
coordinate from before this release shows a different district than the same
seed builds now.

### Changed — the roads
`_plan_roads` lays `ROAD_COUNT` roads per axis on an even 36-cell pitch with
±4 cells of jitter — 4% of the pitch, which reads as nothing. A second, wider
nudge now runs on top: pitches are **40/33/33 and 41/33/36**.

`MIN_PITCH` is what makes a wide nudge safe. Rolling each road independently
at ±7 can bring two of them 14 cells together, and the blocks *between* the
roads are the districts — a squeezed one cannot hold its place, which is the
one-door map bug and exactly why the original jitter was kept small. Every
road is clamped to a minimum pitch from its neighbours after the roll, with a
backward pass so the overflow does not pile onto the barricade.

### Changed — the POIs
Every one was placed with exact arithmetic: the courtyard dead centre,
`_corner_pos` at exactly +1 into a corner, the playground flush at +2 both
sides, the depot centred on its road. The depot slides along its road, the
playground insets each side independently, and corner places sit 1–4 cells in.

### Not changed — the courtyard, and that is measured
Nudging it cost **two houses** (`--probe-world` DOORS 15 → 13), isolated by
neutralising it on its own. The ring of plots is laid around it, so shifting
it three cells squeezes one side below a plot width, and a 23-cell town block
has no room even at ±2. It stays dead centre — a town square being central is
also simply correct.

### How the district did not reroll
Every nudge reads `_side_rng`, or a local RNG seeded off `DISTRICT_SEED` plus
a per-place key. **The layout rng is not touched, so it costs zero draws** —
a single `_rng` draw here would have re-rolled every block assignment, plot
and prop after it, which is a new map, not a nudge. Block zoning, plot rolls
and the safehouse (`[174, 73]`) all came through unchanged.

### Verified
`--probe-world` DOORS **16** (baseline 15 — one better, not worse; the first
attempt scored 10 and that number is the cheapest detector of the
squeezed-block bug). `SMOKE PASS`. 240 fps, worst frame 4.62 ms. UPPERS 6 with
`floorless=0 propless=0`. **All three extractions re-checked because they
moved** — the toll gate dialogue opens, the LZ counts down on its pad, the
rail line is intact.

## [0.6.52] — 2026-08-05 — the map is a game map, not a paper one

v0.6.46 rebuilt the map screen as a surveyor's chart — aged paper, sepia ink
on every edge, woods as diagonal hatch strokes, a symbol on a paper disc for
every place. It was internally consistent, and the user rejected it:

> *"the in game map looks like an actual map that youd hold, i dont want it
> like that, i want there to be colour on there, the trees are just lines in
> there too, and all the roads are the same size oin the map, all the pois are
> like in the same spot ... the map just looks like squares and lines, doesnt
> look like an actual map. remember i dont want a real looking map i just want
> it to look like a good real map that youd see in other video games"*

**The old scheme's mistake, named so it is not repeated:** it answered "this
reads as a diagram" with "make it look hand-drawn", when the real problem was
that everything was the *same* — one hue, one road width, one marker
treatment. Sameness is what reads as a diagram, not colour.

### Changed — terrain instead of paper
Ground is coloured by what it is: open land, denser city blocks, paved
aprons, dirt yards, dim ground beyond the wire. Areas are drawn as a **72%
tint rather than a fill** — the trainyard is a whole block and at full opacity
it landed as one solid slab, which is the "squares" read being fixed.

### Changed — the woods are canopy masses
Each grove is a clump of overlapping discs with a deep tone under, a canopy
over and a sunlit cap offset up-left, so a wood has a light direction like
everything else in the game. The autumn stand keeps its own ramp. An
irregular edge is what stops a blob reading as a diagram — not a different
stroke, which is what the hatching was.

### Changed — the roads have a hierarchy
They did not, and neither does the world: `_plan_roads` appends
`Vector2i(base, 4)` for every road, so all of them really are four cells wide
and the old map was telling the truth. **The honest hierarchy is the span** —
a road crossing the whole district is a through route you can drive end to
end, one that stops short is a stub the council never finished. Through
routes are wide and bright with a dashed centre line; stubs are narrow and
dull. Nothing invents a width the world lacks; it picks which roads to
emphasise, which is what a map is for.

### Changed — markers keyed to what a place is FOR
Green is a way out of the district, red is home, blue is somewhere to go.
Every marker used to be the same ink symbol on the same paper disc inside the
same thin hollow rectangle, so an extraction and a lootable building were
visually identical.

### Added — ground mottle
Broken concrete and weeds, hashed off the cell so it cannot crawl while you
pan. The first cut used patches 1.6–4.3 **cells** across at 0.16 alpha and
read as grey smudges drifting over the district; patch size is what decides
whether this lands as texture or as a rendering fault, and it is well under a
cell now.

### Fixed — the frame rate it cost
The rebuild measured **240 → 210 fps, worst frame 4.61 → 7.09 ms** with the
map open over a live raid. The cause was `antialiased: true` on the grove and
mottle circles — the most numerous primitive on the map by far, and the
district layer is re-rasterised every frame whether or not the draw callback
re-runs, so it was a per-frame cost. Antialiasing off: **240.0 fps, worst
frame 4.45 ms**, and no visible difference at these radii.

### Still open — the layout itself, which is NOT the map's to fix
The user also said *"all the roads are symmetrical, the POIs too"*. That is
the **district**, not the drawing: the grid is a jittered 3×3 and the POIs sit
where the builder put them. The map is fixed by standing rule, so changing it
is a deliberate map revision and the user's call. Logged in `TASKS.md`.

## [0.6.51] — 2026-08-05 — the title is cast metal

### Changed — the menu wordmark
It was the 1× bitmap font blown up 7×, in two flat tones split by a hard seam
straight across every letter, over a soft offset drop shadow — **five colours
in the whole image**. The user: *"its just white, and it goes up and down a
bit thats all, it seems boring"*.

The blow-up was the root of it. Every edge was a 7 px slab while the rest of
the menu renders at 1 px, so the wordmark read as a placeholder pasted over
finished art. The letterforms still come from the game's own font — it is the
only lowercase cut there is — but **the detail is native resolution now**: a
banded cel gradient down the face with wavy seams, a 1 px lit rim on the
top-left edges and a 1 px shaded rim on the bottom-right, chamfered corners so
the silhouette is not an 8 px staircase, and **a real extrusion to the
bottom-right** so the letters have thickness. The drop shadow is gone; the
extrusion does that job and does it with a light direction.

### Changed — the gleam, and `scripts/gleam.gdshader` (new)
The old one was a 34 px-wide `Control` with `clip_contents` sliding a flat
silver copy of the title across it: a **hard-edged vertical rectangle**, and
dark for 5.1 of every 6 seconds. Metal does not gleam in vertical bars.

It is a shader on the wordmark itself now, with two layers on one diagonal
coordinate — a wide dim band that never stops drifting, and a narrow bright
sweep every six seconds. Both add to RGB scaled by the sprite's own alpha, the
same guarantee `flash.gdshader` gives, so the silhouette cannot fatten.
**The intensity is quantised to whole steps**, which matches the banded cel
light the menu paintings use and means a gradual ramp cannot band.

It also costs **two fewer nodes and one texture less**: `title_shine.png` is
gone, and `shader_warm.gd` picks the new shader up on its own because it
discovers them by scanning the folder.

### Changed — the float
The bob ran at 1.3 rad/s, which on letters this heavy read as bouncing. It is
0.6 now, and it is no longer the only thing the title does.

## [0.6.50] — 2026-08-05 — the map-select tile is a picture now

### Changed — the transit tile on the map-select screen
It was a 96×96 top-down diamond of grid lines and coloured blobs, which Godot
then stretched 1.25× into a 120×120 button — so it was blurred as well as
dull. The user asked for *"an actual picture of the map from a scenic view,
very detailed"*.

It is now a **painted dusk vista, drawn at exactly 120×120** so it lands 1:1
in the slot and nothing resamples it: banded cel sky with wavy seams, the
spires on the far horizon, the low sun, the town's roofs with lit windows,
the comms mast and its red light, a treeline, the rail running out toward the
wire, and **the wire itself in silhouette across the foreground** — the
district's whole premise as the nearest thing in frame.

### Fixed while drawing it — two already-known lessons, relearned
- The treeline was first built from `abs(sin(x))` and came out a **regular
  sawtooth that reads as a mountain range** — the exact failure already
  recorded in `HANDOFF.md`. Rebuilt from overlapping crowns of varying width
  and height. **A natural silhouette must never come from a periodic
  function.**
- The chain-link mesh was drawn `10141f` on an `090a14` fence — four values
  apart, so the entire fence read as a solid black bar. Every new element has
  to beat the background it lands on, and that is measured, not assumed.

Verified that **only `menu_map_transit.png` changed** in `art/gen`. The
generator rewrites every file on every run, so that diff is the thing that
proves no other art moved.

## [0.6.49] — 2026-08-05 — the trees move

### Added — foliage sway
Every tree and bush in the district now leans in the wind. **The trunk stays
put and only the crown moves**, each one on its own clock, so a wood reads as
alive rather than as a field of identical statues.

**It is a whole-pixel shift, never a rotation**, which is the standing rule
for this art. It runs in the FRAGMENT stage on purpose: a vertex-stage shear
moves the quad's corners and the texture is then sampled off-axis, ragging
every column. Shifting the UV by an INTEGER number of texels moves whole rows
of pixels sideways instead, so the art lands exactly on its own grid and is
never resampled. Rows pushed past the sprite edge are dropped rather than
clamped, which would have smeared a column of leaf colour off the side.

**Zero new nodes, two materials for the whole district.** The per-instance
phase is hashed from the instance's own world position in the vertex stage
and handed down as a varying, so one shared material still gives every tree
its own timing. That also means it takes **no rng draw** — which matters more
than it sounds, because the district layout is FIXED and an extra draw from
the builder's rng would have re-rolled the entire map.

Matched by PREFIX (`tree_`, `bush_`), not substring: `street_lamp` contains
"tree", and a substring test would have had every lamp post in the district
waving in the wind.

### Verification
**Filmed, not screenshotted** — a still cannot show motion, which this
project has learned the hard way. Across consecutive frames the canopies
shift, the trunks do not, and the edges stay crisp.

**Perf: 240 fps** in the forest at midday (worst frame 4.63 ms) and on a
storm night with every lamp casting (4.79 ms). Node count unchanged at ~8.0k.

## [0.6.48] — 2026-08-05 — your shadow follows the sun

### Added — a directional shadow on the player
It was one static blob underfoot that never changed. It now behaves like a
shadow: **thrown away from the sun, leaning with it, long when the sun is
low and almost nothing at midday**, fading to a soft contact darkening at
night or under heavy cloud — because an overcast sky does not cast one.

**Verified across three times of day, not eyeballed once:** thrown LEFT at
07:00, compact under the feet at 13:00 (highest sun, strongest shadow),
thrown RIGHT at 19:55.

It rides `main.gd`'s existing clock read — the one already feeding the colour
grade and the sun shafts — so the clock is read once per frame, not twice.
It is legal under the never-transform-a-pixel-sprite rule because the blob is
a **soft-alpha texture**, the same carve-out the LZ beacon's ground wash and
the freight's steam already use; the throw is still rounded to whole pixels
because it slides under a sprite parked on the grid.

### Not done, and it is a decision rather than an oversight — props
`TASKS.md` said "everything shares one static blob". **That was wrong.**
`shadow.png` has exactly one user in the entire project: the player. Prop
shading is baked into the art, so props have no shadow node at all.

Giving them cast shadows is therefore a new system, not a tweak — and the
obvious version, a sprite per prop, would add **thousands of nodes against a
~8.0k budget**. It needs the shader route, and it needs a deliberate call on
cost. The premise research is recorded in `TASKS.md` so it is not re-derived:
Godot 2D has no sun light that casts shadows, and in isometric an occluder
shadow projects across a wall as if it were not there, so this cannot be
done with more `LightOccluder2D`.

## [0.6.47] — 2026-08-05 — a gate for the numbers, and the log gets quiet

**No game change.** Tooling and one long-standing noise bug.

### Added — `--checkclaims`, the numbers gate
`--checkdocs` proves a version agrees and a path exists. It cannot read a
sentence, and `CLAUDE.md` has said so for a while: *"a check cannot verify
prose"*. True — and not the whole story, because **the sentences that have
actually rotted on this project were overwhelmingly numeric.** Every one of
these was written down as fact and was false: `~818 nodes` (1717) ·
`~34k nodes` (~8k) · `~34 buildings` (15) · `a 20 min day` (18) ·
`BARRIER_INSET 72` (66) · `3 rotating backdrops` (2).

A number is checkable, so these are now. The gate reads each claim **out of
`CLAUDE.md`'s own prose** — never a duplicated copy, which would only be one
more thing to drift — and compares it against the constant **the game
actually uses, read at runtime** off `WorldBuilder` and `EnvironmentSystem`
rather than regexed out of the source, so the code side cannot be fooled by
a comment or by formatting. It covers the day length, `DAY_SECONDS`,
`BARRIER_INSET`, `MAP_W` and the `DISTRICT_SEED` string, and runs inside
`--smoke`.

**It fails closed.** Reword a sentence so its number no longer parses and you
get a failure naming the pattern, not a silent pass — the vacuous-green mode
that once produced a door test which never touched a door.

**All five claims and the fail-closed path were fire-tested** by planting a
real violation of each and watching it fail, then restoring `CLAUDE.md`
byte-identical. A check that has only ever passed proves nothing.

### Fixed — the headless log is quiet now
A headless run printed **~50 blocks** of `ERROR: Not supported by this
display server`, each with a five-frame stack trace. `Settings.bind_label`
asked the display server to translate a physical keycode; headless has no
keyboard, so every keybind row raised one — on the menu, on the pause menu,
and again on every harness run.

That noise was not free. **It buried real errors**, and it is the reason the
docs have to tell every session "the verdict prints at the END, check the
HEAD for `Parse Error`". The fix returns the plain keycode string when the
display server is headless, which loses nothing: the physical→keycode step
is a courtesy for non-qwerty layouts, and there is no layout without a
display server. **Measured: 50 → 0.**

## [0.6.46] — 2026-08-05 — the map is a drawn map now

### Changed — the map screen, rebuilt as a chart
The user's verdict on it was *"its like some minecraft map"*: flat coloured
rectangles, roads as grey bands, and every place a bare word floating on open
ground. It is drawn now, not diagrammed.

- an **aged-paper sheet** with a ruled ink border
- roads **CASED** — an ink stroke with a pale channel inside it, the way a
  road is drawn on paper
- **the woods are hatched**, short diagonal strokes instead of filled blobs.
  The stroke pattern is hashed off each grove's own cell, never rolled, so it
  is identical on every redraw — anything random there would crawl while you
  pan
- the rail is a ladder, the wire a broken red ink line
- **every place has its own drawn symbol**: a bus for the depot, a crane and
  hook for the scrapyard, a shed and chimney for the warehouses, a swing for
  the playground, a mast with signal arcs for comms, a boom for the toll
  gate, a fountain for the courtyard, a boxcar for the trainyard, a framed
  picture for the gallery, an H pad for the lift, a bell for the school, and
  a red home marker for the safehouse. Anything without its own symbol still
  gets a surveyor's ringed dot rather than nothing
- every building footprint is **inked**, which is most of what stops them
  reading as coloured blocks

Regions — town, forest, warehouse, trainyard — keep a name and take no
symbol, which is the cartographic convention and stops a zone's several
rectangles carpeting the sheet with repeats.

### Fixed — three things that were making it worse, all found by looking
- The town blocks were a SOLID fill covering nearly the whole sheet, so the
  paper only survived as margins: brown boxes with pale gaps, which is the
  same complaint again. They are a 45% tint now and the paper reads through.
- Vehicle name labels switched on at zoom 3.0 **and the map opens at ~3.6**,
  so all ~33 printed the instant you pressed m and carpeted the district. The
  dots already say a vehicle is there; the names wait for zoom 7.0.
- The safehouse no longer prints its name. You spawn on it, so the live "me"
  marker sat on top of the word for the first stretch of every raid.

### Performance
**240 fps, worst frame 4.61 ms** with the map held open over a live raid —
it deliberately does not pause the tree, so this is the one place a UI panel
can cost real frames. The symbols cost nothing per-frame: they are drawn on
the map's own canvas, which only redraws when you pan or zoom.

## [0.6.45] — 2026-08-04 — walls stop light

### Added — real 2D shadows
Every building wall segment now carries a `LightOccluder2D`, so lamps,
interior lights, the flashlight and car headlights are stopped by walls
instead of shining through them. The biggest remaining item on the visual
polish pass.

The occluder line is the **cell edge the wall art already sits on** — the
same two verts the corner posts hang off — so the shadow boundary can never
drift from the wall the way a hand-derived offset once put a door's collider
a cell from its own art.

**One occluder per contiguous RUN, not per segment.** A building's four sides
become a handful of nodes instead of ~22: `+113` nodes across the district
rather than ~330, and the shadow rasterizer is what pays per occluder. A gap
breaks the run, which is the good part — light genuinely spills through a
doorway or a blown-out ruin corner. The door carries its own occluder,
toggled in lockstep with its collider and built from the same manifest
polygon, so a doorway you can walk through is one you can see through.

Shadows are hard-edged on purpose (no PCF): a soft shadow edge fights the
pixel grid, and the light textures are already smooth alpha.

### Fixed — the flashlight no longer shines through walls
The long-standing B7. Stood inside a building at midnight, a brightness scan
straight out through the lit cone reads 90-334 inside the shell and a flat
52-56 — the pure ambient night floor — across the entire street beyond it.
The same change closes the same leak on interior room lights, which had been
carrying a deliberately tight radius to hide it.

### Measured and rejected — glow / bloom
`WorldEnvironment` glow was built, measured and **backed out**; the reasoning
is recorded in `TASKS.md` so nobody retries it blind. Godot's 2D glow does
nothing unless `hdr_2d` is on — with it off, a glowing frame and a
non-glowing frame came out **byte-identical**. With it on, the canvas renders
in linear space, the tuned night went near-black and the frame rate fell
**240 -> 183 fps**. The intent is still worth having and wants additive glow
sprites instead, the way lamps already work.

### Performance
Unchanged where it counts: **240 fps, worst frame 4.64 ms** at midnight with
every lamp casting, against a 4.5 ms baseline. `SMOKE PASS`.

## [0.6.44] — 2026-08-03 — a bad drawing can no longer empty `art/gen`

**No game change.** `tools/gen_art.py` only.

### Fixed — the blast radius, not the bug
`main()` opened by deleting **every PNG in `art/gen`** and then regenerated
them, so any exception part way through left the folder empty and the project
unloadable until someone re-ran the generator. That happened **twice on
2026-08-03** — once from a duplicate `make_rain_splash()` (Python keeps the
later definition, so `assert_palette` got an `Image`), once from `x ** 0.5` on
a negative `x` returning a **complex number** while shaping kettle's beard.
Both times the actual defect was a two-line art bug whose blast radius was the
entire art folder.

Now the run notes its start time, writes everything, and **only then** deletes
the PNGs it did not touch. Same end state, no orphans left behind, but a crash
leaves the previous art exactly where it was.

**Proven, not asserted:** a `RuntimeError` was planted halfway through the run
and the generator executed. `art/gen` held **528 PNGs before and 528 after**.
Under the old order it would have held zero.

### Worth being clear about the scope
This never could have reached a player. `art/gen` is committed, players never
run the generator, and a build with missing art does not load — so `--smoke`
fails and it cannot be pushed. The cost was a dev loop stopping dead.

## [0.6.43] — 2026-08-03 — glass in the door, and kettle finally has a beard

### Added — the door's vision panel
A wired glass rectangle with **blood spattered on the FAR side**. The order is
the whole trick: the dark of the room behind, then the spatter on the far
face, then the safety mesh, then the glass's own reflection **last** — painting
the reflection on top is what puts the blood behind the glass rather than on
the near face.

It is drawn as **spatter, never a mass**: 1-2 px droplets with gaps, a thinning
spray arc and two slow runs. A soft red mass in this project has been mistaken
for a body before, and the first cut of this one was filled runs that read as a
smear until it was broken up.

Also caught: one of the door's wear dents sat at `(lx0+22, ly0+46)` — **inside
the panel** — and drew a navy block across the glass. Moved below it.

### Fixed — kettle's beard *(base art)*
The block that draws it is literally labelled "the white beard" and it
rendered as a **bare chin**, because a smooth pale mass in the same value
family as skin, with no boundary and no texture, is a chin. Now it has a
shadow where it meets the cheek so it sits proud of the face, a ragged bottom
edge instead of a clean arc, strands through the mass, and a moustache that
overhangs rather than sitting flush. **Tones stay warm on purpose** — the note
above that block is right that grey paint goes blue under this candle.

Diffed: the only changed region is **x 287-315, y 318-340**, his lower face.

### Broke and fixed in the same pass
`(1.0 - t*t*0.94) ** 0.5` returns a **complex number** once the bracket goes
negative, which it does two rows below where the original loop stopped. That
killed the build *after* `main()` had already purged `art/gen`. Clamped with
`max(0.0, ...)`. Second time this session a generator crash has left the
project unloadable — **gen_art deletes before it writes.**

## [0.6.42] — 2026-08-03 — the underpass door, and two things that never moved

### Fixed — the bug behind BOTH "I can't see it" reports
`position = roundf(position + speed * delta)`. At 240 fps a 34 px/s walk is
**0.14 px per frame**, so the round put it straight back and the sprite never
moved. The counter's rat did this and sat off-screen at painting x 24 forever;
the birds did it and hung in the sky. Neither looked like a rounding bug from
the outside — they looked like "it isn't there" and "it isn't moving".

**This is rule 1 restated** — the player's true position stays continuous and
only the drawn position snaps to the grid — and it is now a standing rule in
`CLAUDE.md` in those words. `_tick_rain` and the moth were already correct;
they were the only two that were.

### Added — the underpass door *(base art)*
It was **already a bricked-up service doorway** (`dx0, dx1 = 826, 898`), which
is why the user read it as a door and then found nothing door-like in it. Now
it has a recessed leaf, six vertical ribs, two hinges on the LIT side, a kick
plate, and a lever handle with a backplate and keyway at 4/10 height on the
shade side. The tube is at x 636-768, i.e. to its left, so the lit and shade
stiles follow that.

**The brick infill is left intact underneath and painted over.** Its loop
takes two rng draws per course; deleting it would have re-rolled the chalk
dog, the soffit girders and everything downstream. Take the roll and throw it
away.

### Added — two notices, from the lore
A transit authority **shelter sign** pointing down into the underworks (LORE 4
— the war-years shelter cellars are what is behind that door) and a **wardens'
cordon notice**, lattice panel with a red bar through it (LORE 2 — *"nobody
crosses. nothing comes out."*). No readable text: the font has a 5 px x-height
and a legible poster would be enormous, so lines of ink stand in, as every
other sign in this project does.

**Both patches were measured for emptiness before drawing** — and the second
one had to be moved after that: 912-950 was genuinely empty wall and entirely
**off screen**, because the viewport shows painting x 60-900 only. Measure for
empty AND check it is inside the visible window.

### Also
- The rat is redrawn at 15×9 with a snout, an ear, an arched back and a long
  bare tail, and **fades in and out** instead of blinking out of existence in
  the middle of an empty counter.
- The door's kick plate went `253a5e` → `172038` (a navy plate read as a blue
  stripe painted on) and its warm edge light is solid, not every-other-row —
  stepped, it drew a dashed orange line that read as a defect.

## [0.6.41] — 2026-08-03 — the birds were behind the buttons, and mara's grip

### Fixed — the birds, after two wrong answers and a real measurement
They flew at painting y 234, which is **screen row 464 — inside the "play"
button**. So most of every crossing happened behind the menu and only the
gap on the right ever showed one, exactly as the user reported (*"the birds
are still on the right, and i only see one"*). They now fly at y 219-227, on
the `752438` maroon band, clearing the button top at row 229 — over the
skyline buildings whose windows flicker, which is where the user asked for
them. Five on a tighter stagger so they read as a loose flock.

**How long this took is the lesson.** Two theories offered and rejected, a
"force it magenta" test that proved nothing **because `modulate` MULTIPLIES
and magenta over a near-black sprite is still near-black** — the same trap
that had already hidden the drizzle, the underpass drip and the rat — and a
diff-against-the-bake that could not see it. What finally worked was cropping
the flight path and looking at it.

### The birds, properly this time
The height fix above was necessary and not sufficient: the loop also carried a
separate "flying" state and a visibility gate, and between them the sprites
**silently never drew at all** — through four wrong theories, a magenta test
that could not work, and several scans that measured wires and rain instead.
Rewritten flat, then rewritten once more on the user's steer (*"it doesnt
matter if they spawn in the sky, just make them fade in"*): each bird just
ages, drifts left, **fades in over 1.1 s and out over 1.1 s**, and respawns
somewhere else in the sky. No entry point, no gate, no second state. A shared
entry point had stacked them into a vertical column the moment a fast one
caught a slow one; random spawn plus a fade is both simpler and the only thing
that keeps them spread. Speed is rolled per life, 26-78 px/s.

**The lesson, and it is in `CLAUDE.md` now:** every extra piece of state
between "should be on screen" and "is on screen" is another place for a thing
to silently not draw. When something will not appear and the values all look
right, delete the indirection rather than bisecting it.

### Fixed — mara, in both paintings
- **The den:** her jacket half-width went `19 + t^0.45*17` (19 flaring to 36)
  to `15 + t^0.45*12` (15 to 27) — user: *"make mara skinnier in the den
  backdrop"*. Diffed: the only changed region is **x 771-842, y 344-384**.

### Fixed — mara's pencil and arms *(base art)*
User: *"shes not holding the pencil right, like its not in her hands. also
make her arms not square and a bit smaller"*.
- **The pencil is drawn BEFORE the hand now**, so her fingers and palm close
  over the shaft and the lead comes out below onto the map. It used to be
  drawn after, starting up and to the right of her hand and pointing away, so
  nothing on screen was touching it.
- **`limb()` stamped an axis-aligned `c.rect` at every step** — literally why
  the forearms read as planks. It sweeps a rounded section now, the wrist
  width went 8 → 6 and the flexor bulge 2.2 → 1.2.

**The constraint was proven, not asserted.** Diffing the painting against the
previous commit: the only changed region is **x 597-766, y 345-417** — the
forearms and the pencil. Her face and her hair/headset diff to `None`, i.e.
byte-identical. That is the rule this project has already had one rejected
pass over.

## [0.6.40] — 2026-08-03 — rain that lands, on the raid's own model

### Added
- **Menu rain is SIMULATED, not decorated.** `_add_rain` / `_tick_rain` in
  `main_menu.gd`, built on `environment_system.gd`'s model: parallel arrays,
  one sprite per drop, and **every drop carries its own ground row**. It falls
  to that row, dies there, and leaves a splash AT THAT SPOT using the world's
  own `rain_splash.png`. A `CPUParticles2D` cannot do this — a particle has no
  idea where the floor is, so the splashes it fires are a second unrelated
  system, which is exactly what the user saw and rejected.
- The ground row is **rolled per drop** rather than derived from x. In this
  projection a column is not one depth — a drop at any x can land anywhere
  from the middle distance to the near kerb — so the scatter is the correct
  model, not an approximation.
- **Measured: the yard went from 61 still frames in 71 to ZERO.** Something
  moves in every single frame now.

### Changed
- **The birds: 13×9 instead of 7×5, five instead of three, crossing slower.**

### Two wrong answers, recorded because they matter more than the fix
Asked why the birds had stopped showing, I gave two confident explanations —
that they were drawn against too similar a value, then that the new rain was
out-competing them — and the user rejected both, correctly. The measurement
that should have come first showed the birds rendering and moving in **93 of
95 frames**. Neither theory survived a ten-line check. Both the habit and the
technique are now standing rules in `CLAUDE.md`: comparing a shot to the BAKE
cannot answer "why is X not showing", because the vignette darkens every pixel
and swamps the signal — compare **consecutive film frames**, where the
vignette is identical and only motion differs.

Also added there: **every new element must beat the background it lands on,
measured, not eyeballed.** That failed four separate times on 2026-08-03 — the
far signal's eye, the underpass drip, the rat, and the birds — and every time
the code was perfect and the thing was invisible.

## [0.6.39] — 2026-08-03 — things that move, on the two quiet scenes

The user kept both tunnel backdrops (*"lets keep both the backdrops for now,
no harm"*) and asked to press on with the two that still read as photographs.
Everything here is an **object**, not another light — that was the whole note.

### Added — the trainyard
- **Birds.** Three, on staggered clocks, crossing ~430 px of the sunset band
  in about seven seconds each, so one is usually in the air. Hard silhouettes
  against the one bright thing in the picture.
- **Five arcs on the pole lines, bigger and far more often** (*"make the
  trainyards sparks from the poles more noticable, and make more of them"*).
  The sheet went 20×16 → 26×20 with a much wider fan and a hotter core, and
  they fire every 1.4-4.5 s instead of every 3.5-9. Every point is a wire
  pixel sampled out of the bake.
- **Nine lit windows on the far skyline, flickering** (*"maybe some little
  windows on some buildings in the background of the trainyard, and have them
  flicker a bit"*). 2×2 each — at that distance a window is a couple of
  pixels — on nine periods that share no common factor so the row never
  pulses together, and one of them has a bad connection. **Every cell was
  read out of the bake as silhouette with sunset directly behind it**, so
  none of them floats in open sky.

### Added — mara's counter
- **A rat** crosses the counter's empty left third, which the painting
  deliberately keeps as room rather than person. Four frames, legs
  alternating, body dropping a pixel on each contact.

### Removed again, same day
- **The rain "splash marks" on the ground.** User: *"i meant like the actual
  raindrops coming down on the screen should physically hit something on the
  screen, so remove that water stuff on the ground and do what i wanted"*.
  A second particle system of splashes sitting on the ground band has no
  relationship to any individual streak, so it reads as decoration lying on
  the floor. Pulled out entirely rather than left in half-right. The real
  job — hand-rolled drops that die on a per-column ground row and splash at
  that exact point — is **TASKS.md B0a**, written up with the approach.

### Fixed after the user looked
- **The rat was invisible.** Drawn in 090a14 on a counter top of
  241527/341c27 — about 20 values apart. It was rendering perfectly and
  reading as nothing (*"i dont see any rat"*). Repainted pale, 7a4841 with an
  ad7757 ridge. Same lesson as the far signal's eye and the underpass drip: a
  thing has to beat its BACKGROUND, and this background is dark.

### Note on the numbers
`yard` and `counter` still measure ~0.3% mean change. **That is the metric
failing, not the scenes** — a bird is 7×5 px and a rat 11×8, which is
0.006% of a 960×544 frame each. Judge these two off the films.

## [0.6.38] — 2026-08-03 — the drain leaks from the hole, and rain lands

All of this is the user's playtest of v0.6.37, taken point by point.

### Fixed
- **The chop read as a RECTANGLE** (*"it looks like its a rectangle, make it
  smooth like blended in"*). It filled a rect with dashes at UNIFORM density,
  so the overlay's own bounds were the hardest edge in the water. Both the
  drain's and the underpass's now fade to nothing on both axes.
- **The sluice poured into mid-air** (*"make that water connected with the
  water on the ground"*). The sheet was 76 px and stopped ~15 px above the
  channel; it is 98 now and its foam spreads wide ON the surface.
- **Rain vanished instead of landing** (*"all of the rain in the backdrops
  should actually hit the scene, like how it is in game"*). The yard and the
  warden get splash marks across their ground bands — **reusing the world's
  own `rain_splash.png`**, which is what the raid has always used.

### Added
- **The manhole leaks** (*"water coming from the top of the hole, like where
  it opens up ... a couple drops and maybe a bigger drop with a bigger
  bubble"*). Four of the five drips now hang off the manhole rim, and one of
  them is FAT: its own 2-frame drop sprite, a slower fall, and the big half
  of an 8-frame bubble sheet. Two sizes are DRAWN, not scaled — runtime
  scaling of pixel art stays banned.
- **Every landing blows a bubble** — dome rises, tops out with a highlight,
  bursts.
- **`SCENE_SECONDS` 10 → 15** (user call).

### Broke and fixed in the same pass
- **A duplicate `make_rain_splash()`.** gen_art already had one — the world
  rain's 4-frame ground splash — and Python silently kept the LATER
  definition, so `assert_palette` got an `Image` and the build died *after*
  `main()` had already purged `art/gen`, leaving the project unloadable. The
  right answer was reuse, not a second asset. **Check for the name before
  adding a generator to a 17,000-line file.**

### Still quiet, and said plainly
`counter` and `yard` measure ~0.25-0.30% mean change with ~50 still frames in
59. Their additions are rain and sparks, which the metric under-reports — but
the user's read is that they are still the two quietest, and that is the read
that counts. Next for them: a real moving OBJECT each (the counter's hanging
tag row; something crossing the yard), not another light.

## [0.6.37] — 2026-08-03 — the living layers, made noticeable

User: *"these living layers are very minimal, can we add some more to it, to
every backdrop, i want it to be noticable"*, then — and this is the sharper
half of the brief — *"dont just amp up the current ones, find new ones on the
screen and create some, like some flcikering lights, or some pole lines sparks
coming off them"*.

### The tool that made this possible: `--film`
`--film=<name> [--scene=menu] [--backdrop=N] [--film-seconds=N]
[--film-fps=N]` captures a SEQUENCE into `shots/film_<name>/`. **A living
layer is motion and a still cannot show motion** — every judgement about
whether a scene "reads as alive" made off one frame is a guess, and all six of
these were built off guesses. Measuring the first film settled the argument
immediately: the underpass changed **less than 0.5% of the screen in 38 of 47
frames**. It was a still image with a lamp in it. (This is also the frame
capture half of the parked trailer work, which needs exactly this.)

The frame folders are **gitignored** — hundreds of full-res PNGs per run, and
they are a means to a GIF, not a result.

### Fixed — a real bug the user found
- **Rings appeared on the drain's water with nothing falling into them.** The
  two ripples had their OWN random timers and only ripple #0 was ever
  triggered by the drip. Ripples and drips are now **paired by index, four of
  each**, so a ring in that scene is only ever something landing. The drip
  also fell at 900 px/s — across the whole frame in under half a second — so
  you could watch for a minute and never catch one in the air. Now 470.

### Added — new objects, not louder old ones
- **Arcing joints**, one shared 5-frame sheet used three times, every one
  anchored on a real fitting: two on the trainyard's overhead lines (wire
  pixels read out of the bake at 170,175 and 230,205), one on the isolator
  feeding the warden's shift lamp, one on the counter's taped splice — whose
  pilot bead the bake already paints LIVE.
- **The underpass's dead pendant lamp is switched on and failing**, cold
  against the sodium and never in step with it, lighting the half of that
  frame where nothing moved at all.
- **The drain's sluice gate pours.** It has always been described as "leaking
  a sheet into the channel" and the bake draws that sheet in 090a14 — i.e.
  invisible. Six scrolling frames, sheet and foam as ONE object so they can
  never fall out of step.
- **Water surfaces move** in the drain and the underpass — six frames of
  dashes in the water's own drawn language, cycling ~9 a second.
- **The underpass's reflection is now one of its lights.** It is a quarter of
  the frame and was entirely baked, so the tube could stammer out while the
  huge bright patch it throws on the flood sat perfectly still.
- **Rain across the full frame** in the trainyard and at the toll gate. It
  crosses the button bands, and that is a deliberate reversal: those bands are
  kept clear of STRUCTURE, and rain is not structure.
- **The den's candle behaves like a flame** (it moved 14% and guttered once
  every nine seconds — that is a lamp with a loose wire), and its glow's peak
  alpha went 64 → 120, because swinging 40% of almost nothing is nothing.
- **The counter's light box flutters like the fluorescent it is.**

### Measured, before → after (mean % of screen changing per frame, and how
### many frames out of a 4-5 s film are visually still)
| scene | before | after |
|---|---|---|
| drain | 0.56%, 39 still | 1.76%, 5 still |
| underpass | 0.50%, 38 still | 2.01%, 3 still |
| den / yard / warden / counter | ~0.2-0.4%, ~50 still | see the note below |

**HONEST LIMIT OF THAT TABLE:** the metric downsamples bilinearly, which
averages 2 px rain streaks away — so it under-reports the four scenes whose
main addition is rain or sparks, and their numbers barely moved even though
the rain is plainly visible in the frames. It is a good detector of *gross*
stillness and a bad judge of thin fast things. Use it to catch a dead scene,
not to grade a live one.

### Performance
**245 fps on every backdrop**, unchanged. The 172 fps seen during a film is
the capture writing PNGs, not the scene.

## [0.6.36] — 2026-08-03 — the door check was flaky, and that is worse than broken

**No game change.** `harness.gd` only. Found because v0.6.35's smoke printed
`walked through closed doors: #0 off -8 side 1`, then **passed on a re-run of
the identical binary** — and the commit had changed no world art at all (only
`menu_counter_*` overlays were added). Measured at roughly **2 failures in 5
runs**, on a different door each time.

### Fixed
- **The closed-door check measured the wrong frame.** It shoved the player at
  a door, `await`ed a frame, and only then read the position. But
  `player.gd:311` runs `move_and_slide()` **every rendered frame**, and that
  depenetrates a body left flush against a collider — so the read was of the
  player's own recovery, not of the shove, and which side it popped out on
  came down to float error in a sub-pixel overlap. `_shove` uses
  `move_and_collide`, which writes `global_position` synchronously, so the
  answer is ready the moment it returns. It is read there now.
  **8 consecutive passes** after the change.

### Also fixed, but it was NOT the cause
- **The "spawn is clear" guard was a no-op.** `test_move(xform, Vector2.ZERO)`
  with `recovery_as_collision` left at its default `false` reports *clear* for
  a body already inside geometry — a zero-length sweep does not count
  depenetration as a collision. So the check that the comment above it
  describes ("only measure from a start that is actually CLEAR") never
  rejected anything. Now passes `true`. **Changing this alone did not stop the
  flake** — it failed again on the next run — which is how the real cause got
  found. Kept because the guard should do what it says.

### The lesson, in one line
A flaky mandatory gate is worse than no gate: it teaches whoever hits it to
run it again instead of reading it. Which is exactly what happened here first.

## [0.6.35] — 2026-08-03 — mara's counter, and all six are moving

Last of the four. Every menu backdrop now has a living layer, and all four
were built to the same contract: base painting bit-identical (hashed either
side of every regen), overlays built after every base draw, no rng draw taken,
every anchor mapped off the bake.

### Added
- **`menu_counter_box`, `_lamp`, `_arc`, `_flare`, `_dust`** and
  `_tick_counter()`.
- **THE COLD LIGHT IS THE ONE THAT BREATHES.** The den, the warden and the
  underpass all breathe their warm source; this room's key light is the
  drafting box under her map, so the box wavers and the work lamp holds
  steady against it. The inversion is the pitch.
- **The taped splice arcs, then drops an ember.** The pilot bead swells over
  the 1.2 s before release, so the drip has a visible cause instead of
  arriving out of a dark ceiling. The ember falls slowly and **dims as it
  goes** — it is dying on the way down — and flares in the parts tin, on the
  scorch ring the bake has carried all along.
- **A ROUND mote texture** (`menu_counter_dust`) for the dust over the warm
  counter, because `dust.png` is a PLUS and sparse copies of it read as
  four-pointed stars (the reason the warden's dust field was cut in v0.6.33).

### Fixed during the pass
- **A parse error: `motes` was already declared** by the drain's emitter —
  `_build_scenes()` is one scope top to bottom. Caught because the run
  printed `Failed to load script`, not because anything looked wrong.
- **The flare is NOT additive**, unlike every other light in the scene. Added
  over the tin's baked 602c2c, `e8c170` clips to a near-white c9c9c1 and
  reads as an electrical spark; drawn normally it stays gold and reads as hot
  metal landing in a tin.

### Doc fix
- `make_scene_counter`'s docstring put the live pilot bead at **(838, 246)**.
  `_cables` sets it at **(837, 252)**; 838/246 is inside the splice block's
  corner region, not the bead.

## [0.6.34] — 2026-08-03 — the flood, and a tube that is giving up

Third of the four. Same contract: base painting bit-identical (hashed either
side of the regen), overlays built after every base draw, no rng draw taken.

### Added
- **`menu_underpass_tube`, `_halo`, `_pool`, `_ring`** and
  `_tick_underpass()`.
- **THE TUBE, ITS WALL HALO AND ITS WALKWAY POOL ARE ONE VALUE.** A sodium
  tube does not fade, it drops out and strikes again — so this is a steady
  burn with a short stammer punched through it every 7.4 s, not a sine. All
  three lobes take the same number, because a lamp whose reflection keeps
  burning while the lamp is out is two lamps.
- **Three ceiling leaks** drip from the portal beam's underside (y 108) to
  the waterline (y 406) and push a **broken** 3-frame ring out of the flood.
  Broken on purpose: this water is drawn in runs everywhere else in the
  painting, and a clean ellipse on top of it reads as a decal.

### Changed from the pitch note, with reason
- **The drip columns moved to x 262, 372 and 592.** The docstring proposed
  300, 596 and **736** — but 736 is past the walkway's start at 604, so a
  drip there lands on the kerb and the sandbags and would have pushed a ring
  out of concrete. The three now used are all over open water (the sunken car
  owns x < 230) and all outside the button box at 395-565.

### Fixed during the pass
- **The drip rendered as nothing.** Tinting `rain_streak` (already a 3c5e8b
  at 20-76% alpha) with 577277 took it to (20,42,65) — *darker* than the
  202e37 wall it falls down. The yard's drizzle hit the identical trap two
  versions ago; `modulate` MULTIPLIES, so a moving light has to be checked
  against what is behind it, every time.

## [0.6.33] — 2026-08-02 — the warden's gate wakes up

Second of the four. Same contract as the yard: the base painting comes out
bit-identical (hashed either side of the regen), the overlays are built after
every base draw and take no rng draw, and every anchor is mapped off the bake.

### Added
- **`menu_warden_lamp`, `menu_warden_spill`, `menu_warden_blink`,
  `menu_warden_moth`** and `_tick_warden()`.
- **The desk lamp and the road spill breathe on ONE value.** The review note
  on this painting was that nothing joined the pool on the tarmac to the
  window it comes out of — `_light_path` said it in paint, and a shared clock
  says it in motion.
- **He blinks.** A 28×3 overlay laid exactly over rows 253-255, x 662-668 and
  683-689 — the pixels the open eyes occupy — with the bridge of his nose
  left transparent between them. Closed, the upper lid sweeps down: the
  socket colour takes row 253 and the dark seam lands on 254. Verified by
  forcing it on, shooting, and comparing against the bake.
- **A moth works the lampshade**, 3 wing frames on a rounded elliptical
  orbit, and the lamp **guts for 0.16 s** when it touches — every 5-11 s, not
  every pass.
- **The fuse box pilot** (dead in the bake at 810, 268) wakes on a 4.9 s
  period that divides into nothing else in the frame.

### Deliberately not done
- **No dust field in the lamp light.** `dust.png` is a PLUS — full-alpha
  centre, four neighbours at 90, empty corners. Dense it reads as smoke (the
  den) and around a lens it reads as a glow (the LEDs), but six drifting
  alone over the ledger each read as a four-pointed **star**. Cut after
  seeing it in the render.

## [0.6.32] — 2026-08-02 — the trainyard wakes up

First of the four promoted paintings to get a living layer. All five of the
menu's existing techniques are used and no new engine work was needed.

### Added
- **`menu_yard_halo`, `menu_yard_splash`, `menu_yard_glint`** — three runtime
  overlays built at the end of `make_scene_yard()`, after every base draw and
  **taking no rng draw**, so the approved painting is bit-identical. Proven by
  hashing all six backdrops before and after the regen.
- **`_tick_yard()`** in `main_menu.gd`. The signal *ticks* on a 3.4 s beat
  (up 0.35 / hold 1.15 / down 0.5 / dark 1.4) rather than breathing like the
  den's candle — a railway lamp holds an aspect. The cabinet indicator ticks
  on 2.6 s, the far signal down the line holds its aspect and drops out for
  half a second every 6.7 s; no two of the three periods divide. Drizzle runs
  the full height of the LEFT of the frame, and runoff comes off the near
  boxcar's eave to burst on the ballast in a 3-frame splash.

### Fixed during the pass — every one of these was caught in the render
- **The halo read as a MOON.** 72 px across with a 210-alpha core painted a
  pale disc bigger than the signal head. Now 34 px with a 2 px core.
- **The drizzle rendered invisible.** `CPUParticles2D.color` MULTIPLIES the
  texture, and `rain_streak` is already a 3c5e8b at 20-76% alpha; tinting it
  577277 as well took it to (20,42,65) at a quarter alpha. It is white now.
- **The puddle glint came out a cold grey smudge.** ADD over the baked 253a5e
  blue can only neutralise toward grey — it is normal-blended now, weighted
  to its top rows, and broken into dashes like the reflections the painting
  already draws along the sleepers.
- **Both indicator lamps sat one pixel off their lenses.** An ODD-sized
  sprite (`dust.png` is 3×3) centred on P rasterises its middle texel onto
  P-1. Measured against the bake, corrected, and re-measured.
- **The far signal's eye is additive and the cabinet's is not.** That eye is
  baked against a `de9e41` sunset, so a red dot there is darker than its own
  sky and reads as dirt.

## [0.6.31] — 2026-08-02 — the menu changes scene faster

### Changed
- **`SCENE_SECONDS` 30 → 10** (user call, the release after it shipped at 30).
  With the 1.4 s crossfade each backdrop now holds still for about 8.6 s, and
  a full pass through all six takes a minute. The shuffle bag is unchanged —
  still no repeat until every scene has been shown, and none across the join
  between two bags.

## [0.6.30] — 2026-08-02 — six backdrops, drawn from a bag

The four auditioned menu paintings promoted into the rotation. User call:
*"let's add all 4 of those menu backdrops to the game, just like the den and
drain. So we'd have 6 now in total and they all switch between another every
30 seconds. Make it random every time, but you can't repeat the same one if
all havent been seen yet"*.

### Added
- **Four more menu backdrops** — `menu_yard`, `menu_warden`, `menu_underpass`
  and `menu_counter` join the den and the drain, six in total. They are built
  in `_build_scenes()` on exactly the same footing as the other two and fade
  the same way. **They are STATIC** — the den's candle/needles/LEDs and the
  drain's ray/motes/drips have no counterpart yet; a living layer for the new
  four is the next version's work, and the module docstring says so.

### Changed
- **`SCENE_SECONDS` 20.0 → 30.0.**
- **The rotation is a SHUFFLE BAG, not a cycle.** `_process` used to run
  `(_scene_index + 1) % _scenes.size()`, the same six-step loop every launch.
  A bag now holds each index once, `_bag_next()` pops one off the back, and
  the bag refills only when empty — so every round shows all six exactly once
  and nothing returns before the others have had a turn. The **bag seam** is
  handled explicitly: on refill, if the last slot (the next draw) holds the
  scene already on screen, it is swapped with a random earlier slot, which is
  the only way the same painting could ever appear twice running.
  `_bag_reset(shown)` starts a round with one index already spent — used on
  menu entry and by `show_backdrop`, so the backdrop you are looking at is
  never the next one up.
- **Deliberately unseeded**, unlike the world builder: the district must be
  bit-identical every deploy, the menu should differ every launch. Hand-rolled
  Fisher-Yates over `randi_range` — `Array.shuffle()` stays banned.
- `--backdrop=N` now accepts **0-5**; `show_backdrop` still clamps.

## [0.6.29] — 2026-08-02 — the den and the drain, repainted

Both shipped menu backdrops rebuilt to the standard of the four candidate
scenes being auditioned alongside them. User call: *"can you upgrade the den
and the drain paintings a bit to like match all of these 4. I think they are
a bit behind in visuals"*, then *"yes a redesign would be good too"*.

### Changed
- **THE DEN.** Mara is now recognisably the same woman as her portrait in the
  counter pitch — same hair mass and greying lock, same two-cup headset, same
  oxblood jacket, same face construction and the scar through her brow. She
  was a flat block with one dot for an eye. **Verne now reads as the medic**
  he is in the lore: a rail of hung instruments, a shelf of bottles and a
  dressing box, a basin he is rinsing in. **Kettle** gained a face, a flat
  cap, a beard, and the shelf of unredeemed stock LORE 7b says he keeps. The
  two light pools are banded cel light instead of smooth airbrushed ellipses;
  the wall is real shiplap with staggered joints; the floor is depot concrete
  rather than rows that read as brick.
- **DOT NOISE REMOVED from the den — it had been breaking a standing rule.**
  Three sources: the job board's drop shadow was a 50% speckle, the rug was a
  solid block with 6% of its pixels dropped, and the coins were 110 loose
  pixels. All three are now structure — a real shadow step, a woven rug with
  a bound border and fringe, and five modelled coin stacks.
- **THE DRAIN.** The light was smooth concentric rings on a flat wall; it is
  now a shaft modelled as a vertical slot with a separate bounce off the
  pool, its bands cut by bed joints, perpends and a per-brick tone mosaic so
  no contour is ever a clean curve. The brick was a perfect grid — it now has
  rolled course heights, a rolled pitch per course, sagging courses, chipped
  corners, replacement bricks from a redder batch and lime runs. Two thirds
  of the frame was empty black: it gains a barrel soffit overhead, the tunnel
  continuing left through a voussoired arch, a pipe run on saddles, a
  cast-iron penstock cracked open and sheeting water, and a lantern that puts
  one warm source against the cold shaft.

### Fixed
- **A living-layer collision caught before it shipped.** Mara's crown in the
  den originally topped out at y266, which put her hair under the VU-needle
  sprite anchored at (814, 272) — the needle would have animated on her head.
  Found by compositing the real overlay sprites at their exact coordinates
  and reading the result. Her crown is now a flatter dome topping at 286.

### Notes
- `art/gen/manifest.json` is **byte-identical** and only the six menu backdrop
  files changed, so no other art in the game was disturbed. Each scene draws
  from its own rng stream.
- All five living-layer anchors verified in the running game, not just in the
  bake: `--shot --scene=menu --backdrop=0` and `=1` both confirm the candle
  glow lands on the candle and the ray lands on the shaft.

## [0.6.28] — 2026-08-02 — the chain skipped two releases

A third migration audit — six lenses over the docs and the code comments,
19 candidates, 13 confirmed and 6 refuted by adversarial verifiers. Both
gates were green before, during and after, for the third time running.

### Fixed
- **Dying at the wheel could stand your corpse up on the pavement.**
  `exit_car()` guarded only `_player == null`, which covers the case where
  `abandon()` has already emptied the cabin — but `abandon()` does not run
  until ~1.55 s after death, so pressing F in the ~1.2 s before that resumed
  the coroutine with a live reference to a dead player and called
  `unboard_car()` on the body mid-fade. Now `_player == null or _player.dead`,
  the same shape `enter()` uses, with the two arms and why they differ
  written out at the guard. **Found by auditing v0.6.27's own changelog
  entry, which had overclaimed the bug it fixed and papered over this one.**

### Changed
- **`--checkdocs` gained a sixth part: `HANDOFF.md` must NAME the current
  release.** v0.6.26 and v0.6.27 both shipped while the newest handoff entry
  still read "still v0.6.25 … tree clean at v0.6.25", and nothing caught it —
  that file was read for dead paths but never for a version. **Fire-tested on
  the real violation** rather than a planted one: it failed with "HANDOFF.md
  never mentions v0.6.27" before the entry that closed the gap was written.
  Its limit is stated at the check: it proves the number is mentioned, never
  that the entry is true.
- **13 false doc and code-comment claims corrected**, each verified against
  the code and each adversarially re-checked before it was believed:
  `TASKS.md` claimed M2's gun art was "already generated and waiting" (the
  three generator functions have zero call sites and no sprite has ever been
  produced); `CLAUDE.md`'s "visible power cables" standing rule commanded an
  interior flex the user had explicitly deleted; `CLAUDE.md` still said
  "death fade → respawn" when dying ends the raid into the debrief, and still
  listed the licensed audio without the car doors and engine (ggbotnet, cc0 —
  an attribution obligation); `pause_menu.gd`'s header listed three buttons
  and omitted "abandon raid", the one with a scoring side-effect; `main.gd`
  described the freight as "five minutes away" when the in-game clock runs it
  at midnight, 3 nights in 7; `main.gd` said the warm-up camera aims at "the
  spawn crossroads" when it aims at the map centre, ~3200 px from the actual
  spawn; `world_builder.gd` put the comms relay in the open block when it
  sits in the forest; `DESIGN.md` said extraction "ships early, in the 0.6.x
  line" — a pre-renumber number that now reads as upcoming work for something
  that shipped in v0.3.10–v0.4.0 — and described the fallback respawn as a
  crossroads that no longer exists.
- **v0.6.27's entry corrected in place** (see below): the car was never
  "wedged for the rest of the raid", and the two coroutine guards were never
  "identical".

## [0.6.27] — 2026-08-02 — three that outlived their scene

Found by a scene-swap audit: state that survives longer than the thing that
created it. All three verified against the code before the fix, and the
first one reproduced end to end.

### Fixed
- **`--audiodebug` permanently muted the game.** It drives the real volume
  slider to 0 to test it, and that path is
  `Settings.set_volume()` → `_save()` → `user://settings.cfg`. Nothing put
  it back, so a single run left `master=0.0` on disk and **every future
  launch booted silent** — no menu theme, no rain, no footsteps — with no
  on-screen cause and a slider the user never touched sitting at 0%. The
  flag now captures the master first and restores it as its last act, after
  the dumps, so the measurement still shows the muted graph. **Verified by
  running it: `AFTER master=0.00` → `RESTORED master=1.00`, and
  `settings.cfg` reads `master=1.0`.** This is a harness path that was
  silently editing real user settings — exactly what `CLAUDE.md` warns the
  user-data folder holds.
- **Thunder rolled over the main menu.** `Sfx.silence_world()` stopped the
  rain and engine loops but not `_thunder_player`, a multi-second one-shot
  on the same persistent autoload — so a strike a couple of seconds before
  you extracted kept playing through the scene change and over the menu
  guitar. `environment_system.gd` already guarded the *deferred* half of a
  strike; this covers the clap already in flight.
- **Dying at the wheel left a car's door sprite stuck open.** `exit_car()`
  awaits a 0.34 s door swing, then uses `_player` — but the death path
  (`abandon()`) nulls that reference, so pressing F inside the death fade
  called `unboard_car()` on nothing and the coroutine died before reverting
  the open-door variant. **Two claims in this entry were WRONG when it
  shipped and are corrected here rather than quietly dropped** (found by the
  next session's audit): it said the car was "wedged for the rest of the
  raid" — it was not, because `abandon()` clears `driven` and `_busy` itself
  two lines after nulling `_player`, so the car stayed enterable and the only
  residue was the cosmetic sprite. And it said `enter()` "has carried the
  identical guard all along" — the guards are **not** identical (`enter()`
  also tests `.dead`, and must), and it got its own guard in v0.6.43, not
  from the start. The `.dead` half of the story turned out to be a real
  remaining bug; see v0.6.28.

### Changed
- Every blockquote removed from all seven docs (user call: the `>` marker
  lands on every wrapped line and reads as noise). No wording changed.

## [0.6.26] — 2026-08-02 — every scene root defends itself

### Fixed
- **The camera kick and hit flash decayed ~20% slow through every
  hit-stop.** `player.gd` floored its unscale divisor at `0.05` while
  `Juice.hit_stop` sets `Engine.time_scale` to exactly `0.04` — so the
  "divide-by-zero guard" was clamping a legitimate value instead of
  guarding anything. Now `0.001`, matching `juice.gd`'s own floor.
  Sub-perceptual over a 40–70 ms window today; it stops being
  sub-perceptual once M2's guns lean on hit-stop.

### Changed
- **`main_menu.gd` and `splash.gd` now call `Ui.clear()` and
  `Juice.reset()` themselves**, so every scene root starts from a known
  state rather than trusting whoever ran last to have tidied up. Both
  calls are idempotent, so the overlap with `main.gd` costs nothing.
  **This was never a live bug** — `Juice._process` runs
  `PROCESS_MODE_ALWAYS` and unscales its own delta, so a hit-stop always
  expired within ~50 ms, and `main.gd._exit_tree` cleared it besides. It
  was closed because the protection ran through a single path, and any
  future route to the menu that skips that exit would have inherited a
  slowed clock with nothing to clear it.

### Notes
- The other autoloads were audited at the same time and are all clean:
  `Raid.begin()` resets the per-raid ledger on deploy, `Sfx.silence_world()`
  and `Music.play_menu()` run on menu entry, and `Ui.clear()` already ran in
  both directions. `Authority` and `Settings` hold nothing per-raid.

## [0.6.25] — 2026-08-02 — grey days

### Added
- **Overcast weather** (user asked whether the sun shafts only appear when
  it is sunny — they did, but "not sunny" only ever meant "raining", so
  every dry day was a sunny one). Overcast is dry, flat and slightly cool,
  it kills the sun shafts, and it reads as its own forecast on the map
  bar. Eased in on the same slow ramp as the storm tint, so the sky never
  visibly switches.
- This is **not** the fog spell that was rejected earlier. Dawn mist
  happens every morning anyway, so forecasting it said nothing; overcast
  changes the light for a stretch, which is the point.
- The shafts now read a single `sun_blocked()` signal — the greater of
  rain and cloud — rather than rain alone, or an overcast day would still
  have got beams.

### Notes
- Simulated over 500 days the mix now runs **clear 52%, overcast 33%,
  rain 9%, storm 6%**: dry 85% of the time, but sunny only about half.
- **CORRECTION, 2026-08-02 — the figure above was never right.** Solving the
  roll in `scripts/environment_system.gd` for its steady state and weighting
  by spell length gives **overcast ~42%, clear ~36%, rain ~13%, storm ~9%**
  (dry ~78%). The `weather != CLEAR` guard makes it impossible for one clear
  spell to follow another, while overcast can repeat — so **overcast is the
  most common sky, not clear.** The original line is left as shipped history
  with this correction attached; the true numbers live in `CLAUDE.md`.

## [0.6.24] — 2026-08-02 — a smaller font, and the safehouse moves

### Added
- **A second, much smaller font.** The vehicle labels on the map are tiny
  now (user: "way smaller") — 3px x-height in a 6px box, against the main
  font's 5 in 9. It had to be **drawn** at that size, not scaled: the main
  font is a bitmap, so asking it for a smaller size resamples the glyphs
  and blurs them. Same trap the changelog text hit. 40 glyphs, and it is
  there for any future label that needs to be small.
- Vehicle labels yield to each other the way the place names do. Two
  vehicles parked together printed over each other and came out as
  "truckck".

### Changed
- **The safehouse moved to the north-east corner** (user call — a
  deliberate map revision). It used to search outward from the middle of
  the southmost road band, which dropped it inside the playground. It now
  anchors at the open corner and sweeps west then south. It lands at
  [174, 73]; the playground is clear, and walkable cells are unchanged at
  1297.

### Fixed (test)
- The all-doors check spawned the player 20 px inside the room, which can
  land on furniture or in a wall — the physics then ejects the body to
  resolve the overlap, sometimes to the far side of the door, and it
  reported walking through one. It now skips any sample that does not
  start clear. This surfaced the moment the safehouse move reshuffled
  which door is which, and it was the test, not the door.

## [0.6.23] — 2026-08-02 — five things from a playtest

### Fixed
- **You could walk away from the lift and still extract** (user: "it kept
  letting me extract when i was nowhere near"). My own regression: the
  two-second grace added in v0.6.12 so a car clipping the toll zone would
  not reset its countdown was applied to EVERY zone. The toll is
  something you cross at 190 px/s; the lift is somewhere you stand.
  Grace is now driving-exits only, and stepping off the pad cancels at
  once.
- **You could walk through the front of the extraction train** (user).
  The hull was one quad per car, each starting at that car's origin — but
  the locomotive's art reaches about 46 px PAST its origin, so the nose
  was uncovered, and the cars sit 104 apart while each quad was only 96
  long, leaving a slot between every pair. It is one continuous hull now,
  nose to tail. A train is one solid object.

### Changed
- **Vehicle dots on the map are smaller, named, and told apart.** Trucks
  read blue, cars amber, and each dot carries its word. The label only
  draws when the map is zoomed in far enough to read it — at
  whole-district zoom every label lands on its neighbour.
- **Which leaves a tree drops is read off the variant it was drawn with.**
  It used to be a separate flag passed in alongside the variant, so the
  two could disagree — and a green tree shedding autumn leaves is exactly
  the mismatch nobody catches in review (user reported seeing it). One
  source of truth now; art and leaves cannot diverge.
- **A few turned trees out on the perimeter** (user). Rolled from the side
  rng, so the layout stream is untouched and every building, road and POI
  is exactly where it was — verified identical.

## [0.6.22] — 2026-08-02 — the sun gets in

### Added
- **Sun shafts** (user asked for them; the game had never had any). Light
  rakes across the district when the sun is LOW — nothing at night,
  nothing at noon when it is overhead, strongest mid-morning and late
  afternoon. The bearing swings through the day, so morning light and
  evening light do not arrive from the same side.
- They close off when you step under a roof, and heavy weather kills
  them: you do not get shafts through a storm.
- Screen-space bands rather than volumes cast from the buildings. At this
  scale the read you want is "the light is coming from over there", and
  that costs one full-screen pass; real cast volumes would need an
  occluder per wall and would still be hidden behind the rooftops most of
  the time.
- Dithered in the shader, for the same reason the grade is — these are
  very gradual ramps and they would contour into visible bands otherwise.

### Notes
- Deliberately restrained. Strong god-rays over pixel art read as a
  filter laid on top; this is meant to look like the time of day.
- Perf unchanged.

## [0.6.21] — 2026-08-02 — the day actually moves

### Fixed
- **The time of day barely changed for most of the day.** 07:30 to 17:00
  was a single straight line from white to almost-white — **39.5% of the
  clock with no visible change at all** — and 12:40 sits dead in the
  middle of it (user: "it also doesnt even look like the time of day
  changed"). The sun now swings warm-and-low in the morning, neutral and
  brightest at noon, then back to gold through the afternoon. Measured
  warmth across the middle of the frame: −14 at 07:30, −29 at 12:30,
  −11 at 17:00, −31 at 21:00.
- **Faint concentric rings following the player** (user). That was the
  vignette: a radial ramp that gradual quantises into visible contours in
  8-bit, and it is centred on the screen, which is why it tracked the
  character. It is dithered **inside the grade now**, before the frame is
  quantised — the dither film on the layer above could never fix it,
  because the banding is created by this pass. Vignette also eased from
  0.30 to 0.16.

### Added
- **Rain and thunder are muffled indoors** (user). Weather moved to its
  own audio bus with a low-pass that opens and closes as you go through
  a doorway — 20 kHz outside, 1.25 kHz in, ducked 7 dB, eased over about
  a third of a second so it fades rather than switches. Deliberately NOT
  the whole effects group: your own footsteps and the door beside you are
  not muffled by the wall you are standing behind. It is driven by the
  same interior test that reveals the roof, so the sound can never
  disagree with what you are looking at.

### Notes
- There is no sunbeam in the game; the user asked and it has simply never
  existed. Sun shafts are a real feature, not a bug — noted for the
  polish pass.

## [0.6.20] — 2026-08-02 — the grade stopped turning the lights down

### Fixed
- **Everything had got darker, the character worst of all** (user spotted
  it immediately). The grade's split tone was multiplying by the shadow
  colour directly, and that colour has a luminance of 0.384 — so at full
  blend it dimmed shadowed pixels to a third of their value. Anything
  made mostly of dark pixels, like the raider, took the brunt.
- Both tints are now **normalised to luminance 1** before they are
  applied, so they shift hue and nothing else. A colour grade may
  recolour the picture; it must not quietly turn the lights down.
- Added a **shadow lift** that holds the black floor up, so dark sprites
  keep their internal detail instead of collapsing into a flat
  silhouette, and eased the contrast from 0.17 to 0.13.
- Measured on the raider: ungraded 93.0 mean brightness, v0.6.19 82.1,
  now 90.4. Across the whole centre frame the share of pixels below 60
  went 26.2% -> 36.6% -> back to 26.2%. The remaining full-frame drop is
  the vignette, which is meant to be there.

## [0.6.19] — 2026-08-02 — atmosphere

More of the polish pass, still without redrawing anything.

### Added
- **A screen grade over the whole frame**: a contrast S-curve, a split
  tone that cools the shadows and warms the lights, a highlight lift so
  lamps, windows and sparks carry a glow without a blur pass, and an
  elliptical vignette. It is driven by the clock, so 3am is graded
  differently from noon rather than one look stretched across both.
- **Dust in the air.** One emitter riding the camera rather than one per
  lamp — the district has fifty lamps and fifty particle systems mostly
  emitting off-screen for nobody would be a waste. Faint on purpose: the
  job is to stop the air reading as flat empty colour, and the moment you
  can pick out individual specks it reads as snow.

### Notes
- The grade sits UNDER the anti-banding dither film, deliberately. The
  film exists because slow full-screen fades step visibly in 8-bit, and
  the grade creates new ramps for it to break up.
- Nothing scales or rotates: the motes are fixed at scale 1 and the
  emitter follows the camera in whole world pixels, because a fractional
  emitter hands every particle a fractional spawn point, which is
  shimmer.
- **Honest about strength:** in a daytime still this is subtle. It reads
  in motion and at night, where the split tone pulls the shadows cold
  against a warm flashlight cone. Say if you want it pushed harder — the
  values are four uniforms in one file.
- Perf unchanged: 240 fps, 4.54 ms worst, and the grade measured 4.49 vs
  4.54 ms against a build without it, which is noise.

## [0.6.18] — 2026-08-02 — shaders compile once, quietly

### Added
- **A shader warm-up between the studio card and the menu.** It builds
  every shader pipeline once, up front, rather than dropping a frame the
  first time something flashes mid-raid. It carries a "compiling shaders"
  screen with a progress bar — **which only appears when there is real
  work.**
- **It only runs after an update.** A fingerprint of the engine build plus
  the contents of every `.gdshader` is kept in the user directory; if
  nothing changed, the whole step is skipped. This matches how the user
  expected it to behave, and how Godot already behaved: the engine keeps
  a compiled shader cache on disk, so a plain restart never recompiled in
  the first place.

### Notes
- **Today you will not see the bar, on purpose.** There is exactly one
  shader in the project and a cold build of it takes 40 ms — under the
  120 ms threshold, so the screen stays hidden rather than flashing a
  meaningless progress bar. It starts earning its place as the polish
  pass adds outline, colour-grade and sway shaders. The user pushed back
  on this ("if its 8ms will i even see it? whats the point then") and
  they were right; it ships dormant rather than padded with fake delay.
- Measured with the new `--shaderwarm`: cold run 40 ms, stamp sticks,
  second boot costs 0 ms. The smoke can't reach this path because the
  harness skips the splash, so it gets its own check.

## [0.6.17] — 2026-08-02 — impact

First slice of the visual-polish pass, and it takes the direction the user
set: **the base art is not redrawn.** Everything here is engine-level —
shaders, camera, held time — so it lifts every sprite at once instead of
one family at a time.

### Added
- **Camera kick.** Taking a round, and hitting something in a car, now
  move the world. Strength is in WHOLE SCREEN PIXELS and rides the same
  grid the camera already snaps to, so a shake can never knock the view
  half a pixel off and turn into the shimmer rule 1 exists to prevent.
  The car's kick scales with how hard you hit; thunder gets a small one,
  deliberately under the crash so weather never out-punches a collision.
- **Hit stop.** A 55 ms beat of held time when a round lands. Long enough
  to read as weight, short enough that it never reads as a dropped frame
  — which on a 240 Hz display would be the first thing noticed.
- **A per-sprite hit flash**, as a shader on the existing sprite rather
  than a repaint. It mixes toward flat white on RGB only and scales by
  the sprite's own alpha, so the silhouette can't fatten and the art is
  untouched the instant the flash ends. Per-sprite on purpose: a
  full-screen tint tells you that you were hit, this tells you *what*
  was hit — which is what M3's enemies will need.
- `Juice` autoload owns the hit-stop clock and hands out flash materials
  (one material per sprite, one shared compiled shader). It resets on
  deploy and on leaving a raid: an autoload that outlived a raid mid
  hit-stop would hand the next one a world running at 4% speed.

### Notes
- Perf unchanged: 240 fps, 4.47–4.58 ms worst across four runs, storm
  night included. A one-off 7.9 ms frame on first run was shader
  compilation, and did not repeat.

## [0.6.16] — 2026-08-02 — a changelog worth reading

### Changed
- **The in-game changelog is rewritten from the real write-ups.** Its
  older entries were hand-wrapped into ~52-character fragments to fit a
  narrow window, and the renderer dashes every fragment — so one
  sentence became five stubby bullets and, once the window was widened,
  the text stopped filling it. 65 versions have been rewritten from the
  detail already sitting in this file: the reasoning, the numbers, the
  why. One string per bullet, and the labels autowrap to whatever width
  the window is.
- **Apostrophes** (user: "im fine with apostrophes"). The font has the
  glyph and always did; the old text simply avoided them. Natural
  contractions everywhere now. Lowercase stays hard — the generated
  font has no capital glyphs, so a capital cannot render at all.
- The changelog window is a bit smaller again, 548x330.

## [0.6.15] — 2026-08-02 — the harness stops pretending

### Fixed
- **A harness flag that does nothing now says so and exits.** `--toll`,
  `--freight`, `--at=` and `--seed=` are MODIFIERS for `--shot`, not
  actions. Passing one on its own booted the game to the menu and left
  it sitting there forever — indistinguishable from a hung test, and it
  held the shell open until the process was killed by hand. It cost two
  stray Godot instances and about fifteen minutes of CPU before anyone
  noticed. If arguments are given, one of them now has to be a real
  action or the harness prints what it expected and quits with code 2.

## [0.6.14] — 2026-08-02 — menu housekeeping

### Changed
- **The changelog window is much bigger** — 624x384 instead of 280x210,
  with tighter leading, so seven versions fit where two did (user: less
  scrolling). The text stays at size 9 on purpose: the font is a BITMAP
  font cut at that size, so asking for 8 resamples the glyphs instead of
  re-cutting them, and blurry menu text is a failure this project has
  already had once.
- **The changelog button hides while the map-select panel is open.** It
  lives on the menu root, outside the panel, so it stayed clickable
  underneath it (user).
- **The district blurb reads once.** It used to list every POI as prose
  and then list them all again under "on the board", which meant nothing
  to anyone (user). Now: the places once, then what actually matters
  before you commit — the three ways out, and that snipers own
  everything past the wire. "bring a flashlight" is gone; you always
  have one.
- The district name reads as a heading now (accent colour and a rule
  under it) rather than as another line of body copy.

## [0.6.13] — 2026-08-02 — the train is solid

### Fixed
- **You could walk and drive straight through the extraction train**
  (user). The rake was three sprites and nothing else. It has a hull
  now — one parallelogram per car along the rail axis — which switches
  off while you are riding it, so it never fights the weld that keeps
  you aboard.
- **"the freight leaves in..." was printing over the fps counter**
  (user). It sits top-centre now, on fractional anchors so it stays
  centred at any resolution.
- **The map remembers where you left it.** Pan and zoom survive closing
  and reopening; it only fits the whole district on the first open of a
  raid. The values were already being kept — an unconditional recentre
  on every open was throwing them away.

## [0.6.12] — 2026-08-02 — the toll you paid for, and a bench you can sit on

### Fixed
- **You could drive straight through the toll extraction** (user). The
  zone was 240 px across the radius — 480 wide — and a car tops out at
  190 px/s, so you were out the far side in 2.5 s while the countdown
  needs 5. It is 470 now, just over five seconds through the middle,
  and still stops short of the wire so it can never fire while you are
  inside the district. Clipping the edge at speed no longer resets the
  count either: a two-second grace keeps it running, because you are
  still leaving.
- **Paying the warden lasts the whole raid now** (user drove back in,
  turned around, and was shot on the way out). The stand-down used to
  buy exactly one crossing. That read as a bug, because the boom stays
  up and the warden keeps your money — you were being fired on while
  driving out through an open gate. Dying still cancels it.
- **The benches are benches.** The old one had a *one pixel* seat, so
  it read as a fence going up with nowhere to sit (user). Rebuilt as a
  real isometric bench: a seat surface with lengthwise slats, a
  two-slat backrest and four legs.

### Fixed (regression caught in the same pass)
- Removing the telegraph poles' random offset in v0.6.11 also removed
  **two draws from the layout RNG**, which silently re-rolled part of a
  district that is supposed to be FIXED. The roll is taken and thrown
  away now, and doors, stairs, lamps and walkable cells are once again
  bit-identical.
- The closed-door smoke test now walks into **every** door from **both
  sides** at five offsets, not just the first one. Testing a single
  door hid a real failure: when the layout shifted, a different door
  let the player through. All 15 pass.

## [0.6.11] — 2026-08-02 — the wires along the line

### Added
- **Telegraph poles carry wires now** (user: they had none). Four thin
  lines strung pole to pole along the railway, sagging between the
  crossarms. A telegraph route *is* its wires — without them the poles
  were just posts.
- The run skips a span wherever the line changes sides of the track,
  because it genuinely breaks there.

### Changed
- **Power pylons only appear in the woods and out toward the wire**
  (user). The middle of the district is telegraph-pole country; the two
  are different things and mixing them made neither read. Out on the
  outskirts the run thins rather than marching unbroken to the edge.
- Telegraph poles no longer take a random position offset, and their
  crossarms sit at a fixed height. Both were necessary for the wires to
  meet them — the same lesson the pylon spans already taught: the art
  is drawn for one exact gap, so a jittered pole is a pole the wire
  cannot reach. The pole *top* still varies, and the lean and the
  missing-arm variant carry the rest of the variety.

## [0.6.10] — 2026-08-02 — you can see the whole door

### Fixed
- **A door opened from inside was cut in half by the board beside it**
  (user). v0.6.6 made the jamb boards draw *over* the leaf so the wall
  correctly hides a door swinging into the room. When the outward swing
  arrived in v0.6.9 that order was left alone — but an outward door
  swings *toward* the camera and has to cover the jamb, not hide behind
  it. The draw order now flips with the swing.

## [0.6.9] — 2026-08-02 — doors get out of your way

### Changed
- **A door now swings away from whoever opens it** (user). Stand
  outside and it opens into the room; stand inside and it opens out to
  the street. You are never pushed backwards by a door you just opened.
- Both swings live in ONE sheet — frames 0–3 inward, 4–7 outward — so
  it stays a single texture and a single prop. The generator emits a
  second open-state collider for the outward leaf, and whichever leaf
  is actually swinging is the solid one, so the "never a ghost"
  guarantee from v0.6.6 holds in both directions.
- The smoke asserts a door opened from outside does **not** swing
  toward the player, and places the player deliberately first so the
  rest of the door checks stay deterministic.

## [0.6.8] — 2026-08-02 — the upstairs floor stays inside the house

### Fixed
- **The second floor was clipping over the top of the house** (user,
  with the shape drawn on a screenshot). v0.6.7 fixed the floor by
  putting it in front of the walls — which was only half right. A
  second floor is a horizontal plane, and a plane sorted as ONE unit
  is either in front of every wall or behind every wall, and both are
  wrong. Anchored north it hid behind the building's own walls, so the
  furniture floated over grey. Forced in front, it painted over the
  near walls and sat on top of the roofline.
- Each floor tile is now **its own y-sorted node** at its true cell
  position, with the art lifted by a sprite offset rather than by
  moving the node. Sorting position and drawing position are separate
  things, and splitting them is the whole trick: the walls in front of
  you occlude the floor, the walls behind you do not, and neither
  needs a z_index. The z band from v0.6.7 is gone, along with the
  special case that had to be added to keep the staircase from being
  swallowed.

## [0.6.7] — 2026-08-02 — the upstairs floor, and three audit finds

### Fixed
- **Second floors: the furniture no longer floats.** Climbing the
  stairs showed the upper furniture standing on grey nothing, with the
  floorboards visible only as a band through the middle of the room.
  Both leads recorded in the handoff were wrong and are now retired:
  the slab is built correctly and every one of its tiles exists
  (`--probe-world` reports `UPPERS total=6 floorless=0`). The problem
  was **draw order**. A second floor is a horizontal plane, and
  y-sorting a plane against vertical walls cannot work — the container
  is anchored far north so the player always sorts above it, but that
  also put it *behind* the building's own walls, which sit at much
  larger y. So the walls painted over most of the floor. The upper
  floor now takes its own z band while you are on it: the slab above
  the ground floor and its walls, and the player, the upper furniture
  and the staircase above the slab. Everything drops back on the way
  down, so nothing outside that building is touched.
- Proved by experiment rather than argument: `--upstairs=<n>` puts the
  player on a second story and reports the state, and forcing the slab
  to the front made the floor fill the room. `--upstairs` stays as the
  standing check for this.

Three more came from a multi-agent audit of the whole codebase: 35
candidate findings, each handed to skeptics told to refute it. Five
survived; two of those were already fixed in v0.6.6.

### Fixed
- **Dying and then abandoning gave you two debrief screens.** Death
  holds for 1.2 s before it builds its debrief. Pressing escape and
  hitting "abandon raid" during that hold ran both paths, stacking two
  full panels on the same layer — the death timer keeps counting even
  though the tree is paused, because Godot's scene-tree timers default
  to running while paused. There is now one flag, and whichever path
  arrives first owns the screen.
- **Sniper rounds were appearing inside your view instead of flying in
  from off-screen.** They spawned a fixed 430 px away, commented as
  "beyond every supported view half-diagonal". That was true of the
  640×360 design base, but the default setup — borderless at the
  desktop resolution — renders 840×540, whose half-diagonal is ~500.
  At the widest zoom the rounds were popping into existence on screen.
  The distance is now measured from what the camera can actually see,
  at whatever zoom you are on, plus clearance for the camera offset
  and the predicted-aim lead. It only ever increases at the widest
  zoom; zoomed in, the visible rect is smaller than the old floor and
  nothing changes.

### Changed
- The map's place names moved to the layer that only redraws when you
  pan or zoom. They were on the every-frame markers layer, so roughly
  135 text-shaping calls ran at render rate the entire time the map
  was open — on top of the live raid, since the map deliberately does
  not pause the tree. **Honest note: no measured frame-rate win.**
  Across three runs each the difference sits inside the run-to-run
  spread, and the machine holds 240 fps either way. It is strictly
  less work per frame and matches the file's own stated intent, so it
  stays, but it is not a fix for a visible stutter.
- `--perf` accepts `--map=transit`, so the map screen's cost over a
  live raid can be measured rather than argued about. It runs about
  1.0 ms/frame while open, before and after this change.

## [0.6.6] — 2026-08-02 — the door is solid, for real this time

### Fixed
- **Doors are solid in every state.** v0.6.5 added a second collider
  for the open leaf but put it in the wrong place, so the problem
  survived. Three separate bugs, all measured rather than reasoned:
  the swung collider was mirrored **180° for south-facing doors** (the
  common kind) so it sat a whole cell away from the visible panel;
  the east door's open frames **ran off the edge of their canvas** and
  were silently cut in half; and the open leaf used *wall* thickness,
  which made the swung panel reach back across its own doorway and
  seal the middle of the opening.
- The earlier diagnosis — "the leaf opens in place, it doesn't swing
  aside" — was **wrong**, and it came from measuring the sprite's
  centroid. In an isometric view both ground axes point right, so a
  correct 90° turn barely moves a centroid sideways. Measuring the
  leaf's free end shows the art always did swing a full quarter turn
  into the room.
- **Mid-swing the doorway stays shut.** Opening a door used to clear
  the doorway on the first frame, so for the whole 0.24 s animation
  you could walk through a door that still looked closed.
- **The jamb boards beside the opening are solid**, so an open door no
  longer lets you walk through the timber next to it.
- The open frames are sampled along their screen run instead of
  lerping the step vector, which had been under-sampling the middle
  frames — east doors lost most of their leaf and all of their handle.
  Doors were also removed from the clip-audit exemption list, which is
  what had hidden the canvas overrun.

### Changed
- The open and jamb colliders now come from the generator through the
  manifest (`collider_open`, `collider_jambs`). `Door` derives no
  geometry of its own — deriving it is what caused the mirrored panel.

### Fixed (test infrastructure)
- **The door smoke test was vacuous and had been for three releases.**
  It set `velocity` and called `move_and_slide()` in a loop, which
  scales motion by the frame delta; a headless run is uncapped, so the
  player advanced a fraction of a pixel per step and never travelled
  the 26 px to reach the door. Every "did it walk through?" assertion
  passed without anything being touched — which is why v0.6.3 could
  not reproduce the user's report. Pushes now use `move_and_collide`
  in fixed 1 px steps with proper sliding, so they are frame-rate
  independent. The closed door, the swung leaf (from both sides), the
  mid-swing panel, and the opening's passability are all covered.
- `--probe-world` reports second floors:
  `UPPERS total=6 floorless=0 propless=0 stairs=6`.

## [0.6.5] — 2026-08-01 — the door is solid either way

### Fixed
- **A door has collision all the time now, not only when it's shut**
  (user). Opening one used to switch its collider off entirely, so the
  panel became a ghost you could walk straight through — which is what
  the "walk through doors" reports were about. The leaf now carries a
  second collider in its swung position: closed, it blocks the
  doorway; open, it blocks where the panel actually stands. You walk
  through the opening and never through the door.
- The smoke test covers both states: it walks into a closed door from
  five offsets, and asserts an open door still has a solid leaf.
- **The warden can be talked to from a car** — he gets his prompt while
  you're driving, since pulling up to his window in a car is how
  you'll always arrive (the car already acted on the F press; there
  was simply no prompt to tell you so).

## [0.6.4] — 2026-08-01 — walls are one surface

### Fixed
- **The black lines running down every building are gone.** Each wall
  segment ran the automatic outline pass, which draws a dark border on
  every side — including the left and right edges, where segments tile
  against each other. So every join became a black seam, and the whole
  building read as blocks stacked together instead of a wall.
- **That seam is also what showed the player through the wall.** Two
  outlines meeting leave a hairline the wall's own brick never fills,
  and standing close on the far side put an arm through it (user
  screenshot). Tiling pieces now outline their silhouette only —
  `outline_auto(sides=False)` — so there is no seam and nothing to see
  through.

### On the door report
The door's collider is **byte-identical to a wall segment's**
(`[-13.6,-12.8, 18.4,3.2, 13.6,12.8, -18.4,-3.2]`) — a closed door is
exactly as solid as the wall it sits in, and the v0.6.3 smoke test
confirms it blocks from every offset across the leaf. The see-through
above is the most likely thing that was actually being seen. If a door
still lets you pass after this, a circled screenshot pins it down.

## [0.6.3] — 2026-08-01 — a timetable worth learning

### Changed
- **The freight runs three nights in seven** (user call), not every
  night. The three are drawn without replacement each week, so they
  land wherever they land — two together at the start and one at the
  far end is a perfectly good week — and the timetable is re-rolled
  every seventh night. She still arrives at 24:00 on the nights she
  runs, and mara only calls her in on those nights.
- **The cables inside houses are gone.** The exterior box still says
  where a house gets its power; running the flex across the floor
  inside read as clutter rather than as wiring (user).

### Testing
- **Closed doors now have permanent regression cover:** the smoke test
  walks the player straight into a closed door from five lateral
  offsets across the leaf and fails if they get through.

**On the door report:** I could not reproduce it. The new test blocks
at every offset, so a closed door does stop you head-on across its
whole width. It may be an open door's leaf (passable by design), the
wall beside a doorway, or a particular orientation — a circled
screenshot would pin it down.

## [0.6.2] — 2026-08-01 — windows take the HUD with them

### Fixed
- **"press f to open" stayed on screen behind the pause menu** (user
  report), and so did the driving hint, the freight's departure notice
  and mara's radio call. All of them come down while any window is up
  and come back when it closes.
- The reason it couldn't fix itself: most windows **pause the tree**,
  so the labels' owners stop processing at exactly the moment they'd
  need to hide. The window stack now does it for them — opening or
  closing anything tells the `hud` group, which works fine while
  paused. The map, which deliberately doesn't pause, is covered by the
  per-frame check as well.
- The interaction target is dropped along with the prompt, so F can't
  act on something you were standing next to before opening a menu.

## [0.6.1] — 2026-08-01 — the lines actually connect

User photographed the run with red lines drawn where the wires should
be: connected, tower to tower, all the way along.

### Fixed
- **The towers were getting a cell of random jitter**, like every
  other prop in the district. A span is drawn for one exact six-cell
  step, so a tower nudged diagonally off the line could never meet the
  next crossarm — the wires left one tower and missed the other. The
  line is dead straight now, which is also what a transmission line
  actually is. Verified by composing two towers and a span offline and
  checking the wire lands on both crossarms.
- **Only a building or the railway can refuse a tower.** Junk on the
  ground used to block one, and every skipped tower killed two spans,
  leaving long gaps that stopped reading as a line at all. A pylon
  foot standing in the litter is fine.
- **Damage is the exception now, not the rule.** Roughly one tower in
  twenty-five comes down and one span in twenty is snapped, instead of
  a quarter of each — a stretch where most spans were broken just read
  as disconnected rather than derelict.
- **A downed tower still gets its incoming span**, drawn as the
  snapped one: you see the line arrive and drop, which reads far
  better than the wires simply stopping short of nothing.

## [0.6.0] — 2026-08-01 — the grid

### Added
- **Power lines across the district** (user spec). A line of lattice
  towers marches the width of the map with real catenary strung
  between them — the sag is deepest mid-span, and the wires hang
  *above* everything, so they cross roads, sidewalks and shelters the
  way overhead lines do.
- **A good deal of it is down.** Towers come in four states: two
  standing designs, one leaning with a bent arm, and one snapped off
  above the waist with its cables trailing. Spans go missing outright,
  and some are **snapped** — they leave a tower, sag, and end in
  mid-air where the rest came down.
- **The yellow cabinet by the relay.** The run walks to the comms
  relay and goes underground into a utility box on the back of the
  last tower, with a toolbox, drums and a crate left on the ground
  around it. Not a POI — just a thing that's there, as asked.
- Towers are one design repeated with wear, per the standing rule for
  municipal infrastructure, and every standing tower is exactly the
  same height so the spans always meet the crossarms.
- The whole run is rolled from the side RNG, so adding it didn't move
  anything else in the district.

## [0.5.14] — 2026-08-01 — dying ends the raid

### Changed
- **Death ends the raid** (user call). Three rounds used to fade to
  black and wake you back at the safehouse — the placeholder from
  before extraction existed, and it left dying *cheaper* than walking
  out. Now it hands you the same debrief: the doll with the parts that
  took rounds, what was lost with you, who did it and where.
- Dying still tidies what you left behind first — you're taken off the
  second floor and out of the car (engine and headlights off) before
  the screen comes up.
- If a raid somehow has no debrief to show, the old respawn is still
  there as a fallback, so nothing can strand you in a dead world.

### Testing
- The smoke test now **asserts** it: at the end of its run it takes
  three rounds and requires the debrief to appear with the raider
  actually dead. It suppresses the debrief while it's probing
  everything else, because a paused tree behind a death screen would
  strand every later check — the flag is set for exactly that window
  and turned back on for the assertion.

## [0.5.13] — 2026-08-01 — the bill for walking out

### Added
- **Abandoning a raid costs you.** The pause menu's "main menu" is now
  **"abandon raid"**, and it hands you the same debrief dying would
  (user call — quitting mid-raid used to be a free escape, and nothing
  carried over anyway).
- **The debrief reads like a report:** how long you lasted, xp earned,
  kills and raider kills, rounds taken, and what was lost with you —
  money now, the haul once the stash lands in M4.
- **A hit-location doll**, Tarkov-style. Every round the wire puts in
  you records **where** it landed and **who** sent it; the doll marks
  the parts that took them — head, eyes, thorax, stomach, arms, legs —
  reddening with the count, one tick per round, with the full list
  underneath giving the minute, the part and the shooter.
- Snipers roll a real hit location per round: centre mass most of the
  time, with the head, eyes and limbs taking the rest.
- Harness: `--death` takes a few rounds and abandons, so the screen is
  shootable.

**Still to decide:** actually dying (three hits) still respawns you
mid-raid, which is the old placeholder behaviour — it should probably
end the raid into this same screen. Say the word and it will.

## [0.5.12] — 2026-08-01 — every place has its own things in it

### Added
- **A dressing pass for the rest of the POIs** (user: "liven up the map
  a bit. but not too many objects or else it will look odd"). Each
  place gets a handful — four to seven pieces — of things that belong
  to it and nowhere else:
  - **courtyard** — planters, benches, a vending machine, a news box
    and what people left behind around the dry fountain
  - **bus depot** — fare boxes, a mechanic's leavings, tyres and drums
    among the buses
  - **playground** — tyres to climb on, a bench for whoever watched,
    litter in the grass
  - **gallery** — more cans, pallets, a dumpster: what the painters
    brought and never took home
  - **comms relay** — cable drums, a toolbox, the crate the dish came in
  - **the lift** — fuel and freight stacked at the rim of the clearing
    (the clearing itself is claimed ground, so it stays clear to land in)
  - **toll gate** — the warden's own chair, brazier and crates, just
    off his booth
  - **trainyard** — sleepers, drums and gear beside the running line
- Unknown families are skipped rather than crashing the build, so the
  per-place lists can name props a future map might not have.

The scrapyard keeps its hall (user confirmed) — only its stock moved.

## [0.5.11] — 2026-08-01 — freight belongs to the warehouses

### Changed
- **The crates and shelves left the scrapyard** (user call). A
  scrapyard is where things get taken *apart*, so it keeps the
  machines: the vehicle rows, the crane, forklifts, drums, gas
  cylinders and a new **toolbox** family (four variants, some standing
  open with tools showing) left where somebody put them down. The rack
  line along its south edge is now a machine line.
- **The warehouses got all of it, and more.** Their yards carry two to
  three times the stock they did: stacks and pallets spilling out of
  the doors, a line of loaded shelving stood against the outside wall
  with boxes beside it, and one or two trucks backed up with their
  load piled at the tailgate. Inside, the halls are packed — 16–26
  pieces weighted hard toward boxes instead of 8–14 spread evenly.
- **"foggy" is gone from the weather line.** The mist rolls in every
  morning, so reporting it as a forecast said nothing (user call).
  The spells are clear, rain and storm; the morning still reads
  "morning mist" because that's a time of day, not weather.

## [0.5.10] — 2026-08-01 — real weather, and a map that names things

### Changed
- **Rain and storms are genuinely different weather now.** The user
  asked whether there was actually a difference — there wasn't: one
  wet state, and "storming" was just the label for heavy rain. There
  are four spells now: **clear**, **fog**, **rain** and **storm**.
  A storm rains at full strength and throws lightning every 7–19 s;
  plain rain is visibly lighter and only flashes every 45–110 s. Fog
  is its own spell that rolls in and out over ~18 s, on top of the
  dawn mist that was always there. Clear runs longest.
- **The map bar reads "07:12 morning — raining"** — the clock, the
  part of the day (dawn / morning / afternoon / evening / night) and
  the weather, with the environment naming its own weather instead of
  the map guessing from rain density.
- **"court" → "courtyard"** and **"depot" → "bus depot"** on the map.
- **The lz, the gallery, the comms relay, the trainyard, the scrapyard
  and the playground are outlined** on the map like the paved places
  are, so they read as somewhere rather than a word floating over open
  ground.

## [0.5.9] — 2026-08-01 — the clock and the light agree

### Changed
- **The day/night gradient is re-timed to real hours** (user call):
  dawn at **06:00**, full day 07:30, the light going warm from 20:00,
  **dusk at 21:00**, deep night by 22:15 and still dark at 05:00 —
  night is now about nine hours of the cycle. Both endpoints stay
  DEEP_NIGHT so midnight can't snap. `_night_amount_for` (lamps,
  interior lights, the flashlight) tracks the same stops, the dawn fog
  window moved with dawn (04:48 → 09:00), and a raid now starts at
  07:12 instead of 04:19. The freight's 24:00 arrival sits deeper in
  the dark than before.

### Fixed
- **Master volume at 0 didn't silence music.** Measured first: the
  master bus *was* muting correctly (-80 dB, muted, with the music
  player routed through it), so the reported symptom didn't match the
  bus graph. Master now scales **every channel bus** as well as the
  master, so a master of zero mutes music, effects and ambient
  directly — belt and braces, whatever slipped through before.
- Added `--audiodebug` to the harness: it drives the real volume panel
  slider and dumps the bus graph and every player's bus, so audio
  reports get measured instead of guessed.

### Added
- **Blue sparks off the broken power boxes** (user request): two to
  four thrown clear of the housing on each burst, arcing out, falling
  and burning out. Blue because that's what a real short throws, and
  it reads against the warm arc inside the box. *Worth a look in
  motion — bursts are brief and a screenshot rarely catches one.*

## [0.5.8] — 2026-08-01 — the district's clock, on the way in

### Added
- **Map select shows the live in-game time and day/night** before you
  pick a district (user call), and it ticks while you sit there.
- **One world clock.** It lives in the `Raid` autoload; the menu
  advances it and the environment both reads it on deploy and writes
  it back as it runs — so the time you read on the way in is the time
  you land in, and the district keeps its own time while you're in the
  menu. The environment still owns the day *length* and publishes it,
  so there's a single source for that.

**Known oddity, worth a decision:** the clock and the lighting curve
don't agree with real-world intuition — nightfall currently lands at
15:22 and dawn at 04:05, so the screen can read "04:19 — day". The
freight's 24:00 arrival *is* correctly at peak darkness. Re-timing the
gradient so dusk falls nearer 21:00 and dawn nearer 06:00 is a small
change; say the word.

## [0.5.7] — 2026-08-01 — the freight keeps a timetable

All from the user's live playtest.

### Changed
- **The night freight runs on the in-game clock, at 24:00.** She was
  on a five-real-minute cycle, which is why she turned up in the
  morning. Now she arrives at midnight — the darkest point — once per
  in-game day, and mara calls her in just before, so the warning and
  the arrival are the same event. Her lines no longer promise "five
  minutes till the next one"; she's back tomorrow night.
- **The day is longer**: a full cycle is 18 minutes, up from 10.
- **Mara's popup**: the "mara" name plate is gone and the freight line
  no longer says "magpie, mara." — she named herself twice in three
  words. It reads "magpie, ive got a freight inbound to the trainyard.
  give or take." Calls also hold **6.5 s** instead of 4.6 (user: they
  went by too quickly).
- **A very quiet tick** as she keys up (-30 dB, on the sfx bus), and
  still nothing at all when the call drops off.

### Fixed
- **The freight drove through parked boxcars.** Stranded stock was
  placed ON the running line; it now sits a track over on the ballast
  shoulder, so the main line the freight uses stays clear. Sidings
  keep their rolling stock.

## [0.5.6] — 2026-08-01 — lit rooms, and the cable that feeds them

### Added
- **Every house has a room light.** A tin shade on a short flex, hung
  mid-room; it comes on with the dark off the same broadcast the
  street lamps ride, and about a third of them flicker and drop out
  the way a bad supply does. The pool is deliberately tight — a wide
  one washed straight through the walls and lit the street.
- **The cable is real** (standing rule: a powered thing must SHOW
  where its power comes from). The builder lays flex cell by cell from
  the fixture to the wall its exterior power box is bolted to, and you
  can follow it across the floor.
- **The safehouse is wired and dark.** Its box is the broken, arcing
  one, so the flex is there and nothing comes down it — which is the
  whole reason it's a repair job later.

### Notes from getting it working
- Flat decals needed **their own layer** between the floor tilemap and
  the y-sorted world. A `z_index` of -1 inside the y-sorted node sorts
  globally within the canvas layer, so the cables rendered *behind the
  floor* — present, positioned correctly, and completely invisible.
- The fixture is pushed **away from its own box** until the run has
  room to cross open floor. Hung at the room's centre it often landed
  a cell or two from the box, and those cells sit behind the wall
  sprite — again, drawn and invisible.

## [0.5.5] — 2026-08-01 — pines shed needles

### Added
- **Conifers drop needles.** v0.3.14 excluded them from shedding so
  they couldn't drop broadleaf leaves out of a pine — but a pine that
  drops nothing reads as dead (user). They now have their own drop:
  two needle sprites (a fresh green and a dried tan, both brighter
  than the canopy so they don't vanish into the forest floor), a
  thinner shape than a leaf, and their own fall pattern — straight
  down with a slight lean and no flutter, because a needle has no
  blade to catch the air. They fall faster and from tighter in against
  the trunk than a leaf lets go.
- Dead bare snags still drop nothing, by design.
- `--probe-world` prints `SHEDDERS green=/red=/needle=` — this seed
  registers 182 green, 46 autumn and **136 conifer** shedders.

**Worth a look in motion:** inside the dense woods the needles are
subtle against the forest floor's own green speckle; they read most
clearly on pines standing in the open. Say the word and they can go
bigger, brighter or more frequent.

## [0.5.4] — 2026-08-01 — the roads stop somewhere

A deliberate **map revision** of transit-01, approved by the user
("yes its ok to change the map up a bit"), not a re-roll: the fixed
district keeps its seed and every place stays put.

### Changed
- **Roads no longer all cross the whole district.** Each road now
  carries a span, and most of them stop short — the council never
  finished this district. This seed's network: the middle vertical
  (the toll crossing, kept whole on purpose) and two crosstown roads
  run edge to edge; the other five stop, one of them at both ends.
  The north-west and north-east corners now have **no road at all**,
  which is the point (user: "some areas with no roads").
- **Broken ends.** Where a road gives up, its last three cells crack
  and pothole, and the cut is buried under rubble with the odd barrel
  and stick spilling two or three cells past the last slab.
- Sidewalks, crosswalks, traffic lights, street lamps and level-
  crossing signals all follow the spans — no walkway running off past
  a road that was never built, no zebra crossing to nowhere, no lit
  pole standing on unpaved ground.
- The **map screen** draws the real network, stubs and all, instead of
  a tidy grid the district doesn't have.

### How the revision was kept surgical
The spans are rolled from a **side RNG** seeded off the district seed,
so they consume zero draws from the layout RNG: blocks, buildings,
zones, POIs, the rail line, the toll crossing and the safehouse spawn
are bit-identical (verified: `POI safehouse=[127,170,7,6]`,
`POI toll gate=[145,187,5,5]`, unchanged). Only decoration placed
*after* the road passes (lamps, furniture, scatter) shifts, because
skipping a crossing that no longer exists changes what those passes
roll. Road-end dressing spends the side RNG too.

Perf: 240 avg, worst frame 5.53 ms, ~7.6k nodes.

## [0.5.3] — 2026-08-01 — first-open hitches, prewarmed

User confirmed the dip is **first open only** — the changelog panel,
and the map "when i load into the map, i drop down to like 80 fps for
a sec".

### Fixed
- **The changelog built ~300 Labels in the frame you clicked it.**
  Every shipped version's lines were created, shaped and laid out
  lazily on first open. They're now built during the menu's own boot,
  a slice per frame on a ~1.2 ms budget (under the 0.5 s fade-in),
  followed by one invisible layout pass — so the first open has
  nothing left to pay for. Opening it mid-warm is handled; if the
  prewarm never ran, first open still builds them as before.
- **The map drew its whole vector district on first open.** Roads,
  blocks, every building and grove, all in one frame. `MapView` now
  takes one real draw during the deploy tail — the deploy screen is an
  opaque layer 95 and the map is layer 75, so it draws for real behind
  the curtain and the first M press is warm. The prewarm deliberately
  does not touch the window stack, so it can't be mistaken for an open.

## [0.5.2] — 2026-08-01 — the centre line, actually centred

Third attempt, first one measured instead of reasoned — the user's
red-line photo plus pixel measurement of the rendered road.

### Fixed
- **The yellow centre line sat a full lane off, on half the roads.**
  Measured before: the dash sat **0.95 cells** from the centre of the
  four-cell road band. Measured after: **0.02 cells**, with the dash
  weight unchanged (6 screen px, same as before).
  Two compounding causes, neither visible from reading the code:
  - An iso diamond tile only **owns two of its four edges** (the
    top-left and top-right ones); the other two belong to its
    neighbours or the atlas wouldn't tessellate. Both halves of the
    dash were painted along edges their tile does *not* own — so the
    plain "b" tile rendered **literally zero yellow pixels** (verified
    against the atlas), leaving one lone half-dash a lane out, and the
    `_h` non-b tile rendered a 6-pixel sliver.
  - The `p` parameter runs **with +x** on the plain tiles but
    **against +y** on the `_h` ones, so one shared edge condition
    cannot be correct for both orientations. The horizontal roads
    happened to land on the true centre and the vertical ones did not
    — which is why it looked fine half the time and wrong half the
    time.
  Each half now measures the region its tile actually owns and paints
  against the shared boundary, so the dash straddles the true centre
  on both road axes.

## [0.5.1] — 2026-08-01 — shelters off the crossings

### Fixed
- **Bus shelters no longer hang into the crossing road.** A shelter is
  ~1.5 cells long, and the strip cell nearest an intersection still
  has the corner walk cell between itself and the asphalt — so a
  placement there put the roof and glass over the road (user report,
  queue item). Placement rolls burn identically (fixed district safe);
  a shelter whose span would reach a crossing road within two cells
  along its run is simply dropped. Verified at the toll-road crossing:
  the offending shelter is gone, the legitimate one is untouched, and
  everything else in the frame is pixel-identical.

## [0.5.0] — 2026-08-01 — the volume page

### Added
- **Settings → volume** (user call): four sliders — master, music,
  effects, ambient — applying live and persisting in settings.cfg.
  Implemented as real audio buses (`music` / `sfx` / `ambient` routed
  to Master, created by Settings before any audio autoload loads):
  one-shots, steps, horns, car doors and the alarm ride `sfx`; the
  rain bed, thunder and the engine loop (its low-passed bus now sends
  to `ambient`) ride `ambient`; the music player rides `music`. Player
  `volume_db` is never touched, so the music fades and every per-sound
  level keep working underneath the mix. The pause menu and the main
  menu both host the page; ESC steps back through it; harness:
  `--menu=volume`.

## [0.4.14] — 2026-08-01 — the safehouse's problem, and a quieter mara

### Changed
- **The broken, sparking power box is always the safehouse's** (user
  call — a repair quest hangs off it later). The old random pick still
  rolls so the fixed district doesn't reshuffle; the spark just lives
  on the spawn house wall now, lid ajar, arcing beside the door.
- **Mara's radio popup is silent** (user call): the squelch on appear
  and the squelch on disappear are both gone. `Sfx.play_radio` itself
  is kept for M2's walk-in in case a subtle version is ever wanted
  back.

## [0.4.13] — 2026-08-01 — the car faces where it drives

User report (before sleep): driving left showed the truck — and the
cars — facing right.

### Fixed
- **The flank sprites were wrong twice over.** `_veh_profile` runs
  front→rear from index 0, and the flank painter draws index 0 at the
  LEFT — so the body was drawn front-left while the docstring believed
  front-right: the headlight/tail colours were painted on the wrong
  ends, and the art was then registered as the EASTBOUND sprite with
  its mirror as westbound — backwards. Now: the drawn art is the
  westbound sprite (front left, headlights left, tails right), the
  mirror is eastbound, the `_door` frames follow, and the manifest
  light coords ride the corrected ends. The diagonals and the head-on
  views were verified correct and untouched.

### Changed
- **Steering is instant** (user call, supersedes the v0.3.6 carve):
  W/A/S/D — and two keys together for a diagonal — snap the nose to
  that heading immediately. The steering-inertia slerp, the facing
  hysteresis and the turn cooldown are gone. Accel, braking, coast,
  crash physics and the iso squash are unchanged.

## [0.4.12] — 2026-08-01 — taking out the dead code

The audits' verified-safe dead list, deleted. No behavior change — the
point is less surface for the next bug to hide in.

### Removed — scripts
- `world_builder._scatter_around` (the live scatter paths use
  `_place_pile` / `_pick_variant_varied` directly), `extraction.
  zone_position`, `night_freight.in_range_of` and its duplicated
  `state = AWAY`, `Door.INTERACT_RANGE` and `Stairs.INTERACT_RANGE`
  (the toll gate's stays — the prompt and the car both read it),
  `TollDialog.closed` and `ExtractScreen.dismissed` (signals nothing
  connects to), `Ui.owns`/`Ui.top`/`Ui.changed`, map_view's `INK`, and
  the world-builder's `if false` ternary.

### Removed — generator
- The orphaned menu-scene painters `_dither_fill` / `_vgrad` / `_paste`
  / `_skyline_row` (stranded when the storm backdrop was retired) and
  `diamond_bottom_y`; the never-placed families `bus_ne` / `bus_sw` /
  `boxcar_y` / `graffiti_y` (15 PNGs); the unreachable `rail_y` /
  `rail_cross_y` tiles — the district only ever runs rail on x, and the
  maker stays parameterized for a future map that doesn't; and two
  `if False` ternaries (one hid a non-palette colour that would have
  crashed the palette check if ever flipped).

Verified: regeneration proved every surviving sprite byte-identical
(only `floors.png` repacks, and a courtyard shot renders 0 pixels
different against the old atlas); probe bit-identical; SMOKE PASS.
Full art regen + reimport measured at ~5 s total.

## [0.4.11] — 2026-08-01 — the sweep, part two

The remaining fifteen findings from the v0.4.10 audits, fixed. The two
world-builder fixes were verified against the fixed district: the probe
is bit-identical to before (only the unseeded per-raid fog wind
differs), and the one visible change is the intended one.

### Fixed — extraction & death
- **Dying mid-lift stranded the raid.** The helicopter was never freed,
  `_leaving` never reset, and the raider respawned while the sequence
  tweens kept writing to him — no extraction worked for the rest of the
  raid. Death now aborts the sequence: the live tween leg is killed (a
  killed tween never fires `finished`, so the legs poll instead of
  awaiting the signal), the bird is freed, and the state machine resets.
- **You could walk or drive away from your own rope.**
  `set_physics_process(false)` gated nothing — movement runs in
  `_process`. A real `extracting` flag now freezes input (movement,
  interact, flashlight, zoom, the F prompt) while the camera still rides
  the lift; and the lift countdown no longer runs while you're sitting
  in a car — the rope takes a raider, not a sedan.
- **The sniper stand-down never ended.** Pay the toll once and the whole
  ring stayed blind for the rest of the raid, anywhere on the map. It's
  one crossing now: go past the wire and come back inside and the guns
  re-arm — and a respawn always re-arms them.
- **Dying at the wheel left the car running.** Engine state, headlights
  and the driver reference were only cleared by the normal exit path;
  death now runs `abandon()`, so the wreck isn't sitting there with its
  lights burning and the next entry doesn't invert the light toggle.
  Dying during the entry door-swing no longer seats your corpse either.
- **The ground-floor door under a second story could stay open.** The
  stairs auto-close called `toggle()`, which refuses while the leaf is
  mid-swing — and an open doorway up there lets you walk out into the
  air. A `force_closed()` now lands the door shut from any state.

### Fixed — world builder (fixed-district safe)
- **A barricade could spawn under the toll booth** — and on transit-01
  one actually did: the ring pass dressed the booth's cells before the
  booth existed. The booth's ground is now reserved before any ring
  dressing; every rng roll still burns exactly as before, so the rest of
  the district is untouched (verified: probe-identical, and the only
  pixel change at the gate is the removed piece).
- **The safehouse's overlap guards never guarded.** It plans before the
  courtyard, depot apron, comms and gallery exist, so its intersect
  checks always passed — on other seeds the depot apron could paint
  straight through the spawn house. The dead checks are gone and the
  protection now lives on the other side: the plaza and apron paint
  around the safehouse, and the comms/gallery corner picks walk to a
  free corner without extra rolls.

### Fixed — polish
- **Power-box sparks re-rolled their texture every frame at 240 Hz** —
  read as shimmer, not electricity. Each arc frame now holds 45–80 ms.
- **The smoker's exhale showed all its wisps at once, fully lit.** The
  stagger ages were right and the visibility math ignored them; wisps
  now appear one by one off the exhale (and the dust texture is cached).
- **The world-map tooltip stuck between the two "???" tiles** — hover
  state was keyed on the blurb text, which both tiles share. Keyed on
  the tile now.
- **Rain shots could come back empty.** Re-forcing weather (the shot
  harness re-applies flags after the camera settles) double-counted
  every live drop, so the spawner thought the sky was permanently full.
  Live drops are now counted on the inactive→active transition only.

### Performance
- **The deploy tail lost its unbudgeted stalls**: the map bake, the
  vector-map plan and the fog/puddle collectors ran 65k-cell loops with
  no yield after the last placement pass — they tick on the same 2.4 ms
  frame budget as everything else now, and the night freight no longer
  re-parses the 137 KB art manifest (the builder's parsed copy rides
  along in the world info).
- The prop scatter dropped a redundant fixed-count yield that fought the
  time budget, the freight/extraction countdown labels re-shape their
  text only when the digit changes, and the landing-zone smoke column
  stops simulating entirely once it can't be on screen (it ran the
  whole raid).

Perf after: 240 avg fps, worst frame 4.50 ms (baseline 4.45–4.72).

## [0.4.10] — 2026-08-01 — the sweep, part one

Three parallel audits read every script end to end. These are the
severe findings, fixed. The rest are logged, not silently dropped.

### Fixed — softlocks and game-breakers
- **Quitting to the menu with a window open bricked every later raid.**
  The window stack lives in an autoload, so it outlived the scene that
  pushed to it: pause → "main menu" → deploy again left the stack
  occupied, and the new raid read *no input at all* — ESC and M were
  dead too, so there was no way out short of killing the process. Every
  scene root now starts from a cleared stack.
- **Dying aboard the freight was an unrecoverable softlock.** `riding`
  was set on boarding and cleared by nothing anywhere in the codebase,
  and `respawn()` didn't reset it — so after the death fade the player
  was teleported back onto the departed train every frame, invisible,
  collisionless, with input never read. Respawn now clears the ride,
  visibility, collision and floor lift.
- **The first night freight arrived 580 seconds in, not 20.** The cycle
  clock was seeded with its sign inverted, which means the v0.4.8 note
  claiming "the first freight arrives 20 seconds in" was flatly wrong.
- **Extracting worked underneath an open map.** The map deliberately
  doesn't pause the tree, so standing in the landing zone and pressing M
  still ran the countdown and extracted you — which then poisoned the
  window stack per the first bug. Extraction now stands down while any
  window is open, and the green counter no longer sits over the death
  fade.
- **The sniper stand-down was incomplete** — the fix v0.4.8 claimed.
  Already-queued rounds in a staggered volley still spawned and could
  kill you up to 0.84 s after paying the warden or boarding the train.
  Queued rounds are now dropped and `_spawn_round` respects the flag.

### Fixed — world
- **The district's outer rim was bare.** `EDGE_FOREST`, the content
  margin, was left at 85 when v0.4.4 moved the barricade ring to 66, so
  lamps, lone trees, road vehicles, puddles and scatter all stopped 19
  cells short of the barricades.
- **Half the street scatter was missing**: heaps incremented the placed
  counter twice, so the loop hit its budget of 210 pieces early.

### Also
- Rain and the engine bed kept playing under the main menu after
  quitting a raid, and could carry into the next one — world audio is
  silenced when the raid scene exits.
- Timers owned by the SceneTree outlived their scene: the death sequence
  resumed on a freed instance, mara's radio could speak from a freed
  node, and a lightning strike could clap thunder over the main menu.
  All three are guarded.

### Not fixed — logged with reproduction steps
The audits found more than one release should absorb: the helicopter
leaking if you die mid-lift, `stood_down` never resetting (pay the toll,
walk back in, and the whole ring stays blind for the raid), headlights
burning on a car you died in, per-frame `Label.text` churn on three
countdowns, the freight re-parsing the 137 KB manifest during the deploy
tail, `_place_toll_gate` not checking occupancy, `_plan_safehouse`
running before the POI rects it tests against exist, and ~10 genuinely
dead functions and sprite families. All recorded.

## [0.4.9] — 2026-08-01

### Performance
- **Killed the deploy stall** (user: "when you load into transit, it goes
  to like 130 fps for a second"). Measured with `--perf-deploy` instead
  of guessed at: the worst frame was **233.5 ms**, not the ~30 ms scene
  swap the notes claimed. The cause was `preview.png` — a **512 KB dev
  contact sheet**, by far the largest file in `art/gen`, generated by the
  art tool and **referenced by nothing in the game**. `_prewarm_textures`
  loads *every* png in that folder, so the deploy paid to decode and
  upload it every single raid. It now writes to `docs/` instead, where
  Godot never imports it.
  **Before:** build 1.34 s, worst frames 233.5 / 28.8 / 19.1 / 18.0 ms.
  **After:** build 1.11 s, worst frames 29.0 / 18.5 / 6.4 / 5.9 ms.
  The remaining 29 ms is the known menu→game scene swap.

## [0.4.8] — 2026-08-01

### Fixed
- **The snipers kept shooting while you rode the freight out** (user
  report). Boarding now stands the edge guard down, the same way paying
  the toll warden does — riding out past the wire is a legitimate exit,
  not a death sentence. You earned it by catching the train.

### Changed
- **The first freight arrives 20 seconds in**, not 45 — the old wait read
  as the train being late (user). The five-minute cycle after that is
  unchanged.
- **It carries its own light**, because it runs at night: a headlamp
  throwing down the rails ahead of it and a warm spill out of the cab
  windows.
- **Steam breathes off the stack** — slow while she stands in the yard,
  much harder once she's pulling away.
- **mara's radio is small and upper-centre** instead of a large panel in
  the top-left corner, which pulled the eye off the world every time she
  keyed up (user).

## [0.4.7] — 2026-08-01

### Fixed
- **The locomotive was missing its end face** (user: "the extract train is
  missing parts, its like that old car bug we had awhile ago" — and it
  was exactly that bug). The cab end had no full-width wall across the
  body's iso width axis, so the engine looked sawn off. It now carries a
  proper end wall spanning the same ROOF_DEPTH the roof plane does, with
  a lit top rim, a sill, red marker lamps, a cab window, and the side's
  last column wrapped into the corner. The nose end got its wrap and
  coupler plate rebuilt on the same convention.
  **The lesson from the car saga holds: an end drawn as a stub running
  LENGTHWISE off a corner instead of a wall across the width axis always
  reads as missing.** Check every new vehicle against it.

## [0.4.6] — 2026-08-01

### Added
- **A facing cone on the map marker** (user: "a circle i cant really
  tell"). The "me" marker now draws a cone pointing the way the raider
  is looking, so the map tells you which direction to walk instead of
  only where you stand. New `Player.facing_angle()` returns the screen
  direction — the sprite sheet's rows run E,SE,S,SW,W,NW,N,NE, exactly
  45° apart from east, and on an iso map screen direction *is* the
  direction you'd walk. While driving it follows the car's heading.

## [0.4.5] — 2026-08-01

### Changed
- **Furniture variety** (user: "these have visual repetition... make sure
  everything in my game doesnt have repetition"). An audit of every prop
  family's variant count found the real culprit: **all seven interior
  furniture pieces were single sprites** — every house in the district
  had the identical table, chair, bookshelf, cabinet, couch, tv stand
  and bed. Each now bakes 4–5 copies through the v0.3.12
  `clutter_variants` path, so every instance carries its own grime
  patches and its own slight lean. Furniture leans *a little* — a
  cabinet tipped like a crate reads as falling over, not lived-in.
- **Racks** went 4 → 7 variants (the user screenshotted two identical
  ones standing side by side in a yard).
- Every one of those call sites now uses `_pick_variant_varied()`, so
  the same version can never appear twice in a row — which is the repeat
  the eye actually catches.

### Known / queued
- Remaining 2-variant families (benches, dumpsters, shelters, vending,
  newsboxes, forklifts, planters, swings) and the singleton crane and
  sandbox still need the same treatment.
- The deeper fix is parameterising the builders so variants differ in
  SHAPE and size, not only in wear and lean.

## [0.4.4] — 2026-08-01

### Changed
- **The district is bigger** (user: "make the map a bit bigger, so the
  warehouse can be better, its too small now"). `BARRIER_INSET` 78 → 66,
  taking the playable district from roughly 100 cells across to ~124.
  Every zone block gains room — the scrapyard block went 20×14 → 28×22 —
  and the scrapyard hall's size ladder now starts at 16×11 instead of
  12×8, so it builds as a proper warehouse instead of shrinking to
  squeeze past the rails.
- **One railway, the whole way across** (user: "it should be the same
  track all the way across the map, same look, the wood planks with
  steel beam... make sure the railroad tracks are all connected").
  **Reverted the worn/overgrown track variants added in v0.4.1** — the
  stretches of rusted rail with rotted ties and weed-grown ballast broke
  the line into what read as separate, disconnected bits of railway.
  There is one rail tile again: wooden ties under steel rail, identical
  tile to tile, continuous end to end. The trackside dressing from
  v0.4.1 stays — poles, signals and lineside junk were never the
  problem, the track surface was.

## [0.4.3] — 2026-08-01

### Fixed
- **v0.4.2 shipped with a failing smoke test.** The commands were
  chained unconditionally, so a red build reached main. Two genuine
  problems were underneath it:
  - **The smoke test asserted the wrong thing.** It drove whichever car
    came first in the group and demanded 40 px of travel. Moving the
    scrapyard hall shifted the layout, that car ended up parked without
    room, and the entire build failed for it. It now tries all four
    directions and fails only if the car can't move in *any* of them —
    asserting that driving works, not that one car is parked well.
  - **Clutter pile satellites had no occupancy check** (a v0.3.12 bug of
    mine): they could land in roads, in doorways, and on top of parked
    cars. They now test the cell like every other placement does.

## [0.4.2] — 2026-08-01

### Fixed
- **The scrapyard warehouse came back** (user: "thats where the warehouse
  should have been, now you removed it again"). v0.3.14 stopped the hall
  being built on top of the railway by **skipping it** when no rail-free
  footprint fitted — which silently reintroduced the original v0.3.5
  bug, racks and crates standing in the open with no building. Wrong
  trade. The hall is guaranteed again: it now searches the block at
  progressively smaller footprints (12×8 down to 6×4) until one fits
  clear of track, ballast and crossings. A smaller hall is a hall; no
  hall is the old bug.

## [0.4.1] — 2026-08-01

### Changed
- **The rail line reads as a railway** (user: "it does look a bit odd the
  track being all a straight line"). Real mainlines *are* straight, so
  the fix isn't to bend it — it's that a straight line reads as a drawn
  line until something repeats ALONGSIDE it at human intervals:
  - **Telegraph poles** march the whole run at uneven spacing (7–10
    cells, never a metronome) and occasionally swap sides of the track.
    Four variants with different heights and leans; one in three has
    lost a crossarm.
  - **Colour-light signals** stand where they'd really stand — on the
    approach to each level crossing and at the yard throat. Most are
    dead; one still shows an aspect.
  - **Trackside junk** piles along the ballast using the v0.3.12 clutter
    piling, because that's where a railway collects things.
  - **The track wears in STRETCHES, not per tile**: runs of overgrown
    track with grass through the ballast and up between the rails, runs
    of rusted rail with the odd tie rotted away, then clean again. A
    per-cell roll would read as noise; a run reads as neglect.

## [0.4.0] — 2026-08-01

### Added
- **Extract 3: THE NIGHT FREIGHT** (user design, including the timing).
  A locomotive hauling two cars slides into the trainyard **every five
  real minutes, stands for exactly one, and leaves whether you're aboard
  or not**. Miss it and you wait five minutes or walk. `press f to get
  on the train` while it stands; boarding welds you aboard (hidden, out
  of the input loop, camera riding with it), then **"departing in
  10…0"**, then it pulls away slowly, builds speed down the rails and
  off the map into the debrief.
- **The locomotive** is drawn to be unmistakable next to the dead stock:
  longer than a boxcar, taller at the cab, charcoal with an amber
  stripe, warm lit cab windows, a burning headlight and a stack.
- **mara on the radio** (user request). A reusable `Radio` panel — the
  M2 walk-in tutorial is entirely her voice, so it was worth building
  properly. She calls the freight in twenty seconds out, tells you when
  it's down to twenty-five, tells you to sit tight once you're aboard,
  and tells you off when it rolls without you. Calls queue rather than
  clipping each other, because a dispatcher waits for the channel.
- **It sounds like a radio**: new synthesized mic **squelch** on key-up
  and key-down (band-limited hiss, not white noise) either side of every
  transmission, plus a long two-tone **freight horn** heard across the
  district. *There is no voice acting and there won't be by accident —
  bespoke lines can't be sourced from a sound library. The squelch and
  the writing do the performance.*
- Harness: `--freight` puts the train in the yard immediately instead of
  waiting out the real-time cycle.

## [0.3.14] — 2026-08-01

### Fixed
- **Falling leaves, both halves of it** (user: "a tree that doesnt have
  any leaves falling down, its the only tree on the screen", then "its
  like getting spammed on that tree... this other tree is lonely").
  Two separate faults, and the flat 50% shed roll caused the first:
  - **Which trees shed.** A lone oak could lose the coin flip and stand
    inert forever, while a **pine or a bare dead snag could win it** and
    drop broadleaf leaves out of a conifer. Now every broadleaf tree
    sheds (oaks, the autumn grove, and bushes) and conifers and dead
    snags never do. More shedders costs nothing — the environment's
    leaf timer caps the overall fall rate, so this buys variety in
    where leaves come from, not more leaves.
  - **Which tree gets picked.** The spawner chose at random from the
    short list of trees near the camera, so with only a couple in view
    it dumped everything on one of them. It now walks a shuffled cursor
    through that list, giving every visible tree its turn.
- **A building could stand on the railway** (user screenshot). The
  scrapyard hall's fallback placement only dodged the main rail row, so
  a siding could still run under it. It now searches the whole block for
  a rail-free footprint (checking track, ballast and crossings), and
  skips the hall entirely rather than dropping a warehouse on the line.

## [0.3.13] — 2026-08-01

### Added
- **Extract 2: THE TOLL GATE** (user design). Where the middle road
  breaches the wire on the south side there is now a booth with a lit
  serving window, a warden visible inside it, and a striped boom lying
  across the asphalt. Pull up **in a car** and press F — F at the wheel
  talks to him instead of getting out, because the whole point of the
  gate is that you drive to it — or walk up; either way the prompt
  offers it, and the prompt is the permission (v0.3.11's rule).
- **His window.** A portrait panel with his face, whatever he's decided
  to tell you, and three answers: a **reply button that shows the line
  you'd actually say** and changes every time, **pay 30 to extract**,
  and **back away**. He has 26 lines and 14 replies, never repeats
  twice running, and **never runs out** — he will talk about the eleven
  gates he's worked, his brother on the harbor gate, the raider who
  cried at this window, and how much he's made off people like you. He
  never says what the wardens are actually FOR (LORE.md hard rule 3).
- **Paying opens the crossing**: the boom goes up, the edge snipers
  **stand down** (`EdgeGuard.stood_down`), and the toll extract arms
  beyond the wire — drive out down the road and the green counter runs,
  then the debrief. `Raid.money` is a stub (120 a raid) until the stash
  and the economy land in M4; the pay button disables and shows what
  you have when you're short.
- New art: the toll booth (lit window, counter, the man inside), the
  boom in raised and lowered states, and the warden's 48×48 portrait —
  peaked cap with a brass badge, a scar through one eyebrow, and a
  mouth that has said no ten thousand times.
- The toll gate and the landing zone are both named POIs on the map now.
- Harness: `--toll` opens his window for review.

## [0.3.12] — 2026-08-01

### Changed
- **Clutter variation** (user ask: break visual repetition without adding
  procedural generation — the layout stays fixed). Three pieces:
  - **Baked lean, never runtime rotation.** `bake_lean()` shears a prop's
    rows by their height above a pivot, so a "tipped" crate is a
    genuinely different sprite. Runtime rotation is still banned — it
    resamples off the pixel grid and shimmers while the camera scrolls,
    which is why this is done at generation time.
  - **Per-instance wear.** `bake_wear()` ages each copy with a few small
    solid patches of grime (the same patch logic the tiles use — no
    single-pixel dot noise). `clutter_variants()` ties it together:
    every copy gets its own build seed, its own lean and its own wear.
    Crates went 6 → 10 variants, tires 4 → 7, pallets 3 → 6, rubble
    4 → 7 — all visibly different objects, not one object stamped N times.
  - **Asymmetrical piling.** New `_place_pile()` drops an anchor piece
    then satellites that thin out and drift further along the pile's own
    lean, so a heap has a heavy middle and stragglers spilling off one
    side. `_scatter_around()` does loose mixed-family debris with a bias
    so it never reads as a halo. `_clutter_offset()` jitters within a
    cell on WHOLE world pixels (static props must stay on the grid), and
    `_pick_variant_varied()` never hands out the same variant twice
    running — a repeat side by side is what the eye catches first.
  - Applied to the street scatter (a quarter of barrels/tires/rubble now
    land as heaps) and the scrapyard (over half of it does — it is where
    things get dumped). Perf held: 240 avg, worst 4.52 ms.

### Fixed
- **README was out of date**: it still promised "a fresh layout generates
  on every deploy", a 320×320 district, a 20-minute day and a "dead,
  overrun" world. Rewritten for what the game actually is now — one
  fixed learnable district and why it's fixed, the POIs in it, working
  extraction, driveable cars, second stories, the map key, the real
  controls, and the human-only rule.

## [0.3.11] — 2026-08-01

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

## [0.3.10] — 2026-08-01

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

## [0.3.9] — 2026-08-01

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

## [0.3.8] — 2026-08-01

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

## [0.3.7] — 2026-08-01

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
  the steering inertia from v0.3.6 — the car carves toward your input
  and turns tighten as you slow — plus iso squash on the vertical so a
  car crossing north-south covers ground at the rate the tiles imply.
  **E** headlights, **F** in and out. Controls card rewritten to match.
- Smoke harness drives via `auto_drive` now (headless sends no input)
  and asserts both halves of the new rule: the engine must be running
  after entry and silent after stepping out.

Perf: 240 avg, worst 4.72 ms, ~5.3k nodes. SMOKE PASS.

## [0.3.6] — 2026-08-01

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
  been forever). The school stood nearly empty since v0.3.2: its desks
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
  v0.2.7; these two were the stragglers. Circle anything else.)
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

## [0.3.5] — 2026-08-01

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

## [0.3.4] — 2026-08-01

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

## [0.3.3] — 2026-08-01

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

## [0.3.2] — 2026-08-01

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

## [0.3.1] — 2026-08-01

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

## [0.3.0] — 2026-08-01

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

## [0.2.14] — 2026-08-01

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

## [0.2.13] — 2026-08-01

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

## [0.2.12] — 2026-08-01

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

## [0.2.11] — 2026-08-01

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

## [0.2.10] — 2026-08-01

### Changed
- **Car end-cap colors rolled back to the original dark look** (user call —
  the brightened caps from the visibility fix read worse). The v0.2.8
  geometry fixes stayed: raked-ramp fills, smaller wheel arches, the
  attached broken-car door.

## [0.2.9] — 2026-08-01

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

## [0.2.8] — 2026-08-01

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

## [0.2.7] — 2026-08-01

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

## [0.2.6] — 2026-08-01

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

## [0.2.5] — 2026-08-01

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

## [0.2.4] — 2026-08-01

### Added
- **Prone** on Z (rebindable): a full 8-direction crawl sheet (pack on the
  back, boot soles when facing away, per-direction head orientation, 6-frame
  crawl cycle). Slower than crouch (0.32x vs 0.55x); Z toggles, and any crouch
  input stands you back up out of prone. Covered by the smoke test.

### Changed
- The door prompt ("press f to open/close") floats pinned above the door
  itself instead of sitting at the bottom of the screen.

## [0.2.3] — 2026-08-01

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

## [0.2.2] — 2026-08-01

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

## [0.2.1] — 2026-08-01

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

## [0.2.0] — 2026-07-31

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
## [0.1.14] — 2026-07-31

**Versioning from here on:** patch bumps (0.6.x) for polish and fix batches;
the minor only moves when a MILESTONE lands (0.7 gunplay, 0.8 enemies,
0.9 the raid loop). 1.0 = the complete v1 game from the design doc.

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
## [0.1.13] — 2026-07-31

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
## [0.1.12] — 2026-07-31

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
## [0.1.11] — 2026-07-31

### Changed
- Buttons are deep burgundy now — clearly visible over every menu backdrop
  (the old gray-blue blended into the darker scenes).
- The changelog link is a dim flat footer link, matching the version label.
- In-game changelog entries expanded with more detail per version.

## [0.1.10] — 2026-07-31

### Added
- In-game changelog viewer on the main menu (bottom-right, above the version):
  every version since the first build, summarized in plain language.

### Fixed
- Returning to the menu from a raid caused a 1–2 frame hitch (backdrop images
  re-decoding + particle pre-simulation). Backdrops are now preloaded for the
  process lifetime and only the first scene pre-warms its particles.

## [0.1.9] — 2026-07-31

### Changed
- Roof rebuilt as modular pieces placed by explicit formula: one tile per
  interior cell, fascia modules on south/east eaves, lit rims on north/west.
- Wall coping on north/west walls now extends under the roof (mirrored
  variants), and corner posts are exactly wall height so their caps close the
  fascia line at the corners instead of poking through the roof.

## [0.1.8] — 2026-07-31

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

## [0.1.7] — 2026-07-31

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

## [0.1.6] — 2026-07-31

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

## [0.1.5] — 2026-07-31

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

## [0.1.4] — 2026-07-31

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

## [0.1.3] — 2026-07-31

### Fixed
- **High-refresh judder:** movement and camera now update every rendered frame
  instead of at the 60 Hz physics tick. On high-refresh monitors (e.g. 240 Hz)
  the old behavior read as constant stutter.
- **Motion blur/shimmer while walking:** the camera is hard-locked to whole
  pixels every frame, so the low-res screen never resamples mid-scroll.

### Changed
- Game now launches fullscreen (borderless) by default, integer-scaled.

## [0.1.2] — 2026-07-31

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


