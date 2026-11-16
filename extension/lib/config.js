const HOSTS = {
  nws: "api.weather.gov",
  usgs: "earthquake.usgs.gov",
  rss: "feeds.bbci.co.uk",
};
const STATE_FIPS = Object.freeze({
  AL: "01",
  AK: "02",
  AZ: "04",
  AR: "05",
  CA: "06",
  CO: "08",
  CT: "09",
  DE: "10",
  DC: "11",
  FL: "12",
  GA: "13",
  HI: "15",
  ID: "16",
  IL: "17",
  IN: "18",
  IA: "19",
  KS: "20",
  KY: "21",
  LA: "22",
  ME: "23",
  MD: "24",
  MA: "25",
  MI: "26",
  MN: "27",
  MS: "28",
  MO: "29",
  MT: "30",
  NE: "31",
  NV: "32",
  NH: "33",
  NJ: "34",
  NM: "35",
  NY: "36",
  NC: "37",
  ND: "38",
  OH: "39",
  OK: "40",
  OR: "41",
  PA: "42",
  RI: "44",
  SC: "45",
  SD: "46",
  TN: "47",
  TX: "48",
  UT: "49",
  VT: "50",
  VA: "51",
  WA: "53",
  WV: "54",
  WI: "55",
  WY: "56",
  AS: "60",
  GU: "66",
  MP: "69",
  PR: "72",
  VI: "78",
});
const isObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const nonempty = (value) =>
  typeof value === "string" && value.trim().length > 0 && value.length <= 300;

export function safeUrl(value) {
  if (typeof value !== "string" || value.length > 4096) return null;
  try {
    const url = new URL(value);
    return (url.protocol === "http:" || url.protocol === "https:") &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function validateConfig(config) {
  if (
    !isObject(config) ||
    config.schema_version !== 1 ||
    config.live_actions_enabled !== false
  )
    throw new Error(
      "Configuration must have schema version 1 and live actions disabled.",
    );
  if (
    !isObject(config.room) ||
    !isObject(config.alarm_policy) ||
    !Array.isArray(config.enrolled_iphones) ||
    config.enrolled_iphones.length
  )
    throw new Error(
      "Invalid public configuration or private phone enrollment.",
    );
  if (!Array.isArray(config.locations) || config.locations.length > 100)
    throw new Error("Invalid locations.");
  const locationIds = new Set();
  for (const location of config.locations) {
    if (
      !isObject(location) ||
      !nonempty(location.id) ||
      !/^[a-z0-9_-]+$/i.test(location.id) ||
      locationIds.has(location.id) ||
      !nonempty(location.name) ||
      typeof location.watch_enabled !== "boolean" ||
      !nonempty(location.timezone)
    )
      throw new Error("Invalid or duplicate location.");
    if (
      location.household_exposure != null ||
      !Array.isArray(location.google_speaker_targets) ||
      location.google_speaker_targets.length ||
      !Array.isArray(location.horn_targets) ||
      location.horn_targets.length
    )
      throw new Error(
        "Private location and device data cannot be stored in the room.",
      );
    const area = location.awareness_area;
    const counties =
      area == null
        ? null
        : typeof area.county_fips === "string"
          ? [area.county_fips]
          : area.county_fips;
    if (
      area != null &&
      (!isObject(area) ||
        !Object.hasOwn(STATE_FIPS, area.state) ||
        !Array.isArray(counties) ||
        counties.length === 0 ||
        counties.length > 100 ||
        counties.some(
          (county) =>
            typeof county !== "string" ||
            !/^[0-9]{5}$/.test(county) ||
            !county.startsWith(STATE_FIPS[area.state]),
        )))
      throw new Error("Invalid location awareness area.");
    locationIds.add(location.id);
  }
  if (!Array.isArray(config.sources) || config.sources.length > 30)
    throw new Error("Invalid sources.");
  const ids = new Set();
  for (const source of config.sources) {
    if (
      !isObject(source) ||
      !nonempty(source.id) ||
      !/^[a-z0-9_-]+$/i.test(source.id) ||
      ids.has(source.id) ||
      !nonempty(source.name) ||
      typeof source.enabled !== "boolean" ||
      !Number.isInteger(source.interval_minutes) ||
      source.interval_minutes < 1 ||
      source.interval_minutes > 10080 ||
      !Object.hasOwn(HOSTS, source.kind)
    )
      throw new Error("Invalid or duplicate source.");
    const url = safeUrl(source.url);
    if (
      !url ||
      new URL(url).protocol !== "https:" ||
      new URL(url).host !== HOSTS[source.kind]
    )
      throw new Error("Source URL is outside the permitted provider.");
    ids.add(source.id);
  }
  const states = [
    ...new Set(
      config.locations
        .filter((l) => l.watch_enabled && l.awareness_area)
        .map((l) => l.awareness_area.state),
    ),
  ];
  // Explicitly whitelist public fields to avoid persisting or exporting private extras.
  return {
    schema_version: 1,
    artifact_status: "runtime_public_configuration",
    live_actions_enabled: false,
    room: {
      browser: String(config.room.browser || "Google Chrome").slice(0, 300),
      primary_dashboard: safeUrl(config.room.primary_dashboard),
      closing_room_stops_monitoring: false,
    },
    alarm_policy: {
      required_gates: [
        "credible_current_evidence",
        "concrete_watched_household_consequence",
        "time_relevant_preparation_or_protection",
      ],
      qualifying_events_allowed_overnight: true,
      first_phone_delivery: "all_enrolled_iphones",
      speaker_and_horn_delivery: "affected_locations_only",
      acknowledgement_scope: null,
      repeat_and_test_cadence: null,
    },
    enrolled_iphones: [],
    locations: config.locations.map((l) => ({
      id: l.id,
      name: l.name,
      watch_enabled: l.watch_enabled,
      timezone: l.timezone,
      awareness_area:
        l.awareness_area == null
          ? null
          : {
              state: l.awareness_area.state,
              county_fips: Array.isArray(l.awareness_area.county_fips)
                ? [...l.awareness_area.county_fips]
                : l.awareness_area.county_fips,
            },
      household_exposure: null,
      official_alert_enrollment: safeUrl(l.official_alert_enrollment),
      verified_event_ingestion: null,
      google_speaker_targets: [],
      horn_targets: [],
    })),
    sources: config.sources.map((s) => ({
      id: s.id,
      name: s.name,
      kind: s.kind,
      url:
        s.kind === "nws" && states.length
          ? `https://api.weather.gov/alerts/active?area=${states.join(",")}`
          : safeUrl(s.url),
      enabled: s.enabled,
      interval_minutes: s.interval_minutes,
    })),
  };
}
