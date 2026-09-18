"""
Standalone laptop inference script for the fine-tuned Faster R-CNN + MobileNetV3-FPN person detector.

Setup (one-time, on your laptop):
    pip install torch torchvision matplotlib pillow

Usage:
    python test_local_inference_fasterrcnn.py --checkpoint fasterrcnn_person_best.pth --images path/to/img1.jpg path/to/img2.jpg
    python test_local_inference_fasterrcnn.py --checkpoint fasterrcnn_person_best.pth --folder path/to/folder_of_images

Tip: to properly verify detection quality, test on images you KNOW contain a
person — not the cave hard-negative images, which have no person by design.
"""

import argparse
import glob
import os

import torch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from torchvision.transforms import ToTensor
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor


def load_model(checkpoint_path, device):
    """Rebuilds the same architecture used during training, then loads your
    fine-tuned weights. NUM_CLASSES must match training (2 = background + person)."""
    NUM_CLASSES = 2
    model = fasterrcnn_mobilenet_v3_large_fpn(weights=None, weights_backbone=None)

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, NUM_CLASSES)

    state = torch.load(checkpoint_path, map_location=device)
    # Handles both a raw state_dict (fasterrcnn_person_best.pth / _final.pth)
    # and a full checkpoint dict (fasterrcnn_person_epochN.pth, which wraps it).
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    model.load_state_dict(state)

    model.to(device)
    model.eval()
    return model


def run_and_show(model, image_paths, device, score_thresh=0.5):
    n = len(image_paths)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 6))
    if n == 1:
        axes = [axes]

    for ax, path in zip(axes, image_paths):
        img = Image.open(path).convert("RGB")
        img_tensor = ToTensor()(img).to(device)

        with torch.no_grad():
            pred = model([img_tensor])[0]

        ax.imshow(img)
        num_shown = 0
        for box, score, label in zip(pred["boxes"], pred["scores"], pred["labels"]):
            if score < score_thresh:
                continue
            num_shown += 1
            x1, y1, x2, y2 = box.cpu().tolist()
            rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                      linewidth=2, edgecolor="red", facecolor="none")
            ax.add_patch(rect)
            ax.text(x1, max(y1 - 5, 0), f"person {score:.2f}",
                     color="red", fontsize=10, weight="bold")

        ax.set_title(f"{os.path.basename(path)}\n({num_shown} detection(s) >= {score_thresh})")
        ax.axis("off")
        print(f"{path}: {num_shown} detection(s) above threshold "
              f"(highest score seen: {pred['scores'].max().item():.3f} if any boxes exist)"
              if len(pred["scores"]) > 0 else f"{path}: model produced zero raw boxes")

    plt.tight_layout()
    out_path = "local_inference_result_fasterrcnn.png"
    plt.savefig(out_path, dpi=150)
    print("Saved:", out_path)
    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Path to fasterrcnn_person_best.pth (downloaded from Kaggle)")
    parser.add_argument("--images", nargs="*", default=None, help="One or more specific image paths")
    parser.add_argument("--folder", default=None, help="Or: a folder of images to test (first 4 used)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for drawing boxes")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    if args.images:
        image_paths = args.images
    elif args.folder:
        exts = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG", "*.webp")
        image_paths = []
        for ext in exts:
            image_paths.extend(glob.glob(os.path.join(args.folder, ext)))
        image_paths = sorted(set(image_paths))[:4]
    else:
        raise SystemExit("Provide either --images path1 path2 ... or --folder path/to/folder")

    if not image_paths:
        found = os.listdir(args.folder) if args.folder and os.path.isdir(args.folder) else []
        raise SystemExit(
            f"No images found at the given path(s). Folder contents were: {found}\n"
            f"Check the file extensions match, or pass exact paths with --images instead."
        )

    model = load_model(args.checkpoint, device)
    run_and_show(model, image_paths, device, score_thresh=args.threshold)


if __name__ == "__main__":
    main()