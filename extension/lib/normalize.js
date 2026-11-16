import { safeUrl } from "./config.js";

const str = (v, max = 4000) =>
  typeof v === "string" ? v.trim().slice(0, max) : null;
const date = (v) => {
  if (v == null) return null;
  const d = new Date(v);
  return Number.isFinite(d.getTime()) ? d.toISOString() : null;
};
const cleanText = (v) =>
  str(v)
    ?.replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim() || null;
const statusValues = Object.freeze({
    Actual: "actual",
    Test: "test",
    Exercise: "exercise",
    Cancel: "cancelled",
    Cancelled: "cancelled",
  });
const status = (v) =>
  Object.hasOwn(statusValues, v) ? statusValues[v] : "unknown";
const geometry = (value) => {
  if (!value || typeof value !== "object") return null;
  try {
    return JSON.stringify(value).length <= 5000 ? value : null;
  } catch {
    return null;
  }
};
function event(source, raw, now) {
  return {
    id: `${source.id}:${raw.id}`,
    source_id: source.id,
    source_name: source.name,
    title: str(raw.title, 500) || "Untitled",
    summary: cleanText(raw.summary),
    url: safeUrl(raw.url),
    published_at: date(raw.published_at),
    updated_at: date(raw.updated_at),
    collected_at: now,
    expires_at: date(raw.expires_at),
    status: raw.status || "unknown",
    category: raw.category,
    severity: str(raw.severity, 80),
    urgency: str(raw.urgency, 80),
    certainty: str(raw.certainty, 80),
    location_ids: raw.location_ids || [],
    geometry: geometry(raw.geometry),
    instructions: cleanText(raw.instructions),
    official: raw.official,
    ...(source.kind === "nws" ? { awareness_lifecycle: "current" } : {}),
  };
}
export const MAX_SOURCE_ITEMS = 200;
export function normalizeJson(source, data, now, locations = []) {
  if (!data || !Array.isArray(data.features))
    throw new Error("Invalid provider response.");
  const result = [];
  const features = [...data.features]
    .sort((a, b) => {
      const time = (feature) => {
        const v =
          source.kind === "nws"
            ? feature?.properties?.sent
            : feature?.properties?.time;
        const parsed = typeof v === "number" ? v : Date.parse(v);
        return Number.isFinite(parsed) ? parsed : -Infinity;
      };
      return time(b) - time(a);
    })
    .slice(0, MAX_SOURCE_ITEMS);
  for (const feature of features) {
    const p = feature?.properties;
    if (!p || typeof p !== "object") continue;
    if (source.kind === "nws") {
      const id = str(p.id || feature.id, 1000);
      if (!id) continue;
      const sourceUrl =
        [feature.id, p.id].map(safeUrl).find((url) => {
          if (!url) return false;
          const parsed = new URL(url);
          return (
            parsed.protocol === "https:" && parsed.host === "api.weather.gov"
          );
        }) || null;
      const same = Array.isArray(p.geocode?.SAME)
        ? p.geocode.SAME.filter(
            (code) => typeof code === "string" && /^[0-9]{6}$/.test(code),
          ).map((code) => code.slice(1))
        : [];
      const location_ids = locations
        .filter((location) => {
          if (!location.watch_enabled || !location.awareness_area) return false;
          const counties = location.awareness_area.county_fips;
          return (Array.isArray(counties) ? counties : [counties]).some((county) =>
            same.includes(county),
          );
        })
        .map((l) => l.id);
      result.push(
        event(
          source,
          {
            id,
            location_ids,
            title: p.headline || p.event,
            summary: p.description,
            url: sourceUrl,
            published_at: p.sent,
            updated_at: null,
            expires_at: p.expires,
            status: status(
              p.status === "Actual" && p.messageType === "Cancel"
                ? "Cancel"
                : p.status,
            ),
            category: "weather",
            severity: p.severity,
            urgency: p.urgency,
            certainty: p.certainty,
            geometry: feature.geometry,
            instructions: p.instruction,
            official: true,
          },
          now,
        ),
      );
    } else if (source.kind === "usgs") {
      const id = str(feature.id, 1000);
      if (!id) continue;
      result.push(
        event(
          source,
          {
            id,
            title: p.title,
            summary: p.place,
            url: p.url,
            published_at: p.time,
            updated_at: p.updated,
            status: "actual",
            category: "earthquake",
            geometry: feature.geometry,
            official: true,
          },
          now,
        ),
      );
    }
  }
  return result;
}
export function normalizeRss(source, items, now) {
  if (!Array.isArray(items)) throw new Error("Invalid feed response.");
  return items.slice(0, MAX_SOURCE_ITEMS).flatMap((item) => {
    const id = str(item.id || item.url, 1000);
    if (!id) return [];
    return [
      event(
        source,
        {
          id,
          title: item.title,
          summary: item.summary,
          url: item.url,
          published_at: item.published_at,
          updated_at: item.updated_at,
          status: "actual",
          category: "news",
          official: false,
        },
        now,
      ),
    ];
  });
}
