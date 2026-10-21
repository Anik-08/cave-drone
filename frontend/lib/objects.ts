export function summarizeCounts(counts?: Record<string, number> | null): string {
  const entries = Object.entries(counts ?? {});
  if (entries.length === 0) return "No objects";
  return entries
    .sort((a, b) => b[1] - a[1])
    .map(([label, n]) => `${n} ${label}`)
    .join(" · ");
}