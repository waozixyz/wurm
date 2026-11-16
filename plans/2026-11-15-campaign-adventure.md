# Campaign and integrated-challenge redesign

Status: owner correction implemented and the stable pinned release graph passes
the focused, private-display and complete local validation gates. Release 0.2.34
metadata and artifacts are current; the coherent release commit and push are next.

## Owner outcome

- Replace levels 1–50 with fifty deliberate spatial compositions, each with a
  readable route idea and a defined place in the teaching curve.
- Keep puzzle goals inside the normal campaign. There is no extra mode, mission
  selector, move counter, undo system or separate input cadence.
- Give every opening level a challenge that observes ordinary real-time play.
  Missing it never blocks campaign progress; completing it earns a persistent
  account-specific star.
- Preserve levels 51–200, personal level overrides, campaign saves, editor data,
  shader terrain and the restored classic worm proportions.
- Keep landscape and portrait first-class, with solution evidence for every
  opening board and challenge.

## Research adaptation

The earlier research into Snakebird, Snakebird Primer, Apple Worm and A Good
Snowman is retained only as pacing guidance: introduce an interaction alone,
confirm it in a changed spatial setting, then combine it. Apfelwurm keeps its
own continuous top-down play, lives, scoring and existing portal/key/switch
rules. It does not copy gravity, pushing, layouts, one-step input or a separate
puzzle-map structure.

## Campaign pacing

- 1–10: open orchards, dividers, courtyards and growth routes.
- 11–20: matching portals, return paths and route memory.
- 21–30: keys, gates and readable patrol timing.
- 31–40: switches, loop-backs and the Meadow finale.
- 41–50: Leafwood transition and deliberate mechanic combinations.

The authored matrix in `tools/design_levels.zi` remains the source of truth for
names, silhouettes, mechanics, teaching role, hazards and certified loops.
`src/designed_levels.zi` is generated from it. Levels 51–200 are unchanged.

## Integrated stage challenges

Every first-50 stage selects exactly one goal after its normal board and
interaction are loaded:

- ordered fruit: collect the fixed authored fruit route;
- landmark: reach a visible garden stone generated from the certified loop;
- clean run: finish without a collision;
- portal: use a matching portal;
- key: collect the key and open its gate;
- switch: activate the switch stone.

The ready card explains the goal, the live board keeps it visible, and level
cards show earned stars. Goals are event-based and never count moves. The same
normal level completion, lives, score and next-stage flow remain in effect.

Challenge stars use an account-scoped `challenges.dat` record, isolated from
campaign run state, unlocked levels, completion rewards and custom levels. On
first load, an old 20-mission puzzle record is copied once onto stages 1–20 so
existing owner progress is not discarded. The removed legacy record is never
used for new writes.

## Implementation surfaces

- `tools/design_levels.zi` and `src/designed_levels.zi`: authored first-50
  layouts plus orientation-specific landmark cells on certified loops.
- `src/game.zi`: live challenge state and completion from actual play events.
- `src/progress.zi`: account-scoped stars and legacy progress migration.
- `src/app.zi`: ready/live challenge presentation and level-card stars; the
  obsolete separate-mode routes and selectors are removed.
- `src/locales/*.txt` and `src/localization.zi`: all challenge text translated.
- `tests/campaign_replay.zi`: all 200 stages replay in both orientations, with
  every opening challenge required to complete.
- persistence, account, navigation and private-display tests cover isolation,
  migration, status messaging and the live challenge HUD.

## Validation log

- `build-queue -- env LDLIBS=-lz ziran run --target=c tools/design_levels.zi`
  regenerated the authored source and certified routes.
- `build-queue -- ziran check --project` passed after the integrated model was
  introduced.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/campaign_replay.zi -- normal 26 26`
  passed the targeted landmark regression in landscape and portrait.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/run_local.zi -- engine`
  passed: 400 campaign wins with active enemies, both orientations, all
  first-50 challenges complete and zero lives used; progress, editor,
  multiplayer, terrain and native/portable input tests also passed.
- `build-queue -- env LDLIBS=-lz ziran run --locked --target=c tests/run_local.zi -- account-navigation`
  passed on the pinned graph with zero failures. The live local dependency graph
  was intentionally not used for release evidence because its Kryon checkout was
  in the middle of an unrelated desktop-host edit.
- `build-queue -- env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS HARMONY_DESKTOP_RECOVERY=0 WURM_UI_ONLY=challenge LDLIBS=-lz ziran run --locked --target=c tests/run_local.zi -- ui`
  passed the focused normal-stage challenge briefing and live HUD scenario on a
  private display.
- The same pinned private-display command without `WURM_UI_ONLY` passed every UI
  scenario, including editor, input, dialogs, rotation, skins and multiplayer.
- `build-queue -- python3 tools/build_portable.py` produced the stable portable
  game/editor bundles and download archive.
- `build-queue -- env LDLIBS=-lz ziran run --locked --target=c tests/run_local.zi`
  passed the complete repository suite: generated sources and art, all 400
  active-enemy campaign wins and first-50 challenges, account and hosted paths,
  orientation, audio, headless renders and native desktop builds.

## Release gate

- `build-queue -- sh update_version.sh` synchronized release 0.2.34 and Android
  version code 44 from the changelog.
- The complete pinned no-mode suite passed again after the version change.
- Pinned portable packaging rebuilt `build/games/wurm.zx`,
  `build/games/wurm-editor.zx` and
  `build/downloads/wurm-portable-v0.2.34.tar.gz`.
- `git diff --check` passed, the local dependency override was restored, and
  no temporary validation backup remains.
- Commit once, push once, and leave CI/release completion to the existing
  workflow watcher.
