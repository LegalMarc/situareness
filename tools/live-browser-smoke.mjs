// Opt-in read-only smoke test. Uses an isolated Chromium profile and real provider responses.
// Run from the repository root: node tools/live-browser-smoke.mjs
import { chromium } from "playwright";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import path from "node:path";

const extension = path.resolve("extension");
const profiles = path.resolve("work/browser-profiles");
const evidence = path.resolve("work/evidence");
await mkdir(profiles, { recursive: true });
await mkdir(evidence, { recursive: true });
const profile = await mkdtemp(path.join(profiles, "live-smoke-"));
const report = {
  started_at: new Date().toISOString(),
  mode: "live_read_only",
  endpoints: [],
  sources: [],
  offscreen_document: false,
  screenshot: null,
  result: "incomplete",
};
let context;
let timer;
try {
  await Promise.race([
    (async () => {
      context = await chromium.launchPersistentContext(profile, {
        channel: "chromium",
        headless: true,
        viewport: { width: 1400, height: 900 },
        args: [
          `--disable-extensions-except=${extension}`,
          `--load-extension=${extension}`,
        ],
      });
      context.on("response", (response) => {
        const url = new URL(response.url());
        if (
          [
            "api.weather.gov",
            "earthquake.usgs.gov",
            "feeds.bbci.co.uk",
          ].includes(url.hostname)
        )
          report.endpoints.push({
            host: url.hostname,
            path: url.pathname,
            status: response.status(),
          });
      });
      const worker =
        context.serviceWorkers()[0] ||
        (await context.waitForEvent("serviceworker", { timeout: 15_000 }));
      const id = new URL(worker.url()).host;
      const page = await context.newPage();
      await page.goto(`chrome-extension://${id}/room.html`);
      // A fresh profile runs the extension's installation collection. Observe
      // that single collection rather than immediately forcing another poll.
      let state;
      while (true) {
        const response = await page.evaluate(() =>
          chrome.runtime.sendMessage({ type: "GET_STATE" }),
        );
        if (!response?.ok)
          throw new Error(response?.error || "Extension state unavailable.");
        state = response.state;
        const enabled = state.sources.filter((source) => source.enabled);
        if (
          enabled.length > 0 &&
          !state.collector.running &&
          enabled.every((source) => source.last_attempt_at)
        )
          break;
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
      report.sources = state.sources.map((s) => ({
        id: s.id,
        status: s.status,
        last_success_at: s.last_success_at,
        last_error: s.last_error,
        event_count: s.event_count,
        items_available: s.items_available,
        truncated: s.truncated,
      }));
      report.offscreen_document =
        (
          await worker.evaluate(() =>
            chrome.runtime.getContexts({
              contextTypes: ["OFFSCREEN_DOCUMENT"],
            }),
          )
        ).length > 0;
      report.event_counts = Object.fromEntries(
        state.config.sources.map((s) => [
          s.id,
          state.events.filter((e) => e.source_id === s.id).length,
        ]),
      );
      await page.reload();
      await page.waitForFunction(
        () => document.querySelector("#source-list")?.children.length >= 4,
      );
      await page.screenshot({
        path: path.join(evidence, "live-browser-smoke.png"),
        fullPage: false,
      });
      report.screenshot = "work/evidence/live-browser-smoke.png";
      report.result =
        report.sources.every((s) => s.status === "ok") &&
        report.offscreen_document
          ? "passed"
          : "provider_or_parser_failure";
    })(),
    new Promise((_, reject) => {
      timer = setTimeout(
        () => reject(new Error("Smoke test exceeded 85 seconds.")),
        85_000,
      );
    }),
  ]);
} catch (error) {
  report.error = error instanceof Error ? error.message : "Smoke test failed.";
} finally {
  clearTimeout(timer);
  if (context) await context.close().catch(() => {});
  await rm(profile, { recursive: true, force: true });
  report.finished_at = new Date().toISOString();
  await writeFile(
    path.join(evidence, "live-browser-smoke.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report, null, 2));
  if (report.result !== "passed") process.exitCode = 1;
}
