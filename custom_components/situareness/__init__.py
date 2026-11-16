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
from .collector import fetch
from .config import validate
from .const import DOMAIN
from .delivery import deliver_one, live, pending_valid, targets
from .domain import qualify, reconcile

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
        self.initialized = persisted.get("initialized") is True
        self.was_live = persisted.get("was_live") is True
        self.session = async_get_clientsession(hass)

    async def _save(self, records, outbox, outcomes):
        await self.store.async_save(
            {
                "records": records,
                "outbox": outbox,
                "outcomes": outcomes[-100:],
                "initialized": True,
                "was_live": live(self.config),
            }
        )
        self.records, self.outbox, self.outcomes, self.initialized = (
            records,
            outbox,
            outcomes[-100:],
            True,
        )
        self.was_live = live(self.config)

    async def _async_update_data(self):
        try:
            events = await fetch(self.session, self.config["states"])
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
            )
            # Carry an undelivered item through equivalent NWS update identifiers.
            successors = {}
            for event in events:
                for ref in event["references"]:
                    successors.setdefault(ref, []).append(event["id"])
            candidates = []
            for item in self.outbox:
                if not isinstance(item, dict):
                    continue
                matches = []
                incident = item.get("incident_id")
                successor_ids = set(successors.get(incident, []))
                old = self.records.get(incident, {})
                if old.get("state") != "cancelled" and isinstance(
                    old.get("lineage"), list
                ):
                    lineage = set(old["lineage"])
                    successor_ids.update(
                        event["id"]
                        for event in events
                        if lineage.intersection({event["id"], *event["references"]})
                    )
                for successor in successor_ids:
                    candidate = {**item, "incident_id": successor}
                    if pending_valid(
                        candidate, records, self.config, now, allow_suspended=True
                    ):
                        matches.append(candidate)
                if matches:
                    item = sorted(
                        matches,
                        key=lambda x: (
                            records[x["incident_id"]]["state"] != "active",
                            x["incident_id"],
                        ),
                    )[0]
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
                existing = {x["key"] for x in outbox}
                for plan in plans:
                    for item in targets(plan, self.config, now):
                        if item["key"] not in existing:
                            outbox.append(item)
                            existing.add(item["key"])
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
        except Exception as err:
            raise UpdateFailed(
                f"NWS collection or state persistence failed: {type(err).__name__}"
            ) from err
        return {
            "last_success": now.isoformat(),
            "event_count": len(events),
            "active_count": sum(r["state"] == "active" for r in records.values()),
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
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False


async def async_remove_entry(hass, entry):
    """Delete the private journal when the integration entry is removed."""
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
