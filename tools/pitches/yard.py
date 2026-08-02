"""the yard at dusk - standing on the running line, two dead boxcars either side.

BACKDROP PITCH - static scene only, no living layer yet. Unwired: nothing
imports this and gen_art.py never emits it. If the user picks this pitch it
gets promoted into gen_art.py proper; if not, this file is deleted.

GEOMETRY IS PROJECTED, NOT EYEBALLED (critic finding: the brief's coordinates
were illustrative and self-contradictory). One real pinhole camera stood on
the four-foot: eye 1.7 m, focal 831 px (~60 deg horizontal), horizon y 262,
vanishing point x 300. Every ground point, every vertical and every rail comes
out of gy()/gxd()/ppm() below, so the poles are collinear with the VP, the
sleeper ends scale as (y-262), and a 4 m boxcar is really four times a 1 m
man. Nothing here is a hand-placed coordinate except the art detail hung on
the skeleton.

CRITIC CORRECTIONS APPLIED
  1. the horizon is ONE number (262). the district silhouette is drawn
     UPWARD from it, y ~228-262, with a deliberate low gap over the VP, so
     the convergence point sits on the ground line against bright sky instead
     of being buried in a black mass.
  2. scale rebuilt from the projection. the brief's rails were right
     (238 px gauge at the bottom edge) and everything standing beside them
     was ~5x too short. poles are 8 m, cars 4.25 m, signal 4.4 m.
  3. the drip source moved: a 4.25 m car 12 m away puts its roof lip near
     y 80-174, so the drop now comes off the LEFT car's eave (see DRIP_SRC)
     and lands in the baked puddle at PUDDLE - both marked below.
  4. the three 1 px "stars" are gone (dot noise, and the brief itself said
     no stars).
  5. the right car is not a flat rectangle: it shows a lit flank AND a
     raking end face at a different value, with converging ribs.
  6. no overlook citation - there is no overlook, it was dropped on a user
     call. the seam wobble here is written from scratch (see wob()).

SECOND PASS, after the user looked at it (they reported no defects; these
are the honest weaknesses, and none of them touched the sky, the
perspective or the convergence, which are the strongest things here)
  1. the right car had no door, no hardware and no wear of its own - it
     carried its whole side of the frame on value alone. it now has a
     padlocked replacement door on a track, roof vents and a running
     board, a brake wheel on the end, a repair plate and a dirt tide. it
     is NOT the left car mirrored: that one is a plank leaf dragged open
     on a black gap, this one is shut, steel, and a different paint.
  2. the sleepers read as a ladder. tone, length, burial, sink, sideways
     shift, spacing and dropouts are all fought now - see section 4.
  3. the 394a50 haze at y 267-281 was a constant-height stripe the full
     width of the frame. its thickness now swings to nothing and its
     colour dies into the ground away from the glow.
  4. the 7a367b band read as synthwave. magenta is out of the cooling
     ladder entirely, so it survives only as a narrow accent near the
     glow, broken by two cloud bars.
  5. the button band was a perfectly flat field. one broad hollow, one
     palette step (measured: the band is 60/40 151d28 / 202e37 and
     nothing else).
  6. the nearest telegraph pole's foot was hidden behind the left car.
     the car ends nearer and the pole steps back; there are 25 px of open
     ballast between them now.

ROOM LEFT FOR THE LIVING LAYER (do not build it here):
  * signal lens baked UNLIT at 752438, glow sprite goes at SIGNAL_LENS.
    keep the glow <= 40 px radius or it walks into the button band.
  * cabinet indicator baked as a dead dark lens at CAB_LED.
  * far signal at the vanishing point baked as a dark mast, red eye at
    FAR_LED.
  * the puddle is baked WET BUT DARK at PUDDLE - the warm glint strip
    belongs on top of it, not in the bake.
  * drizzle emitter belongs centred on the signal halo, extents ~(28,34).
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gen_art import Canvas, C, SCENE_W, SCENE_H

# ------------------------------------------------------------- the camera ----
HZ = 262.0          # horizon row. ONE number, everything derives from it.
VPX = 300.0         # vanishing point, deliberately left of centre
EYE = 1.7           # camera height above the rail head, metres
FOCAL = 831.0       # ~60 deg horizontal on a 960 px frame
K = FOCAL * EYE     # 1412.7


def gy(d: float) -> float:
    """screen row of a ground point d metres in front of the camera."""
    return HZ + K / d


def ppm(y: float) -> float:
    """pixels per metre (both axes) for a ground row y."""
    return (y - HZ) / EYE


def gxd(x_m: float, d: float) -> float:
    """screen column of a point x_m metres right of the track centre."""
    return VPX + x_m * FOCAL / d


def top_of(h_m: float, d: float) -> float:
    """screen row of the top of a vertical h_m tall standing at distance d."""
    return gy(d) - h_m * ppm(gy(d))


# landmarks the living layer needs (canvas coords)
DRIP_SRC = (100, 141)     # left car eave
PUDDLE = (286, 418)       # four-foot, between the rails
SIGNAL_LENS = (340, 224)
CAB_LED = (346, 286)
FAR_LED = (305, 257)

BAND = (400, 290, 560, 390)   # the menu button band. keep it boring.


def in_band(x: float, y: float, pad: int = 0) -> bool:
    return (BAND[0] - pad <= x <= BAND[2] + pad
            and BAND[1] - pad <= y <= BAND[3] + pad)


def paint() -> Canvas:
    rng = random.Random("spoils:pitch:yard")
    c = Canvas(SCENE_W, SCENE_H)

    # ------------------------------------------------------------ helpers --
    def wob(x, a1, p1, ph1, a2, p2, ph2):
        """two sines of different period, so no long seam is ever a stripe."""
        return a1 * math.sin(x / p1 + ph1) + a2 * math.sin(x / p2 + ph2)

    def seam(a1, p1, a2, p2):
        ph1, ph2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
        return (a1, p1, ph1, a2, p2, ph2)

    def patch(cx, cy, w, h, col, squash=1.0):
        """ONE small solid wear blob. never speckle, never a dot."""
        for dy in range(-h, h + 1):
            t = 1.0 - (dy / float(h + 0.001)) ** 2
            if t <= 0:
                continue
            half = int(w * (t ** 0.62) * squash)
            if half < 1:
                continue
            c.hline(int(cx - half), int(cx + half), int(cy + dy), col)

    # ============================================================== 1. SKY ==
    # cold zenith falling into a burning horizon. eight solid bands, every
    # seam wobbled by two sines, and the four warm bands ALSO cooled
    # horizontally by distance from the glow so no seam is ever full width.
    SKY = ["090a14", "10141f", "172038", "1e1d39", "402751", "7a367b",
           "411d31", "752438", "884b2b", "be772b", "de9e41"]
    # THE COOLING LADDER NO LONGER PASSES THROUGH MAGENTA. it used to, so
    # every warm band out on the flanks turned into 7a367b and the whole
    # upper sky became one magenta field - synthwave, not dusk. the warm
    # bands now cool straight through plum into night, and magenta survives
    # only in its own thin band near the glow: an accent, not a stripe.
    COOL = ["de9e41", "be772b", "884b2b", "752438", "411d31",
            "402751", "1e1d39", "172038", "10141f"]
    cool_i = {n: i for i, n in enumerate(COOL)}
    MAGENTA = ["7a367b", "402751", "1e1d39", "172038", "10141f"]

    # band 5 (the magenta) is also NARROWED, and its two seams wobble on
    # unrelated periods so its thickness swings from ~17 px to nothing - in
    # places the upper seam overtakes the lower and the band simply is not
    # there for a stretch.
    seam_y = [50, 88, 122, 152, 181, 191, 214, 231, 245, 255]
    seam_w = [seam(6.0, 118.0, 3.5, 41.0), seam(5.5, 143.0, 3.0, 37.0),
              seam(5.5, 97.0, 3.0, 29.0), seam(5.0, 131.0, 2.5, 33.0),
              seam(4.0, 109.0, 2.4, 26.0), seam(4.6, 63.0, 2.8, 21.0),
              seam(3.2, 121.0, 1.8, 19.0), seam(2.6, 103.0, 1.6, 31.0),
              seam(2.0, 141.0, 1.3, 22.0), seam(1.6, 79.0, 1.0, 17.0)]

    GLOW_X = 300.0
    sky_col = [[None] * SCENE_W for _ in range(int(HZ))]
    for x in range(SCENE_W):
        edges = [int(round(seam_y[i] + wob(x, *seam_w[i])))
                 for i in range(len(seam_y))]
        for y in range(int(HZ)):
            b = 0
            while b < len(edges) and y >= edges[b]:
                b += 1
            name = SKY[b]
            if name in cool_i or name == "7a367b":
                # the falloff line itself waves in y, two periods, so the
                # cooling never hardens into a vertical edge
                dist = abs(x - GLOW_X
                           + 46.0 * math.sin(y * 0.0182 + 0.9)
                           + 19.0 * math.sin(y * 0.061 + 2.7))
                step = int(max(0.0, dist - 96.0) / 96.0)
                step = min(step, 4)
                if name == "7a367b":
                    # magenta cools out FAST: one step off the glow and it
                    # is already plum. that is what keeps it an accent.
                    name = MAGENTA[min(step, len(MAGENTA) - 1)]
                else:
                    name = COOL[min(cool_i[name] + step, len(COOL) - 1)]
            sky_col[y][x] = C(name)
    for y in range(int(HZ)):
        row = sky_col[y]
        for x in range(SCENE_W):
            c.set(x, y, row[x])

    # two cloud bars lying across the afterglow, lit from beneath. different
    # lengths, thicknesses, bodies and lip colours - never a matched pair.
    def cloud(x0, x1, ymid, thick, body, lip, w1, w2):
        span = float(x1 - x0)
        for x in range(x0, x1 + 1):
            t = (x - x0) / span
            taper = min(1.0, (min(t, 1.0 - t) / 0.17))
            th = thick * (0.55 + 0.45 * math.sin(t * 5.1 + w2)) * taper
            if th < 1.0:
                continue
            cy = ymid + wob(x, 2.6, w1, 0.4, 1.5, 27.0, 2.1)
            y0 = int(round(cy - th * 0.5))
            y1 = int(round(cy + th * 0.5))
            c.vline(x, y0, y1, C(body))
            c.set(x, y1 + 1, C(lip))
            c.set(x, y0 - 1, C("341c27") if body != "341c27" else C("241527"))

    cloud(58, 524, 156, 12.0, "241527", "884b2b", 96.0, 0.7)
    cloud(468, 906, 194, 8.0, "1e1d39", "602c2c", 71.0, 2.9)
    # thinner streaks so the sky is never two bars on a flat field
    cloud(214, 612, 122, 4.0, "172038", "402751", 133.0, 4.3)
    cloud(624, 940, 138, 5.0, "1e1d39", "402751", 83.0, 5.6)
    cloud(96, 388, 208, 4.0, "341c27", "752438", 61.0, 1.8)
    cloud(392, 828, 224, 3.0, "411d31", "884b2b", 111.0, 3.4)
    cloud(40, 300, 236, 3.0, "752438", "be772b", 47.0, 0.2)
    # two bars laid ACROSS what is left of the magenta, so it is broken into
    # islands rather than a band. one takes its lip FROM the magenta, which
    # is the only place that hue is allowed to be bright.
    cloud(104, 556, 184, 7.0, "402751", "7a367b", 89.0, 1.3)
    cloud(590, 878, 178, 5.0, "402751", "411d31", 53.0, 4.8)

    # ==================================================== 2. THE DISTRICT ==
    # flat solid black, drawn UPWARD from the horizon (critic fix 1), with a
    # low gap over the vanishing point so the line converges against sky.
    HZI = int(HZ)
    roof = [HZI] * SCENE_W

    def shed(x0, x1, h, cap=0):
        for x in range(max(0, x0), min(SCENE_W, x1)):
            roof[x] = min(roof[x], HZI - h)
        if cap:
            for x in range(max(0, x0 + cap), min(SCENE_W, x1 - cap)):
                roof[x] = min(roof[x], HZI - h - 3)

    sx = -20
    while sx < SCENE_W:
        w = rng.randint(38, 96)
        h = rng.randint(5, 15)
        if 262 < sx < 340:            # the gap over the vanishing point
            h = rng.randint(0, 2)
        elif 402 < sx + w and sx < 566:   # low over the button band
            h = rng.randint(4, 9)
        shed(sx, sx + w, h, cap=rng.choice((0, 0, 6, 11)))
        sx += w + rng.randint(-4, 9)
    # a water tower, well left of the button band
    shed(360, 396, 24)
    shed(366, 390, 32)
    for x in range(370, 386):
        roof[x] = min(roof[x], HZI - 34)
    c.vline(372, HZI - 34, HZI, C("090a14"))
    # a scrapyard gantry reaching in from the right (mostly behind the car)
    shed(596, 604, 30)
    shed(676, 684, 26)
    for x in range(596, 686):
        roof[x] = min(roof[x], HZI - 30 + int((x - 596) * 0.045))
    # three stacks, no two the same
    for (stx, sth, stw) in ((196, 27, 5), (486, 17, 4), (556, 21, 6)):
        for x in range(stx, stx + stw):
            roof[x] = min(roof[x], HZI - sth)
    # stock stabled on the far sidings: a broken run of stored wagons along
    # the horizon, so the skyline says TRAINYARD instead of generic town.
    wx_ = 356
    while wx_ < 646:
        ln = rng.randint(26, 58)
        ht = rng.randint(6, 10)
        if rng.random() < 0.24:
            wx_ += rng.randint(9, 26)          # a gap in the rake
            continue
        for x in range(wx_, min(SCENE_W, wx_ + ln)):
            roof[x] = min(roof[x], HZI - ht)
        if rng.random() < 0.4:                  # a taller van in the rake
            for x in range(wx_ + 4, min(SCENE_W, wx_ + ln - 4)):
                roof[x] = min(roof[x], HZI - ht - rng.randint(2, 4))
        wx_ += ln + rng.randint(2, 7)
    for x in range(SCENE_W):
        r = roof[x] + int(round(wob(x, 1.2, 53.0, 1.1, 0.8, 17.0, 3.3)))
        if r < HZI:
            c.vline(x, r, HZI - 1, C("090a14"))

    # ======================================================= 3. THE GROUND ==
    # horizontal bands only. NO ray-shaped edge is allowed to cross the
    # button band, so the ground grades by depth, not by a shoulder line on
    # the right (any ray with slope 0.78..9.29 cuts the band - checked).
    g1 = seam(4.0, 127.0, 2.0, 31.0)      # haze -> far ballast  (~268)
    g2 = seam(5.0, 151.0, 2.6, 43.0)      # far ballast -> mid   (~282)
    g3 = seam(6.0, 173.0, 3.0, 47.0)      # mid -> near cinder   (~404)
    # THE HAZE OFF THE FAR YARD IS NOT A STRIPE. it used to be a constant
    # ~14 px of 394a50 running wall to wall, which made it the second
    # brightest thing in the frame and very nearly a band of its own. now:
    # its lower edge is its upper edge PLUS a thickness that swings on three
    # periods sharing no factor - so it swells past 20 px, pinches to one,
    # and in places the thickness goes NEGATIVE and the haze is simply not
    # there. its colour also drops a step away from the glow, so it dies
    # into the ground colour before it ever reaches a frame edge.
    hz = [rng.uniform(0.0, 6.28) for _ in range(4)]
    e1s, e2s, e3s, hz_col = [], [], [], []
    for x in range(SCENE_W):
        e1 = 267.0 + wob(x, *g1)
        thick = (6.5 + 8.0 * math.sin(x / 59.0 + hz[0])
                 + 4.5 * math.sin(x / 23.0 + hz[1])
                 + 3.5 * math.sin(x / 151.0 + hz[2]))
        e1s.append(e1)
        e2s.append(e1 + thick + wob(x, *g2) * 0.3)
        e3s.append(404.0 + wob(x, *g3))
        hd = abs(x - GLOW_X + 46.0 * math.sin(x / 83.0 + hz[3]))
        hz_col.append(C("394a50") if hd < 196.0 else C("202e37"))
    for y in range(HZI, SCENE_H):
        for x in range(SCENE_W):
            if y < e1s[x]:
                dist = abs(x - GLOW_X + 12.0 * math.sin(y * 0.3))
                step = min(int(max(0.0, dist - 118.0) / 108.0), 2)
                col = C(("411d31", "402751", "1e1d39")[step])
            elif y < e2s[x]:
                col = hz_col[x]
            elif y < e3s[x]:
                col = C("202e37")
            else:
                col = C("151d28")
            c.set(x, y, col)

    # THE BUTTON BAND MAY NOT HAVE DETAIL - but it was a perfectly flat
    # field of one colour, and flat reads as unfinished. so: ONE broad
    # hollow, ONE palette step darker, with a damp core one step off that.
    # no edge is straight and none of it is smaller than about 40 px, so
    # there is nothing here for the eye to resolve behind a button.
    # (a first cut put a 172038 damp core inside this. it read as a river
    # sweeping across the middle of the frame - loud, and exactly the kind
    # of shape a button must not sit on. one step, one shape, nothing else.)
    hol = [rng.uniform(0.0, 6.28) for _ in range(3)]
    for x in range(196, 892):
        t = (x - 196) / 696.0
        env = math.sin(math.pi * t) ** 0.5          # dies out at both ends
        top = (308.0 + 17.0 * math.sin(x / 143.0 + hol[0])
               + 7.0 * math.sin(x / 47.0 + hol[1]))
        bot = top + (14.0 + 44.0 * env) + 10.0 * math.sin(x / 71.0 + hol[2])
        if bot - top < 5.0:
            continue
        c.vline(x, int(top), int(bot), C("151d28"))

    # one broad shallow depression in the cinder, kept ENTIRELY BELOW the
    # button band: a single palette step, huge scale, no readable edge.
    for y in range(398, 470):
        t = (y - 398) / 72.0
        cx = 640 + 150 * t + 30 * math.sin(t * 2.3)
        half = 120 + 190 * t
        c.hline(int(cx - half), int(cx + half), y, C("10141f"))

    # the LEFT shoulder: past the ballast the yard goes to cinder and weed.
    # (only the left - a right-hand edge would be a ray through the band.)
    for y in range(HZI + 8, SCENE_H):
        ex = VPX - 0.5883 * 3.9 * (y - HZ) + wob(y, 5.0, 29.0, 2.2, 2.5, 11.0, 0.6)
        if ex > 1:
            c.hline(0, int(ex), y, C("151d28"))
        if ex > 3:
            c.hline(max(0, int(ex) - 2), int(ex), y, C("10141f"))

    # ballast chip patches - six SMALL solid ones, never speckle
    for i in range(6):
        px = rng.randrange(150, 720)
        py = rng.randrange(300, 520)
        if in_band(px, py, 26):
            px = rng.randrange(600, 760)
        patch(px, py, rng.randint(7, 17), rng.randint(2, 5), C("394a50"))
    for i in range(9):
        px = rng.randrange(60, 900)
        py = rng.randrange(300, 540)
        if in_band(px, py, 20):
            continue
        patch(px, py, rng.randint(9, 26), rng.randint(2, 6), C("10141f"))

    # ==================================================== 4. THE SLEEPERS ==
    # TRACK IS A LADDER, and a ladder is exactly the repeating grid this
    # project bans, so the rungs have to be fought on every axis at once:
    #   * TONE over a much wider range - rotted black timber next to a
    #     bleached concrete one next to fresh creosote, never twice running
    #   * LENGTH - short ones, and ends BURIED so they stop short of where
    #     the row says they should
    #   * BALLAST WASHING OVER one end of a sleeper entirely
    #   * SINKING - some sit low and read half as thick
    #   * SIDEWAYS SHIFT as well as skew, so the row is not even a line
    #   * DROPOUTS, sometimes two together, sometimes a long clean run
    # the convergence itself is untouched: every sleeper is still projected.
    LIT = {"10141f": "151d28", "151d28": "202e37", "202e37": "394a50",
           "241527": "341c27", "341c27": "4d2b32", "4d2b32": "602c2c",
           "411d31": "602c2c", "602c2c": "7a4841"}
    # weighted: rotten timber dominates, with a couple of concretes and a
    # couple of near-black ones. THE CONCRETE TONE FLIPS WITH THE GROUND -
    # 202e37 where the cinder is 151d28, 151d28 where the ballast is
    # 202e37 - because a sleeper the same colour as the ground under it
    # does not read as a sleeper at all, it just deletes a rung.
    NEAR_POOL = (["241527"] * 3 + ["341c27"] * 5 + ["4d2b32"] * 4
                 + ["602c2c"] * 2 + ["411d31"] * 3 + ["10141f"]
                 + ["202e37"])
    FAR_POOL = (["341c27"] * 4 + ["4d2b32"] * 4 + ["241527"] * 3
                + ["411d31"] * 2 + ["151d28"] * 2 + ["10141f"] * 2
                + ["602c2c"])
    HALF_MAX = 1.25          # metres. capped so no sleeper end reaches x 400
    d = 3.6
    prev_body = ""
    prev2 = ""
    gap_run = 0
    dropped = 0
    far_merge_y = None
    while d < 90.0:
        y_near = gy(d)
        y_far = gy(d + 0.25)
        if y_near - y_far < 0.8:
            far_merge_y = y_near
            break
        if y_far < SCENE_H + 40:
            half = min(HALF_MAX, rng.uniform(0.94, 1.26))
            skew = rng.uniform(-2.9, 2.9)
            shift = rng.uniform(-0.05, 0.05)        # metres, sideways
            xl = gxd(-half + shift, d)
            xr = gxd(half * rng.uniform(0.90, 1.0) + shift, d)
            pool = NEAR_POOL if y_near > 404 else FAR_POOL
            pool = [p for p in pool if p != prev_body and p != prev2] or pool
            body = rng.choice(pool)
            prev2, prev_body = prev_body, body
            # a dropout, and dropouts cluster: after one, the next is likely.
            # RARE NEAR THE CAMERA - only about four sleepers fall in the
            # bottom 90 rows of the frame, so a dropout rate that reads as
            # pleasant thinning up the line deletes the foreground track
            # entirely down here. (it did: two passes had bare ground under
            # the near rails.)
            near = y_near > 470
            if gap_run and not near:
                missing = rng.random() < 0.42
            else:
                missing = rng.random() < (0.05 if near else 0.13) and d > 4.4
            gap_run = gap_run + 1 if missing else 0
            if missing:
                dropped += 1
            lit = LIT[body]
            # sunk sleepers show less of their face
            sink = rng.uniform(0.0, 0.34) if rng.random() < 0.30 else 0.0
            y_top = y_far + (y_near - y_far) * sink
            # ends buried in the ballast - independent per end. capped so a
            # sleeper never loses more than a third of itself to burial;
            # the wash below can still eat one end on top of that.
            bl = rng.uniform(0.0, 0.22) if rng.random() < 0.5 else 0.0
            br = rng.uniform(0.0, 0.22) if rng.random() < 0.5 else 0.0
            if bl + br > 0.32:
                bl, br = bl * 0.5, br * 0.5
            span = max(1.0, xr - xl)
            x0 = int(xl + span * bl)
            x1 = int(xr - span * br)
            if not missing and x1 > x0:
                for x in range(x0, x1 + 1):
                    t = (x - xl) / span
                    off = skew * (t - 0.5) * 2.0
                    y0 = int(round(y_top + off))
                    y1 = int(round(y_near + off))
                    c.vline(x, y0, y1, C(body))
                    c.set(x, y0, C("241527") if y_near > 372 else C("10141f"))
                    if y1 - y0 >= 2:
                        c.set(x, y1, C(lit))
                if y_near - y_top >= 5 and rng.random() < 0.45:
                    # a split / adze mark, structural not noise
                    wx = int(rng.uniform(x0 + 6, max(x0 + 7, x1 - 6)))
                    c.vline(wx, int(y_top + 1), int(y_near - 1), C("241527"))
                # ballast washed clean over one end: a solid tongue of the
                # ground colour eating into the sleeper, so the row loses a
                # rung end without losing the sleeper
                if rng.random() < 0.34 and span > 26:
                    bal = C("151d28") if y_near > 404 else C("202e37")
                    side = rng.choice((-1, 1))
                    wln = int(span * rng.uniform(0.12, 0.34))
                    for k in range(wln):
                        u = k / max(1.0, wln - 1.0)
                        wx = x0 + k if side < 0 else x1 - k
                        t = (wx - xl) / span
                        off = skew * (t - 0.5) * 2.0
                        hgt = (y_near - y_top) * (1.0 - u ** 0.7)
                        c.vline(wx, int(y_top + off),
                                int(y_top + off + hgt), bal)
        # the pitch itself wanders, and now and then a chair is missing and
        # the gap doubles
        d += 0.60 + rng.uniform(-0.13, 0.15)
        if rng.random() < 0.07:
            d += rng.uniform(0.22, 0.44)

    # beyond the merge point the individual sleepers are sub-pixel: one
    # continuous bed instead of a moire ladder.
    if far_merge_y:
        for y in range(HZI + 5, int(far_merge_y) + 1):
            half = 0.5883 * 1.2 * (y - HZ)
            c.hline(int(VPX - half), int(VPX + half), y,
                    C("341c27") if y > 300 else C("241527"))

    # ======================================================= 5. THE RAILS ==
    GAUGE_H = 0.7175
    for y in range(HZI + 3, SCENE_H):
        pm = ppm(y)
        w = max(1, int(round(0.075 * pm)))
        if y > 452:
            head = "819796"
        elif y > 372:
            head = "577277"
        elif y > 306:
            head = "394a50"
        elif y > 276:
            head = "202e37"
        else:
            head = "241527"
        for s in (-1, 1):
            cx = int(round(VPX + s * GAUGE_H * FOCAL / (K / (y - HZ))))
            c.hline(cx - w // 2, cx - w // 2 + w - 1, y, C(head))
            c.set(cx - w // 2 - 1, y, C("202e37"))
            c.set(cx - w // 2 + w, y, C("151d28"))
    # THE ONE BRIGHT LINE ON THE GROUND, and it points at the vanishing
    # point: the ember lying along the left rail head.
    for y in range(292, 356):
        cx = int(round(VPX - GAUGE_H * (y - HZ) / EYE))
        c.set(cx, y, C("be772b") if y < 336 else C("884b2b"))
        c.set(cx + 1, y, C("be772b") if y < 322 else C("884b2b"))
        if y < 330:
            c.set(cx + 2, y, C("602c2c"))
    for y in range(392, 412):           # a shorter, cooler answer on the right
        cx = int(round(VPX + GAUGE_H * (y - HZ) / EYE))
        c.set(cx + 1, y, C("884b2b"))

    # the baked puddle in the four-foot: WET BUT DARK. the warm glint strip
    # of the living layer sits on top of this, so nothing bright is baked.
    patch(PUDDLE[0], PUDDLE[1], 15, 4, C("172038"))
    patch(PUDDLE[0] + 1, PUDDLE[1] - 1, 10, 2, C("253a5e"))
    c.hline(PUDDLE[0] - 8, PUDDLE[0] + 4, PUDDLE[1] + 4, C("10141f"))

    # ==================================================== 6. THE FAR HAZE ==
    # the line is swallowed by haze rather than converging to a black spike
    for y in range(HZI, HZI + 7):
        for x in range(int(VPX) - 74, int(VPX) + 74):
            t = abs(x - VPX) / 74.0
            if rng.random() < 0.0:
                continue
            if t < 0.45:
                c.set(x, y, C("752438") if y < HZI + 3 else C("411d31"))
            elif t < 0.85:
                c.set(x, y, C("411d31"))

    # ================================================ 7. TELEGRAPH POLES ==
    # collinear with the VP by construction. reverse aerial perspective:
    # near pole has real lit/shade faces, far ones flatten to silhouette.
    # THE NEAREST POLE NOW SHOWS ITS FOOT. it used to stand at d=30, which
    # projects to x 120 - inside the left car's screen span, and because the
    # pole line is FURTHER from the track than the car flank, a pole inside
    # that span is always the further of the two and always occluded. so the
    # strongest pole in the frame was a crossarm floating with no base. two
    # things fixed it together: the car ends nearer (LC_D_FAR, x 116) and the
    # pole steps back to 34 m (x 141), which puts 25 px of open ballast
    # between the car's far corner and the pole's foot. the run is also
    # re-spaced geometrically so the gaps shrink monotonically toward the VP.
    POLE_X = -6.5
    P_D = [34.0, 46.0, 62.0, 84.0, 114.0, 154.0, 208.0, 282.0, 382.0]
    LEAN = [0, 1, -1, 1, 0, -1, 1, 0, -1]
    poles = []
    for i, pd in enumerate(P_D):
        h = 8.0 + rng.uniform(-0.45, 0.45)
        by = gy(pd)
        pm = ppm(by)
        bx = gxd(POLE_X, pd)
        ty = by - h * pm
        w = max(1, int(round(0.30 * pm)))
        arm_hi = h - 0.6
        arm_lo = h - 1.55
        poles.append(dict(d=pd, bx=bx, by=by, ty=ty, w=w, pm=pm,
                          hi=by - arm_hi * pm, lo=by - arm_lo * pm,
                          lean=LEAN[i], no_top=(i == 2)))

    for i, p in enumerate(poles):
        bx, by, ty, w = p["bx"], p["by"], p["ty"], p["w"]
        lean = p["lean"]
        if i == 0:
            body, shade, lit = "4d2b32", "341c27", "602c2c"
        elif i == 1:
            body, shade, lit = "341c27", "241527", "4d2b32"
        elif i <= 3:
            body, shade, lit = "241527", "10141f", "341c27"
        else:
            body = shade = lit = "090a14"
        h_px = by - ty
        for k in range(int(h_px) + 1):
            yy = int(by) - k
            t = k / max(1.0, h_px)
            xx = int(round(bx + lean * t))
            c.hline(xx, xx + w - 1, yy, C(body))
            if w >= 2:
                c.set(xx + w - 1, yy, C(lit))      # ember side (toward the VP)
                c.set(xx, yy, C(shade))
        # crossarms
        for (ay, alen, skip) in ((p["hi"], 2.3, p["no_top"]),
                                 (p["lo"], 1.9, False)):
            if skip:
                continue
            ah = 0.5 * alen * p["pm"]
            axc = bx + lean * ((by - ay) / max(1.0, h_px))
            th = max(1, int(round(0.14 * p["pm"])))
            c.rect(int(axc - ah), int(ay), int(axc + ah + w - 1),
                   int(ay) + th - 1, C(shade if i else "4d2b32"))
            if i == 0:
                c.hline(int(axc - ah), int(axc + ah + w - 1), int(ay),
                        C("602c2c"))
            if i <= 2:
                for e in (int(axc - ah), int(axc + ah + w - 1)):
                    c.set(e, int(ay) - 1, C("73bed3"))
        if i <= 1:                       # a brace under the lower arm
            c.set(int(bx) - 1, int(p["lo"]) + 3, C(shade))
            c.set(int(bx) + w, int(p["lo"]) + 3, C(shade))

    # the wires: four runs, sag solved in world metres so it shrinks with
    # distance on its own. this is the thing the eye follows to the VP.
    def wire_col(y):
        if y < 146:
            return C("402751")
        if y < 208:
            return C("241527")
        return C("090a14")

    def run_wire(d0, d1, h0, sideoff, sag):
        steps = 150
        for k in range(steps + 1):
            t = k / steps
            dd = d0 + (d1 - d0) * t
            hh = h0 - sag * 4.0 * t * (1.0 - t)
            y = gy(dd) - hh * ppm(gy(dd))
            x = gxd(POLE_X + sideoff, dd)
            if 0 <= x < SCENE_W and 0 <= y < HZ + 4:
                c.set(int(x), int(y), wire_col(y))

    for i in range(len(poles) - 1):
        d0, d1 = P_D[i], P_D[i + 1]
        sag = 0.55 * (1.0 - i * 0.06)
        for (hh, so) in ((7.42, -1.15), (7.42, 1.15),
                         (6.47, -0.95), (6.47, 0.95)):
            if i == 2 and hh > 7.0:      # pole 3 lost its upper arm
                continue
            run_wire(d0, d1, hh, so, sag)
    # and off the left edge of frame, toward a pole we never see
    for (hh, so) in ((7.42, -1.15), (7.42, 1.15), (6.47, -0.95), (6.47, 0.95)):
        run_wire(30.0, 17.5, hh, so, 0.6)

    # ====================================================== 8. THE SIGNAL ==
    # right of the running line but FAR (d=48), which is the only way a
    # signal on that side keeps clear of the button band: anything nearer
    # than ~30 m on the right projects straight into it.
    S_D = 48.0
    s_by = gy(S_D)
    s_pm = ppm(s_by)
    s_x = gxd(2.3, S_D)
    s_top = s_by - 4.4 * s_pm
    mw = max(2, int(round(0.22 * s_pm)))
    c.rect(int(s_x), int(s_top), int(s_x) + mw - 1, int(s_by), C("394a50"))
    c.vline(int(s_x), int(s_top), int(s_by), C("202e37"))
    c.vline(int(s_x) + mw - 1, int(s_top) + 2, int(s_by), C("577277"))
    # head: hood over two lamps, only the top one still shows an aspect
    hw = max(4, int(round(0.62 * s_pm)))
    hh_ = max(9, int(round(1.35 * s_pm)))
    hx = int(s_x) - hw // 2 + mw // 2
    hy = int(s_top)
    c.rect(hx, hy, hx + hw, hy + hh_, C("151d28"))
    c.vline(hx + hw, hy + 1, hy + hh_, C("202e37"))
    c.hline(hx - 1, hx + hw + 1, hy - 1, C("202e37"))     # hood lip
    c.rect(hx + 2, hy + 2, hx + hw - 2, hy + 4, C("752438"))   # LENS, unlit
    c.rect(hx + 2, hy + 7, hx + hw - 2, hy + 9, C("10141f"))   # dead lamp
    # relay cabinet at the foot
    cw = max(6, int(round(0.9 * s_pm)))
    ch = max(6, int(round(1.05 * s_pm)))
    cx0 = int(s_x) - 2
    c.rect(cx0, int(s_by) - ch, cx0 + cw, int(s_by), C("394a50"))
    c.rect(cx0, int(s_by) - ch, cx0 + 2, int(s_by), C("577277"))
    c.hline(cx0, cx0 + cw, int(s_by) - ch, C("577277"))
    c.set(CAB_LED[0], CAB_LED[1], C("172038"))           # dead indicator
    c.hline(cx0 - 1, cx0 + cw + 1, int(s_by) + 1, C("10141f"))
    # the visible cable: standing rule - anything powered shows its supply
    for k in range(30):
        t = k / 29.0
        c.set(int(cx0 + cw * 0.5 + (poles[1]["bx"] - cx0 - cw * 0.5) * t),
              int(s_by - 2 + math.sin(t * 3.14) * 4 - t * 3), C("10141f"))

    # A LINESIDE HUT out on the right-hand shoulder, 41 m off. it is the one
    # object that gives the open right of the yard a midground - and it sits
    # at x 596-656, entirely clear of the button band's x range, so it can be
    # as dark as it likes without ever coming near the buttons.
    h_d = 41.5
    h_by = gy(h_d)
    h_pm = ppm(h_by)
    h_x0 = int(gxd(14.4, h_d))
    h_x1 = int(gxd(17.8, h_d))
    h_top = int(h_by - 2.5 * h_pm)
    c.rect(h_x0, h_top, h_x1, int(h_by), C("10141f"))
    c.rect(h_x0, h_top, h_x0 + 5, int(h_by), C("241527"))   # sunset-lit face
    c.vline(h_x0, h_top + 1, int(h_by), C("4d2b32"))
    for k in range(9):                                       # a pitched roof
        c.hline(h_x0 - 3 + k, h_x1 + 3 - k, h_top - 8 + k, C("090a14"))
    c.hline(h_x0 - 3, h_x1 + 3, h_top - 1, C("202e37"))      # eave catch
    c.rect(h_x0 + 12, h_top + 8, h_x0 + 19, h_top + 16, C("090a14"))  # window
    c.hline(h_x0 - 2, h_x1 + 2, int(h_by) + 1, C("090a14"))

    # THE FAR SIGNAL: a dark mast planted on the vanishing point. its red eye
    # is the living layer's slowest blink and the strongest depth cue.
    c.vline(FAR_LED[0], FAR_LED[1] - 1, int(gy(400.0)), C("241527"))
    c.vline(FAR_LED[0] + 1, FAR_LED[1], int(gy(400.0)), C("10141f"))
    c.set(FAR_LED[0], FAR_LED[1], C("752438"))

    # ===================================================== 9. THE BOXCARS ==
    def boxcar(flank_x, d_near, d_far, roof_h, floor_h, side, pal,
               door=None, ribs=13, rust=0, strake=0.19, mid=0.62):
        """one car, projected. `side` -1 = left of the line (we see its
        right-hand flank), +1 = right. lit face, shade face, real edges."""
        body, shade, hi, dark = pal
        x_near = gxd(flank_x, d_near)
        x_far = gxd(flank_x, d_far)
        lo_x, hi_x = (min(x_near, x_far), max(x_near, x_far))

        def dof(x):
            return flank_x * FOCAL / (x - VPX)

        # --- the flank
        for x in range(max(0, int(lo_x)), min(SCENE_W, int(hi_x) + 1)):
            dd = dof(x)
            if dd <= 0:
                continue
            yg = gy(dd)
            pm = ppm(yg)
            y_roof = yg - roof_h * pm
            y_floor = yg - floor_h * pm
            # banded cel light: only the top strake catches the last of the
            # sky. everything below is in the car's own shade.
            band = y_roof + (y_floor - y_roof) * strake
            band2 = y_roof + (y_floor - y_roof) * mid
            for y in range(int(y_roof), int(y_floor) + 1):
                c.set(x, y, C(hi) if y <= band
                      else (C(body) if y <= band2 else C(shade)))
            # eave: soffit under a 1 px lip
            c.set(x, int(y_roof), C(hi))
            c.set(x, int(y_roof) + 1, C(dark))
            c.set(x, int(y_roof) + 2, C(shade))
            # solebar, then the underframe void
            c.set(x, int(y_floor) - 1, C(body))
            c.set(x, int(y_floor), C(body))
            for y in range(int(y_floor) + 1, int(yg) + 1):
                c.set(x, y, C("090a14"))
        # --- ribs, spaced evenly ALONG THE CAR so they tighten with depth
        length = abs(d_far - d_near)
        for r in range(ribs + 1):
            fr = r / float(ribs)
            dd = d_near + (d_far - d_near) * fr
            x = gxd(flank_x, dd)
            if not (0 <= x < SCENE_W):
                continue
            yg = gy(dd)
            pm = ppm(yg)
            y_roof = yg - roof_h * pm
            y_floor = yg - floor_h * pm
            rw = max(1, int(round(0.06 * pm)))
            band = y_roof + (y_floor - y_roof) * strake
            for k in range(rw):
                xx = int(x) + k * side
                c.vline(xx, int(y_roof) + 3, int(y_floor) - 1, C(shade))
            # the rib only catches light where the flank does - one strake
            c.vline(int(x) - side, int(y_roof) + 3, int(band), C(hi))
        # --- door
        if door:
            d0, d1, ajar, dcol, dhi = door
            xa, xb = sorted((gxd(flank_x, d0), gxd(flank_x, d1)))
            for x in range(max(0, int(xa)), min(SCENE_W, int(xb))):
                dd = dof(x)
                yg = gy(dd)
                pm = ppm(yg)
                y_roof = yg - (roof_h - 0.35) * pm
                y_floor = yg - (floor_h + 0.12) * pm
                if ajar and x > xa + (xb - xa) * 0.44:
                    # THE DEEPEST VALUE IN THE FRAME: the gap into the car
                    c.vline(x, int(y_roof), int(y_floor), C("090a14"))
                    c.set(x, int(y_roof), C(dark))
                else:
                    c.vline(x, int(y_roof), int(y_floor), C(dcol))
                    c.vline(x, int(y_roof), int(y_roof + (y_floor - y_roof)
                                                * 0.22), C(dhi))
                    c.set(x, int(y_roof), C(dark))
                    if int(x - xa) % 9 == 0:
                        c.vline(x, int(y_roof) + 2, int(y_floor) - 1, C(shade))
            # the leaf's leading edge, stopped where it was dragged to
            xe = int(xa + (xb - xa) * 0.44)
            c.vline(xe, int(gy(dof(xe)) - (roof_h - 0.3) * ppm(gy(dof(xe)))),
                    int(gy(dof(xe)) - (floor_h + 0.1) * ppm(gy(dof(xe)))),
                    C(dhi))
            # the door rail across the top, and its track
            for x in range(max(0, int(xa) - 8), min(SCENE_W, int(xb) + 8)):
                dd = dof(x)
                yg = gy(dd)
                pm = ppm(yg)
                c.set(x, int(yg - (roof_h - 0.28) * pm), C("577277"))
                c.set(x, int(yg - (roof_h - 0.44) * pm), C("202e37"))
        # --- rust, running DOWN as streaks from the door rail. small solid
        # patches, never dots.
        for i in range(rust):
            fr = rng.uniform(0.05, 0.95)
            dd = d_near + (d_far - d_near) * fr
            x = int(gxd(flank_x, dd))
            yg = gy(dd)
            pm = ppm(yg)
            y0 = int(yg - (roof_h - rng.uniform(0.45, 1.5)) * pm)
            ln = max(3, int(rng.uniform(0.12, 0.36) * pm))
            wdt = max(2, int(rng.uniform(0.09, 0.22) * pm))
            col = C("602c2c") if rng.random() < 0.7 else C("4d2b32")
            for k in range(ln):
                t = k / float(ln)
                shrink = int(wdt * t * 0.7)
                c.hline(x + shrink, x + wdt - 1, y0 + k,
                        col if t < 0.55 else C("4d2b32"))
            c.hline(x, x + wdt - 1, y0 - 1, C(dark))
        return (lo_x, hi_x)

    # LEFT CAR - ochre livery (make_boxcar liveries[0]), door dragged half
    # open, the deepest black in the frame sitting in that gap. it ends at
    # LC_D_FAR rather than 24 m so the nearest telegraph pole's foot clears
    # its far corner - see the pole section.
    LC_D_FAR = 19.0
    boxcar(flank_x=-4.2, d_near=9.0, d_far=LC_D_FAR, roof_h=4.25, floor_h=1.15,
           side=-1, pal=("241527", "10141f", "602c2c", "090a14"),
           door=(12.6, 16.4, True, "4d2b32", "884b2b"), ribs=11, rust=7,
           strake=0.15, mid=0.58)
    # its ONE lit edge: the far corner post facing the ember
    lc_far_x = int(gxd(-4.2, LC_D_FAR))
    lc_by = gy(LC_D_FAR)
    c.vline(lc_far_x, int(lc_by - 4.25 * ppm(lc_by)), int(lc_by), C("602c2c"))
    c.vline(lc_far_x - 1, int(lc_by - 4.25 * ppm(lc_by)) + 2, int(lc_by) - 2,
            C("be772b"))
    # ladder on the far end, and the roof grab iron
    for k in range(7):
        yy = int(lc_by - (1.3 + k * 0.42) * ppm(lc_by))
        c.hline(lc_far_x - 9, lc_far_x - 2, yy, C("577277"))
    c.vline(lc_far_x - 9, int(lc_by - 4.1 * ppm(lc_by)), int(lc_by - 1.2 * ppm(lc_by)), C("394a50"))
    c.vline(lc_far_x - 2, int(lc_by - 4.1 * ppm(lc_by)), int(lc_by - 1.2 * ppm(lc_by)), C("202e37"))
    # bogies
    # bogies stay almost invisible: under a car at dusk everything is black,
    # and a lighter block down there reads as an arch, not a truck.
    for bd in (10.4, 11.9, 16.3, 17.8):
        bx = int(gxd(-4.2, bd))
        byy = gy(bd)
        pm = ppm(byy)
        c.hline(bx - int(0.42 * pm), bx + int(0.42 * pm),
                int(byy - 0.62 * pm), C("151d28"))     # axlebox line only
        c.hline(bx - int(0.30 * pm), bx + int(0.30 * pm),
                int(byy - 0.61 * pm), C("10141f"))
    # its shadow, thrown toward the camera (the sun set down the line)
    for x in range(0, min(SCENE_W, lc_far_x + 30)):
        dd = -4.2 * FOCAL / (x - VPX) if x != int(VPX) else 99.0
        if dd <= 0:
            continue
        yg = gy(dd)
        ln = 14 + int(0.20 * ppm(yg))
        c.vline(x, int(yg), int(yg) + ln, C("10141f"))
        c.vline(x, int(yg), int(yg) + ln // 2, C("090a14"))

    # RIGHT CAR - green livery (liveries[1]): different livery, different
    # door state, different distance, different crop, different wear, and a
    # different lit-edge colour. it also shows a RAKING END FACE, so it is
    # not a flat rectangle with a highlight line (critic finding 2).
    # its body is ONE STEP LIGHTER than it used to be (10141f -> 151d28).
    # at 10141f its ribs, its shade face and its own dirt were all within
    # two RGB steps of each other, so nothing drawn on it could read and it
    # carried its whole side of the frame on silhouette alone. it is still
    # the darkest large mass in the picture; it just has room to hold
    # detail now. NO rust streaks here on purpose - the left car has those,
    # and wear that only moves is not wear that differs.
    RC_X, RC_DN, RC_DF = 9.0, 13.0, 20.0
    RC_ROOF, RC_FLOOR = 4.25, 1.15
    rc = boxcar(flank_x=RC_X, d_near=RC_DN, d_far=RC_DF, roof_h=RC_ROOF,
                floor_h=RC_FLOOR, side=1,
                pal=("151d28", "10141f", "19332d", "090a14"),
                door=None, ribs=9, rust=0, strake=0.17, mid=0.70)

    # every span below is CLAMPED to the flank's own screen extent. it was
    # not, and the first cut hung a roof vent and a repair plate over the
    # near END face, where they read as windows on the wrong plane.
    RC_XA, RC_XB = int(gxd(RC_X, RC_DF)), int(gxd(RC_X, RC_DN))

    def rc_col(x):
        """(ground row, px/metre) for one column of the right car's flank."""
        yg = gy(RC_X * FOCAL / (x - VPX))
        return yg, ppm(yg)

    def rc_span(d0, d1):
        a, b = sorted((gxd(RC_X, d0), gxd(RC_X, d1)))
        return max(RC_XA, int(a)), min(RC_XB, int(b))

    # --- THE SLIDING DOOR. shut, top-hung, padlocked, and deliberately
    # nothing like the left car's dragged-open plank leaf.
    # IT IS A REPLACEMENT DOOR OFF ANOTHER CAR, so it is a different paint
    # from the flank: warm maroon against the car's cold green-grey. that
    # is what finally made it read. two earlier cuts painted it in the
    # car's own values - once flat, once with its light break moved - and
    # both times it disappeared, because two colours a step apart in the
    # dark are the same colour. HUE at equal value reads; value alone did
    # not, and value contrast big enough to read would have made a hole.
    dxa, dxb = rc_span(15.2, 18.4)
    for x in range(dxa, dxb + 1):
        yg, pm = rc_col(x)
        yt = yg - (RC_ROOF - 0.34) * pm
        yb = yg - (RC_FLOOR + 0.12) * pm
        b1 = yt + (yb - yt) * 0.24
        b2 = yt + (yb - yt) * 0.66
        for y in range(int(yt), int(yb) + 1):
            c.set(x, y, C("341c27") if y <= b1
                  else (C("241527") if y <= b2 else C("10141f")))
        c.set(x, int(yt), C("4d2b32"))          # the door's own top edge
        c.set(x, int(yb), C("090a14"))
    # four pressed battens, uneven, each stopping at a different height
    for fr, f0, f1 in ((0.17, 0.06, 0.88), (0.36, 0.10, 0.61),
                       (0.58, 0.05, 0.93), (0.79, 0.14, 0.72)):
        bx = int(dxa + (dxb - dxa) * fr)
        yg, pm = rc_col(bx)
        yt = yg - (RC_ROOF - 0.34) * pm
        yb = yg - (RC_FLOOR + 0.12) * pm
        c.vline(bx, int(yt + (yb - yt) * f0), int(yt + (yb - yt) * f1),
                C("10141f"))
        c.vline(bx + 1, int(yt + (yb - yt) * f0),
                int(yt + (yb - yt) * (f0 + (f1 - f0) * 0.8)), C("4d2b32"))
    # one horizontal press line across it, wobbled so it is not a ruled edge
    for x in range(dxa + 2, dxb - 1):
        u = (x - dxa) / float(max(1, dxb - dxa))
        yg, pm = rc_col(x)
        yt = yg - (RC_ROOF - 0.34) * pm
        yb = yg - (RC_FLOOR + 0.12) * pm
        yc = yt + (yb - yt) * (0.46 + 0.012 * math.sin(u * 9.4))
        c.set(x, int(yc), C("10141f"))
        c.set(x, int(yc) - 1, C("4d2b32"))
    # the leading edge is a lit metal angle - bright only where the light
    # actually falls, not a rail down the whole car - and the trailing edge
    # is a recess with the door's own shadow thrown on the flank beside it
    yg, pm = rc_col(dxb)
    yt = yg - (RC_ROOF - 0.32) * pm
    yb = yg - (RC_FLOOR + 0.08) * pm
    c.vline(dxb, int(yt), int(yb), C("202e37"))
    c.vline(dxb, int(yt), int(yt + (yb - yt) * 0.34), C("394a50"))
    c.vline(dxb + 1, int(yt) + 2, int(yb) - 2, C("090a14"))
    yg, pm = rc_col(dxa)
    yt = yg - (RC_ROOF - 0.32) * pm
    yb = yg - (RC_FLOOR + 0.08) * pm
    c.vline(dxa - 1, int(yt), int(yb), C("090a14"))
    c.vline(dxa - 2, int(yt) + 1, int(yb) - 1, C("090a14"))
    c.vline(dxa - 3, int(yt) + 4, int(yb) - 3, C("10141f"))
    # the track. NOT a bright rail down the whole car - that was the
    # brightest line in the picture. dull steel, the light caught only at
    # the hangers.
    txa, txb = rc_span(14.7, 19.0)
    for x in range(txa, txb + 1):
        yg, pm = rc_col(x)
        yr = yg - (RC_ROOF - 0.24) * pm
        c.set(x, int(yr), C("202e37"))
        c.set(x, int(yr) + 1, C("090a14"))
    for fr in (0.09, 0.37, 0.79):
        hx = int(dxa + (dxb - dxa) * fr)
        yg, pm = rc_col(hx)
        yr = yg - (RC_ROOF - 0.26) * pm
        c.vline(hx, int(yr), int(yr + 0.15 * pm), C("394a50"))
        c.vline(hx + 1, int(yr) + 1, int(yr + 0.14 * pm), C("090a14"))
        c.set(hx, int(yr) - 1, C("577277"))
    # bottom guide angle
    gxa, gxb = rc_span(14.9, 18.8)
    for x in range(gxa, gxb + 1):
        yg, pm = rc_col(x)
        yb = yg - (RC_FLOOR + 0.05) * pm
        c.set(x, int(yb), C("202e37"))
        c.set(x, int(yb) + 1, C("090a14"))
    # the hasp and its padlock, on the leading edge
    hxp = dxb - 12
    hyg, hpm = rc_col(hxp)
    hy = int(hyg - (RC_FLOOR + 1.5) * hpm)
    c.rect(hxp, hy, hxp + 11, hy + 6, C("202e37"))
    c.hline(hxp, hxp + 11, hy, C("577277"))
    c.vline(hxp, hy, hy + 6, C("090a14"))
    c.hline(hxp, hxp + 11, hy + 7, C("090a14"))
    c.rect(hxp + 7, hy + 7, hxp + 11, hy + 12, C("151d28"))     # the lock
    c.hline(hxp + 7, hxp + 11, hy + 13, C("090a14"))
    c.set(hxp + 7, hy + 8, C("394a50"))
    c.set(hxp + 8, hy + 7, C("577277"))

    # --- ROOF HARDWARE: a running board with a piece torn out of it, two
    # vents of different size, and a bent grab iron at the near corner.
    for (fa, fb) in ((0.02, 0.29), (0.34, 0.63), (0.71, 0.97)):
        for x in range(int(RC_XA + (RC_XB - RC_XA) * fa),
                       int(RC_XA + (RC_XB - RC_XA) * fb)):
            yg, pm = rc_col(x)
            c.set(x, int(yg - RC_ROOF * pm) - 1, C("19332d"))
    for (d0, d1, vh_m) in ((15.4, 14.6, 0.30), (18.5, 18.1, 0.20)):
        vx0, vx1 = rc_span(d1, d0)
        for x in range(vx0, vx1 + 1):
            yg, pm = rc_col(x)
            yr = yg - RC_ROOF * pm
            c.vline(x, int(yr - vh_m * pm), int(yr), C("10141f"))
            c.set(x, int(yr - vh_m * pm), C("19332d"))
        yg, pm = rc_col(vx0)
        c.vline(vx0, int(yg - (RC_ROOF + vh_m) * pm), int(yg - RC_ROOF * pm),
                C("090a14"))
    ghx = min(RC_XB - 2, int(gxd(RC_X, 13.4)))
    gyg, gpm = rc_col(ghx)
    gyr = int(gyg - RC_ROOF * gpm)
    c.hline(ghx - 15, ghx, gyr - 9, C("394a50"))
    c.vline(ghx - 15, gyr - 9, gyr - 2, C("202e37"))
    c.vline(ghx, gyr - 8, gyr - 1, C("202e37"))
    # a chunk of the running board gone: carve the silhouette using the sky
    # that is already sitting above it, so the roofline is genuinely broken
    nxa, nxb = rc_span(16.8, 17.4)
    for x in range(nxa, nxb + 1):
        yg, pm = rc_col(x)
        yr = int(yg - RC_ROOF * pm)
        c.vline(x, yr - 1, yr + 1, c.get(x, yr - 7))

    # --- WEAR THAT DIFFERS IN KIND from the left car's rust streaks: a
    # riveted repair plate, two dents where the light break sags, and the
    # dirt tide thrown up off the wheels. (a first cut ran a long wobbled
    # crease the width of the car; it read as a cable hung on the side.)
    # (sized twice. a 45 px wide 202e37 plate read as a lit WINDOW - the
    # brightest thing on that side of the frame. it is a dark plate with a
    # lit lip now, and small.)
    pxa, pxb = rc_span(13.9, 14.55)
    for x in range(pxa, pxb + 1):
        yg, pm = rc_col(x)
        yt = yg - (RC_FLOOR + 1.82) * pm
        yb = yg - (RC_FLOOR + 1.36) * pm
        c.vline(x, int(yt), int(yb), C("10141f"))
        c.set(x, int(yt), C("394a50"))
        c.set(x, int(yb) + 1, C("090a14"))
    yg, pm = rc_col(pxa)
    c.vline(pxa, int(yg - (RC_FLOOR + 1.82) * pm),
            int(yg - (RC_FLOOR + 1.36) * pm), C("202e37"))
    yg, pm = rc_col(pxb)
    c.vline(pxb + 1, int(yg - (RC_FLOOR + 1.82) * pm) + 1,
            int(yg - (RC_FLOOR + 1.36) * pm) + 1, C("090a14"))
    # scuffs: SMALL solid wear patches, nothing more. this spot has now
    # been through three designs and the lesson is about SIZE, not shape -
    # a raised band break read as a painted arch, and a 30 px lens read as
    # a flying saucer stuck to the side of the car. at 10-18 px across the
    # same shape simply reads as wear. dep stays inside 2.2..3.6 m so every
    # one of them lands in the BODY band; a patch that lands in the shade
    # band fills with the shade's own colour and leaves only its lip
    # floating.
    for (dc, dw, dh, dep, col) in ((14.85, 0.30, 0.10, 2.46, "10141f"),
                                   (19.3, 0.26, 0.09, 2.92, "10141f"),
                                   (13.55, 0.14, 0.06, 3.16, "19332d"),
                                   (15.05, 0.20, 0.07, 3.44, "10141f")):
        cx0 = int(gxd(RC_X, dc))
        if not (RC_XA + 4 <= cx0 <= RC_XB - 4):
            continue
        yg, pm = rc_col(cx0)
        patch(cx0, int(yg - dep * pm), max(4, int(dw * pm * 0.5)),
              max(2, int(dh * pm * 0.5)), C(col))
    for x in range(RC_XA, RC_XB + 1):
        u = (x - RC_XA) / float(max(1, RC_XB - RC_XA))
        yg, pm = rc_col(x)
        yb = yg - RC_FLOOR * pm
        yt = yb - (0.30 + 0.11 * math.sin(u * 9.1) + 0.06
                   * math.sin(u * 23.0 + 2.2)) * pm
        c.vline(x, int(yt), int(yb), C("090a14"))

    # the end face: same car, different plane, one value darker, and its own
    # ribs + ladder so it reads as an end and not as wallpaper.
    rd = 13.0
    ry = gy(rd)
    rpm = ppm(ry)
    ex0 = int(gxd(9.0, rd))
    ex1 = SCENE_W - 1
    ey0 = int(ry - 4.25 * rpm)
    ey1 = int(ry - 1.15 * rpm)
    c.rect(ex0, ey0, ex1, ey1, C("10141f"))
    c.rect(ex0, ey0 + 1, ex1, ey0 + 9, C("151d28"))
    c.hline(ex0, ex1, ey0 - 1, C("394a50"))             # ONE lit edge: roof lip
    c.hline(ex0, ex1, ey0 + 10, C("090a14"))
    c.vline(ex0, ey0, ey1, C("19332d"))                 # the corner post
    c.vline(ex0 + 1, ey0 + 6, ey1 - 3, C("10141f"))
    c.rect(ex0, ey1 + 1, ex1, int(ry), C("090a14"))
    # end ribs. these used to be four at a dead 29 px pitch - a visible
    # grid, and the last of them fell off the canvas. uneven now, and each
    # runs a different length.
    for (rox, rlen) in ((33, 0.97), (52, 0.74), (76, 0.91)):
        c.vline(ex0 + rox, ey0 + 12, int(ey0 + 12 + (ey1 - ey0 - 14) * rlen),
                C("090a14"))
        c.vline(ex0 + rox + 1, ey0 + 12,
                int(ey0 + 12 + (ey1 - ey0 - 14) * rlen * 0.42), C("19332d"))
    # end ladder. it used to be pitched at 33 px and its top two rungs were
    # drawn on the SKY above the car; now it is a real 0.4 m pitch that
    # stops under the brake wheel.
    lad_x0, lad_x1 = ex0 + 6, ex0 + 22
    rung = 0.4 * rpm
    ry_b, ry_t = ey1 - 8, ey0 + 62
    k = 0
    while ry_b - k * rung > ry_t:
        yy = int(ry_b - k * rung)
        c.hline(lad_x0, lad_x1, yy, C("202e37"))
        c.hline(lad_x0, lad_x1, yy + 1, C("090a14"))
        k += 1
    c.vline(lad_x0, ry_t, ey1 - 4, C("151d28"))
    c.vline(lad_x1, ry_t, ey1 - 4, C("202e37"))
    # THE BRAKE WHEEL - a real hoop, drawn as a ring so it reads round, lit
    # on the side facing the last of the sky. this is the one shape in the
    # frame that says ROLLING STOCK at a glance, and the left car has
    # nothing like it.
    bw_x, bw_y, bw_r = ex0 + 14, ey0 + 30, 15.0
    for dy in range(-int(bw_r) - 1, int(bw_r) + 2):
        for dx in range(-int(bw_r) - 1, int(bw_r) + 2):
            rr = math.hypot(dx, dy)
            if bw_r - 2.4 <= rr <= bw_r:
                c.set(bw_x + dx, bw_y + dy,
                      C("394a50") if dx + dy < -3 else
                      (C("202e37") if dx - dy < 4 else C("151d28")))
            elif rr <= 2.6:
                c.set(bw_x + dx, bw_y + dy, C("202e37"))
    for ang in (0.35, 2.45, 4.25):                       # three spokes
        for t in range(3, int(bw_r) - 1):
            c.set(bw_x + int(math.cos(ang) * t),
                  bw_y + int(math.sin(ang) * t), C("151d28"))
    c.vline(bw_x, bw_y + 2, ey0 + 74, C("202e37"))       # the brake staff
    c.vline(bw_x + 1, bw_y + 4, ey0 + 72, C("090a14"))
    # a painted-out patch where the reporting marks were. no lettering: the
    # game's font is lowercase-only and stencilled marks would break it.
    c.rect(ex0 + 38, ey0 + 118, ex0 + 86, ey0 + 143, C("151d28"))
    c.rect(ex0 + 41, ey0 + 121, ex0 + 83, ey0 + 140, C("10141f"))
    c.hline(ex0 + 38, ex0 + 86, ey0 + 118, C("19332d"))
    c.hline(ex0 + 38, ex0 + 86, ey0 + 144, C("090a14"))
    # bogies + shadow
    for bd in (13.9, 15.4, 18.1, 19.4):
        bx = int(gxd(9.0, bd))
        byy = gy(bd)
        pm = ppm(byy)
        c.hline(bx - int(0.42 * pm), bx + int(0.42 * pm),
                int(byy - 0.6 * pm), C("151d28"))
        c.hline(bx - int(0.28 * pm), bx + int(0.28 * pm),
                int(byy - 0.59 * pm), C("10141f"))
    for x in range(int(rc[0]), SCENE_W):
        dd = 9.0 * FOCAL / (x - VPX)
        if dd <= 0:
            continue
        yg = min(gy(dd), ry)
        ln = 16 + int(0.22 * ppm(yg))
        c.vline(x, int(yg), int(yg) + ln, C("10141f"))
        c.vline(x, int(yg), int(yg) + ln // 2, C("090a14"))

    # =============================================== 10. FOREGROUND SPOIL ==
    # a stack of lifted sleepers off the right-hand shoulder, well below the
    # button band, so the right side has a foreground anchor too.
    stx, sty = 690, 486
    for k in range(5):
        w2 = 82 - k * 6 + rng.randint(-6, 6)
        off = rng.randint(-9, 9)
        y = sty - k * 9
        c.rect(stx + off, y - 7, stx + off + w2, y, C("10141f"))
        c.hline(stx + off, stx + off + w2, y - 7, C("341c27"))
        c.hline(stx + off, stx + off + w2, y, C("090a14"))
        c.vline(stx + off, y - 7, y, C("090a14"))
        c.vline(stx + off + w2, y - 6, y, C("241527"))
    c.hline(stx - 14, stx + 92, sty + 2, C("090a14"))

    # spoil heaps: solid mounds with a lit crest, one each side, both well
    # clear of the button band. no two the same shape.
    def heap(hx, hy, hw, hh, base, mid, crest):
        for dx in range(-hw, hw + 1):
            t = 1.0 - (dx / float(hw)) ** 2
            top = int(hy - hh * (t ** 0.7) * (0.86 + 0.14 * math.sin(dx * 0.21)))
            c.vline(hx + dx, top, hy, C(base))
            c.vline(hx + dx, top, top + max(1, int(hh * 0.22)), C(mid))
            c.set(hx + dx, top, C(crest))
        c.hline(hx - hw, hx + hw, hy + 1, C("090a14"))

    heap(96, 508, 74, 30, "10141f", "151d28", "202e37")
    heap(884, 470, 62, 24, "10141f", "151d28", "202e37")
    heap(806, 524, 46, 15, "151d28", "202e37", "394a50")

    # standing water: the rain has already been through once. all outside
    # the band, all different shapes.
    for (px, py, pw, ph) in ((624, 432, 26, 5), (168, 466, 17, 4),
                             (886, 424, 21, 4), (352, 486, 14, 3),
                             (742, 402, 12, 3)):
        patch(px, py, pw, ph, C("172038"))
        patch(px + 2, py - 1, int(pw * 0.6), max(1, ph - 2), C("253a5e"))
        c.hline(px - pw // 2, px + pw // 4, py + ph, C("10141f"))

    # a discarded rail chair between the rails, and a length of lifted rail
    cxr, cyr = 430, 512
    c.rect(cxr, cyr, cxr + 21, cyr + 11, C("202e37"))
    c.rect(cxr + 2, cyr - 4, cxr + 12, cyr, C("394a50"))
    c.hline(cxr + 2, cxr + 12, cyr - 4, C("577277"))
    c.hline(cxr, cxr + 21, cyr + 12, C("090a14"))
    c.vline(cxr + 21, cyr + 1, cyr + 11, C("151d28"))
    for k in range(84):                       # the lifted rail, lying askew
        x = 496 + k
        y = 531 - int(k * 0.10)
        c.vline(x, y, y + 4, C("202e37"))
        c.set(x, y, C("819796"))
        c.set(x, y + 1, C("577277"))
        c.set(x, y + 5, C("090a14"))
    c.rect(494, 524, 500, 537, C("394a50"))
    c.hline(494, 500, 524, C("577277"))

    # weeds: solid tufts, thinning toward the middle of the frame, and never
    # inside the button band.
    # real clumps, not scattered blades: a few big ones near the camera and
    # along the left shoulder, thinning to nothing across the open middle.
    def tuft(wx, wy, scale):
        pm = ppm(wy)
        hgt = max(3, int(rng.uniform(0.16, 0.34) * pm * scale))
        if hgt > 42:
            hgt = 42
        blades = rng.randint(7, 15)
        spread = max(3, int(hgt * rng.uniform(0.5, 0.9)))
        for b in range(blades):
            bx = wx + rng.randint(-spread, spread)
            bh = int(hgt * rng.uniform(0.35, 1.0))
            lean = rng.randint(-3, 3)
            col = C("19332d") if rng.random() < 0.7 else C("241527")
            for k in range(bh):
                c.set(bx + int(lean * k / max(1, bh)), wy - k, col)
            c.set(bx + lean, wy - bh, C("25562e") if rng.random() < 0.4
                  else C("19332d"))
        c.hline(wx - spread, wx + spread, wy + 1, C("090a14"))

    placed = 0
    tries = 0
    while placed < 30 and tries < 900:
        tries += 1
        wy = HZI + 30 + int((SCENE_H - HZI - 34) * (rng.random() ** 0.55))
        wx = rng.randrange(4, SCENE_W - 6)
        if in_band(wx, wy, 26):
            continue
        # the open middle of the yard is kept bare; the shoulders are not
        openness = 1.0 - min(1.0, abs(wx - 500) / 320.0)
        if rng.random() < openness * 0.85:
            continue
        tuft(wx, wy, rng.uniform(0.7, 1.3))
        placed += 1
    for wy in (498, 522, 540, 466, 512):        # in the four-foot, near
        wx = rng.randrange(160, 440)
        if not in_band(wx, wy, 20):
            tuft(wx, wy, rng.uniform(0.4, 0.8))

    return c


if __name__ == "__main__":
    paint().img.save(sys.argv[1])
