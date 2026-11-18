# Continuation guide

## Current state

The project contains a Chrome room, an independent Home Assistant NWS integration, public NYC/DC examples, tests, packaging, and a source-research skill. HA defaults to shadow with both output gates false; public examples contain no private footprint, rules, or recipients. The room is not connected to HA health. Do not infer household deployment, real device delivery, or successful commissioning from local tests. Consult [validation](../reports/VALIDATION.md) for evidence rather than assuming a review or test was completed.

Start with the [supervisor handoff](HANDOFF.md) for the latest continuation state. `main` remains at `847d0e5`, which failed independent review. On `wip/supervisor-handoff-20261117`, all Claude Opus 5.5 findings through `bd617e2` (`run_id`: `20261118T022802Z-e54306`, 0 Critical/High/Medium) — including `asyncio.to_thread` per-page parse/normalize offload in `collector.py`, cause-accurate `expired_unsent_reasons` notifications, `_stopping` pre-save guards + stop-before-platform-unload + abandoned-setup notification dismissal, rank-ordered evidence `degraded_at` stability, empty-`new_items` overflow exclusion, extension dead-code/`interval_minutes` fixes, and `docs/CONTEXT.md`/spec/README readability updates — are repaired and pending clean Opus `axes` + fresh `adversarial` reviews (`205` automated tests: `44` Node + `121` HA + `7` skill + `12` real HA + `21` Chromium Playwright; deterministic ZIPs `5434a239...` / `67cbfdde...`; live smoke `2026-11-18T02:51:50.962Z`). Keep household outputs disabled; no commissioning occurred.

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
