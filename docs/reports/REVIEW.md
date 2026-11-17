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
| `83f328c518f4f9c5b87903b5ef56317127a94ae8` | Standards | Claude Opus 5.5, medium effort | Six findings (`run_id`: `20261117T173308Z-a2a286`, 260.9s; zero browser/packaging defects); repaired in `64b6fa0` |
| `83f328c518f4f9c5b87903b5ef56317127a94ae8` | Specification | Claude Opus 5.5, medium effort | Five findings (`run_id`: `20261117T173308Z-a2a286`, 267.0s; zero browser/packaging defects); repaired in `64b6fa0` |
| `64b6fa03ae148cd5964e23e7c1d1420c020175b2` | Standards | Claude Opus 5.5, medium effort | Three findings (0 High, 1 Medium, 2 Low; `run_id`: `20261117T174809Z-251d8a`, 384.8s; zero browser/packaging/catalog defects); repaired in `9308033` |
| `64b6fa03ae148cd5964e23e7c1d1420c020175b2` | Specification | Claude Opus 5.5, medium effort | Four findings (0 High, 1 Medium, 3 Low; `run_id`: `20261117T174809Z-251d8a`, 308.0s; zero HA-01/packaging defects); repaired in `9308033` |
| `930803369829a761cfd4593d4db3f153b8c13d64` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 4 Low, 2 Nit; `run_id`: `20261117T180834Z-0e141a`, 348.0s); repaired in `120c3c4` |
| `930803369829a761cfd4593d4db3f153b8c13d64` | Specification | Claude Opus 5.5, medium effort | Six findings (0 High, 1 Medium, 2 Low, 3 Nit; `run_id`: `20261117T180834Z-0e141a`, 394.4s); repaired in `120c3c4` |
| `120c3c4362ff529a62f3e43e59ff10a8b3c02ec2` | Standards | Claude Opus 5.5, medium effort | Four actionable findings + one non-blocking nit (0 Critical, 0 High, 1 Medium, 2 Low, 1+1 Nit; `run_id`: `20261117T184436Z-6d91c1`, 260.7s; zero browser/packaging/catalog defects); repaired in `f0e8a08` |
| `120c3c4362ff529a62f3e43e59ff10a8b3c02ec2` | Specification | Claude Opus 5.5, medium effort | Three findings (0 High, 0 Medium, 3 Low; `run_id`: `20261117T184436Z-6d91c1`, 244.0s; zero browser/packaging/catalog defects); repaired in `f0e8a08` |
| `f0e8a08eb8f09585666b3ba5b2f966e57cc65a25` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 1 High, 0 Medium, 1 Low, 2 Nit; `run_id`: `20261117T190130Z-35fadb`, 311.6s; zero browser/packaging/catalog defects); repaired in `a146710` |
| `f0e8a08eb8f09585666b3ba5b2f966e57cc65a25` | Specification | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 2 Low, 4 Nit; `run_id`: `20261117T190130Z-35fadb`, 283.6s; zero browser/packaging/catalog defects); repaired in `a146710` |
| `a1467104017f1efad31661370dbd19a4f37189ee` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 0 Medium, 2 Low, 2 Nit; `run_id`: `20261117T192723Z-402b20`, 307.7s; zero browser/packaging/catalog/CAP/gate defects); repaired in `c0a909c` |
| `a1467104017f1efad31661370dbd19a4f37189ee` | Specification | Claude Opus 5.5, medium effort | Six findings (0 Critical, 0 High, 1 Medium, 2 Low, 3 Nit; `run_id`: `20261117T192723Z-402b20`, 340.1s; zero browser/packaging/catalog/room defects); repaired in `c0a909c` |
| `c0a909c3309f1fc9f88ec967d6765df977ed8ca2` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 2 Low, 4 Nit; `run_id`: `20261117T194649Z-7a1803`, 329.5s; zero browser/packaging/catalog/output-gate defects); repaired in `221ed9b` |
| `c0a909c3309f1fc9f88ec967d6765df977ed8ca2` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 2 Medium, 1 Low, 0 Nit; `run_id`: `20261117T194649Z-7a1803`, 390.8s; zero browser/UI/packaging/catalog defects); repaired in `221ed9b` |
| `221ed9b037ea72e826f88716e14826c28e95a3df` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 4 Low, 2 Nit; `run_id`: `20261117T203507Z-d741fd`, 316.3s; zero CAP/browser/packaging/catalog/gate defects); repaired in `ad93ead` |
| `221ed9b037ea72e826f88716e14826c28e95a3df` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261117T203507Z-d741fd`, 287.4s; zero CAP/browser/UI/packaging/catalog defects); repaired in `ad93ead` |
| `ad93eada5a9222fe3120707180b24c2704dc5e7c` | Standards | Claude Opus 5.5, medium effort | Five findings (0 Critical, 0 High, 1 Medium, 2 Low, 2 Nit; `run_id`: `20261117T214931Z-ca8e85`, 318.6s; zero CAP/browser/packaging/catalog/quarantine defects); repaired in `3d18093` |
| `ad93eada5a9222fe3120707180b24c2704dc5e7c` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 1 Low-Medium, 1 Low; `run_id`: `20261117T214931Z-ca8e85`, 291.6s; zero CAP/qualification/quarantine/lifecycle/room/catalog defects); repaired in `3d18093` |
| `3d1809327eafc2bb09c88ef104622e9eacb4b7cc` | Standards | Claude Opus 5.5, medium effort | Six findings (0 Critical, 0 High, 0 Medium, 3 Low, 3 Nit; `run_id`: `20261117T221552Z-4d6117`, 309.4s; zero browser/packaging/catalog/gate defects); repaired in `6236ea8` |
| `3d1809327eafc2bb09c88ef104622e9eacb4b7cc` | Specification | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 0 Medium, 2 Low, 0 Nit + 1 capacity advisory; `run_id`: `20261117T221552Z-4d6117`, 308.7s; zero room/CAP/quarantine/outbox/lifecycle defects); repaired in `6236ea8` |
| `6236ea8f7e47aed3a8d8be0966f77baf8af1b2e7` | Standards | Claude Opus 5.5, medium effort | Five findings (0 Critical, 0 High, 1 Medium, 3 Low, 1 Nit; `run_id`: `20261117T223104Z-7fe723`, 215.8s; zero browser/packaging/catalog/gate/overflow defects); repaired in `c81fb7f` |
| `6236ea8f7e47aed3a8d8be0966f77baf8af1b2e7` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 1 Low, 1 Nit; `run_id`: `20261117T223104Z-7fe723`, 202.2s; zero room/gate/quarantine/store/overflow defects); repaired in `c81fb7f` |
| `c81fb7f5221b54a88453627dd5376216db0051b9` | Standards | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 1 Medium, 1 Low, 0 Nit; `run_id`: `20261117T224454Z-a299b9`, 217.6s; zero core-safety/store/persistence/concurrency/gate/extension/attribute-list defects); repaired in next candidate |
| `c81fb7f5221b54a88453627dd5376216db0051b9` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261117T224454Z-a299b9`, 373.9s; zero room/catalog/quarantine/overflow/store/lifecycle defects); repaired in next candidate |

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

All findings from `fcc9072`, `e38a7fd`, and `83f328c` were repaired in `64b6fa0`.

### Candidate 64b6fa0 Opus review findings

Candidate `64b6fa03ae148cd5964e23e7c1d1420c020175b2` passed 146 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 High findings** and zero packaging or catalog defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T174809Z-251d8a`; 384.8s standards, 308.0s specification) reported 1 Medium + 2 Low standards findings and 1 Medium + 3 Low specification findings (6 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | SPEC-01 | Medium | Missing/empty persisted store on an already-initialized config entry silently resets history without latching `journal_lost`. | Added `entry.data["journal_initialized"]` detection latching `journal_lost` with output withheld and read-only collection preserved; re-review pending. |
| Standards | SIT-REV-M1 | Medium | Overflow drops `state == "cancelled"` records before non-cancel protected items and computes `degraded_until` without dropped-component horizons. | Seeded `state == "cancelled"` protection and expiry in `domain.py`, prioritized `Cancel`/`cancelled` records under overflow, and propagated `dropped_horizon` into `degraded_until` without shrinking earlier horizons; re-review pending. |
| Spec / Standards | SPEC-02 / SIT-REV-L1 | Low | Poll-time `_try_acknowledge(now)` lets future-dated `acknowledge_degraded_at` auto-clear on later polls without reload. | Evaluated `_try_acknowledge` solely at coordinator construction against load time; re-review pending. |
| Spec | SPEC-03 | Low | `_try_acknowledge()` clears `last_degraded_poll`, losing retry-budget credit for the final interval before recovery poll. | Preserved `last_degraded_poll` until after `_migrate_and_prune_outbox()` runs on recovery; re-review pending. |
| Spec | SPEC-04 | Low | `"Cached · source unavailable"` badge suppressed on cached `not_in_latest_fetch` (and missing-lifecycle) NWS items when source is unavailable. | Appended `"cached"` pill alongside `"not_in_latest_fetch"` when `isEventSourceUnavailable(...)` is true and defaulted missing/unknown NWS lifecycle on unavailable sources to `"cached"` (keeping `"expired"` exclusive); re-review pending. |
| Standards | SIT-REV-L2 | Low | Operational history-loss/re-alert caveats for missing stores, store replacement, and early overflow acknowledgement missing from docs alongside `journal_lost`. | Documented `journal_lost`, load-time-only acknowledgement, overflow `dropped_horizon`, and tombstone-loss re-alert risks across `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |

All findings from `fcc9072`, `e38a7fd`, `83f328c`, and `64b6fa0` were verified fixed at `9308033`.

### Candidate 9308033 Opus review findings

Candidate `930803369829a761cfd4593d4db3f153b8c13d64` passed 150 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical and 0 High findings** and zero regressions in prior fixes. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T180834Z-0e141a`; 348.0s standards, 394.4s specification) reported 1 Medium + 4 Low + 2 Nit standards findings and 1 Medium + 2 Low + 3 Nit specification findings (11 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-R1 | Medium | Recoverable oversized/conflicting `Actual Cancel` anywhere in monitored states triggers global 7-day degraded lockdown without operator notification. | Scoped recoverable oversized/conflicting `Actual Cancel`s (non-empty NWS target refs within 5,000-ID cap) per targeted lineage/descendants (`quarantined_cancel_lineages`), delineated Policy 4 vs Policy 6, and added `situareness_degraded` HA persistent notification; re-review pending. |
| Spec | SIT-SPEC-01 | Medium | Raw `quarantined_lineages` references enter `lineage_index()`, tainting independent sibling alerts sharing a root. | Excluded `quarantine_events` from `lineage_index()`, stripped raw refs for all `invalid_ids` in `grouping_events`, and replaced group-level quarantine with per-ID `quarantined_event_ids`/`quarantined_record_ids`; re-review pending. |
| Standards | SIT-R2 | Low | `async_stop()` waits on multi-page fetches during unload/reload. | Tracked `_fetch_task`, cancelled in-flight `fetch()` in `async_stop()`, and aborted before post-stop saves; re-review pending. |
| Standards | SIT-R3 | Low | Poll-refreshed `degraded_at` and `degraded_until` churn recorder history every minute. | Excluded `degraded_at` and `degraded_until` alongside `events` and `last_success` in `SituarenessSensor._unrecorded_attributes`; re-review pending. |
| Standards | SIT-R4 | Low | `malformed_store` reports a moving `degraded_until` timestamp it never honors. | Set `malformed_store` `degraded_until: None` and persisted stable `malformed_store_at` on the config entry until store repair; re-review pending. |
| Standards | SIT-R5 | Low | `runAction` regex routes `"Bundled configuration..."` errors to toast instead of `showDisconnected`. | Removed `Bundled configuration` from `runAction` toast regex so action failures show `"Room could not start"` and disable controls; re-review pending. |
| Spec | SIT-SPEC-02 | Low | `_valid_persisted_store` skips `bool` checks for `initialized` and `was_live`. | Required `bool` for `degraded`, `initialized`, and `was_live` in `_valid_persisted_store`; re-review pending. |
| Spec | SIT-SPEC-03 | Low | `quarantined_count` undercounts earlier identical copies of a conflicting duplicate (`[A, A, A_conflict]`). | Tracked per-ID `id_counts` in `collector.py` and added `id_counts[eid] + 1` on first conflict; re-review pending. |
| Standards / Spec | SIT-R6 / SIT-DOC-04 | Nit | 5,000-identifier quarantine cap skips feature IDs and conflicting-duplicate IDs. | Unified accounting via `add_quarantined_lineage` across all retained unique IDs (feature IDs + ref URLs + conflicting duplicates); re-review pending. |
| Spec | SIT-UI-05 | Nit | `isEventSourceUnavailable` overwrites `state.interval_minutes` when `sources` omits the entry. | Fell back to `config?.interval_minutes ?? state.interval_minutes`; re-review pending. |
| Standards / Spec | SIT-R7 / SIT-DOC-06 | Nit | `docs/reference/cap-cancellation.md` line 3 disclaimer contradicts line 19 assertions. | Reworded line 3 and Policy 6 so `cap-cancellation.md` clearly states required policy while test/review evidence verifies conformance separately; re-review pending. |

All findings from candidate `9308033` (and earlier `fcc9072`, `e38a7fd`, `83f328c`, and `64b6fa0`) were verified fixed at `120c3c4`.

### Candidate 120c3c4 Opus review findings

Candidate `120c3c4362ff529a62f3e43e59ff10a8b3c02ec2` passed 154 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 browser/UI/packaging/catalog findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T184436Z-6d91c1`; 244.0s specification, 260.7s standards) reported 3 Low specification findings and 1 Medium + 2 Low + 1+1 Nit standards findings (5 unique actionable findings + 1 non-blocking doc nit):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-HA-01 | Medium | Invalid `Actual Cancel` persists raw `refs` in `lineage`, unioning root-sharing siblings on Poll 2 into `ambiguous_groups`. | Isolated invalid `Cancel` target references in `uncertain_targets` (validated in `_valid_persisted_store`) without persisting raw `lineage` edges and isolated `nodes` `is_cancel` checks; re-review pending. |
| Spec / Standards | SIT-SPEC-01 / SIT-HA-02 | Low | `journal_lost` and persisted degraded states delay persistence/notification until after a successful fetch, and unload/remove leaves `situareness_degraded` active. | Stabilized `journal_lost_at` on config entry, persisted `journal_lost` before first fetch, synced `situareness_degraded` at init and pre-fetch, and dismissed it in `async_stop`/`async_unload_entry`/`async_remove_entry`; re-review pending. |
| Standards | SIT-HA-03 | Nit | Stopping during the first fetch while healthy returns `_degraded_health()` (`evidence_degraded: True`). | Added `_stopped_health()` returning non-degraded empty health when `not self.degraded`; re-review pending. |
| Spec | SIT-DOC-03 | Low | Docs lack concrete recovery steps for `malformed_store` when deleting the corrupt disk file triggers `journal_lost`. | Documented exact `malformed_store` repair/replacement options (repair disk JSON + reload, delete/empty disk store + reload -> `journal_lost`, or remove & re-add config entry) across `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |
| Standards / Spec | SIT-DOC-01 / SIT-DOC-02 | Low | `docs/ha/README.md:45` states seven real-HA tests and omits `journal_lost` scenarios. | Updated `docs/ha/README.md:45` to report the exact passing real-HA test count and list both `journal_lost` scenarios; re-review pending. |
| Standards (note) | SIT-DOC-02 | Nit | `docs/ha/README.md:27` overstates clearing condition for historic uncertainty (`and any suspended outbox retry expires`). | Clarified that `ended_or_absent` clears once absent while suspended outbox retries prune/expire separately under the 15-minute limit; re-review pending. |

All findings from candidate `120c3c4` were verified fixed at `f0e8a08`.

### Candidate f0e8a08 Opus review findings

Candidate `f0e8a08eb8f09585666b3ba5b2f966e57cc65a25` passed 158 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 browser/UI/packaging/catalog findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T190130Z-35fadb`; 283.6s specification, 311.6s standards) reported 1 High + 1 Low + 2 Nit standards findings and 1 Medium + 2 Low + 4 Nit specification findings (9 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-H1 | High | Replaying an identical invalid-CAP Cancel on Poll 2 triggers `conflicting_prior_cancel` -> global `conflicting_cancellation` because Poll 1 persisted `cap_identity=None`/`cap_references=None`/`lineage=[eid]`. | Persisted incoming Cancel's `cap_identity`/`cap_references` + `uncertain_targets` on first save, matched `uncertain_targets` in `conflicting_prior_cancel`, routed invalid-Cancel `records` cleanly in `cancellation_evidence()`, and verified across Poll 2 replays; re-review pending. |
| Spec | SIT-HA-01 | Medium | Unparseable JSON store file raises during `store.async_load()` or renames to `.corrupt.*` (`None`) instead of latching `malformed_store`. | Caught `store.async_load()` exceptions (`["unreadable"]`) and detected `.corrupt.*` backup files (`["corrupt_json"]`) in `async_setup_entry`, clearing backups on clean save or removal; re-review pending. |
| Spec | SIT-HA-02 | Low | Upgrading a base entry whose existing store triggers `malformed_store` never sets `journal_initialized`, so deleting the store fails to latch `journal_lost`. | Set `journal_initialized: True` when loading any non-empty valid store or entering `malformed_store`; re-review pending. |
| Spec | SIT-HA-03 | Low | Outbox exceeding 5,000 targets raises `ValueError` before `_save()`, failing every poll without durable save or notification. | Bounded outbox at 5,000 targets, saved reconciled records/outbox under durable `outbox_overflow` degraded state, and raised `situareness_degraded`; re-review pending. |
| Standards | SIT-L1 | Low | Duplicated quarantined/cancelled record builder blocks in `reconcile()` and degraded save blocks in `_update_once()`. | Extracted `_cancel_record_identity`, `_quarantined_record`, `_expire_cancellation_horizons`, `_bound_records`, `_latch_degraded`, and `_persist_degraded_poll`; re-review pending. |
| Spec | SIT-HA-04 | Nit | `_stopped_health()` reports `suspended_count: 0` even when `outbox` is non-empty. | Set `suspended_count: len(self.outbox)` in `_stopped_health()`; re-review pending. |
| Spec / Standards | SIT-HA-05 / SIT-N1 | Nit | `async_remove_entry()` deletes the store before dismissing `situareness_degraded`, contrary to spec ordering. | Dismissed `situareness_degraded` before `Store.async_remove()` and aligned `o3-mvp.md`; re-review pending. |
| Spec | SIT-DOC-01 | Nit | `collector.py` counts unique quarantined identifiers per lineage rather than per poll. | Tracked `seen_quarantine_ids` across the entire poll in `fetch()` against the 5,000-ID bound; re-review pending. |
| Spec / Standards | SIT-TEST-01 / SIT-N2 | Nit | Tests contain a leftover drafting comment and inline external review IDs. | Removed the drafting comment and replaced all review-code tags in `tests/ha/**` with behavioral comments; re-review pending. |

All findings from candidate `f0e8a08` were verified fixed at `a146710`.

### Candidate a146710 Opus review findings

Candidate `a1467104017f1efad31661370dbd19a4f37189ee` passed 162 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 browser/UI/packaging/catalog/CAP-core/gate findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T192723Z-402b20`; 307.7s standards, 340.1s specification) reported 2 Low + 2 Nit standards findings and 1 Medium + 2 Low + 3 Nit specification findings (8 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | HA-ACK-01 | Medium | `_try_acknowledge()` deletes `journal_lost_at` before `_save()` runs; if the first poll after reload fails, retries regenerate `degraded_at = now` and lose the acknowledgement. | Retained `journal_lost_at` in `entry.data` inside `_try_acknowledge()` so it clears only when `_save()` persists non-degraded state; re-review pending. |
| Spec | HA-STORE-01 | Low | `except Exception:` around `store.async_load()` treats transient `OSError`/permission errors as `malformed_store`. | Caught only JSON/value/type/key/unsupported-version errors as `malformed_store` and raised `ConfigEntryNotReady` on `OSError`/unexpected load errors; re-review pending. |
| Standards / Spec | SIT-R2 / HA-NOTIF-01 | Low | `_sync_degraded_notification` keys on `(reason, degraded_at, degraded_until)`, re-creating `situareness_degraded` every minute while triggers persist. | Keyed notification on `degraded_reason` alone with stable message text free of moving timestamps; re-review pending. |
| Standards | SIT-R1 | Low | Docs state `outbox_overflow` refreshes `degraded_at`/`degraded_until` while outbox remains above capacity, whereas degraded polls cap outbox at 5,000 before re-evaluating. | Synchronized `docs/ha/README.md`, `home-assistant/README.md`, and `o3-mvp.md` with actual `outbox_overflow` behavior; re-review pending. |
| Spec | DOC-HA-01 | Low | `docs/ha/README.md:29` states ambiguous quarantine suspends all *absent* lineages instead of *all* lineages (current and absent). | Corrected `docs/ha/README.md:29` to state `all lineages (both current and absent) are suspended for that poll`; re-review pending. |
| Spec | DOC-HA-02 | Nit | Docs say "deleting/emptying" the store file transitions to `journal_lost`, whereas a 0-byte file triggers `.corrupt.*`/`malformed_store`. | Clarified docs to say deleting the store file and any `.corrupt.*` backups (or replacing its data with empty JSON `{}`); re-review pending. |
| Standards / Spec | SIT-R3 / PERF-01 | Nit | `_save()` runs `.storage` `.corrupt.*` glob cleanup on every save, including delivery-loop saves. | Added `has_corrupt_backup` and `_needs_corrupt_cleanup` so cleanup runs once when needed; re-review pending. |
| Standards | SIT-R4 | Nit | Test lambda at `tests/ha/test_coordinator.py` references `asyncio` before `import asyncio` and leaves unused `setup_coord = None`. | Moved `import asyncio` above the lambda and removed `setup_coord = None`; re-review pending. |

All findings from candidate `a146710` were verified fixed at `c0a909c`.

### Candidate c0a909c Opus review findings

Candidate `c0a909c3309f1fc9f88ec967d6765df977ed8ca2` passed 163 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 browser/UI/packaging/catalog/output-gate findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T194649Z-7a1803`; 329.5s standards, 390.8s specification) reported 1 Medium + 2 Low + 4 Nit standards findings and 2 Medium + 1 Low specification findings (10 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SAF-01 | Medium | Non-Cancel feature failing `normalize` with valid `feature_id` and one invalid/oversized `@id` sets `quarantine_ambiguous = True` without raising `situareness_degraded`. | Scoped quarantine to `[feature_id, *valid_refs]` when `feature_id` is valid, raised `situareness_degraded` for `quarantine_ambiguous`, and aligned `o3-mvp.md`/`cap-cancellation.md`/READMEs; re-review pending. |
| Spec | SPEC-HA-01 | Medium | `outbox_overflow` strips fingerprints for already-queued overflow targets, causing acknowledgement recovery to re-latch immediately while the alert stays active. | Preserved fingerprints for already-queued targets during initial `outbox_overflow` latching so acknowledged recovery delivers cleanly; re-review pending. |
| Spec | SPEC-HA-02 | Medium | Partial-CAN unreferenced continuing updates (`U -> P`) are quarantined by root cancellation propagation (`C -> P`), blocking new actions. | Distinguished continuing unreferenced segments (`sent >= cancelled_at`) for new qualifying actions while keeping pre-cancellation retries suspended; re-review pending. |
| Spec | SPEC-HA-03 | Low | Future-dated `Actual Cancel` (`sent > now + 5m`) passes `cap_event_valid`, writing raw `lineage` edges and flipping to cancelled once the clock catches up. | Enforced `sent <= now + 5m` in `cap_event_valid(event, now)` and graph/evidence validation so future-dated `Cancel` targets stay isolated in `uncertain_targets`; re-review pending. |
| Standards | HLT-01 | Low | `_degraded_health` omits `quarantined_cancel_lineages`/`recoverable_prior_conflict` checks and couples triggered status to timestamp string equality. | Passed `triggered_now` and `recoverable_prior_conflict` flags and checked `quarantined_cancel_lineages` in `_degraded_health`; re-review pending. |
| Standards | PRV-01 | Low | `Store(hass, 1, prefix)` omits `private=True` for private journal/outbox storage. | Passed `private=True` to `Store` on load and removal; re-review pending. |
| Standards | DOC-01 | Nit | Docs list `malformed_cancellation` for all over-cap `Actual Cancel`s, omitting `conflicting_cancellation` for conflicting duplicates over the 5,000-ID cap. | Synchronized `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |
| Standards | DOC-02 | Nit | `docs/ha/README.md:27` says suspended retries clear when leaving `quarantined`, whereas `ended_or_absent` retries stay suspended up to the 15-minute limit. | Updated `docs/ha/README.md:27` to document retained suspended retries until equivalent recovery, invalidation, or 15-minute expiry; re-review pending. |
| Standards | MNT-01 | Nit | Supersession logic duplicated in `collector.py` and `domain.py`; `_update_once` and `o3-mvp.md` §Home Assistant are overly monolithic. | Reused `resolve_candidates` in `collector.py`, extracted coordinator helpers, and split `o3-mvp.md` §Home Assistant into readable paragraphs; re-review pending. |
| Standards | CMP-01 | Nit | `DataUpdateCoordinator` does not explicitly pass `config_entry=entry`. | Passed `config_entry=entry` in `SituarenessCoordinator.__init__`; re-review pending. |

All findings from candidate `c0a909c` were verified fixed at `221ed9b`.

### Candidate 221ed9b Opus review findings

Candidate `221ed9b037ea72e826f88716e14826c28e95a3df` passed 166 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 CAP/cancellation, browser/UI, packaging, catalog, or live/shadow gate findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T203507Z-d741fd`; 316.3s standards, 287.4s specification) reported 1 Medium + 4 Low + 2 Nit standards findings and 1 Medium + 2 Low specification findings (8 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-01 / SPEC-HA-01 | Medium | `outbox[:5000]` drops targets mid-plan while passing `plans=[]` keeps unqueued plans' fingerprints in `records`. | Queued whole plans atomically (draining 1 deliverable batch before overflow if space frees), kept fingerprints only for queued plans, stripped dropped overflow plans, and documented the ~1,500-target/15m delivery bound; re-review pending. |
| Spec | SPEC-HA-02 | Low | Valid `feature_id` with non-dict/null `properties` triggers `quarantine_ambiguous = True`. | Scoped `[feature_id]` whenever `feature_id` is extractable regardless of `properties` type; re-review pending. |
| Spec / Standards | STD-HA-03 / SIT-07 | Low / Nit | `degraded_reason` restore has an operator-precedence bug and `_valid_persisted_store` accepts unknown/`malformed_store` strings. | Parenthesized fallback expression and validated `degraded_reason` against `PERSISTED_DEGRADED_REASONS`; re-review pending. |
| Standards | SIT-02 | Low | `_degraded_health` hardcodes `planned_count: 0` without showing withheld plans. | Exposed `withheld_count` (and queued `planned_count` on initial `outbox_overflow`) across coordinator health snapshots; re-review pending. |
| Standards | SIT-03 | Low | Double `deepcopy` in `reconcile` and unvalidated 5,001-phone test caused slow-callback warnings; 1,000-record cost was unmeasured. | Replaced double `deepcopy` with single `deepcopy` + shallow dict copies, used `islice(..., 100)` in delivery scan, replaced the 5,001-phone test with a valid 50-phone multi-plan test, and added a 1,000-record `reconcile` benchmark; re-review pending. |
| Standards | SIT-04 | Low | `docs/CONTEXT.md` and `docs/plans/primary-source-roadmap.md` omit degraded mode, `acknowledge_degraded_at`, and `situareness_degraded` notifications. | Synchronized both documents with degraded mode and existing local persistent notifications; re-review pending. |
| Standards | SIT-05 | Low | Normative degraded/cancellation rules are duplicated in long paragraphs across four documents. | Made `docs/spec/o3-mvp.md` (`#home-assistant`) the single canonical normative contract with concise operator summaries and cross-links in `docs/ha/README.md`, `home-assistant/README.md`, and `cap-cancellation.md`; re-review pending. |
| Standards | SIT-06 | Nit | Production `__init__.py` includes test-compatibility `ImportError`/`hasattr`/`isinstance` shims that could hide HA breakage. | Moved test shims into `tests/ha/test_coordinator.py` `HA_MODULES` and fake `hass` fixtures; re-review pending. |

All findings from candidate `221ed9b` were verified fixed at `ad93ead`.

### Candidate ad93ead Opus review findings

Candidate `ad93eada5a9222fe3120707180b24c2704dc5e7c` passed 168 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 CAP/qualification/quarantine/lifecycle/browser/packaging/catalog findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T214931Z-ca8e85`; 318.6s standards, 291.6s specification) reported 1 Medium + 2 Low + 2 Nit standards findings and 1 Medium + 1 Low-Medium + 1 Low specification findings (7 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-R1 / HA-OVF-01 | Medium | `outbox_overflow` latches a 7-day `degraded_until`, halts queued delivery, and freezes item ages via `degraded_delta`, preventing automatic overflow recovery. | Updated `outbox_overflow` to use the 15-minute `MAX_AGE` horizon, keep bounded 100-target/poll queued delivery active without aging freeze (`evidence_degraded: false`, `output_blocked: false`, accurate `deliverable_count`/`suspended_count`/`withheld_count`), and auto-clear once plans fit within `5,000`; re-review pending. |
| Spec | HA-STORE-01 | Low-Medium | Store major/minor version mismatches (`NotImplementedError` or silent `_async_migrate_func` fallback) can retry indefinitely or overwrite instead of entering `malformed_store`. | Added a rejecting `_async_migrate_func` on `Store` and caught `NotImplementedError` alongside `ValueError`/`UnsupportedStorageVersionError` as `malformed_store` with real-HA wrong-version tests; re-review pending. |
| Standards | SIT-R2 | Low | `CancellationEvidenceOverflow` strips planned fingerprints inside `domain.py`, causing coordinator `withheld_count` to report `0`. | Carried stripped `plans` on `CancellationEvidenceOverflow` and passed `len(plans)` into `_persist_degraded_poll` `withheld_count`; re-review pending. |
| Standards | SIT-R3 | Low | `config.validate()` accepts future `acknowledge_degraded_at`, and non-matching load-time acknowledgements remain unconsumed until the clock passes them. | Enforced `ack_ts <= now` in `config.validate(raw, now=None)` and consumed non-matching/premature `acknowledge_degraded_at` values on load so they cannot clear unseen later degradations; re-review pending. |
| Spec | HA-IO-01 | Low | `_deliver_outbox_batch` rewrites the full journal and outbox after every single delivery item (up to ~100 full rewrites per poll). | Batched expired-item pruning and post-group delivery persistence once per completed 10-target delivery group while keeping at-least-once semantics; re-review pending. |
| Standards | SIT-R4 | Nit | `situareness_degraded` notification text hardcodes a "seven-day horizon" and omits `acknowledge_degraded_at` recovery instructions. | Differentiated `outbox_overflow`, horizon-extended evidence/journal degradations (`degraded_until` + `acknowledge_degraded_at` + reload), and `malformed_store` manual repair guidance; re-review pending. |
| Standards | SIT-R5 | Nit | `test_reconcile_thousand_record_bounded_latency` uses a tight `< 0.5s` wall-clock assertion. | Asserted `d.deepcopy` `call_count == 1` deterministically and relaxed the wall-clock sanity bound to `< 5.0s`; re-review pending. |

All findings from candidate `ad93ead` were verified fixed at `3d18093`.

### Candidate 3d18093 Opus review findings

Candidate `3d1809327eafc2bb09c88ef104622e9eacb4b7cc` passed 169 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 Medium findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T221552Z-4d6117`; 309.4s standards, 308.7s specification) reported 3 Low + 3 Nit standards findings and 2 Low specification findings (7 unique findings total, plus 1 capacity advisory):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-HA-01 / HA-JLOST-01 | Low | Reusing a stale `journal_lost_at` across repeat store loss or `malformed_store` deletion shortens the 7-day `journal_lost` hold. | Extended `degraded_until` from `max(lost_ts, detect_now) + MAX_ACCEPTANCE_AGE`, rotated stale timestamps older than 7 days, and cleared `journal_lost_at` on post-fetch saves, non-empty store loads, and `malformed_store` entry; re-review pending. |
| Spec | HA-NOTIFY-01 | Low | `_sync_degraded_notification` picks `.storage` manual-repair text whenever `degraded_until` is null even for non-`malformed_store` reasons. | Selected notification copy by `degraded_reason` (`malformed_store` vs `outbox_overflow` vs `degraded_until`/`acknowledge_degraded_at`); re-review pending. |
| Standards | SIT-HA-02 | Low | Persisted outboxes over 5,000 items pass validation and are truncated silently in `_queue_outbox_plans`. | Rejected `len(outbox) > 5000` in `_valid_persisted_store` as `malformed_store` and removed silent truncation; re-review pending. |
| Standards | SIT-TOOL-01 | Low | `tools/live-browser-smoke.mjs` polling promise can reject unhandled after a timeout before `live-browser-smoke.json` writes. | Added a `stopped` flag checked in the polling loop and `smokePromise.catch(() => {})` before `Promise.race`; re-review pending. |
| Standards | SIT-HA-03 | Nit | `async_setup_entry` assigns private `store._async_migrate_func`. | Removed the private attribute assignment; HA's default `NotImplementedError` and `UnsupportedStorageVersionError` continue mapping version mismatches to `malformed_store`; re-review pending. |
| Standards | SIT-DOC-01 | Nit | `docs/spec/o3-mvp.md` §Home Assistant uses dense single-paragraph blocks restated across READMEs and `docs/CONTEXT.md`. | Reformatted `docs/spec/o3-mvp.md#home-assistant` as structured bulleted subsections and slimmed `docs/ha/README.md`, `home-assistant/README.md`, and `docs/CONTEXT.md` to concise links/summaries; re-review pending. |
| Standards | SIT-HA-04 | Nit | Degraded notifications say "output is blocked" even in shadow mode. | Qualified degraded notification text when `live(self.config)` is false; re-review pending. |

Advisory note `HA-CAP-01` (multi-state feeds near 1,000 features plus retained tombstones reaching the 1,000-record `cancellation_evidence_overflow` bound) is documented in `docs/spec/o3-mvp.md#home-assistant` and `docs/ha/README.md`.

All findings from candidate `3d18093` were verified fixed at `6236ea8`.

### Candidate 6236ea8 Opus review findings

Candidate `6236ea8f7e47aed3a8d8be0966f77baf8af1b2e7` passed 170 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and zero room/live-gate/routing/quarantine/overflow defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T223104Z-7fe723`; 215.8s standards, 202.2s specification) reported 1 Medium + 3 Low + 1 Nit standards findings and 1 Medium + 1 Low + 1 Nit specification findings (7 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-HA-ACK-01 / SIT-HA-02 | Medium / Low | `_latch_degraded` resets `degraded_at` every poll on recurring triggers, racing `acknowledge_degraded_at`; consumed/rejected acks lack operator visibility; notification/docs omit active-trigger clearing prerequisites. | Kept initial `degraded_at` stable across unchanged reasons while extending `degraded_until`, exposed `acknowledge_rejected` in snapshots + notifications (including immediate Poll 1 re-latch), and documented trigger-clear + `>= degraded_at` prerequisites; re-review pending. |
| Spec | SIT-DOC-01 | Medium | Standalone bundle `home-assistant/README.md` links to `../docs/spec/o3-mvp.md` and `../docs/reference/cap-cancellation.md` which are absent from the HA ZIP archive. | Replaced external links with a self-contained recovery, bounds, attribute, retry-freeze, and tombstone-warning section inside `home-assistant/README.md`; re-review pending. |
| Standards | SIT-HA-CANCEL-02 | Low | `_update_once` converts external outer-task `asyncio.CancelledError` into a normal return whenever `self._stopping` is True. | Gated stopped-health fallback on `current_task is None or current_task.cancelling() == 0` so outer task cancellations propagate cleanly; re-review pending. |
| Standards | SIT-HA-STORE-03 | Low | `async_setup_entry` catches broad `(TypeError, KeyError)` on `store.async_load()`, turning internal store errors into `malformed_store`. | Narrowed handler to `(json.JSONDecodeError, ValueError, NotImplementedError)` + `UnsupportedStorageVersionError` so unexpected errors raise `ConfigEntryNotReady`; re-review pending. |
| Standards | SIT-DOC-RETRY-04 | Low | Operator guides promise a 15-minute retry window without explaining the degraded-mode `last_degraded_poll` retry-age freeze across multi-day holds. | Documented degraded-mode retry age preservation and up to 7+ day delayed resumption across `home-assistant/README.md`, `docs/ha/README.md`, and `docs/spec/o3-mvp.md`; re-review pending. |
| Standards | SIT-NIT-05 | Nit | `_deliver_outbox_batch` comment still states per-item persistence and docs omit the expired-key prune save. | Updated comment and docs to describe expired-item pruning saves plus per-10-target-group delivery saves; re-review pending. |
| Spec | SIT-DOC-03 | Nit | `docs/ha/README.md` sensor attribute list omits `event_count` and `source_feature_count`. | Added `event_count`, `source_feature_count`, and `acknowledge_rejected` to `docs/ha/README.md` and `home-assistant/README.md`; re-review pending. |

All findings from candidate `6236ea8` were verified fixed at `c81fb7f`.

### Candidate c81fb7f Opus review findings

Candidate `c81fb7f5221b54a88453627dd5376216db0051b9` passed 171 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and zero room/catalog/quarantine/overflow/lifecycle defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T224454Z-a299b9`; 217.6s standards, 373.9s specification) reported 1 Medium + 1 Low standards findings and 1 Medium + 2 Low specification findings (3 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | HA-ACK-01 / SPEC-HA-01 / DOC-HA-02 | Medium / Low | `config.validate` raises `ValueError` for future or unparseable/naive `acknowledge_degraded_at` strings, failing HA setup (`ConfigEntryNotReady`), hiding `situareness_degraded`/`acknowledge_rejected`, and letting automatic retries apply a future timestamp later; operator docs promise `acknowledge_rejected`. | Validated only non-string/empty/control-character values in `config.validate`, moved timestamp parsing/future checks into `SituarenessCoordinator._try_acknowledge` (setting `acknowledge_rejected: true`, updating `situareness_degraded`, and persisting valid ISO timestamp consumption in `entry.data` and store without blocking setup), and synced docs + real-HA reload coverage; re-review pending. |
| Standards | HA-DOC-02 | Low | `home-assistant/README.md` line 19 states `(unrecoverable Actual Cancel or >5,000 quarantined IDs; 7 days)`, whereas >5,000 non-Cancel IDs trigger `quarantine_ambiguous`. | Clarified `malformed_cancellation`/`conflicting_cancellation` vs poll-scoped `quarantine_ambiguous` in `home-assistant/README.md`; re-review pending. |
| Spec | SPEC-HA-03 | Low | `_bound_records` computes `dropped_horizon` over all dropped groups rather than only dropped protected/cancellation groups, allowing unprotected old records to extend overflow lockouts. | Restricted `dropped_groups` in `_bound_records` to `eid in protected` and verified unprotected 30-day records do not extend `dropped_horizon`; re-review pending. |

All findings from candidate `c81fb7f` are being repaired on `wip/supervisor-handoff-20261117`. Independent Claude Opus 5.5 (`standards`, `spec`, and fresh `adversarial`) reviews on the repaired immutable candidate remain required before release approval.
