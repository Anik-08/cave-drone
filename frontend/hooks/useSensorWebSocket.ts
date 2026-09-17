"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  DataSource,
  SensorBaseline,
  SensorData,
  SensorPayload,
  WebSocketStatus,
} from "@/types/sensor";
import { computeBaseline } from "@/lib/baseline";
import { createDemoReading } from "@/lib/demoSensors";
import {
  BASELINE_DURATION_MS,
  DEMO_INTERVAL_MS,
  HISTORY_LIMIT,
  RECONNECT_DELAY_MS,
  STALE_AFTER_MS,
  WS_URL,
} from "@/lib/config";

export type UseSensorWebSocketOptions = {
  mode?: DataSource;
  url?: string;
  historyLimit?: number;
  reconnectDelayMs?: number;
  staleAfterMs?: number;
  baselineEnabled?: boolean;
  baselineDurationMs?: number;
  demoIntervalMs?: number;
};

export type UseSensorWebSocketReturn = {
  latest: SensorData | null;
  history: SensorData[];
  status: WebSocketStatus;
  source: DataSource;
  reconnectAttempt: number;
  lastMessageAt: number | null;
  now: number;
  isStale: boolean;
  baseline: SensorBaseline;
  baselineCollecting: boolean;
  baselineProgress: number;
};

export function parseSensorPayload(raw: string): SensorPayload | null {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return null;
  }

  const { mq2, mq4, mq7 } = parsed;
  if (
    typeof mq2 !== "number" ||
    !Number.isFinite(mq2) ||
    typeof mq4 !== "number" ||
    !Number.isFinite(mq4) ||
    typeof mq7 !== "number" ||
    !Number.isFinite(mq7)
  ) {
    return null;
  }

  return { mq2: Math.round(mq2), mq4: Math.round(mq4), mq7: Math.round(mq7) };
}

export function useSensorWebSocket(
  options: UseSensorWebSocketOptions = {}
): UseSensorWebSocketReturn {
  const {
    mode = "live",
    url = WS_URL,
    historyLimit = HISTORY_LIMIT,
    reconnectDelayMs = RECONNECT_DELAY_MS,
    staleAfterMs = STALE_AFTER_MS,
    baselineEnabled = true,
    baselineDurationMs = BASELINE_DURATION_MS,
    demoIntervalMs = DEMO_INTERVAL_MS,
  } = options;

  const [latest, setLatest] = useState<SensorData | null>(null);
  const [history, setHistory] = useState<SensorData[]>([]);
  const [status, setStatus] = useState<WebSocketStatus>(() =>
    mode === "live" ? "connecting" : "connected"
  );
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [lastMessageAt, setLastMessageAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [baseline, setBaseline] = useState<SensorBaseline>({
    mq2: null,
    mq4: null,
    mq7: null,
  });
  const [baselineCollecting, setBaselineCollecting] = useState(baselineEnabled);
  const [baselineProgress, setBaselineProgress] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const demoIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestRef = useRef<SensorData | null>(null);
  const baselineBatchRef = useRef<SensorData[]>([]);
  const baselineStartedAtRef = useRef<number | null>(null);
  const baselineDoneRef = useRef(false);

  useEffect(() => {
    latestRef.current = latest;
  }, [latest]);

  const handleReading = useCallback(
    (data: SensorData) => {
      setLatest(data);
      setLastMessageAt(data.timestamp);
      setHistory((prev) => {
        if (prev.length >= historyLimit) {
          return [...prev.slice(prev.length - historyLimit + 1), data];
        }
        return [...prev, data];
      });

      if (baselineEnabled && !baselineDoneRef.current) {
        if (baselineStartedAtRef.current === null) {
          baselineStartedAtRef.current = data.timestamp;
        }
        baselineBatchRef.current = [...baselineBatchRef.current, data];
        const elapsed = data.timestamp - baselineStartedAtRef.current;
        setBaselineProgress(Math.min(1, elapsed / baselineDurationMs));

        if (elapsed >= baselineDurationMs || baselineBatchRef.current.length >= historyLimit) {
          baselineDoneRef.current = true;
          setBaseline(computeBaseline(baselineBatchRef.current));
          setBaselineCollecting(false);
        }
      }
    },
    [baselineDurationMs, baselineEnabled, historyLimit]
  );

  // Live mode: WebSocket with automatic reconnection.
  useEffect(() => {
    if (mode !== "live") return;

    let cancelled = false;

    const cleanUpSocket = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      setReconnectAttempt((attempt) => attempt + 1);
      reconnectTimerRef.current = setTimeout(connect, reconnectDelayMs);
    };

    const connect = () => {
      if (cancelled) return;

      setStatus("connecting");
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        if (cancelled) return;
        setStatus("connected");
        setReconnectAttempt(0);
      };

      socket.onmessage = (event) => {
        if (cancelled || typeof event.data !== "string") return;
        const payload = parseSensorPayload(event.data);
        if (!payload) return;
        handleReading({ ...payload, timestamp: Date.now() });
      };

      socket.onerror = () => {
        socket.close();
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("disconnected");
        scheduleReconnect();
      };
    };

    connect();

    return () => {
      cancelled = true;
      cleanUpSocket();
    };
  }, [handleReading, mode, reconnectDelayMs, url]);

  // Demo mode: generate simulated readings locally.
  useEffect(() => {
    if (mode !== "demo") return;
    if (demoIntervalRef.current) clearInterval(demoIntervalRef.current);

    demoIntervalRef.current = setInterval(() => {
      setStatus("connected");
      setReconnectAttempt(0);
      handleReading(createDemoReading(latestRef.current ?? undefined));
    }, demoIntervalMs);

    return () => {
      if (demoIntervalRef.current) {
        clearInterval(demoIntervalRef.current);
        demoIntervalRef.current = null;
      }
    };
  }, [demoIntervalMs, handleReading, mode]);

  // Clock tick used to refresh "time ago" labels and stale detection.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const isStale = lastMessageAt !== null && now - lastMessageAt > staleAfterMs;

  return {
    latest,
    history,
    status,
    source: mode,
    reconnectAttempt,
    lastMessageAt,
    now,
    isStale,
    baseline,
    baselineCollecting,
    baselineProgress,
  };
}