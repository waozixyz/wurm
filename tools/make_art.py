#!/usr/bin/env python3
"""Extend the garden stage sheet with new art, drawn pixel by pixel in the
sheet's own palette at 16 pixels and doubled, like the committed tiles:

- three animated water frames and four grass floor variants (row y=176),
- a nine-piece hedge set for auto-tiling at tile ids 50-58 (row 2 columns
  10-18, cells the sheet never used), each piece wearing grass on the sides
  that face open space,
- eight decoration objects (row y=208): log, flowers, mushroom, rock,
  butterfly with a second wing frame, snail, bird.

The sheet grows to 640x480; the .argb mirror is rewritten with it. Rerun
after changing anything here; nothing else regenerates this file."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "assets/art/garden.png"
MIRROR = ROOT / "assets/art/garden.argb"

GRASS = (92, 170, 69, 255)
GRASS_LIGHT = (119, 175, 82, 255)
GRASS_DARK = (74, 148, 60, 255)
HEDGE = (49, 113, 52, 255)
HEDGE_LIGHT = (74, 145, 74, 255)
HEDGE_DARK = (36, 88, 42, 255)
WATER = (74, 156, 208, 255)
WATER_LIGHT = (120, 190, 230, 255)
WATER_DARK = (56, 128, 182, 255)
DIRT = (170, 122, 77, 255)
DIRT_DARK = (140, 96, 58, 255)
WOOD = (150, 104, 62, 255)
WOOD_DARK = (110, 74, 42, 255)
WOOD_LIGHT = (186, 140, 92, 255)
WHITE = (246, 246, 240, 255)
YELLOW = (244, 214, 90, 255)
RED = (214, 84, 76, 255)
GREY = (150, 150, 148, 255)
GREY_DARK = (112, 112, 110, 255)
GREY_LIGHT = (190, 190, 186, 255)
ORANGE = (238, 150, 84, 255)
BLUE = (110, 160, 220, 255)
CLEAR = (0, 0, 0, 0)


def blank():
    return [[CLEAR for _ in range(16)] for _ in range(16)]


def put(cell, x, y, color):
    if 0 <= x < 16 and 0 <= y < 16:
        cell[y][x] = color


def rect(cell, x0, y0, x1, y1, color):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(cell, x, y, color)


def speckle(cell, seed, color, count=14, step=3):
    position = seed
    for _ in range(count):
        position = (position * 7919 + 17) & 0xFFFF
        x = (position >> 8) % 16
        y = (position & 0xFF) % 16
        put(cell, x, y, color)


def grass_base(cell, seed=1):
    rect(cell, 0, 0, 15, 15, GRASS)
    speckle(cell, seed, GRASS_LIGHT, 10)
    speckle(cell, seed + 1, GRASS_DARK, 8)


def hedge_base(cell, seed=5):
    rect(cell, 0, 0, 15, 15, HEDGE)
    speckle(cell, seed, HEDGE_LIGHT, 16)
    speckle(cell, seed + 1, HEDGE_DARK, 12)


def water_frame(frame):
    cell = blank()
    rect(cell, 0, 0, 15, 15, WATER)
    speckle(cell, 9 + frame, WATER_DARK, 18)
    for row in (3, 8, 13):
        for x in range(16):
            offset = (x + frame * 2 + row) % 6
            if offset < 3:
                put(cell, x, row + (offset == 2), WATER_LIGHT)
    return cell


def daisy(cell, x, y):
    for petal in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        put(cell, *petal, WHITE)
    put(cell, x, y, YELLOW)


def main():
    sheet = Image.open(SHEET).convert("RGBA")
    canvas = Image.new("RGBA", (640, 480), (0, 0, 0, 0))
    canvas.paste(sheet.crop((0, 0, 640, 400)), (0, 0))

    def place(cell, column, row):
        picture = Image.new("RGBA", (16, 16))
        for y in range(16):
            for x in range(16):
                picture.putpixel((x, y), cell[y][x])
        canvas.paste(picture.resize((32, 32), Image.NEAREST), (column * 32, row * 32))

    # Row 176: water frames and grass variants.
    for frame in range(3):
        place(water_frame(frame), frame, 11)
    variants = []
    for kind in range(4):
        cell = blank()
        grass_base(cell, seed=21 + kind * 4)
        if kind == 0:  # daisies
            daisy(cell, 3, 4)
            daisy(cell, 11, 9)
            daisy(cell, 6, 13)
        elif kind == 1:  # grass tufts
            for tuft_x, tuft_y in ((4, 5), (10, 8), (7, 12)):
                for blade, height in ((-1, 2), (0, 4), (1, 2)):
                    for up in range(height):
                        put(cell, tuft_x + blade, tuft_y - up, GRASS_DARK if up < 2 else HEDGE)
        elif kind == 2:  # pebbles
            for stone_x, stone_y, color in ((4, 10, GREY), (5, 10, GREY_LIGHT), (11, 4, GREY), (12, 4, GREY_DARK)):
                put(cell, stone_x, stone_y, color)
        else:  # clover
            for clover_x, clover_y in ((5, 6), (10, 11)):
                put(cell, clover_x, clover_y, GRASS_DARK)
                put(cell, clover_x - 1, clover_y, HEDGE_LIGHT)
                put(cell, clover_x + 1, clover_y, HEDGE_LIGHT)
                put(cell, clover_x, clover_y - 1, HEDGE_LIGHT)
                put(cell, clover_x, clover_y + 1, HEDGE_LIGHT)
        variants.append(cell)
        place(cell, 4 + kind, 11)

    # Tile ids 50-58 live at row 2, columns 10-18.
    # 50 inner, 51 N, 52 E, 53 S, 54 W, 55 NE, 56 NW, 57 SE, 58 SW.
    for piece in range(9):
        cell = blank()
        hedge_base(cell, seed=31 + piece * 3)
        north = piece in (1, 5, 6)
        east = piece in (2, 5, 7)
        south = piece in (3, 7, 8)
        west = piece in (4, 6, 8)
        if north:
            rect(cell, 0, 0, 15, 2, GRASS)
            rect(cell, 0, 3, 15, 3, HEDGE_DARK)
            speckle(cell, 41 + piece, GRASS_LIGHT, 5)
        if south:
            rect(cell, 0, 13, 15, 15, GRASS)
            rect(cell, 0, 12, 15, 12, HEDGE_DARK)
        if west:
            rect(cell, 0, 0, 2, 15, GRASS)
            rect(cell, 3, 0, 3, 15, HEDGE_DARK)
        if east:
            rect(cell, 13, 0, 15, 15, GRASS)
            rect(cell, 12, 0, 12, 15, HEDGE_DARK)
        place(cell, 10 + piece, 2)

    # Row 208: the decoration objects, on transparency.
    objects = []

    log = blank()
    rect(log, 1, 6, 14, 11, WOOD)
    rect(log, 1, 6, 14, 7, WOOD_LIGHT)
    rect(log, 1, 10, 14, 11, WOOD_DARK)
    rect(log, 0, 5, 1, 12, WOOD_DARK)
    rect(log, 14, 5, 15, 12, WOOD_LIGHT)
    put(log, 2, 8, WOOD_DARK)
    put(log, 2, 9, WOOD_DARK)
    put(log, 12, 8, WOOD_DARK)
    objects.append(log)

    flowers = blank()
    for x, y in ((4, 4), (10, 6), (6, 11), (12, 11)):
        put(flowers, x, y + 1, GRASS_DARK)
        put(flowers, x, y, YELLOW)
        put(flowers, x - 1, y, RED)
        put(flowers, x + 1, y, RED)
        put(flowers, x, y - 1, RED)
        put(flowers, x, y + 1 - 1, RED)
    objects.append(flowers)

    mushroom = blank()
    rect(mushroom, 4, 10, 8, 13, WHITE)
    rect(mushroom, 3, 6, 9, 9, RED)
    rect(mushroom, 4, 5, 8, 5, RED)
    put(mushroom, 5, 7, WHITE)
    put(mushroom, 7, 6, WHITE)
    put(mushroom, 4, 11, (210, 200, 180, 255))
    objects.append(mushroom)

    rock = blank()
    rect(rock, 3, 8, 11, 13, GREY)
    rect(rock, 4, 7, 10, 7, GREY_LIGHT)
    rect(rock, 3, 13, 11, 13, GREY_DARK)
    put(rock, 5, 9, GREY_LIGHT)
    put(rock, 9, 11, GREY_DARK)
    objects.append(rock)

    def butterfly(open_wings):
        cell = blank()
        rect(cell, 7, 5, 8, 11, HEDGE_DARK)
        if open_wings:
            rect(cell, 3, 4, 6, 8, ORANGE)
            rect(cell, 9, 4, 12, 8, ORANGE)
            rect(cell, 4, 9, 6, 11, YELLOW)
            rect(cell, 9, 9, 11, 11, YELLOW)
            put(cell, 4, 5, (250, 200, 140, 255))
            put(cell, 11, 5, (250, 200, 140, 255))
        else:
            rect(cell, 5, 5, 7, 10, ORANGE)
            rect(cell, 8, 5, 10, 10, ORANGE)
            rect(cell, 6, 6, 9, 8, YELLOW)
        put(cell, 7, 4, HEDGE_DARK)
        put(cell, 8, 4, HEDGE_DARK)
        return cell

    objects.append(butterfly(True))
    objects.append(butterfly(False))

    snail = blank()
    rect(snail, 3, 10, 12, 12, (196, 178, 150, 255))
    rect(snail, 4, 5, 10, 10, WOOD)
    rect(snail, 5, 6, 9, 9, WOOD_DARK)
    rect(snail, 6, 7, 8, 8, WOOD_LIGHT)
    put(snail, 3, 8, (206, 160, 110, 255))
    put(snail, 2, 9, (206, 160, 110, 255))
    rect(snail, 10, 7, 11, 9, (196, 178, 150, 255))
    put(snail, 11, 5, HEDGE_DARK)
    put(snail, 12, 6, HEDGE_DARK)
    put(snail, 13, 4, (206, 160, 110, 255))
    objects.append(snail)

    bird = blank()
    rect(bird, 4, 7, 10, 11, BLUE)
    rect(bird, 5, 6, 9, 6, BLUE)
    put(bird, 4, 8, (150, 190, 240, 255))
    rect(bird, 10, 8, 12, 9, ORANGE)
    put(bird, 11, 6, HEDGE_DARK)
    rect(bird, 2, 9, 3, 10, BLUE)
    rect(bird, 4, 12, 9, 12, GREY_DARK)
    put(bird, 6, 13, GREY_DARK)
    put(bird, 8, 13, GREY_DARK)
    objects.append(bird)

    for index, cell in enumerate(objects):
        place(cell, index, 13)

    canvas.save(SHEET)
    import struct
    pixels = canvas.tobytes()
    mirror = bytearray(struct.pack("<ii", 640, 480))
    for y in range(480):
        for x in range(640):
            r, g, b, a = pixels[(y * 640 + x) * 4:(y * 640 + x) * 4 + 4]
            mirror += bytes((b, g, r, a))
    MIRROR.write_bytes(mirror)
    print("Garden sheet extended to 640x480 with water, grass, hedge and object art.")


if __name__ == "__main__":
    main()
