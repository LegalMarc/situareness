# Independent review record

The release gate is open until the current candidate has zero supported unresolved findings on standards, specification, and fresh adversarial review. Interrupted attempts are not approvals. Public records omit private paths and local raw logs.

## Candidates and reviewers

| Candidate | Scope | Reviewer | Result |
| --- | --- | --- | --- |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Public privacy and clean history | Claude Opus 5.5, medium effort | PASS, zero findings |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Standards | Claude Opus 5.5, medium effort | Seven findings; repaired in next checkpoint |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Specification | Claude Opus 5.5, medium effort | Seven findings; repaired in next checkpoint |
| `2c0f1e1864d1738e5c5488d3c0e423c0f0a7ebee` | Standards | Claude Opus 5.5, medium effort | Ten findings; repaired in the next checkpoint; re-review pending |
| `2c0f1e1864d1738e5c5488d3c0e423c0f0a7ebee` | Specification | Claude Opus 5.5, medium effort | Twelve findings; repaired in the next checkpoint; re-review pending |

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

The user replaced the review policy during continuation: implementation and fresh reviews remain within the same model family/provider. Current workers use OpenAI `gpt-6.1-terra`, high effort, and fresh reviewers use `gpt-6-astra`, ultra effort. Historical Opus reviews above remain evidence of their own candidates; they do not approve this continuation.

The focused browser review at immutable `63da80f6660667a529a3c4e0d1a0b7bc368760b5` found one P2 issue, [BROWSE-01](browser-focused-63da80f.md). Its outage-age repair passed 40 Node and 16 browser tests and is checkpointed at `5ec38ac`. Full-candidate re-review is pending.

The supervisor also identified the following supported integration cases in the uncommitted HA continuation; these observations are not an independent immutable-candidate release review:

| Code | Finding | Current disposition |
| --- | --- | --- |
| CAP-SCOPE-01 | A global missing-predecessor rule could quarantine unrelated updates after any retained Cancel. | Scoped to established cancellation components; regression passes, independent review pending. |
| CAP-RENEW-01 | A renewal referencing both a Cancel and the historical root could remain blocked by historical traversal. | Explicit renewal boundary retained without deleting tombstones; regression passes, independent review pending. |
| CAP-STORE-01 | A malformed non-None saved journal or a conflicting replay of a cancellation identity could erase protection. | Durable degradation and restart/no-output regressions pass; independent review pending. |
| CAP-ID-01 | A current Alert/Update with conflicting or incomplete CAP identity/reference metadata could still qualify and deliver outside a known cancellation group; its invalid references could suppress valid candidates in collection. | Reproduced before candidate freeze; repair interrupted by worker usage limit. Resumed 56-test stdlib run reports six failures, including lost invalid-Cancel uncertainty; repair and realistic live/restart regressions remain in progress. |

Before CAP-ID-01 was found, integrated checks passed 40 Node, 56 standard-library HA, seven source-skill, 16 browser and five actual-HA tests (124 total), lint/format, anonymous live read and deterministic archive builds. Those logs are preserved locally as a pre-identity-audit run and must not be used to approve changed files. Five upstream HA dependency deprecations remain unsuppressed. Complete current gates and independent standards, specification and fresh adversarial review are still required.
