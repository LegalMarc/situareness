# Continuation guide

## Current state

The project contains a Chrome room, an independent Home Assistant NWS integration, public NYC/DC examples, tests, packaging, and a source-research skill. HA defaults to shadow with both output gates false; public examples contain no private footprint, rules, or recipients. The room is not connected to HA health. Do not infer household deployment, real device delivery, or successful commissioning from local tests. Consult [validation](../reports/VALIDATION.md) for evidence rather than assuming a review or test was completed.

Start with the [supervisor handoff](HANDOFF.md) for the latest continuation state. `main` remains at `847d0e5`, which failed independent review. On `wip/supervisor-handoff-20261117`, all Claude Opus 5.5 findings through `b7fa712` (`run_id`: `20261118T190958Z-1d0ee5`, 0 Critical/High) were checkpointed in `5696a03`, and all seven high-effort Google-model findings on `5696a03` (`Gemini 4 Neon` standards: `STD-01..04`; `Gemini 4 Hydrogen` specification: `SPEC-01..03`) — `malformed_by_id` duplicate conflict isolation (`STD-01`), `uncertain_targets` recoverability parity in `_cancellation_analysis()` (`STD-02`), preserving pre-cancellation `action_history` on blocked/cancelled targets across polls (`SPEC-01`), passing `last_degraded_poll=None` and `pending_degraded` on `outbox_overflow` pre-drain `_save()` (`STD-03`), `api.weather.gov/alerts/` prefix + `references_complete` checks on `Actual Cancel` messages (`SPEC-02`), stripping shadow-era inactive predecessor actions on `activate=True` `outbox_overflow` (`SPEC-03`), and updating `docs/spec/o3-mvp.md` `"cancelled"` notification attribution (`STD-04`) — are resolved and verified (`227` automated tests: `44` Node + `141` `-W error` / `-X dev` HA with zero slow-callback warnings + `7` skill + `13` real HA + `22` Chromium Playwright). Fresh Google-model `standards`, `spec`, and blind `adversarial` reviews on the repaired immutable candidate remain pending (use Google-provided models in Antigravity; do not invoke external non-Google CLIs without explicit user confirmation). Keep household outputs disabled; no commissioning occurred.

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
