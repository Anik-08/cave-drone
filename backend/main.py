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

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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


async def run_detection(pil_image, threshold):
    """Plain helper — NOT an endpoint. Used by both /api/detect-person and /api/analyze-image."""
    from PIL import ImageDraw
    import torch
    from torchvision.transforms import ToTensor

    model, device = await asyncio.to_thread(get_person_model)
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