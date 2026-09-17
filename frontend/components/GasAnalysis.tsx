"use client";

import { CloudFog, Flame, Wind } from "lucide-react";
import type { GasAnalysis, StatusLevel } from "@/lib/gasAnalysis";
import { SENSOR_THRESHOLDS } from "@/lib/config";
import StatusPill from "@/components/StatusPill";

type Props = {
  analysis: GasAnalysis | null;
};

type Row = {
  label: string;
  sensorLabel: "mq2" | "mq4" | "mq7";
  status: StatusLevel | null;
  detected: boolean;
  detail: string;
  Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
};

export default function GasAnalysis({ analysis }: Props) {
  const rows: Row[] = [
    {
      label: "Combustible gas / smoke",
      sensorLabel: "mq2",
      status: analysis?.mq2Status ?? null,
      detected: analysis?.combustibleGasIndication ?? false,
      detail: "Combustible / smoke",
      Icon: Flame,
    },
    {
      label: "Methane (CH4)",
      sensorLabel: "mq4",
      status: analysis?.mq4Status ?? null,
      detected: analysis?.methaneIndication ?? false,
      detail: "Methane indication",
      Icon: CloudFog,
    },
    {
      label: "Carbon monoxide (CO)",
      sensorLabel: "mq7",
      status: analysis?.mq7Status ?? null,
      detected: analysis?.carbonMonoxideIndication ?? false,
      detail: "CO indication",
      Icon: Wind,
    },
  ];

  const thresholdLabel = (sensorLabel: Row["sensorLabel"]) => {
    const t = SENSOR_THRESHOLDS[sensorLabel];
    return `warn ≥${t.warning} · high ≥${t.high} ADC`;
  };

  return (
    <section aria-label="Gas analysis" className="rounded-md border border-edge bg-panel p-4 md:p-5">
      <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
        Gas analysis
      </h2>
      <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-faint">
        Detected gas indications
      </p>

      <ul className="mt-4 divide-y divide-edge">
        {rows.map((row) => {
          const Icon = row.Icon;
          return (
            <li
              key={row.sensorLabel}
              className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-sm border border-edge bg-panel-raised/60 text-dim">
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm text-foreground">{row.label}</p>
                  <p className="font-mono text-[10px] tabular-nums text-faint">
                    {row.detected && row.status
                      ? `${row.detail} detected`
                      : `No elevated ${row.detail.toLowerCase()}`}
                    {" · "}
                    {thresholdLabel(row.sensorLabel)}
                  </p>
                </div>
              </div>
              {row.status ? <StatusPill status={row.status} /> : null}
            </li>
          );
        })}
      </ul>

      <p className="mt-4 border-t border-edge pt-3 font-mono text-[10px] uppercase tracking-wider text-faint">
        Prototype thresholds — not validated gas limits
      </p>
    </section>
  );
}