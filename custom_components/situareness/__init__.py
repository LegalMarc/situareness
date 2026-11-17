"""Independent NWS monitoring for Home Assistant."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

try:
    from homeassistant.components import persistent_notification
except ImportError:
    persistent_notification = None
from .collector import fetch
from .config import validate
from .const import DOMAIN
from .delivery import deliver_one, live, pending_valid, targets
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
    if reason is not None and not isinstance(reason, str):
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
            for list_key in ("lineage", "reasons", "affected"):
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
        if not isinstance(outbox, list):
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
    return not event.get("references") or (
        old.get("cancel_message") is True
        and not old.get("cap_references")
        and len(old.get("lineage", [])) <= 1
    )


class SituarenessCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config, store, persisted, entry=None):
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=1)
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
            if (
                self._entry is not None
                and self._entry.data.get("malformed_store_at") != stable_at
            ):
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    data={**self._entry.data, "malformed_store_at": stable_at},
                )
        elif (
            self._entry is not None
            and self._entry.data.get("journal_initialized") is True
            and (persisted is None or persisted == {})
        ):
            detect_now = datetime.now(timezone.utc)
            self.records = {}
            self.outbox = []
            self.outcomes = []
            self.initialized = True
            self.was_live = live(self.config)
            self.degraded = True
            self.degraded_reason = "journal_lost"
            self.degraded_at = detect_now.isoformat()
            self.degraded_until = (detect_now + MAX_ACCEPTANCE_AGE).isoformat()
            self.acknowledged_degraded_at = None
            self.last_degraded_poll = detect_now.isoformat()
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
                persisted.get("degraded_reason") or "cancellation_evidence_overflow"
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
        self._try_acknowledge(datetime.now(timezone.utc))
        self.session = async_get_clientsession(hass)
        self._refresh_lock = asyncio.Lock()
        self._fetch_task = None
        self._stopping = False
        self._notified_degraded_state = None
        self._checked_notification_clear = False

    def _try_acknowledge(self, current_now):
        if not self.degraded or self.degraded_reason == "malformed_store":
            return False
        ack = self.config.get("acknowledge_degraded_at")
        if ack is None or ack == self.acknowledged_degraded_at:
            return False
        degraded_at_ts = timestamp(self.degraded_at)
        ack_ts = timestamp(ack)
        if (
            degraded_at_ts is None
            or ack_ts is None
            or not (degraded_at_ts <= ack_ts <= current_now)
        ):
            return False
        self.acknowledged_degraded_at = ack
        self.degraded = False
        self.degraded_reason = None
        self.degraded_at = None
        self.degraded_until = None
        return True

    async def _save(self, records, outbox, outcomes):
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
        if self._entry is not None and (
            self._entry.data.get("journal_initialized") is not True
            or "malformed_store_at" in self._entry.data
        ):
            new_data = {
                k: v for k, v in self._entry.data.items() if k != "malformed_store_at"
            }
            new_data["journal_initialized"] = True
            self.hass.config_entries.async_update_entry(self._entry, data=new_data)

    def _sync_degraded_notification(self):
        if persistent_notification is None or not isinstance(
            getattr(self.hass, "data", None), dict
        ):
            return
        if self.degraded:
            state = (self.degraded_reason, self.degraded_until)
            if self._notified_degraded_state != state:
                until_note = (
                    f" Until: {self.degraded_until}."
                    if self.degraded_until
                    else " Manual store repair or replacement required."
                )
                persistent_notification.async_create(
                    self.hass,
                    f"Situareness output is blocked (reason: {self.degraded_reason})."
                    f"{until_note} Continue using independent official alert channels.",
                    title="Situareness monitoring degraded",
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

    async def _async_update_data(self):
        async with self._refresh_lock:
            if self._stopping:
                raise UpdateFailed("integration is stopping")
            return await self._update_once()

    def _degraded_health(
        self, events=None, candidate_events=None, records=None, now=None
    ):
        """Expose a redacted durable degraded state without delivering."""
        previous = getattr(self, "data", None) or {}
        shown = candidate_events if candidate_events is not None else events
        quarantined_count = 0
        event_summaries = []
        if shown is not None:
            record_map = records or {}
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
        triggered_now = now is not None and self.degraded_at == now.isoformat()
        cancellation_uncertain = (
            triggered_now
            and self.degraded_reason
            in (
                "cancellation_evidence_overflow",
                "malformed_cancellation",
                "conflicting_cancellation",
            )
        ) or any(
            r.get("state") == "quarantined"
            and "cancellation scope uncertain" in r.get("reasons", [])
            for r in (records or {}).values()
        )
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
            "active_count": None,
            "partial": (
                bool(quarantined_count)
                or quarantine_ambiguous
                or cancellation_uncertain
            ),
            "quarantined_count": quarantined_count,
            "quarantine_ambiguous": quarantine_ambiguous,
            "cancellation_uncertain": cancellation_uncertain,
            "evidence_degraded": True,
            "output_blocked": True,
            "degraded_reason": self.degraded_reason,
            "degraded_at": self.degraded_at,
            "degraded_until": self.degraded_until,
            "shadow": not live(self.config),
            "events": event_summaries,
            "planned_count": 0,
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

    async def _update_once(self):
        try:
            if self.degraded and self.degraded_reason == "malformed_store":
                self._sync_degraded_notification()
                return self._degraded_health()
            self._fetch_task = asyncio.ensure_future(
                fetch(self.session, self.config["states"])
            )
            try:
                events = await self._fetch_task
            except asyncio.CancelledError:
                if self._stopping:
                    return getattr(self, "data", None) or self._degraded_health()
                raise
            finally:
                self._fetch_task = None
            if self._stopping:
                return getattr(self, "data", None) or self._degraded_health()
            source_events = getattr(events, "all_events", events)
            candidate_events = resolve_candidates(self.records, events, source_events)
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
            now = datetime.now(timezone.utc)
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
                degraded_trigger = "cancellation_evidence_overflow"
                overflow_horizon = (
                    timestamp(err.dropped_horizon)
                    if isinstance(err.dropped_horizon, str)
                    else err.dropped_horizon
                )
            if degraded_trigger is not None:
                existing_until = timestamp(self.degraded_until)
                candidate_until = overflow_horizon or (now + MAX_ACCEPTANCE_AGE)
                new_until = (
                    max(existing_until, candidate_until)
                    if existing_until is not None
                    else candidate_until
                )
                self.degraded = True
                self.degraded_reason = degraded_trigger
                self.degraded_at = now.isoformat()
                self.degraded_until = new_until.isoformat()
            elif self.degraded:
                if self.degraded_at is None:
                    self.degraded_at = now.isoformat()
                    self.degraded_until = (now + MAX_ACCEPTANCE_AGE).isoformat()
                elif self.degraded_until is None:
                    self.degraded_until = (
                        (timestamp(self.degraded_at) or now) + MAX_ACCEPTANCE_AGE
                    ).isoformat()
                until = timestamp(self.degraded_until)
                if until is not None and now > until:
                    self.degraded = False
                    self.degraded_reason = None
                    self.degraded_at = None
                    self.degraded_until = None
            degraded_delta = (
                now - last_ts
                if (
                    self.last_degraded_poll is not None
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
            if self.degraded:
                withheld_keys = {
                    (groups.get(plan["id"]), plan["fingerprint"]) for plan in plans
                }
                for eid, record in records.items():
                    if record.get("updated") == now.isoformat():
                        rec_actions = record.get("actions")
                        if isinstance(rec_actions, dict):
                            for fp in list(rec_actions):
                                if (groups.get(eid), fp) in withheld_keys:
                                    rec_actions.pop(fp, None)
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
                )
            self.last_degraded_poll = None
            if live(self.config):
                existing = {_outbox_signature(groups, item, records) for item in outbox}
                for plan in plans:
                    for item in targets(plan, self.config, now):
                        if _outbox_signature(groups, item, records) not in existing:
                            outbox.append(item)
                            existing.add(_outbox_signature(groups, item, records))
            if len(outbox) > 5000:
                raise ValueError("delivery outbox limit reached")
            await self._save(records, outbox, list(self.outcomes))
            attempts = failures = 0
            # Each completed attempt is persisted. A crash between service call and save may duplicate it.
            batch = [
                x
                for x in self.outbox
                if pending_valid(x, self.records, self.config, now)
            ][:100]
            by_id = {event["id"]: event for event in candidate_events}
            deadline = now + timedelta(seconds=30)
            for offset in range(0, len(batch), 10):
                if self._stopping:
                    break
                current = datetime.now(timezone.utc)
                if current >= deadline:
                    break
                group = []
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
                        remaining = [x for x in self.outbox if x["key"] != item["key"]]
                        await self._save(self.records, remaining, self.outcomes)
                results = await asyncio.gather(
                    *(
                        deliver_one(self.hass.services, item, self.config)
                        for item in group
                    )
                )
                for item, accepted in zip(group, results):
                    if accepted is None:
                        break
                    attempts += 1
                    failures += not accepted
                    updated = {**item, "attempts": item["attempts"] + 1}
                    remaining = [x for x in self.outbox if x["key"] != item["key"]]
                    if not accepted and pending_valid(
                        updated, self.records, self.config, datetime.now(timezone.utc)
                    ):
                        remaining.append(updated)
                    outcomes = self.outcomes + [
                        {
                            "key": item["key"],
                            "accepted": accepted,
                            "attempt": updated["attempts"],
                            "at": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                    await self._save(self.records, remaining, outcomes)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(
                f"NWS collection or state persistence failed: {type(err).__name__}"
            ) from err
        by_id = {event["id"]: event for event in candidate_events}
        health_now = datetime.now(timezone.utc)
        current_eligible = {
            eid
            for eid, event in by_id.items()
            if records[eid]["state"] == "active"
            and qualify(event, self.config, health_now)["qualifies"]
        }
        deliverable = sum(
            item["incident_id"] in current_eligible
            and pending_valid(item, self.records, self.config, health_now)
            for item in self.outbox
        )
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
        self._sync_degraded_notification()
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
            "pending_count": len(self.outbox),
            "deliverable_count": deliverable,
            "suspended_count": len(self.outbox) - deliverable,
            "delivery_attempts": attempts,
            "delivery_failures": failures,
        }


async def async_setup_entry(hass, entry):
    try:
        config = await hass.async_add_executor_job(
            _read_config, hass.config.path("situareness.json")
        )
    except (ValueError, OSError, json.JSONDecodeError) as err:
        raise ConfigEntryNotReady(f"Invalid situareness.json: {err}") from err
    store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
    persisted = await store.async_load()
    coordinator = SituarenessCoordinator(hass, config, store, persisted, entry=entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.data[DOMAIN][entry.entry_id].async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False


async def async_remove_entry(hass, entry):
    """Delete the private journal when the integration entry is removed."""
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
