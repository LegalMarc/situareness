"""Bounded NWS API client, independent of the browser."""

import asyncio
import json
from urllib.parse import urlencode, urlparse
from .domain import normalize, safe_url

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 10


async def fetch(session, states):
    events = {}
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
            event = normalize(feature)
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
    return [event for eid, event in events.items() if eid not in superseded]
