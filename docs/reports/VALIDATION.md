# Validation status

## Current status

November 17, 2026 continuation: after resolving all 19 Claude Opus 5.5 findings from `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a`, the repaired candidate on `wip/supervisor-handoff-20261117` passes 141 local tests, static checks, Ruff lint/format, warnings-as-errors stdlib checks, deterministic packaging, and a live anonymous browser smoke check (HTTP 200 across NWS, USGS, and both BBC endpoints). Separate independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards`, `spec`, and fresh `adversarial` reviews on the new immutable candidate remain pending. Public `main` remains at `847d0e5`. See [handoff](../plans/HANDOFF.md) and [review findings](REVIEW.md).

No production installation, audible commissioning or clean final adversarial review has occurred. Interrupted or quota-limited attempts are not approvals.

## Automated evidence

Current continuation checks: 41 Node tests, 67 standard-library HA tests, seven source-skill tests, 19 Chromium tests and seven actual-HA tests (141 total). Tests cover extracted installation archives, outage-age updates, bundled-config startup errors, cached non-weather badges, directed CAP identity/reference validation, 7-day acceptance and cancellation-evidence horizon, scoped uncertainty resolution, per-feature malformed/oversized quarantine, deep persisted-store validation, continued read-only collection while output-blocked in degraded state with `acknowledge_degraded_at` and 7-day recovery, independent sibling/descendant delivery, and suspended retries across restart. Actual services and locations are simulated; none proves household delivery. Ruff and deterministic archive builds pass (`ab60bd6d...` for extension ZIP, `d4d2798e...` for HA ZIP). Five upstream actual-HA deprecations remain unsuppressed. Live anonymous browser smoke passed at `2026-11-17T17:10:55Z` with HTTP 200 across all four endpoints (zero active NWS alerts in the sample query, 6 USGS, 22 BBC World, 23 BBC US & Canada).


Candidate `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` passed static checks, 34 Node tests, 33 standard-library Home Assistant policy/boundary/packaging tests, seven companion-catalog tests, and 14 isolated Chromium browser tests. Five additional tests passed against Home Assistant 2026.11.1, including the actual loader, entity/service registries, disk-backed private storage, recorder SQLite exclusions, and removal during an in-flight refresh. Source events and output targets were simulated locally. This is 93 automated tests total, with no household device delivery.

Ruff lint and formatting passed, and the standard-library HA suite passed with warnings treated as errors. A read-only live browser smoke test on November 16 received HTTP 200 from NWS, USGS and both BBC endpoints; NWS returned no current items in the sample NY/DC query. Two installation archive builds produced identical manifests and SHA-256 hashes. These checks cannot validate real CAP lineage or source availability beyond that observation.

The real Home Assistant test dependency stack emitted five upstream deprecation warnings from Home Assistant HTTP and `backoff`. They were not suppressed or patched in the project. The standard-library suite passes with warnings treated as errors. Reproduction commands are in [setup](../setup.md) and [HA setup](../ha/README.md).

## Required release checks

The initial public root was published after a verified privacy review with zero findings. Its clean history contains generic examples and approved public material. Review-driven changes are being checkpointed publicly with release review still pending; this is not a commissioned release. Before a release, resolve the handoff failures and all supported review findings, then recheck the complete tree and Git history. Check local-data exclusions and installation archives, run the complete current test commands, and perform a live anonymous read-only source smoke test. Record the exact public candidate SHA and independent reviewer evidence here when those checks finish.

## Limits

No actual household Home Assistant, private location footprint, enrolled phone, physical speaker or horn was tested. No alert was delivered to a real recipient. API acceptance and a quiet shadow period do not establish reliable receipt. Browser collection depends on Chrome execution and an awake computer; independent operation requires an installed and healthy Home Assistant monitor. Broader primary-source adapters and a room-to-HA health bridge remain planned in the [roadmap](../plans/primary-source-roadmap.md).
