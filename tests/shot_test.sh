#!/bin/sh
# Kept as the original test entry point; the complete local suite includes it.
set -eu
worm_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$worm_root"
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
mkdir -p build/research
ziran check --locked
ziran run --locked shot > build/research/shot-test.ppm 2> build/research/shot-test.log
python3 - <<'PY'
from PIL import Image
image = Image.open('build/research/shot-test.ppm').convert('RGB')
assert image.size == (960, 600)
assert len(image.getcolors(960 * 600)) > 100
PY
