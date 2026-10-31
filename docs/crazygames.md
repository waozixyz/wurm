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
907 × 510, 800 × 450 and portrait 450 × 800. They exercise cover navigation,
painting, failed-save retry, playtesting, account isolation and full reloads
with SDK Data and local saves. They use an isolated headless browser and a stand-in
SDK, with the real SDK network request blocked. These tests establish local
behavior; they do not establish acceptance or live operation on CrazyGames.

## Platform setup

The SDK gets the player's locale from CrazyGames, with English as fallback.
The game reports loading and gameplay events and respects the platform's
audio mute setting. The base 160 levels unlock through play; Mountains opens
only after the configured CrazyGames chapter appears in verified inventory.
An older unowned Mountains save continues at the last free level without
erasing its unlocked/completed history.

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

The title swipes between Play/Continue and Level editor, with visible arrows
and page dots. Arrow keys and wheel select a cover; Enter activates it.
Stages remains below, L opens stages, and E opens the editor directly.

The editor supports New level, From a level, My levels, painting, orientation
and playtesting. Private collections use account-scoped SDK Data (a 640 KiB
snapshot budget); campaign overrides also use SDK Data. Failed writes retain
unsaved edits for retry. Without the SDK, drafts use local browser storage.
Community and sharing are unavailable on this edition; the Dew shop is absent.

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

## Native Store

The title Shop opens native **Skins**, **Stages** and **Coins** tabs. The wallet
shows game coins; configured paid cards show the actual player's catalog
amount and currency, or Free for an explicitly free item. Missing prices and
unconfigured products stay unavailable. Purchases require explicit confirmation.
Restore purchases and Refresh reconcile inventory without charging. Pending
checkout disables repeat charges while Back and the game remain available.
The normal edition retains its 20 Dew Mountains offer.

`src/portal_shop.zi` owns the CrazyGames Store lifecycle and pumps every frame,
even outside the shop. Only verified inventory unlocks configured durable skins
and Mountains; saved wardrobe masks never grant them. Earned coin skins and daily
gifts retain the Rewards rules, with strict SDK Data writes and retry on failure.
Daily chest rewards show coins/gifts without Dew prompts. The chosen skin setting
survives inventory loading and becomes visible once ownership is restored.
No real catalog mapping or IAP activation has been established.
`SDK.store.isAvailable` gates payment on supported app versions/countries;
it does not establish that this game's IAP catalog is configured or enabled.
The runtime separates this from module/read availability, so unsupported
payments never revoke or block restoration of verified known entitlements.
See the official [app payment contract](https://docs.crazygames.com/resources/crazygames-app/)
and the
[Store API](https://docs.crazygames.com/sdk/store/).

The default public config is `{"version":1,"sandbox":false,"products":[]}`.
This disables paid products gracefully, including when the SDK is missing.
The following optional build inputs are mutually exclusive:

- `CRAZYGAMES_STORE_CONFIG`: the public JSON config itself.
- `CRAZYGAMES_STORE_CONFIG_FILE`: a path to the public JSON config, at most
  32 KiB. The build rejects an empty file, invalid mappings and `sandbox:true`.

For example, after an operator has supplied verified mappings, a local package
build can use `CRAZYGAMES_STORE_CONFIG_FILE=work/crazygames/store.json` with
the existing `tools/build_web.zi -- crazygames` command. Inline empty config is
`CRAZYGAMES_STORE_CONFIG='{"version":1,"sandbox":false,"products":[]}'`.
These inputs write public `window.WurmPortalStoreConfig` into the package's
existing `portal-config.js`. They never configure an external catalog or
account. Do not put credentials or tokens in them.

[crazygames-store.example.json](crazygames-store.example.json) illustrates
skins 1, 2, 3 and 7, Mountains and three coin packs. Every SKU and purchase ID
there is explicitly `EXAMPLE_ONLY`; none is a real project catalog ID. Pack
amounts also illustrate the format. The builder never selects this file by
default. Replace every mapping with operator-confirmed values before use.
No prices belong in this config: fresh personalized SDK catalog values supply
`amount`, `amountWithoutDiscount`, `currency`, `isFree` and `canBeBought`.
Missing paid prices disable checkout. Only explicit `isFree:true` permits a
null price.

Products use explicit `kind`, `sku` and `purchaseId` fields. `kind:"skin"`
requires `skinId` 1..8; `kind:"mountains"` has no skin ID; `kind:"coins"`
requires `packCoins` 1..1,000,000,000 and `cumulativeInventory:true`. There
are at most 32 mappings, with unique SKU and purchase ID, unique durable skin
IDs and one Mountains product. Coin skins 9..12 belong to the existing Rewards
system, separate from the durable Mountains mask 512.

For packs, `cumulativeInventory:true` is an operator attestation that each
SKU is **counted, stackable and never consumed**, with one inventory unit per
purchased pack and cumulative counters retained across sessions. This must be
confirmed in the external catalog before enabling a pack. Wurm never calls
`consumeItem` or adds credits from a checkout result. Complete inventory
quantities replace the verified Rewards credit total; repeating a refresh
does not add credits, and reduced quantities reduce credits. The existing
Rewards save format remains unchanged. There is no new wallet ledger.

Import `PortalShop :: #import, file "portal_shop.zi";`. The UI-facing API is:

- `Configure(json: string) -> bool` replaces config and resets the session;
  invalid input disables it. `Init() -> bool` instead reads the public page
  config. Call one at startup; `Open` and `Pump` also initialize lazily.
- `Pump(now: s64)` takes **monotonic milliseconds** and runs once per frame,
  including while the shop is closed. It detects account/availability changes,
  discards old epochs, and reconciles async results. `Reset()` invalidates old
  callbacks and clears verification while keeping config.
- `Open()` requests fresh catalog/inventory. `Refresh() -> bool` and
  `Restore() -> bool` request the same reconciliation. They never charge.
- `Buy(index: s32) -> bool` accepts only an explicit user action for a configured
  product index. A true return means fresh preflight was queued, not payment
  success. It requires a signed-in SDK profile with a stable public ID and
  rejects active work or any unresolved marker. It refreshes personalized
  catalog, stock and complete inventory before invoking the configured ID.
- `StoreState() -> *Model.StoreState` exposes model-owned products, readiness,
  quantities and catalog display fields. Treat it as read-only; both readiness
  flags gate buying and `inventory_ready` gates displayed ownership. Last-good
  values can remain in the struct after an error.
- `Status() -> string`, `Pending() -> bool`, `Busy() -> bool` and
  `Authenticated() -> bool` expose concise UI state. Status values include
  `unavailable`, `config-invalid`, `loading`, `sign-in`, `ready`, `checking-out`,
  `pending`, `restored`, `cancelled`, `storage-error`, `sdk-busy`, `sdk-timeout`,
  `sdk-error`, `catalog-error` and `inventory-error`. Pending calls for Restore; it never
  means the item was granted.
- `PurchasesAvailable() -> bool` exposes payment capability separately from
  model read availability. `CanPurchase() -> bool` also requires authentication,
  idle work, no pending marker and both ready snapshots. Product-level catalog
  and ownership rules still apply during `Buy` preflight.
- `OwnedSkinMask() -> s32` returns verified durable skin bits 1..8;
  `OwnsMountains() -> bool` returns verified Mountains ownership separately.

The bridge retains the documented SDK v3 `getUser().__dangerousUserId` as the
native `userId` account scope. It is not a server credential. Display usernames
never authorize checkout; SDK.user/store retain payment authentication. Guest
profiles can browse a fresh catalog but cannot buy or load player inventory.
Auth listeners invalidate generation before the existing full page reload.
Catalog preflight also re-reads `getUser()` when accounts are available;
a changed identity invalidates the operation before personalized catalog or
checkout calls.
Account changes reset Rewards; CrazyGames does not activate normal Dew sign-in.
See the [official account contract](https://docs.crazygames.com/sdk/user/).

Native paging uses limits of 50, at most 256 merged items and less than 1 MiB
per snapshot. Catalog pages end only at `hasMore:false`; inventory ends at a
short page. Catalog failures still attempt inventory restoration for known
SKUs, with paid checkout disabled until a fresh valid catalog returns.
One SDK call runs at a time. A ten-second request timeout revokes
verification and retains the active guard until the SDK promise settles; it
does not close Pay Station or invent cancellation. Store snapshots never come
from SDK Data ownership caches.

Before checkout, raw account-scoped SDK Data must save and read back a bounded
`wurm-store-pending-v1` marker (version, account ID, configured SKU/purchase ID,
baseline quantity). Missing is distinct from an unknown read. A malformed or
unknown marker blocks buying. It grants nothing. Known cancellation clears it
with verified storage; uncertain errors retain it. After SDK resolution the
runtime refreshes inventory, with at most five bounded follow-up attempts.
Only durable ownership or a pack counter increase beyond baseline clears the
marker. Reload/Restore follows this same path without another charge. Storage
errors can require recovery before checkout becomes available again.

Run the focused local suite without building the final app:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER \
  YUE_DESKTOP_RECOVERY=0 ZIRAN_PAR_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j1 LDLIBS=-lz \
  ziran run --target=c tests/run_local.zi -- store-runtime
```

It runs native lifecycle/config/model/Rewards tests, checks the web runtime
surface and drives the actual transport/page with SDK stubs in a private
headless browser. The fixture blocks external requests and loads no game or
payment payload. `sandbox:true` is accepted only by local SDK fixtures;
production builds reject it. These local tests establish no live purchase,
IAP activation, real catalog, deployment or platform approval.

## Official integration references

- [SDK initialization](https://docs.crazygames.com/sdk/intro/)
- [Game events and audio settings](https://docs.crazygames.com/sdk/game/)
- [Accounts](https://docs.crazygames.com/sdk/user/)
- [Progress saves](https://docs.crazygames.com/sdk/data/)
- [Leaderboards](https://docs.crazygames.com/sdk/leaderboards/)
- [Client score submission](https://docs.crazygames.com/sdk/leaderboards-client/)
- [Gameplay requirements](https://docs.crazygames.com/requirements/gameplay/)
- [Advertisement requirements](https://docs.crazygames.com/requirements/ads/)

The private real-game fixture in `tests/web_test.zi` substitutes SDK, public
sample mappings and account data only. It navigates the actual Wasm canvas using
pointer, wheel, touch and keyboard input. Commerce cases cover personalized
USD/EUR prices, explicit free/missing-price products, explicit purchase IDs,
cancellation/retry, pending reload/restore without a second charge, verified
skin wearing and chapter play, cumulative pack refresh/reload, failed coin
spend/retry, unsupported-payment/catalog-error restore and account isolation.
Private screenshots are written under `work/crazygames/store-ui/`; none are
included in the package. The suite also retains editor and lifecycle coverage.
