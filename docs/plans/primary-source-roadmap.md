# Primary-source roadmap and coding handoff

## Goal and priority

Make a local situation room that can discover authoritative warning channels for a new place, explain its coverage gaps, and obtain useful information with as little publication and collection delay as practical. Keep the browser optional for independent household monitoring. A public clone starts with New York City and Washington, DC examples. A user's actual configuration stays in `ignored-resources/` and browser-local storage.

The next work prioritizes primary data and reusable location configuration over more dashboards, visual effects, or an AI importance score. An official forecast or watch can provide preparation time before an incident exists. An earthquake event feed reports an event after detection. Neither is automatically an instruction to wake a household. Preserve separate awareness, preparation, and protective-action levels.

There is no defensible single guarantee of the earliest warning across every hazard. Prefer the issuing authority or its officially endorsed distribution channel, then measure the chosen transport. A vendor-operated channel can still carry a primary government message. Record the originator separately from the hosting company. News reporting and aggregators provide context and cross-checks, rather than authorizing household actuation.

## Decisions for the public baseline

- D1: O3 remains the architecture: packaged Chrome files plus independently running Home Assistant. No additional application server is required.
- D2: Use JSON for editable/importable configuration and source research. SQLite is unnecessary for the current settings volume and complicates browser portability and AI-assisted diffs. Reconsider it for a future incident-history store, independently of configuration.
- D3: Public files contain NYC/DC examples only. Personal settings, credentials, device enrollment, precise footprints, exports, backups and operational logs belong in `ignored-resources/` or the user's controller/browser storage. Exported settings can disclose watched places and are not automatically safe to share.
- D4: Prefer the NWS alert API and direct USGS GeoJSON feeds in the baseline. Poll at one-minute targets while execution is available. USGS's past-hour feed avoids waiting for the separate significance classification. Preserve source timestamps and source health. Poll targets are not delivery deadlines.
- D5: The companion skill maintains a local research catalog and proposes supported configuration changes. It does not supply alarm authority, run remote code, enroll accounts, or silently enable unsupported sources. The catalog is not yet a runtime input.
- D6: O4 remains a future addition: managed independent collection or an external watchdog. Do not introduce another live incident authority until durable cross-controller deduplication and ownership are designed.

## Current baseline and remaining gaps

Implemented: bundled NWS/USGS/BBC adapters, Chrome worker persistence and room reuse, configurable regional associations, source freshness and bounded retention, browser settings import/export, a source-research skill and catalog validator, and an independent NWS Home Assistant integration with conservative qualification and gated delivery.

Still required before reliance: authenticated household inventory, private exposure and rule configuration, actual phone/speaker commissioning, sustained shadow observation, automatic health notifications, acknowledgment and controlled repeats. The room currently has no authenticated Home Assistant health bridge. Zone-only weather warnings cannot qualify using the current point-and-polygon policy. Broader non-weather and international critical policies are not implemented.

## Source order and evidence

| Priority | Source/channel | Why investigate it | Required distinction |
| --- | --- | --- | --- |
| P1 | NWS CAP/GeoJSON API | Direct issuing-agency weather warnings, updates and cancellation semantics | API/cache/poll delay remains; an empty regional fetch is not an all-clear. |
| P1 | NWS NWWS Open Interface | Official Internet XMPP product stream worth comparing with API polling | Requires NWS credentials and a maintained connection. No account or latency advantage is assumed. |
| P1 | Official local emergency management | Evacuation, shelter-in-place, utilities and local civil emergencies may originate locally | Verify the actual authority and a usable channel; signup or HTML pages do not establish a public API. |
| P1 | Approved live IPAWS access or an evaluated authorized distributor | Potential national all-hazards coverage | Access conditions need verification. The public historical archive is delayed and must never be used as a live detector. |
| P2 | USGS real-time GeoJSON | Direct early event data, revisions and earthquake context | Occurrence time is not publication time; this is not ShakeAlert earthquake early warning. |
| P2 | NHC, tsunami centers and SPC | Primary forecasts, watches, warnings and preparation signals | Product class and issue cadence differ. Map each to its geographic and action semantics. |
| P2 | NOAA SWPC alert JSON | Primary space-weather notices | Separate observations, forecasts and terrestrial household consequences. Most notices must not ring an alarm. |
| P3 | Government-endorsed utility, transit and health channels | Direct operational consequences and preparations | An outage map, service advisory or statistical report can have a different publication delay and access contract. |
| Context | BBC, other reporting and aggregate dashboards | Breadth, explanation and corroboration | Do not present these as the original warning issuer or an automatically qualifying alarm source. |

Current source evidence, including broken or non-machine-readable routes, is in [primary-sources.md](../reference/primary-sources.md). Revalidate it when implementing an adapter.

## Work packages in order

### S0: Public configuration and handoff foundation

Scope: sample configurations, ignored local data, packaging, privacy checks, documentation and reproducible checks. Keep the private development history out of the public Git object graph. Publish only reviewed public files under the approved MIT license.

Acceptance: a fresh clone contains only NYC/DC examples; the packaged extension has no household enrollment or footprint; live gates are false; ignored private files cannot enter a normal commit or installation ZIP. Another coder can follow `docs/INDEX.md` and `docs/plans/RESUME.md` without access to personal data. Add a public CI privacy/build gate before expanding the adapter surface.

### S1: Versioned source registry and measured freshness

Scope: promote the research catalog into a separately versioned runtime contract, with a migration from the existing browser `sources` list. Preserve source role, issuing authority, official endorsement evidence, jurisdiction, hazard classes, transport, access requirements, and validation date. Keep unsupported entries disabled and visible as coverage gaps.

Record `event_origin_at`, `issued_at`, `source_updated_at`, `first_seen_at`, and `fetched_at` separately where available. Capture HTTP Date/Age/cache metadata and collection duration. Compute issuance-to-first-seen delay only when the timestamp meanings are established. Never substitute earthquake origin time for a publication measurement. Preserve clock-skew and unknown-data flags.

Files: a new catalog schema/validator under `config/` and `extension/lib/`, collector metadata, migrations and fixture tests. Reuse the companion research catalog's evidence fields rather than creating a second incompatible vocabulary.

Acceptance: a source can be authentic but stale, available but unsupported, or healthy with no current items. The UI explains each case. Tests cover old schema imports, disabled proposals, an unparseable source time, clock skew, HTTP cache age, partial fetches and retained stale data. Produce an observational latency report with sample period and limitations, rather than an earliest-source ranking based on assumptions.

### S2: Location setup and configuration tab

Scope: turn the current settings dialog into a location-oriented configuration view. Allow a user to import a local JSON file, choose a public locality, inspect authority/coverage evidence, and obtain a ready-to-run companion-skill prompt. Link to the exact versioned public skill. Show the difference between configured, researched, verified and actually monitored coverage.

A change of place must invalidate obsolete associations and flag uncovered hazards. Support multiple counties and official warning/evacuation zones. Keep identifier namespaces explicit: a Census county, a NWS forecast zone, a SAME code and a local evacuation zone are different things. Never infer a household footprint from the center of a town.

New source origins require an explicit browser-permission workflow. Investigate optional per-origin permissions requested by user gesture, instead of granting automatic access to every website. Keep executable adapters packaged locally. Catalog entries must not contain executable JavaScript or remote plugins.

Acceptance: changing NYC to another sample locality does not retain stale coverage claims or remove unrelated user locations. Import/export round-trips private settings locally without publishing them. Unknown sources remain proposals. Mock and browser tests cover denied host permission, removed sources, jurisdiction ambiguity, changed geographic codes and an unsupported local-government channel.

### S3: Fast official weather transport and zone proof

Scope: compare API collection with an optional NWWS-OI connection in Home Assistant. Obtain credentials only through an explicitly authorized enrollment. Parse WMO/AWIPS products using a tested adapter and maintain reconnection, backoff and gap recovery. Keep CAP/API collection as a reconciliation path rather than inventing semantic equivalence between formats.

Add official zone-geometry resolution with provenance and freshness before qualifying zone-only alerts. A household point must match the applicable official zone and reviewed event/action rule. County-level awareness must not become alarm exposure proof.

Acceptance: measured comparisons identify how many products arrived first on each route and account for missing messages. Replays prove updates, cancellations, reconnect gaps and cross-transport duplicates yield one incident lineage. Zone tests include boundary cases and changed zones. An unavailable optional stream degrades visibly and does not erase current incident state.

### S4: NYC/DC local-source tracer bullets

Scope: implement one complete, read-only local-authority adapter at a time. For NYC, resolve the currently advertised RSS route or obtain a documented supported alternative. For DC, verify whether an official machine-readable route exists beyond the public history and subscriber channel. Record unsupported access honestly, rather than scraping a guessed private endpoint.

Keep routine transit disruptions, missing-person notices, exercises and small isolated incidents in awareness channels. Civil-emergency qualification requires an authenticated/official current message, applicable geography, a household consequence and protective action. Do not assign alarm permission to the entire feed.

Acceptance: capture sanitized real-message fixtures, issuer evidence, access conditions, live read-only results and a failure case. A hypothetical emergency message must not qualify solely because the source is official. An exercise, expired notice and unrelated borough incident must not create household sound.

### S5: National/world primary adapters

Scope: evaluate actual live IPAWS access eligibility and redistribution conditions. In parallel, add NHC/tsunami/SPC/SWPC adapters as independent small changes with source-specific IDs, timestamps, lifecycle and geography. For countries outside the U.S., discover the national meteorological/civil-protection authority rather than treating a global news feed as the primary alert system.

Acceptance: each adapter has a documented issuing authority, supported transport, limits and freshness interpretation. An archived IPAWS response is rejected as a live source. National importance alone never creates household sound. Each proposed critical rule has positive and negative replay cases before it can enter commissioning.

### S6: Health, acknowledgment and commissioning

Scope: authenticated read-only HA health in the room; quiet maintenance notifications for a stale/dead collector; separate household acknowledgment; bounded repeats; explicitly scoped silencing; enrollment and output-stop behavior. Keep failure notices separate from the rare protective-action alarm.

Acceptance: test loss of a source, HA restart, disk/persistence failure, a missing phone, unavailable speakers and browser shutdown. Persist pending delivery before output and document at-least-once crash duplicates. Actual iPhone tests must cover locked screen, mute/Focus, Wi-Fi and cellular. Actual speakers/horns require coordinated audible tests and verified stop behavior. Service acceptance remains distinct from human receipt.

### S7: O4 independent watchdog or collector

Scope: evaluate managed scheduling, durable state, account/secret handling, platform quotas, cost and outages. First consider an external watchdog for O3. If O4 also collects and qualifies events, define a single incident owner or a tested cross-controller deduplication protocol. A household-side bridge is still required for local physical outputs.

Acceptance: simulate home power/Internet and HA loss while external detection remains available. Prove bounded, nonduplicated phone escalation and affected-site-only physical routing. Do not claim a free tier or deadline until measured against current provider terms and behavior.

## Coding and review operating plan

Use fast-tier workers for implementation in disjoint ownership areas: registry/collectors, room/configuration, and HA policy/delivery. The coordinating coder owns contracts, integration and this plan. Keep changes as vertical slices with a real source and a failure path, rather than accumulating partially connected adapters.

Before each slice, state its estimate and inspect progress. At twice the estimate, stop the action loop, preserve evidence and reassess. Use independent deep-tier standards/spec review and a fresh adversarial pass for non-small changes. Fix supported findings before calling a slice reviewed. A timed-out or quota-interrupted review is incomplete.

Commit and push an attributable, recoverable checkpoint after each verified slice and before a quota interruption. During longer work, aim for a documented checkpoint every 20–30 minutes. Use a draft branch/PR for incomplete work, state failing/skipped checks, and keep the resume note current. Stage explicit public paths and inspect the staged diff; never stage `ignored-resources/` or credentials. Record the immutable candidate SHA, exact test commands, reviewer metadata and remaining work.

The next coder should start with S1 after confirming S0's public validation and privacy report. Do not activate household sound while developing these work packages.
