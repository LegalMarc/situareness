# Continuation guide

## Current state

The project contains a Chrome room, an independent Home Assistant NWS integration, public NYC/DC examples, tests, packaging, and a source-research skill. HA defaults to shadow with both output gates false; public examples contain no private footprint, rules, or recipients. The room is not connected to HA health. Do not infer household deployment, real device delivery, or successful commissioning from local tests. Consult [validation](../reports/VALIDATION.md) for evidence rather than assuming a review or test was completed.

Start with the [supervisor handoff](HANDOFF.md) for the latest continuation state. `main` remains at `847d0e5`, which failed independent review. On `wip/supervisor-handoff-20261117`, Round 38 was checkpointed at `283d214` (where `Gemini 4 Hydrogen` high `specification` passed a third consecutive time), and all 9 unique findings from `283d214` (`Gemini 4 Neon` high standards `STD-01..03` and blind `Gemini 4 Neon` xhigh adversarial `ADV-01..07`) — durable `quarantine_cancel_lineages` tombstones (`ADV-01`), retained non-cancel conflict `uncertain_targets` (`ADV-02`), same-poll `bad_cancel_eids` disqualification on persisted `Cancel` collisions (`ADV-05`), arrival-order-invariant `refs_by_id`/`overflowed_ids` promotion (`ADV-04`), active sibling outbox migration (`ADV-03`), suspended-from-active retry age freezing (`STD-01`), preserved `SETUP_RETRY` listener across early retries + setup `CancelledError` cleanup (`STD-02`), preserving `outbox_overflow` across `quarantine_ambiguous` (`STD-03`/`ADV-06`), and `#dashboard-link` `target`/`href` hardening (`ADV-07`) — are resolved and verified (`242` automated tests: `44` Node + `156` `-W error` / `-X dev` HA with zero slow-callback warnings + `7` skill + `13` real HA + `22` Chromium Playwright). Roadmap **S0** initial implementation on `wip/s0-public-ci` (`35c62b8`) has an independent review pending 6 fixes (`S0-01..06`) after Round 39 release gates. Fresh `standards`, `spec`, and blind `adversarial` reviews on the Round 39 commit remain pending (use Google-provided models / internal access only once quota resets; never invoke external non-Google CLIs without explicit user confirmation). Keep household outputs disabled; no commissioning occurred.

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
