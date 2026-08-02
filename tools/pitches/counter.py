"""mara's counter — you are standing at the transit booth, the job is already yours.

BACKDROP PITCH - static scene only, no living layer yet. Unwired: nothing
imports this and gen_art.py never emits it. If the user picks this pitch it
gets promoted into gen_art.py proper; if not, this file is deleted.

CRITIC CORRECTIONS APPLIED (see briefs/counter.md, "THE CRITIC'S FINDINGS"):
  * The second job board is GONE. A cork board with pinned paper sheets is
    the den's one canonically load-bearing object (LORE appendix c) and a
    second one made this read as a zoom on scene 0. The story beat it carried
    survives in a DIFFERENT object language: a steel hook rail of stamped
    district tags with ONE BARE HOOK, the snapped wire loop still on it.
  * The radio rig is GONE for the same reason (den rig x700-894 vs the
    brief's x756-916 — same corner, same needle dial, same cyan lamp bank).
    The cool light it justified now comes from a LIGHT BOX built into the
    counter, so the cold source is at counter level: still uplight, still
    cold, but a drafting table in a booth rather than a second radio wall.
  * The horizon MOVED. Brief lip y=470 / floor y=506 / ceiling y=96 landed
    within 4 px of the drain's WALK_Y 468 / WATER_Y 506 / CEIL_Y 92, and the
    scenes crossfade. Here the lip is 430, the top face is 60 px deep, the
    floor is off the bottom of the frame entirely and the ceiling is 104.
  * Proportion fixes: mara's head dropped so her chin sits ~1.4 head heights
    above her own hands (the brief had 160 px of torso under a 30 px head),
    and the counter top face is 60 px deep so it can actually hold a map
    lying flat (the brief declared 24 px and then put a 46 px map on it).
  * The channel-lamp bank the critic called a cloned grid does not exist any
    more; the hook rail that replaced it is rolled per instance.

THE FOREGROUND FIGURE IS GONE FOR GOOD (user, twice: "just remove that black
hand figure thing it just looks weird, replace it with something else on the
screen so that's not a weak spot" and then "the black arm is still on mara's
screen remove that thing"). It began as your shoulder with a pack strap, was
cut back once to a gloved forearm and hand, and failed again. The "you are
standing here, this is your own body" idea is ABANDONED — no third version, no
other body part, no trace of glove, cuff, keeper or wrist wrap. What took its
place is room, not person: kettle's balance on the counter top (see _scale)
and the counter's own locked cupboard on the front face (see _under_counter).

LIVING LAYER IS DELIBERATELY NOT BUILT. Room is left for it and the static
bake already carries its consequences:
  * the taped splice at (838, 246) has its cf573c pilot bead lit and the
    parts tin below it carries a PERMANENT BAKED SCORCH RING, so the ember
    that will drip there has visibly happened a thousand times already;
  * the light box glass is baked in its steady state so a soft-alpha wash
    can breathe on top of it (in the den the WARM light breathes; here the
    cold one does, which is the inversion the pitch is built on);
  * the work lamp bulb is baked lit but shielded by its shade, so a glow
    overlay can be added later without the bake fighting it.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gen_art import Canvas, C, SCENE_W, SCENE_H

from PIL import Image, ImageFilter

# ------------------------------------------------------------- geometry ------
CEIL_Y = 104          # ceiling / tile boundary (drain is 92, den is 46)
TRUSS_TOP = 18        # the depot roof truss: top chord (purlins land on it)
TRUSS_BOT = 38        # bottom chord — carries the band's ONE lit lip
FAR_Y = 372           # counter's far edge (wobbled per column)
LIP_Y = 430           # counter's near edge — the frame's one hard line
BOX = (662, 392)      # cold source: the light box sunk into the counter
LAMP = (806, 404)     # warm source: the shaded work lamp's pool centre

# the reserved button rectangle. NOTHING is drawn inside it, and every light
# term, bevel and tone bias is multiplied by (1 - quiet) so the wall inside it
# collapses to ONE flat value with no rectangular edge anywhere.
Q_X0, Q_X1, Q_FADE = 372, 588, 56

COOL = ["10141f", "151d28", "202e37", "394a50", "577277"]
# the lamp is SHADED and tipped at the map, so it barely touches the wall. The
# first render gave it a full 5-step ramp and 130 px of reach and the result
# was a brown mound of tile that read as a pile of rubble.
WARM = ["151d28", "241527", "341c27", "4d2b32"]


def quiet(x: int) -> float:
    if Q_X0 <= x <= Q_X1:
        return 1.0
    d = Q_X0 - x if x < Q_X0 else x - Q_X1
    return max(0.0, 1.0 - d / float(Q_FADE))


def band(ramp: list, lv: float):
    """Banded cel light — never dithered, never interpolated."""
    return C(ramp[max(0, min(len(ramp) - 1, int(lv + 0.5)))])


def ell_rows(rx: int, ry: int):
    """Half-widths of an ellipse, row by row. Every round thing in this file
    is built from hlines because Canvas has no circle()."""
    out = []
    for dy in range(-ry, ry + 1):
        t = 1.0 - (dy / float(ry)) ** 2
        out.append((dy, int(rx * (t ** 0.5)) if t > 0 else -1))
    return out


def squig(c: Canvas, x0: int, x1: int, y: int, col) -> None:
    """Unreadable writing — the den's idiom. Suggests words, never spells one
    (the font is lowercase-only and legible text would fight the title)."""
    for x in range(x0, x1):
        if (x - x0) % 9 == 7:
            continue
        c.set(x, y + (1 if math.sin(x * 1.9) > 0.35 else 0), col)


# ================================================================= scene =====
def paint() -> Canvas:
    rng = random.Random("spoils:pitch:counter")
    c = Canvas(SCENE_W, SCENE_H)

    # every long horizontal seam gets two sines of different period so it can
    # never read as a ruled stripe
    far = [FAR_Y + int(round(2.4 * math.sin(x / 83.0) + 1.7 * math.sin(x / 29.0 + 1.7)))
           for x in range(SCENE_W)]

    _ceiling(c)
    lvl = _wall_levels(rng, far)

    # mara goes on her own canvas first so her silhouette can carve a
    # one-step-darker halo out of the tile — the den's baked halo, reversed
    mara = Canvas(SCENE_W, SCENE_H)
    _mara_body(mara, rng)
    _mara_arms(mara, rng)
    _wall_halo(mara, lvl, far)
    _wall_paint(c, rng, lvl, far)

    _clock(c, rng, 92, 176, 32)
    _tally(c, rng)
    _hook_rail(c, rng)
    _cables(c)

    _counter(c, rng, far)
    _counter_left(c, rng, far)
    _light_box(c, rng)
    _job_sheet(c, rng)
    _mug(c, rng)
    _parts_tin(c, rng)

    c.img.alpha_composite(mara.img, (0, 0))
    c.px = c.img.load()
    _work_lamp(c, rng)

    _under_counter(c, rng)               # the counter's left third,
    _scale(c, rng)                       # top face and front face
    return c


# ---------------------------------------------------------------- ceiling ---
# THE TOP 49 ROWS WERE ONE FLAT 090a14, EDGE TO EDGE (user: "why is there like
# some black border of the whole screen at the top of all of the paintings, it
# seems a bit odd"). They were right, and it is a DEFECT, not the house style:
# measured the same way, the two SHIPPED backdrops art/gen/menu_den.png and
# art/gen/menu_drain.png have ZERO uniform rows in their ceilings. They are
# just as dark up there — the den's joists are 241527 on 090a14, the drain's
# beams are 10141f — but neither ever collapses to a featureless slab. The den
# hangs joists and a dead bulb's flex into it; the drain cuts a manhole throat
# through it. Something is always in it.
#
# This is the old transit maintenance depot, so the ceiling is a depot's: a
# roof truss across the frame with purlins landing on it from above, the
# conduit that already fed the lamp now HUNG OFF that truss instead of floating
# on straps that began in mid-air, an extract duct running off the left edge
# (the whole left half of this band had nothing in it at all — the conduit only
# ever started at x=624), two DEAD pendants, and a capping plate where the tile
# wall stops. That last one does most of the work: black with a hard edge and
# nothing under it reads as a border, and black with a plate under it reads as
# a ceiling.
#
# NOTHING HERE IS LIGHT, and that is the whole constraint. Every value is
# 090a14 / 10141f / 151d28 / 172038 — one step apart at the black end of the
# ramp — plus a SINGLE 202e37 lip on the truss soffit directly over the light
# box, which is the only thing in the room throwing anything upward at all (the
# work lamp is shaded and tipped at the map, which is why it lights none of
# this). MEASURED: top-60-row mean luminance went 11.52 -> 13.20, against a
# ceiling of 14.52. The two shipped backdrops measure 11.74 (drain) and 13.59
# (den) on the same 60 rows, so this now sits BETWEEN them instead of below
# both. Uniform rows in the whole frame: 49 -> 0. Whole-image mean 32.53 ->
# 32.95. This band is still by a long way the darkest part of the picture.
#
# The pendants are DEAD on purpose. A live one would put a third light source
# in a scene whose entire pitch is two — cold box, warm lamp — and it would
# brighten exactly the region that must not brighten.
def _member(c: Canvas, x0: int, y0: int, x1: int, y1: int, bent: bool) -> None:
    """One truss brace, drawn as a 3 px angle — lit edge, body, shade edge — so
    it reads as steel with a section rather than as a ruled line."""
    n = max(1, abs(x1 - x0))
    for k in range(n + 1):
        t = k / float(n)
        bow = math.sin(t * math.pi) * 3.6 if bent else 0.0
        x = x0 + int(round((x1 - x0) * t))
        y = int(round(y0 + (y1 - y0) * t + bow))
        c.set(x, y, C("151d28"))
        c.set(x, y + 1, C("10141f"))
        c.set(x, y + 2, C("090a14"))


def _pendant(c: Canvas, x: int, drop: int, shade: bool) -> None:
    """A dead pendant on its flex. One kept its shade; the other is a bare
    socket with the glass gone — the same object twice would be the clone the
    standing rule bans."""
    def sway(k):
        return x + int(round(math.sin(k / 23.0 + x * 0.7) * 1.7))

    for k in range(drop):
        sx, sy = sway(k), TRUSS_BOT + 5 + k
        c.set(sx, sy, C("151d28"))
        c.set(sx + 1, sy, C("090a14"))
    cx, by = sway(drop), TRUSS_BOT + 5 + drop
    if shade:
        c.rect(cx - 2, by, cx + 3, by + 2, C("151d28"))       # the holder
        c.set(cx + 3, by, C("090a14"))
        for k in range(13):                                    # the cone
            hw = 3 + int(k * 1.15)
            c.hline(cx - hw, cx + hw, by + 3 + k, C("10141f"))
            if k > 8:                                          # you look up
                c.hline(cx - hw + 3, cx + hw - 3, by + 3 + k, C("090a14"))
            c.set(cx - hw, by + 3 + k, C("151d28"))            # lit outer edge
            c.set(cx + hw, by + 3 + k, C("090a14"))
        c.rect(cx - 2, by + 13, cx + 2, by + 15, C("172038"))  # the dead bulb
        c.set(cx - 2, by + 13, C("090a14"))
        c.set(cx + 2, by + 13, C("090a14"))
    else:
        c.rect(cx - 3, by, cx + 3, by + 7, C("10141f"))        # the bare socket
        c.vline(cx - 3, by, by + 7, C("151d28"))
        c.vline(cx + 3, by, by + 7, C("090a14"))
        c.hline(cx - 4, cx + 4, by + 8, C("090a14"))
        for k in range(5):                                     # what is left of
            hw = 4 - abs(k - 1)                                # the glass
            c.hline(cx - hw, cx + hw, by + 9 + k, C("10141f"))
        c.set(cx - 2, by + 10, C("172038"))
        c.set(cx + 2, by + 12, C("090a14"))


def _ceiling(c: Canvas) -> None:
    # IT KEEPS ITS OWN RNG. _ceiling runs before every other draw in paint(),
    # so taking a single number off the scene stream here would re-roll the
    # entire picture underneath it — the mirror image of the builder rule about
    # never SKIPPING a draw. Nothing below y=108 is allowed to move.
    r = random.Random("spoils:pitch:counter:ceiling")
    c.rect(0, 0, SCENE_W - 1, CEIL_Y + 3, C("090a14"))

    # ---- roof deck: two panel seams above the truss, each with a rolled gap
    # so neither can run edge to edge as a ruled line
    for si in range(2):
        sy = 4 + si * 7 + r.randint(0, 2)
        ph, ph2 = r.uniform(0, 6.3), r.uniform(0, 6.3)
        g0 = r.randrange(120, SCENE_W - 300)
        g1 = g0 + r.randint(90, 220)
        for x in range(SCENE_W):
            if g0 <= x < g1:
                continue
            c.set(x, sy + int(round(1.6 * math.sin(x / 91.0 + ph)
                                    + 1.0 * math.sin(x / 27.0 + ph2))),
                  C("10141f"))

    # ---- purlins landing on the truss from above. Spacing, width, depth, wear
    # and the size of the corroded patch are ALL rolled: no two are the same
    # size and no two gaps match.
    purlins = []
    px = -r.randint(6, 44)
    while px < SCENE_W:
        w = r.randint(4, 11)
        dep = TRUSS_TOP + r.randint(-1, 1)
        purlins.append((px, w))
        c.rect(px, 0, px + w, dep, C("10141f"))
        c.vline(px, 0, dep, C("151d28"))                  # lit face
        c.vline(px + w, 0, dep, C("090a14"))              # shade face
        wy = r.randrange(2, dep - 5)                      # ONE solid corroded
        c.rect(px + 1, wy, px + w - 1 - r.randint(0, 2),  # patch, never speckle
               wy + r.randint(2, 5), C("090a14"))
        c.hline(px - 1, px + w + 1, dep - 1, C("151d28"))  # bearing cleat
        c.hline(px - 1, px + w + 1, dep, C("090a14"))
        px += w + r.randint(52, 126)

    # ---- the truss. Its chords are dead straight because rolled steel is
    # machined — the same argument that keeps the counter's near lip straight.
    # What stops a straight full-width run reading as a ruled stripe is that it
    # is CROSSED: purlins bear on it from above, posts stand inside it, hangers
    # drop off it below, and a splice plate interrupts it.
    c.hline(0, SCENE_W - 1, TRUSS_TOP, C("10141f"))
    c.hline(0, SCENE_W - 1, TRUSS_TOP + 1, C("090a14"))
    # the bolted cleats that hold each purlin down sit ON the chord, in front
    # of it — without them the chord's two rows were the only flat lines left
    # in the band, which is the very thing being fixed
    for (px, w) in purlins:
        c.rect(px - 1, TRUSS_TOP, px + w + 1, TRUSS_TOP + 1, C("151d28"))
        c.set(px + w + 1, TRUSS_TOP + 1, C("090a14"))
        c.set(px - 1, TRUSS_TOP + 1, C("10141f"))
    for x in range(SCENE_W):
        c.set(x, TRUSS_BOT, C("090a14"))                  # shaded top of flange
        c.set(x, TRUSS_BOT + 1, C("10141f"))              # the web face
        c.set(x, TRUSS_BOT + 2, C("10141f"))
        d = abs(x - BOX[0])                               # THE ONE LIT LIP
        c.set(x, TRUSS_BOT + 3,
              C("202e37") if d < 32 else (C("172038") if d < 132 else C("151d28")))
        c.set(x, TRUSS_BOT + 4, C("090a14"))

    # posts at ROLLED panel points, and only some bays are braced — a regular
    # zigzag web is exactly the even-spaced repeat the standing rule bans, and
    # a depot truss that has been patched for forty years would not have one.
    pts, x = [], -r.randint(10, 50)
    while x < SCENE_W + 60:
        pts.append(x)
        x += r.randint(46, 104)
    for x in pts:
        pw = r.randint(2, 4)
        c.rect(x, TRUSS_TOP + 2, x + pw, TRUSS_BOT - 1, C("10141f"))
        c.vline(x, TRUSS_TOP + 2, TRUSS_BOT - 1, C("151d28"))
        c.vline(x + pw, TRUSS_TOP + 2, TRUSS_BOT - 1, C("090a14"))
    braced = sorted(r.sample(range(len(pts) - 1), max(3, len(pts) // 3)))
    buckled = braced[r.randrange(len(braced))]            # one has let go
    for i in braced:
        if r.random() < 0.5:
            y0, y1 = TRUSS_BOT - 3, TRUSS_TOP + 3
        else:
            y0, y1 = TRUSS_TOP + 3, TRUSS_BOT - 3
        _member(c, pts[i], y0, pts[i + 1], y1, i == buckled)

    # one splice plate: the truss arrived in lengths and was bolted up on site
    sp = pts[1 + r.randrange(max(1, len(pts) - 3))]
    c.rect(sp - 9, TRUSS_BOT - 4, sp + 12, TRUSS_BOT + 3, C("151d28"))
    c.hline(sp - 9, sp + 12, TRUSS_BOT - 4, C("172038"))
    c.vline(sp + 12, TRUSS_BOT - 4, TRUSS_BOT + 3, C("090a14"))
    c.hline(sp - 10, sp + 13, TRUSS_BOT + 4, C("090a14"))
    for (rx, ry) in ((sp - 5, TRUSS_BOT - 2), (sp + 4, TRUSS_BOT - 2),
                     (sp - 6, TRUSS_BOT + 1), (sp + 7, TRUSS_BOT)):
        c.set(rx, ry, C("090a14"))
        c.set(rx + 1, ry, C("10141f"))

    # ---- hangers. The conduit's three saddles used to START at y=49, in
    # mid-air, holding it up from nothing. They now run to the truss, which is
    # where a conduit in a depot is hung from, and they land BETWEEN the hook
    # rail's wall brackets below (738 / 836 / 916) so the two steel runs read as
    # one install rather than two unrelated props.
    # they start at TRUSS_BOT+3, wrapping the bottom flange, so the two rows
    # under the chord are not left flat either
    for (hx, hy) in ((676, 63), (762, 63), (890, 63), (96, 67), (214, 67)):
        c.rect(hx, TRUSS_BOT + 3, hx + 3, hy, C("151d28"))
        c.vline(hx + 3, TRUSS_BOT + 4, hy, C("10141f"))
        c.vline(hx + 4, TRUSS_BOT + 5, hy, C("090a14"))

    # one conduit, right half only — the title band (x 340..620) stays bare
    for x in range(624, SCENE_W):
        wob = int(round(1.2 * math.sin(x / 47.0)))
        c.set(x, 54 + wob, C("202e37"))
        c.rect(x, 55 + wob, x, 60 + wob, C("151d28"))
        c.set(x, 61 + wob, C("10141f"))
    for bx in (676, 762, 890):                       # conduit saddles
        c.rect(bx, 49, bx + 3, 63, C("151d28"))
        c.vline(bx + 3, 50, 63, C("10141f"))
        c.set(bx, 49, C("202e37"))

    # ---- the extract duct, running off the left edge and capped at a grille.
    DX1, DY0, DY1 = 296, 66, 93
    c.rect(0, DY0, DX1, DY1, C("10141f"))
    c.hline(0, DX1, DY0, C("090a14"))                    # top, in shade
    c.hline(0, DX1, DY1 - 3, C("151d28"))                # lower edge, the only
    c.hline(0, DX1, DY1 - 2, C("151d28"))                # part uplight reaches
    c.hline(0, DX1, DY1 - 1, C("10141f"))
    c.hline(0, DX1, DY1, C("090a14"))
    sph = r.uniform(0, 6.3)                              # one folded seam along
    for x in range(DX1):                                 # its length, so the
        sy = DY0 + 9 + int(round(1.2 * math.sin(x / 53.0 + sph)))   # body is not
        c.set(x, sy, C("090a14"))                        # one flat slab
        c.set(x, sy + 1, C("151d28"))
    for k in range(3):                                   # solid wear, no dots
        wx = r.randrange(4, DX1 - 70)
        wy = r.randrange(DY0 + 13, DY1 - 11)
        c.rect(wx, wy, wx + r.randint(8, 26), wy + r.randint(3, 7), C("090a14"))
    fx = 62
    for k in range(2):                                   # bolted flange joints
        fx += r.randint(78, 132)
        c.rect(fx, DY0 - 2, fx + 4, DY1 + 1, C("151d28"))
        c.vline(fx - 1, DY0 - 1, DY1, C("090a14"))
        c.vline(fx + 5, DY0 - 1, DY1, C("090a14"))
        c.vline(fx + 1, DY0 - 1, DY1, C("172038"))
    c.vline(DX1 - 1, DY0 + 1, DY1 - 1, C("090a14"))      # the end cap
    c.rect(DX1 - 23, DY0 + 5, DX1 - 6, DY1 - 6, C("090a14"))
    for k in range(4):                                   # its louvres
        c.hline(DX1 - 22, DX1 - 8 - r.randint(0, 4),
                DY0 + 7 + k * 4 + r.randint(0, 1), C("151d28"))

    # ---- two dead pendants over the counter. Both clear of the title band
    # (x 340..620): one to its left, past the duct's end, one to its right,
    # hanging cold directly over the light box the room actually works by.
    _pendant(c, 320, 30, True)
    _pendant(c, 692, 28, False)

    # ---- the capping plate. The tile wall was stopping into nothing at all,
    # which is most of why the black above it read as a border rather than as a
    # room. Wobbled by two sines of different period like every other long
    # horizontal seam in this file, so it cannot rule a line across the frame.
    ph, ph2 = r.uniform(0, 6.3), r.uniform(0, 6.3)
    for x in range(SCENE_W):
        py = 103 + int(round(2.0 * math.sin(x / 67.0 + ph)
                             + 1.4 * math.sin(x / 21.0 + ph2)))
        for yy in range(py + 2, CEIL_Y + 4):
            c.set(x, yy, C("090a14"))                    # its shadow on the wall
        c.set(x, py - 2, C("090a14"))
        c.set(x, py - 1, C("10141f"))
        c.set(x, py, C("10141f"))
        c.set(x, py + 1, C("151d28"))                    # the lit soffit
    bx = -r.randint(0, 70)                               # its fixing brackets
    while bx < SCENE_W:
        bw, bh = r.randint(8, 21), r.randint(5, 12)
        c.rect(bx, 99 - bh, bx + bw, 99, C("10141f"))
        c.vline(bx, 99 - bh, 99, C("151d28"))
        c.vline(bx + bw, 99 - bh, 99, C("090a14"))
        c.hline(bx, bx + bw, 99 - bh, C("151d28"))
        bx += bw + r.randint(54, 158)


# ------------------------------------------------------------- the tile wall -
# Glazed transit-authority tile: a THIRD surface language (den = planks,
# drain = brick). Course boundaries are stored as whole arrays so consecutive
# courses share an edge exactly — computing each course's top independently
# left transparent gaps between them, which rendered as bright dashes.
def _wall_levels(rng: random.Random, far: list) -> dict:
    bounds = []
    edges = []
    y = CEIL_Y + 4
    while y < FAR_Y + 10:
        ph, ph2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
        bounds.append([y + (0 if not bounds else
                            int(round(1.5 * math.sin(x / 61.0 + ph)
                                      + 1.0 * math.sin(x / 23.0 + ph2))))
                       for x in range(SCENE_W)])
        # BIG glazed units, deliberately unlike the drain's brick (which is
        # 9-12 px courses on a 22-46 pitch). Same generator, different stone.
        pitch = rng.randint(46, 64)
        e = []
        jx = -rng.randint(0, 30)
        while jx < SCENE_W + 70:
            e.append(jx)
            jx += pitch + rng.randint(-7, 8)
        edges.append({"set": set(e), "list": e, "bias": rng.uniform(-0.5, 0.5)})
        y += rng.randint(17, 22)
    bounds.append([FAR_Y + 14] * SCENE_W)

    lvl = {}
    for ci in range(len(bounds) - 1):
        eset = edges[ci]["set"]
        bias = edges[ci]["bias"]
        top, bot = bounds[ci], bounds[ci + 1]
        for x in range(SCENE_W):
            q = quiet(x)
            s = 1.0 - q
            y0, y1 = top[x], min(far[x], bot[x])
            for yy in range(y0, y1):
                t = (yy - CEIL_Y) / float(FAR_Y - CEIL_Y)
                # lifted from 0.55: the whole frame came back as "dark and low
                # in chroma" and most of this wall was sitting on one step
                base = 0.78 + 1.30 * (t ** 1.6) + bias * s
                dc = ((x - BOX[0]) ** 2 + ((yy - BOX[1]) * 1.30) ** 2) ** 0.5
                # the shade throws almost nothing upward: a wider reach than
                # this built a brown quadrilateral of tile behind her arm that
                # read as a sheet of cardboard
                dw = ((x - LAMP[0]) ** 2 + ((yy - 410) * 0.9) ** 2) ** 0.5
                cold = max(0.0, 1.0 - dc / 190.0) * s
                warm = max(0.0, 1.0 - dw / 46.0) * s
                grout = (yy == y0) or (x in eset and yy > y0)
                bev = 0.0
                if not grout:
                    if yy <= y0 + 2:
                        bev += 0.9                    # glaze catches the top
                    elif yy >= y1 - 2:
                        bev -= 0.9                    # shade under the lip
                    if (x - 1) in eset or (x - 2) in eset:
                        bev += 0.6
                    elif (x + 1) in eset or (x + 2) in eset:
                        bev -= 0.6
                if warm > cold and warm > 0.04:
                    lv, ramp = base + warm * 1.5 + bev * s, 1
                else:
                    lv, ramp = base + cold * 2.1 + bev * s, 0
                lvl[(x, yy)] = [lv, ramp, grout, q, ci]
    lvl["_edges"] = edges
    lvl["_bounds"] = bounds
    return lvl


def _wall_halo(mara: Canvas, lvl: dict, far: list) -> None:
    """One step darker for ~26 px around her whole silhouette, so she pops off
    the tile with no keyline. The den bakes a halo to make a thing brighter;
    this runs the same move backwards."""
    sil = Image.new("L", (SCENE_W, SCENE_H), 0)
    sp = sil.load()
    for y in range(244, 400):
        for x in range(580, 800):
            if mara.px[x, y][3] > 0:
                sp[x, y] = 255
    hp = sil.filter(ImageFilter.GaussianBlur(11)).load()
    for y in range(CEIL_Y + 4, FAR_Y + 14):
        for x in range(572, 812):
            k = (x, y)
            if k not in lvl or sp[x, y]:
                continue
            a = hp[x, y]
            # softened from 1.6/0.85 once she was rescaled: at the old strength
            # a silhouette this size stamped a dark rounded arch on the tile
            # that read as a doorway behind her
            if a > 92:
                lvl[k][0] -= 1.05
            elif a > 24:
                lvl[k][0] -= 0.55


def _wall_paint(c: Canvas, rng: random.Random, lvl: dict, far: list) -> None:
    edges, bounds = lvl.pop("_edges"), lvl.pop("_bounds")
    for (x, y), (lv, ramp, grout, q, ci) in lvl.items():
        if grout:
            c.set(x, y, C("090a14") if q < 0.45 else C("10141f"))
        else:
            c.set(x, y, band(WARM if ramp else COOL, lv))

    # three mismatched replacement tiles — a different batch, a different glaze
    for _ in range(3):
        ci = rng.randrange(2, len(bounds) - 2)
        cand = [e for e in edges[ci]["list"] if 12 < e < SCENE_W - 70
                and quiet(e) < 0.02 and not (560 < e < 820)]
        if not cand:
            continue
        e0 = cand[rng.randrange(len(cand))]
        e1 = min([e for e in edges[ci]["list"] if e > e0] + [e0 + 30])
        for x in range(e0 + 1, e1):
            y0, y1 = bounds[ci][x] + 1, min(far[x], bounds[ci + 1][x]) - 1
            for y in range(y0, y1):
                c.set(x, y, C("202e37") if y > y0 + 1 else C("394a50"))
            c.set(x, y1, C("151d28"))

    # chipped corners: a small SOLID wedge gone, the dark bedding behind it
    for _ in range(12):
        ci = rng.randrange(1, len(bounds) - 1)
        el = edges[ci]["list"]
        ex = el[rng.randrange(1, len(el) - 2)]
        if quiet(ex) > 0.04 or ex < 10 or ex > SCENE_W - 40:
            continue
        sz = rng.randint(4, 9)
        low = rng.random() < 0.5
        for k in range(sz):
            y = (bounds[ci + 1][ex] - 2 - k) if low else (bounds[ci][ex] + 1 + k)
            if not (bounds[ci][ex] < y < far[ex]):
                continue
            c.hline(ex + 1, ex + 1 + (sz - k), y, C("341c27"))
            c.set(ex + 2 + (sz - k), y, C("241527"))


# ----------------------------------------------------------------- props ----
def _clock(c: Canvas, rng: random.Random, cx: int, cy: int, r: int) -> None:
    """A dead station clock: no hands but one bent stub, the glass gone milky.
    Gives the left wall one readable object so it is not only chalk."""
    for (dy, hw) in ell_rows(r + 3, r + 3):
        if hw > 0:
            c.hline(cx - hw, cx + hw, cy + dy, C("090a14"))
    for (dy, hw) in ell_rows(r + 1, r + 1):
        if hw > 0:
            c.hline(cx - hw, cx + hw, cy + dy,
                    C("394a50") if dy < -r // 2 else C("202e37"))
    for (dy, hw) in ell_rows(r - 3, r - 3):
        if hw > 0:
            c.hline(cx - hw, cx + hw, cy + dy,
                    C("202e37") if dy < 2 else C("151d28"))
    for a in range(0, 360, 30):                     # hour ticks, uneven wear
        if rng.random() < 0.18:
            continue
        x = cx + int(math.cos(math.radians(a)) * (r - 7))
        y = cy + int(math.sin(math.radians(a)) * (r - 7))
        c.set(x, y, C("577277"))
        c.set(x, y + 1, C("394a50"))
    for k in range(15):                             # the one bent hand
        c.set(cx + k, cy - k // 3, C("090a14"))
        c.set(cx + k, cy + 1 - k // 3, C("151d28"))
    c.set(cx, cy, C("577277"))
    for k in range(10):                             # a crack across the glass
        c.set(cx - 20 + k * 4, cy - 16 + (k * k) // 6, C("090a14"))
    c.rect(cx - 4, cy - r - 10, cx + 3, cy - r - 3, C("151d28"))
    c.hline(cx - 4, cx + 3, cy - r - 10, C("202e37"))


# ------------------------------------------------------------------ tally ---
# THE COUNT IS CANON: EXACTLY 83 MARKS — sixteen gates of five, plus three
# loose. It is written in LORE.md section 7a ("THE TALLY IS CLOSED") and the
# warden's wall carries the SAME number, because both walls stopped on the
# same day. Nobody is dying out there any more; this is a finished ledger, not
# a running count.
#
# So the count is made STRUCTURAL here, not a thing a later edit can nudge:
# the row plan below is the only place it is stated, every stroke that gets
# drawn is counted as it is drawn, and _tally ends on an assert. Change a row
# and the module CRASHES rather than quietly drifting off canon.
GATE = 5            # the standard tally five: four uprights, one struck through
LONE = 1            # a single upright — nobody came back to close the gate

# (row y, first x, tokens, gap style per gap). "c" crowded, "n" normal,
# "w" wide. These are ANCHORS, not a ruling: every row wanders on a random
# walk, every gap is re-rolled inside its style, and every stroke owns its
# height, lean, weight and where the chalk lifted. The bottom three rows start
# far left because they run UNDER the station clock, which owns x 57-127 down
# to y 211 — that is also why the top three start at x 140 or right of it.
TALLY_ROWS = [
    (118, 148, [GATE, GATE],                    ["w"]),
    (154, 172, [GATE, GATE],                    ["w"]),
    (192, 138, [GATE, LONE, GATE],              ["n", "w"]),
    (230,  38, [GATE, GATE, GATE, GATE],        ["n", "c", "w"]),
    (268,  32, [GATE, GATE, LONE, GATE],        ["c", "w", "n"]),
    (306,  44, [GATE, LONE, GATE, GATE],        ["w", "n", "c"]),
]
GAP = {"c": (13, 18), "n": (23, 30), "w": (36, 46)}

CHALKS = [C("c7cfcc"), C("a8b5b2"), C("819796"), C("577277")]


def _chalk(base: float, rng: random.Random):
    """A stroke's own weight. The wall under the tally only ever runs
    151d28..202e37, so 394a50 chalk is NOT in the ramp — a mark that cannot be
    counted is not a mark. Faintness is the 4th step and is used sparingly."""
    i = int(base + (1 if rng.random() < 0.30 else 0)
            + (1 if rng.random() < 0.10 else 0))
    return CHALKS[max(0, min(3, i))]


def _stroke(c: Canvas, x: int, y: int, h: int, lean: float, col,
            fat: bool, rng: random.Random) -> int:
    """One chalk upright. It can be pressed hard (fat) or lift for a pixel or
    three, but it never breaks so badly that it stops reading as one stroke.
    Returns the rightmost pixel it touched."""
    skip0 = rng.randrange(3, h - 3) if (h > 12 and rng.random() < 0.34) else -1
    skip1 = skip0 + rng.randint(1, 3)
    right = x
    for k in range(h):
        if skip0 <= k < skip1:
            continue                                  # the chalk lifted
        xx = x + int(k * lean)
        c.set(xx, y + k, col)
        right = max(right, xx)
        if fat:
            c.set(xx + 1, y + k, col)
            right = max(right, xx + 1)
    return right


def _gate(c: Canvas, rng: random.Random, x: int, y: int, base: float) -> tuple:
    """Four uprights and one diagonal struck through them: five marks, one
    hand, one day. Returns (marks drawn, rightmost pixel)."""
    hgt = rng.randint(13, 22)
    sp = rng.randint(5, 8)
    lean = rng.uniform(-0.26, 0.26)
    if rng.random() < 0.18:                           # struck at a clear angle
        lean = rng.choice((-1.0, 1.0)) * rng.uniform(0.34, 0.46)
        sp += 2                                       # or the uprights merge
    tilt = rng.uniform(-0.28, 0.28)                   # the baseline drifts too
    marks, right, cx, ups = 0, x, x, []
    for i in range(4):
        h = max(11, hgt + rng.randint(-3, 3))
        yy = y + int(i * sp * tilt)
        fat = rng.random() < 0.32                     # pressed hard
        right = max(right, _stroke(c, cx, yy, h,
                                   lean + rng.uniform(-0.08, 0.08),
                                   _chalk(base, rng), fat, rng))
        ups.append((cx, yy, h))
        marks += 1
        cx += sp + rng.randint(-1, 1) + (1 if fat else 0)

    # the fifth: struck through all four. Most hands run it up to the right,
    # some run it down — that difference is most of what makes six years of
    # different people read as different people.
    (ax, ay, ah) = ups[0]
    (bx, by, bh) = ups[3]
    # the overhang is CLAMPED: a hard-leaning gate used to push the strike out
    # to 40+ px, and at that length it stopped reading as struck-through and
    # started reading as a sixth, horizontal stroke
    x0 = ax - rng.randint(2, 4) + max(-5, int(ah * min(0.0, lean)))
    x1 = bx + rng.randint(3, 5) + min(5, int(bh * max(0.0, lean)))
    ylo = ay + int(ah * rng.uniform(0.72, 0.88))
    yhi = by + int(bh * rng.uniform(0.10, 0.26))
    if rng.random() < 0.25:
        ylo, yhi = by + int(bh * rng.uniform(0.10, 0.26)), \
                   ay + int(ah * rng.uniform(0.72, 0.88))
        ylo, yhi = yhi, ylo                           # ran it downhill instead
    span = max(8, x1 - x0)
    col = _chalk(base, rng)
    fat = rng.random() < 0.30
    for k in range(span + 1):
        xx = x0 + k
        yy = ylo + int((yhi - ylo) * k / float(span))
        c.set(xx, yy, col)
        if fat:
            c.set(xx, yy + 1, col)
        right = max(right, xx)
    marks += 1
    return marks, right


def _tally(c: Canvas, rng: random.Random) -> None:
    """One chalk mark for every raider who went in and did not come out.

    HERS IS THE ROUGH ONE. Six years of traders, whoever was standing there
    when someone did not come back — no ruling, no system, many hands. So the
    rows wander on a random walk, gates crowd in some places and stand apart in
    others, stroke heights swing, some are pressed hard and some are faint, and
    a few are struck at a clear angle.

    The tension to hold: rough enough to read as accumulated, ordered enough
    that a player who zooms in can still walk sixteen gates and three singles.
    That is why the gates are GROUPED into wandering rows instead of scattered
    freely — the previous cut was 12 free-floating clusters of 1-5 strokes,
    which was both the wrong count and too sparse to read as a wall.

    Nothing here crosses x=316, where quiet() starts biting: the reserved
    button rectangle never sees a chalk pixel.
    """
    marks, right = 0, 0
    for (row_y, x_start, tokens, gaps) in TALLY_ROWS:
        x, drift = x_start, 0
        for i, tok in enumerate(tokens):
            # a random WALK, not independent jitter: that is what makes a row
            # wander instead of vibrate. Clamped at 6 px so a cluster cannot
            # sag into the row beneath it and cost the player the count.
            drift = max(-6, min(6, drift + rng.randint(-4, 5)))
            y = row_y + drift
            # ages toward the counter and toward the light on the right; it
            # never fades so far that a mark stops being countable
            base = 0.35 + 1.9 * ((x - 30) / 330.0 + (y - 112) / 260.0) * 0.9
            if tok == GATE:
                n, r = _gate(c, rng, x, y, base)
            else:                                      # one lone upright
                h = rng.randint(12, 21)
                r = _stroke(c, x, y, h, rng.uniform(-0.30, 0.30),
                            _chalk(base, rng), rng.random() < 0.35, rng)
                n = 1
            marks += n
            right = max(right, r)
            x = r + (rng.randint(*GAP[gaps[i]]) if i < len(tokens) - 1 else 0)

    # CANON — LORE.md section 7a. The warden's wall must print the same number.
    assert marks == 83, "tally must be exactly 83 (canon, LORE.md 7a)"
    assert right < 316, "tally must not reach the reserved button band"


def _hook_rail(c: Canvas, rng: random.Random) -> None:
    """The board is gone. This is a steel rail of stamped district tags with
    ONE BARE HOOK, the snapped wire loop still on it: transit came off the
    wall five minutes ago and is on the counter under her hand."""
    x0, x1, ry = 722, 936, 152
    for x in range(x0, x1 + 1):
        c.rect(x + 4, ry + 4, x + 4, ry + 10, C("090a14"))   # shadow on the tile
    c.hline(x0, x1, ry - 5, C("577277"))                     # top face, lit
    c.hline(x0, x1, ry - 4, C("819796"))
    c.rect(x0, ry - 3, x1, ry + 2, C("394a50"))              # front face
    c.hline(x0, x1, ry + 3, C("202e37"))
    c.hline(x0, x1, ry + 4, C("151d28"))
    for bx in (738, 836, 916):                               # wall brackets
        c.rect(bx, ry - 16, bx + 5, ry - 5, C("394a50"))
        c.vline(bx + 5, ry - 15, ry - 6, C("202e37"))
        c.set(bx + 2, ry - 14, C("577277"))

    # STAMPED METAL PLATES, not paper. The first cut made them 30x46 in
    # a8b5b2 with squiggle rows and they read as hanging sheets — which is the
    # exact den echo this rail exists to avoid. They are now small, dark,
    # bevelled and chamfered, and the hook passes through a punched hole.
    hooks, hx = [], x0 + 20
    for _ in range(6):
        hooks.append(hx)
        hx += rng.randint(26, 44)
    bare = 2 + rng.randrange(2)
    for i, hx in enumerate(hooks):
        c.vline(hx, ry - 7, ry + 12, C("819796"))
        c.vline(hx + 1, ry - 6, ry + 11, C("577277"))
        c.set(hx + 2, ry + 12, C("577277"))
        c.set(hx + 3, ry + 11, C("394a50"))
        if i == bare:                                        # THE BARE HOOK
            for k in range(9):                               # a snapped wire
                a = math.radians(20 + k * 34)                # loop, still on it
                c.set(hx + 2 + int(math.cos(a) * 5),
                      ry + 17 + int(math.sin(a) * 5), C("819796"))
            c.set(hx + 8, ry + 21, C("577277"))
            c.set(hx + 10, ry + 24, C("394a50"))
            continue
        w, h = rng.randint(15, 23), rng.randint(21, 31)
        lean = rng.uniform(-0.07, 0.07)
        bent = rng.random() < 0.4
        patina = (i == 1)
        face = C("25562e") if patina else (C("577277") if i % 2 else C("394a50"))
        lit = C("468232") if patina else C("819796")
        shade = C("19332d") if patina else C("202e37")
        tx, ty = hx - w // 2 + rng.randint(-1, 1), ry + 11
        for k in range(h):
            off = int(k * lean) + (1 if bent and k > h - 6 else 0)
            cut = 3 - k if k < 3 else 0                      # chamfered corners
            c.hline(tx + off + cut, tx + w + off - cut, ty + k, face)
            c.set(tx + off + cut, ty + k, lit)
            c.set(tx + w + off - cut, ty + k, shade)
            c.set(tx + w + off - cut + 2, ty + k + 2, C("090a14"))
        c.hline(tx + 3, tx + w - 3, ty, lit)
        c.hline(tx + int(h * lean) + 1, tx + w + int(h * lean) - 1, ty + h - 1, shade)
        c.rect(hx - 1, ty + 3, hx + 1, ty + 5, C("202e37"))  # punched hole
        c.set(hx, ty + 2, shade)
        c.set(hx - 1, ty + 6, lit)
        for ln in range(rng.randint(1, 2)):                  # stamped, unread
            yy = ty + 10 + ln * 6
            squig(c, tx + 4 + int((yy - ty) * lean),
                  tx + w - 3 + int((yy - ty) * lean), yy, shade)
        c.vline(tx + 2 + int(h * lean * 0.4), ty + 8, ty + h - 3, lit)  # sheen


def _cables(c: Canvas) -> None:
    """Visible power: conduit -> drop -> taped splice -> the lamp and the light
    box. Nothing in this scene is on without a wire running to it."""
    for k in range(180):
        t = k / 180.0
        c.set(838 + int(math.sin(t * 2.2) * 2), 64 + int(t * 176), C("090a14"))
        c.set(841 + int(math.sin(t * 2.6 + 1) * 2), 64 + int(t * 176), C("10141f"))
    c.rect(827, 238, 851, 264, C("090a14"))                  # the taped splice
    c.rect(829, 240, 849, 262, C("202e37"))
    for k in range(4):
        c.hline(827, 851, 242 + k * 6, C("151d28"))
        c.hline(827, 851, 243 + k * 6, C("10141f"))
    c.hline(828, 850, 239, C("394a50"))
    c.set(837, 252, C("cf573c"))                             # RED 2: it is live
    c.set(836, 252, C("752438"))
    c.set(838, 252, C("752438"))
    c.set(837, 251, C("602c2c"))
    for (sx, sy, ex, ey, sag) in ((832, 264, 800, 366, 10), (846, 264, 880, 368, 7)):
        for k in range(96):
            t = k / 96.0
            x = int(sx + (ex - sx) * t)
            y = int(sy + (ey - sy) * t + math.sin(t * math.pi) * sag)
            c.set(x, y, C("090a14"))
            c.set(x + 1, y + 1, C("10141f"))


# --------------------------------------------------------------- counter ----
def _counter(c: Canvas, rng: random.Random, far: list) -> None:
    """The spine. Top face 58 px deep, near lip a hard line at 430, the front
    face running off the bottom of the frame — there is NO floor line, which
    is what stops the scene twinning the drain's three horizons."""
    for x in range(SCENE_W):                                 # wall contact
        q = quiet(x)
        # this shadow crosses the button band, so it lightens by a step inside
        # it: a 090a14 line on 151d28 was the highest-contrast thing in there
        c.rect(x, far[x], x, far[x] + 5, C("10141f") if q > 0.5 else C("090a14"))
        c.rect(x, far[x] + 6, x, far[x] + 10,
               C("151d28") if q > 0.5 else C("241527"))
    # top face: base gradient (a horizontal plane reads by getting lighter
    # toward the viewer) + long wobbled grain runs
    grain = set()
    for gi in range(5):
        gy = 390 + gi * 9 + rng.randint(-2, 2)
        for x in range(SCENE_W):
            grain.add((x, gy + int(round(2.0 * math.sin(x / 97.0 + gi)
                                         + 1.3 * math.sin(x / 31.0 + gi * 2.1)))))
    # the top face has to sit at least one step ABOVE the front face or the
    # whole counter reads as a floor — the first render lost exactly that
    for x in range(SCENE_W):
        y0 = far[x] + 11
        for y in range(y0, LIP_Y):
            t = (y - y0) / float(LIP_Y - y0)
            # the step is pushed to t=0.62 so it falls BELOW the button
            # rectangle's floor at y=412 rather than through the middle of it
            # the near strip was lifted a step (4d2b32 -> 602c2c) for the same
            # "dark and low in chroma" note: it also widens the value gap
            # between the far and near halves, which is what makes a
            # horizontal plane read as horizontal
            col = C("341c27") if t < 0.62 else C("602c2c")
            if (x, y) in grain:
                col = C("241527") if t < 0.62 else C("4d2b32")
            c.set(x, y, col)
    # the warm pool: rock steady (in the den the WARM light breathes — here it
    # is the cold one that will, which is the pitch's inversion)
    _pool(c, LAMP, 86, 26, grain, far,
          [(0.20, "e8c170"), (0.40, "de9e41"), (0.62, "ad7757"),
           (0.82, "884b2b"), (1.00, "602c2c")])
    _pool(c, (BOX[0], BOX[1] + 14), 78, 24, grain, far,
          [(0.30, "253a5e"), (0.58, "1e1d39"), (0.82, "411d31"), (1.00, "241527")])
    # the near lip: dead straight, because a counter edge is machined. It is
    # broken instead by the ONE thing that crosses it — the job sheet, pushed
    # half over to your side — and by a value gradient running along its
    # length. (A foreground forearm used to cross it down at the left as well;
    # that object is gone, and nothing was added to cross it in its place. Two
    # crossings and the lip stops reading as an edge at all.)
    for x in range(SCENE_W):
        dw = abs(x - LAMP[0]) / 155.0
        dc = abs(x - BOX[0]) / 170.0
        if dw < 1.0 and dw < dc:
            hi = C("e8c170") if dw < 0.3 else (C("de9e41") if dw < 0.62 else C("ad7757"))
            lo = C("884b2b")
        elif dc < 1.0:
            hi = C("577277") if dc < 0.35 else (C("394a50") if dc < 0.7 else C("4d2b32"))
            lo = C("341c27")
        else:
            hi = C("602c2c") if x > 180 else C("4d2b32")
            lo = C("341c27")
        c.set(x, LIP_Y - 2, hi)
        c.set(x, LIP_Y - 1, hi)
        c.set(x, LIP_Y, lo)
        c.set(x, LIP_Y + 1, C("090a14"))
        c.set(x, LIP_Y + 2, C("090a14"))
    # front face: quiet by design — the changelog button and version label sit
    # at the bottom right and must have nothing to read behind them
    for y in range(LIP_Y + 3, SCENE_H):
        for x in range(SCENE_W):
            # two solid bands with a wobbled boundary — one hard arc read as a
            # big oval stain on the woodwork
            dw = ((x - LAMP[0]) ** 2 + ((y - LIP_Y) * 2.4) ** 2) ** 0.5 \
                + 9.0 * math.sin(x / 41.0) + 6.0 * math.sin(y / 17.0)
            col = C("241527")
            if dw < 138:
                col = C("341c27")
            if dw < 82:
                col = C("4d2b32")
            c.set(x, y, col)
    # two section joints, so the counter is a built thing and not one slab.
    # Both sit well outside the button rectangle.
    for jx in (152, 764):
        for y in range(far[jx] + 11, SCENE_H):
            xx = jx + int(round(1.4 * math.sin(y / 29.0)))
            c.vline(xx, y, y, C("090a14"))
            c.set(xx + 1, y, C("4d2b32") if y < LIP_Y else C("341c27"))
    for gi in range(2):                                      # two grain runs
        gy = 462 + gi * 42
        for x in range(SCENE_W):
            y = gy + int(round(2.6 * math.sin(x / 113.0 + gi * 1.9)
                               + 1.7 * math.sin(x / 37.0 + gi)))
            c.set(x, y, C("090a14"))
            c.set(x, y + 1, C("341c27") if gi == 0 else C("241527"))
    for k in range(52):                                      # one deep gouge
        y = 494 + int(math.sin(k / 17.0) * 3)
        c.set(302 + k, y, C("4d2b32"))
        c.set(302 + k, y + 1, C("090a14"))


def _counter_left(c: Canvas, rng: random.Random, far: list) -> None:
    """Structure for the counter's left third, which rendered as one flat empty
    plane all the way from x=100 to the button band.

    EVERYTHING HERE STOPS SHORT OF x=316, which is where quiet() starts biting;
    the button rectangle (x 372-588, y 290-390) gains nothing at all. The
    drawers sit on the FRONT face's left, nowhere near the version label and
    the changelog button at bottom right.

    Baked with no light source of its own, because there is none over there:
    the tray's brightest pixel is one 394a50 lip line and the only chroma is
    two brass tokens, which is what a dark corner is allowed."""
    # ---- worn patches where forty years of elbows have polished the top face.
    # SOLID shapes with wobbled edges, never speckle. One value step only: the
    # first cut put a 602c2c core inside a 4d2b32 ring and the pair read as two
    # spilled stains rather than wear.
    #
    # THESE RUN ALL THE WAY TO x=576, NOT JUST THE LEFT THIRD. The reserved
    # button rectangle is y 290-390 and the counter's top face starts at ~383,
    # so everything below y=392 is under the buttons, not behind them; it is
    # the one part of that plane structure is allowed into.
    wear = []
    for _ in range(600):
        if len(wear) >= 9:
            break
        wx = 64 + rng.random() * 512
        wy = 396 + rng.random() * 26
        if any(abs(wx - ox) < 62 for (ox, _oy, _r, _s) in wear):
            continue
        wear.append((wx, wy, rng.randint(16, 40), rng.uniform(0, 6.3)))
    for (fwx, fwy, rx, ph) in wear:
        wx, wy = int(fwx), int(fwy)
        ry = max(4, rx // 4)
        for (dy, hw) in ell_rows(rx, ry):
            if hw < 0:
                continue
            hw += int(round(3.0 * math.sin((wy + dy) / 4.4 + ph)
                            + 2.0 * math.sin(wx / 7.0 + ph)))
            y = wy + dy
            if not (far[wx] + 13 <= y < LIP_Y - 3):
                continue
            # ONE tone, which lands a step ABOVE the far half of the top face
            # and a step BELOW the near half. 884b2b on the near half read as
            # spilled lamplight in the middle of the frame.
            c.hline(wx - hw, wx + hw, y, C("4d2b32"))
    # one inlaid expansion strip running the length of the top face — a long
    # structural line the empty middle had nothing of
    for x in range(40, 578):
        y = 404 + int(round(2.2 * math.sin(x / 121.0) + 1.4 * math.sin(x / 33.0 + 2.0)))
        c.set(x, y, C("241527"))
        c.set(x, y + 1, C("602c2c"))
        c.set(x, y + 2, C("341c27"))
    # the middle gouge sits at y=418, not 396: at 396 it was six pixels under
    # the button rectangle's floor and it was the only thing with any contrast
    # anywhere near it
    for (gx, gl, gy) in ((196, 46, 418), (466, 38, 418), (330, 27, 424)):
        for k in range(gl):                              # three solid gouges
            y = gy + int(math.sin(k / 9.0 + gx) * 2)
            c.set(gx + k, y, C("090a14"))
            c.set(gx + k, y + 1, C("602c2c"))

    # ---- the deposit tray, SUNK into the top face. A plate at this angle is a
    # TRAPEZOID: far edge short, near edge long. Reading it as sunk rather than
    # as a mat lying on the wood depends entirely on one thing — you see the
    # FAR inner wall (it faces the room, so it is the lightest surface in the
    # hole) and you do NOT see the near one, because the near lip hides it.
    # The first cut had that inverted and the tray read as a black mat.
    ty0, ty1 = 392, 422
    tfx0, tfx1 = 120, 190
    tnx0, tnx1 = 108, 204

    def tspan(y):
        t = (y - ty0) / float(ty1 - ty0)
        return int(tfx0 + (tnx0 - tfx0) * t), int(tfx1 + (tnx1 - tfx1) * t)

    a, b = tspan(ty0)
    c.hline(a - 3, b + 3, ty0 - 2, C("241527"))            # the cut in the wood
    c.hline(a - 3, b + 3, ty0 - 1, C("090a14"))
    for y in range(ty0, ty1 + 1):                          # the floor
        a, b = tspan(y)
        t = (y - ty0) / float(ty1 - ty0)
        c.hline(a, b, y, C("151d28") if t > 0.55 else C("10141f"))
        c.set(a, y, C("090a14"))
        c.set(b, y, C("090a14"))
    for k in range(7):                                     # THE FAR INNER WALL
        a, b = tspan(ty0 + k)
        c.hline(a + 1, b - 1, ty0 + k,
                C("394a50") if k < 4 else (C("202e37") if k < 6 else C("151d28")))
    a, b = tspan(ty0)
    c.hline(a + 1, b - 1, ty0, C("577277"))                # its top edge, lit
    a, b = tspan(ty1)
    c.hline(a - 2, b + 2, ty1, C("241527"))                # the near lip: wood,
    c.hline(a - 3, b + 3, ty1 + 1, C("4d2b32"))            # not a bright metal
    c.hline(a - 3, b + 3, ty1 + 2, C("602c2c"))            # line
    c.hline(a - 1, b + 1, ty1 - 1, C("090a14"))
    for k in range(2):                                     # two drain slots
        yy = ty1 - 6 - k * 6
        a, b = tspan(yy)
        c.hline(a + 12 + k * 7, b - 16 + k * 5, yy, C("090a14"))
    # two brass tokens lying in it, and a folded chit — the only chroma this
    # corner of the frame gets, and it is deliberately small
    for (bx, by, br) in ((142, 408, 6), (158, 401, 5)):
        for (dy, hw) in ell_rows(br, max(2, br - 3)):
            if hw < 0:
                continue
            c.hline(bx - hw, bx + hw, by + dy, C("884b2b"))
            if dy < 0:
                c.hline(bx - hw + 1, bx + hw - 1, by + dy, C("be772b"))
        c.set(bx - br + 1, by, C("de9e41"))
        c.set(bx + br - 1, by + 1, C("602c2c"))
        c.hline(bx - br + 2, bx + br - 2, by + br + 1, C("090a14"))
    for k in range(7):                                     # the folded chit,
        c.hline(170 + k, 188 + k // 2, 404 + k,            # lying flat, not a
                C("819796") if k < 3 else C("577277"))     # standing cup
    c.hline(170, 188, 403, C("a8b5b2"))
    c.hline(177, 190, 411, C("090a14"))

    # ---- two drawer fronts in the counter's left bay. The counter is a built
    # thing; the front face was one 130 px of unbroken maroon.
    for (dx0, dy0, dx1, dy1) in ((26, 452, 150, 502), (26, 512, 150, 544)):
        c.rect(dx0, dy0, dx1, dy1, C("341c27"))
        c.hline(dx0, dx1, dy0, C("090a14"))
        c.hline(dx0 + 1, dx1 - 1, dy0 + 1, C("4d2b32"))    # lit top bevel
        c.vline(dx0, dy0, dy1, C("090a14"))
        c.vline(dx0 + 1, dy0 + 2, dy1, C("4d2b32"))
        c.vline(dx1, dy0, dy1, C("241527"))
        if dy1 < SCENE_H - 1:
            c.hline(dx0, dx1, dy1, C("090a14"))
            c.hline(dx0 + 1, dx1 - 1, dy1 - 1, C("241527"))
        # the recessed finger pull — a real hole with a lit lower lip
        px0, px1 = dx0 + 38, dx0 + 88
        py = dy0 + 20
        c.rect(px0, py, px1, py + 7, C("090a14"))
        c.hline(px0 + 2, px1 - 2, py + 7, C("4d2b32"))
        c.hline(px0 + 1, px1 - 1, py + 8, C("602c2c"))
        c.hline(px0 + 3, px1 - 3, py, C("241527"))
    for gi in range(3):                                    # grain over the wood
        gy = 466 + gi * 27
        for x in range(30, 148):
            y = gy + int(round(1.9 * math.sin(x / 43.0 + gi * 2.2)
                               + 1.1 * math.sin(x / 17.0 + gi)))
            if 470 < y < 480 or 530 < y < 540:
                continue
            c.set(x, y, C("241527"))


def _pool(c: Canvas, ctr, rx, ry, grain, far, ramp) -> None:
    """A solid BANDED light pool that respects the counter's grain runs, the
    way the den's candle halo respects the plank edges. Its strength is scaled
    by (1 - quiet) so it fades out before the button band instead of being
    clipped by a straight edge."""
    for (dy, hw) in ell_rows(rx, ry):
        if hw < 0:
            continue
        for dx in range(-hw, hw + 1):
            x, y = ctr[0] + dx, ctr[1] + dy
            if not (0 <= x < SCENE_W) or (x, y) in grain:
                continue
            if not (far[x] + 11 <= y < LIP_Y - 2):
                continue
            s = 1.0 - quiet(x)
            d = 1.0 - (1.0 - ((dx / float(rx)) ** 2 + (dy / float(ry)) ** 2) ** 0.5) * s
            for (lim, col) in ramp:
                if d < lim:
                    c.set(x, y, C(col))
                    break


def _light_box(c: Canvas, rng: random.Random) -> None:
    """The cold source, at COUNTER level: a drafting light box sunk into the
    top with the district map lying on it, lit from underneath. This is what
    replaced the radio rig — same uplight on her face, none of the den's
    inventory. Baked in its steady state so a soft-alpha wash can breathe."""
    # A flat plate seen at this angle is a shallow TRAPEZOID, not a rectangle:
    # the first render drew it square and it read as a monitor standing up.
    ny0, ny1 = 382, 422                                      # far / near edges
    nx0, nx1 = 590, 750                                      # near-edge span
    fx0, fx1 = 606, 734                                      # far-edge span

    def span(y):
        t = (y - ny0) / float(ny1 - ny0)
        return int(fx0 + (nx0 - fx0) * t), int(fx1 + (nx1 - fx1) * t)

    for y in range(ny0 - 3, ny1 + 5):                        # recess shadow
        a, b = span(max(ny0, min(ny1, y)))
        c.hline(a - 3, b + 3, y, C("090a14"))
    for y in range(ny0, ny1 + 1):                            # the steel frame
        a, b = span(y)
        c.hline(a, b, y, C("202e37"))
        c.set(a, y, C("394a50"))
        c.set(b, y, C("151d28"))
    a, b = span(ny0)
    c.hline(a, b, ny0, C("151d28"))                          # far lip, in shade
    a, b = span(ny1)
    c.hline(a, b, ny1, C("577277"))                          # near lip, lit
    c.hline(a + 1, b - 1, ny1 - 1, C("394a50"))
    for y in range(ny0 + 4, ny1 - 3):                        # the glass
        a, b = span(y)
        t = (y - ny0) / float(ny1 - ny0)
        c.hline(a + 6, b - 6, y,
                C("253a5e") if t < 0.24 else (C("3c5e8b") if t < 0.82 else C("253a5e")))
    a, b = span(ny0 + 15)
    c.hline(a + 6, b - 6, ny0 + 15, C("73bed3"))             # the one bright line

    # the district map lying on the glass, backlit through the paper
    my0, my1 = ny0 + 4, ny1 - 6
    for y in range(my0, my1 + 1):
        a, b = span(y)
        a, b = a + 12, b - 12
        for x in range(a, b + 1):
            if (x - a) + (y - my0) < 6 or (b - x) + (my1 - y) < 5:
                continue                                     # torn corners
            t = ((x - a) / float(b - a) - 0.5) ** 2 * 2.4 \
                + ((y - my0) / float(my1 - my0) - 0.5) ** 2
            c.set(x, y, C("c7cfcc") if t < 0.13 else C("a8b5b2"))
    ma, mb = span((my0 + my1) // 2)
    ma, mb = ma + 12, mb - 12
    for k in range(3):                                       # fold creases
        fx = ma + 26 + k * 28 + rng.randint(-4, 4)
        for y in range(my0 + 3, my1 - 1):
            c.set(fx + int(math.sin(y / 11.0) * 1.4), y, C("819796"))
    for k in range(4):                                       # the road grid
        yy = my0 + 7 + k * 7
        a, b = span(yy)
        c.hline(a + 16, b - 16, yy + int(math.sin(k * 2.1) * 1.4), C("577277"))
    for k in range(5):
        c.vline(ma + 12 + k * 21, my0 + 5, my1 - 4, C("577277"))
    c.rect(ma + 54, my0 + 17, ma + 68, my0 + 24, C("25562e"))
    c.rect(ma + 11, my0 + 5, ma + 22, my0 + 11, C("172038"))
    for ang in range(0, 360, 8):                             # RED 1: the mark
        c.set(int(ma + 80 + math.cos(math.radians(ang)) * 11),  # she is making
              int(my0 + 19 + math.sin(math.radians(ang)) * 7), C("a53030"))
    squig(c, ma + 5, ma + 36, my1 - 5, C("394a50"))


def _job_sheet(c: Canvas, rng: random.Random) -> None:
    """The transit sheet, already half pushed across to your side. The only
    object that crosses the near lip, which is what makes the lip an edge."""
    x0, y0, w, h = 612, 406, 68, 46
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            if (x - x0) + (y - y0) < 5 or (x0 + w - x) + (y - y0) < 4:
                continue
            near = (y - y0) / float(h)
            col = C("c09473") if near < 0.55 else C("d7b594")
            if x > x0 + w - 3:
                col = C("884b2b")
            c.set(x, y, col)
    c.hline(x0 + 4, x0 + w - 4, y0 + h, C("090a14"))
    c.hline(x0 + 6, x0 + w - 6, y0 + h + 1, C("241527"))
    c.set(x0 + 34, y0 + 5, C("884b2b"))                      # the old pin hole
    c.set(x0 + 35, y0 + 5, C("884b2b"))
    c.set(x0 + 34, y0 + 6, C("602c2c"))
    c.rect(x0 + 7, y0 + 8, x0 + 27, y0 + 11, C("884b2b"))    # heading bar
    for ln in range(4):
        squig(c, x0 + 7, x0 + w - 8 - (16 if ln == 3 else 0),
              y0 + 16 + ln * 7, C("884b2b"))
    for k in range(rng.randint(2, 3)):                       # thumb creases
        c.hline(x0 + 4, x0 + w - 6, y0 + 22 + k * 11, C("c09473"))


def _mug(c: Canvas, rng: random.Random) -> None:
    """Your mug, going cold — said in two colours, no steam. It sits in the
    dark left third: a second-look detail, never a highlight."""
    x0, x1 = 314, 342
    c.rect(x0 + 3, 426, x1 - 1, 429, C("090a14"))
    for y in range(396, 427):
        t = (y - 396) / 31.0
        for x in range(x0, x1 + 1):
            lit = (x - x0) / float(x1 - x0)
            col = C("202e37") if lit < 0.60 else C("172038")
            if lit < 0.13:
                col = C("394a50")
            if t > 0.88:
                col = C("151d28")
            c.set(x, y, col)
    for (dy, hw) in ell_rows(15, 5):
        if hw >= 0:
            c.hline(328 - hw, 328 + hw, 396 + dy, C("394a50"))
    for (dy, hw) in ell_rows(12, 4):
        if hw >= 0:
            c.hline(328 - hw, 328 + hw, 396 + dy, C("341c27"))   # the tea
    for (dy, hw) in ell_rows(12, 4):
        if hw >= 0:
            c.set(328 - hw, 396 + dy, C("4d2b32"))               # cold skin ring
            c.set(328 + hw, 396 + dy, C("4d2b32"))
    c.rect(x0, 406, x1, 411, C("19332d"))                        # a green
    c.hline(x0, x1, 406, C("25562e"))                            # enamel band —
    c.set(x0, 407, C("25562e"))                                  # the dark left
    c.set(x0 + 1, 408, C("25562e"))                              # third's only
    c.hline(x0, x1, 411, C("10141f"))                            # chroma
    c.set(319, 392, C("a8b5b2"))                                 # a chip
    c.set(320, 392, C("a8b5b2"))
    c.set(319, 393, C("819796"))
    for (dy, hw) in ell_rows(8, 8):
        if hw >= 4:
            c.set(x1 + hw - 3, 410 + dy, C("202e37"))
            c.set(x1 + hw - 4, 410 + dy, C("151d28"))
    del rng


def _parts_tin(c: Canvas, rng: random.Random) -> None:
    """The ember's target. The scorch ring is BAKED: what will drip here at
    runtime has visibly been dripping for a thousand nights already."""
    x0, y0, x1, y1 = 818, 396, 858, 420
    c.rect(x0 + 2, y1 + 1, x1 - 1, y1 + 3, C("090a14"))
    c.rect(x0, y0 + 5, x1, y1, C("394a50"))
    c.vline(x1, y0 + 6, y1, C("202e37"))
    c.vline(x0, y0 + 6, y1, C("577277"))
    for (dy, hw) in ell_rows(20, 6):
        if hw >= 0:
            c.hline(838 - hw, 838 + hw, y0 + 5 + dy,
                    C("577277") if dy < 1 else C("394a50"))
    for a in range(0, 360, 7):                                   # scorch ring
        c.set(int(838 + math.cos(math.radians(a)) * 12),
              int(y0 + 5 + math.sin(math.radians(a)) * 3), C("602c2c"))
    for a in range(0, 360, 11):
        c.set(int(838 + math.cos(math.radians(a)) * 7),
              int(y0 + 5 + math.sin(math.radians(a)) * 2), C("4d2b32"))
    c.set(838, y0 + 4, C("241527"))
    c.set(839, y0 + 5, C("241527"))
    for _ in range(rng.randint(2, 4)):                           # small dents
        dx = x0 + 6 + rng.randrange(26)
        c.rect(dx, y1 - 7 - rng.randrange(4), dx + rng.randint(2, 5), y1 - 5,
               C("202e37"))
    c.hline(x0 + 3, x1 - 3, y1 - 2, C("202e37"))


def _work_lamp(c: Canvas, rng: random.Random) -> None:
    """Shaded, clamped to the counter, rock steady. Its bulb is the brightest
    pixel in the frame and the shade shields it so it cannot bloom."""
    c.rect(794, 358, 812, 372, C("202e37"))                      # clamp
    c.hline(794, 812, 358, C("394a50"))
    c.vline(812, 359, 372, C("151d28"))
    c.rect(796, 372, 810, 379, C("151d28"))
    c.set(798, 362, C("577277"))
    for k in range(66):                                          # the stem
        t = k / 66.0
        x, y = int(803 - t * t * 7), int(358 - t * 42)
        c.set(x - 1, y, C("577277"))
        c.set(x, y, C("394a50"))
        c.set(x + 1, y, C("202e37"))
    for k in range(36):                                          # gooseneck
        t = k / 36.0
        a = math.radians(-92 + t * 100)
        x, y = int(778 + math.cos(a) * 22), int(318 + math.sin(a) * 20)
        c.set(x, y - 1, C("577277"))
        c.set(x, y, C("394a50"))
        c.set(x, y + 1, C("202e37"))
    for k in range(27):                                          # the shade
        t = k / 26.0
        hw = int(7 + t * 21)
        x, y = 782 - int(t * 13), 302 + k
        c.hline(x - hw, x + hw, y, C("202e37") if t < 0.5 else C("151d28"))
        c.set(x - hw, y, C("394a50"))
        c.set(x - hw + 1, y, C("394a50") if t < 0.3 else C("202e37"))
        c.set(x + hw, y, C("10141f"))
    c.hline(775, 789, 301, C("394a50"))
    c.hline(777, 787, 300, C("202e37"))
    for k in range(38):                                          # lit inner rim
        c.set(751 + k, 329, C("884b2b"))
        c.set(751 + k, 330, C("de9e41") if 8 < k < 30 else C("ad7757"))
    c.rect(766, 331, 767, 332, C("e7d5b3"))                      # THE bulb
    c.set(765, 331, C("e8c170"))
    c.set(768, 332, C("e8c170"))
    del rng


# ------------------------------------------------------------------ mara ----
# Face 35 px wide and 45 tall, 62 px across with the hair. She was 26x35 and
# the note back was that she is "too small and too generic for a pitch whose
# entire selling point was a face at conversational distance". The whole figure
# was rescaled about (MCX, 392): her HANDS stay exactly where they were on the
# light box and everything grows UPWARD out of them, so the counter, the box,
# the map and the lamp did not have to move an inch.
FY0, FY1 = 280, 324                              # the face box, 35x45
MCX = 681                                        # her centre line


def _face_hw(y: int) -> int:
    """Half-width of the face at row y — an oval that tapers to the chin, not
    a box. The first render drew a rectangle and it read as a slab. The jaw is
    deliberately NOT symmetric: the left side (screen) carries one extra pixel
    from the cheekbone down, which is most of what stops a face this size
    reading as a mannequin."""
    u = (y - FY0) / float(FY1 - FY0)
    if u < 0.13:
        return 14
    if u < 0.60:
        return 17
    if u < 0.76:
        return 16
    return max(4, int(16 - (u - 0.76) * 50))


def _mara_body(c: Canvas, rng: random.Random) -> None:
    """Head, hair, the headset pushed UP OFF her ears, torso and sleeves.

    She looks DOWN at the map: each eye is one dark lid line under a brow and
    there is no mouth expression to get wrong — the two lights do the
    modelling. UPLIGHT, cold from the light box below-left and warm from the
    lamp below-right, so the forehead and crown stay dark. Both shipped scenes
    light from at or above figure height; this one does not.

    THE HEADSET MOVED ONTO HER CROWN. It used to sit on her neck at y 340-351,
    which the shoulders then buried — the render showed no headset at all. On
    top of her head it is visible, it still says off-channel, and it gives the
    crown (the darkest area on her) one hard light structure.

    THE SLEEVES ARE DRAWN HERE, not with the forearms, because the first render
    read as one flat red poncho: torso and upper arm were a single silhouette
    with no seam. They are separate masses now with a shadowed seam between.
    """
    # ---- torso, oxblood jacket (identity carried over from the den)
    shoulder_top = {}
    for y in range(336, 373):
        t = (y - 336) / 37.0
        half = int(25 + (t ** 0.45) * 21)               # a ROUND shoulder — a
        for x in range(MCX - half, MCX + half + 1):     # near-linear taper
            lit = (x - (MCX - half)) / float(2 * half)  # read as a poncho
            col = C("752438")
            if lit < 0.15 or lit > 0.86:
                col = C("411d31")
            c.set(x, y, col)
            shoulder_top.setdefault(x, y)
        c.set(MCX - half, y, C("3c5e8b"))               # cold rim, box side
        c.set(MCX - half + 1, y, C("253a5e"))
        c.set(MCX + half, y, C("884b2b"))               # warm rim, lamp side
        c.set(MCX + half - 1, y, C("602c2c"))
    for x, y in shoulder_top.items():                   # highlight FOLLOWS the
        if abs(x - MCX) > 19:                           # shoulder line instead
            c.set(x, y + 1, C("a53030"))                # of two ruled strokes
            c.set(x, y + 2, C("a53030"))

    # ---- the sleeves: their own masses, hung off the shoulder points and
    # swung out to the elbows, with a seam of jacket shadow between
    def sleeve(sgn):
        for k in range(140):
            t = k / 139.0
            cx_ = MCX + sgn * (30.0 + 38.0 * t + 6.0 * math.sin(t * 2.2))
            cy_ = 344.0 + t * 68.0
            w = 15.0 - 3.0 * t
            roll = t > 0.86                     # the cuff is PART of the sleeve
            for dx in range(-int(w), int(w) + 1):
                x = int(round(cx_ + dx))
                lit = (dx + w) / (2 * w)
                col = C("411d31")
                if 0.24 < lit < 0.78:
                    col = C("752438")
                if roll:
                    col = C("341c27") if 0.18 < lit < 0.82 else C("241527")
                c.set(x, int(cy_), col)
            c.set(int(round(cx_ - w)), int(cy_),
                  C("253a5e") if sgn < 0 else C("341c27"))
            c.set(int(round(cx_ + w)), int(cy_),
                  C("341c27") if sgn < 0 else C("884b2b"))
            if 0.855 < t < 0.875:                          # the roll's lit lip
                for dx in range(-int(w) + 1, int(w)):
                    c.set(int(round(cx_ + dx)), int(cy_), C("a53030"))
        # the seam: a shadow trench where the sleeve head meets the body
        for k in range(30):
            t = k / 29.0
            x = int(MCX + sgn * (28.0 + 5.0 * t))
            c.set(x, 340 + k, C("341c27"))
            c.set(x + sgn, 340 + k, C("241527"))
    sleeve(-1)
    sleeve(1)

    c.rect(MCX - 18, 330, MCX + 17, 341, C("411d31"))   # collar
    c.hline(MCX - 18, MCX + 17, 330, C("752438"))
    c.rect(MCX - 13, 332, MCX + 12, 342, C("341c27"))   # the neck's own shadow
    c.hline(MCX - 18, MCX - 8, 331, C("a53030"))        # a lit collar point,
    c.set(MCX - 19, 332, C("752438"))                   # one side only
    # her enamel district pin, gone green with age — a specific, worn object
    c.rect(MCX + 9, 333, MCX + 15, 338, C("25562e"))
    c.hline(MCX + 9, MCX + 15, 333, C("468232"))
    c.set(MCX + 15, 338, C("19332d"))
    c.set(MCX + 11, 335, C("19332d"))

    # ---- neck, uplit from underneath. Narrower than the first cut, which put
    # a 20 px straight-sided column under her chin, and with the jaw's own
    # shadow laid across the top of it instead of a lone tendon stroke.
    c.rect(MCX - 8, 318, MCX + 7, 342, C("7a4841"))
    c.rect(MCX - 5, 326, MCX + 4, 338, C("ad7757"))
    c.hline(MCX - 8, MCX + 7, 318, C("4d2b32"))
    c.hline(MCX - 8, MCX + 7, 319, C("602c2c"))
    c.hline(MCX - 7, MCX + 6, 320, C("602c2c"))
    c.set(MCX - 8, 321, C("602c2c"))
    c.set(MCX + 7, 321, C("602c2c"))

    # ---- hair. The crown is the darkest thing on her: nothing lights her
    # from above. Built as a rounded mass — a rectangle read as a helmet, and
    # the first cut was ONE flat 4d2b32 with no banding at all.
    for (dy, hw) in ell_rows(30, 31):
        if hw < 0 or dy > 8:
            continue
        c.hline(MCX - hw, MCX + hw, 288 + dy, C("4d2b32"))
        if dy < -16:
            c.hline(MCX - hw, MCX + hw, 288 + dy, C("341c27"))
        if -6 < dy < 3:                                  # the one lit band, on
            c.hline(MCX + hw - 6, MCX + hw, 288 + dy, C("602c2c"))   # the lamp
    # the side masses. Their ends TAPER — a flat cut at a fixed y left two
    # square corners hanging off her head like the bottom of a cardboard wig.
    for k in range(13):
        c.rect(MCX - 30 + k, 290, MCX - 18, 330 - abs(k - 4) * 2, C("4d2b32"))
        c.rect(MCX + 18, 290, MCX + 30 - k, 324 - abs(k - 5) * 2, C("4d2b32"))
    c.vline(MCX - 30, 290, 322, C("341c27"))
    c.vline(MCX + 30, 290, 314, C("602c2c"))            # the lamp finds this side
    c.vline(MCX + 29, 302, 318, C("884b2b"))            # and the ends catch it
    for k in range(7):                                  # loose strands
        c.vline(MCX - 32 - rng.randrange(3), 276 + k * 8, 282 + k * 8, C("341c27"))
    # low ponytail over her right shoulder — a den identity marker
    for k in range(70):
        t = k / 70.0
        px = int(MCX - 34 - t * 10 + math.sin(t * 3.0) * 4)
        w = int(10 - t * 5)
        c.rect(px - w, 296 + k, px + w, 297 + k, C("4d2b32"))
        c.vline(px - w, 296 + k, 297 + k, C("341c27"))
        c.vline(px + w, 296 + k, 297 + k, C("602c2c") if t < 0.55 else C("4d2b32"))
    c.rect(MCX - 52, 356, MCX - 39, 366, C("341c27"))   # its tie
    c.hline(MCX - 52, MCX - 39, 356, C("4d2b32"))

    # ---- the headset, pushed up onto her crown: she is off-channel, talking
    # to you. Baked in its OFF state — no pilot lamp lit on the cup.
    for k in range(160):
        t = k / 159.0
        a = math.radians(191 + t * 158)
        hx = int(MCX + math.cos(a) * 32)
        hy = int(290 + math.sin(a) * 31)
        c.set(hx, hy, C("202e37"))
        c.set(hx, hy + 1, C("394a50"))
        c.set(hx, hy + 2, C("151d28"))
    # BOTH cups, each hung off the band's end by a visible yoke. The first cut
    # ran the band from 196 to 324 degrees, which ends up at the top-right of
    # her crown, and then put the cup 20 px below it with nothing joining them:
    # the render showed a grey box floating beside her temple.
    for (sgn, yx) in ((-1, MCX - 31), (1, MCX + 31)):
        c.rect(yx - 1, 280, yx + 1, 296, C("394a50"))            # the yoke
        c.vline(yx + sgn * 2, 281, 295, C("151d28"))
        cx0 = yx - 6 if sgn > 0 else yx - 5
        for k in range(17):                                      # the ear cup,
            n = 0 if 2 < k < 14 else 1                           # corners eased
            c.hline(cx0 + n, cx0 + 11 - n, 295 + k, C("202e37"))
            c.set(cx0 + n, 295 + k, C("394a50"))
            c.set(cx0 + 11 - n, 295 + k, C("151d28"))
        c.rect(cx0 + 3, 298, cx0 + 8, 308, C("151d28"))          # the pad
        c.hline(cx0 + 2, cx0 + 9, 295, C("577277"))
        c.hline(cx0 + 2, cx0 + 9, 311, C("090a14"))
        c.set(cx0 + 5, 302, C("341c27"))                         # a dead pilot
    for k in range(30):                                          # its lead
        t = k / 30.0
        c.set(int(MCX + 36 + t * 10), int(310 + t * 32 + math.sin(t * 3.0) * 4),
              C("090a14"))
        c.set(int(MCX + 37 + t * 10), int(310 + t * 32 + math.sin(t * 3.0) * 4),
              C("151d28"))

    # ---- the face. UPLIGHT: cold below-left, warm below-right, forehead and
    # crown dark because nothing lights her from above.
    # THE LIGHT IS PLACED BY HAND, NOT RAMPED. A radial ramp was tried and it
    # failed for a structural reason worth writing down: the face is 35 px
    # wide and the source is ~60 px below it, so every iso-distance contour
    # crosses the face almost HORIZONTALLY. Three separate renders produced a
    # full-width value step in the middle of her face and all three read as a
    # man with a moustache. Below the brow the base tone is now CONSTANT, and
    # the light is put on as cheek, nose, jaw and chin shapes.
    for y in range(FY0, FY1 + 1):
        hw = _face_hw(y)
        c.hline(MCX - hw, MCX + hw, y,
                C("7a4841") if y < FY0 + 14 else C("c09473"))
    # NO LIT FOREHEAD. There used to be an 884b2b patch here and the render
    # caught it twice over: it contradicts the whole lighting idea (nothing in
    # this room lights her from above), and its top edge interlocked with the
    # spikes of the fringe so the pair read as a jagged crown on her head.
    # cheekbones. THEY WERE RECTANGLES and at 12x that is exactly what they
    # looked like: two hard-edged squares stuck on her face. They are lozenges
    # now, leaning with the cheek, and deliberately NOT a mirrored pair — the
    # near one is bigger, brighter and set lower than the far one.
    def cheek(cx0, cy0, rx, ry, lean, col):
        for (dy, hw) in ell_rows(rx, ry):
            if hw < 0:
                continue
            y = cy0 + dy
            cx = cx0 + int(dy * lean)
            fhw = _face_hw(y) - 1
            c.hline(max(MCX - fhw, cx - hw), min(MCX + fhw, cx + hw), y, col)
    # both are LIT (the lamp is off to her left and the box below her), and the
    # hollow under the far one is a separate crescent. Painting the far cheek
    # itself in ad7757 made a round patch DARKER than the skin around it, which
    # at 12x read as a bruise.
    cheek(MCX - 10, FY0 + 27, 6, 6, 0.34, C("d7b594"))
    cheek(MCX + 9, FY0 + 24, 5, 5, -0.28, C("d7b594"))
    for k in range(6):
        c.hline(MCX + 3 + k // 3, MCX + 7 + k // 2, FY0 + 28 + k // 2,
                C("ad7757"))
    # a healed cut across the left cheekbone. Kept SHORT and on one clean
    # diagonal: the first cut ran it flat for 6 px right beside the brow scar
    # and the pair read as one smudge down that side of her face.
    for k in range(5):
        c.set(MCX - 14 + k, FY0 + 27 + k // 2, C("7a4841"))
    # jaw and chin: the uplit underside, a U rather than a band
    for k in range(7):
        hw = _face_hw(FY1 - 6 + k)
        c.hline(MCX - hw, MCX + hw, FY1 - 6 + k, C("d7b594"))
    c.hline(MCX - 5, MCX + 4, FY1 - 1, C("e7d5b3"))
    c.hline(MCX - 4, MCX + 3, FY1, C("e7d5b3"))
    c.hline(MCX - 7, MCX + 6, FY1 - 7, C("d7b594"))
    for y in range(FY0 + 30, FY1 - 3):                  # the cold jaw rim: ONE
        c.set(MCX - _face_hw(y), y, C("253a5e"))        # solid line. A 3c5e8b
    for y in range(FY0 + 33, FY0 + 38):                 # pixel every third row
        c.set(MCX - _face_hw(y) + 1, y, C("3c5e8b"))    # was a dashed smear
    for y in range(FY0 + 28, FY1 - 3):                  # the warm one
        c.set(MCX + _face_hw(y), y, C("884b2b"))
    # hairline: a soft uneven fringe with a HARD PART on her left. A 1 px
    # alternating edge read as the teeth of a comb, so it waves on a long
    # period and carries two heavy locks.
    for k in range(34):
        x = MCX - 17 + k
        drop = 6 + int(round(1.4 * math.sin(k * 0.29) + 0.9 * math.sin(k * 0.63)))
        if 6 <= k <= 10:
            drop += 3                                   # two locks hanging,
        if 21 <= k <= 24:                               # different weights
            drop += 2
        if k == 13:
            drop -= 3                                   # the part
        c.vline(x, FY0 - 3, FY0 + drop, C("4d2b32"))
        c.set(x, FY0 + drop + 1, C("341c27"))
    # A GREYING LOCK, and it must be drawn AFTER the hairline or the hairline
    # paints over it. THREE cuts of this have now failed and all three failed
    # the same way — it was drawn as a straight, bright, uniform-width bar, so
    # it read as a metal rod stuck in her hair (15 px of a8b5b2 down her
    # temple; a 3 px mark on the crown; a 4 px white bar over the fringe).
    # It is hair, so it has to do what the hair does: fall down the SIDE mass,
    # lean as it falls, taper to a point, and stay dim — 577277 into 394a50,
    # nothing brighter, because nothing lights the top of her head.
    for k in range(38):
        t = k / 37.0
        x = MCX - 27 + int(t * 5 + math.sin(t * 2.4) * 2)
        w = 2 - int(t * 2)
        col = C("577277") if t < 0.35 else (C("394a50") if t < 0.75 else C("202e37"))
        c.hline(x, x + w, 284 + k, col)
        c.set(x - 1, 284 + k, C("341c27"))
    for k in range(9):                                  # one thinner strand
        c.set(MCX - 21 + k // 4, 292 + k, C("394a50") if k < 5 else C("202e37"))
    # brows: TWO segments, not a band, and not a matched pair. Under uplight a
    # brow shadows upward. The left one carries a scar notch through it.
    c.hline(MCX - 16, MCX - 7, FY0 + 16, C("602c2c"))
    c.hline(MCX - 15, MCX - 8, FY0 + 17, C("341c27"))
    c.hline(MCX + 5, MCX + 14, FY0 + 15, C("602c2c"))
    c.hline(MCX + 6, MCX + 13, FY0 + 16, C("341c27"))
    c.set(MCX - 12, FY0 + 16, C("c09473"))              # THE SCAR: a break in
    c.set(MCX - 12, FY0 + 17, C("c09473"))              # the brow carried up
    c.set(MCX - 12, FY0 + 15, C("c09473"))              # through it as one
    c.set(MCX - 11, FY0 + 14, C("d7b594"))              # UNBROKEN line — two
    c.set(MCX - 11, FY0 + 13, C("d7b594"))              # loose pale pixels
    c.set(MCX - 10, FY0 + 12, C("c09473"))              # floating above the
    c.set(MCX - 12, FY0 + 18, C("7a4841"))              # brow read as noise
    c.hline(MCX - 14, MCX - 9, FY0 + 18, C("884b2b"))
    c.hline(MCX + 7, MCX + 12, FY0 + 17, C("884b2b"))
    # the eyes: looking DOWN, so each is a lid line with lashes under it and a
    # sliver of catchlight where the box reaches the lower lid
    c.hline(MCX - 15, MCX - 8, FY0 + 20, C("090a14"))
    c.hline(MCX - 14, MCX - 9, FY0 + 21, C("090a14"))
    c.hline(MCX + 6, MCX + 13, FY0 + 19, C("090a14"))
    c.hline(MCX + 7, MCX + 12, FY0 + 20, C("090a14"))
    c.hline(MCX - 13, MCX - 10, FY0 + 22, C("d7b594"))
    c.hline(MCX + 8, MCX + 11, FY0 + 21, C("ad7757"))
    c.set(MCX - 16, FY0 + 20, C("7a4841"))
    c.set(MCX + 14, FY0 + 19, C("7a4841"))
    # nose: a straight bridge with a slight bump and one nostril in shade. The
    # lit plane is VERTICAL, and there is no lit horizontal bar under it —
    # that bar is what kept reading as a moustache.
    # A BRIDGE THAT WIDENS INTO A TIP. The first cut was one 1 px e7d5b3 column
    # eight rows long and it read as a pale stick laid on her face — a nose has
    # to change width or it is a line.
    c.vline(MCX - 3, FY0 + 19, FY0 + 29, C("7a4841"))       # the shade side
    c.vline(MCX - 2, FY0 + 20, FY0 + 26, C("c09473"))
    c.vline(MCX - 1, FY0 + 21, FY0 + 27, C("d7b594"))       # the bridge
    for k in range(4):                                      # the tip, wider
        c.hline(MCX - 3 + k // 2, MCX + 1 - k // 3, FY0 + 27 + k,
                C("d7b594") if k < 2 else C("e7d5b3"))
    c.set(MCX - 1, FY0 + 24, C("e7d5b3"))                   # one catch on the
    c.set(MCX - 4, FY0 + 30, C("7a4841"))                   # bridge, two
    c.set(MCX + 1, FY0 + 30, C("7a4841"))                   # nostrils in shade
    c.hline(MCX - 3, MCX, FY0 + 31, C("ad7757"))
    # mouth: one short soft line, one corner set lower than the other
    c.hline(MCX - 6, MCX + 2, FY0 + 35, C("884b2b"))
    c.set(MCX + 3, FY0 + 36, C("7a4841"))
    c.hline(MCX - 4, MCX + 1, FY0 + 36, C("c09473"))


def _mara_arms(c: Canvas, rng: random.Random) -> None:
    """Both forearms on the counter, cuffs shoved back off the wrists, because
    her hands are the subject: her left hand flat on the map, her right holding
    a stub pencil over the sheet she has pushed toward you.

    Drawn onto MARA'S OWN canvas, before the composite — the composite happens
    after the counter is down, so these still land on top of it, but this way
    the wall halo sees the arms and does not stop at her shoulders.

    The sleeves end at the elbows in _mara_body; every forearm here STARTS at
    the point its sleeve stopped and every hand STARTS at the point its forearm
    stopped: no piece of her floats free of the piece it hangs off."""
    def limb(x0, y0, x1, y1, w0, w1, core, up, dn):
        n = 84
        for k in range(n + 1):
            t = k / float(n)
            x, y, w = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w0 + (w1 - w0) * t
            c.rect(int(x - w), int(y - w * 0.62), int(x + w), int(y + w * 0.62),
                   core)
            c.hline(int(x - w), int(x + w), int(y - w * 0.62), up)
            c.hline(int(x - w), int(x + w), int(y + w * 0.62), dn)

    def hand(cx, ytop, ybot, half, digits, thumb):
        for y in range(ytop, ybot + 1):
            u = (y - ytop) / float(ybot - ytop)
            hw = int(half - abs(u - 0.30) ** 2 * 9)
            c.hline(cx - hw, cx + hw, y, C("c09473"))
            c.set(cx - hw, y, C("7a4841"))
            c.set(cx + hw, y, C("d7b594"))
        c.hline(cx - half + 4, cx + half - 4, ytop, C("d7b594"))
        c.hline(cx - half + 3, cx + half - 3, ybot, C("7a4841"))
        c.hline(cx - half + 2, cx + half - 2, ybot + 1, C("090a14"))
        for (dx, lg, lean) in digits:                    # fingers point AWAY
            fx = cx + dx
            for k in range(lg):
                xx = fx + int(k * lean)
                c.hline(xx, xx + 3, ytop - k,
                        C("c09473") if k < lg - 2 else C("d7b594"))
                c.set(xx + 4, ytop - k, C("7a4841"))     # 1 px shade between
            c.hline(fx + int(lg * lean), fx + 3 + int(lg * lean), ytop - lg,
                    C("d7b594"))
        (tdx, tlen, tsgn) = thumb
        for k in range(tlen):
            xx = cx + tdx + tsgn * k
            yy = ytop + 3 - int(k * 0.7)
            c.hline(xx, xx + tsgn * 3, yy, C("c09473") if k < tlen - 2
                    else C("d7b594"))
            c.set(xx - tsgn, yy + 1, C("7a4841"))

    # THE FOREARMS ARE A STEP DARKER THAN THE HANDS (ad7757 core, not c09473).
    # The first render made both the same value and forearms plus palms fused
    # into one pale plank running the whole width of the light box — the hands
    # are the subject of this pitch and they have to be the brightest skin in
    # the frame, not part of a band.
    # ---- her right arm (screen left). Its sleeve ends at (608, 412).
    limb(608, 410, 646, 392, 11, 8, C("ad7757"), C("c09473"), C("7a4841"))
    for k in range(30):                                     # cold rim, box side
        c.set(610 + k, 402 - int(k * 0.46), C("3c5e8b"))
    hand(651, 386, 400, 18,
         ((-15, 13, -0.16), (-9, 15, -0.05), (-3, 14, 0.05), (3, 11, 0.16)),
         (15, 11, 1))

    # ---- her left arm (screen right). Its sleeve ends at (754, 412).
    limb(754, 410, 718, 390, 11, 8, C("ad7757"), C("c09473"), C("7a4841"))
    for k in range(28):                                     # warm rim, lamp side
        c.set(752 - k, 402 - int(k * 0.48), C("de9e41"))
    hand(714, 384, 397, 17,
         ((-13, 10, -0.12), (-7, 12, -0.04), (-1, 11, 0.06), (5, 8, 0.14)),
         (-16, 10, -1))
    for k in range(26):                                     # the stub pencil
        x, y = 721 + k, 376 - int(k * 0.58)
        c.set(x, y, C("de9e41"))
        c.set(x, y + 1, C("be772b"))
        c.set(x, y + 2, C("884b2b"))
        c.set(x, y - 1, C("e8c170") if k > 7 else C("de9e41"))
    c.set(747, 362, C("341c27"))                            # its lead
    c.set(748, 361, C("090a14"))
    del rng


# ------------------------------------------------- under the counter -------
# MEASURED, NOT GUESSED: of the 11,700 pixels the removed forearm used to own,
# 8,158 were BELOW the near lip. The scale replaces it on the counter TOP, but
# deleting the limb also uncovered a 130 px stretch of front face that had had
# something in front of it since the pitch was first painted, and left it as
# bare maroon. This is the counter's own carcass, not another prop: joinery
# cannot be mistaken for a creature, which is the failure mode that killed the
# shoulder and then the arm.
#
# It is a CUPBOARD, deliberately not a third drawer — the two drawers to its
# left are a stack of flat fronts with finger pulls; this is a framed door with
# a recessed panel, two mismatched strap hinges and a hasp. And the padlock is
# the point: kettle's money lives under this counter (LORE 7a), and it is the
# one hard, bright, instantly-named object in the bottom left of the frame.
def _under_counter(c: Canvas, rng: random.Random) -> None:
    D = C("090a14")
    x0, y0, x1 = 164, 444, 296
    bot = SCENE_H - 1

    c.rect(x0 - 2, y0 - 2, x1 + 2, bot, D)               # the reveal all round
    c.rect(x0, y0, x1, bot, C("341c27"))                 # the door's face
    c.hline(x0 + 1, x1 - 1, y0 + 1, C("4d2b32"))         # lit top bevel
    c.vline(x0 + 1, y0 + 1, bot, C("4d2b32"))            # lit left bevel
    c.vline(x1 - 1, y0 + 2, bot, C("241527"))

    # the recessed panel. A recess lit from the upper left shows its TOP and
    # LEFT inner walls in shadow and its RIGHT and BOTTOM ones catching, and
    # the field sits in the shadow the top wall throws — that pair of facts is
    # the entire difference between a panel and a rectangle drawn on a door.
    px0, px1, py0 = x0 + 16, x1 - 16, y0 + 20
    c.rect(px0, py0, px1, bot, C("341c27"))
    c.rect(px0, py0, px1, py0 + 7, C("241527"))          # the recess's shadow
    c.hline(px0, px1, py0, D)
    c.hline(px0 + 1, px1 - 1, py0 + 1, C("241527"))
    c.vline(px0, py0, bot, D)
    c.vline(px0 + 1, py0 + 2, bot, C("241527"))
    c.vline(px1, py0, bot, C("4d2b32"))                  # the lit inner walls
    c.vline(px1 - 1, py0 + 2, bot, C("602c2c"))
    for gi in range(3):                                  # its own grain, which
        gy = 478 + gi * 24                               # does not line up with
        for x in range(px0 + 2, px1 - 1):                # the counter's runs
            y = gy + int(round(1.7 * math.sin(x / 39.0 + gi * 2.4)
                               + 1.0 * math.sin(x / 15.0 + gi)))
            c.set(x, y, C("241527"))

    # two strap hinges, NOT a matched pair: different lengths, and the lower
    # one has lost its paint down one side. They run back onto the counter
    # frame, because a hinge that starts at the door's own edge has nothing to
    # be hinged to.
    for (hy, ln, worn) in ((462, 36, False), (528, 27, True)):
        c.rect(x0 - 7, hy, x0 + ln, hy + 6, C("202e37"))
        c.hline(x0 - 7, x0 + ln, hy, C("202e37") if worn else C("394a50"))
        c.hline(x0 - 7, x0 + ln, hy + 6, D)
        c.set(x0 + ln, hy + 3, C("151d28"))
        c.rect(x0 - 7, hy + 1, x0 - 4, hy + 5, C("394a50"))   # the knuckle
        c.vline(x0 - 4, hy + 1, hy + 5, C("151d28"))
        for rv in (7, 12 + ln // 2):                     # two rivets, uneven
            c.rect(x0 + rv, hy + 2, x0 + rv + 1, hy + 3, C("577277"))
            c.set(x0 + rv + 1, hy + 4, C("151d28"))
        if worn:
            c.hline(x0 + 4, x0 + ln - 6, hy + 5, C("151d28"))

    # the hasp: a strap swung off the counter frame ONTO the door, so it
    # crosses the door's right edge. That crossing is what makes it a lock and
    # not a bracket.
    hx0, hx1, hy = x1 - 26, x1 + 12, 484
    c.rect(hx0, hy, hx1, hy + 7, C("202e37"))
    c.hline(hx0, hx1, hy, C("394a50"))
    c.hline(hx0, hx1, hy + 7, D)
    c.hline(hx0 + 1, hx1 - 1, hy + 8, C("241527"))
    c.vline(hx0, hy + 1, hy + 6, C("394a50"))
    c.rect(hx0 + 5, hy + 2, hx0 + 15, hy + 5, C("151d28"))   # the slot
    c.hline(hx0 + 5, hx0 + 15, hy + 2, D)
    c.set(hx1 - 4, hy + 2, C("577277"))
    c.set(hx1 - 7, hy + 5, C("151d28"))

    # THE PADLOCK, hanging under the hasp on the two legs of its shackle. The
    # first cut swept the shackle as an arc of nine samples over 144 degrees
    # and the gaps between them rendered as a jagged crown of loose pixels —
    # so the shackle is now two legs and a corner, drawn as the solid thing it
    # is, with its top hidden where it passes through the slot.
    lx = hx0 + 6
    for sx in (lx, lx + 9):
        c.vline(sx, hy + 6, 498, C("577277"))
        c.vline(sx + 1, hy + 6, 498, C("394a50"))
        c.set(sx + 2, hy + 7, C("202e37"))
    c.rect(lx - 3, 497, lx + 14, 514, C("394a50"))       # the body
    c.hline(lx - 2, lx + 13, 496, C("394a50"))           # corners eased
    c.hline(lx - 2, lx + 13, 515, C("151d28"))
    c.vline(lx - 3, 498, 513, C("577277"))
    c.hline(lx - 3, lx + 14, 497, C("577277"))
    c.rect(lx + 10, 498, lx + 14, 514, C("202e37"))      # its turned-away side
    c.hline(lx - 3, lx + 14, 514, C("151d28"))
    c.hline(lx - 2, lx + 13, 516, D)
    c.rect(lx + 2, 504, lx + 6, 506, C("151d28"))        # the keyway
    c.rect(lx + 3, 506, lx + 4, 510, C("151d28"))
    c.set(lx + 3, 503, C("819796"))
    c.rect(lx + 15, 499, lx + 16, 513, C("241527"))      # its shadow, on the
    c.rect(lx - 1, 517, lx + 13, 519, C("241527"))       # door behind it
    del rng


# ----------------------------------------------------- kettle's scale -------
# WHAT WAS HERE BEFORE, AND WHY IT IS GONE (user, twice: "the black arm is
# still on mara's screen remove that thing" / "just remove that black hand
# figure thing it just looks weird, replace it with something else on the
# screen so that's not a weak spot"). A gloved forearm entered from the bottom
# left and rested on the counter — YOU, in an over-the-shoulder framing. It was
# cut back once already (it began as a shoulder with a pack strap) and it still
# failed. The idea is ABANDONED: there is no third version of it, no other body
# part in its place, and not one pixel of glove, cuff, keeper or wrist wrap
# left. The whole lower-left is a room object now.
#
# WHAT REPLACED IT: kettle's balance, at the paying end of the counter.
# LORE 7a — the den is mara's radio plus KETTLE'S MONEY plus verne's table, and
# 7b lists "kettle's scale and shelf" as day-one furniture; section 9 lists
# "scale weights for kettle" as loot you can carry out. So the object is not
# decoration, it is the other half of what this counter is FOR: mara's end has
# the map, the sheet and the district tags, and this end weighs what you
# brought back. It also finishes a story the corner had already half-told —
# the sunk deposit tray with its two brass tokens is a few pixels away, and now
# there is something to weigh them against.
#
# IT IS MID-WEIGH, WHICH IS WHY IT IS NOT SYMMETRIC. The beam tilts down to
# the right: the loaded pan is low and heaped, the empty pan is high, and two
# brass weights still sit unused on the foot. That kills the one real risk in
# putting a balance here — two pans reading as a cloned pair. They are at
# different heights, different fill, different visible interior, hung on a
# different number of wires, and one rim is dented.
#
# VALUES ARE HELD DOWN ON PURPOSE. Nothing lights this corner (see
# _counter_left), so the steel runs 151d28..394a50 with 577277 used only on
# the beam's top edge and the two rims, and the only chroma is dull brass —
# the same 884b2b/be772b the tray tokens use. mara keeps the frame.
def _scale(c: Canvas, rng: random.Random) -> None:
    D, S, M, L, H = (C("090a14"), C("151d28"), C("202e37"),
                     C("394a50"), C("577277"))
    CX, PY = 246, 410                    # column centre line, foot's top plate

    # ---- the foot's shadow on the wood: penumbra first, core over it, thrown
    # down-RIGHT the way every prop on this counter throws (hook plates, tin,
    # mug). Most of it ends up hidden under the foot itself, which is what
    # keeps it from reading as a black puddle.
    for (dy, hw) in ell_rows(33, 11):
        if hw < 0 or dy < -4:
            continue
        c.hline(CX + 7 - hw, CX + 7 + hw, PY + 6 + dy, C("241527"))
    for (dy, hw) in ell_rows(29, 9):
        if hw < 0 or dy < -3:
            continue
        c.hline(CX + 5 - hw, CX + 5 + hw, PY + 6 + dy, D)

    # ---- the foot: a cast plate with REAL thickness. Side wall first, top
    # plate over it, so the two faces meet with no seam to leak through.
    for k in range(1, 8):
        for (dy, hw) in ell_rows(27, 8):
            if hw < 0 or dy < 0:
                continue
            col = M if k < 4 else (S if k < 7 else D)
            c.hline(CX - hw, CX + hw, PY + dy + k, col)
            c.set(CX - hw, PY + dy + k, L if k < 5 else S)
            c.set(CX + hw, PY + dy + k, S if k < 6 else D)
    for (dy, hw) in ell_rows(27, 8):
        if hw < 0:
            continue
        c.hline(CX - hw, CX + hw, PY + dy, L if dy < 2 else M)
        c.set(CX - hw, PY + dy, H if dy < 0 else L)
        c.set(CX + hw, PY + dy, M if dy < 0 else S)
    for (dy, hw) in ell_rows(24, 6):                 # a shallow dish in the top
        if hw < 0:
            continue
        c.hline(CX - hw, CX + hw, PY + dy + 1, M if dy < 1 else L)

    # ---- the column: tapered, with a flare where it is bolted to the foot and
    # a collar the pointer swings against
    for y in range(354, PY + 3):
        t = (y - 354) / float(PY + 2 - 354)
        hw = 3 + int(t * 2.2) + (3 if y > PY - 8 else 0) + (2 if y > PY - 4 else 0)
        c.hline(CX - hw, CX + hw, y, M)
        c.set(CX - hw, y, L)
        c.set(CX + hw, y, S)
    c.rect(CX - 8, 372, CX + 8, 378, M)              # the collar
    c.hline(CX - 8, CX + 8, 372, L)
    c.hline(CX - 7, CX + 7, 373, L)
    c.hline(CX - 8, CX + 8, 378, D)
    c.hline(CX - 7, CX + 7, 377, S)
    c.vline(CX - 8, 373, 377, L)
    c.vline(CX + 8, 373, 377, S)

    # ---- the beam, tilted DOWN TO THE RIGHT because the right pan is loaded.
    # A 16-in-88 slope steps every five or six pixels, and the FIRST cut put a
    # 577277 line along the top and a 090a14 line along the bottom of a body
    # only three pixels thick: every step got outlined and the beam read as a
    # string of sausages. The body is thicker than its edges now and the top
    # edge is one step down from the brightest the frame has.
    BX0, BY0, BX1, BY1 = 202, 342, 290, 358
    span = BX1 - BX0
    for k in range(span + 1):
        t = k / float(span)
        x = BX0 + k
        y = int(round(BY0 + (BY1 - BY0) * t))
        h = 3 + (1 if 0.14 < t < 0.86 else 0)
        c.rect(x, y - h, x, y + h, M)
        c.set(x, y - h, L)
        c.set(x, y + h, S)
        c.set(x, y + h - 1, M)
    for (r0, r1) in ((0.22, 0.34), (0.58, 0.71)):      # two catches, not a rule
        for k in range(int(span * r0), int(span * r1)):
            y = int(round(BY0 + (BY1 - BY0) * k / float(span)))
            c.set(BX0 + k, y - 3 - (1 if 0.14 < k / float(span) < 0.86 else 0), H)
    for (ex, ey) in ((BX0, BY0), (BX1, BY1)):        # the end finials
        c.rect(ex - 2, ey - 4, ex + 1, ey + 4, M)
        c.hline(ex - 2, ex + 1, ey - 4, L)
        c.hline(ex - 2, ex + 1, ey + 4, D)
        c.vline(ex - 2, ey - 3, ey + 3, L)
        c.vline(ex + 1, ey - 3, ey + 3, S)
        c.set(ex, ey, S)                             # the hanger's eye

    # ---- the knife bracket the beam rocks on. It STARTS AT THE BEAM: the
    # first cut began it three pixels lower and the gap read as a beam floating
    # off its own stand.
    for k in range(11):
        w = 6 - k // 2
        c.hline(CX - w, CX + w, 352 + k, M)
        c.set(CX - w, 352 + k, L)
        c.set(CX + w, 352 + k, S)
    c.rect(CX - 3, 344, CX + 3, 349, M)                # the pivot boss, on top
    c.hline(CX - 3, CX + 3, 344, L)
    c.set(CX + 3, 345, S)
    # THERE IS NO POINTER NEEDLE. One was drawn hanging off the boss and it
    # landed straight down the front of the column, so at 1x it did not read as
    # a needle at all — it just made the column look two pixels wider and badly
    # shaded. A part nobody can identify is worth less than the plain metal it
    # covers up.

    # ---- the two pans -------------------------------------------------------
    def wires(ex, ey, pts):
        for (tx, ty) in pts:
            n = max(abs(tx - ex), abs(ty - ey))
            for k in range(n + 1):
                t = k / float(n)
                xx = int(round(ex + (tx - ex) * t))
                yy = int(round(ey + (ty - ey) * t))
                c.set(xx, yy, L if k % 4 else H)
                c.set(xx + 1, yy, S)

    def pan(cx, cy, rx, ry, deep, dent):
        """A dish, not a disc: you see the OUTER wall below the rim and the FAR
        INNER wall inside it, which is the same trick the sunk tray uses and
        the only reason either one reads as having a volume."""
        for dy in range(0, ry + deep + 1):
            t = 1.0 - (dy / float(ry + deep)) ** 2
            hw = int(rx * (t ** 0.5))
            if hw < 1:
                continue
            c.hline(cx - hw, cx + hw, cy + dy, M if dy < ry else S)
            c.set(cx - hw, cy + dy, L if dy < ry + 2 else S)
            c.set(cx + hw, cy + dy, S if dy < ry else D)
            if dy > ry + deep - 3:
                c.hline(cx - hw, cx + hw, cy + dy, D)
        for (dy, hw) in ell_rows(rx, ry):            # the rim ring
            if hw < 0:
                continue
            c.hline(cx - hw, cx + hw, cy + dy, H if dy < 0 else L)
        for (dy, hw) in ell_rows(rx - 3, ry - 1):    # the inside
            if hw < 0:
                continue
            c.hline(cx - hw, cx + hw, cy + dy,
                    L if dy < -ry + 3 else (M if dy < 1 else S))
        if dent:                                     # one rim knocked in
            for k in range(5):
                c.set(cx - rx + 2 + k, cy - ry + 3 + abs(k - 2), M)
                c.set(cx - rx + 3 + k, cy - ry + 4 + abs(k - 2), S)

    # the EMPTY pan, high on the light end. Three wires, an open interior, a
    # dented rim: nothing in it, and it has been knocked about for six years.
    wires(BX0, BY0 + 4, ((188, 362), (202, 360), (215, 362)))
    pan(202, 366, 16, 5, 6, True)

    # the LOADED pan, low on the heavy end. Its shadow lands on the wood first
    # so the pan reads as HANGING over the counter rather than standing on it.
    for (dy, hw) in ell_rows(19, 6):
        if hw < 0:
            continue
        c.hline(294 - hw, 294 + hw, 400 + dy, C("241527"))
    for (dy, hw) in ell_rows(11, 3):
        if hw < 0:
            continue
        c.hline(293 - hw, 293 + hw, 401 + dy, D)
    wires(BX1, BY1 + 4, ((275, 383), (290, 380), (305, 383)))
    pan(290, 386, 17, 6, 4, False)

    # ---- the haul in it: SHINE (LORE 9). IT IS BRASS, AND THAT IS THE WHOLE
    # POINT. Two cuts of this were painted in the same steel as the pan — once
    # at the pan's own values, once a step above them — and BOTH read as one
    # dark silhouette: a leather pouch the first time, a dark fin the second.
    # In a corner with no light of its own, VALUE alone cannot separate two
    # things that touch. Hue can. A warm load in a cold pan reads instantly, it
    # says "the good stuff" with no text, and it ties this end of the counter
    # to the two brass tokens already lying in the tray beside it.
    #
    # A heap of scrap is not a mound either — it is SUMMITS: three lumps of
    # different heights whose slopes meet in visible valleys, each catching on
    # its upper-left face. It STOPS AT y=385, one row above the rim's own
    # centre line, so the near rim of the pan stays in FRONT of the load.
    def lump(px, half, hgt):
        return lambda x: hgt * max(0.0, 1.0 - ((x - px) / float(half)) ** 2)

    lumps = [lump(281, 10, 13), lump(291, 7, 8), lump(299, 8, 16)]
    for x in range(276, 305):
        hgt = max(f(x) for f in lumps)
        top = 386 - int(hgt)
        if top > 384:
            continue
        rise = hgt - max(f(x + 2) for f in lumps)
        for y in range(top, 386):
            c.set(x, y, C("884b2b") if y < 383 else C("602c2c"))
        c.set(x, top, C("be772b") if rise < 0.6 else C("884b2b"))
        c.set(x, top + 1, C("be772b") if rise < 0.2 else C("884b2b"))
    for x in range(276, 305):                        # the valleys between them
        a = 386 - int(max(f(x) for f in lumps))
        b = 386 - int(max(f(x + 1) for f in lumps))
        if b > a + 1:
            c.vline(x + 1, a, min(b, 385), C("602c2c"))
    c.hline(294, 297, 371, C("de9e41"))              # one catch, the tallest
    c.set(293, 372, C("de9e41"))
    # TWO FLAT FACETS ON IT, because parabolas alone came back as a loaf of
    # bread: scrap is pieces, and a piece has a straight edge somewhere.
    for k in range(13):                              # a plate lying askew
        px, py = 276 + k, 375 - k // 3
        c.vline(px, py, py + 2, C("884b2b"))
        c.set(px, py, C("be772b"))
        c.set(px, py + 3, C("602c2c"))
    for k in range(11):                              # a steel bar half buried
        px, py = 281 + k, 381 + k // 5
        c.set(px, py - 1, L)
        c.set(px, py, M)
        c.set(px, py + 1, S)
    # ONE BENT ROD STANDING OUT OF THE PILE, and it is STEEL — the one cold
    # thing in a warm heap, so the heap is a heap of different things and not a
    # single cast lump. Two other objects were tried in this slot and both
    # failed the same way: they left the pan SIDEWAYS. A brass chain over the
    # near rim read as six orange dots (the banned texture), and a length of
    # scrap poking out to the right read, dead obviously in the crop, as a
    # FRYING PAN HANDLE. Anything that leaves this pan horizontally turns it
    # into a skillet. This one leaves upward.
    for k in range(15):
        t = k / 14.0
        rx_ = int(298 + t * 9 - math.sin(t * 2.1) * 3)
        ry_ = int(373 - t * 12)
        c.vline(rx_, ry_, ry_ + 1, M)
        c.set(rx_ + 1, ry_, L)
        c.set(rx_ - 1, ry_, S)

    # ---- two brass weights still on the foot: the beam has not come level, so
    # these have not gone in yet. Deliberately NOT a pair — one stands, one has
    # been knocked onto its side, and they are different sizes.
    wx0 = 224 + rng.randint(-1, 1)
    for y in range(398, 415):                        # the tall one, standing
        u = (y - 398) / 16.0
        hw = 5 if u > 0.22 else 3
        c.hline(wx0 - hw, wx0 + hw, y, C("884b2b") if u > 0.3 else C("602c2c"))
        c.set(wx0 - hw, y, C("be772b"))
        c.set(wx0 + hw, y, C("602c2c"))
    for (dy, hw) in ell_rows(5, 2):                  # its knob
        if hw < 0:
            continue
        c.hline(wx0 - hw, wx0 + hw, 398 + dy,
                C("be772b") if dy < 0 else C("884b2b"))
    c.hline(wx0 - 3, wx0 + 3, 396, C("884b2b"))
    c.set(wx0 - 2, 395, C("602c2c"))
    c.hline(wx0 - 4, wx0 + 4, 415, D)
    # the second one is a BLOCK, not a smaller cylinder and not the same
    # cylinder knocked over — a tipped disc read as a bread roll, and a second
    # cylinder would have been the cloned pair this whole object is built to
    # avoid. Three faces: top, front, and the short side in shade.
    wx1 = 259 + rng.randint(-1, 1)
    for k in range(5):                               # the top face, sheared
        c.hline(wx1 - 6 + k, wx1 + 6 + k, 404 - k,   # up-RIGHT, same width as
                C("be772b") if k > 2 else C("884b2b"))   # the front face
    for k in range(5):                               # the side, turned away
        c.vline(wx1 + 6 + k, 404 - k, 413 - k, C("602c2c"))
        c.set(wx1 + 6 + k, 413 - k, C("241527"))
    c.rect(wx1 - 6, 405, wx1 + 6, 413, C("884b2b"))  # the front face
    c.vline(wx1 - 6, 405, 413, C("be772b"))
    c.hline(wx1 - 6, wx1 + 6, 413, C("602c2c"))
    c.hline(wx1 - 5, wx1 + 6, 414, D)
    c.hline(wx1 - 3, wx1 + 1, 409, C("602c2c"))      # a stamped mark, unread


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
