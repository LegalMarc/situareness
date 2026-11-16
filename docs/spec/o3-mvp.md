# O3 implementation contract

## Architecture and privacy

The Chrome extension provides a read-only room; a separately configured Home Assistant integration monitors NWS independently. Public JSON examples contain New York City and Washington, DC only. Browser settings and exports include watched locations and are sensitive. Private JSON working files belong under `ignored-resources/private-config/` and must not enter release bundles or Git history.

## Room

Collect NWS active alerts, USGS `all_hour` earthquake reports, and BBC feeds using packaged adapters. NWS and USGS target one-minute polling and BBC five-minute polling, subject to provider, network, and browser scheduling delays. USGS reports are post-event, not earthquake early warning. Display source health, times, stale and failed states, and coarse location associations without implying a household impact. Preserve bounded collections, safe links, and validation. Room settings reside in Chrome storage; a changed JSON file requires import to update that storage.

## Home Assistant

Use current actual NWS evidence, a configured household point within supported geometry, an approved event and protective-instruction rule, and a valid action window for qualification. Unknown geometry, missing footprints, tests, cancellations and expired alerts cannot qualify. Reconcile updates and cancellation, deduplicate equivalent active lineage, persist pending targets, and recheck eligibility before delivery. First plans target all configured phones and only affected-location speakers. Both live and commissioning gates must be explicitly true before output calls; default to shadow. No horn adapter is implemented. Do not equate service acceptance with human receipt.

## Research and verification

`config/source-catalog.example.json` is a research catalog and is not consumed at runtime. The source skill can maintain a local catalog and propose supported room changes with validation; additional sources need adapters. Run offline checks, isolated browser tests and isolated actual Home Assistant tests as appropriate. Record exact results, dependencies, warnings, and untested physical behavior. Live commissioning is separate.
