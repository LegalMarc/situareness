"""Bounded NWS API client, independent of the browser."""

import asyncio
import json
from urllib.parse import urlencode, urlparse
from .domain import OversizedFeature, cap_event_valid, normalize, safe_url

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 10


class CollectedEvents(list):
    """Successful paginated fetch with a count of quarantined features."""

    def __init__(
        self,
        events,
        quarantined,
        quarantined_lineages,
        quarantine_ambiguous,
        source_count=None,
        all_events=None,
        uncertain_cancellation=False,
        conflicting_cancellation=False,
        quarantined_cancel_lineages=(),
    ):
        super().__init__(events)
        self.quarantined = quarantined
        self.quarantined_lineages = quarantined_lineages
        self.quarantine_ambiguous = quarantine_ambiguous
        self.all_events = list(events) if all_events is None else all_events
        self.uncertain_cancellation = uncertain_cancellation
        self.conflicting_cancellation = conflicting_cancellation
        self.quarantined_cancel_lineages = list(quarantined_cancel_lineages)
        self.source_count = (
            source_count if source_count is not None else len(events) + quarantined
        )


async def fetch(session, states):
    MAX_QUARANTINE_IDS = 5000
    events = {}
    conflicting_ids = set()
    id_counts = {}
    cancel_seen_for_id = set()
    unrecoverable_cancel_for_id = set()
    quarantined = 0
    quarantined_lineages = []
    quarantined_cancel_lineages = []
    quarantine_ids_count = 0
    quarantine_ambiguous = False
    uncertain_cancellation = False
    conflicting_cancellation = False
    feature_count = 0

    def add_quarantined_lineage(ids, is_cancel=False):
        nonlocal quarantine_ids_count, quarantine_ambiguous
        if not ids:
            return True
        unique_ids = [ids[0], *dict.fromkeys(r for r in ids[1:] if r != ids[0])]
        remaining = MAX_QUARANTINE_IDS - quarantine_ids_count
        if len(unique_ids) <= remaining:
            quarantine_ids_count += len(unique_ids)
            quarantined_lineages.append(unique_ids)
            if is_cancel:
                quarantined_cancel_lineages.append(unique_ids)
            return True
        if remaining > 0:
            sliced = unique_ids[:remaining]
            quarantined_lineages.append(sliced)
            if is_cancel:
                quarantined_cancel_lineages.append(sliced)
            quarantine_ids_count = MAX_QUARANTINE_IDS
        quarantine_ambiguous = True
        return False

    url = "https://api.weather.gov/alerts/active?" + urlencode(
        {"area": ",".join(states)}
    )
    visited = set()
    for _ in range(MAX_PAGES):
        parsed = urlparse(url)
        if (
            not safe_url(url)
            or parsed.path not in ("/alerts", "/alerts/active")
            or url in visited
        ):
            raise ValueError("invalid NWS pagination")
        visited.add(url)
        async with asyncio.timeout(25):
            async with session.get(
                url,
                headers={
                    "Accept": "application/geo+json",
                    "User-Agent": "Situareness/0.1 (Home Assistant)",
                },
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    raise ValueError(f"NWS returned HTTP {response.status}")
                chunks = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    chunks.extend(chunk)
                    if len(chunks) > MAX_BYTES:
                        raise ValueError("NWS response too large")
        payload = json.loads(chunks)
        if (
            not isinstance(payload, dict)
            or payload.get("type") != "FeatureCollection"
            or not isinstance(payload.get("features"), list)
        ):
            raise ValueError("invalid NWS response")
        for feature in payload["features"]:
            feature_count += 1
            if feature_count > 1000:
                raise ValueError("NWS event limit reached")
            try:
                event = normalize(feature)
            except OversizedFeature:
                event = None
            if event is None:
                quarantined += 1
                properties = (
                    feature.get("properties") if isinstance(feature, dict) else None
                )
                is_cancel = (
                    isinstance(properties, dict)
                    and properties.get("status") == "Actual"
                    and properties.get("messageType") == "Cancel"
                )
                raw_id = feature.get("id") if isinstance(feature, dict) else None
                feature_id = (
                    raw_id
                    if isinstance(raw_id, str)
                    and len(raw_id) <= 512
                    and raw_id.isascii()
                    and safe_url(raw_id)
                    and raw_id.startswith("https://api.weather.gov/alerts/")
                    else None
                )
                raw_refs = (
                    properties.get("references")
                    if isinstance(properties, dict)
                    else None
                )
                if (
                    feature_id
                    and isinstance(properties, dict)
                    and (raw_refs is None or isinstance(raw_refs, list))
                ):
                    refs = raw_refs or []
                    refs_valid = True
                    valid_ref_ids = []
                    for ref in refs:
                        ref_id = ref.get("@id") if isinstance(ref, dict) else None
                        if (
                            not isinstance(ref_id, str)
                            or len(ref_id) > 512
                            or not safe_url(ref_id)
                            or (
                                is_cancel
                                and (
                                    not ref_id.isascii()
                                    or not ref_id.startswith(
                                        "https://api.weather.gov/alerts/"
                                    )
                                )
                            )
                        ):
                            refs_valid = False
                            quarantine_ambiguous = True
                        else:
                            valid_ref_ids.append(ref_id)
                    fits = add_quarantined_lineage(
                        [feature_id, *valid_ref_ids], is_cancel=is_cancel
                    )
                    if is_cancel and (not refs_valid or not valid_ref_ids or not fits):
                        uncertain_cancellation = True
                else:
                    quarantine_ambiguous = True
                    if is_cancel:
                        uncertain_cancellation = True
                continue
            eid = event["id"]
            is_cancel = (
                event.get("status") == "Actual"
                and event.get("message_type") == "Cancel"
            )
            if eid in conflicting_ids:
                quarantined += 1
                if is_cancel:
                    cancel_seen_for_id.add(eid)
                    if not event.get("references"):
                        unrecoverable_cancel_for_id.add(eid)
                fits = add_quarantined_lineage(
                    [eid, *event.get("references", [])],
                    is_cancel=(eid in cancel_seen_for_id),
                )
                if (eid in cancel_seen_for_id) and (
                    not fits or eid in unrecoverable_cancel_for_id
                ):
                    conflicting_cancellation = True
                continue
            if eid in events:
                if events[eid] == event:
                    id_counts[eid] += 1
                    continue
                existing = events.pop(eid)
                conflicting_ids.add(eid)
                quarantined += id_counts[eid] + 1
                existing_is_cancel = (
                    existing.get("status") == "Actual"
                    and existing.get("message_type") == "Cancel"
                )
                if existing_is_cancel or is_cancel:
                    cancel_seen_for_id.add(eid)
                    if (existing_is_cancel and not existing.get("references")) or (
                        is_cancel and not event.get("references")
                    ):
                        unrecoverable_cancel_for_id.add(eid)
                combined_refs = list(
                    dict.fromkeys(
                        [*existing.get("references", []), *event.get("references", [])]
                    )
                )
                fits = add_quarantined_lineage(
                    [eid, *combined_refs], is_cancel=(eid in cancel_seen_for_id)
                )
                if (eid in cancel_seen_for_id) and (
                    not fits or eid in unrecoverable_cancel_for_id or not combined_refs
                ):
                    conflicting_cancellation = True
                continue
            id_counts[eid] = 1
            events[eid] = event
            if is_cancel and not event.get("references"):
                uncertain_cancellation = True
            if len(events) > 1000:
                raise ValueError("NWS event limit reached")
        pagination = payload.get("pagination") or {}
        if not isinstance(pagination, dict):
            raise ValueError("invalid NWS pagination")
        url = pagination.get("next")
        if not url:
            break
        if not isinstance(url, str):
            raise ValueError("invalid NWS pagination")
    else:
        raise ValueError("NWS pagination limit reached")
    superseded = set()
    for event in events.values():
        if not cap_event_valid(event):
            continue
        references = list(zip(event["references"], event["reference_identities"]))
        if any(
            (existing := events.get(ref)) is not None
            and (
                not cap_event_valid(existing)
                or existing.get("cap_identity") != identity
            )
            for ref, identity in references
        ):
            continue
        superseded.update(ref for ref, _ in references)
    return CollectedEvents(
        [event for eid, event in events.items() if eid not in superseded],
        quarantined,
        quarantined_lineages,
        quarantine_ambiguous,
        feature_count,
        all_events=list(events.values()),
        uncertain_cancellation=uncertain_cancellation,
        conflicting_cancellation=conflicting_cancellation,
        quarantined_cancel_lineages=quarantined_cancel_lineages,
    )
