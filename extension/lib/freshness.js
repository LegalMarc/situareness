export function sourceFreshness(source, now = Date.now()) {
  if (source?.enabled === false) return "disabled";
  if (!source || source.status === "error") return "error";
  const stamp = Date.parse(source.last_success_at || "");
  if (!Number.isFinite(stamp)) return source.status === "ok" ? "stale" : "idle";
  const interval = Number(source.interval_minutes);
  const staleAfterMinutes =
    Number.isFinite(interval) && interval > 0 ? Math.max(2, interval * 2) : 30;
  const staleAfter = staleAfterMinutes * 60_000;
  return now - stamp > staleAfter ? "stale" : "ok";
}
