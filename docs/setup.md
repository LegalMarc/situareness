# Install and operate the room

## What runs where

The packaged `extension/` contains the room and requires no application server, API key, account, or runtime npm dependencies. Its toolbar button opens or reuses a room tab. Browser collection can continue when the tab closes while Chrome and the profile are running and the computer is awake; it stops when Chrome exits or the computer sleeps.

Home Assistant is a separately installed monitor, independent of Chrome and shadow by default. The room displays its HA status as not connected; it does not read HA health. See [Home Assistant setup](ha/README.md).

## Load into Chrome

1. Open `chrome://extensions` in Chrome and enable Developer mode.
2. Select **Load unpacked** and choose the project's `extension` directory.
3. Pin Situareness and use its toolbar button to open the room.

After a code change, reload the extension. Settings persist in that Chrome profile. Export them before removing the extension if needed.

## Settings and privacy

The room supports editable watched locations, source enablement, polling and display links. The public examples in `config/watch-configuration.json` and `extension/defaults/config.json` use New York City and Washington, DC. A county association is regional awareness only; it does not prove a particular household is exposed. The editor rejects private household footprints, device enrollment, and live actions.

Browser settings and exports still contain watched locations and are sensitive. Do not publish or share them as safe defaults. Store a local export at `ignored-resources/private-config/room.json`. Browser runtime settings live in Chrome storage; editing this file does not change the room until it is imported. The separate HA configuration working copy is `ignored-resources/private-config/home-assistant.json`; copy it privately to HA as `<config>/situareness.json`. Do not commit either file.

## Sources and freshness

The room reads NWS alerts, USGS `all_hour` earthquakes, BBC World and BBC US & Canada. NWS and USGS have one-minute default polling targets; BBC has five-minute targets. USGS reports events after they occur and is not an earthquake early-warning service. Provider propagation and caching, network conditions, Chrome scheduling and sleep add uncertain delay; the room does not guarantee the earliest report.

Source status, collection and source timestamps, errors, stale state and truncation indicate what was retrieved. Cached results survive a failed fetch. An empty view or absence from a bounded fetch is not an all-clear or proof of cancellation. Source links provide further context. `config/source-catalog.example.json` is a research catalog, not an input to these collectors. See [the primary-source roadmap](plans/primary-source-roadmap.md).

## Develop and verify

With Node 22.19 or newer and Python 3.11 or newer:

```sh
npm ci
npx playwright install chromium
npm run check
npm run test:browser
npm run package
```

Browser tests use fixtures and isolated profiles. `node tools/live-browser-smoke.mjs` performs optional anonymous read-only collection. Packaging creates separate room and HA archives in `dist/`. See [the validation report](reports/VALIDATION.md) for recorded evidence and its limits. The [HA guide](ha/README.md) describes optional isolated tests against installed HA interfaces.

## Future work

The primary-source roadmap covers research, adapters and verification. O4 is a future managed-compute alternative. No source catalog engine or HA health bridge is implemented.
