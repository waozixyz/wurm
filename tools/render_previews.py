#!/usr/bin/env python3
"""Render each level's board to a small preview picture for the editor's
level selector. The pictures show the playable base level on each stage's
sheet; rerun after changing level data or tile art."""
import argparse
from pathlib import Path

from PIL import Image
from design_levels import STAGES

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 200, 150


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed previews match regeneration")
    arguments = parser.parse_args()

    changed = 0
    destination = ROOT / "assets/art/campaign-previews"
    if not arguments.check:
        destination.mkdir(parents=True, exist_ok=True)
    for stage, first, end in STAGES:
        sheet = Image.open(ROOT / f"assets/art/campaign-{stage}.png").convert("RGBA")
        canopy = Image.open(ROOT / 'assets/art/forest-canopy.png').convert('RGBA') if stage == 'leafwood' else None
        ground = Image.open(ROOT / 'assets/art/ground-meadow.png').convert('RGBA') if stage == 'meadow' else None
        for number in range(1, end - first + 1):
            designed = ROOT / "build/designed" / f"level{first + number}.dat"
            raw_path = designed
            raw = raw_path.read_bytes()
            tiles = raw[1:1201] if len(raw) > 1201 else raw[1:]
            for portrait in (False,True):
                columns,rows=(30,40) if portrait else (40,30)
                width,height=(150,200) if portrait else (200,150)
                board={(x,y):tiles[x*30+y] for x in range(40) for y in range(30)}
                if portrait:
                    authored=ROOT/'build/designed'/f"level{first+number}-portrait.dat"
                    if authored.exists():
                        data=authored.read_bytes()
                        board={(x,y):data[1+x*40+y] for x in range(30) for y in range(40)}
                    else:board={(29-y,x):tile for (x,y),tile in board.items()}
                field=canopy
                if portrait and canopy is not None:field=Image.open(ROOT/'assets/art/forest-canopy-portrait.png').convert('RGBA')
                preview=Image.new('RGB',(width,height))
                for y in range(rows):
                    for x in range(columns):
                        tile=board[x,y]&127
                        enemy=tile if 40<=tile<=45 else None
                        if enemy is not None:tile=0
                        source=sheet.crop(((tile%20)*32,(tile//20)*32,(tile%20)*32+32,(tile//20)*32+32))
                        if field is not None and (tile==20 or 50<=tile<=58):
                            source=field.crop((x*32,y*32,(x+1)*32,(y+1)*32))
                        if ground is not None and tile in (0,3,4,5,6,15,16,17,19):
                            source=ground.crop((x*ground.width/columns,y*ground.height/rows,
                                               (x+1)*ground.width/columns,(y+1)*ground.height/rows))
                        if enemy is not None:
                            column=6 if enemy==40 else enemy-40
                            source=source.copy()
                            source.alpha_composite(sheet.crop((column*32,64,column*32+32,96)))
                        preview.paste(source.resize((5,5)),(x*5,y*5))
                suffix='-portrait' if portrait else ''
                path=destination/f"{stage}-{number}{suffix}.png"
                if arguments.check:
                    if not path.exists() or Image.open(path).tobytes()!=preview.tobytes():
                        raise SystemExit(f"{path} does not match regeneration; rerun tools/render_previews.py")
                elif not path.exists() or Image.open(path).tobytes()!=preview.tobytes():
                    preview.save(path);changed+=1
    if arguments.check:
        print("Preview pictures match regeneration.")
    else:
        print(f"Previews written: {changed} changed, 400 total.")


if __name__ == "__main__":
    main()
