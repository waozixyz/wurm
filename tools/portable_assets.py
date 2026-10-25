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
            'title.png', 'title-portrait.png'}
    for path in (resources / 'art').rglob('*'):
        if path.is_file() and not (path.name in keep or
                (path.parent.name == 'previews' and path.suffix == '.png' and
                 path.name.startswith(('garden-', 'forest-')))):
            path.unlink()
    sounds = resources / 'sounds'
    sounds.mkdir(exist_ok=True)
    for name in ('start', 'exit', 'lose', 'pickup'):
        with wave.open(str(sounds / (name + '.wav')), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22050)
            output.writeframes((ROOT / 'assets/sounds' / (name + '.pcm')).read_bytes())
    # Compile the shipped editor overrides as data; a portable game never
    # reads a host path. Personal edits take precedence in its own records.
    code = 'BundledLevel :: (level: s32, output: []u8) -> s64 {\n'
    for path in sorted((ROOT / 'assets/levels').glob('level*.dat')):
        level = int(path.stem[5:]) - 1
        data = path.read_bytes()
        code += f'    if level == {level} && output.count >= {len(data)} {{\n'
        code += '        bytes: [' + str(len(data)) + ']u8 = .[\n'
        code += ',\n'.join('            ' + ','.join(map(str, data[at:at + 80])) for at in range(0, len(data), 80))
        code += ']\n'
        code += '        for byte, at: bytes { output[at] = byte }\n'
        code += f'        return {len(data)}\n    }}\n'
    code += '    return -1\n}\n'
    generated.mkdir(parents=True, exist_ok=True)
    (generated / 'portable_levels.zi').write_text(code)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
