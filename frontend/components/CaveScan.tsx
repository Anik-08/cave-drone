"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, ImagePlus, Loader2, ScanFace, Upload, XCircle } from "lucide-react";

type Detection = { box: number[]; confidence: number; label: string };
type PipelineResult = {
  brightness: number;
  was_dark: boolean;
  enhanced_image: string | null;
  detection: { present: boolean; count: number; detections: Detection[]; image: string };
};

type Stage = "idle" | "checking" | "enhancing" | "detecting" | "done";

export default function CaveScan() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [threshold, setThreshold] = useState(0.5);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  async function runPipeline(file?: File) {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setStage("checking");

    const form = new FormData();
    form.append("image", file);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/analyze-image?threshold=${threshold}`,
        { method: "POST", body: form }
      );
      const data: PipelineResult = await response.json();
      if (!response.ok) throw new Error((data as any).detail ?? "Could not analyze image.");

      // Reveal the pipeline stages in order, driven by the real result
      if (data.was_dark) {
        setStage("enhancing");
        await new Promise((r) => setTimeout(r, 700));
      }
      setStage("detecting");
      await new Promise((r) => setTimeout(r, 500));

      setResult(data);
      setStage("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the inference service.");
      setStage("done");
    }
  }

  const stageMessage: Record<Stage, string | null> = {
    idle: null,
    checking: "Checking image brightness...",
    enhancing: "Image is dark — enhancing...",
    detecting: result?.was_dark ? "Image enhanced. Now detecting humans..." : "Image looks fine. Detecting humans...",
    done: null,
  };

  return (
    <section aria-label="Cave scan pipeline" className="rounded-md border border-edge bg-panel p-4 md:p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <ScanFace className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
              Cave scan
            </h2>
          </div>
          <p className="font-mono text-[11px] text-faint">
            Upload a cave frame — dark images are enhanced automatically before detection.
          </p>
        </div>
        <span className="rounded-sm border border-accent/25 bg-accent/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-accent">
          Pipeline ready · v1
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        {/* Left: upload / original */}
        <div className="flex min-h-64 flex-col items-center justify-center rounded-sm border border-dashed border-edge bg-panel-raised/30 p-5 text-center">
          {preview ? (
            <img src={preview} alt="Uploaded cave frame" className="max-h-64 w-full rounded-sm object-contain" />
          ) : (
            <>
              <ImagePlus className="mb-3 h-8 w-8 text-faint" />
              <p className="font-mono text-xs text-dim">Select a cave image to begin</p>
              <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-faint">JPG · PNG · WEBP</p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => runPipeline(e.target.files?.[0])}
          />
          <button
            onClick={() => inputRef.current?.click()}
            className="mt-4 flex items-center gap-2 rounded-sm border border-edge bg-panel px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-accent hover:text-accent"
          >
            <Upload className="h-3.5 w-3.5" />
            {preview ? "Choose another frame" : "Choose image"}
          </button>
        </div>

        {/* Right: pipeline status + result */}
        <div className="flex flex-col rounded-sm border border-edge bg-panel-raised/30 p-4">
          <div className="flex items-center justify-between">
            <p className="font-mono text-[10px] uppercase tracking-wider text-faint">Pipeline output</p>
            {stage !== "idle" && stage !== "done" && <Loader2 className="h-4 w-4 animate-spin text-accent" />}
          </div>

          <div className="my-4 flex flex-1 items-center justify-center border-y border-edge py-8 text-center">
            {error ? (
              <div>
                <XCircle className="mx-auto mb-2 h-6 w-6 text-red-300" />
                <p className="font-mono text-xs text-red-300">{error}</p>
              </div>
            ) : stage !== "idle" && stage !== "done" ? (
              <p className="font-mono text-xs text-dim">{stageMessage[stage]}</p>
            ) : result ? (
              <div>
                {result.detection.present ? (
                  <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-emerald-300" />
                ) : (
                  <XCircle className="mx-auto mb-3 h-10 w-10 text-dim" />
                )}
                <p
                  className={`font-mono text-lg font-semibold uppercase tracking-wider ${
                    result.detection.present ? "text-emerald-300" : "text-dim"
                  }`}
                >
                  {result.detection.present ? "Human detected" : "No human detected"}
                </p>
                <p className="mt-2 font-mono text-[11px] text-faint">
                  {result.was_dark ? "Enhanced before detection" : "No enhancement needed"} · brightness{" "}
                  {result.brightness} · {result.detection.count} detection
                  {result.detection.count === 1 ? "" : "s"}
                </p>
                <img
                  src={result.detection.image}
                  alt="Detection result"
                  className="mx-auto mt-4 max-h-48 rounded-sm object-contain"
                />
              </div>
            ) : (
              <p className="font-mono text-xs text-faint">Results will appear here</p>
            )}
          </div>

          <label className="flex items-center justify-between gap-4 font-mono text-[10px] uppercase tracking-wider text-faint">
            Confidence threshold
            <input
              type="range"
              min="0.05"
              max="0.95"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="accent-accent"
            />
            <span className="w-8 text-right text-dim">{threshold.toFixed(2)}</span>
          </label>
        </div>
      </div>
    </section>
  );
}