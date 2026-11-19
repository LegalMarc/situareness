"""Gated, per-target delivery and durable outbox planning."""

import asyncio
from datetime import datetime, timedelta
import hashlib
import json
from .domain import action_history

MAX_ATTEMPTS = 3
MAX_AGE = timedelta(minutes=15)


def live(config):
    return (
        config.get("live_enabled") is True
        and config.get("commissioning_passed") is True
    )


def targets(plan, config, now):
    """Produce individual, stable work items only from a qualifying plan."""
    items = []
    specs = [("phone", phone, None) for phone in plan["phones"]]
    if config.get("tts_entity"):
        specs += [
            ("speaker", speaker, loc)
            for loc in plan["affected"]
            for speaker in config["locations"][loc].get("speakers", [])
        ]
    for kind, target, location in specs:
        key = hashlib.sha256(
            json.dumps(
                [plan["id"], plan["fingerprint"], kind, target, location]
            ).encode()
        ).hexdigest()
        items.append(
            {
                "key": key,
                "incident_id": plan["id"],
                "fingerprint": plan["fingerprint"],
                "kind": kind,
                "target": target,
                "location": location,
                "event": plan["event"],
                "instruction": plan["instruction"],
                "affected_names": [
                    config["locations"][loc].get("name", loc)
                    for loc in plan["affected"]
                ],
                "source_url": plan["id"],
                "created": now.isoformat(),
                "attempts": 0,
            }
        )
    return items


def pending_valid(item, records, config, now, *, allow_suspended=False):
    try:
        created = datetime.fromisoformat(item["created"])
        record = records.get(item["incident_id"], {})
        if (
            created.tzinfo is None
            or created > now
            or now - created > MAX_AGE
            or not 0 <= item["attempts"] < MAX_ATTEMPTS
        ):
            return False
        active = (
            record.get("state") == "active"
            and record.get("fingerprint") == item["fingerprint"]
        )
        suspended = (
            allow_suspended
            and record.get("state")
            in ("ineligible", "ended_or_absent", "quarantined", "unconfirmed")
            and item["fingerprint"] in action_history(record)
        )
        if not (active or suspended):
            return False
        if item["kind"] == "phone":
            return item["target"] in config["phones"]
        if item["kind"] == "speaker":
            location = item["location"]
            return (
                bool(config.get("tts_entity"))
                and location
                in (
                    record.get("affected", [])
                    if active
                    else action_history(record).get(item["fingerprint"], [])
                )
                and item["target"]
                in config["locations"].get(location, {}).get("speakers", [])
            )
        return False
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _active_target_record(item, records):
    if not isinstance(item, dict):
        return False
    incident_id = item.get("incident_id")
    fingerprint = item.get("fingerprint")
    if not isinstance(incident_id, str) or not isinstance(fingerprint, str):
        return False
    record = records.get(incident_id, {})
    return (
        record.get("state") == "active" and record.get("fingerprint") == fingerprint
    ) or (
        record.get("state") in ("quarantined", "unconfirmed")
        and record.get("prior_state") == "active"
        and fingerprint in action_history(record)
    )


def expired_by_age(item, records, config, now):
    """Return True when an unexhausted queued target for an active or suspended-from-active alert is invalid or expired."""
    try:
        if pending_valid(item, records, config, now, allow_suspended=True):
            return False
        attempts = item["attempts"]
        if (
            isinstance(attempts, bool)
            or not isinstance(attempts, int)
            or not 0 <= attempts < MAX_ATTEMPTS
        ):
            return False
        return _active_target_record(item, records)
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def expiry_reason(item, records, config, now, *, check_exhausted=False):
    """Classify why a queued active-alert target failed delivery."""
    if check_exhausted:
        try:
            if _active_target_record(item, records):
                attempts = item.get("attempts")
                if (
                    not isinstance(attempts, bool)
                    and isinstance(attempts, int)
                    and attempts >= MAX_ATTEMPTS
                ):
                    return "exhausted"
        except (KeyError, TypeError):
            return None
    if not expired_by_age(item, records, config, now):
        return None
    try:
        created = datetime.fromisoformat(item["created"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return "clock_rollback"
    if created.tzinfo is None or created > now:
        return "clock_rollback"
    if now - created > MAX_AGE:
        return "age"
    return "target_removed"


def _phone_payload(item):
    """Bound serialized HA service data, leaving room for the provider envelope."""
    url = item["source_url"]
    names = item.get("affected_names", [])
    shown = []
    for name in names:
        if len(", ".join(shown + [name])) > 150:
            break
        shown.append(name)
    labels = ", ".join(shown) or "multiple locations"
    if len(shown) < len(names):
        labels += f" and {len(names) - len(shown)} other locations"
    payload = {
        "title": "Situareness critical alert",
        "message": "",
        "data": {
            "url": url,
            "push": {"sound": {"name": "default", "critical": 1, "volume": 1.0}},
        },
    }
    instruction = item["instruction"].strip()
    prefix = f"{item['event'][:100]}. Affected: {labels}. "
    suffix = f" Source: {url}"
    payload["message"] = prefix + instruction + suffix

    def size():
        return len(json.dumps(payload, ensure_ascii=True).encode("utf-8"))

    if size() > 2800:
        marker = "... Open source for full instructions."
        payload["message"] = prefix + marker + suffix
        if size() > 2800:
            prefix = f"{item['event'][:64]}. Affected: multiple locations. "
        # Binary search takes JSON escaping and multi-byte characters into account.
        lo, hi = 0, len(instruction)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            payload["message"] = prefix + instruction[:mid] + marker + suffix
            if size() <= 2800:
                lo = mid
            else:
                hi = mid - 1
        payload["message"] = prefix + instruction[:lo].rstrip() + marker + suffix
        if size() > 2800:
            raise ValueError("notification metadata exceeds payload budget")
    return payload


def _speaker_text(item, config):
    location = item["location"]
    name = config["locations"][location].get("name", location)
    prefix = f"{item['event'][:100]}. Affected: {name[:100]}. "
    instruction = item["instruction"].strip()
    if len(instruction) > 300:
        instruction = instruction[:300].rsplit(" ", 1)[0].rstrip(" ,.;:")
        instruction += (
            ". Open the source link in the phone alert for full instructions."
        )
    return prefix + instruction


async def deliver_one(services, item, config):
    """Return None when gated, otherwise service acceptance (not human receipt)."""
    if not live(config):
        return None
    try:
        if item["kind"] == "phone":
            domain, service = "notify", item["target"]
            data = _phone_payload(item)
        elif item["kind"] == "speaker":
            domain, service = "tts", "speak"
            data = {
                "entity_id": config["tts_entity"],
                "media_player_entity_id": item["target"],
                "message": _speaker_text(item, config),
            }
        else:
            return False
        await asyncio.wait_for(
            services.async_call(domain, service, data, blocking=True), timeout=15
        )
        return True
    except Exception:
        return False
