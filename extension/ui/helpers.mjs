import { sourceFreshness } from "../lib/freshness.js";
export { sourceFreshness } from "../lib/freshness.js";

const SECRET_KEY = /(?:token|secret|password|credential|api[_-]?key)/i;
const PRIVATE_KEYS = new Set([
  "household_exposure",
  "enrolled_iphones",
  "google_speaker_targets",
  "horn_targets",
]);

/** Return only HTTP(S) URLs without embedded credentials. */
export function safeHttpUrl(value) {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password
    )
      return null;
    return url.href;
  } catch {
    return null;
  }
}

/** Remove private enrollment/footprint fields and secret-like fields recursively. */
export function publicConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config))
    throw new TypeError("Configuration must be an object.");
  const clean = (value, key = "") => {
    if (PRIVATE_KEYS.has(key) || SECRET_KEY.test(key)) return undefined;
    if (Array.isArray(value))
      return value
        .map((item) => clean(item))
        .filter((item) => item !== undefined);
    if (value && typeof value === "object") {
      const result = {};
      for (const [childKey, childValue] of Object.entries(value)) {
        const child = clean(childValue, childKey);
        if (child !== undefined) result[childKey] = child;
      }
      return result;
    }
    return value;
  };
  const input = clean(config);
  const pick = (value, keys) =>
    Object.fromEntries(
      keys
        .filter((key) => Object.hasOwn(value || {}, key))
        .map((key) => [key, value[key]]),
    );
  return {
    schema_version: input.schema_version,
    artifact_status: input.artifact_status,
    live_actions_enabled: false,
    room: {
      ...pick(input.room, ["browser", "closing_room_stops_monitoring"]),
      ...(Object.hasOwn(input.room || {}, "context_dashboard") ||
      Object.hasOwn(input.room || {}, "primary_dashboard")
        ? {
            context_dashboard: safeHttpUrl(
              Object.hasOwn(input.room, "context_dashboard")
                ? input.room.context_dashboard
                : input.room.primary_dashboard,
            ),
          }
        : {}),
    },
    alarm_policy: pick(input.alarm_policy, [
      "required_gates",
      "qualifying_events_allowed_overnight",
      "first_phone_delivery",
      "speaker_and_horn_delivery",
      "acknowledgement_scope",
      "repeat_and_test_cadence",
    ]),
    enrolled_iphones: [],
    locations: Array.isArray(input.locations)
      ? input.locations.map((location) => ({
          ...pick(location, [
            "id",
            "name",
            "watch_enabled",
            "timezone",
            "input_normalization_note",
          ]),
          ...(Object.hasOwn(location, "official_alert_enrollment")
            ? {
                official_alert_enrollment: safeHttpUrl(
                  location.official_alert_enrollment,
                ),
              }
            : {}),
          ...(Object.hasOwn(location, "verified_event_ingestion")
            ? {
                verified_event_ingestion: safeHttpUrl(
                  location.verified_event_ingestion,
                ),
              }
            : {}),
          ...(location.awareness_area &&
          typeof location.awareness_area === "object"
            ? {
                awareness_area: pick(location.awareness_area, [
                  "state",
                  "county_fips",
                ]),
              }
            : {}),
          household_exposure: null,
          google_speaker_targets: [],
          horn_targets: [],
        }))
      : input.locations,
    sources: Array.isArray(input.sources)
      ? input.sources.map((source) => ({
          ...pick(source, [
            "id",
            "name",
            "kind",
            "enabled",
            "interval_minutes",
          ]),
          ...(Object.hasOwn(source, "url")
            ? { url: safeHttpUrl(source.url) }
            : {}),
        }))
      : input.sources,
  };
}

export function parsePublicConfig(jsonText) {
  let input;
  try {
    input = JSON.parse(jsonText);
  } catch {
    throw new TypeError("Enter valid JSON.");
  }
  if (!input || typeof input !== "object" || Array.isArray(input))
    throw new TypeError("Configuration must be a JSON object.");
  const cleaned = publicConfig(input);
  if (cleaned.schema_version !== 1)
    throw new TypeError("Only schema version 1 is supported.");
  for (const key of ["room", "alarm_policy"]) {
    if (
      !cleaned[key] ||
      typeof cleaned[key] !== "object" ||
      Array.isArray(cleaned[key])
    )
      throw new TypeError(`Configuration must include a ${key} object.`);
  }
  if (!Array.isArray(cleaned.locations))
    throw new TypeError("Configuration must include a locations list.");
  if (!Array.isArray(cleaned.enrolled_iphones)) cleaned.enrolled_iphones = [];
  return cleaned;
}

export function relativeAge(value, now = Date.now()) {
  const time = Date.parse(value || "");
  if (!Number.isFinite(time)) return "No successful fetch";
  const minutes = Math.max(0, Math.floor((now - time) / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function eventTimestamp(event) {
  const published = Date.parse(event?.published_at || "");
  const updated = Date.parse(event?.updated_at || "");
  if (Number.isFinite(published) && Number.isFinite(updated)) {
    return updated >= published
      ? {
          timestamp: updated,
          value: new Date(updated).toISOString(),
          label: "Updated",
        }
      : {
          timestamp: published,
          value: new Date(published).toISOString(),
          label: "Published",
        };
  }
  if (Number.isFinite(updated))
    return {
      timestamp: updated,
      value: new Date(updated).toISOString(),
      label: "Updated",
    };
  if (Number.isFinite(published))
    return {
      timestamp: published,
      value: new Date(published).toISOString(),
      label: "Published",
    };
  const collected = Date.parse(event?.collected_at || "");
  return Number.isFinite(collected)
    ? {
        timestamp: collected,
        value: new Date(collected).toISOString(),
        label: "Collected",
      }
    : { timestamp: 0, value: null, label: "Time unknown" };
}

export function nwsAwarenessLifecycle(
  event,
  now = Date.now(),
  sources = [],
  sourceStates = null,
) {
  const sourceIsWeather =
    Array.isArray(sources) &&
    sources.some(
      (source) => source?.id === event?.source_id && source?.kind === "nws",
    );
  const carriesWeatherLifecycle =
    ["current", "expired", "not_in_latest_fetch"].includes(
      event?.awareness_lifecycle,
    ) &&
    event?.category === "weather" &&
    event?.official === true;
  if (!sourceIsWeather && !carriesWeatherLifecycle) return null;
  const expiry = Date.parse(event?.expires_at || "");
  if (Number.isFinite(expiry) && expiry <= now) return "expired";
  if (event.awareness_lifecycle === "expired") return "expired";
  if (event.awareness_lifecycle === "not_in_latest_fetch")
    return "not_in_latest_fetch";
  if (event.awareness_lifecycle === "current") {
    if (sourceStates) {
      const state = (Array.isArray(sourceStates) ? sourceStates : []).find(
        (source) => source.id === event.source_id,
      );
      const config = Array.isArray(sources)
        ? sources.find((source) => source.id === event.source_id)
        : undefined;
      if (
        !state ||
        sourceFreshness(
          { ...state, interval_minutes: config?.interval_minutes },
          now,
        ) !== "ok"
      )
        return "cached";
    }
    return "current";
  }
  return "unknown";
}

export function matchesEvent(
  event,
  { query = "", category = "all", status = "all", locationId = null } = {},
  locations = [],
) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (
    category !== "all" &&
    (event.category || "other") !== category &&
    !(
      category === "other" &&
      !["news", "weather", "earthquake"].includes(event.category)
    )
  )
    return false;
  if (status !== "all" && event.status !== status) return false;
  if (
    locationId &&
    !(
      Array.isArray(event.location_ids) &&
      event.location_ids.includes(locationId)
    )
  )
    return false;
  if (!normalizedQuery) return true;
  const placeNames = (
    Array.isArray(event.location_ids) ? event.location_ids : []
  )
    .map((id) => locations.find((place) => place.id === id)?.name || "")
    .join(" ");
  const haystack = [
    event.title,
    event.summary,
    event.source_name,
    event.category,
    placeNames,
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase();
  return haystack.includes(normalizedQuery);
}
