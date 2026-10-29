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
stages. Meadow has wider routes, five apples on most boards, no enemies for its
first 20 levels and at most one predictable patrol afterward. Landscape boards
follow the portrait gardens rather than rotating their obstacles.
One pair of portal rings introduces a simple optional shortcut on levels 10,
12, 16, 23, 31 and 38. Their exits have room to turn, and those lessons have no
moving enemies. The ready dialog explains the rings. Later chapters retain
their existing puzzle progression. Personal editor layouts remain unchanged.
Levels follow in order through every landscape. After each goal, the next
board opens dimmed and waits for **Start level** (or Enter/Space). Movement
and enemies stay paused until then; lives and score carry over. Choose level offers a
scrollable grid for each landscape; unlocked levels have large board previews and future levels show a lock. The run (level, lives and score carried into that level) and the
control choice persist. Unlocked progress is saved after every completed
level and survives game over, closing the game and starting a new run.
Continue starts the highest unlocked level with three lives and a fresh
score; Play from start begins at level 1. Earlier save records are imported.
Try again after game over also starts the highest unlocked level with fresh
lives and score, including after replaying an earlier level.
`tools/design_levels.zi` regenerates the boards and static route certificates.
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
to edge. Each level's portrait leads: a landscape without its own record
mirrors the portrait, and a portrait without a design mirrors the
landscape. Mirroring never turns a board. Ten lines leave one axis and ten
repeat along the other, so the entrance stays at the bottom and the exit at
the top. It keeps every floor region, passage, creature count, apple goal
and puzzle idea. A portrait mirror stays at least as roomy as its source: it
thins walls before floor and may drop a small lone hedge pillar, and of its
candidate spreads it takes the most open one. Landscapes may play a little
harder. `tests/orientation_test.zi` checks all 400 boards and plays each
with every apple and full growth (geometry only: creatures and puzzle
ideas off).
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
the other. A layout without its own record shows the mirror of the other,
the player's own first, and is labelled **Mirrored**; Save keeps it as an
independent layout. Should a personal edit leave no mirror that keeps every
passage, a portrait shows the rotated **Best guess** and a landscape its
published board instead. Playtest uses the selected mode even when the
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
`level<N>-portrait.dat` file there, then run `LDLIBS=-lz ziran run --target=c tools/authored_levels.zi`
and `LDLIBS=-lz ziran run --target=c tools/render_previews.zi`. The generated boards are compiled
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
LDLIBS=-lz ziran run --target=c tools/build_desktop.zi
build/account-desktop/wurm
LDLIBS=-lz ziran run --target=c tools/build_android.zi -- --abi arm64-v8a
ziran run --locked shot > build/stages.ppm
WORM_SHOT_LEVEL=200 ziran run --locked shot > build/forest-finale.ppm
ziran check --locked
LDLIBS=-lz ziran run --target=c tests/run_local.zi
```

Wurm's tools and tests are Ziran programs; `ziran run --target=c` builds each
once and runs it. `LDLIBS=-lz ziran run --target=c tests/run_local.zi -- ui`
runs `tests/private_ui_test.zi`, which additionally exercises the real desktop build on
its own verified Xvfb server. It checks all three dialogs in 320x568 portrait
and 640x360 landscape, including their primary and Back to title actions.
It never uses the owner's desktop. The audio
test uses SDL's dummy drivers and verifies that all effects and scores mix.

The Android debug APK is written to `build/android/`. Use `--abi armeabi-v7a`
for the development Moto, and `--verification` for the separate
`xyz.waozi.wurm.verification` install, preserving the normal game and data.
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
LDLIBS=-lz ziran run --target=c tools/build_android.zi -- --release --abi universal
LDLIBS=-lz ziran run --target=c tools/android_release.zi -- sign build/android/Apfelwurm-universal-release-unsigned.apk
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
LDLIBS=-lz ziran run --target=c tools/build_android.zi -- --release --abi universal --edition gplay
LDLIBS=-lz ziran run --target=c tools/android_release.zi -- sign build/android/Apfelwurm-universal-gplay-release-unsigned.apk --edition gplay
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
`tools/make_art.zi` crops and packs those cells into the landscape
sheets without changing gameplay tile IDs or collision rules. It also writes
the display-free `.argb` mirrors. Run it with `--check` to verify the packed
art matches its sources. `assets/art-source/journey-terrain.png` supplies
the five landscape materials; its built-in image-generation prompt is recorded
in `assets/art/title.json`. The same golden orange worm and red apples appear
throughout the journey. `assets/sounds/sounds.json` records the OpenRouter model and prompt
of every sound. The current acoustic garden score was AI-generated with
Lyria; it is not the recovered original MIDI. Garden, factory and space now
form a rotating score. Every four levels requests another piece; long levels
also advance before the current piece ends. Changes wait for a musical phrase
and blend over 4.8 seconds instead of cutting or rewinding. The Ready screen
keeps the score playing between levels, with the start cue reserved for Start.
Loop reads wrap without padding silence, and the native mixer buffers enough
audio to tolerate slower phone frames. The browser uses the same pieces and
fade timing. The packed Arcade host continues to supply its own background
audio and receives the game's effects.

## Recover the assets again

```sh
LDLIBS=-lz ziran run --target=c tools/extract_original.zi -- /mnt/storage/Games/The-Worm_Win_EN
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

`LDLIBS=-lz ziran run --target=c tools/build_web.zi` compiles the same game with Kryon's Canvas2D host
and Emscripten. `LDLIBS=-lz ziran run --target=c tests/run_local.zi -- web` runs a private
browser test, including
control selection, the direct start, portrait resizing and persistent saves.
The browser stores records through Kryon's IndexedDB provider.

The Downloads workflow packages the verified web build beside the signed APKs.
The website repository's Apfelwurm site workflow checks for a newer published
release every ten minutes and deploys its verified browser archive to the
`wurm` Cloudflare Pages project at https://wurm.waozi.xyz automatically, using
the website's existing deployment credentials. Nothing needs updating by hand.

## Profile, appearance and cosmetics

The release desktop build uses `tools/build_desktop.zi`. Android and browser
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
offline retry and playtime unlocks. `tests/account_ui_test.zi` (`run_local.zi -- account-ui`) drives the actual
account build on its own verified Xvfb display in both orientations. Entity's
`python3 scripts/game_shop_test.py` additionally verifies authenticated private
node spending, retry deduplication, fresh-device restore and isolation with
throwaway accounts and Dew. GitHub Actions and live deployment are verified
separately from these local tests.

`tests/account_navigation_test.zi`, which `run_local.zi` builds, exercises the real Wurm frame and
Entity provider without a display, using an isolated account under ignored
`work/account-navigation/`. It verifies actual leaderboard score rows, repeated
opening in both orientations, and Back after an account changes while the
leaderboard is open. It preserves the desktop executable and installed apps.
The USB Moto Profile test also checks repeated score rows and leaving the
activity with Android Back from the title; that device test requires its
verification APK to be installed.
