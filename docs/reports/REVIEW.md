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

## Evidence limits

The candidate passed 79 automated tests, a live anonymous browser read, and deterministic packaging before these findings were discovered. Those successes did not cover the reported triggers. Home Assistant source and delivery targets were simulated. The live smoke returned no NWS alerts, so it cannot validate real CAP lineage. Physical commissioning, broader primary-source adapters, automatic health escalation and the browser-to-HA health bridge remain separate work.
