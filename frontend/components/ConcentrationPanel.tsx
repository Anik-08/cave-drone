"use client";

import { FlaskConical } from "lucide-react";
import type { SensorData, SensorKey } from "@/types/sensor";
import { estimatePpm, isCalibrated } from "@/lib/calibration";
import { SENSOR_META } from "@/lib/config";
import { SENSOR_KEYS } from "@/lib/baseline";

type Props = {
  latest: SensorData | null;
};

export default function ConcentrationPanel({ latest }: Props) {
  return (
    <section aria-label="Concentration estimation" className="rounded-md border border-edge bg-panel p-4 md:p-5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
          Concentration estimation
        </h2>
        <FlaskConical className="h-4 w-4 text-faint" aria-hidden="true" />
      </div>
      <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-faint">
        Requires sensor calibration
      </p>

      <ul className="mt-4 divide-y divide-edge">
        {SENSOR_KEYS.map((key: SensorKey) => {
          const meta = SENSOR_META[key];
          const value = latest ? latest[key] : null;
          const calibrated = isCalibrated(key);
          const ppm = value !== null ? estimatePpm(key, value) : null;

          return (
            <li key={key} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm text-foreground">
                    {meta.name} <span className="text-faint">· {meta.gas}</span>
                  </p>
                  <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-faint">
                    Raw ADC:{" "}
                    <span className="text-dim">{value === null ? "—" : value}</span>
                  </p>
                </div>
                <div className="text-right">
                  {!calibrated ? (
                    <span className="inline-flex items-center gap-1.5 rounded-sm border border-edge bg-panel-raised/60 px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-faint">
                      Not calibrated
                    </span>
                  ) : (
                    <div>
                      <p className="font-mono text-sm font-semibold tabular-nums text-accent">
                        ~{ppm} ppm
                      </p>
                      <p className="font-mono text-[9px] uppercase tracking-wider text-faint">
                        Estimated
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 rounded-sm border border-edge bg-panel-raised/40 p-3">
        <p className="font-mono text-[10px] uppercase tracking-wider text-faint">
          RAW ADC ≠ concentration
        </p>
        <p className="mt-1 text-xs leading-relaxed text-dim">
          A raw ADC value has never been converted to ppm here. Add verified
          calibration points (known gas → ADC) in{" "}
          <code className="font-mono text-[10px] text-faint">lib/calibration.ts</code>{" "}
          and estimated ppm will appear, clearly labelled ESTIMATED.
        </p>
      </div>
    </section>
  );
}