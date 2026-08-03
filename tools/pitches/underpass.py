"""the underpass — transit's road ducking under the rail line, flooded and
never drained: one failing sodium tube on the right, grey daylight in the far
mouth on the left, a car that went in nose first lying half sunk in the near
flood at the bottom left, and the whole picture repeated, broken, in the water.

BACKDROP PITCH - static scene only, no living layer yet. Unwired: nothing
imports this and gen_art.py never emits it. If the user picks this pitch it
gets promoted into gen_art.py proper; if not, this file is deleted.

ROOM LEFT FOR THE LIVING LAYER (not built here, per the brief):
  * the sodium tube is baked at roughly 60% of its contribution — solid
    banded light only.  the additive hot core would sit at (702, 150) and
    the down-left wash at (760, 320) at 300x300, which is the critic's
    corrected size: it cannot reach past x=610 and so never touches the
    buttons.  a dropout removes the top end, never the shape.
  * three ceiling leaks at x = 300, 596 and 736 — chosen so a falling drip
    never crosses the button box.  landing sites: open water (y 406 — this
    said "the car roof (y 338)" until revision 3 moved the car out of that
    column entirely), open water (y 409), the walkway kerb (y 388).
  * the walkway pool and the wall halo are baked here; a breathing glow
    goes on top of them, it does not replace them.
  * the water's dashes are baked at rest.  three (not five) surface strips
    would re-sort the bands under the mouth and under the lamp.

REVISION 2 — WHAT THE USER SAID AFTER LOOKING AT IT, and what was done.  each
of these is FIXED and verified in the render, not planned:
  1. "what is that thing to the right of the door?"  it was a louvred scupper
     with two black stains hanging off it and it read as a smudge.  DELETED.
     in its place: the deck's rainwater downpipe — a stack coming out of the
     soffit, a swan neck, a hopper head, a round pipe with brackets and socket
     collars, and a burst joint that shoves the lower half sideways.  the
     stack above the hopper is load-bearing: without it the cone read as a
     lamp shade on a post.
  2. "the water just looks flat at the doorway."  the flat slab with the
     column of white dashes is gone.  the water in the mouth is a true 1:1
     screen-space mirror about the far waterline at y=262, so the skyline
     lands in its own columns; the tone steps darker forward on wavy seams;
     and each ripple facet is a stroke that grows from 1px tall and tightly
     packed at the far end to 4px tall and widely broken at the near.
  3. "a couple things on top of the water that shouldn't be there."  the
     crate, the drum AND the pallet now float: the waterline cuts each one,
     each leans differently, each pushes a broken ring into the surface and
     drops a broken reflection under itself.  see float_wake().
  4. the flood was a flat 090a14 slab that gave nothing back.  it now carries
     the room's own light, and the tube and the mouth throw specular columns
     down through it — a 1:1 mirror cannot reach either of them.
  5. the sodium halo's concentric rings are broken by a PANEL FIELD: the wall
     is precast, so every panel carries its own tone offset.
  6. the sandbags read as loaves.  rebuilt off a thickness profile pinched at
     both ends, with a real top face and a tied ear.
  7. the top 108px was flat black.  it is a soffit now — girder flanges,
     bracing, one torn brace, leak runs.  still the darkest band in the frame.

REVISION 3 — ONE thing was complained about and ONE thing changed.  the user:
"the thing beside the door ... it kind of looks like the back of a car or
something ... I can't even tell what it is", then "it's more down, towards the
bottom left of the picture, it's like cropped.  That's the car thing I'm
talking about."  FIXED, and it is the only edit in this revision:
  * the car stood at x 202-352 with its front half BEHIND the portal's right
    jamb, so no whole vehicle was ever on screen — hence "cropped".  what was
    left of it was a flat-on rear panel with one lens, no flank, no wheels, no
    bumper and no plate, which at this size is a box.
  * it is rebuilt as a three-quarter rear view standing in the OPEN FLOOD at
    the bottom left, nothing crossing it, water behind it on every side.  real
    box geometry (a near vertical corner, a length axis and a width axis), a
    three-box saloon profile, and the parts that say car: two lamps, a plate
    recess, a bumper with its shadow, arches, handles, a wing mirror over the
    water, a wiper.  it sits to the sills, cut DEAD LEVEL, nothing below.
  * it is drawn at the END of paint(), after the flood, because the water pass
    would otherwise paint straight over it.  its rust roll stays where it
    always was in the seeded stream, so nothing behind it re-rolled: a diff of
    the two renders is empty everywhere except the two car regions and the
    flood columns that used to mirror the old car.
  * the downpipe was NOT touched.  an earlier instruction to delete it was
    withdrawn; it is the wrong object and it stays.

REVISION 4 — ONE thing was complained about and only the CAR changed.  the user:
"The front of the car seems cut off".  they were right, and the reason is worth
keeping: everything forward of the a-pillar was ONE dead-straight 32px diagonal
running from the shoulder to a bare point at the water.  no bonnet top surface,
no wing, no lamp, no bumper — and a long straight edge meeting a flood cannot
read as a waterline, because a waterline is horizontal everywhere.  the eye read
a knife cut.  FIXED in two halves, and it needs both:
  1. ABOVE the water.  the nose drop is 26px on a crowned curve instead of 40px
     on a straight line, so there is a front end left to see: a bonnet TOP PLANE
     four pixels deep whose far edge carries the windscreen base out over the
     nose, a COWL STEP so the bonnet starts below the scuttle instead of flowing
     off it, the near wing with an arch eyebrow, a headlamp and a wrapped front
     bumper — and the waterline cuts all of it DEAD LEVEL at WY, the same line
     the rest of the car is cut on.
  2. BELOW it.  the nose keeps going: a submerged silhouette ahead of and under
     the waterline, no highlight value anywhere in it, holding 202e37 while
     there is still a body to see and then dissolving into the flood's own
     tones, with the surface's LIFT chop running back over the top of it and the
     same broken ring the crate and the drum get where it breaks through.
  three things this took four bakes to learn.  a tapered band above the shoulder
  bulges the silhouette over the scuttle and the whole front reads as a BUBBLE.
  a lamp or a bumper laid parallel to the bonnet is just another rail — they have
  to be LEVEL and cross it.  and a submerged mass painted on the flood's own
  151d28/10141f is drawn and invisible; it has to hold a step above the water it
  is lying in or there is nothing to see.
  the wing mirror moved with it: it used to hang over open water on a long arm
  because the bonnet was under the flood.  the bonnet is not under the flood any
  more, so it is back on the a-pillar, over the wing it is named after — and it
  is a mirror now rather than a near-black box, on a LEVEL arm, with a lit glass
  face inside a housing that is a value above the water.  see the block that
  draws it for why each of those three is load-bearing.
  every roll in the submerged half happens AFTER the last float_wake(), so
  nothing already on the canvas re-rolls.  a pixel diff against the previous
  render is empty outside x 4-135, y 426-498 — the car, its nose and its wake.

CRITIC'S CORRECTIONS APPLIED (see the brief):
  1. the real button box is x 395-565 / y 237-307, ~55px higher than the
     brief planned.  the painted dado moved OFF the buttons entirely, the
     trough clamp re-centred on (480, 300) with half-height 122 so it covers
     y 178-422 (the union of the measured box and the 400-560 / 290-390 band
     this file was commissioned against), and the chalk dog moved down-right
     to (610, 296), clear of both.
  2. the lamp's warm falloff is gated off below x=480 and the walkway stops
     at x=604, so nothing warm and nothing structural enters the box.
  3. the reflection samples with a factor ABOVE 1.0 (2.1), not 0.62 — the
     brief's compression could only ever have reached canvas y 320, so the
     mouth, the sky and the tube could not appear in it at all.  a real
     colour->colour table replaces the undefined "ramp index >= 2" test, and
     colours that map to nothing simply do not reflect, which is what makes
     the car read as a black hole in a pale mirror.
  4/5. no white bakes, no strip canvases, no drip modulate here — this file
     returns one Canvas and nothing else.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gen_art import Canvas, C, SCENE_W, SCENE_H, blob

WATER_Y = 406
WALL_TOP = 100
PANEL_L, PANEL_R = 380, 578          # the cold-forced middle = the button box

# two banded ramps that share their dark end, so the arbitration between the
# two light sources never leaves a seam where they hand over
# the WALL's cold ramp deliberately tops out at 394a50.  577277 and every
# value above it belong to the portal surround and to what is seen through the
# mouth, and to nothing else — that is the palette story, enforced by the ramp
# rather than by good intentions.
COLD = [C("10141f"), C("151d28"), C("202e37"), C("394a50")]
WARM = [C("10141f"), C("151d28"), C("341c27"), C("4d2b32"), C("602c2c"),
        C("7a4841"), C("884b2b")]

# what the flood gives back.  anything not in here does not reflect at all —
# that is deliberate: the sunken car is all near-black, so it prints as a
# hole in the mirror instead of as mush.
REFLECT = {
    C("151d28")[:3]: C("10141f"), C("202e37")[:3]: C("151d28"),
    C("394a50")[:3]: C("202e37"), C("577277")[:3]: C("394a50"),
    C("819796")[:3]: C("577277"), C("a8b5b2")[:3]: C("577277"),
    C("c7cfcc")[:3]: C("819796"), C("ebede9")[:3]: C("a8b5b2"),
    C("341c27")[:3]: C("241527"), C("4d2b32")[:3]: C("341c27"),
    C("602c2c")[:3]: C("341c27"), C("884b2b")[:3]: C("602c2c"),
    C("be772b")[:3]: C("884b2b"), C("de9e41")[:3]: C("be772b"),
    C("e8c170")[:3]: C("be772b"), C("e7d5b3")[:3]: C("de9e41"),
    C("7a4841")[:3]: C("4d2b32"), C("ad7757")[:3]: C("884b2b"),
    C("a53030")[:3]: C("752438"), C("cf573c")[:3]: C("a53030"),
    C("3c5e8b")[:3]: C("253a5e"), C("25562e")[:3]: C("19332d"),
    C("19332d")[:3]: C("19332d"),
}


def paint() -> Canvas:
    rng = random.Random("spoils:pitch:underpass")
    c = Canvas(SCENE_W, SCENE_H)

    # ---------------------------------------------------------------- light --
    def levels(x: int, y: int) -> tuple[float, float]:
        # NEITHER SOURCE IS A POINT, and the first bake proved it: two point
        # falloffs painted two enormous hard-edged discs on a flat wall and
        # the picture read as a room with spotlights.  the mouth is an
        # OPENING, so its distance is to the rectangle of the portal; the tube
        # is a TUBE, so its distance is to a horizontal segment.  the light
        # now hugs the thing making it.
        mdx = max(0.0, abs(x - 192) - 76.0)
        mdy = max(0.0, abs(y - 282) - 92.0)
        lm = max(0.0, 1.0 - (mdx * mdx + mdy * mdy) ** 0.5 / 190.0) ** 1.5
        ldx = max(0.0, abs(x - 702) - 52.0)
        ldy = abs(y - 152) * 1.02
        ll = max(0.0, 1.0 - (ldx * ldx + ldy * ldy) ** 0.5 / 230.0) ** 1.9
        ll *= min(1.0, max(0.0, (x - 545) / 135.0))
        # a two-period wobble so the BAND EDGES are never clean arcs.  it is
        # kept to about 4px of travel: the first pass used ~40px periods with a
        # shallow falloff and turned the seams into enormous amoebas, and the
        # second still scalloped the sodium light into a stain.
        w = (0.012 * math.sin(x / 13.0 + y / 19.0)
             + 0.008 * math.sin(y / 9.0 - x / 23.0))
        # THE TROUGH CLAMP: kills both sources across a wobbled box centred on
        # the real button rect, fading out over ~60px so it is never an edge
        q = trough(x, y)
        f = 1.0 - 0.85 * q
        return max(0.0, lm + w) * f, max(0.0, ll + w) * f

    def trough(x: int, y: int) -> float:
        return max(0.0, 1.0 - max(abs(x - 480) / 168.0,
                                  abs(y - 300 + 4.0 * math.sin(y / 23.0)) / 122.0))

    def wob(x: int, a1: float, p1: float, a2: float, p2: float, ph: float = 0.0):
        return a1 * math.sin(x / p1 + ph) + a2 * math.sin(x / p2 + ph * 1.7)

    # ------------------------------------------------------- the panel field --
    # CRITIC FIX 5: banded radial light on a smooth wall reads as concentric
    # rings, and the wet streaks were never going to be enough on their own.
    # the wall is PRECAST PANELS, so every panel gets its own small tone offset
    # and the ring contours are chopped into a mosaic that reads as concrete
    # instead of as a bullseye.  the offsets have to exist before the fill, so
    # the joint and seam positions are rolled up here rather than at the draw.
    joints = []
    jx = -rng.randint(0, 40)
    while jx < SCENE_W:
        step = rng.randint(96, 140) if PANEL_L - 30 < jx < PANEL_R else rng.randint(44, 68)
        jx += step
        if 0 < jx < SCENE_W:
            joints.append(jx)
    seams = []
    fy = WALL_TOP + rng.randint(18, 30)
    while fy < WATER_Y - 6:
        seams.append((fy, rng.uniform(0.0, 6.0)))
        fy += rng.randint(62, 98)

    col_of = [0] * (SCENE_W + 2)
    ci = 0
    for x in range(SCENE_W + 2):
        while ci < len(joints) and x >= joints[ci]:
            ci += 1
        col_of[x] = ci
    row_of = [0] * (SCENE_H + 2)
    ri = 0
    for y in range(SCENE_H + 2):
        while ri < len(seams) and y >= seams[ri][0]:
            ri += 1
        row_of[y] = ri
    # no two neighbouring panels share an offset, and no offset repeats twice
    # running down a column — a mosaic with duplicates lines up into stripes.
    STEPS = (-0.62, -0.36, -0.14, 0.0, 0.20, 0.44)
    cells = []
    for a in range(len(joints) + 2):
        colv = []
        for b in range(len(seams) + 2):
            ban = {colv[-1] if colv else None,
                   cells[a - 1][b] if a and b < len(cells[a - 1]) else None}
            colv.append(rng.choice([s for s in STEPS if s not in ban]))
        cells.append(colv)

    def wall_col(x: int, y: int, bias: float = 0.0, cold_only: bool = False):
        lm, ll = levels(x, y)
        cb = cells[col_of[max(0, min(SCENE_W + 1, x))]][
            row_of[max(0, min(SCENE_H + 1, y))]] * (1.0 - trough(x, y))
        if ll > lm and not cold_only:
            return WARM[max(0, min(6, int(1.0 + ll * 5.6 + bias + cb + 0.5)))]
        return COLD[max(0, min(3, int(1.0 + lm * 2.4 + bias + cb * 0.55 + 0.5)))]

    # ----------------------------------------------------------- the wall ----
    # the panel is NOT drawn as an object.  a bracketed slab was tried and it
    # read as a roller door hanging in the middle of the tunnel; the middle is
    # simply where neither light reaches, and it is forced cold so not one
    # amber pixel can ever land behind a button.
    for y in range(WALL_TOP, WATER_Y + 10):
        for x in range(SCENE_W):
            inp = PANEL_L <= x <= PANEL_R
            c.set(x, y, wall_col(x, y, 0.0, inp))

    # vertical panel joints: rolled 44-68px, but 96-140px inside the panel so
    # only two land behind the buttons, and drawn one step down there instead
    # of two.
    for jx in joints:
        inside = PANEL_L < jx < PANEL_R
        top = WALL_TOP + rng.randint(4, 14)
        bot = WATER_Y - rng.randint(0, 40)
        for y in range(top, bot):
            wx = jx + int(wob(y, 1.4, 33.0, 0.9, 79.0, jx * 0.01))
            # the joints are cut deeper on the warm side on purpose: banded
            # radial light on smooth concrete reads as a bullseye unless the
            # wall's own structure keeps crossing it.
            c.set(wx, y, wall_col(wx, y, -0.9 if inside else -2.1, inside))

    # horizontal form-board seams, wavy, stopping dead at the panel joints
    for (fy, ph) in seams:
        for x in range(SCENE_W):
            inp = PANEL_L <= x <= PANEL_R
            sy = fy + int(wob(x, 2.4, 47.0, 1.7, 113.0, ph))
            c.set(x, sy, wall_col(x, sy, -0.9 if inp else -1.7, inp))
            c.set(x, sy + 1, wall_col(x, sy + 1, 0.5 if inp else 0.6, inp))

    # recessed form-tie marks, only in the lit right third where they read
    for i in range(6):
        tx = rng.randrange(628, 936)
        ty = rng.randrange(168, 330)
        c.rect(tx, ty, tx + 1, ty + 1, wall_col(tx, ty, -2.5))
        c.hline(tx - 1, tx + 2, ty - 1, wall_col(tx, ty - 1, 1.6))

    # wet streaks running down off the deck line — solid runs, never dots.
    # the extra ones on the right are load-bearing: banded radial light on
    # smooth concrete reads as a bullseye until something keeps crossing it.
    for i in range(34):
        wx = rng.randrange(8, SCENE_W - 8) if i < 15 else rng.randrange(596, 952)
        if PANEL_L - 6 < wx < PANEL_R + 6 or 84 < wx < 300:
            continue
        wy = WALL_TOP + rng.randint(2, 62)
        ln = rng.randint(22, 132)
        wide = ln > 90                    # the long ones run WIDE.  a wall of
        for y in range(wy, min(WATER_Y - 4, wy + ln)):     # 1px lines reads as
            sx = wx + (1 if (y - wy) > ln * 0.7 else 0)    # scratches, which is
            c.set(sx, y, wall_col(sx, y, -1.6))            # a note this file
            if wide and (y - wy) > ln * 0.22:              # has taken before
                c.set(sx + 1, y, wall_col(sx + 1, y, -0.9))
        c.set(wx, min(WATER_Y - 3, wy + ln), C("19332d"))

    # ---------------------------------------------------- the painted dado ---
    # CRITIC FIX 1: this used to be a full-width green stripe at y 254-266,
    # straight through the middle menu button.  it now runs at y 334-348 and
    # stops at both panel joints, so it never enters the box at all.
    # mostly gone: the surviving paint is patches on a ghost of a band, not a
    # green stripe across the frame (the first bake read as a hedge).
    dado_region = set()
    for x in range(SCENE_W):
        if PANEL_L - 2 <= x <= PANEL_R + 2:
            continue
        base = 334 + int(wob(x, 1.8, 53.0, 1.2, 121.0, 1.1))
        for y in range(base, base + 14):
            c.set(x, y, C("19332d"))
            dado_region.add((x, y))
        c.hline(x, x, base, C("10141f"))
    # the surviving paint lives on the COLD side only.  under the sodium light
    # it read as lichen sprouting all over the sandbags, which is one more
    # thing the render told me and the maths could not.
    for i in range(8):
        px = rng.randrange(10, PANEL_L - 20)
        for (qx, qy) in blob(rng, px, rng.randrange(336, 346),
                             rng.randint(20, 54), dado_region):
            c.set(qx, qy, C("25562e"))
    for i in range(15):                     # chipped back to bare concrete
        px = rng.randrange(SCENE_W)
        for (qx, qy) in blob(rng, px, rng.randrange(334, 348),
                             rng.randint(18, 55), dado_region):
            c.set(qx, qy, wall_col(qx, qy))

    # ------------------------------------------------------- the tide line ---
    for x in range(SCENE_W):
        ty = 396 + int(wob(x, 2.0, 37.0, 1.4, 89.0, 2.3))
        c.hline(x, x, ty + 2, C("4d2b32"))
        c.hline(x, x, ty, C("19332d"))
        c.hline(x, x, ty + 1, C("19332d"))
    low = {(x, y) for y in range(374, WATER_Y) for x in range(SCENE_W)
           if not PANEL_L - 8 <= x <= PANEL_R + 8}
    for i in range(8):
        for (qx, qy) in blob(rng, rng.choice((rng.randrange(20, PANEL_L - 20),
                                              rng.randrange(PANEL_R + 20,
                                                            SCENE_W - 20))),
                             rng.randrange(378, WATER_Y - 2),
                             rng.randint(12, 40), low):
            c.set(qx, qy, C("19332d"))

    # ------------------------------------ cable tray + bricked-up doorway ----
    # VISIBLE POWER CABLES: the tube is fed from a box on the wall, up the
    # right-hand rod.  nothing in this frame is simply on with no wire.
    # a slung supply cable the length of the tunnel, on rolled brackets.  it
    # feeds the tube from the box on the right, it crosses the sodium halo and
    # cuts the concentric banding, and it gives the empty middle-left of the
    # wall a line to hang on.  it stays above y=200, well clear of the buttons.
    anchors = [940]
    while anchors[-1] > 316:
        anchors.append(anchors[-1] - rng.randint(58, 96))
    for i in range(len(anchors) - 1):
        a, b = anchors[i + 1], anchors[i]
        ya = 178 + int(wob(a, 3.0, 89.0, 2.2, 197.0, 0.9))
        yb = 178 + int(wob(b, 3.0, 89.0, 2.2, 197.0, 0.9))
        dip = rng.uniform(9.0, 17.0)
        for x in range(a, b + 1):
            u = (x - a) / float(b - a)
            yy = int(ya + (yb - ya) * u + math.sin(u * math.pi) * dip)
            c.set(x, yy, C("090a14"))
            c.set(x, yy + 1, C("090a14"))
            c.set(x, yy - 1, wall_col(x, yy - 1, 1.4, PANEL_L <= x <= PANEL_R))
    for a in anchors:                                # the bracket at each hang
        ya = 178 + int(wob(a, 3.0, 89.0, 2.2, 197.0, 0.9))
        c.rect(a - 2, ya - 7, a + 2, ya + 2, C("090a14"))
        c.hline(a - 2, a + 2, ya - 7, wall_col(a, ya - 7, 1.4))
        c.vline(a - 3, ya - 6, ya + 1, wall_col(a, ya, -2.0))
    c.rect(908, 132, 934, 164, C("202e37"))          # junction box
    c.rect(911, 135, 931, 161, C("151d28"))
    c.hline(908, 934, 132, C("394a50"))
    c.vline(934, 133, 164, C("10141f"))
    c.rect(918, 162, 923, 182, C("151d28"))          # its conduit stub
    c.vline(918, 162, 182, C("341c27"))

    # ------------------------------------------------------ the downpipe -----
    # CRITIC FIX 1 (user: "what is that thing to the right of the door?").  a
    # louvred scupper with two black stains hanging off it read as nothing at
    # all — a smudge.  it is now the deck's rainwater downpipe: a hopper head,
    # a ROUND pipe (lit column, body, shade column, so it reads as a cylinder
    # and not as a stripe), brackets at uneven heights, and a burst joint that
    # explains the stain instead of the stain explaining itself.
    # the light in this bay comes from the mouth on the LEFT, so the pipe's lit
    # side is its left one and every bracket is lit along its top.
    PX = 330
    for y in range(108, 193):                        # the stack up to the deck.
        p = PX + 6                                   # WITHOUT this the hopper
        c.set(p - 3, y, C("090a14"))                 # read as a lamp shade on a
        c.set(p - 2, y, C("394a50"))                 # post — a cone with
        c.set(p - 1, y, C("202e37"))                 # nothing above it is a
        c.set(p, y, C("151d28"))                     # light fitting, a cone fed
        c.set(p + 1, y, C("10141f"))                 # from the deck is a drain
        c.set(p + 2, y, C("090a14"))
    for k in range(9):                               # the swan neck into it
        c.hline(PX + 3 - k, PX + 8, 184 + k, C("151d28"))
        c.set(PX + 3 - k, 184 + k, C("090a14"))
        c.set(PX + 4 - k, 183 + k, C("394a50"))
    c.rect(PX - 1, 190, PX + 8, 195, C("151d28"))
    c.hline(PX - 1, PX + 8, 190, C("394a50"))
    c.rect(PX + 1, 146, PX + 11, 148, C("151d28"))   # its one bracket up there
    c.hline(PX + 1, PX + 11, 146, C("394a50"))
    c.hline(PX + 1, PX + 11, 149, C("090a14"))
    for y in range(196, 234):                        # the hopper head, tapered
        t = max(0.0, (y - 200) / 33.0)
        half = int(19 - 13 * t)
        # a step DARKER than the wall behind it on purpose: at this end of the
        # tunnel the wall is 202e37/394a50, and a hopper painted in those read
        # as an outline with nothing inside it.
        c.hline(PX - half, PX + half, y, C("151d28"))         # front, mid tone
        c.hline(PX - half, PX - half + 2, y, C("394a50"))     # the lit cheek
        c.hline(PX + half - 5, PX + half, y, C("10141f"))     # the shade cheek
        c.set(PX - half - 1, y, C("090a14"))                  # hard silhouette
        c.set(PX + half + 1, y, C("090a14"))
    c.rect(PX - 22, 192, PX + 22, 195, C("151d28"))  # the rim, seen edge on
    c.hline(PX - 22, PX + 22, 192, C("394a50"))
    c.hline(PX - 22, PX + 22, 196, C("090a14"))
    c.vline(PX - 23, 192, 196, C("090a14"))
    c.vline(PX + 23, 192, 196, C("090a14"))
    c.hline(PX - 16, PX + 16, 206, C("151d28"))      # the strap round the head
    c.hline(PX - 16, PX + 16, 207, C("090a14"))
    c.hline(PX - 15, PX + 15, 205, C("394a50"))
    BREAK_T, BREAK_B = 268, 277                      # the burst joint

    def pipe_col(y: int) -> int:                     # the lower half is shoved
        return PX + (3 if y > BREAK_B else 0)        # sideways off its brackets

    # the wet fan below the break, painted on the wall BEFORE the pipe so the
    # pipe stands in front of its own stain.  SOLID and narrow — the old smear
    # was a 40px black cloud that swallowed the whole bay.
    for y in range(BREAK_B, 396):
        t = (y - BREAK_B) / 119.0
        half = int(3 + 11 * t)
        sc = PX + 3 + int(2.0 * math.sin(y / 21.0) + 1.4 * math.sin(y / 47.0))
        for x in range(sc - half, sc + half + 1):
            e = abs(x - sc) / float(half)
            c.set(x, y, wall_col(x, y, -1.4 if e < 0.5 else -0.7))
    for y in range(372, 398):                        # algae where it lands
        sc = PX + 3 + int(2.0 * math.sin(y / 21.0))
        c.hline(sc - 7 - (y - 372) // 3, sc + 6 + (y - 372) // 4, y, C("19332d"))

    for y in range(230, 398):
        if BREAK_T <= y <= BREAK_B:
            continue
        p = pipe_col(y)
        c.set(p - 3, y, C("090a14"))
        c.set(p - 2, y, C("394a50"))
        c.set(p - 1, y, C("202e37"))
        c.set(p, y, C("151d28"))
        c.set(p + 1, y, C("10141f"))
        c.set(p + 2, y, C("090a14"))
    for (by, bw) in ((243, 6), (296, 5), (349, 6), (385, 5)):   # uneven brackets
        p = pipe_col(by)
        c.rect(p - 3 - bw, by, p + 2 + bw, by + 2, C("151d28"))
        c.hline(p - 3 - bw, p + 2 + bw, by, C("394a50"))
        c.hline(p - 3 - bw, p + 2 + bw, by + 3, C("090a14"))
    for cy_ in (315, 366):                           # socket collars
        p = pipe_col(cy_)
        c.rect(p - 4, cy_, p + 3, cy_ + 5, C("202e37"))
        c.hline(p - 4, p + 3, cy_, C("394a50"))
        c.vline(p + 3, cy_, cy_ + 5, C("090a14"))
        c.hline(p - 4, p + 3, cy_ + 5, C("090a14"))
    c.hline(PX - 3, PX + 2, BREAK_T, C("090a14"))    # the torn ends
    c.set(PX - 2, BREAK_T - 1, C("394a50"))
    c.hline(PX, PX + 5, BREAK_B, C("090a14"))
    c.set(PX + 1, BREAK_B + 1, C("394a50"))

    dx0, dx1 = 826, 898                              # bricked-up service door
    c.rect(dx0, 232, dx1, 386, C("341c27"))
    c.rect(dx0 + 3, 238, dx1 - 3, 386, C("4d2b32"))
    c.hline(dx0 - 3, dx1 + 3, 230, C("884b2b"))      # lit lintel lip
    c.hline(dx0 - 3, dx1 + 3, 231, C("602c2c"))
    by = 240
    while by < 386:
        h = rng.randint(11, 15)
        off = rng.randint(0, 22)
        for y in range(by, min(386, by + h)):
            for x in range(dx0 + 3, dx1 - 2):
                if (x + off) % 26 == 0:
                    c.set(x, y, C("341c27"))
        c.hline(dx0 + 3, dx1 - 3, by, C("341c27"))
        by += h
    c.vline(dx0 + 3, 238, 385, C("602c2c"))

    # the hounds' chalk dog — the one mark a person left, small and faint.
    # CRITIC FIX 1: moved to (610, 296); at y 240 it sat level with the top
    # two buttons.
    ck = C("819796")
    gx, gy = 610, 296
    for (a, b, l) in ((0, 8, 26), (2, 6, 3), (24, 6, 4)):     # back, head, rump
        c.hline(gx + a, gx + a + l, gy + b, ck)
    c.hline(gx + 26, gx + 33, gy + 4, ck)                     # snout
    c.set(gx + 33, gy + 5, ck)
    for (lx, ll) in ((3, 12), (8, 11), (21, 12), (26, 10)):   # legs, all uneven
        c.vline(gx + lx, gy + 9, gy + 9 + ll, ck)
    for k in range(7):                                        # tail, curled
        c.set(gx - 2 - k, gy + 7 - int(k * k * 0.22), ck)
    c.set(gx + 30, gy + 2, ck)                                # ear

    # -------------------------------------------------- the deck underside ---
    for x in range(SCENE_W):
        db = 107 + int(wob(x, 2.0, 41.0, 1.5, 97.0, 0.7))
        for y in range(0, db + 1):
            c.set(x, y, C("090a14"))
        c.set(x, db, C("10141f"))
    # CRITIC FIX 7: the top 108px was a flat black bar.  it is the SOFFIT of a
    # rail deck, so it gets the structure a soffit has — three main girder
    # flanges running the length of the frame, the cross-bracing hanging off
    # them, and the leaks staining down between.  every value in here is
    # 090a14/10141f with one 151d28 lip where the tube reaches: the band stays
    # the darkest in the picture, it just stops being empty.
    for (gy, amp, ph, lip) in ((21, 2.2, 0.4, False), (50, 1.8, 2.9, True),
                               (77, 2.6, 5.1, True)):
        for x in range(SCENE_W):
            yy = gy + int(wob(x, amp, 61.0, amp * 0.7, 137.0, ph))
            c.rect(x, yy - 6, x, yy, C("090a14"))          # the web, in shade
            c.set(x, yy, C("10141f"))                      # lit lower flange
            if lip and x > 552:
                c.set(x, yy, C("151d28"))
                c.set(x, yy - 1, C("10141f"))
    gpos = [34, 118, 212, 306, 640, 748, 856, 942]
    for g in gpos:
        g += rng.randint(-9, 9)
        w = rng.randint(8, 12)
        depth = rng.randint(84, 93)
        c.rect(g, 0, g + w, depth, C("10141f"))
        lit = g if g + w // 2 < 480 else g + w
        c.vline(lit, 0, depth, C("151d28"))
        if g > 480:
            c.hline(g, g + w, depth, C("151d28"))
            c.hline(g + 1, g + w - 1, depth - 1, C("202e37"))
        else:
            c.hline(g, g + w, depth, C("10141f"))
    # one bay's brace has torn loose and hangs at an angle — the odd member is
    # what stops the bracing reading as a repeated pattern.
    for k in range(58):
        c.set(760 + k, 24 + int(k * 0.86), C("10141f"))
        c.set(760 + k, 25 + int(k * 0.86), C("090a14"))
    c.rect(816, 72, 820, 80, C("10141f"))
    # leaks bleeding down off the girder flanges.  the first cut made these
    # smooth widening cones and they read as stalactites — they are RUNS, so
    # each one is a cluster of narrow streaks of unequal length with a wobbled
    # edge, and the wet patch spreads sideways only where it starts.
    for (lx, ly, ln, wd) in ((146, 22, 40, 4), (398, 51, 27, 3), (452, 23, 55, 5),
                             (600, 78, 18, 3), (688, 50, 34, 5), (884, 21, 46, 4)):
        for k in range(9):                                 # the wet patch, solid
            c.hline(lx - wd - 1 + k // 3, lx + wd + 1 - k // 3, ly + k, C("10141f"))
        for s in range(rng.randint(3, 5)):
            sx = lx + rng.randint(-wd, wd)
            sl = rng.randint(ln // 3, ln)
            for k in range(sl):
                xx = sx + int(1.6 * math.sin((ly + k) / 23.0 + s))
                c.set(xx, ly + k, C("10141f"))
                if k < sl // 2:
                    c.set(xx + 1, ly + k, C("10141f"))
    # the near portal beam, full width, only the lamp can catch its underside
    for x in range(SCENE_W):
        bb = 107 + int(wob(x, 2.0, 41.0, 1.5, 97.0, 0.7))
        c.rect(x, 92, x, bb, C("090a14"))
        if x >= 596:
            c.set(x, bb, C("202e37"))
            c.set(x, bb - 1, C("10141f"))
        elif 96 <= x <= 312:
            c.set(x, bb, C("10141f"))
    c.hline(596, SCENE_W - 1, 92, C("10141f"))

    # ------------------------------------------------------------ the mouth --
    # a rectangular concrete portal with a REAL reveal, not a hole cut in the
    # wall.  the drain puts a black arch into nothing in this exact real
    # estate; this is the same position at the opposite value.
    JL_O, JL_I, JR_I, JR_O = 90, 130, 266, 294
    HEAD, SOFF = 136, 162
    # the surround is BANDED toward the opening — the light is inside it, so
    # the concrete brightens the closer it gets to the reveal.  flat grey read
    # as a door frame in a house on the first bake.
    for y in range(HEAD, SOFF):                                # lintel front
        d = SOFF - y
        c.rect(JL_O, y, JR_O, y, C("577277") if d <= 5 else
               (C("394a50") if d <= 17 else C("202e37")))
    c.hline(JL_O, JR_O, HEAD, C("151d28"))
    for y in range(SOFF, WATER_Y):
        for x in range(JL_O, JL_I):
            d = JL_I - x
            c.set(x, y, C("577277") if d <= 9 else
                  (C("394a50") if d <= 27 else C("202e37")))
        for x in range(JR_I + 1, JR_O + 1):
            d = x - JR_I
            c.set(x, y, C("577277") if d <= 9 else
                  (C("394a50") if d <= 27 else C("202e37")))
    sy = SOFF + rng.randint(30, 60)                            # precast joints
    while sy < WATER_Y:
        c.hline(JL_O, JL_I - 1, sy, C("202e37"))
        c.hline(JR_I + 1, JR_O, sy + rng.randint(-6, 6), C("202e37"))
        sy += rng.randint(52, 84)
    for x in range(JL_O, JR_O + 1):                            # jamb wear
        if (x * 7 + 3) % 61 < 3:
            c.vline(x, HEAD + rng.randint(40, 200), HEAD + rng.randint(220, 260),
                    C("202e37"))
    c.rect(JL_I, SOFF - 10, JR_I, SOFF - 1, C("202e37"))       # soffit
    c.hline(JL_I, JR_I, SOFF - 10, C("151d28"))
    c.rect(JL_I, SOFF, JL_I + 11, WATER_Y, C("202e37"))        # left reveal
    c.vline(JL_I + 11, SOFF, WATER_Y, C("151d28"))

    OX0, OX1 = JL_I + 12, JR_I                                 # opening
    SKY, SKY_B = SOFF, 218
    for y in range(SKY, SKY_B):
        col = C("c7cfcc") if y < SKY + 6 else (C("a8b5b2") if y < SKY + 28 else C("819796"))
        c.hline(OX0, OX1, y, col)
    # the street outside: a flat silhouette skyline, all different heights
    prof = {}
    bx = OX0 - rng.randint(0, 8)
    while bx < OX1 + 10:
        bw = rng.randint(9, 26)
        bh = rng.randint(6, 34)
        for x in range(bx, min(OX1 + 1, bx + bw)):
            prof[x] = SKY_B - bh
        bx += bw + rng.randint(0, 3)
    for x in range(OX0, OX1 + 1):
        top = prof.get(x, SKY_B - 8)
        c.vline(x, top, 262, C("202e37"))
        c.set(x, top, C("394a50"))
    for x in range(OX0, OX1 + 1):                              # the lattice wire
        if x % 5 in (0, 1):
            c.vline(x, 238, 262, C("151d28"))
    c.hline(OX0, OX1, 238, C("151d28"))
    c.hline(OX0, OX1, 250, C("151d28"))
    for (px, lean, h) in ((166, 1, 30), (212, -1, 26)):        # two leaning posts
        for k in range(h):
            c.set(px + int(k * 0.12) * lean, 262 - k, C("151d28"))
            c.set(px + 1 + int(k * 0.12) * lean, 262 - k, C("090a14"))
    c.vline(244, 220, 262, C("151d28"))                        # dead traffic light
    c.rect(240, 214, 247, 231, C("151d28"))
    c.rect(241, 216, 246, 229, C("10141f"))
    c.set(243, 218, C("341c27"))
    c.set(243, 223, C("341c27"))
    c.set(243, 228, C("19332d"))
    c.hline(239, 248, 213, C("202e37"))

    # ---- the flood running out of the mouth: A MIRROR, not a hem ------------
    # CRITIC FIX 2 (user: "the water just looks flat at the doorway, like it
    # doesn't look right").  it was a flat 577277 slab with a column of white
    # dashes down the middle and it read as a stitched seam in a sheet of
    # paper.  it is rebuilt as an actual reflecting plane:
    #   * the FAR WATERLINE is y=262, where the fence stands in the flood.  a
    #     flat mirror reflects about that line 1:1 IN SCREEN SPACE, so the
    #     sample is sy = 2*262 - y and every reflected thing lands in the SAME
    #     COLUMN as the real one.  that is the whole trick — the eye checks the
    #     columns, and the old version had nothing under anything.
    #   * the surface tone steps DARKER as it comes forward, on wavy seams.
    #   * the ripple dashes are short and tightly packed at the far end and get
    #     longer, sparser, more broken and more sideways-displaced toward the
    #     viewer.  that, not a vanishing point, is what makes water recede.
    #   * the three top cold values live in here and NOWHERE else, which is
    #     what stops this reading as a second drain.
    MIRROR = 262
    SURF = ((288, C("819796")), (320, C("577277")), (358, C("394a50")),
            (386, C("202e37")), (999, C("151d28")))
    for y in range(MIRROR, WATER_Y):
        for x in range(OX0, OX1 + 1):
            b = y + int(wob(x, 3.0, 41.0, 2.1, 103.0, y * 0.017))
            for (lim, col) in SURF:
                if b < lim:
                    c.set(x, y, col)
                    break
    # the submerged kerbs, converging — a depth cue that is NOT a centreline
    for side in (-1, 1):
        for y in range(266, 348):
            d = (y - MIRROR) / 144.0
            kx = 204 + side * int(9 + 62 * d)
            if OX0 < kx < OX1 and (y // (2 + int(4 * d))) % 2 == 0:
                c.set(kx, y, C("577277") if y < 300 else C("394a50"))
                c.set(kx + side, y, C("394a50") if y < 300 else C("202e37"))
    # what the flood gives back through the mouth.  TWO things are deliberate
    # here and the render forced both:
    #   * each dash samples the source ONCE, at its own midpoint, and is then
    #     filled solid.  a per-pixel sample reproduced the fence's 5px picket
    #     comb and the far water came out as static — the exact dot noise the
    #     rules ban.  water throws away fine detail; broad strokes are the
    #     truthful answer as well as the legible one.
    #   * a HAZE FLOOR: at the far end nothing may reflect darker than three
    #     steps up the ramp, and the floor drops as the surface comes forward.
    #     without it the compressed fence printed as black bars on pale water
    #     and the far end had more contrast than the near end, which is
    #     backwards.
    RAMP = ("090a14", "10141f", "151d28", "202e37", "394a50",
            "577277", "819796", "a8b5b2", "c7cfcc")
    RIDX = {C(n)[:3]: i for i, n in enumerate(RAMP)}
    # each ripple facet is a STROKE, and the strokes grow as the surface comes
    # forward: one pixel tall and tightly stacked at the far end, up to four
    # tall and widely broken at the near.  that, and only that, is what makes a
    # flat plane read as receding — a single stroke size at every depth is the
    # flat slab this started as.
    y = MIRROR + 1
    while y < WATER_Y:
        d = (y - MIRROR) / float(WATER_Y - MIRROR)
        th = 1 + int(3.2 * d)
        sy = 2 * MIRROR - y
        if sy < HEAD:          # past the portal head there is only black deck
            y += th
            continue
        surv = 0.96 - 0.44 * d
        floor = max(1, 3 - int(d * 2.4))
        x = OX0 + rng.randrange(0, 4 + int(12 * d))
        while x <= OX1:
            dl = rng.randint(9 + int(9 * d), 24 + int(30 * d))
            if rng.random() < surv:
                jit = int(2.5 * d * math.sin(y * 0.83)
                          + 2.0 * d * math.sin(x * 0.29 + y * 0.11))
                i = RIDX.get(c.get(min(OX1, x + dl // 2) + jit, sy)[:3])
                if i is not None:
                    # capped at 819796: the sky's own top value reflecting
                    # 1:1 put a near-white slab in the near water that was the
                    # brightest thing in the frame.  water is never brighter
                    # than the sky it is copying.
                    col = C(RAMP[min(6, max(floor, i - 1))])
                    for xx in range(x, min(OX1 + 1, x + dl)):
                        for k in range(th):
                            c.set(xx, y + k, col)
            x += dl + rng.randint(1 + int(4 * d), 4 + int(20 * d))
        y += th
    # calm slicks: solid unbroken runs that cut across the ripple, longest and
    # nearest the viewer.  without them the near water is all texture, no form.
    for i in range(16):
        sy_ = rng.randrange(300, WATER_Y - 2)
        d = (sy_ - MIRROR) / 144.0
        sx_ = rng.randrange(OX0, OX1 - 6)
        ln = rng.randint(8 + int(20 * d), 18 + int(52 * d))
        col = C("577277") if d < 0.55 else C("394a50")
        und = C("394a50") if d < 0.55 else C("202e37")
        for xx in range(sx_, min(OX1 + 1, sx_ + ln)):
            yy = sy_ + int(1.4 * math.sin(xx / 19.0 + i))
            c.set(xx, yy, col)
            for k in range(1, 1 + int(1 + 2 * d)):
                c.set(xx, yy + k, und)
    # the waterline itself, broken, where the fence stands in it
    for x in range(OX0, OX1 + 1):
        if (x * 5 + 2) % 13 > 4:
            c.set(x, MIRROR, C("a8b5b2"))
            c.set(x, MIRROR + 1, C("819796"))

    # ---------------------------------------------------- the sunken car -----
    # THE CAR IS NOT DRAWN HERE ANY MORE — it stood at (180, 332), half behind
    # the portal's right jamb, and it is now built at the END of this file, out
    # in the open flood where a whole vehicle fits.  see REVISION 3.
    # what stays here is its rust roll, and ONLY its rust roll: it costs the
    # seeded stream exactly the four draws per patch it always cost, so moving
    # the car cannot re-roll one sandbag, ripple, slick or wake behind it.
    car_rust = [(rng.randrange(34, 160), rng.randrange(41, 60),
                 rng.randint(5, 13), rng.randint(3, 6)) for _ in range(5)]

    # ------------------------------------------------- the raised walkway ----
    # the one dry path through, and a legible game idea.  it stops at x=604 in
    # a collapsed end so it cannot reach the buttons (critic fix 2).
    def wk_top(x: float) -> float:
        return 386.0 + (x - 600.0) * 18.0 / 360.0

    def wk_wl(x: float) -> float:
        return 406.0 + (x - 600.0) * 24.0 / 360.0

    def wk_depth(x: float) -> float:
        return 11.0 + (x - 600.0) * 19.0 / 360.0

    for x in range(604, SCENE_W):
        ty = int(wk_top(x))
        dp = int(wk_depth(x))
        c.rect(x, ty - dp, x, ty - 1, C("394a50"))             # lit top face
        c.set(x, ty - dp, C("151d28"))                         # shade at the wall
        c.set(x, ty - dp + 1, C("202e37"))
        c.rect(x, ty, x, int(wk_wl(x)), C("151d28"))           # front face, shade
        c.set(x, ty, C("577277"))                              # the kerb edge
        c.set(x, ty + 1, C("394a50"))
        c.set(x, ty + 2, C("202e37"))
        c.set(x, int(wk_wl(x)), C("090a14"))
        c.set(x, int(wk_wl(x)) - 1, C("10141f"))
    ex = 632                                                   # expansion joints
    while ex < SCENE_W:
        ty = int(wk_top(ex))
        dp = int(wk_depth(ex))
        for k in range(dp - 1):
            c.set(ex + k // 3, ty - dp + 1 + k, C("202e37"))
            c.set(ex + 1 + k // 3, ty - dp + 1 + k, C("577277"))
        ex += rng.randint(52, 88)
    for i in range(12):                                        # grit and wear
        wx0 = rng.randrange(612, SCENE_W - 24)
        ty = int(wk_top(wx0))
        dp = int(wk_depth(wx0))
        wy0 = ty - rng.randint(2, max(3, dp - 2))
        for k in range(rng.randint(2, 4)):
            c.hline(wx0 + k, wx0 + rng.randint(6, 20), wy0 + k, C("202e37"))
    for i in range(9):                                         # kerb chips
        kx = rng.randrange(618, SCENE_W - 20)
        kl = rng.randint(4, 13)
        for x in range(kx, kx + kl):
            c.hline(x, x, int(wk_top(x)), C("202e37"))
            c.hline(x, x, int(wk_top(x)) + 1, C("151d28"))
    # the light pool the tube throws on the walkway — solid bands, the den's
    # candle-halo method.  the breathing glow goes on TOP of this.
    for dx in range(-88, 89):
        px = 704 + dx
        if px < 606 or px >= SCENE_W:
            continue
        ty = int(wk_top(px))
        dp = int(wk_depth(px))
        wb = 1.0 + 0.10 * math.sin(px / 21.0) + 0.07 * math.sin(px / 9.0)
        for dy in range(-dp + 1, 1):
            d = ((dx / 88.0) ** 2 + ((dy + dp * 0.52) / (dp * 0.56)) ** 2) / wb
            if d < 1.0:
                c.set(px, ty + dy, C("de9e41") if d < 0.20
                      else (C("be772b") if d < 0.52 else C("884b2b")))
    for dx in range(-96, 97):                                  # spill down the face
        px = 704 + dx
        if px < 606 or px >= SCENE_W:
            continue
        ty = int(wk_top(px))
        e = (1.0 - abs(dx) / 96.0) ** 1.4
        for k in range(int(e * 8)):
            c.set(px, ty + 1 + k, C("be772b") if k < e * 3 else
                  (C("884b2b") if k < e * 6 else C("602c2c")))

    # the collapsed end: rubble and three bent bars, so the slab stops for a
    # reason instead of just ending.  drawn AFTER the pool or the pool erases it.
    for i in range(11):
        rx = 600 + rng.randrange(0, 34)
        ry = 376 + rng.randrange(0, 26)
        rw = rng.randint(4, 11)
        rh = rng.randint(3, 7)
        c.rect(rx, ry, rx + rw, ry + rh, C("4d2b32"))
        c.hline(rx, rx + rw, ry, C("884b2b"))
        c.hline(rx, rx + rw, ry + 1, C("602c2c"))
        c.vline(rx + rw, ry + 2, ry + rh, C("341c27"))
    for (bx0, bh, cur) in ((606, 16, 0.30), (614, 11, -0.22), (622, 20, 0.16)):
        for k in range(bh):
            c.set(bx0 + int(k * k * cur * 0.09), 382 - k, C("602c2c"))
            c.set(bx0 + 1 + int(k * k * cur * 0.09), 382 - k, C("341c27"))

    # sandbags: a heap three courses deep at the wall end, tapering to one.
    # CRITIC FIX 6: the first bake gave every bag the same rounded capsule and
    # a bright 2px rim along its top, and the pile read as a rack of loaves.
    # a bag is now built from a THICKNESS PROFILE pinched at both ends and fat
    # OFF-CENTRE, it carries a real top face (about a third of its height, lit)
    # split from the front face by a wavy edge, and the tied end sticks out as
    # an ear.  those are the three things bread does not have.
    def sandbag(bx, by, bw, bh, lean, ear_r, body, top, dark, phase):
        prof = []
        for i in range(bw):
            t = i / float(bw - 1)
            s = math.sin(math.pi * min(1.0, max(0.0, (t - 0.05) / 0.90))) ** 0.42
            fat = 1.0 - 0.20 * (t if ear_r else 1.0 - t)       # fat off-centre
            th = max(2, int(bh * (0.26 + 0.74 * s) * fat))
            base = (by + int(lean * (t - 0.5) * bw * 0.11)
                    + int(1.2 * math.sin(t * 5.0 + phase)))
            prof.append((base, th))
        for i, (base, th) in enumerate(prof):
            x = bx + i
            dep = max(1, int(th * 0.34 + 0.9 * math.sin(i / 3.7 + phase)))
            c.rect(x, base - th, x, base, body)                # front, in shade
            c.rect(x, base - th, x, base - th + dep, top)      # the top face
            c.set(x, base, dark)                               # where it sits
            if i < 2 or i > bw - 3:                            # the tied ends
                c.rect(x, base - th, x, base, dark)            # sit in shade,
                                                               # which is what
                                                               # separates one
                                                               # bag from the
                                                               # next in a heap
        ex = bx + bw - 1 if ear_r else bx                      # the tied ear
        eb, eth = prof[-1 if ear_r else 0]
        for k in range(4):
            xx = ex + (k + 1) * (1 if ear_r else -1)
            c.vline(xx, eb - eth // 2 - 2 + k // 2, eb - 1 - k // 3, dark)
        c.set(ex + (1 if ear_r else -1), eb - eth // 2 - 2, top)
        for i in range(2, bw - 2):                             # the fabric fold
            base, th = prof[i]                                 # — ONE solid
            if th > 4:                                         # seam, never
                c.set(bx + i, base - int(th * 0.34)            # stitch dots
                      + int(1.4 * math.sin(i / 6.0 + phase)), dark)

    MATS = ((C("4d2b32"), C("7a4841"), C("341c27")),
            (C("7a4841"), C("ad7757"), C("4d2b32")),
            (C("341c27"), C("602c2c"), C("241527")))
    bag_rows = ((391, 0, 802, 1.00), (379, 8, 788, 0.88), (367, 22, 764, 0.52))
    for (row_y, shift, stop, dens) in bag_rows:
        bx = 698 + shift + rng.randint(-5, 2)
        ear = rng.random() < 0.5
        while bx < stop:
            bw = rng.randint(15, 35)
            bh = rng.randint(8, 15)
            if rng.random() < dens:
                # under the tube the sacking bleaches out; away from it the
                # same cloth goes to the darkest of the three materials
                near = abs(bx + bw // 2 - 706) < 52
                mi = rng.choice((1, 1, 0) if near else (0, 2, 0, 1))
                body, top, dark = MATS[mi]
                sandbag(bx, row_y + rng.randint(-2, 3), bw, bh,
                        rng.choice((-1, 0, 0, 1)), ear, body, top, dark,
                        rng.uniform(0.0, 6.3))
                if rng.random() < 0.28:                        # burst, spilling
                    sx = bx + rng.randint(4, max(5, bw - 8))
                    for k in range(rng.randint(5, 11)):
                        c.hline(sx - k // 2, sx + 4 + k, row_y + 1 + k // 3,
                                C("ad7757") if k < 4 else C("884b2b"))
                if rng.random() < 0.22:                        # weed in a split
                    c.hline(bx + bw // 2 - 3, bx + bw // 2 + 2,
                            row_y - bh // 2, C("25562e"))
            ear = not ear
            bx += bw + rng.randint(-4, 2)      # they LEAN ON each other; a gap
                                               # between every bag read as a
                                               # scatter of rocks, not a bund

    # the handrail: rolled post spacing, one post bent, one span gone
    # steel against a sodium wall: a black body with an amber rim on the lamp
    # side.  the first cut drew the whole rail in 151d28 and it vanished.
    posts = (626, 668, 726, 799, 848, 921)
    for p in posts:
        ty = int(wk_top(p))
        bend = 5 if p == 726 else 0
        rim = C("884b2b") if p < 800 else C("602c2c")
        for k in range(36):
            px = p + int(k * bend / 36.0)
            c.set(px, ty - k, C("090a14"))
            c.set(px + 1, ty - k, C("090a14"))
            if k < 22:                                         # rim only up top
                c.set(px + 2 if p > 702 else px - 1, ty - k, rim)
        c.hline(p - 1 + bend, p + 2 + bend, ty - 36, C("be772b"))
        c.hline(p - 1 + bend, p + 2 + bend, ty - 35, C("602c2c"))
    for i in range(len(posts) - 1):
        a, b = posts[i], posts[i + 1]
        if a == 848:
            continue                                           # this span is gone
        for x in range(a, b + 1):
            u = (x - a) / float(b - a)
            sag = math.sin(u * math.pi) * 1.6
            ty = wk_top(x)
            for off in (34, 18):
                yy = int(ty - off + sag)
                if off == 34:
                    c.set(x, yy - 1, C("884b2b") if x < 800 else C("602c2c"))
                c.set(x, yy, C("090a14"))
                c.set(x, yy + 1, C("090a14"))
    for (sx_, d_) in ((850, 5), (919, -5)):                     # the torn stubs
        ty = int(wk_top(sx_))
        for off in (34, 18):
            c.hline(min(sx_, sx_ + d_), max(sx_, sx_ + d_), ty - off, C("090a14"))
            c.hline(min(sx_, sx_ + d_), max(sx_, sx_ + d_), ty - off - 1, C("884b2b"))

    # --------------------------------------------------------- the tube ------
    # baked at roughly 60%: solid banded light only, so the runtime dropout
    # takes the top end off and never changes the shape.
    for rx in (640, 760):
        c.rect(rx, 100, rx + 3, 150, C("151d28"))
        c.vline(rx + 3, 100, 150, C("394a50"))
        c.vline(rx, 100, 150, C("090a14"))
    for k in range(0, 46):                                      # the feed cable
        u = k / 45.0
        c.set(int(762 + u * 4), int(176 - u * 40 - math.sin(u * math.pi) * 5),
              C("090a14"))
    c.rect(918, 176, 923, 200, C("151d28"))
    for k in range(0, 160):
        u = k / 159.0
        c.set(int(920 - u * 158), int(200 + math.sin(u * math.pi) * 7 - u * 24),
              C("090a14"))

    c.rect(628, 142, 642, 162, C("202e37"))                     # end housings
    c.rect(762, 136, 776, 156, C("202e37"))
    c.hline(628, 642, 142, C("394a50"))
    c.hline(762, 776, 136, C("394a50"))
    for x in range(636, 769):
        u = (x - 636) / 132.0
        ty = int(152 - u * 6)
        c.set(x, ty, C("e7d5b3"))
        c.rect(x, ty + 1, x, ty + 6, C("e8c170"))
        c.rect(x, ty + 7, x, ty + 9, C("be772b"))
        c.set(x, ty + 10, C("884b2b"))
    for bx in (651, 673, 698, 719, 745):                        # cage bars
        bx += rng.randint(-3, 3)
        u = (bx - 636) / 132.0
        ty = int(152 - u * 6)
        c.rect(bx, ty - 2, bx + 1, ty + 11, C("090a14"))
    c.hline(636, 768, 163, C("602c2c"))                         # cage lower hoop
    c.hline(637, 767, 164, C("341c27"))

    # ------------------------------------------------------------ the water --
    def water_top(x: int) -> int:
        if x < 604:
            return WATER_Y + int(wob(x, 1.6, 31.0, 1.1, 67.0, 3.1))
        return int(wk_wl(x)) + 1

    # CRITIC FIX 4: the flood was a flat 090a14 slab, and a mirror that dark
    # gives nothing back — its reflections were technically present and
    # visually absent.  the surface now carries the room's own light, sampled
    # at the point being MIRRORED (which is where the trough clamp lives, so
    # the middle stays near-black under the buttons without a second rule).
    WCOLD = (C("090a14"), C("10141f"), C("151d28"), C("202e37"), C("394a50"))
    WWARM = (C("090a14"), C("10141f"), C("341c27"), C("4d2b32"), C("602c2c"))
    for y in range(WATER_Y - 4, SCENE_H):
        u = max(0.0, (y - WATER_Y) / float(SCENE_H - WATER_Y))
        att = 1.0 - 0.34 * u
        syl = max(126, int(WATER_Y - (y - WATER_Y) * 1.25))
        rip = 1.0 + 0.11 * math.sin(y / 13.0) + 0.07 * math.sin(y / 5.0)
        for x in range(SCENE_W):
            if y < water_top(x):
                continue
            lm, _ = levels(x, syl)
            # the tube's own pool ON THE FLOOD is its own term: levels() puts
            # the tube 250px up, so its wall falloff never reaches the water.
            wl = 0.0
            if x > 566:
                wl = max(0.0, 1.0 - rip * ((((x - 716) / 268.0) ** 2
                                            + ((y - 414) / 116.0) ** 2) ** 0.5)) ** 1.4
            if wl * 4.6 > lm * 3.6:
                c.set(x, y, WWARM[max(0, min(4, int(wl * 4.6 * att + 0.4)))])
            else:
                c.set(x, y, WCOLD[max(0, min(4, int(lm * 3.6 * att + 0.4)))])

    # surface chop everywhere, so no part of the flood is dead flat.  solid
    # dashes on wavy lines, thinning downward — never dots.
    LIFT = {C("090a14")[:3]: C("10141f"), C("10141f")[:3]: C("151d28"),
            C("151d28")[:3]: C("202e37"), C("202e37")[:3]: C("394a50"),
            C("394a50")[:3]: C("577277"), C("341c27")[:3]: C("4d2b32"),
            C("4d2b32")[:3]: C("602c2c"), C("602c2c")[:3]: C("884b2b")}
    DROP = {v[:3]: C(k) for k, v in
            (("090a14", C("10141f")), ("10141f", C("151d28")),
             ("151d28", C("202e37")), ("202e37", C("394a50")),
             ("10141f", C("341c27")), ("341c27", C("4d2b32")),
             ("4d2b32", C("602c2c")))}
    for i in range(150):
        dy = rng.randrange(WATER_Y + 3, SCENE_H)
        u = (dy - WATER_Y) / float(SCENE_H - WATER_Y)
        dx = rng.randrange(0, SCENE_W - 40)
        ln = rng.randint(16, 160)
        up = rng.random() < 0.45
        th = 1 + int(2.6 * u)
        x = dx
        while x < min(SCENE_W, dx + ln):
            run = rng.randint(5, 15 + int(20 * u))
            if rng.random() > 0.26 + u * 0.26:
                for xx in range(x, min(SCENE_W, x + run)):
                    yy = dy + int(wob(xx, 1.5, 57.0, 1.1, 131.0, i * 0.9))
                    for k in range(th):
                        if yy + k >= water_top(xx):
                            src = c.get(xx, yy + k)[:3]
                            col = (LIFT if up else DROP).get(src)
                            if col is not None:
                                c.set(xx, yy + k, col)
            x += run + rng.randint(3, 14)

    # the flood is a TRUE 1:1 MIRROR about its own near shore (y = 406): the
    # wall foot, the car, the walkway and the bags all land in their own
    # columns.  the facets grow and break up as they come forward, the same
    # rule the water in the mouth uses, so the two surfaces agree.
    y = WATER_Y + 1
    while y < SCENE_H:
        u = (y - WATER_Y) / float(SCENE_H - WATER_Y)
        th = 1 + int(3.4 * u)
        sy = 2 * WATER_Y - y
        surv = 0.80 - 0.50 * u
        x = rng.randrange(0, 30)
        while x < SCENE_W:
            dl = rng.randint(7 + int(9 * u), 20 + int(34 * u))
            if rng.random() < surv:
                wx = int(3.0 * math.sin(y * 0.61) + 2.5 * math.sin(x * 0.21 + y * 0.09))
                col = REFLECT.get(c.get(min(SCENE_W - 1, x + dl // 2) + wx, sy)[:3])
                if col is not None:
                    for xx in range(x, min(SCENE_W, x + dl)):
                        for k in range(th):
                            if y + k >= water_top(xx):
                                c.set(xx, y + k, col)
            x += dl + rng.randint(4, 12 + int(26 * u))
        y += th

    # the tube and the mouth are far too high for that mirror to reach — a 1:1
    # reflection would put them well off the bottom of the frame.  what water
    # actually does with a high light is throw a SPECULAR COLUMN straight down
    # beneath it, in its own columns, widening and breaking as it comes on.
    # that is these, and it is why the flood finally has the lamp in it.
    for (gc, ghw, ramp) in (
            (702, 68, ("e8c170", "de9e41", "be772b", "884b2b", "602c2c", "341c27")),
            (204, 62, ("a8b5b2", "819796", "577277", "394a50", "202e37", "151d28"))):
        y = WATER_Y + 1
        while y < SCENE_H:
            u = (y - WATER_Y) / float(SCENE_H - WATER_Y)
            th = 1 + int(3.0 * u)
            hw = int(ghw * (0.85 + 0.85 * u))
            x = gc - hw + rng.randrange(0, 12)
            while x < gc + hw:
                dl = rng.randint(4 + int(7 * u), 13 + int(26 * u))
                e = abs(x + dl * 0.5 - gc) / float(hw)
                idx = min(5, int(u * 3.4 + e * 2.6 + rng.random() * 1.2))
                if rng.random() < (0.86 - 0.46 * u) * (1.0 - 0.55 * e * e):
                    col = C(ramp[idx])
                    for xx in range(max(0, x), min(SCENE_W, x + dl)):
                        for k in range(th):
                            if y + k >= water_top(xx):
                                c.set(xx, y + k, col)
                x += dl + rng.randint(3, 10 + int(20 * u))
            y += th

    # ------------------------------------------------- foreground debris -----
    # all rooted off the bottom edge, each a solid silhouette with exactly one
    # lit face, no two the same shape, size or lean.
    # CRITIC FIX 3 (user: "there's a couple things on top of the water that
    # shouldn't be there ... either make them look like they're floating for
    # that flooded feel, or just remove it").  the crate and the drum were
    # drawn whole and sat on the flood as if it were a floor.  everything that
    # floats now goes through here, because floating is FOUR things and they
    # had none of them:
    #   1. the WATERLINE CUTS the object — everything under it is not drawn,
    #      and the cut is dead level while the object itself leans.
    #   2. a disturbance ring pushed into the surface where it breaks through.
    #   3. a broken reflection directly beneath, in the object's own columns.
    #   4. a lean, and NOT the same lean on any two of them.
    def float_wake(x0, x1, wl, warm, depth=24):
        hi = C("884b2b") if warm else C("394a50")
        lo = C("602c2c") if warm else C("202e37")
        x = x0 - 10                       # the ring is broken into RUNS: an
        while x < x1 + 11:                # every-nth-pixel break read as a
            run = rng.randint(3, 10)      # dotted line, which is dot noise
            if rng.random() < 0.66:
                for xx in range(x, min(x1 + 11, x + run)):
                    t = (xx - (x0 - 10)) / float(x1 - x0 + 20)
                    yy = wl + int(2.6 * math.sin(t * math.pi)
                                  + 0.9 * math.sin(t * 9.0))
                    c.set(xx, yy, hi)
                    c.set(xx, yy + 1, lo)
            x += run + rng.randint(1, 7)
        y = wl + 2
        while y < wl + depth:
            k = y - wl
            x = x0 - 6 + rng.randrange(0, 7)
            while x < x1 + 6:
                dl = rng.randint(4, 10 + k)
                if rng.random() < 0.92 - k * 0.030:
                    col = REFLECT.get(c.get(min(x + dl // 2, SCENE_W - 1),
                                            2 * wl - y)[:3])
                    if col is not None:
                        for xx in range(x, min(SCENE_W, x + dl)):
                            c.set(xx, y, col)
                            if k > 9:
                                c.set(xx, y + 1, col)
                x += dl + rng.randint(3, 8 + k)
            y += 1 + k // 7

    # the tyre sits against the mouth's reflection on purpose: a black shape
    # in the one pale part of the flood is the cheapest depth cue in the frame
    TX, TY = 268, 492
    for dy in range(-30, 31):                                   # half-sunk tyre
        for dx in range(-38, 39):
            d = (dx / 38.0) ** 2 + (dy / 30.0) ** 2
            if d < 1.0 and dy < 8:
                inner = (dx / 19.0) ** 2 + (dy / 14.0) ** 2 < 1.0
                if inner and dy < 3:
                    continue
                c.set(TX + dx, TY + dy, C("090a14"))
    for k in range(46):
        a = math.radians(196 + k * 1.7)
        c.set(TX + int(math.cos(a) * 37), TY + int(math.sin(a) * 29), C("202e37"))
        c.set(TX + int(math.cos(a) * 36), TY + int(math.sin(a) * 28), C("151d28"))
    for k in range(9):                                          # tread blocks
        a = math.radians(206 + k * 13)
        c.set(TX + int(math.cos(a) * 33), TY + int(math.sin(a) * 26), C("10141f"))

    # the drifting pallet.  its slats used to sit at a dead 5px pitch and it
    # read as a ladder — even spacing on a repeated shape is the one thing the
    # standing rule names outright.  the pitch is unequal now, one slat is
    # missing and one is snapped in two, and it takes a wake like the rest.
    for (dy, dx, w) in ((0, 0, 68), (6, 3, 63), (14, 8, 71), (19, 13, 25),
                        (18, 46, 22), (28, 17, 59)):
        sy, sx = 500 + dy, 396 + dx
        c.rect(sx, sy, sx + w, sy + 2, C("090a14"))
        c.hline(sx, sx + w, sy, C("202e37"))
        c.hline(sx, sx + w, sy + 1, C("151d28"))
    c.rect(399, 499, 403, 529, C("090a14"))                     # the two bearers
    c.rect(456, 505, 460, 533, C("090a14"))
    c.vline(399, 499, 529, C("151d28"))
    c.vline(456, 505, 533, C("151d28"))
    float_wake(398, 470, 535, False, 8)

    for k in range(200):                                        # a drowned cable
        u = k / 199.0
        cx_ = 300 + int(u * 268)
        cy_ = 452 + int(math.sin(u * 2.7 + 0.4) * 26 + u * 34)
        if cy_ >= water_top(cx_):
            c.set(cx_, cy_, C("151d28"))
            c.set(cx_, cy_ + 1, C("090a14"))

    CX, CWL = 736, 497                              # plastic crate, listing right
    for i in range(45):
        x = CX + i
        sh = int(i * 0.13)                          # the list, baked as a shear
        top = 470 - sh
        wl = CWL + int(1.2 * math.sin(i / 7.0))     # but the CUT stays level
        c.rect(x, top + 5, x, wl, C("602c2c"))      # the side the tube lights
        c.rect(x, top, x, top + 2, C("884b2b"))     # the top rail
        c.set(x, top + 3, C("4d2b32"))
        if 4 < i < 40:                              # you can see down into it
            c.rect(x, top + 4, x, top + 9, C("341c27"))
            c.set(x, top + 4, C("241527"))
    for k in range(4):                              # the moulded ribs, uneven
        i = 7 + k * 9 + (k % 2) * 2
        x, sh = CX + i, int(i * 0.13)
        c.vline(x, 470 - sh + 11, CWL - 1, C("341c27"))
        c.vline(x + 1, 470 - sh + 11, CWL - 1, C("884b2b"))
    c.vline(CX, 470, CWL, C("341c27"))              # corner posts
    c.vline(CX + 44, 470 - 5, CWL, C("884b2b"))
    float_wake(CX, CX + 44, CWL, True)

    for k in range(74):                                         # drifting plank
        px = 566 + k
        py = 528 + int(k * 0.09)
        c.rect(px, py, px, py + 6, C("151d28"))
        c.set(px, py, C("202e37"))
    c.vline(640, 534, 540, C("090a14"))

    OX, OWL, ORY = 862, 509, 494                    # oil drum, listing the OTHER
    for k in range(-21, 22):                        # way and riding much deeper
        x = OX + k
        sh = int((21 - k) * 0.10)                   # the list, opposite the crate
        dy = int((1.0 - (k / 21.0) ** 2) ** 0.5 * 6.5)
        rt, rb = ORY - dy + sh, ORY + dy + sh
        wl = OWL + int(1.1 * math.sin(k / 6.0))
        c.rect(x, rb, x, wl, C("341c27"))           # the body, out of the light
        c.rect(x, rt + 1, x, rb - 1, C("241527"))   # down into the open drum
        if k < -6:
            c.rect(x, rt + 1, x, rb - 1, C("4d2b32"))   # its far inner wall
        c.set(x, rt, C("884b2b"))                   # the far rim, catching it
        c.set(x, rb, C("602c2c"))                   # the near rim
    c.hline(OX - 19, OX + 19, ORY + 12, C("602c2c"))            # one rolling rib
    c.hline(OX - 19, OX + 19, ORY + 13, C("241527"))
    for k in range(3):                                          # a rust bloom
        c.hline(OX - 14 + k, OX - 6 + k * 2, ORY + 17 + k, C("4d2b32"))
    float_wake(OX - 21, OX + 21, OWL, False, 20)

    # ---------------------------------------------------- the sunken car -----
    # REVISION 3.  USER: "the thing beside the door ... it kind of looks like
    # the back of a car or something ... I can't even tell what it is", then
    # "it's more down, towards the bottom left of the picture, it's like
    # cropped.  That's the car thing I'm talking about."
    # they were right on every count.  it stood at x 202-352 with its front
    # half BEHIND the portal's right jamb, so no whole vehicle was ever on
    # screen; what was left was a flat-on rear panel — one lens, no flank, no
    # wheels, no bumper, no plate.  a flat rear at this size is a box.
    # it is rebuilt as a THREE-QUARTER rear view standing in the OPEN FLOOD at
    # the bottom left, where nothing crops it and the water is behind it on
    # every side.  the geometry is a real box: a near vertical corner at
    # (134, 478), a length axis running away up-left and a width axis running
    # away up-right, so the rear face AND the whole near flank are in frame.
    # three faces, three values — top 394a50, flank 202e37, rear 151d28 — the
    # same cel language the walkway uses.  the cut is DEAD LEVEL at the
    # waterline and nothing is drawn below it; it sits to the sills, not to the
    # windows, so the doors, the arches and the bumper are all above water.
    CARW, CARH = 232, 80
    car = Canvas(CARW, CARH)
    X0, WY = 128, 74                      # the near vertical corner, at the water
    LUX, LUY = -108.0, -27.0              # along the car: rear -> nose
    LWX, LWY = 78.0, -9.0                 # across it: near flank -> far side
    HB, HR = 28, 46                       # beltline, roofline, px above water
    BOOT, SCR, RFF, WSC = 0.14, 0.30, 0.56, 0.70      # the profile stations
    TOPF, TOPE = C("394a50"), C("577277")
    FLK, FLKD = C("202e37"), C("151d28")
    RER, RERD = C("151d28"), C("10141f")
    GLS, SHN, SIL = C("090a14"), C("3c5e8b"), C("090a14")

    # python round() is BANKER rounding: round(53.5) is 54 and round(54.5) is
    # also 54, so a plane sampled at exact half pixels drops whole rows.  it
    # punched an every-other-row hole down the middle of the near tail lamp.
    def rnd(z):
        return int(math.floor(z + 0.5))

    def cp(u, v, h):
        return (X0 + u * LUX + v * LWX, WY - h + u * LUY + v * LWY)

    # THE PROFILE IS THE WHOLE ARGUMENT.  two bakes of this were thrown away:
    # a slab with a full-length greenhouse read as a panel van, and adding a
    # bonnet to it only made it a pickup.  what a car has and neither of those
    # had is a THREE-BOX SIDE PROFILE — a boot deck, a raked rear screen, a
    # short crowned roof, a raked windscreen, a bonnet — and a nose that goes
    # down.  it went in nose first and it is lying that way: sink() drops the
    # far end and the bonnet drops 40px further, so the front wing tapers away
    # UNDER the level waterline instead of ending on a vertical wall.
    def sink(u):
        return 12.0 * u

    # REVISION 4.  the nose drop used to be LINEAR at 40px, which laid the whole
    # front on ONE dead-straight 32px diagonal running to a point at the water.
    # a straight edge meeting a flood cannot read as a waterline — a waterline is
    # horizontal everywhere — so the eye read a knife cut instead of a car going
    # under.  the bonnet is CROWNED now: level off the cowl, breaking over about
    # a third of the way along, then diving.  31px at the tip instead of 40 also
    # leaves a real front end standing 12px above the LEVEL waterline, which is
    # what there is to cut.
    # the 4.0 is a COWL STEP, and it is the single thing that stops the front
    # reading as one continuous arc off the windscreen: a real bonnet's near
    # shoulder starts a plane's-thickness BELOW the scuttle, so the silhouette
    # notches there and the top surface has somewhere to be.
    def belt_h(u):
        if u <= WSC:
            return HB - sink(u)
        t = (u - WSC) / (1.0 - WSC)
        return HB - sink(u) - 4.0 - 22.0 * t ** 1.5

    def roof_h(u):
        if u <= BOOT or u >= WSC:
            return belt_h(u)
        if u < SCR:
            return HB + (HR - HB) * (u - BOOT) / (SCR - BOOT) - sink(u)
        if u <= RFF:
            return HR - sink(u)
        return HR - (HR - HB) * (u - RFF) / (WSC - RFF) - sink(u)

    def cquad(pts, col):                  # convex quad, clipped at the water
        span = {}
        for i in range(4):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 4]
            n = int(max(abs(bx - ax), abs(by - ay))) + 1
            for k in range(n + 1):
                t = k / float(n)
                xx = ax + (bx - ax) * t
                yy = rnd(ay + (by - ay) * t)
                a, b = span.get(yy, (1e6, -1e6))
                span[yy] = (min(a, xx), max(b, xx))
        for yy in sorted(span):
            if yy <= WY:
                a, b = span[yy]
                car.hline(rnd(a), rnd(b), yy, col)

    def roof_patch(u0, u1, v0, v1, col):  # a patch lying ON the glazing planes
        cquad([cp(u0, v0, roof_h(u0)), cp(u0, v1, roof_h(u0)),
               cp(u1, v1, roof_h(u1)), cp(u1, v0, roof_h(u1))], col)

    def rear_band(v0, v1, h0, h1, col):   # a band on the rear face, in v/h
        for x in range(int(X0 + v0 * LWX), int(X0 + v1 * LWX) + 1):
            v = (x - X0) / LWX
            yb = WY + v * LWY
            for h in range(int(h0), int(h1) + 1):
                yy = rnd(yb - h)
                if yy <= WY:
                    car.set(x, yy, col)

    def flank_band(u0, u1, h0, h1, col):  # the same on the near flank, in u/h
        for x in range(int(X0 + u1 * LUX), int(X0 + u0 * LUX) + 1):
            u = (x - X0) / LUX
            yb = WY + u * LUY
            for h in range(int(h0), int(h1) + 1):
                yy = rnd(yb - h)
                if yy <= WY:
                    car.set(x, yy, col)

    # the five top planes, back to front along the car.  they are what makes
    # this a solid with length instead of a panel, and the two glazed ones are
    # what makes the length read as a CABIN.
    roof_patch(0.0, BOOT, 0.0, 1.0, TOPF)                   # the boot deck
    roof_patch(BOOT, SCR, 0.0, 1.0, RER)                    # the rear screen
    roof_patch(BOOT + 0.015, SCR - 0.01, 0.07, 0.93, GLS)   # and its glass
    roof_patch(SCR, RFF, 0.0, 1.0, TOPF)                    # the roof
    roof_patch(RFF, WSC, 0.0, 1.0, FLKD)                    # the windscreen
    roof_patch(WSC, 1.0, 0.0, 1.0, TOPF)                    # the bonnet
    roof_patch(0.194, 0.208, 0.18, 0.36, SHN)               # sheen on the rear
    roof_patch(0.240, 0.252, 0.60, 0.72, SHN)               # screen, stepped
    cquad([cp(0.172, 0.22, roof_h(0.172)), cp(0.246, 0.70, roof_h(0.246)),
           cp(0.256, 0.70, roof_h(0.256)), cp(0.182, 0.22, roof_h(0.182))], FLK)
    roof_patch(0.164, 0.186, 0.17, 0.23, FLK)               # the wiper pivot

    for x in range(int(X0 + LUX), X0):                      # the near flank
        u = (x - X0) / LUX
        yb = WY + u * LUY
        rt = rnd(yb - roof_h(u))
        bt = rnd(yb - belt_h(u))
        if rt > WY:
            continue                                        # the nose, gone under
        car.rect(x, rt, x, WY, FLK)
        car.rect(x, WY - 4, x, WY, FLKD)                    # the sill, in shade
        car.set(x, rt, TOPE)
        car.set(x, rt + 1, TOPF)
        if bt - rt > 5:                                     # a greenhouse here
            if 0.20 < u < 0.64:
                car.rect(x, rt + 3, x, bt - 2, GLS)         # the side glass
            car.set(x, bt, TOPE)                            # the beltline
            car.set(x, bt + 1, TOPF)
    for x in range(X0, int(X0 + LWX) + 1):                  # the rear face
        v = (x - X0) / LWX
        yb = WY + v * LWY
        top = rnd(yb - HB)
        car.rect(x, top, x, WY, RER)
        car.set(x, top, TOPE)                               # the boot lip
        car.set(x, top + 1, TOPF)
    car.vline(X0 - 1, WY - HB, WY - 7, TOPF)                # the near corner:
    car.vline(X0, WY - HB, WY - 7, RERD)                    # lit flank against
    car.set(X0 - 1, WY - HB - 1, TOPE)                      # the shaded rear

    # -------------------------------------------------------- the front end --
    # REVISION 4 (user: "the front of the car seems cut off").  they were right.
    # everything forward of the a-pillar was a bare triangular wedge: no bonnet
    # top surface, no wing, no lamp, one long straight diagonal ending in a
    # point.  the front now carries the three things that say "front of a car"
    # from behind — a bonnet TOP PLANE in its own lighter value, the near wing
    # with a shoulder line running forward out of the door, and a lamp — and all
    # of it is cut DEAD LEVEL at WY, the same waterline as the rest of the car.
    # the other half of the fix is at the very end of paint(), under the flood.
    def sh_at(x):                           # the shoulder / bonnet near edge
        u = (x - X0) / LUX
        return WY + u * LUY - roof_h(u)

    nose_x = int(X0 + LUX)
    while sh_at(nose_x) > WY:               # where the bonnet enters the water
        nose_x += 1
    # the bonnet's TOP PLANE.  it is the cowl step's worth of surface, held at a
    # constant 4px so its far edge carries the windscreen base straight on out
    # over the nose, and closed to nothing over the last few px where the plane
    # has turned away and gone under.  a tapered band bulged the silhouette
    # above the scuttle and the whole front read as a bubble.
    for x in range(nose_x, 54):
        th = min(4.0, (x - nose_x) * 1.1)
        if th < 1.0:
            continue
        s = rnd(sh_at(x))
        top = s - int(th)
        car.rect(x, top, x, s, TOPF)
        if th >= 3.0:
            car.set(x, top, TOPE)                           # ONE lit edge only:
        car.set(x, s + 1, TOPF)                             # the far one.  a lit
        # shoulder as WELL as a lit far edge put two bright rails 4px apart down
        # the whole nose and the plane between them read as a stripe.
    # EVERYTHING BELOW HERE IS DELIBERATELY HORIZONTAL.  the bonnet, its top
    # plane and the shoulder all run down-left together, and a lamp or a bumper
    # laid parallel to them just adds another rail — two cuts of this read as
    # whiskers drawn on a wedge.  the lamp and the bumper are level, the way the
    # rear bumper across the back of this same car is level, and crossing the
    # diagonal is what makes the front stop being a wedge.
    car.hline(nose_x, nose_x + 12, WY - 7, TOPF)            # the front bumper,
    car.rect(nose_x, WY - 6, nose_x + 12, WY - 3, FLK)      # wrapped round the
    car.rect(nose_x, WY - 2, nose_x + 12, WY, SIL)          # corner onto the wing
    car.vline(nose_x + 12, WY - 7, WY - 2, FLKD)
    LAMP0, LAMPN = nose_x + 1, nose_x + 10                  # the near headlamp
    LTOP = rnd(sh_at(LAMP0)) + 2
    car.rect(LAMP0, LTOP, LAMPN, LTOP + 6, RERD)            # its recess
    car.rect(LAMP0, LTOP + 1, LAMPN - 1, LTOP + 5, C("394a50"))
    car.hline(LAMP0, LAMPN, LTOP, TOPE)                     # the surround, lit
    car.rect(LAMP0 + 6, LTOP + 1, LAMPN - 1, LTOP + 4, FLKD)   # smashed at the
    car.set(LAMP0 + 6, LTOP + 2, C("577277"))                  # outer corner,
    car.set(LAMP0 + 2, LTOP + 3, C("577277"))                  # one shard left

    for u_ in (0.34, 0.58):                                 # door shut lines
        x = rnd(X0 + u_ * LUX)
        yb = WY + u_ * LUY
        car.rect(x, rnd(yb - belt_h(u_)) + 2, x, WY - 5, RERD)
    flank_band(0.37, 0.53, 7, 17, FLKD)                     # one caved door, and
    flank_band(0.38, 0.52, 13, 13, TOPF)                    # the crease in it
    flank_band(0.25, 0.30, 18, 18, TOPF)                    # two door handles, at
    flank_band(0.45, 0.50, 18, 18, TOPF)                    # the depth it sits to
    for x in range(int(X0 + LUX), 118):                     # the algae collar
        yy = WY - 3 + int(1.4 * math.sin(x / 9.0) + 1.0 * math.sin(x / 23.0))
        car.rect(x, yy, x, WY, C("19332d"))
    for (uc, arx, ary) in ((0.22, 16, 10), (0.76, 13, 7)):  # the wheel arches,
        cx_ = rnd(X0 + uc * LUX)                            # dipping into it
        for dx in range(-arx, arx + 1):
            dy = rnd(((1.0 - (dx / float(arx)) ** 2) ** 0.5) * ary)
            car.rect(cx_ + dx, WY - dy, cx_ + dx, WY, SIL)
            car.set(cx_ + dx, WY - dy, RERD)
            if uc > 0.5 and dy > 1:             # the FRONT arch gets an eyebrow.
                car.set(cx_ + dx, WY - dy - 1, TOPF)        # the wing was 20px
                # of empty grey and every line on it so far had run parallel to
                # the bonnet; an arch curve is the one crease that cannot.
    car.rect(118, WY - 6, 208, WY - 6, TOPF)                # the rear bumper,
    car.rect(118, WY - 5, 208, WY - 2, FLK)                 # standing proud and
    car.rect(118, WY - 1, 208, WY, SIL)                     # shadowed underneath
    rear_band(0.04, 0.22, 8, 20, RERD)                      # both lamp recesses
    rear_band(0.78, 0.96, 8, 20, RERD)
    rear_band(0.06, 0.20, 10, 18, C("a53030"))              # the lens still whole
    rear_band(0.06, 0.20, 18, 18, C("cf573c"))
    rear_band(0.80, 0.94, 10, 18, C("341c27"))              # and the dead one
    rear_band(0.83, 0.91, 12, 16, RERD)
    rear_band(0.80, 0.84, 18, 18, C("cf573c"))              # one surviving shard
    rear_band(0.37, 0.63, 7, 17, RERD)                      # the plate recess
    rear_band(0.37, 0.63, 17, 17, TOPF)
    rear_band(0.39, 0.61, 9, 15, TOPF)                      # the plate itself
    rear_band(0.39, 0.61, 15, 15, TOPE)
    for i, (rrx, rry, rrw, rrh) in enumerate(car_rust):     # rust, as SOLID
        px_ = 30 + int((rrx - 34) * 1.30)                   # patches — wide and
        py_ = 42 + (rry - 41)                               # flat, never dots,
        rh_ = max(2, rrh - 2)                               # and only where
        rc = C("4d2b32") if i % 2 else C("341c27")          # there is car
        for k in range(rh_):
            inset = 1 if (k == 0 or k == rh_ - 1) else 0
            for xx in range(px_ + inset, px_ + rrw + 5 - inset):
                q = car.get(xx, py_ + k)
                if q[3] and q[:3] not in (GLS[:3], SIL[:3]):
                    car.set(xx, py_ + k, rc)
    # ------------------------------------------------------- the wing mirror --
    # it read as a small dark BOX floating over the water, because that is what
    # it was: a 12x11 090a14 square filled 151d28, with a second 090a14 square
    # beside it, both painted out of the same near-black the flood is made of,
    # and both hung clear of a car nothing joined them to.  three things carry a
    # mirror at this size and it now has all three.
    #   the ARM.  x 51-59 at car-row 30, dying inside the flank at the a-pillar's
    #   foot, which is where a wing mirror bolts on.  it is LEVEL on purpose: the
    #   a-pillar and the bonnet shoulder are both long diagonals through this
    #   exact corner, and the first cut of this arm ran down-right parallel to
    #   them and disappeared into them — the same lesson the front bumper and the
    #   headlamp forty lines up already learned.  lit 394a50 along the top with
    #   090a14 under it, so it is a bar with a top face and not a scratch.
    #   the LEAN.  10 wide, 8 tall at the outer end and 7 at the inner: the top
    #   edge climbs 2px across the head and the bottom 3px, so it is a
    #   parallelogram tilted up toward the car and never square-on.  the outer
    #   end is the end nearer the camera, so it is the taller one.
    #   the GLASS.  a 577277 catch across the outer-top corner falling to 394a50
    #   on the diagonal, inset on all four sides in a 202e37 housing with 090a14
    #   under its sill.  the housing is 202e37 and NOT the 151d28 it started as:
    #   against 10141f water a near-black housing has no silhouette at all, only
    #   its lit pixels read, and losing the silhouette is precisely how the old
    #   one ended up a box.
    MX0, MX1 = 42, 51                       # the head, out over the front wing

    def m_top(x):
        return 27 - int((x - MX0) * 0.25)

    def m_bot(x):
        return 34 - int((x - MX0) * 0.35)

    for x in range(MX0, MX1 + 1):
        t, b = m_top(x), m_bot(x)
        car.rect(x, t, x, b, FLK)                   # the housing, a SOLID form: a
        car.set(x, t, TOPF)                         # near-black one had no shape
        car.set(x, b, SIL)                          # against near-black water, so
        if x <= MX0 or x >= MX1 - 1:                # only the lit bits ever read
            continue
        for y in range(t + 1, b):                   # the glass, inset on all four
            k = (x - MX0 - 1) + (y - t - 1)         # sides: the brightest mark in
            car.set(x, y, TOPE if k <= 4 else TOPF) # this corner, split on the
        # diagonal so the face falls away toward the inner bottom corner instead
        # of sitting there as one flat lozenge of light.
    for x in range(MX1, 60):                        # the arm, back into the flank
        car.set(x, 30, TOPF)                        # at the pillar foot: LEVEL,
        car.set(x, 31, SIL)                         # lit on top, shade under
    car.outline_auto(SIL)
    c.img.alpha_composite(car.img, (6, 404))
    c.px = c.img.load()
    float_wake(25, 213, 478, False, 26)

    # ---------------------------------------------- the nose under the flood --
    # PART TWO of REVISION 4, and the half that actually kills the "cut off"
    # read: the front does not STOP at the waterline, it keeps going down.  what
    # is below is seen THROUGH the flood, so it carries no highlight value at
    # all, it is a step dimmer and much flatter than the dry bodywork, and it
    # dissolves with depth instead of ending on an outline.  the surface's own
    # runs then cross back over the top of it — same vocabulary as float_wake()
    # and the mirror, which is what keeps it in the same water as everything
    # else down here.  every roll in this section is AFTER the last float_wake,
    # so nothing already on the canvas re-rolls.
    # the form is drawn SOLID first — a broken-up mass has no shape to read and
    # the first cut of this was invisible.  it is the value that says "under":
    # nothing above 202e37 anywhere in it, and it steps down to the flood's own
    # tone with depth so the far end of the nose fades out instead of ending.
    SUBC = (C("202e37"), C("151d28"), C("10141f"))

    def sub_top(cx):                            # the nose, still going down
        return 479.0 + max(0.0, 26.0 - cx) * 0.80

    def sub_bot(cx):                            # the valance, then the underbody
        if cx <= 30:                            # it has to STAY in the readable
            base = 492.0 + (30 - cx) * 0.10     # half of the ramp: the first cut
        elif cx <= 54:                          # went 20px deep and turned black
            base = 492.0 - (cx - 30) * 0.30
        else:
            base = 484.8 - (cx - 54) * 0.42
        # the front wheel, as a LOBE of the hull and not a shape of its own.  a
        # separate dark ellipse read as one more sunk tyre floating loose in the
        # flood, which this picture already has one of, thirty pixels away.
        return base + 7.0 * max(0.0, 1.0 - ((cx - 50) / 16.0) ** 2) ** 0.6

    for cx in range(12, 70):
        t0 = int(sub_top(cx) + 0.8 * math.sin(cx / 6.0) + 0.6 * math.sin(cx / 13.0))
        b0 = int(sub_bot(cx) + 1.2 * math.sin(cx / 8.0 + 2.0))
        if b0 - t0 < 1:
            continue
        for y in range(max(479, t0), b0 + 1):   # never above 479: 477 and 478
            d = y - 478                         # still belong to the DRY car
            c.set(cx, y, SUBC[0] if d < 9 else (SUBC[1] if d < 15 else SUBC[2]))
        # the ramp used to step down every three rows and the whole forward half
        # of the nose landed on 151d28 and 10141f — which is what the FLOOD is
        # made of, so it was drawn and invisible.  the body holds 202e37 while
        # there is still a body to see, and only then dissolves into the water.
        if t0 > 480:                            # the plane, still catching what
            c.set(cx, t0, SUBC[0])              # little light gets down there
        c.set(cx, b0, SUBC[2])                  # and the dark under the sill
    for i in range(18):                         # and the chop running over it —
        ry = 479 + rng.randrange(0, 21)         # the same LIFT the flood's own
        rx = 4 + rng.randrange(0, 56)           # surface texture is built from,
        ln = rng.randint(9, 32)                 # so the two agree
        x = rx
        while x < rx + ln:
            run = rng.randint(4, 12)
            if rng.random() < 0.72:
                for xx in range(x, min(x + run, rx + ln)):
                    yy = ry + int(1.2 * math.sin(xx / 11.0 + i))
                    col = LIFT.get(c.get(xx, yy)[:3])
                    if col is not None:
                        c.set(xx, yy, col)
            x += run + rng.randint(2, 7)
    x = 4                                       # and the ring it pushes up,
    while x < 46:                               # broken into runs like the
        run = rng.randint(3, 10)                # crate's and the drum's
        if rng.random() < 0.62:
            for xx in range(x, min(46, x + run)):
                t = (xx - 4) / 42.0
                yy = 478 + int(2.4 * math.sin(t * math.pi)
                               + 0.9 * math.sin(t * 8.0))
                c.set(xx, yy, C("394a50"))
                c.set(xx, yy + 1, C("202e37"))
        x += run + rng.randint(1, 6)

    return c


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
