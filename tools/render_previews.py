#!/usr/bin/env python3
"""Render each level's board to a small preview picture for the editor's
level selector. The pictures show the playable base level on each stage's
sheet; rerun after changing level data or tile art."""
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 200, 150
STAGES = ("garden", "space", "factory")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed previews match regeneration")
    arguments = parser.parse_args()

    changed = 0
    destination = ROOT / "assets/art/previews"
    if not arguments.check:
        destination.mkdir(parents=True, exist_ok=True)
    for stage_index, stage in enumerate(STAGES):
        sheet = Image.open(ROOT / f"assets/art/{stage}.png").convert("RGBA")
        for number in range(1, 34):
            designed = ROOT / "build/designed" / f"level{number}.dat"
            raw_path = designed if stage_index == 0 and designed.exists() else ROOT / "assets/original" / f"level{stage_index * 33 + number}.dat"
            raw = raw_path.read_bytes()
            tiles = raw[1:1201] if len(raw) > 1201 else raw[1:]
            preview = Image.new("RGB", (WIDTH, HEIGHT))
            for y in range(30):
                for x in range(40):
                    tile = tiles[x * 30 + y] & 127
                    if 40 <= tile <= 45:
                        tile = 0
                    source = sheet.crop(((tile % 20) * 32, (tile // 20) * 32,
                                         (tile % 20) * 32 + 32, (tile // 20) * 32 + 32))
                    preview.paste(source.resize((WIDTH // 40, HEIGHT // 30)), (x * (WIDTH // 40), y * (HEIGHT // 30)))
            path = destination / f"{stage}-{number}.png"
            if arguments.check:
                encoded = preview.tobytes()
                if not path.exists():
                    raise SystemExit(f"{path} is missing; rerun tools/render_previews.py")
                if Image.open(path).tobytes() != encoded:
                    raise SystemExit(f"{path} does not match regeneration; rerun tools/render_previews.py")
            elif not path.exists() or Image.open(path).tobytes() != preview.tobytes():
                preview.save(path)
                changed += 1
    if arguments.check:
        print("Preview pictures match regeneration.")
    else:
        print(f"Previews written: {changed} changed, 99 total.")


if __name__ == "__main__":
    main()
