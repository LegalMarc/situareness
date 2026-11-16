"""Pure, conservative NWS alert policy. No Home Assistant dependencies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from copy import deepcopy
from hashlib import sha256
import json
import math
from urllib.parse import urlparse


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def safe_url(value):
    try:
        u = urlparse(value)
        return (
            value
            if u.scheme == "https"
            and u.hostname == "api.weather.gov"
            and not u.username
            and not u.password
            and u.port in (None, 443)
            else None
        )
    except (TypeError, ValueError):
        return None


def normalize(feature):
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        return None
    p = feature.get("properties")
    if not isinstance(p, dict):
        return None
    identifier = feature.get("id")
    if (
        not isinstance(identifier, str)
        or len(identifier) > 512
        or not identifier.isascii()
        or not safe_url(identifier)
        or not identifier.startswith("https://api.weather.gov/alerts/")
    ):
        return None
    for key in (
        "event",
        "status",
        "messageType",
        "sent",
        "effective",
        "onset",
        "expires",
        "ends",
        "urgency",
        "certainty",
        "instruction",
        "headline",
    ):
        if p.get(key) is not None and (
            not isinstance(p[key], str) or len(p[key]) > 10000
        ):
            return None
    refs = p.get("references") if isinstance(p.get("references"), list) else []
    references = [
        r.get("@id") for r in refs if isinstance(r, dict) and safe_url(r.get("@id"))
    ]
    return {
        "id": identifier,
        "event": p.get("event"),
        "headline": p.get("headline"),
        "status": p.get("status"),
        "message_type": p.get("messageType"),
        "sent": p.get("sent"),
        "effective": p.get("effective"),
        "onset": p.get("onset"),
        "expires": p.get("expires"),
        "ends": p.get("ends"),
        "urgency": p.get("urgency"),
        "certainty": p.get("certainty"),
        "instruction": p.get("instruction"),
        "geometry": feature.get("geometry"),
        "references": references,
    }


def _ring(point, ring):
    """Point-in-ring with boundaries included. Reject malformed coordinate sets."""
    if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError("invalid ring")
    pts = []
    for coord in ring:
        if not isinstance(coord, list) or len(coord) < 2:
            raise ValueError("invalid coordinate")
        x, y = coord[:2]
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, (int, float))
            or not isinstance(y, (int, float))
            or not math.isfinite(x)
            or not math.isfinite(y)
            or not (-180 <= x <= 180 and -90 <= y <= 90)
        ):
            raise ValueError("invalid coordinate")
        pts.append((x, y))
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(pts, pts[1:])):
        raise ValueError("antimeridian geometry unsupported")
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if (
            abs(cross) < 1e-10
            and min(x1, x2) - 1e-10 <= x <= max(x1, x2) + 1e-10
            and min(y1, y2) - 1e-10 <= y <= max(y1, y2) + 1e-10
        ):
            return "boundary"
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return "inside" if inside else "outside"


def matches(point, geometry):
    """Only explicitly configured private points and valid NWS polygons qualify."""
    try:
        if not isinstance(point, list) or len(point) != 2:
            return False
        x, y = point
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, (int, float))
            or not isinstance(y, (int, float))
            or not math.isfinite(x)
            or not math.isfinite(y)
            or not (-180 <= x <= 180 and -90 <= y <= 90)
        ):
            return False
        kind, coords = geometry["type"], geometry["coordinates"]
        polygons = (
            [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
        )
        if not isinstance(polygons, list) or not polygons:
            return False
        found = False
        for poly in polygons:
            if not isinstance(poly, list) or not poly:
                raise ValueError("invalid polygon")
            outer = _ring(point, poly[0])
            holes = [_ring(point, r) for r in poly[1:]]
            # Hole boundaries are ambiguous: fail closed.
            if outer != "outside" and all(h == "outside" for h in holes):
                found = True
        return found
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def qualify(event, config, now):
    reasons = []
    if event.get("status") != "Actual" or event.get("message_type") not in (
        "Alert",
        "Update",
    ):
        reasons.append("not an actual alert or update")
    prefixes = config.get("approved_rules", {}).get(event.get("event"), [])
    instruction = event.get("instruction")
    if not prefixes:
        reasons.append("event not approved")
    if not isinstance(instruction, str) or not instruction.strip():
        reasons.append("missing official protective instruction")
    elif not any(
        instruction.strip().casefold().startswith(prefix.strip().casefold())
        for prefix in prefixes
    ):
        reasons.append("instruction does not match an approved protective action")
    if event.get("urgency") not in ("Immediate", "Expected") or event.get(
        "certainty"
    ) not in ("Observed", "Likely"):
        reasons.append("urgency or certainty not sufficient")
    sent, effective, expires = (
        timestamp(event.get(k)) for k in ("sent", "effective", "expires")
    )
    onset = timestamp(event.get("onset")) if event.get("onset") else effective
    ends = timestamp(event.get("ends")) if event.get("ends") else expires
    if (
        not all((sent, effective, expires, onset, ends))
        or sent > now + timedelta(minutes=5)
        or effective > now
        or expires <= now
        or ends <= now
        or onset > now + timedelta(hours=6)
        or sent >= expires
        or effective >= expires
        or onset >= ends
        or effective >= ends
    ):
        reasons.append("outside action window or missing valid times")
    affected = sorted(
        k
        for k, v in config.get("locations", {}).items()
        if matches(v.get("point"), event.get("geometry"))
    )
    if not affected:
        reasons.append("no matching private household footprint")
    return {
        "qualifies": not reasons,
        "reasons": reasons,
        "affected": affected if not reasons else [],
    }


def fingerprint(event, decision):
    # A changed protective instruction or newly affected household merits reevaluation.
    value = [event.get(k) for k in ("event", "instruction", "urgency", "certainty")] + [
        decision["affected"]
    ]
    return sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def reconcile(previous, events, config, now, baseline=False, activate=False):
    """Return bounded incident journal and plans. Only complete successful polls call this."""
    records = deepcopy(previous or {})
    plans = []
    seen = set()
    for event in events:
        eid = event["id"]
        decision = qualify(event, config, now)
        fp = fingerprint(event, decision)
        # Compare against the current members of the referenced lineage before
        # superseding them. Older references can remain in later CAP updates.
        predecessors = [records.get(eid)] + [
            records.get(ref) for ref in event.get("references", []) if ref != eid
        ]
        equivalent_active = any(
            record
            and record.get("state") == "active"
            and record.get("fingerprint") == fp
            for record in predecessors
        )
        for ref in event.get("references", []):
            if ref in records and ref != eid:
                records[ref] = {**records[ref], "state": "superseded"}
        if (
            decision["qualifies"]
            and not baseline
            and (activate or not equivalent_active)
        ):
            plans.append(
                {
                    "id": eid,
                    "phones": list(config.get("phones", [])),
                    "affected": decision["affected"],
                    "instruction": event["instruction"],
                    "event": event["event"],
                    "fingerprint": fp,
                }
            )
        records[eid] = {
            "state": "active" if decision["qualifies"] else "ineligible",
            "fingerprint": fp,
            "reasons": decision["reasons"],
            "affected": decision["affected"],
            "updated": now.isoformat(),
        }
        seen.add(eid)
    for eid, record in records.items():
        if eid not in seen and record.get("state") == "active":
            record["state"] = "ended_or_absent"
            record["updated"] = now.isoformat()
    records = dict(
        sorted(
            records.items(), key=lambda item: item[1].get("updated", ""), reverse=True
        )[:1000]
    )
    return records, plans
