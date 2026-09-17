export type SensorKey = "mq2" | "mq4" | "mq7";

export type SensorPayload = {
  mq2: number;
  mq4: number;
  mq7: number;
};

export type SensorData = SensorPayload & {
  timestamp: number;
};

export type WebSocketStatus = "connecting" | "connected" | "disconnected";

export type DataSource = "live" | "demo";

export type SensorBaseline = Record<SensorKey, number | null>;