export function pad(n: number): string {
  return n.toString().padStart(2, "0");
}

export function formatClock(ts: number): string {
  const d = new Date(ts);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function formatClockMs(ts: number): string {
  const d = new Date(ts);
  return `${formatClock(ts)}.${pad(Math.floor(d.getMilliseconds() / 10))}`;
}

export function formatAge(timestamp: number, now: number): string {
  const diff = Math.max(0, now - timestamp);
  if (diff < 1000) return `${diff} ms ago`;
  if (diff < 10_000) return `${(diff / 1000).toFixed(1)} sec ago`;
  if (diff < 60_000) return `${Math.round(diff / 1000)} sec ago`;
  return `${Math.round(diff / 60_000)} min ago`;
}

export function formatSignedPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}