import type { SensorKey } from "@/types/sensor";

export type CalibrationPoint = { adc: number; ppm: number };

export type CalibrationEntry = {
  sensor: SensorKey;
  method: "linear";
  points: CalibrationPoint[];
};

/**
 * Verified calibration data, ADC -> ppm.
 *
 * This is intentionally empty. The dashboard refuses to display a ppm value
 * until the sensors have been exposed to known gas concentrations and points
 * have been recorded here. Raw ADC values are always shown uncalibrated.
 */
export const CALIBRATION: CalibrationEntry[] = [];

export function estimatePpm(sensor: SensorKey, adc: number): number | null {
  const entry = CALIBRATION.find((c) => c.sensor === sensor);
  if (!entry || entry.method !== "linear") return null;

  const points = entry.points;
  if (points.length < 2) return null;

  // Order points by increasing ADC so interpolation is deterministic.
  const sorted = [...points].sort((a, b) => a.adc - b.adc);

  for (let i = 0; i < sorted.length - 1; i += 1) {
    const [a, b] = [sorted[i], sorted[i + 1]];
    if (adc >= a.adc && adc <= b.adc) {
      return interpolate(a, b, adc);
    }
  }

  // Clamp outside the calibrated window to the nearest segment.
  if (adc < sorted[0].adc) {
    return interpolate(sorted[0], sorted[1], adc);
  }
  const last = sorted[sorted.length - 1];
  return interpolate(sorted[sorted.length - 2], last, adc);
}

function interpolate(a: CalibrationPoint, b: CalibrationPoint, adc: number): number {
  const ratio = (adc - a.adc) / (b.adc - a.adc || 1);
  return Math.max(0, Math.round(a.ppm + ratio * (b.ppm - a.ppm)));
}

export function isCalibrated(sensor: SensorKey): boolean {
  return CALIBRATION.some((c) => c.sensor === sensor);
}