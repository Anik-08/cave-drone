"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, ImagePlus, Loader2, ScanFace, Upload, XCircle } from "lucide-react";

type Detection = { box: number[]; confidence: number; label: string };
type Result = { present: boolean; count: number; detections: Detection[]; image: string };

export default function PersonDetection() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [threshold, setThreshold] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  async function analyze(file?: File) {
    if (!file) return;
    setPreview(URL.createObjectURL(file)); setResult(null); setError(null); setLoading(true);
    const form = new FormData(); form.append("image", file);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/detect-person?threshold=${threshold}`, { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not analyze image.");
      setResult(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not reach the inference service."); }
    finally { setLoading(false); }
  }

  return <section aria-label="Person detection" className="rounded-md border border-edge bg-panel p-4 md:p-5">
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div><div className="mb-2 flex items-center gap-2"><ScanFace className="h-4 w-4 text-accent" /><h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">Person detection</h2></div><p className="font-mono text-[11px] text-faint">Upload a cave frame for on-device Faster R-CNN analysis.</p></div>
      <span className="rounded-sm border border-accent/25 bg-accent/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-accent">Model ready · v1</span>
    </div>
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <div className="flex min-h-64 flex-col items-center justify-center rounded-sm border border-dashed border-edge bg-panel-raised/30 p-5 text-center">
        {preview ? <img src={result?.image ?? preview} alt="Selected cave frame" className="max-h-64 w-full rounded-sm object-contain" /> : <><ImagePlus className="mb-3 h-8 w-8 text-faint" /><p className="font-mono text-xs text-dim">Select a cave image to begin</p><p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-faint">JPG · PNG · WEBP</p></>}
        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={(e) => analyze(e.target.files?.[0])} />
        <button onClick={() => inputRef.current?.click()} className="mt-4 flex items-center gap-2 rounded-sm border border-edge bg-panel px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-accent hover:text-accent"><Upload className="h-3.5 w-3.5" />{preview ? "Choose another frame" : "Choose image"}</button>
      </div>
      <div className="flex flex-col rounded-sm border border-edge bg-panel-raised/30 p-4">
        <div className="flex items-center justify-between"><p className="font-mono text-[10px] uppercase tracking-wider text-faint">Detection output</p>{loading && <Loader2 className="h-4 w-4 animate-spin text-accent" />}</div>
        <div className="my-4 flex flex-1 items-center justify-center border-y border-edge py-8 text-center">{error ? <div><XCircle className="mx-auto mb-2 h-6 w-6 text-red-300" /><p className="font-mono text-xs text-red-300">{error}</p></div> : result ? <div>{result.present ? <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-emerald-300" /> : <XCircle className="mx-auto mb-3 h-10 w-10 text-dim" />}<p className={`font-mono text-lg font-semibold uppercase tracking-wider ${result.present ? "text-emerald-300" : "text-dim"}`}>{result.present ? "Human detected" : "No human detected"}</p><p className="mt-2 font-mono text-[11px] text-faint">{result.count} detection{result.count === 1 ? "" : "s"} · threshold {threshold.toFixed(2)}</p></div> : <p className="font-mono text-xs text-faint">Inference results will appear here</p>}</div>
        <label className="flex items-center justify-between gap-4 font-mono text-[10px] uppercase tracking-wider text-faint">Confidence threshold <input type="range" min="0.05" max="0.95" step="0.05" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} className="accent-accent" /><span className="w-8 text-right text-dim">{threshold.toFixed(2)}</span></label>
      </div>
    </div>
  </section>;
}
