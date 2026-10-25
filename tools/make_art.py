#!/usr/bin/env python3
"""Fit generated cartoon atlases to the game's stable tile/sprite coordinates.

The source art lives in assets/art-source. This only crops, resizes and packs
that art; the image model supplies the terrain, creatures and decorations.
All gameplay tile IDs and collision rules stay unchanged.
"""
import argparse
from pathlib import Path
import struct

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'assets/art'
SOURCE = ROOT / 'assets/art-source'
SIZE = (640, 480)
CELL = 32


def cells(path, columns, rows):
    image = Image.open(path).convert('RGBA')
    width, height = image.width / columns, image.height / rows
    assert abs(width - height) < max(width, height) * 0.03, path
    return [image.crop((round(x * width), round(y * height), round((x + 1) * width), round((y + 1) * height)))
            .resize((CELL, CELL), Image.Resampling.LANCZOS)
            for y in range(rows) for x in range(columns)]


def build(stage, terrain, sprites, details):
    sheet = Image.new('RGBA', SIZE)

    def place(image, column, row):
        sheet.paste(image, (column * CELL, row * CELL))

    grass, variation, hedge, trunk = (0, 1, 4, 5) if stage == 'garden' else (8, 9, 10, 11)
    for tile in range(20):
        source = 2 if tile == 1 else 3 if tile == 2 else grass
        if stage == 'forest' and tile == 1:
            source = 9
        place(terrain[source], tile, 0)
    for tile in range(20):
        source = 6 if tile == 2 else trunk if tile == 1 else hedge
        place(terrain[source], tile, 1)
    # Smart hedge edges retain grass on the open sides of a painted wall.
    for piece in range(9):
        cell = terrain[hedge].copy()
        for edge, enabled in enumerate((piece in (1, 5, 6), piece in (2, 5, 7),
                                       piece in (3, 7, 8), piece in (4, 6, 8))):
            if enabled:
                bounds = ((0, 0, 32, 3), (29, 0, 32, 32), (0, 29, 32, 32), (0, 0, 3, 32))[edge]
                cell.paste(terrain[grass].crop(bounds), bounds[:2])
        place(cell, 10 + piece, 2)
    for column, sprite in enumerate((sprites[8], sprites[9], sprites[9].rotate(-90),
                                      sprites[9].rotate(180), sprites[9].rotate(90), sprites[10])):
        place(sprite, column, 2)
    for column in range(7):
        place(sprites[column], column, 3)
    place(sprites[7], 0, 7)
    for frame in range(6):
        amount = 28 - frame * 4
        cell = Image.new('RGBA', (CELL, CELL))
        cell.paste(sprites[4].resize((amount, amount), Image.Resampling.LANCZOS),
                   ((CELL - amount) // 2, (CELL - amount) // 2))
        place(cell, frame, 9)
        cell = Image.new('RGBA', (CELL, CELL))
        amount = 8 + frame * 4
        cell.paste(sprites[11].resize((amount, amount), Image.Resampling.LANCZOS),
                   ((CELL - amount) // 2, (CELL - amount) // 2))
        place(cell, frame, 10)
    for frame in range(3):
        place(terrain[6 + frame % 2], frame, 11)
    for variant in range(4):
        place(terrain[variation if variant == 3 else grass], 4 + variant, 11)
    for column, sprite in enumerate((sprites[13], sprites[11], sprites[12], sprites[14],
                                      sprites[15], sprites[15].transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                                      details[0], details[1])):
        place(sprite, column, 13)
    return sheet


def save(image, path, check):
    if check:
        assert path.exists() and Image.open(path).convert('RGBA').tobytes() == image.tobytes(), path
    else:
        image.save(path)
    mirror = struct.pack('<II', *image.size) + image.tobytes('raw', 'BGRA')
    if check:
        assert path.with_suffix('.argb').read_bytes() == mirror, path.with_suffix('.argb')
    else:
        path.with_suffix('.argb').write_bytes(mirror)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    terrain = cells(SOURCE / 'terrain.png', 4, 3)
    sprites = cells(SOURCE / 'sprites.png', 4, 4)
    # Only replace the seven worm cells; other creatures retain their art.
    sprites[:7] = cells(SOURCE / 'worm.png', 4, 4)[:7]
    # The mouth is on the leading edge, viewed from above. Rotate one
    # profile consistently: left, up, right, down are the engine directions.
    head = Image.open(SOURCE / 'head-profile.png').convert('RGBA')
    bounds = head.getchannel('A').getbbox()
    assert bounds, 'head alpha missing'
    head = head.crop(bounds)
    head.thumbnail((30, 30), Image.Resampling.LANCZOS)
    profile = Image.new('RGBA', (CELL, CELL))
    profile.paste(head, ((CELL - head.width) // 2, (CELL - head.height) // 2))
    sprites[:4] = [profile.rotate(angle) for angle in (180, 90, 0, 270)]
    details = cells(SOURCE / 'details.png', 2, 1)
    assert min(Image.open(SOURCE / 'sprites.png').getchannel('A').getextrema()) == 0, 'sprite alpha missing'
    for stage in ('garden', 'forest'):
        save(build(stage, terrain, sprites, details), ART / (stage + '.png'), args.check)
    canopy = Image.open(SOURCE / 'forest-canopy.png').convert('RGBA').resize((40 * CELL, 30 * CELL), Image.Resampling.LANCZOS)
    save(canopy, ART / 'forest-canopy.png', args.check)
    save(canopy.transpose(Image.Transpose.ROTATE_270), ART / 'forest-canopy-portrait.png', args.check)
    for name in ('title', 'title-portrait'):
        image = Image.open(ART / (name + '.png')).convert('RGBA')
        mirror = struct.pack('<II', *image.size) + image.tobytes('raw', 'BGRA')
        path = ART / (name + '.argb')
        if args.check:
            assert path.read_bytes() == mirror, path
        else:
            path.write_bytes(mirror)
    print('Cartoon Garden/Forest atlases and title mirrors ' + ('verified.' if args.check else 'packed.'))


if __name__ == '__main__':
    main()
