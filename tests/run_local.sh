#!/bin/sh
set -eu
worm_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$worm_root"
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS SESSION_MANAGER
export YUE_DESKTOP_RECOVERY=0 MAKEFLAGS=-j1 ZIRAN_PAR_THREADS=1 OMP_NUM_THREADS=1
mkdir -p build/research
# Development overrides are intentional when present. CI has none and uses
# the committed dependency lock for every command.
if [ -f ziran.local.toml ]; then
    lock=""
else
    lock="--locked"
fi
python3 tests/recovery_test.py "${1:-/mnt/storage/Games/The-Worm_Win_EN}"
python3 tools/design_levels.py --check
python3 tests/campaign_design_test.py
python3 tests/authored_design_test.py
python3 tools/locales.py --check
python3 tools/make_art.py --check
python3 tools/render_previews.py --check
ziran check $lock
ziran build $lock --project --root tests --target=c --entry game_test:main --exe -o build/game-test tests/game_test.zi
build/game-test/game_test
ziran build $lock --project --root tests --target=c --entry steering_test:main --exe -o build/steering-test tests/steering_test.zi
build/steering-test/steering_test
ziran build $lock --project --root tests --target=c --entry campaign_replay:main --exe -o build/campaign-replay tests/campaign_replay.zi
build/campaign-replay/campaign_replay
ziran build $lock --project --root tests --target=c --entry progress_test:main --exe -o build/progress-test tests/progress_test.zi
build/progress-test/progress_test
ziran build $lock --project --root tests --define WURM_ACCOUNT_TEST --target=c --entry account_test:main --exe -o build/account-test tests/account_test.zi
build/account-test/account_test
python3 tests/hosted_test.py
ziran build $lock --project --root tests --target=c --entry editor_test:main --exe -o build/editor-test tests/editor_test.zi
build/editor-test/editor_test
ziran build $lock --project --root tests --target=c --entry authored_levels_test:main --exe -o build/authored-levels-test tests/authored_levels_test.zi
build/authored-levels-test/authored_levels_test
ziran build $lock --project --root tests --target=c --entry level_probe:main --exe -o build/level-probe tests/level_probe.zi
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
LDLIBS=-lSDL2 ziran build $lock --project --root tests --target=c --entry audio_test:main --exe -o build/audio-test tests/audio_test.zi
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy build/audio-test/audio_test
ziran run $lock shot > build/research/remake-start.ppm
WORM_SHOT_LEVEL=200 ziran run $lock shot > build/research/remake-mountain-finale.ppm
WORM_SHOT_LEVEL=20 WORM_SHOT_STAGES=1 ziran run $lock shot > build/research/remake-stages.ppm
WORM_SHOT_EDITOR=1 ziran run $lock shot > build/research/remake-editor.ppm
python3 - <<'PY'
from pathlib import Path
from PIL import Image
for name in ('remake-start', 'remake-mountain-finale', 'remake-stages', 'remake-editor'):
    picture = Image.open(Path('build/research') / (name + '.ppm')).convert('RGB')
    assert picture.size == (960, 600)
    assert len(picture.getcolors(960 * 600)) > 100
    picture.save(Path('build/research') / (name + '.png'))
print('Headless local tests: title, mountain finale, title after level 20 and the editor rendered with the new art.')
PY
ziran build $lock desktop
ziran build $lock modal-test
printf '%s\n' 'Apfelwurm local tests passed; GitHub CI is separate.'
