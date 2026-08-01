#!/usr/bin/env python3
"""Generates the SPOILS bitmap pixel font (5x7 monospace caps) as a BMFont
.fnt + atlas PNG that Godot imports as a FontFile. A vector font rasterized
at tiny sizes is what made the UI blurry — a bitmap font is crisp by
construction at every integer scale.

Glyphs are white-on-transparent (NOT palette colors): the UI theme multiplies
them by Apollo palette colors at runtime, same idea as light textures.
Lowercase letters map to the uppercase glyphs (stencil style).
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "art" / "gen"

GLYPHS = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ####", "#    ", "#    ", "#  ##", "#   #", "#   #", " ### "],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "2": [" ### ", "#   #", "    #", "  ## ", " #   ", "#    ", "#####"],
    "3": ["#### ", "    #", "   # ", "  ## ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "],
    " ": ["     ", "     ", "     ", "     ", "     ", "     ", "     "],
    "!": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "    #", "  ## ", "  #  ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "],
    ",": ["     ", "     ", "     ", "     ", "     ", "  ## ", " ##  "],
    ":": ["     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", "     "],
    ";": ["     ", " ##  ", " ##  ", "     ", " ##  ", "  #  ", " #   "],
    "-": ["     ", "     ", "     ", " ### ", "     ", "     ", "     "],
    "+": ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    "=": ["     ", "     ", "#####", "     ", "#####", "     ", "     "],
    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    "\\": ["#    ", "#    ", " #   ", "  #  ", "   # ", "    #", "    #"],
    "(": ["  ## ", " #   ", "#    ", "#    ", "#    ", " #   ", "  ## "],
    ")": [" ##  ", "   # ", "    #", "    #", "    #", "   # ", " ##  "],
    "[": [" ### ", " #   ", " #   ", " #   ", " #   ", " #   ", " ### "],
    "]": [" ### ", "   # ", "   # ", "   # ", "   # ", "   # ", " ### "],
    "<": ["   # ", "  #  ", " #   ", "#    ", " #   ", "  #  ", "   # "],
    ">": [" #   ", "  #  ", "   # ", "    #", "   # ", "  #  ", " #   "],
    "'": ["  #  ", "  #  ", "     ", "     ", "     ", "     ", "     "],
    "\"": [" # # ", " # # ", "     ", "     ", "     ", "     ", "     "],
    "_": ["     ", "     ", "     ", "     ", "     ", "     ", "#####"],
    "%": ["##  #", "##  #", "   # ", "  #  ", " #   ", "#  ##", "#  ##"],
    "*": ["     ", "# # #", " ### ", "#####", " ### ", "# # #", "     "],
    "#": [" # # ", "#####", " # # ", " # # ", " # # ", "#####", " # # "],
}

CELL_W, CELL_H = 6, 8  # 5x7 glyph + 1px spacing baked into the cell
COLS = 16


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    order = sorted(GLYPHS.keys(), key=ord)
    rows = (len(order) + COLS - 1) // COLS
    atlas = Image.new("RGBA", (COLS * CELL_W, rows * CELL_H), (0, 0, 0, 0))

    entries: list[tuple[int, int, int]] = []  # (char_id, atlas_x, atlas_y)
    for i, ch in enumerate(order):
        ax, ay = (i % COLS) * CELL_W, (i // COLS) * CELL_H
        for y, row in enumerate(GLYPHS[ch]):
            for x, cell in enumerate(row):
                if cell == "#":
                    atlas.putpixel((ax + x, ay + y), (255, 255, 255, 255))
        entries.append((ord(ch), ax, ay))
        if ch.isalpha():  # lowercase input renders the uppercase glyph
            entries.append((ord(ch.lower()), ax, ay))

    atlas.save(OUT / "spoils_font.png")

    lines = [
        'info face="Spoils5x7" size=8 bold=0 italic=0 charset="" unicode=1 '
        'stretchH=100 smooth=0 aa=0 padding=0,0,0,0 spacing=0,0 outline=0',
        f"common lineHeight=10 base=7 scaleW={atlas.width} scaleH={atlas.height} "
        "pages=1 packed=0 alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0",
        'page id=0 file="spoils_font.png"',
        f"chars count={len(entries)}",
    ]
    for char_id, ax, ay in sorted(entries):
        lines.append(
            f"char id={char_id} x={ax} y={ay} width={CELL_W} height={CELL_H} "
            f"xoffset=0 yoffset=0 xadvance=6 page=0 chnl=15")
    (OUT / "spoils_font.fnt").write_text("\n".join(lines) + "\n")
    print(f"OK: {len(order)} glyphs ({len(entries)} char entries) -> spoils_font.fnt/.png")


if __name__ == "__main__":
    main()
