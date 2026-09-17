import type { SensorKey } from "@/types/sensor";

export type ThresholdSet = { warning: number; high: number };

/**
 * Prototype ADC thresholds used to classify readings as NORMAL / WARNING / HIGH.
 *
 * IMPORTANT: These values are placeholders selected only so the dashboard can
 * demonstrate its status logic. They are NOT scientifically validated gas
 * limits and must be recalibrated against a known gas source before the
 * dashboard is used for real operational decisions.
 */
export const SENSOR_THRESHOLDS: Record<SensorKey, ThresholdSet> = {
  mq2: { warning: 500, high: 700 },
  mq4: { warning: 200, high: 330 },
  mq7: { warning: 150, high: 220 },
};

export type SensorMeta = {
  name: string;
  gas: string;
  description: string;
  color: string;
};

export const SENSOR_META: Record<SensorKey, SensorMeta> = {
  mq2: {
    name: "MQ-2",
    gas: "Combustible / Smoke",
    description: "Combustible gas / smoke indication",
    color: "#38bdf8",
  },
  mq4: {
    name: "MQ-4",
    gas: "Methane (CH4)",
    description: "Methane (CH4) indication",
    color: "#a78bfa",
  },
  mq7: {
    name: "MQ-7",
    gas: "Carbon monoxide (CO)",
    description: "Carbon monoxide (CO) indication",
    color: "#fb923c",
  },
};

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/ws/sensors";

export const HISTORY_LIMIT = 100;

export const RECONNECT_DELAY_MS = 2500;

export const STALE_AFTER_MS = 5000;

export const BASELINE_DURATION_MS = 8000;

export const DEMO_INTERVAL_MS = 300;