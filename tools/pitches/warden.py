"""the warden's window — night at the toll booth, he is looking straight back at you.

BACKDROP PITCH - static scene only, no living layer yet. Unwired: nothing
imports this and gen_art.py never emits it. If the user picks this pitch it
gets promoted into gen_art.py proper; if not, this file is deleted.

WHAT IS DELIBERATE HERE (do not "fix" these later):

* THE KEY LIGHT COMES FROM BELOW. The desk lamp on his ledger is the only
  light on his face. Every other asset in this project is lit from the
  north-west; inverting it is the whole point of the pitch. So the tops of
  things are DARK and the undersides are LIT — cap crown dark, chin bright,
  brow in shadow, the peak of the cap blacking out his eyes.
* HE IS ASYMMETRIC ON PURPOSE. He leans on his left elbow, so that shoulder
  sits ~6px higher than the other, and the left corner of his mouth is a
  pixel lower than the right. Rule 4's symmetry law is about the player
  sprite; the den's hunched kettle is the precedent for a posed figure.
* THE BASE IS BAKED *LIT* — the cold shift-light rim on the window's top and
  left rails, and the 3c5e8b rim on his cap crown, are painted in. The brief
  contradicted itself here (composition said "baked lit", living layer said
  "baked unlit"). Resolved toward lit, because as a still image the cold rim
  is what separates a dark cap from a dark interior wall. If the failing
  ballast blink ever gets built it needs its own overlay AND this base
  re-baked without those rims.
* ROOM LEFT FOR THE LIVING LAYER (none of it built here): the lamp's warm
  pool is baked as a SOLID BANDED wash only, exactly like the den's candle
  halo, so a soft-alpha breathing glow can sit on top; the fuse box behind
  the glass is baked with no lit LED; the floodlight's ground pool is baked
  flat so a slow cold overlay can swim on it; nothing occupies the moth's
  approach lane.

CRITIC CORRECTIONS APPLIED:
* the razor coil no longer enters the button band. The whole wire line was
  dropped ~38px (top rail y 418-427, horizon y 428) and the coil sits above
  the rail at y ~407-418 — a 17px clearance under y=390 at every x in the
  band. Its 577277 top lip and its barbs are drawn ONLY for x >= 500, and
  the barbs are 4-6px solid triangles, never the 1-2px specks a far coil
  would degenerate into.
* the receding mesh dies at x < 480 (solid slabs past that), so no cell ever
  falls below 8px.
* the lamp and the ledger no longer overlap: lamp x 604-646, ledger x 650-714,
  hand x 712-754. Three objects, three lanes, no guessed occlusion.

WHAT THE RENDER CHANGED (six passes; every one of these looked fine in code
and wrong in the picture, so do not "simplify" them back):
* the interior wall is warm ALL THE WAY UP. Banding its top cold and letting
  the lamp's wash take over below put a hard warm/cold meeting line sweeping
  across the whole window that read as a horizon, not as light.
* his cast shadow is HEAD AND CAP ONLY. Projecting the shoulders too threw a
  pair of brown wings across the interior that read as a cloak, and it
  darkened exactly the strip of wall his dark tunic silhouettes against.
* the shadow steps each pixel DOWN ITS OWN LADDER instead of stamping a fixed
  brown; a warm 341c27 over the cold upper wall is a different object, not a
  shadow.
* the cap flares WIDE and sits SHORT. Two earlier cuts were tall and
  near-vertical and read as a top hat.
* the hand is a cupped palm with knuckle creases. Drawn as four tall rounded
  fingers standing above the palm it read as a row of bottles, then as a bun.
* the boom, the road spill and the sign are all a full step lower than first
  written. Each in turn became the brightest thing in the frame and beat the
  face, which is the one thing this composition cannot afford.

REVISION PASS (the user has now SEEN this one and likes it; twelve more
renders). Four defects, four fixes, and what each one taught:

1. THE LEFT THIRD WAS EMPTY — the user's note as well as mine. It now carries
   three new things, all near-silhouette so none of them can beat the booth:
   `_skyline` (the district past the wire, standing against the horizon
   glow), `_pole` (a distribution pole and its three spans, which is also why
   there is anything at all in the upper-left sky), and `_queue` (the van
   that never paid, nose past the boom, driver's door open). The sky gained a
   second, lower cloud bar over the left only.
2. THE ROAD SPILL read as a geometric orange dagger. Rewritten as `_spill`:
   light has no edge of its own, so the wash is ragged, dies unevenly instead
   of tapering to a point, and every bright value in it now belongs to a
   piece of ROAD — standing water, a rake of wet streaks, a repair patch, a
   manhole, cracks — never to the wash itself.
3. THE TALLIES were a field of scratches. Fifteen groups became seven, with
   real empty wall between them; what makes a tally read as a count is the
   space around each five, not the strokes. **THAT PASS IS SUPERSEDED — see
   the canon rewrite below; do not use its "fewer and more varied" note as
   guidance, it is the opposite of what this man's wall wants.**

CANON PASS (2026-08-02). The tally is now a FIXED NUMBER, not a texture.

* EXACTLY 83 MARKS — sixteen gates of five and three loose. LORE.md 7a, and
  the same number is on the den's wall. `_tallies` builds an explicit plan,
  `_gate` returns what it actually DREW, and an assert crashes the module if
  the two ever disagree.
* ALL 83 ARE ON THE WARM TIMBER. User's words: "can you make the tallies on
  the wardens screen go on the wood, not the gray thing, looks a bit off".
  Nothing is chalked behind the glass, on the rollered grey panel or over the
  fuse box any more.
* HIS HANDWRITING IS NEAT — one ruling shared by both panels, a 4px upright
  pitch and one fixed strike angle, because his own line in
  scripts/toll_dialog.gd is "better handwriting". The jitter is one pixel and
  no more.
* `_burn_old_stream` exists so the shared rng cost did not move. Every
  function painted after the interior draws from that same stream.
4. THE BOOTH'S BOTTOM-RIGHT QUARTER had a vent, a plinth and a conduit that
   ran past to nowhere. `_service` gives all three one reason: the vent is
   the generator's air, the conduit dies in an isolator, the isolator feeds
   the generator, and the can on the plinth is what the generator drinks.

Three traps this pass fell into, all of which looked right in code:
* a wobble added to break a smooth band edge must be TINY and SHORT. The
  first cut at `face_level`'s bottom used amplitude 0.42 where the gradient
  is 0.007/px, and simply replaced one smooth arch with three bigger ones.
* a falloff spent as `lv - int(t * 1.9)` quantises on whole values of t and
  draws hard VERTICAL seams down the beam. Fold distance into the field
  BEFORE the threshold.
* a skyline that rolls "tall" independently per block puts three talls side
  by side, each grows its own thin aerial, and the roofline becomes a comb.
  `not was_tall` is what stops it.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gen_art import Canvas, C, SCENE_W, SCENE_H, blob

# ----------------------------------------------------------------- ramps ----
# two value ladders. bump() walks a colour up or down its own ladder, which is
# how a seam highlight / batten / groove stays correct wherever it lands.
COLD = ("090a14", "10141f", "151d28", "202e37", "394a50",
        "577277", "819796", "a8b5b2", "c7cfcc", "ebede9")
WARM = ("241527", "341c27", "602c2c", "884b2b", "ad7757",
        "c09473", "d7b594", "e7d5b3")
SKIN = ("341c27", "4d2b32", "7a4841", "ad7757", "c09473", "d7b594", "e7d5b3")

_IDX: dict = {}
for _i, _n in enumerate(COLD):
    _IDX[C(_n)] = (COLD, _i)
for _i, _n in enumerate(WARM):
    _IDX.setdefault(C(_n), (WARM, _i))

# a third ladder, for the tarmac under the window's light. It has to bridge
# the road's cold darks and the lamp's warms in ONE run, because a pixel in
# the spill gets stepped up and down by ruts, cracks and standing water and
# must never jump ramp mid-step.
SPILL = ("090a14", "241527", "341c27", "4d2b32", "602c2c", "884b2b")
_SP = {C(_n): _i for _i, _n in enumerate(SPILL)}


def cold(i):
    return C(COLD[max(0, min(len(COLD) - 1, i))])


def warm(i):
    return C(WARM[max(0, min(len(WARM) - 1, i))])


def skin(i):
    return C(SKIN[max(0, min(len(SKIN) - 1, i))])


def bump(col, n):
    e = _IDX.get(col)
    if e is None:
        return col
    ramp, i = e
    return C(ramp[max(0, min(len(ramp) - 1, i + n))])


def lit(col, n):
    """step a pixel along the SPILL ladder if it is on it, otherwise fall
    back to its own ramp — so one rut can run out of the light and into the
    dry tarmac without changing hue at the boundary."""
    i = _SP.get(col)
    if i is None:
        return bump(col, n)
    return C(SPILL[max(0, min(len(SPILL) - 1, i + n))])


# ------------------------------------------------------------- geometry ----
HOR = 434            # the horizon / far treeline base
ROOF_T = 118         # booth roof slab top
ROOF_B = 134
BOOTH_L = 568        # booth front face, left edge
BOOTH_R = 892        # front face meets the return face here
OPEN_L, OPEN_R = 612, 856     # window opening
OPEN_T, OPEN_B = 196, 330
PANE_X = 772         # sliding pane's leading edge (pushed right)
CX = 676             # his centre line
CNT_Y = 330          # counter top, far edge


def wob(x, a1, p1, ph1, a2, p2, ph2):
    """two sines of different period — a long seam must never read as a
    stripe, and one sine still reads as a stripe."""
    return a1 * math.sin(x / p1 + ph1) + a2 * math.sin(x / p2 + ph2)


def rail_y(x: float) -> float:
    return 416.0 + (BOOTH_L - x) / 528.0 * 11.0


def wire_base(x: float) -> float:
    return 449.0 - (BOOTH_L - x) / 528.0 * 13.0


def road_top(x: int) -> int:
    return int(453 + wob(x, 3.0, 61.0, 1.2, 2.0, 17.0, 0.5))


def boom_y(x: float) -> float:
    return 414.0 + (868.0 - x) / 868.0 * 78.0


def face_level(x: int, y: int) -> int:
    """the booth's front face, cel-lit by the shift lamp over the window.
    Keeps the big dark slab from being one flat value and — more usefully —
    lets the face fall to near-black at its left edge so the booth's
    silhouette separates from the 172038 sky behind it."""
    d = ((x - 706) ** 2 + ((y - 168) * 1.25) ** 2) ** 0.5
    lv = max(0.0, 1.0 - d / 470.0) * 2.6 + 0.55
    lv += 0.30 * math.sin(x / 43.0) + 0.20 * math.sin(y / 31.0)
    # THE FALLOFF IS AN ELLIPSE, and down at the bottom of the face its last
    # band edge crossed the wall as one smooth arch that read as a MOUND
    # standing behind the plinth. Short-period wobble, faded in only below
    # y 400 so the lit half of the face is untouched, tears that edge up.
    # The gradient down here is only ~0.007 lv per pixel of y, so the wobble
    # has to be TINY and SHORT — a first cut used 0.42 and 0.26 and simply
    # replaced the arch with three enormous smooth lobes, which is the same
    # defect at a different wavelength.
    if y > 400:
        k = min(1.0, (y - 400) / 44.0)
        lv += k * (0.045 * math.sin(x / 5.3 + 1.9)
                   + 0.034 * math.sin(x / 11.7 + 0.6)
                   + 0.022 * math.sin(y / 6.0 + x / 3.0))
    return int(lv)


# ==================================================================== sky ====
def _sky(c: Canvas, rng: random.Random) -> None:
    # three solid bands, both seams wobbled by two sines. Both are placed far
    # outside the button band (y 290-390) — the lower seam tops out at y 259.
    for x in range(SCENE_W):
        s1 = int(118 + wob(x, 5.0, 83.0, 0.7, 3.0, 29.0, 2.1))
        s2 = int(252 + wob(x, 4.0, 97.0, 1.9, 3.0, 41.0, 0.4))
        for y in range(0, HOR):
            if y < s1:
                col = C("090a14")
            elif y < s2:
                col = C("10141f")
            else:
                col = C("172038")
            c.set(x, y, col)
    # one long cloud bar high in the middle band, so the sky over the buttons
    # is not a dead field — it stops at y<=202, nowhere near the band.
    for x in range(0, 660):
        t1 = int(170 + wob(x, 6.0, 71.0, 2.4, 4.0, 23.0, 1.1))
        t2 = t1 + 13 + int(5 * math.sin(x / 57.0 + 0.3))
        for y in range(t1, t2):
            c.set(x, y, C("151d28"))
        c.set(x, t1, C("172038"))
    # a second, LOWER bar over the left only, because the 172038 band between
    # the cloud above and the skyline below was 150px of one flat colour. It
    # is a different animal from the bar above: shorter, torn along its
    # underside, and DARKER than what it sits on rather than lighter. It stops
    # at x 330 and y 280 — the button band starts at x 400, y 290.
    for x in range(0, 332):
        t1 = int(258 + wob(x, 4.0, 59.0, 1.3, 2.0, 19.0, 0.8))
        t2 = t1 + 9 + int(6.0 * math.sin(x / 31.0 + 2.0)
                          + 2.0 * math.sin(x / 7.0))
        for y in range(t1, min(280, t2)):
            c.set(x, y, C("151d28"))
        c.set(x, t1, C("172038"))
    for (sx, sy) in ((112, 44), (238, 78), (604, 36)):
        c.set(sx, sy, C("577277"))


# ============================================================== zenith ======
# THESE TWO ARE PAINTED LAST, NOT HERE. They live next to _sky because that is
# what they belong to, but paint() calls them at the very end of the run —
# every function in this file draws from ONE shared rng stream, so inserting a
# consumer in the middle would re-roll the whole picture below it. Called last,
# they cost the existing stream nothing. See _burn_old_stream for the same
# problem solved the other way round.
#
# THE DEFECT THEY FIX (user, 2026-08-02): "why is there like some black border
# of the whole screen at the top of all of the paintings, it seems a bit odd".
# Rows 0-109 of this scene were flat 090a14 edge to edge — a slab, which reads
# as a letterbox border rather than as sky. The two SHIPPED backdrops never do
# this: the drain's ceiling is just as dark but its manhole throat and its
# rolled beams run the full height of it, and the den keeps structure in its
# top rows too. Dark is correct here; FEATURELESS is the defect.
#
# THE BUDGET IS THE POINT. This must stay the darkest region of the frame, so
# the entire allowance is ONE step of the cold ladder (090a14 -> 10141f, the
# same step the sky's own lower seams already use) plus a short, broken 151d28
# lip on a few undersides. Nothing here is a light source and nothing is
# allowed a third step. Measured: top-60-row mean luminance 10.84 -> 12.24.
ZEN_LIMIT = 117        # nothing below this line may be touched. The booth roof
                       # slab starts at ROOF_T 118 and the sky's first seam
                       # never rises above y 110, so everything under this is
                       # the signed-off composition.


def _strata(c: Canvas, rng: random.Random) -> None:
    """THIN CLOUD LYING ACROSS THE ZENITH, lit from beneath by the same town
    glow that is already on the horizon.

    AERIAL PERSPECTIVE, IN THE SKY: the low bars are the near ones, so they
    are thinner, more torn, and they are the only ones that get the lit lip.
    The high ones are wider, softer edged and carry no light at all. That
    grading is also what stops four bars at four heights reading as a set of
    stripes — they differ in thickness, in tear, in length and in whether
    they are lit, not merely in y.

    Each bar's TOP AND BOTTOM EDGES ARE INDEPENDENT — two sines apiece plus
    its own bounded random walk. A bar of constant thickness is a ruler. And
    each one dies by losing thickness at both ends rather than by stopping,
    because a cloud with a cut end is a painted rectangle.
    """
    BLACK, STEP, LIP = C("090a14"), C("10141f"), C("151d28")

    def put(x, y, col):
        # the containment guard, and it is deliberately paranoid: a pixel is
        # written ONLY if it is still the flat zenith slab and ONLY above the
        # roof line. It cannot touch the sky's first seam, the three stars, or
        # anything else in the frame no matter what the maths does.
        if 0 <= x < SCENE_W and 0 <= y <= ZEN_LIMIT and c.get(x, y) == BLACK:
            c.set(x, y, col)

    def lip(x, y):
        if 0 <= x < SCENE_W and 0 <= y <= ZEN_LIMIT and c.get(x, y) == STEP:
            c.set(x, y, LIP)

    def bar(x0, x1, mid, half, s1, p1, s2, p2, lit_to):
        wt = wb = 0.0
        run = gap = 0
        for x in range(x0, x1):
            # the walk is what tears the edge; the sines are what stop the
            # tear from reading as noise. Both, or it is one or the other.
            wt = max(-2.0, min(2.0, wt + rng.uniform(-0.55, 0.55)))
            wb = max(-2.0, min(2.0, wb + rng.uniform(-0.55, 0.55)))
            u = (x - x0) / float(x1 - x0)
            taper = min(1.0, min(u, 1.0 - u) * 5.0 + 0.02)
            h = half * taper + s1 * math.sin(x / p1 + 0.7)
            if h < 0.5:
                continue
            m = mid + s2 * math.sin(x / p2 + 2.3)
            top = int(m - h + wt)
            bot = int(m + h + wb)
            for y in range(top, bot + 1):
                put(x, y, STEP)
            # the lit lip. Broken into rolled runs with rolled gaps, and only
            # over the left of the frame, because the glow it is lit by lives
            # on the horizon out at x 0-612. A continuous lip under a whole
            # bar is a drawn outline, not light landing on something.
            if x > lit_to:
                continue
            if gap > 0:
                gap -= 1
                continue
            if run > 0:
                run -= 1
                lip(x, bot)
                if rng.random() < 0.22:
                    lip(x, bot - 1)
                continue
            if rng.random() < 0.055:
                run = rng.randint(4, 17)
            else:
                gap = rng.randint(2, 9)

    # five bars, no two alike in length, thickness, tear or lighting, and
    # nowhere near a common pitch. Two of them overlap in x so the layer reads
    # as depth rather than as a ladder.
    #
    # THE TOP ONE IS CLIPPED BY THE FRAME ON PURPOSE. A first pass put the
    # highest bar at y 27 and left rows 0-18 flat — which is the original
    # defect, just eighteen rows tall instead of a hundred. A sky that is cut
    # off by the top edge mid-cloud says the frame is a crop of somewhere
    # bigger; a sky that stops short of it says the frame is a stage.
    bar(196, 902, 4.0, 2.0, 0.9, 89.0, 3.4, 141.0, -1)      # clipped, faintest
    bar(438, 726, 16.0, 1.5, 0.7, 31.0, 1.1, 53.0, -1)      # a torn-off scrap
    bar(52, 700, 30.0, 4.0, 1.5, 71.0, 2.6, 113.0, -1)      # high, wide, dead
    bar(0, 306, 53.0, 3.0, 1.1, 43.0, 1.9, 79.0, 240)       # short, left
    bar(372, 884, 68.0, 3.2, 1.3, 59.0, 2.2, 97.0, 560)     # long, right
    bar(148, 646, 94.0, 2.6, 0.9, 37.0, 1.6, 67.0, 610)     # low, near, lit


def _mast(c: Canvas, rng: random.Random) -> None:
    """THE BOOTH'S ANTENNA, standing off the roof.

    The strata alone left the top-RIGHT still empty, and a band with nothing
    but horizontals in it has nothing to hang on. This is the vertical. It is
    roof furniture, so its base is hidden behind the roof slab's fascia at
    y 118 exactly as it would be — it stops at ZEN_LIMIT and the fascia's own
    lit lip finishes it.

    IT READS 3D, which for a near-black object means exactly two values: the
    shaft's own 10141f body with a 151d28 edge down the side that faces the
    town glow (left), and a 090a14 edge on the side turned away. The cross
    arms are LIT ON THEIR UNDERSIDES for the same reason — a beam has a lit
    face and a shade face, never one flat value.

    Nothing on it emits: the beacon housing is baked with no lamp, like every
    other light in this pitch.
    """
    BASE_X, TOP_Y = 838, 12
    BLACK, STEP, LIP = C("090a14"), C("10141f"), C("151d28")

    def put(x, y, col):
        if 0 <= x < SCENE_W and 0 <= y <= ZEN_LIMIT and c.get(x, y) != C("577277"):
            c.set(x, y, col)

    def shaft(y):                       # it leans a pixel, like the pole does
        return BASE_X + int((y - TOP_Y) / 84.0 * 2.0)

    for y in range(TOP_Y + 9, ZEN_LIMIT + 1):
        s = shaft(y)
        wd = 2 + int((y - TOP_Y) / 84.0 * 2.0)
        for k in range(wd):
            put(s + k, y, STEP)
        put(s, y, LIP)                  # the glow is off to the left
        put(s + wd - 1, y, BLACK)
    for y in range(TOP_Y, TOP_Y + 9):   # the whip above the top arm
        put(shaft(y), y, STEP)
        put(shaft(y) + 1, y, BLACK)

    # two cross arms, and every number about them is different: height, the
    # reach either side, span, thickness. A first cut gave them 24px and 23px
    # of total span — different offsets about the shaft, but the same LENGTH,
    # and at a glance they read as twins. The eye measures the whole bar, not
    # where the shaft crosses it.
    for (ay, la, ra, th) in ((TOP_Y + 12, 17, 6, 2), (TOP_Y + 41, 6, 10, 3)):
        s = shaft(ay)
        for x in range(s - la, s + ra + 1):
            for y in range(ay, ay + th):
                put(x, y, STEP)
            put(x, ay + th, LIP)        # the lit underside
            put(x, ay - 1, BLACK)       # and the shade face on top
        for k in (-la + 2, ra - 3):     # two pips, unevenly placed
            put(s + k, ay - 3, STEP)
            put(s + k, ay - 2, STEP)

    # the beacon can, dead. Sits under the lower arm on a stub, off to one
    # side, so the mast is not symmetric about its own shaft.
    for y in range(TOP_Y + 58, TOP_Y + 69):
        for x in range(shaft(y) - 8, shaft(y) - 2):
            put(x, y, STEP)
        put(shaft(y) - 8, y, LIP)
        put(shaft(y) - 3, y, BLACK)
    for x in range(shaft(TOP_Y + 62) - 3, shaft(TOP_Y + 62) + 1):
        put(x, TOP_Y + 62, STEP)
    put(shaft(TOP_Y + 68) - 7, TOP_Y + 69, LIP)

    # two stays. They started as one off each side at similar angles and read
    # as a symmetric letter A with the mast for its stem — the pair was more
    # legible than either wire. So: one STEEP and high off the left, one
    # SHALLOW and low off the right, and both slack enough to curve. A guy
    # wire is never dead straight anyway.
    for (ay, ax, sag) in ((TOP_Y + 14, 792, 4.5), (TOP_Y + 50, 904, 2.2)):
        s = shaft(ay)
        n = abs(ax - s)
        for k in range(n):
            u = k / float(n)
            x = int(s + (ax - s) * u)
            y = int(ay + (ZEN_LIMIT - ay) * u + sag * 4.0 * u * (1.0 - u))
            if 0 <= x < SCENE_W and 0 <= y <= ZEN_LIMIT:
                cur = c.get(x, y)
                # capped at the lip value: the whole region's light budget is
                # ONE step off black plus the odd 151d28 edge, and a wire
                # crossing a cloud must not be the thing that spends a third.
                if cur in (C("090a14"), C("10141f")):
                    c.set(x, y, bump(cur, 1))


# ============================================================ background ====
def _far_ground(c: Canvas, rng: random.Random) -> None:
    # AERIAL PERSPECTIVE, and it is what makes the wire read at all: the
    # treeline is the FURTHEST thing, so it is the LEAST contrasty (10141f,
    # one step off the sky). The buffer beyond the wire is the darkest band
    # in the background, which is what the 172038 fence slabs stand against.
    # a low cold glow on the horizon — the rest of the district, out past the
    # wire. It fills what was 180px of dead flat sky and it gives the far
    # treeline something to silhouette against. Top edge y>=404: 14px clear
    # of the button band.
    for x in range(0, 612):
        g = int(410 + wob(x, 5.0, 137.0, 2.6, 3.0, 47.0, 0.9))
        for y in range(g, HOR):
            c.set(x, y, C("253a5e"))
        c.set(x, g, C("172038"))
        c.set(x, g - 1, C("172038"))
    _skyline(c, rng)
    for x in range(0, 612):
        t = int(422 + wob(x, 4.0, 113.0, 0.4, 3.0, 37.0, 2.2)
                + 2.0 * math.sin(x / 13.0 + 1.7))
        for y in range(t, HOR):
            c.set(x, y, C("10141f"))
        c.set(x, t, C("151d28"))
    for x in range(0, 612):
        rt = road_top(x)
        for y in range(HOR, rt):
            c.set(x, y, C("090a14"))
        vt = int(HOR + 9 + wob(x, 3.0, 53.0, 1.4, 2.0, 19.0, 0.2))
        for y in range(vt, rt):
            c.set(x, y, C("10141f"))
    # the far floodlight's pool, aimed LEFT and away — baked flat, cold and
    # DIM so a slow soft-alpha swim can be added later. Cut off left of 400.
    for x in range(70, 340):
        for y in range(HOR, 456):
            d = ((x - 194) / 124.0) ** 2 + ((y - 445) / 11.0) ** 2
            if d < 1.0:
                c.set(x, y, C("172038") if d < 0.34 else C("10141f"))
    # three low humps in the weeds inside the pool (LORE §2). Tiny, ambiguous.
    for (hx, hw, hh) in ((88, 26, 6), (146, 19, 4), (206, 30, 7)):
        for k in range(hw):
            t = abs(k - hw / 2.0) / (hw / 2.0)
            h = int(hh * (1.0 - t * t))
            top = 448 - h
            for y in range(top, 450):
                c.set(hx + k, y, C("090a14"))
            c.set(hx + k, top, C("172038"))


def _skyline(c: Canvas, rng: random.Random) -> None:
    """THE REST OF THE DISTRICT, out past the wire — the thing the horizon
    glow is coming from. Added because the left third was 180px of dead sky
    over 30px of dead ground: this is the cheapest possible content that
    belongs there, because it is pure silhouette and cannot out-shout the
    booth. No lit windows anywhere in it: light emitters stay baked OFF.

    Aerial perspective decides the colour, not the roll — anything tall
    enough to break the glow band has to be 10141f to read against 172038
    sky, and the low blocks stay 172038 so they only read against the glow.

    THE BUTTON BAND: anything overlapping x 392-568 is floored at y 398,
    a clear 8px under the band's bottom edge at y 390.
    """
    x = -rng.randint(0, 20)
    was_tall = False
    while x < 606:
        w = rng.randint(15, 58)
        top = 428 - rng.randint(5, 34)
        # NEVER two talls running. Left to a straight 52% roll, three or four
        # tall blocks landed side by side, each grew its own thin aerial, and
        # the result was a comb of identical spikes — the exact repetition
        # this project bans.
        # the two windows a tall block may stand in are chosen to keep it off
        # the SIGN's back (x 176-269) and out from behind the FLOODLIGHT MAST
        # (x 334-360) — a dark tower directly behind that mast swallowed its
        # legs and the two verticals read as one confused shape.
        tall = ((x + w < 168 or (246 < x and x + w < 330)) and not was_tall
                and rng.random() < 0.78)
        if tall:
            top = 428 - rng.randint(52, 126)          # the few tall ones, kept
        was_tall = tall                               # off the sign's back
        # the button-band floor. It has to apply to the ROOF FURNITURE as well
        # as the block: a block floored at 398 grew a 21px aerial and put 45
        # pixels back inside the band at y 382.
        ceil = 398 if x + w > 386 else 0
        top = max(top, ceil)
        # the low blocks are 151d28, not 172038: at 172038 they were the SAME
        # value as the sky band behind them and only existed where they
        # happened to cross the glow, so the skyline had holes in it.
        col = C("10141f") if top < 396 else C("151d28")
        for xx in range(max(0, x), min(606, x + w)):
            for y in range(top, 430):
                c.set(xx, y, col)
        if rng.random() < 0.30:                        # a starlit roof edge
            c.hline(max(0, x), min(605, x + w - 1), top, bump(col, 1))
        prof = rng.randrange(6)
        if prof == 0 and w > 22:                       # a stepped upper floor
            sx = x + rng.randint(2, w - 14)
            sw = rng.randint(8, max(9, w - 12))
            for xx in range(max(0, sx), min(606, sx + sw)):
                for y in range(max(ceil, top - rng.randint(6, 16)), top):
                    c.set(xx, y, col)
        elif prof == 1:                                # a chimney stack
            sx = x + rng.randint(1, max(2, w - 6))
            for xx in range(max(0, sx), min(606, sx + rng.randint(3, 6))):
                for y in range(max(ceil, top - rng.randint(8, 21)), top):
                    c.set(xx, y, col)
        elif prof == 2 and w > 18:                     # a pitched roof. The
            for k in range(w // 2):                    # ridge is in the
                for xx in (x + k, x + w - 1 - k):      # MIDDLE — written the
                    if 0 <= xx < 606:                  # other way round it
                        c.vline(xx, max(ceil, top - k // 2), top, col)
                                                       # grew a pair of horns
        elif prof == 3 and w > 24:                     # an aerial and its stay.
            sx = min(604, max(0, x + rng.randint(2, max(3, w - 2))))
            h = min(rng.randint(9, 22), top - ceil)    # 2px wide and gated on
            c.vline(sx, top - h, top, col)             # width: a 1px mast on a
            c.vline(sx + 1, top - h, top, col)         # narrow block is a
            c.hline(max(0, sx - 3), min(605, sx + 4),  # tooth, not an aerial
                    top - h + min(rng.randint(1, 4), max(0, h - 1)), col)
        elif prof == 4 and w > 20:                     # a tank on short legs
            tx = x + rng.randint(3, max(4, w - 15))
            tw = rng.randint(9, 15)
            for xx in range(max(0, tx), min(606, tx + tw)):
                for y in range(max(ceil, top - rng.randint(10, 15)), top - 4):
                    c.set(xx, y, col)
            for k in (1, tw - 2):
                if 0 <= tx + k < 606:
                    c.vline(tx + k, top - 5, top, col)
        x += w + rng.randint(0, 13)


def _pole(c: Canvas, rng: random.Random) -> None:
    """a distribution pole beyond the wire and the line it carries, running
    off behind the booth. Standing rule: a powered thing shows where its
    power comes from — the booth's junction box takes its drop off this line
    out of frame to the right, and this is the only reason there is anything
    at all in the upper left.

    The three spans get three DIFFERENT sags on purpose; parallel catenaries
    read as a drawn grid. Every wire pixel steps its own background up one,
    so the line stays visible across sky band, cloud bar and glow alike
    without ever being a fixed bright colour."""
    px, base, top = 104, 434, 188

    def shaft(y):                                     # a real pole leans
        return px + int((y - top) / 246.0 * 3.0)

    for y in range(top, base):
        s = shaft(y)
        wd = 4 + int((y - top) / 246.0 * 3.0)
        for k in range(wd):
            c.set(s + k, y, C("10141f"))
        c.set(s, y, C("090a14"))
        c.set(s + wd - 1, y, C("172038"))             # the glow side
    for (ay, half, thick) in ((196, 23, 3), (214, 15, 2)):
        s = shaft(ay)
        for y in range(ay, ay + thick):
            for xx in range(s - half, s + half + 5):
                c.set(xx, y, C("10141f"))
        c.hline(s - half, s + half + 4, ay, C("172038"))
        for k in (-half + 1, 0, half + 3):            # insulator pips
            c.vline(s + k + 2, ay - 3, ay - 1, C("151d28"))
            c.set(s + k + 2, ay - 3, C("202e37"))
    for k in range(9):                                # the brace under the arm
        c.set(shaft(200 + k) + 5 + k, 200 - k + 9, C("10141f"))
    for y in range(232, 258):                         # the transformer can
        s = shaft(y)
        for xx in range(s - 9, s):
            c.set(xx, y, C("10141f") if xx > s - 8 else C("090a14"))
        c.set(s - 8, y, C("151d28"))
    c.hline(shaft(232) - 9, shaft(232) - 1, 232, C("172038"))
    c.hline(shaft(257) - 9, shaft(257) - 1, 257, C("090a14"))

    def span(x0, x1, y0, y1, sag):
        for x in range(x0, x1):
            u = (x - x0) / float(x1 - x0)
            y = int(y0 + (y1 - y0) * u + sag * 4.0 * u * (1.0 - u))
            c.set(x, y, bump(c.get(x, y), 1))

    for (ya, yb, sg) in ((194, 166, 36), (202, 174, 54), (212, 186, 76)):
        span(shaft(ya) + 20, 566, ya, yb, sg)
        span(0, shaft(ya) - 20, ya - 18, ya, 9)
    for k in range(14):                               # one wire broken, curled
        c.set(shaft(214) - 17 - k // 2, 216 + k + (k * k) // 9,
              C("151d28"))


def _wire(c: Canvas, rng: random.Random) -> None:
    """the cordon: low, far, and mostly a silhouette. Panels shrink 64->26px
    but the MESH stops at x<480 — below an 8px cell any lattice degenerates
    into single-pixel speckle, which is banned."""
    posts = []
    px = BOOTH_L
    while px > 22:
        posts.append(px)
        t = (BOOTH_L - px) / 528.0
        px -= max(9, int((64 - 38 * t) * rng.uniform(0.90, 1.10)))
    posts.append(px)
    # solid slabs first
    for i in range(len(posts) - 1):
        x1, x0 = posts[i], posts[i + 1]
        for x in range(max(0, x0), x1):
            for y in range(int(rail_y(x)), int(wire_base(x))):
                c.set(x, y, C("172038"))
    # diamond mesh, near panels only
    for x in range(480, BOOTH_L):
        for y in range(int(rail_y(x)) + 2, int(wire_base(x))):
            if (x + y) % 8 == 0 or (x - y) % 8 == 0:
                c.set(x, y, C("202e37"))
    # top rail + the ground line the whole run stands on
    for x in range(0, BOOTH_L):
        ry = int(rail_y(x))
        c.set(x, ry, C("202e37"))
        c.set(x, ry + 1, C("10141f"))
        by = int(wire_base(x))
        c.set(x, by, C("090a14"))
        c.set(x, by + 1, C("090a14"))
    # posts, rolled lean and height
    for p in posts:
        if p < 4:
            continue
        lean = rng.choice((0, 0, 0, 1, -1))
        for y in range(int(rail_y(p)) - 2, int(wire_base(p)) + 2):
            xx = p + (lean if y > (rail_y(p) + wire_base(p)) / 2 else 0)
            c.set(xx, y, C("10141f"))
            c.set(xx + 1, y, C("090a14"))
    # RAZOR COIL — solid rolled band ABOVE the rail, never drawn as loops.
    # CRITIC FIX: at x 400-560 its top edge lands at y ~407-410, a clean 17px
    # under the button band. The 577277 lip and the barbs run only x>=500.
    for x in range(26, BOOTH_L):
        ry = int(rail_y(x))
        t = (BOOTH_L - x) / 528.0
        h = max(2, int(11 - 8 * t + 1.4 * math.sin(x / 21.0 + 0.6)))
        for y in range(ry - h, ry):
            c.set(x, y, C("202e37"))
        c.set(x, ry - h, C("172038"))
        if x >= 500:
            c.set(x, ry - h, C("577277"))
    bx = 500
    while bx < BOOTH_L - 6:
        bx += rng.randint(7, 13)
        s = rng.randint(4, 6)
        ry = int(rail_y(bx))
        h = max(2, int(11 - 8 * (BOOTH_L - bx) / 528.0))
        top = ry - h
        for k in range(s):
            half = (s - k) // 2
            c.hline(bx - half, bx + half, top - s + k,
                    C("394a50") if k else C("577277"))


def _tower(c: Canvas, rng: random.Random) -> None:
    """one floodlight tower, near-silhouette, cone aimed left and away."""
    top, base = 196, 434
    for y in range(top, base):
        t = (y - top) / float(base - top)
        lx = int(350 - t * 7)
        rx = int(352 + t * 7)
        c.vline(lx, y, y, C("151d28"))
        c.set(lx + 1, y, C("090a14"))
        c.vline(rx, y, y, C("151d28"))
        c.set(rx + 1, y, C("090a14"))
    by = top + 6
    while by < base - 8:
        by += rng.randint(24, 33)
        t = (by - top) / float(base - top)
        lx, rx = int(350 - t * 7), int(353 + t * 7)
        for k in range(rx - lx):
            c.set(lx + k, by + int(k * rng.choice((0.30, -0.30))), C("151d28"))
    # the head: a hood aimed away to the left, its glass never facing us
    c.rect(334, 184, 360, 197, C("151d28"))
    c.rect(336, 186, 358, 195, C("090a14"))
    c.hline(330, 344, 186, C("202e37"))
    c.hline(330, 342, 187, C("151d28"))
    c.set(333, 192, C("253a5e"))
    c.set(332, 193, C("253a5e"))


def _sign(c: Canvas, rng: random.Random) -> None:
    """a bent stencilled plate. NO GLYPHS — the words are suggested with
    squiggles the way the den's job sheets suggest their notes."""
    def lean(y: int) -> int:
        return int((404 - y) * 0.085)

    # post first, with a rust run
    for y in range(352, 438):
        dx = lean(y)
        c.vline(218 + dx, y, y, C("202e37"))
        c.vline(219 + dx, y, y, C("151d28"))
        c.vline(220 + dx, y, y, C("090a14"))
    for y in range(404, 432):
        if (y // 3) % 2 == 0:
            c.set(218 + lean(y), y, C("602c2c"))
            c.set(219 + lean(y), y, C("341c27"))
    # plate
    for y in range(344, 383):
        dx = lean(y)
        for x in range(176, 269):
            edge = min(x - 176, 268 - x, y - 344, 382 - y)
            if edge < 1:
                col = C("090a14")
            elif y < 366:
                col = C("394a50")     # background plane: LOWEST contrast. The
            else:                     # first cut used 577277/394a50 and the
                col = C("202e37")     # sign read brighter than the man.
            c.set(x + dx, y, col)
    # the bent corner, catching what light there is
    for k in range(15):
        for j in range(15 - k):
            c.set(268 + lean(344 + k) - j, 344 + k,
                  C("577277") if j < 12 - k else C("394a50"))
    # two lines of stencil, squiggled not written
    for (ry, x0, x1) in ((354, 186, 258), (368, 186, 244)):
        for x in range(x0, x1):
            if (x - x0) % 13 > 9:
                continue
            dx = lean(ry)
            c.set(x + dx, ry + (1 if math.sin(x * 1.9) > 0.2 else 0),
                  C("090a14"))
            c.set(x + dx, ry + 1 + (1 if math.sin(x * 1.9) > 0.2 else 0),
                  C("090a14"))
    c.hline(176 + lean(383), 268 + lean(383), 383, C("090a14"))


# ================================================================== road ====
def _spill(c: Canvas, rng: random.Random) -> None:
    """THE WINDOW'S LIGHT ON WET TARMAC.

    The first cut drew this as one smooth lens with a pointed hot core and it
    read as an ORANGE DAGGER lying on the road — a drawn shape, not light.
    What fixes it: light has no edge of its own, it borrows the edge of
    whatever it lands on. So (a) the wash boundary is a per-x random walk on
    top of three sines, never a curve; (b) it does not taper to a point, it
    BREAKS UP as it runs out; (c) every bright value in here now belongs to a
    piece of road — standing water, the rake along the wet ruts, the tarmac's
    own cracks — and never to the wash itself. Its hottest colour is 884b2b
    and it survives only inside puddles, so it can never beat the face.
    """
    jag = {}
    j = 0.0
    for x in range(300, BOOTH_L + 4):
        j = max(-0.19, min(0.19, j + rng.uniform(-0.07, 0.07)))
        jag[x] = j

    def field(x: int, y: int) -> float:
        t = min(1.0, max(0.0, (BOOTH_L - x) / 236.0))
        cy = 478.0 + t * 26.0 + 3.5 * math.sin(x / 43.0 + 2.0)
        hh = 9.0 + t * 23.0
        d = abs(y - cy) / hh
        d += 0.13 * math.sin(x / 27.0) + 0.09 * math.sin(y / 12.0)
        d += 0.07 * math.sin(x / 9.0 + 1.4) + 0.032 * math.sin(x / 4.3 + 0.2)
        d += jag.get(x, 0.0)
        d += max(0.0, t - 0.46) * (3.2 + 1.9 * math.sin(x / 19.0 + 0.7))
        return d

    def level(x: int, y: int) -> int:
        """how bright this pixel of tarmac is, 0-3. The inner steps are also
        spent by distance, so the wash runs out of VALUE before it runs out
        of area — the far end goes dim and ragged instead of ending."""
        d = field(x, y)
        if d >= 1.0:
            return -1
        # the distance falloff is folded INTO d before it is quantised. Spent
        # as a separate `lv - int(t * 1.9)` it stepped on whole values of t
        # and drew two hard VERTICAL seams straight down the beam.
        t = min(1.0, max(0.0, (BOOTH_L - x) / 236.0))
        e = d + t * 0.62
        return 3 if e < 0.34 else (2 if e < 0.70 else 1)

    for x in range(300, BOOTH_L + 2):
        rt = road_top(x)
        for y in range(max(452, rt), SCENE_H):
            lv = level(x, y)
            if lv >= 0:
                c.set(x, y, C(SPILL[lv + 1]))

    # A ROAD REPAIR, straddling the beam's far edge. The single most useful
    # thing in here: the beam now has to cross a piece of the road that is a
    # different material, so its edge is interrupted by something that was
    # already there instead of by its own falloff.
    # Its ENDS are tapered, not cut: a first pass drew it between two fixed x
    # bounds and the two vertical edges read as a rectangle laid over the
    # light, which is the very defect this whole function exists to kill.
    for x in range(464, 556):
        u = (x - 464) / 92.0
        e = min(1.0, min(u, 1.0 - u) * 5.6 + 0.12)
        mid = 474.5 + 3.0 * math.sin(u * 4.3 + 0.9)
        hh = 12.5 * e + 2.5 * math.sin(u * 6.1 + 0.4) + 1.6 * math.sin(x / 6.0)
        if hh < 1.0:
            continue
        top, bot = int(mid - hh), int(mid + hh)
        for y in range(max(top, road_top(x)), bot):
            lv = level(x, y)
            c.set(x, y, C(SPILL[max(0, lv)]) if lv >= 0
                  else C("10141f"))              # the patch is coarser and
        if top >= road_top(x):                   # eats a step of the light,
            c.set(x, top, lit(c.get(x, top), -1))   # but its near lip catches
        c.set(x, bot, lit(c.get(x, bot), 1))        # what the patch does not
    # a manhole inside the beam: a hard-edged real object with a seating
    # groove and a lit near rim, so there is something in the light that is
    # not made of light. It sits FLUSH — a dark disc reads as an open hole.
    for x in range(509, 548):
        u = (x - 528.0) / 19.0
        h = 8.0 * math.sqrt(max(0.0, 1.0 - u * u))
        if h < 0.7:
            continue
        top, bot = int(503 - h), int(503 + h)
        for y in range(top + 1, 503):                # the far half sits in its
            c.set(x, y, lit(c.get(x, y), -1))        # own shade
        # both arcs BREAK where the rim is worn. A closed ellipse outline
        # reads as a ring chalked on the road, not as a cover in it.
        if math.sin(x / 3.1 + 0.6) > -0.55:
            c.set(x, top, C("241527"))
        if math.sin(x / 4.7 + 2.2) > -0.62:
            c.set(x, bot, lit(c.get(x, bot), 1))
    for k in range(3):                               # its lifting slots
        c.hline(517 + k * 8, 521 + k * 8, 499 + k * 2, C("241527"))
        c.hline(517 + k * 8, 521 + k * 8, 500 + k * 2,
                lit(c.get(519, 500 + k * 2), 1))

    # THE RAKE. Wet asphalt does not glow evenly — it streaks ALONG the light.
    # Rolled slopes out of the booth's left corner, each broken into dashes so
    # no two are the same length and none is a full clean line.
    for i in range(11):
        sl = rng.uniform(-0.03, 0.28)
        x = BOOTH_L - rng.randint(1, 30)
        y0 = 470.0 + rng.uniform(-9.0, 22.0)
        thick = rng.randint(1, 3)
        run = rng.randint(34, 170)
        gap = 0
        while run > 0 and x > 326:
            run -= 1
            x -= 1
            yy = int(y0 + (BOOTH_L - x) * sl + 2.0 * math.sin(x / 17.0))
            if gap > 0:
                gap -= 1
                continue
            if rng.random() < 0.04:
                gap = rng.randint(3, 12)
                continue
            for k in range(thick):
                if field(x, yy + k) < 0.94 and yy + k >= road_top(x):
                    cur = c.get(x, yy + k)
                    if _SP.get(cur, 9) < 4:          # capped at 602c2c: the
                        c.set(x, yy + k, lit(cur, 1))  # rake is sheen, not
                                                       # a light source

    # STANDING WATER. This is where the hot value lives now: light has to land
    # on something to be bright, and a puddle is the only thing on a road that
    # can throw it back at you. Rolled sizes, rolled gaps, never a row.
    px = BOOTH_L - rng.randint(6, 20)
    while px > 330:
        pw = rng.randint(6, 15)
        ph = rng.randint(2, 5)
        t = (BOOTH_L - px) / 236.0
        py = int(478 + t * 26 + rng.randint(-11, 13))
        wet = level(px, py) >= 2
        for x in range(px - pw, px + pw + 1):
            u = (x - px) / float(pw)
            h = ph * math.sqrt(max(0.0, 1.0 - u * u))
            h *= 1.0 + 0.24 * math.sin(x / 4.7 + px)
            top, bot = int(py - h), int(py + h)
            if bot < top or bot < road_top(x):
                continue
            for y in range(max(top, road_top(x)), bot + 1):
                cur = c.get(x, y)
                if not wet:
                    c.set(x, y, lit(cur, -1))            # dark water, no light
                elif _SP.get(cur, 9) < 4:
                    c.set(x, y, lit(cur, 1))
            if top >= road_top(x):
                c.set(x, top, lit(c.get(x, top), -2))     # the far lip, dark
            # the near lip is the ONLY 884b2b on the road, and only on the
            # two puddles closest to the window: a glint, not a shape.
            if wet and t < 0.34 and abs(u) < 0.45:
                c.set(x, bot, C("884b2b"))
        px -= pw + rng.randint(16, 58)


def _ruts_and_cracks(c: Canvas, rng: random.Random) -> None:
    """drawn AFTER the light, on purpose. A rut that stops at the edge of the
    spill is a rug's fringe; a rut that runs straight through it is a road."""
    for i in range(5):
        y0 = rng.randint(452, 536)
        sl = rng.uniform(0.16, 0.34)          # runs WITH the road, like the
        wdt = rng.randint(2, 4)               # centre dashes do
        ph = rng.uniform(0, 6.0)
        x = rng.randrange(430, 580)
        while x > -4:
            x -= 1
            yy = int(y0 + (x - 560) * -sl + 4.0 * math.sin(x / 37.0 + ph))
            if yy < road_top(max(0, x)) or yy >= SCENE_H:
                continue
            for k in range(wdt):
                if yy + k < SCENE_H:
                    c.set(x, yy + k, lit(c.get(x, yy + k), -1))
    # cracks: solid, branching, 1px. Structural detail, never dot noise.
    for i in range(5):
        stack = [(rng.randrange(330, 556), rng.randrange(458, 532),
                  rng.uniform(-0.5, 0.5), rng.randint(20, 60))]
        while stack:
            x, y, ang, ln = stack.pop()
            fx, fy = float(x), float(y)
            for k in range(ln):
                ang += rng.uniform(-0.22, 0.22)
                fx -= math.cos(ang) * 1.0
                fy += math.sin(ang) * 0.55 + 0.30
                xx, yy = int(fx), int(fy)
                if not (0 <= xx < SCENE_W and road_top(xx) <= yy < SCENE_H):
                    break
                c.set(xx, yy, lit(c.get(xx, yy), -1))
                if k and k % 9 == 0:
                    c.set(xx, yy + 1, lit(c.get(xx, yy + 1), -2))
                if ln > 24 and rng.random() < 0.06:
                    stack.append((xx, yy, ang + rng.choice((-0.8, 0.8)),
                                  rng.randint(6, 16)))


def _road(c: Canvas, rng: random.Random) -> None:
    for x in range(0, BOOTH_L + 4):
        rt = road_top(x)
        for y in range(rt, SCENE_H):
            c.set(x, y, C("151d28"))
        c.set(x, rt, C("10141f"))
        c.set(x, rt + 1, C("172038"))
    # broken centre dash, rolled lengths and gaps, dimmer with distance
    t = 0.0
    while t < 1.0:
        ln = rng.uniform(0.030, 0.062)
        gp = rng.uniform(0.038, 0.078)
        for k in range(int(ln * 300)):
            u = t + (k / 300.0)
            if u > 1.0:
                break
            x = int(352 - u * 320)
            y = int(452 + u * 96)
            w = 2 + int(u * 3)
            col = C("577277") if u > 0.55 else C("394a50")
            for j in range(w):
                c.set(x - j, y, col)
                c.set(x - j, y + 1, bump(col, -1))
        t += ln + gp
    _spill(c, rng)
    _ruts_and_cracks(c, rng)
    # a couple of solid wear scars, never speckle
    region = {(x, y) for y in range(455, SCENE_H) for x in range(20, 540)}
    for i in range(3):
        for (qx, qy) in blob(rng, rng.randrange(60, 500),
                             rng.randrange(470, 530),
                             rng.randint(30, 90), region):
            c.set(qx, qy, bump(c.get(qx, qy), -1))


def _queue(c: Canvas, rng: random.Random) -> None:
    """THE CAR THAT NEVER PAID. A toll gate with an empty road in front of it
    is a gate with no story; this is the first in a queue that stopped being
    a queue, nose at the boom, driver's door still standing open.

    Near-silhouette by law: the booth is the focal point, so the whole thing
    lives in three cold darks with a single warm rake down its right flank
    where the window's light reaches it, and one dead tail-light glass. No
    lamps, no glow — every light emitter here is baked OFF."""
    x0, x1 = 200, 356
    REAR = 226                       # where the rear face meets the flank
    SCRN = 318                       # where the windscreen starts to fall

    # it sits BELOW the boom on purpose: the bar hangs 18px clear of the roof
    # line all the way along, so the two never run tangent to one another and
    # there is room on the roof for a load that is not eaten by the boom.
    def gnd(x):
        return 534.0 - (x - x0) * 0.23

    def roof(x):
        # the cab roof, then the windscreen falling away to a short bonnet:
        # a flat-topped box all the way to the front end read as a skip.
        r = 496.0 - (x - x0) * 0.12
        if x >= SCRN:
            r += min(11.2, (x - SCRN) * 0.8)
        return r

    # the two planes. The rear face catches the horizon glow and the flank is
    # turned away from everything, so the corner between them is the whole
    # read — this is a box in space, not a blob on the road.
    for x in range(x0, x1):
        g, r = int(gnd(x)), int(roof(x))
        col = C("151d28") if x < REAR else C("090a14")
        for y in range(r, g):
            c.set(x, y, col)
        if x >= REAR:                                 # the flank's lower half
            c.vline(x, min(g - 1, r + 20), g - 1, C("10141f"))
                                                      # lifts one step so the
                                                      # black wheels can read
        if REAR <= x < SCRN:                          # a sliver of roof TOP
            c.vline(x, r, r + 2, C("202e37"))         # face: we look down on it
        c.set(x, r, C("394a50") if x < SCRN + 3 else C("202e37"))
    for y in range(int(roof(REAR)), int(gnd(REAR))):  # the corner post
        c.set(REAR, y, C("202e37"))
    c.vline(x0, int(roof(x0)) + 1, int(gnd(x0)), C("090a14"))
    # glazing: a dead band along the flank and a rear screen, both blacked
    for x in range(REAR + 3, SCRN + 12):
        r = int(roof(x))
        for y in range(r + 4, r + 16 - (x - REAR) // 22):
            c.set(x, y, C("090a14"))
        c.set(x, r + 16 - (x - REAR) // 22, C("202e37"))     # the sill line
    for x in range(x0 + 4, REAR - 2):
        r = int(roof(x))
        for y in range(r + 5, r + 19):
            c.set(x, y, C("10141f"))
    c.hline(x0 + 4, REAR - 3, int(roof(x0)) + 19, C("202e37"))
    for k in range(6):                                # two pillars in the glass
        c.vline(268 + k // 3, int(roof(268)) + 4, int(roof(268)) + 14,
                C("151d28"))
        c.vline(300 + k // 3, int(roof(300)) + 4, int(roof(300)) + 13,
                C("151d28"))
    # THE DRIVER'S DOOR, standing open — the one shape that says abandoned
    # instead of parked, and the only thing that breaks the box
    for k in range(34):
        dx = 262 + k
        top = int(roof(dx)) + 4 + k // 5
        bot = int(gnd(dx)) + 5 + k // 3
        for y in range(top, bot):
            c.set(dx, y, C("10141f") if y < top + 13 else C("151d28"))
        c.set(dx, top, C("577277") if k < 20 else C("394a50"))
        c.set(dx, bot, C("090a14"))
        if k > 26:
            c.vline(dx, top, bot, C("090a14"))        # its shaded far edge
    # wheels: different radii, both flat, both with a lit arch lip over them
    for (wx, wr) in ((238, 10), (334, 8)):
        for k in range(-wr, wr + 1):
            h = int(math.sqrt(max(0.0, wr * wr - k * k)) * 0.78)
            g = int(gnd(wx + k))
            for y in range(g - h, g + 2):
                c.set(wx + k, y, C("090a14"))
            if h > 2:
                c.set(wx + k, g - h - 1, C("202e37"))
    # a tarp lashed over a roof load — the reason it was at the gate at all
    for x in range(272, 314):
        u = (x - 293) / 21.0
        h = int(11.0 * (1.0 - u * u) + 0.5)
        if h < 1:
            continue
        r = int(roof(x))
        for y in range(r - h, r):
            c.set(x, y, C("151d28") if y > r - h + 2 else C("202e37"))
        c.set(x, r - h, C("394a50"))
    for k in range(5):                                # its lashings
        xx = 276 + k * rng.randint(7, 10)
        if xx < 312:
            c.vline(xx, int(roof(xx)) - 7, int(roof(xx)) - 1, C("090a14"))
    # rust eating the sill, and the dead tail-light glass on the rear face
    for k in range(rng.randint(14, 22)):
        xx = 204 + k
        c.vline(xx, int(gnd(xx)) - 5 - k % 3, int(gnd(xx)) - 1, C("341c27"))
    c.rect(x0 + 2, int(roof(x0)) + 23, x0 + 5, int(roof(x0)) + 26, C("752438"))
    for x in range(x0 - 4, x1 + 6):                   # the contact shadow
        u = abs(x - 268) / 76.0
        d = int(5.0 * math.sqrt(max(0.0, 1.0 - u * u)))
        for y in range(int(gnd(min(x1 - 1, max(x0, x)))),
                       int(gnd(min(x1 - 1, max(x0, x)))) + d):
            c.set(x, y, C("090a14"))


# ================================================================= booth ====
def _booth(c: Canvas, rng: random.Random) -> None:
    # front face, cel-lit off the shift lamp
    for x in range(BOOTH_L, BOOTH_R + 1):
        for y in range(ROOF_B, SCENE_H):
            c.set(x, y, cold(face_level(x, y)))
    # return face — the booth is a BOX, not a flat. Its top edge slopes away.
    for x in range(BOOTH_R + 1, SCENE_W):
        t = (x - BOOTH_R) / float(SCENE_W - BOOTH_R)
        top = int(ROOF_B + t * 32)
        for y in range(top, SCENE_H):
            c.set(x, y, cold(max(0, face_level(x, y) - 2)))
        c.set(x, top, C("202e37"))
        c.set(x, top + 1, C("151d28"))
    c.vline(BOOTH_R, ROOF_B, SCENE_H - 1, C("090a14"))
    # corrugation: vertical seams at ROLLED spacing (the den's plank lesson)
    sx = BOOTH_L
    seams = []
    while sx < BOOTH_R - 8:
        sx += rng.randint(22, 34)
        seams.append(sx)
    rx = BOOTH_R + 6
    while rx < SCENE_W:
        seams.append(rx)
        rx += rng.randint(19, 27)
    for s in seams:
        for y in range(ROOF_B, SCENE_H):
            if s > BOOTH_R:
                t = (s - BOOTH_R) / float(SCENE_W - BOOTH_R)
                if y < ROOF_B + t * 32:
                    continue
            lv = face_level(s, y)
            c.set(s, y, cold(lv + 1))
            c.set(s + 1, y, cold(lv - 1))
    # horizontal battens
    for by in (182, 486):
        for x in range(BOOTH_L, SCENE_W):
            yy = by
            if x > BOOTH_R:
                t = (x - BOOTH_R) / float(SCENE_W - BOOTH_R)
                yy = by + int(t * 26)
            lv = face_level(x, yy)
            c.set(x, yy, cold(lv + 1))
            c.set(x, yy + 1, cold(lv + 1))
            c.set(x, yy + 2, cold(lv))
            c.set(x, yy + 3, cold(lv - 2))
    # a few SMALL SOLID wear patches — no dots anywhere
    region = {(x, y) for y in range(ROOF_B + 12, SCENE_H) for x in range(BOOTH_L, SCENE_W)}
    for i in range(4):
        for (qx, qy) in blob(rng, rng.randrange(BOOTH_L + 10, 940),
                             rng.randrange(200, 520),
                             rng.randint(24, 70), region):
            c.set(qx, qy, bump(c.get(qx, qy), -1 if i % 2 else 1))
    # left corner: the booth reads against the sky only because this rim is
    # here — face and sky sit two steps apart and that is not enough alone.
    c.vline(BOOTH_L, ROOF_B, SCENE_H - 1, C("090a14"))
    c.vline(BOOTH_L + 1, ROOF_B, SCENE_H - 1, C("202e37"))
    c.vline(BOOTH_L + 2, ROOF_B, SCENE_H - 1, C("151d28"))

    # ---- the roof slab, overhanging left, receding right ----
    for x in range(552, SCENE_W):
        t = max(0.0, (x - BOOTH_R) / float(SCENE_W - BOOTH_R))
        rt = ROOF_T + int(t * 32)
        rb = rt + 16
        lip = int(2 + 1.2 * math.sin(x / 37.0 + 1.1))
        for y in range(rt, rb):
            if y < rt + lip:
                col = C("577277")
            elif y < rt + lip + 4:
                col = C("394a50")
            elif y < rb - 4:
                col = C("202e37")
            else:
                col = C("090a14")
            c.set(x, y, col)
        c.set(x, rb, C("090a14"))
    for i in range(3):                      # rolled bright segments on the lip
        gx = rng.randrange(560, 900)
        gw = rng.randint(18, 46)
        for x in range(gx, min(SCENE_W, gx + gw)):
            t = max(0.0, (x - BOOTH_R) / float(SCENE_W - BOOTH_R))
            rt = ROOF_T + int(t * 32)
            c.set(x, rt, C("819796"))
            c.set(x, rt + 1, C("819796"))
    # the overhang's hard cel shadow on the face
    for x in range(BOOTH_L, SCENE_W):
        t = max(0.0, (x - BOOTH_R) / float(SCENE_W - BOOTH_R))
        rb = ROOF_T + int(t * 32) + 17
        d = int(5 + 1.4 * math.sin(x / 29.0 + 2.2))
        for y in range(rb, rb + d):
            c.set(x, y, bump(c.get(x, y), -2))

    # ---- the shift lamp over the window, WITH ITS CONDUIT ----
    # (standing rule: a powered thing must show where the power comes from)
    c.rect(694, 154, 726, 158, C("202e37"))
    c.rect(692, 158, 728, 168, C("151d28"))
    c.hline(690, 730, 168, C("394a50"))
    c.hline(694, 726, 169, C("577277"))
    c.rect(700, 170, 720, 173, C("090a14"))
    c.vline(710, 146, 154, C("151d28"))
    for x in range(710, 806):
        c.set(x, 146 + int(2.0 * math.sin((x - 710) / 19.0)), C("151d28"))
        c.set(x, 147 + int(2.0 * math.sin((x - 710) / 19.0)), C("090a14"))
    c.rect(804, 138, 822, 156, C("202e37"))
    c.rect(806, 140, 820, 154, C("151d28"))
    c.hline(806, 820, 140, C("394a50"))

    # ---- the concrete plinth the whole booth stands on ----
    # the bottom quarter of the face was 400px of one dark value; this grounds
    # it and gives the boom something to pass in front of.
    for x in range(BOOTH_L, SCENE_W):
        pt = int(498 + wob(x, 3.0, 67.0, 0.9, 2.0, 23.0, 2.4))
        if x > BOOTH_R:
            pt += int((x - BOOTH_R) / float(SCENE_W - BOOTH_R) * 22)
        for y in range(pt, SCENE_H):
            c.set(x, y, C("202e37") if y < pt + 5 else C("151d28"))
        c.set(x, pt, C("394a50"))
        c.set(x, pt + 1, C("394a50"))
    region = {(x, y) for y in range(500, SCENE_H) for x in range(BOOTH_L, SCENE_W)}
    for i in range(3):
        for (qx, qy) in blob(rng, rng.randrange(BOOTH_L + 20, 940),
                             rng.randrange(508, 538),
                             rng.randint(30, 80), region):
            c.set(qx, qy, C("10141f") if i else C("202e37"))
    # a vent grille — and it is the GENERATOR's air, which is what gives the
    # whole bottom-right quarter its reason: vent, isolator, fuel. See
    # _service() below.
    for k in range(7):
        yy = 430 + k * 4
        c.hline(692, 744, yy, C("10141f"))
        c.hline(694, 742, yy + 1, C("394a50"))
    c.vline(690, 428, 456, C("202e37"))
    c.vline(746, 428, 456, C("10141f"))
    c.hline(690, 746, 427, C("394a50"))
    c.hline(690, 746, 457, C("090a14"))
    # THE POWER FEED, visible end to end: junction box -> conduit -> ground
    for x in range(820, 934):
        c.set(x, 150, C("202e37"))
        c.set(x, 151, C("151d28"))
        c.set(x, 152, C("090a14"))
    for y in range(150, 502):
        dx = int((y - 150) / 352.0 * 26)
        c.vline(928 + dx, y, y, C("202e37"))
        c.vline(929 + dx, y, y, C("151d28"))
        c.vline(930 + dx, y, y, C("090a14"))
        if y % 97 < 4:
            c.hline(926 + dx, 933 + dx, y, C("394a50"))

    # ---- a curled notice taped left of the window ----
    for y in range(214, 257):
        curl = int(3.0 * math.sin((y - 214) / 26.0))
        for x in range(578, 605):
            if x > 601 - curl:
                continue
            col = C("819796") if x < 598 - curl else C("577277")
            if y > 250:
                col = bump(col, -1)
            c.set(x, y, col)
    for k in range(6):
        for x in range(582, 598 - k % 3 * 4):
            if (x - 582) % 11 > 8:
                continue
            c.set(x, 222 + k * 5 + (1 if math.sin(x * 2.1) > 0.3 else 0),
                  C("341c27"))
    c.rect(584, 210, 596, 214, C("c09473"))          # tape
    c.hline(584, 596, 210, C("d7b594"))
    _service(c, rng)


def _service(c: Canvas, rng: random.Random) -> None:
    """THE BOOTH'S SERVICE CORNER — the bottom-right 200x140 was the least
    interesting patch in the picture: a dark wall, one vent, and a conduit
    running past it to nowhere. This gives all three of them a single reason
    to be there. The vent is the generator's air; the conduit comes down off
    the junction box and dies in an isolator; the isolator feeds the
    generator through a spur; and the can on the plinth is what the generator
    drinks. Every one of them was already implied and none of them was drawn.

    Lit from the shift lamp ABOVE the window, so tops are lit and undersides
    are dark — the opposite of the man's face, which is lit from below by the
    desk lamp. That contrast is the whole picture, so it holds out here too.
    Nothing here emits: the isolator's lamp is baked OFF like the fuse box."""
    # the branch off the down-conduit, running back along the wall
    for x in range(846, 954):
        c.set(x, 450, C("394a50"))
        c.set(x, 451, C("202e37"))
        c.set(x, 452, C("090a14"))
    for k in range(3):                                # saddle clips, uneven
        sx = 866 + k * rng.randint(24, 32)
        c.vline(sx, 448, 454, C("151d28"))
        c.set(sx, 448, C("577277"))

    # THE ISOLATOR. Deliberately kept LOW on the ladder — 151d28 body with
    # 394a50 only on the edges the shift lamp can actually reach. A first cut
    # built it in 202e37/577277 and a grey box in the dark bottom corner
    # started pulling the eye off the window, which this picture cannot
    # afford.
    c.rect(800, 448, 848, 494, C("151d28"))
    c.hline(800, 848, 448, C("394a50"))
    c.hline(800, 848, 449, C("202e37"))
    c.hline(800, 848, 493, C("090a14"))
    c.hline(800, 848, 494, C("090a14"))
    c.vline(800, 448, 494, C("202e37"))
    c.vline(848, 448, 494, C("090a14"))
    c.hline(801, 847, 470, C("090a14"))               # the lid seam
    c.hline(801, 847, 471, C("202e37"))
    for hy in (455, 484):                             # two hinges
        c.rect(797, hy, 801, hy + 5, C("202e37"))
        c.set(797, hy, C("394a50"))
    c.rect(846, 466, 851, 473, C("202e37"))           # the hasp
    c.rect(848, 473, 853, 480, C("394a50"))           # and its padlock
    c.rect(849, 475, 852, 478, C("151d28"))
    for k in range(8):                                # the lever, thrown down
        c.set(849 + k, 459 + k // 3, C("394a50"))
        c.set(849 + k, 460 + k // 3, C("202e37"))
    c.rect(855, 460, 858, 464, C("577277"))           # its knob
    c.rect(838, 442, 846, 450, C("10141f"))           # the gland it enters by
    c.hline(838, 846, 442, C("202e37"))
    c.rect(806, 492, 814, 500, C("10141f"))           # and the one it leaves by
    c.rect(806, 454, 822, 466, C("202e37"))           # a rating plate, no
    c.hline(806, 822, 454, C("394a50"))               # glyphs — just the shape
    for k in range(4):
        for x in range(808, 820):
            if (x - 808 + k * 5) % 9 > 5:
                continue
            c.set(x, 456 + k * 3, C("10141f"))
    for k in range(11):                               # the hazard triangle
        c.hline(830 - k // 2, 830 + k // 2, 476 + k,
                C("577277") if k > 8 else C("394a50"))
    for k in range(6):
        c.set(830 + (1 if k % 4 < 2 else -1), 479 + k, C("090a14"))
    # ONE rust weep off the bottom lip, as a solid stain. Drawn as separate
    # columns it read as a row of little legs under the box.
    for k in range(13):
        h = int(4.5 * math.sqrt(max(0.0, 1.0 - ((k - 6) / 6.5) ** 2))
                + 1.5 * math.sin(k * 1.7))
        for y in range(495, 495 + max(0, h)):
            c.set(818 + k, y, C("341c27"))
        if 3 < k < 9:
            c.set(818 + k, 495, C("602c2c"))

    # the spur across to the generator's vent, with a drip loop in it
    for x in range(748, 802):
        d = 1 if 762 < x < 780 else 0
        c.set(x, 468 + d, C("394a50"))
        c.set(x, 469 + d, C("202e37"))
        c.set(x, 470 + d, C("090a14"))
    c.rect(744, 464, 752, 474, C("151d28"))           # where it enters the wall
    c.hline(744, 752, 464, C("394a50"))

    # THE FUEL CAN on the plinth, under the vent. An iso box: top face lit,
    # front face mid, the return face in shade — it has to read 3D like
    # everything else in this project.
    for k in range(9):                                # the top face
        c.hline(702 + k, 738 + k, 472 - k, C("202e37") if k < 7 else C("394a50"))
    for y in range(472, 504):                         # the front face
        v = (y - 472) / 32.0
        c.hline(702, 738, y, C("151d28") if v < 0.72 else C("10141f"))
    for k in range(9):                                # the return face
        c.vline(738 + k, 472 - k, 504 - k, C("10141f") if k < 6 else C("090a14"))
    c.vline(702, 472, 503, C("090a14"))
    c.hline(702, 738, 503, C("090a14"))
    for k in range(26):                               # the pressed-in x brace
        c.set(707 + k, 478 + k // 2, C("10141f"))
        c.set(707 + k, 477 + k // 2, C("202e37"))
        c.set(733 - k, 478 + k // 2, C("10141f"))
        c.set(733 - k, 477 + k // 2, C("202e37"))
    c.rect(722, 466, 730, 470, C("394a50"))           # the cap
    c.set(722, 466, C("577277"))
    for k in range(13):                               # and the carry handle
        c.set(706 + k, 466 - k // 6, C("394a50"))
        c.set(706 + k, 467 - k // 6, C("202e37"))
    for k in range(2):                                # solid rust, never dots.
        for (qx, qy) in blob(rng, rng.randrange(708, 732),   # two patches, not
                             rng.randrange(490, 500),        # three: at 602c2c
                             rng.randint(9, 22),             # they read as a
                             {(x, y) for y in range(482, 503)  # red scrawl
                              for x in range(703, 738)}):
            c.set(qx, qy, C("602c2c") if k else C("341c27"))
    c.hline(700, 748, 504, C("090a14"))               # its contact shadow
    c.hline(704, 744, 505, C("090a14"))


# ============================================ the window and its interior ====
def _interior(c: Canvas, rng: random.Random) -> None:
    # board wall: brightest at counter level, falling off UPWARD — the
    # inverse of every other surface in the game.
    #
    # IT IS WARM ALL THE WAY UP. An earlier cut banded the top of the wall
    # cold and let the lamp's wash take over lower down; the meeting line
    # swept across the whole window and read as a horizon, not as light. The
    # only light in this room is the lamp, so the only ladder in here is the
    # warm one. Cold survives on the frame, the pane and the tally highlights.
    for y in range(OPEN_T, OPEN_B):
        t = (y - OPEN_T) / float(OPEN_B - OPEN_T)
        for x in range(OPEN_L, OPEN_R):
            lv = 0.35 + t * 3.1 - abs(x - 668) / 620.0
            lv += 0.30 * math.sin(x / 37.0 + 0.8) + 0.20 * math.sin(x / 17.0)
            lv += 0.12 * math.sin(y / 21.0)
            c.set(x, y, warm(max(0, min(3, int(lv)))))
    # board joints — structural texture, wavy so they never read as a grid
    jx = OPEN_L + 9
    while jx < OPEN_R - 6:
        for y in range(OPEN_T, OPEN_B):
            c.set(jx + int(1.4 * math.sin(y / 41.0)), y,
                  bump(c.get(jx, y), -1))
        jx += rng.randint(26, 44)
    # a hotter core right behind the ledger — the wash is BAKED SOLID and
    # BANDED (den candle precedent) so a breathing soft-alpha glow can sit on
    # top later without doubling up. Capped at 884b2b: the wall must stay
    # darker than his lit jaw or the face stops separating from it.
    for y in range(286, OPEN_B):
        for x in range(OPEN_L, 780):
            d = abs(x - 664) / 128.0 + (OPEN_B - y) / 68.0
            d += 0.10 * math.sin(x / 23.0) + 0.07 * math.sin(y / 9.0)
            if d < 1.0:
                c.set(x, y, C("884b2b") if d > 0.45 else C("ad7757"))
    _tallies(c, rng)


# --------------------------------------------------------------- the count ----
# CANON: EXACTLY 83 MARKS — sixteen gates of five, plus three loose. A "gate"
# is the standard tally five: four uprights and one diagonal struck through
# them, so 16 x 5 = 80, and 3 single uprights makes 83. The number lives in
# LORE.md section 7a ("THE TALLY IS CLOSED") and it is THE SAME NUMBER on the
# den's wall — the two paintings must agree, because the player zooms in.
# The count below is built from an explicit plan and then counted from what
# was actually DRAWN, and the assert at the end crashes the module rather
# than letting it drift if anyone edits this.
GATES = 16
LOOSE = 3
TALLY_CANON = GATES * 5 + LOOSE          # 83

# HIS handwriting. The den's wall is six years of different hands in the
# dark; this is one man with a system and a straight edge, so the rows are
# RULED — one ladder of baselines shared by both panels — the uprights sit on
# an exact 4px pitch, and every diagonal is struck at the same 2:1 slope.
# The per-stroke jitter is deliberately one pixel and no more: enough that a
# hand is visible, never enough to read as scatter. (An earlier brief asked
# for these to be "fewer and more varied"; that is wrong for him — his own
# line in scripts/toll_dialog.gd is "better handwriting".)
ROW_Y = (205, 222, 239, 256, 273)        # the ruling, shared by both panels
STROKE_H = 11
UP_PITCH = 4                             # gap between uprights
GATE_PITCH = 21                          # gap between gates on a row
LEFT_X = 626                             # the narrow strip beside his ear
RIGHT_X = 712                            # the open panel past his shoulder


def _chalk_stroke(c: Canvas, rng: random.Random, x: int, y: int, h: int) -> None:
    """one upright. Pressed hardest where the stick lands, lifting off at the
    bottom, with at most a single 1px kink partway down — that is what makes
    it a hand and not a stamp."""
    lean = rng.choice((-1, 0, 0, 0, 1))
    kink = rng.randint(4, max(5, h - 2))
    for k in range(h):
        xx = x + (lean if k >= kink else 0)
        col = cold(6)
        if k == 0:
            col = cold(7)                # the press
        elif k >= h - 2:
            col = cold(5)                # the lift
        c.set(xx, y + k, col)


def _gate(c: Canvas, rng: random.Random, gx: int, gy: int,
          uprights: int, struck: bool) -> int:
    """draws one group and RETURNS THE NUMBER OF MARKS IT DREW. The total is
    counted from this, never from arithmetic, so the canon 83 cannot drift
    apart from the picture."""
    marks = 0
    first = last = None
    for i in range(uprights):
        x = gx + i * UP_PITCH
        y = gy + rng.randint(-1, 1)
        h = STROKE_H + rng.randint(-1, 1)
        _chalk_stroke(c, rng, x, y, h)
        if first is None:
            first = x
        last = x
        marks += 1
    if struck:
        # THE ANGLE IS FIXED — 13 up over 16 across, on every gate on the
        # wall. Jittering the two ends independently would swing it several
        # degrees a gate and undo the whole point of him; the roll shifts the
        # WHOLE line by a pixel instead, which is what a steady hand does.
        #
        # TWO THINGS THE RENDER TAUGHT HERE, do not flatten them back:
        # a shallower strike (8 over 16) steps two pixels sideways per row,
        # which is exactly the gap between uprights, so it stopped reading as
        # a diagonal and read as a HORIZONTAL bar — three of the sixteen
        # gates came out as an "H". And the step must be integer division:
        # round() on this line is banker's rounding, and every .5 flipped by
        # parity, so the staircase came out in ragged runs of 1 and 3.
        j = rng.randint(-1, 1)
        ax, ay = first - 2, gy + STROKE_H + 1 + j
        bx = last + 2
        span = bx - ax
        drop = STROKE_H + 2
        for k in range(span + 1):
            yy = ay - (drop * k + span // 2) // span
            c.set(ax + k, yy, cold(7) if k == 0 else cold(6))
        marks += 1
    return marks


def _tallies(c: Canvas, rng: random.Random) -> None:
    """the closed ledger, chalked on the WARM TIMBER ONLY.

    USER CALL: "can you make the tallies on the wardens screen go on the wood,
    not the gray thing, looks a bit off". Every mark used to be spread across
    the whole opening, which put clusters behind the glass, on the grey steel
    panel and over the fuse box — you do not chalk a cabinet. All 83 now sit
    on the two pieces of bare board he can actually reach: the strip beside
    his ear (x 619-648) and the open panel past his right shoulder
    (x 712-770). Both were measured against his silhouette and against his
    cast shadow, which reaches x 705 at its furthest.

    The button band (x 400-560, y 290-390) is nowhere near this — the booth's
    front face does not start until x 568."""
    _burn_old_stream(rng)
    r = random.Random("spoils:pitch:warden:tally")

    # the patch of wall that was rollered grey when the fuse box went in. It
    # stays, but nothing is chalked on it any more: that panel is the reason
    # this half of the room is bare.
    for py in range(238, 282):
        wobx = int(3.0 * math.sin((py - 238) / 9.0))
        for px in range(796 + wobx, 848 - wobx):
            c.set(px, py, C("394a50") if py < 270 else C("202e37"))

    # THE PLAN. Four ruled rows of one gate down the narrow strip, four ruled
    # rows of three gates across the open panel, and the row he never
    # finished: three uprights with no diagonal through them, because the
    # fourth raider of that week never went in.
    plan = []
    for row in range(4):
        plan.append((LEFT_X, ROW_Y[row], 4, True))
    for row in range(4):
        for k in range(3):
            plan.append((RIGHT_X + k * GATE_PITCH, ROW_Y[row], 4, True))
    plan.append((RIGHT_X, ROW_Y[4], LOOSE, False))

    marks = 0
    for (gx, gy, ups, struck) in plan:
        marks += _gate(c, r, gx, gy, ups, struck)

    # canon, and it lives in LORE.md 7a. CRASH rather than drift.
    assert marks == 83, "tally must be exactly 83 (canon, LORE.md 7a)"
    assert marks == TALLY_CANON


def _burn_old_stream(rng: random.Random) -> None:
    """THE SHARED RNG IS A COST, NOT A SOURCE. His face, the ledger's figures,
    the counter's wear and the boom all draw from this same stream after the
    interior is painted, so spending a different number of rolls in here
    silently re-rolls every one of them. CLAUDE.md's rule is to take the roll
    and throw it away: this replays the EXACT draw sequence the pre-canon
    tally spent — 106 of them, in an order fixed by that revision's group
    structure and never by an outcome — and the real work runs on its own
    stream. Delete this and the rest of the picture changes."""
    def old_group(n: int) -> None:
        for _ in range(n):
            rng.randint(10, 17)
            rng.randint(-2, 2)
            rng.randint(4, 6)
        if n >= 5:
            rng.random()
        rng.randint(7, 13)

    for n in (5, 3):                     # the two crisp groups by his ear
        old_group(n)
        rng.randint(30, 38)
    for n in (5, 5, 5, 2):               # the four that sat behind the glass
        rng.randint(-3, 3)
        rng.randint(-2, 2)
        old_group(n)
    rng.randint(-2, 2)                   # the one that cleared the fuse box
    old_group(3)


def _glass(c: Canvas, rng: random.Random) -> None:
    """the sliding pane, pushed right. Sheen is two solid diagonal bands of
    different width — a single band reads as a stripe."""
    for y in range(OPEN_T, OPEN_B):
        for x in range(PANE_X, OPEN_R):
            c.set(x, y, bump(c.get(x, y), -1))
    for (x0, wdt, slope) in ((PANE_X + 14, 26, 0.42), (PANE_X + 58, 11, 0.42)):
        for y in range(OPEN_T, OPEN_B):
            sx = int(x0 + (y - OPEN_T) * slope)
            for k in range(wdt):
                if PANE_X <= sx + k < OPEN_R:
                    c.set(sx + k, y, bump(c.get(sx + k, y), 1))
            # the leading edge steps one further UP ITS OWN LADDER; a fixed
            # 577277 line here read as a crack across the glass
            if PANE_X <= sx < OPEN_R:
                c.set(sx, y, bump(c.get(sx, y), 1))
    # the fuse box behind the glass, baked UNLIT (its LED is a living-layer
    # element and must not be painted on)
    c.rect(800, 258, 820, 276, C("151d28"))
    c.rect(802, 260, 818, 274, C("10141f"))
    c.hline(802, 818, 260, C("394a50"))
    c.set(810, 268, C("341c27"))
    c.vline(810, 276, 292, C("090a14"))
    # the pane's leading edge
    for y in range(OPEN_T, OPEN_B):
        c.vline(PANE_X, y, y, C("819796") if y < 280 else C("a8b5b2"))
        c.vline(PANE_X + 1, y, y, C("577277"))
        c.vline(PANE_X + 2, y, y, C("394a50"))
        c.vline(PANE_X + 3, y, y, C("202e37"))
        c.vline(PANE_X + 4, y, y, C("151d28"))


def _surround(c: Canvas, rng: random.Random) -> None:
    """THE PICTURE'S THESIS, on one object: the steel surround is lit COLD
    from above by the booth's shift light and WARM from below by the desk
    lamp, and the 6px inner reveal is where they meet."""
    # outer frame
    for x in range(OPEN_L - 6, OPEN_R + 7):
        for y in range(OPEN_T - 6, OPEN_T):
            c.set(x, y, C("819796") if y < OPEN_T - 3 else C("577277"))
    for y in range(OPEN_T - 6, OPEN_B + 7):
        for x in range(OPEN_L - 6, OPEN_L):
            c.set(x, y, C("819796") if x < OPEN_L - 3 else C("577277"))
        for x in range(OPEN_R + 1, OPEN_R + 7):
            c.set(x, y, C("394a50") if x > OPEN_R + 3 else C("202e37"))
    for x in range(OPEN_L - 6, OPEN_R + 7):
        for y in range(OPEN_B + 1, OPEN_B + 7):
            c.set(x, y, C("394a50") if y > OPEN_B + 3 else C("202e37"))
    c.hline(OPEN_L - 7, OPEN_R + 7, OPEN_T - 7, C("090a14"))
    c.vline(OPEN_L - 7, OPEN_T - 7, OPEN_B + 7, C("090a14"))
    c.vline(OPEN_R + 7, OPEN_T - 7, OPEN_B + 7, C("090a14"))
    # the warm reveal: the top reveal FACES DOWN, so the lamp owns it
    for x in range(OPEN_L, OPEN_R):
        t = max(0.0, min(1.0, (x - OPEN_L) / 210.0))
        for y in range(OPEN_T, OPEN_T + 6):
            k = 4 - int(t * 2.4) - (1 if y < OPEN_T + 2 else 0)
            c.set(x, y, warm(max(1, k)))
    for y in range(OPEN_T, OPEN_B):
        t = (y - OPEN_T) / float(OPEN_B - OPEN_T)
        for x in range(OPEN_L, OPEN_L + 6):
            c.set(x, y, warm(max(1, int(1.6 + t * 2.6))))
        for x in range(OPEN_R - 5, OPEN_R):
            c.set(x, y, warm(max(1, int(0.9 + t * 1.5))))


# =============================================================== the man ====
def _warden(c: Canvas, rng: random.Random) -> None:
    """Draws him on a scratch canvas, throws HIS OWN CAST SHADOW onto the
    board wall first, then composites him over it.

    The shadow is not decoration — without it his warm-lit jaw sat directly
    against the warm-washed wall and the head stopped separating at all. A
    close light below-left throws the shadow up and to the RIGHT, so that is
    where it goes, in two solid steps, clipped to the window opening."""
    s = Canvas(SCENE_W, SCENE_H)
    _warden_figure(s, rng)
    # each pass steps the wall DOWN ITS OWN LADDER rather than stamping a
    # fixed brown: painted flat it read as a cloak thrown round his shoulders,
    # because a warm 341c27 over the cold upper wall is not a shadow, it is
    # a different object.
    # HEAD AND CAP ONLY. Projecting the shoulders too threw a pair of huge
    # brown wings across the whole interior that read as a cloak — and it
    # darkened exactly the strip of wall his dark tunic has to silhouette
    # against, so the shoulders disappeared.
    for (ox, oy) in ((7, -8), (3, -4)):
        for y in range(196, 292):
            for x in range(630, 730):
                if s.get(x, y)[3] == 0:
                    continue
                px, py = x + ox, y + oy
                if OPEN_L <= px < OPEN_R and OPEN_T <= py < OPEN_B:
                    c.set(px, py, bump(c.get(px, py), -1))
    for y in range(190, 350):
        for x in range(596, 806):
            p = s.get(x, y)
            if p[3]:
                c.set(x, y, p)


def _warden_figure(c: Canvas, rng: random.Random) -> None:
    """46px of face, lit from BELOW by the ledger lamp. Bands run: peak
    shadow (near black) -> brow -> cheeks -> lit jaw -> hot chin rim."""
    # ---- tunic and shoulders (drawn first, the head sits over the neck) ----
    for y in range(286, 344):
        t = (y - 286) / 20.0
        hl = 12 + int(min(1.0, t) * 34)          # his right shoulder, lower
        hr = 12 + int(min(1.0, (y - 280) / 18.0) * 50)   # elbow side, higher
        hr = min(hr, 62)
        for x in range(CX - hl, CX + hr + 1):
            dx = x - CX
            lv = 2
            if y > 296:
                lv = 3
            if y > 308:
                lv = 4
            if y > 318:
                lv = 5
            if dx > hr - 12:
                lv -= 1
            if dx > hr - 5:
                lv -= 1
            if dx < -hl + 4:
                lv -= 1
            lv += int(0.6 * math.sin(x / 19.0 + y / 47.0))
            c.set(x, y, cold(max(1, lv)))
    # folds — rolled positions, never evenly spaced
    fx = CX - 40
    while fx < CX + 56:
        fx += rng.randint(13, 24)
        ln = rng.randint(14, 30)
        y0 = rng.randint(304, 318)
        for y in range(y0, min(340, y0 + ln)):
            c.set(fx + int(1.6 * math.sin(y / 13.0)), y, C("202e37"))
            c.set(fx + 1 + int(1.6 * math.sin(y / 13.0)), y, C("151d28"))
    # neck — the chin blocks most of the up-light, so it stays low on the
    # ladder. Lit as brightly as the jaw it read as a beard.
    for y in range(282, 308):
        for x in range(CX - 11, CX + 12):
            t = (y - 282) / 26.0
            lv = 1 + int(t * 1.7)
            if x > CX + 6:
                lv -= 1
            c.set(x, y, skin(max(0, lv)))
    # collar, open, catching the ledger bounce on its underside
    for k in range(17):
        for j in range(4):
            c.set(CX - 11 - k + j, 296 + k, C("577277") if j < 2 else C("394a50"))
            c.set(CX + 11 + k - j, 298 + k, C("394a50") if j else C("577277"))
        c.set(CX - 11 - k, 299 + k, C("ad7757"))
        c.set(CX + 11 + k, 301 + k, C("884b2b"))
        c.set(CX - 12 - k, 296 + k, C("202e37"))
        c.set(CX + 12 + k, 298 + k, C("202e37"))
    c.rect(CX - 30, 306, CX - 27, 309, C("de9e41"))       # the one collar pin
    c.set(CX - 30, 306, C("e8c170"))
    c.set(CX - 27, 309, C("884b2b"))

    # ---- the arm on the counter (elbow up, forearm coming at you) ----
    for y in range(292, 336):
        t = (y - 292) / 44.0
        x0 = CX + 30 + int(t * 12)
        x1 = CX + 62 + int(t * 8)
        for x in range(x0, x1):
            lv = 2 + int(t * 3.2)
            if x > x1 - 6:
                lv -= 1
            c.set(x, y, cold(max(1, lv)))
        c.set(x0 - 1, y, C("090a14"))
        c.set(x1, y, C("090a14"))
    for k in range(36):                                    # frayed cuff — six
        x = CX + 36 + k                                    # years of it
        h = 320 + rng.randint(0, 3)
        c.vline(x, 312, h, C("394a50"))
        c.set(x, 311, C("577277"))
        c.set(x, h + 1, C("202e37"))

    # ---- the head ----
    # THE UNDER-LIGHT, in five skin tones. Read it bottom-up: chin hottest,
    # then the lit jaw, the cheeks, the brow in shadow, and near-black under
    # the peak. Every band edge is wobbled per-x so no boundary is a stripe.
    def face_w(y: int) -> int:
        if y <= 250:
            return 13 + (y - 238) // 2
        if y <= 274:
            return 19
        # a ROUNDED chin. A straight taper left the bottom rows flat, and a
        # flat hot rim across them read as a bib.
        return int(19 * math.sqrt(max(0.0, 1.0 - ((y - 274) / 19.0) ** 2)))

    # SIX steps bottom-to-top. The first cut used five and the jumps read as
    # hard stripes; e7d5b3 is held back for a 2px rim on the chin's contour,
    # because as a whole band it read as a pale goatee.
    BANDS = ((252, 0), (260, 1), (268, 2), (277, 3), (286, 4))
    for y in range(238, 293):
        w = face_w(y)
        if w < 1:
            continue
        for x in range(CX - w, CX + w + 1):
            dx = x - CX
            yy = y + int(1.3 * math.sin(dx / 12.0 + 0.4)
                         + 0.7 * math.sin(dx / 5.0))
            lv = 5
            for (edge, band) in BANDS:
                if yy < edge:
                    lv = band
                    break
            if dx > w - 4:                     # the lamp is down-LEFT of him
                lv -= 1
            if dx < -w + 2:
                lv -= 1
            c.set(x, y, skin(max(0, lv)))
    for y in range(282, 293):                  # the chin's hot rim, FOLLOWING
        w = face_w(y)                          # the jaw contour
        if w < 1:
            continue
        for k in range(3):
            c.set(CX - w + k, y, skin(6 if k < 2 else 5))
            c.set(CX + w - k, y, skin(5 if k else 6))
    # ears — only their lobes come round far enough to catch anything
    for (ex, sgn) in ((CX - 20, -1), (CX + 20, 1)):
        for y in range(258, 273):
            for k in range(4):
                c.set(ex + sgn * k, y, skin(1 if y < 266 else 2))
        c.set(ex + sgn * 2, 271, skin(3))
        c.set(ex + sgn * 3, 270, skin(3))
    # brow ridge underside — the one lit thing inside the shadow zone
    for x in range(CX - 17, CX + 18):
        yy = 251 + int(1.3 * math.sin((x - CX) / 11.0))
        c.set(x, yy, skin(1))
        c.set(x, yy - 1, skin(0))
    # THE EYES. The peak blacks them out; only the wet lower lids survive.
    for ox in (CX - 16, CX + 5):
        for y in range(247, 256):
            for x in range(ox, ox + 11):
                if y == 247 and (x == ox or x == ox + 10):
                    continue
                c.set(x, y, C("241527"))
        c.hline(ox + 3, ox + 7, 254, C("819796"))       # lower-lid catch
        c.set(ox + 4, 255, C("a8b5b2"))
        c.set(ox + 5, 255, C("a8b5b2"))
        c.hline(ox + 2, ox + 8, 253, C("090a14"))       # the pupil above it
        c.hline(ox + 1, ox + 9, 256, skin(2))           # lower lid
    # nose: the bridge faces UP so it is the darkest thing on the face; the
    # septum underneath is the second-brightest.
    for y in range(256, 272):
        t = (y - 256) / 16.0
        wdt = 2 + int(t * 4)
        for x in range(CX - wdt, CX + wdt + 1):
            c.set(x, y, skin(0 if y < 266 else 1))
    for k in range(11):                                 # the lit septum
        u = abs(k - 5) / 5.0
        c.set(CX - 5 + k, 271 - int(u * 1.4), skin(5))
        c.set(CX - 5 + k, 272 - int(u * 1.4), skin(4))
    c.rect(CX - 7, 269, CX - 5, 271, C("341c27"))       # nostrils
    c.rect(CX + 5, 269, CX + 7, 271, C("341c27"))
    # mouth — the LEFT corner one pixel lower, on purpose. A man who has
    # said no ten thousand times.
    for x in range(CX - 11, CX + 11):
        drop = 1 if x < CX - 6 else 0
        c.set(x, 278 + drop, C("4d2b32"))
        c.set(x, 279 + drop, C("341c27"))
    for k in range(17):                                 # lower lip, lit and
        u = abs(k - 8) / 8.0                            # tapered, not a bar
        if u > 0.80:
            continue
        c.set(CX - 8 + k, 281 + int(u * 1.6), skin(5))
        c.set(CX - 8 + k, 282 + int(u * 1.6), skin(4))
    c.set(CX - 12, 279, skin(1))
    c.set(CX + 11, 278, skin(1))
    # jaw crease
    for k in range(11):
        c.set(CX - 13 - k // 3, 272 + k, skin(2))
        c.set(CX + 13 + k // 3, 272 + k, skin(1))

    # ---- the cap. A PEAKED CAP flares WIDE at the top and sits SHORT; the
    # first two cuts made it tall and near-vertical and it read as a top hat.
    def crown_w(y: int) -> int:
        w = 25 - int((y - 210) * 0.14)
        if y < 215:
            w -= int((215 - y) ** 1.7 * 0.55)
        return w

    for y in range(210, 235):
        w = crown_w(y)
        if w < 2:
            continue
        if y < 218:
            col = C("151d28")
        elif y < 227:
            col = C("172038")
        else:
            col = C("253a5e")
        for x in range(CX - w, CX + w + 1):
            cc = col
            if x > CX + w - 5:
                cc = bump(cc, -1)
            c.set(x, y, cc)
        # THE COLD RIM, and it follows the silhouette exactly — drawn as a
        # flat bar it read as a second hat band floating over the crown.
        c.set(CX - w, y, C("3c5e8b") if y < 222 else C("253a5e"))
        c.set(CX - w + 1, y, C("253a5e"))
        c.set(CX + w, y, C("172038"))
    for y in range(209, 216):                          # the crown's top edge
        for x in range(CX - crown_w(y), CX + crown_w(y) + 1):
            if crown_w(y - 1) < 2 or abs(x - CX) > crown_w(y - 1):
                c.set(x, y, C("3c5e8b"))
                c.set(x, y + 1, C("253a5e"))
    for y in range(235, 240):                          # the band
        for x in range(CX - 22, CX + 23):
            c.set(x, y, C("172038") if y < 238 else C("253a5e"))
    c.rect(CX - 5, 235, CX + 4, 237, C("884b2b"))      # badge, DULL: it is
    c.hline(CX - 5, CX + 4, 237, C("be772b"))          # above the peak, so the
    c.set(CX - 5, 235, C("602c2c"))                    # lamp cannot reach it
    c.set(CX + 4, 235, C("602c2c"))
    c.set(CX - 1, 236, C("602c2c"))
    for x in range(CX - 26, CX + 27):                  # the peak
        t = (x - CX) / 26.0
        d = int(5 * math.sqrt(max(0.0, 1.0 - t * t)))
        for y in range(239, 241 + d):
            c.set(x, y, C("090a14"))
        c.set(x, 239, C("151d28"))
        if d > 0:
            c.set(x, 240 + d, C("341c27"))             # lamp on the visor lip
        if d > 3:
            c.set(x, 240 + d, C("602c2c"))


# =============================================================== counter ====
def _counter(c: Canvas, rng: random.Random) -> None:
    """iso top face (a parallelogram, never a front-on rectangle), a front
    edge, and a hard shadow under it."""
    # the contact shadow where the shelf meets the board wall — without it
    # the top face and the lamp-lit wall behind it are the same warm value
    # and the shelf stops being a separate plane
    for x in range(OPEN_L, min(OPEN_R, 890)):
        yf = CNT_Y + int((x - 588) * 0.018)
        c.set(x, yf - 2, C("602c2c"))
        c.set(x, yf - 1, C("341c27"))
    for k in range(11):
        xs = 9 - k
        for x in range(586 + xs, 890 + xs):
            y = CNT_Y + int((x - xs - 588) * 0.018) + k
            d = ((x - 660) / 190.0) ** 2 + ((k - 3) / 22.0) ** 2
            lv = 3 if d < 0.30 else (2 if d < 0.72 else 1)
            if k > 7:
                lv -= 1
            c.set(x, y, warm(max(1, lv + 1)))
    for x in range(586, 890):
        yf = CNT_Y + int((x - 588) * 0.018)
        for y in range(yf + 11, yf + 23):
            t = (y - yf - 11) / 12.0
            c.set(x, y, C("602c2c") if t < 0.55 else C("4d2b32"))
        for y in range(yf + 23, yf + 29):
            c.set(x, y, C("341c27"))
        c.set(x, yf + 29, C("241527"))
    # three worn-through patches in the top face, different sizes
    region = {(x, y) for y in range(CNT_Y, CNT_Y + 16) for x in range(590, 886)}
    for i in range(3):
        for (qx, qy) in blob(rng, rng.randrange(600, 870),
                             CNT_Y + rng.randrange(2, 9),
                             rng.randint(14, 46), region):
            c.set(qx, qy, C("ad7757") if i != 1 else C("c09473"))
    # TWO DIFFERENT BRACKETS — one welded properly, one bodged
    for y in range(360, 392):                          # welded gusset
        w = int((392 - y) * 0.62)
        for x in range(628, 628 + w):
            c.set(x, y, C("202e37") if x < 628 + w - 3 else C("151d28"))
    c.vline(628, 358, 392, C("394a50"))
    c.hline(626, 640, 358, C("394a50"))
    c.hline(626, 640, 359, C("202e37"))
    for y in range(358, 402):                          # bodged pipe, leaning
        dx = int((y - 358) * 0.22)
        c.vline(824 + dx, y, y, C("394a50"))
        c.vline(825 + dx, y, y, C("577277"))
        c.vline(826 + dx, y, y, C("394a50"))
        c.vline(827 + dx, y, y, C("202e37"))
        c.vline(828 + dx, y, y, C("151d28"))
        if 372 < y < 386:
            c.vline(825 + dx, y, y, C("884b2b"))
            c.vline(826 + dx, y, y, C("602c2c"))
    c.rect(818, 356, 834, 359, C("202e37"))            # the bodge plate
    c.hline(818, 834, 356, C("394a50"))
    # a dented tin cup with its ring stain
    yb = CNT_Y + int((846 - 588) * 0.018)
    for y in range(yb - 17, yb + 4):
        t = (y - (yb - 17)) / 21.0
        w = 8 - int(t * 2)
        for x in range(846 - w, 846 + w):
            lv = 4 if x < 846 - w + 4 else 3
            if x > 846 + w - 3:
                lv = 2
            if y > yb - 4:
                lv -= 1
            c.set(x, y, cold(max(1, lv)))
    c.hline(839, 853, yb - 17, C("819796"))
    c.set(842, yb - 10, C("202e37"))                   # the dent
    c.set(843, yb - 9, C("202e37"))
    c.set(842, yb - 9, C("151d28"))
    for k in range(24):                                # ring stain
        a = k / 24.0 * math.tau
        c.set(int(846 + math.cos(a) * 12), int(yb + 3 + math.sin(a) * 4),
              C("602c2c"))


def _lamp_and_ledger(c: Canvas, rng: random.Random) -> None:
    """THE LIGHT SOURCE, VISIBLE — and the bounce card under his chin.
    Lamp x 612-646, ledger x 650-714, hand x 714-758: three lanes, no
    overlap (the brief had the first two sharing coordinates)."""
    # ---- the open ledger, an ISO PARALLELOGRAM lying on the counter ----
    for k in range(34):
        y = 298 + k
        sh = int(k * 0.46)
        x0, x1 = 650 - sh, 714 - sh
        for x in range(x0, x1):
            t = (x - x0) / float(x1 - x0)
            band = 6
            if t > 0.42 + 0.05 * math.sin(k / 6.0):
                band = 5
            if t > 0.74 + 0.04 * math.sin(k / 4.0):
                band = 4
            if k > 27:
                band -= 1
            c.set(x, y, warm(max(2, band)))
        mid = x0 + int((x1 - x0) * 0.5)
        c.set(mid, y, C("c09473"))                     # the spine
        c.set(mid + 1, y, C("ad7757"))
    for k in range(5):                                 # ruled lines
        for j in range(28):
            y = 302 + j
            sh = int(j * 0.46)
            c.set(650 - sh + 6 + k * 12, y, C("819796"))
    for row in range(7):        # two columns of figures — ROLLED word runs.
        y = 304 + row * 4       # a fixed modulo made it read as lace.
        sh = int((y - 298) * 0.46)
        for (cx0, cw) in ((655, 24), (685, 22)):
            x = cx0 - sh + rng.randint(0, 3)
            end = cx0 - sh + cw
            while x < end:
                run = rng.randint(3, 7)
                for k in range(min(run, end - x)):
                    c.set(x + k, y + (1 if math.sin((x + k) * 1.9) > 0.2 else 0),
                          C("4d2b32"))
                x += run + rng.randint(2, 4)
    for k in range(30):                                # the pen laid across it
        x = 654 + k
        y = 322 - int(k * 0.32)
        c.set(x, y, C("202e37") if k > 4 else C("577277"))
        c.set(x, y + 1, C("151d28"))
    c.set(683, 313, C("819796"))
    for (tx, ty) in ((702, 318), (703, 319), (704, 318), (703, 317),
                     (702, 320), (704, 320)):
        c.set(tx - 9, ty, C("7a4841"))                 # one thumb smudge
    for x in range(646, 716):                          # shadow under the pages
        y = 332 - int((x - 646) * 0.0)
        c.set(x, 332, C("341c27"))
        c.set(x, 333, C("241527"))

    # ---- the desk lamp. The bulb is never visible: only the shade and the
    # pool, so nothing has to blow out. Baked UNLIT-HOT: the a8ca58 rim is
    # the glass, not a glow, so an additive breathing overlay can sit on top.
    for k in range(20):
        y = 288 + k
        w = 5 + k
        x0 = 628 - w
        x1 = 628 + w - int(k * 0.55)
        for x in range(x0, x1):
            t = (x - x0) / float(max(1, x1 - x0))
            col = C("25562e")
            if t < 0.30:
                col = C("468232")
            if t < 0.12:
                col = C("75a743")
            if k > 15:
                col = C("19332d")
            c.set(x, y, col)
    for x in range(608, 646):                           # the hot lower rim
        if 608 <= x < 648:
            c.set(x, 308, C("a8ca58"))
            c.set(x, 309, C("468232"))
            c.set(x, 310, C("25562e"))
    c.hline(614, 642, 307, C("d0da91"))
    for y in range(310, 330):                           # brass neck
        dx = int((y - 310) * 0.25)
        c.vline(626 + dx, y, y, C("de9e41"))
        c.vline(627 + dx, y, y, C("be772b"))
        c.vline(628 + dx, y, y, C("884b2b"))
    for k in range(6):                                  # base
        c.hline(616 + k, 644 - k, 330 + k, C("884b2b") if k < 3 else C("602c2c"))
    c.hline(618, 642, 329, C("be772b"))
    # its cable, run down behind the counter (powered things show their wire)
    for y in range(330, 348):
        c.set(618 + int(2.0 * math.sin((y - 330) / 5.0)), y, C("241527"))


def _hand(c: Canvas, rng: random.Random) -> None:
    """palm up, fingers curled, waiting for the thirty. The brightest small
    shape in the frame after the lamp glass."""
    # A CUPPED PALM, not a row of columns. The first render drew four tall
    # rounded fingers standing above the palm and they read as bottles: the
    # fingers are CURLED TOWARD YOU, so they are short knuckle ridges along
    # the far edge and the palm is a hollow with a lit near rim.
    for y in range(318, 342):
        t = (y - 318) / 24.0
        half = int(18 * math.sqrt(max(0.0, 1.0 - (t - 0.45) ** 2 / 0.30)))
        if half < 3:
            continue
        cx0 = 734 + int(t * 3)
        for x in range(cx0 - half, cx0 + half):
            dx = (x - cx0) / float(half)
            dy = (y - 331) / 11.0
            hollow = dx * dx * 0.7 + dy * dy
            # one step below the face: at full frame the first cut out-shone
            # his head and the eye went to the hand instead of the man
            lv = 4
            if hollow < 0.42:
                lv = 2                      # the hollow of the palm
            elif hollow < 0.72:
                lv = 3
            if t > 0.74:
                lv = 5                      # near rim, closest to the lamp
            if dx > 0.62:
                lv -= 1
            c.set(x, y, skin(max(1, lv)))
    # four curled fingers along the FAR edge, rolled widths, no two alike
    fx = 720
    for i in range(4):
        w = rng.randint(7, 10)
        h = rng.randint(3, 5)
        base = 322 + rng.randint(-1, 1)
        for k in range(w):
            u = abs(k - (w - 1) / 2.0) / max(1.0, (w - 1) / 2.0)
            d = int(h * (1.0 - u * u) + 0.5)
            for y in range(base - d, base + 4):
                c.set(fx + k, y, skin(3 if y > base + 1 else 4))
            if d > 0:
                c.set(fx + k, base - d, skin(5))
        c.vline(fx + w, base - 2, base + 5, skin(1))     # the valley between
        c.hline(fx, fx + w, base + 4, skin(1))           # knuckle crease, so
        c.hline(fx, fx + w, base + 5, skin(2))           # the fingers are not
        fx += w + 1                                      # nubs on a bun
    for y in range(330, 344):                            # thumb, near edge
        k = y - 330
        for x in range(710 + k // 3, 726 + k // 2):
            c.set(x, y, skin(4 if x < 718 else 3))
        c.set(710 + k // 3, y, skin(1))
    c.hline(712, 754, 344, C("341c27"))                  # its shadow
    c.hline(716, 748, 345, C("241527"))


# ============================================================== the boom ====
def _boom(c: Canvas, rng: random.Random) -> None:
    """FOREGROUND: near-silhouette, light arriving only as rims. The hard
    090a14 shadow line under its full length is what makes it sit in FRONT
    of the picture rather than on it."""
    # the counterweight post, standing in front of the booth
    for y in range(372, SCENE_H):
        for x in range(866, 893):
            lv = 3 if x < 878 else 2
            if x > 887:
                lv = 1
            c.set(x, y, cold(lv))
        c.set(866, y, C("884b2b"))                       # the window's rake
        c.set(867, y, C("602c2c"))
        c.set(865, y, C("090a14"))
        c.set(893, y, C("090a14"))
    for y in range(500, 528):                            # rust band at the base
        if (y // 4) % 2 == 0:
            c.hline(868, 884, y, C("602c2c"))
            c.hline(870, 880, y + 1, C("341c27"))
    c.hline(864, 894, 372, C("394a50"))
    c.hline(866, 892, 373, C("202e37"))
    # a short arm and THREE cast slabs of different thickness
    for k in range(46):
        c.set(890 + k, 384 - k // 8, C("202e37"))
        c.set(890 + k, 385 - k // 8, C("151d28"))
        c.set(890 + k, 386 - k // 8, C("090a14"))
    sy = 368
    for th in (7, 10, 5):
        c.rect(902, sy, 934, sy + th, C("151d28"))
        c.hline(902, 934, sy, C("202e37"))
        c.hline(902, 934, sy + th, C("090a14"))
        sy += th + 2
    # THE BOOM. Stripes rolled 5-9px, no two equal, and BANDED BY DISTANCE
    # so the red never shouts: cf573c near, a53030 mid, 752438 far.
    seg = []
    x = 868
    flip = 0
    while x > -40:
        ln = rng.randint(5, 9) * 5
        seg.append((x, x - ln, flip))
        x -= ln
        flip ^= 1
    j1 = rng.randint(-14, 14)
    j2 = rng.randint(-14, 14)
    for (xa, xb, fl) in seg:
        for x in range(max(-40, xb), xa):
            if x < 0:
                continue
            y = boom_y(x)
            kink = 3 if 238 < x < 254 else 0
            h = 8 + int((x / 868.0) * 3)
            # BANDED BY DISTANCE, and deliberately never bright: the first
            # render used c7cfcc for the pale stripe and the boom shouted
            # louder than the man's face.
            if x > 620 + j1:
                cols = (C("cf573c"), C("577277"))
            elif x > 300 + j2:
                cols = (C("a53030"), C("394a50"))
            else:
                cols = (C("752438"), C("202e37"))
            col = cols[fl]
            top = int(y) - h // 2 + kink
            for k in range(h):
                cc = col
                if k == 0:
                    cc = bump(col, 1) if fl else bump(col, 1)
                if k > h - 3:
                    cc = bump(col, -1)
                c.set(x, top + k, cc)
            c.set(x, top - 1, C("090a14"))
            c.set(x, top + h, C("090a14"))
            c.set(x, top + h + 1, C("090a14"))
            if x > 560:                                  # window-side rake
                c.set(x, top, C("577277") if fl else C("394a50"))
    # the jersey-barrier stub rooted off the bottom-left corner
    for y in range(470, SCENE_H):
        t = (y - 470) / 74.0
        x1 = int(96 - t * 14)
        for x in range(0, x1):
            c.set(x, y, C("090a14"))
        if y < 486:
            for x in range(0, x1):
                c.set(x, y, C("10141f"))
        c.set(x1, y, C("090a14"))
    c.hline(0, 96, 470, C("202e37"))
    c.hline(0, 94, 471, C("151d28"))
    for k in range(16):
        c.set(88 - k // 2, 472 + k, C("151d28"))


# ================================================================= paint ====
def paint() -> Canvas:
    rng = random.Random("spoils:pitch:warden")
    c = Canvas(SCENE_W, SCENE_H)
    _sky(c, rng)
    _far_ground(c, rng)
    _pole(c, rng)
    _wire(c, rng)
    _tower(c, rng)
    _sign(c, rng)
    _road(c, rng)
    _queue(c, rng)
    _booth(c, rng)
    _interior(c, rng)
    _warden(c, rng)
    _glass(c, rng)
    _surround(c, rng)
    _counter(c, rng)
    _lamp_and_ledger(c, rng)
    _hand(c, rng)
    _boom(c, rng)
    # LAST ON PURPOSE. Both draw only into the flat zenith slab above y 117,
    # and calling them here means they take their rng draws after every other
    # function has taken its own — so not one pixel below the roof line moves.
    _strata(c, rng)
    _mast(c, rng)
    return c


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
