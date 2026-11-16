import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const defaults = JSON.parse(
  await readFile(
    new URL("../../extension/defaults/config.json", import.meta.url),
  ),
);
const room = "chrome-extension://test/room.html";
const persisted = {};
const listeners = {};
let created = [];
let currentTabs = [];
let tabContexts = [];
let failure = false;
let alarm = null;
const emitter = (name) => ({
  addListener(fn) {
    listeners[name] = fn;
  },
});
globalThis.chrome = {
  runtime: {
    id: "test",
    getURL: (path) => `chrome-extension://test/${path}`,
    onMessage: emitter("message"),
    onInstalled: emitter("installed"),
    onStartup: emitter("startup"),
    getContexts: async (filter) =>
      filter?.contextTypes?.includes("TAB")
        ? tabContexts
        : [{ contextType: "OFFSCREEN_DOCUMENT" }],
    sendMessage: async () => ({
      ok: true,
      items: [
        {
          id: "bbc-one",
          url: "https://www.bbc.com/news/one",
          title: "Headline",
        },
      ],
      items_available: 1,
    }),
  },
  storage: {
    local: {
      get: async (key) => ({ [key]: structuredClone(persisted[key]) }),
      set: async (value) => Object.assign(persisted, structuredClone(value)),
    },
  },
  alarms: {
    get: async () => alarm,
    create: async (name, options) => {
      alarm = { name, ...options };
    },
    onAlarm: emitter("alarm"),
  },
  offscreen: { createDocument: async () => {} },
  action: { onClicked: emitter("action") },
  tabs: {
    query: async () => currentTabs,
    create: async (tab) => {
      created.push(tab);
    },
    update: async (id, tab) => {
      created.push({ id, ...tab });
    },
  },
  windows: {
    update: async (id, props) => {
      created.push({ windowId: id, ...props });
    },
  },
};
const originalFetch = globalThis.fetch;
globalThis.fetch = async (url) => {
  if (url.startsWith("chrome-extension:"))
    return new Response(JSON.stringify(defaults));
  if (failure && url.includes("weather.gov")) throw new Error("network secret");
  return new Response(
    url.includes("bbci.co.uk")
      ? "<rss></rss>"
      : JSON.stringify({
          features: [
            {
              id: "id1",
              properties: {
                id: "https://api.weather.gov/alerts/id1",
                title: "Quake",
                headline: "Weather",
                status: "Actual",
              },
            },
          ],
        }),
  );
};
await import("../../extension/background.js?first");
const send = (message, sender = { id: "test", url: room }) =>
  new Promise((resolve) => {
    const keep = listeners.message(message, sender, resolve);
    if (!keep && message.type === "PARSE_RSS_INTERNAL") resolve(undefined);
  });

test("worker initializes, collects, isolates failures and restores state after restart", async () => {
  const initial = await send({ type: "GET_STATE" });
  assert.equal(initial.ok, true);
  assert.equal(initial.state.collector.running, false);
  assert.equal(alarm.periodInMinutes, 1);
  const first = await send({ type: "REFRESH" });
  assert.equal(first.ok, true);
  assert.equal(first.state.sources.filter((s) => s.status === "ok").length, 4);
  assert.equal(first.state.events.length, 4);
  failure = true;
  const second = await send({ type: "REFRESH" });
  assert.equal(second.state.sources[0].status, "error");
  assert.ok(second.state.sources[0].last_success_at);
  assert.equal(second.state.events.length, 4);
  assert.doesNotMatch(second.state.sources[0].last_error, /secret/);
  assert.equal(
    (await send({ type: "SET_PAUSED", paused: true })).state.collector.paused,
    true,
  );
  const before = structuredClone(persisted);
  await import("../../extension/background.js?restart");
  const restored = await send({ type: "GET_STATE" });
  assert.equal(restored.state.collector.paused, true);
  assert.equal(restored.state.collector.running, false);
  assert.deepEqual(restored.state.events, before.situareness_state_v1.events);
  assert.deepEqual(
    (await send({ type: "REFRESH" })).state.events,
    restored.state.events,
  );
});

test("worker validates trust, configuration, source URLs and reuses room tab", async () => {
  assert.equal(
    (await send({ type: "GET_STATE" }, { id: "test", url: `${room}#main` })).ok,
    true,
  );
  assert.equal(
    (await send({ type: "GET_STATE" }, { id: "other", url: room })).ok,
    false,
  );
  assert.equal(
    (await send({ type: "OPEN_SOURCE", url: "javascript:alert(1)" })).ok,
    false,
  );
  assert.equal(
    (
      await send({
        type: "OPEN_SOURCE",
        url: "https://user:password@example.com",
      })
    ).ok,
    false,
  );
  assert.equal((await send({ type: "SET_PAUSED", paused: "false" })).ok, false);
  const config = structuredClone(defaults);
  config.live_actions_enabled = true;
  assert.equal((await send({ type: "UPDATE_CONFIG", config })).ok, false);
  const changed = structuredClone(defaults);
  changed.locations[0].awareness_area = { state: "NY", county_fips: "36047" };
  const updated = await send({ type: "UPDATE_CONFIG", config: changed });
  assert.equal(updated.ok, true);
  assert.equal(
    updated.state.config.locations[0].awareness_area.county_fips,
    "36047",
  );
  assert.equal(
    updated.state.sources.find((s) => s.id === "nws").status,
    "idle",
  );
  assert.ok(!updated.state.events.some((e) => e.source_id === "nws"));
  created = [];
  tabContexts = [{ tabId: 9, windowId: 7, documentUrl: room }];
  assert.equal((await send({ type: "OPEN_ROOM" })).ok, true);
  assert.deepEqual(created, [
    { id: 9, active: true },
    { windowId: 7, focused: true },
  ]);
  created = [];
  tabContexts = [];
  await send({ type: "OPEN_ROOM" });
  assert.deepEqual(created, [{ url: room }]);
  globalThis.fetch = originalFetch;
});

test("restart ignores corrupt storage entries and derives expiry from the clock", async () => {
  persisted.situareness_state_v1 = {
    config: structuredClone(defaults),
    sources: { not: "an array" },
    events: [
      null,
      "broken",
      {
        id: "nws:expired",
        source_id: "nws",
        collected_at: new Date().toISOString(),
        expires_at: "2020-01-01T00:00:00Z",
        awareness_lifecycle: "current",
      },
      { id: 42 },
    ],
    collector: { paused: true },
  };
  await import("../../extension/background.js?corrupt");
  const restored = await send({ type: "GET_STATE" });
  assert.equal(restored.ok, true);
  assert.equal(restored.state.events.length, 1);
  assert.equal(restored.state.events[0].awareness_lifecycle, "expired");
  assert.equal(restored.state.sources[0].status, "idle");
});

test("alarm slots preserve one-minute cadence despite early ticks and delayed persistence", async () => {
  persisted.situareness_state_v1 = {
    config: structuredClone(defaults),
    sources: [],
    events: [],
    collector: { paused: false },
  };
  const requests = [];
  globalThis.fetch = async (url) => {
    if (url.startsWith("chrome-extension:"))
      return new Response(JSON.stringify(defaults));
    requests.push(url);
    return new Response(
      url.includes("bbci.co.uk")
        ? "<rss></rss>"
        : JSON.stringify({ features: [] }),
    );
  };
  const storageSet = chrome.storage.local.set;
  const originalNow = Date.now;
  chrome.storage.local.set = async (value) => {
    await new Promise((resolve) => setTimeout(resolve, 20));
    await storageSet(value);
  };
  try {
    await import("../../extension/background.js?cadence");
    await send({ type: "GET_STATE" });
    const tick = async (scheduledTime) => {
      listeners.alarm({ name: "situareness_collect", scheduledTime });
      await send({ type: "GET_STATE" });
    };
    const base = Date.now();
    await tick(base);
    await tick(base + 59_997);
    assert.equal(
      requests.filter((url) => url.includes("weather.gov")).length,
      2,
    );
    assert.equal(
      requests.filter((url) => url.includes("earthquake.usgs.gov")).length,
      2,
    );
    assert.equal(
      requests.filter((url) => url.includes("bbci.co.uk")).length,
      2,
    );
    await tick(base + 119_998);
    await tick(base + 179_999);
    await tick(base + 239_998);
    await tick(base + 299_997);
    assert.equal(
      requests.filter((url) => url.includes("weather.gov")).length,
      6,
    );
    assert.equal(
      requests.filter((url) => url.includes("bbci.co.uk")).length,
      4,
    );
    // Chrome may report the original scheduled time after a long sleep.
    Date.now = () => base + 30 * 60_000;
    await tick(base + 359_997);
    assert.equal(
      requests.filter((url) => url.includes("weather.gov")).length,
      7,
    );
    assert.equal(
      requests.filter((url) => url.includes("bbci.co.uk")).length,
      6,
    );
    // An immediate subsequent tick must not repeat the five-minute fetch.
    await tick(base + 419_997);
    assert.equal(
      requests.filter((url) => url.includes("weather.gov")).length,
      8,
    );
    assert.equal(
      requests.filter((url) => url.includes("bbci.co.uk")).length,
      6,
    );
    // Repeated callbacks while a cycle is in progress are coalesced.
    for (const offset of [479_997, 539_997, 599_997]) {
      listeners.alarm({
        name: "situareness_collect",
        scheduledTime: base + offset,
      });
    }
    await send({ type: "GET_STATE" });
    assert.equal(
      requests.filter((url) => url.includes("weather.gov")).length,
      9,
    );
    assert.equal(
      requests.filter((url) => url.includes("bbci.co.uk")).length,
      6,
    );
  } finally {
    chrome.storage.local.set = storageSet;
    Date.now = originalNow;
    globalThis.fetch = originalFetch;
  }
});

test("startup collects overdue sources, manual refresh resets cadence, and retention disclosure expires or resets", async () => {
  const now = Date.now();
  const requests = [];
  const originalNow = Date.now;
  Date.now = () => now;
  globalThis.fetch = async (url) => {
    if (url.startsWith("chrome-extension:"))
      return new Response(JSON.stringify(defaults));
    requests.push(url);
    return new Response(
      url.includes("bbci.co.uk")
        ? "<rss></rss>"
        : JSON.stringify({ features: [] }),
    );
  };
  const states = defaults.sources.map((source) => ({
    ...source,
    status: "ok",
    last_attempt_at: new Date(
      now - (source.id === "nws" ? 120_000 : 10_000),
    ).toISOString(),
    last_alarm_tick: 10,
  }));
  persisted.situareness_state_v1 = {
    config: structuredClone(defaults),
    sources: states,
    events: [],
    collector: {
      paused: false,
      alarm_tick: 10,
      last_alarm_clock_at: now - 10_000,
      last_storage_loss_at: new Date(now - 8 * 86400_000).toISOString(),
    },
  };
  try {
    await import("../../extension/background.js?overdue");
    listeners.startup();
    let state = (await send({ type: "GET_STATE" })).state;
    assert.equal(requests.length, 1);
    assert.ok(requests[0].includes("weather.gov"));
    assert.equal(state.collector.last_storage_loss_at, null);
    await send({ type: "REFRESH" });
    assert.equal(requests.length, 5);
    assert.equal(alarm.delayInMinutes, 1);
    listeners.alarm({ name: "situareness_collect", scheduledTime: now - 1 });
    await send({ type: "GET_STATE" });
    assert.equal(requests.length, 5);
    listeners.alarm({
      name: "situareness_collect",
      scheduledTime: now + 60_000,
    });
    await send({ type: "GET_STATE" });
    assert.equal(
      requests.filter((url) => url.includes("bbci.co.uk")).length,
      2,
    );
    // A full source reset removes the retained collection and its loss disclosure.
    persisted.situareness_state_v1.collector.last_storage_loss_at = new Date(
      now,
    ).toISOString();
    await import("../../extension/background.js?loss-reset");
    state = (await send({ type: "GET_STATE" })).state;
    assert.ok(state.collector.last_storage_loss_at);
    const config = structuredClone(state.config);
    config.sources = [];
    state = (await send({ type: "UPDATE_CONFIG", config })).state;
    assert.equal(state.collector.last_storage_loss_at, null);
  } finally {
    Date.now = originalNow;
    globalThis.fetch = originalFetch;
  }
});

test("disabled cached events age out even without any collection", async () => {
  const now = Date.now();
  const originalNow = Date.now;
  const config = structuredClone(defaults);
  config.sources.forEach((source) => {
    source.enabled = false;
  });
  persisted.situareness_state_v1 = {
    config,
    sources: [],
    events: [
      {
        id: "nws:old",
        source_id: "nws",
        collected_at: new Date(now - 6 * 86400_000).toISOString(),
        awareness_lifecycle: "current",
      },
    ],
    collector: { paused: false },
  };
  try {
    await import("../../extension/background.js?age-without-collection");
    assert.equal((await send({ type: "GET_STATE" })).state.events.length, 1);
    Date.now = () => now + 2 * 86400_000;
    assert.equal((await send({ type: "GET_STATE" })).state.events.length, 0);
    assert.equal(persisted.situareness_state_v1.events.length, 0);
  } finally {
    Date.now = originalNow;
  }
});
