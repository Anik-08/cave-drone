import type { SensorData } from "@/types/sensor";

function walk(
  prev: number,
  min: number,
  max: number,
  step: number,
  spikeEvery?: number
): number {
  const delta = (Math.random() - 0.5) * step * 2;
  let next = prev + delta;
  if (spikeEvery && Math.random() < 1 / spikeEvery) {
    next += step * (3 + Math.random() * 4);
  }
  return Math.min(max, Math.max(min, Math.round(next)));
}

/**
 * Produces simulated sensor readings for Demo Mode.
 *
 * The values are a random walk around plausible Arduino ADC levels, with
 * occasional transients so the status logic can be observed. They are
 * explicitly NOT real readings and are always surfaced in the UI as
 * simulated data.
 */
export function createDemoReading(prev?: SensorData): SensorData {
  const timestamp = Date.now();
  if (!prev) {
    return { mq2: 400, mq4: 150, mq7: 120, timestamp };
  }
  return {
    mq2: walk(prev.mq2, 260, 520, 8, 120),
    mq4: walk(prev.mq4, 105, 245, 6, 90),
    mq7: walk(prev.mq7, 92, 265, 7, 14),
    timestamp,
  };
}