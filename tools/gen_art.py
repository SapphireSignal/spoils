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
# 0.4.1: thin EDGE walls (user: buildings must be walls, not full-tile blocks).
# A segment stands on one tile edge: base line spans (-16,-8)->(16,8) local px
# for the x-axis type ("seg_x", lit SW face) or (-16,8)->(16,-8) for the
# y-axis type ("seg_y", shadowed SE face). Extruded WALL_H up, with an ~8px
# coping on top. Corner/door joints are covered by square posts, so segments
# need no endcap variants. Brick courses repeat with period 16 along the edge,
# so adjacent segments continue each other's pattern seamlessly.

WALL_H = 40
SEG_THICK = 7  # coping depth in screen px

BRICK_STYLES = {
    # two clearly different materials (user: buildings must not match)
    "brick_a": {"x": ("884b2b", "602c2c"), "y": ("7a4841", "4d2b32")},   # red brick
    "brick_b": {"x": ("577277", "394a50"), "y": ("394a50", "202e37")},   # gray masonry
}

# window variants: (start i along edge, top row in face coords, w, h, boarded)
SEG_WINDOWS = [
    (10, 8, 12, 14, False),  # tall
    (7, 12, 18, 9, False),   # wide + low
    (11, 10, 10, 10, True),  # small, boarded up
]

def _seg_base_fy(axis: str, i: int) -> int:
    # base line row for edge-param i (0..31), relative to segment origin
    return (-8 + i // 2) if axis == "x" else (8 - (i + 1) // 2)

def _seg_brick(rng: random.Random, base, mortar, i: int, fy: int) -> tuple:
    course = fy // 4
    if fy % 4 == 3:
        if (i + fy) % 2 == 0:
            return mortar
    elif (i + (8 if course % 2 else 0)) % 16 == 0 and rng.random() < 0.55:
        return mortar
    elif rng.random() < 0.04:
        return mortar
    return base

def make_wall_segment(style: str, axis: str, window_variant: int = -1,
                      broken_seed: int = -1) -> tuple[Canvas, tuple, list]:
    rng = random.Random(f"{SEED}:seg:{style}:{axis}:{window_variant}:{broken_seed}")
    base_col, mortar_col = (C(n) for n in BRICK_STYLES[style][axis])
    # canvas: 32 wide edge + coping overhang + outline margins
    c = Canvas(48, 66)
    ox = 8 if axis == "x" else 8  # local origin x inside canvas
    oy = 56
    cop_dx = SEG_THICK if axis == "x" else -SEG_THICK  # coping goes to the back

    heights: list[int] = []
    if broken_seed >= 0:
        h = rng.randint(8, 20)
        for i in range(32):
            if i % rng.choice((3, 4, 5)) == 0:
                h = max(5, min(24, h + rng.choice((-6, -4, 4, 6))))
            heights.append(h)
    else:
        heights = [WALL_H] * 32

    for i in range(32):
        x = ox + 16 + (-16 + i)
        fy_base = oy + _seg_base_fy(axis, i)
        h = heights[i]
        for k in range(h):
            fy = WALL_H - 1 - k if broken_seed >= 0 else k  # face-local row
            y = fy_base - h + 1 + k
            face_row = (y - (fy_base - WALL_H + 1))
            c.set(x, y, _seg_brick(rng, base_col, mortar_col, i, face_row))
        if broken_seed >= 0:  # broken lip
            cap_y = fy_base - h
            c.set(x, cap_y, C("819796") if rng.random() < 0.5 else base_col)
        else:
            # coping: stepped parallelogram toward the back
            for j in range(abs(cop_dx) + 1):
                jx = x + (j if cop_dx > 0 else -j)
                jy = fy_base - WALL_H - ((j + 1) // 2 if axis == "x" else -((j + 1) // 2))
                jy = fy_base - WALL_H - ((j + 1) // 2)
                r = rng.random()
                col = CONC_L1
                if r < 0.06:
                    col = CONC_BASE
                elif r < 0.09:
                    col = CONC_L2
                c.set(jx, jy, col)
            if i % 2 == 0:  # light crease where coping meets the face
                c.set(x, fy_base - WALL_H, CONC_L2)

    if window_variant >= 0:
        wi, top, w, h, boarded = SEG_WINDOWS[window_variant]
        for i in range(wi, min(32, wi + w)):
            x = ox + 16 + (-16 + i)
            fy_base = oy + _seg_base_fy(axis, i)
            face_top = fy_base - WALL_H + 1
            for fy in range(top, top + h):
                c.set(x, face_top + fy, C("090a14"))
            c.set(x, face_top + top - 1, C("341c27"))   # lintel
            c.set(x, face_top + top + h, C("819796"))   # sill
            if boarded:
                for bi, plank in enumerate(range(top + 1, top + h, 3)):
                    c.set(x, face_top + plank + ((i + bi) % 2),
                          C("884b2b") if (i + bi) % 2 else C("602c2c"))
        for i in (wi - 1, wi + w):  # jambs
            if 0 <= i < 32:
                x = ox + 16 + (-16 + i)
                fy_base = oy + _seg_base_fy(axis, i)
                face_top = fy_base - WALL_H + 1
                for fy in range(top - 1, top + h + 1):
                    c.set(x, face_top + fy, C("341c27"))

    c.outline_auto()
    origin = (ox + 16, oy)
    # thin collision parallelogram along the base line
    if axis == "x":
        a, b = (-16.0, -8.0), (16.0, 8.0)
        n = (-2.4, 4.8)  # ~5px thick, perpendicular-ish
    else:
        a, b = (-16.0, 8.0), (16.0, -8.0)
        n = (2.4, 4.8)
    poly = [a[0] - n[0], a[1] - n[1], b[0] - n[0], b[1] - n[1],
            b[0] + n[0], b[1] + n[1], a[0] + n[0], a[1] + n[1]]
    return c, origin, ["poly", poly]

def make_wall_post(style: str) -> tuple[Canvas, tuple, list]:
    rng = random.Random(f"{SEED}:post:{style}")
    c = Canvas(18, 62)
    lit, dark = (C(n) for n in BRICK_STYLES[style]["x"])
    _, darker = (C(n) for n in BRICK_STYLES[style]["y"])
    bottoms = iso_prism(c, 2, 1, 12, 6, WALL_H + 4, lit, lit, dark)
    for x in range(12):  # concrete cap
        y = bottoms[x]
        c.set(2 + x, y, CONC_L1)
        c.set(2 + x, y - 1, CONC_L1 if x % 2 else CONC_L2)
    for x in range(12):  # course shading
        for y in range(bottoms[x] + 2, bottoms[x] + WALL_H + 4, 4):
            if rng.random() < 0.6:
                c.set(2 + x, y, dark if x < 6 else darker)
    c.outline_auto()
    return c, (8, 1 + WALL_H + 4 + 3), ["circle", 4.0]

def wall_piece_inventory() -> dict[str, tuple[Canvas, tuple, list]]:
    pieces: dict[str, tuple[Canvas, tuple, list]] = {}
    for style in BRICK_STYLES:
        for axis in ("x", "y"):
            pieces[f"seg_{style}_{axis}"] = make_wall_segment(style, axis)
            for v in range(len(SEG_WINDOWS)):
                pieces[f"seg_{style}_{axis}_win_{v}"] = make_wall_segment(style, axis, v)
            for b in range(2):
                pieces[f"seg_{style}_{axis}_broken_{b}"] = make_wall_segment(
                    style, axis, -1, b)
        pieces[f"post_{style}"] = make_wall_post(style)
    return pieces

# ----------------------------------------------------------------- roofs -----
# One purpose-built roof slab per building size (user call: the tile-assembled
# roof never sat right on the thin walls). The slab spans the interior plus a
# small overhang so it caps the walls exactly; fascia trim on the lower edges,
# vents/hatch baked in. The game fades it for the interior reveal.

ROOF_TONES = {  # different shades of "black" per building
    "charcoal": ("151d28", "10141f", "394a50"),
    "umber": ("241527", "10141f", "4d2b32"),
}

def make_building_roof(tiles_w: int, tiles_h: int,
                       tone: str) -> tuple[Canvas, tuple, list | None]:
    rng = random.Random(f"{SEED}:roof:{tiles_w}x{tiles_h}:{tone}")
    base_col, dark_col, lite_col = (C(n) for n in ROOF_TONES[tone])
    margin = 8
    span_w = (tiles_w + tiles_h) * 32 + 2 * margin
    span_h = (tiles_w + tiles_h) * 16 + 2 * margin
    c = Canvas(span_w, span_h)
    off_x = (tiles_h - 1) * 32 + margin  # canvas x of cell (0,0)'s diamond
    off_y = margin

    mask: set = set()
    for cy in range(tiles_h):
        for cx in range(tiles_w):
            sx = off_x + (cx - cy) * 32
            sy = off_y + (cx + cy) * 16
            for y in range(32):
                s = diamond_span(y)
                if s:
                    for x in range(s[0], s[1] + 1):
                        mask.add((sx + x, sy + y))
    # single 2px dilation: the roof edge sits flush on the wall plane
    grown = set(mask)
    for (x, y) in mask:
        for dx, dy in ((2, 1), (-2, 1), (2, -1), (-2, -1), (1, 0), (-1, 0)):
            grown.add((x + dx, y + dy))
    mask = grown

    for (x, y) in mask:
        r = rng.random()
        col = base_col
        if r < 0.09:
            col = dark_col
        elif r < 0.13:
            col = lite_col
        c.set(x, y, col)
    # a few tar patch blobs
    for i in range(3):
        patch = blob(rng, off_x + (tiles_w - 1) * 16 + rng.randint(-40, 40),
                     off_y + (tiles_w + tiles_h) * 8 + rng.randint(-30, 30),
                     rng.randint(30, 70), mask)
        for (x, y) in patch:
            c.set(x, y, dark_col)
    # edges: highlight on upper rims, fascia trim hanging off lower rims
    for (x, y) in list(mask):
        if (x, y - 1) not in mask:
            c.set(x, y, lite_col)
        if (x, y + 1) not in mask:
            c.set(x, y, dark_col)
            c.set(x, y + 1, INK)
            c.set(x, y + 2, INK)
    # vents + hatch, kept off the edges
    bottoms_hint = off_y + (tiles_w + tiles_h) * 8
    vent = Canvas(24, 22)
    vb = iso_prism(vent, 2, 1, 20, 10, 7, CONC_BASE, CONC_D1, CONC_D2)
    for x in range(3, 17):
        if x % 3 != 0:
            vent.set(2 + x, vb[x] + 3, INK)
            vent.set(2 + x, vb[x] + 5, INK)
    vent.outline_auto()
    hatch = Canvas(20, 14)
    hb = iso_prism(hatch, 2, 1, 16, 8, 2, CONC_D1, CONC_D2, INK)
    for x in range(4, 12):
        hatch.set(2 + x, hb[x] - 1, CONC_BASE)
    hatch.outline_auto()
    c.img.alpha_composite(vent.img, (off_x + 8, bottoms_hint - 30))
    c.img.alpha_composite(hatch.img, (off_x - (tiles_h - 2) * 32, bottoms_hint - 4))
    c.px = c.img.load()
    c.outline_auto()

    # origin = center of the SOUTH corner cell (w-1, h-1)
    south_cx = off_x + (tiles_w - 1 - (tiles_h - 1)) * 32 + 32
    south_cy = off_y + (tiles_w - 1 + tiles_h - 1) * 16 + 16
    return c, (south_cx, south_cy), None

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
HAIR, HAIR_D = C("4d2b32"), C("341c27")
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
        c.rect(CX - 4, y0, CX + 3, y0 + 2, HAIR)
        c.vline(CX + 3, y0, y0 + 2, HAIR_D)
        for i, x in enumerate(range(CX - 4, CX + 4)):  # jagged fringe
            if i % 3 != 1:
                c.set(x, y0 + 3, HAIR if x < CX + 2 else HAIR_D)
        c.rect(CX - 4, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.set(CX - 4, y0 + 3, HAIR)
        c.set(CX - 4, y0 + 4, HAIR)      # temples
        c.set(CX + 3, y0 + 4, HAIR_D)
        c.vline(CX + 3, y0 + 5, y0 + 7, SKIN_SH)
        c.hline(CX - 4, CX + 3, y0 + 7, SKIN_SH)
        c.set(CX - 2, y0 + 5, OUTLINE)
        c.set(CX + 1, y0 + 5, OUTLINE)
    elif view == "front34":
        c.rect(CX - 3, y0, CX + 4, y0 + 2, HAIR)
        c.vline(CX + 4, y0, y0 + 2, HAIR_D)
        for i, x in enumerate(range(CX - 3, CX + 5)):
            if i % 3 != 1:
                c.set(x, y0 + 3, HAIR if x < CX + 3 else HAIR_D)
        c.rect(CX - 3, y0 + 4, CX + 4, y0 + 7, SKIN)
        c.set(CX - 3, y0 + 3, HAIR)
        c.set(CX - 3, y0 + 4, HAIR)
        c.vline(CX - 3, y0 + 5, y0 + 7, SKIN_SH)
        c.hline(CX - 3, CX + 4, y0 + 7, SKIN_SH)
        c.set(CX, y0 + 5, OUTLINE)
        c.set(CX + 3, y0 + 5, OUTLINE)
    elif view == "side":
        c.rect(CX - 3, y0, CX + 3, y0 + 2, HAIR)
        c.rect(CX - 3, y0 + 3, CX - 1, y0 + 6, HAIR)   # back of head
        c.vline(CX - 3, y0 + 3, y0 + 6, HAIR_D)
        c.set(CX + 2, y0 + 3, HAIR)                     # fringe tip
        c.set(CX + 3, y0 + 3, HAIR_D)
        c.rect(CX, y0 + 4, CX + 3, y0 + 7, SKIN)
        c.set(CX - 1, y0 + 7, SKIN_SH)                  # jaw under hair
        c.set(CX + 4, y0 + 5, SKIN)
        c.set(CX + 4, y0 + 6, SKIN_SH)
        c.set(CX + 2, y0 + 5, OUTLINE)
        c.hline(CX, CX + 3, y0 + 7, SKIN_SH)
    elif view == "back34":
        # no exposed neck from behind: hair tapers straight into the collar,
        # mirroring the front view (which has no visible neck either)
        c.rect(CX - 3, y0, CX + 4, y0 + 6, HAIR)
        c.vline(CX + 4, y0 + 1, y0 + 6, HAIR_D)
        c.set(CX + 4, y0 + 6, SKIN_SH)                  # ear sliver
        c.rect(CX - 3, y0 + 7, CX + 4, y0 + 7, HAIR_D)
    elif view == "back":
        c.rect(CX - 4, y0, CX + 3, y0 + 6, HAIR)
        c.vline(CX + 3, y0 + 1, y0 + 6, HAIR_D)
        c.rect(CX - 4, y0 + 7, CX + 3, y0 + 7, HAIR_D)


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
    # the torso spans CX-4..CX+3 (even width on an odd center), so arm columns
    # must be placed off the body EDGES to be symmetric, not off CX
    y0 = 19 + bob
    if view in ("front", "back"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = (CX - 6) if side < 0 else (CX + 4)
            yy = y0 + (1 if sw > 0 else 0)
            c.rect(x, yy, x + 1, yy + 8, JKT)
            c.rect(x, yy + 9, x + 1, yy + 10, SKIN if view == "front" else SKIN_SH)
    elif view in ("front34", "back34"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = ((CX - 5) if side < 0 else (CX + 4)) + sw
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

def _render_word(word: str, upper_col, lower_col) -> Image.Image:
    """Render a word with the lowercase UI font glyphs at 1x, outlined."""
    import gen_font
    widths = [len(gen_font.GLYPHS[ch][0]) for ch in word]
    w1 = sum(w + 1 for w in widths) - 1
    text = Image.new("RGBA", (w1 + 2, gen_font.GLYPH_H + 2), (0, 0, 0, 0))
    cx = 1
    for ch, gw in zip(word, widths):
        for y, row in enumerate(gen_font.GLYPHS[ch]):
            for x, cell in enumerate(row):
                if cell == "#":
                    text.putpixel((cx + x, y + 1), upper_col if y < 5 else lower_col)
        cx += gw + 1
    px = text.load()
    for y in range(text.height):
        for x in range(text.width):
            if px[x, y][3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < text.width and 0 <= ny < text.height and \
                            px[nx, ny][3] > 0 and px[nx, ny][:3] != OUTLINE[:3]:
                        px[x, y] = OUTLINE
                        break
    return text

def make_title() -> Image.Image:
    """Big lowercase wordmark for the main menu, two-tone + drop shadow."""
    text = _render_word("spoils", C("ebede9"), C("819796"))
    scale = 6
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

# ---------------------------------------------------------- menu backdrops ---
# Four rotating main-menu scenes, 960x544 (covers the expanded view on any
# reasonable display; important content stays inside the central 640x360).
# Rendered in world space at 1:1 so they stay pixel-crisp at any window size.

SCENE_W, SCENE_H = 960, 544

def _scene_base() -> Canvas:
    c = Canvas(SCENE_W, SCENE_H)
    return c

def _dither_fill(c: Canvas, x0: int, y0: int, x1: int, y1: int, col, density: float,
                 rng: random.Random) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if rng.random() < density:
                c.set(x, y, col)

def _vgrad(c: Canvas, bands: list[tuple]) -> None:
    """bands: [(until_y, color)] — vertical bands with dithered borders."""
    prev_y = 0
    for bi, (until_y, col) in enumerate(bands):
        for y in range(prev_y, until_y):
            for x in range(SCENE_W):
                c.set(x, y, col)
        if bi + 1 < len(bands):  # dither the seam into the next band
            nxt = bands[bi + 1][1]
            for y in range(until_y - 6, until_y + 6):
                for x in range(SCENE_W):
                    if (x * 7 + y * 13) % 11 < (y - (until_y - 6)):
                        c.set(x, y, nxt)
        prev_y = until_y

def _paste(c: Canvas, img: Image.Image, x: int, y: int) -> None:
    c.img.alpha_composite(img, (x, y))
    c.px = c.img.load()

def make_scene_hoard(props: dict) -> Canvas:
    """Concept 1: the master hoard — treasure vault with a lit chest."""
    rng = random.Random(f"{SEED}:scene:hoard")
    c = _scene_base()
    _vgrad(c, [(140, C("090a14")), (330, C("10141f")), (SCENE_H, C("241527"))])
    # cave floor
    for y in range(360, SCENE_H):
        for x in range(SCENE_W):
            c.set(x, y, C("341c27"))
    speckle(c, rng, {(x, y) for y in range(360, SCENE_H) for x in range(0, SCENE_W)},
            [C("241527"), C("4d2b32")], [0.10, 0.05])
    # cave walls closing in from the sides + stalactites
    for x in range(SCENE_W):
        edge = int(90 * (1 - min(x, SCENE_W - 1 - x) / 300.0))
        if edge > 0:
            for y in range(SCENE_H):
                if min(x, SCENE_W - 1 - x) < edge - y // 8:
                    c.set(x, y, C("151d28"))
    for i in range(14):
        sx = rng.randrange(60, SCENE_W - 60)
        ln = rng.randint(14, 44)
        for y in range(ln):
            half = max(1, (ln - y) // 5)
            for x in range(sx - half, sx + half):
                c.set(x, y, C("151d28"))
    # light shaft over the chest: random dither, denser toward the center
    cx = SCENE_W // 2
    for y in range(0, 300):
        half = 26 + y // 4
        for x in range(cx - half, cx + half):
            t = 1.0 - abs(x - cx) / float(half)
            if rng.random() < 0.05 + 0.06 * t:
                c.set(x, y, C("e7d5b3") if rng.random() < 0.3 else C("d7b594"))
    # treasure mound
    for x in range(cx - 210, cx + 210):
        h = int(95 * (1 - ((x - cx) / 210.0) ** 2)) + rng.randint(-2, 2)
        for y in range(400 - h, 400):
            r = rng.random()
            col = C("de9e41")
            if r < 0.28:
                col = C("e8c170")
            elif r < 0.40:
                col = C("be772b")
            elif r < 0.43:
                col = C("ebede9")
            c.set(x, y + 30, col)
    # loose coins on the floor
    for i in range(50):
        px_, py = rng.randrange(cx - 300, cx + 300), rng.randrange(430, SCENE_H - 10)
        c.rect(px_, py, px_ + 2, py + 1, C("e8c170"))
        c.set(px_ + 1, py + 2, C("be772b"))
    # the chest on top of the mound
    bx, by = cx - 45, 262
    c.rect(bx, by + 26, bx + 90, by + 62, C("602c2c"))          # body
    for yy in range(by + 26, by + 62, 8):
        c.hline(bx, bx + 90, yy, C("341c27"))
    c.rect(bx, by + 26, bx + 90, by + 30, C("de9e41"))           # gold trim
    c.rect(bx, by + 56, bx + 90, by + 60, C("de9e41"))
    c.rect(bx + 40, by + 30, bx + 50, by + 42, C("e8c170"))      # clasp
    c.rect(bx - 6, by, bx + 96, by + 14, C("884b2b"))            # open lid
    c.rect(bx - 6, by + 10, bx + 96, by + 14, C("de9e41"))
    for i in range(240):                                          # glow burst
        gx = bx + 45 + rng.randint(-52, 52)
        gy = by + 18 + rng.randint(-16, 12)
        if rng.random() < 0.6:
            c.set(gx, gy, C("e8c170"))
        else:
            c.set(gx, gy, C("ebede9"))
    return c

def make_scene_scrapyard(props: dict) -> tuple[Canvas, Canvas]:
    """Concept 2: neon scrapyard. Returns (base, neon overlay for flicker)."""
    rng = random.Random(f"{SEED}:scene:scrap")
    c = _scene_base()
    _vgrad(c, [(200, C("090a14")), (340, C("10141f")), (SCENE_H, C("151d28"))])
    # junk skyline
    for x in range(0, SCENE_W, 3):
        h = 40 + int(30 * abs(((x * 37) % 100) / 50 - 1)) + rng.randint(-6, 6)
        for y in range(260 - h, 262):
            c.rect(x, y, x + 2, y, C("10141f"))
    # ground
    for y in range(340, SCENE_H):
        for x in range(SCENE_W):
            c.set(x, y, C("202e37"))
    speckle(c, rng, {(x, y) for y in range(340, SCENE_H) for x in range(SCENE_W)},
            [C("151d28"), C("394a50")], [0.09, 0.04])
    # heaps of our own props
    def put(name: str, x: int, y: int) -> None:
        _paste(c, props[name][0].img, x, y)
    for i, (nm, px_, py) in enumerate([
            ("rubble_3", 90, 380), ("rubble_2", 210, 420), ("tires_0", 330, 396),
            ("barrel_1", 160, 356), ("barrel_4", 420, 452), ("crate_2", 520, 380),
            ("rubble_2", 640, 430), ("tires_3", 730, 380), ("barrel_0", 790, 420),
            ("cylinder_3", 260, 470), ("rubble_1", 850, 470), ("crate_5", 60, 460),
            ("tires_1", 590, 470), ("rubble_3", 460, 400)]):
        put(nm, px_, py)
    # broken robot slumped against a heap
    rx, ry = 660, 320
    c.rect(rx, ry, rx + 44, ry + 34, C("394a50"))
    c.rect(rx + 4, ry + 4, rx + 40, ry + 30, C("577277"))
    c.rect(rx + 8, ry + 34, rx + 16, ry + 60, C("394a50"))      # slumped leg
    c.rect(rx + 30, ry + 34, rx + 38, ry + 52, C("202e37"))
    c.rect(rx - 14, ry + 10, rx, ry + 16, C("394a50"))          # hanging arm
    c.rect(rx + 14, ry + 12, rx + 30, ry + 22, C("090a14"))     # eye slot
    c.set(rx + 20, ry + 16, C("cf573c"))
    c.set(rx + 21, ry + 16, C("cf573c"))
    # sign pole + dark panel (lit text lives on the overlay)
    sx, sy = 150, 120
    c.rect(sx + 60, sy + 46, sx + 66, 360, C("151d28"))
    c.rect(sx - 8, sy - 8, sx + 136, sy + 46, C("10141f"))
    c.rect(sx - 8, sy - 8, sx + 136, sy - 6, C("394a50"))
    word = _render_word("spoils", C("411d31"), C("411d31"))  # off-state text
    ghost = word.resize((word.width * 4, word.height * 4), Image.NEAREST)
    _paste(c, ghost, sx + 6, sy - 2)
    # neon overlay: the lit sign text + halo, flickered at runtime
    lit = _render_word("spoils", C("df84a5"), C("c65197"))
    lit_big = lit.resize((lit.width * 4, lit.height * 4), Image.NEAREST)
    ov = Canvas(lit_big.width + 16, lit_big.height + 16)
    _paste(ov, lit_big, 8, 8)
    opx = ov.img.load()
    halo = []
    for y in range(ov.h):
        for x in range(ov.w):
            if opx[x, y][3] == 0:
                near = False
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-2, -1, 0, 1, 2):
                        p = ov.get(x + dx, y + dy)
                        if p[3] > 0 and p[:3] == C("c65197")[:3]:
                            near = True
                if near and (x + y) % 2 == 0:
                    halo.append((x, y))
    for (x, y) in halo:
        ov.set(x, y, C("7a367b"))
    return c, ov

def make_scene_overlook(props: dict, char_sheet: Image.Image) -> tuple[Canvas, Canvas]:
    """Concept 4: the overlook. Returns (base, drifting cloud strip)."""
    rng = random.Random(f"{SEED}:scene:overlook")
    c = _scene_base()
    _vgrad(c, [(150, C("151d28")), (230, C("1e1d39")), (300, C("253a5e")),
               (330, C("3c5e8b")), (SCENE_H, C("202e37"))])
    # pale sun through the murk
    sx, sy = 640, 180
    for y in range(sy - 22, sy + 22):
        for x in range(sx - 22, sx + 22):
            d = ((x - sx) / 22.0) ** 2 + ((y - sy) / 22.0) ** 2
            if d < 1.0 and (x + y) % 2 == 0:
                c.set(x, y, C("73bed3") if d > 0.4 else C("a4dddb"))
    # ruined city skyline on the horizon
    x = 0
    while x < SCENE_W:
        w = rng.randint(18, 44)
        h = rng.randint(20, 70)
        col = C("10141f") if rng.random() < 0.6 else C("151d28")
        for xx in range(x, min(SCENE_W, x + w)):
            top = 300 - h + (3 if (xx // 6) % 2 else 0)
            for y in range(top, 302):
                c.set(xx, y, col)
        if rng.random() < 0.5:  # a few dim lit windows
            for i in range(rng.randint(1, 3)):
                c.set(x + rng.randrange(2, max(3, w - 2)), 300 - rng.randrange(6, max(7, h - 4)),
                      C("de9e41") if rng.random() < 0.7 else C("cf573c"))
        x += w + rng.randint(2, 10)
    # wasteland midground
    for y in range(302, 420):
        for x in range(SCENE_W):
            c.set(x, y, C("202e37") if (x * 3 + y * 5) % 7 else C("151d28"))
    # cliff mass, foreground
    for x in range(SCENE_W):
        ch_ = 140 + int(50 * (x / SCENE_W)) + rng.randint(-2, 2)
        for y in range(SCENE_H - ch_, SCENE_H):
            c.set(x, y, C("151d28"))
        c.set(x, SCENE_H - ch_, C("394a50"))
        if rng.random() < 0.3:
            c.set(x, SCENE_H - ch_ + 1, C("202e37"))
    # scavenged gear + the raider looking out
    def put(name: str, x: int, y: int) -> None:
        _paste(c, props[name][0].img, x, y)
    put("crate_0", 236, 372)
    put("barrel_0", 352, 356)
    put("tires_2", 196, 396)
    raider = char_sheet.crop((0, 7 * 40, 32, 8 * 40))  # N row, idle: facing away
    raider2 = raider.resize((64, 80), Image.NEAREST)
    _paste(c, raider2, 292, 306)
    # cloud strip overlay (drifts at runtime)
    strip = Canvas(SCENE_W, 90)
    for i in range(16):
        bx = rng.randrange(0, SCENE_W)
        bw = rng.randint(60, 160)
        bh = rng.randint(8, 18)
        by = rng.randrange(4, 70)
        for y in range(by, by + bh):
            for x in range(bx, bx + bw):
                d = abs(y - (by + bh / 2)) / (bh / 2)
                if rng.random() < 0.5 * (1 - d):
                    strip.set(x % SCENE_W, y, C("1e1d39") if rng.random() < 0.7 else C("253a5e"))
    return c, strip

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
    for name, piece in wall_piece_inventory().items():
        entries[name] = piece
    entries["roof_7x5"] = make_building_roof(7, 5, "charcoal")  # building A
    entries["roof_6x5"] = make_building_roof(6, 5, "umber")     # building B
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

    # rotating main-menu backdrops (+ their animated overlay layers)
    scene_hoard = make_scene_hoard(entries)
    assert_palette(scene_hoard.img, "menu_hoard")
    scene_hoard.img.save(OUT / "menu_hoard.png")
    scrap_base, scrap_neon = make_scene_scrapyard(entries)
    assert_palette(scrap_base.img, "menu_scrapyard")
    scrap_base.img.save(OUT / "menu_scrapyard.png")
    scrap_neon.img.save(OUT / "menu_scrapyard_neon.png")
    over_base, over_clouds = make_scene_overlook(entries, sheet)
    assert_palette(over_base.img, "menu_overlook")
    over_base.img.save(OUT / "menu_overlook.png")
    over_clouds.img.save(OUT / "menu_overlook_clouds.png")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    import gen_font  # regenerate the UI font too (the purge above removed it)
    gen_font.main()

    # ---- contact sheet ----
    def x3(img: Image.Image) -> Image.Image:
        return img.resize((img.width * 3, img.height * 3), Image.NEAREST)

    pad = 12
    show_walls = ["seg_brick_a_x", "seg_brick_a_y", "seg_brick_a_x_win_0",
                  "seg_brick_a_x_win_1", "seg_brick_a_x_win_2", "seg_brick_a_y_win_0",
                  "seg_brick_a_x_broken_0", "post_brick_a", "seg_brick_b_x",
                  "seg_brick_b_y_win_1", "post_brick_b", "roof_6x5"]
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
