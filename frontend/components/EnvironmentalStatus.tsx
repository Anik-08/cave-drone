"use client";

import { ShieldCheck, TriangleAlert } from "lucide-react";
import type { StatusLevel } from "@/lib/gasAnalysis";

type Props = {
  overall: StatusLevel | null;
  isStale: boolean;
};

const DESCRIPTIONS: Record<StatusLevel, string> = {
  NORMAL: "All sensor readings are within the configured prototype thresholds.",
  WARNING: "Elevated gas sensor indication detected.",
  HIGH: "High gas sensor indication detected. Proceed with caution.",
};

export default function EnvironmentalStatus({ overall, isStale }: Props) {
  const tone = (() => {
    if (!overall) return "offline";
    return overall === "HIGH" ? "high" : overall === "WARNING" ? "warning" : "normal";
  })();

  const styles = {
    normal: {
      box: "border-emerald-400/30 bg-emerald-400/5",
      iconBox: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
      value: "text-emerald-300",
    },
    warning: {
      box: "border-amber-400/40 bg-amber-400/5",
      iconBox: "border-amber-400/25 bg-amber-400/10 text-amber-300",
      value: "text-amber-300",
    },
    high: {
      box: "border-red-400/40 bg-red-400/5",
      iconBox: "border-red-400/25 bg-red-400/10 text-red-300",
      value: "text-red-300",
    },
    offline: {
      box: "border-edge bg-panel-raised/30",
      iconBox: "border-edge bg-panel-raised/60 text-dim",
      value: "text-dim",
    },
  } as const;

  const style = styles[tone];

  return (
    <section aria-label={`Environmental status: ${overall ?? "no data"}`}>
      <div className={`flex h-full flex-col rounded-md border p-4 md:p-5 ${style.box}`}>
        <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
          Environmental status
        </h2>

        <div className="mt-5 flex items-center gap-4">
          <span
            className={`flex h-11 w-11 items-center justify-center rounded-sm border ${style.iconBox}`}
          >
            {tone === "normal" ? (
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            ) : (
              <TriangleAlert className="h-5 w-5" aria-hidden="true" />
            )}
          </span>
          <div>
            <p className={`font-mono text-2xl font-semibold uppercase tracking-wider ${style.value}`}>
              {overall ?? "No data"}
            </p>
            <p className="font-mono text-[10px] uppercase tracking-wider text-faint">
              Overall condition based on 3 sensors
            </p>
          </div>
        </div>

        {overall && (
          <p className="mt-4 text-sm leading-relaxed text-dim">
            {DESCRIPTIONS[overall]}
            {isStale && (
              <span className="mt-1 block font-mono text-[11px] uppercase tracking-wider text-amber-300">
                Data stale — status may be outdated
              </span>
            )}
          </p>
        )}

        <div className="mt-auto border-t border-edge pt-3">
          <p className="font-mono text-[10px] uppercase tracking-wider text-faint">
            Logic: any HIGH → HIGH · any WARNING → WARNING · else NORMAL
          </p>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-faint">
            Based on prototype ADC thresholds — not validated gas concentrations
          </p>
        </div>
      </div>
    </section>
  );
}