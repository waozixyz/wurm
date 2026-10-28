# Apfelwurm — build and development guide

Application id `xyz.waozi.wurm`.


A native Ziran and Kryon game. The illustrated Apfelwurm title offers
**Choose level**, **Play from start** and, after unlocking another level, **Continue**.
Choose swipe steering or a direction pad on first play. Follow the little orange worm
through **200 unique original-inspired levels**, with 40 each in Meadow,
deciduous Leafwood, coniferous Pinewood, Lake and Mountains.
Rooms, spirals, crossings, islands and narrow passes draw from 83 recovered
layouts. The six original enemy types include wandering fire, bouncing
patrols and chasing creatures. Enemy counts and apple goals increase across
stages, while the first six levels introduce movement without enemies.
Opening Meadow levels move more slowly before reaching the original pace.
Levels follow in order through every landscape. Choose level offers a
scrollable grid for each landscape; unlocked levels have large board previews and future levels show a lock. The run (level, lives and score carried into that level) and the
control choice persist. Unlocked progress is saved after every completed
level and survives game over, closing the game and starting a new run.
Continue starts the highest unlocked level with three lives and a fresh
score; Play from start begins at level 1. Earlier save records are imported.
Try again after game over also starts the highest unlocked level with fresh
lives and score, including after replaying an earlier level.
`tools/design_levels.py` regenerates the boards and static route certificates.
The local engine replay wins all 200 levels in both orientations with enemies
active, using recorded seeds and routes from `tests/campaign_cases.json`.
This is separate from device and Android input verification.
The **99 recovered levels** from the owner's `The-Worm_Win_EN/ONLY.ONE`
archive stay the byte-exact reference in `assets/original`.
The game uses new art and sound with the same worm and apples throughout.
Recovered tilesets, title artwork, sounds and scores remain in
`assets/original` as reference material.

The executable was disassembled to recover the single-player rules: movement
by four pixels every 25 Ms, sequential apples, progressive growth, passable
decorative tiles, six monster types, lives, scoring, and the bottom entrance
and top exit. Collect the level's apples, then guide the worm through the
opening at the top centre. An extra life is awarded every 33 points. You start with three lives;
losing the last one ends the game at zero.

## Controls

- Click Play, Enter or Space: choose controls on first play, then start at level 1; Enter or Space also retries
- Click Continue or press C on the title: start the highest unlocked level with three lives and a fresh score
- Click Choose level or press L on the title: browse landscapes and replay an unlocked level; Escape returns to the title
- Arrows, WASD, a held finger moving over the board, or the direction pad: steer immediately
- Pause > Controls: change between swipe steering and the direction pad
- Escape, Space or P: pause and resume
- Q while paused: back to the title
- R: restart the current level with the lives and score the run brought into it
- M: mute and unmute
- E on the title: open the level editor

Collect the apples, then leave through the top opening. Every level, across
all five landscapes, connects automatically, keeping lives and score. Lives lost
are saved immediately; lives earned within a level are kept by finishing it.
Hosted in Arcade, the cover is the title, so opening the game goes straight
into play.

## Mobile-first layout

In play, a themed status bar shows the chapter, level, hearts, apples and score.
Its status chips move onto a second row on narrow phones, keeping the 48-unit
Pause button clear. Pause, game-over and completion dialogs use large stacked
touch buttons and a compact composition for short landscape screens; the title artwork fills the
whole screen with a composition for each orientation. Landscape letterboxes
the 640x480 board. In portrait
the game loads its separate 30x40 portrait board, filling the screen edge
to edge. A missing portrait design starts from a best guess: rotate the
landscape rooms and connect both gates to the largest playable region.
Portrait level 2 has its own horizontal divider and a clear approach.
The worm enters from the bottom and exits at the top in both layouts.
Rotating during play reloads the current level in the other layout, keeping
lives and score. Steering keys and finger movements stay
natural, so Up is always visually up. The gates carve only their own hole;
the neighbouring walls keep their tiles. Open entrance and exit gates show
stone posts on both sides, in either orientation. The worm follows its full
long path with slightly spaced orange segments and a top-down head whose
mouth faces the direction of travel. The desktop window opens from
`WURM_WINDOW=WxH` (default 1280x760); `WURM_WINDOW=480x700` shows the
portrait phone layout.

Touching hedge, stone and water tiles have borders only on exposed edges.
Leafwood walls sample one continuous overhead woodland image; the portrait
version rotates that same field so neighbouring tiles keep matching.

## Level editor

Press E from the title, or launch with `WURM_START=editor`;
the editor opens facing its level selector: use its landscape arrows to browse all five chapters, then
choose a card with the
level's rendered board as its picture, a green frame on saved edits, and
one click to edit that level. Tab or Enter playtests. The held left button paints the selected brush across the canvas, the
right button restores the current layout's base tile, and the palette offers the
stage's floors, solid obstacles and six enemies. The apple goal
is set with the - and + buttons or keys. Up/Down switches through all 200 levels (saving
first), Enter playtests from the entrance, and E returns to the title.
Saving is automatic on switch, exit and playtest, plus the Save button; Reset
(deleting the override) restores the selected layout's base board. The
**Landscape** and **Portrait** buttons select the layout; T switches between them.
Each mode has its own tiles, objects and apple goal, and saves without changing
the other. A missing portrait version is labelled **Best guess**; Save keeps
it as an independent layout. Playtest uses the selected mode even when the
editor window has the other shape.

Landscape edits live in `assets/campaign-levels/level<N>.dat`; portrait edits
use `level<N>-portrait.dat`. Each file contains an apple count, 1,200 tiles,
and 1,200 object ids in column order: 40 columns of 30 rows for landscape,
or 30 columns of 40 rows for portrait. Reset changes only the selected mode. The palette paints floors (grass, dirt, sand), a smart hedge that
fits its own edge and corner pieces, plain hedges, stone and solid water.
Existing object data remains readable, but passive props are not rendered.
A level without a file plays its designed campaign board, so removing a file
restores it. Earlier 66-level edits remain untouched in `assets/levels/`
(and the earlier Android/portable record names); the new campaign uses separate
records. The entrance (bottom centre, green marker) and exit (top centre, red
marker) are carved at runtime from the tiles above and below the edges; the
editor warns when a level could not be entered or left. `WURM_LEVEL_DIR`
redirects where overrides are read and written.

Published editor layouts live in `assets/authored-levels/`, separate from
personal saves. To publish a saved board, copy only its `level<N>.dat` or
`level<N>-portrait.dat` file there, then run `python3 tools/authored_levels.py`
and `python3 tools/render_previews.py`. The generated boards are compiled
into desktop, Android, browser and Arcade editions. Personal progress,
wardrobes and other save records are never included. Reset restores the
published board; a new personal edit takes precedence over it.

## Build

Arcade builds `catalog.json`'s portable entry from this repository and offers
`wurm.zx` as an individual download. It uses the same campaign, artwork,
controls and editor; private editor records belong to `xyz.waozi.wurm`.
The portable host plays packed sound effects. The native editions keep the
streaming soundtrack and secondary-pointer editor controls.

```sh
python3 tools/build_desktop.py
build/account-desktop/wurm
python3 tools/build_android.py --abi arm64-v8a
ziran run --locked shot > build/stages.ppm
WORM_SHOT_LEVEL=200 ziran run --locked shot > build/forest-finale.ppm
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
The device test leaves its own game open on the title. To win every level
with the unchanged game engine on the physical USB Moto, run
`python3 tests/android_campaign_test.py`. It builds an ARMv7 test executable,
replays all 400 level/orientation cases with normal steering and collisions,
and saves per-level results under `build/android-campaign/`. It uses its own
`/data/local/tmp` directory and preserves the normal game process and saves.
`--build-only` prepares the runner without claiming any device test result.
On phones, keep your finger down and move it in the direction you want to
turn. You can make successive corners without lifting or returning to the
press position; a small movement is enough, and lifting makes no extra turn.
Use the top pause button, and tap
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
signed `wurm-v<VERSION>.apk` and `wurm-<VERSION>-fdroid.apk` downloads. Both exclude
Google libraries, and verification rejects Google or Play Billing classes and
the Play Billing permission in these APKs. The F-Droid filename is a source-build distribution
artifact; it does not imply a listing or approval in the F-Droid catalog.

Build and sign the separate Google Play APK with:

```sh
python3 tools/build_android.py --release --abi universal --edition gplay
python3 tools/android_release.py sign build/android/Apfelwurm-universal-gplay-release-unsigned.apk --edition gplay
```

This produces `wurm-v<VERSION>-gplay.apk`, with Play Billing for Dew purchases.
It never replaces either Google-free download. `--bundle` still builds the
Google Play App Bundle; the separate Google Play bundle workflow signs it for
upload to the Play Console.

On every push to master, the Downloads workflow runs the game and private
display tests, builds both Android editions and signs all three names using repository
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
`tools/make_art.py` crops and packs those cells into the landscape
sheets without changing gameplay tile IDs or collision rules. It also writes
the display-free `.argb` mirrors. Run it with `--check` to verify the packed
art matches its sources. `assets/art-source/journey-terrain.png` supplies
the five landscape materials; its built-in image-generation prompt is recorded
in `assets/art/title.json`. The same golden orange worm and red apples appear
throughout the journey. `assets/sounds/sounds.json` records the OpenRouter model and prompt
of every sound. The current acoustic garden score was AI-generated with
Lyria; it is not the recovered original MIDI. It plays continuously through
level and landscape transitions. Loop reads wrap without padding silence,
and the native mixer buffers enough audio to tolerate slower phone frames.
The soundtrack itself is preserved; this update repairs playback.

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

## Browser build and deployment

`python3 tools/build_web.py` compiles the same game with Kryon's Canvas2D host
and Emscripten. `node tests/web_test.mjs` runs a private browser test, including
control selection, the direct start, portrait resizing and persistent saves.
The browser stores records through Kryon's IndexedDB provider.

The Downloads workflow packages the verified web build beside the signed APKs.
The website repository's Apfelwurm site workflow checks for a newer published
release every ten minutes and deploys its verified browser archive to the
`wurm` Cloudflare Pages project at https://wurm.waozi.xyz automatically, using
the website's existing deployment credentials. Nothing needs updating by hand.

## Profile, appearance and cosmetics

The release desktop build uses `tools/build_desktop.py`. Android and browser
builds use the same native Entity account provider through `src/account.zi`;
keys stay in the provider. Desktop profile data lives in
`$XDG_DATA_HOME/wurm/profile` (or `~/.local/share/wurm/profile`), Android uses
private app storage, and the browser uses IndexedDB. `WURM_PROFILE_DIR` selects
a private fixture. Do not point tests at an owner's profile.

Earned marks use Entity's merged `game-progress` record named `wurm`. Runs are
local and completion masks are account scoped. Account changes end the current
view without publishing its old run under the new account. Guest marks never
seed another account automatically. Offline pending completions survive restart.

`wurm-player` has one record per provider device ID, so active milliseconds from
different devices are summed rather than overwritten. Pauses and suspended
frames do not count. `wurm-settings` keeps the selected skin, theme, sound and
controls. A website unlock records opening the explicit `https://waozi.xyz/`
link; it makes no claim to track visits or browsing.

The provider's `entity.game-shop` spends exact integer millionths of Dew and
restores ownership from account-scoped ledger receipts. One stable product key
is shared across retries and devices. The game grants paid skins only after a
confirmed receipt. The three prices are 10, 20 and 30 Dew.

`tests/account_test.zi` covers account changes, completion-only publication,
offline retry and playtime unlocks. `tests/account_ui_test.py` drives the actual
account build on its own verified Xvfb display in both orientations. Entity's
`python3 scripts/game_shop_test.py` additionally verifies authenticated private
node spending, retry deduplication, fresh-device restore and isolation with
throwaway accounts and Dew. GitHub Actions and live deployment are verified
separately from these local tests.
