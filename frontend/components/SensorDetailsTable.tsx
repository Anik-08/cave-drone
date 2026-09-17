"use client";

import type { SensorBaseline, SensorData, SensorKey } from "@/types/sensor";
import type { GasAnalysis } from "@/lib/gasAnalysis";
import { sensorStatus } from "@/lib/gasAnalysis";
import { relativeChange, SENSOR_KEYS } from "@/lib/baseline";
import { SENSOR_META, SENSOR_THRESHOLDS } from "@/lib/config";
import { formatSignedPercent } from "@/lib/format";
import StatusPill from "@/components/StatusPill";

type Props = {
  latest: SensorData | null;
  baseline: SensorBaseline;
  baselineCollecting: boolean;
  baselineProgress: number;
  analysis: GasAnalysis | null;
  isStale: boolean;
};

export default function SensorDetailsTable({
  latest,
  baseline,
  baselineCollecting,
  baselineProgress,
  analysis,
  isStale,
}: Props) {
  return (
    <section aria-label="Sensor details table">
      <div className={`overflow-x-auto rounded-md border border-edge bg-panel ${isStale ? "opacity-70" : ""}`}>
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <caption className="border-b border-edge px-4 py-3 text-left font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
            Sensor details
          </caption>
          <thead>
            <tr className="border-b border-edge bg-panel-raised/40 font-mono text-[10px] uppercase tracking-wider text-faint">
              <th scope="col" className="px-4 py-2.5 text-left font-medium">
                Sensor
              </th>
              <th scope="col" className="px-4 py-2.5 text-left font-medium">
                Gas / Indication
              </th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">
                Raw value
              </th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">
                Baseline
              </th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">
                Change
              </th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">
                Threshold
              </th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {SENSOR_KEYS.map((key: SensorKey, index) => {
              const meta = SENSOR_META[key];
              const value = latest ? latest[key] : null;
              const base = baseline[key];
              const change = value !== null ? relativeChange(value, base) : null;
              const status = analysis ? sensorStatus(analysis, key) : null;
              const thresholds = SENSOR_THRESHOLDS[key];
              const isLast = index === SENSOR_KEYS.length - 1;

              return (
                <tr
                  key={key}
                  className={`border-b border-edge text-[13px] ${isLast ? "border-b-0" : ""}`}
                >
                  <th scope="row" className="px-4 py-3 text-left font-medium text-foreground">
                    {meta.name}
                  </th>
                  <td className="px-4 py-3 text-dim">{meta.gas}</td>
                  <td className="px-4 py-3 text-right text-foreground">
                    {value === null ? "—" : value}
                  </td>
                  <td className="px-4 py-3 text-right text-dim">
                    {base === null ? (
                      baselineCollecting ? (
                        <span title={`Capturing baseline ${Math.round(baselineProgress * 100)}%`}>
                          capture…{Math.round(baselineProgress * 100)}%
                        </span>
                      ) : (
                        "—"
                      )
                    ) : (
                      Math.round(base)
                    )}
                  </td>
                  <td
                    className={`px-4 py-3 text-right ${
                      change === null ? "text-faint" : change > 0 ? "text-amber-300" : "text-dim"
                    }`}
                  >
                    {formatSignedPercent(change)}
                  </td>
                  <td className="px-4 py-3 text-right text-[11px] text-faint">
                    {thresholds.warning} / {thresholds.high}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {status ? <StatusPill status={status} /> : <span className="text-faint">—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-faint">
        Baseline = mean of raw readings captured after startup · change = (value − baseline) / baseline × 100 ·
        thresholds are prototype
      </p>
    </section>
  );
}