# Continuation guide

## Current state

The project contains a Chrome room, an independent Home Assistant NWS integration, public NYC/DC examples, tests, packaging, and a source-research skill. HA defaults to shadow with both output gates false; public examples contain no private footprint, rules, or recipients. The room is not connected to HA health. Do not infer household deployment, real device delivery, or successful commissioning from local tests. Consult [validation](../reports/VALIDATION.md) for evidence rather than assuming a review or test was completed.

Start with the [supervisor handoff](HANDOFF.md) for the latest continuation state. `main` remains at `847d0e5`, which failed independent review. On `wip/supervisor-handoff-20261117`, all Claude Opus 5.5 findings through `aab5fb1` (`run_id`: `20261118T182230Z-b16dc5`, 0 Critical/High) — `"cancelled"` expiry outcomes/reasons in `_migrate_outbox_with_index` (`SIT-M1`), explicit fail-closed CAP-component retention trade-off in `docs/spec/o3-mvp.md` (`SIT-R01`), first-fit queueing after overflow in `_queue_outbox_plans` (`SIT-R02`), truthful `cancellation_uncertain`/`quarantined_count`/`partial` in `_stopped_health`/`_degraded_health` (`SIT-R03`), factored `outbox_overflow` notice + consolidated docs (`SIT-N1`), and pre-drain save clarification in `docs/CONTEXT.md` (`SIT-R04`) — are resolved and pending clean Opus `axes` + fresh `adversarial` reviews (`220` automated tests: `44` Node + `134` HA + `7` skill + `13` real HA + `22` Chromium Playwright; deterministic ZIPs `9d54a200...` / `065d3c81...`; live smoke `2026-11-18T18:33:43.120Z`). Keep household outputs disabled; no commissioning occurred.

## Read first

Read [the index](../INDEX.md), [context](../CONTEXT.md), [the current contract](../spec/o3-mvp.md), [the HA guide](../ha/README.md), and [the primary-source roadmap](primary-source-roadmap.md). The catalog at `config/source-catalog.example.json` is research data, not a runtime input. The local [source skill](../../skills/situareness-sources/SKILL.md) describes catalog research and supported configuration changes.

## Verification

From the project root:

```sh
npm ci
npx playwright install chromium
npm run check
npm run test:browser
python3 -W error -m unittest discover -s tests/ha -p 'test_*.py'
ruff check custom_components/situareness tests/ha tools/package.py
ruff format --check custom_components/situareness tests/ha tools/package.py
npm run package
```

The optional actual-HA tests require the isolated environment in [the HA guide](../ha/README.md); run `npm run test:ha:real` once it is prepared. Tests do not establish real device delivery. Keep `ignored-resources/private-config/room.json` and `ignored-resources/private-config/home-assistant.json` local; HA reads the latter only after it is copied privately to `<config>/situareness.json`.

## Remaining work

Prioritize the [primary-source roadmap](primary-source-roadmap.md): the catalog is not a source engine and unsupported feeds need adapters, validated contracts, and tests. Build an authenticated HA health bridge only with an appropriate design. Separately commission private footprints, rules, phone and speaker targets, and failure behavior before enabling either live gate. Horn control is not implemented. O4 managed compute is a future alternative. Do not claim an independent review was completed without its actual evidence.
