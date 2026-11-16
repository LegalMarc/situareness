import { test, expect, chromium } from "@playwright/test";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import path from "node:path";

const extension = path.resolve("extension");
const profileRoot = path.resolve("work/browser-profiles");
const fixtureTime = new Date();
const rss = `<?xml version="1.0"?><rss version="2.0"><channel><title>BBC test</title>
  <item><guid>bbc-fixture-1</guid><title>Fixture &amp; headline</title><link>https://www.bbc.com/news/fixture</link><description><![CDATA[<b>Fixture story</b>]]></description><pubDate>${fixtureTime.toUTCString()}</pubDate></item>
</channel></rss>`;
const nws = {
  features: [
    {
      id: "https://api.weather.gov/alerts/fixture",
      geometry: null,
      properties: {
        id: "https://api.weather.gov/alerts/fixture",
        headline: "Fixture weather",
        status: "Actual",
        sent: fixtureTime.toISOString(),
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
        title: "Fixture earthquake",
        url: "https://earthquake.usgs.gov/earthquakes/eventpage/fixture",
        time: fixtureTime.getTime(),
      },
    },
  ],
};

async function launch(profile) {
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
async function extensionId(context) {
  const worker =
    context.serviceWorkers()[0] ||
    (await context.waitForEvent("serviceworker", { timeout: 15_000 }));
  return new URL(worker.url()).host;
}
async function routeFixtures(context, control) {
  await context.route(
    /^https:\/\/(api\.weather\.gov|earthquake\.usgs\.gov|feeds\.bbci\.co\.uk)\//,
    async (route) => {
      control.requests.push({
        url: route.request().url(),
        worker: Boolean(route.request().serviceWorker()),
      });
      if (control.fail && route.request().url().includes("api.weather.gov"))
        return route.fulfill({ status: 503, body: "fixture unavailable" });
      if (route.request().url().includes("api.weather.gov"))
        return route.fulfill({
          status: 200,
          contentType: "application/geo+json",
          body: JSON.stringify(nws),
        });
      if (route.request().url().includes("earthquake.usgs.gov"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(usgs),
        });
      return route.fulfill({
        status: 200,
        contentType: "application/rss+xml",
        body: rss,
      });
    },
  );
}
const send = (page, message) =>
  page.evaluate((message) => chrome.runtime.sendMessage(message), message);

test("extension collection, messaging, room reuse and persisted restart", async () => {
  test.setTimeout(90_000);
  await mkdir(profileRoot, { recursive: true });
  const profile = await mkdtemp(path.join(profileRoot, "runtime-"));
  let context;
  try {
    context = await launch(profile);
    const id = await extensionId(context);
    const control = { fail: false, requests: [] };
    await routeFixtures(context, control);
    const page = await context.newPage();
    await page.goto(`chrome-extension://${id}/room.html`);
    const initial = await send(page, { type: "GET_STATE" });
    expect(initial.ok).toBe(true);
    expect(initial.state.ha.status).toBe("not_connected");
    const untrusted = await context.newPage();
    await untrusted.goto(`chrome-extension://${id}/offscreen.html`);
    expect(await send(untrusted, { type: "GET_STATE" })).toEqual({
      ok: false,
      error: "Untrusted sender.",
    });
    await untrusted.close();
    const unpause = await send(page, { type: "SET_PAUSED", paused: false });
    expect(unpause.ok).toBe(true);
    const first = await send(page, { type: "REFRESH" });
    expect(first.ok).toBe(true);
    expect(first.state.sources.map((s) => s.status)).toEqual([
      "ok",
      "ok",
      "ok",
      "ok",
    ]);
    expect(
      first.state.events.find(
        (e) => e.id === "nws:https://api.weather.gov/alerts/fixture",
      ).location_ids,
    ).toEqual(["nyc_sample"]);
    const news = first.state.events.find(
      (e) => e.id === "bbc_world:bbc-fixture-1",
    );
    expect(news.title).toBe("Fixture & headline");
    expect(news.summary).toBe("Fixture story");
    expect(
      control.requests.filter((r) => r.worker).length,
    ).toBeGreaterThanOrEqual(4);
    const changed = structuredClone(first.state.config);
    changed.locations[0].watch_enabled = false;
    changed.locations.push({
      ...changed.locations[0],
      id: "test_region",
      name: "Test Region, NJ",
      watch_enabled: true,
      awareness_area: { state: "NJ", county_fips: "34001" },
    });
    const update = await send(page, { type: "UPDATE_CONFIG", config: changed });
    expect(
      new URL(
        update.state.config.sources.find((s) => s.id === "nws").url,
      ).searchParams.get("area"),
    ).toBe("DC,NJ");
    const changedResult = await send(page, { type: "REFRESH" });
    expect(
      changedResult.state.events.find(
        (e) => e.id === "nws:https://api.weather.gov/alerts/fixture",
      ).location_ids,
    ).toEqual([]);
    await send(page, { type: "UPDATE_CONFIG", config: first.state.config });
    const restored = await send(page, { type: "REFRESH" });
    const lastSuccess = restored.state.sources.find(
      (s) => s.id === "nws",
    ).last_success_at;
    control.fail = true;
    const failed = await send(page, { type: "REFRESH" });
    expect(failed.state.sources.find((s) => s.id === "nws")).toMatchObject({
      status: "error",
      last_success_at: lastSuccess,
      last_error: "Provider returned HTTP 503.",
    });
    expect(
      failed.state.events.some(
        (e) => e.id === "nws:https://api.weather.gov/alerts/fixture",
      ),
    ).toBe(true);
    const invalid = structuredClone(failed.state.config);
    invalid.live_actions_enabled = true;
    expect(
      (await send(page, { type: "UPDATE_CONFIG", config: invalid })).ok,
    ).toBe(false);
    expect(
      (await send(page, { type: "OPEN_SOURCE", url: "javascript:alert(1)" }))
        .ok,
    ).toBe(false);
    expect((await send(page, { type: "OPEN_ROOM" })).ok).toBe(true);
    expect((await send(page, { type: "OPEN_ROOM" })).ok).toBe(true);
    expect(
      context
        .pages()
        .filter((p) => p.url() === `chrome-extension://${id}/room.html`),
    ).toHaveLength(1);
    const paused = await send(page, { type: "SET_PAUSED", paused: true });
    expect(paused.state.collector.paused).toBe(true);
    await context.close();
    context = undefined;
    context = await launch(profile);
    const restartedId = await extensionId(context);
    expect(restartedId).toBe(id);
    await routeFixtures(context, control);
    const restartedPage = await context.newPage();
    await restartedPage.goto(`chrome-extension://${id}/room.html`);
    const restarted = await send(restartedPage, { type: "GET_STATE" });
    expect(restarted.state.collector.paused).toBe(true);
    expect(restarted.state.collector.running).toBe(false);
    expect(
      restarted.state.sources.find((s) => s.id === "nws").last_success_at,
    ).toBe(lastSuccess);
    expect(
      restarted.state.events.some((e) => e.id === "bbc_world:bbc-fixture-1"),
    ).toBe(true);
  } finally {
    if (context) await context.close();
    await rm(profile, { recursive: true, force: true });
  }
});
