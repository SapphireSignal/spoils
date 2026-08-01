#!/usr/bin/env python3
"""SPOILS art pipeline. Generates every game asset into art/gen/ from the Apollo
palette. Deterministic: same script -> same pixels. If an asset looks bad, fix
this file and rerun; never hand-edit outputs.

Outputs:
  art/gen/floors.png     - 64x32 iso floor tiles, 4x5 atlas grid
  art/gen/wall_*.png     - neighbor-masked brick wall pieces
  art/gen/roof_*.png     - roof tiles/vent/hatch (interior-reveal system)
  art/gen/<family>_<n>   - prop variants (procedurally varied per instance)
  art/gen/char.png       - player sheet, 8 dirs x 7 frames (idle + 6 walk), 32x40
  art/gen/title.png      - main-menu wordmark
  art/gen/vignette.png   - menu vignette (soft alpha, intentionally not palette)
  art/gen/dust.png       - particle speck (white, tinted at runtime)
  art/gen/shadow.png     - blob shadow (palette color + alpha)
  art/gen/manifest.json  - sizes/origins/colliders/families consumed by the game

Prop variation: each family (barrel, crate, cylinder, tires, pallet, dumpster,
rubble, pillar) is one parameterized draw function; variants roll proportions,
details, damage, accessories and pose (incl. fallen/toppled) from a seeded rng.
Colliders are computed per variant and shipped in the manifest, so the game
never hardcodes shapes. Runtime scaling/rotation is deliberately NOT used —
it breaks the pixel grid; variation is baked at generation time instead.
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
        for (x, y) in list(core):
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
    elif kind == "dirt_blend":
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

FLOOR_TILES = [
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
# Brick block, 64x32 footprint, extruded H px, neighbor-masked (see 0.2.0).
# 0.4.0 texture pass: mortar courses are dithered one-shade lines, vertical
# joints are sparse (16px staggered, 50% dither) — brick reads as texture,
# not as a grid. Windows come in three shapes incl. boarded-up.

WALL_H = 40
WALL_OX, WALL_OY = 1, 1
WALL_CANVAS = (66, 74)
WALL_ORIGIN = (WALL_OX + 32, WALL_OY + WALL_H + 16)

BRICK_STYLES = {
    "brick_a": {"sw": ("884b2b", "602c2c"), "se": ("602c2c", "341c27")},
    "brick_b": {"sw": ("7a4841", "4d2b32"), "se": ("4d2b32", "341c27")},
}

# window variants: (face columns offset, top row in face coords, w, h, boarded)
WINDOW_VARIANTS = [
    (9, 7, 12, 14, False),   # tall
    (5, 11, 18, 9, False),   # wide + low
    (11, 9, 10, 10, True),   # small, boarded up
]

def _bx(x_local: int) -> int:
    return WALL_OY + diamond_bottom_y(x_local)

def _paint_brick_face(c: Canvas, rng: random.Random, x_range, base, mortar,
                      height_of=None) -> None:
    for lx in x_range:
        x = WALL_OX + lx
        h = WALL_H if height_of is None else height_of(lx)
        top = _bx(lx) + 1 + (WALL_H - h)
        for y in range(top, _bx(lx) + WALL_H + 1):
            fy = y - (_bx(lx) + 1)
            course = fy // 4
            col = base
            if fy % 4 == 3:
                # horizontal mortar course, dithered so it stays soft
                if (x + fy) % 2 == 0:
                    col = mortar
            elif (x + (8 if course % 2 else 0)) % 16 == 0 and rng.random() < 0.55:
                col = mortar  # sparse staggered head joints
            elif rng.random() < 0.04:
                col = mortar  # worn brick
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

def _paint_window(c: Canvas, rng: random.Random, side: str, variant: int) -> None:
    off, top, w, h, boarded = WINDOW_VARIANTS[variant]
    base_col = 0 if side == "sw" else 32
    cols = range(base_col + off, base_col + off + w)
    for lx in cols:
        x = WALL_OX + lx
        ft = _bx(lx) + 1
        for fy in range(top, top + h):
            c.set(x, ft + fy, C("090a14"))
        c.set(x, ft + top - 1, C("341c27"))       # lintel
        c.set(x, ft + top + h, C("819796"))       # sill
    for lx in (min(cols) - 1, max(cols) + 1):     # jambs, soft tone
        x = WALL_OX + lx
        ft = _bx(lx) + 1
        for fy in range(top - 1, top + h + 1):
            c.set(x, ft + fy, C("341c27"))
    if boarded:
        for i, plank_fy in enumerate(range(top + 1, top + h, 3)):
            for lx in cols:
                x = WALL_OX + lx
                ft = _bx(lx) + 1
                wobble = (lx + i) % 3 == 0
                c.set(x, ft + plank_fy + (1 if wobble else 0),
                      C("884b2b") if (lx + i) % 2 else C("602c2c"))

def make_wall_piece(style: str, mask: frozenset, window_side: str | None = None,
                    window_variant: int = 0) -> Canvas:
    rng = random.Random(f"{SEED}:wall:{style}:{sorted(mask)}:{window_side}:{window_variant}")
    colors = BRICK_STYLES[style]
    c = Canvas(*WALL_CANVAS)

    _paint_coping(c, rng)
    if "yp" not in mask:
        _paint_brick_face(c, rng, range(0, 32), C(colors["sw"][0]), C(colors["sw"][1]))
        if window_side == "sw":
            _paint_window(c, rng, "sw", window_variant)
    if "xp" not in mask:
        _paint_brick_face(c, rng, range(32, 64), C(colors["se"][0]), C(colors["se"][1]))
        if window_side == "se":
            _paint_window(c, rng, "se", window_variant)

    for lx in range(0, 32):
        if "yp" not in mask and lx % 2 == 0:
            c.set(WALL_OX + lx, _bx(lx) + 1, CONC_L2)
    for lx in range(32, 64):
        if "xp" not in mask and lx % 2 == 0:
            c.set(WALL_OX + lx, _bx(lx) + 1, CONC_L2)

    # soft vertical crease only at true convex corners
    if "xp" not in mask and "yp" not in mask:
        for y in range(_bx(31) + 2, _bx(31) + WALL_H + 1):
            c.set(WALL_OX + 32, y, C(colors["se"][1]))

    painted = c.outline_auto()
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
        for v in range(len(WINDOW_VARIANTS)):
            pieces[f"wall_{style}_win_x_{v}"] = make_wall_piece(
                style, frozenset(("xn", "xp")), "sw", v)
            pieces[f"wall_{style}_win_y_{v}"] = make_wall_piece(
                style, frozenset(("yn", "yp")), "se", v)
        pieces[f"wall_{style}_broken_a"] = make_wall_broken(style, 0)
        pieces[f"wall_{style}_broken_b"] = make_wall_broken(style, 1)
    return pieces

# ----------------------------------------------------------------- roofs -----
# Tar roof tiles sit WALL_H-6 above the floor inside the parapet; the game
# fades the whole roof group when the player is inside (interior reveal).

def make_roof_tile(variant: int) -> Canvas:
    rng = random.Random(f"{SEED}:roof:{variant}")
    c = Canvas(64, 32)
    region = {(x, y) for y in range(32) for x in range(64) if in_diamond(x, y)}
    for (x, y) in region:
        c.set(x, y, CONC_D1)
    speckle(c, rng, region, [C("151d28"), CONC_BASE], [0.09, 0.05])
    if variant == 1:  # tar patch streaks
        patch = blob(rng, 32 + rng.randint(-10, 10), 16 + rng.randint(-4, 4),
                     rng.randint(20, 40), region)
        for (x, y) in patch:
            c.set(x, y, C("151d28"))
    return c

def make_roof_vent() -> Canvas:
    c = Canvas(24, 22)
    bottoms = iso_prism(c, 2, 1, 20, 10, 7, CONC_BASE, CONC_D1, CONC_D2)
    for x in range(3, 17):  # louver slits on the lit face
        if x % 3 != 0:
            c.set(2 + x, bottoms[x] + 3, INK)
            c.set(2 + x, bottoms[x] + 5, INK)
    c.outline_auto()
    return c

def make_roof_hatch() -> Canvas:
    c = Canvas(20, 14)
    bottoms = iso_prism(c, 2, 1, 16, 8, 2, CONC_D1, CONC_D2, INK)
    for x in range(4, 12):
        c.set(2 + x, bottoms[x] - 1, CONC_BASE)
    c.outline_auto()
    return c

# ---------------------------------------------------------------- props ------

def small_diamond_rows(w: int, d: int) -> list[tuple[int, int]]:
    assert d % 2 == 0 and w == 2 * d, "iso diamond needs w == 2*d, d even"
    rows: list[tuple[int, int]] = []
    for i in range(d):
        k = i + 1 if i < d // 2 else d - i
        half = 2 * k
        rows.append((w // 2 - half, w // 2 + half - 1))
    return rows

def iso_prism(c: Canvas, ox: int, oy: int, w: int, d: int, h: int,
              top, left, right) -> list[int]:
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

WOOD_TONES = [("be772b", "884b2b", "602c2c", "341c27"),
              ("ad7757", "7a4841", "4d2b32", "341c27")]

def draw_crate(rng: random.Random, w: int, h: int, tone: int,
               damaged: bool, stencil: bool) -> tuple[Canvas, tuple, list]:
    d = w // 2
    c = Canvas(w + 4, d + h + 4)
    top, left, right, line = (C(n) for n in WOOD_TONES[tone])
    ox, oy = 2, 1
    bottoms = iso_prism(c, ox, oy, w, d, h, top, left, right)
    for x in range(w):
        y = bottoms[x] - (0 if x % 2 else 1)
        if c.get(ox + x, y)[3] > 0:
            c.set(ox + x, y, C("de9e41") if tone == 0 else C("c09473"))
    for seam_off in range(4, h, 4):
        for x in range(w):
            c.set(ox + x, bottoms[x] + seam_off, line)
    for y in range(bottoms[w // 2] + 1, bottoms[w // 2] + h + 1):
        c.set(ox + w // 2 - 1, y, line)
        c.set(ox + w // 2, y, line)
    if damaged:  # a missing board on the lit face
        gx = rng.randrange(4, w // 2 - 4)
        for x in range(gx, gx + rng.randint(3, 5)):
            for y in range(bottoms[x] + 1, bottoms[x] + min(h, 5)):
                c.set(ox + x, y, OUTLINE)
    if stencil:
        for dx in range(-w // 4, -w // 4 + 6, 2):
            c.set(ox + w // 2 + dx, bottoms[w // 2 + dx] + 2, C("de9e41"))
    c.outline_auto()
    origin = (2 + w // 2, oy + h + d // 2)
    collider = ["diamond", w // 2 + 1.0, d // 2 + 1.0]
    return c, origin, collider

def draw_barrel(rng: random.Random, style: str, h: int, r: int,
                fallen: bool) -> tuple[Canvas, tuple, list]:
    styles = {
        "rust": (C("602c2c"), C("884b2b"), C("341c27"), C("394a50"), C("cf573c")),
        "olive": (C("25562e"), C("468232"), C("19332d"), C("394a50"), C("577277")),
        "steel": (C("3c5e8b"), C("4f8fba"), C("253a5e"), C("577277"), C("73bed3")),
    }
    body, lite, dark, lid, fleck = styles[style]
    if not fallen:
        c = Canvas(2 * r + 4, h + 6)
        cx = r + 2
        top_y, bot_y = 5, h + 3
        for y in range(top_y, bot_y):
            half = r if top_y + 2 <= y <= bot_y - 3 else r - 1
            for x in range(cx - half, cx + half):
                t = (x - (cx - half)) / (2 * half)
                c.set(x, y, lite if t < 0.35 else (body if t < 0.8 else dark))
        for y in range(2, 7):
            half = max(3, r - abs(y - 4) * 2 - 0)
            half = min(r, half + 3)
            for x in range(cx - half, cx + half):
                c.set(x, y, C("819796") if y <= 3 else lid)
        hoop_ys = [top_y + (h - 4) // 3, top_y + 2 * (h - 4) // 3]
        if rng.random() < 0.5:
            hoop_ys.append(top_y + 3)
        for hy in hoop_ys:
            for x in range(cx - r, cx + r):
                c.set(x, hy, dark)
                c.set(x, hy - 1, C("ad7757") if style == "rust" else C("819796"))
        if rng.random() < 0.5:  # dent
            dy = rng.randrange(top_y + 3, bot_y - 3)
            for x in range(cx - r, cx - r + 3):
                c.set(x, dy, dark)
                c.set(x, dy + 1, dark)
        for _ in range(rng.randint(6, 12)):
            c.set(rng.randrange(cx - r + 1, cx + r - 1), rng.randrange(7, bot_y - 1), fleck)
        c.outline_auto()
        return c, (cx, h + 2), ["circle", float(r - 1)]
    # fallen barrel: cylinder on its side, seen at iso angle
    length = h
    c = Canvas(length + 10, 2 * r + 8)
    cy = r + 4
    for i in range(length):
        x = 4 + i
        sh = int(2 * (i / max(1, length - 1)))  # slight iso drop along the length
        for y in range(cy - r + sh, cy + r - 2 + sh):
            t = (y - (cy - r + sh)) / (2 * r - 2)
            c.set(x, y, lite if t < 0.3 else (body if t < 0.75 else dark))
    for y in range(cy - r, cy + r - 2):  # end cap facing camera
        half_ok = abs(y - (cy - 1)) < r - 1
        if half_ok:
            c.set(3, y, lid)
            c.set(2, y, dark)
    for hx in (4 + length // 3, 4 + 2 * length // 3):
        for y in range(cy - r + 1, cy + r - 1):
            c.set(hx, y + 1, dark)
    for _ in range(rng.randint(5, 9)):
        c.set(rng.randrange(6, length + 2), rng.randrange(cy - r + 2, cy + r), fleck)
    c.outline_auto()
    return c, (length // 2 + 4, 2 * r + 2), ["diamond", length / 2 + 2.0, float(r - 2)]

def draw_cylinder(rng: random.Random, color: str, h: int,
                  toppled: bool) -> tuple[Canvas, tuple, list]:
    tones = {
        "steel": (C("4f8fba"), C("3c5e8b"), C("253a5e"), C("73bed3")),
        "red": (C("a53030"), C("752438"), C("411d31"), C("cf573c")),
        "gray": (C("819796"), C("577277"), C("394a50"), C("a8b5b2")),
    }
    lite, base, dark, glint = tones[color]
    if not toppled:
        c = Canvas(14, h + 6)
        cx = 7
        top = 4
        dome = {top: 2, top + 1: 3, top + 2: 4, top + 3: 4}
        for y, half in dome.items():
            for x in range(cx - half, cx + half):
                c.set(x, y, lite if x < cx else base)
        for y in range(top + 4, h + 1):
            for x in range(cx - 4, cx + 4):
                t = (x - (cx - 4)) / 8.0
                c.set(x, y, lite if t < 0.3 else (base if t < 0.75 else dark))
        band_y = top + 4 + (h - top - 4) // 2
        for x in range(cx - 4, cx + 4):
            c.set(x, band_y, dark)
            c.set(x, band_y - 1, glint if x % 2 else base)
            c.set(x, h + 1, C("202e37"))
        c.rect(cx - 1, 1, cx, 3, C("577277"))
        for _ in range(rng.randint(2, 5)):
            c.set(rng.randrange(cx - 3, cx + 3), rng.randrange(top + 6, h), C("602c2c"))
        c.outline_auto()
        return c, (7, h + 1), ["circle", 4.0]
    c = Canvas(h + 8, 16)
    for i in range(h - 4):
        x = 5 + i
        sh = int(1.5 * (i / max(1, h - 5)))
        for y in range(4 + sh, 11 + sh):
            t = (y - 4 - sh) / 7.0
            c.set(x, y, lite if t < 0.3 else (base if t < 0.75 else dark))
    for y in range(5, 10):  # dome end
        c.set(4, y, base)
        c.set(3, y, dark)
    c.rect(h + 1, 6, h + 3, 8, C("577277"))  # valve
    c.outline_auto()
    return c, ((h + 4) // 2, 12), ["diamond", h / 2.0, 4.0]

def draw_tires(rng: random.Random, count: int, single: bool) -> tuple[Canvas, tuple, list]:
    if single:  # one tire leaning upright
        c = Canvas(22, 24)
        cx, cy = 11, 11
        for y in range(22):
            for x in range(22):
                dx, dy = (x - cx) / 9.5, (y - cy) / 9.5
                d = dx * dx + dy * dy
                if 0.35 < d < 1.0:
                    c.set(x, y + 1, C("151d28") if d < 0.8 else C("10141f"))
                elif d <= 0.35:
                    c.set(x, y + 1, C("090a14"))
        for a in range(-3, 4):  # tread highlight arc
            c.set(cx + a, 3 if abs(a) < 2 else 4, C("202e37"))
        c.outline_auto()
        return c, (11, 22), ["circle", 6.0]
    c = Canvas(30, 10 + 6 * count)
    cx = 15
    halves = [8, 11, 12, 12, 11, 9]
    for i in range(count):
        dx = rng.randint(-1, 1)
        base_y = 6 * (count - 1 - i) + 4
        top = i == count - 1
        for row, half in enumerate(halves):
            y = base_y + row
            for x in range(cx + dx - half, cx + dx + half):
                t = (x - (cx + dx - half)) / (2 * half)
                col = C("202e37") if (row <= 1 and 0.15 < t < 0.85) else C("151d28")
                if row >= 4:
                    col = C("10141f")
                c.set(x, y, col)
        if top:
            for row, half in ((0, 5), (1, 6), (2, 5)):
                for x in range(cx + dx - half, cx + dx + half):
                    c.set(x, base_y + row + 1, C("090a14"))
    c.outline_auto()
    return c, (15, 6 * count + 4), ["circle", 7.0 if count > 1 else 6.0]

def draw_pallet(rng: random.Random, broken: bool, stacked: bool) -> tuple[Canvas, tuple, list]:
    c = Canvas(38, 28)
    layers = 2 if stacked else 1
    for layer in range(layers):
        ox, oy = 3 + (1 if layer else 0), 6 - layer * 4
        rows = small_diamond_rows(32, 16)
        for i, (x0, x1) in enumerate(rows):
            for x in range(x0, x1 + 1):
                band = ((x + 2 * i) // 5) % 3
                if broken and layer == 0 and band == 1 and i > 8 and (x // 4) % 3 == 0:
                    continue  # missing slat chunks
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
    return c, (19, 17), None

def draw_dumpster(rng: random.Random, lid_open: bool) -> tuple[Canvas, tuple, list]:
    W, D, H = 36, 18, 16
    c = Canvas(44, 44)
    ox, oy = 3, 9
    bottoms = iso_prism(c, ox, oy, W, D, H, C("394a50"), C("25562e"), C("19332d"))
    if lid_open:
        for i, (x0, x1) in enumerate(small_diamond_rows(W, D)):
            for x in range(x0, x1 + 1):
                c.set(ox + x, oy + i, C("090a14"))  # open: dark interior
        for i in range(D):  # lid leaning up behind the far edge
            y = oy - 7 + i
            x0, x1 = small_diamond_rows(W, D)[i]
            for x in range(x0 + 6, x1 - 6):
                c.set(ox + x, y, C("577277") if i % 3 else C("394a50"))
    else:
        for x in range(W):
            y = bottoms[x] - (0 if x % 2 else 1)
            if c.get(ox + x, y)[3] > 0:
                c.set(ox + x, y, C("577277"))
        for dx in range(-5, 5):
            c.set(ox + W // 2 + dx, oy + D // 2 + (1 if dx % 2 else 0), C("819796"))
    for x in range(W):
        if x % 6 == 2:
            for y in range(bottoms[x] + 2, bottoms[x] + H):
                c.set(ox + x, y, C("19332d") if x < W // 2 else C("10141f"))
    for _ in range(9):
        x = rng.randrange(2, W - 2)
        c.set(ox + x, bottoms[x] + rng.randint(3, H - 1), C("602c2c"))
    c.outline_auto()
    return c, (3 + W // 2, oy + H + D // 2), ["diamond", 19.0, 10.0]

def draw_rubble(rng: random.Random, size: int) -> tuple[Canvas, tuple, list]:
    w = (34, 48, 60)[size]
    hmax = (6, 9, 13)[size]
    c = Canvas(w + 4, hmax + 14)
    grays = [C("202e37"), C("394a50"), C("577277"), C("819796")]
    cx = w // 2 + 2
    for x in range(4, w):
        h = int(hmax * (1 - ((x - cx) / (w / 2 - 1)) ** 2)) + rng.randint(-1, 1)
        for y in range(c.h - 3 - max(0, h), c.h - 2):
            t = rng.random()
            c.set(x, y, grays[1] if t < 0.5 else (grays[0] if t < 0.8 else grays[2]))
    for _ in range(rng.randint(6, 8 + 3 * size)):
        x, y = rng.randrange(6, w - 4), rng.randrange(c.h - 5 - hmax, c.h - 3)
        c.set(x, y, grays[3])
        c.set(x + 1, y, grays[2])
        c.set(x, y + 1, grays[1])
    for _ in range(2 + size):
        x, y = rng.randrange(6, w - 6), rng.randrange(c.h - 4 - hmax, c.h - 3)
        c.set(x, y, C("884b2b"))
        c.set(x + 1, y, C("602c2c"))
    for _ in range(1 + size):
        x = rng.randrange(8, w - 8)
        y = c.h - 4 - rng.randrange(2, max(3, hmax))
        for i in range(rng.randint(4, 7)):
            c.set(x + i, y - i // 2, C("602c2c"))
    c.outline_auto()
    return c, (cx, c.h - 4), None

def draw_pillar(rng: random.Random, kind: str) -> tuple[Canvas, tuple, list]:
    if kind == "fallen":
        c = Canvas(52, 20)
        for i in range(44):
            x = 4 + i
            sh = i // 16
            for y in range(6 + sh, 14 + sh):
                t = (y - 6 - sh) / 8.0
                col = CONC_L1 if t < 0.3 else (CONC_BASE if t < 0.8 else CONC_D1)
                if rng.random() < 0.06:
                    col = CONC_D1
                c.set(x, y, col)
        for y in range(7, 13):  # broken end
            c.set(3, y, CONC_D1)
            c.set(2, y, CONC_D2)
        for i in range(3):
            c.set(48 + i, 9 + i % 2, C("602c2c"))
        c.outline_auto()
        return c, (26, 16), ["diamond", 22.0, 5.0]
    h = 44 if kind == "tall" else 26
    c = Canvas(18, h + 10)
    for y in range(6, h + 4):
        for x in range(4, 14):
            col = CONC_L1 if x < 8 else (CONC_BASE if x < 12 else CONC_D1)
            if rng.random() < 0.08:
                col = CONC_D1
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
    for y in range(h + 2, h + 6):
        for x in range(2, 16):
            c.set(x, y, CONC_BASE if x < 9 else CONC_D1)
    c.outline_auto()
    return c, (9, h + 4), ["circle", 6.0]

def prop_inventory() -> tuple[dict, dict]:
    """Returns ({name: (canvas, origin, collider)}, {family: [names]})."""
    props: dict = {}
    families: dict[str, list[str]] = {}

    def fam(family: str, idx: int, made) -> None:
        name = f"{family}_{idx}"
        props[name] = made
        families.setdefault(family, []).append(name)

    for i in range(6):
        rng = random.Random(f"{SEED}:barrel:{i}")
        style = ("rust", "rust", "olive", "steel", "rust", "olive")[i]
        fallen = i >= 4
        fam("barrel", i, draw_barrel(rng, style, rng.randint(24, 30),
                                     rng.randint(8, 10), fallen))
    for i in range(6):
        rng = random.Random(f"{SEED}:crate:{i}")
        fam("crate", i, draw_crate(rng, rng.choice((24, 28, 32)), rng.randint(10, 15),
                                   i % 2, damaged=(i in (2, 5)), stencil=(i in (0, 3))))
    for i in range(4):
        rng = random.Random(f"{SEED}:cyl:{i}")
        color = ("steel", "red", "gray", "steel")[i]
        fam("cylinder", i, draw_cylinder(rng, color, rng.randint(30, 36), toppled=(i == 3)))
    for i in range(4):
        rng = random.Random(f"{SEED}:tires:{i}")
        fam("tires", i, draw_tires(rng, (3, 2, 1, 1)[i], single=(i == 3)))
    for i in range(3):
        rng = random.Random(f"{SEED}:pallet:{i}")
        fam("pallet", i, draw_pallet(rng, broken=(i == 1), stacked=(i == 2)))
    for i in range(2):
        rng = random.Random(f"{SEED}:dumpster:{i}")
        fam("dumpster", i, draw_dumpster(rng, lid_open=(i == 1)))
    for i in range(4):
        rng = random.Random(f"{SEED}:rubble:{i}")
        fam("rubble", i, draw_rubble(rng, min(i, 2)))
    for i, kind in enumerate(("tall", "snapped", "fallen")):
        rng = random.Random(f"{SEED}:pillar:{i}")
        fam("pillar", i, draw_pillar(rng, kind))
    return props, families

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

SKIN, SKIN_SH = C("d7b594"), C("c09473")
JKT_L, JKT, JKT_D = C("468232"), C("25562e"), C("19332d")
PANT, PANT_D = C("202e37"), C("151d28")
BOOT, BOOT_D = C("341c27"), C("10141f")
BEANIE, BEANIE_D = C("394a50"), C("202e37")
PACK, PACK_D = C("7a4841"), C("4d2b32")
STRAP = C("341c27")

CX, FEET = 16, 37
WALK_FRAMES = 6

BOB = {0: 0, 1: 0, 2: -1, 3: -1, 4: 0, 5: -1, 6: -1}
SIDE_STRIDE = {
    0: (0, 0, 0, 0),
    1: (3, -3, 0, 0), 2: (2, -2, 0, 1), 3: (0, 0, 0, 2),
    4: (-3, 3, 0, 0), 5: (-2, 2, 1, 0), 6: (0, 0, 2, 0),
}
STEP_LIFT = {
    0: (0, 0),
    1: (0, 2), 2: (0, 1), 3: (0, 0),
    4: (2, 0), 5: (1, 0), 6: (0, 0),
}
SIDE_SWING = {0: 0, 1: -2, 2: -1, 3: 0, 4: 2, 5: 1, 6: 0}
FRONT_SWING = {0: 0, 1: 1, 2: 1, 3: 0, 4: -1, 5: -1, 6: 0}


def draw_head(c: Canvas, view: str, bob: int) -> None:
    y0 = 10 + bob
    if view == "front":
        c.rect(CX - 4, y0, CX + 3, y0 + 3, BEANIE)
        c.hline(CX - 4, CX + 3, y0 + 3, BEANIE_D)
        c.rect(CX - 4, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.vline(CX + 3, y0 + 4, y0 + 7, SKIN_SH)
        c.hline(CX - 4, CX + 3, y0 + 7, SKIN_SH)
        c.set(CX - 2, y0 + 5, OUTLINE)
        c.set(CX + 1, y0 + 5, OUTLINE)
    elif view == "front34":
        c.rect(CX - 3, y0, CX + 4, y0 + 3, BEANIE)
        c.hline(CX - 3, CX + 4, y0 + 3, BEANIE_D)
        c.rect(CX - 3, y0 + 4, CX + 4, y0 + 7, SKIN)
        c.vline(CX - 3, y0 + 4, y0 + 7, SKIN_SH)
        c.hline(CX - 3, CX + 4, y0 + 7, SKIN_SH)
        c.set(CX, y0 + 5, OUTLINE)
        c.set(CX + 3, y0 + 5, OUTLINE)
    elif view == "side":
        c.rect(CX - 3, y0, CX + 3, y0 + 3, BEANIE)
        c.hline(CX - 3, CX + 3, y0 + 3, BEANIE_D)
        c.rect(CX - 3, y0 + 4, CX - 1, y0 + 7, SKIN_SH)
        c.rect(CX, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.set(CX + 4, y0 + 5, SKIN)
        c.set(CX + 4, y0 + 6, SKIN_SH)
        c.set(CX + 2, y0 + 5, OUTLINE)
        c.hline(CX - 3, CX + 3, y0 + 7, SKIN_SH)
    elif view == "back34":
        c.rect(CX - 3, y0, CX + 4, y0 + 4, BEANIE)
        c.hline(CX - 3, CX + 4, y0 + 4, BEANIE_D)
        c.rect(CX - 3, y0 + 5, CX + 4, y0 + 7, BEANIE_D)
        c.set(CX + 4, y0 + 6, SKIN_SH)
    elif view == "back":
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
    # both arms the same jacket tone: asymmetric arm shading reads as a bug
    # at this size, and mirrored direction rows make it jump sides
    y0 = 19 + bob
    if view in ("front", "back"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = CX + (side * 6) - (1 if side < 0 else 0)
            yy = y0 + (1 if sw > 0 else 0)
            c.rect(x, yy, x + 1, yy + 8, JKT)
            c.rect(x, yy + 9, x + 1, yy + 10, SKIN if view == "front" else SKIN_SH)
    elif view in ("front34", "back34"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = CX + (5 * side) + (0 if side < 0 else -1) + sw
            c.rect(x, y0, x + 1, y0 + 8, JKT)
            c.rect(x, y0 + 9, x + 1, y0 + 10, SKIN)
    else:
        x = CX + 1 + SIDE_SWING[frame]
        c.rect(x, y0, x + 1, y0 + 8, JKT)
        c.rect(x, y0 + 9, x + 1, y0 + 10, SKIN)


def draw_legs(c: Canvas, view: str, frame: int) -> None:
    if view in ("front", "front34", "back", "back34"):
        lifts = STEP_LIFT[frame]
        for (x0, lift, pcol) in ((CX - 4, lifts[0], PANT), (CX + 1, lifts[1], PANT_D)):
            dy = -lift
            c.rect(x0, 28, x0 + 2, 33 + dy, pcol)
            c.rect(x0, 34 + dy, x0 + 2, 36 + dy, BOOT)
            c.hline(x0, x0 + 2, FEET + dy, BOOT_D)
    else:
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

# ------------------------------------------------------------ menu assets ----

def make_title() -> Image.Image:
    """Big SPOILS wordmark for the main menu, two-tone + shadow."""
    font5x7 = {
        "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
        "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
        "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
        "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
        "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    }
    word = "SPOILS"
    scale = 6
    w1, h1 = len(word) * 6 - 1, 7
    text = Image.new("RGBA", (w1 + 2, h1 + 2), (0, 0, 0, 0))
    for i, ch in enumerate(word):
        for y, row in enumerate(font5x7[ch]):
            for x, cell in enumerate(row):
                if cell == "#":
                    col = C("ebede9") if y < 4 else C("819796")
                    text.putpixel((i * 6 + x + 1, y + 1), col)
    px = text.load()
    for y in range(text.height):  # outline
        for x in range(text.width):
            if px[x, y][3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < text.width and 0 <= ny < text.height and \
                            px[nx, ny][3] > 0 and px[nx, ny][:3] != OUTLINE[:3]:
                        px[x, y] = OUTLINE
                        break
    big = text.resize((text.width * scale, text.height * scale), Image.NEAREST)
    title = Image.new("RGBA", (big.width + 4, big.height + 10), (0, 0, 0, 0))
    shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
    spx, bpx = shadow.load(), big.load()
    for y in range(big.height):
        for x in range(big.width):
            if bpx[x, y][3] > 0:
                spx[x, y] = (9, 10, 20, 140)
    title.paste(shadow, (4, 8), shadow)
    title.paste(big, (0, 0), big)
    return title

def make_vignette() -> Image.Image:
    """Soft radial darkening for menus. Smooth alpha by design (not palette)."""
    w, h = 960, 544
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            dx = (x - w / 2) / (w * 0.62)
            dy = (y - h / 2) / (h * 0.62)
            d = dx * dx + dy * dy
            a = int(max(0.0, min(1.0, (d - 0.25) * 1.6)) * 205)
            if a > 0:
                px[x, y] = (9, 10, 20, a)
    return img

def make_dust() -> Image.Image:
    img = Image.new("RGBA", (3, 3), (0, 0, 0, 0))
    img.putpixel((1, 1), (255, 255, 255, 255))
    for p in ((0, 1), (2, 1), (1, 0), (1, 2)):
        img.putpixel(p, (255, 255, 255, 90))
    return img

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

    manifest: dict = {"tile": [64, 32], "wall_h": WALL_H,
                      "floors": {}, "props": {}, "families": {}, "char": {}}

    floors, coords = make_floors_atlas()
    assert_palette(floors, "floors")
    floors.save(OUT / "floors.png")
    manifest["floors"] = coords

    entries: dict = {}
    props, families = prop_inventory()
    for name, (canvas, origin, collider) in props.items():
        entries[name] = (canvas, origin, collider)
    for name, canvas in wall_piece_inventory().items():
        entries[name] = (canvas, WALL_ORIGIN, ["diamond", 32.0, 16.0])
    entries["roof_tile_0"] = (make_roof_tile(0), (32, 16), None)
    entries["roof_tile_1"] = (make_roof_tile(1), (32, 16), None)
    entries["roof_vent"] = (make_roof_vent(), (12, 15), None)
    entries["roof_hatch"] = (make_roof_hatch(), (10, 8), None)
    entries["shadow"] = (make_shadow(), (12, 6), None)

    grabber = Canvas(8, 12)  # HSlider knob for the UI theme
    grabber.rect(0, 0, 7, 11, C("090a14"))
    grabber.rect(1, 1, 6, 10, C("c7cfcc"))
    grabber.rect(1, 9, 6, 10, C("819796"))
    entries["ui_grabber"] = (grabber, (4, 6), None)

    for name, (canvas, origin, collider) in entries.items():
        if name != "shadow":
            assert_palette(canvas.img, name)
        canvas.img.save(OUT / f"{name}.png")
        manifest["props"][name] = {
            "size": [canvas.w, canvas.h], "origin": list(origin), "collider": collider}
    manifest["families"] = families

    sheet = make_char_sheet()
    assert_palette(sheet, "char")
    sheet.save(OUT / "char.png")
    manifest["char"] = {
        "frame": [32, 40], "cols": 1 + WALK_FRAMES, "origin": [16, 37],
        "dirs": [d for d, _, _ in DIR_VIEWS],
    }

    make_title().save(OUT / "title.png")          # white/palette mix, UI-tinted
    make_vignette().save(OUT / "vignette.png")    # soft alpha by design
    make_dust().save(OUT / "dust.png")            # white, tinted at runtime

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    import gen_font  # regenerate the UI font too (the purge above removed it)
    gen_font.main()

    # ---- contact sheet ----
    def x3(img: Image.Image) -> Image.Image:
        return img.resize((img.width * 3, img.height * 3), Image.NEAREST)

    pad = 12
    show_walls = ["wall_brick_a_m0000", "wall_brick_a_m1100", "wall_brick_a_win_x_0",
                  "wall_brick_a_win_x_1", "wall_brick_a_win_x_2", "wall_brick_a_win_y_0",
                  "wall_brick_a_broken_a", "wall_brick_b_m0000", "wall_brick_b_win_y_1",
                  "roof_vent", "roof_hatch", "roof_tile_0"]
    fam_show = [n for fam in families.values() for n in fam]
    rows_imgs = [
        [x3(floors)],
        [x3(entries[n][0].img) for n in show_walls],
        [x3(entries[n][0].img) for n in fam_show[:16]],
        [x3(entries[n][0].img) for n in fam_show[16:]],
        [x3(sheet), make_title()],
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

    print(f"OK: wrote {len(entries) + 6} files to {OUT}")

if __name__ == "__main__":
    main()
