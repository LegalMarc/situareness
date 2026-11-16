import { test, expect, chromium } from "@playwright/test";
import { mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import path from "node:path";

const extension = path.resolve("extension");
const profileRoot = path.resolve("work/browser-profiles");
const maliciousTitle = "<img src=x onerror=alert(1)> World report";
const rss = `<?xml version="1.0"?><rss version="2.0"><channel><title>BBC fixture</title>
  <item><guid>bbc-fixture-1</guid><title>&lt;img src=x onerror=alert(1)&gt; World report</title><link>https://www.bbc.com/news/fixture</link><description>&lt;svg onload=alert(2)&gt;Observed details</description><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate></item>
</channel></rss>`;
const nws = {
  features: [
    {
      id: "https://api.weather.gov/alerts/fixture",
      geometry: null,
      properties: {
        id: "https://api.weather.gov/alerts/fixture",
        headline: "Wind advisory for New York City",
        status: "Actual",
        sent: new Date().toISOString(),
        geocode: { SAME: ["136061"] },
      },
    },
  ],
};
const usgs = {
  features: [
    {
      id: "quake-fixture",
      geometry: { type: "Point", coordinates: [-73, 42, 5] },
      properties: {
        title: "Magnitude 4.1 earthquake",
        url: "https://earthquake.usgs.gov/earthquakes/eventpage/fixture",
        time: Date.now(),
      },
    },
  ],
};

let context;
let page;
let profile;
let control;

async function launch() {
  return chromium.launchPersistentContext(profile, {
    channel: "chromium",
    headless: true,
    args: [
      `--disable-extensions-except=${extension}`,
      `--load-extension=${extension}`,
      "--no-proxy-server",
      "--host-resolver-rules=MAP api.weather.gov ~NOTFOUND, MAP earthquake.usgs.gov ~NOTFOUND, MAP feeds.bbci.co.uk ~NOTFOUND",
    ],
  });
}

async function workerFor(targetContext = context) {
  return (
    targetContext.serviceWorkers()[0] ||
    targetContext.waitForEvent("serviceworker", { timeout: 15_000 })
  );
}

async function extensionId(targetContext = context) {
  const worker = await workerFor(targetContext);
  return new URL(worker.url()).host;
}

async function routeFixtures(targetContext = context) {
  await targetContext.route(
    /^https:\/\/(api\.weather\.gov|earthquake\.usgs\.gov|feeds\.bbci\.co\.uk)\//,
    async (route) => {
      const url = route.request().url();
      control.requests.push(url);
      if (control.failNws && url.includes("api.weather.gov"))
        return route.fulfill({ status: 503, body: "fixture unavailable" });
      if (url.includes("api.weather.gov"))
        return route.fulfill({
          status: 200,
          contentType: "application/geo+json",
          body: JSON.stringify(nws),
        });
      if (url.includes("earthquake.usgs.gov"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(usgs),
        });
      const body = url.includes("us_and_canada")
        ? '<?xml version="1.0"?><rss version="2.0"><channel><title>Empty fixture</title></channel></rss>'
        : rss;
      return route.fulfill({
        status: 200,
        contentType: "application/rss+xml",
        body,
      });
    },
  );
}

async function send(message) {
  return page.evaluate(
    (request) => chrome.runtime.sendMessage(request),
    message,
  );
}

async function ensureConfigEditorVisible(dialog) {
  const editor = dialog.locator("#config-json");
  if (!(await editor.isVisible()))
    await dialog.getByText("Import or export browser settings").click();
  await expect(editor).toBeVisible();
}

async function openRoom(targetContext = context) {
  const id = await extensionId(targetContext);
  page = await targetContext.newPage();
  await page.goto(`chrome-extension://${id}/room.html`);
  await expect(
    page.getByRole("heading", { name: "World & national events" }),
  ).toBeVisible();
  const state = await send({ type: "GET_STATE" });
  expect(state.ok).toBe(true);
}

async function roomTabCount() {
  const id = await extensionId();
  return context.pages().filter((candidate) => {
    try {
      const url = new URL(candidate.url());
      return url.host === id && url.pathname === "/room.html";
    } catch {
      return false;
    }
  }).length;
}

test.beforeEach(async () => {
  test.setTimeout(90_000);
  await mkdir(profileRoot, { recursive: true });
  profile = await mkdtemp(path.join(profileRoot, "room-"));
  control = { failNws: false, requests: [] };
  context = await launch();
  await extensionId();
  await routeFixtures();
  await openRoom();
  await send({ type: "SET_PAUSED", paused: false });
  const refreshed = await send({ type: "REFRESH" });
  expect(refreshed.ok).toBe(true);
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toBeVisible();
});

test.afterEach(async () => {
  await context?.close();
  if (profile) await rm(profile, { recursive: true, force: true });
});

test("shows read-only status, two sample places, source links, timestamps and safe feed text", async () => {
  await expect(
    page.getByRole("heading", { name: "Read-only · Shadow mode" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Home Assistant is not connected. This room cannot activate household alerts.",
    ),
  ).toBeVisible();
  for (const place of ["New York City, NY", "Washington, DC"])
    await expect(
      page.getByRole("button", { name: new RegExp(place) }),
    ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: maliciousTitle }),
  ).toBeVisible();
  await expect(page.getByText("In latest results")).toBeVisible();
  await expect(page.locator(".event-body img, .event-body svg")).toHaveCount(0);
  await expect(page.locator(".event-time").first()).not.toContainText(
    "Time unknown",
  );
  await expect(
    page.getByRole("link", { name: "Open source ↗" }).first(),
  ).toHaveAttribute("href", /^https:\/\//);
  await expect(
    page.getByRole("link", { name: "Open World Monitor ↗" }),
  ).toHaveAttribute("href", "https://www.worldmonitor.app/dashboard");
  await expect(
    page.getByRole("button", { name: "Pause collection" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Situareness Situation Room" }).click();
  await expect(page).toHaveURL(/#main$/);
  expect((await send({ type: "GET_STATE" })).ok).toBe(true);
  const existingRoomTabs = await roomTabCount();
  expect(existingRoomTabs).toBe(1);
  expect((await send({ type: "OPEN_ROOM" })).ok).toBe(true);
  await expect.poll(roomTabCount).toBe(existingRoomTabs);

  const queryVariant = new URL(page.url());
  queryVariant.searchParams.set("view", "compact");
  await page.goto(queryVariant.href);
  expect((await send({ type: "GET_STATE" })).ok).toBe(true);
  const pageCount = await roomTabCount();
  expect((await send({ type: "OPEN_ROOM" })).ok).toBe(true);
  await expect.poll(roomTabCount).toBe(pageCount);
});

test("filters by search, category and regional place and gives an explicit no-match state", async () => {
  await page
    .getByRole("searchbox", { name: "Search events" })
    .fill("earthquake");
  await expect(
    page.getByRole("heading", { name: "Magnitude 4.1 earthquake" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toHaveCount(0);
  await page.getByRole("searchbox", { name: "Search events" }).fill("");
  await page.getByLabel("Filter by category").selectOption("weather");
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Magnitude 4.1 earthquake" }),
  ).toHaveCount(0);
  await page.getByLabel("Filter by category").selectOption("all");
  await page.getByRole("button", { name: /Washington, DC/ }).click();
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toHaveCount(0);
  await expect(page.getByText("No matching events")).toBeVisible();
  await page
    .getByRole("searchbox", { name: "Search events" })
    .fill("no matching story");
  await expect(page.getByText("No matching events")).toBeVisible();
  await expect(page.locator("#feed-state")).toBeHidden();
});

test("pressing Enter in search applies the filter without navigating or clearing it", async () => {
  const navigationCount = await page.evaluate(
    () => performance.getEntriesByType("navigation").length,
  );
  const search = page.getByRole("searchbox", { name: "Search events" });
  await search.fill("earthquake");
  await search.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Magnitude 4.1 earthquake" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(
      () => performance.getEntriesByType("navigation").length,
    ),
  ).toBe(navigationCount);
  await expect(search).toHaveValue("earthquake");
});

test("saves editable places and provider intervals while live actions stay disabled", async () => {
  await page.getByRole("button", { name: "Open settings" }).click();
  const dialog = page.getByRole("dialog", { name: "Settings" });
  await dialog
    .getByLabel("Place name for nyc_sample")
    .fill("New York City Test");
  await dialog.getByLabel("Watch New York City, NY").uncheck();
  await dialog
    .getByLabel("BBC News World collection interval")
    .selectOption("30");
  await dialog.getByRole("button", { name: "Save settings" }).click();
  await expect(
    page.getByRole("button", { name: "New York City Test" }),
  ).toBeVisible();
  const state = await send({ type: "GET_STATE" });
  expect(state.state.config.live_actions_enabled).toBe(false);
  expect(state.state.config.enrolled_iphones).toEqual([]);
  expect(state.state.config.locations[0].household_exposure).toBeNull();
  expect(state.state.config.locations[0].watch_enabled).toBe(false);
  expect(
    state.state.config.sources.find((source) => source.id === "bbc_world")
      .interval_minutes,
  ).toBe(30);

  await page.getByRole("button", { name: "Open settings" }).click();
  const exportDialog = page.getByRole("dialog");
  await ensureConfigEditorVisible(exportDialog);
  const downloadPromise = page.waitForEvent("download");
  await expect(
    exportDialog.getByText(
      /Exports include watched places and source preferences\. Treat the file as sensitive/,
    ),
  ).toBeVisible();
  await exportDialog.getByRole("button", { name: "Export settings" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(
    "situareness-browser-settings.json",
  );
  const exportPath = await download.path();
  const exportedJson = await readFile(exportPath, "utf8");
  const exportedSettings = JSON.parse(exportedJson);
  expect(exportedSettings.live_actions_enabled).toBe(false);
  expect(exportedSettings.enrolled_iphones).toEqual([]);
  expect(
    exportedSettings.locations.every(
      (place) =>
        place.household_exposure === null &&
        place.google_speaker_targets.length === 0 &&
        place.horn_targets.length === 0 &&
        !Object.hasOwn(place, "latitude") &&
        !Object.hasOwn(place, "longitude"),
    ),
  ).toBe(true);
  await exportDialog.getByRole("button", { name: "Cancel" }).click();

  const jsonConfig = structuredClone(state.state.config);
  jsonConfig.locations[1].name = "Washington from JSON";
  jsonConfig.sources.find(
    (source) => source.id === "bbc_world",
  ).interval_minutes = 10;
  await page.getByRole("button", { name: "Open settings" }).click();
  const jsonDialog = page.getByRole("dialog");
  await ensureConfigEditorVisible(jsonDialog);
  await jsonDialog
    .locator("#config-json")
    .fill(JSON.stringify(jsonConfig, null, 2));
  await jsonDialog.getByRole("button", { name: "Save settings" }).click();
  let saved = await send({ type: "GET_STATE" });
  expect(saved.state.config.locations[1].name).toBe("Washington from JSON");
  expect(
    saved.state.config.sources.find((source) => source.id === "bbc_world")
      .interval_minutes,
  ).toBe(10);

  const imported = structuredClone(saved.state.config);
  imported.locations[1].name = "Washington from import";
  imported.locations[1].watch_enabled = false;
  imported.locations[1].household_exposure = {
    latitude: 40.7,
    longitude: -73.9,
  };
  await page.getByRole("button", { name: "Open settings" }).click();
  const importDialog = page.getByRole("dialog");
  await ensureConfigEditorVisible(importDialog);
  await importDialog
    .locator("#import-file")
    .setInputFiles({
      name: "browser-settings.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(imported)),
    });
  await importDialog.getByRole("button", { name: "Save settings" }).click();
  saved = await send({ type: "GET_STATE" });
  expect(saved.state.config.locations[1]).toMatchObject({
    name: "Washington from import",
    watch_enabled: false,
    household_exposure: null,
  });
  expect(Object.hasOwn(saved.state.config.locations[1], "latitude")).toBe(
    false,
  );
});

test("shows cached data after source failure and surfaces stale/truncated source metadata", async () => {
  control.failNws = true;
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(page.getByText("Provider returned HTTP 503.")).toBeVisible();
  const failed = await send({ type: "GET_STATE" });
  expect(
    failed.state.sources.find((source) => source.id === "nws"),
  ).toMatchObject({
    status: "error",
    last_error: "Provider returned HTTP 503.",
  });
  expect(
    failed.state.events.some(
      (event) => event.title === "Wind advisory for New York City",
    ),
  ).toBe(true);

  const stored = structuredClone(failed.state);
  const old = new Date(Date.now() - 2 * 60 * 60_000).toISOString();
  stored.collector.paused = true;
  stored.collector.last_run_at = old;
  for (const source of stored.sources) {
    source.last_success_at = old;
    source.last_attempt_at = old;
  }
  const addedAt = new Date(Date.now() - 5 * 60_000).toISOString();
  stored.events.push(
    {
      id: "nws:not-latest",
      source_id: "nws",
      source_name: "National Weather Service alerts",
      title: "Not latest fixture",
      summary: null,
      url: null,
      published_at: addedAt,
      updated_at: null,
      collected_at: addedAt,
      expires_at: new Date(Date.now() + 60 * 60_000).toISOString(),
      status: "actual",
      category: "weather",
      severity: null,
      urgency: null,
      certainty: null,
      location_ids: [],
      geometry: null,
      instructions: null,
      official: true,
      awareness_lifecycle: "not_in_latest_fetch",
    },
    {
      id: "nws:expired",
      source_id: "nws",
      source_name: "National Weather Service alerts",
      title: "Expired fixture",
      summary: null,
      url: null,
      published_at: addedAt,
      updated_at: null,
      collected_at: addedAt,
      expires_at: new Date(Date.now() - 60_000).toISOString(),
      status: "actual",
      category: "weather",
      severity: null,
      urgency: null,
      certainty: null,
      location_ids: [],
      geometry: null,
      instructions: null,
      official: true,
      awareness_lifecycle: "current",
    },
  );
  const world = stored.sources.find((source) => source.id === "bbc_world");
  world.items_available = 245;
  world.truncated = true;
  world.event_count = 200;
  await workerFor().then((worker) =>
    worker.evaluate(
      async (value) =>
        chrome.storage.local.set({ situareness_state_v1: value }),
      stored,
    ),
  );
  await context.close();
  context = await launch();
  await routeFixtures();
  await openRoom();
  await expect(page.getByText(/overdue/)).toBeVisible();
  await expect(
    page.getByText("Limited to 200 recent items · 245 available"),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toBeVisible();
  await expect(page.getByText("Not in latest results")).toBeVisible();
  await expect(page.getByText("Source expiry passed")).toBeVisible();
  const expiredCard = page
    .locator(".event-card")
    .filter({ has: page.getByRole("heading", { name: "Expired fixture" }) });
  await expect(expiredCard.locator(".presence-pill")).toHaveAttribute(
    "title",
    /does not establish that the hazard ended/,
  );
});

test("rejects invalid configuration imports and keeps the room usable at a phone viewport", async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "World & national events" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open settings" }).click();
  const dialog = page.getByRole("dialog");
  await ensureConfigEditorVisible(dialog);
  await dialog
    .locator("#import-file")
    .setInputFiles({
      name: "bad.json",
      mimeType: "application/json",
      buffer: Buffer.from('{"schema_version":2}'),
    });
  await expect(dialog.getByRole("alert")).toContainText("schema version 1");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await page.screenshot({
    path: "work/evidence/room-mobile.png",
    fullPage: false,
  });
});

test("settings close button and cancel close without saving edits", async () => {
  await page.getByRole("button", { name: "Open settings" }).click();
  let dialog = page.getByRole("dialog", { name: "Settings" });
  await dialog
    .getByLabel("Place name for nyc_sample")
    .fill("Unsaved close edit");
  await dialog.getByRole("button", { name: "Close settings" }).click();
  await expect(dialog).toBeHidden();
  expect(
    (await send({ type: "GET_STATE" })).state.config.locations[0].name,
  ).not.toBe("Unsaved close edit");

  await page.getByRole("button", { name: "Open settings" }).click();
  dialog = page.getByRole("dialog", { name: "Settings" });
  await dialog
    .getByLabel("Place name for nyc_sample")
    .fill("Unsaved cancel edit");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  expect(
    (await send({ type: "GET_STATE" })).state.config.locations[0].name,
  ).not.toBe("Unsaved cancel edit");

  await page.getByRole("button", { name: "Open settings" }).click();
  dialog = page.getByRole("dialog", { name: "Settings" });
  await dialog
    .getByLabel("Place name for nyc_sample")
    .fill("Unsaved escape edit");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  expect(
    (await send({ type: "GET_STATE" })).state.config.locations[0].name,
  ).not.toBe("Unsaved escape edit");
});

test("refreshes an already open room from collector state without a page reload", async () => {
  const navigationCount = await page.evaluate(
    () => performance.getEntriesByType("navigation").length,
  );
  const current = await send({ type: "GET_STATE" });
  const changed = structuredClone(current.state.config);
  changed.locations[1].name = "Washington updated by collector";
  const response = await send({ type: "UPDATE_CONFIG", config: changed });
  expect(response.ok).toBe(true);
  await expect(
    page.getByRole("button", { name: "Washington updated by collector" }),
  ).toBeVisible({ timeout: 25_000 });
  expect(
    await page.evaluate(
      () => performance.getEntriesByType("navigation").length,
    ),
  ).toBe(navigationCount);
});

test("marks the collector disconnected, preserves cached events and disables stale controls", async () => {
  await page.evaluate(() => {
    Object.defineProperty(chrome.runtime, "sendMessage", {
      configurable: true,
      value: async () => {
        throw new Error("Simulated local collector outage.");
      },
    });
  });
  await expect(page.getByText("Collector disconnected")).toBeVisible({
    timeout: 20_000,
  });
  await expect(
    page.getByText(/Local collector unavailable\. Showing cached data/),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh" })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Pause collection" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("heading", { name: "Wind advisory for New York City" }),
  ).toBeVisible();
});

test("omitted providers use bundled defaults when restored through settings and import", async () => {
  const initial = (await send({ type: "GET_STATE" })).state.config;
  const missing = structuredClone(initial);
  missing.sources = missing.sources.filter(
    (source) => !["nws", "usgs"].includes(source.id),
  );
  expect((await send({ type: "UPDATE_CONFIG", config: missing })).ok).toBe(
    true,
  );
  await page.reload();
  await page.getByRole("button", { name: "Open settings" }).click();
  let dialog = page.getByRole("dialog");
  await expect(
    dialog.getByLabel("National Weather Service alerts collection interval"),
  ).toHaveValue("1");
  await expect(
    dialog.getByLabel("USGS earthquakes (post-event only) collection interval"),
  ).toHaveValue("1");
  await expect(dialog.locator('option[value="NaN"]')).toHaveCount(0);
  await dialog.getByLabel("Enable National Weather Service alerts").check();
  await dialog.getByLabel("Enable USGS earthquakes (post-event only)").check();
  await dialog.getByRole("button", { name: "Save settings" }).click();
  let saved = (await send({ type: "GET_STATE" })).state.config;
  expect(
    saved.sources.find((source) => source.id === "nws").interval_minutes,
  ).toBe(1);
  expect(
    saved.sources.find((source) => source.id === "usgs").interval_minutes,
  ).toBe(1);
  await page.getByRole("button", { name: "Open settings" }).click();
  dialog = page.getByRole("dialog");
  await ensureConfigEditorVisible(dialog);
  await dialog
    .locator("#import-file")
    .setInputFiles({
      name: "missing.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(missing)),
    });
  await expect(
    dialog.getByLabel("Enable National Weather Service alerts"),
  ).not.toBeChecked();
  await expect(
    dialog.getByLabel("Enable USGS earthquakes (post-event only)"),
  ).not.toBeChecked();
  await expect(
    dialog.getByLabel("National Weather Service alerts collection interval"),
  ).toHaveValue("1");
  await expect(
    dialog.getByLabel("USGS earthquakes (post-event only) collection interval"),
  ).toHaveValue("1");
  await dialog.getByLabel("Enable National Weather Service alerts").check();
  await dialog.getByLabel("Enable USGS earthquakes (post-event only)").check();
  await dialog.getByRole("button", { name: "Save settings" }).click();
  saved = (await send({ type: "GET_STATE" })).state.config;
  expect(
    saved.sources.find((source) => source.id === "nws").interval_minutes,
  ).toBe(1);
  expect(
    saved.sources.find((source) => source.id === "usgs").interval_minutes,
  ).toBe(1);
});

test("disabled failed sources are neutral and storage truncation is visible", async () => {
  const stored = structuredClone((await send({ type: "GET_STATE" })).state);
  stored.collector.paused = false;
  stored.collector.storage_truncated = true;
  const source = stored.sources.find((item) => item.id === "nws");
  Object.assign(source, {
    enabled: false,
    status: "error",
    last_error: "Old failure",
    last_success_at: "2020-01-01T00:00:00Z",
  });
  stored.config.sources.find((item) => item.id === "nws").enabled = false;
  await workerFor().then((worker) =>
    worker.evaluate(
      async (value) =>
        chrome.storage.local.set({ situareness_state_v1: value }),
      stored,
    ),
  );
  await context.close();
  context = await launch();
  await routeFixtures();
  await openRoom();
  await expect(
    page
      .locator(".source-row")
      .filter({ hasText: "National Weather Service alerts" }),
  ).toContainText("Disabled");
  await expect(
    page
      .locator(".source-row")
      .filter({ hasText: "National Weather Service alerts" })
      .locator(".source-status"),
  ).toHaveClass(/disabled/);
  await expect(page.getByText("Old failure")).toHaveCount(0);
  await expect(page.locator("#collector-dot")).not.toHaveClass(/error/);
  await expect(page.locator("#freshness-note")).toContainText(
    "500-item storage limit omitted some items",
  );
  await expect(page.locator("#freshness-note")).not.toContainText("failed");
});
