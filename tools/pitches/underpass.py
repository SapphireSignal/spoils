"""the underpass — transit's road ducking under the rail line, flooded and
never drained: one failing sodium tube on the right, grey daylight in the far
mouth on the left, a car sunk to its windows between them, and the whole
picture repeated, broken, in the water.

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
    never crosses the button box.  landing sites: the car roof (y 338), open
    water (y 409), the walkway kerb (y 388).
  * the walkway pool and the wall halo are baked here; a breathing glow
    goes on top of them, it does not replace them.
  * the water's dashes are baked at rest.  three (not five) surface strips
    would re-sort the bands under the mouth and under the lamp.

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
    C("394a50")[:3]: C("202e37"), C("577277")[:3]: C("394a50"),
    C("819796")[:3]: C("577277"), C("a8b5b2")[:3]: C("577277"),
    C("c7cfcc")[:3]: C("819796"), C("ebede9")[:3]: C("a8b5b2"),
    C("602c2c")[:3]: C("341c27"), C("884b2b")[:3]: C("602c2c"),
    C("be772b")[:3]: C("884b2b"), C("de9e41")[:3]: C("be772b"),
    C("e8c170")[:3]: C("be772b"), C("e7d5b3")[:3]: C("de9e41"),
    C("ad7757")[:3]: C("884b2b"),
    C("a53030")[:3]: C("752438"), C("cf573c")[:3]: C("a53030"),
    C("3c5e8b")[:3]: C("253a5e"), C("25562e")[:3]: C("19332d"),
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
        q = max(0.0, 1.0 - max(abs(x - 480) / 168.0,
                               abs(y - 300 + 4.0 * math.sin(y / 23.0)) / 122.0))
        f = 1.0 - 0.85 * q
        return max(0.0, lm + w) * f, max(0.0, ll + w) * f

    def wall_col(x: int, y: int, bias: float = 0.0, cold_only: bool = False):
        lm, ll = levels(x, y)
        if ll > lm and not cold_only:
            return WARM[max(0, min(6, int(1.0 + ll * 5.6 + bias + 0.5)))]
        return COLD[max(0, min(3, int(1.0 + lm * 2.4 + bias + 0.5)))]

    def wob(x: int, a1: float, p1: float, a2: float, p2: float, ph: float = 0.0):
        return a1 * math.sin(x / p1 + ph) + a2 * math.sin(x / p2 + ph * 1.7)

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
    jx = -rng.randint(0, 40)
    while jx < SCENE_W:
        step = rng.randint(96, 140) if PANEL_L - 30 < jx < PANEL_R else rng.randint(44, 68)
        jx += step
        if not (0 < jx < SCENE_W):
            continue
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
    fy = WALL_TOP + rng.randint(18, 30)
    while fy < WATER_Y - 6:
        ph = rng.uniform(0.0, 6.0)
        for x in range(SCENE_W):
            inp = PANEL_L <= x <= PANEL_R
            sy = fy + int(wob(x, 2.4, 47.0, 1.7, 113.0, ph))
            c.set(x, sy, wall_col(x, sy, -0.9 if inp else -1.7, inp))
            c.set(x, sy + 1, wall_col(x, sy + 1, 0.5 if inp else 0.6, inp))
        fy += rng.randint(62, 98)

    # recessed form-tie marks, only in the lit right third where they read
    for i in range(6):
        tx = rng.randrange(628, 936)
        ty = rng.randrange(168, 330)
        c.rect(tx, ty, tx + 1, ty + 1, wall_col(tx, ty, -2.5))
        c.hline(tx - 1, tx + 2, ty - 1, wall_col(tx, ty - 1, 1.6))

    # wet streaks running down off the deck line — solid runs, never dots.
    # the extra ones on the right are load-bearing: banded radial light on
    # smooth concrete reads as a bullseye until something keeps crossing it.
    for i in range(28):
        wx = rng.randrange(8, SCENE_W - 8) if i < 15 else rng.randrange(600, 950)
        if PANEL_L - 6 < wx < PANEL_R + 6 or 84 < wx < 300:
            continue
        wy = WALL_TOP + rng.randint(2, 26)
        ln = rng.randint(22, 96)
        for y in range(wy, min(WATER_Y - 4, wy + ln)):
            sx = wx + (1 if (y - wy) > ln * 0.7 else 0)
            c.set(sx, y, wall_col(sx, y, -1.6))
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

    # the empty stretch between the portal and the trough gets a wall scupper
    # and the salt stain running out of it — structure, not filler, and it is
    # the only thing left of the buttons that carries any detail.
    c.rect(316, 214, 344, 226, C("151d28"))
    c.rect(318, 216, 342, 224, C("090a14"))
    for k in range(4):
        c.vline(321 + k * 6, 216, 224, C("202e37"))
    c.hline(315, 345, 213, wall_col(330, 213, 1.5))
    # a SOLID widening smear, not scattered patches: blob() wanders into thin
    # trails at this scale and the first cut read as scratches on the wall.
    for y in range(228, 352):
        t = (y - 228) / 124.0
        half = int(4 + 17 * t)
        sc = 330 + int(2.5 * math.sin(y / 19.0) + 1.8 * math.sin(y / 41.0))
        for x in range(sc - half, sc + half + 1):
            e = abs(x - sc) / float(half)
            if e < 0.56:
                c.set(x, y, wall_col(x, y, -1.5))
            elif e < 0.92:
                c.set(x, y, wall_col(x, y, -0.7))
    for k in range(3):
        sx = 323 + k * 6
        for y in range(227, 227 + rng.randint(70, 116)):
            c.set(sx + (y - 227) // 34, y, wall_col(sx, y, -2.2))
    for y in range(330, 352):                        # algae where it pools
        sc = 330 + int(2.5 * math.sin(y / 19.0))
        c.hline(sc - 8 - (y - 330) // 3, sc + 7 + (y - 330) // 4, y, C("19332d"))

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

    # the flooded road running out — the mouth's only perspective cue, and the
    # brightest large area in the frame: the three top cold values live here
    # and NOWHERE else, which is what stops this reading as a second drain.
    for y in range(262, WATER_Y):
        c.hline(OX0, OX1, y, C("577277"))
    t = 0
    y = WATER_Y - 1
    while y > 264:
        depth = (y - 262) / 144.0
        run = max(2, int(2 + 7 * depth))
        for k in range(run):
            yy = y - k
            half = int(2 + 26 * ((yy - 262) / 144.0))
            cl = 198 + int((yy - 262) * 0.13)
            c.hline(max(OX0, cl - 1), min(OX1, cl + 1), yy, C("a8b5b2"))
            c.hline(max(OX0, cl - half - rng.randint(2, 9)),
                    max(OX0, cl - half), yy, C("819796"))
            c.hline(min(OX1, cl + half), min(OX1, cl + half + rng.randint(2, 9)),
                    yy, C("819796"))
        y -= run + max(2, int(2 + 6 * depth))
    for i in range(34):                                        # broken pale water
        wy = rng.randrange(266, WATER_Y)
        wx = rng.randrange(OX0, OX1 - 4)
        c.hline(wx, wx + rng.randint(3, 14), wy, C("819796"))
    for i in range(30):
        wy = rng.randrange(266, WATER_Y)
        wx = rng.randrange(OX0, OX1 - 3)
        c.hline(wx, wx + rng.randint(3, 12), wy, C("394a50"))
    for i in range(12):
        wy = rng.randrange(280, WATER_Y)
        wx = rng.randrange(OX0, OX1 - 3)
        c.hline(wx, wx + rng.randint(2, 8), wy, C("202e37"))

    # ---------------------------------------------------- the sunken car -----
    # three-quarter rear view, nose away toward the mouth, sills at the
    # waterline.  built on its own canvas so the far flank's lit rim can be
    # walked down the true silhouette edge, then composited.
    CW, CH = 180, 78
    CAR_X, CAR_Y = 180, 332
    car = Canvas(CW, CH)

    def span(ly: int):
        if ly < 4:
            return None
        if ly < 12:
            u = (ly - 4) / 8.0
            return int(58 - 14 * u), int(130 + 16 * u)
        u = (ly - 12) / 62.0
        return int(44 - 22 * u), int(146 + 26 * u)

    for ly in range(4, CH):
        s = span(ly)
        if s is None:
            continue
        x0, x1 = s
        x1 = min(CW - 1, x1)
        if ly < 11:                                            # roof top face
            for lx in range(x0, x1 + 1):
                car.set(lx, ly, C("394a50") if lx < 92 else C("202e37"))
        elif ly < 37:                                          # greenhouse
            car.rect(x0, ly, x1, ly, C("151d28"))
        elif ly < 49:                                          # boot deck
            car.rect(x0, ly, x1, ly, C("202e37"))
        else:                                                  # flank at water
            car.rect(x0, ly, x1, ly, C("151d28"))
    for ly in range(12, 36):                                   # the rear glass
        s = span(ly)
        x0, x1 = s
        car.rect(x0 + 15, ly, min(CW - 1, x1) - 16, ly, C("090a14"))
    for ly in range(15, 18):                                   # sheen, stepped
        s = span(ly)                                           # so it reads as a
        car.rect(s[0] + 23, ly, s[0] + 58, ly, C("3c5e8b"))    # reflection and
    for ly in range(17, 20):                                   # not an led bar
        s = span(ly)
        car.rect(s[0] + 64, ly, s[0] + 86, ly, C("3c5e8b"))
    for ly in range(20, CH):                                   # rear panel, near
        s = span(ly)
        if s is None:
            continue
        car.rect(max(s[0], 146), ly, min(CW - 1, s[1]), ly, C("10141f"))
    s = span(37)
    car.hline(s[0], min(CW - 1, s[1]), 37, C("577277"))        # boot lip
    car.hline(s[0], min(CW - 1, s[1]), 38, C("394a50"))
    car.rect(160, 40, 170, 48, C("a53030"))                    # intact tail lens
    car.hline(160, 170, 40, C("cf573c"))
    car.rect(150, 42, 156, 48, C("341c27"))                    # smashed to a socket
    car.hline(150, 156, 42, C("10141f"))
    for ly in range(4, CH):                                    # far flank rim
        s = span(ly)
        if s is None:
            continue
        car.set(s[0], ly, C("577277"))
        if ly > 30:
            car.set(s[0] + 1, ly, C("394a50"))
    for i in range(5):                                         # rust, as SOLID
        rx = rng.randrange(34, 160)                            # patches: blob()
        ry = rng.randrange(41, 60)                             # wanders into
        rw, rh = rng.randint(5, 13), rng.randint(3, 6)         # scrawls here
        col = C("4d2b32") if i % 2 else C("341c27")
        for k in range(rh):
            inset = 1 if (k == 0 or k == rh - 1) else 0
            car.rect(rx + inset, ry + k, rx + rw - inset, ry + k, col)
    for ly in range(62, 74):                                   # algae collar
        s = span(ly)
        if s is None:
            continue
        for lx in range(s[0], min(CW - 1, s[1]) + 1):
            if ly > 63 + int(1.6 * math.sin(lx / 11.0) + 1.1 * math.sin(lx / 27.0)):
                car.set(lx, ly, C("19332d"))
    c.img.alpha_composite(car.img, (CAR_X, CAR_Y))
    c.px = c.img.load()

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

    # sandbags: three slumped courses.  BULGED, chamfered and half-lapped —
    # the first bake stacked squared-off blocks in even courses and the whole
    # pile read as sawn timber.
    bag_rows = ((389, 0, 794), (376, 11, 780), (364, 24, 758))
    for (row_y, shift, stop) in bag_rows:                      # a heap that
        bx = 698 + shift + rng.randint(-3, 3)                  # tapers, not a
        while bx < stop:                                       # tidy three-high
                                                               # wall
            bw = rng.randint(18, 30)
            bh = rng.randint(11, 15)
            lean = rng.choice((-1, 0, 0, 1))
            drop = rng.randint(-2, 2)
            burst = rng.random() < 0.34
            body = C("7a4841") if rng.random() < 0.5 else C("4d2b32")
            reg = set()
            for k in range(bh):                                # a LOZENGE, not
                u = k / float(bh - 1)                          # a block: the
                inset = 0                                      # squared-off
                if u < 0.22:                                   # first cut read
                    inset = 3 - int(u * 13.6)                  # as sawn timber
                elif u > 0.80:
                    inset = int((u - 0.80) * 19.0)
                sx = bx + inset + int(k * 0.22) * lean
                y = row_y + drop - k
                c.rect(sx, y, bx + bw - inset + int(k * 0.22) * lean, y, body)
                for a in range(sx, bx + bw - inset + 1):
                    reg.add((a, y))
            top = row_y + drop - bh + 1
            c.hline(bx + 4, bx + bw - 4, top, C("ad7757"))     # amber on the top
            c.hline(bx + 3, bx + bw - 3, top + 1, C("884b2b"))
            c.hline(bx + 2, bx + bw - 2, row_y + drop, C("341c27"))
            for k in range(4):                                 # slack, and a tie
                c.set(bx + 5 + k * 5, top + 4 + k, C("341c27"))
            c.vline(bx + 1, top + 3, top + 7, C("341c27"))
            c.vline(bx + bw - 1, top + 4, top + 9, C("341c27"))
            if burst:
                for (qx, qy) in blob(rng, bx + rng.randint(5, max(6, bw - 5)),
                                     row_y + drop - rng.randint(3, bh - 3),
                                     rng.randint(10, 22), reg):
                    c.set(qx, qy, C("25562e"))
                for k in range(rng.randint(6, 14)):            # spilled sand
                    c.hline(bx + 3 + k, bx + 6 + k, row_y + drop + 1 + k // 4,
                            C("341c27"))
            bx += bw + rng.randint(-3, 1)

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

    for y in range(WATER_Y - 4, SCENE_H):
        for x in range(SCENE_W):
            if y >= water_top(x):
                c.set(x, y, C("090a14"))
    # surface chop everywhere, so the middle of the flood is never dead black.
    # solid dashes on wavy lines, thinning downward — never dots.
    for i in range(120):
        dy = rng.randrange(WATER_Y + 3, SCENE_H)
        u = (dy - WATER_Y) / float(SCENE_H - WATER_Y)
        dx = rng.randrange(0, SCENE_W - 40)
        ln = rng.randint(16, 150)
        tone = C("10141f") if rng.random() < 0.62 else C("151d28")
        x = dx
        while x < min(SCENE_W, dx + ln):
            run = rng.randint(4, 13)
            if rng.random() > 0.30 + u * 0.30:
                for xx in range(x, min(SCENE_W, x + run)):
                    yy = dy + int(wob(xx, 1.5, 57.0, 1.1, 131.0, i * 0.9))
                    if yy >= water_top(xx):
                        c.set(xx, yy, tone)
            x += run + rng.randint(3, 12)

    # CRITIC FIX 3: the reflection samples with a factor ABOVE 1.0, so the
    # sky slot, the warm wall and the tube itself all land inside the flood.
    # every mark in here is a 4-14px SOLID dash — no dots, no dither.
    for y in range(WATER_Y, SCENE_H):
        u = (y - WATER_Y) / float(SCENE_H - WATER_Y)
        surv = 0.85 + u * (0.18 - 0.85)
        sy = int(404 - (y - WATER_Y) * 2.1)
        wx = int(3 * math.sin(y * 0.7) + 2 * math.sin(y * 0.23))
        x = rng.randrange(0, 26)
        while x < SCENE_W:
            dl = rng.randint(4, 14)
            if rng.random() < surv:
                for xx in range(x, min(SCENE_W, x + dl)):
                    if y < water_top(xx):
                        continue
                    col = REFLECT.get(c.get(xx + wx, sy)[:3])
                    if col is not None:
                        c.set(xx, y, col)
            x += dl + rng.randint(6, 24)

    # ------------------------------------------------- foreground debris -----
    # all rooted off the bottom edge, each a solid silhouette with exactly one
    # lit face, no two the same shape, size or lean.
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

    for k in range(6):                                          # floating pallet
        sy = 502 + k * 5
        sx = 398 + k * 4
        w = rng.randint(56, 72)
        c.rect(sx, sy, sx + w, sy + 2, C("090a14"))
        c.hline(sx, sx + w, sy, C("202e37"))
        c.hline(sx, sx + w, sy + 1, C("151d28"))
    c.rect(400, 500, 404, 532, C("090a14"))
    c.rect(458, 504, 462, 534, C("090a14"))
    c.vline(400, 500, 532, C("151d28"))
    c.vline(458, 504, 534, C("151d28"))

    for k in range(200):                                        # a drowned cable
        u = k / 199.0
        cx_ = 300 + int(u * 268)
        cy_ = 452 + int(math.sin(u * 2.7 + 0.4) * 26 + u * 34)
        if cy_ >= water_top(cx_):
            c.set(cx_, cy_, C("151d28"))
            c.set(cx_, cy_ + 1, C("090a14"))

    cx0, cy0 = 738, 480                                         # plastic crate
    c.rect(cx0, cy0, cx0 + 44, cy0 + 30, C("602c2c"))
    c.rect(cx0 + 3, cy0 + 4, cx0 + 41, cy0 + 27, C("341c27"))
    for k in range(4):
        c.vline(cx0 + 9 + k * 9, cy0 + 5, cy0 + 26, C("602c2c"))
    c.hline(cx0 - 3, cx0 + 47, cy0 - 3, C("884b2b"))            # lit top, amber
    c.rect(cx0 - 3, cy0 - 2, cx0 + 47, cy0 - 1, C("602c2c"))
    c.hline(cx0 - 3, cx0 + 47, cy0, C("341c27"))

    for k in range(74):                                         # drifting plank
        px = 566 + k
        py = 528 + int(k * 0.09)
        c.rect(px, py, px, py + 6, C("151d28"))
        c.set(px, py, C("202e37"))
    c.vline(640, 534, 540, C("090a14"))

    ox0, oy0 = 862, 496                                         # oil drum, leaning
    for k in range(40):
        lean = k // 13
        half = 21 - abs(k - 26) // 7
        c.hline(ox0 - half + lean, ox0 + half + lean, oy0 + k, C("341c27"))
        c.hline(ox0 + half - 5 + lean, ox0 + half + lean, oy0 + k, C("4d2b32"))
        c.set(ox0 - half + lean, oy0 + k, C("241527"))
        c.set(ox0 + half + lean, oy0 + k, C("602c2c"))
    for k in range(-20, 21):                                    # the open top
        dy = int((1.0 - (k / 20.0) ** 2) ** 0.5 * 6)
        c.vline(ox0 + k, oy0 - dy, oy0 + dy, C("341c27"))
        c.set(ox0 + k, oy0 - dy, C("884b2b"))
        c.set(ox0 + k, oy0 + dy, C("602c2c"))
    for ry in (oy0 + 12, oy0 + 27):                             # rolling ribs
        c.hline(ox0 - 19 + (ry - oy0) // 13, ox0 + 19 + (ry - oy0) // 13,
                ry, C("602c2c"))
        c.hline(ox0 - 19 + (ry - oy0) // 13, ox0 + 19 + (ry - oy0) // 13,
                ry + 1, C("341c27"))

    return c


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
