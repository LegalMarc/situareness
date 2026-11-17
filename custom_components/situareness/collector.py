"""Bounded NWS API client, independent of the browser."""

import asyncio
import json
from urllib.parse import urlencode, urlparse
from .domain import OversizedFeature, cap_event_valid, normalize, safe_url

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 10


class CancellationEvidenceLost(ValueError):
    """A partial failed fetch observed cancellation evidence it cannot retain."""


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
    ):
        super().__init__(events)
        self.quarantined = quarantined
        self.quarantined_lineages = quarantined_lineages
        self.quarantine_ambiguous = quarantine_ambiguous
        self.all_events = list(events) if all_events is None else all_events
        self.uncertain_cancellation = uncertain_cancellation
        self.source_count = (
            source_count if source_count is not None else len(events) + quarantined
        )


async def fetch(session, states):
    seen_cancel = [False]
    try:
        return await _fetch(session, states, seen_cancel)
    except asyncio.CancelledError as err:
        if seen_cancel[0]:
            raise CancellationEvidenceLost(
                "cancelled fetch after cancellation evidence"
            ) from err
        raise
    except Exception as err:
        if seen_cancel[0]:
            raise CancellationEvidenceLost(
                "incomplete fetch after cancellation evidence"
            ) from err
        raise


async def _fetch(session, states, seen_cancel):
    events = {}
    quarantined = 0
    quarantined_lineages = []
    quarantine_refs = 0
    quarantine_ambiguous = False
    uncertain_cancellation = False
    feature_count = 0
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
            properties = (
                feature.get("properties") if isinstance(feature, dict) else None
            )
            if (
                isinstance(properties, dict)
                and properties.get("status") == "Actual"
                and properties.get("messageType") == "Cancel"
            ):
                seen_cancel[0] = True
            feature_count += 1
            if feature_count > 1000:
                raise ValueError("NWS event limit reached")
            try:
                event = normalize(feature)
            except OversizedFeature:
                quarantined += 1
                if (
                    feature["properties"].get("status") == "Actual"
                    and feature["properties"].get("messageType") == "Cancel"
                ):
                    uncertain_cancellation = True
                refs = feature["properties"].get("references", [])
                ids = [feature["id"]]
                for ref in refs:
                    if isinstance(ref, dict) and isinstance(ref.get("@id"), str):
                        if len(ref["@id"]) > 512:
                            quarantine_ambiguous = True
                        elif safe_url(ref["@id"]):
                            if quarantine_refs >= 5000:
                                quarantine_ambiguous = True
                                break
                            ids.append(ref["@id"])
                            quarantine_refs += 1
                quarantined_lineages.append(ids)
                continue
            if event is None:
                properties = (
                    feature.get("properties") if isinstance(feature, dict) else None
                )
                if (
                    isinstance(properties, dict)
                    and properties.get("status") == "Actual"
                    and properties.get("messageType") == "Cancel"
                ):
                    # Even malformed cancellation evidence must not disappear on
                    # a later poll and allow an uncertain retry to resume.
                    uncertain_cancellation = True
                    quarantine_ambiguous = True
                    quarantined += 1
                    continue
                raise ValueError("invalid NWS feature")
            if event["id"] in events and events[event["id"]] != event:
                raise ValueError("conflicting duplicate NWS message identity")
            events[event["id"]] = event
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
    )
