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
    _wall_halo(mara, lvl, far)
    _wall_paint(c, rng, lvl, far)

    _clock(c, rng, 92, 176, 32)
    _tally(c, rng)
    _hook_rail(c, rng)
    _cables(c)

    _counter(c, rng, far)
    _light_box(c, rng)
    _job_sheet(c, rng)
    _mug(c, rng)
    _parts_tin(c, rng)

    c.img.alpha_composite(mara.img, (0, 0))
    c.px = c.img.load()
    _mara_arms(c, rng)
    _work_lamp(c, rng)

    _magpie(c, rng)                      # foreground last: it occludes all
    return c


# ---------------------------------------------------------------- ceiling ---
def _ceiling(c: Canvas) -> None:
    c.rect(0, 0, SCENE_W - 1, CEIL_Y + 3, C("090a14"))
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
                base = 0.55 + 1.35 * (t ** 1.6) + bias * s
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
    for y in range(276, 384):
        for x in range(596, 796):
            if mara.px[x, y][3] > 0:
                sp[x, y] = 255
    hp = sil.filter(ImageFilter.GaussianBlur(11)).load()
    for y in range(CEIL_Y + 4, FAR_Y + 14):
        for x in range(586, 806):
            k = (x, y)
            if k not in lvl or sp[x, y]:
                continue
            a = hp[x, y]
            if a > 92:
                lvl[k][0] -= 1.6
            elif a > 24:
                lvl[k][0] -= 0.85


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


def _tally(c: Canvas, rng: random.Random) -> None:
    """One chalk mark for every raider who went in and did not come out. It
    fades to nothing well before the button band begins."""
    def chalk(x):
        return C("c7cfcc") if x < 226 else (C("819796") if x < 268 else C("577277"))
    ty = 158
    for row in range(6):
        x = 178 + rng.randint(0, 10)
        for g in range(8):
            n = 5 if (row * 7 + g) % 9 else rng.randint(1, 4)
            lean = rng.uniform(-0.24, 0.24)
            hgt = rng.randint(12, 18)
            for s in range(min(4, n)):
                sx = x + s * rng.randint(4, 6)
                for k in range(hgt):
                    c.set(sx + int(k * lean), ty + k, chalk(sx))
            if n == 5:
                for k in range(hgt + 2):
                    c.set(x - 3 + int(k * (23 / float(hgt + 2))),
                          ty + hgt + 1 - k, chalk(x + 9))
            x += rng.randint(25, 34)
            if x > 306:
                break
        ty += rng.randint(19, 25)


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
            col = C("341c27") if t < 0.62 else C("4d2b32")
            if (x, y) in grain:
                col = C("241527") if t < 0.62 else C("341c27")
            c.set(x, y, col)
    # the warm pool: rock steady (in the den the WARM light breathes — here it
    # is the cold one that will, which is the pitch's inversion)
    _pool(c, LAMP, 86, 26, grain, far,
          [(0.20, "e8c170"), (0.40, "de9e41"), (0.62, "ad7757"),
           (0.82, "884b2b"), (1.00, "602c2c")])
    _pool(c, (BOX[0], BOX[1] + 14), 78, 24, grain, far,
          [(0.30, "253a5e"), (0.58, "1e1d39"), (0.82, "411d31"), (1.00, "241527")])
    # the near lip: dead straight, because a counter edge is machined. It is
    # broken instead by what CROSSES it — the sheet and the magpie's forearm —
    # and by a value gradient running along its length.
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
# Head 42 px wide with hair, face 32x36. The den's heads are 13-15 px and the
# drain has no people at all: nothing in this menu has ever been close enough
# to read where somebody is looking.
FX0, FX1, FY0, FY1 = 668, 693, 306, 340          # the face box, 26x35
MCX = 681                                        # her centre line


def _face_hw(y: int) -> int:
    """Half-width of the face at row y — an oval that tapers to the chin, not
    a box. The first render drew a rectangle and it read as a slab."""
    u = (y - FY0) / float(FY1 - FY0)
    if u < 0.14:
        return 11
    if u < 0.66:
        return 13
    if u < 0.80:
        return 12
    return max(3, int(12 - (u - 0.80) * 46))


def _mara_body(c: Canvas, rng: random.Random) -> None:
    """Head, hair, the headset pushed OFF her ear, shoulders. Everything below
    the counter's far edge is occluded, so this stops at y=374.

    She looks DOWN at the map: each eye is one dark line under a brow and
    there is no mouth expression to get wrong — the two lights do the
    modelling. UPLIGHT, cold from the light box below-left and warm from the
    lamp below-right, so the forehead and crown stay dark. Both shipped scenes
    light from at or above figure height; this one does not."""
    # ---- shoulders, oxblood jacket (identity carried over from the den)
    shoulder_top = {}
    for y in range(350, 376):
        t = (y - 350) / 26.0
        half = int(23 + (t ** 0.42) * 25)               # a ROUND shoulder — a
        for x in range(MCX - half, MCX + half + 1):     # near-linear taper
            lit = (x - (MCX - half)) / float(2 * half)  # read as a poncho
            col = C("752438")
            if lit < 0.17 or lit > 0.85:
                col = C("411d31")
            c.set(x, y, col)
            shoulder_top.setdefault(x, y)
        c.set(MCX - half, y, C("3c5e8b"))               # cold rim, box side
        c.set(MCX - half + 1, y, C("253a5e"))
        c.set(MCX + half, y, C("884b2b"))               # warm rim, lamp side
        c.set(MCX + half - 1, y, C("602c2c"))
    for x, y in shoulder_top.items():                   # highlight FOLLOWS the
        if abs(x - MCX) > 16:                           # shoulder line instead
            c.set(x, y + 1, C("a53030"))                # of two ruled strokes
            c.set(x, y + 2, C("a53030"))
    c.rect(MCX - 14, 344, MCX + 13, 352, C("411d31"))   # collar
    c.hline(MCX - 14, MCX + 13, 344, C("752438"))
    c.rect(MCX - 10, 346, MCX + 9, 353, C("341c27"))    # the neck's own shadow

    # ---- neck, uplit from underneath
    c.rect(MCX - 8, 336, MCX + 7, 350, C("7a4841"))
    c.rect(MCX - 5, 340, MCX + 4, 348, C("ad7757"))
    c.hline(MCX - 7, MCX + 6, 336, C("602c2c"))

    # ---- hair. The crown is the darkest thing on her: nothing lights her
    # from above. Built as a rounded mass — a rectangle read as a helmet.
    for (dy, hw) in ell_rows(23, 24):
        if hw < 0 or dy > 6:
            continue
        c.hline(MCX - hw, MCX + hw, 312 + dy, C("4d2b32"))
        if dy < -13:
            c.hline(MCX - hw, MCX + hw, 312 + dy, C("341c27"))
    c.rect(MCX - 23, 314, MCX - 14, 342, C("4d2b32"))
    c.rect(MCX + 14, 314, MCX + 23, 338, C("4d2b32"))
    c.vline(MCX - 23, 314, 342, C("341c27"))
    c.vline(MCX + 23, 314, 336, C("602c2c"))            # the lamp finds this side
    for k in range(6):                                  # loose strands
        c.vline(MCX - 25 - rng.randrange(2), 302 + k * 6, 306 + k * 6, C("341c27"))
    # low ponytail over her right shoulder — a den identity marker
    for k in range(54):
        t = k / 54.0
        px = int(MCX - 26 - t * 8 + math.sin(t * 3.0) * 3)
        w = int(8 - t * 4)
        c.rect(px - w, 318 + k, px + w, 319 + k, C("4d2b32"))
        c.vline(px - w, 318 + k, 319 + k, C("341c27"))
        c.vline(px + w, 318 + k, 319 + k, C("602c2c") if t < 0.55 else C("4d2b32"))
    c.rect(MCX - 40, 366, MCX - 30, 374, C("341c27"))   # its tie

    # ---- the face. UPLIGHT: cold below-left, warm below-right, forehead and
    # crown dark because nothing lights her from above.
    # A RADIAL ramp off a source below the chin, not horizontal bands: banding
    # a face in flat rows put a hard value step across the middle of it and the
    # first two renders both read as a man with a moustache.
    # THE LIGHT IS PLACED BY HAND, NOT RAMPED. A radial ramp was tried and it
    # failed for a structural reason worth writing down: the face is 26 px
    # wide and the source is ~44 px below it, so every iso-distance contour
    # crosses the face almost HORIZONTALLY. Three separate renders produced a
    # full-width value step in the middle of her face and all three read as a
    # man with a moustache. Below the brow the base tone is now CONSTANT, and
    # the light is put on as cheek, nose, jaw and chin shapes.
    for y in range(FY0, FY1 + 1):
        hw = _face_hw(y)
        c.hline(MCX - hw, MCX + hw, y,
                C("7a4841") if y < FY0 + 11 else C("c09473"))
    for k in range(6):                                  # forehead, half-lit
        c.hline(MCX - 10 + k, MCX + 9 - k, FY0 + 9 - k // 2, C("884b2b"))
    # cheekbones: two separate blobs, deliberately NOT mirrored
    c.rect(MCX - 12, FY0 + 18, MCX - 5, FY0 + 24, C("d7b594"))
    c.rect(MCX - 11, FY0 + 17, MCX - 6, FY0 + 17, C("d7b594"))
    c.rect(MCX + 3, FY0 + 17, MCX + 10, FY0 + 23, C("ad7757"))
    c.rect(MCX + 4, FY0 + 24, MCX + 9, FY0 + 25, C("ad7757"))
    # jaw and chin: the uplit underside, a U rather than a band
    for k in range(6):
        hw = _face_hw(FY1 - 5 + k)
        c.hline(MCX - hw, MCX + hw, FY1 - 5 + k, C("d7b594"))
    c.hline(MCX - 4, MCX + 3, FY1 - 1, C("e7d5b3"))
    c.hline(MCX - 3, MCX + 2, FY1, C("e7d5b3"))
    c.hline(MCX - 6, MCX + 5, FY1 - 6, C("d7b594"))
    for y in range(FY0 + 24, FY1 - 3):                  # the cold jaw rim
        c.set(MCX - _face_hw(y), y, C("253a5e"))
        if y % 3 == 1:
            c.set(MCX - _face_hw(y) + 1, y, C("3c5e8b"))
    for y in range(FY0 + 22, FY1 - 3):                  # the warm one
        c.set(MCX + _face_hw(y), y, C("884b2b"))
    # hairline: a soft uneven fringe. A 1 px alternating edge read as the
    # teeth of a comb, so it waves on a long period with two locks in it.
    for k in range(26):
        x = MCX - 13 + k
        drop = 4 + int(round(1.6 * math.sin(k * 0.42) + 1.0 * math.sin(k * 0.9)))
        if 6 <= k <= 8 or 17 <= k <= 19:
            drop += 3                                   # two locks hanging
        c.vline(x, FY0 - 2, FY0 + drop, C("4d2b32"))
        c.set(x, FY0 + drop + 1, C("341c27"))
    # brow: TWO segments, not a band. Under uplight the brow shadows upward.
    c.hline(MCX - 12, MCX - 6, FY0 + 12, C("602c2c"))
    c.hline(MCX + 4, MCX + 10, FY0 + 12, C("602c2c"))
    c.hline(MCX - 11, MCX - 7, FY0 + 13, C("884b2b"))
    c.hline(MCX + 5, MCX + 9, FY0 + 13, C("884b2b"))
    # the eyes: looking DOWN, so each is one dark line under its lid
    c.hline(MCX - 11, MCX - 7, FY0 + 16, C("090a14"))
    c.hline(MCX + 5, MCX + 9, FY0 + 16, C("090a14"))
    c.hline(MCX - 10, MCX - 8, FY0 + 17, C("884b2b"))
    c.hline(MCX + 6, MCX + 8, FY0 + 17, C("884b2b"))
    # nose: the lit plane is VERTICAL, and there is no lit horizontal bar
    # under it — that bar is what kept reading as a moustache
    c.vline(MCX - 2, FY0 + 16, FY0 + 23, C("884b2b"))
    c.vline(MCX, FY0 + 18, FY0 + 23, C("e7d5b3"))
    c.set(MCX - 1, FY0 + 24, C("884b2b"))
    # mouth: one short soft line. No expression to get wrong.
    c.hline(MCX - 4, MCX + 1, FY0 + 27, C("884b2b"))
    # ---- her ear, and the headset pushed OFF it onto her neck: she is
    # off-channel, talking to you
    c.rect(MCX + 13, FY0 + 13, MCX + 16, FY0 + 22, C("c09473"))
    c.set(MCX + 14, FY0 + 17, C("884b2b"))
    c.rect(MCX + 13, 340, MCX + 21, 351, C("202e37"))            # the ear cup
    c.rect(MCX + 15, 342, MCX + 19, 349, C("151d28"))
    c.hline(MCX + 13, MCX + 21, 340, C("394a50"))
    c.set(MCX + 17, 345, C("577277"))
    # the band sits ON HER NECK and sags DOWNWARD. An earlier cut arced it
    # upward and it crossed her mouth, which is what the render caught.
    for k in range(30):
        t = k / 30.0
        bx_ = int(MCX + 13 - t * 30)
        by_ = int(345 + math.sin(t * math.pi) * 5 + t * 3)
        c.set(bx_, by_, C("202e37"))
        c.set(bx_, by_ + 1, C("151d28"))
    for k in range(24):                                          # its lead
        t = k / 24.0
        c.set(int(MCX + 21 + t * 11), int(350 + t * 22 + math.sin(t * 3.0) * 3),
              C("090a14"))


def _mara_arms(c: Canvas, rng: random.Random) -> None:
    """Both forearms on the counter, cuffs shoved to the elbows, because her
    hands are the subject: the near hand flat and splayed on the map, the far
    hand holding a stub pencil on the sheet she has pushed toward you."""
    def limb(x0, y0, x1, y1, w0, w1, core, up, dn):
        for k in range(65):
            t = k / 64.0
            x, y, w = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w0 + (w1 - w0) * t
            c.rect(int(x - w), int(y - w * 0.6), int(x + w), int(y + w * 0.6), core)
            c.hline(int(x - w), int(x + w), int(y - w * 0.6), up)
            c.hline(int(x - w), int(x + w), int(y + w * 0.6), dn)

    # the upper arms are a STEP DARKER than the torso, or the whole figure
    # reads as one flat red poncho with no arms in it
    limb(648, 358, 630, 402, 10, 8, C("411d31"), C("752438"), C("241527"))
    limb(714, 358, 734, 400, 10, 8, C("411d31"), C("752438"), C("241527"))
    c.rect(622, 394, 640, 406, C("411d31"))                 # cuff, shoved up
    c.hline(622, 640, 394, C("752438"))
    c.rect(724, 392, 744, 404, C("411d31"))
    c.hline(724, 744, 392, C("a53030"))
    limb(632, 402, 660, 392, 8, 6, C("c09473"), C("d7b594"), C("7a4841"))
    limb(734, 400, 708, 390, 8, 6, C("c09473"), C("d7b594"), C("7a4841"))
    for k in range(28):                                     # cold rim, box side
        c.set(632 + k, 396 - int(k * 0.36), C("3c5e8b"))
    for k in range(26):                                     # warm rim, lamp side
        c.set(734 - k, 394 - int(k * 0.36), C("de9e41"))

    # ---- the near hand: flat and splayed on the map
    c.rect(646, 384, 670, 396, C("c09473"))
    c.hline(646, 670, 384, C("d7b594"))
    c.hline(647, 669, 396, C("7a4841"))
    for i in range(5):
        fx = 647 + i * 5
        fl = (7, 10, 11, 9, 6)[i]
        lean = (-2, -1, 0, 1, 2)[i]
        for k in range(fl):
            xx = fx + int(k * lean / float(fl))
            c.hline(xx, xx + 2, 384 - k, C("c09473") if k < fl - 2 else C("d7b594"))
            c.set(xx + 3, 384 - k, C("7a4841"))         # 1 px shade between
        c.hline(fx, fx + 2, 384 - fl, C("d7b594"))
    c.hline(645, 671, 397, C("090a14"))

    # ---- the far hand: two fingers on the sheet, a stub pencil in it
    c.rect(702, 382, 722, 394, C("c09473"))
    c.hline(702, 722, 382, C("d7b594"))
    c.hline(703, 721, 394, C("7a4841"))
    for i in range(2):
        fx = 704 + i * 7
        for k in range(9):
            c.hline(fx, fx + 3, 382 - k, C("c09473") if k < 7 else C("d7b594"))
            c.set(fx + 4, 382 - k, C("7a4841"))
    for k in range(20):                                     # the stub pencil
        x, y = 714 + k, 380 - int(k * 0.6)
        c.set(x, y, C("de9e41"))
        c.set(x, y + 1, C("be772b"))
        c.set(x, y - 1, C("e8c170") if k > 5 else C("de9e41"))
    c.set(734, 368, C("341c27"))
    c.set(735, 367, C("090a14"))
    c.hline(701, 723, 395, C("090a14"))
    del rng


# ------------------------------------------------------------- foreground ---
def _magpie(c: Canvas, rng: random.Random) -> None:
    """YOU. Bottom-left, restricted to the palette's two darkest colours plus
    one top plane — nothing else in the frame at that size uses only those
    tones, so it separates by VALUE with no keyline. Out-of-focus in pixel art
    is FLATNESS, not blur: three readable structures on it (strap + brass
    buckle, the collar's lit lip, the wrist wrap) and nothing else.

    No head, no face: you are the shoulder, which also avoids committing to a
    player model.

    THREE earlier cuts failed and the failures are instructive. One big mass
    with a hump read as a hill; one big mass with a notch read as a landmass;
    one long shallow sweep from the left edge read as a road. The fix was
    never more detail — it was NEGATIVE SPACE. The shoulder now hugs the left
    edge, the arm enters from the BOTTOM of the frame (which is where you are
    standing) and rises to the counter, and the counter shows through the
    wedge between them. A silhouette with a hole in it cannot read as a
    pyramid."""
    # ---- the shoulder: a mass on the left edge, mostly out of frame
    tpts = [(0, 300), (26, 288), (54, 302), (76, 352), (92, 434), (100, 544)]
    top = [0.0] * 120
    for i in range(len(tpts) - 1):
        (ax, ay), (bx_, by_) = tpts[i], tpts[i + 1]
        for x in range(ax, bx_ + 1):
            t = (x - ax) / float(bx_ - ax)
            t = t * t * (3 - 2 * t)                        # smooth, no corners
            top[x] = ay + (by_ - ay) * t
    for x in range(101):
        cy = int(round(top[x] + 2.0 * math.sin(x / 19.0) + 1.3 * math.sin(x / 7.0 + 1.1)))
        c.rect(x, cy, x, SCENE_H - 1, C("090a14"))
        c.set(x, cy, C("253a5e"))                          # THE rim — unbroken
        c.set(x, cy + 1, C("172038"))
        if x < 58:                                         # turned-up collar
            c.rect(x, cy + 2, x, cy + 9, C("10141f"))
            c.set(x, cy + 10, C("090a14"))
            c.set(x, cy + 12 + int(math.sin(x / 23.0) * 2), C("172038"))

    # pack strap: swept along its OWN perpendicular. Offsetting horizontally
    # on a steep diagonal turned it into a ladder of rungs.
    sx0, sy0, sx1, sy1 = 4, 300, 64, 470
    dx, dy = sx1 - sx0, sy1 - sy0
    ln = (dx * dx + dy * dy) ** 0.5
    px, py = -dy / ln, dx / ln
    for k in range(int(ln * 3) + 1):
        t = k / float(int(ln * 3))
        cx_, cy_ = sx0 + dx * t, sy0 + dy * t
        for w in range(-7, 8):
            c.set(int(round(cx_ + px * w)), int(round(cy_ + py * w)), C("341c27"))
        for (w, col) in ((-7, "4d2b32"), (-8, "602c2c"), (7, "090a14"), (8, "090a14")):
            c.set(int(round(cx_ + px * w)), int(round(cy_ + py * w)), C(col))
    bx, by = 24, 356                                       # the brass slider
    c.rect(bx, by, bx + 14, by + 9, C("be772b"))
    c.rect(bx + 2, by + 2, bx + 12, by + 6, C("884b2b"))
    c.hline(bx, bx + 14, by, C("de9e41"))
    c.vline(bx, by, by + 9, C("de9e41"))
    c.hline(bx + 1, bx + 13, by + 9, C("602c2c"))
    c.set(bx + 3, by + 1, C("e8c170"))

    # ---- the arm: its own limb, rising STEEPLY into frame from where you are
    # standing, swept along its perpendicular so it keeps a constant thickness
    # instead of fanning out into a ramp
    a0, a1 = (146.0, 588.0), (266.0, 438.0)
    adx, ady = a1[0] - a0[0], a1[1] - a0[1]
    aln = (adx * adx + ady * ady) ** 0.5
    apx, apy = -ady / aln, adx / aln
    steps = int(aln * 3)
    for k in range(steps + 1):
        t = k / float(steps)
        cx_ = a0[0] + adx * t + math.sin(t * 2.4) * 4
        cy_ = a0[1] + ady * t
        r = 39.0 - 9.0 * t
        for w in range(-int(r), int(r) + 1):
            c.set(int(round(cx_ + apx * w)), int(round(cy_ + apy * w)), C("090a14"))
        for (w, col) in ((-int(r), "253a5e"), (-int(r) + 1, "172038"),
                         (-int(r) + 2, "172038"), (int(r), "10141f")):
            c.set(int(round(cx_ + apx * w)), int(round(cy_ + apy * w)), C(col))
        if 0.08 < t < 0.24:                                # the sleeve cuff
            for w in range(-int(r) + 3, -int(r) + 13):
                c.set(int(round(cx_ + apx * w)), int(round(cy_ + apy * w)),
                      C("10141f"))
        if 0.58 < t < 0.73:                                # the wrist wrap —
            for w in range(-int(r), int(r) - 18):          # verne rebuilt this
                col = "577277" if w < -int(r) + 2 else (   # arm (lore §8)
                    "602c2c" if 0.63 < t < 0.68 and -8 < w < 0 else "394a50")
                c.set(int(round(cx_ + apx * w)), int(round(cy_ + apy * w)), C(col))

    # ---- the hand. It rests on the LIT top face with the fingers fanning
    # away from you, because a hand drawn over the counter's dark front face
    # is 090a14 on 241527 and simply disappears — the render proved it.
    def cap(x0, y0, ang, length, half):
        dxx, dyy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for k in range(int(length * 3) + 1):
            t = k / float(int(length * 3))
            cx_, cy_ = x0 + dxx * length * t, y0 + dyy * length * t
            h = half - (1 if t > 0.88 else 0)              # rounded tip
            for w in range(-h, h + 1):
                c.set(int(round(cx_ - dyy * w)), int(round(cy_ + dxx * w)),
                      C("090a14"))
            c.set(int(round(cx_ - dyy * -h)), int(round(cy_ + dxx * -h)),
                  C("253a5e"))
            c.set(int(round(cx_ - dyy * (-h + 1))), int(round(cy_ + dxx * (-h + 1))),
                  C("172038"))

    for y in range(404, 439):                              # the palm
        t = (y - 404) / 34.0
        pad = int(6 * abs(t - 0.5) ** 2 * 4)
        c.hline(212 + pad, 272 - pad // 2, y, C("090a14"))
    c.hline(220, 266, 404, C("253a5e"))
    c.hline(222, 264, 405, C("172038"))
    c.rect(224, 406, 262, 411, C("172038"))
    for i in range(4):                                     # four fanned fingers
        (rx, ry, ang, lg, hf) = ((242, 406, -52, 26, 6), (254, 410, -42, 28, 6),
                                 (264, 416, -31, 24, 6), (270, 424, -18, 17, 5))[i]
        cap(rx, ry, ang, lg + rng.randint(0, 2), hf)
    cap(220, 424, -104, 18, 6)                             # the thumb
    for (kx, ky) in ((240, 404), (241, 404), (252, 408), (253, 408), (263, 414)):
        c.set(kx, ky, C("3c5e8b"))                         # knuckle catches


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
