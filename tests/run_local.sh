#!/bin/sh
set -eu
worm_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$worm_root"
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS SESSION_MANAGER
export YUE_DESKTOP_RECOVERY=0 MAKEFLAGS=-j1 ZIRAN_PAR_THREADS=1 OMP_NUM_THREADS=1
mkdir -p build/research
python3 tests/recovery_test.py "${1:-/mnt/storage/Games/The-Worm_Win_EN}"
ziran check --locked
ziran build --locked --project --root tests --target=c --entry game_test:main --exe -o build/game-test tests/game_test.zi
build/game-test/game_test
ziran build --locked --project --root tests --target=c --entry level_probe:main --exe -o build/level-probe tests/level_probe.zi
build/level-probe/level_probe > build/research/native-levels.txt
python3 - <<'PY'
from pathlib import Path
values = iter(int(s) for s in Path('build/research/native-levels.txt').read_text().splitlines())
for level in range(1, 100):
    raw = Path(f'assets/original/level{level}.dat').read_bytes()
    for y in range(30):
        for x in range(40):
            assert next(values) == raw[1 + x * 30 + y], (level, x, y)
assert next(values, None) is None
print('Native local test: all 118,800 tile coordinates match the original files.')
PY
LDLIBS=-lSDL2 ziran build --locked --project --root tests --target=c --entry audio_test:main --exe -o build/audio-test tests/audio_test.zi
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy build/audio-test/audio_test
ziran run --locked shot > build/research/remake-title.ppm
WORM_SHOT_LEVEL=99 ziran run --locked shot > build/research/remake-level-99.ppm
python3 - <<'PY'
from pathlib import Path
from PIL import Image
for name in ('remake-title', 'remake-level-99'):
    picture = Image.open(Path('build/research') / (name + '.ppm')).convert('RGB')
    assert picture.size == (960, 600)
    assert len(picture.getcolors(960 * 600)) > 100
    picture.save(Path('build/research') / (name + '.png'))
print('Headless local tests: original title and final level rendered with recovered assets.')
PY
ziran build --locked desktop
printf '%s\n' 'Worm local tests passed; GitHub CI is separate.'
