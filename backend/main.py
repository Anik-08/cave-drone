import json
import asyncio
import base64
import io
import os
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

@lru_cache(maxsize=1)
def get_enhance_model():
    """Load the low-light enhancement (DCE) model once, on first request."""
    from tensorflow import keras
    return keras.models.load_model(DCE_MODEL_PATH)

@app.post("/api/enhance-image")
async def enhance_image_endpoint(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    try:
        import numpy as np
        import tensorflow as tf
        from PIL import Image

        raw = await image.read()
        original = Image.open(io.BytesIO(raw)).convert("RGB")
        resized = original.resize((ENHANCE_IMAGE_SIZE, ENHANCE_IMAGE_SIZE))

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
        enhanced_image = Image.fromarray(enhanced).resize(original.size)

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


@app.post("/api/detect-person")
async def detect_person(image: UploadFile = File(...), threshold: float = 0.5):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    if not 0.05 <= threshold <= 0.99:
        raise HTTPException(status_code=400, detail="Threshold must be between 0.05 and 0.99.")

    try:
        from PIL import Image, ImageDraw, ImageFont
        import torch
        from torchvision.transforms import ToTensor

        raw = await image.read()
        pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
        model, device = await asyncio.to_thread(get_person_model)
        tensor = ToTensor()(pil_image).to(device)
        with torch.no_grad():
            prediction = model([tensor])[0]

        detections = []
        draw = ImageDraw.Draw(pil_image)
        for box, score, label in zip(prediction["boxes"], prediction["scores"], prediction["labels"]):
            if float(score) < threshold or int(label) != 1:
                continue
            x1, y1, x2, y2 = [round(value, 1) for value in box.cpu().tolist()]
            confidence = round(float(score), 4)
            detections.append({"box": [x1, y1, x2, y2], "confidence": confidence, "label": "person"})
            draw.rectangle((x1, y1, x2, y2), outline="#38bdf8", width=max(3, pil_image.width // 300))
            draw.text((x1 + 6, max(4, y1 - 24)), f"PERSON  {confidence:.0%}", fill="#38bdf8")

        output = io.BytesIO()
        pil_image.save(output, format="JPEG", quality=92)
        return {
            "present": bool(detections),
            "count": len(detections),
            "detections": detections,
            "image": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Inference failed: {error}") from error


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
