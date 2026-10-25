# Apfelwurm

Application id `xyz.waozi.wurm`.


A native Ziran and Kryon game using all **99 original levels** recovered
from the owner's `The-Worm_Win_EN/ONLY.ONE` archive, reshaped for mobile:
each level plays on a **20x15 grid** derived from the recovered 40x30 data
by merging 2x2 cell blocks, so cells read twice as large on a phone while
the levels keep their shape (a merged block becomes a wall only when three
or four of its cells were solid; monster markers survive the merge). The
recovered 40x30 files stay in `assets/original` as the reference, and
`tools/make_mobile_levels.py` regenerates `src/levels.zi` from them. The
game shows new art and sound: each stage has its own cover, tiles,
character, monsters, pickup and effects (`assets/art`), and new sound
effects and stage music (`assets/sounds`).

The executable was disassembled to recover the single-player rules: movement
by four pixels every 25 Ms, sequential apples, progressive growth, passable
decorative tiles, six monster types, lives, scoring, and the bottom entrance
and top exit. Collect the level's apples, then guide the worm through the
opening at the top centre. An extra life is awarded every 33 points.

## Controls

- The game opens on the Garden stage (33 levels, playing the Worm). Space
  and Factory are switched off for now (`OPEN_STAGES` in `src/app.zi`); when open,
  Left/Right, A/D, a swipe or the side buttons change stage
- Up/Down or the - and + buttons choose a level; Home/End pick the first/last
- Enter or Space: start or retry
- Arrows, WASD or a swipe over the board: steer
- Escape, Space or P: pause and resume
- Q while paused: back to the stages
- R: restart the current level
- M: mute and unmute

## Mobile-first layout

The green icon bar across the top carries hearts for lives, the apple goal,
the star score and the level; the board letterboxes into the remaining
space, so landscape and portrait both keep the game's proportions. The
desktop window opens from `WURM_WINDOW=WxH` (default 960x600), which is how
the portrait layout is exercised on the desktop.

## Level editor

E on the stages screen (or its pencil button) opens the editor for the chosen
level. The held left button paints the selected brush across the canvas, the
right button restores the recovered original tile, and the palette offers the
stage's floors, walls, false walls and the six monster kinds. The apple goal
is set with the - and + buttons or keys. Up/Down switches levels (saving
first), Enter playtests from the entrance, and E returns to the stages.
Saving is automatic on switch, exit and playtest, plus the Save button; Reset
(deleting the override) restores the recovered original level.

Edits live in `assets/levels/level<N>.dat`, one file per edited level in the
mobile layout (apple count, then the 20x15 tiles in column order). A level
without a file plays its derived mobile level, so removing a file restores
it. The entrance (bottom centre, green marker) and exit (top centre, red
marker) are carved at runtime from the tiles above and below the edges; the
editor warns when a level could not be entered or left. `WURM_LEVEL_DIR`
redirects where overrides are read and written.

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
Codex image generation and fitted to 32-pixel cells; floors, walls and effect
frames are drawn pixel by pixel at 16 pixels and doubled. Each 640x400 stage
sheet keeps the original 20x12 cell layout, so tile values in the recovered
levels still mean the same floor or wall. `assets/sounds/sounds.json` records the OpenRouter model and prompt
of every sound; the scores are trimmed and crossfaded into seamless loops.

## Recover the assets again

```sh
python3 tools/extract_original.py /mnt/storage/Games/The-Worm_Win_EN
python3 tools/make_mobile_levels.py
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
