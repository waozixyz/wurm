<p align="center">
  <img src="assets/art/title.png" alt="Apfelwurm — a little orange worm, an apple meadow and a mountain to climb" width="100%">
</p>

<p align="center">
  <strong>A little worm. A long journey.</strong><br>
  <a href="https://wurm.waozi.xyz/"><strong>Play free in your browser</strong></a>
  · <a href="https://github.com/waozixyz/wurm/releases/latest"><strong>Download for Android</strong></a>
  · <a href="CHANGELOG.md">What's new</a>
</p>

# Apfelwurm

Collect the apples. Find the gate. Keep growing.

Guide a little orange worm from sunny apple meadows through woodland and
lakeshores to the mountains. Apfelwurm brings the spirit of the original
Worm game to **200 distinct levels**, with illustrated landscapes, a gentle
acoustic soundtrack and controls that respond while your finger stays down.

Free to play. All 200 levels can be unlocked through play. No ads. An optional account keeps your
progress and character choices in sync, with cosmetic skins available for Dew.

## Five landscapes. Forty levels each.

- **Meadow:** find your rhythm among grass, hedges and orchard paths, with a slower opening pace.
- **Leafwood:** weave through leafy rooms, mossy courtyards and branching trails.
- **Pinewood:** follow fir-lined passages and watch the patrols around the next corner.
- **Lake:** cross the shores, channels and islands without running out of room.
- **Mountains:** wind through rock corridors, terraces and the final ascent.

Layouts take inspiration from the recovered original game's rooms, spirals
and crossings. Wandering fire, bouncing patrols and chasing enemies make the
journey more demanding as you climb.

Press **Play** and you are straight in the game. The levels follow one after
another through all five landscapes. You start
with three lives and earn more as your score grows. Score and lives carry
between levels throughout your run. **Continue** starts the furthest level
reached in your journey with three lives and a fresh score, even after a game
over or closing the game. **Play from start** begins a new run at level 1
without erasing your progress.

**Choose level** lets you browse all five landscapes, see a large board preview for unlocked levels and a lock for later levels.
Complete a level to unlock the next one.
After a game over, **Try again** starts the furthest unlocked level with
three lives and a fresh score.

## Play your way

Choose **swipe steering** or a **direction pad** on first play. With swipe
steering, move your finger in the direction you want to turn and keep it on
the screen for the next corner. Change your choice from Pause at any time.

On a keyboard, use the arrow keys or WASD. Space or Escape pauses; M mutes.
Collect every apple, then leave through the opening at the top of the board.

Portrait and landscape use their own board layouts. Your unfinished run stays
on this device. Android and the browser can play offline after their assets
are loaded. Signing in syncs earned completion marks and preferences.

## Make a path of your own

Open the level editor with **E** from the title. Browse all 200 boards,
paint terrain and enemies, adjust the apple goal, then playtest from the entrance.

**Landscape** and **Portrait** are independent editor modes. Start a missing
portrait layout from a best guess, refine it, and save without changing the
other version. Playtest always uses the selected layout.

<p align="center"><img src="assets/marketing/editor.png" alt="The portrait level editor with separate Landscape and Portrait modes, terrain brushes and six enemies" width="85%"></p>

## Keep the journey yours

Open **Settings** on the title to choose the softer Dusk, Forest or Sage theme,
change controls or switch sound on and off. **Profile** uses the same account
system as Shovey: create an account, import your key or link another device.
Completion marks, active playtime, preferences and your chosen skin follow the
signed-in account. Guest progress and each account stay separate. Your
unfinished run and personal editor records stay on this device.

The title's **Skin shop** offers Mint for **10 Dew**, Berry for **20 Dew** and
Rose for **30 Dew**, with confirmation before buying. Retrying a purchase,
including from another device, cannot charge for that skin twice. Earn
**Night owl** by playing actively for **5 hours**, **Golden apple** by
completing **level 40**, or **Explorer** by opening **waozi.xyz** from the shop.
Levels unlock through play; Dew buys optional cosmetics.

Account sync and Dew need a connection. There is no advertising or analytics,
and personal editor records are kept out of published packages.

[Play Apfelwurm](https://wurm.waozi.xyz/)
· [Android downloads](https://github.com/waozixyz/wurm/releases/latest)
· [Browser privacy](https://wurm.waozi.xyz/privacy.html)

## Build and contribute

Built with [Ziran](https://ziran-lang.org) and [Kryon](https://kryonlabs.com).
The desktop, Android and browser editions share the same game rules.

```sh
python3 tools/build_desktop.py
build/account-desktop/wurm
sh tests/run_local.sh
```

See the [build and development guide](docs/building.md) for the editor's
save files, Android and portable builds, asset recovery and verification.
[Report a bug or suggest a level](https://github.com/waozixyz/wurm/issues).
