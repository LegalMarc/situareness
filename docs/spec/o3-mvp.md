# O3 implementation contract

## Architecture and privacy

The Chrome extension provides a read-only room; a separately configured Home Assistant integration monitors NWS independently. Public JSON examples contain New York City and Washington, DC only. Browser settings and exports include watched locations and are sensitive. Private JSON working files belong under `ignored-resources/private-config/` and must not enter release bundles or Git history.

## Room

Collect NWS active alerts, USGS `all_hour` earthquake reports, and BBC feeds using packaged adapters. NWS and USGS target one-minute polling and BBC five-minute polling, subject to provider, network, and browser scheduling delays. USGS reports are post-event, not earthquake early warning. Display source health, times, stale and failed states, and coarse location associations without implying a household impact. Preserve bounded collections, safe links, and validation. Room settings reside in Chrome storage; a changed JSON file requires import to update that storage.

The optional `room.context_dashboard` is a non-authoritative third-party display link, initially World Monitor. It is independent of the source collectors and never authorizes an alarm. Legacy `primary_dashboard` imports remain supported. Fresh current NWS items receive retention priority within bounded history; non-expired retained items from a disabled, failed, or overdue source carry a visible cached badge (`Cached · source unavailable`), including NWS items also marked `Not in latest results` (missing or unknown NWS lifecycle defaults to cached when unavailable, whereas `expired` renders only `Source expiry passed`). All items have a seven-day collection-age bound. Global-cap history loss is disclosed separately from freshness and provider truncation, with a seven-day last-loss window and a reset when all previous source identities are removed. Disabled sources display neutral health and are excluded from enabled-source health rollups; an all-disabled collector is neutral. Startup collects overdue sources, and manual collection updates cadence. Bundled configuration failures produce an explicit room error.

## Home Assistant

This section is the normative specification for the Home Assistant integration. See [CAP source evidence and policy](../reference/cap-cancellation.md) for primary-source rationale.

### Qualification and per-feature quarantine

- Collect active NWS alerts across configured states cleanly per poll; transient HTTP, timeout, or pagination failures fail the poll without clearing prior state or latching degraded mode.
- Qualify only current `Actual` NWS `Alert`/`Update` messages issued within the 7-day `MAX_ACCEPTANCE_AGE`, with complete CAP identity/reference tuples, strictly earlier referenced `sent` timestamps, `sent <= now + 5m`, valid action windows (`effective`/`onset`/`expires`/`ends`), a configured household point inside supported Polygon/MultiPolygon geometry, and an approved event and protective-instruction prefix rule.
- Reject unknown geometry, missing footprints, test messages, cancellations, and expired alerts from qualification.
- Isolate malformed, oversized, future-dated (`sent > now + 5m`), or conflicting-duplicate non-cancellation features in per-feature/per-lineage quarantine without failing unrelated valid alerts, preserving pending retries in suspension and preventing raw references from suppressing independent branches.
- When a malformed or oversized non-cancellation feature has an extractable NWS feature `id` (`https://api.weather.gov/alerts/...`), scope quarantine to `[feature_id, *valid_refs]` even when `properties` is non-object or a reference `@id` is invalid.
- Trigger poll-wide `quarantine_ambiguous: true` (suspending all lineages for that poll and raising `situareness_degraded`) only when a feature `id` cannot be safely extracted or unique quarantined IDs exceed 5,000 in one poll.
- Reconcile updates, deduplicate equivalent active lineage, persist state via private `Store(..., private=True)`, target all configured phones and only affected-location speakers, require explicit `live_enabled` and `commissioning_passed` gates (both defaulting to `false`), bridge equivalent inactive actions for at most 15 minutes, and invalidate prior pending targets on changed event or instruction.

### CAP cancellation and continuing segments

- Treat CAP references as directed evidence rather than whole-component cancellation authority. Do not infer cancellation scope from area names, VTEC equality, or overlapping UGCs.
- Keep explicitly cancelled records (including retained `state == "cancelled"` records whose `Cancel` aged out) blocked for `MAX_ACCEPTANCE_AGE` (7 days) before transitioning absent expired records to `ended_or_absent`.
- Isolate invalid or future-dated (`> +5m`) `Actual Cancel` records with recoverable targets in `uncertain_targets` without persisting raw `lineage` edges and without promoting them to authoritative cancellation when clocks advance.
- Quarantine unreferenced pre-cancellation uncertain records and suspend pending retries while current (`cancellation_uncertain`, `partial`); resolve absent uncertainty to `ended_or_absent` on clean polls (keeping existing suspended outbox items bounded by the 15-minute outbox window).
- For valid unreferenced continuing segments issued at or after a partial cancellation (`sent >= cancelled_at`), keep repeating pre-cancellation actions suspended in `quarantined` state while evaluating distinct new qualifying actions normally as `active`. Keep independent sibling branches eligible.

### Bounded storage and headroom

- Enforce caps of 1,000 stored records, 100 references per alert, 100 action fingerprints per record, 5,000 unique quarantined IDs per poll, and 5,000 outbox targets, retaining protected `Cancel`/tombstone components for 7 days from the latest component timestamp.
- Because the collector accepts up to 1,000 features per poll and retained tombstones occupy protected slots, large multi-state alert bursts combined with retained tombstones can reach the 1,000-record `cancellation_evidence_overflow` bound; overflow prioritizes active/current/`Cancel`/`cancelled` records and extends `degraded_until` to the latest `dropped_horizon`.
- When malformed, oversized, or conflicting `Actual Cancel` records have recoverable non-empty reference URLs within the 5,000-ID poll cap, quarantine only those targeted lineages and directed descendants (`cancellation_uncertain`, `partial`).

### Degraded states and `outbox_overflow`

- **Evidence/storage degraded modes (`evidence_degraded: true`, `output_blocked: true`):**
  - `cancellation_evidence_overflow`: Protected history exceeds 1,000 records (`degraded_until` at least 7 days and covers evicted `dropped_horizon`; `withheld_count` reports qualifying plans stripped on overflow).
  - `malformed_cancellation` / `conflicting_cancellation`: An `Actual Cancel` lacks recoverable target references or exceeds the 5,000-ID quarantine cap, or conflicting cancellation evidence cannot be scoped safely (`degraded_until` at least 7 days).
  - `journal_lost`: A previously initialized config entry's store goes missing (`persisted` is `None` or `{}`). Latch with stable `degraded_at` in `journal_lost_at` across pre-fetch failures, persist before fetching, set `degraded_until >= detect_now + MAX_ACCEPTANCE_AGE` (rotating stale `journal_lost_at` past 7 days and clearing `journal_lost_at` on post-fetch saves, non-empty store loads, or `malformed_store` entry so repeat losses get a full 7-day hold).
  - `malformed_store`: Persisted JSON fails decoding, major-version validation (`UnsupportedStorageVersionError`, `NotImplementedError`, or unparseable schema including `.corrupt.*` backups and persisted outboxes >5,000 items), or deep validation (`bool` checks on `initialized`/`was_live`, `degraded_reason` in allowed persisted reasons). Skip collection and writes to preserve disk data (`degraded_until: null`; mark `journal_initialized: true`; transient `OSError` raises `ConfigEntryNotReady` for retry).
- **Capacity mode (`outbox_overflow`, `evidence_degraded: false`, `output_blocked: false`, `partial: true`):**
  - When queued plus newly planned targets exceed 5,000, pre-drain one 100-target batch first if deliverable outbox items exist, then queue new whole plans atomically up to 5,000 targets and strip/withhold overflowing plans (`withheld_count`).
  - Set `degraded_reason: "outbox_overflow"` and `degraded_until = now + MAX_AGE` (15 minutes), continue bounded queued delivery (max 100 targets/poll, 30s deadline, saving once per 10-target delivery group and excluding `outbox_overflow` from `last_degraded_poll` age freezing), surface active `active_count` and accurate `deliverable_count`/`suspended_count`, and clear automatically on any poll where current plans fit within 5,000. Under the 100-target/poll, 15-minute `MAX_AGE` window, backlogs above ~1,500 targets can expire unsent.

### Recovery, notifications, and lifecycle

- Surface `cancellation_uncertain` truthfully on both degraded and healthy snapshots, exclude `events`, `last_success`, `degraded_at`, and `degraded_until` from recorder history, and report `withheld_count` alongside `planned_count`.
- Raise `situareness_degraded` once per reason on load and pre-fetch (qualified when running in shadow mode with live output disabled): name `.storage` manual repair/removal only when `degraded_reason == "malformed_store"`, name `outbox_overflow` continued delivery/auto-clear rules for overflow, and name `degraded_until` + `acknowledge_degraded_at` + reload for all other degraded reasons. Dismiss `situareness_degraded` on recovery, unload, or before deleting the store and `.corrupt.*` backups on entry removal.
- Clear evidence/journal degradations after `degraded_until` on a clean poll once triggers clear, or via one-shot non-future `acknowledge_degraded_at` evaluated at load (`degraded_at <= acknowledge_degraded_at <= load_now`). Reject future `acknowledge_degraded_at` timestamps in `config.validate(raw, now=None)` and consume any non-matching or premature `acknowledge_degraded_at` on load so stale configuration cannot clear a future unseen degradation.
- Recovering from `malformed_store` (repairing JSON, deleting store + `.corrupt.*` backups or replacing data with `{}` to enter `journal_lost`, or removing/re-adding the entry) or acknowledging `cancellation_evidence_overflow` early discards tombstones and can allow in-window alerts to re-evaluate. Withheld alerts and pre-degradation outbox retry budgets remain preserved without duplicating prior deliveries.
- Stop cancels in-flight fetches (`_stopped_health()` preserves non-degraded suspended counts without post-stop writes). No horn adapter exists; service acceptance is not proof of human receipt.

## Research and verification

`config/source-catalog.example.json` is a research catalog and is not consumed at runtime. The source skill can maintain a local catalog and propose supported room changes with validation; additional sources need adapters. Run offline checks, isolated browser tests and isolated actual Home Assistant tests as appropriate. Record exact results, dependencies, warnings, and untested physical behavior. Live commissioning is separate.
