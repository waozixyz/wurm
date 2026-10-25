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
    destination = ROOT / "assets/art/previews"
    if not arguments.check:
        destination.mkdir(parents=True, exist_ok=True)
    for stage, first, end in STAGES:
        sheet = Image.open(ROOT / f"assets/art/{stage}.png").convert("RGBA")
        canopy = Image.open(ROOT / 'assets/art/forest-canopy.png').convert('RGBA') if stage == 'leafwood' else None
        for number in range(1, end - first + 1):
            designed = ROOT / "build/designed" / f"level{first + number}.dat"
            raw_path = designed
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
                    if canopy is not None and (tile == 20 or 50 <= tile <= 58):
                        source = canopy.crop((x * 32, y * 32, (x + 1) * 32, (y + 1) * 32))
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
        print(f"Previews written: {changed} changed, 66 total.")


if __name__ == "__main__":
    main()
