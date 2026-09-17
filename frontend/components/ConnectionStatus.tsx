"use client";

import { Cpu, Server, Wifi, WifiOff, Timer } from "lucide-react";
import type { DataSource, WebSocketStatus } from "@/types/sensor";
import { formatAge } from "@/lib/format";

type Props = {
  source: DataSource;
  status: WebSocketStatus;
  isStale: boolean;
  lastMessageAt: number | null;
  reconnectAttempt: number;
  now: number;
};

function StatusRow({
  icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "ok" | "warn" | "error" | "neutral";
}) {
  const colors: Record<string, string> = {
    ok: "text-emerald-300",
    warn: "text-amber-300",
    error: "text-red-300",
    neutral: "text-foreground",
  };
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-edge bg-panel-raised/60 text-dim">
        {icon}
      </span>
      <div>
        <p className="font-mono text-[10px] uppercase tracking-wider text-faint">{label}</p>
        <p className={`font-mono text-sm tabular-nums ${colors[tone]}`}>{value}</p>
      </div>
    </div>
  );
}

export default function ConnectionStatus({
  source,
  status,
  isStale,
  lastMessageAt,
  reconnectAttempt,
  now,
}: Props) {
  const isDemo = source === "demo";
  const websocketConnected = status === "connected" && !isStale;
  const arduinoOk = !isDemo && websocketConnected && lastMessageAt !== null;
  const hasData = lastMessageAt !== null;

  const websocketValue = isDemo
    ? "Simulated (DEMO)"
    : status === "connected"
      ? "Connected"
      : status === "connecting"
        ? "Connecting"
        : "Disconnected";

  const websocketIcon =
    isDemo || status === "connected" ? (
      <Wifi className="h-4 w-4" aria-hidden="true" />
    ) : (
      <WifiOff className="h-4 w-4" aria-hidden="true" />
    );

  const arduinoValue = isDemo
    ? "Simulated (DEMO)"
    : arduinoOk
      ? "Connected"
      : hasData
        ? "No data yet"
        : "Waiting for Arduino";

  return (
    <section aria-label="Connection status">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-4 rounded-md border border-edge bg-panel px-5 py-4">
        <StatusRow
          icon={<Cpu className="h-4 w-4" aria-hidden="true" />}
          label="Arduino (USB)"
          value={arduinoValue}
          tone={isDemo ? "warn" : arduinoOk ? "ok" : "neutral"}
        />
        <StatusRow
          icon={websocketIcon}
          label="WebSocket"
          value={websocketValue}
          tone={isDemo ? "warn" : status === "connected" ? "ok" : status === "connecting" ? "warn" : "error"}
        />
        <StatusRow
          icon={<Server className="h-4 w-4" aria-hidden="true" />}
          label="Backend"
          value={isDemo ? "Local demo" : status === "connected" ? "Reachable" : "Unreachable"}
          tone={isDemo ? "warn" : status === "connected" ? "ok" : "neutral"}
        />
        <StatusRow
          icon={<Timer className="h-4 w-4" aria-hidden="true" />}
          label="Last update"
          value={lastMessageAt ? `${formatAge(lastMessageAt, now)}` : "—"}
          tone={isStale ? "warn" : "neutral"}
        />

        {status === "disconnected" && !isDemo && (
          <div className="ml-auto flex items-center gap-2 rounded-sm border border-red-400/25 bg-red-400/10 px-3 py-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" aria-hidden="true" />
            <p className="font-mono text-[11px] uppercase tracking-wider text-red-300">
              Reconnecting · attempt {reconnectAttempt}
            </p>
          </div>
        )}

        {isStale && !isDemo && (
          <div className="ml-auto flex items-center gap-2 rounded-sm border border-amber-400/25 bg-amber-400/10 px-3 py-2">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" aria-hidden="true" />
            <p className="font-mono text-[11px] uppercase tracking-wider text-amber-300">
              Data stale — readings are not current
            </p>
          </div>
        )}
      </div>
    </section>
  );
}