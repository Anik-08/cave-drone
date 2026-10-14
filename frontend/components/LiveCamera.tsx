"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Loader2, UserCheck, UserX, Wifi, WifiOff } from "lucide-react";
import {
  CAMERA_HISTORY,
  CAMERA_RECONNECT_MS,
  CAMERA_STALE_AFTER_MS,
  CAMERA_WS_URL,
} from "@/lib/cameraConfig";

type Detection = { box: number[]; confidence: number; label: string };

type LiveFrame = {
  frame_id: number;
  received_at: number;
  angle: string | null;
  brightness: number;
  was_dark: boolean;
  present: boolean;
  count: number;
  detections: Detection[];
  original: string;
  enhanced: string | null;
  annotated: string;
  process_ms: number;
};

type SocketState = "connecting" | "connected" | "disconnected";

export default function LiveCamera() {
  const [frame, setFrame] = useState<LiveFrame | null>(null);
  const [history, setHistory] = useState<LiveFrame[]>([]);
  const [socketState, setSocketState] = useState<SocketState>("connecting");
  const [totalFrames, setTotalFrames] = useState(0);
  const [personFrames, setPersonFrames] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [showOriginal, setShowOriginal] = useState(false);
  const lastFrameAt = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      setSocketState("connecting");
      socket = new WebSocket(CAMERA_WS_URL);

      socket.onopen = () => !cancelled && setSocketState("connected");

      socket.onmessage = (event) => {
        if (cancelled || typeof event.data !== "string") return;
        let data: LiveFrame;
        try {
          data = JSON.parse(event.data) as LiveFrame;
        } catch {
          return;
        }
        if (!data.annotated) return;
        lastFrameAt.current = Date.now();
        setFrame(data);
        setHistory((prev) => [data, ...prev].slice(0, CAMERA_HISTORY));
        setTotalFrames((n) => n + 1);
        if (data.present) setPersonFrames((n) => n + 1);
      };

      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (cancelled) return;
        setSocketState("disconnected");
        timer = setTimeout(connect, CAMERA_RECONNECT_MS);
      };
    };

    connect();
    const tick = setInterval(() => setNow(Date.now()), 1000);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      clearInterval(tick);
      socket?.close();
    };
  }, []);

  const ageMs = lastFrameAt.current ? now - lastFrameAt.current : null;
  const isLive = socketState === "connected" && ageMs !== null && ageMs < CAMERA_STALE_AFTER_MS;

  const badge =
    socketState !== "connected"
      ? { text: "Backend offline", cls: "border-red-400/30 bg-red-400/10 text-red-300", icon: WifiOff }
      : isLive
      ? { text: "Live", cls: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300", icon: Wifi }
      : { text: "Waiting for camera", cls: "border-amber-400/30 bg-amber-400/10 text-amber-300", icon: Loader2 };
  const BadgeIcon = badge.icon;

  return (
    <section aria-label="Live camera feed" className="rounded-md border border-edge bg-panel p-4 md:p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Camera className="h-4 w-4 text-accent" />
            <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-dim">
              Live camera · ESP32-CAM
            </h2>
          </div>
          <p className="font-mono text-[11px] text-faint">
            Every frame the drone captures is brightened if dark, then scanned for people automatically.
          </p>
        </div>
        <span
          className={`flex items-center gap-1.5 rounded-sm border px-2 py-1 font-mono text-[10px] uppercase tracking-wider ${badge.cls}`}
        >
          <BadgeIcon className={`h-3 w-3 ${badge.text === "Waiting for camera" ? "animate-spin" : ""}`} />
          {badge.text}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        {/* Main frame */}
        <div className="relative flex min-h-64 items-center justify-center rounded-sm border border-edge bg-panel-raised/30 p-2">
          {frame ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={showOriginal ? frame.original : frame.annotated}
                alt="Latest drone frame"
                className="max-h-96 w-full rounded-sm object-contain"
              />
              {frame.present && !showOriginal && (
                <span className="absolute left-4 top-4 rounded-sm border border-emerald-400/40 bg-emerald-400/20 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-emerald-200">
                  Human detected
                </span>
              )}
            </>
          ) : (
            <div className="text-center">
              <Camera className="mx-auto mb-3 h-8 w-8 text-faint" />
              <p className="font-mono text-xs text-dim">No frames yet</p>
              <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-faint">
                Power the drone — frames appear here automatically
              </p>
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="flex flex-col gap-3 rounded-sm border border-edge bg-panel-raised/30 p-4">
          <div className="flex items-center gap-3">
            {frame?.present ? (
              <UserCheck className="h-8 w-8 text-emerald-300" />
            ) : (
              <UserX className="h-8 w-8 text-dim" />
            )}
            <div>
              <p
                className={`font-mono text-sm font-semibold uppercase tracking-wider ${
                  frame?.present ? "text-emerald-300" : "text-dim"
                }`}
              >
                {frame ? (frame.present ? "Human detected" : "No human") : "—"}
              </p>
              <p className="font-mono text-[10px] text-faint">
                {frame ? `${frame.count} detection${frame.count === 1 ? "" : "s"}` : "waiting"}
              </p>
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-x-3 gap-y-2 font-mono text-[10px] uppercase tracking-wider">
            <dt className="text-faint">Frame</dt>
            <dd className="text-right text-dim">{frame ? `#${frame.frame_id}` : "—"}</dd>
            <dt className="text-faint">Servo angle</dt>
            <dd className="text-right text-dim">{frame?.angle ? `${frame.angle}°` : "—"}</dd>
            <dt className="text-faint">Brightness</dt>
            <dd className="text-right text-dim">
              {frame ? `${frame.brightness}${frame.was_dark ? " (enhanced)" : ""}` : "—"}
            </dd>
            <dt className="text-faint">Processing</dt>
            <dd className="text-right text-dim">{frame ? `${frame.process_ms} ms` : "—"}</dd>
            <dt className="text-faint">Last frame</dt>
            <dd className="text-right text-dim">{ageMs !== null ? `${Math.round(ageMs / 1000)}s ago` : "—"}</dd>
            <dt className="text-faint">Total / with people</dt>
            <dd className="text-right text-dim">
              {totalFrames} / {personFrames}
            </dd>
          </dl>

          <button
            onClick={() => setShowOriginal((v) => !v)}
            disabled={!frame}
            className="mt-auto rounded-sm border border-edge bg-panel px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-accent hover:text-accent disabled:opacity-40"
          >
            {showOriginal ? "Show detection overlay" : "Show raw camera frame"}
          </button>
        </div>
      </div>

      {history.length > 1 && (
        <div className="mt-4">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-faint">Recent frames</p>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {history.map((h) => (
              <button
                key={h.frame_id}
                onClick={() => setFrame(h)}
                className={`relative shrink-0 overflow-hidden rounded-sm border ${
                  h.present ? "border-emerald-400/60" : "border-edge"
                } ${frame?.frame_id === h.frame_id ? "ring-1 ring-accent" : ""}`}
                title={`Frame #${h.frame_id}${h.angle ? ` · ${h.angle}°` : ""}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={h.annotated} alt={`Frame ${h.frame_id}`} className="h-16 w-24 object-cover" />
                {h.present && (
                  <span className="absolute bottom-0 left-0 right-0 bg-emerald-500/70 text-center font-mono text-[9px] uppercase text-white">
                    person
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}