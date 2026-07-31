#!/usr/bin/env python3
"""Generates docs/banner.png — the repo README wordmark. Same rules as the
game art: Apollo palette only, deterministic, never hand-edited."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"

PAL = {}
for line in (ROOT / "art" / "palettes" / "apollo.gpl").read_text().splitlines():
    parts = line.split()
    if len(parts) == 4 and parts[0].isdigit():
        PAL[parts[3]] = (int(parts[0]), int(parts[1]), int(parts[2]), 255)

FONT = {  # 5x7 pixel capitals
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
}

SCALE = 8
WORD = "SPOILS"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / ".gdignore").write_text("")  # keep the Godot importer out of docs/

    # letters at 1x first
    word_w = len(WORD) * 6 - 1
    text = Image.new("RGBA", (word_w, 7), (0, 0, 0, 0))
    for i, ch in enumerate(WORD):
        for y, row in enumerate(FONT[ch]):
            for x, cell in enumerate(row):
                if cell == "#":
                    col = PAL["c7cfcc"] if y < 4 else PAL["819796"]
                    text.putpixel((i * 6 + x, y), col)
    # 1px outline
    out = Image.new("RGBA", (word_w + 2, 9), (0, 0, 0, 0))
    px = text.load()
    opx = out.load()
    for y in range(7):
        for x in range(word_w):
            if px[x, y][3] > 0:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if opx[x + 1 + dx, y + 1 + dy][3] == 0:
                            opx[x + 1 + dx, y + 1 + dy] = PAL["090a14"]
    for y in range(7):
        for x in range(word_w):
            if px[x, y][3] > 0:
                opx[x + 1, y + 1] = px[x, y]
    word = out.resize((out.width * SCALE, out.height * SCALE), Image.NEAREST)

    # the raider, idle facing camera (char sheet row 2 = S, col 0), at 4x
    sheet = Image.open(ROOT / "art" / "gen" / "char.png")
    raider = sheet.crop((0, 2 * 40, 32, 3 * 40))
    raider = raider.resize((32 * 4, 40 * 4), Image.NEAREST)

    pad = 28
    W = word.width + raider.width + pad * 3
    H = max(word.height, raider.height) + pad * 2
    banner = Image.new("RGBA", (W, H), PAL["10141f"])
    # frame + faint floor line to ground the character
    for x in range(W):
        for t in (0, 1):
            banner.putpixel((x, t), PAL["577277"])
            banner.putpixel((x, H - 1 - t), PAL["577277"])
    for y in range(H):
        for t in (0, 1):
            banner.putpixel((t, y), PAL["577277"])
            banner.putpixel((W - 1 - t, y), PAL["577277"])
    banner.paste(word, (pad, (H - word.height) // 2), word)
    ground_y = (H + raider.height) // 2 - 2
    for x in range(word.width + pad * 2 - 8, W - pad + 12):
        if 0 <= x < W - 2 and x % 2 == 0:
            banner.putpixel((x, ground_y), PAL["202e37"])
    banner.paste(raider, (word.width + pad * 2, (H - raider.height) // 2), raider)

    banner.save(OUT / "banner.png")
    print(f"OK: wrote {OUT / 'banner.png'} ({W}x{H})")


if __name__ == "__main__":
    main()
