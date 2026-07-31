#!/usr/bin/env python3
"""SPOILS art pipeline. Generates every game asset into art/gen/ from the Apollo
palette. Deterministic: same script -> same pixels. If an asset looks bad, fix
this file and rerun; never hand-edit outputs.

Outputs:
  art/gen/floors.png    - 64x32 iso floor tiles, 4x5 atlas grid
  art/gen/wall_*.png    - neighbor-masked brick wall pieces (see below)
  art/gen/<prop>.png    - individual prop sprites
  art/gen/char.png      - player sheet, 8 dirs x 7 frames (idle + 6 walk), 32x40
  art/gen/shadow.png    - blob shadow (palette color + alpha)
  art/gen/manifest.json - sizes/origins/atlas coords consumed by the game
  art/gen/preview.png   - 3x contact sheet for visual review (not used in-game)

Wall system: buildings are rings of 64x32-footprint brick blocks. To avoid the
"row of cubes" look, each piece is generated per neighbor mask (which of the
four tile-axis neighbors also hold a wall): faces that a neighbor covers are
skipped and outlines along shared edges are erased, so runs read as one
continuous wall. Piece names: wall_<style>_m<xn><xp><yn><yp> (bits), plus
wall_<style>_win_x / _win_y (windowed straight runs) and wall_<style>_broken_a/b.
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

    def outline_auto(self, c=OUTLINE) -> set:
        """1px outline: paint transparent pixels that touch an opaque one.
        Returns the set of painted outline pixels."""
        opaque = {(x, y) for y in range(self.h) for x in range(self.w)
                  if self.px[x, y][3] > 0}
        painted: set = set()
        for (x, y) in list(opaque):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) not in opaque and 0 <= nx < self.w and 0 <= ny < self.h:
                    if (nx, ny) not in painted:
                        self.set(nx, ny, c)
                        painted.add((nx, ny))
        return painted

    def mirrored(self) -> "Canvas":
        m = Canvas(self.w, self.h)
        m.img = self.img.transpose(Image.FLIP_LEFT_RIGHT)
        m.px = m.img.load()
        return m

# ------------------------------------------------------------ iso diamond ----
# 64x32 diamond that tessellates exactly under the iso tile lattice
# a*(32,16) + b*(32,-16). Top rows y=0..15 span [30-2y, 33+2y]; bottom rows
# mirror rows 14..0, i.e. y=16..31 span [2+2j, 61-2j] (empty at j=15).

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

# Per-column bottommost diamond row (for extruding side faces / shearing).
def diamond_bottom_y(x: int) -> int:
    best = -1
    for y in range(32):
        if in_diamond(x, y):
            best = y
    return best

DIAMOND_REGION = None  # filled in main() after tessellation check

# --------------------------------------------------------------- floors ------
# Goal (user feedback): the ground must read as one continuous surface, not a
# grid of diamonds. So: NO per-tile edge lines, low-contrast noise only, and
# repetition hidden by many plain variants + rare one-off detail tiles.

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

def _floor_base(c: Canvas, rng: random.Random, base, dark, lite,
                p_dark: float, p_lite: float) -> set:
    region = {(x, y) for y in range(32) for x in range(64) if in_diamond(x, y)}
    for (x, y) in region:
        c.set(x, y, base)
    speckle(c, rng, region, [dark, lite], [p_dark, p_lite])
    return region

def make_floor_tile(kind: str, variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:floor:{kind}:{variant}")
    c = Canvas(64, 32)

    if kind == "concrete":
        _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.05, 0.025)

    elif kind == "crack":
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.05, 0.025)
        x, y = 20 + rng.randrange(24), 8 + rng.randrange(16)
        dx = rng.choice((-1, 1))
        for _ in range(rng.randint(12, 18)):
            if (x, y) in region:
                c.set(x, y, CONC_D1)
                if rng.random() < 0.25:
                    c.set(x + 1, y, CONC_D1)
            x += dx if rng.random() < 0.75 else -dx
            y += rng.choice((0, 1, 1, -1))

    elif kind == "stain":
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.05, 0.025)
        core = blob(rng, 32 + rng.randint(-10, 10), 16 + rng.randint(-4, 4),
                    rng.randint(25, 50), region)
        for (x, y) in core:
            c.set(x, y, CONC_D1)
        for (x, y) in list(core):  # dithered soft rim
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in region and (nx, ny) not in core and (nx + ny) % 2 == 0:
                    c.set(nx, ny, CONC_D1)

    elif kind == "moss":
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.05, 0.025)
        m = blob(rng, 32 + rng.randint(-12, 12), 16 + rng.randint(-5, 5),
                 rng.randint(20, 40), region)
        for (x, y) in m:
            if rng.random() < 0.65:
                c.set(x, y, C("19332d"))
            elif rng.random() < 0.3:
                c.set(x, y, C("25562e"))

    elif kind == "dirt":
        _floor_base(c, rng, C("341c27"), C("241527"), C("4d2b32"), 0.06, 0.10)

    elif kind == "dirt_blend":  # concrete with dirt worked into it (patch edges)
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.05, 0.02)
        speckle(c, rng, region, [C("341c27"), C("4d2b32")], [0.13, 0.09])

    elif kind == "asphalt":
        _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.06, 0.03)

    elif kind == "asphalt_line":
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.06, 0.03)
        for (x, y) in region:
            if abs((x - 32) * 0.5 + (y - 16)) < 1.5 and (x // 10) % 2 == 0 and rng.random() < 0.92:
                c.set(x, y, C("de9e41"))
    else:
        raise ValueError(kind)
    return c

FLOOR_TILES = [  # name -> painter args; atlas laid out in listed order, 4 cols
    ("concrete_0", ("concrete", 0)), ("concrete_1", ("concrete", 1)),
    ("concrete_2", ("concrete", 2)), ("concrete_3", ("concrete", 3)),
    ("concrete_4", ("concrete", 4)), ("concrete_5", ("concrete", 5)),
    ("crack_0", ("crack", 0)), ("crack_1", ("crack", 1)), ("crack_2", ("crack", 2)),
    ("stain_0", ("stain", 0)), ("stain_1", ("stain", 1)),
    ("moss_0", ("moss", 0)),
    ("dirt_0", ("dirt", 0)), ("dirt_1", ("dirt", 1)), ("dirt_2", ("dirt", 2)),
    ("dirt_blend_0", ("dirt_blend", 0)), ("dirt_blend_1", ("dirt_blend", 1)),
    ("asphalt_0", ("asphalt", 0)), ("asphalt_1", ("asphalt", 1)),
    ("asphalt_line", ("asphalt_line", 0)),
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
# Brick block, 64x32 footprint, extruded H px. Canvas 66x74 (1px outline
# margin), diamond at ox,oy = 1,1. Overcast light: SW (left) face lit brick,
# SE (right) face shadowed brick, concrete coping on top.

WALL_H = 40
WALL_OX, WALL_OY = 1, 1
WALL_CANVAS = (66, 74)
WALL_ORIGIN = (WALL_OX + 32, WALL_OY + WALL_H + 16)

BRICK_STYLES = {
    "brick_a": {"sw": ("884b2b", "602c2c"), "se": ("602c2c", "341c27")},
    "brick_b": {"sw": ("7a4841", "4d2b32"), "se": ("4d2b32", "341c27")},
}

def _bx(x_local: int) -> int:
    """Absolute canvas row where the top-face diamond ends for local column x."""
    return WALL_OY + diamond_bottom_y(x_local)

def _paint_brick_face(c: Canvas, rng: random.Random, x_range, base, mortar,
                      height_of=None) -> None:
    for lx in x_range:
        x = WALL_OX + lx
        h = WALL_H if height_of is None else height_of(lx)
        top = _bx(lx) + 1 + (WALL_H - h)
        for y in range(top, _bx(lx) + WALL_H + 1):
            fy = y - (_bx(lx) + 1)  # face-local row: courses follow the shear
            course = fy // 4
            if fy % 4 == 3 or (x + course * 4) % 8 == 0:
                col = mortar
            elif rng.random() < 0.05:
                col = mortar
            else:
                col = base
            c.set(x, y, col)

def _paint_coping(c: Canvas, rng: random.Random) -> None:
    for y in range(32):
        s = diamond_span(y)
        if s:
            for x in range(s[0], s[1] + 1):
                r = rng.random()
                col = CONC_L1
                if r < 0.05:
                    col = CONC_BASE
                elif r < 0.07:
                    col = CONC_L2
                c.set(WALL_OX + x, WALL_OY + y, col)

def _paint_window(c: Canvas, side: str) -> None:
    cols = range(8, 22) if side == "sw" else range(42, 56)
    for lx in cols:
        x = WALL_OX + lx
        ft = _bx(lx) + 1
        for fy in range(8, 23):
            c.set(x, ft + fy, C("090a14"))
        c.set(x, ft + 7, C("341c27"))   # lintel
        c.set(x, ft + 23, C("819796"))  # sill
    for lx in (min(cols) - 1, max(cols) + 1):  # jambs
        x = WALL_OX + lx
        ft = _bx(lx) + 1
        for fy in range(7, 24):
            c.set(x, ft + fy, C("341c27"))

def make_wall_piece(style: str, mask: frozenset, window_side: str | None = None) -> Canvas:
    rng = random.Random(f"{SEED}:wall:{style}:{sorted(mask)}:{window_side}")
    colors = BRICK_STYLES[style]
    c = Canvas(*WALL_CANVAS)

    _paint_coping(c, rng)
    if "yp" not in mask:  # SW face exposed (else the +y neighbor covers it)
        _paint_brick_face(c, rng, range(0, 32), C(colors["sw"][0]), C(colors["sw"][1]))
        if window_side == "sw":
            _paint_window(c, "sw")
    if "xp" not in mask:  # SE face exposed
        _paint_brick_face(c, rng, range(32, 64), C(colors["se"][0]), C(colors["se"][1]))
        if window_side == "se":
            _paint_window(c, "se")

    # light crease where coping meets an exposed face (skip covered sides so
    # coping runs read continuous)
    for lx in range(0, 32):
        if "yp" not in mask and lx % 2 == 0:
            c.set(WALL_OX + lx, _bx(lx) + 1, CONC_L2)
    for lx in range(32, 64):
        if "xp" not in mask and lx % 2 == 0:
            c.set(WALL_OX + lx, _bx(lx) + 1, CONC_L2)

    # vertical corner edge only at true convex corners
    if "xp" not in mask and "yp" not in mask:
        for x in (WALL_OX + 31, WALL_OX + 32):
            for y in range(_bx(31) + 2, _bx(31) + WALL_H + 1):
                c.set(x, y, C("151d28"))

    painted = c.outline_auto()
    # erase outline along edges shared with neighboring wall blocks
    cx_split = WALL_OX + 32
    cy_split = WALL_OY + 16
    for (x, y) in painted:
        upper = y < cy_split
        left = x < cx_split
        if upper and left and "xn" in mask:
            c.set(x, y, (0, 0, 0, 0))
        elif upper and not left and "yn" in mask:
            c.set(x, y, (0, 0, 0, 0))
        elif not upper and left and "yp" in mask:
            c.set(x, y, (0, 0, 0, 0))
        elif not upper and not left and "xp" in mask:
            c.set(x, y, (0, 0, 0, 0))
    return c

def make_wall_broken(style: str, variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:wallbrk:{style}:{variant}")
    colors = BRICK_STYLES[style]
    c = Canvas(*WALL_CANVAS)
    heights: list[int] = []
    h = rng.randint(10, 22)
    for lx in range(64):
        if lx % rng.choice((3, 4, 5)) == 0:
            h = max(6, min(26, h + rng.choice((-6, -4, 4, 6))))
        heights.append(h)
    _paint_brick_face(c, rng, range(0, 32), C(colors["sw"][0]), C(colors["sw"][1]),
                      height_of=lambda lx: heights[lx])
    _paint_brick_face(c, rng, range(32, 64), C(colors["se"][0]), C(colors["se"][1]),
                      height_of=lambda lx: heights[lx])
    # jagged cap: broken brick lip
    for lx in range(64):
        top = _bx(lx) + 1 + (WALL_H - heights[lx])
        cap = C("819796") if rng.random() < 0.4 else (
            C(colors["sw"][0]) if lx < 32 else CONC_L1)
        c.set(WALL_OX + lx, top - 1, cap)
        if rng.random() < 0.3:
            c.set(WALL_OX + lx, top, CONC_L1)
    c.outline_auto()
    return c

def wall_piece_inventory() -> dict[str, Canvas]:
    pieces: dict[str, Canvas] = {}
    for style in BRICK_STYLES:
        for bits in range(16):
            mask = frozenset(d for i, d in enumerate(("xn", "xp", "yn", "yp"))
                             if bits & (1 << i))
            tag = "".join("1" if d in mask else "0" for d in ("xn", "xp", "yn", "yp"))
            pieces[f"wall_{style}_m{tag}"] = make_wall_piece(style, mask)
        pieces[f"wall_{style}_win_x"] = make_wall_piece(
            style, frozenset(("xn", "xp")), window_side="sw")
        pieces[f"wall_{style}_win_y"] = make_wall_piece(
            style, frozenset(("yn", "yp")), window_side="se")
        pieces[f"wall_{style}_broken_a"] = make_wall_broken(style, 0)
        pieces[f"wall_{style}_broken_b"] = make_wall_broken(style, 1)
    return pieces

# ---------------------------------------------------------------- props ------
# Distinct silhouettes on purpose (user feedback: no recolored clones).

def small_diamond_rows(w: int, d: int) -> list[tuple[int, int]]:
    """Row spans (x0,x1) of a w x d iso diamond (d even, w = 2*d)."""
    assert d % 2 == 0 and w == 2 * d, "iso diamond needs w == 2*d, d even"
    rows: list[tuple[int, int]] = []
    for i in range(d):
        k = i + 1 if i < d // 2 else d - i
        half = 2 * k
        rows.append((w // 2 - half, w // 2 + half - 1))
    return rows

def iso_prism(c: Canvas, ox: int, oy: int, w: int, d: int, h: int,
              top, left, right) -> list[int]:
    """Iso box at (ox,oy) = top-left of top-face diamond. Returns per-column
    absolute bottom row of the top face."""
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

def make_crate_wood() -> Canvas:
    W, D, H = 28, 14, 12
    c = Canvas(32, 30)
    top, left, right, line = C("be772b"), C("884b2b"), C("602c2c"), C("341c27")
    ox, oy = 2, 1
    bottoms = iso_prism(c, ox, oy, W, D, H, top, left, right)
    for x in range(W):
        y = bottoms[x] - (0 if x % 2 else 1)
        if c.get(ox + x, y)[3] > 0:
            c.set(ox + x, y, C("de9e41"))
    for x in range(W):
        c.set(ox + x, bottoms[x] + 4, line)
        c.set(ox + x, bottoms[x] + 8, line)
    for y in range(bottoms[W // 2] + 1, bottoms[W // 2] + H + 1):
        c.set(ox + W // 2 - 1, y, line)
        c.set(ox + W // 2, y, line)
    for dx in (-10, -4, 5, 10):
        c.set(ox + W // 2 + dx, bottoms[W // 2 + dx] + 2, C("de9e41"))
    c.outline_auto()
    return c

def make_crate_ammo() -> Canvas:
    """Low, wide olive ammo crate — deliberately flatter than the wood crate."""
    W, D, H = 32, 16, 9
    c = Canvas(36, 30)
    ox, oy = 2, 1
    bottoms = iso_prism(c, ox, oy, W, D, H, C("468232"), C("25562e"), C("19332d"))
    for x in range(W):  # lid rim
        y = bottoms[x]
        c.set(ox + x, y, C("75a743") if x % 2 else C("468232"))
    # lid clasps + stencil dashes on the lit face
    for dx in (-12, 0, 11):
        c.set(ox + W // 2 + dx, bottoms[W // 2 + dx] + 2, C("10141f"))
        c.set(ox + W // 2 + dx, bottoms[W // 2 + dx] + 3, C("10141f"))
    for dx in range(-9, -2, 3):
        c.set(ox + W // 2 + dx, bottoms[W // 2 + dx] + 5, C("75a743"))
        c.set(ox + W // 2 + dx + 1, bottoms[W // 2 + dx] + 5, C("75a743"))
    # rope handles at the tips
    for lx in (0, W - 1):
        c.set(ox + lx, bottoms[lx] + 2, C("341c27"))
        c.set(ox + lx, bottoms[lx] + 3, C("341c27"))
    c.outline_auto()
    return c

def make_dumpster() -> Canvas:
    rng = random.Random(f"{SEED}:dumpster")
    W, D, H = 36, 18, 16
    c = Canvas(40, 38)
    ox, oy = 2, 1
    bottoms = iso_prism(c, ox, oy, W, D, H, C("394a50"), C("25562e"), C("19332d"))
    # lid: gray steel with a highlight seam + handle
    for x in range(W):
        y = bottoms[x] - (0 if x % 2 else 1)
        if c.get(ox + x, y)[3] > 0:
            c.set(ox + x, y, C("577277"))
    for dx in range(-5, 5):
        c.set(ox + W // 2 + dx, oy + D // 2 + (1 if dx % 2 else 0), C("819796"))
    # body ribs + rust
    for x in range(W):
        if x % 6 == 2:
            for y in range(bottoms[x] + 2, bottoms[x] + H):
                c.set(ox + x, y, C("19332d") if x < W // 2 else C("10141f"))
    for _ in range(9):
        x = rng.randrange(2, W - 2)
        c.set(ox + x, bottoms[x] + rng.randint(3, H - 1), C("602c2c"))
    c.outline_auto()
    return c

def make_barrel_rust() -> Canvas:
    rng = random.Random(f"{SEED}:barrel:rust")
    c = Canvas(22, 32)
    body, lite, dark, lid = C("602c2c"), C("884b2b"), C("341c27"), C("394a50")
    cx = 11
    for y in range(6, 30):
        half = 9 if 8 <= y <= 27 else 8
        for x in range(cx - half, cx + half):
            t = (x - (cx - half)) / (2 * half)
            col = lite if t < 0.35 else (body if t < 0.8 else dark)
            c.set(x, y, col)
    lid_half = {3: 5, 4: 8, 5: 9, 6: 9, 7: 8, 8: 6}
    for y, half in lid_half.items():
        for x in range(cx - half, cx + half):
            c.set(x, y, C("577277") if y <= 4 else lid)
    for hy in (12, 21):
        for x in range(cx - 9, cx + 9):
            c.set(x, hy, dark)
            c.set(x, hy - 1, C("ad7757"))
    for _ in range(10):
        c.set(rng.randrange(cx - 8, cx + 8), rng.randrange(9, 29), C("cf573c"))
    c.outline_auto()
    return c

def make_gas_cylinder() -> Canvas:
    """Tall thin steel-blue cylinder — the cool accent among warm props."""
    rng = random.Random(f"{SEED}:gascyl")
    c = Canvas(14, 38)
    cx = 7
    lite, base, dark = C("4f8fba"), C("3c5e8b"), C("253a5e")
    dome = {4: 2, 5: 3, 6: 4, 7: 4}
    for y, half in dome.items():
        for x in range(cx - half, cx + half):
            c.set(x, y, lite if x < cx else base)
    for y in range(8, 33):
        for x in range(cx - 4, cx + 4):
            t = (x - (cx - 4)) / 8.0
            c.set(x, y, lite if t < 0.3 else (base if t < 0.75 else dark))
    for x in range(cx - 4, cx + 4):  # weld band + base ring
        c.set(x, 19, dark)
        c.set(x, 18, C("73bed3") if x % 2 else base)
        c.set(x, 33, C("202e37"))
    c.rect(cx - 1, 1, cx, 3, C("577277"))  # valve
    for _ in range(4):
        c.set(rng.randrange(cx - 3, cx + 3), rng.randrange(20, 32), C("602c2c"))
    c.outline_auto()
    return c

def make_tire_stack() -> Canvas:
    rng = random.Random(f"{SEED}:tires")
    c = Canvas(30, 28)
    cx = 15
    halves = [8, 11, 12, 12, 11, 9]
    offsets = [(0, 18), (1, 12), (-1, 6)]  # bottom -> top, slight skew
    for i, (dx, base_y) in enumerate(offsets):
        top = i == len(offsets) - 1
        for row, half in enumerate(halves):
            y = base_y + row
            for x in range(cx + dx - half, cx + dx + half):
                t = (x - (cx + dx - half)) / (2 * half)
                col = C("202e37") if (row <= 1 and 0.15 < t < 0.85) else C("151d28")
                if row >= 4:
                    col = C("10141f")
                c.set(x, y, col)
        if top:  # dark hole in the top tire
            for row, half in ((0, 5), (1, 6), (2, 5)):
                for x in range(cx + dx - half, cx + dx + half):
                    c.set(x, base_y + row + 1, C("090a14"))
    c.outline_auto()
    return c

def make_pallet() -> Canvas:
    """Flat wooden pallet — low, walk-over dressing."""
    c = Canvas(38, 24)
    ox, oy = 3, 2
    rows = small_diamond_rows(32, 16)
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            band = ((x + 2 * i) // 5) % 3
            col = C("884b2b") if band == 0 else (C("7a4841") if band == 1 else C("341c27"))
            c.set(ox + x, oy + i, col)
    bottoms = [0] * 32
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            bottoms[x] = i
    for x in range(32):
        for y in range(oy + bottoms[x] + 1, oy + bottoms[x] + 4):
            c.set(ox + x, y, C("602c2c") if x < 16 else C("341c27"))
    c.outline_auto()
    return c

def make_rubble(variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:rubble:{variant}")
    c = Canvas(48, 26)
    grays = [C("202e37"), C("394a50"), C("577277"), C("819796")]
    for x in range(4, 44):
        h = int(9 * (1 - ((x - 24) / 22) ** 2)) + rng.randint(-1, 1)
        for y in range(c.h - 3 - max(0, h), c.h - 2):
            t = rng.random()
            c.set(x, y, grays[1] if t < 0.5 else (grays[0] if t < 0.8 else grays[2]))
    for _ in range(rng.randint(8, 12)):
        x, y = rng.randrange(8, 40), rng.randrange(c.h - 11, c.h - 3)
        c.set(x, y, grays[3])
        c.set(x + 1, y, grays[2])
        c.set(x, y + 1, grays[1])
    # the odd brick chunk so piles tie into the buildings
    for _ in range(3 if variant == 0 else 2):
        x, y = rng.randrange(8, 38), rng.randrange(c.h - 9, c.h - 3)
        c.set(x, y, C("884b2b"))
        c.set(x + 1, y, C("602c2c"))
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
    cuts = {}
    for x in range(4, 14):
        cut = rng.randint(0, 5)
        cuts[x] = cut
        for y in range(6, 6 + cut):
            c.set(x, y, (0, 0, 0, 0))
        c.set(x, 6 + cut, C("819796"))
    for rx in (8, 11):
        top = 6 + cuts.get(rx, 0)
        for y in range(top - 3, top + 1):
            c.set(rx, y, C("602c2c"))
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
# Columns: 0 = idle, 1..6 = walk cycle (contact/recoil/passing x2).

SKIN, SKIN_SH = C("d7b594"), C("c09473")
JKT_L, JKT, JKT_D = C("468232"), C("25562e"), C("19332d")
PANT, PANT_D = C("202e37"), C("151d28")
BOOT, BOOT_D = C("341c27"), C("10141f")
BEANIE, BEANIE_D = C("394a50"), C("202e37")
PACK, PACK_D = C("7a4841"), C("4d2b32")
STRAP = C("341c27")

CX, FEET = 16, 37
WALK_FRAMES = 6

# per-frame body bob (applies to head/torso/arms/pack)
BOB = {0: 0, 1: 0, 2: -1, 3: -1, 4: 0, 5: -1, 6: -1}
# side-view stride: (front_dx, back_dx, front_lift, back_lift)
SIDE_STRIDE = {
    0: (0, 0, 0, 0),
    1: (3, -3, 0, 0), 2: (2, -2, 0, 1), 3: (0, 0, 0, 2),
    4: (-3, 3, 0, 0), 5: (-2, 2, 1, 0), 6: (0, 0, 2, 0),
}
# front/back-view step lifts: (left_lift, right_lift)
STEP_LIFT = {
    0: (0, 0),
    1: (0, 2), 2: (0, 1), 3: (0, 0),
    4: (2, 0), 5: (1, 0), 6: (0, 0),
}
# arm swing along facing
SIDE_SWING = {0: 0, 1: -2, 2: -1, 3: 0, 4: 2, 5: 1, 6: 0}
FRONT_SWING = {0: 0, 1: 1, 2: 1, 3: 0, 4: -1, 5: -1, 6: 0}


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
        c.rect(CX - 3, y0 + 4, CX - 1, y0 + 7, SKIN_SH)
        c.rect(CX, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.set(CX + 4, y0 + 5, SKIN)
        c.set(CX + 4, y0 + 6, SKIN_SH)
        c.set(CX + 2, y0 + 5, OUTLINE)
        c.hline(CX - 3, CX + 3, y0 + 7, SKIN_SH)
    elif view == "back34":    # NE
        c.rect(CX - 3, y0, CX + 4, y0 + 4, BEANIE)
        c.hline(CX - 3, CX + 4, y0 + 4, BEANIE_D)
        c.rect(CX - 3, y0 + 5, CX + 4, y0 + 7, BEANIE_D)
        c.set(CX + 4, y0 + 6, SKIN_SH)
    elif view == "back":      # N
        c.rect(CX - 4, y0, CX + 3, y0 + 4, BEANIE)
        c.hline(CX - 4, CX + 3, y0 + 4, BEANIE_D)
        c.rect(CX - 4, y0 + 5, CX + 3, y0 + 7, BEANIE_D)
        c.rect(CX - 2, y0 + 7, CX + 1, y0 + 7, SKIN_SH)


def draw_torso(c: Canvas, view: str, bob: int) -> None:
    y0, y1 = 18 + bob, 27 + bob
    x0, x1 = CX - 4, CX + 3
    c.rect(x0, y0, x1, y1, JKT)
    c.hline(x0, x1, y0, JKT_L)
    c.vline(x1, y0 + 1, y1, JKT_D)
    c.hline(x0, x1, y1, JKT_D)
    if view == "front":
        c.vline(CX, y0 + 1, y1, INK)
        c.vline(CX - 3, y0, y0 + 4, STRAP)
        c.vline(CX + 2, y0, y0 + 4, STRAP)
    if view == "front34":
        c.vline(CX + 1, y0 + 1, y1, INK)
        c.vline(CX - 2, y0, y0 + 4, STRAP)
    if view == "side":
        c.vline(CX + 3, y0 + 1, y1 - 1, JKT_D)
    c.rect(CX - 4, y1 + 1, CX + 3, y1 + 2, PANT)
    c.hline(CX - 4, CX + 3, y1 + 2, PANT_D)


def draw_pack(c: Canvas, view: str, bob: int) -> None:
    y0 = 19 + bob
    if view == "back":
        c.rect(CX - 3, y0, CX + 2, y0 + 8, PACK)
        c.rect(CX - 3, y0 + 6, CX + 2, y0 + 8, PACK_D)
        c.hline(CX - 3, CX + 2, y0, C("ad7757"))
        c.vline(CX, y0, y0 + 8, PACK_D)
    elif view == "back34":
        c.rect(CX - 4, y0, CX + 1, y0 + 8, PACK)
        c.rect(CX - 4, y0 + 6, CX + 1, y0 + 8, PACK_D)
        c.hline(CX - 4, CX + 1, y0, C("ad7757"))
    elif view == "side":
        c.rect(CX - 6, y0 + 1, CX - 4, y0 + 7, PACK)
        c.vline(CX - 6, y0 + 1, y0 + 7, PACK_D)


def draw_arms(c: Canvas, view: str, bob: int, frame: int) -> None:
    y0 = 19 + bob
    if view in ("front", "back"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = CX + (side * 6) - (1 if side < 0 else 0)
            yy = y0 + (1 if sw > 0 else 0)
            c.rect(x, yy, x + 1, yy + 8, JKT if side < 0 else JKT_D)
            c.rect(x, yy + 9, x + 1, yy + 10, SKIN if view == "front" else SKIN_SH)
    elif view in ("front34", "back34"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = CX + (5 * side) + (0 if side < 0 else -1) + sw
            c.rect(x, y0, x + 1, y0 + 8, JKT if side < 0 else JKT_D)
            c.rect(x, y0 + 9, x + 1, y0 + 10, SKIN)
    else:  # side: near arm swings along facing
        x = CX + 1 + SIDE_SWING[frame]
        c.rect(x, y0, x + 1, y0 + 8, JKT_D)
        c.rect(x, y0 + 9, x + 1, y0 + 10, SKIN)


def draw_legs(c: Canvas, view: str, frame: int) -> None:
    if view in ("front", "front34", "back", "back34"):
        lifts = STEP_LIFT[frame]
        for (x0, lift, pcol) in ((CX - 4, lifts[0], PANT), (CX + 1, lifts[1], PANT_D)):
            dy = -lift
            c.rect(x0, 28, x0 + 2, 33 + dy, pcol)
            c.rect(x0, 34 + dy, x0 + 2, 36 + dy, BOOT)
            c.hline(x0, x0 + 2, FEET + dy, BOOT_D)
    else:  # side view: scissor stride toward +x
        front_dx, back_dx, front_lift, back_lift = SIDE_STRIDE[frame]
        for dx, lift, pcol, bcol in ((back_dx, back_lift, PANT_D, BOOT),
                                     (front_dx, front_lift, PANT, BOOT)):
            x0 = CX - 1 + dx
            c.rect(x0, 28, x0 + 2, 33 - lift, pcol)
            c.rect(x0, 34 - lift, x0 + 2, 36 - lift, bcol)
            toe = x0 + (3 if dx >= 0 else 2)
            c.hline(x0, toe, FEET - lift, BOOT_D)


def draw_char_frame(view: str, frame: int) -> Canvas:
    c = Canvas(32, 40)
    bob = BOB[frame]
    if view in ("back", "back34"):
        draw_legs(c, view, frame)
        draw_torso(c, view, bob)
        draw_arms(c, view, bob, frame)
        draw_pack(c, view, bob)
        draw_head(c, view, bob)
    elif view == "side":
        draw_pack(c, view, bob)
        draw_legs(c, view, frame)
        draw_torso(c, view, bob)
        draw_arms(c, view, bob, frame)
        draw_head(c, view, bob)
    else:
        draw_legs(c, view, frame)
        draw_torso(c, view, bob)
        draw_arms(c, view, bob, frame)
        draw_head(c, view, bob)
    c.outline_auto()
    return c

DIR_VIEWS = [
    ("E", "side", False), ("SE", "front34", False), ("S", "front", False),
    ("SW", "front34", True), ("W", "side", True), ("NW", "back34", True),
    ("N", "back", False), ("NE", "back34", False),
]

def make_char_sheet() -> Image.Image:
    cols = 1 + WALK_FRAMES
    sheet = Image.new("RGBA", (cols * 32, 8 * 40), (0, 0, 0, 0))
    for row, (_, view, mirrored) in enumerate(DIR_VIEWS):
        for frame in range(cols):
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
    for stale in OUT.glob("*.png"):
        stale.unlink()

    manifest: dict = {"tile": [64, 32], "floors": {}, "props": {}, "char": {}}

    floors, coords = make_floors_atlas()
    assert_palette(floors, "floors")
    floors.save(OUT / "floors.png")
    manifest["floors"] = coords

    props: dict[str, tuple[Canvas, tuple[int, int]]] = {
        "crate_wood": (make_crate_wood(), (16, 20)),
        "crate_ammo": (make_crate_ammo(), (18, 18)),
        "dumpster": (make_dumpster(), (20, 26)),
        "barrel_rust": (make_barrel_rust(), (11, 27)),
        "gas_cylinder": (make_gas_cylinder(), (7, 33)),
        "tire_stack": (make_tire_stack(), (15, 24)),
        "pallet": (make_pallet(), (19, 13)),
        "rubble_a": (make_rubble(0), (24, 20)),
        "rubble_b": (make_rubble(1), (24, 20)),
        "pillar": (make_pillar(), (9, 50)),
        "shadow": (make_shadow(), (12, 6)),
    }
    for piece_name, canvas in wall_piece_inventory().items():
        props[piece_name] = (canvas, WALL_ORIGIN)

    for name, (canvas, origin) in props.items():
        if name != "shadow":
            assert_palette(canvas.img, name)
        canvas.img.save(OUT / f"{name}.png")
        manifest["props"][name] = {"size": [canvas.w, canvas.h], "origin": list(origin)}

    sheet = make_char_sheet()
    assert_palette(sheet, "char")
    sheet.save(OUT / "char.png")
    manifest["char"] = {
        "frame": [32, 40], "cols": 1 + WALK_FRAMES, "origin": [16, 37],
        "dirs": [d for d, _, _ in DIR_VIEWS],
    }

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # ---- 3x contact sheet for review ----
    def x3(img: Image.Image) -> Image.Image:
        return img.resize((img.width * 3, img.height * 3), Image.NEAREST)

    pad = 12
    show_props = ["crate_wood", "crate_ammo", "dumpster", "barrel_rust",
                  "gas_cylinder", "tire_stack", "pallet", "rubble_a", "rubble_b",
                  "pillar"]
    show_walls = ["wall_brick_a_m0000", "wall_brick_a_m1100", "wall_brick_a_m0011",
                  "wall_brick_a_m1001", "wall_brick_a_win_x", "wall_brick_a_win_y",
                  "wall_brick_a_broken_a", "wall_brick_b_m0000", "wall_brick_b_win_x",
                  "wall_brick_b_broken_b"]
    rows_imgs: list[list[Image.Image]] = [
        [x3(floors)],
        [x3(props[n][0].img) for n in show_walls],
        [x3(props[n][0].img) for n in show_props],
        [x3(sheet)],
    ]
    W = max(sum(i.width + pad for i in row) for row in rows_imgs) + pad
    Hh = sum(max(i.height for i in row) + pad for row in rows_imgs) + pad
    prev = Image.new("RGBA", (W, Hh), C("10141f"))
    ycur = pad
    for row in rows_imgs:
        rh = max(i.height for i in row)
        xcur = pad
        for i in row:
            prev.paste(i, (xcur, ycur + rh - i.height), i)
            xcur += i.width + pad
        ycur += rh + pad
    prev.save(OUT / "preview.png")

    print(f"OK: wrote {len(props) + 3} files to {OUT}")

if __name__ == "__main__":
    main()
