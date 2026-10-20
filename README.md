# Cave-Drone: Low-Light Cave Monitoring and Human Detection

`cave-drone` is a two-part system for cave/underground monitoring:
- **Python/FastAPI backend** for sensor ingest, low-light enhancement, person detection, and live frame processing.
- **Next.js frontend** for real-time dashboarding and manual image/video analysis.

The pipeline is designed for **low-visibility cave scenes** where illumination is poor and person detection can otherwise fail.

---

## 1) What the project does

1. Receives cave frames (single image, video, or live ESP32-CAM uploads).
2. Measures brightness.
3. Applies **Zero-DCE-style enhancement** when the frame is dark.
4. Runs person detection with a **fine-tuned Faster R-CNN MobileNetV3-FPN** model.
5. Streams results to dashboard clients over WebSocket.

---

## 2) Repository layout

```text
backend/
  main.py                           FastAPI service + live ESP receiver + inference pipeline
  model_artifacts.py                Model metadata, checksums, verification/bootstrap CLI
  low_light_test.py                 Local CLI for low-light enhancement testing
  test_local_inference_fasterrcnn.py Local CLI for person detector testing
  dce_model.keras                   Zero-DCE-style enhancement checkpoint
  fasterrcnn_person_best.pth        Fine-tuned person detector checkpoint
  captured/                         Saved ESP32 cycles and frames
frontend/
  app/, components/, hooks/, lib/  Next.js UI and dashboard logic
```

---

## 3) Model documentation (exact models used)

### Low-light enhancement model
- **Implementation in code:** custom Keras model loaded from `backend/dce_model.keras`.
- **Variant behavior:** **Zero-DCE-style iterative curve estimation** (8 iterations, 24-channel curve output, `x = x + r * (x^2 - x)`), implemented in:
  - `backend/main.py` (`run_enhancement`)
  - `backend/low_light_test.py`
- **Input behavior:** RGB image resized to `256x256`, normalized to `[0,1]`.
- **Output behavior:** enhanced RGB image clipped to `[0,255]`, converted to uint8, resized back to original size in API path.

### Human detection model
- **Architecture:** TorchVision `fasterrcnn_mobilenet_v3_large_fpn`.
- **Checkpoint:** `backend/fasterrcnn_person_best.pth`.
- **Head configuration:** 2 classes (`background + person`) with `FastRCNNPredictor`.
- **Class filter:** inference keeps only `label == 1` as person, with threshold filtering.
- **Implemented in:** `backend/main.py` (`get_person_model`, `_run_detection_sync`).

### Artifact registry, provenance, integrity

Use:
```bash
python backend/model_artifacts.py list
python backend/model_artifacts.py verify
python backend/model_artifacts.py bootstrap
```

`bootstrap` downloads exact artifacts from this repository’s `main` branch raw URLs and verifies SHA-256.

Current expected checksums:
- `dce_model.keras`: `cffeea6ff142185107fe0aff6dc30345cc1b73efcbb8495ec636f0a3083938ee`
- `fasterrcnn_person_best.pth`: `ce1c902f44622c53ec9244b8b88e3e7203affb7f3f6cb26c165fbcada6c59aec`

---

## 4) Requirements

- Python 3.10+ (backend)
- Node.js 20+ and npm (frontend)
- Recommended for acceleration: NVIDIA GPU + CUDA-enabled PyTorch/TensorFlow environment
- Works on CPU (slower inference)

---

## 5) Setup (clean clone)

From repository root:

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python model_artifacts.py verify
```

If artifacts are missing/corrupted:
```bash
python model_artifacts.py bootstrap
```

Run backend:
```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

---

## 6) Inference usage

Base backend URL: `http://localhost:8000`

### A) Low-light enhancement only
```bash
curl -X POST "http://localhost:8000/api/enhance-image" \
  -F "image=@/absolute/path/to/frame.jpg"
```

### B) Person detection only
```bash
curl -X POST "http://localhost:8000/api/detect-person?threshold=0.5" \
  -F "image=@/absolute/path/to/frame.jpg"
```

### C) Combined cave scan (auto enhance-if-dark + detect)
```bash
curl -X POST "http://localhost:8000/api/analyze-image?threshold=0.5" \
  -F "image=@/absolute/path/to/frame.jpg"
```

### D) Video scan
```bash
curl -X POST "http://localhost:8000/api/analyze-video?threshold=0.5" \
  -F "video=@/absolute/path/to/video.mp4"
```

### E) Local direct scripts (no API)
```bash
cd backend
python low_light_test.py /absolute/path/in.jpg /absolute/path/out.jpg
python test_local_inference_fasterrcnn.py --checkpoint fasterrcnn_person_best.pth --images /absolute/path/in.jpg
```

---

## 7) Live ESP32-CAM + dashboard flow

Live receiver listens on backend port `5000`:
- endpoint: `POST /upload`
- fields expected: `cycle`, `sensor`, `frames`, `image1`, `image2`, `image3`, ...

Processed frames are broadcast to:
- `ws://127.0.0.1:8000/ws/camera`

Sensor stream endpoint:
- `ws://127.0.0.1:8000/ws/sensors`

---

## 8) Configuration and outputs

Key backend constants (`backend/main.py`):
- `DARKNESS_THRESHOLD = 50`
- `ENHANCE_IMAGE_SIZE = 256`
- `LIVE_THRESHOLD = 0.5`
- `MAX_VIDEO_FRAMES = 30`
- `VIDEO_SAMPLE_INTERVAL_SECONDS = 1.0`

Outputs:
- JSON detections (`present`, `count`, `detections[]`)
- Annotated output images as base64 data URLs
- Captured ESP32 cycles saved under `backend/captured/cycle_*`

---

## 9) Troubleshooting

- **Startup fails with model artifact error**
  - Run `python backend/model_artifacts.py verify`
  - Then `python backend/model_artifacts.py bootstrap`
- **No detections**
  - Lower threshold (`0.5 -> 0.3`) and test with a known-person image.
- **Very slow inference**
  - Use GPU-enabled PyTorch/TensorFlow, reduce video length, or increase frame sampling interval.
- **No live camera updates**
  - Confirm ESP32 is posting to backend port `5000` and frontend is using correct `NEXT_PUBLIC_CAMERA_WS_URL`.

---

## 10) Safety and operational limitations

- This is a **decision-support prototype**, not a certified safety system.
- Gas values and thresholds in dashboard are prototype-level and require domain calibration/validation.
- Vision models can miss detections under severe occlusion, motion blur, or extreme low light.
- Always maintain human-in-the-loop review for safety-critical cave operations.

---

## 11) Development and validation

Backend quick checks:
```bash
cd backend
python -m unittest test_model_artifacts.py
python test_analysis.py
python model_artifacts.py verify
```

Frontend lint:
```bash
cd frontend
npm run lint
```

---

## 12) License and third-party attributions

- Repository code: see project license policy in this repository.
- TorchVision model architecture (`fasterrcnn_mobilenet_v3_large_fpn`): from `torchvision` (BSD-style license).
- Included model artifacts are project assets; review redistribution and dataset/training rights before external distribution.

---

## 13) Contributing

1. Create a branch from `main`.
2. Make focused changes with tests/verification.
3. Ensure model artifacts verify (`python backend/model_artifacts.py verify`).
4. Open a PR with:
   - summary of code/documentation changes
   - commands executed for validation
   - any model-impact details (paths/checksums/version notes)
