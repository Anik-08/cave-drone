# Cave-Drone: Low-Light Cave Monitoring, Human and Object Detection

`cave-drone` is a two-part system for cave/underground monitoring:
- **Python/FastAPI backend** for sensor ingest, low-light enhancement, person detection, general object detection, and live frame processing.
- **Next.js frontend** for real-time dashboarding and manual image/video analysis.

The pipeline is designed for **low-visibility cave scenes** where illumination is poor and person detection can otherwise fail. People are found by a detector fine-tuned for this setting, and every other common object (backpack, bottle, car, animal, and so on) is found by a general-purpose YOLO model running on the same frame.

---

## 1) What the project does

1. Receives cave frames (single image, video, or live ESP32-CAM uploads).
2. Measures brightness.
3. Applies **Zero-DCE-style enhancement** when the frame is dark.
4. Runs person detection with a **fine-tuned Faster R-CNN MobileNetV3-FPN** model.
5. Runs general object detection with a **YOLO11-nano** model (80 common COCO classes) on the same frame, and merges the results with the person detections.
6. Streams results to dashboard clients over WebSocket.

### How the two detectors work together

Both detectors receive the same image: the original frame, or the enhanced frame when the original was dark. Their results are merged into a single list.

- **People** always come from the fine-tuned Faster R-CNN model, because it was trained for cave and low-light scenes.
- **Everything else** comes from YOLO. YOLO's own `person` boxes are discarded on purpose, so a person is never counted twice.
- If YOLO is unavailable for any reason (not installed, weights missing), person detection keeps working and a message is printed in the backend terminal.
- One confidence threshold is applied to both models.

### Dashboard panels

| Panel | What it does |
|---|---|
| Live camera | Shows frames from the ESP32-CAM in real time, with detection boxes, a per-class summary (for example `2 person · 1 backpack`), brightness, and processing time. |
| Object detection | Upload a single image and get people and objects with a confidence slider. |
| Cave scan | Upload a frame; dark images are enhanced automatically before detection. |
| Video scan | Upload a video; about one frame per second is sampled, enhanced if dark, and scanned. |

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
  yolo11n.pt                        YOLO11-nano pretrained weights (general object detection)
  captured/                         Saved ESP32 cycles and frames
frontend/
  app/, components/, hooks/, lib/  Next.js UI and dashboard logic
  lib/objects.ts                    Helper that formats per-class counts (e.g. "2 person · 1 backpack")
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

### Object detection model
- **Architecture:** Ultralytics **YOLO11-nano** (`yolo11n`), a general-purpose detector pretrained on the COCO dataset.
- **Weights:** `backend/yolo11n.pt`. If the file is not present, Ultralytics downloads it automatically the first time the backend needs it (internet access is needed once).
- **Classes:** the 80 standard COCO classes (person, backpack, bottle, car, dog, chair, and so on). Objects outside these classes are not detected.
- **Person handling:** YOLO's `person` class is skipped; people come from the Faster R-CNN model above.
- **Failure behavior:** if YOLO cannot load or run, the backend prints `[DETECT] YOLO object detection skipped: <reason>` and still returns person detections.
- **Thread safety:** YOLO calls are guarded by a lock, because the live worker and the upload endpoints can run at the same time.
- **Implemented in:** `backend/main.py` (`get_object_model`, `_run_combined_detection_sync`, `run_detection`).

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

> Note: the artifact registry covers only the two files above. `yolo11n.pt` is not part of `model_artifacts.py`, so `verify` and `bootstrap` do not check or download it. The backend handles it on its own (see "Object detection model").

---

## 4) Requirements

- Python 3.10+ (backend)
- Node.js 20+ and npm (frontend)
- Recommended for acceleration: NVIDIA GPU + CUDA-enabled PyTorch/TensorFlow environment
- Works on CPU (slower inference)
- Ultralytics (installed through `requirements.txt`) for YOLO object detection. It runs on the same PyTorch installation as the person detector.
- Internet access is needed once if `backend/yolo11n.pt` is not already present.

---

## 5) Setup (clean clone)

From repository root:

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python model_artifacts.py verify
```

If artifacts are missing/corrupted:
```bash
python model_artifacts.py bootstrap
```

Make sure the YOLO weights are in place (skip this if `backend/yolo11n.pt` already exists):
```bash
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```
This downloads `yolo11n.pt` into the current folder, so run it from inside `backend/`.

Check that all three ML libraries load together:
```bash
python -c "import tensorflow, torch, cv2; print('all ok')"
```

Run backend:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

> `python main.py` on its own only loads the file and exits; it does not start the web server. Always start the backend with `uvicorn` as shown above.

When the backend is ready, the terminal shows:
```text
INFO:     Uvicorn running on http://0.0.0.0:8000
[LIVE] Loading models (first frame may take a few seconds)...
[LIVE] Worker ready
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

### Windows (PowerShell) notes

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

- If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, then activate again.
- In PowerShell, `curl` is an alias for a different command. Use `curl.exe` for the examples in section 6.
- `requirements.txt` must be saved as UTF-8. A file written with `pip freeze > requirements.txt` in Windows PowerShell is UTF-16 and will make `pip install -r` fail.

---

## 6) Inference usage

Base backend URL: `http://localhost:8000`

### A) Low-light enhancement only
```bash
curl -X POST "http://localhost:8000/api/enhance-image" \
  -F "image=@/absolute/path/to/frame.jpg"
```

### B) Person and object detection
```bash
curl -X POST "http://localhost:8000/api/detect-objects?threshold=0.5" \
  -F "image=@/absolute/path/to/frame.jpg"
```

The older endpoint `/api/detect-person` is kept for backward compatibility. It runs the same function and returns the same result as `/api/detect-objects`, so it now includes objects as well as people. To read only the people, use the `person_present` and `person_count` fields (or the `person` entry in `counts`) of the response.

Objects usually score lower than people, especially in dark footage, so a threshold of `0.3` to `0.4` often works better for them than `0.5`.

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

The local scripts test the enhancement model and the person detector only. YOLO is exercised through the API endpoints above.

### Example response (`/api/detect-objects`)

```json
{
  "present": true,
  "count": 4,
  "person_present": true,
  "person_count": 1,
  "counts": { "person": 1, "backpack": 2, "bottle": 1 },
  "detections": [
    { "box": [10.0, 10.0, 60.0, 90.0], "confidence": 0.9512, "label": "person" },
    { "box": [100.0, 100.0, 180.0, 200.0], "confidence": 0.8, "label": "backpack" },
    { "box": [200.0, 50.0, 250.0, 140.0], "confidence": 0.7, "label": "backpack" },
    { "box": [300.0, 60.0, 330.0, 120.0], "confidence": 0.6, "label": "bottle" }
  ],
  "image": "data:image/jpeg;base64,..."
}
```

The numbers above are illustrative. `image` is the annotated frame as a base64 data URL.

### Response fields

| Field | Meaning |
|---|---|
| `present` | `true` if **any** object (person or otherwise) was detected |
| `count` | Total number of detections |
| `person_present` | `true` if at least one person was detected (use this for safety alerts) |
| `person_count` | Number of people detected |
| `counts` | Detections per class, for example `{"person": 1, "backpack": 2}` |
| `detections[]` | One entry per detection: `box` (`[x1, y1, x2, y2]` in pixels), `confidence`, `label` |
| `image` | Annotated image as a base64 data URL |

> Compatibility note: before object detection was added, `present` meant "a person was detected". It now means "any object was detected". Anything that only cares about people should read `person_present` instead.

### Extra fields in the combined and video endpoints
- `/api/analyze-image` returns `detection` with all the fields above, plus `brightness`, `was_dark`, and `enhanced_image`.
- `/api/analyze-video` returns, in addition to `frames[]` (each with its own `detection` block) and `total_detections`:
  - `any_person_detected`: a person appeared in at least one sampled frame
  - `any_object_detected`: any object appeared in at least one sampled frame
  - `class_totals`: detections per class summed over all sampled frames

---

## 7) Live ESP32-CAM + dashboard flow

Live receiver listens on backend port `5000`:
- endpoint: `POST /upload`
- fields expected: `cycle`, `sensor`, `frames`, `image1`, `image2`, `image3`, ...

Processed frames are broadcast to:
- `ws://127.0.0.1:8000/ws/camera`

Sensor stream endpoint:
- `ws://127.0.0.1:8000/ws/sensors`

For every frame the live worker checks brightness, enhances the frame if it is dark, runs person detection and object detection, and pushes the result to the dashboard. Each WebSocket message includes:

| Field | Meaning |
|---|---|
| `frame_id`, `received_at`, `cycle`, `frame_index`, `sensor` | Where the frame came from |
| `brightness`, `was_dark` | Brightness check result and whether enhancement was applied |
| `present`, `count` | Any object detected, and how many |
| `person_present`, `counts` | Person flag and per-class counts |
| `detections` | Boxes, confidences, and labels |
| `original`, `enhanced`, `annotated` | Images as base64 data URLs (`enhanced` is `null` when the frame was not dark) |
| `process_ms` | Total processing time for the frame in milliseconds |

The most recent result is also available for debugging at `http://localhost:8000/api/live/latest`.

The backend terminal prints one line per frame, for example:
```text
[LIVE] cycle 3 frame 1 brightness=41.2 dark=True objects=3 {'person': 1, 'bottle': 2} (480 ms)
```

---

## 8) Configuration and outputs

Key backend constants (`backend/main.py`):
- `DARKNESS_THRESHOLD = 50`
- `ENHANCE_IMAGE_SIZE = 256`
- `LIVE_THRESHOLD = 0.5`
- `MAX_VIDEO_FRAMES = 30`
- `VIDEO_SAMPLE_INTERVAL_SECONDS = 1.0`
- `YOLO_MODEL_PATH` (default `backend/yolo11n.pt`)

`LIVE_THRESHOLD` and the `threshold` query parameter apply to both the person detector and YOLO.

Outputs:
- JSON detections (`present`, `count`, `person_present`, `person_count`, `counts`, `detections[]`)
- Annotated output images as base64 data URLs (person boxes in blue, other objects in a color chosen per class, each labelled with class name and confidence)
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
  - Object detection adds a second model to every frame. Check `process_ms` on the dashboard to see the total cost per frame.
- **No live camera updates**
  - Confirm ESP32 is posting to backend port `5000` and frontend is using correct `NEXT_PUBLIC_CAMERA_WS_URL`.
- **`python main.py` prints "Opening Arduino..." and returns to the prompt**
  - This is expected. `main.py` does not start the server by itself. Start the backend with `uvicorn main:app --host 0.0.0.0 --port 8000`.
- **`Arduino unavailable ... could not open port 'COM7'`**
  - This only means no Arduino is connected on that port. Gas-sensor streaming stays idle; image and video analysis are not affected.
- **`[DETECT] YOLO object detection skipped: ...` or `[LIVE] YOLO object model failed to load: ...`**
  - People are still detected; only objects are missing. The message after the colon gives the reason.
  - `No module named 'ultralytics'`: run `pip install -r requirements.txt` inside the backend virtual environment.
  - Download or network error: connect to the internet once, or place `yolo11n.pt` in `backend/` manually.
- **TensorFlow, PyTorch, or OpenCV fail to import after installing packages**
  - Run `python -c "import tensorflow, torch, cv2; print('all ok')"` to see which one fails, then recreate the virtual environment and run `pip install -r requirements.txt` again.
- **People are detected but objects are not**
  - Only the 80 COCO classes are supported. Lower the threshold to `0.3`-`0.4`. Very dark frames reduce YOLO accuracy; compare `/api/detect-objects` (no enhancement) with `/api/analyze-image` (enhances dark frames) on the same photo.
- **`curl` fails with `-F` in PowerShell**
  - Use `curl.exe` instead of `curl`.
- **`pip install -r requirements.txt` fails with an encoding error**
  - Save `requirements.txt` as UTF-8.

---

## 10) Safety and operational limitations

- This is a **decision-support prototype**, not a certified safety system.
- Gas values and thresholds in dashboard are prototype-level and require domain calibration/validation.
- Vision models can miss detections under severe occlusion, motion blur, or extreme low light.
- Always maintain human-in-the-loop review for safety-critical cave operations.
- Object detection is limited to the 80 COCO classes. Cave-specific items (specialist equipment, rock falls, and similar) are not recognized without additional fine-tuning.
- The YOLO11-nano model trades accuracy for speed. It is more likely than the person detector to miss small, distant, or poorly lit objects, so treat object results as hints and keep people as the primary safety signal (`person_present`).
- The low-light enhancer resizes frames to `256x256` and back, which softens the image. For frames that are only moderately dark, detection on the original image may sometimes be better than on the enhanced one.

---

## 11) Development and validation

Backend quick checks:
```bash
cd backend
python -m unittest test_model_artifacts.py
python test_analysis.py
python model_artifacts.py verify
```

Object detection smoke test (backend running):
```bash
curl -X POST "http://localhost:8000/api/detect-objects?threshold=0.4" \
  -F "image=@test_photos/img3.jpeg"
```
The response should contain `counts` and an annotated `image`.

Frontend lint:
```bash
cd frontend
npm run lint
```

---

## 12) License and third-party attributions

- Repository code: see project license policy in this repository.
- TorchVision model architecture (`fasterrcnn_mobilenet_v3_large_fpn`): from `torchvision` (BSD-style license).
- Ultralytics YOLO11 (`yolo11n.pt` and the `ultralytics` package): released by Ultralytics under the **AGPL-3.0** license (an enterprise license is also offered by Ultralytics). Review these terms before distributing or deploying this project beyond coursework or research use. The weights were pretrained on the COCO dataset.
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