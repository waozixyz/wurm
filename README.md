# Apfelwurm

Application id `xyz.waozi.wurm`.


A native Ziran and Kryon game. The illustrated Apfelwurm title has one
**Play** button: start in the Garden, then continue into the Forest as the
same worm. There are **66 unique designed levels**, 33 per chapter, with
wide paths, solid hedges, stone and ponds on the original 40x30 grid.
The opening levels need five apples; later levels mix longer goals and
more involved routes with gentler breaks. The campaign contains no passive
decoration props or monsters. `tools/design_levels.py` regenerates the
boards and complete route certificates. Local tests verify every layout
and complete all 66 levels in both orientations with three apple seeds.
The **99 recovered levels** from the owner's `The-Worm_Win_EN/
ONLY.ONE` archive stay the byte-exact reference in `assets/original`. The game shows new art and sound: each
chapter has its own terrain (`assets/art`), with the same worm, apples and
woodland creatures throughout. Nature music and sound effects live in
`assets/sounds`. The recovered tilesets, title artwork, sounds and scores stay in
`assets/original` as the reference for the level data.

The executable was disassembled to recover the single-player rules: movement
by four pixels every 25 Ms, sequential apples, progressive growth, passable
decorative tiles, six monster types, lives, scoring, and the bottom entrance
and top exit. Collect the level's apples, then guide the worm through the
opening at the top centre. An extra life is awarded every 33 points. You start with three lives;
losing the last one ends the game at zero.

## Controls

- Click Play, Enter or Space: start immediately; Enter or Space also retries
- Arrows, WASD or a swipe over the board: steer
- Escape, Space or P: pause and resume
- Q while paused: back to the title
- R: restart the current level
- M: mute and unmute
- E on the title: open the level editor

Collect the apples, then leave through the top opening. Garden level 33
continues directly into Forest level 1, keeping your lives and score.

## Mobile-first layout

In play, a cream status bar shows the chapter, level, hearts, apples and score.
Its status chips move onto a second row on narrow phones, keeping the 48-unit
Pause button clear. Pause, game-over and completion dialogs use large stacked
touch buttons and a compact composition for short landscape screens; the title artwork fills the
whole screen with a composition for each orientation. Landscape letterboxes
the 640x480 board. In portrait
the same level data stands on its side as a 30x40 board that fills the
screen edge to edge, and the gates follow the board: the worm still enters
from the bottom edge and exits at the top. Steering keys and swipes stay
natural, so Up is always visually up. The gates carve only their own hole;
the neighbouring walls keep their tiles. Open entrance and exit gates show
stone posts on both sides, in either orientation. The worm follows its full
long path with slightly spaced orange segments and a top-down head whose
mouth faces the direction of travel. The desktop window opens from
`WURM_WINDOW=WxH` (default 1280x760); `WURM_WINDOW=480x700` shows the
portrait phone layout.

Touching hedge, stone and water tiles have borders only on exposed edges.
Forest walls sample one continuous overhead woodland image; the portrait
version rotates that same field so neighbouring tiles keep matching.

## Level editor

Press E from the title, or launch with `WURM_START=editor`;
the editor opens facing its level selector: one card per level with the
level's rendered board as its picture, a green frame on saved edits, and
one click to edit that level. Tab or Enter playtests. The held left button paints the selected brush across the canvas, the
right button restores the recovered original tile, and the palette offers the
stage's floors and solid obstacles. The apple goal
is set with the - and + buttons or keys. Up/Down switches levels (saving
first), Enter playtests from the entrance, and E returns to the title.
Saving is automatic on switch, exit and playtest, plus the Save button; Reset
(deleting the override) restores the designed campaign level. T or the turn
button stands the working level up exactly as portrait plays it and back,
so the sideways view can be edited and playtested directly.

Edits live in `assets/levels/level<N>.dat`, one file per edited level:
apple count, the 40x30 tiles, then the 40x30 object ids, all in column
order. The palette paints floors (grass, dirt, sand), a smart hedge that
fits its own edge and corner pieces, plain hedges, stone and solid water.
Existing object data remains readable, but passive props are not rendered.
A level without a file plays its designed campaign board, so removing a file
restores it. The entrance (bottom centre, green marker) and exit (top centre, red
marker) are carved at runtime from the tiles above and below the edges; the
editor warns when a level could not be entered or left. `WURM_LEVEL_DIR`
redirects where overrides are read and written.

## Build

Arcade builds `catalog.json`'s portable entry from this repository and offers
`wurm.zx` as an individual download. It uses the same campaign, artwork,
controls and editor; private editor records belong to `xyz.waozi.wurm`.
The portable host plays packed sound effects. The native editions keep the
streaming soundtrack and secondary-pointer editor controls.

```sh
ziran run --locked desktop
python3 tools/build_android.py --abi arm64-v8a
ziran run --locked shot > build/stages.ppm
WORM_SHOT_LEVEL=66 ziran run --locked shot > build/forest-finale.ppm
ziran check --locked
sh tests/run_local.sh
```

`tests/private_ui_test.py` additionally exercises the real desktop build on
its own verified Xvfb server. It checks all three dialogs in 320x568 portrait
and 640x360 landscape, including their primary and Back to title actions.
It never uses the owner's desktop. The audio
test uses SDL's dummy drivers and verifies that all effects and scores mix.

The Android debug APK is written to `build/android/`. Use `--abi armeabi-v7a`
for the development Moto. `tests/android_controls_test.py APK` verifies touch
start, pause, resume, steering and return to the title on that USB device.
Use `--verification` on both commands for the separate
`xyz.waozi.wurm.verification` install, preserving the normal game and data.
The device test leaves its own game open on the title.
On phones, swipe over the board to steer, use the top pause button, and tap
the pause or game-over card's buttons to continue or return to the title.

## Signed Android downloads

Start each numeric release in `CHANGELOG.md`, then run `sh update_version.sh`.
The generated `version.json` supplies the Android version and increasing
version code. Build and sign both ARM architectures with:

```sh
python3 tools/build_android.py --release --abi universal
python3 tools/android_release.py sign build/android/Apfelwurm-universal-release-unsigned.apk
```

Signing uses the preserved private key in ignored `backup/android-signing/`.
Only its public certificate is tracked in `packaging/android/certificate.pem`.
The signing tool verifies the package, version, certificate, both ARM native
libraries, 16 KB ZIP alignment and current game assets. It produces identical
signed `wurm-v<VERSION>.apk` and `wurm-<VERSION>-fdroid.apk` downloads, following
Shovey's naming format. The F-Droid filename is a source-build distribution
artifact; it does not imply a listing or approval in the F-Droid catalog.

On every push to master, the Downloads workflow runs the game and private
display tests, builds a production APK and signs both names using repository
secrets `WURM_ANDROID_KEYSTORE` and `WURM_ANDROID_KEYSTORE_PASSWORD`. A new
changelog version is published only after those jobs succeed. Tags are created
by that workflow. Publishing uploads directly from the verified build to
GitHub Releases, without using the shared Actions artifact quota. An already
published version is kept; a new download requires a new changelog version.

## Art and sound

The landscape and portrait title illustrations were generated with the built-in
image tool; `assets/art/title.json` records their prompts. The title assets
live at `assets/art/title.png` and `assets/art/title-portrait.png`. Direct
launches resolve their assets relative to the executable, including when
launched from `build/`.

The title uses detailed sunlit storybook art, and the tiles and creatures use clean cartoon
art generated with the built-in image tool. Source atlases live in
`assets/art-source`; their prompts are recorded in `assets/art/title.json`.
`tools/make_art.py` crops and packs those cells into the Garden and Forest
sheets without changing gameplay tile IDs or collision rules. It also writes
the display-free `.argb` mirrors. Run it with `--check` to verify the packed
art matches its sources. The same golden orange worm and red apples appear in both
chapters. `assets/sounds/sounds.json` records the OpenRouter model and prompt
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

The maintained game is single-player, with desktop and Android builds. The
original Windows dialogs and DirectPlay multiplayer have not been ported.
