# Independent review record

The release gate is open until the current candidate has zero supported unresolved findings on standards, specification, and fresh adversarial review. Interrupted attempts are not approvals. Public records omit private paths and local raw logs.

## Candidates and reviewers

| Candidate | Scope | Reviewer | Result |
| --- | --- | --- | --- |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Public privacy and clean history | Claude Opus 5.5, medium effort | PASS, zero findings |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Standards | Claude Opus 5.5, medium effort | Seven findings; repaired in next checkpoint |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Specification | Claude Opus 5.5, medium effort | Seven findings; repaired in next checkpoint |
| `2c0f1e1864d1738e5c5488d3c0e423c0f0a7ebee` | Standards | Claude Opus 5.5, medium effort | Ten findings; repaired in the next checkpoint |
| `2c0f1e1864d1738e5c5488d3c0e423c0f0a7ebee` | Specification | Claude Opus 5.5, medium effort | Twelve findings; repaired in the next checkpoint |
| `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` | Standards | Claude Opus 5.5, medium effort | Ten findings; repaired on WIP branch |
| `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` | Specification | Claude Opus 5.5, medium effort | Nine findings; repaired on WIP branch |
| `63da80f6660667a529a3c4e0d1a0b7bc368760b5` | Focused browser/package | OpenAI `gpt-6-astra`, ultra | One P2 finding (`BROWSE-01`); repaired in `5ec38ac` |
| `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a` | Standards | Claude Opus 5.5, medium effort | Seven findings (`run_id`: `20261117T164428Z-8b628a`, 260.4s); repaired in `e38a7fd` |
| `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a` | Specification | Claude Opus 5.5, medium effort | Twelve findings (`run_id`: `20261117T164428Z-8b628a`, 225.2s); repaired in `e38a7fd` |
| `e38a7fdd88ff4877bf2969bad2658c5025ed583d` | Standards | Claude Opus 5.5, medium effort | Ten findings (`run_id`: `20261117T171412Z-dfb683`, 214.2s; zero browser/packaging defects); repaired in `83f328c` |
| `e38a7fdd88ff4877bf2969bad2658c5025ed583d` | Specification | Claude Opus 5.5, medium effort | Eight findings (`run_id`: `20261117T171412Z-dfb683`, 204.1s; zero browser/packaging defects); repaired in `83f328c` |
| `83f328c518f4f9c5b87903b5ef56317127a94ae8` | Standards | Claude Opus 5.5, medium effort | Six findings (`run_id`: `20261117T173308Z-a2a286`, 260.9s; zero browser/packaging defects); repaired for next candidate |
| `83f328c518f4f9c5b87903b5ef56317127a94ae8` | Specification | Claude Opus 5.5, medium effort | Five findings (`run_id`: `20261117T173308Z-a2a286`, 267.0s; zero browser/packaging defects); repaired for next candidate |

The exact model reported by completed CLI result metadata was `claude-opus-5-5`. The second standards/specification passes took 204.4 and 205.3 seconds respectively. They independently read an immutable full-source snapshot, complete change diff from the public root, documented contract/standards, and raw local test evidence. They executed no code or physical output.

## Standards findings at 2c0f1e1

Codes preserve the standards reviewer's separate axis. Repairs are implemented and locally tested; all remain open pending independent re-review.

| Code | Severity | Finding |
| --- | --- | --- |
| STD-HA-01 | Medium | Inactive equivalent-action history can suppress renewed exposure indefinitely. |
| STD-HA-02 | Low | Ancestor cancellation can leave a descendant retry suspended. |
| STD-HA-03 | Low | Entry removal can race an in-flight save and recreate the private store. |
| STD-HA-04 | Low | One oversized feature or lineage can stop unrelated warning decisions. |
| STD-BR-01 | Medium | The storage-cap warning becomes permanent during ordinary use. |
| STD-BR-02 | Low | A bundled-default load failure leaves the room connecting indefinitely. |
| STD-BR-03 | Low | Explicit context-dashboard null loses to a legacy key. |
| STD-BR-04 | Nit | A configurable dashboard URL retains a fixed World Monitor label. |
| STD-BR-05 | Nit | Startup no longer immediately collects overdue sources. |
| STD-HA-05 | Nit | Pending health does not distinguish suspended work. |

## Specification findings at 2c0f1e1

Codes preserve the specification reviewer's separate axis. Repairs are implemented and locally tested; all remain open pending independent re-review.

| Code | Severity | Finding |
| --- | --- | --- |
| SPEC-HA-01 | Medium | Root-only references can cause duplicate critical plans and retries. |
| SPEC-HA-02 | Medium | A cancellation can miss work migrated to a successor. |
| SPEC-HA-03 | Low | A changed unapproved action retains an old pending action. |
| SPEC-HA-04 | Low | One oversized alert stops all monitoring in the configured states. |
| SPEC-HA-05 | Low | A migrated retry keeps the predecessor's source link. |
| SPEC-HA-06 | Nit | Repeated outbox/event scans can block the event loop at documented bounds. |
| SPEC-HA-07 | Nit | The deduplication description no longer matches inactive-history handling. |
| SPEC-RM-01 | Medium | Global retention loss is permanently mixed into the freshness banner. |
| SPEC-RM-02 | Low | Context-link labeling and explicit-null precedence are misleading. |
| SPEC-RM-03 | Low | Disabled or failed NWS cached items can appear current indefinitely. |
| SPEC-RM-04 | Low | An all-disabled room appears healthy and busy. |
| SPEC-RM-05 | Nit | Manual/install refreshes do not reset collection cadence. |

## Third candidate findings

Candidate `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` passed 93 local automated tests, but independent Opus 5.5 medium-effort reviews found the following. Workers were interrupted by account usage limits; partial repairs and preliminary primary-source captures are preserved in the WIP handoff, with supported findings still open. This is not release approval. Previous narratives were deliberately omitted from the review packets, while executable code, contracts, tests and standards were included.

### Standards

| Code | Severity | Finding |
| --- | --- | --- |
| SR-01 | Medium-high | Long quarantine can erase delivered-action history and cause duplicate alarms. |
| SR-02 | Low | Quarantined/unconfirmed states fail to resolve and can revive legacy history. |
| SR-03 | Low-medium | Reload can discard acceptance records for in-flight delivery. |
| SR-04 | Low | Carried retry items are not deduplicated against each other after a merge. |
| SR-05 | Low | The journal cap can evict a current record and cause persistent refresh failure. |
| SR-06 | Low | Backward clock correction can stall Chrome alarm collection. |
| SR-07 | Low | Whole-component cancellation may stop a continuing sibling segment; source semantics need verification. |
| SR-08 | Low | The HA guide contradicts itself about partial collections. |
| SR-09 | Nit | Retention priority ignores source freshness. |
| SR-10 | Nit | Dashboard setting instructions and UI label drift. |

### Specification

| Code | Severity | Finding |
| --- | --- | --- |
| SPEC-01 | Medium | Quarantine can discard a cancellation tombstone. |
| SPEC-02 | Low | Legacy journal migration can lose or misapply action history. |
| SPEC-03 | Low | The journal cap can evict current records and cancellation evidence. |
| SPEC-04 | Low | Reload can duplicate in-flight deliveries. |
| SPEC-05 | Low | Room retention priority ignores freshness. |
| SPEC-06 | Low | Worker-side bundled-configuration failure is not identified clearly. |
| SPEC-07 | Nit | New neutral/disabled/cached classes lack distinct visual styles. |
| SPEC-08 | Nit | Dashboard documentation label differs from the UI. |
| SPEC-09 | Nit | A helper assumes an array without validating it. |

## Evidence limits

Candidate `2c0f1e1` passed 79 automated tests and `847d0e5` passed 93, plus live anonymous browser reads and deterministic packaging, before their respective findings were discovered. These results do not describe the newer failing WIP. Those successes did not cover the reported triggers. Home Assistant source and delivery targets were simulated. The live smoke returned no NWS alerts, so it cannot validate real CAP lineage. Physical commissioning, broader primary-source adapters, automatic health escalation and the browser-to-HA health bridge remain separate work.

## Supervisor continuation findings

Candidate `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a` passed 128 local tests, but independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T164428Z-8b628a`; 260.4s standards, 225.2s specification) failed with seven standards and twelve specification findings. Prior focused browser review at `63da80f6660667a529a3c4e0d1a0b7bc368760b5` ([BROWSE-01](browser-focused-63da80f.md)) and earlier internal checks (`CAP-SCOPE-01`, `CAP-RENEW-01`, `CAP-STORE-01`, `CAP-ID-01`) are preserved in history.

### Standards findings at fcc9072

| Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- |
| HA-01 | High | Unbounded cancellation protection eventually triggers permanent `CancellationEvidenceOverflow` shutdown. | Enforced 7-day `MAX_ACCEPTANCE_AGE` and anchored `cancellation_horizon`; re-review pending. |
| HA-02 | Medium | `seen_cancel` turns unrelated or transient fetch errors into permanent `CancellationEvidenceLost`. | Removed `seen_cancel` / `CancellationEvidenceLost` and kept malformed-cancel scoping bounded; re-review pending. |
| HA-03 | Medium | Coordinator retry filter restricts the entire component instead of uncertain records. | Removed component-wide filter while keeping `"cancelled"` drop and `"quarantined"` retry suspension; re-review pending. |
| HA-04 | Low | `CancelledError` is swallowed after seeing a Cancel and latches degraded mode on unload/shutdown. | Let `asyncio.CancelledError` propagate untouched; re-review pending. |
| HA-05 | Low | Degraded health misreports `quarantine_ambiguous` and `cancellation_uncertain` regardless of cause. | Added `degraded_reason`/`degraded_at` and accurate diagnostic flags; re-review pending. |
| HA-06 | Low | Superseded cancellation-group records force `prior_state: "active"`, and long non-Cancel features fail the whole poll. | Removed forged `prior_state`; quarantined oversized/malformed non-Cancel features per feature/lineage; re-review pending. |
| DOC-01 | Nit | `tests/fixtures/cap/**` omitted from `docs/INDEX.md` coverage. | Added `covers: tests/fixtures/cap/**` on the `cap-cancellation.md` entry. |

### Specification findings at fcc9072

| Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- |
| SIT-H1 | High | Historic cancellation uncertainty sets poll-wide `quarantined = True` and stalls resolution indefinitely. | Scoped unconfirmed/quarantined resolution per group and active/current-cancel presence; re-review pending. |
| SIT-H2 | High | Cancellation evidence has no retention horizon and deterministically hits the 1,000-record cap. | Added 7-day `MAX_ACCEPTANCE_AGE` and source-anchored `cancellation_horizon` expiry; re-review pending. |
| SIT-H3 | High | Transient or unrelated fetch errors after observing a Cancel permanently latch degraded state. | Removed `CancellationEvidenceLost` fetch-error latching; re-review pending. |
| SIT-M1 | Medium | `CancelledError` is swallowed and writes a degraded latch during unload/shutdown. | Propagates `asyncio.CancelledError` untouched; re-review pending. |
| SIT-M2 | Medium | Degraded mode stops collection and lacks an authorized recovery path. | Continues collection while output-blocked for uncorrupted degradation; recovers via 7-day `degraded_until` or `acknowledge_degraded_at`; re-review pending. |
| SIT-M3 | Medium | Continuing descendant retry is blocked by an unrelated Cancel in the same component. | Removed component-wide outbox filter so uncancelled siblings/descendants migrate cleanly; re-review pending. |
| SIT-M4 | Medium | Single malformed non-Cancel feature fails the entire poll. | Quarantines malformed/oversized non-Cancel features per feature/lineage in `collector.py`; re-review pending. |
| SIT-M5 | Medium | Nested malformed persisted journal entries crash every poll instead of latching `malformed_store`. | Added `_valid_persisted_store` deep schema validation; re-review pending. |
| SIT-M6 | Medium | `_degraded_health()` reports invented `partial`/`quarantine_ambiguous`/`cancellation_uncertain` values. | Reports actual collected counts/events and cause-accurate flags; re-review pending. |
| SIT-L1 | Low | Worker bundled-config errors render as collector disconnect and `runAction` regex omits them. | Added `isBundledConfigError`, schema bootstrap check, and `runAction` regex fix; re-review pending. |
| SIT-L2 | Low | Disabled/failed/overdue USGS and BBC items lack visible cached badges, drifting from `o3-mvp.md`. | Extended `"cached"` badge to non-weather items when `sourceStates` is unavailable/overdue and updated `docs/setup.md`; re-review pending. |
| SIT-N1 | Nit | Superseded records in cancellation groups hardcode `prior_state: "active"`. | Removed the hardcode and guarded `referenced` updates; re-review pending. |

### Candidate e38a7fd Opus review findings

Candidate `e38a7fdd88ff4877bf2969bad2658c5025ed583d` passed 141 local tests and had zero supported defects in the browser room, UI, packaging, and source skill. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T171412Z-dfb683`; 214.2s standards, 204.1s specification) reported ten standards and eight specification findings in Home Assistant and HA documentation:

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-H1 | High | Alerts first qualifying while degraded mark `actions` and fail to deliver after recovery. | Strip withheld plan fingerprints from `actions` while degraded; re-review pending. |
| Standards / Spec | SIT-M2, SIT-M3 / SIT-R1 | High / Medium | `acknowledge_degraded_at` accepts future timestamps, can be reused, and clears `malformed_store` or `degraded_at=None` legacies. | Enforced one-shot `degraded_at <= ack <= now`, backfilled `degraded_at` for legacy degraded stores, and kept `malformed_store` unacknowledged until store repair/replacement; re-review pending. |
| Spec | SIT-R2 | High | Normalized `Actual Cancel` with no recoverable references avoids `malformed_cancellation`. | Trigger `malformed_cancellation` for normalized `Actual Cancel` with empty `references`; re-review pending. |
| Spec | SIT-R3 | High | Update valid in collector but rejected against journal in `reconcile` still hides predecessor `P`. | Added `resolve_candidates` in `domain.py` and coordinator so rejected Updates restore valid predecessors; re-review pending. |
| Standards / Spec | SIT-M1 / SIT-R4 | Medium | Upgrading legacy Cancel records or replaying Cancel with `cap_references_valid=False` latches false `conflicting_cancellation`. | Normalized incoming `cap_references` and lineage matching, and treated pre-upgrade records lacking `cancel_message` as legacy uncertainty; re-review pending. |
| Standards / Spec | SIT-L1 / SIT-R5 | Low | `degraded_at` keeps only the earliest trigger timestamp when re-triggered. | Always update `degraded_at` and `degraded_until` on each active trigger; re-review pending. |
| Standards / Spec | SIT-L4 / SIT-R6 | Low | Deep store validation omits outbox `location`/`created` and record `updated`/`inactive_since`/`cancel_message` checks. | Completed `_valid_persisted_store` validation across all dereferenced fields; re-review pending. |
| Standards / Spec | SIT-L2, SIT-L3 / SIT-R7 | Low | `cancellation_uncertain` persists on resolved outbox items, `_degraded_health()` keeps `quarantine_ambiguous=True` across clean polls, and docs misstate `malformed_cancellation` triggers. | Scoped `cancellation_uncertain` and `quarantine_ambiguous` to active/current-poll evidence and synchronized docs; re-review pending. |
| Standards / Spec | SIT-N1 / SIT-R8 | Nit | Dead `_store_recovered` attribute. | Removed `_store_recovered`; re-review pending. |
| Standards | SIT-N2 | Nit | Documented `degraded_until` missing from sensor attributes. | Exposed `degraded_until` on normal and degraded sensor health; re-review pending. |

### Candidate 83f328c Opus review findings

Candidate `83f328c518f4f9c5b87903b5ef56317127a94ae8` passed 143 local tests and had zero supported defects in the browser room, UI, packaging, and catalog validator. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T173308Z-a2a286`; 260.9s standards, 267.0s specification) reported six standards and five specification findings in Home Assistant and HA documentation:

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-H1 | High | Suspended quarantined retry collides in `_outbox_signature` with an independent sibling in the same group. | Key quarantined outbox items separately by `incident_id` in `_outbox_signature`; re-review pending. |
| Standards / Spec | SIT-H2 / SR-M1 | High / Medium | Conflicting `Cancel` overwrites prior `C -> T1` evidence, allowing `T1` replay after recovery. | Preserved prior `cap_identity`/`cap_references`/`cancel_message`/`lineage` on `conflicting_prior_cancel` while quarantining conflicting references; re-review pending. |
| Standards / Spec | SIT-M1 / SR-H1 | Medium / High | Newly qualifying sibling alerts and `CancellationEvidenceOverflow` polls fail to clear withheld `actions`. | Pop `(group, fp)` from `records` on `now` across all siblings and before raising `CancellationEvidenceOverflow`; re-review pending. |
| Standards | SIT-M2 | Medium | Undelivered pre-degradation outbox items expire past `MAX_AGE` during >15m degradation. | Preserved active retry budget across degradation via `last_degraded_poll` and `degraded_delta` migration without duplicating sent targets; re-review pending. |
| Spec | SR-M2 | Medium | Conflicting duplicate feature in `collector.py` fails the entire poll via `ValueError`. | Quarantined conflicting duplicate features per feature/lineage (and set `conflicting_cancellation` for duplicate Cancels); re-review pending. |
| Standards | SIT-L1 | Low | Docs overstate what `acknowledge_degraded_at` clears while an active trigger persists. | Clarified in `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md` that ongoing triggers refresh `degraded_at`/`degraded_until`; re-review pending. |
| Standards / Spec | SIT-L2 / SR-L1 | Low | Deep store validation misses unhashable `prior_state`/`action_identity`/`fingerprint`/`action_fingerprint`/`action_affected` and outbox payload fields. | Completed `_valid_persisted_store` validation across all record and outbox fields; re-review pending. |
| Spec | SR-L2 | Low | `malformed_store` reports `degraded_at: null` and `degraded_until: null`. | Populated `degraded_at` and `degraded_until` from detection time while keeping `malformed_store` latched until store repair/replacement; re-review pending. |

All findings from `fcc9072`, `e38a7fd`, and `83f328c` are repaired and pass 146 local automated tests, Ruff, deterministic packaging, and live anonymous smoke. Independent Claude Opus 5.5 (`standards`, `spec`, and fresh `adversarial`) reviews on the repaired immutable candidate remain required before release approval.
