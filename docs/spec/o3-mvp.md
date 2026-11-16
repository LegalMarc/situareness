# O3 implementation contract

## Architecture and privacy

The Chrome extension provides a read-only room; a separately configured Home Assistant integration monitors NWS independently. Public JSON examples contain New York City and Washington, DC only. Browser settings and exports include watched locations and are sensitive. Private JSON working files belong under `ignored-resources/private-config/` and must not enter release bundles or Git history.

## Room

Collect NWS active alerts, USGS `all_hour` earthquake reports, and BBC feeds using packaged adapters. NWS and USGS target one-minute polling and BBC five-minute polling, subject to provider, network, and browser scheduling delays. USGS reports are post-event, not earthquake early warning. Display source health, times, stale and failed states, and coarse location associations without implying a household impact. Preserve bounded collections, safe links, and validation. Room settings reside in Chrome storage; a changed JSON file requires import to update that storage.

The optional `room.context_dashboard` is a non-authoritative third-party display link, initially World Monitor. It is independent of the source collectors and never authorizes an alarm. Legacy `primary_dashboard` imports remain supported. Fresh current NWS items receive retention priority within bounded history; disabled, failed or overdue source data is visibly cached. All items have a seven-day collection-age bound. Global-cap history loss is disclosed separately from freshness and provider truncation, with a seven-day last-loss window and a reset when all previous source identities are removed. Disabled sources display neutral health and are excluded from enabled-source health rollups; an all-disabled collector is neutral. Startup collects overdue sources, and manual collection updates cadence. Bundled configuration failures produce an explicit room error.

## Home Assistant

Use current actual NWS evidence, a configured household point within supported geometry, an approved event and protective-instruction rule, and a valid action window for qualification. Unknown geometry, missing footprints, tests, cancellations and expired alerts cannot qualify. Reconcile updates and cancellation, deduplicate equivalent active lineage, persist pending targets, and recheck eligibility before delivery. First plans target all configured phones and only affected-location speakers. Both live and commissioning gates must be explicitly true before output calls; default to shadow. Equivalent inactive actions bridge at most 15 minutes; changed event/instruction invalidates earlier pending work. Cancellation follows the known lineage and stale reappearance stays blocked; a later qualifying update explicitly referencing the cancellation may begin a new action. Oversized lineages are quarantined with partial health while unrelated verified alerts continue; ambiguous quarantine suspends all lineages for that poll. Entry removal stops later saves before deleting the private journal. No horn adapter is implemented. Do not equate service acceptance with human receipt.

## Research and verification

`config/source-catalog.example.json` is a research catalog and is not consumed at runtime. The source skill can maintain a local catalog and propose supported room changes with validation; additional sources need adapters. Run offline checks, isolated browser tests and isolated actual Home Assistant tests as appropriate. Record exact results, dependencies, warnings, and untested physical behavior. Live commissioning is separate.
