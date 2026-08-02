#!/usr/bin/env python3
"""Generates the SPOILS UI font: a lowercase-only proportional pixel font
(BMFont .fnt + atlas) that Godot imports as a FontFile.

Design: x-height 5, ascenders to 7, descenders 2 (9px glyph box, baseline 7).
Proportional widths. BOTH uppercase and lowercase character codes map to the
lowercase glyphs — the user wants no capital letters anywhere, so any string
renders lowercase without touching game code.

Glyphs are white-on-transparent (not palette colors): the UI theme tints them
at runtime, same idea as light textures.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art" / "gen"

# 9 rows per glyph: rows 0-6 above/at baseline (base=7), rows 7-8 descender
GLYPHS = {
    "a": ["    ", "    ", " ## ", "   #", " ###", "#  #", " ###", "    ", "    "],
    "b": ["#   ", "#   ", "### ", "#  #", "#  #", "#  #", "### ", "    ", "    "],
    "c": ["    ", "    ", " ###", "#   ", "#   ", "#   ", " ###", "    ", "    "],
    "d": ["   #", "   #", " ###", "#  #", "#  #", "#  #", " ###", "    ", "    "],
    "e": ["    ", "    ", " ## ", "#  #", "####", "#   ", " ###", "    ", "    "],
    "f": [" ##", "#  ", "###", "#  ", "#  ", "#  ", "#  ", "   ", "   "],
    "g": ["    ", "    ", " ###", "#  #", "#  #", "#  #", " ###", "   #", " ## "],
    "h": ["#   ", "#   ", "### ", "#  #", "#  #", "#  #", "#  #", "    ", "    "],
    "i": ["#", " ", "#", "#", "#", "#", "#", " ", " "],
    "j": ["  #", "   ", "  #", "  #", "  #", "  #", "  #", "  #", "## "],
    "k": ["#   ", "#   ", "#  #", "# # ", "##  ", "# # ", "#  #", "    ", "    "],
    "l": ["#", "#", "#", "#", "#", "#", "#", " ", " "],
    "m": ["     ", "     ", "#### ", "# # #", "# # #", "# # #", "# # #", "     ", "     "],
    "n": ["    ", "    ", "### ", "#  #", "#  #", "#  #", "#  #", "    ", "    "],
    "o": ["    ", "    ", " ## ", "#  #", "#  #", "#  #", " ## ", "    ", "    "],
    "p": ["    ", "    ", "### ", "#  #", "#  #", "#  #", "### ", "#   ", "#   "],
    "q": ["    ", "    ", " ###", "#  #", "#  #", "#  #", " ###", "   #", "   #"],
    "r": ["   ", "   ", "# #", "## ", "#  ", "#  ", "#  ", "   ", "   "],
    "s": ["    ", "    ", " ###", "#   ", " ## ", "   #", "### ", "    ", "    "],
    "t": [" # ", " # ", "###", " # ", " # ", " # ", "  #", "   ", "   "],
    "u": ["    ", "    ", "#  #", "#  #", "#  #", "#  #", " ###", "    ", "    "],
    "v": ["   ", "   ", "# #", "# #", "# #", "# #", " # ", "   ", "   "],
    "w": ["     ", "     ", "# # #", "# # #", "# # #", "# # #", " # # ", "     ", "     "],
    "x": ["    ", "    ", "#  #", " ## ", "  # ", " ## ", "#  #", "    ", "    "],
    "y": ["    ", "    ", "#  #", "#  #", "#  #", "#  #", " ###", "   #", " ## "],
    "z": ["    ", "    ", "####", "  # ", " #  ", "#   ", "####", "    ", "    "],
    "0": [" ## ", "#  #", "#  #", "#  #", "#  #", "#  #", " ## ", "    ", "    "],
    "1": [" # ", "## ", " # ", " # ", " # ", " # ", "###", "   ", "   "],
    "2": [" ## ", "#  #", "   #", "  # ", " #  ", "#   ", "####", "    ", "    "],
    "3": ["### ", "   #", "  # ", " ## ", "   #", "#  #", " ## ", "    ", "    "],
    "4": ["   #", "  ##", " # #", "#  #", "####", "   #", "   #", "    ", "    "],
    "5": ["####", "#   ", "### ", "   #", "   #", "#  #", " ## ", "    ", "    "],
    "6": [" ## ", "#   ", "### ", "#  #", "#  #", "#  #", " ## ", "    ", "    "],
    "7": ["####", "   #", "  # ", "  # ", " #  ", " #  ", " #  ", "    ", "    "],
    "8": [" ## ", "#  #", "#  #", " ## ", "#  #", "#  #", " ## ", "    ", "    "],
    "9": [" ## ", "#  #", "#  #", " ###", "   #", "   #", " ## ", "    ", "    "],
    " ": ["  ", "  ", "  ", "  ", "  ", "  ", "  ", "  ", "  "],
    ".": [" ", " ", " ", " ", " ", "#", "#", " ", " "],
    ",": ["  ", "  ", "  ", "  ", "  ", " #", " #", "# ", "  "],
    ":": [" ", " ", "#", "#", " ", "#", "#", " ", " "],
    ";": ["  ", "  ", " #", " #", "  ", " #", " #", "# ", "  "],
    "!": ["#", "#", "#", "#", "#", " ", "#", " ", " "],
    "?": [" ## ", "#  #", "   #", "  # ", "  # ", "    ", "  # ", "    ", "    "],
    "-": ["    ", "    ", "    ", "    ", "####", "    ", "    ", "    ", "    "],
    "+": ["   ", "   ", " # ", " # ", "###", " # ", " # ", "   ", "   "],
    "=": ["    ", "    ", "    ", "####", "    ", "####", "    ", "    ", "    "],
    "/": ["   #", "   #", "  # ", "  # ", " #  ", " #  ", "#   ", "    ", "    "],
    "\\": ["#   ", "#   ", " #  ", " #  ", "  # ", "  # ", "   #", "    ", "    "],
    "(": [" #", "# ", "# ", "# ", "# ", "# ", " #", "  ", "  "],
    ")": ["# ", " #", " #", " #", " #", " #", "# ", "  ", "  "],
    "[": ["##", "# ", "# ", "# ", "# ", "# ", "##", "  ", "  "],
    "]": ["##", " #", " #", " #", " #", " #", "##", "  ", "  "],
    "<": ["  #", " # ", "#  ", "#  ", " # ", "  #", "   ", "   ", "   "],
    ">": ["#  ", " # ", "  #", "  #", " # ", "#  ", "   ", "   ", "   "],
    "'": ["#", "#", " ", " ", " ", " ", " ", " ", " "],
    "\"": ["# #", "# #", "   ", "   ", "   ", "   ", "   ", "   ", "   "],
    "_": ["    ", "    ", "    ", "    ", "    ", "    ", "####", "    ", "    "],
    "%": ["#  #", "  # ", "  # ", " #  ", " #  ", "#   ", "#  #", "    ", "    "],
    "*": ["   ", "# #", " # ", "###", " # ", "# #", "   ", "   ", "   "],
    "#": ["    ", " # #", "####", " # #", "####", " # #", "    ", "    ", "    "],
}

GLYPH_H = 9
CELL_H = GLYPH_H + 1
COLS = 12


# ---------------------------------------------------------------------------
# THE TINY FONT. A second, much smaller cut for map labels — 3px x-height in a
# 6px box, against the main font's 5 in 9.
#
# It has to be DRAWN at this size, not scaled down from the big one: the main
# font is a bitmap, so asking for a smaller size resamples the glyphs and they
# go blurry. That is the same trap the changelog text hit. Legibility at three
# pixels is rough by nature; these are for one or two words on a map dot, not
# for prose.
# rows 0-1 ascender, 2-4 x-height, 5 descender. baseline 5.
TINY = {
    "a": ["   ", "   ", " ##", "# #", " ##", "   "],
    "b": ["#  ", "#  ", "## ", "# #", "## ", "   "],
    "c": ["   ", "   ", " ##", "#  ", " ##", "   "],
    "d": ["  #", "  #", " ##", "# #", " ##", "   "],
    "e": ["   ", "   ", " # ", "###", " ##", "   "],
    "f": ["  ", " #", "##", " #", " #", "  "],
    "g": ["   ", "   ", " ##", "# #", " ##", "## "],
    "h": ["#  ", "#  ", "## ", "# #", "# #", "   "],
    "i": ["#", " ", "#", "#", "#", " "],
    "j": ["  #", "   ", "  #", "  #", "  #", "## "],
    "k": ["#  ", "# #", "## ", "# #", "# #", "   "],
    "l": ["#", "#", "#", "#", "#", " "],
    "m": ["   ", "   ", "## ", "###", "# #", "   "],
    "n": ["   ", "   ", "## ", "# #", "# #", "   "],
    "o": ["   ", "   ", " # ", "# #", " # ", "   "],
    "p": ["   ", "   ", "## ", "# #", "## ", "#  "],
    "q": ["   ", "   ", " ##", "# #", " ##", "  #"],
    "r": ["   ", "   ", "## ", "#  ", "#  ", "   "],
    "s": ["   ", "   ", " ##", " # ", "## ", "   "],
    "t": [" #", " #", "##", " #", " #", "  "],
    "u": ["   ", "   ", "# #", "# #", " ##", "   "],
    "v": ["   ", "   ", "# #", "# #", " # ", "   "],
    "w": ["   ", "   ", "# #", "###", "## ", "   "],
    "x": ["   ", "   ", "# #", " # ", "# #", "   "],
    "y": ["   ", "   ", "# #", " ##", "  #", "## "],
    "z": ["   ", "   ", "## ", " # ", " ##", "   "],
    "0": [" # ", "# #", "# #", "# #", " # ", "   "],
    "1": [" # ", "## ", " # ", " # ", "###", "   "],
    "2": ["## ", "  #", " # ", "#  ", "###", "   "],
    "3": ["## ", "  #", " ##", "  #", "## ", "   "],
    "4": ["# #", "# #", "###", "  #", "  #", "   "],
    "5": ["###", "#  ", "## ", "  #", "## ", "   "],
    "6": [" ##", "#  ", "###", "# #", "###", "   "],
    "7": ["###", "  #", " # ", " # ", " # ", "   "],
    "8": ["###", "# #", "###", "# #", "###", "   "],
    "9": ["###", "# #", "###", "  #", "## ", "   "],
    " ": ["  ", "  ", "  ", "  ", "  ", "  "],
    "-": ["   ", "   ", "   ", "###", "   ", "   "],
    ":": [" ", " ", "#", " ", "#", " "],
    "'": ["#", "#", " ", " ", " ", " "],
}
TINY_H = 6
TINY_BASE = 5


def build(glyphs: dict, height: int, base: int, name: str, size: int,
          line_height: int) -> int:
    order = sorted(glyphs.keys(), key=ord)
    cell_w = max(len(rows[0]) for rows in glyphs.values()) + 1
    rows_n = (len(order) + COLS - 1) // COLS
    atlas = Image.new("RGBA", (COLS * cell_w, rows_n * (height + 2)), (0, 0, 0, 0))
    entries: list[tuple[int, int, int, int]] = []
    for i, ch in enumerate(order):
        ax, ay = (i % COLS) * cell_w, (i // COLS) * (height + 2)
        rows = glyphs[ch]
        width = len(rows[0])
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell == "#":
                    atlas.putpixel((ax + x, ay + y), (255, 255, 255, 255))
        entries.append((ord(ch), ax, ay, width))
        if ch.isalpha():
            entries.append((ord(ch.upper()), ax, ay, width))
    atlas.save(OUT / f"{name}.png")
    lines = [
        f'info face="{name}" size={size} bold=0 italic=0 charset="" unicode=1 '
        'stretchH=100 smooth=0 aa=0 padding=0,0,0,0 spacing=0,0 outline=0',
        f"common lineHeight={line_height} base={base} scaleW={atlas.width} "
        f"scaleH={atlas.height} pages=1 packed=0 alphaChnl=1 redChnl=0 "
        "greenChnl=0 blueChnl=0",
        f'page id=0 file="{name}.png"',
        f"chars count={len(entries)}",
    ]
    for char_id, ax, ay, width in sorted(entries):
        lines.append(
            f"char id={char_id} x={ax} y={ay} width={width} height={height} "
            f"xoffset=0 yoffset=0 xadvance={width + 1} page=0 chnl=15")
    (OUT / f"{name}.fnt").write_text(chr(10).join(lines) + chr(10))
    return len(order)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    order = sorted(GLYPHS.keys(), key=ord)
    cell_w = max(len(rows[0]) for rows in GLYPHS.values()) + 1
    rows_n = (len(order) + COLS - 1) // COLS
    atlas = Image.new("RGBA", (COLS * cell_w, rows_n * CELL_H), (0, 0, 0, 0))

    entries: list[tuple[int, int, int, int]] = []  # (char_id, x, y, width)
    for i, ch in enumerate(order):
        ax, ay = (i % COLS) * cell_w, (i // COLS) * CELL_H
        rows = GLYPHS[ch]
        width = len(rows[0])
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell == "#":
                    atlas.putpixel((ax + x, ay + y), (255, 255, 255, 255))
        entries.append((ord(ch), ax, ay, width))
        if ch.isalpha():  # capitals render the lowercase glyph too
            entries.append((ord(ch.upper()), ax, ay, width))

    atlas.save(OUT / "spoils_font.png")

    lines = [
        'info face="SpoilsLower" size=9 bold=0 italic=0 charset="" unicode=1 '
        'stretchH=100 smooth=0 aa=0 padding=0,0,0,0 spacing=0,0 outline=0',
        f"common lineHeight=11 base=7 scaleW={atlas.width} scaleH={atlas.height} "
        "pages=1 packed=0 alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0",
        'page id=0 file="spoils_font.png"',
        f"chars count={len(entries)}",
    ]
    for char_id, ax, ay, width in sorted(entries):
        lines.append(
            f"char id={char_id} x={ax} y={ay} width={width} height={GLYPH_H} "
            f"xoffset=0 yoffset=0 xadvance={width + 1} page=0 chnl=15")
    (OUT / "spoils_font.fnt").write_text("\n".join(lines) + "\n")
    n_tiny = build(TINY, TINY_H, TINY_BASE, "spoils_tiny", 6, 7)
    print(f"OK: {len(order)} glyphs ({len(entries)} char entries) -> spoils_font.fnt/.png")
    print(f"OK: {n_tiny} tiny glyphs -> spoils_tiny.fnt/.png")


if __name__ == "__main__":
    main()
