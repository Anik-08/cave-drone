// Where the dashboard connects to receive live ESP32-CAM frames.
// Override with NEXT_PUBLIC_CAMERA_WS_URL in frontend/.env.local if the backend runs elsewhere.
export const CAMERA_WS_URL =
  process.env.NEXT_PUBLIC_CAMERA_WS_URL ?? "ws://127.0.0.1:8000/ws/camera";

export const CAMERA_RECONNECT_MS = 2500;
export const CAMERA_STALE_AFTER_MS = 20000; // no frame for this long => "waiting"
export const CAMERA_HISTORY = 8;            // thumbnails kept in the strip