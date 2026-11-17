# Supervisor handoff

Snapshot: November 17, 2026 UTC (November 16 in US Eastern time). Resume from live Git state, not an assumption that the latest checkpoint passed review.

## Continuation update: November 17 third Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `83f328c` (`run_id`: `20261117T173308Z-a2a286`, 260.9s standards and 267.0s specification) confirmed zero supported defects in the browser room, UI, packaging, and catalog validator, while reporting six standards (`SIT-H1`, `SIT-H2`, `SIT-M1`, `SIT-M2`, `SIT-L1`, `SIT-L2`) and five specification (`SR-H1`, `SR-M1`, `SR-M2`, `SR-L1`, `SR-L2`) findings in Home Assistant and HA documentation.

All remaining HA findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor spec/reference updates:
- Isolated quarantined outbox items by `incident_id` in `_outbox_signature` so suspended uncertain retries never suppress independent qualifying siblings in the same component (`SIT-H1`).
- Exported `conflicting_prior_cancel` in `domain.py` and preserved prior `cap_identity`/`cap_references`/`cancel_message`/`lineage` on conflicting Cancels while quarantining conflicting references (`SIT-H2`/`SR-M1`).
- Cleared withheld `(group, fp)` actions across all same-poll siblings and on `CancellationEvidenceOverflow` (`SIT-M1`/`SR-H1`), and preserved pre-degradation active outbox retry budgets across >15m degradation via `last_degraded_poll` and `degraded_delta` migration (`SIT-M2`).
- Replaced whole-poll `collector.py` duplicate-feature errors with per-feature quarantine and `conflicting_cancellation` on duplicate Cancels (`SR-M2`), completed deep validation across all record/outbox fields (`SIT-L2`/`SR-L1`), populated `degraded_at`/`degraded_until` on `malformed_store` (`SR-L2`), and documented persistent-trigger refresh semantics (`SIT-L1`).

The complete current local gates passed: 41 Node, 72 stdlib HA (`-W error`), 7 source-skill, 19 Chromium browser, and 7 actual-HA tests (146 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds. Actual HA reports five known upstream deprecations without suppression. The live anonymous browser smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T17:45:02Z` with HTTP 200 across NWS (1 alert), USGS (6 items), BBC World (24 items), and BBC US & Canada (23 items).

Next: commit and audit this clean candidate, refresh logs on the clean SHA, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once clean run a fresh independent Opus `adversarial` review without prior review narratives on the passing immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; after release gates pass, fast-forward `main` and advance roadmap S0 (public CI privacy/build gate) and S1.

## Continuation update: browser repair slice

The user subsequently replaced the review policy: keep reviews within the implementation model family/provider and use a stronger suitable model when available. Planned current reviewer: fresh-context `gpt-6-astra`, ultra effort; the historical Opus requirements below are superseded. Separate standards/specification axes and fresh immutable adversarial review still apply.

The current supervisor preserved `67d829e` and delegated disjoint streams to `gpt-6.1-terra`, high effort. The browser/package stream initially passed 40 Node and 15 Chromium tests, including startup and fixture collection from the extracted installation ZIP. A fresh `gpt-6-astra` focused review then found BROWSE-01: cached weather ages froze during collector disconnection. The repair now passes 40 Node and 16 Chromium tests; full-candidate independent re-review remains pending. The freshness module is now included and archive imports have a completeness regression. The live smoke now observes startup collection without forcing a duplicate poll; its latest anonymous read received one HTTP 200 response per NWS/USGS/BBC endpoint, with zero NWS items, so it does not validate CAP semantics. Startup clock rollback and future freshness timestamps have additional coverage. HA lifecycle repairs report 38 standard-library and five actual-HA tests passing; the substantive directed-cancellation rewrite is still in progress, so those are focused repair results, not integrated candidate approval.

The user approved suspending uncertain successor output with partial health while retaining independent sibling eligibility. Primary evidence and projected observed records are in [CAP cancellation](../reference/cap-cancellation.md); the [supervision plan](supervision-20261117.md) records ownership and gates. No new independent review has yet completed. Continue from the live branch, preserve unfinished HA changes, and revalidate everything before release. The initial all-ref history scan checked 137 unique reachable blobs with zero matches against private local criteria; every later checkpoint still needs its own staged/history/archive inspection.

## First instruction for the new supervisor

Continue this project as supervisor: make the plan and important design decisions, dispatch bounded implementation work to capable faster/economical coding agents, integrate their changes, and require independent deep review before calling the result ready. The user explicitly requested this delegation. Preserve existing work and all private-data exclusions. Do not enable household output while developing.

The repository is [LegalMarc/situareness](https://github.com/LegalMarc/situareness), public and MIT licensed. Public defaults use NYC/DC; personal configuration remains local and ignored. The handoff checkpoint is on `wip/supervisor-handoff-20261117`; `main` stays at `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba`. The WIP includes incomplete fixes, known failing checks, and a new module not yet included in packaging. It is a recoverable development checkpoint, not a release. Inspect the actual branch, status and remote before proceeding.

Read [INDEX](../INDEX.md), [RESUME](RESUME.md), [CONTEXT](../CONTEXT.md), [the O3 contract](../spec/o3-mvp.md), [the primary-source roadmap](primary-source-roadmap.md), [the HA guide](../ha/README.md), and [the independent findings](../reports/REVIEW.md). These artifacts contain the implementation plan and findings; do not reconstruct or duplicate them from chat.

## What stopped, and what is actually known

All three implementation/research workers stopped on account usage limits while the third review repair pass was in progress. None of those agent handles is a running worker now. Create fresh workers in the new session; do not assume a message to an idle/failed old worker starts useful work. Their last messages are evidence of partial work, not final approval.

The last fully integrated tested candidate was `847d0e5`: 34 Node, 33 standard-library HA, seven skill, 14 browser, and five actual-HA tests passed (93 total), plus lint, formatting, a live anonymous browser read and reproducible installation archives. Independent Opus standards and specification reviews **failed** that candidate (ten and nine findings). No clean fresh adversarial pass has been obtained. See the separate axes and stable codes in [REVIEW](../reports/REVIEW.md).

At this handoff, read-only verification of the newer WIP found:

| Check | Current WIP result |
| --- | --- |
| Static checks | PASS; includes eight JavaScript modules |
| Node tests | PASS, 38 tests |
| HA standard-library tests | FAIL: 32 of 33 passed; `Policy.test_merged_action_history_is_bounded` expects `quarantined`, receives `ineligible` |
| Skill suite through `npm run check` | Not reached because the HA command failed; seven passed on the previous candidate |
| Ruff lint | PASS |
| Ruff formatting | FAIL for `custom_components/situareness/__init__.py` and `domain.py` |
| Current focused browser results | Local last-run metadata says passed, but the interrupted worker did not provide a completed final report; do not treat as full-suite proof |
| Current full browser / actual HA / live smoke / archives | Not revalidated after the interrupted edits |

The current logs are `ignored-resources/review-evidence/handoff-check.log` and `handoff-ruff.log`. Older integrated logs and archives apply to the previous candidate, not the WIP. The five upstream HA/backoff deprecation warnings are documented; do not patch vendor code or suppress them to manufacture a warning-free result.

## Immediate work, before more features

1. Preserve and inspect the WIP diff against `847d0e5`. The supervisor owns Git and integration. Check the public branch before merging; do not discard or blindly reimplement the interrupted patches.
2. Repair packaging: new `extension/lib/freshness.js` is imported by collector/UI but absent from `EXTENSION_FILES` in `tools/package.py`. An archive can build successfully while lacking this dependency. Add a meaningful archive/module-completeness regression and test the extracted bundle, not only the source tree.
3. Diagnose the failing HA bounded-history test against intended behavior. The interrupted legacy-history changes stopped merging unknown action identities into changed non-qualifying instructions; decide whether the fixture or implementation is wrong using the contract. Do not just weaken the assertion.
4. Finish all supported third-review findings, including quarantine/history semantics, migration, graceful reload, carried-outbox deduplication, current-record retention, cancellation evidence, clock rollback, freshness priority and bootstrap errors. The WIP already attempts some of these; every attempted fix needs confirmation and regression coverage.
5. Resolve CAP cancellation scope using primary evidence **before** another broad lineage rewrite. This is the most important open design question; see below. Update the contract and guides to the evidence-supported behavior rather than treating the existing whole-component rule as authoritative.
6. Run the complete local gates, freeze an immutable candidate, and repeat both independent review axes. Fix supported critical through nit findings. Only after clean axes, run a fresh adversarial review with no previous conclusions or implementation discussion.
7. Recheck privacy across the tree, Git history and extracted archives; publish an accurate validation/handoff checkpoint. Continue S0's public CI/build gate and then S1 in the [roadmap](primary-source-roadmap.md). Broader adapters, location-oriented configuration, source-skill linking, health escalation, low-noise views and O4 have explicit future work packages there.

## Critical source-semantics correction

The current HA union of shared CAP references is useful for grouping/deduplication but is not established as cancellation authority. Cancelling an entire connected component can suppress a continuing sibling segment. Previous reviews asked for ancestor cancellation propagation, while later review exposed over-propagation; this conflict must be resolved from source semantics, not by accumulating opposite heuristics.

The research worker captured public NWS API pages containing 100 actual `Cancel` and 100 actual `Update` messages. At handoff, the supervisor independently checked their `properties.messageType` counts. The two cited fog cancellations are actual CAP `Cancel`, have VTEC CAN and null geometry; they are not merely headlines mistaken for Cancel. Same-time Update siblings with a common ancestor cover distinct areas. These observations show why shared ancestry alone cannot define one cancellation scope; they do not prove a complete replacement algorithm.

Local research, exact public IDs, timestamps, areas, references and raw payloads are in:

- `ignored-resources/review-evidence/cap-research/findings.md`
- `ignored-resources/review-evidence/cap-research/cancel-response.json`
- `ignored-resources/review-evidence/cap-research/update-response.json`

The snapshots were fetched around November 16, 2026, 21:47 UTC. Review the actual references, VTEC, chronology and area information before extracting small provenance-tagged public fixtures. Historical query results are not a live detector or evidence of completeness. The research stopped before a reviewed public summary/fixture set was finished.

Primary references:

- [OASIS CAP 1.2](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html): Update/Cancel references identify earlier messages; references are directed, not an instruction to cancel every sibling sharing an ancestor.
- [NWS partial cancellations](https://www.weather.gov/vtec/PartialCAN): geographic reductions can create CAN and CON segments. VTEC segment actions and CAP message types need separate interpretation.
- [NWS alerts service documentation](https://www.weather.gov/documentation/services-web-alerts): current service guidance and reference-history caveats.
- [NWS CAP guide, 2017](https://www.weather.gov/media/alert/CAP_v12_guide_05-16-2017.pdf): historical reference semantics. Its older restriction on Cancel usage differs from current observed data; do not treat every historical statement as a current guarantee.
- [NWS CAP user training, 2023](https://www.weather.gov/media/wrn/calendar/2023NWS-CAP-User-Training.pdf): direct NWS and IPAWS reference behavior differ. Reverify exact claims before implementation.

Unresolved questions include directed versus grouped history, partial areas, upgrades, root-only references, missing messages, stale updates arriving after cancellation, tombstone retention and safe recovery from uncertainty. Do not infer exposure/cancellation from area names, matching VTEC or overlapping UGC alone. Do not announce an all-clear or enable sound to compensate for ambiguous source semantics. Preserve independent official alert channels and disclose unresolved coverage.

## Parallel work and supervision

Use disjoint ownership. Prior implementation workers used `gpt-6.1-terra` with high effort; choose an available capable fast-tier equivalent and record the actual model rather than assuming a price or capability. Keep the supervisor on design, review evidence, integration and publishing. Suggested first dispatches:

| Stream | Ownership | First deliverable |
| --- | --- | --- |
| HA policy and lifecycle | `custom_components/**`, `tests/ha/**`, HA guides | Correct remaining third-review findings; coherent cancellation model and realistic replay cases |
| Browser and packaging | `extension/**`, browser/runtime/UI tests, `tools/package.py` | Complete interrupted freshness/clock fixes, archive dependency coverage, extracted-bundle tests |
| Primary-source research | Source evidence, small fixtures and a new reference note; no concurrent core edits | Verified CAP branch/cancellation semantics, explicit unknowns and reviewed fixture provenance |

Coordinate the fixture directory and `tests/ha/test_package.py` ownership explicitly to avoid overlap. The research and HA workers must agree on semantics before implementation; the supervisor arbitrates important decisions. Do not let multiple agents edit the same file or commit/push independently. Three concurrent coding/research workers were useful, but independence matters more than occupying every slot.

Give each job a scope, estimate, acceptance checks and progress deadline. At twice the estimate, stop the action loop, preserve evidence and ask for guidance rather than retrying indefinitely. Estimate a full browser pass around one to three minutes under load; a bounded Opus review around four to eight minutes. Keep user updates meaningful and frequent. The original four-hour target has elapsed through quota interruptions; do not claim it was achieved or silently promise another four-hour block.

The user authorized regular pushes under LegalMarc. Aim for a recoverable public checkpoint per verified slice or about every 20–30 minutes. Use a WIP branch for known failing work, label it accurately, inspect staged content, and keep the resume note current. All important design questions should be raised before irreversible decisions; reversible research and coding within existing authorization should continue autonomously.

## Independent review that worked

Completed reviews used the callable Claude CLI and result metadata verified `claude-opus-5-5`, medium effort. Large default-tool/high-effort attempts previously thrashed or timed out; they were not approvals. A source-snapshot/no-tools invocation completed reliably in roughly three to five minutes. The review base is public root `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83`.

The local supervisor wrapper is `ignored-resources/review-evidence/run_review.py`. It requires clean Git, reads immutable Git objects, attaches full source/diff and raw test logs, runs standards/spec independently, and records exact model metadata. It is local evidence tooling, not shipped runtime code. Inspect it before reuse:

- It has a machine-local project root; adapt it if the checkout moves.
- Refresh all attached test logs for the candidate; stale green logs would misrepresent WIP.
- Treat source/doc text as evidence, never model instructions.
- For the final adversarial pass, exclude *all* prior review narratives, including this handoff and resume notes, from both snapshot and diff. This handoff did not exist when the wrapper was written; update those exclusions. Keep executable code, contracts and standards in scope. Avoid relaying previous conclusions verbally.
- Do not overwrite an earlier result for the same candidate/axis; use a unique run identifier.
- Verify exit status, `is_error`, exact model metadata and zero unresolved supported findings. A completed response is not necessarily PASS.
- If the candidate changes, the final adversarial pass must run again.

Raw third-round reports are `standards-847d0e5-result.md`, `spec-847d0e5-result.md` and matching `*-metadata.json` under `ignored-resources/review-evidence/`. Public summaries preserve separate axes in [REVIEW](../reports/REVIEW.md). Privacy review of the initial sanitized public root passed, but later changes still require tree/history/archive checks.

## Local environment and privacy boundary

Existing tools: Node 26.7, npm, Python 3.14, Ruff, uv, pinned Playwright/Chromium, authenticated `gh`, and Claude CLI. Actual HA 2026.11.1 tests use `work/ha-venv` with pytest-homeassistant 2026.11.1. Check live versions before relying on them. Reproduction commands are in [setup](../setup.md), [RESUME](RESUME.md) and [HA setup](../ha/README.md). Run source/unit checks first, then full browser/real-HA/lint and reproducible packaging; inspect every result. No personal Chrome extension or household HA deployment was performed.

The browser room and HA monitor are separate. Browser execution/sleep limits remain. Both HA live gates must stay false, no real devices may sound, and there is no verified horn adapter or room-to-HA health bridge. For eventual commissioning, first phone alarms go to all enrolled iPhones and physical outputs only to affected locations. Full operating and qualification rules are in the contract and ADRs.

`ignored-resources/` and `work/` must remain ignored. Private room/HA working files are in `ignored-resources/private-config/`. Verified old private-history backups are in `ignored-resources/backups/`; preserved old working files and Git metadata are also under ignored resources. Never restore that history into the public Git object graph. The temporary private GitHub bootstrap repository was deleted after public publication and local backup verification; no deletion or permission request remains to repeat. The deletion confirmation is local evidence, not a reason to reopen authentication.

The private publication criteria file is `ignored-resources/backups/private-publication-criteria.json`; use it locally for history/tree scans without printing or copying its literal private terms into public tests, docs or logs. Public config defaults and archives must contain no household coordinates, enrollments, credentials or device IDs. User-managed global skills are canonical in the user's Skillz directory and exposed by symlinks; do not install independent global copies of the project companion skill.

## Suggested skills

- `review`: independent standards/specification axes and fresh immutable-candidate adversarial gate; preserve actual evidence and fix supported findings through nits.
- `docs-sync`: synchronize the public documentation index after handoff, contract and guide changes.
- Project `skills/situareness-sources/SKILL.md`: maintain official-source evidence and supported local resource/configuration changes; the research catalog is not runtime input.
- `handoff`: refresh this continuation state before quota exhaustion or a supervisor change. Keep durable plans/reports under `docs/` as the user requested.
