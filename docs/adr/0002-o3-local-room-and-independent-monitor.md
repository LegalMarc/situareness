# ADR 0002: Local room and independent monitor

## Status

Accepted for the current version; O4 remains future work.

## Decision

Use a packaged Chrome extension for the room and an independently installed Home Assistant integration for initial NWS monitoring. Use editable JSON and browser storage rather than adding a server or database. The public examples are New York City and Washington, DC, without household footprints or recipients.

The room targets one-minute NWS and USGS polling and five-minute BBC polling. USGS `all_hour` is post-event reporting, not earthquake early warning. Polling is not a latency or earliest-delivery guarantee. The Home Assistant integration starts in shadow mode and requires two explicit live gates after commissioning.

## Consequences

The browser collector stops when Chrome is closed or the computer sleeps. HA has separate configuration and source collection. There is no room-to-HA health bridge. A managed scheduled-compute alternative, O4, remains a future option.
