#!/usr/bin/env python3
"""Validate the structure of a Situareness research catalog, not its claims."""
import argparse
import datetime
import json
import re
import sys
from urllib.parse import parse_qsl, urlsplit

LOCATION_FIELDS = {"id", "name", "country", "state"}
SOURCE_FIELDS = {"id", "name", "issuer", "issuer_jurisdiction", "hazard_coverage",
                 "authority_evidence_url", "channel_url", "endpoint_url", "format",
                 "role", "location_ids", "access_status", "runtime_support", "enabled",
                 "checked_at", "evidence_urls", "notes"}
OPTIONAL_FIELDS = {"poll_interval_seconds", "latency_seconds"}
ACCESS = {"public_api/feed", "enrollment_only", "account_or_agreement_required", "manual_only", "unverified"}
ROLES = {"originator", "authorized_distributor", "secondary"}
CREDENTIAL_PARAMS = {"access_token", "api_key", "apikey", "authorization", "client_secret", "key", "password", "secret", "token"}
ID = re.compile(r"[a-zA-Z0-9_-]+\Z")


def fail(message):
    raise ValueError(message)


def fields(value, required, optional, label):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        fail(f"{label}: missing or unknown fields")


def string(value, label, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        fail(f"{label}: expected {'a string' if empty else 'nonempty text'}")


def identifier(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        fail(f"{label}: invalid identifier")


def url(value, label):
    if value is None:
        return
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        fail(f"{label}: invalid URL")
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.port is not None and not 1 <= parsed.port <= 65535:
            fail(f"{label}: expected HTTPS URL without credentials")
        if any(key.casefold() in CREDENTIAL_PARAMS for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
            fail(f"{label}: credential-like query parameter")
    except ValueError:
        fail(f"{label}: invalid HTTPS URL")


def string_array(value, label, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value):
        fail(f"{label}: expected {'an' if allow_empty else 'a nonempty'} array")
    for item in value:
        string(item, label)
    if len(value) != len(set(value)):
        fail(f"{label}: duplicate entries")


def validate(data):
    fields(data, {"schema_version", "locations", "sources"}, set(), "catalog")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("catalog: schema_version must be integer 1")
    if not isinstance(data["locations"], list) or not isinstance(data["sources"], list):
        fail("catalog: locations and sources must be arrays")
    locations = set()
    for loc in data["locations"]:
        fields(loc, LOCATION_FIELDS, set(), "location")
        identifier(loc["id"], "location.id")
        if loc["id"] in locations:
            fail("duplicate location id")
        locations.add(loc["id"])
        for key in ("name", "country", "state"):
            string(loc[key], f"location.{key}")
    sources = set()
    for src in data["sources"]:
        fields(src, SOURCE_FIELDS, OPTIONAL_FIELDS, "source")
        identifier(src["id"], "source.id")
        if src["id"] in sources:
            fail("duplicate source id")
        sources.add(src["id"])
        for key in ("name", "issuer", "issuer_jurisdiction", "format"):
            string(src[key], f"source.{key}")
        string(src["notes"], "source.notes", empty=True)
        string_array(src["hazard_coverage"], "source.hazard_coverage")
        string_array(src["location_ids"], "source.location_ids")
        if not set(src["location_ids"]) <= locations:
            fail("source references unknown location")
        for key in ("authority_evidence_url", "channel_url", "endpoint_url"):
            url(src[key], f"source.{key}")
        string_array(src["evidence_urls"], "source.evidence_urls", allow_empty=True)
        for value in src["evidence_urls"]:
            url(value, "source.evidence_urls")
        if src["role"] not in ROLES or src["access_status"] not in ACCESS or src["runtime_support"] not in {"supported", "proposed"}:
            fail("source: invalid role, access_status or runtime_support")
        if type(src["enabled"]) is not bool:
            fail("source.enabled: expected boolean")
        if src["enabled"] and (src["runtime_support"] != "supported" or src["access_status"] != "public_api/feed" or src["endpoint_url"] is None or src["checked_at"] is None or not src["evidence_urls"]):
            fail("enabled source requires supported runtime, verified public endpoint and evidence")
        date = src["checked_at"]
        if date is not None:
            try:
                if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                    raise ValueError
                datetime.date.fromisoformat(date)
            except ValueError:
                fail("source.checked_at: expected calendar date or null")
        for key in OPTIONAL_FIELDS:
            val = src.get(key)
            if val is not None and (type(val) is not int or val < (1 if key == "poll_interval_seconds" else 0)):
                fail(f"source.{key}: invalid interval")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="catalog JSON file")
    args = parser.parse_args()
    try:
        with open(args.path, encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=unique_object)
        validate(data)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"Invalid catalog: {exc}", file=sys.stderr)
        return 1
    print("Catalog structure valid; source claims and runtime support require independent verification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
