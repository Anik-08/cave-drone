import type { SensorBaseline, SensorData, SensorKey } from "@/types/sensor";

export const SENSOR_KEYS: SensorKey[] = ["mq2", "mq4", "mq7"];

export function computeBaseline(rows: SensorData[]): SensorBaseline {
  const result: SensorBaseline = { mq2: null, mq4: null, mq7: null };
  if (rows.length === 0) return result;

  for (const key of SENSOR_KEYS) {
    const sum = rows.reduce((acc, row) => acc + row[key], 0);
    result[key] = sum / rows.length;
  }

  return result;
}

export function relativeChange(
  current: number,
  baseline: number | null
): number | null {
  if (baseline === null || baseline === 0 || !Number.isFinite(baseline)) {
    return null;
  }
  return ((current - baseline) / baseline) * 100;
}