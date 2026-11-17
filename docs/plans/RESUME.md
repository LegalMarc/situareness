# Continuation guide

## Current state

The project contains a Chrome room, an independent Home Assistant NWS integration, public NYC/DC examples, tests, packaging, and a source-research skill. HA defaults to shadow with both output gates false; public examples contain no private footprint, rules, or recipients. The room is not connected to HA health. Do not infer household deployment, real device delivery, or successful commissioning from local tests. Consult [validation](../reports/VALIDATION.md) for evidence rather than assuming a review or test was completed.

Start with the [supervisor handoff](HANDOFF.md) for the latest continuation state. Public `main` is at `847d0e5`: 93 automated tests passed there, but independent standards/specification review failed. The newer `wip/supervisor-handoff-20261117` checkpoint preserves interrupted fixes and is not ready to merge. At handoff its 38 Node tests and static checks passed; one of 33 HA tests and formatting of two Python files failed. A new JavaScript module is missing from the installation allowlist. CAP sibling/cancellation semantics remain an evidence-dependent design question. Do not apply old green logs to this WIP.

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
