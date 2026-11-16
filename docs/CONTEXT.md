# Project context

## Purpose

Situareness offers a browser room for monitoring public reporting and an independently operating Home Assistant integration for possible household weather alarms. New York City and Washington, DC are public examples that users can change. Private household settings belong outside public artifacts.

## Domain language

A **watched location** is an editable place of interest. A **household footprint** is a separately configured private point used by the Home Assistant policy. A coarse county association is useful for awareness but does not prove exposure. A **qualifying event** has credible current evidence, a concrete household consequence, and useful timely protective action. **Shadow mode** records intended decisions without calling output services.

## Operating model

The Chrome room is a read-only view and does not operate through browser exit or computer sleep. The separately installed Home Assistant integration collects NWS alerts without the room. The initial policy uses approved event and instruction rules, current alert status and times, and a matching private point. It does not automatically authorize an alarm for ordinary news or county proximity.

Both `live_enabled` and `commissioning_passed` default to false. When both are explicitly enabled after commissioning, a qualifying alert targets all configured phone services and speakers only at affected locations. Horn control, acknowledgement, and repeated reminders are not implemented. A service call is not proof of human receipt.

## Sources and configuration

The room has adapters for NWS, USGS `all_hour`, and BBC feeds. One-minute NWS and USGS and five-minute BBC intervals are polling targets, not delivery guarantees. USGS `all_hour` is post-event reporting, not early warning. The source catalog is research material, not runtime configuration. JSON keeps local configuration editable and portable without a new server or database. Room exports and Home Assistant settings may identify watched places or devices and must remain private.

## Current boundaries

The public examples do not contain household points, approved rules, or recipients. The room has no Home Assistant health bridge. Source catalog adapters, broader primary-source coverage, live commissioning, and the O4 managed-compute alternative are future work. See [the primary-source roadmap](plans/primary-source-roadmap.md) and [the continuation guide](plans/RESUME.md).
