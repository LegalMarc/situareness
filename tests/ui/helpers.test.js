import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  eventTimestamp,
  matchesEvent,
  nwsAwarenessLifecycle,
  parsePublicConfig,
  publicConfig,
  relativeAge,
  safeHttpUrl,
  sourceFreshness,
} from "../../extension/ui/helpers.mjs";
import { validateConfig } from "../../extension/lib/config.js";

const defaults = JSON.parse(
  await readFile(
    new URL("../../extension/defaults/config.json", import.meta.url),
  ),
);

test("safeHttpUrl accepts public HTTP URLs and rejects unsafe schemes and credentials", () => {
  assert.equal(
    safeHttpUrl("https://example.org/story?id=2"),
    "https://example.org/story?id=2",
  );
  assert.equal(safeHttpUrl("javascript:alert(1)"), null);
  assert.equal(safeHttpUrl("file:///etc/passwd"), null);
  assert.equal(safeHttpUrl("https://user:pass@example.org"), null);
  assert.equal(safeHttpUrl(undefined), null);
});

test("publicConfig strips private location/device material and secrets, and forces actions off", () => {
  const cleaned = publicConfig({
    schema_version: 1,
    live_actions_enabled: true,
    api_token: "private",
    enrolled_iphones: [{ id: "secret-device" }],
    locations: [
      {
        id: "nyc_sample",
        household_exposure: { lat: 40.7 },
        google_speaker_targets: ["speaker"],
        horn_targets: ["horn"],
        latitude: 40.71,
        longitude: -73.95,
        awareness_area: {
          state: "NY",
          county_fips: ["36005", "36047", "36061", "36081", "36085"],
          coordinates: [40.7, -73.9],
        },
        name: "New York City, NY",
      },
    ],
  });
  assert.equal(cleaned.live_actions_enabled, false);
  assert.deepEqual(cleaned.enrolled_iphones, []);
  assert.equal("api_token" in cleaned, false);
  assert.deepEqual(cleaned.locations[0], {
    id: "nyc_sample",
    name: "New York City, NY",
    awareness_area: {
      state: "NY",
      county_fips: ["36005", "36047", "36061", "36081", "36085"],
    },
    household_exposure: null,
    google_speaker_targets: [],
    horn_targets: [],
  });
  assert.equal("latitude" in cleaned.locations[0], false);
  assert.equal("longitude" in cleaned.locations[0], false);
  assert.equal("coordinates" in cleaned.locations[0].awareness_area, false);
});

test("default browser settings round-trip through export and runtime validation", () => {
  const exported = publicConfig(defaults);
  assert.doesNotThrow(() =>
    validateConfig(parsePublicConfig(JSON.stringify(exported))),
  );
  assert.deepEqual(
    exported.locations.map((place) => place.awareness_area),
    defaults.locations.map((place) => place.awareness_area),
  );
  assert.equal(
    exported.sources.find((source) => source.id === "nws").interval_minutes,
    1,
  );
  assert.equal(
    exported.sources.find((source) => source.id === "usgs").interval_minutes,
    1,
  );
  assert.match(
    exported.sources.find((source) => source.id === "usgs").url,
    /all_hour\.geojson$/,
  );
});

test("configuration import requires supported public schema", () => {
  assert.throws(() => parsePublicConfig("{"), /valid JSON/);
  assert.throws(
    () => parsePublicConfig('{"schema_version":2}'),
    /schema version 1/,
  );
  const input = {
    schema_version: 1,
    room: {},
    alarm_policy: {},
    locations: [{ id: "x", household_exposure: "private" }],
  };
  assert.deepEqual(parsePublicConfig(JSON.stringify(input)).locations, [
    {
      id: "x",
      household_exposure: null,
      google_speaker_targets: [],
      horn_targets: [],
    },
  ]);
});

test("source health goes stale after twice its polling interval, but failures remain errors", () => {
  const now = Date.parse("2026-11-15T12:00:00Z");
  assert.equal(
    sourceFreshness(
      {
        status: "ok",
        interval_minutes: 2,
        last_success_at: "2026-11-15T11:57:00Z",
      },
      now,
    ),
    "ok",
  );
  assert.equal(
    sourceFreshness(
      {
        status: "ok",
        interval_minutes: 2,
        last_success_at: "2026-11-15T11:55:00Z",
      },
      now,
    ),
    "stale",
  );
  assert.equal(
    sourceFreshness(
      {
        status: "ok",
        interval_minutes: 10,
        last_success_at: "2026-11-15T11:41:00Z",
      },
      now,
    ),
    "ok",
  );
  assert.equal(
    sourceFreshness(
      {
        status: "ok",
        interval_minutes: 10,
        last_success_at: "2026-11-15T11:41:00Z",
      },
      now + 2 * 60_000,
    ),
    "stale",
  );
  assert.equal(
    sourceFreshness(
      { status: "error", last_success_at: "2026-11-15T11:59:00Z" },
      now,
    ),
    "error",
  );
});

test("event filtering handles optional fields and place associations without assuming exposure", () => {
  const places = [{ id: "nyc_sample", name: "New York City, NY" }];
  assert.equal(
    matchesEvent(
      {
        title: "Wind warning",
        category: "weather",
        location_ids: ["nyc_sample"],
      },
      { query: "new york", category: "weather", locationId: "nyc_sample" },
      places,
    ),
    true,
  );
  assert.equal(
    matchesEvent(
      { title: "Wind warning", category: "weather" },
      { query: "wind", locationId: "nyc_sample" },
      places,
    ),
    false,
  );
  assert.equal(matchesEvent({}, { category: "other" }, places), true);
});

test("relativeAge gives safe labels for unknown and old timestamps", () => {
  assert.equal(relativeAge(null), "No successful fetch");
  assert.equal(
    relativeAge("2026-11-15T11:00:00Z", Date.parse("2026-11-15T12:05:00Z")),
    "1h ago",
  );
});

test("event ordering uses the later publication or update time and labels collection fallback", () => {
  assert.deepEqual(
    eventTimestamp({
      published_at: "2026-11-15T11:00:00Z",
      updated_at: "2026-11-15T11:30:00Z",
    }),
    {
      timestamp: Date.parse("2026-11-15T11:30:00Z"),
      value: "2026-11-15T11:30:00.000Z",
      label: "Updated",
    },
  );
  assert.equal(
    eventTimestamp({
      published_at: "2026-11-15T11:30:00Z",
      updated_at: "2026-11-15T11:00:00Z",
    }).label,
    "Published",
  );
  assert.equal(
    eventTimestamp({ collected_at: "2026-11-15T10:00:00Z" }).label,
    "Collected",
  );
  assert.equal(eventTimestamp({}).label, "Time unknown");
});

test("NWS lifecycle remains distinct from actual/test status and expiry wins over cache presence", () => {
  const now = Date.parse("2026-11-15T12:00:00Z");
  assert.equal(
    nwsAwarenessLifecycle(
      {
        source_id: "weather_alerts",
        category: "weather",
        official: true,
        status: "actual",
        awareness_lifecycle: "current",
      },
      now,
    ),
    "current",
  );
  assert.equal(
    nwsAwarenessLifecycle(
      {
        source_id: "weather_alerts",
        category: "weather",
        official: true,
        status: "test",
        awareness_lifecycle: "not_in_latest_fetch",
      },
      now,
    ),
    "not_in_latest_fetch",
  );
  assert.equal(
    nwsAwarenessLifecycle(
      {
        source_id: "nws",
        awareness_lifecycle: "current",
        expires_at: "2026-11-15T11:59:00Z",
      },
      now,
      [{ id: "nws", kind: "nws" }],
    ),
    "expired",
  );
  assert.equal(
    nwsAwarenessLifecycle({ source_id: "nws", status: "actual" }, now, [
      { id: "nws", kind: "nws" },
    ]),
    "unknown",
  );
  assert.equal(
    nwsAwarenessLifecycle(
      { source_id: "usgs", awareness_lifecycle: "current" },
      now,
    ),
    null,
  );
  assert.equal(
    nwsAwarenessLifecycle(
      {
        source_id: "nws",
        awareness_lifecycle: "current",
        category: "news",
        official: true,
      },
      now,
    ),
    null,
  );
});

test("disabled source health is neutral even when old or failed", () => {
  assert.equal(
    sourceFreshness({
      enabled: false,
      status: "error",
      last_success_at: "2020-01-01T00:00:00Z",
    }),
    "disabled",
  );
  assert.equal(
    sourceFreshness({
      enabled: false,
      status: "ok",
      last_success_at: "2020-01-01T00:00:00Z",
    }),
    "disabled",
  );
});

test("legacy dashboard imports normalize to the optional context dashboard", () => {
  const legacy = structuredClone(defaults);
  legacy.room.primary_dashboard = legacy.room.context_dashboard;
  delete legacy.room.context_dashboard;
  const cleaned = parsePublicConfig(JSON.stringify(legacy));
  assert.equal(
    cleaned.room.context_dashboard,
    "https://www.worldmonitor.app/dashboard",
  );
  assert.equal(Object.hasOwn(cleaned.room, "primary_dashboard"), false);
  const direct = validateConfig(legacy);
  assert.equal(direct.room.context_dashboard, cleaned.room.context_dashboard);
  assert.equal(Object.hasOwn(direct.room, "primary_dashboard"), false);
  const normalized = validateConfig(cleaned);
  assert.equal(
    normalized.room.context_dashboard,
    cleaned.room.context_dashboard,
  );
  assert.equal(Object.hasOwn(normalized.room, "primary_dashboard"), false);
});

test("explicit null context dashboard overrides a legacy URL", () => {
  const config = structuredClone(defaults);
  config.room.context_dashboard = null;
  config.room.primary_dashboard = "https://example.com/legacy";
  assert.equal(publicConfig(config).room.context_dashboard, null);
  assert.equal(validateConfig(config).room.context_dashboard, null);
});

test("weather presence is marked cached when its source is unavailable or overdue", () => {
  const now = Date.now();
  const event = {
    source_id: "nws",
    awareness_lifecycle: "current",
    category: "weather",
    official: true,
  };
  const sources = [{ id: "nws", kind: "nws", interval_minutes: 1 }];
  for (const source of [
    {
      id: "nws",
      enabled: false,
      status: "ok",
      last_success_at: new Date(now).toISOString(),
    },
    {
      id: "nws",
      enabled: true,
      status: "error",
      last_success_at: new Date(now).toISOString(),
    },
    {
      id: "nws",
      enabled: true,
      status: "ok",
      last_success_at: new Date(now - 180_000).toISOString(),
    },
  ])
    assert.equal(
      nwsAwarenessLifecycle(event, now, sources, [source]),
      "cached",
    );
  assert.equal(
    nwsAwarenessLifecycle(event, now, sources, [
      {
        id: "nws",
        enabled: true,
        status: "ok",
        last_success_at: new Date(now).toISOString(),
      },
    ]),
    "current",
  );
});

test("weather lifecycle tolerates absent source configuration", () => {
  const event = {
    source_id: "nws",
    awareness_lifecycle: "current",
    category: "weather",
    official: true,
  };
  assert.equal(
    nwsAwarenessLifecycle(event, Date.now(), null, [
      { id: "nws", status: "error" },
    ]),
    "cached",
  );
});

test("a source timestamp in the future is not presented as fresh", () => {
  const now = Date.now();
  assert.equal(
    sourceFreshness(
      { status: "ok", interval_minutes: 1, last_success_at: new Date(now + 60_000).toISOString() },
      now,
    ),
    "stale",
  );
});

test("USGS and BBC items are marked cached when their source is unavailable or overdue", () => {
  const now = Date.now();
  const sources = [
    { id: "usgs", kind: "usgs", interval_minutes: 1 },
    { id: "bbc_world", kind: "rss", interval_minutes: 5 },
  ];
  const usgsEvent = { source_id: "usgs", category: "earthquake" };
  const bbcEvent = { source_id: "bbc_world", category: "news" };

  assert.equal(nwsAwarenessLifecycle(usgsEvent, now, sources), null);
  assert.equal(nwsAwarenessLifecycle(bbcEvent, now, sources), null);

  assert.equal(
    nwsAwarenessLifecycle(usgsEvent, now, sources, [
      {
        id: "usgs",
        enabled: true,
        status: "ok",
        last_success_at: new Date(now).toISOString(),
      },
    ]),
    null,
  );
  assert.equal(
    nwsAwarenessLifecycle(bbcEvent, now, sources, [
      {
        id: "bbc_world",
        enabled: true,
        status: "ok",
        last_success_at: new Date(now).toISOString(),
      },
    ]),
    null,
  );

  for (const [event, id, staleAgeMs] of [
    [usgsEvent, "usgs", 180_000],
    [bbcEvent, "bbc_world", 660_000],
  ]) {
    for (const source of [
      {
        id,
        enabled: false,
        status: "ok",
        last_success_at: new Date(now).toISOString(),
      },
      {
        id,
        enabled: true,
        status: "error",
        last_success_at: new Date(now).toISOString(),
      },
      {
        id,
        enabled: true,
        status: "ok",
        last_success_at: new Date(now - staleAgeMs).toISOString(),
      },
    ]) {
      assert.equal(
        nwsAwarenessLifecycle(event, now, sources, [source]),
        "cached",
      );
    }
    assert.equal(nwsAwarenessLifecycle(event, now, sources, []), "cached");
  }
});
