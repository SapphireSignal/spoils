#!/usr/bin/env python3
"""SPOILS art pipeline. Generates every game asset into art/gen/ from the Apollo
palette. Deterministic: same script -> same pixels. If an asset looks bad, fix
this file and rerun; never hand-edit outputs.

Outputs:
  art/gen/floors.png     - 64x32 iso floor tiles, 4-COLUMN atlas, rows =
                           ceil(len(FLOOR_TILES)/4) — 76 tiles today, so a
                           4x19 grid at 256x608 (this said "4x5")
  art/gen/seg*_*.png,
  art/gen/post*_*.png    - thin EDGE-wall segments (plain/window/broken,
                           seg2_/post2_ for the two-story cut) and the
                           square corner posts that cover their joints.
                           (This said "wall_*.png"; no such file is ever
                           written — the edge-wall system replaced the
                           full-tile blocks.)
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

    def outline_auto(self, c=OUTLINE, sides: bool = True) -> set:
        """sides=False skips the LEFT/RIGHT neighbours. Pieces that tile
        edge to edge — the wall segments — must not outline the joins, or
        every seam becomes a black line down the building and the gap
        between two outlines lets whatever is behind show through (user
        saw their own arm through the wall)."""
        opaque = {(x, y) for y in range(self.h) for x in range(self.w)
                  if self.px[x, y][3] > 0}
        painted: set = set()
        steps = ((1, 0), (-1, 0), (0, 1), (0, -1)) if sides else ((0, 1), (0, -1))
        for (x, y) in list(opaque):
            for dx, dy in steps:
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

# --------------------------------------------------------------- floors ------

CONC_D2, CONC_D1, CONC_BASE, CONC_L1, CONC_L2 = (
    C("151d28"), C("202e37"), C("394a50"), C("577277"), C("819796"))

def speckle(c: Canvas, rng: random.Random, region, colors: list[tuple], probs: list[float]) -> None:
    """Organic wear PATCHES, not dot noise (user call 2026-08-01: no little
    dots anywhere, ever). Each color TARGETS roughly prob*0.9 of the region,
    hard-capped at 20%, painted as at most 3 soft blob-shaped patches of
    6-16 px — so coverage lands near the old per-pixel prob, and at the
    larger probs the 3-patch cap holds it well under even that. Reads as
    stains and wear instead of static. (This said "prob*3"; that was the
    FIRST cut and it was retuned down for reading as camo clutter — see the
    inline comment on the loop.) Same signature as the old per-pixel
    speckle so every call site stays valid."""
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
                            # (the old weed pixels here were the "little green
                            # bits" the user banned from walkways)
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
    elif kind.startswith("asphalt_line"):
        # CENTRE dashes. The road is FOUR cells wide, so its true centre is
        # the boundary between the middle two cells (+1 and +2); each paints
        # half the dash along that shared edge. "_h" = roads along +x
        # (screen SE); plain = along +y (SW). "b" = the +2 cell's half.
        #
        # Two things broke this twice before, both invisible from the code:
        # (1) a diamond tile only OWNS two of its four edges (the top-left
        # and top-right ones) — the other two belong to its neighbours, so
        # a half painted along them renders as almost nothing. The plain
        # "b" tile drew LITERALLY ZERO yellow pixels, which is why one lone
        # half-dash was left sitting a full lane off centre. (2) the p
        # parameter runs WITH +x on the plain tiles but AGAINST +y on the
        # "_h" ones, so a single shared condition cannot be right for both
        # orientations — the horizontal roads happened to land correctly
        # and the vertical ones did not (user photo, marked in red).
        #
        # So: work out which end of p is the shared edge for this tile, and
        # measure the region the tile actually owns instead of assuming it
        # reaches ±16. Both halves then sit hard against the true centre.
        region = _floor_base(c, rng, CONC_D1, CONC_D2, CONC_BASE, 0.0, 0.0)  # smooth like the road (user: nothing on the asphalt but cracks/holes)
        horiz = "_h" in kind
        far = kind.endswith("b")
        inner_high = far == horiz
        params = {}
        for (x, y) in region:
            params[(x, y)] = (x - 32) * 0.5 - (y - 16) if horiz \
                else (x - 32) * 0.5 + (y - 16)
        if params:
            edge_p = max(params.values()) if inner_high else min(params.values())
            for (x, y), p in params.items():
                # keep the ORIGINAL dash weight (~1.5 world px): the tile
                # that owns the boundary lays the dash, its partner adds
                # whatever sliver falls on its side. A wider band read as
                # fat notched blocks instead of a painted line.
                on_edge = abs(p - edge_p) <= 1.3
                if on_edge and (x // 8) % 2 == 0 and rng.random() < 0.94:
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
        along_x = "_x" in kind
        # ONE track, the whole way across the district: wooden ties under
        # steel rail, identical tile to tile so the line reads as
        # continuous and connected (user call — the worn/overgrown
        # variants made it look like different broken bits of railway).
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
    ("asphalt_line", ("asphalt_line", 0)), ("asphalt_line_b", ("asphalt_line_b", 0)),
    ("asphalt_line_h", ("asphalt_line_h", 0)), ("asphalt_line_h_b", ("asphalt_line_h_b", 0)),
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
    # the y-axis rail tiles are gone from the registry, not the maker: the
    # district only ever runs rail on x, and the maker stays parameterized
    # for a future map that doesn't
    ("rail_x", ("rail_x", 0)),
    ("rail_cross_x", ("rail_cross_x", 0)),
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

    c.outline_auto(sides=False)   # tiles edge to edge: no seam lines
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
    c.outline_auto(sides=False)   # tiles edge to edge: no seam lines
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
# MODULAR roof, assembled per interior cell — see the placement formulas
# below, which are the truth. (This block used to describe "one purpose-built
# roof slab per building size" that "spans the interior plus a small
# overhang". There is no slab and no per-size asset: no make_roof_slab
# exists, and the comment 8 lines down says the opposite.)
# Vents and a hatch are placed as separate props. The game lifts the whole
# assembly by the wall height and fades it for the interior reveal.

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
#     roof_eave_<tone>_n     (north edges: flat flush 3px closure over the
#                             wall coping)
#     roof_eave_<tone>_w     (west edges: the same, on the y-axis)
#     roof_corner_<tone>     (a cap at each corner)
# (These three lines said "roof_rim_<tone> — 1px lit rim only". No roof_rim
#  asset has ever existed; make_roof_eave is the real maker.)
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
    return c, (19, 17), ["diamond", 12.0, 6.0]

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

def bake_lean(c: Canvas, origin: tuple[int, int], lean: float,
              pivot_y: int | None = None) -> tuple[Canvas, tuple[int, int]]:
    """Tip a prop over by a few degrees — BAKED, never at runtime.

    Runtime rotation is banned in this project: it resamples the sprite off
    the pixel grid and shimmers while the camera scrolls. So a "rotated"
    crate is a DIFFERENT SPRITE, sheared here at generation time. Rows are
    slid horizontally by their height above the pivot, which reads as a
    small tilt at this scale and keeps every pixel on the grid.

    lean: pixels of slide per 10 px of height. +right, -left. Keep it in
    the ±1.5 range — beyond that a box stops looking tipped and starts
    looking broken.
    """
    pivot = c.h - 1 if pivot_y is None else pivot_y
    out = Canvas(c.w + 8, c.h)
    ox = 4
    for y in range(c.h):
        shift = int(round((pivot - y) / 10.0 * lean))
        for x in range(c.w):
            px = c.px[x, y]
            if px[3]:
                out.set(x + ox + shift, y, px)
    return out, (origin[0] + ox, origin[1])


def bake_wear(c: Canvas, rng: random.Random, colors: list[tuple],
              amount: float = 0.06) -> None:
    """Age one instance of a prop: a few small solid patches of grime and
    rust over its opaque pixels. Uses the same patch logic as the tiles
    (NO single-pixel dot noise — user call), so two crates off the same
    generator never wear identically."""
    region = [(x, y) for y in range(c.h) for x in range(c.w)
              if c.px[x, y][3] > 0]
    if not region:
        return
    speckle(c, rng, region, colors, [amount] * len(colors))


def clutter_variants(name: str, count: int, build, rng_seed: str,
                     wear_colors: list[tuple] | None = None,
                     leans: tuple = (0.0, 0.9, -0.9, 1.4, -1.4)) -> list:
    """Bake `count` genuinely different copies of one prop.

    This is the anti-repetition workhorse: every copy gets its own build
    seed (so the generator's own randomness differs), its own baked lean
    from the table, and its own wear pass. Dropping five of these in a
    pile reads as five objects somebody threw down, not one object
    stamped five times.
    """
    out = []
    for i in range(count):
        rng = random.Random(f"{SEED}:{rng_seed}:{i}")
        canvas, origin, collider = build(rng, i)[:3]
        # the builders hand back a TIGHT canvas (already outlined and
        # cropped), so pad before doing anything — leaning and re-outlining
        # a tight sprite pushes ink straight off the edge
        pad = 6
        roomy = Canvas(canvas.w + pad * 2, canvas.h + pad * 2)
        roomy.img.alpha_composite(canvas.img, (pad, pad))
        roomy.px = roomy.img.load()
        canvas = roomy
        origin = (origin[0] + pad, origin[1] + pad)
        lean = leans[i % len(leans)]
        if abs(lean) > 0.01:
            canvas, origin = bake_lean(canvas, origin, lean)
        if wear_colors:
            bake_wear(canvas, rng, wear_colors, 0.04 + 0.03 * (i % 3))
        canvas, origin = crop_canvas(canvas, origin)
        out.append((canvas, origin, collider))
    return out


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

ROOF_DEPTH = 18  # top-face depth in px. 6 read as paper, 12 still read as a
                 # narrow car — this matches the TRUE body width the head-on
                 # and flank views show, so all 8 facings are one vehicle
                 # (user approved the wider cars 2026-08-01)


def _diag_poly(half_long: float, half_wide: float) -> list:
    """Collision parallelogram along the screen (2,1) diagonal — vehicles
    LIE on that diagonal, so an axis-aligned diamond either over-blocks the
    sides or lets you walk through the nose (user report: it did both)."""
    ux, uy = 0.8944, 0.4472
    vx, vy = -0.4472, 0.8944
    corners = [
        (half_long * ux + half_wide * vx, half_long * uy + half_wide * vy),
        (half_long * ux - half_wide * vx, half_long * uy - half_wide * vy),
        (-half_long * ux - half_wide * vx, -half_long * uy - half_wide * vy),
        (-half_long * ux + half_wide * vx, -half_long * uy + half_wide * vy),
    ]
    flat: list = []
    for (px, py) in corners:
        flat.append(round(px, 1))
        flat.append(round(py, 1))
    return ["poly", flat]

VEH_PALETTES = [
    ("752438", "411d31", "241527"),   # oxblood
    ("577277", "394a50", "202e37"),   # gray
    ("25562e", "19332d", "10141f"),   # olive
    ("884b2b", "602c2c", "341c27"),   # rust
    ("3c5e8b", "253a5e", "172038"),   # steel blue
    ("ad7757", "7a4841", "4d2b32"),   # tan
]


def _veh_profile(kind: str, length: int) -> list[int]:
    """Longitudinal height profile from the FRONT (index 0) to the rear,
    at any length. Same silhouette the (2,1) views are built from, so a
    car keeps its shape whichever way it points."""
    prof = []
    for i in range(length):
        f = i / float(length - 1)
        if kind == "car":
            if f < 0.065:
                h = 7
            elif f < 0.26:
                h = 10
            elif f < 0.37:
                h = 10 + int((f - 0.26) / 0.11 * 10)   # windshield rake
            elif f < 0.70:
                h = 20                                  # roof
            elif f < 0.78:
                h = 20 - int((f - 0.70) / 0.08 * 9)     # rear glass
            elif f < 0.93:
                h = 11                                  # trunk
            else:
                h = 8
        else:                                           # pickup
            if f < 0.065:
                h = 8
            elif f < 0.22:
                h = 11
            elif f < 0.28:
                h = 11 + int((f - 0.22) / 0.06 * 9)
            elif f < 0.52:
                h = 20                                  # cab roof
            elif f < 0.57:
                h = 12
            else:
                h = 10                                  # bed wall
        prof.append(h)
    return prof


def make_vehicle_flank(kind: str, scheme: int, broken: bool = False,
                       door_open: bool = False) -> tuple[Canvas, tuple, list]:
    """SCREEN-HORIZONTAL heading (a world diagonal): the flank faces the
    camera dead-on, so the roof lies as a flat band straight above it and
    both end faces go edge-on. The profile runs front-to-rear along +x,
    so the FRONT is at the LEFT — this art IS the westbound sprite, and
    mirroring gives the eastbound twin. (It used to be registered the
    other way round, which is why a car driving left faced right — user
    report 2026-08-01.) One of the four angles the (2,1) sheets can't
    cover."""
    rng = random.Random(f"{SEED}:vehicle8:flank:{kind}:{scheme}:{broken}")
    body_c, body_d, body_dd = (C(n) for n in VEH_PALETTES[scheme])
    glass, glass_d = C("3c5e8b"), C("253a5e")
    L = 62
    depth = 11                       # roof plane: the car's width, foreshortened
    prof = _veh_profile(kind, L)
    clear = 4
    ox, oy = 6, 46
    c = Canvas(L + 14, 68)
    for i in range(L):               # the near flank: one clean vertical face
        x = ox + i
        for y in range(oy - clear - prof[i], oy - clear + 1):
            c.set(x, y, body_d)
    for i in range(L):               # top surface, straight up (width axis)
        x = ox + i
        top = oy - clear - prof[i]
        for t in range(1, depth + 1):
            col = body_c
            if t == depth:
                col = body_dd        # the far rim closes the silhouette
            elif t == depth - 1:
                col = body_d
            c.set(x, top - t, col)
    for i in range(1, L):            # bridge the raked jumps in the contour
        step = prof[i] - prof[i - 1]
        if step > 1:
            for k in range(step):
                c.set(ox + i, oy - clear - prof[i - 1] - k, body_c)
        elif step < -1:
            for k in range(-step):
                c.set(ox + i - 1, oy - clear - prof[i] - k, body_c)
    # windshield + rear glass read as raked panels on the top surface
    for (lo, hi) in ((0.265, 0.37), (0.70, 0.78)):
        for i in range(int(L * lo), int(L * hi)):
            x = ox + i
            top = oy - clear - prof[i]
            for t in range(3, depth - 2):
                c.set(x, top - t, glass if t < depth // 2 else glass_d)
    for i in range(int(L * 0.30), int(L * 0.72)):   # side windows + pillars
        x = ox + i
        top = oy - clear - prof[i]
        if (i - int(L * 0.30)) % 11 < 9:
            for y in range(top + 2, top + 9):
                c.set(x, y, C("090a14") if broken else glass_d)
            if (i - int(L * 0.30)) % 11 < 3:
                for y in range(top + 2, top + 6):
                    c.set(x, y, C("090a14") if broken else glass)
    for i in range(2, L - 2):                        # body trim line
        c.set(ox + i, oy - clear - 2, body_dd)
    c.set(ox + L // 2, oy - clear - 3, body_dd)      # door shutline
    for y in range(oy - clear - prof[L // 2] + 3, oy - clear - 2):
        c.set(ox + L // 2, y, body_dd)
    lights_px: list[tuple[int, int]] = []
    # profile index 0 is the FRONT and draws at the LEFT edge — headlights
    # left, tail lights right (they were painted swapped, so the lamps
    # contradicted the bodywork on both flank headings)
    for k in range(3):                               # headlights, front corner
        c.set(ox + k, oy - clear - prof[0] - 1, C("e8c170"))
    lights_px.append((ox + 1, oy - clear - prof[0] - 1))
    for k in range(3):                               # tail lights, rear corner
        c.set(ox + L - 1 - k, oy - clear - prof[L - 1] - 1, C("a53030"))
    lights_px.append((ox + L - 2, oy - clear - prof[L - 1] - 1))
    c.set(ox + L - 1, oy - clear - 1, C("202e37"))   # bumpers
    c.set(ox, oy - clear - 1, C("202e37"))
    for wf in (int(L * 0.17), int(L * 0.74)):        # wheels on the near side
        cxw = ox + wf
        cyw = oy - 1
        for dy in range(-2, 3):
            for dx in range(-4, 5):
                if dx * dx + dy * dy * 2 <= 12:
                    c.set(cxw + dx, cyw + dy, (0, 0, 0, 0))
        for dy in range(-3, 3):
            for dx in range(-4, 5):
                d = dx * dx + dy * dy * 2
                if d <= 16:
                    c.set(cxw + dx, cyw + dy, C("10141f") if d > 5 else C("202e37"))
        c.set(cxw, cyw, C("577277"))
    if door_open or broken:                          # the swung door panel
        di = ox + L // 2 - 3
        for k in range(7):
            for y in range(oy - clear - 2, oy - clear + 3 - k // 3):
                c.set(di + k, y, body_d if 0 < k < 6 else body_dd)
            if 1 < k < 5:
                c.set(di + k, oy - clear, C("090a14") if broken else glass_d)
    if broken:
        for _ in range(rng.randint(8, 12)):
            x = ox + rng.randrange(2, L - 2)
            y = oy - clear - rng.randrange(1, max(2, prof[x - ox] - 1))
            c.set(x, y, C("884b2b") if rng.random() < 0.6 else C("602c2c"))
    c.outline_auto()
    origin_full = (ox + L // 2, oy)
    cropped, origin = crop_canvas(c, origin_full)
    lights_rel = [[px - origin_full[0], py - origin_full[1]] for (px, py) in lights_px]
    # ground footprint: long across the screen, shallow front-to-back
    half_long = 30.0 if kind == "car" else 32.0
    return cropped, origin, ["poly", [
        -half_long, -7.0, half_long, -7.0, half_long, 7.0, -half_long, 7.0]], \
        lights_rel


def make_vehicle_head(kind: str, scheme: int, toward: bool,
                      broken: bool = False,
                      door_open: bool = False) -> tuple[Canvas, tuple, list]:
    """SCREEN-VERTICAL heading (the other world diagonal): the car comes
    at the camera (toward=True, grille and headlights) or drives away
    (toward=False, tail lights over the trunk). Both flanks go edge-on,
    so this is the roof stacked in bands with ONE end face — drawn back
    to front so nearer bands occlude farther ones."""
    rng = random.Random(f"{SEED}:vehicle8:head:{kind}:{scheme}:{toward}:{broken}")
    body_c, body_d, body_dd = (C(n) for n in VEH_PALETTES[scheme])
    glass, glass_d = C("3c5e8b"), C("253a5e")
    # Seen end-on, a sedan hides everything past its roof, so the whole
    # view is FOUR solid surfaces: the end face, the hood (or trunk), the
    # raked glass, and the roof. Drawn as bands, never per-station — a
    # per-station pass ladders into stripes on the flat runs.
    W = 28                            # the body's true width, head on
    hw_body = W // 2
    hw_glass = hw_body - 4            # the greenhouse taper IS the 3D read
    h_face = 10 if toward else 11     # hood line / trunk line
    h_roof = 20
    d_low = 5 if toward else 4        # hood or trunk length, foreshortened
    d_rake = 3 if toward else 2       # windshield / rear glass
    d_roof = 8
    ox, oy = 8, 66
    c = Canvas(W + 16, 78)
    cx = ox + W // 2

    def _band(y_hi: int, y_lo: int, hw_hi: int, hw_lo: int, top_face: bool) -> None:
        # one surface, filled solid to the ground so nothing can stripe;
        # nearer bands are drawn later and occlude what is behind them
        span = max(1, y_lo - y_hi)
        for y in range(y_hi, y_lo + 1):
            f = (y - y_hi) / float(span)
            hw = int(round(hw_hi + (hw_lo - hw_hi) * f))
            for x in range(cx - hw, cx + hw + 1):
                col = body_c if top_face else body_d
                if x <= cx - hw + 1:
                    col = body_d if top_face else body_c   # lit north-west
                elif x >= cx + hw - 1:
                    col = body_dd                          # shaded east
                c.set(x, y, col)
            for yy in range(y, oy + 1):                    # skirt to ground
                for x in range(cx - hw, cx + hw + 1):
                    if c.px[x, yy][3] == 0:
                        c.set(x, yy, body_dd if x >= cx + hw - 1 else body_d)

    y = oy - h_face                   # the top of the near end face
    y_low_far = y - d_low
    y_rake_far = y_low_far - d_rake - (h_roof - h_face)
    y_roof_far = y_rake_far - d_roof
    _band(y_roof_far, y_rake_far, hw_glass, hw_glass, True)        # roof
    _band(y_rake_far, y_low_far, hw_glass, hw_body, True)          # glass rake
    _band(y_low_far, y, hw_body, hw_body, True)                    # hood/trunk
    for x in range(cx - hw_glass + 1, cx + hw_glass):              # the glass
        for yy in range(y_rake_far + 1, y_low_far):
            c.set(x, yy, glass if x < cx else glass_d)
        c.set(x, y_rake_far, glass_d)
    for x in range(cx - hw_glass + 2, cx + hw_glass - 1):          # roof crown
        c.set(x, y_roof_far + 1, body_c)
    # the near END FACE: the only vertical face the camera can see
    face_top = oy - h_face
    for x in range(cx - hw_body, cx + hw_body + 1):
        for y in range(face_top, oy + 1):
            col = body_dd
            if x <= cx - hw_body + 1:
                col = body_d                            # lit near corner
            elif x >= cx + hw_body - 1:
                col = C("10141f")                       # shaded near corner
            c.set(x, y, col)
        c.set(x, face_top, body_d)    # lit rim along the top of the face
    lights_px: list[tuple[int, int]] = []
    lamp_y = face_top + 2
    if toward:
        for k in range(4):            # headlights, both corners
            c.set(cx - hw_body + 1 + k, lamp_y, C("e8c170"))
            c.set(cx + hw_body - 1 - k, lamp_y, C("e8c170"))
            c.set(cx - hw_body + 1 + k, lamp_y + 1, C("de9e41"))
            c.set(cx + hw_body - 1 - k, lamp_y + 1, C("de9e41"))
        lights_px = [(cx - hw_body + 2, lamp_y), (cx + hw_body - 2, lamp_y)]
        for gy in (lamp_y + 3, lamp_y + 4):             # grille slits
            for x in range(cx - hw_body + 6, cx + hw_body - 5):
                c.set(x, gy, C("151d28"))
        c.set(cx, lamp_y + 2, C("819796"))              # badge
    else:
        for k in range(4):            # tail lights
            c.set(cx - hw_body + 1 + k, lamp_y, C("a53030"))
            c.set(cx + hw_body - 1 - k, lamp_y, C("a53030"))
            c.set(cx - hw_body + 1 + k, lamp_y + 1, C("752438"))
            c.set(cx + hw_body - 1 - k, lamp_y + 1, C("752438"))
        lights_px = [(cx - hw_body + 2, lamp_y), (cx + hw_body - 2, lamp_y)]
        for x in range(cx - hw_body + 4, cx + hw_body - 3):   # trunk shutline
            c.set(x, lamp_y + 3, C("10141f"))
        c.set(cx, lamp_y + 5, C("819796"))              # handle
    for x in range(cx - hw_body + 1, cx + hw_body):     # bumper strip
        c.set(x, oy - 1, C("202e37"))
        c.set(x, oy, C("151d28"))
    for side in (-1, 1):                                # wheels at the corners
        wx = cx + side * (hw_body + 1)
        for dy in range(-4, 1):
            c.set(wx, oy + dy, C("10141f"))
            c.set(wx - side, oy + dy, C("10141f") if dy > -4 else C("202e37"))
        c.set(wx, oy - 2, C("202e37"))
    if broken:
        for _ in range(rng.randint(6, 10)):
            rx = cx + rng.randrange(-hw_body + 1, hw_body - 1)
            ry = oy - rng.randrange(2, 24)
            c.set(rx, ry, C("884b2b") if rng.random() < 0.6 else C("602c2c"))
    if door_open:                     # a door swung out on the near flank
        for k in range(5):
            dy = oy - 10 - k
            for dx in range(0, 4):
                c.set(cx - hw_body - 2 - dx, dy, body_d if dx < 3 else body_dd)
    c.outline_auto()
    origin_full = (cx, oy)
    cropped, origin = crop_canvas(c, origin_full)
    lights_rel = [[px - origin_full[0], py - origin_full[1]] for (px, py) in lights_px]
    # ground footprint: the car's true width, foreshortened front-to-back
    # to match what the sprite shows (a deeper box would stop you before
    # the art touched anything)
    half_w = W / 2.0
    return cropped, origin, ["poly", [
        -half_w, -10.0, half_w, -10.0, half_w, 10.0, -half_w, 10.0]], \
        lights_rel


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
    # door_open is EXCLUDED from the seed: the enter/exit frame must be the
    # SAME vehicle down to its cargo and rust — a re-rolled pickup bed made
    # trucks flash a different color for the door beat (user report)
    rng = random.Random(f"{SEED}:vehicle:{kind}:{scheme}:{rev}:{broken}")
    palettes = [
        ("752438", "411d31", "241527"),   # oxblood
        ("577277", "394a50", "202e37"),   # gray
        ("25562e", "19332d", "10141f"),   # olive
        ("884b2b", "602c2c", "341c27"),   # rust
        ("3c5e8b", "253a5e", "172038"),   # steel blue
        ("ad7757", "7a4841", "4d2b32"),   # tan
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
    half_long = 42.0 if kind == "bus" else 29.0
    half_wide = 12.0 if kind == "bus" else 9.0
    return cropped, origin, _diag_poly(half_long, half_wide), lights_rel

def mirror_prop(prop: tuple) -> tuple:
    """Bake the horizontal mirror of a prop (origin re-anchored, colliders
    x-flipped when directional, light offsets x-flipped). Runtime stays
    transform-free."""
    canvas, origin, collider = prop[0], prop[1], prop[2]
    if collider is not None and collider[0] == "poly":
        flat = collider[1]
        flipped: list = []
        for i in range(0, len(flat), 2):
            flipped.append(-flat[i])
            flipped.append(flat[i + 1])
        collider = ["poly", flipped]
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
        return cropped, origin, ["circle", 5.5]

    if kind in ("oak", "autumn"):
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
        autumn = kind == "autumn"
        base_leaf = C("884b2b") if autumn else C("19332d")
        rim_leaf = C("da863e") if autumn else C("25562e")
        spark_leaf = C("de9e41") if autumn else C("468232")
        accent_leaf = C("cf573c") if autumn else C("25562e")
        under_leaf = C("602c2c") if autumn else C("10141f")
        for (x, y) in pts:
            col = base_leaf
            if (x - 1, y) not in pts or (x, y - 1) not in pts:
                col = rim_leaf if x < cx + lean else under_leaf
            elif rng.random() < 0.10:
                col = accent_leaf
            elif rng.random() < 0.05:
                col = spark_leaf    # bright leaf sparks
            elif (x, y + 1) not in pts:
                col = under_leaf    # dark under-rim
            c.set(x, y, col)
        c.outline_auto()
        cropped, origin = crop_canvas(c, (cx, feet + 1))
        return cropped, origin, ["circle", 5.5]

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
    return cropped, origin, ["circle", 4.0]

def draw_bush(rng: random.Random, variant: int) -> tuple[Canvas, tuple, list | None]:
    """A leafy mound the player can vanish into — no collider. Built as a
    MASS now (user: "they look flat"): lumpy crowns with lit and shaded
    sides, a dark under-skirt, and a crown rim that catches the sky —
    the angular-view illusion, not a front-view sticker."""
    w = rng.choice((40, 46, 52))
    h = w // 2 + rng.randint(14, 18)
    c = Canvas(w + 10, h + 12)
    cx = c.w // 2
    cy = h // 2 + 5
    pts: set = set()
    for dx in range(-w // 2, w // 2 + 1):
        e = 1.0 - (dx / (w / 2.0)) ** 2
        if e <= 0.0:
            continue
        half = h / 2.0 * (e ** 0.5) * rng.uniform(0.85, 1.1)
        for dy in range(int(-half), int(half) + 1):
            pts.add((cx + dx, cy + dy))
    skirt_y = cy + int(h * 0.30)
    for (x, y) in pts:                               # body + under-skirt
        c.set(x, y, C("10141f") if y >= skirt_y else C("19332d"))
    # lumpy crowns: every foliage mass gets a lit NW shoulder and a
    # shaded SE belly — the light model is what sells the volume
    lumps = []
    for i in range(rng.randint(3, 4)):
        lumps.append((cx + rng.randint(-w // 3, w // 3),
                      cy - h // 6 + rng.randint(-h // 6, h // 8),
                      rng.randint(w // 6, w // 4)))
    for (lx, ly, lr) in lumps:
        ry = max(2, lr // 2)
        for dy in range(-ry, ry + 1):
            for dx in range(-lr, lr + 1):
                if (dx / float(lr)) ** 2 + (dy / float(ry)) ** 2 > 1.0:
                    continue
                p = (lx + dx, ly + dy)
                if p not in pts or p[1] >= skirt_y:
                    continue
                if dx - dy * 2 < -lr // 3:
                    c.set(p[0], p[1], C("25562e"))   # lit toward the sky
                elif dy > ry // 3:
                    c.set(p[0], p[1], C("151d28"))   # its own under-shade
        for k in range(rng.randint(2, 4)):           # bright shoulder caps
            hx = lx - lr // 3 + rng.randint(-2, 2) + k
            hy = ly - ry + rng.randint(0, 2)
            if (hx, hy) in pts and hy < skirt_y:
                c.set(hx, hy, C("468232"))
                if (hx + 1, hy) in pts:
                    c.set(hx + 1, hy, C("25562e"))
    for (x, y) in pts:                               # crown rim, sky-lit
        if (x, y - 1) not in pts and y < cy:
            c.set(x, y, C("25562e"))
    if variant == 2:                                 # the berried one
        for i in range(5):
            bx = cx + rng.randint(-w // 3, w // 3)
            by = cy + rng.randint(-h // 4, 0)
            if (bx, by) in pts:
                c.set(bx, by, C("a53030"))
                if (bx + 1, by) in pts:
                    c.set(bx + 1, by, C("a53030"))
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
    """Street bench along the (2,1) axis, drawn as a BOX now (user: "i
    want them more 3d"): a real seat slab with a lit top face, a front
    face and an underside shadow, a wood backrest with a bright top edge,
    and legs with lit/shade sides."""
    c = Canvas(56, 62)
    ox, oy = 4, 30
    ln = 32          # along the bench, on the (2,1) axis
    depth = 12       # ACROSS it, on the (2,-1) axis — the bit you sit on
    slab = 3         # seat thickness
    back_h = 15      # backrest above the seat's far edge
    leg_h = 9
    wood, wood_dk, wood_lt = C("602c2c"), C("341c27"), C("884b2b")
    steel, steel_dk = C("394a50"), C("202e37")

    def pt(i: int, d: int) -> tuple:
        # run i along (2,1), depth d across on (2,-1)
        return ox + i + d, oy + i // 2 - d // 2

    gap_lo, gap_hi = (12, 20) if broken else (-1, -1)

    # THE SEAT, as a real surface: a parallelogram top face with slats
    # running along the bench. Without this the bench had a one-pixel seat
    # line and read as a fence going up, with nothing to sit on (user).
    #
    # Filled per SCREEN COLUMN, not by stepping i and d. Both axes move a
    # half pixel vertically, so integer stepping lands two (i, d) pairs on
    # the same pixel and leaves the one below empty — the first cut came
    # out stippled with holes, which is dot noise and banned.
    for k in range(ln + depth - 1):
        d_lo = max(0, k - (ln - 1))
        d_hi = min(k, depth - 1)
        if d_lo > d_hi:
            continue
        i_here = k - d_hi
        if gap_lo < i_here < gap_hi and gap_lo < k - d_lo < gap_hi:
            continue
        ys = [(k - d) // 2 - d // 2 for d in range(d_lo, d_hi + 1)]
        y0, y1 = min(ys), max(ys)
        for y in range(y0, y1 + 1):
            rel = y - y0                      # 0 is the far edge
            slat = rel % 4 == 3               # slat joints run lengthwise
            col = wood_dk if slat else (wood_lt if rel < 4 else wood)
            c.set(ox + k, oy + y, col)
    # the seat's near edge: front face and the shadow under it
    for i in range(ln):
        if gap_lo < i < gap_hi:
            if i in (gap_lo + 1, gap_hi - 1):          # splintered ends
                x, y = pt(i, 0)
                c.set(x, y, wood_dk)
            continue
        x, y = pt(i, 0)
        for k in range(1, slab + 1):
            c.set(x, y + k, wood if k < slab else wood_dk)
        c.set(x, y + slab + 1, C("241527"))
    # ...and its far edge, so the slab has thickness on both sides
    for i in range(ln):
        x, y = pt(i, depth - 1)
        c.set(x, y + 1, wood_dk)

    # THE BACKREST: two slats standing off the far edge, lit along the top
    for i in range(ln):
        x, y = pt(i, depth - 1)
        for k in range(2, back_h):
            if k in (7, 8):                   # the gap between the slats
                continue
            col = wood_lt if k in (back_h - 1, 9) else wood
            c.set(x, y - k, col)
        c.set(x, y - back_h, wood_dk)

    # LEGS at both ends, front pair and back pair
    for i in (2, ln - 3):
        for d in (1, depth - 2):
            x, y = pt(i, d)
            lean = 1 if (broken and i > 4 and d == 1) else 0
            top = y + (slab + 1 if d == 1 else 1)
            for k in range(leg_h):
                dx = (k // 5) * lean
                c.set(x + dx, top + k, steel)
                c.set(x + dx + 1, top + k, steel_dk)
    c.outline_auto()
    cr, orr = crop_canvas(c, (ox + ln // 2 + depth // 2,
                              oy + ln // 4 - depth // 4 + slab + leg_h))
    return cr, orr, ["diamond", 15.0, 8.0]


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


def make_gem_cracked(stage: int) -> tuple[Canvas, tuple, list | None]:
    """The sapphire with cracks spreading (stage 0..2) — the splash's
    shatter build-up. Same silhouette as the whole gem."""
    base, origin, _ = make_studio_gem()
    c = base
    rng = random.Random(f"{SEED}:gemcrack:{stage}")
    for crack in range(2 + stage * 2):
        x = 8 + rng.randrange(14)
        y = 5 + rng.randrange(4)
        for k in range(4 + stage * 3):
            if 0 <= x < c.w and 0 <= y < c.h and c.px[x, y][3] > 0:
                c.set(x, y, C("ebede9") if k % 3 == 0 else C("172038"))
            x += rng.choice((-1, 0, 1))
            y += 1 if rng.random() < 0.75 else 0
    return c, origin, None

def make_gem_shards() -> list:
    """Flying fragments for the shatter beat."""
    out = []
    for i in range(6):
        rng = random.Random(f"{SEED}:shard:{i}")
        w = rng.randint(4, 7)
        h = rng.randint(4, 6)
        img = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
        px = img.load()
        for y in range(h):
            for x in range(w):
                if abs(x - w // 2) + abs(y - h // 2) <= max(w, h) // 2 + 1:
                    cols = [(115, 190, 211, 255), (79, 143, 186, 255),
                            (164, 221, 219, 255), (60, 94, 139, 255)]
                    px[x + 1, y + 1] = cols[(x + y + i) % 4]
        out.append(img)
    return out

def make_signal_core() -> tuple[Canvas, tuple, list | None]:
    """What was inside the sapphire: the SIGNAL — a bright beacon mote with
    a whip antenna, the studio's namesake."""
    c = Canvas(18, 22)
    cx = 9
    for r_, col in ((5, "253a5e"), (4, "3c5e8b"), (3, "4f8fba"),
                    (2, "73bed3"), (1, "a4dddb")):
        for y in range(-r_, r_ + 1):
            for x in range(-r_, r_ + 1):
                if x * x + y * y <= r_ * r_:
                    c.set(cx + x, 13 + y, C(col))
    c.set(cx, 13, C("ebede9"))
    for y in range(3, 8):                       # the whip
        c.set(cx, y, C("a4dddb"))
    c.set(cx, 2, C("ebede9"))
    c.set(cx - 1, 9, C("73bed3"))
    c.set(cx + 1, 9, C("73bed3"))
    c.outline_auto()
    return c, (cx, 18), None

def make_studio_tag() -> Image.Image:
    """'studio' — the small line under the wordmark."""
    return _render_word("studio", C("577277"), C("394a50"))

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


# the eight character facings, in sheet order E,SE,S,SW,W,NW,N,NE. These are
# exact 45 degree steps in SCREEN space (player.gd derives facing_angle the
# same way), so muzzle art can be drawn straight down them.
GUN_DIRS = ["e", "se", "s", "sw", "w", "nw", "n", "ne"]


def make_muzzle_flash(dir_index: int, frame: int) -> Image.Image:
    """Muzzle flash for one facing (effect: alpha-graded, not palette-locked).

    ONE SPRITE PER FACING because runtime rotation is banned — it breaks the
    pixel grid. Frame 0 is the full bloom, frame 1 the decay."""
    size = 24
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx = cy = size // 2
    ang = math.radians(45.0 * dir_index)
    dx, dy = math.cos(ang), math.sin(ang)
    sx, sy = -dy, dx                      # across the barrel
    core = C("ebede9")
    warm = C("e8c170")
    deep = C("de9e41")
    rng = random.Random(f"{SEED}:muzzle:{dir_index}:{frame}")
    reach = 9.0 if frame == 0 else 5.0
    spread = 2.6 if frame == 0 else 1.6
    # the cone: brightest at the barrel, widening and cooling as it goes
    steps = int(reach * 2)
    for i in range(steps + 1):
        t = i / float(steps)
        along = t * reach
        half = spread * (0.35 + t * 0.65)
        j = -int(half)
        while j <= int(half):
            x = int(round(cx + dx * along + sx * j))
            y = int(round(cy + dy * along + sy * j))
            if not (0 < x < size - 1 and 0 < y < size - 1):
                j += 1
                continue
            edge = abs(j) >= max(int(half), 1)
            if t < 0.35 and not edge:
                col = core + (255,)
            elif edge:
                col = deep + (150 if frame == 0 else 90,)
            else:
                col = warm + (225 if frame == 0 else 150,)
            px[x, y] = col
            j += 1
    # a couple of stray sparks thrown clear of the cone
    for _ in range(rng.randint(2, 4) if frame == 0 else rng.randint(1, 2)):
        d = reach * rng.uniform(0.7, 1.25)
        off = rng.uniform(-2.5, 2.5)
        x = int(round(cx + dx * d + sx * off))
        y = int(round(cy + dy * d + sy * off))
        if 0 < x < size - 1 and 0 < y < size - 1:
            px[x, y] = warm + (200,)
    return img


def make_tracer() -> Image.Image:
    """The player's round in flight — smaller and warmer than the sniper's,
    so the two are never confused (effect: alpha-graded)."""
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    px = img.load()
    core = C("ebede9")
    warm = C("e8c170")
    px[1, 1] = core + (255,)
    px[2, 1] = core + (255,)
    px[1, 2] = warm + (220,)
    px[2, 2] = warm + (220,)
    for p in ((0, 1), (3, 1), (1, 0), (1, 3)):
        px[p] = warm + (90,)
    return img


def make_impact_frames() -> list:
    """Three frames of grit kicked off whatever the round hits. Chips and
    dust, no dot noise — each frame is a handful of solid flecks that thin
    out as it settles (effect: alpha-graded)."""
    out = []
    for f in range(3):
        rng = random.Random(f"{SEED}:impact:{f}")
        size = 14
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = img.load()
        cx = cy = size // 2
        grey = [C("a8b5b2"), C("819796"), C("577277")]
        fade = [255, 190, 110][f]
        for _ in range(rng.randint(5, 7) - f):
            ang = rng.uniform(0.0, math.tau)
            dist = (1.4 + f * 1.9) * rng.uniform(0.6, 1.4)
            x = int(round(cx + math.cos(ang) * dist))
            y = int(round(cy + math.sin(ang) * dist * 0.6))   # iso squash
            if 0 < x < size - 1 and 0 < y < size - 1:
                px[x, y] = grey[rng.randrange(3)] + (fade,)
        if f == 0:
            px[cx, cy] = C("ebede9") + (255,)
        out.append(img)
    return out


DOOR_FRAMES = 4     # frames per swing; the strip holds TWO swings
DOOR_LEAF = 20      # leaf length along the edge, px
DOOR_H = 34         # leaf height
DOOR_HINGE = (22, 50)       # hinge inside a frame; sized so no swing clips
DOOR_FRAME_SIZE = (54, 68)

# the open-state colliders, keyed by prop name. The GENERATOR knows where the
# swung leaf ends up, so it says so — the game must never re-derive it (a
# hand-rolled guess put the panel on the wrong side of x doors for a whole
# release, and you could stroll through every open south door).
DOOR_COLLIDERS: dict[str, dict] = {}

# prop name -> "car" | "truck", published so the map can label its dots
VEHICLE_KINDS: dict[str, str] = {}

# closed / open-inward / open-outward unit step per axis, in screen px per px
# of leaf run. 'x' fits south (yp) walls, 'y' fits east (xp) walls. A door
# swings AWAY from whoever opens it (user call), so every door needs BOTH
# perpendiculars drawn: inward is toward the room, outward is the street.
_DOOR_DIRS = {
    "x": ((1.0, 0.5), (1.0, -0.5), (-1.0, 0.5)),
    "y": ((1.0, -0.5), (-1.0, -0.5), (1.0, 0.5)),
}


def _door_leaf_vec(axis: str, t: float, outward: bool = False) -> tuple[float, float]:
    """Screen offset from hinge to the leaf's free end, t = 0 shut, 1 open.
    The panel turns 90 degrees in the GROUND plane, so this is NOT a lerp of
    the two end states: projected into iso a door standing at 45 degrees is
    WIDER on screen than either the shut or the fully open one. Lerping the
    step (what the first cut did) under-samples the middle frames — the east
    doors lost most of their leaf and all of their handle."""
    closed, in_dir, out_dir = _DOOR_DIRS[axis]
    opened = out_dir if outward else in_dir
    ang = math.radians(90.0 * t)
    cs, sn = math.cos(ang), math.sin(ang)
    return (DOOR_LEAF * (cs * closed[0] + sn * opened[0]),
            DOOR_LEAF * (cs * closed[1] + sn * opened[1]))


def make_door_strip(kind: str, axis: str) -> tuple[Canvas, tuple, list]:
    """Interactive door: a DOOR_FRAMES-frame swing strip. Frame 0 = closed,
    flush IN the wall plane (nothing pokes through the wall any more); last
    frame = swung fully inward, a full quarter turn clear of the opening so
    there is a real gap beside a real panel. Static jamb boards fill the edge
    beside the leaf on every frame. axis 'x' fits south (yp) walls, 'y' fits
    east (xp). Colliders: the shut leaf across the whole edge, the swung leaf
    where it actually stands, and the two jamb stubs (always solid)."""
    base, dark = (C("7a4841"), C("4d2b32")) if kind == "wood" \
        else (C("577277"), C("394a50"))
    frame_w, frame_h = DOOR_FRAME_SIZE
    hx, hy = DOOR_HINGE
    # TWO swings in one strip: 0..3 open inward, 4..7 open outward. The game
    # picks the half that swings away from whoever is opening it.
    strip = Canvas(frame_w * DOOR_FRAMES * 2, frame_h)
    edge_dy = 0.5 if axis == "x" else -0.5
    for f in range(DOOR_FRAMES * 2):
        outward = f >= DOOR_FRAMES
        c = Canvas(frame_w, frame_h)
        ex, ey = _door_leaf_vec(axis,
            float(f % DOOR_FRAMES) / float(DOOR_FRAMES - 1), outward)

        def draw_leaf() -> None:
            # sampled along its SCREEN run, not per leaf-px, so no frame
            # comes out gappy when the panel foreshortens
            steps = max(int(round(max(abs(ex), abs(ey)))), 1)
            for i in range(steps + 1):
                u = i / float(steps)
                x = hx + round(ex * u)
                by = hy + round(ey * u)
                plank = int(u * DOOR_LEAF)      # planks compress as it turns
                for y in range(by - DOOR_H, by + 1):
                    col = base
                    if kind == "wood" and plank % 5 == 4:
                        col = dark
                    if kind == "metal" and (y - (by - DOOR_H)) % 6 == 5:
                        col = dark
                    c.set(x, y, col)
                c.set(x, by - DOOR_H, dark)  # top edge
            # handle near the free end; the panel is never edge-on, so this
            # never lands on nothing
            c.set(hx + round(ex * 0.85), hy + round(ey * 0.85) - DOOR_H // 2,
                  C("10141f"))

        def draw_jambs() -> None:
            # the fixed 6 px of edge either side of the leaf
            for j in list(range(-6, 0)) + list(range(DOOR_LEAF, DOOR_LEAF + 6)):
                x = hx + j
                by = hy + round(j * edge_dy)
                for y in range(by - DOOR_H - 2, by + 1):
                    c.set(x, y, dark if (y - by) % 5 else C("341c27"))

        # WHO OCCLUDES WHO depends on which way it swings. Inward, the leaf
        # travels away from the camera and the wall stands in front of it.
        # Outward, it swings toward the camera and must cover the jamb —
        # drawn the wrong way round the open door looks cut in half by the
        # board beside it (user report on the first cut of the two-way swing).
        if outward:
            draw_jambs()
            draw_leaf()
        else:
            draw_leaf()
            draw_jambs()
        c.outline_auto()
        _paste_canvas(strip, c, f * frame_w, 0)
    # origin: edge midpoint at the leaf base (matches wall-segment anchoring)
    sx, sy = _door_leaf_vec(axis, 0.0)
    origin = (hx + round(sx * 0.5), hy + round(sy * 0.5))
    # n is WALL thickness (the shut leaf is part of the wall line); n_open is
    # a door PANEL, which is thinner. It matters: at wall thickness the swung
    # leaf reaches across its own doorway and seals the middle of the opening,
    # leaving a 4 px corridor to squeeze through.
    if axis == "x":
        a, b = (-16.0, -8.0), (16.0, 8.0)
        n = (-2.4, 4.8)
        n_open = (1.2, 2.4)
    else:
        a, b = (-16.0, 8.0), (16.0, -8.0)
        n = (2.4, 4.8)
        n_open = (1.2, -2.4)

    def quad(p, q, nrm):
        return [p[0] - nrm[0], p[1] - nrm[1], q[0] - nrm[0], q[1] - nrm[1],
                q[0] + nrm[0], q[1] + nrm[1], p[0] + nrm[0], p[1] + nrm[1]]

    # everything below is relative to the origin, same as the sprite offset
    hinge = (-sx * 0.5, -sy * 0.5)
    shut_end = (hinge[0] + sx, hinge[1] + sy)
    ox, oy = _door_leaf_vec(axis, 1.0)
    ux, uy = _door_leaf_vec(axis, 1.0, True)
    # the outward panel is the mirror of the inward one, so its thickness
    # runs the other way across the leaf
    n_out = (n_open[0], -n_open[1]) if axis == "x" else (-n_open[0], n_open[1])
    DOOR_COLLIDERS[f"door_{kind}_{axis}"] = {
        "open": ["poly", quad(hinge, (hinge[0] + ox, hinge[1] + oy), n_open)],
        "open_out": ["poly", quad(hinge, (hinge[0] + ux, hinge[1] + uy), n_out)],
        # the jambs are drawn solid, so they ARE solid — otherwise an open
        # door lets you walk through the boards beside the opening
        "jambs": [["poly", quad(a, hinge, n)], ["poly", quad(shut_end, b, n)]],
    }
    return strip, origin, ["poly", quad(a, b, n)]

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
# v0.3.1: the POI set — stairs/beds for two-story houses, buses for the
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

def make_locomotive() -> tuple[Canvas, tuple, list]:
    """The night freight's engine — the one train in transit that still
    runs, and it is meant to be unmistakable next to the dead stock in
    the yard: longer than a boxcar, taller at the cab, black with warm
    lit windows, a headlight, and a stack. Same (2,1) projection family
    as everything else on rails."""
    rng = random.Random(f"{SEED}:locomotive")
    body_c, body_d, body_dd = C("394a50"), C("202e37"), C("151d28")
    L = 72
    clear = 6
    ox, oy = 6, 52
    c = Canvas(120, 104)
    # profile: long low hood at the front, tall cab toward the rear
    prof = []
    for i in range(L):
        f = i / float(L - 1)
        if f < 0.06:
            h = 20
        elif f < 0.52:
            h = 26                    # the hood
        elif f < 0.58:
            h = 26 + int((f - 0.52) / 0.06 * 12)
        elif f < 0.90:
            h = 38                    # the cab
        else:
            h = 30
        prof.append(h)
    for i in range(L):                            # side face
        x = ox + i
        base = oy + i // 2
        for y in range(base - clear - prof[i], base - clear + 1):
            col = body_d if i % 5 else body_dd    # panel ribs
            if y > base - clear - 5:
                col = body_dd                     # running board shadow
            c.set(x, y, col)
    prev_top = None
    for i in range(L):                            # roof plane
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i]
        span = 1 if prev_top is None else abs(prev_top - top) + 1
        rising = prev_top is not None and prev_top > top
        for t in range(1, ROOF_DEPTH + 1):
            col = body_c if t < ROOF_DEPTH else body_dd
            for k in range(span):
                yy = top + (k if rising else -k)
                c.set(x + t, yy - (t + 1) // 2, col)
                c.set(x + t, yy - t // 2, col)
        prev_top = top
    # cab windows: warm, because somebody is driving it
    for i in range(int(L * 0.60), int(L * 0.86)):
        x = ox + i
        base = oy + i // 2
        top = base - clear - prof[i]
        if (i - int(L * 0.60)) % 9 < 6:
            for y in range(top + 5, top + 13):
                c.set(x, y, C("e8c170") if y < top + 9 else C("de9e41"))
    for i in range(6, int(L * 0.50)):             # hood louvres
        if i % 6 < 2:
            x = ox + i
            base = oy + i // 2
            for y in range(base - clear - prof[i] + 6, base - clear - 8):
                c.set(x, y, body_dd)
    # a stripe down the flank so it reads at a distance
    for i in range(3, L - 3):
        c.set(ox + i, oy + i // 2 - clear - 8, C("de9e41"))
    # THE NEAR END FACE — the cab's back wall. This is the exact bug the
    # car saga was about (CLAUDE.md): an end drawn as a stub continuing
    # LENGTHWISE instead of a full-width wall across the body's iso width
    # axis leaves the vehicle looking sawn off. It has to span the same
    # ROOF_DEPTH the roof plane does.
    cap_h = prof[L - 1]
    wall_x0 = ox + L - 1
    wall_top0 = oy + (L - 1) // 2 - clear - cap_h
    wall_bot0 = oy + (L - 1) // 2 - clear
    for t in range(1, ROOF_DEPTH + 1):
        x = wall_x0 + t
        rise = t // 2
        for y in range(wall_top0 - rise, wall_bot0 - rise + 1):
            c.set(x, y, body_dd)
        c.set(x, wall_top0 - rise, body_d)             # lit rim along the top
        c.set(x, wall_bot0 - rise, C("202e37"))        # sill
        c.set(x, wall_bot0 - rise - 1, C("202e37"))
    for t in (2, 3, ROOF_DEPTH - 3, ROOF_DEPTH - 2):   # marker lamps
        c.set(wall_x0 + t, wall_top0 - t // 2 + 4, C("a53030"))
    for t in range(5, ROOF_DEPTH - 4):                 # the back window
        c.set(wall_x0 + t, wall_top0 - t // 2 + 7, C("253a5e"))
        c.set(wall_x0 + t, wall_top0 - t // 2 + 8, C("253a5e"))
    # wrap the side's last column into the cap so the corner reads solid
    for y in range(wall_top0 + 1, wall_bot0):
        c.set(wall_x0, y, body_dd)
    # the FAR end (the nose): closes the silhouette, carries the headlight
    far_h = prof[0]
    for t in range(1, 3):
        x = ox - t
        base = oy - (t + 1) // 2
        far_top = base - clear - far_h + (t + 1) // 2
        for y in range(far_top, base - clear + 1):
            c.set(x, y, body_dd)
        c.set(x, base - clear, C("202e37"))            # coupler plate
    for k in range(3):                                 # the headlight, burning
        c.set(ox - 2 + k, oy - clear - far_h + 4, C("ebede9"))
        c.set(ox - 2 + k, oy - clear - far_h + 5, C("e8c170"))
    # the stack, and the smoke plate behind it
    stack_x = ox + int(L * 0.18)
    for k in range(7):
        c.set(stack_x, oy + stack_x // 2 - ox // 2 - clear - prof[10] - 6 - k,
              C("202e37"))
        c.set(stack_x + 1, oy + stack_x // 2 - ox // 2 - clear - prof[10] - 6 - k,
              C("151d28"))
    for wf in (10, 30, 52, 64):                   # bogies
        cxw = ox + wf + 3
        cyw = oy + (wf + 3) // 2 - 2
        for dy in range(-2, 3):
            for dx in range(-4, 5):
                if dx * dx + dy * dy * 2 <= 14:
                    c.set(cxw + dx, cyw + dy, (0, 0, 0, 0))
        for dy in range(-3, 3):
            for dx in range(-4, 5):
                d = dx * dx + dy * dy * 2
                if d <= 18:
                    c.set(cxw + dx, cyw + dy, C("10141f") if d > 6 else C("202e37"))
        c.set(cxw, cyw, C("577277"))
    for _ in range(rng.randint(3, 5)):            # soot and wear
        c.set(ox + rng.randrange(4, L - 4), oy + rng.randrange(6, 20),
              C("151d28"))
    c.outline_auto()
    origin_full = (ox + (L + 3) // 2 + ROOF_DEPTH // 2,
                   oy + (L + 3) // 4 - ROOF_DEPTH // 4)
    cropped, origin = crop_canvas(c, origin_full)
    return cropped, origin, ["poly", [
        -44.0, -10.0, 44.0, 10.0, 44.0, 20.0, -44.0, 0.0]]


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
    return cropped, origin, _diag_poly(38.0, 12.0)

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


# ------------------------------------------------ scrapyard + street set ----
# v0.3.2: the scrapyard's machines, the gallery's art, the street's boxes,
# and the houses' power. Same rules: iso, Apollo, 3D-read, quiet wear.

def make_forklift(variant: int) -> tuple[Canvas, tuple, list]:
    """Yard forklift: boxy body, roll cage, mast with the forks raised
    (variant 0) or dropped (1). Small, dented, honest."""
    rng = random.Random(f"{SEED}:forklift:{variant}")
    c = Canvas(56, 50)
    bx, by = 18, 26
    # body: a low prism, warning-yellow with grime
    bottoms = iso_prism(c, bx, by, 16, 8, 8, C("de9e41"), C("be772b"), C("602c2c"))
    for x in range(16):
        b = bottoms[x]
        if x % 5 == 2:
            c.set(bx + x, b + 3, C("602c2c"))          # grime streaks
    # counterweight block at the rear (SE end)
    for x in range(12, 16):
        b = bottoms[x]
        for y in range(b + 1, b + 9):
            c.set(bx + x, y, C("341c27") if x > 13 else C("602c2c"))
    # roll cage: four posts + a flat canopy diamond
    for k in range(10):
        c.set(bx + 3, by + 2 - k, C("341c27"))
        c.set(bx + 12, by + 6 - k, C("341c27"))
        c.set(bx + 8, by - k, C("241527"))
    rows = small_diamond_rows(12, 6)
    for i, (x0, x1) in enumerate(rows):                # canopy
        for x in range(x0, x1 + 1):
            c.set(bx + 1 + x, by - 10 + i, C("202e37") if (x + i) % 2 else C("341c27"))
    # the mast at the NW end: twin rails
    for k in range(16):
        c.set(bx - 2, by + 1 - k, C("394a50"))
        c.set(bx - 1, by + 1 - k, C("577277"))
    # forks: two tines reaching NW, raised or dropped
    fork_y = (by - 11) if variant == 0 else (by + 4)
    for f in range(8):
        c.set(bx - 3 - f, fork_y + (f + 1) // 2, C("819796"))
        c.set(bx - 3 - f, fork_y + (f + 1) // 2 + 2, C("577277"))
    for wf in (2, 12):                                 # wheels
        cxw = bx + wf
        cyw = by + wf // 2 + 8
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    c.set(cxw + dx, cyw + dy,
                          C("10141f") if dx * dx + dy * dy > 1 else C("202e37"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (bx + 8, by + 12))
    return cr, orr, ["diamond", 14.0, 7.0]

def make_crane() -> tuple[Canvas, tuple, list]:
    """THE crane: crawler base, cab, a long lattice boom over the yard and
    a hook that hasn't lifted anything in years."""
    rng = random.Random(f"{SEED}:crane")
    c = Canvas(120, 114)
    bx, by = 18, 84
    iso_prism(c, bx, by, 28, 14, 8, C("202e37"), C("394a50"), C("151d28"))
    for x in range(28):                        # crawler treads
        b = by + 14 + 8
        c.set(bx + x, b - 14 + (x // 2) % 2, C("10141f"))
    iso_prism(c, bx + 10, by - 10, 12, 6, 9, C("de9e41"), C("be772b"), C("602c2c"))
    for wy in range(3):                        # cab glass
        for wx in range(4):
            c.set(bx + 13 + wx, by - 7 + wy, C("3c5e8b") if wy else C("73bed3"))
    # the lattice boom: two chords climbing up-right with X bracing
    x0, y0 = bx + 18, by - 12
    length = 62
    for s in range(length):
        x = x0 + s
        y = y0 - int(s * 0.62)
        c.set(x, y, C("577277"))
        c.set(x, y + 4 + (2 if s < 40 else 1), C("577277"))
        if s % 6 == 0:
            for k in range(5):
                c.set(x, y + k, C("394a50"))
        if s % 11 == 0 and s > 4:              # rust bites
            c.set(x, y, C("884b2b"))
    tip_x, tip_y = x0 + length - 1, y0 - int((length - 1) * 0.62)
    for k in range(26):                        # the cable
        c.set(tip_x - 1, tip_y + 3 + k, C("341c27") if k % 2 else C("241527"))
    for hy in range(4):                        # hook block
        for hx in range(3):
            c.set(tip_x - 2 + hx, tip_y + 29 + hy, C("de9e41") if hy < 2 else C("202e37"))
    c.set(tip_x - 1, tip_y + 34, C("819796"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (bx + 14, by + 20))
    return cr, orr, ["diamond", 17.0, 9.0]

def make_vending(variant: int) -> tuple[Canvas, tuple, list]:
    """Street vending machine, long dead: brand band, dark glass with the
    last products still racked, coin slot."""
    rng = random.Random(f"{SEED}:vending:{variant}")
    brand = C("a53030") if variant == 0 else C("4f8fba")
    brand_d = C("752438") if variant == 0 else C("253a5e")
    c = Canvas(30, 42)
    bottoms = iso_prism(c, 4, 8, 16, 8, 24, C("394a50"), C("577277"), C("202e37"))
    for x in range(16):                        # face: brand band top
        b = bottoms[x]
        for y in range(b + 1, b + 6):
            if x < 8:
                c.set(4 + x, y, brand if y > b + 1 else brand_d)
    for x in range(1, 7):                      # glass window (lit face only)
        b = bottoms[x]
        for y in range(b + 7, b + 17):
            col = C("151d28")
            row = (y - b - 7) // 3
            if (y - b - 7) % 3 == 2 and 0 < x < 6:
                col = [C("cf573c"), C("a8ca58"), C("73bed3")][row % 3]  # products
            c.set(4 + x, y, col)
        c.set(4 + x, b + 17, C("819796"))
    c.set(11, bottoms[7] + 9, C("e8c170"))     # coin slot
    c.set(11, bottoms[7] + 10, C("341c27"))
    c.outline_auto()
    return c, (12, 38), ["diamond", 9.0, 5.0]

def make_newsbox(variant: int) -> tuple[Canvas, tuple, list]:
    """Newspaper box on stub legs, the news six years stale."""
    body = C("cf573c") if variant == 0 else C("3c5e8b")
    body_d = C("752438") if variant == 0 else C("253a5e")
    c = Canvas(22, 30)
    bottoms = iso_prism(c, 4, 6, 12, 6, 11, body, body, body_d)
    for x in range(1, 6):                      # window with the last stack
        b = bottoms[x]
        for y in range(b + 2, b + 7):
            c.set(4 + x, y, C("151d28") if y > b + 4 else C("c7cfcc"))
    for lx in (5, 13):                         # legs
        for k in range(3):
            c.set(lx, 6 + 6 + 11 + k + 1, C("202e37"))
    c.outline_auto()
    return c, (10, 26), ["diamond", 7.0, 4.0]

def make_graffiti_wall(variant: int) -> tuple[Canvas, tuple, list]:
    """A free-standing slab the district uses as a canvas: bubbly tag
    shapes, highlight sweeps, drips. The gallery's whole point."""
    rng = random.Random(f"{SEED}:graffiti:{variant}")
    c = Canvas(52, 58)
    ox, oy = 8, 34
    for i in range(36):                        # the slab (x-axis face)
        x = ox + i
        fy_base = oy + (-8 + i // 2) + 8
        for k in range(22):
            y = fy_base - k
            col = CONC_BASE if (i + k) % 9 else CONC_D1
            c.set(x, y, col)
        c.set(x, fy_base - 22, CONC_L1)        # cap
        c.set(x, fy_base - 23, CONC_L2 if i % 2 else CONC_L1)
    palettes = [
        (C("a23e8c"), C("c65197"), C("df84a5")),
        (C("4f8fba"), C("73bed3"), C("a4dddb")),
        (C("75a743"), C("a8ca58"), C("d0da91")),
    ]
    base_col, mid, lite = palettes[variant % 3]
    # the tag: fat overlapping blobs sweeping across the face
    cx0 = ox + 6 + rng.randrange(4)
    for b in range(rng.randint(3, 4)):
        bx = cx0 + b * rng.randint(6, 8)
        byy = oy - 6 - rng.randint(0, 4) + (bx - ox) // 2
        rx = rng.randint(3, 5)
        ry = rng.randint(4, 6)
        for dy in range(-ry, ry + 1):
            for dx in range(-rx, rx + 1):
                if (dx / rx) ** 2 + (dy / ry) ** 2 <= 1.0:
                    col = base_col
                    if dy < -ry // 3:
                        col = mid
                    if dx - dy > rx:
                        col = lite
                    px_, py_ = bx + dx, byy + dy
                    if ox <= px_ < ox + 36:
                        c.set(px_, py_, col)
    for d in range(rng.randint(3, 5)):         # drips
        dx_ = cx0 + rng.randrange(20)
        dy0 = oy - 2 + (dx_ - ox) // 2
        for k in range(rng.randint(2, 6)):
            c.set(dx_, dy0 + k, base_col)
    for s in range(rng.randint(2, 3)):         # white shine ticks
        sx = cx0 + rng.randrange(18)
        sy = oy - 10 + (sx - ox) // 2 - rng.randrange(4)
        c.set(sx, sy, C("ebede9"))
        c.set(sx + 1, sy + 1, C("ebede9"))
    c.outline_auto()
    return c, (ox + 18, oy + 9), ["poly",
        [-17.0, -9.0, 17.0, 8.0, 17.0, 12.0, -17.0, -5.0]]

def make_spray_cans(variant: int) -> tuple[Canvas, tuple, list | None]:
    """Spent spray cans where an artist crouched — every drop reads
    different (user: the two placements looked cloned): counts, cap
    colors, standing/tipped/crushed poses, an odd dried spill."""
    rng = random.Random(f"{SEED}:cans:{variant}")
    c = Canvas(32, 18)
    caps = [C("a23e8c"), C("73bed3"), C("a8ca58"), C("de9e41"),
            C("cf573c"), C("c65197")]
    rng.shuffle(caps)
    spots = [(6, 6), (13, 9), (21, 5), (25, 11), (9, 12)]
    rng.shuffle(spots)
    for i in range(rng.randint(2, 4)):
        x, y = spots[i]
        pose = rng.randrange(3)
        if pose == 0:                          # standing
            for k in range(5):
                c.set(x, y + k - 3, C("819796") if k else caps[i])
                c.set(x + 1, y + k - 3, C("577277"))
        elif pose == 1:                        # tipped
            d = rng.choice((-1, 1))
            for k in range(5):
                c.set(x + k * d, y, C("819796") if k > 0 else caps[i])
                c.set(x + k * d, y + 1, C("577277"))
        else:                                  # crushed flat
            for k in range(4):
                c.set(x + k, y, C("819796"))
                c.set(x + k, y + 1, C("577277"))
            c.set(x + rng.randrange(4), y - 1, caps[i])
    if variant % 2:                            # a dried spill by one can
        sx = min(spots[0][0] + 3, 25)
        sy = min(spots[0][1] + 2, 13)
        col = caps[rng.randrange(3)]
        for dx in range(-2, 3):
            for dy in range(-1, 2):
                if abs(dx) + abs(dy) < 3:
                    c.set(sx + dx, sy + dy, col)
    c.outline_auto()
    return c, (16, 14), None

def make_smoker_sheet() -> tuple[Canvas, tuple, list | None]:
    """The gallery regular: seated on a bench, spray can in one hand,
    cigarette in the other. 3 frames: resting, drag (ember hot), exhale.
    Drawn at PLAYER scale (user: "make him the size of me") — seated
    height ~30px against the 36px standing character."""
    frames = []
    for f in range(3):
        fc = Canvas(28, 36)
        cx = 13
        # legs seated: thighs forward, shins down to the ground
        for k in range(8):
            fc.set(cx - 2 + k, 22, C("241527"))
            fc.set(cx - 2 + k, 23, C("241527"))
        for k in range(9):
            fc.set(cx + 5, 24 + k, C("241527"))
            fc.set(cx + 6, 24 + k, C("10141f"))
        for bx in range(cx + 4, cx + 8):       # boots
            fc.set(bx, 33, C("151d28"))
        for y in range(11, 22):                # torso: worn coat
            for x in range(cx - 4, cx + 4):
                col = C("4d2b32")
                if x == cx - 4 or y == 21:
                    col = C("341c27")
                fc.set(x, y, col)
        for y in range(4, 11):                 # head + beanie
            for x in range(cx - 3, cx + 3):
                fc.set(x, y, C("d7b594") if y > 6 else C("151d28"))
        fc.set(cx + 1, 9, C("341c27"))         # stubble hint
        fc.set(cx + 2, 9, C("341c27"))
        # LEFT hand: the spray can parked on the seat beside him
        fc.set(cx - 5, 20, C("d7b594"))
        fc.set(cx - 6, 20, C("d7b594"))
        for k in range(5):
            fc.set(cx - 7, 17 + k, C("819796"))
            fc.set(cx - 6, 17 + k, C("577277"))
        fc.set(cx - 7, 16, C("a23e8c"))        # its cap
        # RIGHT hand + cigarette: down (f0), at the mouth (f1), easing (f2)
        if f == 0:
            fc.set(cx + 5, 20, C("d7b594"))
            fc.set(cx + 6, 19, C("c7cfcc"))
            fc.set(cx + 7, 19, C("602c2c"))
        elif f == 1:
            fc.set(cx + 3, 10, C("d7b594"))
            fc.set(cx + 4, 9, C("c7cfcc"))
            fc.set(cx + 5, 9, C("cf573c"))     # ember, pulling hot
        else:
            fc.set(cx + 4, 14, C("d7b594"))
            fc.set(cx + 5, 13, C("c7cfcc"))
            fc.set(cx + 6, 13, C("de9e41"))    # ember cooling
        fc.outline_auto()
        frames.append(fc)
    sheet = Canvas(28 * 3, 36)
    for i, fr in enumerate(frames):
        sheet.img.alpha_composite(fr.img, (i * 28, 0))
    sheet.px = sheet.img.load()
    return sheet, (14, 34), None

# The crossarms sit a FIXED height above the base, and the insulators a
# fixed distance along them, so the wires strung between poles actually
# meet the arms. The pole TOP still varies, which is where the variety
# comes from — same lesson the pylons taught: vary the height and the
# spans stop reaching (CLAUDE.md).
TELE_ARMS = ((44, 7), (37, 5))          # (px above base, half-span)


def _tele_insulators(span: int) -> tuple:
    return (-span + 1, 0, span - 1)


def make_telegraph_pole(variant: int) -> tuple[Canvas, tuple, list]:
    """The poles that march beside the line. A straight railway reads as a
    drawn line until something repeats ALONGSIDE it at human intervals —
    these are that. Two crossarms, insulators, and a lean on some."""
    rng = random.Random(f"{SEED}:telegraph:{variant}")
    c = Canvas(34, 76)
    px, base = 16, 66
    height = rng.randint(48, 56)           # only the top varies now
    lean = (0, 1, -1, 0)[variant % 4]
    for k in range(height):                    # the pole, lit on the north
        x = px + (k * lean) // 24
        c.set(x, base - k, C("602c2c"))
        c.set(x + 1, base - k, C("341c27"))
    top = base - height
    for (arm_up, span) in TELE_ARMS:
        arm_y = base - arm_up
        ax = px + (arm_up * lean) // 24
        for i in range(-span, span + 1):
            c.set(ax + i, arm_y + abs(i) // 4, C("4d2b32"))
        for i in _tele_insulators(span):       # insulators
            c.set(ax + i, arm_y + abs(i) // 4 - 1, C("73bed3"))
    if variant % 3 == 0:                        # one pole has lost an arm
        for i in range(3, 8):
            c.set(px + i, base - TELE_ARMS[0][0] + i // 4, (0, 0, 0, 0))
    for _ in range(rng.randint(1, 3)):
        c.set(px + rng.randint(0, 1), base - rng.randrange(6, height - 6),
              C("241527"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (px, base))
    return cr, orr, ["diamond", 3.0, 2.0]


def make_rail_signal(clear: bool) -> tuple[Canvas, tuple, list]:
    """A colour-light signal on the line. Dead six years, but one of them
    still shows an aspect, which is exactly the kind of detail that makes
    a straight track read as a working railway."""
    c = Canvas(30, 74)
    px, base = 14, 64
    for k in range(44):                        # mast
        c.set(px, base - k, C("394a50"))
        c.set(px + 1, base - k, C("202e37"))
    for i in range(5):                         # base cabinet
        for k in range(7):
            c.set(px - 2 + i, base - k, C("577277") if i < 2 else C("394a50"))
    head_y = base - 50
    for i in range(-4, 5):                     # the head
        for k in range(14):
            c.set(px + i, head_y + k, C("202e37") if abs(i) > 3 else C("151d28"))
    for (ly, col) in ((head_y + 3, C("a53030") if not clear else C("341c27")),
                      (head_y + 8, C("de9e41") if clear else C("241527"))):
        for i in range(-2, 3):
            for k in range(3):
                if abs(i) + k < 4:
                    c.set(px + i, ly + k, col)
    for i in range(-5, 6):                     # the hood over the lamps
        c.set(px + i, head_y - 1, C("151d28"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (px, base))
    return cr, orr, ["diamond", 3.5, 2.0]


def make_toll_booth() -> tuple[Canvas, tuple, list]:
    """The warden's booth on the district edge: a small hut with a lit
    serving window, a counter shelf, a shift light over it, and the man
    himself visible inside. Built like every other prop — iso box with a
    top face, a lit north-west wall and a shaded east one."""
    rng = random.Random(f"{SEED}:tollbooth")
    c = Canvas(72, 84)
    ox, oy = 10, 60          # the booth's south corner
    w, d, h = 26, 13, 30
    # the two visible walls
    for i in range(w):
        x = ox + i
        base = oy + i // 2
        for k in range(h):
            col = C("577277") if k > h - 4 else C("819796")
            if (i + k) % 11 == 0:
                col = C("394a50")            # panel seams
            c.set(x, base - k, col)
    for j in range(d):
        x = ox + w - 1 + j
        base = oy + (w - 1) // 2 - j // 2
        for k in range(h):
            c.set(x, base - k, C("394a50") if k > h - 4 else C("577277"))
    # the roof: a flat top face with a lip
    for i in range(w):
        for j in range(d):
            x = ox + i + j
            y = oy + i // 2 - j // 2 - h
            c.set(x, y, C("a8b5b2") if (i + j) % 9 else C("819796"))
    for i in range(w):                        # roof lip, catching light
        c.set(ox + i, oy + i // 2 - h + 1, C("c7cfcc"))
    # the serving window: a dark opening with a warm light inside
    win_x0, win_y0 = ox + 5, oy + 2 - h + 12
    for i in range(15):
        for k in range(11):
            x = win_x0 + i
            y = win_y0 + i // 2 + k
            c.set(x, y, C("151d28") if k > 1 else C("090a14"))
    for i in range(15):                       # the counter shelf
        c.set(win_x0 + i, win_y0 + i // 2 + 11, C("884b2b"))
        c.set(win_x0 + i, win_y0 + i // 2 + 12, C("602c2c"))
    # the warden, shoulders and head, sitting in the dark of the window
    hx, hy = win_x0 + 6, win_y0 + 6
    for i in range(9):                        # shoulders
        c.set(hx - 3 + i, hy + 4 + (i // 3), C("202e37"))
        c.set(hx - 3 + i, hy + 5 + (i // 3), C("172038"))
    for i in range(6):                        # head
        for k in range(5):
            c.set(hx - 2 + i, hy - 1 + k, C("d7b594"))
    for i in range(7):                        # his cap
        c.set(hx - 3 + i, hy - 2, C("202e37"))
        c.set(hx - 3 + i, hy - 3, C("394a50"))
    c.set(hx, hy + 1, C("151d28"))            # eyes
    c.set(hx + 2, hy + 1, C("151d28"))
    # the shift light over the window
    c.set(ox + 12, oy + 6 - h + 6, C("de9e41"))
    c.set(ox + 13, oy + 6 - h + 6, C("e8c170"))
    for _ in range(rng.randint(2, 4)):        # weathering
        c.set(ox + rng.randrange(2, w - 2), oy + rng.randrange(4, h - 6),
              C("394a50"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (ox + w // 2 + d // 2, oy + w // 4 + 4))
    return cr, orr, ["diamond", 15.0, 8.0]


def make_toll_barrier(raised: bool) -> tuple[Canvas, tuple, list | None]:
    """The boom across the road: a striped pole on a counterweight post.
    Down means pay up; up means somebody already did."""
    c = Canvas(72, 68)
    px, py = 8, 50
    for k in range(14):                       # the post
        c.set(px, py - k, C("577277"))
        c.set(px + 1, py - k, C("394a50"))
    c.set(px, py - 14, C("819796"))
    if raised:
        # the boom stands up: vertical, stripes reading top to bottom
        for k in range(34):
            col = C("cf573c") if (k // 5) % 2 == 0 else C("c7cfcc")
            c.set(px + 3, py - 12 - k, col)
            c.set(px + 4, py - 12 - k, col if k % 5 else C("a53030"))
    else:
        # the boom lies across the road on the iso axis
        for i in range(46):
            col = C("cf573c") if (i // 7) % 2 == 0 else C("c7cfcc")
            y = py - 11 + i // 2
            c.set(px + 3 + i, y, col)
            c.set(px + 3 + i, y + 1, C("a53030") if (i // 7) % 2 == 0
                  else C("819796"))
        for k in range(4):                    # the far rest post
            c.set(px + 48, py - 11 + 23 + k, C("394a50"))
    c.outline_auto()
    cr, orr = crop_canvas(c, (px, py))
    return cr, orr, None


def make_warden_portrait() -> tuple[Canvas, tuple, list | None]:
    """His face for the dialogue window. A warden who has sat this gate a
    long time: peaked cap, a jaw that has said no ten thousand times, and
    eyes that are already counting your bag. Drawn as a solid portrait —
    lit from the north-west like everything else."""
    rng = random.Random(f"{SEED}:warden:face")
    c = Canvas(48, 48)
    # backing plate so the portrait reads as a framed photo
    for y in range(48):
        for x in range(48):
            c.set(x, y, C("172038") if (x + y) % 17 else C("202e37"))
    cx = 24
    # neck and collar
    for y in range(36, 45):
        for x in range(cx - 6, cx + 6):
            c.set(x, y, C("ad7757") if y < 39 else C("202e37"))
    for x in range(cx - 11, cx + 11):         # shoulders
        c.set(x, 43, C("394a50"))
        c.set(x, 44, C("202e37"))
    c.set(cx - 7, 42, C("de9e41"))            # a collar pin, badge brass
    c.set(cx - 6, 42, C("e8c170"))
    # the head: a solid mass, lit left, shaded right
    for y in range(11, 39):
        span = 11
        if y < 14:
            span = 8 + (y - 11)
        elif y > 34:
            span = 11 - (y - 34) * 2
        for x in range(cx - span, cx + span):
            col = C("ad7757")                 # the face's own tone
            if x > cx + span - 4:
                col = C("7a4841")             # shaded cheek
            elif x < cx - span + 3:
                col = C("d7b594")             # lit edge, north-west
            c.set(x, y, col)
    # the cap: a hard band with a peak over the brow
    for y in range(4, 13):
        for x in range(cx - 13, cx + 13):
            col = C("253a5e") if y < 10 else C("172038")
            if y < 6 and abs(x - cx) < 10:
                col = C("3c5e8b")             # crown catching light
            c.set(x, y, col)
    for x in range(cx - 15, cx + 14):         # the peak
        c.set(x, 13, C("10141f"))
        c.set(x, 14, C("151d28"))
    c.set(cx - 1, 8, C("de9e41"))             # cap badge
    c.set(cx, 8, C("e8c170"))
    c.set(cx + 1, 8, C("de9e41"))
    c.set(cx, 9, C("884b2b"))
    # brow shadow, eyes, and the look
    for x in range(cx - 10, cx + 10):
        c.set(x, 16, C("7a4841"))
    for (ex, lit) in ((cx - 6, True), (cx + 4, False)):
        for i in range(4):
            c.set(ex + i, 18, C("ebede9") if lit else C("c7cfcc"))
            c.set(ex + i, 19, C("151d28") if i in (1, 2) else C("a8b5b2"))
        c.set(ex - 1, 17, C("7a4841"))
    for x in range(cx - 8, cx - 2):           # eyebrows, drawn low
        c.set(x, 16, C("341c27"))
    for x in range(cx + 3, cx + 9):
        c.set(x, 16, C("341c27"))
    # nose, and a mouth set in a flat mean line
    for y in range(21, 27):
        c.set(cx, y, C("d7b594"))
        c.set(cx + 1, y, C("7a4841"))
    c.set(cx - 1, 27, C("7a4841"))
    c.set(cx + 2, 27, C("7a4841"))
    for x in range(cx - 6, cx + 6):
        c.set(x, 31, C("7a4841"))
    c.set(cx - 7, 30, C("7a4841"))            # the corner that never lifts
    c.set(cx + 6, 32, C("7a4841"))
    # a scar through one eyebrow, and stubble as patches (never dots)
    for k in range(5):
        c.set(cx + 6 + k // 2, 13 + k, C("d7b594"))
    for _ in range(rng.randint(5, 7)):
        sx = cx + rng.randint(-9, 9)
        sy = 30 + rng.randint(0, 6)
        for dx in range(rng.randint(2, 4)):
            c.set(sx + dx, sy, C("7a4841"))
    return c, (24, 24), None


def make_helicopter() -> tuple[Canvas, tuple, list | None]:
    """The bird that lifts you out: a 3-frame sheet, rotor turning. Seen
    from above and to the side like everything else — fuselage with a lit
    top, a glass nose, tail boom and fin, skids hanging under it, and a
    rotor disc that blurs across the frames."""
    rng = random.Random(f"{SEED}:heli")
    fw, fh = 116, 62
    frames = []
    for f in range(3):
        c = Canvas(fw, fh)
        cx, cy = 46, 36
        # skids first: they hang below the body
        for sx in range(cx - 14, cx + 12):
            c.set(sx, cy + 11, C("202e37"))
        for strut_x in (cx - 10, cx + 6):
            for k in range(3):
                c.set(strut_x, cy + 8 + k, C("394a50"))
        # fuselage: a rounded body, lit along the top
        for dy in range(-9, 10):
            half = int((1.0 - (dy / 10.0) ** 2) ** 0.5 * 17)
            for dx in range(-half, half + 1):
                col = C("394a50")
                if dy < -5:
                    col = C("577277")          # top face catches the sky
                elif dy > 6:
                    col = C("202e37")          # under-shadow
                c.set(cx + dx, cy + dy, col)
        # glass nose, facing west
        for dy in range(-5, 5):
            half = int((1.0 - (dy / 6.0) ** 2) ** 0.5 * 7)
            for dx in range(-half, 1):
                c.set(cx - 11 + dx, cy + dy,
                      C("3c5e8b") if dy < 1 else C("253a5e"))
        # tail boom + fin
        for tx in range(cx + 15, cx + 44):
            c.set(tx, cy - 1, C("577277"))
            c.set(tx, cy, C("394a50"))
            c.set(tx, cy + 1, C("202e37"))
        for k in range(9):
            c.set(cx + 42, cy - 2 - k, C("394a50"))
            c.set(cx + 43, cy - 2 - k, C("202e37"))
        for k in range(4):                     # tail rotor
            c.set(cx + 41 - k, cy - 11 + (k if f == 1 else 0), C("819796"))
        # main rotor: a long blur disc, swept differently each frame
        angle = f * 0.9
        for step in range(-42, 43):
            t = step / 42.0
            rx = int(cx + math.cos(angle) * step)
            ry = int(cy - 13 + math.sin(angle) * step * 0.22)
            if 0 <= rx < fw and 0 <= ry < fh:
                c.set(rx, ry, C("819796") if abs(t) > 0.55 else C("c7cfcc"))
        c.set(cx, cy - 13, C("151d28"))        # the mast
        c.set(cx, cy - 14, C("394a50"))
        for _ in range(rng.randint(2, 4)):     # a little wear
            c.set(cx + rng.randint(-12, 12), cy + rng.randint(-6, 6),
                  C("202e37"))
        c.outline_auto()
        frames.append(c)
    sheet = Canvas(fw * 3, fh)
    for i, fr in enumerate(frames):
        sheet.img.alpha_composite(fr.img, (i * fw, 0))
    sheet.px = sheet.img.load()
    return sheet, (46, 47), None


def make_lz_marker() -> tuple[Canvas, tuple, list | None]:
    """The pickup marker painted on the ground: a worn circle with a
    cross through it, the paint half gone. The green glow and the smoke
    are runtime — this is just what somebody painted years ago."""
    rng = random.Random(f"{SEED}:lz")
    c = Canvas(76, 44)
    cx, cy = 38, 22
    for a in range(0, 360, 3):
        if rng.random() < 0.22:                # the paint has worn through
            continue
        rad = math.radians(a)
        x = int(cx + math.cos(rad) * 30)
        y = int(cy + math.sin(rad) * 15)
        c.set(x, y, C("75a743"))
        c.set(x, y + 1, C("25562e"))
    for k in range(-18, 19):                   # the cross, iso-aligned
        if rng.random() < 0.18:
            continue
        c.set(cx + k, cy + k // 2, C("75a743"))
        c.set(cx + k, cy - k // 2, C("25562e"))
    c.outline_auto()
    return c, (38, 23), None


def make_chalkboard() -> tuple[Canvas, tuple, list | None]:
    """The classroom board on the x-axis wall face: slate, chalk ghost
    lines, the tray, two stubs of chalk nobody came back for."""
    rng = random.Random(f"{SEED}:chalkboard")
    c = Canvas(34, 36)
    ox = 4
    for i in range(26):                        # board follows the wall slope
        x = ox + i
        top = 5 + i // 2
        c.set(x, top, C("151d28"))             # frame
        for k in range(1, 12):
            col = C("19332d")
            if k < 3 and i < 20:
                col = C("25562e")              # dusty sheen, upper left
            c.set(x, top + k, col)
        c.set(x, top + 12, C("151d28"))
        c.set(x, top + 13, C("341c27"))        # the tray
    for s in range(rng.randint(3, 4)):         # chalk ghost lines
        sx = ox + 3 + rng.randrange(12)
        sy = 8 + rng.randrange(6) + (sx - ox) // 2
        for k in range(rng.randint(3, 6)):
            c.set(sx + k, sy + k // 2, C("c7cfcc"))
    for s in range(2):                         # chalk stubs on the tray
        sx = ox + 5 + s * 9 + rng.randrange(3)
        c.set(sx, 5 + (sx - ox) // 2 + 13, C("ebede9"))
        c.set(sx + 1, 5 + (sx - ox) // 2 + 13, C("ebede9"))
    c.outline_auto()
    return c, (17, 33), None


def make_floor_edge(axis: str) -> tuple[Canvas, tuple, list | None]:
    """The second-story slab lip: a dark band under the tile's exposed
    face so the upper floor reads as a DECK above the room instead of
    dissolving into it (x = the SW edge, y = the SE edge)."""
    c = Canvas(64, 36)
    for t in range(32):
        x = t if axis == "x" else 32 + t
        edge_y = (16 + t // 2) if axis == "x" else (31 - t // 2)
        # a LIT top edge over the shadow — dark-on-dark vanished at night
        c.set(x, edge_y + 1, C("577277"))
        c.set(x, edge_y + 2, C("151d28"))
        c.set(x, edge_y + 3, C("090a14"))
    return c, (32, 16), None


def make_power_box(axis: str, broken: bool) -> tuple[Canvas, tuple, list | None]:
    """House power box on the wall face. Working: shut lid, meter, conduit.
    Broken: lid ajar, dangling wires, scorch — sparks come at runtime
    (exactly one broken box per district; a repair quest someday)."""
    rng = random.Random(f"{SEED}:powerbox:{axis}:{broken}")
    c = Canvas(20, 28)
    ox, oy = 5, 8
    slope = 1 if axis == "x" else -1
    for i in range(8):                          # the box, on the wall slope
        x = ox + i
        y0 = oy + (i // 2) * slope
        for k in range(9):
            col = C("394a50")
            if k == 0 or i == 0 or i == 7:
                col = C("202e37")
            c.set(x, y0 + k, col)
    if broken:
        for i in range(4):                      # lid hanging open
            x = ox + 8 + i // 2
            y = oy + (8 // 2) * slope + 2 + i
            c.set(x, y, C("202e37"))
        for w in range(3):                      # dangling wires
            wx = ox + 2 + w * 2
            wy = oy + (2 // 2) * slope + 9
            for k in range(3 + w * 2):
                c.set(wx + (k % 2 if w == 1 else 0), wy + k, C("090a14") if k % 2 else C("341c27"))
            c.set(wx, wy + 3 + w * 2, C("cf573c"))   # live copper tip
        c.set(ox + 3, oy + 1 * slope + 3, C("151d28"))  # scorch
        c.set(ox + 4, oy + 1 * slope + 4, C("151d28"))
    else:
        cxm = ox + 3
        cym = oy + (3 // 2) * slope + 3
        c.set(cxm, cym, C("a8ca58"))            # the meter, faintly alive
        c.set(cxm + 1, cym, C("577277"))
    for k in range(5):                          # conduit down to the ground
        c.set(ox + 6, oy + (6 // 2) * slope + 9 + k, C("577277") if k % 2 else C("394a50"))
    c.outline_auto()
    return c, (9, 21), None

def make_spark_frames() -> list:
    """Three tiny spark bursts for the broken box (runtime blinks them)."""
    out = []
    for f in range(3):
        rng = random.Random(f"{SEED}:spark:{f}")
        img = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
        px = img.load()
        cx = cy = 6
        for i in range(rng.randint(4, 6)):
            ang_x = rng.choice((-1, 0, 1))
            ang_y = rng.choice((-1, 0, 1))
            lx, ly = cx, cy
            for k in range(rng.randint(1, 3)):
                lx += ang_x
                ly += ang_y
                if 0 <= lx < 12 and 0 <= ly < 12:
                    col = [(232, 193, 112, 255), (235, 237, 233, 255),
                           (222, 158, 65, 255)][rng.randrange(3)]
                    px[lx, ly] = col
        px[cx, cy] = (235, 237, 233, 255)
        out.append(img)
    return out

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
    # CRATES get the full anti-repetition treatment: ten of them, each with
    # its own build roll, its own baked lean, and its own wear. A pile of
    # these reads as ten thrown-down boxes instead of one box stamped ten
    # times (user ask: break visual repetition).
    for i, art in enumerate(clutter_variants(
            "crate", 10,
            lambda r, k: draw_crate(r, r.choice((24, 28, 32)), r.randint(10, 15),
                                    k % 2, damaged=(k % 3 == 2),
                                    stencil=(k % 4 == 0)),
            "crate",
            wear_colors=[C("602c2c"), C("341c27")],
            leans=(0.0, 1.1, -1.1, 0.6, -0.6, 0.0, 1.5, -1.5, 0.9, -0.9))):
        fam("crate", i, art)
    for i in range(4):
        fam("toolbox", i, make_toolbox(i))
    for i in range(4):                  # the grid: towers, spans, the cabinet
        fam("pylon", i, make_pylon(i))
    for i in range(2):
        fam("power_wire", i, make_power_wire(i))
    props["utility_box"] = make_utility_box()
    for i in range(4):
        rng = random.Random(f"{SEED}:cyl:{i}")
        color = ("steel", "red", "gray", "steel")[i]
        fam("cylinder", i, draw_cylinder(rng, color, rng.randint(30, 36), toppled=(i == 3)))
    for i, art in enumerate(clutter_variants(
            "tires", 7,
            lambda r, k: draw_tires(r, (3, 2, 1, 1, 2, 1, 3)[k], single=(k in (3, 5))),
            "tires",
            wear_colors=[C("202e37")],
            leans=(0.0, 0.8, -0.8, 1.2, -1.2, 0.4, -0.4))):
        fam("tires", i, art)
    for i, art in enumerate(clutter_variants(
            "pallet", 6,
            lambda r, k: draw_pallet(broken=(k % 3 == 1), stacked=(k % 3 == 2)),
            "pallet",
            wear_colors=[C("602c2c"), C("341c27")],
            leans=(0.0, 1.3, -1.3, 0.7, -0.7, 1.0))):
        fam("pallet", i, art)
    for i in range(2):
        rng = random.Random(f"{SEED}:dumpster:{i}")
        fam("dumpster", i, draw_dumpster(rng, lid_open=(i == 1)))
    for i, art in enumerate(clutter_variants(
            "rubble", 7, lambda r, k: draw_rubble(r, min(k % 3, 2)), "rubble",
            wear_colors=[C("341c27")],
            leans=(0.0, 0.0, 0.6, -0.6, 0.0, 1.0, -1.0))):
        fam("rubble", i, art)
    for i, kind in enumerate(("tall", "snapped", "fallen")):
        rng = random.Random(f"{SEED}:pillar:{i}")
        fam("pillar", i, draw_pillar(rng, kind))

    # interior dressing (not scattered; placed by the builder)
    # FURNITURE VARIETY. Every one of these used to be a single sprite, so
    # every house in the district had the identical table, the identical
    # bookshelf, the identical cabinet (user: "these have visual
    # repetition... make sure everything in my game doesnt have
    # repetition"). Each now bakes five copies with its own grime and its
    # own slight lean — furniture leans a LITTLE, since a cabinet tipped
    # like a crate reads as falling over rather than lived-in.
    _FURNITURE_WEAR = [C("341c27"), C("241527")]
    _FURNITURE_LEANS = (0.0, 0.4, -0.4, 0.7, -0.7)
    for _name, _build in (("couch", make_couch), ("cabinet", make_cabinet),
            ("tv_stand", make_tv_stand), ("table", make_table),
            ("chair", make_chair), ("bookshelf", make_bookshelf)):
        for i, art in enumerate(clutter_variants(
                _name, 5, (lambda b: (lambda r, k: b()))(_build), _name,
                wear_colors=_FURNITURE_WEAR, leans=_FURNITURE_LEANS)):
            fam(_name, i, art)
    for i in range(4):
        fam("crate_stack", i, make_crate_stack(i))
    for i in range(4):
        fam("rack", i, make_rack(i))
    # racks stood in identical pairs in the yards (user screenshot): three
    # more, each worn and leaning its own way
    for i, art in enumerate(clutter_variants(
            "rack", 3, lambda r, k: make_rack(k % 4), "rack_extra",
            wear_colors=[C("341c27"), C("602c2c")],
            leans=(0.5, -0.5, 0.8))):
        fam("rack", 4 + i, art)
    # vehicles: every lane heading pre-baked (nw/se drawn, ne/sw mirrored);
    # the last two specs are broken-into wrecks
    veh_specs = [("car", 0, False), ("car", 4, False), ("pickup", 5, False),
                 ("pickup", 2, False), ("car", 1, False),
                 ("car", 3, True), ("pickup", 1, True)]
    for i, (kind, scheme, broken) in enumerate(veh_specs):
        # the GENERATOR knows whether this is a car or a truck, so it says
        # so — the map screen labels the dots off this rather than
        # hardcoding a list of indexes that would rot the moment the fleet
        # changes (the door collider taught us this one)
        for _side in ("n", "s", "e", "w", "ne", "nw", "se", "sw"):
            VEHICLE_KINDS["vehicle_%s_%d" % (_side, i)] = (
                "truck" if kind == "pickup" else "car")
        art_nw = make_vehicle(kind, scheme, rev=False, broken=broken)
        art_se = make_vehicle(kind, scheme, rev=True, broken=broken)
        fam("vehicle_nw", i, art_nw)
        fam("vehicle_se", i, art_se)
        fam("vehicle_ne", i, mirror_prop(art_nw))
        fam("vehicle_sw", i, mirror_prop(art_se))
        # the FOUR angles a (2,1) sheet cannot draw: the flank view (the
        # car crossing the screen) and the two end-on views. With these
        # the nose can track the cursor through all 8 headings.
        art_w = make_vehicle_flank(kind, scheme, broken=broken)
        fam("vehicle_w", i, art_w)
        fam("vehicle_e", i, mirror_prop(art_w))
        fam("vehicle_s", i, make_vehicle_head(kind, scheme, toward=True,
                                              broken=broken))
        fam("vehicle_n", i, make_vehicle_head(kind, scheme, toward=False,
                                              broken=broken))
        if not broken:
            # driveable cars: the door-open enter/exit frame (texture swap)
            door_nw = make_vehicle(kind, scheme, rev=False, door_open=True)
            door_se = make_vehicle(kind, scheme, rev=True, door_open=True)
            props[f"vehicle_nw_{i}_door"] = door_nw
            props[f"vehicle_se_{i}_door"] = door_se
            props[f"vehicle_ne_{i}_door"] = mirror_prop(door_nw)
            props[f"vehicle_sw_{i}_door"] = mirror_prop(door_se)
            door_w = make_vehicle_flank(kind, scheme, door_open=True)
            props[f"vehicle_w_{i}_door"] = door_w
            props[f"vehicle_e_{i}_door"] = mirror_prop(door_w)
            props[f"vehicle_s_{i}_door"] = make_vehicle_head(
                kind, scheme, toward=True, door_open=True)
            props[f"vehicle_n_{i}_door"] = make_vehicle_head(
                kind, scheme, toward=False, door_open=True)
    # buses for the depot: two liveries parked, two broken into
    bus_specs = [(1, False), (2, False), (0, True), (3, True)]
    for i, (scheme, broken) in enumerate(bus_specs):
        bus_nw = make_vehicle("bus", scheme, rev=False, broken=broken)
        bus_se = make_vehicle("bus", scheme, rev=True, broken=broken)
        fam("bus_nw", i, bus_nw)
        fam("bus_se", i, bus_se)
    # trainyard rolling stock
    for i, (scheme, broken) in enumerate([(0, False), (1, False), (2, False), (0, True)]):
        fam("boxcar_x", i, make_boxcar(scheme, broken))
    buffer_art = make_buffer_stop()
    fam("buffer_stop", 0, buffer_art)
    fam("buffer_stop", 1, mirror_prop(buffer_art))
    # the lit rooms and the flex that feeds them
    props["interior_lamp"] = make_interior_lamp()
    props["cable_x"] = make_cable("x")
    props["cable_y"] = make_cable("y")
    # two-story interiors
    props["stairs"] = make_stairs()
    for i, art in enumerate(clutter_variants(
            "bed", 4, lambda r, k: make_bed(), "bed",
            wear_colors=[C("341c27"), C("241527")],
            leans=(0.0, 0.3, -0.3, 0.6))):
        fam("bed", i, art)
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
    # the scrapyard's machines
    for i in range(2):
        fam("forklift", i, make_forklift(i))
    props["crane"] = make_crane()
    # street furniture round two
    for i in range(2):
        fam("vending", i, make_vending(i))
        fam("newsbox", i, make_newsbox(i))
    # the gallery
    for i in range(3):
        fam("graffiti_x", i, make_graffiti_wall(i))
    for i in range(4):
        fam("spray_cans", i, make_spray_cans(i))
    props["smoker"] = make_smoker_sheet()
    props["chalkboard"] = make_chalkboard()
    props["helicopter"] = make_helicopter()
    props["locomotive"] = make_locomotive()
    for i in range(4):
        fam("telegraph_pole", i, make_telegraph_pole(i))
    # one wire span per gap the placer can roll (7..10 cells)
    for span in range(7, 11):
        props["telegraph_wire_%d" % span] = make_telegraph_wire(span)
    fam("rail_signal", 0, make_rail_signal(False))
    fam("rail_signal", 1, make_rail_signal(True))
    props["toll_booth"] = make_toll_booth()
    props["toll_barrier"] = make_toll_barrier(False)
    props["toll_barrier_open"] = make_toll_barrier(True)
    props["warden_portrait"] = make_warden_portrait()
    props["lz_marker"] = make_lz_marker()
    props["floor_edge_x"] = make_floor_edge("x")
    props["floor_edge_y"] = make_floor_edge("y")
    # house power
    for axis in ("x", "y"):
        props[f"power_box_{axis}"] = make_power_box(axis, False)
        props[f"power_box_{axis}_broken"] = make_power_box(axis, True)
    for i in range(4):
        fam("tree", i, make_tree("pine", i))
    for i in range(3):
        fam("tree", 4 + i, make_tree("oak", i))
    for i in range(2):
        fam("tree", 7 + i, make_tree("dead", i))
    for i in range(3):
        fam("tree_autumn", i, make_tree("autumn", i))
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
    y0 = (13 if crouch else 8) + bob   # +2 frame height (user: a touch bigger)
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
    y0 = (21 if crouch else 16) + bob
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
    y0 = (22 if crouch else 17) + bob
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
    y0 = (22 if crouch else 17) + bob
    arm_len = 7 if crouch else 9
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

    elif view == "front":  # facing S: head to camera, soles away.
        # WIDE now: a body flat on the ground shows its whole shoulder
        # span, not the standing silhouette (user: "really skinny")
        cx = CX
        base = 14
        for side_x in (cx - 5, cx + 2):                  # boots (far end)
            c.rect(side_x, base, side_x + 2, base + 2, boot)
        lift = 1 if phase > 0 else 0
        c.rect(cx - 5, base + 3, cx - 2, base + 7, pant)
        c.rect(cx + 1, base + 3 + lift, cx + 4, base + 7, pant_d)
        c.hline(cx - 5, cx - 2, base + 7, pant_d)
        c.rect(cx - 5, base + 8, cx + 4, base + 15, jkt)  # torso, 10 wide
        c.vline(cx - 5, base + 8, base + 15, jkt_d)
        c.vline(cx + 4, base + 8, base + 15, jkt_d)
        c.rect(cx - 6, base + 13, cx + 5, base + 15, jkt)  # shoulder span
        c.set(cx - 6, base + 13, jkt_d)
        c.set(cx + 5, base + 13, jkt_d)
        if has_pack:
            c.rect(cx - 3, base + 9, cx + 2, base + 14, pack)
            c.vline(cx + 2, base + 9, base + 14, pack_d)
        arm_y = base + 14
        c.rect(cx - 7, arm_y - (1 if phase > 0 else 0), cx - 6, arm_y + 4, jkt)
        c.rect(cx + 6, arm_y - (1 if phase < 0 else 0), cx + 7, arm_y + 4, jkt)
        c.set(cx - 7, arm_y + 5, skin)
        c.set(cx + 6, arm_y + 5, skin)
        c.rect(cx - 4, base + 16 + drag, cx + 3, base + 20 + drag, head_top)
        c.hline(cx - 4, cx + 3, base + 21 + drag, skin_sh)  # brow sliver
        if beard:
            c.hline(cx - 2, cx + 1, base + 22 + drag, hair)

    elif view == "back":
        c.rect(CX - 4, y0, CX + 3, y0 + 6, HAIR)
        c.vline(CX + 3, y0 + 1, y0 + 6, HAIR_D)
        c.rect(CX - 4, y0 + 7, CX + 3, y0 + 7, HAIR_D)


def draw_torso(c: Canvas, view: str, bob: int, crouch: bool = False) -> None:
    y0 = (21 if crouch else 16) + bob
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
    y0 = (22 if crouch else 17) + bob
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
    y0 = (22 if crouch else 17) + bob
    arm_len = 7 if crouch else 9
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
        base = 13
        c.rect(cx - 4, base + drag, cx + 3, base + 4 + drag, head_top)
        arm_y = base + 5
        c.rect(cx - 7, arm_y, cx - 6, arm_y + 5 - (1 if phase > 0 else 0), jkt)
        c.rect(cx + 6, arm_y, cx + 7, arm_y + 5 - (1 if phase < 0 else 0), jkt)
        c.set(cx - 7, arm_y - 1, skin)
        c.set(cx + 6, arm_y - 1, skin)
        c.rect(cx - 6, base + 5, cx + 5, base + 7, jkt)   # shoulder span
        c.set(cx - 6, base + 7, jkt_d)
        c.set(cx + 5, base + 7, jkt_d)
        c.rect(cx - 5, base + 5, cx + 4, base + 13, jkt)  # torso, 10 wide
        c.vline(cx - 5, base + 5, base + 13, jkt_d)
        c.vline(cx + 4, base + 5, base + 13, jkt_d)
        if has_pack:
            c.rect(cx - 3, base + 6, cx + 2, base + 12, pack)
            c.vline(cx - 3, base + 6, base + 12, pack_d)
        lift = 1 if phase > 0 else 0
        c.rect(cx - 5, base + 13, cx - 2, base + 18, pant)
        c.rect(cx + 1, base + 13, cx + 4, base + 18 - lift, pant_d)
        for side_x in (cx - 5, cx + 2):                  # soles toward camera
            c.rect(side_x, base + 19, side_x + 2, base + 21, boot)

    elif view == "diag_front":  # facing SE: along the down-right diagonal.
        # THICK ribbon now - the old 5-wide diagonal read as a stick
        sx, sy = 3, 16
        c.rect(sx, sy, sx + 2, sy + 3, boot)             # soles upper-left
        for i in range(4):                               # legs, leg-thick
            c.rect(sx + 2 + i * 2, sy + 1 + i, sx + 6 + i * 2, sy + 4 + i, pant)
        c.set(sx + 4, sy + 2, pant_d)
        for i in range(5):                               # torso, full mass
            c.rect(sx + 9 + i * 2, sy + 4 + i, sx + 15 + i * 2, sy + 8 + i, jkt)
        c.set(sx + 10, sy + 5, jkt_d)
        if has_pack:
            for i in range(3):
                c.rect(sx + 11 + i * 2, sy + 3 + i, sx + 15 + i * 2, sy + 6 + i, pack)
        hx = sx + 20 + drag
        hy = sy + 11 + drag // 2
        c.rect(hx, hy, hx + 5, hy + 3, head_top)         # standing-sized head
        c.rect(hx + 2, hy + 3, hx + 6, hy + 6, skin)
        if beard:
            c.rect(hx + 4, hy + 6, hx + 6, hy + 6, hair)
        reach = 4 if phase > 0 else 2
        c.rect(hx + 3, hy + 7, hx + 3 + reach, hy + 8, jkt)
        c.set(min(31, hx + 4 + reach), hy + 8, skin)

    else:  # diag_back - facing NE: head upper-right, soles lower-left
        sx, sy = 3, 36
        c.rect(sx, sy - 2, sx + 2, sy + 1, boot)         # soles lower-left
        for i in range(4):
            c.rect(sx + 2 + i * 2, sy - 4 - i, sx + 6 + i * 2, sy - 1 - i, pant)
        c.set(sx + 4, sy - 2, pant_d)
        for i in range(5):
            c.rect(sx + 9 + i * 2, sy - 10 - i, sx + 15 + i * 2, sy - 6 - i, jkt)
        if has_pack:
            for i in range(3):
                c.rect(sx + 10 + i * 2, sy - 11 - i, sx + 14 + i * 2, sy - 9 - i, pack)
        hx = sx + 20 + drag
        hy = sy - 17 - drag // 2
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
# TWO rotating main-menu scenes, 960x544 (covers the expanded view on any
# reasonable display; important content stays inside the central 640x360).
# (This said "Four". Only make_scene_den and make_scene_drain exist: the storm
# scene was RETIRED 2026-08-01 and the unwired "overlook" pitch was DROPPED
# on a user call 2026-08-02 - they looked at it and did not want it. Both
# removals are user calls; restore from git history if that ever reverses.)
# Rendered in world space at 1:1 so they stay pixel-crisp at any window size.

SCENE_W, SCENE_H = 960, 544

def make_scene_drain() -> tuple[Canvas, Image.Image, Canvas]:
    """Menu 1 - THE DRAIN, side-on like a stage.  REDESIGNED 2026-08-02 (user:
    "a redesign would be good too for these"), against the four backdrop
    pitches (yard / warden / underpass / counter) as the bar.

    WHAT THE OLD ONE GOT WRONG, and what replaced it:
      * THE LIGHT WAS A POINT.  one radial falloff on a smooth wall painted
        three or four soft nested ellipses and the picture read as flat rings
        floating on brick.  the shaft is not a point, it is a SLOT: the wall
        term is now distance to a VERTICAL SEGMENT that splays as it falls,
        plus a separate ground BOUNCE off the pool that hugs the benching.
        neither term is ever seen unbroken, because every band edge is cut by
        the wall's own structure - bed joints, perpends and a per-brick tone
        mosaic.  this is the lesson tools/pitches/underpass.py paid for.
      * THE BRICK WAS A PERFECT GRID.  identical bricks at identical pitch,
        which is the visible-grid problem the user complains about most.  now:
        rolled course heights, a rolled pitch PER COURSE, per-brick jitter, a
        no-repeat tone mosaic (no offset repeats beside or above itself),
        wavering courses, chipped corners, replacement bricks from a redder
        batch, a patched section in a different bond, and lime runs out of the
        joints that have lost their mortar.
      * TWO THIRDS OF THE FRAME WAS EMPTY BLACK with one crate in it.  the
        ceiling is a real barrel soffit now (ring courses compressing toward
        the crown, radial joints running to a vanishing point); the left is
        the main drain continuing through a voussoired arch with the channel
        running away into it; the right carries a pipe run on brackets and a
        cast-iron penstock with its headstock, spindle and handwheel, leaking
        a sheet into the channel; and a raider's lantern burns at a cache on
        the benching - the scene's SECOND light source, warm against the cold
        shaft, and the reason the left third is worth looking at.
      * THE LADDER was identical rungs at identical pitch.  the pitch is real
        so it stays regular, but every rung now rolls its own wear, two are
        bent, one is gone to its stubs, the bottom of the run is eaten, and
        the stiles carry a lit face and a shade face.
      * THE WATER was a flat band with random dashes.  it is a reflecting
        plane: a chop whose strokes grow from 1px and tight at the far edge to
        4px and broken at the near one, a cold specular cone under the shaft,
        a warm one under the lantern, and three things floating in it that the
        waterline cuts dead level and that each push a broken ring out.

    THE LIVING-LAYER ANCHORS ARE UNMOVED (scripts/main_menu.gd hardcodes
    them, and an anchor pointing at nothing is animation playing in mid-air):
      (615, 287) the god-ray sprite centre - the shaft is still at x 615.
      (615, 200) the mote emitter, a 40x300 rect - inside the beam.
      (608, 110) where a drip spawns, falling straight down x 608 - open air
        inside the shaft throat.
      (608, 508) where it lands: water_top(608) == 508, asserted at the end of
        this function so a re-roll can never quietly move it.
      (608, 514) and (646, 524) the two ripple sprites - open water, kept
        clear of every floating object.

    THE QUIET ZONE behind the menu buttons (x 400-560, y 290-390, and the
    wordmark's own box up at y 60-175) is held by a two-box wobbled TROUGH
    that damps BOTH light sources.  nothing structural and nothing warm is
    allowed into either box.

    Returns (base, god-ray overlay (soft alpha), 3-frame drip-ripple strip)."""
    rng = random.Random(f"{SEED}:scene:drain")
    c = Canvas(SCENE_W, SCENE_H)

    SHAFT_X = 615
    SPRING_Y = 96            # the barrel soffit springs off the wall here
    WALL_TOP = 108           # the first bed joint, clear of the arced springing
    WALK_Y = 452             # the wall meets the benching
    KERB_Y = 486             # the benching's front nosing
    WATER_Y = 507            # the channel surface - the drip lands on it
    LANT = (250, 456)        # the raider's lantern, the second light source

    COLD = [C("090a14"), C("10141f"), C("151d28"), C("202e37"),
            C("394a50"), C("577277"), C("819796"), C("a8b5b2")]
    WARM = [C("090a14"), C("241527"), C("341c27"), C("4d2b32"),
            C("602c2c"), C("884b2b"), C("ad7757"), C("de9e41")]

    BRICK = [C("090a14"), C("241527"), C("341c27"), C("4d2b32"),
             C("602c2c"), C("884b2b"), C("ad7757")]

    AMB = 1.55                # the darkest a wall face is ever allowed to go

    def band(ramp, lv):
        return ramp[max(0, min(len(ramp) - 1, int(lv + 0.5)))]

    # ------------------------------------------------------------- light ----
    def trough(x, y):
        """the two boxes the ui sits in.  wobbled so the clamp's own edge is
        never a straight line, and linear to zero so it is a gradient and not
        a rectangle of darkness."""
        t1 = 0.46 * max(0.0, 1.0 - max(abs(x - 480) / 126.0,
                                       abs(y - 118 + 3.0 * math.sin(x / 31.0)) / 70.0))
        t2 = 0.78 * max(0.0, 1.0 - max(abs(x - 478) / 140.0,
                                       abs(y - 316 + 4.0 * math.sin(y / 23.0)) / 104.0))
        return max(t1, t2)

    def lev(x, y):
        """(cold level in ramp steps, warm amount 0..1).  the ambient floor
        sits OUTSIDE the trough: the buttons want a dark wall, not a black
        one, or the brick stops existing behind them."""
        t = min(1.0, max(0.0, (y - 10) / float(WALK_Y - 10)))
        half = 21.0 + 30.0 * t * t                 # the beam splays as it falls
        dx = max(0.0, abs(x - SHAFT_X) - half)
        # a NARROW core with a long tail.  the first cut used a wide splay and
        # a hard falloff, which drew a clean-edged triangle on the brick and
        # read as a searchlight cone rather than as light grazing a wall.
        beam = max(0.0, 1.0 - dx / 215.0) ** 2.3 * (0.30 + 0.70 * t)
        bx = abs(x - SHAFT_X)
        by = abs(y - (WALK_Y + 4)) * 1.8           # the bounce hugs the floor
        bounce = max(0.0, 1.0 - (bx * bx + by * by) ** 0.5 / 480.0) ** 1.45
        floor = max(0.0, (y - 140.0) / (WALK_Y - 140.0)) ** 2.0
        lx = abs(x - LANT[0])
        ly = abs(y - LANT[1]) * 1.12
        warm = max(0.0, 1.0 - (lx * lx + ly * ly) ** 0.5 / 132.0) ** 1.9
        warm *= min(1.0, max(0.0, (374 - x) / 48.0))   # never near a button
        w = (0.230 * math.sin(x / 47.0 + y / 61.0)
             + 0.150 * math.sin(y / 29.0 - x / 23.0)
             + 0.090 * math.sin(x / 13.0 + y / 9.0)
             + 0.055 * math.sin(y / 6.0 - x / 5.0))
        f = 1.0 - trough(x, y)
        return (AMB + max(0.0, beam * 3.0 + bounce * 2.3 + floor * 1.0 + w) * f,
                warm * f)

    # --------------------------------------------------------- the courses --
    def spring(x):
        return SPRING_Y + int(round(8.0 * ((x - 480) / 480.0) ** 2))

    bounds = []
    y = WALL_TOP
    while y < WALK_Y:
        ph, ph2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
        amp = 2.3 if rng.random() < 0.17 else 0.9      # one course in six sags
        bounds.append([y + int(round(amp * math.sin(x / 83.0 + ph)
                                     + 0.7 * math.sin(x / 29.0 + ph2)))
                       for x in range(SCENE_W)])
        y += rng.randint(7, 10)
    bounds.append([WALK_Y + 2] * SCENE_W)

    # no offset may repeat beside itself or above itself: a mosaic with
    # duplicates lines back up into stripes, which is the grid all over again
    STEPS = (-0.52, -0.31, -0.13, 0.0, 0.17, 0.38)
    courses = []
    for ci in range(len(bounds) - 1):
        pitch = rng.randint(18, 30)
        e, jx = [], -rng.randint(0, pitch)
        while jx < SCENE_W + 60:
            e.append(jx)
            jx += pitch + rng.randint(-5, 7)
        offs, prev = [], courses[ci - 1][2] if ci else []
        for k in range(len(e) + 1):
            ban = {offs[-1] if offs else None,
                   prev[k] if k < len(prev) else None}
            offs.append(rng.choice([s for s in STEPS if s not in ban]))
        red = {k for k in range(len(e)) if rng.random() < 0.011}
        idx, k = [0] * (SCENE_W + 2), 0
        for x in range(SCENE_W + 2):
            while k < len(e) and x >= e[k]:
                k += 1
            idx[x] = k
        courses.append((set(e), e, offs, red, idx, rng.uniform(-0.28, 0.28)))

    NOWALL = 255
    course_at = bytearray(b"\xff" * (SCENE_W * SCENE_H))
    kind = bytearray(SCENE_W * SCENE_H)     # 0 face 1 bed 2 perp 3 arris 4 lip
    for ci, (eset, e, offs, red, idx, cb) in enumerate(courses):
        top, bot = bounds[ci], bounds[ci + 1]
        for x in range(SCENE_W):
            y0 = max(WALL_TOP - 2, top[x])
            y1 = min(WALK_Y, bot[x])
            perp = x in eset
            for yy in range(y0, y1):
                o = yy * SCENE_W + x
                course_at[o] = ci
                if yy <= top[x]:
                    kind[o] = 1
                elif perp and yy > top[x] + 1:
                    kind[o] = 2
                elif yy == top[x] + 1:
                    kind[o] = 3
                elif yy == y1 - 1:
                    kind[o] = 4

    def wall_col(x, y, bias=0.0):
        if not (0 <= x < SCENE_W and 0 <= y < SCENE_H):
            return C("090a14")
        o = y * SCENE_W + x
        ci = course_at[o]
        cl, wm = lev(x, y)
        s = 1.0 - trough(x, y)
        bo, redbrick = 0.0, False
        if ci != NOWALL:
            eset, e, offs, red, idx, cb = courses[ci]
            k = idx[x]
            bo = offs[min(k, len(offs) - 1)] + cb
            redbrick = k in red
            kk = kind[o]
            if kk == 1:
                bias -= 2.5
            elif kk == 2:
                bias -= 2.0
            elif kk == 3:
                bias += 0.7
            elif kk == 4:
                bias -= 0.8
        if redbrick:
            # a redder BATCH of brick, not a paint chip: it has to track the
            # light without ever climbing off the top of its own ramp, or a
            # lit one comes back as a solid orange rectangle on a grey wall
            return band(BRICK, min(2.9, 0.95 + (cl - AMB) * 0.52 + wm * 2.4
                                   + bias * 1.0 + bo * 0.7))
        if wm > 0.055 and wm * 5.2 > cl - AMB + 0.22:
            return band(WARM, 0.9 + wm * 5.4 + bias + bo * 0.7)
        return band(COLD, cl + bias + bo * s)

    RAMP_AT = {}
    for r in (COLD, WARM, BRICK):
        for i, col in enumerate(r):
            RAMP_AT.setdefault(col, (r, i))

    def dim(x, y, n=1):
        hit = RAMP_AT.get(c.get(x, y))
        if hit is not None:
            r, i = hit
            c.set(x, y, r[max(0, min(len(r) - 1, i - n))])

    # ----------------------------------------------------------- the fill ---
    for yy in range(SCENE_H):
        for x in range(SCENE_W):
            c.set(x, yy, C("090a14"))
    for yy in range(WALL_TOP - 2, WALK_Y):
        for x in range(SCENE_W):
            c.set(x, yy, wall_col(x, yy))

    # --------------------------------------------------- the barrel soffit --
    # ring courses compressing toward the crown, radial joints running back to
    # a vanishing point below the ceiling.  the old scene had flat black here.
    rings, ry, rh = [], 0.0, 2.6
    while ry < SPRING_Y - 5:
        rings.append(ry)
        ry += rh
        rh *= 1.30
    rings.append(float(SPRING_Y))
    nring = len(rings) - 1
    VPY = 320.0
    joint_sets, ring_bias = [], []
    for k in range(nring):
        pick = [v for v in (-0.46, -0.22, 0.0, 0.24, 0.50)
                if not ring_bias or v != ring_bias[-1]]
        ring_bias.append(rng.choice(pick))
    for k in range(nring):
        p = 13 + int(50 * (k / float(nring - 1)) ** 1.4)
        js, jx = [], -rng.randint(0, p)
        while jx < SCENE_W + 80:
            js.append(jx)
            jx += p + rng.randint(-4, 5)
        joint_sets.append(js)
    for k in range(nring):
        y0f, y1f = rings[k], rings[k + 1]
        lo = 0.75 + 1.30 * ((k + 1) / float(nring)) ** 2.1 + ring_bias[k]
        for x in range(SCENE_W):
            bw = 19.0 * ((x - 480) / 480.0) ** 2
            y0 = int(round(y0f + bw))
            y1 = int(round(y1f + bw))
            cl, _ = lev(x, min(SPRING_Y, y1))
            s = 1.0 - trough(x, max(2, y0))
            for yy in range(max(0, y0), min(SPRING_Y + 8, y1)):
                b = 0.0
                if yy == y0:
                    b -= 2.9                        # the ring's bed joint
                elif yy == y0 + 1:
                    b += 0.60
                elif yy == y1 - 1:
                    b -= 0.55
                c.set(x, yy, band(COLD, lo + (cl - AMB) * 0.60 * s + b))
    for k in range(nring):
        y0f, y1f = rings[k], rings[k + 1]
        for jx in joint_sets[k]:
            n = max(1, int(round(y1f - y0f)))
            for i in range(n):
                fy = y0f + i
                sp = (fy - VPY) / (y0f - VPY) if abs(y0f - VPY) > 1 else 1.0
                px = int(round(480 + (jx - 480) * sp))
                bw = 19.0 * ((px - 480) / 480.0) ** 2
                yy = int(round(fy + bw))
                if 0 <= px < SCENE_W and 0 <= yy < SPRING_Y + 8:
                    cl, _ = lev(px, min(SPRING_Y, yy))
                    s = 1.0 - trough(px, max(2, yy))
                    lo = 0.75 + 1.30 * ((k + 1) / float(nring)) ** 2.1 + ring_bias[k]
                    c.set(px, yy, band(COLD, lo + (cl - AMB) * 0.55 * s - 2.0))

    # the corbelled string course the vault springs off: three offsets, each
    # with a lit top edge and its own shadow underneath
    # THE SPRINGING COURSE.  the first cut lit its top edge across all 960 px
    # and painted a bright rail straight through the middle of the frame -
    # exactly the "flat ring" failure one axis over.  it is a SHADOW LINE now
    # with only a hint of a lit arris, and it is broken by its own unit joints.
    for x in range(SCENE_W):
        sy = spring(x)
        cl, _ = lev(x, sy + 6)
        base = cl - 0.55
        c.set(x, sy, band(COLD, base - 2.0))         # the offset's undershadow
        c.set(x, sy + 1, band(COLD, base + 0.45))
        c.set(x, sy + 2, band(COLD, base - 0.25))
        c.set(x, sy + 3, band(COLD, base - 1.6))
        c.set(x, sy + 4, band(COLD, base + 0.25))
        c.set(x, sy + 5, band(COLD, base - 0.35))
        for yy in range(sy + 6, WALL_TOP - 2):
            c.set(x, yy, band(COLD, base - 1.5))
    ux = -rng.randint(0, 30)
    while ux < SCENE_W:                              # corbel unit joints
        ux += rng.randint(34, 74)
        sy = spring(ux)
        for yy in range(sy + 1, WALL_TOP - 2):
            c.set(ux, yy, band(COLD, lev(ux, yy)[0] - 2.6))
        c.set(ux + 1, sy + 1, band(COLD, lev(ux, sy)[0] + 0.3))

    # ------------------------------------------------------- wall defects ---
    # a patched section in a different bond - blockwork shoved into a hole in
    # the brick, mortar smeared, the edge ragged where it was cut in
    px0, px1 = 352, 470
    py0, py1 = 404, 448
    for x in range(px0, px1):
        rag = int(round(2.5 * math.sin(x / 9.0) + 1.5 * math.sin(x / 21.0)))
        for yy in range(py0 + rag, py1):
            cl, _ = lev(x, yy)
            u = ((x - px0) // 29) * 7 + ((yy - py0) // 15) * 3
            b = (-0.35, 0.0, 0.28, -0.18)[u % 4]
            if (x - px0) % 29 == 0 or (yy - py0) % 15 == 0:
                b -= 1.9
            c.set(x, yy, band(COLD, cl + b - 0.45))
        c.set(x, py0 + rag - 1, band(COLD, lev(x, py0)[0] - 2.4))
    for i in range(9):                               # smeared mortar over it
        bx = rng.randrange(px0 + 4, px1 - 8)
        by = rng.randrange(py0 + 4, py1 - 6)
        for (qx, qy) in blob(rng, bx, by, rng.randint(7, 18),
                             {(a, b) for b in range(py0 + 4, py1)
                              for a in range(px0, px1)}):
            c.set(qx, qy, band(COLD, lev(qx, qy)[0] + 0.55))

    # chipped corners: a SOLID wedge gone, the dark bedding showing behind it
    for i in range(34):
        ci = rng.randrange(1, len(courses) - 1)
        el = courses[ci][1]
        ex = el[rng.randrange(1, len(el) - 2)]
        if not (6 < ex < SCENE_W - 12) or trough(ex, bounds[ci][ex]) > 0.30:
            continue
        sz = rng.randint(3, 8)
        low = rng.random() < 0.5
        for k in range(sz):
            yy = (bounds[ci + 1][ex] - 2 - k) if low else (bounds[ci][ex] + 2 + k)
            if not (bounds[ci][ex] < yy < bounds[ci + 1][ex] - 1):
                continue
            c.hline(ex + 1, ex + 1 + (sz - k), yy, band(COLD, lev(ex, yy)[0] - 2.3))
            c.set(ex + 2 + (sz - k), yy, band(COLD, lev(ex, yy)[0] + 0.5))

    # lost mortar: whole runs of a bed joint eaten out, one step deeper again
    for i in range(26):
        ci = rng.randrange(1, len(courses) - 1)
        x0 = rng.randrange(0, SCENE_W - 40)
        ln = rng.randint(14, 70)
        for x in range(x0, min(SCENE_W, x0 + ln)):
            yy = bounds[ci][x]
            c.set(x, yy, band(COLD, lev(x, yy)[0] - 3.4))
            c.set(x, yy + 1, band(COLD, lev(x, yy)[0] - 1.0))

    # lime runs out of the joints that lost it - solid runs that WIDEN, never
    # 1px scratches (a wall of hairlines reads as damage to the picture)
    for i in range(15):
        wx = rng.randrange(8, SCENE_W - 10)
        if trough(wx, 300) > 0.42 or lev(wx, 300)[0] > 3.6:
            continue
        ci = rng.randrange(0, len(courses) - 6)
        wy = bounds[ci][wx]
        ln = rng.randint(22, 74)
        ph = rng.uniform(0, 6.3)
        for yy in range(wy, min(WALK_Y - 2, wy + ln)):
            t = (yy - wy) / float(ln)
            sx = wx + int(round(1.6 * math.sin(yy / 23.0 + ph)))
            base = lev(sx, yy)[0]
            # they have to READ as a stain, not as a scratch: strong on the
            # dark wall, almost nothing where the shaft is already lighting it
            g = max(0.25, 1.35 - 0.22 * base)
            c.set(sx, yy, band(COLD, base + (0.80 - 0.35 * t) * g))
            if t > 0.30:
                c.set(sx + 1, yy, band(COLD, lev(sx + 1, yy)[0] + 0.58 * g))
            if t > 0.58:
                c.set(sx - 1, yy, band(COLD, lev(sx - 1, yy)[0] + 0.40 * g))
            if t > 0.80:
                c.set(sx + 2, yy, band(COLD, lev(sx + 2, yy)[0] + 0.25 * g))

    # tide lines: the drain has run at four different heights and each left a
    # different stain.  they cross every light band, which is half their job.
    for (ty, thick, dark) in ((392, 2, 2), (430, 4, 1)):
        for x in range(SCENE_W):
            base = ty + int(round(2.4 * math.sin(x / 63.0 + ty)
                                  + 1.3 * math.sin(x / 17.0)))
            if (x + int(41 * math.sin(x / 87.0))) % 37 < 14:
                continue                              # broken, not a stripe
            for yy in range(base, base + thick):
                dim(x, yy, dark)
            dim(x, base - 1, -1)

    # moss where the wall stays wet: solid patches, never dot noise
    wall_low = {(x, y) for y in range(WALK_Y - 46, WALK_Y)
                for x in range(SCENE_W)}
    for i in range(11):
        bx = rng.randrange(10, SCENE_W - 20)
        if trough(bx, WALK_Y - 20) > 0.5:
            continue
        depth = rng.randrange(3, 26)
        for (qx, qy) in blob(rng, bx, WALK_Y - depth, rng.randint(14, 40),
                             wall_low):
            # it grows UP out of the wet, so it thins with height instead of
            # sitting on the brick as a detached speck
            if (WALK_Y - qy) > depth + rng.randint(0, 4):
                continue
            c.set(qx, qy, C("19332d"))
        for k in range(rng.randint(2, 5)):
            c.hline(bx - rng.randint(0, 6), bx + rng.randint(1, 7),
                    WALK_Y - rng.randint(1, 4), C("19332d"))

    # THE SETTLEMENT CRACK.  the left third had 250 px of plain wall between
    # the tunnel mouth and the cache and needed one piece of structure.  a
    # BRICKED-UP ARCH was built here first and thrown away: a wide segmental
    # head over a panel of infill reads as a cylinder standing in front of the
    # wall - it came back looking like a silo, three times, at three different
    # spans.  a crack cannot be mistaken for an object.  it steps along the bed
    # joints and down the perpends the way brick actually fails, the wall has
    # dropped a pixel on the low side, and somebody has strapped it with two
    # iron pattress plates and stopped worrying about it.
    crack = []
    cx, cy = 296.0, WALL_TOP + 6
    while cy < WALK_Y - 2:
        run = rng.randint(5, 14)                     # along a bed joint
        step = -1 if rng.random() < 0.72 else 1
        for k in range(run):
            cx += step
            crack.append((int(cx), int(cy)))
        drop = rng.randint(6, 15)                    # then down a perpend
        for k in range(drop):
            cy += 1
            crack.append((int(cx), int(cy)))
    for i, (qx, qy) in enumerate(crack):
        t = i / float(len(crack))
        w = 1 + int(t * 2.2)
        for k in range(w):
            c.set(qx - k, qy, C("090a14"))
        c.set(qx + 1, qy, wall_col(qx + 1, qy, 1.2))     # the arris that lifted
        if (qy * 3 + qx) % 5 < 3:
            c.set(qx + 2, qy, wall_col(qx + 2, qy, 0.6))
        c.set(qx - w, qy, wall_col(qx - w, qy, -1.6))
        if t > 0.3 and (qy * 5 + qx) % 7 < 3:            # spalled shoulders
            c.set(qx + 3, qy, wall_col(qx + 3, qy, -1.7))
            c.set(qx - w - 1, qy, wall_col(qx - w - 1, qy, 1.2))
    # the two straps, and the tell-tale somebody bedded across the crack
    for (px, py, tilt) in ((272, 196, 1), (252, 318, -1)):
        # a solid iron cross bedded flat on the brick: a lit top-left face, a
        # shadow under the bottom-right, its own drop shadow on the wall, and
        # one boss in the middle with the rust that has run out of it
        cells = []
        for dy in range(-10, 11):
            for dx in range(-10, 11):
                arm = (abs(dy) <= 3 and abs(dx) <= 10) or (abs(dx) <= 3 and abs(dy) <= 10)
                if not arm or abs(dx) + abs(dy) > 13:
                    continue
                cells.append((dx, dy))
        for (dx, dy) in cells:                       # the drop shadow first
            c.set(px + dx + 2, py + dy + 2, wall_col(px + dx + 2, py + dy + 2, -2.6))
        for (dx, dy) in cells:
            cl, _ = lev(px + dx, py + dy)
            edge = ((dx + tilt, dy) not in cells) or ((dx, dy - 1) not in cells)
            low = ((dx, dy + 1) not in cells)
            b = 2.3 if edge else (1.3 if (dx + dy) < 0 else 0.5)
            if low:
                b = -1.4
            b += (0.0, 0.2, -0.22)[(dx * 5 + dy * 3) % 3]
            c.set(px + dx, py + dy, band(COLD, cl + b))
        c.rect(px - 3, py - 3, px + 3, py + 3, band(COLD, lev(px, py)[0] + 2.2))
        c.rect(px - 2, py - 2, px + 2, py + 2, band(COLD, lev(px, py)[0] + 0.9))
        c.hline(px - 3, px + 3, py + 4, C("090a14"))
        c.rect(px - 1, py - 1, px + 1, py + 1, C("602c2c"))
        c.set(px, py, C("341c27"))
        for dy in range(5, rng.randint(11, 22)):     # a rust run off the boss
            c.set(px, py + dy, C("341c27") if dy > 9 else C("602c2c"))
            if dy > 12:
                c.set(px + 1, py + dy, C("241527"))

    # debris washed up against the wall: silt, a broken slab, caught sticks
    for x in range(392, 486):
        u = (x - 392) / 94.0
        h = int(15 * math.sin(u * math.pi) ** 0.7
                + 2.0 * math.sin(x / 4.0) + 1.4 * math.sin(x / 11.0))
        for yy in range(WALK_Y - h, WALK_Y + 3):
            c.set(x, yy, band(COLD, lev(x, yy)[0] - 0.6
                              + (0.0, 0.3, -0.25)[(x * 3 + yy * 5) % 3]))
        if h > 2:
            c.set(x, WALK_Y - h, band(COLD, lev(x, WALK_Y - h)[0] + 0.8))
    for i in range(7):                               # sticks caught in it
        sx = rng.randrange(396, 470)
        sy = WALK_Y - rng.randint(0, 9)
        ln = rng.randint(7, 22)
        dy = rng.choice((-1, 0, 0, 1))
        for k in range(ln):
            c.set(sx + k, sy + (k * dy) // 6, C("341c27") if i % 2 else C("241527"))
    c.rect(432, WALK_Y - 19, 452, WALK_Y - 8,        # a broken slab on edge
           band(COLD, lev(442, WALK_Y - 14)[0] + 0.3))
    c.hline(432, 452, WALK_Y - 19, band(COLD, lev(442, WALK_Y - 19)[0] + 1.4))
    c.vline(452, WALK_Y - 19, WALK_Y - 8, C("090a14"))
    c.hline(430, 453, WALK_Y - 7, C("090a14"))

    # ------------------------------------------------------ the left arch ---
    # the main drain carries on into the dark: half an arch cut by the frame,
    # a voussoir ring round it, and the channel running away underneath
    ACX, ACY, ARX, ARY = 18, 308, 168, 162
    RING = 17

    def arch_x(yv):
        """the intrados' right-hand x at height yv (None above the crown)"""
        if yv > ACY:
            return ACX + ARX
        d = 1.0 - ((ACY - yv) / float(ARY)) ** 2
        if d <= 0.0:
            return None
        return ACX + ARX * d ** 0.5

    for yv in range(int(ACY - ARY) - RING - 2, WALK_Y):
        ax = arch_x(yv)
        if ax is None:
            continue
        ai = int(round(ax))
        for x in range(0, min(SCENE_W, ai)):
            c.set(x, yv, C("090a14"))
        # the voussoir ring: radial bricks, each with its own tone
        for k in range(RING):
            x = ai + k
            if not (0 <= x < SCENE_W):
                continue
            ang = math.atan2(max(0.0, ACY - yv) / float(ARY),
                             (x - ACX) / float(ARX))
            seg = int(ang * 15.0)
            vo = (0.0, 0.30, -0.28, 0.14, -0.44, 0.22)[seg % 6]
            cl, _ = lev(x, yv)
            b = vo
            if k == 0:
                b += 1.0                              # the arris catches light
            elif k == RING - 1:
                b -= 1.4
            if abs(ang * 15.0 - round(ang * 15.0)) < 0.055:
                b -= 2.2                              # radial joint
            c.set(x, yv, band(COLD, cl + b - 0.15))
    # the drain carries on in there: the benching, the channel and a second
    # arch ring, all at the bottom of the ramp.  the first cut left this a
    # 300x300 hole of dead black, which is the same complaint as the old scene
    for x in range(0, 186):
        ax = arch_x(WALK_Y - 1)
        if ax is None or x >= ax:
            continue
        d = 1.0 - x / 200.0
        c.set(x, WALK_Y - 3, C("151d28") if d > 0.55 else C("10141f"))
        for yy in range(WALK_Y - 2, KERB_Y - 6):
            c.set(x, yy, C("10141f") if (x + yy) % 5 else C("151d28"))
        for yy in range(KERB_Y - 6, WATER_Y - 4):
            c.set(x, yy, C("090a14"))
    for i in range(30):                              # glints far up the invert
        gx = rng.randrange(4, 150)
        gy = rng.randrange(WATER_Y - 12, WATER_Y - 5)
        c.hline(gx, gx + rng.randint(1, 5), gy, C("151d28"))
    for yv in range(int(ACY - ARY) + 40, WALK_Y - 4):
        ax = arch_x(yv)
        if ax is None:
            continue
        # the wall a long way in.  COURSE LINES ONLY, broken: the first cut
        # scattered single pixels in here and that is the one texture this
        # project bans outright - it read as dust on the screen.
        if yv % 7:
            continue
        far = (int(round(ACX - 46 + (ARX - 58)
                         * max(0.0, 1.0 - ((ACY - yv) / float(ARY - 44)) ** 2) ** 0.5))
               if yv <= ACY else ACX + ARX - 58)
        x = -rng.randint(0, 14)
        while x < min(int(ax) - 6, far):
            ln = rng.randint(7, 26)
            if x >= 0:
                c.hline(x, min(min(int(ax) - 7, far - 1), x + ln), yv, C("10141f"))
            x += ln + rng.randint(4, 17)
    # a second ring further in, a ghost, so the hole has depth
    for yv in range(int(ACY - ARY) + 26, WALK_Y - 8):
        d = 1.0 - ((ACY - yv) / float(ARY - 30)) ** 2 if yv <= ACY else 1.0
        if d <= 0.0:
            continue
        gi = int(round(ACX - 30 + (ARX - 34) * d ** 0.5))
        for k in range(5):
            if 0 <= gi + k < SCENE_W:
                c.set(gi + k, yv, C("151d28") if k < 2 else C("10141f"))
    # roots through a burst joint just outside the arch
    # a root has come through a joint and burst it: a compact mass hanging out
    # of the wall with a few strands under it, all falling the same way.  the
    # first cut sprayed nine strands radially from one point and read as a
    # spider.
    rx0, ry0 = 198, 292
    for (qx, qy) in blob(rng, rx0, ry0, 58,
                         {(a, b) for b in range(284, 306) for a in range(188, 218)}):
        c.set(qx, qy, C("341c27") if (qx * 3 + qy) % 4 else C("19332d"))
    c.hline(rx0 - 9, rx0 + 13, 284, C("090a14"))
    for i in range(6):
        wpx = float(rx0 + rng.randint(-8, 12))
        wpy = float(302 + rng.randint(-3, 3))
        a = math.pi / 2 + rng.uniform(-0.55, 0.55)
        for t in range(rng.randint(12, 34)):
            wpx += math.cos(a)
            wpy += math.sin(a)
            a += rng.uniform(-0.13, 0.13)
            a = max(0.7, min(2.45, a))
            th = 2 if t < 11 else 1
            for k in range(th):
                c.set(int(wpx) + k, int(wpy),
                      C("341c27") if t < 9 else (C("241527") if t < 20
                                                 else C("19332d")))

    # ------------------------------------------------------- the pipe run ---
    def pipe_y(x):
        return 176 + (x - 636) // 24

    PIPE = (-3.0, 0.6, 2.1, 1.4, 0.5, -0.2, -1.0, -1.9, -2.6, -3.4)
    for x in range(636, SCENE_W):
        py = pipe_y(x)
        cl, _ = lev(x, py + 4)
        for k, b in enumerate(PIPE):
            c.set(x, py - 1 + k, band(COLD, cl + b))
    for bx in (664, 748, 836, 926):                  # saddles up to the wall
        bx += rng.randint(-9, 9)
        py = pipe_y(bx)
        for x in range(bx - 5, bx + 6):
            cl, _ = lev(x, py + 4)
            c.set(x, py - 4, band(COLD, cl + 0.9))
            c.set(x, py - 3, band(COLD, cl - 0.2))
            c.set(x, py - 2, band(COLD, cl - 1.6))
            for k, b in enumerate(PIPE):
                c.set(x, py - 1 + k, band(COLD, cl + b - 0.7))
        c.vline(bx - 6, py - 4, py + 8, C("090a14"))
        c.vline(bx + 6, py - 4, py + 8, C("090a14"))
    for cx in (700, 802, 900):                       # socket collars
        cx += rng.randint(-11, 11)
        py = pipe_y(cx)
        for x in range(cx, cx + 7):
            cl, _ = lev(x, py + 4)
            for k, b in enumerate(PIPE):
                c.set(x, py - 2 + k, band(COLD, cl + b + (0.5 if k < 4 else 0.0)))
            c.set(x, py - 3, band(COLD, cl - 2.2))
            c.set(x, py + 8, band(COLD, cl - 3.2))
        for k in range(rng.randint(2, 3)):           # rust runs off the collar
            sx = cx + rng.randint(0, 6)
            ln = rng.randint(6, 17)
            for yy in range(py + 8, py + 8 + ln):
                u = (yy - py - 8) / float(ln)
                c.set(sx, yy, C("602c2c") if u < 0.35 else C("341c27"))
                if u < 0.55:
                    c.set(sx + 1, yy, C("341c27"))
                else:
                    c.set(sx - 1, yy, C("241527"))
    # a thin conduit dropping to a junction box
    for x in range(636, 786):
        c.set(x, 206, band(COLD, lev(x, 206)[0] - 1.6))
        c.set(x, 207, band(COLD, lev(x, 207)[0] + 0.6))
        c.set(x, 208, band(COLD, lev(x, 208)[0] - 2.2))
    for yy in range(200, 220):
        for x in range(786, 806):
            cl, _ = lev(x, yy)
            b = 0.9 if x < 790 or yy < 203 else (-1.6 if yy > 216 else -0.3)
            c.set(x, yy, band(COLD, cl + b))
    c.hline(786, 806, 199, C("090a14"))
    c.hline(786, 806, 220, C("090a14"))
    c.set(795, 210, C("394a50"))

    # bolt scars: a bracket was here and somebody took it
    for yy in range(300, 338):
        rag = int(round(1.6 * math.sin(yy / 5.0) + 1.1 * math.sin(yy / 13.0)))
        for x in range(668 + rag, 708 - rag):
            c.set(x, yy, wall_col(x, yy, 0.45))      # cleaner brick, not a slab
    for (hx, hy) in ((672, 304), (703, 304), (672, 333), (703, 333)):
        c.rect(hx, hy, hx + 1, hy + 1, C("10141f"))
        c.set(hx, hy + 2, wall_col(hx, hy + 2, -1.2))
        c.set(hx, hy - 1, wall_col(hx, hy - 1, 0.9))
        for yy in range(hy + 2, hy + 2 + rng.randint(5, 11)):
            c.set(hx, yy, C("341c27") if yy > hy + 5 else C("602c2c"))

    # ---------------------------------------------------------- the penstock
    # a cast-iron gate over a side inlet: frame, guides, a plate cracked open,
    # a rising spindle up to a headstock and a handwheel
    IX0, IX1, IY0, IY1 = 792, 852, 384, WALK_Y
    GATE_BOT, GATE_TOP = 414, 316                    # the plate, cracked open
    for yy in range(IY0, IY1):
        for x in range(IX0, IX1):
            c.set(x, yy, C("090a14"))
    for x in range(IX0, IX1):                        # the throat's own arch
        d = 1.0 - ((x - (IX0 + IX1) / 2.0) / ((IX1 - IX0) / 2.0)) ** 2
        ty = IY0 + int(10 * (1.0 - max(0.0, d) ** 0.5))
        for yy in range(IY0, ty):
            c.set(x, yy, band(COLD, lev(x, yy)[0] - 1.4))
    for k in range(9):                               # the frame flanges
        for yy in range(GATE_TOP - 18, IY1):
            for x in (IX0 - 9 + k, IX1 + 8 - k):
                cl, _ = lev(x, yy)
                b = 2.0 if k < 3 else (0.2 if k < 6 else -2.2)
                c.set(x, yy, band(COLD, cl + b))
    for yy in range(GATE_TOP - 18, GATE_TOP - 10):   # the guides' head beam
        for x in range(IX0 - 9, IX1 + 9):
            cl, _ = lev(x, yy)
            c.set(x, yy, band(COLD, cl + (1.9 if yy < GATE_TOP - 15 else -0.8)))
    for yy in range(IY0 - 10, IY0 - 4):              # the throat's own lintel
        for x in range(IX0 - 12, IX1 + 12):
            cl, _ = lev(x, yy)
            c.set(x, yy, band(COLD, cl + (1.4 if yy < IY0 - 7 else -1.2)))
    for by in range(IY0 - 6, IY1 - 6, 26):           # bolt bosses
        for x in (IX0 - 6, IX1 + 5):
            c.rect(x, by, x + 2, by + 2, band(COLD, lev(x, by)[0] + 2.4))
            c.set(x + 1, by + 3, C("090a14"))
            for yy in range(by + 4, by + 4 + rng.randint(4, 12)):
                c.set(x + 1, yy, C("341c27") if yy > by + 7 else C("602c2c"))
    PL0, PL1 = IX0 - 2, IX1 + 1
    for yy in range(GATE_TOP, GATE_BOT):
        v = (yy - GATE_TOP) / float(GATE_BOT - GATE_TOP)
        for x in range(PL0, PL1 + 1):
            cl, _ = lev(x, yy)
            b = 1.35 - 1.25 * ((x - PL0) / float(PL1 - PL0)) - 0.75 * v
            c.set(x, yy, band(COLD, cl + b))
    for ry in (GATE_TOP + 2, GATE_TOP + 38, GATE_TOP + 74):   # stiffeners
        for x in range(PL0, PL1 + 1):
            cl, _ = lev(x, ry)
            u = (x - PL0) / float(PL1 - PL0)
            c.set(x, ry - 1, band(COLD, cl + 2.5 - 1.1 * u))
            c.set(x, ry, band(COLD, cl + 1.7 - 1.1 * u))
            c.set(x, ry + 1, band(COLD, cl + 0.2 - 1.1 * u))
            c.set(x, ry + 2, band(COLD, cl - 1.9))
    for vx in (PL0 + 17, PL1 - 16):                  # vertical stiffeners
        for yy in range(GATE_TOP + 4, GATE_BOT - 2):
            cl, _ = lev(vx, yy)
            c.set(vx, yy, band(COLD, cl + 1.9 - 0.7 * (yy - GATE_TOP) / 100.0))
            c.set(vx + 1, yy, band(COLD, cl + 0.6))
            c.set(vx + 2, yy, band(COLD, cl - 1.7))
    for yy in range(GATE_TOP + 6, GATE_BOT - 4, 11):  # the rivet lines
        for x in (PL0 + 4, PL1 - 3):
            cl, _ = lev(x, yy)
            c.set(x, yy, band(COLD, cl + 2.2))
            c.set(x, yy + 1, band(COLD, cl - 1.3))
    for i in range(7):                               # wear, in solid patches
        for (qx, qy) in blob(rng, rng.randrange(PL0 + 3, PL1 - 3),
                             rng.randrange(GATE_TOP + 4, GATE_BOT - 4),
                             rng.randint(6, 19),
                             {(a, b) for b in range(GATE_TOP, GATE_BOT)
                              for a in range(PL0, PL1 + 1)}):
            cl, _ = lev(qx, qy)
            c.set(qx, qy, band(COLD, cl - 0.5) if i % 2 else C("241527"))
    c.rect(816, GATE_TOP - 4, 820, GATE_TOP + 2,     # the lifting lug
           band(COLD, lev(818, GATE_TOP)[0] + 1.8))
    c.set(818, GATE_TOP - 3, C("090a14"))
    c.vline(PL0, GATE_TOP, GATE_BOT - 1, band(COLD, lev(PL0, GATE_TOP)[0] + 2.4))
    c.vline(PL1, GATE_TOP, GATE_BOT - 1, band(COLD, lev(PL1, GATE_TOP)[0] - 1.9))
    c.hline(PL0, PL1, GATE_TOP, band(COLD, lev(PL0, GATE_TOP)[0] + 2.6))
    c.hline(PL0, PL1, GATE_BOT - 2, band(COLD, lev(PL0, GATE_BOT)[0] - 1.6))
    c.hline(PL0, PL1, GATE_BOT - 1, band(COLD, 4.6))  # wet lip, water leaving
    c.hline(PL0, PL1, GATE_BOT, C("090a14"))
    for yy in range(246, GATE_TOP + 2):              # the rising spindle
        cl, _ = lev(818, yy)
        c.set(817, yy, band(COLD, cl + 0.4))
        c.set(818, yy, band(COLD, cl + 2.6))
        c.set(819, yy, band(COLD, cl + 0.6))
        if yy % 5 == 0:                          # the thread
            c.set(817, yy, band(COLD, cl - 1.4))
            c.set(819, yy, band(COLD, cl + 1.8))
    for x in range(IX0 - 4, IX1 + 5):                # the headstock bridge
        cl, _ = lev(x, 242)
        c.set(x, 240, band(COLD, cl + 2.4))
        c.set(x, 241, band(COLD, cl + 1.3))
        c.set(x, 242, band(COLD, cl + 0.2))
        c.set(x, 243, band(COLD, cl - 2.4))
    for lx in (IX0 - 1, IX1 - 1):                    # its legs
        for yy in range(244, GATE_TOP - 4):
            cl, _ = lev(lx, yy)
            c.set(lx, yy, band(COLD, cl + 2.0))
            c.set(lx + 1, yy, band(COLD, cl - 0.4))
    for a in range(0, 360, 4):                       # the handwheel
        ra = math.radians(a)
        for r in (13, 14):
            wx = int(round(818 + math.cos(ra) * r))
            wy = int(round(226 + math.sin(ra) * r * 0.94))
            cl, _ = lev(wx, wy)
            c.set(wx, wy, band(COLD, cl + (2.6 if math.sin(ra) < 0 else 0.6)))
    for a in (18, 102, 198, 288):
        ra = math.radians(a)
        for r in range(3, 13):
            wx = int(round(818 + math.cos(ra) * r))
            wy = int(round(226 + math.sin(ra) * r * 0.94))
            c.set(wx, wy, band(COLD, lev(wx, wy)[0] + 1.6))
    c.rect(816, 224, 820, 228, band(COLD, lev(818, 226)[0] + 2.2))
    c.set(818, 226, C("090a14"))
    # the leak: a sheet out from under the plate, down the throat
    # the leak.  the first cut was a hatched FIELD and it read as a grille
    # bolted over the inlet; it is falling water now - vertical strokes, each
    # its own length and brightness, breaking up as they drop.
    for k in range(17):
        wx = rng.randrange(IX0 + 2, IX1 - 3)
        y0 = GATE_BOT + 1 + rng.randint(0, 4)
        ln = rng.randint(12, IY1 - GATE_BOT)
        wide = rng.random() < 0.45
        broke = y0 + int(ln * rng.uniform(0.45, 0.95))
        for yy in range(y0, min(IY1, y0 + ln)):
            t = (yy - GATE_BOT) / float(IY1 - GATE_BOT)
            if yy > broke and (yy * 5 + wx) % 7 < 4:
                continue
            c.set(wx, yy, band(COLD, 3.6 - 1.4 * t))
            if wide and yy < broke:
                c.set(wx + 1, yy, band(COLD, 2.6 - 1.2 * t))
    c.hline(IX0 + 2, IX1 - 2, GATE_BOT + 1, band(COLD, 4.4))

    # ----------------------------------------------------- cables, left ----
    for (y0, hooks, tone) in ((176, (44, 158, 276), 0), (196, (52, 168, 288), 1)):
        for i in range(len(hooks) - 1):
            x0, x1 = hooks[i], hooks[i + 1]
            for x in range(x0, x1):
                t = (x - x0) / float(x1 - x0)
                sy = y0 + int(round(math.sin(t * math.pi) * (13 + 5 * tone)))
                c.set(x, sy, C("10141f"))
                c.set(x, sy + 1, C("090a14"))
        for hx in hooks:
            for yy in range(y0 - 5, y0 + 2):
                c.set(hx, yy, band(COLD, lev(hx, yy)[0] + 0.9))
            c.set(hx + 1, y0 - 5, band(COLD, lev(hx, y0)[0] + 0.9))
            c.set(hx + 2, y0 - 4, band(COLD, lev(hx, y0)[0] - 1.4))

    # ------------------------------------------------- the manhole shaft ----
    # cut LAST of the wall work so nothing paints over the throat
    for yy in range(0, WALL_TOP + 4):
        for x in range(SHAFT_X - 29, SHAFT_X + 30):
            c.set(x, yy, C("090a14"))
    for yy in range(0, WALL_TOP + 4):                # its brick lining
        t = min(1.0, yy / 74.0)
        for x in range(SHAFT_X - 29, SHAFT_X + 30):
            dx = x - SHAFT_X
            # the near face of the chimney is lit from the sky above and dies
            # downward; the far side of the throat stays a step back
            cl = 2.55 - 1.75 * t - abs(dx) / 21.0 + (0.45 if dx < 0 else -0.30)
            row = (yy + (5 if dx > 0 else 0)) // 8
            if (yy + (5 if dx > 0 else 0)) % 8 == 0:
                cl -= 1.7
            elif (x * 3 + row * 19) % 21 == 0:
                cl -= 1.4
            elif (yy + (5 if dx > 0 else 0)) % 8 == 1:
                cl += 0.45
            cl += (0.0, 0.22, -0.20, 0.12, -0.30)[(x * 7 + row * 5) % 5]
            c.set(x, yy, band(COLD, cl))
    for dx in range(-24, 25):                        # the open cover ring
        dy = int((1.0 - (dx / 24.0) ** 2) ** 0.5 * 7)
        for yy in range(13 - dy, 13 + dy):
            c.set(SHAFT_X + dx, yy, C("172038"))     # the night up there
        c.set(SHAFT_X + dx, 13 + dy, C("577277"))
        c.set(SHAFT_X + dx, 13 - dy, C("394a50"))
        c.set(SHAFT_X + dx, 12 + dy, C("819796"))
    c.set(SHAFT_X - 9, 9, C("c7cfcc"))               # one star
    c.set(SHAFT_X + 13, 17, C("a8b5b2"))
    for x in range(SHAFT_X + 14, SHAFT_X + 54):      # the cover, slid aside
        d = (x - (SHAFT_X + 14)) / 40.0
        h = int(4 * (1.0 - abs(d - 0.5) * 0.7))
        for yy in range(6 - h, 6 + h):
            c.set(x, yy, C("202e37") if yy < 6 else C("151d28"))
        c.set(x, 6 + h, C("090a14"))
        c.set(x, 6 - h, C("394a50"))

    # ------------------------------------------------------- the ladder ----
    LX0, LX1 = SHAFT_X + 7, SHAFT_X + 21
    LTOP, LBOT = 18, WALK_Y - 2
    for yy in range(LTOP, LBOT):
        t = (yy - LTOP) / float(LBOT - LTOP)
        cl, _ = lev(LX0, yy)
        # the foot of the run has been standing in the water for decades, so
        # it loses its highlight and thins - it does NOT turn into a dashed
        # orange line, which is what the first cut did and it read as noise
        eaten = 0.0 if t < 0.88 else (t - 0.88) / 0.12
        c.set(LX0 - 1, yy, band(COLD, cl - 2.2))
        c.set(LX0, yy, band(COLD, cl + 1.5 - 1.1 * eaten))
        c.set(LX0 + 1, yy, band(COLD, cl - 0.7 - 0.5 * eaten))
        c.set(LX1 - 1, yy, band(COLD, cl + 1.1 - 0.9 * eaten))
        c.set(LX1, yy, band(COLD, cl - 1.5))
        c.set(LX1 + 1, yy, band(COLD, cl - 1.9))
        if eaten > 0.3 and (yy * 3) % 7 < 3:
            c.set(LX0 + 1, yy, C("341c27"))
    rung_i = 0
    for ry in range(LTOP + 8, LBOT - 4, 13):         # the pitch is real: regular
        rung_i += 1
        cl, _ = lev(LX0, ry)
        gone = rung_i == 17
        bent = rung_i in (9, 24)
        rust = rng.random() < 0.17
        if gone:                                     # only the two stubs left
            c.hline(LX0 + 1, LX0 + 3, ry, C("602c2c"))
            c.hline(LX1 - 3, LX1 - 1, ry, C("884b2b"))
            c.set(LX0 + 1, ry + 1, C("341c27"))
            continue
        for x in range(LX0 + 1, LX1):
            u = (x - LX0) / float(LX1 - LX0)
            dy = int(round(1.6 * math.sin(u * math.pi))) if bent else 0
            top = band(COLD, cl + (0.8 if rust else 1.6))
            if rust and (x * 5 + rung_i * 3) % 7 < 2:
                top = C("602c2c") if (x + rung_i) % 8 < 4 else C("341c27")
            c.set(x, ry + dy, top)
            c.set(x, ry + 1 + dy, band(COLD, cl - (1.9 if rust else 1.4)))
        if rung_i % 4 == 1:                          # a fixing plate + its rust
            c.rect(LX1 + 1, ry - 2, LX1 + 5, ry + 3, band(COLD, cl + 0.6))
            c.set(LX1 + 5, ry - 2, C("090a14"))
            c.hline(LX1 + 1, LX1 + 5, ry + 4, C("090a14"))
            for yy in range(ry + 4, ry + 4 + rng.randint(5, 16)):
                c.set(LX1 + 3, yy, C("341c27") if yy > ry + 8 else C("602c2c"))

    # ------------------------------------------------------- the benching --
    # THE POOL IS NOT AN ELLIPSE.  the cover is only slid half aside, so the
    # light that gets down here is a lopsided patch with a bite out of its
    # right-hand side, and its edge wobbles instead of describing an arc.  the
    # benching's own joints and cracks then cut across it - which is the whole
    # reason dim() had to learn both ramps, because the lantern's pool is warm
    # and every one of those cuts used to stop dead at it.
    def pool_at(x, yy):
        bx = (x - SHAFT_X) / (196.0 if x < SHAFT_X else 138.0)
        bx += 0.09 * math.sin(yy / 5.0)
        by = (yy - 471) / 21.0
        return max(0.0, 1.0 - bx * bx - by * by
                   + 0.17 * math.sin(x / 41.0) + 0.10 * math.sin(x / 17.0)
                   + 0.07 * math.sin(x / 6.0))

    for yy in range(WALK_Y, KERB_Y):
        for x in range(SCENE_W):
            t = (yy - WALK_Y) / float(KERB_Y - WALK_Y)
            pool = pool_at(x, yy)
            lx = abs(x - LANT[0])
            wp = max(0.0, 1.0 - (lx / 118.0) ** 2 - ((yy - 474) / 21.0) ** 2
                     + 0.20 * math.sin(x / 37.0) + 0.13 * math.sin(x / 11.0)
                     + 0.08 * math.sin(x / 5.0))
            wp *= min(1.0, max(0.0, (374 - x) / 48.0))
            sq = 1.0 - trough(x, 400) * 0.8
            lv = 1.05 + 0.75 * t + pool * 4.7 * sq
            if wp * 5.4 > lv - 0.7 and wp > 0.05:
                c.set(x, yy, band(WARM, 1.0 + wp * 5.6 + 0.5 * t))
            else:
                c.set(x, yy, band(COLD, lv))
    c.hline(0, SCENE_W - 1, WALK_Y, C("090a14"))     # the wall's own shadow
    for x in range(SCENE_W):
        dim(x, WALK_Y + 1, 1)
    # the ladder's rungs throw bars across the pool, thrown right because the
    # shaft is open on its left
    for i in range(9):
        sy = WALK_Y + 2 + i * 4
        if sy >= KERB_Y - 1:
            break
        off = int((sy - WALK_Y) * 1.15)
        for x in range(SHAFT_X + 5 + off, SHAFT_X + 23 + off):
            for yy in range(sy, min(KERB_Y, sy + 2)):
                dim(x, yy, 2)
    for yy in range(WALK_Y + 2, KERB_Y):             # the stiles' own shadows
        off = int((yy - WALK_Y) * 1.15)
        dim(SHAFT_X + 7 + off, yy, 2)
        dim(SHAFT_X + 8 + off, yy, 1)
        dim(SHAFT_X + 21 + off, yy, 2)
    # benching structure: a longitudinal joint, unit joints, cracks
    for x in range(SCENE_W):
        jy = WALK_Y + 12 + int(round(1.4 * math.sin(x / 71.0)))
        if (x + int(7 * math.sin(x / 29.0))) % 41 > 3:
            dim(x, jy, 2)
            dim(x, jy + 1, -1)
    jx = -rng.randint(0, 40)
    while jx < SCENE_W:
        jx += rng.randint(46, 96)
        for yy in range(WALK_Y + 1, KERB_Y):
            dim(jx, yy, 2)
        dim(jx + 1, WALK_Y + 1, -1)
    for i in range(13):                              # cracks, forked
        cx0 = rng.randrange(20, SCENE_W - 20)
        cy0 = WALK_Y + rng.randint(2, 8)
        a = math.pi / 2 + rng.uniform(-0.5, 0.5)
        fx, fy = float(cx0), float(cy0)
        for t in range(rng.randint(12, 28)):
            fx += math.cos(a)
            fy += math.sin(a)
            a += rng.uniform(-0.22, 0.22)
            if fy >= KERB_Y:
                break
            dim(int(fx), int(fy), 2)
    # the nosing, and the channel wall under it
    for x in range(SCENE_W):
        hit = RAMP_AT.get(c.get(x, KERB_Y - 2))
        r, base = hit if hit else (COLD, 2)
        c.set(x, KERB_Y - 1, r[min(len(r) - 1, base + 1)])
        c.set(x, KERB_Y, C("090a14"))
        for yy in range(KERB_Y + 1, WATER_Y):
            t = (yy - KERB_Y) / float(WATER_Y - KERB_Y)
            c.set(x, yy, r[max(0, min(len(r) - 1,
                                      int(base - 1.2 - 1.9 * t + 0.5)))])
    ux = -rng.randint(0, 30)
    while ux < SCENE_W:                              # the channel wall's units
        ux += rng.randint(28, 62)
        for yy in range(KERB_Y + 1, WATER_Y):
            c.set(ux, yy, C("090a14"))
        dim(ux + 1, KERB_Y + 1, -1)
    for i in range(22):                              # spalls off its face
        sx = rng.randrange(6, SCENE_W - 8)
        sy = rng.randrange(KERB_Y + 2, WATER_Y - 2)
        for (qx, qy) in blob(rng, sx, sy, rng.randint(4, 12),
                             {(a, b) for b in range(KERB_Y + 1, WATER_Y)
                              for a in range(SCENE_W)}):
            dim(qx, qy, 1 if (qx + qy) % 3 else 2)
    for x in range(SCENE_W):                         # slime at the waterline
        k = (x + int(19 * math.sin(x / 37.0)) + int(7 * math.sin(x / 11.0)))
        if k % 67 < 26:
            c.set(x, WATER_Y - 2, C("19332d"))
            if k % 67 < 17:
                c.set(x, WATER_Y - 1, C("19332d"))

    # the silt fan the penstock has washed out across the benching
    for x in range(IX0 - 16, IX1 + 17):
        d = abs(x - (IX0 + IX1) / 2.0) / 46.0
        h = int((KERB_Y - WALK_Y) * max(0.0, 1.0 - d * d)
                + 2.2 * math.sin(x / 5.0) + 1.6 * math.sin(x / 13.0))
        for yy in range(WALK_Y + 1, min(KERB_Y, WALK_Y + 1 + h)):
            dim(x, yy, 1)
        if 3 < h < KERB_Y - WALK_Y - 1 and (x * 5) % 7 > 1:
            dim(x, WALK_Y + h, -1)

    # ------------------------------------------------------ the cache ------
    # a raider's stash by the ladder, lit by their own lantern (LORE 7)
    def wbox(x0, y0, x1, y1, top, face, side, dark):
        for yy in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                c.set(x, yy, face)
        for x in range(x0, x1 + 1):
            c.set(x, y0, top)
        for yy in range(y0, y1 + 1):
            c.set(x0, yy, side)
        c.hline(x0, x1, y1 + 1, dark)
        c.vline(x1 + 1, y0, y1 + 1, dark)

    # the crate: boards of THREE different widths with their own shadow gaps,
    # a lit top plane and a corner batten.  the first cut ruled a grid of
    # lines across a flat rectangle and read as a hatch in the wall.
    CX0, CX1, CY0, CY1 = 292, 340, 424, 468
    for yy in range(CY0, CY1 + 1):
        for x in range(CX0, CX1 + 1):
            u = (x - CX0) / float(CX1 - CX0)
            c.set(x, yy, band(BRICK, 4.4 - 1.5 * u
                              + (0.0, 0.2, -0.2)[(x * 3 + yy * 7) % 3]))
    for x in range(CX0, CX1 + 1):                    # the top plane
        c.set(x, CY0, band(BRICK, 5.4 - 1.2 * (x - CX0) / float(CX1 - CX0)))
        c.set(x, CY0 + 1, band(BRICK, 4.9 - 1.2 * (x - CX0) / float(CX1 - CX0)))
    bd = CY0 + 2
    for w in (11, 8, 13, 9):
        bd += w
        if bd >= CY1:
            break
        c.hline(CX0, CX1, bd, band(BRICK, 2.0))
        c.hline(CX0, CX1, bd + 1, band(BRICK, 5.0))
    for bx in (CX0 + 3, CX1 - 4):                    # corner battens
        c.vline(bx, CY0 + 2, CY1, band(BRICK, 5.1 if bx < 310 else 3.4))
        c.vline(bx + 1, CY0 + 2, CY1, band(BRICK, 2.6))
    for i in range(5):                               # knocks and wear
        for (qx, qy) in blob(rng, rng.randrange(CX0 + 4, CX1 - 4),
                             rng.randrange(CY0 + 4, CY1 - 4), rng.randint(5, 13),
                             {(a, b) for b in range(CY0 + 2, CY1 + 1)
                              for a in range(CX0, CX1 + 1)}):
            c.set(qx, qy, band(BRICK, 3.0))
    c.hline(CX0, CX1, CY1 + 1, C("090a14"))
    c.vline(CX1 + 1, CY0, CY1 + 1, C("090a14"))
    c.vline(CX0 - 1, CY0, CY1 + 1, C("090a14"))
    # a jerry can beside it, standing a little further forward
    wbox(348, 438, 368, 466, C("394a50"), C("202e37"), C("577277"), C("090a14"))
    c.rect(352, 444, 364, 458, C("151d28"))          # the recessed face
    c.hline(352, 364, 443, C("394a50"))
    c.vline(351, 444, 458, C("394a50"))
    c.rect(356, 434, 360, 437, C("202e37"))          # its cap
    c.set(356, 434, C("577277"))
    # a rolled tarp lying at the front of the ledge, well clear of the lantern
    for i in range(3):
        ty = 470 - i * 5
        for x in range(168, 231):
            wob = int(round(1.1 * math.sin(x / 9.0 + i)))
            for k in range(4):
                c.set(x, ty + wob + k, C("19332d"))
            c.set(x, ty + wob, C("25562e") if i == 2 else C("19332d"))
            c.set(x, ty + wob + 3, C("090a14") if i else C("19332d"))
        for k in range(rng.randint(3, 6)):           # creases, per roll
            fx = rng.randrange(172, 226)
            c.vline(fx, ty - 1, ty + 3, C("25562e"))
    c.hline(166, 232, 475, C("090a14"))
    c.vline(166, 456, 475, C("090a14"))
    c.vline(232, 456, 475, C("090a14"))

    # THE CAST SHADOWS.  a lamp sitting on the floor throws everything near it
    # a long way, and those shadows are what stop the pool being a disc.  each
    # one leaves its object's BASE, spreads as it goes and breaks up at the
    # far end instead of stopping on a straight edge.
    def floor_shadow(ox0, ox1, base, length, right):
        for k in range(length):
            t = k / float(length)
            x = (ox1 + 1 + k) if right else (ox0 - 1 - k)
            if not (0 <= x < SCENE_W):
                continue
            if t > 0.5 and (x * 7 + int(11 * math.sin(x / 4.0))) % 13 < int(11 * t):
                continue
            y0 = base - int(9 * (1.0 - t)) + int(2.0 * math.sin(x / 6.0))
            y1 = min(KERB_Y, base + 4 + int(13 * t))
            for yy in range(max(WALK_Y + 1, y0), y1):
                dim(x, yy, 3 if t < 0.45 else 2)

    floor_shadow(CX0, CX1, 468, 108, True)
    floor_shadow(168, 230, 474, 92, False)
    floor_shadow(348, 368, 466, 74, True)

    # the lantern: the second light source, and it must READ as the source
    lx, ly = LANT
    for dx in range(-13, 14):                        # its own shadow, small
        h = int(3 * (1.0 - (dx / 13.0) ** 2)) + 1
        for yy in range(478 - h, 480 + h):
            dim(lx + dx, yy, 3)
    c.rect(lx - 6, ly - 7, lx + 6, ly + 15, C("341c27"))   # the frame
    c.rect(lx - 5, ly - 4, lx + 5, ly + 10, C("884b2b"))  # the glass belly
    c.rect(lx - 4, ly - 3, lx + 4, ly + 9, C("de9e41"))
    c.rect(lx - 3, ly - 1, lx + 3, ly + 7, C("e8c170"))
    c.rect(lx - 1, ly + 1, lx + 1, ly + 5, C("ebede9"))   # the flame
    for bxk in (lx - 3, lx + 3):                          # the cage bars
        c.vline(bxk, ly - 4, ly + 10, C("602c2c"))
    c.hline(lx - 6, lx + 6, ly - 7, C("ad7757"))          # the top cap
    c.hline(lx - 5, lx + 5, ly - 6, C("884b2b"))
    c.hline(lx - 6, lx + 6, ly - 5, C("4d2b32"))
    c.rect(lx - 2, ly - 11, lx + 2, ly - 8, C("602c2c"))  # the chimney
    c.set(lx - 2, ly - 11, C("884b2b"))
    c.hline(lx - 7, lx + 7, ly + 16, C("602c2c"))         # the foot
    c.hline(lx - 7, lx + 7, ly + 17, C("341c27"))
    c.hline(lx - 8, lx + 8, ly + 18, C("090a14"))
    c.vline(lx - 7, ly + 12, ly + 17, C("341c27"))
    for a in range(196, 345, 8):                          # the wire handle
        ra = math.radians(a)
        c.set(int(lx + math.cos(ra) * 8), int(ly - 12 + math.sin(ra) * 8),
              C("884b2b"))

    # ------------------------------------------------------- the water -----
    def water_top(x):
        return WATER_Y + int(round(1.1 * math.sin(x / 47.0)
                                   + 0.8 * math.sin(x / 19.0 + 1.1)))

    for yy in range(WATER_Y - 3, SCENE_H):
        for x in range(SCENE_W):
            if yy >= water_top(x):
                c.set(x, yy, C("090a14"))

    def refl(x, y):
        t = max(0.0, (y - WATER_Y) / 37.0)
        hw = 42.0 + 128.0 * t
        d = max(0.0, abs(x - SHAFT_X) - hw * 0.22) / (hw * 0.92)
        return max(0.0, 1.0 - d) ** 1.45 * (1.0 - 0.42 * t)

    def refl_w(x, y):
        t = max(0.0, (y - WATER_Y) / 37.0)
        hw = 20.0 + 62.0 * t
        d = max(0.0, abs(x - LANT[0]) - hw * 0.22) / (hw * 0.92)
        return max(0.0, 1.0 - d) ** 1.5 * (1.0 - 0.5 * t)

    yy = WATER_Y - 2
    row = 0
    while yy < SCENE_H:
        t = max(0.0, (yy - WATER_Y) / 37.0)
        step = 2 + int(3.5 * t)                      # the chop opens up nearer
        thick = 1 + int(3.0 * t)
        x = -rng.randint(0, 40)
        while x < SCENE_W:
            ln = int((4 + 26 * t) * rng.uniform(0.4, 1.7))
            gap = int((3 + 20 * t) * rng.uniform(0.4, 1.9))
            top = water_top(x) if 0 <= x < SCENE_W else WATER_Y
            if yy >= top:
                s = refl(x + ln // 2, yy)
                sw = refl_w(x + ln // 2, yy)
                jitter = rng.uniform(-0.35, 0.35)
                for k in range(thick):
                    for px2 in range(x, min(SCENE_W, x + ln)):
                        if px2 < 0 or yy + k >= SCENE_H:
                            continue
                        if yy + k < water_top(px2):
                            continue
                        if sw * 5.0 > s * 4.6 and sw > 0.06:
                            c.set(px2, yy + k,
                                  band(WARM, 1.0 + sw * 5.4 + jitter - 0.6 * k))
                        else:
                            c.set(px2, yy + k,
                                  band(COLD, 0.95 + s * 4.4 + jitter - 0.55 * k))
            x += ln + gap
        yy += step + thick
        row += 1
    # the bright lip right under the surface, broken
    for x in range(SCENE_W):
        top = water_top(x)
        if (x + int(9 * math.sin(x / 13.0))) % 19 < 12:
            s = refl(x, top + 1)
            sw = refl_w(x, top + 1)
            if sw > 0.05 and sw * 5.0 > s * 4.6:
                c.set(x, top, band(WARM, 1.6 + sw * 5.0))
            else:
                c.set(x, top, band(COLD, 1.5 + s * 4.2))

    def wake(x0, x1, wl, warm=False):
        """a broken ring where a thing breaks the surface, and a broken
        reflection under it - the underpass pitch's float_wake, cut down.  the
        first cut ran a 1-in-5 dashed line of 577277 the whole length of every
        object and read as a bright rule laid across the water."""
        hot = C("577277") if not warm else C("884b2b")
        mid = C("202e37") if not warm else C("4d2b32")
        for x in range(x0 - 4, x1 + 5):
            k = (x * 13 + x0 * 7) % 23
            if k < 11:
                continue
            d = 0 if x0 <= x <= x1 else 1
            c.set(x, wl + d, hot if k > 19 else mid)
        # the broken reflection under it.  the first cut stepped k down a
        # column at every x and came back as a comb of vertical ticks; it has
        # to be laid in HORIZONTAL strokes, the way the rest of the chop is.
        for k in range(1, 8):
            x = x0 - 2
            while x < x1 + 3:
                ln = 2 + (x * 7 + k * 5) % 9
                if (x * 13 + k * 29 + x0) % 11 > 4:
                    for px2 in range(x, min(x1 + 3, x + ln)):
                        c.set(px2, wl + k,
                              C("151d28") if k > 3 else C("202e37"))
                x += ln + 1 + (x * 3 + k) % 7

    # three things floating, each cut DEAD LEVEL by the waterline
    pl_y = water_top(320)
    for x in range(286, 362):                        # a plank, lying over
        u = (x - 286) / 76.0
        tilt = int(round(1.6 * u))
        for k in range(6):
            col = (C("884b2b"), C("602c2c"), C("602c2c"),
                   C("4d2b32"), C("341c27"), C("241527"))[k]
            c.set(x, pl_y - 6 + tilt + k, col)
        if (x * 5) % 19 < 2:                         # grain, not dots
            c.vline(x, pl_y - 5 + tilt, pl_y - 1 + tilt, C("4d2b32"))
    c.vline(286, pl_y - 6, pl_y, C("341c27"))        # the end grain
    c.vline(287, pl_y - 6, pl_y, C("4d2b32"))
    c.hline(286, 361, pl_y, C("090a14"))
    wake(286, 361, pl_y, True)
    dr_y = water_top(706)
    for x in range(682, 730):                        # a drum on its side
        d = 1.0 - ((x - 706) / 24.0) ** 2
        h = int(15 * max(0.0, d) ** 0.5)
        for yy in range(dr_y - h, dr_y):
            u = (dr_y - yy) / float(max(1, h))
            c.set(x, yy, band(COLD, 1.2 + 2.6 * u - 1.1 * abs((x - 700) / 24.0)))
        if h > 2 and (x - 682) % 17 == 0:
            c.vline(x, dr_y - h + 1, dr_y - 1, C("602c2c"))
    for x in range(692, 722):
        c.set(x, dr_y - 12, C("884b2b") if (x % 5) else C("602c2c"))
    c.hline(682, 729, dr_y, C("090a14"))
    wake(682, 729, dr_y)
    mt_y = water_top(150)
    for x in range(112, 200):                        # a raft of caught rubbish
        u = (x - 112) / 88.0
        h = int(6 * math.sin(u * math.pi) ** 0.6 + 1.4 * math.sin(x / 5.0)
                + 1.0 * math.sin(x / 13.0))
        for k in range(max(0, h)):
            c.set(x, mt_y - k, C("19332d") if (x + k) % 5 else C("25562e"))
        if h > 1:
            c.set(x, mt_y - h, C("202e37") if (x * 3) % 7 else C("394a50"))
    for i in range(9):                               # sticks and a can in it
        mx = rng.randrange(116, 190)
        my = mt_y - rng.randint(0, 5)
        ln = rng.randint(5, 16)
        c.hline(mx, mx + ln, my, C("341c27") if i % 3 else C("241527"))
        c.set(mx + ln, my - 1, C("4d2b32"))
    c.rect(160, mt_y - 5, 170, mt_y - 1, C("394a50"))
    c.hline(160, 170, mt_y - 5, C("577277"))
    c.vline(170, mt_y - 5, mt_y - 1, C("202e37"))
    c.hline(112, 199, mt_y + 1, C("090a14"))
    wake(112, 199, mt_y)

    # the drip's landing point is an ANCHOR in scripts/main_menu.gd: it falls
    # down x 608 and vanishes at y 508.  if this ever fails the surface moved
    # and the drip is landing in mid-air.
    assert water_top(608) == 508, f"drip anchor moved: {water_top(608)}"

    # -------------------------------------------------- the god-ray overlay -
    rw, rh = 150, 390
    ray = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    rp = ray.load()
    for y in range(rh):
        t = y / float(rh)
        half = 23 + 25 * t
        for x in range(rw):
            ax = abs(x - rw / 2) / half
            if ax < 1.0:
                a = int(70 * (1.0 - ax) ** 1.6 * (1.0 - t * 0.46))
                if t > 0.9:
                    a = int(a * (1.0 + (t - 0.9) * 3.0))
                if a > 0:
                    rp[x, y] = (168, 181, 178, min(255, a))

    # ---------------------------------------------------- the ripple strip --
    strip = Canvas(54, 8)
    for f in range(3):
        ox = f * 18 + 9
        r = 2 + f * 3
        for a in range(0, 360, 11):
            if (a // 11 + f * 3) % 7 < 2:            # broken rings, not ellipses
                continue
            x = int(ox + math.cos(math.radians(a)) * r)
            y = int(4 + math.sin(math.radians(a)) * r * 0.42)
            if f * 18 <= x < f * 18 + 18:
                strip.set(x, y, C("3c5e8b") if f < 2 else C("253a5e"))
        if f == 0:
            strip.set(ox, 3, C("4f8fba"))
    return c, ray, strip


def make_scene_den() -> tuple[Canvas, Image.Image, Canvas]:
    """Menu 2 — THE DEN: the traders' back room in the old transit depot,
    all three of them home. kettle hunched over his scale in the candle light
    (LEFT), verne at his dressing table under the instrument rail
    (CENTRE-RIGHT), mara on the radio at the rack (RIGHT). Two light sources
    own the frame and nothing else lights anything: warm candle left, cold
    screen right.

    REDESIGNED 2026-08-02 on the user's call ("a redesign would be good too
    for these"), to the standard set by tools/pitches/*.py. What changed:

      * MARA IS BUILT FROM tools/pitches/counter.py's CHARACTER SHEET. She
        was a rectangle of jacket with a square hand and one black dot for an
        eye, and the user said so: "in the den, mara doesn't look anything
        like the other mara painting we made". She now carries the same
        design — the dark-red hair mass, the low ponytail, the greying lock,
        the headset with two visible cups (ON her ears here; on the counter
        they are pushed up because she is off-channel), the oxblood jacket
        with its collar and green enamel district pin, and the scar through
        her left brow. Different angle, different scale, same woman.
      * VERNE'S CORNER SAYS MEDIC. He stood at a shelf with four bottles on
        it. He now has his table: an enamel basin he is rinsing in, a stack
        of folded dressings, an instrument tray, a stained cloth, a shelf of
        mismatched bottles and a rail of hung instruments over his head.
      * THE LIGHT IS BANDED CEL WITH WOBBLED SEAMS. It was two smooth
        airbrushed ellipses; every band edge now rides three sines so it
        cannot read as an airbrush.
      * THE DOT NOISE IS GONE — it broke a standing rule in three places:
        the board's 50%-speckle drop shadow, the rug's 6%-holes weave and
        kettle's 110-loose-pixel coin pile. Shadows step DOWN THE RAMP now
        (see `darker`), the rug is woven from stripes, the coins are stacks.
      * The wall is horizontal shiplap with rolled board heights, staggered
        butt joints, per-board tone, knots, splits and nail pairs (it was
        vertical stripes); the floor is depot concrete with wobbled
        expansion joints (the old board rows read as courses of brick).
      * EVERY FIGURE IS CLIPPED AT THE FAR EDGE OF HIS OWN TABLE and his
        arms are drawn again afterwards, so the things on the table sit in
        FRONT of him. The first cut drew each body over the table top and
        buried kettle's coins and every one of verne's instruments.
      * A QUIET PATCH behind the menu buttons (x 396-564, y 272-408): every
        light term, tone bias and bevel is scaled by (1 - quiet) so the wall
        there collapses to one flat value with no rectangular edge anywhere.
        It used to be a full-height COLUMN and that was wrong — see below.

    COLOUR COHESION PASS, 2026-08-02. The user: "the den painting, the blue
    and the brown areas of the screen is too much, like all the colours of
    the screen should be blended together nicely". The frame read as two
    pictures butted together. The four things that fixed it are written out
    in full above the ramp table in the body; the short version is: ONE
    shared neutral ramp under everything, a bounce tail on each lamp that
    crosses the whole frame, chroma scaled by how much light is actually
    present, and the middle turned from a dead gap into the mixing zone.
    The two-source idea is untouched — warm candle left, cold rig right,
    mara's oxblood jacket still the one warm accent in the cool half.

    ANCHORS scripts/main_menu.gd draws onto — NONE MOVED:
      (150, 344) candle flame (additive glow), (334, 372) ashtray (smoke),
      (746, 262) + (814, 272) VU dial faces on the rack, (760, 312) +
      (860, 372) rig pilot LEDs.

    Returns (base, candle-glow overlay, VU-needle strip)."""
    rng = random.Random(f"{SEED}:scene:den")
    c = Canvas(SCENE_W, SCENE_H)

    CEIL = 52
    FLOOR_Y = 430
    CANDLE = (150, 344)                     # the flame — main_menu.gd's anchor
    WARM_SRC = (150, 352)
    COOL_SRC = (752, 322)                   # the rack's big screen
    QX0, QX1 = 396, 564
    QF_L, QF_R = 176, 168                   # how far the wall's TEXTURE fades
    QY0, QY1, QF_T, QF_B = 272, 408, 86, 78  # ...and the strip it is flat over
    LF_L, LF_R = 112, 96                    # how far the LIGHT flattens

    dark_ramp = ["090a14", "10141f", "151d28"]
    warm_ramp = ["10141f", "241527", "341c27", "4d2b32",
                 "7a4841", "ad7757", "c09473"]
    cool_ramp = ["10141f", "172038", "1e1d39", "253a5e", "3c5e8b", "577277"]
    skin_ramp = ["341c27", "4d2b32", "7a4841", "c09473", "d7b594", "e7d5b3"]

    # every big surface gets a TWIN of its own ramp in the other temperature,
    # same length, same step values. mix2() crossfades between the pair by
    # which lamp is actually reaching that pixel, so the far end of kettle's
    # table catches the rig and verne's bench catches the candle. Nothing
    # in the room belongs to only one lamp.
    warm_twin = ["10141f", "172038", "1e1d39", "253a5e", "3c5e8b", "577277",
                 "819796"]
    cool_twin = ["10141f", "241527", "341c27", "4d2b32", "7a4841", "ad7757"]

    # ---- THE ROOM IS ONE ROOM (colour cohesion pass, 2026-08-02) -----------
    # The user: "the blue and the brown areas of the screen is too much, like
    # all the colours of the screen should be blended together nicely". It read
    # as two paintings butted together — a brown one and a blue one with a dead
    # black gap down the middle where quiet() had killed both lamps.
    #
    # What fixes it, and none of it may be undone without the frame splitting
    # in two again:
    #   * ONE SHARED NEUTRAL RAMP (wall_n, Apollo's slate column) is the room's
    #     own material. warm and cool are the SAME ramp at the SAME value with
    #     only the hue moved, so the unlit wall on the left and the unlit wall
    #     on the right are recognisably one wall.
    #   * EACH LAMP HAS A BOUNCE TAIL (the `amb` term) that crosses the whole
    #     frame. The candle reaches the near edge of the rig and the rig reaches
    #     the far end of kettle's table. That, more than anything else, is what
    #     makes two lamps read as being in one space.
    #   * CHROMA IS SCALED BY HOW MUCH LIGHT IS ACTUALLY THERE. Light is most
    #     coloured where it is strongest; far from both lamps the tint washes
    #     out to the shared neutral instead of driving the hue to its extreme.
    #   * THE MIDDLE IS THE MIXING ZONE, not a hole. quiet() no longer fades
    #     the lamps to nothing there — it blends the light field toward ONE
    #     fixed sample of itself (_QREF), so the column behind the buttons is
    #     perfectly flat AND carries the real warm+cool mixture of that spot.
    wall_n = ["090a14", "10141f", "151d28", "202e37", "394a50", "577277",
              "819796"]
    wall_w = ["090a14", "10141f", "241527", "341c27", "4d2b32", "7a4841",
              "ad7757"]
    wall_c = ["090a14", "10141f", "172038", "253a5e", "3c5e8b", "4f8fba",
              "73bed3"]
    AMB, GAIN, TP, CHROMA = -0.19, 3.61, 2.55, 0.72

    # every ramp colour knows the colour one step below it, so a cast shadow
    # can be a real STEP DOWN over whatever it falls on instead of a speckle
    darker: dict = {}
    for _r in (dark_ramp, wall_n, wall_w, wall_c, warm_ramp, cool_ramp):
        for _i in range(len(_r) - 1, 0, -1):
            darker.setdefault(C(_r[_i])[:3], C(_r[_i - 1]))

    # the snap pool: mixing two ramps lands between palette entries, so the
    # result is pulled back onto Apollo. Kept to the slate / brown / blue
    # families on purpose — a free nearest-match over all 46 would drag
    # midtones into the greens and pinks.
    snap_pool = [C(h)[:3] for h in (
        "090a14 10141f 151d28 202e37 394a50 577277 819796 241527 341c27 "
        "411d31 4d2b32 602c2c 7a4841 884b2b ad7757 c09473 172038 1e1d39 "
        "253a5e 3c5e8b 4f8fba").split()]
    snap_cache: dict = {}

    def snap(r: float, g: float, b: float):
        k = (int(r) >> 1, int(g) >> 1, int(b) >> 1)
        got = snap_cache.get(k)
        if got is None:
            rr, gg, bb = (k[0] << 1) + 1, (k[1] << 1) + 1, (k[2] << 1) + 1
            got = min(snap_pool, key=lambda p: (p[0] - rr) ** 2 * 3
                      + (p[1] - gg) ** 2 * 6 + (p[2] - bb) ** 2 * 2)
            got = (got[0], got[1], got[2], 255)
            snap_cache[k] = got
        return got

    def _quiet(x: float, fl: float, fr: float) -> float:
        if QX0 <= x <= QX1:
            return 1.0
        d = (QX0 - x) / fl if x < QX0 else (x - QX1) / fr
        if d >= 1.0:
            return 0.0
        return 1.0 - d * d * (3.0 - 2.0 * d)     # smoothstep, so the fade in
                                                 # has no edge of its own

    def quiet(x: int, y: int = 340) -> float:
        """kills the wall's own TEXTURE behind the buttons. Its feather is
        LONG on purpose: a flat column beside a textured wall reads as a
        panel hung there, and a short feather just moves the edge.

        It is a WINDOW, not a full-height column: only the strip the buttons
        actually occupy has to be flat, so above and below it the shiplap
        comes back and the middle of the frame stops reading as an empty
        panel between the two lamps."""
        q = _quiet(x, QF_L, QF_R)
        if q <= 0.0:
            return 0.0
        if QY0 <= y <= QY1:
            return q
        d = (QY0 - y) / float(QF_T) if y < QY0 else (y - QY1) / float(QF_B)
        if d >= 1.0:
            return 0.0
        return q * (1.0 - d * d * (3.0 - 2.0 * d))

    def qlit(x: int) -> float:
        """flattens the LIGHT FIELD to one sample. Shorter than quiet() —
        stretching this one would dim the lamps either side of the band."""
        return _quiet(x, LF_L, LF_R)

    def band(ramp: list, lv: float):
        """Banded cel light — never dithered, never interpolated."""
        return C(ramp[max(0, min(len(ramp) - 1, int(lv + 0.5)))])

    def ramp_at(ramp: list, lv: float):
        """A point ALONG a ramp, between its steps. Only the two mixing
        helpers use this; every cel surface still goes through band()."""
        lv = max(0.0, min(len(ramp) - 1.001, lv))
        i = int(lv)
        f = lv - i
        a, b = C(ramp[i]), C(ramp[i + 1])
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f,
                a[2] + (b[2] - a[2]) * f)

    def _key(d: float, r: float) -> float:
        """the pool itself — tight, and the only thing that is really bright"""
        return max(0.0, min(1.0, 1.0 - d / r)) ** 1.4

    def _bounce(d: float, r: float) -> float:
        """what the room gives back. Weak and DELIBERATELY almost flat, but
        it crosses the whole frame — this is the shared base."""
        return max(0.0, min(1.0, 1.0 - d / r))

    def _raw_lights(x: float, y: float, wobbly: bool = True) -> tuple[float,
                                                                     float]:
        """warm, cool in 0..1. The radius is WOBBLED by three sines of
        different period, so no band seam can ever close into a clean
        ellipse — that is what made the old pools read as airbrush.
        wobbly=False is for the button column's reference sample ONLY: with
        the wobble in, one row of it dipped a step darker than its neighbours
        and printed a dark stripe across the otherwise flat patch."""
        wob = ((9.0 * math.sin(x / 41.0 + 0.7) + 6.0 * math.sin(y / 27.0 + 2.1)
                + 4.5 * math.sin((x + y) / 23.0)) if wobbly else 0.0)
        dw = ((x - WARM_SRC[0]) ** 2
              + ((y - WARM_SRC[1]) * 1.55) ** 2) ** 0.5 + wob
        dc = ((x - COOL_SRC[0]) ** 2
              + ((y - COOL_SRC[1]) * 1.28) ** 2) ** 0.5 - wob
        return ((0.86 * _key(dw, 400.0) + 0.38 * _bounce(dw, 1500.0)) / 1.24,
                (0.86 * _key(dc, 430.0) + 0.38 * _bounce(dc, 1400.0)) / 1.24)

    QCX = (QX0 + QX1) * 0.5
    _qref: dict = {}

    def lights(x: int, y: int) -> tuple[float, float]:
        """Behind the buttons the light field is flattened ACROSS X ONLY —
        every row keeps the height falloff the walls either side have. The
        first cut flattened x and y together and the column then ignored the
        wall's own darkening toward the ceiling, which put a pale slab in the
        top middle of the frame. Across the button band itself the field
        barely moves with y, so the band still comes out one flat colour."""
        w, cl = _raw_lights(x, y)
        q = qlit(x)
        if q > 0.0:
            r = _qref.get(y)
            if r is None:
                r = _raw_lights(QCX, y, False)
                _qref[y] = r
            w += (r[0] - w) * q
            cl += (r[1] - cl) * q
        return w, cl

    def tint(lv: float, warm: float, cool: float):
        """One surface pixel: the shared neutral, pushed toward whichever
        lamp is winning HERE and by how much light there is to push with."""
        tot = warm + cool
        te = ((warm - cool) / max(0.001, tot)) * min(1.0, tot / CHROMA)
        n = ramp_at(wall_n, lv)
        o = ramp_at(wall_w if te >= 0.0 else wall_c, lv)
        k = min(1.0, abs(te))
        return snap(n[0] + (o[0] - n[0]) * k, n[1] + (o[1] - n[1]) * k,
                    n[2] + (o[2] - n[2]) * k)

    def mix2(rw: list, rc: list, lv: float, warm: float, cool: float,
            bias: float = 0.0):
        """A MATERIAL lit by both lamps — its own warm and cool ramps,
        crossfaded by which lamp is actually reaching it. Kettle's table
        catches the rig on its far end; verne's catches the candle."""
        tot = warm + cool
        k = max(0.0, min(1.0, cool / max(0.001, tot) + bias))
        # pulled toward whichever lamp owns the surface: a straight ratio put
        # 40% of a slate ramp through the right-hand end of the job board and
        # it read as a blue STAIN, not as bounce.
        k = k ** 1.6 if k < 0.5 else 1.0 - (1.0 - k) ** 1.6
        a, b = ramp_at(rw, lv), ramp_at(rc, lv)
        return snap(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k,
                    a[2] + (b[2] - a[2]) * k)

    def surface(x: int, y: int, base: float):
        """One wall/floor pixel, on the room's shared ramp."""
        warm, cool = lights(x, y)
        return tint(base + AMB + GAIN * ((warm + cool) ** TP), warm, cool)

    def shade(x0: int, y0: int, x1: int, y1: int, steps: int = 1) -> None:
        """Cast shadow: step whatever is already there DOWN the ramp."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                for _ in range(steps):
                    p = c.get(x, y)[:3]
                    if p in darker:
                        c.set(x, y, darker[p])
                    else:
                        break

    def darken(pts) -> None:
        for (qx, qy) in pts:
            p = c.get(qx, qy)[:3]
            if p in darker:
                c.set(qx, qy, darker[p])

    def soft_shadow(cx: int, cy: int, rx: int, ry: int) -> None:
        """A body's shadow on the boards: one step down inside a WOBBLED
        ellipse. shade() is a rectangle, and behind a person a rectangle
        reads as a dark panel hung on the wall."""
        for dy in range(-ry, ry + 1):
            for dx in range(-rx, rx + 1):
                w = (0.11 * math.sin((cx + dx) / 14.0 + 0.6)
                     + 0.08 * math.sin((cy + dy) / 9.0))
                if (dx / float(rx)) ** 2 + (dy / float(ry)) ** 2 + w < 1.0:
                    x, y = cx + dx, cy + dy
                    p = c.get(x, y)[:3]
                    if p in darker:
                        c.set(x, y, darker[p])

    def box(x0: int, y0: int, x1: int, y1: int, face, lit, shd) -> None:
        """A panel with a section: lit top+left, shaded bottom+right."""
        c.rect(x0, y0, x1, y1, face)
        c.hline(x0, x1, y0, lit)
        c.vline(x0, y0, y1, lit)
        c.hline(x0, x1, y1, shd)
        c.vline(x1, y0, y1, shd)

    def limb(x0, y0, x1, y1, w0, w1, ramp, base, rim_lit, rim_shd,
             across: bool = False) -> None:
        """One arm segment with a section. Stepped 3x its own length so it
        can never come out as a ladder of rungs (the first cut of mara's
        raised arm did exactly that: the step was 1.2 px and the gaps showed
        the screen through her sleeve)."""
        n = max(4, int(max(abs(x1 - x0), abs(y1 - y0)) * 3))
        for k in range(n + 1):
            t = k / float(n)
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            w = w0 + (w1 - w0) * t
            iw = max(1, int(round(w)))
            for d in range(-iw, iw + 1):
                u = (d + iw) / float(2 * iw)
                col = band(ramp, base + (1.0 - u) * 2.2)
                if across:
                    c.set(int(round(x)), int(round(y)) + d, col)
                else:
                    c.set(int(round(x)) + d, int(round(y)), col)
            if across:
                c.set(int(round(x)), int(round(y)) - iw, rim_lit)
                c.set(int(round(x)), int(round(y)) + iw, rim_shd)
            else:
                c.set(int(round(x)) - iw, int(round(y)), rim_lit)
                c.set(int(round(x)) + iw, int(round(y)), rim_shd)

    def hand(hx, hy, up_col, dn_col, rim, shd, n_fing: int = 3,
             down: bool = True) -> None:
        for k in range(12):
            t = k / 12.0
            hw = int(6 - abs(t - 0.4) * 5)
            y = hy + k if down else hy - k
            c.hline(hx - hw, hx + hw, y, up_col if t < 0.45 else dn_col)
            c.set(hx - hw, y, rim)
            c.set(hx + hw, y, shd)
        for k in range(n_fing):
            fx = hx - 3 + k * 3
            if down:
                c.vline(fx, hy + 11, hy + 14, dn_col)
                c.set(fx, hy + 14, shd)
            else:
                c.vline(fx, hy - 14, hy - 11, dn_col)
                c.set(fx, hy - 14, up_col)

    def wobble(x: int, a: float, b: float, p: float, q: float) -> int:
        return int(round(a * math.sin(x / p) + b * math.sin(x / q + 1.7)))

    # ================================================== ceiling =============
    # dark, but never a featureless slab: joists across it, the conduit run
    # that feeds the whole den, and the dead bulb still hanging off it.
    c.rect(0, 0, SCENE_W - 1, CEIL - 1, C("090a14"))
    jx = rng.randint(8, 34)
    while jx < SCENE_W:
        w = rng.randint(7, 11)
        c.rect(jx, 0, jx + w, CEIL - 1, C("151d28"))
        c.vline(jx, 0, CEIL - 1, C("202e37"))
        c.vline(jx + w, 0, CEIL - 1, C("090a14"))
        for _ in range(rng.randint(1, 3)):                   # bolt plates
            by = rng.randrange(6, CEIL - 10)
            c.hline(jx + 1, jx + w - 1, by, C("10141f"))
            c.set(jx + 2 + rng.randrange(max(1, w - 4)), by, C("202e37"))
        jx += rng.randint(92, 152)
    for x in range(SCENE_W):                                 # the conduit
        yy = 38 + wobble(x, 1.1, 0.7, 137.0, 61.0)
        c.set(x, yy, C("394a50"))
        c.set(x, yy + 1, C("202e37"))
        c.set(x, yy + 2, C("151d28"))
        c.set(x, yy + 3, C("090a14"))
    for cx_ in range(26, SCENE_W, 106):                      # its saddle clips
        sx = cx_ + rng.randint(-11, 11)
        c.vline(sx, 32, 40, C("202e37"))
        c.vline(sx + 1, 33, 40, C("151d28"))
    for k in range(30):                                      # the dead bulb
        c.set(298 + (1 if k > 18 else 0), 42 + k, C("151d28"))
    c.rect(295, 72, 301, 76, C("394a50"))
    c.rect(296, 76, 300, 82, C("202e37"))
    c.hline(296, 300, 77, C("151d28"))
    c.set(297, 79, C("394a50"))
    for k in range(22):                                      # a coiled lead
        a = k / 21.0 * math.pi * 3.4
        c.set(int(486 + math.cos(a) * 7), int(20 + k * 0.9), C("10141f"))
    c.hline(0, SCENE_W - 1, CEIL - 3, C("10141f"))           # the wall plate
    c.hline(0, SCENE_W - 1, CEIL - 2, C("151d28"))
    c.hline(0, SCENE_W - 1, CEIL - 1, C("090a14"))

    # ================================================== the boarded wall ====
    # horizontal shiplap: rolled board heights, staggered butt joints, a tone
    # per board, a lit proud lip and a shadow line under every board.
    rows = []
    wy = CEIL
    while wy < FLOOR_Y:
        h = rng.randint(13, 19)
        joints = []
        jj = -rng.randint(0, 90)
        while jj < SCENE_W + 60:
            jj += rng.randint(86, 196)
            joints.append(jj)
        rows.append((wy, min(FLOOR_Y, wy + h), joints, rng.uniform(-0.34, 0.34),
                     [rng.uniform(-0.24, 0.24) for _ in range(len(joints) + 2)]))
        wy += h
    for (y0, y1, joints, rbias, bbias) in rows:
        jset = set(joints)
        for x in range(SCENE_W):
            seg = 0
            for j in joints:
                if x >= j:
                    seg += 1
            tone = rbias + bbias[seg]
            for y in range(y0, y1):
                if x in jset and y > y0:
                    c.set(x, y, C("090a14"))
                    continue
                s = 1.0 - quiet(x, y)        # per ROW: the quiet patch is a
                base = 0.66 + tone * s       # window, not a full-height column
                if y == y0:
                    base += 0.70 * s                 # the proud lip catches it
                elif y == y0 + 1:
                    base += 0.28 * s
                elif y >= y1 - 2:
                    base -= 0.82 * s                 # shadow under the board
                c.set(x, y, surface(x, y, base))
    for (y0, y1, joints, rbias, bbias) in rows:      # knots: a SOLID dark core
        if rng.random() < 0.55 and y1 - y0 > 9:      # with one lit lip beneath.
            kx = rng.randrange(14, SCENE_W - 14)     # Drawn as two dashed rings
            ky = rng.randrange(y0 + 4, y1 - 4)       # they read as dead flies.
            rx_ = rng.randint(2, 4)
            for dy in range(-2, 3):
                hw = rx_ - abs(dy)
                if hw < 0 or not (y0 < ky + dy < y1 - 1):
                    continue
                c.hline(kx - hw, kx + hw, ky + dy,
                        surface(kx, ky + dy,
                                0.66 - (2.6 if abs(dy) < 2 else 1.4)))
            if y0 < ky + 3 < y1 - 1:
                c.hline(kx - rx_ + 1, kx + rx_ - 1, ky + 3,
                        surface(kx, ky + 3, 2.0))
        if rng.random() < 0.30:                      # a split along the grain
            sx = rng.randrange(20, SCENE_W - 60)
            ln = rng.randint(20, 70)
            for k in range(ln):
                c.set(sx + k, y0 + 3 + (k // 26), C("090a14"))
                if k % 7 < 2:
                    c.set(sx + k, y0 + 2 + (k // 26),
                          surface(sx + k, y0 + 2, 1.9))
        for j in joints:                             # nail pairs at the joins
            if not (6 < j < SCENE_W - 8):
                continue
            for nx_ in (j - 5, j + 4):
                ny_ = y0 + 4 + rng.randrange(0, max(1, y1 - y0 - 8))
                c.set(nx_, ny_, C("090a14"))
                c.set(nx_, ny_ + 1, C("090a14"))
                c.set(nx_, ny_ - 1, surface(nx_, ny_ - 1, 2.1))
    for _ in range(14):                              # patched-in boards: other
        ri = rng.randrange(1, len(rows) - 1)         # timber, other batch.
        y0, y1, joints, _b, _bb = rows[ri]           # ONLY where a lamp
        cand = [j for j in joints if 30 < j < SCENE_W - 130   # actually reaches
                and quiet(j) <= 0.0 and quiet(j + 120) <= 0.0
                and max(lights(j + 40, (y0 + y1) // 2)) > 0.42]
        if not cand:
            continue
        j0 = cand[rng.randrange(len(cand))]
        j1 = min([j for j in joints if j > j0] + [j0 + 110])
        for x in range(j0 + 1, min(SCENE_W, j1)):
            for y in range(y0 + 1, y1 - 1):
                c.set(x, y, surface(x, y, 1.15 if y > y0 + 2 else 1.75))
    wall_region = {(x, y) for y in range(CEIL + 6, FLOOR_Y - 2)
                   for x in range(SCENE_W)}
    for _ in range(11):                              # damp / soot patches
        pat = blob(rng, rng.randrange(20, SCENE_W - 20),
                   rng.randrange(CEIL + 10, FLOOR_Y - 10),
                   rng.randint(30, 110), wall_region)
        # a patch that touches the flat button rectangle is dropped WHOLE —
        # clipping it there would leave a straight edge on the one part of
        # the wall that has to be featureless. The rolls are still spent.
        if not any(quiet(px_, py_) >= 1.0 for (px_, py_) in pat):
            darken(pat)

    # ================================================== the floor ===========
    for y in range(FLOOR_Y, SCENE_H):
        d = (y - FLOOR_Y) / float(SCENE_H - FLOOR_Y)
        for x in range(SCENE_W):
            c.set(x, y, surface(x, y, 0.94 - d * 1.55))
    for x in range(SCENE_W):                                  # the kick board
        yb = FLOOR_Y + 5 + wobble(x, 0.9, 0.6, 149.0, 53.0)
        for y in range(FLOOR_Y, yb):
            c.set(x, y, surface(x, y, 0.10))
        c.set(x, FLOOR_Y - 1, C("090a14"))
        c.set(x, yb, surface(x, yb, 2.05))
        c.set(x, yb + 1, C("090a14"))
    for jy in (474, 516):                                     # expansion joints
        for x in range(SCENE_W):
            yy = jy + wobble(x, 2.4, 1.6, 83.0, 31.0)
            c.set(x, yy, C("090a14"))
            c.set(x, yy + 1, surface(x, yy + 1, 1.5))
    floor_region = {(x, y) for y in range(FLOOR_Y + 9, SCENE_H)
                    for x in range(SCENE_W)}
    for _ in range(5):                                        # long cracks
        x_ = rng.randrange(60, SCENE_W - 60)
        y_ = rng.randrange(FLOOR_Y + 12, SCENE_H - 30)
        for k in range(rng.randint(40, 100)):
            c.set(x_, y_, C("090a14"))
            x_ += rng.choice((-1, 0, 1, 1, 1))
            y_ += rng.choice((0, 0, 0, 1))
            if k % 23 == 22:                                  # one branch
                for m in range(rng.randint(6, 16)):
                    c.set(x_ + m, y_ - m // 2, C("090a14"))
    for _ in range(9):                                        # oil, solid
        darken(blob(rng, rng.randrange(40, SCENE_W - 40),
                    rng.randrange(FLOOR_Y + 14, SCENE_H - 14),
                    rng.randint(40, 150), floor_region))
    for _ in range(22):                                       # small grit
        bx = rng.randrange(20, SCENE_W - 20)
        by = rng.randrange(FLOOR_Y + 12, SCENE_H - 6)
        for k in range(rng.randint(2, 5)):
            c.set(bx + k, by + (k // 3), surface(bx + k, by, 1.9))

    # ================================================== kettle's rug ========
    # woven stripes and a real fringe. It used to be a solid block with 6% of
    # its pixels dropped at random, which is exactly the dot noise that is
    # banned everywhere else in this file.
    RX0, RX1, RY0, RY1 = 88, 366, 442, 512
    rug_ramp = ["090a14", "241527", "341c27", "411d31", "602c2c", "752438"]
    rug_twin = ["090a14", "172038", "1e1d39", "253a5e", "3c5e8b", "577277"]
    stripes = []
    sx_ = RX0 + 6
    while sx_ < RX1 - 6:
        w_ = rng.randint(3, 11)
        stripes.append((sx_, min(RX1 - 6, sx_ + w_), rng.uniform(-0.9, 0.9)))
        sx_ += w_
    for y in range(RY0, RY1 + 1):
        t = (y - RY0) / float(RY1 - RY0)
        pull = int(round(math.sin(t * math.pi) * 5))          # it lies unevenly
        for (a, b, tone) in stripes:
            for x in range(a - pull, b - pull):
                warm, cool = lights(x, y)
                c.set(x, y, mix2(rug_ramp, rug_twin,
                                 1.5 + (warm + cool * 0.45) * 3.4 + tone,
                                 warm, cool))
            c.set(a - pull, y, C("241527"))                    # each stripe has
        if y % 9 == 0:                                        # its own edge
            darken([(x, y) for x in range(RX0 - pull, RX1 - pull)])
    for x in range(RX0 + 4, RX1 - 4):                         # the bound border
        warm, cool = lights(x, RY0)
        lit = (warm + cool * 0.45) * 2.4
        for yy in (RY0, RY0 + 1, RY0 + 2):
            c.set(x, yy, mix2(rug_ramp, rug_twin, 2.6 + lit, warm, cool))
        for yy in (RY1 - 2, RY1 - 1, RY1):
            c.set(x, yy, mix2(rug_ramp, rug_twin, 2.2 + lit, warm, cool))
        c.set(x, RY0 + 3, C("090a14"))
        c.set(x, RY1 - 3, C("090a14"))
    for k in range(0, RX1 - RX0 - 8, 3):                      # fringe, uneven
        fx = RX0 + 4 + k + rng.randint(-1, 1)
        for m in range(rng.randint(2, 6)):
            warm, cool = lights(fx, RY1 + 1 + m)
            c.set(fx, RY1 + 1 + m,
                  mix2(["241527", "341c27", "602c2c", "ad7757"],
                       ["172038", "1e1d39", "253a5e", "577277"],
                       0.4 + (warm + cool * 0.45) * 2.8, warm, cool))
    rug_region = {(x, y) for y in range(RY0 + 3, RY1 - 2)
                  for x in range(RX0 + 4, RX1 - 4)}
    for _ in range(4):                                        # worn right down
        darken(blob(rng, rng.randrange(RX0 + 20, RX1 - 20),
                    rng.randrange(RY0 + 8, RY1 - 8),
                    rng.randint(30, 90), rug_region))
    for k in range(26):                                       # a folded corner
        c.hline(RX1 - 6 - k, RX1 - 4, RY1 - 24 + k, C("341c27"))
        c.set(RX1 - 6 - k, RY1 - 24 + k, C("602c2c"))

    # ================================================== the job board =======
    BX0, BY0, BX1, BY1 = 66, 92, 352, 274
    shade(BX0 + 7, BY0 + 10, BX1 + 13, BY1 + 15, 2)            # its cast shadow
    shade(BX0 + 13, BY0 + 16, BX1 + 7, BY1 + 9, 1)
    for y in range(BY0, BY1 + 1):                              # the frame
        for x in range(BX0, BX1 + 1):
            warm, cool = lights(x, y)
            c.set(x, y, mix2(["241527", "341c27", "4d2b32", "7a4841",
                              "ad7757"],
                             ["172038", "1e1d39", "253a5e", "3c5e8b",
                              "577277"],
                             0.30 + (warm + cool * 0.45) * 3.1, warm, cool))
    c.hline(BX0, BX1, BY0, C("ad7757"))                        # top catch
    c.hline(BX0 + 1, BX1 - 1, BY0 + 1, C("884b2b"))
    c.vline(BX0, BY0, BY1, C("884b2b"))
    c.hline(BX0, BX1, BY1, C("090a14"))
    c.vline(BX1, BY0, BY1, C("241527"))
    for k in range(10):                                        # mitred corners
        c.set(BX0 + k, BY0 + 9 - k, C("241527"))
        c.set(BX1 - k, BY0 + 9 - k, C("241527"))
        c.set(BX0 + k, BY1 - 9 + k, C("090a14"))
        c.set(BX1 - k, BY1 - 9 + k, C("090a14"))
    CX0, CY0, CX1, CY1 = BX0 + 10, BY0 + 10, BX1 - 10, BY1 - 10
    for y in range(CY0, CY1 + 1):                              # the cork
        for x in range(CX0, CX1 + 1):
            warm, cool = lights(x, y)
            g = 0.0
            if (y * 3 + int(math.sin(x / 13.0) * 2)) % 7 == 0:
                g -= 0.55                                      # pressed grain
            elif (y * 5 + int(math.sin(x / 9.0 + 1.2) * 2)) % 11 == 0:
                g += 0.40
            c.set(x, y, mix2(["241527", "341c27", "4d2b32", "7a4841",
                              "ad7757", "c09473"],
                             ["172038", "1e1d39", "253a5e", "3c5e8b",
                              "577277", "819796"],
                             0.44 + (warm + cool * 0.45) * 3.5 + g,
                             warm, cool))
    c.hline(CX0, CX1, CY0, C("090a14"))                        # rebate shadow
    c.hline(CX0, CX1, CY0 + 1, C("241527"))
    c.vline(CX0, CY0, CY1, C("241527"))
    c.vline(CX1, CY0, CY1, C("884b2b"))
    c.hline(CX0, CX1, CY1, C("884b2b"))
    cork_region = {(x, y) for y in range(CY0 + 2, CY1 - 1)
                   for x in range(CX0 + 2, CX1 - 1)}
    for _ in range(10):                                        # wear, solid
        darken(blob(rng, rng.randrange(CX0 + 8, CX1 - 8),
                    rng.randrange(CY0 + 8, CY1 - 8),
                    rng.randint(18, 60), cork_region))
    for _ in range(12):                                        # old pin holes,
        hx = rng.randrange(CX0 + 6, CX1 - 6)                   # punched through
        hy = rng.randrange(CY0 + 6, CY1 - 6)
        c.rect(hx, hy, hx + 1, hy + 1, C("241527"))
        c.hline(hx, hx + 1, hy + 2, C("884b2b"))
    c.vline(92, CEIL - 1, BY0, C("090a14"))                    # hanging wires
    c.vline(93, CEIL - 1, BY0, C("151d28"))
    c.vline(326, CEIL - 1, BY0, C("090a14"))
    c.vline(327, CEIL - 1, BY0, C("151d28"))

    def mini_photo(px0: int, py0: int, kind: str) -> None:
        c.rect(px0 - 1, py0 - 1, px0 + 24, py0 + 15, C("090a14"))
        for yy in range(15):
            for xx in range(24):
                c.set(px0 + xx, py0 + yy,
                      C("253a5e") if yy < 6 else (C("1e1d39") if yy < 11
                                                  else C("172038")))
        if kind == "transit":
            c.hline(px0, px0 + 23, py0 + 10, C("394a50"))       # the rail line
            c.hline(px0, px0 + 23, py0 + 11, C("202e37"))
            c.rect(px0 + 13, py0 + 6, px0 + 19, py0 + 9, C("25562e"))
            c.hline(px0 + 13, px0 + 19, py0 + 6, C("468232"))
            c.vline(px0 + 5, py0 + 2, py0 + 10, C("090a14"))    # the mast
            c.hline(px0 + 3, px0 + 7, py0 + 2, C("090a14"))
            c.set(px0 + 6, py0 + 4, C("cf573c"))
        elif kind == "the mills":
            c.rect(px0 + 3, py0 + 7, px0 + 17, py0 + 14, C("10141f"))
            c.hline(px0 + 3, px0 + 17, py0 + 7, C("202e37"))
            c.vline(px0 + 7, py0 + 1, py0 + 7, C("10141f"))
            c.vline(px0 + 8, py0 + 1, py0 + 7, C("151d28"))
            c.vline(px0 + 13, py0 + 3, py0 + 7, C("10141f"))
            c.set(px0 + 7, py0, C("341c27"))
        elif kind == "harbor":
            c.hline(px0, px0 + 23, py0 + 12, C("3c5e8b"))       # the water line
            c.hline(px0, px0 + 23, py0 + 13, C("253a5e"))
            c.vline(px0 + 16, py0 + 2, py0 + 11, C("090a14"))   # a crane
            c.hline(px0 + 8, px0 + 16, py0 + 2, C("090a14"))
            c.vline(px0 + 9, py0 + 3, py0 + 5, C("090a14"))
            c.rect(px0 + 2, py0 + 9, px0 + 9, py0 + 11, C("10141f"))
            c.hline(px0 + 2, px0 + 9, py0 + 9, C("202e37"))
        else:                                                   # old ward
            for (bx_, bh) in ((1, 5), (6, 9), (12, 4), (17, 7)):
                c.rect(px0 + bx_, py0 + 12 - bh, px0 + bx_ + 4, py0 + 12,
                       C("10141f"))
                c.hline(px0 + bx_, px0 + bx_ + 4, py0 + 12 - bh, C("202e37"))
            c.vline(px0 + 8, py0, py0 + 3, C("10141f"))
            c.set(px0 + 8, py0, C("cf573c"))

    def squiggle(x0: int, x1: int, y: int, col) -> None:
        for x in range(x0, x1):
            if (x - x0) % 11 == 9:
                continue                       # word gaps
            c.set(x, y + (1 if math.sin(x * 1.7) > 0.3 else 0), col)

    sheets = [("transit", 178, 108, False, 0.10),
              ("the mills", 84, 124, True, -0.07),
              ("harbor", 272, 130, True, 0.05),
              ("old ward", 118, 196, True, -0.04)]
    pins: list[tuple[int, int]] = []
    for (word, sx, sy, crossed, lean) in sheets:
        pw, ph = (74, 66) if word == "transit" else (62, 56)
        pale = word in ("transit", "the mills")
        cut_a, cut_b = rng.randint(2, 6), rng.randint(2, 6)
        curl = rng.randint(4, 9)                               # a lifted corner
        ramp = (["4d2b32", "602c2c", "884b2b", "ad7757", "c09473",
                 "d7b594", "e7d5b3"] if pale else
                ["341c27", "4d2b32", "602c2c", "884b2b", "ad7757",
                 "c09473", "d7b594"])
        for yy in range(ph):
            off = int(round(lean * (yy - ph / 2)))
            for xx in range(pw):
                if xx + yy < cut_a or (pw - xx) + (ph - yy) < cut_b:
                    continue
                if (pw - xx) + yy < curl:                      # the curl, lifted
                    continue
                lv = 3.4 - (yy / float(ph)) * 1.1
                if xx > pw - 4:
                    lv -= 1.3
                if yy > ph - 4:
                    lv -= 1.5
                c.set(sx + xx + off, sy + yy, band(ramp, lv))
        for k in range(curl):                                  # its underside
            c.set(sx + pw - 1 - k + int(round(lean * (-ph / 2 + curl - k))),
                  sy + curl - 1 - k, C("7a4841"))
        shade(sx - 1, sy + ph, sx + pw + 3, sy + ph + 3, 1)    # sheet shadow
        pin = (sx + pw // 2, sy + 3)
        pins.append(pin)
        pin_col = [C("cf573c"), C("73bed3"), C("e8c170"), C("a8ca58")][len(pins) % 4]
        c.set(pin[0], pin[1] + 3, C("341c27"))                 # pressed shadow
        c.set(pin[0] + 1, pin[1] + 3, C("341c27"))
        for (dx, dy) in ((0, 0), (1, 0), (-1, 0), (0, -1), (0, 1),
                         (1, -1), (-1, 1), (1, 1)):
            c.set(pin[0] + dx, pin[1] + dy, pin_col)
        c.set(pin[0] - 1, pin[1] - 1, C("ebede9"))
        c.set(pin[0], pin[1] + 2, C("090a14"))
        # the district name in tall marker ink, underlined
        title = _render_word(word, C("090a14"), C("241527"))
        tall = title.resize((title.width, title.height * 2), Image.NEAREST)
        c.img.alpha_composite(tall, (sx + 5, sy + 8))
        c.px = c.img.load()
        for ux in range(sx + 5, min(sx + 5 + tall.width, sx + pw - 5)):
            c.set(ux, sy + 9 + tall.height + (1 if (ux % 9) > 6 else 0),
                  C("341c27"))
        mini_photo(sx + 5, sy + 26, word)
        for ln in range(3):
            squiggle(sx + 32, sx + pw - 5, sy + 28 + ln * 6, C("341c27"))
        squiggle(sx + 5, sx + pw - 5, sy + 45, C("341c27"))
        squiggle(sx + 5, sx + pw - 19, sy + 50, C("341c27"))
        if crossed:                            # struck off — one solid stroke
            for k in range(pw - 10):
                yy = sy + 8 + int(k * (ph - 16) / float(pw))
                c.set(sx + 5 + k, yy, C("a53030"))
                c.set(sx + 5 + k, yy + 1, C("752438"))
        else:                                  # transit: ringed red, tonight
            for a in range(0, 360, 5):
                c.set(int(pin[0] + math.cos(math.radians(a)) * 9),
                      int(pin[1] + 2 + math.sin(math.radians(a)) * 6),
                      C("a53030"))
            for a in range(0, 360, 5):
                c.set(int(pin[0] + math.cos(math.radians(a)) * 8),
                      int(pin[1] + 3 + math.sin(math.radians(a)) * 5),
                      C("752438"))
            squiggle(sx + 7, sx + 36, sy + 58, C("a53030"))
    for i in range(1, len(pins)):              # red string between the pins
        x0, y0 = pins[0]
        x1, y1 = pins[i]
        for k in range(90):
            t = k / 89.0
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t + math.sin(t * math.pi) * 6
            c.set(int(x), int(y), C("a53030"))
            c.set(int(x), int(y) + 1, C("752438"))

    # ================================================== kettle's table ======
    T_X0, T_X1, T_FAR, T_NEAR = 92, 352, 372, 394
    shade(T_X0 - 4, T_FAR - 3, T_X1 + 4, T_FAR + 2, 2)         # against the wall

    # ---- KETTLE, clipped at the far edge of his own table so everything on
    # it sits in FRONT of him. Pawnbroker's son from old ward: flat cap, the
    # grey beard, hunched over the balance, hard candle-light from the left.
    KX = 300

    def k_hw(y: int) -> int:                       # the head, tapering to jaw
        u = (y - 302) / 30.0
        if u < 0.14:
            return 13
        if u < 0.58:
            return 15
        if u < 0.78:
            return 14
        return max(4, int(14 - (u - 0.78) * 44))

    soft_shadow(KX + 8, 336, 50, 50)                           # his wall shadow
    for y in range(338, T_FAR):                                # the coat
        t = (y - 338) / 34.0
        half = int(21 + (t ** 0.5) * 15)
        for x in range(KX - half, KX + half + 1):
            u = (x - (KX - half)) / float(2 * half)
            lv = 0.9 + (1.0 - u) * 3.2 - (0.7 if 0.40 < u < 0.54 else 0.0)
            c.set(x, y, band(warm_ramp, lv))
        c.set(KX - half, y, C("ad7757"))                       # candle rim
        c.set(KX - half + 1, y, C("884b2b"))
        c.set(KX + half, y, C("090a14"))
        c.set(KX + half - 1, y, C("241527"))
    for k in range(9):                                         # a shoulder seam
        c.set(KX - 24 - k // 3, 340 + k, C("341c27"))
        c.set(KX + 22 + k // 3, 340 + k, C("090a14"))
    for y in range(340, 352):                                  # the scarf
        c.hline(KX - 15, KX + 12, y, C("602c2c") if y < 346 else C("4d2b32"))
    c.hline(KX - 15, KX - 5, 340, C("884b2b"))
    c.hline(KX - 16, KX + 13, 351, C("241527"))
    for k in range(11):                                        # its hanging end
        c.hline(KX - 18 - k // 3, KX - 9 - k // 3, 350 + k,
                C("602c2c") if k < 6 else C("4d2b32"))
    for y in range(302, 333):                                  # the face
        hw = k_hw(y)
        for x in range(KX - hw, KX + hw + 1):
            u = (x - (KX - hw)) / float(2 * hw + 1)
            c.set(x, y, C("d7b594") if u < 0.32 else
                  (C("c09473") if u < 0.66 else C("7a4841")))
    for k in range(6):                                         # the nose
        c.hline(KX - k_hw(314 + k) - 1 + k // 4, KX - k_hw(314 + k) + 1,
                314 + k, C("e7d5b3") if k < 3 else C("d7b594"))
    c.set(KX - k_hw(320), 320, C("c09473"))
    c.hline(KX - 13, KX - 4, 311, C("341c27"))                 # the brow
    c.hline(KX - 12, KX - 6, 312, C("241527"))
    c.hline(KX + 2, KX + 9, 310, C("341c27"))
    c.set(KX - 10, 315, C("090a14"))                           # the near eye
    c.set(KX - 11, 315, C("090a14"))
    c.set(KX - 10, 314, C("e7d5b3"))
    c.set(KX + 4, 314, C("090a14"))                            # the far eye
    c.set(KX + 5, 314, C("090a14"))
    for y in range(319, 338):                                  # the white beard.
        t = (y - 319) / 19.0                                   # It is one step
        hw = int(13 * (1.0 - t * t * 0.94) ** 0.5)             # BRIGHTER than
        for x in range(KX - hw, KX + hw + 1):                  # his skin all
            u = (x - (KX - hw)) / float(2 * hw + 1)            # through — grey
            c.set(x, y, C("e7d5b3") if u < 0.28 else           # paint here goes
                  (C("d7b594") if u < 0.60 else C("ad7757")))  # blue in candle
        c.set(KX + hw, y, C("7a4841"))                         # light
    for k in range(9):                                         # a few strands
        c.set(KX - 8 + k * 2, 336 + (k % 2), C("ad7757"))
    c.hline(KX - 10, KX - 2, 319, C("c09473"))                 # the moustache
    c.hline(KX - 9, KX + 4, 320, C("e7d5b3"))
    c.hline(KX - 8, KX + 2, 321, C("d7b594"))
    c.hline(KX - 6, KX + 1, 324, C("7a4841"))                  # the mouth line
    for y in range(292, 302):                                  # the flat cap
        t = (y - 292) / 10.0
        hw = int(9 + t * 6)
        for x in range(KX - hw - 2, KX + hw + 1):
            u = (x - (KX - hw - 2)) / float(2 * hw + 3)
            c.set(x, y, C("4d2b32") if u < 0.34 else
                  (C("341c27") if u < 0.70 else C("241527")))
    c.hline(KX - 14, KX + 13, 300, C("241527"))
    for k in range(18):                                        # its brim, out
        yb = 300 + k // 7                                      # over the candle
        c.set(KX - 15 - k, yb, C("884b2b") if k < 11 else C("602c2c"))
        c.set(KX - 15 - k, yb + 1, C("602c2c") if k < 11 else C("4d2b32"))
        c.set(KX - 15 - k, yb + 2, C("241527"))
    c.set(KX - 33, 302, C("ad7757"))

    # ---- his shelf of stock: what people have pawned and not come back for
    c.rect(92, 306, 214, 310, C("341c27"))
    c.hline(93, 213, 306, C("ad7757"))
    c.hline(92, 214, 310, C("090a14"))
    for bxx in (98, 208):                                      # its two brackets
        for k in range(9):
            c.set(bxx, 311 + k, C("241527"))
            c.set(bxx + 1 + k // 2, 311 + k, C("341c27"))
    soft_shadow(152, 316, 66, 16)
    c.rect(100, 288, 118, 306, C("341c27"))                    # a mantel clock
    c.hline(101, 117, 288, C("884b2b"))
    c.vline(100, 288, 305, C("602c2c"))
    c.vline(118, 288, 305, C("241527"))
    for (dy, hw) in ((0, 5), (1, 6), (2, 6), (3, 6), (4, 5)):
        c.hline(109 - hw, 109 + hw, 294 + dy, C("d7b594"))
    c.set(109, 296, C("341c27"))
    c.set(110, 297, C("341c27"))
    c.set(108, 298, C("341c27"))
    c.hline(102, 116, 303, C("241527"))
    c.rect(124, 292, 138, 306, C("202e37"))                    # a tin
    c.hline(125, 137, 292, C("577277"))
    c.vline(138, 292, 305, C("090a14"))
    c.hline(126, 136, 298, C("151d28"))
    c.hline(126, 136, 299, C("394a50"))
    for k in range(15):                                        # a pair of boots
        c.hline(146, 152, 291 + k, C("241527") if k % 5 else C("341c27"))
        c.hline(155, 161, 289 + k, C("341c27") if k % 5 else C("241527"))
    c.hline(144, 156, 305, C("090a14"))
    c.hline(153, 165, 303, C("090a14"))
    c.set(146, 290, C("602c2c"))
    c.set(155, 288, C("602c2c"))
    c.rect(170, 294, 190, 306, C("4d2b32"))                    # a valve radio
    c.hline(171, 189, 294, C("884b2b"))
    c.vline(190, 294, 305, C("241527"))
    c.rect(173, 297, 181, 303, C("241527"))
    for k in range(3):
        c.hline(174, 180, 298 + k * 2, C("602c2c"))
    for (dy, hw) in ((0, 2), (1, 3), (2, 3), (3, 2)):          # its dial
        c.hline(186 - hw, 186 + hw, 298 + dy, C("de9e41"))
    c.set(186, 299, C("341c27"))
    c.rect(196, 298, 206, 306, C("819796"))                    # a stack of plates
    c.hline(196, 206, 298, C("c7cfcc"))
    c.hline(196, 206, 301, C("394a50"))
    c.hline(196, 206, 304, C("394a50"))
    c.vline(206, 299, 305, C("577277"))

    # ---- the table, drawn in front of him
    for y in range(T_FAR, T_NEAR + 1):                         # the top face
        for x in range(T_X0, T_X1 + 1):
            warm, cool = lights(x, y)
            t = (y - T_FAR) / float(T_NEAR - T_FAR)
            c.set(x, y, mix2(warm_ramp, warm_twin,
                             1.5 + (warm + cool * 0.45) * 5.0 + t * 0.7,
                             warm, cool))
    for sy_ in (T_FAR + 7, T_FAR + 15):                        # board seams
        for x in range(T_X0, T_X1 + 1):
            c.set(x, sy_ + (1 if math.sin(x / 21.0) > 0.35 else 0), C("341c27"))
    c.hline(T_X0, T_X1, T_NEAR, C("ad7757"))                   # the lit near lip
    c.hline(T_X0, T_X1, T_NEAR + 1, C("884b2b"))
    for y in range(T_NEAR + 2, T_NEAR + 16):                   # the apron
        for x in range(T_X0 + 3, T_X1 - 2):
            warm, cool = lights(x, y)
            c.set(x, y, mix2(warm_ramp, warm_twin,
                             0.15 + (warm + cool * 0.45) * 3.1, warm, cool))
    c.hline(T_X0 + 3, T_X1 - 2, T_NEAR + 16, C("090a14"))
    for lx in (110, 330):                                      # legs
        for y in range(T_NEAR + 14, 478):
            warm, cool = lights(lx, y)
            lv = 0.3 + (warm + cool * 0.45) * 3.0
            c.hline(lx, lx + 8, y, mix2(warm_ramp, warm_twin, lv, warm, cool))
            c.vline(lx, y, y, mix2(warm_ramp, warm_twin, lv + 1.1, warm, cool))
            c.vline(lx + 8, y, y, C("090a14"))
        c.hline(lx - 1, lx + 9, 478, C("090a14"))
    for x in range(112, 331):                                  # the stretcher
        warm, cool = lights(x, 452)
        lit = (warm + cool * 0.45)
        c.set(x, 452, mix2(warm_ramp, warm_twin, 0.6 + lit * 3.0, warm, cool))
        c.set(x, 453, mix2(warm_ramp, warm_twin, 0.1 + lit * 2.6, warm, cool))
        c.set(x, 454, C("090a14"))

    # ---- the ledger, open, weighed down with a stone
    for y in range(372, 391):
        t = (y - 372) / 18.0
        c.hline(96 + int(t * 3), 136 - int(t * 2), y,
                C("d7b594") if y < 385 else C("c09473"))
    c.vline(115, 372, 390, C("a8b5b2"))
    c.vline(116, 373, 390, C("819796"))
    for k in range(5):
        squiggle(99 + (k % 2) * 2, 113, 375 + k * 3, C("7a4841"))
        squiggle(119, 134 - (k % 3) * 3, 375 + k * 3, C("7a4841"))
    c.rect(124, 370, 134, 376, C("394a50"))                    # the stone
    c.hline(125, 133, 370, C("577277"))
    c.set(132, 375, C("202e37"))

    # ---- the candle: the warm source, on its tin saucer
    c.rect(138, 380, 162, 386, C("394a50"))
    c.hline(139, 161, 380, C("819796"))
    c.hline(138, 162, 386, C("090a14"))
    c.rect(141, 376, 159, 381, C("202e37"))
    c.hline(142, 158, 376, C("577277"))
    for y in range(356, 381):                                  # the candle body
        t = (y - 356) / 24.0
        hw = 5 + int(t * 1.6)
        c.hline(150 - hw, 150 + hw, y, C("d7b594"))
        c.hline(150 - hw, 150 - hw + 2, y, C("e7d5b3"))
        c.vline(150 + hw, y, y, C("c09473"))
        c.vline(150 + hw - 1, y, y, C("c09473"))
    for (dx_, dy0, dl) in ((-4, 362, 9), (3, 368, 7), (-1, 372, 5)):
        c.vline(150 + dx_, dy0, dy0 + dl, C("e7d5b3"))         # wax runs
        c.set(150 + dx_ + 1, dy0 + dl, C("d7b594"))
    c.hline(144, 156, 356, C("e7d5b3"))                        # the melted top
    c.hline(146, 154, 355, C("e7d5b3"))
    c.set(150, 354, C("341c27"))                               # the wick
    c.set(150, 353, C("241527"))
    for (dy, hw, col) in ((0, 1, "e7d5b3"), (1, 2, "e8c170"), (2, 2, "e8c170"),
                          (3, 3, "de9e41"), (4, 3, "de9e41"), (5, 2, "be772b"),
                          (6, 2, "884b2b"), (7, 1, "884b2b")):
        c.hline(150 - hw, 150 + hw, CANDLE[1] + dy, C(col))
    c.set(150, CANDLE[1] - 1, C("e7d5b3"))                     # the tip
    c.set(150, CANDLE[1] + 2, C("e7d5b3"))                     # the hot core

    # ---- the coin pouch
    for y in range(374, 393):
        t = abs(y - 384) / 10.0
        hw = int(13 - t * 5)
        c.hline(178 - hw, 178 + hw, y, C("4d2b32") if y > 379 else C("341c27"))
        c.set(178 - hw, y, C("602c2c"))
        c.set(178 + hw, y, C("241527"))
    c.hline(171, 185, 375, C("602c2c"))
    c.hline(173, 183, 373, C("241527"))                        # its drawn cord
    c.set(172, 374, C("884b2b"))

    # ---- the balance: plinth, column, tipped beam, two hung brass pans
    c.rect(200, 380, 242, 388, C("202e37"))                    # plinth
    c.hline(201, 241, 380, C("577277"))
    c.hline(200, 242, 388, C("090a14"))
    c.rect(204, 376, 238, 380, C("151d28"))
    c.hline(205, 237, 376, C("394a50"))
    c.vline(220, 322, 377, C("394a50"))                        # column
    c.vline(221, 322, 377, C("202e37"))
    c.vline(222, 323, 377, C("151d28"))
    c.rect(216, 318, 226, 324, C("202e37"))                    # the pivot head
    c.hline(217, 225, 318, C("577277"))
    c.set(221, 321, C("819796"))
    for x in range(178, 264):                                  # the beam, tipped
        y = 326 + int(round((x - 221) * -0.055))
        c.set(x, y, C("394a50"))
        c.set(x, y + 1, C("202e37"))
        c.set(x, y + 2, C("090a14"))
    c.vline(221, 314, 322, C("577277"))                        # the pointer
    c.set(221, 313, C("819796"))
    for (ex, pan_y, deep) in ((184, 356, True), (256, 336, False)):
        top = 326 + int(round((ex - 221) * -0.055)) + 2
        for k in range(pan_y - top - 5):                       # three chains
            c.set(ex - 9, top + k, C("202e37"))
            c.set(ex, top + k, C("394a50"))
            c.set(ex + 9, top + k, C("202e37"))
        c.hline(ex - 10, ex + 10, pan_y - 5, C("202e37"))      # the yoke
        for (dy, hw, col) in ((0, 14, "de9e41"), (1, 14, "be772b"),
                              (2, 12, "884b2b"), (3, 10, "884b2b"),
                              (4, 7, "602c2c"), (5, 4, "602c2c")):
            c.hline(ex - hw, ex + hw, pan_y + dy, C(col))
        c.hline(ex - 13, ex - 5, pan_y, C("e8c170"))
        c.set(ex - 14, pan_y + 1, C("602c2c"))
        c.set(ex + 14, pan_y + 1, C("341c27"))
        if deep:                                               # loaded with gold
            for (gx, gw) in ((-9, 5), (-2, 6), (5, 4)):
                c.hline(ex + gx, ex + gx + gw, pan_y - 1, C("e8c170"))
                c.hline(ex + gx, ex + gx + gw, pan_y - 2, C("de9e41"))
            c.hline(ex - 4, ex + 1, pan_y - 4, C("e8c170"))
            c.hline(ex - 3, ex, pan_y - 5, C("e7d5b3"))
    for (wx, wh) in ((250, 6), (258, 4), (242, 3)):            # weights, other
        c.rect(wx, 335 - wh, wx + 5, 334, C("884b2b"))         # pan
        c.hline(wx, wx + 5, 335 - wh, C("de9e41"))
        c.vline(wx + 5, 335 - wh, 334, C("602c2c"))
        c.set(wx + 2, 336 - wh, C("e8c170"))

    # ---- coin stacks on the table. The old version was 110 loose pixels.
    for (cx_, n_, tone) in ((252, 7, 0), (266, 4, 1), (278, 9, 0),
                            (292, 5, 1), (304, 3, 0)):
        for k in range(n_):
            y = 386 - k * 2
            c.hline(cx_, cx_ + 10, y, C("de9e41") if tone == 0 else C("be772b"))
            c.hline(cx_, cx_ + 10, y + 1, C("884b2b"))
            c.set(cx_, y, C("be772b"))
            c.set(cx_ + 10, y, C("602c2c"))
        top = 386 - n_ * 2
        c.hline(cx_ + 1, cx_ + 9, top, C("e8c170"))            # the top face
        c.hline(cx_ + 3, cx_ + 7, top - 1, C("e8c170"))
        c.set(cx_ + 4, top - 1, C("e7d5b3"))
    for (lx, ly) in ((318, 388), (246, 390), (330, 384)):      # loose coins
        c.hline(lx, lx + 8, ly, C("be772b"))
        c.hline(lx + 1, lx + 7, ly - 1, C("de9e41"))
        c.hline(lx, lx + 8, ly + 1, C("602c2c"))

    # ---- the ashtray. Runtime smoke rises from (334, 372).
    for y in range(366, 379):
        t = abs(y - 373) / 7.0
        hw = int(15 * (1.0 - t * t) ** 0.5) if t < 1 else 0
        if hw > 0:
            c.hline(334 - hw, 334 + hw, y, C("151d28") if y > 370 else
                    C("202e37"))
            c.set(334 - hw, y, C("394a50"))
            c.set(334 + hw, y, C("090a14"))
    c.hline(322, 346, 367, C("577277"))
    c.hline(326, 342, 371, C("090a14"))                        # the ash bed
    c.hline(328, 340, 372, C("241527"))
    c.hline(330, 338, 370, C("819796"))                        # grey ash
    c.hline(333, 341, 369, C("c7cfcc"))                        # the stub
    c.set(342, 369, C("cf573c"))                               # its ember
    c.set(343, 369, C("884b2b"))

    # ---- kettle's arms, over the table: one out to the loaded pan, one
    # holding a coin up to the flame.
    limb(KX - 19, 350, KX - 32, 360, 8, 7, warm_ramp, 1.1,
         C("ad7757"), C("090a14"))
    limb(KX - 32, 360, KX - 50, 370, 7, 6, warm_ramp, 1.4,
         C("ad7757"), C("090a14"), across=True)
    c.vline(KX - 40, 358, 374, C("341c27"))                    # the rolled cuff
    c.vline(KX - 41, 359, 373, C("602c2c"))
    for y in range(366, 379):                                  # the hand, down
        t = (y - 366) / 13.0                                   # on the table top
        hw = int(6 - abs(t - 0.35) * 5)
        c.hline(KX - 54 - hw, KX - 54 + hw, y,
                C("d7b594") if t < 0.5 else C("c09473"))
        c.set(KX - 54 - hw, y, C("e7d5b3"))
        c.set(KX - 54 + hw, y, C("7a4841"))
    for k in range(3):                                         # fingers spread
        c.vline(KX - 57 + k * 3, 378, 382, C("c09473"))        # on the boards
        c.set(KX - 57 + k * 3, 382, C("7a4841"))
    c.hline(KX - 60, KX - 46, 383, C("341c27"))                # its little
    c.hline(KX - 58, KX - 48, 384, C("241527"))                # shadow
    limb(KX + 20, 352, KX + 14, 370, 8, 7, warm_ramp, 0.9,
         C("884b2b"), C("090a14"))
    for y in range(345, 358):                                  # that hand: a
        t = (y - 345) / 13.0                                   # closed fist,
        hw = int(6 - abs(t - 0.38) * 4)                        # side on
        c.hline(KX + 10 - hw, KX + 10 + hw, y,
                C("d7b594") if t < 0.45 else C("c09473"))
        c.set(KX + 10 - hw, y, C("e7d5b3"))
        c.set(KX + 10 + hw, y, C("7a4841"))
    c.hline(KX + 6, KX + 13, 350, C("ad7757"))                 # the knuckle line
    c.vline(KX + 6, 341, 346, C("c09473"))                     # thumb and finger
    c.set(KX + 6, 341, C("d7b594"))                            # pinching it
    c.vline(KX + 13, 342, 346, C("7a4841"))
    c.hline(KX + 7, KX + 12, 340, C("de9e41"))                 # the coin, edge-on
    c.hline(KX + 8, KX + 11, 339, C("e8c170"))
    c.set(KX + 9, 338, C("e7d5b3"))
    c.hline(KX + 7, KX + 12, 341, C("884b2b"))

    # ================================================== VERNE'S CORNER =====
    # the medic's table. He was a plain figure at a shelf with four bottles;
    # the corner says what he does before you read the figure at all.
    VX0, VX1, V_FAR, V_NEAR = 570, 694, 366, 398
    # the instrument rail over his head — hung tools, every one different,
    # hung SHORT off the rail (the first cut gave each a 20 px wire and the
    # row came out reading as six coat hangers)
    c.rect(590, 176, 690, 180, C("202e37"))
    c.hline(591, 689, 176, C("577277"))
    c.hline(590, 690, 180, C("090a14"))
    c.vline(596, 168, 176, C("151d28"))
    c.vline(684, 168, 176, C("151d28"))
    for (hx, kind, drop) in ((600, 0, 3), (618, 1, 6), (634, 2, 2),
                             (650, 3, 5), (666, 1, 3), (680, 0, 7)):
        c.vline(hx, 180, 180 + drop, C("819796"))
        c.set(hx + 1, 180, C("394a50"))
        b = 181 + drop
        if kind == 0:                                          # shears
            c.rect(hx - 2, b, hx + 3, b + 9, C("a8b5b2"))
            c.vline(hx - 2, b, b + 9, C("c7cfcc"))
            c.vline(hx + 3, b, b + 9, C("577277"))
            for k in range(9):                                 # the two blades
                c.set(hx - 2 - k // 3, b + 9 + k, C("a8b5b2"))
                c.set(hx + 3 + k // 3, b + 9 + k, C("819796"))
            c.set(hx - 4, b + 18, C("577277"))
            c.set(hx + 5, b + 18, C("394a50"))
        elif kind == 1:                                        # forceps
            for k in range(19):
                c.set(hx - 2 + k // 9, b + k, C("c7cfcc"))
                c.set(hx + 2 - k // 9, b + k, C("819796"))
                if k < 4:
                    c.set(hx, b + k, C("a8b5b2"))
            c.hline(hx - 3, hx + 3, b + 19, C("a8b5b2"))
            c.hline(hx - 2, hx + 2, b + 20, C("577277"))
        elif kind == 2:                                        # a clamp
            c.rect(hx - 4, b, hx + 4, b + 7, C("819796"))
            c.hline(hx - 4, hx + 4, b, C("c7cfcc"))
            c.hline(hx - 4, hx + 4, b + 7, C("394a50"))
            c.vline(hx - 4, b, b + 7, C("a8b5b2"))
            c.rect(hx - 2, b + 8, hx + 2, b + 15, C("577277"))
            c.vline(hx - 2, b + 8, b + 15, C("819796"))
        else:                                                  # a bone saw
            c.rect(hx - 2, b, hx + 4, b + 15, C("577277"))
            c.vline(hx - 2, b, b + 15, C("a8b5b2"))
            c.vline(hx + 4, b, b + 15, C("394a50"))
            for k in range(0, 16, 2):
                c.set(hx + 5, b + k, C("c7cfcc"))
                c.set(hx + 6, b + k, C("819796"))
            c.rect(hx - 3, b + 15, hx + 5, b + 20, C("341c27"))
            c.hline(hx - 3, hx + 5, b + 15, C("602c2c"))
    # the shelf of mismatched bottles
    c.rect(590, 232, 692, 236, C("341c27"))
    c.hline(591, 691, 232, C("884b2b"))
    c.hline(590, 692, 236, C("090a14"))
    c.vline(594, 236, 244, C("241527"))                        # its brackets
    c.vline(686, 236, 244, C("241527"))
    for (bx, bw, bh, glass, fill, cap) in (
            (596, 6, 18, "25562e", "468232", "341c27"),
            (606, 5, 12, "253a5e", "3c5e8b", "202e37"),
            (614, 8, 22, "819796", "c7cfcc", "394a50"),
            (626, 6, 14, "4d2b32", "884b2b", "241527"),
            (636, 9, 16, "202e37", "394a50", "151d28"),
            (650, 5, 20, "25562e", "75a743", "19332d"),
            (658, 7, 11, "253a5e", "4f8fba", "172038"),
            (670, 6, 24, "7a4841", "ad7757", "341c27")):
        y0 = 232 - bh
        c.rect(bx, y0, bx + bw, 231, C(glass))
        c.vline(bx, y0, 231, C(fill))                          # the lit edge
        c.vline(bx + bw, y0, 231, C("090a14"))
        c.hline(bx, bx + bw, y0, C(cap))
        c.rect(bx + 1, y0 + bh // 3, bx + bw - 1, 230, C(fill))
        c.vline(bx + bw - 1, y0 + bh // 3, 230, C(glass))
        c.set(bx + 1, y0 + bh // 3 + 1, C("c7cfcc"))           # a glass catch
    c.rect(678, 216, 690, 231, C("c7cfcc"))                    # a dressing box
    c.hline(679, 689, 216, C("ebede9"))
    c.vline(690, 216, 231, C("819796"))
    c.hline(681, 687, 222, C("a53030"))
    c.vline(684, 219, 225, C("a53030"))

    # ---- VERNE: ER nurse, the one who says don't go. Standing behind the
    # table, clipped at its far edge; sleeves rolled, both hands working.
    VVX = 630

    def v_hw(y: int) -> int:
        u = (y - 264) / 36.0
        if u < 0.15:
            return 12
        if u < 0.62:
            return 13
        if u < 0.80:
            return 12
        return max(4, int(12 - (u - 0.80) * 42))

    soft_shadow(VVX + 8, 312, 44, 62)
    for y in range(302, V_FAR):                                # shirt and apron
        t = (y - 302) / 64.0
        half = int(18 + (t ** 0.4) * 9)
        for x in range(VVX - half, VVX + half + 1):
            u = (x - (VVX - half)) / float(2 * half)
            if abs(x - VVX) < half - 6 and y > 312:
                col = band(["202e37", "394a50", "577277", "819796", "a8b5b2",
                            "c7cfcc"], 1.6 + (1.0 - u) * 2.4)   # the apron bib
            else:
                col = band(["090a14", "10141f", "19332d", "25562e", "468232"],
                           0.9 + (1.0 - u) * 2.0)               # the shirt
            c.set(x, y, col)
        c.set(VVX - half, y, C("3c5e8b"))                       # the rack's rim
        c.set(VVX - half + 1, y, C("253a5e"))
        c.set(VVX + half, y, C("090a14"))
    for y in range(312, V_FAR):                                 # the bib edge
        t = (y - 312) / 54.0
        hw = int(11 + t * 6)
        c.vline(VVX - hw, y, y, C("819796"))
        c.vline(VVX + hw, y, y, C("202e37"))
    stain_region = {(a, b) for b in range(318, V_FAR)
                    for a in range(VVX - 16, VVX + 16)}
    for _ in range(2):                                          # old stains,
        col = C("602c2c") if rng.random() < 0.5 else C("4d2b32")  # SOLID patches
        for (qx, qy) in blob(rng, rng.randrange(VVX - 11, VVX + 11),
                             rng.randrange(328, V_FAR - 8),
                             rng.randint(14, 30), stain_region):
            for (ddx, ddy) in ((0, 0), (1, 0), (0, 1), (1, 1)):
                if (qx + ddx, qy + ddy) in stain_region:
                    c.set(qx + ddx, qy + ddy, col)
    c.hline(VVX - 20, VVX + 6, 312, C("a8b5b2"))                # the apron strap
    c.hline(VVX - 18, VVX + 4, 313, C("819796"))
    for y in range(298, 306):                                   # the neck
        c.hline(VVX - 5, VVX + 4, y, C("7a4841") if y > 301 else C("602c2c"))
    c.hline(VVX - 5, VVX + 4, 298, C("4d2b32"))
    for y in range(264, 301):                                   # the face
        hw = v_hw(y)
        for x in range(VVX - hw, VVX + hw + 1):
            u = (x - (VVX - hw)) / float(2 * hw + 1)
            c.set(x, y, C("7a4841") if u > 0.62 else
                  (C("c09473") if u > 0.24 else C("d7b594")))
    for y in range(264, 278):                                   # a cold forehead
        hw = v_hw(y)
        c.hline(VVX - hw, VVX - hw + 4, y, C("ad7757"))
    for k in range(8):                                          # the nose
        c.vline(VVX - 4 - k // 4, 280 + k, 280 + k, C("d7b594"))
    c.hline(VVX - 6, VVX - 2, 288, C("c09473"))
    c.set(VVX - 6, 289, C("7a4841"))
    c.hline(VVX - 13, VVX - 5, 277, C("341c27"))                # brows
    c.hline(VVX + 1, VVX + 8, 276, C("341c27"))
    c.hline(VVX - 12, VVX - 6, 281, C("090a14"))                # eyes, cast down
    c.hline(VVX + 2, VVX + 7, 280, C("090a14"))
    c.set(VVX - 12, 282, C("d7b594"))
    c.hline(VVX - 8, VVX - 1, 293, C("7a4841"))                 # the mouth
    c.hline(VVX - 7, VVX - 2, 294, C("602c2c"))
    for y in range(288, 300):                                   # a shaved jaw
        hw = v_hw(y) - 1                                        # in shadow, NOT
        for x in range(VVX - hw, VVX + hw):                     # dot stubble
            if c.get(x, y)[:3] == C("c09473")[:3]:
                c.set(x, y, C("7a4841"))
            elif c.get(x, y)[:3] == C("d7b594")[:3]:
                c.set(x, y, C("c09473"))
    c.hline(VVX - 8, VVX - 3, 296, C("819796"))                 # going grey, at
    c.hline(VVX - 2, VVX + 2, 297, C("577277"))                 # the jaw only
    for y in range(254, 268):                                   # cropped hair
        t = (y - 254) / 14.0
        hw = int(9 + t * 5)
        for x in range(VVX - hw, VVX + hw + 1):
            u = (x - (VVX - hw)) / float(2 * hw + 1)
            c.set(x, y, C("4d2b32") if u < 0.30 else
                  (C("341c27") if u < 0.68 else C("241527")))
    for k in range(12):                                         # the temples
        c.vline(VVX - 14 + k // 6, 262 + k // 2, 270 + k // 2, C("341c27"))
        c.vline(VVX + 13 - k // 6, 262 + k // 2, 268 + k // 2, C("241527"))
    c.vline(VVX - 13, 264, 270, C("819796"))
    c.set(VVX - 12, 266, C("819796"))

    # ---- his table, in front of him
    shade(VX0 - 4, V_FAR - 3, VX1 + 4, V_FAR + 2, 2)
    for y in range(V_FAR, V_NEAR + 1):
        for x in range(VX0, VX1 + 1):
            warm, cool = lights(x, y)
            t = (y - V_FAR) / float(V_NEAR - V_FAR)
            c.set(x, y, mix2(cool_twin, cool_ramp,
                             0.7 + (cool + warm * 0.45) * 4.2 + t * 0.6,
                             warm, cool))
    for x in range(VX0, VX1 + 1):
        c.set(x, V_FAR + 11 + (1 if math.sin(x / 19.0) > 0.4 else 0),
              C("10141f"))
    c.hline(VX0, VX1, V_NEAR, C("577277"))
    c.hline(VX0, VX1, V_NEAR + 1, C("394a50"))
    for y in range(V_NEAR + 2, V_NEAR + 14):
        for x in range(VX0 + 3, VX1 - 2):
            warm, cool = lights(x, y)
            c.set(x, y, mix2(cool_twin, cool_ramp,
                             0.1 + (cool + warm * 0.45) * 2.6, warm, cool))
    c.hline(VX0 + 3, VX1 - 2, V_NEAR + 14, C("090a14"))
    for lx in (578, 678):
        for y in range(V_NEAR + 12, 476):
            warm, cool = lights(lx, y)
            lit = cool + warm * 0.45
            c.hline(lx, lx + 7, y,
                    mix2(cool_twin, cool_ramp, 0.2 + lit * 2.4, warm, cool))
            c.vline(lx, y, y,
                    mix2(cool_twin, cool_ramp, 0.9 + lit * 2.6, warm, cool))
            c.vline(lx + 7, y, y, C("090a14"))
        c.hline(lx - 1, lx + 8, 476, C("090a14"))
    # the enamel basin he is rinsing in
    for y in range(372, 396):
        t = abs(y - 384) / 12.0
        hw = int(21 * (1.0 - t * t) ** 0.5) if t < 1 else 0
        if hw > 0:
            c.hline(600 - hw, 600 + hw, y, C("c7cfcc") if y < 378 else
                    (C("a8b5b2") if y < 390 else C("819796")))
    for y in range(374, 386):                                   # the water
        t = abs(y - 380) / 6.0
        hw = int(16 * (1.0 - t * t) ** 0.5) if t < 1 else 0
        if hw > 0:
            c.hline(600 - hw, 600 + hw, y,
                    C("3c5e8b") if y < 380 else C("253a5e"))
    c.hline(588, 608, 377, C("73bed3"))
    c.hline(592, 604, 376, C("a4dddb"))
    c.hline(590, 610, 383, C("172038"))
    c.hline(602, 612, 383, C("752438"))                         # what came off
    for k in range(9):                                          # its chipped rim
        c.set(583 + k, 381 + (k // 4), C("819796"))
    c.set(619, 381, C("577277"))
    # the folded dressings, each fold offset
    for k in range(5):
        y = 392 - k * 3
        w = 12 - (k % 2)
        c.rect(636 - w, y - 2, 636 + w, y, C("c7cfcc"))
        c.hline(636 - w, 636 + w, y - 2, C("ebede9"))
        c.hline(636 - w, 636 + w, y, C("819796"))
        c.set(636 + w, y - 1, C("577277"))
    # the instrument tray
    c.rect(656, 378, 692, 392, C("394a50"))
    c.hline(657, 691, 378, C("819796"))
    c.hline(656, 692, 392, C("090a14"))
    c.rect(658, 380, 690, 390, C("202e37"))
    for (ix, il, tone) in ((661, 11, "c7cfcc"), (668, 16, "a8b5b2"),
                           (678, 9, "819796")):
        c.hline(ix, ix + il, 383, C(tone))
        c.hline(ix, ix + il, 384, C("577277"))
        c.set(ix, 382, C("ebede9"))
    c.hline(664, 676, 387, C("752438"))                         # a stained cloth
    c.hline(666, 674, 388, C("a53030"))
    c.hline(668, 672, 386, C("411d31"))
    # ---- both forearms down to the table, sleeves rolled above the elbow
    for (sgn, hx, hy) in ((-1, 600, 372), (1, 668, 370)):
        limb(VVX + sgn * 17, 318, VVX + sgn * 26, 340, 7, 6,
             ["090a14", "10141f", "19332d", "25562e", "468232"], 0.8,
             C("3c5e8b") if sgn < 0 else C("25562e"), C("090a14"))
        c.hline(VVX + sgn * 26 - 8, VVX + sgn * 26 + 8, 340, C("468232"))
        c.hline(VVX + sgn * 26 - 8, VVX + sgn * 26 + 8, 341, C("25562e"))
        limb(VVX + sgn * 26, 342, hx, hy - 2, 6, 5, skin_ramp, 1.3,
             C("e7d5b3") if sgn < 0 else C("d7b594"), C("4d2b32"))
        hand(hx, hy, C("d7b594"), C("c09473"), C("e7d5b3"), C("7a4841"), 3)
    # a crate of supplies and a bucket under the table
    c.rect(592, 442, 642, 476, C("341c27"))
    c.hline(593, 641, 442, C("602c2c"))
    c.vline(592, 442, 476, C("4d2b32"))
    c.vline(642, 442, 476, C("090a14"))
    c.hline(592, 642, 476, C("090a14"))
    for k in (452, 464):
        c.hline(594, 640, k, C("241527"))
        c.hline(594, 640, k + 1, C("4d2b32"))
    c.rect(604, 434, 630, 443, C("c7cfcc"))                     # linen stacked in
    c.hline(604, 630, 434, C("ebede9"))
    c.hline(604, 630, 439, C("819796"))
    c.rect(648, 458, 668, 476, C("202e37"))                     # a bucket
    c.hline(648, 668, 458, C("577277"))
    c.vline(668, 458, 476, C("090a14"))
    c.rect(651, 461, 665, 466, C("172038"))
    for k in range(12):
        c.set(646 + k, 456 - int(math.sin(k / 11.0 * math.pi) * 6),
              C("394a50"))

    # ================================================== MARA'S RACK ========
    # the rig she walked out of the control room with, grown into a rack.
    for ux in (692, 906):                                      # the uprights
        for y in range(222, 412):
            c.vline(ux, y, y, C("577277"))
            c.hline(ux + 1, ux + 6, y, C("202e37"))
            c.vline(ux + 7, y, y, C("090a14"))
        for by in range(230, 410, 26):                         # its punched slots
            c.hline(ux + 2, ux + 5, by, C("151d28"))
            c.set(ux + 3, by + 1, C("394a50"))
    shade(686, 218, 916, 416, 1)

    def rack_unit(x0, y0, x1, y1, wear):
        box(x0, y0, x1, y1, C("202e37"), C("577277"), C("090a14"))
        c.rect(x0 + 3, y0 + 3, x1 - 3, y1 - 3, C("151d28"))
        c.hline(x0 + 3, x1 - 3, y0 + 3, C("090a14"))
        c.hline(x0 + 3, x1 - 3, y1 - 3, C("394a50"))
        for (sx_, sy_) in ((x0 + 2, y0 + 2), (x1 - 2, y0 + 2),
                           (x0 + 2, y1 - 2), (x1 - 2, y1 - 2)):
            c.set(sx_, sy_, C("819796"))                        # rack screws
            c.set(sx_, sy_ + 1, C("394a50"))
        reg = {(a, b) for b in range(y0 + 4, y1 - 3)
               for a in range(x0 + 4, x1 - 3)}
        for _ in range(wear):
            for (qx, qy) in blob(rng, rng.randrange(x0 + 6, x1 - 6),
                                 rng.randrange(y0 + 6, y1 - 6),
                                 rng.randint(6, 18), reg):
                c.set(qx, qy, C("10141f"))

    def dial(nx: int, ny: int) -> None:
        """A meter face with a real bezel and a pivot at the bottom centre —
        main_menu.gd draws its 3-frame needle sprite centred on (nx, ny)."""
        c.rect(nx - 13, ny - 11, nx + 13, ny + 9, C("394a50"))
        c.hline(nx - 12, nx + 12, ny - 11, C("819796"))
        c.hline(nx - 13, nx + 13, ny + 9, C("090a14"))
        c.vline(nx + 13, ny - 11, ny + 9, C("151d28"))
        c.rect(nx - 11, ny - 9, nx + 11, ny + 7, C("172038"))
        c.rect(nx - 10, ny - 8, nx + 10, ny + 6, C("253a5e"))
        c.rect(nx - 9, ny - 7, nx + 9, ny + 5, C("172038"))
        for a in range(200, 341, 14):                           # the tick scale
            c.set(int(nx + math.cos(math.radians(a)) * 8),
                  int(ny + 5 + math.sin(math.radians(a)) * 6.4),
                  C("a53030") if a > 310 else C("819796"))
        c.set(nx, ny + 5, C("394a50"))                          # the pivot
        for (sx_, sy_) in ((nx - 12, ny - 10), (nx + 12, ny - 10),
                           (nx - 12, ny + 8), (nx + 12, ny + 8)):
            c.set(sx_, sy_, C("c7cfcc"))

    rack_unit(700, 230, 792, 290, 3)                           # meter panel 1
    dial(746, 262)
    for (kx_, kr) in ((712, 4), (726, 3), (776, 5)):           # its knobs
        for (dy, hw) in ((-kr, 0), (-kr + 1, kr - 1), (0, kr), (kr - 1, kr - 1)):
            c.hline(kx_ - hw, kx_ + hw, 276 + dy, C("151d28"))
        c.hline(kx_ - kr + 1, kx_ + kr - 1, 276 - kr + 1, C("394a50"))
        c.set(kx_ - 1, 276 - kr + 2, C("819796"))
        c.hline(kx_ - kr, kx_ + kr, 276 + kr, C("090a14"))
    c.hline(706, 736, 240, C("394a50"))                        # a legend strip
    c.hline(706, 728, 244, C("202e37"))
    c.rect(766, 236, 786, 250, C("151d28"))                    # a small readout
    for k in range(3):
        c.hline(769, 783, 239 + k * 4, C("73bed3") if k == 1 else C("253a5e"))

    rack_unit(796, 236, 902, 296, 4)                           # meter panel 2
    dial(814, 272)
    for k in range(7):                                         # a slider bank
        sx_ = 836 + k * 8
        c.vline(sx_, 250, 288, C("090a14"))
        c.vline(sx_ + 1, 250, 288, C("151d28"))
        sy_ = 256 + (k * 37) % 26
        c.rect(sx_ - 2, sy_, sx_ + 3, sy_ + 4, C("394a50"))
        c.hline(sx_ - 2, sx_ + 3, sy_, C("819796"))
        c.hline(sx_ - 2, sx_ + 3, sy_ + 4, C("090a14"))
    c.rect(800, 244, 806, 292, C("151d28"))                    # a vent slot
    for k in range(244, 292, 4):
        c.hline(800, 806, k, C("090a14"))
        c.hline(800, 806, k + 1, C("202e37"))

    # the big screen — THE COOL SOURCE. Everything on this side is lit by it.
    rack_unit(698, 296, 800, 360, 2)
    for y in range(303, 348):                                  # the glass
        for x in range(705, 755):
            c.set(x, y, C("253a5e") if y % 2 == 0 else C("172038"))
    for x in range(705, 755):                                  # the trace
        yy = 326 + int(math.sin((x - 705) * 0.42) * 7
                       + math.sin((x - 705) * 0.13) * 3)
        c.set(x, yy, C("73bed3"))
        c.set(x, yy + 1, C("3c5e8b"))
    c.vline(741, 303, 347, C("253a5e"))                        # the sweep
    c.vline(742, 303, 347, C("3c5e8b"))
    c.hline(705, 754, 303, C("a4dddb"))
    c.hline(705, 754, 347, C("172038"))
    c.vline(704, 302, 348, C("090a14"))
    c.vline(756, 302, 348, C("090a14"))
    c.rect(758, 300, 796, 356, C("151d28"))                    # its control bay
    c.hline(758, 796, 300, C("394a50"))
    for k in range(4):                                         # buttons, varied
        bx_ = 763 + (k % 2) * 16
        by_ = 324 + (k // 2) * 12
        c.rect(bx_, by_, bx_ + 11, by_ + 7, C("202e37"))
        c.hline(bx_, bx_ + 11, by_, C("577277"))
        c.hline(bx_, bx_ + 11, by_ + 7, C("090a14"))
        c.set(bx_ + 9, by_ + 3, C("341c27") if k != 1 else C("cf573c"))
    c.rect(752, 306, 770, 318, C("202e37"))                    # the LED's plate
    c.hline(752, 770, 306, C("577277"))
    c.hline(752, 770, 318, C("090a14"))
    c.rect(756, 309, 764, 315, C("151d28"))
    c.set(760, 312, C("253a5e"))                               # LED anchor: the
    c.set(759, 312, C("172038"))                               # dark lamp under
    c.set(761, 312, C("172038"))                               # the blink

    # the junction box the whole rig feeds from, and its visible cable runs
    c.rect(916, 216, 942, 244, C("202e37"))
    c.hline(917, 941, 216, C("819796"))
    c.hline(916, 942, 244, C("090a14"))
    c.rect(919, 220, 939, 240, C("151d28"))
    for k in range(3):
        c.rect(922, 223 + k * 6, 936, 226 + k * 6, C("341c27"))
        c.hline(922, 936, 223 + k * 6, C("602c2c"))
    c.set(929, 219, C("cf573c"))
    c.set(928, 219, C("752438"))
    for (sx_, sy_, ex_, ey_, sag) in ((922, 244, 860, 300, 9),
                                      (929, 244, 902, 250, 5),
                                      (934, 244, 906, 380, 13),
                                      (918, 240, 800, 246, 11)):
        n = int(max(abs(ex_ - sx_), abs(ey_ - sy_)) * 2)
        for k in range(n + 1):
            t = k / float(n)
            x = sx_ + (ex_ - sx_) * t
            y = sy_ + (ey_ - sy_) * t + math.sin(t * math.pi) * sag
            c.set(int(x), int(y), C("090a14"))
            c.set(int(x) + 1, int(y), C("10141f"))
    for k in range(240):                                       # arcs above
        t = k / 239.0
        c.set(int(700 + t * 216), int(214 + math.sin(t * 3.6) * 10 + t * 3),
              C("090a14"))
        c.set(int(716 + t * 196), int(206 + math.sin(t * 4.6) * 7 + t * 12),
              C("10141f"))

    # ================================================== mara's desk ========
    D_X0, D_X1, D_FAR, D_NEAR = 700, 916, 384, 404
    shade(D_X0 - 4, D_FAR - 3, D_X1 + 4, D_FAR + 2, 2)
    for y in range(D_FAR, D_NEAR + 1):
        for x in range(D_X0, D_X1 + 1):
            warm, cool = lights(x, y)
            t = (y - D_FAR) / float(D_NEAR - D_FAR)
            c.set(x, y, mix2(cool_twin, cool_ramp,
                             0.8 + (cool + warm * 0.45) * 4.4 + t * 0.7,
                             warm, cool))
    for x in range(D_X0, D_X1 + 1):
        c.set(x, D_FAR + 8 + (1 if math.sin(x / 17.0) > 0.4 else 0), C("10141f"))
    c.hline(D_X0, D_X1, D_NEAR, C("577277"))
    c.hline(D_X0, D_X1, D_NEAR + 1, C("394a50"))
    for y in range(D_NEAR + 2, D_NEAR + 15):
        for x in range(D_X0 + 3, D_X1 - 2):
            warm, cool = lights(x, y)
            c.set(x, y, mix2(cool_twin, cool_ramp,
                             0.1 + (cool + warm * 0.45) * 2.7, warm, cool))
    c.hline(D_X0 + 3, D_X1 - 2, D_NEAR + 15, C("090a14"))
    for lx in (708, 900):
        for y in range(D_NEAR + 13, 494):
            warm, cool = lights(lx, y)
            lit = cool + warm * 0.45
            c.hline(lx, lx + 7, y,
                    mix2(cool_twin, cool_ramp, 0.2 + lit * 2.5, warm, cool))
            c.vline(lx, y, y,
                    mix2(cool_twin, cool_ramp, 0.9 + lit * 2.7, warm, cool))
            c.vline(lx + 7, y, y, C("090a14"))
        c.hline(lx - 1, lx + 8, 494, C("090a14"))
    # the set on the desk that carries the second blinking LED
    box(838, 348, 902, 392, C("202e37"), C("577277"), C("090a14"))
    c.rect(841, 351, 899, 389, C("151d28"))
    c.hline(841, 899, 351, C("090a14"))
    for k in range(6):                                          # speaker grille
        c.hline(846, 872, 356 + k * 4, C("090a14"))
        c.hline(846, 872, 357 + k * 4, C("202e37"))
    for k in range(2):                                          # two toggles
        c.rect(880 + k * 8, 358, 884 + k * 8, 368, C("394a50"))
        c.hline(880 + k * 8, 884 + k * 8, 358, C("819796"))
        c.set(882 + k * 8, 360 + k * 4, C("c7cfcc"))
    c.rect(852, 366, 870, 380, C("202e37"))                     # the LED's plate
    c.hline(852, 870, 366, C("577277"))
    c.hline(852, 870, 380, C("090a14"))
    c.rect(856, 369, 864, 375, C("151d28"))
    c.set(860, 372, C("253a5e"))                                # LED anchor
    c.set(859, 372, C("172038"))
    c.set(861, 372, C("172038"))
    for k in range(30):                                         # its own lead,
        t = k / 29.0                                            # down the back
        c.set(int(902 + t * 6), int(388 + t * 14), C("090a14"))
        c.set(int(903 + t * 6), int(388 + t * 14), C("10141f"))
    # her mug, and the log she keeps
    c.rect(714, 372, 730, 390, C("819796"))
    c.hline(715, 729, 372, C("c7cfcc"))
    c.vline(730, 373, 389, C("394a50"))
    c.hline(714, 730, 390, C("090a14"))
    c.rect(716, 374, 728, 377, C("341c27"))
    for k in range(8):
        c.set(732 + int(math.sin(k / 7.0 * math.pi) * 3), 375 + k, C("577277"))
    c.rect(742, 380, 782, 392, C("c7cfcc"))                     # the log book
    c.hline(742, 782, 380, C("ebede9"))
    c.hline(742, 782, 392, C("819796"))
    for k in range(3):
        squiggle(746, 778, 383 + k * 3, C("819796"))

    # ================================================== MARA ================
    # SAME WOMAN AS tools/pitches/counter.py — hair mass, ponytail, greying
    # lock, the two-cup headset, the oxblood jacket, the green enamel pin,
    # the brow scar. Seated at the rig in three-quarter, ON channel, one hand
    # on the cup, lit hard and cold from the screen on her left.
    MX = 806
    MFY0, MFY1 = 300, 337
    ox_ramp = ["241527", "411d31", "752438", "a53030"]

    def m_hw(y: int) -> int:
        u = (y - MFY0) / float(MFY1 - MFY0)
        if u < 0.13:
            return 11
        if u < 0.60:
            return 13
        if u < 0.76:
            return 12
        return max(3, int(12 - (u - 0.76) * 40))

    def m_ell(rx: int, ry: int):
        out = []
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy / float(ry)) ** 2
            out.append((dy, int(rx * (t ** 0.5)) if t > 0 else -1))
        return out

    soft_shadow(MX + 6, 340, 48, 50)                            # off the rack
    c.rect(MX - 44, 330, MX - 36, D_FAR, C("341c27"))           # her chair back
    c.hline(MX - 44, MX - 36, 330, C("602c2c"))
    c.vline(MX - 44, 331, D_FAR, C("4d2b32"))
    c.vline(MX - 36, 331, D_FAR, C("090a14"))
    # ---- the oxblood jacket, clipped at the desk's far edge
    shoulder_top: dict = {}
    for y in range(344, D_FAR):
        t = (y - 344) / 40.0
        half = int(19 + (t ** 0.45) * 17)
        for x in range(MX - half, MX + half + 1):
            u = (x - (MX - half)) / float(2 * half)
            c.set(x, y, C("752438") if 0.16 < u < 0.85 else C("411d31"))
            shoulder_top.setdefault(x, y)
        c.set(MX - half, y, C("3c5e8b"))                        # cold rim, screen
        c.set(MX - half + 1, y, C("253a5e"))
        c.set(MX + half, y, C("241527"))                        # dark rim, away
        c.set(MX + half - 1, y, C("411d31"))
    for x, y in shoulder_top.items():
        if abs(x - MX) > 15:
            c.set(x, y + 1, C("a53030"))
            c.set(x, y + 2, C("a53030"))
    c.rect(MX - 14, 338, MX + 13, 348, C("411d31"))             # the collar
    c.hline(MX - 14, MX + 13, 338, C("752438"))
    c.rect(MX - 10, 340, MX + 9, 349, C("341c27"))
    c.hline(MX - 14, MX - 6, 339, C("a53030"))
    c.set(MX - 15, 340, C("752438"))
    c.rect(MX + 7, 341, MX + 12, 345, C("25562e"))              # the enamel pin
    c.hline(MX + 7, MX + 12, 341, C("468232"))
    c.set(MX + 12, 345, C("19332d"))
    c.set(MX + 9, 343, C("19332d"))
    for y in range(328, 350):                                   # the neck
        c.hline(MX - 6, MX + 5, y, C("7a4841"))
    c.rect(MX - 4, 332, MX + 3, 346, C("ad7757"))
    c.hline(MX - 6, MX + 5, 328, C("4d2b32"))
    c.hline(MX - 6, MX + 5, 329, C("602c2c"))
    # ---- the hair mass: crown darkest, one lit band on the screen side
    for (dy, hw) in m_ell(23, 13):
        if hw < 0 or dy > 7:
            continue
        c.hline(MX - hw, MX + hw, 299 + dy, C("4d2b32"))
        if dy < -8:
            c.hline(MX - hw, MX + hw, 299 + dy, C("341c27"))
        if -4 < dy < 3:
            c.hline(MX - hw, MX - hw + 5, 299 + dy, C("602c2c"))
    for k in range(10):                                         # the side masses
        c.rect(MX - 23 + k, 296, MX - 13, 336 - abs(k - 3) * 2, C("4d2b32"))
        c.rect(MX + 13, 296, MX + 23 - k, 330 - abs(k - 4) * 2, C("4d2b32"))
    c.vline(MX - 23, 296, 330, C("602c2c"))                     # the screen finds
    c.vline(MX - 22, 302, 326, C("884b2b"))                     # this side
    c.vline(MX + 23, 296, 322, C("341c27"))
    for k in range(5):                                          # loose strands
        c.vline(MX + 25 + rng.randrange(3), 296 + k * 8, 302 + k * 8,
                C("341c27"))
    for k in range(52):                                         # the ponytail
        t = k / 52.0
        px_ = int(MX + 26 + t * 8 + math.sin(t * 3.0) * 3)
        w = int(8 - t * 4)
        c.rect(px_ - w, 298 + k, px_ + w, 299 + k, C("4d2b32"))
        c.vline(px_ - w, 298 + k, 299 + k,
                C("602c2c") if t < 0.5 else C("4d2b32"))
        c.vline(px_ + w, 298 + k, 299 + k, C("341c27"))
    c.rect(MX + 28, 342, MX + 38, 350, C("341c27"))             # its tie
    c.hline(MX + 28, MX + 38, 342, C("4d2b32"))
    for k in range(26):                                         # THE GREY LOCK
        t = k / 25.0
        x = MX - 21 + int(t * 4 + math.sin(t * 2.4) * 2)
        w = 2 - int(t * 2)
        col = C("577277") if t < 0.35 else (C("394a50") if t < 0.75
                                            else C("202e37"))
        c.hline(x, x + w, 294 + k, col)
        c.set(x - 1, 294 + k, C("341c27"))
    # ---- the headset, ON her ears: she is on channel, this is her rig
    for k in range(150):
        t = k / 149.0
        a = math.radians(193 + t * 154)
        hx = int(MX + math.cos(a) * 24)
        hy = int(305 + math.sin(a) * 22)
        c.set(hx, hy, C("202e37"))
        c.set(hx, hy + 1, C("394a50"))
        c.set(hx, hy + 2, C("151d28"))
    for (sgn, yx) in ((-1, MX - 24), (1, MX + 24)):
        c.rect(yx - 1, 294, yx + 1, 302, C("394a50"))           # the yoke
        c.vline(yx + sgn * 2, 295, 301, C("151d28"))
        cx0 = yx - 5
        for k in range(15):                                     # the ear cup
            n = 0 if 2 < k < 12 else 1
            c.hline(cx0 + n, cx0 + 9 - n, 300 + k, C("202e37"))
            c.set(cx0 + n, 300 + k, C("394a50"))
            c.set(cx0 + 9 - n, 300 + k, C("151d28"))
        c.rect(cx0 + 3, 303, cx0 + 7, 311, C("151d28"))         # the pad
        c.hline(cx0 + 2, cx0 + 8, 300, C("577277"))
        c.hline(cx0 + 2, cx0 + 8, 314, C("090a14"))
        c.set(cx0 + 4, 306, C("73bed3"))                        # LIVE, not dead
    for k in range(70):                                         # the lead, down
        t = k / 69.0                                            # to the rack
        c.set(int(MX + 30 + t * 26), int(316 + t * 40 + math.sin(t * 3.0) * 5),
              C("090a14"))
        c.set(int(MX + 31 + t * 26), int(316 + t * 40 + math.sin(t * 3.0) * 5),
              C("151d28"))
    # ---- the face. Cold from the screen on her left, nothing from the right.
    for y in range(MFY0, MFY1 + 1):
        hw = m_hw(y)
        c.hline(MX - hw, MX + hw, y,
                C("7a4841") if y < MFY0 + 11 else C("c09473"))
    for y in range(MFY0 + 4, MFY1 - 2):                         # the cold plane
        hw = m_hw(y)
        c.hline(MX - hw, MX - hw + 4, y, C("d7b594"))
        c.set(MX - hw, y, C("3c5e8b"))
    for y in range(MFY0 + 16, MFY1 - 4):                        # the far side
        hw = m_hw(y)                                            # falls away
        c.hline(MX + hw - 3, MX + hw, y, C("7a4841"))
    c.hline(MX - 9, MX + 2, MFY1 - 4, C("d7b594"))              # the lit chin
    c.hline(MX - 7, MX, MFY1 - 3, C("d7b594"))
    c.hline(MX - 5, MX - 1, MFY1 - 2, C("e7d5b3"))
    for (dy, hw_, lean, col) in ((21, 5, 0.3, "d7b594"),
                                 (19, 4, -0.25, "c09473")):
        cx0 = MX - 8 if lean > 0 else MX + 7
        for (ddy, hw2) in m_ell(hw_, hw_):
            if hw2 < 0:
                continue
            y = MFY0 + dy + ddy
            cx = cx0 + int(ddy * lean)
            fhw = m_hw(y) - 1
            c.hline(max(MX - fhw, cx - hw2), min(MX + fhw, cx + hw2), y, C(col))
    for k in range(4):                                          # the healed cut
        c.set(MX - 11 + k, MFY0 + 21 + k // 2, C("7a4841"))
    for k in range(26):                                         # the fringe
        x = MX - 13 + k
        drop = 5 + int(round(1.3 * math.sin(k * 0.38)
                             + 0.8 * math.sin(k * 0.81)))
        if 5 <= k <= 8:
            drop += 2
        if 17 <= k <= 19:
            drop += 2
        if k == 10:
            drop -= 2
        c.vline(x, MFY0 - 3, MFY0 + drop, C("4d2b32"))
        c.set(x, MFY0 + drop + 1, C("341c27"))
    c.hline(MX - 12, MX - 5, MFY0 + 13, C("602c2c"))            # brows, unmatched
    c.hline(MX - 11, MX - 6, MFY0 + 14, C("341c27"))
    c.hline(MX + 4, MX + 11, MFY0 + 12, C("602c2c"))
    c.hline(MX + 5, MX + 10, MFY0 + 13, C("341c27"))
    c.set(MX - 9, MFY0 + 13, C("c09473"))                       # THE SCAR, one
    c.set(MX - 9, MFY0 + 14, C("c09473"))                       # unbroken line
    c.set(MX - 9, MFY0 + 12, C("c09473"))
    c.set(MX - 8, MFY0 + 11, C("d7b594"))
    c.set(MX - 8, MFY0 + 10, C("d7b594"))
    c.set(MX - 9, MFY0 + 15, C("7a4841"))
    c.hline(MX - 11, MX - 7, MFY0 + 15, C("884b2b"))
    c.hline(MX - 12, MX - 6, MFY0 + 17, C("090a14"))            # the eyes, on
    c.hline(MX - 11, MX - 7, MFY0 + 18, C("090a14"))            # the screen
    c.hline(MX + 5, MX + 10, MFY0 + 16, C("090a14"))
    c.hline(MX + 6, MX + 9, MFY0 + 17, C("090a14"))
    c.set(MX - 10, MFY0 + 16, C("73bed3"))                      # its catchlight
    c.set(MX + 6, MFY0 + 15, C("3c5e8b"))
    c.vline(MX - 2, MFY0 + 16, MFY0 + 24, C("7a4841"))          # the nose
    c.vline(MX - 1, MFY0 + 17, MFY0 + 22, C("c09473"))
    c.vline(MX, MFY0 + 18, MFY0 + 23, C("d7b594"))
    for k in range(3):
        c.hline(MX - 2 + k // 2, MX + 1 - k // 3, MFY0 + 23 + k,
                C("d7b594") if k < 2 else C("e7d5b3"))
    c.set(MX - 3, MFY0 + 25, C("7a4841"))
    c.set(MX + 1, MFY0 + 25, C("7a4841"))
    c.hline(MX - 5, MX + 1, MFY0 + 29, C("884b2b"))             # the mouth
    c.set(MX + 2, MFY0 + 30, C("7a4841"))
    c.hline(MX - 3, MX, MFY0 + 30, C("c09473"))
    # ---- her left arm folded up, hand at the ear cup: she is listening
    limb(MX - 20, 356, MX - 34, 344, 9, 8, ox_ramp, 0.5,
         C("253a5e"), C("241527"))
    limb(MX - 34, 344, MX - 30, 328, 8, 6, ox_ramp, 0.5,
         C("253a5e"), C("241527"))
    c.hline(MX - 37, MX - 24, 330, C("341c27"))                 # the pushed cuff
    c.hline(MX - 37, MX - 24, 331, C("241527"))
    for y in range(308, 322):                                   # the hand, small
        t = (y - 308) / 14.0                                    # and pressed to
        hw = int(5 - abs(t - 0.6) * 4)                          # the cup
        c.hline(MX - 31 - hw, MX - 31 + hw, y,
                C("d7b594") if t > 0.45 else C("c09473"))
        c.set(MX - 31 - hw, y, C("e7d5b3"))
        c.set(MX - 31 + hw, y, C("7a4841"))
    for k in range(3):                                          # fingers curled
        c.hline(MX - 29 + k, MX - 24 + k, 306 + k * 3, C("c09473"))
        c.set(MX - 29 + k, 306 + k * 3, C("d7b594"))
    # ---- her right forearm out to the set, keying it
    limb(MX + 20, 356, MX + 34, 372, 9, 8, ox_ramp, 0.5,
         C("a53030"), C("241527"))
    limb(MX + 34, 372, 848, 380, 8, 6, ox_ramp, 0.5,
         C("a53030"), C("241527"), across=True)
    c.vline(MX + 38, 366, 386, C("341c27"))
    c.vline(MX + 39, 367, 385, C("241527"))
    for y in range(376, 388):                                   # the hand, flat
        t = (y - 376) / 12.0
        hw = int(8 - abs(t - 0.4) * 6)
        c.hline(848 - hw, 848 + hw, y, C("c09473") if t > 0.45 else C("d7b594"))
        c.set(848 - hw, y, C("e7d5b3"))
        c.set(848 + hw, y, C("7a4841"))

    # a coil of spare cable on the floor by the rack
    for (rx_, ry_, cy_) in ((22, 8, 508), (16, 6, 512), (11, 4, 510)):
        for a in range(0, 360, 3):
            c.set(int(722 + math.cos(math.radians(a)) * rx_),
                  int(cy_ + math.sin(math.radians(a)) * ry_), C("090a14"))
            c.set(int(722 + math.cos(math.radians(a)) * rx_),
                  int(cy_ - 1 + math.sin(math.radians(a)) * ry_), C("151d28"))

    # ---------------------------------------------------- runtime overlays --
    # candle glow (soft alpha, breathes and gutters at runtime)
    gw, gh = 240, 170
    glow = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    gp = glow.load()
    r, g, b, _ = C("e8c170")
    for y in range(gh):
        for x in range(gw):
            d = ((x - gw / 2) / (gw / 2)) ** 2 + ((y - gh / 2) / (gh / 2)) ** 2
            if d < 1.0:
                gp[x, y] = (r, g, b, int(64 * (1.0 - d) ** 2))

    # VU needle strip: 3 frames, 16x12, drawn over the baked dial faces
    strip = Canvas(48, 12)
    for f in range(3):
        ox = f * 16
        strip.rect(ox, 0, ox + 15, 11, C("172038"))
        strip.rect(ox + 1, 1, ox + 14, 10, C("253a5e"))
        strip.rect(ox + 2, 2, ox + 13, 9, C("172038"))
        for k in range(4):                                    # the scale ticks
            strip.set(ox + 3 + k * 3, 3, C("819796") if k < 3 else C("a53030"))
        strip.set(ox + 13, 3, C("a53030"))
        strip.set(ox + 13, 4, C("752438"))
        tip = (ox + 4, 3) if f == 0 else ((ox + 8, 2) if f == 1 else (ox + 12, 3))
        x0, y0 = ox + 8, 9
        for k in range(9):
            t = k / 8.0
            strip.set(int(x0 + (tip[0] - x0) * t), int(y0 + (tip[1] - y0) * t),
                      C("c7cfcc") if k > 2 else C("819796"))
        strip.set(ox + 8, 9, C("394a50"))
    return c, glow, strip



def make_menu_map_thumb() -> Canvas:
    """The map-select screen's painted preview of transit: the diamond
    district, its road grid, the woods, the rail line — stylized, not a
    live bake. (This used to justify that with "every raid rolls its own
    layout anyway" — false since the fixed-district change: build() defaults
    to DISTRICT_SEED "transit-01", so every deploy is bit-identical and a
    faithful bake IS possible if this is ever redone.)"""
    rng = random.Random(f"{SEED}:mapthumb")
    c = Canvas(96, 96)
    cx = cy = 48
    for y in range(96):
        for x in range(96):
            if abs(x - cx) + abs(y - cy) * 2 < 88:
                c.set(x, y, C("10141f"))
    for y in range(96):                        # the playable diamond
        for x in range(96):
            if abs(x - cx) + abs(y - cy) * 2 < 62:
                c.set(x, y, C("202e37"))
    for i in range(4):                         # road grid, both axes
        off = -24 + i * 16 + rng.randint(-2, 2)
        for t in range(-40, 41):
            px_, py_ = cx + t + off, cy + t // 2 - off // 2
            if abs(px_ - cx) + abs(py_ - cy) * 2 < 60:
                c.set(px_, py_, C("151d28"))
            px2, py2 = cx + t - off, cy - t // 2 - off // 2
            if abs(px2 - cx) + abs(py2 - cy) * 2 < 60:
                c.set(px2, py2, C("151d28"))
    for i in range(60):                        # the woods, one corner
        bx = cx - 20 + rng.randint(-8, 8)
        by = cy + 8 + rng.randint(-5, 5)
        if abs(bx - cx) + abs(by - cy) * 2 < 58:
            c.set(bx, by, C("19332d"))
            c.set(bx + 1, by, C("19332d"))
    for t in range(-30, 31):                   # the rail line
        px_, py_ = cx + t, cy - 10 + t // 4
        if abs(px_ - cx) + abs(py_ - cy) * 2 < 58:
            c.set(px_, py_, C("341c27"))
    for i in range(7):                         # town blocks
        bx = cx + 6 + rng.randint(-3, 12)
        by = cy + 2 + rng.randint(-8, 8)
        if abs(bx - cx) + abs(by - cy) * 2 < 52:
            c.rect(bx, by, bx + 3, by + 2, C("884b2b"))
    c.rect(cx - 2, cy - 2, cx + 1, cy, C("819796"))   # the courtyard glint
    return c

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


def make_pylon(variant: int) -> tuple[Canvas, tuple, list | None]:
    """A lattice power pylon. 0-1 stand, 2 leans with a bent arm, 3 is
    snapped off above the waist — the grid went down with everything else
    (user: "some broken ones too"). The wires themselves are their own
    sprites so a span can be missing without moving the towers."""
    rng = random.Random(f"{SEED}:pylon:{variant}")
    broken = variant == 3
    lean = variant == 2
    # a standing tower is ALWAYS this tall: the spans hang off a fixed
    # crossarm height, and a municipal line is one design repeated with
    # wear, never per-piece variety (standing rule)
    h = 56 if not broken else rng.randint(24, 30)
    half_base, half_top = 11, 4
    steel, dark = C("577277"), C("394a50")
    # generous margins: the lean pushes the top sideways and the crossarms
    # reach 14px either side, and the clip audit fails the build on contact
    c = Canvas(56, h + 20)
    ox, oy = 26, h + 12
    def shift(y: int) -> int:            # the lean grows toward the top
        return int((oy - y) * 0.14) if lean else 0
    for y in range(oy - h, oy + 1):
        f = (oy - y) / float(h)
        half = int(half_base + (half_top - half_base) * f)
        s = shift(y)
        c.set(ox - half + s, y, steel)   # the two legs
        c.set(ox + half + s, y, steel)
        if (oy - y) % 6 == 0:            # horizontal braces
            for x in range(ox - half + s, ox + half + s + 1):
                c.set(x, y, dark)
        if (oy - y) % 3 == 0:            # the cross bracing between them
            span = max(1, half)
            for k in range(-span, span + 1):
                yy = y - abs(k) // 2
                if oy - h <= yy <= oy:
                    c.set(ox + k + s, yy, dark)
    if not broken:                        # the crossarms that carry the wires
        for arm_y in (oy - h + 4, oy - h + 12):
            s = shift(arm_y)
            for x in range(ox - 14 + s, ox + 15 + s):
                c.set(x, arm_y, steel)
            for x in (ox - 14 + s, ox - 7 + s, ox + 7 + s, ox + 14 + s):
                c.set(x, arm_y - 1, dark)     # the insulators
                c.set(x, arm_y - 2, C("819796"))
    else:                                 # a torn-off top, cables trailing
        for k in range(6):
            c.set(ox + rng.randint(-6, 6), oy - h - rng.randint(0, 3), C("241527"))
    c.outline_auto()
    cropped, origin = crop_canvas(c, (ox, oy))
    return cropped, origin, ["diamond", 7, 4]


def make_power_wire(variant: int) -> tuple[Canvas, tuple, list | None]:
    """One span of catenary between two pylons, drawn along the map's +x
    axis (screen down-right). Variant 1 is SNAPPED: it leaves one tower,
    sags, and ends in mid-air where the rest of it came down."""
    span_cells = 6
    w = span_cells * 32
    c = Canvas(w + 20, 130)
    ox, oy = 8, 20
    snapped = variant == 1
    end = int(w * 0.42) if snapped else w
    for line, droop in ((0, 9.0), (1, 13.0)):
        for i in range(end):
            f = i / float(w)
            # a real catenary: the sag is deepest mid-span
            sag = droop * (1.0 - (2.0 * f - 1.0) ** 2)
            y = oy + int(i * 0.5 + sag) + line * 7
            c.set(ox + i, y, C("241527"))
    if snapped:                           # the broken end hangs and frays
        f = end / float(w)
        for k in range(10):
            y = oy + int(end * 0.5 + 9.0 * (1.0 - (2.0 * f - 1.0) ** 2)) + k
            c.set(ox + end + k // 3, y, C("241527"))
    c.outline_auto()
    cropped, origin = crop_canvas(c, (ox, oy))
    return cropped, origin, None


def make_telegraph_wire(span_cells: int) -> tuple[Canvas, tuple, list | None]:
    """The wires between two telegraph poles, one span. FOUR of them — two
    per crossarm, off the OUTER insulators only (the centre insulator
    deliberately gets none; see the loop comment). This said "six — three
    per crossarm", which is exactly the version that was rejected for
    merging into a solid dark band. They run down the map's +x axis, which
    is screen down-right at 32 x 16 px per cell.

    Thinner and slacker than the power catenary on purpose: a transmission
    line is two heavy conductors, a telegraph route is a bundle of thin ones,
    and at native resolution that difference is the whole read. The origin is
    the near pole's BASE, so placing it is just "put it where that pole is"."""
    w = span_cells * 32
    h = span_cells * 16          # the run drops a full half-cell per cell
    # the canvas has to hold the whole DESCENT, not just the pole height:
    # the far end sits h px below the near one, plus the sag
    c = Canvas(w + 32, h + 80)
    ox = 16
    oy = 48                                      # the near pole's base
    for (arm_up, arm_span) in TELE_ARMS:
        # only the OUTER insulators get a wire. All three reads as a solid
        # dark band at this scale — six near-parallel 1 px lines three pixels
        # apart merge into a mass, especially once anything outlines them.
        for ins in (-arm_span + 1, arm_span - 1):
            # sag scales with the span: a long run droops further
            droop = 2.5 + span_cells * 0.55
            for i in range(w):
                f = i / float(w)
                sag = droop * (1.0 - (2.0 * f - 1.0) ** 2)
                x = ox + ins + i
                y = oy - arm_up + int(i * 0.5 + sag) - 1
                c.set(x, y, C("241527"))
    # NO outline_auto here. It draws a border around every run, and on lines
    # this close together the borders meet and fill the gaps — the span came
    # out as a solid dark ramp beside the track.
    cropped, origin = crop_canvas(c, (ox, oy))
    return cropped, origin, None


def make_utility_box() -> tuple[Canvas, tuple, list | None]:
    """The yellow cabinet on the back of the tower by the relay: where the
    district's lines come up out of the ground (user spec)."""
    c = Canvas(30, 44)
    ox, oy = 6, 36
    w, d, h = 16, 8, 18
    body, dark, lite = C("de9e41"), C("884b2b"), C("e8c170")
    bottoms = iso_prism(c, ox, oy - d - h, w, d, h, body, dark, lite)
    for x in range(ox + 2, ox + w - 1):        # the door seam and its hinges
        c.set(x, max(bottoms) + h // 2, dark)
    c.set(ox + w - 3, max(bottoms) + h // 2 - 3, C("241527"))
    for k in range(3):                          # hazard flash across the door
        c.set(ox + 4 + k * 2, max(bottoms) + 4 + k, C("241527"))
    # the conduit going down into the ground
    for y in range(max(bottoms) + h, max(bottoms) + h + 4):
        c.set(ox + w // 2, y, C("394a50"))
    c.outline_auto()
    cropped, origin = crop_canvas(c, (ox + w // 2, max(bottoms) + h + 3))
    return cropped, origin, ["diamond", 7, 4]


def make_toolbox(variant: int) -> tuple[Canvas, tuple, list | None]:
    """A tool chest left where somebody put it down. Iso box with a lit
    top face, a carry handle, and on some of them an open lid with tools
    showing — the scrapyard is where things get taken apart (user)."""
    rng = random.Random(f"{SEED}:toolbox:{variant}")
    w = rng.choice((12, 16))           # iso prisms want w == 2*d, d even
    d = w // 2
    h = rng.randint(6, 9)
    body, dark, lite = (C(n) for n in
                        [("cf573c", "a53030", "da863e"),
                         ("577277", "394a50", "819796"),
                         ("de9e41", "884b2b", "e8c170"),
                         ("3c5e8b", "253a5e", "73bed3")][variant % 4])
    c = Canvas(w + 10, h + d + 14)
    ox, oy = 5, 6                      # top-left; the prism grows downward
    bottoms = iso_prism(c, ox, oy, w, d, h, body, dark, lite)
    hy = oy + d // 2                   # the top face's middle row
    for i in range(w // 4, w - w // 4):     # the carry handle
        c.set(ox + i, hy, C("241527"))
    c.set(ox + w // 4, hy + 1, C("241527"))
    c.set(ox + w - w // 4 - 1, hy + 1, C("241527"))
    if variant % 2:                    # some stand open, tools showing
        for i in range(w // 4, w - w // 4, 3):
            c.set(ox + i, oy - 2, C("819796"))
            c.set(ox + i, oy - 1, C("577277"))
    c.outline_auto()
    base = max(bottoms) + h
    cropped, origin = crop_canvas(c, (ox + w // 2, base))
    return cropped, origin, ["diamond", w // 2 - 1, max(2, d // 2)]


def make_interior_lamp() -> tuple[Canvas, tuple, list | None]:
    """A room's ceiling fixture: a tin shade on a short flex with the bulb
    showing under it. It hangs INSIDE, so it only reads once the roof fades
    — which is exactly when a lit room should matter. No collider: you walk
    under a light, not into it."""
    c = Canvas(20, 26)
    ox, oy = 10, 24
    top, bot = 7, 12
    # the flex starts clear of the canvas edge — outline_auto needs a
    # margin, and the clip audit fails the build if content touches it
    for y in range(2, top):                       # the flex into the ceiling
        c.set(ox, y, C("241527"))
    for y in range(top, bot + 1):                 # the shade, a tin cone
        half = 2 + (y - top)
        for x in range(ox - half, ox + half + 1):
            col = C("577277")
            if x <= ox - half + 1:
                col = C("819796")                 # lit north-west face
            elif x >= ox + half - 1:
                col = C("394a50")                 # shaded east face
            c.set(x, y, col)
    rim = 2 + (bot - top)
    for x in range(ox - rim, ox + rim + 1):       # the rim under the cone
        c.set(x, bot + 1, C("394a50"))
    for (dx, dy) in ((0, 2), (-1, 3), (0, 3), (1, 3), (0, 4)):
        c.set(ox + dx, bot + dy, C("e8c170"))     # the bulb
    c.outline_auto()
    cropped, origin = crop_canvas(c, (ox, oy))
    return cropped, origin, None


def make_cable(axis: str) -> tuple[Canvas, tuple, list | None]:
    """One cell of flex pinned along the floor. STANDING RULE: anything
    powered has to SHOW where its power comes from, so a room light's cable
    is a real object running cell by cell to the wall its box is bolted to.
    'x' runs screen down-right, 'y' screen down-left — the two iso axes."""
    c = Canvas(38, 24)
    ox, oy = 19, 11
    # grey flex over a black shadow: dark enough to read on a concrete
    # floor, light enough to read on a dark wood one — a near-black cable
    # simply vanished into both
    for i in range(-16, 17):
        x = ox + i
        rise = i // 2 if axis == "x" else -(i // 2)
        y = oy + rise
        c.set(x, y, C("394a50") if i % 6 else C("577277"))   # cleats
        c.set(x, y + 1, C("10141f"))              # the shadow it casts
    cropped, origin = crop_canvas(c, (ox, oy))
    return cropped, origin, None


def make_leaves() -> list[Image.Image]:
    """Falling-leaf strips: 2 flutter frames per color (green, bright,
    dry). Tiny palette sprites the environment tumbles off shedder oaks."""
    # indexes 0-1: green canopy leaves. 2-3: AUTUMN reds — only the autumn
    # grove drops those (user: "the green only has green")
    combos = [("25562e", "19332d"), ("468232", "25562e"),
              ("cf573c", "884b2b"), ("da863e", "602c2c")]
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
    # 4-5: NEEDLES. A pine that sheds nothing reads as dead (user), but a
    # conifer dropping broadleaf leaves reads as a bug — so they get their
    # own drop: a thin spine, not a blade, one fresh and one dried out.
    # brighter than the canopy they fall from, or they vanish into the
    # forest floor they land on (a dark needle over dark ground is a
    # needle nobody ever sees)
    for (a, b) in [("468232", "25562e"), ("ad7757", "884b2b")]:
        ca, cb = C(a), C(b)
        img = Image.new("RGBA", (6, 3), (0, 0, 0, 0))
        img.putpixel((0, 0), cb)    # frame 0: falling at a slant
        img.putpixel((1, 1), ca)
        img.putpixel((2, 2), ca)
        img.putpixel((4, 0), ca)    # frame 1: turned edge-on, near vertical
        img.putpixel((4, 1), ca)
        img.putpixel((4, 2), cb)
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
    # NOTE: door_ used to sit here, and hid a real clip for months — the east
    # door's leaf swung straight off the left of its canvas. Doors are audited.
    _EDGE_OK = ("roof_tile_", "roof_fascia_", "roof_eave_", "roof_corner_",
                "seg_", "seg2_", "post_", "post2_", "ui_grabber",
                "floor_edge_",
                # UI art, not world sprites: a portrait plate is meant to
                # fill its frame edge to edge
                "warden_portrait")
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
    for name, kind in VEHICLE_KINDS.items():
        if name in manifest["props"]:
            manifest["props"][name]["vehicle_kind"] = kind
    for name, extra in DOOR_COLLIDERS.items():
        manifest["props"][name]["collider_open"] = extra["open"]
        manifest["props"][name]["collider_open_out"] = extra["open_out"]
        manifest["props"][name]["collider_jambs"] = extra["jambs"]
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
    for i, spark in enumerate(make_spark_frames()):
        spark.save(OUT / f"spark_{i}.png")            # fx: bright alpha
    for i in range(3):
        crack_c, _, _ = make_gem_cracked(i)
        crack_c.img.save(OUT / f"studio_gem_crack_{i}.png")
    for i, shard in enumerate(make_gem_shards()):
        shard.save(OUT / f"studio_shard_{i}.png")
    core_c, _, _ = make_signal_core()
    core_c.img.save(OUT / "studio_signal.png")
    make_studio_tag().save(OUT / "studio_tag.png")
    thumb_canvas = make_menu_map_thumb()
    assert_palette(thumb_canvas.img, "menu_map_transit")
    thumb_canvas.img.save(OUT / "menu_map_transit.png")
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
    # the contact sheet is a DEV artifact — nothing in the game loads it.
    # Kept out of art/gen so Godot never imports it and, more to the
    # point, so the deploy's texture prewarm never pays for it: at 512 KB
    # it was the single largest file in the loaded art folder.
    dev_out = ROOT / "docs"
    dev_out.mkdir(exist_ok=True)
    prev.save(dev_out / "preview.png")

    print(f"OK: wrote {len(entries) + 6} files to {OUT}")

if __name__ == "__main__":
    main()
