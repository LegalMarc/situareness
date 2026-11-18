"""Bounded NWS API client, independent of the browser."""

import asyncio
import json
from urllib.parse import urlencode, urlparse
from .domain import (
    OversizedFeature,
    normalize,
    safe_url,
)

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 50
MAX_FETCH_SECONDS = 50


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
    seen_quarantine_ids = set()
    quarantine_ambiguous = False
    uncertain_cancellation = False
    conflicting_cancellation = False
    feature_count = 0

    def add_quarantined_lineage(ids, is_cancel=False):
        nonlocal quarantine_ambiguous
        if not ids:
            return True
        unique_ids = [ids[0], *dict.fromkeys(r for r in ids[1:] if r != ids[0])]
        retained = []
        fits = True
        for qid in unique_ids:
            if qid in seen_quarantine_ids:
                retained.append(qid)
            elif len(seen_quarantine_ids) < MAX_QUARANTINE_IDS:
                seen_quarantine_ids.add(qid)
                retained.append(qid)
            else:
                quarantine_ambiguous = True
                fits = False
                break
        if retained:
            quarantined_lineages.append(retained)
            if is_cancel:
                quarantined_cancel_lineages.append(retained)
        return fits

    url = "https://api.weather.gov/alerts/active?" + urlencode(
        {"area": ",".join(states)}
    )
    visited = set()
    async with asyncio.timeout(MAX_FETCH_SECONDS):
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
                    if feature_id:
                        refs = raw_refs if isinstance(raw_refs, list) else []
                        valid_ref_ids = [
                            ref_id
                            for ref in refs
                            if isinstance(ref, dict)
                            and isinstance(ref_id := ref.get("@id"), str)
                            and len(ref_id) <= 512
                            and ref_id.isascii()
                            and safe_url(ref_id)
                            and ref_id.startswith("https://api.weather.gov/alerts/")
                        ]
                        refs_valid = (
                            isinstance(properties, dict)
                            and (raw_refs is None or isinstance(raw_refs, list))
                            and len(valid_ref_ids) == len(refs)
                        )
                        fits = add_quarantined_lineage(
                            [feature_id, *valid_ref_ids], is_cancel=is_cancel
                        )
                        if is_cancel and (
                            not refs_valid or not valid_ref_ids or not fits
                        ):
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
                            [
                                *existing.get("references", []),
                                *event.get("references", []),
                            ]
                        )
                    )
                    fits = add_quarantined_lineage(
                        [eid, *combined_refs], is_cancel=(eid in cancel_seen_for_id)
                    )
                    if (eid in cancel_seen_for_id) and (
                        not fits
                        or eid in unrecoverable_cancel_for_id
                        or not combined_refs
                    ):
                        conflicting_cancellation = True
                    continue
                id_counts[eid] = 1
                events[eid] = event
                if is_cancel and not event.get("references"):
                    uncertain_cancellation = True
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
    all_events = list(events.values())
    return CollectedEvents(
        all_events,
        quarantined,
        quarantined_lineages,
        quarantine_ambiguous,
        feature_count,
        all_events=all_events,
        uncertain_cancellation=uncertain_cancellation,
        conflicting_cancellation=conflicting_cancellation,
        quarantined_cancel_lineages=quarantined_cancel_lineages,
    )
