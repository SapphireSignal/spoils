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
    print(f"OK: {len(order)} glyphs ({len(entries)} char entries) -> spoils_font.fnt/.png")


if __name__ == "__main__":
    main()
