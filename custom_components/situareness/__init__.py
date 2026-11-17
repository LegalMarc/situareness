"""Independent NWS monitoring for Home Assistant."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from itertools import islice
import json
import logging
from pathlib import Path

from homeassistant.components import persistent_notification
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .collector import fetch
from .config import validate
from .const import DOMAIN
from .delivery import MAX_AGE, deliver_one, live, pending_valid, targets
from .domain import (
    CancellationEvidenceOverflow,
    MAX_ACCEPTANCE_AGE,
    action_history,
    conflicting_prior_cancel,
    lineage_index,
    qualify,
    reconcile,
    resolve_candidates,
    timestamp,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
PERSISTED_DEGRADED_REASONS = {
    "cancellation_evidence_overflow",
    "outbox_overflow",
    "malformed_cancellation",
    "conflicting_cancellation",
    "journal_lost",
}


def _read_config(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            return validate(json.load(stream))
    except FileNotFoundError:
        return validate({})


def _valid_persisted_store(persisted):
    if persisted is None:
        return True
    if not isinstance(persisted, dict):
        return False
    for bool_key in ("degraded", "initialized", "was_live"):
        if bool_key in persisted and not isinstance(persisted[bool_key], bool):
            return False
    for key in (
        "degraded_at",
        "degraded_until",
        "acknowledged_degraded_at",
        "last_degraded_poll",
    ):
        val = persisted.get(key)
        if val is not None and (not isinstance(val, str) or timestamp(val) is None):
            return False
    reason = persisted.get("degraded_reason")
    if reason is not None and (
        not isinstance(reason, str) or reason not in PERSISTED_DEGRADED_REASONS
    ):
        return False
    if persisted.get("initialized") is True and "records" not in persisted:
        return False
    if "records" in persisted:
        records = persisted["records"]
        if not isinstance(records, dict):
            return False
        for eid, record in records.items():
            if not isinstance(eid, str) or not isinstance(record, dict):
                return False
            for req_str_key in ("state", "updated"):
                if req_str_key in record and not isinstance(record[req_str_key], str):
                    return False
            for opt_str_key in (
                "prior_state",
                "fingerprint",
                "action_identity",
                "action_fingerprint",
                "sent",
                "expires",
                "ends",
                "inactive_since",
            ):
                if (
                    opt_str_key in record
                    and record[opt_str_key] is not None
                    and not isinstance(record[opt_str_key], str)
                ):
                    return False
            if (
                "cancelled_at" in record
                and record["cancelled_at"] is not None
                and (
                    not isinstance(record["cancelled_at"], str)
                    or timestamp(record["cancelled_at"]) is None
                )
            ):
                return False
            if (
                "action_affected" in record
                and record["action_affected"] is not None
                and (
                    not isinstance(record["action_affected"], list)
                    or not all(isinstance(v, str) for v in record["action_affected"])
                )
            ):
                return False
            for bool_key in ("cancel_message", "cancellation_expired"):
                if bool_key in record and not isinstance(record[bool_key], bool):
                    return False
            for list_key in ("lineage", "reasons", "affected", "uncertain_targets"):
                if list_key in record and (
                    not isinstance(record[list_key], list)
                    or not all(isinstance(v, str) for v in record[list_key])
                ):
                    return False
            if "actions" in record:
                actions = record["actions"]
                if not isinstance(actions, dict) or not all(
                    isinstance(k, str)
                    and isinstance(v, list)
                    and all(isinstance(x, str) for x in v)
                    for k, v in actions.items()
                ):
                    return False
            if "cap_identity" in record and record["cap_identity"] is not None:
                ident = record["cap_identity"]
                if (
                    not isinstance(ident, list)
                    or len(ident) != 3
                    or not all(isinstance(x, str) for x in ident)
                ):
                    return False
            if "cap_references" in record and record["cap_references"] is not None:
                refs = record["cap_references"]
                if not isinstance(refs, list) or not all(
                    isinstance(ref, list)
                    and len(ref) == 3
                    and all(isinstance(x, str) for x in ref)
                    for ref in refs
                ):
                    return False
    if "outbox" in persisted:
        outbox = persisted["outbox"]
        if not isinstance(outbox, list) or len(outbox) > 5000:
            return False
        for item in outbox:
            if not isinstance(item, dict):
                return False
            for str_key in (
                "key",
                "incident_id",
                "fingerprint",
                "kind",
                "target",
                "created",
                "event",
                "instruction",
                "source_url",
            ):
                if not isinstance(item.get(str_key), str):
                    return False
            if (
                "affected_names" not in item
                or not isinstance(item["affected_names"], list)
                or not all(isinstance(n, str) for n in item["affected_names"])
            ):
                return False
            if timestamp(item.get("created")) is None:
                return False
            if "location" not in item or not (
                item["location"] is None or isinstance(item["location"], str)
            ):
                return False
            attempts = item.get("attempts")
            if not isinstance(attempts, int) or isinstance(attempts, bool):
                return False
    if "outcomes" in persisted:
        outcomes = persisted["outcomes"]
        if not isinstance(outcomes, list) or not all(
            isinstance(item, dict) for item in outcomes
        ):
            return False
    return True


def _outbox_signature(groups, item, records=None):
    if (
        records is not None
        and records.get(item["incident_id"], {}).get("state") == "quarantined"
    ):
        return (
            "quarantined",
            item["incident_id"],
            item["fingerprint"],
            item["kind"],
            item["target"],
            item["location"],
        )
    return (
        groups.get(item["incident_id"]),
        item["fingerprint"],
        item["kind"],
        item["target"],
        item["location"],
    )


def _unrecoverable_prior_cancel_conflict(event, old):
    if not conflicting_prior_cancel(event, old):
        return False
    old_has_targets = bool(
        old.get("cap_references")
        or old.get("uncertain_targets")
        or len(old.get("lineage", [])) > 1
    )
    return not event.get("references") or (
        old.get("cancel_message") is True and not old_has_targets
    )


def _has_corrupt_store_backup(storage_dir, prefix):
    directory = Path(storage_dir)
    if not directory.is_dir():
        return False
    return any(directory.glob(f"{prefix}.corrupt.*"))


def _clear_corrupt_store_backups(storage_dir, prefix):
    directory = Path(storage_dir)
    if not directory.is_dir():
        return
    for candidate in directory.glob(f"{prefix}.corrupt.*"):
        try:
            candidate.unlink()
        except OSError:
            pass


class SituarenessCoordinator(DataUpdateCoordinator):
    def __init__(
        self, hass, config, store, persisted, entry=None, has_corrupt_backup=False
    ):
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self.config = config
        self.store = store
        self._entry = entry
        if not _valid_persisted_store(persisted):
            detect_now = datetime.now(timezone.utc)
            persisted_deg_at = (
                persisted.get("degraded_at") if isinstance(persisted, dict) else None
            )
            entry_deg_at = (
                self._entry.data.get("malformed_store_at")
                if self._entry is not None
                else None
            )
            stable_at = (
                persisted_deg_at
                if isinstance(persisted_deg_at, str)
                and timestamp(persisted_deg_at) is not None
                else entry_deg_at
                if isinstance(entry_deg_at, str) and timestamp(entry_deg_at) is not None
                else detect_now.isoformat()
            )
            self.records = {}
            self.outbox = []
            self.outcomes = []
            self.initialized = False
            self.was_live = False
            self.degraded = True
            self.degraded_reason = "malformed_store"
            self.degraded_at = stable_at
            self.degraded_until = None
            self.acknowledged_degraded_at = None
            self.last_degraded_poll = None
            if self._entry is not None and (
                self._entry.data.get("malformed_store_at") != stable_at
                or self._entry.data.get("journal_initialized") is not True
                or "journal_lost_at" in self._entry.data
            ):
                new_data = {
                    k: v for k, v in self._entry.data.items() if k != "journal_lost_at"
                }
                new_data["malformed_store_at"] = stable_at
                new_data["journal_initialized"] = True
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    data=new_data,
                )
        elif (
            self._entry is not None
            and self._entry.data.get("journal_initialized") is True
            and (persisted is None or persisted == {})
        ):
            detect_now = datetime.now(timezone.utc)
            entry_lost_at = self._entry.data.get("journal_lost_at")
            entry_ts = (
                timestamp(entry_lost_at) if isinstance(entry_lost_at, str) else None
            )
            if entry_ts is not None and detect_now - entry_ts <= MAX_ACCEPTANCE_AGE:
                stable_lost_at = entry_lost_at
                lost_ts = entry_ts
            else:
                stable_lost_at = detect_now.isoformat()
                lost_ts = detect_now
            self.records = {}
            self.outbox = []
            self.outcomes = []
            self.initialized = True
            self.was_live = live(self.config)
            self.degraded = True
            self.degraded_reason = "journal_lost"
            self.degraded_at = stable_lost_at
            self.degraded_until = (
                max(lost_ts, detect_now) + MAX_ACCEPTANCE_AGE
            ).isoformat()
            self.acknowledged_degraded_at = None
            self.last_degraded_poll = detect_now.isoformat()
            if self._entry.data.get("journal_lost_at") != stable_lost_at:
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    data={**self._entry.data, "journal_lost_at": stable_lost_at},
                )
        else:
            persisted = persisted if isinstance(persisted, dict) else {}
            self.records = persisted.get("records", {})
            self.outbox = persisted.get("outbox", [])
            self.outcomes = persisted.get("outcomes", [])
            self.initialized = persisted.get("initialized") is True or (
                "initialized" not in persisted and bool(self.records or self.outbox)
            )
            # An absent legacy gate marker is not a new live-mode transition.
            self.was_live = persisted.get("was_live") is True or (
                "was_live" not in persisted and self.initialized
            )
            self.degraded = persisted.get("degraded") is True
            self.degraded_reason = (
                (persisted.get("degraded_reason") or "cancellation_evidence_overflow")
                if self.degraded
                else None
            )
            self.degraded_at = persisted.get("degraded_at") if self.degraded else None
            self.degraded_until = (
                persisted.get("degraded_until") if self.degraded else None
            )
            self.acknowledged_degraded_at = persisted.get("acknowledged_degraded_at")
            self.last_degraded_poll = (
                (persisted.get("last_degraded_poll") or self.degraded_at)
                if self.degraded
                else None
            )
            if (
                self._entry is not None
                and bool(persisted)
                and (
                    self._entry.data.get("journal_initialized") is not True
                    or "journal_lost_at" in self._entry.data
                )
            ):
                new_data = {
                    k: v for k, v in self._entry.data.items() if k != "journal_lost_at"
                }
                new_data["journal_initialized"] = True
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    data=new_data,
                )
        self._needs_corrupt_cleanup = bool(
            has_corrupt_backup
            or (self._entry is not None and "malformed_store_at" in self._entry.data)
        )
        self._journal_lost_saved = not (
            self.degraded
            and self.degraded_reason == "journal_lost"
            and (persisted is None or persisted == {})
        )
        entry_ack = (
            self._entry.data.get("acknowledged_degraded_at")
            if self._entry is not None
            else None
        )
        if (
            self.acknowledged_degraded_at is None
            and isinstance(entry_ack, str)
            and timestamp(entry_ack) is not None
        ):
            self.acknowledged_degraded_at = entry_ack
        self.acknowledge_rejected = False
        self._ack_cleared_on_load = False
        self._try_acknowledge(datetime.now(timezone.utc), entry_ack=entry_ack)
        self.session = async_get_clientsession(hass)
        self._refresh_lock = asyncio.Lock()
        self._fetch_task = None
        self._stopping = False
        self._notified_degraded_state = None
        self._checked_notification_clear = False
        self._sync_degraded_notification()

    def _record_consumed_ack(self, ack):
        self.acknowledged_degraded_at = ack
        if (
            self._entry is not None
            and self._entry.data.get("acknowledged_degraded_at") != ack
        ):
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={**self._entry.data, "acknowledged_degraded_at": ack},
            )

    def _try_acknowledge(self, current_now, entry_ack=None):
        if entry_ack is None and self._entry is not None:
            entry_ack = self._entry.data.get("acknowledged_degraded_at")
        ack = self.config.get("acknowledge_degraded_at")
        if ack is None:
            self.acknowledge_rejected = False
            return False
        ack_ts = timestamp(ack) if isinstance(ack, str) and len(ack) <= 100 else None
        if ack_ts is None:
            self.acknowledge_rejected = bool(self.degraded)
            return False
        if not self.degraded:
            self._record_consumed_ack(ack)
            self.acknowledge_rejected = False
            return False
        if self.degraded_reason == "malformed_store" or ack in (
            self.acknowledged_degraded_at,
            entry_ack,
        ):
            if self.degraded_reason != "malformed_store":
                self._record_consumed_ack(ack)
            self.acknowledge_rejected = True
            return False
        degraded_at_ts = timestamp(self.degraded_at)
        if degraded_at_ts is None or not (degraded_at_ts <= ack_ts <= current_now):
            self._record_consumed_ack(ack)
            self.acknowledge_rejected = True
            return False
        self.acknowledged_degraded_at = ack
        self.acknowledge_rejected = False
        self._ack_cleared_on_load = True
        self.degraded = False
        self.degraded_reason = None
        self.degraded_at = None
        self.degraded_until = None
        return True

    async def _save(self, records, outbox, outcomes, *, preserve_lost_at=False):
        await self.store.async_save(
            {
                "records": records,
                "outbox": outbox,
                "outcomes": outcomes[-100:],
                "initialized": True,
                "was_live": live(self.config),
                "degraded": self.degraded,
                "degraded_reason": self.degraded_reason,
                "degraded_at": self.degraded_at,
                "degraded_until": self.degraded_until,
                "acknowledged_degraded_at": self.acknowledged_degraded_at,
                "last_degraded_poll": self.last_degraded_poll,
            }
        )
        self.records, self.outbox, self.outcomes, self.initialized = (
            records,
            outbox,
            outcomes[-100:],
            True,
        )
        self.was_live = live(self.config)
        if self._needs_corrupt_cleanup:
            if self._entry is not None:
                await self.hass.async_add_executor_job(
                    _clear_corrupt_store_backups,
                    self.hass.config.path(".storage"),
                    f"{DOMAIN}.{self._entry.entry_id}",
                )
            self._needs_corrupt_cleanup = False
        clear_lost_at = not preserve_lost_at
        needs_entry_ack = (
            self._entry is not None
            and isinstance(self.acknowledged_degraded_at, str)
            and self._entry.data.get("acknowledged_degraded_at")
            != self.acknowledged_degraded_at
        )
        if self._entry is not None and (
            self._entry.data.get("journal_initialized") is not True
            or "malformed_store_at" in self._entry.data
            or (clear_lost_at and "journal_lost_at" in self._entry.data)
            or needs_entry_ack
        ):
            new_data = {
                k: v
                for k, v in self._entry.data.items()
                if k != "malformed_store_at"
                and (not clear_lost_at or k != "journal_lost_at")
            }
            new_data["journal_initialized"] = True
            if isinstance(self.acknowledged_degraded_at, str):
                new_data["acknowledged_degraded_at"] = self.acknowledged_degraded_at
            self.hass.config_entries.async_update_entry(self._entry, data=new_data)

    def _sync_degraded_notification(self, quarantine_ambiguous=False):
        if self.degraded:
            is_live = live(self.config)
            state = (self.degraded_reason, is_live, self.acknowledge_rejected)
            if self._notified_degraded_state != state:
                rej_note = (
                    "Configured acknowledge_degraded_at did not clear this state "
                    "(malformed_store cannot be acknowledged, or acknowledge_degraded_at was invalid/missing timezone offset, "
                    "in the future, preceded degraded_at, was already consumed, or the triggering condition remained active and re-latched). "
                    if self.acknowledge_rejected
                    else ""
                )
                if self.degraded_reason == "outbox_overflow":
                    title = "Situareness delivery outbox full"
                    if is_live:
                        message = (
                            "Situareness outbox reached the 5,000-target limit; overflowing alert plans are withheld "
                            "while already-queued targets continue bounded delivery. "
                            + rej_note
                            + "This clears automatically once outbox space frees up or the 15-minute degraded_until horizon expires; "
                            "one-shot acknowledge_degraded_at in situareness.json "
                            "(degraded_at <= acknowledge_degraded_at <= reload time) takes effect permanently on reload "
                            "only once outbox overflow has cleared (otherwise the next poll re-latches with a new degraded_at). "
                            "Continue using independent official alert channels."
                        )
                    else:
                        message = (
                            "Situareness monitoring is degraded in shadow mode (live output disabled): "
                            "the outbox reached the 5,000-target limit and overflowing alert plans are withheld. "
                            + rej_note
                            + "This clears automatically once outbox space frees up or the 15-minute degraded_until horizon expires; "
                            "one-shot acknowledge_degraded_at in situareness.json "
                            "(degraded_at <= acknowledge_degraded_at <= reload time) takes effect permanently on reload "
                            "only once outbox overflow has cleared (otherwise the next poll re-latches with a new degraded_at). "
                            "Continue using independent official alert channels."
                        )
                else:
                    title = "Situareness monitoring degraded"
                    prefix = (
                        f"Situareness output is blocked (reason: {self.degraded_reason}). "
                        if is_live
                        else (
                            "Situareness monitoring is degraded in shadow mode with live output disabled "
                            f"(reason: {self.degraded_reason}). "
                        )
                    )
                    if self.degraded_reason == "malformed_store":
                        message = (
                            prefix
                            + rej_note
                            + "Manual store repair or replacement in .storage (or removing and re-adding the integration entry) is required. "
                            + "Continue using independent official alert channels."
                        )
                    else:
                        tail = (
                            "Output remains withheld until "
                            if is_live
                            else "Monitoring remains degraded in shadow mode until "
                        )
                        message = (
                            prefix
                            + rej_note
                            + tail
                            + "the triggering condition clears and degraded_until "
                            "(at least seven days or the latest evicted component horizon) expires, "
                            "or until one-shot acknowledge_degraded_at in situareness.json "
                            "(degraded_at <= acknowledge_degraded_at <= reload time) takes effect permanently on reload "
                            "once the triggering feed condition has left the feed "
                            "(otherwise the next poll re-latches with a new degraded_at). "
                            "Continue using independent official alert channels."
                        )
                persistent_notification.async_create(
                    self.hass,
                    message,
                    title=title,
                    notification_id="situareness_degraded",
                )
                self._notified_degraded_state = state
                self._checked_notification_clear = False
        elif quarantine_ambiguous:
            state = "quarantine_ambiguous"
            if self._notified_degraded_state != state:
                persistent_notification.async_create(
                    self.hass,
                    "Situareness could not determine safe scope for one or more malformed NWS features, "
                    "so all alert lineages are suspended for this poll. Continue using independent official alert channels.",
                    title="Situareness alert scope ambiguous",
                    notification_id="situareness_degraded",
                )
                self._notified_degraded_state = state
                self._checked_notification_clear = False
        elif (
            self._notified_degraded_state is not None
            or not self._checked_notification_clear
        ):
            persistent_notification.async_dismiss(self.hass, "situareness_degraded")
            self._notified_degraded_state = None
            self._checked_notification_clear = True

    async def async_stop(self):
        self._stopping = True
        if self._fetch_task is not None and not self._fetch_task.done():
            self._fetch_task.cancel()
        async with self._refresh_lock:
            pass
        _dismiss_degraded_notification(self.hass)
        self._notified_degraded_state = None

    async def _async_update_data(self):
        async with self._refresh_lock:
            if self._stopping:
                raise UpdateFailed("integration is stopping")
            return await self._update_once()

    def _deliverable_count(self, records, candidate_events, health_now):
        by_id = {event["id"]: event for event in candidate_events}
        current_eligible = {
            eid
            for eid, event in by_id.items()
            if records.get(eid, {}).get("state") == "active"
            and qualify(event, self.config, health_now)["qualifies"]
        }
        return sum(
            item["incident_id"] in current_eligible
            and pending_valid(item, records, self.config, health_now)
            for item in self.outbox
        )

    def _degraded_health(
        self,
        events=None,
        candidate_events=None,
        records=None,
        now=None,
        *,
        triggered_now=False,
        recoverable_prior_conflict=False,
        planned_count=0,
        withheld_count=0,
        delivery_attempts=0,
        delivery_failures=0,
    ):
        """Expose a redacted durable degraded state without delivering (except bounded queued delivery during outbox_overflow)."""
        previous = getattr(self, "data", None) or {}
        shown = candidate_events if candidate_events is not None else events
        record_map = records if records is not None else self.records
        quarantined_count = 0
        event_summaries = []
        if shown is not None:
            quarantined_count = getattr(events, "quarantined", 0) + sum(
                record_map.get(e["id"], {}).get("state") == "quarantined" for e in shown
            )
            event_summaries = [
                {
                    "id": e["id"],
                    "event": (e["event"] or "")[:100],
                    "headline": (e["headline"] or "")[:160],
                    "sent": e["sent"],
                    "expires": e["expires"],
                    "state": record_map.get(e["id"], {}).get("state", "unknown"),
                    "reasons": record_map.get(e["id"], {}).get("reasons", []),
                }
                for e in shown[:25]
            ]
        quarantine_ambiguous = bool(getattr(events, "quarantine_ambiguous", False))
        cancellation_uncertain = (
            (
                triggered_now
                and self.degraded_reason
                in (
                    "cancellation_evidence_overflow",
                    "malformed_cancellation",
                    "conflicting_cancellation",
                )
            )
            or bool(getattr(events, "quarantined_cancel_lineages", ()))
            or recoverable_prior_conflict
            or any(
                r.get("state") == "quarantined"
                and "cancellation scope uncertain" in r.get("reasons", [])
                for r in (records or {}).values()
            )
        )
        is_outbox_overflow = self.degraded_reason == "outbox_overflow"
        if is_outbox_overflow:
            health_now = datetime.now(timezone.utc)
            deliverable = self._deliverable_count(
                record_map, candidate_events or (), health_now
            )
            suspended = len(self.outbox) - deliverable
            active_count = (
                sum(record_map.get(e["id"], {}).get("state") == "active" for e in shown)
                if shown is not None
                else None
            )
        else:
            deliverable = 0
            suspended = len(self.outbox)
            active_count = None
        return {
            "last_success": (
                now.isoformat()
                if events is not None and now is not None
                else previous.get("last_success")
            ),
            "event_count": len(shown) if shown is not None else 0,
            "source_feature_count": (
                getattr(events, "source_count", len(events))
                if events is not None
                else 0
            ),
            "active_count": active_count,
            "partial": (
                bool(quarantined_count)
                or quarantine_ambiguous
                or cancellation_uncertain
                or is_outbox_overflow
            ),
            "quarantined_count": quarantined_count,
            "quarantine_ambiguous": quarantine_ambiguous,
            "cancellation_uncertain": cancellation_uncertain,
            "evidence_degraded": not is_outbox_overflow,
            "output_blocked": not is_outbox_overflow,
            "degraded_reason": self.degraded_reason,
            "degraded_at": self.degraded_at,
            "degraded_until": self.degraded_until,
            "acknowledge_rejected": self.acknowledge_rejected,
            "shadow": not live(self.config),
            "events": event_summaries,
            "planned_count": planned_count,
            "withheld_count": withheld_count,
            "pending_count": len(self.outbox),
            "deliverable_count": deliverable,
            "suspended_count": suspended,
            "delivery_attempts": delivery_attempts,
            "delivery_failures": delivery_failures,
        }

    def _stopped_health(self):
        """Expose a redacted non-degraded snapshot when stopped before first poll."""
        if self.degraded:
            return self._degraded_health()
        return {
            "last_success": None,
            "event_count": 0,
            "source_feature_count": 0,
            "active_count": None,
            "partial": False,
            "quarantined_count": 0,
            "quarantine_ambiguous": False,
            "cancellation_uncertain": False,
            "evidence_degraded": False,
            "output_blocked": False,
            "degraded_reason": None,
            "degraded_at": None,
            "degraded_until": None,
            "acknowledge_rejected": False,
            "shadow": not live(self.config),
            "events": [],
            "planned_count": 0,
            "withheld_count": 0,
            "pending_count": len(self.outbox),
            "deliverable_count": 0,
            "suspended_count": len(self.outbox),
            "delivery_attempts": 0,
            "delivery_failures": 0,
        }

    def _migrate_and_prune_outbox(
        self, records, events, now, groups, degraded_delta=None
    ):
        if not live(self.config):
            return []
        event_index = {}
        for event in events:
            eid = event["id"]
            record = records.get(eid, {})
            if record.get("state") in ("active", "ineligible"):
                for fp in action_history(record):
                    event_index.setdefault((groups[eid], fp), []).append(eid)
        for ids in event_index.values():
            ids.sort(key=lambda eid: (records[eid]["state"] != "active", eid))
        check_time = now - degraded_delta if degraded_delta is not None else now
        candidates = []
        for item in self.outbox:
            if not isinstance(item, dict):
                continue
            incident = item.get("incident_id")
            if records.get(incident, {}).get("state") == "cancelled":
                continue
            successors = event_index.get(
                (groups.get(incident), item.get("fingerprint")), []
            )
            if records.get(incident, {}).get("state") == "quarantined":
                successors = []
            if successors:
                successor = successors[0]
                candidate = {
                    **item,
                    "incident_id": successor,
                    "source_url": successor,
                }
                if pending_valid(
                    candidate, records, self.config, check_time, allow_suspended=True
                ):
                    item = candidate
            if (
                degraded_delta is not None
                and records.get(item.get("incident_id"), {}).get("state") == "active"
                and pending_valid(
                    item, records, self.config, check_time, allow_suspended=True
                )
            ):
                created_ts = timestamp(item.get("created"))
                if created_ts is not None:
                    item = {
                        **item,
                        "created": min(now, created_ts + degraded_delta).isoformat(),
                    }
            candidates.append(item)
        outbox = [
            x
            for x in candidates
            if pending_valid(x, records, self.config, now, allow_suspended=True)
        ]
        unique = {}
        for item in outbox:
            key = _outbox_signature(groups, item, records)
            if key in unique:
                prior_item = unique[key]
                # Keep the strictest retry bounds when lineages merge.
                unique[key] = {
                    **prior_item,
                    "created": min(prior_item["created"], item["created"]),
                    "attempts": max(prior_item["attempts"], item["attempts"]),
                }
            else:
                unique[key] = item
        return list(unique.values())

    def _latch_degraded(self, reason, now, until=None):
        default_window = MAX_AGE if reason == "outbox_overflow" else MAX_ACCEPTANCE_AGE
        candidate_until = until or (now + default_window)
        same_reason = self.degraded and self.degraded_reason == reason
        if self.degraded and (same_reason or reason != "outbox_overflow"):
            existing_until = timestamp(self.degraded_until)
        else:
            existing_until = None
        new_until = (
            max(existing_until, candidate_until)
            if existing_until is not None
            else candidate_until
        )
        if not (same_reason and timestamp(self.degraded_at) is not None):
            self.degraded_at = now.isoformat()
        if self._ack_cleared_on_load:
            self.acknowledge_rejected = True
        self.degraded = True
        self.degraded_reason = reason
        self.degraded_until = new_until.isoformat()

    @staticmethod
    def _strip_withheld_actions(records, plans, groups, now):
        withheld_keys = {
            (groups.get(plan["id"]), plan["fingerprint"]) for plan in plans
        }
        now_iso = now.isoformat()
        for eid, record in records.items():
            if record.get("updated") == now_iso:
                rec_actions = record.get("actions")
                if isinstance(rec_actions, dict):
                    for fp in list(rec_actions):
                        if (groups.get(eid), fp) in withheld_keys:
                            rec_actions.pop(fp, None)

    async def _persist_degraded_poll(
        self,
        records,
        plans,
        outbox,
        groups,
        events,
        candidate_events,
        now,
        *,
        triggered_now=False,
        recoverable_prior_conflict=False,
        planned_count=0,
        delivery_attempts=0,
        delivery_failures=0,
    ):
        self._strip_withheld_actions(records, plans, groups, now)
        self.last_degraded_poll = now.isoformat()
        try:
            await self._save(records, outbox, list(self.outcomes))
        except Exception as save_err:
            raise UpdateFailed(
                "Could not persist cancellation evidence safety state"
            ) from save_err
        self._sync_degraded_notification()
        return self._degraded_health(
            events=events,
            candidate_events=candidate_events,
            records=records,
            now=now,
            triggered_now=triggered_now,
            recoverable_prior_conflict=recoverable_prior_conflict,
            planned_count=planned_count,
            withheld_count=len(plans),
            delivery_attempts=delivery_attempts,
            delivery_failures=delivery_failures,
        )

    async def _queue_outbox_plans(
        self, records, plans, outbox, candidate_events, groups, now
    ):
        """Queue plans atomically up to 5,000 targets; drain pending deliverable work first if needed."""
        attempts = failures = 0
        if not live(self.config) or not plans:
            return outbox, False, [], records, attempts, failures, False

        def build_planned_items(current_outbox, current_records):
            existing = {
                _outbox_signature(groups, item, current_records)
                for item in current_outbox
            }
            seen_in_plans = set(existing)
            planned_items = []
            projected_count = len(current_outbox)
            for plan in plans:
                new_items = []
                for item in targets(plan, self.config, now):
                    sig = _outbox_signature(groups, item, current_records)
                    if sig not in seen_in_plans:
                        new_items.append((item, sig))
                        seen_in_plans.add(sig)
                planned_items.append((plan, new_items))
                projected_count += len(new_items)
            return existing, planned_items, projected_count

        existing, planned_items, projected_count = build_planned_items(outbox, records)
        deliverable_existing = sum(
            1 for x in outbox if pending_valid(x, records, self.config, now)
        )
        already_delivered = False
        if projected_count > 5000 and deliverable_existing > 0:
            pre_drain_records = deepcopy(records)
            self._strip_withheld_actions(records, plans, groups, now)
            await self._save(records, outbox, list(self.outcomes))
            attempts, failures = await self._deliver_outbox_batch(candidate_events, now)
            already_delivered = True
            records = pre_drain_records
            outbox = list(self.outbox)
            existing, planned_items, _ = build_planned_items(outbox, records)

        outbox_overflow = False
        dropped_plans = []
        for plan, new_items in planned_items:
            if not outbox_overflow and len(outbox) + len(new_items) <= 5000:
                for item, sig in new_items:
                    outbox.append(item)
                    existing.add(sig)
            else:
                outbox_overflow = True
                dropped_plans.append(plan)
        return (
            outbox,
            outbox_overflow,
            dropped_plans,
            records,
            attempts,
            failures,
            already_delivered,
        )

    async def _deliver_outbox_batch(self, candidate_events, now):
        """Deliver one bounded poll batch (max 100 targets, 30s deadline)."""
        attempts = failures = 0
        # Expired items and each completed 10-target delivery group are persisted; a crash between service call and save may duplicate that group.
        batch = list(
            islice(
                (
                    x
                    for x in self.outbox
                    if pending_valid(x, self.records, self.config, now)
                ),
                100,
            )
        )
        by_id = {event["id"]: event for event in candidate_events}
        deadline = now + timedelta(seconds=30)
        for offset in range(0, len(batch), 10):
            if self._stopping:
                break
            current = datetime.now(timezone.utc)
            if current >= deadline:
                break
            group = []
            expired_keys = set()
            for item in batch[offset : offset + 10]:
                event = by_id.get(item["incident_id"])
                if (
                    event is not None
                    and pending_valid(item, self.records, self.config, current)
                    and qualify(event, self.config, current)["qualifies"]
                ):
                    group.append(item)
                elif not pending_valid(
                    item, self.records, self.config, current, allow_suspended=True
                ):
                    expired_keys.add(item["key"])
            if expired_keys:
                remaining = [x for x in self.outbox if x["key"] not in expired_keys]
                await self._save(self.records, remaining, self.outcomes)
            if not group:
                continue
            results = await asyncio.gather(
                *(deliver_one(self.hass.services, item, self.config) for item in group)
            )
            processed_keys = set()
            requeued = []
            new_outcomes = []
            for item, accepted in zip(group, results):
                if accepted is None:
                    break
                attempts += 1
                failures += not accepted
                processed_keys.add(item["key"])
                updated = {**item, "attempts": item["attempts"] + 1}
                if not accepted and pending_valid(
                    updated, self.records, self.config, datetime.now(timezone.utc)
                ):
                    requeued.append(updated)
                new_outcomes.append(
                    {
                        "key": item["key"],
                        "accepted": accepted,
                        "attempt": updated["attempts"],
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            if processed_keys or new_outcomes:
                remaining = [
                    x for x in self.outbox if x["key"] not in processed_keys
                ] + requeued
                await self._save(self.records, remaining, self.outcomes + new_outcomes)
        return attempts, failures

    def _healthy_snapshot(
        self,
        events,
        candidate_events,
        records,
        plans,
        now,
        attempts,
        failures,
        recoverable_prior_conflict,
    ):
        """Build the redacted healthy coordinator snapshot and sync notifications."""
        health_now = datetime.now(timezone.utc)
        deliverable = self._deliverable_count(records, candidate_events, health_now)
        quarantine_count = getattr(events, "quarantined", 0) + sum(
            records[e["id"]]["state"] == "quarantined" for e in candidate_events
        )
        cancellation_uncertain = (
            bool(getattr(events, "quarantined_cancel_lineages", ()))
            or recoverable_prior_conflict
            or any(
                record.get("state") == "quarantined"
                and "cancellation scope uncertain" in record.get("reasons", [])
                for record in records.values()
            )
        )
        quarantine_ambiguous = bool(getattr(events, "quarantine_ambiguous", False))
        partial = (
            bool(quarantine_count) or cancellation_uncertain or quarantine_ambiguous
        )
        self._sync_degraded_notification(quarantine_ambiguous=quarantine_ambiguous)
        return {
            "last_success": now.isoformat(),
            "event_count": len(candidate_events),
            "source_feature_count": getattr(
                events, "source_count", len(candidate_events)
            ),
            "active_count": sum(
                records[e["id"]]["state"] == "active" for e in candidate_events
            ),
            "partial": partial,
            "cancellation_uncertain": cancellation_uncertain,
            "evidence_degraded": False,
            "output_blocked": False,
            "degraded_reason": self.degraded_reason,
            "degraded_at": self.degraded_at,
            "degraded_until": self.degraded_until,
            "acknowledge_rejected": False,
            "quarantined_count": quarantine_count,
            "quarantine_ambiguous": quarantine_ambiguous,
            "shadow": not live(self.config),
            "events": [
                {
                    "id": e["id"],
                    "event": (e["event"] or "")[:100],
                    "headline": (e["headline"] or "")[:160],
                    "sent": e["sent"],
                    "expires": e["expires"],
                    "state": records[e["id"]]["state"],
                    "reasons": records[e["id"]]["reasons"],
                }
                for e in candidate_events[:25]
            ],
            "planned_count": len(plans),
            "withheld_count": 0,
            "pending_count": len(self.outbox),
            "deliverable_count": deliverable,
            "suspended_count": len(self.outbox) - deliverable,
            "delivery_attempts": attempts,
            "delivery_failures": failures,
        }

    async def _update_once(self):
        try:
            if self.degraded:
                self._sync_degraded_notification()
            if self.degraded and self.degraded_reason == "malformed_store":
                return self._degraded_health()
            if self.degraded_reason == "journal_lost" and not self._journal_lost_saved:
                try:
                    await self._save(
                        dict(self.records),
                        list(self.outbox),
                        list(self.outcomes),
                        preserve_lost_at=True,
                    )
                except Exception as save_err:
                    raise UpdateFailed(
                        "Could not persist cancellation evidence safety state"
                    ) from save_err
                self._journal_lost_saved = True
            self._fetch_task = asyncio.ensure_future(
                fetch(self.session, self.config["states"])
            )
            try:
                events = await self._fetch_task
            except asyncio.CancelledError:
                current_task = asyncio.current_task()
                if self._stopping and (
                    current_task is None or current_task.cancelling() == 0
                ):
                    return (
                        self.data
                        if getattr(self, "data", None) is not None
                        else self._stopped_health()
                    )
                raise
            finally:
                self._fetch_task = None
            if self._stopping:
                return (
                    self.data
                    if getattr(self, "data", None) is not None
                    else self._stopped_health()
                )
            now = datetime.now(timezone.utc)
            source_events = getattr(events, "all_events", events)
            candidate_events = resolve_candidates(
                self.records, events, source_events, now=now
            )
            conflicting_cancel = bool(
                getattr(events, "conflicting_cancellation", False)
            ) or any(
                _unrecoverable_prior_cancel_conflict(
                    event, self.records.get(event["id"])
                )
                for event in source_events
            )
            recoverable_prior_conflict = any(
                conflicting_prior_cancel(event, self.records.get(event["id"]))
                and not _unrecoverable_prior_cancel_conflict(
                    event, self.records.get(event["id"])
                )
                for event in source_events
            )
            malformed_cancel = bool(
                getattr(events, "uncertain_cancellation", False)
            ) or any(
                event.get("status") == "Actual"
                and event.get("message_type") == "Cancel"
                and not event.get("references")
                for event in source_events
            )
            # Initial shadow setup establishes a baseline; every subsequent restart reconciles normally.
            baseline = not self.initialized and not live(self.config)
            degraded_trigger = (
                "conflicting_cancellation"
                if conflicting_cancel
                else "malformed_cancellation"
                if malformed_cancel
                else None
            )
            plans = []
            overflow_horizon = None
            try:
                records, plans = reconcile(
                    self.records,
                    candidate_events,
                    self.config,
                    now,
                    baseline=baseline,
                    activate=live(self.config) and not self.was_live,
                    partial=bool(getattr(events, "quarantined", 0)),
                    quarantine_lineages=getattr(events, "quarantined_lineages", ()),
                    quarantine_all=getattr(events, "quarantine_ambiguous", False),
                    graph_events=source_events,
                    quarantine_cancel_lineages=getattr(
                        events, "quarantined_cancel_lineages", ()
                    ),
                )
            except CancellationEvidenceOverflow as err:
                records = err.records if err.records is not None else self.records
                plans = list(getattr(err, "plans", None) or ())
                degraded_trigger = "cancellation_evidence_overflow"
                overflow_horizon = (
                    timestamp(err.dropped_horizon)
                    if isinstance(err.dropped_horizon, str)
                    else err.dropped_horizon
                )
            if degraded_trigger is not None:
                self._latch_degraded(degraded_trigger, now, overflow_horizon)
            elif self.degraded:
                horizon = (
                    MAX_AGE
                    if self.degraded_reason == "outbox_overflow"
                    else MAX_ACCEPTANCE_AGE
                )
                if self.degraded_at is None:
                    self.degraded_at = now.isoformat()
                    self.degraded_until = (now + horizon).isoformat()
                elif self.degraded_until is None:
                    self.degraded_until = (
                        (timestamp(self.degraded_at) or now) + horizon
                    ).isoformat()
                until = timestamp(self.degraded_until)
                if until is not None and now > until:
                    self.degraded = False
                    self.degraded_reason = None
                    self.degraded_at = None
                    self.degraded_until = None
                    self.acknowledge_rejected = False
            degraded_delta = (
                now - last_ts
                if (
                    self.degraded_reason != "outbox_overflow"
                    and self.last_degraded_poll is not None
                    and (last_ts := timestamp(self.last_degraded_poll)) is not None
                    and now > last_ts
                )
                else None
            )
            # Carry an undelivered item through equivalent NWS update identifiers.
            # Reconciled records contain only trusted Alert/Update edges;
            # raw source references could reconnect a quarantined forgery.
            groups, _ = lineage_index(records, [])
            outbox = self._migrate_and_prune_outbox(
                records, candidate_events, now, groups, degraded_delta=degraded_delta
            )
            if self.degraded and self.degraded_reason != "outbox_overflow":
                self._ack_cleared_on_load = False
                return await self._persist_degraded_poll(
                    records,
                    plans,
                    outbox,
                    groups,
                    events,
                    candidate_events,
                    now,
                    triggered_now=(degraded_trigger is not None),
                    recoverable_prior_conflict=recoverable_prior_conflict,
                )
            (
                outbox,
                outbox_overflow,
                dropped_plans,
                records,
                attempts,
                failures,
                already_delivered,
            ) = await self._queue_outbox_plans(
                records, plans, outbox, candidate_events, groups, now
            )
            if outbox_overflow:
                self._latch_degraded("outbox_overflow", now, now + MAX_AGE)
                self._ack_cleared_on_load = False
                self._strip_withheld_actions(records, dropped_plans, groups, now)
                self.last_degraded_poll = None
                await self._save(records, outbox, list(self.outcomes))
                if not already_delivered:
                    attempts, failures = await self._deliver_outbox_batch(
                        candidate_events, now
                    )
                self._sync_degraded_notification()
                return self._degraded_health(
                    events=events,
                    candidate_events=candidate_events,
                    records=records,
                    now=now,
                    triggered_now=True,
                    recoverable_prior_conflict=recoverable_prior_conflict,
                    planned_count=len(plans) - len(dropped_plans),
                    withheld_count=len(dropped_plans),
                    delivery_attempts=attempts,
                    delivery_failures=failures,
                )
            if self.degraded and self.degraded_reason == "outbox_overflow":
                self.degraded = False
                self.degraded_reason = None
                self.degraded_at = None
                self.degraded_until = None
                self.acknowledge_rejected = False
            self._ack_cleared_on_load = False
            self.last_degraded_poll = None
            await self._save(records, outbox, list(self.outcomes))
            if not already_delivered:
                attempts, failures = await self._deliver_outbox_batch(
                    candidate_events, now
                )
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(
                f"NWS collection or state persistence failed: {type(err).__name__}"
            ) from err
        return self._healthy_snapshot(
            events,
            candidate_events,
            records,
            plans,
            now,
            attempts,
            failures,
            recoverable_prior_conflict,
        )


async def async_setup_entry(hass, entry):
    try:
        config = await hass.async_add_executor_job(
            _read_config, hass.config.path("situareness.json")
        )
    except (ValueError, OSError, json.JSONDecodeError) as err:
        raise ConfigEntryNotReady(f"Invalid situareness.json: {err}") from err
    prefix = f"{DOMAIN}.{entry.entry_id}"
    store = Store(hass, 1, prefix, private=True)
    has_corrupt_backup = False
    try:
        persisted = await store.async_load()
    except (json.JSONDecodeError, ValueError, NotImplementedError):
        persisted = ["unreadable"]
    except Exception as err:
        cause = getattr(err, "__cause__", None)
        if isinstance(err, OSError) or isinstance(cause, OSError):
            raise ConfigEntryNotReady(f"Could not read persisted store: {err}") from err
        if (
            isinstance(cause, (ValueError, NotImplementedError))
            or type(err).__name__ == "UnsupportedStorageVersionError"
        ):
            persisted = ["unreadable"]
        else:
            raise ConfigEntryNotReady(f"Could not load persisted store: {err}") from err
    if persisted is None and await hass.async_add_executor_job(
        _has_corrupt_store_backup, hass.config.path(".storage"), prefix
    ):
        has_corrupt_backup = True
        persisted = ["corrupt_json"]
    coordinator = SituarenessCoordinator(
        hass,
        config,
        store,
        persisted,
        entry=entry,
        has_corrupt_backup=has_corrupt_backup,
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _dismiss_degraded_notification(hass):
    persistent_notification.async_dismiss(hass, "situareness_degraded")


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.data[DOMAIN][entry.entry_id].async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _dismiss_degraded_notification(hass)
        return True
    return False


async def async_remove_entry(hass, entry):
    """Delete the private journal when the integration entry is removed."""
    _dismiss_degraded_notification(hass)
    prefix = f"{DOMAIN}.{entry.entry_id}"
    await Store(hass, 1, prefix, private=True).async_remove()
    await hass.async_add_executor_job(
        _clear_corrupt_store_backups, hass.config.path(".storage"), prefix
    )
