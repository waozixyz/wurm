# Worm

A native Ziran and Kryon game using all **99 original levels** recovered
from the owner's `The-Worm_Win_EN/ONLY.ONE` archive. The game shows new art and
sound: each stage has its own cover, tiles, character, monsters, pickup and
effects (`assets/art`), and new sound effects and stage music
(`assets/sounds`). The recovered tilesets, title artwork, sounds and scores
stay in `assets/original` as the reference for the level data.

The executable was disassembled to recover the single-player rules: movement
by four pixels every 25 ms, sequential apples, progressive growth, passable
decorative tiles, six monster types, lives, scoring, and the bottom entrance
and top exit. Collect the level's apples, then guide the worm through the
opening at the top center. An extra life is awarded every 33 points.

## Controls

- The game opens on the Garden stage (33 levels, playing the Worm). Space and
  Factory are switched off for now (`OPEN_STAGES` in `src/app.zi`); when open,
  Left/Right, A/D, a swipe or the side buttons change stage
- Up/Down or the - and + buttons choose a level; Home/End pick the first/last
- Enter or Space: start or retry
- Arrows or WASD: steer
- Escape, Space or P: pause and resume
- Q while paused: back to the stages
- R: restart the current level
- M: mute and unmute

## Build

```sh
ziran run --locked desktop
ziran run --locked shot > build/stages.ppm
WORM_SHOT_LEVEL=99 ziran run --locked shot > build/level-99.ppm
ziran check --locked
sh tests/run_local.sh
```

`tests/private_ui_test.py` additionally exercises the real desktop build on
its own verified Xvfb server. It never uses the owner's desktop. The audio
test uses SDL's dummy drivers and verifies that all effects and scores mix.

## Art and sound

Stage covers and the character, monster and pickup sprites were drawn with
Codex image generation and fitted to 16-pixel cells; floors, walls and effect
frames are drawn pixel by pixel. Each stage sheet keeps the original 320x200
cell layout, so tile values in the recovered levels still mean the same floor
or wall. `assets/sounds/sounds.json` records the OpenRouter model and prompt
of every sound; the scores are trimmed and crossfaded into seamless loops.

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
