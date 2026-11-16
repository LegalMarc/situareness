# ADR 0001: Independent monitoring and conservative alarms

## Status

Accepted operating model for the current implementation.

## Decision

The room and the persistent monitor operate independently. A household alarm requires credible current evidence, a concrete watched-household consequence, and useful timely preparation or protection. Qualifying alarms may occur at any hour. The initial Home Assistant policy uses approved NWS rules and a matching private point; a news item or county association alone cannot qualify.

When explicitly commissioned and live gates are enabled, the first alert targets every configured phone, while speakers are limited to affected locations. The implementation does not control horns, invoke police or fire panic, or establish that a recipient heard a notification.

## Consequences

Private footprints, recipients, source rules, and commissioning are administrator responsibilities. Shadow operation is the default. Separate official alert channels remain necessary.
