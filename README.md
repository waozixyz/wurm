# Worm

A native Ziran and Kryon recreation using all **99 original levels** recovered
from the owner's `The-Worm_Win_EN/ONLY.ONE` archive. The original maps replace
the previous eleven generated approximations. All three tilesets, the title
artwork, sprites, four sound effects, and three musical scores are recovered.

The executable was disassembled to recover the single-player rules: movement
by four pixels every 25 ms, sequential apples, progressive growth, passable
decorative tiles, six monster types, lives, scoring, and the bottom entrance
and top exit. Collect the level's apples, then guide the worm through the
opening at the top center. An extra life is awarded every 33 points.

## Controls

- Title: arrows select any of the 99 levels; Home/End select the first/last
- Enter or Space: start or retry
- Arrows or WASD: steer
- Space or P: pause and resume
- R: restart the current level
- Escape: title screen
- M: mute and unmute

## Build

```sh
ziran run --locked desktop
ziran run --locked shot > build/title.ppm
WORM_SHOT_LEVEL=99 ziran run --locked shot > build/level-99.ppm
ziran check --locked
sh tests/run_local.sh
```

`tests/private_ui_test.py` additionally exercises the real desktop build on
its own verified Xvfb server. It never uses the owner's desktop. The audio
test uses SDL's dummy drivers and verifies that all recovered audio mixes.

## Recover the assets again

```sh
python3 tools/extract_original.py /mnt/storage/Games/The-Worm_Win_EN
python3 tools/render_music.py
```

The extractor validates the complete archive, preserves every packed file,
decodes the original PIX run-length encoding and VGA palettes, and generates
`src/original_levels.zi` without changing tile values or column order.
`assets/original/manifest.json` records the archive and extracted file hashes.
The original executable remains outside this repository and is never modified.

Recovery uses Python/Pillow and FFmpeg. Offline music rendering additionally
uses libfluidsynth and a General MIDI soundfont (TimGM6mb by default). MIDI
events and timing are preserved; instrument timbre depends on the soundfont,
as the original depended on the Windows MIDI synthesizer.

The maintained gameplay target is single-player desktop. The original Windows
dialogs, level editor, and DirectPlay multiplayer have not been ported.
