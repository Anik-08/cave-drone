"use client";

import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clapperboard, Loader2, Upload, XCircle } from "lucide-react";

type FrameResult = {
  timestamp: number | null;
  brightness: number;
  was_dark: boolean;
  detection: { present: boolean; count: number; detections: unknown[]; image: string };
};

type VideoResult = {
  duration_seconds: number;
  fps: number;
  frames_processed: number;
  any_person_detected: boolean;
  total_detections: number;
  frames: FrameResult[];
};

export default function VideoScan() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VideoResult | null>(null);

  async function analyzeVideo(file?: File) {
    if (!file) return;
    setFileName(file.name);
    setResult(null);
    setError(null);
    setLoading(true);

    const form = new FormData();
    form.append("video", file);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/analyze-video`,
        { method: "POST", body: form }
      );
      const data: VideoResult = await response.json();
      if (!response.ok) throw new Error((data as { detail?: string }).detail ?? "Could not analyze video.");
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the inference service.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-label="Video scan" className="rounded-md border border-edge bg-panel p-4 md:p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Clapperboard className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
              Video scan
            </h2>
          </div>
          <p className="font-mono text-[11px] text-faint">
            Upload footage — frames are sampled roughly once per second, enhanced if dark, and checked for people.
          </p>
        </div>
        <span className="rounded-sm border border-accent/25 bg-accent/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-accent">
          Beta · sampled frames
        </span>
      </div>

      <div className="flex flex-col items-center justify-center rounded-sm border border-dashed border-edge bg-panel-raised/30 p-6 text-center">
        {loading ? (
          <>
            <Loader2 className="mb-3 h-8 w-8 animate-spin text-accent" />
            <p className="font-mono text-xs text-dim">Processing {fileName}...</p>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-faint">
              This can take a while for longer clips
            </p>
          </>
        ) : (
          <>
            <Upload className="mb-3 h-8 w-8 text-faint" />
            <p className="font-mono text-xs text-dim">{fileName ?? "Select a video file to analyze"}</p>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-faint">MP4 · MOV · AVI</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => analyzeVideo(e.target.files?.[0])}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={loading}
          className="mt-4 flex items-center gap-2 rounded-sm border border-edge bg-panel px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-accent hover:text-accent disabled:opacity-50"
        >
          <Upload className="h-3.5 w-3.5" />
          {fileName ? "Choose another video" : "Choose video"}
        </button>
      </div>

      {error && (
        <div className="mt-4 flex items-center gap-2 rounded-sm border border-red-300/30 bg-red-300/5 px-3 py-2">
          <XCircle className="h-4 w-4 text-red-300" />
          <p className="font-mono text-xs text-red-300">{error}</p>
        </div>
      )}

      {result && (
        <div className="mt-4">
          <div
            className={`mb-4 flex flex-wrap items-center gap-3 rounded-sm border px-3 py-2 ${
              result.any_person_detected ? "border-emerald-300/30 bg-emerald-300/5" : "border-edge bg-panel-raised/30"
            }`}
          >
            {result.any_person_detected ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-300" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-faint" />
            )}
            <p
              className={`font-mono text-sm font-semibold uppercase tracking-wider ${
                result.any_person_detected ? "text-emerald-300" : "text-dim"
              }`}
            >
              {result.any_person_detected
                ? `Person detected in ${result.total_detections} sampled frame${result.total_detections === 1 ? "" : "s"}`
                : "No person detected in sampled frames"}
            </p>
            <p className="ml-auto font-mono text-[10px] uppercase tracking-wider text-faint">
              {result.frames_processed} frames · {result.duration_seconds}s clip
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {result.frames.map((frame, index) => (
              <div
                key={index}
                className={`overflow-hidden rounded-sm border ${
                  frame.detection.present ? "border-emerald-300/50" : "border-edge"
                }`}
              >
                <img src={frame.detection.image} alt={`Frame at ${frame.timestamp}s`} className="w-full object-cover" />
                <div className="flex items-center justify-between px-2 py-1">
                  <span className="font-mono text-[10px] text-faint">{frame.timestamp}s</span>
                  {frame.detection.present ? (
                    <span className="font-mono text-[10px] uppercase text-emerald-300">Person</span>
                  ) : (
                    <span className="font-mono text-[10px] uppercase text-faint">Clear</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}