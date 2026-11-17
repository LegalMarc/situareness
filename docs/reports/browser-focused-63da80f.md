# Focused browser and package review

Candidate: `63da80f6660667a529a3c4e0d1a0b7bc368760b5`. Base: `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83`.

Reviewer: fresh-context OpenAI `gpt-6-astra`, ultra reasoning, reviewing the `gpt-6.1-terra` implementation within the same model family/provider under the user's replacement instructions. This read-only focused pass is separate from the full release standards/specification axes and final adversarial gate. It read immutable Git objects despite unrelated uncommitted HA work.

Result: **FAIL — one P2 finding.**

- **BROWSE-01: Recompute freshness while the collector is disconnected.** Candidate `extension/room.js:523–536`: failed `GET_STATE` requests update the disconnect notice and controls without rerendering sources or events. A room opened with fresh NWS data retains “In latest results” and “Collected Just now” throughout an outage, even after the source becomes overdue. This violates the cached/overdue labeling contract. Recompute time-dependent source and event labels on failed polls while preserving the disconnect notice and disabled controls.

The reviewer reproduced this deterministically in a Node VM loading candidate modules from Git objects: render a fresh one-minute NWS source, advance the clock five minutes, then reject the scheduled request. Card text remained unchanged and the freshness banner remained hidden while the collector correctly showed disconnected.

The pass inspected the scoped source/test changes, candidate setup/spec/context/ADRs, packaging, and supplied verification logs. No other supported finding was established. Repair is implemented with scheduled/manual outage clock-advance regressions: 40 Node and 16 browser tests pass. Independent full-candidate re-review remains pending; this is not release approval or physical commissioning.
