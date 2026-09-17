import type { SensorData, SensorKey } from "@/types/sensor";
import { SENSOR_THRESHOLDS, type ThresholdSet } from "./config";

export type StatusLevel = "NORMAL" | "WARNING" | "HIGH";

export type GasAnalysis = {
  mq2Status: StatusLevel;
  mq4Status: StatusLevel;
  mq7Status: StatusLevel;

  overallStatus: StatusLevel;

  methaneIndication: boolean;
  carbonMonoxideIndication: boolean;
  combustibleGasIndication: boolean;
};

export const STATUS_LEVELS: StatusLevel[] = ["NORMAL", "WARNING", "HIGH"];

export function statusForValue(
  value: number,
  thresholds: ThresholdSet
): StatusLevel {
  if (value >= thresholds.high) return "HIGH";
  if (value >= thresholds.warning) return "WARNING";
  return "NORMAL";
}

/**
 * Transparent overall-status logic:
 *   any HIGH   -> HIGH
 *   any WARNING-> WARNING
 *   otherwise  -> NORMAL
 */
export function computeOverall(statuses: StatusLevel[]): StatusLevel {
  if (statuses.includes("HIGH")) return "HIGH";
  if (statuses.includes("WARNING")) return "WARNING";
  return "NORMAL";
}

export function analyzeGas(data: SensorData): GasAnalysis {
  const mq2Status = statusForValue(data.mq2, SENSOR_THRESHOLDS.mq2);
  const mq4Status = statusForValue(data.mq4, SENSOR_THRESHOLDS.mq4);
  const mq7Status = statusForValue(data.mq7, SENSOR_THRESHOLDS.mq7);

  return {
    mq2Status,
    mq4Status,
    mq7Status,
    overallStatus: computeOverall([mq2Status, mq4Status, mq7Status]),
    methaneIndication: mq4Status !== "NORMAL",
    carbonMonoxideIndication: mq7Status !== "NORMAL",
    combustibleGasIndication: mq2Status !== "NORMAL",
  };
}

export function sensorStatus(analysis: GasAnalysis, key: SensorKey): StatusLevel {
  if (key === "mq2") return analysis.mq2Status;
  if (key === "mq4") return analysis.mq4Status;
  return analysis.mq7Status;
}