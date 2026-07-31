#!/usr/bin/env python3
"""SPOILS art pipeline. Generates every game asset into art/gen/ from the Apollo
palette. Deterministic: same script -> same pixels. If an asset looks bad, fix
this file and rerun; never hand-edit outputs.

Outputs:
  art/gen/floors.png    - 64x32 iso floor tiles, 4x4 atlas grid
  art/gen/<prop>.png    - individual prop sprites (walls, crates, barrels, ...)
  art/gen/char.png      - player sheet, 8 dirs x 5 frames (idle + 4 walk), 32x40
  art/gen/shadow.png    - blob shadow (palette color + alpha)
  art/gen/manifest.json - sizes/origins/atlas coords consumed by the game
  art/gen/preview.png   - 3x contact sheet for visual review (not used in-game)
"""
import json
import random
from pathlib import Path

from PIL import Image

SEED = "spoils-m1"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art" / "gen"

# ---------------------------------------------------------------- palette ----

def load_palette() -> dict[str, tuple[int, int, int, int]]:
    pal: dict[str, tuple[int, int, int, int]] = {}
    for line in (ROOT / "art" / "palettes" / "apollo.gpl").read_text().splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0].isdigit():
            r, g, b, name = parts
            pal[name] = (int(r), int(g), int(b), 255)
    assert len(pal) == 46, f"expected 46 Apollo colors, got {len(pal)}"
    return pal

PAL = load_palette()
PAL_RGB = {v[:3] for v in PAL.values()}

def C(name: str) -> tuple[int, int, int, int]:
    return PAL[name]

OUTLINE = C("090a14")
INK = C("10141f")

# ------------------------------------------------------------- primitives ----

class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.img.load()

    def set(self, x: int, y: int, c) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = c

    def get(self, x: int, y: int):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[x, y]
        return (0, 0, 0, 0)

    def rect(self, x0: int, y0: int, x1: int, y1: int, c) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, c)

    def hline(self, x0: int, x1: int, y: int, c) -> None:
        self.rect(x0, y, x1, y, c)

    def vline(self, x: int, y0: int, y1: int, c) -> None:
        self.rect(x, y0, x, y1, c)

    def outline_auto(self, c=OUTLINE) -> None:
        """1px outline: paint transparent pixels that touch an opaque one."""
        opaque = {(x, y) for y in range(self.h) for x in range(self.w)
                  if self.px[x, y][3] > 0}
        for (x, y) in list(opaque):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) not in opaque:
                    self.set(nx, ny, c)

    def mirrored(self) -> "Canvas":
        m = Canvas(self.w, self.h)
        m.img = self.img.transpose(Image.FLIP_LEFT_RIGHT)
        m.px = m.img.load()
        return m

# ------------------------------------------------------------ iso diamond ----
# 64x32 diamond that tessellates exactly under the (+-32,+-16) tile lattice.
# Top half rows y=0..15 span [30-2y, 33+2y]; bottom rows y=16..31 shrink again.

def diamond_span(y: int) -> tuple[int, int] | None:
    if 0 <= y <= 15:
        return 30 - 2 * y, 33 + 2 * y
    if 16 <= y <= 31:
        j = y - 16
        if 2 + 2 * j > 61 - 2 * j:
            return None
        return 2 + 2 * j, 61 - 2 * j
    return None

def in_diamond(x: int, y: int) -> bool:
    s = diamond_span(y)
    return s is not None and s[0] <= x <= s[1]

def check_tessellation() -> None:
    counts: dict[tuple[int, int], int] = {}
    # valid iso lattice offsets are a*(32,16) + b*(32,-16)
    for a in range(-2, 3):
        for b in range(-2, 3):
            ox, oy = 32 * (a + b), 16 * (a - b)
            for y in range(32):
                s = diamond_span(y)
                if s is None:
                    continue
                for x in range(s[0], s[1] + 1):
                    p = (x + ox, y + oy)
                    if 0 <= p[0] < 64 and 0 <= p[1] < 32:
                        counts[p] = counts.get(p, 0) + 1
    assert all(v == 1 for v in counts.values()) and len(counts) == 64 * 32, \
        "iso diamond does not tessellate"

# Per-column bottommost diamond row (for extruding wall/crate side faces).
def diamond_bottom_y(x: int) -> int:
    best = -1
    for y in range(32):
        if in_diamond(x, y):
            best = y
    return best

# --------------------------------------------------------------- floors ------

CONC_D2, CONC_D1, CONC_BASE, CONC_L1, CONC_L2 = (
    C("151d28"), C("202e37"), C("394a50"), C("577277"), C("819796"))

def speckle(c: Canvas, rng: random.Random, region, colors: list[tuple], probs: list[float]) -> None:
    for (x, y) in region:
        r = rng.random()
        acc = 0.0
        for col, p in zip(colors, probs):
            acc += p
            if r < acc:
                c.set(x, y, col)
                break

def blob(rng: random.Random, cx: int, cy: int, n: int, region: set) -> set:
    """Random-walk blob of ~n pixels constrained to region."""
    out = set()
    x, y = cx, cy
    for _ in range(n * 3):
        if (x, y) in region:
            out.add((x, y))
        if len(out) >= n:
            break
        x += rng.choice((-1, -1, 0, 1, 1))
        y += rng.choice((-1, 0, 0, 1))
        if (x, y) not in region:
            x, y = cx + rng.randint(-3, 3), cy + rng.randint(-2, 2)
    return out

def crack(c: Canvas, rng: random.Random, region: set, col, steps: int) -> None:
    pts = list(region)
    x, y = pts[rng.randrange(len(pts))]
    dx = rng.choice((-1, 1))
    for _ in range(steps):
        if (x, y) in region:
            c.set(x, y, col)
        x += dx if rng.random() < 0.8 else -dx
        y += rng.choice((0, 0, 1, 1, -1))

def make_floor_tile(kind: str, variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:floor:{kind}:{variant}")
    c = Canvas(64, 32)
    region = {(x, y) for y in range(32) for x in range(64) if in_diamond(x, y)}

    if kind in ("concrete", "concrete_cracked", "moss"):
        for (x, y) in region:
            c.set(x, y, CONC_BASE)
        speckle(c, rng, region, [CONC_D1, CONC_L1], [0.07, 0.035])
        if variant >= 1:
            patch = blob(rng, 32 + rng.randint(-12, 12), 16 + rng.randint(-5, 5),
                         rng.randint(30, 70), region)
            for (x, y) in patch:
                c.set(x, y, CONC_L1 if (x + y) % 2 == 0 else CONC_BASE)
        # slab joints: subtle dithered dark line on the lower-right edges only
        for (x, y) in region:
            if (not in_diamond(x + 2, y + 1) or not in_diamond(x - 2, y + 1)) and x % 2 == 0:
                c.set(x, y, CONC_D1)
        if kind == "concrete_cracked":
            for _ in range(rng.randint(1, 2)):
                crack(c, rng, region, CONC_D2, rng.randint(10, 18))
            hole = blob(rng, 32 + rng.randint(-10, 10), 16 + rng.randint(-4, 4),
                        rng.randint(8, 16), region)
            for (x, y) in hole:
                c.set(x, y, CONC_D2)
            for (x, y) in list(hole)[:4]:
                c.set(x, y, OUTLINE)
        if kind == "moss":
            m = blob(rng, 32 + rng.randint(-14, 14), 16 + rng.randint(-6, 6),
                     rng.randint(40, 80), region)
            for (x, y) in m:
                c.set(x, y, C("19332d") if (x * 3 + y) % 3 else C("25562e"))

    elif kind == "asphalt":
        for (x, y) in region:
            c.set(x, y, CONC_D1)
        speckle(c, rng, region, [CONC_D2, CONC_BASE], [0.10, 0.04])
        if variant == 1:
            tar = blob(rng, 32 + rng.randint(-12, 12), 16 + rng.randint(-5, 5),
                       rng.randint(20, 45), region)
            for (x, y) in tar:
                c.set(x, y, CONC_D2)
        if variant == 2:  # worn lane paint dashes along the tile diagonal
            for (x, y) in region:
                if abs((x - 32) * 0.5 + (y - 16)) < 1.5 and (x // 10) % 2 == 0 and rng.random() < 0.92:
                    c.set(x, y, C("de9e41"))

    elif kind == "dirt":
        base, dark, lite = C("4d2b32"), C("341c27"), C("7a4841")
        for (x, y) in region:
            c.set(x, y, base)
        speckle(c, rng, region, [dark, lite, CONC_BASE], [0.12, 0.07, 0.02])
        if variant == 1:  # rubble-strewn dirt
            for _ in range(rng.randint(4, 7)):
                bx, by = 6 + rng.randrange(52), 4 + rng.randrange(24)
                for (x, y) in blob(rng, bx, by, rng.randint(3, 6), region):
                    c.set(x, y, CONC_BASE if rng.random() < 0.7 else CONC_L1)
    else:
        raise ValueError(kind)
    return c

FLOOR_TILES = [  # name -> atlas coords, laid out in listed order (4 columns)
    ("concrete_a", ("concrete", 0)),
    ("concrete_b", ("concrete", 1)),
    ("concrete_c", ("concrete", 2)),
    ("concrete_cracked_a", ("concrete_cracked", 0)),
    ("concrete_cracked_b", ("concrete_cracked", 1)),
    ("asphalt_a", ("asphalt", 0)),
    ("asphalt_b", ("asphalt", 1)),
    ("asphalt_line", ("asphalt", 2)),
    ("dirt_a", ("dirt", 0)),
    ("dirt_b", ("dirt", 1)),
    ("moss_a", ("moss", 0)),
    ("moss_b", ("moss", 1)),
]

def make_floors_atlas() -> tuple[Image.Image, dict[str, list[int]]]:
    cols = 4
    rows = (len(FLOOR_TILES) + cols - 1) // cols
    atlas = Image.new("RGBA", (cols * 64, rows * 32), (0, 0, 0, 0))
    coords: dict[str, list[int]] = {}
    for i, (name, (kind, variant)) in enumerate(FLOOR_TILES):
        cx, cy = i % cols, i // cols
        atlas.paste(make_floor_tile(kind, variant).img, (cx * 64, cy * 32))
        coords[name] = [cx, cy]
    return atlas, coords

# ---------------------------------------------------------------- walls ------
# Wall block: 64x32 footprint extruded up. Canvas 64x(32+H). Overcast top light:
# top face lightest, SW (left) face mid, SE (right) face darkest.

WALL_H = 40

def make_wall(kind: str, variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:wall:{kind}:{variant}")
    H = WALL_H
    c = Canvas(64, 32 + H)

    if kind in ("full", "window"):
        heights = [H] * 64
    else:  # broken: chunky jagged top, varies per column in steps
        heights = []
        h = rng.randint(10, 22)
        for x in range(64):
            if x % rng.choice((3, 4, 5)) == 0:
                h = max(6, min(26, h + rng.choice((-6, -4, 4, 6))))
            heights.append(h)

    # side faces, column by column
    for x in range(64):
        by = diamond_bottom_y(x)  # bottom edge row of the footprint diamond
        h = heights[x]
        top_edge = (H - h) + by
        face = C("394a50") if x < 32 else C("202e37")
        for y in range(top_edge + 1, H + by + 1):
            c.set(x, y, face)

    if kind in ("full", "window"):
        # flat top face: the diamond, raised by H
        for y in range(32):
            s = diamond_span(y)
            if s:
                for x in range(s[0], s[1] + 1):
                    c.set(x, y, C("577277"))
        # light edge where top meets faces (dithered so wall runs don't stripe)
        for x in range(64):
            if x % 2 == 0:
                c.set(x, diamond_bottom_y(x) + 1, C("819796"))
    else:
        # jagged cap: light rubble lip along the varying top
        for x in range(64):
            ty = (H - heights[x]) + diamond_bottom_y(x) + 1
            c.set(x, ty, C("819796") if rng.random() < 0.6 else C("577277"))
            if rng.random() < 0.3:
                c.set(x, ty + 1, C("577277"))

    # face texture: speckle + cracks + pocks
    for x in range(64):
        by = diamond_bottom_y(x)
        for y in range((H - heights[x]) + by + 2, H + by + 1):
            r = rng.random()
            base = C("394a50") if x < 32 else C("202e37")
            if r < 0.06:
                c.set(x, y, C("202e37") if x < 32 else C("151d28"))
            elif r < 0.09:
                c.set(x, y, C("577277") if x < 32 else C("394a50"))
            elif r < 0.10 and kind == "full":
                c.set(x, y, base)
    if kind == "full" and variant == 1:
        for x in range(10, 54, 9):  # streak stains under the cap
            stain = C("202e37") if x < 32 else C("151d28")
            for y in range(diamond_bottom_y(x) + 2, diamond_bottom_y(x) + 2 + rng.randint(4, 12)):
                c.set(x, y, stain)
    if kind == "window":
        # dark window hole sheared along each face
        for wx in (8, 40):
            for x in range(wx, wx + 9):
                ft = diamond_bottom_y(x) + 2  # face top for this column
                for y in range(ft + 6, ft + 18):
                    c.set(x, y, C("090a14"))
                c.set(x, ft + 18, C("577277"))  # sill

    # bullet pocks (clamped to the actual face span per column)
    for _ in range(rng.randint(2, 5)):
        x = rng.randrange(4, 60)
        by = diamond_bottom_y(x)
        top_edge = (H - heights[x]) + by
        lo, hi = top_edge + 4, H + by - 2
        if lo >= hi:
            continue
        y = rng.randint(lo, hi)
        c.set(x, y, C("151d28"))
        c.set(x + 1, y, C("577277"))

    # front vertical edge (where the two faces meet at the bottom vertex)
    bvy = 31  # bottom vertex around x=30..33
    for y in range((H - min(heights[30:34])) + bvy, H + bvy + 1):
        c.set(31, y, C("151d28"))
        c.set(32, y, C("151d28"))

    c.outline_auto()
    return c

# ---------------------------------------------------------------- props ------

def small_diamond_rows(w: int, d: int) -> list[tuple[int, int]]:
    """Row spans (x0,x1) of a w x d iso diamond (d even, w = 2*d so every
    column is covered and the two middle rows reach full width)."""
    assert d % 2 == 0 and w == 2 * d, "iso diamond needs w == 2*d, d even"
    rows: list[tuple[int, int]] = []
    for i in range(d):
        k = i + 1 if i < d // 2 else d - i
        half = 2 * k
        rows.append((w // 2 - half, w // 2 + half - 1))
    return rows

def iso_prism(c: Canvas, ox: int, oy: int, w: int, d: int, h: int,
              top, left, right) -> list[int]:
    """Iso box at (ox,oy) = top-left of the top-face diamond. Returns the
    per-column bottom row of the top face (for drawing sheared details)."""
    rows = small_diamond_rows(w, d)
    bottoms = [0] * w
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            c.set(ox + x, oy + i, top)
            bottoms[x] = i
    for x in range(w):
        b = oy + bottoms[x]
        for y in range(b + 1, b + h + 1):
            c.set(ox + x, y, left if x < w // 2 else right)
    return [oy + b for b in bottoms]

def make_crate(style: str) -> Canvas:
    rng = random.Random(f"{SEED}:crate:{style}")
    W, D, H = 28, 14, 12
    c = Canvas(32, 30)
    if style == "wood":
        top, left, right, line = C("be772b"), C("884b2b"), C("602c2c"), C("341c27")
        top_l = C("de9e41")
    else:  # military olive
        top, left, right, line = C("468232"), C("25562e"), C("19332d"), C("10141f")
        top_l = C("75a743")
    ox, oy = 2, 1
    bottoms = iso_prism(c, ox, oy, W, D, H, top, left, right)
    # top face edge light + plank split across the top
    for x in range(W):
        y = bottoms[x] - (0 if x % 2 else 1)
        if c.get(ox + x, y)[3] > 0:
            c.set(ox + x, y, top_l)
    # plank seams sheared along both side faces
    for x in range(W):
        c.set(ox + x, bottoms[x] + 4, line)
        c.set(ox + x, bottoms[x] + 8, line)
    # vertical center seam down the front edge
    for y in range(bottoms[W // 2] + 1, bottoms[W // 2] + H + 1):
        c.set(ox + W // 2 - 1, y, line)
        c.set(ox + W // 2, y, line)
    if style == "wood":
        for dx in (-10, -4, 5, 10):  # nail glints on the faces
            c.set(ox + W // 2 + dx, bottoms[W // 2 + dx] + 2, C("de9e41"))
    else:
        for dx in range(-6, 0, 2):  # stencil dashes on the left face
            c.set(ox + W // 2 + dx, bottoms[W // 2 + dx] + 6, C("75a743"))
    c.outline_auto()
    return c

def make_barrel(style: str) -> Canvas:
    rng = random.Random(f"{SEED}:barrel:{style}")
    c = Canvas(22, 32)
    if style == "rust":
        body, lite, dark, lid = C("602c2c"), C("884b2b"), C("341c27"), C("394a50")
        fleck = C("cf573c")
    else:
        body, lite, dark, lid = C("25562e"), C("468232"), C("19332d"), C("394a50")
        fleck = C("577277")
    cx = 11
    # body: rounded cylinder, rows 6..29
    for y in range(6, 30):
        half = 9 if 8 <= y <= 27 else 8
        for x in range(cx - half, cx + half):
            t = (x - (cx - half)) / (2 * half)
            col = lite if t < 0.35 else (body if t < 0.8 else dark)
            c.set(x, y, col)
    # lid ellipse, light rim on top
    lid_half = {3: 5, 4: 8, 5: 9, 6: 9, 7: 8, 8: 6}
    for y, half in lid_half.items():
        for x in range(cx - half, cx + half):
            c.set(x, y, C("577277") if y <= 4 else lid)
    # hoops
    for hy in (12, 21):
        for x in range(cx - 9, cx + 9):
            c.set(x, hy, dark)
            c.set(x, hy - 1, C("819796") if style != "rust" else C("ad7757"))
    for _ in range(10):
        c.set(rng.randrange(cx - 8, cx + 8), rng.randrange(9, 29), fleck)
    c.outline_auto()
    return c

def make_rubble(variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:rubble:{variant}")
    c = Canvas(48, 26)
    grays = [C("202e37"), C("394a50"), C("577277"), C("819796")]
    # mound silhouette
    for x in range(4, 44):
        h = int(9 * (1 - ((x - 24) / 22) ** 2)) + rng.randint(-1, 1)
        for y in range(c.h - 3 - max(0, h), c.h - 2):
            t = rng.random()
            c.set(x, y, grays[1] if t < 0.5 else (grays[0] if t < 0.8 else grays[2]))
    # chunk highlights
    for _ in range(rng.randint(8, 12)):
        x, y = rng.randrange(8, 40), rng.randrange(c.h - 11, c.h - 3)
        c.set(x, y, grays[3])
        c.set(x + 1, y, grays[2])
        c.set(x, y + 1, grays[1])
    # rebar sticking out
    for _ in range(2 if variant == 0 else 3):
        x = rng.randrange(10, 38)
        y = c.h - 4 - rng.randrange(5, 9)
        for i in range(rng.randint(4, 7)):
            c.set(x + i, y - i // 2, C("602c2c"))
    c.outline_auto()
    return c

def make_pillar() -> Canvas:
    rng = random.Random(f"{SEED}:pillar")
    c = Canvas(18, 54)
    for y in range(6, 50):
        for x in range(4, 14):
            col = C("577277") if x < 8 else (C("394a50") if x < 12 else C("202e37"))
            if rng.random() < 0.08:
                col = C("202e37")
            c.set(x, y, col)
    # jagged top
    cuts = {}
    for x in range(4, 14):
        cut = rng.randint(0, 5)
        cuts[x] = cut
        for y in range(6, 6 + cut):
            c.set(x, y, (0, 0, 0, 0))
        c.set(x, 6 + cut, C("819796"))
    # exposed rebar poking up from the break, anchored to the surface
    for rx in (8, 11):
        top = 6 + cuts.get(rx, 0)
        for y in range(top - 3, top + 1):
            c.set(rx, y, C("602c2c"))
    # base plinth
    for y in range(48, 52):
        for x in range(2, 16):
            c.set(x, y, C("394a50") if x < 9 else C("202e37"))
    c.outline_auto()
    return c

def make_shadow() -> Canvas:
    c = Canvas(24, 12)
    r, g, b, _ = C("090a14")
    for y in range(12):
        for x in range(24):
            dx, dy = (x - 11.5) / 11.5, (y - 5.5) / 5.5
            d = dx * dx + dy * dy
            if d < 1.0:
                a = 90 if d < 0.55 else 55
                c.set(x, y, (r, g, b, a))
    return c

# ------------------------------------------------------------- character -----
# 32x40 frames, feet baseline y=37, center x=16. Rows in dir order
# E, SE, S, SW, W, NW, N, NE (index = round(atan2(vy,vx)/45deg) mod 8,
# +y = screen down). W/SW/NW are mirrors of E/SE/NE.

SKIN, SKIN_SH = C("d7b594"), C("c09473")
JKT_L, JKT, JKT_D = C("468232"), C("25562e"), C("19332d")
PANT, PANT_D = C("202e37"), C("151d28")
BOOT, BOOT_D = C("341c27"), C("10141f")
BEANIE, BEANIE_D = C("394a50"), C("202e37")
PACK, PACK_D = C("7a4841"), C("4d2b32")
STRAP = C("341c27")

CX, FEET = 16, 37

def draw_head(c: Canvas, view: str, bob: int) -> None:
    y0 = 10 + bob
    if view == "front":       # S
        c.rect(CX - 4, y0, CX + 3, y0 + 3, BEANIE)
        c.hline(CX - 4, CX + 3, y0 + 3, BEANIE_D)
        c.rect(CX - 4, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.vline(CX + 3, y0 + 4, y0 + 7, SKIN_SH)
        c.hline(CX - 4, CX + 3, y0 + 7, SKIN_SH)
        c.set(CX - 2, y0 + 5, OUTLINE)
        c.set(CX + 1, y0 + 5, OUTLINE)
    elif view == "front34":   # SE
        c.rect(CX - 3, y0, CX + 4, y0 + 3, BEANIE)
        c.hline(CX - 3, CX + 4, y0 + 3, BEANIE_D)
        c.rect(CX - 3, y0 + 4, CX + 4, y0 + 7, SKIN)
        c.vline(CX - 3, y0 + 4, y0 + 7, SKIN_SH)
        c.hline(CX - 3, CX + 4, y0 + 7, SKIN_SH)
        c.set(CX, y0 + 5, OUTLINE)
        c.set(CX + 3, y0 + 5, OUTLINE)
    elif view == "side":      # E
        c.rect(CX - 3, y0, CX + 3, y0 + 3, BEANIE)
        c.hline(CX - 3, CX + 3, y0 + 3, BEANIE_D)
        c.rect(CX - 3, y0 + 4, CX - 1, y0 + 7, SKIN_SH)  # back of head/neck
        c.rect(CX, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.set(CX + 4, y0 + 5, SKIN)                       # nose
        c.set(CX + 4, y0 + 6, SKIN_SH)
        c.set(CX + 2, y0 + 5, OUTLINE)
        c.hline(CX - 3, CX + 3, y0 + 7, SKIN_SH)
    elif view == "back34":    # NE
        c.rect(CX - 3, y0, CX + 4, y0 + 4, BEANIE)
        c.hline(CX - 3, CX + 4, y0 + 4, BEANIE_D)
        c.rect(CX - 3, y0 + 5, CX + 4, y0 + 7, BEANIE_D)
        c.set(CX + 4, y0 + 6, SKIN_SH)                    # ear sliver
    elif view == "back":      # N
        c.rect(CX - 4, y0, CX + 3, y0 + 4, BEANIE)
        c.hline(CX - 4, CX + 3, y0 + 4, BEANIE_D)
        c.rect(CX - 4, y0 + 5, CX + 3, y0 + 7, BEANIE_D)
        c.rect(CX - 2, y0 + 7, CX + 1, y0 + 7, SKIN_SH)   # neck

def draw_torso(c: Canvas, view: str, bob: int) -> None:
    y0, y1 = 18 + bob, 27 + bob
    if view in ("front", "back"):
        x0, x1 = CX - 4, CX + 3
    else:
        x0, x1 = CX - 4, CX + 3
    c.rect(x0, y0, x1, y1, JKT)
    c.hline(x0, x1, y0, JKT_L)                 # top light
    c.vline(x1, y0 + 1, y1, JKT_D)             # away-from-light side
    c.hline(x0, x1, y1, JKT_D)                 # hem
    if view == "front":
        c.vline(CX, y0 + 1, y1, INK)           # zip
        c.vline(CX - 3, y0, y0 + 4, STRAP)     # harness straps
        c.vline(CX + 2, y0, y0 + 4, STRAP)
    if view == "front34":
        c.vline(CX + 1, y0 + 1, y1, INK)
        c.vline(CX - 2, y0, y0 + 4, STRAP)
    if view == "side":
        c.vline(CX + 3, y0 + 1, y1 - 1, JKT_D)
    # hips
    c.rect(CX - 4, y1 + 1, CX + 3, y1 + 2, PANT)
    c.hline(CX - 4, CX + 3, y1 + 2, PANT_D)

def draw_pack(c: Canvas, view: str, bob: int) -> None:
    y0 = 19 + bob
    if view == "back":
        c.rect(CX - 3, y0, CX + 2, y0 + 8, PACK)
        c.rect(CX - 3, y0 + 6, CX + 2, y0 + 8, PACK_D)
        c.hline(CX - 3, CX + 2, y0, C("ad7757"))
        c.vline(CX, y0, y0 + 8, PACK_D)        # cinch strap
    elif view == "back34":
        c.rect(CX - 4, y0, CX + 1, y0 + 8, PACK)
        c.rect(CX - 4, y0 + 6, CX + 1, y0 + 8, PACK_D)
        c.hline(CX - 4, CX + 1, y0, C("ad7757"))
    elif view == "side":                        # bulge behind the back (=-x)
        c.rect(CX - 6, y0 + 1, CX - 4, y0 + 7, PACK)
        c.vline(CX - 6, y0 + 1, y0 + 7, PACK_D)

def draw_arms(c: Canvas, view: str, bob: int, swing: int) -> None:
    y0 = 19 + bob
    if view in ("front", "back"):
        for side, sw in ((-1, swing), (1, -swing)):
            x = CX + (side * 6) - (1 if side < 0 else 0)
            yy = y0 + (1 if sw > 0 else 0)
            c.rect(x, yy, x + 1, yy + 8, JKT if side < 0 else JKT_D)
            c.rect(x, yy + 9, x + 1, yy + 10, SKIN if view == "front" else SKIN_SH)
    elif view in ("front34", "back34"):
        for side, sw in ((-1, swing), (1, -swing)):
            x = CX + (5 * side) + (0 if side < 0 else -1) + sw
            c.rect(x, y0, x + 1, y0 + 8, JKT if side < 0 else JKT_D)
            c.rect(x, y0 + 9, x + 1, y0 + 10, SKIN)
    else:  # side: near arm only, swings along facing (+x)
        x = CX + 1 + swing
        c.rect(x, y0, x + 1, y0 + 8, JKT_D)
        c.rect(x, y0 + 9, x + 1, y0 + 10, SKIN)

def draw_legs(c: Canvas, view: str, frame: int) -> None:
    """frame 0=idle, 1..4 walk (1/3 contact poses, 2/4 passing)."""
    if view in ("front", "front34", "back", "back34"):
        lx, rx = CX - 4, CX + 1
        if frame == 0:
            for x0 in (lx, rx):
                c.rect(x0, 28, x0 + 2, 33, PANT if x0 == lx else PANT_D)
                c.rect(x0, 34, x0 + 2, 36, BOOT)
                c.hline(x0, x0 + 2, FEET, BOOT_D)
        else:
            lead = 1 if frame in (1, 2) else -1
            up = 0 if frame in (1, 3) else 1
            for x0, s in ((lx, lead), (rx, -lead)):
                lift = 2 if s > 0 else 0
                dy = -lift
                c.rect(x0, 28, x0 + 2, 33 + dy, PANT if x0 == lx else PANT_D)
                c.rect(x0, 34 + dy, x0 + 2, 36 + dy, BOOT)
                c.hline(x0, x0 + 2, FEET + dy, BOOT_D)
    else:  # side view: scissor stride toward +x
        spread = {0: 0, 1: 3, 2: 1, 3: 3, 4: 1}[frame]
        flip = -1 if frame == 3 else 1
        front_dx, back_dx = spread * flip, -spread * flip
        # back leg first (darker)
        for dx, pcol, bcol in ((back_dx, PANT_D, BOOT), (front_dx, PANT, BOOT)):
            x0 = CX - 1 + dx
            lift = 1 if (frame in (2, 4)) else 0
            c.rect(x0, 28, x0 + 2, 33 - lift, pcol)
            c.rect(x0, 34 - lift, x0 + 2, 36 - lift, bcol)
            c.hline(x0, x0 + 3 if dx >= 0 else x0 + 2, FEET - lift, BOOT_D)

def draw_char_frame(view: str, frame: int) -> Canvas:
    c = Canvas(32, 40)
    bob = -1 if frame in (2, 4) else 0
    swing = {0: 0, 1: 1, 2: 0, 3: -1, 4: 0}[frame]
    if view in ("back", "back34"):
        draw_legs(c, view, frame)
        draw_torso(c, view, bob)
        draw_arms(c, view, bob, swing)
        draw_pack(c, view, bob)
        draw_head(c, view, bob)
    elif view == "side":
        draw_pack(c, view, bob)
        draw_legs(c, view, frame)
        draw_torso(c, view, bob)
        draw_arms(c, view, bob, swing * 2)
        draw_head(c, view, bob)
    else:
        draw_legs(c, view, frame)
        draw_torso(c, view, bob)
        draw_arms(c, view, bob, swing)
        draw_head(c, view, bob)
    c.outline_auto()
    return c

DIR_VIEWS = [  # (row, view, mirrored)
    ("E", "side", False), ("SE", "front34", False), ("S", "front", False),
    ("SW", "front34", True), ("W", "side", True), ("NW", "back34", True),
    ("N", "back", False), ("NE", "back34", False),
]

def make_char_sheet() -> Image.Image:
    sheet = Image.new("RGBA", (5 * 32, 8 * 40), (0, 0, 0, 0))
    for row, (_, view, mirrored) in enumerate(DIR_VIEWS):
        for frame in range(5):
            fc = draw_char_frame(view, frame)
            if mirrored:
                fc = fc.mirrored()
            sheet.paste(fc.img, (frame * 32, row * 40))
    return sheet

# ---------------------------------------------------------------- output -----

def assert_palette(img: Image.Image, name: str) -> None:
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            p = px[x, y]
            if p[3] > 0 and p[:3] not in PAL_RGB:
                raise AssertionError(f"{name}: non-palette pixel {p} at {x},{y}")

def main() -> None:
    check_tessellation()
    OUT.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"tile": [64, 32], "floors": {}, "props": {}, "char": {}}

    floors, coords = make_floors_atlas()
    assert_palette(floors, "floors")
    floors.save(OUT / "floors.png")
    manifest["floors"] = coords

    props: dict[str, tuple[Canvas, tuple[int, int]]] = {
        # name: (canvas, origin) — origin = ground-contact center in canvas px
        "wall_a": (make_wall("full", 0), (32, WALL_H + 16)),
        "wall_b": (make_wall("full", 1), (32, WALL_H + 16)),
        "wall_window": (make_wall("window", 0), (32, WALL_H + 16)),
        "wall_broken_a": (make_wall("broken", 0), (32, WALL_H + 16)),
        "wall_broken_b": (make_wall("broken", 1), (32, WALL_H + 16)),
        "crate_wood": (make_crate("wood"), (16, 20)),
        "crate_mil": (make_crate("mil"), (16, 20)),
        "barrel_rust": (make_barrel("rust"), (11, 27)),
        "barrel_olive": (make_barrel("olive"), (11, 27)),
        "rubble_a": (make_rubble(0), (24, 20)),
        "rubble_b": (make_rubble(1), (24, 20)),
        "pillar": (make_pillar(), (9, 50)),
        "shadow": (make_shadow(), (12, 6)),
    }
    for name, (canvas, origin) in props.items():
        if name != "shadow":
            assert_palette(canvas.img, name)
        canvas.img.save(OUT / f"{name}.png")
        manifest["props"][name] = {"size": [canvas.w, canvas.h], "origin": list(origin)}

    sheet = make_char_sheet()
    assert_palette(sheet, "char")
    sheet.save(OUT / "char.png")
    manifest["char"] = {
        "frame": [32, 40], "cols": 5, "origin": [16, 37],
        "dirs": [d for d, _, _ in DIR_VIEWS],
    }

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # ---- 3x contact sheet for human/Claude review ----
    def x3(img: Image.Image) -> Image.Image:
        return img.resize((img.width * 3, img.height * 3), Image.NEAREST)

    pad = 12
    row1 = x3(floors)
    prop_imgs = [x3(cv.img) for n, (cv, _) in props.items()]
    row2_w = sum(i.width + pad for i in prop_imgs)
    row2_h = max(i.height for i in prop_imgs)
    row3 = x3(sheet)
    W = max(row1.width, row2_w, row3.width) + pad * 2
    Hh = row1.height + row2_h + row3.height + pad * 4
    prev = Image.new("RGBA", (W, Hh), C("151d28"))
    prev.paste(row1, (pad, pad), row1)
    xcur = pad
    for i in prop_imgs:
        prev.paste(i, (xcur, pad * 2 + row1.height + (row2_h - i.height)), i)
        xcur += i.width + pad
    prev.paste(row3, (pad, pad * 3 + row1.height + row2_h), row3)
    prev.save(OUT / "preview.png")

    print(f"OK: wrote {len(props) + 3} files to {OUT}")

if __name__ == "__main__":
    main()
