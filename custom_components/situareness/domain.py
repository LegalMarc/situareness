"""Pure, conservative NWS alert policy. No Home Assistant dependencies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from copy import deepcopy
from hashlib import sha256
import json
import math
from urllib.parse import urlparse

MAX_ACCEPTANCE_AGE = timedelta(days=7)


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

    def __init__(self, message, records=None, dropped_horizon=None, plans=None):
        super().__init__(message)
        self.records = records
        self.dropped_horizon = dropped_horizon
        self.plans = list(plans or ())


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
        value = p.get(key)
        if value is not None:
            if not isinstance(value, str):
                return None
            if len(value) > 10000:
                raise OversizedFeature("NWS property length limit exceeded")
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


def cap_event_valid(event, now=None):
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
    if now is not None:
        sent_ts = timestamp(identity[2])
        if sent_ts is None or sent_ts > now + timedelta(minutes=5):
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
        or now - sent > MAX_ACCEPTANCE_AGE
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


def cancellation_horizon(group_ids, records):
    """Return the retention horizon across all timestamps in a lineage component."""
    timestamps = []
    for eid in group_ids:
        record = records.get(eid)
        if not isinstance(record, dict):
            continue
        record_timestamps = []
        for key in ("ends", "expires", "sent"):
            parsed = timestamp(record.get(key))
            if parsed is not None:
                record_timestamps.append(parsed)
        refs = record.get("cap_references")
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, list) and len(ref) == 3:
                    parsed = timestamp(ref[2])
                    if parsed is not None:
                        record_timestamps.append(parsed)
        if not record_timestamps:
            parsed = timestamp(record.get("updated"))
            if parsed is not None:
                record_timestamps.append(parsed)
        timestamps.extend(record_timestamps)
    return max(timestamps) + MAX_ACCEPTANCE_AGE if timestamps else None


def conflicting_prior_cancel(event, old):
    """Return True if an incoming event conflicts with persisted cancellation state."""
    if old is None:
        return False
    event_refs = (
        event.get("reference_identities") if event.get("cap_references_valid") else None
    )
    event_targets = sorted(set(event.get("references", [])))
    old_targets = old.get("uncertain_targets")
    event_lineage = sorted({event["id"], *event_targets})
    matches = (
        event.get("status") == "Actual"
        and event.get("message_type") == "Cancel"
        and event.get("cap_identity") == old.get("cap_identity")
        and event_refs == old.get("cap_references")
        and (
            (
                isinstance(old_targets, list)
                and event_targets == sorted(set(old_targets))
            )
            or (
                old_targets is None
                and (
                    event_refs is not None
                    or old.get("lineage") is None
                    or event_lineage == old.get("lineage")
                )
            )
        )
    )
    if old.get("cancel_message") or old.get("cancellation_expired"):
        return not matches
    if "cancel_message" not in old:
        return False
    return event.get("status") == "Actual" and event.get("message_type") == "Cancel"


def _cancellation_analysis(
    records, events, groups, now=None, quarantine_cancel_lineages=()
):
    """Analyze explicit cancellations, continuing post-cancel segments, and timestamps."""

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
    seeded_cancelled_identities = {}
    seeded_cancelled_ids = set()
    seeded_uncertain_ids = set()
    ambiguous_groups = set()
    for ids in quarantine_cancel_lineages:
        if ids:
            seeded_uncertain_ids.update(ids)
            cancellations.extend(ids)
    for eid, record in records.items():
        identity = record.get("cap_identity")
        refs = record.get("cap_references")
        is_cancel = record.get("cancel_message") is True
        is_cancelled_record = record.get("state") == "cancelled" and not is_cancel
        if (
            valid_identity(identity)
            and eid == "https://api.weather.gov/alerts/" + identity[1]
            and isinstance(refs, list)
            and all(map(valid_identity, refs))
            and (
                not is_cancel
                or (
                    all(ref[2] < identity[2] for ref in refs)
                    and record.get("uncertain_targets") is None
                )
            )
        ):
            nodes[eid] = (tuple(identity), [tuple(r) for r in refs], is_cancel)
            if is_cancel:
                cancellations.append(eid)
            elif is_cancelled_record:
                seeded_cancelled_identities[tuple(identity)] = groups.get(eid)
                cancellations.append(eid)
        elif is_cancel:
            targets = record.get("uncertain_targets")
            if (
                targets is None
                and isinstance(refs, list)
                and all(map(valid_identity, refs))
            ):
                targets = ["https://api.weather.gov/alerts/" + r[1] for r in refs]
            if targets:
                seeded_uncertain_ids.update([eid, *targets])
                cancellations.extend([eid, *targets])
            else:
                ambiguous_groups.add(groups.get(eid))
        elif is_cancelled_record:
            seeded_cancelled_ids.add(eid)
            cancellations.append(eid)
    for event in events:
        eid = event["id"]
        is_cancel = (
            event.get("status") == "Actual" and event.get("message_type") == "Cancel"
        )
        if eid in records and conflicting_prior_cancel(event, records[eid]):
            prior_rec = records[eid]
            if event.get("references") and (
                not prior_rec.get("cancel_message")
                or len(prior_rec.get("lineage", [])) > 1
                or prior_rec.get("cap_references")
            ):
                seeded_uncertain_ids.update(event.get("references", []))
                if not prior_rec.get("cancel_message"):
                    seeded_uncertain_ids.add(eid)
                cancellations.extend([eid, *event.get("references", [])])
            else:
                ambiguous_groups.add(groups.get(eid))
            continue
        identity = event.get("cap_identity")
        refs = event.get("reference_identities")
        valid = (
            cap_event_valid(event, now)
            and (not is_cancel or records.get(eid, {}).get("uncertain_targets") is None)
            and valid_identity(identity)
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
                if event.get("references"):
                    seeded_uncertain_ids.update([eid, *event["references"]])
                    cancellations.extend([eid, *event["references"]])
                else:
                    ambiguous_groups.add(groups.get(eid))
            continue
        node = (tuple(identity), [tuple(r) for r in refs], is_cancel)
        if eid in nodes and nodes[eid] != node:
            ambiguous_groups.add(groups.get(eid))
        else:
            nodes[eid] = node
        if is_cancel:
            cancellations.append(eid)
    identities = {}
    for eid, (identity, _, _) in nodes.items():
        identities.setdefault(identity, []).append(eid)
    by_identifier = {}
    for identity in identities:
        by_identifier.setdefault(identity[1], set()).add(identity)
    uncertain = set()
    bad_cancel_eids = set()
    for eid, (identity, refs, is_cancel) in nodes.items():
        for ref in refs:
            if ref[2] >= identity[2]:
                if is_cancel:
                    bad_cancel_eids.add(eid)
                    seeded_uncertain_ids.add("https://api.weather.gov/alerts/" + ref[1])
                else:
                    ambiguous_groups.add(groups.get(eid))
            known = by_identifier.get(ref[1])
            if known and ref not in known:
                if is_cancel:
                    bad_cancel_eids.add(eid)
                    seeded_uncertain_ids.add("https://api.weather.gov/alerts/" + ref[1])
                    uncertain.update(known)
                else:
                    ambiguous_groups.add(groups.get(eid))
    valid_cancels = {
        identity
        for eid, (identity, refs, is_cancel) in nodes.items()
        if is_cancel
        and refs
        and eid not in bad_cancel_eids
        and groups.get(eid) not in ambiguous_groups
        and (now is None or timestamp(identity[2]) <= now + timedelta(minutes=5))
    }
    cancelled = set(seeded_cancelled_identities)
    cancelled_by_group = {}
    cancelled_at_by_identity = {}
    for identity, grp in seeded_cancelled_identities.items():
        cancelled_by_group.setdefault(grp, set()).add(identity)
    children = {}
    for eid, (identity, refs, is_cancel) in nodes.items():
        if is_cancel:
            if (
                not refs
                or eid in bad_cancel_eids
                or any(ref[2] >= identity[2] for ref in refs)
                or (
                    now is not None
                    and timestamp(identity[2]) > now + timedelta(minutes=5)
                )
            ):
                if refs:
                    seeded_uncertain_ids.add(eid)
                    seeded_uncertain_ids.update(
                        "https://api.weather.gov/alerts/" + r[1] for r in refs
                    )
                    uncertain.update(refs)
                else:
                    ambiguous_groups.add(groups.get(eid))
            else:
                cancelled.update(refs)
                cancelled_by_group.setdefault(groups.get(eid), set()).update(refs)
                cancel_ts = timestamp(identity[2])
                if cancel_ts is not None:
                    for ref in refs:
                        prev_ts = cancelled_at_by_identity.get(ref)
                        if prev_ts is None or cancel_ts > prev_ts:
                            cancelled_at_by_identity[ref] = cancel_ts
            continue
        # An update that explicitly references a valid earlier Cancel is new
        # evidence. Other older references may supply history, not a path that
        # overrides the renewal boundary.
        if not any(ref in valid_cancels for ref in refs):
            for ref in refs:
                children.setdefault(ref, set()).add(identity)
    for eid, record in records.items():
        identity = record.get("cap_identity")
        if (
            record.get("state") == "cancelled"
            and record.get("cancel_message") is not True
            and valid_identity(identity)
        ):
            ident = tuple(identity)
            if ident in cancelled and ident not in cancelled_at_by_identity:
                ts = timestamp(record.get("cancelled_at"))
                if ts is not None:
                    cancelled_at_by_identity[ident] = ts
    # If a referenced predecessor is missing, it may conceal a path from a
    # cancelled message. A predecessor strictly older than every cancelled
    # identity cannot descend from one under CAP's directed time ordering.
    cancellation_groups = {groups.get(eid) for eid in cancellations} | ambiguous_groups
    for eid, (identity, refs, is_cancel) in nodes.items():
        group_targets = cancelled_by_group.get(groups.get(eid), set())
        if not is_cancel and group_targets:
            earliest = min(target[2] for target in group_targets)
            if any(ref not in identities and ref[2] >= earliest for ref in refs):
                uncertain.add(identity)
    for target_eid in seeded_uncertain_ids:
        if target_eid in nodes and not nodes[target_eid][2]:
            uncertain.add(nodes[target_eid][0])
    hard_uncertain = set(uncertain)
    for eid, (identity, _, is_cancel) in nodes.items():
        if not is_cancel and (
            groups.get(eid) in ambiguous_groups
            or eid in seeded_uncertain_ids
            or timestamp(identity[2]) is None
        ):
            hard_uncertain.add(identity)
    tainted_from_hard = set(hard_uncertain)
    hard_pending = list(hard_uncertain)
    while hard_pending:
        parent = hard_pending.pop()
        for child in children.get(parent, ()):
            if child not in tainted_from_hard:
                tainted_from_hard.add(child)
                hard_pending.append(child)
    failed_cancel_timing = set()
    for anc in cancelled:
        anc_ts = cancelled_at_by_identity.get(anc)
        anc_pending = [anc]
        anc_visited = {anc}
        while anc_pending:
            parent = anc_pending.pop()
            for child in children.get(parent, ()):
                if child not in anc_visited:
                    anc_visited.add(child)
                    anc_pending.append(child)
                    if child not in cancelled:
                        child_ts = timestamp(child[2])
                        if anc_ts is None or child_ts is None or child_ts < anc_ts:
                            failed_cancel_timing.add(child)
    pending = list(cancelled | uncertain)
    visited = set(pending)
    while pending:
        parent = pending.pop()
        for child in children.get(parent, ()):
            if child not in visited:
                visited.add(child)
                uncertain.add(child)
                pending.append(child)
    direct_ids = {
        eid for identity in cancelled for eid in identities.get(identity, ())
    } | seeded_cancelled_ids
    continuing_uncertain_ids = {
        eid
        for identity in uncertain
        if identity not in cancelled
        and identity not in tainted_from_hard
        and identity not in failed_cancel_timing
        for eid in identities.get(identity, ())
        if eid in nodes
        and not nodes[eid][2]
        and eid not in seeded_uncertain_ids
        and groups.get(eid) not in ambiguous_groups
    } - direct_ids
    uncertain_ids = (
        {eid for identity in uncertain for eid in identities.get(identity, ())}
        | seeded_uncertain_ids
    ) - direct_ids
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
    continuing_uncertain_ids &= uncertain_ids
    cancelled_at_by_eid = {
        eid: ts
        for ident, ts in cancelled_at_by_identity.items()
        for eid in identities.get(ident, ())
        if eid in direct_ids
    }
    return direct_ids, uncertain_ids, continuing_uncertain_ids, cancelled_at_by_eid


def cancellation_evidence(
    records, events, groups, now=None, quarantine_cancel_lineages=()
):
    """Find explicit cancelled messages and directed, uncertain successors.

    Persisted edges are only authoritative when recorded with complete CAP
    tuples. Old journal lineage sets do not establish directed relationships.
    """
    direct_ids, uncertain_ids, _, _ = _cancellation_analysis(
        records,
        events,
        groups,
        now=now,
        quarantine_cancel_lineages=quarantine_cancel_lineages,
    )
    return direct_ids, uncertain_ids


def _invalid_graph_ids(prior, graph_events, now=None):
    known_identities = {
        eid: record.get("cap_identity")
        for eid, record in prior.items()
        if isinstance(record.get("cap_identity"), list)
    }
    invalid_ids = set()
    for source in graph_events:
        if conflicting_prior_cancel(source, prior.get(source["id"])):
            invalid_ids.add(source["id"])
            continue
        if prior.get(source["id"], {}).get("uncertain_targets") is not None:
            invalid_ids.add(source["id"])
            continue
        if not cap_event_valid(source, now):
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
    return invalid_ids


def resolve_candidates(previous, events, graph_events=None, now=None):
    """Restore predecessors hidden by a graph update rejected against prior state."""
    if graph_events is None:
        return list(events)
    graph_list = list(graph_events)
    invalid_ids = _invalid_graph_ids(previous or {}, graph_list, now=now)
    by_graph_id = {e["id"]: e for e in graph_list}
    valid_superseded = set()
    for source in graph_list:
        if source["id"] in invalid_ids:
            continue
        references = list(
            zip(source.get("references", []), source.get("reference_identities", []))
        )
        if any(
            (existing := by_graph_id.get(ref)) is not None
            and (
                existing["id"] in invalid_ids
                or existing.get("cap_identity") != identity
            )
            for ref, identity in references
        ):
            continue
        valid_superseded.update(ref for ref, _ in references)
    result = []
    seen_ids = set()
    for e in events:
        eid = e["id"]
        if eid not in valid_superseded and eid not in seen_ids:
            result.append(e)
            seen_ids.add(eid)
    for e in graph_list:
        eid = e["id"]
        if eid not in valid_superseded and eid not in seen_ids:
            result.append(e)
            seen_ids.add(eid)
    return result


def _expire_cancellation_horizons(prior, records, members, active_feed_groups, now):
    """Expire absent cancellation components past the 7-day acceptance horizon."""
    for group, ids in members.items():
        if group in active_feed_groups:
            continue
        if not any(
            prior[eid].get("cancel_message")
            or bool(prior[eid].get("uncertain_targets"))
            or (
                prior[eid].get("state") == "cancelled"
                and not prior[eid].get("cancellation_expired")
            )
            for eid in ids
        ):
            continue
        horizon = cancellation_horizon(ids, prior)
        if horizon is None or now > horizon:
            for eid in ids:
                if prior[eid].get("cancel_message") or prior[eid].get(
                    "uncertain_targets"
                ):
                    prior[eid]["cancel_message"] = False
                    records[eid]["cancel_message"] = False
                    records[eid]["cancellation_expired"] = True
                    prior[eid].pop("uncertain_targets", None)
                    records[eid].pop("uncertain_targets", None)
                if prior[eid].get("state") == "cancelled":
                    since = records[eid].get("inactive_since") or now.isoformat()
                    prior[eid]["state"] = "ended_or_absent"
                    records[eid]["state"] = "ended_or_absent"
                    records[eid]["inactive_since"] = since
                    records[eid]["updated"] = now.isoformat()
                    prior[eid].pop("cancelled_at", None)
                    records[eid].pop("cancelled_at", None)


def _cancel_record_identity(
    eid, event, old_record, refs, invalid_cancel=False, keep_prior_identity=False
):
    """Resolve persisted lineage, CAP identity/references, and uncertain cancel targets."""
    prior_rec = old_record or {}
    if invalid_cancel:
        lineage = prior_rec.get("lineage", [eid]) if old_record else [eid]
        if prior_rec.get("cancel_message"):
            cap_id = prior_rec.get("cap_identity")
            cap_refs = prior_rec.get("cap_references")
            prior_cap_targets = [
                "https://api.weather.gov/alerts/" + r[1]
                for r in (cap_refs or [])
                if isinstance(r, list) and len(r) == 3
            ]
            uncertain_targets = sorted(
                {*(prior_rec.get("uncertain_targets") or []), *prior_cap_targets, *refs}
            )
        else:
            cap_id = event.get("cap_identity")
            cap_refs = (
                event.get("reference_identities")
                if event.get("cap_references_valid")
                else None
            )
            uncertain_targets = sorted(set(refs))
        return lineage, cap_id, cap_refs, uncertain_targets
    lineage = (
        prior_rec.get("lineage", [eid]) if keep_prior_identity else sorted({eid, *refs})
    )
    cap_id = (
        prior_rec.get("cap_identity")
        if keep_prior_identity
        else event.get("cap_identity")
    )
    cap_refs = (
        prior_rec.get("cap_references")
        if keep_prior_identity
        else event.get("reference_identities")
        if event.get("cap_references_valid")
        else None
    )
    uncertain_targets = (
        prior_rec.get("uncertain_targets") if keep_prior_identity else None
    )
    return lineage, cap_id, cap_refs, uncertain_targets


def _quarantined_record(
    eid,
    event,
    old_record,
    fp,
    refs,
    cancelled,
    reasons,
    now,
    *,
    keep_prior_identity=False,
    keep_prior_timestamps=False,
    invalid_cancel=False,
    preserve_cancel_flag=False,
):
    """Build a quarantined record preserving bounded action history and identity rules."""
    prior_rec = old_record or {}
    lineage, cap_id, cap_refs, uncertain_targets = _cancel_record_identity(
        eid,
        event,
        prior_rec,
        refs,
        invalid_cancel=invalid_cancel,
        keep_prior_identity=keep_prior_identity,
    )
    cancel_flag = (
        prior_rec.get("cancel_message", False)
        if preserve_cancel_flag
        else (cancelled or prior_rec.get("cancel_message", False))
    )
    expired_flag = (
        prior_rec.get("cancellation_expired", False)
        if preserve_cancel_flag
        else False
        if (cancelled or prior_rec.get("cancel_message"))
        else prior_rec.get("cancellation_expired", False)
    )
    record = {
        **suspend_record(prior_rec, "quarantined", now),
        "fingerprint": fp,
        "actions": action_history(prior_rec),
        "action_identity": prior_rec.get("action_identity"),
        "lineage": lineage,
        "reasons": reasons,
        "cap_identity": cap_id,
        "cap_references": cap_refs,
        "cancel_message": cancel_flag,
        "cancellation_expired": expired_flag,
        "affected": [],
    }
    for key in ("sent", "expires", "ends"):
        record[key] = (
            prior_rec.get(key)
            if keep_prior_timestamps
            else event.get(key)
            if event.get(key) is not None
            else prior_rec.get(key)
        )
    if uncertain_targets is not None:
        record["uncertain_targets"] = uncertain_targets
    return record


def _bound_records(
    records, graph_events, groups, seen, planned_in_poll, now, plans=None
):
    """Enforce the 1,000-record cap, raising overflow if protected history exceeds it."""
    cancellation_groups = {
        groups.get(eid)
        for eid, record in records.items()
        if record.get("cancel_message") or record.get("state") == "cancelled"
    }
    current_graph_ids = {event["id"] for event in graph_events}
    protected = (
        seen
        | current_graph_ids
        | {eid for eid in records if groups.get(eid) in cancellation_groups}
    )

    def sort_key(item):
        return (
            item[0] in seen,
            item[0] in current_graph_ids,
            bool(item[1].get("cancel_message")),
            item[1].get("state") == "cancelled",
            item[0] in protected,
            item[1].get("updated", ""),
        )

    if len(protected) > 1000:
        sorted_items = sorted(records.items(), key=sort_key, reverse=True)
        bounded = dict(sorted_items[:1000])
        dropped_items = sorted_items[1000:]
        all_members_by_group = {}
        for eid in records:
            all_members_by_group.setdefault(groups.get(eid), []).append(eid)
        dropped_groups = {groups.get(eid) for eid, _ in dropped_items}
        dropped_component_horizons = [
            h
            for g in dropped_groups
            if (h := cancellation_horizon(all_members_by_group.get(g, []), records))
            is not None
        ]
        dropped_horizon = max([now + MAX_ACCEPTANCE_AGE, *dropped_component_horizons])
        for eid, rec in bounded.items():
            if rec.get("updated") == now.isoformat():
                rec_actions = rec.get("actions")
                if isinstance(rec_actions, dict):
                    for fp in list(rec_actions):
                        if (groups.get(eid), fp) in planned_in_poll:
                            rec_actions.pop(fp, None)
        raise CancellationEvidenceOverflow(
            "current messages and cancellation evidence exceed journal limit",
            records=bounded,
            dropped_horizon=dropped_horizon,
            plans=plans,
        )
    return dict(sorted(records.items(), key=sort_key, reverse=True)[:1000])


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
    quarantine_cancel_lineages=(),
):
    """Reconcile bounded history; quarantined inputs cannot end unrelated records."""
    graph_events = list(events if graph_events is None else graph_events)
    records = deepcopy(previous or {})
    prior = {eid: dict(record) for eid, record in records.items()}
    events = resolve_candidates(prior, events, graph_events, now=now)
    # Cancels are source evidence even when a later message references them.
    present = {event["id"] for event in events}
    events = list(events) + [
        event
        for event in graph_events
        if event["id"] not in present
        and event.get("status") == "Actual"
        and event.get("message_type") == "Cancel"
    ]
    plans = []
    invalid_ids = _invalid_graph_ids(prior, graph_events, now=now)

    def actual_cancel(source):
        return (
            source.get("status") == "Actual" and source.get("message_type") == "Cancel"
        )

    # Invalid/conflicting messages cannot establish lineage edges across siblings.
    grouping_events = [
        {**source, "references": []} if source["id"] in invalid_ids else source
        for source in graph_events
    ]
    groups, members = lineage_index(prior, grouping_events)
    for event in events:
        groups.setdefault(event["id"], event["id"])
    for ids in (*quarantine_lineages, *quarantine_cancel_lineages):
        for qid in ids:
            groups.setdefault(qid, qid)
    active_feed_groups = {
        groups[source["id"]] for source in graph_events if source["id"] in groups
    } | {
        groups[qid]
        for ids in quarantine_cancel_lineages
        for qid in ids
        if qid in groups
    }
    _expire_cancellation_horizons(prior, records, members, active_feed_groups, now)
    trusted_events = [
        source
        for source in graph_events
        if source["id"] not in invalid_ids or actual_cancel(source)
    ]
    (
        cancelled_ids,
        uncertain_ids,
        continuing_uncertain_ids,
        cancelled_at_by_eid,
    ) = _cancellation_analysis(
        prior,
        trusted_events,
        groups,
        now,
        quarantine_cancel_lineages=quarantine_cancel_lineages,
    )
    present_ids = {e["id"] for e in events}
    valid_referenced_in_poll = {
        ref
        for e in events
        if e["id"] not in invalid_ids
        and e["id"] not in (uncertain_ids - continuing_uncertain_ids)
        and e["id"] not in cancelled_ids
        for ref in e.get("references", [])
    }
    if quarantine_all:
        quarantined_record_ids = set(records)
        quarantined_event_ids = set(present_ids)
    else:
        quarantined_event_ids = {ids[0] for ids in quarantine_lineages if ids} | {
            ids[0] for ids in quarantine_cancel_lineages if ids
        }
        quarantined_record_ids = set()
        for ids in quarantine_lineages:
            if not ids:
                continue
            if ids[0] in records:
                quarantined_record_ids.add(ids[0])
            for ref_id in ids[1:]:
                if (
                    ref_id in records
                    and ref_id not in present_ids
                    and ref_id not in valid_referenced_in_poll
                ):
                    quarantined_record_ids.add(ref_id)
        for ids in quarantine_cancel_lineages:
            for cid in ids:
                if cid in records and cid not in present_ids:
                    quarantined_record_ids.add(cid)
    planned_in_poll = set()
    seen = set()
    referenced = set()
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
            "pre_cancel_actions": {},
            "inactive_since": None,
        }
        for record_id in ids:
            record = prior[record_id]
            state = semantic_state(record)
            is_withheld_uncertain = record.get(
                "state"
            ) == "quarantined" and "cancellation scope uncertain" in record.get(
                "reasons", []
            )
            if (
                record_id in cancelled_ids
                or state == "cancelled"
                or (
                    record_id in uncertain_ids
                    and record_id not in continuing_uncertain_ids
                )
                or is_withheld_uncertain
            ):
                if (
                    state in inactive_states
                    and not is_withheld_uncertain
                    and record_id not in uncertain_ids
                ):
                    since = timestamp(
                        record.get("inactive_since") or record.get("updated")
                    )
                    if not since or since > now or now - since > timedelta(minutes=15):
                        continue
                if state != "superseded":
                    merge_bounded(summary["pre_cancel_actions"], action_history(record))
                continue
            if state == "superseded":
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
        if eid not in records and eid not in candidate_ids and eid not in invalid_ids:
            records[eid] = {
                "state": "superseded",
                "actions": {},
                "lineage": sorted({eid, *source.get("references", [])}),
                "cap_identity": source.get("cap_identity"),
                "cap_references": source.get("reference_identities")
                if source.get("cap_references_valid")
                else None,
                "cancel_message": False,
                "sent": source.get("sent"),
                "expires": source.get("expires"),
                "ends": source.get("ends"),
                "updated": now.isoformat(),
            }

    for eid in quarantined_record_ids:
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
        invalid_cancel = cancelled and eid in invalid_ids
        old_prior = prior.get(eid)
        if conflicting_prior_cancel(event, old_prior):
            if old_prior.get("cancel_message"):
                conflict_record = {
                    **old_prior,
                    "state": "cancelled",
                    "actions": {},
                    "affected": [],
                    "cancel_message": True,
                    "cancellation_expired": False,
                    "lineage": old_prior.get("lineage", [eid]),
                    "reasons": ["conflicting cancellation evidence"],
                    "updated": now.isoformat(),
                }
                if old_prior.get("uncertain_targets") is not None or (
                    cancelled and refs
                ):
                    old_cap_targets = [
                        "https://api.weather.gov/alerts/" + r[1]
                        for r in (old_prior.get("cap_references") or [])
                        if isinstance(r, list) and len(r) == 3
                    ]
                    conflict_record["uncertain_targets"] = sorted(
                        {
                            *(old_prior.get("uncertain_targets") or []),
                            *old_cap_targets,
                            *refs,
                        }
                    )
                records[eid] = conflict_record
            else:
                records[eid] = _quarantined_record(
                    eid,
                    event,
                    old_prior,
                    fp,
                    refs,
                    cancelled,
                    ["conflicting cancellation evidence"],
                    now,
                    keep_prior_identity=True,
                    keep_prior_timestamps=True,
                    preserve_cancel_flag=True,
                )
            seen.add(eid)
            continue
        continuing_uncertain = (
            uncertain
            and eid in continuing_uncertain_ids
            and eid not in quarantined_event_ids
            and not identity_uncertain
        )
        continuing_withheld = (
            continuing_uncertain
            and fp in summary.get("pre_cancel_actions", {})
            and fp not in summary.get("active", {})
            and (group, fp) not in planned_in_poll
            and not activate
        )
        if (
            eid in quarantined_event_ids
            or identity_uncertain
            or (uncertain and not continuing_uncertain)
            or continuing_withheld
        ):
            reason = (
                "invalid or incomplete CAP identity or references"
                if identity_uncertain
                else "cancellation scope uncertain"
                if uncertain
                else "lineage quarantined"
            )
            quarantined_rec = _quarantined_record(
                eid,
                event,
                records.get(eid, {}),
                fp,
                refs,
                cancelled,
                [reason],
                now,
                keep_prior_identity=identity_uncertain,
                keep_prior_timestamps=identity_uncertain,
                invalid_cancel=invalid_cancel,
            )
            if continuing_withheld and fp in summary.get("pre_cancel_actions", {}):
                merged_actions = dict(quarantined_rec.get("actions", {}))
                if len(merged_actions) < 100 and fp not in merged_actions:
                    merged_actions[fp] = summary["pre_cancel_actions"][fp]
                quarantined_rec["actions"] = merged_actions
            records[eid] = quarantined_rec
            seen.add(eid)
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
            records[eid] = _quarantined_record(
                eid,
                event,
                records.get(eid, {}),
                fp,
                refs,
                cancelled,
                ["action history limit exceeded"],
                now,
                invalid_cancel=invalid_cancel,
            )
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
        lineage, cap_id, cap_refs, uncertain_targets = _cancel_record_identity(
            eid, event, old_prior, refs, invalid_cancel=invalid_cancel
        )
        record = {
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
            "lineage": lineage,
            "cap_identity": cap_id,
            "cap_references": cap_refs,
            "cancel_message": cancelled,
            "cancellation_expired": False,
            "sent": event.get("sent"),
            "expires": event.get("expires"),
            "ends": event.get("ends"),
            "reasons": ["message explicitly referenced by cancellation"]
            if blocked and not cancelled
            else decision["reasons"],
            "affected": decision["affected"] if not blocked else [],
            "updated": now.isoformat(),
        }
        if uncertain_targets is not None:
            record["uncertain_targets"] = uncertain_targets
        if blocked and not cancelled:
            cancel_ts = cancelled_at_by_eid.get(eid)
            cancelled_at = (
                cancel_ts.isoformat()
                if cancel_ts is not None
                else (old_prior.get("cancelled_at") if old_prior else None)
            )
            if cancelled_at is not None:
                record["cancelled_at"] = cancelled_at
        records[eid] = record
        seen.add(eid)
        if not (cancelled or blocked):
            referenced.update(ref for ref in refs if ref != eid)
    for eid in cancelled_ids:
        if eid in records and not records[eid].get("cancel_message"):
            cancel_ts = cancelled_at_by_eid.get(eid)
            cancelled_at = (
                cancel_ts.isoformat()
                if cancel_ts is not None
                else records[eid].get("cancelled_at")
            )
            updated_rec = {
                **records[eid],
                "state": "cancelled",
                "actions": {},
                "reasons": ["message explicitly referenced by cancellation"],
            }
            if cancelled_at is not None:
                updated_rec["cancelled_at"] = cancelled_at
            records[eid] = updated_rec
    current_cancel_groups = {
        groups.get(source["id"]) for source in trusted_events if actual_cancel(source)
    } | {groups.get(cid) for ids in quarantine_cancel_lineages for cid in ids}
    current_cancel_targets = {
        ref
        for source in trusted_events
        if actual_cancel(source)
        for ref in source.get("references", [])
    } | {cid for ids in quarantine_cancel_lineages for cid in ids}
    uncertain_handled = set()
    for eid in uncertain_ids - cancelled_ids:
        if (
            eid in seen
            or eid not in records
            or records[eid].get("cancel_message")
            or (
                eid in continuing_uncertain_ids
                and records[eid].get("state") != "quarantined"
            )
        ):
            continue
        group_has_current_cancel = (
            groups.get(eid) in current_cancel_groups or eid in current_cancel_targets
        )
        record_unconfirmed = (
            quarantine_all
            or (partial and not quarantine_lineages and not quarantine_cancel_lineages)
            or eid in quarantined_record_ids
        )
        if records[eid].get("state") == "active" or group_has_current_cancel:
            inactive_since = records[eid].get("inactive_since") or now.isoformat()
            records[eid] = suspend_record(records[eid], "quarantined", now)
            records[eid]["inactive_since"] = inactive_since
            records[eid]["reasons"] = ["cancellation scope uncertain"]
            uncertain_handled.add(eid)
        elif not record_unconfirmed and records[eid].get("state") in (
            "quarantined",
            "unconfirmed",
        ):
            inactive_since = records[eid].get("inactive_since") or now.isoformat()
            records[eid].update(
                state="ended_or_absent",
                inactive_since=inactive_since,
                reasons=["cancellation scope uncertain"],
                updated=now.isoformat(),
            )
            uncertain_handled.add(eid)
    for ref in referenced:
        if (
            ref in records
            and ref not in seen
            and records[ref].get("state") not in ("cancelled", "quarantined")
        ):
            records[ref]["state"] = "superseded"
    for eid, record in records.items():
        if eid in seen or eid in uncertain_handled:
            continue
        record_unconfirmed = (
            quarantine_all
            or (partial and not quarantine_lineages and not quarantine_cancel_lineages)
            or eid in quarantined_record_ids
        )
        if record.get("state") == "active":
            if record_unconfirmed:
                records[eid] = suspend_record(record, "unconfirmed", now)
            else:
                record.update(
                    state="ended_or_absent",
                    inactive_since=now.isoformat(),
                    updated=now.isoformat(),
                )
        elif not record_unconfirmed and record.get("state") in (
            "unconfirmed",
            "quarantined",
        ):
            since = (
                record.get("inactive_since")
                if semantic_state(record) in ("ineligible", "ended_or_absent")
                else now.isoformat()
            )
            record.update(
                state="ended_or_absent", inactive_since=since, updated=now.isoformat()
            )
    records = _bound_records(
        records, graph_events, groups, seen, planned_in_poll, now, plans=plans
    )
    return records, plans
