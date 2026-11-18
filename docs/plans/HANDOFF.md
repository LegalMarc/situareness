# Supervisor handoff

Snapshot: November 18, 2026 UTC (November 17 in US Eastern time). Resume from live Git state, not an assumption that the latest checkpoint passed review.

## Continuation update: November 18 thirty-second Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `14b5b04` (`run_id`: `20261118T183557Z-2cfe8f`, 202.9s standards) reported **0 Critical, 0 High, and 0 code defects**, leaving 4 doc/notice findings (`DOC-01` Medium, `DOC-02` Low, `DOC-03` Low, `NOTE-01` Nit).

All 4 findings were resolved cleanly in Round 32 (`custom_components/situareness/__init__.py`, `docs/ha/README.md`, and `home-assistant/README.md`):
- **`DOC-01` & `DOC-02`**: Removed the stale duplicate bullets in `docs/ha/README.md` (describing `Store.path` tail-first, chunked binary `save_id` verification accurately) and `home-assistant/README.md` (documenting `outbox_overflow` clearing on the first poll whose new plans fit, without any 15-minute post-overflow hold).
- **`DOC-03`**: Restored self-contained retry bounds (`MAX_ATTEMPTS = 3`, 15-minute `MAX_AGE`, `100` attempts/poll, `30`-second deadline, saved per 10-target group) and the official cancellation-latency caveat (`Official cancellation is learned only on a later poll`) in the shipped `home-assistant/README.md` bundle guide.
- **`NOTE-01`**: Interpolated `max_age_mins` (`MAX_AGE`) into the remaining `"age"` `expired_unsent` notification literal in `_sync_degraded_notification()`.

Verification on the repaired candidate: `run_gates.py` (`220` total tests: `44` Node + `134` stdlib `-W error` HA + `7` skill + `22` Chromium Playwright + `13` real HA, plus Ruff lint/format), deterministic packaging, live anonymous smoke, and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117` and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 thirty-first Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `aab5fb1` (`run_id`: `20261118T182230Z-b16dc5`, 381.8s standards and 297.0s specification) reported **0 Critical and 0 High findings**, leaving 6 unique findings (`SIT-M1` Medium, `SIT-R01` Medium contract availability note, `SIT-R02` Low, `SIT-R03` Low, `SIT-N1` Low, `SIT-R04` Nit).

All 6 findings were resolved cleanly in Round 31 (`custom_components/situareness/__init__.py`, `docs/spec/o3-mvp.md`, `docs/CONTEXT.md`, `docs/ha/README.md`, `home-assistant/README.md`, and `tests/ha/test_coordinator.py`):
- **`SIT-M1`**: Added `"cancelled"` to `VALID_EXPIRY_REASONS` and `_sync_degraded_notification()` `cause_labels`, and emitted `{"expired": True, "reason": "cancelled"}` outcomes + `expired_unsent` count increments when `_migrate_outbox_with_index()` drops pending outbox items whose incident transitioned to `"cancelled"`, with unit test coverage.
- **`SIT-R01`**: Documented in `docs/spec/o3-mvp.md` (§Bounded storage) that protecting all cancellation components across up to 10 configured states is an intentional fail-closed CAP-evidence trade-off rather than evicting cancellation tombstones.
- **`SIT-R02` & `SIT-R03`**: Switched `_queue_outbox_plans()` to continue first-fit queueing for smaller non-empty plans after a larger plan overflows (`o3-mvp.md#home-assistant`), fixed `_degraded_health()` to scan `record_map`, and updated non-degraded `_stopped_health()` to surface persisted `quarantined_count`, `cancellation_uncertain`, and `partial`, with unit tests for both.
- **`SIT-N1` & `SIT-R04`**: Factored the shared live/shadow `outbox_overflow` notification builder and interpolated `MAX_AGE`/`MAX_ATTEMPTS` constants in `_sync_degraded_notification()`, consolidated repeated bounds prose in `docs/ha/README.md` and `home-assistant/README.md` to link to `docs/spec/o3-mvp.md#home-assistant`, and clarified `outbox_overflow` pre-drain service-call persistence in `docs/CONTEXT.md`.

Verification on the repaired candidate: `ruff check`/`ruff format --check` (12 files), `44` Node, `134` stdlib `-W error` HA, `7` skill, `22` Chromium Playwright, and `13` real HA = `220` total tests, deterministic packaging (`9d54a200...` extension ZIP, `065d3c81...` HA ZIP), live anonymous smoke (`2026-11-18T18:33:43.120Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: run full clean `run_gates.py`, commit/push to `wip/supervisor-handoff-20261117`, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 thirtieth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `30e7149` (`run_id`: `20261118T180246Z-dd8694`, 216.4s standards) reported **0 Critical findings**, 0 Specification findings above Low, and 6 unique findings (`F1` High, `F2`/`SIT-01`/`SIT-02` Low, `F3`/`SIT-03` Nit).

All 6 findings were repaired cleanly in Round 30 (`custom_components/situareness/__init__.py`, `custom_components/situareness/domain.py`, `extension/room.html`, `extension/room.js`, `home-assistant/README.md`, `docs/ha/README.md`, `tests/ha/test_domain.py`, `tests/ha/test_coordinator.py`, and `tests/browser/room.spec.js`):
- **`F1`**: Preserved `was_live=self.was_live` across `quarantine_ambiguous` and `_persist_degraded_poll` saves, and cleared carried-over shadow `actions` on non-cancelled `_quarantined_record` transitions during `activate=True` so shadow-seen alerts blocked or quarantined on the first live poll still activate on the next clean poll without re-delivering already-activated alerts.
- **`F2`**: Replaced full multi-MB JSON re-parsing in `_verify_store_save()` with a 4 KiB tail check for `"save_id"` plus a bounded chunked binary scan fallback (documented in `docs/ha/README.md`).
- **`F3`**: Updated `home-assistant/README.md` to state that `outbox_overflow` clears on the next successful poll whose new plans fit (or 15 minutes after the latest overflow if unrenewed).
- **`SIT-01` & `SIT-02`**: Tracked all triggering evidence reasons in `poll_evidence_reasons` so `_compute_degraded_latch` sets `acknowledge_rejected=True` even when an acknowledged cleared reason recurs under a higher-precedence reason, and added concurrent-overflow recovery guidance to `journal_lost` `situareness_degraded` notices when `cancellation_evidence_overflow` occurs simultaneously.
- **`SIT-03`**: Added `id="dashboard-divider" hidden` before `#dashboard-link` in `extension/room.html` and toggled it in `extension/room.js` when `context_dashboard` is null or unsafe.

Verification on the repaired candidate: `ruff check`/`ruff format --check` (12 files), `44` Node, `134` stdlib `-W error` HA, `7` skill, `22` Chromium Playwright, and `13` real HA = `220` total tests, deterministic packaging (`9d54a200...` extension ZIP, `248f9c57...` HA ZIP), live anonymous smoke (`2026-11-18T18:13:25.267Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: run full clean `run_gates.py`, commit/push to `wip/supervisor-handoff-20261117`, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-ninth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `27fb7a0` (`run_id`: `20261118T162534Z-c7cb5b`, 282.4s standards and 350.8s specification) reported **0 Critical findings**, 0 Standards findings above Low, and 7 unique findings (`F1` High, `F2`/`F3`/`SR-01`/`SR-02` Low, `SR-03`/`SR-04` Nit).

All 7 findings were repaired cleanly in Round 29 (`custom_components/situareness/domain.py`, `custom_components/situareness/__init__.py`, `home-assistant/README.md`, `docs/ha/README.md`, `tests/ha/test_domain.py`, and `tests/ha/test_coordinator.py`):
- **`F1`**: Guarded `safe_url(value)` against non-`str` inputs so non-string reference `@id` values cannot raise `AttributeError` in `urlparse()` and abort NWS polls, with regression coverage in `tests/ha/test_domain.py`.
- **`F2`**: Made poll-time degraded state latching, expiry, `outbox_overflow` transitions, and `_ack_cleared_*` resets transactional via pure `degraded_state` computation committed inside `_save()` only after `Store.async_save` and `_verify_store_save` succeed, verified on `FailingStore` in `tests/ha/test_coordinator.py`.
- **`SR-01` & `SR-02`**: Updated `_verify_store_save()` to parse the `Store.path` JSON envelope and check `data["save_id"] == save_id` independently of key ordering (documented in `docs/ha/README.md`), and passed `deliverable=0` from `_stopped_health()` to avoid synchronous `_count_deliverable` scans when stopped during `outbox_overflow`.
- **`F3`, `SR-03`, & `SR-04`**: Corrected `home-assistant/README.md` `outbox_overflow` auto-clear/15-minute window wording, compared parsed UTC `timestamp()` values when merging outbox `created` times across timezone offsets, and removed the wall-clock `elapsed < 0.5` assertion from `tests/ha/test_domain.py`.

Verification on the repaired candidate: `ruff check`/`ruff format --check` (12 files), `44` Node, `133` stdlib `-W error` HA, `7` skill, `21` Chromium Playwright, and `13` real HA = `218` total tests, deterministic packaging (`9ef4d967...` extension ZIP, `114a6d90...` HA ZIP), live anonymous smoke (`2026-11-18T17:58:14.319Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: run full clean `run_gates.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-eighth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `62337c2` (`run_id`: `20261118T160611Z-e864d7`, 313.6s standards and 346.7s specification) reported **0 Critical and 0 High findings**, with zero Specification findings above Low, leaving 6 unique findings (`HA-01` Medium, `HA-02` Low, `SPEC-L1` Low, `HA-03` Low/Nit, `DOC-01`/`DOC-N1` Low/Nit, `SPEC-N1` Nit).

All 6 findings were repaired cleanly in Round 28 (`custom_components/situareness/__init__.py`, `custom_components/situareness/domain.py`, `tests/ha/test_domain.py`, `tests/ha/test_coordinator.py`, and consolidated docs):
- **`HA-01` & `HA-02`**: Constructed `Store(hass, 1, prefix, private=True, atomic_writes=True, serialize_in_event_loop=False)` with isolated top-level collection copies in `_save`, updated `_verify_store_save` docstring for off-loop JSON serialization/atomic filesystem writes, widened at-least-once duplicate caveats across contract, READMEs, and `docs/CONTEXT.md` to cover crash, power loss, or save failure, and verified constructor args in `RecordingStore`.
- **`HA-03` & `SPEC-L1`**: Changed `CancellationEvidenceOverflow` fallback to `deepcopy(self.records)`, required parseable `timestamp(record["updated"])` in `_valid_persisted_store`, and bounded missing-`"updated"` records by poll observation time `now + 5m` in `cancellation_horizon(..., now=now)` with unit test coverage.
- **`SPEC-N1` & `DOC-01` / `DOC-N1`**: Qualified `quarantine_ambiguous`, `acknowledge_rejected`, and `expired_unsent` notifications with `" (Shadow mode: live output is disabled.)"` when live output is off (tested for shadow vs live), corrected `"setup-time store validation"` timing in `docs/spec/o3-mvp.md`, and consolidated duplicated normative prose in `docs/ha/README.md`, `home-assistant/README.md`, and `docs/reference/cap-cancellation.md` into concise operator/CAP summaries linking to `docs/spec/o3-mvp.md#home-assistant`.

Verification on the repaired candidate: `ruff check`/`ruff format --check` (13 files), `44` Node, `131` stdlib `-W error` HA, `7` skill, `21` Chromium Playwright, and `13` real HA = `216` total tests, deterministic packaging (`9ef4d967...` extension ZIP, `df8811b2...` HA ZIP), live anonymous smoke (`2026-11-18T16:20:37.855Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: run full clean `run_gates.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-seventh Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `0cb3656` (`run_id`: `20261118T155112Z-c46492`, 275.5s standards and 251.4s specification) reported **0 Critical and 0 High findings** and zero Standards findings above Nit, leaving 4 unique findings (`SIT-EXP-ACK-01` Medium, `SIT-ACK-COMMIT-02` Low, `TRUTH-01` Nit, `DOC-01`/`SIT-LOOP-03` Nit).

All 4 findings were repaired cleanly in Round 27 (`custom_components/situareness/__init__.py`, `tests/ha/test_coordinator.py`, `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md`):
- **`SIT-EXP-ACK-01`**: Updated `_compute_expired_unsent()` so `expired_unsent_at` advances to `max(existing_at, now).isoformat()` whenever a poll adds new expirations (`poll_expired > 0`), preventing an earlier `acknowledge_degraded_at` from silently clearing later unseen expirations on reload, and verified intermediate-timestamp rejection in unit tests.
- **`TRUTH-01`**: Set `output_blocked: True` whenever `quarantine_ambiguous` holds in `_degraded_health` and `_healthy_snapshot` (while keeping `evidence_degraded: False` outside evidence degraded modes) with unit test assertions.
- **`SIT-ACK-COMMIT-02` & `DOC-01` / `SIT-LOOP-03`**: Updated `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` to distinguish poll-time post-verification commits from load-time rejected/no-op ISO-8601 ack writes and initial store-error markers, document `output_blocked: true` during `quarantine_ambiguous` + latest-expiration `expired_unsent_at` semantics, and accurately describe bounded `<=10`-item qualification rechecks plus `O(n)` in-memory setup/outbox/snapshot bookkeeping on the event loop.

Verification on the repaired candidate: complete local gates (`44` Node, `130` stdlib `-W error` HA with zero asyncio slow-callback warnings, `7` skill, `21` Chromium Playwright, `13` real HA = `215` total), Ruff lint/format, deterministic packaging (`9ef4d967...` extension ZIP, `7b1751b5...` HA ZIP), live anonymous smoke (`2026-11-18T16:02:18.203Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-sixth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `4ea74ca` (`run_id`: `20261118T031956Z-d2125a`, 312.2s standards and 316.6s specification) reported **0 Critical, 0 High, and 0 Medium findings**, with zero live-gate/routing/privacy/persistence-compat/CAP-cancellation/bounds/overflow/ack/packaging/catalog/index defects, leaving 6 unique findings (`SIT-R1`/`SPEC-HA-02` Low, `SPEC-HA-01` Low, `SIT-R2` Nit, `SIT-R3` Nit, `SPEC-ROOM-01` Nit, `SPEC-HA-03` Nit).

All 6 findings were repaired cleanly in Round 26 (`custom_components/situareness/__init__.py`, `extension/room.js`, `tests/ha/test_coordinator.py`, `tests/browser/room.spec.js`, and documentation):
- **`SIT-R1` / `SPEC-HA-02`**: Added `_is_hass_stopping(hass)` to skip `_verify_store_save` when Home Assistant is in `stopping`/`final_write`/`stopped` states (avoiding false `UpdateFailed` on deferred `CoreState.stopping` writes), added a docstring documenting HA `Store` internals (`Store.path` and 512-byte tail layout), and added unit test coverage.
- **`SPEC-HA-01`**: Wrapped `hass.data` registration and `async_forward_entry_setups()` in `async_setup_entry()` so failed platform forwarding pops `hass.data`, dismisses `situareness_degraded`, and calls `await coordinator.async_stop()` before entering `setup_error` or retry, with unit test coverage.
- **`SIT-R2` & `SPEC-HA-03`**: Updated `_compute_expired_unsent()` to reset base count, anchor timestamp, reasons, and horizon once `now > existing_until` before adding new expirations, and tracked `self._last_quarantine_ambiguous` across polls so `resume_after_failed_unload()` restores active `"Situareness alert scope ambiguous"` notices on failed platform unload, with unit tests for both.
- **`SPEC-ROOM-01` & `SIT-R3`**: Prioritized `!enabled.length` ahead of `paused` in `extension/room.js` `renderStatus()` so paused/all-disabled collectors display neutral `"No sources enabled"` status (tested in `tests/browser/room.spec.js`), and rewrote `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` without private leading-underscore symbol names or implementation save counts, splitting dense bullets cleanly.

Verification on the repaired candidate: complete local gates (`44` Node, `130` stdlib `-W error` HA with zero asyncio slow-callback warnings, `7` skill, `21` Chromium Playwright, `13` real HA = `215` total), Ruff lint/format, deterministic packaging (`9ef4d967...` extension ZIP, `62b29da3...` HA ZIP), live anonymous smoke (`2026-11-18T15:40:26.722Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-fifth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `18342bc` (`run_id`: `20261118T025653Z-90db5a`, 240.5s standards and 276.3s specification) reported **0 Critical and 0 High findings**, and zero live-gate/routing/privacy/CAP-cancellation/bounds/store-schema/stop-cancellation/room/INDEX defects, leaving 8 unique findings (`HA-UNLOAD-01` Medium, `SR-01` Medium, `HA-SETUP-02`/`SR-03` Low, `HA-PERSIST-03` Low, `HA-RETRY-04` Low, `DOC-CTX-05`/`SR-02` Low, `SR-04` Nit, `TEST-NIT-06` Nit).

All 8 findings were repaired via `ha-repair` (`775aa2e8`) and supervisor integration (`tests/ui/helpers.test.js`, `asyncio.to_thread` in `tests/ha/test_coordinator.py` `BaseCoordinator._exec`, and doc/report updates):
- **`SR-01`**: Added tail `save_id` verification (`_verify_store_save` via `async_add_executor_job`, validated in `_valid_persisted_store`) after `Store.async_save` and proved against real HA 2026.11.1 `0o500` `.storage` that swallowed `WriteError` fails the poll (`UpdateFailed`) before notify service calls while preserving prior state.
- **`HA-PERSIST-03`**: Replaced pre-save mutating expired updates with pure `_compute_expired_unsent()`, committing `records`, `outbox`, `outcomes`, `last_degraded_poll`, `expired_unsent*`, `acknowledge_rejected`, and `entry.data` only after `_save` and `_verify_store_save` succeed.
- **`HA-UNLOAD-01` & `HA-SETUP-02` / `SR-03`**: Added `resume_after_failed_unload()` when `async_unload_platforms()` returns `False` or raises, and deduplicated `SETUP_RETRY` state listeners via `_SETUP_RETRY_UNSUBS` across repeated failed setup retries and entry removal.
- **`HA-RETRY-04` & `SR-04`**: Added `"exhausted"` to `VALID_EXPIRY_REASONS` / `delivery.expiry_reason(..., check_exhausted=True)` so 3-attempt delivery failures (`attempts >= MAX_ATTEMPTS`) latch `expired_unsent` with cause attribution, and sorted `_merge_consumed_acks` chronologically so older `entry.data` entries cannot regress `acknowledged_degraded_at`.
- **`DOC-CTX-05` / `SR-02` & `TEST-NIT-06`**: Qualified `docs/CONTEXT.md` on pre-delivery vs post-group save failures, updated `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` (`Thirteen tests` in real-HA docs), removed the inline drafting comment in `tests/ha/test_coordinator.py`, replaced the no-op `undefined ??` expression in `tests/ui/helpers.test.js`, and used `asyncio.to_thread` in `BaseCoordinator._exec` for zero slow-callback warnings.

Verification on the repaired candidate: complete local gates (`44` Node, `126` stdlib `-W error` HA, `7` skill, `21` Chromium Playwright, `13` real HA = `211` total), Ruff lint/format, deterministic packaging (`5434a239...` extension ZIP, `9b7357f9...` HA ZIP), live anonymous smoke (`2026-11-18T03:11:38.600Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-fourth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `bd617e2` (`run_id`: `20261118T022802Z-e54306`, 392.1s standards and 441.5s specification) reported **0 Critical, 0 High, and 0 Medium findings**, with zero live-gate/routing/privacy/CAP-cancellation/bounds/store-schema/ack/room-UI/catalog/index defects, leaving only 12 Low and Nit items (`SIT-L01`/`SPEC-01`, `SIT-L02`, `SIT-L03`, `SIT-L04`, `SIT-L05`, `SIT-L06`, `STD-01`, `SIT-N01`, `SIT-N02`, `SIT-N03`, `NIT-01`, `NIT-02`).

All 12 items were repaired via `ha-repair` (`775aa2e8`) and `browser-repair` (`50a99905`) plus supervisor integration, iteration-safe state-change/stopping refinements, and doc/report updates:
- **`STD-01` & `NIT-01`**: Extracted `_parse_and_collect_page()` in `collector.py` and dispatched per-page `json.loads` + `normalize` + lineage bookkeeping via `asyncio.to_thread` inside `fetch()`, and corrected `delivery.expired_by_age()`'s docstring.
- **`SIT-L01` / `SPEC-01`**: Added `delivery.expiry_reason()`, persisted/validated `expired_unsent_reasons` and outcome `"reason"` (`age`, `clock_rollback`, `target_removed`), keyed notifications on `reasons`, and attributed clock rollbacks and removed targets accurately in `situareness_degraded` notices.
- **`SIT-L02` & `SIT-L05`**: Guarded `_update_once` and `_queue_outbox_plans` with `_stopping` checks before post-fetch writes and delivery (`_stopped_poll_result()`), stopped the coordinator in `async_unload_entry()` before `async_unload_platforms()`, and attached an iteration-safe (`call_soon`) `entry.async_on_state_change` listener on failed first refresh to dismiss `situareness_degraded` if `SETUP_RETRY` abandons/fails (`not_loaded`/`setup_error`/`migration_error`, verified in real HA 2026.11.1).
- **`SIT-L03` & `SIT-L04`**: Retained higher-precedence active evidence reasons (`_EVIDENCE_REASON_RANK`) and non-`outbox_overflow` `degraded_at` across concurrent/intermittent evidence triggers, and skipped empty-`new_items` already-queued plans in `_queue_outbox_plans()` during `outbox_overflow`.
- **`SIT-N02`, `NIT-02`, `SIT-N03`, `SIT-L06`, & `SIT-N01`**: Removed dead `staticMethod`/wrapper/unused-return code in `__init__.py`, removed unread `storage_truncated` fallback in `extension/background.js`, aligned `extension/room.js` (`freshnessFor()`) with `helpers.mjs` on `configured?.interval_minutes ?? source.interval_minutes`, corrected `docs/CONTEXT.md` on store-save `UpdateFailed` vs `situareness_degraded`, fixed `"latched;re-latching"`, and broke dense doc/spec bullets into scannable sub-bullets while preserving all anchors (`docs/ha/README.md` real-HA count updated to `Twelve`).

Verification on the repaired candidate: complete local gates (`44` Node, `121` stdlib `-W error` HA with zero asyncio slow-callback warnings, `7` skill, `21` Chromium Playwright, `12` real HA = `205` total), Ruff lint/format, deterministic packaging (`5434a239...` extension ZIP, `67cbfdde...` HA ZIP), live anonymous smoke (`2026-11-18T02:51:50.962Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-third Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `8637f5e` (`run_id`: `20261118T020354Z-a2c113`, 297.6s standards and 304.0s specification) reported **0 Critical findings**, 0 Medium findings, and zero live-gate/routing/privacy/CAP-cancellation/store-schema/ack-reuse/lifecycle/browser/packaging/catalog/index defects, leaving 5 unique findings (`HA-QA-01` High, `HA-COL-02` Low, `SIT-R1` Low, `SIT-R2` Low, `SIT-R3`/`HA-ACK-03` Nit/Low).

All 5 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor review, doc/report updates, and test-harness cleanup (`asyncio.sleep(0)` yield in `BaseCoordinator._exec`):
- **`HA-QA-01`**: Passed `quarantine_all` into `_bound_records()` (`domain.py`) and updated `_is_actionable_record()` so `quarantined`/`unconfirmed` records are protected only when `prior_state == "active"`, `action_history` is within the `15m` bridge window, or (`not quarantine_all and state == "quarantined"`), preventing poll-wide `quarantine_all` bursts over >1,000 `ineligible` events from raising `CancellationEvidenceOverflow` and latching a 7-day block (while still sorting `quarantined`/`unconfirmed` ahead of `ineligible` and testing recovery on the next clean poll).
- **`HA-COL-02`**: Added `MAX_FETCH_SECONDS = 50` in `collector.py` and wrapped the `MAX_PAGES = 50` pagination loop in `async with asyncio.timeout(MAX_FETCH_SECONDS):`, keeping the inner 25s per-page timeout and testing multi-page deadline enforcement.
- **`SIT-R1` & `SIT-R2`**: Offloaded `_strip_withheld_actions` (all 3 call sites) and `_select_deliverable_batch` prefiltering/sorting via `hass.async_add_executor_job`, synchronized the loop/executor split (including `collector.fetch()` HTTP/JSON and per-group `<=10`-item delivery rechecks), and updated save-count bounds across `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` (`up to 11 saves/poll normally, or up to 22 saves/poll when a near-capacity pre-drain runs a second delivery pass`).
- **`SIT-R3` / `HA-ACK-03`**: Aligned `_try_acknowledge()`'s degraded branch with its healthy branch (`exp_at_ts is not None and exp_at_ts <= ack_ts <= current_now`) so missing `expired_unsent_at` does not silently clear latched `expired_unsent`, and documented this across contract and READMEs.

Verification on the repaired candidate: complete local gates (`43` Node, `114` stdlib `-W error` HA with zero asyncio slow-callback warnings, `7` skill, `21` Chromium Playwright, `11` real HA = `196` total), Ruff lint/format, deterministic packaging (`823de6d0...` extension ZIP, `f9816a9d...` HA ZIP), live anonymous smoke (`2026-11-18T02:19:37.389Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-second Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `039ea07` (`run_id`: `20261118T014754Z-e43694`, 272.7s standards and 182.6s specification) reported **0 Critical/High findings** and zero live-gate/CAP-quarantine/cancellation/ack-rejection/offload/room/packaging defects, leaving 6 unique items (`SPEC-HA-01`/`HA-DOC-PAGES` Medium, `DOC-HA-02`/`HA-DOC-RETRY` Low, `HA-CORRUPT-CLEANUP` Low, `HA-PREDRAIN-LATENCY` Low, `HA-NOTIFY-RECOVERY` Nit, `HA-DUP-DISMISS` Nit).

All 6 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor review/refinements (`_finish_poll_delivery()` + `attempted_keys`/`exclude_keys` single-attempt-per-poll guard) and doc/report updates:
- **`SPEC-HA-01` / `HA-DOC-PAGES` & `DOC-HA-02` / `HA-DOC-RETRY`**: Raised `collector.MAX_PAGES` from `10` to `50` with 12-page/51-page tests, and aligned `docs/ha/README.md`, `home-assistant/README.md`, and `docs/spec/o3-mvp.md` to state `"three total attempts (MAX_ATTEMPTS = 3: one initial call plus up to two retries)"`.
- **`HA-CORRUPT-CLEANUP` & `HA-NOTIFY-RECOVERY`**: Captured `had_malformed_entry` before mutating `entry.data`, checked `_has_corrupt_store_backup` at startup when `persisted is None or persisted == {}` so `{}` replacement clears stale `.corrupt.*` backups on first save, and updated `malformed_store` notifications to instruct deleting any `.corrupt.*` backups alongside the store file.
- **`HA-PREDRAIN-LATENCY` & `HA-DUP-DISMISS`**: Added `_finish_poll_delivery()` using remaining `100 - attempts` budget within the shared `30s` deadline (excluding `attempted_keys` already tried during pre-drain so no failed retry fires twice in one poll), disclosed full-pre-drain next-poll queueing across docs, and removed duplicate notification dismissal in `async_unload_entry()`.

Verification on the repaired candidate: complete local gates (`43` Node, `109` stdlib `-W error` HA, `7` skill, `21` Chromium Playwright, `11` real HA = `191` total), Ruff lint/format, deterministic packaging (`823de6d0...` extension ZIP, `04e583f8...` HA ZIP), live anonymous smoke (`2026-11-18T01:59:56.086Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twenty-first Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `e13efc8` (`run_id`: `20261118T011756Z-942760`, 335.6s standards and 324.1s specification) reported **0 Critical findings** and zero live-gate/routing/privacy/CAP-quarantine/outbox-overflow/async-offload/room/packaging defects, leaving 9 unique findings (`HA-BOUND-01` Medium, `SPEC-HA-01` Medium, `HA-BOUND-02` Low, `HA-NOTE-01`/`SPEC-HA-02` Low, `SPEC-HA-03` Low, `HA-OUT-01` Low, `DOC-HA-01` Low, `HA-STORE-01` Low, `HA-JL-01` Nit).

All 9 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor review/refinements and contract/README/report updates:
- **`HA-BOUND-01` & `HA-BOUND-02`**: Extracted `_is_actionable_record()` in `domain.py` `_bound_records()` so absent `quarantined`/`unconfirmed`/15m-bridge `ended_or_absent` (`actions`) records stay protected ahead of `ineligible` bursts, while excluding non-actionable hidden `superseded` placeholders outside actionable/cancellation groups (and preventing >15m `superseded` history from lingering in `protected`).
- **`SPEC-HA-01`**: Removed the raw 1,000-feature abort in `collector.py` (`fetch()`) while preserving `feature_count` (`source_count`), `MAX_PAGES`, `MAX_BYTES`, and `MAX_QUARANTINE_IDS` bounds and testing 1,005-feature collector bursts end-to-end through `_async_update_data()`.
- **`HA-NOTE-01` / `SPEC-HA-02`**: Updated `_sync_degraded_notification()` rejected-ack text (standalone `expired_count > 0` and concurrent `quarantine_ambiguous`) to name premature (`< expired_unsent_at`), missing `expired_unsent_at`, and already-consumed causes plus `expired_unsent_at <= acknowledge_degraded_at <= reload time`.
- **`SPEC-HA-03` & `HA-JL-01`**: Added `VALID_RECORD_STATES` schema validation in `_valid_persisted_store()`, rejected future `journal_lost_at > detect_now` with `MAX_TIMESTAMP` horizon clamping, extracted `_clear_degraded_state()`, and cleaned up unused `batch_expired` unpacking.
- **`HA-OUT-01`, `HA-STORE-01`, & `DOC-HA-01`**: Expanded `delivery.expired_by_age()` to surface unexhausted active/suspended-active targets dropped on clock rollback (`created > now`) or target invalidation, armed `_needs_corrupt_cleanup` with warning logs until `.corrupt.*` unlink succeeds (entering `journal_lost` when an already-recovered entry loses its main store), and restored delivery-semantics disclosures across `docs/ha/README.md`, `docs/spec/o3-mvp.md`, and `home-assistant/README.md`.

Verification on the repaired candidate: complete local gates (`43` Node, `105` stdlib `-W error` HA, `7` skill, `21` Chromium Playwright, `11` real HA = `187` total), Ruff lint/format, deterministic packaging (`823de6d0...` extension ZIP, `790df37b...` HA ZIP), live anonymous smoke (`2026-11-18T01:42:19.648Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 twentieth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `698fe14` (`run_id`: `20261118T004922Z-f1724a`, 248.1s standards and 294.2s specification) reported **0 Critical findings** and zero live-gate/routing/privacy/CAP/quarantine/store/offload/room/packaging defects, leaving 5 unique items (`F1`/`HA-SNAP-01` High/Medium, `F2` Medium, `F3` Low, `HA-ACK-02` Low, `HA-DEG-03` Low).

All 5 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor review/refinements and contract/README/report updates:
- **`F1` / `HA-SNAP-01`**: Switched `_healthy_snapshot()` to safe `.get()` / membership lookups falling back to `"ineligible"` and per-event `qualify()` reasons when `_bound_records()` evicts unprotected current `ineligible` items past 1,000 records, and moved `_healthy_snapshot()` inside `_update_once()`'s `try:` block.
- **`F2` & `F3`**: Persisted validated `expired_unsent`, `expired_unsent_at`, and `expired_unsent_until` in store (`7`-day `MAX_ACCEPTANCE_AGE` latch from latest expiration or cleared on reload via valid unconsumed `expired_unsent_at <= acknowledge_degraded_at <= load_now`), surfaced latched counts across healthy, degraded, and `_stopped_health()` snapshots, kept pre-fetch `_sync_degraded_notification()` aligned with `self.expired_unsent`, and keyed notification state tuples on exact integer `expired_count`.
- **`HA-ACK-02`**: Tracked `_ack_cleared_reason` alongside `_ack_cleared_on_load` so Poll 1 marks `acknowledge_rejected: true` only when the cleared reason itself re-latches, not on unrelated new degradations (`outbox_overflow`, `malformed_cancellation`, etc.).
- **`HA-DEG-03`**: Preserved feed cancellation trigger precedence (`conflicting_cancellation` / `malformed_cancellation`) over concurrent `CancellationEvidenceOverflow` while enforcing `max(until, fallback_until)` and documenting concurrent-overflow history/horizon recovery guidance.

Verification on the repaired candidate: complete local gates (`43` Node, `99` stdlib `-W error` HA, `7` skill, `21` Chromium Playwright, `11` real HA = `181` total), Ruff lint/format, deterministic packaging (`823de6d0...` extension ZIP, `8510ccca...` HA ZIP), live anonymous smoke (`2026-11-18T01:10:34.474Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`. Next: commit/push to `wip/supervisor-handoff-20261117`, refresh clean-HEAD logs, and run Opus `axes` + fresh `adversarial` reviews on the immutable candidate. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 nineteenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `6bd9bc9` (`run_id`: `20261118T002932Z-5e3623`, 361.5s standards and 230.3s specification) reported **0 Critical, 0 High, and 0 Medium standards findings**, and zero live-gate/routing/privacy/CAP/quarantine/store/ack/offload/room/packaging defects, leaving 5 items (`SPEC-HA-01` Medium, `SIT-PERF-01` Low, `SIT-AVAIL-01` Low, `SPEC-HA-02` Nit, `DOC-01` Nit).

All 5 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/README/report updates:
- **`SPEC-HA-01`**: Added `expired_by_age()` in `delivery.py`; surfaced `expired_unsent` (`partial: True`), `"expired": True` outcomes, and `situareness_degraded` notifications when active queued targets (including first attempts) age past the 15-minute `MAX_AGE` window; synchronized `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md`.
- **`SIT-PERF-01`**: Coalesced expired-item pruning and post-delivery persistence in `_deliver_outbox_batch()` into at most one save per 10-target group and documented the per-item instruction serialization cost (~10KB/target, up to ~12 saves/poll under 5,000-target load).
- **`SIT-AVAIL-01`**: Excluded pure `ineligible` non-cancellation items (without action history or cancellation evidence) from `protected` in `_bound_records()` so multi-state bursts do not crowd out retained tombstones or latch 7-day `cancellation_evidence_overflow`.
- **`SPEC-HA-02` & `DOC-01`**: Documented automatic first-save cleanup of stale `.corrupt.*` backups after `malformed_store` recovery, and removed the `"non-Cancel"` qualifier from `quarantine_ambiguous` in `home-assistant/README.md`.

Next: run complete local gates (`43` Node, `95` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `177` total), deterministic packaging (`823de6d0...` extension, `7c78b35a...` HA), live anonymous smoke (`2026-11-18T00:44:36.350Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 eighteenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `c132758` (`run_id`: `20261118T001451Z-588b6e`, 323.9s standards and 386.0s specification) reported **0 Critical, 0 High, and 0 Medium findings across both axes**, leaving only 6 small Low/Nit findings (`SR-DOC-01` Low, `SR-DOC-02` Low, `SPEC-01`/`SR-DOC-03` Low/Nit, `SR-MAINT-01`/`STD-01` Nit, `STD-02` Nit, `DOC-01` Nit).

All 6 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/context/README/report updates:
- **`SR-DOC-01` & `DOC-01`**: Clarified in `docs/CONTEXT.md` that evidence/storage degradations block **all** output while `outbox_overflow` withholds only overflowing plans, and changed bare `"acknowledgement"` to `"recipient alert acknowledgement"` in `docs/ha/README.md` and `home-assistant/README.md`.
- **`SR-DOC-02`**: Differentiated `_sync_degraded_notification()` recovery copy by `degraded_reason` (`journal_lost`, `cancellation_evidence_overflow`, and feed-triggered `malformed_cancellation`/`conflicting_cancellation`) and synchronized `docs/spec/o3-mvp.md`.
- **`SPEC-01` / `SR-DOC-03` & `STD-02`**: Removed `resolve_candidates()` and the unreachable `len(events) > 1000` check from `collector.py` `fetch()` so `fetch()` runs only async HTTP pagination and JSON/feature normalization while candidate resolution runs solely off-loop in `_resolve_and_scan_candidates()`.
- **`SR-MAINT-01` / `STD-01`**: Removed dead `SituarenessCoordinator._migrate_and_prune_outbox` and unused keyword parameters (`planned_count`, `delivery_attempts`, `delivery_failures`) on `_persist_degraded_poll`.

Next: run complete local gates (`43` Node, `93` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `175` total), deterministic packaging (`823de6d0...` extension, `546c8cb7...` HA), live anonymous smoke (`2026-11-18T00:25:07.117Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 18 seventeenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `05a979e` (`run_id`: `20261117T234711Z-2fcb85`, 408.5s standards and 339.1s specification) reported **0 Critical, 0 High, 0 Medium specification findings, and zero live-gate/store-roundtrip/journal/lifecycle/recorder/packaging/room/index defects**, leaving 7 findings (`SR-01` / `SR-02` Medium, `SR-03` / `SR-04` / `SR-ACK-01` / `SR-ACK-02` Low, and `SR-CFG-01` Nit).

All 7 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/reference/README/report updates:
- **`SR-01`**: Restricted supersession and lineage-grouping authority strictly to `Actual` `Update` and `Cancel` messages (`_actual_superseding()`) across `resolve_candidates()` and `reconcile()` so non-`Actual` (`Test`/`Exercise`/`System`) or `Alert` messages cannot supersede referenced `Actual` alerts or migrate pending outbox items.
- **`SR-02`**: Clarified across `docs/spec/o3-mvp.md`, `docs/reference/cap-cancellation.md`, and `home-assistant/README.md` that malformed/oversized non-`Cancel` features quarantine `feature_id` and absent, unreferenced prior records in `valid_refs` (`[feature_id, *absent_unreferenced_valid_refs]`) so raw references on a non-`Cancel` feature cannot suppress valid current candidates.
- **`SR-03`**: Added bounded `consumed_acknowledgements` history (`<= 100` valid ISO timestamps merged via `_merge_consumed_acks()` across `entry.data` and store without downgrade on reload or save).
- **`SR-04`**: Offloaded all post-fetch coordinator CPU work (`_valid_persisted_store`, `_resolve_and_scan_candidates`, `reconcile`, `_migrate_outbox_with_index`, `_build_planned_items`, `_count_deliverable`) via `hass.async_add_executor_job`, and documented the boundary against async `collector.fetch()`.
- **`SR-ACK-01`, `SR-ACK-02`, & `SR-CFG-01`**: Preserved `_config_ack_rejected` across mid-session `degraded_until` and `outbox_overflow` auto-clears, merged rejected-ack notices into concurrent `quarantine_ambiguous` notifications, and rejected C0, DEL (`U+007F`), and C1 (`U+0080–U+009F`) control characters in `config.validate()`.

Next: run complete local gates (`43` Node, `93` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `175` total), deterministic packaging (`823de6d0...` extension, `81636df8...` HA), live anonymous smoke (`2026-11-18T00:05:57.899Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 sixteenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `3b35e7c` (`run_id`: `20261117T232125Z-6894d0`, 359.6s standards and 349.8s specification) reported **0 Critical, 0 High, 0 Medium specification findings, and zero live-gate/routing/privacy/shadow/room/packaging defects**, leaving 7 findings (`SIT-R01` Medium, `SPEC-HA-01` / `SIT-R02` / `SIT-R03` / `SPEC-HA-02` Low, and `SIT-R04` / `SPEC-HA-03` Nit).

All 7 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/README/index/report updates:
- **`SIT-R01` & `SPEC-HA-01`**: Defined `MAX_TIMESTAMP` (`9998-12-31T23:59:59+00:00`), bounded each record's retention timestamps in `cancellation_horizon()` at `min(ts, updated + 5m)` so future-dated invalid Cancels expire cleanly after 7 days (`NOW + 5m + MAX_ACCEPTANCE_AGE`), and clamped `cancellation_horizon()`, `_bound_records()`, and `_latch_degraded()` horizons at `MAX_TIMESTAMP` so reload validation never enters `malformed_store` on late-`9998` inputs.
- **`SIT-R02`**: Offloaded `reconcile` and `_valid_persisted_store` via `hass.async_add_executor_job`, scoped `_deliverable_count` and batched `_deliver_outbox_batch` `qualify()` calls to queued active IDs, and tightened the 1,000-record `reconcile` benchmark to `< 0.5s`.
- **`SIT-R03`**: Sorted deliverable outbox batches with never-attempted (`attempts == 0`) targets ahead of retries while preserving FIFO order within each tier.
- **`SPEC-HA-02` & `SPEC-HA-03`**: Surfaced `acknowledge_rejected: true` and `situareness_degraded` on invalid/naive/over-length/future `acknowledge_degraded_at` values even while healthy (`_healthy_snapshot` / `_stopped_health`), consumed valid future ISO timestamps without failing setup, and removed the inaccurate 15-minute expiry clause from `outbox_overflow` notifications.
- **`SIT-R04`**: Synchronized `docs/INDEX.md` anchors with all current headings in `docs/spec/o3-mvp.md` and `home-assistant/README.md`.

Next: run complete local gates (`43` Node, `91` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `173` total), deterministic packaging (`823de6d0...` extension, `bca74a2b...` HA), live anonymous smoke (`2026-11-17T23:41:13.215Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 fifteenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `1078764` (`run_id`: `20261117T230054Z-57bc4c`, 286.1s standards and 394.5s specification) reported **0 Critical, 0 High, 0 Medium specification findings, and zero browser/packaging/catalog/gate/routing/overflow/store/lifecycle defects**, leaving only 4 small HA/documentation findings (`HA-01` Medium, `HA-02` Low, `SPEC-01`/`HA-04` Low/Nit, `HA-03`/`NIT-01` Nit).

All 4 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/README/report updates:
- **`HA-01`**: Bounded `domain.timestamp()` to UTC years `2–9998` and added `OverflowError` clamping in `cancellation_horizon()` and `_bound_records()` so far-future year-`9999` or year-`0001` timestamps fail closed or quarantine per-feature/per-lineage without wedging `reconcile`/`UpdateFailed` once the component leaves the feed, with domain and coordinator regression tests.
- **`HA-02`**: Updated `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` to match `_deliver_outbox_batch()` (`persisting once before a 10-target group when expired items are pruned and once after each completed 10-target group`).
- **`SPEC-01` / `HA-04` & `HA-03` / `NIT-01`**: Removed unused `now=None` from `config.validate(raw)`, removed the `len(ack) > 100` setup rejection from `config.validate(raw)` so over-length `acknowledge_degraded_at` strings pass setup and trigger runtime `acknowledge_rejected: true` in `_try_acknowledge()` while keeping monitoring online, and updated `docs/spec/o3-mvp.md`, READMEs, and tests.

Next: run complete local gates (`43` Node, `90` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `172` total), deterministic packaging (`823de6d0...` extension, `0b2f7ec3...` HA), live anonymous smoke (`2026-11-17T23:16:55.849Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 fourteenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `c81fb7f` (`run_id`: `20261117T224454Z-a299b9`, 217.6s standards and 373.9s specification) reported **0 Critical, 0 High, and zero room/catalog/quarantine/overflow/lifecycle defects**, leaving only 3 unique HA/documentation findings (`HA-ACK-01`/`SPEC-HA-01`/`DOC-HA-02` Medium/Low, `HA-DOC-02` Low, `SPEC-HA-03` Low).

All 3 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/README/report updates:
- **`HA-ACK-01` / `SPEC-HA-01` / `DOC-HA-02`**: Restricted `config.validate()` to basic string/length/control-character checks on `acknowledge_degraded_at` and handled unparseable/timezone-naive/future/premature/reused strings cleanly inside `SituarenessCoordinator._try_acknowledge()` (keeping monitoring online, setting `acknowledge_rejected: true`, updating `situareness_degraded`, and recording valid ISO timestamp consumption in `entry.data` and store so retries cannot auto-apply it later), with full unit (`c.validate` -> coordinator) and real-HA reload coverage.
- **`HA-DOC-02`**: Clarified in `home-assistant/README.md` that exceeding 5,000 quarantined non-Cancel IDs sets poll-scoped `quarantine_ambiguous` while `malformed_cancellation`/`conflicting_cancellation` apply to unrecoverable or over-cap `Actual Cancel` / conflicting cancellation evidence.
- **`SPEC-HA-03`**: Restricted `dropped_groups` in `domain.py` `_bound_records()` to `eid in protected` so unprotected old history cannot extend `dropped_horizon` / `degraded_until`, and verified an unprotected 30-day record does not inflate `dropped_horizon`.

Next: run complete local gates (`43` Node, `89` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `171` total), deterministic packaging (`823de6d0...` extension, `026b10b4...` HA), live anonymous smoke (`2026-11-17T22:57:35.151Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 thirteenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `6236ea8` (`run_id`: `20261117T223104Z-7fe723`, 215.8s standards and 202.2s specification) reported **0 Critical, 0 High, and zero room/live-gate/routing/quarantine/overflow defects**, leaving 7 HA/documentation findings (`SIT-HA-ACK-01`/`SIT-HA-02` Medium/Low, `SIT-DOC-01` Medium, `SIT-HA-CANCEL-02` Low, `SIT-HA-STORE-03` Low, `SIT-DOC-RETRY-04` Low, `SIT-NIT-05` Nit, `SIT-DOC-03` Nit).

All 7 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor bundle-doc/contract/report updates:
- **`SIT-HA-ACK-01` & `SIT-HA-02`**: Preserved initial `degraded_at` while extending `degraded_until` across unchanged degraded reasons, exposed `acknowledge_rejected` across snapshots and `situareness_degraded` notifications (including Poll 1 re-latch after load-time acknowledgement on a still-active trigger), and explicitly documented `>= degraded_at` and trigger-clear prerequisites.
- **`SIT-DOC-01`, `SIT-DOC-RETRY-04`, `SIT-NIT-05`, & `SIT-DOC-03`**: Made `home-assistant/README.md` fully self-contained for the HA ZIP bundle (replacing external `../docs/` links), documented degraded-mode `last_degraded_poll` retry-age preservation up to 7+ days, added `event_count`/`source_feature_count`/`acknowledge_rejected` to `docs/ha/README.md`, and documented expired-item pruning saves alongside per-10-target-group delivery persistence.
- **`SIT-HA-CANCEL-02` & `SIT-HA-STORE-03`**: Propagated external outer-task `asyncio.CancelledError` (`current_task.cancelling() > 0`) during `async_stop()`, and narrowed `store.async_load()` catch in `async_setup_entry()` so internal `TypeError`/`KeyError` raise `ConfigEntryNotReady` instead of latching `malformed_store`.

Next: run complete local gates (`43` Node, `89` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `171` total), deterministic packaging (`823de6d0...` extension, `b50926c6...` HA), live anonymous smoke (`2026-11-17T22:41:41.061Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 twelfth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `3d18093` (`run_id`: `20261117T221552Z-4d6117`, 309.4s standards and 308.7s specification) reported **0 Critical, 0 High, and 0 Medium findings**, leaving 7 small Low/Nit findings (`SIT-HA-01`/`HA-JLOST-01`, `HA-NOTIFY-01`, `SIT-HA-02`, `SIT-HA-03`, `SIT-TOOL-01`, `SIT-DOC-01`, `SIT-HA-04`) plus 1 advisory capacity note (`HA-CAP-01`).

All 7 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor tool/doc/report updates:
- **`SIT-HA-01` & `HA-JLOST-01`**: Extended `journal_lost` `degraded_until` from `max(lost_ts, detect_now) + MAX_ACCEPTANCE_AGE`, rotated stale `journal_lost_at` older than 7 days, cleared `journal_lost_at` on post-fetch saves (`preserve_lost_at=True` only on pre-fetch safety save), non-empty store loads, and `malformed_store` entry.
- **`HA-NOTIFY-01` & `SIT-HA-04`**: Switched `_sync_degraded_notification()` selection strictly to `degraded_reason` (so legacy non-`malformed_store` entries with `degraded_until: None` receive `degraded_until`/`acknowledge_degraded_at` guidance instead of `.storage` instructions) and qualified degraded notifications when `live(self.config)` is false.
- **`SIT-HA-02` & `SIT-HA-03`**: Rejected persisted outboxes over 5,000 items in `_valid_persisted_store()` as `malformed_store` (removing silent truncation), and removed private `store._async_migrate_func` patching while retaining `NotImplementedError`/`UnsupportedStorageVersionError` handling.
- **`SIT-TOOL-01` & `SIT-DOC-01` / `HA-CAP-01`**: Added timeout cancellation guards (`stopped` + `smokePromise.catch`) in `tools/live-browser-smoke.mjs`, formatted `docs/spec/o3-mvp.md#home-assistant` as structured bulleted subsections (including the `HA-CAP-01` multi-state headroom note), and slimmed `docs/ha/README.md`, `home-assistant/README.md`, and `docs/CONTEXT.md` to concise links.

Next: run complete local gates (`43` Node, `88` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `170` total), deterministic packaging (`823de6d0...` extension, `d7bc1dad...` HA), live anonymous smoke (`2026-11-17T22:27:51.635Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 eleventh Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `ad93ead` (`run_id`: `20261117T214931Z-ca8e85`, 318.6s standards and 291.6s specification) reported **0 Critical, 0 High, and 0 CAP/qualification/quarantine/lifecycle/browser/packaging/catalog findings**, leaving 7 unique Home Assistant, test, and doc findings (`SIT-R1`/`HA-OVF-01` Medium, `HA-STORE-01` Low–Medium, `SIT-R2` Low, `SIT-R3` Low, `HA-IO-01` Low, `SIT-R4` Nit, `SIT-R5` Nit).

All 7 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/doc/report updates:
- **`SIT-R1` / `HA-OVF-01`**: Switched `outbox_overflow` to the 15-minute `MAX_AGE` horizon without advancing item age via `last_degraded_poll`, continued bounded `100`-target/poll queued delivery (`evidence_degraded: False`, `output_blocked: False`, accurate `deliverable_count`/`suspended_count`/`withheld_count`, active `active_count`), and auto-cleared `outbox_overflow` on the first poll where capacity fits.
- **`HA-STORE-01`**: Rejected storage major/minor version mismatches via `_async_migrate_func` (`ValueError`) and caught `NotImplementedError` alongside `UnsupportedStorageVersionError` as `malformed_store` without altering on-disk files, verified by an additional real-HA test (`11 passed`).
- **`SIT-R2` & `SIT-R4`**: Carried stripped `plans` on `CancellationEvidenceOverflow` to surface accurate `withheld_count`, and updated `situareness_degraded` notifications to distinguish `outbox_overflow`, `degraded_until` + `acknowledge_degraded_at` + reload recovery, and `.storage` manual repair for `malformed_store`.
- **`SIT-R3`**: Enforced non-future `acknowledge_degraded_at` in `config.validate(raw, now=None)` and consumed non-matching/premature load-time acknowledgements (`self.acknowledged_degraded_at = ack`) so stale config entries cannot clear future degradations.
- **`HA-IO-01`**: Batched expired-item pruning and post-delivery persistence in `_deliver_outbox_batch()` to save once per completed 10-target delivery group.
- **`SIT-R5`**: Checked single-`deepcopy` behavior deterministically (`patch.object(d, "deepcopy")`) with a relaxed `<5.0s` wall-clock sanity bound in `tests/ha/test_domain.py`, and synchronized docs/READMEs.

Next: run complete local gates (`43` Node, `87` stdlib HA, `7` skill, `21` Chromium, `11` actual HA = `169` total), deterministic packaging (`823de6d0...` extension, `3a3b1a7e...` HA), live anonymous smoke (`2026-11-17T22:12:43.675Z`, HTTP 200 across NWS/USGS/BBC), and `audit_private.py`, commit/push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, and run Opus `axes` + fresh `adversarial` reviews. Household outputs remain disabled and no commissioning occurred.

## Continuation update: November 17 tenth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `221ed9b` (`run_id`: `20261117T203507Z-d741fd`, 316.3s standards and 287.4s specification) reported **0 Critical, 0 High, and 0 CAP/cancellation, browser/UI, packaging, catalog, or live/shadow gate findings**, leaving 8 unique Home Assistant, test, and doc findings (1 Medium, 5 Low, 2 Nit).

All 8 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/doc/report updates:
- **`SIT-01` / `SPEC-HA-01`**: Implemented whole-plan atomic queueing in `_queue_outbox_plans()` up to `5,000` targets with conditional single-batch pre-drain (`deliverable_existing` headroom check) and `_strip_withheld_actions()` cleanup so only completely queued plans retain action fingerprints, and documented the ~1,500-target/15m delivery bound.
- **`SPEC-HA-02`**: Scoped quarantine to `[feature_id, *valid_refs]` whenever `feature_id` is extractable even when `properties` is non-object/`null`.
- **`STD-HA-03` / `SIT-07`**: Added `PERSISTED_DEGRADED_REASONS` validation in `_valid_persisted_store()` and fixed operator precedence in coordinator `degraded_reason` restoration.
- **`SIT-02`**: Added `"withheld_count"` across coordinator health snapshots (`_healthy_snapshot`, `_stopped_health`, `_degraded_health`, `_persist_degraded_poll`) alongside queued `planned_count` and pre-drain delivery counters on initial `outbox_overflow`.
- **`SIT-03`**: Eliminated the double `deepcopy` in `domain.py` `reconcile()`, used `itertools.islice(..., 100)` in `_deliver_outbox_batch()`, replaced the unvalidated 5,001-phone overflow test with a validated 50-phone × 101-alert multi-plan test (eliminating asyncio slow-callback warnings), and added a `<0.5s` 1,000-record `reconcile` benchmark (`0.0221s` measured).
- **`SIT-04` & `SIT-05`**: Synchronized `docs/CONTEXT.md` and `docs/plans/primary-source-roadmap.md` with degraded/output-blocked mode and `situareness_degraded` notifications; consolidated normative CAP/degraded-mode rules into `docs/spec/o3-mvp.md#home-assistant` with concise operator summaries and cross-links in `docs/ha/README.md`, `home-assistant/README.md`, and `docs/reference/cap-cancellation.md`.
- **`SIT-06`**: Removed `ImportError`/`hasattr`/`isinstance` test-compatibility shims from `custom_components/situareness/__init__.py` and moved default `persistent_notification` and mock `hass` attributes into `tests/ha/test_coordinator.py`.

The complete local gates passed: 43 Node, 87 stdlib HA (`-W error`, zero slow-callback warnings), 7 source-skill, 21 Chromium browser, and 10 actual-HA tests (168 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`823de6d0...` extension, `8829a299...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T21:44:06.766Z` with HTTP 200 across NWS (0 alerts), USGS (8 items), BBC World (27 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once both pass, run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** and **S1**.

## Continuation update: November 17 ninth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `c0a909c` (`run_id`: `20261117T194649Z-7a1803`, 329.5s standards and 390.8s specification) reported **0 Critical, 0 High, and 0 browser/UI/packaging/catalog/output-gate findings**, leaving 10 Home Assistant and documentation findings (3 Medium, 3 Low, 4 Nit).

All 10 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor contract/reference/report updates:
- **`SAF-01`**: Scoped non-`Cancel` malformed/oversized features with valid `feature_id` to `[feature_id, *valid_refs]` in `collector.py`, raised `situareness_degraded` on `quarantine_ambiguous` with clean recovery dismissal, and aligned `o3-mvp.md`, `cap-cancellation.md`, and HA READMEs.
- **`SPEC-HA-01`**: Preserved already-queued targets' action fingerprints on initial `outbox_overflow` latching so acknowledged reload recovery delivers the capped 5,000-target outbox cleanly instead of self-relatching on active alerts.
- **`SPEC-HA-02`**: Distinguished valid unreferenced continuing segments (`sent >= cancelled_at`, via persisted `cancelled_at`) so new qualifying actions plan as `active`, temporary ineligibility preserves continuing actions without false quarantine, superseded continuing records do not pollute `partial`, and repeating pre-cancellation actions stay withheld as `quarantined`.
- **`SPEC-HA-03`**: Added the `sent <= now + 5m` clock check to `cap_event_valid(event, now)` and graph/cancellation validation so future-dated `Actual Cancel` records isolate `uncertain_targets` without writing raw `lineage` edges or flipping to cancelled after clock catch-up.
- **`HLT-01`, `PRV-01`, & `CMP-01`**: Replaced timestamp-string equality in `_degraded_health()` with explicit `triggered_now`, `recoverable_prior_conflict`, and `quarantined_cancel_lineages` checks; passed `private=True` to `Store` on load/removal; passed `config_entry=entry` to `DataUpdateCoordinator.__init__`.
- **`MNT-01`, `DOC-01`, & `DOC-02`**: Reused `resolve_candidates` in `collector.py`, extracted `_deliver_outbox_batch` and `_healthy_snapshot` in `__init__.py`, split `o3-mvp.md` §Home Assistant into readable paragraphs, documented `conflicting_cancellation` vs `malformed_cancellation` for over-cap Cancels, and clarified suspended retry retention past uncertainty resolution in `docs/ha/README.md`.

The complete local gates passed: 43 Node, 85 stdlib HA (`-W error`), 7 source-skill, 21 Chromium browser, and 10 actual-HA tests (166 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`823de6d0...` extension, `bea4f884...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T20:31:57.387Z` with HTTP 200 across NWS (0 alerts), USGS (10 items), BBC World (25 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once both pass, run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** and **S1**.

## Continuation update: November 17 eighth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `a146710` (`run_id`: `20261117T192723Z-402b20`, 307.7s standards and 340.1s specification) reported **0 Critical and 0 High findings** and zero browser/UI/packaging/catalog/CAP-core/gate defects, leaving 8 unique findings (1 Medium, 4 Low, 3 Nit).

All 8 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor spec/reference/report updates:
- **`HA-ACK-01`**: Retained `journal_lost_at` in `entry.data` inside `_try_acknowledge()` so it clears only when `_save()` persists a non-degraded state, preserving acknowledgement recovery across failed first-poll retries.
- **`HA-STORE-01`**: Narrowed `store.async_load()` error handling in `async_setup_entry()` so JSON/value/type/key/unsupported-version errors latch `malformed_store` while transient `OSError` / permission errors raise `ConfigEntryNotReady` for retry.
- **`SIT-R2` & `HA-NOTIF-01`**: Keyed `_sync_degraded_notification` on `degraded_reason` alone and removed advancing timestamps from notification text to eliminate per-minute notification churn.
- **`SIT-R3` & `PERF-01`**: Added `has_corrupt_backup` and `_needs_corrupt_cleanup` so `_save()` clears `.corrupt.*` backups only once when needed.
- **`SIT-R1`, `DOC-HA-01`, `DOC-HA-02`, & `SIT-R4`**: Corrected `docs/ha/README.md` ambiguous-quarantine scope (`all lineages (both current and absent)`), clarified per-poll refresh vs `outbox_overflow`, replaced ambiguous store-emptying guidance with deleting the store/backups or replacing its data with `{}` across all contract/guide docs, and cleaned the asyncio import ordering + dead variable in `tests/ha/test_coordinator.py`.

The complete local gates passed: 43 Node, 82 stdlib HA (`-W error`), 7 source-skill, 21 Chromium browser, and 10 actual-HA tests (163 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`823de6d0...` extension, `062fd336...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T19:41:35.151Z` with HTTP 200 across NWS (0 alerts), USGS (6 items), BBC World (24 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once both pass, run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** and **S1**.

## Continuation update: November 17 seventh Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `f0e8a08` (`run_id`: `20261117T190130Z-35fadb`, 311.6s standards and 283.6s specification) reported **0 browser/UI/packaging/catalog findings**, and identified 9 unique findings in Home Assistant, docs, and tests (`SIT-H1` High, `SIT-HA-01` Medium, `SIT-HA-02`/`SIT-HA-03`/`SIT-L1` Low, `SIT-HA-04`/`SIT-HA-05`/`SIT-N1`/`SIT-DOC-01`/`SIT-TEST-01`/`SIT-N2` Nit).

All 9 findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor spec/reference/report updates:
- **`SIT-H1` & `SIT-L1`**: Persisted incoming Cancel's `cap_identity`/`cap_references` + `uncertain_targets` on first save, matched `uncertain_targets` in `conflicting_prior_cancel`, routed invalid-Cancel `records` cleanly in `cancellation_evidence()` without poisoning `ambiguous_groups`, and extracted `_expire_cancellation_horizons`, `_cancel_record_identity`, `_quarantined_record`, `_bound_records`, `_latch_degraded`, and `_persist_degraded_poll`.
- **`SIT-HA-01` & `SIT-HA-02`**: Wrapped `store.async_load()` exceptions and detected HA `.corrupt.*` backup files in `async_setup_entry()` so corrupt/unparseable JSON files latch `malformed_store`, cleared `.corrupt.*` backups on clean save/remove, and set `entry.data["journal_initialized"] = True` when loading any non-empty or malformed store.
- **`SIT-HA-03`**: Replaced uncaught `ValueError` on `len(outbox) > 5000` with bounding the outbox at 5,000 targets, saving reconciled records/outbox under durable `outbox_overflow` degraded state, and raising `situareness_degraded`.
- **`SIT-HA-04`, `SIT-HA-05`/`SIT-N1`, `SIT-DOC-01`, `SIT-TEST-01`/`SIT-N2`**: Set `_stopped_health()` `suspended_count = len(self.outbox)`, dismissed `situareness_degraded` before `Store.async_remove()` in `async_remove_entry()` (matching `o3-mvp.md`), tracked per-poll `seen_quarantine_ids` against the 5,000-ID limit, updated `docs/ha/README.md:45` to `Ten tests passed`, and replaced all inline review-code tags and drafting comments across `tests/ha/**` with behavioral descriptions.

The complete local gates passed: 43 Node, 81 stdlib HA (`-W error`), 7 source-skill, 21 Chromium browser, and 10 actual-HA tests (162 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`823de6d0...` extension, `76f0abc4...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T19:22:26.316Z` with HTTP 200 across NWS (0 alerts), USGS (7 items), BBC World (24 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once both pass, run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** and **S1**.

## Continuation update: November 17 sixth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `120c3c4` (`run_id`: `20261117T184436Z-6d91c1`, 260.7s standards and 244.0s specification) reported **0 Critical, 0 High, and 0 browser/UI/packaging/catalog findings**, leaving 5 unique actionable findings (+1 non-blocking doc nit): `SIT-HA-01` (Medium), `SIT-SPEC-01`/`SIT-HA-02` (Low), `SIT-HA-03` (Nit), `SIT-DOC-03` (Low), `SIT-DOC-01`/`SIT-DOC-02` (Low), and non-blocking `SIT-DOC-02` (Nit).

All findings were repaired via `ha-repair` (`775aa2e8`) plus supervisor spec/reference/report updates:
- **`SIT-HA-01`**: Isolated invalid `Actual Cancel` records by preserving prior `lineage` without raw incoming `refs`, persisting `uncertain_targets` (validated in `_valid_persisted_store` and cleaned on 7-day horizon expiry), and avoiding `ambiguous_groups` poisoning across Poll 1, Poll 2+, and sibling continuation.
- **`SIT-SPEC-01` & `SIT-HA-02`**: Stabilized `journal_lost_at` on the config entry, persisted `journal_lost` to the store before the first fetch, synced `situareness_degraded` at init and pre-fetch, and dismissed it cleanly in `async_stop()`, `async_unload_entry()`, and `async_remove_entry()`.
- **`SIT-HA-03`**: Added `_stopped_health()` so cancelling the first fetch during stop while healthy returns non-degraded empty health rather than `_degraded_health()`.
- **`SIT-DOC-03`, `SIT-DOC-01`/`SIT-DOC-02`, and non-blocking `SIT-DOC-02`**: Documented concrete `malformed_store` recovery options (repair disk JSON + reload, delete/empty disk store + reload -> `journal_lost`, or remove and re-add config entry), updated `docs/ha/README.md:45` to `Nine tests passed` covering both `journal_lost` real-HA scenarios, and corrected `docs/ha/README.md:27` on historic uncertainty clearing vs 15-minute outbox expiry.

The complete local gates passed: 43 Node, 78 stdlib HA (`-W error`), 7 source-skill, 21 Chromium browser, and 9 actual-HA tests (158 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`823de6d0...` extension, `dc0e15c6...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T18:59:17.394Z` with HTTP 200 across NWS (0 alerts), USGS (11 items), BBC World (24 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once both pass, run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** and **S1**.

## Continuation update: November 17 fifth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `9308033` (`run_id`: `20261117T180834Z-0e141a`, 348.0s standards and 394.4s specification) reported **0 Critical and 0 High findings** and zero regressions in prior fixes, leaving 1 Medium + 4 Low + 2 Nit standards findings and 1 Medium + 2 Low + 3 Nit spec findings (11 unique findings total).

All 11 findings were repaired via disjoint workers (`ha-repair` `775aa2e8` and `browser-repair` `50a99905`) plus supervisor spec/reference/report updates:
- **`SIT-R1` & `SIT-R7`/`SIT-DOC-06`**: Scoped malformed/oversized/conflicting `Actual Cancel`s with recoverable non-empty NWS target references within the 5,000-ID cap per targeted lineage/descendants (`quarantined_cancel_lineages`), delineated Policy 4 vs Policy 6 across `cap-cancellation.md`/`o3-mvp.md`, removed the `cap-cancellation.md` line 3 self-contradiction, and added the `situareness_degraded` HA persistent notification on global degraded lockdown.
- **`SIT-SPEC-01`**: Excluded `quarantine_events` from `lineage_index()`, stripped raw refs for all `invalid_ids` in `grouping_events`, and replaced group-level quarantine with per-ID `quarantined_event_ids`/`quarantined_record_ids` so malformed/conflicting siblings never taint independent root-sharing alerts.
- **`SIT-R2`**: Tracked `_fetch_task`, cancelled in-flight `fetch()` inside `async_stop()`, and aborted cleanly on post-stop without writing saves.
- **`SIT-R3`**: Excluded `degraded_at` and `degraded_until` alongside `events` and `last_success` in `SituarenessSensor._unrecorded_attributes`.
- **`SIT-R4` & `SIT-SPEC-02`**: Required `bool` for `initialized` and `was_live` in `_valid_persisted_store`, reported `degraded_until: None` for `malformed_store`, and persisted stable `malformed_store_at` on the config entry until store repair.
- **`SIT-SPEC-03` & `SIT-R6`/`SIT-DOC-04`**: Counted all identical earlier copies of conflicting duplicates (`[A, A, A_conflict]` -> `quarantined == 3`) and unified the 5,000-identifier cap across feature IDs, reference URLs, and conflicting duplicates via `add_quarantined_lineage`.
- **`SIT-R5` & `SIT-UI-05`**: Routed worker `"Bundled configuration..."` action errors in `extension/room.js` through `showDisconnected()` and fell back to `state.interval_minutes` in `isEventSourceUnavailable()` when `sources` omits an entry.

The complete local gates passed: 43 Node, 75 stdlib HA (`-W error`), 7 source-skill, 21 Chromium browser, and 8 actual-HA tests (154 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`823de6d0...` extension, `27902908...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T18:41:32.635Z` with HTTP 200 across NWS (0 alerts), USGS (9 items), BBC World (24 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on the clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once clean run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** (public CI privacy/build gate) and **S1**.

## Continuation update: November 17 fourth Opus repair candidate

Independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews of `64b6fa0` (`run_id`: `20261117T174809Z-251d8a`, 384.8s standards and 308.0s specification) reported zero High findings and zero packaging/catalog defects, leaving one Medium and three Low `spec` findings (`SPEC-01`–`SPEC-04`) plus one Medium and two Low `standards` findings (`SIT-REV-M1`, `SIT-REV-L1` [same as `SPEC-02`], `SIT-REV-L2` — 6 unique findings total).

All 6 remaining findings were repaired via disjoint workers (`ha-repair` `775aa2e8` and `browser-repair` `50a99905`) plus supervisor specification/report updates:
- **`SPEC-01` & `SIT-REV-L2`**: Tracked `"journal_initialized": True` on the config entry after saving a journal so a missing or empty persisted store on an already-initialized entry latches `degraded_reason="journal_lost"` (withholding output while continuing read-only collection until `degraded_until` or load-time acknowledgement) instead of resetting cleanly.
- **`SIT-REV-M1`**: Retained `state == "cancelled"` protection and seven-day expiry in `domain.py` even after a `Cancel` record ages out, prioritized active/current/`Cancel`/`cancelled` records under overflow, and propagated `dropped_horizon` across evicted components into `degraded_until` without shrinking earlier longer horizons.
- **`SPEC-02` & `SIT-REV-L1`**: Evaluated `acknowledge_degraded_at` solely at coordinator construction against load time (`degraded_at <= acknowledge_degraded_at <= load_now`), preventing future-dated timestamps from auto-clearing on later polls without reload.
- **`SPEC-03`**: Preserved `last_degraded_poll` across load-time acknowledgement until `_migrate_and_prune_outbox()` credits the final degraded interval on the recovery poll.
- **`SPEC-04`**: Exported `isEventSourceUnavailable(...)` in `extension/ui/helpers.mjs`, rendered `"Cached · source unavailable"` alongside `"Not in latest results"` when an NWS source is unavailable, and defaulted missing/unknown non-expired NWS lifecycle metadata to `"cached"` while unavailable (`"expired"` stays exclusive).
- **`SIT-REV-L2`**: Added explicit history-loss/re-alert disclosures for resetting/replacing `malformed_store`/`journal_lost` stores and early `cancellation_evidence_overflow` acknowledgement across `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`.

The complete local gates passed: 42 Node, 73 stdlib HA (`-W error`), 7 source-skill, 20 Chromium browser, and 8 actual-HA tests (150 total), plus static checks, Ruff lint/format, and two identical deterministic ZIP builds (`60910aad...` extension, `fb0b4645...` HA). Actual HA reports five known upstream deprecations without suppression. Live anonymous smoke (`node tools/live-browser-smoke.mjs`) passed at `2026-11-17T18:06:18.354Z` with HTTP 200 across NWS (1 alert), USGS (7 items), BBC World (24 items), and BBC US & Canada (23 items).

Next: run `audit_private.py`, commit and push to `wip/supervisor-handoff-20261117`, refresh verification logs on the clean `HEAD`, run independent Claude Opus 5.5 (`claude-opus-5-5`, medium effort) `standards` and `spec` reviews, and once both pass, run a fresh independent Opus `adversarial` review on that immutable candidate. Household outputs remain disabled and no commissioning occurred. `main` remains at `847d0e5`; once all release gates pass, fast-forward `main` and advance roadmap **S0** (public CI privacy/build gate) and **S1**.

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
