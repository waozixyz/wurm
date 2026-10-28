#!/usr/bin/env python3
"""Prepare the game's portable art, original edited levels and sound effects."""
from pathlib import Path
import json
import shutil
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]


def prepare(resources, generated):
    # Native mirrors and unused recovered chapters are kept in the source.
    for child in list(resources.iterdir()):
        if child.name not in ('art', 'levels', 'catalog.json'):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    keep = {'garden.png', 'forest.png', 'forest-canopy.png', 'forest-canopy-portrait.png',
            'meadow.png', 'leafwood.png', 'pinewood.png', 'lake.png', 'mountains.png',
            'title.png', 'title-portrait.png', 'ground-meadow.png', 'water-field.png',
            'campaign-meadow.png', 'campaign-leafwood.png', 'campaign-pinewood.png', 'campaign-lake.png', 'campaign-mountains.png'}
    for path in (resources / 'art').rglob('*'):
        if path.is_file() and not (path.name in keep or
                (path.parent.name == 'campaign-previews' and path.suffix == '.png' and
                 path.name.startswith(('meadow-', 'leafwood-', 'pinewood-', 'lake-', 'mountains-')))):
            path.unlink()
    sounds = resources / 'sounds'
    sounds.mkdir(exist_ok=True)
    for name in ('start', 'exit', 'lose', 'pickup'):
        with wave.open(str(sounds / (name + '.wav')), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            output.writeframes((ROOT / 'assets/sounds' / (name + '.pcm')).read_bytes())
    # The authored campaign is compiled from designed_levels.zi. Personal
    # editor records stay in the host's private storage, never in the bundle.
    code = 'BundledLevel :: (level: s32, output: []u8) -> s64 { unused level; unused output; return -1 }\n'
    generated.mkdir(parents=True, exist_ok=True)
    (generated / 'portable_levels.zi').write_text(code)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
