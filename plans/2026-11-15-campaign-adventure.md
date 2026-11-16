# Campaign and puzzle-adventure redesign

Status: implementation, local validation and the staged-scope audit are complete. The owner rejected the resized/redesigned worm in the first graphics follow-up, so its exact pre-refresh proportions are restored while the corrected visual pass concentrates on richer terrain/tile variants, stronger area palettes and clearer basic-skin colors. The corrected atlases and all 400 campaign previews are regenerated, the fresh private-display review is complete, and the final no-mode local suite passes end to end. The coherent Wurm commit and push are next.

## Outcome

- Replace campaign levels 1–50 with fifty deliberate spatial compositions, each with a named idea, a readable route choice, and a defined place in the teaching/difficulty curve.
- Preserve levels 51–200 and every personal campaign override. Published layouts remain defaults only; player records keep priority.
- Add Puzzle Adventure as a genuinely separate mode: a map of unlockable areas, authored missions, fixed objectives, deterministic interactions, and its own persistent progress. Campaign runs, custom levels, editor state, scores, lives, and completion rewards must not leak into it.
- Keep landscape and portrait play first-class. Every campaign and adventure board needs geometry/solution evidence in both orientations.

## Provisional design pillars

1. **A spatial idea before difficulty.** Each board gets one memorable silhouette or route decision (courtyard, braid, switchback, loop, island chain, paired rooms), not a shuffled wall blend.
2. **Teach, confirm, combine, rest.** A mechanic appears alone, returns in a changed spatial context, then combines with an earlier idea. Short open recovery boards separate demanding clusters.
3. **Readable consequences.** Keys permanently open a visible gate; switches visibly change a route; matching rings connect clearly separated rooms. Adventure objectives use fixed placements rather than random apple positions.
4. **Fair growth.** Safe turning space, entrance clearance, and a full route for the grown worm remain verified. Moving hazards arrive only after their movement can be read in safe rooms.
5. **Meaningful unlocks.** An adventure area opens by completing the prior area's required missions. Area cards show the mechanic and completion, while locked areas state the requirement.
6. **Two identities, not two menus.** Campaign remains flowing arcade play with lives and score. Adventure advances one deliberate cell at a time, supports undo/restart, has no lives tax, and returns to its area map after a puzzle.
7. **Non-linear relief.** Each unlocked area offers several missions at once. Completing a required subset opens the next area, so one difficult puzzle does not stop the journey.

## Research basis and adaptation

- [Snakebird — Noumenon Games](https://store.steampowered.com/app/357300/) describes a non-linear world map, themed zones, length gain, shape planning and teleportation. Apfelwurm adapts the non-linear themed-area structure, length-aware routing and portals, without copying gravity, pushing, lifting, layouts or assets.
- [Snakebird Primer](https://store.steampowered.com/app/1014140/) and [Snakebird Complete — Nintendo](https://www.nintendo.com/us/store/products/snakebird-complete-switch/) establish the value of a gentler teaching island before the harder set. Apfelwurm therefore introduces each interaction alone, confirms it in a changed room, then combines it.
- [Apple Worm — Poki](https://poki.com/en/g/apple-worm) explains the useful tension that growth can enable progress while also causing traps. Apfelwurm uses its own top-down rule set: fixed fruit order changes body length and therefore which return routes remain safe.
- [A Good Snowman Is Hard To Build — official press page](https://agoodsnowman.com/press/) was reviewed as a reference for compact authored puzzle identity. No unsupported secret-garden or unlock claims are used.

These are design references only. The implementation stays within Apfelwurm's verified engine capabilities: top-down turning, growth, fixed or random fruit, gates, switches, matching portals and existing moving hazards. It does not invent gravity, bridging, pushing or lifting.

## Campaign pacing draft (levels 1–50)

- 1–5 — movement and space: open orchard, single divider, broad bend, courtyard, first full loop.
- 6–10 — planning for growth: offset lanes, fork and rejoin, nested garden, broad spiral, landmark crossings.
- 11–15 — matching rings: optional shortcut, forced crossing, return trip, two-room route, portal amid growth.
- 16–20 — route memory: alternating rooms, false shortcut, long return, linked courts, calm mastery board.
- 21–25 — keys and gates: key in sight, key off-route, gate-first reveal, two approach choices, key plus portal.
- 26–30 — predictable patrols: safe observation, crossing timing, circular patrol, guarded key, recovery maze.
- 31–35 — switches: visible toggle, loop-back toggle, switch beyond portal, timing with patrol, mixed mastery.
- 36–40 — meadow finale: branching rooms, chained route decisions, hazard crossing, garden gauntlet, open finale.
- 41–45 — Leafwood transition: new visual language with familiar ideas, tighter rooms, portal/key recombination.
- 46–50 — first expert set: switch and portal interplay, guarded returns, long-body routing, multi-step finale, rest vista.

The locked matrix records every opening level's name, silhouette/family, mechanic, teaching role, hazard count, apple route, and landscape/portrait certificate in `tools/design_levels.zi` and `src/designed_levels.zi`. The design and replay tests validate that matrix rather than maintaining a second hand-copied list here.

## Puzzle Adventure draft

Five areas, four missions each:

1. **Orchard Trail** — ordered fixed fruit, keys, and route reading.
2. **Moonring Ruins** — paired portals and return-path planning.
3. **Flooded Garden** — switches that change accessible corridors.
4. **Ember Burrow** — readable moving hazards combined with gates.
5. **Sky Sanctuary** — deliberate combinations of fixed objectives, keys/switches, portals, and hazards.

Adventure uses authored mission boards and mission metadata, not campaign numbering dressed as a new selector. Each mission has a fixed objective sequence and explicit interaction recipe. Input advances exactly one board cell, and an undo snapshot restores the prior deliberate move. Completing missions records only adventure completion; required completions unlock the next area. A failed, restarted or abandoned mission does not mutate campaign run data.

## Content corrections after the first review

- Replaced the campaign-derived Adventure layout cycle with twenty compact, purpose-built missions arranged as five themed areas of four missions.
- Authored each mission's fixed fruit sequence, key, gate, switch, portal and hazard positions together with a short active solution route. The Adventure replays now execute those mechanics rather than validating disabled/static board geometry.
- Added forty frozen active witnesses: every mission in landscape and portrait. The witnesses assert exact interaction coordinates, required key/switch/portal use, objective order, moving-enemy state and deterministic RNG/body state.
- Replaced the fixed 512-entry Adventure input history with a dynamic history. The real app-entry regression plays 587 moves and then undoes successfully, proving input continues beyond the former limit.
- Made undo/restart replay the same deterministic mission state and verify board, body, objective, gate, enemies and RNG after restoration.
- Added branching unlock, account separation and campaign/custom/editor isolation coverage for Adventure progress.

## Implementation surfaces

- `tools/design_levels.zi` / `src/designed_levels.zi`: explicit first-50 recipes, authored names/metadata, and generated adventure boards/metadata.
- `src/game.zi`: adventure objective state and deterministic interactions while retaining campaign rules.
- `src/progress.zi`: separate adventure record, load/save/unlock helpers, and account-switch isolation.
- `src/app.zi`: title entry, area map, mission picker, adventure HUD/ready/completion flow, and orientation reload.
- `src/locales/*.txt` / `src/localization.zi`: all new interface and objective copy in every shipped locale.
- tests: campaign content invariants, two-orientation solution replays, interaction recipes, and save isolation.
- README/CHANGELOG: player-facing behavior under Unreleased, with no version or release changes.

## Graphics follow-up after owner review

The first implementation deliberately reused the existing renderer, which left the redesigned content looking too close to the previous game. The first attempted follow-up changed the presentation without changing authored cells, collision, solutions, save data or input bounds. Its worm resizing was rejected and is superseded by the owner correction below; the useful environment work remains:

- Each of the five landscapes now owns a recognizable journey palette used across selector backgrounds, cards, frames, HUD accents and overlays.
- Campaign and Adventure boards use a crafted inset frame, continuous materials with stronger exposed edges, sparse landscape-specific details, water glints and a clearer board boundary.
- Fruit, keys, switches, portals and hazards use readable silhouettes and interaction auras. The rejected larger head/body and added face/gloss are not part of the corrected result.
- Title actions sit on a coherent journey deck; stage, level, Adventure-area and mission selectors use illustrated covers, material cards, progress rails/dots and area-specific color.
- Ready, pause, victory, settings, shop, controls, editor and local-multiplayer surfaces inherit the same frame/card language.
- The private-display suite now captures the Adventure area map, mission picker and live puzzle in addition to its campaign/title/editor/settings/multiplayer coverage.

The bounded pre-edit audit inspected all 143 existing private-display PNGs in six contact sheets under `build/research/visual-review/`. Fresh display-free title and live-board renders are collected in `graphics-follow-up.png`; the landscape frame, continuous ground, stronger walls, object auras, connected worm and classic character face are all visible there. The upstream Kryon artifact-input defect found during the first fresh run was repaired, after which all 13 private-display scenarios passed and restored the stable native binaries.

### Owner correction: terrain and color, not a larger worm

The owner rejected the worm resizing and face/gloss redesign. The corrected pass restores the earlier head/body sizes, draw stride, sprite opacity, classic head art and local-multiplayer geometry exactly; board dimensions, on-screen cell size, camera, collision and controls remain unchanged. The connected body already present before the rejected pass stays at its earlier proportions.

The graphics effort now targets the requested surfaces:

- expose multiple deterministic crops from each high-resolution journey material instead of stamping one identical 32-pixel floor/wall cell across a board;
- select those variants by board position while retaining all existing tile IDs and collision semantics;
- enrich sparse top-down landscape details and keep every decoration non-interactive;
- brighten the five area palettes without changing layout geometry; and
- strengthen the companion body colors for the basic skins while preserving every skin image, identity, selection and directional transform.

The complete related source-art set, all existing skin captures, the recovered references, five landscape captures and both rejected-pass closeups were inspected in three contact sheets under `build/research/visual-review/` before this correction was implemented.

The corrected atlas packs nine deterministic material crops per landscape, varied smart-wall pieces, three water frames and four floor variants while keeping every stable sprite coordinate and collision tile ID. `build/research/visual-review/corrected-atlas-variants.png` records the five-area atlas review. The previous landscape, portrait and four basic-skin captures were copied to `build/research/visual-review/before/` before the fresh private-display run. The matching fresh results are collected in `after-gameplay-contact.png`, `after-skins-contact.png` and `basic-skins-before-after.png`; review confirms the earlier head, stride, body width and skin geometry in both orientations while showing richer materials and clearer basic colors.

## Verification ledger

- [x] Research decisions incorporated and content matrix locked.
- [x] First 50 generated from explicit authored recipes; generated levels 51–200 are byte-stable against the previous revision.
- [x] Campaign design test proves 50 unique concepts and both-orientation reachability.
- [x] Campaign geometry replays solve all 200 in both orientations with authored moving hazards active; this legacy 400-board certificate disables portal/key/switch mechanics.
- [x] Adventure engine replays solve every mission in both orientations and exercise key, switch, portal, ordered-objective, and hazard combinations.
- [x] Adventure unlock/save tests prove campaign/custom/editor records are untouched.
- [x] Locale generator and authored/designed-level generators are current.
- [x] Focused native engine suite passes, including 400 hazard-active campaign geometry wins, 40 active Adventure witnesses, deterministic undo, branching progress and native/portable input integration.
- [x] Active-mechanics campaign witnesses solve the redesigned first 50 in both orientations and prove intended portal/key/switch engagement.
- [x] The real app-entry regression accepts 587 Adventure moves and then undoes, covering the removed 512-move cap.
- [x] Native desktop and portable shared entries build at their stable paths; portable outputs are `build/games/wurm.zx` and `build/games/wurm-editor.zx`.
- [x] Full local suite passes through `build-queue`.
- [x] UI navigation is exercised on a private display with inherited desktop variables scrubbed and recovery disabled.
- [x] Fresh private-display screenshots reviewed for the graphics follow-up, including Adventure selectors and live board.
- [x] Parent handoff completed before commit; the owner's direct commit request superseded the earlier internal review hold.

## Current local verification evidence

All commands below ran through `build-queue`; GitHub CI is separate and has not been checked for this uncommitted work. The bounded native record is Harmony task log `5ca974fa260fdae85130606c63ebcec8d32b`, and this ledger keeps the review summary outside generated build output.

- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/run_local.zi -- engine` — passed with `game_test`, `start_clearance_test`, `meadow_test`, `campaign_design_test`, `campaign_replay`, `adventure_test`, `progress_test`, `editor_test`, `multiplayer_test`, plus native and portable input integration. Campaign replay reported 400 wins with active enemies and zero lives used; the focused first-50 certificates additionally reported 100 wins with intended portal/key/switch mechanics active. Adventure reported all 20 missions and 40 active witnesses.
- `build-queue -- python3 tests/arcade_entry_test.py` — passed the normal, editor and hosted shared-entry paths, including the 587-move Adventure route followed by undo.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/run_local.zi -- account-navigation` — passed with zero account-navigation failures after building the full non-bootstrap application runtime.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/run_local.zi -- hosted` — passed with zero hosted-UI failures.
- `build-queue -- python3 tools/build_portable.py` — passed; stable outputs are `build/games/wurm.zx` (40,652,050 bytes, 2026-11-15 22:40 local) and `build/games/wurm-editor.zx` (6,732,947 bytes, 2026-11-15 22:40 local), with resource manifests beside them.
- `build-queue -- env LDLIBS=-lz ziran build desktop` — passed at Ziran `7441f9f5` and restored the native application at its stable desktop path.
- `build-queue -- ziran check` — passed.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tools/make_art.zi` — passed and regenerated all five corrected campaign atlases at their stable paths.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tools/render_previews.zi` — passed and regenerated all 400 campaign previews at their stable paths.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tools/make_art.zi -- --check` — passed with `Five journey atlases, reference art and title mirrors verified.`
- `build-queue -- env LDLIBS=-lz ziran run --target=c tools/render_previews.zi -- --check` — passed with all generated campaign previews matching regeneration.
- `build-queue -- sh -c '<decoded-pixel comparison against HEAD>'` — confirmed the five corrected landscape atlases and their ARGB sources contain real changes. Six incidental generator rewrites were pixel-identical and were restored byte-for-byte, so they will not enter the feature commit.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/run_local.zi -- ui` — passed after the upstream Kryon artifact-input repair. It built test-driven desktop and modal editions, exercised all private-Xvfb navigation in both orientations with inherited display/session variables removed and desktop recovery disabled, then restored the normal stable desktop and modal binaries. The direct runner reported all 13 interface scenarios successful, including campaign/Adventure selection, editor, controls, skins, the semantic volume slider and multiplayer.
- `build-queue -- python3 tests/skin_art_pixels_test.py /mnt/storage/Projects/waozixyz/modules/entity` — passed after narrowing the base-sheet comparison to the exact head/body cells shared with the profile. Chapter terrain can vary while all thirteen wardrobe identities keep identical game and leaderboard pixels.
- `build-queue -- ziran lock` — passed and recorded the complete locally tested dependency graph.
- `build-queue -- env LDLIBS=-lz ziran run --target=c tests/run_local.zi` — final no-mode rerun exited 0 with `Apfelwurm local tests passed; GitHub CI is separate.` It covered all 400 active-enemy campaign wins, 100 first-50 mechanics witnesses, all 40 active Adventure witnesses, persistence/input/account/hosted/art/audio/picture gates, portable packaging and both final desktop builds.
- In the upstream Game2D dependency, `build-queue -- make test` passed native and portable navigation/control, swipe, public-import and raylib-ABI tests for the public Kryon API migration.

A prior full no-mode `tests/run_local.zi` pass completed every Wurm campaign, Adventure, persistence, input, account, hosted, art, locale, audio and picture body, then its final desktop artifact publication was invalidated when the shared Ziran checkout changed revision during the provider transaction. The separately rerun account-navigation gate now passes with zero failures, the private-display UI gate passes all 13 scenarios, and a fresh native desktop build completes.

One rerun exposed an uncommitted shared Ziran fuel-register experiment when the portable half of `steering_test` trapped in `SessionOpen`. The exact evidence was routed upstream; that experiment was removed and the shared tools rebuilt. The exact command `build-queue -- ziran run --project build/steering-test/test.zx` then passed. A later final no-mode run also completed every Wurm-owned gate and both final desktop builds from the corrected graphics state.
