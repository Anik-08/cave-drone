# import json
# import asyncio
# import base64
# import io
# import os
# import tempfile
# from functools import lru_cache

# try:
#     import serial
# except ImportError:
#     serial = None

# import re
# import csv
# import time
# import threading
# from datetime import datetime
# from contextlib import asynccontextmanager
# from http.server import BaseHTTPRequestHandler, HTTPServer

# from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
# from fastapi.middleware.cors import CORSMiddleware

# @asynccontextmanager
# async def lifespan(_app):
#     # Runs once when uvicorn starts: remember the event loop, start the live worker
#     # and start the ESP32 receiver (port 5000) in a background thread.
#     global main_loop
#     main_loop = asyncio.get_running_loop()
#     ensure_live_worker()
#     start_esp_receiver()
#     yield
#     stop_esp_receiver()


# app = FastAPI(lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# MODEL_PATH = os.path.join(os.path.dirname(__file__), "fasterrcnn_person_best.pth")
# DCE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "dce_model.keras")
# ENHANCE_IMAGE_SIZE = 256
# DARKNESS_THRESHOLD = 50
# VIDEO_SAMPLE_INTERVAL_SECONDS = 1.0
# MAX_VIDEO_FRAMES = 30
# VIDEO_OUTPUT_MAX_WIDTH = 480

# @app.post("/api/analyze-video")
# async def analyze_video_pipeline(video: UploadFile = File(...), threshold: float = 0.5):
#     if not video.content_type or not video.content_type.startswith("video/"):
#         raise HTTPException(status_code=400, detail="Please upload a valid video file.")
#     if not 0.05 <= threshold <= 0.99:
#         raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

#     tmp_path = None
#     try:
#         import cv2
#         from PIL import Image

#         raw = await video.read()
#         suffix = os.path.splitext(video.filename or "")[1] or ".mp4"
#         fd, tmp_path = tempfile.mkstemp(suffix=suffix)
#         with os.fdopen(fd, "wb") as f:
#             f.write(raw)

#         capture = cv2.VideoCapture(tmp_path)
#         fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
#         total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
#         duration = total_frames / fps if fps else 0.0
#         frame_step = max(1, round(fps * VIDEO_SAMPLE_INTERVAL_SECONDS))

#         results = []
#         frame_index = 0
#         processed = 0

#         while processed < MAX_VIDEO_FRAMES and frame_index < total_frames:
#             capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
#             success, frame_bgr = capture.read()
#             if not success:
#                 break

#             pil_frame = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

#             brightness = compute_brightness(pil_frame)
#             was_dark = brightness < DARKNESS_THRESHOLD

#             working_frame = await run_enhancement(pil_frame) if was_dark else pil_frame
#             detection_summary, annotated = await run_detection(working_frame, threshold)

#             if annotated.width > VIDEO_OUTPUT_MAX_WIDTH:
#                 ratio = VIDEO_OUTPUT_MAX_WIDTH / annotated.width
#                 annotated = annotated.resize((VIDEO_OUTPUT_MAX_WIDTH, round(annotated.height * ratio)))

#             buf = io.BytesIO()
#             annotated.save(buf, format="JPEG", quality=80)
#             image_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

#             results.append({
#                 "timestamp": round(frame_index / fps, 2) if fps else None,
#                 "brightness": round(brightness, 1),
#                 "was_dark": was_dark,
#                 "detection": {**detection_summary, "image": image_b64},
#             })

#             processed += 1
#             frame_index += frame_step

#         capture.release()

#         return {
#             "duration_seconds": round(duration, 2),
#             "fps": round(fps, 2),
#             "frames_processed": processed,
#             "any_person_detected": any(r["detection"]["present"] for r in results),
#             "total_detections": sum(r["detection"]["count"] for r in results),
#             "frames": results,
#         }
#     except HTTPException:
#         raise
#     except Exception as error:
#         raise HTTPException(status_code=500, detail=f"Video analysis failed: {error}") from error
#     finally:
#         if tmp_path and os.path.exists(tmp_path):
#             os.remove(tmp_path)

# def compute_brightness(pil_image):
#     import numpy as np
#     gray = pil_image.convert("L")
#     return float(np.array(gray).mean())


# @lru_cache(maxsize=1)
# def get_enhance_model():
#     """Load the low-light enhancement (DCE) model once, on first request."""
#     from tensorflow import keras
#     return keras.models.load_model(DCE_MODEL_PATH)


# async def run_enhancement(pil_image):
#     """Plain helper — NOT an endpoint. Used by both /api/enhance-image and /api/analyze-image."""
#     import numpy as np
#     import tensorflow as tf
#     from PIL import Image

#     resized = pil_image.resize((ENHANCE_IMAGE_SIZE, ENHANCE_IMAGE_SIZE))
#     arr = np.array(resized).astype("float32") / 255.0
#     arr = np.expand_dims(arr, axis=0)

#     model = await asyncio.to_thread(get_enhance_model)
#     dce_output = await asyncio.to_thread(model, arr, training=False)

#     x = arr
#     for i in range(0, 3 * 8, 3):
#         r = dce_output[:, :, :, i:i + 3]
#         x = x + r * (tf.square(x) - x)

#     enhanced = tf.clip_by_value(x[0], 0.0, 1.0)
#     enhanced = tf.cast(enhanced * 255, tf.uint8).numpy()
#     return Image.fromarray(enhanced).resize(pil_image.size)


# @app.post("/api/enhance-image")
# async def enhance_image_endpoint(image: UploadFile = File(...)):
#     if not image.content_type or not image.content_type.startswith("image/"):
#         raise HTTPException(status_code=400, detail="Please upload a valid image file.")

#     try:
#         from PIL import Image

#         raw = await image.read()
#         original = Image.open(io.BytesIO(raw)).convert("RGB")
#         enhanced_image = await run_enhancement(original)

#         output = io.BytesIO()
#         enhanced_image.save(output, format="JPEG", quality=92)
#         return {
#             "image": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
#         }
#     except Exception as error:
#         raise HTTPException(status_code=500, detail=f"Enhancement failed: {error}") from error


# try:
#     arduino = serial.Serial(port="COM7", baudrate=9600, timeout=1) if serial else None
# except Exception as error:
#     arduino = None
#     print(f"Arduino unavailable; sensor WebSocket will remain idle: {error}")

# # Give Arduino time to reset after opening COM port
# print("Opening Arduino...")


# def read_sensor_data():

#     if arduino is None:
#         return None

#     while True:

#         line = arduino.readline()

#         if not line:
#             continue

#         try:
#             text = line.decode("utf-8", errors="ignore").strip()

#             print("RAW:", repr(text))

#             # Find JSON inside the received line
#             start = text.find("{")
#             end = text.rfind("}")

#             if start == -1 or end == -1:
#                 continue

#             json_text = text[start:end + 1]

#             data = json.loads(json_text)

#             # Make sure required values exist
#             if "mq2" not in data:
#                 continue

#             if "mq4" not in data:
#                 continue

#             if "mq7" not in data:
#                 continue

#             return {
#                 "mq2": data["mq2"],
#                 "mq4": data["mq4"],
#                 "mq7": data["mq7"]
#             }

#         except (json.JSONDecodeError, UnicodeDecodeError):
#             print("Ignored corrupted data")
#             continue


# @app.get("/")
# def home():
#     return {
#         "message": "Drone sensor backend is running"
#     }


# @lru_cache(maxsize=1)
# def get_person_model():
#     """Load the supplied detector once, on the first image request."""
#     import torch
#     from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
#     from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

#     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#     model = fasterrcnn_mobilenet_v3_large_fpn(weights=None, weights_backbone=None)
#     features = model.roi_heads.box_predictor.cls_score.in_features
#     model.roi_heads.box_predictor = FastRCNNPredictor(features, 2)
#     state = torch.load(MODEL_PATH, map_location=device)
#     if isinstance(state, dict) and "model_state_dict" in state:
#         state = state["model_state_dict"]
#     model.load_state_dict(state)
#     model.to(device).eval()
#     return model, device


# async def run_detection(pil_image, threshold):
#     """Plain helper — NOT an endpoint. Used by both /api/detect-person and /api/analyze-image."""
#     from PIL import ImageDraw
#     import torch
#     from torchvision.transforms import ToTensor

#     model, device = await asyncio.to_thread(get_person_model)
#     tensor = ToTensor()(pil_image).to(device)
#     with torch.no_grad():
#         prediction = model([tensor])[0]

#     detections = []
#     annotated = pil_image.copy()
#     draw = ImageDraw.Draw(annotated)
#     for box, score, label in zip(prediction["boxes"], prediction["scores"], prediction["labels"]):
#         if float(score) < threshold or int(label) != 1:
#             continue
#         x1, y1, x2, y2 = [round(value, 1) for value in box.cpu().tolist()]
#         confidence = round(float(score), 4)
#         detections.append({"box": [x1, y1, x2, y2], "confidence": confidence, "label": "person"})
#         draw.rectangle((x1, y1, x2, y2), outline="#38bdf8", width=max(3, annotated.width // 300))
#         draw.text((x1 + 6, max(4, y1 - 24)), f"PERSON  {confidence:.0%}", fill="#38bdf8")

#     return {"present": bool(detections), "count": len(detections), "detections": detections}, annotated


# @app.post("/api/detect-person")
# async def detect_person(image: UploadFile = File(...), threshold: float = 0.5):
#     if not image.content_type or not image.content_type.startswith("image/"):
#         raise HTTPException(status_code=400, detail="Please upload a valid image file.")
#     if not 0.05 <= threshold <= 0.99:
#         raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

#     try:
#         from PIL import Image

#         raw = await image.read()
#         pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
#         detection_summary, annotated = await run_detection(pil_image, threshold)

#         output = io.BytesIO()
#         annotated.save(output, format="JPEG", quality=92)
#         return {
#             **detection_summary,
#             "image": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
#         }
#     except Exception as error:
#         raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error


# @app.post("/api/analyze-image")
# async def analyze_image_pipeline(image: UploadFile = File(...), threshold: float = 0.5):
#     if not image.content_type or not image.content_type.startswith("image/"):
#         raise HTTPException(status_code=400, detail="Please upload a valid image file.")
#     if not 0.05 <= threshold <= 0.99:
#         raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

#     try:
#         from PIL import Image

#         raw = await image.read()
#         original = Image.open(io.BytesIO(raw)).convert("RGB")

#         brightness = compute_brightness(original)
#         was_dark = brightness < DARKNESS_THRESHOLD

#         working_image = original
#         enhanced_image_b64 = None
#         if was_dark:
#             working_image = await run_enhancement(original)
#             buf = io.BytesIO()
#             working_image.save(buf, format="JPEG", quality=92)
#             enhanced_image_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

#         detection_summary, annotated = await run_detection(working_image, threshold)

#         output = io.BytesIO()
#         annotated.save(output, format="JPEG", quality=92)
#         final_image_b64 = "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")

#         return {
#             "brightness": round(brightness, 1),
#             "was_dark": was_dark,
#             "enhanced_image": enhanced_image_b64,
#             "detection": {**detection_summary, "image": final_image_b64},
#         }
#     except Exception as error:
#         raise HTTPException(status_code=500, detail=f"Pipeline failed: {error}") from error



# # =====================================================================
# #  LIVE ESP32-CAM PIPELINE  (replaces the old standalone server.py)
# #
# #  ESP32 --multipart POST--> http://<laptop>:5000/upload     (same as before, ESP code unchanged)
# #      fields: cycle, sensor, frames, image1, image2, image3 ...
# #   -> saved to ./captured/cycle_XXX/frame_YY.jpg + cycles.csv (same as server.py)
# #   -> each frame: brightness check -> DCE enhance if dark -> person detection
# #   -> pushed over WebSocket /ws/camera -> dashboard "Live camera" panel
# # =====================================================================
# ESP_RECEIVER_PORT = 5000
# OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "captured")
# CSV_FILE = os.path.join(OUTPUT_DIR, "cycles.csv")
# MAX_CYCLES_TO_KEEP = 50
# LIVE_THRESHOLD = 0.5          # person-detection confidence for live frames
# LIVE_QUEUE_SIZE = 12          # frames waiting for the model; oldest dropped when full

# main_loop = None
# live_clients: set = set()
# live_queue = None
# live_worker_task = None
# latest_live_result = None
# live_frame_counter = 0
# _receiver_server = None


# def to_data_url(pil_image, quality=85):
#     buf = io.BytesIO()
#     pil_image.save(buf, format="JPEG", quality=quality)
#     return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# async def process_live_frame(item):
#     """brightness -> enhance (if dark) -> detect. Returns the JSON payload for the dashboard."""
#     from PIL import Image

#     started = time.perf_counter()
#     original = Image.open(io.BytesIO(item["raw"])).convert("RGB")

#     brightness = compute_brightness(original)
#     was_dark = brightness < DARKNESS_THRESHOLD

#     working = original
#     enhanced_b64 = None
#     if was_dark:
#         working = await run_enhancement(original)
#         enhanced_b64 = to_data_url(working)

#     summary, annotated = await run_detection(working, LIVE_THRESHOLD)

#     return {
#         "frame_id": item["frame_id"],
#         "received_at": item["received_at"],
#         "cycle": item.get("cycle"),
#         "frame_index": item.get("frame_index"),
#         "sensor": item.get("sensor"),
#         "brightness": round(brightness, 1),
#         "was_dark": was_dark,
#         "present": summary["present"],
#         "count": summary["count"],
#         "detections": summary["detections"],
#         "original": to_data_url(original, 75),
#         "enhanced": enhanced_b64,
#         "annotated": to_data_url(annotated, 85),
#         "process_ms": round((time.perf_counter() - started) * 1000),
#     }


# async def broadcast_live(payload):
#     dead = []
#     for client in list(live_clients):
#         try:
#             await client.send_json(payload)
#         except Exception:
#             dead.append(client)
#     for client in dead:
#         live_clients.discard(client)


# async def live_worker():
#     """Single worker so the CPU/GPU only runs one inference at a time."""
#     global latest_live_result
#     print("[LIVE] Loading models (first frame may take a few seconds)...")
#     try:
#         await asyncio.to_thread(get_person_model)
#     except Exception as error:
#         print(f"[LIVE] Person model failed to load: {error}")
#     print("[LIVE] Worker ready")

#     while True:
#         item = await live_queue.get()
#         try:
#             payload = await process_live_frame(item)
#             latest_live_result = payload
#             print(
#                 f"[LIVE] cycle {payload['cycle']} frame {payload['frame_index']} "
#                 f"brightness={payload['brightness']} dark={payload['was_dark']} "
#                 f"persons={payload['count']} ({payload['process_ms']} ms)"
#             )
#             await broadcast_live(payload)
#         except Exception as error:
#             print(f"[LIVE] Frame failed: {error}")


# def ensure_live_worker():
#     global live_queue, live_worker_task
#     if live_queue is None:
#         live_queue = asyncio.Queue(maxsize=LIVE_QUEUE_SIZE)
#     if live_worker_task is None or live_worker_task.done():
#         live_worker_task = asyncio.create_task(live_worker())


# def _enqueue_frame(item):
#     """Runs on the event loop thread."""
#     if live_queue.full():
#         try:
#             live_queue.get_nowait()
#         except asyncio.QueueEmpty:
#             pass
#     live_queue.put_nowait(item)


# # ---------- ESP32 receiver (port 5000), ported from your server.py ----------
# def parse_multipart(body, boundary):
#     delimiter = b"--" + boundary
#     for part in body.split(delimiter):
#         if not part or part in (b"--\r\n", b"--"):
#             continue
#         if part.startswith(b"\r\n"):
#             part = part[2:]
#         header_end = part.find(b"\r\n\r\n")
#         if header_end == -1:
#             continue
#         headers_raw = part[:header_end].decode("utf-8", errors="ignore")
#         data = part[header_end + 4:]
#         if data.endswith(b"\r\n"):
#             data = data[:-2]
#         name_m = re.search(r'name="([^"]*)"', headers_raw)
#         yield {"name": name_m.group(1) if name_m else None, "data": data}


# def append_csv_row(cycle, sensor, frames, total_bytes, ts):
#     write_header = not os.path.isfile(CSV_FILE)
#     with open(CSV_FILE, "a", newline="") as f:
#         w = csv.writer(f)
#         if write_header:
#             w.writerow(["cycle", "timestamp", "sensor_avg", "frames", "total_bytes",
#                         "frame1_bytes", "frame2_bytes", "frame3_bytes"])
#         w.writerow([cycle, ts, sensor, len(frames), total_bytes,
#                     len(frames.get(1, b"")), len(frames.get(2, b"")), len(frames.get(3, b""))])


# def cleanup_old_cycles():
#     try:
#         dirs = sorted(d for d in os.listdir(OUTPUT_DIR)
#                       if d.startswith("cycle_") and os.path.isdir(os.path.join(OUTPUT_DIR, d)))
#         for d in dirs[:-MAX_CYCLES_TO_KEEP] if len(dirs) > MAX_CYCLES_TO_KEEP else []:
#             full = os.path.join(OUTPUT_DIR, d)
#             for f in os.listdir(full):
#                 try:
#                     os.remove(os.path.join(full, f))
#                 except OSError:
#                     pass
#             try:
#                 os.rmdir(full)
#             except OSError:
#                 pass
#             print(f"[ESP] Cleaned old {d}")
#     except Exception as e:
#         print(f"[ESP] cleanup error: {e}")


# class ESPReceiver(BaseHTTPRequestHandler):
#     def do_POST(self):
#         global live_frame_counter
#         if self.path != "/upload":
#             self.send_response(404); self.end_headers(); return

#         length = int(self.headers.get("Content-Length", 0))
#         bm = re.search(r"boundary=(.+)", self.headers.get("Content-Type", ""))
#         if not bm:
#             self.send_response(400); self.end_headers(); return

#         body = self.rfile.read(length)
#         cycle, sensor, frames_expected, images = None, None, 0, {}

#         for field in parse_multipart(body, bm.group(1).strip().encode()):
#             name = field["name"]
#             if name == "cycle":
#                 try: cycle = int(field["data"].decode().strip())
#                 except ValueError: pass
#             elif name == "sensor":
#                 sensor = field["data"].decode().strip()
#             elif name == "frames":
#                 try: frames_expected = int(field["data"].decode().strip())
#                 except ValueError: pass
#             elif name and name.startswith("image"):
#                 try: images[int(name.replace("image", ""))] = field["data"]
#                 except ValueError: pass

#         if cycle is None or not images:
#             self.send_response(400); self.end_headers()
#             self.wfile.write(b"Missing cycle or images"); return

#         # 1) save exactly like the old server.py
#         folder = os.path.join(OUTPUT_DIR, f"cycle_{cycle:03d}")
#         os.makedirs(folder, exist_ok=True)
#         total_bytes = 0
#         for idx in sorted(images):
#             path = os.path.join(folder, f"frame_{idx:02d}.jpg")
#             with open(path, "wb") as f:
#                 f.write(images[idx])
#             total_bytes += len(images[idx])
#             print(f"[ESP] Saved {path} ({len(images[idx])} bytes)")
#         if sensor is not None:
#             with open(os.path.join(folder, "sensor.txt"), "w") as f:
#                 f.write(f"sensor_value={sensor}\n")
#         try:
#             sensor_int = int(sensor) if sensor is not None else -1
#         except (ValueError, TypeError):
#             sensor_int = -1
#         ts = datetime.now().isoformat(timespec="seconds")
#         append_csv_row(cycle, sensor_int, images, total_bytes, ts)
#         print(f"[ESP] Cycle {cycle} complete - {len(images)}/{frames_expected} frames, sensor={sensor}")
#         cleanup_old_cycles()

#         # 2) hand every frame to the live AI pipeline
#         if main_loop is not None and live_queue is not None:
#             for idx in sorted(images):
#                 live_frame_counter += 1
#                 item = {
#                     "raw": images[idx],
#                     "frame_id": live_frame_counter,
#                     "received_at": int(time.time() * 1000),
#                     "cycle": cycle,
#                     "frame_index": idx,
#                     "sensor": sensor,
#                 }
#                 main_loop.call_soon_threadsafe(_enqueue_frame, item)

#         self.send_response(200); self.end_headers()
#         self.wfile.write(b"OK")

#     def log_message(self, fmt, *args):
#         pass


# def start_esp_receiver():
#     global _receiver_server
#     os.makedirs(OUTPUT_DIR, exist_ok=True)
#     try:
#         _receiver_server = HTTPServer(("0.0.0.0", ESP_RECEIVER_PORT), ESPReceiver)
#     except OSError as error:
#         print(f"[ESP] Could not open port {ESP_RECEIVER_PORT}: {error}")
#         print("[ESP] Is the old server.py still running? Close it (Ctrl+C) and restart.")
#         return
#     threading.Thread(target=_receiver_server.serve_forever, daemon=True).start()
#     print(f"[ESP] Receiver listening on port {ESP_RECEIVER_PORT}  ->  POST /upload")


# def stop_esp_receiver():
#     if _receiver_server is not None:
#         _receiver_server.shutdown()


# @app.get("/api/live/latest")
# def live_latest():
#     """Debug: http://localhost:8000/api/live/latest"""
#     return latest_live_result or {"message": "No frames received yet."}


# @app.websocket("/ws/camera")
# async def camera_websocket(websocket: WebSocket):
#     await websocket.accept()
#     live_clients.add(websocket)
#     print(f"[LIVE] dashboard connected ({len(live_clients)} client(s))")
#     try:
#         if latest_live_result is not None:
#             await websocket.send_json(latest_live_result)
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         pass
#     except Exception as error:
#         print("[LIVE] websocket error:", error)
#     finally:
#         live_clients.discard(websocket)
#         print(f"[LIVE] dashboard disconnected ({len(live_clients)} client(s))")


# @app.websocket("/ws/sensors")
# async def sensor_websocket(websocket: WebSocket):

#     await websocket.accept()

#     print("WebSocket client connected")

#     try:

#         while True:

#             data = await asyncio.to_thread(read_sensor_data)

#             if data is not None:
#                 print("SENDING:", data)
#                 await websocket.send_json(data)
#             else:
#                 await asyncio.sleep(2)

#     except WebSocketDisconnect:

#         print("WebSocket client disconnected")

#     except Exception as e:

#         print("WebSocket error:", e)



import json
import asyncio
import base64
import io
import os
import tempfile
from functools import lru_cache

try:
    import serial
except ImportError:
    serial = None

import re
import csv
import time
import threading
from datetime import datetime
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(_app):
    # Runs once when uvicorn starts: remember the event loop, start the live worker
    # and start the ESP32 receiver (port 5000) in a background thread.
    global main_loop
    main_loop = asyncio.get_running_loop()
    ensure_live_worker()
    start_esp_receiver()
    yield
    stop_esp_receiver()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "fasterrcnn_person_best.pth")
DCE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "dce_model.keras")
ENHANCE_IMAGE_SIZE = 256
DARKNESS_THRESHOLD = 50
VIDEO_SAMPLE_INTERVAL_SECONDS = 1.0
MAX_VIDEO_FRAMES = 30
VIDEO_OUTPUT_MAX_WIDTH = 480

@app.post("/api/analyze-video")
async def analyze_video_pipeline(video: UploadFile = File(...), threshold: float = 0.5):
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Please upload a valid video file.")
    if not 0.05 <= threshold <= 0.99:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

    tmp_path = None
    try:
        import cv2
        from PIL import Image

        raw = await video.read()
        suffix = os.path.splitext(video.filename or "")[1] or ".mp4"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)

        capture = cv2.VideoCapture(tmp_path)
        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total_frames / fps if fps else 0.0
        frame_step = max(1, round(fps * VIDEO_SAMPLE_INTERVAL_SECONDS))

        results = []
        frame_index = 0
        processed = 0

        while processed < MAX_VIDEO_FRAMES and frame_index < total_frames:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame_bgr = capture.read()
            if not success:
                break

            pil_frame = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

            brightness = compute_brightness(pil_frame)
            was_dark = brightness < DARKNESS_THRESHOLD

            working_frame = await run_enhancement(pil_frame) if was_dark else pil_frame
            detection_summary, annotated = await run_detection(working_frame, threshold)

            if annotated.width > VIDEO_OUTPUT_MAX_WIDTH:
                ratio = VIDEO_OUTPUT_MAX_WIDTH / annotated.width
                annotated = annotated.resize((VIDEO_OUTPUT_MAX_WIDTH, round(annotated.height * ratio)))

            buf = io.BytesIO()
            annotated.save(buf, format="JPEG", quality=80)
            image_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

            results.append({
                "timestamp": round(frame_index / fps, 2) if fps else None,
                "brightness": round(brightness, 1),
                "was_dark": was_dark,
                "detection": {**detection_summary, "image": image_b64},
            })

            processed += 1
            frame_index += frame_step

        capture.release()

        return {
            "duration_seconds": round(duration, 2),
            "fps": round(fps, 2),
            "frames_processed": processed,
            "any_person_detected": any(r["detection"]["present"] for r in results),
            "total_detections": sum(r["detection"]["count"] for r in results),
            "frames": results,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {error}") from error
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def compute_brightness(pil_image):
    import numpy as np
    gray = pil_image.convert("L")
    return float(np.array(gray).mean())


@lru_cache(maxsize=1)
def get_enhance_model():
    """Load the low-light enhancement (DCE) model once, on first request."""
    from tensorflow import keras
    return keras.models.load_model(DCE_MODEL_PATH)


async def run_enhancement(pil_image):
    """Plain helper — NOT an endpoint. Used by both /api/enhance-image and /api/analyze-image."""
    import numpy as np
    import tensorflow as tf
    from PIL import Image

    resized = pil_image.resize((ENHANCE_IMAGE_SIZE, ENHANCE_IMAGE_SIZE))
    arr = np.array(resized).astype("float32") / 255.0
    arr = np.expand_dims(arr, axis=0)

    model = await asyncio.to_thread(get_enhance_model)
    dce_output = await asyncio.to_thread(model, arr, training=False)

    x = arr
    for i in range(0, 3 * 8, 3):
        r = dce_output[:, :, :, i:i + 3]
        x = x + r * (tf.square(x) - x)

    enhanced = tf.clip_by_value(x[0], 0.0, 1.0)
    enhanced = tf.cast(enhanced * 255, tf.uint8).numpy()
    return Image.fromarray(enhanced).resize(pil_image.size)


@app.post("/api/enhance-image")
async def enhance_image_endpoint(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    try:
        from PIL import Image

        raw = await image.read()
        original = Image.open(io.BytesIO(raw)).convert("RGB")
        enhanced_image = await run_enhancement(original)

        output = io.BytesIO()
        enhanced_image.save(output, format="JPEG", quality=92)
        return {
            "image": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {error}") from error


try:
    arduino = serial.Serial(port="COM7", baudrate=9600, timeout=1) if serial else None
except Exception as error:
    arduino = None
    print(f"Arduino unavailable; sensor WebSocket will remain idle: {error}")

# Give Arduino time to reset after opening COM port
print("Opening Arduino...")


def read_sensor_data():

    if arduino is None:
        return None

    while True:

        line = arduino.readline()

        if not line:
            continue

        try:
            text = line.decode("utf-8", errors="ignore").strip()

            print("RAW:", repr(text))

            # Find JSON inside the received line
            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1:
                continue

            json_text = text[start:end + 1]

            data = json.loads(json_text)

            # Make sure required values exist
            if "mq2" not in data:
                continue

            if "mq4" not in data:
                continue

            if "mq7" not in data:
                continue

            return {
                "mq2": data["mq2"],
                "mq4": data["mq4"],
                "mq7": data["mq7"]
            }

        except (json.JSONDecodeError, UnicodeDecodeError):
            print("Ignored corrupted data")
            continue


@app.get("/")
def home():
    return {
        "message": "Drone sensor backend is running"
    }


@lru_cache(maxsize=1)
def get_person_model():
    """Load the supplied detector once, on the first image request."""
    import torch
    from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = fasterrcnn_mobilenet_v3_large_fpn(weights=None, weights_backbone=None)
    features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(features, 2)
    state = torch.load(MODEL_PATH, map_location=device)
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    model.load_state_dict(state)
    model.to(device).eval()
    return model, device


def _run_detection_sync(pil_image, threshold):
    """Heavy, blocking inference. Always call it through run_detection() so it runs in a thread."""
    from PIL import ImageDraw
    import torch
    from torchvision.transforms import ToTensor

    model, device = get_person_model()
    tensor = ToTensor()(pil_image).to(device)
    with torch.no_grad():
        prediction = model([tensor])[0]

    detections = []
    annotated = pil_image.copy()
    draw = ImageDraw.Draw(annotated)
    for box, score, label in zip(prediction["boxes"], prediction["scores"], prediction["labels"]):
        if float(score) < threshold or int(label) != 1:
            continue
        x1, y1, x2, y2 = [round(value, 1) for value in box.cpu().tolist()]
        confidence = round(float(score), 4)
        detections.append({"box": [x1, y1, x2, y2], "confidence": confidence, "label": "person"})
        draw.rectangle((x1, y1, x2, y2), outline="#38bdf8", width=max(3, annotated.width // 300))
        draw.text((x1 + 6, max(4, y1 - 24)), f"PERSON  {confidence:.0%}", fill="#38bdf8")

    return {"present": bool(detections), "count": len(detections), "detections": detections}, annotated


async def run_detection(pil_image, threshold):
    """Plain helper — NOT an endpoint. Runs inference off the event loop so the server stays responsive."""
    return await asyncio.to_thread(_run_detection_sync, pil_image, threshold)


@app.post("/api/detect-person")
async def detect_person(image: UploadFile = File(...), threshold: float = 0.5):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    if not 0.05 <= threshold <= 0.99:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

    try:
        from PIL import Image

        raw = await image.read()
        pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
        detection_summary, annotated = await run_detection(pil_image, threshold)

        output = io.BytesIO()
        annotated.save(output, format="JPEG", quality=92)
        return {
            **detection_summary,
            "image": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error


@app.post("/api/analyze-image")
async def analyze_image_pipeline(image: UploadFile = File(...), threshold: float = 0.5):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    if not 0.05 <= threshold <= 0.99:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

    try:
        from PIL import Image

        raw = await image.read()
        original = Image.open(io.BytesIO(raw)).convert("RGB")

        brightness = compute_brightness(original)
        was_dark = brightness < DARKNESS_THRESHOLD

        working_image = original
        enhanced_image_b64 = None
        if was_dark:
            working_image = await run_enhancement(original)
            buf = io.BytesIO()
            working_image.save(buf, format="JPEG", quality=92)
            enhanced_image_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        detection_summary, annotated = await run_detection(working_image, threshold)

        output = io.BytesIO()
        annotated.save(output, format="JPEG", quality=92)
        final_image_b64 = "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")

        return {
            "brightness": round(brightness, 1),
            "was_dark": was_dark,
            "enhanced_image": enhanced_image_b64,
            "detection": {**detection_summary, "image": final_image_b64},
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {error}") from error



# =====================================================================
#  LIVE ESP32-CAM PIPELINE  (replaces the old standalone server.py)
#
#  ESP32 --multipart POST--> http://<laptop>:5000/upload     (same as before, ESP code unchanged)
#      fields: cycle, sensor, frames, image1, image2, image3 ...
#   -> saved to ./captured/cycle_XXX/frame_YY.jpg + cycles.csv (same as server.py)
#   -> each frame: brightness check -> DCE enhance if dark -> person detection
#   -> pushed over WebSocket /ws/camera -> dashboard "Live camera" panel
# =====================================================================
ESP_RECEIVER_PORT = 5000
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "captured")
CSV_FILE = os.path.join(OUTPUT_DIR, "cycles.csv")
MAX_CYCLES_TO_KEEP = 50
LIVE_THRESHOLD = 0.5          # person-detection confidence for live frames
LIVE_QUEUE_SIZE = 3           # frames waiting for the model; oldest dropped so the view stays real-time

main_loop = None
live_clients: set = set()
live_queue = None
live_worker_task = None
latest_live_result = None
live_frame_counter = 0
_receiver_server = None


def to_data_url(pil_image, quality=85):
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


async def process_live_frame(item):
    """brightness -> enhance (if dark) -> detect. Returns the JSON payload for the dashboard."""
    from PIL import Image

    started = time.perf_counter()
    original = Image.open(io.BytesIO(item["raw"])).convert("RGB")

    brightness = compute_brightness(original)
    was_dark = brightness < DARKNESS_THRESHOLD

    working = original
    enhanced_b64 = None
    if was_dark:
        working = await run_enhancement(original)
        enhanced_b64 = await asyncio.to_thread(to_data_url, working)

    summary, annotated = await run_detection(working, LIVE_THRESHOLD)

    return {
        "frame_id": item["frame_id"],
        "received_at": item["received_at"],
        "cycle": item.get("cycle"),
        "frame_index": item.get("frame_index"),
        "sensor": item.get("sensor"),
        "brightness": round(brightness, 1),
        "was_dark": was_dark,
        "present": summary["present"],
        "count": summary["count"],
        "detections": summary["detections"],
        "original": await asyncio.to_thread(to_data_url, original, 70),
        "enhanced": enhanced_b64,
        "annotated": await asyncio.to_thread(to_data_url, annotated, 80),
        "process_ms": round((time.perf_counter() - started) * 1000),
    }


async def broadcast_live(payload):
    dead = []
    for client in list(live_clients):
        try:
            await client.send_json(payload)
        except Exception:
            dead.append(client)
    for client in dead:
        live_clients.discard(client)


async def live_worker():
    """Single worker so the CPU/GPU only runs one inference at a time."""
    global latest_live_result
    print("[LIVE] Loading models (first frame may take a few seconds)...")
    try:
        await asyncio.to_thread(get_person_model)
    except Exception as error:
        print(f"[LIVE] Person model failed to load: {error}")
    print("[LIVE] Worker ready")

    while True:
        item = await live_queue.get()
        try:
            payload = await process_live_frame(item)
            latest_live_result = payload
            print(
                f"[LIVE] cycle {payload['cycle']} frame {payload['frame_index']} "
                f"brightness={payload['brightness']} dark={payload['was_dark']} "
                f"persons={payload['count']} ({payload['process_ms']} ms)"
            )
            await broadcast_live(payload)
        except Exception as error:
            print(f"[LIVE] Frame failed: {error}")


def ensure_live_worker():
    global live_queue, live_worker_task
    if live_queue is None:
        live_queue = asyncio.Queue(maxsize=LIVE_QUEUE_SIZE)
    if live_worker_task is None or live_worker_task.done():
        live_worker_task = asyncio.create_task(live_worker())


def _enqueue_frame(item):
    """Runs on the event loop thread."""
    if live_queue.full():
        try:
            live_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    live_queue.put_nowait(item)


# ---------- ESP32 receiver (port 5000), ported from your server.py ----------
def parse_multipart(body, boundary):
    delimiter = b"--" + boundary
    for part in body.split(delimiter):
        if not part or part in (b"--\r\n", b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        headers_raw = part[:header_end].decode("utf-8", errors="ignore")
        data = part[header_end + 4:]
        if data.endswith(b"\r\n"):
            data = data[:-2]
        name_m = re.search(r'name="([^"]*)"', headers_raw)
        yield {"name": name_m.group(1) if name_m else None, "data": data}


def append_csv_row(cycle, sensor, frames, total_bytes, ts):
    write_header = not os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["cycle", "timestamp", "sensor_avg", "frames", "total_bytes",
                        "frame1_bytes", "frame2_bytes", "frame3_bytes"])
        w.writerow([cycle, ts, sensor, len(frames), total_bytes,
                    len(frames.get(1, b"")), len(frames.get(2, b"")), len(frames.get(3, b""))])


def cleanup_old_cycles():
    try:
        dirs = sorted(d for d in os.listdir(OUTPUT_DIR)
                      if d.startswith("cycle_") and os.path.isdir(os.path.join(OUTPUT_DIR, d)))
        for d in dirs[:-MAX_CYCLES_TO_KEEP] if len(dirs) > MAX_CYCLES_TO_KEEP else []:
            full = os.path.join(OUTPUT_DIR, d)
            for f in os.listdir(full):
                try:
                    os.remove(os.path.join(full, f))
                except OSError:
                    pass
            try:
                os.rmdir(full)
            except OSError:
                pass
            print(f"[ESP] Cleaned old {d}")
    except Exception as e:
        print(f"[ESP] cleanup error: {e}")


class ESPReceiver(BaseHTTPRequestHandler):
    def do_POST(self):
        global live_frame_counter
        if self.path != "/upload":
            self.send_response(404); self.end_headers(); return

        length = int(self.headers.get("Content-Length", 0))
        bm = re.search(r"boundary=(.+)", self.headers.get("Content-Type", ""))
        if not bm:
            self.send_response(400); self.end_headers(); return

        body = self.rfile.read(length)
        cycle, sensor, frames_expected, images = None, None, 0, {}

        for field in parse_multipart(body, bm.group(1).strip().encode()):
            name = field["name"]
            if name == "cycle":
                try: cycle = int(field["data"].decode().strip())
                except ValueError: pass
            elif name == "sensor":
                sensor = field["data"].decode().strip()
            elif name == "frames":
                try: frames_expected = int(field["data"].decode().strip())
                except ValueError: pass
            elif name and name.startswith("image"):
                try: images[int(name.replace("image", ""))] = field["data"]
                except ValueError: pass

        if cycle is None or not images:
            self.send_response(400); self.end_headers()
            self.wfile.write(b"Missing cycle or images"); return

        # 1) save exactly like the old server.py
        folder = os.path.join(OUTPUT_DIR, f"cycle_{cycle:03d}")
        os.makedirs(folder, exist_ok=True)
        total_bytes = 0
        for idx in sorted(images):
            path = os.path.join(folder, f"frame_{idx:02d}.jpg")
            with open(path, "wb") as f:
                f.write(images[idx])
            total_bytes += len(images[idx])
            print(f"[ESP] Saved {path} ({len(images[idx])} bytes)")
        if sensor is not None:
            with open(os.path.join(folder, "sensor.txt"), "w") as f:
                f.write(f"sensor_value={sensor}\n")
        try:
            sensor_int = int(sensor) if sensor is not None else -1
        except (ValueError, TypeError):
            sensor_int = -1
        ts = datetime.now().isoformat(timespec="seconds")
        append_csv_row(cycle, sensor_int, images, total_bytes, ts)
        print(f"[ESP] Cycle {cycle} complete - {len(images)}/{frames_expected} frames, sensor={sensor}")
        cleanup_old_cycles()

        # 2) hand every frame to the live AI pipeline
        if main_loop is not None and live_queue is not None:
            for idx in sorted(images):
                live_frame_counter += 1
                item = {
                    "raw": images[idx],
                    "frame_id": live_frame_counter,
                    "received_at": int(time.time() * 1000),
                    "cycle": cycle,
                    "frame_index": idx,
                    "sensor": sensor,
                }
                main_loop.call_soon_threadsafe(_enqueue_frame, item)

        self.send_response(200); self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, fmt, *args):
        pass


def start_esp_receiver():
    global _receiver_server
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        _receiver_server = HTTPServer(("0.0.0.0", ESP_RECEIVER_PORT), ESPReceiver)
    except OSError as error:
        print(f"[ESP] Could not open port {ESP_RECEIVER_PORT}: {error}")
        print("[ESP] Is the old server.py still running? Close it (Ctrl+C) and restart.")
        return
    threading.Thread(target=_receiver_server.serve_forever, daemon=True).start()
    print(f"[ESP] Receiver listening on port {ESP_RECEIVER_PORT}  ->  POST /upload")


def stop_esp_receiver():
    if _receiver_server is not None:
        _receiver_server.shutdown()
        _receiver_server.server_close()   # free port 5000 right away (matters with --reload)


@app.get("/api/live/latest")
def live_latest():
    """Debug: http://localhost:8000/api/live/latest"""
    return latest_live_result or {"message": "No frames received yet."}


@app.websocket("/ws/camera")
async def camera_websocket(websocket: WebSocket):
    await websocket.accept()
    live_clients.add(websocket)
    print(f"[LIVE] dashboard connected ({len(live_clients)} client(s))")
    try:
        if latest_live_result is not None:
            await websocket.send_json(latest_live_result)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as error:
        print("[LIVE] websocket error:", error)
    finally:
        live_clients.discard(websocket)
        print(f"[LIVE] dashboard disconnected ({len(live_clients)} client(s))")


@app.websocket("/ws/sensors")
async def sensor_websocket(websocket: WebSocket):

    await websocket.accept()

    print("WebSocket client connected")

    try:

        while True:

            data = await asyncio.to_thread(read_sensor_data)

            if data is not None:
                print("SENDING:", data)
                await websocket.send_json(data)
            else:
                await asyncio.sleep(2)

    except WebSocketDisconnect:

        print("WebSocket client disconnected")

    except Exception as e:

        print("WebSocket error:", e)