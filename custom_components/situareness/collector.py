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
MAX_TOTAL_FEATURES = 25000


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


def _cancel_refs_recoverable(ev):
    return bool(ev.get("references")) and ev.get("references_complete", True)


def _parse_and_collect_page(raw_bytes, state):
    MAX_QUARANTINE_IDS = 5000
    events = state["events"]
    conflicting_ids = state["conflicting_ids"]
    malformed_by_id = state.setdefault("malformed_by_id", {})
    id_counts = state["id_counts"]
    cancel_seen_for_id = state["cancel_seen_for_id"]
    unrecoverable_cancel_for_id = state["unrecoverable_cancel_for_id"]
    quarantined_lineages = state["quarantined_lineages"]
    quarantined_cancel_lineages = state["quarantined_cancel_lineages"]
    seen_quarantine_ids = state["seen_quarantine_ids"]
    refs_by_id = state.setdefault("refs_by_id", {})
    overflowed_ids = state.setdefault("overflowed_ids", set())
    promoted_cancel_ids = state.setdefault("promoted_cancel_ids", set())

    def add_quarantined_lineage(ids, is_cancel=False):
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
                state["quarantine_ambiguous"] = True
                fits = False
                break
        if retained:
            quarantined_lineages.append(retained)
            if is_cancel:
                quarantined_cancel_lineages.append(retained)
        return fits

    def record_quarantined_id_refs(fid, ref_ids, *, is_cancel=False):
        acc = refs_by_id.setdefault(fid, {})
        ref_overflow = False
        for ref_id in ref_ids:
            if ref_id == fid or ref_id in acc:
                continue
            if len(acc) < MAX_QUARANTINE_IDS:
                acc[ref_id] = None
            else:
                ref_overflow = True
                overflowed_ids.add(fid)
                state["quarantine_ambiguous"] = True
                break
        if is_cancel and fid not in promoted_cancel_ids:
            promoted_cancel_ids.add(fid)
            lineage_ids = [fid, *acc]
        else:
            lineage_ids = [fid, *ref_ids]
        fits = add_quarantined_lineage(lineage_ids, is_cancel=is_cancel)
        if not fits or ref_overflow:
            overflowed_ids.add(fid)
        return fits and not ref_overflow and fid not in overflowed_ids

    payload = json.loads(raw_bytes)
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "FeatureCollection"
        or not isinstance(payload.get("features"), list)
    ):
        raise ValueError("invalid NWS response")
    for feature in payload["features"]:
        state["feature_count"] += 1
        if state["feature_count"] > MAX_TOTAL_FEATURES:
            raise ValueError("too many NWS alert features")
        try:
            event = normalize(feature)
        except OversizedFeature:
            event = None
        if event is None:
            state["quarantined"] += 1
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
                properties.get("references") if isinstance(properties, dict) else None
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
                if feature_id in events:
                    existing = events.pop(feature_id)
                    conflicting_ids.add(feature_id)
                    state["quarantined"] += id_counts[feature_id]
                    existing_is_cancel = (
                        existing.get("status") == "Actual"
                        and existing.get("message_type") == "Cancel"
                    )
                    if existing_is_cancel or is_cancel:
                        cancel_seen_for_id.add(feature_id)
                    if (
                        (existing_is_cancel and not _cancel_refs_recoverable(existing))
                        or not refs_valid
                        or (is_cancel and not valid_ref_ids)
                    ):
                        unrecoverable_cancel_for_id.add(feature_id)
                    combined_refs = list(
                        dict.fromkeys([*existing.get("references", []), *valid_ref_ids])
                    )
                    fits = record_quarantined_id_refs(
                        feature_id,
                        combined_refs,
                        is_cancel=(feature_id in cancel_seen_for_id),
                    )
                    if (feature_id in cancel_seen_for_id) and (
                        not fits
                        or feature_id in unrecoverable_cancel_for_id
                        or feature_id in overflowed_ids
                        or not combined_refs
                    ):
                        state["conflicting_cancellation"] = True
                    if is_cancel and (
                        not refs_valid
                        or not valid_ref_ids
                        or not fits
                        or feature_id in overflowed_ids
                    ):
                        state["uncertain_cancellation"] = True
                elif feature_id in conflicting_ids:
                    if is_cancel:
                        cancel_seen_for_id.add(feature_id)
                    if not refs_valid or (is_cancel and not valid_ref_ids):
                        unrecoverable_cancel_for_id.add(feature_id)
                    fits = record_quarantined_id_refs(
                        feature_id,
                        valid_ref_ids,
                        is_cancel=(feature_id in cancel_seen_for_id),
                    )
                    if (feature_id in cancel_seen_for_id) and (
                        not fits
                        or feature_id in unrecoverable_cancel_for_id
                        or feature_id in overflowed_ids
                    ):
                        state["conflicting_cancellation"] = True
                    if is_cancel and (
                        not refs_valid
                        or not valid_ref_ids
                        or not fits
                        or feature_id in overflowed_ids
                    ):
                        state["uncertain_cancellation"] = True
                else:
                    prior_malformed = malformed_by_id.get(feature_id)
                    if prior_malformed is not None:
                        prev_feat, prev_cancel, prev_refs_valid, prev_refs = (
                            prior_malformed
                        )
                        if prev_feat != feature:
                            conflicting_ids.add(feature_id)
                            if prev_cancel or is_cancel:
                                cancel_seen_for_id.add(feature_id)
                            if (
                                not prev_refs_valid
                                or not refs_valid
                                or (prev_cancel and not prev_refs)
                                or (is_cancel and not valid_ref_ids)
                            ):
                                unrecoverable_cancel_for_id.add(feature_id)
                            combined_refs = list(
                                dict.fromkeys([*prev_refs, *valid_ref_ids])
                            )
                            fits = record_quarantined_id_refs(
                                feature_id,
                                combined_refs,
                                is_cancel=(feature_id in cancel_seen_for_id),
                            )
                            if (feature_id in cancel_seen_for_id) and (
                                not fits
                                or feature_id in unrecoverable_cancel_for_id
                                or feature_id in overflowed_ids
                                or not combined_refs
                            ):
                                state["conflicting_cancellation"] = True
                        else:
                            fits = record_quarantined_id_refs(
                                feature_id, valid_ref_ids, is_cancel=is_cancel
                            )
                    else:
                        malformed_by_id[feature_id] = (
                            feature,
                            is_cancel,
                            refs_valid,
                            valid_ref_ids,
                        )
                        fits = record_quarantined_id_refs(
                            feature_id, valid_ref_ids, is_cancel=is_cancel
                        )
                    if is_cancel and (
                        not refs_valid
                        or not valid_ref_ids
                        or not fits
                        or feature_id in overflowed_ids
                    ):
                        state["uncertain_cancellation"] = True
            else:
                state["quarantine_ambiguous"] = True
                if is_cancel:
                    state["uncertain_cancellation"] = True
            continue
        eid = event["id"]
        is_cancel = (
            event.get("status") == "Actual" and event.get("message_type") == "Cancel"
        )
        if eid in conflicting_ids or eid in malformed_by_id:
            extra_refs = ()
            if eid in malformed_by_id and eid not in conflicting_ids:
                _, prev_cancel, prev_refs_valid, extra_refs = malformed_by_id[eid]
                conflicting_ids.add(eid)
                if prev_cancel:
                    cancel_seen_for_id.add(eid)
                if not prev_refs_valid or (prev_cancel and not extra_refs):
                    unrecoverable_cancel_for_id.add(eid)
            state["quarantined"] += 1
            if is_cancel:
                cancel_seen_for_id.add(eid)
                if not _cancel_refs_recoverable(event):
                    unrecoverable_cancel_for_id.add(eid)
            combined_refs = list(
                dict.fromkeys([*event.get("references", []), *extra_refs])
            )
            fits = record_quarantined_id_refs(
                eid,
                combined_refs,
                is_cancel=(eid in cancel_seen_for_id),
            )
            if (eid in cancel_seen_for_id) and (
                not fits or eid in unrecoverable_cancel_for_id or eid in overflowed_ids
            ):
                state["conflicting_cancellation"] = True
            continue
        if eid in events:
            if events[eid] == event:
                id_counts[eid] += 1
                continue
            existing = events.pop(eid)
            conflicting_ids.add(eid)
            state["quarantined"] += id_counts[eid] + 1
            existing_is_cancel = (
                existing.get("status") == "Actual"
                and existing.get("message_type") == "Cancel"
            )
            if existing_is_cancel or is_cancel:
                cancel_seen_for_id.add(eid)
                if (existing_is_cancel and not _cancel_refs_recoverable(existing)) or (
                    is_cancel and not _cancel_refs_recoverable(event)
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
            fits = record_quarantined_id_refs(
                eid, combined_refs, is_cancel=(eid in cancel_seen_for_id)
            )
            if (eid in cancel_seen_for_id) and (
                not fits or eid in unrecoverable_cancel_for_id or eid in overflowed_ids
            ):
                state["conflicting_cancellation"] = True
            continue
        id_counts[eid] = 1
        events[eid] = event
        if is_cancel and not _cancel_refs_recoverable(event):
            state["uncertain_cancellation"] = True
    pagination = payload.get("pagination") or {}
    if not isinstance(pagination, dict):
        raise ValueError("invalid NWS pagination")
    next_url = pagination.get("next")
    if next_url is not None and not isinstance(next_url, str):
        raise ValueError("invalid NWS pagination")
    return next_url


async def fetch(session, states):
    state = {
        "events": {},
        "conflicting_ids": set(),
        "malformed_by_id": {},
        "id_counts": {},
        "cancel_seen_for_id": set(),
        "unrecoverable_cancel_for_id": set(),
        "quarantined": 0,
        "quarantined_lineages": [],
        "quarantined_cancel_lineages": [],
        "seen_quarantine_ids": set(),
        "refs_by_id": {},
        "overflowed_ids": set(),
        "promoted_cancel_ids": set(),
        "quarantine_ambiguous": False,
        "uncertain_cancellation": False,
        "conflicting_cancellation": False,
        "feature_count": 0,
    }
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
            url = await asyncio.to_thread(_parse_and_collect_page, bytes(chunks), state)
            if not url:
                break
        else:
            raise ValueError("NWS pagination limit reached")
    all_events = list(state["events"].values())
    return CollectedEvents(
        all_events,
        state["quarantined"],
        state["quarantined_lineages"],
        state["quarantine_ambiguous"],
        state["feature_count"],
        all_events=all_events,
        uncertain_cancellation=state["uncertain_cancellation"],
        conflicting_cancellation=state["conflicting_cancellation"],
        quarantined_cancel_lineages=state["quarantined_cancel_lineages"],
    )
