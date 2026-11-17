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
from .collector import CancellationEvidenceLost, fetch
from .config import validate
from .const import DOMAIN
from .delivery import deliver_one, live, pending_valid, targets
from .domain import (
    CancellationEvidenceOverflow,
    action_history,
    lineage_index,
    qualify,
    reconcile,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


def _read_config(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            return validate(json.load(stream))
    except FileNotFoundError:
        return validate({})


class SituarenessCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config, store, persisted):
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=1)
        )
        self.config = config
        self.store = store
        malformed_store = persisted is not None and not isinstance(persisted, dict)
        persisted = persisted if isinstance(persisted, dict) else {}
        self.records = (
            persisted.get("records", {})
            if isinstance(persisted.get("records", {}), dict)
            else {}
        )
        self.outbox = (
            persisted.get("outbox", [])
            if isinstance(persisted.get("outbox", []), list)
            else []
        )
        self.outcomes = (
            persisted.get("outcomes", [])
            if isinstance(persisted.get("outcomes", []), list)
            else []
        )
        self.initialized = persisted.get("initialized") is True or (
            "initialized" not in persisted and bool(self.records or self.outbox)
        )
        # An absent legacy gate marker is not a new live-mode transition.
        self.was_live = persisted.get("was_live") is True or (
            "was_live" not in persisted and self.initialized
        )
        self.degraded = (
            malformed_store
            or persisted.get("degraded") is True
            or (
                persisted.get("initialized") is True
                and not isinstance(persisted.get("records"), dict)
            )
            or ("outbox" in persisted and not isinstance(persisted["outbox"], list))
        )
        self.session = async_get_clientsession(hass)
        self._refresh_lock = asyncio.Lock()
        self._stopping = False

    async def _save(self, records, outbox, outcomes):
        await self.store.async_save(
            {
                "records": records,
                "outbox": outbox,
                "outcomes": outcomes[-100:],
                "initialized": True,
                "was_live": live(self.config),
                "degraded": self.degraded,
            }
        )
        self.records, self.outbox, self.outcomes, self.initialized = (
            records,
            outbox,
            outcomes[-100:],
            True,
        )
        self.was_live = live(self.config)

    async def async_stop(self):
        self._stopping = True
        async with self._refresh_lock:
            pass

    async def _async_update_data(self):
        async with self._refresh_lock:
            if self._stopping:
                raise UpdateFailed("integration is stopping")
            return await self._update_once()

    def _degraded_health(self):
        """Expose a redacted durable evidence-loss state without delivering."""
        previous = getattr(self, "data", None) or {}
        return {
            "last_success": previous.get("last_success"),
            "event_count": 0,
            "source_feature_count": 0,
            "active_count": None,
            "partial": True,
            "quarantined_count": 0,
            "quarantine_ambiguous": True,
            "cancellation_uncertain": True,
            "evidence_degraded": True,
            "output_blocked": True,
            "shadow": not live(self.config),
            "events": [],
            "planned_count": 0,
            "pending_count": len(self.outbox),
            "deliverable_count": 0,
            "suspended_count": len(self.outbox),
            "delivery_attempts": 0,
            "delivery_failures": 0,
        }

    async def _update_once(self):
        try:
            if self.degraded:
                return self._degraded_health()
            events = await fetch(self.session, self.config["states"])
            source_events = getattr(events, "all_events", events)
            conflicting_cancel = any(
                (old := self.records.get(event["id"], {})).get("cancel_message")
                and (
                    event.get("status") != "Actual"
                    or event.get("message_type") != "Cancel"
                    or event.get("cap_identity") != old.get("cap_identity")
                    or event.get("reference_identities") != old.get("cap_references")
                )
                or (
                    event.get("status") == "Actual"
                    and event.get("message_type") == "Cancel"
                    and (old := self.records.get(event["id"])) is not None
                    and not old.get("cancel_message")
                )
                for event in source_events
            )
            if (
                conflicting_cancel
                or getattr(events, "uncertain_cancellation", False)
                or any(
                    event.get("status") == "Actual"
                    and event.get("message_type") == "Cancel"
                    and (
                        not event.get("cap_identity")
                        or not event.get("cap_references_valid")
                        or not event.get("reference_identities")
                    )
                    for event in source_events
                )
            ):
                self.degraded = True
                await self._save(self.records, self.outbox, self.outcomes)
                return self._degraded_health()
            now = datetime.now(timezone.utc)
            # Initial shadow setup establishes a baseline; every subsequent restart reconciles normally.
            baseline = not self.initialized and not live(self.config)
            records, plans = reconcile(
                self.records,
                events,
                self.config,
                now,
                baseline=baseline,
                activate=live(self.config) and not self.was_live,
                partial=bool(getattr(events, "quarantined", 0)),
                quarantine_lineages=getattr(events, "quarantined_lineages", ()),
                quarantine_all=getattr(events, "quarantine_ambiguous", False),
                graph_events=getattr(events, "all_events", events),
            )
            # Carry an undelivered item through equivalent NWS update identifiers.
            groups, _ = lineage_index(records, events)
            event_index = {}
            for event in events:
                eid = event["id"]
                record = records[eid]
                if record["state"] in ("active", "ineligible"):
                    for fp in action_history(record):
                        event_index.setdefault((groups[eid], fp), []).append(eid)
            for ids in event_index.values():
                ids.sort(key=lambda eid: (records[eid]["state"] != "active", eid))
            cancellation_groups = {
                groups.get(eid)
                for eid, record in records.items()
                if record.get("cancel_message")
            }
            current_events = {event["id"]: event for event in events}
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
                elif groups.get(incident) in cancellation_groups:
                    source_identity = records.get(incident, {}).get("cap_identity")
                    successors = [
                        eid
                        for eid in successors
                        if eid == incident
                        or (
                            source_identity
                            and source_identity
                            in current_events[eid].get("reference_identities", [])
                            and current_events[eid].get("cap_references_valid")
                        )
                    ]
                    if (
                        not successors
                        and records.get(incident, {}).get("state") == "superseded"
                    ):
                        records[incident] = {
                            **records[incident],
                            "state": "unconfirmed",
                            "prior_state": "active",
                        }
                if successors:
                    successor = successors[0]
                    candidate = {
                        **item,
                        "incident_id": successor,
                        "source_url": successor,
                    }
                    if pending_valid(
                        candidate, records, self.config, now, allow_suspended=True
                    ):
                        item = candidate
                candidates.append(item)
            outbox = (
                [
                    x
                    for x in candidates
                    if pending_valid(x, records, self.config, now, allow_suspended=True)
                ]
                if live(self.config)
                else []
            )
            if live(self.config):

                def signature(x):
                    return (
                        groups.get(x["incident_id"]),
                        x["fingerprint"],
                        x["kind"],
                        x["target"],
                        x["location"],
                    )

                unique = {}
                for item in outbox:
                    key = signature(item)
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
                outbox = list(unique.values())
                existing = set(unique)
                for plan in plans:
                    for item in targets(plan, self.config, now):
                        if signature(item) not in existing:
                            outbox.append(item)
                            existing.add(signature(item))
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
            by_id = {event["id"]: event for event in events}
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
        except (CancellationEvidenceLost, CancellationEvidenceOverflow):
            self.degraded = True
            try:
                await self._save(self.records, self.outbox, self.outcomes)
            except Exception as save_err:
                raise UpdateFailed(
                    "Could not persist cancellation evidence safety state"
                ) from save_err
            return self._degraded_health()
        except Exception as err:
            raise UpdateFailed(
                f"NWS collection or state persistence failed: {type(err).__name__}"
            ) from err
        by_id = {event["id"]: event for event in events}
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
            records[e["id"]]["state"] == "quarantined" for e in events
        )
        cancellation_uncertain = any(
            record.get("state") == "quarantined"
            and "cancellation scope uncertain" in record.get("reasons", [])
            for record in records.values()
        )
        return {
            "last_success": now.isoformat(),
            "event_count": len(events),
            "source_feature_count": getattr(events, "source_count", len(events)),
            "active_count": sum(records[e["id"]]["state"] == "active" for e in events),
            "partial": bool(quarantine_count) or cancellation_uncertain,
            "cancellation_uncertain": cancellation_uncertain,
            "evidence_degraded": False,
            "output_blocked": False,
            "quarantined_count": quarantine_count,
            "quarantine_ambiguous": bool(
                getattr(events, "quarantine_ambiguous", False)
            ),
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
                for e in events[:25]
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
    coordinator = SituarenessCoordinator(hass, config, store, persisted)
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
