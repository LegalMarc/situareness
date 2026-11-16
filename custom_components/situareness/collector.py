"""Bounded NWS API client, independent of the browser."""

import asyncio
import json
from urllib.parse import urlencode, urlparse
from .domain import OversizedFeature, normalize, safe_url

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
    ):
        super().__init__(events)
        self.quarantined = quarantined
        self.quarantined_lineages = quarantined_lineages
        self.quarantine_ambiguous = quarantine_ambiguous
        self.source_count = (
            source_count if source_count is not None else len(events) + quarantined
        )


async def fetch(session, states):
    events = {}
    quarantined = 0
    quarantined_lineages = []
    quarantine_refs = 0
    quarantine_ambiguous = False
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
            feature_count += 1
            if feature_count > 1000:
                raise ValueError("NWS event limit reached")
            try:
                event = normalize(feature)
            except OversizedFeature:
                quarantined += 1
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
                raise ValueError("invalid NWS feature")
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
    superseded = {ref for event in events.values() for ref in event["references"]}
    return CollectedEvents(
        [event for eid, event in events.items() if eid not in superseded],
        quarantined,
        quarantined_lineages,
        quarantine_ambiguous,
        feature_count,
    )
