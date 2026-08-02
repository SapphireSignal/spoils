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
    for (sx, sy) in ((112, 44), (238, 78), (604, 36)):
        c.set(sx, sy, C("577277"))


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
def _road(c: Canvas, rng: random.Random) -> None:
    for x in range(0, BOOTH_L + 4):
        rt = road_top(x)
        for y in range(rt, SCENE_H):
            c.set(x, y, C("151d28"))
        c.set(x, rt, C("10141f"))
        c.set(x, rt + 1, C("172038"))
    # ruts: wavy SOLID lines running with the road, rolled width
    for i in range(4):
        x0 = rng.randrange(40, 480)
        drift = rng.uniform(-0.55, -0.15)
        wdt = rng.randint(2, 4)
        ph = rng.uniform(0, 6.0)
        y = road_top(x0) + rng.randint(6, 22)
        while y < SCENE_H:
            xx = int(x0 + (y - 450) * drift + 5.0 * math.sin(y / 29.0 + ph))
            for k in range(wdt):
                c.set(xx + k, y, C("10141f"))
            y += 1
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
    # THE WINDOW'S SPILL ON THE TARMAC — the light's proof on the ground.
    # It EMANATES from behind the booth's left corner rather than floating as
    # an ellipse in the middle of the road (the first render read as a rug):
    # long in x, shallow in y, sheared down-left, and cut hard by the booth.
    # kept SMALL and low on the ladder on purpose: two earlier cuts made it
    # the largest bright shape in the frame and it beat the man's face.
    for x in range(330, BOOTH_L + 2):
        t = min(1.0, (BOOTH_L - x) / 236.0)      # 0 at the booth, 1 far left
        cy = 478 + t * 26                        # the wedge drops as it goes
        hh = 9 + t * 23                          # and widens
        for y in range(452, SCENE_H):
            d = abs(y - cy) / hh
            d += 0.12 * math.sin(x / 27.0) + 0.09 * math.sin(y / 12.0)
            if d < 1.0 and y >= road_top(x):
                if d < 0.22 and t < 0.34:
                    col = C("884b2b")     # a small hot core near the booth,
                elif d < 0.34:            # so the smear reads as LIGHT and
                    col = C("602c2c")     # not as a stain on the tarmac
                elif d < 0.68:
                    col = C("4d2b32")
                else:
                    col = C("341c27")
                c.set(x, y, col)
    # a couple of solid wear scars, never speckle
    region = {(x, y) for y in range(455, SCENE_H) for x in range(20, 540)}
    for i in range(3):
        for (qx, qy) in blob(rng, rng.randrange(60, 500),
                             rng.randrange(470, 530),
                             rng.randint(30, 90), region):
            c.set(qx, qy, bump(c.get(qx, qy), -1))


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
    # a vent grille — structural detail, and the only thing in that quarter
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


def _tallies(c: Canvas, rng: random.Random) -> None:
    """the count. Every stroke is a GROOVE — 2px of board colour with a
    highlight on its lamp side. The variation here is load-bearing, not
    garnish: rolled heights, wobbling baselines drifting downhill, two
    groups left short, one cross-stroke going the wrong way, one group cut
    much deeper, and one patch rollered over with the count restarted."""
    def group(gx: int, gy: int, n: int, deep: bool, dim: bool) -> int:
        groove = C("090a14") if deep else C("341c27")
        hi = C("394a50") if dim else C("819796")
        xs = []
        x = gx
        for i in range(n):
            h = rng.randint(9, 14)
            yy = gy + rng.randint(-2, 2)
            c.vline(x, yy, yy + h, groove)
            c.vline(x + 1, yy, yy + h, groove)
            c.vline(x - 1, yy + 1, yy + h, hi)
            xs.append((x, yy, h))
            x += rng.randint(3, 5)
        if n >= 5:                                   # the cross stroke
            back = rng.random() < 0.25               # one goes the wrong way
            x0, y0, h0 = xs[0]
            x1, y1, h1 = xs[-1]
            span = (x1 + 1) - (x0 - 2)
            for k in range(span):
                u = k / float(max(1, span - 1))
                yy = int((y0 + h0 * 0.75) + (1 - 2 * back) *
                         ((y1 + h1 * 0.25) - (y0 + h0 * 0.75)) * u)
                if back:
                    yy = int((y0 + h0 * 0.25) + ((y1 + h1 * 0.8) -
                             (y0 + h0 * 0.25)) * u)
                c.set(x0 - 2 + k, yy, groove)
                c.set(x0 - 2 + k, yy + 1, hi)
        return x + rng.randint(7, 13)

    # the two crisp ones in the un-glassed strip beside his ear
    y = 214
    for n in (5, 3):
        group(620, y, n, deep=False, dim=False)
        y += rng.randint(30, 38)
    # a rollered-over patch on the right wall, with the count restarted on it
    for py in range(244, 288):
        wobx = int(3.0 * math.sin((py - 244) / 9.0))
        for px in range(790 + wobx, 842 - wobx):
            c.set(px, py, C("394a50") if py < 276 else C("202e37"))

    # the rest, behind the glass where the sheen softens them
    row_y = 208
    for row in range(3):
        gx = 750 + rng.randint(-4, 6)
        while gx < 842:
            n = 5
            if rng.random() < 0.18:
                n = rng.randint(2, 4)                # left incomplete
            deep = rng.random() < 0.12
            gx = group(gx, row_y + rng.randint(-3, 3), n, deep, dim=True)
        row_y += rng.randint(28, 34)
    # the restarted count, on top of the patch
    group(798, 254, 4, deep=False, dim=True)


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
    _wire(c, rng)
    _tower(c, rng)
    _sign(c, rng)
    _road(c, rng)
    _booth(c, rng)
    _interior(c, rng)
    _warden(c, rng)
    _glass(c, rng)
    _surround(c, rng)
    _counter(c, rng)
    _lamp_and_ledger(c, rng)
    _hand(c, rng)
    _boom(c, rng)
    return c


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
