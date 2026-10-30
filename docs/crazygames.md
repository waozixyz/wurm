# CrazyGames edition

The CrazyGames package is a separate browser edition, selected with
`WURM_CRAZYGAMES`. The normal browser, desktop, Android and hosted editions
keep their own accounts and Dew features.

Build the package from the current checkout:

```sh
LDLIBS=-lz ziran run --target=c tools/build_web.zi -- crazygames
LDLIBS=-lz ziran run --target=c tests/run_local.zi -- crazygames
```

The build writes `build/crazygames/web/` and packages it as
`work/crazygames.zip`, with `index.html` at the archive root. It preserves the
normal `build/web/` output. The packager rejects oversized packages, duplicate
loose art, shared account scripts and unexpected external page dependencies.
Only the official CrazyGames SDK loads from another domain.

Local browser tests serve the unpacked archive below a nested URL at
907 × 510 and 800 × 450. They use an isolated headless browser and a stand-in
SDK, with the real SDK network request blocked. These tests establish local
behavior; they do not establish acceptance or live operation on CrazyGames.

## Platform setup

The SDK gets the player's locale from CrazyGames, with English as fallback.
The game reports loading and gameplay events and respects the platform's
audio mute setting. Every chapter unlocks through play without Dew.

One Play click starts the game with saved controls or swipe steering for a
new guest. Controls remain available in Settings and Pause. Later levels keep
their board preview before starting.

The profile uses CrazyGames sign-in and displays the player's portal name.
Guests can play without signing in. Campaign progress and settings use the
SDK Data module for both guests and signed-in players. Select **Yes, using the
Data Module from the CrazyGames SDK** in the submission's Progress Save setting.
Without that setting, data calls fail and the game displays a warning that
progress is kept only until the page closes. A missing account record never
imports another player's local save. When the SDK is unavailable, the game
uses local guest saves.

The portal edition does not offer the Dew shop or the editor routes that
depend on the normal account service. The other editions keep those features.

CrazyGames starts new games with Basic Launch, where monetization is
disabled. Full Launch and leaderboard availability require platform approval.
The official leaderboard feature is invitation only and supports one
leaderboard per game. A source integration cannot activate those features
by itself.

Before submitting, verify the final package in CrazyGames' Preview tool,
confirm the selected account/progress options and test the SDK integration
there. Local SDK stubs cannot verify platform account configuration, score
acceptance, ad delivery or cross-device synchronization.

The independent **CrazyGames** GitHub Actions workflow runs on pushes to
`master` and can also be started with **Run workflow**. After building and
running the CrazyGames local suite, it uploads the `wurm-crazygames` artifact.
Its downloaded ZIP contains `index.html` at the root and is the package for
portal review. This workflow does not submit the game or approve covers and
gameplay videos. The local builder still produces `work/crazygames.zip`.

## Build configuration

Both settings are optional; an ordinary build has no leaderboard key and
keeps advertisements off.

For GitHub builds, set `CRAZYGAMES_LEADERBOARD_KEY` as a repository secret
and `CRAZYGAMES_ADS_ENABLED` as a repository variable when needed. With neither
configured, the artifact uses an empty key and advertisements are off.

- `CRAZYGAMES_LEADERBOARD_KEY`: the invited game's 32-byte, canonical base64
  client encryption key, matching its Developer Portal configuration. This is
  the client encryption key, not a server API key. Invalid supplied keys stop
  the build without printing their value.
- `CRAZYGAMES_ADS_ENABLED`: `true` or `false`. Enable it only after CrazyGames
  approves Full Launch. Only SDK midgame videos are requested, at completed
  campaign-level boundaries. Basic Launch keeps it false.

Configure the platform leaderboard as points, descending, non-incremental,
with a ten-second submission cooldown and an allowed range of 0–2147483647.
The game submits its best campaign run score. Requests are encrypted, queued
and retried; an SDK completion does not prove the server accepted a score.
The rankings themselves appear through CrazyGames' platform UI.

During an ad request and playback, the game blocks input and simulation.
Actual playback mutes audio; completion and errors restore the player's and
platform's mute settings. An unanswered request recovers without blocking
play indefinitely.

## Official integration references

- [SDK initialization](https://docs.crazygames.com/sdk/intro/)
- [Game events and audio settings](https://docs.crazygames.com/sdk/game/)
- [Accounts](https://docs.crazygames.com/sdk/user/)
- [Progress saves](https://docs.crazygames.com/sdk/data/)
- [Leaderboards](https://docs.crazygames.com/sdk/leaderboards/)
- [Client score submission](https://docs.crazygames.com/sdk/leaderboards-client/)
- [Gameplay requirements](https://docs.crazygames.com/requirements/gameplay/)
- [Advertisement requirements](https://docs.crazygames.com/requirements/ads/)
