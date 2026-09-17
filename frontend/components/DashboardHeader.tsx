"use client";

import { Cpu, FlaskConical, Radio, WifiOff } from "lucide-react";
import type { DataSource, WebSocketStatus } from "@/types/sensor";
import { formatClock } from "@/lib/format";

type Props = {
  source: DataSource;
  status: WebSocketStatus;
  isStale: boolean;
  lastMessageAt: number | null;
  reconnectAttempt: number;
  onModeChange: (mode: DataSource) => void;
};

function SourceBadge({ source }: { source: DataSource }) {
  if (source === "demo") {
    return (
      <span
        aria-label="Demo mode: simulated data"
        className="inline-flex items-center gap-1.5 rounded-sm border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-amber-300"
      >
        <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
        DEMO · SIMULATED
      </span>
    );
  }
  return (
    <span
      aria-label="Live Arduino data"
      className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-400/25 bg-emerald-400/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-emerald-300"
    >
      <span className="relative flex h-2 w-2" aria-hidden="true">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-40" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
      </span>
      LIVE ARDUINO DATA
    </span>
  );
}

function ConnectionBadge({ status, isStale }: { status: WebSocketStatus; isStale: boolean }) {
  if (isStale) {
    return (
      <span
        aria-label="Data stale"
        className="inline-flex items-center gap-1.5 rounded-sm border border-red-400/25 bg-red-400/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-red-300"
      >
        <WifiOff className="h-3.5 w-3.5" aria-hidden="true" />
        DATA STALE
      </span>
    );
  }
  switch (status) {
    case "connected":
      return (
        <span
          aria-label="Connected"
          className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-400/25 bg-emerald-400/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-emerald-300"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
          LIVE DATA
        </span>
      );
    case "connecting":
      return (
        <span
          aria-label="Connecting"
          className="inline-flex items-center gap-1.5 rounded-sm border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-amber-300"
        >
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" aria-hidden="true" />
          CONNECTING
        </span>
      );
    default:
      return (
        <span
          aria-label="Disconnected"
          className="inline-flex items-center gap-1.5 rounded-sm border border-red-400/25 bg-red-400/10 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-red-300"
        >
          <WifiOff className="h-3.5 w-3.5" aria-hidden="true" />
          DISCONNECTED
        </span>
      );
  }
}

function ModeButton({
  value,
  label,
  active,
  onSelect,
}: {
  value: DataSource;
  label: string;
  active: boolean;
  onSelect: (mode: DataSource) => void;
}) {
  const Icon = value === "live" ? Radio : Cpu;
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      aria-pressed={active}
      aria-label={label}
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2.5 py-1 font-mono text-[11px] font-medium uppercase tracking-wider transition-colors ${
        active
          ? "border-accent/50 bg-accent/15 text-accent"
          : "border-edge bg-panel-raised/60 text-dim hover:text-foreground"
      }`}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {value === "live" ? "Live" : "Demo"}
    </button>
  );
}

export default function DashboardHeader({
  source,
  status,
  isStale,
  lastMessageAt,
  reconnectAttempt,
  onModeChange,
}: Props) {
  return (
    <header className="border-b border-edge bg-panel/70 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4 py-5 md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-faint">
              Underground Exploration Ground Station
            </p>
            <h1 className="mt-1.5 text-xl font-semibold tracking-tight text-foreground md:text-2xl">
              <span className="text-accent">DRONE</span> ENVIRONMENT MONITOR
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <SourceBadge source={source} />
            <ConnectionBadge status={status} isStale={isStale} />
            {status === "disconnected" && (
              <span className="hidden font-mono text-[11px] text-faint lg:inline">
                retry #{reconnectAttempt}
              </span>
            )}
            <div
              aria-label="Last update time"
              className="rounded-sm border border-edge bg-panel-raised/60 px-2.5 py-1 font-mono text-[11px] tabular-nums text-dim"
            >
              LAST UPDATE{" "}
              <span className="text-foreground">
                {lastMessageAt ? formatClock(lastMessageAt) : "--:--:--"}
              </span>
            </div>
            <div className="flex overflow-hidden rounded-sm border border-edge">
              <ModeButton value="live" label="Live Arduino data" active={source === "live"} onSelect={onModeChange} />
              <ModeButton value="demo" label="Demo simulated data" active={source === "demo"} onSelect={onModeChange} />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}