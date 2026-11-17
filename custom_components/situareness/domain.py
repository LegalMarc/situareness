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


class CancellationEvidenceOverflow(ValueError):
    """Cancellation evidence cannot fit safely in the durable journal."""


class OversizedFeature(ValueError):
    """A validly framed feature exceeds the per-lineage safety limit."""


def cap_identity(identifier, sender, sent):
    """Validate an NWS CAP identity tuple, normalizing its timestamp to UTC."""
    parsed = timestamp(sent)
    if (
        not isinstance(identifier, str)
        or not identifier
        or len(identifier) > 512
        or not identifier.isascii()
        or not isinstance(sender, str)
        or not sender
        or len(sender) > 512
        or not sender.isascii()
        or not parsed
    ):
        return None
    return [sender, identifier, parsed.isoformat()]


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
    if len(refs) > 100 or any(
        isinstance(r, dict) and isinstance(r.get("@id"), str) and len(r["@id"]) > 512
        for r in refs
    ):
        raise OversizedFeature("NWS reference limit exceeded")
    references = [
        r.get("@id") for r in refs if isinstance(r, dict) and safe_url(r.get("@id"))
    ]
    identity = cap_identity(p.get("id"), p.get("sender"), p.get("sent"))
    if identity and identifier != "https://api.weather.gov/alerts/" + identity[1]:
        identity = None
    reference_identities = []
    for ref in refs:
        if not isinstance(ref, dict):
            reference_identities.append(None)
            continue
        ref_identity = cap_identity(
            ref.get("identifier"), ref.get("sender"), ref.get("sent")
        )
        if (
            ref_identity
            and ref.get("@id") != "https://api.weather.gov/alerts/" + ref_identity[1]
        ):
            ref_identity = None
        reference_identities.append(ref_identity)
    return {
        "id": identifier,
        "cap_identity": identity,
        "reference_identities": reference_identities,
        "cap_references_valid": (
            p.get("references") is None or isinstance(p.get("references"), list)
        )
        and all(reference_identities),
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


def cap_event_valid(event):
    """Require internally consistent, chronologically directed CAP tuples."""
    identity = event.get("cap_identity")
    refs = event.get("reference_identities")
    references = event.get("references")
    if (
        not isinstance(identity, list)
        or len(identity) != 3
        or cap_identity(identity[1], identity[0], identity[2]) != identity
        or event.get("id") != "https://api.weather.gov/alerts/" + identity[1]
        or timestamp(event.get("sent")) != timestamp(identity[2])
        or event.get("cap_references_valid") is not True
        or not isinstance(refs, list)
        or not isinstance(references, list)
        or len(refs) != len(references)
    ):
        return False
    if event.get("message_type") in ("Update", "Cancel") and not refs:
        return False
    for ref, url in zip(refs, references):
        if (
            not isinstance(ref, list)
            or len(ref) != 3
            or cap_identity(ref[1], ref[0], ref[2]) != ref
            or url != "https://api.weather.gov/alerts/" + ref[1]
            or ref[2] >= identity[2]
        ):
            return False
    return True


def qualify(event, config, now):
    reasons = []
    if not cap_event_valid(event):
        reasons.append("invalid or incomplete CAP identity or references")
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


def action_history(record):
    """Return the last qualified action(s), including legacy journal records."""
    if isinstance(record.get("actions"), dict):
        return record["actions"]
    action = record.get("action_fingerprint")
    if not action and semantic_state(record) in ("active", "ended_or_absent"):
        action = record.get("fingerprint")
    return (
        {action: record.get("action_affected", record.get("affected", []))}
        if action
        else {}
    )


def semantic_state(record):
    """Keep local collection uncertainty separate from source inactivity."""
    state = record.get("state")
    if state in ("quarantined", "unconfirmed"):
        return record.get("prior_state") or "ineligible"
    return state


def suspend_record(record, state, now):
    previous = semantic_state(record)
    inactive_since = record.get("inactive_since")
    if previous in ("ineligible", "ended_or_absent") and not inactive_since:
        inactive_since = record.get("updated")
    return {
        **record,
        "actions": action_history(record),
        "state": state,
        "prior_state": previous,
        "inactive_since": inactive_since,
        "updated": now.isoformat(),
    }


def action_identity(event):
    """Material wording independent of temporary geometry or urgency changes."""
    value = [event.get("event"), event.get("instruction")]
    return sha256(json.dumps(value, ensure_ascii=True).encode()).hexdigest()


def lineage_index(records, events):
    """Union shared identifiers once; return component IDs and member records."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(ids):
        if not ids:
            return
        anchor = ids[0]
        find(anchor)
        for value in ids[1:]:
            a, b = find(anchor), find(value)
            if a != b:
                parent[b] = a

    for eid, record in records.items():
        union([eid, *record.get("lineage", [])])
    for event in events:
        union([event["id"], *event.get("references", [])])
    members = {}
    for eid in records:
        members.setdefault(find(eid), []).append(eid)
    return {eid: find(eid) for eid in parent}, members


def cancellation_evidence(records, events, groups, now=None):
    """Find explicit cancelled messages and directed, uncertain successors.

    Persisted edges are only authoritative when recorded with complete CAP
    tuples. Old journal lineage sets do not establish directed relationships.
    """

    identity_cache = {}

    def valid_identity(value):
        if (
            not isinstance(value, list)
            or len(value) != 3
            or not all(isinstance(v, str) for v in value)
        ):
            return False
        key = tuple(value)
        if key not in identity_cache:
            identity_cache[key] = cap_identity(value[1], value[0], value[2]) == value
        return identity_cache[key]

    nodes = {}
    cancellations = []
    ambiguous_groups = set()
    for eid, record in records.items():
        identity = record.get("cap_identity")
        refs = record.get("cap_references")
        is_cancel = record.get("cancel_message") is True
        if (
            valid_identity(identity)
            and eid == "https://api.weather.gov/alerts/" + identity[1]
            and isinstance(refs, list)
            and all(map(valid_identity, refs))
        ):
            nodes[eid] = (tuple(identity), [tuple(r) for r in refs], is_cancel)
            if is_cancel:
                cancellations.append(eid)
        elif is_cancel:
            ambiguous_groups.add(groups.get(eid))
    for event in events:
        eid = event["id"]
        is_cancel = (
            event.get("status") == "Actual" and event.get("message_type") == "Cancel"
        )
        identity = event.get("cap_identity")
        refs = event.get("reference_identities")
        valid = (
            valid_identity(identity)
            and eid == "https://api.weather.gov/alerts/" + identity[1]
            and timestamp(event.get("sent")) == timestamp(identity[2])
            and event.get("cap_references_valid")
            and isinstance(refs, list)
            and all(map(valid_identity, refs))
            and event.get("references")
            == ["https://api.weather.gov/alerts/" + ref[1] for ref in refs]
        )
        if not valid:
            if is_cancel:
                ambiguous_groups.add(groups.get(eid))
            continue
        node = (tuple(identity), [tuple(r) for r in refs], is_cancel)
        if eid in nodes and nodes[eid] != node:
            ambiguous_groups.add(groups.get(eid))
        nodes[eid] = node
        if is_cancel:
            cancellations.append(eid)
    identities = {}
    for eid, (identity, _, _) in nodes.items():
        identities.setdefault(identity, []).append(eid)
    by_identifier = {}
    for identity in identities:
        by_identifier.setdefault(identity[1], set()).add(identity)
    for eid, (identity, refs, _) in nodes.items():
        for ref in refs:
            if ref[2] >= identity[2]:
                ambiguous_groups.add(groups.get(eid))
            known = by_identifier.get(ref[1])
            if known and ref not in known:
                ambiguous_groups.add(groups.get(eid))
    valid_cancels = {
        identity
        for eid, (identity, refs, is_cancel) in nodes.items()
        if is_cancel
        and refs
        and groups.get(eid) not in ambiguous_groups
        and (now is None or timestamp(identity[2]) <= now + timedelta(minutes=5))
    }
    cancelled = set()
    cancelled_by_group = {}
    children = {}
    for eid, (identity, refs, is_cancel) in nodes.items():
        if is_cancel:
            if (
                not refs
                or any(ref[2] >= identity[2] for ref in refs)
                or (
                    now is not None
                    and timestamp(identity[2]) > now + timedelta(minutes=5)
                )
            ):
                ambiguous_groups.add(groups.get(eid))
            else:
                cancelled.update(refs)
                cancelled_by_group.setdefault(groups.get(eid), set()).update(refs)
            continue
        # An update that explicitly references a valid earlier Cancel is new
        # evidence. Other older references may supply history, not a path that
        # overrides the renewal boundary.
        if not any(ref in valid_cancels for ref in refs):
            for ref in refs:
                children.setdefault(ref, set()).add(identity)
    # If a referenced predecessor is missing, it may conceal a path from a
    # cancelled message. A predecessor strictly older than every cancelled
    # identity cannot descend from one under CAP's directed time ordering.
    cancellation_groups = {groups.get(eid) for eid in cancellations} | ambiguous_groups
    uncertain = set()
    for eid, (identity, refs, is_cancel) in nodes.items():
        group_targets = cancelled_by_group.get(groups.get(eid), set())
        if not is_cancel and group_targets:
            earliest = min(target[2] for target in group_targets)
            if any(ref not in identities and ref[2] >= earliest for ref in refs):
                uncertain.add(identity)
    pending = list(cancelled | uncertain)
    visited = set(pending)
    while pending:
        parent = pending.pop()
        for child in children.get(parent, ()):
            if child not in visited:
                visited.add(child)
                uncertain.add(child)
                pending.append(child)
    direct_ids = {eid for identity in cancelled for eid in identities.get(identity, ())}
    uncertain_ids = {
        eid for identity in uncertain for eid in identities.get(identity, ())
    } - direct_ids
    # A prior record with no directed identity metadata cannot be interpreted
    # as a sibling or descendant of a cancellation in its old component.
    uncertain_ids.update(
        eid
        for eid, record in records.items()
        if groups.get(eid) in cancellation_groups
        and eid not in nodes
        and not record.get("cancel_message")
    )
    uncertain_ids.update(
        event["id"]
        for event in events
        if groups.get(event["id"]) in cancellation_groups and event["id"] not in nodes
    )
    uncertain_ids.update(eid for eid in groups if groups.get(eid) in ambiguous_groups)
    return direct_ids, uncertain_ids


def reconcile(
    previous,
    events,
    config,
    now,
    baseline=False,
    activate=False,
    partial=False,
    quarantine_lineages=(),
    quarantine_all=False,
    graph_events=None,
):
    """Reconcile bounded history; quarantined inputs cannot end unrelated records."""
    graph_events = list(events if graph_events is None else graph_events)
    # Cancels are source evidence even when a later message references them.
    present = {event["id"] for event in events}
    events = list(events) + [
        event
        for event in graph_events
        if event["id"] not in present
        and event.get("status") == "Actual"
        and event.get("message_type") == "Cancel"
    ]
    prior = deepcopy(previous or {})
    records = deepcopy(prior)
    plans = []
    quarantine_events = [
        {"id": ids[0], "references": ids[1:]} for ids in quarantine_lineages if ids
    ]
    known_identities = {
        eid: record.get("cap_identity")
        for eid, record in prior.items()
        if isinstance(record.get("cap_identity"), list)
    }
    invalid_ids = set()
    for source in graph_events:
        if not cap_event_valid(source):
            invalid_ids.add(source["id"])
            continue
        known = known_identities.get(source["id"])
        if known is not None and known != source["cap_identity"]:
            invalid_ids.add(source["id"])
        else:
            known_identities[source["id"]] = source["cap_identity"]
    for source in graph_events:
        if source["id"] in invalid_ids:
            continue
        if any(
            ref in known_identities and known_identities[ref] != identity
            for ref, identity in zip(
                source["references"], source["reference_identities"]
            )
        ):
            invalid_ids.add(source["id"])
    grouping_events = [
        {**source, "references": []} if source["id"] in invalid_ids else source
        for source in graph_events
    ]
    groups, members = lineage_index(prior, [*grouping_events, *quarantine_events])
    trusted_events = [
        source for source in graph_events if source["id"] not in invalid_ids
    ]
    cancelled_ids, uncertain_ids = cancellation_evidence(
        prior, trusted_events, groups, now
    )
    quarantine_groups = {groups[e["id"]] for e in quarantine_events}
    if quarantine_all:
        quarantine_groups = set(groups.values())
    planned_in_poll = set()
    seen = set()
    referenced = set()
    quarantined = False
    inactive_states = {"ineligible", "ended_or_absent", "quarantined", "unconfirmed"}
    summaries = {}

    def merge_bounded(target, source):
        for key, value in source.items():
            target[key] = value
            if len(target) > 100:
                break

    for group, ids in members.items():
        summary = {
            "has_active": False,
            "active": {},
            "inactive": {},
            "active_identity": {},
            "inactive_identity": {},
            "inactive_since": None,
        }
        for record_id in ids:
            record = prior[record_id]
            if record_id in cancelled_ids or record_id in uncertain_ids:
                continue
            state = semantic_state(record)
            if state in ("superseded", "cancelled"):
                continue
            bucket = "inactive" if state in inactive_states else "active"
            if bucket == "inactive":
                since = timestamp(record.get("inactive_since") or record.get("updated"))
                if not since or since > now or now - since > timedelta(minutes=15):
                    continue
                summary["inactive_since"] = min(
                    summary["inactive_since"] or since, since
                )
            else:
                summary["has_active"] |= state == "active"
            history = action_history(record)
            merge_bounded(summary[bucket], history)
            by_identity = summary[bucket + "_identity"]
            merge_bounded(
                by_identity.setdefault(record.get("action_identity"), {}), history
            )
        summaries[group] = summary
    # Keep verified source edges for messages hidden by the candidate filter.
    # They can be needed to classify a delayed cancellation after a restart.
    candidate_ids = {event["id"] for event in events}
    for source in graph_events:
        eid = source["id"]
        if eid not in records and eid not in candidate_ids:
            records[eid] = {
                "state": "superseded",
                "actions": {},
                "lineage": sorted({eid, *source.get("references", [])}),
                "cap_identity": source.get("cap_identity"),
                "cap_references": source.get("reference_identities")
                if source.get("cap_references_valid")
                else None,
                "cancel_message": False,
                "updated": now.isoformat(),
            }

    for group in quarantine_groups:
        for eid in members.get(group, []):
            if records[eid].get("state") not in ("cancelled", "superseded"):
                records[eid] = suspend_record(records[eid], "quarantined", now)
    for event in events:
        eid = event["id"]
        group = groups[eid]
        refs = event.get("references", [])
        decision = qualify(event, config, now)
        fp = fingerprint(event, decision)
        identity = action_identity(event)
        cancelled = (
            event.get("status") == "Actual" and event.get("message_type") == "Cancel"
        )
        summary = summaries.get(group, {})
        blocked = eid in cancelled_ids
        uncertain = eid in uncertain_ids and not cancelled
        identity_uncertain = not cancelled and eid in invalid_ids
        if group in quarantine_groups or uncertain or identity_uncertain:
            old_record = records.get(eid, {})
            records[eid] = {
                **suspend_record(old_record, "quarantined", now),
                "fingerprint": fp,
                "actions": action_history(old_record),
                "action_identity": old_record.get("action_identity"),
                "lineage": sorted({eid, *refs}),
                "reasons": [
                    "invalid or incomplete CAP identity or references"
                    if identity_uncertain
                    else "cancellation scope uncertain"
                    if uncertain
                    else "lineage quarantined"
                ],
                "cap_identity": event.get("cap_identity"),
                "cap_references": event.get("reference_identities")
                if event.get("cap_references_valid")
                else None,
                "cancel_message": cancelled or old_record.get("cancel_message", False),
                "affected": [],
            }
            seen.add(eid)
            quarantined = True
            continue
        actions = {}

        def include_bucket(bucket):
            if decision["qualifies"]:
                merge_bounded(actions, summary.get(bucket, {}))
            else:
                indexed = summary.get(bucket + "_identity", {})
                merge_bounded(actions, indexed.get(identity, {}))

        include_bucket("active")
        inactive_dates = []
        if not summary.get("has_active"):
            include_bucket("inactive")
            if summary.get("inactive_since"):
                inactive_dates.append(summary["inactive_since"])
        else:
            for record_id in {eid, *refs}:
                record = prior.get(record_id, {})
                if semantic_state(record) not in inactive_states:
                    continue
                since = timestamp(record.get("inactive_since") or record.get("updated"))
                if not since or since > now or now - since > timedelta(minutes=15):
                    continue
                inactive_dates.append(since)
                if decision["qualifies"] or record.get("action_identity") == identity:
                    merge_bounded(actions, action_history(record))
        if len(actions) > 100:
            quarantined = True
            old_record = records.get(eid, {})
            records[eid] = {
                **suspend_record(old_record, "quarantined", now),
                "fingerprint": fp,
                "actions": action_history(old_record),
                "action_identity": old_record.get("action_identity"),
                "lineage": sorted({eid, *refs}),
                "reasons": ["action history limit exceeded"],
                "cap_identity": event.get("cap_identity"),
                "cap_references": event.get("reference_identities")
                if event.get("cap_references_valid")
                else None,
                "cancel_message": cancelled or old_record.get("cancel_message", False),
                "affected": [],
            }
            seen.add(eid)
            continue
        equivalent = fp in actions or (group, fp) in planned_in_poll
        if (
            decision["qualifies"]
            and not blocked
            and not baseline
            and (activate or not equivalent)
            and (group, fp) not in planned_in_poll
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
            planned_in_poll.add((group, fp))
        if cancelled or blocked:
            actions = {}
        elif decision["qualifies"]:
            actions = {fp: decision["affected"]}
        inactive_since = min(inactive_dates, default=now).isoformat()
        records[eid] = {
            "state": "cancelled"
            if cancelled or blocked
            else "active"
            if decision["qualifies"]
            else "ineligible",
            "fingerprint": fp,
            "actions": actions,
            "action_identity": identity,
            "inactive_since": None
            if decision["qualifies"] and not blocked
            else inactive_since,
            "lineage": sorted({eid, *refs}),
            "cap_identity": event.get("cap_identity"),
            "cap_references": event.get("reference_identities")
            if event.get("cap_references_valid")
            else None,
            "cancel_message": cancelled,
            "reasons": ["message explicitly referenced by cancellation"]
            if blocked and not cancelled
            else decision["reasons"],
            "affected": decision["affected"] if not blocked else [],
            "updated": now.isoformat(),
        }
        seen.add(eid)
        referenced.update(ref for ref in refs if ref != eid)
    for eid in cancelled_ids:
        if eid in records and not records[eid].get("cancel_message"):
            records[eid] = {
                **records[eid],
                "state": "cancelled",
                "actions": {},
                "reasons": ["message explicitly referenced by cancellation"],
            }
    for eid in uncertain_ids - cancelled_ids:
        if eid in records and not records[eid].get("cancel_message"):
            records[eid] = suspend_record(records[eid], "quarantined", now)
            records[eid]["reasons"] = ["cancellation scope uncertain"]
            quarantined = True
    for ref in referenced:
        if (
            ref in records
            and ref not in seen
            and records[ref].get("state") not in ("cancelled", "quarantined")
        ):
            records[ref]["state"] = "superseded"
    for eid, record in records.items():
        if eid not in seen and record.get("state") == "active":
            if partial or quarantined:
                records[eid] = suspend_record(record, "unconfirmed", now)
            else:
                record.update(
                    state="ended_or_absent",
                    inactive_since=now.isoformat(),
                    updated=now.isoformat(),
                )
        elif (
            eid not in seen
            and not (partial or quarantined)
            and record.get("state") in ("unconfirmed", "quarantined")
        ):
            since = (
                record.get("inactive_since")
                if semantic_state(record) in ("ineligible", "ended_or_absent")
                else now.isoformat()
            )
            record.update(
                state="ended_or_absent", inactive_since=since, updated=now.isoformat()
            )
    cancellation_groups = {
        groups.get(eid)
        for eid, record in records.items()
        if record.get("cancel_message")
    }
    protected = (
        seen
        | {event["id"] for event in graph_events}
        | {eid for eid in records if groups.get(eid) in cancellation_groups}
    )
    if len(protected) > 1000:
        raise CancellationEvidenceOverflow(
            "current messages and cancellation evidence exceed journal limit"
        )
    records = dict(
        sorted(
            records.items(),
            key=lambda item: (item[0] in protected, item[1].get("updated", "")),
            reverse=True,
        )[:1000]
    )
    return records, plans
