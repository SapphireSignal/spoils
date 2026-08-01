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
import math
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
    """Organic wear PATCHES, not dot noise (user call 2026-08-01: no little
    dots anywhere, ever). Each color covers roughly prob*3 of the region as
    a few soft blob-shaped patches — reads as stains and wear instead of
    static. Same signature as the old per-pixel speckle so every call site
    stays valid."""
    pts = list(region)
    if not pts:
        return
    area = len(pts)
    for col, p in zip(colors, probs):
        # QUIET wear: roughly the old coverage, but as 1-3 small soft
        # patches instead of scattered pixels (the first cut at 3x coverage
        # with 14-40px blobs turned every tile into camo clutter)
        want = int(area * min(0.2, p * 0.9))
        placed = 0
        patches = 0
        while placed < want and patches < 3:
            cx, cy = pts[rng.randrange(area)]
            patch = blob(rng, cx, cy, rng.randint(6, 16), region)
            for (qx, qy) in patch:
                c.set(qx, qy, col)
            placed += max(6, len(patch))
            patches += 1

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
    elif kind == "concrete_worn":
        # sun-bleached block: same hue, reads a step lighter — used in
        # district-scale weathering zones so neighborhoods differ subtly
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.018, 0.055)
        speckle(c, rng, region, [CONC_L2], [0.012])
    elif kind == "concrete_damp":
        # shaded/damp block: a step darker, moss creeping in the pores
        region = _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.075, 0.008)
        speckle(c, rng, region, [CONC_D2, C("19332d")], [0.03, 0.012])
    elif kind == "dirt":
        # packed soil with STRUCTURE, not dots: rut dashes worn along the
        # path, clod clusters, the odd stone (flat maroon read as a dead
        # red stripe once the old speckle went away)
        region = _floor_base(c, rng, C("341c27"), C("241527"), C("4d2b32"),
                             0.02, 0.02)
        speckle(c, rng, region, [C("202e37")], [0.05])   # gray mud pulls the
        # red out of the earth — long dirt strips read blood-red without it
        for i in range(rng.randint(10, 14)):
            x = 6 + rng.randrange(52)
            y = 4 + rng.randrange(24)
            for k in range(rng.randint(3, 7)):     # rut dash, iso-slanted
                q = (x - k, y + (k >> 1))
                if q in region:
                    c.set(q[0], q[1], C("241527"))
        for i in range(rng.randint(4, 7)):         # clods
            x = 6 + rng.randrange(52)
            y = 4 + rng.randrange(24)
            for q in ((x, y), (x + 1, y), (x, y + 1)):
                if q in region:
                    c.set(q[0], q[1], C("4d2b32") if q[1] == y else C("241527"))
        for i in range(rng.randint(2, 4)):         # stones
            q = (6 + rng.randrange(52), 4 + rng.randrange(24))
            if q in region:
                c.set(q[0], q[1], C("394a50"))
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
                col = C("241527")  # board seam (grain dots removed — no dot
            c.set(x, y, col)       # noise anywhere, user call)

    elif kind == "screed":
        # warehouse floor: smooth finished concrete, one uniform surface.
        # A building uses ONE screed variant for every cell, so the tile must
        # be feature-free: any baked blob would repeat like wallpaper
        if variant % 2 == 1:
            _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.012, 0.03)
        else:
            _floor_base(c, rng, CONC_BASE, CONC_D1, CONC_L1, 0.012, 0.03)

    elif kind == "forest":
        # woodland floor: GREEN-family patches only — the old warm-brown mix
        # scattered red confetti across every wood (user: no red noise)
        region = _floor_base(c, rng, C("19332d"), C("10141f"), C("25562e"), 0.07, 0.05)
        speckle(c, rng, region, [C("341c27")], [0.018])

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

    elif kind.startswith("sidewalk"):
        # walkway slabs flanking roads: lighter than the asphalt, with joint
        # lines cut ACROSS the run every 16 iso units (16 divides 64, so
        # joints continue seamlessly tile to tile). sidewalk_v runs along the
        # cell +y axis (flanks vertical roads), sidewalk_h along +x. Broken
        # variants lose chunks to the dirt underneath and grow weeds in the
        # bites — nature reclaiming the district.
        # a clearly PALER slab band than the concrete field around it,
        # SMOOTH except for its joint lines (user: no things on the walks;
        # the lines are fine). "crack" variant adds one hairline.
        region = _floor_base(c, rng, CONC_L1, CONC_BASE, CONC_L2, 0.0, 0.0)
        broken = "broken" in kind
        for (x, y) in region:
            if kind.startswith("sidewalk_v"):
                param = (x - 32) * 0.5 - (y - 16)   # joint lines run along +x
            else:
                param = (x - 32) * 0.5 + (y - 16)   # joint lines run along +y
            if param % 16 < 1.1:
                c.set(x, y, CONC_BASE)
        if "crack" in kind and not broken:          # one clean hairline
            x, y = 14 + rng.randrange(24), 6 + rng.randrange(14)
            dx = rng.choice((-1, 1))
            for _ in range(rng.randint(14, 22)):
                if (x, y) in region:
                    c.set(x, y, CONC_BASE)
                    if rng.random() < 0.3:
                        c.set(x + 1, y, CONC_BASE)
                x += dx if rng.random() < 0.7 else -dx
                y += rng.choice((0, 1, 1, -1))
        if broken:
            for _ in range(rng.randint(2, 3)):
                bite = blob(rng, 8 + rng.randrange(48), 6 + rng.randrange(20),
                            rng.randint(10, 26), region)
                for (x, y) in bite:
                    c.set(x, y, C("341c27"))        # down to the dirt
                for (x, y) in list(bite):
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if (nx, ny) in region and (nx, ny) not in bite:
                            if (nx + ny) % 2 == 0:
                                c.set(nx, ny, CONC_D2)
                            elif rng.random() < 0.18:
                                c.set(nx, ny, C("25562e"))  # weeds in the cracks
            x, y = 10 + rng.randrange(24), 6 + rng.randrange(16)
            dx = rng.choice((-1, 1))
            for _ in range(rng.randint(14, 22)):    # one long wandering crack
                if (x, y) in region:
                    c.set(x, y, CONC_D2)
                x += dx if rng.random() < 0.7 else -dx
                y += rng.choice((0, 1, 1, -1))

    elif kind.startswith("crosswalk"):
        # zebra stripes across the road at intersections, HEAVILY worn — most
        # paint is gone, what's left is faded and nibbled. Same iso families
        # as the sidewalk joints; period 8 divides 64 for seam continuity.
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)  # smooth like the road (user: nothing on the asphalt but cracks/holes)
        for (x, y) in region:
            if kind == "crosswalk_v":
                param = (x - 32) * 0.5 - (y - 16)   # stripes run along +x
            else:
                param = (x - 32) * 0.5 + (y - 16)
            if param % 8 < 3.0:
                r = rng.random()
                if r < 0.42:
                    c.set(x, y, C("819796"))        # surviving paint
                elif r < 0.52:
                    c.set(x, y, C("577277"))        # half-worn paint

    elif kind == "manhole":
        # a manhole cover sunk into the asphalt — sparse street furniture
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)  # smooth like the road (user: nothing on the asphalt but cracks/holes)
        cx_, cy_ = 32, 16
        for (x, y) in region:
            d = ((x - cx_) / 9.0) ** 2 + ((y - cy_) / 4.5) ** 2
            if d < 1.0:
                c.set(x, y, C("151d28"))
                if d > 0.62:
                    c.set(x, y, CONC_BASE)          # rim ring
        c.set(cx_ - 3, cy_, C("090a14"))            # pick holes
        c.set(cx_ + 2, cy_, C("090a14"))

    elif kind == "asphalt_stall":
        # parking stall separator: pale worn line along the lower-left edge
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)  # smooth like the road (user: nothing on the asphalt but cracks/holes)
        for (x, y) in region:
            if not in_diamond(x - 2, y + 1) and rng.random() < 0.8:
                c.set(x, y, C("819796"))

    elif kind == "asphalt":
        # SMOOTH road surface (user call) — damage lives in its own tiles
        _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)
    elif kind == "asphalt_crack":
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)
        x, y = 16 + rng.randrange(30), 6 + rng.randrange(16)
        dx = rng.choice((-1, 1))
        for _ in range(rng.randint(16, 26)):        # a wandering crack
            if (x, y) in region:
                c.set(x, y, CONC_D2)
                if rng.random() < 0.35:
                    c.set(x + 1, y, C("090a14"))
            x += dx if rng.random() < 0.72 else -dx
            y += rng.choice((0, 1, 1, -1))
    elif kind == "asphalt_hole":
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)
        hx = 22 + rng.randrange(20)
        hy = 9 + rng.randrange(12)
        hole = blob(rng, hx, hy, rng.randint(12, 22), region)
        for (x, y) in hole:                          # a small pothole
            c.set(x, y, C("090a14"))
        for (x, y) in list(hole):                    # chipped rim
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in region and (nx, ny) not in hole:
                    c.set(nx, ny, CONC_BASE if (nx + ny) % 3 == 0 else CONC_D2)
    elif kind == "asphalt_line":
        # center dashes for roads running along the cell +y axis (screen SW).
        # dash period 16 px: 64/16 tessellates, so dashes continue seamlessly
        # from tile to tile (a 20 px period phased randomly at every seam)
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)  # smooth like the road (user: nothing on the asphalt but cracks/holes)
        for (x, y) in region:
            if abs((x - 32) * 0.5 + (y - 16)) < 1.5 and (x // 8) % 2 == 0 and rng.random() < 0.94:
                c.set(x, y, C("de9e41"))
    elif kind == "asphalt_line_h":
        # same dashes for roads running along the cell +x axis (screen SE)
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)  # smooth like the road (user: nothing on the asphalt but cracks/holes)
        for (x, y) in region:
            if abs((x - 32) * 0.5 - (y - 16)) < 1.5 and (x // 8) % 2 == 0 and rng.random() < 0.94:
                c.set(x, y, C("de9e41"))

    elif kind == "ballast":
        # trainyard gravel bed: dark base with STONES — small 2-4px shapes
        # with their own shadow, clustered (structure, never dot noise)
        region = _floor_base(c, rng, C("202e37"), C("151d28"), C("394a50"), 0.0, 0.0)
        for _ in range(rng.randint(6, 9)):
            cx_, cy_ = 6 + rng.randrange(52), 4 + rng.randrange(24)
            for s in range(rng.randint(3, 6)):
                sx = cx_ + rng.randint(-5, 5)
                sy = cy_ + rng.randint(-3, 3)
                if (sx, sy) in region and (sx + 1, sy) in region:
                    c.set(sx, sy, C("394a50"))
                    c.set(sx + 1, sy, C("577277") if (sx + sy) % 2 else C("394a50"))
                    if (sx, sy + 1) in region:
                        c.set(sx, sy + 1, C("151d28"))   # stone shadow

    elif kind.startswith("rail_cross"):
        # a level crossing: rails let into the asphalt, flange grooves beside
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)
        along_x = kind.endswith("_x")
        for (x, y) in region:
            p = (x - 32) * 0.5 - (y - 16) if along_x else (x - 32) * 0.5 + (y - 16)
            for rail_c in (-3.5, 3.5):
                d = abs(p - rail_c)
                if d < 0.8:
                    c.set(x, y, C("819796") if (x + y) % 9 else C("577277"))
                elif d < 1.7:
                    c.set(x, y, C("090a14"))            # flange groove

    elif kind.startswith("rail"):
        # rails on the ballast bed, ties beneath — period 8 divides 64 so the
        # track continues seamlessly tile to tile. rail_x runs along the cell
        # +x axis (screen SE), rail_y along +y (screen SW).
        region = _floor_base(c, rng, C("202e37"), C("151d28"), C("394a50"), 0.0, 0.0)
        for _ in range(rng.randint(4, 6)):              # sparse stones outside the ties
            sx, sy = 6 + rng.randrange(52), 4 + rng.randrange(24)
            if (sx, sy) in region:
                c.set(sx, sy, C("394a50"))
                if (sx, sy + 1) in region:
                    c.set(sx, sy + 1, C("151d28"))
        along_x = kind.endswith("_x")
        for (x, y) in region:
            p = (x - 32) * 0.5 - (y - 16) if along_x else (x - 32) * 0.5 + (y - 16)
            q = (x - 32) * 0.5 + (y - 16) if along_x else (x - 32) * 0.5 - (y - 16)
            if abs(p) < 6.5 and q % 8 < 2.2:            # wooden tie
                c.set(x, y, C("341c27") if q % 8 < 1.4 else C("241527"))
        for (x, y) in region:                            # rails OVER the ties
            p = (x - 32) * 0.5 - (y - 16) if along_x else (x - 32) * 0.5 + (y - 16)
            for rail_c in (-3.5, 3.5):
                d = p - rail_c
                if abs(d) < 0.8:
                    c.set(x, y, C("819796"))            # polished head
                elif 0.8 <= d < 1.8:
                    c.set(x, y, C("394a50"))            # web shadow side

    elif kind == "plaza":
        # courtyard pavers: pale slabs with a diamond joint grid, period 16
        # (divides 64 — seams continue). A few WHOLE pavers sit a shade
        # deeper — worn patchwork, never a checkerboard, never dots
        region = _floor_base(c, rng, CONC_L1, CONC_BASE, CONC_L2, 0.0, 0.0)
        worn = {(rng.randrange(-2, 2), rng.randrange(-2, 2))
                for _ in range(rng.randint(1, 2))}
        for (x, y) in region:
            u = (x - 32) * 0.5 + (y - 16)
            v = (x - 32) * 0.5 - (y - 16)
            if (int(u // 16), int(v // 16)) in worn:
                c.set(x, y, CONC_BASE)
            if u % 16 < 1.1 or v % 16 < 1.1:
                c.set(x, y, CONC_BASE)                  # joint lines
        if variant == 2:                                 # one cracked slab
            x, y = 14 + rng.randrange(28), 6 + rng.randrange(14)
            dx = rng.choice((-1, 1))
            for _ in range(rng.randint(12, 18)):
                if (x, y) in region:
                    c.set(x, y, CONC_D1)
                x += dx if rng.random() < 0.7 else -dx
                y += rng.choice((0, 1, 1, -1))
    else:
        raise ValueError(kind)
    return c

FLOOR_TILES = [
    ("concrete_0", ("concrete", 0)), ("concrete_1", ("concrete", 1)),
    ("concrete_2", ("concrete", 2)), ("concrete_3", ("concrete", 3)),
    ("concrete_4", ("concrete", 4)), ("concrete_5", ("concrete", 5)),
    ("crack_0", ("crack", 0)), ("crack_1", ("crack", 1)), ("crack_2", ("crack", 2)),
    ("crack_3", ("crack", 3)),
    ("stain_0", ("stain", 0)), ("stain_1", ("stain", 1)), ("stain_2", ("stain", 2)),
    ("moss_0", ("moss", 0)), ("moss_1", ("moss", 1)),
    ("dirt_0", ("dirt", 0)), ("dirt_1", ("dirt", 1)), ("dirt_2", ("dirt", 2)),
    ("dirt_3", ("dirt", 3)),
    ("dirt_blend_0", ("dirt_blend", 0)), ("dirt_blend_1", ("dirt_blend", 1)),
    ("dirt_blend_2", ("dirt_blend", 2)),
    ("asphalt_0", ("asphalt", 0)), ("asphalt_1", ("asphalt", 1)),
    ("asphalt_crack_0", ("asphalt_crack", 0)), ("asphalt_crack_1", ("asphalt_crack", 1)),
    ("asphalt_hole_0", ("asphalt_hole", 0)), ("asphalt_hole_1", ("asphalt_hole", 1)),
    ("asphalt_line", ("asphalt_line", 0)), ("asphalt_line_h", ("asphalt_line_h", 0)),
    ("wood_0", ("wood", 0)), ("wood_1", ("wood", 1)), ("wood_2", ("wood", 2)),
    ("wood_3", ("wood", 3)), ("wood_4", ("wood", 4)),
    ("asphalt_stall", ("asphalt_stall", 0)),
    ("screed_0", ("screed", 0)), ("screed_1", ("screed", 1)),
    ("screed_2", ("screed", 2)), ("screed_3", ("screed", 3)),
    ("forest_0", ("forest", 0)), ("forest_1", ("forest", 1)),
    ("forest_2", ("forest", 2)), ("forest_3", ("forest", 3)),
    ("grass_blend_0", ("grass_blend", 0)), ("grass_blend_1", ("grass_blend", 1)),
    ("grass_blend_2", ("grass_blend", 2)),
    ("concrete_worn_0", ("concrete_worn", 0)), ("concrete_worn_1", ("concrete_worn", 1)),
    ("concrete_worn_2", ("concrete_worn", 2)),
    ("concrete_damp_0", ("concrete_damp", 0)), ("concrete_damp_1", ("concrete_damp", 1)),
    ("concrete_damp_2", ("concrete_damp", 2)),
    ("sidewalk_v_0", ("sidewalk_v", 0)),
    ("sidewalk_h_0", ("sidewalk_h", 0)),
    ("sidewalk_v_crack_0", ("sidewalk_v_crack", 0)),
    ("sidewalk_v_crack_1", ("sidewalk_v_crack", 1)),
    ("sidewalk_h_crack_0", ("sidewalk_h_crack", 0)),
    ("sidewalk_h_crack_1", ("sidewalk_h_crack", 1)),
    ("sidewalk_v_broken_0", ("sidewalk_v_broken", 0)),
    ("sidewalk_v_broken_1", ("sidewalk_v_broken", 1)),
    ("sidewalk_h_broken_0", ("sidewalk_h_broken", 0)),
    ("sidewalk_h_broken_1", ("sidewalk_h_broken", 1)),
    ("crosswalk_v", ("crosswalk_v", 0)), ("crosswalk_h", ("crosswalk_h", 0)),
    ("manhole_0", ("manhole", 0)),
    ("ballast_0", ("ballast", 0)), ("ballast_1", ("ballast", 1)),
    ("ballast_2", ("ballast", 2)),
    ("rail_x", ("rail_x", 0)), ("rail_y", ("rail_y", 0)),
    ("rail_cross_x", ("rail_cross_x", 0)), ("rail_cross_y", ("rail_cross_y", 0)),
    ("plaza_0", ("plaza", 0)), ("plaza_1", ("plaza", 1)), ("plaza_2", ("plaza", 2)),
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

STORY_H = 32  # extra face height of a second story (roof lifts by this too)

def _draw_seg_window(c: Canvas, ox: int, oy: int, axis: str,
                     face_h: int, wi: int, top: int, w: int, h: int,
                     boarded: bool) -> None:
    """One window opening on a wall face. GLASS, not a black void (user:
    "make them see through like how an actual window would look"): sky-blue
    panes darkening toward the sill, a diagonal sheen streak, and a thin
    mullion cross. Boarded variant keeps its planks over a dark gap."""
    for i in range(wi, min(32, wi + w)):
        x = ox + 16 + (-16 + i)
        fy_base = oy + _seg_base_fy(axis, i)
        face_top = fy_base - face_h + 1
        for fy in range(top, top + h):
            row = fy - top
            col = C("3c5e8b")                        # daytime glass
            if row >= int(h * 0.55):
                col = C("253a5e")                    # interior shadow low
            sheen = (i * 2 - row) % 23               # one diagonal reflection
            if sheen in (4, 5):
                col = C("73bed3")
            elif sheen == 6:
                col = C("a4dddb")
            if boarded:
                col = C("10141f")                    # dark gap behind boards
            # mullion cross: one center column, one center row
            if i == wi + w // 2 or row == h // 2:
                col = C("151d28")
            c.set(x, face_top + fy, col)
        c.set(x, face_top + top - 1, C("341c27"))    # lintel
        c.set(x, face_top + top + h, C("819796"))    # sill
        if boarded:
            for bi, plank in enumerate(range(top + 1, top + h, 3)):
                c.set(x, face_top + plank + ((i + bi) % 2),
                      C("884b2b") if (i + bi) % 2 else C("602c2c"))
    for i in (wi - 1, wi + w):  # jambs
        if 0 <= i < 32:
            x = ox + 16 + (-16 + i)
            fy_base = oy + _seg_base_fy(axis, i)
            face_top = fy_base - face_h + 1
            for fy in range(top - 1, top + h + 1):
                c.set(x, face_top + fy, C("341c27"))

def make_wall_segment(style: str, axis: str, window_variant: int = -1,
                      broken_seed: int = -1, variant: int = 0,
                      stories: int = 1, upper_only: bool = False) -> tuple[Canvas, tuple, list]:
    """upper_only: just the second-story band + coping — the transom piece
    that closes the hole above a ground-floor door on two-story walls."""
    rng = random.Random(
        f"{SEED}:seg:{style}:{axis}:{window_variant}:{broken_seed}:{variant}:{stories}:{upper_only}")
    base_col, mortar_col = (C(n) for n in BRICK_STYLES[style][axis])
    extra = STORY_H if stories == 2 else 0
    face_h = WALL_H + extra
    # canvas: 32 wide edge + coping overhang + outline margins
    c = Canvas(48, 66 + extra)
    ox = 8
    oy = 56 + extra
    cop_dx = SEG_THICK if axis == "x" else -SEG_THICK  # coping goes to the back

    heights: list[int] = []
    if broken_seed >= 0:
        h = rng.randint(8, 20)
        for i in range(32):
            if i % rng.choice((3, 4, 5)) == 0:
                h = max(5, min(24, h + rng.choice((-6, -4, 4, 6))))
            heights.append(h)
    else:
        heights = [face_h] * 32

    for i in range(32):
        x = ox + 16 + (-16 + i)
        fy_base = oy + _seg_base_fy(axis, i)
        h = heights[i]
        for k in range(h):
            y = fy_base - h + 1 + k
            face_row = (y - (fy_base - face_h + 1))
            if upper_only and face_row > STORY_H:
                continue          # transom piece: nothing below the floor line
            col = _seg_brick(rng, base_col, mortar_col, i, face_row)
            if stories == 2 and face_row in (STORY_H - 1, STORY_H):
                # string course: a pale concrete band marking the floor line
                col = CONC_L1 if (i + face_row) % 2 else CONC_BASE
            c.set(x, y, col)
        if broken_seed >= 0:  # broken lip
            cap_y = fy_base - h
            c.set(x, cap_y, C("819796") if rng.random() < 0.5 else base_col)
        else:
            # coping: stepped parallelogram toward the back
            for j in range(abs(cop_dx) + 1):
                jx = x + (j if cop_dx > 0 else -j)
                jy = fy_base - face_h - ((j + 1) // 2)
                r = rng.random()
                col = CONC_L1
                if r < 0.06:
                    col = CONC_BASE
                elif r < 0.09:
                    col = CONC_L2
                c.set(jx, jy, col)
            if i % 2 == 0:  # light crease where coping meets the face
                c.set(x, fy_base - face_h, CONC_L2)

    if window_variant >= 0:
        wi, top, w, h, boarded = SEG_WINDOWS[window_variant]
        # ground-floor window (below the string course on two-story walls)
        _draw_seg_window(c, ox, oy, axis, face_h, wi, top + extra, w, h, boarded)
        if stories == 2:
            # the upper room's window, stacked over the ground one
            up_h = min(h, STORY_H - 12)
            _draw_seg_window(c, ox, oy, axis, face_h, wi, 7, w, up_h, False)

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
    return c, origin, None if upper_only else ["poly", poly]

def make_wall_post(style: str, stories: int = 1) -> tuple[Canvas, tuple, list]:
    # exactly the face height: the cap sits flush in the roof plane, closing
    # the fascia line at each corner instead of poking through the roof
    rng = random.Random(f"{SEED}:post:{style}:{stories}")
    post_h = WALL_H + (STORY_H if stories == 2 else 0)
    c = Canvas(18, 62 + (STORY_H if stories == 2 else 0))
    lit, dark = (C(n) for n in BRICK_STYLES[style]["x"])
    _, darker = (C(n) for n in BRICK_STYLES[style]["y"])
    bottoms = iso_prism(c, 2, 1, 12, 6, post_h, lit, lit, dark)
    for x in range(12):  # concrete cap
        y = bottoms[x]
        c.set(2 + x, y, CONC_L1)
        c.set(2 + x, y - 1, CONC_L1 if x % 2 else CONC_L2)
    for x in range(12):  # course shading
        for y in range(bottoms[x] + 2, bottoms[x] + post_h, 4):
            if rng.random() < 0.6:
                c.set(2 + x, y, dark if x < 6 else darker)
    c.outline_auto()
    return c, (8, 1 + post_h + 3), ["circle", 4.0]

def wall_piece_inventory() -> dict[str, tuple[Canvas, tuple, list]]:
    pieces: dict[str, tuple[Canvas, tuple, list]] = {}
    for style in BRICK_STYLES:
        for axis in ("x", "y"):
            # THREE plain variants per style/axis: long walls reused one
            # image and the repetition showed (user: no obvious patterns)
            pieces[f"seg_{style}_{axis}"] = make_wall_segment(style, axis)
            for sv in (1, 2):
                pieces[f"seg_{style}_{axis}_v{sv}"] = make_wall_segment(
                    style, axis, -1, -1, sv)
            for v in range(len(SEG_WINDOWS)):
                pieces[f"seg_{style}_{axis}_win_{v}"] = make_wall_segment(style, axis, v)
            for b in range(2):
                pieces[f"seg_{style}_{axis}_broken_{b}"] = make_wall_segment(
                    style, axis, -1, b)
            # two-story pieces: taller face, floor string course, stacked
            # windows — the town houses that grew a second floor
            pieces[f"seg2_{style}_{axis}"] = make_wall_segment(
                style, axis, -1, -1, 0, 2)
            for sv in (1, 2):
                pieces[f"seg2_{style}_{axis}_v{sv}"] = make_wall_segment(
                    style, axis, -1, -1, sv, 2)
            for v in range(len(SEG_WINDOWS)):
                pieces[f"seg2_{style}_{axis}_win_{v}"] = make_wall_segment(
                    style, axis, v, -1, 0, 2)
            pieces[f"seg2_{style}_{axis}_upper"] = make_wall_segment(
                style, axis, -1, -1, 0, 2, True)
        pieces[f"post_{style}"] = make_wall_post(style)
        pieces[f"post2_{style}"] = make_wall_post(style, 2)
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
        c = Canvas(2 * r + 6, h + r + 6)
        cx = r + 3
        top_cy = r // 2 + 2
        ell_h = max(2, r // 2)

        def edge_dy(dx: int) -> int:
            f = 1.0 - (dx * dx) / float(r * r)
            return int(round(math.sqrt(max(0.0, f)) * ell_h))

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
        # upright tank as a true iso cylinder: elliptical shoulder, domed
        # cap with a curved highlight, walls hanging off the ellipse curve
        r = 5
        c = Canvas(2 * r + 6, h + 12)
        cx = r + 3
        top_cy = 7

        def edge_dy(dx: int) -> int:
            f = 1.0 - (dx * dx) / float(r * r)
            return int(round(math.sqrt(max(0.0, f)) * (r // 2 + 1)))

        for dx in range(-r, r + 1):  # domed cap above the shoulder ellipse
            dy = edge_dy(dx)
            for y in range(top_cy - dy - 2, top_cy + dy + 1):
                col = base
                if y < top_cy - dy:
                    col = lite                       # dome crown
                elif dx < -1 and y <= top_cy:
                    col = lite
                elif y >= top_cy + dy - 1:
                    col = dark
                c.set(cx + dx, y, col)
        c.rect(cx - 1, 2, cx, 4, C("577277"))        # valve stub on top
        c.set(cx + 1, 3, C("394a50"))
        for dx in range(-r, r + 1):  # walls follow the ellipse's lower edge
            dy = edge_dy(dx)
            t = (dx + r) / float(2 * r)
            col = lite if t < 0.28 else (base if t < 0.74 else dark)
            for y in range(top_cy + dy, top_cy + dy + h - 8):
                c.set(cx + dx, y, col)
        band_h = (h - 8) // 2
        for dx in range(-r, r + 1):  # safety band follows the curvature
            dy = edge_dy(dx)
            c.set(cx + dx, top_cy + dy + band_h, dark)
            c.set(cx + dx, top_cy + dy + band_h - 1, glint if dx % 2 else base)
            c.set(cx + dx, top_cy + dy + h - 8, C("202e37"))  # foot ring
        for _ in range(rng.randint(2, 5)):
            fx = rng.randrange(cx - r + 1, cx + r - 1)
            c.set(fx, top_cy + edge_dy(fx - cx) + rng.randrange(3, h - 10), C("602c2c"))
        c.outline_auto()
        return c, (cx, top_cy + h - 7), ["circle", 4.0]
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
    # tire stack as stacked tori: each tire is an ellipse ring with a side
    # wall; the top one shows its tread ellipse AND the dark hole through
    # the middle — that hole is what sells the 3D (user: everything 3D)
    c = Canvas(32, 17 + 5 * count)
    cx = 15
    r_out = 11

    def ell(dx: int, r: int) -> int:
        f = 1.0 - (dx * dx) / float(r * r)
        return int(round(math.sqrt(max(0.0, f)) * (r * 0.45)))

    for i in range(count):
        jx = rng.randint(-1, 1)
        base_y = 8 + 5 * (count - 1 - i)
        top = i == count - 1
        for dx in range(-r_out, r_out + 1):  # side wall band
            dy = ell(dx, r_out)
            for y in range(base_y + dy, base_y + dy + 5):
                t = (dx + r_out) / float(2 * r_out)
                c.set(cx + jx + dx, y, C("151d28") if t < 0.6 else C("10141f"))
        if top:
            for dx in range(-r_out, r_out + 1):  # tread ellipse on top
                dy = ell(dx, r_out)
                for y in range(base_y - dy, base_y + dy + 1):
                    col = C("151d28")
                    if y <= base_y - dy + 1 and dx < 2:
                        col = C("202e37")            # rim highlight NW
                    c.set(cx + jx + dx, y, col)
            for dx in range(-5, 6):              # the hole through the middle
                dy = ell(dx, 5)
                for y in range(base_y - dy, base_y + dy + 1):
                    c.set(cx + jx + dx, y, C("090a14"))
        else:
            for dx in range(-r_out, r_out + 1):  # sliver of this tire's top
                dy = ell(dx, r_out)
                c.set(cx + jx + dx, base_y + dy, C("202e37") if dx < 0 else C("151d28"))
    c.outline_auto()
    return c, (15, 8 + 5 * count + 4), ["circle", 7.0 if count > 1 else 6.0]

def draw_pallet(broken: bool, stacked: bool) -> tuple[Canvas, tuple, list]:
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
        peak = c.h - 3 - max(0, h)
        for y in range(peak, c.h - 2):
            # a mound, not a blob: lit western slope, shaded eastern slope,
            # a bright ridge along the crest, dark contact at the ground
            depth = y - peak
            col = grays[1]
            if x < cx - 2 and depth > 0:
                col = grays[2] if rng.random() < 0.6 else grays[1]
            elif x > cx + 2:
                col = grays[0] if rng.random() < 0.7 else grays[1]
            if depth == 0 and rng.random() < 0.7:
                col = grays[3] if abs(x - cx) < w // 4 else grays[2]
            if y >= c.h - 3:
                col = grays[0]
            c.set(x, y, col)
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
    # upright column as a real iso PRISM: diamond top, two shaded faces, a
    # plinth — the old front-view rectangle read completely flat (user call)
    h = 44 if kind == "tall" else 26
    c = Canvas(20, h + 14)
    rows = small_diamond_rows(12, 6)
    ox, oy = 3, 3
    bottoms = [0] * 12
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            bottoms[x] = i
    for x in range(12):  # shaft: lit west face, shaded east
        b = oy + bottoms[x]
        for y in range(b + 1, b + h + 1):
            col = CONC_L1 if x < 4 else (CONC_BASE if x < 8 else CONC_D1)
            if rng.random() < 0.07:
                col = CONC_D1 if x < 8 else CONC_D2
            c.set(ox + x, y, col)
    if kind == "tall":  # clean cap
        for i, (x0, x1) in enumerate(rows):
            for x in range(x0, x1 + 1):
                c.set(ox + x, oy + i, CONC_L2 if i < 3 else CONC_L1)
    else:  # snapped: rough broken top with rebar
        for i, (x0, x1) in enumerate(rows):
            for x in range(x0, x1 + 1):
                jag = rng.randint(0, 2)
                c.set(ox + x, oy + i + jag, CONC_BASE if rng.random() < 0.6 else CONC_D1)
                if jag > 1:
                    c.set(ox + x, oy + i, (0, 0, 0, 0))
        for rx in (4, 8):
            top = oy + bottoms[rx]
            for y in range(top - 3, top + 1):
                c.set(ox + rx, y, C("602c2c"))
            c.set(ox + rx + 1, top - 3, C("884b2b"))
    for x in range(12):  # plinth at the base
        b = oy + bottoms[x] + h
        c.set(ox + x - 1 if x == 0 else ox + x, b + 1, CONC_BASE if x < 8 else CONC_D1)
        c.set(ox + x, b + 2, CONC_D1 if x < 8 else CONC_D2)
    c.outline_auto()
    return c, (ox + 6, oy + h + 5), ["circle", 6.0]

# ------------------------------------------------------------ furniture -----
# Interior dressing so buildings read as lived-in places, not empty shells.

def make_couch() -> tuple[Canvas, tuple, list]:
    c = Canvas(50, 46)
    seat_top, seat_l, seat_r = C("752438"), C("411d31"), C("241527")
    iso_prism(c, 3, 12, 44, 22, 8, seat_top, seat_l, seat_r)
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
    iso_prism(c, 2, 20, 28, 14, 8, C("4d2b32"), C("341c27"), C("241527"))
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
    for lx, ly in ((6, 15), (24, 15), (15, 20)):  # legs
        c.vline(lx, ly - 4, ly + 6, C("341c27"))
    c.outline_auto()
    return c, (15, 24), ["diamond", 13.0, 7.0]

def make_chair() -> tuple[Canvas, tuple, list]:
    c = Canvas(18, 28)
    iso_prism(c, 3, 12, 12, 6, 6, C("602c2c"), C("4d2b32"), C("341c27"))
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
    """Industrial shelving with a UNIQUE, unevenly-jostled load per variant.
    WIDER + DEEPER frame (user: shelves read too small for their boxes) and
    properly human stacking: staggered heights, off-grid offsets, boxes
    shoved against each other, mixed sizes — never a tidy row (user: 'like
    someone actually stacked them there')."""
    rng = random.Random(f"{SEED}:rack:{variant}")
    # height stays under the wall cap; the growth is in width and depth
    c = Canvas(84, 58)
    steel, steel_d = C("394a50"), C("202e37")
    for level_y in (20, 38):
        rows = small_diamond_rows(68, 34)
        for i, (x0, x1) in enumerate(rows):
            for x in range(x0, x1 + 1):
                c.set(4 + x, level_y + i // 2, steel if i % 2 else steel_d)
    for ux in (6, 39, 72):
        c.vline(ux, 18, 53, steel_d)
        c.vline(ux + 1, 18, 53, steel)
    for level_base in (7, 25):
        slots = [7, 27, 47]
        rng.shuffle(slots)
        for i in range(rng.randint(1, 3)):
            w = rng.choice((12, 16, 20, 24))   # iso boxes need w % 4 == 0
            box, _, _ = draw_crate(rng, w, rng.randint(7, 11), rng.randrange(2),
                                   rng.random() < 0.35, rng.random() < 0.3)
            bx = slots[i] + rng.randint(-4, 4)
            by = level_base + rng.randint(-2, 3)
            _paste_canvas(c, box, bx, by, rng.random() < 0.5)
            if rng.random() < 0.35 and w <= 20:  # a smaller box shoved against it
                box2, _, _ = draw_crate(rng, rng.choice((8, 12)),
                                        rng.randint(5, 8), rng.randrange(2),
                                        rng.random() < 0.4, False)
                _paste_canvas(c, box2, bx + w + rng.randint(-1, 4),
                              by + rng.randint(3, 6), rng.random() < 0.5)
    c.outline_auto()
    return c, (38, 51), ["diamond", 34.0, 14.0]

ROOF_DEPTH = 12  # top-face depth in px — the old 6 read as a paper-thin car

def make_vehicle(kind: str, scheme: int, rev: bool = False,
                 broken: bool = False, door_open: bool = False) -> tuple[Canvas, tuple, list]:
    """Iso vehicle along the screen (2,1) diagonal: side face + a DEEP roof
    plane + a visible SE end cap, so it reads as a solid body, not a cutout.
    rev=False: front at the NW end (heading NW, tail lights on the end cap).
    rev=True:  profile reversed (heading SE, head lights + grille on the cap,
    windshield glass on the roof near the cap). Mirrored copies of both give
    the NE / SW headings — all four lane directions ship pre-baked.
    broken=True: shattered glass, rust, dents — looted where it stands.
    door_open=True: same intact car with its door swung out — the enter/exit
    frame for DRIVEABLE cars (texture swap is the animation).
    kind "bus": long transit body with a passenger door and roof hatches."""
    rng = random.Random(f"{SEED}:vehicle:{kind}:{scheme}:{rev}:{broken}:{door_open}")
    palettes = [
        ("752438", "411d31", "241527"),   # oxblood
        ("577277", "394a50", "202e37"),   # gray
        ("25562e", "19332d", "10141f"),   # olive
        ("884b2b", "602c2c", "341c27"),   # rust
    ]
    body_c, body_d, body_dd = (C(n) for n in palettes[scheme])
    glass, glass_d = C("3c5e8b"), C("253a5e")
    L = 64 if kind == "bus" else 46
    wheels = (9, 50) if kind == "bus" else (8, 34)
    prof = []
    if kind == "bus":
        for i in range(L):
            if i < 2:
                h = 9
            elif i < 5:
                h = 9 + (i - 1) * 5     # windshield rake up to the flat roof
            else:
                h = 24
            prof.append(min(h, 24))
        win_lo, win_hi = 7, L - 4
        glass_roof = (2, 6)
    elif kind == "car":
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
            else:
                # bed wall, LEVEL all the way into a full-height tailgate.
                # The old 2-column drop to 8 shaved the bed's rear corner
                # into a diagonal ramp — the exact spot the user circled
                # as "the back of the truck is missing"
                h = 10
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
    oy = 40 if kind == "bus" else 34  # tall flat bus roof needs headroom
    ox = 6
    c = Canvas(104 if kind == "bus" else 84, 86 if kind == "bus" else 70)
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
    # the end face is a FULL-WIDTH wall: it spans the body along the NE
    # width axis exactly like the roof plane does, hanging from the rear
    # rim (tailgate / trunk lip / grille top) down to a bumper strip. The
    # old lengthwise corner stub read as the whole back "hanging out" off
    # one side (user, with the circled sheet: "it should be on the back
    # like a normal truck" — then confirmed the same flaw on cars).
    wall_x0 = ox + L - 1
    wall_top0 = oy + (L - 1) // 2 - clear - cap_h
    wall_bot0 = oy + (L - 1) // 2 - clear
    for t in range(1, ROOF_DEPTH + 1):
        x = wall_x0 + t
        rise = t // 2
        for y in range(wall_top0 - rise, wall_bot0 - rise + 1):
            c.set(x, y, body_dd)
        c.set(x, wall_top0 - rise, body_d)             # lit rim along the top
        if 1 < t < ROOF_DEPTH:                          # gate / trunk shutline
            c.set(x, wall_top0 - rise + 2, C("10141f"))
        c.set(x, wall_bot0 - rise, C("202e37"))        # bumper strip
        c.set(x, wall_bot0 - rise - 1, C("202e37"))
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
            c.set(x, y, body_dd)
        c.set(x, base - clear, C("202e37"))    # bumper hint
    # a 1px light sliver on the far corner (headlight fwd art, tail rev art)
    c.set(ox - 2, oy - 1 - clear - far_h + 2, C("de9e41") if not rev else C("752438"))
    # lights sit at BOTH ends of the full-width face, like a real vehicle
    lights_px: list[tuple[int, int]] = []  # absolute px, for the alarm flashers
    light_col = C("e8c170") if rev else (C("cf573c") if scheme == 0 else C("a53030"))
    for t in (1, 2, ROOF_DEPTH - 2, ROOF_DEPTH - 1):
        c.set(wall_x0 + t, wall_top0 - t // 2 + 3, light_col)
    lights_px = [(wall_x0 + 1, wall_top0 + 3),
                 (wall_x0 + ROOF_DEPTH - 1, wall_top0 - (ROOF_DEPTH - 1) // 2 + 3)]
    if rev:  # grille slits across the middle of the front face
        for gt in range(4, ROOF_DEPTH - 3):
            c.set(wall_x0 + gt, wall_top0 - gt // 2 + 4, C("151d28"))
            c.set(wall_x0 + gt, wall_top0 - gt // 2 + 6, C("151d28"))
    for wf in wheels:  # wheel arches + wheels
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
    if kind == "bus":
        # the passenger door: a full-height dark leaf pair near the visible
        # end, with a center split and a step well
        door_lo = (win_hi - 12) if not rev else (win_lo + 5)
        for i in range(door_lo, door_lo + 6):
            x = ox + i
            base = oy + i // 2
            top = base - clear - prof[i] + 3
            for y in range(top, base - clear):
                c.set(x, y, C("151d28") if i != door_lo + 3 else C("090a14"))
            c.set(x, base - clear, C("090a14"))          # step well
        for t in range(int(L * 0.30), int(L * 0.34)):    # roof hatch 1
            x = ox + t
            for rt in (5, 6, 7):
                c.set(x + rt, oy + t // 2 - clear - prof[t] - (rt + 1) // 2, C("151d28"))
        for t in range(int(L * 0.62), int(L * 0.66)):    # roof hatch 2
            x = ox + t
            for rt in (5, 6, 7):
                c.set(x + rt, oy + t // 2 - clear - prof[t] - (rt + 1) // 2, C("151d28"))
        for i in range(3, L - 3):                        # livery stripe
            x = ox + i
            base = oy + i // 2
            c.set(x, base - clear - 4, C("c7cfcc") if scheme != 1 else C("de9e41"))
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
    if broken or door_open:
        # the open door: a panel swung out over the sill — CONNECTED to the
        # body (it hinges at the sill line, no floating debris). The same
        # panel is the driveable cars' enter/exit frame (door_open).
        door_i = (win_lo + win_hi) // 2 + rng.randrange(-3, 3)
        for k in range(6):
            x = ox + door_i + k
            base = oy + (door_i + k) // 2
            top = base - clear - 1
            for y in range(top, top + 5 - (k // 3)):
                c.set(x, y, body_d if 0 < k < 5 else body_dd)
            if 1 < k < 4:
                c.set(x, top + 2, C("090a14") if broken else glass_d)
        c.set(ox + door_i + 4, oy + (door_i + 4) // 2 - clear + 2, C("819796"))  # handle
    if broken:
        # broken into reads as EVENTS, not damage noise (user call): the
        # hanging door, one flat tire, dark side glass, some rust
        for _ in range(rng.randint(8, 12)):  # rust bloom
            x = ox + rng.randrange(2, L - 2)
            base = oy + x // 2
            y = base - clear - rng.randrange(1, max(2, prof[min(L - 1, x - ox)] - 1))
            c.set(x, y, C("884b2b") if rng.random() < 0.6 else C("602c2c"))
        # one flat tire: the rear wheel squashes onto the ground
        flat_x = ox + wheels[1] + 3
        flat_y = oy + (wheels[1] + 3) // 2 - 1
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
    collider = ["diamond", 38.0, 19.0] if kind == "bus" else ["diamond", 29.0, 15.0]
    return cropped, origin, collider, lights_rel

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

def draw_bush(rng: random.Random, variant: int) -> tuple[Canvas, tuple, list | None]:
    """A leafy clump the player can push through — no collider. The game's
    Foliage manager wiggles it and fades it while you're inside."""
    w = rng.choice((16, 20, 24))
    h = w // 2 + rng.randint(1, 3)
    c = Canvas(w + 8, h + 10)
    cx = c.w // 2
    cy = h // 2 + 4
    pts: set = set()
    for dx in range(-w // 2, w // 2 + 1):
        e = 1.0 - (dx / (w / 2.0)) ** 2
        if e <= 0.0:
            continue
        half = h / 2.0 * (e ** 0.5) * rng.uniform(0.82, 1.12)
        for dy in range(int(-half), int(half) + 1):
            pts.add((cx + dx, cy + dy))
    for (x, y) in pts:
        col = C("19332d")
        if (x - 1, y) not in pts or (x, y - 1) not in pts:
            col = C("25562e")                        # lit north-west rim
        elif (x, y + 1) not in pts:
            col = C("10141f")                        # ground shadow rim
        c.set(x, y, col)
    for i in range(rng.randint(2, 4)):               # leaf-cluster highlights
        x = cx + rng.randint(-w // 3, w // 3)
        y = cy + rng.randint(-h // 3, 0)
        c.set(x, y, C("468232"))
        c.set(x + 1, y, C("25562e"))
    if variant == 2:                                 # the berried one
        for i in range(3):
            c.set(cx + rng.randint(-w // 3, w // 3),
                  cy + rng.randint(0, h // 3), C("a53030"))
    c.set(cx, cy + h // 2 + 1, C("341c27"))          # a hint of stem
    c.outline_auto()
    cr, orr = crop_canvas(c, (cx, cy + h // 2 + 2))
    return cr, orr, None


def draw_tuft(rng: random.Random, variant: int) -> tuple[Canvas, tuple, list | None]:
    """A few blades of grass through the concrete — dead-spot dressing."""
    c = Canvas(18, 16)
    base_x, base_y = 9, 11
    for b in range(rng.randint(3, 5)):
        bx = base_x + rng.randint(-3, 3)
        ht = rng.randint(3, 5)
        lean = rng.choice((-1, 0, 1))
        for k in range(ht):
            c.set(bx + (lean * k) // 3, base_y - k,
                  C("25562e") if k < ht - 1 else C("468232"))
    c.set(base_x + rng.randint(-2, 2), base_y + 1, C("19332d"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (base_x, base_y + 1))
    return cr, orr, None


def draw_bench(rng: random.Random, broken: bool) -> tuple[Canvas, tuple, list]:
    """Street bench along the (2,1) axis: metal frame, worn wood slats."""
    c = Canvas(48, 40)
    ox, oy = 8, 16
    ln = 26
    for i in range(ln):                              # three seat slats
        x = ox + i
        by = oy + i // 2
        for (s, col) in ((0, C("884b2b")), (2, C("602c2c")), (4, C("341c27"))):
            if broken and s == 2 and 9 < i < 16:
                continue                             # a slat kicked out
            c.set(x, by + s // 2, col)
            c.set(x, by + s // 2 + 1 if s == 0 else by + s // 2, col)
    for i in range(ln):                              # backrest rail
        x = ox + i
        c.set(x, oy + i // 2 - 6, C("394a50"))
        c.set(x, oy + i // 2 - 5, C("202e37"))
    for (px_, lean) in ((ox + 2, 0), (ox + ln - 3, 0)):
        top = oy + (px_ - ox) // 2
        for k in range(6):                           # legs
            c.set(px_ + (k // 4 if broken and lean == 0 and px_ > ox + 4 else 0),
                  top + 3 + k, C("202e37"))
        c.set(px_, top - 6, C("202e37"))             # back post
        c.set(px_, top - 4, C("202e37"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (ox + ln // 2, oy + ln // 4 + 8))
    return cr, orr, ["diamond", 12.0, 5.0]


def draw_shelter(rng: random.Random, wrecked: bool) -> tuple[Canvas, tuple, list]:
    """Bus shelter along the (2,1) axis — it IS the transit district.
    Glass back wall, flat roof, a route plate; the wrecked one lost a
    pane and most of its dignity."""
    c = Canvas(84, 80)
    ox, oy = 14, 50
    ln = 48
    post_h = 26
    # glass panes between the posts (drawn first, posts overlap)
    for i in range(ln):
        x = ox + i
        by = oy + i // 2
        pane = i // 16
        dead_pane = wrecked and pane == 1
        for k in range(4, post_h - 4):
            if dead_pane:
                continue
            col = C("253a5e")
            if (i + k) % 9 == 0:
                col = C("3c5e8b")                    # glint diagonal
            c.set(x, by - k, col)
    if wrecked:                                      # shards at the dead pane
        for i in range(6):
            sx_ = ox + 18 + rng.randrange(12)
            c.set(sx_, oy + sx_ // 2 - ox // 2 + rng.randint(0, 2), C("73bed3"))
            c.set(sx_ + 1, oy + sx_ // 2 - ox // 2 + 1, C("253a5e"))
    for pi in (0, 16, 32, ln - 1):                   # posts
        x = ox + pi
        by = oy + pi // 2
        for k in range(post_h):
            c.set(x, by - k, C("202e37"))
            c.set(x + 1, by - k, C("151d28"))
    for i in range(ln):                              # frame rails
        x = ox + i
        by = oy + i // 2
        c.set(x, by - 4, C("202e37"))
        c.set(x, by - post_h + 3, C("202e37"))
    # roof slab: top face toward NE, drip edge
    for i in range(ln + 2):
        x = ox - 1 + i
        ry = oy + (i - 1) // 2 - post_h
        for t in range(1, 9):
            col = C("151d28") if t < 8 else C("10141f")
            c.set(x + t, ry - (t + 1) // 2, col)
            c.set(x + t, ry - t // 2, col)
        c.set(x, ry, C("202e37"))                    # fascia
        c.set(x, ry + 1, C("090a14"))
    if wrecked:                                      # roof corner sags
        for i in range(10):
            c.set(ox + ln - 8 + i, oy + (ln - 8 + i) // 2 - post_h + i // 3,
                  C("151d28"))
    # bench inside
    for i in range(20):
        x = ox + 14 + i
        by = oy + (14 + i) // 2
        c.set(x, by - 8, C("602c2c"))
        c.set(x, by - 7, C("341c27"))
    # route plate on the near post
    c.rect(ox - 3, oy - post_h + 2, ox + 3, oy - post_h + 8, C("090a14"))
    c.rect(ox - 2, oy - post_h + 3, ox + 2, oy - post_h + 7, C("de9e41"))
    c.set(ox - 1, oy - post_h + 5, C("090a14"))
    c.set(ox + 1, oy - post_h + 5, C("090a14"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (ox + ln // 2, oy + ln // 4 + 2))
    return cr, orr, ["diamond", 20.0, 8.0]


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

def make_traffic_light(state: str) -> tuple[Canvas, tuple, list | None]:
    """Intersection traffic light, long dead like the district. One design
    with wear (the barricade lesson): a pole, an arm reaching over the road,
    a 3-lens head hanging off it. States: dark_a / dark_b (intact but
    unpowered — lenses in dead muted hues), bent (arm drooping), smashed
    (lenses out, glass down, a wire dangling), fallen (the whole pole flat
    on the ground, head popped off — no collider, walk over it)."""
    rng = random.Random(f"{SEED}:tlight:{state}")
    steel, steel_d = C("394a50"), C("202e37")
    dead_red, dead_amber, dead_green = C("411d31"), C("602c2c"), C("19332d")

    if state == "fallen":
        c = Canvas(52, 24)
        for i in range(34):                      # pole lying along +x
            x = 4 + i
            sh = i // 12                          # slight iso drop
            c.set(x, 8 + sh, steel)
            c.set(x, 9 + sh, steel_d)
            if i % 9 == 4 and rng.random() < 0.7:
                c.set(x, 8 + sh, C("884b2b"))     # rust where it hit
        c.rect(3, 6, 4, 11, steel_d)              # base plate at the near end
        hx, hy = 40, 6                            # head knocked off, lying
        c.rect(hx, hy, hx + 7, hy + 5, steel_d)
        c.set(hx + 1, hy + 2, dead_red)
        c.set(hx + 3, hy + 2, C("090a14"))        # popped lens
        c.set(hx + 5, hy + 2, dead_green)
        c.set(hx + 8, hy + 6, C("577277"))        # glass shards
        c.set(hx + 3, hy + 7, C("577277"))
        c.outline_auto()
        return c, (24, 14), None

    c = Canvas(34, 60)
    px_, py = 7, 50
    arm_len = 15 if state != "dark_b" else 10
    droop = 3 if state == "bent" else 0
    for y in range(9, py + 1):                    # the pole
        c.set(px_, y, steel)
        c.set(px_ + 1, y, steel_d)
    for y in range(py - 24, py, 6):               # pole wear
        if rng.random() < 0.6:
            c.set(px_, y, C("577277") if rng.random() < 0.5 else C("884b2b"))
    c.rect(px_ - 1, py, px_ + 2, py + 1, steel_d)  # base
    c.hline(px_ - 1, px_ + 2, py + 2, C("151d28"))
    if state == "dark_b":                          # small worn sign plate
        c.rect(px_ + 2, py - 22, px_ + 5, py - 18, C("577277"))
        c.set(px_ + 3, py - 21, C("819796"))
    for xi in range(arm_len):                      # the arm, reaching +x
        dy = droop * xi // max(1, arm_len - 1)
        c.set(px_ + xi, 9 + dy, steel)
        c.set(px_ + xi, 10 + dy, steel_d)
    if state == "bent":
        c.set(px_ + 3, 9, C("151d28"))             # kink at the bend
    hx = px_ + arm_len - 2                         # head hangs at the arm end
    hy = 11 + droop
    c.hline(hx, hx + 5, hy, C("577277"))           # lit top face (3D rule)
    c.rect(hx, hy + 1, hx + 5, hy + 13, steel_d)
    c.vline(hx + 5, hy + 1, hy + 13, C("151d28"))  # shaded east edge
    lenses = [dead_red, dead_amber, dead_green]
    if state == "smashed":
        lenses = [C("090a14")] * 3
    for li, col in enumerate(lenses):
        ly = hy + 2 + li * 4
        c.rect(hx + 1, ly, hx + 3, ly + 2, col)
        c.set(hx + 3, ly + 2, C("151d28"))         # lens hood shadow
    if state == "smashed":
        c.set(hx + 2, hy + 6, C("090a14"))
        c.rect(hx + 1, hy + 10, hx + 3, hy + 12, C("090a14"))  # bottom socket torn
        c.set(hx + 2, hy + 14, C("151d28"))        # dangling wire
        c.set(hx + 2, hy + 15, C("151d28"))
        c.set(hx + 3, hy + 16, C("151d28"))
        c.set(hx - 1, py + 1, C("577277"))         # glass at the pole foot
        c.set(hx + 2, py + 1, C("577277"))
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
        for i in range(steps):
            a = i / steps * 2 * math.pi
            x = int(size / 2 + math.cos(a) * radius)
            y = int(size / 2 + math.sin(a) * radius * 0.55)  # iso-squashed
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


# ------------------------------------------------- districts update props ----
# v0.6.18: the POI set — stairs/beds for two-story houses, buses for the
# depot, boxcars + buffers for the trainyard, the playground, courtyard
# pieces, and the comms relay compound. All iso, all Apollo, all 3D-read.

def make_stairs() -> tuple[Canvas, tuple, list]:
    """Interior staircase: seven stacked iso steps climbing the cell -y axis
    (screen up-right), solid wooden mass, pale tread noses. Drawn back to
    front so occlusion is right. F-interact takes you up."""
    c = Canvas(52, 56)
    top_col, lit, dark = C("be772b"), C("884b2b"), C("602c2c")
    for s in range(6, -1, -1):                # back-top first, front last
        h = 4 * (s + 1)
        ox = 6 + s * 5
        oy = 48 - s * 2 - 4 - h
        iso_prism(c, ox, oy, 8, 4, h, top_col, lit, dark)
        for x in range(2, 6):                 # pale tread nose on the front lip
            c.set(ox + x, oy + 4, C("ad7757"))
    c.outline_auto()
    return c, (10, 50), ["diamond", 12.0, 6.0]

def make_bed() -> tuple[Canvas, tuple, list]:
    """Upstairs bed: iso mattress, oxblood blanket over the near half,
    pillow at the head, a wooden headboard rising along the NE edge."""
    c = Canvas(36, 34)
    iso_prism(c, 4, 14, 24, 12, 6, C("a8b5b2"), C("819796"), C("577277"))
    rows = small_diamond_rows(24, 12)
    for i, (x0, x1) in enumerate(rows):       # blanket over the lower half
        if i >= 5:
            for x in range(x0, x1 + 1):
                col = C("752438")
                if i == 5:
                    col = C("411d31")         # fold line
                elif (x + i) % 9 == 0:
                    col = C("411d31")         # soft creases
                c.set(4 + x, 14 + i, col)
    for i in range(1, 4):                     # pillow at the head (NE)
        (x0, x1) = rows[i]
        for x in range(x1 - 6, x1 - 1):
            c.set(4 + x, 14 + i, C("c7cfcc"))
        c.set(4 + rows[3][1] - 6, 17, C("819796"))
    # headboard: a slab along the NE-upper edge, rising above the mattress
    for k in range(11):
        x = 4 + 12 + k
        edge_y = 14 + (k + 1) // 2
        for up in range(1, 8 - k // 3):
            c.set(x, edge_y - up, C("4d2b32") if up > 1 else C("7a4841"))
    c.outline_auto()
    return c, (18, 30), ["diamond", 13.0, 7.0]

def make_boxcar(scheme: int, broken: bool) -> tuple[Canvas, tuple, list]:
    """Freight boxcar on the (2,1) iso diagonal, same projection family as
    the road vehicles: ribbed slab side, sliding door, roof walkway, full
    end wall with a ladder, twin bogies. broken=True: door dragged open."""
    rng = random.Random(f"{SEED}:boxcar:{scheme}:{broken}")
    liveries = [("884b2b", "602c2c", "341c27"),
                ("25562e", "19332d", "10141f"),
                ("577277", "394a50", "202e37")]
    body_c, body_d, body_dd = (C(n) for n in liveries[scheme])
    L = 56
    clear = 6
    oy = 44
    ox = 6
    c = Canvas(96, 88)
    prof = [24 if i < 2 or i >= L - 2 else 26 for i in range(L)]
    for i in range(L):                       # side face with rib shading
        x = ox + i
        base = oy + i // 2
        for y in range(base - clear - prof[i], base - clear + 1):
            col = body_d if i % 4 else body_dd
            c.set(x, y, col)
    door_lo, door_hi = (20, 36)
    open_shift = 9 if broken else 0
    for i in range(door_lo, door_hi):        # sliding door (or its open gap)
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i] + 4
        for y in range(top, base - clear - 1):
            if broken and i < door_lo + open_shift:
                c.set(x, y, C("090a14"))     # the gap: interior darkness
            else:
                c.set(x, y, body_c if (i + y) % 4 else body_d)
    for i in range(door_lo - 1, door_hi + 1):  # door rails top + bottom
        x = ox + i
        base = oy + i // 2
        c.set(x, base - clear - prof[i] + 3, C("151d28"))
        c.set(x, base - clear - 1, C("151d28"))
    if not broken:
        c.set(ox + door_hi - 3, oy + (door_hi - 3) // 2 - clear - 10, C("c7cfcc"))
    prev_top = None
    for i in range(L):                       # roof plane with walkway strip
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i]
        span = 1 if prev_top is None else abs(prev_top - top) + 1
        rising = prev_top is not None and prev_top > top
        for t in range(1, ROOF_DEPTH + 1):
            col = body_c
            if t == ROOF_DEPTH:
                col = body_d
            elif t in (5, 6):
                col = body_d                 # the walkway plank line
            elif rng.random() < 0.02:
                col = body_d
            for k in range(span):
                yy = top + (k if rising else -k)
                c.set(x + t, yy - (t + 1) // 2, col)
                c.set(x + t, yy - t // 2, col)
        prev_top = top
    cap_h = prof[L - 1]
    wall_x0 = ox + L - 1
    wall_top0 = oy + (L - 1) // 2 - clear - cap_h
    wall_bot0 = oy + (L - 1) // 2 - clear
    for t in range(1, ROOF_DEPTH + 1):       # SE end wall, full width
        x = wall_x0 + t
        rise = t // 2
        for y in range(wall_top0 - rise, wall_bot0 - rise + 1):
            c.set(x, y, body_dd)
        c.set(x, wall_top0 - rise, body_d)
    for t in (2, 3, 4):                      # ladder rungs up the end wall
        x = wall_x0 + t
        for ry in range(3, cap_h - 2, 4):
            c.set(x, wall_bot0 - t // 2 - ry, C("819796"))
    for y in range(wall_top0 + 1, wall_bot0):
        c.set(ox + L - 1, y, body_dd)
    far_h = prof[0]
    for t in range(1, 3):                    # far end closes the silhouette
        x = ox - t
        base = oy - (t + 1) // 2
        for y in range(base - clear - far_h + (t + 1) // 2, base - clear + 1):
            c.set(x, y, body_dd)
    c.set(ox - 2, oy - 1 - clear - far_h + 3, C("151d28"))  # coupler hint
    for wf in (8, 42):                       # twin bogies
        for wx in range(10):
            x = ox + wf + wx
            base = oy + (wf + wx) // 2
            c.set(x, base - clear + 1, C("10141f"))
            c.set(x, base - clear + 2, C("10141f"))
        for wcx in (2, 7):
            cxw = ox + wf + wcx
            cyw = oy + (wf + wcx) // 2 - clear + 3
            for dy in range(-1, 2):
                for dx in range(-2, 3):
                    if dx * dx + dy * dy <= 3:
                        c.set(cxw + dx, cyw + dy, C("151d28"))
            c.set(cxw, cyw, C("394a50"))
    if broken:
        for _ in range(rng.randint(8, 13)):  # rust blooms
            x = ox + rng.randrange(2, L - 2)
            base = oy + x // 2
            y = base - clear - rng.randrange(2, 22)
            c.set(x, y, C("884b2b") if rng.random() < 0.6 else C("602c2c"))
    c.outline_auto()
    origin_full = (ox + (L + 3) // 2 + ROOF_DEPTH // 2,
                   oy + (L + 3) // 4 - ROOF_DEPTH // 4)
    cropped, origin = crop_canvas(c, origin_full)
    return cropped, origin, ["diamond", 36.0, 18.0]

def make_buffer_stop() -> tuple[Canvas, tuple, list]:
    """End-of-siding buffer: concrete block, two raked steel beams, a red
    crossbeam that has seen better days."""
    c = Canvas(30, 34)
    iso_prism(c, 7, 20, 16, 8, 4, CONC_L1, CONC_BASE, CONC_D1)
    for s in range(10):                       # raked beams
        y = 24 - s
        c.set(10 + s // 2, y, C("577277"))
        c.set(11 + s // 2, y, C("394a50"))
        c.set(18 + s // 2, y, C("577277"))
        c.set(19 + s // 2, y, C("394a50"))
    for x in range(9, 25):                    # crossbeam with worn red
        c.set(x, 14 + (x - 9) // 4, C("a53030") if x % 5 else C("411d31"))
        c.set(x, 15 + (x - 9) // 4, C("341c27"))
    c.outline_auto()
    return c, (15, 28), ["diamond", 9.0, 5.0]

def make_swing_set(broken: bool) -> tuple[Canvas, tuple, list]:
    """Playground swings along the +x axis: A-frames, top bar, chain seats.
    broken=True: one seat hangs from a single chain."""
    c = Canvas(60, 48)
    bar_y0 = 8
    for i in range(44):                       # top bar (iso slope +1/2)
        x = 8 + i
        y = bar_y0 + i // 2
        c.set(x, y, C("884b2b") if i % 7 else C("602c2c"))
        c.set(x, y + 1, C("602c2c"))
    for end in (0, 42):                       # A-frame legs at both ends
        ex = 8 + end
        ey = bar_y0 + end // 2
        for leg in range(16):
            c.set(ex - leg // 3, ey + leg, C("602c2c"))
            c.set(ex + leg // 3 + 1, ey + leg, C("341c27"))
    for si, seat_i in enumerate((12, 27)):    # two swings
        sx = 8 + seat_i
        sy = bar_y0 + seat_i // 2 + 2
        broken_this = broken and si == 1
        chains = (0, 5) if not broken_this else (2,)
        for ch in chains:
            for cy in range(9):
                if cy % 2 == 0:
                    c.set(sx + ch, sy + cy, C("577277"))
        if broken_this:                       # seat dangling from one chain
            for k in range(5):
                c.set(sx + 2 + k // 2, sy + 9 + k, C("341c27"))
        else:
            for k in range(7):
                c.set(sx + k - 1, sy + 9, C("341c27"))
                c.set(sx + k - 1, sy + 10, C("241527"))
    c.outline_auto()
    return c, (30, 42), ["poly", [-21.0, -12.0, 23.0, 10.0, 23.0, 14.0, -21.0, -8.0]]

def make_slide() -> tuple[Canvas, tuple, list]:
    """Playground slide: platform + ladder at the NE end, pale chute
    pouring toward the SW."""
    c = Canvas(42, 38)
    iso_prism(c, 24, 6, 12, 6, 3, C("577277"), C("394a50"), C("202e37"))
    for leg in ((25, 14), (34, 12)):
        for y in range(leg[1], 30):
            c.set(leg[0], y, C("341c27"))
            c.set(leg[0] + 1, y, C("341c27"))
    for r in range(4):                        # ladder rungs behind
        c.set(36, 12 + r * 4, C("819796"))
        c.set(37, 12 + r * 4, C("819796"))
        c.set(38, 13 + r * 4, C("577277"))
    for s in range(22):                       # the chute
        x = 26 - s
        y = 10 + s
        if y > 31:
            break
        for w in range(5):
            col = C("819796")
            if w == 2:
                col = C("a8b5b2")             # center shine
            if w in (0, 4):
                col = C("577277")             # raised edge rails
            c.set(x + w, y, col)
    for s in range(6):                        # run-out flat at the bottom
        for w in range(5):
            c.set(4 + w + s, 32 + s // 3, C("819796") if w != 2 else C("a8b5b2"))
    c.outline_auto()
    return c, (20, 35), ["diamond", 14.0, 7.0]

def make_sandbox() -> tuple[Canvas, tuple, list | None]:
    """Low wooden sandbox, walk-over: plank frame, dug-up sand, one
    half-buried tire. No collider by design."""
    rng = random.Random(f"{SEED}:sandbox")
    c = Canvas(48, 26)
    rows = small_diamond_rows(44, 22)
    for i, (x0, x1) in enumerate(rows):
        for x in range(x0, x1 + 1):
            u = (x - 22) * 0.5 + (i - 11)
            v = (x - 22) * 0.5 - (i - 11)
            if abs(u) > 8.2 or abs(v) > 8.2:
                c.set(2 + x, 2 + i, C("884b2b") if (x + i) % 6 else C("602c2c"))
            else:
                c.set(2 + x, 2 + i, C("ad7757") if (x * 3 + i * 7) % 13 else C("c09473"))
    for _ in range(4):                        # dig shadows
        bx, by = 12 + rng.randrange(22), 7 + rng.randrange(10)
        for (dx, dy) in ((0, 0), (1, 0), (2, 1), (1, 1)):
            c.set(bx + dx, by + dy, C("7a4841"))
    for a in range(10):                       # half-buried tire arc
        c.set(28 + a, 12 - (a * (10 - a)) // 8, C("151d28"))
        c.set(28 + a, 13 - (a * (10 - a)) // 8, C("10141f"))
    c.outline_auto()
    return c, (24, 20), None

def make_flagpole() -> tuple[Canvas, tuple, list]:
    """School flagpole: tall mast, halyard, a tattered dark strip of flag."""
    rng = random.Random(f"{SEED}:flagpole")
    c = Canvas(24, 70)
    iso_prism(c, 6, 60, 8, 4, 3, CONC_L1, CONC_BASE, CONC_D1)
    for y in range(8, 62):
        c.set(10, y, C("819796") if y % 9 else C("577277"))
        if y % 2:
            c.set(11, y, C("577277"))
    for y in range(10, 60, 2):                # halyard
        c.set(13, y, C("341c27"))
    for fy in range(9):                       # the flag: tattered, hanging
        w = 8 - max(0, fy - 4) - (1 if rng.random() < 0.4 else 0)
        for fx in range(w):
            c.set(12 + fx, 9 + fy, C("411d31") if (fx + fy) % 7 else C("752438"))
    c.outline_auto()
    return c, (11, 65), ["circle", 2.5]

def make_planter(variant: int) -> tuple[Canvas, tuple, list]:
    """Courtyard concrete planter, overgrown — the district reclaims its
    own decorations."""
    rng = random.Random(f"{SEED}:planter:{variant}")
    c = Canvas(28, 32)
    iso_prism(c, 4, 12, 20, 10, 7, CONC_L1, CONC_BASE, CONC_D1)
    rows = small_diamond_rows(20, 10)
    for i, (x0, x1) in enumerate(rows):       # soil, inset from the rim
        for x in range(x0 + 2, x1 - 1):
            if 1 <= i < 9:
                c.set(4 + x, 12 + i, C("341c27"))
    for _ in range(rng.randint(3, 5)):        # the overgrowth mound
        bx, by = 9 + rng.randrange(10), 8 + rng.randrange(6)
        for (dx, dy) in ((0, 0), (1, 0), (-1, 0), (0, -1), (1, -1), (0, 1), (2, 0)):
            qx, qy = bx + dx, by + dy
            if 4 <= qx < 26 and 2 <= qy < 20:
                c.set(qx, qy, C("25562e") if (dx + dy) % 2 else C("19332d"))
    if variant == 1:                          # cracked face
        x, y = 8, 16
        for _ in range(7):
            c.set(x, y, CONC_D1)
            x += rng.choice((0, 1, 1))
            y += rng.choice((0, 1))
    c.outline_auto()
    return c, (14, 26), ["diamond", 10.0, 5.0]

def make_fountain_dry() -> tuple[Canvas, tuple, list]:
    """The courtyard's dry fountain: wide basin, cracked bowl of leaf
    litter, a center pedestal that stopped mattering years ago."""
    rng = random.Random(f"{SEED}:fountain")
    c = Canvas(52, 40)
    rows = small_diamond_rows(44, 22)
    for i, (x0, x1) in enumerate(rows):       # rim ring around a dead bowl
        for x in range(x0, x1 + 1):
            u = (x - 22) * 0.5 + (i - 11)
            v = (x - 22) * 0.5 - (i - 11)
            r2 = (u / 8.4) ** 2 + (v / 8.4) ** 2
            if r2 > 1.0:
                c.set(4 + x, 6 + i, CONC_L1 if (x + i) % 3 else CONC_L2)
            else:
                c.set(4 + x, 6 + i, C("151d28"))
    for i, (x0, x1) in enumerate(rows):       # outer wall face on the near side
        if i > 14:
            for x in range(x0, x1 + 1):
                c.set(4 + x, 6 + i + 4, CONC_BASE if x % 2 else CONC_D1)
    for _ in range(5):                        # leaf litter drifts in the bowl
        bx, by = 16 + rng.randrange(18), 12 + rng.randrange(8)
        for (dx, dy) in ((0, 0), (1, 0), (2, 0), (1, 1)):
            c.set(bx + dx, by + dy, C("341c27"))
    iso_prism(c, 22, 8, 8, 4, 7, CONC_L1, CONC_BASE, CONC_D1)   # pedestal
    x, y = 14, 18                             # the crack that ended it
    for _ in range(9):
        c.set(x, y, CONC_D1)
        x += rng.choice((1, 1, 0))
        y += rng.choice((0, 1, 0))
    c.outline_auto()
    return c, (26, 32), ["diamond", 21.0, 11.0]

def make_comms_tower() -> tuple[Canvas, tuple, list]:
    """The relay: a lattice mast with X-bracing, a mid-height dish, a top
    platform and whip antenna. The tallest thing left standing out here."""
    c = Canvas(40, 92)
    top_y = 14
    base_y = 84
    for band in range(top_y + 4, base_y - 4, 8):  # X bracing behind the legs
        t = (band - top_y) / (base_y - top_y)
        off = int(3 + t * 9)
        for i in range(2 * off):
            x = 20 - off + i
            up = band + (i * 8) // (2 * off)
            dn = band + 8 - (i * 8) // (2 * off)
            c.set(x, up, C("394a50"))
            c.set(x, dn, C("394a50"))
    for y in range(top_y, base_y):            # two visible legs, converging
        t = (y - top_y) / (base_y - top_y)
        off = 3 + t * 9
        for leg_x in (int(20 - off), int(20 + off)):
            col = C("577277") if y % 11 else C("884b2b")   # rust bites
            c.set(leg_x, y, col)
            c.set(leg_x + 1, y, C("394a50"))
    for x in range(15, 26):                   # top platform
        c.set(x, top_y, C("341c27"))
        c.set(x, top_y + 1, C("151d28"))
    for y in range(top_y - 10, top_y):        # whip antenna + beacon
        c.set(20, y, C("577277"))
    c.set(20, top_y - 11, C("a53030"))
    c.set(20, top_y - 12, C("cf573c"))
    for dy in range(6):                       # the mid-height dish
        w = (6, 8, 8, 7, 5, 3)[dy]
        for dx in range(w):
            col = C("819796") if dy < 2 or dx in (0, w - 1) else C("577277")
            c.set(7 + dx + dy // 2, 38 + dy, col)
    c.set(13, 41, C("341c27"))                # feed arm
    c.set(14, 40, C("341c27"))
    iso_prism(c, 8, 82, 8, 4, 3, CONC_L1, CONC_BASE, CONC_D1)   # pads
    iso_prism(c, 24, 82, 8, 4, 3, CONC_L1, CONC_BASE, CONC_D1)
    c.outline_auto()
    return c, (20, 86), ["diamond", 12.0, 6.0]

def make_dish_ground() -> tuple[Canvas, tuple, list]:
    """Ground-mounted dish aimed at nothing anymore."""
    c = Canvas(32, 28)
    for dy in range(11):                      # the reflector, tilted ellipse
        w = (4, 8, 11, 13, 14, 14, 13, 11, 9, 6, 3)[dy]
        for dx in range(w):
            col = C("819796")
            if 1 < dy < 9 and 1 < dx < w - 2:
                col = C("577277") if (dx + dy) % 4 else C("394a50")
            c.set(6 + dx + dy // 3, 3 + dy, col)
    for k in range(6):                        # feed arm to the focus
        c.set(20 - k, 5 + k, C("341c27"))
    c.set(21, 4, C("151d28"))
    for leg in ((11, 15), (19, 14)):          # A-mount legs
        for y in range(leg[1], 24):
            c.set(leg[0], y, C("394a50"))
            c.set(leg[0] + 1, y, C("202e37"))
    c.outline_auto()
    return c, (16, 24), ["diamond", 10.0, 5.0]

def make_equip_shed() -> tuple[Canvas, tuple, list]:
    """Relay equipment shed: corrugated metal, hazard-striped door panel,
    roof vent, a conduit running down the corner."""
    c = Canvas(52, 50)
    bottoms = iso_prism(c, 6, 8, 32, 16, 20, C("394a50"), C("577277"), C("202e37"))
    for x in range(32):                       # corrugation ribs both faces
        if x % 3 == 0:
            b = bottoms[x]
            for y in range(b + 1, b + 20):
                c.set(6 + x, y, C("394a50") if x < 16 else C("151d28"))
    for dx in range(8):                       # door on the lit SW face
        for dy in range(13):
            c.set(10 + dx, 22 + dy - dx // 2, C("341c27") if dy else C("241527"))
    for dx in range(8):                       # hazard stripe over the door
        col = C("de9e41") if (dx // 2) % 2 == 0 else C("151d28")
        c.set(10 + dx, 22 - dx // 2, col)
        c.set(10 + dx, 23 - dx // 2, col)
    for y in range(4, 9):                     # roof vent
        for x in range(5):
            c.set(24 + x, y, C("151d28") if y % 2 else C("202e37"))
    for y in range(12, 30):                   # conduit down the far corner
        c.set(37, y, C("819796") if y % 5 else C("577277"))
    c.outline_auto()
    return c, (22, 42), ["diamond", 17.0, 9.0]

def make_school_sign() -> tuple[Canvas, tuple, list]:
    """The school's sign board: nobody can read it anymore — the letters
    are weathered to scribbles, which is somehow worse."""
    rng = random.Random(f"{SEED}:schoolsign")
    c = Canvas(34, 36)
    for qx in (8, 24):                        # posts
        for y in range(16, 32):
            c.set(qx, y, C("341c27"))
            c.set(qx + 1, y, C("241527"))
    for x in range(4, 30):                    # board frame + face
        for y in range(6, 18):
            edge = x in (4, 29) or y in (6, 17)
            c.set(x, y, C("602c2c") if edge else C("151d28"))
    for row_y in (9, 13):                     # unreadable scribble lines
        x = 7
        while x < 27:
            run = rng.randint(2, 4)
            for k in range(min(run, 27 - x)):
                c.set(x + k, row_y + rng.choice((0, 0, 1)), C("a8b5b2"))
            x += run + rng.randint(1, 2)
    c.outline_auto()
    return c, (17, 32), ["diamond", 12.0, 5.0]

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
        fam("pallet", i, draw_pallet(broken=(i == 1), stacked=(i == 2)))
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
        if not broken:
            # driveable cars: the door-open enter/exit frame (texture swap)
            door_nw = make_vehicle(kind, scheme, rev=False, door_open=True)
            door_se = make_vehicle(kind, scheme, rev=True, door_open=True)
            props[f"vehicle_nw_{i}_door"] = door_nw
            props[f"vehicle_se_{i}_door"] = door_se
            props[f"vehicle_ne_{i}_door"] = mirror_prop(door_nw)
            props[f"vehicle_sw_{i}_door"] = mirror_prop(door_se)
    # buses for the depot: two liveries parked, two broken into
    bus_specs = [(1, False), (2, False), (0, True), (3, True)]
    for i, (scheme, broken) in enumerate(bus_specs):
        bus_nw = make_vehicle("bus", scheme, rev=False, broken=broken)
        bus_se = make_vehicle("bus", scheme, rev=True, broken=broken)
        fam("bus_nw", i, bus_nw)
        fam("bus_se", i, bus_se)
        fam("bus_ne", i, mirror_prop(bus_nw))
        fam("bus_sw", i, mirror_prop(bus_se))
    # trainyard rolling stock
    for i, (scheme, broken) in enumerate([(0, False), (1, False), (2, False), (0, True)]):
        art = make_boxcar(scheme, broken)
        fam("boxcar_x", i, art)
        fam("boxcar_y", i, mirror_prop(art))
    buffer_art = make_buffer_stop()
    fam("buffer_stop", 0, buffer_art)
    fam("buffer_stop", 1, mirror_prop(buffer_art))
    # two-story interiors
    props["stairs"] = make_stairs()
    props["bed"] = make_bed()
    # the playground
    for i, playground_broken in enumerate((False, True)):
        fam("swing_set", i, make_swing_set(playground_broken))
    props["slide"] = make_slide()
    props["sandbox"] = make_sandbox()
    props["flagpole"] = make_flagpole()
    props["school_sign"] = make_school_sign()
    # the courtyard
    for i in range(2):
        fam("planter", i, make_planter(i))
    props["fountain_dry"] = make_fountain_dry()
    # the comms relay
    props["comms_tower"] = make_comms_tower()
    props["dish_ground"] = make_dish_ground()
    props["equip_shed"] = make_equip_shed()
    for i in range(4):
        fam("tree", i, make_tree("pine", i))
    for i in range(3):
        fam("tree", 4 + i, make_tree("oak", i))
    for i in range(2):
        fam("tree", 7 + i, make_tree("dead", i))
    props["street_lamp"] = make_street_lamp("working")
    fam("street_lamp_dead", 0, make_street_lamp("dead_bent"))
    fam("street_lamp_dead", 1, make_street_lamp("dead_smashed"))
    # traffic lights: arm reaches +x; mirrored family for corners on the
    # other side of the road, so the head always hangs over the asphalt
    for i, state in enumerate(("dark_a", "dark_b", "bent", "smashed")):
        tl = make_traffic_light(state)
        fam("traffic_light", i, tl)
        fam("traffic_light_m", i, mirror_prop(tl))
    tl_flat = make_traffic_light("fallen")
    fam("traffic_light_flat", 0, tl_flat)
    fam("traffic_light_flat", 1, mirror_prop(tl_flat))
    for kind in ("wood", "metal"):
        for axis in ("x", "y"):
            props[f"door_{kind}_{axis}"] = make_door_strip(kind, axis)
    for i in range(4):
        rng = random.Random(f"{SEED}:stick:{i}")
        fam("stick", i, draw_stick(rng, i))
    for i in range(3):
        rng = random.Random(f"{SEED}:bush:{i}")
        fam("bush", i, draw_bush(rng, i))
    for i in range(3):
        rng = random.Random(f"{SEED}:tuft:{i}")
        fam("tuft", i, draw_tuft(rng, i))
    for i, broken in enumerate((False, True)):
        rng = random.Random(f"{SEED}:bench:{i}")
        bench = draw_bench(rng, broken)
        fam("bench_x", i, bench)
        fam("bench_y", i, mirror_prop(bench))
    for i, wrecked in enumerate((False, True)):
        rng = random.Random(f"{SEED}:shelter:{i}")
        shelter = draw_shelter(rng, wrecked)
        fam("shelter_x", i, shelter)
        fam("shelter_y", i, mirror_prop(shelter))
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
        bob = max(bob, -1)  # crouch keeps the bob subtle
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

def _dither_fill(c: Canvas, x0: int, y0: int, x1: int, y1: int, col, density: float,
                 rng: random.Random) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if rng.random() < density:
                c.set(x, y, col)

def _vgrad(c: Canvas, bands: list[tuple], rng: random.Random | None = None,
           seam: int = 26) -> None:
    """bands: [(until_y, color)] — vertical bands. Seams blend over a WIDE
    noisy zone (probability ramp) so the sky reads as a gradient, not
    stripes — the old 6px ordered dither still striped at menu scale."""
    prev_y = 0
    for bi, (until_y, col) in enumerate(bands):
        for y in range(prev_y, until_y):
            for x in range(SCENE_W):
                c.set(x, y, col)
        prev_y = until_y
    if rng is None:
        rng = random.Random(f"{SEED}:vgrad")
    # WAVY solid seams, no dot-dither (user call: no little dots anywhere):
    # each band boundary is a slow organic curve instead of a straight line
    for bi in range(len(bands) - 1):
        until_y, col = bands[bi]
        nxt = bands[bi + 1][1]
        t1 = rng.uniform(70.0, 150.0)
        t2 = rng.uniform(23.0, 47.0)
        p1 = rng.uniform(0.0, math.tau)
        p2 = rng.uniform(0.0, math.tau)
        for x in range(SCENE_W):
            edge = until_y + int(seam * 0.7 * math.sin(x / t1 + p1)
                                 + seam * 0.3 * math.sin(x / t2 + p2))
            for y in range(min(edge, until_y), max(edge, until_y)):
                c.set(x, y, nxt if edge < until_y else col)

def _paste(c: Canvas, img: Image.Image, x: int, y: int) -> None:
    c.img.alpha_composite(img, (x, y))
    c.px = c.img.load()

def _skyline_row(c: Canvas, rng: random.Random, y_base: int, h_lo: int, h_hi: int,
                 col, w_lo: int = 18, w_hi: int = 44, gap_lo: int = 2,
                 gap_hi: int = 10) -> list[tuple[int, int, int]]:
    """One receding row of building silhouettes; returns (x0, x1, top) blocks.
    Every roofline is ROLLED (flat / notched / slanted / stepped, antennas,
    water tanks, sagging corners) — the old uniform crenellation read as one
    repeating castle wall."""
    blocks: list[tuple[int, int, int]] = []
    x = -rng.randint(0, 20)
    while x < SCENE_W:
        w = rng.randint(w_lo, w_hi)
        h = rng.randint(h_lo, h_hi)
        top = y_base - h
        style = rng.randrange(5)
        notch_p = rng.choice((5, 7, 9))
        slant = rng.uniform(-0.25, 0.25)
        sag = rng.randint(2, 5) if rng.random() < 0.25 else 0
        for xx in range(max(0, x), min(SCENE_W, x + w)):
            i = xx - x
            step = 0
            if style == 1 and (i // notch_p) % 2:
                step = 3
            elif style == 2:
                step = int(i * slant) if slant > 0 else int((w - i) * -slant)
            elif style == 3 and i > w * 0.6:
                step = 4
            if sag and (i < 3 or i > w - 4):
                step += sag
            for y in range(top + step, y_base + 2):
                c.set(xx, y, col)
        if rng.random() < 0.30:  # antenna mast
            ax = x + rng.randint(2, max(3, w - 3))
            if 0 <= ax < SCENE_W:
                for y in range(top - rng.randint(5, 14), top):
                    c.set(ax, y, col)
        if rng.random() < 0.18 and w > 24:  # rooftop water tank
            tx = x + rng.randint(3, w - 12)
            c.rect(tx, top - 6, tx + 8, top - 1, col)
            c.set(tx + 1, top, col)
            c.set(tx + 7, top, col)
        blocks.append((max(0, x), min(SCENE_W, x + w), top))
        x += w + rng.randint(gap_lo, gap_hi)
    return blocks


def make_scene_drain() -> tuple[Canvas, Image.Image, Canvas]:
    """Menu 1 — THE DRAIN, side-on like a stage (the one-point perspective
    version never stopped reading as floating rings and a black pyramid):
    a flat brick wall the full width of the frame, a ceiling line, one
    shaft of light falling from an open manhole to the walkway, black
    water along the bottom, the tunnel swallowing itself into a dark
    arch at the left edge. Returns (base, god-ray overlay (soft alpha),
    3-frame drip-ripple strip)."""
    rng = random.Random(f"{SEED}:scene:drain")
    c = Canvas(SCENE_W, SCENE_H)
    SHAFT_X = 615
    CEIL_Y = 92
    WALK_Y = 468
    WATER_Y = 506

    ramp = [C("090a14"), C("10141f"), C("151d28"), C("202e37"), C("394a50")]

    def lit(x: int, y: int, boost: float = 0.0):
        d = ((x - SHAFT_X) ** 2 + ((y - (WALK_Y - 60)) * 1.9) ** 2) ** 0.5
        lv = boost + max(0.0, 1.0 - d / 420.0) * 4.4
        # banded, never dithered — dot noise is banned everywhere
        return ramp[max(0, min(len(ramp) - 1, int(lv + 0.5)))]

    # the brick wall, full frame: rolled course heights + staggered joints
    wy = CEIL_Y
    while wy < WALK_Y:
        row_h = rng.randint(9, 12)
        joints = []
        jx = -rng.randint(0, 30)
        while jx < SCENE_W:
            jx += rng.randint(22, 46)
            joints.append(jx)
        for y in range(wy, min(WALK_Y, wy + row_h)):
            for x in range(SCENE_W):
                col = lit(x, y)
                if y == wy:
                    col = C("090a14")               # mortar line
                elif x in joints and y > wy + 1:
                    col = C("090a14")               # brick joint
                c.set(x, y, col)
        wy += row_h
    # ceiling: dark slab + beams
    for y in range(0, CEIL_Y):
        for x in range(SCENE_W):
            c.set(x, y, C("090a14"))
    for bx in range(70, SCENE_W, 150):
        jx = bx + rng.randint(-12, 12)
        if abs(jx - SHAFT_X) < 44:
            continue                                 # not through the shaft
        c.rect(jx, CEIL_Y - 10, jx + 8, CEIL_Y, C("10141f"))
        c.vline(jx + 8, CEIL_Y - 10, CEIL_Y, C("151d28"))
    c.hline(0, SCENE_W - 1, CEIL_Y, C("10141f"))

    # the manhole shaft: a gap in the ceiling, faint baked light column
    for y in range(0, CEIL_Y):
        for x in range(SHAFT_X - 28, SHAFT_X + 29):
            c.set(x, y, C("10141f"))                 # shaft throat
    for dx in range(-24, 25):                        # the open cover ring
        dy = int((1.0 - (dx / 24.0) ** 2) ** 0.5 * 6)
        for y in range(12 - dy, 12 + dy):
            c.set(SHAFT_X + dx, y, C("172038"))      # night sky up there
        c.set(SHAFT_X + dx, 12 + dy, C("577277"))
        c.set(SHAFT_X + dx, 12 - dy, C("394a50"))
    c.set(SHAFT_X - 7, 8, C("c7cfcc"))               # one star
    c.rect(SHAFT_X + 26, 6, SHAFT_X + 44, 10, C("151d28"))  # slid-aside cover
    c.hline(SHAFT_X + 27, SHAFT_X + 43, 6, C("202e37"))
    # (no baked dot-column: the wall's banded lit() carries the brightness
    # and the runtime god-ray overlay provides the soft beam)

    # the ladder, bolted inside the shaft line
    for ry in range(CEIL_Y - 60, WALK_Y - 2, 13):
        if ry > 4:
            c.hline(SHAFT_X + 8, SHAFT_X + 20, ry, C("577277"))
            c.set(SHAFT_X + 8, ry + 1, C("202e37"))
            c.set(SHAFT_X + 20, ry + 1, C("202e37"))
    c.vline(SHAFT_X + 7, 20, WALK_Y, C("394a50"))
    c.vline(SHAFT_X + 21, 20, WALK_Y, C("394a50"))
    c.vline(SHAFT_X + 6, 22, WALK_Y - 1, C("151d28"))

    # the tunnel mouth at the left edge: an arch into nothing, solid
    for x in range(0, 150):
        e = 1.0 - (x / 150.0) ** 2
        ay = int(CEIL_Y + 40 - 36 * (e ** 0.5))
        for y in range(ay, WALK_Y):
            if x < 118 or y > ay + (x - 118) * 8:
                c.set(x, y, C("090a14"))
        c.set(x, ay, C("151d28"))                    # faint arch rim
        c.set(x, ay - 1, C("10141f"))

    # pipes on the wall, right side, with brackets and rust
    for x in range(SHAFT_X + 60, SCENE_W):
        py = 180 + (x - SHAFT_X - 60) // 14
        c.set(x, py - 1, lit(x, py - 1, 1.0))
        c.set(x, py, C("394a50"))
        c.set(x, py + 1, C("202e37"))
        c.set(x, py + 2, C("151d28"))
        c.set(x, py + 3, C("090a14"))
        if x % 61 < rng.randint(3, 6) and x % 61 > 0:  # rust runs, not dots
            c.set(x, py + 1, C("884b2b"))
            c.set(x, py, C("602c2c"))
        if x % 52 == 0:
            c.vline(x, py + 3, py + 9, C("151d28"))
    for a in range(0, 360, 30):                      # valve wheel
        c.set(int(SHAFT_X + 170 + math.cos(math.radians(a)) * 6),
              int(188 + math.sin(math.radians(a)) * 6), C("577277"))
    # cables sagging along the left half
    for k in range(160):
        t = k / 160.0
        sag = math.sin(t * math.pi) * 18
        c.set(int(140 + t * 330), int(120 + sag), C("10141f"))
        c.set(int(150 + t * 320), int(132 + sag * 0.8), C("151d28"))

    # wet streaks + moss patches on the wall (solid, structural)
    for i in range(14):
        wx = rng.randrange(130, SCENE_W - 10)
        wy_ = rng.randrange(CEIL_Y + 4, 200)
        ln = rng.randint(12, 60)
        c.vline(wx, wy_, wy_ + ln, C("10141f"))
        c.set(wx, wy_ + ln + 1, C("172038"))
    wall_low = {(x, y) for y in range(WALK_Y - 30, WALK_Y)
                for x in range(130, SCENE_W)}
    for i in range(7):
        patch = blob(rng, rng.randrange(150, SCENE_W - 20),
                     WALK_Y - rng.randrange(4, 24), rng.randint(8, 26), wall_low)
        for (qx, qy) in patch:
            c.set(qx, qy, C("19332d"))

    # the walkway ledge
    for y in range(WALK_Y, WATER_Y):
        for x in range(SCENE_W):
            col = lit(x, y, 0.7 if abs(x - SHAFT_X) < 200 else 0.2)
            c.set(x, y, col)
    c.hline(0, SCENE_W - 1, WALK_Y, C("090a14"))
    # the light pool on the walkway: solid banded ellipse
    for dx in range(-74, 75):
        for dy in range(-10, 11):
            d = (dx / 74.0) ** 2 + (dy / 10.0) ** 2
            if d < 1.0:
                c.set(SHAFT_X + dx, WALK_Y + 18 + dy,
                      C("819796") if d < 0.3 else C("577277"))
    c.hline(SHAFT_X - 90, SHAFT_X + 90, WATER_Y - 1, C("577277"))
    c.hline(SHAFT_X - 170, SHAFT_X - 91, WATER_Y - 1, C("394a50"))
    c.hline(SHAFT_X + 91, SHAFT_X + 170, WATER_Y - 1, C("394a50"))

    # black water: solid, with the shaft's reflection as broken DASHES
    for y in range(WATER_Y, SCENE_H):
        for x in range(SCENE_W):
            c.set(x, y, C("090a14"))
    for y in range(WATER_Y + 2, SCENE_H, 3):          # reflection column
        for k in range(2):
            gx = SHAFT_X + rng.randint(-24, 20)
            c.hline(gx, gx + rng.randint(2, 5), y,
                    C("253a5e") if rng.random() < 0.7 else C("3c5e8b"))
    for y in range(WATER_Y + 4, SCENE_H, 7):          # faint drift lines
        gx = rng.randrange(30, SCENE_W - 40)
        c.hline(gx, gx + rng.randint(3, 7), y, C("172038"))
    c.hline(0, SCENE_W - 1, WATER_Y, C("090a14"))

    # raider cache in the pool's edge light
    bx, by = SHAFT_X - 118, WALK_Y + 26
    c.rect(bx, by - 14, bx + 22, by, C("341c27"))
    c.rect(bx + 1, by - 13, bx + 21, by - 9, C("602c2c"))
    c.hline(bx + 1, bx + 21, by - 8, C("884b2b"))
    c.vline(bx + 11, by - 8, by - 1, C("241527"))
    c.hline(bx, bx + 22, by, C("090a14"))
    c.rect(bx + 28, by - 9, bx + 34, by, C("202e37"))
    c.rect(bx + 29, by - 7, bx + 33, by - 3, C("151d28"))
    c.set(bx + 31, by - 10, C("394a50"))
    c.rect(bx - 22, by - 6, bx - 4, by, C("411d31"))
    c.hline(bx - 22, bx - 4, by - 6, C("752438"))
    c.hline(bx - 24, bx + 36, by + 1, C("090a14"))

    # (no baked dot-vignette — the runtime vignette.png is smooth alpha)

    # god-ray overlay (soft alpha, breathes at runtime)
    rw, rh = 150, 390
    ray = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    rp = ray.load()
    for y in range(rh):
        t = y / float(rh)
        half = 24 + 24 * t
        for x in range(rw):
            ax = abs(x - rw / 2) / half
            if ax < 1.0:
                a = int(72 * (1.0 - ax) ** 1.6 * (1.0 - t * 0.5))
                if a > 0:
                    rp[x, y] = (168, 181, 178, a)

    # drip ripple strip: 3 frames, 18x8
    strip = Canvas(54, 8)
    for f in range(3):
        ox = f * 18 + 9
        r = 2 + f * 3
        for a in range(0, 360, 15):
            x = int(ox + math.cos(math.radians(a)) * r)
            y = int(4 + math.sin(math.radians(a)) * r * 0.4)
            if 0 <= x < 54:
                strip.set(x, y, C("253a5e") if f == 2 else C("3c5e8b"))
    return c, ray, strip


def make_scene_den() -> tuple[Canvas, Image.Image, Canvas]:
    """Menu 2 — THE DEN: the traders' back room, all three of them home.
    kettle hunched behind his scale on the candle side, verne at the
    medicine shelf, mara at the radio wall. Two light sources own the frame
    (warm candle left, cool radio right) with DITHERED falloff. The job
    board carries paper JOB SHEETS — pin, title, a little photo of the
    district, squiggled unreadable notes; transit ringed red: tonight's
    job. Returns (base, candle-glow overlay, VU-needle strip)."""
    rng = random.Random(f"{SEED}:scene:den")
    c = Canvas(SCENE_W, SCENE_H)
    CANDLE = (150, 366)
    RADIO = (760, 320)
    warm_ramp = [C("241527"), C("341c27"), C("602c2c"), C("884b2b"), C("ad7757")]
    cool_ramp = [C("172038"), C("1e1d39"), C("253a5e"), C("3c5e8b")]

    def light_levels(x: int, y: int) -> tuple[float, float]:
        dw = ((x - CANDLE[0]) ** 2 + ((y - CANDLE[1]) * 2.1) ** 2) ** 0.5
        dc = ((x - RADIO[0]) ** 2 + ((y - RADIO[1]) * 1.9) ** 2) ** 0.5
        return max(0.0, 1.0 - dw / 350.0), max(0.0, 1.0 - dc / 310.0)

    def ramp_pick(ramp_: list, lv: float):
        # clean banded light — the coin-flip dither read as dot static
        return ramp_[max(0, min(len(ramp_) - 1, int(lv + 0.5)))]

    CEIL = 46
    # back wall: planks with ROLLED widths, tone jitter, knots, nails and
    # splits — a fixed 26px rhythm read as an obvious grid (user report)
    plank_edges: list[int] = []
    px_ = 0
    while px_ < SCENE_W:
        plank_edges.append(px_)
        px_ += rng.randint(16, 36)
    plank_of: list[int] = [0] * SCENE_W
    for pi in range(len(plank_edges)):
        x0 = plank_edges[pi]
        x1 = plank_edges[pi + 1] if pi + 1 < len(plank_edges) else SCENE_W
        for x in range(x0, min(SCENE_W, x1)):
            plank_of[x] = pi
    plank_bias = [rng.uniform(-0.55, 0.55) for _ in plank_edges]
    plank_split = {pi: (rng.randrange(plank_edges[pi] + 3,
                        min(SCENE_W - 1, plank_edges[pi] + 14)),
                        rng.randrange(90, 320))
                   for pi in range(len(plank_edges)) if rng.random() < 0.16}
    knots = {}
    for pi in range(len(plank_edges)):
        for k in range(rng.randrange(0, 3)):
            kx = plank_edges[pi] + rng.randint(3, 12)
            knots[(kx, rng.randrange(CEIL + 20, 410))] = True
    for y in range(CEIL, 430):
        for x in range(SCENE_W):
            warm, cool = light_levels(x, y)
            pi = plank_of[x]
            plank_edge = x in plank_edges
            base_i = (1 if plank_edge else 0) + plank_bias[pi]
            if warm >= cool and warm > 0.03:
                col = ramp_pick(warm_ramp, base_i + warm * 4.2)
            elif cool > 0.03:
                col = ramp_pick(cool_ramp, base_i + cool * 3.4)
            else:
                col = C("090a14") if plank_edge else C("10141f")
            c.set(x, y, col)
    for (kx, ky) in knots:                                # knots + grain swirls
        c.set(kx, ky, C("241527"))
        c.set(kx + 1, ky, C("341c27"))
        c.set(kx, ky + 1, C("341c27"))
    for pi, (sx_, sy_) in plank_split.items():            # split boards
        for k in range(rng.randint(20, 70)):
            c.set(sx_ + (k // 16), sy_ + k, C("090a14"))
    for pi in range(len(plank_edges)):                    # nail pairs
        nx_ = plank_edges[pi] + rng.randint(2, 10)
        for ny_ in (CEIL + rng.randint(6, 14), 410 - rng.randint(0, 10)):
            c.set(nx_, ny_, C("151d28"))
    # ceiling: joists over darkness + a dead bulb on its cable
    for y in range(0, CEIL):
        for x in range(SCENE_W):
            c.set(x, y, C("090a14"))
    for bx in range(40, SCENE_W, 128):
        jx = bx + rng.randint(-8, 8)
        c.rect(jx, 8, jx + 7, CEIL - 1, C("241527"))
        c.vline(jx + 7, 8, CEIL - 1, C("10141f"))
    c.vline(298, 0, 66, C("151d28"))
    c.rect(296, 67, 300, 72, C("394a50"))
    c.set(297, 69, C("577277"))
    # floor: board ROWS with staggered joints and rolled tones — the old
    # constant diagonal seam period was one more readable grid
    fy = 430
    row_i = 0
    while fy < SCENE_H:
        row_h = 8 + int((fy - 430) / 20) + rng.randint(0, 2)
        tone_flip = rng.random() < 0.5
        joints = []
        jx = -rng.randint(0, 60)
        while jx < SCENE_W:
            jx += rng.randint(46, 130)
            joints.append(jx)
        for y in range(fy, min(SCENE_H, fy + row_h)):
            for x in range(SCENE_W):
                warm, cool = light_levels(x, y)
                col = C("241527") if tone_flip else C("341c27")
                if warm > 0.44:
                    col = C("602c2c")
                elif warm > 0.28:
                    col = C("4d2b32")
                elif cool > 0.34:
                    col = C("1e1d39")
                if y == fy:
                    col = C("090a14")                     # row seam
                elif x in joints and y > fy + 1:
                    col = C("090a14")                     # staggered joint
                c.set(x, y, col)
        for jx in joints:                                  # nail at each joint
            if 0 <= jx - 1 < SCENE_W and fy + 2 < SCENE_H:
                c.set(jx - 1, fy + 2, C("151d28"))
        fy += row_h
        row_i += 1
    floor_region = {(x, y) for y in range(432, SCENE_H) for x in range(SCENE_W)}
    for i in range(7):                                     # worn traffic patches
        patch = blob(rng, rng.randrange(120, 840), rng.randrange(440, 520),
                     rng.randint(40, 110), floor_region)
        for (qx, qy) in patch:
            c.set(qx, qy, C("4d2b32"))
    # kettle's rug
    for y in range(438, 502):
        for x in range(96, 356):
            edge = min(x - 96, 355 - x, y - 438, 501 - y)
            if edge < 2 and rng.random() < 0.5:
                continue                      # frayed edge
            if edge < 2:
                c.set(x, y, C("752438"))
            elif rng.random() > 0.06:
                c.set(x, y, C("411d31"))
    c.rect(150, 462, 165, 470, C("341c27"))   # worn through to boards
    c.rect(280, 480, 291, 486, C("341c27"))

    # ---- THE JOB BOARD ----
    for y in range(108, 282):                 # drop shadow
        for x in range(78, 362):
            if rng.random() < 0.5:
                c.set(x, y, C("090a14"))
    c.rect(66, 92, 352, 274, C("341c27"))     # frame
    c.rect(70, 96, 348, 270, C("4d2b32"))     # cork
    cork_region = {(x, y) for y in range(96, 270) for x in range(70, 348)}
    for i in range(8):                        # cork wear patches, not dots
        patch = blob(rng, 70 + rng.randrange(278), 96 + rng.randrange(174),
                     rng.randint(16, 44), cork_region)
        for (qx, qy) in patch:
            c.set(qx, qy, C("602c2c") if i % 3 else C("341c27"))
    c.hline(66, 240, 91, C("ad7757"))         # top edge catch, warm half
    c.hline(241, 352, 91, C("577277"))        # cool half
    c.vline(92, CEIL - 1, 92, C("090a14"))    # hanging wires
    c.vline(326, CEIL - 1, 92, C("090a14"))

    def mini_photo(px0: int, py0: int, kind: str) -> None:
        c.rect(px0 - 1, py0 - 1, px0 + 24, py0 + 15, C("090a14"))
        for yy in range(15):
            for xx in range(24):
                c.set(px0 + xx, py0 + yy, C("253a5e") if yy < 8 else C("172038"))
        if kind == "transit":
            for xx in range(24):
                c.set(px0 + xx, py0 + 10, C("394a50"))
            c.rect(px0 + 14, py0 + 7, px0 + 19, py0 + 9, C("25562e"))
            c.vline(px0 + 5, py0 + 2, py0 + 10, C("090a14"))
            c.set(px0 + 6, py0 + 3, C("411d31"))
        elif kind == "the mills":
            c.rect(px0 + 4, py0 + 7, px0 + 17, py0 + 14, C("10141f"))
            c.vline(px0 + 7, py0 + 1, py0 + 7, C("10141f"))
            c.vline(px0 + 13, py0 + 2, py0 + 7, C("10141f"))
            c.set(px0 + 7, py0, C("341c27"))
            c.set(px0 + 8, py0 - 1, C("241527"))
        elif kind == "harbor":
            for xx in range(24):
                if rng.random() < 0.5:
                    c.set(px0 + xx, py0 + 12, C("3c5e8b"))
            c.vline(px0 + 16, py0 + 2, py0 + 11, C("090a14"))
            c.hline(px0 + 9, px0 + 16, py0 + 2, C("090a14"))
            c.set(px0 + 9, py0 + 3, C("090a14"))
            c.rect(px0 + 2, py0 + 9, px0 + 9, py0 + 11, C("10141f"))
        else:  # old ward
            for (bx_, bh) in ((1, 5), (6, 9), (12, 4), (17, 7)):
                c.rect(px0 + bx_, py0 + 12 - bh, px0 + bx_ + 4, py0 + 12,
                       C("10141f"))
            c.vline(px0 + 8, py0, py0 + 3, C("10141f"))

    def squiggle(x0: int, x1: int, y: int, col) -> None:
        for x in range(x0, x1):
            if (x - x0) % 11 == 9:
                continue                       # word gaps
            c.set(x, y + (1 if math.sin(x * 1.7) > 0.3 else 0), col)

    sheets = [("transit", 180, 110, False), ("the mills", 86, 122, True),
              ("harbor", 274, 128, True), ("old ward", 116, 196, True)]
    pins: list[tuple[int, int]] = []
    for (word, sx, sy, crossed) in sheets:
        pw, ph = (72, 64) if word == "transit" else (60, 54)
        paper = C("d7b594") if sx < 470 else C("a8b5b2")
        shade = C("c09473") if sx < 470 else C("819796")
        cut_a = rng.randint(1, 4)              # two torn corners, clean cuts
        cut_b = rng.randint(1, 4)
        for yy in range(ph):
            for xx in range(pw):
                if xx + yy < cut_a or (pw - xx) + (ph - yy) < cut_b:
                    continue                   # torn corners
                col = paper
                if xx > pw - 3 or yy > ph - 3:
                    col = shade                # edge shading
                c.set(sx + xx, sy + yy, col)
        pin = (sx + pw // 2, sy + 1)
        pins.append(pin)
        c.set(pin[0], pin[1], C("cf573c"))     # tack
        c.set(pin[0], pin[1] + 1, C("de9e41"))
        title = _render_word(word, C("241527"), C("341c27"))
        c.img.alpha_composite(title, (sx + 4, sy + 5))
        c.px = c.img.load()
        mini_photo(sx + 4, sy + 18, word)
        for ln in range(3):                    # unreadable notes, right column
            squiggle(sx + 31, sx + pw - 4, sy + 20 + ln * 6, C("341c27"))
        squiggle(sx + 4, sx + pw - 4, sy + 38, C("341c27"))
        squiggle(sx + 4, sx + pw - 18, sy + 44, C("341c27"))
        if crossed:                            # struck off the rotation
            for k in range(pw - 8):
                if rng.random() < 0.8:
                    c.set(sx + 4 + k, sy + 6 + int(k * (ph - 12) / pw),
                          C("a53030"))
        else:                                  # transit: ringed red, tonight
            for a in range(0, 360, 7):
                x = int(pin[0] + math.cos(math.radians(a)) * 7)
                y = int(pin[1] + 1 + math.sin(math.radians(a)) * 5)
                c.set(x, y, C("a53030"))
            squiggle(sx + 6, sx + 34, sy + 56, C("a53030"))
    for i in range(1, len(pins)):              # red strings between pins
        x0, y0 = pins[0]
        x1, y1 = pins[i]
        steps = 44
        for k in range(steps + 1):
            t = k / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t + math.sin(t * math.pi) * 5
            c.set(int(x), int(y), C("a53030"))

    # ---- kettle's corner (warm) ----
    c.rect(104, 384, 344, 398, C("602c2c"))    # table top
    c.rect(108, 398, 340, 404, C("341c27"))
    for lx in (118, 326):
        c.rect(lx, 404, lx + 5, 466, C("241527"))
        c.set(lx + 5, 406, C("341c27"))
    # KETTLE — a real little person, not a silhouette: seated behind the
    # table in profile, hunched toward the scale, candle-lit from the left
    kx, ky = 252, 330                                   # head anchor
    c.rect(kx, ky, kx + 15, ky + 11, C("d7b594"))       # face, profile left
    c.vline(kx + 15, ky + 2, ky + 10, C("c09473"))      # far shade
    c.rect(kx + 12, ky + 1, kx + 15, ky + 11, C("c09473"))
    c.rect(kx - 2, ky - 4, kx + 17, ky, C("341c27"))    # flat cap
    c.hline(kx - 5, kx + 6, ky, C("4d2b32"))            # brim toward candle
    c.set(kx - 5, ky - 1, C("602c2c"))
    c.rect(kx + 2, ky + 8, kx + 12, ky + 13, C("819796"))  # grey beard
    c.set(kx + 1, ky + 9, C("a8b5b2"))
    c.set(kx + 6, ky + 5, C("090a14"))                  # eye
    c.rect(kx - 4, ky + 13, kx + 20, ky + 40, C("602c2c"))  # coat, hunched
    c.rect(kx - 4, ky + 13, kx + 2, ky + 40, C("884b2b"))   # candle-lit front
    c.vline(kx - 4, ky + 14, ky + 39, C("ad7757"))
    c.rect(kx + 14, ky + 13, kx + 20, ky + 40, C("4d2b32")) # shaded back
    c.rect(kx + 4, ky + 16, kx + 12, ky + 20, C("341c27"))  # scarf
    c.rect(kx - 12, ky + 18, kx - 2, ky + 23, C("602c2c"))  # arm reaching out
    c.hline(kx - 12, kx - 2, ky + 18, C("884b2b"))
    c.rect(kx - 16, ky + 21, kx - 11, ky + 25, C("d7b594")) # hand at the scale
    c.set(kx - 16, ky + 25, C("c09473"))
    c.rect(kx - 2, ky + 40, kx + 18, ky + 46, C("341c27"))  # lap into table line
    # the scale, big enough to read
    c.vline(205, 324, 382, C("202e37"))
    c.vline(206, 324, 382, C("151d28"))
    c.hline(167, 245, 324, C("202e37"))
    c.hline(167, 245, 325, C("151d28"))
    for (ex, pan_y) in ((167, 344), (245, 336)):
        c.vline(ex, 326, pan_y - 3, C("394a50"))       # chains
        c.hline(ex - 9, ex + 9, pan_y, C("151d28"))    # pan
        c.hline(ex - 7, ex + 7, pan_y + 1, C("202e37"))
        c.set(ex - 9, pan_y - 1, C("394a50"))
        c.set(ex + 9, pan_y - 1, C("394a50"))
    for k in range(6):                                  # brass in the low pan
        c.set(162 + k * 2, 343, C("e8c170") if k % 2 else C("de9e41"))
    c.set(205, 320, C("577277"))                        # pivot glint
    for i in range(110):                                # brass pile on the table
        px_ = 262 + rng.randrange(70)
        py_ = 376 + rng.randrange(8)
        c.set(px_, py_, (C("de9e41"), C("e8c170"), C("be772b"))[rng.randrange(3)])
    # the candle, fat, with a SOLID banded wall halo that respects the plank
    # lines (runtime glow breathes softly on top)
    plank_set = set(plank_edges)
    for dy in range(-38, 39):
        for dx in range(-54, 55):
            d = (dx / 54.0) ** 2 + (dy / 38.0) ** 2
            x = CANDLE[0] + dx
            y = CANDLE[1] - 24 + dy
            if d < 1.0 and y < 384 and x not in plank_set:
                if d < 0.34:
                    c.set(x, y, C("ad7757"))
                elif d < 0.72:
                    c.set(x, y, C("884b2b"))
    c.rect(CANDLE[0] - 3, CANDLE[1] - 16, CANDLE[0] + 2, CANDLE[1], C("d7b594"))
    c.vline(CANDLE[0] + 2, CANDLE[1] - 14, CANDLE[1], C("c09473"))
    c.set(CANDLE[0] - 1, CANDLE[1] - 18, C("de9e41"))
    c.rect(CANDLE[0] - 1, CANDLE[1] - 21, CANDLE[0], CANDLE[1] - 18, C("e8c170"))
    c.set(CANDLE[0] - 1, CANDLE[1] - 22, C("e7d5b3"))
    c.hline(CANDLE[0] - 6, CANDLE[0] + 5, CANDLE[1] + 1, C("884b2b"))
    c.hline(CANDLE[0] - 4, CANDLE[0] + 3, CANDLE[1] + 2, C("602c2c"))
    # ashtray on the table's end — runtime smoke rises from here
    c.rect(330, 378, 340, 381, C("202e37"))
    c.set(334, 377, C("cf573c"))

    # ---- VERNE at the medicine shelf (center-right), a real figure ----
    c.hline(636, 706, 248, C("341c27"))                 # shelf plank
    c.hline(636, 706, 249, C("241527"))
    c.rect(640, 234, 646, 247, C("25562e"))             # bottles, all different
    c.set(642, 232, C("468232"))
    c.set(641, 238, C("468232"))
    c.rect(652, 238, 657, 247, C("3c5e8b"))
    c.set(654, 236, C("73bed3"))
    c.rect(663, 230, 668, 247, C("819796"))             # tall jar
    c.set(664, 234, C("a8b5b2"))
    c.rect(674, 240, 683, 247, C("c7cfcc"))             # one bandage roll
    c.set(677, 243, C("819796"))
    vx, vy = 652, 286                                   # head anchor
    c.rect(vx, vy, vx + 13, vy + 12, C("d7b594"))       # face, 3/4 right
    c.vline(vx, vy + 2, vy + 11, C("c09473"))
    c.rect(vx - 1, vy - 3, vx + 14, vy + 1, C("341c27"))  # short dark hair
    c.set(vx + 14, vy - 1, C("4d2b32"))
    c.set(vx + 9, vy + 5, C("090a14"))                  # eye
    c.rect(vx - 4, vy + 12, vx + 17, vy + 48, C("394a50"))  # coat
    c.rect(vx + 1, vy + 16, vx + 12, vy + 44, C("c7cfcc"))  # medic apron
    c.vline(vx + 1, vy + 17, vy + 43, C("a8b5b2"))
    c.set(vx + 6, vy + 22, C("a53030"))                 # small red cross
    c.set(vx + 6, vy + 24, C("a53030"))
    c.set(vx + 5, vy + 23, C("a53030"))
    c.set(vx + 7, vy + 23, C("a53030"))
    c.vline(vx + 17, vy + 14, vy + 46, C("253a5e"))     # cool rim
    c.vline(vx - 4, vy + 14, vy + 46, C("2a2e37") if False else C("341c27"))
    c.rect(vx - 9, vy + 24, vx - 3, vy + 29, C("394a50"))   # arm up to shelf
    c.rect(vx - 12, vy + 20, vx - 6, vy + 25, C("d7b594"))  # hand at a bottle
    c.rect(vx - 2, vy + 48, vx + 6, vy + 78, C("202e37"))   # legs
    c.rect(vx + 8, vy + 48, vx + 16, vy + 78, C("151d28"))
    c.rect(vx - 3, vy + 78, vx + 7, vy + 82, C("10141f"))   # boots
    c.rect(vx + 7, vy + 78, vx + 17, vy + 82, C("090a14"))
    c.rect(vx - 8, vy + 84, vx + 22, vy + 87, C("090a14"))  # ground shadow

    # ---- mara at the radio wall (cool) ----
    # units first: two SCREEN units (glowing scanline faces), the rest dark
    units = ((700, 240, 790, 296, True), (700, 304, 768, 352, False),
             (796, 252, 886, 300, True), (776, 308, 874, 356, False),
             (700, 360, 786, 400, False), (794, 364, 868, 404, False))
    for (rx0, ry0, rx1, ry1, screen) in units:
        # baked halo behind the glowing units, BEFORE the box itself
        c.rect(rx0, ry0, rx1, ry1, C("151d28"))
        c.rect(rx0 + 2, ry0 + 2, rx1 - 2, ry1 - 2, C("202e37"))
        if screen:                                       # scanline glass, clean
            for yy in range(ry0 + 5, ry1 - 10):
                for xx in range(rx0 + 6, rx1 - 6):
                    if yy % 2 == 0:
                        c.set(xx, yy, C("253a5e"))
                    else:
                        c.set(xx, yy, C("172038"))
            for xx in range(rx0 + 6, rx1 - 6):           # a waveform trace
                yy = (ry0 + ry1) // 2 + int(math.sin(xx * 0.55) * 3)
                c.set(xx, yy, C("73bed3"))
            c.hline(rx0 + 6, rx1 - 6, ry1 - 8, C("394a50"))  # control strip
            for i in range(3):
                c.set(rx0 + 10 + i * 8, ry1 - 6, C("577277"))
        else:                                            # dark unit: one LED
            c.set(rx1 - 8, ry0 + 8, C("73bed3"))
            c.set(rx1 - 9, ry0 + 8, C("253a5e"))         # its tiny halo
            c.set(rx1 - 8, ry0 + 7, C("172038"))
            c.set(rx1 - 8, ry0 + 9, C("172038"))
    for (nx_, ny_) in ((746, 262), (814, 272)):          # dial faces (needles)
        c.rect(nx_ - 10, ny_ - 8, nx_ + 10, ny_ + 5, C("253a5e"))
        c.rect(nx_ - 9, ny_ - 7, nx_ + 9, ny_ + 4, C("3c5e8b"))
        c.rect(nx_ - 8, ny_ - 6, nx_ + 8, ny_ + 3, C("172038"))
    # the junction box the whole rig feeds into — cables visibly run to it
    c.rect(878, 226, 894, 240, C("202e37"))
    c.rect(880, 228, 892, 238, C("151d28"))
    c.set(884, 232, C("cf573c"))                          # fuse LED
    c.set(883, 232, C("752438"))
    c.set(885, 232, C("752438"))
    for (sx_, sy_, ex_, ey_) in ((884, 240, 840, 252), (884, 240, 886, 300),
                                 (880, 238, 790, 244)):
        steps = 24                                        # cable drops
        for k in range(steps + 1):
            t = k / steps
            x = sx_ + (ex_ - sx_) * t
            y = sy_ + (ey_ - sy_) * t + math.sin(t * math.pi) * 6
            c.set(int(x), int(y), C("090a14"))
    for k in range(80):                                   # cable arcs above
        t = k / 80.0
        c.set(int(700 + t * 178), int(226 + math.sin(t * 3.4) * 9 + t * 4),
              C("090a14"))
        c.set(int(730 + t * 148), int(214 + math.sin(t * 4.4) * 7 + t * 16),
              C("10141f"))
    c.rect(690, 408, 900, 420, C("341c27"))              # desk
    c.rect(694, 420, 896, 426, C("241527"))
    c.vline(706, 426, 486, C("241527"))
    c.vline(882, 426, 490, C("241527"))
    # MARA — seated at the rig, oxblood jacket (the warm accent inside the
    # cool zone: the eye goes to her), headset on, screen-lit
    mx, my = 736, 336                                    # head anchor
    c.rect(mx, my, mx + 14, my + 12, C("d7b594"))        # face, 3/4 right
    c.vline(mx, my + 3, my + 11, C("c09473"))
    c.rect(mx - 2, my - 4, mx + 8, my + 10, C("4d2b32")) # hair
    c.rect(mx - 4, my + 8, mx + 1, my + 22, C("4d2b32")) # low ponytail
    c.set(mx - 4, my + 22, C("341c27"))
    c.set(mx + 10, my + 5, C("090a14"))                  # eye toward screens
    c.hline(mx - 2, mx + 14, my - 5, C("151d28"))        # headset band
    c.set(mx - 2, my - 4, C("151d28"))
    c.set(mx + 14, my - 4, C("151d28"))
    c.rect(mx + 12, my + 4, mx + 17, my + 12, C("202e37"))  # ear cup
    c.set(mx + 14, my + 7, C("73bed3"))                  # cup LED
    c.hline(mx - 1, mx + 12, my - 3, C("3c5e8b"))        # screen light on hair
    c.rect(mx - 6, my + 12, mx + 18, my + 44, C("752438"))  # jacket
    c.vline(mx + 18, my + 14, my + 42, C("3c5e8b"))      # rig-side rim
    c.rect(mx + 16, my + 14, mx + 18, my + 42, C("411d31"))
    c.vline(mx - 6, my + 14, my + 42, C("411d31"))       # shaded back
    c.rect(mx + 12, my + 20, mx + 30, my + 26, C("752438"))  # arm to the dial
    c.hline(mx + 12, mx + 30, my + 20, C("df84a5") if False else C("a53030"))
    c.rect(mx + 28, my + 24, mx + 34, my + 29, C("d7b594"))  # hand on the knob
    c.rect(mx - 8, my + 44, mx + 16, my + 66, C("202e37"))   # legs, seated
    c.rect(mx - 10, my + 66, mx - 2, my + 72, C("10141f"))   # boot
    c.rect(mx + 12, my + 44, mx + 18, my + 50, C("151d28"))
    c.rect(mx - 14, my + 42, mx + 20, my + 47, C("341c27"))  # chair seat
    c.vline(mx - 10, my + 47, my + 76, C("241527"))          # chair legs
    c.vline(mx + 16, my + 47, my + 78, C("241527"))
    c.rect(mx - 18, my + 8, mx - 13, my + 46, C("341c27"))   # chair back
    c.vline(mx - 13, my + 10, my + 44, C("241527"))

    # (no baked dot-vignette — the runtime vignette.png is smooth alpha)

    # candle glow overlay (soft alpha, breathes at runtime)
    gw, gh = 240, 170
    glow = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    gp = glow.load()
    r, g, b, _ = C("e8c170")
    for y in range(gh):
        for x in range(gw):
            d = ((x - gw / 2) / (gw / 2)) ** 2 + ((y - gh / 2) / (gh / 2)) ** 2
            if d < 1.0:
                gp[x, y] = (r, g, b, int(70 * (1.0 - d) ** 2))

    # VU needle strip: 3 frames, 16x12
    strip = Canvas(48, 12)
    for f in range(3):
        ox = f * 16
        strip.rect(ox, 0, ox + 15, 11, C("253a5e"))
        strip.rect(ox + 1, 1, ox + 14, 10, C("172038"))
        strip.set(ox + 13, 2, C("a53030"))
        strip.set(ox + 14, 2, C("a53030"))
        tip = (ox + 4, 3) if f == 0 else ((ox + 8, 2) if f == 1 else (ox + 12, 3))
        x0, y0 = ox + 8, 10
        for k in range(9):
            t = k / 8.0
            strip.set(int(x0 + (tip[0] - x0) * t), int(y0 + (tip[1] - y0) * t),
                      C("c7cfcc"))
    return c, glow, strip


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

def make_fog_puffs() -> list[Image.Image]:
    """Dawn fog wisps: lobed soft-alpha clouds (atmosphere — palette-exempt
    like light and dust). The runtime drifts them through the woods each
    morning at very low opacity; they must never block vision."""
    out: list[Image.Image] = []
    # 0..2: wisps. 3..4: BIG banks, roughly double — mixed sizes read as real
    # weather instead of a swarm of identical puffs (user call)
    sizes = [((104, 150), (26, 38)), ((104, 150), (26, 38)), ((104, 150), (26, 38)),
             ((200, 250), (44, 60)), ((230, 290), (50, 68))]
    for i in range(5):
        rng = random.Random(f"{SEED}:fog:{i}")
        (w_lo, w_hi), (h_lo, h_hi) = sizes[i]
        w = rng.randint(w_lo, w_hi)
        h = rng.randint(h_lo, h_hi)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        lobes = [(w * 0.5, h * 0.55, w * 0.42, h * 0.40)]
        for L in range(rng.randint(2, 3) + (2 if i >= 3 else 0)):
            lobes.append((rng.uniform(w * 0.22, w * 0.78),
                          rng.uniform(h * 0.35, h * 0.72),
                          rng.uniform(w * 0.16, w * 0.30),
                          rng.uniform(h * 0.22, h * 0.42)))
        for y in range(h):
            for x in range(w):
                a = 0.0
                for (cx, cy, rx, ry) in lobes:
                    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                    if d < 1.0:
                        a = max(a, (1.0 - d) ** 1.5)
                if a > 0.02:
                    px[x, y] = (168, 181, 178, int(200 * a))
        out.append(img)
    return out


def make_leaves() -> list[Image.Image]:
    """Falling-leaf strips: 2 flutter frames per color (green, bright,
    dry). Tiny palette sprites the environment tumbles off shedder oaks."""
    combos = [("25562e", "19332d"), ("468232", "25562e"), ("884b2b", "602c2c")]
    out: list[Image.Image] = []
    for (a, b) in combos:
        ca, cb = C(a), C(b)
        img = Image.new("RGBA", (6, 3), (0, 0, 0, 0))
        img.putpixel((0, 1), ca)    # frame 0: lying flat
        img.putpixel((1, 1), ca)
        img.putpixel((1, 0), cb)
        img.putpixel((4, 0), ca)    # frame 1: folded edge-on
        img.putpixel((4, 1), ca)
        img.putpixel((3, 1), cb)
        out.append(img)
    return out


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

    manifest: dict = {"tile": [64, 32], "wall_h": WALL_H, "story_h": STORY_H,
                      "floors": {}, "props": {}, "families": {}, "char": {}}

    floors, coords = make_floors_atlas()
    assert_palette(floors, "floors")
    floors.save(OUT / "floors.png")
    manifest["floors"] = coords

    # entries: 3-tuples, or 4 with light coords (vehicles)
    entries, families = prop_inventory()
    for name, piece in wall_piece_inventory().items():
        entries[name] = piece
    for tone in ROOF_TONES:
        for v in range(4):
            entries[f"roof_tile_{tone}_{v}"] = make_roof_tile(tone, v)
        for v in range(2):
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
                "seg_", "seg2_", "post_", "post2_", "door_", "ui_grabber")
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
    for i, puff in enumerate(make_fog_puffs()):
        puff.save(OUT / f"fog_{i}.png")               # atmosphere: soft alpha
    for i, leaf in enumerate(make_leaves()):
        leaf.save(OUT / f"leaves_{i}.png")
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
    drain_base, drain_ray, drain_ripple = make_scene_drain()
    assert_palette(drain_base.img, "menu_drain")
    assert_palette(drain_ripple.img, "menu_drain_ripple")
    drain_base.img.save(OUT / "menu_drain.png")
    drain_ray.save(OUT / "menu_drain_ray.png")          # light: soft alpha
    drain_ripple.img.save(OUT / "menu_drain_ripple.png")
    den_base, den_glow, den_needles = make_scene_den()
    assert_palette(den_base.img, "menu_den")
    assert_palette(den_needles.img, "menu_den_needles")
    den_base.img.save(OUT / "menu_den.png")
    den_glow.save(OUT / "menu_den_glow.png")            # light: soft alpha
    den_needles.img.save(OUT / "menu_den_needles.png")

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
