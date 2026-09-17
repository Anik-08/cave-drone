"use client";

import { Gauge } from "lucide-react";
import type { SensorKey } from "@/types/sensor";
import type { StatusLevel } from "@/lib/gasAnalysis";
import { SENSOR_META } from "@/lib/config";
import { formatAge } from "@/lib/format";
import StatusPill from "@/components/StatusPill";

type Props = {
  sensorKey: SensorKey;
  value: number | null;
  status: StatusLevel | null;
  history: number[];
  lastUpdateAt: number | null;
  isStale: boolean;
  now: number;
};

function Sparkline({
  data,
  color,
  stale,
}: {
  data: number[];
  color: string;
  stale: boolean;
}) {
  const width = 240;
  const height = 44;

  if (data.length < 2) {
    return (
      <div
        className="flex h-11 w-full items-center justify-center font-mono text-[10px] uppercase tracking-wider text-faint"
        aria-hidden="true"
      >
        awaiting data
      </div>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - 3 - ((v - min) / range) * (height - 8);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-11 w-full"
      aria-hidden="true"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
        opacity={stale ? 0.35 : 1}
      />
    </svg>
  );
}

export default function GasSensorCard({
  sensorKey,
  value,
  status,
  history,
  lastUpdateAt,
  isStale,
  now,
}: Props) {
  const meta = SENSOR_META[sensorKey];

  return (
    <article
      aria-label={`${meta.name} sensor card`}
      className={`rounded-md border border-edge bg-panel p-4 transition-opacity ${
        isStale ? "opacity-70" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-foreground">
            {meta.name}
          </h3>
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-faint">
            {meta.description}
          </p>
        </div>
        <Gauge
          className="h-4 w-4 shrink-0 text-dim"
          style={{ color: meta.color }}
          aria-hidden="true"
        />
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="font-mono text-4xl font-semibold tabular-nums tracking-tight text-foreground">
          {value === null ? "—" : value}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-faint">
          RAW ADC
        </span>
      </div>

      <div className="mt-3">
        <Sparkline data={history} color={meta.color} stale={isStale} />
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-edge pt-3">
        <div>
          {status ? (
            <StatusPill status={status} />
          ) : (
            <span className="font-mono text-[11px] uppercase tracking-wider text-faint">
              —
            </span>
          )}
        </div>
        <span className="font-mono text-[11px] tabular-nums text-faint">
          {lastUpdateAt ? formatAge(lastUpdateAt, now) : "no data"}
        </span>
      </div>
    </article>
  );
}