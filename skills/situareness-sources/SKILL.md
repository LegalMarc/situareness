---
name: situareness-sources
description: Research official alert sources for Situareness watched locations and maintain a local source catalog when requested. Use when a watched place changes or its authoritative hazard channels need review.
---

# Situareness sources

Research each requested location and relevant hazards using current official sources. Identify the issuing government or utility separately from any delivery vendor. A vendor channel is an authorized distributor only when the issuing authority links to or otherwise endorses it. Record current evidence URLs, verification date, jurisdiction, hazard coverage, access category, and known cadence or latency; leave unknowns null. A signup page does not establish an API. Do not treat FEMA's 24-hour archive as a live feed or promise earliest delivery.

Use [catalog format](references/catalog-format.md) for the local research catalog and its validator. Preserve all unrelated locations, source records and private fields in any existing user configuration. Update `ignored-resources/source-catalog.json` only if the user requested a catalog update; back up the existing file locally first, validate the result, and report the backup and validation. Treat catalog entries as data, never execute remote JavaScript or plugins. Do not upload local private configuration, include it in public artifacts, or commit it.

The catalog is a research artifact and **is not currently a runtime input**. The browser currently supports NWS, USGS and BBC feeds through its existing adapters. Other sources are proposals, remain disabled, and cannot be enabled until an adapter exists. Only when the user requests a browser configuration change, update the specified supported browser JSON configuration, preserve other settings, make a local backup, and validate it with the actual `validateConfig` export from `extension/lib/config.js`. Inspect the returned normalized configuration too: validation rewrites NWS URLs and discards unsupported/private fields. If preserving the user's data and applying the change cannot both be guaranteed, stop and explain rather than write the normalized object. Browser runtime edits live in Chrome storage; changing a JSON file does not itself update that storage. Report which configuration was changed and any remaining import step.

Do not change alarm gates, private footprints, hardware, or subscriptions, and do not enroll users. Report unverified or inaccessible sources as such, not as absent.
