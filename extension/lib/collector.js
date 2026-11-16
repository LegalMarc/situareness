import { MAX_SOURCE_ITEMS, normalizeJson, normalizeRss } from "./normalize.js";

export const MAX_BYTES = 8_000_000;
export const MAX_EVENTS = 500;
const TIMEOUT_MS = 12000;
const RETAIN_MS = 7 * 24 * 60 * 60 * 1000;

export async function readBounded(response) {
  if (!response.ok)
    throw new Error(`Provider returned HTTP ${response.status}.`);
  const length = Number(response.headers.get("content-length"));
  if (length > MAX_BYTES)
    throw new Error("Provider response exceeded size limit.");
  if (!response.body) throw new Error("Provider response has no body.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let size = 0,
    result = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) {
        await reader.cancel();
        throw new Error("Provider response exceeded size limit.");
      }
      result += decoder.decode(value, { stream: true });
    }
    return result + decoder.decode();
  } finally {
    reader.releaseLock();
  }
}
export function sourceState(source, previous) {
  return {
    id: source.id,
    name: source.name,
    url: source.url,
    enabled: source.enabled,
    status: previous?.status || "idle",
    last_attempt_at: previous?.last_attempt_at || null,
    last_alarm_tick: Number.isSafeInteger(previous?.last_alarm_tick)
      ? previous.last_alarm_tick
      : null,
    last_success_at: previous?.last_success_at || null,
    last_error: previous?.last_error || null,
    event_count: previous?.event_count || 0,
    items_available: previous?.items_available ?? null,
    truncated: previous?.truncated ?? false,
  };
}
export async function collectSource(
  source,
  previous,
  {
    fetcher = fetch,
    parseRss,
    locations = [],
    now = () => new Date(),
    timeoutMs = TIMEOUT_MS,
  } = {},
) {
  const attempt = now().toISOString();
  const current = {
    ...sourceState(source, previous),
    last_attempt_at: attempt,
  };
  const controller = new AbortController();
  let timer;
  const deadline = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      const error = new Error("Timed out");
      error.name = "AbortError";
      reject(error);
    }, timeoutMs);
  });
  try {
    const work = (async () => {
      const response = await fetcher(source.url, {
        signal: controller.signal,
        redirect: "error",
        credentials: "omit",
        cache: "no-store",
        headers: {
          Accept:
            source.kind === "rss"
              ? "application/rss+xml, application/xml, text/xml"
              : "application/geo+json, application/json",
        },
      });
      const body = await readBounded(response);
      const received = now().toISOString();
      const parsed =
        source.kind === "rss" ? await parseRss(body) : JSON.parse(body);
      const available =
        source.kind === "rss"
          ? parsed.items_available
          : parsed.features?.length;
      if (!Number.isInteger(available) || available < 0)
        throw new Error("Invalid provider response.");
      const events =
        source.kind === "rss"
          ? normalizeRss(source, parsed.items, received)
          : normalizeJson(source, parsed, received, locations);
      return {
        source: {
          ...current,
          status: "ok",
          last_success_at: received,
          last_error: null,
          event_count: events.length,
          items_available: available,
          truncated:
            available > MAX_SOURCE_ITEMS || Boolean(parsed?.pagination?.next),
        },
        events,
        source_kind: source.kind,
      };
    })();
    return await Promise.race([work, deadline]);
  } catch (error) {
    const message =
      error?.name === "AbortError"
        ? "Provider request timed out."
        : /^Provider (returned HTTP \d+|response exceeded size limit|response has no body)\.$/.test(
              error?.message || "",
            )
          ? error.message
          : "Provider request or response failed.";
    return {
      source: { ...current, status: "error", last_error: message },
      events: null,
    };
  } finally {
    clearTimeout(timer);
  }
}
export function retainEvents(existing, results, now) {
  const cutoff = now.getTime() - RETAIN_MS;
  const byId = new Map();
  for (const item of existing) {
    if (
      item &&
      typeof item.id === "string" &&
      (Date.parse(item.collected_at) >= cutoff ||
        (item.awareness_lifecycle === "current" &&
          (!Number.isFinite(Date.parse(item.expires_at)) ||
            Date.parse(item.expires_at) > now.getTime())))
    )
      byId.set(item.id, item);
  }
  for (const result of results) {
    if (result.source_kind === "nws" && result.events) {
      const seen = new Set(result.events.map((item) => item.id));
      for (const [id, item] of byId) {
        if (
          item.source_id === result.source.id &&
          !seen.has(id) &&
          item.awareness_lifecycle !== "expired"
        ) {
          byId.set(id, { ...item, awareness_lifecycle: "not_in_latest_fetch" });
        }
      }
    }
    for (const item of result.events || []) byId.set(item.id, item);
  }
  const ordered = [...byId.values()].sort((a, b) => {
    const priority = (item) =>
      item.awareness_lifecycle === "current" &&
      (!Number.isFinite(Date.parse(item.expires_at)) ||
        Date.parse(item.expires_at) > now.getTime())
        ? 1
        : 0;
    return (
      priority(b) - priority(a) ||
      (Date.parse(b.updated_at || b.published_at || b.collected_at) || 0) -
        (Date.parse(a.updated_at || a.published_at || a.collected_at) || 0)
    );
  });
  return {
    events: ordered.slice(0, MAX_EVENTS),
    dropped: Math.max(0, ordered.length - MAX_EVENTS),
  };
}

export function mergeEvents(existing, results, now) {
  return retainEvents(existing, results, now).events;
}

// Expiry is local clock-based information, independent of source availability.
export function markExpired(events, now) {
  return events.map((item) => {
    const expiry = Date.parse(item.expires_at);
    if (
      item.awareness_lifecycle &&
      item.awareness_lifecycle !== "expired" &&
      Number.isFinite(expiry) &&
      expiry <= now.getTime()
    ) {
      return { ...item, awareness_lifecycle: "expired" };
    }
    return item;
  });
}
