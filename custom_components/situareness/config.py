"""Validate private administrator-owned configuration."""

import re
import math

STATES = {"NY", "DC"}
IDENT = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SERVICE = re.compile(r"^mobile_app_[a-z0-9_]+$")
ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError("configuration must be an object")
    states = raw.get("states", sorted(STATES))
    if (
        not isinstance(states, list)
        or not states
        or len(states) > 10
        or any(
            not isinstance(s, str) or not re.fullmatch(r"[A-Z]{2}", s) for s in states
        )
    ):
        raise ValueError("states must be a nonempty list of state codes")
    locations = raw.get("locations", {})
    if not isinstance(locations, dict) or len(locations) > 50:
        raise ValueError("locations must be an object")
    speaker_count = 0
    for name, loc in locations.items():
        if (
            not isinstance(name, str)
            or not IDENT.fullmatch(name)
            or not isinstance(loc, dict)
        ):
            raise ValueError("invalid location")
        name_value = loc.get("name", name)
        if (
            not isinstance(name_value, str)
            or not name_value.strip()
            or len(name_value) > 100
            or any(ord(ch) < 32 for ch in name_value)
        ):
            raise ValueError("invalid location name")
        p = loc.get("point")
        if p is not None and (
            not isinstance(p, list)
            or len(p) != 2
            or any(
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                for v in p
            )
            or not -180 <= p[0] <= 180
            or not -90 <= p[1] <= 90
        ):
            raise ValueError("invalid point")
        speakers = loc.get("speakers", [])
        if not isinstance(speakers, list) or any(
            not isinstance(x, str)
            or not ENTITY.fullmatch(x)
            or not x.startswith("media_player.")
            for x in speakers
        ):
            raise ValueError("invalid speakers")
        speaker_count += len(speakers)
    if speaker_count > 100:
        raise ValueError("too many speakers")
    phones = raw.get("phones", [])
    if (
        not isinstance(phones, list)
        or len(phones) > 50
        or any(not isinstance(x, str) or not SERVICE.fullmatch(x) for x in phones)
    ):
        raise ValueError("invalid phone services")
    approved = raw.get("approved_rules", {})
    if not isinstance(approved, dict) or len(approved) > 100:
        raise ValueError("invalid approved rules")
    for event, prefixes in approved.items():
        if (
            not isinstance(event, str)
            or not event.strip()
            or len(event) > 100
            or not isinstance(prefixes, list)
            or not prefixes
            or len(prefixes) > 50
            or any(
                not isinstance(p, str) or len(p.strip()) < 10 or len(p) > 300
                for p in prefixes
            )
        ):
            raise ValueError("invalid event or instruction prefixes")
    tts = raw.get("tts_entity")
    if tts is not None and (
        not isinstance(tts, str)
        or not ENTITY.fullmatch(tts)
        or not tts.startswith("tts.")
    ):
        raise ValueError("invalid TTS entity")
    for key in ("live_enabled", "commissioning_passed"):
        if key in raw and not isinstance(raw[key], bool):
            raise ValueError("live gates must be boolean")
    return {
        "states": list(dict.fromkeys(states)),
        "locations": locations,
        "phones": list(dict.fromkeys(phones)),
        "approved_rules": approved,
        "tts_entity": tts,
        "live_enabled": raw.get("live_enabled", False),
        "commissioning_passed": raw.get("commissioning_passed", False),
    }
