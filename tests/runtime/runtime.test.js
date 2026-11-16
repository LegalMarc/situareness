import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { safeUrl, validateConfig } from "../../extension/lib/config.js";
import { normalizeJson, normalizeRss } from "../../extension/lib/normalize.js";
import {
  collectSource,
  mergeEvents,
  markExpired,
  readBounded,
  MAX_BYTES,
} from "../../extension/lib/collector.js";

const defaults = JSON.parse(
  await readFile(
    new URL("../../extension/defaults/config.json", import.meta.url),
  ),
);
const config = () => structuredClone(defaults);
const timestamp = "2026-11-15T12:00:00.000Z";
const now = () => new Date(timestamp);

test("public config retains two generic sample places, disables actions and blocks private fields", () => {
  const valid = validateConfig(config());
  assert.deepEqual(
    valid.locations.map((l) => l.id),
    ["nyc_sample", "washington_dc_sample"],
  );
  for (const edit of [
    (c) => (c.live_actions_enabled = true),
    (c) => c.enrolled_iphones.push("secret"),
    (c) => (c.locations[0].household_exposure = { point: [1, 2] }),
    (c) => c.locations[0].horn_targets.push("horn"),
    (c) => (c.sources[0].url = "https://evil.example/feed"),
    (c) => (c.sources[0].url = "https://user:pw@api.weather.gov/feed"),
    (c) => (c.sources[0].interval_minutes = 0),
    (c) => c.sources.push(c.sources[0]),
  ]) {
    const candidate = config();
    edit(candidate);
    assert.throws(() => validateConfig(candidate));
  }
  const candidate = config();
  candidate.secret = "private";
  candidate.locations[0].private_extra = "private";
  assert.ok(!JSON.stringify(validateConfig(candidate)).includes("private"));
});

test("source URLs reject executable schemes and credentials", () => {
  for (const value of [
    "javascript:alert(1)",
    "data:text/html,hi",
    "file:///etc/passwd",
    "https://user:password@example.org/",
    "not a url",
  ])
    assert.equal(safeUrl(value), null);
  assert.equal(
    safeUrl("https://example.org/story"),
    "https://example.org/story",
  );
});

test("normalizes official and news records with stable IDs and honest unknowns", () => {
  const nws = defaults.sources[0];
  const response = {
    features: [
      {
        id: "https://api.weather.gov/alerts/x",
        geometry: null,
        properties: {
          id: "https://api.weather.gov/alerts/x",
          headline: "Storm",
          status: "Actual",
          messageType: "Cancel",
          sent: "2026-11-15T11:00:00Z",
          expires: "2026-11-16T11:00:00Z",
        },
      },
    ],
  };
  const [event] = normalizeJson(nws, response, timestamp);
  assert.equal(event.id, "nws:https://api.weather.gov/alerts/x");
  assert.equal(event.status, "cancelled");
  assert.equal(event.severity, null);
  assert.deepEqual(event.location_ids, []);
  assert.equal(event.official, true);
  assert.equal(
    normalizeJson(
      nws,
      { features: [{ id: "x", properties: {} }] },
      timestamp,
    )[0].status,
    "unknown",
  );
  const usgs = normalizeJson(
    defaults.sources[1],
    {
      features: [
        {
          id: "quake1",
          geometry: { type: "Point", coordinates: [-1, 2, 3] },
          properties: {
            title: "Quake",
            time: 0,
            url: "https://earthquake.usgs.gov/x",
          },
        },
      ],
    },
    timestamp,
  )[0];
  assert.equal(usgs.published_at, "1970-01-01T00:00:00.000Z");
  assert.equal(usgs.category, "earthquake");
  const [news] = normalizeRss(
    defaults.sources[2],
    [
      {
        id: "a",
        title: "Headline",
        url: "javascript:bad",
        summary: "<b>Text</b>",
      },
    ],
    timestamp,
  );
  assert.equal(news.url, null);
  assert.equal(news.summary, "Text");
  assert.equal(news.official, false);
});

test("unknown weather status labels cannot resolve through Object prototype properties", () => {
  const fixture = { features: [{ id: 'status-edge', properties: { id: 'status-edge', headline: 'Status edge', status: 'constructor', sent: timestamp } }] };
  const [event] = normalizeJson({ id: 'nws', name: 'Weather', kind: 'nws' }, fixture, timestamp);
  assert.equal(event.status, 'unknown');
});

test("bounded responses reject declared and streamed excessive content", async () => {
  await assert.rejects(
    readBounded(
      new Response("x", {
        headers: { "content-length": String(MAX_BYTES + 1) },
      }),
    ),
    /size limit/,
  );
  const stream = new ReadableStream({
    start(c) {
      c.enqueue(new Uint8Array(MAX_BYTES + 1));
      c.close();
    },
  });
  await assert.rejects(readBounded(new Response(stream)), /size limit/);
});

test("failure retains previous success and sanitizes errors", async () => {
  const source = defaults.sources[0];
  const previous = { status: "ok", last_success_at: timestamp, event_count: 5 };
  const failure = await collectSource(source, previous, {
    now,
    fetcher: async () => {
      throw new Error("secret token");
    },
  });
  assert.equal(failure.events, null);
  assert.equal(failure.source.status, "error");
  assert.equal(failure.source.last_success_at, timestamp);
  assert.equal(failure.source.event_count, 5);
  assert.doesNotMatch(failure.source.last_error, /secret/);
  const http = await collectSource(source, previous, {
    now,
    fetcher: async () => new Response("", { status: 503 }),
  });
  assert.equal(http.source.last_error, "Provider returned HTTP 503.");
  const success = await collectSource(source, previous, {
    now,
    fetcher: async () => new Response(JSON.stringify({ features: [] })),
  });
  assert.equal(success.source.status, "ok");
  assert.equal(success.source.event_count, 0);
});

test("deduplicates by stable ID, retains failed-provider cache and drops old entries", () => {
  const item = (id, collected_at, title) => ({ id, collected_at, title });
  const existing = [
    item("a", timestamp, "old"),
    item("b", timestamp, "retained"),
    item("c", "2026-10-01T00:00:00Z", "expired"),
  ];
  const merged = mergeEvents(
    existing,
    [{ events: [item("a", timestamp, "new")] }, { events: null }],
    now(),
  );
  assert.equal(merged.length, 2);
  assert.equal(merged.find((x) => x.id === "a").title, "new");
  assert.ok(merged.some((x) => x.id === "b"));
});

test("county awareness is validated, round trips, and matches only SAME county codes", () => {
  const value = config();
  const roundtrip = validateConfig(
    JSON.parse(JSON.stringify(validateConfig(value))),
  );
  assert.deepEqual(roundtrip.locations.map((l) => l.awareness_area), [
    { state: "NY", county_fips: ["36005", "36047", "36061", "36081", "36085"] },
    { state: "DC", county_fips: "11001" },
  ]);
  for (const area of [
    { state: "NY", county_fips: "11001" },
    { state: "NY", county_fips: ["36061", "3606"] },
    { state: "ZZ", county_fips: "11001" },
  ]) {
    const invalid = config();
    invalid.locations[0].awareness_area = area;
    assert.throws(() => validateConfig(invalid));
  }
  const raw = {
    features: [
      {
        id: "x",
        properties: {
          status: "Actual",
          geocode: { SAME: ["136005", "136047", "136061", "136081", "136085", "111001", "999999", "bad"] },
        },
      },
    ],
  };
  const [event] = normalizeJson(
    defaults.sources[0],
    raw,
    timestamp,
    roundtrip.locations,
  );
  assert.deepEqual(event.location_ids, ["nyc_sample", "washington_dc_sample"]);
  assert.equal(event.geometry, null); // A county association is not household geometry.
  roundtrip.locations[0].watch_enabled = false;
  assert.deepEqual(
    normalizeJson(defaults.sources[0], raw, timestamp, roundtrip.locations)[0]
      .location_ids,
    ["washington_dc_sample"],
  );
  raw.features[0].properties.geocode = {};
  assert.deepEqual(
    normalizeJson(defaults.sources[0], raw, timestamp, roundtrip.locations)[0]
      .location_ids,
    [],
  );
});

test("provider cap keeps newest records and reports truncation and available count", async () => {
  const features = Array.from({ length: 205 }, (_, i) => ({
    id: `id${i}`,
    properties: {
      sent: new Date(Date.UTC(2026, 0, 1, 0, i)).toISOString(),
      status: "Actual",
    },
  }));
  const response = await collectSource(defaults.sources[0], null, {
    now,
    fetcher: async () => new Response(JSON.stringify({ features })),
  });
  assert.equal(response.source.items_available, 205);
  assert.equal(response.source.truncated, true);
  assert.equal(response.source.event_count, 200);
  assert.ok(response.events.some((e) => e.id.endsWith("id204")));
  assert.ok(!response.events.some((e) => e.id.endsWith("id0")));
  const failure = await collectSource(defaults.sources[0], response.source, {
    now,
    fetcher: async () => {
      throw new Error("failed");
    },
  });
  assert.equal(failure.source.items_available, 205);
  assert.equal(failure.source.truncated, true);
});

test("timeout bounds network and parser even if a dependency ignores abort", async () => {
  const stalledNetwork = await collectSource(defaults.sources[0], null, {
    now,
    timeoutMs: 5,
    fetcher: () => new Promise(() => {}),
  });
  assert.equal(stalledNetwork.source.last_error, "Provider request timed out.");
  const stalledParser = await collectSource(defaults.sources[2], null, {
    now,
    timeoutMs: 5,
    fetcher: async () => new Response("<rss/>"),
    parseRss: () => new Promise(() => {}),
  });
  assert.equal(stalledParser.source.last_error, "Provider request timed out.");
});

test("NWS area query tracks enabled public awareness states", () => {
  const candidate = config();
  candidate.locations[0].watch_enabled = false;
  candidate.locations.push({
    ...candidate.locations[1],
    id: "test_region",
    name: "Test Region, NJ",
    watch_enabled: true,
    awareness_area: { state: "NJ", county_fips: "34001" },
  });
  const result = validateConfig(candidate);
  const area = new URL(
    result.sources.find((s) => s.kind === "nws").url,
  ).searchParams
    .get("area")
    .split(",");
  assert.deepEqual(area, ["DC", "NJ"]);
  assert.ok(!area.includes("NY"));
});

test("NWS cached lifecycle distinguishes missing results, errors, caps, and expiry", async () => {
  const source = defaults.sources[0];
  const raw = {
    features: [
      {
        id: "alert-a",
        properties: { status: "Actual", expires: "2026-11-15T13:00:00Z" },
      },
    ],
  };
  const present = await collectSource(source, null, {
    now,
    fetcher: async () => new Response(JSON.stringify(raw)),
  });
  const cached = mergeEvents([], [present], now());
  assert.equal(cached[0].awareness_lifecycle, "current");
  const failed = await collectSource(source, present.source, {
    now,
    fetcher: async () => {
      throw new Error("offline");
    },
  });
  assert.equal(
    mergeEvents(cached, [failed], now())[0].awareness_lifecycle,
    "current",
  );
  const empty = await collectSource(source, present.source, {
    now,
    fetcher: async () => new Response(JSON.stringify({ features: [] })),
  });
  const absent = mergeEvents(cached, [empty], now());
  assert.equal(absent[0].awareness_lifecycle, "not_in_latest_fetch");
  assert.equal(absent[0].status, "actual");
  const paged = await collectSource(source, present.source, {
    now,
    fetcher: async () =>
      new Response(
        JSON.stringify({
          features: [],
          pagination: { next: "https://api.weather.gov/next" },
        }),
      ),
  });
  assert.equal(paged.source.truncated, true);
  assert.equal(
    mergeEvents(cached, [paged], now())[0].awareness_lifecycle,
    "not_in_latest_fetch",
  );
  assert.equal(
    markExpired(absent, new Date("2026-11-15T13:00:00.000Z"))[0]
      .awareness_lifecycle,
    "expired",
  );
});

test("NWS source links prefer safe HTTPS feature ID over provider URN", () => {
  const source = defaults.sources[0];
  const normalize = (featureId, propertyId) =>
    normalizeJson(
      source,
      {
        features: [
          { id: featureId, properties: { id: propertyId, status: "Actual" } },
        ],
      },
      timestamp,
    )[0];
  const alert = normalize(
    "https://api.weather.gov/alerts/real-id",
    "urn:oid:2.49.0.1.840.0.fixture",
  );
  assert.equal(alert.id, "nws:urn:oid:2.49.0.1.840.0.fixture");
  assert.equal(alert.url, "https://api.weather.gov/alerts/real-id");
  assert.equal(
    normalize("javascript:alert(1)", "https://api.weather.gov/alerts/fallback")
      .url,
    "https://api.weather.gov/alerts/fallback",
  );
  assert.equal(
    normalize("https://evil.example/alert", "javascript:alert(1)").url,
    null,
  );
  assert.equal(
    normalize("http://api.weather.gov/alerts/x", "urn:oid:fixture").url,
    null,
  );
});
