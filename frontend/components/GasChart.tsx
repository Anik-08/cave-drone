"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SensorData } from "@/types/sensor";
import { SENSOR_META } from "@/lib/config";
import { formatClock, formatClockMs } from "@/lib/format";

type Props = {
  history: SensorData[];
};

export default function GasChart({ history }: Props) {
  const data = useMemo(
    () =>
      history.map((d) => ({
        time: d.timestamp,
        mq2: d.mq2,
        mq4: d.mq4,
        mq7: d.mq7,
      })),
    [history]
  );

  const tooltipStyle = {
    backgroundColor: "#0b1220",
    border: "1px solid #1e2a38",
    borderRadius: 6,
    fontSize: 12,
    color: "#e6edf3",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  };

  return (
    <section aria-label="Real-time sensor history chart" className="rounded-md border border-edge bg-panel p-4 md:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
          Real-time sensor history
        </h2>
        <span className="font-mono text-[11px] tabular-nums text-faint">
          {data.length} reading{data.length === 1 ? "" : "s"} · rolling window
        </span>
      </div>

      <div className="h-64 w-full">
        {data.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 rounded-sm border border-dashed border-edge bg-panel-raised/30 text-center">
            <p className="font-mono text-[11px] uppercase tracking-wider text-dim">
              No sensor data yet
            </p>
            <p className="max-w-xs font-mono text-[11px] text-faint">
              Start the FastAPI backend with the Arduino attached, or switch to Demo Mode.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2733" />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(v: number) => formatClock(v)}
                stroke="#3e4d5c"
                tick={{ fill: "#7b8894", fontSize: 10, fontFamily: "ui-monospace, monospace" }}
                minTickGap={40}
              />
              <YAxis
                domain={[0, "auto"]}
                tickFormatter={(v: number) => String(Math.round(v))}
                stroke="#3e4d5c"
                tick={{ fill: "#7b8894", fontSize: 10, fontFamily: "ui-monospace, monospace" }}
                allowDecimals={false}
                width={44}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                labelFormatter={(label) => formatClockMs(label as number)}
                formatter={(value) => [value, "RAW ADC"]}
                itemStyle={{ color: "#cbd5e1" }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}
                formatter={(value) => (
                  <span style={{ color: "#8b98a5" }}>{String(value).toUpperCase()}</span>
                )}
              />
              <Line
                type="monotone"
                dataKey="mq2"
                name="MQ-2"
                stroke={SENSOR_META.mq2.color}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="mq4"
                name="MQ-4"
                stroke={SENSOR_META.mq4.color}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="mq7"
                name="MQ-7"
                stroke={SENSOR_META.mq7.color}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-faint">
        Y axis — raw ADC value (uncalibrated) · status thresholds are prototype
      </p>
    </section>
  );
}