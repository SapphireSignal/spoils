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
        _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.032, 0.016)
    elif kind == "crack":
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.032, 0.016)
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
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.032, 0.016)
        core = blob(rng, 32 + rng.randint(-10, 10), 16 + rng.randint(-4, 4),
                    rng.randint(25, 50), region)
        for (x, y) in core:
            c.set(x, y, CONC_D1)
        for (x, y) in list(core):
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in region and (nx, ny) not in core and (nx + ny) % 2 == 0:
                    c.set(nx, ny, CONC_D1)
    elif kind == "moss":
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.032, 0.016)
        m = blob(rng, 32 + rng.randint(-12, 12), 16 + rng.randint(-5, 5),
                 rng.randint(20, 40), region)
        for (x, y) in m:
            if rng.random() < 0.65:
                c.set(x, y, C("19332d"))
            elif rng.random() < 0.3:
                c.set(x, y, C("25562e"))
    elif kind == "dirt":
        _floor_base(c, rng, C("341c27"), C("241527"), C("4d2b32"), 0.045, 0.07)
    elif kind == "dirt_blend":
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.032, 0.014)
        speckle(c, rng, region, [C("341c27"), C("4d2b32")], [0.09, 0.06])
    elif kind == "wood":
        # interior plank floor: boards run along one iso axis, seams + grain
        region = {(x, y) for y in range(32) for x in range(64) if in_diamond(x, y)}
        tones = [C("4d2b32"), C("341c27"), C("602c2c")]
        for (x, y) in region:
            board = (x + 2 * y) // 8
            col = tones[(board * 7 + variant * 3) % 3]
            if (x + 2 * y) % 8 == 0:
                col = C("241527")  # board seam
            elif rng.random() < 0.02:
                col = C("241527")  # sparse grain — a whole house repeats this
            c.set(x, y, col)       # tile, so baked features must stay subtle

    elif kind == "screed":
        # warehouse floor: smooth finished concrete, one uniform surface.
        # A building uses ONE screed variant for every cell, so the tile must
        # be feature-free: any baked blob would repeat like wallpaper
        if variant == 1:
            _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.012, 0.03)
        else:
            _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.012, 0.03)

    elif kind == "forest":
        # woodland floor: dark mulch with undergrowth flecks (speckle kept low —
        # dense dots shimmer when the camera scrolls back and forth)
        region = _floor_base(c, rng, C("19332d"), C("341c27"), C("241527"), 0.11, 0.07)
        speckle(c, rng, region, [C("25562e"), C("4d2b32")], [0.035, 0.028])

    elif kind == "grass_blend":
        # transition tile: concrete with grass CREEPING onto it in clumps —
        # placed automatically wherever concrete touches woodland, so biome
        # edges blend instead of snapping tile-to-tile
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.028, 0.012)
        for _ in range(rng.randint(4, 6)):
            patch = blob(rng, 6 + rng.randrange(52), 4 + rng.randrange(24),
                         rng.randint(8, 20), region)
            for (x, y) in patch:
                if rng.random() < 0.8:
                    c.set(x, y, C("19332d") if rng.random() < 0.7 else C("25562e"))
        for _ in range(10 + variant * 6):  # stray blades
            x, y = 4 + rng.randrange(56), 2 + rng.randrange(28)
            if (x, y) in region:
                c.set(x, y, C("25562e"))

    elif kind == "asphalt_stall":
        # parking stall separator: pale worn line along the lower-left edge
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.04, 0.02)
        for (x, y) in region:
            if not in_diamond(x - 2, y + 1) and rng.random() < 0.8:
                c.set(x, y, C("819796"))

    elif kind == "asphalt":
        _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.04, 0.02)
    elif kind == "asphalt_line":
        # center dashes for roads running along the cell +y axis (screen SW).
        # dash period 16 px: 64/16 tessellates, so dashes continue seamlessly
        # from tile to tile (a 20 px period phased randomly at every seam)
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.04, 0.02)
        for (x, y) in region:
            if abs((x - 32) * 0.5 + (y - 16)) < 1.5 and (x // 8) % 2 == 0 and rng.random() < 0.94:
                c.set(x, y, C("de9e41"))
    elif kind == "asphalt_line_h":
        # same dashes for roads running along the cell +x axis (screen SE)
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.04, 0.02)
        for (x, y) in region:
            if abs((x - 32) * 0.5 - (y - 16)) < 1.5 and (x // 8) % 2 == 0 and rng.random() < 0.94:
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
    ("asphalt_line", ("asphalt_line", 0)), ("asphalt_line_h", ("asphalt_line_h", 0)),
    ("wood_0", ("wood", 0)), ("wood_1", ("wood", 1)), ("wood_2", ("wood", 2)),
    ("asphalt_stall", ("asphalt_stall", 0)),
    ("screed_0", ("screed", 0)), ("screed_1", ("screed", 1)),
    ("forest_0", ("forest", 0)), ("forest_1", ("forest", 1)),
    ("forest_2", ("forest", 2)),
    ("grass_blend_0", ("grass_blend", 0)), ("grass_blend_1", ("grass_blend", 1)),
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
SEG_THICK = 2  # cap depth in screen px — slim and flush with the wall
               # (a wide cap read as a fat lid on a thin wall; the ROOF's eave
               # modules are what overhang, not the wall itself)

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
    ox = 8
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
    # exactly WALL_H tall: the cap sits flush in the roof plane, closing the
    # fascia line at each corner instead of poking through the roof
    rng = random.Random(f"{SEED}:post:{style}")
    c = Canvas(18, 62)
    lit, dark = (C(n) for n in BRICK_STYLES[style]["x"])
    _, darker = (C(n) for n in BRICK_STYLES[style]["y"])
    bottoms = iso_prism(c, 2, 1, 12, 6, WALL_H, lit, lit, dark)
    for x in range(12):  # concrete cap
        y = bottoms[x]
        c.set(2 + x, y, CONC_L1)
        c.set(2 + x, y - 1, CONC_L1 if x % 2 else CONC_L2)
    for x in range(12):  # course shading
        for y in range(bottoms[x] + 2, bottoms[x] + WALL_H, 4):
            if rng.random() < 0.6:
                c.set(2 + x, y, dark if x < 6 else darker)
    c.outline_auto()
    return c, (8, 1 + WALL_H + 3), ["circle", 4.0]

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

ROOF_TONES = {  # both black (user call), subtly distinct
    "charcoal": ("151d28", "10141f", "394a50"),
    "pitch": ("10141f", "090a14", "202e37"),
}

# Modular roof system (user direction: modular prefabs + explicit placement
# formulas). The game places, per interior cell:
#     roof_tile_<tone>_<v>   at  map_to_local(cell) + (0, -WALL_H)
# and per boundary edge of the interior, at edge_midpoint + (0, -WALL_H):
#     roof_fascia_<tone>_s   (south edges: dark trim hanging off the eave)
#     roof_fascia_<tone>_e   (east edges)
#     roof_rim_<tone>        (north/west edges: 1px lit rim only)
# Tiles use the same tessellating diamond as the floor, so seams are exact.

def make_roof_tile(tone: str, variant: int) -> tuple[Canvas, tuple, list | None]:
    rng = random.Random(f"{SEED}:rooftile:{tone}:{variant}")
    base_col, dark_col, lite_col = (C(n) for n in ROOF_TONES[tone])
    c = Canvas(64, 32)
    region = {(x, y) for y in range(32) for x in range(64) if in_diamond(x, y)}
    for (x, y) in region:
        c.set(x, y, base_col)
    speckle(c, rng, region, [dark_col, lite_col], [0.09, 0.04])
    if variant == 1:
        patch = blob(rng, 32 + rng.randint(-10, 10), 16 + rng.randint(-4, 4),
                     rng.randint(20, 40), region)
        for (x, y) in patch:
            c.set(x, y, dark_col)
    return c, (32, 16), None

def make_roof_fascia(tone: str, axis: str) -> tuple[Canvas, tuple, list | None]:
    base_col, dark_col, lite_col = (C(n) for n in ROOF_TONES[tone])
    c = Canvas(40, 24)
    ox, oy = 4, 10
    for i in range(32):
        x = ox + 16 + (-16 + i)
        by = oy + _seg_base_fy(axis, i)
        c.set(x, by - 1, lite_col)   # lit eave rim
        c.set(x, by, dark_col)       # fascia board
        c.set(x, by + 1, INK)
        c.set(x, by + 2, INK)
    return c, (ox + 16, oy), None

def make_roof_eave(tone: str, side: str) -> tuple[Canvas, tuple, list | None]:
    """North/west roof edge: a FLAT, flush 3px closure over the wall coping.
    Straight rows that follow the tile edge slope exactly — the old deep
    speckled eave staircased against the tile grid and read as a rippling
    mesh hanging off half the roof. side 'n': x-axis edge; 'w': y-axis."""
    base_col, dark_col, lite_col = (C(n) for n in ROOF_TONES[tone])
    axis = "x" if side == "n" else "y"
    c = Canvas(44, 22)
    ox, oy = 6, 14
    for i in range(32):
        x = ox + 16 + (-16 + i)
        by = oy + _seg_base_fy(axis, i)
        c.set(x, by - 1, lite_col)   # thin straight lit rim
        c.set(x, by - 2, base_col)   # flush closure over the coping
        c.set(x, by - 3, INK)        # clean outline, no serration
    return c, (ox + 16, oy), None

def make_roof_corner(tone: str) -> tuple[Canvas, tuple, list | None]:
    """Post cap at the roof plane, exactly post-sized (12x6) and carrying the
    same rim/trim treatment as the fascia, so the roof's outline lines
    continue straight through the corners instead of breaking."""
    base_col, dark_col, lite_col = (C(n) for n in ROOF_TONES[tone])
    c = Canvas(16, 14)
    rows = small_diamond_rows(12, 6)
    cells: set = set()
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            cells.add((2 + x, 2 + i))
            c.set(2 + x, 2 + i, base_col)
    for (x, y) in cells:
        if (x, y - 1) not in cells:
            c.set(x, y, lite_col)          # rim continues over the cap
        if (x, y + 1) not in cells:
            c.set(x, y, dark_col)          # fascia trim continues below
            c.set(x, y + 1, INK)
            c.set(x, y + 2, INK)
    return c, (8, 5), None

def make_roof_tile_broken(tone: str, variant: int) -> tuple[Canvas, tuple, list | None]:
    """Roof tile with a collapsed hole — exposed joists across the gap."""
    rng = random.Random(f"{SEED}:roofbrk:{tone}:{variant}")
    base, origin, collider = make_roof_tile(tone, 0)
    c = base
    _, dark_col, lite_col = (C(n) for n in ROOF_TONES[tone])
    hole = blob(rng, 32 + rng.randint(-8, 8), 16 + rng.randint(-4, 4),
                rng.randint(60, 110),
                {(x, y) for y in range(32) for x in range(64) if in_diamond(x, y)})
    for (x, y) in hole:
        # DARKNESS, not transparency: a true see-through hole showed whatever
        # rendered under the lifted roof sprite — misprojected ground or wall
        # pieces (user report). A torn roof opens into black attic shadow.
        c.set(x, y, C("090a14") if (x * 3 + y * 7) % 11 else C("10141f"))
    for (x, y) in list(hole):  # torn edge
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in hole and c.get(nx, ny)[3] > 0 and (nx + ny) % 2 == 0:
                c.set(nx, ny, lite_col)
    # joists spanning the hole
    ys = sorted({y for (_, y) in hole})
    if ys:
        for jy in range(ys[0] + 2, ys[-1], 5):
            for (x, y) in hole:
                if y == jy or y == jy + 1:
                    c.set(x, y, C("341c27") if y == jy else C("241527"))
    return c, origin, collider

def make_roof_vent() -> tuple[Canvas, tuple, list | None]:
    c = Canvas(24, 24)
    vb = iso_prism(c, 2, 2, 20, 10, 7, CONC_BASE, CONC_D1, CONC_D2)
    for x in range(3, 17):
        if x % 3 != 0:
            c.set(2 + x, vb[x] + 3, INK)
            c.set(2 + x, vb[x] + 5, INK)
    c.outline_auto()
    return c, (12, 16), None

def make_roof_hatch() -> tuple[Canvas, tuple, list | None]:
    c = Canvas(20, 16)
    hb = iso_prism(c, 2, 2, 16, 8, 2, CONC_D1, CONC_D2, INK)
    for x in range(4, 12):
        c.set(2 + x, hb[x] - 1, CONC_BASE)
    c.outline_auto()
    return c, (10, 9), None

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
    c = Canvas(w + 4, d + h + 6)
    top, left, right, line = (C(n) for n in WOOD_TONES[tone])
    ox, oy = 2, 2
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
    if damaged and w // 2 - 4 > 4:  # a missing board on the lit face
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
        # a REAL iso cylinder (the old front-view drum read completely flat
        # next to the 3D vehicles): elliptical top face, walls hanging from
        # the ellipse's curve, hoops that follow the same curvature
        import math as _math
        c = Canvas(2 * r + 6, h + r + 6)
        cx = r + 3
        top_cy = r // 2 + 2
        ell_h = max(2, r // 2)

        def edge_dy(dx: int) -> int:
            f = 1.0 - (dx * dx) / float(r * r)
            return int(round(_math.sqrt(max(0.0, f)) * ell_h))

        # top face: full ellipse — lid fill, lit near rim, dark far rim
        for dx in range(-r, r + 1):
            dy = edge_dy(dx)
            for y in range(top_cy - dy, top_cy + dy + 1):
                col = lid
                if y <= top_cy - dy + 1 and dx < 1:
                    col = C("819796")            # lit back-left rim
                elif y >= top_cy + dy - 1:
                    col = dark                   # near rim shadow
                c.set(cx + dx, y, col)
        c.set(cx, top_cy, dark)                  # bung
        c.set(cx + 1, top_cy, dark)
        # walls: hang from the ellipse's lower edge, shaded around the curve
        for dx in range(-r, r + 1):
            dy = edge_dy(dx)
            t = (dx + r) / float(2 * r)
            col = lite if t < 0.28 else (body if t < 0.74 else dark)
            for y in range(top_cy + dy, top_cy + dy + h):
                c.set(cx + dx, y, col)
        # hoops follow the same curvature
        hoop_hs = [h // 3, (2 * h) // 3]
        if rng.random() < 0.5:
            hoop_hs.append(2)
        for hh in hoop_hs:
            for dx in range(-r, r + 1):
                dy = edge_dy(dx)
                c.set(cx + dx, top_cy + dy + hh, dark)
                c.set(cx + dx, top_cy + dy + hh - 1,
                    C("ad7757") if style == "rust" else C("819796"))
        if rng.random() < 0.5:  # dent on the shaded side
            dent_y = top_cy + ell_h + rng.randrange(3, h - 3)
            for x in range(cx + r - 3, cx + r):
                c.set(x, dent_y, body)
                c.set(x, dent_y + 1, body)
        for _ in range(rng.randint(6, 12)):
            fx = rng.randrange(cx - r + 1, cx + r - 1)
            c.set(fx, top_cy + edge_dy(fx - cx) + rng.randrange(2, h - 1), fleck)
        c.outline_auto()
        return c, (cx, top_cy + h + 1), ["circle", float(r - 1)]
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
        c = Canvas(14, h + 8)
        cx = 7
        top = 5
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
            c.set(x, h + 2, C("202e37"))
        c.rect(cx - 1, 2, cx, 4, C("577277"))
        for _ in range(rng.randint(2, 5)):
            c.set(rng.randrange(cx - 3, cx + 3), rng.randrange(top + 6, h), C("602c2c"))
        c.outline_auto()
        return c, (7, h + 2), ["circle", 4.0]
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
        c = Canvas(26, 27)
        cx, cy = 12, 12
        for y in range(24):
            for x in range(24):
                dx, dy = (x - cx) / 9.5, (y - cy) / 9.5
                d = dx * dx + dy * dy
                if 0.35 < d < 1.0:
                    c.set(x, y + 1, C("151d28") if d < 0.8 else C("10141f"))
                elif d <= 0.35:
                    c.set(x, y + 1, C("090a14"))
        for a in range(-3, 4):  # tread highlight arc
            c.set(cx + a, 4 if abs(a) < 2 else 5, C("202e37"))
        c.outline_auto()
        return c, (12, 23), ["circle", 6.0]
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
    c = Canvas(44, 48)
    ox, oy = 3, 10
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
        c = Canvas(56, 22)
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

# ------------------------------------------------------------ furniture -----
# Interior dressing so buildings read as lived-in places, not empty shells.

def make_couch() -> tuple[Canvas, tuple, list]:
    c = Canvas(50, 46)
    seat_top, seat_l, seat_r = C("752438"), C("411d31"), C("241527")
    bottoms = iso_prism(c, 3, 12, 44, 22, 8, seat_top, seat_l, seat_r)
    # backrest along the NE edge (faces the camera across the seat)
    for i in range(22):
        x0, x1 = small_diamond_rows(44, 22)[i]
        for x in range(x1 - 3, x1 + 1):
            for y in range(12 + i - 10, 12 + i + 2):
                c.set(3 + x, y, seat_l if x < x1 - 1 else seat_r)
    # cushion seams on the seat
    for x in range(10, 40, 10):
        for y in range(12 + small_diamond_rows(44, 22)[10][0] // 2, 30):
            if c.get(3 + x, y)[3] > 0 and (x + y) % 2 == 0:
                c.set(3 + x, y, seat_r)
    c.outline_auto()
    return c, (25, 33), ["diamond", 23.0, 12.0]

def make_cabinet() -> tuple[Canvas, tuple, list]:
    c = Canvas(30, 46)
    wood_t, wood_l, wood_r = C("602c2c"), C("4d2b32"), C("341c27")
    bottoms = iso_prism(c, 2, 3, 24, 12, 28, wood_t, wood_l, wood_r)
    for x in range(24):  # door split + knobs
        y = bottoms[x]
        if x == 12:
            c.vline(2 + x, y + 3, y + 26, C("241527"))
    c.set(2 + 10, bottoms[10] + 13, C("de9e41"))
    c.set(2 + 14, bottoms[14] + 13, C("de9e41"))
    c.outline_auto()
    return c, (14, 40), ["diamond", 13.0, 7.0]

def make_tv_stand() -> tuple[Canvas, tuple, list]:
    # tall enough for the full base: the old 38px canvas cut the stand's
    # bottom rows clean off (user screenshot)
    c = Canvas(34, 46)
    bottoms = iso_prism(c, 2, 20, 28, 14, 8, C("4d2b32"), C("341c27"), C("241527"))
    # tv on top: dark slab, screen facing SW with a glint
    tv = iso_prism(c, 7, 6, 16, 8, 12, C("151d28"), C("202e37"), C("10141f"))
    for x in range(2, 16):
        for y in range(tv[x] + 2, tv[x] + 11):
            if x < 9:
                c.set(7 + x, y, C("253a5e"))
        if 3 <= x <= 6:
            c.set(7 + x, tv[x] + 3 + x - 3, C("3c5e8b"))  # screen glint
    c.outline_auto()
    return c, (17, 35), ["diamond", 15.0, 8.0]

def make_table() -> tuple[Canvas, tuple, list]:
    c = Canvas(30, 30)
    rows = small_diamond_rows(24, 12)
    for i, (x0, x1) in enumerate(rows):  # top slab, floating on legs
        for x in range(x0, x1 + 1):
            c.set(3 + x, 4 + i, C("602c2c") if i else C("7a4841"))
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            if 4 + i + 2 <= 18:
                pass
    for lx, ly in ((6, 15), (24, 15), (15, 20)):  # legs
        c.vline(lx, ly - 4, ly + 6, C("341c27"))
    c.outline_auto()
    return c, (15, 24), ["diamond", 13.0, 7.0]

def make_chair() -> tuple[Canvas, tuple, list]:
    c = Canvas(18, 28)
    bottoms = iso_prism(c, 3, 12, 12, 6, 6, C("602c2c"), C("4d2b32"), C("341c27"))
    for i in range(6):  # backrest on the NE side
        x0, x1 = small_diamond_rows(12, 6)[i]
        for x in range(x1 - 1, x1 + 1):
            for y in range(12 + i - 8, 12 + i):
                c.set(3 + x, y, C("4d2b32"))
    c.outline_auto()
    return c, (9, 21), ["circle", 4.0]

def make_bookshelf() -> tuple[Canvas, tuple, list]:
    rng = random.Random(f"{SEED}:bookshelf")
    c = Canvas(32, 44)
    bottoms = iso_prism(c, 2, 3, 24, 12, 26, C("4d2b32"), C("341c27"), C("241527"))
    book_cols = [C("752438"), C("25562e"), C("3c5e8b"), C("602c2c"), C("819796")]
    for shelf in range(3):  # shelves with book spines on the lit face
        for x in range(2, 12):
            y = bottoms[x] + 4 + shelf * 8
            c.set(2 + x, y + 4, C("241527"))
            if rng.random() < 0.85:
                col = book_cols[rng.randrange(len(book_cols))]
                c.vline(2 + x, y + 1, y + 3, col)
    c.outline_auto()
    return c, (15, 38), ["diamond", 14.0, 7.0]

def _paste_canvas(c: Canvas, piece: Canvas, x: int, y: int,
                  mirror: bool = False) -> None:
    img = piece.img.transpose(Image.FLIP_LEFT_RIGHT) if mirror else piece.img
    c.img.alpha_composite(img, (x, y))
    c.px = c.img.load()

def crop_canvas(c: Canvas, origin: tuple[int, int],
                margin: int = 1) -> tuple[Canvas, tuple[int, int]]:
    """Trim a canvas to its opaque bounding box (+margin), keeping the origin
    anchored to the same pixel. Lets tall/piled sprites draw on a roomy canvas
    without shipping dead space — and guarantees nothing is ever clipped."""
    bbox = c.img.getbbox()
    if bbox is None:
        return c, origin
    x0 = max(0, bbox[0] - margin)
    y0 = max(0, bbox[1] - margin)
    x1 = min(c.w, bbox[2] + margin)
    y1 = min(c.h, bbox[3] + margin)
    out = Canvas(x1 - x0, y1 - y0)
    out.img.alpha_composite(c.img.crop((x0, y0, x1, y1)))
    out.px = out.img.load()
    return out, (origin[0] - x0, origin[1] - y0)

def make_crate_stack(variant: int) -> tuple[Canvas, tuple, list]:
    """Messy human-piled stack: every box gets cumulative random offsets,
    its own size, and sometimes a mirrored orientation — no perfect stacking."""
    rng = random.Random(f"{SEED}:cratestack:{variant}")
    # roomy canvas + crop: piled boxes could climb past the old fixed canvas
    # top, which clipped the top crate's lid flat
    c = Canvas(48, 76)
    base_w = rng.choice((24, 28))
    base_h = rng.randint(11, 14)
    base, base_origin, _ = draw_crate(rng, base_w, base_h, rng.randrange(2),
                                      rng.random() < 0.3, rng.random() < 0.5)
    base_x = (c.w - base.w) // 2
    base_y = c.h - base.h - 2
    _paste_canvas(c, base, base_x, base_y, rng.random() < 0.5)
    top_x, top_y = base_x, base_y
    prev = base
    count = rng.randint(1, 2)
    for i in range(count):
        w = rng.choice((16, 20, 24))
        h = rng.randint(8, 12)
        box, _, _ = draw_crate(rng, w, h, rng.randrange(2),
                               rng.random() < 0.3, rng.random() < 0.4)
        # jostle: offset from the box below, never perfectly centered
        top_x = top_x + (prev.w - box.w) // 2 + rng.randint(-4, 4)
        top_y = top_y - h - rng.randint(1, 3)
        _paste_canvas(c, box, top_x, top_y, rng.random() < 0.5)
        prev = box
    cropped, origin = crop_canvas(c, (c.w // 2, base_y + base_origin[1]))
    return cropped, origin, ["diamond", base_w / 2 + 1.0, base_w / 4 + 1.0]

def make_rack(variant: int) -> tuple[Canvas, tuple, list]:
    """Industrial shelving with a UNIQUE, unevenly-jostled load per variant."""
    rng = random.Random(f"{SEED}:rack:{variant}")
    # keep total height under the wall height so racks never poke past the
    # wall cap when parked against a wall
    c = Canvas(68, 58)
    steel, steel_d = C("394a50"), C("202e37")
    for level_y in (20, 36):
        rows = small_diamond_rows(52, 26)
        for i, (x0, x1) in enumerate(rows):
            for x in range(x0, x1 + 1):
                c.set(4 + x, level_y + i // 2, steel if i % 2 else steel_d)
    for ux in (6, 30, 54):
        c.vline(ux, 18, 52, steel_d)
        c.vline(ux + 1, 18, 52, steel)
    # random load: count, slots, sizes, tones, damage, mirroring all rolled
    for level_base in (8, 25):
        slots = [8, 22, 36]
        rng.shuffle(slots)
        for i in range(rng.randint(1, 3)):
            w = rng.choice((16, 20, 24))
            box, _, _ = draw_crate(rng, w, rng.randint(8, 11), rng.randrange(2),
                                   rng.random() < 0.35, rng.random() < 0.3)
            _paste_canvas(c, box, slots[i] + rng.randint(-3, 3),
                          level_base + rng.randint(-2, 2), rng.random() < 0.5)
    c.outline_auto()
    return c, (30, 50), ["diamond", 28.0, 12.0]

ROOF_DEPTH = 12  # top-face depth in px — the old 6 read as a paper-thin car

def make_vehicle(kind: str, scheme: int, rev: bool = False,
                 broken: bool = False) -> tuple[Canvas, tuple, list]:
    """Iso vehicle along the screen (2,1) diagonal: side face + a DEEP roof
    plane + a visible SE end cap, so it reads as a solid body, not a cutout.
    rev=False: front at the NW end (heading NW, tail lights on the end cap).
    rev=True:  profile reversed (heading SE, head lights + grille on the cap,
    windshield glass on the roof near the cap). Mirrored copies of both give
    the NE / SW headings — all four lane directions ship pre-baked.
    broken=True: shattered glass, rust, dents — looted where it stands."""
    rng = random.Random(f"{SEED}:vehicle:{kind}:{scheme}:{rev}:{broken}")
    palettes = [
        ("752438", "411d31", "241527"),   # oxblood
        ("577277", "394a50", "202e37"),   # gray
        ("25562e", "19332d", "10141f"),   # olive
        ("884b2b", "602c2c", "341c27"),   # rust
    ]
    body_c, body_d, body_dd = (C(n) for n in palettes[scheme])
    glass, glass_d = C("3c5e8b"), C("253a5e")
    L = 46
    prof = []
    if kind == "car":
        for i in range(L):
            if i < 3:
                h = 7
            elif i < 12:
                h = 10
            elif i < 17:
                h = 10 + (i - 11) * 2   # windshield ramp
            elif i < 32:
                h = 20                  # roof
            elif i < 36:
                h = 20 - (i - 31) * 2   # rear ramp
            elif i < 43:
                h = 11
            else:
                h = 8
            prof.append(h)
        win_lo, win_hi = 17, 33
        glass_roof = (12, 18)           # raked glass region (front)
    else:  # pickup: tall cab front, low open bed rear
        for i in range(L):
            if i < 3:
                h = 8
            elif i < 10:
                h = 11
            elif i < 13:
                h = 11 + (i - 9) * 3    # windshield ramp
            elif i < 24:
                h = 20                  # cab roof
            elif i < 26:
                h = 12
            elif i < 44:
                h = 10                  # bed wall
            else:
                h = 8
            prof.append(h)
        win_lo, win_hi = 13, 25
        glass_roof = (9, 14)
    bed_lo, bed_hi = 26, 44   # open-bed interior span in profile coords
    if rev:
        prof = prof[::-1]
        win_lo, win_hi = L - win_hi, L - win_lo
        glass_roof = (L - glass_roof[1], L - glass_roof[0])
        bed_lo, bed_hi = L - 44, L - 26
    clear = 4  # ground clearance (wheels fill it)
    oy = 34
    ox = 6
    c = Canvas(84, 70)
    for i in range(L):  # body side face
        x = ox + i
        base = oy + i // 2
        for y in range(base - clear - prof[i], base - clear + 1):
            c.set(x, y, body_d)
    prev_top = None
    for i in range(L):  # roof plane toward NE — deep enough to read as width
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i]
        # on the raked ramps (windshield/trunk) the profile jumps 2+ per
        # column; bridge the whole jump or the plane renders as ladder slats
        # ("the front or back is always missing" — user report, twice)
        span = 1 if prev_top is None else abs(prev_top - top) + 1
        rising = prev_top is not None and prev_top > top
        for t in range(1, ROOF_DEPTH + 1):
            col = body_c
            if t == ROOF_DEPTH:
                col = body_d            # far rim
            elif rng.random() < 0.02:
                col = body_d
            for k in range(span):
                yy = top + (k if rising else -k)
                c.set(x + t, yy - (t + 1) // 2, col)
                c.set(x + t, yy - t // 2, col)
        prev_top = top
    # raked glass on the roof plane (windshield when heading SE, rear glass
    # when heading NW) — this is what makes the facing readable from above
    glass_prev = None
    for i in range(glass_roof[0], glass_roof[1]):
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i]
        g_span = 1 if glass_prev is None else abs(glass_prev - top) + 1
        g_rising = glass_prev is not None and glass_prev > top
        for t in range(2, ROOF_DEPTH - 1):
            var_col = glass if t < 5 else glass_d
            for k in range(g_span):
                yy = top + (k if g_rising else -k)
                c.set(x + t, yy - (t + 1) // 2, var_col)
                c.set(x + t, yy - t // 2, var_col)
        glass_prev = top
    for i in range(win_lo, win_hi):  # side window band with pillars
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i]
        if (i - win_lo) % 8 < 6:
            for y in range(top + 2, top + 8):
                # broken into: side glass gone dark (a couple of glints stay)
                c.set(x, y, C("090a14") if broken else glass_d)
            if (i - win_lo) % 8 < 2:
                for y in range(top + 2, top + 6):
                    c.set(x, y, C("a8b5b2") if (broken and (x + y) % 7 == 0)
                          else (C("090a14") if broken else glass))
    for i in range(2, L - 2):  # body trim line
        x = ox + i
        base = oy + i // 2
        c.set(x, base - clear - 2, body_dd)
    seam = (win_lo + win_hi) // 2
    for y in range(oy + seam // 2 - clear - prof[seam] + 2, oy + seam // 2 - clear):
        c.set(ox + seam, y, body_dd)
    # SE end cap: the only end face the camera can see. Rear of an NW-bound
    # car (tail lights + trunk seam), front of an SE-bound one (head lights +
    # grille). 5px deep with a wrapped corner so the body clearly ENDS in a
    # face, not a flat cutoff (user report: "cars don't have fronts/backs").
    cap_h = prof[L - 1]
    cap_d = 5
    for t in range(cap_d):
        x = ox + L + t
        base = oy + (L + t) // 2
        top_y = base - clear - cap_h + (t + 1) // 2
        for y in range(top_y, base - clear + 1):
            # MID tone, not darkest: a body_dd cap disappears against dark
            # asphalt and reads as a missing end (three user reports)
            c.set(x, y, body_d if t < cap_d - 1 else body_dd)
        c.set(x, top_y, body_c)                   # lit top edge of the cap
        c.set(x, base - clear, C("394a50"))       # steel bumper, visible
        c.set(x, base - clear - 1, C("394a50"))
    # wrapped corner: the side face's last column darkens into the cap
    for y in range(oy + (L - 1) // 2 - clear - cap_h + 1, oy + (L - 1) // 2 - clear):
        c.set(ox + L - 1, y, body_dd)
    # FAR-END wrap: the hidden end must still close the silhouette — a flat
    # cutoff read as "the car is missing its front" (user report)
    far_h = prof[0]
    for t in range(1, 3):
        x = ox - t
        base = oy - (t + 1) // 2
        far_top = base - clear - far_h + (t + 1) // 2
        for y in range(far_top, base - clear + 1):
            c.set(x, y, body_d if t == 1 else body_dd)
        c.set(x, base - clear, C("394a50"))    # bumper hint, visible
    # a 1px light sliver on the far corner (headlight fwd art, tail rev art)
    c.set(ox - 2, oy - 1 - clear - far_h + 2, C("de9e41") if not rev else C("752438"))
    cap_top = oy + L // 2 - clear - cap_h
    lights_y = cap_top + 2
    lights_px: list[tuple[int, int]] = []  # absolute px, for the alarm flashers
    if rev:  # head lights + grille slits
        for lx in (0, 1):
            c.set(ox + L + lx, lights_y, C("e8c170"))
        for lx in (3, 4):
            c.set(ox + L + lx, lights_y + 1, C("e8c170"))
        lights_px = [(ox + L, lights_y), (ox + L + 4, lights_y + 1)]
        for gy in (lights_y + 3, lights_y + 5):
            c.set(ox + L + 1, gy, C("151d28"))
            c.set(ox + L + 2, gy, C("151d28"))
            c.set(ox + L + 3, gy + 1, C("151d28"))
    else:    # tail lights + trunk seam
        tail = C("cf573c") if scheme == 0 else C("a53030")
        for lx in (0, 1):
            c.set(ox + L + lx, lights_y, tail)
        for lx in (3, 4):
            c.set(ox + L + lx, lights_y + 1, tail)
        lights_px = [(ox + L, lights_y), (ox + L + 4, lights_y + 1)]
        for sx_ in range(1, 4):
            c.set(ox + L + sx_, lights_y + 3 + (sx_ // 2), C("10141f"))
    for wf in (8, 34):  # wheel arches + wheels
        cxw = ox + wf + 3
        cyw = oy + (wf + 3) // 2 - 1
        # carve SMALL and only around the wheel itself: the old radius-4.2
        # carve ate the lower half of the 8px-tall hood/trunk sections — THE
        # "missing front/back" that survived three fixes
        for dy in range(-2, 3):
            for dx in range(-3, 4):
                if dx * dx + dy * dy <= 8:
                    c.set(cxw + dx, cyw + dy, (0, 0, 0, 0))
        for dy in range(-3, 3):
            for dx in range(-3, 4):
                d = dx * dx + dy * dy
                if d <= 10:
                    c.set(cxw + dx, cyw + dy, C("10141f") if d > 3 else C("202e37"))
        c.set(cxw, cyw, C("577277"))
    if kind == "pickup":  # cargo strictly INSIDE the bed — no cab overlap
        inner_lo = bed_lo + 3   # margins off the cab wall and the tailgate
        inner_hi = bed_hi - 3
        cursor = inner_lo
        for i in range(rng.randint(1, 2)):
            w = rng.choice((10, 12, 14))
            if cursor + w + 4 > inner_hi:  # no room left: skip, never overlap
                break
            mini = Canvas(w + 4, 14)
            mb = iso_prism(mini, 2, 1, w, w // 2, rng.randint(4, 6),
                C("be772b"), C("884b2b"), C("602c2c"))
            for mx in range(w):
                mini.set(2 + mx, mb[mx] + 2, C("341c27"))
            mini.outline_auto()
            bi = cursor + rng.randint(0, max(0, inner_hi - (cursor + w + 4)))
            c.img.alpha_composite(mini.img, (ox + bi, oy + bi // 2 - 24))
            c.px = c.img.load()
            cursor = bi + w + 5
    if broken:
        # broken into reads as EVENTS, not damage noise (user call): a door
        # left hanging open, one flat tire, dark side glass, some rust
        for _ in range(rng.randint(8, 12)):  # rust bloom
            x = ox + rng.randrange(2, L - 2)
            base = oy + x // 2
            y = base - clear - rng.randrange(1, max(2, prof[min(L - 1, x - ox)] - 1))
            c.set(x, y, C("884b2b") if rng.random() < 0.6 else C("602c2c"))
        # the open door: a panel swung out over the sill — CONNECTED to the
        # body (it hinges at the sill line, no floating debris)
        door_i = (win_lo + win_hi) // 2 + rng.randrange(-3, 3)
        for k in range(6):
            x = ox + door_i + k
            base = oy + (door_i + k) // 2
            top = base - clear - 1
            for y in range(top, top + 5 - (k // 3)):
                c.set(x, y, body_d if 0 < k < 5 else body_dd)
            if 1 < k < 4:
                c.set(x, top + 2, C("090a14"))     # its window, dark
        c.set(ox + door_i + 4, oy + (door_i + 4) // 2 - clear + 2, C("819796"))  # handle
        # one flat tire: the rear wheel squashes onto the ground
        flat_x = ox + 34 + 3
        flat_y = oy + (34 + 3) // 2 - 1
        for dx in range(-3, 4):
            c.set(flat_x + dx, flat_y + 1, C("10141f"))
        for dx in range(-4, 5):
            c.set(flat_x + dx, flat_y + 2, C("10141f"))
        c.set(flat_x - 5, flat_y + 2, C("202e37"))  # rubber spread
        c.set(flat_x + 5, flat_y + 2, C("202e37"))
    c.outline_auto()
    origin_full = (ox + (L + 3) // 2 + ROOF_DEPTH // 2, oy + (L + 3) // 4 - ROOF_DEPTH // 4)
    cropped, origin = crop_canvas(c, origin_full)
    # light positions relative to the origin are crop-invariant — the alarm
    # system flashes small overlays exactly on the baked light pixels
    lights_rel = [[px - origin_full[0], py - origin_full[1]] for (px, py) in lights_px]
    return cropped, origin, ["diamond", 29.0, 15.0], lights_rel

def mirror_prop(prop: tuple) -> tuple:
    """Bake the horizontal mirror of a prop (origin re-anchored, collider is
    symmetric, light offsets x-flipped). Keeps runtime transform-free."""
    canvas, origin, collider = prop[0], prop[1], prop[2]
    mirrored = (canvas.mirrored(), (canvas.w - 1 - origin[0], origin[1]), collider)
    if len(prop) > 3:
        return mirrored + ([[-lx, ly] for (lx, ly) in prop[3]],)
    return mirrored

def make_tree(kind: str, variant: int) -> tuple[Canvas, tuple, list]:
    """Trees, rebuilt. Every kind draws trunk FIRST, then grows the canopy
    down ONTO it with guaranteed overlap — a floating canopy is impossible by
    construction (the old code sized trunk and canopy independently and tall
    variants opened a gap). Drawn roomy, then cropped to content."""
    rng = random.Random(f"{SEED}:tree:{kind}:{variant}")
    c = Canvas(52, 92)
    cx = 26
    feet = c.h - 6

    if kind == "pine":
        trunk_len = rng.randint(14, 19)
        trunk_top = feet - trunk_len
        for y in range(trunk_top, feet + 2):
            c.set(cx - 1, y, C("4d2b32"))
            c.set(cx, y, C("341c27"))
        c.set(cx - 2, feet + 1, C("341c27"))  # root flare
        c.set(cx + 1, feet + 1, C("241527"))
        layers = rng.randint(3, 5)
        base_half = rng.randint(11, 15)
        bottom = trunk_top + 5  # bottom layer bites into the trunk: connected
        for li in range(layers):
            half = max(3, base_half - li * max(2, base_half // layers))
            lh = rng.randint(9, 12)
            top = bottom - lh
            for yy in range(lh):
                w = max(1, half * (yy + 1) // lh)
                jag = 1 if (yy % 3 == 2 and rng.random() < 0.6) else 0
                for x in range(cx - w - jag, cx + w + jag):
                    col = C("19332d")
                    if x < cx - w + 2:
                        col = C("25562e")          # lit western edge
                    elif x > cx + w - 3:
                        col = C("10141f")          # shaded east
                    elif rng.random() < 0.05:
                        col = C("10141f")
                    c.set(x, top + yy, col)
            for x in range(cx - half, cx + half):  # dark under-rim per layer
                if c.get(x, top + lh - 1)[3] > 0 and rng.random() < 0.75:
                    c.set(x, top + lh - 1, C("10141f"))
            bottom = top + rng.randint(3, 4)       # next layer overlaps this
        c.outline_auto()
        cropped, origin = crop_canvas(c, (cx, feet + 1))
        return cropped, origin, ["circle", 3.0]

    if kind == "oak":
        trunk_len = rng.randint(11, 15)
        trunk_top = feet - trunk_len
        lean = rng.choice((-1, 0, 0, 1))
        for y in range(trunk_top, feet + 2):
            dx = lean if y < trunk_top + trunk_len // 2 else 0
            c.set(cx - 1 + dx, y, C("4d2b32"))
            c.set(cx + dx, y, C("341c27"))
            if y > feet - 2:  # widening base
                c.set(cx - 2 + dx, y, C("4d2b32"))
                c.set(cx + 1 + dx, y, C("241527"))
        # canopy: 2-3 elliptical lobes, the lowest one swallowing the trunk top
        lobes = [(cx + lean, trunk_top - 2, rng.randint(11, 14), rng.randint(8, 10))]
        for i in range(rng.randint(1, 2)):
            lobes.append((cx + lean + rng.randint(-7, 7),
                          trunk_top - 6 - rng.randint(4, 9),
                          rng.randint(8, 12), rng.randint(6, 8)))
        pts: set = set()
        for (ox_, oy_, a, b) in lobes:
            for y in range(oy_ - b, oy_ + b + 1):
                for x in range(ox_ - a, ox_ + a + 1):
                    d = ((x - ox_) / a) ** 2 + ((y - oy_) / b) ** 2
                    if d < 1.0 + rng.uniform(-0.14, 0.05):
                        pts.add((x, y))
        for (x, y) in pts:
            col = C("19332d")
            if (x - 1, y) not in pts or (x, y - 1) not in pts:
                col = C("25562e") if x < cx + lean else C("10141f")
            elif rng.random() < 0.10:
                col = C("25562e")
            elif rng.random() < 0.05:
                col = C("468232")   # bright leaf sparks
            elif (x, y + 1) not in pts:
                col = C("10141f")   # dark under-rim
            c.set(x, y, col)
        c.outline_auto()
        cropped, origin = crop_canvas(c, (cx, feet + 1))
        return cropped, origin, ["circle", 3.5]

    # dead tree: tapering snag with forked branches
    h = rng.randint(34, 52)
    top = feet - h
    for y in range(top, feet + 2):
        c.set(cx - 1, y, C("341c27"))
        if y > top + h // 3:  # lower trunk is thicker
            c.set(cx, y, C("241527"))
    c.set(cx - 2, feet + 1, C("341c27"))
    c.set(cx + 1, feet + 1, C("241527"))
    for i in range(rng.randint(3, 5)):
        by = top + 3 + rng.randint(0, max(1, h - 18))
        dxs = 1 if rng.random() < 0.5 else -1
        bl = rng.randint(5, 11)
        for s in range(bl):
            c.set(cx - 1 + dxs * s, by - (s * 2) // 3, C("341c27"))
        if bl > 7 and rng.random() < 0.7:  # twig fork at the branch tip
            fx = cx - 1 + dxs * (bl - 2)
            fy = by - ((bl - 2) * 2) // 3
            for s in range(rng.randint(2, 4)):
                c.set(fx + dxs * s, fy + (1 if rng.random() < 0.5 else -1) * (s // 2),
                      C("241527"))
    c.outline_auto()
    cropped, origin = crop_canvas(c, (cx, feet + 1))
    return cropped, origin, ["circle", 2.0]

def make_body(variant: int) -> tuple[Canvas, tuple, list | None]:
    """A fallen raider past the barricades — drawn with the SAME lying-figure
    geometry as the player's prone sheet, so bodies are exactly character
    sized. Randomized: jacket color, hair or knit cap, beards, packs, pose."""
    rng = random.Random(f"{SEED}:body:{variant}")
    jackets = [("752438", "411d31"), ("3c5e8b", "253a5e"), ("577277", "394a50"),
               ("884b2b", "602c2c"), ("7a4841", "4d2b32"), ("a53030", "752438")]
    jkt, jkt_d = (C(n) for n in jackets[variant % len(jackets)])
    hair_cols = ["4d2b32", "341c27", "602c2c", "819796"]
    hair = C(hair_cols[rng.randrange(len(hair_cols))])
    hat = None
    if rng.random() < 0.4:
        hat = C(["a53030", "de9e41", "394a50", "25562e"][rng.randrange(4)])
    colors = {
        "jkt": jkt, "jkt_d": jkt_d, "pant": C("202e37"), "pant_d": C("151d28"),
        "boot": C("10141f"), "hair": hair, "skin": C("d7b594"),
        "skin_sh": C("c09473"), "pack": C("7a4841"), "pack_d": C("4d2b32"),
    }
    c = Canvas(34, 44)
    view = ("side", "front", "diag_front")[rng.randrange(3)]
    # dried stain beneath, dark and subtle
    for i in range(rng.randint(5, 9)):
        c.set(12 + rng.randint(-4, 6), 30 + rng.randint(-3, 2), C("241527"))
    _lying_figure(c, view, rng.choice((-1, 0, 1)), 0, colors,
                  hat=hat, beard=(hat is None and rng.random() < 0.45),
                  has_pack=rng.random() < 0.35)
    c.outline_auto()
    cr, orr = crop_canvas(c, (16, 33))
    return cr, orr, None


def make_barricade(kind: str, state: str) -> tuple[Canvas, tuple, list | None]:
    """Playable-edge barricades: concrete jersey barriers and metal fences,
    running along the screen (2,1) axis (mirrored at registration for the
    other axis). States: intact, damaged (cracked / bent), fallen (flat on
    the ground, no collider — walk right over it). The ring these form IS the
    map's advertised edge; the world visibly continues beyond them."""
    rng = random.Random(f"{SEED}:barricade:{kind}:{state}")
    LN = 28
    c = Canvas(LN + 14, 46)
    ox, oy = 4, 28

    if kind == "jersey" and state.startswith("askew"):
        # knocked off the line: the same barrier at a visibly wrong angle
        slope = 0.85 if state == "askew_a" else 0.2
        for i in range(LN - 4):
            x = ox + i
            by = oy + int(i * slope) - (10 if state == "askew_a" else 0)
            for k in range(9):
                col = CONC_BASE
                if rng.random() < 0.06:
                    col = CONC_D1
                c.set(x, by - k, col)
            c.set(x, by, CONC_D2)
            c.set(x, by - 9, CONC_L1)
        c.outline_auto()
        cr, orr = crop_canvas(c, (ox + (LN - 4) // 2, oy + 6))
        return cr, orr, ["diamond", 13.0, 6.0]

    if kind == "jersey":
        if state == "fallen":  # tipped onto its back: low flat slab
            for i in range(LN):
                x = ox + i
                by = oy + i // 2
                for d in range(6):
                    col = CONC_BASE if d < 4 else CONC_D1
                    if rng.random() < 0.06:
                        col = CONC_D2
                    c.set(x + d, by - 2 - (d + 1) // 2, col)
                c.set(x, by - 1, CONC_D1)
            c.outline_auto()
            cr, orr = crop_canvas(c, (ox + LN // 2, oy + 7))
            return cr, orr, None
        heights = [10] * LN
        if state == "cracked":  # a chunk bitten out of the middle
            bite_at = rng.randint(9, 15)
            for i in range(bite_at, bite_at + rng.randint(4, 6)):
                if i < LN:
                    heights[i] = rng.randint(3, 6)
        for i in range(LN):
            x = ox + i
            by = oy + i // 2
            h = heights[i]
            for k in range(h):
                col = CONC_BASE
                if (i + k) % 9 < 2 and h == 10 and 2 < k < 8:
                    col = C("de9e41") if (i + k) % 2 else C("be772b")  # worn chevron
                elif rng.random() < 0.05:
                    col = CONC_D1
                c.set(x, by - k, col)
            c.set(x, by, CONC_D2)               # dark foot
            top_y = by - h
            c.set(x, top_y, CONC_L1)            # lit crown
            c.set(x + 1, top_y - 1, CONC_D1)    # thin top face toward NE
            c.set(x + 2, top_y - 1, CONC_D1)
        if state == "cracked":  # rubble at the foot of the bite
            for r in range(rng.randint(3, 5)):
                rx = ox + rng.randint(8, 20)
                c.set(rx, oy + rx // 2 + rng.randint(0, 1) - 4, CONC_L1)
        c.outline_auto()
        cr, orr = crop_canvas(c, (ox + LN // 2, oy + 8))
        return cr, orr, ["diamond", 15.0, 5.0]

    # metal fence panel
    steel, steel_d, rust = C("577277"), C("394a50"), C("884b2b")
    if state == "fallen":  # panel flat on the ground
        for i in range(LN):
            x = ox + i
            by = oy + i // 2
            c.set(x, by - 2, steel_d)
            c.set(x + 4, by - 4, steel_d)
            if i % 5 == 0:  # cross slats of the lattice, laying flat
                for d in range(1, 4):
                    c.set(x + d, by - 2 - (d + 1) // 2, steel_d if d % 2 else rust)
        c.outline_auto()
        cr, orr = crop_canvas(c, (ox + LN // 2, oy + 7))
        return cr, orr, None
    # standing lattice panel — the piece the user pointed at, upright: a
    # dense diagonal cross-hatch between two posts, top rail, rusted through
    sag = 2 if state == "bent" else 0
    post_h = 14
    for px_ in (1, LN - 2):  # posts
        x = ox + px_
        by = oy + px_ // 2
        for k in range(post_h):
            c.set(x, by - k, steel_d if k % 4 else rust)
        c.set(x, by, C("202e37"))
    for i in range(1, LN - 1):  # top + bottom rails (mid-sag if bent)
        x = ox + i
        mid_dip = sag if abs(i - LN // 2) < 8 else 0
        by = oy + i // 2
        c.set(x, by - 13 + mid_dip, steel)
        c.set(x, by - 12 + mid_dip, steel_d)
        c.set(x, by - 1, steel_d)
    for i in range(1, LN - 1):  # dense diagonal lattice fill
        x = ox + i
        mid_dip = sag if abs(i - LN // 2) < 8 else 0
        by = oy + i // 2
        for k in range(2, 12):
            on_diag = (i + k) % 3 == 0 or (i - k) % 3 == 0
            if on_diag and rng.random() > 0.1:
                c.set(x, by - k + mid_dip, steel_d if (i + k) % 2 else steel)
            elif rng.random() < 0.04:
                c.set(x, by - k + mid_dip, rust)
    c.outline_auto()
    cr, orr = crop_canvas(c, (ox + LN // 2, oy + 8))
    return cr, orr, ["diamond", 15.0, 5.0]


def make_street_lamp(state: str) -> tuple[Canvas, tuple, list]:
    """Lamp fixture with a DARK bulb — the lit look is a separate glow overlay
    the game fades in at night (working lamps only). Dead variants are part of
    the 'nobody left' dressing: bent heads, smashed panes."""
    rng = random.Random(f"{SEED}:lamp:{state}")
    c = Canvas(26, 70)
    px_, py = 8, 62
    for y in range(10, py + 1):
        c.set(px_, y, C("394a50"))
        c.set(px_ + 1, y, C("202e37"))
    droop = 2 if state == "dead_bent" else 0
    for xi, x in enumerate(range(px_, px_ + 12)):
        dy = droop * xi // 11
        c.set(x, 10 + dy, C("394a50"))
        c.set(x, 11 + dy, C("202e37"))
    hy = 12 + droop
    c.rect(px_ + 10, hy, px_ + 15, hy + 3, C("202e37"))
    if state == "dead_smashed":
        c.rect(px_ + 11, hy + 2, px_ + 14, hy + 3, C("10141f"))   # empty pane
        c.set(px_ + 12, hy + 4, C("394a50"))                       # glass drop
        c.set(px_ + 11, hy + 6, C("151d28"))                       # dangling wire
        c.set(px_ + 11, hy + 7, C("151d28"))
    else:
        c.rect(px_ + 11, hy + 2, px_ + 14, hy + 3, C("394a50"))    # dark bulb
    if state == "dead_bent":
        c.set(px_ + 9, 11, C("151d28"))  # kink at the bend
    for y in range(py - 26, py, 7):      # pole wear
        if rng.random() < 0.6:
            c.set(px_, y, C("577277"))
    c.rect(px_ - 2, py, px_ + 3, py + 2, C("202e37"))
    c.outline_auto()
    return c, (px_, py + 2), ["circle", 2.0]

def make_lamp_glow() -> Image.Image:
    """Warm halo around a lit lamp head. Smooth alpha by design (light, like
    dust/vignette — palette-exempt)."""
    w, h = 26, 18
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    r, g, b, _ = C("e8c170")
    for y in range(h):
        for x in range(w):
            d = ((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2
            if d < 1.0:
                px[x, y] = (r, g, b, int(150 * (1.0 - d) ** 2))
    px[12, 8] = (235, 237, 233, 230)  # hot core on the bulb
    px[13, 8] = (235, 237, 233, 230)
    return img

def make_light_radial() -> Image.Image:
    """PointLight2D texture: smooth white radial falloff (light: exempt)."""
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    half = size / 2.0
    for y in range(size):
        for x in range(size):
            d = (((x - half) / half) ** 2 + ((y - half) / half) ** 2) ** 0.5
            if d < 1.0:
                a = int(255 * (1.0 - d) ** 1.7)
                px[x, y] = (255, 255, 255, a)
    return img

def make_light_cone() -> Image.Image:
    """Flashlight cone pointing +x, origin at the left-center edge."""
    import math
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cy = size / 2.0
    half_angle = math.radians(26.0)
    for y in range(size):
        for x in range(1, size):
            dy = y - cy
            dist = (x * x + dy * dy) ** 0.5
            if dist >= size - 2:
                continue
            ang = abs(math.atan2(dy, x))
            if ang > half_angle:
                continue
            radial = 1.0 - dist / (size - 2)
            angular = 1.0 - (ang / half_angle) ** 2
            near_soft = min(1.0, x / 26.0)
            a = int(235 * (radial ** 1.35) * angular * near_soft)
            if a > 0:
                px[x, y] = (255, 255, 255, a)
    return img

def make_alarm_light() -> Image.Image:
    """Amber blink dot overlaid on a car's baked light pixels during alarms."""
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    px = img.load()
    r, g, b, _ = C("e8c170")
    for x, y in ((1, 1), (2, 1), (1, 2), (2, 2)):
        px[x, y] = (r, g, b, 255)
    for x, y in ((0, 1), (3, 1), (0, 2), (3, 2), (1, 0), (2, 0), (1, 3), (2, 3)):
        px[x, y] = (r, g, b, 110)
    return img

def make_studio_gem() -> tuple[Canvas, tuple, list | None]:
    """The sapphire — SapphireSignal's mark. Classic gem cut: light table,
    faceted crown, deep pavilion, all Apollo blues."""
    c = Canvas(30, 26)
    cx = 15
    # crown (top band)
    for y in range(4, 9):
        half = 11 - (8 - y)
        for x in range(cx - half, cx + half):
            col = C("73bed3")
            if y == 4:
                col = C("a4dddb")                      # lit table
            elif x < cx - half + 3 or abs(x - cx) < 2:
                col = C("a4dddb") if y < 6 else C("4f8fba")
            elif x > cx + half - 3:
                col = C("3c5e8b")
            c.set(x, y, col)
    # pavilion (tapering bottom)
    for y in range(9, 22):
        half = max(1, 11 - (y - 9))
        for x in range(cx - half, cx + half):
            t = (x - (cx - half)) / max(1, 2 * half)
            col = C("4f8fba")
            if t < 0.25:
                col = C("73bed3")
            elif t > 0.72:
                col = C("253a5e")
            if (x + y) % 9 == 0:
                col = C("3c5e8b")                      # facet lines
            c.set(x, y, col)
    c.set(cx - 5, 5, C("ebede9"))                      # the sparkle
    c.set(cx - 4, 5, C("ebede9"))
    c.set(cx - 5, 6, C("ebede9"))
    c.outline_auto()
    return c, (cx, 22), None

def make_signal_rings() -> list[Image.Image]:
    """Expanding broadcast rings for the splash — pixel circles, faded by
    the runtime via modulate."""
    rings: list[Image.Image] = []
    for radius in (6, 10, 15, 21, 28, 36):
        size = radius * 2 + 4
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = img.load()
        r, g, b, _ = C("73bed3")
        steps = max(24, radius * 8)
        import math as _math
        for i in range(steps):
            a = i / steps * 2 * _math.pi
            x = int(size / 2 + _math.cos(a) * radius)
            y = int(size / 2 + _math.sin(a) * radius * 0.55)  # iso-squashed
            if 0 <= x < size and 0 <= y < size:
                px[x, y] = (r, g, b, 210)
        rings.append(img)
    return rings

def make_signal_beam() -> Image.Image:
    """The first beam: a bright vertical edge that sweeps the wordmark in."""
    img = Image.new("RGBA", (8, 60), (0, 0, 0, 0))
    px = img.load()
    core = C("a4dddb")
    glow = C("4f8fba")
    for y in range(60):
        px[3, y] = (core[0], core[1], core[2], 235)
        px[4, y] = (core[0], core[1], core[2], 160)
        px[2, y] = (glow[0], glow[1], glow[2], 110)
        px[5, y] = (glow[0], glow[1], glow[2], 70)
        if y % 3 == 0:
            px[1, y] = (glow[0], glow[1], glow[2], 45)
    return img

def make_studio_word() -> Image.Image:
    """'sapphire signal' in the game font, sapphire-toned, 2x."""
    word = _render_word("sapphire signal", C("a4dddb"), C("4f8fba"))
    return word.resize((word.width * 2, word.height * 2), Image.NEAREST)

def make_sniper_round() -> Image.Image:
    """Bright tracer round for the map-edge sniper (effect: alpha-graded)."""
    img = Image.new("RGBA", (6, 6), (0, 0, 0, 0))
    px = img.load()
    core = C("ebede9")
    warm = C("e8c170")
    px[2, 2] = core
    px[3, 2] = core
    px[2, 3] = core
    px[3, 3] = core
    for p in ((1, 2), (1, 3), (4, 2), (4, 3), (2, 1), (3, 1), (2, 4), (3, 4)):
        px[p] = (warm[0], warm[1], warm[2], 170)
    for p in ((1, 1), (4, 1), (1, 4), (4, 4)):
        px[p] = (warm[0], warm[1], warm[2], 70)
    return img

DOOR_FRAMES = 4
DOOR_LEAF = 20      # leaf length along the edge, px
DOOR_H = 34         # leaf height

def make_door_strip(kind: str, axis: str) -> tuple[Canvas, tuple, list]:
    """Interactive door: a DOOR_FRAMES-frame swing strip. Frame 0 = closed,
    flush IN the wall plane (nothing pokes through the wall any more); last
    frame = swung fully inward. Static jamb boards fill the edge beside the
    leaf on every frame. axis 'x' fits south (yp) walls, 'y' fits east (xp).
    Collider = thin quad along the full edge (game disables it while open)."""
    base, dark = (C("7a4841"), C("4d2b32")) if kind == "wood" \
        else (C("577277"), C("394a50"))
    frame_w, frame_h = 48, 60
    strip = Canvas(frame_w * DOOR_FRAMES, frame_h)
    # hinge sits 6 edge-px in from the first jamb; edge midpoint is the origin
    for f in range(DOOR_FRAMES):
        c = Canvas(frame_w, frame_h)
        hx, hy = 14, 46
        edge_dy = 0.5 if axis == "x" else -0.5
        # jamb boards: the fixed 6 px of edge on each side of the leaf
        for j in list(range(-6, 0)) + list(range(DOOR_LEAF, DOOR_LEAF + 6)):
            x = hx + j
            by = hy + round(j * edge_dy)
            for y in range(by - DOOR_H - 2, by + 1):
                c.set(x, y, dark if (y - by) % 5 else C("341c27"))
        # the leaf: swings from along-the-edge to inward-perpendicular
        t = f / float(DOOR_FRAMES - 1)
        if axis == "x":   # closed dir (2,1) -> open dir (2,-1)
            dx_step, dy_step = 1.0, 0.5 - t
        else:             # closed dir (2,-1) -> open dir (-2,-1)
            dx_step, dy_step = 1.0 - 2.0 * t, -0.5
        for i in range(DOOR_LEAF):
            x = hx + round(i * dx_step)
            by = hy + round(i * dy_step)
            for y in range(by - DOOR_H, by + 1):
                col = base
                if kind == "wood" and i % 5 == 4:
                    col = dark
                if kind == "metal" and (y - (by - DOOR_H)) % 6 == 5:
                    col = dark
                c.set(x, y, col)
            c.set(x, by - DOOR_H, dark)  # top edge
        # handle near the free end, fades as the leaf turns edge-on
        if abs(dx_step) > 0.4:
            handle_x = hx + round((DOOR_LEAF - 3) * dx_step)
            handle_y = hy + round((DOOR_LEAF - 3) * dy_step) - DOOR_H // 2
            c.set(handle_x, handle_y, C("10141f"))
        c.outline_auto()
        _paste_canvas(strip, c, f * frame_w, 0)
    # origin: edge midpoint at the leaf base (matches wall-segment anchoring)
    origin = (14 + 10, 46 + (5 if axis == "x" else -5))
    if axis == "x":
        a, b = (-16.0, -8.0), (16.0, 8.0)
        n = (-2.4, 4.8)
    else:
        a, b = (-16.0, 8.0), (16.0, -8.0)
        n = (2.4, 4.8)
    poly = [a[0] - n[0], a[1] - n[1], b[0] - n[0], b[1] - n[1],
            b[0] + n[0], b[1] + n[1], a[0] + n[0], a[1] + n[1]]
    return strip, origin, ["poly", poly]

def draw_stick(rng: random.Random, variant: int) -> tuple[Canvas, tuple, list | None]:
    """Fallen branch litter for the woods and grove floors."""
    ln = rng.randint(8, 16)
    c = Canvas(ln + 6, 10)
    x, y = 3, 5 + rng.randint(-1, 1)
    slope = rng.choice((-1, 1)) * rng.uniform(0.15, 0.4)
    cols = (C("4d2b32"), C("341c27"), C("602c2c"))
    for i in range(ln):
        col = cols[0] if i % 5 else cols[2]
        c.set(x + i, y + round(i * slope), col)
        if rng.random() < 0.3:
            c.set(x + i, y + round(i * slope) + 1, cols[1])
    if ln > 10 and rng.random() < 0.8:  # fork
        fx = x + rng.randrange(3, ln - 4)
        fy = y + round((fx - x) * slope)
        fdir = -1 if slope > 0 else 1
        for s in range(rng.randint(2, 4)):
            c.set(fx + s, fy + fdir * ((s + 1) // 2), cols[1])
    c.outline_auto()
    return c, (c.w // 2, 6), None

def draw_trash(rng: random.Random, kind: str) -> tuple[Canvas, tuple, list | None]:
    """Tiny litter: cans, bottles, paper scraps — dressing around broken-into
    cars and doorways. No colliders, pure set dressing."""
    if kind.startswith("can"):
        tones = {"can_a": ("819796", "577277"), "can_b": ("a53030", "752438"),
                 "can_c": ("468232", "25562e")}
        lite, dark = (C(n) for n in tones[kind])
        c = Canvas(9, 8)
        fallen = rng.random() < 0.5
        if fallen:
            for i in range(5):
                c.set(2 + i, 3, lite)
                c.set(2 + i, 4, dark)
            c.set(1, 3, C("a8b5b2"))  # open lid ring
            c.set(1, 4, C("a8b5b2"))
        else:
            for y in range(2, 6):
                c.set(3, y, lite)
                c.set(4, y, dark)
            c.set(3, 2, C("a8b5b2"))
            c.set(4, 2, C("819796"))
        c.outline_auto()
        return c, (4, 6), None
    if kind == "bottle":
        c = Canvas(11, 8)
        glass, glint = C("19332d"), C("468232")
        for i in range(5):  # lying on its side
            c.set(2 + i, 3, glass)
            if i in (1, 3):
                c.set(2 + i, 2, glint)
        c.set(7, 3, glass)  # neck
        c.set(8, 3, C("341c27"))
        c.outline_auto()
        return c, (5, 4), None
    # paper scrap
    c = Canvas(9, 7)
    for (x, y) in ((2, 2), (3, 2), (4, 2), (2, 3), (3, 3), (5, 3), (4, 4)):
        c.set(x, y, C("a8b5b2") if (x + y) % 2 else C("c7cfcc"))
    c.outline_auto()
    return c, (4, 4), None

def make_puddle(variant: int) -> tuple[Canvas, tuple, list | None]:
    rng = random.Random(f"{SEED}:puddle:{variant}")
    w = rng.randint(26, 42)
    h = w // 2
    c = Canvas(w + 4, h + 4)
    cx, cy = c.w // 2, c.h // 2
    for y in range(c.h):
        for x in range(c.w):
            dx = (x - cx) / (w / 2)
            dy = (y - cy) / (h / 2)
            d = dx * dx + dy * dy + rng.uniform(-0.15, 0.15)
            if d < 1.0:
                r, g, b, _ = C("253a5e")
                a = 200 if d < 0.7 else 120
                c.set(x, y, (r, g, b, a))
    for i in range(w // 4):
        x = rng.randrange(4, c.w - 4)
        y = rng.randrange(2, c.h - 2)
        if c.get(x, y)[3] > 0:
            r, g, b, _ = C("3c5e8b")
            c.set(x, y, (r, g, b, 200))
    return c, (cx, cy), None

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

    # interior dressing (not scattered; placed by the builder)
    props["couch"] = make_couch()
    props["cabinet"] = make_cabinet()
    props["tv_stand"] = make_tv_stand()
    props["table"] = make_table()
    props["chair"] = make_chair()
    props["bookshelf"] = make_bookshelf()
    for i in range(4):
        fam("crate_stack", i, make_crate_stack(i))
    for i in range(4):
        fam("rack", i, make_rack(i))
    # vehicles: every lane heading pre-baked (nw/se drawn, ne/sw mirrored);
    # the last two specs are broken-into wrecks
    veh_specs = [("car", 0, False), ("car", 1, False), ("pickup", 2, False),
                 ("car", 3, True), ("pickup", 1, True)]
    for i, (kind, scheme, broken) in enumerate(veh_specs):
        art_nw = make_vehicle(kind, scheme, rev=False, broken=broken)
        art_se = make_vehicle(kind, scheme, rev=True, broken=broken)
        fam("vehicle_nw", i, art_nw)
        fam("vehicle_se", i, art_se)
        fam("vehicle_ne", i, mirror_prop(art_nw))
        fam("vehicle_sw", i, mirror_prop(art_se))
    for i in range(4):
        fam("tree", i, make_tree("pine", i))
    for i in range(3):
        fam("tree", 4 + i, make_tree("oak", i))
    for i in range(2):
        fam("tree", 7 + i, make_tree("dead", i))
    props["street_lamp"] = make_street_lamp("working")
    fam("street_lamp_dead", 0, make_street_lamp("dead_bent"))
    fam("street_lamp_dead", 1, make_street_lamp("dead_smashed"))
    for kind in ("wood", "metal"):
        for axis in ("x", "y"):
            props[f"door_{kind}_{axis}"] = make_door_strip(kind, axis)
    for i in range(4):
        rng = random.Random(f"{SEED}:stick:{i}")
        fam("stick", i, draw_stick(rng, i))
    for i, kind in enumerate(("can_a", "can_b", "can_c", "bottle", "paper")):
        rng = random.Random(f"{SEED}:trash:{i}")
        fam("trash", i, draw_trash(rng, kind))
    for i in range(3):
        props[f"puddle_{i}"] = make_puddle(i)
    # edge barricades: x-axis drawn, y-axis mirrored; fallen ones are a
    # separate family (no collider — they're walked over)
    for i, (kind, state) in enumerate(
            [("jersey", "intact"), ("jersey", "cracked"),
             ("fence", "intact"), ("fence", "bent")]):
        art = make_barricade(kind, state)
        fam("barricade_x", i, art)
        fam("barricade_y", i, mirror_prop(art))
    for i, (kind, state) in enumerate([("jersey", "fallen"), ("fence", "fallen")]):
        art = make_barricade(kind, state)
        fam("barricade_x_flat", i, art)
        fam("barricade_y_flat", i, mirror_prop(art))
    for i, state in enumerate(("askew_a", "askew_b")):
        art = make_barricade("jersey", state)
        fam("barricade_x_askew", i, art)
        fam("barricade_y_askew", i, mirror_prop(art))
    for i in range(6):  # fallen raiders (half mirrored for pose variety)
        art = make_body(i)
        fam("body", i, mirror_prop(art) if i % 2 else art)
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


def draw_head(c: Canvas, view: str, bob: int, crouch: bool = False) -> None:
    y0 = (15 if crouch else 10) + bob
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


def draw_torso(c: Canvas, view: str, bob: int, crouch: bool = False) -> None:
    y0 = (23 if crouch else 18) + bob
    y1 = (30 if crouch else 27) + bob
    x0, x1 = CX - 4, CX + 3
    c.rect(x0, y0, x1, y1, JKT)
    c.hline(x0, x1, y0, JKT_L)
    c.vline(x1, y0 + 1, y1, JKT_D)
    c.vline(x0, y0 + 1, y1, JKT_D)  # left edge shaded like the right one, so
    c.hline(x0, x1, y1, JKT_D)      # BOTH arms read separate from the torso
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


def draw_pack(c: Canvas, view: str, bob: int, crouch: bool = False) -> None:
    y0 = (24 if crouch else 19) + bob
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


def draw_arms(c: Canvas, view: str, bob: int, frame: int, crouch: bool = False) -> None:
    # both arms the same jacket tone: asymmetric arm shading reads as a bug
    # at this size, and mirrored direction rows make it jump sides
    # the torso spans CX-4..CX+3 (even width on an odd center), so arm columns
    # must be placed off the body EDGES to be symmetric, not off CX
    y0 = (24 if crouch else 19) + bob
    arm_len = 6 if crouch else 8
    if view in ("front", "back"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = (CX - 6) if side < 0 else (CX + 4)
            yy = y0 + (1 if sw > 0 else 0)
            c.rect(x, yy, x + 1, yy + arm_len, JKT)
            c.rect(x, yy + arm_len + 1, x + 1, yy + arm_len + 2,
                   SKIN if view == "front" else SKIN_SH)
    elif view in ("front34", "back34"):
        swing = FRONT_SWING[frame]
        for side, sw in ((-1, swing), (1, -swing)):
            x = ((CX - 5) if side < 0 else (CX + 4)) + sw
            c.rect(x, y0, x + 1, y0 + arm_len, JKT)
            if side < 0:  # this arm overlaps the torso: shade its inner column
                c.vline(x + 1, y0, y0 + arm_len, JKT_D)
            c.rect(x, y0 + arm_len + 1, x + 1, y0 + arm_len + 2, SKIN)
    else:
        x = CX + 1 + SIDE_SWING[frame]
        c.rect(x, y0, x + 1, y0 + arm_len, JKT)
        c.rect(x, y0 + arm_len + 1, x + 1, y0 + arm_len + 2, SKIN)


def draw_legs(c: Canvas, view: str, frame: int, crouch: bool = False) -> None:
    # crouch: legs start lower (bent under the dropped torso), wider stance
    leg_top = 33 if crouch else 28
    if view in ("front", "front34", "back", "back34"):
        lifts = STEP_LIFT[frame]
        spread = 1 if crouch else 0
        for (x0, lift, pcol) in ((CX - 4 - spread, lifts[0], PANT),
                                 (CX + 1 + spread, lifts[1], PANT_D)):
            lift = min(lift, 1) if crouch else lift
            dy = -lift
            c.rect(x0, leg_top, x0 + 2, 33 + dy, pcol)
            c.rect(x0, 34 + dy, x0 + 2, 36 + dy, BOOT)
            c.hline(x0, x0 + 2, FEET + dy, BOOT_D)
    else:
        front_dx, back_dx, front_lift, back_lift = SIDE_STRIDE[frame]
        if crouch:
            front_dx += 2   # bent knees: legs offset forward under the body
            back_dx -= 1
            front_lift = min(front_lift, 1)
            back_lift = min(back_lift, 1)
        for dx, lift, pcol, bcol in ((back_dx, back_lift, PANT_D, BOOT),
                                     (front_dx, front_lift, PANT, BOOT)):
            x0 = CX - 1 + dx
            c.rect(x0, leg_top, x0 + 2, 33 - lift, pcol)
            c.rect(x0, 34 - lift, x0 + 2, 36 - lift, bcol)
            toe = x0 + (3 if dx >= 0 else 2)
            c.hline(x0, toe, FEET - lift, BOOT_D)


def draw_char_frame(view: str, frame: int, crouch: bool = False) -> Canvas:
    c = Canvas(32, 40)
    bob = BOB[frame]
    if crouch:
        bob = maxi_bob(bob)
    if view in ("back", "back34"):
        draw_legs(c, view, frame, crouch)
        draw_torso(c, view, bob, crouch)
        draw_arms(c, view, bob, frame, crouch)
        draw_pack(c, view, bob, crouch)
        draw_head(c, view, bob, crouch)
    elif view == "side":
        draw_pack(c, view, bob, crouch)
        draw_legs(c, view, frame, crouch)
        draw_torso(c, view, bob, crouch)
        draw_arms(c, view, bob, frame, crouch)
        draw_head(c, view, bob, crouch)
    else:
        draw_legs(c, view, frame, crouch)
        draw_torso(c, view, bob, crouch)
        draw_arms(c, view, bob, frame, crouch)
        draw_head(c, view, bob, crouch)
    c.outline_auto()
    return c


def maxi_bob(bob: int) -> int:
    return max(bob, -1)  # crouch keeps the bob subtle

DIR_VIEWS = [
    ("E", "side", False), ("SE", "front34", False), ("S", "front", False),
    ("SW", "front34", True), ("W", "side", True), ("NW", "back34", True),
    ("N", "back", False), ("NE", "back34", False),
]

# ------------------------------------------------------------- prone sheet ---
# Lying flat on the stomach, crawling. Same sheet geometry as the other
# stances (8 dirs x idle+6 frames, 32x40, feet-anchored origin), so the
# player script only swaps textures. Five base views, mirrored like DIR_VIEWS.

PRONE_VIEWS = [
    ("E", "side", False), ("SE", "diag_front", False), ("S", "front", False),
    ("SW", "diag_front", True), ("W", "side", True), ("NW", "diag_back", True),
    ("N", "back", False), ("NE", "diag_back", False),
]

def _lying_figure(c: Canvas, view: str, phase: int, drag: int, colors: dict,
                  hat=None, beard: bool = False, has_pack: bool = True) -> None:
    """Shared lying-flat figure at TRUE character proportions (the standing
    model is 8 wide with a 8x8 head — a prone body keeps that mass). Used by
    the player's prone sheet AND the fallen raiders, so they always match.
    phase: -1/0/1 crawl arm; drag: 0/1 body creep. colors: jkt/jkt_d/pant/
    pant_d/boot/hair/skin/skin_sh/pack/pack_d."""
    jkt, jkt_d = colors["jkt"], colors["jkt_d"]
    pant, pant_d = colors["pant"], colors["pant_d"]
    boot = colors["boot"]
    hair, skin, skin_sh = colors["hair"], colors["skin"], colors["skin_sh"]
    pack, pack_d = colors["pack"], colors["pack_d"]
    head_top = hat if hat is not None else hair

    if view == "side":  # facing E: head right, pack humped on the back
        y = 28
        c.rect(2, y + 3, 5, y + 5, boot)                 # boots trailing
        c.rect(5, y + 2, 12, y + 5, pant)                # legs, leg-thick
        c.hline(5, 12, y + 5, pant_d)
        if phase > 0:
            c.rect(7, y + 1, 9, y + 1, pant_d)           # a knee lifts
        c.rect(12, y, 22, y + 5, jkt)                    # torso
        c.hline(12, 22, y + 5, jkt_d)
        c.vline(12, y, y + 4, jkt_d)
        if has_pack:
            c.rect(13, y - 3, 19, y, pack)               # pack rides the back
            c.hline(13, 19, y - 3, pack_d)
        c.rect(22 + drag, y, 28 + drag, y + 4, skin)     # head, standing-sized
        c.rect(22 + drag, y - 2, 27 + drag, y + 1, head_top)
        c.set(28 + drag, y + 3, skin_sh)
        if beard:
            c.rect(26 + drag, y + 4, 28 + drag, y + 4, hair)
        reach = 30 if phase > 0 else 26                  # crawling arm
        c.rect(23 + drag, y + 5, reach + drag, y + 6, jkt)
        c.set(min(31, reach + drag + 1), y + 6, skin)

    elif view == "front":  # facing S: head to camera, soles away
        cx = CX
        base = 16
        for side_x in (cx - 4, cx + 1):                  # boots (far end)
            c.rect(side_x, base, side_x + 2, base + 2, boot)
        lift = 1 if phase > 0 else 0
        c.rect(cx - 4, base + 3, cx - 2, base + 7, pant)
        c.rect(cx + 1, base + 3 + lift, cx + 3, base + 7, pant_d)
        c.rect(cx - 4, base + 7, cx + 3, base + 14, jkt)  # torso, full width
        c.vline(cx - 4, base + 7, base + 14, jkt_d)
        c.vline(cx + 3, base + 7, base + 14, jkt_d)
        if has_pack:
            c.rect(cx - 2, base + 8, cx + 1, base + 13, pack)
            c.vline(cx + 1, base + 8, base + 13, pack_d)
        arm_y = base + 13
        c.rect(cx - 6, arm_y - (1 if phase > 0 else 0), cx - 5, arm_y + 3, jkt)
        c.rect(cx + 4, arm_y - (1 if phase < 0 else 0), cx + 5, arm_y + 3, jkt)
        c.set(cx - 6, arm_y + 4, skin)
        c.set(cx + 5, arm_y + 4, skin)
        c.rect(cx - 4, base + 15 + drag, cx + 3, base + 19 + drag, head_top)
        c.hline(cx - 4, cx + 3, base + 20 + drag, skin_sh)  # brow sliver
        if beard:
            c.hline(cx - 2, cx + 1, base + 21 + drag, hair)

    elif view == "back":  # facing N: head away (hair only), soles at camera
        cx = CX
        base = 15
        c.rect(cx - 4, base + drag, cx + 3, base + 4 + drag, head_top)
        arm_y = base + 4
        c.rect(cx - 6, arm_y, cx - 5, arm_y + 4 - (1 if phase > 0 else 0), jkt)
        c.rect(cx + 4, arm_y, cx + 5, arm_y + 4 - (1 if phase < 0 else 0), jkt)
        c.set(cx - 6, arm_y - 1, skin)
        c.set(cx + 5, arm_y - 1, skin)
        c.rect(cx - 4, base + 5, cx + 3, base + 12, jkt)
        c.vline(cx - 4, base + 5, base + 12, jkt_d)
        c.vline(cx + 3, base + 5, base + 12, jkt_d)
        if has_pack:
            c.rect(cx - 2, base + 6, cx + 1, base + 11, pack)
            c.vline(cx - 2, base + 6, base + 11, pack_d)
        lift = 1 if phase > 0 else 0
        c.rect(cx - 4, base + 12, cx - 2, base + 16, pant)
        c.rect(cx + 1, base + 12, cx + 3, base + 16 - lift, pant_d)
        for side_x in (cx - 4, cx + 1):                  # soles toward camera
            c.rect(side_x, base + 17, side_x + 2, base + 19, boot)

    elif view == "diag_front":  # facing SE: along the down-right diagonal
        sx, sy = 4, 18
        c.rect(sx, sy, sx + 2, sy + 2, boot)             # soles upper-left
        for i in range(3):                               # legs, leg-thick
            c.rect(sx + 2 + i * 2, sy + 1 + i, sx + 5 + i * 2, sy + 3 + i, pant)
        for i in range(5):                               # torso, full mass
            c.rect(sx + 7 + i * 2, sy + 3 + i, sx + 11 + i * 2, sy + 6 + i, jkt)
        if has_pack:
            for i in range(3):
                c.rect(sx + 9 + i * 2, sy + 2 + i, sx + 12 + i * 2, sy + 4 + i, pack)
        hx = sx + 17 + drag
        hy = sy + 9 + drag // 2
        c.rect(hx, hy, hx + 5, hy + 3, head_top)         # standing-sized head
        c.rect(hx + 2, hy + 3, hx + 6, hy + 6, skin)
        if beard:
            c.rect(hx + 4, hy + 6, hx + 6, hy + 6, hair)
        reach = 4 if phase > 0 else 2
        c.rect(hx + 3, hy + 7, hx + 3 + reach, hy + 8, jkt)
        c.set(min(31, hx + 4 + reach), hy + 8, skin)

    else:  # diag_back — facing NE: head upper-right, soles lower-left
        sx, sy = 4, 34
        c.rect(sx, sy - 1, sx + 2, sy + 1, boot)         # soles lower-left
        for i in range(3):
            c.rect(sx + 2 + i * 2, sy - 3 - i, sx + 5 + i * 2, sy - 1 - i, pant)
        for i in range(5):
            c.rect(sx + 7 + i * 2, sy - 8 - i, sx + 11 + i * 2, sy - 5 - i, jkt)
        if has_pack:
            for i in range(3):
                c.rect(sx + 8 + i * 2, sy - 9 - i, sx + 11 + i * 2, sy - 8 - i, pack)
        hx = sx + 17 + drag
        hy = sy - 15 - drag // 2
        c.rect(hx, hy, hx + 5, hy + 3, head_top)         # hair only, facing away
        reach = 4 if phase > 0 else 2
        c.rect(hx + 2, hy - 2, hx + 2 + reach, hy - 1, jkt)
        c.set(min(31, hx + 3 + reach), hy - 2, skin)


PLAYER_LYING_COLORS = {
    "jkt": JKT, "jkt_d": JKT_D, "pant": PANT, "pant_d": PANT_D, "boot": BOOT_D,
    "hair": HAIR, "skin": SKIN, "skin_sh": SKIN_SH, "pack": PACK, "pack_d": PACK_D,
}

def draw_prone_frame(view: str, frame: int) -> Canvas:
    c = Canvas(32, 40)
    # crawl cycle: 0 = still; 1-3 pull with one arm, 4-6 with the other
    phase = 0 if frame == 0 else (1 if frame <= 3 else -1)
    drag = 1 if frame in (2, 3, 5, 6) else 0  # the body creeps mid-pull
    _lying_figure(c, view, phase, drag, PLAYER_LYING_COLORS)
    c.outline_auto()
    return c


def make_char_prone_sheet() -> Image.Image:
    cols = 1 + WALK_FRAMES
    sheet = Image.new("RGBA", (cols * 32, 8 * 40), (0, 0, 0, 0))
    for row, (_, view, mirrored) in enumerate(PRONE_VIEWS):
        for frame in range(cols):
            fc = draw_prone_frame(view, frame)
            if mirrored:
                fc = fc.mirrored()
            sheet.paste(fc.img, (frame * 32, row * 40))
    return sheet

def make_char_sheet(crouch: bool = False) -> Image.Image:
    cols = 1 + WALK_FRAMES
    sheet = Image.new("RGBA", (cols * 32, 8 * 40), (0, 0, 0, 0))
    for row, (_, view, mirrored) in enumerate(DIR_VIEWS):
        for frame in range(cols):
            fc = draw_char_frame(view, frame, crouch)
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

def make_title() -> tuple[Image.Image, Image.Image, Image.Image]:
    """Returns (wordmark, silver shine layer, tagline). The tagline is its own
    static image (user: smaller, not animated with the title); the shine layer
    is the wordmark in silver, swept across at runtime for a gleam."""
    text = _render_word("spoils", C("ebede9"), C("819796"))
    scale = 7
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

    # shine: letter pixels only (not outline/shadow), in bright silver
    shine = Image.new("RGBA", title.size, (0, 0, 0, 0))
    shp = shine.load()
    tp = title.load()
    for y in range(title.height):
        for x in range(title.width):
            p = tp[x, y]
            if p[3] > 0 and p[:3] in (C("ebede9")[:3], C("819796")[:3]):
                shp[x, y] = C("ebede9") if p[:3] == C("ebede9")[:3] else C("c7cfcc")

    tag = _render_word("loot. extract. survive.", C("c7cfcc"), C("819796"))
    return title, shine, tag

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
    # sign pole + dark panel (lit text lives on the overlay), sized to fit
    sx, sy = 150, 120
    word = _render_word("spoils", C("411d31"), C("411d31"))  # off-state text
    ghost = word.resize((word.width * 3, word.height * 3), Image.NEAREST)
    var_w = ghost.width
    c.rect(sx + var_w // 2 - 3, sy + ghost.height + 4, sx + var_w // 2 + 3, 360, C("151d28"))
    c.rect(sx - 8, sy - 8, sx + var_w + 18, sy + ghost.height + 4, C("10141f"))
    c.rect(sx - 8, sy - 8, sx + var_w + 18, sy - 6, C("394a50"))
    _paste(c, ghost, sx + 6, sy - 2)
    # neon overlay: the lit sign text + halo, flickered at runtime
    lit = _render_word("spoils", C("df84a5"), C("c65197"))
    lit_big = lit.resize((lit.width * 3, lit.height * 3), Image.NEAREST)
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

def make_dither() -> Image.Image:
    """A 128x128 noise film at ~1/255 alpha. Laid over the world it shifts
    every screen pixel's rounding threshold differently, so slow full-screen
    tint fades dissolve as grain instead of stepping in visible unison
    (the user can SEE single 8-bit steps of the day/night cycle)."""
    rng = random.Random(f"{SEED}:dither")
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    px = img.load()
    for y in range(128):
        for x in range(128):
            if rng.random() < 0.5:
                px[x, y] = (255, 255, 255, 1)
            else:
                px[x, y] = (0, 0, 0, 1)
    return img

def make_dust() -> Image.Image:
    img = Image.new("RGBA", (3, 3), (0, 0, 0, 0))
    img.putpixel((1, 1), (255, 255, 255, 255))
    for p in ((0, 1), (2, 1), (1, 0), (1, 2)):
        img.putpixel(p, (255, 255, 255, 90))
    return img

RAIN_RGB = C("3c5e8b")[:3]  # the puddles' glint blue — rain matches them now

def make_rain_streak() -> Image.Image:
    img = Image.new("RGBA", (2, 9), (0, 0, 0, 0))
    r, g, b = RAIN_RGB
    for y in range(9):
        a = 50 + y * 18
        img.putpixel((0, y), (r, g, b, min(210, a)))
        if y > 3:
            img.putpixel((1, y), (r, g, b, min(140, a - 40)))
    return img

SPLASH_FRAMES = 4
SPLASH_W, SPLASH_H = 14, 10

def make_rain_splash() -> Image.Image:
    """4-frame ground splash, same blue as the rain and the puddles. The
    impact point is at (7,7) of every frame; the game leaves the sprite at
    the drop's landing spot in the WORLD (splashes must never follow the
    camera) and frees it after the last frame."""
    img = Image.new("RGBA", (SPLASH_W * SPLASH_FRAMES, SPLASH_H), (0, 0, 0, 0))
    r, g, b = RAIN_RGB

    def put(f: int, x: int, y: int, a: int) -> None:
        img.putpixel((f * SPLASH_W + 7 + x, 7 + y), (r, g, b, a))

    # f0: the drop core hitting
    put(0, 0, 0, 230)
    put(0, 0, -1, 200)
    put(0, 1, 0, 140)
    # f1: crown up
    for (x, y, a) in ((-1, -1, 210), (1, -1, 210), (0, -2, 190), (0, 0, 150),
                      (-2, 0, 120), (2, 0, 120)):
        put(1, x, y, a)
    # f2: ring widening, crown falling
    for (x, y, a) in ((-3, 0, 150), (3, 0, 150), (-2, -1, 130), (2, -1, 130),
                      (0, -1, 90), (-4, 0, 80), (4, 0, 80)):
        put(2, x, y, a)
    # f3: flat fading ripple
    for (x, y, a) in ((-4, 0, 90), (4, 0, 90), (-3, 1, 70), (3, 1, 70),
                      (-5, 0, 50), (5, 0, 50), (0, 1, 40)):
        put(3, x, y, a)
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
    for name, entry in props.items():
        entries[name] = entry  # 3-tuples, or 4 with light coords (vehicles)
    for name, piece in wall_piece_inventory().items():
        entries[name] = piece
    for tone in ROOF_TONES:
        for v in range(2):
            entries[f"roof_tile_{tone}_{v}"] = make_roof_tile(tone, v)
            entries[f"roof_tile_{tone}_broken_{v}"] = make_roof_tile_broken(tone, v)
        entries[f"roof_fascia_{tone}_s"] = make_roof_fascia(tone, "x")
        entries[f"roof_fascia_{tone}_e"] = make_roof_fascia(tone, "y")
        entries[f"roof_eave_{tone}_n"] = make_roof_eave(tone, "n")
        entries[f"roof_eave_{tone}_w"] = make_roof_eave(tone, "w")
        entries[f"roof_corner_{tone}"] = make_roof_corner(tone)
    entries["roof_vent"] = make_roof_vent()
    entries["roof_hatch"] = make_roof_hatch()
    entries["shadow"] = (make_shadow(), (12, 6), None)

    grabber = Canvas(8, 12)  # HSlider knob for the UI theme
    grabber.rect(0, 0, 7, 11, C("090a14"))
    grabber.rect(1, 1, 6, 10, C("c7cfcc"))
    grabber.rect(1, 9, 6, 10, C("819796"))
    entries["ui_grabber"] = (grabber, (4, 6), None)

    # clip audit: opaque pixels on a canvas border mean the draw ran off the
    # canvas and got silently cut (tv stand, crate stacks... never again).
    # Grid modules that abut by design are exempt.
    _EDGE_OK = ("roof_tile_", "roof_fascia_", "roof_eave_", "roof_corner_",
                "seg_", "post_", "door_", "ui_grabber")
    clipped = []
    for name, entry in entries.items():
        if any(name.startswith(p) for p in _EDGE_OK):
            continue
        img = entry[0].img
        pxa = img.load()
        w, h = img.size
        if any(pxa[x, 0][3] > 0 or pxa[x, h - 1][3] > 0 for x in range(w)) or \
                any(pxa[0, y][3] > 0 or pxa[w - 1, y][3] > 0 for y in range(h)):
            clipped.append(name)
    if clipped:
        raise AssertionError(f"CLIPPED (content touches canvas edge): {clipped}")

    for name, entry in entries.items():
        canvas, origin, collider = entry[0], entry[1], entry[2]
        if name != "shadow":
            assert_palette(canvas.img, name)
        canvas.img.save(OUT / f"{name}.png")
        manifest["props"][name] = {
            "size": [canvas.w, canvas.h], "origin": list(origin), "collider": collider}
        if len(entry) > 3:
            manifest["props"][name]["lights"] = entry[3]
    manifest["families"] = families

    sheet = make_char_sheet()
    assert_palette(sheet, "char")
    sheet.save(OUT / "char.png")
    crouch_sheet = make_char_sheet(crouch=True)
    assert_palette(crouch_sheet, "char_crouch")
    crouch_sheet.save(OUT / "char_crouch.png")
    prone_sheet = make_char_prone_sheet()
    assert_palette(prone_sheet, "char_prone")
    prone_sheet.save(OUT / "char_prone.png")
    manifest["char"] = {
        "frame": [32, 40], "cols": 1 + WALK_FRAMES, "origin": [16, 37],
        "dirs": [d for d, _, _ in DIR_VIEWS],
    }

    title_img, shine_img, tagline_img = make_title()
    title_img.save(OUT / "title.png")
    shine_img.save(OUT / "title_shine.png")
    tagline_img.save(OUT / "tagline.png")
    make_vignette().save(OUT / "vignette.png")    # soft alpha by design
    make_dither().save(OUT / "dither.png")        # anti-banding film
    make_dust().save(OUT / "dust.png")            # white, tinted at runtime
    make_rain_streak().save(OUT / "rain_streak.png")
    make_rain_splash().save(OUT / "rain_splash.png")
    make_lamp_glow().save(OUT / "lamp_glow.png")      # light halo: soft alpha
    make_light_radial().save(OUT / "light_radial.png")  # Light2D textures
    make_light_cone().save(OUT / "light_cone.png")
    make_sniper_round().save(OUT / "sniper_round.png")
    make_alarm_light().save(OUT / "alarm_light.png")
    gem_c, _, _ = make_studio_gem()
    assert_palette(gem_c.img, "studio_gem")
    gem_c.img.save(OUT / "studio_gem.png")
    for i, ring in enumerate(make_signal_rings()):
        ring.save(OUT / f"signal_ring_{i}.png")       # splash fx: alpha-graded
    make_signal_beam().save(OUT / "signal_beam.png")
    make_studio_word().save(OUT / "studio_word.png")

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
    show_walls = ["seg_brick_a_x", "seg_brick_a_y",
                  "seg_brick_a_x_win_0", "seg_brick_a_x_win_1", "seg_brick_a_x_win_2",
                  "seg_brick_a_x_broken_0", "post_brick_a", "seg_brick_b_x",
                  "seg_brick_b_y_win_1", "post_brick_b",
                  "roof_tile_charcoal_0", "roof_fascia_charcoal_s", "roof_vent"]
    fam_show = [n for fam in families.values() for n in fam]
    third = (len(fam_show) + 2) // 3
    rows_imgs = [
        [x3(floors)],
        [x3(entries[n][0].img) for n in show_walls],
        [x3(entries[n][0].img) for n in fam_show[:third]],
        [x3(entries[n][0].img) for n in fam_show[third:2 * third]],
        [x3(entries[n][0].img) for n in fam_show[2 * third:]],
        [x3(sheet), title_img],
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
