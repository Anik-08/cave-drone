import type { StatusLevel } from "@/lib/gasAnalysis";

const STATUS_STYLES: Record<
  StatusLevel,
  { dot: string; wrapper: string }
> = {
  NORMAL: {
    dot: "bg-emerald-400",
    wrapper: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
  },
  WARNING: {
    dot: "bg-amber-400",
    wrapper: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  },
  HIGH: {
    dot: "bg-red-400",
    wrapper: "border-red-400/25 bg-red-400/10 text-red-300",
  },
};

export default function StatusPill({ status }: { status: StatusLevel }) {
  const style = STATUS_STYLES[status];
  return (
    <span
      aria-label={`Status: ${status}`}
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider ${style.wrapper}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${style.dot}`} />
      {status}
    </span>
  );
}