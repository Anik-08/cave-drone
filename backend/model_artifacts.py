from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen


BACKEND_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ModelArtifact:
    key: str
    filename: str
    sha256: str
    source_url: str
    license_note: str
    description: str

    @property
    def path(self) -> Path:
        return BACKEND_DIR / self.filename


MODEL_ARTIFACTS: tuple[ModelArtifact, ...] = (
    ModelArtifact(
        key="zero_dce_keras_v1",
        filename="dce_model.keras",
        sha256="cffeea6ff142185107fe0aff6dc30345cc1b73efcbb8495ec636f0a3083938ee",
        source_url="https://raw.githubusercontent.com/vikasprajapati-01/cave-drone/main/backend/dce_model.keras",
        license_note="Project artifact (verify reuse rights before redistribution).",
        description="Zero-DCE style curve-estimation network checkpoint used for low-light enhancement.",
    ),
    ModelArtifact(
        key="fasterrcnn_person_mbv3_fpn_v1",
        filename="fasterrcnn_person_best.pth",
        sha256="ce1c902f44622c53ec9244b8b88e3e7203affb7f3f6cb26c165fbcada6c59aec",
        source_url="https://raw.githubusercontent.com/vikasprajapati-01/cave-drone/main/backend/fasterrcnn_person_best.pth",
        license_note="Project artifact; architecture from TorchVision (BSD-style license).",
        description="Fine-tuned Faster R-CNN MobileNetV3-FPN person detector checkpoint.",
    ),
)


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(artifact: ModelArtifact) -> tuple[bool, str]:
    if not artifact.path.exists():
        return False, f"missing: {artifact.filename}"
    actual = compute_sha256(artifact.path)
    if actual.lower() != artifact.sha256.lower():
        return False, f"checksum mismatch: {artifact.filename} ({actual})"
    return True, f"ok: {artifact.filename}"


def verify_all_artifacts() -> list[tuple[ModelArtifact, bool, str]]:
    return [(artifact, *verify_artifact(artifact)) for artifact in MODEL_ARTIFACTS]


def _download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def bootstrap_artifacts(force: bool = False) -> list[str]:
    messages: list[str] = []
    for artifact in MODEL_ARTIFACTS:
        valid, status = verify_artifact(artifact)
        if valid and not force:
            messages.append(status)
            continue

        if artifact.path.exists():
            artifact.path.unlink()
        _download_file(artifact.source_url, artifact.path)
        valid_after, status_after = verify_artifact(artifact)
        if not valid_after:
            raise RuntimeError(
                f"Failed to bootstrap {artifact.filename}: {status_after}. "
                f"Source URL: {artifact.source_url}"
            )
        messages.append(f"downloaded: {artifact.filename}")
    return messages


def assert_required_artifacts_ready() -> None:
    errors = [status for _, valid, status in verify_all_artifacts() if not valid]
    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(
            "Required model artifact check failed: "
            f"{joined}. Run `python backend/model_artifacts.py bootstrap` from repository root."
        )


def _print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or bootstrap cave-drone model artifacts.")
    parser.add_argument(
        "command",
        choices=("verify", "bootstrap", "list"),
        default="verify",
        nargs="?",
        help="verify=check files, bootstrap=download+verify, list=print metadata",
    )
    parser.add_argument("--force", action="store_true", help="Force re-download during bootstrap.")
    args = parser.parse_args()

    if args.command == "list":
        lines = [
            f"{artifact.key}: file={artifact.filename} sha256={artifact.sha256} url={artifact.source_url}"
            for artifact in MODEL_ARTIFACTS
        ]
        _print_lines(lines)
        return 0

    if args.command == "bootstrap":
        _print_lines(bootstrap_artifacts(force=args.force))

    results = verify_all_artifacts()
    _print_lines(status for _, _, status in results)
    return 0 if all(valid for _, valid, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
