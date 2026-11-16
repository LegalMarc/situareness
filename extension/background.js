import { safeUrl, validateConfig } from "./lib/config.js";
import {
  collectSource,
  markExpired,
  retainEvents,
  sourceState,
} from "./lib/collector.js";

const STORAGE_KEY = "situareness_state_v1";
const ALARM = "situareness_collect";
const ROOM = chrome.runtime.getURL("room.html");
function isRoomUrl(value) {
  try {
    const expectedRoom = new URL(ROOM);
    const candidate = new URL(value);
    return (
      candidate.protocol === expectedRoom.protocol &&
      candidate.host === expectedRoom.host &&
      candidate.pathname === expectedRoom.pathname
    );
  } catch {
    return false;
  }
}
let state;
let queue = Promise.resolve();
let offscreenCreating;
let alarmPending = false;

function exclusive(task) {
  const result = queue.then(task);
  queue = result.catch(() => {});
  return result;
}
async function persist() {
  await chrome.storage.local.set({ [STORAGE_KEY]: state });
}
async function initialize() {
  if (state) return;
  const stored = (await chrome.storage.local.get(STORAGE_KEY))[STORAGE_KEY];
  let config;
  try {
    config = validateConfig(stored?.config);
  } catch {
    const response = await fetch(chrome.runtime.getURL("defaults/config.json"));
    config = validateConfig(await response.json());
  }
  const storedSources = Array.isArray(stored?.sources) ? stored.sources : [];
  const nwsIds = new Set(
    config.sources.filter((s) => s.kind === "nws").map((s) => s.id),
  );
  const storedEvents = Array.isArray(stored?.events) ? stored.events : [];
  const legacyNwsIds = new Set(
    storedEvents
      .filter(
        (e) =>
          e &&
          nwsIds.has(e.source_id) &&
          !["current", "expired", "not_in_latest_fetch"].includes(
            e.awareness_lifecycle,
          ),
      )
      .map((e) => e.source_id),
  );
  const validEvents = storedEvents.filter(
    (e) =>
      e &&
      typeof e === "object" &&
      !Array.isArray(e) &&
      typeof e.id === "string" &&
      typeof e.source_id === "string" &&
      typeof e.collected_at === "string" &&
      (!nwsIds.has(e.source_id) || !legacyNwsIds.has(e.source_id)),
  );
  const retained = retainEvents(
    markExpired(validEvents, new Date()),
    [],
    new Date(),
  );
  state = {
    schema_version: 1,
    config,
    events: retained.events,
    sources: config.sources.map((s) =>
      sourceState(
        s,
        legacyNwsIds.has(s.id)
          ? null
          : storedSources.find((p) => p && p.id === s.id && p.url === s.url),
      ),
    ),
    collector: {
      paused: stored?.collector?.paused === true,
      running: false,
      last_run_at: stored?.collector?.last_run_at || null,
      alarm_tick: Number.isSafeInteger(stored?.collector?.alarm_tick)
        ? stored.collector.alarm_tick
        : 0,
      last_alarm_clock_at: Number.isFinite(
        stored?.collector?.last_alarm_clock_at,
      )
        ? stored.collector.last_alarm_clock_at
        : Number.isFinite(stored?.collector?.last_alarm_scheduled_at)
          ? stored.collector.last_alarm_scheduled_at
          : null,
      storage_truncated:
        stored?.collector?.storage_truncated === true || retained.dropped > 0,
    },
    ha: { status: "not_connected" },
  };
  await persist();
  // Alarms may be cleared by Chrome between sessions; re-establish when the worker starts.
  if (!(await chrome.alarms.get(ALARM)))
    await chrome.alarms.create(ALARM, { periodInMinutes: 1 });
}
async function parseRss(text) {
  if (!offscreenCreating)
    offscreenCreating = (async () => {
      const contexts = await chrome.runtime.getContexts({
        contextTypes: ["OFFSCREEN_DOCUMENT"],
        documentUrls: [chrome.runtime.getURL("offscreen.html")],
      });
      if (!contexts.length)
        await chrome.offscreen.createDocument({
          url: "offscreen.html",
          reasons: ["DOM_PARSER"],
          justification:
            "Parse read-only RSS feeds without executing feed content.",
        });
    })().finally(() => {
      offscreenCreating = null;
    });
  await offscreenCreating;
  const response = await chrome.runtime.sendMessage({
    type: "PARSE_RSS_INTERNAL",
    text,
  });
  if (
    !response?.ok ||
    !Array.isArray(response.items) ||
    !Number.isInteger(response.items_available) ||
    response.items_available < response.items.length
  )
    throw new Error("Feed parsing failed.");
  return { items: response.items, items_available: response.items_available };
}
async function refresh(force, alarmClockAt = null) {
  await initialize();
  if (state.collector.paused) return state;
  // Count periodic alarm slots independently of request and storage latency. Chrome
  // may deliver early or late; the observed delivery clock catches up after sleep.
  if (Number.isFinite(alarmClockAt)) {
    const previous = state.collector.last_alarm_clock_at;
    const slots =
      previous === null
        ? 1
        : Math.max(1, Math.round((alarmClockAt - previous) / 60000));
    state.collector.alarm_tick += slots;
    state.collector.last_alarm_clock_at = alarmClockAt;
  }
  const due = state.config.sources.filter((s) => {
    const previous = state.sources.find((p) => p.id === s.id);
    return (
      s.enabled &&
      (force ||
        previous?.last_alarm_tick == null ||
        (Number.isFinite(alarmClockAt) &&
          state.collector.alarm_tick - previous.last_alarm_tick >=
            s.interval_minutes))
    );
  });
  if (!due.length) {
    if (Number.isFinite(alarmClockAt)) await persist();
    return state;
  }
  state.collector.running = true;
  await persist();
  try {
    // Batch requests to bound concurrency even with a user-edited source list.
    const results = [];
    for (let i = 0; i < due.length; i += 4) {
      results.push(
        ...(await Promise.all(
          due.slice(i, i + 4).map((s) =>
            collectSource(
              s,
              state.sources.find((p) => p.id === s.id),
              { parseRss, locations: state.config.locations },
            ),
          ),
        )),
      );
    }
    for (const result of results) {
      if (Number.isFinite(alarmClockAt))
        result.source.last_alarm_tick = state.collector.alarm_tick;
      state.sources = state.sources.map((s) =>
        s.id === result.source.id ? result.source : s,
      );
    }
    const retained = retainEvents(
      markExpired(state.events, new Date()),
      results,
      new Date(),
    );
    state.events = markExpired(retained.events, new Date());
    state.collector.storage_truncated ||= retained.dropped > 0;
    state.collector.last_run_at = new Date().toISOString();
  } finally {
    state.collector.running = false;
    await persist();
  }
  return state;
}
async function openRoom() {
  const contexts = await chrome.runtime.getContexts({
    contextTypes: ["TAB"],
  });
  const roomContext = contexts.find(
    (context) =>
      Number.isInteger(context.tabId) && isRoomUrl(context.documentUrl),
  );
  if (roomContext) {
    await chrome.tabs.update(roomContext.tabId, { active: true });
    if (Number.isInteger(roomContext.windowId))
      await chrome.windows.update(roomContext.windowId, { focused: true });
  } else await chrome.tabs.create({ url: ROOM });
}
async function handle(message) {
  await initialize();
  const updated = markExpired(state.events, new Date());
  if (updated.some((event, index) => event !== state.events[index])) {
    state.events = updated;
    await persist();
  }
  switch (message?.type) {
    case "GET_STATE":
      return { ok: true, state };
    case "REFRESH":
      return { ok: true, state: await refresh(true) };
    case "SET_PAUSED":
      if (typeof message.paused !== "boolean")
        throw new Error("Paused must be a boolean.");
      state.collector.paused = message.paused;
      await persist();
      return { ok: true, state };
    case "UPDATE_CONFIG": {
      const config = validateConfig(message.config);
      const oldAreas = JSON.stringify(
        state.config.locations.map((l) => [
          l.id,
          l.watch_enabled,
          l.awareness_area,
        ]),
      );
      const newAreas = JSON.stringify(
        config.locations.map((l) => [l.id, l.watch_enabled, l.awareness_area]),
      );
      const keep = new Set(
        config.sources
          .filter(
            (s) =>
              !(s.kind === "nws" && oldAreas !== newAreas) &&
              state.config.sources.some(
                (old) =>
                  old.id === s.id && old.kind === s.kind && old.url === s.url,
              ),
          )
          .map((s) => s.id),
      );
      state.events = state.events.filter((e) => keep.has(e.source_id));
      state.sources = config.sources.map((s) =>
        sourceState(
          s,
          keep.has(s.id) ? state.sources.find((p) => p.id === s.id) : null,
        ),
      );
      state.config = config;
      await persist();
      return { ok: true, state };
    }
    case "OPEN_ROOM":
      await openRoom();
      return { ok: true };
    case "OPEN_SOURCE": {
      const url = safeUrl(message.url);
      if (!url) throw new Error("Invalid source URL.");
      await chrome.tabs.create({ url });
      return { ok: true };
    }
    default:
      throw new Error("Unknown request.");
  }
}
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "PARSE_RSS_INTERNAL") return;
  const isRoomPage = sender.id === chrome.runtime.id && isRoomUrl(sender.url);
  if (!isRoomPage) {
    sendResponse({ ok: false, error: "Untrusted sender." });
    return;
  }
  exclusive(() => handle(message)).then(sendResponse, (error) =>
    sendResponse({
      ok: false,
      error:
        error instanceof Error &&
        /^(Configuration|Invalid|Private|Source URL|Paused|Unknown request)/.test(
          error.message,
        )
          ? error.message
          : "Request failed.",
    }),
  );
  return true;
});
chrome.action.onClicked.addListener(() => {
  void exclusive(async () => {
    await initialize();
    await openRoom();
  }).catch(() => {});
});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM && !alarmPending) {
    alarmPending = true;
    const alarmClockAt = Math.max(alarm.scheduledTime, Date.now());
    void exclusive(() => refresh(false, alarmClockAt))
      .catch(() => {})
      .finally(() => {
        alarmPending = false;
      });
  }
});
chrome.runtime.onInstalled.addListener(() => {
  void exclusive(async () => {
    await initialize();
    await refresh(false);
  }).catch(() => {});
});
chrome.runtime.onStartup.addListener(() => {
  void exclusive(async () => {
    await initialize();
    await refresh(false);
  }).catch(() => {});
});
